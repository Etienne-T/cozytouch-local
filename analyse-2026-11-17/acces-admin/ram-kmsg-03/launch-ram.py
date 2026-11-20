#!/usr/bin/env python3
"""Prepare one reviewed RAM boot on the Pi; no hardware access without --execute.

Required external Tcl contracts (all must exist even for a dry plan):
* preflight: read-only assertions, CPU remains halted, Tcl error on failure;
* quiesce: reviewed peripheral sequence, sets COZY_QUIESCE_COMMITTED=1 BEFORE
  its first device write; accepts COZY_ALLOW_QUIESCE=reviewed;
* rollback: separately reviewed recovery procedure. It is RECORDED, NEVER
  sourced automatically by this program. No improvised reset on an error.

After a quiesce commit, any failure leaves OpenOCD running for coordinated
recovery. Before that boundary, the launcher attempts to resume the old Linux
only when the commit marker can still be read and is exactly zero.

The supplied OpenOCD config is opened as-is (the coordinator's Pi config already
initializes the target and binds Tcl6666 to loopback). This program does not
generate peripheral-register writes or storage commands. External scripts must
not hide transfers/resets in the read-only preflight. Their reviewed dependencies
are the coordinator's responsibility. They are rehashed immediately before use.

OpenOCD get_reg/set_reg and read_memory contracts:
https://openocd.org/doc-release/html/General-Commands.html
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

KERNEL_SHA256 = "8c58bb4c0bbb294f9e2b017f245183f09541ae394c59356c41b342e030d7475a"
DTB_SHA256 = "f9dfe9677f8188bae1e03b5f34f178a9b783f262d65deed48680bac83591da3a"
KERNEL_ADDRESS = 0x22000000
DTB_ADDRESS = 0x21000000
DDR_START, DDR_END = 0x20000000, 0x28000000
# Margins reviewed separately in NOYAU-B-MARGES-RAM.md for this pinned kernel.
KERNEL_OUTPUT_START, KERNEL_BSS_END = 0x20008000, 0x205FE0BC
DECOMPRESSOR_END = 0x22307600
HOST, PORT = "127.0.0.1", 6666
COMMIT_VARIABLE = "COZY_QUIESCE_COMMITTED"


class LaunchError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tcl_word(value: str | Path) -> str:
    """Quote one Tcl word, independently of shell quoting or JSON escaping."""
    value = str(value)
    if any(c in value for c in ("\0", "\x1a", "\r", "\n")):
        raise LaunchError("control character in Tcl argument")
    for old, new in (("\\", "\\\\"), ("$", "\\$"), ("[", "\\["),
                     ("]", "\\]"), ('"', '\\"')):
        value = value.replace(old, new)
    return '"' + value + '"'


def parse_integer(value: str) -> int:
    value = value.strip()
    if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+", value):
        return int(value, 16)
    if re.fullmatch(r"[+-]?[0-9]+", value):
        return int(value, 10)
    raise LaunchError("OpenOCD returned a non-integer scalar")


def plain_tcl_words(value: str) -> list[str]:
    """Strict subset needed for OpenOCD integer lists and core-register dicts."""
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1].strip()
    if re.search(r"[^A-Za-z0-9_+.:\-\s]", value):
        raise LaunchError("unexpected Tcl structure in integer response")
    return value.split()


class Log:
    def __init__(self, directory: Path):
        self.directory = directory
        self.events = (directory / "events.jsonl").open("x", encoding="utf-8")
        self.summary: dict = {"hardware_access_performed": False,
                              "boot_confirmed": False, "stage": "validated"}

    def event(self, event: str, **fields):
        record = {"utc": datetime.now(timezone.utc).isoformat(),
                  "event": event, **fields}
        self.events.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.events.flush()
        # No raw Tcl response, memory contents, script or bootargs on stdout.
        print(json.dumps(record, ensure_ascii=False), flush=True)

    def state(self, stage: str, **fields):
        self.summary.update(stage=stage, **fields)
        temporary = self.directory / "state.json.new"
        temporary.write_text(json.dumps(self.summary, indent=2), encoding="utf-8")
        temporary.replace(self.directory / "state.json")
        self.event("stage", stage=stage)


class TclRPC:
    def __init__(self, sock: socket.socket, log: Log, timeout: float):
        self.sock, self.log, self.timeout = sock, log, timeout
        self.buffer = bytearray()
        self.request_id = 0

    def _frame(self, deadline: float, label: str) -> bytes:
        began = time.monotonic()
        next_progress = began + 15
        while True:
            if b"\x1a" in self.buffer:
                end = self.buffer.index(0x1A)
                frame = bytes(self.buffer[:end])
                del self.buffer[:end + 1]
                return frame
            now = time.monotonic()
            if now >= deadline:
                raise LaunchError(f"Tcl timeout during {label}")
            self.sock.settimeout(min(1.0, deadline - now))
            try:
                data = self.sock.recv(65536)
            except socket.timeout:
                data = None
            if data == b"":
                raise LaunchError(f"Tcl connection closed during {label}")
            if data:
                self.buffer.extend(data)
            if len(self.buffer) > 8 * 1024 * 1024:
                raise LaunchError("oversized Tcl response")
            if now >= next_progress:
                self.log.event("waiting", operation=label,
                               elapsed_s=round(now - began, 1))
                next_progress = now + 15

    def command(self, command: str, label: str) -> str:
        self.request_id += 1
        marker = f"__COZY_RAM_RPC_{self.request_id}__"
        # Tcl catch returns the true interpreter status; do not scrape human
        # 'mdw'/'reg' output or guess success from absence of the word 'error'.
        wrapped = (f"set __cozy_rpc_rc [catch {tcl_word(command)} __cozy_rpc_value]; "
                   f'format "{marker}%d\\n%s" $__cozy_rpc_rc $__cozy_rpc_value')
        self.log.event("command_begin", operation=label)
        self.sock.sendall(wrapped.encode("utf-8") + b"\x1a")
        deadline = time.monotonic() + self.timeout
        while True:
            raw = self._frame(deadline, label)
            response = raw.decode("utf-8", errors="strict")
            if not response.startswith(marker):
                # An unsolicited notification or an old response must not be
                # mistaken for the result of the current command.
                self.log.event("other_tcl_frame", bytes=len(raw))
                continue
            status, separator, value = response[len(marker):].partition("\n")
            if not separator or not re.fullmatch(r"-?[0-9]+", status):
                raise LaunchError("malformed Tcl RPC envelope")
            if int(status) != 0:
                # Keep diagnostics private; never echo a potentially sensitive
                # external-script response to the console.
                error_path = self.log.directory / f"tcl-error-{self.request_id}.txt"
                error_path.write_text(value, encoding="utf-8")
                os.chmod(error_path, 0o600)
                raise LaunchError(f"Tcl failure status {int(status)} in {label}; see {error_path.name}")
            self.log.event("command_end", operation=label)
            return value.strip()

    def read_memory(self, address: int, width: int, count: int) -> list[int]:
        if width not in (8, 16, 32, 64) or count < 1 or count > 1024:
            raise LaunchError("invalid memory-read geometry")
        words = plain_tcl_words(self.command(
            f"read_memory {address:#x} {width} {count} phys", "read_memory"))
        values = [parse_integer(word) for word in words]
        if len(values) != count or any(not 0 <= x < (1 << width) for x in values):
            raise LaunchError("memory-read count or width mismatch")
        return values

    def get_reg(self, names: list[str], force: bool = True) -> dict[str, int]:
        if not names or any(not re.fullmatch(r"[a-zA-Z0-9_]+", n) for n in names):
            raise LaunchError("invalid register list")
        command = "get_reg " + ("-force " if force else "") + "{" + " ".join(names) + "}"
        words = plain_tcl_words(self.command(command, "get_reg"))
        if len(words) != 2 * len(names):
            raise LaunchError("register response has wrong length")
        result = {}
        for name, value in zip(words[0::2], words[1::2]):
            if name in result:
                raise LaunchError("duplicate register response")
            result[name] = parse_integer(value)
        if set(result) != set(names) or any(not 0 <= x <= 0xFFFFFFFF for x in result.values()):
            raise LaunchError("register response does not match request")
        return result

    def sctlr(self) -> int:
        return parse_integer(self.command("arm mrc 15 0 1 0 0", "read_SCTLR"))

    def commit_state(self) -> int:
        result = parse_integer(self.command(
            f"expr {{[info exists {COMMIT_VARIABLE}] && ${COMMIT_VARIABLE}}}",
            "read_quiesce_commit"))
        if result not in (0, 1):
            raise LaunchError("invalid quiesce commit marker")
        return result


def validate_file(path: Path, expected_sha: str | None = None) -> dict:
    if not path.is_file():
        raise LaunchError(f"required file missing: {path}")
    tcl_word(path)  # Refuse control characters before any connection.
    actual = sha256_file(path)
    if expected_sha is not None and actual != expected_sha:
        raise LaunchError(f"SHA-256 mismatch: {path.name}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual}


def unchanged(record: dict):
    validate_file(Path(record["path"]), record["sha256"])


def visible_inputs(files: dict) -> dict:
    """Do not print the expected MAC, its file contents or its fingerprint."""
    return {name: ({"path": record["path"], "identifier_not_displayed": True}
                   if name == "expected_mac" else record)
            for name, record in files.items()}


def verify_mac_identity(rpc: TclRPC, record: dict, log: Log):
    unchanged(record)
    text = Path(record["path"]).read_text(encoding="ascii").strip()
    if not re.fullmatch(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}|[0-9a-fA-F]{12}", text):
        raise LaunchError("expected MAC file has an unsupported format")
    expected = bytes.fromhex(text.replace(":", "").replace("-", ""))
    station_low, station_high = rpc.read_memory(0xF802C098, 32, 2)
    actual = station_low.to_bytes(4, "little") + (station_high & 0xFFFF).to_bytes(2, "little")
    if not hmac.compare_digest(expected, actual):
        raise LaunchError("MAC identity mismatch before quiescence; identifier not displayed")
    log.event("mac_identity_match", identifier_not_displayed=True)


def source_checked(rpc: TclRPC, record: dict, label: str):
    unchanged(record)
    rpc.command("source " + tcl_word(record["path"]), label)


def wait_for_tcl(process: subprocess.Popen, log: Log, timeout: float) -> socket.socket:
    deadline, next_progress = time.monotonic() + timeout, time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise LaunchError("OpenOCD exited; inspect openocd.log")
        try:
            return socket.create_connection((HOST, PORT), timeout=0.5)
        except OSError:
            if time.monotonic() >= next_progress:
                log.event("waiting_for_openocd")
                next_progress = time.monotonic() + 5
            time.sleep(0.2)
    raise LaunchError("OpenOCD Tcl startup timeout")


def check_cpu_for_entry(rpc: TclRPC, log: Log):
    # Read CP15 only: never invent an MMU/cache transition here.
    control = rpc.sctlr()
    if control & ((1 << 0) | (1 << 2) | (1 << 12)):
        raise LaunchError("SCTLR still enables MMU, D-cache or I-cache")
    context = rpc.get_reg(["cpsr", "pc"], force=False)
    if context["cpsr"] & 0xFF != 0xD3:
        raise LaunchError("CPU is not ARM/SVC with IRQ/FIQ masked")
    log.event("cpu_entry_checks", sctlr_hex=hex(control),
              cpsr_hex=hex(context["cpsr"]), context="OpenOCD staged core context")


def load_and_verify(rpc: TclRPC, record: dict, address: int, name: str, log: Log):
    unchanged(record)
    path = Path(record["path"])
    rpc.command(f"load_image {tcl_word(path)} {address:#x} bin", f"load_{name}")
    dump = log.directory / f"readback-{name}.bin"
    if dump.exists():
        raise LaunchError("readback path already exists")
    rpc.command(f"dump_image {tcl_word(dump)} {address:#x} {record['bytes']}",
                f"full_readback_{name}")
    actual = validate_file(dump, record["sha256"])
    if actual["bytes"] != record["bytes"]:
        raise LaunchError(f"readback size mismatch for {name}")
    log.event("readback_verified", image=name, bytes=actual["bytes"],
              sha256=actual["sha256"])


def run(args, files: dict):
    if not sys.platform.startswith("linux"):
        raise LaunchError("--execute is intended for the coordinator's local Linux Pi")
    if args.run_dir.exists():
        raise LaunchError("run directory already exists; preserve previous evidence")
    # Never attach to somebody else's session or kill an existing server.
    try:
        existing = socket.create_connection((HOST, PORT), timeout=0.5)
    except OSError:
        pass
    else:
        existing.close()
        raise LaunchError("Tcl6666 is already in use; no existing process was changed")
    os.umask(0o077)
    args.run_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    log = Log(args.run_dir)
    log.summary.update(inputs=visible_inputs(files), rollback_tcl=files["rollback"],
                       automatic_rollback=False, automatic_reset_on_error=False)
    log.state("opening_openocd")
    process = None
    rpc = None
    quiesce_invoked = False
    old_linux_resumable = True
    try:
        for record in files.values():
            unchanged(record)
        output = (args.run_dir / "openocd.log").open("xb")
        process = subprocess.Popen([args.openocd, "-f", files["config"]["path"]],
                                   cwd=str(Path(files["config"]["path"]).parent),
                                   stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        output.close()
        log.summary.update(hardware_access_performed=True, openocd_pid=process.pid)
        log.state("waiting_for_tcl")
        rpc = TclRPC(wait_for_tcl(process, log, args.startup_timeout), log,
                     args.command_timeout)
        rpc.command("targets " + tcl_word(args.target), "select_target")
        rpc.command(f"adapter speed {args.adapter_khz}", "set_reviewed_adapter_speed")
        rpc.command(f"halt {args.halt_ms}", "halt_old_linux")
        rpc.command("arm7_9 fast_memory_access disable", "disable_fast_memory_access")
        rpc.command(args.target + " configure -work-area-size 0", "disable_work_area")
        initial_regs = rpc.get_reg(["pc", "cpsr", "r0", "r1", "r2"])
        log.summary["initial_registers"] = {k: hex(v) for k, v in initial_regs.items()}
        rpc.command(f"set {COMMIT_VARIABLE} 0", "initialize_commit_marker")
        log.state("read_only_preflight")
        verify_mac_identity(rpc, files["expected_mac"], log)
        source_checked(rpc, files["preflight"], "external_read_only_preflight")
        if rpc.commit_state() != 0:
            raise LaunchError("preflight unexpectedly marked a quiesce commit")
        log.state("quiesce_starting")
        # Recovery must be present and unchanged at the last reversible boundary.
        unchanged(files["rollback"])
        rpc.command("set COZY_ALLOW_QUIESCE reviewed", "arm_reviewed_quiesce")
        quiesce_invoked = True
        source_checked(rpc, files["quiesce"], "external_reviewed_quiesce")
        if rpc.commit_state() != 1:
            raise LaunchError("quiesce did not leave its mandatory commit marker")
        old_linux_resumable = False
        log.state("quiesced_no_old_linux_resume")
        # ARM926 soft_reset_halt is the coordinator-reviewed OpenOCD operation,
        # not an improvised hardware reset or a peripheral-register sequence.
        rpc.command("soft_reset_halt", "arm926_soft_reset_halt")
        rpc.command("wait_halt 10000", "confirm_halted_after_soft_reset")
        check_cpu_for_entry(rpc, log)
        log.state("loading_ram")
        load_and_verify(rpc, files["kernel"], KERNEL_ADDRESS, "kernel", log)
        load_and_verify(rpc, files["dtb"], DTB_ADDRESS, "dtb", log)
        if bytes(rpc.read_memory(DTB_ADDRESS, 8, 4)) != b"\xd0\x0d\xfe\xed":
            raise LaunchError("DTB magic readback mismatch")
        check_cpu_for_entry(rpc, log)
        expected = {"cpsr": 0xD3, "r0": 0, "r1": 0xFFFFFFFF,
                    "r2": DTB_ADDRESS, "pc": KERNEL_ADDRESS}
        pairs = " ".join(f"{name} {value:#x}" for name, value in expected.items())
        rpc.command("set_reg {" + pairs + "}", "stage_boot_registers")
        # IMPORTANT: get_reg -force here can discard dirty register values
        # prepared by set_reg. OpenOCD flushes that context on resume. Verify
        # the pending context without -force and do not claim hardware readback.
        staged = rpc.get_reg(list(expected), force=False)
        if staged != expected:
            raise LaunchError("staged boot registers differ from the required values")
        if rpc.sctlr() & ((1 << 0) | (1 << 2) | (1 << 12)):
            raise LaunchError("SCTLR changed before kernel entry")
        log.state("verified_ready_to_enter", staged_registers={k: hex(v) for k, v in staged.items()},
                  staged_not_forced_hardware_readback=True)
        # Exact WDT feed explicitly supplied/reviewed by the coordinator. No
        # mode-register write and no further target checks before kernel entry.
        rpc.command("write_memory 0xfffffe40 32 {0xa5000001} phys", "final_reviewed_watchdog_feed")
        rpc.command(f"resume {KERNEL_ADDRESS:#x}", "enter_pinned_zimage_once")
        log.state("kernel_entry_requested_not_boot_confirmed", openocd_left_running=True)
        log.event("completed", meaning="resume acknowledged; successful Linux/SSH boot is not established",
                  openocd_pid=process.pid)
        return 0
    except BaseException as error:
        # A failed/partial quiesce source can have changed peripherals already.
        # Query its explicit boundary; if that cannot be established, do NOT
        # resume an arbitrary context or reset the board.
        safe_to_resume = old_linux_resumable and not quiesce_invoked
        if rpc is not None:
            try:
                safe_to_resume = old_linux_resumable and rpc.commit_state() == 0
            except Exception:
                safe_to_resume = False
        resumed = False
        if rpc is not None and safe_to_resume:
            try:
                rpc.command("resume", "resume_old_linux_before_commit")
                resumed = True
            except Exception:
                pass
        log.state("aborted_old_linux_resumed" if resumed else "aborted_recovery_required",
                  error_type=type(error).__name__, error=str(error), old_linux_resumed=resumed,
                  openocd_left_running=process is not None and process.poll() is None,
                  rollback_requires_coordinator=True)
        log.event("aborted", old_linux_resumed=resumed,
                  recovery="reviewed external rollback required; no automatic reset was executed")
        return 2
    finally:
        if rpc is not None:
            rpc.sock.close()
        # Deliberately do not call shutdown/terminate/kill or source rollback.
        # OpenOCD remains available on loopback for the coordinator's recovery.
        log.events.close()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--dtb", type=Path, required=True)
    parser.add_argument("--preflight-tcl", type=Path, required=True)
    parser.add_argument("--quiesce-tcl", type=Path, required=True)
    parser.add_argument("--rollback-tcl", type=Path, required=True)
    parser.add_argument("--expected-mac-file", type=Path, required=True,
                        help="local extracted ethmac file; identifier is compared but never displayed")
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="new evidence directory; never reuse a previous run")
    parser.add_argument("--openocd-config", type=Path,
                        default=Path("<CHEMIN_LOCAL>"))
    parser.add_argument("--openocd", default="openocd")
    parser.add_argument("--target", default="at91sam9g25.cpu")
    parser.add_argument("--adapter-khz", type=int, default=1000)
    parser.add_argument("--startup-timeout", type=float, default=30)
    parser.add_argument("--command-timeout", type=float, default=900)
    parser.add_argument("--halt-ms", type=int, default=10000)
    parser.add_argument("--execute", action="store_true",
                        help="explicitly perform one reviewed attempt; otherwise only validate local inputs")
    return parser.parse_args()


def main():
    args = arguments()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", args.target):
        raise LaunchError("invalid target name")
    if (args.startup_timeout <= 0 or args.command_timeout <= 0 or args.halt_ms <= 0
            or args.adapter_khz <= 0):
        raise LaunchError("timeouts must be positive")
    args.run_dir = args.run_dir.resolve()
    paths = {"kernel": args.kernel, "dtb": args.dtb, "config": args.openocd_config,
             "preflight": args.preflight_tcl, "quiesce": args.quiesce_tcl,
             "rollback": args.rollback_tcl, "expected_mac": args.expected_mac_file}
    files = {name: validate_file(path.resolve(),
                                KERNEL_SHA256 if name == "kernel" else
                                DTB_SHA256 if name == "dtb" else None)
             for name, path in paths.items()}
    kernel_end = KERNEL_ADDRESS + files["kernel"]["bytes"]
    dtb_end = DTB_ADDRESS + files["dtb"]["bytes"]
    if not (DDR_START <= KERNEL_OUTPUT_START < KERNEL_BSS_END < DTB_ADDRESS < dtb_end
            <= KERNEL_ADDRESS < kernel_end <= DECOMPRESSOR_END <= DDR_END):
        raise LaunchError("pinned kernel/DTB memory plan is not disjoint inside DDR")
    if not args.execute:
        print(json.dumps({"mode": "local_validation_only", "hardware_access_performed": False,
                          "openocd_started": False, "inputs": visible_inputs(files),
                          "kernel_address": hex(KERNEL_ADDRESS), "dtb_address": hex(DTB_ADDRESS),
                          "command_timeout_s": args.command_timeout,
                          "automatic_rollback": False,
                          "execution_requires_explicit_flag": "--execute"}, indent=2))
        return 0
    return run(args, files)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LaunchError as error:
        print(f"Refused before launch: {error}", file=sys.stderr)
        raise SystemExit(2)
