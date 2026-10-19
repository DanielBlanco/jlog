# Repository Guidelines

## Project Structure & Module Organization

This checkout currently contains development tooling only; there are no application sources, tests, assets, or package manifests yet.

- `.tool-versions` pins Node.js to `24.13.0`.
- `roc_nightly-macos_apple_silicon-2026-10-09-258ab27/` contains the bundled Roc compiler, licensing files, and macOS linker support.
- The matching `.tar.gz` file is the compiler distribution archive.
- `docs/` contains project documentation. Read [What is JSONL?](docs/jsonl.md) for format rules, examples, and reference links.

Keep future application code separate from the compiler directory. Document the entry point and source/test layout when introducing them; `main.roc` below is an example, not an existing file.

## Build, Test, and Development Commands

The bundled compiler targets macOS Apple Silicon. From the repository root, add it to your shell's path:

```sh
export PATH="$PWD/roc_nightly-macos_apple_silicon-2026-10-09-258ab27:$PATH"
```

- `roc --help`: inspect available compiler commands.
- `roc repl`: start an interactive session without an application file.
- `roc run main.roc`: run an application after its entry point exists.
- `roc build main.roc`: compile an application binary.
- `roc check main.roc`: check source code without building or running it.
- `roc test main.roc`: run top-level `expect` checks in the module and its imported local modules.
- `roc fmt .` / `roc fmt --check .`: format Roc sources or verify their formatting.

No npm scripts or project-specific build wrappers are configured.

## Coding Style & Naming Conventions

Use `roc fmt` as the authority for Roc indentation and layout. Choose descriptive module and function names, and keep filenames consistent with module declarations. No additional lint configuration or established naming convention exists yet. Avoid editing bundled compiler or linker files as application code.

## Testing Guidelines

Use Roc's built-in `expect` checks for new Roc behavior, including edge cases and regression coverage for fixes. Run `roc check`, `roc test`, and `roc fmt --check` against the relevant sources before submitting changes. No coverage threshold or separate test-file naming convention is configured.

## Commit & Pull Request Guidelines

This directory has no Git metadata, so existing commit conventions cannot be verified. Use concise, imperative commit subjects, such as `Add log parsing module`. Pull requests should explain the change, link relevant issues, and list validation commands and results. Include screenshots only for visible interface changes. Explicitly document toolchain upgrades and their platform requirements.
