# GitHub testing development

## Scope and owner decisions

The only active development and distribution channel is testing. Stable is not authorized. No stable tag, release, APT promotion or publication may be performed without explicit owner approval. No workflow in the initial CI has publication permissions or a stable promotion path.

Preserve Ubuntu compatibility, including the existing os-release fields. Keep the working Firefox integration and the AR9565-specific workaround unless a verified regression or an equivalent tested replacement justifies a change. Prefer virtual-machine evidence over requesting manual hardware tests from the owner. Full reproducibility, comprehensive physical-hardware certification and long-term security/maintenance programs are deferred. CI is an incremental development tool rather than a new requirement to rebuild the entire distribution on every commit.

## Initial CI

The read-only Testing CI workflow runs existing static tests, builds the KDE Connect SFTP binary package using Ubuntu's Go toolchain and independently checks whether QEMU reports KVM acceleration. KVM availability is an infrastructure check, not a guest boot or a product PASS. The jobs do not publish packages or releases.

## Subsequent work

- Import the external builder inputs and define a runner workspace contract before attempting the existing offline sbuild flow in Actions. No historical manifest is proof of a new build.
- Add independent QEMU boot, installer and first-boot tests using disposable disks, QMP screenshots and serial logs. Use KVM when available. Label unavailable acceleration as INFRA_INVALID; do not silently substitute a product PASS.
- Do not publish ISOs to GitHub Releases. Use CI artifacts for temporary QA evidence only. The owner will clone the repository and build testing ISOs locally using the documented build procedure. Stable remains prohibited until explicit owner authorization.
- Validate Calamares target consistency immediately before unmount. Test each supported storage/boot mode separately, including the actual package state and live-only cleanup.
- Evaluate the experimental ZRAM policy in its independent testing branch using repeatable memory pressure and responsiveness measurements. Keep LZ4 initially. Do not claim measured performance gains before VM evidence exists.

## Change-aware CI

- Pull requests targeting testing run once per update. Push runs are restricted to testing, preserving post-merge integration checks. Superseded runs for the same ref are cancelled.
- Static and contract tests remain mandatory on every run. Install missing test dependencies only.
- The independent planner compares the checked-out tree against the event base using a NUL-delimited Git diff with renames treated as delete/add. It does not depend on the hosted path-filter file-count limit. Missing comparisons and manual runs select every expensive job.
- KDE Connect builds run for related sources, tests or build tooling. KVM capability runs for VM, installer, live-image or relevant builder changes. CI policy changes select both jobs.
- The planner runs in parallel with the static suite; expensive jobs are independently scheduled after planning. Skipped jobs mean not selected, never a fresh product PASS.
- The current Go package deliberately uses vendored dependencies and an isolated Debian build cache. Do not share that cache or bypass clean-build evidence merely for faster CI. Measure checkout, dependency installation and test duration before adding caches.
- Future ISO/VM workflows must check KVM on their own runner, not rely on the earlier capability result. No workflow publishes releases or promotes stable.
