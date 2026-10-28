# Install jlog 0.1.0

Use `jlog-0.1.0-macos-arm64.tar.gz` on macOS ARM64 or
`jlog-0.1.0-linux-x86_64.tar.gz` on Linux x86-64. Download the matching `.sha256`
file alongside it. The checksum detects damaged downloads; obtain both files
from the same trusted [v0.1.0 release](https://github.com/DanielBlanco/jlog/releases/tag/v0.1.0).

In Bash or zsh, set `JLOG_ARCHIVE` to the archive filename in the current
directory, then run:

```sh
if command -v sha256sum >/dev/null; then
  sha256sum -c "$JLOG_ARCHIVE.sha256"
else
  shasum -a 256 -c "$JLOG_ARCHIVE.sha256"
fi
tar -xzf "$JLOG_ARCHIVE"
JLOG_DIRECTORY="${JLOG_ARCHIVE%.tar.gz}"
JLOG_INSTALL_PREFIX="${JLOG_INSTALL_PREFIX:-$HOME/.local}"
mkdir -p "$JLOG_INSTALL_PREFIX/bin"
install -m 755 "$JLOG_DIRECTORY/bin/jlog" "$JLOG_INSTALL_PREFIX/bin/jlog"
export PATH="$JLOG_INSTALL_PREFIX/bin:$PATH"
jlog --version
```

Expected version: `jlog 0.1.0`. Keep `LICENSE`, `THIRD_PARTY_NOTICES.md` and the
`licenses/` directory with redistributed copies. `BUILD.json` identifies the
tested optimized binary, source, compiler, corrected platform and bundled files.

The installed executable runs offline without Roc, Rust or another language
runtime. It reads one JSONL file or stdin and leaves inputs unchanged:

```sh
jlog --help
jlog events.jsonl
set -o pipefail
jlog --where status=failed events.jsonl | jlog --count
```

Exit codes: 0 success, 1 internal error, 2 usage error, 3 I/O error, 4 malformed
records. Filtering can emit valid matches before later malformed records or I/O
errors; check the pipeline status. A failed write can leave truncated output.
Normal OS signal termination follows the shell's signal conventions.

The native verification reports record tested OS versions. Support is limited
to the tested configurations in `SUPPORT.md`: macOS
15.7.9 ARM64 (also tested on 27.0.1) and Ubuntu 24.04.5 x86-64. Other OS
versions/distributions are unverified.
