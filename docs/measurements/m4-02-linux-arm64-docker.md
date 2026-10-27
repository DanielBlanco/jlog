# M4-02 Linux ARM64 resource measurements in Docker

Recorded 2026-10-27. All **70 measured cases** pass exact output/status/hash
checks, with no application source changes. A 62-case smoke matrix also passes.
This is native ARM64 execution in an ARM64 Linux VM on Apple Silicon, not
emulated x86-64 and not a bare-metal Linux host. **The planned native Linux
x86-64 release gate remains open.**

The [JSON artifact](m4-02-linux-arm64-docker.json) preserves every command,
fixture size/max-line bytes, N, native elapsed/user/system time, peak RSS in
bytes, statuses, output/input hashes, guest/host/image/compiler provenance,
source hashes, and the separate failing descriptor gate.

## Environment and preparation

| Item | Recorded value |
| --- | --- |
| Physical host | Apple M1 Pro, macOS ARM64, 32 GiB RAM. |
| Docker engine/guest | Linux ARM64 (`aarch64`), Docker Desktop, Linux 7.0.14-linuxkit. |
| Guest resources | 10 virtual CPUs; 8,214,851,584 bytes RAM; no additional container CPU/memory quota. |
| Userspace | Debian 12 bookworm, 4,096-byte pages; 8,388,608-byte stack soft limit. |
| Execution user | UID 1000; permission fixtures execute without root privileges. |
| Compiler/platform | Roc `nightly-2026-10-09-258ab27`; unchanged basic-cli 0.25.0 pin. |
| Timing tool | Debian `time` package 1.9-0.2, GNU verbose format; its version banner reports `UNKNOWN`, retained in JSON. |
| Source/data storage | `/src` read-only bind mount; compiler outputs, caches, fixtures and stdout on the container's Linux filesystem. |
| Runtime networking | Docker bridge disconnected after build/test dependencies resolved; attached network map is empty during measurement. |

The exact compiler asset is
`roc_nightly-linux_arm64-2026-10-09-258ab27.tar.gz`, downloaded from the
[immutable pinned nightly release](https://github.com/roc-lang/nightlies/releases/tag/nightly-2026-10-09-258ab27)
and verified against SHA-256
`9750ce89a820d3cdeadd751996d26c70b68584ca9428e52f43a1bb20702c54e5`.
The Debian base manifest is
`sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8`;
the built image ID is
`sha256:77bae4abc313f331d62956145c843235a20d82f7729b7d5d76ff2c70fa5fa6f5`.
Installed tooling package versions are archived; apt security updates can make a
future rebuild differ from this image despite the pinned base/compiler.

The optimized measured binary is a statically linked ARM aarch64 ELF,
SHA-256 `e279601f4160b9b4830e34f37340a472680ba492eaf3225f8c9ff9ec24504f25`.
It is retained locally as ignored `dist/jlog-linux-arm64`; the macOS `dist/jlog`
was not replaced. Source base commit is `816f65c` plus the pending measurement
tooling/docs; application module hashes are recorded and no application source
diff was introduced.

## Verification before measurement

[The Docker verification script](../../tests/docker/verify.sh) executes the
checks against the native compiler and both freshly built Linux artifacts:

| Check | Result |
| --- | --- |
| `roc check` and explicit-source formatting | Pass. |
| Development pure checks | 273 pass. |
| Optimized pure checks | 273 pass. |
| Ordinary executable suite against dev | 63 methods pass, no skips. |
| Ordinary executable suite against speed | 63 methods pass, no skips. |
| Timing normalization unit checks | Three pass, including Linux KiB-to-byte conversion and unchanged macOS interpretation. |
| Strict descriptor gate, both builds | Three methods fail with 15 failing subcases per build; exit 1 is preserved. |

The executable suite successfully opens a raw invalid-UTF-8 filename on the
guest filesystem and exercises permissions, broken pipes, and actual WouldBlock
after a consumed prefix. These are Linux ARM64 results; they do not substitute
for execution on the required x86-64 target.

`time -v /usr/bin/true` succeeds and reports 828 KiB maximum RSS. A separate
Python process touches a 32 MiB allocation and reports 39,788 KiB peak RSS,
checking that the timer observes real resident growth. GNU time's
[maximum-RSS unit](https://www.gnu.org/software/time/manual/html_node/Memory-Resources.html)
is converted from KiB to bytes; it is not treated as the byte value used by
macOS. Measurements cover the CLI process, excluding the Python driver, Docker
VM/daemon, physical host, and filesystem page cache.

## Fixture matrix and results

The same seven fixture definitions as the
[macOS baseline](m4-02-macos-arm64.md) have identical SHA-256 hashes:
100,000/1,000,000 valid 1,024-byte records; all-invalid equivalents; single
1 MiB/8 MiB bodies; and a two-record input with maximum tail N. All run through
file and redirected stdin. Valid data covers inspect/count/filter and tail
N=0/1/64/4096/16384; invalid data covers inspect/count/filter and tail N=0/16384.
Large-line cases cover all modes with tail N=1.

Native elapsed seconds and peak RSS in MiB for file input:

| Mode | 100,000 time | 100,000 RSS | 1,000,000 time | 1,000,000 RSS |
| --- | ---: | ---: | ---: | ---: |
| Inspect | 0.74 | 0.38 | 7.38 | 0.39 |
| Count | 0.71 | 0.42 | 7.12 | 0.42 |
| Filter | 1.05 | 0.38 | 9.98 | 0.39 |
| Tail 0 | 0.71 | 0.39 | 6.96 | 0.38 |
| Tail 1 | 0.70 | 0.38 | 6.85 | 0.42 |
| Tail 64 | 1.11 | 0.51 | 10.65 | 0.51 |
| Tail 4096 | 0.74 | 5.13 | 6.95 | 5.13 |
| Tail 16384 | 0.72 | 19.38 | 6.96 | 19.38 |

At fixed N=16,384, redirected stdin peaks at 19.51 MiB for both input sizes;
N=4,096 peaks at 5.13 MiB. Count/filter remain around 0.4 MiB despite the
10-fold input increase and 512,000,000 bytes of output from the larger filter.
Original order and bytes are checked by exact golden hashes. The maximum-N tiny
input emits exactly two records at about 0.39 MiB peak RSS, without N-slot
preallocation.

All-invalid RSS stays around 0.39–0.42 MiB across sizes/modes/sources. Both
100,000 and 1,000,000 invalid records retain exactly 100 details, report the
correct omitted count, emit count 0 or empty tail/filter data, and exit 4.

RSS ranges across the four long-line modes:

| Body size | File RSS | Stdin RSS |
| --- | ---: | ---: |
| 1 MiB | 2.45 MiB | 1.38 MiB |
| 8 MiB | 17.18–17.56 MiB | 8.48–10.04 MiB |

All long-line cases complete with status 0 and exact output; no stack failure
occurs under the recorded limit. Native 8 MiB-case elapsed times are about
0.06 seconds. Very short GNU timer values round to hundredths; 0.00 does not
mean zero work.

The observations support bounded retention and diagnostics, memory depending
on the largest line/retained tail, and no per-record O(N) growth over the tested
range. No measured failure justified a production optimization or an additional
large-input follow-up. No absolute RSS threshold was selected after seeing data.

These are one-observation sequential warm-cache measurements in a shared VM,
with no CPU isolation, cache eviction or bare-metal throughput guarantee.
Some elapsed/system times vary substantially between cases, including tail 64;
the raw values are retained without assigning an unverified cause. RSS is a
whole-run maximum and does not locate its phase. Differences from macOS do not
by themselves identify allocator behavior, payload copies, or a language-level
memory improvement.

## Reproduce and remaining work

Use the [Docker instructions](../../tests/docker/README.md) and pinned
[Dockerfile](../../tests/docker/Dockerfile). The main measurement invocation is:

```sh
docker exec jlog-m4-linux-arm64 python3 tests/measure_resources.py \
  --binary /work/jlog-speed --work-dir /work/full
```

`--environment` can add a JSON file with the physical-host, engine/image and
execution provenance. Full fixtures and raw timing/diagnostic files remain in
the task container, outside the checkout; compact JSON is checked in with this
report. The container is stopped after export rather than leaving a background
measurement process running.

Native Linux x86-64 resource measurements and full M4-03 native CI remain open.
The strict descriptor suite still fails on both measured OS environments; no
expectation, platform or compiler pin was changed to hide that gap. No release,
push, or commit was performed during this Docker stage.

Subsequent [native CI](../plans/m4-03-native-ci.md) now supplies the required
[Linux x86-64 resource evidence](m4-02-linux-x86_64-ci.md). All 70 cases pass;
strict descriptor conformance remains failing. The Docker observations above
remain supplemental ARM64 evidence.
