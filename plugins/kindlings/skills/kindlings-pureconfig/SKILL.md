---
name: kindlings-pureconfig
description: >-
  Kindlings PureConfig derivation (kindlings-pureconfig-derivation, JVM-only, package
  hearth.kindlings.pureconfigderivation) - deriving pureconfig ConfigReader, ConfigWriter and ConfigConvert with
  KindlingsConfigReader.derived, KindlingsConfigWriter.derived, KindlingsConfigConvert.derived, the PureConfig
  config class (kebab-case keys, "type" discriminator, withWrappedSubtypes, withStrictDecoding, withoutUseDefaults),
  per-type KindlingsProductHint / KindlingsCoproductHint (Field, Wrapped, FirstSuccess), @configKey and
  @transientField. Use when replacing pureconfig-generic / pureconfig-generic-scala3
  (pureconfig.generic.semiauto.deriveReader, pureconfig.generic.auto._, derives ConfigReader, ProductHint,
  FieldCoproductHint, deriveEnumerationReader) with Kindlings, when ConfigSource.load fails with KeyNotFound /
  UnknownKey / UnexpectedValueForFieldCoproductHint, when hints are ignored, or on pureconfigDerivation timeouts.
  For Scala.js / Native HOCON see kindlings-sconfig.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings PureConfig derivation

Derives PureConfig `ConfigReader` / `ConfigWriter` / `ConfigConvert` for case classes, sealed traits, Scala 3 enums,
Java enums, named tuples, value classes and more, with one API on Scala 2.13 and 3. It replaces only PureConfig's
generic derivation: keep using `pureconfig.ConfigSource` and PureConfig's built-in readers (primitives, collections,
`java.time`, `FiniteDuration`, `URI`, `Path`, ...), which are found by implicit search. **JVM only** (Typesafe Config
is JVM-only); for Scala.js / Scala Native use `kindlings-sconfig`.

**Version:** written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
https://kindlings.readthedocs.io/en/0.4.0/pureconfig-derivation/ (replace `0.4.0` with the version used).

Generic topics: `kindlings-getting-started`, `kindlings-troubleshooting` (errors, timeouts, debug output),
`kindlings-derivation-policy`, `kindlings-migration`, `kindlings-integrations` (refined/iron/neotype/newtype, cats).

## Dependency

```scala
libraryDependencies += "com.kubuszok" %% "kindlings-pureconfig-derivation" % "0.4.0" // %% only: JVM
//> using dep com.kubuszok::kindlings-pureconfig-derivation:0.4.0
```

`pureconfig-core` and `pureconfig-generic-base` (failure types only, no Shapeless/Magnolia) come transitively. Remove
`pureconfig-generic` / `pureconfig-generic-scala3` and their imports.

## Core usage

```scala
import hearth.kindlings.pureconfigderivation._
import pureconfig._

case class Db(jdbcUrl: String, poolSize: Int = 10)
case class AppConfig(db: Db, tags: List[String]) // Db is derived recursively

object AppConfig {
  implicit val reader: ConfigReader[AppConfig] = KindlingsConfigReader.derived[AppConfig]
  // or both directions: implicit val convert: ConfigConvert[AppConfig] = KindlingsConfigConvert.derived[AppConfig]
}

ConfigSource.default.load[AppConfig]                                   // from application.conf
ConfigSource.string("""db { jdbc-url = "x" }, tags = [a]""").load[AppConfig]
```

Scala 3: `case class AppConfig(...) derives KindlingsConfigReader` (also `KindlingsConfigWriter`,
`KindlingsConfigConvert`), or `given ConfigReader[AppConfig] = KindlingsConfigReader.derived`.

| Method | Result |
|---|---|
| `KindlingsConfigReader.derived[A]` | `KindlingsConfigReader[A] <: pureconfig.ConfigReader[A]` |
| `KindlingsConfigWriter.derived[A]` | `KindlingsConfigWriter[A] <: pureconfig.ConfigWriter[A]` |
| `KindlingsConfigConvert.derived[A]` | `KindlingsConfigConvert[A] <: pureconfig.ConfigConvert[A]` |

All are implicit defs / `given`s taking an implicit `PureConfig` (default `PureConfig.default`). Pass one explicitly
with `derived[A](cfg)` (Scala 2) / `derived[A](using cfg)` (Scala 3). The instances are ordinary PureConfig instances:
`map`/`emap`/`contramap`/`xmap` and `ConfigSource` work unchanged.

## Configuration

Defaults match PureConfig's derivation exactly.

```scala
implicit val config: PureConfig = PureConfig.default
  .withSnakeCaseMemberNames
  .withStrictDecoding
```

| Field (default) | Builders |
|---|---|
| `transformMemberNames` (`ConfigFieldMapping(CamelCase, KebabCase)`) | `withKebabCaseMemberNames`, `withSnakeCaseMemberNames`, `withPascalCaseMemberNames`, `withScreamingSnakeCaseMemberNames`, `withCamelCaseMemberNames` (identity), `withTransformMemberNames(f)` |
| `transformConstructorNames` (`ConfigFieldMapping(PascalCase, KebabCase)`) | `withKebabCaseConstructorNames`, `withSnakeCaseConstructorNames`, `withTransformConstructorNames(f)` |
| `discriminator` (`Some("type")`) | `withDiscriminator(field)`, `withWrappedSubtypes` (= `None`, single-key objects `circle { ... }`) |
| `useDefaults` (`true`) | `withUseDefaults` / `withoutUseDefaults` |
| `allowUnknownKeys` (`true`) | `withAllowUnknownKeys` / `withStrictDecoding` |

`ConfigFieldMapping`, `CamelCase`, `KebabCase`, ... are PureConfig's own (`import pureconfig._`).

### Per-type hints

Kindlings reads its **own** hint types, looked up as implicits (companion of the type or in scope where derivation
runs); they override the global `PureConfig` for that type:

| Kindlings hint | Upstream equivalent |
|---|---|
| `KindlingsProductHint[A](transformMemberNames = .., useDefaults = .., allowUnknownKeys = ..)` | `ProductHint[A](fieldMapping, useDefaultArgs, allowUnknownKeys)` |
| `KindlingsCoproductHint.Field[A](fieldName = "type", transformConstructorNames = ..)` | `FieldCoproductHint[A]` (with `fieldValue` overridden) |
| `KindlingsCoproductHint.Wrapped[A](transformConstructorNames = ..)` | custom single-key `CoproductHint` |
| `KindlingsCoproductHint.FirstSuccess[A]()` | `FirstSuccessCoproductHint[A]` |

```scala
object Db {
  implicit val hint: KindlingsProductHint[Db] = KindlingsProductHint[Db](allowUnknownKeys = false)
}
sealed trait Level; case object Debug extends Level; case object Info extends Level
object Level {
  // declare the concrete variant as the type
  implicit val hint: KindlingsCoproductHint.Wrapped[Level] = KindlingsCoproductHint.Wrapped[Level]()
}
```

Hint parameters default to **PureConfig's defaults, not to your global `PureConfig`** - a hint that only sets
`allowUnknownKeys` also resets names to kebab-case.

Annotations (`import hearth.kindlings.pureconfigderivation.annotations._`): `@configKey("name")` renames a field or a
sealed subtype (wins over transforms and hints); `@transientField` skips a field (**must have a default**).

## Semantics (same as PureConfig's derivation)

- Every failure is reported (each failing field, then each unknown key of a strict product; each failing collection
  item / map value), with PureConfig's reasons: `KeyNotFound` (with candidate keys), `WrongType`, `UnknownKey`,
  `UnexpectedValueForFieldCoproductHint`, `NoValidCoproductOptionFound`.
- Missing `Option` field -> `None`; missing field with a default -> the default (unless `withoutUseDefaults`).
- Discriminator: the value must be an object, the subtype is read without the discriminator key; writing a subtype
  with a field named like the discriminator throws `CoproductHintException`.
- Case-object families: with the default discriminator `{ type = info }`; with `withWrappedSubtypes` /
  `KindlingsCoproductHint.Wrapped` plain strings (`level = info`), like `deriveEnumerationReader`/`Writer`.
- `FirstSuccess`: subtypes tried in alphabetical order of their names, first success wins.
- Empty `Option` fields are omitted when writing.

## Differences from PureConfig

Checked against `pureconfig.generic.semiauto` (Shapeless on 2.13, `pureconfig-generic-scala3` on 3) with equivalent
hints: **no differences** in values read, failures (reason and path) or values written. Kindlings-only additions are
opt-in or additive:

- One API on 2.13 and 3; `derives` for Reader, Writer **and** Convert on Scala 3 (upstream's native `derives` covers
  only `ConfigReader` and ignores hints); hints honoured on Scala 3.
- `withWrappedSubtypes` for families that are not all case objects, `@configKey`, `@transientField`.
- Recursive types without `Lazy`, named tuples, union types, value classes, and refined/Iron/neotype/newtype types via
  integration modules (no `pureconfig-refined` etc.).
- Not ported: arbitrary custom `ProductHint`/`CoproductHint` implementations (only the built-in hint configurations
  above), pureconfig-cats/yaml/circe adapters (use `kindlings-cats-integration`, other Kindlings modules).

## Migration quick map

| PureConfig | Kindlings |
|---|---|
| `pureconfig.generic.semiauto.deriveReader[A]` / `deriveWriter` / `deriveConvert` | `KindlingsConfigReader.derived[A]` / `KindlingsConfigWriter.derived[A]` / `KindlingsConfigConvert.derived[A]` |
| `import pureconfig.generic.auto._` | instances in companions for root types; nested types derive recursively |
| Scala 3 `derives ConfigReader` | `derives KindlingsConfigReader` |
| `implicit def hint = ProductHint[A](ConfigFieldMapping(CamelCase, SnakeCase))` | `implicit val hint: KindlingsProductHint[A] = KindlingsProductHint[A](ConfigFieldMapping(CamelCase, SnakeCase))` (or a global `PureConfig`) |
| `FieldCoproductHint[A]("kind")` | `KindlingsCoproductHint.Field[A](fieldName = "kind")` |
| `FirstSuccessCoproductHint[A]` | `KindlingsCoproductHint.FirstSuccess[A]()` |
| `deriveEnumerationReader[E]` / `Writer` | `derived` + `withWrappedSubtypes` (or `KindlingsCoproductHint.Wrapped[E]()`) |

## Settings and debugging

- Settings namespace: `pureconfigDerivation`, e.g. `-Xmacro-settings:pureconfigDerivation.timeout=30s`,
  `pureconfigDerivation.logDerivation=true`, `pureconfigDerivation.policy.*`.
- Debug one scope: `import hearth.kindlings.pureconfigderivation.debug._`.
- Policy opt-in import: `import hearth.kindlings.pureconfigderivation.policy.allowDerivationForPureconfigDerivation`.

## Gotchas

- **`ProductHint` / `FieldCoproductHint` has no effect** - Kindlings ignores upstream hint types; convert them to
  `KindlingsProductHint` / `KindlingsCoproductHint.*`.
- **`could not find implicit value for parameter reader: ConfigReader[AppConfig]` at `load[AppConfig]`** - put an
  `implicit val` (or `derives`) in the root type's companion; `ConfigReader[A]` searches do not look into
  `KindlingsConfigReader`'s companion.
- **Ambiguous implicits** - `pureconfig.generic.auto._` or an upstream `derives ConfigReader` still present; remove
  them.
- **`KeyNotFound` for a camelCase key** - keys are kebab-case by default (`jdbcUrl` -> `jdbc-url`); the failure's
  candidate keys show what was found.
- **Enum read as `{ type = info }` instead of `info`** - case-object families need `withWrappedSubtypes` /
  `KindlingsCoproductHint.Wrapped` to be strings, as upstream.
- **Coproduct hint not found** - declare it with the concrete type (`KindlingsCoproductHint.Wrapped[Level]`), not the
  sealed parent `KindlingsCoproductHint[Level]`.
- **`@transientField` compile error** - the field needs a default value.
- **Scala.js / Scala Native link errors** - this module is JVM-only; switch to `kindlings-sconfig`.
- **`class CollectionBuildException in object PureConfigDerivationUtils cannot be accessed` on 0.2.x** - bug #132,
  fixed in 0.3.0; upgrade (older third-party guides pin 0.2.0).
- **Scala 2: `HearthAssertionError: Hearth assertion failed: MIO timeout is already set`** - a `val` holding a derived
  instance has no explicit type (`val reader = KindlingsConfigReader.derived[A]`) and the same file derives a type with a sealed-trait
  field: Scala 2 types the un-annotated `val` while the other derivation is running. Give such vals an explicit
  type (always do so for `implicit val`s).

## Links

- Guide: https://kindlings.readthedocs.io/en/0.4.0/pureconfig-derivation/
- Differences: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#pureconfig-derivation
- Source: https://github.com/kubuszok/kindlings/tree/0.4.0/pureconfig-derivation/src/main
