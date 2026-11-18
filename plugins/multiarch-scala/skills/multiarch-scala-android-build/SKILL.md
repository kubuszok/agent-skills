---
name: multiarch-scala-android-build
description: >-
  Building Android APKs from sbt without Gradle using multiarch-scala's AndroidPlugin (multiarch.sbt.AndroidPlugin,
  AndroidBuild): SDK auto-download (ANDROID_HOME, ANDROID_SDK_ROOT, androidSdkCacheDir), androidDex,
  androidPackage, androidSign, androidInstall, androidMinSdk / androidTargetSdk / androidBuildToolsVersion,
  androidR8Version, AndroidManifest.xml in src/main/resources, src/main/scala-android sources, native .so files from
  pnm-provider / jni-provider JARs into lib/<abi>, PanamaPort for Panama FFM, assets vs Java resources. Covers
  failures such as NoSuchFieldError SDK_INT_FULL, VerifyError wide register index, "AndroidManifest.xml not found",
  "adb not found", missing android.* classes on first build, and getResource returning null on Android.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Android APKs with AndroidPlugin

Version: written for multiarch-scala **0.4.0**. Check `sbt-multiarch-scala` in the user's `project/plugins.sbt`; if it
differs, read
<https://github.com/kubuszok/multiarch-scala/blob/0.4.0/plugin/src/main/scala/multiarch/sbt/AndroidBuild.scala> at
that tag. Android support changed after 0.4.0 (marked below); snapshots such as `0.4.0-20-ga3e0f08-SNAPSHOT`
contain those changes, and Android apps using PanamaPort or `NativeLibLoader` need them.

`AndroidPlugin` (requires `JvmPlugin`, never auto-triggered) runs the Android toolchain directly from sbt: D8 for
dex, aapt2, zipalign, apksigner, adb. No Gradle, no Android Gradle Plugin.

```
androidDex -> androidPackage -> androidSign -> androidInstall   (each runs the previous one)
```

## Setup

```scala
lazy val androidApp = (project in file("android"))
  .enablePlugins(AndroidPlugin)
  .settings(
    Compile / mainClass := Some("com.example.MainActivity"),
    androidSdkCacheDir  := (ThisBuild / baseDirectory).value / "android-sdk", // default: <project dir>/android-sdk
    libraryDependencies += "com.example" % "pnm-provider-mylib-android" % "1.0.0"
  )
```

`src/main/resources/AndroidManifest.xml` is required:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.example.myapp">
  <application android:label="My App" android:hasCode="true">
    <activity android:name=".MainActivity" android:exported="true">
      <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
      </intent-filter>
    </activity>
  </application>
</manifest>
```

The plugin is a plain sbt project feature; a projectMatrix row can use the same settings through
`.settings(multiarch.sbt.AndroidBuild.taskSettings *)` plus `AndroidBuild.androidSdkCacheDir := ...` (that is what
`enablePlugins(AndroidPlugin)` adds, together with the `scala-android` source directory below).

## Keys

| Key (autoImport) | Default | Notes |
|---|---|---|
| `androidSdkCacheDir` | `baseDirectory / "android-sdk"` | where the SDK is downloaded when no env var points at one |
| `androidSdkRoot` | task | `ANDROID_HOME`, then `ANDROID_SDK_ROOT`, then `androidSdkCacheDir`; downloads command-line tools + `platforms;android-35` + `build-tools;35.0.0` when none exists (licenses auto-accepted) |
| `androidMinSdk` | `26` | Android 8.0, PanamaPort's minimum |
| `androidTargetSdk` | `35` | also selects `platforms/android-<n>/android.jar` |
| `androidBuildToolsVersion` | `"35.0.0"` | aapt2, zipalign, apksigner |
| `androidDex`, `androidPackage`, `androidSign`, `androidInstall` | tasks | see below |
| `AndroidBuild.androidR8Version` (not auto-imported) | `"9.1.56"` | **after 0.4.0**: R8/D8 JAR downloaded from Google Maven for dexing |
| `AndroidBuild.androidR8Rules` (not auto-imported) | `None` | declared but not used by `androidDex` (no shrinking) |

What the plugin adds to the project: `android.jar` and the PanamaPort JARs to `Compile / unmanagedJars`,
`fork := true`, and `src/main/scala-android/` as a source directory when the SDK is already present.

## What each task does

- `androidDex`: compiles, merges classes from `fullClasspath` into one JAR (skipping `android.jar`, `META-INF/`,
  `java/*` classes, and JARs whose name contains `scribe`), runs D8 with `--min-api androidMinSdk`; output
  `classes*.dex` in `<crossTarget>/android/dex/`. 0.4.0 uses `build-tools/35.0.0/lib/d8.jar`; after 0.4.0 the pinned
  R8 `androidR8Version`.
- `androidPackage`: aapt2 links the manifest; **your project's resources become APK `assets/`** (without
  `AndroidManifest.xml`, `lib/`, `META-INF/`); adds all dex files; adds `src/main/resources/lib/<abi>/*.so`; adds
  `.so` files from dependency JARs (`native/android-<arch>/` or `native/<artifact>/<version>/android-<arch>/`)
  as `lib/arm64-v8a`, `lib/armeabi-v7a`, `lib/x86_64` (from `android-aarch64`, `android-armv7`, `android-x86_64`);
  **after 0.4.0** also copies dependency JARs' Java resources to the APK root; then zipalign.
- `androidSign`: creates `<crossTarget>/android/debug.keystore` (password `android`, alias `androiddebugkey`) once
  and signs `app-debug.apk`. Debug signing only.
- `androidInstall`: `adb install -r` from `<sdk>/platform-tools/adb`.

## Gotchas

- **App crashes on API 26-35 with `NoSuchFieldError: ... SDK_INT_FULL`** (PanamaPort) - build-tools 35's D8 does not
  backport PanamaPort's `Build.VERSION.SDK_INT_FULL` reads. Fixed after 0.4.0 by dexing with R8/D8 9.1.56; use a
  newer snapshot. On 0.4.0 the app only runs on API 36+ devices.
- **`NoSuchMethodError: java.nio.file.Path.of` from `NativeLibLoader` on devices below API 34** - multiarch-core
  0.4.0; fixed after 0.4.0.
- **`getResourceAsStream` returns `null` on the device for a resource that works on desktop** - the project's own
  resources are packaged as `assets/` and must be read with `context.getAssets.open(path)`. Resources inside
  dependency JARs reach the APK root (where `ClassLoader.getResource` finds them) only after 0.4.0; on 0.4.0 they
  are dropped.
- **First build fails with `object android is not a member of package`** (or `scala-android` sources are ignored)
  - `android.jar` and `src/main/scala-android/` are added only when the SDK already exists, and the source
  directory is decided when the build loads. Run `androidSdkRoot` once (it downloads the SDK), then `reload`.
- **`AndroidManifest.xml not found at <dir> — create it in src/main/resources/`** - the manifest is read from
  `Compile / resourceDirectory`.
- **`adb not found at <sdk>/platform-tools/adb — install platform-tools via sdkmanager`** - the automatic download
  installs only the platform and build-tools. Install `platform-tools`, or point `ANDROID_HOME` at a full SDK.
- **`VerifyError: ... wide register index out of range`** at start-up - D8 mishandles some Scala 3 lambda bytecode;
  it was seen with scribe, whose JARs are therefore left out of the dex. Route logging to `android.util.Log` on
  Android. If another library triggers it, it must be kept out of the Android classpath.
- **Two providers ship the same `lib/<abi>/libx.so`** - APK packaging keeps the first one silently; there is no
  collision check on Android ([#32](https://github.com/kubuszok/multiarch-scala/issues/32)). Depend on one.
- **Each Android project downloads its own SDK** - the default cache is per project; set
  `androidSdkCacheDir := (ThisBuild / baseDirectory).value / "android-sdk"` or `ANDROID_HOME`. Add the directory,
  `*.apk` and `*.keystore` to `.gitignore`.
- **`UnsatisfiedLinkError` for a provider library on a device** - the provider has no `.so` for the device ABI
  (arm64 phones need `android-aarch64`, most emulators `android-x86_64`); check the JAR with
  `unzip -l <jar> | grep android-`.
- **Desktop tests resolve Android binaries after adding Android code to a shared module** - `android.jar` reached
  a desktop runtime classpath; see the `multiarch-scala-jvm-native-loading` skill.
