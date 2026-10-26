Jsonl :: {}.{
	Reason : [Blank, InvalidUtf8, Bom, TooDeep, InvalidJson]

	## Validate a framed line in diagnostic order: blank, UTF-8, initial first-line
	## BOM, depth limit, then JSON grammar. Preserve the original record bytes.
	classify : Line -> [Valid, Invalid(Reason)]
	classify = |line| {
		if is_blank(line.body) {
			return Invalid(Blank)
		}
		text = match Str.from_utf8(line.body) {
			Ok(value) => value
			Err(_) => return Invalid(InvalidUtf8)
		}
		if has_initial_bom(line) {
			return Invalid(Bom)
		}
		match within_depth(text) {
			Err(reason) => Invalid(reason)
			Ok({}) => if valid_json(text) {
				Valid
			} else {
				Invalid(InvalidJson)
			}
		}
	}

	## Reject nesting above 128 before JSON parsing, ignoring brackets inside quoted
	## strings and tracking escapes. This resource precheck does not validate grammar.
	within_depth : Str -> Try({}, [TooDeep])
	within_depth = |input| {
		initial : { depth : U64, quoted : Bool, escaped : Bool }
		initial = { depth: 0, quoted: False, escaped: False }
		input.to_utf8().fold_try(initial, scan_depth).map_ok(|_| {})
	}

	## Check complete JSON grammar with the builtin parser and skip-only adapter,
	## without building a value tree or converting numbers. Call within_depth first
	## for untrusted input to bound parser recursion.
	valid_json : Str -> Bool
	valid_json = |text| {
		parsed : Try(AnyJson, _)
		parsed = Json.parse(text)
		parsed.is_ok()
	}

	State : { pending : List(U8), next_line : U64 }
	Line : { number : U64, body : List(U8) }

	start : State
	start = { pending: [], next_line: 1 }

	## Consume a byte chunk, emitting each LF-terminated physical line to the reducer.
	## Remove one CR immediately before LF; retain unfinished bytes across chunks.
	feed : State, List(U8), a, (a, Line -> a) -> { state : State, value : a }
	feed = |state, bytes, value, emit| bytes.fold(
		{ state, value },
		|current, byte| {
			if byte == 10 {
				emit_line(current.state, without_final_cr(current.state.pending), current.value, emit)
			} else {
				{ ..current, state: { ..current.state, pending: current.state.pending.append(byte) } }
			}
		},
	)

	## At successful EOF, emit a nonempty pending line without stripping a lone CR.
	## Clear emitted bytes; empty input and a trailing LF add no phantom record.
	finish : State, a, (a, Line -> a) -> { state : State, value : a }
	finish = |state, value, emit| if state.pending.is_empty() {
		{ state, value }
	} else {
		emit_line(state, state.pending, value, emit)
	}
}

## Recognize empty bodies and bodies containing only the four JSON whitespace
## bytes: space, tab, LF, and CR. Other Unicode whitespace is not blank JSONL.
is_blank : List(U8) -> Bool
is_blank = |bytes| bytes.all(|byte| byte == 32 or byte == 9 or byte == 10 or byte == 13)

## Recognize a UTF-8 BOM only at the beginning of physical line 1.
has_initial_bom : Jsonl.Line -> Bool
has_initial_bom = |line| match line.body {
	[239, 187, 191, ..] => line.number == 1
	_ => False
}

## Advance the quote/escape-aware depth scanner by one byte, rejecting an opening
## container at depth 128. Grammar validation remains the builtin parser's job.
scan_depth = |state, byte| {
	if state.quoted {
		if state.escaped {
			Ok({ ..state, escaped: False })
		} else if byte == 92 {
			Ok({ ..state, escaped: True })
		} else if byte == 34 {
			Ok({ ..state, quoted: False })
		} else {
			Ok(state)
		}
	} else if byte == 34 {
		Ok({ ..state, quoted: True })
	} else if byte == 123 or byte == 91 {
		if state.depth == 128 {
			Err(TooDeep)
		} else {
			Ok({ ..state, depth: state.depth + 1 })
		}
	} else if (byte == 125 or byte == 93) and state.depth > 0 {
		Ok({ ..state, depth: state.depth - 1 })
	} else {
		Ok(state)
	}
}

## Emit one numbered line and advance framing state. Callers decide whether CRLF
## normalization applies; LF and EOF emission share clearing and numbering rules.
emit_line : Jsonl.State, List(U8), a, (a, Jsonl.Line -> a) -> { state : Jsonl.State, value : a }
emit_line = |state, body, value, emit| {
	state: { pending: [], next_line: state.next_line + 1 },
	value: emit(value, { number: state.next_line, body }),
}

## Remove one terminal CR from an LF-terminated line body. Call only after LF;
## a lone CR at EOF remains record data.
without_final_cr = |bytes| if bytes.is_empty() {
	bytes
} else if bytes.get(bytes.len() - 1) == Ok(13) {
	bytes.drop_last(1)
} else {
	bytes
}

expect {
	actual = Jsonl.feed(Jsonl.start, "{}\n".to_utf8(), [], |lines, line| lines.append(line))
	actual == { state: { pending: [], next_line: 2 }, value: [{ number: 1, body: [123, 125] }] }
}

expect {
	partial = Jsonl.feed(Jsonl.start, "{}".to_utf8(), [], |lines, line| lines.append(line))
	actual = Jsonl.finish(partial.state, partial.value, |lines, line| lines.append(line))
	actual == { state: { pending: [], next_line: 2 }, value: [{ number: 1, body: [123, 125] }] }
}

## Collect framed lines from byte chunks for tests, including final EOF emission.
## Production uses a reducer per line instead of retaining the whole input.
framed = |chunks| {
	result = chunks.fold({ state: Jsonl.start, value: [] }, |current, chunk|
		Jsonl.feed(current.state, chunk, current.value, |lines, line| lines.append(line)))
	Jsonl.finish(result.state, result.value, |lines, line| lines.append(line))
}

# M1-07 already-supported LF/EOF cases retained as regression assertions.
expect framed([]) == { state: Jsonl.start, value: [] }
expect framed([[]]) == { state: Jsonl.start, value: [] }
expect framed(["\n".to_utf8()]).value == [{ number: 1, body: [] }]
expect framed(["{}\n\n".to_utf8()]).value == [{ number: 1, body: [123, 125] }, { number: 2, body: [] }]
expect framed(["{}\nnull".to_utf8()]).value == [{ number: 1, body: [123, 125] }, { number: 2, body: [110, 117, 108, 108] }]
expect {
	complete = framed(["{}".to_utf8()])
	Jsonl.finish(complete.state, complete.value, |lines, line| lines.append(line)) == complete
}
expect framed(["\\n\n".to_utf8()]).value == [{ number: 1, body: [92, 110] }]

expect framed(["{}\r".to_utf8(), "\n".to_utf8()]).value == [{ number: 1, body: [123, 125] }]

# M1-08 regressions: CR is removed only immediately before a physical LF.
expect framed(["\r\n".to_utf8()]).value == [{ number: 1, body: [] }]
expect framed(["\r\r\n".to_utf8()]).value == [{ number: 1, body: [13] }]
expect framed(["{}\rnull\r".to_utf8()]).value == [{ number: 1, body: [123, 125, 13, 110, 117, 108, 108, 13] }]
expect framed([[195], [169, 10]]).value == [{ number: 1, body: [195, 169] }]
expect framed([[255], [10], [195]]).value == [{ number: 1, body: [255] }, { number: 2, body: [195] }]
expect {
	partial = Jsonl.feed(Jsonl.start, [195], [], |lines, line| lines.append(line))
	partial == { state: { pending: [195], next_line: 1 }, value: [] }
}

## Verify test framing against expected lines for every two-chunk split, empty
## chunk boundaries, and one-byte chunks.
all_cuts_match = |bytes, expected| {
	initial = { offset: 0.U64, good: framed([[], bytes]).value == expected }
	result = bytes.fold(
		initial,
		|state, _byte| {
			offset = state.offset + 1
			left = bytes.sublist({ start: 0, len: offset })
			right = bytes.drop_first(offset)
			{ offset, good: state.good and framed([left, [], right]).value == expected }
		},
	)
	result.good and framed(bytes.map(|byte| [byte])).value == expected
}

expect {
	bytes = "{}\r\ncafé λ🙂\r\n\rX\n\"\\n\"\nfinal\r".to_utf8()
	expected = [
		{ number: 1, body: [123, 125] },
		{ number: 2, body: "café λ🙂".to_utf8() },
		{ number: 3, body: [13, 88] },
		{ number: 4, body: [34, 92, 110, 34] },
		{ number: 5, body: "final\r".to_utf8() },
	]
	all_cuts_match(bytes, expected)
}

expect {
	body = "x".repeat(32769).to_utf8()
	actual = framed([body.sublist({ start: 0, len: 16384 }), body.drop_first(16384), [13], [10]])
	actual.value == [{ number: 1, body }] and actual.state == { pending: [], next_line: 2 }
}

# M1-09: a blank physical line is an invalid record, not an ignored separator.
expect Jsonl.classify({ number: 1, body: [] }) == Invalid(Blank)
expect Jsonl.classify({ number: 2, body: " \t\r ".to_utf8() }) == Invalid(Blank)

expect Jsonl.classify({ number: 1, body: " \t{}\r ".to_utf8() }) == Valid

# M1-10: invalid UTF-8 is a line defect, never replacement text.
expect Jsonl.classify({ number: 1, body: [255] }) == Invalid(InvalidUtf8)
expect Jsonl.classify({ number: 1, body: [239, 187, 191, 123, 125] }) == Invalid(Bom)

# M1-10 regression bytes and precedence; grammar distinctions follow M1-12/13.
expect Jsonl.classify({ number: 1, body: [239, 187, 191, 255] }) == Invalid(InvalidUtf8)
expect Jsonl.classify({ number: 1, body: [192, 175] }) == Invalid(InvalidUtf8)
expect Jsonl.classify({ number: 2, body: [226, 130] }) == Invalid(InvalidUtf8)
expect Jsonl.classify({ number: 2, body: [237, 160, 128] }) == Invalid(InvalidUtf8)
expect Jsonl.classify({ number: 2, body: [244, 144, 128, 128] }) == Invalid(InvalidUtf8)
expect Jsonl.classify({ number: 1, body: "\"﻿\"".to_utf8() }) == Valid
expect Jsonl.classify({ number: 2, body: "﻿{}".to_utf8() }) != Invalid(Bom)
expect Jsonl.classify({ number: 1, body: " ﻿{}".to_utf8() }) != Invalid(Bom)
expect Jsonl.classify({ number: 3, body: "{\"text\":\"café λ🙂\"}".to_utf8() }) == Valid

# M1-11: enforce the application resource limit before recursive JSON parsing.
expect Jsonl.classify({ number: 1, body: "[".repeat(129).concat("0").concat("]".repeat(129)).to_utf8() }) == Invalid(TooDeep)

# M1-11 boundary and precheck regressions, independent of grammar validation.
expect Jsonl.classify({ number: 1, body: "[".repeat(128).concat("0").concat("]".repeat(128)).to_utf8() }) == Valid
expect Jsonl.classify({ number: 1, body: "{\"x\":".repeat(128).concat("0").concat("}".repeat(128)).to_utf8() }) == Valid
expect Jsonl.classify({ number: 1, body: "{\"x\":".repeat(129).concat("0").concat("}".repeat(129)).to_utf8() }) == Invalid(TooDeep)
expect Jsonl.within_depth(Json.to_str("[".repeat(200))) == Ok({})
expect Jsonl.within_depth("{\"quoted \\\" key [\":\"a\\\\b\\\"[{}] café λ\"}") == Ok({})
expect Jsonl.within_depth("{\"x\":\"\\\\\",\"y\":[]}") == Ok({})
expect Jsonl.within_depth("[[}") == Ok({})
expect Jsonl.within_depth("null") == Ok({})
expect Jsonl.classify({ number: 1, body: [239, 187, 191].concat("[".repeat(129).to_utf8()) }) == Invalid(Bom)
expect Jsonl.classify({ number: 1, body: [255].concat("[".repeat(129).to_utf8()) }) == Invalid(InvalidUtf8)

# M1-12: the skip adapter accepts any JSON value without numeric conversion.
expect Jsonl.valid_json("{}")

# Validation-only adapter: no value tree, number conversion, or serialization.
AnyJson :: {}.{

	## Build a parser that consumes one JSON value with the builtin skip routine,
	## returning an empty marker and the remaining parser state without decoding it.
	parser_for = |encoding| |state| {
		rest = Json.skip_json_value(encoding, state)?
		Ok({ value: AnyJson.{}, rest })
	}
}

# M1-12 positive grammar/precision regressions.
expect Jsonl.valid_json("[]")
expect Jsonl.valid_json("\"café\\nλ🙂\"")
expect Jsonl.valid_json("42")
expect Jsonl.valid_json("true")
expect Jsonl.valid_json("false")
expect Jsonl.valid_json("null")
expect Jsonl.valid_json("[1,true,null,\"x\",{\"nested\":[[],{}]}]")
expect Jsonl.valid_json("{\"x\":{\"a\":[1,2]},\"x\":null}")
expect Jsonl.valid_json("1e9999")
expect Jsonl.valid_json("340282366920938463463374607431768211456")
expect Jsonl.valid_json("9007199254740993")
expect Jsonl.valid_json("-0")
expect Jsonl.valid_json("-1.2345E-9999")
expect Jsonl.valid_json("\"\\uD83D\\uDE42\"")
expect Jsonl.valid_json(" {\"white\":true}\t\r ")
expect Jsonl.valid_json("\"\\\"\\\\\\b\\f\\n\\r\\t\\/\"")
expect Jsonl.valid_json("9".repeat(2000))

# M1-13: propagate builtin grammar failure through line classification.
expect Jsonl.classify({ number: 2, body: "not-json".to_utf8() }) == Invalid(InvalidJson)

# M1-13 malformed grammar and non-JSON whitespace regressions.
expect Jsonl.classify({ number: 2, body: "// comment".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "/*x*/null".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "[1,]".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "{\"x\":1,}".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "01".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "-01".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "+1".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: ".1".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "1.".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "1e".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "1e+".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "NaN".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "Infinity".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "1 2".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "{}null".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"\\q\"".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"\\uZZZZ\"".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"\\uD800\"".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"\\uDC00\"".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"\\uD800x\"".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"\\uD800\\u0041\"".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "{\"\\uD800\":1}".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: [34, 97, 9, 98, 34] }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "\"unterminated".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "[1".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "{\"x\":}".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "{".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "}".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "'single'".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: [0] }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: [12] }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: " ".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: "﻿{}".to_utf8() }) == Invalid(InvalidJson)
expect Jsonl.classify({ number: 2, body: " ﻿{}".to_utf8() }) == Invalid(InvalidJson)
expect framed(["[1,\n2]\n".to_utf8()]).value.map(Jsonl.classify) == [Invalid(InvalidJson), Invalid(InvalidJson)]
