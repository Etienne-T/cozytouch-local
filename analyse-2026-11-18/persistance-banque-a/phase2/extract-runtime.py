import gzip
import hashlib
from pathlib import Path
import re
import stat
import sys

archive, root = map(Path, sys.argv[1:])
data = archive.read_bytes()
assert hashlib.sha256(data).hexdigest() == "fcf6ea211338de9453551d940c2d7c991dd730637876903aeb52899987e430cf"
manifest = {
    "bin/busybox", "lib/ld-linux.so.3", "lib/libc.so.6", "lib/libm.so.6", "lib/libdl.so.2",
    "lib/libgcc_s.so.1", "lib/libpthread.so.0", "lib/libresolv.so.2", "lib/librt.so.1",
    "lib/libutil.so.1", "usr/bin/luajit", "usr/lib/lua/5.1/cjson.so", "usr/lib/libcrypt.so.2",
    "usr/lib/libcrypt.so.2.0.0", "usr/lib/libip4tc.so.2", "usr/lib/libip4tc.so.2.0.0",
    "usr/lib/libip6tc.so.2", "usr/lib/libip6tc.so.2.0.0", "usr/lib/libxtables.so.12",
    "usr/lib/libxtables.so.12.7.0", "usr/lib/xtables/libxt_conntrack.so",
    "usr/lib/xtables/libxt_standard.so", "usr/lib/xtables/libxt_tcp.so",
    "usr/sbin/xtables-legacy-multi", "usr/sbin/dropbear", "usr/bin/dropbearkey",
    "usr/lib/libluajit-5.1.so.2", "usr/lib/libluajit-5.1.so.2.1.1767980792",
}
payload = gzip.decompress(data)
cursor = 0
installed = set()
while cursor + 110 <= len(payload):
    header = payload[cursor:cursor + 110]
    assert header.startswith(b"070701")
    fields = [int(header[i:i + 8], 16) for i in range(6, 110, 8)]
    size, name_size = fields[6], fields[11]
    name = payload[cursor + 110:cursor + 110 + name_size - 1].decode()
    cursor = (cursor + 110 + name_size + 3) & ~3
    if name == "TRAILER!!!":
        break
    if name in manifest:
        assert name not in installed
        item = root / name
        item.parent.mkdir(parents=True, exist_ok=True)
        body = payload[cursor:cursor + size]
        if stat.S_ISLNK(fields[1]):
            link = body.decode()
            assert re.fullmatch(r"(?:\.\./sbin/)?[A-Za-z0-9._+-]+", link)
            item.symlink_to(link)
        else:
            assert stat.S_ISREG(fields[1]) and body.startswith(b"\x7fELF")
            item.write_bytes(body)
            item.chmod(fields[1] & 0o777)
        installed.add(name)
    cursor = (cursor + size + 3) & ~3
assert installed == manifest
print(f"FUSION_ELF_ALLOWLIST entries={len(installed)}")

