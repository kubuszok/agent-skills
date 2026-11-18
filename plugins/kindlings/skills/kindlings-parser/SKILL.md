---
name: kindlings-parser
description: >-
  Yacc-style BNF grammars embedded in Scala with kindlings-parser - Grammar.grammar[Result, F] { g => import g._;
  ... } compiled at compile time into LALR(1) tables, a lexer DFA and, for LL(1) grammars, a recursive-descent fast
  path. Covers nonTerminal, terminal(regex).map / .mapSlice, Numbers, skip, ::=, all(...).pure and effectful
  actions, ||, opt, rep, rep1, sepBy, sepBy1, .as[C], left/right/nonassoc/.prec, enable(RequireLL1 | RequireLALR |
  ThrowingInRuntime), Parser[F, R].parse on String/Reader/InputStream, ParseError, engines for
  Id/Option/Try/Either/Future, kindlings-parser-cats-effect (catseffect, CatsEffectEngine), kindlings-parser-fs2
  (streams pipe/pipeIn/bytePipe) and pushMachine. Use when code imports hearth.kindlings.parser, when comparing it
  with yacc/fastparse/cats-parse, or on errors like "shift/reduce conflict", "reduce/reduce conflict", "this grammar
  is not LL(1)", "No ParserEngine for", "has no error channel for rejected values", "Unexpected token at".
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings Parser (`kindlings-parser`)

Write a BNF grammar with typed semantic actions inside Scala; a macro turns it into a parser at compile time. Grammar
problems (conflicts, unproductive or productionless non-terminals, bad regexes) are compile errors at the offending
production. The LALR(1) machine keeps its stack on the heap (no stack overflow on deep nesting), can pause for
effects/streamed input, and LL(1) grammars additionally get a generated recursive-descent parser for `String` inputs.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/parser/>. The module is marked **early stage** in 0.4.0: the grammar syntax
is settled, engines/inputs/codegen may still change.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-parser" % "0.4.0"
// optional
libraryDependencies += "com.kubuszok" %%% "kindlings-parser-cats-effect" % "0.4.0" // Parser[IO, R], any Sync/Async F
libraryDependencies += "com.kubuszok" %%% "kindlings-parser-fs2"         % "0.4.0" // fs2 Pipes
```

```scala
//> using dep com.kubuszok::kindlings-parser:0.4.0
```

Scala 2.13 and 3; JVM, Scala.js, Scala Native (all three modules).

## Imports

```scala
import hearth.kindlings.parser._            // Grammar, Parser, ParseError, Id, Numbers, Slices, ParserEngine, ...
import hearth.kindlings.parser.catseffect._ // Cats Effect engines (kindlings-parser-cats-effect)
import hearth.kindlings.parser.streams._    // fs2 pipes (kindlings-parser-fs2)
```

Inside the grammar block always `import g._` to get the DSL (`nonTerminal`, `terminal`, `all`, `rep`, flags, ...).

## A grammar

```scala
import hearth.kindlings.parser._

val calc: Parser[Id, Int] = Grammar.grammar[Int, Id] { g =>
  import g._
  // 1. flags, declarations, skip, precedence
  val expr = nonTerminal[Int]
  val num  = terminal("[0-9]+").map(_.toInt)
  skip("[ \\t]+")
  left("+", "-")
  left("*", "/")
  // 2. productions
  expr ::= (
    all(expr, "+", expr).pure((a, _, b) => a + b) ||
      all(expr, "-", expr).pure((a, _, b) => a - b) ||
      all(expr, "*", expr).pure((a, _, b) => a * b) ||
      all(expr, "/", expr).pure((a, _, b) => a / b) ||
      all("(", expr, ")").pure((_, e, _) => e) ||
      all(num).pure(n => n)
  )
  // 3. start symbol as the last expression
  expr
}

calc.parse("1 + 2 * (3 - 1)") // 5
```

- `Grammar.grammar[R, F]` (result type first, effect second) returns `Parser[F, R]` (effect first); `parse` returns
  `F[R]`. With `F = Id` the value is returned directly and syntax errors are thrown as `ParseError`.
- `all(s1, ..., sN).pure((v1, ..., vN) => r)` is a pure action; `all(...)((v1, ...) => fr)` must return `F[R]`.
  Use `_` for values you ignore (they are never converted). Max 22 symbols per sequence.
- Literals (`"+"`) are terminals whose value is the literal; `terminal("regex")` values are the matched `String`
  (convert with `.map`, or `.mapSlice((input, start, end) => ...)` / `Numbers.int|long|double` to avoid copying).
- `opt(s)`: `Option[A]`; `rep`/`rep1`/`sepBy(s, sep)`/`sepBy1`: `List[A]`, or any collection/value type with
  `.as[C]` (e.g. `.as[Vector[A]]`, `.as[NonEmptyList[A]]` with `kindlings-cats-integration`).
- Same syntax on Scala 2.13 and Scala 3. On Scala 2.13 put multi-line alternatives in parentheses and end each line
  with `||` (as above).

Full grammar syntax, tokens, precedence, collections and diagnostics: [grammars.md](grammars.md).

## Running

| `F` | effectful action failure | syntax error |
|---|---|---|
| `Id` | - | throws `ParseError` |
| `Option` | `None` | `None` |
| `scala.util.Try` | `Failure` | `Failure(ParseError)` |
| `Either[E, *]` (via a type alias) | `Left` | `Left` via `ParseErrorLift[E]`: built in for `ParseError`, `Throwable`, `String` |
| `Future` | failed future | failed future (needs an implicit `ExecutionContext`) |
| any cats-effect `Sync`/`Async` `F` | the failed `F` | `F.raiseError(ParseError)` (`import hearth.kindlings.parser.catseffect._`) |

```scala
type Result[A] = Either[String, A]                    // an alias, so Grammar.grammar[R, Result] has a 1-hole F
val p: Parser[Result, Int] = Grammar.grammar[Int, Result] { g =>
  import g._
  val sum = nonTerminal[Int]
  val num = terminal("-?[0-9]+").map(_.toInt)
  skip(" +")
  // effectful action: returns Result[Int]; a Left stops the parse
  sum ::= all(sepBy1(all(num)(n => if (n < 0) Left(s"negative: $n") else Right(n)), ",")).pure(_.sum)
  sum
}
p.parse("1, 2, 3")                                   // Right(6)
p.parse("1, 2,")                                     // Left("Unexpected token at 1:6: found end of input, expected num")
p.parse(new java.io.StringReader(text), bufferSize = 64) // Reader / InputStream (UTF-8): bounded memory
```

Cats Effect, fs2 pipes, the push machine and `ParseError` fields: [running.md](running.md).

## Performance

LL(1) grammars without precedence declarations and without effectful actions get a generated recursive-descent parser
for `String` inputs (close to jawn speed for JSON); anything else, and every error report, uses the LALR(1) machine.
`enable(RequireLL1)` makes "not LL(1)" a compile error with explanations; `enable(RequireLALR)` disables the fast path.
Details, flag table and an LL(1) expression grammar: [performance.md](performance.md).

## Differences from yacc / fastparse-style libraries

- Like yacc: LALR(1) with `left`/`right`/`nonassoc` (`%left`...) and `.prec(op)` (`%prec`), conflicts reported at
  compile time. Unlike yacc: no separate grammar file or code generator, typed actions, an integrated longest-match
  lexer (literals beat regexes on equal length), and grammars are type-checked Scala.
- Unlike parser combinators (fastparse, cats-parse, parboiled2): no backtracking, left recursion is fine, ambiguities
  are compile errors instead of silent first-match behaviour, and parsing is stack-safe at any depth.
- Not (yet) supported: composing grammars (one grammar = one block), dynamic grammars (loops/conditionals/helper
  methods in the block), non-literal patterns, regex anchors/look-arounds/back-references/lazy quantifiers.

## Debugging

The parser has no `-Xmacro-settings` namespace in 0.4.0 (no debug import, timeout or derivation policy). Grammar
problems are reported as compile errors at the production; use `enable(RequireLL1)` to get a plain-language
explanation of why a grammar misses the fast path. For general macro/build issues see the `kindlings-troubleshooting`
skill.

## Gotchas

- **`shift/reduce conflict on "+"`** - declare precedence/associativity (`left("+")`, ...) or restructure the rule;
  for a unary operator use `.prec("NEG")` with `nonassoc("NEG")` declared at a higher level.
- **`reduce/reduce conflict`** - two productions can reduce on the same input; usually duplicated alternatives or two
  empty-able rules in the same position. Restructure.
- **`grammar symbols (and the grammar DSL) can only be used in productions, not inside actions or .map functions`** -
  actions are moved out of the block into generated code; compute values from the action parameters only.
- **`grammar blocks may only contain declarations ...` / `helper methods are not supported`** - the block must be
  static: no `if`, loops, `def`s, or vals other than `nonTerminal`/`terminal`.
- **`expected a string literal (patterns are compiled at compile time)`** - patterns must be literals, not variables.
- **`terminal ... matches the empty string`** - make the regex consume at least one char; use `opt`/`rep` for
  optionality.
- **`No ParserEngine for F`** - `F` is not one of the built-ins; for `IO` etc. add `kindlings-parser-cats-effect` and
  `import hearth.kindlings.parser.catseffect._`; for `Future` provide an implicit `ExecutionContext`; for `Either`
  use a type alias and a `ParseErrorLift[E]` for your `E`.
- **`F has no error channel for rejected values`** - `.as[NonEmptyList[A]]` / refined / Iron collections can reject
  values, which `Id` cannot report. Use `Option`/`Try`/`Either`/`Future`/cats-effect, or `enable(ThrowingInRuntime)`.
  Prefer `rep1`/`sepBy1` so the grammar guarantees non-emptiness.
- **Actions run twice / side effects duplicated** - on invalid input (or nesting deeper than 1000) the fast path bails
  out and the LALR(1) machine re-parses, re-running pure actions and `.map`s. Keep them side-effect free; put effects
  in effectful actions (which disable the fast path).
- **Keyword vs identifier** - the lexer takes the longest match and literals win ties, so `"if"` matches `if` but
  `iffy` is an identifier.
- **`.as[C]` with `Grammar.interpreted`** - not supported (`Grammar.interpreted` always builds `List`s).
- **Maps from repetitions** - `.as[Map[K, V]]` is rejected; collect pairs and call `.toMap` in the action.

## Links

- Overview: <https://kindlings.readthedocs.io/en/0.4.0/parser/>
- Writing grammars: <https://kindlings.readthedocs.io/en/0.4.0/parser-grammars/>
- Running parsers: <https://kindlings.readthedocs.io/en/0.4.0/parser-running/>
- Flags and performance: <https://kindlings.readthedocs.io/en/0.4.0/parser-performance/>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/parser>
