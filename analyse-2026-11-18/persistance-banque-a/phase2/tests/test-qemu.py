#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
from pathlib import Path
import pty
import queue
import re
import secrets
import select
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time

if os.environ.get("COZYTOUCH_QEMU_NETNS") != "1":
    os.execvp("unshare", ["unshare", "--net", "--", "sh", "-c",
              'ip link set lo up && exec env COZYTOUCH_QEMU_NETNS=1 python3 "$@"',
              "cozytouch-netns", str(Path(__file__).resolve()), *sys.argv[1:]])
assert {name for _, name in socket.if_nameindex()} == {"lo"}, "QEMU host must have loopback only"

here = Path(__file__).resolve().parent
work = Path(sys.argv[1]).resolve()
limit_scenarios = ["limits-mismatch", "limits-missing", "limits-duplicate", "limits-late",
                   "limits-inverted", "limits-guard", "limits-unexpected",
                   "limits-equal", "limits-low", "limits-high", "limits-outage"]
all_scenarios = ["healthy", "wrong-revision", "term", "outage", "lwt", "passive", "reset", "alias", "pulse-refused",
                 "ota-trial", "ota-fail", "late-broker-v4", "late-broker", "private", "private-slow",
                 "diag-bornes", "regular-refusal", *limit_scenarios]
candidate_scenarios = {"late-broker", "private", "outage", "private-slow", "regular-refusal", *limit_scenarios}
# late-broker-v4: factory application of root A v4 (negative control, expected to give up at 95 s).
# late-broker: candidate application (CT_CANDIDATE_APP archive, or built from ../src) staged as a trial.
lab_flags = {"alias": " ct_lab_alias", "pulse-refused": " ct_lab_pulse_fail",
             "ota-trial": " ct_lab_apps=ota", "ota-fail": " ct_lab_apps=otafail", "late-broker": " ct_lab_apps=late",
             **{name: " ct_lab_apps=late" for name in candidate_scenarios}}
late_broker_delay = 110
scenarios = sys.argv[2:] or all_scenarios
assert set(scenarios) <= set(all_scenarios)
max_discovery = os.environ.get("CT_DISCOVERY_MAX") == "1"
assert not max_discovery or set(scenarios) <= {"private", "outage"}, "max discovery fixture requires private or outage"
client_id = "x" * 48 if max_discovery else "synthetic-arm926"
interval = 3600 if max_discovery else 30
prefix = "cozytouch/" + client_id


def wait_port(port):
    until = time.monotonic() + 5
    while time.monotonic() < until:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("broker did not start")


def start_broker(config, port):
    server = subprocess.Popen(["mosquitto", "-c", config], stderr=subprocess.DEVNULL)
    try:
        wait_port(port)
    except BaseException:
        server.terminate()
        server.wait()
        raise
    return server


def mqtt_connect(port, user, password):
    conn = socket.create_connection(("127.0.0.1", port), timeout=3)
    def mqtt_string(value):
        return struct.pack(">H", len(value)) + value.encode()
    body = b"\0\4MQTT\x04\xc2\0\20" + b"".join(map(mqtt_string, ("audit", user, password)))
    conn.sendall(bytes([0x10, len(body)]) + body)
    with conn:
        data = conn.makefile("rb")
        return data.read(4)


def crc(payload):
    value = 0
    for byte in payload:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ (7 if value & 128 else 0)) & 255
    return value


def uart_frame(identifier, payload):
    return struct.pack(">BHH", 2, identifier, len(payload) + 1) + payload + bytes([crc(payload), 3])


def uart_receive(stream, identifier, *, diag_type=None):
    head = stream.read(5)
    assert len(head) == 5, "UART frame header"
    start, actual_identifier, size = struct.unpack(">BHH", head)
    assert start == 2 and 1 <= size <= 128, "unexpected outgoing UART header"
    body = stream.read(size + 1)
    assert len(body) == size + 1 and body[-1] == 3 and body[-2] == crc(body[:-2])
    payload = body[:-2]
    if actual_identifier == 0x0100 and len(payload) >= 37 and payload[34:36] == b"\x01\x03":
        if diag_type is None:
            assert payload[36] not in (6, 7), f"forbidden extended status type {payload[36]}"
        else:
            assert payload[36] == diag_type, "unexpected diagnostic status type"
    assert actual_identifier in (identifier if isinstance(identifier, tuple) else (identifier,)), (
        f"unexpected outgoing UART command {actual_identifier:#06x}, expected {identifier}")
    return payload


def uart_reply(stream, payload, expected_index, target_raw=200):
    assert len(payload) == 39 and payload[34:] == b"\1\3\3\0\0", "only MAIN_INFO READ"
    assert payload[:6] == bytes.fromhex("010203040506" if expected_index == 1 else "010203070809")
    return uart_frame(0x010d, b"\xff\xff\xff\xa0" + payload[3:6] + payload[:3] +
                      bytes([0, 150, 0, 4, 5, 0]) + struct.pack(">HH", target_raw, 201) + bytes([0, 0, 0, 0, 0, 1, 0, 0]))


def diagnostic_bornes(guest, ssh, normal_read):
    script = (here.parent / "diag/bornes-diag.lua").read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(script).hexdigest()
    copied = subprocess.run(ssh + ["cat > /run/ct/bornes-diag.lua && sha256sum /run/ct/bornes-diag.lua"],
                            input=script, capture_output=True, timeout=10, check=True)
    assert copied.stdout.decode().split()[0] == digest
    run = 'app=$(cat /run/ct/app-dir) && test -n "$app" && LUA_PATH="$app/?.lua" luajit /run/ct/bornes-diag.lua'
    rejected = subprocess.run(ssh + [run], capture_output=True, text=True, timeout=10)
    assert rejected.returncode == 1
    assert rejected.stdout.splitlines() == ["DIAG_ERROR etape=service", "DIAG_DONE restored=true"]
    # Le service du banc est le fils de supervise. TERM laisse le service relire termios.
    stop = r"""
app=$(cat /run/ct/app-dir) || exit 1
expected=$(printf 'luajit\000%s/service.lua\000--run\000' "$app" | hexdump -v -e '1/1 "%02x"')
supervisor=$(printf '/bin/sh\000/usr/libexec/ct/supervise\000' | hexdump -v -e '1/1 "%02x"')
for process in /proc/[0-9]*; do
    [ "$(cat "$process/comm" 2>/dev/null)" = luajit ] || continue
    [ "$(hexdump -v -e '1/1 "%02x"' "$process/cmdline" 2>/dev/null)" = "$expected" ] || continue
    parent=$(awk '/^PPid:/ {print $2}' "$process/status") || continue
    [ "$(hexdump -v -e '1/1 "%02x"' "/proc/$parent/cmdline" 2>/dev/null)" = "$supervisor" ] || continue
    kill -TERM "${process##*/}" && exit 0
done
exit 1
"""
    subprocess.run(ssh + [stop], capture_output=True, timeout=10, check=True)
    guest.wait("UART_CLEANUP restored=true")
    guest.wait("SUPERVISOR_HOLD")
    held = subprocess.run(ssh + ["exec 4<>/dev/ttyAMA1; " + run], capture_output=True, text=True, timeout=10)
    assert held.returncode == 1
    assert held.stdout.splitlines() == ["DIAG_ERROR etape=proprietaire_uart", "DIAG_DONE restored=true"]
    before = len(guest.history)
    process = subprocess.Popen(ssh + [run], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # Le lanceur SSH ne journalise pas la pulsation dans la console du banc.
        assert select.select([process.stdout], [], [], 10)[0], "pulsation de diagnostic absente"
        pulse = process.stdout.readline()
        assert pulse.strip() == "RADIO_PULSE low_ms=35 restored=true lab", pulse
        guest.radio.sendall(uart_frame(0x050e, b"\x01") + uart_frame(0x0403, b"\4"))
        assert uart_receive(guest.stream, 0x0500) == b"\0"
        guest.radio.sendall(uart_frame(0x0500, b"\0v2.4.2"))
        context = bytes.fromhex("d4e5f6a7") + normal_read[3:6] + normal_read[:3]
        last_master = bytes.fromhex("ab9e7d")
        ack = context + bytes.fromhex("00960004050082eb0000")
        main = uart_reply(guest.stream, normal_read, 1)[5:-2]
        main = context + main[10:22] + last_master + main[25:]
        previous = None
        for index, kind in enumerate((3, 7, 6, 7, 3), 1):
            request = uart_receive(guest.stream, 0x0100, diag_type=kind)
            sent = time.monotonic()
            assert request == normal_read[:36] + bytes([kind]) + normal_read[37:], "diagnostic CETHI only"
            assert previous is None or sent - previous >= 9.8, "window and pause before next request"
            previous = sent
            if kind == 3:
                guest.radio.sendall(uart_frame(0x010d, main))
            elif kind == 7:
                guest.radio.sendall(uart_frame(0x010d, ack))
                if index == 2:
                    short_refusal = context + bytes.fromhex("009600040809")
                    echo = context + b"\xaa" + normal_read[:34] + b"\xbb"
                    guest.radio.sendall(uart_frame(0x010d, short_refusal) + uart_frame(0x040c, echo))
        stdout, stderr = process.communicate(timeout=16)
        assert process.returncode == 0 and not stderr, stdout + stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
    guest.drain()
    assert not any("SERVICE_LAUNCH " in line or "REBOOT_NOW" in line for line in guest.history[before:])
    guest.radio.settimeout(0.25)
    try:
        assert not guest.stream.read(1), "extra UART command after diagnostic"
    except TimeoutError:
        pass

    diagnostic = [line for line in stdout.splitlines() if line.startswith("DIAG_")]
    logged = subprocess.run(ssh + ["cat /run/ct/bornes-diag.txt"], text=True, capture_output=True,
                            timeout=10, check=True).stdout.splitlines()
    assert diagnostic == logged
    assert diagnostic[0] == "DIAG_READY revision=2.4.2" and diagnostic[-1] == "DIAG_DONE restored=true"
    assert [line for line in diagnostic if line.startswith("DIAG_REQUEST ")] == [
        f"DIAG_REQUEST requete={i} type={kind} cible=CETHI ctx=<ctx>"
        for i, kind in enumerate((3, 7, 6, 7, 3), 1)
    ]
    assert [line for line in diagnostic if line.startswith("DIAG_WINDOW ")] == [
        f"DIAG_WINDOW requete={i} type={kind} trames={count}"
        for i, (kind, count) in enumerate(((3, 1), (7, 3), (6, 0), (7, 1), (3, 1)), 1)
    ]
    frames = []
    for line in diagnostic:
        if line.startswith("DIAG_FRAME "):
            match = re.fullmatch(r"DIAG_FRAME requete=(\d+) type=\d+ t=(\d+\.\d{3}) phase=attente (.+)", line)
            assert match and 0 <= float(match[2]) <= 8, line
            frames.append((int(match[1]), match[3]))
    reference = "id=0x010d longueur=28 ctx=<ctx> cethi=oui statut=05 detail=00 suite=00960004050000c800c90000<ctx>010000"
    maximum = "id=0x010d longueur=20 ctx=<ctx> cethi=oui statut=05 detail=00 suite=00960004050082eb0000 centiemes_kelvin=33515 celsius=62.00"
    assert frames == [
        (1, reference), (2, maximum),
        (2, "id=0x010d longueur=16 ctx=<ctx> cethi=oui statut=08 detail=09 suite=009600040809"),
        (2, "id=0x040c longueur=46 ctx=<ctx> cethi=- statut=- detail=- suite=aa<ctx>bb"),
        (4, maximum), (5, reference),
    ], frames
    for secret in (context[:4], normal_read[:3], normal_read[3:6], normal_read[18:34], last_master):
        assert secret.hex() not in stdout and secret.hex() not in "\n".join(logged)
    print("DIAG_PRECONDITIONS service actif et autre propriétaire UART refusés", flush=True)
    print("DIAG_SCRIPT_SHA256 " + digest, flush=True)
    print("\n".join(diagnostic), flush=True)
    print("DIAG_BORNES trames et masquage vérifiés, journal identique à stdout", flush=True)


# A distinctive raw MAIN_INFO value checks that it still reaches MQTT unchanged.
TARGET_RAW = dict.fromkeys(candidate_scenarios, 51200)
LIMIT_KEYS = {"target_temp", "setpoint_min", "setpoint_max"}
OBSOLETE_LIMIT_KEYS = {"target_temp_min", "target_temp_max"}
ENV_KEYS = {"env_presence", "env_lux", "env_humidity", "env_temp"}


def assert_limits(values, target_temp=None):
    assert OBSOLETE_LIMIT_KEYS.isdisjoint(values)
    if target_temp is None:
        assert LIMIT_KEYS.isdisjoint(values), values
    else:
        assert values["setpoint_min"] == 20 and values["setpoint_max"] == 62, values
        assert values["target_temp"] == target_temp, values


def limit_reply(request, centikelvin):
    # Captured payload after RSSI and addresses (substituted by synthetic context).
    context = b"\xff\xff\xff\xa0" + request[3:6] + request[:3]
    return uart_frame(0x010d, context + bytes.fromhex("008e00040500") + struct.pack(">H", centikelvin) + b"\0\0")


def limits_exchange(guest, scenario):
    failure = {
        "limits-mismatch": "INCONSISTENT_VALUES",
        "limits-inverted": "INCONSISTENT_VALUES",
        "limits-equal": "INCONSISTENT_VALUES",
        "limits-low": "INCONSISTENT_VALUES",
        "limits-high": "INCONSISTENT_VALUES",
        "limits-missing": "TIMEOUT",
        "limits-duplicate": "UNEXPECTED_ACK",
        "limits-guard": "UNEXPECTED_ACK",
        "limits-late": "UNEXPECTED_ACK",
        "limits-unexpected": "UNEXPECTED_ACK",
    }.get(scenario)
    fixture = {
        "limits-mismatch": (33515, 29315, 33415),
        "limits-inverted": (29315, 33515, 29315),
        "limits-equal": (33515, 33515, 33515),
        "limits-low": (33515, 27314, 33515),
        "limits-high": (37316, 29315, 37316),
        "limits-missing": (33515, None),
        "limits-duplicate": (33515, 29315),
        "limits-unexpected": (33515,),
    }.get(scenario, (33515, 29315, 33515))
    last_reply = last_sent = None
    for kind, value, delay in zip((7, 6, 7), fixture, (0.073, 0.075, 0.072)):
        request = uart_receive(guest.stream, 0x0100, diag_type=kind)
        sent_at = time.monotonic()
        assert request[:6] == bytes.fromhex("010203040506")
        assert len(request) == 39 and request[34:] == bytes((1, 3, kind, 0, 0))
        if last_reply is not None:
            pause = sent_at - last_reply
            assert pause >= 0.45, f"limit requests not spaced: {pause:.3f}s"
            assert sent_at - last_sent >= 0.98, "less than one second between limit requests"
        last_sent = sent_at
        if value is None:
            break
        time.sleep(delay)
        reply = limit_reply(request, value)
        if scenario == "limits-unexpected":
            payload = reply[5:-2]
            guest.radio.sendall(uart_frame(0x010d, payload[:-1] + b"\1"))
        last_reply = time.monotonic()
        guest.radio.sendall(reply)
        if scenario == "limits-duplicate" and kind == 6:
            guest.radio.sendall(reply)
    if scenario == "limits-guard":
        time.sleep(0.25)
        guest.radio.sendall(reply)
    if scenario == "limits-late":
        time.sleep(1.7)
        last_reply = time.monotonic()
        guest.radio.sendall(limit_reply(request, 29315))

    state = subscribe(*port_for_private, f"{prefix}/cethi/state", fresh=True)
    # The first post-guard request must be the first private read and no retry.
    first_private = uart_receive(guest.stream, 0x0101)
    elapsed = time.monotonic() - (sent_at if value is None else last_reply)
    assert elapsed >= (10.8 if value is None else 1.8), f"short guard: {elapsed:.3f}s"
    marker = "LIMITS_UNAVAILABLE reason=" + failure if failure else "LIMITS_ACCEPTED"
    guest.wait(marker)
    if failure:
        assert not select.select([state.stdout], [], [], 0.15)[0], "unexpected MQTT state after rejected limits"
        state.terminate()
        state.communicate(timeout=5)
    else:
        values = json.loads(read_subscriber(state)[0])
        assert values["target_raw"] == 51200
        assert_limits(values, 62.0)
    assert sum(line.startswith("LIMIT_ARMED ") for line in guest.history) == len(fixture)
    print(f"LIMITS_RESULT {scenario}: {marker}; guard={elapsed:.3f}s; first private read after guard", flush=True)
    return first_private


def limits_followup(guest, scenario, first_private, initial):
    states = [subscribe(*port_for_private, f"{prefix}/{label}/state", fresh=True) for label in ("cethi", "ic3")]
    for position, (index, register, blob) in enumerate(PRIVATE_FIXTURE):
        request = first_private if position == 0 else uart_receive(guest.stream, 0x0101)
        private_reply(guest, request, index, register, "" if blob is None else blob)
    guest.wait("PRIVATE_PUBLISHED")
    for state in states:
        values = json.loads(read_subscriber(state)[0])
        assert_limits(values)
    if scenario in ("limits-late", "limits-missing"):
        states = [subscribe(*port_for_private, f"{prefix}/{label}/state", fresh=True) for label in ("cethi", "ic3")]
        guest.radio.settimeout(38)
        first = uart_receive(guest.stream, 0x0100)
        guest.radio.sendall(uart_reply(guest.stream, first, 1, 25600))
        guest.radio.sendall(uart_reply(guest.stream, uart_receive(guest.stream, 0x0100), 2, 23456))
        for i, state in enumerate(states):
            values = json.loads(read_subscriber(state)[0])
            assert values["status"] == "DONE" and values["target_raw"] == (25600, 23456)[i]
            assert values["sequence"] > initial[i]["sequence"]
            assert_limits(values)
        print(f"LIMITS_FOLLOWUP {scenario}: fresh regular pair; no limit retry", flush=True)
    guest.drain()
    assert not any("SERVICE_EXIT" in line for line in guest.history)


# Private register exchange (scenario "private"): order of src/registers.lua, synthetic blobs.
# None = no reply (TIMEOUT), "access" = reply with a non-READ access code (DEVICE_ERROR).
PRIVATE_FIXTURE = [
    (1, 0x0017, "021d00000000"), (1, 0x0003, "22b40057"), (1, 0x0033, "67ae"), (1, 0x0034, "0ec6"),
    (1, 0x0006, "00"), (1, 0x0000, "00"), (1, 0x0005, "access"), (1, 0x0001, None), (1, 0x0031, "2af8"),
    (1, 0x001a, "00d8ffec017f"), (1, 0x001b, "ffecff840248"), (1, 0x001c, "00"),
    # v4: CETHI total energy (4 159 092 Wh) and manual-mode limits (50.0 / 62.0 °C).
    (1, 0x0004, "003f7674"), (1, 0x0041, "01f4026c"),
    (2, 0x0136, "01"), (2, 0x0137, "d200"), (2, 0x0138, "aa00"), (2, 0x0104, "2300"), (2, 0x011d, "0000"),
    (2, 0x013a, "00"), (2, 0x013b, "1478"), (2, 0x013c, "5a"), (2, 0x013e, "00"), (2, 0x013f, "01"),
    # v4: IC3 drying setting 90 / 240, ambient 18.50 °C (i16 LE /100), environment sensor (presence 1,
    # 150 lx, 54.5 %, 18.5 °C, LE) and IndexConso raw blob.
    (2, 0x013d, "5af0"), (2, 0x0115, "3a07"), (2, 0x0140, "0196002102b900"), (2, 0x0116, "4a040000"),
]
PRIVATE_EXPECTED = [
    {"water_temp": 54.1, "hp_hours": 8884, "elec_hours": 87, "elec_index": 26542, "hp_index": 3782,
     "dhw_mode": "autoMode", "boost_days": 0, "away_days": None, "water_litres": None, "v40_litres": 11000,
     "air_in_temp": 21.6, "evap_low_temp": -2.0, "evap_high_temp": None,
     "energy_total": 4159092, "manual_min_temp": 50.0, "manual_max_temp": 62.0},
    {"mode": "auto", "effective_setpoint": 21.0, "comfort_setpoint": 17.0, "eco_lowering": 3.5,
     "derogated_setpoint": 0, "boost_minutes": 0, "boost_setting": 20, "boost_max": 120,
     "drying_minutes": 90, "temporary_state": "permanentHeating", "occupancy": "ON",
     "drying_setting": 90, "drying_max": 240, "ambient_temp": 18.5, "env_presence": "ON", "env_lux": 150,
     "env_humidity": 54.5, "env_temp": 18.5, "index_conso_raw": "4a040000"},
]


def private_reply(guest, request, index, register, blob):
    assert len(request) == 40 and request[34:38] == b"\x07\x04\x0c\x60", "private READ shape"
    assert request[38:40] == struct.pack(">H", register), f"private READ order {register:#06x}"
    assert request[3:6] == bytes.fromhex("040506" if index == 1 else "070809"), "private READ target"
    if blob is None:
        return
    value = b"" if blob == "access" else bytes.fromhex(blob)
    head = b"\xff\xff\xff\xa0" + request[3:6] + request[:3] + bytes([0, 150, 0, 0x21, 0x0c, 0x60])
    if register == 0x0005:
        head = head[:-1] + b"\x61"  # non-fatal DEVICE_ERROR
    if register == 0x0017:
        guest.radio.sendall(uart_frame(0x040c, head + struct.pack(">H", 0x0018) + value))
    guest.radio.sendall(uart_frame(0x040c, head + struct.pack(">H", register) + value))


def private_reads(guest, first_private):
    # Subscribe near the end to isolate the optional publication from MAIN_INFO.
    for position, (index, register, blob) in enumerate(PRIVATE_FIXTURE[:-1]):
        request = first_private if position == 0 else uart_receive(guest.stream, 0x0101)
        private_reply(guest, request, index, register, blob)
    states = [subscribe(*port_for_private, prefix + "/" + label + "/state", fresh=True)
              for label in ("cethi", "ic3")]
    time.sleep(0.15)
    private_reply(guest, uart_receive(guest.stream, 0x0101), *PRIVATE_FIXTURE[-1])
    guest.wait("PRIVATE_PUBLISHED", 30)
    for i, (state, expected) in enumerate(zip(states, PRIVATE_EXPECTED)):
        values = json.loads(read_subscriber(state)[0])
        assert values["status"] == "DONE" and values["target_raw"] == TARGET_RAW["private"]
        assert_limits(values, 62.0 if i == 0 else None)
        for key, want in expected.items():
            assert key in values and values[key] == want, f"{key}={values.get(key)!r} expected {want!r}"
    results = [line for line in guest.history if line.startswith("PRIVATE_RESULT")]
    assert len(results) == 28, results
    assert any("register=0x0001 status=TIMEOUT" in line for line in results)
    assert any("register=0x0005 status=DEVICE_ERROR" in line for line in results)
    assert not any("SERVICE_EXIT" in line for line in guest.history)
    print("PRIVATE_READS: 28 registers checked; CETHI target 62.0 C; environment data still read", flush=True)


def outage_during_private(guest, server, conf, first_private):
    private_reply(guest, first_private, *PRIVATE_FIXTURE[0])
    request = uart_receive(guest.stream, 0x0101)
    server.terminate()
    server.wait()
    guest.wait("MQTT_DISCONNECTED")
    private_reply(guest, request, *PRIVATE_FIXTURE[1])
    guest.wait("PRIVATE_RESULT index=1 register=0x0003 status=DONE")
    guest.radio.settimeout(1)
    try:
        assert not guest.radio.recv(1), "UART wrote during private-series outage"
    except TimeoutError:
        pass
    guest.radio.settimeout(15)
    server = start_broker(conf, port_for_private[0])
    restarted = time.monotonic()
    try:
        cethi, ic3 = [subscribe(*port_for_private, prefix + "/" + label + "/state", fresh=True)
                      for label in ("cethi", "ic3")]
        first = uart_receive(guest.stream, 0x0100)
        guest.radio.sendall(uart_reply(guest.stream, first, 1, 23456))
        second = uart_receive(guest.stream, 0x0100)
        guest.radio.sendall(uart_reply(guest.stream, second, 2, 12345))
        for state, want in ((cethi, 23456), (ic3, 12345)):
            values = json.loads(read_subscriber(state)[0])
            assert values["target_raw"] == want, f"I2 stale state after reconnect: {values}"
            assert "water_temp" not in values and "hp_hours" not in values, "partial series survived reconnect"
            assert_limits(values, 39.2 if want == 23456 else None)
        elapsed = time.monotonic() - restarted
        assert elapsed < 15, f"fresh state took {elapsed:.3f}s after reconnect"
        private_reply(guest, uart_receive(guest.stream, 0x0101), *PRIVATE_FIXTURE[0])
    except BaseException:
        server.terminate()
        server.wait()
        raise
    print(f"I2_PRIVATE_OUTAGE: old series discarded; fresh pair within {elapsed:.3f}s of broker restart "
          f"(interval {interval}s), then new optional series", flush=True)
    return server


def outage_during_limits(guest, server, conf):
    request = uart_receive(guest.stream, 0x0100, diag_type=7)
    assert request[:6] == bytes.fromhex("010203040506")
    server.terminate()
    server.wait()
    guest.wait("MQTT_DISCONNECTED")
    guest.radio.sendall(limit_reply(request, 33515))
    guest.wait("LIMITS_UNAVAILABLE reason=INTERRUPTED")
    server = start_broker(conf, port_for_private[0])
    try:
        states = [subscribe(*port_for_private, f"{prefix}/{label}/state") for label in ("cethi", "ic3")]
        for index in (1, 2):
            request = uart_receive(guest.stream, 0x0100)
            guest.radio.sendall(uart_reply(guest.stream, request, index, index * 100))
        for index, state in enumerate(states, 1):
            values = json.loads(read_subscriber(state)[0])
            assert values["target_raw"] == index * 100
            assert_limits(values)
        request = uart_receive(guest.stream, 0x0101)
        private_reply(guest, request, *PRIVATE_FIXTURE[0])
        guest.drain()
        assert [line for line in guest.history if line.startswith("LIMIT_ARMED ")] == ["LIMIT_ARMED type=7"]
        assert not any(line.startswith(("LIMITS_ACCEPTED", "SERVICE_EXIT")) for line in guest.history)
    except BaseException:
        server.terminate()
        server.wait()
        raise
    print("LIMITS_OUTAGE interrupted after MAX1; fresh regular pair; no limit retry", flush=True)
    return server


def private_slow(guest, initial, first_private):
    guest.radio.settimeout(38)
    silent = [register for index, register, _ in PRIVATE_FIXTURE if index == 1]
    previous = [values["observed_monotonic_ms"] for values in initial]
    gaps = []
    start = time.monotonic()
    count = 0
    request = first_private
    while count < len(silent):
        if len(request) == 40:
            private_reply(guest, request, 1, silent[count], None)
            count += 1
            if count < len(silent):
                request = uart_receive(guest.stream, (0x0100, 0x0101))
            continue
        subscribers = [subscribe(*port_for_private, prefix + "/" + label + "/state", fresh=True)
                       for label in ("cethi", "ic3")]
        time.sleep(0.15)
        guest.radio.sendall(uart_reply(guest.stream, request, 1, 12345))
        guest.radio.sendall(uart_reply(guest.stream, uart_receive(guest.stream, 0x0100), 2, 23456))
        for i, state in enumerate(subscribers):
            values = json.loads(read_subscriber(state)[0])
            observed = values["observed_monotonic_ms"]
            gaps.append(observed - previous[i])
            previous[i] = observed
        request = uart_receive(guest.stream, (0x0100, 0x0101))
    guest.wait("PRIVATE_RESULT index=1 register=0x0041 status=TIMEOUT")
    elapsed = time.monotonic() - start
    assert elapsed > 60 and len(gaps) >= 4 and max(gaps) < 60000 and min(gaps) > 0, (elapsed, gaps)
    print(f"I3_PRIVATE_SLOW: {count} silent registers over {elapsed:.1f}s; MAIN_INFO max gap {max(gaps)}ms", flush=True)


class Guest:
    def __init__(self, args, working, radio):
        self.lines = queue.Queue()
        self.history = []
        self.vm = subprocess.Popen(args, cwd=working, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        def read():
            for line in self.vm.stdout:
                self.lines.put(line.strip())
        threading.Thread(target=read, daemon=True).start()
        self.radio = socket.socket(socket.AF_UNIX)
        self.radio.settimeout(20)
        end = time.monotonic() + 5
        while time.monotonic() < end:
            try:
                self.radio.connect(str(radio))
                break
            except (ConnectionRefusedError, FileNotFoundError):
                time.sleep(0.05)
        else:
            self.wait("LAB_SERVICE_STARTED", 1)
        self.stream = self.radio.makefile("rb")

    def wait(self, label, timeout=22):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            try:
                line = self.lines.get(timeout=max(0.01, until - time.monotonic()))
            except queue.Empty:
                break
            self.history.append(line)
            if 'Kernel panic' in line:
                break
            if label in line:
                return line
        tail = "\n".join(self.history[-65:])
        raise AssertionError(f"Missing guest marker {label}\n{tail}")

    def drain(self):
        while True:
            try:
                self.history.append(self.lines.get_nowait())
            except queue.Empty:
                return

    def command(self, text):
        self.vm.stdin.write(text + "\n")
        self.vm.stdin.flush()

    def close(self):
        self.stream.close()
        self.radio.close()
        if self.vm.poll() is None:
            self.vm.terminate()
        self.vm.wait(timeout=5)


def subscribe(port, username, password, topic, count=1, fresh=False):
    return subprocess.Popen(["mosquitto_sub", "-h", "127.0.0.1", "-p", str(port), "-u", username,
                             "-P", password, "-t", topic, "-C", str(count), "-W", "38" if fresh else "12", "-q", "1"] + (["-R"] if fresh else []),
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def read_subscriber(proc, timeout=14):
    value, _ = proc.communicate(timeout=timeout)
    assert proc.returncode == 0, "independent MQTT subscriber timeout"
    return value.splitlines()


with tempfile.TemporaryDirectory(prefix="ctq2-") as temporary:
    lab = Path(temporary)
    prefs = lab / "prefs/ct"
    prefs.mkdir(parents=True, mode=0o700)
    username = "synthetic"
    password = secrets.token_hex(12)
    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        host_port = port_socket.getsockname()[1]
    subprocess.run(["mosquitto_passwd", "-b", "-c", lab / "passwd", username, password],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    port_for_private = (host_port, username, password)
    conf = lab / "broker.cfg"
    conf.write_text(f"listener {host_port} 127.0.0.1\nallow_anonymous false\n"
                    f"password_file {lab / 'passwd'}\npersistence false\nuser root\n")
    (prefs / "broker.conf").write_text(
        f"broker_ipv4=10.0.2.2\nbroker_port={host_port}\nmqtt_username={username}\n"
        f"mqtt_password={password}\nclient_id={client_id}\nlan_ipv4=10.0.2.15\n"
        f"lan_prefix=24\nadmin_ipv4=10.0.2.2\ninterval_seconds={interval}\n")
    fixture_context = ["00", "0c01", "000000", "0c", "00", "0000", "00", "07", "11" * 16]
    (prefs / "targets.conf").write_text("\n".join("|".join([label, "010203", addr] + fixture_context)
                                                   for label, addr in (("CETHI", "040506"), ("IC3", "070809"))) + "\n")
    runtime = work / "latest-trees/root"
    result = subprocess.run(["qemu-arm", "-cpu", "arm926", "-L", runtime, runtime / "usr/bin/dropbearkey",
                             "-t", "ed25519", "-f", prefs / "ssh_host_key"],
                            check=True, capture_output=True, text=True)
    public_line = next(line for line in result.stdout.splitlines() if line.startswith("ssh-ed25519 "))
    key = lab / "admin"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key], check=True)
    (prefs / "authorized_keys").write_bytes(key.with_suffix(".pub").read_bytes())
    with socket.socket() as ssh_socket:
        ssh_socket.bind(("127.0.0.1", 0))
        ssh_port = ssh_socket.getsockname()[1]
    known = lab / "known_hosts"
    known.write_text(f"[127.0.0.1]:{ssh_port} {public_line}\n")
    ssh = ["ssh", "-F", "/dev/null", "-i", key, "-p", str(ssh_port),
           "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
           "-o", "IdentityAgent=none", "-o", "GlobalKnownHostsFile=/dev/null",
           "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={known}",
           "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=4", "root@127.0.0.1"]
    for file in prefs.iterdir():
        file.chmod(0o600)
    # Application archives (CTAPP1) built like build-app.py, staged by ct-update.lua itself.
    factory_modules = {p.name: p.read_bytes() for p in sorted((runtime / "usr/share/cozytouch/phase2").glob("*.lua"))
                       if p.name != "radio-start.lua"}
    def ctapp(files):
        parts = [b"CTAPP1\n"] + [f"F {n} {len(d)} {hashlib.sha256(d).hexdigest()}\n".encode() + d
                                 for n, d in files.items()] + [b"END\n"]
        return b"".join(parts)
    def stage(variant, files):
        target = lab / f"prefs-{variant}"
        shutil.copytree(lab / "prefs", target)
        data = files if isinstance(files, bytes) else ctapp(files)
        digest = hashlib.sha256(data).hexdigest()
        staging_run = lab / f"run-{variant}"
        staging_run.mkdir()
        subprocess.run(["qemu-arm", "-cpu", "arm926", "-L", runtime, runtime / "usr/bin/luajit",
                        runtime / "usr/libexec/ct/ct-update.lua", "install", digest], input=data, check=True,
                       capture_output=True, env=dict(os.environ, CT_TEST="1", CT_APPS=str(target), CT_RUN=str(staging_run)))
        return "v-" + digest[:12]
    ota_version = stage("ota", factory_modules)
    broken = dict(factory_modules, **{"service.lua": b"print('BROKEN_APP')\nos.exit(35)\n"})
    fail_version = stage("otafail", broken)
    if os.environ.get("CT_CANDIDATE_APP"):
        candidate = Path(os.environ["CT_CANDIDATE_APP"]).read_bytes()
    else:
        candidate_dir = lab / "candidate"
        subprocess.run(["python3", here.parent / "prepare-lua.py",
                        here.parents[3] / "analyse-2026-11-17/buildroot-ram/variante-service-20261118/overlay/usr/share/cozytouch/mqtt",
                        here.parent / "src", candidate_dir], check=True)
        candidate = {p.name: p.read_bytes() for p in sorted(candidate_dir.glob("*.lua")) if p.name != "radio-start.lua"}
    late_version = stage("late", candidate)
    print("CANDIDATE_APP version=" + late_version, flush=True)
    lan_archive = ctapp(dict(factory_modules, **{"service.lua": factory_modules["service.lua"] + b"\n-- lan\n"}))
    lan_digest = hashlib.sha256(lan_archive).hexdigest()
    subprocess.run(["bash", here / "build-lab.sh", work, lab], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE)
    dtb = lab / "lab.dtb"
    dtb.write_bytes((work / "out/qemu/arch/arm/boot/dts/arm/versatile-pb.dtb").read_bytes())
    seed = [f"{byte:02x}" for byte in os.urandom(64)]
    subprocess.run(["fdtput", "-t", "bx", dtb, "/chosen", "rng-seed", *seed], check=True)
    # Serial 0 is the console. Serial 1 is the synthetic UART endpoint.
    cmdline = ("console=ttyAMA0 rdinit=/lab-init panic=-1 loglevel=5 "
               "nandsim.first_id_byte=0x2c nandsim.second_id_byte=0xf1 "
               "nandsim.third_id_byte=0x80 nandsim.fourth_id_byte=0x15 "
               "nandsim.parts=1,1023 nandsim.bch=4")
    server = start_broker(conf, host_port)
    guest = None
    try:
        assert mqtt_connect(host_port, username, "synthetic-invalid") == b"\x20\2\0\5"
        assert mqtt_connect(host_port, username, password) == b"\x20\2\0\0"
        print("MQTT_AUTH valid accepted / invalid rejected", flush=True)
        for scenario in scenarios:
            print(f"SCENARIO {scenario}", flush=True)
            if scenario.startswith("late-broker"):
                server.terminate()
                server.wait()
            radio = lab / "serial.sock"
            radio.unlink(missing_ok=True)
            args = ["qemu-system-arm", "-M", "versatilepb", "-cpu", "arm926", "-m", "128M",
                    "-display", "none", "-audio", "none", "-monitor", "none", "-serial", "stdio",
                    "-chardev", f"socket,id=radio,path={radio},server=on,wait=off", "-serial", "chardev:radio",
                    "-nic", f"user,model=smc91c111,hostfwd=tcp:127.0.0.1:{ssh_port}-10.0.2.15:2222",
                    "-no-reboot", "-kernel", work / "bin/qemu.zImage", "-dtb", dtb,
                    "-initrd", lab / "lab.cpio.gz", "-append", cmdline + lab_flags.get(scenario, "")]
            guest = Guest(args, lab, radio)
            print(guest.wait("NANDSIM_GEOMETRY_OK", 45), flush=True)
            print(guest.wait("UBIFS_EXACT_MOUNT_OK", 45), flush=True)
            guest.wait("SERVICE_LAUNCH attempt=1")
            if scenario == "alias":
                guest.wait("UART_OPEN_FAILED")
                guest.wait("SUPERVISOR_HOLD")
                guest.command("count")
                guest.wait("LAB_COUNTER value=2 pointer=unchanged")
                print("UART_ALIAS existing owner detected by device identity; no READ or ack", flush=True)
                guest.close()
                guest = None
                server.terminate()
                server.wait()
                server = start_broker(conf, host_port)
                continue
            if scenario == "ota-fail":
                assert "APP_SELECT mode=trial version=" + fail_version in guest.history
                guest.wait("BROKEN_APP")
                guest.wait("APP_TRIAL_FAILED version=" + fail_version + " reboot=once")
                guest.wait("REBOOT_NOW")
                guest.wait("reboot: Restarting system")
                guest.vm.wait(timeout=10)
                assert not any("LAB_COUNTER" in line or "HEALTH_OK" in line for line in guest.history)
                print("OTA_FAIL trial dropped before the single reboot; no counter ack", flush=True)
                guest.close()
                guest = None
                server.terminate()
                server.wait()
                server = start_broker(conf, host_port)
                continue
            if scenario == "pulse-refused":
                guest.wait("RADIO_PULSE refused=lab")
                guest.wait("UART_CLEANUP restored=true")
                guest.wait("STM32_PULSE_FAILED")
                guest.wait("SUPERVISOR_HOLD")
                guest.command("count")
                print(guest.wait("LAB_COUNTER value=2 pointer=unchanged"), flush=True)
                print("PULSE_REFUSED no STM32 wait, no READ or ack; UART restored", flush=True)
                guest.close()
                guest = None
                server.terminate()
                server.wait()
                server = start_broker(conf, host_port)
                continue
            print(guest.wait("RADIO_PULSE low_ms=35 restored=true lab"), flush=True)
            if scenario == "passive":
                guest.command("observe")
                guest.wait("LAB_PASSIVE_RECEIPT")
                guest.wait("STACK_START passive_receipt")
            else:
                guest.radio.sendall(uart_frame(0x050e, b"\x01") + uart_frame(0x0403, b"\4"))
            assert uart_receive(guest.stream, 0x0500) == b"\0"
            response = b"\0v2.4.3" if scenario == "wrong-revision" else b"\0v2.4.2"
            guest.radio.sendall(uart_frame(0x0500, response))
            if scenario == "wrong-revision":
                guest.wait("STM32_REVISION_MISMATCH")
                guest.wait("SUPERVISOR_HOLD")
                guest.command("count")
                print(guest.wait("LAB_COUNTER value=2 pointer=unchanged"), flush=True)
                assert "LED state=error applied=false" in guest.history
                print("WRONG_REVISION no READ or ack; UART restored; LED error requested", flush=True)
            else:
                if scenario == "late-broker-v4":
                    guest.wait("SERVICE_EXIT status=31", late_broker_delay)
                    guest.wait("SUPERVISOR_HOLD")
                    assert "APP_SELECT mode=factory version=factory" in guest.history
                    assert not any("READ_ARMED" in line or "HEALTH_OK" in line for line in guest.history)
                    print("LATE_BROKER_V4 factory application gives up at 95 s wall time (defect reproduced)", flush=True)
                    guest.close()
                    guest = None
                    server = start_broker(conf, host_port)
                    continue
                if scenario == "late-broker":
                    guest.radio.settimeout(1)
                    until = time.monotonic() + late_broker_delay
                    while time.monotonic() < until:
                        try:
                            assert not guest.radio.recv(1), "UART READ while the broker is absent"
                        except TimeoutError:
                            pass
                    guest.drain()
                    assert "APP_SELECT mode=trial version=" + late_version in guest.history
                    assert any("MQTT_DISCONNECTED" in line for line in guest.history)
                    assert not any(marker in line for line in guest.history
                                   for marker in ("SERVICE_EXIT", "HEALTH_TIMEOUT", "SUPERVISOR_HOLD", "APP_TRIAL_FAILED"))
                    print(f"LATE_BROKER broker absent {late_broker_delay} s: service still waiting, no READ, no exit", flush=True)
                    server = start_broker(conf, host_port)
                    guest.radio.settimeout(38)
                first = uart_receive(guest.stream, 0x0100)
                guest.command("net")
                guest.wait("LAB_NO_DEFAULT_ROUTE")
                guest.wait("LAB_NETWORK_DROP")
                if scenario == "reset":
                    guest.radio.sendall(uart_frame(0x050e, b"\x01"))
                    guest.wait("UART_CLEANUP restored=true")
                    guest.wait("STM32_RESET")
                    guest.command("count")
                    print(guest.wait("LAB_COUNTER value=2 pointer=unchanged"), flush=True)
                    print("UNEXPECTED_RESET stops armed READ and preserves counter", flush=True)
                    guest.close()
                    guest = None
                    server.terminate()
                    server.wait()
                    server = start_broker(conf, host_port)
                    continue
                if scenario == "term":
                    guest.command("term")
                    guest.wait("LAB_TERM_SENT")
                    time.sleep(0.2)
                if scenario == "outage":
                    server.terminate()
                    server.wait()
                    guest.wait("MQTT_DISCONNECTED")
                guest.radio.sendall(uart_reply(guest.stream, first, 1, TARGET_RAW.get(scenario, 200)))
                if scenario == "term":
                    guest.wait("READ_RESULT index=1 status=DONE")
                    guest.wait("UART_CLEANUP restored=true")
                    guest.wait("MQTT_DISCONNECT complete=true")
                    guest.command("count")
                    guest.wait("LAB_COUNTER value=2 pointer=unchanged")
                    print("TERM READ drained; no second READ; termios reread; graceful MQTT; no counter ack", flush=True)
                else:
                    if scenario == "outage":
                        guest.wait("READ_RESULT index=1 status=DONE")
                        guest.radio.settimeout(1)
                        try:
                            assert not guest.radio.recv(1), "UART wrote during broker outage"
                        except TimeoutError:
                            pass
                        guest.radio.settimeout(38)
                        server = start_broker(conf, host_port)
                        first = uart_receive(guest.stream, 0x0100)
                        guest.radio.sendall(uart_reply(guest.stream, first, 1, TARGET_RAW.get(scenario, 200)))
                    state_a = subscribe(host_port, username, password, prefix + "/cethi/state")
                    state_b = subscribe(host_port, username, password, prefix + "/ic3/state")
                    time.sleep(0.15)
                    second = uart_receive(guest.stream, 0x0100)
                    if scenario == "regular-refusal":
                        main = uart_reply(guest.stream, second, 2)[5:-2]
                        refused_at = time.monotonic()
                        guest.radio.sendall(uart_frame(0x010d, main[:14] + b"\x08\x09"))
                        result = guest.wait("READ_RESULT index=2")
                        elapsed = time.monotonic() - refused_at
                        exit_line = guest.wait("SERVICE_EXIT status=")
                        assert result.endswith("status=DEVICE_ERROR") and "status=33 " in exit_line, (result, exit_line)
                        assert elapsed < 1, f"short IC3 refusal took {elapsed:.3f}s"
                        assert not any(line.startswith(("LIMIT_ARMED ", "HEALTH_OK")) for line in guest.history)
                        print(f"REGULAR_REFUSAL IC3 DEVICE_ERROR in {elapsed:.3f}s; exit 33 before health", flush=True)
                        for state in (state_a, state_b):
                            state.terminate()
                            state.communicate(timeout=5)
                        guest.close()
                        guest = None
                        server.terminate()
                        server.wait()
                        server = start_broker(conf, host_port)
                        continue
                    guest.radio.sendall(uart_reply(guest.stream, second, 2, TARGET_RAW.get(scenario, 200)))
                    if scenario == "limits-outage":
                        guest.wait("HEALTH_OK counter_ack=verified")
                    elif scenario in candidate_scenarios:
                        try:
                            first_private = limits_exchange(guest, scenario)
                        except (AssertionError, TimeoutError):
                            guest.drain()
                            print("\n".join(line for line in guest.history if line.startswith(
                                ("LIMIT_", "LIMITS_", "READ_ARMED ", "READ_RESULT ", "HEALTH_", "SERVICE_EXIT "))), flush=True)
                            raise
                        assert guest.history.index("HEALTH_OK counter_ack=verified") < guest.history.index("LIMIT_ARMED type=7")
                    else:
                        guest.wait("HEALTH_OK counter_ack=verified")
                    initial = [json.loads(read_subscriber(state)[0]) for state in (state_a, state_b)]
                    assert all(values["status"] == "DONE" for values in initial)
                    if scenario in candidate_scenarios:
                        for values in initial:
                            assert_limits(values)
                    if scenario == "private":
                        private_reads(guest, first_private)
                    if scenario == "outage":
                        server = outage_during_private(guest, server, conf, first_private)
                    if scenario == "private-slow":
                        private_slow(guest, initial, first_private)
                    if scenario == "limits-outage":
                        server = outage_during_limits(guest, server, conf)
                    elif scenario in limit_scenarios:
                        limits_followup(guest, scenario, first_private, initial)
                    raw_configs = read_subscriber(subscribe(host_port, username, password, "homeassistant/#", 2))
                    configs = [json.loads(config) for config in raw_configs]
                    if scenario in candidate_scenarios:
                        assert len({tuple(config["dev"]["ids"]) for config in configs}) == 2
                        assert {config["stat_t"] for config in configs} == {prefix + "/cethi/state", prefix + "/ic3/state"}
                        assert all(not any("cmd" in key or "command" in key for key in component)
                                   for config in configs for component in config["cmps"].values())
                        assert all(len(config.encode()) <= 6144 for config in raw_configs)
                        # client_id is ASCII (up to 48 bytes); exp_aft grows from 75 to 3645.
                        expiration = interval + 45
                        assert all(config["exp_aft"] == expiration for config in configs)
                        expiration_growth = len(str(3645)) - len(str(expiration))
                        largest_configs = [len(config.replace(client_id, "x" * 48).encode()) + expiration_growth
                                           for config in raw_configs]
                        assert max(largest_configs) <= 6144, largest_configs
                        # v3 corrections (maj-lan-3): V40 raw index, Wh counters, IC3 timers and boost setting.
                        cmps = {config["stat_t"]: config["cmps"] for config in configs}
                        cethi, ic3 = cmps[prefix + "/cethi/state"], cmps[prefix + "/ic3/state"]
                        # v4: 15 + 3 (energy_total, manual_min/max_temp) and
                        # 13 + 8 (drying_setting/max, ambient_temp, env_* x4, index_conso_raw).
                        assert len(cethi) == len(ic3) == 21, (len(cethi), len(ic3))
                        assert LIMIT_KEYS <= cethi.keys() and LIMIT_KEYS.isdisjoint(ic3)
                        assert all(OBSOLETE_LIMIT_KEYS.isdisjoint(cs) for cs in (cethi, ic3))
                        assert all(cethi[k]["p"] == "sensor" and cethi[k]["unit_of_meas"] == "°C"
                                   and cethi[k]["dev_cla"] == "temperature" for k in LIMIT_KEYS)
                        assert cethi["target_temp"]["stat_cla"] == "measurement"
                        assert all(cethi[k]["ent_cat"] == "diagnostic" for k in LIMIT_KEYS - {"target_temp"})
                        v40 = cethi["v40_litres"]
                        assert "unit_of_meas" not in v40 and "dev_cla" not in v40 and "brut" in v40["name"], v40
                        assert all(cethi[k]["unit_of_meas"] == "Wh" and cethi[k]["dev_cla"] == "energy"
                                   and cethi[k]["stat_cla"] == "total_increasing" for k in ("elec_index", "hp_index"))
                        assert "restante" in ic3["boost_minutes"]["name"] and "restante" in ic3["drying_minutes"]["name"]
                        assert ic3["boost_setting"]["unit_of_meas"] == ic3["boost_max"]["unit_of_meas"] == "min"
                        # v4 entities. Existing keys and unique_id unchanged (<client>_<device>_<key>).
                        assert cethi["v40_litres"]["uniq_id"] == client_id + "_cethi_v40_litres"
                        assert ic3["occupancy"]["uniq_id"] == client_id + "_ic3_occupancy"
                        assert all(c["uniq_id"] == client_id + "_" + d + "_" + k
                                   for d, cs in (("cethi", cethi), ("ic3", ic3)) for k, c in cs.items())
                        e = cethi["energy_total"]
                        assert (e["unit_of_meas"], e["dev_cla"], e["stat_cla"]) == ("Wh", "energy", "total_increasing"), e
                        assert all(cethi[k]["ent_cat"] == "diagnostic" and cethi[k]["unit_of_meas"] == "°C" for k in
                                   ("manual_min_temp", "manual_max_temp"))
                        assert ic3["drying_setting"]["unit_of_meas"] == ic3["drying_max"]["unit_of_meas"] == "min"
                        assert ic3["ambient_temp"]["dev_cla"] == ic3["env_temp"]["dev_cla"] == "temperature"
                        assert ic3["env_presence"]["p"] == "binary_sensor" and ic3["env_presence"]["pl_on"] == "ON"
                        assert ic3["env_humidity"]["unit_of_meas"] == "%" and ic3["env_lux"]["unit_of_meas"] == "lx"
                        assert all(ic3[k]["en"] is False and ic3[k]["ent_cat"] == "diagnostic" for k in ENV_KEYS)
                        raw = ic3["index_conso_raw"]
                        assert raw["en"] is False and raw["ent_cat"] == "diagnostic" and "unit_of_meas" not in raw, raw
                        assert sum("en" in c for cs in (cethi, ic3) for c in cs.values()) == 9  # current/rssi x2 + env x4 + raw
                        print("MQTT_DEVICE_DISCOVERY components=" + "/".join(str(len(c["cmps"])) for c in configs)
                              + " bytes=" + "/".join(c["stat_t"].rsplit("/", 2)[-2] + ":" + str(len(r.encode()))
                                                     for c, r in zip(configs, raw_configs))
                              + " max_supported_bytes=" + "/".join(
                                  c["stat_t"].rsplit("/", 2)[-2] + ":" + str(size)
                                  for c, size in zip(configs, largest_configs)), flush=True)
                    else:
                        assert len({tuple(config["device"]["identifiers"]) for config in configs}) == 2
                        assert {config["state_topic"] for config in configs} == {prefix + "/cethi/state", prefix + "/ic3/state"}
                        assert all(not any("command" in key for key in config) for config in configs)
                    guest.command("count")
                    print(guest.wait("LAB_COUNTER value=0 pointer=unchanged"), flush=True)
                    print("MQTT_DISCOVERY two devices; independent states; current session PUBACKs; no command topics", flush=True)
                    if scenario in ("ota-trial", "late-broker"):
                        version = ota_version if scenario == "ota-trial" else late_version
                        assert "APP_SELECT mode=trial version=" + version in guest.history
                        assert any(line.startswith("APP_PROMOTED version=" + version) for line in guest.history)
                        guest.command("appstate")
                        print(guest.wait(f"LAB_APP current={version} previous=- next=- trying=- apps=ro"), flush=True)
                        print("OTA_TRIAL staged version booted once, promoted after health, apps back to ro", flush=True)
                    if scenario == "late-broker":
                        print("LATE_BROKER broker started late: full pair, HEALTH_OK, counter 0, trial promoted", flush=True)
                    if scenario == "healthy":
                        assert "APP_SELECT mode=factory version=factory" in guest.history
                        led = [line for line in guest.history if line.startswith("LED state=")]
                        assert led[:2] == ["LED state=working applied=false", "LED state=ok applied=false"], led
                        print("LED working then ok after HEALTH_OK (no LED class in QEMU: applied=false)", flush=True)
                        guest.command("sshcheck")
                        guest.wait("LAB_DROPBEAR_LISTEN")
                        master, slave = pty.openpty()
                        try:
                            result = subprocess.run(["ssh", "-F", "/dev/null", "-tt", "-i", key, "-p", str(ssh_port),
                                                     "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
                                                     "-o", "IdentityAgent=none", "-o", "GlobalKnownHostsFile=/dev/null",
                                                     "-o", "StrictHostKeyChecking=yes", "-o",
                                                     f"UserKnownHostsFile={known}", "-o", "LogLevel=ERROR",
                                                     "-o", "ConnectTimeout=4", "root@127.0.0.1",
                                                     "test -t 0 && readlink /proc/self/fd/0"],
                                                    stdin=slave, env=dict(os.environ, TERM="xterm"), check=False,
                                                    capture_output=True, text=True, timeout=10)
                        finally:
                            os.close(slave)
                            os.close(master)
                        assert result.returncode == 0 and "/dev/pts/" in result.stdout, f"SSH rc={result.returncode}"
                        bad = subprocess.run(ssh + ["ct-update install " + "0" * 64], input=lan_archive,
                                             capture_output=True, timeout=60)
                        assert b"UPDATE_REFUSED sha256" in bad.stdout and bad.returncode == 2, bad
                        good = subprocess.run(ssh + ["ct-update install " + lan_digest], input=lan_archive,
                                              capture_output=True, timeout=60)
                        assert good.returncode == 0 and b"UPDATE_STAGED version=v-" + lan_digest[:12].encode() in good.stdout, good
                        status = subprocess.run(ssh + ["ct-update status; grep ' /apps ' /proc/mounts"],
                                                capture_output=True, text=True, timeout=30)
                        assert f"APP_LINK next=v-{lan_digest[:12]}" in status.stdout, status.stdout
                        assert "APP_STATUS mode=factory" in status.stdout
                        assert " ro," in status.stdout.split("ubi0:apps /apps", 1)[1].splitlines()[0], status.stdout
                        print("LAN_UPDATE install over SSH: bad hash refused, archive staged as next, /apps back to ro", flush=True)
                        assert guest.history.index("FIREWALL_DEFAULT_DROP_INTERFACES_DOWN") < guest.history.index("CONFINED_LAN_UP")
                        print("NETWORK firewall before link, IPv6 off, no default route; SSH key and PTY", flush=True)
                    if scenario == "diag-bornes":
                        assert "APP_SELECT mode=factory version=factory" in guest.history
                        diagnostic_bornes(guest, ssh, first)
                    if scenario == "passive":
                        print("PASSIVE_RECEIPT same Linux boot; correlated 2.4.2 required", flush=True)
                    if scenario == "outage":
                        print("MQTT_OUTAGE finishes armed READ; no new READ while disconnected; reconnect and full pair", flush=True)
                    if scenario == "lwt":
                        lwt = subscribe(host_port, username, password, prefix + "/availability", fresh=True)
                        time.sleep(0.2)
                        guest.command("kill")
                        guest.wait("LAB_KILL_SENT")
                        guest.wait("SUPERVISOR_HOLD")
                        assert read_subscriber(lwt, timeout=40) == ["offline"]
                        assert read_subscriber(subscribe(host_port, username, password, prefix + "/availability")) == ["offline"]
                        print("MQTT_LWT offline retained on process SIGKILL", flush=True)
            guest.close()
            guest = None
            # Force a clean broker between independent scenarios.
            server.terminate()
            server.wait()
            server = start_broker(conf, host_port)
    finally:
        if guest:
            guest.close()
        if server.poll() is None:
            server.terminate()
        server.wait()

