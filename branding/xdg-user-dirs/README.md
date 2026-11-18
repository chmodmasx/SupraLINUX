# XDG user directory translations

`locale/` contains the compiled gettext catalogs from the upstream
`xdg-user-dirs` 0.19 source:

- Source: `xdg-user-dirs_0.19.orig.tar.xz`
- SHA-256: `e92deb929c10d4b29329397af8a2585101247f7e6177ac6f1d28e82130ed8c19`
- Upstream: https://www.freedesktop.org/wiki/Software/xdg-user-dirs/
- License: GPL-2.0-or-later (see the source package and
  `/usr/share/doc/xdg-user-dirs/copyright` in the rootfs).

The Ubuntu 26.04 binary package does not install these catalogs, so
`xdg-user-dirs-update` otherwise leaves the directory names in English even
when the user selected another language. The files were generated with:

```sh
for po in xdg-user-dirs-0.19/po/*.po; do
    lang=$(basename "$po" .po)
    mkdir -p "locale/$lang/LC_MESSAGES"
    msgfmt -o "locale/$lang/LC_MESSAGES/xdg-user-dirs.mo" "$po"
done
```

`tools/live/customize-rootfs.sh` copies `locale/` into
`/usr/share/locale/`. This is translation data only; it does not replace the
Ubuntu package or its code.
