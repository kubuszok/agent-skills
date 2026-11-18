---
name: multiarch-scala-library-vs-app
description: >-
  Deciding how a multiarch-scala build is laid out: cross-platform libraries published with projectMatrix and
  consumed with %%% (artifacts _3, _sjs1_3, _native0.5_3), applications that package per platform
  (MultiArchJvmReleasePlugin releasePackage / releasePlatform / releaseAll, Scala.js fullLinkJS, Scala Native
  nativeLink, AndroidPlugin APKs, withCrossNative link rows), and provider JARs (sn-provider, jni-provider,
  pnm-provider) with autoScalaLibrary := false and crossPaths := false. Covers merging internal modules into one
  published JAR, where native libraries belong (provider JAR vs app), publish / skip, and common mistakes such as
  packaging plugins or withCrossNative on a library, %% instead of %%% on sbt 1, and missing fork := true.
  Use when structuring a new multi-platform build or splitting an existing one.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Libraries, applications and provider JARs

Version: written for multiarch-scala **0.4.0**. Check `sbt-multiarch-scala` in the user's `project/plugins.sbt`;
if it differs, read <https://github.com/kubuszok/multiarch-scala/blob/0.4.0/README.md> at that tag.

A multiarch-scala build usually contains three kinds of projects. Mixing up their settings causes either missing
packaging or broken publishing.

| Concern | Library | Application | Provider JAR |
|---|---|---|---|
| Purpose | code other builds depend on | something end users run | native binaries + manifest, no Scala code |
| Shape | `projectMatrix` with `.jvmPlatform` / `.jsPlatform` / `.nativePlatform` | same, or plain projects per platform | plain `project` |
| Published | yes | no (`publish / skip := true`) | yes |
| Artifact names | `my-lib_3`, `my-lib_sjs1_3`, `my-lib_native0.5_3` | - | `pnm-provider-foo-desktop` (no suffix) |
| Consumed with | `%%%` on sbt 1.x; `%%` on sbt 2.x | - | `%` |
| multiarch plugins | none needed (maybe `MultiArchResourcesPlugin` / `MultiArchServiceLoaderPlugin` helpers) | `NativeProviderPlugin`, `MultiArchJvmReleasePlugin`, `AndroidPlugin`, `withCrossNative` | none; `multiarch-core` in the meta-build for `Platform` and the manifest codec |
| Main class | none | `Compile / mainClass` | none |

## Libraries

```scala
lazy val myLib = (projectMatrix in file("my-lib"))
  .settings(name := "my-lib", organization := "com.example")
  .jvmPlatform(scalaVersions = Seq(scala3))
  .jsPlatform(scalaVersions = Seq(scala3))
  .nativePlatform(scalaVersions = Seq(scala3))
```

- Platform code in `src/main/scalajvm/`, `scalajs/`, `scalanative/`.
- No packaging, no `withCrossNative`, no `nativeLink`: a library never links; the application that uses it does.
- A library that wraps native code does not need to put the binaries in its own JAR: depend on (or document) a
  provider JAR, and load with `NativeLibLoader` (JVM) or `@link` + `NativeProviderPlugin` in the app (Native).
  A library's `@link("foo")` makes every consuming app need the matching `sn-provider` and `NativeProviderPlugin`.
- Several internal modules can be published as one JAR by appending their `packageBin / mappings` and marking them
  `publish / skip := true`:

```scala
.jvmPlatform(scalaVersions = Seq(scala3), settings = Seq(
  Compile / packageBin / mappings ++= (platformJdk.jvm(scala3) / Compile / packageBin / mappings).value
))
```

  The merged module's dependencies are then not in the published POM; add them to the publishing module.

## Applications

```scala
import multiarch.sbt.{ NativeProviderPlugin, Platform }
import multiarch.sbt.ProjectMatrixOps._

lazy val app = (projectMatrix in file("app"))
  .settings(publish / skip := true, Compile / mainClass := Some("myapp.Main"))
  .dependsOn(core)
  .jvmPlatform(scalaVersions = Seq(scala3), settings = Seq(
    fork := true,
    javaOptions += "--enable-native-access=ALL-UNNAMED"
  ))
  .jsPlatform(scalaVersions = Seq(scala3), settings = Seq(scalaJSUseMainModuleInitializer := true))
  .nativePlatform(scalaVersions = Seq(scala3), settings = NativeProviderPlugin.projectSettings)
  .settings(libraryDependencies += "com.example" % "sn-provider-foo" % "1.0.0")
  .withCrossNative(scala3) // one link row per desktop platform; non-host rows only when zig is installed
```

| Platform | How | Output |
|---|---|---|
| JVM, needs a JDK | `MultiArchJvmReleasePlugin` `releasePackage` | `target/release-package/<app>/` with launcher scripts |
| JVM, self-contained | `releasePlatform <classifier>` / `releaseAll` | `.tar.gz` / `.zip` with jlinked JRE + Roast launcher |
| Browser | sbt-scalajs `fullLinkJS` + your HTML (skill `multiarch-scala-browser-packaging`) | JS bundle |
| Scala Native | `nativeLink` (+ `withCrossNative` rows) | binary per platform |
| Android | `AndroidPlugin` `androidDex` ... `androidSign` | signed debug APK |

`MultiArchJvmReleasePlugin` and `AndroidPlugin` are AutoPlugins for single projects; in a matrix, add their
settings to the JVM row (`JvmPackaging.jvmSettings ++ JvmPackaging.distSettings`, `AndroidBuild.taskSettings`)
rather than `enablePlugins` on the whole matrix. Release keys are in the `multiarch-scala-setup` skill's
`jvm-release.md`.

## Provider JARs

```scala
lazy val myProvider = project
  .in(file("providers/pnm-provider-foo-desktop"))
  .settings(
    name             := "pnm-provider-foo-desktop",
    autoScalaLibrary := false,
    crossPaths       := false
    // + packageBin / mappings for native/... and a generated manifest
  )
```

The manifest format, the v2 `native/<artifact>/<version>/<classifier>/` layout and a complete build are in the
`multiarch-scala-setup` skill's `provider-manifests.md`. Split providers by consumer: desktop JARs for JVM
(`pnm-`/`jni-`), Android JARs (`android-*` classifiers), static JARs for Scala Native (`sn-`).

Real-world references: [sge](https://github.com/kubuszok/sge) (library + demos with JVM, browser, Native and Android
packaging) and [sge-native-providers](https://github.com/kubuszok/sge-native-providers) (provider JARs built from
Rust and C).

## Common mistakes

- **Packaging plugins or `withCrossNative` on a library** - nothing to package or link; it only slows the build and
  may publish odd artifacts.
- **`%%` for a cross-platform library on sbt 1.x** - resolves the JVM artifact on every row; JS/Native rows fail.
  Use `%%%` (sbt 2.x `%%` is already platform-aware).
- **`%%` for a provider JAR** - providers have no Scala suffix; use `%`.
- **Publishing an application** - set `publish / skip := true`.
- **JVM app without `fork := true`** - native loading runs inside sbt's JVM and class loaders; `java.library.path`,
  `--enable-native-access` and provider discovery do not apply.
- **Provider dependency only on the library** - put provider JARs on every application and test project that runs
  native code; do not rely on them flowing through `dependsOn`.
