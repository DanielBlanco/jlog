"""Executable checks; set JLOG_BIN to the binary under test (never built here)."""
import os
import errno
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest


HELP = (
    b'Usage: jlog [INPUT] [--count | --tail N | --where KEY=TEXT]\n'
    b'       jlog --help | --version\n'
    b'\n'
    b'INPUT is one file, or - for stdin (the default); use ./- for a file named -.\n'
    b'Options may precede or follow INPUT; -- ends option parsing.\n'
    b'No operation flag selects inspection and validation.\n'
    b'  --count          Count valid records.\n'
    b'  --tail N         Last N valid records; N is 0..4294967295.\n'
    b'  --where KEY=TEXT Match a literal top-level key against an exact JSON string.\n'
    b'                   Split at the first =; no type coercion or nested queries.\n'
    b'  --help, -h       Show help (standalone).\n'
    b'  --version, -V    Show version (standalone).\n'
    b'\n'
    b'Every physical line is validated; malformed lines are reported and processing\n'
    b'continues. Data stdout contains only results; diagnostics go to stderr.\n'
    b'Exit codes: 0 valid input; 1 internal/resource failure; 2 invalid arguments;\n'
    b'            3 input/output failure; 4 malformed JSONL.\n'
)


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = str(Path(os.environ['JLOG_BIN']).resolve(strict=True))

    def run_cli(self, *args, input_bytes=b''):
        return subprocess.run(
            [self.binary, *args], input=input_bytes, capture_output=True, timeout=5,
        )

    def test_m1_16_file_single_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'one.jsonl'
            path.write_bytes(b'{}\n')
            result = self.run_cli(str(path))
            self.assertEqual(result.stdout,
                             f'File: {path}\nRecords: 1\nValid: 1\nInvalid: 0\n'.encode())
            self.assertEqual((result.stderr, result.returncode), (b'', 0))

    def assert_file_report(self, data, report, status=0):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_bytes(data)
            result = self.run_cli(str(path))
            self.assertEqual(result.stdout, f'File: {path}\n'.encode() + report)
            self.assertEqual((result.stderr, result.returncode), (b'', status))
            self.assertEqual(path.read_bytes(), data)

    def test_m1_16_empty_and_eof(self):
        cases = [
            (b'', b'Records: 0\nValid: 0\nInvalid: 0\n', 0),
            (b'null', b'Records: 1\nValid: 1\nInvalid: 0\n', 0),
            (b'\n', b'Records: 1\nValid: 0\nInvalid: 1\n\nMalformed records:\n  line 1: blank line\n', 4),
        ]
        for data, report, status in cases:
            with self.subTest(data=data):
                self.assert_file_report(data, report, status)

    def test_m1_16_representative_and_malformed(self):
        representative = (
            b'{"status":"ok","skill":"Roc","detail":{"attempts":[1,2]}}\n'
            b'{"status":"failed","skill":"caf\xc3\xa9\\n\xce\xbb"}\n'
            b'{"status":"failed","skill":null}\n{"status":false}\n42\n'
        )
        self.assert_file_report(representative, b'Records: 5\nValid: 5\nInvalid: 0\n')
        self.assert_file_report(
            b'{}\n\nnot-json\nnull',
            b'Records: 4\nValid: 2\nInvalid: 2\n\nMalformed records:\n'
            b'  line 2: blank line\n  line 3: invalid JSON\n', 4,
        )

    def test_m1_16_values_unicode_precision(self):
        data = ('[]\n"café \u03bb🙂"\ntrue\nfalse\nnull\n'
                '340282366920938463463374607431768211456\n1e9999\n'
                '{"pair":"\\uD83D\\uDE42","x":1,"x":null}\n').encode()
        self.assert_file_report(data, b'Records: 8\nValid: 8\nInvalid: 0\n')

    def test_m1_16_crlf_and_numbering(self):
        self.assert_file_report(
            b'{}\r\n\r\nnull\r',
            b'Records: 3\nValid: 2\nInvalid: 1\n\nMalformed records:\n'
            b'  line 2: blank line\n', 4,
        )

    def test_m1_16_defects_and_recovery(self):
        data = (b'\xef\xbb\xbf{}\n\xff\n"\\uD800"\n' +
                b'[' * 129 + b'0' + b']' * 129 + b'\n' +
                b'{"unicode":"\xef\xbb\xbf"}\n\xef\xbb\xbf{}\nnull')
        self.assert_file_report(
            data, b'Records: 7\nValid: 2\nInvalid: 5\n\nMalformed records:\n'
            b'  line 1: BOM is not allowed\n  line 2: invalid UTF-8\n'
            b'  line 3: invalid JSON\n  line 4: nesting exceeds 128\n'
            b'  line 6: invalid JSON\n', 4,
        )
        self.assert_file_report(b'[' * 128 + b'0' + b']' * 128,
                                b'Records: 1\nValid: 1\nInvalid: 0\n')

    def test_m1_16_first_100_errors(self):
        expected = (b'Records: 102\nValid: 1\nInvalid: 101\n\nMalformed records:\n' +
                    b''.join(f'  line {n}: blank line\n'.encode() for n in range(1, 101)) +
                    b'  ... 1 more invalid records\n')
        self.assert_file_report(b'\n' * 101 + b'{}', expected, 4)

    def test_m1_16_native_path_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.fsencode(directory) + b'/native-\xc3\xa9.jsonl'
            with open(path, 'wb') as stream:
                stream.write(b'{}\n')
            result = self.run_cli(path)
            expected = ('File: ' + directory + '/native-\u00e9.jsonl\n'
                        'Records: 1\nValid: 1\nInvalid: 0\n').encode()
            self.assertEqual((result.stdout, result.stderr, result.returncode),
                             (expected, b'', 0))

    def test_m1_16_non_utf8_native_path(self):
        # Darwin's filesystem rejects this name before jlog can open a fixture.
        # Keep real non-UTF-8 opening acceptance on filesystems supporting it.
        parent = '/private/tmp' if sys.platform == 'darwin' else None
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            path = os.fsencode(directory) + b'/native-\xff.jsonl'
            try:
                with open(path, 'wb') as stream:
                    stream.write(b'{}\n')
            except OSError as error:
                if sys.platform != 'darwin' or error.errno != errno.EILSEQ:
                    raise
                result = self.run_cli(path)
                self.assertEqual((result.stdout, result.returncode), (b'', 3))
                self.assertIn(b'jlog: ', result.stderr)
                self.assertIn(b'native-', result.stderr)
            else:
                result = self.run_cli(path)
                expected = ('File: ' + directory + '/native-\ufffd.jsonl\n'
                            'Records: 1\nValid: 1\nInvalid: 0\n').encode()
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (expected, b'', 0))

    def test_m1_16_source_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'line\n\t\r\x01.jsonl'
            path.write_bytes(b'{}')
            result = self.run_cli(str(path))
            expected = (f'File: {directory}/line\\n\\t\\r\\u0001.jsonl\n'
                        'Records: 1\nValid: 1\nInvalid: 0\n').encode()
            self.assertEqual((result.stdout, result.stderr, result.returncode),
                             (expected, b'', 0))

    def test_m1_16_input_errors_suppress_report(self):
        self.assertNotEqual(os.geteuid(), 0, 'Permission test requires an unprivileged user')
        with tempfile.TemporaryDirectory() as directory:
            denied = Path(directory) / 'denied'
            denied.write_bytes(b'{}\n')
            denied.chmod(0)
            try:
                for path, category in [(Path(directory) / 'missing', b'not found'),
                                       (denied, b'permission denied'),
                                       (Path(directory), b'directory')]:
                    with self.subTest(path=path):
                        result = self.run_cli(str(path))
                        self.assertEqual((result.stdout, result.returncode), (b'', 3))
                        self.assertIn(os.fsencode(path), result.stderr)
                        self.assertIn(category, result.stderr.lower())
            finally:
                denied.chmod(0o600)

    def test_m1_17_stdin_empty(self):
        result = self.run_cli()
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'File: <stdin>\nRecords: 0\nValid: 0\nInvalid: 0\n', b'', 0))

    def assert_stdin_report(self, data, report, status=0):
        for args in [(), ('-',)]:
            with self.subTest(args=args):
                result = self.run_cli(*args, input_bytes=data)
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (b'File: <stdin>\n' + report, b'', status))

    def test_m1_17_stdin_records_and_eof(self):
        cases = [
            (b'', b'Records: 0\nValid: 0\nInvalid: 0\n', 0),
            (b'{}', b'Records: 1\nValid: 1\nInvalid: 0\n', 0),
            (b'{}\nnull\n', b'Records: 2\nValid: 2\nInvalid: 0\n', 0),
            (b'{}\r\n\xff\n\nnull',
             b'Records: 4\nValid: 2\nInvalid: 2\n\nMalformed records:\n'
             b'  line 2: invalid UTF-8\n  line 3: blank line\n', 4),
            (b'\n', b'Records: 1\nValid: 0\nInvalid: 1\n\nMalformed records:\n'
             b'  line 1: blank line\n', 4),
        ]
        for data, report, status in cases:
            with self.subTest(data=data):
                self.assert_stdin_report(data, report, status)
                self.assert_file_report(data, report, status)

    def test_m1_17_stdin_long_lines_and_unicode(self):
        cases = [
            b'"' + b'a' * 16382 + '🙂'.encode() + b'"\r\nnull',
            b'"' + b'a' * 16381 + b'"\r\nnull',
            b'"' + b'a' * 100000 + b'"\nnull',
        ]
        for data in cases:
            with self.subTest(length=len(data)):
                self.assert_stdin_report(data, b'Records: 2\nValid: 2\nInvalid: 0\n')
                self.assert_file_report(data, b'Records: 2\nValid: 2\nInvalid: 0\n')

    def test_m1_17_stdin_validation(self):
        data = b'\xef\xbb\xbf{}\n1e9999\n' + b'[' * 129 + b'0' + b']' * 129 + b'\n"\\uD800"\ntrue'
        report = (b'Records: 5\nValid: 2\nInvalid: 3\n\nMalformed records:\n'
                  b'  line 1: BOM is not allowed\n  line 3: nesting exceeds 128\n'
                  b'  line 4: invalid JSON\n')
        self.assert_stdin_report(data, report, 4)
        self.assert_file_report(data, report, 4)

    def test_m1_17_stdin_error_cap(self):
        expected = (b'Records: 101\nValid: 0\nInvalid: 101\n\nMalformed records:\n' +
                    b''.join(f'  line {n}: blank line\n'.encode() for n in range(1, 101)) +
                    b'  ... 1 more invalid records\n')
        self.assert_stdin_report(b'\n' * 101, expected, 4)

    def test_m1_18_preflight_with_stdin_held_open(self):
        cases = [
            (('--help',), HELP, 0), (('-h',), HELP, 0),
            (('--version',), b'jlog 0.1.0\n', 0),
            (('-V',), b'jlog 0.1.0\n', 0),
            (('--unknown',), b'', 2), (('--tail',), b'', 2),
            (('--where',), b'', 2), (('--help', 'extra'), b'', 2),
        ]
        for args, stdout, status in cases:
            with self.subTest(args=args):
                read_fd, write_fd = os.pipe()
                try:
                    # The parent keeps write_fd open: reading stdin would block.
                    result = subprocess.run([self.binary, *args], stdin=read_fd,
                                            capture_output=True, timeout=3)
                finally:
                    os.close(read_fd)
                    os.close(write_fd)
                self.assertEqual((result.stdout, result.returncode), (stdout, status))
                if status == 0:
                    self.assertEqual(result.stderr, b'')
                else:
                    self.assertIn(b'\nUsage: jlog ', result.stderr)

    def test_m1_18_usage_before_file_io(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / 'missing')
            for args in [(missing, '--unknown'), (missing, '--tail', '-1'),
                         ('--help', missing), ('--version', missing),
                         (missing, '--count', '--count')]:
                with self.subTest(args=args):
                    result = self.run_cli(*args)
                    self.assertEqual((result.stdout, result.returncode), (b'', 2))
                    self.assertIn(b'\nUsage: jlog ', result.stderr)
                    self.assertNotIn(b'not found', result.stderr)

    def test_m1_17_stdin_read_error_suppresses_report(self):
        with tempfile.TemporaryDirectory() as directory:
            # Verified to yield StdinErr(IsADirectory), unlike EBADF (host EOF).
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                result = subprocess.run([self.binary], stdin=descriptor,
                                        capture_output=True, timeout=3)
            finally:
                os.close(descriptor)
        self.assertEqual((result.stdout, result.returncode), (b'', 3))
        self.assertIn(b'jlog: <stdin>:', result.stderr)


    def test_m1_06_extra_information_arguments(self):
        result = self.run_cli('--help', 'extra')
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.startswith(b'jlog: '))
        self.assertIn(b'\nUsage: jlog ', result.stderr)

    def test_m1_06_help_alias(self):
        result = self.run_cli('-h')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (HELP, b'', 0))

    def test_m1_06_usage_regressions(self):
        cases = [
            ('-h', 'extra'), ('--version', 'extra'), ('-V', 'extra'),
            ('--help', '--count'), ('--help', '--version'),
            ('--field', 'skill'), ('--tail', '+1'), ('--count', '--count'),
            ('--where', 'missing'), ('--tail',), ('one', 'two'),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.startswith(b'jlog: '))
                self.assertIn(b'\nUsage: jlog ', result.stderr)

    def test_m1_05_invalid_utf8_text_regressions(self):
        for args in [(b'--where', b'a=\xff'), (b'--where=a=\xff',),
                     (b'--tail', b'1\xff'), (b'--\xff',)]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'\nUsage: jlog ', result.stderr)

    def test_m1_06_help(self):
        result = self.run_cli('--help')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (HELP, b'', 0))

    def test_m1_01_version_alias(self):
        result = self.run_cli('-V')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'jlog 0.1.0\n', b'', 0))

    def test_m1_01_version(self):
        result = self.run_cli('--version')
        self.assertEqual(result.stdout, b'jlog 0.1.0\n')
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
