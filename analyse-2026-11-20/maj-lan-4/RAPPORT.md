# Quatrième mise à jour LAN (v4) — lectures du chauffe-eau et du sèche-serviettes

Le 20 novembre 2026, la candidate v4 a été reconstruite après la seconde revue. Le banc ARM926 utilise un UART simulé, une NAND simulée et des services MQTT et SSH de test isolés sur la boucle locale. L’archive est destinée à une vérification hors ligne. Aucun essai sur la passerelle réelle ni déploiement n’a été effectué.

| Élément | Valeur |
|---|---|
| [Archive finale](../../analyse-2026-11-18/persistance-banque-a/phase2/applications/ct-20261120d.ctapp) | `ct-20261120d.ctapp`, 7 modules, 60 430 octets |
| SHA-256 | `1b3e4c30f96c04ee338a1ebde1f4f7e53cb7dbfe0c8560b097e999a48734c426` |
| Version | `v-1b3e4c30f96c` |
| [Archive examinée lors de la seconde revue](ct-20261120d-v-c6ca112e8cde.ctapp) | `v-c6ca112e8cde`, SHA-256 `c6ca112e8cdeb002e4398e3da12a5d63a477eb0ba1de7f750721edb59975d914` |
| [Archive examinée lors de la première revue](ct-20261120d-v-e1d10ab4c2c0.ctapp) | `v-e1d10ab4c2c0` |
| [Version précédente (v3)](../../analyse-2026-11-18/persistance-banque-a/phase2/applications/ct-20261120c.ctapp) | `v-5a15d3d38a81` |
| Journal de la suite principale (non publié) | `private-reads-v4-20261120.log` |

## Retrait des bornes après seconde revue

La v4 retire les requêtes d’état étendues de types 6 et 7, leur transaction UART, le filtre dédié aux réponses tardives et le calcul de la consigne en °C. Les clés `target_temp`, `target_temp_min` et `target_temp_max` sont absentes des états MQTT et de la découverte Home Assistant. Dans la candidate revue, le maximum ne partait jamais, donc la consigne calculée restait inconnue. La revue a également établi qu’un refus court tardif pouvait être traité comme une réponse MAIN_INFO et arrêter le service. L’étude de la consigne en °C reprendra lors d’un essai sur le matériel réel. [Seconde revue](REVUE-ASTRA-2.md)

Le service conserve la cible brute `target_raw` et le registre privé `0x0041`. Pour ce registre, deux ou trois octets renseignent la température minimale du mode manuel. Quatre octets renseignent aussi sa température maximale. Le test M2 couvre les longueurs de un à quatre octets.

La session UART et le module assemblé `uart.lua` sont identiques à v3 octet pour octet. MAIN_INFO conserve le codec, le délai UART de 8 s, l’ordre CETHI puis IC3 et le traitement des erreurs. La santé garde son budget de 95 s de session MQTT et son contrôle après les acquittements de disponibilité, de découverte et des deux états de la première paire. Le diff se trouve en annexe. Référence UART v3 (non publié) · Référence service v3 (non publié)

Les corrections I2 et I3 restent appliquées. Une coupure MQTT abandonne les valeurs et les lectures en attente de la série. Une paire MAIN_INFO arrivée à échéance passe dès la fin de la lecture éventuellement armée. Sous MQTT, les états de la série optionnelle sont publiés ensemble lorsque les 28 réponses ou délais sont traités.

La seconde revue a mesuré 3 595,6 s d’attente pour le premier état frais après une coupure de 3 s avec un intervalle de 3 600 s. La production utilise 60 s. Le service relance désormais une paire fraîche dès que la nouvelle connexion a acquitté la disponibilité et la découverte et que la transaction UART en cours a fini. Il republie à la réception de cette paire et fixe l’échéance suivante à partir de cette lecture. Le banc a mesuré **0,210 s** après le redémarrage du courtier à l’intervalle maximal. [Seconde revue](REVUE-ASTRA-2.md) · Essai à 3 600 s (non publié)

## Nouvelles entités Home Assistant par rapport à v3

| Appareil | Registre | Clés des nouvelles entités | Valeurs |
|---|---|---|---|
| Chauffe-eau (CETHI) | `0x0004` | `energy_total` | Énergie totale en Wh, compteur croissant |
| Chauffe-eau (CETHI) | `0x0041` | `manual_min_temp`, `manual_max_temp` | Températures minimale et maximale du mode manuel, °C, diagnostic |
| Sèche-serviettes (IC3) | `0x013d` | `drying_setting`, `drying_max` | Durée réglée et durée maximale de séchage, min |
| Sèche-serviettes (IC3) | `0x0115` | `ambient_temp` | Température ambiante, °C |
| Sèche-serviettes (IC3) | `0x0140` | `env_presence`, `env_lux`, `env_humidity`, `env_temp` | Présence, luminosité en lx, humidité en %, température en °C |
| Sèche-serviettes (IC3) | `0x0116` | `index_conso_raw` | Index de consommation brut en hexadécimal, diagnostic désactivé par défaut |

La v4 ajoute **11 entités**. Les clés de v3 gardent le même identifiant unique `<client>_<appareil>_<clé>`. Le test vérifie les unités, les classes, les composants désactivés par défaut et l’absence de sujet de commande. Les six registres ajoutés suivent les lectures v3 dans la liste de chaque appareil. La comparaison avec `v-c6ca112e8cde` confirme que les 28 définitions de registre et leurs décodeurs sont identiques. [Définitions et décodage](../../analyse-2026-11-18/persistance-banque-a/phase2/src/registers.lua)

| Découverte MQTT par appareil | CETHI | IC3 |
|---|---:|---:|
| Composants, v3 → v4 | 15 → 18 | 13 → 21 |
| JSON mesuré à 16 octets d’identifiant, 30 s | 4 300 octets | 4 755 octets |
| JSON mesuré à 48 octets d’identifiant, 3 600 s | 4 974 octets | 5 525 octets |

Les deux charges utiles restent sous le plafond de 6 144 octets. La découverte annonce une expiration égale à l’intervalle plus 45 s, soit 105 s en production. Mesure standard (non publié) · Mesure maximale (non publié)

## Demandes radio par cycle de 300 s

À connexion stable, la série privée démarre après la première paire publiée, puis toutes les `ceil(300 / interval_seconds)` paires si la série précédente est terminée. Une reconnexion remet ce compteur à zéro. Les chiffres sont des nombres nominaux de requêtes à cadence régulière.

| Demandes sur 300 s | v3 à 60 s | v4 à 60 s | v4 à 30 s |
|---|---:|---:|---:|
| MAIN_INFO `0x0100`, type 3 | 10 | 10 | 20 |
| Registres privés `0x0101`, accès `0x60` | 22 (12 + 10) | 28 (14 + 14) | 28 (14 + 14) |
| Statut étendu types 6 et 7 | 0 | 0 | 0 |
| **Total nominal** | **32** | **38** | **48** |

Les 28 lectures privées peuvent cumuler 140 s de délais UART si toutes expirent. Le service peut intercaler une paire MAIN_INFO entre deux lectures privées. Une seule transaction UART est active à la fois.

## Provenance des lectures de registre

Le script `scripts/catalogue.sh` produit `catalogue.txt`. Il reprend `catalog.py` et ajoute les numéros de ligne des états et des convertisseurs de `analyse-2026-11-17/lua/all/appsB/overkiz/io-homecontrol/lib/Overkiz/knowledge/io/devices.lua`, noté `devices.lua`. Les enregistrements GenericV2 viennent de `parite-ha-recherche/gateway-ids-all.txt` : chaque registre y est suivi de `bl 0x194bac`.

| Registre (raw id) | État OEM, ligne | Convertisseur, ligne | GenericV2 (`gateway-ids-all.txt`) |
|---|---|---|---|
| `0x0004` (201327617) | `core:ElectricEnergyConsumptionState`, `devices.lua:19103` | `slot0[199]` `readUInt32(1)`, `:1710` | l. 6, `0x1869e0` |
| `0x0041` (201343233) | `core:MinimalTemperatureManualModeState` `:18761` ; `core:MaximalTemperatureManualModeState` `:18737` | `slot0[289]` `#<2 → nil`, `readUInt16(1)/10`, `:2232` ; `slot0[287]` `#<4 → nil`, `readUInt16(3)/10`, `:2218` | l. 50, `0x18a058` |
| `0x013d` (201407745) | `io:DryingDurationUserParameterState` `:21835` ; `io:DryingDurationMaxState` `:21811` | `slot0[189]` `readUInt8(1)`, `:1676` ; `slot0[518]` `readUInt8(2)`, `:3620` | l. 124, `0x190a5c` (identifiant calculé) |
| `0x0115` (201397505) | `core:TemperatureState` (sous-appareil n° 7), `:19707` | `slot0[355]`, `:2676-2681` : `if readInt16(1,false) == -1 then return -1 else return readInt16(1,false)/100` | l. 95, `0x18d824` (identifiant calculé) |
| `0x0140` (201408513) | `core:OccupancyState` `:21871`, `core:LuminanceState` `:21883`, `core:RelativeHumidityState` `:21895`, `core:TemperatureState` `:21907` | `slot0[520]` `:3626`, `[521]` `readUInt16(2,false)` `:3633`, `[522]` `readUInt16(4,false)/10` `:3636`, `[523]` `readInt16(6,false)/10` `:3639` | l. 127, `0x190e0c` |
| `0x0116` (201397761) | **aucun état** dans le catalogue (`catalogue.txt`, section vide) | — | l. 96, `0x18d95c` |

Points vérifiés dans le code OEM :
- **Sentinelle de `0x0115` :** seul le brut −1 (`ff ff` en LE) est une sentinelle. L'OEM renvoie alors l'entier −1 au lieu de −0,01 °C. Nous publions null. Toute autre valeur négative est une vraie température : le test unitaire décode `ce ff` en −0,5 °C.
- **Présence de `0x0140` (`:3626-3631`) :** le code décompilé compare `slot1 == 1`, une variable non définie. C'est un artefact du décompilateur, et l'intention est `readUInt8(1) == 1`. Nous gardons 0 → `noPersonInside` (OFF), 1 → `personInside` (ON), et toute autre valeur → nil, comme l'OEM.
- **Positions de `0x0140` :** les positions 1, 2, 4 et 6 sont confirmées. La lecture la plus longue, i16 en 6, impose 7 octets au moins. Il n'existe aucune sentinelle pour la luminosité, l'humidité ou la température.
- **`0x0041`.** Le décodage suit les deux seuils du catalogue OEM. Un blob de 2 ou 3 octets renseigne le minimum. Le maximum reste inconnu jusqu'au quatrième octet.

## Vérifications hors ligne

Les contrôles LuaJIT ARM couvrent le chargement des sept modules, les 35 clés issues des 28 registres, les réponses courtes de `0x0041` et le test d’origine du codec MAIN_INFO. La session simulée vérifie les requêtes MAIN_INFO de type 3 pour les deux appareils, les refus de 16 et 20 octets, le délai dépassé et le reset STM32. La comparaison CTAPP1 confirme que seuls `service.lua` et `registers.lua` diffèrent de l’archive v3. Les empreintes de v3 et de `root.ubifs` sont vérifiées avant et après la suite.

Le banc contrôle chaque trame UART qu’il reçoit et échoue sur un statut étendu de type 6 ou 7. Le scénario `private` vérifie l’ordre des 28 lectures, le rejet d’une réponse portant un mauvais numéro de registre, un délai dépassé et un refus. Il contrôle les valeurs publiées, notamment `target_raw`, et l’absence des trois clés retirées dans l’état et la découverte.

La suite principale a réussi les huit scénarios (`EXIT_STATUS 0`) avec `CT_CANDIDATE_APP` pointant vers `ct-20261120d.ctapp`. Le banc sélectionne la candidate pour `private`, `late-broker` et `outage`. Les cinq autres scénarios conservent leurs variantes de référence. Journal de la suite (non publié)

| Scénario | Vérification |
|---|---|
| `private` | 28 registres lus ou traités, état complet et découverte des deux appareils. |
| `late-broker` | Attente de 110 s sans courtier, puis première paire, santé, compteur à 0 et promotion de `v-1b3e4c30f96c`. |
| `healthy` | Santé et compteur à 0. Le banc vérifie le pare-feu, le PTY SSH et le refus d’une mise à jour à l’empreinte erronée. |
| `outage` | Deux coupures pendant une lecture MAIN_INFO puis pendant un registre privé. La paire fraîche arrive 0,191 s après le second redémarrage du courtier à l’intervalle de 30 s. La série privée repart du premier registre. |
| `ota-fail` | Abandon de la version volontairement défectueuse avant le redémarrage unique, sans acquittement du compteur. |
| `ota-trial` | Promotion de la version d’essai après validation de la santé. `/apps` revient en lecture seule. |
| `term` | Fin de la lecture armée, restauration des paramètres UART, fermeture MQTT et compteur à 2. |
| `lwt` | État `offline` publié et conservé après `SIGKILL`. |

Les deux essais à 3 600 s, `private` et `outage`, ont réussi. Avec un intervalle de 30 s, `private-slow` laisse 14 registres sans réponse pendant 70,0 s. L’écart maximal observé entre lectures MAIN_INFO est de 31,141 s pour une expiration de 75 s. Essais à 3 600 s (non publié) · Essai de lectures lentes (non publié)

Le journal de v-c6ca112e8cde (non publié) conserve les résultats de la version examinée lors de la seconde revue. Les reproductions historiques des défauts de borne restent dans les journaux de régression (non publié) et les deux revues. [Première revue](REVUE-ASTRA.md) · [Seconde revue](REVUE-ASTRA-2.md)

## Annexe · Comparaison des sources avec v3

### `uart-session.lua`

```text
git diff --no-index -- uart-session-v3.lua.orig ../../analyse-2026-11-18/persistance-banque-a/phase2/src/uart-session.lua
```

La commande ne produit aucun diff et renvoie 0. Le contrôle `cmp` du script de construction donne le même résultat. [Source finale](../../analyse-2026-11-18/persistance-banque-a/phase2/src/uart-session.lua)

### `service.lua`

Les seuls écarts portent sur l’activation des entités, l’expiration MQTT et l’ordonnancement des séries. Le diff montre les lignes de contexte des lectures MAIN_INFO et de la santé. [Source finale](../../analyse-2026-11-18/persistance-banque-a/phase2/src/service.lua)

```diff
diff --git a/analyse-2026-11-20/maj-lan-4/service-v3.lua.orig b/analyse-2026-11-18/persistance-banque-a/phase2/src/service.lua
index e6b88e6..77c872a 100644
--- a/analyse-2026-11-20/maj-lan-4/service-v3.lua.orig
+++ b/analyse-2026-11-18/persistance-banque-a/phase2/src/service.lua
@@ -48,11 +48,11 @@ local labels = {'CETHI', 'IC3'}
 local function component(id, key, ha, enabled)
   local c = {p = ha.p, name = ha.name, uniq_id = id .. '_' .. key,
     val_tpl = "{{value_json.get('" .. key .. "')}}"}
   c.unit_of_meas, c.dev_cla, c.stat_cla, c.ent_cat, c.ops = ha.unit, ha.dev_cla, ha.stat_cla, ha.ent_cat, ha.ops
   if ha.p == 'binary_sensor' then c.pl_on, c.pl_off = 'ON', 'OFF' end
-  if enabled == false then c.en = false end
+  if enabled == false or ha.en == false then c.en = false end
   return c
 end
 local function discovery(index)
   local label = labels[index]
   local id = config.client_id .. '_' .. label:lower()
@@ -65,11 +65,12 @@ local function discovery(index)
   cmps.rssi_raw = component(id, 'rssi_raw', {p = 'sensor', name = 'Signal radio', unit = 'dBm',
     dev_cla = 'signal_strength', stat_cla = 'measurement', ent_cat = 'diagnostic'}, false)
   return json.encode({
     dev = {ids = {id}, name = 'Cozytouch ' .. label, mf = 'Atlantic'}, o = {name = 'cozytouch-hub'},
     stat_t = config.state_topics[index], avty_t = config.topic_prefix .. '/availability',
-    exp_aft = config.interval_seconds + 30, cmps = cmps
+    -- Allow for one optional read already in flight, two MAIN_INFO reads and two PUBACKs.
+    exp_aft = config.interval_seconds + 45, cmps = cmps
   })
 end
 
 local mqtt = MQTT.new(config, Net.transport(config), print)
 Led.set('working')
@@ -88,13 +89,13 @@ local ok, reason = pcall(function()
   uart = UART.open_session(targets, Net.now, device)
   local next_read, pending_publish = 0, false
   local pair, pair_connection = {}, nil
   local read_index, sequence = 1, 0
   local online, stopping, ack_done = false, false, false
-  -- Private registers: read after a published main pair, at most every 300 s, one at a time.
-  -- A failed private read only clears its values; it never stops the service.
+  -- An optional series starts after a published MAIN_INFO pair and yields to the next pair when due.
   local details, main = {{}, {}}, {}
+  local main_connection, private_details
   local private_queue, pairs_done = {}, 0
   local private_every = math.max(1, math.ceil(300 / config.interval_seconds))
   local function state_payload(i)
     local out = {}
     for key, value in pairs(main[i]) do out[key] = value end
@@ -114,10 +115,16 @@ local ok, reason = pcall(function()
       print('HEALTH_TIMEOUT connected_seconds=' .. health_budget)
       terminal_code, stopping = 31, true
     end
     if stopping and not uart.active and uart.stage ~= 'revision' then break end
     mqtt:step(now)
+    if main_connection and (mqtt.state ~= 'ready' or main_connection ~= mqtt.connections) then
+      -- Finish an armed UART read, but discard everything acquired on the old connection.
+      main_connection, private_details = nil, nil
+      private_queue, pairs_done, details, main = {}, 0, {{}, {}}, {}
+      next_read = 0
+    end
     local result = uart:step(stopping)
     if uart.ready and not online and not stopping then
       online = true
       mqtt:set_availability('online')
     end
@@ -125,17 +132,21 @@ local ok, reason = pcall(function()
       local label = labels[result.index]
       local blob = result.data and result.data.blob or ''
       print(string.format('PRIVATE_RESULT index=%d register=0x%04x status=%s bytes=%d', result.index,
         result.target_index, result.status, #blob))
       if result.status == 'RESET_CONTEXT_LOST' then terminal_code = 33; break end
-      local values = result.status == 'DONE' and Registers.decode(label, result.target_index, blob) or {}
-      for _, f in ipairs(Registers.allowed[label][result.target_index].fields) do
-        local value = values[f.key]
-        if value == nil then value = json.null end
-        details[result.index][f.key] = value
+      if private_details then
+        local values = result.status == 'DONE' and Registers.decode(label, result.target_index, blob) or {}
+        for _, f in ipairs(Registers.allowed[label][result.target_index].fields) do
+          local value = values[f.key]
+          if value == nil then value = json.null end
+          private_details[result.index][f.key] = value
+        end
       end
-      if #private_queue == 0 and mqtt.state == 'ready' and not stopping and main[1] and main[2] then
+      if private_details and #private_queue == 0 and not stopping then
+        details = private_details
+        private_details = nil
         for i, topic in ipairs(config.state_topics) do mqtt:set(topic, state_payload(i), false) end
         pending_publish, pair_connection = true, mqtt.connections
         print('PRIVATE_PUBLISHED')
       end
     elseif result then
@@ -153,31 +164,33 @@ local ok, reason = pcall(function()
           remaining_time_raw = d.remaining_time_raw, origin_raw = d.origin, rssi_raw = d.rssi,
           observed_monotonic_ms = math.floor(Net.now() * 1000), sequence = sequence
         }
         if result.index == 2 then
           main = {pair[1], pair[2]}
+          main_connection = pair_connection
           for i, topic in ipairs(config.state_topics) do mqtt:set(topic, state_payload(i), false) end
           pending_publish, read_index = true, 1
           next_read = Net.now() + config.interval_seconds
-          if pairs_done % private_every == 0 then
+          if not private_details and pairs_done % private_every == 0 then
+            private_details = {{}, {}}
             for i, label in ipairs(labels) do
               for _, r in ipairs(Registers.devices[label]) do private_queue[#private_queue + 1] = {i, r.index} end
             end
           end
           pairs_done = pairs_done + 1
         else
           read_index = 2
         end
       else
-        pair, read_index, next_read = {}, 1, Net.now() + config.interval_seconds
+        pair, read_index, next_read = {}, 1, 0
       end
     end
     local ready = online and mqtt.state == 'ready'
       and mqtt.acknowledged[config.topic_prefix .. '/availability'] == 'online'
       and has_current_ack(config.discovery_topics[1]) and has_current_ack(config.discovery_topics[2])
     if pending_publish and (mqtt.state ~= 'ready' or pair_connection ~= mqtt.connections) then
-      pending_publish, read_index, next_read = false, 1, Net.now() + config.interval_seconds
+      pending_publish, read_index, next_read = false, 1, 0
     end
     if ready and pending_publish and has_current_ack(config.state_topics[1])
         and has_current_ack(config.state_topics[2]) and not stopping then
       pending_publish = false
       if not ack_done then
@@ -187,21 +200,22 @@ local ok, reason = pcall(function()
         print('HEALTH_OK counter_ack=verified')
       end
     end
     Led.set((ready and ack_done and not pending_publish) and 'ok' or 'working')
     if read_index == 2 and (not ready or pair_connection ~= mqtt.connections) then
-      pair, read_index, next_read = {}, 1, Net.now() + config.interval_seconds
+      pair, read_index, next_read = {}, 1, 0
     end
-    if not stopping and ready and not pending_publish and not uart.active and #private_queue > 0 then
-      local item = table.remove(private_queue, 1)
-      uart:start_private(item[1], item[2])
-      uart.active.target_index = item[2]
-    elseif not stopping and ready and not pending_publish and not uart.active
-        and (read_index == 2 or Net.now() >= next_read) then
-      if read_index == 1 then pair, pair_connection = {}, mqtt.connections end
-      uart:start(read_index)
-      print('READ_ARMED index=' .. read_index)
+    if not stopping and ready and not pending_publish and not uart.active then
+      if read_index == 2 or Net.now() >= next_read then
+        if read_index == 1 then pair, pair_connection = {}, mqtt.connections end
+        uart:start(read_index)
+        print('READ_ARMED index=' .. read_index)
+      elseif #private_queue > 0 then
+        local item = table.remove(private_queue, 1)
+        uart:start_private(item[1], item[2])
+        uart.active.target_index = item[2]
+      end
     end
     Net.pause()
   end
   if terminal_code == 0 and not ack_done then terminal_code = 31 end
 end)
```

## Déploiement, 20 novembre 2026 vers 12 h 48 (heure de Paris), autorisé par <PERSONNE> (« oui! »)

- **Installation :** `UPDATE_STAGED version=v-1b3e4c30f96c files=7`.
- **Redémarrage et essai :** `ct-update reboot`, puis `HEALTHY=yes` à 21 secondes de fonctionnement. Ensuite : `current=v-1b3e4c30f96c`, `previous=v-5a15d3d38a81`.
- **Contrôle par abonné MQTT en lecture seule** (`sub-states.ps1`) :
  - configurations : chauffe-eau, 18 composants et 4 217 octets ; sèche-serviettes, 21 composants et 4 656 octets ;
  - comparaison avec Overkiz :

| Valeur | Hub | Référence | Verdict |
|---|---|---|---|
| `ambient_temp` (`0x0115`) | 18,5 °C | Overkiz 18,5 °C (19 nov.) | identique |
| `drying_setting` (`0x013d`) | 90 min (max 120) | Overkiz 90 | identique |
| `energy_total` (`0x0004`) | 4 161 579 Wh | Overkiz 4 159 092 Wh (19 nov.) | +2 487 Wh = hausse exacte de `hp_index` (3 782 → 6 269) |
| `index_conso_raw` (`0x0116`) | `04af` | Overkiz 1098 (19 nov.) | 0x04af = 1199 en gros-boutiste : candidat cohérent (compteur, +101 en un jour) ; à confirmer par un second relevé |
| `manual_min_temp` / `manual_max_temp` (`0x0041`) | null | — | pas de réponse ou blob trop court |
| `env_*` (`0x0140`) | présence OFF, 0 lx, 100 %, 0 °C | — | valeurs suspectes : capteur absent ou valeurs sentinelles probables |

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
