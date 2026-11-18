---
name: kindlings-getting-started
description: >-
  Entry point for Kindlings (com.kubuszok kindlings-* artifacts, packages hearth.kindlings.*), Hearth-based
  sanely-automatic type class derivation for Scala 2.13 and 3 that replaces circe-generic(-extras), jsoniter-scala
  JsonCodecMaker.make, kittens, avro4s, pureconfig-generic, tapir Schema.derived, scala-yaml derives, cats-tagless
  macros, macwire, ScalaMock and quicklens. Covers the module table (artifact, package, type classes, platforms;
  JVM-only and Scala 3-only modules), sbt / Mill / scala-cli coordinates, the shared API shape
  (KindlingsEncoder.derived[A] as implicit def / inline given, implicit val vs given vs derives, inline
  encode/decode helpers), recursive and nested types, generic types like Box[A], never mixing with upstream
  generic-derivation imports, user-provided implicits winning, fat-JAR runtime footprint, and which kindlings-* skill to read next. Use when
  adding Kindlings to a build, picking a module, writing the first derived instance, or shrinking a fat JAR.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Getting started with Kindlings

Kindlings re-implements the *derivation layer* of popular Scala libraries with
[Hearth](https://scala-hearth.readthedocs.io/) macros: one API on Scala 2.13 and Scala 3, on JVM, Scala.js and Scala
Native. You keep using the upstream library (circe's `asJson`, jsoniter's `writeToString`, pureconfig's
`ConfigSource`, tapir endpoints...) - Kindlings only produces the instances.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/> (swap `0.4.0` for the version in use). Before 0.4.0 several wire formats
and APIs differed - see the `kindlings-migration` skill.

## Modules

All artifacts are `"com.kubuszok" %% "<artifact>" % "0.4.0"`; all packages start with `hearth.kindlings.`.

| Artifact | Package | Entry points (type classes) | Replaces | Skill |
|---|---|---|---|---|
| `kindlings-circe-derivation` | `circederivation` | `KindlingsEncoder`, `KindlingsDecoder`, `KindlingsCodecAsObject` | circe-generic, circe-generic-extras, Scala 3 `Configured*` | `kindlings-circe` |
| `kindlings-jsoniter-derivation` | `jsoniterderivation` | `KindlingsJsonValueCodec`, `KindlingsJsonCodec` | jsoniter-scala `JsonCodecMaker.make` | `kindlings-jsoniter` |
| `kindlings-tapir-schema-derivation` | `tapirschemaderivation` | `KindlingsSchema` (`.schema` gives `sttp.tapir.Schema`) | `Schema.derived`, `sttp.tapir.generic.auto` | `kindlings-tapir-schema` |
| `kindlings-pureconfig-derivation` | `pureconfigderivation` | `KindlingsConfigReader`, `KindlingsConfigWriter`, `KindlingsConfigConvert` | pureconfig-generic (**JVM only**) | `kindlings-pureconfig` |
| `kindlings-sconfig-derivation` | `sconfigderivation` | `ConfigReader`, `ConfigWriter`, `ConfigCodec` (own types, for `org.ekrich:sconfig`) | - (HOCON on JS/Native) | `kindlings-sconfig` |
| `kindlings-avro-derivation` | `avroderivation` | `AvroSchemaFor`, `AvroEncoder`, `AvroDecoder` | avro4s (**JVM only**) | `kindlings-avro` |
| `kindlings-yaml-derivation` | `yamlderivation` | `KindlingsYamlEncoder`, `KindlingsYamlDecoder`, `KindlingsYamlCodec` | scala-yaml `derives` | `kindlings-yaml` |
| `kindlings-xml-derivation` | `xmlderivation` | `KindlingsXmlEncoder`, `KindlingsXmlDecoder`, `KindlingsXmlCodec` | - (scala-xml based) | `kindlings-xml` |
| `kindlings-ubjson-derivation` | `ubjsonderivation` | `UBJsonValueCodec` | - | `kindlings-ubjson` |
| `kindlings-cats-derivation` | `catsderivation` | `Show.derived`, `Eq.derived`, `Functor.derived`, ... (extension methods) | kittens | `kindlings-cats` |
| `kindlings-cats-tagless-derivation` | `catstaglessderivation` | `KindlingsFunctorK`, `KindlingsApplyK`, `KindlingsInstrument`, ... | cats-tagless `Derive.*` | `kindlings-cats-tagless` |
| `kindlings-scalacheck-derivation` | `scalacheckderivation` | `DeriveArbitrary`, `DeriveShrink`, `DeriveCogen` | scalacheck-shapeless / scalacheck-derived | `kindlings-scalacheck` |
| `kindlings-diff-derivation` | `diffderivation` | `Diff` | - (structural diffs for tests) | `kindlings-diff` |
| `kindlings-fast-show-pretty` | `fastshowpretty` | `FastShowPretty` | - (pretty printing) | `kindlings-fast-show-pretty` |
| `kindlings-di` / `kindlings-di-cats` | `di` / `dicats` | `DI.wire`, `autowire`, `DI.plan`, `DICats.wireResource` | macwire | `kindlings-di` |
| `kindlings-mock` | `mock` | `Mock.mock`, `Mock.stub` | ScalaMock | `kindlings-mock` |
| `kindlings-optics` | `optics` | `obj.modify(_.a.b)` | quicklens | `kindlings-optics` |
| `kindlings-parser` (+ `-cats-effect`, `-fs2`) | `parser` | `Grammar.grammar` | yacc-style parsers | `kindlings-parser` |
| `kindlings-cats-integration`, `-refined-`, `-iron-`, `-neotype-`, `-newtype-integration` | - (no import) | support for cats data types, refined, Iron, neotype, scala-newtype | `circe-refined`, `pureconfig-cats`... | `kindlings-integrations` |

Extras: `kindlings-jsoniter-json` (small JSON AST + codec for jsoniter) and `kindlings-tapir-openapi-jsoniter`
(serialize tapir OpenAPI with jsoniter, JVM + Scala.js).

Platforms: everything is published for Scala 2.13 and 3 on JVM, Scala.js and Scala Native, except:

- **JVM only**: `kindlings-avro-derivation`, `kindlings-pureconfig-derivation`, `kindlings-newtype-integration`.
- **JVM + Scala.js only**: `kindlings-di-cats`, `kindlings-tapir-openapi-jsoniter`.
- **Scala 3 only**: `kindlings-iron-integration`, `kindlings-neotype-integration`.

0.4.0 is built with Scala 2.13.18 and Scala 3.8.4. Scala 3 projects need a Scala 3.8+ compiler (an older compiler
cannot read 3.8 TASTy); Scala 2 projects should be on a recent 2.13 (2.13.18+ avoids scala-library eviction
warnings/errors).

Each module depends on the upstream *core* library (e.g. `circe-core`, `jsoniter-scala-core`, `pureconfig-core`,
`tapir-core`, `cats-core`), not on its generic-derivation module. Add parsers/printers yourself (`circe-parser`...).

## Dependency coordinates

```scala
// sbt, JVM-only project
libraryDependencies += "com.kubuszok" %% "kindlings-circe-derivation" % "0.4.0"
// sbt, Scala.js / Scala Native / crossProject
libraryDependencies += "com.kubuszok" %%% "kindlings-circe-derivation" % "0.4.0"
// test-only modules: kindlings-mock always; kindlings-scalacheck-derivation and kindlings-diff-derivation
// unless production code uses them (e.g. diffs for audit logs)
libraryDependencies += "com.kubuszok" %%% "kindlings-mock" % "0.4.0" % Test
libraryDependencies += "com.kubuszok" %%% "kindlings-scalacheck-derivation" % "0.4.0" % Test
```

Depend only on the modules from the table above. `kindlings-derivation-commons`, `kindlings-macro-commons` and
`kindlings-json-schema-config-macro-providers` appear in the dependency tree but are compile-time internals - never add
them yourself. For what is needed at runtime and how to strip the macro code from a fat JAR, see
[runtime-footprint.md](runtime-footprint.md).

```scala
// Mill 1.x (Mill 0.11/0.12: `def ivyDeps = Agg(ivy"...")`); use `::0.4.0` (double colon) in Scala.js/Native modules
def mvnDeps = Seq(mvn"com.kubuszok::kindlings-circe-derivation:0.4.0")
```

```scala
//> using dep com.kubuszok::kindlings-circe-derivation:0.4.0
```

## The shared API shape

Every derivation module follows the same pattern (circe shown; swap the names from the table above):

```scala
import hearth.kindlings.circederivation._   // KindlingsEncoder, KindlingsDecoder, Configuration
import io.circe.{Decoder, Encoder}
import io.circe.syntax._

case class Address(street: String, city: String)
case class Person(name: String, age: Int, addresses: List[Address])

// Scala 2.13 (also compiles on Scala 3): instances for the ROOT types used at call sites, in the companion
object Person {
  implicit val encoder: Encoder[Person] = KindlingsEncoder.derived[Person] // Address/List[Address] derived inside
  implicit val decoder: Decoder[Person] = KindlingsDecoder.derived[Person]
}

Person("Ann", 30, Nil).asJson // the upstream API, using the instance above
```

```scala
// Scala 3 alternatives
case class Person(name: String, age: Int, addresses: List[Address]) derives KindlingsEncoder, KindlingsDecoder

object Person:
  given Encoder[Person] = KindlingsEncoder.derived
```

```scala
// Inline helpers: derive + run in one expression, no instance kept (circe / jsoniter shown)
val json = KindlingsEncoder.encode(Person("Ann", 30, Nil))
val back = KindlingsDecoder.decode[Person](json)               // Either[DecodingFailure, Person]
val str  = KindlingsJsonValueCodec.writeToString(Person("Ann", 30, Nil))  // jsoniterderivation
```

Other inline helpers: `AvroEncoder.encode` / `AvroDecoder.decode` / `AvroSchemaFor.schemaOf`,
`KindlingsYamlEncoder.toYamlString` / `KindlingsYamlDecoder.fromYamlString`, `KindlingsXmlEncoder.toXmlString` /
`KindlingsXmlDecoder.fromXmlString`, `KindlingsJsonValueCodec.readFromString`.

### How "sanely-automatic" works

- `X.derived[A]` is an `implicit def` macro (Scala 2) / `inline given` (Scala 3) in the companion of the Kindlings
  type class. Calling it explicitly is "semi-automatic", but it is **recursive**: one expansion derives `A` and every
  nested case class, sealed trait, collection, `Option`, map, tuple, value class... it reaches. No `Lazy`, no
  `implicit lazy val` knot-tying for recursive types (`case class Tree(children: List[Tree])` just works).
- Automatic use costs the same as semi-automatic: when something asks for the **Kindlings** type
  (`KindlingsEncoder[A]`, `Diff[A]`, `FastShowPretty[A]`, `UBJsonValueCodec[A]`, ...), the compiler finds `derived`
  in the type class companion and expands it there. Each such call site expands separately - to derive a type once,
  keep it in an `implicit val` / `given`.
- Upstream APIs ask for the **upstream** type (`io.circe.Encoder[A]`, `JsonValueCodec[A]`, `pureconfig.ConfigReader[A]`,
  `sttp.tapir.Schema[A]`), whose implicit scope does not include the Kindlings companion. So for the root types you pass
  to upstream APIs, define an instance (companion `implicit val`, `given`, or `derives`). Nested types need nothing.
- Kindlings types extend the upstream ones (`KindlingsEncoder[A] <: Encoder[A]`, `KindlingsJsonValueCodec[A] <:
  JsonValueCodec[A]`, `KindlingsConfigReader[A] <: ConfigReader[A]`, `KindlingsYamlEncoder[A] <: YamlEncoder[A]`), so
  annotate the val with the upstream type. Exceptions: tapir (`KindlingsSchema.derived[A].schema`), and modules with
  their own type classes (Avro, sconfig, XML, UBJson, Diff, FastShowPretty).
- Not implicit: cats (`Show.derived` etc. are extension methods from `import hearth.kindlings.catsderivation.extensions._`;
  opt-in auto via `import hearth.kindlings.catsderivation.auto.show._` etc.), cats-tagless, scalacheck
  (`DeriveArbitrary.derived[A]` or `Arbitrary.derived` via `scalacheckderivation.extensions._`), and sconfig on
  Scala 2 (`ConfigReader.derived` is a plain `def` there, a `given` on Scala 3).
- Most serde `derived`/helper methods take an implicit config (`Configuration`, `JsoniterConfig`, `PureConfig`,
  `SConfig`, `AvroConfig`, `YamlConfig`, `XmlConfig`, `UBJsonConfig`); each companion has an `implicit val default`,
  so an `implicit val` / `given` of the config in scope overrides it.

### User-provided implicits always win

Before deriving any nested type, the macro searches implicit scope for an existing instance (your hand-written
`Encoder[Instant]`, a companion `implicit val`, an upstream built-in). Only when none exists does it derive. Put custom
leaf instances (`Instant`, `UUID` formats, newtypes without an integration) in the type's companion or in scope at the
derivation site. Configure per-field details with the module's annotations (e.g. `@fieldName`, `@transientField`;
circe/jsoniter/... skills list them).

### Generic types (`Box[A]`)

On Scala 3, `case class Box[A](a: A) derives KindlingsEncoder` makes the compiler require a `KindlingsEncoder[A]` for
the type parameter, so `A` is derived by Kindlings even if a hand-written `Encoder[A]` exists (before 0.3.2 this even
encoded `String` as an array of chars, issue #206). For generic types write the instance by hand with an upstream
context bound:

```scala
// Scala 3
object Box:
  given [A: Encoder]: Encoder[Box[A]] = KindlingsEncoder.derived
// Scala 2.13
object Box {
  implicit def boxEncoder[A: Encoder]: Encoder[Box[A]] = KindlingsEncoder.derived[Box[A]]
}
```

## Never mix with upstream generic derivation

Remove the upstream derivation module and its imports; keep only the core library. With both in scope you get
ambiguous implicits, or - worse - Kindlings' "use the implicit if one exists" rule silently picks upstream's
auto-derived instance for nested types, with upstream's configuration and wire format.

| Module | Remove / do not import |
|---|---|
| circe | `circe-generic`, `circe-generic-extras`; `io.circe.generic.auto._`, `io.circe.generic.semiauto._`, `io.circe.generic.extras.{auto, semiauto}._`, `@JsonCodec` / `@ConfiguredJsonCodec` from circe (Kindlings has its own); Scala 3 `derives Codec.AsObject` / `ConfiguredCodec` |
| jsoniter | `jsoniter-scala-macros` (`JsonCodecMaker.make`) for the same types |
| pureconfig | `pureconfig-generic`, `pureconfig-generic-scala3`; `pureconfig.generic.auto._`, `pureconfig.generic.semiauto._`, Scala 3 `derives ConfigReader` |
| tapir | `sttp.tapir.generic.auto._`, `Schema.derived`, `derives Schema` |
| cats | `kittens`; `cats.derived.*`, `cats.derived.auto.*`, `cats.derived.semiauto` |
| avro | `avro4s` |
| yaml | scala-yaml's own `derives YamlCodec` / `YamlEncoder` / `YamlDecoder` |
| scalacheck | `scalacheck-shapeless` (`org.scalacheck.ScalacheckShapeless._`), scalacheck-derived |
| cats-tagless | `cats.tagless.Derive.*`, `@autoFunctorK` and friends |

See `kindlings-migration` for the full mapping per upstream.

## Integrations need no import

`kindlings-cats-integration`, `kindlings-refined-integration`, `kindlings-iron-integration`,
`kindlings-neotype-integration` and `kindlings-newtype-integration` are discovered by every derivation module when the
jar is on the compile classpath - no import, no config. See `kindlings-integrations`.

## Gotchas

- **"could not find implicit value for parameter encoder: io.circe.Encoder[Person]" at `asJson`** - only
  `import hearth.kindlings.circederivation._` is not enough; upstream searches for `Encoder`, not `KindlingsEncoder`.
  Add a companion `implicit val` / `given` / `derives` for that root type.
- **`value derive is not a member`** - `derive` was removed in 0.2.0; use `derived`. (Scala 3 circe has a new
  `KindlingsEncoder.derive(transformMemberNames = ...)` with named config arguments - a different thing.)
- **Always annotate the type of vals/defs holding derived instances** (`implicit val c: JsonValueCodec[A] = ...`, not
  `implicit val c = ...`): un-annotated ones have triggered a Hearth assertion error on Scala 2.13 (see
  `kindlings-troubleshooting`) and are rejected under `-Xsource:3`.
- **Same type derived at many call sites slows compilation** - each expansion is independent; store it once in a
  companion `implicit val` / `given`.
- **Instances differ from upstream defaults** (e.g. circe value classes are unwrapped by default, jsoniter
  discriminator is `None` by default) - check `kindlings-migration` before switching a production wire format, and pin
  it with round-trip and golden tests.
- **Derivation timed out / fails on CI only** - see `kindlings-troubleshooting` (`-Xmacro-settings:<ns>.timeout=30s`).
- **Team wants explicit instances only** - see `kindlings-derivation-policy`.

## Which skill next

- A specific format/type class: `kindlings-circe`, `kindlings-jsoniter`, `kindlings-tapir-schema`,
  `kindlings-pureconfig`, `kindlings-sconfig`, `kindlings-avro`, `kindlings-yaml`, `kindlings-xml`,
  `kindlings-ubjson`, `kindlings-cats`, `kindlings-cats-tagless`, `kindlings-scalacheck`, `kindlings-diff`,
  `kindlings-fast-show-pretty`.
- Non-derivation macros: `kindlings-di`, `kindlings-mock`, `kindlings-optics`, `kindlings-parser`.
- Switching from upstream or upgrading Kindlings: `kindlings-migration`.
- Compile errors, debug logging, timeouts, settings: `kindlings-troubleshooting`.
- Restricting where derivation may happen: `kindlings-derivation-policy`.
- refined / Iron / neotype / scala-newtype / cats data types: `kindlings-integrations`.

Docs: <https://kindlings.readthedocs.io/en/0.4.0/> - FAQ: <https://kindlings.readthedocs.io/en/0.4.0/faq/> - source:
<https://github.com/kubuszok/kindlings/tree/0.4.0>.
