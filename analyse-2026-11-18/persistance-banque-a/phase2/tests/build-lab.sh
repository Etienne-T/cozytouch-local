#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
work=$(realpath "$1")
lab=$(realpath "$2")
tree=$lab/tree
mtd=$work/sources/mtd-utils-2.2.1
umask 077
mkdir -p "$tree/fixture" "$lab/persistent/boot/update" "$lab/prefs/ct"
gzip -dc "$work/images/rescue.cpio.gz" | (cd "$tree"; cpio -id --quiet)
cp -a "$work/latest-trees/root/bin/"{ln,grep,head,awk,sort,umount,readlink} "$tree/bin/"
ln -s busybox "$tree/bin/chroot"
install -m 0755 "$here/lab-init" "$tree/lab-init"
for binary in ubiformat ubiupdatevol; do
    install -m 0755 "$mtd/$binary" "$tree/sbin/$binary"
    arm-linux-gnueabi-strip "$tree/sbin/$binary"
done
printf '2\n' > "$lab/persistent/boot/boot_count_file"
printf 'ubi0:root\n' > "$lab/persistent/boot/boot_information_file"
printf '20180731\n' > "$lab/persistent/boot/update/bootloaderid"
mkfs.ubifs -m 2048 -e 126976 -x lzo -c 25 -U -r "$lab/persistent" -o "$lab/persistent.ubifs"
cat > "$lab/ubinize.cfg" <<EOF
[root]
mode=ubi
image=$work/images/root.ubifs
vol_id=7
vol_size=20951040
vol_type=static
vol_name=root
[apps]
mode=ubi
image=$work/images/apps.ubifs
vol_id=12
vol_size=16506880
vol_type=dynamic
vol_name=apps
[persistent]
mode=ubi
image=$lab/persistent.ubifs
vol_id=6
vol_size=3174400
vol_type=dynamic
vol_name=persistent
EOF
ubinize -m 2048 -p 131072 -s 2048 -O 2048 -o "$tree/fixture/lab.ubi" "$lab/ubinize.cfg"
mkfs.ubifs -m 2048 -e 126976 -x lzo -c 130 -U -r "$lab/prefs" -o "$tree/fixture/apps-synthetic.ubifs"
# Application trial fixtures (prefs-<name>: /ct plus /app staged by ct-update itself).
for variant in "$lab"/prefs-*; do
    [ -d "$variant" ] || continue
    mkfs.ubifs -m 2048 -e 126976 -x lzo -c 130 -U -r "$variant" -o "$tree/fixture/apps-${variant##*/prefs-}.ubifs"
done
(cd "$tree"; find . -print0 | LC_ALL=C sort -z | cpio -0 -o -H newc --owner 0:0 | gzip -n -1) > "$lab/lab.cpio.gz"

