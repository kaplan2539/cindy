# Booting from NAND

Instead of booting into FEL mode and downloading U-Boot, Linux and the root
file system every time, we want to write everything to the NAND and boot into
Linux automatically after powering on C.H.I.P.

When powered on, the Allwinner R8 SOC on C.H.I.P first executes code in the
built-in Boot-ROM ([BROM](https://linux-sunxi.org/BROM)).
At this time the 512 MB DRAM on C.H.I.P are not initialized and the R8 SOC can
only work with the internal 48 KiB SRAM.
The BROM code checks if the FEL pin is low (i.e. connected to GND) and if so
goes to the FEL USB boot mode. With the R8 in FEL USB mode, we can interact
with the SOC via the `sunxi-fel` tool as described various time in the previous
chapters.
If the FEL pin is high, the BROM code starts checking the various storage
options (e.g. C.H.I.P's NAND) for a valid boot signature at the right location.
If no boot signature is found the BROM code switches to FEL mode.
If such a boot signature is found the code is loaded from the storage into the
SRAM and executed.
The maximum size of this early stage boot code is 0x7e00 bytes (31.5 KiB) on
Allwinner R8/A12 SOCs.

The limited space in the SRAM is why we need the U-Boot secondary program
loader (SPL). We've already used U-Boot SPL in the first chapters without
explaining anything about it.
Without going into detail, the following paragraph tries to gives a very high
level and probably too simplified overview.

We used the `sunxi-fel uboot` command that expects a binary containing U-Boot
including the SPL code. The SPL code is downloaded to the SRAM of the SOC
and executed to initialize the DRAM. C.H.I.P's DRAM configuration is hard-coded
in the SPL. After initializing the DRAM, the SOC goes back to FEL mode.
Now U-Boot, Linux, the device tree and the root file filesystem can be
downloaded to DRAM using the `sunxi-fel` tool.
Next, U-Boot is executed and unpacks and starts the Linux kernel.

In this chapter we want to write the SPL code to the first blocks of the NAND
where it can be picked up and executed by the BROM code. Once the DRAM is
initialized, we want the SPL code to read the full U-Boot code from the NAND
into DRAM and then hand over control to U-Boot. For that to work, not only the
DRAM configuration but also the NAND configuration must be hardcoded into the
SPL code. The DRAM and NAND parameters are specified in the the U-Boot
configuration.

## Different NAND types

NAND memory device technology is used inside of SD card, SSD's and EMMC chips
which behave like block devices. These block devices abstract away many of the
things necessary to operate raw NAND chips as storage devices.
C.H.I.P does not use SD cards or EMMC chips, but comes with raw NAND.
This requires special treatment in software to implement error correction and
wear-leveling.

There are two different variants of C.H.I.P out in the wild -
those with 8 GB SK hynix `H27UCG8T2ETR` NAND modules and those with 4 GB Toshiba
`TC58TEG5DCLTA00` NAND modules:
 
|                  | SK hynix      | Toshiba         |
| ---------------- | ------------- | --------------- |
| Part No          | H27UCG8T2ETR  | TC58TEG5DCLTA00 |
| Type             | MLC           | MLC             |
| Erase Block Size | 4194304 bytes | 4194304 bytes   |
| Page Size        | 16384 bytes   | 16384 bytes     |
| Sub-Page Size    | 16384 bytes   | 16384 bytes     |
| OOB Size         | 1664 bytes    | 1280 bytes      |
| Max. LEB COUNT   | 4096          | 4096            |
| Capacity         | 8 GB          | 4 GB            |

Both chips are Multi-level cell "MLC" NAND chips. Compared to Single-level cell
"SLC" NAND, they store multiple bits per cell resulting in a higher data density.
Unfortunately that comes at a price - they are more sensitive to errors and have
a lower endurance. MLC NAND is not supported by the UBI/UBIFS layers in mainline
Linux. However, the original NextThingCo Linux 4.4 branches supported MLC NAND.
Both NAND chips can also be operated in an SLC mode, where only one bit per cell
is stored. Only half their capacity is available for data storage as a result.
Here we focus on mainline Linux and thus use the NAND in SLC mode.

NAND consists of so called "erase-blocks". Whenever data is written to the NAND
a whole erase-block is erased and re-written. Even when only a single bit
has changed, it is necessary to write a full erase-block.
Erase-blocks wear out with a growing number of write-cycles and can become
unusable, so-called "bad blocks".
Wear-leveling algorithms to miminimize wear-out and bad-block handling needs to
be implemented in software.

Data is read in pages, in our case for both NAND types in chunks 16 KiB at once.
Thus, each erase block consists of 256 pages.
Pages can also be divided in sub-pages, but that is not the case for the NAND
used on C.H.I.P. For every page there is a so-called out-of-band (OOB) area
where error-correction-code (ECC) data is stored.
So in reality, the SK hynix NAND has a page size of 16384 + 1664 = 18048 bytes 
of which 16384 are available for data storage. Consequently, the erase blocks
are really 4620288 bytes in size with 4194304 usable bytes.
For Toshiba its the real page size is 16384 + 1280 = 17664 bytest and the real
erase block size is 4521984 bytes.
This becomes important when we want to read from raw NAND and prepare raw NAND
images for flashing.

As already mentioned, the SK hynix and the Toshiba NAND used on C.H.I.P differ
in their capacity and their OOB size.
In the `CHIP_defconfig` for U-Boot in the previous chapter we have defined OOB
size matching the SK hynix NAND module `CONFIG_SYS_NAND_OOBSIZE=0x680` - as
 0x680 converted to decimal is 1664.
So far this setting did not matter, as we always loaded U-Boot and it's SPL
part to C.H.I.P's RAM via the `sunxi-fel` tool.
But as we want the U-Boot SPL to load the rest of U-Boot from the NAND we now
have to define the correct OOB size.

So, when building the U-Boot SPL for a the Toshiba NAND, we need update the
U-Boot defconfig:

```
sed -i -e 's/\(CONFIG_SYS_NAND_OOBSIZE\)=.*/\1=0x500/' \
${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/CHIP_defconfig
cd ${BR_DIR}
make uboot-reconfigure
```

And when we want to switch back to SK hynix NAND do this:
```
sed -i -e 's/\(CONFIG_SYS_NAND_OOBSIZE\)=.*/\1=0x680/' \
${BR2_EXTERNAL}/board/nextthingco/CHIP/uboot/CHIP_defconfig
make uboot-reconfigure
``` 

## SPL NAND image

The BROM code only has a very basic NAND driver implementation that does not
know about the parameters of the actual NAND chip. It tries to read the SPL code
from page 0 on block 0 of the NAND. If it does not find valid boot code there
it continues at page 0x40, page 0x80, and page 0xc0 on erase block 0.
Then it continues with pages 0x100, 0x140, 0x180 and 0x1c0 on erase block 1.
For maximum robustness in total a copies of the SPL code can be writte to the
NAND. 

As the BROM code does not know about the size of the NAND for each page various
formats are probed - more details are explained in the
[linux-sunxi.org](https://linux-sunxi.org/NAND#More_information_on_BROM_NAND)
wiki.

The `sunxi-nand-image-builder` tool takes the `sunxi-spl.bin` as input and
writes an output file including error correction codes that can be flashed onto
the raw NAND and is recognized by the BROM code.
Various formats can be selected - the most robust one only using 1024 bytes per
page plus 64 bit for error correction.

Let's create a BROM image for sk Hynix NAND:
```
cd ${BR_DIR}/output/images
${BR_DIR}/output/host/bin/sunxi-nand-image-builder -p 16384 -o 1280 -e 0x400000 -s -b -u 1024 -c 64/1024 sunxi-spl.bin sunxi-spl.bin.nand
```
This blows up the 16384 bytes `sunxi-spl.bin` into a 282624 bytes `sunxi-spl.bin.nand` file. 

in a socalled "post-image"
script in Buildroot. The post-image script is executed after U-Boot, Linux
and the rootfs have been built.

Let's add the sunxi-tools (including the `sunxi-nand-image-builder`) to the
Buildroot host tools and also declare the post image script:
```
cat <<EOF >>"${BR2_EXTERNAL}"/configs/nextthingco_chip_defconfig
BR2_PACKAGE_HOST_SUNXI_TOOLS=y
BR2_ROOTFS_POST_IMAGE_SCRIPT="\${BR2_EXTERNAL_CHIP_PATH}/board/nextthingco/CHIP/post-image.sh"
EOF

cd ${BR_DIR}
make nextthingco_chip_defconfig
```

Create that `post-image.sh` script which will be executed by Buildroot after
it has created the U-Boot, Linux and root filesystem images:
```
cat <<EOF >${BR2_EXTERNAL}/board/nextthingco/CHIP/post-image.sh
#!/bin/bash

# Environment variables passed in from buildroot:
# BR2_CONFIG, HOST_DIR, STAGING_DIR, TARGET_DIR, BUILD_DIR, BINARIES_DIR and BASE_DIR.

echo "##############################################################################"
echo "## \$0 "
echo "##############################################################################"

echo "# \\\$1 = \$1"
echo "# \\\$2 = \$2"

IFS=", " read -r -a EXTRA_ARGS <<< "\$2"

echo "# BR2_CONFIG=\$BR2_CONFIG"
echo "# BR2_EXTERNAL=\$BR2_EXTERNAL"
echo "# HOST_DIR=\$HOST_DIR"
echo "# STAGING_DIR=\$STAGING_DIR"
echo "# TARGET_DIR=\$TARGET_DIR"
echo "# BUILD_DIR=\$BUILD_DIR"
echo "# BINARIES_DIR=\$BINARIES_DIR"
echo "# BASE_DIR=\$BASE_DIR"

ROOT_DIR="\${BR2_EXTERNAL_CHIP_PATH}"

# Read U-Boot version and config file from the Buildroot configuration
UBOOT_VER="\$(sed -n -e 's/BR2_TARGET_UBOOT_VERSION="\([^"]*\)"/\1/p' \$BR2_CONFIG)"
UBOOT_CFG="\${BUILD_DIR}/uboot-${UBOOT_VER}/.config"
[ ! -f "\${UBOOT_CFG}" ] && echo "ERROR: cannot find U-Boot config $UBOOT_CFG" && exit 1

# Read NAND parameters from the U-Boot configuration
BLOCK_SIZE="\$(sed -n -e 's/CONFIG_SYS_NAND_BLOCK_SIZE=\(.*\)/\1/p' \$UBOOT_CFG)"
PAGE_SIZE="\$(sed -n -e 's/CONFIG_SYS_NAND_PAGE_SIZE=\(.*\)/\1/p' \$UBOOT_CFG)"
OOB_SIZE="\$(sed -n -e 's/CONFIG_SYS_NAND_OOBSIZE=\(.*\)/\1/p' \$UBOOT_CFG)"

INPUT_SPL="\${BINARIES_DIR}/sunxi-spl.bin"
OUTPUT_SPL="\${BINARIES_DIR}/sunxi-spl.bin.ecc"
OUTPUT_IMAGE="\${BINARIES_DIR}/sunxi-spl.bin.nan"

\${HOST_DIR}/bin/sunxi-nand-image-builder -s -b -c 64/1024 -u 1024 -e \${BLOCK_SIZE} -p \${PAGE_SIZE} -o \${OOB_SIZE} \${INPUT_SPL} \${OUTPUT_SPL}


OUTPUT_BLOCK_SIZE=\$(( BLOCK_SIZE/PAGE_SIZE * (PAGE_SIZE+OOB_SIZE) ))

dd if=/dev/urandom of=\${OUTPUT_IMAGE} bs=\$((PAGE_SIZE+OOB_SIZE))

EOF
chmod a+x ${BR2_EXTERNAL}/board/nextthingco/CHIP/post-image.sh
```

As described in 
,
the A13/R8 BROM code tries to read the SPL code from page 0, page 64, page 128,
... until it finds a valid signature.


### Write U-Boot SPL to the NAND
- repeat SPL code multiple times, special format
- we need to 
Two partitions: SPL and SPL-backup

### Write U-Boot to the NAND
 - the U-Boot image does not  

### Write Rootfs to the NAND
 - enable building of ubi/ubifs images in Buildroot:
 - the ubifs/ubi images are not depending on the OOB size of the NAND chip used, i.e. we ca

### script to flash whatever Buildroot spits out
