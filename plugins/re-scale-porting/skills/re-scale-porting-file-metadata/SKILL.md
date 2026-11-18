---
name: re-scale-porting-file-metadata
description: >-
  Query, filter and batch-update the key-value properties in ported files' header comments with
  `re-scale fileinfo --given <path|dir|glob> --when <predicate> --then <action>` - select fields without opening
  files, find files by property (covenant, source-reference, original-src, upstream-commit, authors, status),
  batch `set`, `sync-check` against migration.tsv, and `track-commit` for upstream commit hashes. Use when you need a
  header property of one or many files, files missing a property, or to stamp properties across files.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# File header metadata

Written for re-scale **0.2.0** (check `re-scale --version`). `re-scale fileinfo`
reads `Key: value` lines from a file's leading comment, so you can query
properties instead of opening files.

```
re-scale fileinfo --given <path|dir|glob> [--when <predicate>] --then <action> [--machine-readable] [--dry-run]
```

`--given` defaults to `.`, `--then` to `select *`.

| Action | Does |
|---|---|
| `select *` | print every header property |
| `select f1,f2` | print the named properties |
| `set k1=v1,k2=v2` | insert or update properties in the header |
| `sync-check` | compare `migration.tsv` with the headers; exit 1 on mismatch |
| `track-commit` | write the upstream file's latest commit hash into `upstream-commit` and update `migration.tsv` |

## Properties

- Parsed from the leading `/* */` or `//` comment, first 80 lines. Keys are
  lower-cased; `Copyright` and `SPDX-License-Identifier` are skipped. A key is
  one word with letters, digits, `_`, `-` (so `Original source:` is NOT a
  property, `original-src:` is).
- Covenant lines lose their prefix: `covenant`, `baseline-spec-pass`,
  `baseline-loc`, `baseline-methods`, `source-reference`, `verified`
  (`Covenant-dart-reference` also becomes `source-reference`).
- Common plain keys: `original-src`, `authors`, `upstream-commit`, `module`,
  `status`, `tags`; Migration notes: `renames`, `convention`, `idiom`,
  `audited`.

## Predicates (`--when`)

| Operator | Example |
|---|---|
| `=` / `!=` | `covenant=full-port`, `status!=ported` |
| `contains` | `authors contains alice` (substring or comma-list member) |
| `starts-with` / `ends-with` | `source-reference ends-with .java` |
| `&&`, `\|\|`, `!`, `( )` | `(status=ported \|\| status=done) && covenant=full-port` |

A missing property equals the empty string, so `upstream-commit=` finds files
without it. Quote values with spaces: `status="in progress"`.

## Recipes

```
re-scale fileinfo --given <file> --then "select covenant,source-reference"
re-scale fileinfo --given <dir> --when "covenant=full-port" --then "select covenant,verified" --machine-readable
re-scale fileinfo --given <dir> --when "covenant=full-port && upstream-commit=" --then "set upstream-commit=pending" --dry-run
re-scale fileinfo --given <dir> --then "sync-check"
re-scale fileinfo --given <dir> --when "original-src!=" --then "track-commit" --dry-run
```

Drop `--dry-run` to apply. `set` keeps the `Covenant-` prefix on disk for
covenant fields.

## When to use what

| Need | Use |
|---|---|
| a property of one or many files | `fileinfo select` |
| files missing a property | `fileinfo --when "<key>="` |
| stamp properties on many files | `fileinfo set` (try `--dry-run` first) |
| the code itself | read the file |
| gate checks | `re-scale enforce` |
| migration / issue / audit rows | `re-scale db` |

## Gotchas

- **What `--given` covers.** Relative paths resolve against the project root,
  not the current directory. `.` means the scan targets (main sources, no
  tests); a directory or glob walks only `.scala` files.
- **`set` splits on commas.** `set authors=a, b` writes `authors=a` and drops
  `b`. Values with commas must be edited by hand.
- **`track-commit` needs a repository.** It runs `git log -1` for the path in
  `original-src` (or `source-reference`) inside the submodule that
  `.rescale/source-repos.yaml` maps it to (by path prefix, or by the migration
  row's library). Without a mapping it runs in the project root and finds
  nothing.
- **`sync-check` reports mismatches as exit 1**; read them before "fixing" -
  either the header or the migration row may be the stale side.
