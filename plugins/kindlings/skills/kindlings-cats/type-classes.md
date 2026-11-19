# Type classes derived by `kindlings-cats-derivation` (Kindlings 0.4.0)

All are called as `<Companion>.derived[T]` after `import hearth.kindlings.catsderivation.extensions._` (Scala 3: also
`derives <TypeClass>`).

## Kind `*` (case classes, sealed traits, Scala 3 enums, case objects)

| Type class | Package | Notes |
|---|---|---|
| `Show` | `cats` | `Name(field = value, ...)`; zero-field types as `Name()`; `@sensitiveData` |
| `ShowPretty` | `hearth.kindlings.catsderivation` | multi-line, `showLines`; `@sensitiveData` |
| `Eq`, `Order`, `PartialOrder`, `Hash` | `cats.kernel` | sealed traits: different subtypes are unequal / ordered by subtype order (Scala 3: declaration order; Scala 2: by name); `PartialOrder`: fields with only a `PartialOrder` (e.g. `Set`) allowed, different subtypes incomparable (`NaN`) |
| `Semigroup`, `Monoid`, `CommutativeSemigroup`, `CommutativeMonoid`, `Band`, `Semilattice`, `BoundedSemilattice`, `Group`, `CommutativeGroup` | `cats.kernel` | products only (field-wise); every field needs the same type class |
| `Empty` | `alleycats` | products: field-wise; sealed traits: the single subtype forming an `Empty` (a subtype with an implicit `Empty` is preferred) |

Field instances are summoned, or derived recursively for nested case classes / sealed traits (unless an implicit
`StrictDerivation` is in scope).

## Kind `* -> *` (`F[_]`: case classes with one type parameter; sealed traits where noted)

Fields may be the parameter `A`, constants, `G[A]` (needs `G`'s instance), deeper nestings (`List[Option[A]]`, composed
instances) and, for recursive types, fields mentioning the type itself (`children: List[Tree[A]]`).

| Type class | Package | Requirements |
|---|---|---|
| `Functor`, `Foldable`, `Traverse` | `cats` | `Functor`/`Foldable`/`Traverse` for every wrapping `G`; sealed traits supported (e.g. `IList[A]`). 0.4.0 bug (fixed after 0.4.0): `Functor` for a case class recursive through a container fails - use `Traverse` |
| `Contravariant` | `cats` | `A` only in contravariant positions (e.g. `A => Int` fields) |
| `Invariant` | `cats` | `A` in any position |
| `Apply`, `Applicative`, `Pure` (`alleycats`) | | `Apply`/`Applicative`/`Pure` for every wrapping type; constant fields combined with `Semigroup` / `Monoid` / `Empty` |
| `Reducible`, `NonEmptyTraverse` | `cats` | `Foldable`/`Traverse` for every wrapping type and at least one never-empty field (`A` itself or a `Reducible`/`NonEmptyTraverse` wrapper), e.g. `Nel[A](head: A, tail: List[A])` |
| `SemigroupK`, `MonoidK`, `EmptyK` (`alleycats`) | | `G[A]` fields combined with `SemigroupK[G]` / `MonoidK[G]` / `EmptyK[G]` |
| `NonEmptyAlternative`, `Alternative` | `cats` | every field wraps `A` in a (NonEmpty)Alternative type (`G[H[A]]` also needs `H: Applicative`); a bare `A` field is rejected |
| `ConsK` | `alleycats` | case classes with head + nested tail (`Nel[A](head: A, tail: List[A])`); list-like sealed traits not supported |

A wrapping type constructor that is itself one of your case classes (`middle: Nel[A]`) needs its instance in scope -
HKT derivations do not derive nested type constructors.

## Kind `(*, *) -> *`

| Type class | Package | Notes |
|---|---|---|
| `Bifunctor`, `Bifoldable`, `Bitraverse` | `cats` | case classes and sealed traits with two type parameters (e.g. `Result[A, E]`) |

## Debug / settings

`import hearth.kindlings.catsderivation.debug._` or `-Xmacro-settings:catsDerivation.logDerivation=true`;
timeout `-Xmacro-settings:catsDerivation.timeout=30s`.
