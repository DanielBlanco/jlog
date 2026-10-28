# jlog 0.1.0

First release of jlog, a small JSONL/NDJSON explorer written in Roc.

- Inspect and validate a file or stdin, with physical line numbers and capped diagnostics.
- Count valid records with `--count` and retain the last N valid records with bounded `--tail N` storage.
- Stream top-level string matches with `--where KEY=TEXT`, preserving original record bodies and numeric spellings.
- Show opt-in inspection progress on stderr with `--progress`.
- Process input incrementally, leave input files unchanged and run offline without Roc or Rust installed.

## Downloads and installation

Choose `jlog-0.1.0-macos-arm64.tar.gz` for macOS ARM64 or
`jlog-0.1.0-linux-x86_64.tar.gz` for Linux x86-64. Download its `.sha256` sidecar
and follow `INSTALL.md` inside the archive, or read the
[installation guide](https://github.com/DanielBlanco/jlog/blob/v0.1.0/release/INSTALL.md).
The release also includes a provenance manifest and combined `SHA256SUMS`.

Verified baselines: macOS 15.7.9 ARM64 (also tested on 27.0.1) and Ubuntu
24.04.5 x86-64 on the recorded native CI kernel. See the
[support policy](https://github.com/DanielBlanco/jlog/blob/v0.1.0/release/SUPPORT.md)
for platform limits. Native acceptance, strict I/O, resource and offline archive
checks pass on both release targets.

Exit codes: 0 success, 1 internal error, 2 usage error, 3 I/O error, 4 malformed
records. Use `pipefail` when piping filtered output into another command;
filtering can emit a valid prefix before a later error.

`--field`, nested queries, follow mode and a TUI are outside v0.1. Project code
is MIT licensed; complete third-party notices accompany both archives.
