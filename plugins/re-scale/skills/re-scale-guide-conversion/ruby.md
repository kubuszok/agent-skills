# Ruby to Scala 3

Ruby is dynamically typed and leans on metaprogramming, so a line-by-line port
rarely works:

1. Understand what the code does (read its tests, too).
2. Write Scala from that behaviour, with real types.
3. Prove equivalence with tests - port the upstream tests or feed both
   implementations the same inputs.

`re-scale enforce compare` does not parse Ruby (it falls back to the Dart
parser), so method parity is checked by hand.

## Types

| Ruby | Scala 3 |
|---|---|
| `String` / `Symbol` | `String` (an `enum` when the symbols form a closed set) |
| `Integer` / `Float` | `Int`/`Long` (Ruby integers are unbounded - use `BigInt` if values can grow) / `Double` |
| `nil` | `Nullable[A]` |
| `Array` / `Hash` | `ArrayBuffer`/`List` / `mutable.LinkedHashMap` (Ruby hashes keep insertion order) |
| `Regexp` | `scala.util.matching.Regex` |
| `Proc`, lambda, block | function type `A => B` |

## Control flow and classes

`unless c` -> `if (!c)`; `case/when` -> `match`; `begin/rescue/ensure` ->
`try/catch/finally`; `return`, `next`, `break` in blocks -> boundaries (see
`re-scale-guide-control-flow`). `class A < B` -> `extends`; `module` mixed in
with `include` -> `trait`; `attr_accessor`/`attr_reader` -> `var`/`val`;
`def initialize` -> primary constructor; `def self.m` -> companion method.

## Strings and regexes

| Ruby | Scala 3 |
|---|---|
| `"#{e}"` | `s"${e}"` |
| `gsub(re, s)` / `sub(re, s)` | `re.replaceAllIn(str, s)` / `re.replaceFirstIn(str, s)` (escape `$` and `\` in `s` with `Regex.quoteReplacement`) |
| `str.match(re)`, `=~`, `$1` | `re.findFirstMatchIn(str)`, `m.group(1)` |
| `scan(re)` | `re.findAllIn(str)` |
| `strip` | `trim` or `strip` - the three disagree on which characters count as whitespace; check inputs with control or Unicode spaces |
| `/x/i` / `/x/m` | `"(?i)x".r` / `"(?s)x".r` (Ruby `m` = dot matches newline) |
| `^` / `$` | Ruby anchors are per line: use `(?m)` or `\A` / `\z` to match Ruby |

Regex dialects differ between Ruby, the JVM, Scala.js (JavaScript regexes) and
Scala Native. Test every ported regex on each platform the module targets.

## Iteration

`each` -> `foreach`, `map` -> `map`, `select` -> `filter`, `reject` ->
`filterNot`, `reduce` -> `reduceLeft`/`foldLeft`, `any?` -> `exists`,
`all?` -> `forall`, `flat_map` -> `flatMap`.
