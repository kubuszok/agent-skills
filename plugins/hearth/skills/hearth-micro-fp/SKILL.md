---
name: hearth-micro-fp
description: >-
  Hearth micro-fp (hearth.fp, hearth.fp.data, hearth.fp.effect) for Scala 2.13 / Scala 3 macro authors - type
  classes Functor, Applicative, Parallel, Traverse, ApplicativeTraverse, ParallelTraverse, DirectStyle; syntax pure,
  map2, tuple, parMap2, parTuple, traverse, parTraverse, sequence, parSequence; where instances live, fail-fast vs
  aggregating; NonEmptyList, NonEmptyVector, NonEmptyMap, Id; MIO beyond the basics - handleError, recover, redeem, attempt,
  orElse, firstOf, mio.log.*, MErrors / MResult, MIO.scoped, MLocal, running MIO yourself with unsafe.runSync and
  rendering logs, Environment.handleMioTerminationException, hearth.mioTerminationShouldUseReportError,
  withMioTimeout, withMioLoggingDisabled. Use when code imports hearth.fp, when parTraverse / parMap2 does not
  compile ("No given instance of type hearth.fp.Parallel", "could not find implicit value for evidence parameter of
  type hearth.fp.Parallel", "Not found: type *"), or when picking an error-aggregating data type.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth micro-fp

A tiny, dependency-free FP toolkit for code running **inside macros**: just enough type classes to aggregate errors (`parTraverse`), a direct-style escape hatch for builder callbacks (`DirectStyle`), non-empty collections and `MIO` (Macro IO) with structured logs. It is not a Cats replacement and is not meant for runtime code.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/ (replace `0.4.5`).

How a derivation is structured around `MIO` (rules, `runToExprOrFail`, its timeout, error ADTs, `MIO.scoped` inside `Expr.quote`) is covered by the `hearth-type-class-derivation` skill. This skill is the reference for the toolkit itself.

## Setup and imports

`hearth` already depends on `hearth-micro-fp`; add it alone only when you want the toolkit without the rest of Hearth: `"com.kubuszok" %% "hearth-micro-fp" % "0.4.5"` (`%%%` cross-platform), Scala CLI `//> using dep com.kubuszok::hearth-micro-fp::0.4.5`.

| Import | Brings |
|---|---|
| `hearth.fp.syntax.*` | postfix `.map`, `.pure[F]`, `.map2`, `.tuple`, `.parMap2`, `.parTuple`, `.traverse`, `.parTraverse`, `.sequence`, `.parSequence` |
| `hearth.fp.instances.*` | instances for `Id`, `Option`, `Either`, `Try`, `List`, `Vector` |
| `hearth.fp.DirectStyle` | the `DirectStyle[F].scoped` type class (instances for `Id`/`Option`/`Either`/`Try` are in its companion - **not** in `syntax`) |
| `hearth.fp.data.*` | `NonEmptyList`, `NonEmptyVector`, `NonEmptyMap` (their instances are in their companions) |
| `hearth.fp.effect.*` | `MIO`, `Log`, `MLocal`, `MState`, `MErrors`, `MResult`, `LogRendering` (`DontRender`, `RenderFrom`, `RenderOnly`), `MEval` |
| `hearth.fp.*` | the type classes themselves, `Id[A] = A`, `ignore(a*)` (silence unused-value warnings) |

Inside a `MacroCommons` macro the same imports apply. On Scala 2.13 the `*` imports need `-Xsource:3` (or write `_`).

## Type classes and syntax

| Type class | Methods | Semantics |
|---|---|---|
| `Functor[F]` | `map` | |
| `Applicative[F]` | `pure`, `map2(fa, fb)(f)`; syntax `a.pure[F]`, `fa.map2(fb)(f)`, `fa.tuple(fb)` | sequential, **fail-fast**: `fb` is by-name and skipped once `fa` failed |
| `Parallel[F]` (extends `Applicative`) | `parMap2`; syntax `fa.parMap2(fb)(f)`, `fa.parTuple(fb)` | both sides evaluated, **errors aggregated** |
| `Traverse[F]` | `traverse[G: Applicative]`, `parTraverse[G: Parallel]`; syntax also `fga.sequence`, `fga.parSequence` | `F` is the container, `G` the effect; aggregation is decided by `G` |
| `ApplicativeTraverse[F]` / `ParallelTraverse[F]` | both of the above | combined only so that implicit search for `Functor`/`Applicative` is not ambiguous |
| `DirectStyle[F]` | `scoped { runSafe => ... runSafe(fa) ... }` | direct-style extraction, see below |

The `par` prefix means "independent, aggregate errors" - nothing runs concurrently.

## Instances: where and how they behave

| `F` | Instance | Where | `par*` behaviour |
|---|---|---|---|
| `Id` | `ParallelTraverse` | `hearth.fp.instances` | no errors |
| `Option` | `ParallelTraverse` | `hearth.fp.instances` | `None` if any is `None` (nothing to aggregate) |
| `Either[List[E], *]`, `Either[Vector[E], *]` | `ParallelTraverse` | `hearth.fp.instances` | **aggregates** (`e1 ++ e2`) |
| `Either[NonEmptyList[E], *]`, `Either[NonEmptyVector[E], *]` | `ParallelTraverse` | `NonEmptyList` / `NonEmptyVector` companions | **aggregates** |
| `Either[E, *]` (any other `E`), `Try` | `ApplicativeTraverse` | `hearth.fp.instances` | **no `Parallel`**: only `traverse`/`map2`, fail-fast |
| `List`, `Vector` | `ApplicativeTraverse` | `hearth.fp.instances` | as containers; no `Parallel` |
| `NonEmptyList`, `NonEmptyVector` | `Traverse` | companions | containers only (no `Applicative`) |
| `MIO` | `Parallel` + `DirectStyle` | `MIO` companion | **aggregates** `MErrors` (not a `Traverse`) |
| `MEval` | `Applicative` + `DirectStyle` | `MEval` companion | stack-safe lazy eval, no errors |
| `Id`, `Option`, `Either[E, *]`, `Try` | `DirectStyle` | `DirectStyle` companion | |

`NonEmptyMap` has no instances. To traverse a `Map`, traverse `map.toList` and rebuild.

Runnable (Scala 3.3 and 2.13 with `-Xsource:3`), outputs as printed:

```scala
//> using dep com.kubuszok::hearth-micro-fp::0.4.5
import hearth.fp.DirectStyle
import hearth.fp.data.*
import hearth.fp.instances.*
import hearth.fp.syntax.*

type Errs[A] = Either[List[String], A]   // a type alias avoids needing kind-projector
type Err[A]  = Either[String, A]
def check(i: Int): Errs[Int] = if (i % 2 == 0) Right(i) else Left(List(s"$i is odd"))
def check1(i: Int): Err[Int]  = if (i % 2 == 0) Right(i) else Left(s"$i is odd")
def checkNel(i: Int): Either[NonEmptyList[String], Int] =
  if (i % 2 == 0) Right(i) else Left(NonEmptyList.one(s"$i is odd"))

List(1, 2, 3).traverse(check)        // Left(List(1 is odd))                 - fail-fast
List(1, 2, 3).parTraverse(check)     // Left(List(1 is odd, 3 is odd))       - aggregated
List(1, 2, 3).traverse(check1)       // Left(1 is odd)        (parTraverse(check1) does not compile)
List(1, 2, 3).parTraverse(checkNel)  // Left(NonEmptyList(1 is odd, 3 is odd))
check(1).tuple(check(3))             // Left(List(1 is odd))
check(1).parTuple(check(3))          // Left(List(1 is odd, 3 is odd))
List(check(1), check(2), check(5)).parSequence // Left(List(1 is odd, 5 is odd))
List(Option(1), None).sequence       // None
1.pure[Errs]                         // Right(1)
NonEmptyVector(2, 4).traverse(check) // Right(NonEmptyVector(2, 4))
```

For macro errors you usually do not pick an `Either` at all: `MIO` aggregates `NonEmptyVector[Throwable]` and adds logs. Use `Either[List[E], *]`/`Either[NonEmptyList[E], *]` for small pure helpers (e.g. validating annotations) and lift the result into `MIO` at the boundary.

Writing your own instance: implement `pure` + `map2` (`Applicative`), plus `parMap2` (`Parallel`), or `traverse` + `parTraverse` (`Traverse`); examples in the [docs](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#creating-type-class-instances).

## `DirectStyle`

```scala
val r: Err[Int] = DirectStyle[Err].scoped { runSafe =>
  val a = runSafe(check1(2))
  val b = runSafe(check1(3))   // short-circuits here
  a + b
}                               // Left(3 is odd)
```

`MIO.scoped(runSafe => ...)` is the same for `MIO` and keeps errors and logs of every `runSafe`d program. Its real purpose is extracting a value inside a callback that must return a plain value - an `Expr.splice` inside `Expr.quote`, `LambdaBuilder.map`, `ValDefsCache` builders - where `flatMap` cannot reach (pattern in `hearth-type-class-derivation`).

Rules (`runSafe` short-circuits by throwing a private `ControlThrowable` that `scoped` catches):

- Call `runSafe` only **synchronously inside its own `scoped` block**. A `runSafe` stored in a closure and invoked later throws `PassErrors` (Either/Option/Try) or `java.util.NoSuchElementException: key not found: RunSafe(1)` (MIO).
- Never `catch { case _: Throwable => ... }` around `runSafe`: it swallows the short-circuit (`Right(-1)` instead of `Left(boom)`, verified). `NonFatal` and `scala.util.Try` are safe (they skip `ControlThrowable`).
- Not stack-safe; each `runSafe` evaluates its argument on a separate (virtual, JDK 21+) thread. Prefer `flatMap`/`traverse` for deep recursion; use `scoped` only where combinators cannot go.
- Keep the block small inside splices: pull the value out, then quote. Do not run a whole derivation direct-style while a lambda/instance splice is being evaluated (owners stop lining up for `LambdaBuilder`).

## Data types

| Type | Build | API |
|---|---|---|
| `NonEmptyList[+A](head, tail: List[A])` | `NonEmptyList(1, 2, 3)`, `NonEmptyList(1, List(2))`, `.one(a)`, `.fromList(l): Option[...]` | `+:`, `:+`, `++`, `map`, `flatMap`, `iterator`, `toList`, `toVector`, `toNonEmptyVector`, `size`, `mkString` |
| `NonEmptyVector[+A](head, tail: Vector[A])` | same, `.fromVector(v)` | same, `toNonEmptyList` |
| `NonEmptyMap[K, +V](head: (K, V), tail: ListMap[K, V])` | `NonEmptyMap("a" -> 1, "b" -> 2)`, `.one(kv)`, `.fromListMap(m)` | `+:`, `:+`, `++`, `map`, `flatMap` (both may shrink on key collisions), `iterator`, `toListMap`, `toList`, `toVector`, `toNonEmptyList`, `toNonEmptyVector`, `size`, `mkString` |

They are case classes (pattern-match `NonEmptyVector(head, tail)`), with no `filter`/`exists`/`get`/`foldLeft`: go through `toList`/`iterator`. Insertion order is kept in `NonEmptyMap`; `:+` with an existing key moves that key to the end (`NonEmptyMap("a" -> 1, "b" -> 2) :+ ("a" -> 3)` is `NonEmptyMap((b,2), (a,3))`).

## `MIO` beyond the basics

Full combinator table: [mio-reference.md](mio-reference.md). The essentials:

- Errors are `MErrors = NonEmptyVector[Throwable]`; `MResult[A] = Either[MErrors, A]`. `MIO.fail` takes `Throwable`s only - define an error ADT (`extends Exception(msg) with NoStackTrace`).
- `MIO(thunk)`, `MIO.defer`, `flatMap`, `map`, ... catch `NonFatal` exceptions and turn them into failures (`MIO(1 / 0)` gives `Left(/ by zero)`).
- Recover: `handleError(es => a)`, `handleErrorWith(es => mio)`, `recover { case NonEmptyVector(MyError(m), _) => ... }`, `recoverWith`, `redeem(onSuccess)(onFailure)`, `redeemWith`, `attempt: MIO[MResult[A]]` / `unattempt`.
- Alternatives: `a.orElse(b)` and `MIO.firstOf(a, b, c)` return the first success, or fail with **all** attempts' errors.
- Log: `Log.info/warn/error(msg)` (by-name), `Log.namedScope(name)(mio)`, and on a value `mio.log.info(msg)`, `mio.log.valueAsInfo(a => ...)`, `mio.log.errorsAsWarn(es => ...)`, `mio.log.resultAsInfo(r => ...)` (also `Warn`/`Error` variants).
- State: `MLocal(initial)(fork)(join)` - copied per `par*` branch and joined; `MLocal.unsafeSharedParallel(initial)` - branches see each other's writes (caches). `local.get`, `local.set(a)`.

### Running `MIO` yourself

In a `MacroCommons` macro, prefer `runToExprOrFail` (see `hearth-type-class-derivation`): it installs the timeout, Ctrl+C handling, benchmarking/flame graphs, disables logging when nothing is rendered, and reports logs once. Run by hand only when you need the result as something other than one `Expr` (e.g. several values, custom reporting) or outside `MacroCommons`:

```scala
import hearth.fp.effect.*
import scala.concurrent.duration.*

def describe[A: Type]: Expr[String] = Environment.handleMioTerminationException {
  Environment.withMioTimeout(10.seconds)(program[A].unsafe.runSync) match {
    case Left(timeout)                => Environment.reportErrorAndAbort(timeout.getMessage)
    case Right((state, Right(value))) => Expr(value)
    case Right((state, Left(errors))) =>
      Environment.reportErrorAndAbort(
        errors.toVector.map(_.getMessage).mkString("\n") + "\n" + state.logs.render.fromInfo("MyMacro")
      )
  }
}
```

(compile-checked inside `MacroCommonsScala2` and `MacroCommonsScala3`). `state.logs.render` also has `fromWarn`, `fromError`, `onlyInfo`/`onlyWarn`/`onlyError`, `apply(root)(level => Boolean)`, `apply(root, rendering: LogRendering): Option[String]` and `speedscopeFlameGraph(name, macroStart)`. Rendered output:

```
MyMacro:
└ main:
  ├ rule a:
  │ └ [Info]  a yielded
  ├ rule b:
  │ └ [Info]  b matched
  └ [Info]  done
```

- `unsafe.runSync` alone sets up nothing: no timeout, no Ctrl+C handling, no benchmarking, and every call starts from an empty state (no logs or `MLocal` values are carried between runs).
- `Environment.withMioTimeout(timeout)(thunk): Either[MIO.MioTimeoutException, A]` sets the global deadline; `MioTimeoutException.capturedState.logs` has the logs collected so far. It is not re-entrant (see Gotchas).
- `Environment.handleMioTerminationException(thunk)` catches `MIO.MioTerminationException` (Ctrl+C / SIGTERM / thread interrupt while an `MIO` runs) and, by default, reports where the program was (last result, next step, `MLocal` values, logs) via `reportErrorAndAbort`, which aborts only the current macro. With `-Xmacro-settings:hearth.mioTerminationShouldUseReportError=false` it prints to stderr and rethrows, which on Scala 2 stops the whole compilation; on Scala 3 each looping macro still has to be interrupted. Behind a compilation server stderr may be invisible.
- `Environment.withMioLoggingDisabled(thunk)` makes `Log.*` and `Log.namedScope` no-ops while `thunk` runs (saves allocations). Rendered logs will be empty, so use it only when logs are discarded.

## Gotchas

- **`No given instance of type hearth.fp.Parallel[[B] =>> Either[String, B]] was found`** (Scala 3) / **`could not find implicit value for evidence parameter of type hearth.fp.Parallel[[+B]Either[String,B]]`** (Scala 2) on `.parTraverse`/`.parMap2`/`.parTuple`/`.parSequence` -> `Either[E, *]` with a single `E` cannot aggregate, so it has no `Parallel` -> use `Either[List[E], *]`, `Either[Vector[E], *]`, `Either[NonEmptyList[E], *]`, `Either[NonEmptyVector[E], *]` or `MIO`; or switch to fail-fast `.traverse`.
- **`Not found: type *`** (Scala 3) / **`not found: type *` + `Either[String,<error>] takes no type parameters`** (Scala 2) in `1.pure[Either[String, *]]` or `DirectStyle[Either[String, *]]` -> placeholder syntax needs kind-projector -> Scala 3.3: `-Ykind-projector`; newer Scala 3 (checked on 3.7): `-Xkind-projector`; Scala 2.13: `addCompilerPlugin("org.typelevel" % "kind-projector" % "0.13.4" cross CrossVersion.full)` (Scala CLI: `//> using plugin org.typelevel:::kind-projector:0.13.4`). Or declare `type Err[A] = Either[String, A]`, which needs nothing. Syntax calls like `xs.traverse(f)` infer `G` without any of this.
- **`not found: value DirectStyle` / `NonEmptyList` / missing `.traverse` on Scala 2.13** -> `import hearth.fp.*` is read as importing a member named `*` -> add `-Xsource:3` or use `_`.
- **Only the first error reported** -> `traverse`, `map2`, `tuple`, `flatMap`/for-comprehension are fail-fast by design -> use the `par*` variant for independent steps.
- **`MIO.fail("message")` does not compile** -> errors are `Throwable`s -> wrap in an error case class extending `Exception`/`NoStackTrace`.
- **Using micro-fp or `MIO` in runtime (non-macro) code** -> may fail to link on Scala.js / Scala Native (`DirectStyle` and `MIO` use JVM-only threads and executors); macros always expand on the JVM, so it is fine there. Do not ship it in generated code either - see [FAQ](https://scala-hearth.readthedocs.io/en/0.4.5/faq/#can-i-use-micro-fpmio-in-the-production-code). `MIO` is also not parallel at runtime.
- **`runSafe` leaked or swallowed** -> `PassErrors` / `NoSuchElementException: key not found: RunSafe(N)`, or a failure silently becoming a success -> see `DirectStyle` rules above.
- **`StackOverflowError` in deeply recursive direct style** -> `DirectStyle` is not stack-safe -> use `flatMap`/`traverse` (stack-safe in `MIO`/`MEval`).
- **`HearthAssertionError: MIO timeout is already set — you are re-entering runToExprOrFail/withMioTimeout`** -> a nested top-level run (often summoning a macro-derived implicit whose macro also calls `runToExprOrFail`, or your own `withMioTimeout` inside it) -> one run per expansion; compose with `flatMap`/`MIO.scoped`. A nested `unsafe.runSync` does not assert but silently drops its logs and `MLocal` state.
- **Logs rendered empty** -> rendered inside `withMioLoggingDisabled`, or `runToExprOrFail` with every rendering set to `DontRender` (it disables logging) -> enable at least one rendering.
- **Compilation loops forever** -> interrupt it; with `handleMioTerminationException` (built into `runToExprOrFail`) the error shows the `MIO` step and logs at the time of interruption. Set a `timeout` so CI fails instead of hanging.
- **`Option` with `parTraverse` gives no extra information** -> `None` carries no error; use an aggregating `Either` to report what is missing.

## Reference

- Docs: [Micro FP](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/) ([type classes](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#type-classes), [DirectStyle](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#directstyle), [Data](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#data), [MIO combinators](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#combinators), [Running MIO](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#running-mio), [Shared parallel state](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#shared-parallel-state-mlocalunsafesharedparallel)), [MIO termination handling](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#mio-termination-handling).
- Source: [hearth.fp](https://github.com/kubuszok/hearth/tree/0.4.5/hearth-micro-fp/src/main/scala/hearth/fp) ([instances.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-micro-fp/src/main/scala/hearth/fp/instances.scala), [MIO.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-micro-fp/src/main/scala/hearth/fp/effect/MIO.scala)), [Environments.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/Environments.scala) (termination, timeout, logging switch).
- Related skills: `hearth-type-class-derivation` (MIO-based derivation, `runToExprOrFail`), `hearth-debugging` (log switches, flame graphs), `hearth-lambda-builder` and `hearth-def-caching` (builders that take `MIO` bodies).
