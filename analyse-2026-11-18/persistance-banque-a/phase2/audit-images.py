import gzip
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

work = Path(sys.argv[1]).resolve()
images = work / "images"
root = work / "latest-trees/root"
durable = root / "boot/dtb"
rescue = images / "rescue.dtb"
chosen = "/chosen"
controller = "/ahb/ebi@10000000/nand-controller"
nand = controller + "/nand@3"
parts = nand + "/partitions"


def fdt(path, node, prop=None, kind="x"):
    if prop is None:
        args = ["fdtget", "-p", path, node]
    else:
        args = ["fdtget", "-t", kind, path, node, prop]
    return subprocess.check_output(args, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has(path, node, prop):
    return prop in fdt(path, node).splitlines()


config = (images / "sam9.config").read_text().splitlines()
enabled = ["MTD", "MTD_RAW_NAND", "MTD_NAND_ATMEL", "MTD_UBI", "UBIFS_FS", "UBIFS_FS_LZO"]
for option in enabled:
    assert f"CONFIG_{option}=y" in config
for option in ("MTD_NAND_NANDSIM", "MTD_UBI_FASTMAP", "UBIFS_FS_AUTHENTICATION", "FS_ENCRYPTION",
               "IP_PNP", "DEVMEM"):
    assert f"CONFIG_{option}=y" not in config
assert fdt(durable, chosen).splitlines() == ["stdout-path"]
for path in (durable, rescue):
    assert fdt(path, controller, "compatible", "s") == "atmel,at91sam9g45-nand-controller"
    assert fdt(path, controller, "status", "s") == "okay"
    ecc = fdt(path, controller, "ecc-engine")
    assert ecc == fdt(path, "/ahb/apb/ecc-engine@ffffe000", "phandle")
    assert fdt(path, nand, "nand-ecc-mode", "s") == "hw"
    assert fdt(path, nand, "nand-ecc-strength") == "4"
    assert fdt(path, nand, "nand-ecc-step-size") == "200"
    assert fdt(path, nand, "nand-bus-width") == "8"
    piod = fdt(path, "/ahb/apb/pinctrl@fffff400/gpio@fffffa00", "phandle")
    assert fdt(path, nand, "rb-gpios") == f"{piod} 5 0"
    assert fdt(path, nand, "cs-gpios") == f"{piod} 4 0"
    assert fdt(path, parts + "/bootstrap@0", "reg") == "0 20000"
    assert fdt(path, parts + "/ubi@20000", "reg") == "20000 7fe0000"
assert has(durable, nand, "nand-on-flash-bbt") and not has(rescue, nand, "nand-on-flash-bbt")
assert not has(durable, nand, "cozytouch,read-only-nand") and has(rescue, nand, "cozytouch,read-only-nand")
assert has(rescue, parts + "/ubi@20000", "read-only") and has(rescue, parts + "/bootstrap@0", "read-only")
assert "ubi.mtd" not in fdt(rescue, chosen, "bootargs", "s")
assert fdt(rescue, "/ahb/apb/serial@f801c000", "status", "s") == "disabled"

guard = work / "out/sam9/drivers/mtd/nand/raw/atmel/nand-controller.o"
assert b"Cozytouch NAND read-only command guard; RAM BBT only" in guard.read_bytes()
zimage = images / "rescue.zImage"
assert zimage.read_bytes()[0x24:0x28] == bytes.fromhex("18286f01")
assert sha(zimage) == sha(root / "boot/zImage")
assert (root / "boot/cmdline").read_bytes() == b"ubi.mtd=ubi rootfstype=ubifs ro ip=off\n"
assert (root / "boot/bootloaderid").read_bytes() == b"20180731\n"
assert not (root / "boot/initrd").exists()
assert not any((root / "root/.ssh").iterdir())
assert not any((work / "latest-trees/apps/ct").iterdir())
assert stat.S_IMODE((work / "latest-trees/apps/ct").stat().st_mode) == 0o700

cpio = images / "rescue.cpio.gz"
count = cpio.stat().st_size
start = int(fdt(rescue, chosen, "linux,initrd-start"), 16)
end = int(fdt(rescue, chosen, "linux,initrd-end"), 16)
assert start == 0x24000000 and end == start + count
assert rescue.stat().st_size <= 1024 * 1024 and zimage.stat().st_size <= 8 * 1024 * 1024
assert count <= 16 * 1024 * 1024
payload = gzip.decompress(cpio.read_bytes())
assert payload.startswith(b"070701")
assert b"ssh_host_key" not in payload and b"authorized_keys" not in payload
print(json.dumps({
    "sam9_builtin": enabled,
    "pmecc": {"bits": 4, "step": 512},
    "durable_dtb_sha256": sha(durable),
    "durable_dtb_initrd_bounds": False,
    "root_boot_marker": "20180731",
    "kboot_default_marker_path": "/persistent/boot/update/bootloaderid",
    "compiled_atmel_read_only_guard": True,
    "rescue_auto_attach": False,
    "rescue_ram": {
        "dtb": hex(0x21000000), "zImage": hex(0x22000000),
        "initrd_start": hex(start), "initrd_end_exclusive": hex(end)
    },
    "private_configuration_files_in_distributable": 0,
}, indent=2))

