# Look mom no UART!

Having C.H.I.P hooked up via UART and being able to interactively type commands
in U-BOOT and is great for debugging.
It becomes kind of a burden though when you need to do it to boot up your C.H.I.P.
In this chapter we are adding scripts to flash your U-Boot and the Buildroot image
automatically and setup everything such that C.H.I.P can boot straight into Linux
without manual intervention via UART.

## Configure U-Boot to automatically boot from NAND

We are adding a `nand_boot.cfg` U-Boot configuration fragment in order to change
the `BOOT_COMMAND` such that it mounts the UBI rootfs partition on the NAND and
loads the Linux kernel and the device tree binary from
there. We also define the `bootargs` and finally boot into the Linux kernel:
```
cat <<EOF >${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/nand_boot.cfg
CONFIG_AUTOBOOT=y
CONFIG_USE_BOOTCOMMAND=y
CONFIG_BOOTCOMMAND="\
if test -n \${fel_booted} && test -n \${fel_scriptaddr}; then \
    source \${fel_scriptaddr}; \
fi; \
ubi part rootfs; ubifsmount ubi0:rootfs; ubifsload 0x42000000 /boot/zImage; ubifsload 0x43000000 /boot/sun5i-r8-chip.dtb; setenv bootargs root=ubi0_0 rootfstype=ubifs ubi.mtd=4 rw earlyprintk waitroot; bootz 0x42000000 - 0x43000000"
EOF
```

Now also activate the new configuration fragment:
```
sed -i -e '
s%\(BR2_TARGET_UBOOT_CONFIG_FRAGMENT_FILES=\).*%\1\"\${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/nand.cfg \${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/nand_boot.cfg\"%g
' ${BR2_EXTERNAL}/configs/nextthingco_chip_defconfig

make nextthingco_chip_defconfig
```

Then re-compile u-boot and run the post-image scripts:
```
make uboot-reconfigure
make
```

## Bash script to write U-Boot onto the NAND


# WIP ---v

## TODAYS LEARNINGS:
- it does not work to create a ubi image with buildroot and flash that with the u-boot nand write command
- what works:
  - only create rootfs.ubifs with buildroot
```
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin write 0x43400000 sunxi-spl.bin.nand write 0x43800000 u-boot.bin.nand write 0x50000000 rootfs.ubifs

# in cu terminal / u-boot shell:
nand erase.part rootfs
ubi part rootfs
ubi createvol rootfs
ubi writevol 0x50000000 rootfs $ROOTFS_SIZE
```

NOTE: it would be more logical to name our UBI partition "ubi", and keep "rootfs" as the name for the ubi-volume:
```
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin write 0x43400000 sunxi-spl.bin.nand write 0x43800000 u-boot.bin.nand write 0x50000000 rootfs.ubifs

# in cu terminal / u-boot shell:
nand erase.part ubi
ubi part ubi
ubi createvol rootfs
ubi writevol 0x50000000 rootfs $ROOTFS_SIZE
```



	
## Add the U-Boot boot script

U-Boot checks for a boot script at address `0x43100000`. If it finds one, it
processes the commands defined in there and we don't need to type them via UART.

Let's put the commands into the file `${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot/boot.cmd`:
```
cat <<EOF >>${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot/boot.cmd
EOF
```

Enable the generation of a U-Boot boot script in the Buildroot configuration:
```
cat <<EOF >>"${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
BR2_PACKAGE_HOST_UBOOT_TOOLS_BOOT_SCRIPT=y
BR2_PACKAGE_HOST_UBOOT_TOOLS_BOOT_SCRIPT_SOURCE="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot/boot.cmd"
EOF
```

Update config and re-build host-uboot-tools to generate `output/images/boot.scr`:
```
make nextthingco_chip_defconfig
make host-uboot-tools-rebuild
```

Create fel-boot:
```
cat <<EOF >${WORKD_DIR}/bin/fel-boot
#!/bin/bash

D=${BR_DIR}/output/images

sunxi-fel -v -p uboot ${D}/u-boot-sunxi-with-spl.bin \
                write 0x42000000 ${D}/zImage \
                write 0x43000000 ${D}/sun5i-r8-chip.dtb \
                write 0x43100000 ${D}/boot.scr \
                write 0x43400000 ${D}/sunxi-spl.bin.nand \
                write 0x43800000 ${D}/u-boot.bin.nand \
                write 0x50000000 ${D}/rootfs.cpio.uboot
EOF
```
Now, U-Boot auto-boot automatically detects the script uploaded to 0x43100000 and executes it!

Define U-Boot BOOT_COMMAND:
```
UBOOT_CFG="${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/CHIP_defconfig"
sed -i -e 's/\(CONFIG_SYS_NAND_OOBSIZE\)=.*/\1=0x500/' ${UBOOT_CFG}"\

cd ${BR_DIR}
make uboot-reconfigure


```

TODO:
 1.) add install.sh to rootfs.tar.gz: 
```
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
poweroff
```

 2.) modify boot.scr / better create flash.sh:
```
nand erase.chip
nand write.raw.noverify 0x43400000 0x0 0x100
nand write.raw.noverify 0x43400000 0x400000 0x100
nand write 0x43800000 0x800000 0x400000
setenv bootargs init=/install.sh
bootz 0x42000000 0x50000000 0x43000000
```
FINDOUT: does init=install.sh disable password / login?

### direnv
Create .envrc:
```
cat <<EOF >.envrc 
# set U-Boot version
export UBOOT_VER=2022.01

# Retrieve latest Linux version
export LINUX_VER=6.12.70

# set Buildroot version
export BR_VER=2025.02.10

# define working dir - use absolute paths!
export WORK_DIR="\${PWD}"
export DOWNLOAD_DIR="\${WORK_DIR}/download"
export BR_DIR="\${WORK_DIR}/buildroot-${BR_VER}"
export BR2_EXTERNA="\${WORK_DIR}/buildroot-external"

export PATH=\$PATH:${PWD}/bin
EOF
```


