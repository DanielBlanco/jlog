import Jsonl

Operations :: {}.{
	report : Str, Summary -> Str
	report = |source, summary| {
		label = escape_source(source)
		header = "File: ${label}\nRecords: ${summary.records.to_str()}\nValid: ${summary.valid.to_str()}\nInvalid: ${summary.invalid.to_str()}\n"
		if summary.invalid == 0 {
			header
		} else {
			details = summary.errors.fold(header.concat("\nMalformed records:\n"), |text, error|
				text.concat("  line ${error.number.to_str()}: ${reason_text(error.reason)}\n"))
			omitted = summary.invalid - summary.errors.len()
			if omitted > 0 {
				details.concat("  ... ${omitted.to_str()} more invalid records\n")
			} else {
				details
			}
		}
	}

	escape_source : Str -> Str
	escape_source = |source| match Str.from_utf8(escape_bytes(source.to_utf8(), [])) {
		Ok(text) => text
		Err(_) => crash "Source escaping produced invalid UTF-8"
	}

	reason_text : Jsonl.Reason -> Str
	reason_text = |reason| match reason {
		Blank => "blank line"
		InvalidUtf8 => "invalid UTF-8"
		Bom => "BOM is not allowed"
		TooDeep => "nesting exceeds 128"
		InvalidJson => "invalid JSON"
	}

	Summary : { records : U64, valid : U64, invalid : U64, errors : List({ number : U64, reason : Jsonl.Reason }) }
	start : Summary
	start = { records: 0, valid: 0, invalid: 0, errors: [] }

	inspect_line : Summary, Jsonl.Line -> Summary
	inspect_line = |summary, line| match Jsonl.classify(line) {
		Valid => { ..summary, records: summary.records + 1, valid: summary.valid + 1 }
		Invalid(reason) => {
			..summary,
			records: summary.records + 1,
			invalid: summary.invalid + 1,
			errors: if summary.errors.len() < 100 {
				summary.errors.append({ number: line.number, reason })
			} else {
				summary.errors
			},
		}
	}
}

# M1-14: inspection totals reflect every framed line.
expect Operations.inspect_line(Operations.start, { number: 1, body: "{}".to_utf8() }) == { records: 1, valid: 1, invalid: 0, errors: [] }
expect Operations.inspect_line(Operations.start, { number: 42, body: [] }) == { records: 1, valid: 0, invalid: 1, errors: [{ number: 42, reason: Blank }] }

# Test-only driver reuses production framing/classification/reduction.
summarize = |bytes| {
	partial = Jsonl.feed(Jsonl.start, bytes, Operations.start, Operations.inspect_line)
	Jsonl.finish(partial.state, partial.value, Operations.inspect_line).value
}

expect {
	actual = summarize("\n".repeat(101).to_utf8())
	actual.records == 101 and actual.invalid == 101 and actual.errors.len() == 100
}

# M1-14 totals/physical numbering/order regression cases.
expect summarize([]) == Operations.start
expect summarize("{}\n\nnot-json\nnull".to_utf8()) == { records: 4, valid: 2, invalid: 2, errors: [{ number: 2, reason: Blank }, { number: 3, reason: InvalidJson }] }
expect {
	actual = summarize("\n".repeat(101).concat("{}\n").to_utf8())
	actual.records == actual.valid + actual.invalid and actual.valid == 1 and actual.errors.first() == Ok({ number: 1, reason: Blank }) and actual.errors.get(99) == Ok({ number: 100, reason: Blank })
}
expect summarize([255, 10, 123, 125, 10, 10]).errors == [{ number: 1, reason: InvalidUtf8 }, { number: 3, reason: Blank }]

# M1-15: report bytes are a pure rendering contract.
expect Operations.report("<stdin>", Operations.start) == "File: <stdin>\nRecords: 0\nValid: 0\nInvalid: 0\n"
expect Operations.report("mixed.jsonl", summarize("{}\n\nnot-json\nnull".to_utf8())) == "File: mixed.jsonl\nRecords: 4\nValid: 2\nInvalid: 2\n\nMalformed records:\n  line 2: blank line\n  line 3: invalid JSON\n"
expect {
	report = Operations.report("many", summarize("\n".repeat(101).to_utf8()))
	report.contains("  ... 1 more invalid records\n") and report.split_on("  line ").len() == 101
}
expect Operations.report("a\nb\tc\r", Operations.start) == "File: a\\nb\\tc\\r\nRecords: 0\nValid: 0\nInvalid: 0\n"

# Control escaping only; ordinary Unicode and native display backslashes survive.
escape_bytes = |remaining, out| match remaining {
	[] => out
	[194, byte, .. as rest] if byte >= 128 and byte <= 159 => escape_bytes(rest, out.concat(control_escape(byte)))
	[byte, .. as rest] => {
		escaped = match byte {
			10 => "\\n".to_utf8()
			13 => "\\r".to_utf8()
			9 => "\\t".to_utf8()
			8 => "\\b".to_utf8()
			12 => "\\f".to_utf8()
			_ if byte < 32 or byte == 127 => control_escape(byte)
			_ => [byte]
		}
		escape_bytes(rest, out.concat(escaped))
	}
}

control_escape = |byte| [92, 117, 48, 48, hex_digit(U8.shr_wrap(byte, 4)), hex_digit(U8.bitwise_and(byte, 15))]

hex_digit = |nibble| if nibble < 10 {
	nibble + 48
} else {
	nibble + 87
}

# M1-15 rendering/source-label regression cases.
expect Operations.report("one", summarize("{}".to_utf8())) == "File: one\nRecords: 1\nValid: 1\nInvalid: 0\n"
expect Operations.report("big", { records: 1234567, valid: 1234567, invalid: 0, errors: [] }) == "File: big\nRecords: 1234567\nValid: 1234567\nInvalid: 0\n"
expect Str.from_utf8([0, 31, 127]).map_ok(Operations.escape_source) == Ok("\\u0000\\u001f\\u007f")
expect Str.from_utf8([194, 128, 194, 133, 194, 159]).map_ok(Operations.escape_source) == Ok("\\u0080\\u0085\\u009f")
expect Operations.escape_source("café λ🙂\\name") == "café λ🙂\\name"
expect Operations.report("bad", summarize("SECRET not json".to_utf8())).contains("SECRET") == False
expect Operations.report("all", { records: 5, valid: 0, invalid: 5, errors: [{ number: 1, reason: Blank }, { number: 2, reason: InvalidUtf8 }, { number: 3, reason: Bom }, { number: 4, reason: TooDeep }, { number: 5, reason: InvalidJson }] }) == "File: all\nRecords: 5\nValid: 0\nInvalid: 5\n\nMalformed records:\n  line 1: blank line\n  line 2: invalid UTF-8\n  line 3: BOM is not allowed\n  line 4: nesting exceeds 128\n  line 5: invalid JSON\n"
