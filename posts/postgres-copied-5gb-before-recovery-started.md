---
title: "Postgres copied 5 GiB before recovery started"
date: 2026-07-26
description: "My copy-on-write Postgres branching benchmark said a 5 GiB branch took 61.9 s and left a 5.05 GiB writable layer. The cause was a pre-recovery fsync pass opening every data file O_RDWR, which forces a full OverlayFS copy-up."
tags: [postgres, overlayfs, linux, copy-on-write, docker, performance, debugging]
---

# Postgres copied 5 GiB before recovery started

I've been building [pgoverlay](https://github.com/abd-ulbasit/pgoverlay), which gives you copy-on-write branches of a Postgres database: seed once from a running server, then create disposable, writable copies that share the base data and store only what they change. Each branch is a stock `postgres` container whose `PGDATA` is an OverlayFS mount: the seeded source volume read-only below, an empty writable volume on top.

The first real benchmark said branching a 5 GiB database took **61.9 seconds** and left a **5.05 GiB** writable layer behind.

The 61.9 seconds is a performance problem. The 5.05 GiB is a correctness problem. On a system whose entire premise is that a branch shares one base and writes only its own changes, a writable layer the size of the whole dataset means the copy-on-write is not happening. I had built a slow `cp`.

## The measurement

`hack/benchmark.sh`, five create/destroy cycles per size, on a Colima VM (4 CPUs, 8 GiB RAM, Ubuntu 24.04, kernel 6.8, Docker's overlay2 driver on a VM-local ext4 disk) on an M1 Pro. Databases generated with `pgbench -i`.

| Database | Branch create (p50 of 5) | Writable layer after create |
|---|---|---|
| 1.00 GiB | 7.66 s | 1.05 GiB |
| 5.00 GiB | **61.85 s** | **5.05 GiB** |

Individual 5 GiB runs: 69.9, 66.1, 61.4, 60.0, 61.9 s. Not noise, not a cold-cache artifact: a stable cost that scaled with data size.

Two things fell out of the table immediately:

1. The writable layer was ≈ the database size, every time. 1.05 GiB for a 1.00 GiB database, 5.05 GiB for a 5.00 GiB one. That's not "some overhead." That's a full copy plus change.
2. Divide bytes by seconds and you get ~87 MB/s at 5 GiB and ~140 MB/s at 1 GiB. That's not a Postgres number, it's a disk number. The smaller dataset fits the VM's page cache and the larger one doesn't. Create time wasn't being spent on anything clever. It was being spent moving bytes.

So the question stopped being "why is branch creation slow" and became "who is copying the database, and when."

## Who

A branch's seed comes from `pg_basebackup`, which means the data directory it boots on is a crash-consistent snapshot. So a branch's first boot is crash recovery. And the branch logs said the recovery itself did nothing:

```
redo done ... elapsed: 0.00 s
```

Zero seconds of redo, after sixty seconds of *something*. Whatever was eating the time happened before WAL replay.

Before replaying WAL, Postgres syncs the data directory in `SyncDataDirectory()`. The point is durability: if the cluster crashed once, there may be dirty pages from before the crash sitting in the OS page cache, and recovery must not build on top of writes that could still be lost. So Postgres walks the entire data directory and fsyncs every file in it, before it touches the WAL.

The relevant detail is *how* it opens those files. Shape of it, from `fd.c`:

```c
/* fsync_fname_ext(), simplified */
flags = PG_BINARY;
if (!isdir)
    flags |= O_RDWR;    /* not every platform allows fsync() on a read-only fd */
else
    flags |= O_RDONLY;

fd = OpenTransientFile(fname, flags);
pg_fsync(fd);
CloseTransientFile(fd);
```

Every regular file in `PGDATA`, opened read-write. It writes nothing. It opens, fsyncs, closes. On any normal filesystem that's a cheap portability quirk that nobody has to think about.

On OverlayFS it is the whole bug.

## OverlayFS copies up on open, not on write

The kernel's overlayfs documentation puts it plainly: when a file in the lower layer is accessed in a way that requires write access ("such as opening for write access"), it is first copied from the lower filesystem to the upper filesystem.

Read that as an implementation detail, because it is one: **the copy-up is triggered by the open, not by the write.** A process that opens a lower-layer file `O_RDWR`, writes not a single byte, and immediately closes it has still copied the entire file into the upper layer. The kernel cannot know at open time that you weren't going to write, so it materializes the file first and asks questions never.

If you want to see it with Postgres out of the way, here is the whole mechanism with nothing else in the frame. Run it as root, with the scratch directory on ext4 or xfs (tmpfs isn't accepted as an `upperdir`):

```sh
mkdir -p /var/tmp/ovl/{lower,upper,work,merged}
dd if=/dev/zero of=/var/tmp/ovl/lower/big bs=1M count=100 status=none
mount -t overlay overlay \
  -o lowerdir=/var/tmp/ovl/lower,upperdir=/var/tmp/ovl/upper,workdir=/var/tmp/ovl/work \
  /var/tmp/ovl/merged

find /var/tmp/ovl/upper -type f    # nothing yet, the upper layer is empty

# open read-write, write nothing, close
python3 -c 'import os; os.close(os.open("/var/tmp/ovl/merged/big", os.O_RDWR))'

find /var/tmp/ovl/upper -type f    # /var/tmp/ovl/upper/big
du -sh  /var/tmp/ovl/upper/big     # 100M
```

Now put the two halves together. Postgres opens every file in `PGDATA` read-write to fsync it. OverlayFS copies up every file that is opened read-write. So the durability pass that runs *before* recovery copied the entire dataset into the branch's supposedly-empty writable layer, before the branch served a single query. All in preparation for a WAL replay that then took 0.00 seconds.

The mechanism isn't specific to Postgres. Anything that fsyncs a directory tree at startup, or opens files read-write to check them, will do this on any overlay-backed filesystem. That's every container image layer in the world.

## Confirming it, and the fix

A plausible mechanism isn't a diagnosis. `recovery_init_sync_method` (Postgres 14+) exists precisely to replace the per-file pass with a single `syncfs()` call per filesystem, so the control run is one flag on an otherwise identical run:

```sh
exec docker-entrypoint.sh postgres -c recovery_init_sync_method=syncfs
```

That run finished recovery with the writable layer at **16 KiB**. Not 5 GiB, not 500 MiB: 16 KiB. One variable, and the copy disappeared entirely.

That control run is now the fix; it's a single line in the branch entrypoint. Re-running the same benchmark with it in place:

| 5.00 GiB database | Branch create (p50 of 5) | Writable layer after create |
|---|---|---|
| before | 61.85 s | 5.05 GiB |
| after | **1.89 s** | **33.1 MiB** |

And creation is now flat in database size (1.90 s at 1 GiB, 1.89 s at 5 GiB), which is what a copy-on-write system is supposed to look like. The 33.1 MiB is recycled WAL segments written during recovery plus overlay bookkeeping.

**Why `syncfs` is safe here, specifically.** `syncfs()` syncs the whole filesystem containing the data directory, which is a *superset* of what the per-file pass covers, so the property that pass exists to guarantee (no pre-recovery dirty pages left unflushed) still holds, and crash-recovery semantics don't change. The documented downsides of `syncfs` are that I/O errors on unrelated files on the same filesystem can be reported to you, and that on some kernels errors can be missed; both are scoped to *other files on the same filesystem*, and a pgoverlay branch's filesystem is its own disposable overlay mount holding nothing else. It costs me Postgres 13 and below, and Linux-only, which is now a documented support floor rather than a silent degradation.

## What I did not fix

The cost moved. It did not vanish, and pretending otherwise would make the numbers above worthless.

OverlayFS copies up **whole files**, and Postgres heap and index segments run to 1 GiB each. Before the fix, creation had already materialized every file, so subsequent writes only grew an already-copied layer. After the fix the layer starts near-empty, so the first write to any segment pays that segment's entire copy-up. The write-amplification column in my own benchmarks reads *worse* after the fix than before it:

| 5.00 GiB database | rw layer after updating 1% of rows |
|---|---|
| before | +179.1 MiB |
| after | 5.20 GiB |

Those two numbers measure different things. The old probe measured incremental growth of a fully-materialized layer; the new one measures copy-up from scratch. But the underlying trade is real. A bulk `UPDATE` plus `CHECKPOINT` touching every segment converges on roughly 1× the database.

So the honest statement is: **the cost moved from pay-at-create to pay-per-file-written.** pgoverlay is built for dev, CI, and PR-review branches that read a lot and write a little. For that workload it's strictly better, and branches stay in the tens of megabytes. For a branch that rewrites its whole dataset, it's a wash. Block-level copy-on-write (ZFS, or a CSI driver with real snapshots) doesn't have this problem at all, because its copy-up granularity is a block rather than a file. That's a genuine advantage of those backends and I'd rather say so than round it off.

## Where this sits

There are good tools here and I'm not going to pretend otherwise. [Neon](https://neon.tech) and [Supabase](https://supabase.com) both do database branching well. But in their clouds, on their storage. You can't point them at the Postgres you already run. [DBLab](https://postgres.ai/products/how-it-works) is the established self-hosted answer, and it's block-level CoW, which as noted is technically the better primitive. The cost is that you provision and operate a ZFS or LVM pool for it.

pgoverlay takes the middle path: plain Docker or Kubernetes, stock Postgres images, and OverlayFS (the same mechanism container images already use) applied to `PGDATA`. No special filesystem, no cloud, no patched Postgres. The whole-file copy-up granularity above is the price of that choice.

## The part worth keeping

Two things I'd take to the next project:

**A benchmark that contradicts your design is the most valuable output it can produce.** The number that mattered wasn't 61.9 seconds, it was 5.05 GiB. "Slow" invites tuning; "the writable layer is the size of the database" tells you the design isn't running. I nearly went looking for I/O tuning knobs first.

**Copy-on-write filesystems are triggered by intent, not by action.** OverlayFS charges you a full file copy for *declaring* you might write. So on an overlay-backed path, `O_RDWR` is not a cheap default; it's a commitment, and any code that opens files read-write "just to be safe" is buying the most expensive thing in the system.

---

Full before/after tables, methodology, hardware, and the pre-fix numbers kept intact: [docs/benchmarks.md](https://github.com/abd-ulbasit/pgoverlay/blob/main/docs/benchmarks.md). The project is Go and Apache-2.0: [github.com/abd-ulbasit/pgoverlay](https://github.com/abd-ulbasit/pgoverlay).
