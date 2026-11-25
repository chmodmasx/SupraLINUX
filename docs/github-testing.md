# GitHub testing development

## Scope and owner decisions

The only active development and distribution channel is testing. Stable is not authorized. No stable tag, release, APT promotion or publication may be performed without explicit owner approval. No workflow in the initial CI has publication permissions or a stable promotion path.

Preserve Ubuntu compatibility, including the existing os-release fields. Keep the working Firefox integration and the AR9565-specific workaround unless a verified regression or an equivalent tested replacement justifies a change. Prefer virtual-machine evidence over requesting manual hardware tests from the owner. Full reproducibility, comprehensive physical-hardware certification and long-term security/maintenance programs are deferred. CI is an incremental development tool rather than a new requirement to rebuild the entire distribution on every commit.

## Initial CI

The read-only Testing CI workflow runs existing static tests, builds the KDE Connect SFTP binary package using Ubuntu's Go toolchain and independently checks whether QEMU reports KVM acceleration. KVM availability is an infrastructure check, not a guest boot or a product PASS. The jobs do not publish packages or releases.

## Subsequent work

- Import the external builder inputs and define a runner workspace contract before attempting the existing offline sbuild flow in Actions. No historical manifest is proof of a new build.
- Add independent QEMU boot, installer and first-boot tests using disposable disks, QMP screenshots and serial logs. Use KVM when available. Label unavailable acceleration as INFRA_INVALID; do not silently substitute a product PASS.
- Use testing pre-releases only. GitHub release assets must be smaller than 2 GiB each; split larger ISO files with SHA-256 for each part and for the reassembled ISO, or link to an external ISO host. Publication is not implemented in the initial CI.
- Validate Calamares target consistency immediately before unmount. Test each supported storage/boot mode separately, including the actual package state and live-only cleanup.
- Evaluate ZRAM settings in VMs using repeatable memory pressure and responsiveness measurements before changing the default. Keep LZ4 and the current policy until comparisons justify a change.
