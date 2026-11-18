---
name: hearth-getting-started
description: >-
  Hearth (com.kubuszok hearth, Scala macros standard library) setup and project structure for writing Scala 2.13
  and/or Scala 3 macros - sbt, Mill and Scala CLI coordinates, the hearth-cross-quotes compiler plugin for Scala 3,
  MacroCommons / MacroCommonsScala2 / MacroCommonsScala3, shared macro trait plus thin per-version adapters (`def
  ... = macro`, `inline def ... = ${ ... }`), hearth-munit tests, docs links and common misconceptions. Use when
  starting a new Hearth-based macro (type class derivation, DSL, DI, mocking), adding Hearth to a build, or wiring
  macro entry points.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth: getting started

How to add Hearth to a build and structure a macro library on top of it (single-version or cross-compiled Scala 2.13 + Scala 3). For deeper topics see the sibling skills listed at the end.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: `https://scala-hearth.readthedocs.io/en/<version>/` (latest: https://scala-hearth.readthedocs.io/en/latest/ - NOT `hearth.readthedocs.io`, an unrelated Python project). Look up versions on Maven Central (`com.kubuszok`), never guess them.

## What Hearth is (and is not)

- A **standard library for macros**: `Type`, `Expr`, `Method`, `CaseClass`, `Enum`, `SingletonValue`, `NamedTuple`, `JavaBean`, `AnonymousInstance`, `DestructuredExpr`, `ValDefsCache`/`ValDefBuilder`, `LambdaBuilder`, `MatchCase`, implicit summoning with failure reasons, `MIO` (Macro IO) for error aggregation + logging, Standard Extensions (`IsCollection`, `IsMap`, `IsOption`, `IsEither`, `IsValueType`) discovered from the classpath.
- Its main value is **corner cases already handled** (type params reapplied to subtypes/methods, singletons, opaque types, named tuples, Java enums, default values, recursive types) - useful even for a Scala 3-only or Scala 2-only macro.
- It is **not** a translation layer that runs Scala 2 macros on Scala 3, and it does not hide the native API: `UntypedType` is `c.Type`/`TypeRepr`, `UntypedExpr` is `c.Tree`/`Term`, and every `Type`/`Expr` converts both ways. Write ~90% with Hearth, drop to native code where needed.
- Not only for derivation: DI (`enclosingScope`), mocks (`AnonymousInstance`), optics/DSLs/parsers (`DestructuredExpr`).
- You may not need a macro library at all if you only quote/splice values (Scala 3 `inline`, `scala.compiletime`, `Mirror`).

Common misconceptions to correct: "Hearth is mainly for cross-compiling" (no - single-version is first-class); "Cross Quotes add overhead" (no - rewritten once when the macro library compiles); "prototype in raw `quotes.reflect` and port later" (not recommended - you rebuild the corner-case handling).

## Dependencies

Artifacts (all `com.kubuszok`): `hearth` (core, pulls `hearth-micro-fp` and `hearth-better-printers`), `hearth-cross-quotes` (Scala 3 compiler plugin; on Scala 2.13 it is a macro library pulled in transitively), `hearth-munit` (test utilities). Built against Scala 2.13 and Scala 3 LTS (3.3), JDK 11 bytecode, JVM/Scala.js/Scala Native.

**sbt** (single platform: `%%`; cross-platform with sbt-crossproject/sbt-projectmatrix: `%%%`):

```scala
libraryDependencies += "com.kubuszok" %% "hearth" % "0.4.5"
libraryDependencies += "com.kubuszok" %% "hearth-munit" % "0.4.5" % Test

// Cross Quotes: Scala 3 only, as a compiler plugin (JVM artifact, so `%%`, never `%%%`)
libraryDependencies ++= (CrossVersion.partialVersion(scalaVersion.value) match {
  case Some((3, _)) => Seq(compilerPlugin("com.kubuszok" %% "hearth-cross-quotes" % "0.4.5"))
  case _            => Seq.empty
})

// Recommended on Scala 2.13: `import x.{A as B}`, `&` types and `*` varargs used by Hearth examples
scalacOptions ++= (CrossVersion.partialVersion(scalaVersion.value) match {
  case Some((2, 13)) => Seq("-Xsource:3")
  case _             => Seq.empty
})
```

(The plugin artifact is `hearth-cross-quotes_3`; if you write the suffix by hand use `"com.kubuszok" % "hearth-cross-quotes_3" % "0.4.5"`.)

**Mill** (1.x names; Mill 0.12 uses `ivyDeps`/`scalacPluginIvyDeps`/`ivy"..."`):

```scala
def mvnDeps = Seq(mvn"com.kubuszok::hearth:0.4.5")
def scalacPluginMvnDeps = // only in the Scala 3 cross module
  Seq(mvn"com.kubuszok::hearth-cross-quotes:0.4.5")
```

**Scala CLI**:

```scala
//> using dep com.kubuszok::hearth:0.4.5
//> using test.dep com.kubuszok::hearth-munit:0.4.5
// Scala 3 file using Expr.quote/Expr.splice/Type.of:
//> using plugin com.kubuszok::hearth-cross-quotes::0.4.5
```

The plugin is needed **only** when Scala 3 code uses Cross Quotes (`Expr.quote`, `Expr.splice`, `Type.of`, `Type.CtorN.of`, `Type.CtorK1.of`, `Type.CtorN.UpperBounded.of`/`Bounded.of`). Without it, compiling the Scala 3 macro module fails with `Install cross-quotes-plugin to use this method` (a `@compileTimeOnly` error) at every such call. On Scala 2.13 it is not a compiler plugin: Cross Quotes arrive as macros through `hearth`, so do not add it there.

**Minimum Scala version of your users.** Hearth runs on Scala 2.13.16+ and 3.3 LTS+, but `summonExprIgnoring`/`Expr.summonImplicitIgnoring` (used to stop a derivation from summoning itself, see `hearth-type-class-derivation`) needs **Scala 2.13.17+ / 3.7.0+** in the module where the macro expands, and throws on older compilers. Decide the supported Scala versions before designing the macro.

## Project structure

Macros must be compiled before the code that expands them: put them in `src/main` of a library module and expand them in `src/test` or a downstream module.

### Scala 3 only

```scala
import hearth.MacroCommonsScala3
import scala.quoted.*

class MyMacro(q: Quotes) extends MacroCommonsScala3(using q) {
  def describe[A: Type](expr: Expr[A]): Expr[String] =
    Expr(s"${expr.plainPrint} : ${Type[A].plainPrint}")
}
object MyMacro {
  // Scala 3 macros must be called from a stable location: instantiate the class here
  def describe[A: Type](expr: Expr[A])(using q: Quotes): Expr[String] = new MyMacro(q).describe(expr)
}
object Api {
  inline def describe[A](inline expr: A): String = ${ MyMacro.describe('expr) }
}
```

Here `Type`/`Expr` are `scala.quoted.Type`/`Expr`, so native `'{...}`/`${...}` work - but wrap them with `withQuotes { '{ ... ${ passQuotes { ... } } ... } }` when Hearth builders (`LambdaBuilder`, `ValDefBuilder`) are involved (see `hearth-cross-quotes`). Using Cross Quotes avoids that entirely.

### Scala 2.13 only

```scala
import hearth.MacroCommonsScala2
import scala.language.experimental.macros
import scala.reflect.macros.blackbox

class MyMacro(val c: blackbox.Context) extends MacroCommonsScala2 {
  def describe[A: c.WeakTypeTag](expr: c.Expr[A]): c.Expr[String] =
    Expr(s"${expr.plainPrint} : ${Type[A].plainPrint}")
}
object Api {
  def describe[A](expr: A): String = macro MyMacro.describe[A]
}
```

### Cross-compiled (shared logic + adapters)

```
src/main/scala/mylib/MyTypeClass.scala            // type class + companion extends MyTypeClassCompanionCompat
src/main/scala/mylib/internal/MyMacrosImpl.scala  // trait MyMacrosImpl { this: MacroCommons => ... } - all the logic
src/main/scala-2/mylib/MyTypeClassCompanionCompat.scala // `def ... = macro` + Scala 2 bundle class
src/main/scala-3/mylib/MyTypeClassCompanionCompat.scala // `inline def`/`inline given` + Scala 3 class + object
```

(sbt picks up `scala-2`/`scala-3` dirs automatically; in Mill use the cross module's version-specific source folders.)

```scala
// shared: src/main/scala
package mylib
import hearth.MacroCommons
import hearth.std.StdExtensions // needed only for IsCollection/IsOption/... (both platform classes mix it in)

private[mylib] trait ShowMacrosImpl { this: MacroCommons & StdExtensions =>
  def deriveTypeClass[A: Type]: Expr[Show[A]] = ???        // returns a Show[A] instance
  def deriveInline[A: Type](value: Expr[A]): Expr[String] = ??? // inlines Show[A].show(value)
}
```

```scala
// Scala 2: src/main/scala-2
package mylib
import scala.language.experimental.macros
import scala.reflect.macros.blackbox

private[mylib] trait ShowCompanionCompat { this: Show.type =>
  implicit def derived[A]: Show[A] = macro ShowMacros.deriveTypeClassImpl[A]
  def show[A](value: A): String = macro ShowMacros.deriveInlineImpl[A]
}
private[mylib] class ShowMacros(val c: blackbox.Context) extends hearth.MacroCommonsScala2 with ShowMacrosImpl {
  // Scala 2 cannot call the shared method directly as a macro impl: forward with c.WeakTypeTag/c.Expr
  def deriveTypeClassImpl[A: c.WeakTypeTag]: c.Expr[Show[A]] = deriveTypeClass[A]
  def deriveInlineImpl[A: c.WeakTypeTag](value: c.Expr[A]): c.Expr[String] = deriveInline[A](value)
}
```

```scala
// Scala 3: src/main/scala-3 (compiled with the hearth-cross-quotes plugin)
package mylib
import scala.quoted.*

private[mylib] trait ShowCompanionCompat { this: Show.type =>
  inline given derived[A]: Show[A] = ${ ShowMacros.deriveTypeClass[A] }
  inline def show[A](inline value: A): String = ${ ShowMacros.deriveInline[A]('value) }
}
private[mylib] class ShowMacros(q: Quotes) extends hearth.MacroCommonsScala3(using q), ShowMacrosImpl
private[mylib] object ShowMacros {
  def deriveTypeClass[A: Type](using q: Quotes): Expr[Show[A]] = new ShowMacros(q).deriveTypeClass[A]
  def deriveInline[A: Type](value: Expr[A])(using q: Quotes): Expr[String] = new ShowMacros(q).deriveInline[A](value)
}
```

In shared code use **Cross Quotes** (`Expr.quote { ... Expr.splice(e) ... }`, `Type.of[A]`) - see `hearth-cross-quotes`. When Hearth lacks an API, declare an abstract method in the shared trait and implement it in each adapter with the native API; a shared macro extension can match `case MacroCommonsScala3(platformCommons) =>` / `case MacroCommonsScala2(platformCommons) =>` in a platform-specific source file.

## Imports you will need

```scala
import hearth.*                 // MacroCommons, ...
import hearth.fp.effect.*       // MIO, Log, MLocal, RenderFrom, DontRender, ...
import hearth.fp.instances.*    // Applicative/Parallel/Traverse instances (List, Option, Either, ...; MIO's are in its companion)
import hearth.fp.syntax.*       // .traverse, .parTraverse, .parMap2, ...
import hearth.std.*             // StdExtensions, Rule, Rules, ProviderResult, StandardMacroExtension
```

`Type`, `Expr`, `Method`, `CaseClass`, `Environment`, ... are members of `MacroCommons` (available inside the trait with `this: MacroCommons =>`), not top-level imports. `Environment.loadStandardExtensions()` and `IsCollection`/`IsOption`/... additionally need `StdExtensions` in the self-type (`this: MacroCommons & StdExtensions =>`). Non-MIO type classes and `NonEmptyList`/`NonEmptyVector`/`NonEmptyMap`: see `hearth-micro-fp`.

## Testing macros

`hearth-munit` provides `hearth.Suite` (`group`, `==>`, `<==>` with diffs) and `hearth.MacroSuite` (`compileErrors("code").check("expected text")`, `.checkNot(...)`, `.arePresent()`). Test every supported shape on **both** Scala versions, error messages for unsupported types, that user-provided implicits win, and recursive types. A fixture macro returning `Expr[hearth.data.Data]` lets one expansion assert many properties. Details: `hearth-testing`.

## Gotchas

- **`Install cross-quotes-plugin to use this method`** (Scala 3, when compiling the macro module) -> the `hearth-cross-quotes` plugin is missing from the Scala 3 macro module -> add it as `compilerPlugin`/`scalacPluginMvnDeps`/`//> using plugin`.
- **Plugin added with `%%%`** -> resolution fails (the Scala 3 plugin is published for the JVM only) -> add it only for Scala 3, as a JVM artifact (`%%`). On Scala 2.13 do not add it at all.
- **`HearthRequirementError: Expr.summonImplicitIgnoring on Scala 2 relies on c.inferImplicitValueIgnoring method, which is available since Scala 2.13.17`** (or `... on Scala 3 relies on Implicits.searchIgnoring method, which is available since Scala 3.7.0`) -> the code expanding the macro is compiled with an older Scala -> raise the minimum Scala version of the library, or branch on `Environment.currentScalaVersion`.
- **Macro used where it is defined** -> Scala 2: `macro implementation not found: ... (the most common reason for that is that you cannot use macro implementations in the same compilation run that defines them)`; Scala 3: `Cannot call macro ... defined in the same source file` -> move the call to tests or a dependent module.
- **Scala 2.13 parse errors on `import x.{Underlying as T}` or `A & B`** -> add `-Xsource:3` (or use `=>`/`with`).
- **Scala 3: `ScopeException ... different Quotes context`** with native quotes -> use `passQuotes`/`withQuotes` or Cross Quotes.
- **Kindlings' helpers are not Hearth.** `DerivationTimeout`, `DerivationPolicy`, `ensureStandardExtensionsLoaded`, `LoadStandardExtensionsOnce` come from Kindlings' internal `derivation-commons`; in your library use the Hearth APIs they wrap (`runToExprOrFail(timeout = ...)`, `Environment.loadStandardExtensions()`, `Environment.typedSettings`).
- **Fat JARs**: most of Hearth runs only inside the compiler. Keep `hearth.source`, `hearth.typename`, the classes directly in package `hearth`, and `hearth.data` if production code uses `Data`; everything else is compile-time only. See `hearth-runtime-utilities` (fat-jar.md) and the FAQ section "Which parts of Hearth end up in my application at runtime?" (in the [latest docs](https://scala-hearth.readthedocs.io/en/latest/faq/); added after 0.4.5).

## Reference

- API cheat sheet: [api-reference.md](api-reference.md)
- Docs: [Welcome + full `Show` walk-through](https://scala-hearth.readthedocs.io/en/0.4.5/), [Basic Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/), [Cross Quotes](https://scala-hearth.readthedocs.io/en/0.4.5/cross-quotes/), [Micro FP / MIO](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/), [Best Practices](https://scala-hearth.readthedocs.io/en/0.4.5/best-practices/), [Derivation Checklist](https://scala-hearth.readthedocs.io/en/0.4.5/derivation-checklist/), [Standard Extensions](https://scala-hearth.readthedocs.io/en/0.4.5/standard-extensions/), [Debug Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/debug-utilities/), [FAQ](https://scala-hearth.readthedocs.io/en/0.4.5/faq/), condensed overview [llms.txt](https://github.com/kubuszok/hearth/blob/0.4.5/docs/user-guide/llms.txt).
- Runnable cross-compiled demo: [hearth-tests demo `Show`](https://github.com/kubuszok/hearth/tree/0.4.5/hearth-tests/src/main/scala/hearth/demo/simple).
- Real libraries built on Hearth 0.4.5: [Kindlings 0.4.0](https://github.com/kubuszok/kindlings/tree/0.4.0) (derivation modules, `di`, `mock`, `optics`, `parser`, integrations).
- Before shipping: see the `hearth-macro-review` skill (production-readiness checklist).
- Next steps: `hearth-cross-quotes`, `hearth-type-class-derivation`, `hearth-case-classes-and-enums`, `hearth-def-caching`, `hearth-standard-extensions`, `hearth-introspection`, `hearth-expr-toolkit`, `hearth-micro-fp`, `hearth-hkt-derivation`, `hearth-expr-parsing-dsl`, `hearth-cross-compilation-pitfalls`, `hearth-debugging`, `hearth-testing`, `hearth-generated-code-performance`, `hearth-lambda-builder`.
- Using Hearth's runtime utilities (`TypeName`, `hearth.source`, versions) in ordinary code: `hearth-runtime-utilities`.
