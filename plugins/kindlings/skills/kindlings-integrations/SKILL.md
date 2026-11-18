---
name: kindlings-integrations
description: >-
  Kindlings integration modules that teach every derivation module (and optics/parser) about third-party types with
  no import - kindlings-cats-integration (NonEmptyList, NonEmptyVector, NonEmptySeq, NonEmptyLazyList,
  NonEmptyChain, Chain, NonEmptyMap, NonEmptySet, Validated, ValidatedNel, Const), kindlings-refined-integration
  (Refined[A, P], refineV validation), kindlings-iron-integration (A :| C, RefinedType, RuntimeConstraint; Scala 3
  only), kindlings-neotype-integration (neotype Newtype/Subtype, make validation; Scala 3 only),
  kindlings-newtype-integration (scala-newtype @newtype/@newsubtype via newtype-compat; JVM only). Covers platforms,
  validation on decode, tapir validators via tapir-refined/tapir-iron/neotype-tapir, and what is not supported. Use
  when fields use these types, on "was not handled by any ... derivation rule" for refined/iron/neotype types, or
  when replacing circe-refined, pureconfig-cats, avro4s-refined and similar per-library modules.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings integration modules

Integration jars register Hearth providers (`IsCollection`, `IsMap`, `IsEither`, `IsValueType`) that every Kindlings
derivation discovers at compile time through a service loader. Add the dependency - **no import, no implicit, no
config**. One integration jar replaces the per-library modules (`circe-refined`, `pureconfig-cats`, `avro4s-refined`,
`iron-circe`, ...) for all Kindlings modules at once.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/> (pages `cats-integration`, `refined-integration`, `iron-integration`,
`neotype-integration`, `newtype-integration`).

## Modules and platforms

| Artifact | Handles | Scala | Platforms | Also add |
|---|---|---|---|---|
| `kindlings-cats-integration` | cats data types (below) | 2.13, 3 | JVM, JS, Native | `cats-core` (transitive) |
| `kindlings-refined-integration` | `Refined[A, P]` (`A Refined P`) | 2.13, 3 | JVM, JS, Native | `eu.timepit::refined` |
| `kindlings-iron-integration` | Iron `A :| C`, `RefinedType` / `RefinedSubtype` companions' `T` | **3 only** | JVM, JS, Native | `io.github.iltotore::iron` |
| `kindlings-neotype-integration` | neotype `Newtype[A]` / `Subtype[A]` (`Foo.Type`) | **3 only** | JVM, JS, Native | `io.github.kitlangton::neotype` |
| `kindlings-newtype-integration` | scala-newtype `@newtype` / `@newsubtype` | 2.13, 3 | **JVM only** | expansion of `@newtype` (below) |

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-refined-integration" % "0.4.0"  // %% for JVM-only builds
libraryDependencies += "eu.timepit"   %%% "refined"                       % "0.11.4" // 0.4.0 is built against 0.11.4
```

```scala
//> using dep com.kubuszok::kindlings-iron-integration:0.4.0
```

Versions Kindlings 0.4.0 was built against: cats 2.13.0, refined 0.11.4, Iron 3.3.2, neotype 0.7.2, newtype-compat
0.1.1.

## What each one does

**Encoding unwraps, decoding validates.** Wrapper types are encoded with the underlying type's instance; decoding
decodes the underlying value and then runs the library's own validation, turning a failure into a decoding error of
the format (circe `DecodingFailure`, jsoniter `JsonReaderException`, pureconfig failure, ...).

| Type | Decoding | Needs in scope |
|---|---|---|
| `Refined[A, P]` | `refineV[P]` | `Validate[A, P]` (refined provides it for standard predicates) |
| `A :| C` | Iron `RuntimeConstraint[A, C]` | `RuntimeConstraint` (Iron provides it for standard constraints) |
| `Key.T` with `object Key extends RefinedType[A, C]` / `RefinedSubtype[A, C]` | companion's `either` | - |
| neotype `Email.Type` (`object Email extends Newtype[String]` / `Subtype`) | companion's `make` (runs `validate`; error is the `String` it returned or `"Validation Failed"`) | - |
| scala-newtype `UserId` (`@newtype case class UserId(value: Int)`), also type-parameterized | none - zero-cost wrap, never fails | - |

cats-integration:

| Type | Encoded as | Decoding |
|---|---|---|
| `NonEmptyList`, `NonEmptyVector`, `NonEmptySeq`, `NonEmptyLazyList`, `NonEmptyChain` | array / sequence | must be non-empty |
| `Chain` | array | - |
| `NonEmptyMap[K, V]` | like `Map` (object, or array of pairs) | non-empty; needs `Order[K]` |
| `NonEmptySet[A]` | array | non-empty; needs `Order[A]` |
| `Validated[E, A]`, `ValidatedNel[E, A]` | as an either-like type (circe example output: `{"Valid":{"a":"alice"}}`) | - |
| `Const[A, B]` | unwrapped to `A` | - |

They compose: `NonEmptyList[Int Refined Positive]` works with both jars present. The same providers power
`kindlings-optics` `.each` (e.g. over `NonEmptyList`) and `kindlings-parser` `.as[...]` collection building.

```scala
import hearth.kindlings.circederivation._
import io.circe.{Decoder, Encoder}
import eu.timepit.refined.api.Refined
import eu.timepit.refined.numeric.Positive
import cats.data.NonEmptyList

case class Order(quantity: Int Refined Positive, items: NonEmptyList[String])
object Order {
  implicit val enc: Encoder[Order] = KindlingsEncoder.derived[Order]
  implicit val dec: Decoder[Order] = KindlingsDecoder.derived[Order] // {"quantity":0,...} or "items":[] -> Left
}
```

## scala-newtype setup

The integration brings `com.kubuszok::newtype-compat` (and `io.estatico:newtype`), but `@newtype` must still be
expanded by your build:

```scala
scalacOptions ++= (if (scalaBinaryVersion.value == "2.13") Seq("-Ymacro-annotations") else Nil)
libraryDependencies ++= (
  if (scalaBinaryVersion.value == "3")
    Seq(compilerPlugin("com.kubuszok" %% "newtype-plugin" % "0.1.1" cross CrossVersion.full))
  else Nil
)
```

## tapir schemas and validators

`kindlings-tapir-schema-derivation` gives these types the **underlying type's schema without validators**. To document
constraints as validators (`minimum`, `maxLength`, `pattern`, `minItems`...), add the tapir integration of that library
and import its schemas where the schema is derived - Kindlings uses them like any other implicit `Schema`:

| Library | Dependency | Import |
|---|---|---|
| refined | `"com.softwaremill.sttp.tapir" %% "tapir-refined"` | `import sttp.tapir.codec.refined._` |
| Iron | `"com.softwaremill.sttp.tapir" %% "tapir-iron"` | `import sttp.tapir.codec.iron.given` |
| neotype | `"io.github.kitlangton" %% "neotype-tapir"` | `import neotype.interop.tapir.given` (custom validator, not visible in OpenAPI) |
| scala-newtype | not needed (same schema as tapir-newtype) | optional `import sttp.tapir.codec.newtype._` |

Non-empty cats collections are required and get `minItems: 1` without extra imports.

## Not supported / limitations

- No integration for other wrapper libraries (e.g. monix-newtypes, zio-prelude `Newtype`, `Tagged` types): provide
  instances for those types yourself (they win over derivation), or rely on built-in support where the type is an
  `AnyVal` or a Scala 3 opaque type with a recognisable constructor.
- refined without a `Validate[A, P]` instance, or Iron without `RuntimeConstraint[A, C]`, is skipped with a reason in
  the error ("is a Refined type, but no Validate instance was found ...").
- scala-newtype carries no validation; `kindlings-newtype-integration` is JVM-only.
- Iron and neotype require Scala 3.
- `NonEmptyMap` / `NonEmptySet` need an `Order` instance for the key/element.
- Kindlings' own tapir schemas do not express constraints (see above).
- Before 0.3.2, Iron types over `String` could be mis-handled as plain `String` by pureconfig/sconfig; before 0.3.3 there
  were no neotype/newtype integrations; `NonEmptySeq` / `NonEmptyLazyList` arrived in 0.3.1.

## Gotchas

- **`The type ... was not handled by any ... derivation rule` for a refined/Iron/neotype/newtype type** - the
  integration jar is missing from the compile classpath of the module where the derivation expands. Since 0.4.0 the
  error names the module to add.
- **Works in tests but not in main (or only downstream)** - the jar was added with `% Test`, or only to a downstream
  module while instances are derived in an upstream module. It must be on the classpath where the macro runs.
- **Upstream per-library modules still present** (`circe-refined`, `io.github.iltotore::iron-circe`,
  `pureconfig-cats`...) - harmless: an implicit they provide (e.g. `Encoder[Int Refined Positive]`) is found first and
  wins over the integration. Remove them for consistent behaviour, or keep them deliberately.
- **No import needed** - do not look for `hearth.kindlings.refinedintegration._` etc.; those packages contain only
  internal providers.
- **Decoding fails with a validation message** - expected: e.g. jsoniter + Iron reports a missing refined field as a
  missing required field, circe/jsoniter accept and reject the same inputs as circe-refined / neotype-circe /
  neotype-jsoniter.
