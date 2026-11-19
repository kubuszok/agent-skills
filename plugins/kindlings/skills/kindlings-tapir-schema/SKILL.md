---
name: kindlings-tapir-schema
description: >-
  Kindlings tapir Schema derivation (kindlings-tapir-schema-derivation, package
  hearth.kindlings.tapirschemaderivation) - deriving sttp.tapir.Schema with KindlingsSchema.derived[A].schema,
  derives KindlingsSchema, derivedEnumeration, PreferSchemaConfig, and how schemas follow the Kindlings circe
  Configuration or jsoniter JsoniterConfig (field names, discriminators, wrapped ADTs, required vs optional fields).
  Use when replacing tapir Schema.derived / sttp.tapir.generic.auto._ / sttp.tapir.generic.Configuration, when
  OpenAPI docs do not match the JSON codecs, on errors "No JSON library configuration found in implicit scope",
  "Multiple JSON library configurations found", "type parameter was inferred as Nothing", the old
  KindlingsSchema.derive self-reference null, tapirSchemaDerivation timeouts, or refined/iron validators missing
  from schemas.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings tapir Schema derivation

Derives tapir `Schema[A]` for case classes, sealed traits, Scala 3 enums, Java enums, named tuples, opaque types and
more, on Scala 2.13 and 3, **reading the JSON configuration of the Kindlings circe or jsoniter module** so the
documented schema matches what the codecs actually read and write.

**Version:** written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
https://kindlings.readthedocs.io/en/0.4.0/tapir-schema-derivation/ (replace `0.4.0` with the version used).

Generic topics: `kindlings-getting-started`, `kindlings-troubleshooting`, `kindlings-derivation-policy`,
`kindlings-migration`, `kindlings-integrations` (refined/iron/neotype/newtype, cats collections). JSON codec details:
`kindlings-circe`, `kindlings-jsoniter`.

## Dependency

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-tapir-schema-derivation" % "0.4.0" // JVM / JS / Native
// plus exactly the JSON module your codecs use:
libraryDependencies += "com.kubuszok" %%% "kindlings-circe-derivation" % "0.4.0"    // or
libraryDependencies += "com.kubuszok" %%% "kindlings-jsoniter-derivation" % "0.4.0"
```

`tapir-core` comes transitively. A Kindlings JSON module is **required**: the schema macro takes no configuration of
its own and fails without a circe `Configuration` or a `JsoniterConfig` in implicit scope (their companions provide
defaults, so having the module on the classpath is enough).

## Core usage

`KindlingsSchema[A]` is a wrapper, **not** a `Schema[A]`: take `.schema` to get the tapir value.

```scala
import hearth.kindlings.tapirschemaderivation._
import hearth.kindlings.circederivation._ // or jsoniterderivation._
import sttp.tapir.Schema

case class Person(name: String, age: Int, address: Address) // Address derived recursively
object Person {
  implicit val schema: Schema[Person] = KindlingsSchema.derived[Person].schema
}
```

Scala 3:

```scala
case class Person(name: String, age: Int) derives KindlingsSchema
object Person:
  given Schema[Person] = summon[KindlingsSchema[Person]].schema
// or simply: given Schema[Person] = KindlingsSchema.derived[Person].schema
```

| Method | Result |
|---|---|
| `KindlingsSchema.derived[A]` | `KindlingsSchema[A]` (implicit def / `given`); `.schema: Schema[A]` |
| `KindlingsSchema.derivedEnumeration[A]` | `KindlingsSchema[A]`: a string-enumeration schema for a sealed trait / enum whose cases are all singletons (not implicit); values are the plain case names (like tapir), not `transformConstructorNames` |

Generic types can take the schemas of their parameters as evidence (the name then includes the actual argument, e.g.
`Box[Int]`): Scala 3 `case class Box[A](value: A) derives KindlingsSchema`; Scala 2.13
`implicit def boxSchema[A: KindlingsSchema]: KindlingsSchema[Box[A]] = KindlingsSchema.derived[Box[A]]`. A `Schema[A]`
in scope works as evidence too.

Your own implicit `Schema` for any type (fields, `Option`, maps, ...) always wins. Tapir's annotations from
`sttp.tapir.Schema.annotations._` are honoured: `@description`, `@title`, `@encodedName`, `@format`, `@validate`,
`@validateEach`, `@default`, `@deprecated`, `@hidden`, `@encodedExample`, `@customise`.

## How the schema follows the JSON configuration

- Field names: circe `transformMemberNames` / `@fieldName`; jsoniter `fieldNameMapper` / `@fieldName` / `@named`.
- Sum types: discriminator field added to each subtype (`const` value) when configured; without a discriminator,
  subtypes are shown in the **wrapped** form the codecs write (`{"Circle":{...}}`; with jsoniter, case objects as
  strings unless `circeLikeObjectEncoding`). Nested sealed hierarchies are flattened to the leaves, as both codecs do
  (circe: an intermediate with a hand-written `Encoder` stays one subtype).
- circe `withoutValueClassUnwrapping`: `AnyVal` classes shown as objects. jsoniter: Java enums / `Enumeration` as
  strings (or ids), tuples as arrays (`prefixItems`), `Option[Option[A]]` as the ADT jsoniter writes.
- Required vs optional - a field is optional exactly when the decoder derived with the same config accepts it missing:

| Field | jsoniter `JsoniterConfig` | circe `Configuration` |
|---|---|---|
| `Option[A]` | optional | optional |
| has a default value | optional unless `requireDefaultFields` | optional only with `useDefaults` |
| collection / map (no default) | optional unless `requireCollectionFields` | **required** |
| non-empty collection (cats `NonEmptyList`, ...) | required (`minItems: 1`) | required (`minItems: 1`) |
| Scala 3 `T \| Null` | optional and nullable | like its type |
| anything else | required | required |

`transient*` jsoniter settings only affect writing, so they do not make fields optional.

## Both circe and jsoniter on the classpath

The macro then finds two configs and fails (`Multiple JSON library configurations found: circe, jsoniter-scala.`).
Typical cause: circe codecs plus `kindlings-tapir-openapi-jsoniter` (depends on `kindlings-jsoniter-derivation`).
The error prints both fixes verbatim (0.4.0's hint printed a non-compiling `PreferSchemaConfig[circeConfig]`). Pick
one, either globally:

```scala
scalacOptions += "-Xmacro-settings:tapirSchemaDerivation.preferConfig=circe" // or jsoniter-scala
```

or with an implicit in an enclosing object (not a class body) visible where the schema is derived:

```scala
implicit val preferCirce: PreferSchemaConfig[hearth.kindlings.circederivation.Configuration] =
  PreferSchemaConfig[hearth.kindlings.circederivation.Configuration]
// jsoniter: PreferSchemaConfig[hearth.kindlings.jsoniterderivation.JsoniterConfig]
```

## Differences from tapir's own derivation

Checked against tapir's `Schema.derived` (and tapir-cats, tapir-iron, tapir-refined, neotype-tapir, tapir-newtype) by
comparing rendered JSON Schemas on Scala 2.13 and 3. Differences:

| Topic | tapir | Kindlings |
|---|---|---|
| Optional fields | every `Option` and every collection | exactly what the decoder accepts missing (circe: collections required) |
| Naming / discriminator config | separate `sttp.tapir.generic.Configuration`, must be kept in sync by hand | read from the JSON codec config |
| Refined / Iron / neotype constraints | validators via tapir-refined / tapir-iron / neotype-tapir | the underlying type's schema; import the tapir integration (`sttp.tapir.codec.iron.given`, `sttp.tapir.codec.refined._`, `neotype.interop.tapir.given`, `sttp.tapir.codec.newtype._`) to get the same validators |
| Map keyed by a type member (`Name.Type`, Iron `Key.T`) | named after the member (`Map_Type_Int`) | named after the companion (`Map_Name_Int`) |
| Type aliases in names | alias name | dealiased (`Not[Empty]`) |
| Value classes on Scala 3, non-`String` map keys, `Char`, named tuples, opaque types | hand-written / `Schema.schemaForMap` needed | derived |
| Recursive types | `implicit lazy val` / `implicit def` workarounds | work |

Not ported: `Schema.oneOfWrapped`, the `Schema.derivedEnumeration` builder API (`.defaultStringBased`, custom encode).
`.modify(_.path)` is tapir core and works on the result as usual.

## Settings and debugging

- Settings namespace: `tapirSchemaDerivation`, e.g. `-Xmacro-settings:tapirSchemaDerivation.timeout=30s`,
  `tapirSchemaDerivation.logDerivation=true`, `tapirSchemaDerivation.preferConfig=circe`,
  `tapirSchemaDerivation.policy.*`.
- Debug one scope: `import hearth.kindlings.tapirschemaderivation.debug._`.
- Policy opt-in import: `import hearth.kindlings.tapirschemaderivation.policy.allowDerivationForTapirSchemaDerivation`.

## Gotchas

- **`derive` vs `derived` (issue #119)** - Kindlings 0.1.x had `KindlingsSchema.derive[A]` returning `Schema[A]`;
  `implicit val schema: Schema[A] = KindlingsSchema.derive[A]` picked up the implicit being defined, giving a compile
  error or a `null` schema at runtime. `derive` was removed; use `KindlingsSchema.derived[A].schema`, whose macro skips
  the type being derived during implicit search.
- **`type mismatch: KindlingsSchema[A]` where `Schema[A]` expected** - add `.schema`; `derives KindlingsSchema` alone
  does not give tapir endpoints a `Schema[A]`.
- **`KindlingsSchema.derived: type parameter was inferred as Nothing`** - write the type argument
  (`KindlingsSchema.derived[Person].schema`).
- **`No JSON library configuration found in implicit scope`** - add `kindlings-circe-derivation` or
  `kindlings-jsoniter-derivation` to the build.
- **Schema names / casing differ from the API** - the schema uses the config visible at the derivation site; derive
  schemas where the same `Configuration` / `JsoniterConfig` as the codecs is in scope.
- **Validators missing for refined/Iron types** - import the library's tapir integration where the schema is derived.
- **Collections required with circe** - correct: circe decoders reject a missing collection field. Give the field a
  default and use `withDefaults` if it should be optional.
- **`Option` field optional but not nullable, while the codec writes `"field":null`** - both codecs write `null` for
  `None` by default; jsoniter `withTransientNone`, circe a printer with `dropNullValues = true` (see `kindlings-http-api`).
- **Scala 2: `HearthAssertionError: Hearth assertion failed: MIO timeout is already set`** - a `val` holding a derived
  instance has no explicit type (`val ks = KindlingsSchema.derived[A]`) and the same file derives a type with a sealed-trait
  field: Scala 2 types the un-annotated `val` while the other derivation is running. Give such vals an explicit
  type (always do so for `implicit val`s).

## Links

- Guide: https://kindlings.readthedocs.io/en/0.4.0/tapir-schema-derivation/
- Differences: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#tapir-schema-derivation
- Source: https://github.com/kubuszok/kindlings/tree/0.4.0/tapir-schema-derivation/src/main
