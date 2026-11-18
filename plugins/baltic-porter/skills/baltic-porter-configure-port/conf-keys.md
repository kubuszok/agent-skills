# Port `.conf` keys (engine master `ab8e129d`)

Read off `balticporter.runner.PortConfig`
(<https://github.com/kubuszok/balticporter/blob/master/balticporter/engine/src/main/scala/balticporter/runner/PortConfig.scala>).
Semantics are in the engine's
[Configuring a port](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/configuring-a-port.md).
Any key not listed here is not read, and an unread key fails the load.

## Top level

| key | notes |
|---|---|
| `label` | required; the module id published in `port-map.tsv` (`module=`) |
| `roots { name = "path" }` | named roots for `@name/…` paths; overridable by the caller |
| `base` | path of the base conf; makes this a dependent |
| `input { … }` | required, see below |
| `output { portRoot, sourceSet }` | required; `sourceSet` is `main` or `test` |
| `manifest { … }` | required, see below |
| `provenance { upstreamName, originalLicense, sourcePathPrefix, upstreamCommit, sourceRoot, notices }` | first three required inside the block; `notices` are upstream LICENSE/NOTICE files copied beside the emitted code (a declared file that is missing is fatal) |
| `runtimeMode` | `dependency` (default) or `vendored` |
| `determinism` | `emission` (default), `full`, `off`; a `--determinism=` argument overrides |
| `lenient` / `preview` | booleans, defaults `true` / `false` |
| `supportSources { fqn = "path" }` | a hand-supplied support type |
| `cache` | a cache directory |
| `baseReports = [...]` | extra directories to look for a base module's `port-map.tsv` under (the run's own report tree is searched first); for a base ported in another repository |
| `project { moduleName, organization, scalaVersion, sbtVersion, deps, testDeps, testFramework }` | generates an sbt skeleton; omit in an existing build |
| `nextStep` | a hint printed at the end of the run |

## `input`

| key | notes |
|---|---|
| `sourceRoot` | required |
| `includeGlobs` / `excludeGlobs` | default `**.java` minus `package-info.java` / `module-info.java` |
| `files` | explicit list; exclusive with the globs |
| `classpathFile` | one path-separator-joined line; must exist |
| `classpathCoordinates` | maven coordinates resolved with `cs` into `classpathFile` |
| `classpath` | jars listed directly |
| `resolutionRoots` / `resolutionExcludes` | resolved against, never emitted |
| `frontend` | frontend id, default `java-spoon` |
| `preservedAnnotations` | FQN prefixes of argument-bearing type annotations this port carries over (marker annotations are always kept) |

## `manifest`

| key | notes |
|---|---|
| `name` | required |
| `governs` | FQN prefixes this module claims; empty means no claim |
| `dropTypes`, `dropMethods` | `owner#name` or `owner#name(P1,P2)` |
| `packageRenames`, `typeRenames`, `subPackages`, `flattenNestedTypes`, `allowPackageSplit` | naming; applied after every other phase |
| `inject` | directories/files of Scala this module ships |
| `providedSources` | replacements your build compiles itself; read, never copied |
| `platformDirs { jvm, js, native }` | per-row inject; only those three row names |
| `rowSources { <row> = [ { root, files } ] }` | upstream's own per-platform Java for a class |
| `resources = [ { root, files } ]` | classpath resources copied at their upstream paths |
| `serviceProviders` | upstream `META-INF/services/<interface>` files this module ships; without them `ServiceLoader` silently finds no provider |
| `dependencies = [ { org, name, rev, cross, resolver } ]` | artifacts the emitted code needs; `cross` is `scala` (default), `java` or `platform` |
| `targets` | platforms this port builds for; a dependent may only narrow |
| `externalParenless` | exact `Owner#member` FQNs whose calls are emitted without `()` |
| `surface = [ { transform = "…", … } ]` | phases; see the customize-port skill |
| `resolutions { key = remedyId }` | picks a remedy a phase offers for one location; unknown ids are refused |
| `parity { roots, packageMapping, upstreamMarkers }` | a reference hand port that `derive = true` phases read |
| `frozenDerivedPolicy` | a committed `derived-policy.tsv` used instead of (or checked against) `parity` |

## Inherited by a dependent

| inherited — facts about the shared surface | not inherited — this module's own build |
|---|---|
| `dropTypes`, `dropMethods`, `packageRenames`, `typeRenames`, `subPackages`, `flattenNestedTypes`, `allowPackageSplit`, `surface`, per-location remedy selections | `sourceSet`, `input`, `provenance`, `runtimeMode`, `supportSources`, `project`, `inject`, `platformDirs`, `rowSources`, `providedSources`, `serviceProviders`, `baseReports`, `targets` (may only narrow), `dependencies`, `externalParenless`, `parity` |
