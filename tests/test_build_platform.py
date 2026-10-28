"""Verify that prepared-platform reuse rejects stale or altered build artifacts."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_platform


class PreparedPlatformTests(unittest.TestCase):
    def test_artifact_corruption_is_not_reused(self):
        """A changed host library must force a verified rebuild instead of stale reuse."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "libhost.a"
            library.write_bytes(b"tested host")
            manifest = {"identity": "pinned inputs", "target": "arm64mac",
                        "files_sha256": {"libhost.a": hashlib.sha256(library.read_bytes()).hexdigest()}}
            (root / build_platform.MARKER).write_text(json.dumps(manifest))
            self.assertEqual(build_platform.prepared(root, "pinned inputs", "arm64mac"), manifest)
            library.write_bytes(b"different host")
            self.assertIsNone(build_platform.prepared(root, "pinned inputs", "arm64mac"))

    def test_other_inputs_or_target_are_not_reused(self):
        """Unchanged artifacts built with another patch or architecture cannot satisfy the pin."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "main.roc"
            source.write_bytes(b"platform")
            manifest = {"identity": "old patch", "target": "arm64mac",
                        "files_sha256": {"main.roc": hashlib.sha256(source.read_bytes()).hexdigest()}}
            (root / build_platform.MARKER).write_text(json.dumps(manifest))
            self.assertIsNone(build_platform.prepared(root, "new patch", "arm64mac"))
            self.assertIsNone(build_platform.prepared(root, "old patch", "x64musl"))


if __name__ == "__main__":
    unittest.main()
