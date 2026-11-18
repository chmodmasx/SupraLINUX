# Contributing to SupraLINUX

SupraLINUX is a personal project developed locally. It does not assume a CI
platform, a Git provider, or a pull-request workflow.

## Branches

- `main`: stable releases. No direct commits.
- `testing`: integration. Features, fixes, and tests go here.
- `feature/<topic>` and `fix/<topic>`: focused work, branched from `testing`.

A release is merged into `main` from `testing` or from a tested `hotfix`.
`main` may receive merges from tested branches and tags, not direct work.

## Commits

- Spanish messages with a prefix: `feat:`, `fix:`, `docs:`, `build:`,
  `test:`, `chore:`, `refactor:`.
- One commit per coherent unit. Do not mix unrelated areas.
- Do not include artifacts, disks, host screenshots, credentials, or logs.
- Sign commits with DCO: `git commit -s`.

## Testing

- Unit tests: `make check` once the tools are in the repo.
- Clean build: `sbuild`/`unshare` in a retained rootfs.
- Installation and desktop: ISO or disposable VM.
- Never modify an installed distribution. It is read-only diagnostics.
- Release tests run on the ISO, not on the host.

## Packaging

- Debian Policy and `debhelper`.
- Patches documented in `debian/patches/series`.
- Complete DEP-5 `debian/copyright`, including assets and vendor code.
- Versions `0supralinuxN`; clear changelog entries.
- Do not hide Build-Depends by preinstalling SDKs in the rootfs.
- Do not commit `.deb`, `.changes`, `.buildinfo`, `.dsc`, ISOs, `.qcow2`,
  logs, or `__pycache__`.

## Documentation

- Spanish is primary; `README.en.md` and `docs/README.en.md` cover English.
- Behavior changes are documented in the same commit or the corresponding
  docs commit.
- Architecture decisions go in `docs/decisions.md`.

## Security

Do not open public issues for vulnerabilities. See [SECURITY.en.md](SECURITY.en.md).

## License and DCO

By contributing, you agree that your contribution is distributed under the
license of the corresponding area (see [LICENSE](LICENSE)) and you certify the
DCO with `git commit -s`.
