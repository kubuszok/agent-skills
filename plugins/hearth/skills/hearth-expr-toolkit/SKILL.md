---
name: hearth-expr-toolkit
description: >-
  Hearth expression toolkit for Scala 2.13 / Scala 3 macro authors - turning values into code and back: Expr(value),
  Expr.unapply / expr.value, built-in ExprCodec instances, ExprCodec.derived, Expr.semiEval (what it can and cannot
  evaluate) with EvalOverride, Expr.semiQuote with QuoteOverride, TypeCodec and literal types (Type(5), Type.unapply,
  Type.StringCodec.fromType), VarArgs (toIterableOption for xs*), FreshName, MatchCase (typeMatch, eqValue,
  typeTestMatch, matchOn), ValDefs, expr.position / sourceCode / upcast / annotated / suppressUnused / tpe,
  Expr.singletonOf, existentials ??, ??<:, ??>:, Expr_??, Existential.apply[F, A]. Fixes "Cannot semi-evaluate ...
  is compiled together with the code expanding the macro", "Method 'apply' invocation failed: argument type
  mismatch", "ExprCodec.derived[...].toExpr failed: Cannot semi-quote value of type", "Type.StringCodec cannot be used
  as an extractor in a pattern", scala.MatchError from generated matches.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth expression toolkit

Utilities for building expressions inside a macro and for moving data between the macro and the code: lift a value
the macro computed into code (`Expr(value)`, `semiQuote`), read a value the user wrote back into the macro
(`expr.value`, `semiEval`), and assemble `match`es, local vals and varargs without knowing the types upfront.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#expression-operations (replace `0.4.5`).

All APIs are members of `MacroCommons` (code lives in `trait X { this: MacroCommons => ... }`). Long tables (built-in
codecs, everything `semiEval` handles, error messages) are in [semi-eval-and-codecs.md](semi-eval-and-codecs.md).
Related skills: `hearth-cross-quotes` (`Expr.quote`/`Expr.splice`, `Type.of`), `hearth-def-caching` (`ValDefBuilder`,
`ValDefsCache`), `hearth-lambda-builder`, `hearth-case-classes-and-enums`, `hearth-expr-parsing-dsl`
(`DestructuredExpr`), `hearth-introspection` (`Type`/`Method` metadata).

## Which tool lifts/unlifts what

| Need | Use | Result |
|---|---|---|
| Value the macro computed, built-in type (primitives, `String`, `BigInt`, collections, `Option`, `Either`, `Data`, `Class`, `ClassTag`) | `Expr(value)` | `Expr[A]` (needs `ExprCodec[A]`, collections also `Type[Elem]`) |
| Literal/constant the user wrote, built-in type | `expr.value`, `Expr.unapply(expr)`, `case Expr(v) =>` | `Option[A]` |
| Any user expression (calls, constructors, companion vals, lambdas) evaluated at compile time | `expr.semiEval` / `Expr.semiEval(expr, overrides)` | `Either[NonEmptyVector[String], A]` |
| Value of a case class / sealed trait / object | `Expr.semiQuote(value)` / `(value, overrides)` (needs `Type[A]`) | `Either[String, Expr[A]]` |
| Both directions for one ADT | `ExprCodec.derived[A]` | `ExprCodec[A]` (`toExpr` = semiQuote, `fromExpr` = `semiEval(...).toOption`) |
| Literal **type** (`Type["abc"]`) <-> value | `Type(value)`, `Type.unapply(tpe)`, `Type.StringCodec.fromType(tpe)` | `Type[A]` / `Option[...]` |

```scala
implicit val IntType: Type[Int] = IntT               // private val IntT: Type[Int] = Type.of[Int] in the trait
val lifted: Expr[List[Int]] = Expr(List(1, 2, 3))    // scala.List.apply[scala.Int](1, 2, 3)
lifted.value                                         // Some(List(1, 2, 3))
e match { case Expr(n) => s"const $n"; case _ => "not a constant" }   // e: Expr[Int]
```

`Expr(value)` is for the final value only. Prefer `Expr.quote(...)` whenever the code that produces the value can be
quoted - it keeps the user's code instead of a snapshot of its result.

## `semiEval`: evaluate user code at compile time

```scala
configExpr.semiEval match {                                      // Expr[Config] -> Either[NonEmptyVector[String], Config]
  case Right(config) => generateFor(config)
  case Left(errors)  => Environment.reportErrorAndAbort(s"Config must be known at compile time: ${errors.mkString(", ")}")
}
```

It replays the tree with JVM reflection: literals, operators, objects and companion members, constructor and method
calls (varargs, overloads, named/default arguments), blocks of `val`s, lambdas without control flow, Scala 3 inline
proxies. It refuses `var`s, `match`/`if`/loops inside lambdas, local `def`/class definitions, and **anything defined
in the module where the macro expands** (no class files yet). Details: [semi-eval-and-codecs.md](semi-eval-and-codecs.md#semieval).

Overrides customise evaluation per (sub)type; the dispatcher must return a `none` existential for every type it does
not handle:

```scala
implicit val PortType: Type[Port] = PortT
val noOverride: Existential[EvalOverride] = {
  implicit val AnyType: Type[Any] = AnyT
  Existential[EvalOverride, Any](EvalOverride.none[Any])
}
val overrides: UntypedType => Existential[EvalOverride] = tpe =>
  if (tpe =:= UntypedType.fromTyped[Port])
    Existential[EvalOverride, Port](EvalOverride[Port](portExpr => Right(Port(9999))))   // Expr[Port] => Either[String, Port]
  else noOverride
configExpr.semiEval(overrides)               // Config(h,Port(9999),List())
```

`QuoteOverride[A]` (`A => Either[String, Expr[A]]`) works the same for `Expr.semiQuote(value, overrides)`.

## `semiQuote` and `ExprCodec.derived`

```scala
implicit val ConfigType: Type[Config] = ConfigT
Expr.semiQuote(Config("localhost", Port(8080), List("a"))) match {   // new demo.Config("localhost", new demo.Port(8080), ...)
  case Right(expr) => expr
  case Left(error) => Environment.reportErrorAndAbort(error)          // "Cannot semi-quote value of type ..."
}

val codec: ExprCodec[Config] = ExprCodec.derived[Config]              // needs Type[Config] in scope
codec.toExpr(Config("localhost", Port(8080), Nil))                   // aborts compilation if a field is not quotable
codec.fromExpr(userExpr)                                              // Option[Config], None on any semiEval failure
```

`semiQuote` tries, in order: your override, the built-in codecs (also `Seq`/`List`/`Vector`/`Set`/`Option`/`Map`/`Either`
of built-in elements), `SingletonValue`, `CaseClass` (field by field), `Enum` (child chosen by the value's runtime
class; singletons by value). Anything else (a plain class) fails. `ExprCodec.derived` is not an implicit - call it
inside the macro. It also consults `ExprCodec[F]` implicits for nested types, but searched at the **user's** call
site, not your macro's scope: a local `implicit val portCodec: ExprCodec[Port]` in your macro is ignored (verified) -
use explicit overrides instead.

## Literal types: `TypeCodec`

```scala
implicit val IntType: Type[Int] = IntT
val five: Type[Int] = Type(5)                    // plainPrint: "5" - type it as Type[Int], NOT Type[5]
Type.unapply(five)                               // Some(5) - uses TypeCodec[Int]
Type.unapply(IntType)                            // None - not a literal type
Type.StringCodec.fromType(Type[A]).map(_.value)  // Some("abc") for A = "abc"; Type.IntCodec etc. likewise
```

`TypeCodec` has `toType`/`fromType`, no `unapply`: `case Type.StringCodec(v) =>` does not compile. Bidirectional for
primitives, `String`, tuples, `Option`/`Either` families and objects; collections, `Class`, `ClassTag` are
`toType`-only.

## `VarArgs`

Shared signature `def m[A: Type](args: VarArgs[A]): Expr[...]`; adapters pass Scala 2 `args: c.Expr[A]*` and
Scala 3 `args: Expr[Seq[A]]` (from `inline xs: A*` + `'xs`) unchanged.

```scala
args.toIterableOption match {
  case Some(exprs) => ...   // m(a, b) and m(): one Expr[A] per argument
  case None        => ...   // m(xs*) - elements known only at runtime: treat as a whole or report an error
}
args.toList / toVector / toSeq / to(factory)                 // Scala 3: Nil for m(xs*); Scala 2: one Seq-typed element
Expr.quote(List(Expr.splice(VarArgs.from(exprs.reverse))*))  // VarArgs(e1, e2) / VarArgs.from(it): Expr[Seq[A]]
```

## `MatchCase`: build a `match` when cases are found during expansion

```scala
implicit val IntType: Type[Int] = IntT; implicit val StringType: Type[String] = StringT
e.matchOn[String](                                              // also (NonEmptyVector) / (NonEmptyList) overloads
  MatchCase.eqValue[Int](Expr(1), "one").map(_ => Expr("one")), // case one @ 1 =>  (literal / object / enum value pattern)
  MatchCase.typeMatch[Int]("other").map(o => Expr.quote("other " + Expr.splice(o).toString)) // case other: Int =>
)
```

- **`matchOn` adds no default case.** A value no case matches throws `scala.MatchError` at runtime (verified). Unless
  the cases are exhaustive by type (e.g. every `Enum` child), end with a fallback `MatchCase.typeMatch[A]` arm.
- Effectful case bodies: `MatchCase.typeMatch[C]("c").traverse(c => mio(c))` gives `MIO[MatchCase[Expr[B]]]`
  (`import hearth.fp.syntax.*`); combine several with `parTuple`/`parTraverse` to aggregate errors, then `matchOn`.
- `MatchCase.typeTestMatch[A, B]` (`case b @ tt(_)` with a summoned `scala.reflect.TypeTest[A, B]`) is Scala 3-only;
  on Scala 2 it always fails.
- `DirectStyle[MatchCase]` needs `import MatchCase.unsafe.*` and exactly one `runSafe` per `scoped` block.
- For whole-ADT dispatch use `Enum.matchOn` (`hearth-case-classes-and-enums`), which picks `typeMatch`/`eqValue` per child.

## `FreshName` and `ValDefs`

Names of generated bindings are always made fresh: `FreshName.FromType` (default for vals and `typeMatch`),
`FreshName.FromExpr` (default for `eqValue`), `FreshName.FromPrefix("acc")` or just `"acc"` (implicit conversion).

```scala
ValDefs.createVal(expr, "tmp").use { tmp => ... }                  // { val tmp$macro$1 = expr; ... }
ValDefs.createVar[Int](Expr(0), "acc").use { case (get, set) =>    // var: getter Expr + setter Expr[Int] => Expr[Unit]
  Expr.quote { Expr.splice(set(Expr.quote(Expr.splice(get) + 41))); Expr.splice(get) + 1 }   // 42
}
```

Also `createLazy`, `createDef`; combine several with `map2`/`parMap2`/`traverse` before `.use`. For reusable or
recursive helper defs use `ValDefsCache` (`hearth-def-caching`).

## Expression operations

| API | Result | Notes |
|---|---|---|
| `expr.upcast[B]` | `Expr[B]` | only widens; needs `Type[A]` and `Type[B]` |
| `expr.suppressUnused` | `Expr[Unit]` | silences "unused value" in generated code |
| `expr.annotated[Ann](args: UntypedExpr*)` | `Expr[A]` | `{ @Ann(args) val annotated = expr; annotated }`; works for Java annotations (`java.lang.SuppressWarnings`); needs `Type[Ann]` |
| `Expr.singletonOf[A]` | `Option[Expr[A]]` | reference to an object / Scala 3 parameterless enum case / Java enum value |
| `expr.tpe` / `Expr.typeOf(expr)` | `Type[A]` | the compiler's type of the tree - may be **narrower** than `A` |
| `expr.position` / `expr.sourceCode` | `Option[Position]` / `Option[String]` | `sourceCode` is the user's text (`"local * 2"`); `None` for synthetic trees |
| `expr.as_??`, `as_??<:[U]`, `as_??>:[L]`, `as_<:??<:[L, U]` | `Expr_??` & bounded variants | forget the type, keep `Type` evidence |

## Existentials

`??` = `Existential[Type]`, `Expr_??` = `Existential[Expr]`; bounded: `??<:[U]`, `??>:[L]`, `L <:??<: U` (and the
`Expr_` versions). Name the hidden type with an import - then `Type[T]` is implicit:

```scala
import field.{Underlying as Field, value as fieldExpr}   // field: Expr_??; Scala 2 needs -Xsource:3 for `as`
Existential[EvalOverride, Port](someOverride)            // build one yourself: Existential[F, A](value: F[A]) needs Type[A]
existential.mapK[G](tpe => fa => ...)                    // change F keeping the same Underlying
```

Do not use `Underlying` (a path-dependent type) inside `Expr.quote` on Scala 2 - move that quote into a method with a
real type parameter (see `hearth-cross-quotes`).

## Gotchas

- **`Cannot semi-evaluate apply: demo.LocalConf is compiled together with the code expanding the macro, so it cannot be loaded at compile time`** -> the type/object lives in the module (or test scope) that calls the macro. `semiEval`, `ExprCodec.derived(...).fromExpr` (silently `None`) and `Type.classOfType` all need classes the compiler can load: types from your macro module or another dependency. Tell users to put compile-time configuration types in a separate module.
- **Scala 2, Hearth 0.4.5: `Method 'apply' invocation failed: argument type mismatch`** for `List("a")`, `Vector(1)`, `Map("a" -> 1)` - a factory call with exactly **one** vararg element (two or more, and `Seq(x)`, work; Scala 3 is fine). `ExprCodec.derived(...).fromExpr` returns `None` for such fields. Until fixed upstream: document `Seq(x)`/2+ elements for users, or catch it and report a clear error.
- **`Cannot semi-evaluate mutable: it is a var, and its value at compile time is not its value at runtime`** / **`Cannot semi-evaluate a lambda whose body uses an if`** (`a match`, `a while loop`, `a local definition`, ...) -> by design; ask for a `val` or a simpler lambda, or supply an `EvalOverride`.
- **`ExprCodec.derived[Foo].toExpr failed: Cannot semi-quote value of type Foo`** (compile error at the user's call site) -> `Foo` (or a field type) is a plain class. Quote it yourself in a `QuoteOverride` and call `Expr.semiQuote(value, overrides)` instead of `derived`. The messages contain ANSI colours - do not assert on them verbatim.
- **Your own `implicit ExprCodec[X]` is ignored by `ExprCodec.derived`** -> it searches the user's call site; pass `EvalOverride`/`QuoteOverride`s explicitly.
- **`Type.StringCodec cannot be used as an extractor in a pattern because it lacks an unapply or unapplySeq method`** (Scala 2: `method StringCodec is not a case class, nor does it have a valid unapply/unapplySeq member`) -> use `Type.StringCodec.fromType(tpe).map(_.value)` or `Type.unapply(tpe)` with a `Type[String]`-typed `tpe`.
- **`val t: Type[5] = Type(5)` prints `java.lang.Integer`, `Type.unapply[5](t)` is `None`** -> the singleton expected type selects the object codec; write `val t: Type[Int] = Type(5)`.
- **`scala.MatchError` from generated code** -> `matchOn` without a fallback arm.
- **`m(xs*)` handled as "no arguments"** (Scala 3) or as one `Seq`-typed `Expr[A]` (Scala 2) -> check `toIterableOption`.
- **`NullPointerException` during expansion with overrides** -> the override dispatcher returned `null` for an unhandled type (it is called for every sub-tree's widened type); always return `Existential[EvalOverride, Any](EvalOverride.none[Any])` (`QuoteOverride.none` for `semiQuote`).
- **`Upcasting can only be done to type proved to be super type!`** -> `upcast` only widens; narrow with `.asInstanceOf[B]` inside `Expr.quote`.
- **Code depends on `expr.tpe` being `A`** -> it may be a subtype (e.g. `String` for an `Expr[Any]`); use the `Type[A]` you were given.

## Reference

- Docs: [Expression operations](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#expression-operations), [semiEval](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#exprsemieval), [semiQuote](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#semiquote), [ExprCodec](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#exprcodec), [TypeCodec](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#typecodec), [Existential types](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#existential-types), [VarArgs](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#varargs), [FreshName](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#freshname), [MatchCase](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#matchcase), [ValDefs](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#valdefs).
- Sources: [Exprs.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Exprs.scala), [ExprCodecDerivation.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/ExprCodecDerivation.scala), [Existentials.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Existentials.scala); override examples in [ExprCodecFixturesImpl.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-tests/src/main/scala/hearth/typed/ExprCodecFixturesImpl.scala).
