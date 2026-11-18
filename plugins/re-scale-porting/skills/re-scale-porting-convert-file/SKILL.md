---
name: re-scale-porting-convert-file
description: >-
  Convert one original source file (Java, Dart, Ruby or JavaScript) to Scala 3 in a re-scale porting project, end
  to end - read the original from the local checkout, write the license header, find or create the target file,
  apply the conversion guides, compile with `re-scale build compile`, then record progress with
  `re-scale db migration set` and header properties with `re-scale fileinfo ... set`. Use when asked to port,
  convert or translate a specific upstream file.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Convert one file

Written for re-scale **0.2.0** (check `re-scale --version`). Input: the path of
the original source file (`$ARGUMENTS` in a slash command).

## Procedure

1. **Read the original** completely from the local checkout (a submodule such
   as `original-src/`). Never fetch it from the web - the checkout is pinned to
   the version being ported. Note the `@author` tags.

2. **Find the target.** The project's `CLAUDE.md` or contributing docs map
   upstream paths to Scala paths and list renamed or merged files. Check
   `re-scale db migration get <source_path>` for the current status and port
   path. If a Scala file exists, port only what is missing.

3. **Load the guides**: `re-scale-porting-guide-conversion` (plus its language page),
   `re-scale-porting-guide-nullable`, `re-scale-porting-guide-control-flow`,
   `re-scale-porting-guide-code-style`, and the project's type-mapping document.

4. **Write the license header first**, before `package` (see
   `re-scale-porting-guide-code-style`), including the original path and authors.

5. **Convert** every method, branch, edge case and comment. Compile as you go:
   ```
   re-scale build compile --module <M> --jvm --errors-only
   ```

6. **Finish clean**: zero errors and zero warnings on every platform the module
   builds for (`--jvm --js --native`), and
   `re-scale enforce shortcuts --file <scala>` prints no hits.

7. **Update tracking:**
   ```
   re-scale db migration set <source_path> --status ai_converted --port-path <scala path>
   ```
   `migration set` only updates an existing row. If `migration get` shows no
   row, there is no CLI command to add one in 0.2.0 - tell the user.
   Status names are project conventions (`ai_converted`, `ported`, ...); use
   the ones already in `re-scale db migration stats`.

8. **Write the Migration notes** in the header (`Renames:`, `Convention:`,
   `Idiom:`, `Audited:` with today's date), then stamp tracking keys:
   ```
   re-scale fileinfo --given <scala> --then "set original-src=<source_path>,status=ai_converted"
   ```
   `set` splits on commas, so a value cannot contain one - put a multi-author
   list in the header by hand.

9. Hand the file to `re-scale-porting-verify-file` or, in an implement/audit loop, to
   the auditor.

## Rules

- **Porting is binary - 100% or not done.** See `re-scale-porting-guide-porting`.
- Use `re-scale` commands and the harness's file tools; the hook denies most
  shell utilities.
