---
name: hearth-testing
description: >-
  Testing Scala 2.13 / Scala 3 macros with hearth-munit (`"com.kubuszok" %%% "hearth-munit" % ... % Test`) and
  hearth.data.Data - hearth.Suite (group, ==>, <==> structural diff for Data and String, "name".ignoreOnScala2_13 /
  ignoreOnScala3 / ignoreOnJvm / ignoreOnJs / ignoreOnNative, stripANSI), hearth.MacroSuite (compileErrors("...")
  .check / .checkNot / .arePresent() for expected compilation errors), hearth.ScalaCheckSuite (property, ===,
  AssertEq), the fixture pattern of a macro returning Expr[Data] (Data.map, Data.list, Data(...), Expr(data)), Data
  accessors / fold / diff / render, Data.parseString / parseList and how -Xmacro-settings values are parsed
  (Environment.typedSettings). Use when writing or debugging tests for a macro, reading a "<==> assertion failed (diff
  from expected)" or "Error message did not contain expected snippet" failure, or parsing macro settings into Data.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Testing macros with hearth-munit and `Data`

How to test a macro (Hearth-based or not): put small **fixture macros** next to the macro, have each return many
facts at once as a `hearth.data.Data` value, and compare the whole value in an MUnit spec with `<==>`, which prints a
per-field diff. Expected compilation errors are checked with `MacroSuite.compileErrors`.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala
`//> using dep`); if it differs, prefer the docs for that version:
https://scala-hearth.readthedocs.io/en/0.4.5/best-practices/#how-to-test-macros-effectively and
https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/ (`data.Data`, Macro Settings) (replace `0.4.5`).

## Setup

```scala
// sbt (%% for JVM only, %%% for JVM/Scala.js/Scala Native)
libraryDependencies += "com.kubuszok" %%% "hearth-munit" % "0.4.5" % Test
// Scala CLI
//> using test.dep com.kubuszok::hearth-munit::0.4.5
```

`hearth-munit` 0.4.5 brings `hearth`, MUnit 1.3.6 and ScalaCheck 1.20.0 transitively. Register MUnit as the test
framework as usual (sbt does it automatically for MUnit 1.x).

A macro cannot be expanded in the compilation unit that defines it: keep the macro and its fixtures in `main` (or a
separate module) and the specs in `test`.

## Suites

All three are in package `hearth`.

| Trait                    | Adds                                                                                    |
|--------------------------|-----------------------------------------------------------------------------------------|
| `hearth.Suite`           | extends `munit.BaseFunSuite`; `group`, `==>`, `<==>`, `ignoreOn*`, `stripANSI`           |
| `hearth.MacroSuite`      | `Suite` + `compileErrors("code").check(...)` / `.checkNot(...)` / `.arePresent()`        |
| `hearth.ScalaCheckSuite` | `Suite` + `property(name)(prop)`, `a === b`, Arbitrary for `NonEmptyList`/`NonEmptyVector`/`NonEmptyMap`/`MIO`/`MEval` |

```scala
import hearth.data.Data

final class MyMacroSpec extends hearth.MacroSuite {

  group("typeInfo") {                                  // test name becomes "typeInfo / case class"
    test("case class") {
      TypeInfoFixtures.typeInfo[mylib.model.Point] <==> Data.map(
        "plainPrint" -> Data("mylib.model.Point"),
        "shortName" -> Data("Point"),
        "isCaseClass" -> Data(true),
        "isSealed" -> Data(false)
      )
    }
  }

  test("only on Scala 3".ignoreOnScala2_13) { ... }    // also ignoreOnScala3, ignoreOnJvm, ignoreOnJs, ignoreOnNative
  test(munit.TestOptions("x").ignoreOnJs) { ... }      // same methods on TestOptions

  test("rejects non-case classes") {
    compileErrors("mylib.fixtures.TypeInfoFixtures.onlyCaseClasses[mylib.model.Shape]")
      .check("mylib.model.Shape is not a case class")  // snippets must appear in this order; gaps allowed
    compileErrors("mylib.fixtures.TypeInfoFixtures.onlyCaseClasses[mylib.model.Point]")
      .checkNot("not a case class")                    // passes for code that compiles ("" has no snippets)
    compileErrors("...").arePresent()                  // just "compilation failed"
  }
}
```

Assertions:

- `actual ==> expected` - plain `==` (arrays compared element-wise); failure message
  `==> assertion failed:` / `  <actual> != <expected>` / `at <file>:<line>`.
- `actual <==> expected` - for two `Data` or two `String`s. `Data`: structural diff by path. `String`: compared line
  by line, ignoring ANSI colors, failure lists only differing lines. Prefer these for fixture results and error
  messages.
- `"text".stripANSI` - remove color codes before comparing with `==>`.
- `compileErrors(code)` is MUnit's macro: it returns the error output as a `String` (`""` if the code compiles), and
  `check`/`checkNot` strip ANSI before matching. Errors reported by macros (`reportErrorAndAbort`, `c.abort`) are
  captured too - verified on Scala 2.13 and 3.

Real `<==>` failure output (`-` = expected, `+` = actual):

```
<==> assertion failed (diff from expected):
a:
  - 2
  + 1
b[1]:
  - null
  + "y"
c:
  - true
  + null
at TypeInfoSpec.test.scala:51
```

A missing map key or list element is shown as `null`.

ScalaCheck:

```scala
final class PropSpec extends hearth.ScalaCheckSuite {
  import org.scalacheck.Prop.forAll
  property("roundtrip") { forAll { (i: Int) => Data(i) === Data(i) } }  // === uses <==> for Data/String
  group("grp") { property("unit body") { forAll((s: String) => s.length ==> s.length) } }  // Unit bodies allowed
}
```

`===` dispatches through `AssertEq`: `<==>` for `Data` and `String`, runs `MIO`/`MEval` and compares results,
`==>` otherwise. Reproduce a failure with `override def scalaCheckInitialSeed = "<seed from the failure>"`; tune with
`override protected def scalaCheckTestParameters`. There is no `Arbitrary[Data]`.

## The fixture pattern: one expansion, many facts

A fixture macro computes everything you want to check about one input and returns `Expr[Data]`; `Expr(data)` works
through the built-in `ExprCodec[Data]`. With Hearth, write the logic once in a trait over `MacroCommons` and add thin
per-version adapters (only the one you need if you are single-version). This compiles as is on Scala 3 (no
cross-quotes plugin needed, since it uses no `Expr.quote`) and on Scala 2.13:

```scala
// main, shared by Scala 2 and 3
package mylib.fixtures

import hearth.MacroCommons
import hearth.data.Data

trait TypeInfoFixturesImpl { this: MacroCommons =>

  def typeInfo[A: Type]: Expr[Data] = Expr(
    Data.map(
      "plainPrint" -> Data(Type.plainPrint[A]),
      "shortName" -> Data(Type.shortName[A]),
      "isCaseClass" -> Data(Type.isCaseClass[A]),
      "isSealed" -> Data(Type.isSealed[A])
    )
  )

  def onlyCaseClasses[A: Type]: Expr[Data] =
    if (Type.isCaseClass[A]) Expr(Data(Type.shortName[A]))
    else Environment.reportErrorAndAbort(s"${Type.plainPrint[A]} is not a case class")
}
```

```scala
// main, Scala 3 adapter
package mylib.fixtures

import hearth.data.Data
import scala.quoted.*

final private class TypeInfoFixtures(q: Quotes) extends hearth.MacroCommonsScala3(using q), TypeInfoFixturesImpl

object TypeInfoFixtures {
  inline def typeInfo[A]: Data = ${ typeInfoImpl[A] }
  private def typeInfoImpl[A: Type](using q: Quotes): Expr[Data] = new TypeInfoFixtures(q).typeInfo[A]
  // onlyCaseClasses: same shape
}
```

```scala
// main, Scala 2.13 adapter
package mylib.fixtures

import hearth.data.Data
import scala.language.experimental.macros
import scala.reflect.macros.blackbox

final private class TypeInfoFixtures(val c: blackbox.Context) extends hearth.MacroCommonsScala2 with TypeInfoFixturesImpl {
  def typeInfoImpl[A: c.WeakTypeTag]: c.Expr[Data] = typeInfo[A]
}

object TypeInfoFixtures {
  def typeInfo[A]: Data = macro TypeInfoFixtures.typeInfoImpl[A]
}
```

Guidelines:

- One fixture per scenario family, many keys per fixture; add keys instead of new macros (each macro costs compile
  time and two adapters).
- Put values that differ between Scala 2 and 3 (tree printing, positions) into keys you can override per version, or
  normalize them in the fixture (`removeAnsiColors`, trimming paths) so one expected `Data` works on both.
- Turn failures into data instead of aborting when you want to assert on them: `Data(s"<failed: $error>")`.
- Never unwrap results manually (`result.asMap.get("field")...`) in specs - you lose the diff. Compare the whole
  structure with `<==>`.

## `Data` in brief

JSON-like value: null, `Int`, `Long`, `Float`, `Double`, `Boolean`, `String`, `List[Data]`, `Map[String, Data]`.
Build with `Data()`, `Data(x)`, `Data.list(...)`, `Data.map(k -> v, ...)` (keeps insertion order); read with `fold`,
`asInt`/.../`asMap`, `get(key)`, `get(index)`, `getOrElse`; compare with `diff` / `<==>`; print with `render`.
Full API, parsing rules for `-Xmacro-settings` (`42` Int, `42L` Long, `1.5f` Float, `"x"` String, ...) and
examples: [data.md](data.md).

## Gotchas

- **`Error message did not contain expected snippet`** - `check` searches the snippets **in order** in the
  ANSI-stripped message; a snippet that occurs earlier than the previous one fails. Also the wording differs per
  compiler: Scala 3 `Found: ... Required: ...`, Scala 2 `type mismatch; found : String("a") required: Int`. Split
  version-specific checks with `.ignoreOnScala2_13` / `.ignoreOnScala3`.
- **`compileErrors` returns `""` for code you expected to fail** - the snippet is type-checked at the
  `compileErrors` call site, with that site's imports; prefer fully qualified names so the snippet means the same
  everywhere.
- **`cannot compile dynamic expressions, only constant literals.`** (Scala 2) - pass a string literal to
  `compileErrors`, not a `val`.
- **Fixture changes are not picked up / old results** - incremental compilation does not re-expand a macro whose
  call site did not change. Clean the test module after changing macro or fixture code.
- **Scala 2 `macro implementation not found: ...` / Scala 3 `Cannot call macro method ... defined in the same
  source file`** - the macro is expanded in the compilation unit that defines it. Fixtures go to `main` or another
  module.
- **`<==>` passes although types differ** - numeric values compare by value across kinds: `Data(1) <==> Data(1L)`
  passes (`Data(1) == Data(1L)` is `true`), only `render` differs (`1` vs `1L`). If the numeric kind matters, assert
  on it explicitly (e.g. `Data(d.asLong.isDefined)`) or compare `render`.
- **Map key order** - `<==>`/`diff` compare maps by key; order does not matter for the assertion, but `render`
  follows insertion order.
- **Diffs full of escape codes** - `prettyPrint` output contains ANSI; store `plainPrint` or strip colors in the
  fixture. String `<==>` ignores ANSI, `Data` `<==>` does not.
- **Test runs on the wrong platform** - `ignoreOn*` is decided by the Hearth artifact linked into the tests
  (`LanguageVersion.byHearth`, `Platform.byHearth`), i.e. the platform/version the test is compiled for.
- **`hearth-munit` in a fat JAR / production classpath** - add it with `% Test` (`test.dep` in Scala CLI).
- **Docs say ScalaCheckSuite has `Arbitrary` for `Data`** - it does not in 0.4.5; write a `Gen` yourself.

## Reference

- Docs: [Best Practices - testing](https://scala-hearth.readthedocs.io/en/0.4.5/best-practices/#how-to-test-macros-effectively),
  [Basic Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/) (`data.Data`, Macro Settings).
- Sources: [Suite.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-munit/src/main/scala/hearth/Suite.scala),
  [MacroSuite.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-munit/src/main/scala/hearth/MacroSuite.scala),
  [ScalaCheckSuite.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth-munit/src/main/scala/hearth/ScalaCheckSuite.scala),
  [DataCommons.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/data/DataCommons.scala).
- Hearth's own fixtures as larger examples:
  [hearth-tests fixtures](https://github.com/kubuszok/hearth/tree/0.4.5/hearth-tests/src/main/scala/hearth/typed),
  [specs](https://github.com/kubuszok/hearth/tree/0.4.5/hearth-tests/src/test/scala/hearth/typed).
- Related skills: `hearth-getting-started` (project layout), `hearth-debugging` (seeing generated code),
  `hearth-runtime-utilities`.
