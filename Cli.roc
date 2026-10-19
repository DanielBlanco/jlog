import pf.OsStr

Cli :: {}.{
	parse : List(OsStr) -> Try({ source : [Stdin, File(OsStr)], operation : [Inspect, Count, Tail(U32), Where({ key : Str, text : Str }), Help, Version] }, [Usage])
	parse = |args| match args {
		[arg] if arg.to_str_try() == Ok("--help") or arg.to_str_try() == Ok("-h") => Ok({ source: Stdin, operation: Help })
		[arg] if arg.to_str_try() == Ok("--version") or arg.to_str_try() == Ok("-V") => Ok({ source: Stdin, operation: Version })
		_ => parse_args(args, Stdin, Inspect, False, False)
	}

	help_text : Str
	help_text = "Usage: jlog [INPUT] [--count | --tail N | --where KEY=TEXT]\n       jlog --help | --version\n\nINPUT is one file, or - for stdin (the default); use ./- for a file named -.\nOptions may precede or follow INPUT; -- ends option parsing.\nNo operation flag selects inspection and validation.\n  --count          Count valid records.\n  --tail N         Last N valid records; N is 0..4294967295.\n  --where KEY=TEXT Match a literal top-level key against an exact JSON string.\n                   Split at the first =; no type coercion or nested queries.\n  --help, -h       Show help (standalone).\n  --version, -V    Show version (standalone).\n\nEvery physical line is validated; malformed lines are reported and processing\ncontinues. Data stdout contains only results; diagnostics go to stderr.\nExit codes: 0 valid input; 1 internal/resource failure; 2 invalid arguments;\n            3 input/output failure; 4 malformed JSONL.\n"
}

parse_args = |args, source, operation, positional, has_input| match args {
	[] => Ok({ source, operation })
	[_, ..] if positional and has_input => Err(Usage)
	[arg, .. as rest] if positional => parse_args(
		rest,
		if arg.to_str_try() == Ok("-") {
			Stdin
		} else {
			File(arg)
		},
		operation,
		True,
		True,
	)
	[arg, ..] if arg.to_bytes().first() == Ok(45) and arg.to_str_try().is_err() => Err(Usage)
	[arg, .. as rest] if arg.to_str_try() == Ok("--") => parse_args(rest, source, operation, True, has_input)
	[arg, value, .. as rest] if arg.to_str_try() == Ok("--where") => {
		if operation != Inspect {
			return Err(Usage)
		}
		text_operand = value.to_str_try().map_err(|_| Usage)?
		parts = text_operand.split_on("=")
		if parts.len() < 2 {
			return Err(Usage)
		}
		key = match parts {
			[first, ..] => first
			[] => ""
		}
		text = Str.join_with(parts.drop_first(1), "=")
		parse_args(rest, source, Where({ key, text }), False, has_input)
	}
	[arg, value, .. as rest] if arg.to_str_try() == Ok("--tail") => {
		if operation != Inspect {
			return Err(Usage)
		}
		text_operand = value.to_str_try().map_err(|_| Usage)?
		bytes = text_operand.to_utf8()
		if bytes.is_empty() or !bytes.all(|byte| byte >= 48 and byte <= 57) {
			return Err(Usage)
		}
		n = U32.from_str(text_operand).map_err(|_| Usage)?
		parse_args(rest, source, Tail(n), False, has_input)
	}
	[arg, .. as rest] => if option_parts(arg).first() == Ok("--tail") {
		operand = Str.join_with(option_parts(arg).drop_first(1), "=")
		parse_args([OsStr.from_str("--tail"), OsStr.from_str(operand)].concat(rest), source, operation, False, has_input)
	} else if option_parts(arg).first() == Ok("--where") {
		operand = Str.join_with(option_parts(arg).drop_first(1), "=")
		parse_args([OsStr.from_str("--where"), OsStr.from_str(operand)].concat(rest), source, operation, False, has_input)
	} else if arg.to_str_try() == Ok("--count") {
		if operation != Inspect {
			return Err(Usage)
		}
		parse_args(rest, source, Count, False, has_input)
	} else if arg.to_bytes().first() == Ok(45) and arg.to_str_try() != Ok("-") {
		Err(Usage)
	} else {
		if has_input {
			return Err(Usage)
		}
		next_source = if arg.to_str_try() == Ok("-") {
			Stdin
		} else {
			File(arg)
		}
		parse_args(rest, next_source, operation, False, True)
	}
}

# An undecodable native filename is never converted to text or reconstructed.
option_parts = |arg| match arg.to_str_try() {
	Ok(text) => text.split_on("=")
	Err(_) => []
}

expect Cli.parse([OsStr.from_str("events.jsonl")]) == Ok({ source: File(OsStr.from_str("events.jsonl")), operation: Inspect })

expect Cli.parse([]) == Ok({ source: Stdin, operation: Inspect })

expect Cli.parse([OsStr.from_str("-")]) == Ok({ source: Stdin, operation: Inspect })

expect Cli.parse([OsStr.from_str("./-")]) == Ok({ source: File(OsStr.from_str("./-")), operation: Inspect })

expect Cli.parse([OsStr.from_str("--count")]) == Ok({ source: Stdin, operation: Count })

expect Cli.parse([OsStr.from_str("--tail"), OsStr.from_str("10")]) == Ok({ source: Stdin, operation: Tail(10) })

expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("status=failed")]) == Ok({ source: Stdin, operation: Where({ key: "status", text: "failed" }) })

expect Cli.parse([OsStr.from_str("--tail=10")]) == Ok({ source: Stdin, operation: Tail(10) })

expect Cli.parse([OsStr.from_str("--where=a=x=y")]) == Ok({ source: Stdin, operation: Where({ key: "a", text: "x=y" }) })

expect Cli.parse([OsStr.from_str("--"), OsStr.from_str("--count")]) == Ok({ source: File(OsStr.from_str("--count")), operation: Inspect })

# M1-03: already-supported operand/order variants are retained as regressions.
expect Cli.parse([OsStr.from_str("events.txt"), OsStr.from_str("--count")]) == Ok({ source: File(OsStr.from_str("events.txt")), operation: Count })
expect Cli.parse([OsStr.from_str("--count"), OsStr.from_str("events.txt")]) == Ok({ source: File(OsStr.from_str("events.txt")), operation: Count })
expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("-key=-value")]) == Ok({ source: Stdin, operation: Where({ key: "-key", text: "-value" }) })
expect Cli.parse([OsStr.from_str("--tail=00010"), OsStr.from_str("--"), OsStr.from_str("-events")]) == Ok({ source: File(OsStr.from_str("-events")), operation: Tail(10) })
expect Cli.parse([OsStr.from_str("--where==x")]) == Ok({ source: Stdin, operation: Where({ key: "", text: "x" }) })
expect Cli.parse([OsStr.from_str("--where=a=")]) == Ok({ source: Stdin, operation: Where({ key: "a", text: "" }) })

expect Cli.parse([OsStr.from_str("--unknown")]) == Err(Usage)

expect Cli.parse([OsStr.from_str("one"), OsStr.from_str("two")]) == Err(Usage)

expect Cli.parse([OsStr.from_str("--count"), OsStr.from_str("--count")]) == Err(Usage)

expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("status")]) == Err(Usage)

expect Cli.parse([OsStr.from_str("--tail=+1")]) == Err(Usage)

# M1-04 rejection regressions.
expect Cli.parse([OsStr.from_str("--field")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--field=skill")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--where")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--count"), OsStr.from_str("--tail"), OsStr.from_str("1")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail"), OsStr.from_str("1"), OsStr.from_str("--count")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("a=x"), OsStr.from_str("--where"), OsStr.from_str("a=x")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail"), OsStr.from_str("1"), OsStr.from_str("--tail=2")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("-"), OsStr.from_str("one")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("one"), OsStr.from_str("--"), OsStr.from_str("two")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--"), OsStr.from_str("one"), OsStr.from_str("two")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=-1")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=1.0")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail= 1")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=1 ")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=١")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=4294967296")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=9999999999999999999999999")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--where=missing")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--count=x")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--tail=0")]) == Ok({ source: Stdin, operation: Tail(0) })
expect Cli.parse([OsStr.from_str("--tail=4294967295")]) == Ok({ source: Stdin, operation: Tail(4294967295) })
expect Cli.parse([OsStr.from_str("--tail=000000000000000000000001")]) == Ok({ source: Stdin, operation: Tail(1) })

# M1-05: invalid textual operands must never be decoded lossily.
expect Cli.parse([OsStr.from_str("--where"), OsStr.unix_bytes([97, 61, 255])]) == Err(Usage)

expect Cli.parse([OsStr.unix_bytes([45, 45, 119, 104, 101, 114, 101, 61, 97, 61, 255])]) == Err(Usage)

# M1-05 native paths remain untouched; textual variants are rejected.
expect Cli.parse([OsStr.unix_bytes([102, 255])]) == Ok({ source: File(OsStr.unix_bytes([102, 255])), operation: Inspect })
expect Cli.parse([OsStr.from_str("--"), OsStr.unix_bytes([45, 255])]) == Ok({ source: File(OsStr.unix_bytes([45, 255])), operation: Inspect })
expect Cli.parse([OsStr.from_str("--tail"), OsStr.unix_bytes([49, 255])]) == Err(Usage)
expect Cli.parse([OsStr.unix_bytes([45, 255])]) == Err(Usage)
expect Cli.parse([OsStr.windows_u16s([0xD800])]) == Ok({ source: File(OsStr.windows_u16s([0xD800])), operation: Inspect })
expect Cli.parse([OsStr.from_str("--where"), OsStr.windows_u16s([97, 61, 0xD800])]) == Err(Usage)

expect Cli.parse([OsStr.from_str("--help")]) == Ok({ source: Stdin, operation: Help })

expect Cli.parse([OsStr.from_str("-h")]) == Ok({ source: Stdin, operation: Help })

expect Cli.parse([OsStr.from_str("--version")]) == Ok({ source: Stdin, operation: Version })

# M1-06 standalone information regressions.
expect Cli.parse([OsStr.from_str("-V")]) == Ok({ source: Stdin, operation: Version })
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("-h"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--version"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("-V"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("events"), OsStr.from_str("--help")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("--count")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--version"), OsStr.from_str("--version")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("--version")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("--")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--"), OsStr.from_str("--help")]) == Ok({ source: File(OsStr.from_str("--help")), operation: Inspect })
