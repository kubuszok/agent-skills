---
name: sbt-kubuszok-github-actions
description: >-
  GitHub Actions workflows for a Scala project built with the sbt-kubuszok plugin: ci.yml (scalafmt --check job, build
  matrix over scala 2_13/3 x platform jvm/js/native running `sbt ci-<platform>-<scala>` aliases, JDK pinning,
  coverage) and release.yml (`sbt ci-release` publishing SNAPSHOTs from master and releases from git tags to Maven
  Central, GPG import with crazy-max/ghaction-import-gpg, SONATYPE_USERNAME / SONATYPE_PASSWORD, GPG_PRIVATE_KEY /
  GPG_PASSPHRASE secrets, fetch-depth: 0, PR snapshots guarded to trusted authors via author_association), testing a
  change from a PR snapshot in another repo, the tag-based release procedure, Scala Steward / Dependabot interplay.
  Use when creating or editing .github/workflows in a repo whose project/plugins.sbt has sbt-kubuszok, when a
  snapshot/release publish job fails, or before tagging a release.
license: Apache-2.0
metadata:
  library: sbt-kubuszok
  library-version: "0.2.6"
---

# GitHub Actions for sbt-kubuszok projects

The plugin decides **what** a run publishes from git alone. A tag on HEAD makes it a release. Without a tag the run
publishes `<tag>-<n>-g<sha>-SNAPSHOT`. So the workflows stay short: a CI workflow that runs the generated `ci-*`
aliases, and a release workflow that runs `sbt ci-release` on every master push and every tag. Do not add version
computation, `publishTo` logic or `sonatypeBundleRelease` steps.

Version: written for sbt-kubuszok **0.2.6**. Check `project/plugins.sbt`; on other versions compare with
<https://github.com/kubuszok/sbt-kubuszok/blob/0.2.6/src/main/scala/kubuszok/sbt/KubuszokPlugin.scala> and the
plugin's own workflows. Build setup (aliases, `projectType`) is in `sbt-kubuszok-setup`. Error texts are in
`sbt-kubuszok-troubleshooting`.

## Rules (each one broke a real repo)

1. **`actions/checkout` with `fetch-depth: 0`** in the release job (required) and in jobs that depend on the version
   (MiMa, version printing); recommended in every job that runs sbt. Without the full history and tags,
   `git describe` fails and snapshots are versioned `<sha>-SNAPSHOT`, which does not sort. The tag/release logic
   also loses its input.
2. **Run release.yml on `push` to master, on tags, and on `pull_request` guarded to trusted authors.** Publishing
   snapshots from PRs is the intended workflow: other repos (or the maintainer) test a change from its PR snapshot
   before merging and releasing. The job must carry the trusted-author `if:` guard from the template
   (`author_association` in `OWNER`/`MEMBER`/`COLLABORATOR`). Without the guard, Dependabot, Scala Steward and fork
   PRs, which get no secrets, fail with `Input required and not supplied: gpg_private_key`. A bare `pull_request`
   trigger without the guard is the bug, not the trigger itself. Do not remove the trigger "to be safe".
3. **Import the GPG key with `crazy-max/ghaction-import-gpg`** before sbt. sbt-pgp signs with the `gpg` binary. The
   `PGP_SECRET`/`PGP_PASSPHRASE` env vars of sbt-ci-release do nothing here and end in
   `gpg: signing failed: No secret key`.
4. **Pass `SONATYPE_USERNAME` / `SONATYPE_PASSWORD`** (a Central Portal user token) as env of the `sbt ci-release`
   step. sbt's built-in Central publishing reads them. No `credentials` file is needed.
5. **Run `sbt ci-release`, nothing else.** It already does `+publishSigned` (every cross axis), plus `sonaRelease`
   on a tag. Hand-written `publishSigned ; sonaRelease` lists miss `+`, modules or the release step. In older repos,
   a green tag run published nothing because the alias never called `sonaRelease`.
6. **Pin the JDK** in `coursier/setup-action` (`jvm: 'temurin:1.17.0.15'`). Its default moves (to 25 at the time of
   writing), and Scala 2.13.16 cannot read JDK 25 class files. sbt 2 needs JDK 17+. sbt 1.x builds may release on 11.
7. **Pass several sbt commands as one argument** (`sbt "a ; b"`). sbt 2 joins separate program arguments into one
   line, and `sbt a b` fails with `Expected ';'` (or `Expected '/'`, depending on the commands).
10. **On sbt 2, run sbt in the foreground on CI: `sbt --server ...`.** sbt 2's launcher defaults to a thin client
    that starts a background server. On a runner the server keeps the environment of the step that started it (a
    later step's `SONATYPE_*` never reach it), it cannot start from bash on Windows, and runs can fail with
    `failed to connect to server`. kubuszok repos (lls, sge, ssg) put a wrapper that adds `--server` first on `PATH`
    in their setup action (template in [workflows.md](workflows.md)).
11. **The release job needs every pre-step CI has**: source generation, Node/npm for bundled assets, native
    toolchains or downloaded native libraries. `ci-release` compiles and packages everything again from a clean
    checkout.
8. **Check formatting with the `scalafmt` CLI** (`scalafmt --check`). It covers every file `.scalafmt.conf` matches.
   `sbt "scalafmtCheckAll ; scalafmtSbtCheck"` covers the projects' sources, `build.sbt` and `project/*.scala`, but
   misses other meta-build source directories and docs. `scalafmtOnCompile` is off on CI (`CI=true`), so unformatted code only shows up
   here. Format the whole repo in the adoption PR.
9. **Do not use `cancel-in-progress` in release.yml.** Cancelling a publish halfway leaves a partial snapshot or
   staging upload. CI may use it.

## Required secrets

| Secret | Used by |
|---|---|
| `GPG_PRIVATE_KEY` | `crazy-max/ghaction-import-gpg` `gpg_private_key` (ASCII-armored private key) |
| `GPG_PASSPHRASE` | same action, `passphrase` |
| `SONATYPE_USERNAME` | env of `sbt ci-release` (Central Portal token user) |
| `SONATYPE_PASSWORD` | env of `sbt ci-release` (Central Portal token password) |
| `CODECOV_TOKEN` | optional, `codecov/codecov-action` |

Repos in the `kubuszok` organization use organization-level secrets. A repo in another account needs them added
there. Ask the maintainer and never put values in the workflow.

## Workflows

Copy-ready `ci.yml` and `release.yml` (plus variants: release gated on CI, nested builds,
bigger release heap) are in [workflows.md](workflows.md). In short:

- **ci.yml**: a `check-formatting` job (`scalafmt --check`), and a `build` job with a matrix
  `scala: ['2_13','3'] x platform: ['jvm','js','native']` (exclude the cells your build does not have) that runs
  `sbt ci-${{ matrix.platform }}-${{ matrix.scala }}`. The matrix values must match the alias names the build
  registers (`ci-jvm-2_13`, `ci-native-3`, ...). Old CI that called pre-matrix project ids (`sbt core3/test`) breaks
  after migration.
- **release.yml**: triggers on master pushes, tags and trusted-author PRs (guarded job), then checkout
  (fetch-depth 0), coursier cache, GPG import, setup JDK and sbt, and `sbt ci-release` with the Sonatype env.

## Release procedure

1. Merge to master and wait for the **snapshot** publish on that push to succeed. It exercises signing, Scaladoc for
   every cell, and POM validation for snapshots.
2. Make sure no dependency is a `-SNAPSHOT`. `checkNoSnapshotDeps` fails a tagged build with
   `Refusing to publish releasable version X: it depends on SNAPSHOT modules`. Release upstream first, then bump.
3. Tag the master commit with a bare version and push it: `git tag 1.2.3 && git push origin 1.2.3`. kubuszok repos
   use bare tags. sbt-git would also accept `v1.2.3`, but **any** tag on HEAD makes `ci-release` call `sonaRelease`,
   so never put non-version tags on master commits.
4. The tag push triggers release.yml, which runs `+publishSigned` into `localStaging` and then `sonaRelease` uploads
   and releases the bundle.
5. After the run succeeds and the artifacts are on Central, create the GitHub release for the tag with notes
   (kubuszok repos publish one per version; the tag alone is not enough):
   `gh release create 1.2.3 --verify-tag --latest --title 1.2.3 --notes "..."`. Summarize user-visible changes and
   upgrade steps since the previous tag (`git log --oneline <previous-tag>..1.2.3`).
6. If the tag run failed **before** `sonaRelease` uploaded anything (compile, doc, OOM, SNAPSHOT guard), fix it on
   master, move the tag (`git tag -f 1.2.3 <fixed-sha> && git push -f origin 1.2.3`) and let it re-run. If the
   version already reached Central, it cannot be re-published: release the next patch version.

## Testing a change from a PR snapshot

1. Open the PR from a branch of the repo itself (not a fork) as a trusted author. The guarded release job publishes
   `<last-tag>-<n>-g<sha>-SNAPSHOT`, where `<sha>` is GitHub's PR **merge commit**, not the branch head. Read the
   exact version from the job log (`gh run view <id> --log | grep -o '[^/ ]*-SNAPSHOT' | sort -u`) or compute it with
   `git fetch origin refs/pull/<n>/merge && git describe --tags FETCH_HEAD`. Every push to the PR publishes a new one.
2. In the consuming repo, add the snapshot repository and the version. For a library dependency, the plugin already
   adds the resolver. For an sbt plugin, add it in `project/plugins.sbt`, because the resolver only exists once the
   plugin is loaded:
   ```scala
   resolvers += "Maven Central Snapshots" at "https://central.sonatype.com/repository/maven-snapshots" // TODO: remove after release
   addSbtPlugin("com.kubuszok" % "sbt-my-plugin" % "1.2.3-4-gabcdef1-SNAPSHOT")
   ```
3. Open a PR in the consumer and let its CI run. After the release, turn the same PR into the version bump: set the
   released version and drop the resolver. Never release a consumer while it still points at a snapshot;
   `checkNoSnapshotDeps` refuses it anyway.

## Scala Steward and Dependabot

kubuszok repos manage Scala compiler versions by hand. `updates.pin` does not hold a Scala LTS line (Steward unifies
it with a newer Scala 3 present in the build), and per-artifact ignores miss platform-suffixed artifacts, so the
whole group is ignored:

```hocon
updates.ignore = [ { groupId = "org.scala-lang" } ]
updates.pin = [
  # only for repos that stay on sbt 1.x
  { groupId = "org.scala-sbt", artifactId = "sbt", version = "1." }
]
pullRequests.grouping = [
  { name = "scala-versions", title = "Scala compiler updates", filter = [{ group = "org.scala-lang" }, { group = "org.scoverage" }] }
]
```

Also ignore hand-pinned `-SNAPSHOT` dependencies of your own libraries.

- Scala Steward bumps `sbt.version` and `sbt-kubuszok` separately. Those PRs fail until both are compatible (see the
  version table in `sbt-kubuszok-setup`). Merge them together, or push the missing bump onto the Steward PR.
- Repos that stay on sbt 1.x (to keep releasing on JDK 11, or because they are themselves sbt 1 meta-builds) pin it:
  `updates.pin = [{ groupId = "org.scala-sbt", artifactId = "sbt", version = "1." }]` in `.scala-steward.conf`.
- Dependabot for `github-actions` (`.github/dependabot.yml`, weekly) keeps `actions/checkout`, `coursier/*` and
  `crazy-max/ghaction-import-gpg` current. Its PRs have no secrets, which is why the release job needs the
  trusted-author guard.

## Gotchas

- **The release job does more than CI.** `ci-*` runs clean/compile/test (plus coverage on JVM) and `doc` for the
  published modules of its cell. `ci-release` builds, documents, packages and signs **every** matrix cell in one JVM.
  Typical first-release failures:
  - `OutOfMemoryError: Java heap space` in `Compile / doc`. Give the release step more heap (variant in
    workflows.md).
  - Scaladoc errors in a cell CI does not run, or in a build whose `Aliases` sets `docInCi = false` or whose aliases
    are hand-written. Run `sbt +publishLocal` before tagging.
- **Release does not wait for CI.** Snapshots of a red commit still get published. If that matters, gate it (variant
  in workflows.md).
- **429s in setup steps** (`Error downloading ... latest.stable` while installing scalafmt/scala-cli/sbt) come from
  unpinned, uncached `coursier/setup-action` apps: pin the tool versions and cache every job (workflows.md, "Pin tool
  versions").
- **Transient Central errors** on snapshot upload (`HTTP response code: 429`, `Connection is closed`) are rate limits.
  Re-run the job; they are not configuration errors.
- **Nested sbt builds** (for example a build plugin in `my-build/` with its own `project/`) need their own
  `sbt ci-release` step with `working-directory`.
