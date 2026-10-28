"""Package a previously verified optimized executable without rebuilding it."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile

import build_platform


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
TARGETS = {"arm64mac": "macos-arm64", "x64musl": "linux-x86_64"}
REQUIRED_CHECKS = {"check", "format", "measurement-units", "platform-units"} | {
    f"{name}-{mode}" for mode in ("dev", "speed")
    for name in ("pure", "build", "file", "cli", "io-contract")}


def sha256(path):
    """Hash an executable, archive or notice without retaining large inputs."""
    return build_platform.sha256(path)


def binary_target(data):
    """Recognize the supported executable headers and reject other architectures."""
    if data[:6] == b"\x7fELF\x02\x01" and len(data) >= 64:
        if struct.unpack_from("<H", data, 18)[0] == 62:
            return "x64musl"
    if data[:4] == b"\xcf\xfa\xed\xfe" and len(data) >= 32:
        if struct.unpack_from("<I", data, 4)[0] == 0x0100000C:
            return "arm64mac"
    raise ValueError("Expected a Linux x86-64 ELF or macOS ARM64 Mach-O executable")


def verified_build(evidence):
    """Require successful native suites and matching source, platform and executable identities."""
    environment = json.loads((evidence / "environment.json").read_text())
    results = json.loads((evidence / "verification.json").read_text())
    if (not REQUIRED_CHECKS.issubset(item["name"] for item in results)
            or any(item["status"] != 0 for item in results)):
        raise ValueError("All native checks, including both strict I/O suites, must pass")
    target = environment["target"]
    native = {"arm64mac": ("Darwin", "arm64"), "x64musl": ("Linux", "x86_64")}
    if (target not in TARGETS or environment["execution"] != "native"
            or (environment["uname"][0], environment["uname"][4]) != native[target]
            or not environment["source_hashes_unchanged"] or not environment["platform_hashes_unchanged"]):
        raise ValueError("Evidence must describe an unchanged build on its native release target")
    actual = {str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT / "src").glob("*")) if p.is_file()}
    if actual != environment["source_sha256"]:
        raise ValueError("Application sources differ from the verified build")
    lock, _, identity = build_platform.configuration()
    platform_build = environment["platform_build"]
    if (environment["roc"] != "Roc compiler version nightly-2026-10-09-258ab27"
            or platform_build["identity"] != identity or platform_build["target"] != target
            or platform_build["patch_sha256"] != lock["patch"]["sha256"]):
        raise ValueError("Compiler/platform evidence differs from the approved pins")
    binary = evidence / "jlog-speed"
    if sha256(binary) != environment["binary_speed_sha256"]:
        raise ValueError("Optimized executable differs from the tested artifact")
    if binary_target(binary.read_bytes()[:64]) != target:
        raise ValueError("Executable architecture differs from its native verification")
    return binary, environment


def package(evidence, output):
    """Create a deterministic archive, provenance and checksum from verified inputs only."""
    binary, environment = verified_build(evidence)
    notices = json.loads((ROOT / "release/notices.json").read_text())
    for name, digest in notices["files_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"Notice differs from its recorded source: {name}")
    if notices["cargo_lock_sha256"] != environment["platform_build"]["cargo_lock_sha256"]:
        raise ValueError("Dependency notices describe a different host dependency lock")
    # Reading LICENSE is intentional: an unchosen project license blocks packaging.
    files = {"bin/jlog": binary.read_bytes(), "LICENSE": (ROOT / "LICENSE").read_bytes(),
             "INSTALL.md": (ROOT / "release/INSTALL.md").read_bytes(),
             "SUPPORT.md": (ROOT / "release/SUPPORT.md").read_bytes(),
             "THIRD_PARTY_NOTICES.md": (ROOT / "release/THIRD_PARTY_NOTICES.md").read_bytes()}
    files.update({str(Path(name).relative_to("release")): (ROOT / name).read_bytes()
                  for name in notices["files_sha256"]})
    manifest = {"version": VERSION, "target": environment["target"],
                "binary_sha256": sha256(binary), "native_verification": environment,
                "verification_sha256": sha256(evidence / "verification.json"),
                "notices": notices,
                "files_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files["BUILD.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    name = f"jlog-{VERSION}-{TARGETS[environment['target']]}"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}.tar.gz"
    with archive.open("xb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar:
                for path, data in sorted(files.items()):
                    info = tarfile.TarInfo(f"{name}/{path}")
                    info.size, info.mode = len(data), 0o755 if path == "bin/jlog" else 0o644
                    tar.addfile(info, io.BytesIO(data))
    checksum = f"{sha256(archive)}  {archive.name}\n"
    archive.with_suffix(archive.suffix + ".sha256").write_text(checksum)
    print(checksum, end="", flush=True)
    return archive


def main():
    """Require existing passing native evidence and write a new release candidate archive."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/release")
    args = parser.parse_args()
    package(args.evidence.resolve(strict=True), args.output.resolve())


if __name__ == "__main__":
    main()
