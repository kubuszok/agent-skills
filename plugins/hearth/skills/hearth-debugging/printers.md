# Hearth better printers (Hearth 0.4.5)

Readable renderings of trees and types: with line breaks, indentation and optional ANSI colours. Two ways to get them:
through `MacroCommons` (nothing to add), or standalone from the `hearth-better-printers` artifact in a macro that does
not use the rest of Hearth. Docs: [Better Printers](https://scala-hearth.readthedocs.io/en/0.4.5/better-printers/).

## Through `MacroCommons`

| Call (companion form also exists: `Expr.plainPrint(expr)`, `Type.plainPrint[A]`, ...) | Output |
|---|---|
| `expr.plainPrint` | source-like code, no colours - for tests, comparisons, keys |
| `expr.prettyPrint` | source-like code with ANSI colours - for compiler messages and logs only |
| `expr.plainAST` / `expr.prettyAST` | indented raw tree structure (no colours / ANSI) |
| `Type[A].plainPrint` / `Type[A].prettyPrint` | fully qualified type with type arguments, dealiased |
| `Type[A].shortName` | name only: no package, no type arguments (`Option`) |
| `Type[A].fqcn` | `plainPrint` up to the first `[` (`scala.Option`) - for messages, not type identity |
| `Type[A].runtimePlainPrint(f)` / `runtimePrettyPrint(f)` / `runtimeShortPrint(f)` | an `Expr[String]` built at runtime, see below |

`UntypedType` and `??` have the same `plainPrint`/`prettyPrint`/`shortName`; `Method` has `plainPrint`/`prettyPrint` of
its signature.

Verified on both Scala 2.13.16 and 3.3.9 for `Api.describe(Map("a" -> List(1)).get("a"))`:

```
plainPrint=scala.Predef.Map.apply[java.lang.String, scala.collection.immutable.List[scala.Int]](scala.Predef.ArrowAssoc[java.lang.String]("a").->[scala.collection.immutable.List[scala.Int]](scala.List.apply[scala.Int](1))).get("a")
Type.plainPrint=scala.Option[scala.collection.immutable.List[scala.Int]]
shortName=Option
fqcn=scala.Option
```

The code and type strings were identical on both versions here, but that is not guaranteed in general (rendering of
lambdas, synthetic names and blocks differs). The AST dumps always differ (`plainAST` was 145 lines on Scala 2 and
91 on Scala 3 for this expression): never compare `*AST` output across Scala versions, and keep cross-version test
expectations on `plainPrint`.

What runs underneath:

| | Scala 2 | Scala 3 |
|---|---|---|
| `expr.plainPrint` / `prettyPrint` | `showCodePretty(tree, SyntaxHighlight.plain / ANSI)` | the compiler's `Printer.TreeCode` / `Printer.TreeAnsiCode` |
| `expr.plainAST` / `prettyAST` | `showRawPretty(tree, plain / ANSI)` | `FormattedTreeStructure` / `FormattedTreeStructureAnsi` |
| `Type[A].plainPrint` / `prettyPrint` | `showCodePretty(tpe.dealias, plain / ANSI)` | `Printer.TypeReprCode` / `TypeReprAnsiCode` plus Hearth's own fixes (full names, all aliases removed) |

`expr.plainPrint`/`prettyPrint` strip Hearth's fresh-name suffixes `$macro$N` (`myName$macro$1` -> `myName`). Other
compiler suffixes (`x$1`, `evidence$1`, `rassoc$1`) are kept: they keep names unique when the printed code is reparsed.
The `*AST` methods and type printers do not strip anything.

## Standalone `hearth-better-printers`

For macros that do not use `MacroCommons`. JVM, Scala.js and Scala Native artifacts exist (the code only runs in the
compiler anyway):

```scala
libraryDependencies += "com.kubuszok" %% "hearth-better-printers" % "0.4.5"
//> using dep com.kubuszok::hearth-better-printers::0.4.5
```

### Scala 2: `ShowCodePrettyScala2`

Mix the trait into the macro bundle; it needs the context as `val c: blackbox.Context`:

```scala
import scala.language.experimental.macros
import scala.reflect.macros.blackbox
import hearth.treeprinter.{ShowCodePrettyScala2, SyntaxHighlight}

class Printers(val c: blackbox.Context) extends ShowCodePrettyScala2 {
  import c.universe._
  def codeImpl[A](expr: c.Expr[A]): c.Expr[String] =
    c.Expr[String](q"${showCodePretty(expr.tree, SyntaxHighlight.plain)}")
  def astImpl[A](expr: c.Expr[A]): c.Expr[String] =
    c.Expr[String](q"${showRawPretty(expr.tree, SyntaxHighlight.ANSI)}")
}
object Printers {
  def code[A](expr: A): String = macro Printers.codeImpl[A]
  def ast[A](expr: A): String = macro Printers.astImpl[A]
}
```

Signatures (both accept a `Tree` or a `Type`):

```scala
def showCodePretty(any: Any, highlight: SyntaxHighlight, printTypes: BooleanFlag = None, printIds: BooleanFlag = None,
                   printOwners: BooleanFlag = None, printPositions: BooleanFlag = None, printRootPkg: Boolean = false): String
def showRawPretty(any: Any, highlight: SyntaxHighlight, /* same flags */): String
```

`SyntaxHighlight.ANSI` colours, `SyntaxHighlight.plain` does not (`hearth.treeprinter.SyntaxHighlight`; you can
implement the trait for other colour codes). `BooleanFlag` is `c.universe.BooleanFlag`: pass `true`/`false`.

Compared with the built-in `showCode`, for `List(1, 2).map(_ + 1)`:

```
showCode:       scala.`package`.List.apply[Int](1, 2).map[Int](((x$2: Int) => x$2.+(1)))
showCodePretty: scala.List.apply[scala.Int](1, 2).map[scala.Int](((x$1: scala.Int) => x$1.+(1)))
```

and blocks get line breaks and indentation:

```
{
  val a = 1;
  if (a.>(0))
    "pos"
  else 
    "neg"
}
```

`showRawPretty` prints one node per line, indented, with symbols as `??? /* Symbol of def map (flags: ...) */` comments.

### Scala 3: `ShowCodePrettyScala3`

Provides only tree-**structure** printers, as `Printer[Tree]` instances; for code use the compiler's own
`Printer.TreeCode` / `Printer.TreeAnsiCode`, which already format and colour. It needs the `Quotes` as `val quotes`:

```scala
import scala.quoted.*
import hearth.treeprinter.ShowCodePrettyScala3

class Printers(using val quotes: Quotes) extends ShowCodePrettyScala3 {
  import quotes.reflect.*
  def ast[A](expr: Expr[A]): Expr[String]  = Expr(expr.asTerm.show(using FormattedTreeStructure))     // or FormattedTreeStructureAnsi
  def code[A](expr: Expr[A]): Expr[String] = Expr(expr.asTerm.show(using Printer.TreeCode))           // or Printer.TreeAnsiCode
}
object Printers {
  inline def ast[A](inline expr: A): String = ${ astImpl('expr) }
  def astImpl[A: Type](expr: Expr[A])(using Quotes): Expr[String] = new Printers().ast(expr)
}
```

Built-in `Printer.TreeStructure` prints everything on one line; `FormattedTreeStructure` prints one node per line.
Node names are taken from the first `quotes.reflect` extractor that matches, so they can differ from
`Printer.TreeStructure`: for `List(1, 2).map(_ + 1)` it printed `TypeSelect` where `TreeStructure` prints `Select`,
`TypedOrTest` for `Typed`, and `Lambda(List(ValDef(...)), body)` for `Block(List(DefDef("$anonfun", ...)), Closure(...))`.

Both examples above were compiled and run (Scala 2.13.16, Scala 3.3.9) against the published 0.4.5 artifact.

## Scala 2 vs Scala 3 output

Outputs differ on purpose: each follows its compiler's tree model (Scala 3 has `Inlined`, `Inferred`, `Lambda`; Scala
2 shows symbols and `TypeTree(TypeRef(...))`). Do not assert on AST dumps in cross-compiled tests, and do not try to
make them match. For stable assertions use `plainPrint` (and check that it matches on both versions).

## Truncation

Strings built by the better printers stop near 64 KB (the JVM limit for a string constant is 65 535 bytes) and end
with:

```
... (StringBuilder approaches its maximum length limit, output truncated - use Printer.TreeStructure or try printing smaller tree instead)
```

This affects Scala 2 `showCodePretty`/`showRawPretty` (so all Scala 2 `MacroCommons` printers) and Scala 3
`FormattedTreeStructure*` (`plainAST`/`prettyAST`). Print a smaller subtree (one method body, one field) instead of a
whole generated instance, or log it with `Debug.withFinalCodeInIDE` on a small example.

## Unsupported trees: `hearth.betterPrintersShouldFailOnUnsupportedTree`

When the printer meets a tree or type it does not know, it throws `UnsupportedOperationException` with
`Unsupported tree for showCodePretty:` (or `Unsupported type for showCodePretty:`), the tree printed by the built-in
printer, its raw structure and a request to report an issue at https://github.com/kubuszok/hearth/issues. A
`MacroCommons` program running in `MIO` gets it as a failure (it is `NonFatal`); outside `MIO` the exception escapes the
macro and the compiler reports an exception during macro expansion.

To unblock yourself until it is fixed, pass

```
-Xmacro-settings:hearth.betterPrintersShouldFailOnUnsupportedTree=false
```

(default `true`) to the module where the macro **expands**. The printers then fall back to the built-in rendering for
that node (Scala 2 `<type ?>` or the plain `TreePrinter` output; Scala 3 `Printer.TreeStructure` or `toString`). The
setting is read once and cached for the lifetime of the loaded printer classes, so restart a long-running build server
(sbt, Bloop, Metals) after changing it. It is not listed in the user docs.

## Runtime-aware type printing

`Type[A].runtimePlainPrint(f)` (and `runtimePrettyPrint`, `runtimeShortPrint`) build an `Expr[String]` that prints `A`
at runtime. `f: ?? => Option[Expr[String]]` is called for `A` and, recursively, for its type arguments; where it returns
`Some(expr)` that runtime string is spliced in, everything else is the compile-time `plainPrint` / `prettyPrint` /
`shortName` text. Typical use: a type argument that is abstract in the macro but has a runtime name (a summoned
`TypeName[T]`, `ClassTag[T]`).

```scala
def runtimeName[A: Type]: Expr[String] =
  Type[A].runtimePlainPrint { tpe =>
    if (tpe.plainPrint == "scala.Int") Some(Expr("<int>")) else None
  }
// runtimeName[Either[String, List[Int]]] evaluates to "scala.util.Either[java.lang.String, scala.collection.immutable.List[<int>]]"
```

(verified on Scala 2.13.16 and 3.3.9). Applied types are decomposed only when some argument (at any depth) is
overridden; otherwise the whole type is one literal. Hearth's `TypeName.derived` is built this way: see
[TypeNameMacros.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typename/TypeNameMacros.scala)
and [Type Name utilities](https://scala-hearth.readthedocs.io/en/0.4.5/typename-utilities/). Standalone, the same
logic is `runtimeAwareTypePrint(tpe, overrideFn, printType)` in the `RuntimeAwareTypePrinterScala2` /
`RuntimeAwareTypePrinterScala3` traits.

## Gotchas

- **Assertion fails only because of colours** -> compared `prettyPrint`/`prettyAST` output -> compare `plainPrint`;
  never regex-strip ANSI codes from `prettyPrint` to get a key.
- **Test expectation passes on one Scala version only** -> asserting on `plainAST`/`prettyAST` or on Scala-specific
  rendering -> assert on `plainPrint`, or keep per-version expectations.
- **`x$1`/`evidence$1` in expected strings** -> only `$macro$N` is stripped, other synthetic names stay; avoid
  asserting on them.
- **Error message unreadable / cut off** -> printed a whole generated tree -> print the relevant subtree; output is
  truncated near 64 KB anyway.
- **`Unsupported tree for showCodePretty`** -> report it; meanwhile
  `-Xmacro-settings:hearth.betterPrintersShouldFailOnUnsupportedTree=false`.
- **Scala 3 standalone: no `showCodePretty`** -> it is Scala 2 only; on Scala 3 use `Printer.TreeAnsiCode` for code and
  `FormattedTreeStructure(Ansi)` for structure.
- **`ShowCodePrettyScala2` / `ShowCodePrettyScala3` do not compile when mixed in** -> the abstract member must be named
  exactly `c` (Scala 2, `val c: blackbox.Context`) / `quotes` (Scala 3, `val quotes: Quotes`).
- **Expensive messages** -> `prettyPrint` of a big type/tree is not free; build such strings by-name (`Log.info(...)`)
  or only on failure.
