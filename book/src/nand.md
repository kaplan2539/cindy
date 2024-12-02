# NAND Support

Thanks to Boris Brezillon, Linux supports the Toshiba NAND used on some CHIPs
in emulated SLC mode since version 5.8.
Chris Morgan added SLC mode support for the Hynix NAND on the original CHIP in
Linux version 5.16.

Unfortunately, U-Boot at the time of writing does not support the NAND memory
on CHIP out of the box.
However, Chris Morgan also provides patches for U-Boot v2022.01 in his
[chip-debroot](https://github.com/macromorgan/chip-debroot)
repository on Github.

In this chapter we'll first setup Linux to use CHIP's NAND in SLC mode, then
switch to the patched version of U-Boot 2022.01 which supports the NAND in SLC
mode and finally write special bootloader and rootfs images that allow for
booting CHIP from the NAND.

## Access the NAND from Linux

### Linux Configuration

So far, we've used the `sunxi_defconfig` in the Linux tree. Let's enable
the so-called Memory Technology Device (MTD) drivers and support for raw NAND and
the Allwinner NAND controller as well as UBI/UBIFS. Type:

```
export UBOOT_VER=2024.10
export LINUX_VER=6.6.63
export BR=buildroot-2024.02.08
cd "${BR}"
make linux-nconfig
```

Then select:
```
Device Drivers  --->
  <*> Memory Technology Device (MTD) support  --->
    Partition parsers  ---> 
       <*> Command line partition table parsing
       <*> OpenFirmware (device tree) partitioning parser
    NAND  --->
      <*> Raw/Parallel NAND Device Support  --->
        <*>   Allwinner NAND controller
    <*>   Enable UBI - Unsorted block images  --->
File systems  ---> 
  [*] Miscellaneous filesystems  --->
    <*>   UBIFS file system support
```
Then save hit the <F9> key to exit and save your Linux configuration.
The configuration will be written to `output/build/linux-${LINUX_VER}/.config`.

Alternatively, make sure these lines are in your Linux `.config` file:
```
CONFIG_MTD=y
CONFIG_MTD_CMDLINE_PARTS=y
CONFIG_MTD_RAW_NAND=y
CONFIG_MTD_NAND_SUNXI=y
CONFIG_MTD_UBI=y
CONFIG_MISC_FILESYSTEMS=y
CONFIG_UBIFS_FS=y
```

Save the configuration as Linux default configuration:
```
make linux-savedefconfig
cp output/build/linux-${LINUX_VER}/defconfig ../buildroot-external/board/nextthingco/CHIP/linux/chip_defconfig
```

The device tree for CHIP included in the Linux source do not enable the NAND.
We need to create a patch that we place in `buildroot-external/board/nextthingco/CHIP/sun5i-r8-chip.dts.nand.patch`:
```
cat <<EOF >../buildroot-external/board/nextthingco/CHIP/linux/sun5i-r8-chip.dts.nand.patch
--- a/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts     2024-11-27 11:25:04.172206469 +0100
+++ b/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts     2024-12-02 10:34:49.783858862 +0100
@@ -280,3 +280,44 @@
        usb0_vbus-supply = <&reg_usb0_vbus>;
        usb1_vbus-supply = <&reg_vcc5v0>;
 };
+
+&nfc {
+       pinctrl-names = "default";
+       pinctrl-0 = <&nand_pins &nand_cs0_pin &nand_rb0_pin>;
+       status = "okay";
+
+       nand@0 {
+               #address-cells = <2>;
+               #size-cells = <2>;
+               reg = <0>;
+               allwinner,rb = <0>;
+               nand-ecc-mode = "hw";
+               nand-ecc-maximize;
+               nand-on-flash-bbt;
+               spl@0 {
+                   label = "SPL";
+                   reg = /bits/ 64 <0x0 0x400000>;
+               };
+
+               spl-backup@400000 {
+                   label = "SPL.backup";
+                   reg = /bits/ 64 <0x400000 0x400000>;
+               };
+
+               u-boot@800000 {
+                   label = "U-Boot";
+                   reg = /bits/ 64 <0x800000 0x400000>;
+               };
+
+               env@c00000 {
+                   label = "env";
+                   reg = /bits/ 64 <0xc00000 0x400000>;
+               };
+
+               rootfs@1000000 {
+                   label = "rootfs";
+                   reg = /bits/ 64 <0x1000000 0x1ff000000>;
+                   slc-mode;
+               };
+       };
+};
EOF
```
NOTE: We're hardcoding 5 partiions here: `spl` (4MB), `spl-backup` (4MB), `u-boot` (4MB), `env` (4MB) and `rootfs` (remaining space, slc-mode).

Buildroot is going to automatically apply the patch the next time we build.

Let's add some file system utilities to the Buildroot configuration - type:
```
make nconfig
```

Then select `mtd, jffs2 and ubi/ubifs tools` and make sure the `mkfs.ubifs` is also selected:
```
Target packages  --->
     Filesystem and flash utilities  --->
          [*] mtd, jffs2 and ubi/ubifs tools
                *** MTD tools selection ***
          [ ]   docfdisk
          [ ]   doc_loadbios
          [*]   flashcp
          [*]   flash_erase
          [*]   flash_lock
          [ ]   flash_otp_dump
          [ ]   flash_otp_info
          [ ]   flash_otp_lock
          [ ]   flash_otp_write
          [ ]   flash_otp_erase
          [*]   flash_unlock
          [ ]   ftl_check
          [ ]   ftl_format
          [ ]   jffs2dump
          [ ]   lsmtd
          [ ]   mkfs.jffs2
          [*]   mkfs.ubifs
```

Then save hit the <F9> key to exit and save the Buildroot configuration.
The configuration will be written to `.config`.

Save the configuration as Buildroot default configuration for CHIP and
build the new Linux kernel and the new rootfs:
```shell
make savedefconfig
make
```

Boot into our new OS image:
```shell,ignore
cd output/images
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin \
                write 0x42000000 zImage \
                write 0x43000000 sun5i-r8-chip.dtb \
                write 0x50000000 rootfs.cpio.uboot
```

In U-Boot, boot:
```
bootz 0x42000000 0x50000000 0x43000000
```

Format the root partition:
```shell
mtdinfo
mtdinfo /dev/mtd0
flash_erase /dev/mtd5 0 2035
ubiformat /dev/mtd5
ubiattach -m 5                           # --> generates /dev/ubi0, also displays number of LEBs = e.g. 1952
ubimkvol /dev/ubi0 --name rootfs -S 1952 # --> creates /dev/ubi0_0
mkfs.ubifs /dev/ubi0_0                   # --> doesn't really create ubifs
mount -t ubifs /dev/ubi0_0 /mnt          # --> ubifs is created as part of mounting
cp -va /bin /usr /mnt/                   # --> copy stuff from ramdisk to nand
reboot
```
NOTE: leaving out the `mkfs.ubifs /dev/ubi0_0` step above seems to work fine as long as only Linux is involved.
However, we won't be able to mount the ubifs partition from U-Boot without!

In the U-Boot terminal type:
```
bootz 0x42000000 0x500000 0x43000000
```

In Linux, we now can read from NAND after reboot:
```
ubiattach -m 5                           # --> generates /dev/ubi0
mount -t ubifs /dev/ubi0_0 /mnt          # --> ubifs is created as part of mounting
find /mnt
```

## U-Boot v2022.01

The patches from Chris Morgan are for U-Boot v2022.01.
For simplicity, we are going to switch to that version as it allows us to
use the unmodified patches.
So let's create a new Buildroot configuration, in which we tell Buildroot to use
U-Boot v2022.01, a custom U-Boot config file and define the directory for custom
U-Boot patches:

```shell
export LINUX_VER=6.6.63
export UBOOT_VER=2022.01
cat <<EOF >../buildroot-external/configs/nextthingco_chip_defconfig
BR2_arm=y
BR2_cortex_a8=y
BR2_TOOLCHAIN_EXTERNAL=y
BR2_LINUX_KERNEL=y
BR2_LINUX_KERNEL_CUSTOM_VERSION=y
BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="${LINUX_VER}"
BR2_LINUX_KERNEL_PATCH="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/linux"
BR2_LINUX_KERNEL_USE_CUSTOM_CONFIG=y
BR2_LINUX_KERNEL_CUSTOM_CONFIG_FILE="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/linux/chip_defconfig"
BR2_LINUX_KERNEL_DTS_SUPPORT=y
BR2_LINUX_KERNEL_INTREE_DTS_NAME="allwinner/sun5i-r8-chip"
BR2_LINUX_KERNEL_DTB_OVERLAY_SUPPORT=y
BR2_LINUX_KERNEL_INSTALL_TARGET=y
BR2_PACKAGE_MTD=y
BR2_PACKAGE_MTD_MKFSUBIFS=y
BR2_TARGET_ROOTFS_CPIO=y
BR2_TARGET_ROOTFS_CPIO_GZIP=y
BR2_TARGET_ROOTFS_CPIO_UIMAGE=y
BR2_TARGET_UBOOT=y
BR2_TARGET_UBOOT_BUILD_SYSTEM_KCONFIG=y
BR2_TARGET_UBOOT_CUSTOM_VERSION=y
BR2_TARGET_UBOOT_CUSTOM_VERSION_VALUE="${UBOOT_VER}"
BR2_TARGET_UBOOT_PATCH="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot"
BR2_TARGET_UBOOT_USE_CUSTOM_CONFIG=y
BR2_TARGET_UBOOT_CUSTOM_CONFIG_FILE="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot/CHIP_defconfig"
BR2_TARGET_UBOOT_NEEDS_DTC=y
BR2_TARGET_UBOOT_NEEDS_PYLIBFDT=y
BR2_TARGET_UBOOT_SPL=y
BR2_TARGET_UBOOT_SPL_NAME="u-boot-sunxi-with-spl.bin spl/u-boot-spl.bin"
EOF
make nextthingco_chip_defconfig
```

Download patches to enable SLC mode for the NAND:
```
wget -c -P ../buildroot-external/board/nextthingco/CHIP/uboot https://raw.githubusercontent.com/macromorgan/chip-debroot/main/u-boot_files/0001-sunxi-Add-support-for-slc-emulation-on-mlc-NAND.patch
wget -c -P ../buildroot-external/board/nextthingco/CHIP/uboot https://raw.githubusercontent.com/macromorgan/chip-debroot/main/u-boot_files/0001-sunxi-nand-Undo-removal-of-DMA-specific-code-that-br.patch
```

Create a CHIP_defconfig for U-Boot:
```
cat <<EOF >../buildroot-external/board/nextthingco/CHIP/uboot/CHIP_defconfig
CONFIG_ARM=y
CONFIG_ARCH_SUNXI=y
CONFIG_DEFAULT_DEVICE_TREE="sun5i-r8-chip"
CONFIG_SPL=y
CONFIG_MACH_SUN5I=y
CONFIG_DRAM_TIMINGS_DDR3_800E_1066G_1333J=y
CONFIG_USB0_VBUS_PIN="PB10"
CONFIG_VIDEO_COMPOSITE=y
CONFIG_CHIP_DIP_SCAN=y
CONFIG_SPL_I2C=y
CONFIG_CMD_DFU=y
CONFIG_CMD_MTDPARTS=y
CONFIG_MTDIDS_DEFAULT="nand0=nand0"
CONFIG_MTDPARTS_DEFAULT="nand0:0x400000(SPL),0x400000(SPL.backup),0x400000(U-Boot),0x400000(U-Boot.backup),-(rootfs)slc"
CONFIG_DFU_RAM=y
CONFIG_SYS_I2C_MVTWSI=y
CONFIG_SYS_I2C_SLAVE=0x7f
CONFIG_SYS_I2C_SPEED=400000
# CONFIG_MMC is not set
CONFIG_MTD=y
CONFIG_DM_MTD=y
CONFIG_MTD_RAW_NAND=y
CONFIG_SYS_NAND_USE_FLASH_BBT=y
CONFIG_NAND_SUNXI_SPL_ECC_SIZE=512
CONFIG_SYS_NAND_BLOCK_SIZE=0x400000
CONFIG_SYS_NAND_PAGE_SIZE=0x4000
CONFIG_SYS_NAND_OOBSIZE=0x680
CONFIG_SYS_NAND_U_BOOT_OFFS_REDUND=0xc00000
CONFIG_UBI_SILENCE_MSG=y
CONFIG_AXP_ALDO3_VOLT=3300
CONFIG_AXP_ALDO4_VOLT=3300
CONFIG_CONS_INDEX=2
CONFIG_USB_EHCI_HCD=y
CONFIG_USB_OHCI_HCD=y
CONFIG_USB_MUSB_GADGET=y
EOF
```

Build new configured U-Boot:
```
make uboot-reconfigure
```

TODO: In U-Boot:
```
=> ubi part rootfs
=> ubi info
UBI: MTD device name:            "rootfs"
UBI: MTD device size:            4088 MiB
UBI: physical eraseblock size:   2097152 bytes (2048 KiB)
UBI: logical eraseblock size:    2064384 bytes
UBI: number of good PEBs:        2036
UBI: number of bad PEBs:         8
UBI: smallest flash I/O unit:    16384
UBI: VID header offset:          16384 (aligned 16384)
UBI: data offset:                32768
UBI: max. allowed volumes:       128
UBI: wear-leveling threshold:    4096
UBI: number of internal volumes: 1
UBI: number of user volumes:     1
UBI: available PEBs:             122
UBI: total number of reserved PEBs: 1914
UBI: number of PEBs reserved for bad PEB handling: 72
UBI: max/mean erase counter: 2/1
=> ubi info l
Volume information dump:
        vol_id          0
        reserved_pebs   1838
        alignment       1
        data_pad        0
        vol_type        3
        name_len        6
        usable_leb_size 2064384
        used_ebs        1838
        used_bytes      3794337792
        last_eb_bytes   2064384
        corrupted       0
        upd_marker      0
        skip_check      0
        name            rootfs
Volume information dump:
        vol_id          2147479551
        reserved_pebs   2
        alignment       1
        data_pad        0
        vol_type        3
        name_len        13
        usable_leb_size 2064384
        used_ebs        2
        used_bytes      4128768
        last_eb_bytes   2
        corrupted       0
        upd_marker      0
        skip_check      0
        name            layout volume
=> ubifsmount ubi0:rootfs
=> ubifsls /
<DIR>        5024  Thu Jan 01 00:04:02 1970  bin
<DIR>         608  Thu Jan 01 00:04:05 1970  dev
<DIR>        1712  Thu Jan 01 00:04:05 1970  etc
<DIR>        3080  Thu Jan 01 00:04:04 1970  lib
<DIR>         160  Mon Nov 28 09:21:16 2022  mnt
<DIR>         160  Mon Nov 28 09:21:16 2022  opt
<DIR>         160  Sat Dec 03 16:39:02 2022  run
<DIR>         160  Mon Nov 28 09:21:16 2022  tmp
<DIR>         160  Mon Nov 28 09:21:16 2022  sys
<DIR>         672  Thu Jan 01 00:04:05 1970  var
<DIR>         544  Thu Jan 01 00:04:05 1970  usr
<DIR>         304  Thu Jan 01 00:04:02 1970  boot
<DIR>         160  Mon Nov 28 09:21:16 2022  proc
<DIR>        3736  Thu Jan 01 00:04:05 1970  sbin
<DIR>         160  Mon Nov 28 09:21:16 2022  root
<LNK>          11  Thu Jan 01 00:04:04 1970  linuxrc
<LNK>           3  Thu Jan 01 00:04:04 1970  lib32
<DIR>         160  Mon Nov 28 09:21:16 2022  media
=> ubifsls /boot
            25748  Thu Dec 01 08:52:19 2022  sun5i-r8-chip.dtb
          5357864  Thu Dec 01 08:52:19 2022  zImage
=> ubifsload 0x42000000 /boot/zImage
Loading file '/boot/zImage' to addr 0x42000000...
Done
=> ubifsload 0x43000000 /boot/sun5i-r8-chip.dtb
Loading file '/boot/sun5i-r8-chip.dtb' to addr 0x43000000...
Done

setenv bootargs root=ubi0_0 rootfstype=ubifs ubi.mtd=4 rw earlyprintk waitroot
bootz 0x42000000 - 0x43000000
```

NOTE: for some reason `setenv bootargs root=/dev/ubi0:rootfs rootfstype=ubifs ubi.mtd=4 rw earlyprintk waitroot`
does not work. That's why we specify `root=ubi0_0`.

