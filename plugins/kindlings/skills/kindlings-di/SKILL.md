---
name: kindlings-di
description: >-
  Compile-time dependency injection with kindlings-di (a macwire port on Hearth) and kindlings-di-cats (Cats-Effect
  Resource wiring). Covers DI.wire, wireRec, wireWith, wireSet, wireList, autowire, autowireMembersOf, wiredInModule
  / Wired, the @Module annotation, softwaremill tagging (@@, taggedWith), DI.plan builder (asLazyVals, storeAsDef,
  provide, debugTree, debugMermaid, build) and DICats.wireResource[F, T] with companion resource[F] factories. Use
  when code imports hearth.kindlings.di or hearth.kindlings.dicats, when migrating from macwire
  (com.softwaremill.macwire wire/autowire/autocats), when wiring fails with "Cannot find a value of type", "Found
  multiple values of type", "cyclic dependencies detected", "unused dependencies", "Missing dependency of type",
  "Ambiguous instances of types", or when asking why wire does not see a local val or an outer class member on Scala
  3.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings DI (`kindlings-di`, `kindlings-di-cats`)

Compile-time dependency injection: `wire[A]` and friends look at the enclosing lexical scope at compile time and emit
plain constructor calls (no reflection, no runtime container). `kindlings-di-cats` adds `DICats.wireResource`, which
composes Cats-Effect `Resource`s into one `Resource[F, A]`.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/di/> and <https://kindlings.readthedocs.io/en/0.4.0/di-cats/>.

## Dependencies

```scala
// sbt (use %% on JVM-only projects)
libraryDependencies += "com.kubuszok" %%% "kindlings-di"      % "0.4.0"
libraryDependencies += "com.kubuszok" %%% "kindlings-di-cats" % "0.4.0" // optional, Resource wiring
```

```scala
//> using dep com.kubuszok::kindlings-di:0.4.0
```

- `kindlings-di`: Scala 2.13 and 3, JVM, Scala.js, Scala Native. Pulls in `com.softwaremill.common::tagging`
  transitively (the `@@` tag types).
- `kindlings-di-cats`: Scala 2.13 and 3, JVM, Scala.js, Scala Native (Native only after 0.4.0). Depends on
  `kindlings-di` and cats-effect 3.

## Imports

```scala
import hearth.kindlings.di.DI        // DI.wire[A], DI.autowire[A](deps, ...), DI.plan[A]...
import hearth.kindlings.di._         // or bare macwire spelling: wire[A], autowire[A](deps, ...), wireSet[A] ...
import hearth.kindlings.di.Module    // @Module annotation
import com.softwaremill.tagging._    // @@, taggedWith

import hearth.kindlings.dicats.DICats // DICats.wireResource[F, A](deps, ...)
import hearth.kindlings.dicats._      // or bare wireResource[F, A](deps, ...)
```

The same code works on Scala 2.13 and Scala 3; there is nothing to `derive`, these are plain macro calls.

## Scope-based wiring: `wire`, `wireRec`, `wireWith`, `wireSet`, `wireList`

```scala
import hearth.kindlings.di.DI

class DatabaseAccess()
class SecurityFilter()
class UserFinder(databaseAccess: DatabaseAccess, securityFilter: SecurityFilter)

class UserModule {
  lazy val databaseAccess = new DatabaseAccess()
  lazy val securityFilter = new SecurityFilter()
  lazy val userFinder: UserFinder = DI.wire[UserFinder] // new UserFinder(databaseAccess, securityFilter)
}
```

`wire[A]` builds `A` from:

1. `A`'s **public primary constructor**, otherwise a **single matching companion `apply`**;
2. each parameter resolved by type (subtype-aware) from the scope; **implicit parameters** go through normal implicit
   search instead.

Candidates, nearest scope first (nearest wins; two candidates in the *same* scope are an ambiguity error):

- parameters of the **closest enclosing method** (all clauses, `implicit`/`using` included; by-name ones evaluated
  where needed), plus, **on Scala 2 only**, `val`s local to that method declared before the call;
- members (declared and inherited, public or protected, `val`/`lazy val`/parameterless `def`) of the immediately
  enclosing class and of enclosing **objects**;
- public parameterless members of any in-scope value whose type is annotated `@Module`.

| Call | What it does |
|---|---|
| `DI.wire[A]` | construct `A` from scope; every dependency must already be in scope |
| `DI.wireRec[A]` | like `wire`, but builds missing dependencies recursively (never fabricates `java.*`/`scala.*` types) |
| `DI.wireWith(factory)` | resolve the factory's parameters from scope and apply it; arities 0-22; e.g. `DI.wireWith(makeFinder _)` or a lambda |
| `DI.wireSet[A]` / `DI.wireList[A]` | collect every in-scope value conforming to `A` (`List` keeps declaration order) |
| `DI.wiredInModule(module)` | runtime `Wired` registry of the module's public parameterless reference-typed members: `wired.lookup(classOf[T])`, `lookupSingleOrThrow`, `withInstances(...)`, `withInstanceFactory(() => ...)` |

### Tags and modules

```scala
import com.softwaremill.tagging._
import hearth.kindlings.di.{DI, Module}

trait Primary; trait Replica
class Database(url: String)
class Connector(primary: Database @@ Primary, replica: Database @@ Replica)

class TaggedModule {
  val primaryDb: Database @@ Primary = new Database("primary").taggedWith[Primary]
  val replicaDb: Database @@ Replica = new Database("replica").taggedWith[Replica]
  lazy val connector: Connector = DI.wire[Connector]
}

@Module class DataModule { lazy val databaseAccess = new DatabaseAccess() ; lazy val securityFilter = new SecurityFilter() }
class AppModule(dataModule: DataModule) { lazy val userFinder: UserFinder = DI.wire[UserFinder] } // reaches into dataModule
```

Module composition by trait inheritance also works (inherited members are candidates; a diamond shares one instance).

## Explicit graphs: `autowire`

`DI.autowire[A](dep1, dep2, ...)` ignores the lexical scope and builds the whole graph of `A` from an explicit list of instances
and factory functions, creating everything else through public constructors / companion `apply`s. Every type is built
once and shared via a generated local `val`.

```scala
val finder: UserFinder = DI.autowire[UserFinder](new DatabaseAccess(), new SecurityFilter())
val finder2 = DI.autowire[UserFinder](
  new DatabaseAccess(),
  (db: DatabaseAccess) => new SecurityFilter() // factory: its params are wired from the graph
)
val fromModule = DI.autowire[UserFinder]( DI.autowireMembersOf(dataModule) ) // seed with a module's members
```

- `autowireMembersOf(module)` adds every public parameterless member (`val`, `lazy val`, no-arg `def`) by its declared
  type. Unused members are fine; only a module none of whose members is used fails with
  `unused dependencies: DI.autowireMembersOf(module)`. (0.4.0: every member had to be used, with a garbled message;
  fixed after 0.4.0.)

- A dependency is a **factory** only if its static type is a function type (also via a type alias), or on Scala 3 a
  context-function literal `(a: A) ?=> B`. A class that merely extends a function type (`List`, `Map`,
  `class Maker extends (A => B)`) is an instance.
- Compile errors: `cyclic dependencies detected; ...`, `cannot use a primitive type or String in autowiring; ...`,
  `unused dependencies: ...`, `duplicate type in dependencies list`, and
  `cannot find a provided dependency, public constructor or public apply method for: ...` (each with the wiring path).

## `DI.plan` (Kindlings' own, not macwire)

Always recursive, always caching, configurable without touching domain classes. Finish with `.build`.

```scala
import hearth.kindlings.di.{DI, PlanDebug, PlanStorage}

val app: App =
  DI.plan[App]
    .asLazyVals                                    // default for the graph: asVals (default) | asLazyVals | asDefs
    .storeAsDef[RequestHandler]                    // per type: storeAsVal | storeAsLazyVal | storeAsDef
    .provide[DatabaseAccess](new DatabaseAccess()) // by-name factory used instead of the constructor
    .debugTree                                     // or .debugMermaid: print the wiring graph at compile time
    .build
// enum forms: .defaultStorage(PlanStorage.LazyVal), .storeAs[T](storage = PlanStorage.Def), .debug(PlanDebug.Mermaid)
```

A `def`-stored type is re-created on every use, so it is **not** shared.

## Resource wiring: `DICats.wireResource`

`DICats.wireResource[F, A](dep1, dep2, ...)` is the F-agnostic counterpart of macwire's `autocats` (which is fixed to `IO`).
No `Sync`/`Async` constraint is needed. Each dependency is classified by its type: `Resource[F, X]` is `flatMap`ped,
`F[X]` is lifted with `Resource.eval`, a plain `X` is used directly, a function (or Scala 3 context function) is a
factory. Acquisition follows argument order (topologically sorted when factories depend on each other) and release
runs in reverse. Missing intermediate types are constructed and shared; a companion
`def resource[F[_]: Sync]: Resource[F, T]` (or constraint-free `def resource[F[_]]`) is discovered and used
automatically - a Kindlings extension with no macwire equivalent.

```scala
import cats.effect.{Resource, Sync, SyncIO}
import hearth.kindlings.dicats.DICats

class Config
class Connection
object Connection {
  def resource[F[_]: Sync]: Resource[F, Connection] = Resource.make(Sync[F].delay(new Connection))(_ => Sync[F].unit)
}
class Service(config: Config, connection: Connection)

val service: Resource[SyncIO, Service] = DICats.wireResource[SyncIO, Service](new Config) // Connection via its companion
```

Errors: `Failed to create an instance of [...]` with `Missing dependency of type [X]. Path ...`,
`Ambiguous instances of types [...] for [...]`, `Not used providers for the following types [...]`,
`Cyclic dependency detected for [...]`. Details: [resource-wiring.md](resource-wiring.md).

## Debugging

No derivation timeout or derivation policy applies to DI (it is not type-class derivation). For generic macro
debugging see the `kindlings-troubleshooting` skill. Module-specific switches:

| Module | Full generation log (resolution + generated code) | Wiring graph only |
|---|---|---|
| di | `import hearth.kindlings.di.debug._` or `-Xmacro-settings:di.logGeneration=true` | `-Xmacro-settings:di.logWiring=tree` (or `=mermaid`); `DI.plan` also `.debugTree` / `.debugMermaid` |
| di-cats | `import hearth.kindlings.dicats.debug._` or `-Xmacro-settings:diCats.logGeneration=true` | `-Xmacro-settings:diCats.logWiring=tree` (or `=mermaid`) |

```scala
// build.sbt
scalacOptions += "-Xmacro-settings:di.logWiring=tree"
```

## Differences from macwire

- `wire`/`wireRec`/`wireWith`/`wireSet`/`wireList`/`autowire`/`autowireMembersOf`/`wiredInModule` follow macwire;
  `DI.plan` is Kindlings-only.
- Cross-platform (JVM, Scala.js, Scala Native). macwire's JVM-proxy request/session **scopes are not ported**, nor the
  reflective half of `Wired` (`wireClassInstance` / `wireClassInstanceByName`); `Wired` keeps the lookup/registry API.
- Only the **closest** enclosing method's parameters are candidates (macwire also looks at outer methods and enclosing
  lambdas). Method-local `val`s are seen on **Scala 2 only**.
- Only the immediately enclosing class exposes `this`; members of an **outer enclosing class** are not reachable
  (enclosing objects always are).
- di-cats: generic over `F` (macwire `autocats` is `IO`-only); companion `resource[F]` factories; a passed instance
  whose type is the root type is reused as the root (macwire rebuilds it). Tag (`@@`) disambiguation is **not** ported
  to `wireResource`.

## Gotchas

- **`Cannot find a value of type: [X]` although a local `val x: X` exists (Scala 3).** Method-local vals are only
  visible on Scala 2. Fix: make it a method parameter, a member of the enclosing class/object, or use
  `DI.autowire[A](x, ...)`.
- **`Cannot find a value of type` inside a nested class.** Members of an outer enclosing class are not reachable, and a
  local/anonymous class body ends the search (the defining method's parameters are not seen). Move the wiring into the
  class that owns the dependencies, put them in an `object`, or pass a `@Module` value.
- **`Found multiple values of type [X]: [a, b]`.** Two candidates in the same scope. Tag them (`X @@ Tag`), move one to
  another scope, or wire explicitly with `autowire`/`DI.plan.provide`.
- **`wire` does not build missing intermediates.** That is by design (macwire semantics). Use `wireRec`, `autowire` or
  `DI.plan`.
- **`String`/primitive dependencies.** `wireRec`/`autowire`/`DI.plan` refuse to fabricate `java.*`/`scala.*` types
  (`cannot use a primitive type or String in autowiring`). Provide such values explicitly, ideally tagged
  (`String @@ DbUrl`) or wrapped in a config class.
- **`unused dependencies: ...` from `autowire`.** Every passed dependency must be used (except individual members of
  `autowireMembersOf(module)`); remove it or fix the type.
- **Passing a context-function `val` to `autowire`/`wireResource` (Scala 3).** The compiler applies it before the macro
  sees it; pass a context-function *literal* instead.
- **`DI.plan` member declared with `asDefs`/`storeAsDef`** is rebuilt on every use - do not use it for things that must
  be singletons (connection pools).
- Give members that hold a `wire` call an explicit type (`lazy val userFinder: UserFinder = DI.wire[UserFinder]`), as
  all documented examples do, so their type does not depend on the macro expansion.

## Links

- DI guide: <https://kindlings.readthedocs.io/en/0.4.0/di/>
- di-cats guide: <https://kindlings.readthedocs.io/en/0.4.0/di-cats/>
- Debugging: <https://kindlings.readthedocs.io/en/0.4.0/debugging/>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/di> and
  <https://github.com/kubuszok/kindlings/tree/0.4.0/di-cats>
