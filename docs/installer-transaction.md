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

## Parallel candidate scenarios

Run 45767814663 reached PREVIEW_READY. Reviewed confirmation.ppm (artifact
15092727409) shows the actual Install now button, /dev/vda, EFI and Btrfs
plan. The Btrfs job uses the exact reviewed modal crop and runs the existing
first-boot contract. EXT4 explores the dropdown and verifies the requested
root filesystem in the generated plan, then stops at confirmation. LUKS2
only explores the encryption controls and preserves the blank disk; status
DISCOVERY_READY is not an installation or encryption PASS. All jobs use the
same pinned ISO, isolated disposable disks and fail-fast false. No disk
images are published. This temporary workflow remains experimental.

## Second matrix

Run 45769015656: Btrfs installation and disk-only first boot PASS (all seven
installed contract checks), EXT4 PREVIEW_READY and LUKS2 DISCOVERY_READY.
The EXT4 confirmation crop from artifact 15092843015 matches the reviewed
Btrfs crop exactly; generated root plan is ext4. Enable commit and pass the
actual filesystem to the installed checker. Require the explicit Calamares
no-error completion log before reboot. The encryption screenshot from
15093780002 shows the two password fields at y550. Fill those disposable
fields and navigate to the summary, requiring the separate ext4 /boot plan;
no encrypted disk writes authorized until plan and unlock are verified.

## Third matrix: input reliability and visible greeter

Run 45771355048: both unencrypted installations completed and booted, with
six of seven contract checks passing. Actual useradd in both logs was
supraq, not supraqa; hostname supraqates was also truncated in the earlier
successful run. LUKS2 screenshot showed mismatched password lengths,
a disabled Next button, and the intended EFI/ext4 /boot/LUKS2 layout.
Replace asynchronous send-key with explicit press/release input events and
settling delays; capture filled fields. Do not loosen the user assertion.
Merge current testing into this branch (includes #24 and #26), enable the
optional greeter gate and direct unencrypted root check. LUKS2 stays preview.

Run 45785493220: EXT4 full installation/boot/greeter PASS; LUKS2 preview
PASS including separate ext4 /boot; Btrfs installed, user and seven other
checks passed except encryption verification used anonymous MAJ:MIN 0:30.
Resolve actual block source and require single Btrfs backing member instead.
The greeter gate remains mandatory for unencrypted commit scenarios.

## Encrypted installation discovery branch

Run 45785493220 artifact 15100228650: reviewed summary shows GPT, EFI
300 MiB, separate ext4 /boot 4 GiB, remaining root LUKS2 with Btrfs inside.
The confirmation modal crop matches the previous reviewed hash; require
an additional exact partition-plan crop and log LUKS2 assertion before
commit. The encrypted disk itself must pass cryptsetup isLuks --type luks2
and partition filesystem checks. Capture offline disk-only boot frames
without guessing an unlock prompt. UNLOCK_DISCOVERY_READY is a screenshot
collection status, not verified unlock or installed-system PASS. The
existing unencrypted matrix remains independently active on PR #22.
