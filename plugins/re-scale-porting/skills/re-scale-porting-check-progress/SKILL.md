---
name: re-scale-porting-check-progress
description: >-
  Report the progress of a port tracked with re-scale - migration status counts (`re-scale db migration stats`),
  audit verdicts, covenant coverage (`enforce verify --all`), shortcut hits, and header metadata coverage via
  `re-scale fileinfo`, plus keeping a ratchet baseline so counts only go down. Use when asked how far a port is,
  for a status summary, or before and after a batch of porting work.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Check progress

Written for re-scale **0.2.0** (check `re-scale --version`).

## Procedure

1. Migration: `re-scale db migration stats` (by status, library, module).
2. Audit: `re-scale db audit stats`.
3. Issues: `re-scale db issues stats`.
4. Covenants:
   ```
   re-scale enforce verify --all --machine-readable
   ```
   TSV `file<TAB>pass|fail<TAB>reason`. Count `pass`; among failures, separate
   `no covenant header` (not stamped yet) from real failures.
5. Shortcuts:
   ```
   re-scale enforce shortcuts --machine-readable
   ```
   TSV `file<TAB>line<TAB>pattern<TAB>text`: count hits and distinct files.
6. Header metadata:
   ```
   re-scale fileinfo --given . --when "covenant=full-port" --then "select covenant" --machine-readable
   re-scale fileinfo --given . --when "covenant=full-port && upstream-commit=" --then "select source-reference" --machine-readable
   ```
   The first counts covenanted files, the second those without upstream commit
   tracking.

## Report

- Migration: X of Y upstream files converted (Z skipped with reasons)
- Audit: P pass, M minor, J major
- Issues: open vs resolved
- Covenants: N stamped, V verified, F failing
- Shortcuts: H hits in K files (gap-fix candidates)
- Upstream tracking: N covenanted files without `upstream-commit`

## Ratchet

For long campaigns, keep the numbers that must only fall (shortcut hits,
covenant failures, `.fail`/`assume(` markers in tests, open major issues) in a
committed baseline file next to the exact command that measures each one.
Re-measure with the same command after every change; any increase is a
regression. Lower the baseline only after a verified improvement - raising it
needs the user.

## Notes

- `--machine-readable` output is TSV; save it to a file and read it rather
  than piping into `wc`/`grep` (the hook denies those pipes).
- `enforce verify --all` reads every `.scala` file under the scan roots and can
  take minutes on large projects.
- Never read `.rescale/data/` directly.
