---
name: re-scale-porting-audit-package
description: >-
  Audit every ported Scala file in one package (or a batch of packages) against the original sources with re-scale -
  enumerate the files, run the per-file audit, write a per-package audit document, record verdicts with
  `re-scale db audit set`, compile, and commit. Use when asked to audit a whole package, directory or module of a
  port, or to produce an audit report per package.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Audit a package

Written for re-scale **0.2.0** (check `re-scale --version`). Input: a package
path such as `math`, `graphics/g2d` or `parser` (`$ARGUMENTS` in a slash
command). `/batch` means: ask the user for a list of packages and audit them
one after another, committing between packages so an interrupted session
loses nothing.

## Procedure

1. **Find the paths.** The project's `CLAUDE.md` or contributing docs map
   upstream packages to Scala source directories.

2. **Enumerate files**: the `.scala` files directly in the package directory
   (not sub-packages). For cross-built modules also check platform-specific
   source directories (for example `src/main/scalajvm`, `scalajs`,
   `scalanative`).

3. **Existing audit doc**: look for `docs/audit/<slug>.md` (or wherever the
   project keeps them), slug = package path with `/` replaced by `-`.

4. **Audit each file** with the `re-scale-porting-audit-file` procedure: compare the
   public API (methods, constants, enums, inner types), conventions, TODOs and
   stubs; update the Migration notes; record the verdict with
   `re-scale db audit set`. For 30+ files work in batches of about 15 and write
   the partial audit doc between batches.

5. **Write the audit doc**:
   ```markdown
   # Audit: <package>

   Audited: N/N files | Pass: P | Minor: M | Major: J
   Last updated: YYYY-MM-DD

   ### FileName.scala

   | Field | Value |
   |-------|-------|
   | Port path | `<path>` |
   | Original source(s) | `<original path>` |
   | Status | pass / minor_issues / major_issues |
   | Tested | Yes - `<test path>` / No - reason |

   **Completeness**: summary of API coverage.
   **Issues**: list, or "None".
   ```

6. **Compile**: `re-scale build compile --module <M> --errors-only` - header
   edits can break a file.

7. **Commit** (when the user allows commits):
   ```
   re-scale git stage <files>
   re-scale git commit --m "audit <pkg>: N files (P pass, M minor, J major)"
   ```

## Rules

- Never read or edit `.rescale/data/` directly; use `re-scale db`.
- Use the harness's search/read/edit tools rather than shell commands.
- Check results with `re-scale db audit list --package <name>`; the
  `package` column holds the file's parent directory name, matched as a
  substring.
