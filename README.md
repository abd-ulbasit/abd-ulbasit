# Abdul Basit Sajid

Backend and infrastructure engineer, working remotely with a UK team since 2023.
I work on capacity, latency and the deployment path: what a system costs to run,
why it is slow, and how it ships without going down. Go, Python, Kubernetes,
Postgres.

Four times the number was not what it looked like.

## A copy-on-write system copied 5 GiB

Branching a 5 GiB Postgres database in [pgbranch][pgbranch] took 61.9 s and left
a writable layer the size of the entire dataset. On a system whose whole premise
is that branches share one base and store only their own changes, that is not
slowness. That is the copy-on-write not happening.

The branch's own log said `redo done ... elapsed: 0.00 s`, so the minute went
somewhere before WAL replay. Before recovery, Postgres fsyncs every file in the
data directory, and it opens each one `O_RDWR`, because not every platform
allows `fsync()` on a read-only descriptor. It writes nothing. But OverlayFS
copies a file up on the open, not on the write, so the durability pass copied
the whole dataset before a single query ran. After the fix: 1.89 s and 33.1 MiB.

p50 of five runs on a Colima VM (4 vCPU, kernel 6.8, overlay2 on ext4) hosted on
an M1 Pro, June 2026. The [benchmarks doc][bench] still publishes the pre-fix
table, and says why the two sets of numbers are not comparable.

## The hazard was documented one layer below where it bit me

In [goqueue][goqueue], `Log.ReadFrom` took a read lock and then called an
exported method that took the same lock again. Go's `RWMutex` is not reentrant,
and a pending writer blocks new readers, so the second acquisition deadlocks
against a writer that is itself waiting on the first.

I had written the warning myself, [one layer down][note]:

> `// Note: We need to unlock before calling ReadFrom (it locks again)`

Knowing a hazard and finding every instance of it are separate jobs. There was a
second one in the quota manager.

## A metric that reads as broken and is correct

[sluice][sluice] exports `sluice_pool_hits_total`, and on the L4 path it is
always zero. Making it move means not forwarding the client's FIN to the
backend. I tried that. A client that half-closed received an empty response, and
because the abandoned socket went back into the pool still owing a reply, the
next client could be served the previous client's response body.

Both were reproduced, the change was reverted, and the README explains the zero
instead. An idle counter is cheaper than a protocol-visible correctness bug.

## Eight milliseconds on the GPU, 2,400 Python calls around it

A real-time inference service took 2.8 s per request while the GPU sat at 0 to
13% utilisation. Inference itself was 8 ms per model, and around each of those
8 ms were roughly 2,400 Python function calls. A bigger GPU makes the 8 ms
smaller and does nothing at all to the rest, which is why buying hardware had
not helped: the ceiling was a single Python process, not the accelerator.
Fixing the fan-out is what made four GPUs usable in the first place. Proved to
500 concurrent under load test, against a production peak of 147.

---

Some of this is still wrong. I do not know which part yet.

[basit.engineer][site] · [pgbranch][pgbranch] · [goqueue][goqueue] ·
[steward][steward] · [sluice][sluice] · [forgepoint][forgepoint] ·
[Kubernetes guide][guide]

This file used to generate itself. A cron job wrote 34 of the first 65 commits
in this repository and not one of them said anything.

[site]: https://basit.engineer
[pgbranch]: https://github.com/abd-ulbasit/pgbranch
[goqueue]: https://github.com/abd-ulbasit/goqueue
[sluice]: https://github.com/abd-ulbasit/sluice
[steward]: https://github.com/abd-ulbasit/steward
[forgepoint]: https://github.com/abd-ulbasit/forgepoint
[guide]: https://github.com/abd-ulbasit/bookstore-kubernetes-guide
[bench]: https://github.com/abd-ulbasit/pgbranch/blob/main/docs/benchmarks.md#before-the-fix-branch-creation-scaled-with-data-size
[note]: https://github.com/abd-ulbasit/goqueue/blob/beac5b4e727f47f1d991f40774948715542788bf/internal/storage/segment.go#L1121
