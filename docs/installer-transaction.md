# Calamares transaction QA

The standalone driver uses the actual captured 1280x800 Calamares Spanish
sidebar selection colors and QMP tablet input. It checks every page transition
and uses the dedicated tagged 40 GiB qcow2 disk only. User and password are
disposable test fixture values, not production credentials. The initial
candidate workflow stops at the confirmation dialog, reports PREVIEW_READY,
and verifies the disk is still blank. No installation PASS is claimed.

The commit path requires a reviewed confirmation button crop SHA-256 and click
within that crop. It refuses a changed dialog, requires the finished page,
and calls the installed-system contract by rebooting the same virtual disk
with no ISO and preserved UEFI variables. Commit path is unvalidated until
a real run. The temporary artifact selector must not merge unchanged.
