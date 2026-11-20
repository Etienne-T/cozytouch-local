-- Status LED through the kernel LED class (pwm-leds, src/leds.dtsi).
-- States: boot = orange (kernel default), working = green blinking 1 Hz,
-- ok = green, error = red. The LED is advisory: write failures never stop the service.
local M = {}
local base = '/sys/class/leds/pwm:%s:user/%s'
local current

local function write(color, attribute, value)
  local file = io.open(string.format(base, color, attribute), 'w')
  if not file then return false end
  local ok = file:write(value) and true or false
  return file:close() and ok
end

local patterns = {
  boot = {red = 255, green = 255},
  working = {red = 0, green = 'blink'},
  ok = {red = 0, green = 255},
  error = {red = 255, green = 0},
}

function M.set(state)
  if state == current then return end
  local pattern = assert(patterns[state], 'LED state')
  current = state
  local applied = true
  for _, color in ipairs({'red', 'green'}) do
    local value = pattern[color]
    local ok
    if value == 'blink' then
      ok = write(color, 'trigger', 'timer') and write(color, 'delay_on', '500')
        and write(color, 'delay_off', '500')
    else
      ok = write(color, 'trigger', 'none') and write(color, 'brightness', tostring(value))
    end
    applied = applied and ok
  end
  print('LED state=' .. state .. ' applied=' .. tostring(applied))
end

return M
