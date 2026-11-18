# Hearth macro review checklist

Each item says what to check (**Check**) and how to find evidence (**Verify**). Items marked *(derivation)* apply
only to type class derivation. This checklist extends Hearth's
[Derivation Checklist](https://scala-hearth.readthedocs.io/en/latest/derivation-checklist/) and
[Best Practices](https://scala-hearth.readthedocs.io/en/latest/best-practices/).

## 1. Maintainability

**M1. Separation of concerns.**
- **Check:** Each derivation step is its own named method or type: one rule per type category (built-in, value type,
  option, map, collection, case class, enum, singleton, ...), a context type that carries the derivation state, and
  separate files for the macro logic, the adapters, the runtime helpers and the public API. Rules are ordered
  explicitly, in one place.
- **Verify:** Look for one giant method with nested `if`/`match` over type shapes. That is a finding.

**M2. Errors as an ADT.**
- **Check:** Failures are values of a sealed error type (field, subtype and reason recorded). They are rendered into
  one message at the end. They are not `String`s built at the failure site, and not exceptions thrown from deep
  inside.
- **Verify:** Search for `reportErrorAndAbort` / `reportError` / `throw` outside the top-level entry point.

**M3. Untyped code is contained.**
- **Check:** Any use of untyped trees (`UntypedExpr`, `UntypedType`, `UntypedMethod`, `c.Tree`,
  `quotes.reflect.Term`/`TypeRepr`) or `asInstanceOf` on `Expr`/`Type` sits in a small helper with a descriptive
  name and a typed signature. The rest of the code sees only `Expr[A]`/`Type[A]`.
- **Verify:** Grep for `Untyped`, `asUntyped`, `.asInstanceOf[Expr`, `quotes.reflect`, `c.universe` in shared code.

**M4. Shared code is platform-agnostic.**
- **Check:** Shared logic uses the Hearth API (`Expr.quote`/`Expr.splice`, `Type.of`, `CaseClass`, `Enum`, ...).
  Scala-version-specific code lives only in the adapters or in clearly separated helpers. Native API is used where
  Hearth has no equivalent, not out of habit.
- **Verify:** Compare `src/main/scala` with `scala-2` / `scala-3`. Check whether logic is duplicated between the
  versions.

**M5. Structured, lazy logging.**
- **Check:** The derivation runs in `MIO`. Every rule attempt, match, yield, cache hit and recursive descent is
  wrapped in `Log.namedScope(...)` with `Log.info`/`Log.warn`. Messages are by-name, so they cost nothing when
  logging is off; `namedScope` names are strict `String`s, so they must not call `prettyPrint`. The log tells the whole story of an expansion without adding `println`s.
- **Verify:** Count `Log.namedScope` uses per rule. Look for `println` or `Environment.reportInfo` used for
  debugging.

**M6. Runtime helpers are stable.**
- **Check:** The generated code calls public runtime helpers and constructors. MiMa checks them. Generated code
  does not reach into `private[lib]` internals. Accessibility differs between the expansion site and the library,
  and calls that compile inside the library can fail in user code.
- **Verify:** Find what the quoted code references. Check MiMa settings in the build. Check whether any test calls
  the macro from a package outside the library.

**M7. No accidental complexity.**
- **Check:** `LambdaBuilder` is used only to build lambdas over collection or option elements. Multi-method
  instances use def-caching. No hand-rolled caches keyed by strings (see [llm-mistakes.md](llm-mistakes.md)).

## 2. User friendliness

**U1. Configuration exists and is validated.**
- **Check:**
  - Global settings use a namespaced `-Xmacro-settings:<lib>.<key>=<value>`, parsed with
    `Environment.typedSettings`. Never JVM `-D` properties.
  - Local configuration uses an implicit config value, annotations, or DSL methods. It is evaluated at compile
    time where possible (e.g. by reading the config `Expr`), so the generated code does not do config lookups at
    runtime.
  - Unknown or invalid values give a warning or error that names the key and the accepted values.
- **Verify:** Find the settings parsing. Pass a wrong value in a test and check the message.

**U2. Settings work on Scala 2 and Scala 3.**
- **Check:** List-valued settings are not split on `,`. Both Scala 2 and Scala 3 split `-Xmacro-settings` values on
  commas, so a value cannot contain `,`. Use `|` (as Hearth's own `hearth.cross-quotes.logging` does) or `;`, or
  separate options.
- **Check:** A `Left` from `Environment.typedSettings` (any two settings of any library conflict) is reported, not
  silently turned into "no settings" with `.toOption`.

**U3. Preview of the generated code, on demand.**
- **Check:** Users can see the derivation log and the final expression (pretty-printed) without editing the macro.
  Both of these work:
  - globally: `-Xmacro-settings:<lib>.logDerivation=true`;
  - per scope or per expansion: an importable marker implicit (e.g. `import mylib.debug.logDerivation`),
    optionally restricted to a position with `Environment.isExpandedAt("File.scala:12")`.
  The marker is defined outside any companion, so it is never found implicitly by accident.
- **Verify:** Find the marker type and the setting key. Check that a test or doc shows the output.

**U4. Timing and a time budget.**
- **Check:**
  - The documentation tells users how to profile expansion: `-Xmacro-settings:hearth.mioBenchmarkScopes=true` and
    `hearth.mioBenchmarkFlameGraphDir=<dir>`, which produce `.speedscope.json` flame graphs.
  - The `timeout` passed to `runToExprOrFail` (default 2 seconds) is configurable, e.g.
    `<lib>.timeoutSeconds=30` read with `.asInt` (`30s` would parse as a `String` you must parse yourself), with a
    sensible default. On loaded CI machines a too-tight default turns into flaky
    builds.

**U5. Control over where derivation happens** *(derivation)*.
- **Check:**
  - There is one API, no separate "auto" and "semiauto" imports with different semantics.
  - `TC.derived[A]` is recursive within one expansion, and also usable as an implicit/given.
  - Users who want instances only in chosen places get an opt-out or opt-in mechanism (a policy setting, allowed
    scopes, or an explicit import), with a compile error telling them to define the instance.
  - The docs say where to put an instance so it is derived once (companion `implicit val` / `given`).

**U6. Inline entry point** *(derivation)*.
- **Check:** Besides the instance-returning `derived`, there is an inlined variant (`TC.encode(value)`-style) that
  shares the core logic. It uses a user-provided instance for the root type if one exists.

**U7. Runtime performance is measured.**
- **Check:**
  - JMH benchmarks compare the generated code with hand-written code or the library being replaced.
  - Primitives and built-ins are handled inline, without an instance per field.
  - Summoned instances are cached as `lazy val`s inside the instance, not re-summoned or re-allocated per call.
  - Recursive or large logic is split into `def`s (the JVM 64 kB method limit).
  - Final instances are built with a factory method or lambda, not one anonymous class per expansion (class count
    and metaspace).
  - Benchmarks include a wide type (dozens of fields) and the runtime-config path, not only small models.

**U8. Actionable, aggregated errors.**
- **Check:**
  - All failing fields and subtypes are reported in one compilation: `parTraverse`/`parTuple` over fields and
    subtypes, and `parTuple` across the bodies of a multi-method instance.
  - Each error names the type path (`Outer.field: Inner`), the reason (no public constructor, unsupported type,
    missing implicit plus what was tried), and how to fix it or enable logging.
  - Nothing aborts at the first failure.
- **Verify:** Write a type with two unsupported fields and one bad subtype. The error must list all three.

**U9. No warnings in user code.**
- **Check:** The generated code is warning-free under `-Xfatal-warnings`/`-Werror` and common linters, or is
  annotated with `@nowarn` and `@SuppressWarnings`. Scala 3 enum singletons are compared with `eq` rather than
  with `isInstanceOf`, which emits an "unchecked type test" warning at the expansion site.
- **Verify:** The test build enables strict warnings.

**U10. Documentation for users.**
- **Check:** Supported types, every configuration option with its default, how to debug, and known differences from
  any library this one replaces.

**U11. Generated methods stay small and linear.**
- **Check:** No generated method of a 100-field case class exceeds 8000 B (Scala 2.13 and 3, compile-time and runtime
  config); the code grows by a constant per field; statically known config is resolved in the macro.
- **Verify:** A size guard test exists; `javap -c -p` the largest method; items 44-52 of
  [llm-mistakes.md](llm-mistakes.md).

## 3. Correctness and test coverage

**C1. Built-in types first** *(derivation)*.
- **Check:**
  - Primitives, `String`, `BigDecimal`/`BigInt`, `java.time`, `UUID` and the like are handled by a dedicated
    built-in rule.
  - That rule runs before the collection rule. Otherwise `String` falls into `IsCollection` as `Iterable[Char]`.
    This shows up with Scala 3 `derives` on generic types, which auto-derives for the type parameters.
- **Verify:** A test for each built-in type, and a `derives` test on `case class Box[A](a: A)` with `A = String`.

**C2. Optional types.**
- **Check:** The rule uses `IsOption` (not only `scala.Option`). The semantics are decided and tested: a missing
  field, an explicit `null`, a `None` with a default, a nested `Option[Option[A]]`, and an `Option` of a derived
  type. `Either`-like types go through `IsEither` (`Either`, `Try`, integrations such as Cats `Validated`) and are
  tested if supported.

**C3. Default values.**
- **Check:** Case class defaults (including those depending on type parameters or on other parameters) are used or
  ignored according to the configuration. This is tested both ways, including generic case classes and defaults in
  classes from another compilation unit.

**C4. Value types and opaque types.**
- **Check:**
  - `AnyVal` wrappers and opaque types (Scala 3) go through `IsValueType`, so wrap/unwrap is consistent and
    integrations (refined, iron, newtypes) work.
  - Smart-constructor failures are reported, not swallowed.
  - The value-type rule is guarded with `Type[A].isNamedTuple` on Scala 3, because named tuples are opaque types
    (for every arity) that the opaque-type `IsValueType` provider may match.

**C5. Collections and maps.**
- **Check:** `IsMap` is checked before `IsCollection`, since every `Map` is an `Iterable`. Arrays (which need a
  `ClassTag`), Java collections if supported, and empty collections are tested.

**C6. Products.**
- **Check:** Case classes with 0, 1 and 22+ fields, multiple parameter lists, private constructors (a clear error),
  generic case classes, tuples, Scala 3 named tuples, and Java Beans (if applicable; `JavaBean` utilities). Huge
  case classes (100 fields, with defaults and `Option`s) compile, and their generated methods stay small (U11).

**C7. Sums.**
- **Check:**
  - Sealed traits and classes (nested hierarchies), case objects, Scala 3 enums (parameterless and
    parameterized), Java enums, and `scala.Enumeration` if claimed.
  - Singletons go through `SingletonValue`.
  - The order of subtypes is deterministic on both Scala versions.
  - Subtypes with type parameters are handled.
  - Scala 3 union types, if claimed: runtime-distinguishable members, and a clear error
    (`Type[A].unionRefusalReason`) for members that need a user-provided `TypeTest`.

**C8. Recursion.**
- **Check:**
  - `case class Tree(children: List[Tree])` and mutually recursive types work with a single `TC.derived[Tree]`
    and no user tricks.
  - Recursion is detected by the type (the `ValDefsCache` key compares types with `=:=`), not by a printed name.
  - It is also tested with the recursive types defined in another module or compilation unit (read from the
    classpath / TASTy).

**C9. Implicit priority without runaway recursion** *(derivation)*.
- **Check:**
  - (a) A user-provided implicit for a nested type (and for the root, in inline mode) overrides the generated logic.
  - (b) Implicit search excludes the macro's own auto-derivation methods, plus the parent library's auto-derivation
    when the type class extends it. Use `Type[TC[A]].summonExprIgnoring(...)`. Otherwise you get infinite
    expansion or a compiler OOM. `summonExprIgnoring` throws on Scala older than 2.13.17 / 3.7.0: the library's
    minimum Scala versions must meet that, or older versions need a different design.
  - (c) `implicit val tc: TC[A] = TC.derived[A]` does not resolve to itself, which compiles to `null` or a cycle.
  - (d) Recursion inside the derivation goes through the cache, not through implicit search.
  - (e) Summoned instances are cached as `lazy val`s.
- **Verify:** A test for each of (a) to (e).

**C10. Generic contexts.**
- **Check:** Derivation inside a generic method (`def f[A: TC]`), with abstract type members, path-dependent types,
  and type aliases. It fails with a clear error when the type is not concrete enough.

**C11. Macro extensions.**
- **Check:**
  - The standard extensions are loaded once per macro expansion, through a single guarded call to
    `Environment.loadStandardExtensions()`. Loading them on every rule invocation re-scans providers and, from the
    second call on, emits an "already loaded" compiler info that takes the single info slot per position, hiding the
    rendered derivation log; never loading them means integrations are silently ignored.
  - Rules use `IsCollection`/`IsMap`/`IsOption`/`IsEither`/`IsValueType` instead of hard-coding `List`/`Map`/
    `Option`.
  - If the library offers its own extension point, its `MacroExtension` is discovered from the classpath and
    tested.
- **Verify:** A test with an integration provider on the test classpath, e.g. a Cats `NonEmptyList` provider or a
  test-local provider.

**C12. Configuration is tested.**
- **Check:** Every option is tested, at its default and non-default values, with invalid values, and combined with
  per-field annotations, including precedence: annotation > local config > global setting.

**C13. Cross-version and cross-platform tests.**
- **Check:**
  - The same shared tests run on Scala 2.13 and Scala 3, and on JS/Native if published.
  - Scala-3-only features (enums, opaque types, named tuples, union types) are tested in `scala-3` test sources,
    and only those.
  - Failures caused by Hearth or compiler bugs stay visible: a reproducer plus a tracked issue, not a moved test.

**C14. Multi-method instances** *(derivation)*.
- **Check:**
  - Every method body is derived at the outer level using a shared `ValDefsCache`, and each method calls cached
    `def`s by name from inside its splice. On Scala 3, sibling `Expr.splice`s get separate `Quotes`.
  - `cache.toValDefs.use` wraps the whole `new TC[A] { ... }`. If it wraps a single method body instead, the
    cached `lazy val`s are re-initialised on every call.
  - Bodies are derived with `parTuple` so errors aggregate. The `ValDefsCache` MLocal is shared across
    parallel branches; any *other* `MLocal` that one branch writes and another reads must stay sequential, because
    parallel branches fork it.

**C15. Golden and round-trip tests** *(serialization-like macros)*.
- **Check:** The wire format is pinned by golden tests. Round trips are tested. Behaviour that differs from the
  library being replaced is documented and tested.

**C16. Stress tests** *(derivation)*.
- **Check:** Tests derive, on Scala 2.13 and 3:
  - a ~100-field case class with defaults and `Option`s (methods under 8000 B, see U11);
  - a sealed hierarchy with 100+ subtypes, and a chain of 20+ nested case classes;
  - one field type repeated dozens of times: derived once through the cache, compile time stays linear;
  - recursion: direct (`Tree(children: List[Tree])`), mutual (`A -> B -> A`), through `Option`/`Map`/`Either`/an
    integration type, through a sealed trait, generic (`Tree[A]`), with a user-provided instance inside the cycle, and
    with the types defined in another compilation unit;
  - for HKT derivation: the same recursive shapes, e.g. `Functor` for `Tree[A](value: A, children: List[Tree[A]])`.
- **Verify:** Each of these compiles within the default timeout and round-trips (or behaves) correctly at runtime.
