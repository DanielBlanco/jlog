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

## Parse arguments before I/O, dispatch help/version or inspection, and map failures
## to process exits. Count, tail, and filtering currently return exit 1.
main! : List(OsStr) => Try({}, [Exit(I32)])
main! = |args| match Cli.parse(args) {
	Ok({ operation: Help, .. }) => Stdout.write!(Cli.help_text).map_err(|_| Exit(3))
	Ok({ operation: Version, .. }) => Stdout.line!("jlog 0.1.0").map_err(|_| Exit(3))
	Err(Usage) => {
		Stderr.write!("jlog: invalid arguments\nUsage: jlog [INPUT] [--count | --tail N | --where KEY=TEXT]\nTry 'jlog --help' for help.\n").map_err(|_| Exit(3))?
		Err(Exit(2))
	}
	Ok({ operation: Inspect, source: File(native) }) => inspect_file!(native)
	Ok({ operation: Inspect, source: Stdin }) => inspect_reader!(FromStdin, "<stdin>")
	Ok(_) => {
		Stderr.line!("jlog: data operations are not implemented yet").map_err(|_| Exit(3))?
		Err(Exit(1))
	}
}

## Open the original native path and inspect its buffered reader. Display text is
## used only for labels; open failures are reported on stderr with exit 3.
inspect_file! : OsStr => Try({}, [Exit(I32)])
inspect_file! = |native| {
	label = native.display()
	reader = match File.open_reader!(Path.from_os_str(native)) {
		Ok(value) => value
		Err(PathErr(err, _)) => return input_error!(label, IOErr.to_str(err))
	}
	inspect_reader!(FromFile(reader), label)
}

## Feed file or stdin chunks through the shared framer and inspection reducer.
## Emit the completed report only at successful EOF; read failures return exit 3.
inspect_reader! : [FromFile(File.Reader), FromStdin], Str => Try({}, [Exit(I32)])
inspect_reader! = |source, label| {
	var $current = { state: Jsonl.start, value: Operations.start }
	var $reading = True
	while $reading {
		bytes = match read_bytes!(source) {
			Ok(value) => value
			Err(InputError(err)) => return input_error!(label, IOErr.to_str(err))
		}
		if bytes.is_empty() {
			$reading = False
		} else {
			$current = Jsonl.feed($current.state, bytes, $current.value, Operations.inspect_line)
		}
	}
	summary = Jsonl.finish($current.state, $current.value, Operations.inspect_line).value
	inspection_report!(label, summary)
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

## Write the completed report to stdout, returning exit 4 for malformed records
## or exit 3 if writing fails. Valid and empty inputs succeed.
inspection_report! : Str, Operations.Summary => Try({}, [Exit(I32)])
inspection_report! = |label, summary| {
	Stdout.write!(Operations.report(label, summary)).map_err(|_| Exit(3))?
	if summary.invalid > 0 {
		Err(Exit(4))
	} else {
		Ok({})
	}
}

## Write an input failure to stderr with an escaped source label and return exit 3,
## including when the diagnostic itself cannot be written.
input_error! : Str, Str => Try({}, [Exit(I32)])
input_error! = |label, reason| {
	Stderr.line!("jlog: ${Operations.escape_source(label)}: ${reason}").map_err(|_| Exit(3))?
	Err(Exit(3))
}
