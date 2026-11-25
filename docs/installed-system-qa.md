# Installed system QA contract

The independent read-only guest checker `tools/qa/installed-contract.py`
is intended to run after Calamares finishes and a disposable VM boots from
its installed disk, with the ISO removed. It must not be run on the owner's
physical system as a substitute for QA. The eventual VM harness supplies
the chosen boot mode, filesystem, test username, expected package versions
from the same source inventory, and live machine-id when captured.

It checks distribution identity and non-live boot, dpkg and exact overlay
versions, removal of live-only packages and permissions, mounted root and
Btrfs subvolumes (when applicable), ESP/GRUB and running kernel/initramfs,
test-user home ownership, essential services, testing APT source, and actual
ZRAM size, compression and priority. The JSON output separates checks so
a single failure does not hide the remaining results.

Unit tests exercise the ZRAM contract against synthetic 2–64 GiB memory
configurations and bad outcomes. These are not measured performance results.
Actual integration requires the automated Calamares driver and first boot
in KVM. Secure Boot enforcement, encryption and rollback interruption
remain separate scenarios, not certified by this checker.
