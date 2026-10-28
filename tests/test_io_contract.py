"""Strict descriptor conformance gate, including the patched host's exit-3 regressions.

Run explicitly with JLOG_BIN and unittest discovery using this filename. These
assert the specified exit-3 behavior, without skips or expected-failure markers.
The ordinary test_cli.py suite also covers broken pipes and real read failures.
"""
import errno
import os
from pathlib import Path
import subprocess
import unittest


class DescriptorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Resolve the explicitly selected executable without building implicitly."""
        cls.binary = str(Path(os.environ['JLOG_BIN']).resolve(strict=True))

    def test_write_only_stdin(self):
        """Require read errors from a descriptor proven unreadable by os.read."""
        for operation in [(), ('--count',), ('--tail', '1'), ('--where', 'x=y')]:
            with self.subTest(operation=operation):
                read_fd, write_fd = os.pipe()
                try:
                    with self.assertRaises(OSError) as error:
                        os.read(write_fd, 1)
                    self.assertEqual(error.exception.errno, errno.EBADF)
                    result = subprocess.run([self.binary, *operation], stdin=write_fd,
                                            capture_output=True, timeout=5)
                finally:
                    os.close(read_fd)
                    os.close(write_fd)
                self.assertEqual(result.returncode, 3)
                self.assertEqual(result.stdout, b'')
                self.assertIn(b'jlog: <stdin>:', result.stderr)

    def test_read_only_stdout(self):
        """Require exit 3 when stdout cannot accept bytes, including information modes."""
        for operation in [('--help',), ('--version',), (), ('--count',),
                          ('--tail', '1'), ('--where', 'x=y')]:
            with self.subTest(operation=operation):
                descriptor = os.open(os.devnull, os.O_RDONLY)
                try:
                    with self.assertRaises(OSError) as error:
                        os.write(descriptor, b'x')
                    self.assertEqual(error.exception.errno, errno.EBADF)
                    result = subprocess.run([self.binary, *operation], input=b'{"x":"y"}\n',
                                            stdout=descriptor, stderr=subprocess.PIPE, timeout=5)
                finally:
                    os.close(descriptor)
                self.assertEqual(result.returncode, 3)

    def test_read_only_stderr(self):
        """Require diagnostic/progress write errors to override other exit categories."""
        for operation, data in [(('--unknown',), b''), (('--progress',), b'{}\n'),
                                (('--count',), b'bad\n{}\n'),
                                (('--tail', '1'), b'bad\n{}\n'),
                                (('--where', 'x=y'), b'bad\n')]:
            with self.subTest(operation=operation):
                descriptor = os.open(os.devnull, os.O_RDONLY)
                try:
                    with self.assertRaises(OSError) as error:
                        os.write(descriptor, b'x')
                    self.assertEqual(error.exception.errno, errno.EBADF)
                    result = subprocess.run([self.binary, *operation], input=data,
                                            stdout=subprocess.PIPE, stderr=descriptor, timeout=5)
                finally:
                    os.close(descriptor)
                self.assertEqual(result.returncode, 3)
                self.assertEqual(result.stdout, b'')


if __name__ == '__main__':
    unittest.main()
