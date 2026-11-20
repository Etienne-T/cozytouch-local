"""Pause our acquisition driver after pass A, for the SHA-256 verification path."""
from pathlib import Path
import os
import signal
import time
root=Path('<CHEMIN_LOCAL>')
pid=15567
while True:
    process=Path(f'/proc/{pid}/cmdline')
    if not process.exists() or b'backup-nand-sparse.py' not in process.read_bytes():
        raise SystemExit('Acquisition driver not running; no process signalled')
    records=(root/'pass-A/manifest.jsonl').read_text().splitlines()
    if len(records)==64 and (root/'nand-full-A-data-oob.raw').stat().st_size==138412032:
        os.kill(pid,signal.SIGSTOP)
        print('PASS_A_COMPLETE_DRIVER_PAUSED',flush=True)
        break
    time.sleep(1)
