---
name: kindlings-troubleshooting
description: >-
  Diagnosing Kindlings (hearth.kindlings.*) compile errors and build problems - "Macro derivation failed with the
  following errors", "was not handled by any encoder derivation rule", "Macro 'KindlingsEncoder.derived' timed out
  after 5000ms", "Derivation of ... is enabled only in the following scopes", ambiguous implicits, "Method too
  large", -Werror warnings at expansion sites, NPEs from self-referencing instances, HearthAssertionError
  re-entering runToExprOrFail, sbt metaspace growth. Covers debug logging (debug._ imports, <ns>.logDerivation=true,
  logGeneration), derivation timeouts (<ns>.timeout, formats, 5 s default, CI flakiness, 1ms canary), the full table
  of settings namespaces per module, passing -Xmacro-settings in sbt / Mill / scala-cli / mdoc and the Scala 3
  comma-splitting difference, Hearth flame graphs, and known fixed bugs worth upgrading for. Use when a Kindlings
  derivation fails, is slow, or behaves differently than expected.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Troubleshooting Kindlings derivation

How to read Kindlings' compile errors, turn on debug logging, tune the derivation timeout, pass macro settings in each
build tool, and which versions fix which known bugs.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/debugging/>. Many of the problems below are fixed bugs - check
[Known bugs fixed in later versions](#known-bugs-fixed-in-later-versions) first when the user is not on 0.4.0.

## Reading a derivation error

A failed derivation aborts with one message listing **every** problem found (not only the first):

```text
Macro derivation failed with the following errors:
  - The type com.acme.Money was not handled by any encoder derivation rule:
    <one line per rule saying why it did not apply>
Enable debug logging with: import hearth.kindlings.circederivation.debug.logDerivationForKindlingsEncoder or scalac option -Xmacro-settings:circeDerivation.logDerivation=true
```

| Message (circe wording; other modules are analogous) | Cause | Fix |
|---|---|---|
| `The type X was not handled by any ... derivation rule` | `X` is a leaf with no implicit instance and no rule applies (abstract/Java class, `Any`, function, opaque type of an unsupported library, ...) | Provide an implicit for `X` (in `X`'s companion or in scope at the derivation site); for refined / Iron / neotype / scala-newtype add the integration (since 0.4.0 the error names the module to add) - see `kindlings-integrations` |
| `The type A was not handled ...` where `A` is a type parameter | deriving `Box[A]` with abstract `A` and no instance for `A` | `implicit def boxEnc[A: Encoder]: Encoder[Box[A]] = KindlingsEncoder.derived[Box[A]]` (Scala 3: `given [A: Encoder]: Encoder[Box[A]] = KindlingsEncoder.derived`) |
| `@transientField on field 'x' of Y requires a default value` | transient fields are filled from the default when decoding | add a default value |
| `The type X does not have any children!` | sealed trait with no visible subclasses (on Scala 2 this can also be the compiler's `knownDirectSubclasses` limitation when the derivation is type-checked before the subclasses in the same file) | add subclasses / move the instance below the subclasses or to another file |
| `enumAsStrings is enabled but X has cases that are not singletons` | string-enum encoding for a sum with case classes | drop `enumAsStrings` for that type or make all cases objects |
| `Derivation of X[T] is enabled only in the following scopes` / `is globally disabled` | the derivation policy is `opt-in` | see `kindlings-derivation-policy` |
| `Macro 'X.derived' timed out after 5000ms` | the 5 s per-expansion budget ran out | raise `<ns>.timeout`, see [Derivation timeout](#derivation-timeout) |
| `ambiguous implicit values` | upstream automatic derivation (`io.circe.generic.auto._`, `pureconfig.generic.auto._`, `sttp.tapir.generic.auto._`, `cats.derived.*`...) also in scope | remove the upstream import; see `kindlings-getting-started` |
| `could not find implicit value ... io.circe.Encoder[A]` at an upstream call (`asJson`, `writeToString`, `ConfigSource.load`) | upstream searches for its own type class, whose implicit scope does not contain Kindlings' `derived` | define `implicit val` / `given` / `derives` for that root type |
| `value derive is not a member of ...` | `derive` was removed in 0.2.0 | use `derived` |

Errors are reported at the expansion site with Kindlings' own wording, never `diverging implicit expansion` or
`could not find Lazy implicit`. If the message is unclear, turn on debug logging - with logging enabled the logs are
appended to the error.

## Debug logging

Two equivalent switches per module: a scoped import (logs every derivation in that file) or a global scalac option.
The output (compiler `info` messages) shows which rule handled each type, which implicits were summoned and the
generated code.

```scala
import hearth.kindlings.circederivation.debug._   // per file
```

```scala
scalacOptions += "-Xmacro-settings:circeDerivation.logDerivation=true"   // whole module
```

## Settings namespaces

Timeout and derivation-policy keys live under the module's namespace; `logDerivation` mostly does too.

| Module | Namespace (`<ns>.timeout`, `<ns>.policy.*`) | Global logging key | Debug import (`hearth.kindlings.` + ...) |
|---|---|---|---|
| circe-derivation | `circeDerivation` | `circeDerivation.logDerivation=true` | `circederivation.debug._` |
| jsoniter-derivation | `jsoniterDerivation` | `jsoniterDerivation.logDerivation=true` | `jsoniterderivation.debug._` |
| tapir-schema-derivation | `tapirSchemaDerivation` | `tapirSchemaDerivation.logDerivation=true` | `tapirschemaderivation.debug._` |
| pureconfig-derivation | `pureconfigDerivation` | `pureconfigDerivation.logDerivation=true` | `pureconfigderivation.debug._` |
| sconfig-derivation | `sconfigDerivation` | `sconfigDerivation.logDerivation=true` | `sconfigderivation.debug._` |
| avro-derivation | `avroDerivation` | `avroDerivation.logDerivation=true` | `avroderivation.debug._` |
| yaml-derivation | `yamlDerivation` | `yamlDerivation.logDerivation=true` | `yamlderivation.debug._` |
| xml-derivation | `xmlDerivation` | `xmlDerivation.logDerivation=true` | `xmlderivation.debug._` |
| ubjson-derivation | `ubjsonDerivation` | `ubjsonDerivation.logDerivation=true` | `ubjsonderivation.debug._` |
| cats-derivation | `catsDerivation` | `catsDerivation.logDerivation=true` | `catsderivation.debug._` |
| cats-tagless-derivation | `catsTaglessDerivation` | `catsTaglessDerivation.logDerivation=true` | `catstaglessderivation.debug._` |
| scalacheck-derivation | `scalacheckDerivation` | `scalacheckDerivation.logDerivation=true` | `scalacheckderivation.debug._` |
| diff-derivation | `diffDerivation` | `diffDerivation.logDerivation=true` (0.4.0: import only) | `diffderivation.debug._` |
| fast-show-pretty | `fastShowPrettyDerivation` | `fastShowPrettyDerivation.logDerivation=true` (0.4.0: only `fastShowPretty.logDerivation=true`, still accepted) | `fastshowpretty.debug._` |
| di / di-cats | - | `di.logGeneration=true` / `diCats.logGeneration=true`; wiring graph `di.logWiring=tree` or `=mermaid` (`diCats.logWiring`) | `di.debug._` / `dicats.debug._` |
| mock | - | `mock.logGeneration=true` | `mock.debug._` |
| optics | - | `optics.logGeneration=true` | `optics.debug._` |

Module-specific extras exist (e.g. `tapirSchemaDerivation.preferConfig=circe` when both circe and jsoniter configs are
visible) - see the module's skill. Hearth itself reads the `hearth.*` namespace (flame graphs below).

## Derivation timeout

Every derivation module aborts an expansion that takes longer than **5 seconds** (default) with
`Macro '<name>' timed out after 5000ms`. Large ADTs, very wide case classes and - most often - slow or overloaded CI
machines (parallel compilation, cold JIT) hit it; a build that compiles locally but times out on CI is the classic
symptom. Raise it per module:

```scala
scalacOptions ++= Seq(
  "-Xmacro-settings:circeDerivation.timeout=30s",
  "-Xmacro-settings:jsoniterDerivation.timeout=1m"
)
```

| Format | Example | Meaning |
|---|---|---|
| plain integer | `30` | seconds |
| seconds | `30s`, `30second`, `30seconds` | seconds |
| milliseconds | `5000ms`, `5000millis`, `5000milliseconds` | milliseconds |
| minutes | `1m`, `1minute`, `5minutes` | minutes |

- In 0.4.0 a bare integer is parsed as seconds (Hearth parses `30` as a number). Users reported bare integers being
  ignored with 0.3.x; the explicit `30s` form works everywhere.
- An unrecognised string emits a compiler warning and uses 5 s; a zero/negative value also falls back to 5 s.
- The timeout is per macro expansion and per module namespace; set it for every module that needs it.
- **Canary**: to check that a setting reaches the compiler at all (mdoc, Mill, IDE, a sub-project), set
  `<ns>.timeout=1ms` temporarily - compilation must fail with `timed out after 1ms`. If it does not, the option is
  not being passed.
- If an expansion is genuinely slow, find out why with a flame graph (below) rather than only raising the limit; the
  same type derived at many call sites can be stored once in an `implicit val` / `given`.

## Passing `-Xmacro-settings`

Pass **one `-Xmacro-settings:key=value` option per setting**. Scala 3 splits a single option on commas
(`-Xmacro-settings:a=1,b=2` becomes two settings) while Scala 2 keeps it as one string (the value of `a` would be
`1,b=2`) - so comma-joined settings are not portable. For list values (policy `allowedScopes`) Kindlings splits on
`;` or `|`, never `,`.

```scala
// sbt (use Test / scalacOptions for test-only settings)
scalacOptions += "-Xmacro-settings:circeDerivation.timeout=30s"
```

```scala
// Mill 1.x (Mill 0.11/0.12: T { ... } instead of Task { ... })
override def scalacOptions = Task { super.scalacOptions() ++ Seq("-Xmacro-settings:circeDerivation.timeout=30s") }
```

```scala
//> using option -Xmacro-settings:circeDerivation.timeout=30s
```

On the scala-cli command line: `scala-cli compile . -O -Xmacro-settings:circeDerivation.timeout=30s`.

**mdoc**: users have reported that settings in the project's `scalacOptions` / `mdoc.properties` did not reach mdoc's
snippet compiler. Verify with the 1ms canary; if it compiles, pass the options through mdoc's own
`--scalac-options` argument (e.g. via `mdocExtraArguments` in sbt-mdoc), one `-Xmacro-settings:` per setting.

## Flame graphs (slow derivations)

```scala
scalacOptions ++= Seq(
  "-Xmacro-settings:hearth.mioBenchmarkScopes=true",
  "-Xmacro-settings:hearth.mioBenchmarkFlameGraphDir=/tmp/kindlings-flamegraphs"
)
```

Writes one `.speedscope.json` per macro expansion (also when it times out); open it at <https://www.speedscope.app/>.
Look for repeated implicit searches and rules evaluated for the same type many times.

## Gotchas

- **Settings appear to be ignored** - wrong namespace (fast-show-pretty 0.4.0: logging only under `fastShowPretty`;
  diff 0.4.0: no global logging key), several settings joined with commas (see above), or the build tool not
  forwarding options. Use the 1ms canary.
- **`Method too large: ...decode_X$macro$1`** - the JVM's 64 KB method limit.
  [#308](https://github.com/kubuszok/kindlings/issues/308): `AvroDecoder` for a case class with 88+ defaulted fields
  fails on 0.4.0 (fixed after 0.4.0; wide decoders of other modules were also shrunk below the JIT limit). On 0.4.0:
  write that one instance by hand, or split the record into nested case classes (this changes the Avro schema).
  Kindlings modules must all be on the same version, so downgrading only the Avro module is not an option.
- **`HearthAssertionError: ... MIO timeout is already set — you are re-entering runToExprOrFail`** (Hearth bug, not
  fixed) - Scala 2.13, when a `val` holding a derived instance has **no explicit type**
  (`implicit val codec = KindlingsJsonValueCodec.derived[A]`) and the same file derives a type with a sealed-trait
  field. Fix: always annotate the type of vals/defs holding derived instances
  (`implicit val codec: JsonValueCodec[A] = ...`).
- **`assertion failed: missing outer accessor in class X`** (Scala 3 compiler crash, Hearth bug, not fixed) - a sealed
  trait declared inside a class (test suite, `.sc` script) whose case objects live in its companion. Declare the
  hierarchy at the top level or in an `object`.
- **Error text with `\u001b[35m`-style codes** (raw `compileErrors` string, IDE problem view) - 0.4.0 on Scala 2.13
  coloured type names in derivation errors; fixed after 0.4.0 (debug logs keep colours). On 0.4.0 strip
  `\u001b\[[0-9;]*m` before comparing.
- **NullPointerException / `null` instance at runtime** - with 0.1.x `derive` the macro could pick up the very
  `implicit val` being defined (issue #119, tapir `implicit val s: Schema[A] = KindlingsSchema.derive[A]`); use
  `derived` (0.2.0+; tapir: `KindlingsSchema.derived[A].schema`). Instances in different objects that refer to each
  other can still hit ordinary Scala initialisation order - use `implicit lazy val` (Scala 3 `given`s without
  parameters are already lazy).
- **`-Werror` fails on a warning in generated code** - warnings from macro-expanded code are reported at the expansion
  site in your file, so `@nowarn` on the derived type does not help. Known cases are fixed (Scala 3 enum "unchecked
  type test" in cats Eq/Order and Diff: 0.3.2; deprecated API calls under Scala 3.10: 0.4.0). For a new one, silence it
  with a `-Wconf:msg=<regex>:s` filter and report it.
- **sbt metaspace grows with every `clean; compile` in a long-running sbt server** - fixed in 0.3.2 (Hearth 0.4.2).
- **`[info] Extension ... was already loaded in this macro expansion` spam** - fixed in 0.1.1.
- **Kindlings 0.4.0 needs Hearth 0.4.5+** on the compile classpath - do not force an older `com.kubuszok::hearth`
  with `dependencyOverrides`; and do not mix Kindlings artifacts of different versions (0.4.0 is not binary compatible
  with 0.3.x).
- **xml open bugs** (not fixed): `XmlConfig.withEnumAsStrings` has no effect; `@xmlWrapper` is ignored;
  `@xmlAttribute` on a non-text field writes its `toString`. See `kindlings-xml`.
- **Integration not picked up** - integration jars are discovered via the compile classpath of the module where the
  derivation expands; `% Test`-scoped or added only to a downstream module, they are invisible. See
  `kindlings-integrations`.

## Known bugs fixed in later versions

| Symptom | Issue | Fixed in |
|---|---|---|
| `Extension ... was already loaded` warnings | #65 | 0.1.1 |
| `.derive` existed next to `.derived`; tapir `derive` picked the val being defined (compile error / runtime null) | #119 | 0.2.0 (`derive` removed) |
| circe: absent `Option[A]` field failed when `A` is derived | #120 | 0.2.0 |
| pureconfig: `class CollectionBuildException in object PureConfigDerivationUtils cannot be accessed` | #132 | 0.3.0 |
| sbt metaspace / class-metadata leak across `clean; compile` | #199 | 0.3.2 |
| Scala 3 `derives` on a generic type encoded `String` as an array of chars | #206 | 0.3.2 |
| "unchecked type test" warnings for Scala 3 enums (cats Eq/Order, Diff) breaking `-Werror` | #184 | 0.3.2 |
| jsoniter: case objects / parameterless enum cases failed to decode in wrapper and discriminator modes | #196 | 0.3.2 |
| circe: product decoders accepted non-object JSON | #235 | 0.3.4 |
| jsoniter/ubjson: absent fields decoded as `null`/`0`, missing required fields accepted | #264 | 0.3.4 |
| Scala 2: derivation failed when a member named `scala`, `java`, `cats`, `io`, `sttp`... was in scope | - | 0.4.0 |
| scalacheck: `Arbitrary` for recursive sealed traits overflowed the stack | - | 0.4.0 |
| a derivation error with a `null` message crashed the macro with an NPE | - | 0.4.0 |
| avro: `Method too large` for `AvroDecoder` of 88+ defaulted fields | #308 | after 0.4.0 |
| derivation error messages contained ANSI colour codes (Scala 2.13) | - | after 0.4.0 |
| policy: opt-in mode also gated collections/`Option`/value types (`derived[List[User]]` denied); untyped `val x = X.derived[A]` failed with "illegal cyclic reference" / "Recursive value needs type" | - | after 0.4.0 |
| diff: `modifyField(name).using(d)` ignored; `diffDerivation.logDerivation` not read; ANSI codes in plain `seqDiff` names | - | after 0.4.0 |
| fast-show-pretty: `fastShowPrettyDerivation.logDerivation` not read | - | after 0.4.0 |
| xml: absent `Option`/collection elements failed; empty `String` failed with `MissingContent`; `Option` attributes written as `Some(v)` (also with a runtime config); `withAttributesByDefault` output did not decode (`MissingElement`); `String`s trimmed; runtime-config encoder of a wide case class ran the compiler out of memory | - | after 0.4.0 |
| scalacheck: `ClassCastException: scala.util.Right cannot be cast to ...` for `Either` smart-constructor value types | - | after 0.4.0 |
| cats: `Functor.derived` for recursive case classes (`found Tree[W2], required Tree[Any]`); `ConsK` `ClassCastException` for a non-`List` tail | - | after 0.4.0 |
| circe (Scala 3): `KindlingsCodecAsObject.derive` lacked `enumAsStrings` | - | after 0.4.0 |
| di: unused members of `autowireMembersOf(module)` reported as errors (garbled message) | - | after 0.4.0 |
| avro (Scala 2): `<empty>` namespace for types in the empty package | - | after 0.4.0 |
| tapir: the "Multiple JSON library configurations" hint printed non-compiling code | - | after 0.4.0 |

Upgrading across 0.3.4 and 0.4.0 changes several wire formats - read `kindlings-migration` before upgrading.

## Links

- Debugging & diagnostics: <https://kindlings.readthedocs.io/en/0.4.0/debugging/>
- FAQ: <https://kindlings.readthedocs.io/en/0.4.0/faq/>
- Release notes: <https://github.com/kubuszok/kindlings/releases>
- Issues: <https://github.com/kubuszok/kindlings/issues>
