---
name: kindlings-jsoniter
description: >-
  Kindlings jsoniter-scala derivation (kindlings-jsoniter-derivation, package hearth.kindlings.jsoniterderivation) -
  deriving JsonValueCodec, JsonCodec and JsonKeyCodec with KindlingsJsonValueCodec.derived,
  KindlingsJsonCodec.derived/deriveKeyCodec, writeToString/readFromString, syntax toJsonString/fromJsonString,
  JsoniterConfig (withDiscriminator, withTransientNone, withTransientDefault, jsoniterScalaDefaults, makeCirceLike
  presets), @named/@fieldName/@transientField/@stringified. Also the kindlings-jsoniter-json AST
  (hearth.kindlings.jsoniterjson.Json, JsonPath optics) and kindlings-tapir-openapi-jsoniter (TapirOpenApi,
  OpenApiJsoniter). Use when replacing jsoniter-scala-macros JsonCodecMaker.make / CodecMakerConfig, when output
  differs from JsonCodecMaker (None written as null, discriminator missing, wrapper objects, default fields
  written), on Option/null/missing-field questions, "missing required field", jsoniterDerivation timeouts, or
  Circe-free JSON AST / OpenAPI serialization.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings jsoniter-scala derivation

Derives jsoniter-scala `JsonValueCodec` / `JsonCodec` / `JsonKeyCodec` for case classes, sealed traits, Scala 3
enums, Java enums, `Enumeration`s, tuples, named tuples, opaque types and more, with one API on Scala 2.13 and 3. It
replaces `jsoniter-scala-macros` (`JsonCodecMaker`); keep using `jsoniter-scala-core` (`readFromString`,
`writeToArray`, ...).

**Version:** written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
https://kindlings.readthedocs.io/en/0.4.0/jsoniter-derivation/ (replace `0.4.0` with the version used).

Generic topics: `kindlings-getting-started` (setup, sanely-automatic derivation), `kindlings-troubleshooting`
(errors, timeouts, debug output), `kindlings-derivation-policy`, `kindlings-migration`, `kindlings-integrations`.
Sibling references: [codec-maker-config.md](codec-maker-config.md) (full `CodecMakerConfig` -> `JsoniterConfig` map),
[json-ast-and-openapi.md](json-ast-and-openapi.md) (`kindlings-jsoniter-json`, `kindlings-tapir-openapi-jsoniter`).

## Dependency

```scala
libraryDependencies += "com.kubuszok" %% "kindlings-jsoniter-derivation" % "0.4.0"   // JVM
libraryDependencies += "com.kubuszok" %%% "kindlings-jsoniter-derivation" % "0.4.0"  // JVM / Scala.js / Scala Native
//> using dep com.kubuszok::kindlings-jsoniter-derivation:0.4.0
```

`jsoniter-scala-core` comes transitively (declare it explicitly to pin its version). Drop `jsoniter-scala-macros`
from files using Kindlings.

## Core usage

```scala
import hearth.kindlings.jsoniterderivation._
import com.github.plokhotnyuk.jsoniter_scala.core._

case class Person(name: String, age: Int, tags: List[String])
object Person {
  implicit val codec: JsonValueCodec[Person] = KindlingsJsonValueCodec.derived[Person]
}

writeToString(Person("Ann", 30, Nil))           // {"name":"Ann","age":30,"tags":[]}
readFromString[Person]("""{"name":"Bob","age":2}""") // tags absent -> Nil
```

Scala 3: `case class Person(...) derives KindlingsJsonValueCodec`, or
`given JsonValueCodec[Person] = KindlingsJsonValueCodec.derived`.

| Method | Result |
|---|---|
| `KindlingsJsonValueCodec.derived[A]` | `KindlingsJsonValueCodec[A] <: JsonValueCodec[A]` (implicit def / `given`) |
| `KindlingsJsonCodec.derived[A]` | `KindlingsJsonCodec[A] <: JsonCodec[A]` (value + key codec, for types also used as map keys) |
| `KindlingsJsonCodec.deriveKeyCodec[A]` | `JsonKeyCodec[A]` |
| `KindlingsJsonValueCodec.writeToString[A](a)` | `String` (inline, no instance kept) |
| `KindlingsJsonValueCodec.readFromString[A](s)` | `Either[JsonReaderException, A]` |
| `import hearth.kindlings.jsoniterderivation.syntax._`: `a.toJsonString`, `s.fromJsonString[A]` | same as the two above |
| `import JsonValueCodecExtensions._`: `codec.map(f)(g)`, `codec.mapDecode(f)(g)` | adapt an existing codec (`f` returns `Either[String, B]` in `mapDecode`) |

Every method takes an implicit/`using` `JsoniterConfig` (default `JsoniterConfig.default` from the companion). Pass
one explicitly: `KindlingsJsonValueCodec.derived[A](cfg)` (Scala 2) / `derived[A](using cfg)` (Scala 3).

## Configuration

```scala
implicit val config: JsoniterConfig = JsoniterConfig.default
  .withSnakeCaseFieldNames
  .withDiscriminator("type")
  .withTransientNone
```

Most-used builders (full list and upstream mapping: [codec-maker-config.md](codec-maker-config.md)):

- Names: `withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`,
  `withScreamingSnakeCaseFieldNames`, `withFieldNameMapper(f)` (a function or `{ case "a" => "b" }`),
  `withSnakeCaseAdtLeafClassNames`, `withKebabCaseAdtLeafClassNames`, `withAdtLeafClassNameMapper(f)` (receives the
  **fully-qualified** name), `withJavaEnumValueNameMapper(f)`.
- ADTs: `withDiscriminator(field)`, `withDiscriminatorFieldName(opt)`, `withRequireDiscriminatorFirst(false)`,
  `withAlwaysEmitDiscriminator`, `withCirceLikeObjectEncoding`, `withEnumAsStrings` (Kindlings-only).
- Writing: `withTransientDefault`, `withTransientEmpty`, `withTransientNone`, `withTransientNull`, `withStringified`,
  `withMapAsArray`, `withInlineOneValueClasses`, `withSkipNestedOptionValues`.
- Reading: `withSkipUnexpectedFields(false)`, `withRequireCollectionFields`, `withRequireDefaultFields`,
  `withCheckFieldDuplication`, `withEmptyCollectionsAsEmpty` (Kindlings-only), number/insert limits
  (`withMapMaxInsertNumber(n)`, `withSetMaxInsertNumber(n)`, `withBigDecimalPrecision(n)`, ...).
- `withDecodingOnly` / `withEncodingOnly`, `withUseScalaEnumValueId`, `withScalaTransientSupport`.
- Presets: `JsoniterConfig.jsoniterScalaDefaults` (upstream's defaults), `JsoniterConfig.makeCirceLike`,
  `makeOpenapiLike`, `makeWithoutDiscriminator`, ... (one per `JsonCodecMaker.makeXxx`).

Builders mostly take no argument and switch a flag on; to switch one off use `copy(flag = false)`.
Contradictory settings (e.g. `withCirceLikeObjectEncoding` with a discriminator) are compile errors for a config known
at compile time, and an `IllegalArgumentException` when the codec is created otherwise.

A config is evaluated at compile time when it is `JsoniterConfig.default`, a preset, an expression passed directly,
or (Scala 3) a local `val`/`given` or an `object`'s `val` initialised with such an expression; then compile-time
validations apply and the codec has no runtime config checks. On Scala 2, configs stored in members of classes/objects
of the module being compiled are always treated as runtime configs.

Annotations (`import hearth.kindlings.jsoniterderivation.annotations._`): `@fieldName("x")` or `@named("x")` on a field,
`@named("X")` on an ADT leaf / Scala 3 enum case, `@transientField` (needs a default), `@stringified`.

## Wire format and Option / null / missing semantics

Kindlings' **defaults differ from `JsonCodecMaker.make`** in 7 fields: no discriminator (wrapper objects), every field
written (`transientDefault`/`transientEmpty`/`transientNone` off, so `None` is written as `null`), no duplicate-key
check, no map/set insert limits. `JsoniterConfig.jsoniterScalaDefaults` restores upstream exactly.

| Value | Default config | `withDiscriminator("type")` |
|---|---|---|
| `Circle(1.0)` | `{"Circle":{"r":1.0}}` | `{"type":"Circle","r":1.0}` (discriminator first) |
| case object `Origin` | `"Origin"` (`{"Origin":{}}` with `withCirceLikeObjectEncoding`) | `{"type":"Origin"}` (`"Origin"` with `withEnumAsStrings`) |
| Java enum / `Enumeration` | `"VALUE"` | `"VALUE"` |
| `AnyVal` class | its value (always unwrapped) | same |
| tuple / named tuple | `[1,"a"]` / `{"i":1,"s":"a"}` | same |

Absent field when reading: has a default -> the default (fails with `withRequireDefaultFields`); `Option` -> `None`;
collection/map -> empty (fails with `withRequireCollectionFields`); anything else -> `missing required field "x"`.

JSON `null`: `Option` -> `None`; collection/map -> empty; reference type with a default -> the default; primitives /
value classes / reference types without default -> error; Scala 3 `T | Null` -> `null`.

`Option[Option[A]]` without `withSkipNestedOptionValues` is encoded as an ADT (`{"Some":{"value":1}}`), as upstream.

Collection field with a non-empty default: `[]` decodes as **the default** (upstream behaviour). Since Kindlings writes
`C(Nil)` as `{"xs":[]}`, such values do not round-trip unless you add `withEmptyCollectionsAsEmpty`.

Map keys: `String`, primitives and boxes, `BigInt`/`BigDecimal`, `UUID`, `java.time`, value classes/opaque types over
those, case-object enums, and types with an implicit `JsonKeyCodec` (user-provided ones win). Other keys need
`withMapAsArray` (compile error otherwise, with a compile-time config).

## Differences from jsoniter-scala

Checked against `JsonCodecMaker.make` with the equivalent `CodecMakerConfig` for every option. Differences:

- The 7 default values above (`jsoniterScalaDefaults` restores them).
- Recursive types need no `allowRecursiveTypes` flag.
- Without a discriminator a case object is also read from `{"Leaf":{}}` (superset).
- A Scala 3 `T | Null` field holding `null` is written as `null` without `transientNull` (upstream throws an NPE).
- With `checkFieldDuplication` off, a repeated key's decoder gets the field default (upstream: the earlier value).
- Error for another JSON type in a defaulted field says `expected '{'` (upstream adds `or null`).
- Extras: `withEnumAsStrings`, `withEmptyCollectionsAsEmpty`, `Unit` coded as `{}`, `writeToString`/`readFromString`
  and `syntax` without keeping an instance.

## Settings and debugging

- Settings namespace: `jsoniterDerivation`, e.g. `-Xmacro-settings:jsoniterDerivation.timeout=30s`,
  `-Xmacro-settings:jsoniterDerivation.logDerivation=true`, `jsoniterDerivation.policy.*`.
- Debug one scope: `import hearth.kindlings.jsoniterderivation.debug._`.
- Policy opt-in import: `import hearth.kindlings.jsoniterderivation.policy.allowDerivationForJsoniterDerivation`.

## Gotchas

- **`"o":null` in output / fields with default values written** - Kindlings' write-everything defaults; add
  `withTransientNone`, `withTransientDefault`, `withTransientEmpty`, or use `jsoniterScalaDefaults`.
- **Clients expect `{"type":"Circle",...}` but get `{"Circle":{...}}`** - no discriminator by default; add
  `withDiscriminator("type")`.
- **`expected key: "type"`** - the discriminator must be the first key by default; use
  `withRequireDiscriminatorFirst(false)`.
- **`List(1)` read back for a written `[]`** - field default + `[]`; add `withEmptyCollectionsAsEmpty`.
- **`'a' parameter of 'C' should be defined as 'val' or 'var' in the primary constructor.`** - a constructor parameter
  without a public accessor; make it a `val` or `@transientField` (with a default).
- **`@named` / `@transient` from `jsoniter_scala.macros` ignored** - import Kindlings' annotations instead.
- **Untrusted input** - insert limits are off by default; set `withMapMaxInsertNumber(1024)` /
  `withSetMaxInsertNumber(1024)` or start from `jsoniterScalaDefaults`.
- **Config not applied with `derives`** - the `JsoniterConfig` must be visible at the type's definition site.
- **Ambiguous implicits** - another `JsonValueCodec[A]` (e.g. from `JsonCodecMaker.make` in scope) next to the
  Kindlings one; keep one instance per type.
- **"derived timed out after 5000ms"** - raise `jsoniterDerivation.timeout` (see `kindlings-troubleshooting`).
- **Scala 2: `HearthAssertionError: Hearth assertion failed: MIO timeout is already set`** - a `val` holding a derived
  instance has no explicit type (`val codec = KindlingsJsonValueCodec.derived[A]`) and the same file derives a type with a sealed-trait
  field: Scala 2 types the un-annotated `val` while the other derivation is running. Give such vals an explicit
  type (always do so for `implicit val`s).

## Links

- Guide: https://kindlings.readthedocs.io/en/0.4.0/jsoniter-derivation/
- Differences: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#jsoniter-derivation
- JSON AST: https://kindlings.readthedocs.io/en/0.4.0/jsoniter-json/
- OpenAPI: https://kindlings.readthedocs.io/en/0.4.0/tapir-openapi-jsoniter/
- Source: https://github.com/kubuszok/kindlings/tree/0.4.0/jsoniter-derivation/src/main
