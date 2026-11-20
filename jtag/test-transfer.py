import importlib.util
from pathlib import Path
import json
import zlib
spec = importlib.util.spec_from_file_location('backup', '<CHEMIN_LOCAL>')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ocd = module.OCD()
try:
    ocd.cmd('adapter speed 3000')
    assert ocd.reg('pc') == module.DONE
    expected = ocd.reg('sp_svc')
    dest = module.OUT/'buffer-speed3000.raw'
    assert not dest.exists()
    ocd.cmd(f'dump_image {dest} 0x20000000 2162688')
    data = dest.read_bytes()
    actual = zlib.crc32(data)
    record = {'target_crc32': f'{expected:08x}', 'transfer_crc32': f'{actual:08x}',
              'bytes': len(data), 'match': len(data) == 2162688 and actual == expected}
    if not record['match']:
        ocd.cmd('adapter speed 2000')
    (module.OUT/'transfer-speed3000.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record), flush=True)
finally:
    ocd.sock.close()
