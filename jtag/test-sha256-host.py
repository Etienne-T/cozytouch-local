import ctypes
import hashlib
import json
from pathlib import Path
root = Path('<CHEMIN_LOCAL>')
lib = ctypes.CDLL(str(root/'sha256-host.so'))
fn = lib.hash_buffer
fn.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
cases = [b'', b'abc', b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq', b'a'*1000000]
for n in [55,56,63,64,65,127,128,129,2112,2162688]:
    cases.append((bytes(range(256))*((n+255)//256))[:n])
results = []
for data in cases:
    output = ctypes.create_string_buffer(32)
    buf = ctypes.create_string_buffer(data)
    fn(buf, len(data), output)
    actual = output.raw.hex()
    expected = hashlib.sha256(data).hexdigest()
    assert actual == expected, len(data)
    results.append({'bytes': len(data), 'sha256': actual, 'match': True})
(root/'sha256-host-validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'tests_passed': len(results)}))
