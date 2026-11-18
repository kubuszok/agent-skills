# Writing grammars (kindlings-parser 0.4.0)

Full docs: <https://kindlings.readthedocs.io/en/0.4.0/parser-grammars/>

```scala
Grammar.grammar[Result, F] { g =>
  import g._
  // flags:        enable(RequireLL1) / disable(...)
  // declarations: val x = nonTerminal[A]; val t = terminal("regex"); skip("regex"); left/right/nonassoc(...)
  // productions:  x ::= alternative || alternative || ...
  startSymbol // last expression: the start non-terminal, producing Result
}
```

Declarations come before productions (enforced). `Grammar.interpreted[R, F]` takes the same block but evaluates it at
run time (slower; no `.as[C]`); use `Grammar.grammar`.

## Syntax

| Construct | Meaning |
|---|---|
| `val e = nonTerminal[A]` | non-terminal producing `A`; primitives (`Int`, `Double`, ...) stay unboxed |
| `val t = terminal("[0-9]+")` | regex terminal; value is the matched `String` |
| `t.map(f)` | convert the token's value (chainable) |
| `t.mapSlice((input, start, end) => ...)` | convert from the input and token bounds without copying; must be the **first** conversion; its pattern must not be used by another terminal |
| `"+"` | literal terminal; value is the literal |
| `"[a-z]+".r` | inline regex terminal |
| `skip("[ \\t\\n]+")` | text skipped between tokens (whitespace, comments); may be repeated |
| `nt ::= alts` | add productions (may be repeated for the same `nt`) |
| `all(s1, ..., sN).pure((v1, ..., vN) => r)` | alternative with a pure action |
| `all(s1, ..., sN)((v1, ..., vN) => fr)` | alternative with an effectful action returning `F[R]` |
| `a \|\| b` | alternatives |
| single symbol/literal as an alternative | passes its value through: `suffix ::= "Sr." \|\| "Jr." \|\| ""` |
| `""` as a whole alternative | empty alternative (value `""`) |
| `("+" \|\| "-")` used as a symbol | inline group (anonymous helper non-terminal) |
| `opt(s)` | `Option[A]` |
| `rep(s)` / `rep1(s)` | zero/one or more, `List[A]` |
| `sepBy(s, sep)` / `sepBy1(s, sep)` | separated list, `List[A]` |
| `rep(...).as[C]` (also `rep1`/`sepBy`/`sepBy1`) | collect into `C` instead of `List` |
| `left(ops*)`, `right(ops*)`, `nonassoc(ops*)` | precedence levels, lowest first (terminals only) |
| `all(...).prec(op)` | production takes `op`'s precedence (`%prec`) |
| `enable(flag)` / `disable(flag)` | `RequireLL1`, `RequireLALR`, `ThrowingInRuntime` (see performance.md) |

Sequences are limited to 22 symbols; split longer ones into helper non-terminals.

## Tokens

- Regex subset (DFA-compatible Java syntax): literals, escapes, `.`, classes (`[a-z]`, `[^"\\]`, `\d`, `\w`, `\s`),
  groups, `|`, `?`, `*`, `+`, `{n,m}`. Anchors, back-references, look-arounds, lazy quantifiers and flags are compile
  errors, as are patterns matching the empty string.
- One lexer for all terminals, **longest match**; on equal length a **literal beats a regex** (keywords vs
  identifiers).
- `Slices.indexOf(input, ch, start, end)` searches within the token; `Numbers.int`/`long`/`double` parse in place:

```scala
val string = terminal("\"[^\"]*\"").mapSlice((input, start, end) => input.substring(start + 1, end - 1))
val number = terminal("-?[0-9]+(\\.[0-9]+)?([eE][+-]?[0-9]+)?").mapSlice(Numbers.double)
```

With a `String` input, `input` in `mapSlice` is the whole input: stay within `[start, end)`.

## Actions

- Pure actions (`.pure`) never touch `F`; effectful actions must return `F[R]` of the grammar's `F`.
- Ignored parameters (`_`) are never converted (`.map` does not run).
- Actions are lifted into generated code: they may use anything in scope **except** grammar symbols / the DSL.
- `.map` functions and pure actions may be skipped when unused and may run twice (fast-path fallback): keep them pure.

## Collections: `.as[C]`

Any type Hearth's standard extensions recognise:

- `IsCollection`: Scala collections (`Vector`, `Set`, `ArraySeq`, `ArrayBuffer`, ...), arrays, Java collections (JVM),
  and provider-backed types such as cats `NonEmptyList`/`NonEmptyVector`/`NonEmptyChain`/`Chain` (add
  `kindlings-cats-integration`);
- `IsValueType` wrapping a collection: `AnyVal` wrappers, refined / Iron types (add `kindlings-refined-integration` /
  `kindlings-iron-integration`).

```scala
final case class Tags(values: Set[String]) extends AnyVal
tags ::= all(rep(terminal("#[a-z]+")).as[Tags]).pure(t => t)
list ::= all("[", sepBy(num, ",").as[ArraySeq[Int]], "]").pure((_, ns, _) => ns)
```

Maps are rejected (collect pairs, `.toMap` in the action). A builder is filled directly; no intermediate `List`.
Types whose smart constructor can reject values (`NonEmptyList`, `List[Int] Refined NonEmpty`,
`List[Int] :| MinLength[2]`) produce a `ParseError` (`Invalid cats.data.NonEmptyList[scala.Int]: ...`) and so require
an `ErrorChannel[F]` (Option, Try, Either with `ParseErrorLift`, Future, cats-effect `F` with the `catseffect` import),
or `enable(ThrowingInRuntime)` for `Id`.

## Precedence

```scala
left("-")
right("^")
nonassoc("NEG")              // highest: declared last
expr ::= (
  all(expr, "-", expr).pure((a, _, b) => a - b) ||
    all(expr, "^", expr).pure((a, _, b) => math.pow(a.toDouble, b.toDouble).toInt) ||
    all("-", expr).prec("NEG").pure((_, e) => -e) ||
    all(num).pure(n => n)
)
// "10 - 2 - 3" == 5, "2 ^ 3 ^ 2" == 512, "-2 ^ 2" == 4
```

A production takes the precedence of its last terminal that has one, or of `.prec(op)`. Precedence declarations
disable the recursive-descent fast path.

## Compile-time diagnostics (exact message starts)

| Message | Fix |
|---|---|
| `shift/reduce conflict on X: after ... the parser can either reduce by it or shift X` (+ LR state) | precedence/associativity for `X` and the production, or restructure |
| `reduce/reduce conflict on X: both ... and ... can be reduced` | restructure (remove duplicated / overlapping empty alternatives) |
| `non-terminal x has no productions (add some with x ::= ...)` | add productions |
| `non-terminal x cannot derive any finite input` | add a non-recursive alternative |
| `non-terminal x is not reachable from the start symbol` (warning) | remove it or use it |
| `terminal ... matches the empty string` / `skipped pattern /.../ matches the empty string` | require at least one char |
| `skipped pattern /.../ is also used as a terminal` | use different patterns |
| `invalid terminal pattern: ...` / `regex patterns must be string literals` | supported regex subset, literal strings |
| `the pattern ... is used by a terminal with mapSlice and by another terminal` | one declaration per `mapSlice` pattern |
| `.mapSlice must be the first conversion of a terminal(...)` | reorder |
| `.as[C] is only available on repetitions (rep, rep1, sepBy, sepBy1)` | apply `.as` to a repetition |
| `grammar symbols (and the grammar DSL) can only be used in productions, not inside actions or .map functions` | compute from action parameters |
| `grammar blocks may only contain declarations ...` / `helper methods are not supported in grammar blocks yet` | keep the block static |
| `the left-hand side of ::= must be a non-terminal declared in this grammar block` | declare it with `nonTerminal` |
| `the grammar block must end with the start non-terminal` | end the block with the start symbol |
| `RequireLL1 and RequireLALR ask for different parsers` / `X is both enabled and disabled` | conflicting flags |
| `enable(RequireLL1): this grammar is not LL(1) ...` | see performance.md |

## Limitations

- Static grammar block only (no conditionals, loops or helper methods around declarations/productions).
- Literal patterns only.
- No grammar composition: a grammar is one block.
