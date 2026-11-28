# semiEval, semiQuote and codecs - reference (Hearth 0.4.5)

Verified against the 0.4.5 sources ([Exprs.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Exprs.scala), [ExprCodecDerivation.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/ExprCodecDerivation.scala), the `SemiEval` objects in [ExprsScala2.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala-2/hearth/typed/ExprsScala2.scala) / [ExprsScala3.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala-3/hearth/typed/ExprsScala3.scala)) and compile-checked with Scala 3.3.7 and 2.13.16.

## Signatures

```scala
Expr(value)                                             // Expr.apply[A: ExprCodec](value: A): Expr[A]
Expr.unapply(expr) / expr.value                         // Option[A], via ExprCodec[A].fromExpr
expr.semiEval                                           // Either[NonEmptyVector[String], A]
expr.semiEval(overrides)                                // overrides: UntypedType => Existential[EvalOverride]
Expr.semiQuote(value)                                   // needs Type[A]; Either[String, Expr[A]]
Expr.semiQuote(value, overrides)                        // overrides: UntypedType => Existential[QuoteOverride]
type EvalOverride[A]  = Option[Expr[A] => Either[String, A]]   // EvalOverride(f) / EvalOverride.none[A]
type QuoteOverride[A] = Option[A => Either[String, Expr[A]]]   // QuoteOverride(f) / QuoteOverride.none[A]
ExprCodec.derived[A]                                    // Scala 3: inline def derived[A](using Type[A]); Scala 2: macro
trait ExprCodec[A] { def toExpr(value: A): Expr[A]; def fromExpr(expr: Expr[A]): Option[A] }
```

Overrides are keyed by the **widened** type of each sub-tree (`semiEval`) or by the static type being quoted
(`semiQuote`) and are consulted before the built-in logic; compare keys with `=:=` (`tpe =:= UntypedType.fromTyped[X]`).
An override for `X` replaces evaluation of the whole `X`-typed sub-tree.

## Built-in `ExprCodec`s

| Types | Direction | Notes |
|---|---|---|
| `Null`, `Unit`, `Boolean`, `Byte`, `Short`, `Int`, `Long`, `Float`, `Double`, `Char`, `String` | both | `fromExpr` only for constants |
| `BigInt`, `BigDecimal`, `StringContext` | both | |
| `java.lang.Class[A]`, `ClassTag[A]` | both | need `Type[A]`; `fromExpr` reads `classOf[A]` / `ClassTag[A](...)` of the same `A`, and the class must be loadable |
| `Array[A]`, `IArray[A]` (Scala 3), `Seq[A]`, `List[A]`, `Nil.type`, `Vector[A]`, `Set[A]`, `Map[K, V]` | both | need `ExprCodec` and `Type` of elements |
| `Option[A]`, `Some[A]`, `None.type`, `Either[L, R]`, `Left[L, R]`, `Right[L, R]` | both | |
| `hearth.data.Data` | both | `fromExpr` uses `semiEval` |
| `HearthVersion`, `JDKVersion`, `ScalaVersion`, `LanguageVersion`, `Platform` | both | (the docs say one-way; the sources implement `fromExpr` on both Scala versions) |

`ExprCodec.derived` and `semiQuote` use a fixed built-in list: the primitives, `String`, `BigInt`, `BigDecimal`,
`Data`, and `Seq`/`List`/`Vector`/`Set`/`Option`/`Map`/`Either` whose elements are themselves in that list.

## What `semiEval` evaluates

- Literals; arithmetic, comparison, bitwise and boolean operators on primitives; `String +`.
- Objects on the classpath (`None`, `Nil`, your `object`s) and their members (`Settings.default`, `Cfg.create(42)`, chains).
- Constructor calls (`new Foo(...)`), method calls on evaluable receivers (overloads, varargs, named and default
  arguments), methods reached through implicit value classes (`StringOps`, `RichInt`: `"abc".capitalize`, `1.max(2)`), methods inherited by objects (`Predef`).
- Blocks of `val`s (including compiler-generated ones), `isInstanceOf`/`asInstanceOf`, synthesized `ValueOf`.
- Lambdas of any arity (Scala 3; up to 22 on Scala 2) whose body has no `match`, `if`, loops, `try`, `return`,
  assignments or local definitions - the body runs when the function is applied.
- Scala 3 only: references to immutable local `val`s outside the tree are replaced by their right-hand side (so the
  non-`inline` arguments of an `inline def` are evaluable). Scala 2 cannot read them.
- Java enum values and other Java static fields (`java.math.RoundingMode.FLOOR`, `java.io.File.separator`), also
  qualified and nested in other expressions - e.g. an annotation argument read with `decodedConstructorArguments`.

## What it refuses (and the messages)

| Message (prefix) | Cause |
|---|---|
| `Cannot semi-evaluate <name>: <Class> is compiled together with the code expanding the macro, so it cannot be loaded at compile time` | class/object from the module where the macro expands (also when stale class files exist, so clean and incremental builds agree) |
| `Cannot semi-evaluate <name>: it is a var, and its value at compile time is not its value at runtime` | `var` member |
| `Cannot semi-evaluate a lambda whose body uses an if` (`a match`, `a while loop`, `a try`, `a return`, `an assignment`, `a class definition`, `a local definition`) | unsafe lambda body |
| `Cannot semi-evaluate statement: ...` / `Cannot semi-evaluate expression: ...` | `def`, `lazy val`, class, `match`, `if` ... outside lambdas, or any unsupported tree |
| `Cannot resolve module: ...`, `Cannot resolve class for constructor: ...`, `Cannot resolve enum value: ...` | class not on the compiler's classpath |
| `Method 'm' threw: ...`, `Constructor threw: ...` | the evaluated code threw |
| `Method 'apply' invocation failed: argument type mismatch` | Scala 2 in 0.4.5: a factory call with exactly one vararg element (`List("a")`, `Vector(1)`, `Map(k -> v)`); two or more elements and `Seq(x)` work |
| `No method 'm' with N parameters found on ...`, `Cannot invoke method ...` | reflection could not find a matching method |
| `Cannot semi-evaluate ...: reflection failed with java.lang.LinkageError ...` | a method signature mentions a class that cannot be loaded |

All failures are aggregated in the `NonEmptyVector`. `fromExpr` of a derived codec throws them away (`toOption`) - call
`semiEval` yourself when you want to show users why their value is not compile-time evaluable.

## `semiQuote` / `ExprCodec.derived`

Order: override -> built-in list above -> `SingletonValue` (reference to the object/enum case) -> `CaseClass`
(fields via `productElement`, rebuilt with the primary constructor: `new demo.Config(...)`) -> `Enum` (singleton
children matched by value, others by the value's runtime class; the result is upcast to the parent). Otherwise
`Left("Cannot semi-quote value of type <T>")` (also `Unknown return type for field ...`, `Failed to construct ...`,
`No child of <T> matches runtime class ...`).

`ExprCodec.derived[A]`:

- traverses `A` (case-class fields, enum children) and, for every nested non-built-in type `F`, searches an implicit
  `ExprCodec[F]` at the macro call site and `semiEval`s it into an override - in practice only instances reachable
  from user code, never the local implicits of your macro;
- `toExpr` = `semiQuote` with those overrides; failure aborts compilation with
  `ExprCodec.derived[<A>].toExpr failed: <reason>`;
- `fromExpr` = `Expr.semiEval(expr, overrides).toOption`.

## `TypeCodec`

```scala
trait TypeCodec[U] { def toType[A <: U](value: A): Type[A]; def fromType[A](tpe: Type[A]): Option[Existential.UpperBounded[U, Id]] }
Type(value)          // Type.apply[A](value: A)(implicit TypeCodec[A]): Type[A]
Type.unapply(tpe)    // Type.unapply[A](tpe: Type[A])(implicit TypeCodec[A]): Option[A]
```

| Types | Direction |
|---|---|
| `Null`, `Unit`, `Boolean`, `Byte`, `Short`, `Int`, `Long`, `Float`, `Double`, `Char`, `String` | both (`Type.IntCodec`, `Type.StringCodec`, ...; also as implicits in `TypeCodec`) |
| `Tuple1`..`Tuple22`, Scala 3 `*:` tuples | both |
| `Option`, `Some`, `None.type`, `Either`, `Left`, `Right` | both |
| objects on the classpath (`ModuleCodec`, chosen for any `A <: Singleton`) | both |
| `Array`, `Seq`, `List`, `Nil.type`, `Vector`, `Map`, `Set`, `Class`, `ClassTag` | `toType` only |

Because the object codec matches any singleton type, `val t: Type[5] = Type(5)` resolves to it and produces
`java.lang.Integer`; keep the expected type wide (`Type[Int]`).
