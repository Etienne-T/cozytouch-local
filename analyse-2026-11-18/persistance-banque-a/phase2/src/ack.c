#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

static const char counter[] = "boot_count_file";
static const char scratch[] = ".boot_count_file.phase2";
static const char zero[] = "0\n";

static int inspect(int dir, const char *name, struct stat *st, int *already_zero)
{
    char data[12];
    int fd = openat(dir, name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
    if (fd < 0)
        return -1;
    int ok = !fstat(fd, st) && S_ISREG(st->st_mode) && st->st_uid == 0 &&
             st->st_nlink == 1 && !(st->st_mode & 022);
    ssize_t size = ok ? read(fd, data, sizeof(data)) : -1;
    close(fd);
    if (size < 2 || size >= (ssize_t)sizeof(data) || data[size - 1] != '\n')
        return -1;
    for (ssize_t i = 0; i + 1 < size; ++i)
        if (data[i] < '0' || data[i] > '9')
            return -1;
    *already_zero = size == 2 && data[0] == '0';
    return 0;
}

static void checkpoint(const char *name)
{
#ifdef CT_ACK_TEST
    const char *cut = getenv("CT_CUT");
    if (cut && !strcmp(cut, name)) {
        puts("CUT_POINT");
        fflush(stdout);
        raise(SIGSTOP);
    }
#else
    (void)name;
#endif
}

static int update(int dir)
{
    struct stat initial, verify, leftover;
    int was_zero, is_zero, own_scratch = 0, fd = -1, result = -1;

    if (inspect(dir, counter, &initial, &was_zero))
        return -1;
    if (!fstatat(dir, scratch, &leftover, AT_SYMLINK_NOFOLLOW)) {
        if (!S_ISREG(leftover.st_mode) || leftover.st_uid != 0 ||
            leftover.st_nlink != 1 || (leftover.st_mode & 022) ||
            unlinkat(dir, scratch, 0) || fsync(dir))
            return -1;
    } else if (errno != ENOENT) {
        return -1;
    }
    if (was_zero)
        return 0;
    fd = openat(dir, scratch, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0)
        return -1;
    own_scratch = 1;
    if (write(fd, zero, sizeof(zero) - 1) != (ssize_t)sizeof(zero) - 1 ||
        fchown(fd, initial.st_uid, initial.st_gid) ||
        fchmod(fd, initial.st_mode & 0777) || fsync(fd))
        goto out;
    checkpoint("before-rename");
    if (renameat(dir, scratch, dir, counter))
        goto out;
    own_scratch = 0;
    checkpoint("after-rename");
    if (fsync(dir) || inspect(dir, counter, &verify, &is_zero) || !is_zero ||
        (verify.st_mode & 0777) != (initial.st_mode & 0777) ||
        verify.st_gid != initial.st_gid)
        goto out;
    result = 0;
out:
    close(fd);
    if (own_scratch) {
        if (!unlinkat(dir, scratch, 0))
            (void)fsync(dir);
    }
    return result;
}

#ifndef CT_ACK_TEST
static int readonly_mount(FILE *mounts, const char *device, const char *where)
{
    char line[1024], source[96], path[96], fs[32], options[256];
    rewind(mounts);
    while (fgets(line, sizeof(line), mounts)) {
        if (sscanf(line, "%95s %95s %31s %255s", source, path, fs, options) == 4 &&
            !strcmp(path, where) && !strcmp(source, device) && !strcmp(fs, "ubifs") &&
            (!strcmp(options, "ro") || !strncmp(options, "ro,", 3)))
            return 1;
    }
    return 0;
}
#endif

int main(int argc, char **argv)
{
#ifdef CT_ACK_TEST
    if (argc != 4 || strcmp(argv[3], "healthy"))
        return 2;
    const char *guard = argv[1], *boot = argv[2];
#else
    (void)argv;
    struct utsname uts;
    FILE *mounts = fopen("/proc/mounts", "re");
    int healthy_mounts = mounts && readonly_mount(mounts, "ubi0:root", "/") &&
                         readonly_mount(mounts, "ubi0:apps", "/apps");
    if (mounts)
        fclose(mounts);
    if (argc != 1 || !healthy_mounts || uname(&uts) ||
        strcmp(uts.release, "6.12.0-cozy-a"))
        return 2;
    const char *guard = "/run/ct/boot-count-attempted";
    const char *boot = "/persistent/boot";
#endif
    int lock = open(guard, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (lock < 0)
        return errno == EEXIST ? 3 : 1;
    close(lock);
#ifndef CT_ACK_TEST
    if (mount("ubi0:persistent", "/persistent", "ubifs", MS_NODEV | MS_NOSUID | MS_NOEXEC, NULL))
        return 1;
#endif
    int dir = open(boot, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    int result = dir < 0 ? -1 : update(dir);
    if (dir >= 0)
        close(dir);
#ifndef CT_ACK_TEST
    if (umount("/persistent"))
        result = -1;
#endif
    return result ? 1 : 0;
}
