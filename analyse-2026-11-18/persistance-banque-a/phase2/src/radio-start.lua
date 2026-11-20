-- Remise en route radio au lancement du service, une seule fois par lancement.
-- Reprend la sequence OEM serial_rf (PA2=0, PA3=1, PA5=BOOT0=0, PA6=BOOT1=0, 35 ms, PA2=1),
-- reduite a PA2 : PA3, PA5 et PA6 sont deja a ces niveaux de facon passive sur la carte.
-- Logique identique a analyse-2026-11-19/boot-banque-a/impulsion-pa2.lua, validee sur le hub
-- le 19 novembre 2026 (STACK_START, revision 2.4.2, deux READ, HEALTH_OK).
-- Refuse d'agir si PA2..PA6 ne sont pas libres, en entree et a 11100. Sortie 0 seulement si
-- l'impulsion est faite et l'etat passif retrouve.
local ffi = require('ffi')
ffi.cdef[[
int open(const char *path, int flags);
int close(int fd);
int ioctl(int fd, unsigned long req, void *arg);
int usleep(unsigned int usec);
typedef struct { uint32_t line_offset; uint32_t flags; char name[32]; char consumer[32]; } gpioline_info;
typedef struct { uint32_t lineoffsets[64]; uint32_t flags; uint8_t default_values[64];
                 char consumer_label[32]; uint32_t lines; int fd; } gpiohandle_request;
typedef struct { uint8_t values[64]; } gpiohandle_data;
typedef struct { uint32_t flags; uint8_t default_values[64]; uint32_t padding[4]; } gpiohandle_config;
]]
local GET_LINEINFO, GET_LINEHANDLE = 0xC048B402, 0xC16CB403
local GET_VALUES, SET_VALUES, SET_CONFIG = 0xC040B408, 0xC040B409, 0xC054B40A
local INPUT, OUTPUT = 1, 2
local PASSIVE = '11100'
local C = ffi.C

local function levels(chip)
  for off = 2, 6 do
    local info = ffi.new('gpioline_info'); info.line_offset = off
    assert(C.ioctl(chip, GET_LINEINFO, info) == 0, 'RADIO_LINEINFO_FAILED')
    assert(info.flags == 0, 'RADIO_LINE_NOT_FREE_INPUT')
  end
  local req = ffi.new('gpiohandle_request')
  for i = 0, 4 do req.lineoffsets[i] = i + 2 end
  req.flags, req.lines = INPUT, 5
  ffi.copy(req.consumer_label, 'ct-read')
  assert(C.ioctl(chip, GET_LINEHANDLE, req) == 0, 'RADIO_LINEHANDLE_FAILED')
  local d = ffi.new('gpiohandle_data')
  local got = C.ioctl(req.fd, GET_VALUES, d) == 0
  C.close(req.fd)
  assert(got, 'RADIO_GET_FAILED')
  return string.format('%d%d%d%d%d', d.values[0], d.values[1], d.values[2], d.values[3], d.values[4])
end

local chip = C.open('/dev/gpiochip0', 2)
if chip < 0 then print('RADIO_PULSE refused=open'); os.exit(1) end
local ok, before = pcall(levels, chip)
if not ok or before ~= PASSIVE then
  C.close(chip)
  print('RADIO_PULSE refused=passive_state')
  os.exit(1)
end

local req = ffi.new('gpiohandle_request')
req.lineoffsets[0], req.flags, req.lines, req.default_values[0] = 2, OUTPUT, 1, 0
ffi.copy(req.consumer_label, 'ct-pwr')
if C.ioctl(chip, GET_LINEHANDLE, req) ~= 0 then
  C.close(chip)
  print('RADIO_PULSE refused=request')
  os.exit(1)
end
-- PA2 = 0 depuis la demande de ligne
C.usleep(35000)
local high = ffi.new('gpiohandle_data'); high.values[0] = 1
local ok_high = C.ioctl(req.fd, SET_VALUES, high) == 0
local cfg = ffi.new('gpiohandle_config'); cfg.flags = INPUT
local ok_input = C.ioctl(req.fd, SET_CONFIG, cfg) == 0
C.close(req.fd)

local ok_after, after = pcall(levels, chip)
C.close(chip)
local done = ok_high and ok_input and ok_after and after == PASSIVE
print('RADIO_PULSE low_ms=35 restored=' .. tostring(done))
os.exit(done and 0 or 1)
