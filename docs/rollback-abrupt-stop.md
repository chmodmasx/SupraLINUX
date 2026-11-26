# Abrupt rollback stop QA

Four independent KVM jobs use the already-built #25 ISO (run 45771451393),
verify its SHA-256 and the exact packaged recovery helper SHA-256. The
product helper is unchanged. QA-only PATH wrappers pause just before or
after the real Python exchange, and just before or after the backup
rename. A host-side SIGKILL stops the exact QEMU child without shutdown;
a new live VM mounts the same disposable raw disk with normal Btrfs replay.

Before exchange, the current root must remain active; after exchange
but before sync either complete root is acceptable. After the exchange
sync the restored root must persist. At every boundary, @ exists,
the two root markers are complementary, @home and the source snapshot
are preserved. No repair, automatic replay of the rollback operation,
or external disk access. The raw test disk uses cache=none; the host
and physical storage remain powered, so this is a synthetic hard-stop
experiment, not a physical power-loss or arbitrary in-syscall guarantee.

All four cases are NOT_RUN until CI reports results. This temporary
cross-run workflow must be replaced with a same-run ISO gate before
merging; the experiment requires the #25 atomic helper.

Run 45785776774: all four cases exited before reaching their checkpoint;
no abrupt stop or replay occurred. Retain guest shell trace and helper log
on early exit, and explicitly set the QA wrapper PATH. No fault-tolerance
result is claimed. Keep the original pinned ISO and helper hash.

Run 45852386149 showed the real helper completed normally without reaching
any pause. A likely cause is execution restriction on /run; move wrappers
into a fresh /tmp directory, verify their direct execution and inherited
PATH in a child shell, then invoke the unchanged packaged helper. This is
an instrumentation hypothesis, not a demonstrated filesystem fault.
