# re-scale 0.1.5 command reference

Checked against the sources at
<https://github.com/kubuszok/re-scale/tree/0.1.5/src/main/scala/rescale>.
Every command prints its own usage with `--help`. Flags take `--key value` or
`--key=value`; a flag followed by another `--flag` (or nothing) is a boolean.

## db - tracking tables

```
re-scale db migration list [--status S] [--lib L] [--module M] [--package P] [--limit N] [--offset N]
re-scale db migration get <source_path>
re-scale db migration set <source_path> [--status S] [--notes TEXT] [--port-path P]
re-scale db migration stats

re-scale db issues list [--status S] [--category C] [--file PATH] [--severity SEV] [--limit N] [--offset N]
re-scale db issues add <file> <category> <severity> <description>
re-scale db issues resolve <ISS-NNN>
re-scale db issues reopen <ISS-NNN>
re-scale db issues stats

re-scale db audit list [--status S] [--package P] [--tested T] [--limit N] [--offset N]
re-scale db audit get <file_path>
re-scale db audit set <file_path> --status pass|minor_issues|major_issues [--tested yes|no|partial] [--notes TEXT]
re-scale db audit stats

re-scale db merge --target <tsv> --source <tsv> [--strategy renumber|prefer-left|prefer-right|stricter]
re-scale db <custom-table> list|get|set|add|delete|stats [--key K] [--<column> V ...]
```

Behaviour worth knowing:

- `migration set` only **updates** an existing row (matched exactly on
  `source_path`); there is no `migration add`. On an unknown path it still
  prints `Updated:` and changes nothing. `migration get` matches by substring.
- `audit set` inserts a row when the file is new. Without `--status` a new row
  is recorded as `pass`. The `package` column is filled with the file's parent
  directory name, and `audit list --package` is a substring match on it.
- `issues resolve --notes TEXT` **replaces** the issue description with
  ` — TEXT`. Leave `--notes` off and record the resolution in a commit
  message instead.
- `issues list --category` and `--file` are substring matches; `--status` and
  `--severity` are exact.
- `db merge` reconciles a table from another branch or worktree; `renumber`
  (default for issues) renumbers colliding `ISS-` ids, `stricter` (for audit)
  keeps the worse verdict.
- Custom tables are declared in `.rescale/databases.yaml`
  (`tables: <name>: {file, key, headers, defaults}`) and stored in `.rescale/data/<file>`.

## enforce - scanners and covenants

```
re-scale enforce shortcuts [--src DIRS] [--file F] [--covenanted] [--machine-readable]
re-scale enforce stale-stubs [--src DIRS] [--machine-readable]
re-scale enforce verify --file <path> | --all [--src DIRS] [--machine-readable]
re-scale enforce covenant-apply --file <path> --source <ref> [--spec-pass N] [--covenant LEVEL] [--dry-run] [--force]
re-scale enforce skip-policy [list]
re-scale enforce skip-policy add <path> <tool> [--reason TEXT] [--added-by NAME]
re-scale enforce compare --port <scala> --source <java|dart> [--strict]
```

- `--src` takes comma-separated roots; without it the scan targets are used.
- `shortcuts` exits 0 even with hits (exit 1 only with `--covenanted` and
  hits); read the output, `No shortcut markers found` means clean.
- `compare` exits 1 on missing methods, short bodies or dropped constructor
  parameters. It parses `.java` and `.dart`; any other extension is parsed as
  Dart, so the result is not meaningful for Ruby or JavaScript.
- `verify --file` fails on a file with no covenant header, and on a
  `full-port` covenant whose baseline methods disappeared or that has shortcut
  hits. Covenants other than `full-port` always pass.
- `covenant-apply` refuses when the file has shortcut hits (unless `--force`).
  It records `--source` as a reference but does **not** read it: run `compare`
  yourself first.
- `skip-policy add <path> <tool>`: `<tool>` is `shortcuts`, `stale-stubs` or
  `*`. A path ending in `/` covers a directory; otherwise it matches the whole
  file. Only the `shortcuts` and `stale-stubs` commands read the policy;
  `verify` and `covenant-apply` do not.

## fileinfo - header properties

```
re-scale fileinfo --given <path|dir|glob> [--when <predicate>] --then <action> [--machine-readable] [--dry-run]
```

Actions: `select *`, `select f1,f2`, `set k1=v1,k2=v2`, `sync-check`,
`track-commit`. Details in the `re-scale-porting-file-metadata` skill.

## build, test, git

```
re-scale build compile [--module M] [--jvm] [--js] [--native] [--all] [--errors-only]
re-scale build compile-fmt [same flags as compile]
re-scale build fmt                      # sbt --client scalafmtAll
re-scale build publish-local [--module M] [--jvm] [--js] [--native] [--all]
re-scale build kill-sbt                 # sbt --client shutdown

re-scale test unit [--module M] [--jvm] [--js] [--native] [--all] [--only SUITE]
re-scale test verify                    # compile + Test/compile, every module, JVM/JS/Native

re-scale git status|diff|diff-staged|diff-stat|diff-count|log|log-full|show|branch|blame|tags
re-scale git stage <paths> | stage-all | commit --m 'message' | push
re-scale git gh pr|issue|run|api ...
```

- All build/test commands run `sbt --client <module><suffix>/<task>` one after
  another and stop at the first failure.
- `--module M` picks one module, otherwise every module. `--jvm`, `--js`,
  `--native` select platform projects `M`, `MJS`, `MNative`; `--all`, or no
  platform flag, runs only `M`.
- `--only SUITE` becomes `testOnly *SUITE*`.
- `--errors-only` prints only lines containing `[error]`.
- `git commit` takes only a message (`--m` or `--message`); it runs
  `git commit -m <message>`.

## proc, doctor, runner, metals

```
re-scale proc list [--kind sbt|java|metals|all] [--dir DIR]
re-scale proc kill --pid N
re-scale proc kill --kind sbt|java|metals|all [--dir DIR]    # --kind all requires --dir
re-scale proc kill-sbt [--dir DIR]                           # no --dir = every sbt server on the machine

re-scale doctor [--ci]          # runs .rescale/doctor.yaml; --ci skips interactive installs
re-scale runner list
re-scale runner <name> [--mode MODE] [POSITIONAL...]        # .rescale/runners.yaml; positionals fill $1, $2, ...
re-scale metals install | start [--port N] | stop | status  # default port 7845
```

Config examples for `doctor.yaml` and `runners.yaml`: the
[README at 0.1.5](https://github.com/kubuszok/re-scale/blob/0.1.5/README.md).
