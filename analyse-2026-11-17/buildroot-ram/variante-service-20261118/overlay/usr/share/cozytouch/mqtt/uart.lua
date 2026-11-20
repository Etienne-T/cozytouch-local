-- Derived module: tested codec and ABI preserved; no automatic CLI.
-- Autonomous warm-session reader. No OEM/cloud modules; no reset/init/discovery.
-- Hardware CLI: luajit cozytouch-read.lua --read-two /run/ct/.../targets.private.conf
-- Offline CLI: --selftest | --check-config FILE | --abi-only
local M={}
local function xor(a,b)
  local n,p=0,1
  for _=1,8 do if a%2~=b%2 then n=n+p end a=math.floor(a/2) b=math.floor(b/2) p=p*2 end
  return n
end
function M.crc(s)
  local c=0
  for i=1,#s do c=xor(c,s:byte(i)); for _=1,8 do local hi=c>=128; c=(c*2)%256; if hi then c=xor(c,7) end end end
  return c
end
local function unhex(s,n)
  assert(type(s)=='string' and #s==n*2 and s:match('^[0-9a-f]+$'),'invalid private field')
  return (s:gsub('..',function(b) return string.char(tonumber(b,16)) end))
end
local function be(s,i,n) local v=0; for j=i,i+n-1 do v=v*256+s:byte(j) end return v end
local function frame(id,p) local n=#p+1; return string.char(2,math.floor(id/256),id%256,math.floor(n/256),n%256)..p..string.char(M.crc(p),3) end
local field_sizes={3,3,1,2,3,1,1,2,1,1,16}
function M.config(text)
  assert(type(text)=='string' and #text<2048,'config size')
  local out={}; local seen={}
  for line in text:gmatch('[^\r\n]+') do
    local cells={}; for c in (line..'|'):gmatch('(.-)|') do cells[#cells+1]=c end
    assert(#cells==12 and (cells[1]=='CETHI' or cells[1]=='IC3') and not seen[cells[1]],'config targets')
    local t={label=cells[1],fields={}}
    for i,n in ipairs(field_sizes) do t.fields[i]=unhex(cells[i+1],n) end
    t.source=t.fields[1]; t.target=t.fields[2]
    assert(t.source~=t.target and t.target~=string.rep('\0',3),'invalid node context')
    assert(t.fields[11]~=string.rep('\0',16),'empty key context')
    seen[t.label]=true;out[#out+1]=t
  end
  assert(#out==2 and out[1].label=='CETHI' and out[2].label=='IC3' and out[1].target~=out[2].target,'exactly two ordered distinct targets required')
  return out
end
function M.request(t)
  -- Named context fields follow FrameDefinition.lua, not RF replay bytes.
  -- Only ACTIVATE_STATUS_REQUEST, MAIN_INFO, zero functional parameters.
  local p=table.concat(t.fields)..string.char(1,3,3,0,0)
  assert(#p==39 and p:byte(35)==1 and p:sub(36)==string.char(3,3,0,0),'READ allowlist')
  return frame(0x0100,p)
end
function M.parser()
  local p={buf='',rejected=0,noise=0,since=nil}
  function p:feed(chunk,now)
    assert(#chunk<=4096,'oversized input chunk')
    self.buf=self.buf..chunk
    local out={}
    while #self.buf>0 do
      local at=self.buf:find(string.char(2),1,true)
      if not at then self.noise=self.noise+#self.buf;self.buf='';self.since=nil;break end
      if at>1 then self.noise=self.noise+at-1;self.buf=self.buf:sub(at);self.since=nil end
      if not self.since then self.since=now end
      local discard=false
      if #self.buf>=5 then
        local n=be(self.buf,4,2)
        if n<1 or n>128 then discard=true
        elseif #self.buf>=n+6 then
          local payload=self.buf:sub(6,n+4)
          if self.buf:byte(n+6)~=3 or self.buf:byte(n+5)~=M.crc(payload) then discard=true
          else
            out[#out+1]={id=be(self.buf,2,2),payload=payload}
            self.buf=self.buf:sub(n+7);self.since=nil
          end
        elseif now-self.since>=0.25 then discard=true else break end
      elseif now-self.since>=0.25 then discard=true else break end
      if discard then self.rejected=self.rejected+1;self.buf=self.buf:sub(2);self.since=nil end
    end
    assert(#self.buf<=134,'parser bound')
    return out
  end
  return p
end
function M.transaction(target,start,deadline)
  local t={target=target,start=start,deadline=deadline,done=false,ignored=0}
  function t:finish(status,data) if self.done then return false end;self.done=true;self.status=status;self.data=data;return true end
  function t:tick(now) if not self.done and now>=self.deadline then self:finish('TIMEOUT') end end
  function t:accept(f,now)
    self:tick(now);if self.done then return false end
    if f.id==0x050e then self:finish('RESET_CONTEXT_LOST');return true end
    local p=f.payload
    if f.id~=0x010d or #p<16 or p:sub(5,7)~=target.target or p:sub(8,10)~=target.source then self.ignored=self.ignored+1;return false end
    -- Only IO, 2-way ACTIVATE_ACK; IO control flag is bit 5 (MSB schema).
    if p:byte(11)~=0 or math.floor(p:byte(12)/32)%2~=0 or p:byte(14)~=4 then self.ignored=self.ignored+1;return false end
    local basic,detailed=p:byte(15),p:byte(16)
    local cs,es=math.floor(basic/8),basic%8
    local info={command_status=cs,execute_status=es,detailed_status=detailed,rssi=be(p,1,4)}
    if info.rssi>=2147483648 then info.rssi=info.rssi-4294967296 end
    if cs~=0 or es==0 or es==1 or detailed~=0 then self:finish('DEVICE_ERROR',info);return true end
    if es~=5 then self.ignored=self.ignored+1;return false end
    -- Context-dependent ACK: 10 bytes MAIN_INFO then FPI1,FPI2 (both zero).
    if #p~=28 or p:byte(27)~=0 or p:byte(28)~=0 then self:finish('UNSUPPORTED_ACK_SHAPE',info);return true end
    info.target_raw=be(p,17,2);info.current_raw=be(p,19,2);info.remaining_time_raw=be(p,21,2);info.origin=p:byte(26)
    -- Bytes 23..25 are the private last-master address and are never logged.
    self:finish('DONE',info);return true
  end
  return t
end
function M.selftest()
  assert(M.crc('123456789')==0xf4,'CRC known vector')
  local f1={'010203','040506','00','0c01','000000','0c','00','0000','00','07',string.rep('11',16)}
  local f2={'010203','070809','00','0d01','000000','0c','00','0000','00','07',string.rep('11',16)}
  local text='CETHI|'..table.concat(f1,'|')..'\nIC3|'..table.concat(f2,'|')..'\n'
  local targets=M.config(text);local tx=M.request(targets[1]);assert(#tx==46 and tx:byte(40)==1,'TX shape')
  local p=string.char(255,255,255,160)..targets[1].target..targets[1].source..string.char(0,150,0,4,5,0,200,0,200,0,0,0,1,2,3,1,0,0)
  local rx=frame(0x010d,p);assert(#p==28,'fixture')
  for cut=0,#rx do
    local parser=M.parser();local a=parser:feed(rx:sub(1,cut),0);local b=parser:feed(rx:sub(cut+1),0.01)
    assert(#a+#b==1 and #parser.buf==0,'fragmentation')
  end
  local parser=M.parser(); local got={}
  for i=1,#rx do for _,f in ipairs(parser:feed(rx:sub(i,i),i/1000)) do got[#got+1]=f end end
  assert(#got==1 and got[1].payload==p,'byte fragmentation')
  local bad=rx:sub(1,-3)..string.char((rx:byte(-2)+1)%256,3)
  parser=M.parser();assert(#parser:feed('noise'..bad..rx..rx,0)==2 and parser.rejected>=1,'CRC resync and concatenation')
  parser=M.parser();assert(#parser:feed(string.char(2,1,13,255,255)..rx,0)==1 and parser.rejected>=1,'oversized length')
  parser=M.parser();assert(#parser:feed(string.char(2,1,13,0,100)..rx,0)==0,'wait partial');assert(#parser:feed('',0.3)==1,'partial deadline resync')
  local t=M.transaction(targets[1],0,8);assert(t:accept({id=0x010d,payload=p},0.1) and t.status=='DONE' and t.data.target_raw==51200,'decode')
  assert(not t:accept({id=0x010d,payload=p},0.2),'single terminal')
  t=M.transaction(targets[2],0,8);assert(not t:accept({id=0x010d,payload=p},0.1) and not t.done,'wrong target');t:tick(8);assert(t.status=='TIMEOUT','timeout')
  t=M.transaction(targets[1],0,8);assert(not t:accept({id=0x010e,payload=p},0.1),'wrong callback')
  local wrong=p:sub(1,13)..string.char(3)..p:sub(15);assert(not t:accept({id=0x010d,payload=wrong},0.2),'wrong command')
  local err=p:sub(1,14)..string.char(3*8+5)..p:sub(16);assert(t:accept({id=0x010d,payload=err},0.3) and t.status=='DEVICE_ERROR','BAD_MAC terminal')
  t=M.transaction(targets[1],0,8);assert(t:accept({id=0x050e,payload=''},0.1) and t.status=='RESET_CONTEXT_LOST','reset')
  t=M.transaction(targets[1],0,8);assert(not t:accept({id=0x010d,payload=p},8) and t.status=='TIMEOUT','late valid ACK')
  assert(not pcall(M.config,text..text),'duplicate config rejection')
  assert(not pcall(M.config,text:gsub('11111111111111111111111111111111','00000000000000000000000000000000')),'zero key rejection')
  print('SELFTEST_OK crc_vector fragmentation_all_splits bytewise malformed_crc length_bound resync partial_deadline concat correlation wrong_command timeout late_ack single_terminal device_error reset config_allowlist')
end
local function ffi_setup()
  local ffi=require('ffi')
  ffi.cdef[[
    typedef struct { unsigned int iflag,oflag,cflag,lflag; unsigned char line; unsigned char cc[19]; } ct_termios;
    typedef struct { long sec,nsec; } ct_time;
    typedef struct { unsigned long ino; long off; unsigned short reclen; unsigned char type; char name[256]; } ct_dirent;
    void *opendir(const char *); ct_dirent *readdir(void *); int closedir(void *);
    long readlink(const char *,char *,unsigned long); int getpid(void);
    int open(const char*,int,...); int close(int); long read(int,void*,unsigned long);
    long write(int,const void*,unsigned long); int ioctl(int,unsigned long,...);
    int usleep(unsigned int); int clock_gettime(int,ct_time*); int flock(int,int);
  ]]
  assert(ffi.os=='Linux' and ffi.arch=='arm' and ffi.sizeof('long')==4,'ARM Linux ABI required')
  assert(ffi.sizeof('ct_termios')==36 and ffi.offsetof('ct_termios','cc')==17 and ffi.offsetof('ct_dirent','name')==11,'kernel ABI')
  return ffi,ffi.C
end
-- Service backend: owns UART until close; coordinator owns daemon supervision.
local abi_cache=nil
local function ensure_abi()
  if not abi_cache then abi_cache={ffi_setup()} end
  return abi_cache[1],abi_cache[2]
end
function M.check_abi() ensure_abi();return true end
function M.open_session(targets,now,absolute)
  local ffi,C=ensure_abi()
  local self={tty=-1,lock=-1,old=nil,old_valid=false,exclusive=false,parser=M.parser(),active=nil,index=0,ready=false}
  local function bounded() assert(now()<absolute,'UART whole-run deadline') end
  local function listdir(path)
    local dir=C.opendir(path);if dir==nil then return nil end
    local names={};while true do local e=C.readdir(dir);if e==nil then break end;local n=ffi.string(e.name);if n~='.' and n~='..' then names[#names+1]=n end end
    C.closedir(dir);return names
  end
  function self:noowners()
    local me=tostring(tonumber(C.getpid()));local link=ffi.new('char[4096]')
    for _,pid in ipairs(assert(listdir('/proc'),'proc scan')) do bounded();if pid:match('^%d+$') then
      local dir='/proc/'..pid..'/fd';local names=listdir(dir)
      if not names then local present=C.opendir('/proc/'..pid);if present~=nil then C.closedir(present);error('uninspectable live process') end
      else for _,fd in ipairs(names) do local n=tonumber(C.readlink(dir..'/'..fd,link,4096));if n>0 and ffi.string(link,n)=='/dev/ttyS1' and not(pid==me and tonumber(fd)==self.tty) then error('UART already owned') end end end
    end end
  end
  function self:close()
    local ok=true
    if self.tty>=0 then
      if self.old_valid and C.ioctl(self.tty,0x5402,self.old)~=0 then ok=false end
      if self.exclusive and C.ioctl(self.tty,0x540d,ffi.cast('void*',0))~=0 then ok=false end
      if C.close(self.tty)~=0 then ok=false end;self.tty=-1
    end
    if self.lock>=0 then C.close(self.lock);self.lock=-1 end
    print('UART_CLEANUP restored='..tostring(ok));io.stdout:flush();return ok
  end
  local ok,err=xpcall(function()
    self.lock=tonumber(C.open('/run/ct/autonomous-uart.lock',0x42,ffi.cast('int',384)))
    assert(self.lock>=0 and C.flock(self.lock,6)==0,'UART client lock')
    self:noowners();self.tty=tonumber(C.open('/dev/ttyS1',0x902));assert(self.tty>=0,'UART open')
    assert(C.ioctl(self.tty,0x540c,ffi.cast('void*',0))==0,'TIOCEXCL');self.exclusive=true;self:noowners()
    self.old=ffi.new('ct_termios[1]');assert(C.ioctl(self.tty,0x5401,self.old)==0,'TCGETS');self.old_valid=true
    local raw=ffi.new('ct_termios[1]');raw[0].cflag=0x18b2;raw[0].cc[5]=0;raw[0].cc[6]=0
    assert(C.ioctl(self.tty,0x5402,raw)==0,'TCSETS')
    local check=ffi.new('ct_termios[1]');assert(C.ioctl(self.tty,0x5401,check)==0 and tonumber(check[0].cflag)==0x18b2 and tonumber(check[0].iflag)==0 and tonumber(check[0].oflag)==0 and tonumber(check[0].lflag)==0,'raw UART verification')
  end,debug.traceback)
  if not ok then self:close();error(err,0) end
  local buf=ffi.new('char[4096]');self.quiet=now();self.drain_deadline=now()+1
  function self:receive()
    bounded();local n=tonumber(C.read(self.tty,buf,4096))
    if n>0 then self.last_bytes=now();return self.parser:feed(ffi.string(buf,n),now()) end
    if n<0 and ffi.errno()~=11 and ffi.errno()~=4 then error('UART read errno='..ffi.errno()) end
    return self.parser:feed('',now())
  end
  function self:start(index)
    bounded();assert(self.ready and not self.active,'UART not ready or busy');self:noowners()
    local target=assert(targets[index]);local packet=M.request(target)
    assert(#packet==46 and packet:sub(1,5)==string.char(2,1,0,0,40) and packet:sub(40,44)==string.char(1,3,3,0,0) and packet:byte(45)==M.crc(packet:sub(6,44)) and packet:byte(46)==3,'TX READ allowlist')
    self.active=M.transaction(target,now(),math.min(now()+8,absolute));self.index=index
    local off=0;local finish=now()+0.5
    while off<#packet do bounded();assert(now()<finish,'UART write deadline');local n=tonumber(C.write(self.tty,packet:sub(off+1),#packet-off))
      if n>0 then off=off+n elseif n<0 and ffi.errno()~=11 and ffi.errno()~=4 then error('UART write errno='..ffi.errno()) else C.usleep(1000) end
    end
    print('TX_READ target='..target.label..' parameter=65537');io.stdout:flush()
  end
  function self:step()
    local frames=self:receive()
    if not self.ready then
      if self.last_bytes then self.quiet=self.last_bytes;self.last_bytes=nil end
      for _,f in ipairs(frames) do assert(f.id~=0x050e,'reset during UART drain') end
      assert(now()<self.drain_deadline,'UART quiet deadline')
      if now()-self.quiet>=0.3 and #self.parser.buf==0 then self.ready=true;print('UART_READY warm_session=true') end
      return nil
    end
    for _,f in ipairs(frames) do
      assert(f.id~=0x050e,'STM32 reset: context lost, cold initialization not implemented')
      if self.active then self.active:accept(f,now()) end
    end
    if self.active then self.active:tick(now());if self.active.done then local result=self.active;self.active=nil;result.index=self.index;return result end end
    return nil
  end
  return self
end

return M
