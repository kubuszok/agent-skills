# `hearth` plugin

Skills for writing your own Scala 2.13 and Scala 3 macros with [Hearth](https://github.com/kubuszok/hearth)
**0.4.5**, the macros' standard library. Covers type class derivation, DSLs, wiring and any other macro.
Docs: <https://scala-hearth.readthedocs.io/en/0.4.5/>.

Install: `/plugin install hearth@kubuszok` (Claude Code). See the [root README](../../README.md) for other harnesses.

Most skills are for macro **authors**. `hearth-runtime-utilities` is for anyone using Hearth's runtime utilities
(`TypeName`, `hearth.source`, versions) in ordinary code, and `hearth-debugging` also shows users of any macro
library how to preview generated code. To use libraries built on Hearth, such as Kindlings, install their own plugin.

## Skills

| Skill | Covers |
|---|---|
| `hearth-getting-started` | What Hearth is, build setup (sbt / Mill / Scala CLI, cross-quotes plugin), single-version vs cross-compiled macro structure, API cheat sheet |
| `hearth-cross-quotes` | `Expr.quote` / `Expr.splice`, `Type.of`, `Type.CtorN`, Quotes scoping, fixes for common cross-quotes errors |
| `hearth-type-class-derivation` | Sanely-automatic derivation architecture: rules, `MIO`, logs, `runToExprOrFail`, implicit summoning without self-recursion |
| `hearth-case-classes-and-enums` | `CaseClass`, `Enum`, `SingletonValue`, named tuples, default values, building and matching values |
| `hearth-def-caching` | `ValDefsCache`: recursive types, multi-method instances, `parTuple` error aggregation |
| `hearth-lambda-builder` | `LambdaBuilder` for collection and option iteration, and when not to use it |
| `hearth-introspection` | Reading types and members: `Type` predicates/navigation, `Method` details (expectations, accessors, visibility), `JavaBean`, `Position`, `Environment` context, untyped bridge |
| `hearth-expr-toolkit` | Values to code and back: `ExprCodec` (+ `derived`), `semiEval`/`semiQuote` with overrides, literal `Type`s, `VarArgs`, `FreshName`, `MatchCase`, `ValDefs`, existentials |
| `hearth-micro-fp` | `hearth.fp`: type classes and syntax, instances, `NonEmptyList`/`NonEmptyVector`/`NonEmptyMap`, `DirectStyle`, MIO combinators and running MIO |
| `hearth-standard-extensions` | `IsCollection` / `IsMap` / `IsOption` / `IsEither` / `IsValueType`, and writing your own provider (integration) |
| `hearth-macro-extensions` | Your own extension points: `MacroExtension`, `Environment.loadMacroExtensions*`, `ExtensionLoadingResult`, `META-INF/services` |
| `hearth-hkt-derivation` | Polymorphic (`F[_]`, `Alg[_[_]]`) derivation |
| `hearth-expr-parsing-dsl` | Parsing selector or path lambdas, marker DSLs, `AnonymousInstance`, `enclosingScope` |
| `hearth-cross-compilation-pitfalls` | Symptom index plus the full list of Scala 2 / Scala 3 pitfalls |
| `hearth-debugging` | `Debug` utilities (also for users of any macro library), derivation logs, previewing generated code, better printers, flame graphs |
| `hearth-generated-code-performance` | Fast generated code: factory instances, cache placement, compile-time evaluation, inlined built-ins |
| `hearth-testing` | `hearth-munit` (`Suite`, `MacroSuite`, `ScalaCheckSuite`), fixture macros returning `hearth.data.Data`, the `Data` API |
| `hearth-runtime-utilities` | Runtime utilities for any code: `TypeName`, `hearth.source` (`MethodName`, `Line`, `File`, `Location`, `Text`), version classes, what to keep in fat JARs |
| `hearth-macro-review` | (Self-)review and production-readiness checklist: maintainability, user friendliness, correctness, and mistakes LLMs typically make |
