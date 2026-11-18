# Hearth cross-compilation pitfalls - details (Hearth 0.4.5)

Each entry: symptom, platform, cause, fix. Index in [SKILL.md](SKILL.md).

## 1. Sibling `Expr.splice` isolation

**Scala 3.** `ScopeException: Expression created in a splice was used outside of that splice` (often only with `-Xcheck-macros`) or wrong owners. Every `Expr.splice` in one `Expr.quote` has its own `Quotes`; an `Expr` (or a `lazy val`/cached value) first built inside one splice cannot be used in another.

Fix: derive everything before the quote, with one shared `ValDefsCache`, turn each method body into a cached `def`, wrap the whole instance with `cacheState.toValDefs.use`, and in each splice only call the def-builder function (`hearth-def-caching`). Helper `Type`s kept in fields: `Type.Lazy`. Scala 3-only code may use `withMacroEntryCtx`. Do **not** "fix" it with `LambdaBuilder`. Builder results spliced later must be `def`s, not `val`s.

## 2. Path-dependent types inside `Expr.quote`

**Scala 2.** `import param.tpe.Underlying as Field; Expr.quote(x.asInstanceOf[Field])` generates code referring to `param`, which does not exist at the expansion site: `not found: value param` (or generated code containing `param.Underlying`).

Fix: a helper with regular type parameters owning the quote:

```scala
def castTo[F: Type](e: Expr[Any]): Expr[F] = Expr.quote(Expr.splice(e).asInstanceOf[F])
import param.tpe.Underlying as Field
castTo[Field](expr)
```

Same for element types from `Type.CtorN.unapply` and for `IsValueType`/`IsCollection` inner types: providers and rules should build quotes in `mk[A, E](AT: Type[A], ET: Type[E])`-style helpers.

## 3. Macro-internal values inside `Expr.quote`

**Scala 2.** Values of type `??`, `Expr_??`, `Type[...]`, your ctx or error ADT referenced inside a quote (even inside an `Expr.splice` block) make the reifier fail (`Option[MyMacros.this.??]` ...). Compute them in a `val` before the quote and only splice `Expr`s.

The same holds for the *types* of lambdas created inside a splice: a helper such as
`dispatch(cursorFor: ChildReader[A] => Expr[Cursor])` called inside `Expr.splice` with a lambda whose parameter is a
class nested in your rule (`ChildReader`) fails at the user's call site with
`object MyRuleImpl is not a member of package ...` (`note: trait MyRuleImpl exists, but it has no companion object`).
Pass plain values instead (e.g. `Boolean => Expr[Cursor]`), and look up the macro-internal data outside the splice.

## 4. `Type.of` bootstrap cycles

**Both.** `implicit val X: Type[X] = Type.of[X]` asks the native summoner (`weakTypeTag`/`scala.quoted.Type.of`) for a `Type[X]` while that very implicit is in scope. Since Hearth 0.4.0 the val being defined is excluded for statically known types, but it still fails when `X` is abstract (nothing to materialize from) and in some provider code.

Symptoms: `forward reference to value ...`, Scala 3 `Infinite loop in function body`, `null` `Type` at runtime.

Abstract `X` fails to compile (no `Type[X]` to materialize it from). Fix: `[A: Type]` context bounds; `Type.of` in a separate object/scope (`object Types { def ShowOf[A: Type] = Type.of[Show[A]] }`) then `implicit val s: Type[Show[A]] = Types.ShowOf[A]`; non-implicit `val`s passed explicitly; inside splices pass `Type.of[A]` directly as the argument. In a Scala 3 provider do not `import platformCommons.{*, given}`.

## 5. Self-summoning (`summonExprIgnoring`)

**Both.** Searching for `TC[A]` with plain `summonImplicit` finds your own `implicit def derived`/`inline given` (or a parent library's auto-derivation), expanding the macro inside itself: hangs, `OutOfMemoryError`, diverging implicits. With `implicit val tc: TC[X] = TC.derived[X]` it can also find `tc` itself -> runtime `null`/StackOverflowError.

Fix: `Type[TC[A]].summonExprIgnoring(ignored*)` with `ignored = Type.of[TC.type].unsortedMethodsNamed("derived").map(_.asUntyped)` (plus the parent library's derivation methods), and skip the search for the root type in the `derived` entry point.

**Version requirement:** `summonExprIgnoring`/`Expr.summonImplicitIgnoring` needs Scala **2.13.17+ / 3.7.0+** in the module where the macro expands. On older compilers (incl. 2.13.16 and 3.3 LTS) it throws `HearthRequirementError: Expr.summonImplicitIgnoring on Scala 2 relies on c.inferImplicitValueIgnoring method, which is available since Scala 2.13.17` (Scala 3: `... Implicits.searchIgnoring method, which is available since Scala 3.7.0`). Either raise the library's minimum Scala version (Kindlings requires 2.13.18 / 3.8), or check `Environment.currentScalaVersion` and, on older compilers, avoid having an auto-derivation implicit that a plain `summonExpr` could find (e.g. make `derived` non-implicit there). Hearth has no ignoring search for older compilers.

## 6. Extractor and rule order

**Both / Scala 3.** `Map <: Iterable` so `IsCollection` matches maps -> check `IsMap` first. `String` and `Option` are also `IsCollection`s -> built-ins and options before collections. Scala 3 named tuples are opaque types (for every arity), which the built-in opaque-type `IsValueType` provider may unwrap -> guard the value-type rule with `if (Type[A].isNamedTuple)` (always `false` on Scala 2). Singletons are rejected by `CaseClass.parse` -> singleton rule before the case-class rule.

## 7. Scala 3 parameterless enum cases and `isInstanceOf`

**Scala 3.** Generated `y.isInstanceOf[E.A]` for `enum E { case A, B }` warns "the type test for E.A cannot be checked at runtime" **at the user's call site** (fatal with `-Werror`; `@nowarn` in macro sources does not help): parameterless cases are erased to `E`. Affects code comparing two values (Eq, Order, diffs). Hearth's own `Enum.matchOn`/`parMatchOn` already avoid it (they emit `case x @ EnumValue` via `MatchCase.eqValue` for parameterless enum cases and Java enums). Only hand-written type tests need a fix: `SingletonValue.unapply(Type[Child])` / `Expr.singletonOf[Child]` and compare with `eq` (or `MatchCase.eqValue`); keep `isInstanceOf` only for case-class children.

## 8. Phantom type parameters

**Both.** A type param not constrained by arguments is inferred as `Nothing` on Scala 2 and `Any` on Scala 3. Guard at the entry point:

```scala
if (Type[A] =:= Type.of[Nothing] || Type[A] =:= Type.of[Any])   // =:= accepts any Type[B], no cast needed
  Environment.reportErrorAndAbort(s"type parameter inferred as ${Type[A].prettyPrint}; pass it explicitly")
```

## 9. `upcast` only widens

**Both.** `expr.upcast[B]` asserts `A <:< B` ("Upcasting can only be done to type proved to be super type!") and needs both `Type`s. Narrow with `.asInstanceOf[B]` inside `Expr.quote`.

## 10. Constructor arguments are type-checked

**Both.** Calling constructors/methods through `Method` (`fold`, `ApplyValues`) or `CaseClass.construct` checks each argument's type against the parameter: `Expr[Any]` for an `Int` field is rejected. Keep each field's own type through transformations (helper `def adapt[Field: Type](e: Expr[Field]): Expr[Field]` that casts inside the quote).

## 11. Never key anything by `prettyPrint`

**Both.** `prettyPrint` contains ANSI colours that differ for the same type written at the call site and read from the classpath. A cache key / "in progress" set built from it misses recursion and emits duplicated helpers. Use `plainPrint`, or rely on `ValDefsCache` comparing signature types with `=:=`, or `Type.Cache`. Keep `prettyPrint` for logs.

## 12. Unused implicit `Type` warnings

**Both.** An implicit `Type[X]` needed only by a quote is flagged "is never used" (fatal with `-Xfatal-warnings`). Put such declarations in a named `def` annotated `@scala.annotation.nowarn("msg=is never used")` (on a `def`, not a `val` or block).

## 13. Types that cannot be written in a Scala 2 quote

**Scala 2.** Newtype aliases implemented as `object X { type Type[A] }` (e.g. Cats `NonEmptyChain`, `NonEmptyMap`, `NonEmptySet`) -> `not found: value data`; refined/structural types built in nested quotes -> `object Trees is not a member of package scala.reflect.api`. Fix: a runtime helper object (MiMa-checked) taking/returning `Any`; the quote only calls it and casts.

## 14. Cast inside the quote

**Scala 3 (`-Xcheck-macros`).** `(Expr.quote(helper(x)): Expr[Any]).asInstanceOf[Expr[Iterable[E]]]` fails the tree-type invariant. Write `Expr.quote(helper(x).asInstanceOf[Iterable[E]])`.

## 15. `asInstanceOf` checks the outer class

**JVM.** Only type arguments are erased: `validated.asInstanceOf[Either[E, A]]` throws `ClassCastException`, `left.asInstanceOf[Either[E, Int]]` does not. Erasure tricks must keep the outer class.

## 16. `ValDefsCache` wrapping scope

**Both.** `toValDefs.use` must wrap the outermost expression referencing the cached definitions (the whole instance). Wrapping each method separately duplicates every def (unused-method warnings) and turns `lazy val`s into per-call locals.

## 17. `classOf` for an abstract type parameter

**Both.** `classOf[M]` in a quote for an abstract macro type param fails ("class type required but M found" / "M is not a class type"); `Expr(classOf[...])` lifting differs between versions. Summon `scala.reflect.ClassTag[M]` during expansion and use `Expr.quote(Expr.splice(ct).runtimeClass)`. `Type.classOfType[A]` gives a `java.lang.Class` at compile time only for classes already on the classpath.

## 18. `Class` is Hearth's `Class[A]`

**Both.** Inside `MacroCommons`, unqualified `Class` is Hearth's class view. Write `java.lang.Class` in generated code (prefer `java.lang.Class[Any]` over `[?]`).

## 19. `MacroExtension` with intersection types

**Both.** `MacroExtension[A & B & C]` checks `ctx` against a single erased class (the `ClassTag` of the intersection keeps only one component), so applicability checks are wrong. Extend `MacroExtension[MacroCommons & StdExtensions]` (or `StandardMacroExtension`) and match `ctx` against your trait inside `extend`.

## 20. Arrays need a `ClassTag`

**Both.** Building `Array[T]` (also via `IsCollection` for arrays) summons `ClassTag[T]` during expansion. For macro-internal sequences use `List`; for generic user types make sure a `ClassTag` is available or report a clear error.

## 21. Errors inside generated quasiquotes

**Scala 2.** Errors located at `<macro>:line:col` ("expected ")" but found ...", `not found: value rassoc$1`) come from the quasiquote Cross Quotes printed from your quote. Enable `-Xmacro-settings:hearth.cross-quotes.logging=true` (or a `|`-separated file list) to see it, simplify the quote (fewer nesting levels, logic in helpers/runtime methods, avoid deep right-associative chains), and report a minimal reproducer to kubuszok/hearth.

## 22. Macros need concrete types at the call site

**Both.** `def helper[A](a: A) = MyTC.show(a)` expands the macro for an abstract `A`. Expand with concrete types, or have the helper take an implicit `MyTC[A]`.

## 23. `Type` equality

**Scala 3.** `scala.quoted.Type` does not override `equals`; `==`, `Set[Type[?]]`, `Map` keys and backtick patterns misbehave (they work on Scala 2, hiding the bug). Use `=:=`/`<:<`, `Type.Cache`, or `plainPrint` keys.

## 24. Commas in `-Xmacro-settings`

**Both.** Scala 2 and Scala 3 both split `-Xmacro-settings:a=1,b=2` on commas into separate settings, so a value cannot contain `,` (the tail loses its `lib.` prefix). Separate list items with `|` (as Hearth's own `hearth.cross-quotes.logging` does) or `;`, or pass several `-Xmacro-settings` options. Also note that `Environment.typedSettings` parses every setting of every library into one tree and is `Left` if any two conflict (`a=1` and `a.b=2`, or a key given twice) - report that `Left` instead of silently ignoring your settings.

## 25. Scala 2 quotes are not hygienic

**Scala 2.** Names of `val`s declared inside `Expr.quote` are used as written. When a spliced expression refers to a
quoted variable of the same name, the expansion captures it:

```scala
Expr.quote {
  cursor.asObject match {
    case Right(obj) => Expr.splice(readField(Expr.quote(obj)))  // the outer `obj`
  }
}
// with readField(objExpr) = Expr.quote { val obj = Expr.splice(objExpr); ... }
// Scala 2 expands it to `val obj = obj` -> "recursive value obj needs type" at the user's derivation site
```

Scala 3 renames the binders and compiles the same code, so the bug only shows up in the Scala 2.13 build (often only
for some shapes, e.g. fields with defaults). Give quoted local `val`s and the variables you splice in distinct names.
