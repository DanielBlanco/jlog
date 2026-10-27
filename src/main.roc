app [main!] { pf: platform "https://github.com/roc-lang/basic-cli/releases/download/0.25.0/CZsY7tYZwR3rj9kYbpaCfxki2yVAaRL8bBwMLvB2xkbA.tar.zst" }

import Cli
import Jsonl
import Operations

import pf.OsStr
import pf.Stdout
import pf.Stderr
import pf.File
import pf.Path
import pf.IOErr
import pf.Stdin
import pf.Monotonic

ProgressOutput : [Quiet, Reporting(Operations.Progress)]

InputMode : [Inspect, Count, Tail(U32), Where({ key : Str, text : Str })]

## Parse arguments before I/O and dispatch help/version or an implemented input
## mode. Every implemented operation shares framing and checked validation.
main! : List(OsStr) => Try({}, [Exit(I32)])
main! = |args| match Cli.parse(args) {
	Ok({ operation: Help, .. }) => write_stdout!(Cli.help_text)
	Ok({ operation: Version, .. }) => write_stdout!("jlog 0.1.0\n")
	Err(Usage) => report_failure!("jlog: invalid arguments\nUsage: jlog [INPUT] [--progress] [--count | --tail N | --where KEY=TEXT]\nTry 'jlog --help' for help.", UsageFailure)
	Ok({ operation: Inspect, source, progress }) => read_source!(source, Inspect, progress)
	Ok({ operation: Count, source, .. }) => read_source!(source, Count, False)
	Ok({ operation: Tail(size), source, .. }) => read_source!(source, Tail(size), False)
	Ok({ operation: Where(filter), source, .. }) => read_source!(source, Where(filter), False)
}

## Write result text exactly as supplied; callers include any required newline.
## Map stdout write errors reported by the platform to input/output exit status 3.
write_stdout! : Str => Try({}, [Exit(I32)])
write_stdout! = |text| Stdout.write!(text).map_err(|_| Exit(3))

## Write exact diagnostic text, including any existing newlines. Returned write
## errors map to exit 3; this also supports a block of capped data diagnostics.
write_stderr! : Str => Try({}, [Exit(I32)])
write_stderr! = |text| Stderr.write!(text).map_err(|_| Exit(3))

## Write one stderr line, mapping reported write errors to exit 3. Both progress
## and failure diagnostics use this newline and error policy.
write_stderr_line! : Str => Try({}, [Exit(I32)])
write_stderr_line! = |text| write_stderr!(text.concat("\n"))

## Write a diagnostic with a final LF and return the requested failure status.
## A stderr write error reported by the platform overrides that status with exit 3.
report_failure! : Str, Operations.Failure => Try(a, [Exit(I32)])
report_failure! = |message, failure| {
	write_stderr_line!(message)?
	Err(Exit(Operations.exit_code(Failed(failure))))
}

## Select a native file reader or stdin without reconstructing paths from labels.
## Open failures report exit 3 before the shared read loop or progress starts.
read_source! : Cli.Source, InputMode, Bool => Try({}, [Exit(I32)])
read_source! = |source, mode, progress| match source {
	File(native) => {
		label = native.display()
		reader = match File.open_reader!(Path.from_os_str(native)) {
			Ok(value) => value
			Err(PathErr(err, _)) => return input_error!(label, IOErr.to_str(err))
		}
		process_reader!(FromFile(reader), label, mode, progress)
	}
	Stdin => process_reader!(FromStdin, "<stdin>", mode, progress)
}

## Feed file or stdin chunks through shared framing and checked validation.
## Drain filter matches per read; inspect/count/tail results wait for EOF.
process_reader! : [FromFile(File.Reader), FromStdin], Str, InputMode, Bool => Try({}, [Exit(I32)])
process_reader! = |source, label, mode, progress| {
	limit = match mode {
		Tail(size) => size
		_ => 0
	}
	consume = |value, line| match mode {
		Where(filter) => Operations.filter_checked(value, line, filter)
		_ => Operations.consume_checked(value, line)
	}
	var $current = { state: Jsonl.start, value: Ok(Operations.stream_start(limit)) }
	var $progress = start_progress!(progress)
	var $reading = True
	while $reading {
		bytes = match read_bytes!(source) {
			Ok(value) => value
			Err(InputError(err)) => {
				previous = checked_state!(label, $current.state, $current.value)?
				return finish_input!(label, mode, $progress, previous, ReadError(IOErr.to_str(err)))
			}
		}
		if bytes.is_empty() {
			$reading = False
		} else {
			$current = Jsonl.feed($current.state, bytes, $current.value, consume)
			checked = checked_state!(label, $current.state, $current.value)?
			$progress = update_progress!($progress, checked.summary)?
			match mode {
				Where(_) => {
					ready = Operations.drain_matches(checked)
					write_records!(ready.bodies)?
					$current = { ..$current, value: Ok(ready.state) }
				}
				_ => {}
			}
		}
	}
	finished = Jsonl.finish($current.state, $current.value, consume)
	completed = checked_state!(label, finished.state, finished.value)?
	finish_input!(label, mode, $progress, completed, Eof)
}

## Resolve the production EOF/read-failure transition before emitting deferred
## progress, diagnostics, count, tail, or inspection results.
finish_input! : Str, InputMode, ProgressOutput, Operations.StreamState, [Eof, ReadError(Str)] => Try({}, [Exit(I32)])
finish_input! = |label, mode, progress, state, event| {
	completed = match Operations.complete_stream(state, event) {
		Ok(value) => value
		Err(ReadError(reason)) => return input_error!(label, reason)
	}
	finish_progress!(progress, completed.summary)?
	complete_output!(label, mode, completed)
}

## Map exhausted counters or unexpected validated-object lookup failure to exit 1.
## Failed reductions contain no deferred results; earlier filter output may exist.
checked_state! : Str, Jsonl.State, Operations.StreamResult => Try(Operations.StreamState, [Exit(I32)])
checked_state! = |label, framing, result| {
	if framing.exhausted {
		return report_failure!("jlog: resource/counter exhausted", ResourceFailure)
	}
	match result {
		Ok(state) => Ok(state)
		Err(ResourceFailure) => report_failure!("jlog: resource/counter exhausted", ResourceFailure)
		Err(LookupFailure(number)) => report_failure!("jlog: ${Operations.escape_source(label)}: line ${number.to_str()}: validated JSON lookup failed", InternalFailure)
	}
}

## Read a monotonic timestamp only when progress was explicitly requested.
## Quiet inspections perform no clock reads or progress writes.
start_progress! : Bool => ProgressOutput
start_progress! = |enabled| if enabled {
	Reporting(Operations.progress_start(Monotonic.now!()))
} else {
	Quiet
}

## Check progress after a read has been framed. Write only when the pure rate
## limiter permits it, and retain the timestamp/count only after a successful write.
update_progress! : ProgressOutput, Operations.Summary => Try(ProgressOutput, [Exit(I32)])
update_progress! = |output, summary| match output {
	Quiet => Ok(Quiet)
	Reporting(previous) => {
		now_ns = Monotonic.now!()
		if Operations.progress_due(previous, now_ns, summary) {
			write_stderr_line!(Operations.progress_text(summary, False))?
			Ok(Reporting({ last_update_ns: now_ns, records: summary.records }))
		} else {
			Ok(output)
		}
	}
}

## Write one final progress snapshot only after successful EOF, including empty
## input and any final unterminated line. Reported write errors return exit 3.
finish_progress! : ProgressOutput, Operations.Summary => Try({}, [Exit(I32)])
finish_progress! = |output, summary| match output {
	Quiet => Ok({})
	Reporting(_) => write_stderr_line!(Operations.progress_text(summary, True))
}

## Read raw bytes from either transport, normalizing EOF to an empty list while
## preserving read errors exposed by the platform as InputError.
read_bytes! : [FromFile(File.Reader), FromStdin] => Try(List(U8), [InputError(IOErr)])
read_bytes! = |source| match source {
	FromFile(reader) => reader.read_line!().map_err(|FileErr(err)| InputError(err))
	FromStdin => match Stdin.bytes!() {
		Ok(bytes) => Ok(bytes)
		Err(EndOfFile) => Ok([])
		Err(StdinErr(err)) => Err(InputError(err))
	}
}

## Write deferred inspection/count/tail results or final filter matches at EOF.
## Data diagnostics stay on stderr; a reported write failure overrides exit 4.
complete_output! : Str, InputMode, Operations.StreamState => Try({}, [Exit(I32)])
complete_output! = |label, mode, completed| {
	summary = completed.summary
	match mode {
		Inspect => write_stdout!(Operations.report(label, summary))?
		Count => {
			write_stderr!(Operations.data_diagnostics(label, summary))?
			write_stdout!(Operations.count_report(summary))?
		}
		Tail(_) => {
			write_stderr!(Operations.data_diagnostics(label, summary))?
			write_records!(Operations.tail_lines(completed.tail))?
		}
		Where(_) => {
			write_records!(completed.matches)?
			write_stderr!(Operations.data_diagnostics(label, summary))?
		}
	}
	validation_status(summary)
}

## Write one bounded group of original bodies, adding exactly one LF per record.
## Shared by EOF tail output and per-read filtering without a combined byte copy.
write_records! : List(List(U8)) => Try({}, [Exit(I32)])
write_records! = |bodies| {
	for body in bodies {
		Stdout.write_bytes!(body).map_err(|_| Exit(3))?
		write_stdout!("\n")?
	}
	Ok({})
}

## Map a successfully completed validation to exit 0 or malformed-input exit 4.
## I/O failures return earlier and never reach this completion-only policy.
validation_status : Operations.Summary -> Try({}, [Exit(I32)])
validation_status = |summary| {
	code = Operations.exit_code(Completed(summary))
	if code == 0 {
		Ok({})
	} else {
		Err(Exit(code))
	}
}

## Write an input failure to stderr with an escaped source label and return exit 3,
## including when the diagnostic itself cannot be written.
input_error! : Str, Str => Try({}, [Exit(I32)])
input_error! = |label, reason| report_failure!("jlog: ${Operations.escape_source(label)}: ${reason}", IoFailure)
