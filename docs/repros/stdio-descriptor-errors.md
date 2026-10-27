# Standard descriptor errors hidden by the pinned platform

**Current status:** the approved host correction passes both required native
CI jobs. See the [execution report](../plans/m4-03-stdio-correction.md).
The reproducer below deliberately retains the original published platform.

Rechecked on 2026-10-27, native macOS ARM64, Roc
`nightly-2026-10-09-258ab27` and basic-cli 0.25.0. These are known release
blockers under the existing exit-3 contract, not newly accepted behavior.

## Application-level acceptance

Build jlog, then run the strict descriptor suite:

```sh
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_io_contract.py' -v
```

[The tests](../../tests/test_io_contract.py) first confirm `EBADF` through Python
OS calls on the same descriptor. They then pass that descriptor to the actual
binary and require exit 3. They have no skips or expected-failure markers.

| Fixture | Required | Observed on this host |
| --- | --- | --- |
| Write-only stdin, four input modes | Exit 3, no completed result. | Exit 0; inspection/count behave as empty input, tail/filter emit nothing. |
| Read-only stdout, help/version and four input modes | Exit 3. | Exit 0 despite discarded output. |
| Read-only stderr, usage/progress/data diagnostics | Exit 3. | Original status 2/0/4; the write failure is hidden. |

All three methods fail: **15 failing subcases**. Actual closed-reader pipe
errors and directory-stdin read errors pass in `test_cli.py`; those fixtures
exercise different errors and do not establish descriptor conformance.

## Independent platform probe

This probe contains no application parser, counters, or exit policy. It exposes
the result of a single platform call through the other, healthy output stream.
Save as `/private/tmp/DescriptorProbe.roc` and build with the same pinned compiler
and a writable cache:

```roc
app [main!] { pf: platform "https://github.com/roc-lang/basic-cli/releases/download/0.25.0/CZsY7tYZwR3rj9kYbpaCfxki2yVAaRL8bBwMLvB2xkbA.tar.zst" }

import pf.OsStr
import pf.Stdin
import pf.Stdout
import pf.Stderr
import pf.IOErr

## Expose one platform result through the other, healthy output descriptor.
main! : List(OsStr) => Try({}, [Exit(I32)])
main! = |args| match args.map(|arg| arg.display()) {
    ["read"] => {
        result = match Stdin.bytes!() {
            Ok(bytes) => "Ok(${bytes.len().to_str()} bytes)"
            Err(EndOfFile) => "Err(EndOfFile)"
            Err(StdinErr(err)) => "Err(${IOErr.to_str(err)})"
        }
        Stdout.line!(result).map_err(|_| Exit(3))
    }
    ["stdout"] => {
        result = match Stdout.write!("probe\n") {
            Ok({}) => "Ok({})"
            Err(StdoutErr(err)) => "Err(${IOErr.to_str(err)})"
        }
        Stderr.line!(result).map_err(|_| Exit(3))
    }
    ["stderr"] => {
        result = match Stderr.write!("probe\n") {
            Ok({}) => "Ok({})"
            Err(StderrErr(err)) => "Err(${IOErr.to_str(err)})"
        }
        Stdout.line!(result).map_err(|_| Exit(3))
    }
    _ => Err(Exit(2))
}
```

```sh
roc build --opt=dev --output=/private/tmp/descriptor-probe /private/tmp/DescriptorProbe.roc
```

```python
import os, subprocess

binary = "/private/tmp/descriptor-probe"
read_fd, write_fd = os.pipe()
try:
    result = subprocess.run([binary, "read"], stdin=write_fd,
                            capture_output=True, timeout=5)
    print(result.stdout)  # b"Err(EndOfFile)\n"
finally:
    os.close(read_fd)
    os.close(write_fd)

for stream in ("stdout", "stderr"):
    descriptor = os.open(os.devnull, os.O_RDONLY)
    try:
        healthy = "stderr" if stream == "stdout" else "stdout"
        result = subprocess.run([binary, stream],
                                **{stream: descriptor, healthy: subprocess.PIPE},
                                timeout=5)
        print(getattr(result, healthy))  # b"Ok({})\n"
    finally:
        os.close(descriptor)
```

The independent probe freshly built without errors/warnings and produced these
three results. The application cannot distinguish those returned values from
real EOF or successful writes.

Inspection of the cached pinned `Stdin.roc`, `Stdout.roc`, `Stderr.roc`,
`File.roc`, and hosted interfaces found no public standard-descriptor validation
or explicit flush API. Whole-input reading, text decoding, terminal raw-mode
changes, and opening OS-specific descriptor paths are not suitable portable
substitutes for incremental byte I/O. No platform, FFI, dependency, contract, or
pin change was made. A platform correction needs its own tested change; these
acceptance assertions should become green without changing their expected exit.

## Root cause and isolated correction (2026-10-27)

The reported GitHub failure is reproduced locally with the unchanged published
platform: the same 15 subcases fail. The 0.25.0 Rust host at release commit
`6e787d231017e9888027330de5d651f388e807fd` uses Rust's standard stream locks in
`hosted_stdin_*`, `hosted_stdout_*` and `hosted_stderr_*`.
[Rust's standard stream implementation](https://doc.rust-lang.org/src/std/io/stdio.rs.html)
explicitly handles `EBADF` as a successful zero-byte read or successful write.
This explains why jlog's existing error mapping receives EOF/success instead of
the operating-system error. Flushing again cannot recover the hidden error.

An isolated upgrade experiment uses the published basic-cli 0.26.0 archive and
its minimum compiler `nightly-2026-10-12-2664a27`. Only the temporary copy is
adapted for the new raw-file-read, EOF and monotonic-clock APIs. Its check and
961 inline checks pass, but all 15 descriptor subcases still fail. The
[0.26 native Unix backend](https://github.com/roc-lang/basic-cli/blob/0.26.0/src/native_stdio/unix.rs)
explicitly converts `EBADF` to EOF/success too. Six existing ordinary nonblocking
read-failure subcases additionally time out because that backend waits on
`EAGAIN`. No optimized upgrade build is attempted after these mandatory failures.
An upgrade alone is therefore not a demonstrated fix.

The [candidate patch](../../platform/patches/stdio-access.patch) instead targets the exact
0.25.0 source. Before each standard-stream operation it checks Unix descriptor
access with `fcntl(F_GETFL)`, returning the OS error for an invalid descriptor or
`EBADF` for an incompatible read/write mode. This query consumes no input and
emits no output. Existing Rust buffering, 16-KiB stdin chunks, flushing, error
conversion and ABI are retained. Empty output writes remain no-ops. All nine
standard-stream host functions use the guard; no new dependency is added.

The host is built separately with `cargo build --locked --release --lib` using
installed Rust 1.99.0, then linked into a temporary copy of the published 0.25.0
platform. Roc stays at `nightly-2026-10-09-258ab27`; application modules are
unchanged apart from the temporary platform path in the copied entry point.

| Check on native macOS ARM64 | Dev | Speed |
| --- | --- | --- |
| Compiler check / source formatting | Pass | Same sources. |
| Inline checks with local platform | 486 pass | 486 pass |
| Ordinary executable suite | 63 methods pass | 63 methods pass |
| Strict descriptor gate | Three methods / all 15 subcases pass | Three methods / all 15 subcases pass |
| Silent output controls | Three pass | Three pass |

The local platform import includes 213 platform checks in addition to the 273
project checks; this is not 486 distinct project requirements. Silent controls
verify that a valid count ignores unusable stderr when it has no diagnostics,
and tail-zero/nonmatching filtering ignore unusable stdout when they emit no
records. Existing prefix WouldBlock, broken pipes and permission checks pass.
No assertion is weakened or skipped.

[Candidate evidence](basic-cli-stdio-candidate.json) records source/patch/archive/
host/binary hashes and actual results. The zero-context patch intentionally has
no whitespace-only context lines. To check/apply it to the exact upstream source:

```sh
git apply --check --unidiff-zero /path/to/stdio-access.patch
git apply --unidiff-zero /path/to/stdio-access.patch
```

The temporary host source/build is `/private/tmp/jlog-stdio-platform`; the
application/platform copies and tested binaries are in
`/private/tmp/jlog-stdio-backport`. The unsuccessful upgrade experiment is in
`/private/tmp/jlog-stdio-upgrade`. These paths are local diagnostic artifacts.

**Candidate snapshot before adoption:** jlog still referenced the original official archive;
the compiler pin, CI workflow, Dockerfile and existing acceptance tests were
unchanged. The correction had not executed on native Linux x86-64, and no new
resource baseline was claimed. Adoption required a reproducible patched-platform
build with pinned provenance and native CI verification. No upstream issue/PR,
dependency publication or project commit/push was made during this investigation.

The user subsequently approved adoption. The patch now lives under `platform/`,
and [the pinned bootstrap](../../platform/README.md) prepares the local and CI
platform. The candidate results above remain a historical snapshot; current
integration and native verification are tracked in the progress record.
Both [corrected native CI jobs](../plans/m4-03-stdio-correction.md) now pass,
including every strict descriptor assertion. The original reproducer and
candidate evidence above preserve the failure and the isolated RED/GREEN path.
