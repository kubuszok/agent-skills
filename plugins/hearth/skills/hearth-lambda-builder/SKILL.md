---
name: hearth-lambda-builder
description: >-
  Hearth LambdaBuilder (LambdaBuilder.of1..of22, .map, .traverse, .build, .buildWith) for Scala 2.13 / Scala 3
  macros and when NOT to use it - only for lambdas whose parameter types or arity are known only during expansion,
  typically element lambdas for collection / Option / Map iteration helpers. Covers the alternatives - direct
  cross-quoted lambdas `Expr.quote { (x: T) => ... }`, helper methods with type parameters for path-dependent types,
  cached defs for multi-method instances - and the Scala 3 rule to keep built lambdas in a `def`, not a `val`. Use
  when tempted to build an `Expr[A => B]` programmatically.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth `LambdaBuilder` and its strict scope

`LambdaBuilder` builds `Expr[(A, B, ...) => R]` when the parameter types/count are only known during expansion, optionally running an effect (`MIO`) to produce the body.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#lambdabuilder (replace `0.4.5`).

## API

```scala
import hearth.fp.syntax.*     // .traverse
import hearth.fp.instances.*

// pure body
val inc: Expr[Int => Int] = LambdaBuilder.of1[Int]("a").buildWith(a => Expr.quote(Expr.splice(a) + 1))
val mul: Expr[(Int, Int) => Int] =
  LambdaBuilder.of2[Int, Int]("a", "b").map { case (a, b) => Expr.quote(Expr.splice(a) * Expr.splice(b)) }.build

// effectful body (the body's MIO errors and logs are kept; one body, so nothing to aggregate)
def elementLambda[Item: Type](derive: Expr[Item] => MIO[Expr[String]]): MIO[Expr[Item => String]] =
  LambdaBuilder.of1[Item]("item").traverse(derive).map(_.build[String])
```

`of1` ... `of22`; parameter names are prefixes (fresh names are generated). `build[R]`/`buildWith` need an implicit `Type[R]` for the result type.

## The rule: collection / Option iteration only

Use `LambdaBuilder` only for a lambda handed to a runtime helper that **iterates** (`decodeList(reader, itemFn)`, `writeMap(map, entryFn)`, `opt.map(innerFn)`), or when arity/types are genuinely dynamic. For everything else:

| Need | Use instead |
|---|---|
| Lambda with known shape | `Expr.quote { (x: T) => Expr.splice(body(Expr.quote(x))) }` |
| Body mentions a path-dependent type (`isValueType.Underlying`, a field's `Underlying`) - Scala 2 "not found: value ..." | a helper method with a regular type parameter that returns the quoted lambda: `def wrapFn[A: Type, In: Type](vt: IsValueTypeOf[A, In]): Expr[In => A] = Expr.quote { (in: In) => ... }` |
| Several methods of one instance, Scala 3 `ScopeException` with sibling splices | cached defs via `ValDefsCache` (`hearth-def-caching`) |
| A body that recursively derives against the lambda parameter | a cached `def` wrapped in a direct quoted lambda: `Expr.quote { (r: R) => Expr.splice(callDef(Expr.quote(r))) }` |
| Hot collection loops | inline `while` loop calling cached defs, or `IsCollectionOf.foreach` (no `Function1` per element) |

`LambdaBuilder` is not a fix for sibling-splice isolation - pre-building lambdas only hides the problem and adds a `Function1.apply` per call.

## Gotchas

- **Scala 3 "wrong staging level" / `ScopeException`** when a built lambda is spliced into another `Expr.quote` -> it was stored in a `val` and captured the outer `Quotes` -> use `def lambda = LambdaBuilder...build` (re-evaluated in the current scope), or keep it inside the `MIO` chain.
- **Native Scala 3 quotes inside builder callbacks** (`'{...}`/`${...}`) -> `ScopeException ... different Quotes context` -> use `Expr.quote`/`Expr.splice`, or wrap with `withQuotes`/`passQuotes`.
- **`DirectStyle[LambdaBuilder[From, *]]` not found** -> it needs `import LambdaBuilder.unsafe.*`, and `runSafe` must be called exactly once inside `scoped`.
- **Runtime cost** -> every element pays a virtual `Function1.apply`; for performance-critical codecs generate a loop instead (`hearth-generated-code-performance`).

## Reference

- Docs: [LambdaBuilder](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#lambdabuilder), [Cross Quotes known issues (`val` vs `def`)](https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/#known-issues-and-gotchas).
- Legitimate use in Kindlings 0.4.0: [circe collection encoder rule](https://github.com/kubuszok/kindlings/blob/0.4.0/circe-derivation/src/main/scala/hearth/kindlings/circederivation/internal/compiletime/rules/EncoderHandleAsCollectionRule.scala).
