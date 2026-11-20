-- Append this backend after the qualified codec and ABI declarations.

-- Atlantic private READ (GenericV2). Request shape from the 17 November capture (sonde 0x001a):
-- the same 34-byte node context as MAIN_INFO, then subCommand PRIVATE=7, legacySize=4 and the
-- private TSD: manufacturer 0x0c, access 0x60 (READ), index u16 BE. Only allowlisted indexes.
local Registers = require('registers')
function M.private_request(t, index)
  assert(Registers.allowed[t.label] and Registers.allowed[t.label][index], 'PRIVATE_READ_ALLOWLIST')
  local p = table.concat(t.fields) .. string.char(7, 4, 0x0c, 0x60, math.floor(index / 256), index % 256)
  assert(#p == 40 and p:byte(35) == 7 and p:byte(36) == 4 and p:byte(37) == 0x0c and p:byte(38) == 0x60,
    'PRIVATE_READ_SHAPE')
  return frame(0x0101, p)
end

-- Reply 0x040c (LISTENER__PRIVATE_COMMAND_ACK): rssi i32, device, hub, frameType, ctrl0, ctrl1,
-- command 0x21, then manufacturer, access echo, index BE and the value blob.
function M.private_transaction(target, index, start, deadline)
  local t = {target = target, index = index, start = start, deadline = deadline, done = false, ignored = 0}
  function t:finish(status, data) if self.done then return false end; self.done = true; self.status = status; self.data = data; return true end
  function t:tick(now) if not self.done and now >= self.deadline then self:finish('TIMEOUT') end end
  function t:accept(f, now)
    self:tick(now); if self.done then return false end
    if f.id == 0x050e then self:finish('RESET_CONTEXT_LOST'); return true end
    local p = f.payload
    if f.id ~= 0x040c or #p < 18 or p:sub(5, 7) ~= target.target or p:sub(8, 10) ~= target.source
        or be(p, 17, 2) ~= index then
      self.ignored = self.ignored + 1; return false
    end
    if p:byte(11) ~= 0 or math.floor(p:byte(12) / 32) % 2 ~= 0 or p:byte(14) ~= 0x21 or p:byte(15) ~= 0x0c then
      self.ignored = self.ignored + 1; return false
    end
    local info = {access = p:byte(16), blob = p:sub(19)}
    if info.access ~= 0x60 or #info.blob > 32 then self:finish('DEVICE_ERROR', info); return true end
    self:finish('DONE', info); return true
  end
  return t
end

local limit_types = {7, 6, 7}
local function limit_phase(target, transmit, now)
  assert(target.label == 'CETHI', 'LIMIT_TARGET')
  local start = now()
  local phase = {limits = true, values = {}, requests = 0, next_request = start,
    last_rx = start, quiet = 2}

  function phase:send_next()
    self.requests = self.requests + 1
    local kind = limit_types[self.requests]
    local payload = table.concat(target.fields) .. string.char(1, 3, kind, 0, 0)
    transmit(frame(0x0100, payload))
    self.sent = now()
    self.deadline = self.sent + 1
    print('LIMIT_ARMED type=' .. kind)
  end

  function phase:accept(item, time)
    local p = item.payload
    if not self.deadline or time >= self.deadline or item.id ~= 0x010d or #p ~= 20
        or p:sub(5, 10) ~= target.target .. target.source
        or p:sub(11, 16) ~= '\0\142\0\4\5\0' or p:sub(19, 20) ~= '\0\0' then
      self.failed = self.failed or 'UNEXPECTED_ACK'
      return
    end
    self.values[self.requests] = be(p, 17, 2)
    self.deadline = nil
    self.next_request = math.max(self.sent + 1, time + 0.5)
  end

  function phase:tick(time, continue_limits, drained, partial)
    if self.deadline and time >= self.deadline then
      self.last_rx = math.max(self.last_rx, self.deadline)
      self.quiet = 10
      self.deadline = nil
      self.failed = self.failed or 'TIMEOUT'
    end
    if not continue_limits then self.failed = self.failed or 'INTERRUPTED' end
    if self.deadline then return end
    -- Between requests or during the guard, no part of a frame is expected.
    if partial then self.failed = self.failed or 'UNEXPECTED_PARTIAL' end
    if not drained or partial then return end
    if self.failed or self.requests == #limit_types then
      self.done = time >= self.last_rx + self.quiet
    elseif time >= self.next_request then
      self:send_next()
    end
  end

  return phase
end

function M.open_session(targets, now, path)
  local ffi, C = ensure_abi()
  local safe = require('config').safe
  local self = {tty = -1, lock = -1, exclusive = false, ready = false, parser = M.parser(),
    stage = 'stack', boot_deadline = now() + 20, last_boot_event = now()}
  local buf = ffi.new('char[4096]')
  local blank = ffi.cast('void *', 0)
  local boot_marker = io.open('/proc/sys/kernel/random/boot_id', 'rb')
  local boot_id = boot_marker and boot_marker:read('*l')
  if boot_marker then boot_marker:close() end
  local next_receipt_check = 0

  function self:close()
    local ok = true
    if self.tty >= 0 then
      if self.old then
        local check = ffi.new('ct_termios[1]')
        if C.ioctl(self.tty, 0x540b, ffi.cast('int', 0)) ~= 0
          or C.ioctl(self.tty, 0x5402, self.old) ~= 0
          or C.ioctl(self.tty, 0x5401, check) ~= 0
          or ffi.string(check, 36) ~= ffi.string(self.old, 36) then
          ok = false
        end
      end
      if self.exclusive and C.ioctl(self.tty, 0x540d, blank) ~= 0 then ok = false end
      if C.close(self.tty) ~= 0 then ok = false end
      self.tty = -1
    end
    if self.lock >= 0 then C.close(self.lock); self.lock = -1 end
    return ok
  end

  local ok = pcall(function()
    self.lock = C.open('/run/ct/autonomous-uart.lock', 0xa0042, ffi.cast('int', 384))
    assert(self.lock >= 0 and C.flock(self.lock, 6) == 0)
    assert(safe.ct_uart_sole(path, -1) == 0)
    self.tty = C.open(path, 0xa0902)
    assert(self.tty >= 0)
    assert(C.ioctl(self.tty, 0x540c, blank) == 0)
    self.exclusive = true
    assert(safe.ct_uart_sole(path, self.tty) == 0)
    local old = ffi.new('ct_termios[1]')
    assert(C.ioctl(self.tty, 0x5401, old) == 0)
    self.old = old
    local raw = ffi.new('ct_termios[1]')
    raw[0].cflag = 0x18b2
    assert(C.ioctl(self.tty, 0x5402, raw) == 0)
    local check = ffi.new('ct_termios[1]')
    assert(C.ioctl(self.tty, 0x5401, check) == 0 and ffi.string(check, 36) == ffi.string(raw, 36))
  end)
  if not ok then
    local restored = self:close()
    error(restored and 'UART_OPEN_FAILED' or 'UART_RESTORE_FAILED', 0)
  end

  -- The STM32 starts on its own at power-up and emits STACK_START before Linux opens
  -- ttyS1 (first bank A boot, 19 November 2026). Like the OEM start mode, pulse PA2 once
  -- while the UART is open, then wait for the fresh STACK_START.
  if os.execute('luajit /usr/share/cozytouch/phase2/radio-start.lua') ~= 0 then
    local restored = self:close()
    error(restored and 'STM32_PULSE_FAILED' or 'UART_RESTORE_FAILED', 0)
  end
  self.boot_deadline, self.last_boot_event = now() + 20, now()

  local function transmit(packet)
    assert(safe.ct_uart_sole(path, self.tty) == 0, 'UART_OWNER_CHANGED')
    local offset, deadline = 0, now() + 0.5
    while offset < #packet do
      assert(now() < deadline, 'UART_TX_TIMEOUT')
      local sent = C.write(self.tty, packet:sub(offset + 1), #packet - offset)
      if sent > 0 then
        offset = offset + sent
      elseif sent < 0 and ffi.errno() ~= 4 and ffi.errno() ~= 11 then
        error('UART_WRITE_FAILED', 0)
      else
        C.usleep(1000)
      end
    end
  end

  function self:start(index)
    assert(self.ready and not self.active, 'UART_STATE')
    local target = assert(targets[index], 'UART_TARGET')
    transmit(M.request(target))
    local sent = now()
    self.active = M.transaction(target, sent, sent + 8)
    self.active.index = index
  end

  function self:start_private(index, register)
    assert(self.ready and not self.active, 'UART_STATE')
    local target = assert(targets[index], 'UART_TARGET')
    transmit(M.private_request(target, register))
    local sent = now()
    self.active = M.private_transaction(target, register, sent, sent + 5)
    self.active.index, self.active.private = index, true
  end

  function self:start_limits()
    assert(self.ready and not self.active and not self.limits_started, 'UART_STATE')
    self.limits_started = true
    self.active = limit_phase(targets[1], transmit, now)
    if #self.parser.buf ~= 0 or self.parser.since then self.active.failed = 'UNEXPECTED_PARTIAL' end
  end

  function self:step(stopping, continue_limits)
    local n = C.read(self.tty, buf, 4096)
    local read_errno = n < 0 and ffi.errno() or nil
    assert(n >= 0 or read_errno == 4 or read_errno == 11, 'UART_READ_FAILED')
    local time = now()
    local active = self.active
    local rejects, noise = self.parser.rejected, self.parser.noise
    local frames = self.parser:feed(n > 0 and ffi.string(buf, n) or '', time)
    if active and active.limits then
      if n > 0 then active.last_rx = time end
      if self.parser.rejected ~= rejects or self.parser.noise ~= noise then
        active.failed = active.failed or 'UART_PARSE_REJECTED'
      end
    end
    for _, item in ipairs(frames) do
      local stack = item.id == 0x0403 and item.payload == '\4'
      if item.id == 0x050e then
        assert(self.stage == 'stack' and not self.boot_reset and #item.payload == 1, 'STM32_RESET')
        self.boot_reset = true
        self.last_boot_event = time
      elseif stack then
        assert(self.stage == 'stack' and not self.stack_seen, 'STM32_RESET')
        self.stack_seen = true
        self.last_boot_event = time
        print('STACK_START observed')
      elseif self.stage == 'revision' and item.id == 0x0500 then
        assert(time < self.rev_deadline and #item.payload == 7 and item.payload:byte(1) == 0,
          'STM32_REVISION_CORRELATION')
        assert(item.payload == '\0v2.4.2', 'STM32_REVISION_MISMATCH')
        self.stage, self.ready = 'ready', true
        print('UART_READY revision=2.4.2')
      elseif self.active then
        self.active:accept(item, time)
      end
    end
    if not stopping and self.stage == 'stack' then
      assert(time < self.boot_deadline, 'STM32_STACK_TIMEOUT')
      if not self.stack_seen and not self.boot_reset and boot_id and time >= next_receipt_check then
        next_receipt_check = time + 0.25
        local received, receipt = pcall(require('config').read, '/run/ct', 'stack-start-observed', 64)
        if received and receipt == ('STACK_START ' .. boot_id .. '\n') then
          self.stack_seen = true
          self.last_boot_event = time
          print('STACK_START passive_receipt')
        end
      end
      if self.stack_seen and time - self.last_boot_event >= 0.35 and #self.parser.buf == 0 then
        transmit(frame(0x0500, '\0'))
        self.stage, self.rev_deadline = 'revision', now() + 3
      end
    elseif self.stage == 'revision' then
      assert(time < self.rev_deadline, 'STM32_REVISION_TIMEOUT')
    end
    if self.active then
      if self.active.limits then
        local drained = n == 0 or read_errno == 11
        local partial = #self.parser.buf ~= 0 or self.parser.since ~= nil
        self.active:tick(now(), not stopping and continue_limits, drained, partial)
      else
        self.active:tick(now())
      end
      if self.active.done then
        local result = self.active
        self.active = nil
        return result
      end
    end
  end
  return self
end

return M
