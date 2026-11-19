---
name: sbt-kubuszok-setup
description: >-
  Adding the sbt-kubuszok sbt plugin (addSbtPlugin("com.kubuszok" % "sbt-kubuszok" % ...)) to a Scala build, or
  migrating a build to it: which bundled plugins (sbt-git, sbt-scalafmt, sbt-scoverage, sbt-projectmatrix,
  sbt-commandmatrix, sbt-scalajs, sbt-scala-native, sbt-pgp, sbt-mima-plugin, sbt-ide-settings, sbt-welcome) and
  settings (publishTo, versionScheme, git versioning, ci-release, scalafmtOnCompile, Maven Central snapshots resolver)
  it already provides and must not be configured again, projectType (ScalaLibrary / JarOnly / NonPublished, default
  NonPublished), KubuszokRootPlugin, Aliases and al.commandAliases (ci-jvm-3, test-js-2_13, publish-local-for-tests,
  testFull, doc in ci), DevProperties, dev.properties and dev.prop, foldVersion, isCI, sbt 1.x vs sbt 2.x compatibility. Use when editing project/plugins.sbt or
  build.sbt of a project that uses or should use sbt-kubuszok, or when kubuszok.sbt._ / KubuszokPlugin.autoImport
  appear in the build.
license: Apache-2.0
metadata:
  library: sbt-kubuszok
  library-version: "0.2.6"
---

# Setting up a build with sbt-kubuszok

sbt-kubuszok is an sbt plugin that bundles the plugins kubuszok projects use. It also configures versioning,
publishing to Maven Central and formatting, so the build does not have to. **Most first-release failures came from
re-configuring what the plugin already does, or from forgetting the few things it does not do.**

Version: written for sbt-kubuszok **0.2.6**. Check the version in the user's `project/plugins.sbt`. If it differs, read
the README and plugin source at that tag (<https://github.com/kubuszok/sbt-kubuszok/tree/0.2.6>). Builds on 0.2.4 or
older lack `commandAliases`, `testFull` in sbt 2 aliases, `doc` in `ci`, `dev.prop` and the `ide.scala` fix; upgrade
them to 0.2.6 instead of writing workarounds. CI workflows are covered by `sbt-kubuszok-github-actions`, and
error messages by `sbt-kubuszok-troubleshooting`.

## 1. Pick versions that work together

| sbt (`project/build.properties`) | sbt-kubuszok | JDK for sbt |
|---|---|---|
| 1.11.0+ (kubuszok repos use 1.13.1) | 0.2.6 | 11+ |
| 2.0.x | **0.2.3** (last version for sbt 2.0; upgrade sbt to 2.1 instead) | 17+ |
| 2.1.x | **0.2.4+** (required; use 0.2.6) | 17+ |

- `ci-release` relies on sbt's built-in Central publishing (`localStaging`, `sonaRelease`), which arrived in **sbt
  1.11**. On an older sbt, upgrade sbt first.
- Since 0.2.4 the sbt 2 artifact is built against sbt 2.1.0 / Scala 3.9.0. 0.2.3 bundles an sbt-pgp that breaks on sbt 2.1.
  **Always bump `sbt.version` and sbt-kubuszok in the same commit.** A Scala Steward PR that bumps only one of them
  fails with `IncompatiblePluginsException`.
- A repo that stays on sbt 1.x pins it in `.scala-steward.conf`:
  `updates.pin = [{ groupId = "org.scala-sbt", artifactId = "sbt", version = "1." }]`.

## 2. `project/plugins.sbt`

```scala
// sbt-kubuszok bundles: sbt-git, sbt-scalafmt, sbt-scoverage, sbt-commandmatrix, sbt-pgp, sbt-mima-plugin,
// sbt-ide-settings, sbt-scalajs, sbt-scala-native (+ sbt-projectmatrix and sbt-welcome on sbt 1.x only)
addSbtPlugin("com.kubuszok" % "sbt-kubuszok" % "0.2.6")
// only plugins that are NOT bundled, e.g.:
// addSbtPlugin("pl.project13.scala" % "sbt-jmh" % "0.4.8")
```

**Delete** these lines from `plugins.sbt` when migrating. Re-adding them at a different version than the bundled one
causes conflicts or binary-incompatibility errors:

| Bundled in 0.2.6 | Version |
|---|---|
| `com.github.sbt:sbt-git` | 2.2.0 |
| `org.scalameta:sbt-scalafmt` | 2.6.2 |
| `org.scoverage:sbt-scoverage` | 2.4.4 |
| `com.indoorvivants:sbt-commandmatrix` | 0.1.0 |
| `org.scala-js:sbt-scalajs` | 1.23.0 |
| `org.scala-native:sbt-scala-native` | 0.5.12 |
| `com.github.sbt:sbt-pgp` | 2.4.0 |
| `com.typesafe:sbt-mima-plugin` | 1.2.1 |
| `org.jetbrains.scala:sbt-ide-settings` | 1.1.4 |
| `com.eed3si9n:sbt-projectmatrix` | 0.11.0 (sbt 1.x only; built into sbt 2) |
| `com.github.reibitto:sbt-welcome` | 0.6.0 (sbt 1.x only; no sbt 2 build) |

Also remove `sbt-ci-release`, `sbt-sonatype` and `sbt-dynver` if present. They duplicate what the plugin does, and
sbt-ci-release's env-var conventions (`PGP_SECRET`) do not apply here.

A `.scalafmt.conf` must exist in the repo root. CI checks formatting with it.

## 3. What the plugin already does: do not configure it again

`KubuszokPlugin` triggers automatically for every project.

| Concern | What the plugin sets (0.2.6) | Remove from the build |
|---|---|---|
| Versioning | sbt-git `GitVersioning` with `useGitDescribe`. A tag on HEAD gives the release version (`1.2.3`). Otherwise the version is `<last-tag>-<n>-g<sha>-SNAPSHOT`. Uncommitted changes are ignored: `isSnapshot` is true exactly when HEAD has no tag. | `version :=` / `ThisBuild / version :=`, `enablePlugins(GitVersioning, GitBranchPrompt)`, `git.*` settings, sbt-dynver, `-Dproject.version` hacks |
| Where to publish | `publishTo`: SNAPSHOT goes to `https://central.sonatype.com/repository/maven-snapshots`, a release goes to `localStaging` (bundled, then uploaded by `sonaRelease`) | `publishTo`, `sonatypeCredentialHost`, `sonatypeRepository`, credentials files |
| POM basics | `publishMavenStyle := true`, `pomIncludeRepository := _ => false`, `versionScheme := Some("early-semver")`, `Test / publishArtifact := false` | the same settings |
| Release command | `ci-release`: `+publishSigned`, then `sonaRelease` if HEAD has any tag | custom `ci-release` commands, `addCommandAlias("ci-release", ...)` (an alias to `al.release` points at itself) |
| Release guard | `checkNoSnapshotDeps` runs before `publish`/`publishSigned`. A non-SNAPSHOT version that depends (transitively) on a `-SNAPSHOT` fails. | nothing |
| Formatting | `scalafmtOnCompile := !isCI` (`isCI` is `CI=true` in the env, which GitHub Actions sets) | `scalafmtOnCompile` settings, local `isCI` definitions |
| Resolvers | `resolvers += mavenCentralSnapshots` globally | the same resolver in `build.sbt` (it is still needed in `project/plugins.sbt` to resolve a SNAPSHOT plugin) |
| Scaladoc / console | `-Ygenerate-inkuire` for Scala 3 docs; strips `-Werror`, `-Xfatal-warnings` and unused-import warnings in `console` | nothing |

**Keep** what the plugin does **not** set:

- the POM metadata Central requires: `organization`, `name`/`moduleName`, `description`, `homepage`, `licenses`,
  `developers`, `scmInfo`;
- doc and sources JARs: do not set `packageDoc / publishArtifact := false` or `packageSrc / publishArtifact := false`.
  Central's publishing requirements list javadoc and sources JARs. To get an empty doc JAR, use
  `Compile / doc / sources := Seq.empty`. Skipping doc JARs only for snapshots
  (`packageDoc / publishArtifact := !isSnapshot.value`) is the one accepted shortcut, used where Scaladoc is slow;
- MiMa settings (`mimaPreviousArtifacts`, `mimaFailOnNoPrevious`);
- scalac options, dependencies, `Global / allowUnsafeScalaLibUpgrade` (see troubleshooting).

## 4. Mark what gets published: `projectType`

```scala
projectType := ProjectType.ScalaLibrary // published (Scala library, cross-versioned artifact)
projectType := ProjectType.JarOnly      // published (sbt plugin, Java/resource-only JAR)
projectType := ProjectType.NonPublished // DEFAULT: publish / skip := true, publishArtifact := false
```

- The **default is `NonPublished`**. Every module meant for Central needs
  `ScalaLibrary` or `JarOnly`. Otherwise `ci-release` succeeds and uploads nothing for it.
- Root, tests, examples and benchmarks can keep the default. Do not add `publish / skip := true` as well. If a shared
  `publishSettings` and a `noPublishSettings` both reach one project, apply `noPublishSettings` **last**; the later
  `projectType` wins.
- In 0.2.6, `JarOnly` publishes exactly like `ScalaLibrary`. For a non-Scala JAR, still set
  `crossPaths := false, autoScalaLibrary := false` yourself.
- An sbt plugin module uses `enablePlugins(SbtPlugin)` and `projectType := ProjectType.JarOnly`. To cross-publish it
  for sbt 2, add `crossScalaVersions := Seq("3.x", "2.12.x")` with `pluginCrossBuild / sbtVersion`.
  `ci-release` uses `+`, so every axis is published.

## 5. Root project and aggregation

```scala
lazy val root = project
  .in(file("."))
  .enablePlugins(KubuszokRootPlugin) // ONLY on root
  .settings(name := "my-lib-root")   // projectType stays NonPublished
  .aggregate(core.projectRefs *)
  .aggregate(tests.projectRefs *)
```

- `ci-release` runs from root, so **every published module must be aggregated by root**. Otherwise it is silently
  not published.
- `KubuszokRootPlugin` is `noTrigger`. On sbt 1.x it adds sbt-welcome (`logo`, `usefulTasks`). On sbt 2 it adds
  nothing beyond `KubuszokPlugin`. Never enable it on other modules.
- A separate nested sbt build (for example an sbt plugin in a subdirectory with its own `project/`) needs its own
  `addSbtPlugin(sbt-kubuszok)`, its own `projectType`, and its own `sbt ci-release` step in the release workflow.

## 6. Matrix modules, `Aliases` and `DevProperties`

```scala
import commandmatrix.extra.*
import kubuszok.sbt.*
import kubuszok.sbt.KubuszokPlugin.autoImport.*

// project/Versions.scala: `object versions { val scala213 = "2.13.18"; val scala3 = "3.3.8"; ... }`
// (not `val versions = new { ... }` in build.sbt: on sbt 2 the build is Scala 3, where members of an anonymous
// class are not accessible without reflection)

val dev = new DevProperties(Some(versions.scala213), Some(versions.scala3), versions.platforms)

lazy val core = projectMatrix          // lazy val: matrices are referenced before definition
  .in(file("core"))
  .someVariations(versions.scalas, versions.platforms)(dev.only1VersionInIDE *)
  .settings(publishSettings)           // includes projectType := ProjectType.ScalaLibrary

lazy val tests = projectMatrix.in(file("tests"))
  .someVariations(versions.scalas, versions.platforms)(dev.only1VersionInIDE *)
  .dependsOn(core)                     // NonPublished by default

lazy val al = new Aliases(published = Seq(core), testOnly = Seq(tests), compileOnly = Seq())
```

- `Aliases` generates the command strings that CI runs. `al.ci("JVM", "3")` expands to
  `clean ; coverage ; <ids>/compile ; <ids>/test ; coverageAggregate ; coverageOff` (coverage only on JVM), then
  `compileOnly` compiles, then `<id>/doc` for `published` modules. On sbt 2 the commands use `<id>/testFull`. `al.test(...)` runs tests only, `al.publishLocalForTests(filter)` publishes locally, and
  `al.release == "ci-release"`. Platforms are `"JVM" | "JS" | "Native"`, Scala binaries are `"2.13" | "3"`
  (2.12 axes are ignored). Alias names follow `ci-<jvm|js|native>-<2_13|3>`.
- `published`/`testOnly`/`compileOnly` only drive these commands. **They do not decide what is published**:
  `projectType` does. Keep both in sync. A published module missing from `published` drops out of
  `publish-local-for-tests`, and a test module listed in `published` gets `publishLocal`ed.
- Platform-specific settings go through `MatrixAction.ForPlatform(s)(...).Configure(_.settings(...))` passed to
  `someVariations`. After `someVariations`, `.jvmPlatform(...)` and similar calls do not apply.
- **Register the aliases with `al.commandAliases(...)` on root** (sbt 1 and sbt 2). It adds `ci-*` and `test-*` for
  every (platform, Scala) combination that has projects, plus `publish-local-for-tests` when a filter is given:
  `.settings(al.commandAliases(publishLocalForTestsFilter = Some((_, platform) => platform == "JVM")))`. On sbt 1,
  `usefulTasks := al.usefulTasks(...)` (sbt-welcome) registers the same aliases and also lists them on startup; use
  one or the other. Templates are in [build-templates.md](build-templates.md).
- **Do not hand-write what the plugin now generates**: no `fullTests`/`testFull` rewriting (sbt 2's `test` is
  cached and could report "No tests to run"; the generated commands already use `testFull`), no `ci` override that
  only adds `<id>/doc` (already there, so Scaladoc errors fail CI instead of the release; override
  `protected def docInCi = false` to opt out), no `addCommandAlias("ci-release", ...)`.
- Override `ci`/`test` in an `Aliases` subclass for project-specific steps (for example MiMa); `commandAliases` uses
  the overrides.

### dev.properties

`DevProperties` reads `dev.properties` from the build root to decide which matrix row the IDE (Metals/IntelliJ via BSP)
imports. kubuszok repos **commit** a default file and tell developers to
`git update-index --assume-unchanged dev.properties` before editing it:

```properties
# Do not commit changes to this file! Run: git update-index --assume-unchanged dev.properties
# Allowed: 2.13, 3
ide.scala = 3
# Allowed: jvm, js, native
ide.platform = jvm
```

- If the file is missing and more than one platform is configured, the build fails to load:
  `Build not configured to use exactly 1 platform, ide.platform must be jvm, js, or native`.
- With both `scala213` and `scala3` set, `ide.scala` picks the IDE version (`2.13` or `3`); a missing key means 3.
  Values are trimmed. Do not re-derive `ide.scala`/`ide.platform` in the build.
- Project-specific keys go into the same file. Read them with `dev.prop(name): Option[String]` (trimmed, `None` when
  missing or blank), not `dev.props.getProperty`, which returns `null` for a missing key:
  ```scala
  val logCrossQuotes: Boolean = dev.prop("log.cross-quotes").fold(!isCI)(_ == "true")
  ```

### Helpers

- `foldVersion(scalaVersion.value)(for2_13 = Seq(...), for3 = Seq(...))` returns `Seq.empty` for other versions.
- `isCI: Boolean`, `mavenCentralSnapshots: Resolver`, `checkNoSnapshotDeps` task.

## 7. Migration checklist (existing build -> sbt-kubuszok)

1. Set sbt and the plugin version from section 1, and clean `plugins.sbt` (section 2).
2. Remove everything in the "Remove" column of section 3. Keep POM metadata, doc JARs and MiMa.
3. Add `projectType := ProjectType.ScalaLibrary` (or `JarOnly`) to every published module. Leave the others at the
   default.
4. Make root aggregate all modules and enable `KubuszokRootPlugin` on root only.
5. Build `Aliases` and register the aliases with `al.commandAliases(...)` on root.
6. Commit `dev.properties` if you use `DevProperties`.
7. Run `scalafmtAll`, `scalafmtSbt` (or the `scalafmt` CLI on the whole repo) and commit the result. CI checks
   formatting and `scalafmtOnCompile` is off there.
8. Verify locally before pushing:
   - `sbt "show version ; show isSnapshot"` (one argument: sbt 2 joins several arguments into one line)
   - `sbt "projects"`
   - `sbt ci-jvm-3`
   - `sbt "+publishLocal"`, which runs Scaladoc on every cell.
   - `sbt "show <module>/publish/skip"` should be `false` for published modules and `true` for the others.
9. Write the workflows with `sbt-kubuszok-github-actions`. Before tagging, confirm that the first master-push snapshot
   publish succeeded.

## Gotchas

- **Workarounds copied from older builds.** Builds written for 0.2.4 contain `fullTests` helpers, hand-written
  `addCommandAlias` loops, `ci` overrides adding `/doc`, `dev.props.getProperty(...)` and `ci-release` aliases.
  Replace them with `al.commandAliases(...)` and `dev.prop(...)` instead of copying them.
- **Any tag on HEAD makes it a release.** `ci-release` runs `sonaRelease` whenever `git.gitCurrentTags` is non-empty.
  Never put non-version tags on master commits.
- **A `v` prefix works but is not the convention.** sbt-git strips `v` from `v1.2.3`. kubuszok repos tag bare
  `1.2.3`.
- **Deleting too much while migrating.** Removing `packageDoc` settings, MiMa or POM metadata along with the
  boilerplate breaks the release (Central validation). Remove only what section 3 lists.
- **Git worktrees need 0.2.6+.** sbt-git's JGit cannot read the `.git` file of a `git worktree`. On 0.2.5 and older,
  `version` inside a worktree falls back to a timestamp (`20261118T202211`) and tags are not seen. 0.2.6 reads the
  repository through the `git` CLI there, so upgrade. Do not set `useConsoleForROGit := true` by hand on 0.2.5: its
  console reader reports `gitCurrentTags == Seq("")` on an untagged commit, so `isSnapshot` becomes `false` and
  `ci-release` would attempt a release (0.2.6 filters the empty tag out).
- **`ci-*` starts with `clean`.** Builds with source generators or prebuilt caches that `clean` would wipe override
  `ci` in the `Aliases` subclass, e.g.
  `override def ci(p: String, s: String) = super.ci(p, s).split(" ; ").filterNot(_ == "clean").mkString(" ; ")`.
- **Extra artifacts (classifier JARs) on sbt 2.** `artifacts` and `packagedArtifacts` are project-level keys;
  `Compile / packagedArtifacts` is silently ignored by `publish`/`publishLocal` (sbt 1 and 2). Use
  `addArtifact(Artifact(name.value, "jar", "jar", "natives"), myNativesJar)` at project level. It also handles sbt 2
  caching; a hand-written `packagedArtifacts := ...` needs `Def.uncached(...)` on sbt 2 or fails to load with
  `given evidence sjsonnew.JsonFormat[...Map[...Artifact, xsbti.HashedVirtualFileRef]] is not found`. Files go in as
  `HashedVirtualFileRef` (`fileConverter.value.toVirtualFile(file.toPath)`), not `File`. Native libraries can instead
  go inside the main JAR via `Compile / packageBin / mappings`, which is what the kubuszok `*-native-providers` do.
- **Nested builds drift.** A nested sbt build (its own `project/`) has its own `plugins.sbt`: bump sbt-kubuszok there
  too, and remove bundled plugins from it as well.
- **`checkNoSnapshotDeps` does not see the meta-build.** SNAPSHOT plugins in `project/plugins.sbt` are not checked;
  release only with released plugins.
- More symptoms with error texts are in `sbt-kubuszok-troubleshooting`.
