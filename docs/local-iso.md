# Local testing ISO

After the testing ISO QA workflow has been validated and integrated, build from
a committed checkout on an amd64 Ubuntu 26.04-compatible host:

```sh
git switch testing
git pull --ff-only
make iso
```

The target checks host dependencies and reports a complete installation command
if they are missing. It never installs host packages automatically. It requires
at least 22 GiB free and sudo only for the mapped-root live builder and its
preflight. It clones the local committed tree into a fresh workspace, builds the
three current overlays, stages them, and invokes the same testing-only live
builder as CI. It never publishes a release or writes to the APT archive.

The default workspace is under `/var/tmp`. Set `SUPRALINUX_WORKSPACE` to a
larger filesystem if necessary; its path and all parent directories must be
traversable by uid 100000. Each build gets a new directory. The command prints
the output ISO and checksum, plus the retained logs and source commit. The
rootfs and other build evidence are intentionally not deleted automatically.
The checkout used to invoke make is not altered.

This command is initially experimental; a successful build is not evidence of
Calamares installation or a stable release.
