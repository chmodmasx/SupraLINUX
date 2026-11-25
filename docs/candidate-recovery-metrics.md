# Candidate recovery and live metrics

This temporary candidate-specific QA workflow reuses the existing exact ISO
from run 45628300933. The recovery test boots an offline KVM guest with a
fresh sparse disk tagged SUPRAQA-ROLLBACK, creates a synthetic Btrfs layout,
executes the shipped recovery helper, and verifies restored root contents,
unchanged home, retained source snapshot and previous root. It does not use
a host block device or perform an installed-system reboot after rollback.
The independent metrics test records guest time-to-ready, uptime, available
memory, load, processes and swap after a 30-second settling interval.
These are live VM observations, not installed OS benchmarks or hardware
performance guarantees. Neither result certifies power-loss recovery.
The fixed artifact selector is temporary and must not merge unchanged.
