---
name: hearth-type-class-derivation
description: >-
  Hearth type class derivation architecture for Scala 2.13 / Scala 3 macros - sanely-automatic derivation, rule
  chains (hearth.std.Rule, Rules, Rule.matched, Rule.yielded), derivation context, MIO / Log / MLocal / MIO.scoped,
  runToExprOrFail (single call, 2 s default timeout, "Macro ... timed out after 2000ms"), error ADTs and aggregation
  with parTraverse, summonExprIgnoring to avoid self-summoning (infinite expansion, compiler OOM, StackOverflow,
  runtime null; needs Scala 2.13.17+ / 3.7.0+), derived + inline entry points, LogDerivation import and -Xmacro-settings logging, canonical rule
  order. Use when designing or fixing a derivation macro (encoder, decoder, Show, Eq, codec) built with Hearth.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth type class derivation

How to structure a production-quality derivation macro with Hearth: one sanely-automatic expansion that walks the whole type, prefers user implicits, aggregates every error and can explain itself.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/best-practices/ and https://scala-hearth.readthedocs.io/en/0.4.5/derivation-checklist/ (replace `0.4.5`).

## Sanely-automatic derivation

The macro recurses **internally** (fields, subtypes, elements) instead of relying on implicit search for nested types. Users write one `derived` call (or none: `derived` is an `implicit def`/`inline given` in the companion), recursive types work without `Lazy`, errors know the whole context. Nested types still go through a "use implicit when available" rule first, so user instances win. Background: [blog post](https://kubuszok.com/2025/sanely-automatic-derivation/).

Provide two entry points sharing one core: `derived[A]: TC[A]` (instance) and an inline one (e.g. `show[A](value): String`) that generates the body directly.

## Building blocks

```scala
import hearth.MacroCommons
import hearth.fp.effect.*      // MIO, Log, MLocal, RenderFrom, DontRender
import hearth.fp.instances.*
import hearth.fp.syntax.*      // parTraverse, parMap2, ...
import hearth.std.*            // Rule, Rules, StdExtensions

trait ShowMacrosImpl { this: MacroCommons & StdExtensions =>

  // 1. Context: everything a rule needs, so signatures never change when you add a field
  final case class Ctx[A](tpe: Type[A], value: Expr[A], cache: MLocal[ValDefsCache], derivedType: Option[??]) {
    def nest[B: Type](newValue: Expr[B]): Ctx[B] = copy[B](tpe = Type[B], value = newValue)
  }
  def ctx[A](implicit c: Ctx[A]): Ctx[A] = c
  implicit def ctxType[A: Ctx]: Type[A] = ctx[A].tpe

  // 2. Rules: Matched(result) = handled, Yielded(reasons) = try the next one, failed MIO = rule applies but failed
  abstract class ShowRule(val name: String) extends Rule {
    def apply[A: Ctx]: MIO[Rule.Applicability[Expr[String]]]
  }

  def deriveRecursively[A: Ctx]: MIO[Expr[String]] =
    Log.namedScope(s"Deriving Show for ${Type[A].plainPrint}") {     // scope names are strict: keep them cheap
      Rules(UseImplicit, BuiltIn, AsValueType, AsOption, AsMap, AsCollection, AsSingleton, AsCaseClass, AsEnum)(_[A])
        .flatMap {
          case Right(result) => MIO.pure(result)
          case Left(reasons) =>
            val details = reasons.toListMap.toList.map { case (rule, rs) => s" - ${rule.name}: ${rs.mkString(", ")}" }
            MIO.fail(ShowError.Unsupported(Type[A].prettyPrint, details))
        }
    }
  // object UseImplicit extends ShowRule("use implicit when available") { ... } etc.
}
```

- `MIO` is lazy, non-memoized, stack-safe and catches `NonFatal` (`MIO.scoped`/`runSafe` direct style is not guaranteed stack-safe for deep nesting). Sequential composition (`flatMap`, `>>`, for) is fail-fast; `parTraverse`, `parMap2`, `parTuple` **aggregate errors** - use them for fields, subtypes and independent method bodies.
- `MIO.scoped { runSafe => ... runSafe(mio) ... }` gives direct style, needed inside builder callbacks (`Expr.quote`/`Expr.splice`, `buildCachedWith`, `LambdaBuilder.map`).
- `Log.info/warn/error(msg)` take by-name messages (cheap when logging is off); wrap every step in `Log.namedScope(...)` so the rendered log tells the story. `namedScope`'s name is a **strict** `String`: build it from `plainPrint` or constants, and put costly renderings (`prettyPrint`) inside `Log.info`.
- `MLocal(initial)(fork)(join)` is state forked per parallel branch; `MLocal.unsafeSharedParallel(initial)` is shared across branches (what `ValDefsCache.mlocal` uses).
- Errors: a sealed ADT extending `scala.util.control.NoStackTrace` with a `message`; render all of them once at the end.

## Entry point

```scala
def deriveTypeClass[A: Type]: Expr[Show[A]] = {
  if (Type[A] =:= Type.of[Nothing] || Type[A] =:= Type.of[Any])
    Environment.reportErrorAndAbort(s"Show.derived: type parameter inferred as ${Type[A].prettyPrint}, pass it explicitly")
  val selfType: Option[??] = Some(Type[A].as_??)   // compute OUTSIDE quotes
  implicit val ShowA: Type[Show[A]] = ShowOf[A] // helper: def ShowOf[X: Type] = Type.of[Show[X]] in a Types object
  Log.namedScope(s"Show.derived[${Type[A].plainPrint}] at ${Environment.currentPosition.prettyPrint}") {
    MIO.scoped { runSafe =>
      runSafe(Environment.loadStandardExtensions().toMIO(allowFailures = false)) // once per expansion
      val cache = ValDefsCache.mlocal // a `def`: call it ONCE per expansion and pass this value around
      // Derive BEFORE the quote, as a cached def over its own parameter (see `hearth-def-caching`)...
      val rootDef = ValDefBuilder.ofDef1[A, String](s"show_${Type[A].shortName}", "value")
      runSafe(cache.buildCachedWith("show-root", rootDef) { case (_, value) =>
        runSafe(deriveRecursively[A](using Ctx[A](Type[A], value, cache, selfType)))
      })
      val showRoot: Expr[A] => Expr[String] = runSafe(cache.get1Ary[A, String]("show-root")).get // built above
      // ...then wrap the WHOLE instance, so cached lazy vals/defs live once per instance, not per call
      runSafe(cache.get).toValDefs.use { _ =>
        Expr.quote {
          ShowFactories.instance[A]((a: A) => Expr.splice(showRoot(Expr.quote(a))))
        }
      }
    }
  }.runToExprOrFail(
    "Show.derived",
    infoRendering = if (shouldLog) RenderFrom(Log.Level.Info) else DontRender,
    timeout = macroTimeout
  ) { (logs, errors) =>
    val msg = errors.toVector.map(_.getMessage).mkString("\n")
    s"Failed to derive Show[${Type[A].prettyPrint}]:\n$msg" +
      (if (logs.nonEmpty) s"\nLogs:\n$logs" else "\nEnable logging: import mylib.debug.logDerivation")
  }
}
```

- Do not derive inside the instance's `Expr.splice` and call `toValDefs.use` there: the cached `lazy val`s (summoned instances) and `def`s then become locals of the method body and are re-created on **every call**.
- `runToExprOrFail` is the program's `main`: call it **exactly once per expansion**, at the top. Compose inner `MIO`s with `flatMap`/`MIO.scoped`; calling it again inside the same expansion throws `HearthAssertionError: ... MIO timeout is already set` (runs of other expansions the compiler starts meanwhile, e.g. a summoned macro-derived implicit, are isolated and fine). Its `timeout` defaults to **2 seconds** - large ADTs on a loaded CI exceed it (`Macro 'X' timed out after 2000ms`). Pass a larger default and let users override it via your own setting namespace:

```scala
private def macroTimeout: scala.concurrent.duration.FiniteDuration =
  Environment.typedSettings.toOption.flatMap(_.get("myLib")).flatMap(_.get("timeoutSeconds"))
    .flatMap(_.asInt).map(scala.concurrent.duration.FiniteDuration(_, "s"))
    .getOrElse(scala.concurrent.duration.FiniteDuration(30, "s"))
```

- `Environment.typedSettings` is `Either[String, Data]`: every `-Xmacro-settings` entry of **every** library is parsed into one tree, and any conflict (a key given twice, `a=1` with `a.b=2`) makes it `Left`, so `.toOption` silently drops your settings - consider logging the `Left`. Values are parsed like Scala literals: `30` is an `Int`, `30L` a `Long`, `1.5` a `Double`, `1.5f` a `Float`, `true`/`false` a `Boolean`, `"x"` a quoted `String`, anything else (`30s`) a raw `String` you parse yourself.
- Logging switch: an import-based marker plus a scalac option (`-Xmacro-settings:myLib.logDerivation=true`):

```scala
// runtime code
object Show { sealed trait LogDerivation; object LogDerivation extends LogDerivation }
package object debug { implicit val logDerivation: Show.LogDerivation = Show.LogDerivation } // NOT in the companion
// macro
def shouldLog: Boolean = {
  implicit val LD: Type[Show.LogDerivation] = LogDerivationType
  Expr.summonImplicit[Show.LogDerivation].isDefined ||
    Environment.typedSettings.toOption.flatMap(_.get("myLib")).flatMap(_.get("logDerivation")).flatMap(_.asBoolean).getOrElse(false)
}
```

`-Xmacro-settings` is global to every macro: always namespace your keys (`myLib.`). Both Scala 2 and 3 split a value on commas: use `|` or `;` inside list values.

## Use-implicit rule: never summon yourself

**Requires Scala 2.13.17+ / 3.7.0+ where the macro expands.** `summonExprIgnoring` (`Expr.summonImplicitIgnoring`) throws `HearthRequirementError` (`... available since Scala 2.13.17` / `... since Scala 3.7.0`) on older compilers, including 2.13.16 and 3.3 LTS. Set your library's minimum Scala versions accordingly (Kindlings requires 2.13.18 / 3.8), or on older compilers (`Environment.currentScalaVersion`) avoid an auto-derivation implicit that a plain `summonExpr` could find. Hearth has no ignoring search there.

```scala
object UseImplicit extends ShowRule("use implicit when available") {
  private lazy val ignored: Seq[UntypedMethod] =
    Type.of[Show.type].unsortedMethods.collect { case m if m.name == "derived" => m.asUntyped }
  def apply[A: Ctx]: MIO[Rule.Applicability[Expr[String]]] =
    if (ctx[A].derivedType.exists(_.Underlying =:= Type[A])) MIO.pure(Rule.yielded("type being derived"))
    else ShowOf[A].summonExprIgnoring(ignored*).toEither match {
      case Right(inst) => MIO.pure(Rule.matched(Expr.quote(Expr.splice(inst).show(Expr.splice(ctx[A].value)))))
      case Left(why)   => MIO.pure(Rule.yielded(why))
    }
}
```

- Ignore your own auto-derivation (`derived`, `auto` givens). If your type class extends another library's, also ignore **that** library's derivation methods (e.g. its `derived`/semiauto), or summoning recurses into it.
- Skip the search for the root type when entered from `derived` (`derivedType`), otherwise `implicit val s: Show[X] = Show.derived[X]` finds `s` itself and generates code calling itself (null / StackOverflowError at runtime). Do not skip it in the inline entry point.
- Cache each summoned instance in a `lazy val` (`ValDefBuilder.ofLazy`) and each derived case class / enum body in a `def` - see `hearth-def-caching`. That also makes recursive types work.

## Canonical rule order

1. use cached def (recursion / already derived) 2. use implicit 3. (named tuple, if it must win over value types) 4. built-in primitives and `String` 5. value type (`IsValueType`, guard `Type[A].isNamedTuple`) 6. option (`IsOption`) 7. map (`IsMap`) 8. collection (`IsCollection`) 9. singleton (`SingletonValue`) 10. case class (`CaseClass`) 11. enum / sealed / union (`Enum`).

Why: `Map <: Iterable` (map before collection); `String` and `Option` also match `IsCollection` (built-in and option before collection); Scala 3 named tuples are opaque types (any arity) that `IsValueType`'s opaque-type provider may unwrap; `CaseClass.parse` rejects singletons. Details: `hearth-standard-extensions`, `hearth-case-classes-and-enums`.

## Gotchas

- **Compiler hangs / OOM / "diverging implicit" while deriving** -> plain `summonImplicit` found your own `derived` (or the parent library's auto-derivation) -> `summonExprIgnoring(ignored*)`.
- **Runtime `NullPointerException` or StackOverflowError from `implicit val x: TC[A] = TC.derived[A]`** -> self type not skipped in the use-implicit rule.
- **`Macro 'X' timed out after 2000ms`** -> default timeout; raise it via `runToExprOrFail(timeout = ...)` and make it configurable. To verify your setting is read, set it to `1ms` once.
- **`HearthAssertionError: ... MIO timeout is already set`** -> your expansion starts a second `runToExprOrFail` while its own is active -> stay in one `MIO` program. (A nested `mio.unsafe.runSync` does not throw, but starts from empty state and loses logs and `MLocal`s - avoid it too.)
- **`HearthRequirementError: Expr.summonImplicitIgnoring ... available since Scala 2.13.17`** (or `3.7.0`) -> users compile with an older Scala -> see the version note in the use-implicit section.
- **Only the first error is reported** -> sequential `for`/`flatMap` over fields/subtypes/methods -> `parTraverse`/`parTuple`. (Exception: branches that must see each other's `MLocal` state created with fork/join semantics.)
- **Primitive fields derived as collections of `Char`, `String` encoded as an array** -> no built-in rule before the collection rule.
- **Type parameter inferred as `Nothing` (Scala 2) / `Any` (Scala 3)** for a phantom `A` -> guard and abort with a hint.
- **Calling your macro from a generic helper `def f[A](a: A) = Show.show(a)`** -> the macro sees an abstract `A` -> derive with concrete types or require an implicit `Show[A]` in the helper.
- **Info logs missing** -> only the first `reportInfo` per position is shown; render the whole `MIO` log once (as `runToExprOrFail` does). A second `Environment.loadStandardExtensions()` in the same expansion emits `Extension ... was already loaded in this macro expansion, skipping re-initialization` infos that take that slot - load once.
- **Your `-Xmacro-settings` ignored** -> `Environment.typedSettings` is `Left` because some settings (maybe another library's) conflict -> report the `Left`.
- **Unexpected exceptions swallowed** -> in `renderFailure`, print unknown `Throwable`s with their stack trace.

## Reference

- Full walk-through: [Hearth landing page `Show` example](https://scala-hearth.readthedocs.io/en/0.4.5/), [Micro FP / MIO](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/), [Standard Extensions - rule-based derivation](https://scala-hearth.readthedocs.io/en/0.4.5/standard-extensions/), [Derivation Checklist](https://scala-hearth.readthedocs.io/en/0.4.5/derivation-checklist/).
- Reference implementations (Kindlings 0.4.0 on Hearth 0.4.5): encoder style [FastShowPrettyMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/FastShowPrettyMacrosImpl.scala) with [its rules](https://github.com/kubuszok/kindlings/tree/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/rules); decoder style [circe DecoderMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/circe-derivation/src/main/scala/hearth/kindlings/circederivation/internal/compiletime/DecoderMacrosImpl.scala); combined codec [jsoniter CodecMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/jsoniter-derivation/src/main/scala/hearth/kindlings/jsoniterderivation/internal/compiletime/CodecMacrosImpl.scala).
- Related skills: `hearth-case-classes-and-enums`, `hearth-def-caching`, `hearth-standard-extensions`, `hearth-micro-fp` (type classes, `NonEmpty*`, MIO combinators), `hearth-debugging`, `hearth-testing`, `hearth-generated-code-performance`, and the `hearth-macro-review` skill before release.
