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

Download and unpack the latest "LTS" release:

```shell
# set U-Boot version
export UBOOT_VER=
LATEST_TAG=$( curl -s "https://gitlab.com/api/v4/projects/u-boot%2Fu-boot/repository/tags?order_by=version&sort=desc" \
  | jq -r '[ .[] | select(.name | test("-rc") | not) ][0].name'
)

# Retrieve latest Linux version
export LINUX_VER=$(curl -s https://www.kernel.org/releases.json | jq -r '
    [ .releases[] | select(.moniker=="longterm") | .version ]
    | sort_by(split(".") | map(tonumber)) | last
')

# set Buildroot version
export BR_VER=2025.02.10

# define working dir - use absolute paths!
export WORK_DIR="${HOME}/Projects/CHIP-BUILDROOT-${BR_VER}"
export DOWNLOAD_DIR="${WORK_DIR}/download"
export BR_DIR="${WORK_DIR}/buildroot-${BR_VER}"

mkdir -p ${WORK_DIR}
mkdir -p ${DOWNLOAD_DIR}

echo "# Downloading Buildroot"
wget -c -P "${DOWNLOAD_DIR}" https://buildroot.org/downloads/buildroot-${BR_VER}.tar.gz
tar -C "${WORK_DIR}" -x -f "${DOWNLOAD_DIR}/buildroot-${BR_VER}.tar.gz"
```

## Customizing Buildroot for CHIP

We are going to use the 'br2-external' mechanism (c.f. Buildroot documentation
 [Chapter 9.2](https://buildroot.org/downloads/manual/manual.html#outside-br-custom)
 ) in order to keep our
customizations outside of the official Buildroot tree:

```shell
export BR2_EXTERNAL="${WORK_DIR}/buildroot-external"
mkdir -p "${BR2_EXTERNAL}"
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
BR2_TARGET_UBOOT_SPL_NAME="u-boot-sunxi-with-spl.bin spl/sunxi-spl.bin"
EOF
```

Now compile Linux, U-Boot and build a rootfs image using Buildroot:

```shell
cd "${BR_DIR}"
make nextthingco_chip_defconfig
make
```

Buildroot put everything into the `output/images` sub-directory.
The following commands are booting into U-Boot SPL and then upload the Linux
kernel, the device tree and the Buildroot root file system into CHIP's DRAM:
```shell
cd "${BR_DIR}/output/images"
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
