---
name: baltic-porter-generated-code
description: >-
  Working in a repository whose Scala sources are generated from Java by the Baltic Porter engine
  (sge, ssg, lls): how project/BalticPorterGen.scala, the balticporter-engine pin in
  project/plugins.sbt, the port policy (sge-port/, lls-port/, ssg-*/port/*.conf), src_managed and the
  .generated-marker fit together; never editing generated code or patching callers and tests to fit
  it; wiring generated resources ("Could not initialize class"); bumping the engine pin and proving
  the snapshot is published (maven-metadata.xml, timestamped snapshots); a base port artifact
  (lls-port) evicting the engine pin. Use when a compile or test error points into
  target/balticporter*/…/src_managed, before changing generated code or a caller to fit it, when
  bumping the Baltic Porter pin, or when generation is stale, skipped or fails.
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# Generated code in a Baltic Porter consumer

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
If the pin is another commit, read the user guide at that commit:
`https://github.com/kubuszok/balticporter/tree/<hash>/docs/user-guide`.

## How it is wired

- `project/plugins.sbt` puts `balticporter-engine` on the **build's** classpath (ssg also pins
  `balticporter-frontend-ts` at the same hash), resolved from
  `https://central.sonatype.com/repository/maven-snapshots`. There is no engine checkout: the engine
  jar carries only the generic engine, and everything specific to the ported library lives in the
  consumer's own repository:
  - sge: `sge-port/` (policy Scala compiled into the meta-build by `project/build.sbt`, injected files
    under `sge-port/overrides/`, frozen derived policy `sge-port/*derived-policy.tsv`), plus replacements
    sge compiles itself, read through `providedSources`;
  - lls: `lls-port/`, also published as the `lls-port` artifact that sge's build depends on;
  - ssg: `.conf` files and injected sources under `ssg-liquid/port/` and `ssg-md/port/`.
- `project/BalticPorterGen.scala` (sge also has `BalticPorterExtGen.scala` and
  `BalticPorterEcsGen.scala`) runs the port inside the sbt JVM as a source generator, either through
  a `.conf` (`balticporter.runner.PortConfig.load(conf).execute()`, ssg) or a hand-written
  `balticporter.runner.PortRun(...)` (sge, lls). Input: the upstream Java in a git submodule under
  `original-src/`. Output: `<portRoot>/src_managed/` — `main/scala` shared by every platform row,
  `<jvm|js|native>/scala` per row, `main/resources`. sge's core lands in `target/balticporter-sge/`,
  lls's in `target/balticporter-lls/`, ssg's under `target/balticporter/`.
- The output is reused while the generator's `.generated-marker` matches its inputs (engine pin,
  upstream commit, generator source, JDK major and, where hashed, the policy files). Delete the
  marker to force a regeneration. `sbt --client generatePort` runs only the generation.
- The sbt server must run on the JDK the repository states (all three: 25). The generated code
  differs by JDK major (a member gets `override` only where that JDK's supertype declares it).
- Reports: the generator sets `balticporter.reportDir` per port; each run writes
  `<reportDir>/run-latest/` (`decisions.tsv`, `findings.tsv`, `srcmap.tsv`, `port-map.tsv`, …).
  sge: `target/balticporter-reports/<label>/run-latest/`; ssg:
  `target/balticporter/port-report/<label>/run-latest/`. Without `reportDir` a run inside sbt
  writes no report at all.

How a `.conf` is written is in `baltic-porter-configure-port`; the engine's own guide is
[Getting started](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/getting-started.md).

## Rules

1. **Never edit a generated file**, and never patch hand-written code, a test or a build setting to
   fit a generated defect. The next generation overwrites the first, and the second hides a
   translation bug from every other consumer. The plugin's hook (Claude Code only) blocks edits under
   `src_managed/` and `target/balticporter-*/`.
2. A wrong generated member is fixed where it is decided, in this order:
   - the port's **policy** in this repository (a rename, a dropped or injected type, a method body,
     a phase's configuration) — see `baltic-porter-customize-port`;
   - the **engine**, when the rule is true of every library — that change is made in
     <https://github.com/kubuszok/balticporter>, published, and then pinned here;
   - an **injected hand-written file** shipped by the policy, when no mechanical translation exists.
     Look at what the previous hand port did at that exact site first.
   `baltic-porter-root-cause-port` is the procedure for deciding which.
3. No test is skipped, ignored, deleted or rewritten to pass, and no warning filter, exclusion or
   baseline is widened to get green. When a generated API differs from what a test expects, decide
   which matches the upstream Java: Java wins for behaviour, the previous hand port wins for API
   spelling.
4. Platform limits (no threads on Scala.js, no client-memory vertex arrays in WebGL, no reflection on
   Scala.js/Native) are answered at the smallest site the upstream project itself answered them (for
   libGDX, its GWT backend emulation), as a per-platform source row, never by moving shared tests off
   a platform. See `baltic-porter-cross-platform-port`.
5. **The port's `main/resources` is a second output and needs its own wiring.** A build that collects
   only the generated `.scala` compiles green and throws at the first lookup, often from a static
   initialiser, as `Could not initialize class <Owner>$`. Wire it as a task that runs the generation
   and then lists the files — `Compile / resourceGenerators += Def.task { generate(…);
   balticporter.sbtgen.SbtGen.resourceFiles(portRoot, "main").map(_.toFile) }.taskValue` — plus
   `Compile / managedResourceDirectories +=` that directory so each file keeps its package path.
   Never a directory test inside a setting: settings are evaluated while the build loads, before the
   port has run on a fresh checkout, so the test reads false and nothing ships.
6. The generated code asks for a resource at the **upstream** path (`/com/vladsch/…`): a classpath
   lookup is a string literal and no rename moves it. A hand port that moved its copy into the
   renamed namespace leaves a resource tree that answers at neither name. Ship the port's own tree
   and delete the hand one once nothing reads it.

## Tracing an error back to its cause

1. Read the first error, not the count: one typer error hides every later compiler phase's errors.
2. Find the generated member. Each non-mechanical decision carries a `/* porter: … */` note saying
   which rule produced it and why (`reason=universal|configured|library-rule`, `phase=…`, `key=…`);
   `grep -rn '/\* porter:' <portRoot>/src_managed` lists them all. The same rows are in the run's
   `decisions.tsv`.
3. Classify and fix as in `baltic-porter-root-cause-port`. For an engine fix, reduce it to the
   smallest Java input; the engine's `balticporter-testkit` (`balticporter.testkit.PortSuite`) runs a
   Java snippet through phases and shows the emitted Scala, see `baltic-porter-customize-port`.
4. Only after the fix is published, repin (below). Then touch the consumer, and only its pin.

## Bumping the engine pin

1. A snapshot is published for each commit pushed to the engine's `master`. A second push within
   minutes cancels the first one's release, so that commit is never published. Pin only a hash you
   have proven exists.
2. Prove it. Since sbt 2.1 the snapshot repository holds **timestamped files only**
   (`…-<hash>-20261118.102813-1.pom`), so the plain `<hash>-SNAPSHOT.pom` answers 404. Probe the
   version's metadata:
   `curl -s -o /dev/null -w '%{http_code}' https://central.sonatype.com/repository/maven-snapshots/com/kubuszok/balticporter-engine_3/<hash>-SNAPSHOT/maven-metadata.xml` → `200`.
   Engine commits published by sbt 2.0 have the plain `.pom` instead; accept either. The
   artifact-level version list is not in chronological order, so do not pick "the latest" from it.
3. Replace the hash on every pin line of `project/plugins.sbt` (sge: `libraryDependencies` and
   `dependencyOverrides`; ssg: engine and `frontend-ts`), `reload`, regenerate, run the full local gate
   (`sbt --client verifyLocal`), then push once. See `baltic-porter-consumer-ci`.
4. For a local iteration before the engine is published: in an engine checkout, commit (the version
   is the commit hash), `sbt --client "reload; publishLocal"`, and pin that hash locally. Never push a
   pin that is not on Central.
5. A base's port artifact (sge depends on `lls-port`) depends on the engine it was built with, and
   two commit-hash versions are not comparable: eviction can silently pick the base's engine over
   your pin. Keep `ThisBuild / libraryDependencySchemes += "com.kubuszok" %% "balticporter-engine" %
   VersionScheme.Always` and `dependencyOverrides += "com.kubuszok" %% "balticporter-engine" % "<pin>"`
   beside the pin, and check that the generation log's `engine=` stamp equals the pin. When the engine
   changes a class the base's port artifact compiles against, a `NoSuchMethodError` from the
   meta-build means: republish the base (lls) against the new engine first, then pin the new base
   version here.
