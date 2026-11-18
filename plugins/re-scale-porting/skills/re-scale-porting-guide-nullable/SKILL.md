---
name: re-scale-porting-guide-nullable
description: >-
  Replacing Java/Dart/Ruby null with the project's opaque Nullable[A] type when porting a library to Scala 3 under
  re-scale - initialising fields, the getOrElse / fold / foreach / map / flatMap / isDefined / isEmpty patterns,
  null-returning methods, Dart `?.`, `??`, `!`, and the interop boundary where `orNull` is allowed. Also explains
  the re-scale shortcut hits `null-cast`, `get-or-else-null`, `nullable-null-fallback` and `this-null-arg`. Use when
  a ported file has `null`, `== null`, `@Nullable`, `T?`, `nil`, or when `re-scale enforce shortcuts` reports a null
  pattern.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Nullable guide

Written for re-scale **0.1.5** (check `re-scale --version`). re-scale itself
ships no `Nullable` type: each project picks one, usually an allocation-free
opaque type with `Option`-like extension methods (for example
`lowlevel.Nullable` from [lls](https://github.com/kubuszok/lls), or a plain
`opaque type Nullable[+A] = A | Null`). The
project's `CLAUDE.md` or contributing docs name the type, its import and its
exact API - read them first; method names below are the common ones and may
differ.

## Rules

- No raw `null` in ported code. A value that may be absent has type
  `Nullable[A]`; everything else is non-null.
- Initialise an absent field with `Nullable.empty`, never with `null`, `_`
  or `scala.compiletime.uninitialized`.
- A Java method that returns `null` becomes a method returning
  `Nullable[A]` that returns the empty value. Do not turn "returns null" into
  "throws".
- `orNull` (or the type's equivalent) only where a Java/JS API needs a real
  `null`; put `@nowarn` on it only if required and leave a comment naming the
  API.
- Never `null.asInstanceOf[T]`, `.getOrElse(null)` or `this(null, ...)`.

## Patterns

```scala
// Java: Foo x = null;                    // Java: Foo x = make();
var x: Nullable[Foo] = Nullable.empty      var x: Nullable[Foo] = Nullable(make())
```

| Java shape | Scala |
|---|---|
| `x == null ? dflt : x` | `x.getOrElse(dflt)` |
| `if (x == null) throw new E(); use(x)` | `x.fold(throw new E())(a => use(a))` |
| `x == null ? compute() : f(x)` | `x.fold(compute())(a => f(a))` |
| `if (x != null) use(x)` | `x.foreach(a => use(a))` |
| `x != null` / `x == null` | `x.isDefined` / `x.isEmpty` |
| `x == null ? null : x.y()` | `x.map(_.y())` |
| chained nullable calls | `x.flatMap(a => g(a))` |
| "I know it is not null" | `x.get` or `x.nn`, whichever the type has (throws when empty - only where Java would also throw) |

Return a found value from a loop:

```scala
def findFirst(items: Iterable[Item]): Nullable[Item] = boundary {
  for (item <- items) {
    if (matches(item)) break(Nullable(item))
  }
  Nullable.empty
}
```

Dart null safety:

| Dart | Scala |
|---|---|
| `T?` | `Nullable[T]` |
| `x!` | `x.get` / `x.nn` |
| `x?.m()` | `x.map(_.m())` |
| `x ?? d` | `x.getOrElse(d)` |
| `x?.m() ?? d` | `x.fold(d)(_.m())` |
| `x ??= v` | `if (x.isEmpty) x = Nullable(v)` |

Ruby `nil` maps to `Nullable` the same way.

## Gotchas

- **Shortcut hits.** `re-scale enforce shortcuts` reports `null-cast`
  (`null.asInstanceOf[`), `get-or-else-null` (`.getOrElse(null)`),
  `nullable-null-fallback` (`Nullable.empty.getOrElse(null)`) and
  `this-null-arg` (`this(null, ...)`). Rewrite with the patterns above. For a
  real interop boundary, a skip-policy entry hides **every** shortcut hit in
  that file - prefer moving the interop call into a small dedicated file and
  listing only that one (`re-scale enforce skip-policy add <file> shortcuts --reason "..."`).
- **`Nullable[Nullable[A]]`.** A plain `A | Null` cannot tell "empty" from
  "contains empty"; some implementations (lls) encode nesting, others do not.
  Check before relying on it, and keep nesting out of public signatures.
- **Primitive types.** `Nullable[Int]` boxes. Java `int` is never null; use
  `Nullable` only where Java used a reference type (`Integer`).
- **Equality.** `x == null` on a `Nullable` compiles; use `isEmpty` so the
  intent survives a change of representation.
