"""Prove Secure Boot from guest EFI state, not merely firmware choice."""
import argparse
import importlib.util
from pathlib import Path
import shutil


def load(path):
    spec = importlib.util.spec_from_file_location("candidate_boot", path)
    boot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boot)
    return boot


SECURE_CHECK = r"""
set -eu
test -d /sys/firmware/efi
secure=$(od -An -tu1 -j4 -N1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c | tr -d ' ')
setup=$(od -An -tu1 -j4 -N1 /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c | tr -d ' ')
test "$secure" = 1
test "$setup" = 0
echo "SecureBoot=$secure SetupMode=$setup"
"""


def secure_command(original, iso, output, runtime, mode):
    command = original(iso, output, runtime, "bios")
    code = Path("/usr/share/OVMF/OVMF_CODE_4M.secboot.fd")
    template = Path("/usr/share/OVMF/OVMF_VARS_4M.ms.fd")
    if not code.is_file() or not template.is_file():
        raise OSError("Secure Boot OVMF firmware or enrolled Microsoft variables missing")
    vars_file = runtime / "OVMF_VARS.fd"
    shutil.copyfile(template, vars_file)
    command[command.index("-machine") + 1] = "q35,accel=kvm,smm=on"
    command += ["-global", "driver=cfi.pflash01,property=secure,value=on",
                "-drive", f"if=pflash,format=raw,readonly=on,file={code}",
                "-drive", f"if=pflash,format=raw,file={vars_file}"]
    return command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("boot_helper", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    boot = load(args.boot_helper)
    original = boot.command_line
    # Preserve the exact candidate's live desktop checks, adding EFI enforcement.
    boot.CHECK = SECURE_CHECK + "\n" + boot.CHECK
    boot.command_line = lambda *a: secure_command(original, *a)
    return boot.run(args.iso.resolve(), args.output.resolve(), "uefi-secure", 420)


if __name__ == "__main__":
    raise SystemExit(main())
