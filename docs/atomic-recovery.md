# Atomic root exchange

Run 45769104623 proved renameat2(RENAME_EXCHANGE) on sibling Btrfs
subvolumes on the candidate kernel with clean remounts. Replace the
two root renames with one exchange, sync the prepared snapshot before
activation, sync the exchange before naming the former root, serialize
helper invocations and fail closed without deleting either root on
ambiguous interruption. Backup naming is not the activation step.
If interrupted, @rollback-* may contain either the prepared or previous
root; do not automatically delete these or blindly replay exchange.
Automated reconciliation by recorded subvolume IDs and actual abrupt
power-cut/fault-injection testing remain pending. This change removes
the namespace gap, not a proof of power-loss durability or recovery
against arbitrary hardware failure.

The temporary candidate workflow injects the exact checked-out helper
into a disposable live guest and records its SHA-256. It tests the real
backend against the existing synthetic fixture, not the packaged ISO
or an installed system. Remove the cross-run artifact workflow before
merge and validate the resulting same-run ISO.

## Evidence and permanent CI

Run 45771451444 passed against the exact checked-out helper (SHA-256
4f54dc0f1ee0c3707656b63a6297be1f4a03658bb86ba1d765c705c153b73d1a).
Run 45771451393 built a new ISO and passed nine of nine jobs including
packaged recovery, BIOS, UEFI, Secure Boot, and metrics. Static CI
45771451425 passed six of six. The temporary cross-run workflow has
been removed; the existing same-run ISO recovery gate remains.
Revalidate the synchronized testing tree before merging.
