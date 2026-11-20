#!/usr/bin/env python3
import os
from pathlib import Path
from select import select
import signal
import subprocess
import sys
import tempfile
import time

script = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as path:
    command = Path(path) / "luajit"
    for code, expected in ((127, 3), (35, 1), (36, 1), (31, 1)):
        command.write_text(f"#!/bin/sh\nexit {code}\n")
        command.chmod(0o700)
        proc = subprocess.Popen(["/bin/sh", script], env=dict(os.environ, PATH=path + ":/bin:/usr/bin"),
                                stdout=subprocess.PIPE, start_new_session=True)
        try:
            seen = b""
            end = time.monotonic() + 12
            while b"SUPERVISOR_HOLD" not in seen:
                ready, _, _ = select([proc.stdout], [], [], max(0, end - time.monotonic()))
                assert ready
                seen += os.read(proc.stdout.fileno(), 4096)
            assert seen.count(b"SERVICE_LAUNCH") == expected
        finally:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
print("SUPERVISION maximum three pre-exec attempts; no automatic restart from terminal service errors")

