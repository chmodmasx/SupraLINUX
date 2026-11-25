# Testing archive preflight

The signed archive diagnostic reads the checked-in testing source and public key
using isolated APT lists/cache/configuration. It does not install packages,
modify the host's APT sources, publish packages, or require a signing key.

Run as an unprivileged user on Ubuntu:

```sh
python3 tools/live/check-testing-archive.py /tmp/supralinux-archive-report.json
```

The JSON report records exact inventory versions present in the signed archive,
including which gaps affect the desktop profile. PASS only means those versions
are available; BLOCKED means a valid diagnostic found missing versions (the
diagnostic job itself can complete successfully); INFRA_INVALID means the
archive could not be inspected reliably and the process exits nonzero.

The workflow runs on relevant testing pull requests and retains the diagnostic
for seven days. Manual dispatch is subject to GitHub's default-branch workflow
availability; it does not authorize changes to main. This is not an ISO build,
package certification, or stable publication.
