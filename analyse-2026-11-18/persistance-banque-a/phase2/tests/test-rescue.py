#!/usr/bin/env python3
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

work = Path(sys.argv[1]).resolve()
dtb = work / "out/qemu/arch/arm/boot/dts/arm/versatile-pb.dtb"
cmdline = ("console=ttyAMA0 rdinit=/init panic=-1 loglevel=5 "
           "nandsim.first_id_byte=0x2c nandsim.second_id_byte=0xf1 "
           "nandsim.third_id_byte=0x80 nandsim.fourth_id_byte=0x15 nandsim.parts=1,1023")
params = ["qemu-system-arm", "-M", "versatilepb", "-cpu", "arm926", "-m", "128M", "-display", "none",
          "-serial", "stdio", "-monitor", "none", "-audio", "none", "-nic", "none", "-no-reboot",
          "-kernel", work / "bin/qemu.zImage", "-dtb", dtb, "-initrd", work / "images/rescue.cpio.gz",
          "-append", cmdline]
with subprocess.Popen(params, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as vm:
    output = queue.Queue()
    def pump():
        while data := os.read(vm.stdout.fileno(), 4096):
            output.put(data)
    threading.Thread(target=pump, daemon=True).start()
    seen = b""
    def expect(marker, timeout=20):
        global seen
        end = time.monotonic() + timeout
        while marker not in seen:
            try:
                seen += output.get(timeout=max(0.01, end - time.monotonic()))
            except queue.Empty:
                raise AssertionError(seen[-2500:].decode(errors="replace")) from None
    try:
        expect(b"COZY_RESCUE_RO: MTD, no automatic UBI attach")
        expect(b"# ")
        # Output markers are split in the command so serial echo is never a pass.
        vm.stdin.write(b"mtdinfo /dev/mtd1 && [ ! -d /sys/class/ubi/ubi0 ] && printf 'RESCUE_%s\\n' 'TOOLS_OK'\n")
        vm.stdin.flush()
        expect(b"RESCUE_TOOLS_OK")
        assert b"NAND" in seen and b"131072" in seen
        print("RESCUE_EXACT_CPIO booted under ARM926, mtdinfo usable, no automatic UBI attachment")
    finally:
        vm.terminate()
        vm.wait(timeout=5)

