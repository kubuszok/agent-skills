---
name: hearth-hkt-derivation
description: >-
  Hearth polymorphic (higher-kinded, F[_] / kind * -> *) type class derivation in Scala 2.13 / Scala 3 macros -
  Functor, Foldable, Traverse, Contravariant, Applicative, ConsK, tagless-final algebras Alg[_[_]]. Covers
  Type.Ctor1.of[F] entry points (Scala 2 implicit c.WeakTypeTag[F[Any]]), Type.CtorK1, Type.decompose1 + summoning
  TC[G] for an unknown field constructor, the erased F[Any] / Any => Any approach, two-probe field classification
  (F[Int] vs F[String]), local type parameters inside Expr.splice, witness-type factories, and Scala 2 "free type
  variable" errors. Use when deriving a type class whose parameter is a type constructor.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth HKT (polymorphic) derivation

Deriving `TC[F[_]]` (e.g. `Functor[F]`) differs from `TC[A]`: methods have their own type params (`map[A, B]`), field types must be classified relative to the parameter, and nested constructors need `TC[G]` summoned for a `G` known only during expansion.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/#local-type-parameters-in-splices (replace `0.4.5`).

## Entry points

```scala
// shared: trait FunctorMacrosImpl { this: MacroCommons & StdExtensions =>
//   def deriveFunctor[F[_]](FCtor: Type.Ctor1[F]): Expr[cats.Functor[F]] = ... }

// Scala 2 bundle: Type.Ctor1.of[F] reads the implicit WeakTypeTag[F[Any]] - keep that parameter (matched by name)
class FunctorMacros(val c: blackbox.Context) extends MacroCommonsScala2 with FunctorMacrosImpl {
  def deriveFunctorImpl[F[_]](implicit ft: c.WeakTypeTag[F[Any]]): c.Expr[cats.Functor[F]] =
    deriveFunctor[F](Type.Ctor1.of[F])
}
// Scala 2 API: def derived[F[_]]: cats.Functor[F] = macro FunctorMacros.deriveFunctorImpl[F]

// Scala 3
class FunctorMacros(q: Quotes) extends MacroCommonsScala3(using q), FunctorMacrosImpl {
  def mkCtor1[G[_]](using scala.quoted.Type[G]): Type.Ctor1[G] = Type.Ctor1.of[G] // rewritten by the plugin
}
object FunctorMacros {
  def deriveFunctorImpl[F[_]: Type](using q: Quotes): Expr[cats.Functor[F]] = {
    val m = new FunctorMacros(q); m.deriveFunctor[F](m.mkCtor1[F])
  }
}
// Scala 3 API: inline def derived[F[_]]: cats.Functor[F] = ${ FunctorMacros.deriveFunctorImpl[F] }
```

For algebras `Alg[_[_]]` use `Type.CtorK1.of[Alg]` (Scala 2 reads `c.WeakTypeTag[Alg[Option]]`).

## Classify fields with two probes

```scala
val ccInt    = CaseClass.parse(using FCtor[Int])     // F[Int]
val ccString = CaseClass.parse(using FCtor[String])  // F[String]
// zip the fields by name and compare their types:
//   Int    / String  -> DIRECT   (field: A)         map it
//   same   / same    -> INVARIANT (label: String)   copy
//   differs otherwise -> NESTED  (items: List[A])   recurse or summon TC[G]
```

## Summoning `TC[G]` for a nested constructor

No platform-specific code needed (since Hearth 0.4.0):

```scala
Type.decompose1(using fieldType) match {           // List[Int] -> (Ctor1 of List, Int)
  case Some((gCtor, _)) =>
    implicit val tcOfG: Type[cats.Functor[AnyK1]] = Type.CtorK1.of[cats.Functor].apply(using gCtor)
    Expr.summonImplicit[cats.Functor[AnyK1]].toOption // finds the real Functor[List]
  case None => None
}
```

`AnyK1`/`AnyK2` are static labels; the underlying type is the real `G`. `decompose2` splits `G[X, Y]`; types are dealiased first.

## Generating the methods

Two working approaches:

1. **Local type params in splices** (Cross Quotes supports them on both versions): generate `def map[A, B](fa: F[A])(f: A => B): F[B] = Expr.splice { body[F, A, B](Expr.quote(fa), Expr.quote(f))(Type.of[A], Type.of[B]) }` - pass `Type.of[A]` **at the call site**. On Scala 2 these are free types: any `Expr.quote` mentioning `A`/`B` must stay inline in that splice (a quote inside a helper method expands separately -> "free type variable A").
2. **Erased approach** (most robust, needed for the factory pattern): build the body for `F[Any]` / `Any => Any` and cast at the boundary - safe because of JVM erasure:

```scala
Expr.quote {
  FunctorFactories.functorInstance[F] { (fa: F[W1], f: W1 => W2) =>
    Expr.splice(mapBody[F, W1, W2](Expr.quote(fa), Expr.quote(f))(Type.of[W1], Type.of[W2]))
  }
}
// runtime (MiMa-checked) code:
object FunctorFactories {
  sealed trait W1; sealed trait W2    // never instantiated, only labels
  def functorInstance[F[_]](mapFn: (F[W1], W1 => W2) => F[W2]): cats.Functor[F] = new cats.Functor[F] {
    def map[A, B](fa: F[A])(f: A => B): F[B] = mapFn.asInstanceOf[(F[A], A => B) => F[B]](fa, f)
  }
}
```

Rules for witness types: keep `Type.Ctor1[F]` available as an implicit (Scala 2 substitutes `F` in lambda parameter types only then); use `W1`/`W2` only as **type arguments** (`F[W1]`, `W1 => W2`), never as a direct lambda parameter type (Scala 3 emits a `checkcast` to `W1` -> `ClassCastException`) - use `Any` for raw values (`pure(a)`, fold accumulators); for an extra `G[_]` (traverse) use `type AnyF[X] = Any` (kind-correct), e.g. `Applicative[AnyF]`.

When rebuilding a case class with transformed fields, keep each field's own type (`.asInstanceOf[Field]` inside a helper with `Field: Type`): constructor arguments are type-checked (see `hearth-case-classes-and-enums`). Composed type classes (Applicative = pure + map + ap, Alternative = Applicative + SemigroupK) are cheapest when each method body is derived directly (several cached defs, `hearth-def-caching`) rather than delegating to derived parent instances at runtime.

## Gotchas

- **Scala 2 `free type variable A`** -> a helper's own `Expr.quote` references local type params of a method inside an outer quote -> keep that quote inline in the splice, or use the erased approach.
- **Scala 2 `not found: type F`** in generated lambdas -> no implicit `Type.Ctor1[F]` in scope where the quote is written.
- **`ClassCastException ... W1`** (Scala 3) -> witness type used as a direct lambda parameter type -> use `Any` there.
- **`.asInstanceOf` is not fully erased**: the outer class is checked at runtime (`validated.asInstanceOf[Either[E, A]]` throws), only type arguments are erased.
- **`Applicative[Any]` kind mismatch on Scala 3** -> use `type AnyF[X] = Any`.
- **Scala 2 entry point cannot find `Type.Ctor1[F]`** -> the bundle method lacks `implicit ft: c.WeakTypeTag[F[Any]]`.
- **Kind-projector / type lambdas** (`Either[String, *]`) cannot be passed as `F` to `Type.Ctor1.of` on Scala 2 -> build them with `Type.Ctor2.of[Either].setA[String]`.

## Reference

- Docs: [Local type parameters in splices](https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/#local-type-parameters-in-splices), [decomposing applied types](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#type-operations).
- Kindlings 0.4.0 (cats-derivation): [FunctorMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/compiletime/FunctorMacrosImpl.scala), [ConsKMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/compiletime/ConsKMacrosImpl.scala) (carry-and-absorb over direct/nested fields), [ContravariantMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/compiletime/ContravariantMacrosImpl.scala), [TraverseMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/compiletime/TraverseMacrosImpl.scala), witness factories [CatsDerivationFactories](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/runtime/CatsDerivationFactories.scala); Scala 2 / Scala 3 bridges in [`scala-2`](https://github.com/kubuszok/kindlings/tree/0.4.0/cats-derivation/src/main/scala-2/hearth/kindlings/catsderivation/internal/compiletime) / [`scala-3`](https://github.com/kubuszok/kindlings/tree/0.4.0/cats-derivation/src/main/scala-3/hearth/kindlings/catsderivation/internal/compiletime).
