# jlog 0.1.0 platform support

Release verification covers these native configurations:

| Release archive | Verified baseline | Runtime |
| --- | --- | --- |
| `macos-arm64` | macOS 15.7.9 ARM64; also tested locally on macOS 27.0.1 ARM64 | macOS system library; no Roc or Rust installation required. |
| `linux-x86_64` | Ubuntu 24.04.5 x86-64 on the native GitHub runner; its kernel is recorded in the verification report | Static musl executable; no separate language runtime required. |

Support is limited to these tested configurations for v0.1. Earlier macOS
versions and other Linux distributions/kernel combinations are unverified.
macOS 15.7.9 is the oldest tested macOS version; Ubuntu 24.04.5 is the Linux
distribution baseline. We make no broader minimum-kernel or libc compatibility
claim from static linking. The Mach-O deployment target is build metadata,
not evidence of testing on older macOS versions.

Linux ARM64 Debian 12 Docker results are supplemental. There is no Linux ARM64,
macOS x86-64 or Windows release archive. Native execution is required for each
release target; emulation and cross-builds do not substitute for that evidence.

Each archive's `BUILD.json` records the native build/test environment, pinned
toolchain, corrected basic-cli platform and executable/file hashes. The final
release manifest links those artifacts to their offline smoke checks. Runtime
verification denies network access and makes Roc/Rust unavailable to the process.
Installation uses local checksum, tar and install tools.
