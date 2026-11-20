local ffi = require('ffi')
ffi.cdef[[
int ct_read_file(const char *, const char *, char *, int);
int ct_uart_sole(const char *, int);
]]
local safe = ffi.load('/usr/lib/libct-safe.so')
local M = { safe = safe }

function M.read(directory, name, max)
  local buffer = ffi.new('char[?]', max + 1)
  local size = safe.ct_read_file(directory, name, buffer, max + 1)
  assert(size > 0 and size <= max, 'private file rejected')
  return ffi.string(buffer, size)
end

local function ipv4(value)
  assert(value, 'missing IPv4')
  local a, b, c, d = value:match('^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  a, b, c, d = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
  assert(a and a <= 255 and b <= 255 and c <= 255 and d <= 255
    and value == table.concat({a, b, c, d}, '.'), 'noncanonical IPv4')
  assert(a == 10 or (a == 172 and b >= 16 and b <= 31) or (a == 192 and b == 168), 'private IPv4 required')
  return ((a * 256 + b) * 256 + c) * 256 + d
end

local function integer(value, low, high)
  assert(value and value:match('^%d+$'), 'invalid number')
  local number = tonumber(value)
  assert(number >= low and number <= high and tostring(number) == value, 'numeric bound')
  return number
end

function M.parse(text)
  local config = {}
  local keys = {
    broker_ipv4 = true, broker_port = true, mqtt_username = true, mqtt_password = true,
    client_id = true, lan_ipv4 = true, lan_prefix = true, admin_ipv4 = true, interval_seconds = true
  }
  for line in text:gmatch('[^\r\n]+') do
    if line:sub(1, 1) ~= '#' then
      local key, value = line:match('^([a-z][a-z0-9_]*)=(.+)$')
      assert(keys[key] and not config[key] and not value:find('[%z\1-\31\127]'), 'configuration field')
      config[key] = value
    end
  end
  for key in pairs(keys) do
    assert(config[key], 'missing required configuration field')
  end
  local address = ipv4(config.lan_ipv4)
  local broker = ipv4(config.broker_ipv4)
  local admin = ipv4(config.admin_ipv4)
  config.lan_prefix = integer(config.lan_prefix, 8, 30)
  local block = 2 ^ (32 - config.lan_prefix)
  for _, host in ipairs({ address, broker, admin }) do
    assert(math.floor(host / block) == math.floor(address / block)
      and host % block > 0 and host % block < block - 1, 'local hosts only')
  end
  assert(address ~= broker and address ~= admin, 'distinct local peers required')
  config.broker_port = integer(config.broker_port, 1, 65535)
  config.interval_seconds = integer(config.interval_seconds, 30, 3600)
  assert(#config.mqtt_username <= 128 and not config.mqtt_username:find('[\128-\255]')
    and #config.mqtt_password <= 256, 'MQTT credential bounds')
  assert(#config.client_id <= 48 and config.client_id:match('^[A-Za-z0-9_-]+$'), 'MQTT identifier syntax')
  config.topic_prefix = 'cozytouch/' .. config.client_id
  config.state_topics = {config.topic_prefix .. '/cethi/state', config.topic_prefix .. '/ic3/state'}
  -- Device-based discovery (one config per device). The legacy per-entity topics of the first
  -- version are cleared with an empty retained payload at each start.
  config.discovery_topics = {
    'homeassistant/device/' .. config.client_id .. '_cethi/config',
    'homeassistant/device/' .. config.client_id .. '_ic3/config'
  }
  config.legacy_topics = {
    'homeassistant/sensor/' .. config.client_id .. '/cethi/config',
    'homeassistant/sensor/' .. config.client_id .. '/ic3/config'
  }
  return config
end

return M
