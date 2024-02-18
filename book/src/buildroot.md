# Buildroot

In the Warm Up Excercise chapter we've manually installed a cross-compiler,
downloaded the U-Boot, Linux and Busybox sources, compiled them and created
a rootfs image.
In this chapter we are going to use Buildroot to do that for us.

Buildroot is a great tool to generate embedded Linux images.
It integrates all of the steps mentioned above and makes it really easy to
add various software packages to the root file system.

We can only give very brief overview of how to use Buildroot for our purposes.
Luckily, Buildroot comes with
[detailed documentation](https://buildroot.org/downloads/manual/manual.html)
 that should cover everything important to know.

Download and unpack the latest "stable" release:

```shell
wget -c -P download https://buildroot.org/downloads/buildroot-2023.11.tar.gz
tar xf download/buildroot-2023.11.tar.gz
```

## Customizing Buildroot for CHIP

We are going to use the 'br2-external' mechanism (c.f. Buildroot documentation
 [Chapter 9.2](https://buildroot.org/downloads/manual/manual.html#outside-br-custom)
 ) in order to keep our
costumizations outside of the official buildroot tree:

```
mkdir buildroot-external
export BR2_EXTERNAL="$(realpath buildroot-external)"
```

Create `buildroot-external/external.desc`:

```
cat <<EOF >buildroot-external/external.desc
name: CHIP
desc: Buildroot configuration for CHIP
EOF
```

Create `buildroot-external/external.mk`:

```
cat <<EOF >buildroot-external/external.mk
include \$(sort \$(wildcard \$(BR2_EXTERNAL_CHIP_PATH)/package/*/*.mk))
EOF
```

Create empty `buildroot-external/Config.in`:

```
touch buildroot-external/Config.in
```

Create
[recommended directory structure](https://buildroot.org/downloads/manual/manual.html#customize-dir-structure):

```shell
mkdir -p "${BR2_EXTERNAL}"/board/nextthingco/CHIP/{dts,linux,uboot}
mkdir -p "${BR2_EXTERNAL}"/configs
```

Create Buildroot configuration for CHIP, for now using the default U-Boot
`CHIP_defconfig` and Linux `sunxi_defconfig`:

```shell
cat <<EOF >"${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
BR2_arm=y
BR2_cortex_a8=y
BR2_TOOLCHAIN_EXTERNAL=y
BR2_LINUX_KERNEL=y
BR2_LINUX_KERNEL_CUSTOM_VERSION=y
BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="6.1.68"
BR2_LINUX_KERNEL_PATCH="${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/linux"
BR2_LINUX_KERNEL_DEFCONFIG="sunxi"
BR2_LINUX_KERNEL_DTS_SUPPORT=y
BR2_LINUX_KERNEL_INTREE_DTS_NAME="sun5i-r8-chip"
BR2_LINUX_KERNEL_DTB_OVERLAY_SUPPORT=y
BR2_LINUX_KERNEL_INSTALL_TARGET=y
BR2_TARGET_ROOTFS_CPIO=y
BR2_TARGET_ROOTFS_CPIO_GZIP=y
BR2_TARGET_ROOTFS_CPIO_UIMAGE=y
BR2_TARGET_UBOOT=y
BR2_TARGET_UBOOT_BUILD_SYSTEM_KCONFIG=y
BR2_TARGET_UBOOT_CUSTOM_VERSION=y
BR2_TARGET_UBOOT_CUSTOM_VERSION_VALUE="2023.10"
BR2_TARGET_UBOOT_PATCH="${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot"
BR2_TARGET_UBOOT_BOARD_DEFCONFIG="CHIP"
BR2_TARGET_UBOOT_NEEDS_DTC=y
BR2_TARGET_UBOOT_NEEDS_PYLIBFDT=y
BR2_TARGET_UBOOT_SPL=y
BR2_TARGET_UBOOT_SPL_NAME="u-boot-sunxi-with-spl.bin spl/u-boot-spl.bin"
EOF
```

Now compile Linux, U-Boot and build a rootfs image using Buildroot:

```shell
cd buildroot-2023.11
make nextthingco_chip_defconfig
make
```

Buildroot put everything into the `output/images` sub-directory.
To boot type:

```shell
cd output/images
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin \
                write 0x42000000 zImage \
                write 0x43000000 sun5i-r8-chip.dtb \
                write 0x43400000 rootfs.cpio.uboot
```
