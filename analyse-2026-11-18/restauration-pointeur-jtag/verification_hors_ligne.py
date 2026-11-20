import hashlib
import json
import struct
import sys
import tarfile
import zlib
from pathlib import Path

from ubireader.ubi import ubi
from ubireader.ubi_io import ubi_file
from ubireader.ubifs import ubifs, walk
from ubireader.ubifs.misc import process_reg_file


ROOT = Path(__file__).resolve().parents[2]
NAND = ROOT / 'donnees/nand-2026-11-17'
ARCHIVE = NAND.parent / 'cozytouch-nand-20261117.tar.gz'
BASE = ROOT / 'analyse-2026-11-17'
LIVE = NAND.parent / 'nand-live-2026-11-17/20261117T175226.846789Z'
LEB, PEB, PAGE, OOB = 0x1f000, 0x20000, 0x800, 0x40
SIZE = 0x8000000
POINTER, COUNT = 'boot_information_file', 'boot_count_file'
REFERENCE = {POINTER: b'ubi0:rootB\n', COUNT: b'0\n'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def inspect_archive():
    expected = {name: digest for digest, name in
                (line.split(maxsplit=1) for line in (NAND / 'SHA256SUMS').read_text().splitlines())}
    require(fingerprint(ARCHIVE) == Path(str(ARCHIVE) + '.sha256').read_text().split()[0], 'Archive SHA-256')
    with tarfile.open(ARCHIVE, 'r|gz') as archive:
        seen = set()
        for member in archive:
            if member.name not in expected:
                continue
            require(member.isfile() and member.name not in seen, 'Archive member')
            with archive.extractfile(member) as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            require(digest == expected[member.name] == fingerprint(NAND / member.name), member.name)
            seen.add(member.name)
        require(seen == set(expected), 'Archive incomplete')
    raw, data, oob = (NAND / name for name in ('nand-full-A-data-oob.raw', 'nand-data-128MiB.bin', 'nand-oob-4MiB.bin'))
    require((raw.stat().st_size, data.stat().st_size, oob.stat().st_size) ==
            (SIZE // PAGE * (PAGE + OOB), SIZE, SIZE // PAGE * OOB), 'Geometry')
    first, second = ([json.loads(line) for line in (NAND / name).read_text().splitlines()] for name in
                     ('pass-A/manifest.jsonl', 'verification-B.jsonl'))
    require(len(first) == len(second) == 64, 'Capture batch count')
    with raw.open('rb') as raw_stream, data.open('rb') as data_stream, oob.open('rb') as oob_stream:
        for index, (acquired, reread) in enumerate(zip(first, second)):
            segment = raw_stream.read(1024 * (PAGE + OOB))
            require(len(segment) == 1024 * (PAGE + OOB) and acquired['first_page'] == reread['first_page'] == index * 1024
                    and acquired['pages'] == reread['pages'] == 1024
                    and hashlib.sha256(segment).hexdigest() == acquired['sha256'] == reread['sha256_target'] == reread['sha256_A']
                    and f'{zlib.crc32(segment):08x}' == acquired['crc32'] == reread['crc32_target']
                    and reread['independent_nand_read'] and reread['match'], f'Capture batch {index}')
            require(all(segment[start:start + PAGE] == data_stream.read(PAGE) and
                        segment[start + PAGE:start + PAGE + OOB] == oob_stream.read(OOB)
                        for start in range(0, len(segment), PAGE + OOB)), f'Page layout in batch {index}')
    print('OK archive, SHA-256, 64 lots A/B, 65536 pages data/OOB.', flush=True)


def inspect_capture(data_path, volume_path, original):
    require(data_path.stat().st_size == SIZE, 'Data image size')
    volume = volume_path.read_bytes()
    image = ubi(ubi_file(str(data_path), PEB, PEB, None))
    require(len(image.images) == 1, 'UBI images')
    volumes = {entry.name.decode(): entry for entry in image.images[0].volumes.values()}
    ids = {'persistent': 6, 'root': 7, 'rootB': 9, 'apps': 12, 'appsB': 8}
    require({name: volumes[name].vol_id for name in ids} == ids, 'Volume IDs')
    blocks = {entry.leb_num: entry for entry in volumes['persistent'].get_blocks(image.blocks).values()}
    filesystem = ubifs(ubi_file(str(volume_path), LEB, 0, None))
    master = filesystem.master_node
    index, errors = {}, []
    walk.index(filesystem, master.root_lnum, master.root_offs, index, errors)
    require(not errors and filesystem.leb_size == LEB and len(volume) == 25 * LEB, 'UBIFS index or size')
    boot = next(entry.inum for entry in index[1]['dent'] if entry.name == 'boot')
    values, coordinates = {}, {}
    with data_path.open('rb') as physical, (NAND / 'nand-full-A-data-oob.raw').open('rb') as raw:
        if original:
            require(len(blocks) == 19, 'Reference volume map')
            for number in range(25):
                block = blocks.get(number)
                physical.seek(block.file_offset + block.ec_hdr.data_offset if block else 0)
                payload = physical.read(LEB) if block else b'\xff' * LEB
                require(payload == volume[number * LEB:(number + 1) * LEB], f'LEB {number}')
        for name, (expected_inode, expected_peb, expected_offset) in {
            POINTER: (70, 112, 0x2df800),
            COUNT: (71, 109 if original else 387, 0x2b3000 if original else 0x2b8800),
        }.items():
            inode = next(entry.inum for entry in index[boot]['dent'] if entry.name == name)
            node, = index[inode]['data']
            position = node.offset - 48
            number, offset = divmod(position, LEB)
            block = blocks[number]
            base = block.file_offset
            require((inode, base // PEB, position) == (expected_inode, expected_peb, expected_offset)
                    and base % PEB == 0 and PEB <= base <= SIZE - PEB
                    and block.ec_hdr.data_offset == 0x1000 and block.ec_hdr.vid_hdr_offset == PAGE, 'Coordinates')
            magic, crc, sequence, length, kind = struct.unpack_from('<IIQIB', volume, position)
            address = base + 0x1000 + offset
            page, column = divmod(address, PAGE)
            raw_address = page * (PAGE + OOB) + column
            require(magic == 0x06101831 and kind == 1 and node.compr_type == 0 and node.size == node.compr_len
                    and length == 48 + node.size and length <= min(LEB - offset, PAGE - column), 'Node size or type')
            serialized = volume[position:position + length]
            require(crc == (zlib.crc32(serialized[8:]) ^ 0xffffffff), 'UBIFS CRC')
            physical.seek(address)
            require(physical.read(length) == serialized, 'Physical node mismatch')
            if original:
                raw.seek(raw_address)
                require(raw.read(length) == serialized, 'Raw node mismatch')
            values[name] = process_reg_file(filesystem, index[inode], name, index)
            coordinates[name] = (address, sequence)
            print(f'{name}: PEB {base // PEB}, LEB {number}+{offset:#x}, data {address:#x}, raw {raw_address:#x}, sq {sequence}')
    require(values == REFERENCE, 'Reference contents')
    return values, coordinates


def fingerprints(files):
    return {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}


def simulate(reference, old, newer):
    require(old[COUNT] != newer[COUNT], 'Moving counter not detected')
    before = {POINTER: b'ubi0:root\n', COUNT: b'2\n', 'synthetic-neighbour': b'unchanged'}
    after = {**before, **reference}
    require(fingerprints(after) == fingerprints({**before, **REFERENCE}), 'Nominal result')
    for first in (COUNT, POINTER):
        partial = {**before, first: reference[first]}
        require(fingerprints(partial) != fingerprints(after), 'Partial write accepted')
        require(fingerprints({**partial, **{name: before[name] for name in reference}}) == fingerprints(before), 'Rollback')
    require(fingerprints({**after, 'synthetic-neighbour': b'changed'}) != fingerprints(after), 'Neighbour changed')
    missing = {name: value for name, value in before.items() if name != COUNT}
    restored = {name: (missing[name] if name in reference else value)
                for name, value in after.items() if name not in reference or name in missing}
    require(fingerprints(restored) == fingerprints(missing), 'Rollback with absent file')
    print('OK simulation: write, partial write rejected, neighbour change rejected, rollback.')


if __name__ == '__main__':
    require(len(sys.argv) == 1, 'No arguments accepted')
    inspect_archive()
    print('JTAG snapshot:', flush=True)
    reference, original = inspect_capture(NAND / 'nand-data-128MiB.bin',
                                          BASE / 'extraction/volumes/nand-data-128MiB.bin/img-372254595_vol-persistent.ubifs', True)
    print('Non-atomic Linux snapshot:', flush=True)
    _, newer = inspect_capture(LIVE / 'nand-live-nonatomic-data.bin',
                               BASE / 'live-interface/offline-backup/comparison/persistent-live-ecc.ubifs', False)
    simulate(reference, original, newer)
