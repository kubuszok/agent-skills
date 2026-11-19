---
name: kindlings-fast-show-pretty
description: >-
  Pretty-printing Scala values as indented, Scala-literal-like text with kindlings-fast-show-pretty (Scala 2.13 and
  3, JVM/JS/Native). Covers FastShowPretty.render(value, RenderConfig), the FastShowPretty[A] type class (derived,
  derives FastShowPretty, render into a StringBuilder), RenderConfig (Default, Compact, Tabs, FourSpaces,
  indentString, startLevel), @sensitiveData redaction ([redacted], [redacted: reason]), primitive suffixes (42L,
  3.14d, 1.toByte), and how it differs from cats Show / ShowPretty. Use when code imports
  hearth.kindlings.fastshowpretty, when logging or debugging nested case classes, collections and ADTs as readable
  multi-line output, or when redacting passwords / PII in rendered values.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings FastShowPretty (`kindlings-fast-show-pretty`)

Kindlings' own pretty-printer: renders case classes, sealed traits, enums, collections, maps and primitives as
indented, multi-line, Scala-literal-like text (quoted and escaped strings, typed numeric literals). Not a cats
type class - for `cats.Show` / kittens-style `ShowPretty` see `kindlings-cats`.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/fast-show-pretty/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-fast-show-pretty" % "0.4.0" // %% on JVM-only builds
```

```scala
//> using dep com.kubuszok::kindlings-fast-show-pretty:0.4.0
```

No other runtime dependencies. JVM, Scala.js, Scala Native; Scala 2.13 and 3.

## Usage

```scala
import hearth.kindlings.fastshowpretty._

case class Address(street: String, city: String)
case class Person(name: String, age: Int, address: Address)

// One call: derive + render inline, no instance kept
println(FastShowPretty.render(Person("Alice", 30, Address("123 Main St", "NY")), RenderConfig.Default))
// Person(
//   name = "Alice",
//   age = 30,
//   address = Address(
//     street = "123 Main St",
//     city = "NY"
//   )
// )
```

Type class form, when an instance must be passed around:

```scala
// Scala 2.13 (also valid on Scala 3)
implicit val personShow: FastShowPretty[Person] = FastShowPretty.derived[Person]
// Scala 3
case class Point(x: Int, y: Int) derives FastShowPretty

val sb = personShow.render(new StringBuilder, RenderConfig.Default, 0)(person)  // appends to sb, returns it
sb.toString
```

`trait FastShowPretty[A] { def render(sb: StringBuilder, config: RenderConfig, level: Int)(value: A): StringBuilder }`.
`FastShowPretty.derived` is an implicit/given ("sanely-automatic"): `implicitly[FastShowPretty[A]]` derives on demand;
nested types are derived recursively; your own `FastShowPretty[X]` instances are used for `X` fields. There is no
`show` syntax extension - write a helper such as `def pretty[A: FastShowPretty](a: A): String`.

## `RenderConfig`

`final case class RenderConfig(indentString: String = "  ", startLevel: Int = 0)`.

| Constant | `indentString` |
|---|---|
| `RenderConfig.Default` | two spaces |
| `RenderConfig.Compact` | `""` - still one field per line, just not indented |
| `RenderConfig.Tabs` | `"\t"` |
| `RenderConfig.FourSpaces` | four spaces |

`startLevel` indents nested lines as if the value were already `startLevel` levels deep (the first line is not
indented) - useful when embedding output in an already indented log line. There is no single-line mode.

## Output format

| Value | Rendered |
|---|---|
| `Int` / `Long` / `Double` / `Float` | `42` / `42L` / `3.14d` / `3.14f` |
| `Byte` / `Short` | `42.toByte` / `42.toShort` |
| `Char` / `String` | `'a'` / `"hello"` (escaped) |
| case class | `Name(\n  field = value,\n  ...\n)` |
| collection | `List(\n  "a",\n  "b"\n)`, empty `List()` |
| map | `Map(\n  ("a", 1)\n)` |
| tuple | `Tuple2(\n  _1 = 1,\n  _2 = "x"\n)` |
| sealed-trait / enum value | `(Circle(\n    radius = 5.0d\n  )): Shape`, case object `(Red()): Color` |

## `@sensitiveData`

```scala
import hearth.kindlings.fastshowpretty.annotations.sensitiveData

case class User(name: String, @sensitiveData password: String, @sensitiveData("PII") email: String)
// password = [redacted], email = [redacted: PII]

@sensitiveData("financial data") case class CreditCard(number: String)
// any CreditCard, also nested as a field, renders as [redacted: financial data]
```

## Compared with cats `Show` / `ShowPretty`

`cats.Show` (also Kindlings-derived, see `kindlings-cats`) is single-line and prints strings unquoted
(`Person(name = Alice, age = 30)`); `ShowPretty` is multi-line. FastShowPretty adds quoting/escaping, typed literals,
configurable indentation and the ADT type ascription; it does not need cats.

## Gotchas

- **Unexpected `(X()): Parent` wrapping**: values statically typed as a sealed trait / enum are rendered with the
  parent type; render a case class / case object at its own type (`render(Circle(1.0), ...)` → `Circle(...)`) to
  drop it (Scala 3 enum cases are always typed as the enum).
- **Output too long for logs**: it is always multi-line; there is no width-based folding.
- **`render` without a config**: there is no default argument - pass `RenderConfig.Default`.

## Debugging, timeouts, policy

All settings live under `fastShowPrettyDerivation` (after 0.4.0; 0.4.0 read logging only from `fastShowPretty`):

- Logging: `import hearth.kindlings.fastshowpretty.debug._` (`logDerivationForFastShowPretty`) or
  `scalacOptions += "-Xmacro-settings:fastShowPrettyDerivation.logDerivation=true"` (the legacy
  `fastShowPretty.logDerivation=true` is still accepted).
- Timeout and policy: `-Xmacro-settings:fastShowPrettyDerivation.timeout=30s`,
  `-Xmacro-settings:fastShowPrettyDerivation.policy.enabled=opt-in`; opt-in marker
  `import hearth.kindlings.fastshowpretty.policy._` (`allowDerivationForFastShowPretty`).

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`.

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/fast-show-pretty/>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/fast-show-pretty/src/main>
