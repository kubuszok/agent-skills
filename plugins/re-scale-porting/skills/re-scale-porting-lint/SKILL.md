---
name: re-scale-porting-lint
description: >-
  Inspect and tighten Scala 3 compiler lint settings in a re-scale project - which -W flags and -Wconf suppressions
  build.sbt enables (`status`), the available Scala 3 lint flags (`flags`), unused-symbol warnings E198 from a
  compile (`unused`), and null-related shortcut hits with skip-policy for interop (`null`); plus removing a -Wconf
  suppression once a warning category is fixed. Use when asked about linter flags, unused imports/privates/locals,
  -Werror failures, or promoting warnings to errors.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Lint flags

Written for re-scale **0.1.5** (check `re-scale --version`). Input: one of
`status`, `flags`, `unused`, `null` (`$ARGUMENTS` in a slash command).

## `status`

1. Read `build.sbt` (and any `project/*.scala` settings) and find
   `scalacOptions`.
2. List the enabled flags with their purpose and every `-Wconf` rule.
3. Say which categories are errors (under `-Werror`), which are silenced or
   downgraded to info.

## `flags`

1. Read the current `scalacOptions`.
2. Table the Scala 3 lint flags - `-Wunused:imports,privates,locals,explicits,implicits,params,patvars,nowarn`
   (or `all`), `-Wvalue-discard`, `-Wnonunit-statement`, `-Wimplausible-patterns`,
   `-Wrecurse-with-default`, `-Wenum-comment-discard`, `-Wsafe-init`,
   `-Wshadow:...`, `-deprecation`, `-feature` - marked enabled, disabled or
   suppressed. Check the exact set against `scalac -W` for the project's Scala
   version; it changes between releases.
3. For disabled flags give the reason if the build or docs record one.

## `unused`

1. Compile and keep the output:
   `re-scale build compile` (write it to a file, then search it).
2. Find the unused-symbol warnings (message id `E198`).
3. Count by kind (imports, privates, locals, pattern variables) and list by
   file.

## `null`

1. `re-scale enforce shortcuts` and keep the `null-cast`, `get-or-else-null`,
   `nullable-null-fallback` and `this-null-arg` hits.
2. Fix them with `re-scale-porting-guide-nullable`. For a real Java interop boundary,
   suggest isolating it; a skip-policy entry
   (`re-scale enforce skip-policy add <path> shortcuts --reason "Java interop: ..."`)
   hides every shortcut hit in that file.

## Promoting warnings to errors

When a category is fully fixed (for example no unused imports remain), remove
its `-Wconf` suppression from `build.sbt` so `-Werror` keeps it at zero.

## Rules

Use `re-scale build` or `sbt --client`; bare `sbt` is denied by the hook.
