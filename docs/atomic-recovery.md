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
