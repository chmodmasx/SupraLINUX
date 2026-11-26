# Reusable live guest probes

The recovery and metrics probes use the ISO supplied by the caller and the
QMP implementation from the same checkout. They do not select or depend on
any previous Actions run. Guest operations are isolated in separate shell
modules. The recovery probe only creates a synthetic Btrfs layout on a
dedicated empty disposable disk identified by its fixed virtual serial.
The metrics probe is read-only. Neither certifies an installed system,
hardware performance, power-loss recovery or encrypted rollback.

After the ISO pipeline has created and checksum-verified a candidate, these
entry points may be executed in separate KVM jobs. No local manual owner
testing is required.

```sh
python3 tools/qa/recovery-live-metrics.py "$ISO" "$RUN/recovery" --mode recovery
python3 tools/qa/recovery-live-metrics.py "$ISO" "$RUN/metrics" --mode metrics
```

The unit tests check the guest scripts and host helper contract; actual guest
execution remains necessary for product-level PASS.
