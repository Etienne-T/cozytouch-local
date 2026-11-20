#!/usr/bin/env python3
import concurrent.futures
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
if os.geteuid() != 0:
    raise SystemExit("Test uses a root-owned fixture")
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    boot = root / "boot"
    boot.mkdir()
    counter = boot / "boot_count_file"
    pointer = boot / "boot_information_file"
    scratch = boot / ".boot_count_file.phase2"
    lock = root / "boot-attempt"
    pointer.write_bytes(b"ubi0:root\n")
    pointer_inode = pointer.stat().st_ino
    def start(health="healthy", cut=None):
        env = os.environ.copy()
        if cut:
            env["CT_CUT"] = cut
        return subprocess.Popen([binary, lock, boot, health], env=env,
                                text=True, stdout=subprocess.PIPE)
    def reset():
        lock.unlink(missing_ok=True)
        counter.write_bytes(b"2\n")
        counter.chmod(0o644)
    reset()
    assert start("unhealthy").wait() == 2
    assert counter.read_bytes() == b"2\n" and not lock.exists() and not scratch.exists()
    print("HEALTH_KO unchanged")
    assert start().wait() == 0 and counter.read_bytes() == b"0\n"
    assert counter.stat().st_mode & 0o777 == 0o644 and not scratch.exists()
    assert start().wait() == 3
    print("HEALTH_OK durable readback and once-per-boot")
    reset()
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: start().wait(), range(2))) == [0, 3]
    print("CONCURRENT once only")
    for cut, content in (("before-rename", b"2\n"), ("after-rename", b"0\n")):
        reset()
        process = start(cut=cut)
        assert process.stdout.readline().strip() == "CUT_POINT"
        _, status = os.waitpid(process.pid, os.WUNTRACED)
        assert os.WIFSTOPPED(status)
        process.kill()
        assert process.wait() == -signal.SIGKILL
        assert counter.read_bytes() == content
        assert scratch.exists() == (cut == "before-rename")
        assert start().wait() == 3
        lock.unlink()
        assert start().wait() == 0 and counter.read_bytes() == b"0\n" and not scratch.exists()
        print(f"SIMULATED_PROCESS_CUT {cut} whole value, clean next healthy boot")
    assert pointer.read_bytes() == b"ubi0:root\n" and pointer.stat().st_ino == pointer_inode
    print("POINTER unchanged")

