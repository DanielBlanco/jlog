"""Measure the optimized CLI on macOS/Linux; keep fixtures outside the checkout."""
import argparse
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import tempfile
import time
import re


def digest_file(path):
    """Hash a file incrementally without retaining its contents in the runner."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(index, width):
    """Construct a known valid fixture record of exactly width bytes including LF."""
    status = "failed" if index % 2 == 0 else "passed"
    prefix = f'{{"seq":"{index:012d}","status":"{status}","payload":"'.encode()
    suffix = b'"}\n'
    padding = width - len(prefix) - len(suffix)
    if padding < 0:
        raise ValueError("Record width is too small")
    return prefix + b"x" * padding + suffix


def make_fixture(root, name, count, width, invalid=False):
    """Write generated records and golden hashes from known fixture templates."""
    path = root / (name + ".jsonl")
    digest = hashlib.sha256()
    selected = hashlib.sha256()
    bad = b"!" + b"x" * (width - 2) + b"\n"
    with path.open("xb") as handle:
        for index in range(count):
            body = bad if invalid else record(index, width)
            handle.write(body)
            digest.update(body)
            if not invalid and index % 2 == 0:
                selected.update(body)
    return {"name": name, "path": str(path), "records": count,
            "bytes": path.stat().st_size, "max_body_bytes": width - 1,
            "record_bytes": width, "invalid": invalid, "sha256": digest.hexdigest(),
            "selected_sha256": selected.hexdigest()}


def diagnostics(label, count, inspection):
    """Specify capped expected diagnostics for the deliberately all-invalid fixture."""
    prefix = "  line " if inspection else f"jlog: {label}: line "
    text = "".join(f"{prefix}{number}: invalid JSON\n"
                   for number in range(1, min(count, 100) + 1))
    if count > 100:
        text += (f"  ... {count - 100} more invalid records\n" if inspection
                 else f"jlog: {label}: {count - 100} more invalid records\n")
    return text.encode()


def expected_output(fixture, mode, tail_n, label):
    """Specify byte counts/hashes for known fixtures; never parse or buffer JSON input."""
    count = fixture["records"]
    invalid = count if fixture["invalid"] else 0
    valid = count - invalid
    stderr = diagnostics(label, invalid, False) if invalid and mode != "inspect" else b""
    if mode == "inspect":
        stdout = (f"File: {label}\nRecords: {count}\nValid: {valid}\nInvalid: {invalid}\n").encode()
        if invalid:
            stdout += b"\nMalformed records:\n" + diagnostics(label, invalid, True)
    elif mode == "count":
        stdout = f"{valid}\n".encode()
    elif mode == "filter":
        return {"status": 4 if invalid else 0, "stdout_bytes": ((count + 1) // 2) * fixture["record_bytes"] if valid else 0,
                "stdout_sha256": fixture["selected_sha256"], "stderr": stderr}
    else:
        retained = min(tail_n, valid)
        digest = hashlib.sha256()
        for index in range(count - retained, count):
            digest.update(record(index, fixture["record_bytes"]))
        return {"status": 4 if invalid else 0,
                "stdout_bytes": retained * fixture["record_bytes"],
                "stdout_sha256": digest.hexdigest(), "stderr": stderr}
    return {"status": 4 if invalid else 0, "stdout_bytes": len(stdout),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr": stderr}


def parse_usage(path):
    """Normalize macOS byte RSS and GNU time KiB RSS to the same byte unit."""
    text = path.read_text()
    times = re.search(r"([0-9.]+) real\s+([0-9.]+) user\s+([0-9.]+) sys", text)
    rss = re.search(r"(\d+)\s+maximum resident set size", text)
    if times is not None and rss is not None:
        return {"real_seconds": float(times[1]), "user_seconds": float(times[2]),
                "system_seconds": float(times[3]), "max_rss_bytes": int(rss[1])}
    user = re.search(r"User time \(seconds\):\s*([0-9.]+)", text)
    system = re.search(r"System time \(seconds\):\s*([0-9.]+)", text)
    elapsed = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([0-9:.]+)", text)
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
    if any(value is None for value in (user, system, elapsed, rss)):
        raise ValueError(f"Unrecognized native time output: {path}")
    seconds = 0.0
    for component in elapsed[1].split(":"):
        seconds = seconds * 60 + float(component)
    return {"real_seconds": round(seconds, 6), "user_seconds": float(user[1]),
            "system_seconds": float(system[1]), "max_rss_bytes": int(rss[1]) * 1024}


def host_metadata():
    """Record measured OS/CPU/stack context, including Linux container limits."""
    common = {"platform": platform.platform(), "architecture": platform.machine(),
            "page_size_bytes": os.sysconf("SC_PAGE_SIZE"), "logical_cpus": os.cpu_count(),
            "stack_soft_limit_bytes": resource.getrlimit(resource.RLIMIT_STACK)[0],
            "roc": subprocess.check_output(["roc", "version"], text=True).strip()}
    if sys.platform == "darwin":
        hardware = subprocess.check_output(
            ["sysctl", "-n", "hw.model", "hw.memsize", "machdep.cpu.brand_string"], text=True).splitlines()
        return {**common, "hardware_model": hardware[0], "memory_bytes": int(hardware[1]),
                "cpu": hardware[2], "macos": subprocess.check_output(["sw_vers"], text=True).strip()}
    cpuinfo = Path("/proc/cpuinfo").read_text()
    cpu = re.search(r"^(?:model name|Hardware|Processor)\s*:\s*(.+)", cpuinfo, re.M)
    memory = re.search(r"^MemTotal:\s*(\d+) kB", Path("/proc/meminfo").read_text(), re.M)
    limits = {}
    for name in ("memory.max", "memory.swap.max", "cpu.max"):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            limits[name] = path.read_text().strip()
    return {**common, "cpu": cpu[1] if cpu else "Not reported by guest",
            "memory_bytes": int(memory[1]) * 1024, "cgroup_limits": limits,
            "linux_os_release": Path("/etc/os-release").read_text().strip(),
            "timing_tool": subprocess.check_output(["/usr/bin/time", "--version"], text=True).strip()}


def case_name(fixture_name, mode, source, tail_n):
    """Name a measurement consistently for output artifacts and case selection."""
    return f"{fixture_name}-{source}-{mode}" + (f"-{tail_n}" if mode == "tail" else "")


def run_case(binary, root, fixture, mode, source, tail_n, timeout):
    """Time one actual CLI process, assert golden results, and discard verified stdout."""
    name = case_name(fixture["name"], mode, source, tail_n)
    stdout_path, stderr_path, usage_path = [root / (name + suffix) for suffix in (".stdout", ".stderr", ".time")]
    operation = {"inspect": [], "count": ["--count"], "filter": ["--where", "status=failed"],
                 "tail": ["--tail", str(tail_n)]}[mode]
    args = [str(binary), *operation, fixture["path"]] if source == "file" else [str(binary), *operation]
    expected = expected_output(fixture, mode, tail_n, fixture["path"] if source == "file" else "<stdin>")
    started = time.perf_counter()
    timed_out = False
    with Path(fixture["path"]).open("rb") as input_handle, stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        flag = "-l" if sys.platform == "darwin" else "-v"
        process = subprocess.Popen(["/usr/bin/time", flag, "-o", str(usage_path), *args],
                                   stdin=input_handle if source == "stdin" else subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, start_new_session=True,
                                   env=dict(os.environ, LC_ALL="C"))
        try:
            status = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            status = process.wait()
    elapsed = time.perf_counter() - started
    usage = parse_usage(usage_path) if not timed_out else {}
    actual_hash = digest_file(stdout_path)
    actual_bytes = stdout_path.stat().st_size
    verified = (not timed_out and status == expected["status"]
                and actual_bytes == expected["stdout_bytes"] and actual_hash == expected["stdout_sha256"]
                and stderr_path.read_bytes() == expected["stderr"])
    result = {"name": name, "fixture": fixture["name"], "source": source, "mode": mode,
              "tail_n": tail_n if mode == "tail" else None, "command": args, **usage,
              "elapsed_seconds": round(elapsed, 6), "exit_status": status,
              "timed_out": timed_out, "verified": verified,
              "stdout_bytes": actual_bytes, "stdout_sha256": actual_hash,
              "stderr_bytes": stderr_path.stat().st_size,
              "stderr_sha256": digest_file(stderr_path), "raw_usage": str(usage_path)}
    if verified:
        stdout_path.unlink()
    return result


def run_matrix(binary, root, sizes, tail_sizes, long_lines, timeout, selection, environment):
    """Generate temporary fixtures and execute measurements sequentially without overlap."""
    report = {"schema_version": 1, "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "host": host_metadata(), "binary_path": str(binary), "binary_sha256": digest_file(binary),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "parameters": {"sizes": sizes, "tail_sizes": tail_sizes, "long_line_body_bytes": long_lines,
                             "record_bytes": 1024, "timeout_seconds": timeout, "repetitions": 1,
                             "case_selection": selection},
              "method": "Sequential warm-cache runs; stdin is redirected from the same fixture. Native OS time RSS/CPU excludes the Python parent. Golden output is hashed outside the timed child.",
              "execution_environment": environment,
              "fixtures": [], "runs": []}
    cases = []

    def add_fixture(name, count, width, invalid, modes):
        """Generate only fixtures required by selected measurements, then queue them."""
        selected = [(mode, source, n) for source in ("file", "stdin") for mode, n in modes
                    if fnmatch.fnmatchcase(case_name(name, mode, source, n), selection)]
        if not selected:
            return
        print(f"Generating {name} ({count * width} bytes)", flush=True)
        fixture = make_fixture(root, name, count, width, invalid)
        report["fixtures"].append(fixture)
        cases.extend((fixture, mode, source, n) for mode, source, n in selected)

    for count in sizes:
        for invalid in (False, True):
            name = f'{"invalid" if invalid else "valid"}-{count}'
            limits = sorted({0, max(tail_sizes)}) if invalid else tail_sizes
            modes = [("inspect", 0), ("count", 0), ("filter", 0), *[("tail", n) for n in limits]]
            add_fixture(name, count, 1024, invalid, modes)
    for width in long_lines:
        add_fixture(f"long-{width}", 1, width + 1, False,
                    [("inspect", 0), ("count", 0), ("filter", 0), ("tail", 1)])
    add_fixture("tiny-max-n", 2, 1024, False, [("tail", 4294967295)])
    if not cases:
        raise ValueError(f"No measurements match {selection!r}")
    destination = root / "results.json"
    for index, (fixture, mode, source, n) in enumerate(cases, 1):
        print(f'[{index}/{len(cases)}] {fixture["name"]} {source} {mode} {n if mode == "tail" else ""}', flush=True)
        result = run_case(binary, root, fixture, mode, source, n, timeout)
        report["runs"].append(result)
        destination.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: result.get(key) for key in
                          ("elapsed_seconds", "max_rss_bytes", "exit_status", "verified", "timed_out")}), flush=True)
        if not result["verified"]:
            raise RuntimeError(f"Failed result or timeout; inspect {destination} and raw artifacts")
    for fixture in report["fixtures"]:
        if digest_file(Path(fixture["path"])) != fixture["sha256"]:
            raise RuntimeError(f'Input changed: {fixture["path"]}')
    if digest_file(binary) != report["binary_sha256"]:
        raise RuntimeError("The measured binary changed during the run")
    report["input_and_binary_hashes_verified"] = True
    report["runner_sha256"] = digest_file(Path(__file__))
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified {len(cases)} measurements: {destination}", flush=True)


def main():
    """Parse measurement settings and require a fresh external artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100000, 1000000])
    parser.add_argument("--tail-sizes", nargs="+", type=int, default=[0, 1, 64, 4096, 16384])
    parser.add_argument("--long-lines", nargs="+", type=int, default=[1048576, 8388608])
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--cases", default="*", help="Run only measurement names matching this shell-style pattern")
    parser.add_argument("--environment", type=Path, help="Additional JSON provenance such as Docker engine/image/physical host details")
    args = parser.parse_args()
    if sys.platform not in ("darwin", "linux"):
        parser.error("This runner requires macOS time -l or Linux GNU time -v")
    if min(args.sizes) < 1 or min(args.tail_sizes) < 0 or max(args.tail_sizes) > 4294967295 or min(args.long_lines) < 128 or args.timeout <= 0:
        parser.error("Counts/timeouts must be positive; tail N must fit U32; long bodies must be at least 128 bytes")
    binary = args.binary.resolve(strict=True)
    checkout = Path(__file__).resolve().parents[1]
    if args.work_dir is None:
        parent = "/private/tmp" if sys.platform == "darwin" else tempfile.gettempdir()
        root = Path(tempfile.mkdtemp(prefix="jlog-m4-resources-", dir=parent))
    else:
        root = args.work_dir.resolve()
        if root.is_relative_to(checkout):
            parser.error("Keep generated fixtures and outputs outside the checkout")
        root.mkdir(parents=True, exist_ok=False)
    print(f"Artifacts: {root}", flush=True)
    environment = json.loads(args.environment.read_text()) if args.environment else {}
    run_matrix(binary, root, args.sizes, args.tail_sizes, args.long_lines, args.timeout, args.cases, environment)


if __name__ == "__main__":
    main()
