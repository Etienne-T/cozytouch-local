-- ct-update : versions de l'application dans /apps/app (conception :
-- analyse-2026-11-19/mise-a-jour-lan/CONCEPTION.md). Appele par le lien ct-update sous flock.
--   status | install <sha256> (archive CTAPP1 sur l'entree standard) | rollback | reboot
--   boot-select (init) | promote (healthy, apres ack) | abandon (supervise, essai en echec)
-- Variables de test : CT_APPS, CT_RUN, CT_FACTORY, CT_TEST=1 (ni remontage ni redemarrage).
local APPS = os.getenv('CT_APPS') or '/apps'
local RUN = os.getenv('CT_RUN') or '/run/ct'
local FACTORY = os.getenv('CT_FACTORY') or '/usr/share/cozytouch/phase2'
local TEST = os.getenv('CT_TEST') == '1'
local APP = APPS .. '/app'
local MAX_ARCHIVE, MAX_FILE, MAX_FILES = 4 * 1024 * 1024, 1024 * 1024, 64

io.stdout:setvbuf('no')

local function q(s)
  assert(type(s) == 'string' and not s:find("'", 1, true), 'quote')
  return "'" .. s .. "'"
end
local function sh(command) return os.execute(command) == 0 end
local function capture(command)
  local pipe = assert(io.popen(command))
  local data = pipe:read('*a')
  pipe:close()
  return data
end
local function read_file(path)
  local file = io.open(path, 'rb')
  if not file then return nil end
  local data = file:read('*a')
  file:close()
  return data
end
local function write_file(path, data)
  local file = assert(io.open(path, 'wb'))
  assert(file:write(data))
  assert(file:close())
end
local function valid_name(name)
  return #name <= 64 and name:match('^[a-z][a-z0-9_-]*%.lua$') ~= nil
end
local function valid_version(name) return name and name:match('^v%-[0-9a-f]+$') ~= nil end

local function link(name)
  local path = APP .. '/' .. name
  if not sh('test -L ' .. q(path)) then return nil end
  local target = capture('readlink ' .. q(path)):gsub('\n$', '')
  return valid_version(target) and target or nil
end
local function present(name)
  local path = APP .. '/' .. name
  return sh('test -e ' .. q(path) .. ' -o -L ' .. q(path))
end

local writable = false
local function rw()
  if writable then return end
  if not TEST then assert(sh('mount -o remount,rw,nodev,nosuid,noexec ' .. q(APPS)), 'APPS_REMOUNT_RW') end
  writable = true
end
local function ro()
  if not writable then return end
  sh('sync')
  if not TEST then assert(sh('mount -o remount,ro,nodev,nosuid,noexec ' .. q(APPS)), 'APPS_REMOUNT_RO') end
  writable = false
end
local function set_link(name, target)
  local temporary = APP .. '/.' .. name .. '.tmp'
  assert(sh('rm -f ' .. q(temporary)), 'rm')
  assert(sh('ln -s ' .. q(target) .. ' ' .. q(temporary)), 'ln')
  assert(os.rename(temporary, APP .. '/' .. name))
end
local function drop_link(name) assert(sh('rm -f ' .. q(APP .. '/' .. name)), 'rm') end

-- A version directory holds MANIFEST and exactly the regular files it lists.
local function verify_dir(dir)
  local manifest = read_file(dir .. '/MANIFEST')
  if not manifest or #manifest == 0 then return false end
  local listed, rebuilt = {}, {}
  for sum, name in manifest:gmatch('([0-9a-f]+)  ([^\n]+)\n') do
    if #sum ~= 64 or not valid_name(name) or listed[name] then return false end
    listed[name] = true
    rebuilt[#rebuilt + 1] = sum .. '  ' .. name .. '\n'
  end
  if table.concat(rebuilt) ~= manifest or not listed['service.lua'] then return false end
  for entry in capture('ls -A ' .. q(dir)):gmatch('[^\n]+') do
    if entry ~= 'MANIFEST' and not listed[entry] then return false end
  end
  for name in pairs(listed) do
    local path = q(dir .. '/' .. name)
    if not sh('test -f ' .. path .. ' -a ! -L ' .. path) then return false end
  end
  return sh('cd ' .. q(dir) .. ' && sha256sum -c MANIFEST >/dev/null 2>&1')
end
local function verify(version) return valid_version(version) and verify_dir(APP .. '/' .. version) end

local function run_state()
  return (read_file(RUN .. '/app-mode') or ''):gsub('\n$', ''),
         (read_file(RUN .. '/app-version') or ''):gsub('\n$', '')
end

local function refuse(reason)
  print('UPDATE_REFUSED ' .. reason)
  os.exit(2)
end

-- CTAPP1 archive: "CTAPP1\n", then per file "F <name> <size> <sha256>\n<bytes>", then "END\n".
local function parse(data)
  if data:sub(1, 7) ~= 'CTAPP1\n' then refuse('format') end
  local pos, files, seen = 8, {}, {}
  while true do
    if data:sub(pos) == 'END\n' then break end
    local header_end = data:find('\n', pos, true)
    if not header_end then refuse('truncated') end
    local name, size, sum = data:sub(pos, header_end - 1):match('^F ([^ ]+) (%d+) ([0-9a-f]+)$')
    if not name or not valid_name(name) or seen[name] or #sum ~= 64 then refuse('entry') end
    size = tonumber(size)
    if size > MAX_FILE or header_end + size > #data then refuse('entry_size') end
    local content = data:sub(header_end + 1, header_end + size)
    if not loadstring(content, '=' .. name) then refuse('lua_syntax ' .. name) end
    seen[name] = true
    files[#files + 1] = {name = name, sum = sum, content = content}
    if #files > MAX_FILES then refuse('too_many_files') end
    pos = header_end + size + 1
  end
  if not seen['service.lua'] then refuse('no_service') end
  table.sort(files, function(a, b) return a.name < b.name end)
  return files
end

local commands = {}

function commands.status()
  local mode, version = run_state()
  print('APP_STATUS mode=' .. (mode ~= '' and mode or 'unknown') .. ' running=' .. (version ~= '' and version or 'factory'))
  for _, name in ipairs({'current', 'previous', 'next', 'trying'}) do
    print('APP_LINK ' .. name .. '=' .. (link(name) or '-'))
  end
  for entry in capture('ls -A ' .. q(APP) .. ' 2>/dev/null'):gmatch('[^\n]+') do
    if valid_version(entry) then print('APP_VERSION ' .. entry .. ' valid=' .. tostring(verify(entry))) end
  end
end

function commands.install(sum)
  if not (sum and #sum == 64 and sum:match('^[0-9a-f]+$')) then refuse('usage') end
  local mode = run_state()
  if mode == 'trial' or present('trying') then refuse('trial_in_progress') end
  if not TEST and not read_file(RUN .. '/healthy') then refuse('boot_not_healthy') end
  local data = io.stdin:read(MAX_ARCHIVE + 1) or ''
  if #data > MAX_ARCHIVE then refuse('archive_size') end
  local incoming = RUN .. '/incoming.ctapp'
  write_file(incoming, data)
  local got = capture('sha256sum ' .. q(incoming)):match('^([0-9a-f]+)')
  os.remove(incoming)
  if got ~= sum then refuse('sha256') end
  local files = parse(data)
  local version = 'v-' .. sum:sub(1, 12)
  if link('current') == version then refuse('already_current') end
  rw()
  assert(sh('mkdir -p ' .. q(APP)), 'mkdir')
  local stage = APP .. '/.stage-' .. version
  assert(sh('rm -rf ' .. q(stage) .. ' && mkdir ' .. q(stage)), 'stage')
  local manifest = {}
  for _, file in ipairs(files) do
    write_file(stage .. '/' .. file.name, file.content)
    manifest[#manifest + 1] = file.sum .. '  ' .. file.name .. '\n'
  end
  write_file(stage .. '/MANIFEST', table.concat(manifest))
  sh('sync')
  if not verify_dir(stage) then
    sh('rm -rf ' .. q(stage))
    ro()
    refuse('file_sha256')
  end
  assert(sh('rm -rf ' .. q(APP .. '/' .. version)), 'rm')
  assert(os.rename(stage, APP .. '/' .. version))
  set_link('next', version)
  ro()
  print('UPDATE_STAGED version=' .. version .. ' files=' .. #files .. ' (active at next boot)')
end

function commands.rollback()
  local previous = link('previous')
  if not verify(previous) then refuse('no_valid_previous') end
  if present('trying') then refuse('trial_in_progress') end
  rw()
  set_link('next', previous)
  ro()
  print('UPDATE_ROLLBACK_STAGED version=' .. previous .. ' (active at next boot)')
end

local function reboot()
  sh('sync')
  if TEST then print('REBOOT_REQUESTED'); return end
  print('REBOOT_NOW')
  sh('sleep 2')
  os.execute('reboot -f')
end
commands.reboot = reboot

commands['boot-select'] = function()
  local mode, version = 'factory', nil
  if sh('test -d ' .. q(APP)) then
    local candidate = link('next')
    if candidate then
      rw()
      set_link('trying', candidate)
      drop_link('next')
      ro()
      if verify(candidate) then
        mode, version = 'trial', candidate
      else
        print('APP_TRIAL_INVALID version=' .. candidate)
        rw(); drop_link('trying'); ro()
      end
    elseif present('trying') then
      print('APP_TRIAL_ABANDONED version=' .. (link('trying') or '?'))
      rw(); drop_link('trying'); ro()
    end
    if mode == 'factory' then
      local current = link('current')
      if current and verify(current) then
        mode, version = 'current', current
      elseif current then
        print('APP_CURRENT_INVALID version=' .. current)
      end
    end
  end
  write_file(RUN .. '/app-dir', (version and APP .. '/' .. version or FACTORY) .. '\n')
  write_file(RUN .. '/app-mode', mode .. '\n')
  write_file(RUN .. '/app-version', (version or '') .. '\n')
  print('APP_SELECT mode=' .. mode .. ' version=' .. (version or 'factory'))
end

function commands.promote()
  write_file(RUN .. '/healthy', 'ok\n')
  local mode, version = run_state()
  if mode ~= 'trial' then return end
  assert(valid_version(version) and link('trying') == version, 'APP_TRYING_MISMATCH')
  local current = link('current')
  rw()
  if current and current ~= version then set_link('previous', current) end
  set_link('current', version)
  drop_link('trying')
  local keep = {[version] = true, [current or ''] = true, [link('next') or ''] = true}
  for entry in capture('ls -A ' .. q(APP)):gmatch('[^\n]+') do
    if (valid_version(entry) and not keep[entry]) or entry:match('^%.stage%-') then
      assert(sh('rm -rf ' .. q(APP .. '/' .. entry)), 'prune')
    end
  end
  ro()
  write_file(RUN .. '/app-mode', 'current\n')
  print('APP_PROMOTED version=' .. version .. ' previous=' .. (current or '-'))
end

function commands.abandon()
  local mode, version = run_state()
  if mode ~= 'trial' then return 1 end
  rw()
  drop_link('trying')
  ro()
  print('APP_TRIAL_FAILED version=' .. version .. ' reboot=once')
  reboot()
end

local name = arg[1]
local command = commands[name]
if not command then print('usage: ct-update status|install <sha256>|rollback|reboot'); os.exit(2) end
local ok, result = pcall(command, arg[2])
if not ok then
  pcall(ro)
  print('UPDATE_ERROR ' .. tostring(result):gsub('\n', ' '))
  os.exit(1)
end
os.exit(type(result) == 'number' and result or 0)
