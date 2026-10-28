import "help.txt" as usage_text : Str
import pf.OsStr

Cli :: {}.{
	Source : [Stdin, File(OsStr)]
	Operation : [Inspect, Count, Tail(U32), Where({ key : Str, text : Str }), Help, Version]
	Command : { source : Source, operation : Operation, progress : Bool }

	## Decode native arguments once, then select standalone help/version or parse a
	## command without I/O. Preserve original native values for opening filenames.
	parse : List(OsStr) -> Try(Command, [Usage])
	parse = |args| {
		arguments = args.map(decode_argument)
		match arguments {
			[{ text: Ok(text), .. }] if text == "--help" or text == "-h" => Ok({ progress: False, source: Stdin, operation: Help })
			[{ text: Ok(text), .. }] if text == "--version" or text == "-V" => Ok({ progress: False, source: Stdin, operation: Version })
			_ => parse_args(arguments, { source: Stdin, operation: Inspect, progress: False, options_ended: False, has_input: False })
		}
	}

	## Help embedded from help.txt at compile time; retain its final newline.
	help_text : Str
	help_text = usage_text
}

Argument : { native : OsStr, text : Try(Str, [Usage]) }

ParseState : { source : Cli.Source, operation : Cli.Operation, progress : Bool, options_ended : Bool, has_input : Bool }

## Keep the native argument alongside one strict UTF-8 conversion. A failed text
## conversion remains usable as a filename; option operands propagate Usage.
decode_argument : OsStr -> Argument
decode_argument = |native| { native, text: native.to_str_try().map_err(|_| Usage) }

## Consume decoded arguments, dispatching known options while retaining input and
## operation decisions. Arguments after -- go directly to input selection.
parse_args : List(Argument), ParseState -> Try(Cli.Command, [Usage])
parse_args = |args, state| match args {
	[] => Ok({ source: state.source, operation: state.operation, progress: state.progress })
	[arg, .. as rest] if state.options_ended => parse_input(arg, rest, state)
	[arg, .. as rest] => match arg.text.map_ok(|text| text.split_on("=")) {
		Ok(["--"]) => parse_args(rest, { ..state, options_ended: True })
		Ok(["--count"]) => select_operation(Count, rest, state)
		Ok(["--progress"]) => if state.progress {
			Err(Usage)
		} else {
			parse_args(rest, { ..state, progress: True })
		}
		Ok(["--tail", .. as inline]) => {
			operand = option_operand(inline, rest)?
			size = parse_tail_size(operand.text)?
			select_operation(Tail(size), operand.rest, state)
		}
		Ok(["--where", .. as inline]) => {
			operand = option_operand(inline, rest)?
			filter = parse_filter(operand.text)?
			select_operation(Where(filter), operand.rest, state)
		}
		_ => parse_input(arg, rest, state)
	}
}

## Select exactly one native input, treating - as stdin. Before --, reject other
## dash-leading arguments as unknown or undecodable options.
parse_input : Argument, List(Argument), ParseState -> Try(Cli.Command, [Usage])
parse_input = |arg, rest, state| {
	if state.has_input {
		return Err(Usage)
	}
	if !state.options_ended and arg.native.to_bytes().first() == Ok(45) and arg.text != Ok("-") {
		return Err(Usage)
	}
	source = if arg.text == Ok("-") {
		Stdin
	} else {
		File(arg.native)
	}
	parse_args(rest, { ..state, source, has_input: True })
}

## Select one operation. Inspect is the default and indicates that no operation
## flag has been supplied; repeated or conflicting flags yield Usage.
select_operation : Cli.Operation, List(Argument), ParseState -> Try(Cli.Command, [Usage])
select_operation = |operation, rest, state| {
	if state.operation != Inspect {
		return Err(Usage)
	}
	parse_args(rest, { ..state, operation })
}

## Read an equals-form operand or consume the next decoded argument, even when it
## starts with a dash. Rejoin inline parts to preserve embedded equals signs.
option_operand : List(Str), List(Argument) -> Try({ text : Str, rest : List(Argument) }, [Usage])
option_operand = |inline, args| match inline {
	[] => match args {
		[arg, .. as rest] => Ok({ text: arg.text?, rest })
		[] => Err(Usage)
	}
	_ => Ok({ text: Str.join_with(inline, "="), rest: args })
}

## Accept only nonempty ASCII decimal digits in the U32 range. Leading zeroes are
## allowed; signs, whitespace, non-ASCII digits, and overflow yield Usage.
parse_tail_size : Str -> Try(U32, [Usage])
parse_tail_size = |text| {
	bytes = text.to_utf8()
	if bytes.is_empty() or !bytes.all(|byte| byte >= 48 and byte <= 57) {
		return Err(Usage)
	}
	U32.from_str(text).map_err(|_| Usage)
}

## Split KEY=TEXT at the first equals sign, allowing an empty key or value and
## preserving subsequent equals signs. A missing separator yields Usage.
parse_filter : Str -> Try({ key : Str, text : Str }, [Usage])
parse_filter = |operand| match operand.split_on("=") {
	[key, .. as parts] if !parts.is_empty() => Ok({ key, text: Str.join_with(parts, "=") })
	_ => Err(Usage)
}

expect Cli.parse([OsStr.from_str("events.jsonl")]) == Ok({ progress: False, source: File(OsStr.from_str("events.jsonl")), operation: Inspect })

expect Cli.parse([]) == Ok({ progress: False, source: Stdin, operation: Inspect })

expect Cli.parse([OsStr.from_str("-")]) == Ok({ progress: False, source: Stdin, operation: Inspect })

expect Cli.parse([OsStr.from_str("./-")]) == Ok({ progress: False, source: File(OsStr.from_str("./-")), operation: Inspect })

expect Cli.parse([OsStr.from_str("--count")]) == Ok({ progress: False, source: Stdin, operation: Count })

expect Cli.parse([OsStr.from_str("--tail"), OsStr.from_str("10")]) == Ok({ progress: False, source: Stdin, operation: Tail(10) })

expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("status=failed")]) == Ok({ progress: False, source: Stdin, operation: Where({ key: "status", text: "failed" }) })

expect Cli.parse([OsStr.from_str("--tail=10")]) == Ok({ progress: False, source: Stdin, operation: Tail(10) })

expect Cli.parse([OsStr.from_str("--where=a=x=y")]) == Ok({ progress: False, source: Stdin, operation: Where({ key: "a", text: "x=y" }) })

expect Cli.parse([OsStr.from_str("--"), OsStr.from_str("--count")]) == Ok({ progress: False, source: File(OsStr.from_str("--count")), operation: Inspect })

# M1-03: already-supported operand/order variants are retained as regressions.
expect Cli.parse([OsStr.from_str("events.txt"), OsStr.from_str("--count")]) == Ok({ progress: False, source: File(OsStr.from_str("events.txt")), operation: Count })
expect Cli.parse([OsStr.from_str("--count"), OsStr.from_str("events.txt")]) == Ok({ progress: False, source: File(OsStr.from_str("events.txt")), operation: Count })
expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("-key=-value")]) == Ok({ progress: False, source: Stdin, operation: Where({ key: "-key", text: "-value" }) })
expect Cli.parse([OsStr.from_str("--tail=00010"), OsStr.from_str("--"), OsStr.from_str("-events")]) == Ok({ progress: False, source: File(OsStr.from_str("-events")), operation: Tail(10) })
expect Cli.parse([OsStr.from_str("--where==x")]) == Ok({ progress: False, source: Stdin, operation: Where({ key: "", text: "x" }) })
expect Cli.parse([OsStr.from_str("--where=a=")]) == Ok({ progress: False, source: Stdin, operation: Where({ key: "a", text: "" }) })

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
expect Cli.parse([OsStr.from_str("--tail=0")]) == Ok({ progress: False, source: Stdin, operation: Tail(0) })
expect Cli.parse([OsStr.from_str("--tail=4294967295")]) == Ok({ progress: False, source: Stdin, operation: Tail(4294967295) })
expect Cli.parse([OsStr.from_str("--tail=000000000000000000000001")]) == Ok({ progress: False, source: Stdin, operation: Tail(1) })

# M1-05: invalid textual operands must never be decoded lossily.
expect Cli.parse([OsStr.from_str("--where"), OsStr.unix_bytes([97, 61, 255])]) == Err(Usage)

expect Cli.parse([OsStr.unix_bytes([45, 45, 119, 104, 101, 114, 101, 61, 97, 61, 255])]) == Err(Usage)

# M1-05 native paths remain untouched; textual variants are rejected.
expect Cli.parse([OsStr.unix_bytes([102, 255])]) == Ok({ progress: False, source: File(OsStr.unix_bytes([102, 255])), operation: Inspect })
expect Cli.parse([OsStr.from_str("--"), OsStr.unix_bytes([45, 255])]) == Ok({ progress: False, source: File(OsStr.unix_bytes([45, 255])), operation: Inspect })
expect Cli.parse([OsStr.from_str("--tail"), OsStr.unix_bytes([49, 255])]) == Err(Usage)
expect Cli.parse([OsStr.unix_bytes([45, 255])]) == Err(Usage)
expect Cli.parse([OsStr.windows_u16s([0xD800])]) == Ok({ progress: False, source: File(OsStr.windows_u16s([0xD800])), operation: Inspect })
expect Cli.parse([OsStr.from_str("--where"), OsStr.windows_u16s([97, 61, 0xD800])]) == Err(Usage)

expect Cli.parse([OsStr.from_str("--help")]) == Ok({ progress: False, source: Stdin, operation: Help })

expect Cli.parse([OsStr.from_str("-h")]) == Ok({ progress: False, source: Stdin, operation: Help })

expect Cli.parse([OsStr.from_str("--version")]) == Ok({ progress: False, source: Stdin, operation: Version })

# M1-06 standalone information regressions.
expect Cli.parse([OsStr.from_str("-V")]) == Ok({ progress: False, source: Stdin, operation: Version })
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("-h"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--version"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("-V"), OsStr.from_str("extra")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("events"), OsStr.from_str("--help")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("--count")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--version"), OsStr.from_str("--version")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("--version")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--help"), OsStr.from_str("--")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--"), OsStr.from_str("--help")]) == Ok({ progress: False, source: File(OsStr.from_str("--help")), operation: Inspect })

# Optional progress is independent of source and operation selection.
expect Cli.parse([OsStr.from_str("--progress")]) == Ok({ source: Stdin, operation: Inspect, progress: True })
expect Cli.parse([OsStr.from_str("--progress"), OsStr.from_str("events.jsonl")]) == Ok({ source: File(OsStr.from_str("events.jsonl")), operation: Inspect, progress: True })
expect Cli.parse([OsStr.from_str("events.jsonl"), OsStr.from_str("--progress")]) == Ok({ source: File(OsStr.from_str("events.jsonl")), operation: Inspect, progress: True })
expect Cli.parse([OsStr.from_str("--progress"), OsStr.from_str("--count")]) == Ok({ source: Stdin, operation: Count, progress: True })
expect Cli.parse([OsStr.from_str("--progress"), OsStr.from_str("--progress")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--progress=true")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--progress"), OsStr.from_str("--help")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--version"), OsStr.from_str("--progress")]) == Err(Usage)
expect Cli.parse([OsStr.from_str("--"), OsStr.from_str("--progress")]) == Ok({ source: File(OsStr.from_str("--progress")), operation: Inspect, progress: False })
expect Cli.parse([OsStr.from_str("--where"), OsStr.from_str("--progress=x")]) == Ok({ source: Stdin, operation: Where({ key: "--progress", text: "x" }), progress: False })
