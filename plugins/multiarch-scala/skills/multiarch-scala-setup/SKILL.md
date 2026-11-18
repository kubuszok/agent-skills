---
name: multiarch-scala-setup
description: >-
  Entry point for multiarch-scala (sbt plugin com.kubuszok sbt-multiarch-scala, libraries multiarch-core,
  multiarch-resources, multiarch-serviceloader, multiarch-panama-api, multiarch-panama-jdk, sn-provider-curl).
  Covers the artifact map, project/plugins.sbt for sbt 1.x and sbt 2.x (sbt-scala-native and sbt-projectmatrix are
  not pulled in transitively), a projectMatrix build for JVM + Scala.js + Scala Native, platform source directories
  (src/main/scalajvm, scalajs, scalanative), project IDs, NativeProviderPlugin wiring with sn-provider.json
  providers, nativeConfig ordering (:= vs ~=), the Platform classifiers, snapshot resolvers, and which
  multiarch-scala-* skill to read next. Use when adding multiarch-scala to a build, when Scala Native linking cannot
  find a provider library, or when nativeConfig settings disappear.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Setting up multiarch-scala

multiarch-scala is a set of sbt plugins and small libraries for Scala projects that target the JVM, Scala.js and
Scala Native, and that ship native libraries (`.a`, `.so`, `.dylib`, `.dll`) inside ordinary JARs called
**providers**.

Version: written for multiarch-scala **0.4.0**. Check the version in the user's `project/plugins.sbt`
(`sbt-multiarch-scala`) and `libraryDependencies` (`multiarch-*`). If it differs, read the README and sources at that
tag: <https://github.com/kubuszok/multiarch-scala/blob/0.4.0/README.md> (swap `0.4.0`). Snapshots newer than 0.4.0
are published as `0.4.0-<N>-g<hash>-SNAPSHOT` (e.g. `0.4.0-20-ga3e0f08-SNAPSHOT`); where they differ, this skill says
"after 0.4.0". Keep the plugin and every `multiarch-*` library on the same version.

## Artifacts

| Artifact | How to depend | Scala / platforms | What it gives |
|---|---|---|---|
| `sbt-multiarch-scala` | `addSbtPlugin(...)` | sbt 1.x and sbt 2.x | `NativeProviderPlugin`, `MultiArchNativeReleasePlugin`, `MultiArchJvmReleasePlugin`, `AndroidPlugin`, `ProjectMatrixOps.withCrossNative`, `MultiArchResourcesPlugin` / `MultiArchServiceLoaderPlugin` helpers |
| `multiarch-core` | `%%` | 2.12, 2.13, 3; JVM | `Platform`, `ProviderType`, `NativeLibLoader`, manifest codec |
| `multiarch-resources` | `%%%` | 2.13, 3; JVM, JS, Native | `PlatformResources` (classpath resources on all platforms) |
| `multiarch-serviceloader` | `%%%` | 2.13, 3; JVM, JS, Native | `PlatformServiceLoader` - **after 0.4.0 only**, not in the 0.4.0 release |
| `multiarch-panama-api` | `%%` | Scala 3 only; JVM (JDK 17 bytecode) | `PanamaProvider` abstraction, Android `PanamaPortProvider` |
| `multiarch-panama-jdk` | `%%` | Scala 3 only; JVM, JDK 22+ at run time | `JdkPanama` over `java.lang.foreign` |
| `sn-provider-curl` | `%` (no Scala suffix) | any | static libcurl for the 6 desktop platforms |

All are `"com.kubuszok" ... % "0.4.0"`. On sbt 2.x `%%` is already platform-aware, so `%%` works where sbt 1.x
needs `%%%`.

Next skills:

| Task | Skill |
|---|---|
| Library vs application layout, what to publish | `multiarch-scala-library-vs-app` |
| Loading `.so`/`.dylib`/`.dll` on the JVM (JNI, Panama) | `multiarch-scala-jvm-native-loading` |
| `PanamaProvider`, desktop + Android FFI from one code base | `multiarch-scala-panama` |
| Link-testing all 6 desktop targets with zig | `multiarch-scala-cross-native-testing` |
| Android APK (`androidDex` ... `androidInstall`) | `multiarch-scala-android-build` |
| Resources and `ServiceLoader` on JS/Native | `multiarch-scala-resources-serviceloader` |
| Scala.js browser bundle | `multiarch-scala-browser-packaging` |
| Writing your own provider JAR | [provider-manifests.md](provider-manifests.md) |
| JVM release archives (jlink + Roast launcher) | [jvm-release.md](jvm-release.md) |

## project/plugins.sbt

The plugin declares `sbt-scala-native` (and, on sbt 1.x, `sbt-projectmatrix`) as `Provided`: **add them yourself**.

sbt 1.x:

```scala
addSbtPlugin("com.eed3si9n"     % "sbt-projectmatrix"   % "0.11.0")
addSbtPlugin("org.scala-js"     % "sbt-scalajs"         % "<1.x version>")
addSbtPlugin("org.scala-native" % "sbt-scala-native"    % "0.5.12") // the version multiarch 0.4.0 is built against
addSbtPlugin("com.kubuszok"     % "sbt-multiarch-scala" % "0.4.0")
```

sbt 2.x: the same lines without `sbt-projectmatrix` (projectMatrix is built into sbt 2).

For a snapshot, also add the resolver (both in `project/plugins.sbt` for the plugin and in `build.sbt` for libraries):

```scala
resolvers += "Central Portal Snapshots" at "https://central.sonatype.com/repository/maven-snapshots"
```

Imports in `build.sbt` - the AutoPlugins are visible by name, helper objects are not:

```scala
import multiarch.sbt.{ Platform, NativeProviderPlugin, ProjectMatrixOps }
import multiarch.sbt.ProjectMatrixOps._ // for .withCrossNative
```

`multiarch.sbt.Platform` is an alias of `multiarch.core.Platform`.

## A three-platform matrix

```scala
val scala3 = "3.3.7" // any Scala 3 (or 2.13) the user already uses

lazy val core = (projectMatrix in file("core"))
  .settings(name := "my-lib")
  .jvmPlatform(scalaVersions = Seq(scala3))
  .jsPlatform(scalaVersions = Seq(scala3))
  .nativePlatform(scalaVersions = Seq(scala3))
```

- Platform-specific sources go to `src/main/scalajvm/`, `src/main/scalajs/`, `src/main/scalanative/` (no dash).
  sbt-projectmatrix adds these automatically; `scala-jvm`-style folders need manual
  `Compile / unmanagedSourceDirectories` entries.
- Project IDs: the JVM row has no platform suffix when the JVM is a default axis. With Scala 3 rows you get `core3`,
  `coreJS3`, `coreNative3`. Run `sbt projects` to see the real IDs; `.defaultAxes(...)` changes them.

## Scala Native + provider JARs (NativeProviderPlugin)

`NativeProviderPlugin` (requires `ScalaNativePlugin`, never auto-triggered) finds `sn-provider.json` manifests on
`Compile / dependencyClasspathAsJars` and in project resources, extracts the static libraries for the target
platform into `target/native-libs/<classifier>/`, and appends to `nativeConfig.linkingOptions`:

```
existing options ++ -L<extract dir> ++ <each declared binary, absolute path> ++ <deduplicated flags-groups> ++ rpath
```

rpath: macOS `-rpath <dir> -rpath @executable_path`; Linux `-Wl,-rpath,<dir> -Wl,-rpath,$ORIGIN`; Windows none -
after `nativeLink` every extracted `.dll` is copied next to the executable instead.

Plain project:

```scala
lazy val app = (project in file("app"))
  .enablePlugins(NativeProviderPlugin) // ScalaNativePlugin is enabled through `requires`
  .settings(libraryDependencies += "com.kubuszok" % "sn-provider-curl" % "0.4.0")
```

projectMatrix: do not `enablePlugins` on the whole matrix (it would put Scala Native on the JVM and JS rows).
Add the plugin's settings to the native row only:

```scala
.nativePlatform(
  scalaVersions = Seq(scala3),
  settings = NativeProviderPlugin.projectSettings ++ Seq(
    libraryDependencies += "com.kubuszok" % "sn-provider-curl" % "0.4.0"
  )
)
```

Keys (all re-exported by `NativeProviderPlugin.autoImport`):

| Key | Default | Meaning |
|---|---|---|
| `nativeLibPlatform` / `nativeProviderPlatform` | `Platform.host` | Platform to extract / merge flags for (the plugin keeps them in sync) |
| `nativeLibSourceDir` | `None` | Use `<dir>/<classifier>/` directly instead of extracting from JARs |
| `nativeProviderTypes` | `Seq(ProviderType.ScalaNative)` | Manifest types to read |
| `nativeLibExtract`, `nativeLibDir`, `nativeProviderLibDir`, `discoverManifests`, `mergedLinkerFlags` | - | Tasks; `show mergedLinkerFlags` is the quickest debugging aid |

### nativeConfig ordering

The plugin defines `nativeConfig := { val c = nativeConfig.value; c.withLinkingOptions(...) }`, so it composes with
anything defined **before** it. Anything defined **after** it must keep the previous value:

```scala
nativeConfig ~= (_.withEmbedResources(true))                        // fine
nativeConfig := nativeConfig.value.withMultithreading(false)        // fine
nativeConfig := NativeConfig.empty.withLTO(...)                     // drops -L, the .a files and the flags
```

In a projectMatrix this includes settings added by a later, broader `.settings(...)` or
`MatrixAction.ForAll.Configure(...)` block.

## Platform classifiers

`linux-x86_64`, `linux-aarch64`, `macos-x86_64`, `macos-aarch64`, `windows-x86_64`, `windows-aarch64` (desktop:
Scala Native, JNI/Panama, JVM packaging) and `android-aarch64`, `android-armv7`, `android-x86_64` (JNI/Panama only).
In code: `Platform.LinuxX86_64`, ..., `Platform.AndroidArmV7`; `Platform.desktop`, `Platform.android`,
`Platform.host`, `Platform.fromClassifier("macos-aarch64")`. Scala Native triples use `*-pc-windows-msvc` for Windows.

## Gotchas

- **`[native-provider] Could not find native library JARs for platform '<p>' in the classpath.`** -
  `NativeProviderPlugin` is enabled but no dependency carries `native/` entries for that platform. Add a provider
  (with `%`, it has no Scala suffix) or set `nativeLibSourceDir`. Provider dependencies declared on another project
  may not reach this one; add them to every project that links or runs.
- **`ld: library not found for -l<name>` / `undefined reference` at `nativeLink`** although a provider is on the
  classpath - the plugin's settings never reached `nativeConfig`: either they are missing on this row, or a later
  `nativeConfig := ...` without `.value` replaced them. Check with `show <project>/nativeConfig` that
  `-L.../native-libs/<classifier>` is in `linkingOptions`. A library's `@link("x")` annotation adds `-lx` but does
  not extract `libx.a`; the consumer still needs the provider and the plugin.
- **A provider version bump keeps linking the old `.a`** - `nativeLibExtract` reuses
  `target/native-libs/<classifier>/` whenever it contains any native library, without checking which JARs it came
  from (open issue [#29](https://github.com/kubuszok/multiarch-scala/issues/29)). Delete that directory or run
  `clean` after changing provider versions.
- **`[native-provider] Native library collision for platform '<p>': file '<f>' is bundled by 2 providers`** - two
  providers ship the same file name; classpath order would pick one silently. Depend on only one of them. When both
  owners are the same artifact at two versions, the cause is a dependency conflict or a stale JAR, not two providers
  ([#33](https://github.com/kubuszok/multiarch-scala/issues/33)).
- **Windows binary links, then exits with `0xC0000135` (STATUS_DLL_NOT_FOUND)** - the import libraries (`.lib`)
  linked, but the matching `.dll` is not next to the `.exe`. The plugin copies only DLLs that the provider JAR
  contains; the provider must ship them in its `windows-*` folders.
- **`OutOfMemoryError` while linking with `withEmbedResources(true)`** - Scala Native embeds every classpath
  resource, provider JARs included. Restrict with
  `.withResourceIncludePatterns(Seq("**.json", "**.png"))`.
- **sbt 2.x: `nativeLink` on another machine uses this machine's clang path** (e.g. `D:\usr\bin\clang` on Windows) -
  sbt 2 caches task results, remote cache included, and `nativeConfig` holds absolute toolchain paths. Make the final
  value uncached, as the last setting of each native row: `nativeConfig := Def.uncached(nativeConfig.value)`.
- **`TypeError: package scala.scalajs.js does not have a member method async`** while compiling the JS row - seen
  with Scala 3.8.x and an sbt-scalajs older than 1.20, whose Scala.js library is older than the one the Scala 3
  library expects. Upgrade sbt-scalajs.
- **Scala Native 0.4 style `Zone { implicit z => ... }` fails with "Missing parameter type"** - Scala Native 0.5
  passes the zone as a context function: `Zone { val p = alloc[Float](n) }`.
