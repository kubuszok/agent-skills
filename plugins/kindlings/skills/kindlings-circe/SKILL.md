---
name: kindlings-circe
description: >-
  Kindlings circe derivation (kindlings-circe-derivation, package hearth.kindlings.circederivation) - deriving
  io.circe Encoder, Encoder.AsObject, Decoder and Codec.AsObject with KindlingsEncoder, KindlingsDecoder,
  KindlingsCodecAsObject (derived, deriveAsObject, deriveUnwrapped, patch, incomplete, deriveEnum, encode/decode),
  the Kindlings Configuration (withSnakeCaseMemberNames, withDiscriminator, withDefaults, withStrictDecoding,
  withEnumAsStrings, withoutValueClassUnwrapping), @fieldName/@transientField, @JsonCodec/@ConfiguredJsonCodec,
  ExtrasDecoder. Use when replacing circe-generic, circe-generic-extras, io.circe.generic.semiauto/auto,
  deriveEncoder/deriveDecoder/deriveConfiguredCodec, @JsonKey or Scala 3 ConfiguredCodec with Kindlings, when JSON
  shape differs from expectations (value classes unwrapped, wrapper objects vs discriminator, Option/null/missing
  fields, defaults), or when circeDerivation macro errors, timeouts or ambiguous implicits appear.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings circe derivation

Derives circe `Encoder` / `Encoder.AsObject` / `Decoder` / `Codec.AsObject` for case classes, sealed traits, Scala 3
enums, Java enums, named tuples, opaque types and more, with one API on Scala 2.13 and Scala 3. It replaces only the
*derivation* layer: keep using circe itself (`asJson`, `io.circe.parser.decode`, `Json`, cursors, ...).

**Version:** written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
https://kindlings.readthedocs.io/en/0.4.0/circe-derivation/ (replace `0.4.0` with the version used).

Generic topics live in sibling skills: setup and "sanely-automatic" basics in `kindlings-getting-started`, compile
errors / timeouts / debug output in `kindlings-troubleshooting`, opt-in-only derivation in `kindlings-derivation-policy`,
step-by-step upstream migration in `kindlings-migration`, refined/iron/cats collections in `kindlings-integrations`.

## Dependency

```scala
libraryDependencies += "com.kubuszok" %% "kindlings-circe-derivation" % "0.4.0"   // JVM
libraryDependencies += "com.kubuszok" %%% "kindlings-circe-derivation" % "0.4.0"  // JVM / Scala.js / Scala Native
//> using dep com.kubuszok::kindlings-circe-derivation:0.4.0
```

`circe-core` comes transitively; add `circe-parser` yourself if you parse strings. **Remove** `circe-generic` /
`circe-generic-extras` imports (`io.circe.generic.auto._`, `semiauto._`, `extras._`) from files using Kindlings.

## Core usage

```scala
import hearth.kindlings.circederivation._
import io.circe._

case class Address(street: String, city: String)
case class Person(name: String, age: Int, address: Address) // Address is derived recursively, no instance needed

object Person {
  // Scala 2.13 and 3: put instances of types used with circe APIs in the companion
  implicit val codec: Codec.AsObject[Person] = KindlingsCodecAsObject.derived[Person]
  // or separately:
  // implicit val encoder: Encoder[Person] = KindlingsEncoder.derived[Person]
  // implicit val decoder: Decoder[Person] = KindlingsDecoder.derived[Person]
}
```

Scala 3:

```scala
case class Person(name: String, age: Int) derives KindlingsCodecAsObject
// or: derives KindlingsEncoder, KindlingsDecoder
given Encoder.AsObject[Person] = KindlingsEncoder.deriveAsObject[Person]
```

| Method | Result | Notes |
|---|---|---|
| `KindlingsEncoder.derived[A]` | `KindlingsEncoder[A]` (an `Encoder.AsObject` at runtime for products/sums) | implicit def / `given` |
| `KindlingsEncoder.deriveAsObject[A]` | `Encoder.AsObject[A]` | compile error if `A` does not encode to an object |
| `KindlingsDecoder.derived[A]` | `KindlingsDecoder[A]` (also an `ExtrasDecoder[A]`) | implicit def / `given` |
| `KindlingsCodecAsObject.derived[A]` | `KindlingsCodecAsObject[A] <: Codec.AsObject[A]` | uses `deriveAsObject` for the encoder |
| `KindlingsEncoder.deriveUnwrapped[A]` / `KindlingsDecoder.deriveUnwrapped[A]` | single-field case class coded as its field | generic-extras' `deriveUnwrapped*` |
| `KindlingsDecoder.patch[A]` | `Decoder[A => A]` | absent / `null` key keeps the old value |
| `KindlingsDecoder.incomplete[(P1, ..) => C]` | `Decoder[(P1, ..) => C]` | `Labelled["field", T]` selects a field by name |
| `KindlingsEncoder.encode[A](a)` / `KindlingsDecoder.decode[A](json)` | `Json` / `Either[DecodingFailure, A]` | inline, no instance kept |
| `KindlingsCodecAsObject.deriveEnum[A]()` / `deriveEnum[A](transformConstructorNames)` (also on Encoder/Decoder) | `Codec[A]` | **Scala 3 only**; sum of singletons as strings |
| `KindlingsCodecAsObject.derive[A](transformMemberNames = .., discriminator = .., ...)` (also on Encoder/Decoder) | as `derived` | **Scala 3 only**; config as named args, like `ConfiguredCodec.derive` (`enumAsStrings` on `KindlingsCodecAsObject.derive` only after 0.4.0) |
| `@JsonCodec`, `@JsonCodec(encodeOnly = true)`, `@ConfiguredJsonCodec` | companion instances | **Scala 2 only**, needs `scalacOptions += "-Ymacro-annotations"` |

All of them take an implicit/`using` `hearth.kindlings.circederivation.Configuration` (default `Configuration.default`
from its companion). Pass one explicitly with `KindlingsEncoder.derived[A](cfg)` (Scala 2) or
`KindlingsEncoder.derived[A](using cfg)` (Scala 3).

`derived` is an implicit def / `given`, so nested types are derived inside one macro expansion and user-provided
instances (in scope or in companions) always win over built-in rules. A `derives` clause or an `implicit val` in the
companion is still the way to make an instance visible to circe APIs that ask for `Encoder[A]`/`Decoder[A]`.

A derived instance resolves its field instances once per instance (after 0.4.0 also for encoders: a user
`implicit def` field `Encoder`/`KeyEncoder` is evaluated once, not per encode); with a runtime-only `Configuration` the
transformed field/subtype names are computed once per instance. Inline `KindlingsEncoder.encode` still resolves them
on every call.

## Configuration

```scala
implicit val config: Configuration = Configuration.default
  .withSnakeCaseMemberNames
  .withDiscriminator("type")
  .withDefaults
// or with named args: Configuration(useDefaults = true, discriminator = Some("type"))
```

| Field (default) | Builders |
|---|---|
| `transformMemberNames` (`identity`) | `withSnakeCaseMemberNames`, `withKebabCaseMemberNames`, `withPascalCaseMemberNames`, `withScreamingSnakeCaseMemberNames`, `withTransformMemberNames(f)` |
| `transformConstructorNames` (`identity`) | `withSnakeCaseConstructorNames`, `withKebabCaseConstructorNames`, `withPascalCaseConstructorNames`, `withScreamingSnakeCaseConstructorNames`, `withTransformConstructorNames(f)` |
| `useDefaults` (`false`) | `withDefaults` / `withoutDefaults` |
| `discriminator` (`None` = wrapper object `{"Circle":{...}}`) | `withDiscriminator(field)` / `withoutDiscriminator` |
| `strictDecoding` (`false`) | `withStrictDecoding` / `withoutStrictDecoding` |
| `enumAsStrings` (`false`) | `withEnumAsStrings` / `withoutEnumAsStrings` |
| `unwrapValueClasses` (**`true`**) | `withValueClassUnwrapping` / `withoutValueClassUnwrapping` |

Renaming functions: `renaming.snakeCase`, `renaming.screamingSnakeCase`, `renaming.kebabCase`, `renaming.pascalCase`,
`renaming.replaceWith("Old" -> "new", ...)` (like Scala 3 core's `io.circe.derivation.renaming`).

A configuration evaluable at compile time (an inline `Configuration.default.withX` / `Configuration(...)` expression,
named arguments, and on Scala 3 also a local `val`/`given`) enables compile-time checks (e.g. `enumAsStrings` on a sum
with non-singleton cases) and removes runtime config checks. On Scala 2 a local `implicit val` is only known at runtime.

Annotations (`import hearth.kindlings.circederivation.annotations._`):

- `@fieldName("json_name")` - rename one field (replaces generic-extras' `@JsonKey`, works on Scala 3 too).
- `@transientField` - skip the field; it **must have a default value**.

## Wire format cheatsheet

| Value | Default config | `withDiscriminator("type")` |
|---|---|---|
| `Circle(1.0)` in `sealed trait Shape` | `{"Circle":{"radius":1.0}}` | `{"radius":1.0,"type":"Circle"}` (discriminator appended last) |
| case object `Red` | `{"Red":{}}` (`"Red"` with `withEnumAsStrings`) | `{"type":"Red"}` |
| `case class UserId(v: Int) extends AnyVal` | `5` | `5`; as a sum child it is written wrapped (`{"UserId":5}`), since it cannot carry the discriminator |
| same with `withoutValueClassUnwrapping` | `{"v":5}` | |
| tuple `(1, "a")` | `[1,"a"]` | |

Nested sealed hierarchies are flattened (a leaf is written under its own name), as in circe's Scala 3 derivation.

Decoding rules:

- Absent `Option[A]` field: `None` (with or without a default, whatever `A` is).
- `withDefaults`: an absent field, or a `null` the field decoder rejects, gets the Scala default; a `null` the decoder
  accepts (`None` for `Option`) is kept.
- Without `withDefaults`: absent non-`Option` fields fail even if they have defaults.
- Non-object JSON for a case class fails with "expecting object" (`WrongTypeExpectation`).
- `withStrictDecoding`: unknown keys fail (`Strict decoding Person - unexpected fields: ...`); the discriminator is an
  expected key; a wrapper object with more than one key fails.
- `decodeAccumulating` accumulates errors inside nested types, collections and maps.
- Error messages use circe's Scala 3 wording on both Scala versions.

Map keys: a `KeyEncoder`/`KeyDecoder` in scope wins; otherwise primitives, value classes and enums (constructor name
with `transformConstructorNames`) work automatically.

## Differences from upstream circe

Behaviour is checked against circe-generic, circe-generic-extras and circe's Scala 3 `ConfiguredCodec`. Intentional
differences (full tables: [upstream-differences.md](upstream-differences.md)):

- **`AnyVal` case classes are unwrapped by default** (`5`, upstream `{"value":5}`). Use
  `withoutValueClassUnwrapping` for byte-compatible JSON with circe-generic(-extras).
- Scala 2 behaves like circe's **Scala 3** core: error wording, the choice of key in a wrapper object with extra keys
  (first known constructor in JSON order), strict decoding of wrapper objects, hand-written intermediate instances of
  nested hierarchies are used (generic-extras ignored them).
- A sum child that is not a JSON object is written wrapped with a discriminator and Kindlings also reads it back.
- `enumAsStrings` works for full enums on Scala 2 and 3 through one flag; with a runtime-only config, a non-singleton
  case fails at runtime (`DecodingFailure` / `IllegalArgumentException`) instead of at compile time.
- Extras: recursive types without `Lazy`, Java enums, named tuples, opaque types, automatic enum/value-class map keys,
  `@fieldName` on Scala 3.

## Migration quick map

| Upstream | Kindlings |
|---|---|
| `io.circe.generic.semiauto.deriveEncoder/deriveDecoder/deriveCodec` | `KindlingsEncoder.derived` / `KindlingsDecoder.derived` / `KindlingsCodecAsObject.derived` |
| `deriveEncoder` typed as `Encoder.AsObject[A]` | `KindlingsEncoder.deriveAsObject[A]` |
| `io.circe.generic.auto._` | instances in companions (or `derives`); nested types are derived recursively |
| generic-extras `Configuration.default.withSnakeCaseMemberNames...` | same builder names on `hearth.kindlings.circederivation.Configuration` |
| `deriveConfiguredEncoder/Decoder/Codec` | `KindlingsEncoder/KindlingsDecoder/KindlingsCodecAsObject.derived` with an implicit Kindlings `Configuration` |
| `deriveEnumerationCodec` | `derived` with `withEnumAsStrings` (Scala 3: also `KindlingsCodecAsObject.deriveEnum[A]()`) |
| `deriveUnwrappedCodec` | `Codec.from(KindlingsDecoder.deriveUnwrapped[A], KindlingsEncoder.deriveUnwrapped[A])` |
| `deriveExtrasCodec` / `ExtrasDecoder` | `KindlingsDecoder` / `KindlingsCodecAsObject` implement `hearth.kindlings.circederivation.ExtrasDecoder` (`isStrict`, `decodeStrict`) |
| `deriveFor[A].patch`, `deriveConfiguredFor[A].patch` | `KindlingsDecoder.patch[A]` |
| `deriveFor[F].incomplete` (shapeless `FieldType`) | `KindlingsDecoder.incomplete[F]` (`Labelled["name", T]`) |
| `@JsonKey("x")` | `@fieldName("x")` |
| `@JsonCodec` / `@ConfiguredJsonCodec` (Scala 2) | `hearth.kindlings.circederivation.JsonCodec` / `ConfiguredJsonCodec` (Scala 2), `derives` on Scala 3 |
| Scala 3 `derives Codec.AsObject` / `ConfiguredCodec` + `given io.circe.derivation.Configuration` | `derives KindlingsCodecAsObject` + `given hearth.kindlings.circederivation.Configuration` |

Wire-format checklist when migrating: value classes (see above), and Kindlings' Scala 2 output following circe's
Scala 3 rules. Add golden (round-trip + fixed JSON) tests for every type on the wire.

## Settings and debugging

- Settings namespace: `circeDerivation`, e.g. `scalacOptions += "-Xmacro-settings:circeDerivation.timeout=30s"`,
  `-Xmacro-settings:circeDerivation.logDerivation=true`, `circeDerivation.policy.*` (see `kindlings-derivation-policy`).
- Debug one scope: `import hearth.kindlings.circederivation.debug._` (or only `logDerivationForKindlingsEncoder` /
  `logDerivationForKindlingsDecoder`).
- Policy opt-in import: `import hearth.kindlings.circederivation.policy.allowDerivationForCirceDerivation`.

## Gotchas

- **Ambiguous implicit values / wrong instance picked** - `io.circe.generic.auto._` (or a circe `derives Codec`) is
  still in scope next to Kindlings. Remove the upstream derivation imports; keep one derivation per type.
- **`reference to Configuration is ambiguous`** - both `io.circe.derivation._` / `io.circe.generic.extras._` and
  `hearth.kindlings.circederivation._` are wildcard-imported. Drop the upstream import or import Kindlings' class by name.
- **Config silently ignored** - the implicit `Configuration` must be visible where `derived` expands; for Scala 3
  `derives` that is the type's definition site (a `given` imported there or defined in an enclosing scope). Otherwise
  `Configuration.default` from the companion is used. A circe `io.circe.derivation.Configuration` is not read.
- **JSON is `5` where `{"value":5}` was expected** - value classes are unwrapped by default; use
  `withoutValueClassUnwrapping`.
- **`derives KindlingsCodecAsObject` / `deriveAsObject` fails for a value class, tuple or `enumAsStrings` enum** - the
  type does not encode to an object; use `derives KindlingsEncoder, KindlingsDecoder` (or `deriveEnum` on Scala 3).
- **`implicit val e: Encoder.AsObject[A] = KindlingsEncoder.derived[A]` does not type-check** - `derived`'s static
  type is `KindlingsEncoder[A]`; use `deriveAsObject`.
- **`@transientField` compile error** - the field has no default value.
- **Missing field with a default still fails** - `useDefaults` is off by default (as in circe); add `withDefaults`.
- **`@JsonCodec` "enable macro annotations (-Ymacro-annotations)"** - add the flag on Scala 2.13; on Scala 3 use
  `derives`.
- **Case class with several parameter lists** - rejected at compile time (as circe does).
- **Generic types on Scala 3**: `case class Box[A](a: A) derives KindlingsEncoder` asks for `KindlingsEncoder[A]` for
  each type argument; built-in types are handled (fixed bug #206 encoded `String` as an array of chars in older
  versions). To reuse plain circe instances for `A`, write
  `given [A: Encoder]: Encoder[Box[A]] = KindlingsEncoder.derived[Box[A]]` in `Box`'s companion.
- **"derived timed out after 5000ms" on CI** - raise `circeDerivation.timeout` (see `kindlings-troubleshooting`).
- **Scala 2: `HearthAssertionError: Hearth assertion failed: MIO timeout is already set`** - a `val` holding a derived
  instance has no explicit type (`val enc = KindlingsEncoder.derived[A]`) and the same file derives a type with a sealed-trait
  field: Scala 2 types the un-annotated `val` while the other derivation is running. Give such vals an explicit
  type (always do so for `implicit val`s).

## Links

- Guide: https://kindlings.readthedocs.io/en/0.4.0/circe-derivation/
- Differences: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#circe-derivation
- Source: https://github.com/kubuszok/kindlings/tree/0.4.0/circe-derivation/src/main
