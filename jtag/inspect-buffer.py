from pathlib import Path
import zlib
import json
root = Path('<CHEMIN_LOCAL>')
data = (root/'failed-buffer-reread.raw').read_bytes()
assert len(data) == 2162688
flags = (root/'pass-A/pages-06144-07167.flags').read_bytes()
old = bytearray(b'\xff' * len(data))
for part in (root/'pass-A').glob('pages-06144-07167.range-*.bin'):
    start, end = map(int, part.stem.split('-')[-2:])
    old[start*2112:end*2112] = part.read_bytes()
diff = [i for i, (a,b) in enumerate(zip(old, data)) if a != b]
print(json.dumps({'crc_reread': f'{zlib.crc32(data):08x}',
                  'crc_initial': f'{zlib.crc32(old):08x}',
                  'different_bytes': len(diff), 'first_offsets': diff[:20],
                  'false_erased_flags': [i for i,x in enumerate(flags)
                      if x == 255 and data[i*2112:(i+1)*2112] != b'\xff'*2112]}))
