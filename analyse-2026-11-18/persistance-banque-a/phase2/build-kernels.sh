#!/bin/bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
project=$(realpath "$here/../../..")
workspace=$(realpath "$1")
source=$workspace/sources/linux-6.12
out=$workspace/out
mkdir -p "$out" "$workspace/bin"
export ARCH=arm CROSS_COMPILE=arm-linux-gnueabi-
export KBUILD_BUILD_USER=cozytouch KBUILD_BUILD_HOST=offline
export KBUILD_BUILD_TIMESTAMP='2026-11-18 00:00:00 UTC'
export KBUILD_BUILD_VERSION=1 LC_ALL=C
python3 "$here/patch-nand.py" "$source"
dts=$source/arch/arm/boot/dts
install -m 644 "$project/analyse-2026-11-17/buildroot-ram/boot-review/at91-kizboxmini-ram4.dts" "$dts/"
install -m 644 "$here/src/"{nand.dtsi,leds.dtsi,durable.dts,rescue.dts} "$dts/"
kernel() {
    profile=$1
    base=$2
    shift 2
    config=$out/$profile/.config
    mkdir -p "$out/$profile"
    cp "$base" "$config"
    "$source/scripts/config" --file "$config" \
        --set-str LOCALVERSION -cozy-a --disable LOCALVERSION_AUTO \
        --enable MTD --enable MTD_RAW_NAND --enable MTD_NAND_ECC_SW_HAMMING \
        --enable MTD_UBI --disable MTD_UBI_FASTMAP --enable UBIFS_FS --enable UBIFS_FS_LZO \
        --disable UBIFS_FS_AUTHENTICATION --disable UBIFS_FS_ENCRYPTION \
        --disable FS_ENCRYPTION --enable TMPFS --enable DEVTMPFS --enable DEVTMPFS_MOUNT "$@"
    make -s -C "$source" O="$out/$profile" olddefconfig
    for symbol in MTD MTD_RAW_NAND MTD_UBI UBIFS_FS UBIFS_FS_LZO; do
        grep -qx "CONFIG_$symbol=y" "$config"
    done
    make -s -C "$source" O="$out/$profile" -j"$JOBS" zImage
    cp "$out/$profile/arch/arm/boot/zImage" "$workspace/bin/$profile.zImage"
    cp "$config" "$workspace/bin/$profile.config"
}
: "${JOBS:=12}"
reference=$project/analyse-2026-11-18/variante-fusion
case "${2:-sam9}" in
sam9)
    kernel sam9 "$reference/images/kernel.config" --enable MTD_NAND_ATMEL --disable MTD_NAND_NANDSIM
    grep -qx CONFIG_MTD_NAND_ATMEL=y "$workspace/bin/sam9.config"
    for profile in durable rescue; do
        "${CROSS_COMPILE}cpp" -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
            -I "$source/include" -I "$dts" "$dts/$profile.dts" > "$out/$profile.dts"
        dtc -I dts -O dtb -o "$workspace/bin/$profile.dtb" "$out/$profile.dts"
    done
    ;;
qemu)
    kernel qemu "$reference/evidence/qemu-kernel.config" --enable MTD_NAND_NANDSIM --enable MTD_NAND_ECC_SW_BCH
    grep -qx CONFIG_MTD_NAND_NANDSIM=y "$workspace/bin/qemu.config"
    ;;
*) exit 2;;
esac

