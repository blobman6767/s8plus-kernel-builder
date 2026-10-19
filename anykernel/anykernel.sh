### AnyKernel3 Ramdisk Mod Script
### Samsung Galaxy S8+ (SM-G955F / dream2lte, Exynos 8895) - A-only, no slots

properties() { '
kernel.string=universal8895 kernel + KernelSU/SUSFS
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=dream2lte
device.name2=dream2ltexx
device.name3=SM-G955F
device.name4=dream2ltexx
supported.versions=
supported.patchlevels=
'; } # end properties

# shell variables - matches BoardConfigCommon.mk:
#   BOARD_KERNEL_BASE 0x10000000, PAGESIZE 2048,
#   --kernel_offset 0x8000 --ramdisk_offset 0x01000000 --tags_offset 0x100
BLOCK=/dev/block/by-name/BOOT;
IS_SLOT_DEVICE=0;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;

## AnyKernel install
. tools/ak3-core.sh;

split_boot;
flash_boot;
## end install
