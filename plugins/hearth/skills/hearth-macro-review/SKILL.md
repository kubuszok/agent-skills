---
name: hearth-macro-review
description: >-
  Hearth macro review and production-readiness checklist for Scala 2.13 / Scala 3 macros built on Hearth
  (MacroCommons, MIO, Expr.quote/Expr.splice, CaseClass, Enum, ValDefsCache, summonExprIgnoring, standard
  extensions). Use when asked to review, self-review, audit or harden a macro or a type class derivation, before
  releasing a macro library, after an agent wrote or changed macro code, or when asking "is this macro production
  ready?". Covers maintainability (separation of concerns, containment of untyped trees, logs and named scopes),
  user friendliness (configuration, previewing the generated code, timing/flame graphs, controlling where derivation
  happens, actionable aggregated errors, runtime performance), correctness (type coverage, Option/default values/
  AnyVal/opaque types/named tuples/Java Beans, macro extensions, implicit priority vs recursion) and mistakes LLMs
  typically make in Hearth macros.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth macro review

Use this skill to review a macro written with Hearth: your own work (self-review) or someone else's. The output is a
review report and a production-readiness verdict. It is not a list of style nits.

Written for Hearth 0.4.5. If the project uses another Hearth version (check `build.sbt` / `build.mill` /
`//> using dep com.kubuszok::hearth`), check every API named here against
`https://scala-hearth.readthedocs.io/en/<version>/` before you flag its absence.

## How to run the review

1. **Map the macro.** Find:
   - the public entry points: the Scala 2 `def ... = macro ...` and the Scala 3 `inline def ... = ${ ... }`;
   - the per-version adapters (bridges);
   - the shared logic (traits mixing in `MacroCommons`);
   - the runtime helpers the generated code calls;
   - the tests.
   Note what the macro is: a type class derivation (instance-returning and/or inlined), a DSL, wiring, or something
   else. Some checklist items apply to derivations only.
2. **Read the code before the tests.** Then read the tests and check them against the checklist's test-coverage
   items. A behaviour that is not tested counts as not verified.
3. **Go through all three categories in [checklist.md](checklist.md):**
   - maintainability;
   - user friendliness;
   - correctness and test coverage.
   For each item record ✅ (done, with evidence: file:line or test name), ❌ (missing or wrong), ➖ (does not apply,
   with a one-line reason), or ❓ (cannot tell from the code).
4. **Hunt for the known LLM mistakes in [llm-mistakes.md](llm-mistakes.md).** Check every one, even when the code
   looks fine. These mistakes compile, often pass the happy-path tests, and break later.
5. **Compile and test if you can.** Check that the tests cover Scala 2.13 and Scala 3 (and JS/Native if the library
   publishes them). Clean the test module before you re-run: incremental compilation does not re-expand macros, so
   a stale test may pass against old generated code.
6. **Write the report** in the format below.

Do not "fix" a finding by narrowing what is tested. That includes deleting a test case, moving a shared test into a
`scala-2/` / `scala-3/` / platform-specific directory, or relaxing an assertion. If a failure comes from a Hearth bug,
say so and write a minimal reproducer (see "Hearth gaps" below).

## Report format

```
## Verdict: <Production ready | Ready with caveats | Not production ready>
<2-4 sentences: what the macro does, its biggest risk, what blocks release (if anything)>

## Blockers            (wrong code generated, crashes/OOM in the compiler, silent wrong behaviour,
                        user implicits ignored, infinite expansion, no way to diagnose failures)
- [category] finding — evidence (file:line / missing test) — suggested fix

## Should fix          (bad UX, missing configuration/preview/timing, untested supported cases, warnings
                        in user code, fail-fast errors, maintainability debt that will cause bugs)
## Nice to have
## Not applicable      (item — reason)
## Hearth gaps         (things the macro had to work around, or checklist items Hearth's docs miss)
```

Rate the macro **Not production ready** if any of these holds:
- a user-provided implicit does not override the generated logic;
- derivation recurses into itself through implicit search (infinite expansion or OOM risk);
- recursive types do not work, or need user-side tricks;
- errors are reported fail-fast with no aggregation, or do not say which field or subtype failed;
- the user cannot see what the macro generated, and nothing logs the derivation;
- the generated code emits warnings that users with `-Xfatal-warnings` must suppress;
- a supported category of types (per the library's own docs) has no tests.

## The three categories in short

The full items, with how to verify each one, are in [checklist.md](checklist.md).

**Maintainability**
- Concerns are split into dedicated methods, types and files: rules and steps have names, and no 500-line
  `deriveImpl`.
- Errors are an ADT, not strings glued together.
- Untyped trees (`UntypedExpr`/`UntypedType`, `c.Tree`, `quotes.reflect.Term`) and `asInstanceOf` juggling are
  confined to small, named helpers.
- Shared code uses Hearth's cross-platform API. Only adapters touch native API.
- `MIO` with `Log.namedScope` around every step, so a structured log can be rendered on demand.
- Generated code calls runtime helpers that are binary compatible and checked by MiMa.

**User friendliness**
- Configuration:
  - global, via namespaced `-Xmacro-settings:<lib>.<key>=...` read with `Environment.typedSettings`;
  - local, via an implicit config, annotations or the DSL;
  - both validated, with a warning or error for unknown or invalid values.
- Introspection on demand, enabled globally (a scalac option) or per expansion (an import, or a position): the
  derivation log and a preview of the generated code.
- Timing on demand (`hearth.mioBenchmarkScopes`, flame graphs) and a configurable time budget. Note that
  `runToExprOrFail` has a default `timeout` of 2 seconds.
- Type class derivation lets users control *where* expansion happens, without separate "auto" and "semiauto" APIs.
  Sanely-automatic derivation is recursive inside one expansion. A policy or opt-in scope mechanism restricts
  where it may run.
- Runtime performance is measured (JMH against hand-written code or the library being replaced), not assumed.
- Errors are actionable and aggregated: every failing field or subtype is reported in one compilation, with the
  reason and a hint on how to enable logging. No fail-fast that hides the next problem until a rerun.

**Correctness**
- Every type category the macro claims to support is tested:
  - built-in and primitive types;
  - `Option`, `Either` (`IsEither`), collections, maps (`IsMap` checked before `IsCollection`);
  - value types (`AnyVal`), opaque types, named tuples, tuples;
  - case classes (0, 1 and many fields; default values; generic);
  - sealed hierarchies, Scala 3 enums, Java enums, case objects, Scala 3 union types (if claimed);
  - Java Beans;
  - recursive types, type-parametric types, types read from another compilation unit, generic call sites.
- Macro extensions work: the standard extensions are loaded once per expansion, providers are used instead of
  hard-coded types, and an integration on the classpath (e.g. a Cats `NonEmptyList` provider) is tested.
- The configuration is tested: every option, its default, and invalid values.
- Implicits:
  - user instances override the generated logic;
  - the macro never summons its own auto-derivation (`summonExprIgnoring`, which needs Scala 2.13.17+ / 3.7.0+ -
    check that the library's documented minimum Scala versions meet it);
  - `implicit val x: TC[A] = TC.derived[A]` does not pick itself up;
  - recursion goes through the macro's internal cache (`ValDefsCache` `def`s), not implicit search;
  - Scala 3 `derives` on a generic type does not mis-derive type parameters such as `String`.

## Hearth gaps

When the review finds something Hearth should have prevented or documented:
- a missing utility;
- a checklist item missing from Hearth's [Derivation Checklist](https://scala-hearth.readthedocs.io/en/latest/derivation-checklist/);
- a bug that needs a workaround.

Report it to the user as a Hearth gap. Suggest opening an issue at https://github.com/kubuszok/hearth/issues with
a minimal reproducer. Keep the workaround in the macro, with a comment linking the issue. Never hide it.

## Related skills

- `hearth-type-class-derivation`: the rule-based derivation architecture these checks assume.
- `hearth-def-caching`: caching, recursion and multi-method instances.
- `hearth-standard-extensions`: `IsCollection`/`IsMap`/`IsOption`/`IsValueType` and providers.
- `hearth-cross-compilation-pitfalls`: the full pitfall list.
- `hearth-debugging`: logs, previews, flame graphs.
