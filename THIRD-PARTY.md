# Third-party components

SupraLINUX includes code, artwork, fonts, and translation data from other
projects. This file is an index; the authoritative license and attribution
for each package is in its `debian/copyright`.

| Component | License | Where |
|---|---|---|
| KDE Plasma, Frameworks, Gear, Breeze | GPL/LGPL, per package | `packages/kde/`, `packages/plasma/`, `packages/gear/` |
| Breeze Plymouth theme | GPL-3.0-only or KDE-Accepted-GPL | `packages/desktop/supralinux-branding/usr/share/plymouth/` |
| GNU Unifont (GRUB `.pf2`) | GPL-2.0-or-later with font exception | `branding/grub/supralinux/unifont-*.pf2` |
| Ubuntu, Debian, casper | per package | `packages/system/casper/debian/copyright` |
| Calamares | GPL-3.0-or-later | `installer/`, package metadata |
| Noto Color Emoji | OFL-1.1 | `packages/fonts/noto-color-emoji/debian/copyright` |
| xdg-user-dirs translations | GPL-2.0-or-later | `branding/xdg-user-dirs/` |
| Go vendored modules (sftp, x/sys, x/crypto) | BSD | `packages/apps/supralinux-kdeconnect-sftp/vendor/` |
| Wallpapers | CC-BY-4.0 | `branding/`, `packages/desktop/supralinux-theme/` |
| Sounds | CC0-1.0 | `packages/desktop/supralinux-theme/` |
| Breeze-derived icon artwork | LGPL-3.0-or-later with KDE exception | `packages/desktop/supralinux-icons/debian/copyright` |
| Breeze-derived theme parts | LGPL-2.1-or-later | `packages/desktop/supralinux-theme/debian/copyright` |

## Xenlism

The GRUB layout is inspired by Xenlism, but no Xenlism backgrounds, icons,
fonts, or `theme.txt` assets were copied. The assets in
`branding/grub/supralinux/` are original.

## Full license texts

See `LICENSES/` for the complete texts used by the project's own work.
Third-party packages keep their own license files in their source packages
and in `debian/copyright`.
