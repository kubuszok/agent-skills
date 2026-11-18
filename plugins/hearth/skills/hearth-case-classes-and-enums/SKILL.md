---
name: hearth-case-classes-and-enums
description: >-
  Hearth data-type introspection and construction for Scala 2.13 / Scala 3 macros - CaseClass.parse,
  caseFieldValuesAt, construct / parConstruct, primaryConstructor and the Method builder chain (Method.fold, default
  values, Arguments), copyMethod, annotations on fields (annotationsOfType,
  Annotations.decodedConstructorArguments), SingletonValue (case objects, parameterless Scala 3 enum cases, Java
  enum values), Enum.parse with matchOn / parMatchOn (sealed traits, Scala 3 enums, Java enums, Enumeration, union
  types with TypeTest), NamedTuple, JavaBean. Use when a macro reads fields of case classes (encoders, Show, Eq),
  constructs them (decoders), or dispatches on subtypes; also for "the type test for E.A cannot be checked at
  runtime" warnings and "is a singleton, use SingletonValue instead of CaseClass".
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth: case classes, enums, singletons, named tuples

Hearth's views over data types. All `parse` methods return `ClassViewResult[V]` (`.toOption`, `.toEither` with the reason) - use the reason as the `Rule.yielded(...)` message.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#class (replace `0.4.5`).

Imports: `hearth.fp.effect.*`, `hearth.fp.instances.*`, `hearth.fp.syntax.*`; code lives in `trait X { this: MacroCommons => }`.

## Reading fields (encoder style)

```scala
def showCaseClass[A: Ctx]: MIO[Rule.Applicability[Expr[String]]] =
  CaseClass.parse[A].toEither match {
    case Left(reason) => MIO.pure(Rule.yielded(reason))
    case Right(cc) =>
      cc.caseFieldValuesAt(ctx[A].value).toList          // ListMap[String, Expr_??], declaration order
        .parTraverse { case (name, field) =>             // parTraverse: report ALL failing fields
          import field.{Underlying as Field, value as fieldExpr}
          Log.namedScope(s"Field $name: ${Type[Field].prettyPrint}") {
            deriveRecursively[Field](using ctx[A].nest(fieldExpr)).map(r => Expr.quote(Expr.splice(Expr(name)) + "=" + Expr.splice(r)))
          }
        }
        .map(parts => Rule.matched(joinWithCommas(parts)))
  }
```

- `caseFieldValuesAt(expr, visibility = AtCallSite)` returns only fields accessible at the expansion site (pass `Everywhere` / `Anywhere` to change). Keys are declared names on both Scala versions.
- `cc.caseFields: List[Method]`, `cc.primaryConstructor: Method`, `cc.nonPrimaryConstructors`; `param.tpe`, `param.index`, `param.hasDefault`, `param.defaultValue: Option[Method]`, `param.annotations`, `param.isByName`, `param.isVararg` come from `cc.primaryConstructor.totalParameters.flatten`.
- Zero-field case classes are valid (`caseFieldValuesAt` is empty) - handle them.

## Constructing (decoder style)

Simplest: `construct`/`parConstruct` with one callback per constructor parameter:

```scala
cc.parConstruct[MIO] { param =>
  import param.tpe.Underlying as Field
  decodeField[Field](param.name).map(_.as_??)            // MIO[Expr_??]; must be an Expr of the param's type
}  // MIO[Option[Expr[A]]] - None when the primary constructor is not public: report it as an error
// This overload checks `Everywhere`; pass `CaseClass.ConstructField[MIO](...)` with `visibility = AtCallSite` to
// allow e.g. `private[pkg]` constructors visible at the expansion site. An Expr_?? whose type is not a subtype of the
// parameter type throws "Upcasting can only be done to type proved to be super type!" (not a failed MIO).
```

When some arguments may be omitted (use default values) or you want an `Either` error instead of an exception, drive the constructor `Method` yourself; arguments are a `Map[String, Expr_??]`, omitted parameters with defaults use the default:

```scala
val args: Map[String, Expr_??] = Map("name" -> nameExpr.as_??)   // "age" has a default
cc.primaryConstructor.fold(
  onInstance = _ => sys.error("never called for constructors"),
  onTypes    = _ => Map.empty,   // never called for constructors: class type arguments come from Type[A]
  onValues   = _ => args
) match {
  case Right(built) => import built.Underlying as R; built.value.upcast[A]   // R <:< A
  case Left(error)  => Environment.reportErrorAndAbort(error)                // e.g. missing / ill-typed argument
}
```

**Wide case classes:** never put a field's `try`/`if` fallback directly in the constructor's argument list (quadratic size, "Method too large" at a few dozen fields); decode each field in a local `def` and pass plain values - see `hearth-generated-code-performance` (`wide-types.md`).

Arguments are type-checked: an `Expr[Any]` for an `Int` field is rejected - keep each field's own type (see the helper-method trick below). Update one field of an existing value with `cc.copyMethod()` (`Option[Method.OnInstance.Of[A]]`): apply the instance, then (for a generic case class) the type arguments, then only the changed arguments, then `build()`. It is `None` for `sealed abstract case class`, vararg case classes, or an inaccessible `copy` (default `visibility = AtCallSite`).

## Annotations on fields and types

```scala
// final class fieldName(val name: String) extends scala.annotation.StaticAnnotation
val renamed: Option[String] = param.annotationsOfType[fieldName].headOption
  .flatMap(Annotations.decodedConstructorArguments(_))
  .flatMap(_.headOption.flatMap(_.toOption))
  .collect { case s: String => s }
```

`Type[A].annotations`, `Type[A].typeAnnotations` (annotated types like `Int @ann`), `hasAnnotationOfType[Ann]`. `decodedConstructorArguments(ann): Option[List[Either[String, Any]]]` evaluates each argument with `semiEval` (literals, objects, constructor/method calls on the classpath). It gives `Left(reason)` per argument it cannot evaluate - including references to classes/objects of the module being compiled - and `None` if the annotation is not a constructor call. `Annotations.constructorArguments(ann)` gives the unevaluated `Expr_??`s.

## Singletons

`SingletonValue.parse[A]` / `SingletonValue.unapply(tpe)` match case objects, parameterless Scala 3 enum cases, plain objects, Java enum values and `Enumeration` values; `sv.singletonExpr: Expr[A]` references the value. Give them their **own rule before the case-class rule** - `CaseClass.parse` rejects them with "... is a singleton, use SingletonValue instead of CaseClass". `Expr.singletonOf[A]` is a shortcut.

## Sum types: `Enum`

```scala
Enum.parse[A].toEither match {
  case Left(reason) => MIO.pure(Rule.yielded(reason))
  case Right(enumm) =>
    enumm.parMatchOn[MIO, String](ctx[A].value) { matched =>   // matched: Expr_??<:[A] narrowed to the child
      import matched.{Underlying as Child, value as childExpr}
      deriveRecursively[Child](using ctx[A].nest(childExpr))
    }.flatMap {
      case Some(matchExpr) => MIO.pure(Rule.matched(matchExpr))
      case None            => MIO.fail(MyError.NoChildren(Type[A].prettyPrint))
    }
}
```

- Handles sealed traits/classes, Scala 3 `enum`s, Java enums, `scala.Enumeration` and (Scala 3) union types whose members are distinguishable at runtime (or have a user-provided `scala.reflect.TypeTest`, see below). `matchOn` is the fail-fast variant; `parMatchOn` aggregates errors from all children.
- `enumm.directChildren: ListMap[String, ??<:[A]]` (immediate subtypes; nested sealed traits appear as one child) is keyed by the subtype's **simple** name: same-named subtypes from different scopes collapse into one entry, and the key format changes to the full name in 0.5.0 - do not rely on it. `Type[A].directChildrenList` (`Option[List[(String, ??<:[A])]]`, since 0.4.1) keeps every child; `Type[A].directChildrenInOrder(ChildrenOrder.DeclarationWhenAvailable | ChildrenOrder.ByName)` gives a stable order. Derive discriminator names yourself (e.g. from the child type's name) instead of from the map keys. `enumm.exhaustiveChildren: Option[NonEmptyMap[String, ??<:[A]]]` (flattened leaves).
- For decoders, build the child from its name: iterate the children, use `SingletonValue.unapply` for singletons and the case-class path for the rest, and emit a `match` on the discriminator string: one `MatchCase.eqValue(Expr(name))` per child plus a final `MatchCase.typeMatch[String]()` arm that reports the unknown discriminator (`MatchCase.matchOn` adds no default arm, so without it an unknown value is a runtime `MatchError`).
- Unions whose members a class test cannot distinguish (`List[Int] | List[String]`) are accepted only with a user-provided `scala.reflect.TypeTest` per member; `Type[A].unionRefusalReason` tells the user which ones (use it in the error). On Scala 2 `isUnionType` is always `false`.

## Named tuples (Scala 3.7+)

`NamedTuple.parse[A]` -> `nt.fields: List[(String, ??)]`, `nt.primaryConstructor`, `nt.construct[F](CaseClass.ConstructField[F](param => ...))`. `Type[A].isNamedTuple` is `false` on Scala 2. Put the named-tuple check **before** the value-type rule (named tuples are opaque types, which the opaque-type `IsValueType` provider may unwrap).

## Gotchas

- **`the type test for E.A cannot be checked at runtime` at the user's call site** (fatal with `-Werror`; `@nowarn` in your source does not help) -> generated `y.isInstanceOf[E.A]` for a parameterless Scala 3 enum case (erased to `E`). Rules comparing two values (Eq, Order, diff) must check `SingletonValue.unapply(Type[Child])` and compare with `eq` against `sv.singletonExpr`; only case-class children get `isInstanceOf`. Single-dispatch `matchOn` is safe.
- **Scala 2 `not found: value param` / `value field`** -> `Field` from `import param.tpe.Underlying as Field` used inside `Expr.quote`. Move that quote into a method with a real type parameter: `def wrap[F: Type](e: Expr[F]): Expr[...] = Expr.quote(...)`.
- **"Upcasting can only be done to type proved to be super type!"** -> `expr.upcast[B]` only widens; narrow with `.asInstanceOf[B]` inside `Expr.quote` (needs `Type[B]`).
- **`MIO[Option[Expr[A]]]` ignored** -> `construct` returns `None` for an inaccessible constructor; turn it into a readable error (private constructor, private subtype).
- **Two subtypes with the same simple name collapse into one** (e.g. `Outer.Green` and a top-level `Green`) -> `directChildren` keys by simple name -> use `directChildrenList` and build unambiguous names.
- **Sealed trait with no children** -> `Enum.parse` is `Incompatible` ("has no direct children"); report it instead of generating an empty match.
- **Child types of generic sealed traits** -> Hearth reapplies the parent's type arguments to children; do not reconstruct child types by name.
- **Before Hearth 0.4.4, Scala 3 enum cases from `directChildren` summoned `Mirror.Sum`/had no `ValueOf`** (kubuszok/hearth#395) - upgrade if you summon `Mirror`/`ValueOf` for children.
- **Recursive data types** (`case class Tree(children: List[Tree])`) loop or blow up the method size unless each case class/enum body is a cached `def` - see `hearth-def-caching`.
- **Value classes / opaque types** are better handled by `IsValueType` (unwrap/wrap) than as one-field case classes - see `hearth-standard-extensions`.

## Reference

- Docs: [Class views](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#class), [Method / calling methods](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#method), [annotations](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#reading-annotation-arguments), [union types](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#union-types-scala-3-only).
- Kindlings 0.4.0: [FastShowPretty case class rule](https://github.com/kubuszok/kindlings/blob/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/rules/FastShowPrettyHandleAsCaseClassRule.scala), [enum rule](https://github.com/kubuszok/kindlings/blob/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/rules/FastShowPrettyHandleAsEnumRule.scala), decoder construction in [circe DecoderMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/circe-derivation/src/main/scala/hearth/kindlings/circederivation/internal/compiletime/DecoderMacrosImpl.scala), two-value enum comparison in [cats-derivation rules](https://github.com/kubuszok/kindlings/tree/0.4.0/cats-derivation/src/main/scala/hearth/kindlings/catsderivation/internal/compiletime/rules).
