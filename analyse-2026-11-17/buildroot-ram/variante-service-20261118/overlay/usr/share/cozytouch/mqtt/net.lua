-- Linux FFI TCP transport. Numeric private IPv4 only, no DNS/account access.
local ffi=require('ffi')
require('uart').check_abi() -- Declares the shared clock once; opens no UART.
ffi.cdef[[
typedef struct { unsigned short family,port; unsigned char addr[4]; unsigned char zero[8]; } ct_mqtt_sockaddr;
typedef struct { int fd; short events,revents; } ct_mqtt_pollfd;
typedef struct { long sec,nsec; } ct_mqtt_time;
int socket(int,int,int); int connect(int,const void*,unsigned int); int close(int);
long send(int,const void*,unsigned long,int); long recv(int,void*,unsigned long,int);
int poll(ct_mqtt_pollfd*,unsigned long,int); int getsockopt(int,int,int,void*,unsigned int*);
int inet_pton(int,const char*,void*); unsigned short htons(unsigned short);
int usleep(unsigned int); int getpid(void);
typedef union { unsigned long alignment; unsigned char bytes[128]; } ct_mqtt_sigset;
int sigemptyset(ct_mqtt_sigset*); int sigaddset(ct_mqtt_sigset*,int);
int sigprocmask(int,const ct_mqtt_sigset*,ct_mqtt_sigset*);
int sigtimedwait(const ct_mqtt_sigset*,void*,const ct_mqtt_time*);
]]
local C=ffi.C;local M={}
assert(ffi.os=='Linux','Linux socket ABI required')
assert(ffi.sizeof('ct_mqtt_sockaddr')==16 and ffi.sizeof('ct_mqtt_pollfd')==8,'socket ABI')
function M.now() local ts=ffi.new('ct_time[1]');assert(C.clock_gettime(1,ts)==0,'clock_gettime');return tonumber(ts[0].sec)+tonumber(ts[0].nsec)/1e9 end
function M.pause() C.usleep(10000) end
function M.pid() return tonumber(C.getpid()) end
function M.stop_signals()
  -- Consume blocked TERM/INT synchronously. No Lua code runs in an async
  -- signal handler; the normal service path can restore termios safely.
  local set=ffi.new('ct_mqtt_sigset[1]');local previous=ffi.new('ct_mqtt_sigset[1]')
  assert(C.sigemptyset(set)==0 and C.sigaddset(set,2)==0 and C.sigaddset(set,15)==0 and C.sigprocmask(0,set,previous)==0,'signal mask')
  local zero=ffi.new('ct_mqtt_time[1]')
  return {
    poll=function() local n=C.sigtimedwait(set,nil,zero);if n==2 or n==15 then return true end;assert(n<0 and (ffi.errno()==11 or ffi.errno()==4),'signal wait');return false end,
    restore=function() return C.sigprocmask(2,previous,nil)==0 end,
  }
end
function M.transport(config)
  local t={fd=-1};local buf=ffi.new('char[4096]')
  function t:close() if self.fd>=0 then C.close(self.fd);self.fd=-1 end end
  function t:open()
    assert(self.fd<0,'socket already open');self.fd=tonumber(C.socket(2,0x80801,0));assert(self.fd>=0,'socket errno='..ffi.errno()) -- stream|nonblock|cloexec
    local addr=ffi.new('ct_mqtt_sockaddr[1]');addr[0].family=2;addr[0].port=C.htons(config.broker_port)
    assert(C.inet_pton(2,config.broker_ipv4,addr[0].addr)==1,'numeric IPv4')
    local result=C.connect(self.fd,addr,16);assert(result==0 or ffi.errno()==115,'connect errno='..ffi.errno())
  end
  function t:connected()
    assert(self.fd>=0,'socket closed');local p=ffi.new('ct_mqtt_pollfd[1]');p[0].fd=self.fd;p[0].events=4
    local result=C.poll(p,1,0);assert(result>=0 or ffi.errno()==4,'poll errno='..ffi.errno());if result<=0 then return false end
    local err=ffi.new('int[1]');local size=ffi.new('unsigned int[1]',4)
    assert(C.getsockopt(self.fd,1,4,err,size)==0,'getsockopt errno='..ffi.errno());assert(err[0]==0,'connect SO_ERROR='..tonumber(err[0])..' poll_revents='..tonumber(p[0].revents));return true
  end
  function t:write(data)
    local n=tonumber(C.send(self.fd,data,#data,0x4000)) -- MSG_NOSIGNAL
    if n<0 and (ffi.errno()==11 or ffi.errno()==4) then return 0 end
    assert(n>=0,'socket send errno='..ffi.errno());return n
  end
  function t:read()
    local n=tonumber(C.recv(self.fd,buf,4096,0));if n<0 and (ffi.errno()==11 or ffi.errno()==4) then return nil end
    assert(n~=0,'socket EOF');assert(n>0,'socket receive errno='..ffi.errno());return ffi.string(buf,n)
  end
  return t
end
return M
