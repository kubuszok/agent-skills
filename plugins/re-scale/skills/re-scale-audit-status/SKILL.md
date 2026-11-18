---
name: re-scale-audit-status
description: >-
  Show audit status from re-scale's audit table - overall counts by verdict with `re-scale db audit stats`, or one
  package's files with `re-scale db audit list --package`, and which files in the package have no audit row yet. Use
  when asked how much of a port has been audited, which files are unaudited, or for the pass / minor_issues /
  major_issues breakdown.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# Audit status

Written for re-scale **0.1.5** (check `re-scale --version`). Input: optional
package name (`$ARGUMENTS` in a slash command).

## Whole project

```
re-scale db audit stats
```

Report the counts per status (`pass`, `minor_issues`, `major_issues`).

## One package

```
re-scale db audit list --package <name>
re-scale db audit list --package <name> --status major_issues
re-scale db audit list --tested no
```

Then list the package's `.scala` files (Glob tool) and report the ones with no
row - they are unaudited.

## Notes

- `--package` is a substring match on the `package` column, which
  `audit set` fills with the file's parent directory name; rows written by
  older tools may use dotted package names, so try both forms.
- `--status` and `--tested` are exact matches. `--limit N` / `--offset N`
  page long lists.
- Never read `.rescale/data/audit.tsv` directly; the hook denies it.
