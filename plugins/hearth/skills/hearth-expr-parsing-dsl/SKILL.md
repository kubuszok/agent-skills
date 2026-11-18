---
name: hearth-expr-parsing-dsl
description: >-
  Hearth for non-derivation Scala 2.13 / Scala 3 macros - parsing selector lambdas and DSLs with DestructuredExpr
  (parse, MethodCall, AppliedInstance / AppliedTypes / AppliedValues, receiver, extractFieldPath, extractLambda,
  skipContextualWrappers, ValDefinition / LocalReference, findReferences), marker methods with @compileTimeOnly and
  invariant implicit evidence (`_.a.b.each.when[T]`, quicklens/optics-like modify), MatchCase for non-exhaustive
  matches, calling methods via the Method builder chain, AnonymousInstance for mocks / proxies (`new Trait {
  override ... }`), enclosingScope / Enclosure / enclosingMethodParameters for MacWire-like dependency injection.
  Use when building optics, query builders, mocking, DI wiring or grammar DSLs with Hearth.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth for DSLs, optics, mocks and DI

Macros that read user code (selector lambdas, blocks) or the call site's surroundings and generate code - no rule chain or derivation cache needed.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#destructuredexpr (replace `0.4.5`).

## Module shape

- Shared `private[mylib] trait XMacrosImpl { this: MacroCommons => def x[...](...): Expr[...] }`.
- Per-platform bridge: Scala 2 `class XMacros(val c: blackbox.Context) extends MacroCommonsScala2 with XMacrosImpl`; Scala 3 `class XMacros(q: Quotes) extends MacroCommonsScala3(using q), XMacrosImpl` + object forwarding methods.
- Per-platform syntax: Scala 2 `implicit class ... { def x(...): R = macro ... }`; Scala 3 `extension (inline obj: T) inline def x(...): R = ${ ... }`. Take selector lambdas as `inline` parameters on Scala 3 so the tree is visible.
- Errors: `Environment.reportErrorAndAbort(msg, node.position.get)` at the offending sub-expression (or collect them in `MIO` if there can be several).

## Parsing expressions: `DestructuredExpr`

```scala
DestructuredExpr.extractFieldPath[Person, String](selector) match {   // `_.address.street` only
  case Right(path) => path.fieldNames                                  // List("address", "street")
  case Left(err)   => Environment.reportErrorAndAbort(err)
}

def steps(node: DestructuredExpr): List[String] = node match {         // general walk
  case mc: DestructuredExpr.MethodCall => mc.receiver.fold(List.empty[String])(steps) :+ mc.method.name
  case _                               => Nil
}
DestructuredExpr.extractLambda(selector) match {
  case Right(info) => steps(info.body)                                 // info.params: List[Lambda.Param]
  case Left(err)   => Environment.reportErrorAndAbort(err)
}
```

- Nodes are plain classes without extractors, so match them with type patterns (`case mc: DestructuredExpr.MethodCall => mc.method / mc.applied / mc.receiver`): `MethodCall` (`method: Method`, `applied: List[MethodCall.Applied]`) where `Applied` is `AppliedInstance` (`.value`), `AppliedTypes` (`.typeArgs: List[??]`), `AppliedValues` (`.args: List[DestructuredExpr]`); plus `Lambda`, `Lambda.ParamRef`, `Literal(value)`, `Singleton`, `Block`, `ValDefinition`, `LocalReference`, `Import`, `LocalDefinition`, `Varargs`, `NonDestructurable`. Every node has `tpe: ??`, `toUntypedExpr`, `position`.
- `mc.receiver` normalizes `implicit class` (`Ops(x).each`) and Scala 3 `extension` (`each(x)`) forms to `x`.
- Implicit evidence and `using` arguments appear as extra `AppliedValues`; on Scala 3 an `extension [C] def when[T <: C]` has **two** `AppliedTypes` clauses - take the last one's last argument.
- Context-function DSLs (`Ctx ?=> A => B`): `DestructuredExpr.skipContextualWrappers(node)` peels the contextual lambda / binding block (no-op on Scala 2).
- Block DSLs: `ValDefinition`/`LocalReference` share the same `LocalBinding` instance - compare with `eq`, never by name; `binding.isExternal` for vals defined outside the parsed block; `node.findReferences(bindings)` searches the whole tree; `lambda.unusedParams`.
- Recover a precisely typed expression: `node.toUntypedExpr.asTyped[node.tpe.Underlying].as_??` (after `import node.tpe.Underlying`).
- Annotation arguments: `Annotations.constructorArguments(ann)` / `decodedConstructorArguments(ann)`.

## Marker DSLs (`.each`, `.at(i)`, `.when[T]`)

Markers only make the path type-check; the macro rewrites them:

```scala
// Scala 3
extension [C, A](c: C)(using IsElementOf.Aux[C, A])
  @scala.annotation.compileTimeOnly("each can only be used inside modify")
  def each: A = sys.error("each can only be used inside modify")
```

- Pin element types with an **invariant** evidence on the exact container type (`IsElementOf[C] { type Elem }`); a bare `extension [F[_], A](fa: F[A])` lets Scala 2 widen `List[Int]` to `A = Any`. Materialize the evidence with a macro consulting `IsCollection`/`IsMap`/`IsOption` - a **whitebox** macro on Scala 2 (`val c: whitebox.Context` on the bundle, still a `MacroCommonsScala2`) and `transparent inline given` on Scala 3 - so every container with a provider gets `.each` automatically.
- Scala 2 consumes the refined evidence through an implicit **conversion** (`implicit def toEachOps[C](c: C)(implicit ev: IsElementOf[C]): EachOps[C, ev.Elem]`), not an `implicit class`.
- Give all evidences a common non-sealed marker trait so the parser can drop evidence arguments with one `<:<` check.
- `@compileTimeOnly` fires on Scala 3 extensions but not reliably on Scala 2 implicit-class methods: keep `sys.error` bodies too and do not assert the compile error cross-platform.
- Optionally confine Scala 3 markers to the DSL with a phantom context function (`Ctx ?=> (S => A)`, markers require `(using Ctx)`, `Ctx` has no public instance).

## Generating the transformation

- Copy-with-modification: `CaseClass.parse[S]`, `cc.caseFieldValuesAt(s)` for all fields, replace one, rebuild with `cc.construct[F]` or `cc.copyMethod()`; recurse into the focused field through a helper with a regular type parameter (`buildModify[F: Type](...)`) so its path-dependent type never enters a quote.
- Non-exhaustive subtype step (`.when[Sub]`): `MatchCase.matchOn(scrutinee)(NonEmptyVector(MatchCase.typeMatch[Sub]().map(...), MatchCase.typeMatch[S]().map(identity)))` - the parent-type arm is the fall-through; Scala 3 marks the scrutinee `@unchecked`.
- Collection steps: dispatch on `IsMap`/`IsCollection`/`IsOption`/`IsEither` and rebuild with `factory`/`build` (see `hearth-standard-extensions`), so any container with a provider works.
- Calling arbitrary methods/constructors: `method.fold(onInstance, onTypes, onValues)` (`Either[String, Expr_??]`) or match `Method.OnInstance` / `ApplyTypes` / `ApplyValues` / `Result[R]` and `build()`. Keep applying while the step is `ApplyValues` (implicit clauses are separate steps). Arguments are `Map[String, Expr_??]`; omitted defaulted params use their defaults.

## Mocks and proxies: `AnonymousInstance`

```scala
AnonymousInstance.parse[A].toEither match {        // parseWithMixins[A](mixins: List[??])
  case Right(ai) =>
    val overrides: Map[UntypedMethod, OverrideBody] = ai.mustOverride.map { cm =>
      cm.method.asUntyped -> new OverrideBody {
        def apply(octx: OverrideContext): Expr_?? = stubFor(octx) // octx.self, method, parameters, returnType, typeParameters, returnsThisType
      }
    }.toMap
    // constructorArgs: arguments for the chosen constructor's parameters, by name; Map.empty only for a no-arg/all-default one
    ai.construct(constructor = ai.classParent.flatMap(_._2.headOption), constructorArgs = Map.empty, overrides = overrides) match {
      case Right(expr)  => expr
      case Left(errors) => Environment.reportErrorAndAbort(errors.toVector.mkString("\n"))
    }
  case Left(reason) => Environment.reportErrorAndAbort(reason)  // final, sealed, inaccessible type, class parent without an
                                                               // accessible constructor, 2+ class parents (parseWithMixins)
}
```

`mustOverride`, `mayOverride`, `cannotOverride`, `diamondConflicts`, `classParent: Option[(??, List[Method])]`, `traitParents`. When `octx.returnsThisType`, return `octx.self` without casting. An abstract `var` can be implemented only on Scala 2.

## DI: `enclosingScope`

`enclosingScope: NonEmptyVector[Enclosure]` (member of `MacroCommons`, innermost first): `Enclosure.Method` (`localValues` - **Scala 2 only**, closest method), `Enclosure.Value`, `Enclosure.Class` (`members: List[Method]`, `thisRef: Option[Expr_??]` - only for the closest class), `Enclosure.Object` (`thisRef: Expr_??`), `Enclosure.Package` (differs between versions). `Environment.enclosingMethodParameters: List[List[Enclosure.Parameter]]` (`name`, `tpe`, `ref`, `isImplicit`, `isByName`) works the same on both. Call a member: find it in `members`, apply it to `thisRef` with the `Method` chain.

## Gotchas

- **`class type required but M found` / `M is not a class type`** from `classOf[M]` for an abstract macro type param -> summon `ClassTag[M]` during expansion and use `Expr.quote(Expr.splice(ct).runtimeClass)`.
- **`found ...this.Class[_], required Class[_]`** -> inside `MacroCommons`, `Class` is Hearth's `Class[A]` view; write `java.lang.Class` (and prefer `java.lang.Class[Any]` over `[?]` in quotes).
- **Element type widened to `Any` on Scala 2** -> covariant marker signature; use invariant evidence.
- **`<non-destructurable: $anonfun>` / lambda not recognized** -> context-function or `Inlined` wrappers left in place; use `skipContextualWrappers` / `extractLambda`; on Scala 3 make the parameter `inline`.
- **Test-only trap (Scala 3)**: a `B ?=> C` value is eta-applied wherever a given is in scope, even when passed as `Any`; store it as `B => C` if you need the function itself.
- **DI sees nothing on Scala 3** -> `localValues` is always empty there; rely on class/object members and `enclosingMethodParameters`.

## Reference

- Docs: [DestructuredExpr](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#destructuredexpr), [Method](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#method), [MatchCase](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#matchcase), [AnonymousInstance](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#anonymousinstancea), [Enclosing scope](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#enclosing-scope).
- Kindlings 0.4.0: optics [ModifyMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/optics/src/main/scala/hearth/kindlings/optics/internal/compiletime/ModifyMacrosImpl.scala) (+ [per-platform markers](https://github.com/kubuszok/kindlings/tree/0.4.0/optics/src/main)), mocks [MockMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/mock/src/main/scala/hearth/kindlings/mock/internal/compiletime/MockMacrosImpl.scala), DI [WiringMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/di/src/main/scala/hearth/kindlings/di/internal/compiletime/WiringMacrosImpl.scala), [parser](https://github.com/kubuszok/kindlings/tree/0.4.0/parser) (block DSL).
