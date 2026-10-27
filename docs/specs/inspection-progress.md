# Optional inspection progress

## Summary

Help users confirm that long inspections are advancing by showing physical-line
and invalid-line counts while input is processed. Progress is explicitly enabled
with the modifier named `--progress`; ordinary invocations retain their current
output. This authorized addition changes the earlier prohibition on all progress
indicators while preserving clean result output and incremental inspection.

## Entities

- An inspection reads one selected input and classifies its physical lines.
- A progress snapshot describes how many physical lines that inspection has
  classified and how many of them are invalid.
- A completion snapshot describes the final totals after successful end of input.

## Models

| Field | Business type and rules |
| --- | --- |
| Progress enabled | Required yes/no choice; defaults to no. |
| Lines inspected | Required nonnegative whole number, including invalid lines. |
| Invalid lines | Required nonnegative whole number, never above lines inspected. |
| Complete | Required yes/no indication; yes only after successful end of input. |

Snapshots contain no record bodies, keys, or other input content. Counts have no
digit grouping and reflect completed physical lines rather than partial records.

## Limitations/Constraints

Progress must leave the final inspection report and its destination unchanged.
It must remain useful when standard error is redirected, use plain text without
colors or terminal control sequences, and avoid retaining additional input.
No percentage, total-size estimate, or background heartbeat is required.

## Business rules

- Progress is optional and is written only to standard error. No progress is
  emitted for ordinary invocations or for unsuccessful argument validation.
- The modifier may appear before or after the input and may be supplied once.
  A repeated modifier or a value assigned to it is a usage error. The existing
  option terminator and standalone help/version rules continue to apply.
- The modifier does not select an operation. It may accompany other operation
  flags, but only inspection emits progress. Count and tail retain their data
  output contracts without inspection snapshots. Unfinished operations retain
  their existing failure behavior and emit no inspection progress.
- During inspection, snapshots are emitted at most once per second and only
  when the inspected-line count has advanced. They are checked as input is
  processed; blocked reads and very long individual records may delay updates.
- A snapshot reads “jlog: N lines inspected, M invalid” and ends with a newline.
- Successful end of input always produces a final snapshot with the suffix
  “ (complete)”, including empty inputs and final unterminated records. This
  snapshot is exempt from the periodic rate limit.
- Malformed records continue to be inspected and contribute to both progress
  totals and the existing final report. Existing exit status rules remain.
- Input failure may leave earlier progress visible but produces no completion
  snapshot and no completed inspection report. Failure to write progress, when
  reported by the environment, stops processing with the existing I/O status.

## Acceptance criteria

1. Without the modifier, ordinary inspection stdout, stderr, and exit behavior
   is unchanged; help and usage text advertise the new modifier.
2. A short successful inspection with the modifier emits its ordinary stdout
   report and one final progress line on stderr with matching totals.
3. Empty input completes with zero inspected and zero invalid lines; an
   unterminated final record is included exactly once.
4. Both file and standard-input inspection emit progress. Long-running input
   produces a snapshot before EOF while stdout remains empty until EOF.
5. Periodic updates are suppressed before one second elapses, stop repeating
   unchanged counts, and resume when sufficient time and new lines exist.
6. A malformed input still reports its final invalid total and exits with the
   existing malformed-input status after EOF.
7. Unknown, repeated, malformed, or incompatible arguments fail before input I/O
   and produce no progress. Modifier-like text after the option terminator can
   still name a file, and text consumed as an operand retains its existing rules.
8. Open/read failures produce an input diagnostic and no completion snapshot.
9. Redirected progress is newline-delimited plain text with no cursor controls.
10. Help explains the opt-in modifier, its destination, and its inspection scope.

## Out-of-scope/Open Questions

Out of scope: verbose logging, progress percentages or bars, terminal animation,
configurable update intervals, background updates during blocked reads, and
implementation of count, tail, or filtering.

No business decisions remain open. Plain-text counts and approximately one-second
updates are deliberate defaults within the user's authorization.
