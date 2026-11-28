---
name: kindlings-diff
description: >-
  Structural diffing of Scala values with kindlings-diff-derivation (Scala 2.13 and 3, JVM/JS/Native), an
  alternative to difflicious and diffx. Covers Diff[A] (Diff.derived, derives Diff, diff, snapshot), DiffResult
  (Identical, ValueChanged, Record, Variant, TypeMismatch, SeqDiff, MapDiff, SetDiff, OptionalDiff, StringDiff,
  isIdentical), Myers-aligned collection and line/word/char string diffs, DiffRenderer.render with RenderConfig
  (plain, default, NameStyle, ColorMode, Indent), Diff.assertNoDiff / assertDiff for tests, ignoreField,
  Diff.approximate for numeric tolerance. Use when code imports hearth.kindlings.diffderivation, when writing test
  assertions that show what differs between two case classes, or when migrating from difflicious / diffx.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings Diff (`kindlings-diff-derivation`)

Kindlings' own type class `Diff[A]`: compares two values structurally and returns a `DiffResult` tree (field-by-field
for case classes, Myers shortest-edit-script for sequences, line → word → char for strings) that `DiffRenderer` prints.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/diff-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-diff-derivation" % "0.4.0" % Test // %% on JVM-only builds
```

```scala
//> using test.dep com.kubuszok::kindlings-diff-derivation:0.4.0
```

No other runtime dependencies. JVM, Scala.js, Scala Native; Scala 2.13 and 3.

## Usage

```scala
import hearth.kindlings.diffderivation._

case class Person(name: String, age: Int)

// Scala 2.13 (also valid on Scala 3)
implicit val diffPerson: Diff[Person] = Diff.derived[Person]
// Scala 3
case class Item(id: Int, tags: List[String]) derives Diff

val result: DiffResult = diffPerson.diff(Person("Alice", 30), Person("Alice", 31))
result.isIdentical                                   // false
println(DiffRenderer.render(result, RenderConfig.plain))
// Person(
//   name = "Alice",
//   age = 30 -> 31,
// )
```

`Diff.derived` is an implicit/given ("sanely-automatic"): `Diff[A]` / `implicitly[Diff[A]]` derives on demand, nested
types are derived recursively in one expansion, and instances you provide (e.g. a tolerant `Diff[Double]`) are used
instead of derivation.

`Diff[A]` members: `diff(left, right): DiffResult`, `snapshot(value): DiffResult` (used for inserted/deleted
elements), names `plainName` (FQN), `simpleName`, `shortName`, `prettyName` (ANSI-coloured FQN).

### In tests

```scala
Diff.assertNoDiff(actual, expected)   // throws AssertionError("Values differ:\n<plain rendering>")
val r = Diff.assertDiff(a, b)         // throws if identical, returns the DiffResult
```

Use them from any test framework (MUnit, ScalaTest, ...); there are no framework-specific integrations.

### Tweaks

```scala
val ignoringAge: Diff[Person] = Diff.derived[Person].ignoreField("age")   // also .modifyField("age").ignore
implicit val tolerant: Diff[Double] = Diff.approximate(0.001)             // |l - r| <= epsilon is identical
```

`ignoreField` works on the top-level record (or a sealed-trait variant's body), by field name; it is not path-based.
`modifyField(name).using(diff)` replaces the comparison of that field with `diff` (same scope; fixed after 0.4.0, where
it was silently ignored).
`Diff.approximate[T: Numeric](epsilon)` in implicit scope is picked up for every `T` field of derived types.

## Rendering

`DiffRenderer.render(result, config = RenderConfig.default)`.

| `RenderConfig` | Meaning |
|---|---|
| `RenderConfig.default` | `NameStyle.Simple`, `ColorMode.Ansi`, `Indent.Spaces(2)` |
| `RenderConfig.plain` | same with `ColorMode.Plain` (`+` / `-` / `~` markers) - use for logs and assertion messages |
| `RenderConfig(nameStyle, colorMode, indent)` | `NameStyle.Simple` / `Short` / `FullyQualified` / `Pretty`; `ColorMode.Ansi` / `Plain`; `Indent.Spaces(n)` / `Indent.Tab` |

## What is compared how

| Type | Result |
|---|---|
| Case classes | `DiffResult.Record` (field by field) |
| Sealed traits / enums | `Variant` (same subtype) or `TypeMismatch` |
| Primitives, `BigInt`, `BigDecimal` | `Identical` / `ValueChanged` (`==`) |
| `String` | `StringDiff`: Myers over lines, changed lines over words, changed words over chars |
| `List`, `Vector`, `Seq`, ... | `SeqDiff` of `Edit.Equal` / `Edit.Insert` / `Edit.Delete` (Myers, shortest edit script) |
| `Map[K, V]` | `MapDiff` matched by key |
| `Set[A]` | `SetDiff` matched by element |
| `Option[A]` | `OptionalDiff` |
| Value classes / opaque types | unwrapped |
| Case objects | always identical |
| Recursive types | supported |

## Compared with difflicious / diffx

Kindlings adds Myers-optimal sequence alignment (difflicious/diffx match greedily or by index), hierarchical string
diffs, configurable name style / colour / indentation, Scala Native. Not available in 0.4.0: path-based configuration
(`ignoreAt`, `modify(_.a.b)`), test-framework integrations, custom matching of collection elements by key for derived
fields. Cats collections (`NonEmptyList`, ...) work with `kindlings-cats-integration` on the classpath.

## Gotchas

- **`modifyField(name).using(otherDiff)` has no effect in 0.4.0** (fixed after 0.4.0). On 0.4.0 put an implicit
  `Diff[FieldType]` in scope before deriving, or use `ignoreField`.
- **`ignoreField` on a nested field does nothing**: it only applies to the fields of the instance it is called on.
  Derive and ignore on the nested type's instance and keep it implicit while deriving the outer type.
- **Floating-point noise reported as changes**: provide `implicit val d: Diff[Double] = Diff.approximate(eps)` where
  the outer `Diff` is derived.
- **ANSI escape codes in CI logs / assertion messages**: render with `RenderConfig.plain`. 0.4.0's `Diff.seqDiff`
  element names still contained ANSI codes under `RenderConfig.plain`, and nested entries of sequences/maps/sets were
  not indented under their `+`/`-` marker (both fixed after 0.4.0).
- **Values differing only in a `private val` constructor field reported identical** (0.4.0) - such fields are compared
  after 0.4.0 (as difflicious / diffx).
- **`Diff.derived` inferred as `Nothing`/`Any`** (error "type parameter was inferred as ..."): pass the type explicitly.

## Debugging, timeouts, policy

- Settings namespace: `diffDerivation`.
- Log one derivation: `import hearth.kindlings.diffderivation.debug._` (`logDerivationForDiffDerivation`), or the
  whole module: `-Xmacro-settings:diffDerivation.logDerivation=true` (ignored by 0.4.0, read after 0.4.0).
- Timeout (default 5 s): `-Xmacro-settings:diffDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.diffderivation.policy._` (`allowDerivationForDiffDerivation`).

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`.

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/diff-derivation/>
- Feature parity: <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#diff-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/diff-derivation/src/main>
