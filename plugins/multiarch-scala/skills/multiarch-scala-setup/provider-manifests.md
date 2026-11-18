# Provider JARs and manifests (multiarch-scala 0.4.0)

A provider is a plain JAR (no Scala code, no Scala suffix) with native libraries under `native/` and one manifest at
the JAR root. Verified against
[ProviderManifest.scala](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/core/src/main/scala/multiarch/core/ProviderManifest.scala),
[ProviderManifestCodec.scala](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/core/src/main/scala/multiarch/core/ProviderManifestCodec.scala)
and [NativeExtract.scala](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/core/src/main/scala/multiarch/core/NativeExtract.scala).

## Manifest file name = provider type

| File | `ProviderType` | Libraries | Used by |
|---|---|---|---|
| `sn-provider.json` | `ScalaNative` | static `.a` / `.lib` | `NativeProviderPlugin` at link time |
| `jni-provider.json` | `Jni` | shared `.so` / `.dylib` / `.dll` | `NativeLibLoader` at run time, `AndroidPlugin` |
| `pnm-provider.json` | `Panama` | shared `.so` / `.dylib` / `.dll` | `NativeLibLoader` at run time, `AndroidPlugin` |

JNI and Panama manifests have the same format; the separate names keep the static and dynamic variants of one
library from being mixed up. One JAR carries at most one manifest. Naming convention for artifacts:
`sn-provider-<lib>`, `jni-provider-<lib>`, `pnm-provider-<lib>` (often with `-desktop` / `-android` suffixes).

## Format

```json
{
  "provider-schema-version": "0.2.0",
  "provider-name": "mylib",
  "provider-artifact": "pnm-provider-mylib-desktop",
  "provider-version": "1.2.0",
  "bundles": ["linux-x86_64/libmylib.so", "macos-aarch64/libmylib.dylib", "windows-x86_64/mylib.dll"],
  "configs": [
    {
      "config-name": "mylib",
      "linux-x86_64":   { "binary": "libmylib.so" },
      "macos-aarch64":  { "binary": "libmylib.dylib" },
      "windows-x86_64": { "binary": "mylib.dll" }
    }
  ]
}
```

- Top level: `provider-schema-version`, `provider-name`, `configs` (v1, schema `0.1.0`); `provider-artifact`,
  `provider-version`, `bundles` are the **v2** additions (schema `0.2.0`), read by multiarch 0.4.0 and later.
- `configs[*]`: `config-name` plus one object per platform classifier.
- Per platform: `binary` (file to extract/link/load), `stub` (SN only: archive that only satisfies the linker),
  `flags-groups` (SN only: `[["-framework","Security"],["-lpthread"]]`; groups are deduplicated across providers
  by exact equality and kept together in order).
- An SN config with no `binary` contributes only its `flags-groups` (system libraries).
- `bundles`: every native file the JAR physically carries, as `<classifier>/<file>`. Used for collision detection
  and, with artifact and version, for the v2 resource path.

## JAR layout

| Layout | Entry path | Notes |
|---|---|---|
| v2 (0.4.0+) | `native/<provider-artifact>/<provider-version>/<classifier>/<file>` | needs the three v2 fields; consumers must use multiarch >= 0.4.0 |
| legacy fat JAR | `native/<classifier>/<file>` | still read; `NativeLibLoader` prints `[multiarch] '<file>' resolved via legacy layout` once per library. Not removed before 1.0.0 / 2027-01 ([#27](https://github.com/kubuszok/multiarch-scala/issues/27)) |
| legacy flat JAR | `native/<file>` | single-platform JAR; only for Scala Native extraction |

## Building a provider with sbt

Static template + generated v2 manifest, as the library's own
[sn-provider-curl](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/build.sbt) does. The meta-build needs
`multiarch-core` (`project/plugins.sbt`: `libraryDependencies += "com.kubuszok" %% "multiarch-core" % "0.4.0"`) or
the sbt plugin, which depends on it.

```scala
import multiarch.core.{ Platform, ProviderManifestCodec }

lazy val myProvider = project
  .in(file("providers/pnm-provider-mylib-desktop"))
  .settings(
    name             := "pnm-provider-mylib-desktop",
    autoScalaLibrary := false, // no scala-library dependency
    crossPaths       := false, // no _3 / _2.13 suffix
    Compile / packageBin / mappings ++= {
      val natives = baseDirectory.value / "natives" // natives/<classifier>/<files>
      val prefix  = s"native/${moduleName.value}/${version.value}"
      Platform.desktop.flatMap { p =>
        val dir = natives / p.classifier
        if (dir.exists()) IO.listFiles(dir).filter(_.isFile).map(f => f -> s"$prefix/${p.classifier}/${f.getName}").toSeq
        else Seq.empty
      }
    },
    Compile / resourceGenerators += Def.task {
      val template = IO.read(baseDirectory.value / "manifest-template.json") // v1-shaped: no v2 fields
      val natives  = baseDirectory.value / "natives"
      val bundles  = Platform.desktop.flatMap { p =>
        val dir = natives / p.classifier
        if (dir.exists()) IO.listFiles(dir).filter(_.isFile).map(f => s"${p.classifier}/${f.getName}").toSeq else Nil
      }.sorted
      val out = (Compile / resourceManaged).value / "pnm-provider.json"
      IO.write(out, ProviderManifestCodec.enrich(template, moduleName.value, version.value, bundles))
      Seq(out)
    }.taskValue
  )
```

`enrich` sets the schema to `0.2.0` and injects artifact, version and bundles; computing `bundles` and the mappings
from the same directory listing keeps them from drifting.

**sbt 2.x**: `packageBin / mappings` is keyed by `xsbti.HashedVirtualFileRef`, so convert each file:
`(fileConverter.value.toVirtualFile(f.toPath): xsbti.HashedVirtualFileRef) -> path`.

Release check: `NativeExtract.validateBundles(manifest, jarEntries: Map[String, Long], minLibBytes)` returns
`missing` / `undersized` / `undeclared` violations for a built JAR (empty when the JAR matches its manifest).

## Consuming

- Scala Native: `NativeProviderPlugin` (see SKILL.md) - nothing to call.
- JVM: `NativeLibLoader.load("mylib")` (see the `multiarch-scala-jvm-native-loading` skill).
- Android: `AndroidPlugin` copies `.so` files from `native/android-<arch>/` (legacy) or
  `native/<artifact>/<version>/android-<arch>/` (v2) into `lib/<abi>/` of the APK.
- Opt-in build-time collision check for JVM projects without `NativeProviderPlugin`:

```scala
import multiarch.sbt.NativeProviderSettings
myProject
  .settings(NativeProviderSettings.collisionCheckSettings *)
  .settings(Compile / compile := (Compile / compile).dependsOn(NativeProviderSettings.nativeProviderCheckCollisions).value)
```

## Gotchas

- **`[native-provider] Binary 'libfoo.a' not found in .../native-libs/<classifier>`** (a warning, then link
  errors) - the manifest's `binary` does not match the file name in the JAR for that platform. Names are case- and
  extension-exact.
- **`NativeLibLoader.loadAll` / `loadConfigs` cannot find a library on Windows** - they turn `binary` back into a
  logical name by stripping a leading `lib` and the extension, then map it again (`foo.dll` on Windows,
  `libfoo.so` / `libfoo.dylib` elsewhere). A Windows binary named `libfoo.dll`, or a versioned name like
  `libfoo.so.1`, does not round-trip. Use `foo.dll` and `libfoo.so` / `libfoo.dylib`.
- **A consumer on multiarch 0.3.x finds nothing in a v2 provider** - the `native/<artifact>/<version>/...` layout is
  read from 0.4.0 on. Consumers upgrade multiarch before upgrading to v2 providers.
- **`Failed to parse pnm-provider.json manifest at <url>`** from `loadAll` - a corrupt or truncated manifest is a
  hard error there; `load(name)` instead records it and reports it in the final `UnsatisfiedLinkError` note.
