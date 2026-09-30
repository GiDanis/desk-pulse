# Orange Pi Zero 3W kernel fixes

`0001-sun60iw2-enable-cmn-pll-for-dp-altmode.patch` adds the missing CMN PLL1
clock enable to the A733 USB-C DP+USB (two-lane Alt Mode) PHY setup. The
currently installed 6.6.98 kernel reports a DP_D PLL-enable timeout and fails
clock recovery; manually applying that one register write at runtime allowed
the monitor link to train at 5.4 Gbit/s. The patch is intended for the Orange
Pi `orange-pi-6.6-sun60iw2` kernel source tree.

The patch is a kernel source change; it takes effect only after building and
booting the rebuilt kernel. Keep the stock `/boot/uImage` as a recovery copy
when installing a test image.

The locally built test kernel is `uImage.dpfix`; `boot.scr.dpfix` selects it only
when `/boot/orangepiEnv.txt` contains `kernel_test=1`, leaving the stock kernel
as the default when that flag is absent. The exact source commit, stock kernel
configuration, image hashes, and 960x640@60 test mode are recorded alongside
these files. The live register-write test trained the DP link; the rebuilt
kernel image still needs its boot test before the fix is considered persistent.
