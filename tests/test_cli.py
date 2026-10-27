"""Executable checks; set JLOG_BIN to the binary under test (never built here)."""
import os
import errno
import fcntl
import hashlib
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import select
import signal
import tempfile
import sys
import time
import unittest


HELP = (
    b'Usage: jlog [INPUT] [--progress] [--count | --tail N | --where KEY=TEXT]\n'
    b'       jlog --help | --version\n'
    b'\n'
    b'INPUT is one file, or - for stdin (the default); use ./- for a file named -.\n'
    b'Options may precede or follow INPUT; -- ends option parsing.\n'
    b'No operation flag selects inspection and validation.\n'
    b'  --progress       Show inspection progress on stderr (about once per second).\n'
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
        """Resolve the explicitly supplied executable once for the suite."""
        cls.binary = str(Path(os.environ['JLOG_BIN']).resolve(strict=True))

    def run_cli(self, *args, input_bytes=b''):
        """Run the selected binary with captured streams and a bounded timeout."""
        return subprocess.run(
            [self.binary, *args], input=input_bytes, capture_output=True, timeout=5,
        )

    def assert_file_and_stdin(self, data, operation, stdout, stderr=b'', status=0):
        """Check hand-specified bytes with source-label substitution and unchanged input."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'records.data'
            path.write_bytes(data)
            before = hashlib.sha256(data).digest()
            for args, source in [((*operation, str(path)), str(path)),
                                 ((str(path), *operation), str(path)),
                                 (operation, '<stdin>'), ((*operation, '-'), '<stdin>')]:
                with self.subTest(args=args):
                    result = self.run_cli(*args, input_bytes=data)
                    label = source.encode()
                    self.assertEqual((result.stdout, result.stderr, result.returncode),
                                     (stdout.replace(b'{source}', label),
                                      stderr.replace(b'{source}', label), status))
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_m4_01_published_representative_all_modes(self):
        """Execute the exact specification fixture for every mode and source form."""
        first = b'{"status":"ok","skill":"Roc","detail":{"attempts":[1,2]}}\n'
        selected = (b'{"status":"failed","skill":"caf\xc3\xa9\\n\xce\xbb"}\n'
                    b'{"status":"failed","skill":null}\n')
        suffix = b'{"status":false}\n42\n'
        data = first + selected + suffix
        for operation, stdout in [
                ((), b'File: {source}\nRecords: 5\nValid: 5\nInvalid: 0\n'),
                (('--count',), b'5\n'), (('--tail', '2'), suffix),
                (('--where', 'status=failed'), selected)]:
            with self.subTest(operation=operation):
                self.assert_file_and_stdin(data, operation, stdout)

    def test_m4_01_published_malformed_all_modes(self):
        """Execute the published malformed example with exact data-mode diagnostics."""
        diagnostics = (b'jlog: {source}: line 2: blank line\n'
                       b'jlog: {source}: line 3: invalid JSON\n')
        report = (b'File: {source}\nRecords: 4\nValid: 2\nInvalid: 2\n\n'
                  b'Malformed records:\n  line 2: blank line\n  line 3: invalid JSON\n')
        for operation, stdout, stderr in [
                ((), report, b''), (('--count',), b'2\n', diagnostics),
                (('--tail', '10'), b'{}\nnull\n', diagnostics),
                (('--where', 'status=failed'), b'', diagnostics)]:
            with self.subTest(operation=operation):
                self.assert_file_and_stdin(b'{}\n\nnot-json\nnull', operation,
                                           stdout, stderr, 4)

    def test_m4_01_validation_precedence_all_modes(self):
        """Share full validation and physical numbering across all operation callbacks."""
        selected = b'{"status":"failed","pair":"\\uD83D\\uDE42","n":1e9999}'
        deep = b'[' * 128 + b'0' + b']' * 128
        last = b'{"status":"failed","bom":"\xef\xbb\xbf"}'
        lines = [b'\xef\xbb\xbf\xff', b'\xef\xbb\xbf{}', b'[' * 129,
                 b' \t\r', b'"raw\tcontrol"', b'"\\uD800"', b'{}null',
                 selected, deep, last]
        data = b'\r\n'.join(lines)
        details = [(1, b'invalid UTF-8'), (2, b'invalid JSON'),
                   (3, b'nesting exceeds 128'), (4, b'blank line'),
                   (5, b'invalid JSON'), (6, b'invalid JSON'), (7, b'invalid JSON')]
        diagnostics = b''.join(b'jlog: {source}: line ' + str(n).encode() + b': ' + reason
                               + b'\n' for n, reason in details)
        report = (b'File: {source}\nRecords: 10\nValid: 3\nInvalid: 7\n\nMalformed records:\n'
                  + b''.join(f'  line {n}: '.encode() + reason + b'\n'
                             for n, reason in details))
        for operation, stdout, stderr in [
                ((), report, b''), (('--count',), b'3\n', diagnostics),
                (('--tail', '1'), last + b'\n', diagnostics),
                (('--tail', '0'), b'', diagnostics),
                (('--where', 'status=failed'), selected + b'\n' + last + b'\n', diagnostics)]:
            with self.subTest(operation=operation):
                self.assert_file_and_stdin(data, operation, stdout, stderr, 4)

    def test_m4_01_long_records_data_modes(self):
        """Preserve long UTF-8 records across stdin reads and flush final pending bytes."""
        first = (b' {"padding":"' + b'a' * 16368 + '🙂'.encode() + b'b' * 20000
                 + b'","status":"failed","message":"line\\nend"} ')
        nonmatch = b'{"status":"failed","status":null}'
        last = b'{"status":"failed","id":2}\r'
        data = first + b'\r\n' + nonmatch + b'\nbad\n' + last
        diagnostic = b'jlog: {source}: line 3: invalid JSON\n'
        for operation, stdout in [(('--count',), b'3\n'),
                                  (('--tail', '2'), nonmatch + b'\n' + last + b'\n'),
                                  (('--where', 'status=failed'), first + b'\n' + last + b'\n')]:
            with self.subTest(operation=operation):
                self.assert_file_and_stdin(data, operation, stdout, diagnostic, 4)

    def test_m4_01_data_diagnostics_escape_source(self):
        """Escape data-mode source labels and keep private malformed bodies out of stderr."""
        body = b'{"status":"failed"}\n'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'line\n\t\x7fλ.data'
            data = b'PRIVATE invalid input\n' + body
            source.write_bytes(data)
            diagnostic = (f'jlog: {directory}/line\\n\\t\\u007fλ.data: line 1: invalid JSON\n').encode()
            for operation, stdout in [(('--count',), b'1\n'),
                                      (('--tail', '1'), body),
                                      (('--where', 'status=failed'), body)]:
                with self.subTest(operation=operation):
                    result = self.run_cli(*operation, str(source))
                    self.assertEqual((result.stdout, result.stderr, result.returncode),
                                     (stdout, diagnostic, 4))
            self.assertEqual(source.read_bytes(), data)

    def test_m4_01_literal_paths_and_dash_operand(self):
        """Open literal option/dash filenames and consume a dash-leading filter operand."""
        body = b'{"-key":"-value"}\n'
        with tempfile.TemporaryDirectory() as directory:
            for name in ('-', '-events', '--count', 'events.anything'):
                (Path(directory) / name).write_bytes(body)
            for args, stdout in [
                    (('./-', '--count'), b'1\n'),
                    (('--tail=01', '--', '-events'), body),
                    (('--where', '-key=-value', '--', '--count'), body),
                    (('events.anything', '--count'), b'1\n')]:
                with self.subTest(args=args):
                    result = subprocess.run([self.binary, *args], cwd=directory,
                                            input=b'bad\n', capture_output=True, timeout=5)
                    self.assertEqual((result.stdout, result.stderr, result.returncode),
                                     (stdout, b'', 0))

    def test_m4_01_usage_does_not_read_stdin(self):
        """Reject the full tail boundary/operation conflict matrix before blocking input."""
        cases = [('--tail', value) for value in
                 ('-1', '+1', '1.0', '', ' 1', '1 ', '١', '4294967296')]
        cases.extend([('--tail=1', '--tail=1'), ('--tail=1', '--where=a=b'),
                      ('--where=a=b', '--count'), ('--where=a=b', '--where=a=b'),
                      ('--field=skill',), ('--count=value',)])
        for args in cases:
            with self.subTest(args=args):
                read_fd, write_fd = os.pipe()
                try:
                    result = subprocess.run([self.binary, *args], stdin=read_fd,
                                            capture_output=True, timeout=3)
                finally:
                    os.close(read_fd)
                    os.close(write_fd)
                self.assertEqual((result.stdout, result.returncode), (b'', 2))
                self.assertEqual(result.stderr,
                                 b"jlog: invalid arguments\nUsage: jlog [INPUT] [--progress] "
                                 b"[--count | --tail N | --where KEY=TEXT]\n"
                                 b"Try 'jlog --help' for help.\n")

    def test_m4_01_redirected_data_with_malformed_source(self):
        """Keep redirected tail/filter JSONL valid, exact, and numerically lossless."""
        first = b' {"status":"failed","n":9007199254740993} '
        last = b'{"status":"failed","n":1e9999}'
        data = first + b'\r\nbad\nnull\r\n' + last
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'events.data'
            source.write_bytes(data)
            before = hashlib.sha256(data).digest()
            for operation, expected in [(('--tail', '2'), b'null\n' + last + b'\n'),
                                        (('--where', 'status=failed'), first + b'\n' + last + b'\n')]:
                with self.subTest(operation=operation):
                    output = Path(directory) / 'selected.jsonl'
                    with output.open('wb') as handle:
                        result = subprocess.run([self.binary, *operation, str(source)],
                                                stdout=handle, stderr=subprocess.PIPE, timeout=5)
                    self.assertEqual((result.stderr, result.returncode),
                                     (f'jlog: {source}: line 2: invalid JSON\n'.encode(), 4))
                    self.assertEqual(output.read_bytes(), expected)
                    parsed = [json.loads(body, parse_float=Decimal)
                              for body in output.read_bytes().splitlines()]
                    self.assertEqual(len(parsed), 2)
                    self.assertEqual(parsed[-1]['n'], Decimal('1e9999'))
                    if operation[0] == '--where':
                        self.assertEqual(parsed[0]['n'], 9007199254740993)
                    self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_m4_01_sigterm_preserves_normal_termination(self):
        """Leave SIGTERM to the OS after proving a streaming filter is running."""
        process = subprocess.Popen([self.binary, '--where', 'status=failed'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        body = b'{"status":"failed"}\n'
        try:
            process.stdin.write(body)
            self.assertTrue(select.select([process.stdout], [], [], 3)[0])
            self.assertEqual(process.stdout.readline(), body)
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual((stdout, stderr, process.returncode),
                             (b'', b'', -signal.SIGTERM))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_m4_01_readme_sample(self):
        """Keep the README sample count, progress, and last two original bodies exact."""
        source = Path(__file__).resolve().parent / 'sample.jsonl'
        before = hashlib.sha256(source.read_bytes()).digest()
        report = f'File: {source}\nRecords: 6\nValid: 6\nInvalid: 0\n'.encode()
        tail = (
            b'{"timestamp":"2026-10-26T10:00:05Z","level":"error","status":"failed",'
            b'"skill":"Networking","message":"Connection failed\\nCheck the upstream service",'
            b'"details":{"attempt":2,"response":null}}\n'
            b'{"timestamp":"2026-10-26T10:00:06Z","level":"info","status":"ok",'
            b'"skill":"Roc","message":"Application stopped","details":{"processed":4,"failed":1}}\n'
        )
        for operation, stdout, stderr in [
                ((), report, b''), (('--count',), b'6\n', b''),
                (('--tail', '2'), tail, b''),
                (('--progress',), report, b'jlog: 6 lines inspected, 0 invalid (complete)\n')]:
            with self.subTest(operation=operation):
                result = self.run_cli(*operation, str(source))
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (stdout, stderr, 0))
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_m4_01_mid_read_failure_all_modes(self):
        """Inject real WouldBlock after a consumed prefix without closing the pipe."""
        selected = b'{"status":"failed","id":1}\n'
        prefix = b'bad\n' + selected + b'{"status":"failed"'
        for operation in [(), ('--progress',), ('--count',), ('--tail', '0'),
                          ('--tail', '2'), ('--where', 'status=failed')]:
            with self.subTest(operation=operation):
                read_fd, write_fd = os.pipe()
                try:
                    self.assertEqual(os.write(write_fd, prefix), len(prefix))
                    flags = fcntl.fcntl(read_fd, fcntl.F_GETFL)
                    fcntl.fcntl(read_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                    # Keep the writer open: exhausting buffered bytes must fail,
                    # rather than become EOF. The child shares this read cursor.
                    result = subprocess.run([self.binary, *operation], stdin=read_fd,
                                            capture_output=True, timeout=5)
                    with self.assertRaises(OSError) as error:
                        os.read(read_fd, 1)
                    self.assertIn(error.exception.errno, (errno.EAGAIN, errno.EWOULDBLOCK))
                finally:
                    os.close(read_fd)
                    os.close(write_fd)
                expected = selected if operation == ('--where', 'status=failed') else b''
                self.assertEqual((result.stdout, result.returncode), (expected, 3))
                self.assertTrue(result.stderr.startswith(b'jlog: <stdin>: '))
                self.assertRegex(result.stderr.lower(), b'would block|temporarily unavailable')
                self.assertNotIn(b'(complete)', result.stderr)
                self.assertNotIn(b'invalid JSON', result.stderr)
                self.assertNotIn(b'status', result.stderr)

    def test_progress_short_file_and_stdin(self):
        """Opt-in progress preserves reports and counts every physical line at EOF."""
        data = b'{}\n\nnull'
        report = (b'Records: 3\nValid: 2\nInvalid: 1\n\nMalformed records:\n'
                  b'  line 2: blank line\n')
        progress = b'jlog: 3 lines inspected, 1 invalid (complete)\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mixed.jsonl'
            path.write_bytes(data)
            for args in [('--progress', str(path)), (str(path), '--progress')]:
                with self.subTest(args=args):
                    result = self.run_cli(*args)
                    self.assertEqual(result.returncode, 4)
                    self.assertEqual(result.stdout, f'File: {path}\n'.encode() + report)
                    self.assertEqual(result.stderr, progress)
            self.assertEqual(path.read_bytes(), data)
        for args in [('--progress',), ('--progress', '-'), ('-', '--progress')]:
            with self.subTest(args=args):
                result = self.run_cli(*args, input_bytes=data)
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (b'File: <stdin>\n' + report, progress, 4))

    def test_m2_03_count_file_and_stdin(self):
        """Count valid records at EOF with data diagnostics and file/stdin parity."""
        cases = [
            (b'', b'0\n', b'', 0),
            (b'null', b'1\n', b'', 0),
            (b'{}\n\nnot-json\nnull', b'2\n',
             b': line 2: blank line\n{prefix}: line 3: invalid JSON\n', 4),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            for data, count, detail, status in cases:
                path.write_bytes(data)
                for args, label in [(('--count', str(path)), str(path)),
                                    ((str(path), '--count'), str(path)),
                                    (('--count',), '<stdin>'),
                                    (('-', '--count'), '<stdin>')]:
                    with self.subTest(data=data, args=args):
                        prefix = f'jlog: {label}'.encode()
                        diagnostics = prefix + detail.replace(b'{prefix}', prefix) if detail else b''
                        result = self.run_cli(*args, input_bytes=data)
                        self.assertEqual(result.returncode, status)
                        self.assertEqual((result.stdout, result.stderr), (count, diagnostics))
                self.assertEqual(path.read_bytes(), data)

    def test_m3_06_filter_file_and_stdin(self):
        """Filter exact original bodies with file/stdin parity and no data decoration."""
        lines = [
            b'{"status":"ok","skill":"Roc","detail":{"attempts":[1,2]}}',
            b' \t{"status":"failed","skill":"caf\\u00e9\\n\\u03bb","n":9007199254740993} ',
            b'{"status":"failed","skill":null,"huge":1e9999,"x":1,"x":null}',
            b'{"status":false}', b'42',
        ]
        data = b'\r\n'.join(lines)
        expected = b'\n'.join(lines[1:3]) + b'\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_bytes(data)
            for args in [('--where', 'status=failed', str(path)),
                         (str(path), '--where=status=failed'),
                         ('--where', 'status=failed'), ('-', '--where=status=failed')]:
                with self.subTest(args=args):
                    result = self.run_cli(*args, input_bytes=data)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual((result.stdout, result.stderr), (expected, b''))
            self.assertEqual(path.read_bytes(), data)

    def test_m3_06_filter_operands_and_final_record(self):
        """Preserve literal operands, decoded escapes, and an unterminated last body."""
        cases = [('=x', b'{"":"x"}'), ('a=', b'{"a":""}'),
                 ('a=x=y', b'{"a":"x=y"}'),
                 ('request.status=failed', b'{"request.status":"failed"}'),
                 (' key = value ', b'{" key ":" value "}'),
                 ('status=failed', b'{"status":"failed"}\r')]
        text = 'a"b\\c\nλ'
        cases.append(('v=' + text, json.dumps({'v': text}).encode()))
        for operand, body in cases:
            with self.subTest(operand=operand):
                result = self.run_cli('--where', operand, input_bytes=body)
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (body + b'\n', b'', 0))

    def test_m3_06_filter_streams_before_eof(self):
        """Emit selected records while stdin is open and flush the final pending line."""
        process = subprocess.Popen([self.binary, '--where', 'status=failed'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        first = b' {"status":"failed","id":1} '
        last = b'{"status":"failed","id":2}'
        try:
            process.stdin.write(first + b'\n')
            self.assertTrue(select.select([process.stdout], [], [], 3)[0],
                            'A matching record must stream before EOF')
            self.assertEqual(process.stdout.readline(), first + b'\n')
            self.assertIsNone(process.poll())
            process.stdin.write(b'bad\n' + last)
            self.assertFalse(select.select([process.stdout, process.stderr], [], [], 0.2)[0])
            process.stdin.close()
            process.stdin = None
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual((stdout, stderr, process.returncode),
                             (last + b'\n', b'jlog: <stdin>: line 2: invalid JSON\n', 4))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_m2_06_tail_file_and_stdin(self):
        """Tail valid original records in order while validating the whole input."""
        data = b' \t{}\r\n\nnot-json\nnull\r\n42'
        cases = [('0', b''), ('1', b'42\n'), ('0002', b'null\n42\n'),
                 ('4294967295', b' \t{}\nnull\n42\n')]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_bytes(data)
            for size, expected in cases:
                for args, label in [(('--tail', size, str(path)), str(path)),
                                    ((str(path), '--tail=' + size), str(path)),
                                    (('--tail', size), '<stdin>')]:
                    with self.subTest(size=size, args=args):
                        diagnostics = (f'jlog: {label}: line 2: blank line\n'
                                       f'jlog: {label}: line 3: invalid JSON\n').encode()
                        result = self.run_cli(*args, input_bytes=data)
                        self.assertEqual(result.returncode, 4)
                        self.assertEqual((result.stdout, result.stderr),
                                         (expected, diagnostics))
            self.assertEqual(path.read_bytes(), data)

    def test_m3_07_filter_no_matches(self):
        """Treat all valid nonobjects and missing/nonstring fields as nonmatches."""
        for data in [b'', b'null\ntrue\n42\n1e9999\n["failed"]\n"failed"',
                     b'{}\n{"status":null}\n{"status":1e9999}\n{"status":false}\n'
                     b'{"status":[]}\n{"status":{}}\n{"status":"Failed"}',
                     b'{"status":"failed","status":null}\n'
                     b'{"status":"failed","stat\\u0075s":"ok"}']:
            with self.subTest(data=data):
                result = self.run_cli('--where=status=failed', input_bytes=data)
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (b'', b'', 0))

    def test_m3_07_filter_defects_recovery_and_cap(self):
        """Continue after every malformed kind, count physical lines, and cap details."""
        match = b' {"status":"failed","status":"failed","n":1e9999} '
        bad = [b'\xef\xbb\xbf{}', b'\xff', b'', b'not-json', b'[' * 129 + b'0' + b']' * 129]
        reasons = [b'BOM is not allowed', b'invalid UTF-8', b'blank line',
                   b'invalid JSON', b'nesting exceeds 128']
        lines = []
        for invalid in bad:
            lines.extend([invalid, match])
        result = self.run_cli('--where', 'status=failed', input_bytes=b'\r\n'.join(lines))
        self.assertEqual((result.stdout, result.returncode), ((match + b'\n') * 5, 4))
        self.assertEqual(result.stderr, b''.join(
            b'jlog: <stdin>: line ' + str(index * 2 + 1).encode() + b': ' + reason + b'\n'
            for index, reason in enumerate(reasons)))
        result = self.run_cli('--where=status=failed', input_bytes=(
            match + b'\n' + b'bad\n' * 103 + match))
        expected = b''.join(f'jlog: <stdin>: line {n}: invalid JSON\n'.encode()
                            for n in range(2, 102))
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         ((match + b'\n') * 2,
                          expected + b'jlog: <stdin>: 3 more invalid records\n', 4))

    def test_m3_07_filter_diagnostic_failure_keeps_emitted_prefix(self):
        """An actual broken stderr pipe yields 3 after already-streamed matches."""
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        body = b'{"status":"failed"}\n'
        try:
            result = subprocess.run([self.binary, '--where', 'status=failed'],
                                    input=body + b'bad\n', stdout=subprocess.PIPE,
                                    stderr=write_fd, timeout=5)
        finally:
            os.close(write_fd)
        self.assertEqual((result.stdout, result.returncode), (body, 3))

    def test_m3_08_filter_count_pipeline(self):
        """Pipe selected JSONL into count and check both processes independently."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            for malformed in (False, True):
                data = (b'{"status":"failed","n":1e9999}\n{"status":"ok"}\n'
                        + (b"bad\n" if malformed else b"")
                        + b'{"status":null,"status":"failed"}')
                path.write_bytes(data)
                before = hashlib.sha256(data).digest()
                with self.subTest(malformed=malformed):
                    producer = subprocess.Popen(
                        [self.binary, "--where", "status=failed", str(path)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    consumer = None
                    try:
                        consumer = subprocess.Popen(
                            [self.binary, "--count"], stdin=producer.stdout,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        producer.stdout.close()
                        stdout, stderr = consumer.communicate(timeout=5)
                        _, producer_errors = producer.communicate(timeout=5)
                        self.assertEqual((stdout, stderr, consumer.returncode),
                                         (b"2\n", b"", 0))
                        self.assertEqual(producer.returncode, 4 if malformed else 0)
                        expected_errors = (f"jlog: {path}: line 3: invalid JSON\n".encode()
                                           if malformed else b"")
                        self.assertEqual(producer_errors, expected_errors)
                        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)
                    finally:
                        for process in (producer, consumer):
                            if process is not None:
                                if process.poll() is None:
                                    process.kill()
                                process.communicate(timeout=5)

    def test_m3_08_filter_redirect_and_unchanged_source(self):
        """Redirect byte-preserved output to a file accepted by an independent parser."""
        bodies = [b' \t{"status":"failed","message":"caf\\u00e9","n":9007199254740993} ',
                  b'{"status":"ok"}', b'{"status":0,"status":"failed","n":1e9999}']
        data = b"\r\n".join(bodies)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "events.jsonl"
            output = Path(directory) / "selected.jsonl"
            source.write_bytes(data)
            before = hashlib.sha256(data).digest()
            with output.open("wb") as handle:
                result = subprocess.run(
                    [self.binary, str(source), "--where=status=failed"],
                    stdout=handle, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual((result.stderr, result.returncode), (b"", 0))
            self.assertEqual(output.read_bytes(), bodies[0] + b"\n" + bodies[2] + b"\n")
            parsed = [json.loads(body, parse_float=Decimal)
                      for body in output.read_bytes().splitlines()]
            self.assertEqual(len(parsed), 2)
            self.assertTrue(all(record["status"] == "failed" for record in parsed))
            self.assertEqual(parsed[0]["n"], 9007199254740993)
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_m2_08_file_errors_all_modes(self):
        """Keep all deferred outputs empty on real missing/permission/directory errors."""
        self.assertNotEqual(os.geteuid(), 0, 'Permission test requires an unprivileged user')
        with tempfile.TemporaryDirectory() as directory:
            denied = Path(directory) / 'denied'
            denied.write_bytes(b'{}\n')
            denied.chmod(0)
            try:
                for path, category in [(Path(directory) / 'missing', b'not found'),
                                       (denied, b'permission denied'),
                                       (Path(directory), b'directory')]:
                    for operation in [(), ('--count',), ('--tail', '1'), ('--tail', '0'),
                                      ('--where', 'status=failed')]:
                        with self.subTest(path=path, operation=operation):
                            result = self.run_cli(*operation, str(path))
                            self.assertEqual((result.stdout, result.returncode), (b'', 3))
                            self.assertIn(os.fsencode(path), result.stderr)
                            self.assertIn(category, result.stderr.lower())
            finally:
                denied.chmod(0o600)

    def test_m2_09_stdin_read_errors_all_modes(self):
        """A reported stdin read error suppresses every deferred output and completion."""
        with tempfile.TemporaryDirectory() as directory:
            for operation in [('--progress',), ('--count',), ('--tail', '1'), ('--tail', '0'),
                              ('--where', 'status=failed')]:
                with self.subTest(operation=operation):
                    descriptor = os.open(directory, os.O_RDONLY)
                    try:
                        result = subprocess.run([self.binary, *operation], stdin=descriptor,
                                                capture_output=True, timeout=5)
                    finally:
                        os.close(descriptor)
                    self.assertEqual((result.stdout, result.returncode), (b'', 3))
                    self.assertIn(b'jlog: <stdin>:', result.stderr)
                    self.assertNotIn(b'(complete)', result.stderr)

    def test_m2_10_closed_stdout_pipes(self):
        """Real broken output pipes override success and malformed-input status."""
        cases = [(('--help',), b''), (('--version',), b''), ((), b'{}\n'),
                 (('--count',), b'{}\n'), (('--tail', '1'), b'{}\n'),
                 ((), b'bad\n{}\n'), (('--count',), b'bad\n{}\n'),
                 (('--tail', '1'), b'bad\n{}\n'),
                 (('--where', 'x=y'), b'{"x":"y"}\n'),
                 (('--where', 'x=y'), b'bad\n{"x":"y"}\n')]
        for args, data in cases:
            with self.subTest(args=args, data=data):
                read_fd, write_fd = os.pipe()
                os.close(read_fd)
                try:
                    result = subprocess.run([self.binary, *args], input=data,
                                            stdout=write_fd, stderr=subprocess.PIPE, timeout=5)
                finally:
                    os.close(write_fd)
                self.assertEqual(result.returncode, 3)
                self.assertNotIn(b'crash', result.stderr.lower())

    def test_m2_10_closed_stderr_pipes(self):
        """Stop cleanly on diagnostic/progress write failure without deferred stdout."""
        cases = [(('--unknown',), b''), (('--where', 'x=y'), b'bad\n'),
                 (('--progress',), b'{}\n'), (('--count',), b'bad\n{}\n'),
                 (('--tail', '1'), b'bad\n{}\n')]
        for args, data in cases:
            with self.subTest(args=args):
                read_fd, write_fd = os.pipe()
                os.close(read_fd)
                try:
                    result = subprocess.run([self.binary, *args], input=data,
                                            stdout=subprocess.PIPE, stderr=write_fd, timeout=5)
                finally:
                    os.close(write_fd)
                self.assertEqual((result.stdout, result.returncode), (b'', 3))

    def test_m2_06_tail_empty_wraps_and_original_bytes(self):
        """Handle empty/max-N input, repeated ring wraps, and lossless record output."""
        for size in ('0', '1', '4294967295'):
            with self.subTest(size=size):
                result = self.run_cli('--tail', size)
                self.assertEqual((result.stdout, result.stderr, result.returncode), (b'', b'', 0))
        data = b''.join(f'{n}\n'.encode() for n in range(1, 21))
        result = self.run_cli('--tail', '3', input_bytes=data)
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'18\n19\n20\n', b'', 0))
        bodies = [b' 1e9999 ', b'9007199254740993', b'{"x":1,"x":null}',
                  '"café λ🙂"'.encode(), b'null\r']
        result = self.run_cli('--tail', '4294967295', input_bytes=b'\r\n'.join(bodies))
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'\n'.join(bodies) + b'\n', b'', 0))

    def test_m2_06_tail_waits_for_eof(self):
        """Tail defers stdout through EOF and ignores the inspection progress modifier."""
        process = subprocess.Popen([self.binary, '--progress', '--tail', '2'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        try:
            process.stdin.write(b'1\n2\n3')
            self.assertFalse(select.select([process.stdout, process.stderr], [], [], 0.2)[0])
            self.assertIsNone(process.poll())
            process.stdin.close()
            process.stdin = None
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual((stdout, stderr, process.returncode), (b'2\n3\n', b'', 0))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_m2_03_count_values_and_error_cap(self):
        """Accept all JSON kinds and cap data diagnostics while counting all input."""
        data = ('[]\n"café λ🙂"\ntrue\nfalse\nnull\n'
                '340282366920938463463374607431768211456\n1e9999\n').encode()
        result = self.run_cli('--count', input_bytes=data)
        self.assertEqual((result.stdout, result.stderr, result.returncode), (b'7\n', b'', 0))
        result = self.run_cli('--count', input_bytes=b'\n' * 103 + b'{}')
        diagnostics = (b''.join(f'jlog: <stdin>: line {n}: blank line\n'.encode()
                                for n in range(1, 101)) +
                       b'jlog: <stdin>: 3 more invalid records\n')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'1\n', diagnostics, 4))

    def test_m2_03_count_waits_for_eof(self):
        """Defer count and data diagnostics while a partial input remains open."""
        process = subprocess.Popen([self.binary, '--count'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        try:
            process.stdin.write(b'{}\n\nnull')
            self.assertFalse(select.select([process.stdout, process.stderr], [], [], 0.2)[0])
            self.assertIsNone(process.poll())
            process.stdin.close()
            process.stdin = None
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual((stdout, stderr, process.returncode),
                             (b'2\n', b'jlog: <stdin>: line 2: blank line\n', 4))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_progress_count_keeps_data_contract(self):
        """Inspection-only progress does not decorate an implemented count result."""
        result = self.run_cli('--progress', '--count', input_bytes=b'{}\n\nnull')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'2\n', b'jlog: <stdin>: line 2: blank line\n', 4))

    def test_progress_empty_and_unterminated(self):
        """Completion snapshots include empty input and the final unterminated record."""
        cases = [
            (b'', b'Records: 0\nValid: 0\nInvalid: 0\n',
             b'jlog: 0 lines inspected, 0 invalid (complete)\n'),
            (b'null', b'Records: 1\nValid: 1\nInvalid: 0\n',
             b'jlog: 1 lines inspected, 0 invalid (complete)\n'),
        ]
        for data, report, progress in cases:
            with self.subTest(data=data):
                result = self.run_cli('--progress', input_bytes=data)
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (b'File: <stdin>\n' + report, progress, 0))

    def test_progress_before_eof(self):
        """Show rate-limited stderr progress while stdin stays open and stdout waits."""
        process = subprocess.Popen([self.binary, '--progress'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   bufsize=0)
        try:
            process.stdin.write(b'{}\n')
            self.assertFalse(select.select([process.stderr], [], [], 0.2)[0],
                             'Progress must not print immediately for every line')
            time.sleep(1.05)
            process.stdin.write(b'\nnull\n')
            self.assertTrue(select.select([process.stderr], [], [], 3)[0],
                            'Progress must appear before EOF')
            self.assertEqual(process.stderr.readline(),
                             b'jlog: 3 lines inspected, 1 invalid\n')
            self.assertIsNone(process.poll())
            self.assertFalse(select.select([process.stdout], [], [], 0)[0],
                             'The completed report must wait for EOF')
            process.stdin.write(b'true')
            self.assertFalse(select.select([process.stderr], [], [], 0.2)[0],
                             'Do not repeat progress before the next interval')
            process.stdin.close()
            process.stdin = None
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(stdout,
                             b'File: <stdin>\nRecords: 4\nValid: 3\nInvalid: 1\n\n'
                             b'Malformed records:\n  line 2: blank line\n')
            self.assertEqual((stderr, process.returncode),
                             (b'jlog: 4 lines inspected, 1 invalid (complete)\n', 4))
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_progress_argument_errors(self):
        """Reject repeated/value-taking progress and combined information commands."""
        for args in [('--progress', '--progress'), ('--progress=true',),
                     ('--progress', '--help'), ('--version', '--progress'),
                     ('--progress', '--tail'), ('--progress', '--where')]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual((result.stdout, result.returncode), (b'', 2))
                self.assertIn(b'\nUsage: jlog ', result.stderr)
                self.assertNotIn(b'lines inspected', result.stderr)

    def test_progress_filename_after_terminator(self):
        """Keep --progress usable as a literal filename after the option terminator."""
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / '--progress').write_bytes(b'{}\n')
            for args, stderr in [
                    (('--', '--progress'), b''),
                    (('--progress', '--', '--progress'),
                     b'jlog: 1 lines inspected, 0 invalid (complete)\n')]:
                with self.subTest(args=args):
                    result = subprocess.run([self.binary, *args], cwd=directory,
                                            capture_output=True, timeout=5)
                    self.assertEqual((result.stdout, result.stderr, result.returncode),
                                     (b'File: --progress\nRecords: 1\nValid: 1\nInvalid: 0\n',
                                      stderr, 0))

    def test_progress_input_errors_no_completion(self):
        """Do not publish completed progress or a report after open/read failures."""
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cli('--progress', str(Path(directory) / 'missing'))
            self.assertEqual((result.stdout, result.returncode), (b'', 3))
            self.assertIn(b'not found', result.stderr.lower())
            self.assertNotIn(b'lines inspected', result.stderr)
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                result = subprocess.run([self.binary, '--progress'], stdin=descriptor,
                                        capture_output=True, timeout=5)
            finally:
                os.close(descriptor)
            self.assertEqual((result.stdout, result.returncode), (b'', 3))
            self.assertIn(b'jlog: <stdin>:', result.stderr)
            self.assertNotIn(b'(complete)', result.stderr)

    def test_progress_filter_keeps_data_contract(self):
        """Inspection progress does not decorate streamed filtering or diagnostics."""
        result = self.run_cli('--progress', '--where', 'status=failed',
                              input_bytes=b'{"status":"failed"}\nbad\n')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'{"status":"failed"}\n',
                          b'jlog: <stdin>: line 2: invalid JSON\n', 4))

    def test_m1_16_file_single_record(self):
        """Verify the complete report for a file containing one valid record."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'one.jsonl'
            path.write_bytes(b'{}\n')
            result = self.run_cli(str(path))
            self.assertEqual(result.stdout,
                             f'File: {path}\nRecords: 1\nValid: 1\nInvalid: 0\n'.encode())
            self.assertEqual((result.stderr, result.returncode), (b'', 0))

    def assert_file_report(self, data, report, status=0):
        """Assert exact file report bytes, status, and unchanged input contents."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_bytes(data)
            result = self.run_cli(str(path))
            self.assertEqual(result.stdout, f'File: {path}\n'.encode() + report)
            self.assertEqual((result.stderr, result.returncode), (b'', status))
            self.assertEqual(path.read_bytes(), data)

    def test_m1_16_empty_and_eof(self):
        """Check empty files, unterminated records, and a single blank line."""
        cases = [
            (b'', b'Records: 0\nValid: 0\nInvalid: 0\n', 0),
            (b'null', b'Records: 1\nValid: 1\nInvalid: 0\n', 0),
            (b'\n', b'Records: 1\nValid: 0\nInvalid: 1\n\nMalformed records:\n  line 1: blank line\n', 4),
        ]
        for data, report, status in cases:
            with self.subTest(data=data):
                self.assert_file_report(data, report, status)

    def test_m1_16_representative_and_malformed(self):
        """Check representative records and recovery past malformed physical lines."""
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
        """Accept JSON value kinds, Unicode, duplicate keys, and unbounded numbers."""
        data = ('[]\n"café \u03bb🙂"\ntrue\nfalse\nnull\n'
                '340282366920938463463374607431768211456\n1e9999\n'
                '{"pair":"\\uD83D\\uDE42","x":1,"x":null}\n').encode()
        self.assert_file_report(data, b'Records: 8\nValid: 8\nInvalid: 0\n')

    def test_m1_16_crlf_and_numbering(self):
        """Preserve physical numbering across CRLF, blank lines, and a final CR."""
        self.assert_file_report(
            b'{}\r\n\r\nnull\r',
            b'Records: 3\nValid: 2\nInvalid: 1\n\nMalformed records:\n'
            b'  line 2: blank line\n', 4,
        )

    def test_m1_16_defects_and_recovery(self):
        """Report encoding, BOM, grammar, and depth defects while continuing."""
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
        """Cap file error details at 100 while counting every invalid record."""
        expected = (b'Records: 102\nValid: 1\nInvalid: 101\n\nMalformed records:\n' +
                    b''.join(f'  line {n}: blank line\n'.encode() for n in range(1, 101)) +
                    b'  ... 1 more invalid records\n')
        self.assert_file_report(b'\n' * 101 + b'{}', expected, 4)

    def test_m1_16_native_path_bytes(self):
        """Open and label a filename supplied as native UTF-8 bytes."""
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
        """Check native invalid-UTF-8 paths, including Darwin fixture rejection."""
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
        """Escape control characters in filename labels in the report."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'line\n\t\r\x01.jsonl'
            path.write_bytes(b'{}')
            result = self.run_cli(str(path))
            expected = (f'File: {directory}/line\\n\\t\\r\\u0001.jsonl\n'
                        'Records: 1\nValid: 1\nInvalid: 0\n').encode()
            self.assertEqual((result.stdout, result.stderr, result.returncode),
                             (expected, b'', 0))

    def test_m1_16_input_errors_suppress_report(self):
        """Require exit 3 and no report for missing, unreadable, or directory input."""
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
        """Report zero totals when implicit stdin reaches EOF immediately."""
        result = self.run_cli()
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'File: <stdin>\nRecords: 0\nValid: 0\nInvalid: 0\n', b'', 0))

    def assert_stdin_report(self, data, report, status=0):
        """Assert identical reports for implicit stdin and an explicit dash."""
        for args in [(), ('-',)]:
            with self.subTest(args=args):
                result = self.run_cli(*args, input_bytes=data)
                self.assertEqual((result.stdout, result.stderr, result.returncode),
                                 (b'File: <stdin>\n' + report, b'', status))

    def test_m1_17_stdin_records_and_eof(self):
        """Check stdin/file parity for framing, malformed records, and EOF."""
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
        """Preserve long records, Unicode, and CRLF across transport boundaries."""
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
        """Require the same validation diagnostics for stdin and files."""
        data = b'\xef\xbb\xbf{}\n1e9999\n' + b'[' * 129 + b'0' + b']' * 129 + b'\n"\\uD800"\ntrue'
        report = (b'Records: 5\nValid: 2\nInvalid: 3\n\nMalformed records:\n'
                  b'  line 1: BOM is not allowed\n  line 3: nesting exceeds 128\n'
                  b'  line 4: invalid JSON\n')
        self.assert_stdin_report(data, report, 4)
        self.assert_file_report(data, report, 4)

    def test_m1_17_stdin_error_cap(self):
        """Cap stdin error details at 100 and report the omitted count."""
        expected = (b'Records: 101\nValid: 0\nInvalid: 101\n\nMalformed records:\n' +
                    b''.join(f'  line {n}: blank line\n'.encode() for n in range(1, 101)) +
                    b'  ... 1 more invalid records\n')
        self.assert_stdin_report(b'\n' * 101, expected, 4)

    def test_m1_18_preflight_with_stdin_held_open(self):
        """Ensure help, version, and usage errors finish without reading stdin."""
        cases = [
            (('--help',), HELP, 0), (('-h',), HELP, 0),
            (('--version',), b'jlog 0.1.0\n', 0),
            (('-V',), b'jlog 0.1.0\n', 0),
            (('--unknown',), b'', 2), (('--tail',), b'', 2),
            (('--where',), b'', 2), (('--help', 'extra'), b'', 2),
            (('--progress', '--progress'), b'', 2),
            (('--progress', '--help'), b'', 2),
            (('--progress=true',), b'', 2),
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
        """Reject invalid arguments before attempting to open a missing file."""
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
        """Require a directory-stdin read failure to suppress the report and exit 3."""
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
        """Reject help combined with an extra argument using the usage diagnostic."""
        result = self.run_cli('--help', 'extra')
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.startswith(b'jlog: '))
        self.assertIn(b'\nUsage: jlog ', result.stderr)

    def test_m1_06_help_alias(self):
        """Match the exact help output and success status for the short alias."""
        result = self.run_cli('-h')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (HELP, b'', 0))

    def test_m1_06_usage_regressions(self):
        """Reject unsupported, repeated, conflicting, or incomplete arguments."""
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
        """Reject undecodable option names and operands without lossy conversion."""
        for args in [(b'--where', b'a=\xff'), (b'--where=a=\xff',),
                     (b'--tail', b'1\xff'), (b'--\xff',)]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'\nUsage: jlog ', result.stderr)

    def test_m1_06_help(self):
        """Match the exact long-form help output with empty stderr and exit 0."""
        result = self.run_cli('--help')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (HELP, b'', 0))

    def test_m1_01_version_alias(self):
        """Match the exact version output and status for the short alias."""
        result = self.run_cli('-V')
        self.assertEqual((result.stdout, result.stderr, result.returncode),
                         (b'jlog 0.1.0\n', b'', 0))

    def test_m1_01_version(self):
        """Match the exact long-form version output, stderr, and success status."""
        result = self.run_cli('--version')
        self.assertEqual(result.stdout, b'jlog 0.1.0\n')
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
