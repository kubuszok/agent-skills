---
name: re-scale-porting-guide-verification
description: >-
  Post-conversion verification checklist for a Scala file ported under re-scale, cheapest check first - compile on
  every target platform, tests that actually ran, `re-scale enforce shortcuts`, `enforce compare --strict`,
  `enforce stale-stubs`, `enforce verify`, stamping a covenant with `enforce covenant-apply`, upstream commit
  tracking and migration/audit status. Use before declaring a ported file done, before stamping a Covenant header,
  and when a covenant check fails in CI.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Verification checklist

Written for re-scale **0.2.0** (check `re-scale --version`). Run after every
conversion, in this order; stop and fix at the first failure.

| # | Check | Command | Pass when |
|---|---|---|---|
| 1 | Header | read the file's first lines | license header, upstream path, authors, Migration notes |
| 2 | Compile | `re-scale build compile --module M --jvm --js --native --errors-only` (only the platforms the module builds for) | no errors, no warnings |
| 3 | Tests | `re-scale test unit --module M --jvm --js --native` (same platforms) | every suite passes AND the suites you expect appear with more than 0 tests run |
| 4 | Shortcuts | `re-scale enforce shortcuts --file F` | prints `No shortcut markers found` |
| 5 | Parity | `re-scale enforce compare --port F --source S --strict` (Java/Dart) | exit 0: no missing methods, short bodies or dropped constructor parameters |
| 6 | Stale stubs | `re-scale enforce stale-stubs --src <module>/src/main/scala` | no hits |
| 7 | Covenant | `re-scale enforce verify --file F` (only if F already has a covenant) | `verified` |
| 8 | Stamp | `re-scale enforce covenant-apply --file F --source S [--spec-pass N]` | `created` or `updated` |
| 9 | Upstream commit | `re-scale fileinfo --given F --then "track-commit"` | `upstream-commit` written |
| 10 | Tracking | `re-scale db migration set S --status <status>`; `re-scale db audit set F --status pass --tested yes` | rows updated |
| 11 | Sync | `re-scale fileinfo --given <dir> --then "sync-check"` | exit 0 |

Steps 1-6 are the conversion gate. Steps 7-11 belong to whoever is allowed to
close work - in an implement/audit loop that is the auditor or orchestrator,
not the implementer.

## Manual checks the tools cannot do

- **Completeness**: every public and private method, constant, enum and inner
  type of the original is present (renames recorded under `Renames:`).
- **Branches**: every `if`/`switch` arm, loop and `catch` of the original is
  present - compare method by method, not file by file.
- **Idioms**: no `return`, no raw `null`, no Java keywords (`public`, `static`,
  `void`), braces, split packages, `final case class`.
- **Semantics**: the "compiles but means something else" table in
  `re-scale-porting-guide-conversion`.
- **Comments**: every original comment kept.
- **Tests**: upstream tests ported when they exist; a test that exposed a bug
  led to a code fix, not a weaker test.

## Covenant headers

`covenant-apply` writes a block like this into the leading comment:

```
 * Covenant: full-port
 * Covenant-baseline-spec-pass: 776
 * Covenant-baseline-loc: 1153
 * Covenant-baseline-methods: name1,name2,...
 * Covenant-source-reference: path/to/Original.java
 * Covenant-verified: 2026-04-08
```

From then on `re-scale enforce verify` fails the file if a baseline method
disappears or a shortcut marker appears. A CI gate usually runs
`re-scale enforce verify --all` plus `re-scale enforce shortcuts --covenanted`
(which exits 1 when a covenanted file has hits). `--spec-pass` records the
module's passing test count at stamping time. `--covenant <level>` writes
another level (e.g. `partial-port`); only `full-port` is enforced.

## Gotchas

- **`--all` compiles only the base (JVM) project.** It means "no platform
  suffix", not "all platforms". Pass `--jvm --js --native`, or run
  `re-scale test verify` to compile main and test sources of every module on
  all three.
- **`enforce shortcuts` exits 0 with hits.** Read its output. Only
  `--covenanted` turns hits into exit 1.
- **`covenant-apply` refused.** `refused - N shortcut hit(s): pattern@line`.
  Fix the hits; `--force` skips the check but `enforce verify` will then fail
  the file. Skip-policy entries are ignored by `verify` and `covenant-apply`.
- **`covenant-apply` does not compare with the source.** `--source` is only
  recorded. Run step 5 first; the baseline locks in whatever methods the
  file has, complete or not.
- **`verify` fails with `no covenant header`** on any file without one; with
  `--all` it walks every `.scala` file under the scan roots, so uncovenanted
  files show up as failures too. Count only real failures.
- **`covenant-apply` fails on a file with no leading `/* ... */` comment.**
  Write the license header first; the covenant lines go inside it.
- **`track-commit` finds no commit.** It reads `original-src` (or
  `source-reference`, or any `*-reference` key) from the header and runs
  `git log` in the repository `.rescale/source-repos.yaml` maps it to
  (`source-repos: {<lib>: <submodule path>}`) - chosen by path prefix, or by
  the migration row's library. Add the mapping, or make the header path start
  with the submodule path.
- **A test file nobody runs.** Check the runner output lists your suite with a
  non-zero test count; a misnamed or misplaced suite passes by not running.
