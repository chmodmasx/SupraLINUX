# Installed graphical readiness

PR #22 run 45769015656 proved Btrfs installation and installed-system
contract PASS (7 checks). Artifact 15092858677 installed/screen.ppm
is black. Active graphical.target and SDDM service alone do not
prove a visible login screen or a logged-in Plasma session.

This optional --verify-greeter gate requires an active SDDM greeter
session, matching process, and two nonblank framebuffer samples.
Retain session and SDDM diagnostics. The image heuristic rejects
blank/cursor-only frames; it does not recognize login UI semantics.
This is static preparation, not a verified greeter or login. Wire
into the candidate install driver after current matrix completes.
Do not change product autologin, disable authentication or claim
logged-in Wayland desktop based on these checks. A subsequent
observed login and session check is still required.
