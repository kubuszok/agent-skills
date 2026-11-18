---
name: re-scale-guide-code-style
description: >-
  Code style for Scala 3 files ported from another language in a re-scale project - the license header with
  upstream attribution and a Migration notes block (which `re-scale fileinfo` parses), braces with -no-indent, split
  package clauses, -Werror lint flags, final case classes, Scala 3 enums, getters/setters, preserved comments, and
  scalafmt via `re-scale build fmt`. Use when creating or reviewing a ported .scala file, writing its header, or
  fixing style and warning errors such as unused imports (E198) under -Werror.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Code style for ported files

Written for re-scale **0.1.5** (check `re-scale --version`). These are the
conventions shared by re-scale projects. The project's own contributing docs
win on every detail (header wording, copyright line, package names, flags).

## License header

The first thing in the file, before `package`. It keeps the upstream
attribution and records the port:

```scala
/*
 * Ported from <upstream project> - <upstream URL>
 * Original source: <path of the upstream file, relative to its source root>
 * Original authors: <from @author tags, or "See AUTHORS file">
 * Original license: <upstream license>
 *
 * <project copyright line, e.g. "Copyright (c) 2026 <project> contributors">
 * SPDX-License-Identifier: <project license>
 *
 * Migration notes:
 *   Renames: <package/class/method renames>
 *   Convention: <convention changes, e.g. "Nullable instead of null">
 *   Idiom: <Scala idiom replacements, e.g. "boundary/break for early returns">
 *   Audited: <YYYY-MM-DD>
 */
```

- A file merged from several upstream files lists every source, one per line.
- A file with no upstream counterpart gets only the project's own lines.
- Take authors from the original's `@author` tags; do not invent them.
- `re-scale fileinfo` reads `Key: value` lines from this leading comment (first
  80 lines), lower-casing keys and skipping `Copyright` and
  `SPDX-License-Identifier`. `Renames`, `Convention`, `Idiom`, `Audited` and
  any tracking keys you add (`original-src`, `authors`, `upstream-commit`,
  `status`) become queryable - see `re-scale-file-metadata`.

## Syntax

- **Braces everywhere** (`-no-indent`): every `class`, `trait`, `object`,
  `enum`, `def` and multi-line body uses `{ }`.
- **Split package clauses**, never a dotted one. Each clause also imports the
  parent package's members:
  ```scala
  package mylib
  package text
  package parser
  ```
- `final case class` always. Scala 3 `enum`, never `scala.Enumeration`; use
  `enum X extends java.lang.Enum[X]` where Java code or `ordinal`/`valueOf`
  parity matters.
- Uninitialised `var` is `= scala.compiletime.uninitialized`, never `= _`
  (for a nullable field use the project's empty value instead).
- Java getters/setters with no logic become a public `var x`. With logic:
  `def x: T` and `def x_=(v: T): Unit`. Keep the original names when the
  project promises API compatibility with the upstream library - its docs say
  which.
- No `return` (see `re-scale-guide-control-flow`), no raw `null` (see
  `re-scale-guide-nullable`).
- Prefer `given`/`using` over global singletons, `Ordering` over
  `Comparator`, `AutoCloseable` over custom dispose interfaces - when the
  project's docs say so.

## Comments

**Never remove or rewrite comments from the original source.** Translate code
inside them only if the project asks for it. Add your own notes to the header's
Migration notes, not in place of upstream comments.

Upstream comments can contain words the shortcut scanner treats as markers
(`TODO`, `for now`, `simplified`, `pending`, `deferred`, `shim`, `Phase 2`,
...). Keep the comment; record the false positive in the audit notes.

## Compiler flags

Typical settings (check `build.sbt`):

```
-deprecation -feature -no-indent -Werror
-Wimplausible-patterns -Wrecurse-with-default -Wenum-comment-discard
-Wunused:imports,privates,locals,patvars,nowarn
```

Warnings are errors. Fix the cause; suppress only with a targeted
`@nowarn("msg=...")` or `@nowarn("id=E198")` (unused symbol) and a comment
saying why. During a cleanup campaign, cite an open issue id on the same line.
`re-scale-lint` covers flag status and unused-symbol reports.

## Formatting

`re-scale build fmt` runs `sbt --client scalafmtAll` with the project's
`.scalafmt.conf`; `re-scale build compile-fmt` formats and then compiles.

## Bugs

When porting or a test reveals a bug, fix the code - never bend the test to
the bug. If the bug is in the upstream library too, keep upstream behaviour
unless the project decides otherwise, and record the decision in the header.
