#!/usr/bin/env python3
"""Build a CTAPP1 application archive for ct-update.

Usage: build-app.py <module directory> <output.ctapp> [--include name.lua ...]
Takes every *.lua of the directory except radio-start.lua, which belongs to root A
(it drives the radio power line and is called by absolute path).
Prints the archive SHA-256 and the version name the hub will use.
"""
import hashlib
from pathlib import Path
import re
import sys

source, output = Path(sys.argv[1]), Path(sys.argv[2])
names = sorted(p.name for p in source.glob("*.lua") if p.name != "radio-start.lua")
assert "service.lua" in names, "service.lua missing"
parts = [b"CTAPP1\n"]
for name in names:
    assert re.fullmatch(r"[a-z][a-z0-9_-]*\.lua", name) and len(name) <= 64, name
    data = (source / name).read_bytes()
    assert len(data) <= 1024 * 1024, name
    parts.append(f"F {name} {len(data)} {hashlib.sha256(data).hexdigest()}\n".encode() + data)
parts.append(b"END\n")
archive = b"".join(parts)
assert len(archive) <= 4 * 1024 * 1024
output.write_bytes(archive)
digest = hashlib.sha256(archive).hexdigest()
print(f"CTAPP sha256={digest} version=v-{digest[:12]} files={len(names)} bytes={len(archive)}")
