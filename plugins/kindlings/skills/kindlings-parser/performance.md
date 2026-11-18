# Flags and performance (kindlings-parser 0.4.0)

Full docs: <https://kindlings.readthedocs.io/en/0.4.0/parser-performance/>

## Which parser runs

- Every grammar compiles to LALR(1) tables run by a heap-stack machine (left recursion, precedence, any nesting depth,
  pausable for effects/streams, error reporting). Reductions and, for `String` inputs, the lexer are generated code.
- An **LL(1)** grammar additionally gets a generated **recursive-descent** parser. It is used when **all** hold:
  - the grammar is LL(1), has **no effectful actions** and **no** `left`/`right`/`nonassoc` declarations, and
    `RequireLALR` is not enabled;
  - the input is a `String` (not `Reader`/`InputStream`/push/fs2);
  - the engine runs to completion (`Id`, `Option`, `Try`, `Either`, `Future`) - not the Cats Effect engine or fs2
    pipes, which run with a step budget.
- The fast path never reports errors: on a syntax error, a rejected value, an exception from an action, or nesting
  deeper than 1000 levels, it bails out and the machine re-parses from the start (same values, same action order, but
  actions before the failure run twice).

## Flags

Set inside the block, before declarations: `enable(RequireLL1)`.

| Flag | Effect |
|---|---|
| `RequireLL1` | compile error with explanations if the grammar is not LL(1) (like `@tailrec`); `String` errors are reported by a top-down machine listing only tokens valid in context |
| `RequireLALR` | LALR(1) machine only; no recursive-descent fast path |
| `ThrowingInRuntime` | allow rejecting collections/value types (`NonEmptyList`, refined, Iron) in `Id`; the rejection is thrown as `ParseError` |

`disable(flag)` documents that a flag is off (the default). Enabling and disabling the same flag, or both
`RequireLL1` and `RequireLALR`, is a compile error.

## Why a grammar is not LL(1) (`RequireLL1` explanations)

| Reported reason | Fix |
|---|---|
| a rule starts with itself (left recursion, possibly via `a -> b -> a`) | use `rep`/`sepBy`: `list ::= all(item, rep(all(",", item)))` |
| alternatives start with the same token | factor out: `all(x, "a") \|\| all(x, "b")` becomes `all(x, "a" \|\| "b")` |
| an empty alternative (`""`, `opt`, empty `rep`) whose next token can start another alternative | restructure so the choice is decided by one token |
| an optional part / repetition / separator whose next token could also follow it (`all(rep("x"), "x")`) | make the end unambiguous |
| a repetition of something that can match nothing | make the repeated symbol non-empty |

Keep `enable(RequireLL1)` in fast grammars so they stay LL(1) as they evolve.

## Writing fast grammars

- Prefer LL(1): one non-terminal per precedence level with `rep` for operators, `rep`/`sepBy` instead of left
  recursion.
- Convert tokens in place: `.mapSlice(Numbers.double)` etc. and slice off string-literal quotes, instead of `.map` on a
  copied `String`.
- Keep effectful actions out of hot rules (they disable the fast path); a pure grammar in `Either`/`Try` still reports
  syntax errors through the effect.
- Declare primitive non-terminals (`nonTerminal[Int]`, `nonTerminal[Double]`) - unboxed between reductions.
- Collect directly with `.as[C]` instead of converting a `List` in the action.

### LL(1) expression grammar

```scala
val calc: Parser[Id, Double] = Grammar.grammar[Double, Id] { g =>
  import g._
  enable(RequireLL1)
  val sum = nonTerminal[Double]
  val sumOp = nonTerminal[Double => Double]
  val product = nonTerminal[Double]
  val productOp = nonTerminal[Double => Double]
  val factor = nonTerminal[Double]
  val num = terminal("[0-9]+(\\.[0-9]+)?").mapSlice(Numbers.double)
  skip(" +")
  sum ::= all(product, rep(sumOp)).pure((a, ops) => ops.foldLeft(a)((acc, op) => op(acc)))
  sumOp ::= all("+", product).pure((_, b) => (a: Double) => a + b) ||
    all("-", product).pure((_, b) => (a: Double) => a - b)
  product ::= all(factor, rep(productOp)).pure((a, ops) => ops.foldLeft(a)((acc, op) => op(acc)))
  productOp ::= all("*", factor).pure((_, b) => (a: Double) => a * b) ||
    all("/", factor).pure((_, b) => (a: Double) => a / b)
  factor ::= all("(", sum, ")").pure((_, e, _) => e) || all(num).pure(n => n)
  sum
}
calc.parse("1 + 2 * (3 - 1) / 4") // 2.0
```

## Reference numbers (from the 0.4.0 docs, JMH, ~1 MB JSON)

| Parser | Scala 3 ops/s | Scala 2.13 ops/s |
|---|---|---|
| jawn | 224.5 | 192.6 |
| kindlings-parser recursive descent, `mapSlice(Numbers.double)` | 199.0 | 155.3 |
| kindlings-parser recursive descent, `.map(_.toDouble)` | 172.9 | 142.8 |
| kindlings-parser LALR(1) (`RequireLALR`) | 108.5 | 85.1 |

Arithmetic (Scala 3): LL(1) grammar 70.6 ops/s, precedence-based LALR(1) 63.5, fastparse 20.0.
