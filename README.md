# Abdul Basit Sajid

Backend and infrastructure engineer, working remotely with a UK team since 2023.
I work on capacity, latency and the deployment path: what a system costs to run,
why it is slow, and how it ships without going down. Go, Python, Kubernetes,
Postgres.

Four times the number was not what it looked like.

## A copy-on-write system copied what it read

[pgoverlay][pgoverlay] gives each pull request its own Postgres branch: a stock
container whose data directory is an OverlayFS view of one shared seed, meant
to store only what that branch changes. A branch of a 5 GiB database held
5.05 GiB before its first query, and one `SELECT count(*)` copied a 488.5 MiB
table into a branch that had only read it.

Same cause both times. Postgres opens files `O_RDWR` even when it only reads
them: every file in the data directory before WAL replay, because not every
platform allows `fsync()` on a read-only descriptor, and every table file a
query touches. OverlayFS copies a file up on the open, not on the write. A
one-flag control run proved the first (`recovery_init_sync_method=syncfs`:
16 KiB, not 5.05 GiB). For the second, v1.0.0 preloads a small library that
opens table files read-only until their first write, so reads copy no table
data, at a warm pgbench cost of at most 1.6% at the median.

The 5 GiB numbers come from a Colima VM on an M1 Pro (create times are the
median of five runs), the 488.5 MiB read from Docker on Linux with ext4, and
the pgbench numbers from GitHub-hosted amd64 and arm64 runners. All of them,
with their raw runs, are in the [benchmarks doc][bench], and the
[write-up][post] tells the whole story.

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

A real-time inference service took 2.8 s per request while GPU utilisation sat
between 0 and 13% under normal load, reaching 83% only at 150 concurrent users.
Inference itself was 8 ms per model, and around each of those
8 ms were roughly 2,400 Python function calls. A bigger GPU makes the 8 ms
smaller and does nothing at all to the rest, which is why buying hardware had
not helped: the ceiling was a single Python process, not the accelerator.
Fixing the fan-out is what made four GPUs usable in the first place. Proved to
500 concurrent under load test, on four L40Ses.

---

Some of this is still wrong. I do not know which part yet.

[basit.engineer][site] · [pgoverlay][pgoverlay] · [goqueue][goqueue] ·
[steward][steward] · [sluice][sluice] · [forgepoint][forgepoint] ·
[Kubernetes guide][guide]

[site]: https://www.basit.engineer
[pgoverlay]: https://github.com/abd-ulbasit/pgoverlay
[goqueue]: https://github.com/abd-ulbasit/goqueue
[sluice]: https://github.com/abd-ulbasit/sluice
[steward]: https://github.com/abd-ulbasit/steward
[forgepoint]: https://github.com/abd-ulbasit/forgepoint
[guide]: https://github.com/abd-ulbasit/bookstore-kubernetes-guide
[bench]: https://github.com/abd-ulbasit/pgoverlay/blob/main/docs/benchmarks.md#true-copy-on-write-v100
[post]: https://www.basit.engineer/posts/a-select-copied-the-whole-table.html
[note]: https://github.com/abd-ulbasit/goqueue/blob/beac5b4e727f47f1d991f40774948715542788bf/internal/storage/segment.go#L1121
