# CI archive compatibility

Runs 45785574406 and 45785601685 stopped at rootfs dependency
resolution. The signed testing archive now offers theme 1.3.3
with Breaks: supralinux-defaults (< 1.3.0); this source tree stages
defaults 1.2.7. Last successful run 45771451393 installed theme 1.3.2
and then staged defaults 1.2.7. Temporarily pin the known compatible
theme version for this exact local overlay only, require availability
from the signed archive, assert both installed versions and remove
the build-only pin before ISO creation. No change to shipped update
policy, signing keys, testing repository, or stable channel.

This integration branch combines the independently reviewed #23 and
#25 trees (disjoint changes) and runs their permanent probes on ONE
shared ISO. Keep the original PRs as evidence until this integration
passes. A full synchronized source/archive update is still needed;
do not silently import or downgrade other product packages.
