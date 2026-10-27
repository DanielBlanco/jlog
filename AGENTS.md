# Repository Guidelines

## Development Status & Resumption

M1 through M3 behavior is implemented. Strict descriptor-edge conformance from
M2 remains open; the user explicitly authorized proceeding to M3 with that gap
recorded. Read the latest [progress record](docs/plans/jlog-v0.1-progress.md) and the
[development handoff](docs/plans/jlog-handoff.md) before resuming for current state,
verification, and checkpoint limits.

The separately authorized `--progress` extension adds opt-in, rate-limited stderr
counts to inspection. See its [specification](docs/specs/inspection-progress.md).
The later authorizations cover M2 count/tail and error handling, and M3 streaming
string-only filtering. On 2026-10-27 the user authorized starting M4 with M4-01,
the contract/coverage audit. See the progress record for its results and open
release gates. The user subsequently authorized the next task, M4-02 resource
measurements, while retaining the unresolved M4-01 release gates. The later
request authorizes M4-03 native CI alongside Linux x86-64 measurements. Release
publishing remains a separate action.

## Project Structure & Module Organization

- `src/main.roc` is the application entry point and owns I/O and exit mapping.
- `src/Cli.roc`, `src/Jsonl.roc`, and `src/Operations.roc` own pure parsing,
  framing/validation/lookup, and operation reducers/rendering, respectively. Pure
  tests are inline `expect` checks in these modules.
- `src/help.txt` contains the CLI help, imported as a string at compile time by
  `src/Cli.roc`. Preserve the final newline when editing and rebuild to apply changes.
- `tests/test_cli.py` runs executable acceptance tests using Python's stdlib.
- `tests/test_io_contract.py` is the strict standard-descriptor conformance gate.
  It currently fails on the pin; run it explicitly and preserve its exit-3
  expectations. Passing `test_cli.py` alone is not full release verification.
- `tests/measure_resources.py` runs macOS/Linux resource measurements against an
  explicitly supplied optimized binary. It records architecture/environment,
  generates large fixtures outside the checkout, and verifies outputs/hashes.
  `tests/test_measure_resources.py` checks timing formats/units; `tests/docker/`
  provides the pinned unprivileged Linux container and verification instructions.
- `.github/workflows/native-ci.yml` and `tests/ci/` automate pinned native
  Linux x86-64/macOS ARM64 verification and resource measurements. Strict
  descriptor failures must remain fatal, even when independent measurements run.
- `dist/` contains ignored build outputs.
- `docs/` contains documentation, including `docs/specs/` and `docs/plans/`.
  Read [What is JSONL?](docs/jsonl.md) for format rules and examples.
- `.tool-versions` pins Node.js to `24.13.0`; Node is not required for jlog.

Keep application code in `src/`, separate from compiler and cache directories.

## Build, Test, and Development Commands

Use Roc `nightly-2026-10-09-258ab27` on your `PATH`; the compiler is outside the
checkout. Discover it with `command -v roc` and confirm the pin with `roc version`.
The application pins `basic-cli` 0.25.0. Native CI now executes macOS ARM64 and
Linux x86-64 check/build/test/resource sequences; ordinary suites and all resource
cases pass, while strict descriptor conformance still fails on both. See the
[CI evidence](docs/plans/m4-03-native-ci.md). Linux ARM64 Docker remains supplemental.

Run commands from the repository root:

```sh
mkdir -p dist
roc build --opt=dev --output=dist/jlog src/main.roc
JLOG_BIN="$PWD/dist/jlog" python3 -m unittest discover -s tests -p 'test_cli.py' -v
```

- `roc --help`: inspect available compiler commands.
- `roc repl`: start an interactive session without an application file.
- `roc run src/main.roc -- --help`: run the CLI locally.
- `roc build --opt=speed --output=dist/jlog src/main.roc`: build an optimized binary.
- `roc check src/main.roc`: check source code without building or running it.
- `roc test --opt=dev --no-cache src/main.roc`: run inline `expect` checks in the application and its imported local modules. Repeat with `--opt=speed` for optimized verification.
- `roc fmt src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc`: format project sources. Add `--check` to verify formatting without edits.

No npm scripts are configured. The native CI command driver is documented in
[`tests/ci/README.md`](tests/ci/README.md).

## Coding Style & Naming Conventions

Use `roc fmt` as the authority for Roc indentation and layout. Choose descriptive module and function names, and keep filenames consistent with module declarations. Document each named Roc function with a `##` comment explaining its behavior and relevant input/error contract; document Python helpers and test methods with docstrings. No additional lint configuration exists. Avoid editing compiler or linker files as application code.

## Testing Guidelines

Use Roc's built-in `expect` checks for new Roc behavior, including edge cases and regression coverage for fixes. Run `roc check`, `roc test`, and `roc fmt --check` against the relevant sources before submitting changes. No coverage threshold or separate test-file naming convention is configured.

## Commit & Pull Request Guidelines

Use concise, imperative commit subjects, such as `Add log parsing module`. Pull requests should explain the change, link relevant issues, and list validation commands and results. Include screenshots only for visible interface changes. Explicitly document toolchain upgrades and their platform requirements.
