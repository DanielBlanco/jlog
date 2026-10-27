"""Execute README usage/install blocks against an explicitly supplied optimized binary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    """Hash copied inputs and installed executables without retaining their contents."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fenced_sections(text):
    """Read fenced blocks by heading while ignoring shell comments inside fences."""
    sections = {}
    heading, language, body = "", None, []
    for line in text.splitlines():
        if language is not None:
            if line == "```":
                sections.setdefault(heading, []).append((language, "\n".join(body) + "\n"))
                language, body = None, []
            else:
                body.append(line)
        elif line.startswith("```"):
            language = line[3:]
        elif re.match(r"^#{1,6} ", line):
            heading = line.split(" ", 1)[1]
    return sections


def run_examples(binary, work, destination, source_checks=False):
    """Run actual documented commands in an isolated workspace and preserve verification evidence."""
    readme = ROOT / "README.md"
    readme_text = readme.read_text()
    sections = fenced_sections(readme_text)
    help_text = (ROOT / "src/help.txt").read_bytes()
    version = b"jlog 0.1.0\n"
    (work / "dist").mkdir()
    (work / "tests").mkdir()
    shutil.copy2(binary, work / "dist/jlog")
    for name in ("sample.jsonl", "sample-big.jsonl"):
        shutil.copyfile(ROOT / "tests" / name, work / "tests" / name)
    sample = (work / "tests/sample.jsonl").read_bytes()
    big = (work / "tests/sample-big.jsonl").read_bytes()
    fixture_hashes = {name: sha256(work / "tests" / name)
                      for name in ("sample.jsonl", "sample-big.jsonl")}
    install_prefix = work / "install prefix with spaces"
    environment = dict(os.environ, LC_ALL="C", JLOG_INSTALL_PREFIX=str(install_prefix))
    report = {"schema_version": 1, "host": platform.platform(), "architecture": platform.machine(),
              "readme_sha256": sha256(readme), "binary_sha256": sha256(binary),
              "fixture_sha256": fixture_hashes, "work_dir": str(work),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"), "cases": [], "source_checks": []}

    def block(heading, index=0, language="sh"):
        """Select a required published block; missing documentation is a verification failure."""
        return [body for lang, body in sections[heading] if lang == language][index]

    def inspect(label, count):
        """Specify the complete report for the known all-valid example inputs."""
        return f"File: {label}\nRecords: {count}\nValid: {count}\nInvalid: 0\n".encode()

    def check(name, script, stdout, stderr=b"", status=0, shell="/bin/bash", cwd=None, env=None):
        """Execute one documented block and retain exact stream/status checks, including failures."""
        command = [shell, "-f", "-e", "-c", script] if shell.endswith("zsh") else [shell, "--noprofile", "--norc", "-e", "-c", script]
        result = subprocess.run(command, cwd=cwd or work, env=env or environment,
                                capture_output=True, timeout=30)
        stderr_ok = stderr(result.stderr) if callable(stderr) else result.stderr == stderr
        verified = result.returncode == status and result.stdout == stdout and stderr_ok
        report["cases"].append({"name": name, "shell": shell, "script": script,
                                "exit_status": result.returncode, "expected_status": status,
                                "stdout_bytes": len(result.stdout), "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                                "stderr": result.stderr.decode(errors="replace"), "verified": verified})
        destination.write_text(json.dumps(report, indent=2) + "\n")
        print(f"{name}: {'PASS' if verified else 'FAIL'} (exit {result.returncode})", flush=True)
        if not verified:
            raise AssertionError(f"README block failed: {name}; inspect {destination}")

    check("quick-start", block("Quick start"), block("Quick start", language="text").encode())
    events = (work / "events.jsonl").read_bytes()
    check("inspect-help-version", block("Inspect a file"), inspect("events.jsonl", 2) + help_text + version)
    for name in ("-events.jsonl", "-"):
        (work / name).write_bytes(events)
    check("literal-filenames", block("Inspect a file", 1), inspect("-events.jsonl", 2) + inspect("./-", 2))
    check("stdin-forms", block("Read from stdin"), inspect("<stdin>", 2) * 3)
    check("redirect-report", block("Read from stdin", 1), b"")
    assert (work / "report.txt").read_bytes() == inspect("events.jsonl", 2)

    def progress_matches(stderr):
        """Accept optional periodic updates while requiring every documented EOF count."""
        lines = stderr.splitlines(keepends=True)
        complete = [line for line in lines if b"(complete)" in line]
        return (all(re.fullmatch(rb"jlog: \d+ lines inspected, \d+ invalid(?: \(complete\))?\n", line) for line in lines)
                and complete == [f"jlog: {n} lines inspected, 0 invalid (complete)\n".encode() for n in (6, 2, 2)])

    check("inspection-progress", block("Show inspection progress"), inspect("tests/sample.jsonl", 6) + inspect("<stdin>", 2), progress_matches)
    check("malformed-report", block("Find malformed records"), block("Find malformed records", language="text").encode(), status=4)
    documented_count = re.search(r"The sample prints `(\d+)`", readme_text)[1].encode()
    check("count", block("Count valid records"), documented_count + b"\n2\n")
    suffix = b"".join(sample.splitlines(keepends=True)[-2:])
    check("tail", block("Show the last valid records"), suffix * 2)
    assert (work / "recent.jsonl").read_bytes() == events
    selected = b"".join(line for line in big.splitlines(keepends=True) if json.loads(line).get("status") == "failed")
    documented_matches = re.search(r"The pipeline prints `(\d+)`", readme_text)[1].encode()
    check("filter-pipeline", block("Filter by a string field"), selected + documented_matches + b"\n")
    assert (work / "failed.jsonl").read_bytes() == selected
    capture_status = block("Use exit codes in scripts")
    mixed = (work / "mixed.jsonl").read_bytes()
    check("capture-valid-status", capture_status, b"All records are valid.\n")
    (work / "events.jsonl").write_bytes(mixed)
    check("capture-malformed-status", capture_status, b"Malformed records found; see report.txt.\n")
    (work / "events.jsonl").write_bytes(events)
    pipeline = block("Preserve pipeline failures")
    diagnostics = b"jlog: mixed.jsonl: line 2: blank line\njlog: mixed.jsonl: line 3: invalid JSON\n"
    check("pipeline-malformed-status", pipeline, b"0\n", diagnostics, 4)
    check("pipeline-without-pipefail", pipeline.replace("set -o pipefail\n", "", 1), b"0\n", diagnostics)
    if platform.system() == "Darwin":
        check("zsh-capture-valid-status", capture_status, b"All records are valid.\n", shell="/bin/zsh")
        (work / "events.jsonl").write_bytes(mixed)
        check("zsh-capture-malformed-status", capture_status, b"Malformed records found; see report.txt.\n", shell="/bin/zsh")
        (work / "events.jsonl").write_bytes(events)
        check("zsh-pipeline-malformed-status", pipeline, b"0\n", diagnostics, 4, shell="/bin/zsh")
    check("user-install", block("Install the executable"), version)
    installed = install_prefix / "bin/jlog"
    assert sha256(installed) == report["binary_sha256"]
    assert installed.stat().st_mode & 0o777 == 0o755
    installed_script = """if command -v roc >/dev/null || command -v rustc >/dev/null; then exit 99; fi
jlog --version
jlog --help
printf '%s\\n' '{"status":"failed"}' '{"status":"ok"}' | jlog --where status=failed | jlog --count
"""
    check("installed-without-toolchain-on-path", installed_script, version + help_text + b"1\n",
          cwd=install_prefix, env=dict(environment, PATH=str(install_prefix / "bin")))
    if source_checks:
        def source_check(name, script, stdout_contains=b"", stderr_contains=b""):
            """Explicitly execute documented source commands and retain compiler/test logs."""
            result = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-e", "-c", script],
                                    cwd=ROOT, env=environment, capture_output=True, timeout=300)
            (work / f"source-{name}.stdout").write_bytes(result.stdout)
            (work / f"source-{name}.stderr").write_bytes(result.stderr)
            verified = (result.returncode == 0 and stdout_contains in result.stdout
                        and stderr_contains in result.stderr)
            report["source_checks"].append({"name": name, "script": script,
                                            "exit_status": result.returncode, "verified": verified,
                                            "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr),
                                            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                                            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
            destination.write_text(json.dumps(report, indent=2) + "\n")
            print(f"source-{name}: {'PASS' if verified else 'FAIL'}", flush=True)
            if not verified:
                raise AssertionError(f"README source block failed: {name}; inspect {work}")

        source_check("build", block("Build an optimized executable"), stdout_contains=version)
        source_check("run-check-format", block("Run locally and check sources"), stdout_contains=help_text)
        source_check("development-progress", block("Show inspection progress", 1),
                     stdout_contains=inspect("tests/sample-big.jsonl", 12000),
                     stderr_contains=b"jlog: 12000 lines inspected, 0 invalid (complete)\n")
        source_check("dev-and-speed-regressions", block("Test development and optimized builds"), stderr_contains=b"OK\n")
        # The focused descriptor command is the following block under the same heading.
        source_check("strict-descriptors", block("Test development and optimized builds", 1), stderr_contains=b"OK\n")
        report["source_built_binary_sha256"] = sha256(ROOT / "dist/jlog")
    assert sha256(binary) == report["binary_sha256"]
    assert sha256(work / "dist/jlog") == report["binary_sha256"]
    assert all(sha256(work / "tests" / name) == digest for name, digest in fixture_hashes.items())
    report["installed_binary_sha256"] = sha256(installed)
    report["binary_and_fixture_hashes_verified"] = True
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified {len(report['cases'])} README/install cases and {len(report['source_checks'])} source blocks: {destination}", flush=True)


def main():
    """Require a tested binary and create a fresh external example/install workspace."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--source-checks", action="store_true",
                        help="Also execute documented Roc build/check/test blocks in this checkout")
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    if args.work_dir:
        work = args.work_dir.resolve()
        if work.is_relative_to(ROOT):
            parser.error("Keep example inputs/install outputs outside the checkout")
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="jlog-readme-"))
    destination = args.report.resolve() if args.report else work / "readme.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"README workspace: {work}", flush=True)
    run_examples(binary, work, destination, args.source_checks)


if __name__ == "__main__":
    main()
