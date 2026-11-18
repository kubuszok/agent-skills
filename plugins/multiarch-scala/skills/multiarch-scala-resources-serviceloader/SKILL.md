---
name: multiarch-scala-resources-serviceloader
description: >-
  Reading classpath resources and finding java.util.ServiceLoader providers on JVM, Scala.js and Scala Native with
  multiarch-scala: multiarch-resources (multiarch.resources.PlatformResources getResourceAsStream /
  getResourceBytes / getResourceAsString / resourceExists, MultiArchResourcesPlugin.embeddedResourcesSettings,
  EmbeddedResourcesGen) and multiarch-serviceloader (multiarch.serviceloader.PlatformServiceLoader load / register,
  MultiArchServiceLoaderPlugin.embeddedServiceProvidersSettings generated from META-INF/services). Covers the
  projectMatrix wiring per platform, referencing the generated object so dead-code elimination keeps it,
  withEmbedResources on Scala Native, and failures such as getResourceAsStream returning null on Scala.js,
  "Referring to non-existent class java.util.ServiceLoader" on Scala.js, the Scala Native "first argument of method load needs to be literal
  constant of class type" error, and an empty provider list. Use when shared code reads resources or service providers.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Resources and ServiceLoader on every platform

Version: written for multiarch-scala **0.4.0**. `multiarch-resources` is in 0.4.0; **`multiarch-serviceloader` is
not** - it exists only in snapshots after 0.4.0 (e.g. `0.4.0-20-ga3e0f08-SNAPSHOT`, resolver
`https://central.sonatype.com/repository/maven-snapshots`) and the next release. Check the user's versions; if they
differ, read <https://github.com/kubuszok/multiarch-scala/tree/0.4.0/multiarch-resources> and, for the service
loader, <https://github.com/kubuszok/multiarch-scala/blob/master/README.md>. The sbt plugin and the runtime module
must come from the same version.

| Platform | `Class.getResourceAsStream` | `java.util.ServiceLoader` |
|---|---|---|
| JVM | works | works |
| Scala.js | no classpath: always `null` | not in the Scala.js library; fails at link time |
| Scala Native | works only with `nativeConfig.withEmbedResources(true)` | `load` accepts only a literal `classOf[Concrete]`, so no generic wrapper can call it |

Both modules give one API and generate, at build time, the code the non-JVM platforms need.

## Resources: multiarch-resources

```scala
libraryDependencies += "com.kubuszok" %%% "multiarch-resources" % "0.4.0" // Scala 2.13 and 3; %% on sbt 2.x
```

```scala
import multiarch.resources.PlatformResources

val text: Option[String]       = PlatformResources.getResourceAsString(classOf[MyClass], "/data/table.csv")
val bytes: Option[Array[Byte]] = PlatformResources.getResourceBytes(classOf[MyClass], "/img/logo.png")
val in: Option[java.io.InputStream] = PlatformResources.getResourceAsStream(classOf[MyClass], "/x.json")
val exists: Boolean            = PlatformResources.resourceExists(classOf[MyClass], "/x.json")
```

Paths follow `Class.getResourceAsStream`: a leading `/` is from the classpath root, otherwise relative to the
class's package (on Scala.js a missing `/` is simply added).

Build wiring - the JS row embeds the resource directory into a generated object; the Native row embeds resources
into the binary; the JVM needs nothing:

```scala
import multiarch.sbt.MultiArchResourcesPlugin

lazy val myLib = (projectMatrix in file("my-lib"))
  .jvmPlatform(scalaVersions)
  .jsPlatform(scalaVersions, settings = MultiArchResourcesPlugin.embeddedResourcesSettings(
    objectName = "my.lib.GeneratedEmbeddedResources"   // default: multiarch.resources.GeneratedEmbeddedResources
    // resourceDir = Def.setting((Compile / resourceDirectory).value)  // the default
  ))
  .nativePlatform(scalaVersions, settings = Seq(
    nativeConfig ~= (_.withEmbedResources(true).withResourceIncludePatterns(Seq("**.csv", "**.json")))
  ))
```

The generated object registers its files in its initializer. Reference it once from code that runs on Scala.js
before the first lookup, or the linker removes it:

```scala
val _ = my.lib.GeneratedEmbeddedResources
```

On Scala.js, a lookup that is not embedded falls back to Node's `fs` under a few fixed directories relative to the
working directory (`src/main/resources`, `src/test/resources`, `target/...`) - convenient in tests run from the
repository, useless in a browser.

## Service providers: multiarch-serviceloader (after 0.4.0)

```scala
libraryDependencies += "com.kubuszok" %%% "multiarch-serviceloader" % "<snapshot after 0.4.0>"
```

```scala
import multiarch.serviceloader.PlatformServiceLoader

val it: Iterator[Codec] = PlatformServiceLoader.load(classOf[Codec]).iterator() // drop-in shape
val all: List[Codec]    = PlatformServiceLoader.load(classOf[Codec]).toList

PlatformServiceLoader.register(classOf[Codec], new JsonCodec) // by hand, works on every platform
```

- JVM: `load` wraps exactly one `java.util.ServiceLoader`, so class loader and caching are the JDK's; registered
  providers come after the discovered ones.
- JS and Native: providers come only from registration. `register` is by-name and evaluated on every iteration,
  so each traversal creates fresh instances; registering twice yields the provider twice.
- `load(...)` returns `ServiceProviders[T]` (only `iterator()` and `toList`), not a Scala collection.

Build wiring - generate `register` calls from the same `META-INF/services/<service>` files the JVM reads:

```scala
import multiarch.sbt.MultiArchServiceLoaderPlugin

val generatedProviders = MultiArchServiceLoaderPlugin.embeddedServiceProvidersSettings(
  objectName = "my.lib.GeneratedServiceProviders" // default: multiarch.serviceloader.GeneratedServiceProviders
  // resourceDir = Def.setting((Compile / resourceDirectory).value), config = Compile  (use Test for test-only providers)
)

lazy val myLib = (projectMatrix in file("my-lib"))
  .jvmPlatform(scalaVersions)
  .jsPlatform(scalaVersions, settings = generatedProviders)
  .nativePlatform(scalaVersions, settings = generatedProviders)
```

For a descriptor `META-INF/services/my.lib.Codec` containing `my.lib.JsonCodec` it emits
`PlatformServiceLoader.register(classOf[my.lib.Codec], new my.lib.JsonCodec())`, so a renamed or missing provider
class is a compile error instead of an empty iterator. Reference the object once from the entry point:
`val _ = my.lib.GeneratedServiceProviders`. Scala Native's `nativeConfig.withServiceProviders(...)` is not needed.

## Gotchas

- **`PlatformResources` returns `None` on Scala.js in the browser or a published artifact, but works in tests** -
  the resources were not embedded (settings missing on the JS row), or the generated object was never referenced
  and was removed by dead-code elimination; the test run only worked through the Node `fs` fallback.
- **`not found: EmbeddedResources`** when compiling a JVM or Native row - `embeddedResourcesSettings` was applied to
  the whole matrix; the generated code uses a Scala.js-only class. Apply it to the JS row only.
- **Duplicate class `GeneratedEmbeddedResources` / `GeneratedServiceProviders`** - two modules on one classpath use
  the default object name. Give each module its own `objectName`.
- **Only one directory is embedded** - `embeddedResourcesSettings` reads one `resourceDir`. For a second directory
  (e.g. generated resources), add another `sourceGenerators` task calling
  `multiarch.sbt.EmbeddedResourcesGen.generate(dir, outFile, "my.lib.MoreResources", streams.value.log)` and
  reference that object too.
- **Scala Native resource lookup returns `None`** - `withEmbedResources(true)` is missing, or a later
  `nativeConfig := ...` replaced it. Use include patterns; embedding everything can run the linker out of memory.
- **`Referring to non-existent class java.util.ServiceLoader`** (Scala.js linker) or
  **`Limitation of ScalaNative runtime: first argument of method load needs to be literal constant of class type`**
  - shared code calls `java.util.ServiceLoader.load(cls)`. Call `PlatformServiceLoader.load(cls)` instead.
- **`PlatformServiceLoader.load` is empty on JS/Native** - the generated object was not referenced before the first
  `load`, the settings are missing on that row, or the descriptor is not under `<resourceDir>/META-INF/services/`.
- **Compile error naming an odd first provider class in the generated file** - the descriptor starts with a UTF-8
  BOM; generators before the post-0.4.0 fix kept it in the class name. Save the file without a BOM.
- **A nested provider class** (`Outer$Inner` in the descriptor) is emitted as `Outer.Inner`; if that does not
  resolve in Scala, the build fails by design.
