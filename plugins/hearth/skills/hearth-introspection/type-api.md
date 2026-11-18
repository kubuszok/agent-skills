# `Type` API reference (Hearth 0.4.5)

Verified against [Types.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Types.scala).
"Ext" = extension method on `Type[A]` (`Type[A].isCaseClass`); "Companion" = `Type.isCaseClass[A]`. Most methods
exist in both forms; the **companion-only** ones are marked - writing them as extensions fails with
`value ... is not a member of Type[A]`.

On an existential `tpe: ??` only `shortName`, `fqcn`, `plainPrint`, `prettyPrint`, `runtime*Print` and `asUntyped`
are available directly; for anything else go through the carried `Type`: `tpe.Underlying.isCaseClass`, or
`import tpe.Underlying as X` and `Type[X].isCaseClass`.

## Printing

| Ext | Result | Notes |
|---|---|---|
| `shortName` | `"Function1"` | no package, no type arguments |
| `fqcn` | `"scala.Function1"` | not an identity - `Box[Int]` and `Box[String]` share it |
| `plainPrint` | `"scala.Function1[scala.Int, java.lang.String]"` | stable; use for keys/messages that are compared |
| `prettyPrint` | same with ANSI colours | logs and errors only |
| `runtimePlainPrint(fn)` / `runtimePrettyPrint(fn)` / `runtimeShortPrint(fn)` | `Expr[String]` | `fn: ?? => Option[Expr[String]]` substitutes parts (e.g. type parameters known only at runtime) |

## Predicates (`Boolean`, both forms)

| Group | Methods |
|---|---|
| Built-ins | `isPrimitive` (incl. `Unit`), `isArray`, `isIArray` (Scala 3), `isJvmBuiltIn` (primitives, `String`, arrays, `java.lang.*`), `isInJavaLangPackage`, `isTypeSystemSpecial` (`Any`, `AnyRef`, `AnyVal`, `Null`, `Nothing`) |
| Shapes | `isTuple` (also `*:` on Scala 3), `isNamedTuple` (Scala 3.7+), `isFunction` (also classes extending `FunctionN`), `isContextFunction` (Scala 3), `isUnionType` (Scala 3), `isOpaqueType` |
| Classes | `isClass`, `notJvmBuiltInClass`, `isPlainOldJavaObject` (non-abstract, non-sealed, non-enum class - case classes too), `isJavaBean` / `isJavaBean(visibility)` (POJO, not an object, accessible nullary constructor) |
| Modifiers | `isAbstract`, `isFinal`, `isTrait`, `isSealed`, `isObject`, `isVal` (singleton type of a value, e.g. parameterless enum case) |
| Case/enums | `isCase`, `isCaseClass`, `isCaseObject`, `isCaseVal`, `isJavaEnum`, `isJavaEnumValue`, `isEnumeration` (`scala.Enumeration` values) |
| Visibility | `isAvailable(Everywhere \| AtCallSite \| Anywhere)` |
| Relations | `Type[A] <:< Type[B]`, `Type[A] =:= Type[B]` (companion: `isSubtypeOf[A, B]`, `isSameAs[A, B]`); **companion-only** `Type.hasSameTypeConstructor[A, B]` |
| Unions (Scala 3) | `unionMemberRequiresTypeTest[B]`, `unionRefusalReason: Option[String]` |

## Navigation and metadata

| Method | Form | Result |
|---|---|---|
| `position` | both | `Option[Position]` of the definition |
| `getRuntimeClass` (ext) / `Type.classOfType[A]` (companion) | both | `Option[java.lang.Class[A]]` - `None` for types of the module being compiled, abstract types, type parameters |
| `Type.typeArguments[A]` | **companion-only** | `List[??]` |
| `parents`, `baseClasses` | both | `List[??]` (direct parents / linearization) |
| `directChildren` | both | `Option[ListMap[String, ??<:[A]]]` keyed by simple name (same-named children collapse) |
| `Type.directChildrenList[A]` | **companion-only** | `Option[List[(String, ??<:[A])]]` - keeps all children |
| `directChildrenInOrder(order)` | both | `ChildrenOrder.DeclarationWhenAvailable` or `ChildrenOrder.ByName` (same on both Scala versions) |
| `exhaustiveChildren` | both | `Option[NonEmptyMap[String, ??<:[A]]]` (leaves of nested hierarchies) |
| `companionObject`, `pseudoCompanionObject` | both | `Option[Expr_??]` (the latter also finds newtype objects) |
| `opaqueUnderlyingType` | both | `Option[??]` (always `None` on Scala 2) |
| `functionComponents`, `contextFunctionComponents` | both | `Option[(List[??], ??)]` |
| `annotations`, `annotationsOfType[Ann]`, `hasAnnotationOfType[Ann]` | both | annotations on the symbol (`@Ann class Foo`), matched with `<:<` |
| `typeAnnotations`, `typeAnnotationsOfType[Ann]` | both | annotations in type position (`String @Ann`) |
| `Type.decompose1[A]` / `decompose2[A]` | **companion-only** | split `G[X]` / `G[X, Y]` when `G` is unknown (see `hearth-hkt-derivation`) |
| `primaryConstructor`, `defaultConstructor`, `constructors`, `methods`, `unsortedMethods`, `unsortedMethodsNamed(n)` | ext (companion: `Method.primaryConstructorOf[A]` etc.) | see [method-api.md](method-api.md) |
| `summonExpr`, `summonExprIgnoring(methods*)` | ext | `SummoningResult[A]`; `Ignoring` needs Scala 2.13.17+ / 3.7.0+ where the macro expands |
| `asUntyped`, `as_??`, `as_??<:[U]`, `as_??>:[L]`, `as_<:??<:[L, U]` | ext | untyped / existential forms |

## Memo and helper types

```scala
new Type.Cache[F]                      // get(Type[A]): Option[F[A]], put(Type[A], v), getOrPut(Type[A])(v)
Type.Lazy(Type.of[X])                  // computed on first use, in the macro-entry scope; converts to Type[X] implicitly
```

`Type.Cache` compares keys with `=:=` and, on Scala 3, also separates entries per `Expr.splice` scope (a miss just
recomputes). Keep it for a single expansion.
