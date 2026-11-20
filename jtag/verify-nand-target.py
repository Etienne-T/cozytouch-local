"""Second complete NAND read, verified with on-target SHA-256 per chunk.

No second raw image is synthesized. Evidence consists of target digests,
register checks and CRCs compared to the first acquired image's manifest.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path('<CHEMIN_LOCAL>')
spec = importlib.util.spec_from_file_location('backup', ROOT/'backup-nand-sparse.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
OUT = module.OUT
OCD = module.OCD
HASH_ENTRY = 0x00300000
HASH_DONE = 0x00300008


def target_hash(ocd, address, length, output):
    ocd.cmd(f'reg r0 {address}')
    ocd.cmd(f'reg r1 {length}')
    ocd.cmd('reg r2 0x20301000')
    ocd.cmd(f'resume {HASH_ENTRY}')
    ocd.cmd('wait_halt 60000')
    assert ocd.reg('pc') == HASH_DONE
    assert not output.exists()
    ocd.cmd(f'dump_image {output} 0x20301000 32')
    digest = output.read_bytes()
    assert len(digest) == 32
    return digest.hex()


def read_chunk(ocd, first):
    ocd.cmd('reg r3 0x20000000')
    ocd.cmd(f'reg r4 {first}')
    ocd.cmd('reg r5 1024')
    ocd.cmd('resume 0x00307000')
    ocd.cmd('wait_halt 50000')
    for reg, expected in {'pc':module.DONE,'r3':0x20210000,'r4':first+1024,'r5':0}.items():
        assert ocd.reg(reg) == expected, reg
    return f'{ocd.reg("sp_svc"):08x}'


def validate(ocd):
    cases = [b'', b'abc', b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq']
    cases += [bytes(range(n)) for n in [55,63,64,65,127,128,129]]
    results=[]
    for i,data in enumerate(cases):
        path=OUT/f'sha-test-{i}.input'
        path.write_bytes(data if data else b'\0')
        ocd.cmd(f'load_image {path} 0x20310000 bin')
        actual=target_hash(ocd,0x20310000,len(data),OUT/f'sha-test-{i}.digest')
        expected=hashlib.sha256(data).hexdigest()
        assert actual==expected, (i,actual,expected)
        results.append({'test':i,'bytes':len(data),'sha256':actual,'match':True})
    records=[json.loads(x) for x in (OUT/'pass-A/manifest.jsonl').read_text().splitlines()]
    baseline=records[40]  # a filled 2-MiB NAND range, already acquired
    crc=read_chunk(ocd,baseline['first_page'])
    actual=target_hash(ocd,0x20000000,2162688,OUT/'sha-test-nand.digest')
    assert actual==baseline['sha256'] and crc==baseline['crc32']
    results.append({'test':'nand','first_page':baseline['first_page'],
                    'bytes':2162688,'sha256':actual,'crc32':crc,'match':True})
    (OUT/'sha256-target-validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({'target_tests_passed':len(results)}),flush=True)


def verify(ocd):
    baseline=[json.loads(x) for x in (OUT/'pass-A/manifest.jsonl').read_text().splitlines()]
    assert len(baseline)==64
    directory=OUT/'verification-B'
    directory.mkdir(exist_ok=True)
    manifest=OUT/'verification-B.jsonl'
    old=[json.loads(x) for x in manifest.read_text().splitlines()] if manifest.exists() else []
    assert [x['first_page'] for x in old]==list(range(0,len(old)*1024,1024))
    began=time.monotonic()
    with manifest.open('a') as log:
        for i,record in enumerate(baseline):
            first=record['first_page']
            assert first==i*1024
            if i<len(old):
                assert old[i]['sha256_target']==record['sha256']
                continue
            for attempt in range(1,4):
                output=directory/f'pages-{first:05d}-attempt-{attempt}.sha256'
                if output.exists():
                    output=directory/f'pages-{first:05d}-attempt-{attempt}-{time.time_ns()}.sha256'
                crc=read_chunk(ocd,first)
                actual=target_hash(ocd,0x20000000,2162688,output)
                if actual==record['sha256'] and crc==record['crc32']:
                    break
                print(json.dumps({'retry_page':first,'sha256_target':actual,'crc32_target':crc}),flush=True)
            else:
                raise RuntimeError(f'Independent NAND verification failed at page {first}')
            result={'pass':'B','first_page':first,'pages':1024,'bytes':2162688,
                    'sha256_target':actual,'sha256_A':record['sha256'],
                    'crc32_target':crc,'independent_nand_read':True,'match':True,
                    'elapsed_s':round(time.monotonic()-began,1)}
            line=json.dumps(result)
            log.write(line+'\n');log.flush();print(line,flush=True)
    print(json.dumps({'verification_complete':True,'pages':65536,'raw_bytes':138412032}),flush=True)


ocd=OCD()
try:
    if sys.argv[1:] == ['validate']:
        validate(ocd)
    elif sys.argv[1:] == ['verify']:
        verify(ocd)
    else:
        raise SystemExit('Use validate or verify')
finally:
    ocd.sock.close()
