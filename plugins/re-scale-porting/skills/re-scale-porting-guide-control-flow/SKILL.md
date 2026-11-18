---
name: re-scale-porting-guide-control-flow
description: >-
  Translating return, break, continue, labelled break/continue and switch from Java, Dart or Ruby into Scala 3
  scala.util.boundary / boundary.break when porting a library under re-scale - where the boundary goes (around the
  method, the loop, or the loop body), nested labels, breaks inside try/catch, and switch fall-through. Also covers
  the re-scale shortcut hits `flag-break-var`, `return-comment`, `break-comment` and `scalastyle-ignore-return`.
  Use when a ported method has an early return, a loop with break/continue, a labelled jump, a switch statement, or
  a `var done`/`var stop` flag.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Control-flow guide

Written for re-scale **0.2.0** (check `re-scale --version`). re-scale projects
ban `return`, and Scala has no `break`/`continue`, so every early exit becomes
`scala.util.boundary` + `boundary.break`.

```scala
import scala.util.boundary
import scala.util.boundary.break
```

## Where the boundary goes

| Java | The boundary wraps | Jump |
|---|---|---|
| `return v;` | the method body | `break(v)` |
| `break;` | the **loop** | `break()` |
| `continue;` | the **loop body** | `break()` |
| `break outer;` | the labelled statement (outer loop) | `break()(using outer)` |
| `continue outer;` | the outer loop's **body** | `break()(using outerBody)` |

```scala
// return
def find(xs: Array[Int]): Int = boundary {
  for (x <- xs) {
    if (x > 10) break(x)
  }
  -1
}

// break: boundary around the loop
boundary {
  while (cond) {
    if (stop) break()
    step()
  }
}

// continue: boundary around the body
while (cond) {
  boundary {
    if (skip) break()
    step()
  }
}
```

## Nested boundaries

`break` without `using` jumps to the **innermost** boundary. As soon as two
boundaries are nested - including one you add later for a `continue` - name
them, or the inner one silently steals the outer jump:

```scala
boundary[Int] { outer ?=>
  for (xs <- xss) {
    boundary[Unit] { inner ?=>
      for (x <- xs) {
        if (done(x)) break(x)(using outer)
        if (skip(x)) break(())(using inner)
      }
    }
  }
  -1
}
```

A method body with both `return` and `continue` needs this every time.

## Gotchas

- **A `break` crossing a `try` with a broad `catch` is swallowed.**
  `boundary.Break` extends `RuntimeException`, so `case e: Exception`,
  `case _: Throwable` and `case NonFatal(e)` catch it and the loop keeps
  running. Java's jumps cannot be caught. Put a re-throw arm first:
  ```scala
  try { ... break(v) ... }
  catch {
    case b: boundary.Break[?] => throw b
    case e: Exception          => handle(e)
  }
  ```
- **`switch` without `default`.** Java falls out of the switch when nothing
  matches; a Scala `match` without `case _ => ()` throws `MatchError`. Always
  add the fall-out arm for a switch *statement*. A Java switch *expression*
  (`->`, `yield`) is exhaustive and needs none.
- **`switch` on a null `String` or enum** throws `NullPointerException` in
  Java. A Scala `match` lets `null` reach the fall-out arm and silently does
  nothing; add `case null => throw new NullPointerException()` when the
  selector can be null.
- **Fall-through.** A case without `break` runs into the next case. Merge the
  labels (`case A | B =>`) when the bodies are identical; otherwise repeat the
  following case's code in the arm. A `break` in the middle of a case leaves
  the case - wrap that arm in its own boundary.
- **Labelled `break` on a non-loop.** Java allows `label: { ... break label; ... }`
  on any block or `if`. Put a named boundary around exactly that statement.
- **Flag variables.** `re-scale enforce shortcuts` reports `flag-break-var` for
  `var done|continue|finished|stop|canBreak|shouldBreak|shouldContinue`.
  Replace a flag you introduced with a boundary. If the original itself has
  that flag as real state, keeping it is faithful: note the false positive in
  the audit notes (a skip-policy entry would hide every other hit in the file).
- **Commented-out jumps.** `// return ...` and `// break ...` lines are
  reported as `return-comment` / `break-comment`; a `return` hidden behind
  `// scalastyle:ignore` is `scalastyle-ignore-return`. Translate the jump.
- **Lambdas.** A `break` inside a closure that runs after the boundary has
  exited (stored callback, lazy collection, another thread) fails at runtime.
  Use boundaries only around code that runs synchronously.
- **Performance.** A `break` that stays in the same method compiles to a jump;
  one that crosses a closure (for example `foreach`) throws an exception with
  no stack trace. In hot loops prefer `while` with an index.
