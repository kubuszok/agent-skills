---
name: baltic-porter-ci-caching
description: >-
  How GitHub Actions CI is structured and cached in repositories that generate Scala with Baltic
  Porter (sge, ssg, lls): one `generate` job with the upstream submodule, one `compile` job per
  platform row, everything else restoring; the kubuszok/balticporter/.github/actions/generated-port
  action and its cache key (key-extra, the 512-character limit, fail-on-cache-miss); the sbt 2 remote
  cache (BuildBuddy, BUILDBUDDY_API_KEY, per-OS namespaces); why sbt runs with --server on a runner;
  what is never cached (per-job dependency caches, nativeConfig, scaladoc with the remote cache on).
  Use when adding or changing a CI job or workflow in such a repository, when a job is slow or
  repeats work another job did, when touching a cache key, when a job fails with a missing or stale
  generated tree, and before adding a setup step to a workflow.
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# CI and caching in a Baltic Porter consumer

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
The general CI and release workflows of an sbt-kubuszok build (scalafmt check, `ci-*` matrix,
`ci-release`, GPG and Central secrets) are covered by the `sbt-kubuszok-github-actions` skill of the
`sbt-kubuszok` plugin. This skill adds what generated code changes.

## The shape

```
wave 0   format · covenant gate · plugin tests            need nothing from the generator
         generate                                         the ONLY job with the upstream submodule
wave 1   compile (jvm | js | native)                      every module compiled once, on Linux
wave 2   tests · links · integration tests · scaladoc     restore, then only link and run
release  publish snapshot → demos against that snapshot   demos.yml (reusable workflow)
```

Rules that keep it that way:

1. **One job generates.** Only `generate` initialises the submodule, needs full git history and runs
   Baltic Porter. Every other job restores the tree. A job that adds `git submodule update` or a
   generation step is wrong: give it `needs: [generate]` and the repository's `generated-port` action
   in `restore` mode.
2. **One job per platform row compiles.** Downstream jobs `needs: [compile]` and get the outputs from
   the remote cache. Compiling needs no clang, Node or display; linking and running do, so only those
   jobs install them (`setup-native-toolchain`, `setup-js`, `setup-gl-xvfb` in sge).
3. **Nothing resolves the engine from a checkout.** The engine is the artifact pinned in
   `project/plugins.sbt`; the port's policy and injected files are in this repository.
4. **No step is written twice.** A step two jobs share is a composite action under
   `.github/actions/`; a job group two workflows share is a reusable workflow (`workflow_call`).
   Versions (JDK, Node) are input defaults of `setup-scala` / `setup-js`, nowhere else.
5. **Commands are sbt aliases**, never multi-line YAML: `generatePort`, `testCompile-<row>-3`,
   `ci-<row>-3`, `test-<row>-3`, `verifyLocal`. sge's `ci-*` aliases drop the leading `clean` that
   sbt-kubuszok's `ci` command starts with, because `clean` deletes `target/balticporter-*`, the
   generated tree.
6. **Demos consume published artifacts.** `release.yml` publishes the snapshot and then calls
   `demos.yml` with its version; the demos resolve it from Maven Central's snapshot repository. Only
   a fork PR (nothing is published for it) publishes locally, from `ci.yml`. Since sbt 2.1 a snapshot
   is published with timestamped file names only, so a job waiting for it looks for the version's
   `maven-metadata.xml`, not `<artifact>-<version>.pom`.

## The two caches, and what each is for

| | Actions cache (`actions/cache`) | sbt 2 remote cache (BuildBuddy, Bazel gRPC) |
|---|---|---|
| holds | the generated tree `target/balticporter-<module>` | compile outputs, by input hash |
| key | engine pin · upstream commit the checkout records · generator source · JDK major · `key-extra` (the port's own policy files) | computed by sbt per task |
| written by | `generate` (and `release.yml`'s publish job), once per distinct key | every job that has the API key |
| shared across | jobs, workflows and re-runs of the same ref; a PR also reads the base branch's entries | jobs of the SAME OS × arch × (ci or dev) namespace |
| miss | `restore` mode fails the job: `generate` did not run or the key inputs changed mid-run | the task simply runs |

- The generated-tree key is computed by
  [`kubuszok/balticporter/.github/actions/generated-port`](https://github.com/kubuszok/balticporter/blob/master/.github/actions/generated-port/action.yml)
  (inputs `mode`, `key`, `path`, `submodule`, `command`, `pin-file`, `generator`, `key-extra`; output
  `key`). Each consumer wraps it in a local action that pins its version (a commit hash) in ONE
  place. Downstream jobs take the key from `needs.generate.outputs.key`; they cannot compute it
  (shallow checkout, no submodule).
- An Actions cache key is limited to 512 characters. Every further upstream commit and builder hash
  a consumer adds goes into `key-extra`, already reduced to a short string (e.g. a `hashFiles(…)`
  digest). A consumer that composes its own key folds it the same way (ssg's key failed validation
  at seven upstream commits).
- The generator's own `.generated-marker` repeats the inputs it can read without the submodule. A
  restored tree whose marker does not match is refused with the reason; it is never silently
  regenerated or silently reused.
- **The JDK major is part of both.** The generated code differs by JDK (a member gets `override`
  only where that JDK's supertype declares it), so generate and compile on the same major.

## What is never cached

- `~/.cache/sbt/v2` through `actions/cache`: the remote cache supersedes it, and per-OS keys made it
  worse.
- Dependencies per job (`coursier/cache-action`, setup-java's `cache: sbt`): every job saves its own
  1–2 GB entry, a repository has 10 GB, and eviction is least-recently-used — one run pushed the
  12 MB generated-port entry out and the next job failed on `fail-on-cache-miss`. Before adding ANY
  cache, check `gh api repos/<owner>/<repo>/actions/cache/usage` and the size of what it would save.
- Native toolchain tasks (`nativeConfig`, discovered clang paths): machine-specific outputs poisoned
  other operating systems once; they are `Def.uncached`, and the remote cache is namespaced per OS.
- Scaladoc with the remote cache on: sbt 2 replays a cached *failure*, and scaladoc crashes
  nondeterministically. sge's doc job restores compile outputs with the cache on, then runs `doc`
  with `SGE_REMOTE_CACHE=off` and one retry with the local action cache purged.
- A tagged release: built from source, remote cache off.
- Fork PRs have no secrets: the remote cache is off and nothing is published; everything still works.

## On a runner, sbt runs in the foreground

For an sbt 2 build the `sbt` launcher defaults to a thin client that starts a background server
(locally that is what you want: `sbt --client`). On a runner it is wrong:

- the server keeps the environment of the step that started it, so a later step's `env:` never
  reaches the build — Sonatype credentials on a publish step after a generation step ("Unable to
  find credentials"), `SGE_REMOTE_CACHE=off` on a doc step after a compile step;
- in bash on Windows the client cannot start the server at all (`Cannot run program "C:/Program
  Files"`).

The consumers' `setup-scala` action therefore puts a wrapper first on the `PATH` that calls the real
launcher with `--server` (one JVM per call, no state between steps). Never install sbt in a workflow
any other way, and never add `--client` there.

## Measured (sge, the same commit content before and after the restructuring)

| | before | after |
|---|---|---|
| runner time, CI + release workflows | 276 min | 168 min (−39 %) |
| jobs that run Baltic Porter | 17 | 1 (66 s on a cache hit, ~4–5 min on a miss) |
| jobs that check out the engine / the submodule | 18 / 16 | 0 / 1 |
| compile of the three platform rows | inside every job | 3 parallel jobs, 3.5–4 min each |
| demos | built 5× from locally published artifacts, ~47 runner-min | against the published snapshot, ~20 runner-min |
| CI wall clock | 24.6 min | 26.6 min |
| lls: runner time / longest job | 85 min / 27.5 min | 56 min / 13.7 min |

The wall clock did NOT improve: the critical path is `generate` → `compile` → the slowest non-Linux
Native row (Windows 17 min, macOS 16.5 min), and those rows still compile everything themselves
because the remote cache is namespaced per OS. Sharing platform-independent compile outputs across
operating systems is the open lever; it needs an experiment that proves it cannot poison a cache
first.

## Reading a run

- Wall clock and runner minutes: `gh run view <id> --json jobs --jq '.jobs[] | [.name, .conclusion,
  ((.completedAt|fromdate)-(.startedAt|fromdate))] | @tsv'`.
- Did generation run? The `generate` job's restore step says whether the cache hit; a hit skips the
  submodule and the generation entirely.
- Did a job recompile? Its sbt log prints `compiling N Scala sources` for a module `compile` already
  built only on a remote-cache miss. Then check the job ran on the same OS/arch namespace and that
  `BUILDBUDDY_API_KEY` reached it (a reusable workflow needs it passed under `secrets:`).
- sbt 2.1 prints the test summary as `passed: total N` / `failed: total N`; a guard that greps for
  the sbt 2.0 spelling (`Passed: Total`) misses it. Use `[Pp]assed: [Tt]otal [1-9]`.
- After a push: ONE `gh run watch <id> --exit-status` in the background; read every red job before
  changing anything; re-run a flake with `gh run rerun <id> --failed`, never an empty commit.

## Before changing CI

Lint locally with `actionlint`. A workflow change cannot be tested locally beyond that, so batch CI
edits into ONE push, and keep every sbt-level piece (aliases, the generator, the marker) verifiable
with `sbt --client`, which IS testable locally: a lone clone with no sibling directories must
`generatePort` and test-compile.
