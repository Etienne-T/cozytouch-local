#!/usr/bin/env python3
"""State machine of ct-update.lua, run by the ARM LuaJIT of the image under qemu-arm.

CT_TEST=1: no remount and no reboot; the directories are temporary.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

work = Path(sys.argv[1]).resolve()
here = Path(__file__).resolve().parent
runtime = work / "latest-trees/root"
script = runtime / "usr/libexec/ct/ct-update.lua"
factory = runtime / "usr/share/cozytouch/phase2"


def archive(files, corrupt=None):
    parts = [b"CTAPP1\n"]
    for name, data in files.items():
        digest = hashlib.sha256(data).hexdigest()
        if corrupt == name:
            digest = "0" * 64
        parts.append(f"F {name} {len(data)} {digest}\n".encode() + data)
    parts.append(b"END\n")
    return b"".join(parts)


with tempfile.TemporaryDirectory(prefix="ctupd-") as temporary:
    base = Path(temporary)
    apps, run = base / "apps", base / "run"
    apps.mkdir()
    run.mkdir()
    env = dict(os.environ, CT_TEST="1", CT_APPS=str(apps), CT_RUN=str(run), CT_FACTORY="/factory")

    def ct(*args, data=b"", code=0):
        result = subprocess.run(["qemu-arm", "-cpu", "arm926", "-L", runtime, runtime / "usr/bin/luajit",
                                 script, *args], input=data, capture_output=True, env=env, timeout=60)
        out = result.stdout.decode()
        assert result.returncode == code, f"{args} rc={result.returncode}\n{out}{result.stderr.decode()}"
        return out

    def link(name):
        path = apps / "app" / name
        return os.readlink(path) if path.is_symlink() else None

    def snapshot():
        root = apps / "app"
        if not root.exists():
            return None
        def value(p):
            if p.is_symlink():
                return "link:" + os.readlink(p)
            return "dir" if p.is_dir() else p.read_bytes().hex()
        return sorted((str(p.relative_to(root)), value(p)) for p in root.rglob("*"))

    def boot():
        out = ct("boot-select")
        return out, (run / "app-mode").read_text().strip(), (run / "app-dir").read_text().strip()

    def healthy():
        return ct("promote")

    good = {p.name: p.read_bytes() for p in sorted(factory.glob("*.lua")) if p.name != "radio-start.lua"}
    v1 = archive(good)
    v2 = archive(dict(good, **{"service.lua": good["service.lua"] + b"\n-- v2\n"}))
    sha1, sha2 = hashlib.sha256(v1).hexdigest(), hashlib.sha256(v2).hexdigest()
    ver1, ver2 = "v-" + sha1[:12], "v-" + sha2[:12]

    out, mode, directory = boot()
    assert mode == "factory" and directory == "/factory", out
    print("BOOT no /apps/app: factory application from root A")

    assert "UPDATE_STAGED version=" + ver1 in ct("install", sha1, data=v1)
    assert link("next") == ver1 and link("current") is None
    out, mode, directory = boot()
    assert mode == "trial" and directory == str(apps / "app" / ver1) and link("trying") == ver1 and link("next") is None
    assert "APP_PROMOTED version=" + ver1 in healthy()
    assert link("current") == ver1 and link("trying") is None and (run / "app-mode").read_text() == "current\n"
    out, mode, _ = boot()
    assert mode == "current", out
    print("INSTALL, one trial, promotion after health, then current at next boot")

    healthy()
    ct("install", sha2, data=v2)
    out, mode, _ = boot()
    assert mode == "trial" and link("trying") == ver2
    out = ct("abandon")
    assert "APP_TRIAL_FAILED version=" + ver2 in out and "REBOOT_REQUESTED" in out
    assert link("trying") is None and link("current") == ver1
    out, mode, directory = boot()
    assert mode == "current" and directory.endswith(ver1)
    print("TRIAL_FAILURE trying dropped, one reboot requested, back to current")

    healthy()
    ct("install", sha2, data=v2)
    boot()
    out, mode, _ = boot()
    assert "APP_TRIAL_ABANDONED version=" + ver2 in out and mode == "current" and link("trying") is None
    print("POWER_CUT during trial: next boot abandons it and runs current")

    healthy()
    ct("install", sha2, data=v2)
    boot()
    healthy()
    assert link("current") == ver2 and link("previous") == ver1
    versions = sorted(p.name for p in (apps / "app").iterdir() if p.name.startswith("v-"))
    assert versions == sorted([ver1, ver2]), versions
    assert "UPDATE_ROLLBACK_STAGED version=" + ver1 in ct("rollback")
    assert link("next") == ver1
    print("ROLLBACK previous staged as next; pruning keeps current and previous")
    os.unlink(apps / "app" / "next")

    boot()
    before = snapshot()
    refusals = [
        ("sha256", ["install", "0" * 64], v2),
        ("usage", ["install", "xyz"], v2),
        ("format", None, b"TAR\n"),
        ("entry", None, archive({"../x.lua": b"", "service.lua": b""})),
        ("entry", None, archive({"Service.lua": b""})),
        ("no_service", None, archive({"config.lua": b"return 1\n"})),
        ("lua_syntax", None, archive({"service.lua": b"this is not lua ("})),
        ("truncated", None, v2[:-4]),
        ("file_sha256", None, archive(dict(good), corrupt="config.lua")),
        ("archive_size", None, b"CTAPP1\n" + b"-" * (4 * 1024 * 1024)),
        ("already_current", None, archive(dict(good, **{"service.lua": good["service.lua"] + b"\n-- v2\n"}))),
    ]
    for reason, args, data in refusals:
        if args is None:
            args = ["install", hashlib.sha256(data).hexdigest()]
        out = ct(*args, data=data, code=2)
        assert f"UPDATE_REFUSED {reason}" in out, (reason, out)
        assert snapshot() == before, reason
    print("REFUSALS sha256, usage, format, traversal and names, no service, Lua syntax, truncation, "
          "file hash, size, already current: state unchanged")

    ct("install", sha1, data=v1)
    boot()
    assert "UPDATE_REFUSED trial_in_progress" in ct("install", sha2, data=v2, code=2)
    healthy()
    print("TRIAL_IN_PROGRESS install refused until promotion")

    victim = apps / "app" / link("current") / "config.lua"
    victim.write_bytes(victim.read_bytes() + b"-- tampered\n")
    out, mode, directory = boot()
    assert "APP_CURRENT_INVALID" in out and mode == "factory" and directory == "/factory"
    extra = apps / "app" / link("previous") / "extra.lua"
    extra.write_bytes(b"return 1\n")
    assert "valid=false" in ct("status")
    print("MANIFEST tampered current or extra file: factory application; status reports invalid")
