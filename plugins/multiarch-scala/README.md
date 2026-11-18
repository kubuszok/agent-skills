# `multiarch-scala` plugin

Skills for **using** [multiarch-scala](https://github.com/kubuszok/multiarch-scala) **0.4.0**: sbt plugins and
small libraries for Scala builds that target the JVM, Scala.js and Scala Native and ship native libraries in
provider JARs. Reference: the [README at 0.4.0](https://github.com/kubuszok/multiarch-scala/blob/0.4.0/README.md).

Some fixes and the `multiarch-serviceloader` module exist only in snapshots after 0.4.0
(`0.4.0-<N>-g<hash>-SNAPSHOT`); the skills mark these as "after 0.4.0".

Install: `/plugin install multiarch-scala@kubuszok` (Claude Code). See the [root README](../../README.md) for other
harnesses.

## Skills

| Skill | Covers |
|---|---|
| `multiarch-scala-setup` | Start here: artifacts, `plugins.sbt` for sbt 1.x and 2.x, projectMatrix layout, `NativeProviderPlugin` and `nativeConfig` ordering, platform classifiers; reference files for writing provider JARs (manifest v2) and JVM release packaging |
| `multiarch-scala-library-vs-app` | Library vs application vs provider JAR: what each publishes, packages and depends on |
| `multiarch-scala-jvm-native-loading` | `NativeLibLoader` for JNI and Panama on the JVM, resolution order, loader failures |
| `multiarch-scala-panama` | `multiarch-panama-api` / `-jdk`: one FFI code base for JDK 22+ and Android (PanamaPort) |
| `multiarch-scala-cross-native-testing` | zig cross-linking of Scala Native for all 6 desktop targets, `withCrossNative` |
| `multiarch-scala-android-build` | `AndroidPlugin`: APKs from sbt without Gradle, native `.so` packaging, PanamaPort |
| `multiarch-scala-resources-serviceloader` | `multiarch-resources` and `multiarch-serviceloader` on JS/Native |
| `multiarch-scala-browser-packaging` | Browser bundles for the Scala.js row (plain sbt-scalajs) |
