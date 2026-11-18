# `hearth` plugin

Skills for writing your own Scala 2.13 and Scala 3 macros with [Hearth](https://github.com/kubuszok/hearth)
**0.4.5**, the macros' standard library. Covers type class derivation, DSLs, wiring and any other macro.
Docs: <https://scala-hearth.readthedocs.io/en/0.4.5/>.

Install: `/plugin install hearth@kubuszok` (Claude Code). See the [root README](../../README.md) for other harnesses.

These skills are for macro **authors**. To use libraries built on Hearth, such as Kindlings, install their own
plugin instead.

## Skills

| Skill | Covers |
|---|---|
| `hearth-getting-started` | What Hearth is, build setup (sbt / Mill / Scala CLI, cross-quotes plugin), single-version vs cross-compiled macro structure, API cheat sheet |
| `hearth-cross-quotes` | `Expr.quote` / `Expr.splice`, `Type.of`, `Type.CtorN`, Quotes scoping, fixes for common cross-quotes errors |
| `hearth-type-class-derivation` | Sanely-automatic derivation architecture: rules, `MIO`, logs, `runToExprOrFail`, implicit summoning without self-recursion |
| `hearth-case-classes-and-enums` | `CaseClass`, `Enum`, `SingletonValue`, named tuples, default values, building and matching values |
| `hearth-def-caching` | `ValDefsCache`: recursive types, multi-method instances, `parTuple` error aggregation |
| `hearth-lambda-builder` | `LambdaBuilder` for collection and option iteration, and when not to use it |
| `hearth-standard-extensions` | `IsCollection` / `IsMap` / `IsOption` / `IsEither` / `IsValueType`, and writing your own provider (integration) |
| `hearth-hkt-derivation` | Polymorphic (`F[_]`, `Alg[_[_]]`) derivation |
| `hearth-expr-parsing-dsl` | Parsing selector or path lambdas, marker DSLs, `AnonymousInstance`, `enclosingScope` |
| `hearth-cross-compilation-pitfalls` | Symptom index plus the full list of Scala 2 / Scala 3 pitfalls |
| `hearth-debugging` | Debug utilities, derivation logs, previewing generated code, flame graphs, testing macros |
| `hearth-generated-code-performance` | Fast generated code: factory instances, cache placement, compile-time evaluation, inlined built-ins |
| `hearth-macro-review` | (Self-)review and production-readiness checklist: maintainability, user friendliness, correctness, and mistakes LLMs typically make |
