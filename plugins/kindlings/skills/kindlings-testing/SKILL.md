---
name: kindlings-testing
description: >-
  Testing code that uses Kindlings-derived instances (hearth.kindlings.*): golden tests pinning wire formats (circe
  asJson.noSpaces, jsoniter writeToString, toYamlString, toXmlString, Avro schemaOf / AvroIO.toBinary /
  SchemaCompatibility, HOCON render), round-trip property tests with Arbitrary.derived / Shrink.derived in
  munit.ScalaCheckSuite or ScalaTest ScalaCheckPropertyChecks and why they legitimately fail (NaN, Option[Option],
  None vs missing, defaults, @transientField), readable failures with Diff.assertNoDiff (vs munit assertNoDiff),
  differential tests of upstream-derived (circe-generic, jsoniter-scala make) vs Kindlings codecs during a migration,
  compile-time tests with munit compileErrors / ScalaTest assertTypeError for "does not derive" and derivation-policy
  denial, hand-written implicits winning, % Test dependencies, CI derivation timeouts. Use when writing or reviewing
  tests for derived codecs or instances, or before migrating to or upgrading Kindlings.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Testing code that uses Kindlings-derived instances

What to test when codecs, generators and other instances are derived by Kindlings, and how: golden tests, round-trip
properties, readable failures, differential tests during a migration, compile-time tests, CI settings.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/latest/testing/>. Module details live in other skills: `kindlings-scalacheck`
(Arbitrary/Shrink/Cogen), `kindlings-diff` (Diff API), `kindlings-migration` (upstream differences),
`kindlings-derivation-policy`, `kindlings-troubleshooting` (timeouts, error messages).

## Dependencies

```scala
libraryDependencies ++= Seq(
  "org.scalameta" %% "munit"                           % "1.3.6" % Test,
  "org.scalameta" %% "munit-scalacheck"                % "1.3.1" % Test,
  "com.kubuszok"  %% "kindlings-scalacheck-derivation" % "0.4.0" % Test, // %%% on Scala.js / Native
  "com.kubuszok"  %% "kindlings-diff-derivation"       % "0.4.0" % Test
)
```

```scala
//> using test.dep com.kubuszok::kindlings-scalacheck-derivation:0.4.0
//> using test.dep com.kubuszok::kindlings-diff-derivation:0.4.0
```

ScalaTest instead: `org.scalatest::scalatest:3.2.19` + `org.scalatestplus::scalacheck-1-18:3.2.19.0` (works with the
ScalaCheck 1.20 that Kindlings brings). Keep scalacheck/diff derivation in `Test`. The module that derives production
instances, and its integrations (`kindlings-cats-integration`, `-refined-`, `-iron-`, ...), must be in `Compile` of the
project where the derivation expands; an integration added with `% Test` is invisible to `src/main` derivations.

## Why golden tests are mandatory with sanely-automatic derivation

A derived instance is generated from the type plus whatever is in implicit scope at the derivation site. Any of these
silently changes output without touching the codec: a new implicit `Configuration` / `JsoniterConfig` in scope, a new
instance in a companion, an integration jar on the classpath, migrating from upstream derivation (defaults differ),
upgrading Kindlings (0.3.4 and 0.4.0 changed wire formats). Verified example: adding
`implicit val config: Configuration = Configuration.default.withDiscriminator("type")` next to
`KindlingsEncoder.derived[Order]` turns `{"status":{"Suspended":{"reason":"fraud"}}}` into
`{"status":{"reason":"fraud","type":"Suspended"}}` - and round-trip tests still pass, because the decoder changes
too. Only golden tests catch this. The derivation policy controls *where* derivation happens, goldens check *what*
it produces.

## Golden tests

Pin root types that cross a process boundary, both directions (encode a fixed value; decode payloads produced by
older releases):

```scala
import hearth.kindlings.diffderivation._
import io.circe.parser.decode
import io.circe.syntax._

class OrderGoldenSuite extends munit.FunSuite {
  val order = Order(1L, List("apple"), Money(1050), None, Status.Suspended("fraud"))

  test("Order is encoded as agreed with the clients") {
    assertNoDiff( // munit's String comparison
      order.asJson.noSpaces,
      """{"id":1,"items":["apple"],"total":"10.50","note":null,"status":{"Suspended":{"reason":"fraud"}}}"""
    )
  }
  test("payloads written by the previous release still decode") {
    val stored = """{"id":1,"items":["apple"],"total":"10.50","status":{"Suspended":{"reason":"fraud"}}}"""
    Diff.assertNoDiff(decode[Order](stored).fold(throw _, identity), order)
  }
}
```

(`Order` has `implicit val encoder/decoder = KindlingsEncoder/KindlingsDecoder.derived[Order]` in its companion and a
hand-written string `Encoder[Money]`.) File-based goldens and a reusable `assertGolden` helper:
[golden-files.md](golden-files.md).

| Format | Produce the golden with |
|---|---|
| circe | `value.asJson.noSpaces` / `.spaces2` (string compare pins field order; `io.circe.Json` equality ignores object field order) |
| jsoniter | `writeToString(value)` (Kindlings defaults differ from `JsonCodecMaker.make`) |
| YAML | `KindlingsYamlEncoder.toYamlString(value)` |
| XML | `KindlingsXmlEncoder.toXmlString(value, "element")` |
| Avro | `AvroSchemaFor.schemaOf[A].toString` and `AvroIO.toBinary(value)` as hex; plus schema compatibility (below) |
| PureConfig | `ConfigWriter[A].to(value).render(ConfigRenderOptions.concise())` |
| tapir | the generated OpenAPI document |

Avro reader/writer compatibility against the previous release's schema (Apache Avro API):

```scala
import hearth.kindlings.avroderivation._
import org.apache.avro.{Schema, SchemaCompatibility}

val v1 = new Schema.Parser().parse(previousSchemaJson)
val result = SchemaCompatibility.checkReaderWriterCompatibility(AvroSchemaFor.schemaOf[ItemAdded], v1)
assertEquals(result.getType, SchemaCompatibility.SchemaCompatibilityType.COMPATIBLE, result.getDescription)
```

Maintainability: hand-built values (never ScalaCheck-generated) covering every field and every subtype, with
`None`, empty collections, defaults and odd strings; one or two values per root type; no `Map`/`Set` with more than 4
entries (hash order) - use `ListMap` or compare parsed JSON; run the same goldens on every Scala version and platform
you cross-build for; never auto-create missing golden files in CI.

## Round-trip property tests

```scala
import hearth.kindlings.diffderivation._
import hearth.kindlings.scalacheckderivation.extensions._
import io.circe.parser.decode
import io.circe.syntax._
import org.scalacheck.{Arbitrary, Gen, Prop, Shrink}

class OrderRoundTripSuite extends munit.ScalaCheckSuite {
  // hand-written generator for a type with invariants: derivation uses it for every Money field
  implicit val arbMoney: Arbitrary[Money] = Arbitrary(Gen.choose(0L, 1000000L).map(Money(_)))
  implicit val arbOrder: Arbitrary[Order] = Arbitrary.derived[Order]
  implicit val shrinkOrder: Shrink[Order] = Shrink.derived[Order] // minimal counterexamples

  property("decode(encode(order)) == order") {
    Prop.forAll { (order: Order) =>
      Diff.assertNoDiff(decode[Order](order.asJson.noSpaces).fold(throw _, identity), order)
    }
  }
}
```

munit-scalacheck accepts a `Unit`-returning property body, so assertions work inside `forAll`. Round-trips do not
replace goldens (encoder and decoder can change together). Values that legitimately do not round-trip (verified with
0.4.0):

| Case | Behaviour | Fix |
|---|---|---|
| `Double.NaN` | `NaN != NaN`; circe writes `null` and reads it back as `NaN`; jsoniter throws `illegal number: NaN` | ScalaCheck's default `Arbitrary[Double]` is finite; filter custom generators, or `Diff.approximate` / own equality |
| `Option[Option[A]]` (circe) | `Some(None)` written as `null`, read back as `None` | exclude `Some(None)`, or jsoniter `withSkipNestedOptionValues` |
| `None` vs absent field | both decode to `None` | wire choice - pin with a golden |
| jsoniter non-empty default collection | `C(xs = Nil)` for `xs: List[Int] = List(1)` -> `{"xs":[]}` -> `C(List(1))` | `JsoniterConfig...withEmptyCollectionsAsEmpty` |
| `@transientField` | not written, decoded as the default | generate only the default for it |
| unpaired surrogates in `String` | jsoniter: `illegal char sequence of surrogate pair` | default `Arbitrary[String]` never generates them; custom ones might |
| `Array` fields | case-class `==` compares arrays by reference | `Diff.assertNoDiff` compares contents |

## Readable failures with Diff

`Diff.assertNoDiff(obtained, expected)` throws `AssertionError("Values differ:\n" + plain rendering)` showing only the
changed parts (`left -> right`, unchanged nested records collapsed to `Money(...)`); `Diff.assertDiff(a, b)` throws if
identical and returns the `DiffResult`. Instances derive on demand; tweaks (`ignoreField`, `Diff.approximate`) are in
`kindlings-diff`. Example failure:

```text
Values differ:
Patch(
  nickname = None -> Some(None),
  score = NaN -> NaN,
)
```

## Differential tests during a migration

Keep the upstream derivation library as a `% Test` dependency until the migration is done and compare both on
generated values:

```scala
class DifferentialSuite extends munit.ScalaCheckSuite {
  implicit val arbMoney: Arbitrary[Money] = Arbitrary(Gen.choose(0L, 1000000L).map(Money(_)))
  implicit val arbOrder: Arbitrary[Order] = Arbitrary.derived[Order]

  val upstream: Encoder[Order] = { // local block: upstream instances must not leak into implicit scope
    import io.circe.generic.semiauto._
    implicit val status: Encoder[Status] = deriveEncoder[Status]
    deriveEncoder[Order]
  }

  property("Kindlings writes the same JSON as circe-generic") {
    Prop.forAll((order: Order) => assertEquals(order.asJson, upstream(order)))
  }
}
```

Also cross-decode (upstream output with the Kindlings decoder and vice versa). For known differences (see
`kindlings-migration` / differences.md) configure Kindlings to match (e.g. `JsoniterConfig.jsoniterScalaDefaults`,
`AvroConfig.avro4sDefaults`, `withoutValueClassUnwrapping`) or assert the exact expected difference; never skip
silently. Then delete the suite and the dependency; the goldens stay. Note: circe-generic on Scala 3 cannot derive
value classes (`Mirror.Of` missing), so differential tests of `AnyVal` fields only work on Scala 2.

## Compile-time tests

```scala
class CompileTimeSuite extends munit.FunSuite {
  test("a type with a Thread field does not get an Encoder") {
    val errors: String = compileErrors("hearth.kindlings.circederivation.KindlingsEncoder.derived[Option[Thread]]")
    val plain = errors.replaceAll("\u001b\\[[0-9;]*m", "") // only needed on 0.4.0 (ANSI codes in type names)
    assert(plain.contains("java.lang.Thread was not handled by any encoder derivation rule"), plain)
  }
  test("the hand-written Encoder[Money] wins over derivation") {
    assertEquals(Order(1L, Nil, Money(5), None, Status.Active).asJson.hcursor.get[String]("total"), Right("0.05"))
  }
}
```

Derivation policy (test sources compiled with `-Xmacro-settings:circeDerivation.policy.enabled=opt-in` and
`...policy.allowedScopes=com.acme.model`):

```scala
val errors: String = compileErrors("hearth.kindlings.circederivation.KindlingsEncoder.derived[com.acme.model.Address]")
assert(errors.contains("is enabled only in the following scopes"), errors)

assertEquals(compileErrors("""
  import hearth.kindlings.circederivation.policy._
  hearth.kindlings.circederivation.KindlingsEncoder.derived[com.acme.model.Address]
"""), "")
```

Match stable fragments only (`was not handled by any <x> derivation rule`, `is enabled only in the following
scopes`, `is globally disabled`); the full message lists every rule tried and grows between versions. ScalaTest:
`assertTypeError(code)` / `assertDoesNotCompile(code)` (no message access; `assertDoesNotCompile` also passes on a
typo, prefer `assertTypeError`).

## CI

Test sources derive a lot at once (`Arbitrary`, `Shrink`, `Diff` for the whole model, plus codecs) and CI is slower:
`Macro '...' timed out after 5000ms` on CI only -> raise the timeout for tests,
`Test / scalacOptions += "-Xmacro-settings:scalacheckDerivation.timeout=30s"` (one option per module namespace, e.g.
`diffDerivation`, `circeDerivation`). Details and the 1ms canary: `kindlings-troubleshooting`. A policy configured for
`Compile` may also apply to tests in other packages: `kindlings-derivation-policy` gotchas.

## Gotchas

- **`Found: Order, Required: String` on `assertNoDiff(a, b)`** - inside a munit suite the inherited
  `assertNoDiff(String, String)` wins even after `import Diff._`. Call `Diff.assertNoDiff(...)` qualified.
- **Error-message assertion fails although the message looks right** - 0.4.0 on Scala 2.13 (and Scala 3 with colour
  enabled) prints type names in derivation errors with ANSI codes (`java.[35mlang...`; fixed after 0.4.0). Strip
  `\u001b\[[0-9;]*m` first or match text without type names.
- **`Recursive value errors needs type` (Scala 3) / `illegal cyclic reference involving value errors` (Scala 2.13)
  from `compileErrors`** - 0.4.0 with an opt-in derivation policy: `val errors = compileErrors(...)` without a type, or
  on 2.13 any untyped `val e = X.derived[A]`, breaks the derivation (fixed after 0.4.0). On 0.4.0 write
  `val errors: String = ...`.
- **Sealed trait whose case object sits in its companion (`object St { case object On extends St }`), declared inside
  a class (suite, `.sc` script)** - Scala 3 on 0.4.0: `assertion failed: missing outer accessor in class MySuite`
  compiler crash (fixed after 0.4.0); Scala 2.13, decoders/codecs (not encoders), not fixed yet:
  `Internal error: unable to find the outer accessor symbol of class MySuite`. Move test models to the top level or a
  top-level `object`. Case classes **with default values** nested in a trait (`trait T { case class U(a: Int = 1) }`)
  hit the same kind of failure (Hearth bug, not fixed): declare them in an `object`.
- **Goldens changed after upgrading past 0.4.0 without a model change** - expected for `private val` fields (now
  encoded), Java enum order on Scala 3 (declaration order), tuples in HOCON (lists), xml annotations, avro4s-4 parity,
  tapir annotation inheritance, scalacheck sample sizes; see `kindlings-migration` (upgrading).
- **Golden passes in CI although nobody wrote it** - the helper created the missing file. Fail on missing files and
  regenerate only behind an explicit switch (`UPDATE_GOLDEN`), see [golden-files.md](golden-files.md).
- **Round-trip test fails on generated data** - check the table above before suspecting the codec; restrict the
  generator with a hand-written `Arbitrary` for that leaf type (derivation picks it up for every field).
- **Round-trip passes but clients broke** - round-trips cannot see format changes; add goldens.
- **Missing implicit `Arbitrary[X]` in `forAll`** - `Arbitrary.derived` is not implicit; define
  `implicit val arb: Arbitrary[X] = Arbitrary.derived[X]` (see `kindlings-scalacheck`).

## Links

- User guide: <https://kindlings.readthedocs.io/en/latest/testing/>
- Golden/round-trip background: FAQ "Why not separate automatic and semi-automatic derivation?"
  <https://kindlings.readthedocs.io/en/0.4.0/faq/>
- Feature parity (expected differences from upstream): <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/>
