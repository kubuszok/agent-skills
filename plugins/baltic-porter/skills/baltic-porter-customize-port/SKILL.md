---
name: baltic-porter-customize-port
description: >-
  Changing what a Baltic Porter port generates: deciding whether a fix is an engine rule, a phase
  configuration or a library-specific rule; configuring the engine's surface phases from the `.conf`
  (collections retarget/retargetRewrites, type-redirect, call-site-substitution, method-body,
  add-members, member-rename, nullability, primitive-to-opaque, bean-properties, registry,
  type-class-params, class-to-trait, globals-to-implicits, …) with the shared `scope { only / except }`
  grammar; the drop + inject / providedSources recipe; and, when config cannot express it, writing a
  balticporter.tir.Phase plus a TransformFactory registered in META-INF/services and testing it with
  balticporter.testkit.PortSuite. Use after the issue has been classified (baltic-porter-read-port-issues
  or baltic-porter-root-cause-port), when editing a port's manifest surface, or when writing a custom
  phase for one library.
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# Customizing a port

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
The engine's own guide is
[Customizing the translation](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/customizing-translation.md);
every phase's keys are in [phases.md](phases.md).

## 0. Decide the kind BEFORE writing anything

Get it wrong and a general engine quietly becomes a converter for one library:

- **(a) universal**: a fact about Java and Scala, true of every codebase (reference equality,
  `x++` as a value, `switch` fall-through, class initialisers; see
  [Java semantics Scala does not share](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/java-semantics.md)).
  It belongs in the engine, unconditionally. Report it at <https://github.com/kubuszok/balticporter>;
  do not work around it in the consumer.
- **(b) same mechanism, different values**: the engine ships the phase, you supply this library's
  values in the conf or manifest. **Most fixes belong here.** An empty parameter leaves the phase a
  no-op.
- **(c) only ever this library**: an allocation invariant, a runtime convention of one library's
  design. A separate rule you write and register in YOUR repository, never an engine change.

Reach for (c) only after establishing that the mechanism cannot be shared. A rule whose only
library-specific part is a LIST OF NAMES is a (b) with the policy written inline; a rule that encodes
an INVARIANT of the library's design is a (c).

## 1. (b): configuring a phase

A `manifest.surface` entry is `{ transform = "<name>", …its own keys… }`. Names resolve through
`java.util.ServiceLoader`, an unknown one lists every name on the classpath, and any key a phase
does not read fails the load. Phases run in the order declared; the package and type renames
(`manifest.packageRenames` / `typeRenames`) always run last, so **every policy key is written in the
UPSTREAM (Java) namespace**.

### The shared `scope` grammar

```hocon
{ transform = "collections", scope { except = ["com.foo.Bridge"] } }   # everywhere except these
{ transform = "collections", scope { only   = ["com.foo.gl"] } }       # only these
# scope absent                                                        # the phase's own default
```

Both at once is refused. `only = []` is honoured as written. Scopes match fully-qualified names and
cut only at a name separator, so `com.foo` never covers `com.foobar`. A phase that RETYPES existing
declarations defaults to everywhere; a phase that ADDS declarations (`add-members`, `registry`)
defaults to nowhere, and so does `nullary-arity` (changing an arity changes the surface, so it needs
an explicit `scope` or `force`).

After scoping a retyping phase, check two things: the scope changes the emitted SURFACE (two modules
scoping it differently emit signatures that each compile alone and not together — the `manifest`
check), and every boundary the scope creates is COUNTED (`collection-boundary`), never silently
coerced.

### Following a reference hand port: `derive`

`member-rename`, `bean-properties`, `nullary-arity`, `visibility`, `class-tag-params`, `nullability`
and `primitive-to-opaque` accept `derive = true`: the phase also reads a reference hand port declared
under `manifest.parity` and follows its spelling. Once stable, freeze it:
`manifest.frozenDerivedPolicy = "<path>/derived-policy.tsv"` (copied from a run's report directory).
With `parity` also set, the run fails when the derivation disagrees with the frozen file. sge keeps
its frozen policies in `sge-port/*derived-policy.tsv`.

### Drop + replace

`dropTypes` says "this type is not translated; something else supplies its fully-qualified name".
The replacement is either `inject` (Scala files this module ships, copied into `src_managed`) or
`providedSources` (Scala your build already compiles; read for its surface, never copied). The
engine reads the replacement's members with a Scala parser: overrides adopt its parameter types,
calls follow its arity and property spellings, and a parenless `def` / `val` / `var` drops the `()`
at call sites. A drop is inherited by a dependent; the replacement is not.

The `class-to-trait` recipe, for a hand port that reshaped an abstract class into a trait:

```hocon
manifest {
  dropTypes = ["com.foo.Pool"]
  inject    = ["overrides/mylib/Pool.scala"]        # the hand-written trait, with the abstract vals
  surface = [
    { transform = "class-to-trait"
      specs { "com.foo.Pool" { params = [ { index = 0, name = "initialCapacity" }, { index = 1, name = "max" } ] } } }
  ]
}
```

`externalParenless = ["org.junit.runner.Description#getTestClass"]` emits calls to the listed
external members without `()`, for a member a JS/Native shim declares parenless while the JVM class
file has `()`. Not inherited.

### What a conf cannot hold

Where a phase takes a `Symbol => Boolean`, config refuses and names the escape hatch: list exact
names (`primitive-to-opaque`'s `hints` / `extraHints`), or write a `TransformFactory` of your own that
builds the value in Scala (section 2 below), or build the `PortRun` by hand.

## 2. (c): a library-specific rule in YOUR repository

### The phase

```scala
import balticporter.tir.*

final class MyLibRule extends Phase:
  def name: String = "mylib-thing"       // a report identity; any characters
  // every hook defaults to identity; override the ones you need
  override def transformApply(t: Tree.Apply)(using Program): Term = t
  override def transformType(t: TypeRepr)(using Program): TypeRepr = t
  override def run(program: Program): Program = super.run(program)   // full control, for a whole-program pass
```

Also available: `runsAfter` / `runsBefore` (phase names), `transformClassDef`, `transformDefDef`,
`transformValDef`, `transformTypeDef`, `transformIdent`, `transformSelect`, `transformTypeApply`,
`transformNew`, `transformLambda`, `transformBlock`, `transformTerm` (catch-all), and
`record(d: Decision)` for provenance. See
[`Phase.scala`](https://github.com/kubuszok/balticporter/blob/master/balticporter/api/src/main/scala/balticporter/tir/Phase.scala).

Obligations:

- **Walk with `StandardTraversal`** (`mapClassDef`, `scanTerm`), never a private recursion. A walk
  that misses one node kind reports zero hazards from a program that has them.
- **Record a check even when it finds nothing**: `CheckReport.record(name, findings)`, so the report
  can tell "found nothing" from "never ran".
- **Say in the finding which kind the fix is** (here: library-specific, and why), so the next reader
  does not have to investigate.
- **If the rule retypes declarations** it changes the emitted surface: implement `SurfacePolicy`
  (`surfaceFingerprint`: pure, stable, order-independent) so two modules' instances can be compared,
  and `PolicySource` if it takes policy that can fail to match, so a key that never fired reaches
  the `policy` check.

### Getting it into a `.conf`

```scala
final class MyLibFactory extends TransformFactory:
  def name: String = "mylib-thing"                       // stable, kebab-case: published API
  def fromConfig(config: ConfigView): Phase = new MyLibRule
```

```
# src/main/resources/META-INF/services/balticporter.tir.TransformFactory
com.example.port.MyLibFactory
```

```hocon
manifest { surface = [ { transform = "mylib-thing" } ] }
```

The factory and the service file must be on the classpath of the JVM that runs the port — in a
consumer, the sbt meta-build (sge compiles its policy Scala from `sge-port/src/main/scala` into the
meta-build via `project/build.sbt`). Contract
([`TransformFactory.scala`](https://github.com/kubuszok/balticporter/blob/master/balticporter/api/src/main/scala/balticporter/tir/TransformFactory.scala)):

- `fromConfig` gets the entry minus its `transform` key and must throw
  `ConfigError(config.at(key), why)` for anything it cannot honour. Every key an accessor reads is
  recorded, and the loader fails on unread keys, so you never write an unknown-key check.
- `ConfigView` accessors: `string`, `int`, `bool`, `strings`, `stringMap`, `child`, `children`,
  `keys`, `isObject`, `requireString`, `requireChild`, `enumerated`, `at`. A single string is never
  widened to a one-element list.
- `TransformFactory.scopeOf(config)` gives you the shared `scope { }` grammar.
- A factory is a `final class` with a public no-argument constructor, never a Scala `object`:
  `ServiceLoader` cannot call an object's private constructor.

### Testing it: `balticporter.testkit.PortSuite`, with negative tests

Add `"com.kubuszok" %% "balticporter-testkit" % "<same pin>"` to the test classpath of whatever
compiles the rule (it brings MUnit).

```scala
import balticporter.testkit.PortSuite

class MyLibRuleSpec extends PortSuite:
  test("the hazard is reported") {
    val r = new MyLibRule
    port("""class Scene { … }""", r)
    assertEquals(r.findings.size, 1)
  }
  test("a shape that is NOT the hazard is not reported") {
    val r = new MyLibRule
    port("""class Scene { … }""", r)
    assertEquals(r.findings, Nil)
  }
  test("an analysis does not change the emitted Scala") {
    val java = """class Scene { … }"""
    assertEquals(port(java, new MyLibRule).out, port(java).out)
  }
```

(`findings` above is your rule's own field.) `port(java, phases*)` parses the snippet, runs the
phases and emits; the `Ported` result has `before`, `after`, `out` (the emitted Scala) and
`idBefore` / `idAfter`. Assertions: `assertEmits`, `assertNotEmits`, `assertEmitsMatch` and
`assertVacated(p, fullName)` (a type has no USAGES left, which is stronger than its name not
appearing). A rule never shown NOT to fire is not known to work. Run the suite through
`sbt --client "<project>/testOnly <Spec>"` (`baltic-porter-sbt2-client`).

## 3. Push a rule down the scale

A (c) that proves useful for a SECOND library was never a (c). If its library-specific part is a
name list or a map, it should become an engine phase with that list as its parameter (empty = no-op,
plus a `scope` if it retypes); if it is a fact about Java and Scala, it is an (a). Propose either to
the engine repository rather than copying the rule into a second consumer.

Then regenerate and measure: change one thing at a time (`baltic-porter-read-port-issues`).
