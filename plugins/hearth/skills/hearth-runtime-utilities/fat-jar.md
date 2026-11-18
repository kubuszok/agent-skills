# Hearth in fat JARs: what is used at runtime

Summary of the FAQ entry "Which parts of Hearth end up in my application at runtime? Can I remove the rest from a fat
JAR?". That entry was added to Hearth's docs **after 0.4.5**, so it exists only in the latest docs:
https://scala-hearth.readthedocs.io/en/latest/faq/#which-parts-of-hearth-end-up-in-my-application-at-runtime-can-i-remove-the-rest-from-a-fat-jar
(not under `/en/0.4.5/`). The package layout it describes is the same in 0.4.5.

Libraries built with Hearth depend on it in the normal `Compile` scope, so Hearth is on the runtime classpath and in
every fat JAR (sbt-assembly, Maven Shade, Gradle Shadow, ...). Most of it only runs inside the compiler during macro
expansion. **This only matters on the JVM**: the Scala.js and Scala Native linkers already drop unreachable code.

## Keep (used at runtime)

| Package                         | Artifact | Why                                                                          |
|---------------------------------|----------|------------------------------------------------------------------------------|
| `hearth.source`                 | `hearth` | `Line`, `File`, `FileName`, `MethodName`, `Location`, `Text` values used by your code |
| `hearth.typename`               | `hearth` | generated `TypeName[A]` instances run in your program                        |
| `hearth` (classes directly in it) | `hearth` | `HearthVersion`, `ScalaVersion`, `JDKVersion`, `LanguageVersion`, `Platform`; macros may lift them into generated code. The other classes there are compile-time only but small - keep the whole package |

## Probably only needed in tests

| Package                                         | Artifact       | Notes                                                       |
|-------------------------------------------------|----------------|-------------------------------------------------------------|
| `hearth.data`                                   | `hearth`       | `Data`, `DiffEntry`; drop only if production code never uses `Data` |
| `hearth` (`Suite`, `MacroSuite`, `ScalaCheckSuite`) | `hearth-munit` | must be a `% Test` dependency; if it is in the fat JAR, fix the scope instead of filtering |

## Safe to remove (macro expansion only)

| Package / dependency                                   | Artifact                            | Notes |
|--------------------------------------------------------|-------------------------------------|-------|
| `hearth.typed`, `hearth.untyped`                       | `hearth`                            | core macro API, the largest part |
| `hearth.std`, `hearth.std.extensions`, `META-INF/services/hearth.*` | `hearth`               | standard extensions, loaded by the compiler via `ServiceLoader` |
| `hearth.debug`                                         | `hearth`                            | `Debug.*` expands to the wrapped expression |
| `hearth.fp`                                            | `hearth-micro-fp` (whole artifact)  | unless your production code uses micro-FP (not recommended) |
| `hearth.treeprinter`                                   | `hearth-better-printers` (whole)    | |
| `hearth.cq`                                            | `hearth-cross-quotes` (whole)       | library dependency on Scala 2; compiler plugin (never on the runtime classpath) on Scala 3 |
| `scala-compiler`, `jline`, `java-diff-utils`           | pulled in by Hearth on Scala 2.13   | unless the application uses them itself (runs the compiler/REPL, uses JLine) |
| `scala-reflect`                                        | pulled in by Hearth on Scala 2.13   | Hearth's runtime classes do not need it; other libraries using Scala 2 runtime reflection do |

Libraries built on Hearth have the same split (their macro implementations are compile-time only); check their docs.

**Scala 3 multi-stage programming** (`scala.quoted.staging`) runs the compiler inside the application, so the
"compile-time only" packages become runtime dependencies. Untested by Hearth - keep everything if you use staging.

## sbt-assembly example (sbt 1.x, sbt-assembly 2.x)

```scala
assembly / assemblyExcludedJars := {
  val compileTimeOnlyJars = Seq(
    "hearth-better-printers_",
    "hearth-cross-quotes_",
    "hearth-micro-fp_",
    // Scala 2.13 only - remove these lines if your application uses them itself
    "scala-compiler-",
    "jline-",
    "java-diff-utils-"
  )
  (assembly / fullClasspath).value.filter { jar =>
    compileTimeOnlyJars.exists(jar.data.getName.startsWith)
  }
}

assembly / assemblyMergeStrategy := {
  case PathList("hearth", "typed" | "untyped" | "std" | "debug", _*)                => MergeStrategy.discard
  case PathList("META-INF", "services", service) if service.startsWith("hearth.") => MergeStrategy.discard
  // uncomment if nothing in your production code uses hearth.data.Data:
  // case PathList("hearth", "data", _*) => MergeStrategy.discard
  case other =>
    val defaultStrategy = (assembly / assemblyMergeStrategy).value
    defaultStrategy(other)
}
```

Then run the application (or its integration tests) from the fat JAR. `NoClassDefFoundError` mentioning
`hearth/...` means something needs that package at runtime: put it back (and report the class to Hearth).
