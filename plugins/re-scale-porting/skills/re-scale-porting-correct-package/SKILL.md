---
name: re-scale-porting-correct-package
description: >-
  Re-audit and fix every issue in one package of a re-scale port in four phases - audit, fix (stubs, missing
  methods, convention violations, missing tests), re-audit until clean (at most three rounds), then compile and
  commit - with `re-scale enforce shortcuts` and `enforce verify` as the gate for each touched file. Use when asked
  to correct, clean up or bring a whole package to pass.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.2.0"
---

# Correct a package

Written for re-scale **0.2.0** (check `re-scale --version`). Input: a package
path such as `math` or `parser/inline` (`$ARGUMENTS` in a slash command).

## Phase 1: Re-audit

1. Run the `re-scale-porting-audit-package` procedure on the package with the current
   criteria.
2. Collect every issue, major first, also
   `re-scale db issues list --file <package dir> --status open`.

## Phase 2: Fix

3. Work through the list:
   - **Stubs / incomplete bodies**: port the missing logic from the original.
   - **Missing methods or fields**: port them.
   - **Convention violations**: `return` -> `boundary`/`break`, `null` ->
     the project's nullable type, header, braces, split packages.
   - **Missing tests**: port the original's tests; if it has none, write tests
     for the public API.
4. Compile after each batch: `re-scale build compile --module <M> --errors-only`.
5. Run tests when tests changed: `re-scale test unit --module <M>` (add
   `--jvm --js --native` for cross-built modules) and check your suites ran.
6. Gate every touched file:
   - `re-scale enforce shortcuts --file <path>` - no new hits
   - `re-scale enforce verify --file <path>` - passes, if it has a covenant

## Phase 3: Re-audit

7. Run `re-scale-porting-audit-package` again; fixes can introduce new problems.
8. Fix and re-audit until clean, at most three rounds; then report what is
   left instead of looping.

## Phase 4: Commit

9. `re-scale build compile --module <M>`.
10. When the user allows commits:
    ```
    re-scale git stage <files>
    re-scale git commit --m "correct <pkg>: fix N issues (M major, m minor)"
    ```
    Resolve the fixed issues with `re-scale db issues resolve <ISS-NNN>`.

## Rules

- Never remove comments from the original; only add or update Migration notes.
- **Porting is binary - 100% or not done.** See `re-scale-porting-guide-porting`.
- Use `re-scale` commands and the harness's file tools, not shell utilities.
