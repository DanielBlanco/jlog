# Roc Feasibility for jlog v0.1

Research date: 2026-10-18. The proposed behavior is defined in
[the v0.1 specification](../specs/jlog-v0.1.md). This report distinguishes local
execution, inspected source, and recommendations. Only documentation was added
to the repository; capability probes were created outside it in temporary storage.

Final investigation decision: **REDUCED SCOPE** — `--field` is deferred to v0.2.
The user approved this scope for planning; the specification now reflects it.
Keep inspection, count, tail, string-only filtering, and the depth-128 limit.
The extraction experiments below remain research evidence, not v0.1 deliverables.

## 1. Verified toolchain and platform

| Component | Evidence and recommendation |
| --- | --- |
| Installed compiler | `command -v roc` resolves to `/Users/dblanco/.local/roc/roc`; `roc version` reports `nightly-2026-10-09-258ab27` |
| Research host | `uname -sm` reports `Darwin arm64` |
| Compiler distribution | Pin the [official new-compiler nightly](https://github.com/roc-lang/nightlies/releases/tag/nightly-2026-10-09-258ab27), built from Roc commit `258ab27`; do not select the older alpha compiler |
| CLI platform | Existing `main.roc` pins [basic-cli 0.25.0](https://github.com/roc-lang/basic-cli/releases/tag/0.25.0), release commit `6e787d2` |
| Platform bundle | `https://github.com/roc-lang/basic-cli/releases/download/0.25.0/CZsY7tYZwR3rj9kYbpaCfxki2yVAaRL8bBwMLvB2xkbA.tar.zst` |

The cached platform bundle was inspected directly. Its `main.roc` declares
`arm64mac`, `x64mac`, `x64musl`, `arm64musl`, and `x64win`, and contains the target
host/linker libraries. The published [platform README](https://github.com/roc-lang/basic-cli#supported-targets)
also lists these targets. Compiler target names alone are insufficient: the
platform must supply matching host artifacts.

The installed macOS archive is
`roc_nightly-macos_apple_silicon-2026-10-09-258ab27.tar.gz`; its locally measured
SHA-256 is `aa6339579730fcea4753940bec21f5d8cf8be8e25659ec001abccbc3463a60b2`.
This is an observed local hash, not independently authenticated upstream provenance.
Record download URLs and checksums for each CI compiler archive when configuring CI.

Repository instructions are partly stale: the compiler bundle is outside the
checkout, and `main.roc` already exists as a file-size example. `.tool-versions`
pins Node 24.13.0, not Roc. Do not treat Node as an application/build dependency.
Existing `roc check main.roc` passed; existing `roc fmt --check main.roc` failed.
Neither the example nor the contributor guide was changed during this research.

## 2. Official references and verified APIs

Start with the [official examples](https://www.roc-lang.org/examples/),
[new-compiler tutorial](https://github.com/roc-lang/roc/blob/main/docs/mini-tutorial-new-compiler.md),
and [versioned basic-cli documentation](https://roc-lang.github.io/basic-cli/0.25.0/).
The website's main builtin documentation can move independently of the pinned
compiler; confirm signatures locally before use.

| Need | Verified API / behavior |
| --- | --- |
| Entry point and arguments | `main! : List(OsStr) => Try({}, [Exit(I32)])`; arguments exclude the executable name; `Env.program_name!` retrieves that separately |
| CLI parsing | Pattern matching over arguments and a small pure parser are sufficient; convert textual operands with `OsStr.to_str_try`; preserve paths with `Path.from_os_str` |
| Incremental file input | `File.open_reader!` returns a buffered `Reader`; `Reader.read_line!` returns `Try(List(U8), _)`, includes LF when present, and returns an empty list at EOF |
| Other file reads | `Reader.read_up_to!`, `read_exactly!`, and `chunks` are available; chunk boundaries need not align with lines or UTF-8 |
| Stdin | `Stdin.bytes! : () => Try(List(U8), [EndOfFile, StdinErr(IOErr)])`; reads at most 16,384 bytes per call |
| Text stdin | `Stdin.line!` returns `Str`; avoid it when distinguishing invalid UTF-8 from I/O failure and preserving physical framing matters |
| UTF-8 | `Str.from_utf8` validates bytes and returns a `BadUtf8` error; no lossy conversion for record validation |
| Output | `Stdout.line!`, `write!`, `write_bytes!`, and the equivalent `Stderr` functions return explicit write errors |
| I/O failures | `IOErr` includes `NotFound`, `PermissionDenied`, `IsADirectory`, and `BrokenPipe`; source errors use `PathErr`/`FileErr` |
| Exit status | Platform `main_for_host!` maps `Ok({})` to 0 and `Err(Exit(code))` to that code; other uncaught errors print a generic message and exit 1 |
| JSON | Builtin `Json.parse` decodes a known target type; `Json.to_str` encodes supported types; `Json.skip_json_value` is usable inside a custom `parser_for` adapter |
| Unit tests | Top-level `expect`; `roc test` follows imported local modules/path dependencies, excluding URL dependency tests |

Signatures above were checked against cached 0.25.0 sources and local probes,
not inferred from older `Task`, `Arg`, or `Decode.from_bytes` examples. Current
syntax uses `app [main!] { pf: platform "…" }`, `import pf.File`, `|arg|` lambdas,
`match`, `Try` with `Ok`/`Err`, `?`, effectful `!` functions with `=>`, and nominal
types with associated methods. A local probe also compiled `var $counter`/`while`.
Use annotations for integer counts; unconstrained numeric literals can infer
an unsuitable numeric type.

The [official effect-loop example](https://www.roc-lang.org/examples/LoopEffect/README.html)
demonstrates repeated stdin reading and `Err(Exit(1))`. The
[file/argument example](https://www.roc-lang.org/examples/CommandLineArgsFile/README.html)
and [typed JSON example](https://www.roc-lang.org/examples/Json/README.html) provide
starting points. The JSON example's argument pattern still includes a program-name
slot, unlike the pinned platform: follow the inspected platform and executable
probe for argument indexing.

## 3. File processing and arbitrary JSON

### Incremental input

For files, use one buffered reader and consume one byte line at a time. Distinguish
an empty byte list at EOF from `[10]`, which is a blank physical line. Strip LF and
its preceding CR for framing, retain the original body for output, then validate
UTF-8 and JSON. Reader resources close when their last reference is released.

For stdin, accumulate `Stdin.bytes!` chunks until LF, processing completed lines
and retaining only the incomplete suffix. Decode UTF-8 after framing so a character
split between chunks remains valid. At EOF process a nonempty suffix once.
Do not use `Path.read_utf8!`, `Stdin.read_to_end!`, or `Stream.collect!` for input;
they collect data and undermine the intended memory bound.

Stdin support is technically feasible in v0.1. Its extra cost is a small byte-line
framer, including tests for split CRLF/UTF-8 and malformed bytes. File input can
use the same pure line classifier without introducing a generic I/O framework.

### JSON capabilities: verified boundaries

The [builtin Encoding/Json reference](https://www.roc-lang.org/docs/main/Encoding/)
and [Dict reference](https://www.roc-lang.org/docs/main/Dict/) describe typed
parsing and dictionary operations. The following results come from the installed
compiler, not an assumed `Json.Value` API. The initial nine capability `expect` blocks passed
with both `roc test --opt=dev` and `roc test --opt=speed`, with exit 0 and no warnings.
Negative `roc check` probes exited 1 for `Json.Value` (missing nested type) and
`Encoding.JsonEncoding` / `Encoding.JsonState` (undeclared types).

| Capability | Executable evidence and limitation |
| --- | --- |
| Arbitrary JSON validation | A nominal adapter delegates to `Json.skip_json_value`; `Json.parse` checks complete consumption. All six kinds, nested heterogeneous values, `1e9999`, and an integer above U128 passed. Malformed grammar/escapes and lone surrogates failed as expected. |
| Dynamic keys | `Json.parse` into `Dict(Str, Str)` plus `Dict.get` handled literal dotted, empty, equals-containing, Unicode-escaped keys, and `KeyNotFound`. Keys need not be known at compile time. |
| Heterogeneous objects | `Dict(Str, Field)` with a small adapter retained decoded strings and classified other values by skipping them. This verifies string-only lookup among arbitrary values; it does **not** retain those other values for extraction. |
| Duplicate keys | `{"x":"first","\u0078":"last"}` looked up as `"last"`; a later null replaced an earlier string in the classification probe. Last decoded key wins in these dictionary cases. Nested output duplicate handling still needs an encoder test. |
| Integer accuracy | Parsing `9007199254740993` as U64 and encoding it preserved the value; F64 round-tripped it as `9007199254740992`. F64 is unsuitable as the general numeric representation. |
| Numeric range | F64 parsing rejected `1e9999`; U128 parsing rejected `340282366920938463463374607431768211456` (2^128). The validation adapter accepted both. Finite numeric types alone do not cover the accepted JSON number syntax. |
| General decode/re-encode | **Not verified.** No builtin `Json.Value` exists. Typed records/dictionaries do not provide a ready-made heterogeneous value tree, exact arbitrary numbers, or general field serialization. |
| Raw-token access | Construction through `Encoding.JsonEncoding` / `Encoding.JsonState` was rejected. No supported raw-value/span API was established; token preservation is not assumed easy. |

The record-based classification adapter uses existing JSON parsers, not new JSON
grammar rules. A separate exploratory union-based adapter probe caused a compiler
SIGSEGV during `roc check`; its cause was not isolated. The passing record-based
probe is the established evidence; this is not proof that union decoders in
general are unsupported. Keep complex adapter designs conditional on executable
checks against this pin.

### Reproducible capability evidence

Save the following pure probe as `ReviewJson.roc` in a temporary directory and run:

```sh
roc check /tmp/ReviewJson.roc
roc test --opt=dev --verbose /tmp/ReviewJson.roc
roc test --opt=speed --verbose /tmp/ReviewJson.roc
```

The observed result was `All (9) tests passed` in each test mode. This probe only
checks compiler/builtin behavior; it has no application entry point, I/O loop,
filter implementation, or extractor. `Field.text` is a probe convention: one
string for a string value, an empty list for every other value.

<details>
<summary>Executable Roc probe</summary>

```roc
ReviewJson :: {}

Any :: {}.{
	parser_for = |encoding| |state| {
		rest = Json.skip_json_value(encoding, state)?
		Ok({ value: Any.{}, rest })
	}
}

Field :: { text : List(Str) }.{
	parser_for = |encoding| |state|
		match Json.parse_str(encoding, state) {
			Ok(parsed) => Ok({ value: Field.{ text: [parsed.value] }, rest: parsed.rest })
			Err(_) => {
				rest = Json.skip_json_value(encoding, state)?
				Ok({ value: Field.{ text: [] }, rest })
			}
		}
}

valid = |input| {
	parsed : Try(Any, _)
	parsed = Json.parse(input)
	parsed.is_ok()
}

expect ["null", "true", "42", "\"café\\nλ\"", "[1,true,null]", "{\"x\":{\"a\":[]}}", "1e9999", "340282366920938463463374607431768211456"].all(valid)
expect ["1 2", "01", "[1,]", "{\"x\":}", "\"\\q\"", "\"\\uD800\""].all(|input| !valid(input))
expect {
	parsed : Try(Dict(Str, Field), _)
	parsed = Json.parse("{\"x\":\"first\",\"\\u0078\":\"last\",\"request.status\":\"literal\",\"n\":9007199254740993,\"nested\":{\"a\":[1,true]}}")
	parsed.map_ok(|fields| fields.get("x").map_ok(|field| field.text)) == Ok(Ok(["last"]))
}
expect {
	parsed : Try(Dict(Str, Field), _)
	parsed = Json.parse("{\"x\":\"first\",\"x\":null}")
	parsed.map_ok(|fields| fields.get("x").map_ok(|field| field.text)) == Ok(Ok([]))
}
expect {
	parsed : Try(Dict(Str, Str), _)
	parsed = Json.parse("{\"request.status\":\"literal\",\"\\u0073kill\":\"Roc\",\"\":\"empty\",\"a=b\":\"equals\"}")
	parsed.map_ok(|fields| (fields.get("request.status"), fields.get("skill"), fields.get(""), fields.get("a=b"), fields.get("missing"))) == Ok((Ok("literal"), Ok("Roc"), Ok("empty"), Ok("equals"), Err(KeyNotFound)))
}
expect {
	parsed : Try(F64, _)
	parsed = Json.parse("9007199254740993")
	parsed.map_ok(|number| Json.to_str_try(number)) == Ok(Ok("9007199254740992"))
}
expect {
	parsed : Try(U64, _)
	parsed = Json.parse("9007199254740993")
	parsed.map_ok(|number| Json.to_str(number)) == Ok("9007199254740993")
}
expect {
	parsed : Try(F64, _)
	parsed = Json.parse("1e9999")
	parsed.is_err()
}
expect {
	parsed : Try(U128, _)
	parsed = Json.parse("340282366920938463463374607431768211456")
	parsed.is_err()
}
```

</details>

These initial samples did not establish full JSON conformance, lossless
arbitrary-value encoding, depth enforcement, or large-input behavior. The final
investigation below resolves depth enforcement; full conformance and large-input
measurements remain release tests. `Json.parse_str` and typed `Json.to_str` can serve decoded string
comparisons/encoding, but neither constitutes a general JSON value model.

### Extraction alternatives and recommendation

The revised field-output contract permits semantically equivalent single-line
JSON. Whitespace, escaping, object order, and numeric spelling may change; exact
numeric meaning, decoded strings, array order, and last-key-wins semantics may
not. Replace field-format byte assertions with semantic-fidelity tests, using an
exact decimal/integer oracle rather than F64. Retain byte assertions for tail and
filter output. This relaxation does not make a lossy numeric representation acceptable.

| Alternative | Tradeoff and disposition |
| --- | --- |
| Existing typed builtins and a small adapter | Proven for validation and dynamic string classification/lookup. Reuse these capabilities; they avoid a handwritten parser. They do not yet solve general field encoding. |
| Compatible JSON value package | Prefer an existing package with dynamic values and exact numbers if its pinned version passes the probes. The inspected [roc-json README](https://github.com/lukewilliamboswell/roc-json) and [source](https://github.com/lukewilliamboswell/roc-json/blob/main/package/Json.roc) use older `Decode`/`Result`/opaque-wrapper APIs and legacy linker instructions. No compatible release or suitable general value model was verified; this is a candidate for investigation, not a dependency recommendation. |
| Existing parser combinators with an application value adapter | Can delegate grammar to builtins instead of rewriting JSON. Requires proof of recursive heterogeneous values, exact numbers, duplicate behavior, and encoding; no such complete adapter was verified. Avoid a large custom DOM framework. |
| Upstream value/raw-value support or a different tested toolchain pin | Could remove application parsing machinery, at the cost of upstream work or a toolchain migration. No newer compatible API was verified; any pin change must rerun probes and preserve the specified behavior. |
| Handwritten token locator/parser | Carries quoting, nesting, Unicode, numeric, duplicate-key, and maintenance risks. Removing token-format preservation removes the original reason to prefer a scanner. It is **not selected** for v0.1. |

### Final investigation 1: arbitrary field extraction

**Finding:** schema-specific extraction works, but no straightforward general,
lossless field representation was verified on the pin. `ExtractionProbe.roc`
passed 15 executable `expect` blocks in both dev and speed modes:

| Input value / case | Verified outcome |
| --- | --- |
| Unicode strings, newline/quote/backslash escapes | `Dict(Str, Str)` lookup and `Json.to_str` preserve decoded content and emit valid quoted JSON. |
| Both booleans | `Dict(Str, Bool)` lookup and encoding emit `true` / `false`. |
| Null | A small adapter over `Json.parse_null` / `Json.encode_null` round-trips `null`. |
| Arrays | `List(U64)` round-trips numeric arrays; a known `(Str, Bool, Null)` tuple round-trips a heterogeneous array. The tuple fixes the shape at compile time. |
| Nested objects | A known nested record schema decodes, extracts, re-encodes, and parses back to equal values. This is not arbitrary-shape object support. |
| Duplicate keys | Escaped top-level duplicates resolve to the last value; nested `Dict(Str, Str)` duplicates collapse to the last decoded key on re-encoding. |
| Number 2^128 | U128 and Dec decoding fail with `InvalidJson`, despite the JSON being syntactically valid. |
| Number 2^128+1 | F64 decoding produces the same F64 as 2^128: precision is lost. |
| `1e9999` | F64 and Dec decoding fail with `InvalidJson`; neither provides a lossless extraction representation. |
| Arbitrary values through the skip adapter | `Dict(Str, Any)` accepts huge numbers and nested heterogeneous data, but does not retain their values. |

Additional negative compiler probes confirmed that encoding this skip-only `Any`
value requires an absent `encoder_for`, matching `JsonState` as a plain `Input`
tag union fails, and inserting `Json.parse_json_number` into `parser_for` fails:
that helper takes `Str`, while the callback receives an opaque `JsonState`.
These results rule out the small adapters attempted, not all possible Roc designs.

An exact-number representation, recursive value model, and codec could be designed,
or source spans could be located manually, but neither was established as a small
existing abstraction. The previously inspected package was not verified compatible.
A complete parser, custom serialization framework, platform/FFI change, or runtime
`jq` dependency is disproportionate for this learning release.

**Recommendation:** defer `--field` to v0.2 rather than weaken numeric accuracy or
ship only some value kinds under that flag. The cost is postponing convenient
projection; users can pipe the remaining CLI's JSONL output to an existing tool.
The benefit is shipping a useful Roc CLI without a new JSON subsystem. Validation
still accepts huge valid numbers, and string-only filtering still skips non-string
values without converting them. Revisit field extraction when a compatible value
or raw-value API/package passes the full deferred acceptance tests.

### Final investigation 2: nesting depth

**Finding:** keep the depth limit of 128. No builtin configurable limit was verified;
the unguarded validator accepted arrays and objects at both depths 128 and 129.
A small application resource precheck can enforce the limit before invoking it,
without parsing JSON grammar. `DepthProbe.roc` passed 16 checks in both modes.

| Case | Builtin validator | Precheck followed by validator |
| --- | --- | --- |
| 128 nested arrays | Accepts | Accepts |
| 129 nested arrays | Accepts | Rejects as `NestingTooDeep` before parsing |
| 128 nested objects | Accepts | Accepts |
| 129 nested objects | Accepts | Rejects as `NestingTooDeep` before parsing |
| Scalar / empty containers | Accepts | Accepts |
| More than 128 brackets inside a string | Accepts | Accepts; string contents do not count |
| Quotes, escaped backslashes, Unicode, delimiters inside strings/keys | Accepts tested fixtures | Accepts tested fixtures |
| Malformed `[[}` | Rejects | Precheck allows it; builtin rejects it |

The precheck tracks only a bounded counter and two booleans (inside string,
previous backslash). Outside strings it counts opening/closing braces and brackets;
at the 129th opening it returns immediately. It does not validate delimiters,
keys, numbers, escapes, or final balance: those remain the builtin parser's job.
The explicit result match invokes JSON parsing only after the precheck succeeds.
Run it after UTF-8/BOM classification to preserve the existing diagnostic priority.

This is a small linear prepass over the current line with fixed counter state,
not a JSON grammar parser, token extractor, or serialization framework. It avoids
sending excessive nesting to the recursive validator. No depth requirement change
is needed. These bounded tests do not establish whole-application memory behavior
or Linux runtime compatibility; those remain final release gates.

### Reproducing the final experiments

The two complete pure probes are embedded below so the findings survive temporary
file cleanup. Save them under their exact filenames in a temporary directory:

```sh
roc check /tmp/ExtractionProbe.roc
roc check /tmp/DepthProbe.roc
roc fmt --check /tmp/ExtractionProbe.roc /tmp/DepthProbe.roc
roc test --opt=dev --verbose /tmp/ExtractionProbe.roc
roc test --opt=speed --verbose /tmp/ExtractionProbe.roc
roc test --opt=dev --verbose /tmp/DepthProbe.roc
roc test --opt=speed --verbose /tmp/DepthProbe.roc
```

Observed: 15 extraction checks and 16 depth checks pass in each mode, with exit 0
and no compiler warnings. Expected rejection/rounding cases are assertions about
API limitations, not successful arbitrary extraction. All experiments used the
pinned compiler on macOS ARM64; no application sources or build configuration
were changed.

<details>
<summary>ExtractionProbe.roc — typed round-trips and numeric limitations</summary>

```roc
ExtractionProbe :: {}

Null :: {}.{
	parser_for = |encoding| |state| {
		rest = Json.parse_null(encoding, state)?
		Ok({ value: Null.{}, rest })
	}
	encoder_for = |encoding| |_, state| Json.encode_null(encoding, state)
}

Any :: {}.{
	parser_for = |encoding| |state| {
		rest = Json.skip_json_value(encoding, state)?
		Ok({ value: Any.{}, rest })
	}
}

expect {
	parsed : Try(Dict(Str, Str), _)
	parsed = Json.parse("{\"field\":\"café\\nλ \\\"quote\\\" \\\\slash\"}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("\"café\\nλ \\\"quote\\\" \\\\slash\""))
}
expect {
	parsed : Try(Dict(Str, Bool), _)
	parsed = Json.parse("{\"field\":true}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("true"))
}
expect {
	parsed : Try(Dict(Str, Null), _)
	parsed = Json.parse("{\"field\":null}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("null"))
}
expect {
	parsed : Try(Dict(Str, List(U64)), _)
	parsed = Json.parse("{\"field\":[1,2,3]}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("[1,2,3]"))
}
expect {
	parsed : Try(Dict(Str, { nested : { name : Str, values : List(Bool) } }), _)
	parsed = Json.parse("{\"field\":{\"nested\":{\"name\":\"λ\",\"values\":[true,false]}}}")
	parsed.map_ok(
		|fields| fields.get("field").map_ok(
			|value| {
				encoded = Json.to_str(value)
				roundtrip : Try({ nested : { name : Str, values : List(Bool) } }, _)
				roundtrip = Json.parse(encoded)
				roundtrip == Ok(value)
			},
		),
	) == Ok(Ok(True))
}
expect {
	parsed : Try(Dict(Str, Str), _)
	parsed = Json.parse("{\"field\":\"first\",\"\\u0066ield\":\"last\"}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("\"last\""))
}
expect {
	parsed : Try(Dict(Str, (Str, Bool, Null)), _)
	parsed = Json.parse("{\"field\":[\"λ\",false,null]}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("[\"λ\",false,null]"))
}
expect {
	parsed : Try(Dict(Str, F64), _)
	parsed = Json.parse("{\"field\":1e9999}")
	parsed.is_err()
}
expect {
	parsed : Try(Dict(Str, U128), _)
	parsed = Json.parse("{\"field\":340282366920938463463374607431768211456}")
	parsed.is_err()
}
expect {
	parsed : Try(Dict(Str, F64), _)
	parsed = Json.parse("{\"field\":340282366920938463463374607431768211457}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| value == 340282366920938463463374607431768211456)) == Ok(Ok(True))
}
expect {
	parsed : Try(Dict(Str, Any), _)
	parsed = Json.parse("{\"field\":340282366920938463463374607431768211457,\"huge\":1e9999,\"nested\":{\"items\":[true,null,\"λ\"]}}")
	parsed.is_ok()
}

expect {
	parsed : Try(Dict(Str, Bool), _)
	parsed = Json.parse("{\"field\":false}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("false"))
}
expect {
	parsed : Try(Dict(Str, Dict(Str, Str)), _)
	parsed = Json.parse("{\"field\":{\"x\":\"first\",\"\\u0078\":\"last\"}}")
	parsed.map_ok(|fields| fields.get("field").map_ok(|value| Json.to_str(value))) == Ok(Ok("{\"x\":\"last\"}"))
}

expect {
	parsed : Try(Dict(Str, Dec), _)
	parsed = Json.parse("{\"field\":1e9999}")
	parsed.is_err()
}
expect {
	parsed : Try(Dict(Str, Dec), _)
	parsed = Json.parse("{\"field\":340282366920938463463374607431768211456}")
	parsed.is_err()
}
```

</details>

<details>
<summary>DepthProbe.roc — bounded precheck and depths 128/129</summary>

```roc
DepthProbe :: {}

Any :: {}.{
	parser_for = |encoding| |state| {
		rest = Json.skip_json_value(encoding, state)?
		Ok({ value: Any.{}, rest })
	}
}

within_depth = |input| {
	initial : { depth : U64, quoted : Bool, escaped : Bool }
	initial = { depth: 0, quoted: False, escaped: False }
	input.to_utf8().fold_try(
		initial,
		|state, byte| {
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
					Err(NestingTooDeep)
				}
					else {
						Ok({ ..state, depth: state.depth + 1 })
					}
			} else if (byte == 125 or byte == 93) and state.depth > 0 {
				Ok({ ..state, depth: state.depth - 1 })
			} else {
				Ok(state)
			}
		},
	).map_ok(|_| {})
}

valid = |input| {
	parsed : Try(Any, _)
	parsed = Json.parse(input)
	parsed.is_ok()
}

accepted = |input|
	match within_depth(input) {
		Ok({}) => valid(input)
		Err(_) => False
	}

array = |depth| "[".repeat(depth).concat("0").concat("]".repeat(depth))

object = |depth| "{\"x\":".repeat(depth).concat("0").concat("}".repeat(depth))

expect valid(array(128))
expect valid(array(129))
expect valid(object(128))
expect valid(object(129))
expect accepted(array(128))
expect within_depth(array(129)) == Err(NestingTooDeep)
expect accepted(object(128))
expect within_depth(object(129)) == Err(NestingTooDeep)
expect accepted("[]") and accepted("{}") and accepted("null")
expect accepted(Json.to_str("[".repeat(200)))
expect within_depth("[[}").is_ok() and !valid("[[}")
expect accepted("{\"quoted \\\" key [\":\"a\\\\b\\\"[{}] café λ\"}")
expect accepted("{\"x\":\"\\\\\\\\\",\"brackets\":\"[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]\"}")
expect accepted("{\"x\":[\"[\",{\"y\":\"\\\"\\\\[\\\"\"}]}")

expect !accepted(array(129))
expect !accepted(object(129))
```

</details>

## 4. Small architecture and repository layout

Keep effects at the boundary and transformations pure:

```text
arguments → input bytes/lines → JSONL validation → operation → output
```

Suggested layout for implementation; these files are not created by this task:

```text
main.roc                   # app declaration, I/O loop, error/exit mapping
Cli.roc                    # pure arguments → operation/source or usage error
Jsonl.roc                  # framing, validity, top-level string lookup
Operations.roc             # counts, matching, bounded tail state
README.md                  # installation, commands, status/partial-output contract
LICENSE                    # recommend MIT for jlog-owned code
CONTRIBUTING.md             # concise toolchain setup and validation checklist
docs/                      # JSONL introduction and technical research
specs/                     # behavior contracts
examples/events.jsonl       # small valid demonstration fixture
tests/fixtures/            # valid, malformed, encoding and boundary inputs
tests/integration.py       # stdlib subprocess checks for streams and statuses
.github/workflows/ci.yml    # pinned native build/test matrix
```

Use tagged unions for operations and classified failures, records for counters
and line metadata, and pattern matching for EOF/errors. A straightforward effect
loop can own readers and output; pure functions should not import platform I/O.
Use a bounded FIFO/ring for tail without per-record O(N) list reconstruction.
Keep the actual state representation flexible and verify that retained slices
do not keep whole input chunks alive unnecessarily.

MIT is a simple license recommendation, subject to the owner's choice. Preserve
required platform/dependency notices in distributions; jlog's license does not
relicense them. Keep compiler archives, caches, binaries, and generated stress
fixtures out of Git. A short contribution guide is justified by the compiler pin
and the distinction between pure `expect` checks and executable tests.

## 5. Build, test, and distribution approach

The installed compiler's `--help`, `build --help`, and `test --help` were inspected.
After implementation, document these commands from the repository root:

```sh
roc version
roc check main.roc
roc test main.roc
roc fmt --check main.roc Cli.roc Jsonl.roc Operations.roc
mkdir -p dist
roc build --opt=speed --output=dist/jlog main.roc
python3 tests/integration.py dist/jlog
```

The source filenames and integration script are proposed, not existing wrappers.
Use `roc fmt` as the formatting authority. Ensure pure modules are reachable from
the tested root; use a separate test root only if needed. Test stdout, stderr,
and statuses independently, with unprivileged permission tests and controlled
broken-pipe/read-error tests. Test data output by parsing every line separately.

### Executed capability probes

| Probe | Observed result |
| --- | --- |
| Arguments / exit / stderr | Only passed arguments received; `Err(Exit(7))` returned status 7; stderr stayed separate |
| File line reading | Bytes `{}\r\n\n\xff` yielded `[123,125,13,10]`, `[10]`, `[255]`, then `[]` |
| Raw stdin | Empty input returned `EndOfFile`; newline and final unterminated bytes preserved; 16,385 bytes split into reads of 16,384 and 1 |
| JSON adapter | Accepted all six value kinds and `1e9999`; rejected the malformed samples described above in dev and speed builds |
| Built-in testing | Original typed JSON check passed; all nine documented review `expect` blocks passed in both dev and speed test modes |
| macOS build/run | `--opt=dev` and `--opt=speed` built and ran native ARM64 probes |
| Linux cross-build | `--opt=speed --target=x64musl` and `--target=arm64musl` built; x86-64 output identified as a statically linked ELF executable |

Build flags above were exercised on temporary probes, not on a jlog application.
Linux binaries were not executed on this Darwin host. macOS binaries use OS
libraries; Linux static musl linkage does not prove support for every Linux kernel.
No minimum OS version, signing/notarization behavior, throughput, or final jlog
binary size has been established.

Initial builds failed because the sandbox could not write compiler caches.
Setting `ROC_CACHE_DIR` to a writable temporary cache containing the already cached
platform packages allowed builds and tests to succeed. This was an environment
restriction, not a platform compatibility failure. Shell network access was also
unavailable; official web pages and existing cached sources supplied the research.

### Realistic CI and releases

Use native GitHub runners for macOS ARM64 and Linux x86-64. The official
[setup-roc action](https://github.com/roc-lang/setup-roc) documents Linux/macOS
support and `version: nightly-new-compiler` with `nightly-tag` for a dated pin.
Pin the action itself to a reviewed commit and select
`nightly-2026-10-09-258ab27`; verify `roc version` in every job. Its complete
installation workflow and the matching Linux compiler archive were not executed
in this session, so the first CI run must verify them.

Each required job should check, format-check, run `expect`s, build an optimized
binary, and execute integration fixtures. Cache dependencies by compiler version
and platform URL. Cross-compilation is useful for producing artifacts, but native
execution must pass before declaring a target supported. Add Linux ARM64 once a
native runner and tests pass; defer other platform targets.

Generate roughly 100 MiB and 1 GiB inputs with fixed maximum record size for
scheduled/manual stress checks. Measure elapsed time and peak RSS for inspection,
count, filter, and fixed-N tail. Compare different N values separately;
also test a single 8 MiB line, all-invalid input, and a million short lines.
Investigate memory growth proportional to total file size or record count, or
tail runtime proportional to N on every insertion. Publish measured results,
not an unverified speed claim. Keep ordinary PR CI fixtures small.

Release archives should contain the tested target binary, license/notices,
checksums, and short installation instructions. Verify them on clean native
runners without Roc installed. No custom platform or host-language framework is
needed; compilation downloads dependencies, but the resulting CLI should work
offline. Updating the toolchain requires repeating these compatibility checks.

## 6. Decision and adopted specification changes

**REDUCED SCOPE:** defer `--field` to v0.2; retain inspection, count, tail,
string-only filtering, and the depth-128 limit for v0.1. Arbitrary validation and
string lookup use verified builtins/adapters. General extraction still needs an
unverified exact-value representation, whereas depth enforcement needs only the
small tested resource precheck. A new JSON subsystem would work against the
learning-and-shipping objective.

The user approved these minimum specification edits before implementation planning.
They are now reflected in the specification:

1. Remove `--field KEY` from the v0.1 syntax/help, goals, field-output examples,
   and M3 deliverable; reserve it for v0.2. Until introduced it is an unsupported
   option, using the existing usage-error contract (exit 2, empty stdout).
2. Move field extraction requirements and field-specific acceptance criteria to
   the v0.2 roadmap, retaining them rather than dropping coverage. Keep exact
   numeric semantics, all JSON value kinds, Unicode, duplicate-key handling,
   missing/null distinctions, and pipeline-safe JSON encoding as re-entry gates.
3. Leave M1/M2 and all remaining output/error/non-goal contracts unchanged. M3
   becomes string-only filtering; M4 validates all four retained operations on
   native targets and prepares the release. Input-kind/number/depth tests shared
   with the deferred extractor remain v0.1 validation/filter tests.
4. Keep the 128-depth rule and its diagnostic/precedence unchanged. Record the
   verified precheck in feasibility guidance; the specification need not prescribe
   its implementation.

The feasibility investigation did not implement application code. The subsequent
TDD plan follows the approved four-operation specification; the deferred `--field`
requirements remain unproven for a straightforward general implementation.
Native Linux execution, large-file memory/stack and tail measurements, full JSON
regression coverage, controlled I/O failures, and packaged-binary verification
remain normal release gates. Repeat capability probes after any toolchain change.

Decision: **REDUCED SCOPE**, not BLOCKED — the useful four-operation CLI can ship
with the selected toolchain; only general field projection lacks a straightforward
verified implementation path.
