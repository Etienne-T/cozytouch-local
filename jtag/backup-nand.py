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
import zlib

ROOT = Path('<CHEMIN_LOCAL>')
OUT = ROOT / 'nand-backup-20261117'
OUT.mkdir(exist_ok=True)
PAGE = 2112
RAM = 0x20000000
ENTRY = 0x00307000
DONE = 0x003070bc


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
        self.cmd('wait_halt 50000')
        expected = {'pc': DONE, 'r3': RAM + count * PAGE,
                    'r4': first + count, 'r5': 0}
        for reg, value in expected.items():
            actual = self.reg(reg)
            if actual != value:
                raise RuntimeError(f'{reg}: {actual:#x} != {value:#x}')
        target_crc = self.reg('sp_svc')
        attempt = 1
        while path.with_suffix(f'.attempt-{attempt}.flags').exists():
            attempt += 1
        flags_path = path.with_suffix(f'.attempt-{attempt}.flags')
        self.cmd(f'dump_image {flags_path} 0x20300000 {count}')
        flags = flags_path.read_bytes()
        assert len(flags) == count
        data = bytearray(b'\xff' * (count * PAGE))
        i = 0
        while i < count:
            if flags[i] == 255:
                i += 1
                continue
            start = i
            while i < count and flags[i] != 255:
                i += 1
            part = path.with_suffix(f'.attempt-{attempt}.range-{start}-{i}.bin')
            length = (i-start)*PAGE
            response = self.cmd(f'dump_image {part} {RAM+start*PAGE} {length}')
            if f'dumped {length} bytes' not in response:
                raise RuntimeError('Unexpected dump response: ' + response)
            buf = part.read_bytes()
            assert len(buf) == length
            data[start*PAGE:i*PAGE] = buf
        actual_crc = zlib.crc32(data)
        if actual_crc != target_crc:
            raise RuntimeError(f'CRC mismatch: {actual_crc:08x} != {target_crc:08x}')
        with path.open('xb') as result:
            result.write(data)
        self.last_stats = {'crc32': f'{actual_crc:08x}',
                           'erased_pages': flags.count(255)}
        return data


def validate(ocd):
    for page in [0, 63, 4096, 65535]:
        slow = ROOT / 'nand-20261117' / (f'validation-page{page}-slow.raw' if page else 'page0-slow-a.raw')
        fast = OUT / f'validation-page{page}-custom.raw'
        if fast.exists():
            raise RuntimeError('Validation path already exists')
        data = ocd.acquire(page, 1, fast)
        assert data == slow.read_bytes(), f'Page {page} differs'
        print(json.dumps({'validation_page': page, 'match': True,
                          'sha256': hashlib.sha256(data).hexdigest()}), flush=True)


def backup(ocd):
    # Each pass freshly reads every physical NAND page, including bad blocks.
    for label in ['A', 'B']:
        directory = OUT / ('pass-' + label)
        directory.mkdir(exist_ok=True)
        final = OUT / f'nand-full-{label}-data-oob.raw'
        digest = hashlib.sha256()
        began = time.monotonic()
        manifest_path = directory / 'manifest.jsonl'
        previous = [json.loads(line) for line in manifest_path.read_text().splitlines()] if manifest_path.exists() else []
        assert [r['first_page'] for r in previous] == list(range(0, len(previous)*1024, 1024))
        assert (final.stat().st_size if final.exists() else 0) == len(previous)*1024*PAGE
        with final.open('ab') as dest, manifest_path.open('a') as manifest:
            for first in range(0, 65536, 1024):
                chunk = directory / f'pages-{first:05d}-{first+1023:05d}.raw'
                if first//1024 < len(previous):
                    data = chunk.read_bytes()
                    assert len(data) == 1024*PAGE
                    assert hashlib.sha256(data).hexdigest() == previous[first//1024]['sha256']
                    digest.update(data)
                    continue
                for attempt in range(1, 4):
                    try:
                        data = ocd.acquire(first, 1024, chunk)
                        break
                    except RuntimeError as exc:
                        if 'CRC mismatch' not in str(exc) or attempt == 3:
                            raise
                        print(json.dumps({'retry_page': first, 'attempt': attempt,
                                          'reason': str(exc)}), flush=True)
                        if attempt == 2:
                            ocd.cmd('adapter speed 1000')
                sha = hashlib.sha256(data).hexdigest()
                record = {'pass': label, 'first_page': first, 'pages': 1024,
                          'bytes': len(data), 'sha256': sha,
                          'elapsed_s': round(time.monotonic()-began, 1)}
                record.update(ocd.last_stats)
                baseline = ROOT / 'nand-20261117' / 'pass-A' / chunk.name
                if baseline.exists():
                    record['identical_to_basic'] = data == baseline.read_bytes()
                    assert record['identical_to_basic'], 'Basic reader mismatch'
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


if __name__ == '__main__':
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
