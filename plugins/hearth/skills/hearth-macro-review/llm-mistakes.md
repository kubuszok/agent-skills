# Mistakes LLMs make in Hearth macros

Check the reviewed code for each mistake below, whether or not it seems relevant. These mistakes compile and often
pass happy-path tests. Each entry gives the symptom, the cause, and what the correct version looks like.

## Summoning and recursion

1. **Plain implicit summoning inside a derivation.**
   - **Symptom:** infinite macro expansion, a compiler `OutOfMemoryError`, or a very slow compilation.
   - **Cause:** the macro summons `TC[Field]`, and implicit search finds the macro's own `derived` (or the parent
     library's auto-derivation), which expands the macro again.
   - **Correct:** `Type[TC[B]].summonExprIgnoring(<own auto-derivation methods>, <parent library auto methods>)`.
     Recurse through the internal cache. `summonExprIgnoring` needs Scala 2.13.17+ / 3.7.0+ where the macro expands
     and throws on older compilers - a library supporting 2.13.16 or 3.3 LTS cannot rely on it.
2. **Recursion by implicit search instead of the cache.**
   - **Symptom:** recursive types need `lazy val`, `Lazy`, or user-defined instances. Errors lose the path.
   - **Correct:** walk the type internally, and use `ValDefsCache` `def`s keyed by type.
3. **The self-referencing semi-auto instance.**
   - **Symptom:** `implicit val tc: TC[A] = TC.derived[A]` compiles to a reference to itself. The result is a
     runtime `null`, a `NullPointerException` or a stack overflow.
   - **Correct:** exclude the type being derived (`TC[A]` itself) from implicit search for instance-returning
     derivation, but not for the inline variant.
4. **Cache or recursion keys built from `prettyPrint`.**
   - **Symptom:** a recursive type is expanded twice, or helpers are duplicated. This happens only when the type
     comes from another compilation unit.
   - **Cause:** `prettyPrint` contains ANSI colours that depend on how the type was read.
   - **Correct:** let `ValDefsCache` compare types (`=:=`), or use `plainPrint` in string keys. Keep `prettyPrint`
     for messages only.
5. **No built-in rule before the collection rule.**
   - **Symptom:** a `String` is encoded as an array of chars. It surfaces with Scala 3 `derives` on a generic type,
     because the compiler derives instances for the type parameters too.
   - **Correct:** a `HandleAsBuiltInTypeRule` placed before the collection rule.
6. **The user-implicit rule placed too late.**
   - **Symptom:** users cannot override the encoding of a field type.
   - **Correct:** the "use an implicit when available" rule runs first, before the built-in, value-type and
     collection rules.

## Rule ordering and type categories

7. **`IsCollection` checked before `IsMap`.** A `Map` is an `Iterable`, so maps get encoded as sequences of pairs.
   Check `IsMap` first.
8. **`IsValueType` without a named-tuple guard (Scala 3).** Named tuples are opaque types (any arity), which the
   opaque-type `IsValueType` provider may match. Guard it with `if (Type[A].isNamedTuple)` before the value-type match.
9. **`isInstanceOf` on parameterless Scala 3 enum cases.**
   - **Symptom:** an "unchecked type test" warning at every expansion site, which breaks `-Werror`. Users cannot
     suppress it with `@nowarn` in their own source.
   - **Correct:** use `Enum[A].matchOn`, which emits `case x @ EnumValue` (via `MatchCase.eqValue`) for parameterless
     enum cases and Java enums, or `MatchCase.eqValue` / `Expr.singletonOf[A]` with `eq` in hand-written code.
10. **Hard-coded `List`/`Option`/`Map`.** Matching on concrete types instead of `IsCollection`/`IsOption`/`IsMap`
    silently ignores every integration module (Cats collections, refined, iron, newtypes).
11. **Standard extensions loaded never, or on every rule call.**
    - Never loaded: integrations do nothing.
    - Loaded on every call: compilation slows down, and the "already loaded" info message from the second call takes
      the single info slot, so the derivation log is not shown.
    - **Correct:** load them once per expansion behind a guard.
12. **`ProviderResult` treated as an `Option`.** Provider results carry the reasons why a provider did not match.
    Keep them, so errors can explain the skipped providers.

## Splices, caching and multi-method instances

13. **`LambdaBuilder` as a fix for Scala 3 `ScopeException`.**
    - **Symptom:** sibling `Expr.splice`s inside one `Expr.quote` each get their own `Quotes`. Reusing an `Expr`
      built in one splice in another throws `ScopeException`.
    - **Wrong fix:** wrapping everything in `LambdaBuilder`. That is a misdiagnosis.
    - **Correct:** derive every body at the outer level into a shared `ValDefsCache`, call the cached `def`s by name
      inside the splices, and wrap the whole instance in `cache.toValDefs.use`. Use `LambdaBuilder` only for
      collection or option element lambdas.
14. **`toValDefs.use` around a method body instead of the whole instance.** It compiles and works, but the cached
    `lazy val`s and helper `def`s become local to the method and are re-created on every call. That costs runtime
    performance.
15. **Sequential `for` over the method bodies of a multi-method instance.** It reports only the first failing body.
    Use `parTuple`. The `ValDefsCache` is shared between parallel branches, but other `MLocal` state is forked, so keep
    branches sequential only when one reads state that another writes.
16. **Expressions computed at runtime that could be computed at compile time.** For example, calling
    `config.fieldNameMapper(name)` in generated code when the config `Expr` can be evaluated during expansion.

## Errors and UX

17. **`Environment.reportErrorAndAbort` deep inside a rule.** This is fail-fast: users fix one error per
    compilation. Return a failed `MIO` and let `parTraverse`/`parTuple` aggregate. Report once, at the entry point.
18. **Error messages without a path or a reason.** A message like "Cannot derive TC for A" is not actionable. Name
    the field or subtype path, what was tried, and how to enable the derivation log.
19. **`println` debugging left in, or `Environment.reportInfo` called several times.** Only the first `reportInfo`
    per position is shown, on both Scala 2 and 3. Use `Log` with named scopes and render the log once.
20. **The timeout left at the default.** `runToExprOrFail` uses a 2-second timeout by default. It is not
    configurable unless you expose it, and it fails builds on slow CI machines.
21. **Comma-separated list settings.** Both Scala 2 and Scala 3 split `-Xmacro-settings` values on commas.
    Use `|` or `;` as separators.

22. **`runToExprOrFail` called more than once, or nested.**
    - Run the `MIO` program once, at the entry point.
    - A nested call, for example through a helper that is itself a macro entry, re-enters the timeout machinery and
      fails with `HearthAssertionError: ... MIO timeout is already set`.
23. **The `LogDerivation`-style marker implicit defined in a companion object.** It is then always in implicit
    scope, and logging is on everywhere. Define it in a separate `debug` object that users import.
24. **Settings keys without a namespace.** `-Xmacro-settings` are visible to every macro on the classpath. Prefix
    every key with the library name (`mylib.logDerivation`).
25. **`prettyPrint` evaluated eagerly in logs and skip reasons.** Rendering types costs time on every expansion. Pass
    messages by-name (`Log.info(...)` already takes a by-name argument, but `Log.namedScope(name)` does not), and use
    `skippedLazily` for provider skip reasons.

## Quoting traps

26. **Path-dependent or existential values used inside `Expr.quote`.** For example `x.Underlying` from an extractor,
    or a `??`/`Expr_??` taken apart inside the quote. Destructure outside the quote: `import x.Underlying as B`, or
    a helper method with a type parameter `[B: Type]`. Splice only fully typed values.
27. **`implicit val A: Type[A] = Type.of[A]` for an abstract `A`.** It fails to compile (there is no `Type[A]` to
    materialize it from; older Hearth resolved it to the val itself). Take the `Type` from the macro's type parameter
    or from a decomposition (`CaseClass`, `Is*` extractors). For a concrete type (`Type.of[Foo]`) it is fine.
28. **Builder results stored in `val`s and spliced into a different quote on Scala 3.** Each quote has its own
    scope. Rebuild inside the quote, or call a cached `def` by name.
29. **Casting the `Expr` without proof.** `expr.asInstanceOf[Expr[B]]` is fine only after the type was proven (`=:=`/
    `<:<`, an extractor match, a `CaseClass`/`Is*` decomposition). Otherwise cast inside the generated code
    (`Expr.quote { Expr.splice(expr).asInstanceOf[B] }`) or use `upcast` when widening is enough. Do not pass
    `Expr[Any]` where a constructor expects concrete argument types.
30. **Comparing `Type`s with `==` or a backticked pattern.** Use `=:=` (or `<:<`). Structural equality of type
    representations is not type equality.
31. **Witness types used as lambda parameter types in erased HKT derivation (Scala 3).** These produce a
    `checkcast` to the witness type at runtime and a `ClassCastException`. Keep witness types out of the parameter
    types of generated lambdas.

## Cross-compilation traps

32. **The cross-quotes plugin missing on Scala 3, or added with `%%%`.** It is a compiler plugin for Scala 3 only.
    Add it for the Scala 3 build only, as `compilerPlugin("com.kubuszok" % "hearth-cross-quotes_3" % version)` or
    the equivalent in your build tool.
33. **Kindlings helpers assumed to be Hearth API.** `DerivationTimeout`, `DerivationPolicy`,
    `ensureStandardExtensionsLoaded` and `LogDerivation` are Kindlings conventions built on Hearth, not part of it.
    Re-implement the idea (see the `hearth-type-class-derivation` skill) or verify the name in Hearth's source.

34. **`classOf[M]` for an abstract macro type parameter.** It is impossible. Use the `Type`, or a `ClassTag`
    summoned at the call site.
35. **`Class` inside macro code.** Hearth's cake has a `Class[A]` type that shadows `java.lang.Class`. Write
    `java.lang.Class` explicitly.
36. **`Type.of[A]` inside an extension's own initialisation.** This causes bootstrap cycles. Use the patterns in the
    `hearth-cross-compilation-pitfalls` skill.
37. **`Expr.upcast` used to narrow.** It only widens.
38. **`Array` without a `ClassTag`.** Building arrays needs a `ClassTag` in the generated code.
39. **Prototyping in raw `quotes.reflect` / `c.universe` "and porting later".** This rebuilds corner-case handling
    that Hearth already has (type parameters on subtypes, defaults, opaque types, Java enums, ...). Start with
    Hearth, and drop to the native API in small contained helpers only where needed.
40. **Invented API names.** Hearth's API is large and similar names exist. Verify every method against the docs,
    the source, or `cellar`/Metals before using it, especially `CaseClass`, `Enum`, `ValDefsCache` and
    `summonExprIgnoring` signatures.

## Testing and process

41. **Tests "fixed" by narrowing.** Shared tests moved to `scala-2/` / `scala-3/` / `scalajvm/`, cases deleted, or
    assertions loosened, to get CI green. Keep failing tests visible, write a reproducer, and track the bug (in
    Hearth if it's Hearth's).
42. **Results trusted after an incremental build.** Incremental compilation does not re-expand macros in unchanged
    test files. Clean the test module after changing the macro, otherwise the tests check the old generated code.
43. **Only happy-path, same-file fixtures.** Missing: types from another compilation unit, generic call sites,
    2.13 and 3 together, invalid configuration, compile-error tests that assert the message (all errors, with
    paths).

## Generated-code shape and cost

These compile, pass behavioural tests and oracles, and look fine on a 5-field benchmark. They surface as "Method too
large" on wide types, or as methods over 8000 B that HotSpot never JIT-compiles. Kindlings 0.4.0 shipped all of them
while adding upstream-parity behaviour (see the `hearth-generated-code-performance` skill, section 5).

44. **A runtime `if` on configuration the macro already evaluated.**
    - **Symptom:** both branches emitted for every field or subtype; the method doubles in size.
    - **Cause:** new behaviour added as `if (config.x) ... else ...` inside the quote, next to code that already uses
      the compile-time config value.
    - **Correct:** branch in the macro on the evaluated value and emit only the branch that applies. Emit the runtime
      `if` only on the path where the config cannot be evaluated.
45. **`try`/`if`/`match` inside an argument list.**
    - **Symptom:** quadratic growth in the number of fields; a huge StackMapTable on Scala 2.13.
    - **Cause:** a field's fallback logic written as a constructor argument, a `::` element or a builder argument.
      The compiler spills every argument evaluated before a `try`, and needs a frame listing all live values for
      each branch.
    - **Correct:** decode each field in its own local `def` (`ValDefs.createDef`), bind results with statements, and
      pass plain values to the constructor. Write optional entries with statements (`builder.put(...)` under an
      `if`), not with an `if` inside the list being built.
46. **Per-field nesting.** A chain of `flatMap`s, a fold that wraps each field around the previous ones, or a `match`
    per field around the rest. Generate flat statements: `val rK = if (rK-1 ok) fieldK else rK-1` for fail-fast,
    `val eK = merge(eK-1, rK)` (with `null` = no failure) for accumulating.
47. **A decoder expression used as a "type witness".** For example `unsafeCast(value, <decoder expr>)` to get the
    field type. The decoder is evaluated (allocated) again on every call. Cast the value to the field type instead.
48. **One method with a runtime `failFast` flag.** Every field gets both modes. Emit two methods and choose once.
49. **Local `lazy val`s in per-call code.** Each one allocates a `LazyRef` and synchronizes on every call. Use a
    local `def`, a `val`, or a `lazy val` of the instance.
50. **Per-call work that belongs to the instance or to compile time.** Schemas, name lists or alias lists, regexes
    (`String.replaceAll`), expected-key `Set`s and field decoders rebuilt inside the method that runs per call. Cache
    them on the instance, or compute them in the macro.
51. **The same splice emitted several times.** A dispatch lambda or field body spliced into two or three places
    duplicates its whole bytecode. Bind it once (a `def` or a `val`) and refer to it.
52. **No size check.** Only small fixtures in tests and benchmarks, so quadratic growth is never seen. Add a guard
    test that derives for a 100-field fixture and fails when any generated method exceeds 8000 B, on both Scala
    versions, with a compile-time and a runtime config.
