# `DICats.wireResource` reference (kindlings-di-cats 0.4.0)

```scala
// sbt - JVM and Scala.js in 0.4.0; also Scala Native after 0.4.0
libraryDependencies += "com.kubuszok" %%% "kindlings-di-cats" % "0.4.0"
```

```scala
import hearth.kindlings.dicats.DICats   // DICats.wireResource[F, T](dep1, dep2, ...)
import hearth.kindlings.dicats._        // bare wireResource[F, T](dep1, dep2, ...)
```

Signature (both Scala versions): `wireResource[F[_], T](dependencies: Any*): Resource[F, T]`. Pass `F` and `T`
explicitly.

## Dependency kinds

| Argument type | Treatment |
|---|---|
| `Resource[F, X]` | acquired with `flatMap`; `X` becomes available |
| `F[X]` | `Resource.eval`, then `flatMap` |
| plain `X` | spliced as-is (no wrapping) |
| function `(A, B) => X` (also via type alias) / Scala 3 context-function literal `(a: A) ?=> X` | factory: its parameters are resolved from the graph; the result is handled by its shape (`Resource`/`F`/plain) |
| value whose class extends a function type | a plain instance, not a factory |

Resolution is by type and subtype-aware (a `Resource[F, Impl]` satisfies a `Trait` parameter).

## Construction

- The root and every missing intermediate type are built from the public primary constructor, else a single matching
  companion `apply`, else a companion `resource[F]` method (`def resource[F[_]]` or `def resource[F[_]: Sync]` etc.; the
  context-bound implicits are summoned for your `F`). A `resource` method with explicit value parameters is not used.
- Each distinct type is built once and shared (diamonds allocate once).
- `java.*`/`scala.*` types (e.g. `String`) are never auto-built: provide them.
- A provided instance of the root type is used as the root (macwire's `autocats` rebuilds it instead).

## Ordering

Acquisition follows argument order; factories that depend on other providers are topologically sorted so their inputs
are acquired first. Release is in reverse order, as with hand-written nested `flatMap`s.

```scala
import cats.effect.{Resource, SyncIO}
import hearth.kindlings.dicats.DICats

class Config; class Db; class Cache
class App(config: Config, db: Db, cache: Cache)

val app: Resource[SyncIO, App] = DICats.wireResource[SyncIO, App](
  new Config,                                  // plain value
  Resource.eval(SyncIO(new Db)),               // resource
  SyncIO(new Cache)                            // effect
)
```

## Compile errors

| Message (prefix) | Cause | Fix |
|---|---|---|
| `Failed to create an instance of [T].` + `Missing dependency of type [X]. Path [constructor T].param ...` | no provider and `X` is not constructible (e.g. `String`, a trait) | pass a value / resource / factory for `X` |
| `Ambiguous instances of types [A, B] for [X]` | two providers conform to `X` (also an instance plus a factory) | pass only one, or make types distinct |
| `Not used providers for the following types [X]` | a passed dependency is not needed | remove it |
| `Cyclic dependency detected for [X]` | cycle in the graph | restructure the classes so the graph is acyclic |
| `Cannot find an implicit value of type: [...]` | a constructor's implicit parameter or a `resource[F]` context bound (e.g. `Sync[F]`) is missing | import/provide the instance for your `F` |

Note: the di-cats user guide says a missing parameter reports *"Cannot find a value of type ..."*; the actual message
is the `Missing dependency of type ...` form above.

## Not supported

- Tagged (`@@`) disambiguation of dependencies inside `wireResource`.
- Scala Native in 0.4.0 (published after 0.4.0).

## Debugging

`import hearth.kindlings.dicats.debug._` or `-Xmacro-settings:diCats.logGeneration=true` (full log + generated code);
`-Xmacro-settings:diCats.logWiring=tree|mermaid` (graph only; provided instances, resources/effects, factories and
`resource[F]` factories are labelled).
