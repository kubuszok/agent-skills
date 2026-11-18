---
name: baltic-porter-configure-port
description: >-
  Writing a Baltic Porter port configuration (HOCON `.conf`, loaded by
  balticporter.runner.PortConfig) for a directory of Java sources, or the equivalent hand-written
  PortRun: label, input (sourceRoot, includeGlobs/excludeGlobs, files, classpathFile,
  classpathCoordinates, resolutionRoots, resolutionExcludes), output (portRoot, sourceSet, src_managed),
  roots and `@name/` paths, the manifest (dropTypes, dropMethods, packageRenames, typeRenames, inject,
  providedSources, platformDirs, rowSources, resources, surface), provenance, runtimeMode, the
  `base = "…"` dependent module, how many confs a port needs, wiring it into an sbt source generator
  with balticporter.reportDir, and errors like "key(s) nobody read" or a missing classpathFile. Use
  when starting a port of a Java library that has no configuration yet, or adding a second source set,
  module or extension to one that does.
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# Configuring a port

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
The format is documented in full in the engine's
[Configuring a port](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/configuring-a-port.md)
and [Multi-module ports](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/multi-module-ports.md);
the loader
[`PortConfig.scala`](https://github.com/kubuszok/balticporter/blob/master/balticporter/engine/src/main/scala/balticporter/runner/PortConfig.scala)
is the authority when a document and the code disagree. On a different pin, read those files at the
pinned commit. Every key is summarised in [conf-keys.md](conf-keys.md).

Real configurations to read first: ssg's `ssg-md/port/main.conf` (a base), `ssg-md/port/ext.conf`
(a dependent) and `ssg-liquid/port/main.conf`. sge and lls build their `PortRun` in Scala
(`project/BalticPorterGen.scala`, policy under `sge-port/` / `lls-port/`).

Not covered here: configuring one phase's own keys or writing a library-specific rule
(`baltic-porter-customize-port`), reading what the run reports (`baltic-porter-read-port-issues`).

## 0. Three ways to run a port — pick the `.conf` unless you need Scala

| way | for |
|---|---|
| `balticporter.runner.PortConfig.load(conf, args, roots = …).execute()` from your generator | **the usual shape**; ssg does this |
| a hand-written `balticporter.runner.PortRun(...)` | a `Symbol => Boolean` predicate, a computed file list, several source sets from one program; sge and lls do this |
| `balticporter.runner.PortConfigMain <port.conf>` | a one-off with nothing to write |

Both the conf and `PortRun` build the same values; neither is a downgrade.

**In an sbt source generator, set the report directory yourself.** A run inside sbt's JVM cannot
derive a report identity from a main class, so it writes NO report unless `balticporter.reportDir`
is set. Give every port its own directory, under one shared root so a dependent finds its base's
port map:

```scala
System.setProperty("balticporter.reportDir", reports.resolve("mylib").toString)
try balticporter.runner.PortConfig.load(portDir.resolve("main.conf")).execute()
finally System.clearProperty("balticporter.reportDir")
```

Wrap the generator in `synchronized` (matrix rows run it in parallel), keep a `.generated-marker`
of its inputs (engine pin, upstream commit, generator source, policy files, JDK major) beside the
output, and skip the run when it matches. `project/BalticPorterGen.scala` in
[ssg](https://github.com/kubuszok/ssg) and [sge](https://github.com/kubuszok/sge) are complete
examples.

## 1. Paths: relative to the conf file, or under a named root

Every path resolves against **the conf file itself**, lexically — not the working directory. For a
conf that is run from elsewhere, declare named roots and write paths as `@name/…`:

```hocon
roots {
  consumer = "../.."                            # this repository
  work     = "../../target/balticporter-work"   # files the run prepares (resolved classpaths)
  ports    = "../../target/balticporter"        # where generated code goes
}
input  { sourceRoot = "@consumer/original-src/mylib/src/main/java" }
output { portRoot = "@ports/mylib", sourceSet = "main" }
```

The caller may override a root: `PortConfig.load(conf, roots = Map("work" -> dir))`. Overriding an
undeclared root, or using `@name/` for a root nobody declared, is refused by name.

## 2. `input`: what the frontend parses, and what it only resolves against

- `sourceRoot` (required); `includeGlobs` / `excludeGlobs` (default: `**.java`, minus
  `package-info.java` and `module-info.java`) or `files` — never both. `include` alone is a HOCON
  keyword and cannot be used. The list is sorted: unit order is emission order.
- **The frontend classpath is the upstream library's own dependencies**, at the versions the
  library's build DECLARES (`build.gradle`, `pom.xml`), not current ones. Either point
  `classpathFile` at one path-separator-joined line (`cs fetch --classpath junit:junit:4.12 > …`), or
  list `classpathCoordinates = ["org:name:rev", …]` and the run resolves them with `cs` (which must be
  on the `PATH`) into `classpathFile`, reusing the file while it still matches.
- A `classpathFile` that does not exist is **fatal**. An unresolvable reference does not fail parsing:
  it resolves WRONGLY (a static import from `org.junit.Assert` becomes `this.assertEquals(...)`) and
  the port reports success.
- `resolutionRoots` are parsed and resolved against, never emitted. A run whose resolution roots lie
  outside its own source root is structurally a dependent (section 5). `resolutionExcludes` skips paths
  under a root (a GWT `super-source` tree that redeclares the same classes). Do not narrow the root
  instead: a base's published surface is joined through the whole root.

## 3. `output`: where the Scala lands

`output { portRoot = "…", sourceSet = "main" }` (`main` or `test`). Scala always lands at
`<portRoot>/src_managed/{main,test}/scala`, per-row files at `src_managed/<jvm|js|native>/scala`,
resources at `src_managed/main/resources` — gitignored, deleted by `sbt clean`, never under `src/`.
This layout cannot be redirected.

Where the port replaces PART of an existing hand-written module, the hand-written half stays a
build setting (`unmanagedSourceDirectories` with an `excludeFilter` naming the files the port now
emits), never a copy.

**Name the port for its DESTINATION**, not the upstream library: the directory, `label` and
`manifest.name` all use the id of the module the Scala becomes in your build (`sge-graphs`, not
`simple-graphs`). `label` is what the run publishes as `module=` in `port-map.tsv`, and a dependent's
base chain matches against it. `provenance.upstreamName` keeps the library's own name.

## 4. `manifest`: the port's policy (required)

```hocon
manifest {
  name           = "mylib"                                  # required
  governs        = ["com.example.mylib"]                    # FQN prefixes this module claims; may be empty
  dropTypes      = ["com.example.mylib.Reflection"]          # not translated; something else supplies the FQN
  dropMethods    = ["com.example.mylib.Pool#free(Object)"]
  packageRenames { "com.example.mylib" = "mylib" }
  typeRenames    { "com.example.mylib.Utils$Helper" = "Helper" }
  inject          = ["overrides/mylib"]                      # ready-made Scala this module ships
  providedSources = ["../mylib/src/main/scala"]              # replacements your build compiles itself: read, never copied
  platformDirs    = { jvm = ["overrides/mylib-jvm"] }        # per-row inject: jvm | js | native
  resources       = [ { root = "@upstream/src/main/resources", files = ["mylib/data.json"] } ]
  surface = [ { transform = "collections" }, { transform = "mutable-params" } ]
}
```

- **A drop is shared; its replacement is not.** `dropTypes` / `dropMethods` bind every module that
  sees the type and are inherited by a dependent. `inject`, `platformDirs`, `rowSources` and
  `providedSources` are build artefacts of ONE module: a dependent that copied them would define the
  same type twice.
- **Prefer `providedSources` to `inject`** when your build already compiles the replacement: the
  engine reads its surface (property spellings, companion `apply`, parameter types) and copies
  nothing, so there is one home per file.
- **Renames are data, not a phase.** `packageRenames` / `typeRenames` run after every other phase,
  because every other policy is written in the UPSTREAM namespace. Writing
  `{ transform = "package-rename" }` in `surface` is refused by name. `subPackages` and
  `flattenNestedTypes` compose: a type promoted and moved is named in both.
- **`resources` is a second output** that the build must wire separately
  (`baltic-porter-generated-code`, rule 5). Generated code looks resources up at the UPSTREAM path.
- `surface` lists the phases that shape emitted signatures, in order. Each entry is
  `{ transform = "<name>", …its own keys… }`; an unknown name lists every name on the classpath. The
  per-phase keys are in `baltic-porter-customize-port`. Every retyping phase takes
  `scope { except = [...] }` or `scope { only = [...] }` (never both).

## 5. A second module: `base = "…"`

```hocon
label = "mylib-test"
base  = "main.conf"        # relative to THIS file
```

`base` reads that file's `manifest` and computes `baseManifest.extendedBy(thisManifest)`. It is not
an include: the base's `input`, `output`, `provenance` and `runtimeMode` are ignored. What is and is
not inherited is in [conf-keys.md](conf-keys.md#inherited-by-a-dependent). The engine runs a
manifest-agreement check on every port and refuses: a dependent that declares no base (resolution
roots outside its source root and no `base`; for a vendored tree you resolve against but never port,
declare an empty manifest for it and say so); a drop, rename or signature-shaping phase in one module
and not the other; one phase twice with different policy; a dependent that widens `targets`.

A dependent's phases follow the base's: it inherits the base's `surface` and the base's member
renames. For a base that is itself a port of part of the same upstream tree (lls beneath sge-core),
decide the base's SOURCE SET first, against which types the reference hand port declares where: a
base may not emit a type the dependent owns, drops or reshapes (fatal `SurfaceIntrusion`,
`ExtraDrop`). The dependent excludes the base's files from its own globs.

## 6. How many confs? Count DESTINATIONS, never upstream modules

A run's emission identity is the pair (`portRoot`, `sourceSet`), and a run starts by wiping its
output. **A second run at the same pair deletes the first's output** — no error, just a smaller tree.

- An upstream that splits one library across N maven modules under one package root is ONE conf
  with a list of globs (ssg's `ssg-md/port/main.conf` covers twelve flexmark modules).
- A second SOURCE SET (`main` + `test`) is a second conf at the same `portRoot` with
  `base = "main.conf"`.
- A third tree in the same consumer module gets its own `portRoot` with packages disjoint from the
  base's, named for its destination (ssg: `ssg-md` and `ssg-md-ext`).

Signs you got this wrong: an emitted file count that fell with no scope change; two ports that each
compile alone and not together; one report directory per upstream module.

## 7. Provenance and the rest

- `provenance { upstreamName, originalLicense, sourcePathPrefix }` (all three required inside the
  block; `upstreamCommit` is derived from the vendored tree's git state). It is a licence
  obligation: every generated file gets a header naming the upstream project, commit and licence,
  and omitting the block ships NO attribution with nothing reporting it. State the licence the
  upstream file carries; where a hand port disagrees, upstream wins.
- `runtimeMode`: `dependency` (default; support types come from `balticporter-runtime`) or
  `vendored` (copied beside the emitted code). Vendor at most one source set: two copies of a support
  type are rejected by the Scala.js and Scala Native linkers.
- `determinism` (`emission` default, `full`, `off`), `lenient` (default `true`), `preview` (default
  `false`; `true` makes the emitter write a `compiletime.error` where it has no faithful Scala). Leave
  them at their defaults unless a specific failure says otherwise.
- `project { … }` generates an sbt skeleton. **Omit it** in an existing build.

## 8. Any key nobody reads fails the run

```
port config: /…/typo.conf: 1 key(s) nobody read: manifest.dropType. HOCON accepts any key it is
given, so a misspelt one is a policy entry that silently does nothing. Fix the spelling, or delete
the key.
```

A bad KEY is caught here, at load. A bad VALUE (a `dropTypes` entry naming no type) reaches the run
and is reported by the `policy` check. A conf loaded only as somebody's `base` has just its
`manifest` read, so a typo in its own `input`/`output` is caught only when it is loaded as a port in
its own right: **load every conf as a port at least once**.

## 9. What a conf deliberately cannot hold

No class name in a string, no expression language, no predicate. Where a phase takes a
`Symbol => Boolean`, either the engine's default needs no policy, or the conf names things as data,
or the conf refuses and names the escape hatch: a `TransformFactory` of your own that builds the
value in Scala, or a hand-written `PortRun`. That is `baltic-porter-customize-port`.

## 10. Before measuring anything

Load the conf once and see that it does not throw. Configuration errors surface before anything is
written: one line naming the key to fix. Then regenerate (`sbt --client generatePort` in a consumer)
and read the report (`baltic-porter-read-port-issues`).
