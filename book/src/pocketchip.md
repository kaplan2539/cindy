# PocketCHIP

## Linux

### LCD

Create a patch for CHIP's dts to enable the PocketCHIP lcd:
```
cat <<EOF |sed -e 's/^         / \t/; s/        /\t/g; s/+ $/+/g' >${BR2_EXTERNAL}/board/nextthingco/CHIP/linux/01-sun5i-r8-chip.dts.lcd.patch
--- a/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts	2026-07-12 01:17:12.549754373 +0200
+++ b/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts	2026-07-12 00:02:08.862363121 +0200
@@ -82,13 +82,42 @@
                 reset-gpios = <&pio 2 19 GPIO_ACTIVE_LOW>; /* PC19 */
         };
 
+        backlight: backlight {
+                compatible = "pwm-backlight";
+                pwms = <&pwm 0 8000 1>;
+                brightness-levels = <0 1 2 4 8 12 16 24 28 32 100>;
+                default-brightness-level = <8>;
+                enable-gpios = <&pio 3 18 GPIO_ACTIVE_HIGH>;
+        };
+        
+        panel {
+                compatible = "olimex,lcd-olinuxino-43-ts";
+                connector-type = "dpi";
+                power-supply = <&reg_vcc3v3>;
+                backlight = <&backlight>;
+        
+                port {
+                        panel_input: endpoint {
+                                remote-endpoint = <&tcon0_out_panel>;
+                        };
+                };
+        };
+
         onewire {
                 compatible = "w1-gpio";
                 gpios = <&pio 3 2 (GPIO_ACTIVE_HIGH | GPIO_PULL_UP)>; /* PD2 */
         };
 };
 
+&pwm {
+        pinctrl-names = "default";
+        pinctrl-0 = <&pwm0_pin>;
+        status = "okay";
+};
+
 &be0 {
+        /delete-property/ interconnects;
+        /delete-property/ interconnect-names;
         status = "okay";
 };
 
@@ -237,11 +266,28 @@
 };
 
 &tcon0 {
+        pinctrl-names = "default";
+        pinctrl-0 = <&lcd_rgb565_pins>;
         status = "okay";
 };
 
+&tcon0_out {
+        #address-cells = <1>;
+        #size-cells = <0>;
+
+        tcon0_out_panel: endpoint@0 {
+                reg = <0>;        
+                remote-endpoint = <&panel_input>;
+        };
+
+        endpoint@1 {
+                reg = <1>;        
+                status = "disabled";
+        };
+};
+
 &tve0 {
-        status = "okay";
+        status = "disabled";
 };
 
 &uart1 {
EOF
```

Create Linux configuration fragment:
```
cat <<EOF >"${BR2_EXTERNAL}"/board/nextthingco/CHIP/linux/lcd.cfg
CONFIG_DRM_FBDEV_EMULATION=y
CONFIG_FB=y
CONFIG_FB_DEVICE=y
CONFIG_PINCTRL_AXP209=y
EOF
```
TODO: enable .../lcd.cfg in "${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig

### Keyboard

dts patch to enable the keyboard:
```
cat <<EOF |sed -e 's/^         / \t/; s/        /\t/g; s/+ $/+/g' >${BR2_EXTERNAL}/board/nextthingco/CHIP/linux/02-sun5i-r8-chip.dts.keyboard.patch
--- a/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts	2026-07-22 23:32:47.354576484 +0200
+++ b/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts	2026-07-22 22:51:19.533940030 +0200
@@ -49,6 +49,7 @@
 
 #include <dt-bindings/gpio/gpio.h>
 #include <dt-bindings/interrupt-controller/irq.h>
+#include <dt-bindings/input/input.h>
 
 / {
 	model = "NextThing C.H.I.P.";
@@ -160,7 +161,72 @@
 };
 
 &i2c1 {
-	status = "disabled";
+	status = "okay";
+	keyboard: keyboard@34 {
+		compatible = "ti,tca8418";
+		reg = <0x34>;
+		interrupt-parent = <&pio>;
+		interrupts = <6 1 IRQ_TYPE_EDGE_FALLING>;
+		keypad,num-rows = <6>;
+		keypad,num-columns = <10>;
+		keypad,autorepeat;
+		linux,keymap = <
+			MATRIX_KEY(0, 0, KEY_EQUAL)
+			MATRIX_KEY(0, 1, KEY_1)
+			MATRIX_KEY(0, 2, KEY_2)
+			MATRIX_KEY(0, 3, KEY_3)
+			MATRIX_KEY(0, 4, KEY_4)
+			MATRIX_KEY(0, 5, KEY_5)
+			MATRIX_KEY(0, 6, KEY_6)
+			MATRIX_KEY(0, 7, KEY_7)
+			MATRIX_KEY(0, 8, KEY_8)
+			MATRIX_KEY(0, 9, KEY_9)
+			MATRIX_KEY(1, 0, KEY_Q)
+			MATRIX_KEY(1, 1, KEY_W)
+			MATRIX_KEY(1, 2, KEY_E)
+			MATRIX_KEY(1, 3, KEY_R)
+			MATRIX_KEY(1, 4, KEY_T)
+			MATRIX_KEY(1, 5, KEY_Y)
+			MATRIX_KEY(1, 6, KEY_U)
+			MATRIX_KEY(1, 7, KEY_I)
+			MATRIX_KEY(1, 8, KEY_O)
+			MATRIX_KEY(1, 9, KEY_P)
+			MATRIX_KEY(2, 0, KEY_A)
+			MATRIX_KEY(2, 1, KEY_S)
+			MATRIX_KEY(2, 2, KEY_D)
+			MATRIX_KEY(2, 3, KEY_F)
+			MATRIX_KEY(2, 4, KEY_G)
+			MATRIX_KEY(2, 5, KEY_H)
+			MATRIX_KEY(2, 6, KEY_J)
+			MATRIX_KEY(2, 7, KEY_K)
+			MATRIX_KEY(2, 8, KEY_L)
+			MATRIX_KEY(2, 9, KEY_ENTER)
+			MATRIX_KEY(3, 0, KEY_TAB)
+			MATRIX_KEY(3, 1, KEY_Z)
+			MATRIX_KEY(3, 2, KEY_X)
+			MATRIX_KEY(3, 3, KEY_C)
+			MATRIX_KEY(3, 4, KEY_V)
+			MATRIX_KEY(3, 5, KEY_B)
+			MATRIX_KEY(3, 6, KEY_N)
+			MATRIX_KEY(3, 7, KEY_M)
+			MATRIX_KEY(3, 8, KEY_UP)
+			MATRIX_KEY(3, 9, KEY_DOWN)
+			MATRIX_KEY(4, 0, KEY_ESC)
+			MATRIX_KEY(4, 1, KEY_RIGHTALT)
+			MATRIX_KEY(4, 2, KEY_LEFTALT)
+			MATRIX_KEY(4, 3, KEY_SPACE)
+			MATRIX_KEY(4, 4, KEY_RIGHTCTRL)
+			MATRIX_KEY(4, 5, KEY_SLASH)
+			MATRIX_KEY(4, 6, KEY_RIGHTSHIFT)
+			MATRIX_KEY(4, 8, KEY_LEFT)
+			MATRIX_KEY(4, 9, KEY_RIGHT)
+			MATRIX_KEY(5, 0, KEY_LEFTSHIFT)
+			MATRIX_KEY(5, 1, KEY_0)
+			MATRIX_KEY(5, 2, KEY_MINUS)
+			MATRIX_KEY(5, 3, KEY_BACKSPACE)
+			MATRIX_KEY(5, 4, KEY_DOT)
+		>;
+	};
 };
 
 &i2c2 {EOF
```

Create a Buildroot overlay to start getty on tty0:
```
mkdir -p "${BR2_EXTERNAL}"/overlay/etc
cat <<EOF >"${BR2_EXTERNAL}"/overlay/etc/inittab
# /etc/inittab
#
# Copyright (C) 2001 Erik Andersen <andersen@codepoet.org>
#
# Note: BusyBox init doesn't support runlevels.  The runlevels field is
# completely ignored by BusyBox init. If you want runlevels, use
# sysvinit.
#
# Format for each entry: <id>:<runlevels>:<action>:<process>
#
# id        == tty to run on, or empty for /dev/console
# runlevels == ignored
# action    == one of sysinit, respawn, askfirst, wait, and once
# process   == program to run

# Startup the system
::sysinit:/bin/mount -t proc proc /proc
::sysinit:/bin/mount -o remount,rw /
::sysinit:/bin/mkdir -p /dev/pts /dev/shm
::sysinit:/bin/mount -a
::sysinit:/bin/mkdir -p /run/lock/subsys
::sysinit:/sbin/swapon -a
null::sysinit:/bin/ln -sf /proc/self/fd /dev/fd
null::sysinit:/bin/ln -sf /proc/self/fd/0 /dev/stdin
null::sysinit:/bin/ln -sf /proc/self/fd/1 /dev/stdout
null::sysinit:/bin/ln -sf /proc/self/fd/2 /dev/stderr
::sysinit:/bin/hostname -F /etc/hostname
# now run any rc scripts
::sysinit:/etc/init.d/rcS

# Put a getty on the serial port
console::respawn:/sbin/getty -L  console 0 vt100 # GENERIC_SERIAL
tty1::respawn:/sbin/getty -L  tty1 0 linux

# Stuff to do for the 3-finger salute
#::ctrlaltdel:/sbin/reboot

# Stuff to do before rebooting
::shutdown:/etc/init.d/rcK
::shutdown:/sbin/swapoff -a
::shutdown:/bin/umount -a -r
EOF
```

## U-BOOT

```
cat <<EOF >"${BR2_EXTERNAL}"/board/nextthingco/CHIP/u-boot/lcd.cfg
# CONFIG_VIDEO_HDMI is not set
CONFIG_VIDEO_LCD_MODE="x:480,y:272,depth:18,pclk_khz:9000,le:10,ri:5,up:3,lo:8,hs:30,vs:5,sync:3,vmode:0"
CONFIG_VIDEO_LCD_BL_EN="PD18"
CONFIG_VIDEO_LCD_BL_PWM="PB2"
# CONFIG_VIDEO_LCD_BL_PWM_ACTIVE_LOW is not set
EOF
```

TODO: enable .../lcd.cfg in "${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
