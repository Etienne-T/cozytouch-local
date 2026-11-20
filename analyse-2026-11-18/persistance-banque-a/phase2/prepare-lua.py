from pathlib import Path
import sys

reference, source, destination = map(Path, sys.argv[1:])
destination.mkdir(parents=True, exist_ok=True)
uart = (reference / "uart.lua").read_text()
# Preserve the frame codec, correlation, known vectors and kernel termios ABI.
uart = uart[:uart.index("function M.open_session(")]
(destination / "uart.lua").write_text(uart + (source / "uart-session.lua").read_text())
(destination / "net.lua").write_bytes((reference / "net.lua").read_bytes())
mqtt = (reference / "mqtt.lua").read_text()
replacements = [
    ("-- No subscribe, incoming commands, TLS, credentials, or production endpoints.",
     "-- MQTT username/password on an isolated LAN; no subscription or command path."),
    ("return M.packet(0x10,str('MQTT')..string.char(4,0x2e)..u16(20)..str(c.client_id)..str(c.topic_prefix..'/availability')..str('offline'))",
     "return M.packet(0x10, str('MQTT') .. string.char(4, 0xee) .. u16(20)"
     " .. str(c.client_id) .. str(c.topic_prefix .. '/availability') .. str('offline')"
     " .. str(c.mqtt_username) .. str(c.mqtt_password))"),
    ("assert(topic:sub(1,#config.topic_prefix+1)==config.topic_prefix..'/' and #topic<=200 and #payload<=2048,'MQTT publication allowlist/bound')",
     "assert(#topic <= 200 and #payload <= 6144, 'MQTT publication bound')"),
    ("assert(#topic<=200 and #payload<=2048 and id>=1", "assert(#topic<=200 and #payload<=6144 and id>=1"),
    # Device-based discovery configs exceed 2 KiB: one packet up to 8 KiB, still one in flight.
    ("assert(n>=0 and n<=4096);local bytes={}", "assert(n>=0 and n<=8192);local bytes={}"),
    ("assert(#self.tx+#packet<=4096,'MQTT send bound')", "assert(#self.tx+#packet<=8192,'MQTT send bound')"),
    ("assert(topic==config.topic_prefix..'/availability' or topic==config.topic_prefix..'/cethi/state' or topic==config.topic_prefix..'/ic3/state' or topic==config.topic_prefix..'/test/state','MQTT topic not allowed')",
     "assert(topic == config.topic_prefix .. '/availability' or topic == config.state_topics[1]"
     " or topic == config.state_topics[2] or topic == config.discovery_topics[1]"
     " or topic == config.discovery_topics[2] or topic == config.legacy_topics[1]"
     " or topic == config.legacy_topics[2], 'MQTT topic not allowed')"),
    ("assert(count<=4,'publication queue bound')", "assert(count<=7,'publication queue bound')"),
    ("self.next_try=now+self.backoff", "self.acknowledged={}\n"
     "    for _, topic in ipairs(config.state_topics) do self.latest[topic]=nil;self.dirty[topic]=nil end\n"
     "    self.next_try=now+self.backoff"),
    ("sent.topic:sub(#config.topic_prefix+2)", "sent.topic:match('/([^/]+)$')"),
    ("for _,suffix in ipairs({'cethi/state','ic3/state','test/state'}) do local candidate=config.topic_prefix..'/'..suffix;",
     "for _,candidate in ipairs({config.legacy_topics[1],config.legacy_topics[2],config.discovery_topics[1],config.discovery_topics[2],config.state_topics[1],config.state_topics[2]}) do "),
    ("""  function c:graceful_disconnect()
    assert(self:offline_acked(),'offline publication not acknowledged')
    -- A short/nonblocking DISCONNECT write is insufficient: close without a
    -- complete packet causes the broker to publish the already-offline LWT.
    pcall(function() self.io:write(string.char(0xe0,0)) end);self:close_abrupt()
  end""",
     """  function c:graceful_disconnect(now, pause, deadline)
    assert(self:offline_acked(), 'offline publication not acknowledged')
    local packet = string.char(0xe0, 0)
    local ok = pcall(function()
      while #packet > 0 and now() < deadline do
        local sent = self.io:write(packet)
        assert(sent >= 0 and sent <= #packet, 'invalid socket write count')
        packet = packet:sub(sent + 1)
        if #packet > 0 then pause() end
      end
    end)
    self:close_abrupt()
    return ok and #packet == 0
  end""")
]
for before, after in replacements:
    assert mqtt.count(before) == 1, "MQTT baseline differs"
    mqtt = mqtt.replace(before, after)
(destination / "mqtt.lua").write_text(mqtt)
(destination / "config.lua").write_bytes((source / "config.lua").read_bytes())
(destination / "service.lua").write_bytes((source / "service.lua").read_bytes())
(destination / "radio-start.lua").write_bytes((source / "radio-start.lua").read_bytes())
(destination / "led.lua").write_bytes((source / "led.lua").read_bytes())
(destination / "registers.lua").write_bytes((source / "registers.lua").read_bytes())
