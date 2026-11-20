import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

rows = {}
for path, expected_max in zip(map(Path, sys.argv[1:]), (165, 130), strict=True):
    data = path.read_bytes()
    magic, crc, _, length, kind = struct.unpack_from("<IIQIB", data)
    assert (magic, length, kind) == (0x06101831, 4096, 6)
    assert (zlib.crc32(data[8:length]) ^ 0xffffffff) == crc
    flags, min_io, leb, count, maximum = struct.unpack_from("<IIIII", data, 28)
    version, compressor = struct.unpack_from("<IH", data, 80)
    ro_compat = struct.unpack_from("<I", data, 124)[0]
    assert (flags, min_io, leb, maximum, version, compressor, ro_compat) == (0, 2048, 126976, expected_max, 4, 1, 0)
    assert len(data) == count * leb <= maximum * leb
    rows[path.name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                          flags=flags, min_io=min_io, leb_size=leb, leb_count=count, max_lebs=maximum,
                          format_version=version, compressor="lzo", ro_compat_version=ro_compat)
print(json.dumps(rows, indent=2))

