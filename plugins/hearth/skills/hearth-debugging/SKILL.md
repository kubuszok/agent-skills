---
name: hearth-debugging
description: >-
  Debugging Hearth-based Scala 2.13 / Scala 3 macros - hearth.debug.Debug (withFinalCodeInIDE, withFinalASTInIDE,
  withInferredTypeInIDE, withGivenCodeInIDE, DebugOps), MIO Log rendering via runToExprOrFail (RenderFrom,
  DontRender), LogDerivation imports and -Xmacro-settings logging switches, Environment.isExpandedAt, reportInfo
  limits, expr.prettyPrint / prettyAST, hearth.mioBenchmarkScopes flame graphs (.speedscope.json), cross-quotes
  logging, compiler flags (-Xcheck-macros, -Ymacro-debug-lite, -Vimplicits, -explain), testing with hearth-munit
  MacroSuite compileErrors and Data fixtures. Use when a Hearth macro generates wrong code, fails with an unclear
  error, is slow to compile, or prints nothing.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Debugging Hearth macros

Tools for seeing what a macro sees and generates, for both the macro author and the macro's users.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala `//> using dep`); if it differs, prefer the docs for that version: https://scala-hearth.readthedocs.io/en/0.4.5/debug-utilities/ and https://scala-hearth.readthedocs.io/en/0.4.5/best-practices/ (replace `0.4.5`).

## First: make sure the macro actually re-expands

Incremental compilation does not re-expand macros whose call sites did not change. After changing macro code, **clean** the modules that expand it (and the macro module) before concluding "nothing changed" or "no debug output".

## See the generated code (no macro changes needed)

```scala
import hearth.debug.Debug
Debug.withFinalCodeInIDE { MyTC.derived[Foo] }     // final code after all expansions, as a compiler info/IDE hint
Debug.withFinalASTInIDE { MyTC.derived[Foo] }      // raw tree
Debug.withInferredTypeInIDE { expr }
Debug.withGivenCodeInIDE[MyTC[Foo]]                // what implicit search resolves to
Debug.withGivenASTInIDE[MyTC[Foo]]; Debug.withGivenTypeInIDE[MyTC[Foo]]
import hearth.debug.DebugOps.*                     // expr.withFinalCodeInIDE etc. (Scala 2: DebugOps._)
```

Output appears in compilation logs and as hover hints (Metals, IntelliJ, Scastie). These work for any macro, not only Hearth-based ones. Remove them before committing.

## Log the derivation (for you and your users)

Structure the macro as one `MIO` program with `Log.namedScope`/`Log.info` at every decision (rule attempted, matched, yielded with reason, cache hit). `runToExprOrFail` renders the tree once:

```scala
mio.runToExprOrFail(
  "MyTC.derived",
  infoRendering = if (shouldLog) RenderFrom(Log.Level.Info) else DontRender, // RenderOnly(level) also exists
  errorRendering = if (shouldLog) RenderFrom(Log.Level.Info) else RenderFrom(Log.Level.Error)
) { (logs, errors) => s"...errors...\n$logs\nEnable logging: import mylib.debug.logDerivation" }
```

Offer two switches (see `hearth-type-class-derivation` for code): an importable marker implicit (`import mylib.debug.logDerivation`, defined outside the companion so it is never in implicit scope by default) and `-Xmacro-settings:mylib.logDerivation=true`, read via `Environment.typedSettings`. Mention both in every error message. Keep messages by-name (`Log.info(s"...")` is lazy) so disabled logging is free.

## Debug output from inside the macro

```scala
if (Environment.isExpandedAt("MySpec.scala:42")) {      // or "MySpec.scala:42:10"
  Environment.reportInfo(s"tree: ${expr.prettyAST}")      // or println - not forwarded by build servers
}
```

- Only the **first** `reportInfo` and the first `reportWarn` per position are shown; aggregate into one message. Scala 2 shows only the first `reportError` per position, Scala 3 all.
- Columns differ: `Foo.bar` expands at column of `bar` on Scala 2 and of `Foo` on Scala 3.
- Printers: `expr.prettyPrint`/`plainPrint` (code), `expr.prettyAST`/`plainAST` (tree), `Type[A].prettyPrint`/`plainPrint`. `pretty*` use ANSI colours (logs only); `plain*` for tests and keys.

## Compile-time performance: flame graphs

```
-Xmacro-settings:hearth.mioBenchmarkScopes=true
-Xmacro-settings:hearth.mioBenchmarkFlameGraphDir=/tmp/flames
```

Each expansion run through `runToExprOrFail` writes a `.speedscope.json` (open at https://www.speedscope.app) with one frame per `Log.namedScope`; rendered logs get durations. Typical findings: repeated `loadStandardExtensions`, re-derived types (missing caching), expensive `prettyPrint` in eagerly built messages. A timeout (`Macro 'X' timed out after ...ms`) also writes the graph and logs collected so far.

## Cross Quotes rewrite

`-P:hearth.cross-quotes:logging=true` (Scala 3) / `-Xmacro-settings:hearth.cross-quotes.logging=true` (Scala 2), or a comma-separated list of file names instead of `true`, prints the native code each `Expr.quote` became when compiling the macro library. Scala 2 errors at `<macro>:line:col` come from that generated code - see `hearth-cross-quotes`.

## Compiler flags worth knowing

- Scala 3: `-Xcheck-macros` (catches Quotes-scope and tree-type bugs early), `-explain`, `-explain-types`.
- Scala 2: `-Ymacro-debug-lite` / `-Ymacro-debug-verbose` (all expansions - use on a tiny reproducer), `-Vimplicits`, `-Vimplicits-verbose-tree`.
- Both: `-Vprint:<phase>`, `-Xshow-phases`/`-Vphases`.
- "Binary search" a failing implicit chain: add stub `implicit val x: TC[Field] = ???` per field type, remove half until it compiles again.

## Testing macros

`"com.kubuszok" %% "hearth-munit" % "0.4.5" % Test`:

```scala
final class MyTCSpec extends hearth.MacroSuite {
  group("errors") {
    test("unsupported type lists every problem") {
      compileErrors("MyTC.derived[Unsupported]").check("No MyTC for", "field")   // or .checkNot(...), .arePresent()
    }
  }
}
```

`==>` for equality, `<==>` for `String`/`hearth.data.Data` with diffs. A fixture macro returning `Expr[hearth.data.Data]` checks many properties in one expansion. Test unsupported types (aggregated error text), user-instance-wins, recursive types, both Scala versions.

## Gotchas

- **No output at all** -> nothing re-expanded (clean), or info rendering is `DontRender`, or a previous `reportInfo` at the same position consumed the slot.
- **`println` output missing** -> build servers (sbt client, Bloop, Metals) do not forward it; use `reportInfo`/logs.
- **Logs only on failure** -> pass the same `RenderFrom(Log.Level.Info)` for `infoRendering` when the switch is on.
- **Users cannot debug** -> the error message must say how to enable logging and list reasons per rule/field, not only "cannot derive".
- **Timeout instead of an error** -> raise/configure the `runToExprOrFail` timeout; check the flame graph for loops.

## Reference

- Docs: [Debug Utilities](https://scala-hearth.readthedocs.io/en/0.4.5/debug-utilities/), [Best Practices - debugging and testing](https://scala-hearth.readthedocs.io/en/0.4.5/best-practices/), [Micro FP - logging and flame graphs](https://scala-hearth.readthedocs.io/en/0.4.5/micro-fp/#logging), [Better Printers](https://scala-hearth.readthedocs.io/en/0.4.5/better-printers/).
- Example switches: Kindlings 0.4.0 [fast-show-pretty `debug` package](https://github.com/kubuszok/kindlings/blob/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/debug/package.scala) and `shouldWeLogDerivation` in [FastShowPrettyMacrosImpl](https://github.com/kubuszok/kindlings/blob/0.4.0/fast-show-pretty/src/main/scala/hearth/kindlings/fastshowpretty/internal/compiletime/FastShowPrettyMacrosImpl.scala).
