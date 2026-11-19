---
name: kindlings-sconfig
description: >-
  Kindlings sconfig derivation (kindlings-sconfig-derivation, package hearth.kindlings.sconfigderivation) -
  cross-platform HOCON (JVM, Scala.js, Scala Native) reading/writing on top of org.ekrich sconfig with
  Kindlings-owned ConfigReader, ConfigWriter, ConfigCodec (derived, from, to, map, emap, contramap), the SConfig
  config class, ProductHint / CoproductHint (Field, Wrapped, FirstSuccess), ConfigFieldMapping/KebabCase naming,
  @configKey/@transientField, ConfigDecodingError (KeyNotFound, WrongType, CannotConvert, UnknownKey, Multiple). Use
  when a project needs PureConfig-like typed config on Scala.js or Scala Native, when porting from
  kindlings-pureconfig or PureConfig, on "Key not found" / "Expected type OBJECT" errors, missing ConfigReader for
  Duration/UUID/java.time, Scala 2 implicit-not-found for ConfigReader, or sconfigDerivation timeouts.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings sconfig derivation (cross-platform HOCON)

Derives config readers/writers for case classes, sealed traits, Scala 3 enums, Java enums, named tuples, value
classes and collections against [sconfig](https://github.com/ekrich/sconfig) (a Scala port of Typesafe Config), so it
works on **JVM, Scala.js and Scala Native**. sconfig has no derivation of its own; this module ships its own type
classes and mirrors `kindlings-pureconfig` (same knobs, same defaults, PureConfig's semantics).

**Version:** written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
https://kindlings.readthedocs.io/en/0.4.0/sconfig-derivation/ (replace `0.4.0` with the version used).

Generic topics: `kindlings-getting-started`, `kindlings-troubleshooting`, `kindlings-derivation-policy`,
`kindlings-migration`, `kindlings-integrations`. JVM-only projects already on PureConfig: `kindlings-pureconfig`.

## Dependency

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-sconfig-derivation" % "0.4.0" // JVM / JS / Native
//> using dep com.kubuszok::kindlings-sconfig-derivation:0.4.0
```

`org.ekrich::sconfig` comes transitively (declare it to pin a version). On Scala.js / Scala Native add a `java.time`
polyfill (sconfig references `java.time.Duration`), e.g.
`libraryDependencies += "io.github.cquiroz" %%% "scala-java-time" % "<version>"`.

## Core usage

```scala
import hearth.kindlings.sconfigderivation._
import org.ekrich.config.ConfigFactory

case class Http(host: String = "0.0.0.0", port: Int)
case class AppConfig(http: Http, tags: List[String]) // Http, List derived in the same expansion

object AppConfig {
  implicit val reader: ConfigReader[AppConfig] = ConfigReader.derived[AppConfig]
  implicit val writer: ConfigWriter[AppConfig] = ConfigWriter.derived[AppConfig]
  // or both: implicit val codec: ConfigCodec[AppConfig] = ConfigCodec.derived[AppConfig]
}

val result: Either[ConfigDecodingError, AppConfig] =
  AppConfig.reader.from(ConfigFactory.parseString("http { port = 8080 }, tags = [a]").root)
val rendered: String = AppConfig.writer.to(AppConfig(Http(port = 8080), Nil)).render
```

Scala 3: `derives ConfigReader` / `ConfigWriter` / `ConfigCodec`, or `given ConfigReader[A] = ConfigReader.derived`.

| Type class (all in `hearth.kindlings.sconfigderivation`) | API |
|---|---|
| `ConfigReader[A]` | `from(value: ConfigValue): Either[ConfigDecodingError, A]`, `map`, `emap(A => Either[String, B])`; `ConfigReader[A]` summons |
| `ConfigWriter[A]` | `to(value: A): ConfigValue`, `contramap` |
| `ConfigCodec[A]` | `extends ConfigReader[A] with ConfigWriter[A]` |

`derived` takes an implicit/`using` `SConfig` (default `SConfig.default`). **On Scala 3 `derived` is a `given`; on
Scala 2 it is a plain (non-implicit) def** - always assign it to an `implicit val`.

Built-in instances (in the companions): `String`, `Boolean`, `Int`, `Long`, `Short`, `Byte`, `Float`, `Double`,
`Char`, `BigDecimal`, `BigInt`, `Option[A]`. Collections (`List`, `Vector`, `Seq`, `Set`, any `IsCollection`) and
`Map[String, A]` are synthesised by the macro inside a derivation, not provided as standalone implicits. There is **no
built-in** reader for `FiniteDuration`, `java.time`, `UUID`, `URI`, ... - define one (see Gotchas).

## Configuration

`SConfig` has the same fields, builders and defaults as `PureConfig` in `kindlings-pureconfig`:

| Field (default) | Builders |
|---|---|
| `transformMemberNames` (`ConfigFieldMapping(CamelCase, KebabCase)`) | `withKebabCaseMemberNames`, `withSnakeCaseMemberNames`, `withPascalCaseMemberNames`, `withScreamingSnakeCaseMemberNames`, `withCamelCaseMemberNames`, `withTransformMemberNames(f)` |
| `transformConstructorNames` (`ConfigFieldMapping(PascalCase, KebabCase)`) | `withKebabCaseConstructorNames`, `withSnakeCaseConstructorNames`, `withTransformConstructorNames(f)` |
| `discriminator` (`Some("type")`) | `withDiscriminator(field)`, `withWrappedSubtypes` |
| `useDefaults` (`true`) | `withUseDefaults` / `withoutUseDefaults` |
| `allowUnknownKeys` (`true`) | `withAllowUnknownKeys` / `withStrictDecoding` |

Naming conventions are the module's own (no PureConfig dependency): `CamelCase`, `PascalCase`, `KebabCase`,
`SnakeCase`, `ScreamingSnakeCase`, `ConfigFieldMapping(from, to)`, `ConfigFieldMapping(f)`,
`mapping.withOverrides("a" -> "b")`.

Per-type hints (implicits, e.g. in the type's companion; they override `SConfig` for that type):

```scala
implicit val dbHint: ProductHint[Db] =
  ProductHint[Db](transformMemberNames = ConfigFieldMapping(CamelCase, SnakeCase), allowUnknownKeys = false)
implicit val levelHint: CoproductHint.Wrapped[Level] = CoproductHint.Wrapped[Level]() // concrete variant as the type
```

`CoproductHint.Field[A](fieldName = "type", transformConstructorNames = ..)`, `CoproductHint.Wrapped[A](..)`,
`CoproductHint.FirstSuccess[A]()`. Hint parameters default to the module defaults, not to your global `SConfig`.

Annotations (`import hearth.kindlings.sconfigderivation.annotations._`): `@configKey("name")` on a field or a sealed
subtype; `@transientField` (needs a default value). Annotations win over hints and `SConfig`.

## Semantics and errors

Behaviour follows PureConfig's derivation (the module runs pureconfig-derivation's scenarios):

- every failure is collected (`ConfigDecodingError.Multiple`; `ConfigDecodingError.flatten(e)` lists them);
- missing key: `KeyNotFound(path, key, candidates)` at the object that lacks it; `Option` fields (and readers mixing
  in `ReadsMissingKeys`) read it as missing instead;
- other variants: `WrongType`, `CannotConvert`, `UnknownKey` (strict), `UnexpectedValueForFieldCoproductHint`,
  `NoValidCoproductOptionFound` (FirstSuccess); writers throw `CoproductHintException(CollidingKeys)`;
- `ConfigDecodingError` extends `Throwable`: `getMessage` gives `Key not found: 'host'. (at db)`;
- case-object families: `{ type = info }` with a discriminator, plain strings with `withWrappedSubtypes`; an unknown
  string fails with `CannotConvert` on both Scala versions;
- empty `Option` fields are omitted when writing;
- field instances are resolved once per derived reader/writer (an `implicit def` is called once per instance, as in
  PureConfig), and subtype names from `transformConstructorNames` are computed once per instance, also with a runtime
  config (after 0.4.0).

## sconfig vs pureconfig module

| | `kindlings-pureconfig` | `kindlings-sconfig` |
|---|---|---|
| Platforms | JVM | JVM, JS, Native |
| Type classes | extend `pureconfig.ConfigReader/Writer/Convert` | own `ConfigReader` / `ConfigWriter` / `ConfigCodec` |
| Derivation entry | `KindlingsConfigReader.derived` | `ConfigReader.derived` (non-implicit on Scala 2) |
| Config / hints | `PureConfig`, `KindlingsProductHint`, `KindlingsCoproductHint.*` | `SConfig`, `ProductHint`, `CoproductHint.*` |
| Built-in leaf types | all of PureConfig's | primitives, `BigDecimal`, `BigInt`, `Option` |
| Errors | `ConfigReaderFailures` | `ConfigDecodingError` |
| Loading | `ConfigSource.default.load[A]` | `reader.from(ConfigFactory.parseString(..).root)` / `config.getValue(path)` |

Porting between them: rename the type classes and config class, re-create leaf readers for non-primitive types.

## Settings and debugging

- Settings namespace: `sconfigDerivation`, e.g. `-Xmacro-settings:sconfigDerivation.timeout=30s`,
  `sconfigDerivation.logDerivation=true`, `sconfigDerivation.policy.*`.
- Debug one scope: `import hearth.kindlings.sconfigderivation.debug._`.
- Policy opt-in import: `import hearth.kindlings.sconfigderivation.policy.allowDerivationForSconfigDerivation`.

## Gotchas

- **`could not find implicit value ... ConfigReader[A]` on Scala 2** - `derived` is not implicit there; define
  `implicit val reader: ConfigReader[A] = ConfigReader.derived[A]`.
- **Derivation fails on `FiniteDuration`, `UUID`, `Instant`, ...** - not built in; provide one, e.g.
  ```scala
  implicit val fd: ConfigReader[FiniteDuration] = ConfigReader[String].emap { s =>
    scala.util.Try(Duration(s)).toOption.collect { case f: FiniteDuration => f }.toRight(s"not a duration: $s")
  }
  ```
- **`Expected type OBJECT. Found STRING instead.` for an enum** - case objects use the `type` discriminator by default;
  use `withWrappedSubtypes` or `CoproductHint.Wrapped` for plain strings.
- **`Key not found` for camelCase keys** - default naming is kebab-case.
- **Linking fails on JS/Native mentioning `java.time`** - add the `scala-java-time` polyfill.
- **Standalone `ConfigReader[List[A]]` not found** - collections are only synthesised inside a derivation; derive
  `ConfigReader.derived[List[A]]` or wrap it in a case class.
- **Scala 2: `HearthAssertionError: Hearth assertion failed: MIO timeout is already set`** - a `val` holding a derived
  instance has no explicit type (`val reader = ConfigReader.derived[A]`) and the same file derives a type with a sealed-trait
  field: Scala 2 types the un-annotated `val` while the other derivation is running. Give such vals an explicit
  type (always do so for `implicit val`s).

## Links

- Guide: https://kindlings.readthedocs.io/en/0.4.0/sconfig-derivation/
- Feature table: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#sconfig-derivation
- Source: https://github.com/kubuszok/kindlings/tree/0.4.0/sconfig-derivation/src/main
