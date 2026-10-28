#!/usr/bin/env bash
# Install only the pinned compiler for the asserted native runner architecture.
set -euo pipefail

expected_os="$1"
expected_arch="$2"
destination="$3"
test "$(uname -s)" = "$expected_os"
test "$(uname -m)" = "$expected_arch"
test ! -e "$destination"

case "$expected_os/$expected_arch" in
  Linux/x86_64)
    asset=roc_nightly-linux_x86_64-2026-10-09-258ab27.tar.gz
    digest=dcb99abdf17d062246c05e394357ad682b883a6bcff7b2e581e20564ea88ffc4
    ;;
  Darwin/arm64)
    asset=roc_nightly-macos_apple_silicon-2026-10-09-258ab27.tar.gz
    digest=aa6339579730fcea4753940bec21f5d8cf8be8e25659ec001abccbc3463a60b2
    ;;
  *) printf 'Unsupported native CI platform: %s/%s\n' "$expected_os" "$expected_arch" >&2; exit 1 ;;
esac

archive="$(mktemp)"
trap 'rm -f "$archive"' EXIT
curl --fail --location --retry 3 \
  "https://github.com/roc-lang/nightlies/releases/download/nightly-2026-10-09-258ab27/$asset" \
  --output "$archive"
if test "$expected_os" = Darwin; then
  actual="$(shasum -a 256 "$archive" | cut -d ' ' -f 1)"
else
  actual="$(sha256sum "$archive" | cut -d ' ' -f 1)"
fi
test "$actual" = "$digest"
mkdir -p "$destination"
tar -xzf "$archive" -C "$destination" --strip-components=1
version="$("$destination/roc" version)"
test "$version" = 'Roc compiler version nightly-2026-10-09-258ab27'
printf '%s\n%s  %s\n' "$version" "$digest" "$asset"
