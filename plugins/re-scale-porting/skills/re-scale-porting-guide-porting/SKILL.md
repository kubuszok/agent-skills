---
name: re-scale-porting-guide-porting
description: >-
  The porting workflow for re-scale projects - the 100% rule, the implement -> audit -> fix -> re-audit loop with
  the re-scale-porting:port-implementer and re-scale-porting:port-auditor agents, fixing one tracked issue with a failing test first, proof of red and
  mutation checks, documented skips instead of silent omissions, and who may resolve issues or stamp covenants. Use
  when starting or orchestrating porting work, when dispatching implementer/auditor subagents, when fixing an
  `ISS-NNN` issue from `re-scale db issues`, or when someone argues a partial port is good enough.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Porting workflow

Written for re-scale **0.2.0** (check `re-scale --version`). Use this when
converting code from an original source (Java, Dart, Ruby, JavaScript) to
Scala 3, or when checking ported code for completeness.

## The 100% rule

**Porting is binary - 100% or not done.** Every method, branch and edge case
of the original is ported. A file at 74% is incomplete, not "mostly done".
"Diminishing returns", "low priority", "edge case", "good enough" are not
reasons. The only valid reason to skip something is an explicit user
instruction - and then it is recorded (below).

## Nothing is skipped silently

Every upstream file ends up in one of two states:

1. **Ported** - a Scala file exists and its audit row is `pass` or
   `minor_issues`.
2. **Skipped, with a recorded reason** - for example
   `re-scale db migration set <source_path> --status skipped --notes "JVM-only dependency; replaced by X"`.
   Good reasons: depends on a library the target platforms cannot use,
   command-line entry point, IDE/build-tool glue, upstream's own dev tooling,
   deprecated upstream, replaced by a Scala-native equivalent (name it). "Not
   yet" is not a skip; it is an open issue.

Anything else is a gap the audit must report.

## Agents (Claude Code)

| Agent | Role | Edits code? |
|---|---|---|
| `re-scale-porting:port-implementer` | ports original code, addresses findings | yes |
| `re-scale-porting:port-auditor` | compares port with original, records issues | no |

In other harnesses, run the same two roles as separate sessions with the
agent files' instructions.

## The implement-audit loop

```
1. IMPLEMENTER: port the file or module -> compile, test, report metrics
2. AUDITOR:     compare original and port -> findings, issues, PASS/FAIL
3. ORCHESTRATOR (you): PASS -> close and commit; FAIL -> send findings back
4. IMPLEMENTER: fix every finding (mandatory) -> compile, test, report
5. AUDITOR:     re-audit; repeat until PASS
```

Never consider porting done after one implementation pass. Use the loop for new
ports and for filling gaps. It is not needed for build changes or
documentation.

Roles stay separate:
- The implementer does not resolve issues, stamp covenants or edit `.rescale/`.
- The auditor does not edit code. When several auditors run in parallel from
  different worktrees, they recommend issues and the orchestrator files them -
  parallel `issues add` from separate checkouts allocate colliding ids.
- The orchestrator re-runs the cheap gates itself instead of trusting a
  report; a gate claimed green that is red is itself a finding.
- Use a different model (or at least a fresh context) for the auditor than for
  the implementer.

## Fixing one tracked issue

1. **Reproduce first.** Write (or receive) a test that fails for exactly the
   reason the issue states, and commit it before the fix. If it will not
   fail, the issue may be stale - report that instead of "fixing".
2. **Fix from the original.** Find the original file and lines; port that
   logic. No workaround that "should behave the same".
3. **Differential tests** for options that were accepted but ignored: toggle
   each one and assert the outputs differ, citing how the original uses it.
4. **Do not touch the red test**, existing expectations (without an upstream
   citation), or add `.fail`/`assume`/`@nowarn` without an open issue id on the
   same line.
5. **Audit**: proof of red (revert the fix, the test fails; restore, it
   passes), a mutation spot-check (break the fix on purpose, the tests catch
   it), the cheat sweep in the `re-scale-porting:port-auditor` agent, and a re-read of the issue
   text - every clause fixed, or FAIL.
6. Only then `re-scale db issues resolve <ISS-NNN>`.

## Keeping score

```
re-scale db issues list --file <path-part> --status open
re-scale db issues stats
re-scale db audit list --package <pkg>
re-scale db audit stats
re-scale db migration stats
```

A useful guard for long campaigns is a **ratchet**: record the counts that
should only go down (shortcut hits, `verify --all` failures, `.fail`/`assume`
markers in tests) in a committed baseline file, compare after every change,
and treat any increase as a failure. Only lower the baseline after a verified
improvement; raising it is a user decision.

## Related skills

- `re-scale-porting-guide-conversion`, `re-scale-porting-guide-nullable`,
  `re-scale-porting-guide-control-flow`, `re-scale-porting-guide-code-style`
- `re-scale-porting-guide-verification` - the checklist before "done"
- `re-scale-porting-convert-file`, `re-scale-porting-audit-file`, `re-scale-porting-audit-package`,
  `re-scale-porting-correct-package`, `re-scale-porting-gap-fix`
- `re-scale-porting-file-metadata`, `re-scale-porting-check-progress`

## Gotchas

- **Lost work after merging branches.** Issue/audit TSVs edited on two branches
  conflict; reconcile with
  `re-scale db merge --target <ours.tsv> --source <theirs.tsv>` (issues default
  to renumbering colliding ids, audit with `--strategy stricter` keeps the
  worse verdict).
- **Stale "not ported" comments.** Before believing a comment that says
  something is missing, check the code; `re-scale enforce stale-stubs` finds
  comments naming identifiers that now exist.
