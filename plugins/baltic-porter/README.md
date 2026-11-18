# `baltic-porter` plugin

Skills for repositories that **use** [Baltic Porter](https://github.com/kubuszok/balticporter), the
engine that generates Scala 3 sources from Java libraries as an sbt source generator — for example
[sge](https://github.com/kubuszok/sge), [ssg](https://github.com/kubuszok/ssg) and
[lls](https://github.com/kubuszok/lls). They are written for an agent working in such a consumer
repository, which has no engine checkout: engine files are linked on GitHub.

Version: written against engine master `ab8e129d`. Baltic Porter has no releases yet; a consumer pins
a snapshot per engine commit in `project/plugins.sbt` as
`"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`. The engine's user guide is
in [`docs/user-guide`](https://github.com/kubuszok/balticporter/tree/master/docs/user-guide).

Install: `/plugin install baltic-porter@kubuszok` (Claude Code). See the [root README](../../README.md)
for other harnesses. Building and publishing with sbt-kubuszok (aliases, CI matrix, releases) is
covered by the `sbt-kubuszok` plugin; install it alongside.

## Skills

| Skill | Covers |
|---|---|
| `baltic-porter-generated-code` | How generation is wired (pin, `BalticPorterGen.scala`, policy, `src_managed`, marker, reports), never editing generated code, resources, bumping and proving the engine pin |
| `baltic-porter-configure-port` | Writing a port `.conf` or `PortRun`: input, output, roots, manifest, dependents (`base`), how many confs, report directory under sbt; key reference |
| `baltic-porter-customize-port` | The three kinds of fix, every surface phase and its keys, `scope`, `derive`, drop + inject, writing and testing a library-specific `Phase` + `TransformFactory` |
| `baltic-porter-read-port-issues` | The report directory, `errors.tsv` lanes, every check, policy that never fired, `decisions.tsv` and porter notes, test-failure anchors |
| `baltic-porter-root-cause-port` | Tracing a generated spelling to the decision that produced it, comparing with the reference hand port, choosing where the fix goes |
| `baltic-porter-cross-platform-port` | Scala.js / Scala Native javalib gaps, portability findings, per-platform policy answers |
| `baltic-porter-consumer-ci` | The local loop before a push (`generatePort`, `testCompile-*`, `verifyLocal`), what counts as cheating, the covenant gate |
| `baltic-porter-ci-caching` | CI shape (one `generate`, one `compile` per row), the `generated-port` action and its cache key, the sbt remote cache, `--server` on runners |
| `baltic-porter-sbt2-client` | Driving sbt 2 with `--client`, `reload` before `publishLocal`, a stale action cache, the JDK, the generation marker, sbt 2.1's test summary |

## Hooks (Claude Code only)

`hooks/hooks.json` registers `hooks/guard.py` as a `PreToolUse` hook (via `${CLAUDE_PLUGIN_ROOT}`) on
`Bash` and on `Edit` / `Write` / `NotebookEdit`. Other harnesses ignore it. It blocks:

- a bare `sbt` / `sbt -batch` (use `sbt --client "…"`), and pattern kills (`pkill`, `killall`,
  `xargs kill`);
- in-place `sed -i` / `perl -i` and Python rewrites of repository files (scratch paths are allowed);
- `git merge` without `--ff-only`, `--no-verify`, `git reset --hard`, `git stash`, empty commits and
  plain force pushes;
- `rm -rf` of the sbt cache;
- `git push` in a repository with `project/BalticPorterGen.scala` until `target/local-verification`
  (written by `sbt --client verifyLocal`) names HEAD, unless only docs, `.github/`, `.claude/` or
  `.rescale/data/` changed since;
- edits under `src_managed/` or `target/balticporter-*/`.

Self-test: `python3 hooks/guard_test.py`.
