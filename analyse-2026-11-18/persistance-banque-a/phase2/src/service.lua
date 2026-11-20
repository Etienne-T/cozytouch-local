local directory = assert(arg[0]:match('^(.*[/\\])'))
package.path = directory .. '?.lua;' .. package.path
local Config = require('config')
local UART = require('uart')
local Net = require('net')
local MQTT = require('mqtt')
local json = require('cjson')
local Led = require('led')

io.stdout:setvbuf('no')
local mode = arg[1]
local private_dir = '/apps/ct'
local device = '/dev/ttyS1'
local loaded, config, targets = pcall(function()
  local c = Config.parse(Config.read(private_dir, 'broker.conf', 4096))
  local t = UART.config(Config.read(private_dir, 'targets.conf', 2047))
  return c, t
end)
if not loaded then print('CONFIG_REJECTED'); os.exit(21) end

if mode == '--check-config' then
  print('CONFIG_OK targets=2')
  return
end
if mode == '--network' then
  local loaded_keys, keys, host_key = pcall(function()
    return Config.read(private_dir, 'authorized_keys', 4096), Config.read(private_dir, 'ssh_host_key', 4096)
  end)
  if not loaded_keys then print('SSH_CONFIG_REJECTED'); os.exit(21) end
  local function write(path, data)
    local file = assert(io.open(path, 'wb'))
    assert(file:write(data))
    assert(file:close())
  end
  write('/run/ct/ssh/authorized_keys', keys)
  write('/run/ct/ssh/host_key', host_key)
  local command = table.concat({'/usr/libexec/ct/network.sh', config.lan_ipv4,
    config.lan_prefix, config.broker_ipv4, config.broker_port, config.admin_ipv4}, ' ')
  os.exit(os.execute(command) == 0 and 0 or 21)
end
assert(mode == '--run', 'service mode')

local Registers = require('registers')
local labels = {'CETHI', 'IC3'}

-- Home Assistant device-based discovery: one retained config per device, one component per value.
-- Values come from the device state topic; a missing or null key renders None (unknown in HA).
local function component(id, key, ha, enabled)
  local c = {p = ha.p, name = ha.name, uniq_id = id .. '_' .. key,
    val_tpl = "{{value_json.get('" .. key .. "')}}"}
  c.unit_of_meas, c.dev_cla, c.stat_cla, c.ent_cat, c.ops = ha.unit, ha.dev_cla, ha.stat_cla, ha.ent_cat, ha.ops
  if ha.p == 'binary_sensor' then c.pl_on, c.pl_off = 'ON', 'OFF' end
  if enabled == false or ha.en == false then c.en = false end
  return c
end
local function discovery(index)
  local label = labels[index]
  local id = config.client_id .. '_' .. label:lower()
  local cmps = {}
  for _, r in ipairs(Registers.devices[label]) do
    for _, f in ipairs(r.fields) do cmps[f.key] = component(id, f.key, f.ha) end
  end
  if label == 'CETHI' then
    cmps.target_temp = component(id, 'target_temp',
      {p = 'sensor', name = 'Consigne', unit = '°C', dev_cla = 'temperature', stat_cla = 'measurement'})
    cmps.setpoint_min = component(id, 'setpoint_min',
      {p = 'sensor', name = 'Borne basse', unit = '°C', dev_cla = 'temperature', ent_cat = 'diagnostic'})
    cmps.setpoint_max = component(id, 'setpoint_max',
      {p = 'sensor', name = 'Borne haute', unit = '°C', dev_cla = 'temperature', ent_cat = 'diagnostic'})
  end
  cmps.current_raw = component(id, 'current_raw',
    {p = 'sensor', name = 'Paramètre principal (brut)', stat_cla = 'measurement', ent_cat = 'diagnostic'}, false)
  cmps.rssi_raw = component(id, 'rssi_raw', {p = 'sensor', name = 'Signal radio', unit = 'dBm',
    dev_cla = 'signal_strength', stat_cla = 'measurement', ent_cat = 'diagnostic'}, false)
  for _, cmp in pairs(cmps) do
    -- Allow for one optional read already in flight, two MAIN_INFO reads and two PUBACKs.
    cmp.exp_aft = config.interval_seconds + 45
  end
  return json.encode({
    dev = {ids = {id}, name = 'Cozytouch ' .. label, mf = 'Atlantic'}, o = {name = 'cozytouch-hub'},
    stat_t = config.state_topics[index], avty_t = config.topic_prefix .. '/availability',
    cmps = cmps
  })
end

local mqtt = MQTT.new(config, Net.transport(config), print)
Led.set('working')
-- Health budget: 95 s of MQTT session time, not wall time. While the broker is
-- unreachable (Home Assistant still booting after a power cut), the service waits.
local health_budget, connected_seconds, last_tick = 95, 0, Net.now()
local stop = Net.stop_signals()
local uart
local terminal_code = 0
local function has_current_ack(topic)
  return mqtt.state == 'ready' and mqtt.acknowledged[topic] == (mqtt.latest[topic] or {}).payload
    and mqtt.latest[topic] ~= nil
end

local ok, reason = pcall(function()
  uart = UART.open_session(targets, Net.now, device)
  local next_read, pending_publish = 0, false
  local pair, pair_connection = {}, nil
  local read_index, sequence = 1, 0
  local online, stopping, ack_done = false, false, false
  -- An optional series starts after a published MAIN_INFO pair and yields to the next pair when due.
  local details, main = {{}, {}}, {}
  local main_connection, private_details
  local limit_min, limit_max
  local private_queue, pairs_done = {}, 0
  local private_every = math.max(1, math.ceil(300 / config.interval_seconds))
  local function state_payload(i)
    local out = {}
    for key, value in pairs(main[i]) do out[key] = value end
    for key, value in pairs(details[i]) do out[key] = value end
    if i == 1 and limit_min then
      out.setpoint_min, out.setpoint_max = Registers.celsius(limit_min), Registers.celsius(limit_max)
      out.target_temp = Registers.setpoint(out.target_raw, limit_min, limit_max)
    end
    return json.encode(out)
  end
  -- Remove the per-entity configs of the first version (single raw sensor) before the device configs.
  for _, topic in ipairs(config.legacy_topics) do mqtt:set(topic, '', true) end
  for i, topic in ipairs(config.discovery_topics) do mqtt:set(topic, discovery(i), true) end
  mqtt:set_availability('offline')
  while true do
    stopping = stopping or stop.poll()
    local now = Net.now()
    if mqtt.state == 'ready' then connected_seconds = connected_seconds + (now - last_tick) end
    last_tick = now
    if not ack_done and terminal_code == 0 and connected_seconds >= health_budget then
      print('HEALTH_TIMEOUT connected_seconds=' .. health_budget)
      terminal_code, stopping = 31, true
    end
    if stopping and not uart.active and uart.stage ~= 'revision' then break end
    mqtt:step(now)
    if main_connection and (mqtt.state ~= 'ready' or main_connection ~= mqtt.connections) then
      -- Finish an armed UART read, but discard everything acquired on the old connection.
      main_connection, private_details = nil, nil
      private_queue, pairs_done, details, main = {}, 0, {{}, {}}, {}
      next_read = 0
    end
    local result = uart:step(stopping, not stopping and mqtt.state == 'ready' and main_connection == mqtt.connections)
    if uart.ready and not online and not stopping then
      online = true
      mqtt:set_availability('online')
    end
    if result and result.limits then
      local max1, minimum, max2 = unpack(result.values)
      if not result.failed and max1 and minimum and max1 == max2
          and minimum < max1 and minimum >= 27315 and max1 <= 37315 then
        limit_min, limit_max = minimum, max1
        mqtt:set(config.state_topics[1], state_payload(1), false)
        pending_publish = true
        print('LIMITS_ACCEPTED')
      else
        print('LIMITS_UNAVAILABLE reason=' .. (result.failed or 'INCONSISTENT_VALUES'))
      end
    elseif result and result.private then
      local label = labels[result.index]
      local blob = result.data and result.data.blob or ''
      print(string.format('PRIVATE_RESULT index=%d register=0x%04x status=%s bytes=%d', result.index,
        result.target_index, result.status, #blob))
      if result.status == 'RESET_CONTEXT_LOST' then terminal_code = 33; break end
      if private_details then
        local values = result.status == 'DONE' and Registers.decode(label, result.target_index, blob) or {}
        for _, f in ipairs(Registers.allowed[label][result.target_index].fields) do
          local value = values[f.key]
          if value == nil then value = json.null end
          private_details[result.index][f.key] = value
        end
      end
      if private_details and #private_queue == 0 and not stopping then
        details = private_details
        private_details = nil
        for i, topic in ipairs(config.state_topics) do mqtt:set(topic, state_payload(i), false) end
        pending_publish, pair_connection = true, mqtt.connections
        print('PRIVATE_PUBLISHED')
      end
    elseif result then
      print('READ_RESULT index=' .. result.index .. ' status=' .. result.status)
      if result.status ~= 'DONE' then
        terminal_code = (result.status == 'TIMEOUT') and 32 or 33
        break
      end
      if mqtt.state == 'ready' and pair_connection == mqtt.connections and not stopping then
        local d = result.data
        sequence = sequence + 1
        pair[result.index] = {
          status = 'DONE', value_semantics = 'main_parameter_raw',
          current_raw = d.current_raw, target_raw = d.target_raw,
          remaining_time_raw = d.remaining_time_raw, origin_raw = d.origin, rssi_raw = d.rssi,
          observed_monotonic_ms = math.floor(Net.now() * 1000), sequence = sequence
        }
        if result.index == 2 then
          main = {pair[1], pair[2]}
          main_connection = pair_connection
          for i, topic in ipairs(config.state_topics) do mqtt:set(topic, state_payload(i), false) end
          pending_publish, read_index = true, 1
          next_read = Net.now() + config.interval_seconds
          if not private_details and pairs_done % private_every == 0 then
            private_details = {{}, {}}
            for i, label in ipairs(labels) do
              for _, r in ipairs(Registers.devices[label]) do private_queue[#private_queue + 1] = {i, r.index} end
            end
          end
          pairs_done = pairs_done + 1
        else
          read_index = 2
        end
      else
        pair, read_index, next_read = {}, 1, 0
      end
    end
    local ready = online and mqtt.state == 'ready'
      and mqtt.acknowledged[config.topic_prefix .. '/availability'] == 'online'
      and has_current_ack(config.discovery_topics[1]) and has_current_ack(config.discovery_topics[2])
    if pending_publish and (mqtt.state ~= 'ready' or pair_connection ~= mqtt.connections) then
      pending_publish, read_index, next_read = false, 1, 0
    end
    if ready and pending_publish and has_current_ack(config.state_topics[1])
        and has_current_ack(config.state_topics[2]) and not stopping then
      pending_publish = false
      if not ack_done then
        local ack_status = os.execute('/usr/libexec/ct/healthy')
        if ack_status ~= 0 then terminal_code = 34; break end
        ack_done = true
        print('HEALTH_OK counter_ack=verified')
      end
    end
    Led.set((ready and ack_done and not pending_publish) and 'ok' or 'working')
    if read_index == 2 and (not ready or pair_connection ~= mqtt.connections) then
      pair, read_index, next_read = {}, 1, 0
    end
    if not stopping and ready and not pending_publish and not uart.active then
      if ack_done and main_connection == mqtt.connections and not uart.limits_started then
        uart:start_limits()
      elseif read_index == 2 or Net.now() >= next_read then
        if read_index == 1 then pair, pair_connection = {}, mqtt.connections end
        uart:start(read_index)
        print('READ_ARMED index=' .. read_index)
      elseif #private_queue > 0 then
        local item = table.remove(private_queue, 1)
        uart:start_private(item[1], item[2])
        uart.active.target_index = item[2]
      end
    end
    Net.pause()
  end
  if terminal_code == 0 and not ack_done then terminal_code = 31 end
end)
local restored = not uart or uart:close()
print('UART_CLEANUP restored=' .. tostring(restored))
if not ok then
  local label = tostring(reason):match('STM32_[A-Z_]+') or tostring(reason):match('UART_[A-Z_]+') or 'SERVICE_FAILURE'
  terminal_code = label:match('^STM32_') and 35 or 36
  print(label)
end
if not restored then terminal_code = 36 end
if terminal_code ~= 0 then Led.set('error') end
mqtt:set_availability('offline')
local cutoff = Net.now() + 6
if mqtt.state == 'ready' then
  while Net.now() < cutoff and mqtt.state == 'ready' and not mqtt:offline_acked() do
    mqtt:step(Net.now())
    Net.pause()
  end
end
if mqtt:offline_acked() then
  local sent = mqtt:graceful_disconnect(Net.now, Net.pause, cutoff)
  print('MQTT_DISCONNECT complete=' .. tostring(sent))
else
  mqtt:close_abrupt()
end
if not stop.restore() then terminal_code = 36 end
print('SERVICE_EXIT status=' .. terminal_code .. ' pubacks=' .. mqtt.acks)
os.exit(terminal_code)

