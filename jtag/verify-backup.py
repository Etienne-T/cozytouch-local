"""Verify acquired image against independent on-target SHA-256 reread."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

root = Path(sys.argv[1])
size = 65536 * 2112
a_path = root / 'nand-full-A-data-oob.raw'
assert a_path.stat().st_size == size
a = a_path.read_bytes()
report = {'raw_bytes': size, 'page_data_bytes': 2048, 'page_oob_bytes': 64,
          'pages': 65536, 'blocks': 1024,
          'sha256_A': hashlib.sha256(a).hexdigest(),
          'verification_mode': 'Full independent NAND reread; on-target SHA-256 per 1024 pages; no second raw image synthesized.'}
records = [json.loads(line) for line in
           (root/'pass-A/manifest.jsonl').read_text().splitlines()]
second = [json.loads(line) for line in
          (root/'verification-B.jsonl').read_text().splitlines()]
assert len(records) == len(second) == 64
for index, (record, reread) in enumerate(zip(records, second)):
    assert record['first_page'] == reread['first_page'] == index*1024
    assert record['pages'] == reread['pages'] == 1024
    assert record['bytes'] == reread['bytes'] == 2162688
    segment = a[index*2162688:(index+1)*2162688]
    sha = hashlib.sha256(segment).hexdigest()
    crc = f'{zlib.crc32(segment):08x}'
    assert sha == record['sha256'] == reread['sha256_target'] == reread['sha256_A']
    assert crc == record['crc32'] == reread['crc32_target']
    assert reread['independent_nand_read'] and reread['match']
report['manifest_chunks_verified'] = 128
report['all_target_crc32_verified'] = True
report['independent_read_sha256_verified'] = True
report['independent_sha256_chunks_verified'] = 64
data = bytearray()
oob = bytearray()
erased = 0
for i in range(65536):
    page = a[i*2112:(i+1)*2112]
    data.extend(page[:2048])
    oob.extend(page[2048:])
    erased += page == b'\xff' * 2112
report['fully_erased_pages'] = erased
report['non_ff_bad_block_marker_candidates'] = [block for block in range(1024)
    if oob[block*64*64] != 255 or oob[(block*64+1)*64] != 255]
report['ubi_eraseblock_headers'] = [i for i in range(1024)
    if data[i*131072:i*131072+4] == b'UBI#']
images = []
offset = 0
while True:
    offset = data.find(b'\x27\x05\x19\x56', offset)
    if offset < 0:
        break
    if offset + 64 <= len(data):
        header = bytearray(data[offset:offset+64])
        magic, hcrc, timestamp, length, load, entry, dcrc = struct.unpack('>7I', header[:28])
        header[4:8] = b'\0' * 4
        if zlib.crc32(header) == hcrc and offset+64+length <= len(data):
            images.append({'offset': offset, 'data_bytes': length,
                           'header_crc_ok': True,
                           'physical_contiguous_payload_crc_ok': zlib.crc32(data[offset+64:offset+64+length]) == dcrc,
                           'os': header[28], 'arch': header[29],
                           'type': header[30], 'compression': header[31]})
    offset += 4
report['uimage_headers'] = images
for name, content in [('nand-data-128MiB.bin', data), ('nand-oob-4MiB.bin', oob)]:
    with (root / name).open('xb') as f:
        f.write(content)
    report[name] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
report['limitations'] = ['Raw acquisition; ECC bytes preserved, no ECC correction applied.',
                         'No hardware restore tested.',
                         'STM32 internal flash is not included.',
                         'uImage payload checks use physical contiguous bytes; UBI mapping is not reconstructed.']
(root / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'ubi_eraseblock_headers'}, indent=2))
print('UBI eraseblocks:', len(report['ubi_eraseblock_headers']))
