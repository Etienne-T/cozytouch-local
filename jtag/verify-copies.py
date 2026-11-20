"""Verify SHA256SUMS in the given backup directory (read only)."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(sys.argv[1])
checked = []
for line in (root/'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    path = root / name
    assert path.resolve().is_relative_to(root.resolve())
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            digest.update(chunk)
    assert digest.hexdigest() == expected, name
    checked.append({'file': name, 'bytes': path.stat().st_size, 'sha256': expected})
print(json.dumps({'verified': True, 'files': checked}, indent=2))
