---
name: multiarch-scala-panama
description: >-
  Writing Panama FFM (foreign function) code once for the desktop JVM and Android with multiarch-scala's
  multiarch-panama-api and multiarch-panama-jdk modules (package multiarch.panama: PanamaProvider, Panama.provider,
  Panama.detect, JdkPanama over java.lang.foreign, PanamaPortProvider over PanamaPort com.v7878.foreign). Covers the
  dependencies (Scala 3 only), path-dependent types (p.MemorySegment, p.Arena, p.Linker, p.SymbolLookup,
  p.FunctionDescriptor), downcallHandle / upcallStub, loading the library with NativeLibLoader, and failures such as
  ClassNotFoundException multiarch.panama.JdkPanama$, NoClassDefFoundError com/v7878/foreign, and
  NoSuchFieldError SDK_INT_FULL on Android. Use when FFI code must run on both JDK 22+ and Android.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Panama FFM on desktop and Android (multiarch-panama-api / -jdk)

Version: written for multiarch-scala **0.4.0**. Check the version in the user's build; if it differs, read
<https://github.com/kubuszok/multiarch-scala/tree/0.4.0/panama-api> and
<https://github.com/kubuszok/multiarch-scala/tree/0.4.0/panama-jdk> at that tag.

Android has no `java.lang.foreign`. [PanamaPort](https://github.com/vova7878/PanamaPort) (`com.v7878.foreign`) is a
backport with the same shape, but code written against one package does not compile against the other. These two
modules put a trait in between, so FFI code is written once:

| Module | Artifact | Contents |
|---|---|---|
| API | `"com.kubuszok" %% "multiarch-panama-api" % "0.4.0"` | `trait PanamaProvider`, `object Panama` (run-time selection), `object PanamaPortProvider` (Android implementation) |
| JDK | `"com.kubuszok" %% "multiarch-panama-jdk" % "0.4.0"` | `object JdkPanama` over `java.lang.foreign` (needs JDK 22+ at run time) |

Both are Scala 3 only (`_3`) and JVM only; the API module is JDK 17 bytecode so it also runs on Android.
Neither depends on `multiarch-core`; add it for `NativeLibLoader`.

## Dependencies per target

- Desktop JVM: `multiarch-panama-api`, `multiarch-panama-jdk`, `multiarch-core`, a `pnm-provider-*` JAR, plus
  `fork := true` and `javaOptions += "--enable-native-access=ALL-UNNAMED"`.
- Android: `multiarch-panama-api`, `multiarch-core`, the `pnm-provider-*-android` JAR, and `AndroidPlugin` (skill
  `multiarch-scala-android-build`). The plugin downloads the PanamaPort AARs (version `v0.1.0`) from Maven Central and
  puts their classes on the compile classpath and into the dex; there is no sbt dependency to declare for them.
  Do not put `multiarch-panama-jdk` into the APK.

## Writing FFI code

Take the provider as a value and use its path-dependent types. Method names differ from `java.lang.foreign` where
an extension would clash (`findOrThrow`, `segAddress`, `allocateString`, `arenaClose`, ...).

```scala
import java.lang.invoke.MethodHandle
import multiarch.panama.{ Panama, PanamaProvider }

final class MyLib(val p: PanamaProvider) {
  private val lib: p.SymbolLookup =
    p.SymbolLookup.libraryLookup(multiarch.core.NativeLibLoader.load("mylib"), p.Arena.global())

  private val hAdd: MethodHandle = p.Linker.nativeLinker().downcallHandle(
    lib.findOrThrow("my_add"),
    p.FunctionDescriptor.of(p.JAVA_INT, p.JAVA_INT, p.JAVA_INT)
  )

  def add(a: Int, b: Int): Int = hAdd.invoke(a, b).asInstanceOf[Int]
}

val myLib = new MyLib(Panama.provider) // JdkPanama on JDK 22+, PanamaPortProvider when java.lang.foreign is absent
```

Surface of `PanamaProvider` (see
[PanamaProvider.scala](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/panama-api/src/main/scala/multiarch/panama/PanamaProvider.scala)
for the full list):

| Area | Members |
|---|---|
| `p.MemorySegment` | `NULL`, `ofAddress`, `ofBuffer`, `copyFromBytes`/`copyToBytes` (also `Floats`, `Ints`, `Shorts`) |
| segment extensions | `segAddress`, `segReinterpret`, `segSlice`, `segAsByteBuffer`, `segCopyFrom`, `get/setInt`, `Long`, `Float`, `Double`, `Address`, `getIntAtIndex`, `getString`, `isNull` |
| `p.Arena` | `ofConfined()`, `ofAuto()`, `global()`; extensions `allocate`, `allocateElems`, `allocateLayout`, `allocateString`, `arenaClose()` |
| `p.Linker` | `nativeLinker()`; extensions `downcallHandle(symbol, desc)`, `upcallStub(target, desc, arena)` |
| `p.SymbolLookup` | `libraryLookup(path, arena)`, `loaderLookup()`; extensions `findSymbol(name): Option[...]`, `findOrThrow(name)` |
| `p.FunctionDescriptor` | `of(ret, args*)`, `ofVoid(args*)` |
| layouts | `JAVA_INT`, `JAVA_FLOAT`, `JAVA_BYTE`, `JAVA_LONG`, `JAVA_DOUBLE`, `ADDRESS`, `structLayout(...)`, `layoutByteSize`, `intSize` ... |

`Panama.detect(jdkClass, androidClass)` takes the class names of the two implementations, so a project can supply
its own providers.

## Gotchas

- **`ClassNotFoundException: multiarch.panama.JdkPanama$`** from `Panama.provider` on a desktop JVM -
  `multiarch-panama-jdk` is missing from the runtime classpath.
- **`NoClassDefFoundError: com/v7878/foreign/...`** - `Panama.provider` chose `PanamaPortProvider` outside an
  Android build: either the JVM is older than the one with `java.lang.foreign` (use JDK 22+), or the APK was not
  built by `AndroidPlugin`, which is what adds PanamaPort.
- **Android app dies with `NoSuchFieldError: SDK_INT_FULL` on API 26-35** - PanamaPort reads
  `Build.VERSION.SDK_INT_FULL` (API 36) and needs a D8 new enough to rewrite it. multiarch 0.4.0 dexes with
  build-tools 35's D8, which leaves the read in place; after 0.4.0 `androidDex` downloads R8/D8 9.1.56 instead. Use
  a newer snapshot for Android.
- **JDK 22+ prints `WARNING: A restricted method in java.lang.foreign.Linker has been called`** (later JDKs refuse)
  - add `--enable-native-access=ALL-UNNAMED` to `javaOptions` of `run` and `Test`. Release packages built by
  `MultiArchJvmReleasePlugin` already pass it.
