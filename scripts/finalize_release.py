"""Collect both tested native archives into a checksummed release set without rebuilding or publishing."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

import package_release

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import verify_release


ROOT = Path(__file__).resolve().parents[1]
SMOKE_CASES = {"version", "help", "inspect-read-only-file", "count", "tail-original-bytes",
               "filter-original-bytes", "filter-to-count-pipeline", "empty-stdin"}


def verify_set(reports):
    """Require one passing archive per native target, with identical shared release inputs."""
    if len(reports) != 2 or {item["target"] for item in reports} != set(package_release.TARGETS):
        raise ValueError("Release set requires both native targets exactly once")
    if not all(item["verified"] for item in reports):
        raise ValueError("Both native archives must be verified")
    for key in ("version", "source_sha256", "platform_identity", "license_sha256", "notices_sha256", "support_sha256"):
        if reports[0][key] != reports[1][key]:
            raise ValueError(f"Release inputs differ between native targets: {key}")


def read_json(path):
    """Read a required native verification document; absent or malformed evidence fails closed."""
    return json.loads(path.read_text())


def inspect_artifact(root):
    """Verify the archived bytes against full native tests, README/resource results and offline smoke evidence."""
    evidence = root / "evidence"
    binary, environment = package_release.verified_build(evidence)
    target = environment["target"]
    archive = root / "release" / f"jlog-{package_release.VERSION}-{package_release.TARGETS[target]}.tar.gz"
    smoke = read_json(evidence / "release.json")
    readme = read_json(evidence / "readme.json")
    resources = read_json(root / "measurements/results.json")
    with tempfile.TemporaryDirectory(prefix="jlog-finalize-") as scratch:
        _, manifest = verify_release.unpack_checked(archive, Path(scratch))
    expected_cases = {item["name"] for item in smoke["cases"]}
    if (not smoke.get("verified") or expected_cases != SMOKE_CASES
            or len(smoke["cases"]) != len(SMOKE_CASES) or not all(item["verified"] for item in smoke["cases"])
            or smoke["install_exit_status"] != 0 or not smoke["input_binary_archive_hashes_unchanged"]
            or smoke["archive_sha256"] != package_release.sha256(archive)
            or smoke["binary_sha256"] != package_release.sha256(binary)
            or smoke["build"] != manifest or manifest["native_verification"] != environment):
        raise ValueError(f"Native archive smoke evidence does not match the tested artifact: {target}")
    expected_isolation = "macOS sandbox-exec" if target == "arm64mac" else "Docker FROM scratch"
    if smoke["isolation"]["method"] != expected_isolation or smoke["execution"] != "native":
        raise ValueError(f"Offline/native isolation evidence is missing: {target}")
    if target == "arm64mac" and not smoke.get("network_denial_probe_verified"):
        raise ValueError("macOS network-denial probe must pass")
    if (not readme["binary_and_fixture_hashes_verified"] or not readme["cases"]
            or len(readme["source_checks"]) != 5
            or not all(item["verified"] for item in readme["cases"] + readme["source_checks"])
            or readme["binary_sha256"] != manifest["binary_sha256"]
            or len(resources["runs"]) != 70 or not all(item["verified"] for item in resources["runs"])
            or not resources["input_and_binary_hashes_verified"]
            or resources["binary_sha256"] != manifest["binary_sha256"]):
        raise ValueError(f"README or resource verification is incomplete: {target}")
    for name, path in {"LICENSE": ROOT / "LICENSE", "SUPPORT.md": ROOT / "release/SUPPORT.md",
                       "INSTALL.md": ROOT / "release/INSTALL.md",
                       "THIRD_PARTY_NOTICES.md": ROOT / "release/THIRD_PARTY_NOTICES.md"}.items():
        if package_release.sha256(path) != manifest["files_sha256"][name]:
            raise ValueError(f"Bundled release document differs from reviewed source: {name}")
    notices = read_json(ROOT / "release/notices.json")
    if manifest["notices"] != notices:
        raise ValueError("Archive notices differ from the reviewed inventory")
    for name, digest in notices["files_sha256"].items():
        relative = str(Path(name).relative_to("release"))
        if package_release.sha256(ROOT / name) != digest or manifest["files_sha256"].get(relative) != digest:
            raise ValueError(f"Notice bytes differ from the pinned inventory: {name}")
    github = environment["github"]
    report = {"target": target, "version": manifest["version"], "verified": True,
              "archive": archive.name, "archive_sha256": package_release.sha256(archive),
              "archive_bytes": archive.stat().st_size, "binary_sha256": manifest["binary_sha256"],
              "source_commit": environment["commit"], "source_sha256": environment["source_sha256"],
              "platform_identity": environment["platform_build"]["identity"],
              "license_sha256": manifest["files_sha256"]["LICENSE"],
              "notices_sha256": package_release.sha256(ROOT / "release/notices.json"),
              "support_sha256": manifest["files_sha256"]["SUPPORT.md"],
              "runtime_host": smoke["host"], "runtime_architecture": smoke["architecture"],
              "isolation": smoke["isolation"], "offline_cases": len(smoke["cases"]),
              "readme_cases": len(readme["cases"]), "source_blocks": len(readme["source_checks"]),
              "resource_cases": len(resources["runs"]),
              "native_run_url": f"https://github.com/{github['GITHUB_REPOSITORY']}/actions/runs/{github['GITHUB_RUN_ID']}",
              "evidence_sha256": {name: package_release.sha256(evidence / name) for name in
                                  ("environment.json", "verification.json", "readme.json", "release.json")}}
    return archive, report


def finalize(artifacts, output):
    """Copy the exact verified archive pairs and emit a combined manifest/checksum file in a fresh directory."""
    inspected = [inspect_artifact(path) for path in artifacts]
    reports = sorted((report for _, report in inspected), key=lambda item: item["target"])
    verify_set(reports)
    output.mkdir(parents=True, exist_ok=False)
    checksums = []
    for archive, report in sorted(inspected, key=lambda item: item[0].name):
        shutil.copyfile(archive, output / archive.name)
        shutil.copyfile(archive.with_suffix(".gz.sha256"), output / (archive.name + ".sha256"))
        if package_release.sha256(output / archive.name) != report["archive_sha256"]:
            raise ValueError("Copied archive checksum differs")
        checksums.append(f"{report['archive_sha256']}  {archive.name}\n")
    manifest = {"schema_version": 1, "version": package_release.VERSION, "status": "verified release candidate",
                "published": False, "license": "MIT", "targets": reports,
                "support_policy": (ROOT / "release/SUPPORT.md").read_text()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    checksums.append(f"{package_release.sha256(output / 'manifest.json')}  manifest.json\n")
    (output / "SHA256SUMS").write_text("".join(checksums))
    print(f"Verified both native archives; release set: {output}", flush=True)
    return manifest


def main():
    """Require two downloaded native artifact roots; never build, merge, tag or publish."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, nargs=2, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    finalize([path.resolve(strict=True) for path in args.artifacts], args.output.resolve())


if __name__ == "__main__":
    main()
