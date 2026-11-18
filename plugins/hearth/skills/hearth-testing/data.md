# `hearth.data.Data` reference (Hearth 0.4.5)

`import hearth.data.Data` (also `hearth.data.{DiffEntry, Diff}`). Part of the main `hearth` artifact, works on
JVM/Scala.js/Scala Native. Examples below were run on Scala 3.3.7 and 2.13.16; output is real.

## What it is

A JSON-like value: null, `Int`, `Long`, `Float`, `Double`, `Boolean`, `String`, `List[Data]` or `Map[String, Data]`.
It is an unboxed type (`type Data = Data.Impl`; an opaque union type on Scala 3, an abstract type on Scala 2), so
there is no case class to pattern-match on - use `fold` or the `asX` accessors.

## Building

```scala
Data()                         // null
Data(1); Data(1L); Data(1.5f); Data(1.5); Data(true); Data("x")
Data(List(Data(1)))            // from List[Data]
Data(Map("k" -> Data(1)))      // from any Map[String, Data]
Data.list(Data(1), Data("x"))  // varargs
Data.map("a" -> Data(1), "b" -> Data.list())  // varargs, ListMap: insertion order kept
```

In a macro, `Expr(data)` turns a `Data` into code that rebuilds it (the built-in `ExprCodec[Data]` is bidirectional,
so it can also read a literal `Data` expression back).

## Reading

All on the implicit `Data.DataOps`:

| Method                                                         | Result                                      |
|----------------------------------------------------------------|---------------------------------------------|
| `fold(onNull, onInt, onLong, onFloat, onDouble, onBoolean, onString, onList, onMap)` | the matching handler's result (`onNull` is by-name) |
| `asNull` / `asInt` / `asLong` / `asFloat` / `asDouble` / `asBoolean` / `asString` / `asList` / `asMap` | `Option` (`asNull: Option[Unit]`), `None` for any other shape |
| `get(key: String)` / `get(index: Int)`                         | `Option[Data]` (`None` if not a map/list or missing) |
| `getOrElse(key, default)` / `getOrElse(index, default)`        | `Data`                                      |
| `updateAsInt(f)` ... `updateAsMap(f)`                          | `Data` with `f` applied if the shape matches, unchanged otherwise |
| `diff(expected: Data)`                                         | `Diff` = `List[DiffEntry]`, empty if equal  |
| `render`                                                       | multi-line text, `Long` with `L`, `Float` with `f`, strings quoted |

```scala
val d = Data.map("a" -> Data.list(Data(1), Data("x")), "b" -> Data())
d.get("a").flatMap(_.get(1)).flatMap(_.asString)  // Some("x")
d.getOrElse("missing", Data(0))                    // Data(0)
d.get("b").flatMap(_.asNull)                       // Some(())
d.updateAsMap(_ - "b")                             // {a: [1, "x"]}
d.fold("null", _ => "int", _ => "long", _ => "float", _ => "double", _ => "bool", _ => "string", _ => "list",
  m => s"map of ${m.size}")                        // "map of 2"
d.render
// {
//   a: [
//     1,
//     "x"
//   ],
//   b: null
// }
```

In tests, prefer `actual <==> expected` over reading fields one by one.

## Diff

`DiffEntry(expected: Data, actual: Data, path: List[DiffEntry.Path])`, path segments `DiffEntry.Key(key)` /
`DiffEntry.Index(idx)`, `renderedPath` like `b[1]` or `a.c`, `render` (ANSI-colored, `-` expected, `+` actual).
`Diff` has `.render` too, after `import hearth.data._` (Scala 3: `hearth.data.*`).

```scala
val actual = Data.map("a" -> Data(1), "b" -> Data.list(Data("x"), Data("y")))
val expected = Data.map("a" -> Data(2), "b" -> Data.list(Data("x")), "c" -> Data(true))
actual.diff(expected).map(e => s"${e.renderedPath}: ${e.expected.render} vs ${e.actual.render}")
// List(a: 2 vs 1, b[1]: null vs "y", c: true vs null)
```

- Maps are compared by key (order does not matter), lists by index; a missing key/element appears as `null`.
- Leaves are compared with Scala `==` on the boxed values, so `Data(1)` equals `Data(1L)` and `Data(1.0)` -
  `Data(1).diff(Data(1L))` is empty. `render` still shows the difference (`1` vs `1L`).

## Parsing strings and settings

`Data.parseString(s: String): Either[String, Data]` - after `trim`:

| Input                         | Result                          |
|-------------------------------|---------------------------------|
| `42`, `-7`                    | `Int` (too large -> `Left("For input string: \"99999999999\"")`) |
| `42L`                         | `Long`                          |
| `1.5`, `1.5d`                 | `Double`                        |
| `1.5f`, `1f`                  | `Float`                         |
| `true`, `FALSE` (any case)    | `Boolean`                       |
| `"quoted"`                    | `String` without the quotes     |
| anything else (`1e3`, `hello`, `a b`) | `String`, as given (untrimmed) |

`Data.parseList(strings: List[String]): Either[String, Data]` - parses `key=value` entries; dotted keys nest:

```scala
Data.parseList(List("mylib.debug=true", "mylib.limit=42", "mylib.big=42L", "mylib.ratio=1.5f", "mylib.raw=hello"))
  .map(_.render)
// Right({
//   mylib: {
//     big: 42L,
//     debug: true,
//     limit: 42,
//     ratio: 1.5f,
//     raw: "hello"
//   }
// })
Data.parseList(List("a=1", "a.b=2"))  // Left(a: values: 1 AND nested values: b)
Data.parseList(List("a=1", "a=2"))    // Left(a: multiple values: 1, 2)
Data.parseList(List("flag", "a.b=1")) // Right(ListMap(a -> ListMap(b -> 1))) - entries without '=' are ignored
Data.parseList(List("mylib.limit=99999999999", "x=1", "x=2"))
// Left(limit: For input string: "99999999999"
// x: multiple values: 1, 2)
```

- Errors of all keys are collected and joined with newlines; a value error is prefixed with its innermost key only.
- Key order of the result is **not** the input order (keys are grouped through a `Map`); `<==>` does not care, but
  `render` / `toString` may list keys differently than written.

### `-Xmacro-settings`

Inside a macro, `Environment.typedSettings: Either[String, Data]` is `Data.parseList(Environment.XMacroSettings)`.
With

```scala
scalacOptions ++= Seq("-Xmacro-settings:mylib.debug=true", "-Xmacro-settings:mylib.limit=42")
// Scala CLI: //> using options -Xmacro-settings:mylib.debug=true -Xmacro-settings:mylib.limit=42
```

a fixture returning `Expr(Environment.typedSettings.fold(e => Data(s"error: $e"), identity))` yields
`Data.map("mylib" -> Data.map("debug" -> Data(true), "limit" -> Data(42)))` on both Scala 2.13 and 3 (repeated
`-Xmacro-settings:` flags accumulate). Read one value with
`Environment.typedSettings.toOption.flatMap(_.get("mylib")).flatMap(_.get("debug")).flatMap(_.asBoolean)`.

Namespace keys by library (`mylib.*`): every macro library sees all settings, and one malformed entry (e.g. `a=1`
next to `a.b=2`) turns the whole `typedSettings` into a `Left`.
