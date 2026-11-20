-- Closed allowlist of Atlantic private registers read with GenericV2 READ (access 0x60).
-- Sources (offline, 20 November 2026; v3 corrections: analyse-2026-11-20/maj-lan-3/RAPPORT.md):
--   catalogue io/devices.lua, CETHI V4 component slot4[604] and IC3 component: state names and converters;
--   Daemon.so appsB: every index below is registered through the GenericV2 wrapper (ELF 0x194bac);
--   capture 17 November (sonde 0x001a): request 07 04 0c 60 <index BE>, reply 0x040c 0c 60 <index> <blob>.
-- Positions are 1-based in the reply blob, like the OEM ByteArray. Big-endian unless the OEM converter
-- reads with `false` (little-endian: the IC3 temperatures). READ only: no write path exists here.
local M = {}

local function u8(b, i) return b:byte(i) end
local function i8(b, i) local v = b:byte(i); return v >= 128 and v - 256 or v end
local function u16be(b, i) return b:byte(i) * 256 + b:byte(i + 1) end
local function i16be(b, i) local v = u16be(b, i); return v >= 32768 and v - 65536 or v end
local function u16le(b, i) return b:byte(i + 1) * 256 + b:byte(i) end
local function i16le(b, i) local v = u16le(b, i); return v >= 32768 and v - 65536 or v end
local function u32be(b, i) return u16be(b, i) * 65536 + u16be(b, i + 2) end
local function tenth(v) return math.floor(v + 0.5) / 10 end -- v is an integer count of 0.1 units
local function hundredth(v) return v / 100 end -- v is an integer count of 0.01 units
local function hex(b) return (b:gsub('.', function(c) return string.format('%02x', c:byte()) end)) end

-- Each register: index, minimum blob size, and fields {key, decode(blob), optional minimum size}.
-- Each field has a Home Assistant component (p, name, and optional unit/class/category).
local C = '°C'
M.devices = {
  CETHI = {
    {index = 0x0017, size = 2, fields = {
      {key = 'water_temp', decode = function(b) return tenth(i16be(b, 1)) end,
       ha = {p = 'sensor', name = "Température de l'eau (milieu)", unit = C, dev_cla = 'temperature', stat_cla = 'measurement'}}}},
    {index = 0x0003, size = 4, fields = {
      {key = 'hp_hours', decode = function(b) return u16be(b, 1) end,
       ha = {p = 'sensor', name = 'Fonctionnement pompe à chaleur', unit = 'h', dev_cla = 'duration', stat_cla = 'total_increasing', ent_cat = 'diagnostic'}},
      {key = 'elec_hours', decode = function(b) return u16be(b, 3) end,
       ha = {p = 'sensor', name = 'Fonctionnement appoint électrique', unit = 'h', dev_cla = 'duration', stat_cla = 'total_increasing', ent_cat = 'diagnostic'}}}},
    -- 0x0033 io:PowerHeatElectricalState, 0x0034 io:PowerHeatPumpState: Wh counters on 16 bits (wrap at 65536).
    -- Evidence (maj-lan-3/RAPPORT.md): from the 17 Nov OEM cache to Overkiz on 19 Nov, the delta of the u32 total
    -- 0x0004 (core:ElectricalEnergyInWh) equals delta(0x0033) + delta(0x0034 mod 65536): 8727 = 2445 + 6282.
    -- Keys kept from v2 so the Home Assistant unique_id stays the same. total_increasing: a wrap is a new cycle.
    {index = 0x0033, size = 2, fields = {
      {key = 'elec_index', decode = function(b) return u16be(b, 1) end,
       ha = {p = 'sensor', name = 'Énergie appoint électrique', unit = 'Wh', dev_cla = 'energy', stat_cla = 'total_increasing'}}}},
    {index = 0x0034, size = 2, fields = {
      {key = 'hp_index', decode = function(b) return u16be(b, 1) end,
       ha = {p = 'sensor', name = 'Énergie pompe à chaleur', unit = 'Wh', dev_cla = 'energy', stat_cla = 'total_increasing'}}}},
    {index = 0x0006, size = 1, fields = {
      {key = 'dhw_mode', decode = function(b)
         local v = u8(b, 1)
         return v == 0 and 'autoMode' or v == 1 and 'manualEcoActive' or v == 2 and 'manualEcoInactive' or nil
       end,
       ha = {p = 'sensor', name = 'Mode eau chaude', dev_cla = 'enum', ops = {'autoMode', 'manualEcoActive', 'manualEcoInactive'}}}}},
    {index = 0x0000, size = 1, fields = {
      {key = 'boost_days', decode = function(b) return i8(b, 1) end,
       ha = {p = 'sensor', name = 'Durée du boost', unit = 'd', dev_cla = 'duration'}}}},
    {index = 0x0005, size = 1, fields = {
      {key = 'away_days', decode = function(b) local v = u8(b, 1); return v == 255 and 'toujours' or tostring(v) end,
       ha = {p = 'sensor', name = "Durée d'absence (jours)"}}}},
    {index = 0x0001, size = 2, fields = {
      {key = 'water_litres', decode = function(b) return u16be(b, 1) end,
       ha = {p = 'sensor', name = "Consommation d'eau", unit = 'L', dev_cla = 'water', stat_cla = 'total'}}}},
    -- 0x0031 core:V40WaterVolumeEstimationState (OEM module ECS.V40ConsumEst): plain readUInt16(1), no scale in
    -- the OEM code. 11000 on the hub is impossible in litres for a 250 L tank: published as a raw index.
    -- Key kept from v2 (unique_id); its name is historical, the value has no unit.
    {index = 0x0031, size = 2, fields = {
      {key = 'v40_litres', decode = function(b) return u16be(b, 1) end,
       ha = {p = 'sensor', name = 'V40 eau chaude (index brut)', stat_cla = 'measurement', ent_cat = 'diagnostic'}}}},
    {index = 0x001a, size = 2, fields = {
      {key = 'air_in_temp', decode = function(b) return tenth(i16be(b, 1)) end,
       ha = {p = 'sensor', name = 'Sonde air entrant', unit = C, dev_cla = 'temperature', stat_cla = 'measurement', ent_cat = 'diagnostic'}}}},
    {index = 0x001b, size = 2, fields = {
      {key = 'evap_low_temp', decode = function(b) return tenth(i16be(b, 1)) end,
       ha = {p = 'sensor', name = 'Sonde évaporateur bas', unit = C, dev_cla = 'temperature', stat_cla = 'measurement', ent_cat = 'diagnostic'}}}},
    {index = 0x001c, size = 2, fields = {
      {key = 'evap_high_temp', decode = function(b) return tenth(i16be(b, 1)) end,
       ha = {p = 'sensor', name = 'Sonde évaporateur haut', unit = C, dev_cla = 'temperature', stat_cla = 'measurement', ent_cat = 'diagnostic'}}}},
    -- v4 (analyse-2026-11-20/maj-lan-4/RAPPORT.md). 0x0004 core:ElectricEnergyConsumptionState, converter
    -- slot0[199] readUInt32(1) (devices.lua:19103, :1710), core:ElectricalEnergyInWh: the u32 total that
    -- Overkiz shows as ballon_eau_chaude_consommation (4 159 092 Wh on 19 November). No 16-bit wrap.
    {index = 0x0004, size = 4, fields = {
      {key = 'energy_total', decode = function(b) return u32be(b, 1) end,
       ha = {p = 'sensor', name = 'Énergie totale', unit = 'Wh', dev_cla = 'energy', stat_cla = 'total_increasing'}}}},
    -- 0x0041 core:MinimalTemperatureManualModeState readUInt16(1)/10 and core:MaximalTemperatureManualModeState
    -- readUInt16(3)/10 (devices.lua:18761, :18737; converters :2232, :2218). Manual-mode limits.
    {index = 0x0041, size = 2, fields = {
      {key = 'manual_min_temp', decode = function(b) return tenth(u16be(b, 1)) end,
       ha = {p = 'sensor', name = 'Température minimale (mode manuel)', unit = C, dev_cla = 'temperature', ent_cat = 'diagnostic'}},
      {key = 'manual_max_temp', size = 4, decode = function(b) return tenth(u16be(b, 3)) end,
       ha = {p = 'sensor', name = 'Température maximale (mode manuel)', unit = C, dev_cla = 'temperature', ent_cat = 'diagnostic'}}}},
  },
  IC3 = {
    {index = 0x0136, size = 1, fields = {
      {key = 'mode', decode = function(b)
         local v = u8(b, 1)
         return v == 0 and 'standby' or v == 1 and 'auto' or v == 2 and 'internal' or 'external'
       end,
       ha = {p = 'sensor', name = 'Mode', dev_cla = 'enum', ops = {'standby', 'auto', 'internal', 'external'}}}}},
    {index = 0x0137, size = 2, fields = {
      {key = 'effective_setpoint', decode = function(b) return tenth(u16le(b, 1)) end,
       ha = {p = 'sensor', name = 'Consigne effective', unit = C, dev_cla = 'temperature', stat_cla = 'measurement'}}}},
    {index = 0x0138, size = 2, fields = {
      {key = 'comfort_setpoint', decode = function(b) return tenth(u16le(b, 1)) end,
       ha = {p = 'sensor', name = 'Consigne confort', unit = C, dev_cla = 'temperature', stat_cla = 'measurement'}}}},
    {index = 0x0104, size = 2, fields = {
      {key = 'eco_lowering', decode = function(b) return tenth(u16le(b, 1)) end,
       ha = {p = 'sensor', name = 'Abaissement éco', unit = C, stat_cla = 'measurement'}}}},
    {index = 0x011d, size = 2, fields = {
      {key = 'derogated_setpoint', decode = function(b) return tenth(u16le(b, 1)) end,
       ha = {p = 'sensor', name = 'Consigne de dérogation', unit = C, dev_cla = 'temperature', stat_cla = 'measurement', ent_cat = 'diagnostic'}}}},
    -- 0x013a core:BoostModeDurationState (OEM module SSV.TempoBoostSsv, read every 10 min) and 0x013c
    -- io:DryingDurationState (SSV.TempoSechageSsv): running timers, 0 outside a boost or a drying cycle.
    -- 0x013b (SSV.ParametragesBoostSsv, read once a day): user setting @1, maximum @2 (converters 189 and 518).
    -- 0x013d (SSV.ParametragesSechageSsv): same layout for drying. It IS registered GenericV2 with a computed
    -- id (0x0D01 + 0x0c000000 + 0x13000, Daemon.so 0x190a40-0x190a74, call 0x194bac; parite-ha-recherche).
    {index = 0x013a, size = 1, fields = {
      {key = 'boost_minutes', decode = function(b) return u8(b, 1) end,
       ha = {p = 'sensor', name = 'Durée restante du boost', unit = 'min', dev_cla = 'duration'}}}},
    {index = 0x013b, size = 2, fields = {
      {key = 'boost_setting', decode = function(b) return u8(b, 1) end,
       ha = {p = 'sensor', name = 'Durée du boost (réglage)', unit = 'min', dev_cla = 'duration'}},
      {key = 'boost_max', decode = function(b) return u8(b, 2) end,
       ha = {p = 'sensor', name = 'Durée maximale du boost', unit = 'min', dev_cla = 'duration', ent_cat = 'diagnostic'}}}},
    {index = 0x013c, size = 1, fields = {
      {key = 'drying_minutes', decode = function(b) return u8(b, 1) end,
       ha = {p = 'sensor', name = 'Durée restante du séchage', unit = 'min', dev_cla = 'duration'}}}},
    {index = 0x013e, size = 1, fields = {
      {key = 'temporary_state', decode = function(b)
         local v = u8(b, 1)
         return v == 0 and 'permanentHeating' or v == 1 and 'boost' or v == 2 and 'drying' or nil
       end,
       ha = {p = 'sensor', name = 'État temporaire', dev_cla = 'enum', ops = {'permanentHeating', 'boost', 'drying'}}}}},
    {index = 0x013f, size = 1, fields = {
      {key = 'occupancy', decode = function(b) return u8(b, 1) ~= 0 and 'ON' or 'OFF' end,
       ha = {p = 'binary_sensor', name = 'Présence', dev_cla = 'occupancy'}}}},
    -- v4. 0x013d io:DryingDurationUserParameterState readUInt8(1), io:DryingDurationMaxState readUInt8(2)
    -- (devices.lua:21835, :21811; converters :1676, :3620).
    {index = 0x013d, size = 2, fields = {
      {key = 'drying_setting', decode = function(b) return u8(b, 1) end,
       ha = {p = 'sensor', name = 'Durée du séchage (réglage)', unit = 'min', dev_cla = 'duration'}},
      {key = 'drying_max', decode = function(b) return u8(b, 2) end,
       ha = {p = 'sensor', name = 'Durée maximale du séchage', unit = 'min', dev_cla = 'duration', ent_cat = 'diagnostic'}}}},
    -- 0x0115 core:TemperatureState of sub-device #7 (ECL.TemperatureAmbianteLocale): readInt16(1, false)/100,
    -- and the raw value -1 is returned as the sentinel -1 (devices.lua:19707, converter :2676-2681): null here.
    {index = 0x0115, size = 2, fields = {
      {key = 'ambient_temp', decode = function(b) local v = i16le(b, 1); if v == -1 then return nil end; return hundredth(v) end,
       ha = {p = 'sensor', name = 'Température ambiante', unit = C, dev_cla = 'temperature', stat_cla = 'measurement'}}}},
    -- 0x0140 SSV.EtatCapteurEnvironnementauxSsv (sub-devices #2-#5, devices.lua:21871-21918, converters
    -- :3626-3641): occupancy readUInt8(1) 0 = noPersonInside, 1 = personInside, other = nil; luminance
    -- readUInt16(2, false); humidity readUInt16(4, false)/10; temperature readInt16(6, false)/10. No sentinel.
    {index = 0x0140, size = 7, fields = {
      {key = 'env_presence', decode = function(b) local v = u8(b, 1); return v == 0 and 'OFF' or v == 1 and 'ON' or nil end,
       ha = {p = 'binary_sensor', name = "Présence (capteur d'environnement)", dev_cla = 'occupancy',
        ent_cat = 'diagnostic', en = false}},
      {key = 'env_lux', decode = function(b) return u16le(b, 2) end,
       ha = {p = 'sensor', name = 'Luminosité', unit = 'lx', dev_cla = 'illuminance', stat_cla = 'measurement',
        ent_cat = 'diagnostic', en = false}},
      {key = 'env_humidity', decode = function(b) return tenth(u16le(b, 4)) end,
       ha = {p = 'sensor', name = 'Humidité', unit = '%', dev_cla = 'humidity', stat_cla = 'measurement',
        ent_cat = 'diagnostic', en = false}},
      {key = 'env_temp', decode = function(b) return tenth(i16le(b, 6)) end,
       ha = {p = 'sensor', name = "Température (capteur d'environnement)", unit = C, dev_cla = 'temperature',
        stat_cla = 'measurement', ent_cat = 'diagnostic', en = false}}}},
    -- 0x0116 ECL.IndexConso: no converter in the local catalogue, decoding unknown. Raw blob as lowercase hex,
    -- diagnostic and disabled by default, to compare with the Overkiz consumption (1098).
    {index = 0x0116, size = 1, fields = {
      {key = 'index_conso_raw', decode = function(b) return hex(b) end,
       ha = {p = 'sensor', name = 'IndexConso (brut, hexadécimal)', ent_cat = 'diagnostic', en = false}}}},
  },
}

M.allowed = {}
for label, registers in pairs(M.devices) do
  M.allowed[label] = {}
  for _, r in ipairs(registers) do
    assert(not M.allowed[label][r.index], 'duplicate register')
    M.allowed[label][r.index] = r
  end
end

-- Decode one reply blob. A short blob gives no value (nil), never a guess.
function M.decode(label, index, blob)
  local r = assert(M.allowed[label] and M.allowed[label][index], 'register not allowed')
  local out = {}
  if #blob >= r.size then
    for _, f in ipairs(r.fields) do
      if #blob >= (f.size or r.size) then out[f.key] = f.decode(blob) end
    end
  end
  return out
end

-- Every value key of a device (for clearing stale values).
function M.keys(label)
  local keys = {}
  for _, r in ipairs(M.devices[label]) do
    for _, f in ipairs(r.fields) do keys[#keys + 1] = f.key end
  end
  return keys
end

function M.celsius(centikelvin)
  return (centikelvin - 27315) / 100
end

-- OEM fromRawTemperatureValue: interpolate on 0..51200 and round to a tenth of a degree.
function M.setpoint(raw, minimum, maximum)
  if raw and raw >= 0 and raw <= 51200 then
    local c = M.celsius(raw * (maximum - minimum) / 51200 + minimum)
    return math.floor(c * 10 + 0.5) / 10
  end
end

return M
