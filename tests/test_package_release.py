"""Protect release gates against accidentally packaging unverified or altered executables."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import package_release
import verify_release


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        """Create minimal native evidence with every required gate and the current source identity."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        data = bytearray(64)
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 62)
        (self.root / "jlog-speed").write_bytes(data)
        lock, _, identity = package_release.build_platform.configuration()
        self.environment = {"target": "x64musl", "execution": "native",
                            "uname": ["Linux", "test", "kernel", "version", "x86_64"],
                            "source_hashes_unchanged": True, "platform_hashes_unchanged": True,
                            "roc": "Roc compiler version nightly-2026-10-09-258ab27",
                            "platform_build": {"identity": identity, "target": "x64musl",
                                               "patch_sha256": lock["patch"]["sha256"]},
                            "source_sha256": {str(p.relative_to(package_release.ROOT)): package_release.sha256(p)
                                              for p in (package_release.ROOT / "src").glob("*") if p.is_file()},
                            "binary_speed_sha256": package_release.sha256(self.root / "jlog-speed")}
        self.results = [{"name": name, "status": 0} for name in sorted(package_release.REQUIRED_CHECKS)]

    def verify(self, environment=None, results=None):
        """Write one evidence variant and invoke the production release gate."""
        (self.root / "environment.json").write_text(json.dumps(environment or self.environment))
        (self.root / "verification.json").write_text(json.dumps(self.results if results is None else results))
        return package_release.verified_build(self.root)

    def test_failed_or_missing_descriptor_gate_blocks_packaging(self):
        """Passing ordinary suites cannot hide either a failed or absent strict descriptor suite."""
        self.verify()
        for mode in ("dev", "speed"):
            with self.subTest(mode=mode):
                failed = copy.deepcopy(self.results)
                next(item for item in failed if item["name"] == f"io-contract-{mode}")["status"] = 1
                with self.assertRaisesRegex(ValueError, "strict I/O"):
                    self.verify(results=failed)
                with self.assertRaisesRegex(ValueError, "strict I/O"):
                    self.verify(results=[item for item in self.results if item["name"] != f"io-contract-{mode}"])

    def test_changed_binary_source_or_architecture_blocks_packaging(self):
        """Recorded success cannot authorize a replaced executable, changed sources or wrong target."""
        for change in ("binary_speed_sha256", "source_sha256", "execution", "uname"):
            environment = copy.deepcopy(self.environment)
            environment[change] = {"changed": "source"} if change == "source_sha256" else "changed"
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify(environment=environment)
        data = bytearray((self.root / "jlog-speed").read_bytes())
        struct.pack_into("<H", data, 18, 183)
        (self.root / "jlog-speed").write_bytes(data)
        self.environment["binary_speed_sha256"] = package_release.sha256(self.root / "jlog-speed")
        with self.assertRaisesRegex(ValueError, "executable"):
            self.verify()


class ArchiveContractTests(unittest.TestCase):
    def setUp(self):
        """Create a small archive fixture with independent expected content and executable mode."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.name = "jlog-0.1.0-linux-x86_64"
        self.archive = self.root / (self.name + ".tar.gz")
        data = bytearray(64)
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 62)
        self.files = {"bin/jlog": bytes(data), "LICENSE": b"test fixture", "INSTALL.md": b"instructions", "SUPPORT.md": b"support policy",
                      "THIRD_PARTY_NOTICES.md": b"notices", "licenses/example.txt": b"upstream notice"}

    def write_archive(self, executable_mode=0o755):
        """Write a fixture and its external checksum, optionally reproducing lost executable permissions."""
        manifest = {"version": "0.1.0", "target": "x64musl",
                    "binary_sha256": hashlib.sha256(self.files["bin/jlog"]).hexdigest(),
                    "files_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in self.files.items()}}
        files = dict(self.files, **{"BUILD.json": json.dumps(manifest).encode()})
        with tarfile.open(self.archive, "w:gz") as tar:
            for name, data in files.items():
                member = tarfile.TarInfo(f"{self.name}/{name}")
                member.size = len(data)
                member.mode = executable_mode if name == "bin/jlog" else 0o644
                tar.addfile(member, io.BytesIO(data))
        self.archive.with_suffix(".gz.sha256").write_text(f"{package_release.sha256(self.archive)}  {self.archive.name}\n")

    def test_corrupt_download_is_rejected(self):
        """An archive changed after checksumming must fail before extraction or execution."""
        self.write_archive()
        verify_release.unpack_checked(self.archive, self.root / "valid")
        with self.archive.open("ab") as handle:
            handle.write(b"changed download")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify_release.unpack_checked(self.archive, self.root / "invalid")

    def test_lost_executable_permissions_are_rejected(self):
        """A valid checksum cannot hide an incorrectly packaged executable mode."""
        self.write_archive(executable_mode=0o644)
        with self.assertRaisesRegex(ValueError, "permissions"):
            verify_release.unpack_checked(self.archive, self.root / "invalid")

    def test_missing_license_is_rejected(self):
        """A self-consistent file inventory still must include the required license and notices."""
        del self.files["LICENSE"]
        self.write_archive()
        with self.assertRaisesRegex(ValueError, "license"):
            verify_release.unpack_checked(self.archive, self.root / "invalid")


if __name__ == "__main__":
    unittest.main()
