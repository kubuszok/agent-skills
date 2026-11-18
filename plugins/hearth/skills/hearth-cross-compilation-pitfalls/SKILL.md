---
name: hearth-cross-compilation-pitfalls
description: >-
  Index of known pitfalls when cross-compiling Hearth macros for Scala 2.13 and Scala 3 - sibling Expr.splice
  isolation (ScopeException), path-dependent `Underlying` types and `??` inside Expr.quote (Scala 2 "not found:
  value ..."), Type.of bootstrap cycles, summonExprIgnoring vs infinite expansion / OOM, IsMap before IsCollection,
  IsValueType intercepting named tuples, Scala 3 enum isInstanceOf "cannot be checked at runtime", phantom type
  params inferred as Nothing / Any, upcast only widens, primaryConstructor strict argument types, Array ClassTag,
  prettyPrint cache keys, unused implicit Type warnings, MacroExtension ClassTag erasure, classOf of abstract types,
  java.lang.Class shadowing. Use when a Hearth macro compiles on one Scala version but fails (at compile, expansion
  or runtime) on the other, or before reviewing cross-compiled macro code.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth cross-compilation pitfalls

A symptom-first index of things that bite when one Hearth macro serves Scala 2.13 and Scala 3. Details, causes and fixes are in [pitfalls.md](pitfalls.md).

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/#limitations (replace `0.4.5`).

## Always do

- Test **both** Scala versions (and JS/Native if published) - many bugs below appear on one only. Keep failing tests in shared test sources; Scala-version-specific test dirs are only for version-specific features (Scala 3 enums, named tuples, opaque types).
- Clean the macro module **and** the modules expanding it after changing macro code: incremental compilation does not re-expand macros (stale expansions look like "my fix did nothing") and can report spurious cyclic-reference errors until a clean build.
- Compile tests with `-Xfatal-warnings` and many linters (users will), and on Scala 3 with `-Xcheck-macros` to catch Quotes-scope and tree-type bugs.

## Index

| # | Symptom | Platform | Topic |
|---|---|---|---|
| 1 | `ScopeException: Expression created in a splice was used outside of that splice` | Scala 3 | [sibling splices](pitfalls.md#1-sibling-exprsplice-isolation) |
| 2 | `not found: value param` / `value elem` / generated `x.Underlying` | Scala 2 | [path-dependent types in quotes](pitfalls.md#2-path-dependent-types-inside-exprquote) |
| 3 | reification errors mentioning `this.??` / `Expr_??` | Scala 2 | [macro-internal types in quotes](pitfalls.md#3-macro-internal-values-inside-exprquote) |
| 4 | `forward reference to value`, `Infinite loop in function body`, null `Type` at runtime | both | [Type.of bootstrap cycle](pitfalls.md#4-typeof-bootstrap-cycles) |
| 5 | compiler hangs / OOM / StackOverflow / runtime null; `...relies on ... available since Scala 2.13.17` / `3.7.0` | both | [self-summoning](pitfalls.md#5-self-summoning-summonexprignoring) |
| 6 | maps as arrays of pairs, `String` as chars | both | [extractor order](pitfalls.md#6-extractor-and-rule-order) |
| 7 | named tuple treated as a value type | Scala 3 | [named tuple vs IsValueType](pitfalls.md#6-extractor-and-rule-order) |
| 8 | `the type test for E.A cannot be checked at runtime` at user call site | Scala 3 | [enum singletons](pitfalls.md#7-scala-3-parameterless-enum-cases-and-isinstanceof) |
| 9 | type param inferred as `Nothing` (2.13) / `Any` (3) | both | [phantom params](pitfalls.md#8-phantom-type-parameters) |
| 10 | `Upcasting can only be done to type proved to be super type!` | both | [upcast](pitfalls.md#9-upcast-only-widens) |
| 11 | constructor rejects `Expr[Any]` argument | both | [strict argument types](pitfalls.md#10-constructor-arguments-are-type-checked) |
| 12 | duplicated helpers / recursion not detected | both | [prettyPrint keys](pitfalls.md#11-never-key-anything-by-prettyprint) |
| 13 | "is never used" for implicit `Type` | both | [unused Type implicits](pitfalls.md#12-unused-implicit-type-warnings) |
| 14 | `Not found: value data` with newtype aliases | Scala 2 | [runtime helpers](pitfalls.md#13-types-that-cannot-be-written-in-a-scala-2-quote) |
| 15 | `object Trees is not a member of package scala.reflect.api` | Scala 2 | [refined types in nested quotes](pitfalls.md#13-types-that-cannot-be-written-in-a-scala-2-quote) |
| 16 | tree-type invariant failure under `-Xcheck-macros` | Scala 3 | [cast inside quotes](pitfalls.md#14-cast-inside-the-quote) |
| 17 | `ClassCastException` from `asInstanceOf` | JVM | [outer class not erased](pitfalls.md#15-asinstanceof-checks-the-outer-class) |
| 18 | duplicated/unused cached defs, slow instances | both | [toValDefs.use scope](pitfalls.md#16-valdefscache-wrapping-scope) |
| 19 | `class type required but M found` | both | [classOf of abstract type](pitfalls.md#17-classof-for-an-abstract-type-parameter) |
| 20 | `found ...this.Class[_], required Class[_]` | both | [Class shadowing](pitfalls.md#18-class-is-hearths-classa) |
| 21 | custom `MacroExtension` never applied | both | [ClassTag erasure](pitfalls.md#19-macroextension-with-intersection-types) |
| 22 | `Array` building fails without `ClassTag` | both | [arrays](pitfalls.md#20-arrays-need-a-classtag) |
| 23 | error at `<macro>:line:col` | Scala 2 | [Cross Quotes printing](pitfalls.md#21-errors-inside-generated-quasiquotes) |
| 24 | macro call in a generic helper sees abstract `A` | both | [concrete types](pitfalls.md#22-macros-need-concrete-types-at-the-call-site) |
| 25 | `Type` pattern with backticks never matches | Scala 3 | [Type equality](pitfalls.md#23-type-equality) |
| 26 | list-valued `-Xmacro-settings` value loses its tail / prefix | both | [commas in settings](pitfalls.md#24-commas-in--xmacro-settings) |
| 27 | `recursive value x needs type` / `recursive val` at the user's call site | Scala 2 | [names are not hygienic](pitfalls.md#25-scala-2-quotes-are-not-hygienic) |
| 28 | `object XRuleImpl is not a member of package ...` (`note: trait XRuleImpl exists, but it has no companion object`) | Scala 2 | [macro-internal types in quotes](pitfalls.md#3-macro-internal-values-inside-exprquote) |

## Reference

- [Cross Quotes limitations and known issues](https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/#limitations), [FAQ](https://scala-hearth.readthedocs.io/en/0.4.5/faq/).
- Related: `hearth-cross-quotes`, `hearth-def-caching`, `hearth-standard-extensions`, `hearth-debugging`.
