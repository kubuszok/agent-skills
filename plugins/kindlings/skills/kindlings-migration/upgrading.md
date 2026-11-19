# Upgrading between Kindlings versions

Condensed from the GitHub release notes (<https://github.com/kubuszok/kindlings/releases>). Always keep every
`kindlings-*` artifact on the same version, and recompile everything that expanded Kindlings macros.

## 0.1.x -> 0.2.0 (source-breaking)

- `derive` removed from every module; only `derived` remains. Find-and-replace `.derive[` -> `.derived[`.
  - 0.1.x `derive` returned the *upstream* type (e.g. `Encoder[A]`) and was not implicit; `derived` returns the
    Kindlings type and is an implicit def / inline given. Annotate vals with the upstream type if needed.
  - tapir: `implicit val s: Schema[A] = KindlingsSchema.derived[A].schema` (the old `derive[A]` could pick up the val
    being defined -> compile error or runtime `null`, issue #119).
- Fixed: circe absent `Option[A]` field with a derived `A` (#120); single-element named tuples (#115).
- 0.1.1 already removed the `Extension ... was already loaded` warning spam (#65).

## 0.2.x -> 0.3.0 / 0.3.1 / 0.3.2 / 0.3.3 (source compatible)

- 0.3.0: new modules `kindlings-di`, `-di-cats`, `-mock`, `-optics`, `-cats-tagless-derivation`,
  `-tapir-openapi-jsoniter`; pureconfig "`CollectionBuildException ... cannot be accessed`" fixed (#132).
- 0.3.1: derivation policy (`<ns>.policy.*`, see `kindlings-derivation-policy`), `logGeneration` for di/mock/optics,
  cats `NonEmptySeq` / `NonEmptyLazyList` support.
- 0.3.2: sbt metaspace leak fixed (Hearth 0.4.2, #199); built-in type rules so `derives` on generic types no longer
  encodes `String` as a char array (#206); Scala 3 enum "unchecked type test" warnings in cats Eq/Order and Diff
  fixed (#184); jsoniter/ubjson singleton enum cases decode in wrapper/discriminator modes (#196). Iron types no longer
  match the `String` built-in rule in pureconfig/sconfig.
- 0.3.3: `kindlings-parser` (+ cats-effect, fs2), neotype and scala-newtype integrations.

## -> 0.3.4 (binary compatible with 0.3.2, but wire formats change)

Code compiled against 0.3.x keeps linking but keeps the old behaviour until recompiled.

jsoniter-derivation (and ubjson-derivation analogously):

- absent fields decode like jsoniter-scala: default value, `None`, empty collection, or
  `missing required field "<name>"` (before: `null`/`0`, missing required fields accepted, #264);
- without a discriminator case objects / parameterless enum cases are written as `"Leaf"` (was `{"Leaf":{}}`, still
  readable; `withCirceLikeObjectEncoding` writes the old form);
- tuples are arrays `[a,b]` (were `{"_1":..,"_2":..}`); Java enums / `Enumeration` always strings (or ids);
- `Some(None)` of `Option[Option[A]]` no longer written as `null` unless `skipNestedOptionValues`;
- `adtLeafClassNameMapper` receives fully-qualified names - wrap custom mappers as
  `JsoniterConfig.simpleClassName.andThen(...)`; name helpers follow upstream (`HTTPServer` -> `http_server`);
- `transient*` flags affect only encoding; `isStringified` no longer applies to case-class fields;
- `setMaxInsertNumber` limits only sets; `BigDecimal` rounded to `bigDecimalPrecision` instead of rejected;
- user-provided key/field/leaf codecs take precedence over built-ins; error messages use upstream wording;
  `require*` failures are `JsonReaderException`;
- new compile errors: contradictory flags, key/discriminator collisions, unsupported map keys with a compile-time config.

circe-derivation:

- nested sealed hierarchies are flattened: `{"Child":{..}}` / `"type":"Child"` (the old `{"Parent":{"Child":..}}` is no
  longer read); discriminator written last; tuples as arrays;
- discriminator + non-object child written as `{"Name": value}` (was `{"type":..,"value":..}`);
- product decoders reject non-object JSON (#235); case objects check their input;
- `KindlingsDecoder.patch` became a macro with circe semantics (no deep merge); new `Configuration.unwrapValueClasses`
  (default `true`); decoders extend `ExtrasDecoder`; enum map keys use the constructor name;
- new compile errors: `deriveAsObject` on non-object types, several parameter lists, `enumAsStrings` on non-singleton
  sums.

tapir-schema-derivation: schemas follow the circe/jsoniter config (wrapped/flattened ADTs, string enums, tuples as
arrays...); `SName.typeParameterShortNames` contains fully-qualified names (OpenAPI component names change).

## 0.3.x -> 0.4.0 (NOT binary compatible)

Build:

- recompile everything that expanded Kindlings 0.3.x macros (removed `internal.runtime` helpers);
- requires Hearth 0.4.5+;
- removed: old-arity constructors / `apply` / `copy` of circe `Configuration`, `JsoniterConfig`, `UBJsonConfig`,
  `AvroConfig`, `YamlConfig` (use named arguments or `with*` builders); `UBJsonConfig.unapply` (Scala 2); `JsoniterConfig`
  / `UBJsonConfig` `snakeCase` / `kebabCase` / `pascalCase` (use `enforce_snake_case`, `` `enforce-kebab-case` ``,
  `EnforcePascalCase`); the 0.3.x deep-merge `KindlingsDecoder.patch[A](implicit Decoder[A], Encoder[A])`.

All modules - sealed subtype order: Scala 2 always by name, Scala 3 always declaration order (also for types from other
modules). Affects Avro ENUM/UNION order, generators, `Order` across subtypes, untagged YAML decoding order, error texts.

avro-derivation:

- Scala default values become schema defaults (union default branch moves first) - `withoutScalaDefaultsInSchema` for
  the old schemas;
- `LocalDateTime` is `timestamp-nanos` (was millis) - `withLocalDateTimePrecision(TimestampPrecision.Millis)`;
- generic record names use one `_` between type arguments (`Pair__String_Int`, was `Pair__String__Int`);
- UNION members ordered by `@avroSortPriority` then full name; `@avroFixed` / case objects in unions get namespaces;
  `Enumeration` ENUMs named after the enumeration object;
- decoders reject `null`/missing primitives without defaults (were `0`/`false`); fields with defaults fall back to the
  default; integral widening as avro4s.
- Known regression: `AvroDecoder` for 88+ defaulted fields hits "Method too large" (#308, fixed after 0.4.0).

yaml-derivation: scala-yaml defaults - constructor defaults used for absent fields, sealed traits **untagged**
(`radius: 1.0` instead of `Circle: { radius: 1.0 }`), absent `Option` -> `None`, scala-yaml error messages. Old
behaviour: `YamlConfig.kindlings03Defaults` (or `.withWrappedSubtypes` / `.withoutUseDefaults`). A positional
5-argument `YamlConfig(...)` call now gets the new defaults.

tapir-schema-derivation (OpenAPI output changes): optional exactly when the decoder accepts the field missing (circe:
collections required); non-empty collections required with `minItems: 1`; discriminator `const` on the field's
schema; case objects named after the object; map schemas `Map_V` / `Map_K_V`; type-member types (Iron `RefinedType`,
neotype, newtype) named after the companion.

pureconfig-derivation / sconfig-derivation: all failures reported (not only the first), upstream failure types
(`KeyNotFound` with candidates; sconfig: `ConfigDecodingError.KeyNotFound` instead of `Missing`), with a discriminator
the value must be an object (no bare strings for case objects), without one case-object families read only strings,
empty `Option` omitted when writing, `FirstSuccess` hints really try subtypes. New dependency `pureconfig-generic-base`.

jsoniter / ubjson: with `withRequireDefaultFields`, `null` / `[]` / `{}` no longer decode to the default; jsoniter
`withCirceLikeObjectEncoding` no longer reads case objects from strings; `mapMaxInsertNumber` checked after every insert.

jsoniter-json: max nesting depth 128 (`JsonCodec.withMaxDepth(n)`), numbers keep their original text,
`JsonNumber.fromString` accepts only JSON numbers.

cats-derivation: `PartialOrder` derived on its own (fields need `PartialOrder`; different subtypes compare as `NaN`);
`Empty` for sealed traits needs exactly one subtype forming an `Empty`; Scala 2 `Order` across subtypes by name.

cats-tagless: `SemigroupalK` / `ApplyK` combine members without `F` with their `Semigroup`.

scalacheck: `Cogen` seeds and collection `Shrink` follow ScalaCheck (fixed-seed values change); Scala 2 generator order by
name.

optics: `.at(i)` on a missing `Seq` index throws `IndexOutOfBoundsException` (was `NoSuchElementException`);
`.atOrElse(i, d)` appends `f(d)`.

diff: `prettyName` computed at runtime from the plain type name; `NameStyle.Pretty` with `ColorMode.Plain` has no escape
codes.

circe-derivation: no semantic changes beyond the Scala 2 subtype order.

## 0.4.0 -> next release (binary compatible, MiMa-checked against 0.4.0; recompile to get the changes)

Behaviour changes:

- xml: absent `Option` element/attribute -> `None` and absent collection/map element -> empty (were `MissingElement`);
  empty `String` element/attribute -> `""` (was `MissingContent`), absent `String` -> `MissingElement`; `Option`
  attributes written as the value / omitted for `None` (were `Some(v)` / `None`); `withTransientEmpty` no longer omits
  empty `String`s; with `withTransientNone` an empty `Option[String]` element decodes as `Some("")`.
- derivation policy: gates only structural derivation - collections, `Option`, `Either`, value types, tuples are never
  gated (`derived[List[User]]` at a denied site compiles when `User` has an instance).
- avro: a type in the empty package has no namespace on Scala 2 either (was `<empty>`) - schema change for such types.
- yaml: repeated key in a case-class mapping -> last value (was first); non-scalar key -> `Parameter of a class must be
  a scalar value` (was ignored).
- diff: `modifyField(name).using(d)` is applied (was ignored); `diffDerivation.logDerivation=true` is read.
- di: unused members of `DI.autowireMembersOf(module)` are not errors (only a wholly unused module is).
- fast-show-pretty: all settings under `fastShowPrettyDerivation` (`fastShowPretty.logDerivation` still accepted).
- derivation error messages contain no ANSI colour codes (Scala 2.13).
- a user `implicit def` field instance is evaluated once per derived instance, not per call (circe encoders,
  pureconfig, sconfig, avro, yaml, cats; scalacheck: once when the generator is built); runtime-config
  `fieldNameMapper` (jsoniter, ubjson) and subtype-name mappers (circe, sconfig, yaml) run once per instance.

Fixed: avro "Method too large" (#308); scalacheck `ClassCastException` for `Either` smart-constructor value types; cats
`Functor` for recursive case classes, `ConsK` `ClassCastException`; circe `KindlingsCodecAsObject.derive(enumAsStrings
= ...)` (Scala 3); untyped `val x = X.derived[A]` under an opt-in policy; tapir `PreferSchemaConfig` hint compiles.
New: `hearth.kindlings.parser.MachineStatus`; `kindlings-di-cats` for Scala Native.
