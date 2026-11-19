# build.sbt templates for sbt-kubuszok 0.2.6

These templates are distilled from kubuszok repositories (scala-sax-parser and kindlings on sbt 2.1, hearth on
sbt 1.13). Replace `my-lib`, the modules and the versions with your own.

## Shared part (sbt 1.x and sbt 2.x)

```scala
import commandmatrix.extra.*
import kubuszok.sbt.*
import kubuszok.sbt.KubuszokPlugin.autoImport.*

// project/Versions.scala (works on sbt 1 and sbt 2; `val versions = new { ... }` in build.sbt does not compile
// usefully on sbt 2, whose build dialect is Scala 3):
//
//   import sbt.VirtualAxis
//   object versions {
//     val scala213 = "2.13.18"
//     val scala3 = "3.3.8"
//     val scalas = List(scala213, scala3)
//     val platforms = List(VirtualAxis.jvm, VirtualAxis.js, VirtualAxis.native)
//     val munit = "1.3.6" // >= 1.3.1 on Scala Native 0.5.12, see sbt-kubuszok-troubleshooting
//   }

val dev = new DevProperties(
  scala213 = Some(versions.scala213),
  scala3 = Some(versions.scala3),
  platforms = versions.platforms
)

val settings = Seq(
  scalacOptions ++= foldVersion(scalaVersion.value)(
    for2_13 = Seq("-Xsource:3"),
    for3 = Seq("-Xcheck-macros")
  )
)

// What Central requires and the plugin does NOT set. Version, publishTo, versionScheme, etc. come from the plugin.
val publishSettings = Seq(
  organization := "com.kubuszok",
  homepage := Some(url("https://github.com/kubuszok/my-lib")),
  organizationHomepage := Some(url("https://kubuszok.com")),
  licenses := Seq("Apache-2.0" -> url("https://www.apache.org/licenses/LICENSE-2.0")),
  scmInfo := Some(
    ScmInfo(url("https://github.com/kubuszok/my-lib/"), "scm:git:git@github.com:kubuszok/my-lib.git")
  ),
  startYear := Some(2026),
  developers := List(
    Developer("MateuszKubuszok", "Mateusz Kubuszok", "", url("https://kubuszok.com"))
  ),
  projectType := ProjectType.ScalaLibrary
)
// No `noPublishSettings` needed: NonPublished is the default.

lazy val core = projectMatrix
  .in(file("core"))
  .someVariations(versions.scalas, versions.platforms)(dev.only1VersionInIDE *)
  .settings(settings)
  .settings(publishSettings)
  .settings(
    name := "my-lib",
    moduleName := "my-lib",
    description := "What my-lib does"
  )

lazy val tests = projectMatrix
  .in(file("tests"))
  .someVariations(versions.scalas, versions.platforms)(dev.only1VersionInIDE *)
  .settings(settings)
  .settings(
    name := "my-lib-tests",
    libraryDependencies += "org.scalameta" %%% "munit" % versions.munit % Test // on sbt 2 use %% (platform-aware there)
  )
  .dependsOn(core)

// ci-* runs clean, coverage (JVM), compile, test (testFull on sbt 2) and doc for `published`.
lazy val al = new Aliases(published = Seq(core), testOnly = Seq(tests))

// Project-specific steps go into a subclass, e.g. MiMa:
// lazy val al = new Aliases(published = Seq(core), testOnly = Seq(tests)) {
//   override def ci(platform: String, scalaBinary: String): String =
//     (super.ci(platform, scalaBinary) +: projectIds(published, platform, scalaBinary).map(id => s"$id/mimaReportBinaryIssues"))
//       .mkString(" ; ")
// }
```

Platform-specific settings go into `someVariations` actions:

```scala
val jsNativeSources = MatrixAction
  .ForPlatforms(VirtualAxis.js, VirtualAxis.native)
  .Configure(_.settings(Compile / unmanagedSourceDirectories += (Compile / sourceDirectory).value / "scala-jsNative"))

lazy val core = projectMatrix.in(file("core"))
  .someVariations(versions.scalas, versions.platforms)((dev.only1VersionInIDE :+ jsNativeSources) *)
```

## Root (sbt 1.x and sbt 2.x)

```scala
lazy val root = project
  .in(file("."))
  .enablePlugins(KubuszokRootPlugin)
  .settings(settings)
  .settings(name := "my-lib-root")
  // ci-jvm-3, ci-js-2_13, ..., test-jvm-3, ..., publish-local-for-tests (filter: (scalaBinary, platform) => Boolean)
  // do NOT add a `ci-release` alias: the command already exists
  .settings(al.commandAliases(publishLocalForTestsFilter = Some((_, platform) => platform == "JVM")))
  .aggregate(core.projectRefs *)
  .aggregate(tests.projectRefs *)
```

On sbt 1.x, sbt-welcome can register the same aliases and print them on startup. Use it instead of
`commandAliases`, not together with it:

```scala
import sbtwelcome.UsefulTask

  .settings(
    logo := s"my-lib ${version.value} for Scala ${versions.scalas.mkString(", ")}",
    usefulTasks := al.usefulTasks(
      publishLocalForTestsFilter = Some((_, platform) => platform == "JVM"),
      extra = Seq(UsefulTask("scalafmtAll ; scalafmtSbt", "Format everything").alias("fmt"))
    )
  )
```

Extra project aliases (code generation, local verification) stay plain `addCommandAlias(...)` next to
`commandAliases`.

`commandAliases` registers only combinations that have projects, so the CI matrix must list exactly those.

## sbt plugin module (published for sbt 1.x and sbt 2.x)

```scala
lazy val plugin = project
  .in(file("plugin"))
  .enablePlugins(SbtPlugin)
  .settings(publishSettings)
  .settings(
    name := "sbt-my-plugin",
    projectType := ProjectType.JarOnly,
    crossScalaVersions := Seq("3.9.0", "2.12.21"), // the Scala version of the oldest sbt 2 you support
    scalaVersion := "2.12.21",
    pluginCrossBuild / sbtVersion := (scalaBinaryVersion.value match {
      case "2.12" => "1.13.1"
      case _      => "2.1.0"
    })
  )
```

`ci-release` runs `+publishSigned`, so both the `_2.12_1.0` and `_sbt2_3` artifacts are published. Build the sbt 2
axis against the oldest sbt 2 you want to support (an sbt 2.0-built plugin also loads on sbt 2.1; sbt 2.1.0 uses
Scala 3.9.0).

## Java / resource-only JAR

```scala
lazy val natives = project
  .in(file("natives"))
  .settings(publishSettings)
  .settings(
    projectType := ProjectType.JarOnly,
    crossPaths := false,        // not set by JarOnly in 0.2.6
    autoScalaLibrary := false,  // not set by JarOnly in 0.2.6
    Compile / doc / sources := Seq.empty // empty but present javadoc JAR (Central requires one)
  )
```

Native libraries go inside the JAR under a per-OS path. On sbt 2 `mappings` take `HashedVirtualFileRef`:

```scala
// after kubuszok/ssg-native-providers build.sbt
Compile / packageBin / mappings ++= {
  val conv = fileConverter.value
  val dir = baseDirectory.value / "natives" / "linux-x86_64" // filled by an earlier CI step (build or download)
  if (dir.exists())
    sbt.IO.listFiles(dir).filter(_.isFile).toSeq
      .map(f => (conv.toVirtualFile(f.toPath): xsbti.HashedVirtualFileRef) -> s"native/linux-x86_64/${f.getName}")
  else Seq.empty
}
```

The release workflow must produce the same `natives/` before `sbt ci-release` (see `sbt-kubuszok-github-actions`),
and CI should check the JAR contents, because a missing library still packages fine.
