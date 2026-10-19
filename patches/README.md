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

## Fixes found by build 4

Build 4 got all the way through the config gates (SUSFS v2.2.0 detected,
`CONFIG_THREAD_INFO_IN_TASK=y`, `CONFIG_KSU_SUSFS=y` survived kconfig, driver
reported all seven hooks found) and then failed compiling `fs/stat.o`:

1. **Declaration order.** In this tree `vfs_fstatat()` is at line ~124 but the
   stock KSU extern block is ~200 lines further down, so the SUSFS declarations
   landed *after* their use -> `'ksu_su_compat_enabled' undeclared`, three
   `-Werror=implicit-function-declaration`, and a resulting `conflicting types
   for '__ksu_is_allow_uid_for_current'`. The SUSFS declarations now sit right
   after `EXPORT_SYMBOL(vfs_fstat)`, where the redmi tree keeps them, and the
   late block carries only the non-SUSFS extern (its dangling
   `__attribute__((hot))` would otherwise have attached to a variable).

2. **`filename_lookup` was `static`** in this tree's `fs/namei.c` (the redmi
   tree has it non-static). SUSFS calls it from `fs/stat.c` and `fs/open.c`, so
   it is de-staticized under `#ifdef CONFIG_KSU_SUSFS` and left static
   otherwise. No `EXPORT_SYMBOL` needed - all three objects are built into
   vmlinux.

Checked and NOT a problem: `susfs_is_inode_sus_path` has a 2-arg form only
under `#if LINUX_VERSION_CODE >= KERNEL_VERSION(6,6,0)`; 4.4 takes the 1-arg
form. `getname_flags` is already declared non-static in `include/linux/fs.h`.
`ksu_handle_sys_read` is declared 1-arg here but 3-arg in the driver - benign,
the driver body never dereferences the two extra params (they exist for the
tracepoint path), and this is what the proven redmi tree does.

## Fixes found by build 8

Build 8 cleared `fs/stat.c` and `fs/exec.c` and surfaced two more:

3. **`fs/notify/fdinfo.c`: no `inotify_mark_user_mask()` in this tree.** The
   redmi fixup commit (`4284431b`) rewrites that `seq_printf` to call a helper
   this kernel does not have. Replaced with this tree's own local
   `u32 mask = mark->mask & IN_ALL_EVENTS`, matching its original `seq_printf`.

4. **`drivers/staging/samsung/sec_gaf.c`: `struct thread_info` has no member
   `cpu`.** This is a genuine consequence of `select THREAD_INFO_IN_TASK` -
   that option moves `cpu` (and `task`) out of `thread_info` into
   `task_struct`, and Samsung's ramdump-offset exporter still reads the old
   location. Guarded to point at `offsetof(struct task_struct, cpu)` when
   `THREAD_INFO_IN_TASK && SMP`. Not fixed by disabling `CONFIG_SEC_DEBUG`:
   that is `=y` here and gates a lot more than this file.

A sweep for every other site that `THREAD_INFO_IN_TASK` could break
(`offsetof(struct thread_info, cpu|task)`, `ti->task`, `ti->cpu`,
`current_thread_info()->task`) found only two more, both already correct:
`arch/arm64/include/asm/current.h` reads `sp_el0` under the option, and
`include/asm-generic/current.h` is not used by arm64.

## Fixes found by build 10 (link stage)

Build 10 compiled the **whole kernel** and then failed linking `vmlinux`:

    fs/stat.c:386: undefined reference to `ksu_handle_newfstat_ret'
    fs/stat.c:508: undefined reference to `ksu_handle_fstat64_ret'

The driver defines both only inside `#ifdef CONFIG_KSU_MANUAL_HOOK`
(`runtime/ksud_integration.c`, guard opens at line 593). SUSFS inline hook is a
*different member of the same kconfig choice*, so in a SUSFS build they do not
exist - and `inline_hook_check.mk` never asks for them, only
`manual_hook_check.mk` does. The redmi tree handles this exactly this way:
its `*_ret` call sites are guarded `#ifdef CONFIG_KSU_MANUAL_HOOK`, and in
SUSFS mode it instead calls `ksu_handle_vfs_fstat(fd, &stat->size)` from
`vfs_fstat()` behind the `ksu_is_init_rc_hook_enabled` static key - that is how
ksud gets its init.rc injected.

So: the three `#if defined(CONFIG_KSU) && !defined(CONFIG_KSU_KPROBES_KSUD)`
guards in `fs/stat.c` gained `&& !defined(CONFIG_KSU_SUSFS)`, and `vfs_fstat()`
gained the `ksu_handle_vfs_fstat` hook.

The linker reporting *only* these two also confirms `ksu_handle_sys_read`,
`ksu_handle_input_handle_event`, `ksu_handle_setresuid`, `ksu_handle_stat`,
`ksu_handle_faccessat`, `ksu_handle_execveat`, `ksu_handle_sys_reboot` and
`ksu_su_compat_enabled` all resolve in SUSFS mode.
