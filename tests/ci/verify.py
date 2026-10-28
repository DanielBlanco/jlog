"""Run native CI checks, retain every command status, and keep conformance failures fatal."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import build_platform


PIN = "Roc compiler version nightly-2026-10-09-258ab27"
TARGETS = {("Darwin", "arm64"): "arm64mac", ("Linux", "x86_64"): "x64musl"}


def sha256(path):
    """Hash source/build artifacts without loading entire executables into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(name, command, output, results, binary=None):
    """Capture one real command's combined log/status and echo its log into CI."""
    print(f"::group::{name}", flush=True)
    environment = dict(os.environ)
    if binary:
        environment["JLOG_BIN"] = str(binary)
    with (output / f"{name}.log").open("wb") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
    print((output / f"{name}.log").read_text(errors="replace"), end="", flush=True)
    print("::endgroup::", flush=True)
    results.append({"name": name, "command": command, "status": result.returncode})
    (output / "verification.json").write_text(json.dumps(results, indent=2) + "\n")
    return result.returncode == 0


def main():
    """Verify native pins, execute both build suites, and expose measurement readiness."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=sorted(TARGETS.values()))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    if os.geteuid() == 0:
        parser.error("Run as an ordinary user so permission checks are meaningful")
    if TARGETS.get((platform.system(), platform.machine())) != args.target:
        parser.error("The requested target must match the native OS and architecture")
    version = subprocess.check_output(["roc", "version"], text=True).strip()
    if version != PIN:
        parser.error(f"Unexpected compiler: {version}")
    _, _, platform_identity = build_platform.configuration()
    platform_build = build_platform.prepared(build_platform.OUTPUT, platform_identity, args.target)
    if platform_build is None:
        parser.error("Run python3 scripts/build_platform.py to prepare and verify the pinned platform")
    source_paths = sorted(Path("src").glob("*"))
    source_hashes = {str(path): sha256(path) for path in source_paths if path.is_file()}
    environment = {"execution": "native", "target": args.target, "uid": os.geteuid(),
                   "uname": list(platform.uname()), "python": sys.version, "roc": version,
                   "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                   "source_sha256": source_hashes,
                   "platform_build": platform_build,
                   "github": {name: os.environ.get(name) for name in
                              ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID",
                               "GITHUB_RUN_ATTEMPT", "RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion")}}
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    results = []
    run("check", ["roc", "check", "src/main.roc"], output, results)
    run("format", ["roc", "fmt", "--check", "src/main.roc", "src/Cli.roc",
                   "src/Jsonl.roc", "src/Operations.roc"], output, results)
    units_ok = run("measurement-units", ["python3", "-m", "unittest", "discover", "-s", "tests",
                                        "-p", "test_measure_resources.py", "-v"], output, results)
    platform_units_ok = run("platform-units", ["python3", "-m", "unittest", "discover", "-s", "tests",
                                             "-p", "test_build_platform.py", "-v"], output, results)
    run("release-units", ["python3", "-m", "unittest", "discover", "-s", "tests",
                          "-p", "test_package_release.py", "-v"], output, results)
    measure_ready = False
    for optimization in ("dev", "speed"):
        binary = output / f"jlog-{optimization}"
        pure_ok = run(f"pure-{optimization}", ["roc", "test", f"--opt={optimization}", "--no-cache",
                                              "src/main.roc"], output, results)
        built = run(f"build-{optimization}", ["roc", "build", "--no-cache", f"--opt={optimization}",
                                              f"--target={args.target}", f"--output={binary}",
                                              "src/main.roc"], output, results)
        if not built:
            continue
        run(f"file-{optimization}", ["file", str(binary)], output, results)
        ordinary_ok = run(f"cli-{optimization}", ["python3", "-m", "unittest", "discover", "-s", "tests",
                                                 "-p", "test_cli.py", "-v"], output, results, binary)
        run(f"io-contract-{optimization}", ["python3", "-m", "unittest", "discover", "-s", "tests",
                                           "-p", "test_io_contract.py", "-v"], output, results, binary)
        environment[f"binary_{optimization}_sha256"] = sha256(binary)
        if optimization == "speed":
            measure_ready = pure_ok and ordinary_ok and units_ok and platform_units_ok
    unchanged = all(sha256(Path(path)) == digest for path, digest in source_hashes.items())
    environment["source_hashes_unchanged"] = unchanged
    platform_unchanged = build_platform.prepared(build_platform.OUTPUT, platform_identity, args.target) is not None
    environment["platform_hashes_unchanged"] = platform_unchanged
    (output / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
            handle.write(f"measure-ready={str(measure_ready and unchanged and platform_unchanged).lower()}\n")
    failures = [item["name"] for item in results if item["status"] != 0]
    print(f"Failed commands: {', '.join(failures) if failures else 'none'}", flush=True)
    return 1 if failures or not unchanged or not platform_unchanged else 0


if __name__ == "__main__":
    sys.exit(main())
