---
name: re-scale-porting-gap-fix
description: >-
  Fix every re-scale enforcement failure in one ported Scala file - triage each `re-scale enforce shortcuts` hit
  (todo, fixme, ???, null-cast, flag-break-var, for-now-comment, stub-comment ...), port the missing methods and
  short bodies reported by `enforce compare --strict`, re-run the gates, compile, test, and stamp a covenant. Use
  when a file has shortcut hits, missing methods, short bodies or dropped constructor parameters, or fails
  `enforce verify`.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Gap-fix one file

Written for re-scale **0.1.5** (check `re-scale --version`). Input: the path of
the ported Scala file (`$ARGUMENTS` in a slash command).

## Procedure

1. `re-scale enforce shortcuts --file <path>` - note every hit.
2. `re-scale enforce compare --port <path> --source <original> --strict` -
   note missing methods, short bodies, dropped constructor parameters (Java
   and Dart sources; compare Ruby/JS by hand).
3. Read both files completely.
4. Fix each hit:

   | Hit | Action |
   |---|---|
   | `todo`, `fixme`, `hack`, `xxx` | port the missing logic; remove the marker when done |
   | `scala-unimpl`, `not-implemented`, `unsupported-op`, `throw-not-yet` | implement from the original (keep an `UnsupportedOperationException` the original itself throws) |
   | `stub-comment`, `placeholder-comment`, `not-yet-comment`, `deferred-comment`, `tbd-comment`, `pending-comment` | port the deferred logic, then drop the comment |
   | `for-now-comment`, `simplified-comment`, `minimal-comment`, `best-effort-comment`, `approximation-comment` | port the full logic; reword only if the comment is false and the code is complete |
   | `null-cast`, `get-or-else-null`, `nullable-null-fallback`, `this-null-arg` | nullable patterns (`re-scale-porting-guide-nullable`) |
   | `flag-break-var`, `return-comment`, `break-comment`, `scalastyle-ignore-return` | boundaries (`re-scale-porting-guide-control-flow`) |
   | `catch-throwable` | narrow the catch to what the original catches |
   | missing method / short body | port from the original |
   | dropped constructor parameter | add the parameter back |

   A hit inside an upstream comment copied verbatim is a false positive: keep
   the comment and note it in the audit.

5. Re-run the gates:
   ```
   re-scale enforce shortcuts --file <path>                                # no hits
   re-scale enforce compare --port <path> --source <original> --strict     # exit 0
   ```
6. Compile: `re-scale build compile --module <M> --errors-only` (with
   `--jvm --js --native` for cross-built modules).
7. Test: `re-scale test unit --module <M>` (same platform flags); confirm the
   relevant suites ran.
8. Stamp: `re-scale enforce covenant-apply --file <path> --source <original>`
   (skip if you are the implementer in an implement/audit loop - the auditor
   stamps).
9. Commit message shape: `<module>: gap-fix <file> - N shortcuts resolved, M methods ported`.

## Escape hatch

For a hit that is genuinely correct (a real `null` at a Java interop call),
`re-scale enforce skip-policy add <path> shortcuts --reason "..."` hides it -
and every other shortcut hit in that file. `enforce verify` and
`covenant-apply` ignore the skip-policy, so such a file still cannot be
covenanted without `--force`. Prefer isolating the interop in a small file.

## Rules

- Never read or edit `.rescale/data/` directly.
- Use the harness's file tools, not shell utilities.
