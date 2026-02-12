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
mode. 

## Access the NAND from Linux

### Linux Configuration

So far, we have used the `sunxi_defconfig` in the Linux tree.
Now, we are creating a Linux kernel config frament to enable the Memory Technology Device (MTD) drivers, support for raw NAND and the Allwinner NAND controller as well as UBI/UBIFS. Type:

```
cat <<EOF >"${BR2_EXTERNAL}"/board/nextthingco/CHIP/linux/nand.cfg
CONFIG_MTD=y
CONFIG_MTD_CMDLINE_PARTS=y
CONFIG_MTD_RAW_NAND=y
CONFIG_MTD_NAND_SUNXI=y
CONFIG_MTD_UBI=y
CONFIG_MISC_FILESYSTEMS=y
CONFIG_UBIFS_FS=y
EOF
```

The device tree for CHIP included in the Linux source does not enable the NAND.
We need to create a patch that we place in `buildroot-external/board/nextthingco/CHIP/sun5i-r8-chip.dts.nand.patch`:
```
cat <<EOF |sed -e 's/^         / \t/; s/        /\t/g; s/+ $/+/g' >${BR2_EXTERNAL}/board/nextthingco/CHIP/linux/sun5i-r8-chip.dts.nand.patch
--- a/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts        2026-02-11 22:47:01.214772251 +0100
+++ b/arch/arm/boot/dts/allwinner/sun5i-r8-chip.dts        2026-02-11 22:48:26.003942388 +0100
@@ -280,3 +280,44 @@
         usb0_vbus-supply = <&reg_usb0_vbus>;
         usb1_vbus-supply = <&reg_vcc5v0>;
 };
+
+&nfc {
+        pinctrl-names = "default";
+        pinctrl-0 = <&nand_pins &nand_cs0_pin &nand_rb0_pin>;
+        status = "okay";
+
+        nand@0 {
+                #address-cells = <2>;
+                #size-cells = <2>;
+                reg = <0>;
+                allwinner,rb = <0>;
+                nand-ecc-mode = "hw";
+                nand-ecc-maximize;
+                nand-on-flash-bbt;
+                spl@0 {
+                        label = "SPL";
+                        reg = /bits/ 64 <0x0 0x400000>;
+                };
+
+                spl-backup@400000 {
+                        label = "SPL.backup";
+                        reg = /bits/ 64 <0x400000 0x400000>;
+                };
+
+                u-boot@800000 {
+                        label = "U-Boot";
+                        reg = /bits/ 64 <0x800000 0x400000>;
+                };
+
+                env@c00000 {
+                        label = "env";
+                        reg = /bits/ 64 <0xc00000 0x400000>;
+                };
+
+                rootfs@1000000 {
+                        label = "rootfs";
+                        reg = /bits/ 64 <0x1000000 0x1ff000000>;
+                        slc-mode;
+                };
+        };
+};
EOF
```
NOTE: We are hardcoding 5 partitions here: `spl` (4MB), `spl-backup` (4MB), `u-boot` (4MB), `env` (4MB) and `rootfs` (remaining space, slc-mode).
Buildroot is going to automatically apply the patch the next time we build.

Let us add some file system utilities to our target rootfs and also let Buildroot know that it should merge-in our Linux configuration fragment:
```
cat <<EOF >>"${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
BR2_PACKAGE_MTD=y
BR2_PACKAGE_MTD_MKFSUBIFS=y
BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES="\${BR2_EXTERNAL}/board/nextthingco/CHIP/linux/nand.cfg"
EOF
```

It is time to build our new Buildroot configuration:
```
cd "${BR_DIR}"
make nextthingco_chip_defconfig;
make linux-rebuild
make
```

Boot into our new OS image:
```shell,ignore
cd ${BR_DIR}/output/images
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin \
                write 0x42000000 zImage \
                write 0x43000000 sun5i-r8-chip.dtb \
                write 0x50000000 rootfs.cpio.uboot
```

In U-Boot, boot:
```
bootz 0x42000000 0x50000000 0x43000000
```

After logging in to Linux, format the root partition on the NAND and copy the rootfs from the ram disk:
```shell
mtdinfo
mtdinfo /dev/mtd0
flash_erase /dev/mtd4 0 2035
ubiformat -y /dev/mtd4
ubiattach -m 4                           # --> generates /dev/ubi0, also displays number of LEBs = e.g. 1952
ubimkvol /dev/ubi0 --name rootfs -S 1952 # --> creates /dev/ubi0_0
mkfs.ubifs /dev/ubi0_0                   # --> doesn't really create ubifs
mount -t ubifs /dev/ubi0_0 /mnt          # --> ubifs is created as part of mounting
cp -va /bin /boot /crond.reboot /dev /etc /init /lib /lib32 /linuxrc /media /opt /root /sbin /usr /var /mnt # --> copy stuff from ramdisk to nand
cd /mnt
mkdir mnt run proc sys tmp
cd /
umount /mnt
reboot
```
NOTE: leaving out the `mkfs.ubifs /dev/ubi0_0` step above seems to work fine as long as only Linux is involved.
However, we won't be able to mount the ubifs partition from U-Boot without!

In the U-Boot terminal type:
```
bootz 0x42000000 0x50000000 0x43000000
```

In Linux, we now can read from NAND after reboot:
```
ubiattach -m 4                           # --> generates /dev/ubi0
mount -t ubifs /dev/ubi0_0 /mnt          # --> ubifs is created as part of mounting
find /mnt
```

## Access the NAND from U-Boot

The patches from Chris Morgan are for U-Boot v2022.01.
For simplicity, we are going to switch to that version as it allows us to
use the unmodified patches.
So let's update the Buildroot configuration to use U-Boot v2022.01 and a custom U-Boot config files:

```shell
export UBOOT_VER=2022.01

sed -i -e '
s/\(BR2_TARGET_UBOOT_CUSTOM_VERSION_VALUE=\).*/\1\"'$UBOOT_VER'\"/;
/^$/d;
/^BR2_TARGET_UBOOT_BOARD_DEFCONFIG=.*/d;
/^BR2_TARGET_UBOOT_USE_CUSTOM_CONFIG=.*/d;
/^BR2_TARGET_UBOOT_CUSTOM_CONFIG_FILE=.*/d;
' ${BR2_EXTERNAL}/configs/nextthingco_chip_defconfig

cat <<EOF >>${BR2_EXTERNAL}/configs/nextthingco_chip_defconfig
BR2_TARGET_UBOOT_USE_CUSTOM_CONFIG=y
BR2_TARGET_UBOOT_CUSTOM_CONFIG_FILE="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot/CHIP_defconfig"
EOF
 
cd ${BR_DIR}
make nextthingco_chip_defconfig
```

Download patches to enable SLC mode for the NAND:
```
wget -c -P ${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot https://raw.githubusercontent.com/macromorgan/chip-debroot/main/u-boot_files/0001-sunxi-Add-support-for-slc-emulation-on-mlc-NAND.patch
wget -c -P ${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot https://raw.githubusercontent.com/macromorgan/chip-debroot/main/u-boot_files/0001-sunxi-nand-Undo-removal-of-DMA-specific-code-that-br.patch
```

Create a `CHIP_defconfig` for U-Boot:
```
cat <<EOF >${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/CHIP_defconfig
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

Next, boot - note: we are not uploading Linux anymore:
```shell,ignore
cd ${BR_DIR}/output/images
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin 
```

In our cu-terminal, hit the Any-Key and type the following U-Boot commands:
```
ubi part rootfs
ubifsmount ubi0:rootfs
ubifsload 0x42000000 /boot/zImage
ubifsload 0x43000000 /boot/sun5i-r8-chip.dtb
setenv bootargs root=ubi0_0 rootfstype=ubifs ubi.mtd=4 rw earlyprintk waitroot
bootz 0x42000000 - 0x43000000
```

NOTE: for some reason `setenv bootargs root=/dev/ubi0:rootfs rootfstype=ubifs ubi.mtd=4 rw earlyprintk waitroot`
does not work. That's why we specify `root=ubi0_0`.

Woohoo! We've just booted the Linux kernel and device tree U-Boot loaded from NAND. And Linux mounted its rootfs from NAND!
In the next chapter, we are going to show how to also write U-Boot onto the NAND such that CHIP can boot without using a USB connection and the sunxi-fel tool.
