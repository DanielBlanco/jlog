# M4-02 resource measurements: native macOS ARM64

Recorded 2026-10-27 from application baseline `816f65c`, with no application
source changes. All **74 measured cases** passed exact output, status, diagnostic,
and input/binary hash checks. No measured retention/scaling or stack failure
requires a production change. This evidence covers this native host; native
Linux x86-64 measurements and strict descriptor failures remain release gates.
Supplemental [Linux ARM64 Docker results](m4-02-linux-arm64-docker.md) are now
recorded separately.

## Host and artifact

- Apple M1 Pro, MacBookPro18,1, 32 GiB physical RAM.
- macOS 27.0.1 (26A434), native ARM64; stack soft limit 8,176 KiB.
- Roc `nightly-2026-10-09-258ab27`; basic-cli 0.25.0 at the existing pin.
- Optimized `dist/jlog`, built with `roc build --opt=speed --output=dist/jlog src/main.roc`.
- Executable SHA-256: `0bf01d6835fa99f8dec215c922be8bd8f68601653dae1a0a326a01cb24c6ed77`.

The [JSON artifact](m4-02-macos-arm64.json) preserves every command, fixture size,
maximum body length, N, native elapsed/user/system time, peak RSS, exit status,
output sizes/hashes, input hashes, host metadata, and driver identity. Paths to
generated inputs and raw timing logs are machine-local; large fixtures/stdout
are not checked in. The tested executable remains in ignored `dist/`.

## Method

[The Python standard-library driver](../../tests/measure_resources.py) generates
known fixture templates, runs the actual binary sequentially, and uses native
`/usr/bin/time -l`. Its maximum resident set size is in bytes; tables convert it
to MiB (1,048,576 bytes). RSS and CPU cover the target process, excluding the
Python parent, fixture generation, and subsequent hashing. Stdout goes to a real
file, is verified, then removed. Stderr and raw timing text are retained.

The default matrix has 70 cases, one observation per case:

| Fixture | Records | Input bytes | Maximum body bytes | Expected result |
| --- | ---: | ---: | ---: | --- |
| Valid, short records | 100,000 | 102,400,000 | 1,023 | Exit 0; count 100,000; filter selects 50,000 original records. |
| Valid, short records | 1,000,000 | 1,024,000,000 | 1,023 | Exit 0; count 1,000,000; filter selects 500,000 original records. |
| All invalid | 100,000 | 102,400,000 | 1,023 | Exit 4; zero valid records; 100 details plus 99,900 omitted. |
| All invalid | 1,000,000 | 1,024,000,000 | 1,023 | Exit 4; zero valid records; 100 details plus 999,900 omitted. |
| One long record | 1 | 1,048,577 | 1,048,576 | Exit 0; original body plus LF from tail/filter. |
| One long record | 1 | 8,388,609 | 8,388,608 | Exit 0; original body plus LF from tail/filter. |
| Maximum N, tiny input | 2 | 2,048 | 1,023 | Tail N=4,294,967,295 emits exactly two original records; exit 0. |

Valid records have a unique sequence string, alternating `failed`/`passed`
status, and ASCII padding. Golden byte counts/hashes come from those known
templates; the driver does not parse arbitrary JSON, implement a framer, or
maintain a reference tail ring. This checks eviction/order as well as selection.
All-invalid records deliberately start with `!`; diagnostics are specified
independently with the first-100 cap and omitted count.

Every fixture runs from both a file argument and redirected stdin. Valid short
records exercise inspect/count/filter and tail N=0/1/64/4096/16384; invalid
records exercise inspect/count/filter and tail N=0/16384. Long records exercise
all four modes, with tail N=1. No input or binary hash changed.

Two initial file-inspection cases were repeated because their elapsed times
contained about two seconds beyond measured CPU. Two additional tail cases used
4,000,000 records (4,096,000,000 bytes) at fixed N=16,384 to investigate RSS
variation. Those follow-ups are retained alongside the original observations;
no outlier was silently discarded. Two 62-case small-fixture runs verified the
driver before the baseline and after adding targeted case selection.

## Short-record results

Native file-input measurements; time is native elapsed seconds, RSS is MiB.
Detailed redirected-stdin results are in the JSON artifact.

| Mode | 100,000 time | 100,000 RSS | 1,000,000 time | 1,000,000 RSS |
| --- | ---: | ---: | ---: | ---: |
| Inspect | 2.85 | 2.92 | 9.03 | 2.89 |
| Count | 0.69 | 2.83 | 6.84 | 2.83 |
| Filter | 1.73 | 3.25 | 16.77 | 3.25 |
| Tail 0 | 0.73 | 2.84 | 6.91 | 2.80 |
| Tail 1 | 0.75 | 2.89 | 6.92 | 2.84 |
| Tail 64 | 0.70 | 3.70 | 6.94 | 3.72 |
| Tail 4096 | 0.78 | 38.02 | 7.19 | 44.73 |
| Tail 16384 | 0.98 | 68.92 | 7.36 | 101.95 |

For redirected stdin, inspect/count/filter peak RSS is 2.89–3.41 MiB on the
1,000,000-record input, versus 2.92–3.38 MiB on 100,000 records. Filter output is
512,000,000 bytes in the larger case, with its exact expected hash. These samples
show no accumulation of input or emitted matches in those modes.

The file-inspection repeats were 2.73 and 6.85 seconds, with RSS 2.52 and
2.78 MiB. Initial inspect user+system CPU was 0.70 and 6.89 seconds; repeat CPU
was 0.67 and 6.83 seconds. The elapsed/CPU discrepancy is retained without
assigning an unverified cause. It does not justify a generic throughput claim.

At 1,000,000 records, file-tail user CPU is 6.71 seconds for N=64 and 6.85 seconds
for N=16,384. Increasing retained slots 256-fold does not produce corresponding
per-record work growth in these observations. Output bytes also increase with N.

Tail RSS includes substantially more than retained payload bytes and varies
between processes. The fixed-N follow-up checks that this variation does not
simply track total input size:

| Records, N=16,384 | File RSS | Stdin RSS | File time | Stdin time |
| --- | ---: | ---: | ---: | ---: |
| 100,000 | 68.92 | 76.94 | 0.98 | 0.92 |
| 1,000,000 | 101.95 | 78.75 | 7.36 | 7.10 |
| 4,000,000 | 92.66 | 99.41 | 30.77 | 27.34 |

The 40-fold input increase does not produce proportional RSS growth; the later
file measurement is below the earlier maximum. This supports bounded retention
over the measured range, without identifying allocator behavior as the cause
or promising an absolute memory ceiling. The maximum-N/tiny-input cases peak at
1.95 MiB (file) and 1.91 MiB (stdin), without N-sized preallocation.

## Long lines and invalid input

RSS ranges across inspect/count/filter/tail 1:

| Body size | File RSS | Stdin RSS |
| --- | ---: | ---: |
| 1 MiB | 5.19–5.28 MiB | 3.13–3.20 MiB |
| 8 MiB | 31.05–31.30 MiB | 14.83–15.08 MiB |

Every 8 MiB case completes with status 0 and correct output. Memory increases
with the largest line, with no stack failure under the recorded stack limit.
This does not establish an arbitrary-line-size guarantee. Native times for the
8 MiB cases are 0.05–0.06 seconds; the timer prints hundredths, so very short
reported times (including 0.00) must not be interpreted as zero execution time.

All-invalid peak RSS is 2.66–2.91 MiB at 100,000 records and 2.80–3.02 MiB at
1,000,000 records across both sources and the measured modes. Counts, exactly
100 details, omitted counts, empty tail/filter output, and exit 4 are verified.
There is no observed unbounded diagnostic retention.

## Follow-up: record sharing and the phase of the RSS peak

The whole-run `time -l` measurements above do not identify when their maximum
occurred. A subsequent gated probe addresses that question without modifying
or rebuilding the executable. Its [four-trial summary](m4-02-tail-phases.json)
preserves exact RSS values, per-child final `wait4` maximum RSS, output hashes,
probe identity, and the input/binary hashes.

The probe sends 100,000 or 1,000,000 of the existing 1,024-byte records with
tail N=16,384. It keeps the input writer open after the byte queue drains,
waits 0.5 seconds, and confirms stdout is still empty. It reads current and
lifetime-maximum RSS through the SDK's `MACH_TASK_BASIC_INFO` fields. Then it
closes input, leaves stdout unread until output blocks, and measures again
before draining/verifying all 16 MiB of tail output. Final `wait4.ru_maxrss`
captures the exact per-child whole-run maximum, including exit.

Representative 1,000,000-record results, MiB:

| Transport in the phase probe | Pre-EOF current RSS | Pre-EOF high-water RSS | Output-blocked current RSS | Final maximum RSS |
| --- | ---: | ---: | ---: | ---: |
| Stdin pipe | 88.66 | 88.66 | 89.14 | 89.14 |
| Named pipe through `File.Reader` | 75.14 | 76.61 | 75.59 | 76.61 |

Most resident memory is already present before EOF. For stdin the exact maximum
occurs after EOF, with an increase of about 0.48 MiB. For the file-reader probe
the maximum is reached during processing and does not increase during output.
The 100,000-record trials show the same distinction: stdin grows from a 62.58
MiB pre-EOF maximum to 63.08 MiB final maximum; the file-reader maximum remains
56.52 MiB. These are additional controlled pipe/FIFO runs, not phase timestamps
for the original regular-file measurements.

The pinned compiler's
[list runtime](https://github.com/roc-lang/roc/blob/258ab27f79bef726d501e3b79ce2e47e54e83f9d/src/builtins/list.zig#L1954)
updates a unique outer list directly; a shared list goes through `makeUnique`.
That fallback copies outer element representations and increments nested
reference counts. For this `List(List(U8))` ring, those elements are three-word
byte-list descriptors, whose underlying record bytes remain shared. `listSet`
releases the displaced element. Sharing can keep an old allocation alive, but
this is not a recursive payload clone on every replacement.

`tail_lines` can allocate an ordered outer list at EOF. One complete array of
16,384 descriptors occupies 384 KiB on ARM64; this scale is consistent with the
small observed output increase, but does not prove the exact allocation cause.
The writer sends bodies individually rather than building one combined payload.
The remaining RSS overhead is not explained by this experiment: resident pages
and spare capacity are not counts of live record copies. Determining their exact
contribution would require allocation-level profiling.

## Reproduce and interpret

From the repository root after building the pinned optimized executable:

```sh
python3 tests/measure_resources.py --binary dist/jlog
python3 tests/measure_resources.py --binary dist/jlog --sizes 100000 1000000 --cases 'valid-*-file-inspect'
python3 tests/measure_resources.py --binary dist/jlog --sizes 4000000 --cases 'valid-*-tail-16384'
```

Each command uses a fresh temporary directory. The default matrix needs about
3 GiB of available disk space; the 4,000,000-record follow-up needs about 4 GiB.
The sandbox used for development blocks the timing tool's `kern.clockrate`
query; these measurements used explicitly approved execution outside that
sandbox. A `/usr/bin/time -l /usr/bin/true` control confirmed the tool works.

Runs are sequential, with no cache eviction, CPU isolation, or statistical
throughput guarantee. They use one host, synthetic ASCII payloads, regular-file
stdout, and redirected-file stdin rather than a live producer. Timings include
OS scheduling/I/O effects. No absolute RSS threshold was invented after seeing
the results, and no speculative tuning was introduced.

The native macOS part of M4-02 is recorded, followed by supplemental native ARM64
guest measurements on Linux. The current driver also supports GNU `time -v`;
the original driver identity is preserved in this artifact. Native Linux x86-64
execution is still needed. M4-01's strict
descriptor suite remains failing, so these resource checks do not establish
release readiness. Native CI, installation/packaging, licenses/notices and OS
support remain later tasks. No application/platform/FFI/pin change or release
publication was made.

Subsequent [native CI](../plans/m4-03-native-ci.md) now executes both required
architectures, including the [Linux x86-64 matrix](m4-02-linux-x86_64-ci.md) and
a [second macOS matrix](m4-02-macos-arm64-ci.json). Each passes all 70 cases;
the original macOS results above remain unchanged. Strict descriptor conformance
continues to fail on both native CI targets.
