# Independent candidate storage and memory probes

Exploratory QA, NOT_RUN at creation. The pinned ISO is the same candidate
used by PR #22. Each job uses its own offline KVM VM; no build duplication.
The ZRAM jobs exercise 2, 4, 8 and 12 GiB assigned RAM and the actual
installed-contract zram_policy function on the live system. A desktop
readiness failure is not a ZRAM-specific failure. The 8 GiB cap above
16 GiB of guest RAM remains unit-tested only; larger runtime cases require
a larger runner. This is not a comparative performance benchmark.

The atomic-exchange job tests renameat2(RENAME_EXCHANGE) on two sibling
Btrfs subvolumes on a dedicated 4 GiB fixture disk, with two clean remounts.
It tests the candidate primitive, not the current recovery helper,
power-loss durability, or a real installed OS. No fallback to the two
rename sequence. If supported, use the evidence to design a separately
reviewed recoverable transaction protocol and fault-injection matrix.
The candidate workflow uses a temporary cross-run artifact; do not merge
it unchanged. Integrate successful probes with the same-run ISO job.
