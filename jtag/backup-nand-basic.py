"""Physical NAND backup over an already initialized OpenOCD Tcl session.

Uses nand-reader.bin in volatile SRAM. NAND commands are READ only.
Writes new files exclusively; never overwrites a previous acquisition.
"""
import hashlib
import json
from pathlib import Path
import re
import socket
import sys
import time

ROOT = Path('<CHEMIN_LOCAL>')
OUT = ROOT / 'nand-20261117'
PAGE = 2112
RAM = 0x20000000
ENTRY = 0x00307000
DONE = 0x00307080


class OCD:
    def __init__(self):
        self.sock = socket.create_connection(('127.0.0.1', 6666), 10)
        self.sock.settimeout(180)

    def cmd(self, command):
        self.sock.sendall(command.encode() + b'\x1a')
        data = b''
        while b'\x1a' not in data:
            part = self.sock.recv(65536)
            if not part:
                raise RuntimeError('OpenOCD connection closed')
            data += part
        result = data.split(b'\x1a')[0].decode(errors='replace').strip()
        if re.search(r'error|not halted|timed out|failed', result, re.I):
            raise RuntimeError(command + ': ' + result)
        return result

    def reg(self, name):
        result = self.cmd('reg ' + name)
        return int(re.search(r'0x([0-9a-fA-F]+)', result).group(1), 16)

    def acquire(self, first, count, path):
        assert not path.exists(), path
        assert 0 <= first < 65536 and 0 < count <= 1024
        assert first + count <= 65536
        self.cmd('reg r3 0x%x' % RAM)
        self.cmd('reg r4 %d' % first)
        self.cmd('reg r5 %d' % count)
        self.cmd('resume 0x%x' % ENTRY)
        self.cmd('wait_halt 20000')
        expected = {'pc': DONE, 'r3': RAM + count * PAGE,
                    'r4': first + count, 'r5': 0}
        for reg, value in expected.items():
            actual = self.reg(reg)
            if actual != value:
                raise RuntimeError(f'{reg}: {actual:#x} != {value:#x}')
        response = self.cmd(f'dump_image {path} {RAM} {count * PAGE}')
        if 'dumped %d bytes' % (count * PAGE) not in response:
            raise RuntimeError('Unexpected dump response: ' + response)
        data = path.read_bytes()
        if len(data) != count * PAGE:
            raise RuntimeError('Wrong chunk size')
        return data


def validate(ocd):
    ocd.cmd('at91sam9g25.cpu configure -work-area-size 0')
    for page in [63, 4096, 65535]:
        slow = OUT / f'validation-page{page}-slow.raw'
        fast = OUT / f'validation-page{page}-custom.raw'
        if slow.exists() or fast.exists():
            raise RuntimeError('Validation path already exists')
        ocd.cmd('mww 0xfffffe40 0xa5000001')
        reply = ocd.cmd(f'nand dump 0 {slow} {page * 2048} 2048 oob_raw')
        assert 'dumped 2112 bytes' in reply, reply
        assert ocd.reg('pc') == DONE
        data = ocd.acquire(page, 1, fast)
        assert data == slow.read_bytes(), f'Page {page} differs'
        print(json.dumps({'validation_page': page, 'match': True,
                          'sha256': hashlib.sha256(data).hexdigest()}), flush=True)


def backup(ocd):
    # Each pass freshly reads every physical NAND page, including bad blocks.
    for label in ['A', 'B']:
        directory = OUT / ('pass-' + label)
        directory.mkdir(exist_ok=False)
        final = OUT / f'nand-full-{label}-data-oob.raw'
        digest = hashlib.sha256()
        began = time.monotonic()
        with final.open('xb') as dest, (directory / 'manifest.jsonl').open('x') as manifest:
            for first in range(0, 65536, 1024):
                chunk = directory / f'pages-{first:05d}-{first+1023:05d}.raw'
                data = ocd.acquire(first, 1024, chunk)
                sha = hashlib.sha256(data).hexdigest()
                record = {'pass': label, 'first_page': first, 'pages': 1024,
                          'bytes': len(data), 'sha256': sha,
                          'elapsed_s': round(time.monotonic()-began, 1)}
                if label == 'B':
                    original = OUT / 'pass-A' / chunk.name
                    record['identical_to_A'] = data == original.read_bytes()
                    if not record['identical_to_A']:
                        record['mismatch'] = True
                dest.write(data)
                dest.flush()
                digest.update(data)
                line = json.dumps(record)
                manifest.write(line + '\n')
                manifest.flush()
                print(line, flush=True)
        print(json.dumps({'pass_complete': label, 'bytes': final.stat().st_size,
                          'sha256': digest.hexdigest()}), flush=True)


ocd = OCD()
try:
    if sys.argv[1:] == ['validate']:
        validate(ocd)
    elif sys.argv[1:] == ['backup']:
        backup(ocd)
    else:
        raise SystemExit('Use validate or backup')
finally:
    ocd.sock.close()
