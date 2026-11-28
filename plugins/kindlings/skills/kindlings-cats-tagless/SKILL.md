---
name: kindlings-cats-tagless
description: >-
  Deriving cats-tagless type classes for tagless-final algebras (trait Alg[F[_]] and case class Alg[F[_]]) with
  kindlings-cats-tagless-derivation on Scala 2.13 and 3. Covers KindlingsFunctorK, KindlingsContravariantK,
  KindlingsInvariantK, KindlingsApplyK, KindlingsSemigroupalK and KindlingsInstrument (.derived), mapK / imapK /
  contramapK / productK with FunctionK, supported algebra shapes, and differences from cats-tagless
  (Derive.functorK, @autoFunctorK / @finalAlg macro annotations, Scala 3 @experimental derives). Use when code
  imports hearth.kindlings.catstaglessderivation or cats.tagless, when replacing cats.tagless.Derive or the
  @autoFunctorK annotations, or when cats-tagless derivation needs -Ymacro-annotations / @experimental.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings cats-tagless derivation (`kindlings-cats-tagless-derivation`)

Derives cats-tagless type classes of kind `(* -> *) -> *` for tagless-final algebras, with the same call on Scala 2.13
and 3, no macro annotations and no `@experimental`. For cats/kittens type classes see `kindlings-cats`.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/cats-tagless-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-cats-tagless-derivation" % "0.4.0" // %% on JVM-only builds
```

```scala
//> using dep com.kubuszok::kindlings-cats-tagless-derivation:0.4.0
```

`org.typelevel::cats-tagless-core` (0.16.x) comes in transitively; `cats-tagless-macros` is not needed. JVM, Scala.js,
Scala Native.

## Usage

```scala
import hearth.kindlings.catstaglessderivation._   // Kindlings*K objects
import cats.tagless.FunctorK
import cats.arrow.FunctionK

trait UserRepo[F[_]] {
  def find(id: Int): F[String]
  def version: String            // members without F are kept as they are
}

object UserRepo {
  // Scala 2.13 (also valid on Scala 3)
  implicit val functorK: FunctorK[UserRepo] = KindlingsFunctorK.derived[UserRepo]
  // Scala 3: given FunctorK[UserRepo] = KindlingsFunctorK.derived
}

val optionRepo: UserRepo[Option] = new UserRepo[Option] {
  def find(id: Int) = if (id == 1) Some("Alice") else None
  def version = "1"
}
val toList = new FunctionK[Option, List] { def apply[A](fa: Option[A]): List[A] = fa.toList }
val listRepo: UserRepo[List] = FunctorK[UserRepo].mapK(optionRepo)(toList)
```

| Entry point | Derives | Use |
|---|---|---|
| `KindlingsFunctorK.derived[Alg]` | `cats.tagless.FunctorK[Alg]` | `mapK` (F in covariant positions) |
| `KindlingsContravariantK.derived[Alg]` | `cats.tagless.ContravariantK[Alg]` | `contramapK` (F only in argument positions) |
| `KindlingsInvariantK.derived[Alg]` | `cats.tagless.InvariantK[Alg]` | `imapK` (F in both positions) |
| `KindlingsSemigroupalK.derived[Alg]` | `cats.tagless.SemigroupalK[Alg]` | `productK` over `Tuple2K` |
| `KindlingsApplyK.derived[Alg]` | `cats.tagless.ApplyK[Alg]` | `productK` + `mapK` |
| `KindlingsInstrument.derived[Alg]` | `cats.tagless.aop.Instrument[Alg]` | wrap each call with algebra/method names |

The type argument can be inferred from the expected type (`val fk: FunctorK[UserRepo] = KindlingsFunctorK.derived`).
These are plain methods, not implicits - define the instance once (companion object) and summon it normally. There is
no `derives` form.

## Supported algebra shapes

- `trait Alg[F[_]]` and `case class Alg[F[_]](a: F[Int], ...)` (cats-tagless core `Derive.*` is trait-only).
- Mixed members: `F`-returning and plain ones (plain ones preserved; `SemigroupalK`/`ApplyK` on trait algebras combine
  plain results with their `Semigroup` when one exists, else keep the first algebra's; case-class algebras always keep
  the first's).
- Polymorphic methods (`def m[A](a: A): F[List[A]]`), multiple parameter lists, by-name and default arguments, varargs.
- `F[_]` in argument position (`def transform(in: F[Int]): F[String]`) via `InvariantK`; algebras with no `F` members
  via `ContravariantK` / `InvariantK`.
- Nested algebras (`inner: InnerAlg[F]`): the inner instance is derived recursively if none is in scope.
- After 0.4.0: sealed trait and Scala 3 enum algebras, recursive ones included, for `FunctorK`, `ContravariantK` and
  `InvariantK` (cats-tagless-data's `derives`, also on Scala 2.13); case-class fields and trait members nesting `F` in
  multi-argument types (`Kleisli[F, A, B]`, `EitherT`, `OptionT`, `Tuple2K`, `EitherK`, `FunctionK`, `Cokleisli`)
  through the `*K` instance of `[F[_]] =>> T[F]`; algebras with extra type parameters via a Scala 3 type lambda;
  faster generated `mapK` for members nesting `F`.
- Not supported (Hearth gaps): refined algebras with type members (`Alg[F] { type T = ... }`), dependent method types,
  Scala 2 aliases of algebras with extra type parameters, and on Scala 3 a by-name parameter of a method type parameter
  in `SemigroupalK` / `ApplyK`.

## Differences from cats-tagless

| cats-tagless | Kindlings |
|---|---|
| `cats.tagless.Derive.functorK[Alg]` (Scala 2 macros; Scala 3 `@experimental`) | `KindlingsFunctorK.derived[Alg]`, no `@experimental` |
| `@autoFunctorK`, `@autoInvariantK`, `@finalAlg`, `@autoInstrument` (Scala 2, `-Ymacro-annotations`) | not supported - write the instance in the companion with `.derived` |
| Scala 3 `derives FunctorK` / `cats-tagless-data` for case classes | `.derived` works for case-class algebras on both Scala versions |
| `aop.Aspect`, `Derive.const` / `void` / `readerT`, `Derive.semigroupK` / `monoidK` | not ported (`Instrument` is the only AOP type class) |
| `Derive.functor` / `contravariant` / `invariant` / `semigroupal` / `apply` / `flatMap` / `bifunctor` / `profunctor` (kind `* -> *` algebras) | not ported |

Same behaviour otherwise (oracle-tested against `Derive.*` for every method shape above, including when the natural
transformation runs and how often by-name arguments are evaluated).

### Migrating

1. Replace `cats-tagless-macros` with `kindlings-cats-tagless-derivation` (keep `cats-tagless-core` APIs).
2. Replace `@autoFunctorK` / `@finalAlg` on the algebra with an explicit companion:
   `object Alg { implicit val functorK: FunctorK[Alg] = KindlingsFunctorK.derived[Alg] }`. `@finalAlg`'s
   `Alg.apply[F]` summoner is not generated - use `implicitly` / `summon` or write `def apply`.
3. Drop `-Ymacro-annotations` if nothing else needs it, and `@experimental` / `-experimental` on Scala 3.

## Gotchas

- **`Cannot derive FunctorK for trait: method 'transform' has F[_] in parameter position`**: `F` appears as an
  argument type. Use `InvariantK` (or `ContravariantK` if `F` appears only in arguments).
- **`depends on the type constructor parameter but is not a direct application of it`** for a case-class algebra field
  such as `Kleisli[F, A, B]` - 0.4.0 only, fixed after 0.4.0.
- **`mapK` on an algebra whose plain members you expected to change**: only `F`-typed members are transformed.

## Debugging, timeouts, policy

- Settings namespace: `catsTaglessDerivation`.
- Log derivations: `import hearth.kindlings.catstaglessderivation.debug._` (`logDerivationForCatsTaglessDerivation`);
  project-wide: `scalacOptions += "-Xmacro-settings:catsTaglessDerivation.logDerivation=true"`.
- Timeout (default 5 s): `-Xmacro-settings:catsTaglessDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.catstaglessderivation.policy._`
  (`allowDerivationForCatsTaglessDerivation`), checked once at the entry point.

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`.

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/cats-tagless-derivation/>
- Feature parity: <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#cats-tagless-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/cats-tagless-derivation/src/main>
