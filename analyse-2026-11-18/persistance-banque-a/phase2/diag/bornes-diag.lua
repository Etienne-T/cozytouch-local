-- Sonde ponctuelle CETHI. Charger les modules de l'application via LUA_PATH.
io.stdout:setvbuf('no')
local device = '/dev/ttyS1'
local uart, signals, journal
local phase = 'modules'

local function emit(line)
  print(line)
  if journal then assert(journal:write(line, '\n')) end
end

local function service_absent()
  local files = assert(io.popen("printf '%s\\n' /proc/[0-9]*/cmdline", 'r'))
  local found = false
  for path in files:lines() do
    local file = io.open(path, 'rb')
    if file then
      local cmd = file:read(4096) or ''
      file:close()
      local exe, script = cmd:match('^([^%z]+)%z([^%z]+)%z%-%-run%z')
      if exe and (exe == 'luajit' or exe:match('/luajit$'))
          and (script == 'service.lua' or script:match('/service%.lua$')) then
        found = true
        break
      end
    end
  end
  assert(files:close() and not found)
end

local function masque(payload, id, secrets)
  local masked = {}
  for _, secret in ipairs(secrets) do
    local at = payload:find(secret, 1, true)
    while at do
      for i = at, at + #secret - 1 do masked[i] = true end
      at = payload:find(secret, at + 1, true)
    end
  end
  if id == 0x010d and #payload == 28 then
    -- MAIN_INFO peut aussi contenir l'adresse du dernier contrôleur.
    for i = 23, 25 do masked[i] = true end
  end
  return masked
end

local function describe(frame, secrets, target)
  local payload, id = frame.payload, frame.id
  local masked = masque(payload, id, secrets)
  local function octet(i)
    if not payload:byte(i) then return '-' end
    return masked[i] and '<ctx>' or ('%02x'):format(payload:byte(i))
  end
  local tail = {}
  for i = 11, #payload do
    if i == 11 or not (masked[i] and masked[i - 1]) then
      tail[#tail + 1] = octet(i)
    end
  end
  local status, detail, cethi, temperature = '-', '-', '-', ''
  if id == 0x010d then
    status, detail = octet(15), octet(16)
    if #payload >= 10 then
      cethi = payload:sub(5, 7) == target.target and payload:sub(8, 10) == target.source and 'oui' or 'non'
    end
    if #payload == 20 then
      if masked[17] or masked[18] then
        temperature = ' centiemes_kelvin=<ctx> celsius=<ctx>'
      else
        local hi, lo = payload:byte(17, 18)
        local value = hi * 256 + lo
        temperature = (' centiemes_kelvin=%d celsius=%.2f'):format(value, (value - 27315) / 100)
      end
    end
  end
  return ('id=0x%04x longueur=%d ctx=<ctx> cethi=%s statut=%s detail=%s suite=%s%s'):format(
    id, #payload, cethi, status, detail, #tail > 0 and table.concat(tail) or '-', temperature)
end

local ok, reason = pcall(function()
  local Config = require('config')
  local UART = require('uart')
  local Net = require('net')
  phase = 'service'
  service_absent()
  phase = 'proprietaire_uart'
  assert(Config.safe.ct_uart_sole(device, -1) == 0)

  phase = 'configuration'
  local targets = UART.config(Config.read('/apps/ct', 'targets.conf', 2047))
  local target = targets[1]
  assert(target.label == 'CETHI')
  local secrets = {}
  for _, t in ipairs(targets) do
    for _, secret in ipairs({t.source, t.target, t.fields[11], table.concat(t.fields)}) do
      secrets[#secrets + 1] = secret
    end
  end
  local request_context = table.concat(target.fields)
  assert(#request_context == 34)

  signals = Net.stop_signals()
  phase = 'ouverture_uart'
  uart = UART.open_session({target}, Net.now, device)
  phase = 'journal'
  journal = assert(io.open('/run/ct/bornes-diag.txt', 'w'))
  assert(journal:setvbuf('no'))

  local index, kind, started, deadline, count
  local fresh_stack = false
  local feed = uart.parser.feed
  function uart.parser:feed(chunk, now)
    local frames = feed(self, chunk, now)
    for _, frame in ipairs(frames) do
      if started then
        local window = now < deadline
        if window then count = count + 1 end
        emit(('DIAG_FRAME requete=%d type=%d t=%.3f phase=%s %s'):format(
          index, kind, now - started, window and 'attente' or 'pause', describe(frame, secrets, target)))
      elseif frame.id == 0x0403 and frame.payload == '\4' then
        fresh_stack = true
      end
    end
    return frames
  end

  -- Le constructeur MAIN_INFO fournit le contexte et l'enveloppe UART.
  -- Seuls le type étendu et le CRC changent dans la demande de statut.
  local main_request = UART.request
  function UART.request(t)
    assert(t == target and t.label == 'CETHI')
    assert(kind == 3 or kind == 6 or kind == 7)
    local packet = main_request(t)
    assert(#packet == 46 and packet:sub(1, 5) == '\2\1\0\0\40' and packet:byte(-1) == 3)
    local payload = packet:sub(6, -3)
    assert(payload == request_context .. '\1\3\3\0\0')
    payload = payload:sub(1, 36) .. string.char(kind) .. payload:sub(38)
    return packet:sub(1, 5) .. payload .. string.char(UART.crc(payload)) .. packet:sub(-1)
  end

  local function step()
    assert(not signals.poll(), 'DIAG_SIGNAL')
    uart:step(false)
  end

  phase = 'demarrage_radio'
  while not uart.ready do
    step()
    if not uart.ready then Net.pause() end
  end
  assert(fresh_stack, 'DIAG_STACK_ABSENT')
  emit('DIAG_READY revision=2.4.2')

  local function listen(until_time)
    repeat
      step()
      if Net.now() >= until_time then return end
      Net.pause()
    until false
  end

  local sequence = {3, 7, 6, 7, 3}
  for i, requested in ipairs(sequence) do
    index, kind, count = i, requested, 0
    phase = 'emission'
    emit(('DIAG_REQUEST requete=%d type=%d cible=CETHI ctx=<ctx>'):format(index, kind))
    assert(not signals.poll(), 'DIAG_SIGNAL')
    uart:start(1)
    started = uart.active.start
    deadline = started + 8
    phase = 'reception'
    listen(deadline)
    emit(('DIAG_WINDOW requete=%d type=%d trames=%d'):format(index, kind, count))
    if i < #sequence then listen(Net.now() + 2) end
  end
end)

local restored = phase ~= 'ouverture_uart' or reason == 'UART_OPEN_FAILED' or reason == 'STM32_PULSE_FAILED'
if uart then
  local closed, checked = pcall(uart.close, uart)
  restored = closed and checked == true
end
if signals and not signals.restore() then ok = false end
if not ok then
  -- Les erreurs brutes peuvent contenir des paramètres. Seuls ces codes sont publics.
  local code = type(reason) == 'string' and reason:match('([A-Z][A-Z0-9_]+)$')
  local public = {
    UART_OPEN_FAILED = true, UART_RESTORE_FAILED = true, UART_OWNER_CHANGED = true,
    UART_READ_FAILED = true, UART_WRITE_FAILED = true, UART_TX_TIMEOUT = true,
    STM32_PULSE_FAILED = true, STM32_RESET = true, STM32_STACK_TIMEOUT = true,
    STM32_REVISION_TIMEOUT = true, STM32_REVISION_CORRELATION = true, STM32_REVISION_MISMATCH = true,
    DIAG_STACK_ABSENT = true, DIAG_SIGNAL = true,
  }
  pcall(emit, 'DIAG_ERROR etape=' .. phase .. (public[code] and ' code=' .. code or ''))
end
local written = pcall(emit, 'DIAG_DONE restored=' .. tostring(restored))
local closed = not journal or journal:close()
os.exit(ok and restored and written and closed and 0 or 1)
