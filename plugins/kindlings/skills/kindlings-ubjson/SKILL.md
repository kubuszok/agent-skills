---
name: kindlings-ubjson
description: >-
  Deriving UBJSON (Universal Binary JSON) codecs with kindlings-ubjson-derivation on Scala 2.13 and 3
  (JVM/JS/Native). Covers UBJsonValueCodec (.derived, derives), UBJsonWriter / UBJsonReader (toByteArray),
  UBJsonConfig (withDiscriminator, withSnakeCaseFieldNames, withAdtLeafClassNameMapper,
  withTransientNone/Default/Empty, withRequireDefaultFields, withEmptyCollectionsAsEmpty, DoS limits), annotations
  @fieldName, @named, @transientField, @stringified, UBJsonValueCodecExtensions map/mapDecode, and
  UBJsonReaderException ("missing required field"). Jsoniter-scala-like semantics on a binary format. Use when code
  imports hearth.kindlings.ubjsonderivation, when serializing case classes or sealed traits to compact binary JSON,
  or when writing a UBJsonValueCodec for a custom type.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings UBJSON derivation (`kindlings-ubjson-derivation`)

A self-contained [UBJSON](https://ubjson.org/) library: a streaming `UBJsonWriter` / `UBJsonReader` plus compile-time
derivation of `UBJsonValueCodec[A]`. Encoding rules and config mirror jsoniter-scala's `CodecMakerConfig` (and
`kindlings-jsoniter`), applied to typed binary values. No upstream library is replaced.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/ubjson-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-ubjson-derivation" % "0.4.0" // %% on JVM-only builds
```

```scala
//> using dep com.kubuszok::kindlings-ubjson-derivation:0.4.0
```

No other runtime dependency. JVM, Scala.js, Scala Native; Scala 2.13 and 3.

## Imports

```scala
import hearth.kindlings.ubjsonderivation._                              // codec, reader, writer, UBJsonConfig
import hearth.kindlings.ubjsonderivation.annotations._                  // @fieldName, @named, @transientField
import hearth.kindlings.ubjsonderivation.UBJsonValueCodecExtensions._   // codec.map / codec.mapDecode
```

## Core usage

```scala
case class Person(name: String, age: Int)

// Scala 2.13 (also valid on Scala 3)
implicit val personCodec: UBJsonValueCodec[Person] = UBJsonValueCodec.derived[Person]

// Scala 3
given UBJsonValueCodec[Person] = UBJsonValueCodec.derived
case class Person3(name: String) derives UBJsonValueCodec

val writer = new UBJsonWriter()          // in-memory buffer; new UBJsonWriter(out: java.io.OutputStream) streams
personCodec.encode(writer, Person("Alice", 30))
val bytes: Array[Byte] = writer.toByteArray   // only for the no-arg (in-memory) writer

val back: Person = personCodec.decode(new UBJsonReader(bytes))  // throws UBJsonReaderException on bad input
```

`UBJsonValueCodec[A]` has `decode(reader: UBJsonReader): A`, `encode(writer: UBJsonWriter, value: A): Unit` and
`nullValue: A`. Decoding throws (no `Either`): `UBJsonReaderException(message, position)`, e.g.
`missing required field "a" (at position 2)`; wrap in `Try` if needed.

`UBJsonValueCodec.derived` is an implicit/given ("sanely-automatic"): `implicitly[UBJsonValueCodec[A]]` derives on
demand, nested types are derived recursively in one expansion, and your own `UBJsonValueCodec[X]` instances win.

### Custom types via `map` / `mapDecode`

```scala
import java.time.Instant
implicit val instantCodec: UBJsonValueCodec[Instant] =
  UBJsonValueCodec.derived[Long].map(Instant.ofEpochMilli)(_.toEpochMilli)

case class Email(value: String)
implicit val emailCodec: UBJsonValueCodec[Email] =
  UBJsonValueCodec.derived[String].mapDecode(s => if (s.contains("@")) Right(Email(s)) else Left("bad email"))(_.value)
```

`mapDecode` failures become `UBJsonReaderException` via `reader.decodeError(msg)`.

## Configuration (`UBJsonConfig`)

Implicit, default `UBJsonConfig.default`; builders return a copy:

```scala
implicit val ubjsonConfig: UBJsonConfig = UBJsonConfig.default
  .withSnakeCaseFieldNames
  .withDiscriminator("type")
  .withTransientNone
```

Most-used options (full table with defaults: [configuration.md](configuration.md)):

- names: `withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`,
  `withScreamingSnakeCaseFieldNames`, `withFieldNameMapper(f)`; subtypes: `withSnakeCaseAdtLeafClassNames`,
  `withKebabCaseAdtLeafClassNames`, `withAdtLeafClassNameMapper(f)` (receives the **fully qualified** leaf name; default
  `UBJsonConfig.simpleClassName`). Mappers may be `PartialFunction`s (undefined names stay unchanged).
- ADTs: default wrapper `{"Circle":{"radius":1.0}}`, case objects as strings `"Origin"`; `withDiscriminator(field)` →
  `{"type":"Circle","radius":1.0}`; `withCirceLikeObjectEncoding` → case objects as `{"Origin":{}}`;
  `withEnumAsStrings` keeps all-case-object ADTs as strings even with a discriminator.
- encoding omissions: `withTransientDefault`, `withTransientEmpty`, `withTransientNone`, `withTransientNull`.
- decoding strictness: `withRequireDefaultFields`, `withRequireCollectionFields`, `withCheckFieldDuplication`,
  `withSkipUnexpectedFields(false)`, `withRequireDiscriminatorFirst(false)`.

Missing fields decode as their default, `None`, `null` (Scala 3 `T | Null`) or an empty collection; anything else
throws `missing required field "<name>"`. As in jsoniter-scala, `null` for a field with a default and an empty
array/object for a collection field with a default decode **as the default** (see Gotchas).

The config is evaluated at compile time when it is `UBJsonConfig.default`, passed explicitly, or (Scala 3) an
`implicit val`/`given` initialised with such an expression - the codec then has no runtime config checks. Configs
from a `var` or computed at runtime work too, checked when the codec runs.

## Annotations (`hearth.kindlings.ubjsonderivation.annotations`)

| Annotation | Effect |
|---|---|
| `@fieldName("n")` | field name |
| `@named("n")` | on an ADT leaf: its name, used as is; on a field: like `@fieldName` |
| `@transientField` | skipped both ways; field needs a default |
| `@stringified` | accepted for source compatibility with jsoniter, **no effect** (UBJSON numbers are typed) |

## Type support

Primitives as native UBJSON types, `BigDecimal`/`BigInt` (`H` high-precision, DoS-limited), `String`, `Option`
(`null` for `None`), collections, `Map` (string keys → object, other keys → array of pairs), tuples (arrays), case
classes and plain classes (primary-constructor `val`/`var` params, all parameter lists), value classes (unwrapped),
sealed hierarchies (nested ones flattened to leaves), Scala 3 enums, Java enums and `scala.Enumeration` (names, or ids
with `withUseScalaEnumValueId`), Scala 3 `T | Null`, generic, higher-kinded and recursive types.

## Gotchas

- **`C(xs = Nil)` decodes back with the default `xs`** when the field has a non-empty default (jsoniter semantics).
  Fix: `withEmptyCollectionsAsEmpty`. Similarly `None` in a field whose default is `Some(...)` decodes as the default
  unless `withRequireDefaultFields`.
- **`Some(None)` round-trip**: nested `Option[Option[A]]` is encoded as the ADT `Option` by default so it survives;
  `withSkipNestedOptionValues` flattens it.
- **Contradictory config** (`requireCollectionFields` + `transientEmpty`, `requireDefaultFields` + `transientDefault`,
  discriminator + `circeLikeObjectEncoding`) fails compilation when the config is known at compile time, otherwise
  throws `IllegalArgumentException` when the codec is created.
- **Duplicate names** after mapping / `@fieldName` / `@named`, or two leaves mapping to the same name, fail derivation.
- **Side-effecting `fieldNameMapper`** with a runtime-only config runs once per field per codec instance (on first
  use), not per decode (after 0.4.0).
- **`toByteArray` throws `UnsupportedOperationException`** on a writer created over your own `OutputStream`.
- **Not interchangeable with JSON**: same data model, binary wire format. For JSON use `kindlings-jsoniter` /
  `kindlings-circe`.

## Debugging, timeouts, policy

- Settings namespace: `ubjsonDerivation`.
- Log one derivation: `import hearth.kindlings.ubjsonderivation.debug._`; project-wide:
  `scalacOptions += "-Xmacro-settings:ubjsonDerivation.logDerivation=true"`.
- Timeout (default 5 s): `-Xmacro-settings:ubjsonDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.ubjsonderivation.policy._` (`allowDerivationForUbjsonDerivation`).

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`, `kindlings-integrations`.

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/ubjson-derivation/>
- Feature parity: <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#ubjson-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/ubjson-derivation/src/main>
