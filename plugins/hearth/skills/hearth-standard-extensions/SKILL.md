---
name: hearth-standard-extensions
description: >-
  Hearth Standard Macro Extensions for Scala 2.13 / Scala 3 macros - hearth.std.StdExtensions,
  Environment.loadStandardExtensions() (load once per expansion), IsCollection / IsCollectionOf (asIterable,
  foreach, factory, build, CtorResult), IsMap (key, value, pair), IsOption, IsEither, IsValueType (unwrap, wrap),
  CtorLikeOf (PlainValue, EitherStringOrValue, ...), ProviderResult, lastUnapplyFailure, and writing your own
  StandardMacroExtension provider with META-INF/services and priority (integrations for cats NonEmptyList, refined,
  iron, newtypes, Java collections). Use when a macro must support collections, maps, options, eithers or
  wrapper/opaque types, or when publishing an integration module; also for "Extension ... was already loaded in this
  macro expansion".
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth Standard Extensions

Shared shape interfaces - `IsCollection`, `IsMap`, `IsOption`, `IsEither`, `IsValueType` - whose providers are discovered from the classpath. A macro that asks these instead of hard-coding `Iterable`/`Option` automatically supports every type some integration teaches Hearth about (Java collections, `Array`/`IArray`, opaque types, Cats `NonEmptyList`, Iron/Refined/neotype...), with no imports at the call site.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/standard-extensions/ (replace `0.4.5`).

## Using them

1. Self-type the shared trait `this: MacroCommons & StdExtensions =>` (`MacroCommonsScala2`/`MacroCommonsScala3` already mix `StdExtensions` in).
2. Load the providers **once per macro expansion**, before matching, at the top of the `MIO` program:

```scala
Environment.loadStandardExtensions().toMIO(allowFailures = false) // MIO[...]; fails with all loading errors
```

Calling it again in the same expansion re-registers nothing but scans the classpath again and emits `Extension ... was already loaded in this macro expansion, skipping re-initialization` info messages. If several entry points share a bundle (codec = encoder + decoder), guard it with a `private var loaded = false` in the bundle class, or load at the single top-level entry.

3. Match in this order (rule order matters, see `hearth-type-class-derivation`):

```scala
Type[A] match {
  case _ if Type[A].isNamedTuple => ...                   // Scala 3 single-field named tuples are opaque types
  case IsValueType(vt) =>
    import vt.{Underlying as Inner, value as isVT}        // isVT.unwrap(expr): Expr[Inner]; isVT.wrap: CtorLikeOf[Inner, A]
    ...
  case IsOption(opt) =>
    import opt.{Underlying as Item, value as isOpt}       // isOpt.fold(expr)(onEmpty, item => ...), empty, of(item)
    ...
  case IsMap(m) =>                                        // BEFORE IsCollection: Map <: Iterable
    import m.{Underlying as Pair, value as isMap}
    import isMap.{Key, Value, CtorResult}                 // brings Type[Key], Type[Value], Type[CtorResult]
    ...
  case IsCollection(c) =>
    import c.{Underlying as Item, value as isColl}
    import isColl.CtorResult
    ...
  case IsEither(e) => ...                                 // e.LeftValue, e.RightValue, e.value: IsEitherOf[A, L, R]
  case _ => ...
}
```

Collections: read with `isColl.foreach(expr)(item => Expr[Unit])` (zero-closure `while` loop, providers may optimize) or `isColl.asIterable(expr)`; build with `isColl.factory` (`Factory[Item, CtorResult]`) then `isColl.build` (`CtorLikeOf[Builder[Item, CtorResult], A]`); `isColl.sizeHintForBuilder(expr)` may give a size (can be negative at runtime - guard with `>= 0`).

`CtorLikeOf` variants (from `wrap`/`build`): `PlainValue(ctor, method)` (always succeeds), `EitherStringOrValue`, `EitherIterableStringOrValue`, `EitherThrowableOrValue`, `EitherIterableThrowableOrValue` (validated - non-empty collections, refined types). Pattern-match and handle each; a decoder must turn `Left` into its own error type.

```scala
isVT.wrap match {
  case CtorLikeOf.PlainValue(ctor, _)          => ctor(innerExpr)                                   // Expr[A]
  case CtorLikeOf.EitherStringOrValue(ctor, _) => Expr.quote(Expr.splice(ctor(innerExpr)).fold(e => fail(e), a => a))
  case other                                   => ... // report as unsupported, do not silently ignore
}
```

## Built-in coverage (0.4.5)

`IsCollection`: Scala collections, `Array`, `String` (as `Char`s), `Option` (0-1 elements), `Iterator`, `::` (non-empty `List`); JVM: Java collections, maps, `Iterable`, `Iterator`, `Enumeration`, `Dictionary`, `Stream`, `Optional`, `BitSet`; Scala 3: `IArray`. `IsOption`: `Option`, Java `Optional`. `IsEither`: `Either`, `Try`. `IsValueType`: one-field `AnyVal`s, Scala 3 opaque types with a companion smart constructor (priority -1000), JVM boxed primitives (`java.lang.Integer`, ...). Java map providers emit `java.util.Map.entry` (JDK 9+): compile users with `-release 11`.

Because `String` and `Option` are also `IsCollection`s, primitives/built-ins and options must be matched before collections.

## Diagnosing a non-match

- `IsCollection.parse[A]` returns `ProviderResult.Matched(v)` or `ProviderResult.Skipped(reasons)` (reasons per provider: `Left(throwable)` = provider failed, `Right(() => message)` = declined; in 0.4.5 the message is a lazy thunk).
- After failed `unapply`s, `IsCollection.lastUnapplyFailure` (also `IsOption`, `IsEither`, `IsValueType`, `IsMap`) holds the reasons (`null` if the last match succeeded).
- After a match, `IsValueType.lastMatchProvenance: Option[ProviderProvenance]` tells which provider matched (`isBuiltIn`).

## Writing an integration

See [writing-providers.md](writing-providers.md): a `StandardMacroExtension` registering `IsCollection`/`IsValueType`/`IsOption`/`IsEither` providers, listed in `META-INF/services/hearth.std.StandardMacroExtension`. Users only add your module to the classpath. For something that does not fit one-or-two-inner-type shapes (N type params, your own rule), define your own `MacroExtension[YourMacroTrait]` and load it with `Environment.loadMacroExtensions[YourExtension]`.

## Gotchas

- **Maps handled as collections of tuples (JSON arrays instead of objects)** -> `IsCollection` checked before `IsMap`.
- **`String` encoded as an array of chars** -> missing built-in rule before the collection rule.
- **`(name: String)` named tuple treated as a `String` wrapper** -> `IsValueType` matched it; guard with `Type[A].isNamedTuple` (always `false` on Scala 2).
- **Nothing matches at all** -> `Environment.loadStandardExtensions()` was not run in this expansion (no providers registered).
- **Third-party provider never used** -> missing/incorrect `META-INF/services/hearth.std.StandardMacroExtension`, the module is not on the *compile* classpath of the code expanding the macro, or a higher-priority provider (e.g. the opaque-type one) wins - check `lastMatchProvenance`.
- **`ProviderResult` is not an `Option`** -> no `.orElse`; use `unapply` patterns or `.toOption`.
- **`Type[Key]`/`Type[Item]` not found inside `Expr.quote`** -> import the members of the matched value (`import isMap.{Key, Value, CtorResult}`, `import c.Underlying as Item`).
- **Validation silently skipped** -> `wrap`/`build` returned `EitherStringOrValue` and only `PlainValue` was handled.

## Reference

- Docs: [Standard Extensions](https://scala-hearth.readthedocs.io/en/0.4.5/standard-extensions/), [Macro Extensions](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#macro-extensions).
- Sources: [StdExtensions.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/std/StdExtensions.scala), [built-in providers](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scala/hearth/std/extensions).
- Kindlings 0.4.0 rules using them: [FastShowPretty map/collection/option/value-type rules](https://github.com/kubuszok/kindlings/tree/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/rules).
