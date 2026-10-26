# Repository Guidelines

## Development Status & Resumption

M1-A and M1-B are implemented; development is paused. Read the
[development handoff](docs/plans/jlog-handoff.md) before resuming for current state,
verification, and checkpoint limits.

## Project Structure & Module Organization

- `src/main.roc` is the application entry point and owns I/O and exit mapping.
- `src/Cli.roc`, `src/Jsonl.roc`, and `src/Operations.roc` own pure parsing,
  framing/validation, and inspection summaries/rendering, respectively. Pure
  tests are inline `expect` checks in these modules.
- `src/help.txt` contains the CLI help, imported as a string at compile time by
  `src/Cli.roc`. Preserve the final newline when editing and rebuild to apply changes.
- `tests/test_cli.py` runs executable acceptance tests using Python's stdlib.
- `dist/` contains ignored build outputs.
- `docs/` contains documentation, including `docs/specs/` and `docs/plans/`.
  Read [What is JSONL?](docs/jsonl.md) for format rules and examples.
- `.tool-versions` pins Node.js to `24.13.0`; Node is not required for jlog.

Keep application code in `src/`, separate from compiler and cache directories.

## Build, Test, and Development Commands

Use Roc `nightly-2026-10-09-258ab27` on your `PATH`; the compiler is outside the
checkout. Discover it with `command -v roc` and confirm the pin with `roc version`.
The application pins `basic-cli` 0.25.0. Native verification currently covers
macOS Apple Silicon; Linux x86-64 verification remains pending.

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

No npm scripts or project-specific build wrappers are configured.

## Coding Style & Naming Conventions

Use `roc fmt` as the authority for Roc indentation and layout. Choose descriptive module and function names, and keep filenames consistent with module declarations. Document each named Roc function with a `##` comment explaining its behavior and relevant input/error contract; document Python helpers and test methods with docstrings. No additional lint configuration exists. Avoid editing compiler or linker files as application code.

## Testing Guidelines

Use Roc's built-in `expect` checks for new Roc behavior, including edge cases and regression coverage for fixes. Run `roc check`, `roc test`, and `roc fmt --check` against the relevant sources before submitting changes. No coverage threshold or separate test-file naming convention is configured.

## Commit & Pull Request Guidelines

Use concise, imperative commit subjects, such as `Add log parsing module`. Pull requests should explain the change, link relevant issues, and list validation commands and results. Include screenshots only for visible interface changes. Explicitly document toolchain upgrades and their platform requirements.
