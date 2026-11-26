# Installed storage and boot security contract

Read-only optional extensions to the existing guest checker. The default
unencrypted installed-system caller remains unchanged. Explicit
--encryption none verifies a direct root partition; --encryption luks2
requires an active crypt root, single backing LUKS device, successful
LUKS2 JSON metadata inspection, matching crypttab passphrase entry and a
separate unencrypted ext4 /boot as specified in partition.conf.
--mode uefi-secure additionally requires actual EFI SecureBoot=1 and
SetupMode=0. No keys, passphrases or raw metadata are written to evidence.

This is preparation for the matrix, not a LUKS2 installation driver or
unlock automation. Unit fixtures cover malformed EFI flags, metadata
and crypttab; real storage topology and initramfs unlock require an
installed VM. The current boot-installed.py has not yet been changed
to request these optional flags; integrate that once the first boot
and encrypted partition UI are observed. Do not report runtime PASS
from static tests.
