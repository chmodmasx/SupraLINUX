# SupraLINUX

A personal Linux distribution based on **Ubuntu 26.04 LTS**, with **KDE Plasma 6.6.7**, the Calamares installer, Secure Boot, and Btrfs recovery.

> **Status:** 1.0.0 Aurora in preparation.  
> Personal project, no warranty. Not affiliated with Canonical, Ubuntu, or KDE.

Website: <https://supralinux.com>

## What it is

SupraLINUX aims for a complete KDE desktop, an LTS base, and the tools needed to install, update, and recover the system without surprises.

It includes:

- KDE Plasma 6.6.7, Frameworks 6.24, Gear 25.12.3, and Qt 6.10.2.
- Calamares installer with Btrfs, LUKS, and data RAID.
- Secure Boot on BIOS and UEFI, using Ubuntu's signed chain.
- Snapper and recovery from the live environment.
- Firefox with Spanish language packs.
- Keyring/Secret Service working from first login.
- Aurora theme, fonts, and desktop defaults.
- Signed APT repository for our own packages.

The ISO will be published when the 1.0.0 release is validated.

## Base

| Component | Version |
|---|---|
| Base | Ubuntu 26.04 LTS |
| Desktop | KDE Plasma 6.6.7 |
| Frameworks | 6.24 |
| Gear | 25.12.3 |
| Qt | 6.10.2 |
| Architecture | amd64 |

## Repository

```text
packages/       Debian packaging
branding/       Visual identity, GRUB, Plymouth, and wallpapers
installer/      Calamares configuration and recovery
tools/          Build, import, and live tools
tests/          Tests and fixtures
docs/           Documentation
manifests/      Build and release records
```

## Documentation

- [Documentation index](docs/README.en.md)

Full documentation is published with the 1.0.0 release.

## Build

The build uses a clean environment with `sbuild`/`unshare` and a retained rootfs. Full steps are published with the 1.0.0 release documentation.

No installed distribution is modified. Tests run on an ISO, rootfs, or disposable VM.

## Security

For KDE or Ubuntu issues, use their official channels. For issues in SupraLINUX packaging, defaults, or integration, report privately:

- `https://supralinux.com/bugs.html` (mark “security” in the summary).
- When the repository is public, a private security advisory will be enabled.

Do not open public issues for vulnerabilities. See [SECURITY.en.md](SECURITY.en.md).

## Contributing

The project is developed locally and does not assume a CI platform. Branch, commit, testing, and DCO rules are in [CONTRIBUTING.en.md](CONTRIBUTING.en.md).

## License

Original code and configuration use **GPL-2.0-or-later**, with per-package exceptions. Artwork, sounds, fonts, and KDE-derived parts have their own licenses. See [LICENSE](LICENSE), [THIRD-PARTY.md](THIRD-PARTY.md), and [LICENSES/](LICENSES/).

Documentation is published under **CC BY-SA 4.0**.

## Trademark

SupraLINUX is the project name. Ubuntu's name and logo are not used to identify the product. “Based on Ubuntu” is a descriptive reference.

Forks and derivatives must use their own name and logo and must not imply endorsement by SupraLINUX, Canonical, Ubuntu, or KDE.

## Credits

To KDE, Ubuntu, Calamares, Noto, Breeze, and the other projects whose licenses and attributions are preserved in each package.
