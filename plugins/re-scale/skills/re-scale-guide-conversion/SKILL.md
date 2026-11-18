---
name: re-scale-guide-conversion
description: >-
  Rules for converting Java, Dart or Ruby source files to Scala 3 by hand in a re-scale porting project - planning,
  the step-by-step Java procedure (statics to companions, interfaces to traits, generics, collections, exceptions,
  getters/setters), Dart and Ruby mapping tables, and the Java constructs that compile in Scala but behave
  differently (reference ==, post-increment, switch without default, static initialisers, int-to-float widening,
  List.remove overloads, inclusive range ends). Use when converting a .java, .dart or .rb file to .scala, or when a
  ported method compiles but behaves differently from the original.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Conversion guide

Written for re-scale **0.1.5** (check `re-scale --version`). Load this with
`re-scale-guide-nullable`, `re-scale-guide-control-flow` and
`re-scale-guide-code-style`. The project's own type-mapping document (package
renames, replacement collections, error types, context parameters) overrides
the generic tables here - find it in the project's `CLAUDE.md` or contributing
docs before starting.

Language tables:
- [java.md](java.md) - the step-by-step Java procedure
- [dart.md](dart.md) - Dart types, null safety, classes, async, enums
- [ruby.md](ruby.md) - Ruby types, blocks, regexes; port from behaviour, not lines

## Principles

1. **Port the logic, not the syntax** - but keep every method, branch, edge
   case and comment. "Idiomatic" never means "shorter by dropping cases".
2. **Java's behaviour is the contract.** When Scala's obvious translation means
   something else, write what Java meant (table below).
3. **Keep the upstream API** (names, parameter order, overloads) unless the
   project's docs record a different decision.
4. **Read the original from the local checkout** (usually a submodule such as
   `original-src/`), never from the web.

## Planning

1. Find the existing target file through the project's path mapping, and check
   `re-scale db migration get <source_path>` for its status.
2. List the original's members (`re-scale enforce compare` gives the method
   set for Java and Dart).
3. Decide where statics, nested types and helpers go (companion object, same
   file, split files) before writing code.
4. Compile often: `re-scale build compile --module <M> --jvm --errors-only`.
5. Commenting code out is only an intermediate step to get the rest compiling.
   It must be gone before you report the file done; the scanner flags the
   leftovers.

## Java constructs that compile but mean something else

| Java | Naive Scala | Problem | Write |
|---|---|---|---|
| `a == b` on references | `a == b` | Scala `==` calls `equals` (infinite recursion inside `equals`) | `a eq b` |
| `a.equals(b)` | `a.equals(b)` | fine, but `==` is null-safe | `a == b` |
| `x++` used as a value | `{ x += 1; x }` | Java yields the old value | `{ val p = x; x += 1; p }` |
| `arr[f()] += v` | `arr(f()) = arr(f()) + v` | `f()` runs twice | bind `f()` to a `val` first |
| `switch` without `default` | `match` without `case _` | `MatchError` where Java fell out | add `case _ => ()` |
| `static final int X = 1` | `val X: Int = 1` | Java inlines constants; reading a `val` initialises the object (init-order cycles) | `final val X = 1` (constant type) |
| `static { ... }` / static field init | `object` body | runs when the `object` is first touched, not when the class is first used | move registration to where it is needed, or touch the object from the class |
| `int` passed to a `float`/`double` slot | relies on implicit widening | deprecated conversion, an error under `-Werror` | `.toFloat` / `.toDouble` |
| `list.remove(Integer.valueOf(x))` | `buf.remove(x)` | Scala's `remove` is by index | `buf -= x` or `indexOf` + `remove` |
| inclusive end index | passed to an exclusive API | off by one | `end + 1` |
| method returning a new value vs mutating | renamed to the "same" Scala method | e.g. `BitSet.xor` returns a new set | check mutability, use `^=` etc. |
| `String.format("%.2f", x)` | `s"$x"` | format flags lost | `f"$x%.2f"` or `String.format` |
| overloads `f(int)` + `f(Object)`, or with varargs | same overloads | Scala resolves overloads differently | check each call resolves to the same overload |
| array forwarded to a `T...` / `Any*` parameter | the array | with an `Object`/`Any` element type it compiles as ONE element | `arr*` |
| `synchronized` method | modifier dropped | runs unlocked | `= this.synchronized { ... }` |
| `try (R r = ...)` | plain `try` | resource never closed | `try ... finally r.close()` per resource, in reverse order, or `scala.util.Using` when no early exit crosses it |
| `catch (Exception e)` around a jump | `case e: Exception` | swallows `boundary.Break` | see `re-scale-guide-control-flow` |
| secondary constructor calling `super(args)` | not expressible | Scala secondary constructors cannot call super | promote to the primary constructor, or a factory in the companion |

## After converting

```
re-scale enforce shortcuts --file <scala>                          # no hits
re-scale enforce compare --port <scala> --source <original> --strict  # Java/Dart only
re-scale build compile --module <M> --jvm --errors-only            # add --js/--native if the module is cross-built
re-scale test unit --module <M> --jvm
```

Then follow `re-scale-guide-verification`, and update tracking as in
`re-scale-convert-file`.

## Gotchas

- **`compare` reports missing methods that were renamed.** It matches names.
  Record each deliberate rename under `Renames:` in the header so the auditor
  can match them.
- **Short body on a correct method.** `--strict` flags bodies under 70% of the
  source's token count; idiomatic Scala can be legitimately shorter. Re-read
  the original branch by branch before accepting it.
- **Upstream tests.** If the original has tests, port them too; they are the
  only proof the semantics above survived.
