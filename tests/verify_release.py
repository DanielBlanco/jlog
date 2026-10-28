"""Install a fresh release archive and verify its native executable with network access denied."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_release


ROOT = Path(__file__).resolve().parents[1]


def unpack_checked(archive, work):
    """Check the download checksum, exact archive contents, modes and every bundled file hash."""
    expected = f"{package_release.sha256(archive)}  {archive.name}\n"
    if archive.with_suffix(archive.suffix + ".sha256").read_text() != expected:
        raise ValueError("Archive checksum mismatch")
    prefix = archive.name.removesuffix(".tar.gz")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if (len({member.name for member in members}) != len(members)
                or any(not m.isfile() or not m.name.startswith(prefix + "/")
                       or ".." in Path(m.name).parts for m in members)):
            raise ValueError("Unexpected archive member or path")
        manifest = json.load(tar.extractfile(f"{prefix}/BUILD.json"))
        expected_names = {f"{prefix}/{name}" for name in manifest["files_sha256"]} | {f"{prefix}/BUILD.json"}
        if {member.name for member in members} != expected_names:
            raise ValueError("Archive differs from its file inventory")
        required = {"bin/jlog", "LICENSE", "INSTALL.md", "SUPPORT.md", "THIRD_PARTY_NOTICES.md"}
        if not required.issubset(manifest["files_sha256"]) or not any(n.startswith("licenses/") for n in manifest["files_sha256"]):
            raise ValueError("Missing executable, license, notices or instructions")
        for member in members:
            relative = member.name[len(prefix) + 1:]
            data = tar.extractfile(member).read()
            if relative != "BUILD.json" and hashlib.sha256(data).hexdigest() != manifest["files_sha256"][relative]:
                raise ValueError(f"Bundled file checksum mismatch: {relative}")
            if member.mode != (0o755 if relative == "bin/jlog" else 0o644):
                raise ValueError(f"Incorrect permissions: {relative}")
            destination = work / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.chmod(member.mode)
    binary = work / prefix / "bin/jlog"
    if (package_release.sha256(binary) != manifest["binary_sha256"]
            or package_release.binary_target(binary.read_bytes()[:64]) != manifest["target"]):
        raise ValueError("Archived executable differs from its tested identity or architecture")
    if prefix != f"jlog-{manifest['version']}-{package_release.TARGETS[manifest['target']]}":
        raise ValueError("Archive filename differs from its version/target")
    return work / prefix, manifest


def verify(archive, work, destination):
    """Install with the bundled commands, run real offline operations and preserve integrity evidence."""
    unpacked, manifest = unpack_checked(archive, work)
    expected_native = {"arm64mac": ("Darwin", "arm64"), "x64musl": ("Linux", "x86_64")}
    if (platform.system(), platform.machine()) != expected_native[manifest["target"]]:
        raise ValueError("Archive smoke tests must execute on their native release architecture")
    if os.geteuid() == 0:
        raise ValueError("Run as an ordinary user to verify read-only input handling")
    prefix = work / "install prefix with spaces"
    copied = work / archive.name
    shutil.copyfile(archive, copied)
    shutil.copyfile(archive.with_suffix(archive.suffix + ".sha256"), work / (archive.name + ".sha256"))
    install_text = (unpacked / "INSTALL.md").read_text()
    install_script = install_text.split("```sh\n", 1)[1].split("```", 1)[0]
    environment = dict(os.environ, JLOG_ARCHIVE=archive.name, JLOG_INSTALL_PREFIX=str(prefix))
    install = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-e", "-c", install_script],
                             cwd=work, env=environment, capture_output=True, timeout=30)
    if install.returncode or not install.stdout.endswith(b"jlog 0.1.0\n") or install.stderr:
        raise AssertionError(f"Bundled installation failed: {install}")
    installed = prefix / "bin/jlog"
    if package_release.sha256(installed) != manifest["binary_sha256"] or installed.stat().st_mode & 0o777 != 0o755:
        raise AssertionError("Installation changed the executable or its permissions")
    fixture = work / "events.jsonl"
    records = b'{"status":"failed","value":1e999}\r\n{"status":"ok"}\n{"status":"failed","message":"caf\xc3\xa9"}'
    selected = b'{"status":"failed","value":1e999}\n{"status":"failed","message":"caf\xc3\xa9"}\n'
    fixture.write_bytes(records)
    fixture.chmod(0o444)
    fixture_hash = package_release.sha256(fixture)
    runtime_env = {"PATH": str(prefix / "bin"), "LC_ALL": "C"}
    report = {"schema_version": 1, "host": platform.platform(), "architecture": platform.machine(),
              "execution": "native", "archive": archive.name, "archive_sha256": package_release.sha256(archive),
              "binary_sha256": manifest["binary_sha256"], "build": manifest,
              "install_script": install_script, "install_exit_status": install.returncode,
              "install_stdout": install.stdout.decode(), "work_dir": str(work), "cases": []}
    image = None
    if platform.system() == "Darwin":
        # Deny both network use and toolchain execution, even through absolute paths.
        profile = '(version 1)(allow default)(deny network*)(deny process-exec (regex #"/(roc|rustc|cargo)$"))'
        profile += f'(deny file-read* (subpath {json.dumps(str(ROOT))}))'
        profile += '(deny file-read* (subpath "/Users/runner/.rustup") (subpath "/Users/runner/.cargo"))'
        command = ["/usr/bin/sandbox-exec", "-p", profile, str(installed)]
        runtime_fixture = str(fixture)
        report["isolation"] = {"method": "macOS sandbox-exec", "network": "deny network*",
                               "toolchains": "absent from PATH; executable names denied, including absolute paths",
                               "profile": profile}
        probe = "import socket\ns=socket.socket()\ntry:\n s.connect(('127.0.0.1',9))\nexcept PermissionError:\n print('network denied')\nelse:\n raise SystemExit('network unexpectedly allowed')\n"
        result = subprocess.run(command[:3] + [sys.executable, "-c", probe], cwd=work,
                                env=runtime_env, capture_output=True, timeout=30)
        if result.returncode or result.stdout != b"network denied\n":
            raise AssertionError(f"Network-denial probe failed: {result}")
        result = subprocess.run(command[:3] + ["/bin/sh", "-c", "if command -v roc || command -v rustc || command -v cargo; then exit 99; fi"],
                                cwd=work, env=runtime_env, capture_output=True, timeout=30)
        if result.returncode != 0 or result.stdout:
            raise AssertionError("A compiler is reachable on the runtime PATH")
        report["network_denial_probe_verified"] = True
    else:
        context = work / "offline-image"
        context.mkdir()
        shutil.copyfile(installed, context / "jlog")
        (context / "jlog").chmod(0o755)
        shutil.copyfile(fixture, context / "events.jsonl")
        (context / "events.jsonl").chmod(0o444)
        (context / "Dockerfile").write_text("FROM scratch\nCOPY jlog /jlog\nCOPY events.jsonl /events.jsonl\nUSER 65534:65534\nENTRYPOINT [\"/jlog\"]\n")
        image = f"jlog-offline-{os.getpid()}"
        subprocess.run(["docker", "build", "--network=none", "--tag", image, str(context)], check=True)
        command = ["docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--interactive", image]
        runtime_fixture = "/events.jsonl"
        report["isolation"] = {"method": "Docker FROM scratch", "network": "none", "root_files": ["jlog", "events.jsonl"],
                               "user": "65534:65534", "read_only": True,
                               "toolchains": "No compiler, shell or language runtime exists in the image"}

    def run(name, args, stdout, status=0, data=None):
        """Check exact output/status under the platform's network-denying runtime boundary."""
        result = subprocess.run(command + args, input=data, cwd=work, env=runtime_env if image is None else None,
                                capture_output=True, timeout=30)
        verified = result.returncode == status and result.stdout == stdout and result.stderr == b""
        report["cases"].append({"name": name, "args": args, "exit_status": result.returncode,
                                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                                "stderr": result.stderr.decode(errors="replace"), "verified": verified})
        destination.write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name}: {'PASS' if verified else 'FAIL'}", flush=True)
        if not verified:
            raise AssertionError(f"Offline archive smoke failed: {name}; see {destination}")
        return result.stdout

    try:
        run("version", ["--version"], b"jlog 0.1.0\n")
        run("help", ["--help"], (ROOT / "src/help.txt").read_bytes())
        run("inspect-read-only-file", [runtime_fixture], f"File: {runtime_fixture}\nRecords: 3\nValid: 3\nInvalid: 0\n".encode())
        run("count", ["--count", runtime_fixture], b"3\n")
        run("tail-original-bytes", ["--tail", "1", runtime_fixture], selected.splitlines(keepends=True)[-1])
        run("filter-original-bytes", ["--where", "status=failed", runtime_fixture], selected)
        # Connect actual child streams; do not substitute a Python count or reducer.
        with tempfile.TemporaryFile() as errors:
            producer = subprocess.Popen(command + ["--where", "status=failed", runtime_fixture], cwd=work,
                                        env=runtime_env if image is None else None, stdout=subprocess.PIPE, stderr=errors)
            consumer = subprocess.run(command + ["--count"], stdin=producer.stdout, cwd=work,
                                      env=runtime_env if image is None else None, capture_output=True, timeout=30)
            producer.stdout.close()
            producer_status = producer.wait(timeout=30)
            errors.seek(0)
            producer_stderr = errors.read()
        passed = producer_status == consumer.returncode == 0 and consumer.stdout == b"2\n" and not (producer_stderr or consumer.stderr)
        report["cases"].append({"name": "filter-to-count-pipeline", "producer_exit_status": producer_status,
                                "consumer_exit_status": consumer.returncode, "verified": passed})
        if not passed:
            raise AssertionError("Offline filter-to-count pipeline failed")
        run("empty-stdin", ["--count"], b"0\n", data=b"")
        assert package_release.sha256(fixture) == fixture_hash
        assert package_release.sha256(installed) == manifest["binary_sha256"]
        assert package_release.sha256(archive) == report["archive_sha256"]
        report["input_binary_archive_hashes_unchanged"] = True
        report["verified"] = True
    finally:
        destination.write_text(json.dumps(report, indent=2) + "\n")
        if image:
            subprocess.run(["docker", "image", "rm", image], check=True)
    print(f"Verified offline release archive: {destination}", flush=True)


def main():
    """Require an archive and a fresh external installation directory on the native target."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.work_dir:
        work = args.work_dir.resolve()
        if work.is_relative_to(ROOT):
            parser.error("Keep installation tests outside the checkout")
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="jlog-release-"))
    destination = args.report.resolve() if args.report else work / "release.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    verify(args.archive.resolve(strict=True), work, destination)


if __name__ == "__main__":
    main()
