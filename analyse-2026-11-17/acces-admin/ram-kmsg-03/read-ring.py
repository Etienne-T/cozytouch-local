import socket,json,sys,time,struct,os
from pathlib import Path
os.umask(0o077)
out=Path(sys.argv[1]);out.mkdir(mode=0o700,exist_ok=False)
sock=socket.create_connection(('127.0.0.1',6666),timeout=8);sock.settimeout(30)
def cmd(c):
    sock.sendall(('set rc [catch {'+c+'} result]; format "RC=%d\\n%s" $rc $result').encode()+b'\x1a')
    b=b''
    while b'\x1a' not in b:
        p=sock.recv(65536)
        if not p:raise RuntimeError('closed')
        b+=p
    head,_,body=b.split(b'\x1a')[0].decode().partition('\n')
    if head!='RC=0':raise RuntimeError(head+' '+body)
    return body
def rd(addr,width,n):
    return [int(v,0) for v in cmd(f'read_memory {addr:#x} {width} {n} phys').strip().strip('{}').split()]
r={};halted=False;start=time.monotonic()
try:
    cmd('halt 10000');halted=True
    size,ptr=rd(0x205c8980,32,2)
    r.update(size=size,pointer=hex(ptr),reset_status=hex(rd(0xfffffe04,32,1)[0]))
    seq=rd(0x205e8c08,32,6)
    r.update(first_seq=seq[0]+(seq[1]<<32),next_seq=seq[2]+(seq[3]<<32),first_idx=seq[4],next_idx=seq[5])
    assert 1024<=size<=1024*1024 and 0xc0000000<=ptr<=0xc8000000-size
    words=[]
    for off in range(0,size,1024):words+=rd(ptr-0xa0000000+off,32,min(1024,size-off)//4)
    (out/'ring.bin').write_bytes(struct.pack('<'+'I'*len(words),*words))
finally:
    if halted:r['resume']=cmd('resume')
    sock.close();r['elapsed_seconds']=time.monotonic()-start
    (out/'metadata.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
