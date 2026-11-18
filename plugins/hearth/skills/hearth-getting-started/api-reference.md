# Hearth 0.4.5 API cheat sheet

Members of `MacroCommons` (use inside `trait X { this: MacroCommons => ... }`) unless an import is shown. Verified against the Hearth 0.4.5 sources; when in doubt check [the sources](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scala/hearth) or [Basic Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/).

## Types

| API | Result | Notes |
|---|---|---|
| `Type[A]` | `Type[A]` | summons the implicit `Type[A]` (context bound `[A: Type]`) |
| `Type.of[A]` | `Type[A]` | Cross Quotes; creates a `Type` from a literal type |
| `Type.Ctor1.of[F]` ... `Type.Ctor22.of[F]` | `Type.CtorN[F]` | `.apply[A]` builds `Type[F[A]]`, `.unapply(tpe)` extracts args as `??` |
| `Type.Ctor2.of[Either].setA[String]` / `.setLast[Int]` | `Type.Ctor1[...]` | partial application (apply from the back) |
| `Type.CtorN.fromUntyped[F](untyped)` / `ctor.asUntyped` | | convert to/from `UntypedType` |
| `Type.CtorK1.of[Alg]` | | for `Alg[_[_]]` (kind `(* -> *) -> *`) |
| `Type.decompose1[A]` / `decompose2[A]` | `Option[(Ctor1[AnyK1], ??)]` | split `G[X]` when `G` is unknown statically |
| `Type.Lazy(Type.of[X])` | `Type.Lazy[X]` | helper `Type` kept in a field; converts to `Type[X]` implicitly |
| `new Type.Cache[F]` | | per-type memo keyed by `=:=` (`get`, `put`, `getOrPut`) |
| `Type[A].prettyPrint` / `plainPrint` / `shortName` / `fqcn` | `String` | `prettyPrint` has ANSI colors - logs only, never keys |
| `Type[A] <:< Type[B]`, `Type[A] =:= Type[B]` | `Boolean` | never use `==` on `Type`s |
| `Type[A].isCaseClass` / `isCaseObject` / `isCaseVal` / `isSealed` / `isJavaEnum` / `isOpaqueType` / `isNamedTuple` / `isUnionType` / `isTuple` / `isFunction` / `isAbstract` / `isPrimitive` ... | `Boolean` | |
| `Type.typeArguments[A]`, `Type[A].parents` / `baseClasses` | `List[??]` | |
| `Type[A].directChildren` / `exhaustiveChildren` | `Option[...]` of `??<:[A]` | sealed / enum / union children |
| `Type[A].primaryConstructor` / `constructors` / `methods` / `unsortedMethods` / `unsortedMethodsNamed(n)` | `Method`s | prefer `unsorted*` for lookups |
| `Type[A].companionObject` / `pseudoCompanionObject` | `Option[Expr_??]` | |
| `Type[A].annotations` / `annotationsOfType[Ann]` / `typeAnnotations` / `hasAnnotationOfType[Ann]` | | |
| `Type[A].summonExpr` / `summonExprIgnoring(methods*)` | `SummoningResult[A]` | `.toOption`, `.toEither`, `.isDefined`, `.fold(...)` |
| `Type[A].as_??` | `??` | existential; `import t.Underlying as X` brings `Type[X]` |
| `Type.StringCodec`, `IntCodec`, ... | `TypeCodec` | literal types: `case Type.StringCodec(value) =>` |

## Expressions

| API | Result | Notes |
|---|---|---|
| `Expr(value)` | `Expr[A]` | lift via `ExprCodec` (primitives, String, collections, Option, Either, ...) |
| `Expr.quote { ... }` / `Expr.splice(e)` | | Cross Quotes; splice only inside quote |
| `Expr.summonImplicit[A]` / `summonImplicitIgnoring[A](methods*)` | `SummoningResult[A]` | |
| `expr.prettyPrint` / `plainPrint` / `prettyAST` / `plainAST` | `String` | |
| `expr.upcast[B]` | `Expr[B]` | asserts `A <:< B`; needs `Type[A]` and `Type[B]` |
| `expr.as_??` | `Expr_??` | `import e.{Underlying as T, value as v}` |
| `expr.semiEval` | `Either[NonEmptyVector[String], A]` | evaluate config-like expressions at compile time |
| `expr.annotated[scala.annotation.nowarn]()` | `Expr[A]` | `{ @nowarn val x = expr; x }` |
| `expr.suppressUnused` | `Expr[Unit]` | |
| `Expr.singletonOf[A]` | `Option[Expr[A]]` | |
| `MatchCase.typeMatch[A]()` / `eqValue(expr)` / `typeTestMatch[A, B]()` / `MatchCase.matchOn(scrutinee)(cases)` | | build `match` expressions |
| `ValDefs.createVal/createVar/createLazy/createDef(expr, name)` then `.use { ref => ... }` | `Expr[B]` | local definitions with fresh names |
| `ValDefBuilder.ofVal/ofVar/ofLazy[T](name)`, `ofDef0..ofDef22[A..., R](name, argNames...)` | | build/caching of `def`s (see `hearth-def-caching`) |
| `ValDefsCache.empty` / `ValDefsCache.mlocal` | | cache of definitions; `.toValDefs.use(_ => expr)` |
| `LambdaBuilder.of1[A](name)` ... `of22` + `.map`/`.traverse` + `.build[R]` / `.buildWith(f)` | `Expr[A => R]` | collection/Option iteration lambdas only |
| `DestructuredExpr.parse(expr)` / `extractFieldPath[S, A](lambda)` / `extractLambda(expr)` | | semantic expression parsing |

## Classes and methods

| API | Result |
|---|---|
| `CaseClass.parse[A]` / `Enum.parse[A]` / `SingletonValue.parse[A]` / `NamedTuple.parse[A]` / `JavaBean.parse[A]` / `AnonymousInstance.parse[A]` | `ClassViewResult[...]` (`.toOption`, `.toEither`) |
| `CaseClass.unapply(tpe)`, `Enum.unapply(tpe)`, `SingletonValue.unapply(tpe)` | `Option[...]` |
| `cc.caseFieldValuesAt(expr)` | `ListMap[String, Expr_??]` |
| `cc.construct[F](param => F[Expr_??])` / `cc.parConstruct[F](...)` | `F[Option[Expr[A]]]` |
| `cc.primaryConstructor` / `cc.caseFields` / `cc.copyMethod()` | `Method` / `List[Method]` / `Option[Method.OnInstance.Of[A]]` |
| `enumm.matchOn[F, B](expr)(matched => F[Expr[B]])` / `parMatchOn` | `F[Option[Expr[B]]]` |
| `enumm.directChildren` / `exhaustiveChildren` | children as `??<:[A]` |
| `sv.singletonExpr` | `Expr[A]` |
| `method.name` / `isImplicit` / `isCaseField` / `totalParameters` / `knownReturning` / `asUntyped` | |
| `method.fold(onInstance, onTypes, onValues)` / `foldF[F](...)` | `Either[String, Expr_??]` |
| `Method.OnInstance` -> `ApplyTypes` -> `ApplyValues` -> `Result[R]#build()` | builder chain |
| `param.name` / `index` / `tpe` / `hasDefault` / `defaultValue` / `annotations` / `isByName` / `isVararg` / `isImplicit` | |
| `Annotations.decodedConstructorArguments(ann)` | `Option[List[Either[String, Any]]]` |

## Environment

| API | Notes |
|---|---|
| `Environment.reportInfo/reportWarn/reportError(msg[, pos])` | only the first info/warn per position is shown |
| `Environment.reportErrorAndAbort(msg[, pos])` | `Nothing` |
| `Environment.currentPosition` / `isScala2_13` / `isScala3` / `isJvm` / `isJs` / `isNative` | |
| `Environment.XMacroSettings` / `Environment.typedSettings` | `-Xmacro-settings` raw / parsed as `hearth.data.Data` |
| `Environment.isExpandedAt("File.scala:12[:34]")` | debug only one expansion |
| `Environment.loadStandardExtensions()` / `loadMacroExtensions[E]` / `...Excluding` / `...When` | `ExtensionLoadingResult` (`.toMIO(allowFailures = false)`) |
| `enclosingScope` (member of `MacroCommons`) / `Environment.enclosingMethodParameters` | call-site surroundings |
| `withQuotes` / `passQuotes` / `withMacroEntryCtx` | Scala 3-only (`MacroCommonsScala3`) |

## MIO (`import hearth.fp.effect.*`)

| API | Notes |
|---|---|
| `MIO(thunk)`, `MIO.pure(a)`, `MIO.fail(err)`, `MIO.defer(mio)`, `MIO.firstOf(m1, m2, ...)` | lazy, non-memoized, catches `NonFatal` |
| `>>`, `*>`, `<*`, `flatMap`, `map`, `flatTap`, `orElse`, `recover`, `attempt` | sequential (fail-fast) |
| `parMap2`, `parTuple`, `&>`, `<&`, `.parTraverse`, `.parSequence` | parallel (aggregate errors) |
| `MIO.scoped { runSafe => ... runSafe(mio) ... }` | direct style |
| `Log.info/warn/error(msg)`, `Log.namedScope(name)(mio)` | by-name messages |
| `MLocal(initial)(fork)(join)`, `MLocal.unsafeSharedParallel(initial)`, `.get`, `.set` | state |
| `mio.runToExprOrFail(name, infoRendering, warnRendering, errorRendering, failOnErrorLog, timeout)((logs, errors) => msg)` | run ONCE per expansion; `timeout` defaults to 2 s; renderings: `DontRender`, `RenderFrom(Log.Level.Info)`, `RenderOnly(level)` |

## Standard extensions (`this: MacroCommons & StdExtensions =>`)

`IsCollection(ic)` (`asIterable`, `foreach`, `factory`, `build`, `CtorResult`, `sizeHintForBuilder`, `asMap`), `IsMap(im)` (`key`, `value`, `pair`, `Key`, `Value`), `IsOption(io)` (`empty`, `of`, `fold`, `getOrElse`, `orElse`), `IsEither(ie)` (`left`, `right`, `fold`, ...), `IsValueType(vt)` (`unwrap`, `wrap: CtorLikeOf`, `ctors`), `CtorLikeOf.PlainValue/EitherStringOrValue/EitherThrowableOrValue/...`. See `hearth-standard-extensions`.
