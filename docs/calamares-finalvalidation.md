# Calamares final target validation (testing proposal)

Version 1.0.3 adds a separate shellprocess stage after cleanup and wallet initialization, before the success flag and unmount. It checks dpkg audit, absence of selected live packages and recovery permissions, offline APT parsing and testing source, a matching kernel/initramfs pair, GRUB syntax, machine-id format and enabled core services. Recovery purge errors are no longer ignored.

This is a first implementation, not a certified installer. The full final-target contract still needs VM-based coverage of EFI files and boot, Btrfs subvolume layout, LUKS2, user identity and permissions, machine-id uniqueness, apt candidate availability and first boot. The check of the testing suite is intentional: no stable publication is authorized. When stable is explicitly approved, revise that contract under a separate reviewed change.

Status: pending clean build, new build-input manifest and functional VM installation across supported modes. Prior version 1.0.2 manifests and results are historical and are not evidence for this change.
