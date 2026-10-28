# M4-05 archive preparation and offline verification

Authorized 2026-10-27 by the user's request to start the next task after M4-04.
Implementation is prepared; **M4-05 is not yet complete**. The user subsequently
approved the proposed MIT license, now applied in root `LICENSE`. Actual native
release-candidate CI execution remains pending. No public release is published.

## Packaging and regression gates

[`scripts/package_release.py`](../../scripts/package_release.py) reuses the
verified optimized binary. It requires passing native checks for both build
modes, including strict descriptor suites, and matches application sources,
compiler/platform identities, binary hash and architecture. It verifies the
notice inventory and Cargo.lock identity. It never rebuilds the executable.

Archives contain 11 regular files: the executable (0755), project license,
installation instructions, third-party notice index, six full notice documents
and per-archive build manifest. Packaging writes a SHA-256 sidecar and uses
deterministic entry metadata/gzip headers. Before MIT was approved, creating
distributable candidates stopped at the missing root `LICENSE`, as intended.
That prerequisite is now resolved.

Five release tooling methods verify that failed/missing strict results, changed
sources/binaries/architecture, a corrupted archive, lost executable permissions
or a missing license are rejected. Full Python discovery passes **77 methods**
against the existing corrected local binary, including all descriptor subcases.
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
`/private/tmp/jlog-m405-*`. No Linux native archive smoke result is claimed.

## Pending completion

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
Remaining archive work:

1. Execute the complete native CI/archive sequence on both release targets.
2. Download/check those CI archives and retain their final checksums, native smoke results
   and provenance; record M4-05 completion.

The workflow changes have not been pushed as part of the requested local commit
checkpoint. M4-06 ownership/notices/final audit and release publication remain
separate tasks.
