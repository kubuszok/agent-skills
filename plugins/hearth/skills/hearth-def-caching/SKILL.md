---
name: hearth-def-caching
description: >-
  Hearth ValDefsCache def-caching for Scala 2.13 / Scala 3 macros - ValDefBuilder.ofLazy / ofDef1..ofDef22,
  ValDefsCache.mlocal, forwardDeclare, buildCachedWith, get0Ary..get22Ary, isBuilt, toValDefs.use placement,
  recursive types, multi-method type class instances (Hash, codecs with encode + decode) and parTuple error
  aggregation; ValDefs.createVal / createVar. Fixes "ScopeException: Expression created in a splice was used outside
  of that splice", "buildCachedWith('...'): key+signature already built", Scala 2 "not found: value x$macro$N",
  unused cached defs warnings, 64KB "Method too large", and lazy vals re-initialized on every call. Use when
  generated code needs reusable/recursive helper defs or an instance with several methods.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth def-caching with `ValDefsCache`

Generate each case-class/enum body once as a local `def` (and each summoned implicit once as a `lazy val`), reference it by name wherever needed, and emit all definitions in one block around the final expression. This keeps generated code small (the JVM's 64KB method limit), makes recursive types work, and is **the** fix for Scala 3 sibling-splice isolation in multi-method instances.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#valdefscache (replace `0.4.5`).

## API

```scala
val cache: MLocal[ValDefsCache] = ValDefsCache.mlocal          // shared across parallel MIO branches; `mlocal` is a def -
                                                               // call it ONCE per expansion and pass this value everywhere

val defB = ValDefBuilder.ofDef1[A, String](s"show_${Type[A].shortName}", "value") // def show_Foo(value: Foo): String
val lazyB = ValDefBuilder.ofLazy[Show[A]](s"instance_${Type[A].shortName}")       // lazy val instance_Foo: Show[Foo]

cache.forwardDeclare(key, defB)                     // MIO[Unit]: callable before you START building it (optional)
cache.buildCachedWith(key, defB) { case (self, valueArg) => body } // MIO[Unit]; forward-declares itself, so recursive
                                                    // calls inside `body` already resolve; body: Expr[String] from the def's own param
cache.get1Ary[A, String](key)                       // MIO[Option[Expr[A] => Expr[String]]] - builds a call by name
cache.get0Ary[Show[A]](key)                         // for vals / lazy vals
defB.isBuilt(cacheSnapshot, key)                    // Boolean, on a snapshot from cache.get
cacheSnapshot.toValDefs.use(_ => resultExpr)        // { def ...; lazy val ...; resultExpr }
```

`ofDefN` takes the def name prefix then optional parameter name prefixes (strings convert to `FreshName`); names are made fresh automatically. Entries are keyed by `(key, argument Types, return Type)` compared with `=:=`, so one constant key like `"cached-show"` serves every type `A` as long as the signature mentions `A`.

Every forward-declared entry must be built before `toValDefs`, otherwise it fails with `Definitions were forward declared, but not built`.

## Single-method derivation with recursion

```scala
def deriveRecursively[A: Ctx]: MIO[Expr[String]] = {
  val key = "cached-show"
  ctx[A].cache.get1Ary[A, String](key).flatMap {
    case Some(call) => MIO.pure(call(ctx[A].value))           // already derived, or recursion -> call by name
    case None =>
      val defB = ValDefBuilder.ofDef1[A, String](s"show_${Type[A].shortName}", "value")
      for {
        _ <- MIO.scoped { runSafe =>   // buildCachedWith forward-declares the def, so recursion inside resolves to a call
               runSafe(ctx[A].cache.buildCachedWith(key, defB) { case (_, value) =>
                 runSafe(deriveViaRules[A](using ctx[A].nest(value))) // body uses the def's OWN parameter
               })
             }
        call <- ctx[A].cache.get1Ary[A, String](key)
      } yield call.get(ctx[A].value)
  }
}
// at the entry point: cache <- ctx.cache.get; then cache.toValDefs.use(_ => result)
```

Leaf types (primitives, types with a user implicit) need no def - inline them and only cache structural types.

## Multi-method instances (Scala 3 sibling splices)

Each `Expr.splice` in `Expr.quote { new TC[A] { def m1 = splice(...); def m2 = splice(...) } }` gets its own `Quotes` on Scala 3; deriving inside them and sharing results fails with `ScopeException: Expression created in a splice was used outside of that splice`. Recipe:

1. Run **all** derivation before the quote (in the outer `MIO.scoped` block), with **one** shared `ValDefsCache.mlocal`; each method body becomes a cached def (`buildCachedWith`, which forward-declares it).
2. Derive independent method bodies in parallel with `parTuple` so users see errors of all of them at once.
3. Get the call builders with `getNAry`, snapshot the cache, and wrap the **whole** instance expression with `toValDefs.use`.
4. Splices contain only calls to those builders - name references, valid in any `Quotes`.

```scala
MIO.scoped { runSafe =>
  val cache = ValDefsCache.mlocal
  val x0: Expr[A] = Expr.quote(null.asInstanceOf[A])  // placeholders, replaced by the defs' own params
  runSafe {
    Environment.loadStandardExtensions().toMIO(allowFailures = false) >>
      deriveHash[A](using HashCtx(x0, cache)).parTuple(deriveEqv[A](using EqCtx(x0, x0, cache)))
  }
  val hashCall: Expr[A] => Expr[Int]               = runSafe(cache.get1Ary[A, Int]("cached-hash")).get
  val eqvCall: (Expr[A], Expr[A]) => Expr[Boolean] = runSafe(cache.get2Ary[A, A, Boolean]("cached-eqv")).get
  runSafe(cache.get).toValDefs.use { _ =>
    Expr.quote {
      HashFactories.instance[A](
        (a: A) => Expr.splice(hashCall(Expr.quote(a))),
        (x: A, y: A) => Expr.splice(eqvCall(Expr.quote(x), Expr.quote(y)))
      )
    }
  }
}
```

Generated shape: `{ def hash_Foo(value: Foo): Int = ...; def eqv_Foo(x: Foo, y: Foo): Boolean = ...; HashFactories.instance[Foo](a => hash_Foo(a), (x, y) => eqv_Foo(x, y)) }`. (`HashFactories` is your runtime helper - see `hearth-generated-code-performance`.) If a rule might not populate the key (e.g. a primitive handled inline), check `defB.isBuilt(snapshot, key)` and, if false, build a fallback def under its own key - do not rely on `getNAry` returning `Some`, which is also true for forward-declared-only entries.

## Gotchas

- **`buildCachedWith('key'): key+signature already built`** (a `HearthRequirementError`, `NonFatal`, so it reaches your `runToExprOrFail` failure renderer as an MIO error starting with `Hearth requirement failed:`) -> building the same key+signature twice (e.g. two fields of the same type) -> check `defB.isBuilt(snapshot, key)` (or `getNAry` returning `Some`) first and reuse.
- **`Definitions were forward declared, but not built`** at `toValDefs` -> a `forwardDeclare`d key was never built (e.g. a rule failed or took another path) -> build every declared key, or do not forward-declare it.
- **Scala 2 `not found: value x$macro$12`** -> the def body references a value bound by the wrapping quote / outer ctx, but defs are emitted outside it -> pass that value as a def parameter (bump `ofDefN` arity) and build a fresh ctx from the def's params inside `buildCachedWith`.
- **`ScopeException` on Scala 3** -> derivation still runs inside a splice of a multi-method quote -> hoist it before the quote (recipe above).
- **Cached `lazy val`s re-initialized on every call / slow instances** -> `toValDefs.use` wraps only one method body (defs become locals of that method) -> wrap the entire instance expression.
- **"private method ... is never used" warnings / duplicated defs** -> `toValDefs.use` called per method, each copy containing all defs -> one `toValDefs.use` around the whole result.
- **Cache key collisions** -> different types sharing a key with an erased signature (`Any => Any`) collide: `buildCachedWith` fails with "already built", or `getNAry` returns the other type's def -> include the type in the key (`s"decode:${Type[B].plainPrint}"`), never `prettyPrint` (ANSI colours differ for the same type read from source vs classpath, so recursion is missed).
- **Exponential compile time** with many repeated field types -> types re-derived instead of cached; make sure every structural rule goes through the cache and the cache is shared (`ValDefsCache.mlocal` is shared across `parTraverse`/`parTuple` branches by design).
- **`parTuple` and your own state** -> `MLocal(initial)(fork)(join)` values are forked per branch, so a branch never sees the other's writes; derive sequentially when one derivation reads state another writes (e.g. a decoder body and a schema of the same value).
- **`Method too large` / 64KB, or methods over 8000 B (never JIT-compiled)** -> large ADTs inlined into one expression -> every case class / enum body as its own def. A wide case class also needs per-field local defs and flat statements: no `try`/`if` inside the constructor's argument list, no nesting per field (see `hearth-generated-code-performance`, section 5).

## `ValDefs` for local vals/vars

`ValDefs.createVal[A](expr, "name")`, `createVar[A](init, "name")` (gives `(getter, setter)`), `createLazy`, `createDef`; compose with `map2`/`tuple`/`traverse`/`sequence` (or direct style) and finish with `.use { refs => Expr[B] }`. `ValDefs` has no `Parallel` instance, so `parMap2`/`parTraverse` do not compile on it. More in `hearth-expr-toolkit`. Use typed `createVar`s instead of an `Array[Any]` when accumulating decoded fields (no boxing).

## Reference

- Docs: [ValDefs](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#valdefs), [ValDefBuilder](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#valdefbuilder), [ValDefsCache](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#valdefscache), [MLocal shared parallel state](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#shared-parallel-state-mlocalunsafesharedparallel).
- Kindlings 0.4.0: two-method instance [cats `HashMacrosImpl`](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/compiletime/HashMacrosImpl.scala); five-method codec derived with `parTuple` [jsoniter `CodecMacrosImpl`](https://github.com/kubuszok/kindlings/blob/0.4.0/jsoniter-derivation/src/main/scala/hearth/kindlings/jsoniterderivation/internal/compiletime/CodecMacrosImpl.scala); per-type helper `getHelper`/`setHelper` in [FastShowPrettyMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/FastShowPrettyMacrosImpl.scala).
- Related: `hearth-lambda-builder` (why not to use it here), `hearth-generated-code-performance`.
