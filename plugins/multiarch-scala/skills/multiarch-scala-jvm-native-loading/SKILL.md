---
name: multiarch-scala-jvm-native-loading
description: >-
  Loading native shared libraries (.so, .dylib, .dll) on the JVM and Android with multiarch-core's
  multiarch.core.NativeLibLoader (load, loadAll, loadConfigs, ProviderType.Panama / ProviderType.Jni) from
  pnm-provider / jni-provider JARs, for Panama FFM (java.lang.foreign SymbolLookup.libraryLookup) and JNI
  (System.load). Covers the resolution order (java.library.path, manifest-v2 index, legacy native/<classifier>/
  layout, Android class loader), fork := true and --enable-native-access=ALL-UNNAMED, dev overrides, and failures
  such as UnsatisfiedLinkError "Cannot find native library", android.jar on the test classpath making the host
  look like android-aarch64, and NoSuchMethodError Path.of on Android. Use instead of hand-written OS/arch
  detection, resource extraction or System.loadLibrary.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Loading native libraries on the JVM with NativeLibLoader

Version: written for multiarch-scala **0.4.0** (`"com.kubuszok" %% "multiarch-core" % "0.4.0"`, Scala 2.12, 2.13
and 3, JVM only). Check the version in the user's build; if it differs, read
<https://github.com/kubuszok/multiarch-scala/blob/0.4.0/core/src/main/scala/multiarch/core/NativeLibLoader.scala>
at that tag. Fixes marked "after 0.4.0" are in snapshots such as `0.4.0-20-ga3e0f08-SNAPSHOT`.

## The rule

Do not write OS/arch detection, `lib`-prefix/extension mapping, temp-file extraction or `System.loadLibrary` for
libraries that come from provider JARs. `NativeLibLoader` already does all of that, thread-safely, for the 6
desktop and 3 Android classifiers.

## Dependencies

```scala
libraryDependencies ++= Seq(
  "com.kubuszok" %% "multiarch-core" % "0.4.0",               // the loader
  "com.kubuszok" %  "pnm-provider-mylib-desktop" % "1.0.0"     // provider JAR: no Scala suffix, plain %
)
```

`multiarch-core` is not a dependency of `multiarch-panama-jdk`; add it explicitly. Provider JARs are best added to
every project that runs or tests the code, not only to a library it depends on.

## API

```scala
import multiarch.core.{ NativeLibLoader, ProviderType }

val path: java.nio.file.Path = NativeLibLoader.load("mylib") // logical name, not "libmylib.so"

NativeLibLoader.loadAll(ProviderType.Jni)                        // System.load every binary of every jni-provider.json
NativeLibLoader.loadConfigs(ProviderType.Panama, Set("mylib"))   // only configs with these config-name values
```

- `load` returns the path and does **not** call `System.load` - pass it to Panama or to `System.load` yourself.
- `loadAll` / `loadConfigs` read the given manifest type (`ProviderType.Jni` -> `jni-provider.json`,
  `ProviderType.Panama` -> `pnm-provider.json`), skip `stub` entries, and call `System.load` on each binary.
- Name mapping: Windows `mylib.dll`; elsewhere `System.mapLibraryName` (`libmylib.so`, `libmylib.dylib`).
- Each library is extracted once per JVM into a `multiarch-native-*` temp directory deleted on exit; results are
  cached by logical name.

Panama (`java.lang.foreign`, JDK 22+):

```scala
import java.lang.foreign.*

val lookup = SymbolLookup.libraryLookup(NativeLibLoader.load("mylib"), Arena.global())
val myFunction = Linker.nativeLinker().downcallHandle(
  lookup.find("my_function").orElseThrow(),
  FunctionDescriptor.of(ValueLayout.JAVA_INT, ValueLayout.ADDRESS)
)
```

For code that must also run on Android, use `multiarch-panama-api` instead of `java.lang.foreign` directly (skill
`multiarch-scala-panama`).

JNI:

```scala
System.load(NativeLibLoader.load("mylib").toAbsolutePath.toString)
```

## Resolution order of `load(name)`

1. `java.library.path` - every directory (split on the path separator); a dev override always wins.
2. Manifest-v2 index - every `jni-provider.json` / `pnm-provider.json` that declares `provider-artifact` and
   `provider-version`; extracts `native/<artifact>/<version>/<classifier>/<file>`. Two different providers owning
   the same file throw an `UnsatisfiedLinkError` with a collision report.
3. Legacy layout `native/<classifier>/<file>` (prints `[multiarch] '<file>' resolved via legacy layout` once).
4. On Android: the class loader's `findLibrary`, then `System.loadLibrary`.
5. `UnsatisfiedLinkError` listing what was searched:

```
Cannot find native library 'libmylib.so' (logical name: 'mylib').
  Searched java.library.path: ...
  Searched classpath resource: native/<artifact>/<version>/linux-x86_64/libmylib.so (manifest v2)
  Searched classpath resource: native/linux-x86_64/libmylib.so (legacy layout)
  Note: ...
  Host platform: linux-x86_64
```

The host classifier is `<os>-<arch>` from `os.name` / `os.arch`; the OS is `android` whenever the class
`android.app.Activity` can be loaded.

## Build settings

```scala
fork := true,                                           // also covers Test / fork
javaOptions += "--enable-native-access=ALL-UNNAMED"     // Panama: JDK 22+ warns without it, later JDKs deny
```

Dev override with a locally built library: `javaOptions += s"-Djava.library.path=${baseDirectory.value}/native/target/release"`.

## Gotchas

- **`UnsatisfiedLinkError: Cannot find native library ...` with `Host platform: android-aarch64` on a desktop** -
  the Android SDK's `android.jar` stub is on the runtime/test classpath (for example because a module compiles
  against it and the jar leaks through `dependsOn`), so `android.app.Activity` loads and the loader looks for
  Android binaries. Keep `android.jar` compile-only: filter it out of `Test / fullClasspath`, and for `run` also
  `Runtime / fullClasspath` and (sbt 2.x forks `run` with it) `Runtime / fullClasspathAsJars`:

  ```scala
  Test / fullClasspath := (Test / fullClasspath).value.filterNot(_.data.getName == "android.jar")
  ```
  (sbt 2.x: wrap in `Def.uncached` and get the file name through `fileConverter.value.toPath(e.data)`.)
- **`UnsatisfiedLinkError` that names only the legacy path** - no manifest on the classpath owns that file for this
  platform: the provider JAR is missing from this project, does not cover the host classifier, or the name passed
  to `load` differs from the file (`load("mylib")` looks for `libmylib.so`, not `mylib.so`).
- **Works with `fork := true`, fails without it** - the loader reads manifests and resources through its own class
  loader; under sbt's layered class loaders the provider JARs may sit in a layer it cannot see
  ([#36](https://github.com/kubuszok/multiarch-scala/issues/36)). Always fork.
- **`NoSuchMethodError: java.nio.file.Path.of` on Android below API 34** - multiarch-core 0.4.0 calls `Path.of`;
  fixed after 0.4.0 (`Paths.get`). Use a newer snapshot for Android apps with `minSdk` < 34.
- **`Failed to parse jni-provider.json manifest at <url>`** - from `loadAll` / `loadConfigs`; a provider JAR has a
  corrupt manifest. Re-download or fix the provider.
- **Library loads but `lookup.find("sym")` is empty** - the library does not export that symbol
  (`nm -D libmylib.so | grep sym`, `nm -gU` on macOS); check C++ name mangling and `extern "C"`.
- **munit `intercept[UnsatisfiedLinkError]` does not catch it** - it is a `LinkageError`, which munit treats as fatal.
  Use `try`/`catch` in tests that expect it.
