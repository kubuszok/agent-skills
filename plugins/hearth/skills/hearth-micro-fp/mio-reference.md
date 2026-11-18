# `MIO` reference (Hearth 0.4.5)

All names are in `hearth.fp.effect` (`import hearth.fp.effect.*`) unless stated otherwise. Verified against the
[0.4.5 sources](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-micro-fp/src/main/scala/hearth/fp/effect/MIO.scala).
`MIO` is lazy (nothing runs until a run), not memoized (reusing a value re-runs it), stack-safe for combinators, and
synchronous: "parallel" means "independent, errors aggregated", never threads.

## Types

| Name | Definition |
|---|---|
| `MErrors` | `NonEmptyVector[Throwable]` |
| `MResult[A]` | `Either[MErrors, A]`; `MResult.pure(a)`, `MResult.fail(e, es*)`, `MResult.fail(errs)`, `MResult.void`; `result.suspend: MIO[A]` |
| `MState` | final state of a run: `logs: Logs` (`Vector[Log]`) and `MLocal` values |
| `Log.Level` | `Log.Level.Info`, `Warn`, `Error` (ordered) |
| `LogRendering` | `DontRender`, `RenderFrom(level)`, `RenderOnly(level)` |

## Constructors

| Call | Result |
|---|---|
| `MIO.pure(a)` | success |
| `MIO.void` | `MIO[Unit]` success |
| `MIO.fail(e, es*)` / `MIO.fail(errs: MErrors)` | failure (`Throwable`s only) |
| `MIO(thunk)` | suspended; a `NonFatal` exception becomes a failure |
| `MIO.defer(mioThunk)` | builds the `MIO` when it runs (recursion, side-effecting setup); catches `NonFatal` |
| `MIO.suspend(mresultThunk)` / `mresult.suspend` | lazily lift an `MResult` |
| `MIO.firstOf(a, b, c*)` | first success, or all errors aggregated (`a.orElse(b).orElse(c)`) |
| `MIO.scoped { runSafe => ... runSafe(mio) ... }` | direct style (`DirectStyle[MIO]`), errors and logs of every `runSafe` kept |

## Sequencing (fail-fast)

| Call | Meaning |
|---|---|
| `fa.flatMap(f)`, `fa.flatten`, for-comprehension | sequence |
| `fa.map(f)`, `fa.as(b)`, `fa.void` | transform / replace value |
| `fa.flatTap(f)` / `fa.mapTap(f)` | run `f` for its effect, keep the value |
| `fa.map2(fb)(f)`, `fa.tuple(fb)` | combine; `fb` is skipped if `fa` failed |
| `fa >> fb`, `fa *> fb`, `fa <* fb` | sequence keeping one side |

## Parallel (aggregating)

| Call | Meaning |
|---|---|
| `fa.parMap2(fb)(f)`, `fa.parTuple(fb)` | both run from the same state; if both fail, `e1 ++ e2` |
| `fa &> fb`, `fa <& fb` | like `*>` / `<*` but aggregating |
| `xs.parTraverse(f)`, `mios.parSequence` | with `hearth.fp.syntax.*` and `hearth.fp.instances.*` (the container's `Traverse`) |

`MLocal(initial)(fork)(join)` values are forked per branch and joined afterwards; `MLocal.unsafeSharedParallel(initial)`
values flow through branches in order (branch B sees branch A's writes).

## Error handling

| Call | Meaning |
|---|---|
| `fa.handleError(es => a)` | recover from any failure with a value |
| `fa.handleErrorWith(es => mio)` | recover with another program |
| `fa.recover { case NonEmptyVector(MyError(m), _) => a }` | recover from matching failures only; others stay failures |
| `fa.recoverWith(pf)` | same, with a program |
| `fa.redeem(onSuccess)(onFailure)` | map both outcomes to a value |
| `fa.redeemWith(onSuccess)(onFailure)` | map both outcomes to a program (the primitive the others use; it also turns an exception thrown by the continuations into a failure with an error log `Caught exception ...`) |
| `fa.attempt` | `MIO[MResult[A]]`, never fails |
| `fa.unattempt` | back from `MIO[MResult[B]]` to `MIO[B]` |
| `fa.attemptTap(r => ...)` / `fa.attemptFlatTap(r => mio)` | inspect the result, keep it unchanged |
| `fa.orElse(fb)` | `fa`, or `fb` if `fa` failed; if both fail, errors of both |

Verified outputs (Scala 3.3 and 2.13), with `rule(name, ok)` logging and failing with `DerivationError(s"$name does not apply")` when `!ok`:

```
MIO.firstOf(rule("a", false), rule("b", false), rule("c", true))   Right(via c)
MIO.firstOf(rule("a", false), rule("b", false))                    Left(a does not apply, b does not apply)
rule("a", false).handleError(_ => "default")                       Right(default)
rule("a", false).recover { case NonEmptyVector(DerivationError(m), _) => s"recovered: $m" }
                                                                   Right(recovered: a does not apply)
rule("a", false).redeem(identity)(es => s"${es.size} error(s)")    Right(1 error(s))
rule("a", true).attempt                                            Right(Right(via a))
rule("a", false).map2(rule("b", false))(_ + _)                     Left(a does not apply)
rule("a", false).parMap2(rule("b", false))(_ + _)                  Left(a does not apply, b does not apply)
List("x", "y").parTraverse(n => rule(n, false))                    Left(x does not apply, y does not apply)
MIO(1 / 0)                                                         Left(/ by zero)
```

## Logging

| Call | Meaning |
|---|---|
| `Log.info(msg)`, `Log.warn(msg)`, `Log.error(msg)` | `MIO[Unit]`; `msg` is by-name (free when logging is disabled) |
| `Log.namedScope(name)(mio)` | nest the logs of `mio` under `name` (and a flame-graph frame when benchmarking) |
| `mio.log.info(msg)` (`warn`, `error`) | log after success, keep the value |
| `mio.log.valueAsInfo(a => msg)` (`Warn`, `Error`) | log computed from the value |
| `mio.log.errorsAsInfo(es => msg)` (`Warn`, `Error`) | log computed from the errors, still failing |
| `mio.log.resultAsInfo(r => msg)` (`Warn`, `Error`) | log computed from the `MResult` |

A failed program still has its logs: render them in the error message.

## Running and rendering

| Call | Meaning |
|---|---|
| `mio.unsafe.runSync: (MState, MResult[A])` | run with no timeout, no Ctrl+C handling, no benchmarking; starts from an empty state |
| `mioOfExpr.runToExprOrFail(name, ...)(renderFailure)` | the `MacroCommons` entry point (see the `hearth-type-class-derivation` skill) |
| `state.logs.render.fromInfo(root)` / `fromWarn` / `fromError` | tree of entries at or above the level |
| `state.logs.render.onlyInfo(root)` / `onlyWarn` / `onlyError` | entries of exactly that level |
| `state.logs.render(root)(level => Boolean)` | custom filter |
| `state.logs.render(root, rendering): Option[String]` | by `LogRendering` (`DontRender` gives `None`) |
| `state.logs.render.speedscopeFlameGraph(name, macroStart)` / `speedscopeFlameGraphTo(out, name, macroStart)` | speedscope JSON; needs `MIO.benchmarkScopes = true` while running |

## Global switches and `Environment` helpers

| Name | Meaning |
|---|---|
| `Environment.withMioTimeout(timeout)(thunk): Either[MIO.MioTimeoutException, A]` | sets the global deadline; not re-entrant (`HearthAssertionError` if a deadline is already set) |
| `MIO.MioTimeoutException(capturedState, prettyPrintedMessage)` | `capturedState.logs` holds the logs collected before the deadline |
| `Environment.handleMioTerminationException(thunk)` | turns `MIO.MioTerminationException` (Ctrl+C, SIGTERM, thread interrupt) into a report of the last `MIO` step, `MLocal` values and logs |
| `-Xmacro-settings:hearth.mioTerminationShouldUseReportError=true` (default) | report with `reportErrorAndAbort` (aborts only the current macro) |
| `-Xmacro-settings:hearth.mioTerminationShouldUseReportError=false` | print to stderr and rethrow (stops the compilation on Scala 2) |
| `Environment.withMioLoggingDisabled(thunk)` | `Log.*`/`namedScope` record nothing while `thunk` runs; saved and restored, so nesting is safe |
| `Environment.configureMioBenchmarking()` | applies `-Xmacro-settings:hearth.mioBenchmarkScopes=true` (`runToExprOrFail` calls it) |
| `MIO.benchmarkScopes`, `MIO.disableLogging`, `MIO.timeoutDeadlineNanos` | the underlying global `var`s; prefer the helpers above, which restore them |
