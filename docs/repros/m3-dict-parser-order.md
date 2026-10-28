# Custom dictionary parser declaration-order crash

Observed on native macOS ARM64 with Roc `nightly-2026-10-09-258ab27` during M3.
This pure reproducer does not depend on basic-cli.

The existing feasibility probe parses a dictionary of record-backed field markers
inside top-level `expect` blocks and passes. Moving that operation into a function
exposes a declaration-order problem: the following version crashes both checking
and testing with SIGSEGV/status 139, rather than producing a type diagnostic.

Save this as `/private/tmp/ParserOrder.roc`:

```roc
ParserOrder :: {}.{
    matches : List(U8), Str, Str -> Try(Bool, [LookupFailure])
    matches = |body, key, text| {
        source = Str.from_utf8(body).map_err(|_| LookupFailure)?
        parsed : Try(Dict(Str, Field), _)
        parsed = Json.parse(source)
        fields = parsed.map_err(|_| LookupFailure)?
        match fields.get(key) {
            Ok(value) => Ok(value.text == [text])
            Err(_) => Ok(False)
        }
    }
}

Field :: { text : List(Str) }.{
    parser_for = |encoding| |state| match Json.parse_str(encoding, state) {
        Ok(parsed) => Ok({ value: Field.{ text: [parsed.value] }, rest: parsed.rest })
        Err(_) => {
            rest = Json.skip_json_value(encoding, state)?
            Ok({ value: Field.{ text: [] }, rest })
        }
    }
}

expect ParserOrder.matches("{\"status\":\"failed\"}".to_utf8(), "status", "failed") == Ok(True)
```

```sh
roc check /private/tmp/ParserOrder.roc
roc test --opt=dev --no-cache /private/tmp/ParserOrder.roc
```

Move the complete `Field` declaration above `ParserOrder`, keeping the function,
decoder, and assertion unchanged. The isolated test then passes. Applying the
same ordering to the production `StringField` decoder lets the application
check, test, and build on the existing pin.

This is an observed compiler limitation, not a general Roc requirement that
definitions be ordered. Alternate comparison expressions and a private helper
also crashed; a boolean-only variant timed out. Those shapes are not used as a
way to weaken matching or suppress a failing assertion. The record-based decoder
still delegates JSON syntax to the builtins, retains strings, skips other values,
and leaves original input bytes untouched.
