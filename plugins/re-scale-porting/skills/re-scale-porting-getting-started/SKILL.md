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
  library-version: "0.2.0"
---

# re-scale: getting started

re-scale is a Scala Native CLI that gives a porting project a hook layer, TSV
tracking databases and anti-shortcut scanners. Project specifics live in
`.rescale/` in the consuming repository, not in the tool.

This skill describes re-scale **0.2.0**. Check `re-scale --version`; if it
differs, read the README at the matching tag
(`https://github.com/kubuszok/re-scale/blob/<tag>/README.md`).

## Install

re-scale is published to Maven Central: a native executable for Linux and
macOS on x86_64 and aarch64, and a JVM build for everything else.

- **Claude Code plugin** (this plugin): a `SessionStart` hook uses a
  `re-scale` already on `PATH` if it reports 0.2.0; otherwise it installs 0.2.0
  with [Coursier](https://get-coursier.io) into
  `~/.local/share/re-scale/0.2.0/bin` (or `$RESCALE_INSTALL_DIR`) - the native
  executable, or the JVM build when no executable fits and `java` is on `PATH` -
  and puts that directory on `PATH` for the session. It needs `cs` on `PATH`.
  `RESCALE_REPOSITORY` points it at a Maven Central mirror.
- **Manually**, with Coursier:
  ```bash
  V=0.2.0
  cs install --install-dir ~/.local/bin "re-scale:{\"dependencies\":[\"com.kubuszok:re-scale_native0.5_3:$V\"],\"repositories\":[\"central\"],\"launcherType\":\"prebuilt\",\"prebuilt\":\"https://repo1.maven.org/maven2/com/kubuszok/re-scale_native0.5_3/\${version}/re-scale_native0.5_3-\${version}-\${platform}.bin\"}"
  re-scale --version
  ```
  On another platform install the JVM build (Java 17+; every call starts a JVM):
  ```bash
  cs install --install-dir ~/.local/bin "re-scale:{\"dependencies\":[\"com.kubuszok:re-scale_3:$V\"],\"repositories\":[\"central\"],\"mainClass\":\"rescale.Main\",\"javaOptions\":[\"-Xmx1g\"]}"
  ```

The executable caps its heap at 1 GB (compiled in); set `GC_MAXIMUM_HEAP_SIZE`
to override it. The JVM build runs with `-Xmx1g`.

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

- **`re-scale: command not found` at session start.** The hook prints a
  `[re-scale] WARNING` to stderr and exits 0 when it cannot install: usually
  `cs` is not on `PATH` (install Coursier and restart the session), or the
  download failed. The full output is in
  `~/.local/share/re-scale/0.2.0/install.log`. The Linux executables need
  glibc 2.35 or newer; on an older system the hook falls back to the JVM build
  if `java` is on `PATH`.
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
