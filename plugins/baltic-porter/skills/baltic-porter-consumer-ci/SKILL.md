---
name: baltic-porter-consumer-ci
description: >-
  Making a pull request green in a repository that generates Scala with Baltic Porter (sge, ssg,
  lls): the fix-everything-locally-then-push-once loop over the JVM, Scala.js, Scala Native and
  Android rows, the regenerate / testCompile / verifyLocal chain, target/local-verification and the
  push hook, the re-scale covenant gate and its `covenant-baseline-approved:` marker, generator inputs
  read from a branch instead of a commit, and the list of fixes that count as cheating (@Ignore,
  editing a test to the generated spelling, compile-only rows, growing a baseline). Use whenever a
  sge/ssg/lls CI job is red, before pushing to such a repository, and when a consumer file was patched
  to make generated code compile.
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# Consumer CI: the loop

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
Aliases and paths below are sge's; ssg and lls have the same shape (check their `build.sbt` for the
exact alias bodies).

CI is not the debugger. One push per cycle, every row green locally first.

## 1. The loop

1. Collect EVERY failing job: JVM, JS, Native, Android, `packageSrc`, scalafmt, the covenant gate,
   and the dependents that were cancelled. Read each log to its root cause and group by cause
   (`gh run view <id> --log-failed`).
2. Classify each cause:
   - an engine rule true of every library (fixed in the engine repository, then repinned);
   - this port's policy (a phase's configuration, a drop, an injected file);
   - a library-specific rule this repository plugs into the engine;
   - the consumer build (aliases, pins, markers);
   - drift that was already there before this change.
   The fix goes where the cause is, never into the generated tree. `baltic-porter-root-cause-port`
   is the procedure.
3. Fix ALL known causes, regenerate, run the whole chain below locally, then push. A red CI after
   that returns to step 1 for ALL failures — never a one-line patch and another push.

## 2. What counts as cheating (each was tried and reverted)

- `@Ignore` / `.ignore` on a test, deleting a test, an empty suite, `assert(true)`.
- Editing a test to the generated spelling (`same.getOrElse(null)`, a boxed `Float.valueOf`): the
  test is the reference; the generated spelling is wrong.
- Replacing `testFull` with `compile`, downgrading a JS/Native row to compile-only, skipping a module
  in an alias.
- Growing `.rescale/data/covenant-gate-baseline.tsv`; adding `@nowarn`, `null.asInstanceOf` or
  `.getOrElse(null)` to a hand-written file (the scanner counts them as `null-cast` and
  `get-or-else-null`).
- A JVM-only dependency (jackson, ANTLR, reflection) to make a row pass.
- Patching an extension to the generated core's spelling (`u_=` → `setU`, `compare` → `compareTo`).
  The fix is the derivation or policy that made the core diverge from the reference; then
  `git checkout <merge-base> -- <file>` puts the extension back.

## 3. The chain (sge; ssg and lls have the same shape)

```
# JDK 25 for the sbt server (see baltic-porter-sbt2-client)
# if the pin moved: edit project/plugins.sbt (every balticporter pin line) -> <hash>-SNAPSHOT
sbt --client "reload; generatePort"
sbt --client "testCompile-jvm-3"; sbt --client "testCompile-js-3"; sbt --client "testCompile-native-3"
git commit …
sbt --client "verifyLocal"   # scalafmtCheckAll; scalafmtSbtCheck; ci-jvm-3; test-js-3; test-native-3; markVerified
sbt --client "sge/Compile/packageSrc"
.rescale/scripts/covenant-gate.sh   # needs the re-scale CLI on the PATH
```

Run each command through `tee` (`baltic-porter-sbt2-client`). Rows fail in order: fix the first
row's root cause before reading the next; the same cause usually explains all three.

`verifyLocal` ends with `markVerified`, which refuses a dirty tree and writes the verified commit to
`target/local-verification`. The plugin's guard hook (Claude Code only) refuses `git push` in a
repository that has `project/BalticPorterGen.scala` until that file names HEAD. Commits that change
only `*.md`, `docs/`, `.github/`, `.claude/` or `.rescale/data/` since the verified commit are exempt.

A LOCAL engine pin is never pushed. The engine change is pushed to the engine's `master` once, its
snapshot release finishes, you prove it is published, repin to that hash, verify, push
(`baltic-porter-generated-code`, "Bumping the engine pin").

What CI does with it (sge): one `generate` job runs Baltic Porter and stores the tree in the Actions
cache; `compile` builds each platform row once into the sbt remote cache; every other job restores
both and only links and runs; the demos build against the snapshot `release.yml` publishes
(`baltic-porter-ci-caching`). After a push: ONE `gh run watch <id> --exit-status` in the background,
then read every red job before touching anything. Never poll, never re-push a one-line guess, never
an empty commit to retrigger: `gh run rerun <id> --failed`.

## 4. The generator and hand-written files

- sge's generator reads its hand-written replacements from `sge/src/main/scala` through
  `providedSources` (read for their surface, never copied). Never copy such a file into
  `sge-port/overrides/`; each replacement has one home. Read the repository's own `CLAUDE.md`
  "Generated Code" section for the current layout.
- Fatal findings that the generator downgrades to warnings are pre-existing dropped-type references
  the hand tree replaces. A NEW fatal kind is yours.
- **Every generator input is a fixed object, never a branch name.** A generator once read a
  hand-written reference tree from `master`. The pull request was green because `master` still held
  that tree; the merge removed it, and master's first CI run failed with hundreds of type mismatches
  naming no cause. Pin a reference tree by commit hash in the generator source (so it is part of the
  generated tree's cache key). **A pull request's green run proves nothing about the push run on the
  default branch when an input is read from that branch — after a merge, read the default branch's
  own run.**

## 5. The covenant gate (sge)

`.rescale/scripts/covenant-gate.sh` runs re-scale's `enforce` checks against the merge base. Growth
against the merge base — a new `(file, kind)` pair, a raised count, rows removed together with a
deleted file — needs a line `covenant-baseline-approved: <reason>` in EVERY commit that edits
`.rescale/data/covenant-gate-baseline.tsv` since the merge base. An uncommitted baseline edit can
never be approved. A `methods removed` line names methods the generated code lost against the
reference; each is a derivation or policy question first, and never a header edit.

## 6. What to report

Per row: the count before → after, the root cause per group, which repository fixed it, and the
residues left with their owner (pre-existing drift, open engine items). Never "green" without the
three rows' test totals.
