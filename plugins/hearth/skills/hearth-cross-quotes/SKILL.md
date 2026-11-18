---
name: hearth-cross-quotes
description: >-
  Hearth Cross Quotes for Scala 2.13 + Scala 3 macros - Expr.quote, Expr.splice, Type.of, Type.Ctor1.of / Type.CtorN
  (apply, unapply, setA, setB, fromUntyped), Type.Lazy, passQuotes / withQuotes / withMacroEntryCtx for native
  Scala 3 quotes, and fixes for their errors - "forward reference to value", "':' expected but identifier found",
  errors at `<macro>:line:col`, "not found: value ..." from path-dependent `Underlying` types, "free type variable",
  ScopeException "different Quotes context" / "Expression created in a splice was used outside of that splice",
  "Install cross-quotes-plugin to use this method". Use when writing or debugging quoted code in a Hearth macro.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth Cross Quotes

`Expr.quote`/`Expr.splice`/`Type.of` let one quoted-code source compile on Scala 2.13 (rewritten into quasiquotes by a macro) and Scala 3 (rewritten into `'{}`/`${}` by the `hearth-cross-quotes` compiler plugin). The rewrite happens once, when the macro library compiles. Optional for single-version macros, recommended for cross-compiled ones.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/ (replace `0.4.5`).

Setup: the plugin is needed on Scala 3 only (`compilerPlugin("com.kubuszok" %% "hearth-cross-quotes" % "0.4.5")`, see `hearth-getting-started`).

## Core usage

```scala
trait MyMacros { this: hearth.MacroCommons =>

  // Expr.quote: write the code you want generated; Expr.splice: weave an Expr into it
  def plusOne(e: Expr[Int]): Expr[Int] = Expr.quote(Expr.splice(e) + 1)

  // type parameters must come with a Type context bound - it is passed to the quote automatically
  def describe[A: Type](e: Expr[A]): Expr[String] = Expr.quote(Expr.splice(e).toString)

  // lambdas and local defs inside quotes are fine, also nested quote-in-splice
  def mapper[A: Type]: Expr[A => String] = Expr.quote { (a: A) => Expr.splice(describe[A](Expr.quote(a))) }
}
```

Rules:

- `Expr.splice` only **directly inside** an `Expr.quote`, and only on an `Expr`.
- Everything a quote references must exist at the **expansion site**: fully-qualified/global symbols, the quote's own locals, or spliced `Expr`s. Never macro-internal values (`??`, `Expr_??`, `Type`s, cases of your ADTs) - compute those outside the quote.
- Keep quotes small and simple; push logic into Scala code around them, or into a runtime helper method called from the quote.

## `Type.of` and type constructors

```scala
private object Types {               // or fields of the macro trait
  val StringT: Type[String] = Type.of[String]
  val OptionCtor: Type.Ctor1[Option] = Type.Ctor1.of[Option]
  val EitherCtor: Type.Ctor2[Either] = Type.Ctor2.of[Either]
  def ShowOf[A: Type]: Type[Show[A]] = Type.of[Show[A]]
}

def analyze[In: Type]: Expr[String] = Type[In] match {
  case Types.OptionCtor(a)      => import a.Underlying as A; Expr(s"Option of ${Type[A].plainPrint}")
  case Types.EitherCtor(l, r)   => Expr(s"Either of ${l.plainPrint} and ${r.plainPrint}")
  case t if t =:= Types.StringT => Expr("String")
  case _                        => Expr("unknown")
}
```

- `Type.CtorN.of` exists for N = 1..22; `.apply[A]` builds `Type[F[A]]` (needs `Type[A]` in scope), `.unapply` decomposes (also subtypes, via the base type, on both Scala versions). Bounded variants: `Type.Ctor1.UpperBounded.of[U, F]`, `Type.Ctor1.Bounded.of[L, U, F]`.
- Partial application: `Type.Ctor2.of[Either].setA[String]` (=> `Ctor1[Either[String, *]]`), `.setB[Int]` (=> `Ctor1[Either[*, Int]]`). Setters are named by parameter letter (`setA`, `setB`, `setC`, ...; there is no `setLast`, although older docs show it); apply several from the **back** (`setC`, then `setB`, then `setA`) so the letters stay stable.
- Untyped interop: `ctor.asUntyped`, `Type.Ctor1.fromUntyped[F](untyped)`; unknown constructors: `Type.decompose1[A]` (see `hearth-hkt-derivation`).
- Compare types with `=:=`/`<:<`, never with `==` or backtick patterns: Scala 3 `Type`s do not override `equals`, so ``case `stringType` =>`` works on 2.13 and silently fails on 3.
- **Helper `Type`s in fields:** an eager `val X = Type.of[X]` is computed on every expansion, and is safe only because of *when* the enclosing object initializes (an object first touched inside an `Expr.splice` behaves like a `lazy val`); a plain `lazy val` is unsafe on Scala 3 (bound to the first splice that forces it). Use `Type.Lazy`:

```scala
private val StringType: Type.Lazy[String] = Type.Lazy(Type.of[String])
def m: Expr[String] = { implicit val S: Type[String] = StringType; Expr.quote("x") }
```

## Local type parameters inside splices

A method defined inside a quote may use its own type params in a splice (`def map[A, B](...) = Expr.splice { ... }`). Pass `Type.of[A]` **at the call site** where a helper expects implicit `Type`s:

```scala
Expr.quote {
  new Functor[F] {
    def map[A, B](fa: F[A])(f: A => B): F[B] = Expr.splice {
      mapBody[F, A, B](Expr.quote(fa), Expr.quote(f))(Type.of[A], Type.of[B])
    }
  }
}
```

Do not write `implicit val evA: Type[A] = Type.of[A]` for such an abstract `A` - there is nothing to materialize it from. On Scala 2 these local params are "free types" that do not cross into a **separately expanded** quote: if `mapBody` itself does `Expr.quote { ... }` mentioning `A`, Scala 2 fails with "free type variable A". Keep quotes that mention local type params inline in the splice body (helpers may do non-quoting work), or use the erased approach from `hearth-hkt-derivation`.

## Scala 3 `Quotes` scoping

- Each `Expr.splice` opens its own nested `Quotes`. An `Expr` created inside one splice must not be used in a sibling splice of the same quote ("Expression created in a splice was used outside of that splice", under `-Xcheck-macros`). For multi-method instances derive everything **before** the outer quote and call cached `def`s by name from each splice - see `hearth-def-caching`.
- Store results of builders (`LambdaBuilder...build`, `ValDefBuilder`) in a **`def`**, not a `val`, when they are later spliced into another `Expr.quote`; a `val` captures the outer `Quotes`. Same for `mio.unsafe.runSync` results.
- Native `'{...}`/`${...}` in a Scala 3-only macro that also uses Hearth builders: wrap each quote with `withQuotes { ... }` and each splice body with `passQuotes { ... }`. Not needed with Cross Quotes.
- Memoizing an `Expr` across splices (Scala 3-only code): `withMacroEntryCtx(expr)` builds it with the entry `Quotes`. In cross-compiled code do not memoize `Expr`s across splices: produce them from a `def` (re-evaluated per splice), or derive everything before the outer quote and call cached defs (`hearth-def-caching`). Keep helper `Type`s in `Type.Lazy`; `Type.Cache` is safe across splices only because it recomputes per splice scope.

## Gotchas

- **`forward reference to value X defined on line N extends over definition of value Y`** -> `implicit val t: Type[A] = Type.of[A]` makes the native summoner pick up the val being defined (older Hearth / abstract `A`). Since Hearth 0.4.0 (kubuszok/hearth#285) the defined val is excluded for statically-known types (fully for fields of objects/classes on Scala 2 since 0.4.4; sibling `implicit val` fields forcing each other on Scala 3 fixed in 0.4.1); otherwise compute it in a scope without the implicit: `private val AType = Type.of[A]` then `implicit val t: Type[A] = AType`, or take `[A: Type]`.
- **`':' expected but identifier found`** around `companionExpr_??: Expr_??` -> identifier ending with `?`/symbol char followed by `:` -> add a space: `companionExpr_?? : Expr_??`.
- **Scala 2 error at `.../<macro>:row:col`** (e.g. `expected ")" but found identifier`) -> the error is in the quasiquote Cross Quotes generated by printing your quote. Simplify that quote: move logic out, split nested blocks, call a runtime helper, avoid exotic syntax; enable logging (below) to see the generated source; report a minimal reproducer to kubuszok/hearth.
- **Expansion fails with generated code mentioning `someValue.Underlying`** / Scala 2 **`not found: value param`** -> a path-dependent type (`import param.tpe.Underlying as Field`) used inside a quote was not substituted. Move the quote into a helper with a regular type parameter: `def mk[F: Type](e: Expr[F]): Expr[...] = Expr.quote { ... }` and call `mk[Field](...)`. Report it if a plain context bound does not help.
- **`??`/`Expr_??` inside `Expr.quote`** (Scala 2 reification failures, e.g. `Option[MyImpl.this.??]`) -> compute the value in a `val` before the quote.
- **Scala 2 `object Trees is not a member of package scala.reflect.api`** with refined/structural types built in nested quotes -> construct the value in a runtime helper method and call it from the quote.
- **"is never used" warnings for implicit `Type`s needed only by a quote** (fatal under `-Xfatal-warnings`) -> put them in a named `def` annotated `@scala.annotation.nowarn("msg=is never used")`.
- **`Install cross-quotes-plugin to use this method`** (compile error in the Scala 3 macro module, from `@compileTimeOnly`) -> plugin missing on Scala 3.
- **Scala 3 plugin rewrites syntactically**: it assumes `Type`, `Expr`, `Expr.quote` are the `MacroCommons` ones. Mixing `scala.quoted.Type.of`/`'{}` with Cross Quotes in one file, or your own `quote`/`splice` methods, is undefined behaviour (often a compiler crash).
- **Type aliases / kind-projector in `Type.CtorN.of`** are not supported on Scala 2 -> use the full constructor and `setA`/`setB`/... (applied from the back).
- **`Type.CtorN.UpperBounded.of`/`Bounded.of` `.unapply` ignores the bounds** (open issue kubuszok/hearth#400) -> check `<:<` on the extracted types yourself.
- Hearth before 0.4.1 broke `val List = Type.Ctor1.of[List]` (value named like the type) on Scala 2 - prefer distinct names (`ListCtor`) anyway.

## Debugging the rewrite

```scala
// Scala 3
scalacOptions += "-P:hearth.cross-quotes:logging=true"           // or a |-separated list of files
// Scala 2.13
scalacOptions += "-Xmacro-settings:hearth.cross-quotes.logging=true"
```

Instead of `true` you can pass a `|`-separated list of `File.scala`, `File.scala:line` or `File.scala:line:col` (not a comma-separated one: the compiler splits `-Xmacro-settings` on commas). Prints how each quote was rewritten while compiling the macro library. Clean before recompiling, incremental compilation does not re-run it for unchanged files.

## Reference

- [Cross Quotes docs](https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/) (limitations, known issues), [passQuotes/withQuotes](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#passquotes-and-withquotes-scala-3-only), [Type.Cache/Type.Lazy](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#typecache-and-typelazy), [FAQ](https://scala-hearth.readthedocs.io/en/0.4.5/faq/).
- More pitfalls: `hearth-cross-compilation-pitfalls`.
