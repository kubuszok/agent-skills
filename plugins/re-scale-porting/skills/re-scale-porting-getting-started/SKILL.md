---
name: re-scale-porting-getting-started
description: >-
  Setting up and using the re-scale CLI (Scala Native porting toolkit) in a repository that ports a library to
  Scala 3 - installing the binary, the `.rescale/` directory (doctor.yaml, runners.yaml, databases.yaml,
  source-repos.yaml, modules.txt, scan-targets.txt, data/*.tsv), and which command to reach for (db, enforce,
  fileinfo, build, test, git, proc, doctor, runner, metals), with the full command reference. Use when re-scale is
  not on PATH, when adding a .rescale config file, or when unsure which re-scale command fits a porting task.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# re-scale: getting started

re-scale is a Scala Native CLI that gives a porting project a hook layer, TSV
tracking databases and anti-shortcut scanners. Project specifics live in
`.rescale/` in the consuming repository, not in the tool.

This skill describes re-scale **0.1.5**. Check `re-scale --version`; if it
differs, read the README at the matching tag
(`https://github.com/kubuszok/re-scale/blob/<tag>/README.md`).

## Install

- **Claude Code plugin** (this plugin): a `SessionStart` hook clones the 0.1.5
  tag into `~/.local/share/re-scale/0.1.5` (or `$RESCALE_HOME`), builds it with
  `sbt install` on first use, and puts its `bin/` on `PATH` for the session.
- **Manually**: `git clone --branch 0.1.5 https://github.com/kubuszok/re-scale.git`,
  `sbt install` inside it, then add its `bin/` to `PATH`.

Both need a JDK (22+), sbt and Clang/LLVM. Always call the `bin/re-scale`
wrapper: it caps the heap at 1 GB; the raw binary is unsupported.

## The hook: install `re-scale-hooks` too

The guard hook (denying shell `grep`/`find`/`sed`, bare `sbt`, `rm`, `kill`,
destructive git and direct access to `.rescale/data/`) lives in the separate
`re-scale-hooks` plugin. Install it too: the porting skills assume its rules.
Its `re-scale-hooks-guard` skill lists the rules and the
`.rescale/claude-hooks.yaml` format.

## Project layout

re-scale finds the project root by walking up from the current directory to the
first of `.rescale`, `build.sbt`, `build.sc`, `pom.xml`, `Cargo.toml`,
`package.json`, `pyproject.toml`, `.git`.

| File | Purpose |
|---|---|
| `.rescale/claude-hooks.yaml` | Extra hook rules (see `re-scale-hooks-guard`) |
| `.rescale/doctor.yaml` | Environment checks and install steps for `re-scale doctor` |
| `.rescale/runners.yaml` | Test-runner adapters for `re-scale runner <name>` |
| `.rescale/databases.yaml` | Custom TSV tables for `re-scale db <table> ...` |
| `.rescale/source-repos.yaml` | `source-repos:` map of library name -> submodule path, used by `fileinfo ... track-commit` |
| `.rescale/modules.txt` | Module names, one per line; otherwise every top-level dir with `src/main/scala` |
| `.rescale/scan-targets.txt` | Source roots for the scanners; otherwise `*/src/main/scala` and `src/main/scala` |
| `.rescale/data/migration.tsv` | Per-upstream-file port status |
| `.rescale/data/issues.tsv` | Issue tracker (`ISS-NNN`) |
| `.rescale/data/audit.tsv` | Per-file audit verdict |
| `.rescale/data/skip-policy.tsv` | Allow list for the scanners |

Never read or edit `.rescale/data/` directly - go through `re-scale db` and
`re-scale enforce skip-policy`, which lock the file. The hook denies Read,
Edit and Write on any path containing `.rescale/data/`.

## Which command

| Task | Command | Skill |
|---|---|---|
| Port a file | `re-scale build compile`, `re-scale db migration set` | `re-scale-porting-convert-file` |
| Check a port is complete | `re-scale enforce compare --strict`, `enforce shortcuts` | `re-scale-porting-verify-file`, `re-scale-porting-audit-file` |
| Fix scanner hits | `re-scale enforce shortcuts --file` | `re-scale-porting-gap-fix` |
| Lock a finished file | `re-scale enforce covenant-apply` | `re-scale-porting-guide-verification` |
| Read header properties | `re-scale fileinfo --given F --then "select *"` | `re-scale-porting-file-metadata` |
| Progress numbers | `re-scale db migration stats`, `db audit stats` | `re-scale-porting-check-progress` |
| Kill a stuck sbt server | `re-scale proc kill --kind sbt --dir <repo>` | - |

Flags for every command: [cli-reference.md](cli-reference.md).

## Gotchas

- **`re-scale: command not found` at session start.** The first build takes
  a while and needs sbt and Clang on `PATH`; the hook prints a warning to
  stderr and exits 0 when it fails. Run `sbt install` in
  `~/.local/share/re-scale/0.1.5` by hand to see the error.
- **`--all` is not "all platforms".** In `build compile`, `build publish-local`
  and `test unit`, `--all` means "no platform suffix" - the same as passing no
  platform flag. For JVM + JS + Native pass `--jvm --js --native`, or use
  `re-scale test verify` (compiles main and test of every module on all three).
  The platform flags append `JS` / `Native` to module names, matching sbt
  `projectMatrix` naming.
- **Wrong module list.** If modules do not follow `<dir>/src/main/scala`, list
  them in `.rescale/modules.txt`; scanners use `.rescale/scan-targets.txt`.
- **A command was denied.** Read the reason; it names the alternative
  (`re-scale-hooks-guard` lists them). If the command is really needed, ask the
  user to add a rule rather than working around the hook.
