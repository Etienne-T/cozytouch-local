#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
project=$(realpath "$here/../../..")
workspace=$(realpath "$1")
out=$workspace/images
trees=$(mktemp -d "$workspace/trees.XXXXXXXX")
root=$trees/root
apps=$trees/apps
rescue=$trees/rescue
mtd=$workspace/sources/mtd-utils-2.2.1
reference=$project/analyse-2026-11-18/variante-fusion
umask 022
mkdir -p "$out" "$root" "$apps" "$rescue"
python3 "$here/extract-runtime.py" "$reference/images/rootfs.cpio.gz" "$root"
for directory in proc sys dev dev/pts run tmp apps persistent root/.ssh boot etc usr/libexec/ct sbin; do
    mkdir -p "$root/$directory"
done
chmod 0700 "$root/root" "$root/root/.ssh"
chmod 1777 "$root/tmp"
for name in sh ash mount umount mkdir sleep watchdog setsid cttyhack cat ls grep awk ip dmesg printf ln \
            readlink sync chmod chown stat poweroff head sort dd hexdump date sha256sum rm reboot flock; do
    ln -s busybox "$root/bin/$name"
done
ln -s ../init "$root/sbin/init"
for name in iptables ip6tables iptables-save ip6tables-save; do
    ln -s xtables-legacy-multi "$root/usr/sbin/$name"
done
printf 'root:x:0:0:root:/root:/bin/sh\n' > "$root/etc/passwd"
printf 'root:x:0:\ntty:x:5:\n' > "$root/etc/group"
printf 'root:*:0:0:99999:7:::\n' > "$root/etc/shadow"
chmod 0600 "$root/etc/shadow"
printf 'passwd: files\ngroup: files\nshadow: files\nhosts: files\n' > "$root/etc/nsswitch.conf"
install -m 0755 "$here/src/init-durable" "$root/init"
install -m 0755 "$here/src/"{supervise,network.sh,healthy,ct-update} "$root/usr/libexec/ct/"
install -m 0644 "$here/src/ct-update.lua" "$root/usr/libexec/ct/"
ln -s ../libexec/ct/ct-update "$root/usr/bin/ct-update"
arm-linux-gnueabi-gcc -Wall -Wextra -Werror -march=armv5te -Os -s -static \
    "$here/src/ack.c" -o "$root/usr/libexec/ct/ack"
arm-linux-gnueabi-gcc -Wall -Wextra -Werror -march=armv5te -Os -s -fPIC -shared \
    "$here/src/private.c" -o "$root/usr/lib/libct-safe.so"
old_service=$project/analyse-2026-11-17/buildroot-ram/variante-service-20261118/overlay/usr/share/cozytouch/mqtt
python3 "$here/prepare-lua.py" "$old_service" "$here/src" "$root/usr/share/cozytouch/phase2"
for module in "$root/usr/share/cozytouch/phase2/"*.lua "$root/usr/libexec/ct/ct-update.lua"; do
    LD_LIBRARY_PATH="$root/usr/lib" qemu-arm -cpu arm926 -L "$root" "$root/usr/bin/luajit" -e "assert(loadfile('$module'))" >/dev/null
done
install -m 0644 "$workspace/bin/sam9.zImage" "$root/boot/zImage"
install -m 0644 "$workspace/bin/durable.dtb" "$root/boot/dtb"
printf '%s\n' 'ubi.mtd=ubi rootfstype=ubifs ro ip=off' > "$root/boot/cmdline"
printf '%s\n' 20180731 > "$root/boot/bootloaderid"
mkdir -m 0700 "$apps/ct"
# Buildroot runtime selection starts with explicit ELF paths. No historic config is copied.
mkfs.ubifs -m 2048 -e 126976 -x lzo -c 165 -U -r "$root" -o "$out/root.ubifs"
mkfs.ubifs -m 2048 -e 126976 -x lzo -c 130 -U -r "$apps" -o "$out/apps.ubifs"
python3 "$here/verify-superblock.py" "$out/root.ubifs" "$out/apps.ubifs" > "$out/ubifs.json"

mkdir -p "$rescue/"{dev,proc,sys,run,bin,lib,sbin}
cp -a "$root/bin/"{busybox,sh,mount,mkdir,watchdog,setsid,cttyhack,cat,ls,dmesg,dd,sleep,hexdump,sha256sum} "$rescue/bin/"
cp -a "$root/lib/"{ld-linux.so.3,libc.so.6,libm.so.6,libgcc_s.so.1,libpthread.so.0,libresolv.so.2} "$rescue/lib/"
install -m 0755 "$here/src/init-rescue" "$rescue/init"
for binary in mtdinfo nanddump ubinfo ubiattach ubidetach; do
    install -m 0755 "$mtd/$binary" "$rescue/sbin/$binary"
    arm-linux-gnueabi-strip "$rescue/sbin/$binary"
done
mknod -m 0600 "$rescue/dev/console" c 5 1
(cd "$rescue"; find . -print0 | LC_ALL=C sort -z | cpio -0 -o -H newc --owner=0:0 | gzip -n -9) > "$out/rescue.cpio.gz"
install -m 0644 "$workspace/bin/sam9.zImage" "$out/rescue.zImage"
install -m 0644 "$workspace/bin/rescue.dtb" "$out/rescue.dtb"
bytes=$(wc -c < "$out/rescue.cpio.gz")
test "$bytes" -le 16777216
fdtput -t x "$out/rescue.dtb" /chosen linux,initrd-end "$(printf '%x' "$((0x24000000 + bytes))")"
install -m 0644 "$workspace/bin/sam9.config" "$out/sam9.config"
(cd "$out"; sha256sum root.ubifs apps.ubifs rescue.zImage rescue.dtb rescue.cpio.gz sam9.config ubifs.json > SHA256SUMS)
ln -sfn "$trees" "$workspace/latest-trees"
printf '%s\n' "IMAGES_OK"

