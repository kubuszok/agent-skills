---
name: kindlings-optics
description: >-
  Quicklens-style lenses with kindlings-optics - nested immutable updates without hand-written .copy chains,
  generated at compile time for Scala 2.13 and 3 on JVM, Scala.js and Scala Native. Covers obj.modify(_.a.b) with
  using / apply / setTo / setToIfDefined / setToIf / usingIf, path steps .each, .eachWhere, .at, .index, .atOrElse,
  .eachLeft, .eachRight, .when[Subtype], common fields of sealed traits and Scala 3 enums, modifyAll, reusable
  lenses modifyLens / modifyAllLens / andThenModify (PathModify, PathLazyModify), and .each over cats
  NonEmptyList/Chain via kindlings-cats-integration. Use when code imports hearth.kindlings.optics, when migrating
  from SoftwareMill quicklens (com.softwaremill.quicklens), or on errors like "`.each` is only usable inside a
  `modify(...)` path", "`modify` expects a path lambda like `_.a.b.c`", "no accessible field", "can only descend a
  field into a case class or a sealed hierarchy/enum", "`.each` is not supported on".
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings Optics (`kindlings-optics`)

`obj.modify(_.a.b.c).using(f)` parses the path lambda at compile time and generates the nested copy-with-modification.
It is an independent reimplementation of the [quicklens](https://github.com/softwaremill/quicklens) DSL (same names),
with no reflection and no dependency on quicklens.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/optics/>.

## Dependency

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-optics" % "0.4.0"
```

```scala
//> using dep com.kubuszok::kindlings-optics:0.4.0
```

Scala 2.13 and 3; JVM, Scala.js, Scala Native. There is **no** `kindlings-optics-cats` artifact: cats collections work
through `kindlings-cats-integration` (see below).

## Import

```scala
import hearth.kindlings.optics._        // or: import hearth.kindlings.optics.syntax._
```

Same syntax on Scala 2.13 and Scala 3.

## Core usage

```scala
import hearth.kindlings.optics._

final case class Street(name: String)
final case class Address(street: Street)
final case class Person(name: String, age: Int, address: Address)

val p = Person("Anna", 30, Address(Street("Main")))

p.modify(_.address.street.name).using(_.toUpperCase) // nested update
p.modify(_.age).setTo(31)
```

### Terminal operations on `PathModify[S, A]`

| Terminal | Effect |
|---|---|
| `using(f: A => A)` / `apply(f)` | apply `f` to the focus |
| `setTo(v)` | replace the focus |
| `setToIfDefined(v: Option[A])` | replace only if `v` is `Some` |
| `setToIf(cond)(v)` | replace only if `cond` (`v` is by-name) |
| `usingIf(cond)(f)` | apply `f` only if `cond` |

### Path steps

| Step | Applies to | Meaning |
|---|---|---|
| `_.field` | case class; sealed trait / Scala 3 `enum` whose field is declared on the parent | descend into the field (for a sealed parent the macro matches every case) |
| `.each` | any collection, `Option`, `Map` (values), `Array`, Java collections, anything with a Hearth `IsCollection`/`IsMap`/`IsOption` provider | every element |
| `.eachWhere(p)` | same as `.each` | elements matching `p` |
| `.at(i)` | `Seq` (Int index; after 0.4.0 any `Seq`, mutable included, and `Array`), `Map` (key) | element; `IndexOutOfBoundsException` (`ArrayIndexOutOfBoundsException` for arrays) / `NoSuchElementException` if absent |
| `.index(i)` | `Seq`, `Array`, `Map` | element; no-op if absent |
| `.atOrElse(i, d)` | `Seq`, `Array`, `Map` | element; if absent, appends `f(d)` (Seq) or inserts `key -> f(d)` (Map); `d` is by-name after 0.4.0 (`???` allowed) |
| `.at` / `.index` / `.atOrElse(d)` | `Option` (no index) | the value; `.at` on `None` throws `NoSuchElementException` |
| `.eachLeft` / `.eachRight` | `Either` | the `Left` / `Right` value; no-op on the other side |
| `.when[Sub]` | sealed hierarchy | narrow to subtype `Sub`; other subtypes unchanged |

```scala
team.modify(_.members.each).using(_.toUpperCase)
scores.modify(_.values.at(1)).using(_ + 100)
result.modify(_.value.eachRight).using(_ + 1)
(animal: Animal).modify(_.when[Dog].name).using(_.toUpperCase)
(animal: Animal).modify(_.name).using(_.toUpperCase) // `name` declared on sealed trait Animal
config.modify(_.servers.each.ports.eachWhere(_ < 1024)).using(_ + 8000)
```

### Several paths and reusable lenses

After 0.4.0 `.at`/`.index`/`.atOrElse` on Scala `Seq`s, `Array`s and immutable `Map`s update in place through `updated`,
like quicklens (O(log n) for `Vector`/`Map`).

```scala
names.modifyAll(_.first, _.third).using(_.toUpperCase)   // same focus type; shared prefixes rebuilt with one copy
box.modifyAll(_.xs.each, _.name).using(_.toUpperCase)

val anonymize: Person => Person = modifyLens[Person](p => p.name).setTo("anon") // PathLazyModify terminals return T => T
val both = modifyAllLens[Names](_.first, _.second).using(_.trim)

val toAddress = modifyLens[Person](p => p.address)
val toStreet  = modifyLens[Address](a => a.street)
val toStreetOfPerson = toAddress.andThenModify(toStreet)  // PathLazyModify[Person, Street]
toStreetOfPerson.setTo(Street("Elm"))(p)
```

`modifyAll` (after 0.4.0, as quicklens) builds a path tree: paths sharing an `.each` / `.eachLeft` / `.eachRight` /
`.when[T]` traverse it once, and overlapping paths are applied in the order written (0.4.0 applied each path to the
original value independently - results of overlapping paths can differ). Also after 0.4.0: `modify(obj)(path)` /
`modifyAll(obj)(paths)` spellings on Scala 2 too, and `andThenModify` on `T => PathModify[T, U]`.

### Cats non-empty collections

Add `kindlings-cats-integration` (no extra import) and `.each` works over `NonEmptyList`, `NonEmptyVector`,
`NonEmptyChain`, `Chain` and `NonEmptyMap` values:

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-cats-integration" % "0.4.0"
```

Any custom container works once it has a Hearth `IsCollection`/`IsMap` provider on the classpath; there is no
optics-specific extension point.

## Differences from quicklens

- Same DSL names and semantics (checked against quicklens by differential tests in the Kindlings repo).
- `.each`/`.eachWhere` work on every container Hearth's collection SPI supports (`Set`, `Array`, Java and cats
  collections, ...); quicklens' `Map.eachWhere` is Scala 3 only, here it works on both.
- `.when[Sub]` and common sealed fields also work for Scala 3 `enum`s.
- `.index(i)` with a **negative** index is a no-op on both Scala versions (quicklens for Scala 2 throws
  `IndexOutOfBoundsException`).
- Supported after 0.4.0: hand-written classes with their own `copy`, case classes with an implicit second parameter
  list, intersection (`A with B` / `A & B`) and self types, `.eachWhere` predicates capturing local values (crashed
  scalac 2 in 0.4.0).
- Not supported: Scala 3 extension-method `copy`/accessors (opaque types), literal-typed focuses, user-defined
  `QuicklensFunctor` (write a Hearth `IsCollection`/`IsMap` provider instead).

## Debugging

`import hearth.kindlings.optics.debug._` or `-Xmacro-settings:optics.logGeneration=true` prints the parsed path and
the generated code. No derivation timeout or derivation policy applies. For general macro troubleshooting see the
`kindlings-troubleshooting` skill.

## Gotchas

- **`` `.each` is only usable inside a `modify(...)` path `` (also `.at`, `.when`, ...)** - path markers are
  `@compileTimeOnly`; they exist only inside the lambda passed to `modify`/`modifyAll`/`modifyLens`.
- **`` `modify` expects a path lambda like `_.a.b.c`, but got: ... ``** - the path must be a lambda literal written at
  the call site; a function stored in a `val`, a method reference, or a lambda with logic is not a path. Use
  `modifyLens` to reuse a path.
- **`` `modify` expects a field-access path ... but got an unsupported step ``** - only field selections and the steps
  above are allowed (no method calls such as `.head`, `.get`, `.apply(0)`); use `.at(0)`, `.at` on `Option`, etc.
- **`can only descend a field into a case class or a sealed hierarchy/enum`** (after 0.4.0: `... or a class with a
  copy method taking that field`) - a plain class without a usable `copy` (0.4.0: any non-case class); give it a
  `copy` method, make it a case class or update it manually.
- **`` `modify`: no accessible field `x` on [T] ``** - only case-class constructor fields can be updated (not a `val` in
  the class body or a `def`). For a field declared on a sealed parent, every case must have it as a constructor
  field; otherwise use `.when[Case].x`.
- **`` `.each` is not supported on [T] ``** - `T` has no collection/map/Option provider; for cats types add
  `kindlings-cats-integration`, for custom types register an `IsCollection.Provider`.
- **`modifyAll` with different focus types** fails to type-check; split into separate `modify` calls.
- **`` `modifyAll` expects an explicit list of paths ``** - do not splat a runtime `Seq` of paths (`paths: _*`).
- **Both quicklens and Kindlings imported** - the two `modify` extensions are ambiguous; import only one.

## Links

- Guide: <https://kindlings.readthedocs.io/en/0.4.0/optics/>
- Feature parity: <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#optics>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/optics>
