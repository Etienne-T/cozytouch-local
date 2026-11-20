"""Stream a stable Pi evidence directory, verify tar-stream SHA, compress locally."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import sys

root=Path(sys.argv[1])
dest=root/'source-pi.tar.gz'
temp=root/'source-pi.partial.tar.gz'
assert not dest.exists() and not temp.exists()
ssh=['ssh','-i','<CHEMIN_LOCAL>',
     '-o','BatchMode=yes','-o','ConnectTimeout=10','<UTILISATEUR_ADMIN>@<IP_ADMIN>']
command="bash -o pipefail -c 'tar -C \"<CHEMIN_LOCAL>\" -cf - cozytouch-jtag | tee >(sha256sum > \"<CHEMIN_LOCAL>\")'"
digest=hashlib.sha256()
count=0
proc=subprocess.Popen(ssh+[command],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
with temp.open('xb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',compresslevel=1,mtime=0) as out:
    while True:
        data=proc.stdout.read(1048576)
        if not data:
            break
        digest.update(data);count+=len(data);out.write(data)
errors=proc.stderr.read().decode(errors='replace')
if proc.wait()!=0:
    raise RuntimeError(errors)
remote=subprocess.check_output(ssh+['cat "<CHEMIN_LOCAL>"'],text=True).split()[0]
assert remote==digest.hexdigest(), 'Tar stream checksum mismatch'
temp.rename(dest)
compressed=hashlib.sha256(dest.read_bytes()).hexdigest()
receipt={'tar_bytes':count,'tar_sha256_local':digest.hexdigest(),
         'tar_sha256_pi':remote,'source_stream_verified':True,
         'gzip_bytes':dest.stat().st_size,'gzip_sha256':compressed}
(root/'source-archive-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
