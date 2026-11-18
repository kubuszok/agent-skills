---
name: re-scale-verify-file
description: >-
  Quick verification of one ported Scala file in a re-scale project - header and convention checks (no return, no
  raw null, final case classes, split packages, braces), `re-scale enforce shortcuts` and `enforce verify`, compile
  with `re-scale build compile`, run the module's tests, and report PASS or FAIL with specifics. Use right after
  converting or editing a ported file, or when asked whether a file is OK. For a full audit against the original
  use re-scale-audit-file.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Verify one file

Written for re-scale **0.1.5** (check `re-scale --version`). Input: the path of
the ported Scala file (`$ARGUMENTS` in a slash command).

## Procedure

1. Read the file.

2. Quick checks:
   - license header with upstream attribution?
   - no `return`?
   - no raw `null` (the project's nullable type instead)?
   - every case class `final`?
   - split package clauses?
   - braces on every class/trait/object/def?

3. Gates:
   ```
   re-scale enforce shortcuts --file <path>     # expect "No shortcut markers found"
   re-scale enforce verify --file <path>        # only if the file has a covenant
   ```

4. Compile the module the file belongs to:
   ```
   re-scale build compile --module <M> --errors-only
   ```
   Add `--jvm --js --native` for cross-built modules - `--all` alone builds
   only the base project.

5. Run its tests if any exist: `re-scale test unit --module <M>` (same
   platform flags; `--only <Suite>` for one suite). Confirm the suite ran.

6. Report PASS or FAIL, listing each failed check with file:line and the fix.

This does not compare against the original source; for that use
`re-scale-audit-file` or the `re-scale-guide-verification` checklist.

## Rules

Use `re-scale` commands and the harness's file tools, not shell utilities.
