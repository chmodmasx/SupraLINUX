# Installed disk boot harness

The QA-only runner `tools/qa/boot-installed.py` requires a standalone
disposable qcow2 file created by the installer harness, not a host block
device. It boots with no ISO, no network and QEMU snapshot mode so the
original test image is preserved. UEFI requires the variable store from the
installation VM. It checks QMP KVM acceleration, waits for the guest agent
and the installed identity, and invokes the independent installed-system
contract using package versions from the source inventory. Output includes
the guest contract, console, QMP screenshot and first-boot timing.

The harness depends on the boot-live QMP helper in PR #13. It does not
install the OS or unlock LUKS2. The encrypted and Secure Boot installed
scenarios require explicit additional firmware and unlock automation.
Unit tests verify command construction and contract arguments; no actual
installed boot is certified until an installer run provides the disk.
