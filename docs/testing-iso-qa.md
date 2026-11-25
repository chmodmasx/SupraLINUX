# Testing ISO QA

The testing-only workflow builds three local overlays from the same checked-out
PR merge tree: defaults, Calamares configuration and KDE Connect SFTP. Each
binary is checked against the inventory and retained temporarily. The staging
step rejects missing, duplicate, wrong-version or wrong-architecture overlays
and records their SHA-256 hashes.

The live builder invokes the existing mmdebstrap hooks and ISO assembly under
the documented subuid mapping. It uses the signed testing archive for remaining
packages and the pinned Ubuntu kernel. The rootfs contract rejects stale
inventory binaries before sealing. It requires a fresh output directory and
22 GiB free. The recovery GUI is required for this candidate.

This is an experimental QA workflow: no stable promotion, no APT publication,
no GitHub Release. A successful build and checksum do not certify guest boot
or installation. The ISO artifact is retained for three days. Logs and package
inventory evidence are retained for seven days. The first execution validates
the runner's storage and namespace assumptions. Manual dispatch depends on
default-branch availability; the initial PR triggers the workflow without
changing main.
