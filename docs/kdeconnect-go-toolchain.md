# KDE Connect SFTP: Go toolchain correction

Version 1.0.3 corrects the Debian minimum Go dependency to `2:1.26~` to match `go.mod` (Go 1.26.0). Ubuntu 26.04 provides `golang-go` 2:1.26~1. The previous build manifest recorded Go 1.26.8; the change corrects the declared dependency, not the implementation.

Status: source change only, pending clean sbuild, updated build-input manifest, package smoke test and testing publication. The 1.0.2 release manifest and historical PASS evidence remain unchanged. Do not reuse the prior artifact or interpret it as evidence for 1.0.3. No stable release is authorized.
