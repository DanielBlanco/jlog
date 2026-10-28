"""Require matching native archive smoke evidence before finalizing a release set."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import finalize_release


class ReleaseSetTests(unittest.TestCase):
    def setUp(self):
        """Describe two independently verified native targets from one unchanged source tree."""
        self.reports = []
        for target in ("arm64mac", "x64musl"):
            self.reports.append({"target": target, "version": "0.1.0", "source_sha256": {"src/main.roc": "source"},
                                 "platform_identity": "platform", "license_sha256": "license",
                                 "notices_sha256": "notices", "support_sha256": "support",
                                 "verified": True})

    def test_requires_both_distinct_native_targets(self):
        """Two macOS results cannot stand in for a missing native Linux archive check."""
        finalize_release.verify_set(self.reports)
        with self.assertRaisesRegex(ValueError, "both native targets"):
            finalize_release.verify_set([self.reports[0], self.reports[0]])

    def test_rejects_failed_archive_verification(self):
        """An explicitly failed smoke report blocks the final release manifest."""
        reports = copy.deepcopy(self.reports)
        reports[1]["verified"] = False
        with self.assertRaisesRegex(ValueError, "verified"):
            finalize_release.verify_set(reports)

    def test_rejects_mixed_release_inputs(self):
        """Passing targets must agree on source, version, platform, license, notices and support policy."""
        for key in ("version", "source_sha256", "platform_identity", "license_sha256", "notices_sha256", "support_sha256"):
            reports = copy.deepcopy(self.reports)
            reports[1][key] = "different"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "differ"):
                finalize_release.verify_set(reports)


if __name__ == "__main__":
    unittest.main()
