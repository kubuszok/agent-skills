---
name: kindlings-migration
description: >-
  Migrating to Kindlings from circe-generic / circe-generic-extras (deriveEncoder, deriveConfiguredCodec,
  @JsonCodec, @ConfiguredJsonCodec, @JsonKey, deriveUnwrappedCodec, deriveEnumerationCodec, Scala 3
  ConfiguredCodec), jsoniter-scala JsonCodecMaker.make / CodecMakerConfig, kittens (cats.derived.semiauto, auto),
  avro4s (AvroSchema, SchemaFor, AvroOutputStream), pureconfig-generic (deriveReader, ProductHint,
  FieldCoproductHint, pureconfig.generic.auto), tapir Schema.derived / sttp.tapir.generic.auto, scala-yaml derives
  YamlCodec, scalacheck-shapeless, cats-tagless Derive / @autoFunctorK, macwire, ScalaMock and quicklens -
  dependency swap, import swap, API mapping and the behaviour/default differences that change wire formats. Also
  upgrading between Kindlings versions (0.1.x derive -> derived, 0.3.4 and 0.4.0 wire-format and
  binary-compatibility breaks, removed config overloads, YamlConfig.kindlings03Defaults). Use when replacing an
  upstream derivation library with Kindlings or bumping the Kindlings version.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Migrating to Kindlings (and between Kindlings versions)

Kindlings replaces only the **derivation** layer: keep the upstream core library and its runtime APIs (`asJson`,
`writeToString`, `ConfigSource.load`, tapir endpoints, `.show`), swap the derivation dependency, imports and the calls
that create instances.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/feature-parity/>. Per-upstream behaviour differences are in
[differences.md](differences.md); Kindlings version-to-version changes are in [upgrading.md](upgrading.md).

## Migration procedure

1. **Pin the wire format first.** Before touching the build, add golden tests (serialized samples checked into the
   repo) and round-trip tests for the types you persist or send. Defaults differ in places (see below); tests are the
   only reliable guard.
2. **Swap dependencies.** Remove the upstream *generic/macros* module, add the Kindlings module (`"com.kubuszok" %%
   "kindlings-<x>" % "0.4.0"`, `%%%` for Scala.js/Native). The upstream core comes in transitively.
3. **Swap imports.** Remove every upstream auto/semiauto import (they would otherwise be picked up for nested types or
   cause ambiguities), add `import hearth.kindlings.<x>derivation._`.
4. **Replace instance definitions.** One `implicit val` / `given` / `derives` per *root* type that reaches upstream
   APIs; delete instances that existed only to feed nested types (Kindlings derives them recursively). Keep
   hand-written leaf instances - they win over derivation.
5. **Port configuration** to the Kindlings config class / annotations, then choose explicitly between Kindlings'
   defaults and the upstream-compatible preset where one exists.
6. **Run the golden tests**, fix differences with configuration (most have an opt-in), and only then accept intended
   format changes.

## circe (circe-generic, circe-generic-extras, Scala 3 `io.circe.derivation`)

Dependency: `"io.circe" %% "circe-generic(-extras)"` -> `"com.kubuszok" %% "kindlings-circe-derivation" % "0.4.0"`.
Imports: `io.circe.generic.semiauto._` / `auto._` / `io.circe.generic.extras._` -> `hearth.kindlings.circederivation._`
(annotations: `hearth.kindlings.circederivation.annotations._`).

| Upstream | Kindlings |
|---|---|
| `deriveEncoder[A]` / `deriveDecoder[A]` / `deriveCodec[A]` | `KindlingsEncoder.derived[A]` / `KindlingsDecoder.derived[A]` / `KindlingsCodecAsObject.derived[A]` |
| `deriveConfiguredEncoder/Decoder/Codec[A]` + implicit `extras.Configuration` | the same `derived` calls + implicit `hearth.kindlings.circederivation.Configuration` |
| `Configuration.default.withSnakeCaseMemberNames.withDefaults.withDiscriminator("type").withStrictDecoding` | same builder names on Kindlings' `Configuration` (fields `transformMemberNames`, `transformConstructorNames`, `useDefaults`, `discriminator`, `strictDecoding`, plus `enumAsStrings`, `unwrapValueClasses`) |
| `Encoder.AsObject` via semiauto | `KindlingsEncoder.deriveAsObject[A]` (or `derived`, which is an `AsObject` for products/sums) |
| `deriveEnumerationCodec[A]` / Scala 3 `ConfiguredEnumCodec.derive()` | `Configuration.default.withEnumAsStrings`; Scala 3 also `KindlingsCodecAsObject.deriveEnum()` |
| `deriveUnwrappedEncoder/Decoder` | `KindlingsEncoder.deriveUnwrapped[A]` / `KindlingsDecoder.deriveUnwrapped[A]` |
| `deriveFor[A].patch` / `.incomplete` | `KindlingsDecoder.patch[A]` / `KindlingsDecoder.incomplete[F]` (`Labelled["name", T]` replaces shapeless `FieldType`) |
| `@JsonKey("x")` (Scala 2 only) | `@fieldName("x")` (both Scala versions); new: `@transientField` |
| `@JsonCodec` / `@ConfiguredJsonCodec` (Scala 2, `-Ymacro-annotations`) | `hearth.kindlings.circederivation.JsonCodec` / `ConfiguredJsonCodec` (Scala 2, `-Ymacro-annotations`); Scala 3: `derives KindlingsCodecAsObject` |
| Scala 3 `derives ConfiguredCodec` + `given Configuration` | `derives KindlingsCodecAsObject` + `given Configuration` (Kindlings' class) |
| Scala 3 `ConfiguredCodec.derive(transformMemberNames = ...)` | `KindlingsCodecAsObject.derive(transformMemberNames = ...)` (also on `KindlingsEncoder` / `KindlingsDecoder`) |
| `ExtrasDecoder` | `hearth.kindlings.circederivation.ExtrasDecoder` |

Key difference: `AnyVal` case classes are **unwrapped** by default (`UserId(5)` -> `5`); upstream Scala 2 writes
`{"value":5}` - use `Configuration.default.withoutValueClassUnwrapping` to keep it. No `Lazy` needed for recursion.
Error messages follow Scala 3 circe core wording on both Scala versions. Details: [differences.md](differences.md#circe).

## jsoniter-scala (`JsonCodecMaker.make`)

Dependency: drop `jsoniter-scala-macros`, add `kindlings-jsoniter-derivation` (brings `jsoniter-scala-core`).

| Upstream | Kindlings |
|---|---|
| `JsonCodecMaker.make[A]` | `KindlingsJsonValueCodec.derived[A]` (implicit `JsoniterConfig`, default `JsoniterConfig.default`) |
| `JsonCodecMaker.make[A](CodecMakerConfig.withX(...))` | `KindlingsJsonValueCodec.derived[A](JsoniterConfig.jsoniterScalaDefaults.withX...)` |
| `makeCirceLike`, `makeWithoutDiscriminator`, `makeOpenapiLike`, ... | `KindlingsJsonValueCodec.derived[A](JsoniterConfig.makeCirceLike)` etc. (all presets, built on upstream defaults) |
| `CodecMakerConfig.withFieldNameMapper(JsonCodecMaker.enforce_snake_case)` | `.withFieldNameMapper(JsoniterConfig.enforce_snake_case)` or `.withSnakeCaseFieldNames` |
| `.withTransientDefault(true)` (Boolean argument) | `.withTransientDefault` (no argument; turn off with named-argument `copy(transientDefault = false)`) |
| `allowRecursiveTypes = true` | not needed - recursion always allowed |
| `@named`, `@transient`, `@stringified` (`...macros` package) | `hearth.kindlings.jsoniterderivation.annotations.{named, transientField, stringified}` (also `@fieldName`) |
| key codecs | `KindlingsJsonCodec.deriveKeyCodec[A]` |

**Default differences** (Kindlings -> upstream): no discriminator (`None` vs `Some("type")`, i.e. wrapper objects),
`transientDefault/Empty/None = false` (vs `true`), `checkFieldDuplication = false` (vs `true`), map/set insert limits
`Int.MaxValue` (vs 1024). For byte-for-byte upstream output start from **`JsoniterConfig.jsoniterScalaDefaults`**.
Details: [differences.md](differences.md#jsoniter-scala).

## kittens

Dependency: `kittens` -> `kindlings-cats-derivation`. Imports: `cats.derived.*` ->
`hearth.kindlings.catsderivation.extensions._` (adds `.derived` to the cats companions).

| kittens | Kindlings |
|---|---|
| `cats.derived.semiauto.show[A]`, `.eq`, `.order`, `.functor[F]`, ... | `Show.derived[A]`, `Eq.derived[A]`, `Order.derived[A]`, `Functor.derived[F]`, ... |
| Scala 3 `derives Show, Eq` with `import cats.derived.*` | `derives Show, Eq` with `import hearth.kindlings.catsderivation.extensions.*` (or explicit `given`) |
| `import cats.derived.auto.show._` | `import hearth.kindlings.catsderivation.auto.show._` (Scala 3: `auto.show.given`); Scala 2 has `show, eq, order, partialOrder, hash, semigroup, monoid, empty`, Scala 3 also `functor, contravariant, foldable, traverse` |
| `cats.derived.ShowPretty` | `hearth.kindlings.catsderivation.ShowPretty` |

Differences: zero-field types render as `Name()` in `Show`; `ConsK` for list-like sealed traits is not supported; a
wrapped field whose type constructor is another case class (e.g. `middle: Nel[A]`) needs that instance in scope. See
the `kindlings-cats` skill and [differences.md](differences.md#kittens).

## avro4s

Dependency: `avro4s-core` -> `kindlings-avro-derivation` (JVM only). Import `hearth.kindlings.avroderivation._`.

| avro4s | Kindlings |
|---|---|
| `AvroSchema[A]` | `AvroSchemaFor.schemaOf[A]` |
| `SchemaFor[A]` / `Encoder[A]` / `Decoder[A]` | `AvroSchemaFor.derived[A]` / `AvroEncoder.derived[A]` / `AvroDecoder.derived[A]` (encoders/decoders also carry the schema) |
| `AvroOutputStream.binary` / `AvroInputStream.binary`, JSON streams | `AvroIO.toBinary(value)` / `AvroIO.fromBinary[A](bytes)`, `AvroIO.toJson` / `AvroIO.fromJson[A]` |
| `@AvroName`, `@AvroNamespace`, `@AvroDoc`, `@AvroAlias`, `@AvroProp`, `@AvroFixed`, `@AvroTransient`, `@AvroNoDefault`, `@AvroErasedName`, `@AvroEnumDefault`, `@AvroError` | lower-case `@avroName`, `@avroNamespace`, ... in `hearth.kindlings.avroderivation.annotations` (`@transientField` for transient, `@fieldName` also renames) |
| `@AvroSortPriority(1.0f)` | `@avroSortPriority(1)` (`Int`) |
| `ScalePrecision` / `@AvroScalePrecision(scale, precision)` | `AvroConfig.withDecimalConfig(precision, scale)` / `@avroScalePrecision(precision, scale)` - note the argument order |
| `FieldMapper(SnakeCase)` | `AvroConfig.default.withSnakeCaseFieldNames` |

Defaults differ: `BigDecimal` is a STRING (avro4s: `decimal(8, 2)` bytes) and `OffsetDateTime` a `timestamp-millis`
long (avro4s: ISO string) - **`AvroConfig.avro4sDefaults`** restores avro4s' behaviour. Tuple record names include type
arguments. Details: [differences.md](differences.md#avro4s).

## pureconfig (pureconfig-generic / pureconfig-generic-scala3)

Dependency: drop `pureconfig-generic*` (keep `pureconfig-core`), add `kindlings-pureconfig-derivation` (JVM only).

| pureconfig | Kindlings |
|---|---|
| `deriveReader[A]` / `deriveWriter[A]` / `deriveConvert[A]`, `import pureconfig.generic.auto._`, Scala 3 `derives ConfigReader` | `KindlingsConfigReader.derived[A]` / `KindlingsConfigWriter.derived[A]` / `KindlingsConfigConvert.derived[A]`; Scala 3 `derives KindlingsConfigReader` |
| `implicit val h: ProductHint[A] = ProductHint(ConfigFieldMapping(CamelCase, SnakeCase), useDefaultArgs = ..., allowUnknownKeys = ...)` | `implicit val h: KindlingsProductHint[A] = KindlingsProductHint[A](transformMemberNames = ..., useDefaults = ..., allowUnknownKeys = ...)` |
| `FieldCoproductHint[A]("kind")` | `KindlingsCoproductHint.Field[A](fieldName = "kind")` |
| `FirstSuccessCoproductHint[A]` | `KindlingsCoproductHint.FirstSuccess[A]()` |
| custom single-key wrapping `CoproductHint` | `KindlingsCoproductHint.Wrapped[A]()` or global `PureConfig.default.withWrappedSubtypes` |
| `deriveEnumerationReader[E]` | `KindlingsConfigReader.derived[E]` with `PureConfig.default.withWrappedSubtypes` (case-object families then read strings) |
| (none) | global `implicit val c: PureConfig = PureConfig.default.withSnakeCaseMemberNames.withStrictDecoding`, `@configKey("x")`, `@transientField` |

**Upstream `ProductHint` / `CoproductHint` implicits are ignored** - convert each to `KindlingsProductHint` /
`KindlingsCoproductHint`. Defaults match upstream (kebab-case keys, `type` discriminator, defaults used, unknown keys
allowed). Keep using `pureconfig.ConfigSource`. Details: [differences.md](differences.md#pureconfig).

## tapir (`Schema.derived`, `sttp.tapir.generic.auto`)

Add `kindlings-tapir-schema-derivation`; remove `import sttp.tapir.generic.auto._`.

| tapir | Kindlings |
|---|---|
| `implicit val s: Schema[A] = Schema.derived` / `derives Schema` | `implicit val s: Schema[A] = KindlingsSchema.derived[A].schema` |
| `Schema.derivedEnumeration[E]` (case objects) | `KindlingsSchema.derivedEnumeration[E].schema` (case-object-only sealed traits) |
| `implicit val c: sttp.tapir.generic.Configuration` | not used - the schema follows the circe `Configuration` / `JsoniterConfig` in scope, so it matches the JSON codec |
| `@description`, `@encodedName`, `@validate`, ... | the same `sttp.tapir.Schema.annotations` |

Never write `implicit val s: Schema[A] = ...` with a method that returns `Schema[A]` directly from the macro (0.1.x
`derive`): the macro could pick up the val being defined (#119). Fields are required/optional according to the JSON
decoder, not tapir's "Option and collections are optional" rule. See the `kindlings-tapir-schema` skill.

## scala-yaml

`derives YamlCodec` / `YamlEncoder` / `YamlDecoder` -> `derives KindlingsYamlCodec` / `KindlingsYamlEncoder` /
`KindlingsYamlDecoder` (Scala 3), or `KindlingsYamlCodec.derived[A]` (works on Scala 2.13 too); keep `asYaml` /
`as[A]`. Since 0.4.0 the defaults match scala-yaml (untagged sealed traits, constructor defaults used). See
`kindlings-yaml`.

## scalacheck-shapeless / scalacheck-derived

Remove `import org.scalacheck.ScalacheckShapeless._` (or scalacheck-derived's imports). Use
`implicit val arb: Arbitrary[A] = DeriveArbitrary.derived[A]` (also `DeriveShrink`, `DeriveCogen`), or
`Arbitrary.derived[A]` / Scala 3 `derives Arbitrary` with `import hearth.kindlings.scalacheckderivation.extensions._`.
No `Recursive[T]` / `RecursionFallback` needed. See `kindlings-scalacheck`.

## cats-tagless

`Derive.functorK[Alg]`, `@autoFunctorK`, Scala 3 `derives FunctorK` -> `KindlingsFunctorK.derived[Alg]` (likewise
`KindlingsContravariantK`, `KindlingsInvariantK`, `KindlingsApplyK`, `KindlingsSemigroupalK`, `KindlingsInstrument`)
in a companion `implicit val`; no macro annotations, no `@experimental`. See `kindlings-cats-tagless`.

## macwire, ScalaMock, quicklens (reimplementations, not wrappers)

| Upstream | Kindlings | Notes |
|---|---|---|
| `import com.softwaremill.macwire._`; `wire`, `wireSet`, `wireList`, `wireWith`, `wireRec`, `autowire` | `import hearth.kindlings.di._` (or `DI.wire[...]`); same names; `@Module` is `hearth.kindlings.di.Module`; tagging stays `com.softwaremill.tagging._` | no request/session proxy scopes; only the closest enclosing method's parameters; local vals only on Scala 2; macwire-cats `autowire` (`Resource[IO, _]`) -> `DICats.wireResource[F, A](...)` in `kindlings-di-cats`. See `kindlings-di`. |
| ScalaMock `extends MockFactory`, `mock[T]`, `stub[T]`, `(m.f _).expects(x).returning(y)` | `import hearth.kindlings.mock._, hearth.kindlings.mock.syntax._`; `with MockSuite` + `withExpectations { ... }` or `implicit val ctx: MockContext = new MockContext` + `ctx.verifyExpectations()`; `Mock.mock[T]`, `Mock.stub[T]`, same `.expects(...).returning(...)` | no reflection/bytecode, works on JS/Native; framework-agnostic. See `kindlings-mock`. |
| `import com.softwaremill.quicklens._`; `obj.modify(_.a.b).setTo(x)`, `.each`, `.at`, `.when[T]`, `modifyAll`, `modifyLens` | `import hearth.kindlings.optics._`; the same names | use the `obj.modify(path)` extension form; product-like classes with a hand-written `copy` are not supported; `.index(-1)` is a no-op on Scala 2 (quicklens 2 throws). See `kindlings-optics`. |

## Migrating between Kindlings versions

Summary (full list in [upgrading.md](upgrading.md)):

- **0.1.x -> 0.2.0**: `derive` removed; replace `.derive[` with `.derived[` (tapir: `KindlingsSchema.derived[A].schema`).
- **0.2.x -> 0.3.x**: source compatible; new modules (di, mock, optics, cats-tagless, parser, neotype/newtype
  integrations), derivation policy (0.3.1), bug fixes (0.3.2: metaspace leak, `derives` on generic types).
- **-> 0.3.4**: binary compatible but **wire-format changes** in jsoniter, ubjson and circe (absent fields, case objects
  as strings, tuples as arrays, nested sealed hierarchies flattened, ...).
- **-> 0.4.0**: **not binary compatible** with 0.3.x (recompile everything, all Kindlings artifacts on one version,
  Hearth 0.4.5+); old-arity config constructors/`copy` removed; wire/schema changes in avro, yaml, tapir, pureconfig,
  sconfig, scalacheck, cats and Scala 2 sealed-subtype ordering.

## Gotchas

- **Ambiguous implicits or a nested type encoded "the old way"** - an upstream auto import is still in scope; remove
  it (Kindlings uses any implicit it finds for nested types).
- **`could not find implicit ... Encoder[A]` after removing `generic.auto`** - automatic derivation now only happens
  for Kindlings types; add instances for root types used with upstream APIs.
- **JSON changed after migrating from jsoniter-scala** - use `JsoniterConfig.jsoniterScalaDefaults` (or a `make*`
  preset) as the base config.
- **Avro schema changed** - `AvroConfig.avro4sDefaults`; tuple record names differ by design.
- **pureconfig hints ignored** - convert to `KindlingsProductHint` / `KindlingsCoproductHint`.
- **circe value classes changed shape** - `withoutValueClassUnwrapping`.
- **`derive(...)` on Scala 3 circe** is the named-arguments factory, not the removed 0.1.x `derive[A]`.
