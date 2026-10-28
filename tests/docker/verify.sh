#!/bin/sh
# Build and verify the pinned application as the image's unprivileged user.
set -eu

cd /src
test "$(id -u)" != 0
git config --global --add safe.directory /src

# Keep the mounted checkout read-only; generated platform files need a writable copy.
python3 -c 'import shutil; shutil.copytree("/src", "/work/source", ignore=shutil.ignore_patterns(".git", ".cache", "dist", "__pycache__", "basic-cli"))'
cd /work/source
python3 scripts/build_platform.py --work-dir /work/platform-build

case "$(uname -m)" in
  aarch64|arm64) target=arm64musl ;;
  x86_64) target=x64musl ;;
  *) printf 'Unsupported native build architecture\n' >&2; exit 1 ;;
esac

roc version
roc check src/main.roc
roc fmt --check src/main.roc src/Cli.roc src/Jsonl.roc src/Operations.roc
roc test --opt=dev --no-cache src/main.roc
roc build --opt=dev --no-cache --target="$target" --output=/work/jlog-dev src/main.roc
JLOG_BIN=/work/jlog-dev python3 -m unittest discover -s tests -p 'test_cli.py'
JLOG_BIN=/work/jlog-dev python3 -m unittest discover -s tests -p 'test_io_contract.py'

roc test --opt=speed --no-cache src/main.roc
roc build --opt=speed --no-cache --target="$target" --output=/work/jlog-speed src/main.roc
JLOG_BIN=/work/jlog-speed python3 -m unittest discover -s tests -p 'test_cli.py'
JLOG_BIN=/work/jlog-speed python3 -m unittest discover -s tests -p 'test_io_contract.py'
python3 -m unittest discover -s tests -p 'test_measure_resources.py'
python3 -m unittest discover -s tests -p 'test_build_platform.py'
file /work/jlog-dev /work/jlog-speed
