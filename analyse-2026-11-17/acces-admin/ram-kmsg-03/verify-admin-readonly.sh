#!/bin/sh
# Run only after the parent authenticates to the temporary daemon.
# Does not print keys, tokens, authorized_keys, environment, or process cmdlines.
set -eu
printf 'IDENTITY\n'
id
printf 'ROOT_UID\n'
id -u
test "$(id -u)" = 0
printf 'KERNEL_RELEASE_AND_ARCH\n'
uname -r
uname -m
printf 'SELECTED_MOUNTS\n'
awk '$2=="/" || $2=="/run" || $2=="/root/.ssh" || $2=="/persistent" || $2=="/data" {print $1,$2,$3,$4}' /proc/mounts
printf 'RAM_PATH_PERMISSIONS\n'
stat -c '%u %g %a %n' /run/ct /run/ct/ssh /run/ct/ssh/authorized_keys /run/ct/h
printf 'SSH_TEMPORARY_VIEW_MATCH\n'
if cmp -s /run/ct/ssh/authorized_keys /root/.ssh/authorized_keys; then
    printf 'temporary_authorized_key_view_matches=yes\n'
else
    printf 'temporary_authorized_key_view_matches=no\n'
    exit 1
fi
printf 'DROPBEAR_PROCESS\n'
read -r pid < /run/ct/p
case "$pid" in ''|*[!0-9]*) printf 'invalid_pid\n';exit 1;;esac
printf 'pid=%s\n' "$pid"
cat "/proc/$pid/comm"
awk '/^Uid:/ || /^Gid:/ {print}' "/proc/$pid/status"
printf 'READ_ONLY_ADMIN_CHECK_PASSED\n'
