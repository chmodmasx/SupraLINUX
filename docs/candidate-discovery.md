# Candidate discovery

Temporary candidate-specific workflow for the verified ISO from run 45628300933.
It checks a fixed SHA-256 before running two independent KVM guests. The
installer discovery guest has one newly-created 40 GiB sparse virtual disk,
no networking or host storage, and opens the real Calamares application to
capture the actual UI, logs, and available accessibility interfaces. It does
not select partitioning or execute installation. Secure Boot uses enrolled
Microsoft OVMF variables and requires SecureBoot=1 and SetupMode=0 in the
guest, in addition to a working live Plasma session.

This exploratory workflow is pinned to an expiring artifact; it must not be
merged as a permanent candidate selector. The reusable probe modules can be
integrated after the resulting evidence is inspected. No product publication.
