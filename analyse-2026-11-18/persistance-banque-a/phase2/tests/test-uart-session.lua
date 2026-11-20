-- Exercise the packaged dispatcher and parser with a simulated clock and UART.
local directory, scenario = arg[1], arg[2]
package.path = directory .. '/?.lua;' .. package.path
local UART = require('uart')
local ffi = require('ffi')
local clock, incoming, sent = -1, '', {}
local C = {
  open = function() return 1 end,
  close = function() return 0 end,
  flock = function() return 0 end,
  ioctl = function(_, operation, buffer)
    if operation == 0x5401 then ffi.cast('uint32_t *', buffer)[2] = 0x18b2 end
    return 0
  end,
  read = function(_, buffer)
    if #incoming == 0 then ffi.errno(11); return -1 end
    local data = incoming
    incoming = ''
    ffi.copy(buffer, data, #data)
    return #data
  end,
  write = function(_, data, size)
    sent[#sent + 1] = {time = clock, kind = data:byte(42)}
    return size
  end,
}
for index = 1, math.huge do
  local name, prepare = debug.getupvalue(UART.open_session, index)
  assert(name, 'UART ABI upvalue missing')
  if name == 'ensure_abi' then
    -- Keep the real termios declarations while replacing the C I/O entry points.
    prepare()
    debug.setupvalue(UART.open_session, index, function() return ffi, C end)
    break
  end
end
package.loaded.config = {safe = {ct_uart_sole = function() return 0 end}}
os.execute = function(command)
  assert(command == 'luajit /usr/share/cozytouch/phase2/radio-start.lua')
  return 0
end

local function frame(id, payload)
  return string.char(2, math.floor(id / 256), id % 256, 0, #payload + 1)
    .. payload .. string.char(UART.crc(payload), 3)
end

local function status(target, marker, basic, detail, data)
  return frame(0x010d, '\255\255\255\160' .. target.target .. target.source
    .. string.char(0, marker, 0, 4, basic, detail) .. data)
end

local context = '|00|0c01|000000|0c|00|0000|00|07|' .. string.rep('11', 16) .. '\n'
local targets = UART.config('CETHI|010203|040506' .. context .. 'IC3|010203|070809' .. context)
local uart = UART.open_session(targets, function() return clock end, '/simulated')
local function step(time, bytes)
  assert(time >= clock, 'clock moved backwards')
  clock, incoming = time, bytes or ''
  return uart:step(false, true)
end
step(-1, frame(0x0403, '\4'))
step(-0.5)
step(-0.25, frame(0x0500, '\0v2.4.2'))
assert(uart.ready)
sent = {}

local max = status(targets[1], 0x8e, 5, 0, '\130\235\0\0')
local min = status(targets[1], 0x8e, 5, 0, '\114\131\0\0')
local function start_limits()
  clock = 0
  uart:start_limits()
  assert(not step(0) and #sent == 1 and sent[1].kind == 7)
end
local function first_two()
  start_limits()
  step(0.125, max)
  step(1)
  step(1.125, min)
end
local function nominal()
  first_two()
  step(2)
  step(2.125, max)
end
local function rejected(time, reason)
  local result = assert(step(time), 'phase must finish once quiet')
  assert(result.failed == reason, 'unexpected result: ' .. tostring(result.failed))
end

if scenario == 'regular' or scenario == 'regular-after' then
  if scenario == 'regular-after' then
    nominal()
    assert(not assert(step(4.125)).failed)
  end
  local checks = {
    {2, 0x96, 8, 9, '', 'DEVICE_ERROR'},
    {2, 0x96, 8, 9, string.rep('\0', 4), 'DEVICE_ERROR'},
    {2, 0xd6, 5, 0, string.rep('\0', 12), 'DONE'},
    {1, 0x96, 8, 9, string.rep('\0', 12), 'DEVICE_ERROR'},
    {2, 0x96, 8, 9, string.rep('\0', 12), 'DEVICE_ERROR'},
    {1, 0x96, 5, 0, string.rep('\0', 11) .. '\1', 'UNSUPPORTED_ACK_SHAPE'},
    {1, 0x8e, 5, 0, '\130\235\0\0', 'UNSUPPORTED_ACK_SHAPE'},
  }
  for _, check in ipairs(checks) do
    local index, marker, basic, detail, data, expected = unpack(check)
    for _, later in ipairs({false, true}) do
      uart:start(index)
      local reply = status(targets[index], marker, basic, detail, data)
      if later then reply = reply .. status(targets[index], 0x96, 5, 0, string.rep('\0', 12)) end
      local time = clock + 0.125
      local result = step(time, reply) or step(clock + 8)
      assert(result and result.status == expected, ('regular %d/%02x/%d followup=%s expected=%s actual=%s')
        :format(index, marker, #data + 16, tostring(later), expected, result and result.status or 'pending'))
      assert(clock == time, 'regular reply did not terminate immediately')
    end
  end
elseif scenario == 'partial-guard' then
  nominal()
  step(4.075, max:sub(1, 12))
  assert(not step(4.125), 'guard ended with ' .. #uart.parser.buf .. ' bytes buffered')
  step(4.175, max:sub(13))
  assert(not step(6.174), 'guard ended before two seconds of quiet')
  rejected(6.175, 'UNEXPECTED_PARTIAL')
elseif scenario == 'late-max1' then
  first_two()
  assert(not step(1.95, max:sub(1, 12)))
  step(2)
  step(2.075, max:sub(13))
  local result = assert(step(4.075))
  local values = result.values
  assert(result.failed == 'UNEXPECTED_PARTIAL' and #sent == 2,
    ('late MAX1 substituted for MAX2: requests=%d values=%s/%s/%s')
      :format(#sent, tostring(values[1]), tostring(values[2]), tostring(values[3])))
elseif scenario == 'identical-max' then
  first_two()
  step(2)
  -- Same bytes as MAX1, wholly within MAX2's window. Source is indistinguishable.
  step(2.125, max)
  local result = assert(step(4.125))
  assert(not result.failed and result.values[1] == 33515 and result.values[2] == 29315
    and result.values[3] == 33515)
elseif scenario == 'crc' or scenario == 'private-ack' then
  nominal()
  local bad = scenario == 'crc' and max:sub(1, -3) .. string.char((max:byte(-2) + 1) % 256, 3)
    or frame(0x040c, '')
  step(2.25, bad)
  rejected(4.25, scenario == 'crc' and 'UART_PARSE_REJECTED' or 'UNEXPECTED_ACK')
elseif scenario == 'spacing' then
  start_limits()
  step(0.125, max)
  step(0.999)
  assert(#sent == 1)
  step(1)
  assert(#sent == 2 and sent[2].kind == 6)
  step(1.75, min)
  step(2.249)
  assert(#sent == 2)
  step(2.25)
  assert(#sent == 3 and sent[3].kind == 7)
elseif scenario == 'timeout' then
  start_limits()
  step(1)
  step(1.125, max)
  assert(not step(11.124), 'timeout guard did not extend after UART input')
  rejected(11.125, 'TIMEOUT')
  assert(#sent == 1)
else
  error('unknown scenario: ' .. scenario)
end
assert(uart:close())
print('UART_SESSION_OK ' .. scenario)
