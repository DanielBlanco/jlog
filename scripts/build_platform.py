"""Prepare the checksum-pinned basic-cli 0.25 host with jlog's descriptor correction."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "platform/basic-cli.lock.json"
OUTPUT = ROOT / "platform/basic-cli"
MARKER = "jlog-platform.json"
TARGETS = {("Darwin", "arm64"): ("arm64mac", "aarch64-apple-darwin"),
           ("Linux", "x86_64"): ("x64musl", "x86_64-unknown-linux-musl"),
           ("Linux", "aarch64"): ("arm64musl", "aarch64-unknown-linux-musl")}


def sha256(path):
    """Hash large archives and native libraries without retaining them in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration():
    """Verify the reviewed patch and identify all checked-in build inputs."""
    lock = json.loads(LOCK.read_text())
    patch = ROOT / lock["patch"]["path"]
    if sha256(patch) != lock["patch"]["sha256"]:
        raise RuntimeError("Platform patch differs from its pinned checksum")
    identity = hashlib.sha256(LOCK.read_bytes() + patch.read_bytes()
                              + Path(__file__).read_bytes()).hexdigest()
    return lock, patch, identity


def prepared(output, identity, target):
    """Accept a cached platform only when its inputs, target and every file match."""
    try:
        data = json.loads((output / MARKER).read_text())
        if data["identity"] != identity or data["target"] != target or not data["files_sha256"]:
            return None
        actual = {str(path.relative_to(output)): sha256(path)
                  for path in output.rglob("*") if path.is_file() and path.name != MARKER}
        return data if actual == data["files_sha256"] else None
    except (OSError, ValueError, KeyError):
        return None


def download(item, destination):
    """Reuse verified downloads and reject an unexpected server response before extraction."""
    if destination.is_file() and sha256(destination) == item["sha256"]:
        return
    partial = destination.with_suffix(".partial")
    subprocess.run(["curl", "--fail", "--location", "--retry", "3", item["url"],
                    "--output", str(partial)], check=True)
    if sha256(partial) != item["sha256"]:
        partial.unlink()
        raise RuntimeError(f"Download checksum mismatch: {item['url']}")
    partial.replace(destination)


def build(lock, patch, identity, target, rust_target, work):
    """Rebuild the exact patched source, retaining the published Roc ABI and target support files."""
    work.mkdir(parents=True, exist_ok=True)
    source_archive, bundle = work / "source.tar.gz", work / "bundle.tar.zst"
    download(lock["source"], source_archive)
    download(lock["bundle"], bundle)
    source = work / "source"
    if source.exists():
        shutil.rmtree(source)
    source.mkdir()
    subprocess.run(["tar", "-xzf", str(source_archive), "-C", str(source),
                    "--strip-components=1"], check=True)
    host_source = source / "src/lib.rs"
    if sha256(host_source) != lock["patch"]["original_source_sha256"]:
        raise RuntimeError("The upstream host source does not match the reviewed base")
    subprocess.run(["git", "apply", "--unsafe-paths", "--unidiff-zero", "--directory", str(source),
                    str(patch)], cwd=ROOT, check=True)
    if sha256(host_source) != lock["patch"]["patched_source_sha256"]:
        raise RuntimeError("The patched host source does not match the reviewed correction")
    environment = dict(os.environ)
    # An explicitly selected installed alias is accepted only at the exact version.
    environment["RUSTUP_TOOLCHAIN"] = os.environ.get("RUSTUP_TOOLCHAIN", lock["rust_version"])
    environment["CARGO_TARGET_DIR"] = str(work / "target")
    rustc = subprocess.check_output(["rustc", "--version"], env=environment, text=True).strip()
    if not rustc.startswith(f"rustc {lock['rust_version']} ("):
        raise RuntimeError(f"Expected Rust {lock['rust_version']}; found {rustc}")
    command = ["cargo", "build", "--locked", "--release", "--lib"]
    library = work / "target/release/libhost.a"
    if platform.system() == "Linux":
        command.extend(["--target", rust_target])
        environment[f"CC_{rust_target.replace('-', '_')}"] = "musl-gcc"
        library = work / "target" / rust_target / "release/libhost.a"
    subprocess.run(command, cwd=source, env=environment, check=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".basic-cli-", dir=OUTPUT.parent))
    try:
        # GNU tar needs zstd; BSD tar can decode the same verified archive directly.
        if platform.system() == "Linux":
            raw_tar = work / "bundle.tar"
            subprocess.run(["zstd", "--decompress", "--force", str(bundle), "-o", str(raw_tar)], check=True)
        else:
            raw_tar = bundle
        subprocess.run(["tar", "-xf", str(raw_tar), "-C", str(staging)], check=True)
        for other in (staging / "targets").iterdir():
            if other.name != target:
                shutil.rmtree(other)
        shutil.copyfile(library, staging / "targets" / target / "libhost.a")
        shutil.copyfile(source / "LICENSE", staging / "LICENSE")
        files = {str(path.relative_to(staging)): sha256(path)
                 for path in sorted(staging.rglob("*")) if path.is_file()}
        data = {"identity": identity, "target": target, "rust_target": rust_target,
                "rustc": rustc, "version": lock["version"], "source_commit": lock["source"]["commit"],
                "source_archive_sha256": lock["source"]["sha256"],
                "bundle_sha256": lock["bundle"]["sha256"], "patch_sha256": lock["patch"]["sha256"],
                "cargo_lock_sha256": sha256(source / "Cargo.lock"), "files_sha256": files}
        (staging / MARKER).write_text(json.dumps(data, indent=2) + "\n")
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        staging.replace(OUTPUT)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return data


def main():
    """Select the native target and verify or prepare the ignored platform directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=ROOT / ".cache/platform")
    args = parser.parse_args()
    native = TARGETS.get((platform.system(), platform.machine()))
    if native is None:
        parser.error("Supported native builds: macOS ARM64 and Linux x86-64/ARM64")
    target, rust_target = native
    lock, patch, identity = configuration()
    existing = prepared(OUTPUT, identity, target)
    if existing:
        print(f"Verified existing basic-cli {lock['version']} + stdio patch ({target})")
        return
    data = build(lock, patch, identity, target, rust_target,
                 args.work_dir.resolve() / f"{identity[:16]}-{target}")
    print(f"Prepared basic-cli {data['version']} + stdio patch ({target}): {OUTPUT}")


if __name__ == "__main__":
    main()
