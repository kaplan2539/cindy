# Buildroot

In the Warm-Up exercise chapter we've manually installed a cross-compiler,
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
# set U-Boot version
export UBOOT_VER=2024.10
export LINUX_VER=6.6.63

# set Buildroot version
export BR=buildroot-2024.02.8

mkdir -p download

echo "# Downloading Buildroot"
wget -c -P download https://buildroot.org/downloads/${BR}.tar.gz
tar xf download/${BR}.tar.gz
```

## Customizing Buildroot for CHIP

We are going to use the 'br2-external' mechanism (c.f. Buildroot documentation
 [Chapter 9.2](https://buildroot.org/downloads/manual/manual.html#outside-br-custom)
 ) in order to keep our
customizations outside of the official Buildroot tree:

```shell
mkdir -p buildroot-external
export BR2_EXTERNAL="$(realpath buildroot-external)"
```

Create `external.desc`:

```shell
cat <<EOF >"${BR2_EXTERNAL}"/external.desc
name: CHIP
desc: Buildroot configuration for CHIP
EOF
```

Create `external.mk`:

```shell
cat <<EOF >"${BR2_EXTERNAL}"/external.mk
include \$(sort \$(wildcard \$(BR2_EXTERNAL_CHIP_PATH)/package/*/*.mk))
EOF
```

Create empty `Config.in`:

```shell
touch "${BR2_EXTERNAL}"/Config.in
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
BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="${LINUX_VER}"
BR2_LINUX_KERNEL_PATCH="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/linux"
BR2_LINUX_KERNEL_DEFCONFIG="sunxi"
BR2_LINUX_KERNEL_DTS_SUPPORT=y
BR2_LINUX_KERNEL_INTREE_DTS_NAME="allwinner/sun5i-r8-chip"
BR2_LINUX_KERNEL_DTB_OVERLAY_SUPPORT=y
BR2_LINUX_KERNEL_INSTALL_TARGET=y
BR2_TARGET_ROOTFS_CPIO=y
BR2_TARGET_ROOTFS_CPIO_GZIP=y
BR2_TARGET_ROOTFS_CPIO_UIMAGE=y
BR2_TARGET_UBOOT=y
BR2_TARGET_UBOOT_BUILD_SYSTEM_KCONFIG=y
BR2_TARGET_UBOOT_CUSTOM_VERSION=y
BR2_TARGET_UBOOT_CUSTOM_VERSION_VALUE="${UBOOT_VER}"
BR2_TARGET_UBOOT_PATCH="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/uboot"
BR2_TARGET_UBOOT_BOARD_DEFCONFIG="CHIP"
BR2_TARGET_UBOOT_NEEDS_DTC=y
BR2_TARGET_UBOOT_NEEDS_PYLIBFDT=y
BR2_TARGET_UBOOT_SPL=y
BR2_TARGET_UBOOT_SPL_NAME="u-boot-sunxi-with-spl.bin spl/u-boot-spl.bin"
EOF
```

Now compile Linux, U-Boot and build a rootfs image using Buildroot:

```shell
cd "${BR}"
make nextthingco_chip_defconfig
make
```

Buildroot put everything into the `output/images` sub-directory.
The following commands are booting into U-Boot SPL and then upload the Linux
kernel, the device tree and the Buildroot root file system into CHIP's DRAM:
```shell
cd output/images
sunxi-fel -v -p uboot u-boot-sunxi-with-spl.bin \
                write 0x42000000 zImage \
                write 0x43000000 sun5i-r8-chip.dtb \
                write 0x50000000 rootfs.cpio.uboot
```

NOTE: We are uploading the root file system to address `0x50000000` now.
If the rootfs gets bigger we might get into trouble uploading it into the
memory region between `0x4300000000` and `0x4fffffff`.
Read the [Sunxi website](https://linux-sunxi.org/Initial_Ramdisk) and
[this post](https://groups.google.com/g/linux-sunxi/c/Itt3Bko0bVA/m/Mqt5zTj1qaIJ)
for more details.

To boot, type the following in the `cu` terminal window:
```
bootz 0x42000000 0x50000000 0x43000000
```
