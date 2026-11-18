---
name: multiarch-scala-cross-native-testing
description: >-
  Cross-compiling and link-testing Scala Native binaries for all 6 desktop platforms (linux, macos, windows on x86_64
  and aarch64) from one machine with zig, using multiarch-scala's MultiArchNativeReleasePlugin, zigCrossTarget,
  ProjectMatrixOps.withCrossNative, NativeCrossAxis and ZigCross.crossSettings. Covers prerequisites (zig on the sbt
  server's PATH, provider JARs with every platform), generated project IDs, target/zig-wrappers,
  target/native-libs/<classifier>, what can and cannot be tested without the target machine, and link failures on
  cross targets (cannot find -lstdc++, unresolved external symbol on Windows, missing cross rows). Use before pushing
  Scala Native changes that CI builds on several runners.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Cross-linking Scala Native with zig

Version: written for multiarch-scala **0.4.0** (unchanged on master as of 53d7ca1). Check `sbt-multiarch-scala` in
the user's `project/plugins.sbt`; if it differs, read
<https://github.com/kubuszok/multiarch-scala/blob/0.4.0/plugin/src/main/scala/multiarch/sbt/ProjectMatrixOps.scala>
and `MultiArchNativeReleasePlugin.scala` at that tag.

Linking is where most cross-platform Scala Native builds break: a missing `.a` for one platform, a flag missing
from one manifest, a Windows-only symbol. With `zig cc` as the C compiler, one machine can link the binary for every
desktop target. The binaries cannot be run there, but a link that succeeds locally rarely fails in CI.

## Prerequisites

- `zig` on the `PATH` **of the sbt server** (`zig version` must exit 0). Restart the server after installing it.
- Provider JARs that contain every target platform (e.g. `sn-provider-curl` ships all 6). Extraction for a target
  fails if the provider lacks it.
- The NativeProviderPlugin setup from the `multiarch-scala-setup` skill.
- A Unix-like build host: the generated wrappers are `#!/bin/sh` scripts.

## Option 1: `withCrossNative` on a projectMatrix (recommended)

```scala
import multiarch.sbt.ProjectMatrixOps._

lazy val app = (projectMatrix in file("app"))
  .jvmPlatform(scalaVersions = Seq(scala3))
  .nativePlatform(scalaVersions = Seq(scala3), settings = NativeProviderPlugin.projectSettings)
  .settings(libraryDependencies += "com.kubuszok" % "sn-provider-curl" % "0.4.0")
  .withCrossNative(scala3)
```

`withCrossNative(scalaVersion)` adds one row per desktop platform. Each row carries `NativeCrossAxis(platform)`,
enables `ScalaNativePlugin`, `NativeProviderPlugin` and `MultiArchNativeReleasePlugin`, and sets
`zigCrossTarget := Some(platform)` - except the **host** row, which gets `None` and uses the normal toolchain.
Without zig only the host row is added (the build still loads). The host row exists in addition to the
`.nativePlatform` row.

Project IDs come from sbt-projectmatrix: matrix name + `NativeCrossAxis` suffix + platform suffix + Scala suffix,
minus the matrix's default axes. With the default axes and Scala 3 that is, for example,
`appNativeLinuxX86_64Native3`; with `.defaultAxes(VirtualAxis.jvm, VirtualAxis.scalaABIVersion(scala3))` it is
`appNativeLinuxX86_64Native`. Always check with `sbt projects`.

| Platform | `NativeCrossAxis` suffix | Scala Native triple | zig target |
|---|---|---|---|
| `linux-x86_64` | `NativeLinuxX86_64` | `x86_64-unknown-linux-gnu` | `x86_64-linux-gnu` |
| `linux-aarch64` | `NativeLinuxAarch64` | `aarch64-unknown-linux-gnu` | `aarch64-linux-gnu` |
| `macos-x86_64` | `NativeMacosX86_64` | `x86_64-apple-darwin` | `x86_64-macos` |
| `macos-aarch64` | `NativeMacosAarch64` | `aarch64-apple-darwin` | `aarch64-macos` |
| `windows-x86_64` | `NativeWindowsX86_64` | `x86_64-pc-windows-msvc` | `x86_64-windows-gnu` |
| `windows-aarch64` | `NativeWindowsAarch64` | `aarch64-pc-windows-msvc` | `aarch64-windows-gnu` |

Use `withCrossNative` on applications only; a library has nothing to link (see `multiarch-scala-library-vs-app`).

## Option 2: one project for one target

```scala
import multiarch.sbt.Platform

lazy val appLinux = (project in file("app-linux"))
  .enablePlugins(MultiArchNativeReleasePlugin) // brings NativeProviderPlugin and ScalaNativePlugin
  .settings(zigCrossTarget := Some(Platform.LinuxX86_64))
```

`ZigCross.crossSettings(platform)` gives the same `nativeConfig` and platform settings without the AutoPlugin
(add `NativeProviderPlugin` yourself). With a target set, the plugin writes `target/zig-wrappers/zig-cc-<classifier>`
and `zig-cxx-<classifier>` (`exec zig cc -target <zig target> "$@"`), sets them as clang/clang++, sets the target
triple, and points `nativeLibPlatform` / `nativeProviderPlatform` at the target.

## Workflow

```bash
sbt projects                                  # find the generated IDs
sbt appNative3/nativeLink                     # host
sbt appNativeLinuxX86_64Native3/nativeLink    # one cross target
```

Before pushing: compile every platform row, link the host binary, link every cross row, run the tests that can
run on the host. Afterwards `target/native-libs/<classifier>/` (per row) shows what was extracted for that target.

What this proves: Scala code compiles for each platform, provider manifests cover every platform, flags are
complete and in a valid order. What it cannot prove: run-time behaviour on other platforms, macOS first-thread
requirements, DLL search paths on Windows, glibc version differences. Android is not a zig target.

## Gotchas

- **No cross rows in `sbt projects`, only the host row** - zig was not on the `PATH` when the sbt server started.
  Fix `PATH`, then `sbt shutdown` (or exit) and start again; `reload` is not enough if the server's environment is
  stale.
- **Cross rows fail to link while `appNative3` links** - settings passed to `.nativePlatform(settings = ...)` apply
  only to that row; the rows from `withCrossNative` get the matrix-level `.settings(...)` and the three plugins.
  Put provider dependencies and `nativeConfig` tweaks at matrix level (or in a `MatrixAction` for native rows).
- **`Could not find native library JARs for platform 'linux-aarch64'`** on a cross row - the provider does not
  contain that platform. `unzip -l <provider.jar> | grep linux-aarch64` to check.
- **`cannot find -lstdc++`** on a Linux cross target - zig ships libc++, not libstdc++. Link `-lc++` on zig rows
  (`zigCrossTarget` exists only where `MultiArchNativeReleasePlugin` is enabled, hence `.?`):
  ```scala
  nativeConfig := {
    val c     = nativeConfig.value
    val isZig = zigCrossTarget.?.value.flatten.isDefined
    val cxx   = if (isZig || Platform.host.isMac) "-lc++" else "-lstdc++"
    c.withLinkingOptions(c.linkingOptions :+ cxx)
  }
  ```
- **`unresolved external symbol` on a Windows target** - the import library or the `.a` for Windows is missing or
  named differently. The plugin copies `libfoo.a` to `foo.lib` (and `libfoo.lib` to `foo.lib`) after extracting
  for Windows; the manifest's `binary` must match a file the JAR contains.
- **Symbols for the wrong architecture** - set `nativeLibPlatform` and `nativeProviderPlatform` together;
  `MultiArchNativeReleasePlugin` and `ZigCross.crossSettings` do it for you, hand-written settings often forget one.
- **The first cross link is slow** - zig builds and caches libc for each target on first use.
