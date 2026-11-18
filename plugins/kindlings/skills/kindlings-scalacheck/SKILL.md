---
name: kindlings-scalacheck
description: >-
  Deriving ScalaCheck Arbitrary, Cogen and Shrink with kindlings-scalacheck-derivation on Scala 2.13 and 3
  (JVM/JS/Native), replacing scalacheck-shapeless and scalacheck-derived. Covers Arbitrary.derived / Cogen.derived /
  Shrink.derived (import extensions), DeriveArbitrary / DeriveCogen / DeriveShrink, Scala 3 `derives Arbitrary,
  Shrink, Cogen`, recursive types without Recursive / RecursionFallback / Lazy, size control (Gen.resize,
  Gen.sized), functions and Gen fields, custom collections such as NonEmptyList, and Shrink behaviour
  (Shrink.shrinkAny, nested case classes not shrinking before 0.3.3). Use when code imports
  hearth.kindlings.scalacheckderivation or org.scalacheck and needs generators for case classes, sealed traits or
  enums, when migrating from org.scalacheck.ScalacheckShapeless._ or scalacheck-derived, or when generation of
  recursive types overflows the stack.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings ScalaCheck derivation (`kindlings-scalacheck-derivation`)

Compile-time derivation of `org.scalacheck.Arbitrary`, `Cogen` and `Shrink` for case classes, sealed traits, Scala 3
enums, Java enums and more, with one API on Scala 2.13 and 3. No configuration class and no annotations.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/scalacheck-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-scalacheck-derivation" % "0.4.0" % Test // %% on JVM-only builds
```

```scala
//> using test.dep com.kubuszok::kindlings-scalacheck-derivation:0.4.0
```

`org.scalacheck::scalacheck` (1.20.0 at Kindlings 0.4.0) comes in transitively; ScalaCheck's own instances (whatever
version is on the classpath) are used for primitives, `String`, `java.time.*`, durations, `UUID`, ...

## Usage

```scala
import hearth.kindlings.scalacheckderivation.extensions._   // adds `derived` to Arbitrary / Cogen / Shrink companions
import org.scalacheck.{Arbitrary, Cogen, Shrink, Prop}

case class Person(name: String, age: Int)
sealed trait Shape
case class Circle(radius: Double) extends Shape
case class Rectangle(width: Double, height: Double) extends Shape

// Scala 2.13 (also valid on Scala 3)
implicit val arbPerson: Arbitrary[Person] = Arbitrary.derived[Person]
implicit val shrinkPerson: Shrink[Person] = Shrink.derived[Person]
implicit val cogenPerson: Cogen[Person]   = Cogen.derived[Person]

// without the extensions import
import hearth.kindlings.scalacheckderivation.{DeriveArbitrary, DeriveCogen, DeriveShrink}
implicit val arbShape: Arbitrary[Shape] = DeriveArbitrary.derived[Shape]

// Scala 3 (extensions import in scope at the definition)
case class Book(title: String, pages: Int) derives Arbitrary, Shrink, Cogen

Prop.forAll((s: Shape) => true).check()
```

Derivation is recursive within one expansion: nested case classes, sealed traits, collections, maps, `Option`,
`Either`, `Try`, tuples, functions (`Function0`-`Function22`, `PartialFunction`), `Future` and `Gen` fields need no
instance in scope (e.g. a `Person => Int` field derives `Cogen[Person]` itself). Instances you provide always win.
`derived` is not implicit - there is no import-and-forget auto mode; define instances for the types used in
`forAll`.

Also supported: Scala 3 enums, Java enums, `scala.Enumeration`, value classes and opaque types (via the underlying
type), named tuples (Scala 3), refined / iron types (with the integration module), and any container with an
`IsCollection` / `IsMap` provider (e.g. cats `NonEmptyList`, `NonEmptyMap`, `Chain` with `kindlings-cats-integration`):
`Arbitrary` regenerates rejected (e.g. empty) candidates, `Shrink` never shrinks a non-empty container to an empty one.

## Recursion and size

Recursive types need no `Lazy`, `Recursive[T]` or `RecursionFallback`:

```scala
case class Tree(value: Int, children: List[Tree])
implicit val arbTree: Arbitrary[Tree] = Arbitrary.derived[Tree]
```

The size shrinks with depth, and at size 0 only sealed-trait cases that cannot recurse are generated, so generation
terminates. To bound size/depth use ScalaCheck itself: `Gen.resize(5, arbTree.arbitrary)`, `forAll(Gen.resize(...))`,
or the `minSize`/`maxSize` test parameters. Collection and string sizes stay within `Gen.size`.

## Shrink behaviour

- Case classes shrink field by field; sealed-trait values shrink only within their own subtype (like scalacheck-derived;
  scalacheck-shapeless also shrinks into other subtypes); collections use ScalaCheck's own `shrinkContainer` algorithm.
- Derivation ignores the implicits in `Shrink`'s companion that would hide structure - the catch-all no-op
  `Shrink.shrinkAny` and the generic collection / `Option` / `Either` / tuple combinators - so nested types are
  shrunk structurally. ScalaCheck's instances for primitives, `String`, durations etc. are still used.
- Opt a type out of shrinking: `implicit val noShrinkX: Shrink[X] = Shrink.shrinkAny`. Types that cannot be derived fall
  back to `Shrink.shrinkAny` (no shrinking).

## Differences from scalacheck-shapeless / scalacheck-derived

- Same API on Scala 2.13 and 3 and all platforms; no shapeless.
- Same `Cogen` seeds as ScalaCheck / upstream for products (`Cogen` of every field, then `Cogen[Unit]`); for sealed traits
  Kindlings perturbs with the subtype's `Cogen` and then its index (as scalacheck-derived; scalacheck-shapeless differs
  on Scala 2).
- At size 0 Kindlings still generates a value where scalacheck-derived may return `Gen.fail`.
- Subtype order (affects sealed-trait `Cogen` seeds): Scala 3 declaration order, Scala 2 subtypes sorted by name.
- No automatic mode (`import org.scalacheck.ScalacheckShapeless._`): call `.derived` explicitly.

Migration: drop `scalacheck-shapeless` / `scalacheck-derived` and their imports (`org.scalacheck.ScalacheckShapeless._`,
`io.github.martinhh.derived.scalacheck.given`), add `import hearth.kindlings.scalacheckderivation.extensions._`,
define `implicit val arb: Arbitrary[A] = Arbitrary.derived[A]` (or `derives Arbitrary`), remove `Recursive` /
`RecursionFallback` instances.

## Gotchas

- **Nested case classes not shrunk** (only top-level fields change): Kindlings before 0.3.3 picked ScalaCheck's no-op
  `shrinkAny` for fields without a `Shrink` in scope. Upgrade to 0.3.3+.
- **Wrong or failing values for `NonEmptyList` / cats containers** (empty `NonEmptyList`, runtime failures in
  `Shrink`/`Cogen`): fixed in 0.3.3; upgrade, and add `kindlings-cats-integration` for the cats types.
- **Ambiguous implicits**: do not keep `ScalacheckShapeless._` / scalacheck-derived auto imports next to Kindlings
  instances.
- **`value derived is not a member of object org.scalacheck.Arbitrary`**: the `extensions` import is missing (or use
  `DeriveArbitrary.derived`).
- **Sample is `None` sometimes for recursive types**: `.sample` can fail on a single draw; retry
  (`Iterator.continually(gen.sample).flatten.next()`) or use `forAll`.

## Debugging, timeouts, policy

- Settings namespace: `scalacheckDerivation`.
- Log derivations: `import hearth.kindlings.scalacheckderivation.debug._` (`logDerivationForScalaCheckDerivation`);
  project-wide: `scalacOptions += "-Xmacro-settings:scalacheckDerivation.logDerivation=true"`.
- Timeout (default 5 s): `-Xmacro-settings:scalacheckDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.scalacheckderivation.policy._`
  (`allowDerivationForScalacheckDerivation`).

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`, `kindlings-integrations` (refined / iron /
cats collections).

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/scalacheck-derivation/>
- Feature parity: <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#scalacheck-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/scalacheck-derivation/src/main>
