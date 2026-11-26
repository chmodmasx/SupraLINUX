# Calamares transaction QA

The standalone driver uses the actual captured 1280x800 Calamares Spanish
sidebar selection colors and QMP tablet input. It checks every page transition
and uses the dedicated tagged 40 GiB qcow2 disk only. User and password are
disposable test fixture values, not production credentials. The initial
candidate workflow stops at the confirmation dialog, reports PREVIEW_READY,
and verifies the disk is still blank. No installation PASS is claimed.

The commit path requires a reviewed confirmation button crop SHA-256 and click
within that crop. It refuses a changed dialog, requires the finished page,
and calls the installed-system contract by rebooting the same virtual disk
with no ISO and preserved UEFI variables. Commit path is unvalidated until
a real run. The temporary artifact selector must not merge unchanged.

## Welcome readiness regression

Run 45754757653 failed at the first transition. Its initial welcome.ppm
shows KDE's Welcome Center in front of Calamares, with inactive Next; its
later frames match the unobscured welcome logo and Next regions of the
successful discovery run 45752676747. Calamares logs show asynchronous
requirements finished after the window appeared. The previous sidebar
classifier accepted the obscured frame. This is evidence of a readiness
and focus defect in QA, not an established installer defect.

Wait for completed requirements, use a neutral focus click outside controls,
and require two unobscured welcome samples before navigation. The two crop
digests are from the pinned candidate and discovery frames, excluding the
clock. Unknown frames fail closed. Separate tablet motion, press and release
to avoid timing ambiguity. Retain before/after focus frames. No change to
the product or disk guard; no blind retries of Next or confirmation.
The crop profile and runtime behavior require revalidation for other ISOs.
