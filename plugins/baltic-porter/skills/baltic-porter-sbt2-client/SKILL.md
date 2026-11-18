---
name: baltic-porter-sbt2-client
description: >-
  Driving sbt 2 in a repository that generates Scala with Baltic Porter (sge, ssg, lls): `sbt --client`
  only, one client per server, one quoted command string, `reload` before `publishLocal` because the
  version is the git hash at server load, a stale action cache (~/Library/Caches/sbt/v2/ac), the JDK
  the server runs on, the generation marker and `generatePort`, sbt 2.1's `passed: total` / `failed:
  total` summary, long runs logged with tee. Use before any sbt invocation in such a repository, and
  when sbt behaves strangely there (stale output, a wrong version, "Not a valid command", "Expected ID
  character", a hang, "sbt server disconnected").
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# Driving sbt 2 in a Baltic Porter consumer

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
The consumers (sge, ssg, lls) build with sbt 2.1.0 and sbt-kubuszok 0.2.4 (0.2.5 on its way). Check
`project/build.properties` and `project/plugins.sbt`; on sbt 2.0.x the test summary and a few
details below differ.

This skill covers how sbt is *driven* in these repositories. How the build is *set up* (the
`ci-<platform>-<scala>` / `test-*` aliases, `testFull`, `projectType`, which sbt-kubuszok version goes
with which sbt) is in the `sbt-kubuszok` plugin's skills: `sbt-kubuszok-setup`,
`sbt-kubuszok-github-actions` and `sbt-kubuszok-troubleshooting`. Install that plugin too rather than
re-deriving it here. The sbt 2 change summary is at
<https://www.scala-sbt.org/2.x/docs/en/changes/sbt-2.0-change-summary.html>.

The `hooks/guard.py` hook of this plugin (Claude Code only) blocks a bare `sbt`, `sbt -batch` and
pattern kills (`pkill`, `killall`). The rules below are why.

## 1. One server per checkout, one client at a time

- Always `sbt --client "cmd1; cmd2"`. A bare `sbt` starts a second server against the same
  checkout. Two clients on one server queue rather than fail, so a "hang" is usually the other client.
- A git worktree has its own server (its own directory). Commands in a worktree and in the main
  checkout run in parallel; two commands in one checkout do not.
- Never `pkill` by pattern: it is machine-wide and kills other sessions' servers. Stop the server
  with `sbt --client shutdown` in its directory.
- `sbt --client` does not pass the shell's environment or `-D` options to the server. A flag the
  build must read goes in a file. For the engine's debug flags that file is
  `.balticporter/debug.properties` (see
  [Debugging a port](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/debugging.md)).
- Shut down every server you started when you are done (`sbt --client shutdown` in each directory).
  Idle worktree servers outlive the session and exhaust the machine's memory.

## 2. Project ids and command strings

- Ask the build: `sbt --client projects`. Matrix rows are `<id>` (JVM), `<id>JS` and `<id>Native`,
  for example `sge`, `sgeJS`, `sgeNative`. There is no `sgeJVM`.
- Pass ONE quoted string, with tasks joined by `;`. Two arguments (`sbt --client "a" "b"`) are joined
  into one command line and fail with `Expected whitespace character` or `Expected ID character`.
- A hyphenated project id needs backticks only inside `build.sbt`, never on the command line.

## 3. The version is the git hash at server load

These builds version themselves from git when the build loads. After a commit, `publishLocal`
without `reload` publishes the new code under the old version. Always run
`sbt --client "reload; publishLocal"` and read the `published …/<version>/…` line. A docs-only commit
also moves the version. Locally published artifacts land in `~/.ivy2/local/com.kubuszok/<artifact>_3/`.

This matters when one consumer pins another's locally published artifact (sge pins lls's `lls-port`
at the lls version).

## 4. The action cache goes stale: move it aside, never delete blindly

The action cache is `~/Library/Caches/sbt/v2/ac` on macOS (`~/.cache/sbt/v2/ac` on Linux). Beside it,
`cas` is the content store and can be tens of GB. When a task "did nothing", a test passes on stale
classes, or `[error] … not found` appears after a clean tree, run
`mv ~/Library/Caches/sbt/v2/ac ~/Library/Caches/sbt/v2/ac.stale-$(date +%F)` and rerun. Never wipe the
whole `~/Library/Caches/sbt`: it cold-starts every other agent on the machine (the guard hook blocks
`rm -rf` on it).

Test totals that vary between runs are sbt 2 skipping unchanged suites, not a regression. Read the
failure line, not the total. sbt 2.1 prints the summary as `passed: total N, …` and `failed: total
N, …` (sbt 2.0 printed `Passed: Total` / `Failed: Total`); a script or CI guard that greps for it
should accept both, e.g. `[Pp]assed: [Tt]otal [1-9]`.

## 5. The JDK is an input

- The generated code depends on the JDK major that ran the generation: a member gets `override` only
  where that JDK's supertype declares it. sge, ssg and lls run the server on JDK 25 (their CI's
  `setup-scala` default). Check the repository's `CLAUDE.md` / `AGENTS.md` and
  `.github/actions/setup-scala/action.yml`.
- In every shell: `export JAVA_HOME=$(cs java-home --jvm <id>); export PATH=$JAVA_HOME/bin:$PATH`.
- On macOS, `/usr/libexec/java_home -v <N>` silently answers another JDK when N is not registered
  there. Check `java -version` and point `JAVA_HOME` at the real install.
- The JDK a server runs on is fixed when it starts: `sbt --client shutdown`, then start again.
- `overrides nothing` errors in generated code are a JDK mismatch until proven otherwise.

## 6. Multi-command steps are aliases in build.sbt, never YAML

A step that runs several commands is an sbt alias in `build.sbt`: sge has `generatePort`,
`testCompile-{jvm,js,native}-3`, `ci-jvm-3`, `test-js-3`, `test-native-3`, `verifyLocal`. A
`\`-continued `sbt '…'` in YAML fails with `Not a valid command: \`. A new step is a new alias plus
one YAML line. On CI, sbt runs in the foreground (`--server`), not through the client; see
`baltic-porter-ci-caching`.

## 7. The generated tree and its marker

- Each consumer regenerates when the generator's `.generated-marker` file does not match the current
  inputs: the engine pin, the upstream commit, the generator source, the JDK major, and (where the
  generator hashes them) the port's policy files. sge: `target/balticporter-sge/.generated-marker`,
  lls: `target/balticporter-lls/.generated-marker`; `project/BalticPorterGen.scala` names the others.
  A new pin or a JDK change regenerates by itself after `reload`. Delete the marker only to force a
  regeneration.
- sge's policy Scala (`sge-port/src/main/scala`) is compiled into the meta-build, so after editing it
  the generator refuses until `reload`.
- The log says which tree a command compiled. Grep for `[Baltic Porter] Using cached …` or
  `[Baltic Porter] Generated …` before reading errors.
- `sbt --client generatePort` runs the generation alone.
- Parallel matrix rows share one generation (the generator is `synchronized`).

## 8. Long runs

- `tee` every long command into a scratch file (`… 2>&1 | tee $SCRATCH/<what>.log | grep …`). The
  terminal shows a few lines; the log is what you read back.
- Over about 10 minutes: run it in the background and wait for the completion notification. A
  harness may kill a foreground process tree when the call ends (exit 137). Never `sleep`-poll or loop
  on `ps` / `tail`.
- Scalafmt-on-compile can rewrite files during a build. Run `git status` after a run and re-read any
  file the build reformatted before editing it.

## 9. When the server misbehaves

`sbt server disconnected`, `failed to connect to server`, `Connection refused; starting a new server`:
another client was killed mid-command or the server died. Run `sbt --client shutdown` in that
checkout, confirm with `pgrep -fl sbt-launch` and the PID's working directory
(`lsof -p <pid> | grep cwd`), `kill` that one PID if it survived, and rerun.
