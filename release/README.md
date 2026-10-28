# Release archive preparation

M4-05 prepares macOS ARM64 and Linux x86-64 archives from the **already tested**
optimized executable. It does not rebuild the application or publish a release.
The project uses the approved root [MIT license](../LICENSE).
The [support policy](SUPPORT.md) records the verified native baselines and limits.
The final release-set tool checks both native artifacts before creating a manifest.

Use a native verification output directory containing `jlog-speed`,
`environment.json` and `verification.json` (see [native CI](../tests/ci/README.md)).
The packager requires passing checks for both builds, including every strict
descriptor suite; it verifies the source, compiler, platform and binary hashes.
Downloaded GitHub ZIP files can lose executable permission bits. The archive
sets `bin/jlog` to 0755 while preserving the tested bytes.

```sh
python3 scripts/package_release.py \
  --evidence /tmp/jlog-native-evidence \
  --output dist/release
```

Outputs are `jlog-0.1.0-{macos-arm64,linux-x86_64}.tar.gz` and the matching
`.tar.gz.sha256`, one pair for the supplied native target. The output archive
must not already exist. Sorted entries, zero timestamps, numeric owners and a
fixed gzip header make repeated packaging of identical inputs deterministic on
the same packaging toolchain. This is not a claim about reproducible compilation.

Each archive contains only `bin/jlog`, the project license, bundled installation
instructions, support policy, third-party notices, complete upstream license documents and
`BUILD.json`. That per-archive manifest preserves the tested source/CI/platform
identity, binary hash and bundled file inventory. Compiler/cache/large fixture
data and development executables are excluded. SHA-256 detects corruption;
checksums are not signatures or independent proof of origin.

Run the smoke test on the archive's native OS/architecture, as an ordinary user:

```sh
python3 tests/verify_release.py \
  --archive dist/release/jlog-0.1.0-macos-arm64.tar.gz \
  --report /tmp/jlog-release-smoke.json
```

On Linux substitute `linux-x86_64`; Docker must be available. The verifier checks
the external checksum, exact archive inventory, every bundled hash and executable
permissions. It executes the bundled installation block in a fresh temporary
directory and a prefix containing spaces. Eight runtime checks cover help,
version, inspection, count, tail, original-byte filtering, a real filter→count
pipeline and empty stdin. A fixture containing CRLF, UTF-8, an unbounded JSON
exponent and a final unterminated record is read-only; fixture, binary and archive
hashes must remain unchanged.

- **Linux x86-64:** a locally built `FROM scratch` image contains only the
  installed static executable and fixture. It has no Roc, Rust, shell or language
  runtime. Every execution uses UID 65534, a read-only filesystem, dropped
  capabilities and `--network=none`. Building this image needs no base-image pull.
- **macOS ARM64:** `sandbox-exec` denies all network access and execution of
  `roc`, `rustc` or `cargo`, including absolute paths. The runtime PATH contains
  only the installed executable and the source checkout is inaccessible. A
  socket probe verifies network denial and a shell probe verifies toolchain
  absence from PATH. Compilers remain installed on the host but are unavailable
  to the tested process. Applying this sandbox requires running outside any
  enclosing sandbox that forbids `sandbox_apply`.

Installation uses local checksum/tar/install commands; runtime checks execute
inside the network-denying boundaries. The JSON report records this distinction,
commands, statuses, hashes, native environment and isolation method. A successful
smoke test never substitutes for full native acceptance/resource evidence.

## Notice provenance

[`notices.json`](notices.json) pins the original notice file hashes, Cargo.lock
hash and 87 crate identities. The crate inventory is the conservative union of
`cargo metadata --locked --filter-platform` for `aarch64-apple-darwin` and
`x86_64-unknown-linux-musl`. Each downloaded `.crate` was SHA-256 checked against
the pinned Cargo.lock before copying all LICENSE/COPYING/NOTICE/COPYRIGHT files.
The checked-in text retains original paths and full notices, including build
dependencies and code the linker may discard. The platform, compiler and Rust
standard-library documents come from the exact pinned releases described in the
inventory. No runtime license retrieval or packaging dependency is introduced.

When a compiler/platform/dependency pin changes, recollect notices from those
verified sources and review the inventory before replacing its hashes. The
packager refuses a mismatched Cargo.lock or changed notice file. The
[M4-06 audit](../docs/plans/m4-06-release-audit.md) records the final review
separately from this mechanical collection.

## Finalize both verified native archives

Download and extract the two artifacts from the same passing native CI run.
Pass their roots, each containing `evidence/`, `measurements/` and `release/`,
to the finalizer:

```sh
python3 scripts/finalize_release.py \
  --artifacts /tmp/native-macos-arm64 /tmp/native-linux-x86_64 \
  --output dist/jlog-0.1.0-release
```

The output directory must be new. The finalizer rechecks full native test,
README, resource and offline archive results; hashes; current source/platform
pins; and the bundled license, notices, support and installation documents.
It rejects missing/duplicate targets, failed smoke checks and differing shared
release inputs. It copies the exact tested archives/checksum sidecars and writes
`manifest.json` plus `SHA256SUMS` (archives and manifest). No rebuild occurs.
Publication, tagging and merging remain separate actions.
