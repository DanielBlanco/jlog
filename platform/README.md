# Pinned basic-cli platform

jlog uses basic-cli **0.25.0** with a small Unix descriptor-access correction.
Roc stays pinned to `nightly-2026-10-09-258ab27`. The user approved this dependency
change after the published platform's 15 descriptor cases failed and an isolated
patched host passed both optimization suites. See the
[investigation](../docs/repros/stdio-descriptor-errors.md).

[basic-cli.lock.json](basic-cli.lock.json) pins the upstream source commit/archive,
official platform archive, original/patched host source hashes, reviewed patch
and Rust **1.99.0**. [The patch](patches/stdio-access.patch) checks descriptor
access before Rust's standard streams can suppress `EBADF`; it preserves empty
writes, buffering and the hosted ABI. It uses the platform's existing libc
dependency. The application receives normal platform errors and maps them to
exit 3 with its existing code.

Prepare the native platform from the repository root:

```sh
rustup toolchain install 1.99.0 --profile minimal

# Linux x86-64 only (macOS uses its native toolchain):
# sudo apt-get update
# sudo apt-get install --yes musl-tools zstd
# rustup target add --toolchain 1.99.0 x86_64-unknown-linux-musl

python3 scripts/build_platform.py
```

Prerequisites are Python 3.9+, curl, Git, tar, Rust/rustup, and a native C
compiler. Linux additionally needs zstd and the native musl C/Rust target; the
Dockerfile configures ARM64's corresponding target automatically. First-time
downloads require network access. If an installed Rust alias already resolves
to exactly 1.99.0, it can be selected with `RUSTUP_TOOLCHAIN`; the bootstrap still
rejects any other version.

The bootstrap verifies archive and source hashes before applying the patch,
builds the host with `cargo build --locked --release --lib`, and replaces only
the selected native target's `libhost.a` in a copy of the published bundle. The
published Roc modules, Linux libc/unwind support files, upstream license and
third-party notices accompany that copy. There is no new runtime download or
Rust compiler requirement for the resulting executable.

Generated `basic-cli/` and `.cache/platform/` are ignored. The application imports
`platform/basic-cli/main.roc`; prepare the platform before invoking Roc commands.
Repeat the bootstrap to validate the input identity, target and every generated
file checksum. Changed or incomplete output is rebuilt from verified archives.
CI checks platform integrity before and after both build/test sequences.

`basic-cli/jlog-platform.json` records input identity, source/archive/patch hashes,
Rust compiler, Cargo.lock and every generated file's hash, including the native
host. CI artifacts retain it alongside test and resource results. Build paths
and host tooling can affect binary hashes; no cross-machine bit-for-bit claim
is made. Tests always execute the actual resulting binary.

These build and verification changes do not publish a platform fork or release.
