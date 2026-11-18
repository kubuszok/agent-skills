# Hearth 0.4.5 API cheat sheet

Members of `MacroCommons` (use inside `trait X { this: MacroCommons => ... }`) unless an import is shown. Verified against the Hearth 0.4.5 sources; when in doubt check [the sources](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scala/hearth) or [Basic Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/).

## Types

| API | Result | Notes |
|---|---|---|
| `Type[A]` | `Type[A]` | summons the implicit `Type[A]` (context bound `[A: Type]`) |
| `Type.of[A]` | `Type[A]` | Cross Quotes; creates a `Type` for a type written statically in the source |
| `Type.Ctor1.of[F]` ... `Type.Ctor22.of[F]` | `Type.CtorN[F]` | `.apply[A]` builds `Type[F[A]]`, `.unapply(tpe)` extracts args as `??` |
| `Type.Ctor2.of[Either].setA[String]` / `.setB[Int]` | `Type.Ctor1[...]` | partial application; one setter per parameter letter (`setA`, `setB`, `setC`, ...; there is no `setLast`); apply several from the back. `Ctor1.setA` gives a `Type[F[A]]` |
| `Type.CtorN.fromUntyped[F](untyped)` / `ctor.asUntyped` | | convert to/from `UntypedType` |
| `Type.CtorK1.of[Alg]` | | for `Alg[_[_]]` (kind `(* -> *) -> *`) |
| `Type.decompose1[A]` / `decompose2[A]` | `Option[(Ctor1[AnyK1], ??)]` / `Option[(Ctor2[AnyK2], (??, ??))]` | split `G[X]` / `G[X, Y]` when `G` is unknown statically |
| `Type.Lazy(Type.of[X])` | `Type.Lazy[X]` | helper `Type` kept in a field; converts to `Type[X]` implicitly |
| `new Type.Cache[F]` | | per-type memo keyed by `=:=` (`get`, `put`, `getOrPut`); on Scala 3 entries are partitioned per `Expr.splice` scope (a lookup from another splice recomputes) |
| `Type[A].prettyPrint` / `plainPrint` / `shortName` / `fqcn` | `String` | `prettyPrint` has ANSI colors - logs only, never keys |
| `Type[A] <:< Type[B]`, `Type[A] =:= Type[B]` | `Boolean` | never use `==` on `Type`s |
| `Type[A].isCaseClass` / `isCaseObject` / `isCaseVal` / `isSealed` / `isJavaEnum` / `isOpaqueType` / `isNamedTuple` / `isUnionType` / `isTuple` / `isFunction` / `isAbstract` / `isPrimitive` ... | `Boolean` | |
| `Type.typeArguments[A]`, `Type[A].parents` / `baseClasses` | `List[??]` | |
| `Type[A].directChildren` / `exhaustiveChildren` | `Option[...]` of `??<:[A]` | sealed / enum / union children |
| `Type[A].primaryConstructor` / `constructors` / `methods` / `unsortedMethods` / `unsortedMethodsNamed(n)` | `Option[Method]` / `List[Method]` | prefer `unsorted*` for lookups (see `hearth-introspection`) |
| `Type[A].companionObject` / `pseudoCompanionObject` | `Option[Expr_??]` | |
| `Type[A].annotations` / `annotationsOfType[Ann]` / `typeAnnotations` / `hasAnnotationOfType[Ann]` | | |
| `Type[A].summonExpr` / `summonExprIgnoring(methods*)` | `SummoningResult[A]` | `.toOption`, `.toEither`, `.isDefined`, `.fold(...)`; `*Ignoring` needs Scala 2.13.17+ / 3.7.0+ where the macro expands (throws on older) |
| `Type[A].as_??` | `??` | existential; `import t.Underlying as X` brings `Type[X]` |
| `Type(value)` / `Type.unapply(tpe)` (needs an implicit `TypeCodec[A]`), `Type.StringCodec.fromType(tpe)` | `Type[...]` / `Option[...]` | literal (singleton) types: `val five: Type[Int] = Type(5)` builds the literal type `5` (ascribe the widened type: an expected `Type[5]` picks the object codec), `Type.unapply(five) == Some(5)`. `TypeCodec` itself has no `unapply`: `case Type.StringCodec(v) =>` does not compile. See `hearth-expr-toolkit` |

## Expressions

| API | Result | Notes |
|---|---|---|
| `Expr(value)` / `Expr.unapply(expr)` | `Expr[A]` / `Option[A]` | lift/unlift via `ExprCodec` (primitives, String, collections, Option, Either, `Data`, ...); `ExprCodec.derived`, `semiQuote`: `hearth-expr-toolkit` |
| `Expr.quote { ... }` / `Expr.splice(e)` | | Cross Quotes; splice only inside quote |
| `Expr.summonImplicit[A]` / `summonImplicitIgnoring[A](methods*)` | `SummoningResult[A]` | `*Ignoring`: Scala 2.13.17+ / 3.7.0+ only |
| `expr.prettyPrint` / `plainPrint` / `prettyAST` / `plainAST` | `String` | |
| `expr.upcast[B]` | `Expr[B]` | asserts `A <:< B`; needs `Type[A]` and `Type[B]` |
| `expr.as_??` | `Expr_??` | `import e.{Underlying as T, value as v}` |
| `expr.semiEval` / `Expr.semiEval(expr[, overrides])` | `Either[NonEmptyVector[String], A]` | evaluate config-like expressions at compile time; refuses members of the module being compiled |
| `expr.annotated[scala.annotation.nowarn]()` | `Expr[A]` | `{ @nowarn val x = expr; x }`; needs implicit `Type[nowarn]` and `Type[A]` |
| `expr.suppressUnused` | `Expr[Unit]` | |
| `Expr.singletonOf[A]` | `Option[Expr[A]]` | |
| `MatchCase.typeMatch[A]()` / `eqValue(expr)` / `typeTestMatch[A, B]()` (Scala 3) / `MatchCase.matchOn(scrutinee)(cases)` | | build `match` expressions; no default arm is added |
| `ValDefs.createVal/createVar/createLazy/createDef(expr, name)` then `.use { ref => ... }` | `Expr[B]` | local definitions with fresh names |
| `ValDefBuilder.ofVal/ofVar/ofLazy[T](name)`, `ofDef0..ofDef22[A..., R](name, argNames...)` | | build/caching of `def`s (see `hearth-def-caching`) |
| `ValDefsCache.empty` / `ValDefsCache.mlocal` | | cache of definitions; `.toValDefs.use(_ => expr)` |
| `LambdaBuilder.of1[A](name)` ... `of22` + `.map`/`.traverse` + `.build[R]` / `.buildWith(f)` | `Expr[A => R]` | only when the lambda's parameter types/arity are computed during expansion; otherwise write the lambda inside `Expr.quote` |
| `DestructuredExpr.parse(expr)` / `extractFieldPath[S, A](lambda)` / `extractLambda(expr)` | | semantic expression parsing |

## Classes and methods

| API | Result |
|---|---|
| `CaseClass.parse[A]` / `Enum.parse[A]` / `SingletonValue.parse[A]` / `NamedTuple.parse[A]` / `JavaBean.parse[A]` (see `hearth-introspection`) / `AnonymousInstance.parse[A]` | `ClassViewResult[...]` (`.toOption`, `.toEither`) |
| `CaseClass.unapply(tpe)`, `Enum.unapply(tpe)`, `SingletonValue.unapply(tpe)` | `Option[...]` |
| `cc.caseFieldValuesAt(expr)` | `ListMap[String, Expr_??]` |
| `cc.construct[F](param => F[Expr_??])` / `cc.parConstruct[F](...)` | `F[Option[Expr[A]]]` |
| `cc.primaryConstructor` / `cc.caseFields` / `cc.copyMethod()` | `Method` / `List[Method]` / `Option[Method.OnInstance.Of[A]]` |
| `enumm.matchOn[F, B](expr)(matched => F[Expr[B]])` / `parMatchOn` | `F[Option[Expr[B]]]` |
| `enumm.directChildren` / `exhaustiveChildren` | children as `??<:[A]` |
| `sv.singletonExpr` | `Expr[A]` |
| `method.name` / `isImplicit` / `isCaseField` / `totalParameters` / `knownReturning` / `asUntyped` | |
| `method.fold(onInstance, onTypes, onValues)` / `foldF[F](...)` | `Either[String, Expr_??]` / `F[Either[String, Expr_??]]` (needs `DirectStyle[F]`) |
| `Method.OnInstance` -> `ApplyTypes` -> `ApplyValues` -> `Result[R]#build()` | builder chain |
| `param.name` / `index` / `tpe` / `hasDefault` / `defaultValue` / `annotations` / `isByName` / `isVararg` / `isImplicit` | |
| `Annotations.decodedConstructorArguments(ann)` | `Option[List[Either[String, Any]]]` |

## Environment

| API | Notes |
|---|---|
| `Environment.reportInfo/reportWarn/reportError(msg[, pos])` | only the first info per position is shown, on both versions (do not rely on repeated warnings either); errors: Scala 2 shows only the first per position, Scala 3 all - aggregate and report once |
| `Environment.reportErrorAndAbort(msg[, pos])` | `Nothing` |
| `Environment.currentPosition` / `isScala2_13` / `isScala3` / `isJvm` / `isJs` / `isNative` / `currentScalaVersion` / `currentPlatform` / `currentJDKVersion` | see `hearth-introspection` |
| `Environment.XMacroSettings` / `Environment.typedSettings` | `List[String]` raw / `Either[String, hearth.data.Data]` parsed (`Left` if any two settings of any library conflict) |
| `Environment.isExpandedAt("File.scala:12[:34]")` | debug only one expansion |
| `Environment.loadStandardExtensions()` / `loadMacroExtensions[E]` / `...Excluding` / `...When` | `ExtensionLoadingResult` (`.toMIO(allowFailures = false)`); `loadStandardExtensions` needs `StdExtensions` in the self-type |
| `enclosingScope` (member of `MacroCommons`) / `Environment.enclosingMethodParameters` | call-site surroundings |
| `withQuotes` / `passQuotes` / `withMacroEntryCtx` | Scala 3-only (`MacroCommonsScala3`) |

## MIO (`import hearth.fp.effect.*`)

| API | Notes |
|---|---|
| `MIO(thunk)`, `MIO.pure(a)`, `MIO.fail(err)`, `MIO.defer(mio)`, `MIO.firstOf(m1, m2, ...)` | lazy, non-memoized, catches `NonFatal` |
| `>>`, `*>`, `<*`, `flatMap`, `map`, `flatTap`, `orElse`, `recover`, `attempt` | sequential (fail-fast) |
| `parMap2`, `parTuple`, `&>`, `<&`, `.parTraverse`, `.parSequence` | parallel (aggregate errors) |
| `MIO.scoped { runSafe => ... runSafe(mio) ... }` | direct style |
| `Log.info/warn/error(msg)`, `Log.namedScope(name)(mio)` | messages are by-name; scope **names are strict** (keep them cheap) |
| `MLocal(initial)(fork)(join)`, `MLocal.unsafeSharedParallel(initial)`, `.get`, `.set` | state |
| `mio.runToExprOrFail(macroName, infoRendering = DontRender, warnRendering = RenderFrom(Log.Level.Warn), errorRendering = RenderFrom(Log.Level.Error), failOnErrorLog = false, timeout = 2.seconds)((renderedLogs: String, errors: NonEmptyVector[Throwable]) => String)` | run ONCE per expansion; renderings: `DontRender`, `RenderFrom(level)`, `RenderOnly(level)` |

## Standard extensions (`this: MacroCommons & StdExtensions =>`)

`IsCollection(ic)` (`asIterable`, `foreach`, `factory`, `build`, `CtorResult`, `sizeHintForBuilder`, `asMap`), `IsMap(im)` (`key`, `value`, `pair`, `Key`, `Value`), `IsOption(io)` (`empty`, `of`, `fold`, `getOrElse`, `orElse`), `IsEither(ie)` (`left`, `right`, `fold`, ...), `IsValueType(vt)` (`unwrap`, `wrap: CtorLikeOf`, `ctors`), `CtorLikeOf.PlainValue/EitherStringOrValue/EitherThrowableOrValue/...`. See `hearth-standard-extensions`.

More: `hearth-introspection` (Type/Method/JavaBean/Position details), `hearth-expr-toolkit` (ExprCodec, semiEval/semiQuote, VarArgs, MatchCase, existentials), `hearth-micro-fp` (type classes, non-empty collections, MIO combinators).
