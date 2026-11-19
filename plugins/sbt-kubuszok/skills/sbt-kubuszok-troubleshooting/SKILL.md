---
name: sbt-kubuszok-troubleshooting
description: >-
  Diagnosing failed builds and failed snapshot/release publishing in projects using the sbt-kubuszok sbt plugin:
  IncompatiblePluginsException / NoClassDefFoundError IvyActions$ after an sbt bump, "Input required and not
  supplied: gpg_private_key", "gpg: signing failed: No secret key", "Refusing to publish releasable version ... depends
  on SNAPSHOT modules", "Expected ';'", "failed to connect to server", test-interface (strict) eviction, "Scala version mismatch ... allowMismatchScala", "Build not configured to use
  exactly 1 platform", "No tests to run" on sbt 2, scaladoc errors and OutOfMemoryError only in the release job,
  modules silently not published, wrong SNAPSHOT versions (<sha>-SNAPSHOT), scalafmt check failures, allowUnsafeScalaLibUpgrade.
  Use when a CI or "Sonatype Release" GitHub Actions run fails in a repo whose project/plugins.sbt has sbt-kubuszok,
  or when the first release after adopting the plugin goes wrong.
license: Apache-2.0
metadata:
  library: sbt-kubuszok
  library-version: "0.2.6"
---

# Troubleshooting sbt-kubuszok builds and publishing

This catalogue was collected from the first CI and publish runs of 13 repositories that adopted the plugin. Each
entry gives the symptom, the cause and the fix. For the correct setup from scratch, see `sbt-kubuszok-setup` and
`sbt-kubuszok-github-actions`.

Version: written for sbt-kubuszok **0.2.6**. Check `project/plugins.sbt`. Behaviour referenced here lives in
<https://github.com/kubuszok/sbt-kubuszok/tree/0.2.6/src/main/scala>. Several entries below are fixed by upgrading
from 0.2.4 to 0.2.6 and deleting the workaround.

First, work out which job failed. The `build` job of ci.yml runs `sbt ci-<platform>-<scala>`. The **Sonatype
Release** job runs `sbt ci-release`, which also runs Scaladoc, packaging, signing and upload for every cell, so it
can fail when CI was green. Read the log with `gh run view <id> --log-failed`.

## Build does not load

**`sbt.internal.IncompatiblePluginsException: Binary incompatibility in plugins detected`** /
**`NoClassDefFoundError: sbt/internal/librarymanagement/IvyActions$`**
- Cause: the sbt version and the sbt-kubuszok version do not match. This typically happens when a Scala Steward PR
  bumped `sbt.version` to 2.1.x while sbt-kubuszok stayed on 0.2.3, whose bundled sbt-pgp breaks on sbt 2.1. It also
  happens when the build re-adds a bundled plugin at another version in `plugins.sbt`.
- Fix: use sbt 2.1.x with 0.2.4+ (0.2.6), sbt 2.0.x with 0.2.3, or sbt ≥ 1.11 with 0.2.6. Bump both in one commit. Remove
  bundled plugins from `plugins.sbt`.

**`Build not configured to use exactly 1 platform, ide.platform must be jvm, js, or native`** (or the `ide.scala`
variant: `Unsupported ide.scala=... in dev.properties, it must be 2.13 or 3`)
- Cause: `DevProperties` found no `dev.properties` (or no matching key) in a build with several platforms.
- Fix: commit a default `dev.properties` with `ide.scala` and `ide.platform` (see `sbt-kubuszok-setup`).

**NPE or "Reference to undefined setting" at load after restructuring**
- Cause: a `projectMatrix` defined with `val` instead of `lazy val` and referenced before its definition (by `Aliases`
  or `aggregate`), or a self-referencing setting such as `doc / sources := (doc / sources).value ...` at
  `ThisBuild`.
- Fix: use `lazy val` for all matrices and for `al`, and define settings at project scope.

**Errors mentioning `allowUnsafeScalaLibUpgrade`, or a scala-library version conflict right after adoption**
- Cause: the bundled Scala.js/Scala Native (or a dependency) needs a newer `scala-library` 2.13 patch than the build's
  `scalaVersion`. sbt ≥ 1.11 refuses to upgrade the standard library silently.
- Fix (preferred): raise the 2.13 version to the current patch. Otherwise set
  `Global / allowUnsafeScalaLibUpgrade := true`, which kubuszok builds use when a dependency was built with a
  newer 2.13.

**`not found: value logo` / `usefulTasks` / `object sbtwelcome is not a member`** on sbt 2
- Cause: sbt-welcome is not bundled for sbt 2.
- Fix: drop them and register the aliases with `al.commandAliases(...)` (template in `sbt-kubuszok-setup`).

## CI job fails

**`Not a valid command: ci-jvm-3`** (or `publish-local-for-tests`)
- Cause: the aliases were never registered. Add `.settings(al.commandAliases(...))` on root (or, on sbt 1,
  `usefulTasks := al.usefulTasks(...)`). Another cause is a CI matrix cell that has no projects (for example `2_13`
  while the build is Scala 3 only); `commandAliases` registers only existing combinations.
- Fix: register the aliases, and make the matrix match the cells that exist.

**`Not a valid project ID: core3`** (or similar) in an old CI command
- Cause: the CI still calls project ids from before the projectmatrix migration.
- Fix: replace the command with `sbt ci-${{ matrix.platform }}-${{ matrix.scala }}`.

**"Check formatting" fails** right after adoption
- Cause: `scalafmtOnCompile` formats only locally (it is off when `CI=true`), and it never formats `build.sbt` or
  `project/*.scala`. CI's `scalafmt --check` covers all of them.
- Fix: run `scalafmt` (CLI) or `sbt "scalafmtAll ; scalafmtSbt"` and commit the result. Repeat after widening root
  aggregation.

**Green CI, but no tests ran** (`No tests to run`) on sbt 2
- Cause: sbt 2's `test` is incremental and cached. sbt-kubuszok ≤ 0.2.4 `Aliases` emitted `<id>/test`, or the
  aliases are hand-written with `/test`.
- Fix: upgrade to 0.2.6, whose `Aliases` emit `<id>/testFull` on sbt 2, and delete `fullTests`-style rewriting.

**`FileNotFoundException: .../scoverage-data/scoverage.measurements.*`** in JVM `ci-*` on sbt 2 with `fork := true`
- Cause: the forked test JVM writes coverage measurements into a directory that does not exist yet.
- Fix: create `crossTarget.value / "scoverage-data"` in a `Test / compile` hook for forked modules, or do not fork
  those tests.

**IDE imports Scala 3 although `ide.scala = 2.13`**, or an NPE / `MatchError: null` from a custom `dev.properties` key
- Cause: sbt-kubuszok ≤ 0.2.4 ignored `ide.scala` when both 2.13 and 3 were built, and `dev.props.getProperty`
  returns `null` for a missing key.
- Fix: upgrade to 0.2.6 and read custom keys with `dev.prop("key")` (an `Option`).

**`found version conflict(s) in library dependencies ... org.scala-native:test-interface_native0.5_3:0.5.12 (strict) is selected over 0.5.8`**
on a Scala Native project
- Cause: Scala Native artifacts use the `strict` version scheme. A test library that exports an older
  `test-interface` transitively conflicts with the bundled Scala Native 0.5.12: munit ≤ 1.3.0 (1.3.1+ scopes it to
  `test`), scalacheck 1.19.
- Fix: munit ≥ 1.3.1 (≥ 1.3.3 matches 0.5.12). For other libraries, relax eviction on the Native platform only:
  `MatrixAction.ForPlatforms(VirtualAxis.native).Configure(_.settings(evictionErrorLevel := sbt.util.Level.Warn))`
  passed to `someVariations` (as kubuszok/pipez does).

**`failed to connect to server`** (sbt 2 on GitHub Actions), or credentials/env not visible to sbt in a later step
- Cause: sbt 2's launcher runs a thin client with a background server, which keeps the first step's environment.
- Fix: run `sbt --server ...` (PATH wrapper in `sbt-kubuszok-github-actions`).

**Version is a timestamp (`20261118T202211`) or tags are ignored locally**
- Cause: the build runs in a `git worktree` on sbt-kubuszok 0.2.5 or older; sbt-git's JGit cannot read it.
- Fix: upgrade to 0.2.6, which reads worktrees through the `git` CLI. Remove any hand-set `useConsoleForROGit`.

## Release / snapshot job fails

**`##[error]Input required and not supplied: gpg_private_key`** at "Import GPG key"
- Cause: release.yml runs on `pull_request` without the trusted-author guard, and Dependabot, Scala Steward and fork
  PRs get no secrets.
- Fix: add the trusted-author `if:` guard from `sbt-kubuszok-github-actions`. Keep the `pull_request` trigger: PR
  snapshots from trusted authors are intended.

**`gpg: signing failed: No secret key`** / `Failure running 'gpg --batch ... --detach-sign'`
- Cause: the key was never imported into gpg. A common reason is that the workflow passes sbt-ci-release-style
  `PGP_SECRET`/`PGP_PASSPHRASE` env vars.
- Fix: add a `crazy-max/ghaction-import-gpg@v7` step with `GPG_PRIVATE_KEY` / `GPG_PASSPHRASE` before `sbt ci-release`.

**401/403 from `central.sonatype.com`**
- Cause: `SONATYPE_USERNAME`/`SONATYPE_PASSWORD` are missing from the step's `env`, or they hold the account login
  instead of a Central Portal user token. The namespace (for example `com.kubuszok`) may also not be verified for
  that account.
- Fix: correct the secrets and the env mapping.

**`Refusing to publish releasable version 1.2.3: it depends on SNAPSHOT modules: ...`**
- Cause: `checkNoSnapshotDeps` found a `-SNAPSHOT` dependency (possibly transitive) in a tagged build.
- Fix: release that dependency, pin its final version, then move the tag. This is safe because nothing was uploaded.

**`Scala version mismatch: tests (Scala X) depends on compat (Scala Y). To allow this, set ThisProject / allowMismatchScala := true`**
- Cause: `ci-release` cross-publishes with `+`, which visits every aggregated project's `crossScalaVersions`. That
  includes NonPublished test modules whose versions are a superset of what their dependency declares.
- Fix: keep a test module's `crossScalaVersions` within those of its dependencies, set
  `allowMismatchScala := true` on that test module, or remove it from root's aggregation.

**Scaladoc errors only in the release job** (`The link target "X" is ambiguous`, an unresolved `[[X]]` that is fatal
on 2.13)
- Cause: CI did not run `doc` for that cell: sbt-kubuszok ≤ 0.2.4 (whose `ci` had no `doc`), `docInCi = false`,
  hand-written aliases, or a cell missing from the CI matrix.
- Fix: fix the links. Upgrade to 0.2.6 (its `ci` runs `<id>/doc` for published modules), or run `sbt +publishLocal`
  before merging.

**`java.lang.OutOfMemoryError: Java heap space`** in `Compile / doc` during `ci-release`
- Cause: every cell is documented and packaged in one sbt JVM.
- Fix: raise `-Xmx` on the release runner (the `.jvmopts` variant in `sbt-kubuszok-github-actions`). Scaladoc NPEs on
  JDK 24/25 are a JDK and Scala problem: pin the JDK to 17.

**Release published without javadoc/sources JARs, or rejected by Central for them**
- Cause: `packageDoc / publishArtifact := false` / `packageSrc / publishArtifact := false` (often added to dodge a
  Scaladoc crash). Central's requirements list both JARs.
- Fix: remove it. For an intentionally empty doc JAR, use `Compile / doc / sources := Seq.empty`. For a Scaladoc NPE
  on JDK 24/25, see the JIT exclude in `sbt-kubuszok-github-actions`.

**`Expected ';'`** (or `Expected '/'`) at the start of the sbt step
- Cause: on sbt 2, `sbt "+publishSigned" sonaRelease` or `sbt testFull mima` (several arguments) is joined into one
  line.
- Fix: use `sbt ci-release`, or one argument `sbt "a ; b"`.

**`HTTP response code: 429`** or `Connection is closed` while uploading snapshots
- Cause: transient Central rate limiting.
- Fix: re-run the job. No configuration change is needed.

## Run is green but the result is wrong

**A module is missing from Central (snapshot or release)**
- Check `sbt "show <module>/publish/skip"`. If it is `true`, the module still has the default
  `projectType := NonPublished`; set `ScalaLibrary` or `JarOnly`.
- Check that root aggregates the module. `ci-release` runs from root.
- For sbt-plugin or `crossScalaVersions` modules, check that the build uses `ci-release`, which adds `+`, rather than
  a hand-written `publishSigned`.

**A tag run is green but nothing was released**
- Cause: a custom `ci-release` alias or command shadows the plugin's and never calls `sonaRelease`, or the checkout
  had no tags (missing `fetch-depth: 0`).
- Fix: delete the override and use the plugin's `ci-release`.

**Snapshot version is `<40-char-sha>-SNAPSHOT`** instead of `1.2.3-4-gabcdef1-SNAPSHOT`
- Cause: a shallow checkout with no tags, or a repo with no version tag yet.
- Fix: `fetch-depth: 0`. If the repo has no tag yet, this version is expected until the first release.

**Version is fixed (`0.1.0-SNAPSHOT`) or not from git**
- Cause: a leftover `version :=` / `ThisBuild / version :=`, or a `project.version` system property, which sbt-git
  honours as an override.
- Fix: remove the override.

**A non-version tag triggered a release**
- Cause: `ci-release` releases whenever HEAD has **any** tag.
- Fix: never tag master commits with non-version tags.

**A test module was published locally by `publish-local-for-tests`, or a published one was skipped**
- Cause: the `Aliases(published = ...)` lists do not match `projectType`.
- Fix: keep the two in sync.

## Reporting

If the plugin's behaviour differs from this skill at the pinned version, check the plugin source at the user's
version. Report the difference to <https://github.com/kubuszok/sbt-kubuszok/issues> rather than patching around it
in the build.
