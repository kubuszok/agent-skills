# JVM release packaging (MultiArchJvmReleasePlugin, multiarch-scala 0.4.0)

Verified against
[JvmPackaging.scala](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/plugin/src/main/scala/multiarch/sbt/JvmPackaging.scala)
and [MultiArchJvmReleasePlugin.scala](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/plugin/src/main/scala/multiarch/sbt/MultiArchJvmReleasePlugin.scala).

`MultiArchJvmReleasePlugin` (requires `JvmPlugin`, never auto-triggered) builds release archives for any of the 6
desktop platforms from one machine: it downloads each target's JDK, jlinks a runtime, and wraps the app in a
[Roast](https://github.com/fourlastor-alexandria/roast) native launcher. Its keys can also be added without the
AutoPlugin through `JvmPackaging.jvmSettings` (simple mode) and `JvmPackaging.distSettings` (distribution mode).

```scala
import multiarch.sbt.Platform

lazy val app = (project in file("app"))
  .enablePlugins(MultiArchJvmReleasePlugin)
  .settings(
    Compile / mainClass := Some("com.example.Main"),
    releaseTargets := Map(
      Platform.LinuxX86_64   -> "https://cdn.azul.com/zulu/bin/<zulu-jdk>-linux_x64.tar.gz",
      Platform.MacosAarch64  -> "https://cdn.azul.com/zulu/bin/<zulu-jdk>-macosx_aarch64.tar.gz",
      Platform.WindowsX86_64 -> "https://cdn.azul.com/zulu/bin/<zulu-jdk>-win_x64.zip"
    )
  )
```

| Task | Output |
|---|---|
| `releasePackage` | `target/release-package/<app>/` with `bin/<app>`, `bin/<app>.bat`, `lib/*.jar`, `native/` - needs a JDK on the user's machine |
| `releasePlatform <classifier>` | `target/release-dist/<app>-<classifier>.tar.gz` (`.zip` for Windows; macOS contains `<app>.app`) |
| `releaseAll` | one archive per entry of `releaseTargets` |

| Key | Default | Notes |
|---|---|---|
| `releaseTargets` | `Map.empty` | `Platform -> JDK archive URL` (`.tar.gz`, `.tgz` or `.zip`); must be a full JDK with `jmods/` |
| `releaseAppName` | `name.value` | archive, launcher and bundle name |
| `releaseJlinkModules` | `java.base, java.desktop, java.logging, java.management, jdk.unsupported, jdk.zipfs` | add e.g. `java.net.http` if the app needs it |
| `releaseVmArgs` | `Seq.empty` | `--enable-native-access=ALL-UNNAMED` is always added |
| `releaseUseZgc` | `true` | Roast `useZgcIfSupportedOs` |
| `releaseRunOnFirstThread` | `true` | macOS only (`-XstartOnFirstThread`, needed by GLFW-style windowing) |
| `releaseMacOsBundleId` | `com.app.<name>` | `Info.plist` |
| `releaseMacOsIcon` | `None` | `.icns` file |
| `releaseNativeLibDirs` | `Seq.empty` | directories whose `.so`/`.dylib`/`.dll` are copied into `native/`; then `-Djava.library.path=native` is set |
| `releaseCrossNativeLibDir` | `None` | `<dir>/<classifier>/` per platform, falling back to `releaseNativeLibDirs` |
| `releaseRoastVersion` | `1.5.0` | |
| `releaseCacheDir` | `~/.cache/sbt-multiarch-scala` | JDK and Roast downloads, keyed by file name |

Provider JARs (`pnm-provider-*`, `jni-provider-*`) are dependencies like any other and go into `app/`;
`NativeLibLoader` extracts from them at run time, so `releaseNativeLibDirs` is only for libraries that are not in
a provider.

## Gotchas

- **`releasePackage requires Compile / mainClass to be set`** (also for `releasePlatform` / `releaseAll`) - set
  `Compile / mainClass` explicitly.
- **`Platform 'linux-aarch64' not in releaseTargets. Available: ...`** - the argument is a classifier and must be a
  key of `releaseTargets`.
- **`jmods directory not found in target JDK`** - the URL points at a JRE, or a JDK build without `jmods/`. Use a
  full JDK archive.
- **Archive for another OS is much larger than for the host OS** - jlink runs only when target OS == host OS; for
  another OS the whole target JDK (`bin`, `lib`, `conf`, `legal`) is copied, and `releaseJlinkModules` is ignored.
  Build each OS's archive on that OS if size matters.
- **A Swing/AWT/JavaFX app hangs on macOS** - the default `releaseRunOnFirstThread := true` starts the JVM with
  `-XstartOnFirstThread`, which those toolkits do not expect. Set it to `false` for them.
- **macOS refuses to run the app** - on a macOS build host the launcher, `.dylib`s and the `.app` are only
  ad-hoc signed (`codesign --sign -`); archives built on Linux/Windows are not signed at all. Real distribution needs
  your own signing and notarisation.
- **A re-uploaded JDK is not picked up** - downloads are cached by file name in `releaseCacheDir`; delete the
  cached archive and its `extracted-<classifier>` directory.
