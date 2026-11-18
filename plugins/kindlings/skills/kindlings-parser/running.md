# Running parsers (kindlings-parser 0.4.0)

Full docs: <https://kindlings.readthedocs.io/en/0.4.0/parser-running/>

## Effects and engines

`Grammar.grammar[R, F]` needs an implicit `ParserEngine[F]` **where the grammar is defined** and returns
`Parser[F, R]`. Built-in engines (in `ParserEngine`'s companion, no import needed): `Id`, `Option`, `Try`,
`Either[E, *]` (needs a `ParseErrorLift[E]`; built-in for `ParseError`, `Throwable`, `String`) and `Future` (needs an
implicit `ExecutionContext`; one continuation per effectful action, effects run in parse order).

```scala
type Result[A] = Either[String, A] // use an alias for Either (no kind-projector needed)

final case class MyError(msg: String)
implicit val lift: ParseErrorLift[MyError] = (e: ParseError) => MyError(e.getMessage) // custom Left type
```

Pure work (lexing, parsing, `.pure` actions) runs inline; `F` is only touched when an effectful action produced a value.

### Cats Effect (`kindlings-parser-cats-effect`)

```scala
import cats.effect.IO
import hearth.kindlings.parser._
import hearth.kindlings.parser.catseffect._   // ParserEngine + ErrorChannel for any Async[F] / Sync[F]

val parser: Parser[IO, Int] = Grammar.grammar[Int, IO] { g =>
  import g._
  val sum = nonTerminal[Int]
  val num = terminal("[0-9]+").map(_.toInt)
  skip(" +")
  sum ::= (
    all(num)(n => IO.println(s"read $n").as(n)) ||
      all(sum, num)((s, n) => IO.println(s"read $n").as(s + n))
  )
  sum
}
parser.parse("1 2 3") // IO[Int]; the parse runs when the IO runs (and again on each run)
```

- One `delay` segment for pure work; each effectful action costs one `flatMap`.
- Every `budget` steps (default `CatsEffectEngine.DefaultBudget` = 4096) the engine `cede`s (for `Async`).
  Custom: `implicit val engine: ParserEngine[IO] = CatsEffectEngine.async[IO](budget = 16384)` (or
  `CatsEffectEngine.sync[F](budget = ...)`).
- `Reader`/`InputStream` refills run in `Sync[F].blocking`.
- Syntax errors are `F.raiseError(ParseError)`.
- Budgeted engines do not use the recursive-descent fast path.

## Inputs

| Call | Notes |
|---|---|
| `parser.parse(input: String)` | in place; the only input that can use the recursive-descent fast path |
| `parser.parse(reader: java.io.Reader, bufferSize = Parser.DefaultBufferSize)` | chunked; memory bounded by buffer + longest token; positions are `Long`; reader not closed |
| `parser.parse(stream: java.io.InputStream)` | UTF-8, chunked; stream not closed |
| `parser.pushMachine(initialBufferSize = Parser.DefaultBufferSize)` | low-level push API (below) |

`Parser.DefaultBufferSize` is 64 KiB. `parser.terminalNames` lists the token names used in error messages.

### fs2 (`kindlings-parser-fs2`)

```scala
import hearth.kindlings.parser.streams._
```

| Pipe | Parser | Stream |
|---|---|---|
| `parser.pipe` | `Parser[F, R]` (effectful actions evaluated in `F`) | `Stream[F, String]` |
| `parser.bytePipe` | `Parser[F, R]` | `Stream[F, Byte]` (UTF-8) |
| `parser.pipeIn[G]` | `Parser[Id, R]` | `Stream[G, String]`, any `G` |
| `parser.bytePipeIn[G]` | `Parser[Id, R]` | `Stream[G, Byte]` (UTF-8) |

```scala
val sum: Parser[Id, Int] = Grammar.grammar[Int, Id] { g =>
  import g._
  val sum = nonTerminal[Int]
  skip("[ \\n]+")
  sum ::= all(rep(terminal("[0-9]+").map(_.toInt))).pure(_.sum)
  sum
}
Stream("1 2 ", "3", "4 5\n", "6").covary[IO].through(sum.pipeIn[IO]).compile.lastOrError // IO(48): "34" spans chunks
```

The whole stream is one input producing one `R`; tokens and multi-byte UTF-8 characters may span chunks; memory stays
bounded. To parse many records, make the start symbol a repetition (or split the stream yourself).

### Push machine (integrations, REPLs)

```scala
import hearth.kindlings.parser.internal.runtime.Machine // status constants live here in 0.4.0

val m = parser.pushMachine()
m.feed("1 2 ")
m.feed("3")
m.endOfInput()
m.run(budget = 4096) match {               // returns an Int status
  case Machine.Done      => m.result       // Any: cast to R
  case Machine.Error     => throw m.error  // ParseError
  case Machine.Effect    => /* run m.pendingEffect (an F[_]), then m.resume(value) and run again */
  case Machine.NeedInput => /* feed more (or endOfInput()) and run again */
  case Machine.Yield     => /* budget spent: run again later */
}
```

The engines and fs2 pipes are built on this machine.

## Syntax errors

`ParseError extends Exception` with `offset: Long`, `line: Int`, `column: Int`, `found: String`,
`expected: List[String]`, `detail: String`, `endOfInput: Boolean`. Message format:
`Unexpected token at 1:9: found "+", expected num` (or `expected one of: ...`).

`endOfInput == true` means the input ended while more was expected - the input is a valid prefix (a REPL can ask for
another line). Values rejected by a collection's smart constructor are `ParseError`s too.

With `enable(RequireLL1)`, the fallback on `String` inputs is a top-down machine whose `expected` lists only the tokens
valid in the current context.
