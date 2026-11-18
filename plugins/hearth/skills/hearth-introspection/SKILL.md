---
name: hearth-introspection
description: >-
  Hearth introspection for Scala 2.13 / Scala 3 macro authors - reading types and members: Type predicates and
  metadata (isCaseClass, isSealed, isJavaBean, isPlainOldJavaObject, isFunction, functionComponents, typeArguments,
  directChildrenList, getRuntimeClass, isAvailable, fqcn, plainPrint), Type.Cache keyed by =:=, Type.Lazy; Method -
  methods / unsortedMethods / unsortedMethodsNamed, Method.sort, expectations (MethodExpectation NeedsInstance /
  NeedsTypes / NeedsValues, parameter-list merging), parameters vs totalParameters, knownReturning, isScalaGetter /
  isJavaGetter / accessorName, byNameUnderlying, varargs, Accessible (Everywhere, AtCallSite, Anywhere); Class[A]
  umbrella view; JavaBean (beanGetters, beanSetters, constructWithSetters); Position (line, column, sourceCode);
  Environment (currentScalaVersion, currentJDKVersion, currentPlatform, isScala3); UntypedType / UntypedExpr bridge,
  MacroCommonsScala3(platformCommons). Fixes "value typeArguments is not a member of Type[A]".
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth introspection: types, members, positions, environment

How a macro asks questions about the code it is expanded in: what a type is, which members it has and how to call
them, where something is in the source, and which Scala/JDK/platform compiles it.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#type-operations (replace `0.4.5`).

All APIs are members of `MacroCommons`. Full tables: [type-api.md](type-api.md) (every `Type` predicate/navigation
method, companion vs extension form) and [method-api.md](method-api.md) (`Method`, `Parameter`, accessors,
rendering). Related skills: `hearth-case-classes-and-enums` (`CaseClass`, `Enum`, `SingletonValue`, `NamedTuple`,
calling constructors with `Method.fold`), `hearth-expr-parsing-dsl` (`DestructuredExpr`, `AnonymousInstance`,
`enclosingScope`), `hearth-hkt-derivation` (`Type.Ctor1`, `decompose1`), `hearth-expr-toolkit` (building
expressions), `hearth-debugging` (`Environment.isExpandedAt`, reporting).

## Types

```scala
Type[A].isCaseClass / isSealed / isJavaBean / isOpaqueType / isTuple / isFunction ...  // Boolean predicates
Type.typeArguments[A]                    // List[??] - companion only, there is no Type[A].typeArguments
Type.directChildrenList[A]               // Option[List[(String, ??<:[A])]] - companion only; keeps same-named children
Type[A].directChildren                   // Option[ListMap[String, ??<:[A]]] - keyed by simple name
Type[A].functionComponents               // Option[(List[??], ??)] for FunctionN (and classes extending it)
Type[A].getRuntimeClass                  // Option[java.lang.Class[A]] - None for types of the module being compiled
Type[A].isAvailable(AtCallSite)          // can generated code mention A here?
Type[A].plainPrint / shortName / fqcn    // "scala.Function1[scala.Int, java.lang.String]" / "Function1" / "scala.Function1"
Type[A] =:= Type[B]; Type[A] <:< Type[B] // never `==`
```

- `fqcn` is not an identity (`Box[Int]` and `Box[String]` share it) and `prettyPrint` has ANSI colours - use `=:=`,
  `Type.hasSameTypeConstructor`, or `plainPrint` for keys and messages that are compared.
- `isPlainOldJavaObject` is `true` for any non-abstract, non-sealed, non-enum class, case classes included;
  `isJavaBean` additionally needs a public nullary constructor.
- Scala 3-only features report `false`/`None` on Scala 2: `isUnionType`, `isIArray`, `isContextFunction`,
  `isNamedTuple`, `opaqueUnderlyingType`.

**Per-type memo.** `Type` has no value equality, so do not key a `Map` by it. `new Type.Cache[F]` stores one `F[X]`
per type, compared with `=:=`; keep it for one expansion (a field of the macro class), not thread-safe:

```scala
private type Printed[X] = String
private lazy val printed = new Type.Cache[Printed]
def describe[A: Type]: String = printed.getOrPut(Type[A])(expensive[A])   // also get(Type[A]), put(Type[A], v)
```

Helper `Type`s kept in fields: `Type.Lazy(Type.of[X])` (see `hearth-cross-quotes`).

## Members: `Method`

```scala
Type[A].methods                     // all members, stable order (declared by position, then inherited by name) - costly
Type[A].unsortedMethods             // same, unspecified order - use for find/filter
Type[A].unsortedMethodsNamed("vs")  // only that name; converts only the matches - use for lookups by name
Method.sort(subset)                 // stable order for a filtered subset; Method.sortBy(pairs)(_._2)
Type[A].primaryConstructor / constructors / defaultConstructor   // Option[Method] / List / Option (nullary)
```

Each `Method` is the first step of a builder chain (`OnInstance` -> `ApplyTypes` -> `ApplyValues` -> `Result`); call
it with `method.fold(onInstance, onTypes, onValues)` (example in `hearth-case-classes-and-enums`). What a method
needs is described upfront by `expectations`:

| Method | `expectations` (verified on 2.13 and 3) |
|---|---|
| `def add(a: Int)(b: Int)(implicit c: Ordering[Int]): Int` | `NeedsInstance, NeedsValues(a, b), NeedsValues(c)` |
| `def poly[T](t: T): List[T]` | `NeedsInstance, NeedsTypes([T]), NeedsValues(t)` - `knownReturning == None` |
| `val v: Int` / `lazy val l` / `var w` | `NeedsInstance` only |
| `def unbox(b: Box)(t: b.T)` | `..., NeedsValues(b), NeedsValues(t)` (path-dependent list starts a new step) |

Consecutive value lists merge into one step except `implicit`/`using` lists and path-dependent ones; Scala 3 clause
interleaving (`def f[A](a: A)[B](b: B)`) adds more `NeedsTypes`/`NeedsValues` steps - never hard-code a layout.

- `totalParameters: List[ListMap[String, Parameter]]` - every value parameter of the whole method, grouped by source
  clause (`add` -> `[a] [b] [c]`), stable along the chain. `parameters` - only those the **current** step expects
  (empty unless the step is `ApplyValues`).
- `knownReturning: Option[??]` - `None` until enough is applied (generic methods), or when the member's type is still
  being inferred (`val x = myMacro[A]` without a type annotation).
- Predicates: `isVal`, `isVar`, `isLazy`, `isDef`, `isImplicit`, `isConstructor`, `isCaseField`, `isDeclared`,
  `isInherited`, `isSynthetic`, `isFinal`, `isAbstract`, `isOverride`, `isPrivate`/`privateWithin`,
  `isProtected`/`protectedWithin`, `isAvailable(Everywhere | AtCallSite | Anywhere)`; arity `arity`, `isNullary`,
  `isUnary`, `isBinary`, `isNAry(n)`.
- Accessors: `isScalaGetter` (`val`/`var`/`lazy val`), `isScalaSetter` (`w_=`), `isJavaGetter` (`getX()` non-Unit,
  `isX()` Boolean), `isJavaSetter` (`setX(v): Unit`), `accessorName` (`w_=` -> `w`, `getCount` -> `count`).
- Parameters: `param.name`, `index`, `tpe: ??`, `hasDefault`, `defaultValue: Option[Method]`, `isImplicit`,
  `annotationsOfType[Ann]`; `isByName` + `byNameUnderlying: Option[??]` (the `A` of `=> A`); `isVararg` with `tpe`
  normalized to `scala.collection.immutable.Seq[A]` - pass an `Expr[Seq[A]]` as the argument.
- `method.plainPrint` -> `demo.Api: def vs(xs: scala.Int*): scala.Int`; `toString` adds the applied state.

**Visibility.** `Accessible` is what the *generated code* needs: `Everywhere` (public only), `AtCallSite` (reachable
from the expansion site, incl. `private[pkg]` - the safe default for emitted calls), `Anywhere` (no filter - for
listing). Class-view methods (`caseFieldValuesAt`, `construct`, `constructWithSetters`) take it as `visibility`.

## `Class[A]`: pick the most specific view

```scala
Class[A] match {                       // Class.apply tries SingletonValue, NamedTuple, CaseClass, Enum, JavaBean in order
  case sv: SingletonValue[?] => ...
  case cc: CaseClass[?]      => ...
  case e: Enum[?]            => ...
  case jb: JavaBean[?]       => ...     // ANY public class with a nullary constructor lands here
  case cls                   => cls.constructors / cls.methods / cls.method("name")
}
```

Or ask for one view: `cls.asCaseClass`, `asEnum`, `asJavaBean`, `asSingleton`, `asNamedTuple` (`Option`s), or
`X.parse[A]` (`ClassViewResult`, with the reason in `toEither`).

## `JavaBean`

```scala
JavaBean.parse[A].toEither match {     // "... is a POJO but has no public default constructor" / "... is not a plain old Java object"
  case Right(jb) =>
    jb.defaultConstructor              // Method
    jb.beanGetters / jb.beanSetters    // List[Method] (getters include getClass - filter it out)
    jb.constructWithoutSetters()       // Option[Expr[A]]: `new A()`, None if the constructor is not accessible
    jb.constructWithSetters[MIO] { (name, param) =>        // also parConstructWithSetters (aggregates errors)
      import param.tpe.Underlying as F
      valueFor[F](name).map(_.as_??)                       // MIO[Expr_??] of the setter's parameter type
    }                                                      // MIO[Option[Expr[A]]]: { val b = new A(); b.setX(..); ...; b }
  case Left(reason) => ...
}
```

The callback's `name` is the setter's **parameter** name (`setName(v: String)` gives `"v"`, Java classes compiled
without `-parameters` give `arg0`), not the property name. When you need property names (e.g. to read a config key),
iterate `jb.beanSetters`, take `accessorName`, and build the setter calls yourself with `Method.fold` on a
`ValDefs.createVal(constructorExpr)`-bound instance.

## `Position`

```scala
Environment.currentPosition            // where the macro is expanded
expr.position / method.position / param.position / Type[A].position   // Option[Position]
pos.file / fileName / line / column / offset / sourceCode / prettyPrint ("File.scala:42:10") / prettyPrintLong
positions.sorted                       // implicit Ordering: by file, then offset
```

`line`/`column` are 1-based on both versions. Columns of the same call still differ (verified): for `M.ops(local * 2)`
`currentPosition` is at `M` on Scala 3 but at `ops` on Scala 2, and `expr.position` of `local * 2` is at `local` on
Scala 3 but at `*` on Scala 2. Compare files and lines, or `sourceCode`, not columns.

## `Environment`

| API | Value |
|---|---|
| `currentScalaVersion` | `ScalaVersion(major, minor, patch)` of the compiler, e.g. `Scala 3.3.7`; has an `Ordering` |
| `currentLanguageVersion`, `isScala2_13`, `isScala3` | `LanguageVersion.Scala2_13` / `Scala3` |
| `currentPlatform`, `isJvm`, `isJs`, `isNative` | `Platform.Jvm` / `Js` / `Native` - the **target** platform |
| `currentJDKVersion` | JDK running the compiler as `JDKVersion(1, feature)`, e.g. `JDK 1.17` - compare `.minor` |

```scala
import scala.math.Ordering.Implicits.*
if (Environment.currentScalaVersion >= hearth.ScalaVersion(3, 7, 0)) ... // e.g. before summonExprIgnoring
```

## Untyped bridge

Typed APIs are preferred; drop down only for operations the typed layer lacks (types of any kind, platform-specific
trees):

```scala
val ut: UntypedType = Type[A].asUntyped             // or UntypedType.fromTyped[A]
ut.asTyped[A]; ut.as_??                             // back: Type[A] / ??  (UntypedType.toTyped[A](ut), UntypedType.as_??(ut))
val ue: UntypedExpr = expr.asUntyped                // UntypedExpr.fromTyped(expr)
ue.asTyped[A]; ue.as_??                             // UntypedExpr.toTyped[A](ue) / Expr_?? with the tree's own type
UntypedExpr.as_??(ue, knownType)                    // Expr_?? with a type you know (e.g. read before untypecheck)
method.asUntyped / UntypedMethod; param.asUntyped   // untyped members
```

Platform-specific code in a shared extension (in a Scala 3-only source file):

```scala
commons match {                                     // commons: hearth.MacroCommons
  case hearth.MacroCommonsScala3(pc) => import pc.quotes.reflect.*; Symbol.spliceOwner.owner.name
  case _                             => "not Scala 3"
}
```

(`hearth.MacroCommonsScala2(pc)` likewise exposes `pc.c` on Scala 2.)

## Gotchas

- **`value typeArguments is not a member of Type[A]`** (also `directChildrenList`) -> companion-only: `Type.typeArguments[A]`, `Type.directChildrenList[A]` (the docs table lists extension forms that do not exist).
- **A plain service class is treated as a JavaBean** -> `Class[A]`/`JavaBean.parse` accept every public class with a nullary constructor, even with no setters; check `jb.beanSetters.nonEmpty` or match `CaseClass`/`Enum` first and decide explicitly.
- **`getClass` among `beanGetters`** -> it is a Java getter by name; filter it out.
- **Bean setter values keyed wrongly** -> the `constructWithSetters` callback gets the setter's parameter name; see JavaBean above.
- **By-name parameter type prints as `` scala.`<byname>`[java.lang.String] `` (Scala 2) / `=> scala.Predef.String` (Scala 3)** -> use `param.byNameUnderlying`.
- **`knownReturning` is `None`** -> generic method before `ApplyTypes`, or a member whose type is being inferred; do not `.get`.
- **Slow expansion on types with many members** -> `methods` resolves positions for sorting every member; use `unsortedMethodsNamed` / `unsortedMethods` and `Method.sort` on the subset.
- **Scala 2 warning `The outer reference in this type test cannot be checked at run time`** on `case MethodExpectation.NeedsValues(ps) =>` (path-dependent case classes) -> harmless; with `-Werror` add `@nowarn("msg=outer reference")` on the method.
- **`isPrivate == false` for `private[pkg]`** -> check `privateWithin`/`isAvailable(AtCallSite)`.
- **`isOverride` differs for `java.lang.Object` members** (`true` on Scala 2, `false` on Scala 3) -> do not branch on it for them.
- **`getRuntimeClass` / `Type.classOfType` is `None`** for types compiled in the same module as the expansion, abstract types and type parameters.
- **Var setter parameter is named `x$1`** (`w_=(x$1: Int)`) -> do not derive names from it; use `accessorName`.
- **`currentJDKVersion` is not the target JDK** -> it is the JVM running the compiler (`-release` is not visible).

## Reference

- Docs: [Type operations](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#type-operations), [Type.Cache and Type.Lazy](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#typecache-and-typelazy), [Method](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#method), [Obtaining Method](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#obtaining-method), [Method operations](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#method-operations), [Parameters and arguments](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#parameters-and-arguments), [Class](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#class), [JavaBean](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#javabeana), [Position](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#position), [Current compilation context](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#current-compilation-context), [Versions](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#versions).
- Sources: [Types.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Types.scala), [Methods.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Methods.scala), [Classes.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Classes.scala), [Environments.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/Environments.scala), [untyped/](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scala/hearth/untyped).
