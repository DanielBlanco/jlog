# Third-party notices for jlog 0.1.0

jlog's project license is in `LICENSE`. Dependencies retain their own terms.
The archive includes the following unabridged upstream documents in `licenses/`:

| File | Origin |
| --- | --- |
| `basic-cli-LICENSE.txt` | basic-cli 0.25.0 source, commit `6e787d231017e9888027330de5d651f388e807fd`; UPL 1.0. |
| `basic-cli-THIRD-PARTY.md` | Published 0.25.0 bundle's notices, including musl and LLVM libunwind. |
| `roc-LICENSE.txt`, `roc-legal-details.txt` | Official Roc `nightly-2026-10-09-258ab27` compiler archive. The compiler itself is not distributed here. |
| `rust-COPYRIGHT-library.html` | Rust 1.99.0 standard-library copyright and license inventory. The Rust compiler is not distributed here. |
| `host-crates.txt` | License/notice files from 87 checksum-verified crates in the pinned host's macOS ARM64/Linux x86-64 dependency graphs. |

The inventory conservatively includes build dependencies and code that the
linker can discard. Inclusion does not mean every listed component is linked
into each executable. Linux includes static libc support; macOS uses its system
library. `BUILD.json` records the native target, upstream identities and notice
hashes. The repository's `release/notices.json` records each crate checksum and
the original notice paths/hashes; the same inventory accompanies the archive.

jlog changes basic-cli's Unix standard-descriptor access handling before calling
Rust standard streams. This preserves `EBADF` errors that upstream 0.25.0 can
suppress. The corrected source is built with Rust 1.99.0; its original/patched
source checksums and patch checksum are pinned in `platform/basic-cli.lock.json`.
The patch is available in the jlog source at `platform/patches/stdio-access.patch`.

Sources: <https://github.com/DanielBlanco/jlog>,
<https://github.com/roc-lang/basic-cli>, <https://github.com/roc-lang/roc>,
<https://github.com/rust-lang/rust/tree/1.99.0> and the crates.io packages named
in `BUILD.json`. No runtime download is needed to read these notices or run jlog.
