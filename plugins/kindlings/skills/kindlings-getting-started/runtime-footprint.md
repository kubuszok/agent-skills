# Runtime footprint and fat JARs (Kindlings 0.4.0)

Kindlings modules are ordinary `Compile` dependencies, so all their code ends up on the runtime classpath and in every
fat JAR (sbt-assembly, Maven Shade, Gradle Shadow). Most of it is macro implementation that only the compiler runs.
In the published JVM jars, compile-time-only packages are over 80% of the bytes.

This matters only on the JVM. The Scala.js and Scala Native linkers already drop unreachable code.

Source: the FAQ entry "Which parts of Kindlings end up in my application at runtime?" at
<https://kindlings.readthedocs.io/en/latest/faq/>. Hearth's FAQ has the matching list for Hearth's own packages.

## Package classification

`*` stands for any one package segment, usually the module package (`circederivation`, `jsoniterderivation`,
`parser`, ...). When several rows match, the most specific row wins.

**Keep (used at runtime):**

| Package | Contents |
|---|---|
| `hearth.kindlings.*` (anything not listed below) | public API: type classes, companions, configuration, syntax; `jsoniterjson`, `tapiropenapijsoniter` (including its `internal` codecs), parser runtime and its `catseffect` / `streams` engines |
| `hearth.kindlings.*.internal.runtime` | helpers and factories called by macro-generated code |
| `hearth.kindlings.*.annotations` | annotations such as `@fieldName`. Some generated code creates them at runtime: a derived tapir `Schema` creates jsoniter's `@named`, and Avro creates `@avroSortPriority` |

**Test-only modules.** Add these with `% Test`. If one ends up in a fat JAR, fix the dependency scope rather than
filtering it out.

| Package | Artifact |
|---|---|
| `hearth.kindlings.mock` | `kindlings-mock` |
| `hearth.kindlings.scalacheckderivation` | `kindlings-scalacheck-derivation` |
| `hearth.kindlings.diffderivation` | `kindlings-diff-derivation` (keep it in `Compile` if production code computes diffs) |

**Safe to remove (compile time only):**

| Package / file | Artifact |
|---|---|
| `hearth.kindlings.*.internal.compiletime` (and subpackages) | every derivation, macro and integration module |
| `hearth.kindlings.derivation.compiletime` | `kindlings-derivation-commons` (whole artifact) |
| `hearth.kindlings.macros.compiletime` | `kindlings-macro-commons` (whole artifact) |
| `hearth.kindlings.jsonschemaconfigs` | `kindlings-json-schema-config-macro-providers` (whole artifact) |
| `META-INF/services/hearth.*` | macro extensions, loaded by the compiler via `ServiceLoader` |
| `hearth.kindlings.*.debug`, `hearth.kindlings.*.policy` | tiny marker implicits. Remove them only if no code refers to the marker values, e.g. a `val` that exists to keep `-Wunused` quiet |

The refined, iron, neotype and newtype integrations are entirely compile-time code. `kindlings-cats-integration` has a
small runtime part: `hearth.kindlings.catsintegration.internal.runtime`.

## sbt-assembly example

The example assumes sbt 1.x and sbt-assembly 2.x. The Hearth rules come from Hearth's FAQ.

```scala
assembly / assemblyExcludedJars := {
  val compileTimeOnlyJars = Seq(
    "hearth-better-printers_", "hearth-cross-quotes_", "hearth-micro-fp_",
    // Scala 2.13 only; remove if the application itself uses them
    "scala-compiler-", "jline-", "java-diff-utils-"
  )
  (assembly / fullClasspath).value.filter(jar => compileTimeOnlyJars.exists(jar.data.getName.startsWith))
}

assembly / assemblyMergeStrategy := {
  case PathList("hearth", "kindlings", _, "internal", "compiletime", _*)           => MergeStrategy.discard
  case PathList("hearth", "kindlings", "derivation" | "macros", "compiletime", _*) => MergeStrategy.discard
  case PathList("hearth", "kindlings", "jsonschemaconfigs", _*)                    => MergeStrategy.discard
  // only if nothing refers to the debug / policy marker values:
  // case PathList("hearth", "kindlings", _, "debug" | "policy", _*) => MergeStrategy.discard
  case PathList("hearth", "typed" | "untyped" | "std" | "debug", _*)                => MergeStrategy.discard
  case PathList("META-INF", "services", service) if service.startsWith("hearth.") => MergeStrategy.discard
  case other => (assembly / assemblyMergeStrategy).value(other)
}
```

## Gotchas

- **Test the fat JAR, not only the build.** Run the application or its integration tests from the assembled JAR. A
  `NoClassDefFoundError` mentioning `hearth/kindlings/...` means a removed package is needed at runtime. Restore that
  package, and report the class upstream.
- **Runtime compilation needs everything.** With Scala 3 `scala.quoted.staging` or Scala 2's
  `scala.tools.reflect.ToolBox`, macros expand inside the running application, so nothing above is safe to remove.
  Kindlings and Hearth are untested with staging.
- **Do not depend directly on `kindlings-derivation-commons`, `kindlings-macro-commons` or
  `kindlings-json-schema-config-macro-providers`.** They are internal macro infrastructure, pulled in transitively.
