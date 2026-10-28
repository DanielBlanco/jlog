import Jsonl

Operations :: {}.{

	## Render the valid-record count for a completed input summary. The effectful
	## caller must defer this result until successful EOF; malformed lines add zero.
	count_report : Summary -> Str
	count_report = |summary| "${summary.valid.to_str()}\n"

	## Render capped data-mode diagnostics and the omitted count after EOF, using
	## escaped source labels and stable reasons without including record contents.
	data_diagnostics : Str, Summary -> Str
	data_diagnostics = |source, summary| {
		label = escape_source(source)
		details = summary.errors.fold("", |text, error|
			text.concat("jlog: ${label}: line ${error.number.to_str()}: ${reason_text(error.reason)}\n"))
		omitted = summary.invalid - summary.errors.len()
		if omitted > 0 {
			details.concat("jlog: ${label}: ${omitted.to_str()} more invalid records\n")
		} else {
			details
		}
	}

	## Render an EOF inspection summary with an escaped source label, retained error
	## details, and an omitted-detail count when needed. Always end with LF.
	report : Str, Summary -> Str
	report = |source, summary| {
		header = report_header(escape_source(source), summary)
		if summary.invalid == 0 {
			return header
		}
		details = summary.errors.fold(header.concat("\nMalformed records:\n"), |text, error|
			text.concat(render_error(error)))
		omitted = summary.invalid - summary.errors.len()
		if omitted > 0 {
			details.concat("  ... ${omitted.to_str()} more invalid records\n")
		} else {
			details
		}
	}

	## Escape C0, DEL, and C1 controls in a display label while preserving other
	## Unicode and literal backslashes. This text must not be used to open a path.
	escape_source : Str -> Str
	escape_source = |source| match Str.from_utf8(escape_bytes(source.to_utf8(), [])) {
		Ok(text) => text
		Err(_) => crash "Source escaping produced invalid UTF-8"
	}

	## Map a classified record defect to its stable human-readable diagnostic.
	reason_text : Jsonl.Reason -> Str
	reason_text = |reason| match reason {
		Blank => "blank line"
		InvalidUtf8 => "invalid UTF-8"
		Bom => "BOM is not allowed"
		TooDeep => "nesting exceeds 128"
		InvalidJson => "invalid JSON"
	}

	ErrorDetail : { number : U64, reason : Jsonl.Reason }
	Summary : { records : U64, valid : U64, invalid : U64, errors : List(ErrorDetail) }
	start : Summary
	start = { records: 0, valid: 0, invalid: 0, errors: [] }

	Tail : { limit : U64, next : U64, bodies : List(List(U8)) }

	## Start with no stored bodies, regardless of requested N. Widening the CLI's
	## U32 limit is lossless and matches the list indexing type.
	tail_start : U32 -> Tail
	tail_start = |limit| { limit: limit.to_u64(), next: 0, bodies: [] }

	## Retain a valid original record body within the requested bound. Validation
	## is the caller's job, including when the limit is zero.
	tail_push : Tail, List(U8) -> Tail
	tail_push = |tail, body| {
		if tail.limit == 0 {
			return tail
		}
		if tail.bodies.len() < tail.limit {
			return { ..tail, bodies: tail.bodies.append(body) }
		}
		bodies = match tail.bodies.set(tail.next, body) {
			Ok(value) => value
			Err(OutOfBounds) => crash "Tail ring index out of bounds"
		}
		next = tail.next + 1
		{
			..tail,
			bodies,
			next: if next == tail.limit {
				0
			} else {
				next
			},
		}
	}

	## Return retained bodies in input order for output after successful EOF.
	tail_lines : Tail -> List(List(U8))
	tail_lines = |tail| if tail.next == 0 {
		tail.bodies
	} else {
		tail.bodies.drop_first(tail.next).concat(tail.bodies.sublist({ start: 0, len: tail.next }))
	}

	Progress : { last_update_ns : U64, records : U64 }

	## Start the progress rate limiter at a supplied monotonic timestamp. The clock
	## is read by the caller so scheduling remains pure and deterministic in tests.
	progress_start : U64 -> Progress
	progress_start = |now_ns| { last_update_ns: now_ns, records: 0 }

	## Permit a periodic snapshot only after one second and newly inspected lines.
	## Guard subtraction so a backwards timestamp cannot underflow the timer.
	progress_due : Progress, U64, Summary -> Bool
	progress_due = |previous, now_ns, summary| {
		if now_ns < previous.last_update_ns {
			return False
		}
		summary.records > previous.records and now_ns - previous.last_update_ns >= 1000000000
	}

	## Render plain progress counts without a newline; the effectful writer supplies
	## it. Mark successful EOF explicitly so partial progress is never completion.
	progress_text : Summary, Bool -> Str
	progress_text = |summary, complete| {
		text = "jlog: ${summary.records.to_str()} lines inspected, ${summary.invalid.to_str()} invalid"
		if complete {
			text.concat(" (complete)")
		} else {
			text
		}
	}

	## Classify one physical line and increment inspection totals, retaining only
	## the first 100 invalid line numbers and reasons in encounter order.
	inspect_line : Summary, Jsonl.Line -> Summary
	inspect_line = |summary, line| record_classification(summary, line.number, Jsonl.classify(line))

	StreamState : { summary : Summary, tail : Tail, matches : List(List(U8)) }
	StreamFailure : [ResourceFailure, LookupFailure(U64)]
	StreamResult : Try(StreamState, StreamFailure)
	Failure : [UsageFailure, IoFailure, ResourceFailure, InternalFailure]

	## Map completed validation and explicit fatal categories to the CLI contract.
	## Fatal input/output failures override any earlier malformed-record status.
	exit_code : [Completed(Summary), Failed(Failure)] -> I32
	exit_code = |outcome| match outcome {
		Completed(summary) => if summary.invalid > 0 {
			4
		} else {
			0
		}
		Failed(UsageFailure) => 2
		Failed(IoFailure) => 3
		Failed(_) => 1
	}

	## Start shared validation and optional tail retention. A zero limit retains
	## no record bodies and serves inspection/count without separate counters.
	stream_start : U32 -> StreamState
	stream_start = |limit| { summary: start, tail: tail_start(limit), matches: [] }

	## Classify each physical line once, update shared totals, and retain only
	## valid original bodies in the bounded tail. Invalid lines still count.
	consume_line : StreamState, Jsonl.Line -> StreamState
	consume_line = |state, line| record_validated(state, line, Jsonl.classify(line))

	## Propagate sticky stream failures and consume one line with checked counters.
	## Classification is shared with filtering rather than repeated for matching.
	consume_checked : StreamResult, Jsonl.Line -> StreamResult
	consume_checked = |current, line| checked_line(current, line).map_ok(|step| step.state)

	## Validate and match one line, buffering only matching original bodies from
	## the current read. The caller must drain this buffer before the next read.
	filter_checked : StreamResult, Jsonl.Line, { key : Str, text : Str } -> StreamResult
	filter_checked = |current, line, filter| {
		step = checked_line(current, line)?
		if !step.valid {
			return Ok(step.state)
		}
		matches = Jsonl.matches_valid(line.body, filter.key, filter.text).map_err(|_| LookupFailure(line.number))?
		if matches {
			Ok({ ..step.state, matches: step.state.matches.append(line.body) })
		} else {
			Ok(step.state)
		}
	}

	## Transfer this read's matching bodies to the writer and clear retention.
	## Previously written matches are never accumulated in the next stream state.
	drain_matches : StreamState -> { bodies : List(List(U8)), state : StreamState }
	drain_matches = |state| { bodies: state.matches, state: { ..state, matches: [] } }

	## Resolve EOF versus a reported read failure. Failure drops the deferred
	## summary/tail state; the caller may render results only for a successful EOF.
	complete_stream : StreamState, [Eof, ReadError(Str)] -> Try(StreamState, [ReadError(Str)])
	complete_stream = |state, event| match event {
		Eof => Ok(state)
		ReadError(reason) => Err(ReadError(reason))
	}

}

## Check totals before classifying a physical line, then return its updated state
## and validity decision. Failure remains separate from malformed-record reasons.
checked_line : Operations.StreamResult, Jsonl.Line -> Try({ state : Operations.StreamState, valid : Bool }, Operations.StreamFailure)
checked_line = |current, line| {
	state = current?
	if state.summary.records == U64.highest or state.summary.valid == U64.highest or state.summary.invalid == U64.highest {
		return Err(ResourceFailure)
	}
	classification = Jsonl.classify(line)
	Ok({ state: record_validated(state, line, classification), valid: classification == Valid })
}

## Apply one existing classification to shared totals and optional tail storage.
## Retain pending filter bodies unchanged until their separate drain step.
record_validated : Operations.StreamState, Jsonl.Line, [Valid, Invalid(Jsonl.Reason)] -> Operations.StreamState
record_validated = |state, line, classification| {
	summary = record_classification(state.summary, line.number, classification)
	tail = match classification {
		Valid => Operations.tail_push(state.tail, line.body)
		Invalid(_) => state.tail
	}
	{ ..state, summary, tail }
}

## Update validation totals and bounded details from one already-classified
## physical line. Inspection tests and production streaming share this reducer.
record_classification : Operations.Summary, U64, [Valid, Invalid(Jsonl.Reason)] -> Operations.Summary
record_classification = |summary, number, classification| {
	counted = { ..summary, records: summary.records + 1 }
	match classification {
		Valid => { ..counted, valid: counted.valid + 1 }
		Invalid(reason) => {
			..counted,
			invalid: counted.invalid + 1,
			errors: retain_error(counted.errors, { number, reason }),
		}
	}
}

## Render the four header lines from an already escaped source label. Joining a
## final empty string supplies exactly one trailing LF.
report_header : Str, Operations.Summary -> Str
report_header = |label, summary| Str.join_with(
	[
		"File: ${label}",
		"Records: ${summary.records.to_str()}",
		"Valid: ${summary.valid.to_str()}",
		"Invalid: ${summary.invalid.to_str()}",
		"",
	],
	"\n",
)

## Render one retained physical-line error without including the record body.
render_error : Operations.ErrorDetail -> Str
render_error = |error| "  line ${error.number.to_str()}: ${Operations.reason_text(error.reason)}\n"

## Retain the first 100 error details in encounter order. Totals continue to grow
## independently after this bounded list is full.
retain_error : List(Operations.ErrorDetail), Operations.ErrorDetail -> List(Operations.ErrorDetail)
retain_error = |errors, error| if errors.len() < 100 {
	errors.append(error)
} else {
	errors
}

# M1-14: inspection totals reflect every framed line.
expect Operations.inspect_line(Operations.start, { number: 1, body: "{}".to_utf8() }) == { records: 1, valid: 1, invalid: 0, errors: [] }
expect Operations.inspect_line(Operations.start, { number: 42, body: [] }) == { records: 1, valid: 0, invalid: 1, errors: [{ number: 42, reason: Blank }] }

## Summarize test bytes through production framing and classification, including
## a final unterminated record at EOF.
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

## Append escaped UTF-8 label bytes to out, recognizing C1's two-byte encoding.
## Ordinary Unicode bytes and native display backslashes pass through unchanged.
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

## Encode a control value as a six-byte Unicode escape with lowercase hex digits.
control_escape = |byte| [92, 117, 48, 48, hex_digit(U8.shr_wrap(byte, 4)), hex_digit(U8.bitwise_and(byte, 15))]

## Convert a nibble in 0..15 to its lowercase ASCII hexadecimal digit byte.
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

# M2-01: count output is one ungrouped decimal integer and a final LF at EOF.
expect Operations.count_report(Operations.start) == "0\n"
expect Operations.count_report(summarize("{}\nnull\n42".to_utf8())) == "3\n"
expect Operations.count_report(summarize("\nnot-json\n".to_utf8())) == "0\n"
expect Operations.count_report(summarize("{}\n\nnot-json\nnull".to_utf8())) == "2\n"
expect Operations.count_report({ records: 1234569, valid: 1234567, invalid: 2, errors: [] }) == "1234567\n"
expect Operations.count_report({ records: 18446744073709551615, valid: 18446744073709551615, invalid: 0, errors: [] }) == "18446744073709551615\n"
expect {
	partial = Jsonl.feed(Jsonl.start, "{}\nnull".to_utf8(), Operations.start, Operations.inspect_line)
	completed = Jsonl.finish(partial.state, partial.value, Operations.inspect_line)
	partial.value.valid == 1 and Operations.count_report(completed.value) == "2\n"
}

# M2-02: data diagnostics belong on stderr and retain physical line references.
expect Operations.data_diagnostics("events.jsonl", summarize("{}\n\nnot-json\nnull".to_utf8())) == "jlog: events.jsonl: line 2: blank line\njlog: events.jsonl: line 3: invalid JSON\n"
expect Operations.data_diagnostics("<stdin>", Operations.start) == ""
expect Operations.data_diagnostics("valid", summarize("{}\nnull\n".to_utf8())) == ""
expect Operations.data_diagnostics("a\nb\t", summarize("SECRET not json".to_utf8())) == "jlog: a\\nb\\t: line 1: invalid JSON\n"
expect {
	diagnostics = Operations.data_diagnostics("many", summarize("\n".repeat(103).to_utf8()))
	diagnostics.split_on(": line ").len() == 101 and diagnostics.ends_with("jlog: many: 3 more invalid records\n")
}

# M2-04: tail grows with received valid records, never with the requested limit.
expect Operations.tail_lines(Operations.tail_push(Operations.tail_start(1), "null".to_utf8())) == ["null".to_utf8()]
expect Operations.tail_lines(Operations.tail_start(0)) == []
expect Operations.tail_lines(Operations.tail_start(10)) == []
expect {
	tail = ["{}".to_utf8(), "null".to_utf8(), "42".to_utf8()].fold(Operations.tail_start(0), Operations.tail_push)
	tail.bodies.is_empty() and tail.next == 0
}
expect {
	tail = ["{}".to_utf8(), "null".to_utf8()].fold(Operations.tail_start(3), Operations.tail_push)
	Operations.tail_lines(tail) == ["{}".to_utf8(), "null".to_utf8()]
}
expect {
	tail = ["{}".to_utf8(), "null".to_utf8()].fold(Operations.tail_start(4294967295), Operations.tail_push)
	tail.limit == 4294967295 and tail.bodies.len() == 2 and Operations.tail_lines(tail) == ["{}".to_utf8(), "null".to_utf8()]
}

# M2-05: overflowing a full tail evicts the oldest valid record.
expect {
	tail = ["1".to_utf8(), "2".to_utf8(), "3".to_utf8()].fold(Operations.tail_start(2), Operations.tail_push)
	Operations.tail_lines(tail) == ["2".to_utf8(), "3".to_utf8()]
}
expect {
	tail = ["1".to_utf8(), "2".to_utf8(), "3".to_utf8(), "4".to_utf8(), "5".to_utf8()].fold(Operations.tail_start(2), Operations.tail_push)
	tail.bodies.len() == 2 and Operations.tail_lines(tail) == ["4".to_utf8(), "5".to_utf8()]
}
expect {
	tail = ["1".to_utf8(), "2".to_utf8(), "3".to_utf8()].fold(Operations.tail_start(1), Operations.tail_push)
	Operations.tail_lines(tail) == ["3".to_utf8()] and tail.next == 0
}
expect {
	before = ["1".to_utf8(), "2".to_utf8()].fold(Operations.tail_start(2), Operations.tail_push)
	after = Operations.tail_push(before, "3".to_utf8())
	Operations.tail_lines(before) == ["1".to_utf8(), "2".to_utf8()] and Operations.tail_lines(after) == ["2".to_utf8(), "3".to_utf8()]
}

# M2-07: detected exhaustion is a fatal resource failure, never wrapped totals.
expect Operations.consume_checked(Ok({ ..Operations.stream_start(0), summary: { records: 18446744073709551615, valid: 18446744073709551615, invalid: 0, errors: [] } }), { number: 1, body: "{}".to_utf8() }) == Err(ResourceFailure)
expect Operations.consume_checked(Err(ResourceFailure), { number: 1, body: "{}".to_utf8() }) == Err(ResourceFailure)
expect {
	seed = { ..Operations.stream_start(0), summary: { records: 18446744073709551614, valid: 18446744073709551614, invalid: 0, errors: [] } }
	first = Operations.consume_checked(Ok(seed), { number: 1, body: "{}".to_utf8() })
	first.map_ok(|state| state.summary.valid) == Ok(18446744073709551615) and Operations.consume_checked(first, { number: 2, body: "null".to_utf8() }) == Err(ResourceFailure)
}
expect Operations.consume_checked(Ok({ ..Operations.stream_start(0), summary: { records: 18446744073709551615, valid: 0, invalid: 18446744073709551615, errors: [] } }), { number: 1, body: [] }) == Err(ResourceFailure)
expect Operations.exit_code(Completed(Operations.start)) == 0
expect Operations.exit_code(Completed({ ..Operations.start, records: 1, invalid: 1 })) == 4
expect Operations.exit_code(Failed(UsageFailure)) == 2
expect Operations.exit_code(Failed(IoFailure)) == 3
expect Operations.exit_code(Failed(ResourceFailure)) == 1
expect Operations.exit_code(Failed(InternalFailure)) == 1

# M2-09: a reported read failure discards all deferred results after a prefix.
expect {
	prefix = Operations.consume_line(Operations.stream_start(2), { number: 1, body: "{}".to_utf8() })
	Operations.complete_stream(prefix, ReadError("injected read failure")) == Err(ReadError("injected read failure"))
}
expect {
	prefix = Operations.consume_line(Operations.stream_start(2), { number: 1, body: "{}".to_utf8() })
	Operations.complete_stream(prefix, Eof) == Ok(prefix)
}
expect {
	invalid = Operations.consume_line(Operations.stream_start(2), { number: 1, body: [] })
	prefix = Operations.consume_line(invalid, { number: 2, body: "null".to_utf8() })
	Operations.exit_code(Completed(prefix.summary)) == 4 and Operations.complete_stream(prefix, ReadError("mid-read")) == Err(ReadError("mid-read")) and Operations.exit_code(Failed(IoFailure)) == 3
}

# M3-07: filtering shares validation, drains bounded matches, and preserves failure.
expect {
	filter = { key: "status", text: "failed" }
	consume = |value, line| Operations.filter_checked(value, line, filter)
	partial = Jsonl.feed(Jsonl.start, "bad\n{\"status\":\"failed\"}\nnull\n".to_utf8(), Ok(Operations.stream_start(0)), consume)
	match partial.value {
		Ok(state) => state.summary == { records: 3, valid: 2, invalid: 1, errors: [{ number: 1, reason: InvalidJson }] } and state.matches == ["{\"status\":\"failed\"}".to_utf8()] and state.tail.bodies.is_empty()
		Err(_) => False
	}
}
expect {
	body = " {\"status\":\"failed\"} ".to_utf8()
	match Operations.filter_checked(Ok(Operations.stream_start(0)), { number: 1, body }, { key: "status", text: "failed" }) {
		Ok(prefix) => {
			written = Operations.drain_matches(prefix)
			next = Operations.drain_matches(written.state)
			written.bodies == [body] and written.state.matches.is_empty() and next.bodies.is_empty() and Operations.complete_stream(written.state, ReadError("mid-read")) == Err(ReadError("mid-read")) and Operations.exit_code(Failed(IoFailure)) == 3
		}
		Err(_) => False
	}
}
expect {
	filter = { key: "status", text: "failed" }
	consume = |value, line| Operations.filter_checked(value, line, filter)
	partial = Jsonl.feed(Jsonl.start, "bad\n{\"status\":\"failed\"}\n".to_utf8(), Ok(Operations.stream_start(0)), consume)
	match partial.value {
		Ok(prefix) => {
			written = Operations.drain_matches(prefix)
			written.bodies.len() == 1 and Operations.exit_code(Completed(written.state.summary)) == 4 and Operations.complete_stream(written.state, ReadError("mid-read")) == Err(ReadError("mid-read")) and Operations.exit_code(Failed(IoFailure)) == 3
		}
		Err(_) => False
	}
}
expect Operations.filter_checked(Err(LookupFailure(42)), { number: 43, body: [] }, { key: "", text: "" }) == Err(LookupFailure(42))
expect Operations.filter_checked(Err(ResourceFailure), { number: 43, body: [] }, { key: "", text: "" }) == Err(ResourceFailure)
expect Operations.filter_checked(Ok({ ..Operations.stream_start(0), summary: { records: 18446744073709551615, valid: 18446744073709551615, invalid: 0, errors: [] } }), { number: 1, body: "{}".to_utf8() }, { key: "", text: "" }) == Err(ResourceFailure)

# Progress scheduling and rendering are independent of a real clock or stream.
expect Operations.progress_start(123) == { last_update_ns: 123, records: 0 }
expect Operations.progress_due(Operations.progress_start(0), 999999999, { ..Operations.start, records: 1, valid: 1 }) == False
expect Operations.progress_due(Operations.progress_start(0), 1000000000, { ..Operations.start, records: 1, valid: 1 })
expect Operations.progress_due(Operations.progress_start(0), 1000000000, Operations.start) == False
expect Operations.progress_due({ last_update_ns: 1000000000, records: 2 }, 1999999999, { ..Operations.start, records: 3, valid: 3 }) == False
expect Operations.progress_due({ last_update_ns: 1000000000, records: 2 }, 2000000000, { ..Operations.start, records: 3, valid: 3 })
expect Operations.progress_due({ last_update_ns: 1000000000, records: 2 }, 3000000000, { ..Operations.start, records: 2, valid: 2 }) == False
expect Operations.progress_due({ last_update_ns: 100, records: 0 }, 99, { ..Operations.start, records: 1, valid: 1 }) == False
expect Operations.progress_text(Operations.start, True) == "jlog: 0 lines inspected, 0 invalid (complete)"
expect Operations.progress_text({ ..Operations.start, records: 42, valid: 40, invalid: 2 }, False) == "jlog: 42 lines inspected, 2 invalid"
