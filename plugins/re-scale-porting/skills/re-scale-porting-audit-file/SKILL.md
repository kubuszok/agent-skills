---
name: re-scale-porting-audit-file
description: >-
  Audit one ported Scala file against its original source with re-scale - read its header properties with
  `re-scale fileinfo`, run `enforce shortcuts`, `enforce compare --strict` and `enforce verify`, check conventions
  and tests, record the verdict with `re-scale db audit set`, and stamp a covenant when it passes. Use when asked to
  audit, review or sign off a single ported file, or to record a pass / minor_issues / major_issues verdict.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Audit one file

Written for re-scale **0.2.0** (check `re-scale --version`). Input: the path
of the ported Scala file (`$ARGUMENTS` when run as a slash command).

## Procedure

1. **Read the header properties** without opening the whole file:
   ```
   re-scale fileinfo --given <path> --then "select *"
   ```
   Shows covenant status, `source-reference`/`original-src`, authors,
   `upstream-commit` and the Migration notes keys.

2. **Find the original.** From `original-src`, `source-reference` (or any
   `*-reference` key), or through the project's path mapping. Read it from the
   local checkout (a submodule such as `original-src/`), never from the web.

3. **Read both files** completely.

4. **Run the gates:**
   ```
   re-scale enforce shortcuts --file <path>
   re-scale enforce compare --port <path> --source <original> --strict   # Java/Dart sources
   re-scale enforce verify --file <path>                                 # only if it has a covenant
   ```

5. **Compare by hand**: method inventory, branches, error handling, edge
   cases, side effects - the procedure in the `re-scale-porting:port-auditor` agent. Check
   renames against the header's `Renames:` line.

6. **Check conventions**: license header with upstream attribution; no
   `return`; no raw `null`; `final case class`; split packages; braces;
   `boundary`/`break` where the original exits early; original comments kept.

7. **Check tests**: does the original have tests, and are they ported and run?

8. **Record the verdict** (always pass `--status`; a new row without it is
   stored as `pass`):
   ```
   re-scale db audit set <path> --status <pass|minor_issues|major_issues> --tested <yes|no|partial> --notes "..."
   ```
   Record each problem as an issue:
   `re-scale db issues add <path> <category> <severity> "<specific description>"`.

9. **If everything passes**, update the header's `Audited:` date and stamp the
   covenant:
   ```
   re-scale enforce covenant-apply --file <path> --source <original> [--spec-pass N]
   ```

## Verdicts

- `pass` - every method and branch ported, gates clean, conventions met.
- `minor_issues` - complete logic, convention or documentation problems only.
- `major_issues` - anything missing, stubbed or behaving differently.

## Rules

- Never read or edit `.rescale/data/` directly; use `re-scale db`.
- Prefer the harness's search/read tools (Grep, Glob, Read in Claude Code) to
  shell `grep`/`find`/`cat`; the re-scale hook denies the shell versions.
