# SUSFS kernel-side patch for universal8895 (4.4.302)

`0001-susfs-v2.2.0-kernel-4.4-exynos8895.patch` ports **SUSFS v2.2.0** into the
LineageOS `universal8895` 4.4 tree (branch `lineage-23.2`).

## Where it came from

`susfs4ksu` has **no kernel-4.4 branch** (4.9 is the floor, and that branch is
still v1.5.5). The ReSukiSU driver reads `SUSFS_VERSION` out of
`include/linux/susfs.h` and expects 2.x. So the sources here were taken from the
4.4 tree already proven on the Redmi Note 7 (lavender):

    blobman6767/android_kernel_xiaomi_sdm660_44 @ 02242273  (resukisu-susfs-newfstat)
      e480a927  add susfs          -> fs/susfs.c, include/linux/susfs{,_def}.h + hooks
      4284431b  fs: fix for susfs
      bab1fe05  static symbol export
      400c5712  update static symbol export
      aade056a  add susfs hook     -> only the 4 hooks exynos lacked

Dropped from `e480a927`: the `drivers/kernelsu/` changes (that tree vendors the
driver in-tree; here the driver comes from the pinned snapshot) and pure
blank-line churn.

## Things that are NOT a straight copy

The Redmi and exynos trees diverge, so these were hand-reconciled:

1. **Hook ABI.** With `CONFIG_KSU_SUSFS=y` the driver switches
   `ksu_handle_stat`/`ksu_handle_faccessat` from `const char __user **` to
   `struct filename **`, and hooks execve inside `do_execveat_common()` with a
   real `&fd`/`&flags` instead of the stock tree's `(int *)AT_FDCWD`/`0`. These
   are `extern` declarations, so a mismatch compiles silently and misbehaves at
   runtime. `fs/{stat,open,exec}.c` now carry the SUSFS flow under
   `#ifdef CONFIG_KSU_SUSFS` with the original kept under `#else`.
2. **`select THREAD_INFO_IN_TASK`** added to `arch/arm64/Kconfig`.
   `CONFIG_KSU_SUSFS depends on THREAD_INFO_IN_TASK && 64BIT`. The tree already
   ships the whole backport (`current.h`, `thread_info.h`, `head.S`, `entry.S`,
   `asm-offsets.c`, `smp.c`, ...) but arm64 never selected it. It is a
   promptless `bool`, so a defconfig line is ignored - it must be `select`ed.
   SUSFS's TIF bits (33-35) do not collide with arm64's (max 29).
3. **`CONFIG_RKP_NS_PROT`** (Samsung RKP) turns `struct mount.mnt` into a
   pointer, which would break every SUSFS `&mnt->mnt`. It is `depends on
   RKP_KDP`, `default n`, nothing selects it, and LineageOS leaves RKP off - so
   the embedded-struct layout SUSFS expects is what gets built. If RKP is ever
   enabled this patch must be revisited.
4. `fs/proc/cmdline.c` uses `updated_command_line` (the LineageOS tree already
   spoofs `verifiedbootstate=green` / `warranty_bit=0` there), not the Redmi's
   `new_command_line`.
5. `drop_mountpoint()`, `inotify_fdinfo()` and `show_smap()` differ structurally;
   the SUSFS blocks were re-anchored by hand.

`kernel/reboot.c` needed nothing - the tree already has `ksu_handle_sys_reboot`
with the matching `void __user **arg` signature.

## Verifying

    git clone --depth=1 -b lineage-23.2 \
      https://codeberg.org/universal8895/kernel_samsung_universal8895 k
    cd k && git apply --check ../patches/0001-susfs-v2.2.0-kernel-4.4-exynos8895.patch
