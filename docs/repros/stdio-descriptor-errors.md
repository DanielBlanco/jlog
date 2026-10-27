# Standard descriptor errors hidden by the pinned platform

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
