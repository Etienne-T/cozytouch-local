# Cozytouch / Overkiz Local Control Analysis

Date: 2026-04-06
Workspace: `.`

## Objective

Document the current Atlantic Cozytouch installation, determine whether the two devices can be controlled without the vendor cloud, explain what prevents local-only control, and outline realistic technical alternatives.

## Questions Investigated

1. Can the two devices be controlled without the cloud connection?
2. If not, what prevents local control?
3. If not, what are the realistic solutions?
4. Can the devices be controlled without the gateway entirely?

## Local Installation Context

### Gateway

- Product: old Cozytouch bridge
- Manual present locally: `Notice_Bridge_COZYTOUCH_Sauter.pdf (not published)`
- Bridge ID: `<NUMERO_BRIDGE>`
- IP: `<IP_HUB>`
- MAC: `<MAC_HUB>`

### Devices

- `ASAMA`
  - Type reported in Home Assistant / Overkiz model mapping: `AtlanticElectricalTowelDryer`
  - Firmware: `E725008`
- Atlantic domestic hot water unit
  - Type reported in Home Assistant / Overkiz model mapping: `DomesticHotWaterProduction`
  - Firmware: `E722804`

### Current Software Stack

- Home Assistant integration: Overkiz
  - <https://www.home-assistant.io/integrations/overkiz>
- Home Assistant source:
  - <https://github.com/home-assistant/core/tree/dev/homeassistant/components/overkiz>
- Python library used by the integration:
  - <https://github.com/iMicknl/python-overkiz-api>

## Summary Conclusion

With the current Atlantic Cozytouch bridge and these devices, the practical answer is:

- Home Assistant control is currently cloud-dependent.
- There is no evidence of a supported local LAN API for this Cozytouch bridge.
- The two devices are most likely controlled behind the bridge over proprietary sub-GHz radio rather than directly over IP.
- Native full-feature control from Home Assistant without the bridge is not realistically available with the current setup.
- Manual control on the appliances themselves remains available even when internet access is lost.

## What Was Done

### 1. Reviewed the local bridge manual

The local PDF `Notice_Bridge_COZYTOUCH_Sauter.pdf (not published)` was treated as the primary hardware reference for the installed bridge.

Relevant findings from the manual:

- The bridge requires Ethernet connection to the home router.
- The status LED distinguishes internet connected vs not connected.
- The manual explicitly says an internet connection is required for installation.
- Pairing and setup are performed through the Cozytouch application.
- The bridge has radio functionality on `868.25 MHz`, `868.95 MHz`, and `869.85 MHz`.
- `PROG` and `RESET` are present physically, but the manual says they have no action in the Cozytouch app at that time.

Interpretation:

- This old bridge behaves like a network uplink plus proprietary radio gateway.
- The documentation does not expose any local HTTP, HTTPS, MQTT, or other user-facing LAN control interface.

### 2. Probed the bridge on the local network

The following read-only checks were run against `<IP_HUB>`.

Connectivity:

- ICMP ping succeeded. The bridge is reachable on the LAN.

TCP service checks:

- Port `22`: closed
- Port `53`: closed
- Port `80`: closed
- Port `443`: closed
- Port `8080`: closed
- Port `8443`: closed
- Port `1883`: closed
- Port `8883`: closed

Interpretation:

- The bridge is alive on the LAN but does not expose the usual local control/API ports checked during this analysis.
- In particular, `8443` being closed matters because Somfy local API hubs expose their developer-mode API there.
- This does not mathematically prove there is no hidden local interface, but it strongly argues against a supported local LAN API on this bridge.

### 3. Cross-checked Home Assistant and upstream API support

#### Home Assistant Overkiz documentation

Source:

- <https://www.home-assistant.io/integrations/overkiz>

Important findings:

- The integration supports both cloud API and local API.
- The local API is documented as available only for some Somfy hubs.
- Supported hubs page explicitly marks local API support for:
  - Somfy Connexoon IO
  - Somfy Connexoon RTS
  - Somfy TaHoma v2
- Atlantic Cozytouch is listed as a supported hub in general, but not as a hub with local API availability.
- Home Assistant also documents that if a device works through the cloud API but not the local API, that can be an inherent limitation of the local API.

Interpretation:

- Home Assistant supports Atlantic Cozytouch through Overkiz cloud.
- Home Assistant local Overkiz mode is not documented as available for Atlantic Cozytouch bridges.

#### Upstream `pyoverkiz` library

Source:

- <https://github.com/iMicknl/python-overkiz-api>

Important findings:

- The library supports Atlantic Cozytouch as a cloud server family.
- The README includes a local API example, but the example is specifically for `Somfy TaHoma (local)`.
- The local example points to `https://<gateway>:8443/enduser-mobile-web/1/enduserAPI/`.
- The local example requires a token generated from Somfy Developer Mode.

Interpretation:

- The upstream library clearly supports local mode for Somfy developer-enabled hubs.
- It does not provide evidence that an Atlantic Cozytouch bridge exposes the same local API.

#### Official Somfy local API documentation

Source:

- <https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode>

Important findings:

- Somfy local control requires enabling Developer Mode in the Somfy app.
- The gateway then exposes a local HTTPS API.
- Discovery uses mDNS `_kizboxdev._tcp`.
- Authentication uses bearer tokens.
- The documented local endpoint is intended for TaHoma developer-enabled gateways.

Interpretation:

- There is a documented local Overkiz-family API, but it is explicitly a Somfy TaHoma developer-mode feature.
- No equivalent official Cozytouch bridge developer-mode documentation was found during this analysis.

### 4. Cross-checked Atlantic vendor documentation

Sources:

- <https://www.atlantic.fr/aide/cozytouch/fonctionnement/pourquoi-y-a-t-il-besoin-d-une-box-pour-piloter-des-produits-connectes-avec-cozytouch>
- <https://www.atlantic.fr/aide/cozytouch/fonctionnement/quel-est-le-protocole-de-communication-entre-les-produits>
- <https://www.atlantic.fr/aide/cozytouch/fonctionnement/peut-on-piloter-les-appareils-connectes-sans-cozytouch>
- <https://www.atlantic.fr/aide/cozytouch/fonctionnement/a-quoi-sert-le-bridge-cozytouch>

Important findings:

- Atlantic explains the app communicates via a server.
- Atlantic states that permanent internet connectivity is required for remote control.
- Atlantic states many products use `IO Homecontrol`, especially radiators and towel dryers.
- Atlantic states `IO Homecontrol` products require the additional Cozytouch bridge.
- Atlantic also states newer product families are increasingly moving to Wi-Fi or Zigbee, but that is a product-family trend, not evidence that this installed setup is locally controllable.
- Atlantic states that without Cozytouch you lose the remote connected-product functions.

Interpretation:

- Atlantic describes the system as server-mediated rather than LAN-local.
- The towel dryer category aligns with `IO Homecontrol + bridge`.
- The current installation should be treated as bridge-mediated radio control with cloud orchestration.

## Diagnosis

## 1. Can the two devices be controlled without the cloud connection?

### Through the current Home Assistant Overkiz integration

No, not in any supported way identified here.

Reasoning:

- Home Assistant local Overkiz mode targets only some Somfy hubs.
- The Atlantic Cozytouch bridge is not documented as a local API hub.
- The bridge does not expose common local API ports on the LAN.

### Directly from the devices themselves

Yes, but only through their local physical controls.

Reasoning:

- Loss of cloud/internet does not imply the appliances stop functioning.
- It only removes app / Home Assistant / remote orchestration capabilities.

## 2. What is preventing cloud-free HA control?

Several distinct constraints exist.

### A. The bridge does not appear to expose a supported local IP API

- No official Atlantic Cozytouch developer-mode API was found.
- The old bridge manual gives no sign of a local control API.
- Local probing found no exposed API service on the most likely ports.

### B. The devices are behind a radio gateway, not first-class LAN devices

- The bridge manual shows sub-GHz radio operation at `868.x MHz`.
- That implies Home Assistant is not talking directly to the towel dryer or hot-water appliance over IP.
- Instead, the bridge is the translator between the network side and the appliance side.

### C. The vendor ecosystem is architected around cloud mediation

- Atlantic documentation explicitly describes the app as communicating through a server.
- This is consistent with many Overkiz-family cloud deployments.

### D. Even where Overkiz local APIs exist, they are not universally available across hub families

- Somfy TaHoma developer mode is official and documented.
- Atlantic Cozytouch local developer mode was not found.

## 3. Can the devices be controlled without the gateway entirely?

### Native protocol path

Probably not in a practical, supported sense.

Reasoning:

- The devices appear to rely on the bridge for the radio/protocol translation layer.
- There is no evidence in this analysis that Home Assistant can speak to the devices directly over IP.

### Manual control path

Yes.

Reasoning:

- Users can still operate the devices locally at the appliance controls.

### Custom hardware bypass path

Potentially yes, but only by replacing or bypassing the Cozytouch control path.

Reasoning:

- If the appliance exposes a compatible physical control input, Home Assistant can control that input instead of the original radio ecosystem.

## Realistic Solution Paths

## Option 1. Keep the current cloud path

Description:

- Continue using Home Assistant `Overkiz -> Atlantic Cozytouch bridge -> devices`.

Pros:

- No hardware changes.
- Full compatibility with the currently supported integration path.

Cons:

- Internet dependency remains.
- Vendor cloud remains a control-plane dependency.

## Option 2. Replace the control path with local hardware automation

Description:

- Bypass Cozytouch for automation and drive the appliances through local electrical interfaces when supported by the hardware.

Examples:

- Towel dryer:
  - `fil pilote`
  - dry contact
  - relay control through ESPHome / Shelly / similar local-first hardware
- Hot water production:
  - contactor control
  - boost/eco input
  - dry-contact input if supported by the model

Pros:

- Fully local Home Assistant control is achievable.
- No vendor cloud required.
- Operationally robust once implemented correctly.

Cons:

- Usually gives only coarse control, not full vendor feature parity.
- May lose telemetry, vendor modes, schedules, and device-native semantics.
- Requires model-specific electrical validation and safe installation practices.

Assessment:

- This is the most realistic path if the goal is local-first automation rather than preserving every Cozytouch feature.

## Option 3. Reverse engineer the current bridge/device protocol

Description:

- Investigate the existing system deeply enough to reproduce control without the cloud.

Possible work items:

- Capture bridge outbound traffic to identify cloud endpoints and authentication flow.
- Inspect whether the bridge uses pinned TLS, mutual TLS, or application-level crypto.
- Perform mDNS and full port discovery from a less restricted host.
- Attempt firmware extraction from the bridge.
- Use SDR tools to inspect `868 MHz` traffic.
- Study pairing/authentication between bridge and devices.
- Implement a custom translator or Home Assistant integration if enough protocol details are recovered.

Pros:

- Could preserve more native functionality if successful.
- Technically interesting.

Cons:

- Highest effort by far.
- Likely blocked by encryption, pairing secrets, proprietary protocol details, or bridge firmware hardening.
- No guarantee of success.

Assessment:

- This is viable as a research project, not as a quick practical fix.

## Option 4. Replace the gateway or product family with local-first equipment

Description:

- Migrate away from Cozytouch/Overkiz cloud dependence entirely.

Possible targets:

- Zigbee devices integrated directly in Home Assistant
- Matter-capable devices
- HomeKit devices supported by Home Assistant HomeKit Controller
- Products with documented LAN APIs
- Industrial-style devices exposing Modbus or dry contacts

Pros:

- Strongest long-term local-control story.
- Better interoperability with Home Assistant.

Cons:

- Costly.
- May require partial appliance replacement or connectivity-module replacement.

Assessment:

- Best long-term architecture if local control is a strict requirement.

## Why a Somfy TaHoma Local API Swap Is Not a Safe Assumption

A tempting idea is to replace only the bridge with a Somfy gateway that supports developer mode.

Why this is uncertain:

- The existence of Somfy local API support does not prove your Atlantic devices can be paired to a Somfy developer-capable hub.
- Even if pairing were possible, device-class support may be incomplete.
- This analysis found no primary-source evidence proving that these two specific Atlantic devices can be moved to a Somfy local API path with preserved functionality.

Conclusion:

- This should be treated as speculative until validated against hardware compatibility data or real pairing tests.

## Best Current Diagnosis Per Device

### `ASAMA` towel dryer (`AtlanticElectricalTowelDryer`)

Most likely situation:

- Uses `IO Homecontrol` through the Cozytouch bridge.
- Cloud-free Home Assistant control is not available through the current vendor stack.
- Best non-cloud path is likely local electrical control if the model offers an appropriate interface.

### Domestic hot water production (`DomesticHotWaterProduction`)

Most likely situation:

- Currently enrolled behind the bridge in the Overkiz/Cozytouch ecosystem.
- There is no evidence from this investigation that it exposes a direct local API in the current installation.
- Best non-cloud path is likely model-specific electrical integration if suitable control inputs exist.

Note:

- Atlantic has newer Wi-Fi-connected water heater families, but that does not imply this installed unit can be detached from the bridge and controlled locally over the LAN.

## Confidence Level

High confidence:

- The current Home Assistant setup is cloud-dependent.
- The old Cozytouch bridge does not expose a supported local API on the common ports checked.
- Atlantic documentation positions this ecosystem as server-mediated.

Medium confidence:

- Full native local control is not realistically available for these devices with the current bridge.

Lower confidence / not fully ruled out:

- An undocumented local service on an unusual port.
- A hidden maintenance interface.
- A bridge or device exploit / reverse-engineered path not covered by vendor documentation.

These lower-confidence possibilities exist in theory, but they should be treated as research hypotheses rather than practical solutions.

## Practical Recommendation

If the goal is to stop depending on vendor cloud infrastructure, the realistic paths are:

1. Replace the control path with local electrical automation per appliance.
2. Replace the appliance/connectivity ecosystem with local-first hardware.
3. Treat full protocol reverse engineering as a separate R&D project, not as the primary operational plan.

## Suggested Next Technical Steps

If continuing the investigation, the next useful steps would be:

1. Identify the exact appliance references and electrical control interfaces for both devices.
2. Determine whether each unit exposes `fil pilote`, dry contact, booster input, tariff input, or another externally controllable interface.
3. Decide whether the goal is:
   - full native feature parity, or
   - reliable local automation with reduced feature scope.
4. If pursuing reverse engineering:
   - run a full `nmap` scan from a host with unrestricted network access
   - inspect ARP, DHCP, mDNS, and DNS behavior of the bridge
   - capture bridge outbound traffic at the router
   - check whether TLS interception is possible
   - inspect radio traffic around `868.25`, `868.95`, and `869.85 MHz`

## Source List

Primary and near-primary sources used during this investigation:

- Home Assistant Overkiz documentation:
  - <https://www.home-assistant.io/integrations/overkiz>
- Home Assistant Overkiz source tree:
  - <https://github.com/home-assistant/core/tree/dev/homeassistant/components/overkiz>
- `pyoverkiz` upstream library:
  - <https://github.com/iMicknl/python-overkiz-api>
- Somfy TaHoma Developer Mode:
  - <https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode>
- Atlantic FAQ about required box / internet:
  - <https://www.atlantic.fr/aide/cozytouch/fonctionnement/pourquoi-y-a-t-il-besoin-d-une-box-pour-piloter-des-produits-connectes-avec-cozytouch>
- Atlantic FAQ about communication protocols:
  - <https://www.atlantic.fr/aide/cozytouch/fonctionnement/quel-est-le-protocole-de-communication-entre-les-produits>
- Atlantic FAQ about use without Cozytouch:
  - <https://www.atlantic.fr/aide/cozytouch/fonctionnement/peut-on-piloter-les-appareils-connectes-sans-cozytouch>
- Atlantic FAQ about the bridge:
  - <https://www.atlantic.fr/aide/cozytouch/fonctionnement/a-quoi-sert-le-bridge-cozytouch>
- Local manual present in this workspace:
  - `Notice_Bridge_COZYTOUCH_Sauter.pdf (not published)`

## Final Answer

For this installation, the current Atlantic Cozytouch bridge should be treated as a cloud-managed radio gateway rather than a local API appliance. The installed devices do not appear to be directly locally controllable over IP via Home Assistant, and the gateway itself does not expose a supported local API surface in the way Somfy developer-mode gateways do. If local-first control is the requirement, the practical choices are either hardware-level retrofit per appliance or migration to a more open connectivity stack.

---

# Ecosystem Progress Scan

Date of scan: 2026-04-06

## Objective

This section documents the current public state of discussion and progress around the two practical non-cloud paths identified earlier:

1. Appliance-level local retrofit
2. Reverse engineering the Cozytouch / Overkiz / io-homecontrol stack

The goal is not to collect every mention of Cozytouch online, but to answer a narrower question:

- Is there active work in these areas?
- How mature is each path today?
- Is there already a practical route for hardware similar to this installation?

## Executive Summary

There is real public progress on both paths, but the maturity is very different.

### Retrofit path

Status: active and practical

- For heaters and towel dryers, the community path is centered on `fil pilote` and related electrical-control retrofits rather than replacing the Cozytouch radio protocol.
- For Atlantic domestic hot water equipment, there are active projects that intercept internal serial communication and expose local MQTT.
- This path is the most realistic route to cloud-free Home Assistant control today.

### Reverse engineering path

Status: technically active, but still research-grade for Atlantic Cozytouch

- There is serious protocol-level work around `io-homecontrol`.
- There are older but still relevant gateway-rooting writeups for Cozytouch / KizBox / Connexoon class hardware.
- However, no finished and broadly adopted local-first Home Assistant path was found for an Atlantic Cozytouch bridge controlling Atlantic devices like those in this installation.

## Option 1 Status: Appliance-Level Local Retrofit

## 1A. Towel dryer / heater control via `fil pilote`

### What is being discussed publicly

There is sustained Home Assistant community activity around replacing vendor-connected heating control with `fil pilote` hardware.

Representative discussions found:

- Home Assistant Community:
  - <https://community.home-assistant.io/t/fil-pilote-easy-interface/106286>
- Home Assistant Communauté Francophone:
  - <https://forum.hacf.fr/t/cozytouch-atlantic-et-seche-serviettes/61666>
  - <https://forum.hacf.fr/t/nodon-fil-pilote-seche-serviette-communication-z2m-ok-pas-de-commande/70912>
  - <https://forum.hacf.fr/t/gestion-fil-pilote-radiateur/72838>
  - <https://forum.hacf.fr/t/extinction-materiel-zigbee-equation-fil-pilote/36936>

### What these discussions indicate

- The community is not waiting for Atlantic or Overkiz to become local-first.
- For compatible heaters, the practical recommendation is often to bypass the connected ecosystem and control the heating mode electrically.
- Zigbee `fil pilote` modules are actively used and discussed.
- The main work is no longer "is this possible?" but rather:
  - which module behaves best
  - how many pilot-wire modes are supported
  - how to map those modes cleanly into Home Assistant
  - how model-specific edge cases behave in real installations

### Relevance to your `ASAMA` towel dryer

This is the strongest practical alternative for the towel dryer side.

Important caveat:

- It depends on the exact electrical interface exposed by the model.
- A towel dryer may support classic pilot-wire modes but still keep some appliance-specific functions local to the device, such as timed drying or blower behavior.

### Maturity assessment

High for basic local control.

Meaning:

- There is enough public adoption to call this a proven direction.
- It is not equivalent to a full local replacement of Cozytouch feature parity.
- It is instead a robust path to local climate-mode control.

## 1B. Domestic hot water local control projects

### Main project found

- AquaMQTT:
  - <https://github.com/tspopp/AquaMQTT>

### Main associated discussion

- HAcF thread:
  - <https://forum.hacf.fr/t/integration-dun-chauffe-eau-atlantic-explorer-en-mqtt/40493?page=19>

### What AquaMQTT does

The project does not localize Cozytouch itself. Instead, it inserts a microcontroller between the user interface controller and the main controller of compatible DHW heat pumps, decodes the internal serial traffic, and republishes telemetry/control via MQTT.

The project states compatibility or reported compatibility with several Groupe Atlantic families, including:

- Atlantic Explorer
- Atlantic Calypso
- Sauter Pagosa Green
- Thermor Aeromax

### Current status signal

The HAcF discussion remained active into:

- 2025-12-07
- 2026-01-14

The January 14, 2026 activity includes discussion around `Thermor Aeromax Access`, which suggests the project is still being actively evaluated and extended rather than abandoned.

### Relevance to your domestic hot water device

This is potentially relevant if your hot-water unit is architecturally similar to the supported or community-tested Atlantic/Thermor families.

Important caveats:

- AquaMQTT is not a generic solution for every Atlantic water heater.
- Compatibility depends on the internal controller family and the serial protocol being close enough to the known ones.
- This is a hardware-hacking path, not a simple integration install.

### Maturity assessment

Medium.

Meaning:

- This is no longer just a concept.
- There is a real implementation and active community iteration.
- But it remains model-family dependent and requires invasive wiring/interception work.

## Option 2 Status: Reverse Engineering the Cozytouch / Overkiz / io-homecontrol Stack

## 2A. Protocol-level reverse engineering: `io-homecontrol`

### Main project found

- `iown-homecontrol`:
  - <https://github.com/Velocet/iown-homecontrol>

### Observed status

At the time of review, the repository shows:

- 175 commits
- 251 stars
- open issues and pull requests
- documented radio and link-layer material
- command-layer documentation
- implementation work for microcontroller-based tooling

The project's own status section still marks substantial parts as incomplete or work in progress, including:

- higher protocol layers
- 1-way library implementation
- 2-way library implementation
- missing actuator firmware samples
- higher-level abstraction work

### Why this matters

This is the clearest evidence that the protocol is not impenetrable. Public reverse engineering has advanced beyond speculation:

- radio characteristics are documented
- frame structure work exists
- toolchains exist for experimentation
- low-cost hardware targets exist

The project also aligns closely with the radio frequencies found in the local Cozytouch bridge manual:

- `868.25 MHz`
- `868.95 MHz`
- `869.85 MHz`

### Relevance to your setup

This is highly relevant at the research level because it confirms the bridge/device side is part of an actively studied ecosystem.

However, it does not currently provide:

- a polished Home Assistant integration for Atlantic Cozytouch local control
- a finished drop-in replacement for your bridge
- a turnkey path for your two devices

### Maturity assessment

Medium for protocol research, low for turnkey user outcome.

## 2B. Gateway rooting / local API recovery efforts

### Cozytouch / KizBox rooting writeups

Relevant material found:

- Benjamin Lafois Cozytouch series:
  - <https://www.lafois.com/tag/cozytouch/>

Notable parts of that work:

- The Cozytouch bridge is identified as a KizBox Mini class gateway.
- Internal system access was obtained.
- Internal services and DBus interactions were investigated.
- The existence of local API-related components was identified.
- The project encountered persistence and operational limitations; it did not become a finished end-user local-control solution.

### Somfy gateway work

Relevant material found:

- Unauthorized Access blog:
  - <https://blog.unauthorizedaccess.nl/2021/04/07/no-clouds-just-sunshine.html>
- Somfy TaHoma Developer Mode:
  - <https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode>

What this tells us:

- Somfy-class Overkiz hardware was sufficiently close to enable both unofficial hacking and eventually an official local API on supported products.
- Home Assistant later adopted that official Somfy local API path.

### Relevance to Atlantic Cozytouch

This is encouraging from a family-architecture perspective, but it does not solve the Atlantic case directly.

Why:

- Atlantic Cozytouch still does not expose the same documented official local API path found for some Somfy hubs.
- The existence of rooting writeups shows the platform can be studied, not that it is solved.

### Maturity assessment

Low to medium.

Meaning:

- Valuable for researchers.
- Not yet an operational recommendation for ordinary deployment.

## What Was Not Found

Several things would have materially changed the recommendation, and none were found during this scan:

- An official Atlantic Cozytouch developer-mode local API
- A maintained Home Assistant local integration specifically for Atlantic Cozytouch bridge local control
- A finished custom bridge replacement project widely reported as working for Atlantic towel dryers and Atlantic DHW devices through `io-homecontrol`
- Strong evidence that your exact Atlantic device classes can simply be moved onto a Somfy local API gateway with preserved functionality

## Additional Relevant Finding: Alternate Atlantic Cloud Integration

A separate custom Home Assistant integration exists for a different Atlantic cloud ecosystem:

- `gduteil/cozytouch`
  - <https://github.com/gduteil/cozytouch>

Why it matters:

- It includes tested support mentions such as `Sauter Asama Connecté II Ventilo`.
- That suggests Atlantic has more than one connectivity stack depending on product generation/family.

Why it does not change the core conclusion:

- It remains cloud-based.
- It does not provide an offline local-control path for the old bridge setup analyzed in this document.

## Ranked Practicality For This Installation

Based on the current public ecosystem state, the options rank as follows for your setup.

### 1. Towel dryer: electrical retrofit via `fil pilote` or equivalent

Practicality: highest

Reason:

- The community path is mature.
- The outcome is local-first.
- The engineering risk is manageable if the exact model supports the expected electrical interface.

### 2. Hot water unit: internal bus interception if the controller family matches known projects

Practicality: moderate

Reason:

- There is visible project activity and some Atlantic-family success.
- Compatibility risk is much higher than with `fil pilote`.
- The implementation is more invasive.

### 3. Full Cozytouch / bridge / io-homecontrol reverse engineering for end-user control

Practicality: low for operations, high for research value

Reason:

- There is meaningful protocol progress.
- There is no evidence of a finished general solution for this Atlantic bridge and these devices.

### 4. Waiting for an official Atlantic local API

Practicality: very low

Reason:

- No evidence was found that such a path is emerging for the old Cozytouch bridge family.

## Recommendation Update

The ecosystem scan strengthens the earlier conclusion:

- If the goal is a practical local-first outcome, retrofit is the route with the strongest current momentum.
- If the goal is protocol archaeology and platform liberation, there is enough public reverse-engineering progress to justify further work, but it should be treated as R&D rather than an immediate solution.

For your exact installation, the best next step remains:

1. identify the exact electrical control interfaces of the towel dryer and hot-water unit
2. determine whether the hot-water unit belongs to a controller family already touched by AquaMQTT or similar work
3. only pursue full bridge/protocol reverse engineering if the research value itself is part of the goal

## Sources For This Section

- `fil pilote` and community retrofit discussions:
  - <https://community.home-assistant.io/t/fil-pilote-easy-interface/106286>
  - <https://forum.hacf.fr/t/cozytouch-atlantic-et-seche-serviettes/61666>
  - <https://forum.hacf.fr/t/nodon-fil-pilote-seche-serviette-communication-z2m-ok-pas-de-commande/70912>
  - <https://forum.hacf.fr/t/gestion-fil-pilote-radiateur/72838>
  - <https://forum.hacf.fr/t/extinction-materiel-zigbee-equation-fil-pilote/36936>
- AquaMQTT:
  - <https://github.com/tspopp/AquaMQTT>
  - <https://forum.hacf.fr/t/integration-dun-chauffe-eau-atlantic-explorer-en-mqtt/40493?page=19>
- `io-homecontrol` reverse engineering:
  - <https://github.com/Velocet/iown-homecontrol>
- Cozytouch rooting / gateway hacking:
  - <https://www.lafois.com/tag/cozytouch/>
  - <https://blog.unauthorizedaccess.nl/2021/04/07/no-clouds-just-sunshine.html>
- Alternate Atlantic cloud integration:
  - <https://github.com/gduteil/cozytouch>
