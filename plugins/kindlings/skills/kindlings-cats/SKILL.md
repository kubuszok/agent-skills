---
name: kindlings-cats
description: >-
  Deriving Cats / cats-kernel / alleycats type classes with kindlings-cats-derivation, a kittens replacement for
  Scala 2.13 and 3. Covers Show, ShowPretty, Eq, Order, PartialOrder, Hash, Semigroup, Monoid, Commutative*, Band,
  Semilattice, BoundedSemilattice, Group, CommutativeGroup, Empty, Functor, Contravariant, Invariant, Apply,
  Applicative, Foldable, Traverse, Reducible, NonEmptyTraverse, SemigroupK, MonoidK, NonEmptyAlternative,
  Alternative, Pure, EmptyK, ConsK, Bifunctor, Bifoldable, Bitraverse via `Show.derived[A]`, `Functor.derived[F]`,
  Scala 3 `derives Show, Eq, Functor` and `auto.show` imports; @sensitiveData redaction, StrictDerivation, and
  differences from kittens (cats.derived.semiauto, derives). Use when code imports hearth.kindlings.catsderivation,
  when migrating from kittens / cats.derived, or on "value derived is not a member of object cats.Show" errors.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings Cats derivation (`kindlings-cats-derivation`)

Compile-time derivation of 35 type classes from cats, cats-kernel and alleycats for case classes, sealed traits and
Scala 3 enums, with one API on Scala 2.13 and 3 - a replacement for kittens. `.derived` is added to the cats companions
as an extension method. For tagless-final algebras (`FunctorK`, ...) see `kindlings-cats-tagless`.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/cats-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-cats-derivation" % "0.4.0" // %% on JVM-only builds
```

```scala
//> using dep com.kubuszok::kindlings-cats-derivation:0.4.0
```

`cats-core` and `alleycats-core` come in transitively. JVM, Scala.js, Scala Native; Scala 2.13 and 3. Remove `kittens`.

## Imports

```scala
import hearth.kindlings.catsderivation.extensions._   // REQUIRED: adds `derived` to Show, Eq, Functor, ... companions
import hearth.kindlings.catsderivation.ShowPretty     // Kindlings' multi-line Show (not kittens' cats.derived.ShowPretty)
import hearth.kindlings.catsderivation.annotations.sensitiveData
import cats._, cats.syntax.all._
```

`import hearth.kindlings.catsderivation._` alone does **not** bring `derived` into scope; the `extensions` import does.

## Core usage

```scala
case class Person(name: String, age: Int)
case class Box[A](value: A, rest: List[A])
case class Pair[A, B](a: A, b: B)

// Scala 2.13 (also valid on Scala 3)
implicit val showPerson: Show[Person]     = Show.derived[Person]
implicit val orderPerson: Order[Person]   = Order.derived[Person]
implicit val functorBox: Functor[Box]     = Functor.derived[Box]
implicit val traverseBox: Traverse[Box]   = Traverse.derived[Box]
implicit val bifunctorPair: Bifunctor[Pair] = Bifunctor.derived[Pair]

// Scala 3: given or derives (with the extensions import in scope at the definition)
given Monoid[Person] = Monoid.derived
case class Point(x: Int, y: Int) derives Show, Eq, Order
case class Tree[A](value: A, children: List[Tree[A]]) derives Traverse  // Traverse is also a Functor

Person("Alice", 30).show   // Person(name = Alice, age = 30)
```

Monomorphic derivation is recursive: nested case classes / sealed traits without an instance get one derived inside the
same expansion; instances you provide (`implicit`/`given`) always win.

### Automatic (import-based) derivation

There is no implicit `derived` on the cats companions. For kittens-`auto`-like behaviour import a per-type-class object:

```scala
import hearth.kindlings.catsderivation.auto.show._      // Scala 2
import hearth.kindlings.catsderivation.auto.show.given  // Scala 3
Person("Bob", 1).show
```

Available objects: Scala 2 - `show`, `eq`, `order`, `partialOrder`, `hash`, `semigroup`, `monoid`, `empty`; Scala 3 -
the same plus `functor`, `contravariant`, `foldable`, `traverse`. Everything else: use `.derived`.

## Supported type classes (summary)

- **Kind `*`**: `Show`, `ShowPretty`, `Eq`, `Order`, `PartialOrder`, `Hash`, `Semigroup`, `Monoid`,
  `CommutativeSemigroup`, `CommutativeMonoid`, `Band`, `Semilattice`, `BoundedSemilattice`, `Group`,
  `CommutativeGroup`, `alleycats.Empty`.
- **Kind `* -> *`**: `Functor`, `Contravariant`, `Invariant`, `Apply`, `Applicative`, `Foldable`, `Traverse`,
  `Reducible`, `NonEmptyTraverse`, `SemigroupK`, `MonoidK`, `NonEmptyAlternative`, `Alternative`, `alleycats.Pure`,
  `alleycats.EmptyK`, `alleycats.ConsK`.
- **Kind `(*, *) -> *`**: `Bifunctor`, `Bifoldable`, `Bitraverse` (case classes and sealed traits).

Shape requirements per type class (which fields need which instances, sealed-trait support, ConsK shape):
[type-classes.md](type-classes.md).

## `ShowPretty` and `@sensitiveData`

`ShowPretty[A] extends cats.Show[A]` with `showLines(a): List[String]`; `show` joins the lines with the line separator.

```scala
case class User(name: String, @sensitiveData password: String, @sensitiveData("PII") email: String)
implicit val showUser: Show[User] = Show.derived[User]
User("Alice", "s3cret", "a@b.c").show  // User(name = Alice, password = [redacted], email = [redacted: PII])

@sensitiveData("classified") case class Secret(code: String)   // whole type → [redacted: classified]
```

`@sensitiveData` affects `Show` and `ShowPretty` only.

## `StrictDerivation`

```scala
import hearth.kindlings.catsderivation.StrictDerivation
implicit val strict: StrictDerivation = StrictDerivation.instance
val s = Show.derived[Outer]  // now fails to compile if Show[Inner] is not already in scope
```

Disables recursive derivation of field instances (supported by the monomorphic derivations such as Show, ShowPretty,
Eq, Order, PartialOrder, Hash, Semigroup, Monoid, Group, Empty). For a library-wide "explicit only" rule use the
derivation policy instead (`kindlings-derivation-policy`).

## Differences from kittens

- One API on both Scala versions (kittens: shapeless on 2, Mirrors on 3); Scala 2 also gets Band/Semilattice/Group/
  Bifunctor/NonEmptyAlternative/... that kittens offers only on Scala 3; faster generated code.
- Zero-field case classes and case objects render as `Name()` in `Show` (kittens 3: `Name`; kittens 2: `Name$()`).
- `reduceRightTo` is lazier: later fields are not evaluated when the function short-circuits.
- Apply/Applicative for recursive types (rose tree) work; kittens' instances overflow the stack.
- A wrapped field whose type constructor is another case class (`middle: Nel[A]`) is derived recursively after 0.4.0,
  like kittens; 0.4.0 needed its instance in scope (`implicit val r: Reducible[Nel] = Reducible.derived[Nel]`).
- `ConsK`: case classes with head + tail shape (`Nel[A](head: A, tail: List[A])`); after 0.4.0 also kittens 2's
  list-like sealed traits (`IList` with `ICons`/`INil`) and case classes prepending to a nested collection.
- After 0.4.0: `Bifunctor`/`Bifoldable`/`Bitraverse` support fields nesting the type parameters (`List[E]`,
  `Either[A, E]`, another data type) and recursive types, like kittens 3; `Functor`/`Foldable`/`Traverse` support
  recursion through another type constructor (`rest: Option[AtLeastOne[A]]`); `Empty` derives for
  `Recursive(i: Int, is: Option[Recursive])` and recursive sealed traits (their nil case); derived polymorphic instances
  are `Serializable`; kittens' discipline law suites pass on derived instances. In 0.4.0 these shapes threw
  `ClassCastException` at runtime (Bi*/Functor/Foldable/Traverse) or did not compile (`Empty`).
- `private val` constructor fields are shown / compared / combined (after 0.4.0, as kittens); 0.4.0 ignored them in
  `Show`/`Eq`/`Order`/`Hash` and failed to derive `Semigroup`/`Monoid`/`Functor`/`Traverse` & co. for such classes.
- Scala 3: a Java enum's `Order` follows the constants' declaration order (after 0.4.0; before, constants referred to
  in the compiled code came first, so it could change between builds).
- Not ported: kittens `cats.sequence` / `lift` / `replicateH` (shapeless HList utilities), `MkIterable`.
- Scala 3 subtype order is declaration order; on Scala 2 subtypes are ordered by name (affects `Order` across
  subtypes). Kittens on Scala 2 sorts by full name - differs only for numbered names (`Item2` vs `Item10`).

### Migrating from kittens

| kittens | Kindlings |
|---|---|
| `cats.derived.semiauto.show[A]`, `semiauto.eq[A]`, `semiauto.functor[F]`, ... | `Show.derived[A]`, `Eq.derived[A]`, `Functor.derived[F]`, ... with `import hearth.kindlings.catsderivation.extensions._` |
| Scala 3 `import cats.derived.*` + `derives Show` | `import hearth.kindlings.catsderivation.extensions.*` + `derives Show` |
| `import cats.derived.auto.show._` | `import hearth.kindlings.catsderivation.auto.show._` (Scala 3: `.given`) |
| `cats.derived.ShowPretty` | `hearth.kindlings.catsderivation.ShowPretty` |

## Gotchas

- **`value derived is not a member of object cats.kernel.Eq`** (Scala 2; Scala 3 reports a similar "not a member"
  error, also for `derives Show`): the `extensions` import is missing at that spot.
- **Ambiguous `derived`** when kittens' `cats.derived._` / `cats.derived.*` and Kindlings' extensions are both
  imported - remove the kittens import (and the kittens dependency).
- **Polymorphic derivation fails for a field `G[A]`**: `Functor`/`Traverse`/`Apply`/... need an instance for every
  wrapping `G` (e.g. `Traverse[Option]` from cats); on 0.4.0 also for your own case class `G` (derived recursively
  after 0.4.0).
- **`ClassCastException` from a derived `Bifunctor`/`Bifoldable`/`Bitraverse`/`Foldable`/`Traverse`** of a type with
  nested or recursive fields - 0.4.0 only (applied the function to the whole field), fixed after 0.4.0.
- **Scala 2 `-Werror`: "is never used" at an `EmptyK.derived` site** - fixed after 0.4.0.
- **Reducible / NonEmptyTraverse rejected**: at least one field must never be empty (the `A` itself, or wrapped in a
  `Reducible` type).
- **NonEmptyAlternative / Alternative rejected**: every field must wrap `A` in a (NonEmpty)Alternative type; a bare `A`
  field is not allowed.
- **`Functor.derived` on a case class recursive through a container** (`Tree[A](value: A, children: List[Tree[A]])`)
  fails in 0.4.0 with `type mismatch; found: Tree[...CatsDerivationFactories.W2] required: Tree[Any]` (Scala 2 and 3;
  fixed after 0.4.0). On 0.4.0 derive `Traverse` instead - `Traverse.derived[Tree]` works and is a `Functor`.
- **`ConsK.derived` throws `ClassCastException`** when the nested tail uses a type constructor other than `List` (e.g.
  with a custom `ConsK` instance) - 0.4.0 only, fixed after 0.4.0.
- A field instance given by a user `implicit def` is evaluated once per derived instance, not per call (after 0.4.0,
  also for nested/composed instances of polymorphic type classes).
- **Scala 3 enum `Eq`/`Order` with `-Werror`**: older versions emitted "unchecked type test" warnings; fixed in 0.3.2.

## Debugging, timeouts, policy

- Settings namespace: `catsDerivation`.
- Log derivations: `import hearth.kindlings.catsderivation.debug._` (`logDerivationForCatsDerivation`); project-wide:
  `scalacOptions += "-Xmacro-settings:catsDerivation.logDerivation=true"`.
- Timeout (default 5 s): `-Xmacro-settings:catsDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.catsderivation.policy._` (`allowDerivationForCatsDerivation`). The
  HKT derivations (`Functor.derived[F]`, ...) check the policy once at the entry point.

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`, `kindlings-migration`,
`kindlings-integrations` (cats collections such as `NonEmptyList` in fields).

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/cats-derivation/>
- Feature parity (kittens): <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#cats-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/cats-derivation/src/main>
