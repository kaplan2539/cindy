# Look mom no UART!

Having C.H.I.P hooked up via UART and being able to interactively type commands
in U-BOOT and is great for debugging.
It becomes kind of a burden though when you need to do it to boot up your C.H.I.P.
In this chapter we are adding scripts to flash your U-Boot and the Buildroot image
automatically and setup everything such that C.H.I.P can boot straight into Linux
without manual intervention via UART.

## Enable UBIFS generation in Buildroot

First, we enable the generation of an UBIFS rootfs image in our Buildroot config:

```
UBOOT_NAND_CFG="buildroot-external/board/nextthingco/CHIP/uboot/nand.cfg"
NAND_BLOCK_SIZE=$(sed -n -e 's/CONFIG_SYS_NAND_BLOCK_SIZE=\(.*\)/\1/p' "${UBOOT_NAND_CFG}")
NAND_PAGE_SIZE=$(sed -n -e 's/CONFIG_SYS_NAND_PAGE_SIZE=\(.*\)/\1/p' "${UBOOT_NAND_CFG}")

MINIOSIZE="${NAND_PAGE_SIZE}"
LEB_SIZE="$(printf "0x%x" $((NAND_BLOCK_SIZE/2 - 2*NAND_PAGE_SIZE)))" 

cat <<EOF >>"${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
BR2_TARGET_ROOTFS_UBIFS=y
BR2_TARGET_ROOTFS_UBIFS_LEBSIZE=${LEB_SIZE}
BR2_TARGET_ROOTFS_UBIFS_MINIOSIZE=${MINIOSIZE}
BR2_TARGET_ROOTFS_UBIFS_MAXLEBCNT=4096
BR2_TARGET_ROOTFS_UBIFS_RT_LZO=y
BR2_TARGET_ROOTFS_UBIFS_NONE=y
BR2_TARGET_ROOTFS_UBIFS_OPTS=""
EOF

cd ${BR_DIR}
make nextthingco_chip_defconfig
```

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

We are going to use the U-Boot we have built above not only to boot Linux, but
also to write the NAND images. For that to work we need to overwrite the auto
boot command we defined above by downloading a U-boot environment file to address
`0x43100000` with the `sunxi-fel` tool. The first line in the `uenv.txt` file
needs to be `#=uEnv`:

```
cat <<END >${BR_DIR}/output/images/flash.sh
#!/bin/bash

if [ -z "\${BR_DIR}" ]; then
    D="\${PWD}"
else
    D="\${BR_DIR}/output/images"
fi

UENV_TXT="\${D}/uenv.txt"
SUNXI_SPL_BIN_NAND="\${D}/sunxi-spl.bin.nand"
U_BOOT_BIN_NAND="\${D}/u-boot.bin.nand"
ROOTFS_UBIFS="\${D}/rootfs.ubifs"

ROOTFS_UBIFS_SIZE=\$(stat -c%s "\${ROOTFS_UBIFS}")
ROOTFS_UBIFS_SIZE=\$(printf "0x%x" \${ROOTFS_UBIFS_SIZE}) 

cat <<EOF >"\${UENV_TXT}"
#=uEnv
bootdelay=0
bootcmd=\
nand erase.chip; \
nand write.raw.noverify 0x43000000 SPL 0x100; \
nand write.raw.noverify 0x43000000 SPL.backup 0x100; \
nand write 0x44000000 U-Boot 0x400000; \
nand write 0x44000000 U-Boot.backup 0x400000; \
ubi part rootfs; \
ubi createvol rootfs; \
ubi writevol 0x50000000 rootfs \${ROOTFS_UBIFS_SIZE}; \
reset
EOF

echo "# please connect CHIP with FEL-pin pulled low"
while ! sunxi-fel ver >/dev/null 2>&1; do sleep 0.5; done

sunxi-fel -v -p \
    uboot u-boot-sunxi-with-spl.bin \
    write 0x42000000 "\${UENV_TXT}" \
    write 0x43000000 "\${D}/sunxi-spl.bin.nand" \
    write 0x44000000 "\${D}/u-boot.bin.nand" \
    write 0x50000000 "\${D}/rootfs.ubifs"

echo "# flashing..."
while ! sunxi-fel ver >/dev/null 2>&1; do sleep 0.5; done
echo "# done!"
echo 
echo "# please pull FEL pin high (remove cable connected to GND) and power-cycle CHIP"

END
chmod a+x ${BR_DIR}/output/images/flash.sh
```

