-- Run with LuaJIT and lua-cjson: luajit tests/test-discovery.lua src
-- Capture the service's retained publications with network and UART stubs.
local directory = assert(arg[1], 'application Lua directory required')
package.path = directory .. '/?.lua;' .. package.path
local json = require('cjson')
local ffi = require('ffi')
local load = ffi.load
ffi.load = function(path)
  assert(path == '/usr/lib/libct-safe.so')
  return {}
end
local Config = require('config')
ffi.load = load

local allowed = {}
for key in ([[
  dev device o origin cmps components stat_t state_topic cmd_t command_topic
  avty availability avty_t availability_topic avty_mode availability_mode
  avty_tpl availability_template pl_avail payload_available
  pl_not_avail payload_not_available qos e encoding
]]):gmatch('%S+') do
  allowed[key] = true
end

local function check(client_id, interval)
  local broker = ([[
broker_ipv4=192.168.42.2
broker_port=1883
mqtt_username=test
mqtt_password=test
client_id=%s
lan_ipv4=192.168.42.3
lan_prefix=24
admin_ipv4=192.168.42.4
interval_seconds=%d
]]):format(client_id, interval)
  local config = Config.parse(broker)
  function Config.read(_, name)
    if name == 'broker.conf' then return broker end
    assert(name == 'targets.conf')
    return ''
  end

  local payloads = {}
  local noop = function() end
  local yes = function() return true end
  package.loaded.uart = {
    config = noop,
    open_session = function() return {close = yes} end
  }
  package.loaded.net = {
    transport = noop,
    now = function() return 0 end,
    stop_signals = function() return {poll = yes, restore = yes} end
  }
  package.loaded.led = {set = noop}
  package.loaded.mqtt = {new = function()
    return {
      state = 'stopped', acks = 0,
      set = function(_, topic, payload, retained)
        assert(retained)
        if topic == config.legacy_topics[1] or topic == config.legacy_topics[2] then
          assert(payload == '')
          return
        end
        assert(topic == config.discovery_topics[1] or topic == config.discovery_topics[2], topic)
        assert(not payloads[topic], topic)
        payloads[topic] = payload
      end,
      set_availability = noop, offline_acked = function() return false end, close_abrupt = noop
    }
  end}

  local original_arg, original_exit = arg, os.exit
  arg = {[0] = directory .. '/service.lua', '--run'}
  os.exit = function(code) assert(code == 31, 'unexpected service exit ' .. code) end
  local ok, reason = pcall(dofile, arg[0])
  arg, os.exit = original_arg, original_exit
  assert(ok, reason)

  local names = {'Cozytouch CETHI', 'Cozytouch IC3'}
  for index, topic in ipairs(config.discovery_topics) do
    local raw = assert(payloads[topic], topic)
    assert(#raw <= 6144, topic .. ' exceeds 6144 bytes')
    local payload = json.decode(raw)
    for key in pairs(payload) do
      assert(allowed[key], topic .. ' invalid root key: ' .. key)
    end
    assert(payload.stat_t == config.state_topics[index], topic)
    assert(payload.dev.name == names[index], topic)
    local count = 0
    for key, cmp in pairs(payload.cmps) do
      assert(cmp.p == 'sensor' or cmp.p == 'binary_sensor', topic .. ' invalid platform: ' .. key)
      assert(cmp.exp_aft == interval + 45, topic .. ' invalid expiration: ' .. key)
      count = count + 1
    end
    assert(count == 21, topic .. ' unexpected component count: ' .. count)
    print(('%s interval=%d bytes=%d components=%d'):format(topic, interval, #raw, count))
  end
end

check('cozytouch-hub', 30)
check('cozytouch-hub', 60)
check(string.rep('x', 48), 3600)
