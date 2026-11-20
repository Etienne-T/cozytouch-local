# Libere OpenOCD apres le lancement RAM03 du 19 novembre 2026 (attempt-20261119).
# Derive de release-fusion-pi.py. Aucun reset, aucun halt, aucun acces NAND.
from pathlib import Path
import json, socket, subprocess, time

run = Path('<CHEMIN_LOCAL>')
state = json.loads((run / 'state.json').read_text())
assert state['stage'] == 'kernel_entry_requested_not_boot_confirmed', state['stage']
pid = state['openocd_pid']
cmdline = Path('/proc') / str(pid) / 'cmdline'
args = cmdline.read_bytes().split(b'\0')
assert Path(args[0].decode()).name == 'openocd'
assert b'<CHEMIN_LOCAL>' in args
print('OPENOCD_IDENTIFIED pid=%d' % pid, flush=True)
with socket.create_connection(('127.0.0.1', 6666), timeout=5) as sock:
    sock.sendall(b'shutdown\x1a')
for i in range(60):
    try:
        if not cmdline.read_bytes():
            break
    except FileNotFoundError:
        break
    time.sleep(.1)
else:
    raise RuntimeError('OpenOCD still active')
subprocess.run(['raspi-gpio', 'set', '8-11', 'ip'], check=True, capture_output=True)
assert subprocess.check_output(['raspi-gpio', 'get', '8-11']).count(b'func=INPUT') == 4
assert subprocess.run(['pgrep', '-x', 'openocd'], capture_output=True).returncode == 1
print('OPENOCD_STOPPED GPIO_INPUTS=4')
