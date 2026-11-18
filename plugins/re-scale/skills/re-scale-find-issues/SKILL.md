---
name: re-scale-find-issues
description: >-
  Sweep a re-scale port for quality problems - `re-scale enforce shortcuts` (TODO, ???, stub and "for now" markers,
  null casts), `enforce stale-stubs`, leftover `return` / `null` / TODO in main sources, open rows in
  `re-scale db issues`, files missing upstream commit tracking, and migration.tsv drift via
  `fileinfo ... sync-check`. Use when asked to find remaining problems, technical debt or gaps across the codebase,
  or to pick the next gap-fix targets.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Find issues

Written for re-scale **0.1.5** (check `re-scale --version`).

## Procedure

1. Scanners (save the output to a file if it is long):
   ```
   re-scale enforce shortcuts --machine-readable
   re-scale enforce stale-stubs --machine-readable
   ```
   See [the pattern list](#shortcut-patterns) for what each hit means.

2. Convention leftovers in main sources (Grep tool, `*/src/main/scala/`):
   - `\breturn\b` - remaining `return`
   - `\bnull\b` - raw `null` outside interop
   - `TODO|FIXME`

3. Open issues:
   ```
   re-scale db issues list --status open
   re-scale db issues list --status open --severity <sev>
   ```

4. Files without upstream commit tracking:
   ```
   re-scale fileinfo --given . --when "covenant=full-port && upstream-commit=" --then "select source-reference" --machine-readable
   ```

5. Tracking drift:
   ```
   re-scale fileinfo --given . --then "sync-check"
   ```

6. Summarise by severity, group by file, and suggest the next step for each
   (usually `re-scale-gap-fix` for scanner hits).

## Shortcut patterns

Matched anywhere in a line: `todo`, `fixme`, `hack`, `xxx`, `unsupported-op`
(`UnsupportedOperationException`), `not-implemented`
(`throw new NotImplementedError`), `scala-unimpl` (`???`), `catch-throwable`,
`null-cast`, `nullable-null-fallback`, `get-or-else-null`, `this-null-arg`,
`flag-break-var`, `scalastyle-ignore-return`, `throw-not-yet`
(`throw new RuntimeException("... not yet`), `nowarn-stub`, `cssStub-fn`.

Matched only inside comments: `stub-comment`, `simplified-comment`,
`minimal-comment`, `placeholder-comment`, `tbd-comment`, `pending-comment`,
`shim-comment`, `best-effort-comment`, `approximation-comment`,
`deferred-comment`, `phase-n-comment` (`Phase 2`), `not-yet-comment`,
`would-be-used`, `handled-below`, `for-now-comment`, `break-comment`,
`return-comment`, `would-do-comment`, `aspirational-com`.

Source: [Shortcuts.scala at 0.1.5](https://github.com/kubuszok/re-scale/blob/0.1.5/src/main/scala/rescale/enforce/Shortcuts.scala).

## Notes

- `enforce shortcuts` exits 0 even with hits; read the output.
- Upstream comments copied verbatim can trigger comment patterns. They stay
  (comments are never removed); note them as false positives.
- Skip-policy entries (`re-scale enforce skip-policy list`) hide every hit of
  that tool in the listed file or directory - review them as part of the sweep.
- Never read or search `.rescale/data/` directly; use `re-scale db`.
