# M4-05 archive preparation and offline verification

Authorized 2026-10-27 by the user's request to start the next task after M4-04.
**M4-05 is complete.** Final native run
[40608149721](https://github.com/DanielBlanco/jlog/actions/runs/40608149721)
passes both release targets, including offline archive verification. MIT is
applied in root `LICENSE`. The preparation history below precedes the final
completion record at the end. Subsequent publication is recorded in the
[v0.1.0 publication record](../verification/jlog-0.1.0-publication.json);
archive identities below retain the pre-publication checkpoint.

## Packaging and regression gates

[`scripts/package_release.py`](../../scripts/package_release.py) reuses the
verified optimized binary. It requires passing native checks for both build
modes, including strict descriptor suites, and matches application sources,
compiler/platform identities, binary hash and architecture. It verifies the
notice inventory and Cargo.lock identity. It never rebuilds the executable.

Final archives contain 12 regular files: the executable (0755), project license,
installation instructions, support policy, third-party notice index, six full notice documents
and per-archive build manifest. Packaging writes a SHA-256 sidecar and uses
deterministic entry metadata/gzip headers. Before MIT was approved, creating
distributable candidates stopped at the missing root `LICENSE`, as intended.
That prerequisite is now resolved.

Five release tooling methods verify that failed/missing strict results, changed
sources/binaries/architecture, a corrupted archive, lost executable permissions
or a missing license are rejected. Initial full Python discovery passes **77 methods**
against the corrected local binary, including all descriptor subcases. The final
release-set tool adds three methods, for **80** in the completed sequence.
Roc check/format, Python 3.9 syntax/docstrings, notice integrity and actionlint
pass. Application code, platform patch/bootstrap and compiler pin are unchanged.

## Notice provenance

[`release/notices.json`](../../release/notices.json) records all original notice
hashes and 87 crates from the union of native macOS ARM64/Linux x86-64 Cargo
graphs. Every `.crate` checksum matches the original pinned Cargo.lock before
copying its LICENSE/COPYING/NOTICE/COPYRIGHT files. This conservative collection
includes build-only dependencies and code the linker can discard.

The basic-cli UPL and published third-party notices, Roc UPL/legal details and
Rust 1.99.0 standard-library copyright inventory are included verbatim. Roc's
documents were independently compared with the official compiler archive whose
SHA-256 is `aa6339579730fcea4753940bec21f5d8cf8be8e25659ec001abccbc3463a60b2`.
The final M4-06 dependency/license review remains separate from this collection.

## Private fixture archive checks

To verify the harness while leaving the project license unchanged, private
fixture source directories outside the checkout contain this explicit marker:

> TEST FIXTURE ONLY: project license choice is pending. Not for distribution.

These are **test fixtures**, not release candidates. Their executables are the
unaltered optimized binaries from M4-04 native run 40571638408:

| Target | Binary SHA-256 | Fixture archive size |
| --- | --- | --- |
| macOS ARM64 | `c43bbc634256da04ef0123a1f1defd5df6580c54f72299760a5a7a51dfe240c1` | 349,003 bytes |
| Linux x86-64 | `9b8271f8771b3686311504e172f96ef66bbc60a0b0dc57350efc969608a2ac14` | 1,621,782 bytes |

Both fixture archives reproduce byte-for-byte in a second packaging directory.
Native macOS 27.0.1 ARM64 passes bundled installation and all eight runtime cases:
help, version, inspection, count, tail, byte-preserving filtering, a real
filter→count pipeline and empty stdin. The read-only CRLF/UTF-8/unterminated
fixture and executable/archive hashes remain unchanged. A socket probe confirms
network denial; no compiler is on the runtime PATH and absolute compiler
execution is denied. The initial harness assumed a particular `command -v`
failure status; it now uses an explicit conditional, and the corrected harness
passes. This was a harness issue, not application RED.

The [durable summary](../verification/m4-05-preparation-macos-arm64.json) records
these private-fixture results. Raw reports/fixtures remain under
`/private/tmp/jlog-m405-*`. At that fixture checkpoint, no Linux native archive
smoke result was claimed; the final native result follows below.

## Initial MIT candidate checkpoint

After MIT approval, both actual candidates package successfully from the tested
M4-04 binaries. The macOS MIT archive passes installation and all eight local
offline runtime checks; input, executable and archive integrity pass. The
[MIT candidate report](../verification/m4-05-mit-macos-arm64-local.json) preserves
the actual license hash, case results and both archive identities:

| Candidate | Archive SHA-256 |
| --- | --- |
| `jlog-0.1.0-macos-arm64.tar.gz` | `ddc8a23babfb21832b372641d69bca31515c504cfa516f91dc5e0c9cd8014214` |
| `jlog-0.1.0-linux-x86_64.tar.gz` | `d77962cbf420811056b449204d1913d6260c271bae829e6aa9d37ccd95c2ca4d` |

Generated archives and sidecar checksums live in ignored `dist/release/`; their
source tooling, approved license, notices and durable evidence are committed.

The workflow is prepared to package only after full native verification, README
checks and resource measurements succeed. Linux runtime checks use a local
`FROM scratch` image with no compiler/shell/runtime and `--network=none`.
macOS runtime checks deny network/toolchain access with `sandbox-exec`. Local
installation uses the bundled checksum/tar/install commands; runtime checks
then execute within those isolation boundaries. See the
[maintainer instructions](../../release/README.md) for exact commands and scope.

The user approved the proposed [MIT license](../../LICENSE), including
`Copyright (c) 2026 Daniel Blanco`, while requesting a clean commit checkpoint.
The checkpoint's remaining archive work, completed below:

1. Execute the complete native CI/archive sequence on both release targets.
2. Download/check those CI archives and retain their final checksums, native smoke results
   and provenance; record M4-05 completion.

The workflow changes were not pushed as part of that requested local commit
checkpoint. The subsequent wrap-up request authorizes finishing M4-05/06.

## Final native completion

Code commit `7f92f8c079ff3ccfed13fd2d977e2eda252420af` passes both
[PR run 40608149721](https://github.com/DanielBlanco/jlog/actions/runs/40608149721)
and [push run 40608143058](https://github.com/DanielBlanco/jlog/actions/runs/40608143058).
The final artifacts use PR merge checkout
`26081f3f4d9926fe8e3b519d16e1a766264c921a`; current application hashes match.

| Final native verification | macOS ARM64 | Linux x86-64 |
| --- | --- | --- |
| Pure tests, dev/speed | 486 per build pass | 486 per build pass |
| Ordinary executable tests, dev/speed | 64 per build pass | 64 per build pass |
| Strict descriptors, dev/speed | All 15 subcases per build pass | All 15 subcases per build pass |
| Tooling unit methods | All 13 pass | All 13 pass |
| README usage/install and source blocks | 19 cases and five blocks pass | 16 cases and five blocks pass |
| Resource matrix | 70/70 pass | 70/70 pass |
| Offline archive cases | 8/8 pass | 8/8 pass |

Linux executes the installed static binary in a `FROM scratch` image with no
compiler, shell or language runtime, UID 65534, a read-only filesystem and
`--network=none`. macOS denies network and compiler execution through the runtime
sandbox; its socket-denial probe passes. Installation and raw-record pipelines
pass; fixture, executable and archive hashes remain unchanged.

Downloaded native ZIP hashes match GitHub metadata. The finalizer revalidates
both real artifacts, every archive entry/hash/mode, all required evidence and
matching shared release inputs. Additional checks on a copied real artifact
reject failed smoke status, an incorrect archive hash and a missing smoke case.
No second executable build is used. Both binary hashes match earlier corrected
CI builds exactly.

The exact finalized release set lives in ignored `dist/jlog-0.1.0-release/`:

| Archive | SHA-256 |
| --- | --- |
| `jlog-0.1.0-macos-arm64.tar.gz` | `8c2ad5de5aaa4b31e418536252d8dde2f6dd07738cbef781e68d53d8ae18de35` |
| `jlog-0.1.0-linux-x86_64.tar.gz` | `0e88e9fda6fb585157910c167d3ff4ce487edfa2fddbccd6cd078f89b7822f6a` |

`SHA256SUMS` verifies both archives and `manifest.json`. Durable
[native evidence](../verification/m4-05-native-archives.json),
[manifest](../verification/jlog-0.1.0-release-manifest.json) and
[checksums](../verification/jlog-0.1.0-SHA256SUMS) preserve the final identities.
Raw ZIPs/extracted results remain under `/private/tmp/jlog-closeout-*`;
GitHub artifacts expire 2026-11-11. See the [final audit](m4-06-release-audit.md).
