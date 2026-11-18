---
name: hearth-runtime-utilities
description: >-
  Hearth's runtime utilities for ordinary (non-macro) Scala 2.13 / Scala 3 code and library APIs - hearth.source
  (`import hearth.source._`, MethodName, Line, File, FileName, Location, Text[T] / Text.generate for assert-style
  messages), hearth.typename (`TypeName[A]`, `[A: TypeName]`, plainPrint / simplePrint / shortPrint / prettyPrint,
  custom TypeName instances injected into type arguments), version values in package hearth (JDKVersion
  runtimeJDKVersion / compiletimeJDKVersion, ScalaVersion byJVMRuntime / byCompileTime, LanguageVersion.byHearth,
  Platform.byHearth, HearthVersion.byHearthLibrary), which Hearth packages to keep in a fat JAR / sbt-assembly, and
  hearth.debug.Debug for inspecting any macro. Use when code calls these APIs, gets "No file found for position",
  Scala.js/Native linking errors about java.lang.reflect, `List[A]` instead of the real type name, or
  NoClassDefFoundError hearth/... after shrinking a JAR.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth runtime utilities

Hearth is a library for writing macros, but a few of its packages are meant for **ordinary code**: values that a
macro fills in at the call site (source location, type names, versions) and then your program uses at runtime. No
compiler plugin or flags are needed; add the dependency and import.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala
`//> using dep`); if it differs, prefer the docs for that version:
https://scala-hearth.readthedocs.io/en/0.4.5/source-utilities/,
https://scala-hearth.readthedocs.io/en/0.4.5/typename-utilities/ and
https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#versions (replace `0.4.5`).

```scala
// sbt (use %% for JVM-only, %%% for JVM/Scala.js/Scala Native)
libraryDependencies += "com.kubuszok" %%% "hearth" % "0.4.5"
// Scala CLI
//> using dep com.kubuszok::hearth::0.4.5
```

All examples below were compiled and run with Hearth 0.4.5 on Scala 3.3.7, 3.7.4, 2.13.16 and 2.13.18 (JVM); quoted
output is real.

## `hearth.source` - where was I called from?

| Type             | Is                         | Value                                                                  |
|------------------|----------------------------|------------------------------------------------------------------------|
| `MethodName`     | subtype of `String`        | name of the innermost enclosing method; `<init>` in a class/object body or a top-level `val` |
| `Line`           | subtype of `Int`           | 1-based line of the call site                                          |
| `File`           | subtype of `String`        | **absolute** path of the source file, `/`-separated                    |
| `FileName`       | subtype of `String`        | last path segment, e.g. `Main.scala`                                   |
| `Location`       | `case class (file: File, line: Line)` | `toString` = `s"$file:$line"`, `.fileName: FileName`        |
| `Text[T]`        | `case class (value: T, source: String)` | `toString` = `s"$source = $value"`                        |

`MethodName`/`Line`/`File`/`FileName` are abstract subtypes (zero-cost, no wrapper). Each companion has an implicit
`derived` macro (`implicit def` on Scala 2, `inline given` on Scala 3), so `implicitly[Line]` / `summon[Line]` /
`Line.derived` materialize it; build one by hand with `Line.wrap(42)`, `MethodName.wrap("foo")`, etc. `Location` is
derived from the implicit `File` and `Line`.

**Take them as implicit parameters** - then the value describes the caller, not your helper:

```scala
import hearth.source._  // Scala 3: hearth.source.*

object Log {
  def debug(msg: String)(implicit method: MethodName, line: Line, file: FileName): Unit =
    println(s"[$file:$line $method] $msg")
  def where(implicit loc: Location): String = loc.toString
}

object Main {
  def main(args: Array[String]): Unit = {
    Log.debug("hello")                               // [Main.scala:35 main] hello
    List(1).foreach { _ => Log.debug("in lambda") }  // [Main.scala:36 main] in lambda  (lambdas are skipped)
    val loc = implicitly[Location]
    println(s"${loc.fileName}:${loc.line}")          // Main.scala:37
  }
}
```

### `Text[T]` - value plus its source code (since 0.4.0)

`Text.generate` is an implicit conversion macro: any argument passed where a `Text[T]` is expected is captured with
the source text of the expression (trimmed; falls back to a printed tree when the compiler has no source). No
`import scala.language.implicitConversions` is needed at the call site.

```scala
import hearth.source._

def check(cond: Text[Boolean]): Unit =
  if (!cond.value) throw new AssertionError(s"Failed: ${cond.source}")

val a = 1; val b = 2
check(a + b == 4)               // AssertionError: Failed: a + b == 4
Text.generate("abc".length)     // value = 3, source = "abc".length, toString: "abc".length = 3
```

The argument is evaluated eagerly (it is a plain value, not by-name).

## `hearth.typename.TypeName[A]` - readable type names at runtime

`trait TypeName[A] { prettyPrint; plainPrint; simplePrint; shortPrint }`, `toString` = `plainPrint`,
`TypeName[A]` = `implicitly`. Instances are derived automatically by a macro in the companion.

```scala
import hearth.typename.TypeName

val tn = TypeName[Option[String]]
tn.plainPrint   // scala.Option[java.lang.String]     (fully qualified, no ANSI)
tn.simplePrint  // Option[String]                     (short names, with type arguments)
tn.shortPrint   // Option                             (short name only)
tn.prettyPrint  // like plainPrint, with ANSI colors - do not put it in logs/files
TypeName[Map[String, example.User]].plainPrint  // scala.collection.immutable.Map[java.lang.String, example.User]
type Alias = Map[Int, String]
TypeName[Alias].plainPrint                      // scala.collection.immutable.Map[scala.Int, java.lang.String] (dealiased)
```

**In a library API, ask for it with a context bound** so the caller's concrete type is used, and callers can
override it with their own implicit:

```scala
def validate[A: TypeName](a: A): Either[String, A] = Left(s"Invalid ${TypeName[A].simplePrint}: $a")
validate(User("a", Nil))  // Left(Invalid User: User(a,List()))
```

**Injection.** When the derived instance prints a type argument, it uses an existing `TypeName` for it (a custom
instance or a context-bound parameter) - **only if the call site is compiled with Scala 2.13.17+ or 3.7.0+**:

```scala
object Custom {
  implicit val customStr: TypeName[String] = new TypeName[String] {
    def prettyPrint = "Str"; def plainPrint = "Str"; def simplePrint = "Str"; def shortPrint = "Str"
  }
  def listName[A: TypeName]: TypeName[List[A]] = TypeName[List[A]]

  TypeName[Option[String]].plainPrint  // 3.7.4 / 2.13.18: scala.Option[Str]    3.3.7 / 2.13.16: scala.Option[java.lang.String]
  listName[example.User].plainPrint    // 3.7.4 / 2.13.18: ...List[example.User] 3.3.7 / 2.13.16: ...List[A]
}
```

If the library must support older compilers, avoid deriving `TypeName[F[A]]` for an abstract `A`; take
`TypeName[F[A]]` itself as the context bound, or build the string from `TypeName[A]`:
`s"List[${TypeName[A].simplePrint}]"`.

Macro authors: inside a macro use `Type.plainPrint[A]` (compile-time string) or `Type.runtimePlainPrint` - `TypeName`
is for code that runs in the user's program.

## Versions (package `hearth`)

```scala
import hearth.{HearthVersion, JDKVersion, LanguageVersion, Platform, ScalaVersion}

JDKVersion.runtimeJDKVersion     // JDK 1.24        - JDKVersion(major = 1, minor = <feature>) - major is always 1
JDKVersion.compiletimeJDKVersion // JDK 1.24        - JDK that ran the compiler, baked in as a constant
ScalaVersion.byJVMRuntime        // Scala 3.3.7     - scala library on the runtime classpath
ScalaVersion.byCompileTime       // Scala 3.3.7     - compiler that compiled this call site
LanguageVersion.byHearth         // Scala 3         - Scala2_13 | Scala3, which Hearth artifact is linked
Platform.byHearth                // Jvm             - Jvm | Js | Native (isJvm / isJs / isNative)
HearthVersion.byHearthLibrary    // Some(Hearth 0.4.5 (Scala 3, Jvm)) - from the JAR name; None when not from a JAR
```

- `ScalaVersion(major, minor, patch)`: `isScala2_13`, `isScala3`, `toLanguageVersion` (throws
  `Unsupported Scala version: ...` for anything but 2.13.x / 3.x).
- `JDKVersion`, `ScalaVersion`, `LanguageVersion` have an implicit `Ordering`:
  `Ordering[ScalaVersion].gteq(ScalaVersion.byJVMRuntime, ScalaVersion(2, 13, 0))`.
- `LanguageVersion` / `Platform` are case objects: `Platform.Jvm`, `Platform.Js`, `Platform.Native`
  (not `Platform.JVM`), `LanguageVersion.Scala2_13`, `LanguageVersion.Scala3`.
- **JVM only at runtime:** `runtimeJDKVersion`, `ScalaVersion.byJVMRuntime` / `byScalaLibrary` / `resolveBy*Library`
  and `HearthVersion.byHearthLibrary` use reflection/class-loader APIs. `compiletimeJDKVersion`, `byCompileTime`,
  `byHearth` are constants and work on Scala.js / Native.

## Fat JARs: what to keep

Libraries built with Hearth bring it in the normal `Compile` scope, so it lands in fat JARs. Keep `hearth.source`,
`hearth.typename` and the classes directly in package `hearth`; most of the rest only runs inside the compiler. Details,
the full table and an sbt-assembly snippet: [fat-jar.md](fat-jar.md).

## Inspecting any macro: `hearth.debug.Debug`

Compile-time only, works for macros from **any** library (not just Hearth-based ones), on Scala 2.13 and 3:

```scala
import hearth.debug.Debug
Debug.withFinalCodeInIDE { someLib.derive[Foo] }  // final expanded code as a compiler info / IDE hint
Debug.withGivenCodeInIDE[Encoder[Foo]]             // what implicit search resolves to
```

It expands to the wrapped expression, so nothing stays in the runtime code; remove it before committing. More (AST
and type variants, `DebugOps`, logging): the `hearth-debugging` skill.

## Gotchas

- **Helper reports its own location instead of the caller's** (every message shows the helper's file, line and
  method name) - the value was materialized inside the helper (`implicitly[Line]` in its body). Declare it as an implicit parameter of every
  method between the caller and the place you read it.
- **`MethodName` is `<init>`** - the call is in a class/object body, a constructor, or a top-level `val` (Scala 3).
  Not an error; call it from inside a method, or pass `MethodName.wrap("...")` explicitly.
- **`MethodName` is an unexpected name** - it is the innermost `def`, including local `def`s; lambdas are skipped.
- **`No file found for position rs$line$3:<16..16>`** (also `No method found for position ...` when there is no
  enclosing method symbol) - the compiler has no source file, typically the REPL. Use `File`/`FileName`/`Location`
  only in compiled sources.
- **Wrong `Line` / `FileName` in Scala CLI `.sc` scripts** - the script is compiled as a wrapper (`s.sc` reports
  `s.scala` and a shifted line, e.g. 11 for line 3). Use `.scala` files when the numbers matter.
- **Non-reproducible builds / leaked build paths** - `File` and `Location` embed the absolute path of the build
  machine (`/home/ci/work/...`) into the bytecode. Use `FileName` or `Location.fileName` (or strip a prefix) in code
  that ships.
- **Production use** - Hearth's own docs call `hearth.source` a reference implementation and suggest
  [sourcecode](https://github.com/com-lihaoyi/sourcecode) for production; `hearth.source` is fine when Hearth is
  already on the classpath.
- **`TypeName` prints `List[A]` / ignores a custom instance** - the call site is compiled with Scala < 2.13.17 or
  < 3.7.0, where injection is disabled (the macro cannot summon without finding itself). Upgrade the compiler of the
  module that calls `TypeName`, or take the full `TypeName[F[A]]` as the context bound.
- **`<name> is a forward reference extending over the definition of <val>`** (2.13.17+ / 3.7+) - a local
  `implicit val x: TypeName[...]` defined later in the same block is found by injection. Define custom instances in
  an object/companion or before their first use.
- **Garbled names in logs** - `prettyPrint` contains ANSI escape codes; use `plainPrint` / `simplePrint`.
- **Scala.js / Native link error** `Referring to non-existent method java.lang.Class.getProtectionDomain()` /
  `non-existent class java.lang.reflect.Method` ... `There were linking errors` - a JVM-only version lookup
  (`runtimeJDKVersion`, `byJVMRuntime`, `byHearthLibrary`) is reachable. Use `Platform.byHearth` /
  `LanguageVersion.byHearth` / the `compiletime*` variants, or keep the call in JVM-only sources.
- **`JDKVersion.runtimeJDKVersion.major == 1` on JDK 21** - by design the feature version is in `minor`
  (`JDK 1.21`); compare `minor` or the whole value via `Ordering`.
- **`NoClassDefFoundError: hearth/...` from a shrunk fat JAR** - a runtime package was excluded; see
  [fat-jar.md](fat-jar.md).

## Reference

- Docs: [Source Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/source-utilities/),
  [Type Name Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/typename-utilities/),
  [Versions](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#versions),
  [Debug Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/debug-utilities/).
- Sources: [sources.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/source/sources.scala),
  [SourceMacros.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/source/SourceMacros.scala),
  [TypeName.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typename/TypeName.scala),
  [TypeNameMacros.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typename/TypeNameMacros.scala),
  [versions.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/versions.scala).
- Related skills: `hearth-debugging` (Debug, logging), `hearth-testing` (hearth-munit, `Data`).
