"""Check resource-unit normalization against independent native-tool examples."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("measure_resources", Path(__file__).with_name("measure_resources.py"))
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


class TimingTests(unittest.TestCase):
    def test_linux_verbose_units_and_elapsed(self):
        """Convert GNU time's KiB and h:mm:ss output to bytes and seconds."""
        text = ("Command exited with non-zero status 4\n"
                "\tUser time (seconds): 1.25\n"
                "\tSystem time (seconds): 0.05\n"
                "\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:02:03.45\n"
                "\tMaximum resident set size (kbytes): 1234\n")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.txt"
            path.write_text(text)
            self.assertEqual(measure.parse_usage(path), {
                "real_seconds": 3723.45, "user_seconds": 1.25,
                "system_seconds": 0.05, "max_rss_bytes": 1263616,
            })

    def test_macos_units_remain_bytes(self):
        """Preserve the existing macOS format and byte-sized RSS interpretation."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.txt"
            path.write_text("        0.25 real 0.20 user 0.01 sys\n"
                            "             1234  maximum resident set size\n")
            self.assertEqual(measure.parse_usage(path), {
                "real_seconds": 0.25, "user_seconds": 0.20,
                "system_seconds": 0.01, "max_rss_bytes": 1234,
            })

    def test_invalid_timing_is_not_zero_measurement(self):
        """Reject incomplete timing data instead of inventing a zero RSS result."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.txt"
            path.write_text("time: measurement unavailable\n")
            with self.assertRaises(ValueError):
                measure.parse_usage(path)


if __name__ == "__main__":
    unittest.main()
