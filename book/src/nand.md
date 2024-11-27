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
the socalled Memory Technolgy Device (MTD) drivers and support for raw NAND and
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
--- a/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts     2024-11-22 15:38:37.000000000 +0100
+++ b/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts     2024-11-27 11:24:37.140950697 +0100
@@ -280,3 +280,19 @@
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
+       };
+};
EOF
```
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

In U-Boot specify `bootargs` for the nand partitions:
```
setenv bootargs mtdparts=1c03000.nand-controller:0x400000(SPL)ro,0x400000(SPL.backup)ro,0x400000(U-Boot)ro,0x400000(U-Boot.backup)ro,0x2000000(swupdate)slc,-(rootfs)slc
bootz 0x42000000 0x500000 0x43000000
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

Don't forget to specify the mtd partitions before booting CHIP again:
```
setenv bootargs mtdparts=1c03000.nand-controller:0x400000(SPL)ro,0x400000(SPL.backup)ro,0x400000(U-Boot)ro,0x400000(U-Boot.backup)ro,0x2000000(swupdate)slc,-(rootfs)slc
bootz 0x42000000 0x500000 0x43000000
```

Now verify we can read from nand after reboot:
```
ubiattach -m 5                           # --> generates /dev/ubi0
mount -t ubifs /dev/ubi0_0 /mnt          # --> ubifs is created as part of mounting
find /mnt
```
