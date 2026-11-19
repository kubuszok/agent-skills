---
name: kindlings-yaml
description: >-
  Deriving scala-yaml (org.virtuslab.yaml) YamlEncoder, YamlDecoder and YamlCodec with kindlings-yaml-derivation on
  Scala 2.13 and 3. Covers KindlingsYamlEncoder, KindlingsYamlDecoder, KindlingsYamlCodec (.derived, derives,
  encode/toYamlString, decode/fromYamlString), the syntax import, YamlConfig (withSnakeCaseMemberNames,
  withDiscriminator, withWrappedSubtypes, withUntaggedSubtypes, withoutUseDefaults, withEnumAsStrings,
  withEmptyCollectionsAsFlow, kindlings03Defaults), @fieldName and @transientField, and differences from
  scala-yaml's own `derives YamlCodec`. Use when code imports hearth.kindlings.yamlderivation, when replacing
  scala-yaml derivation (or needing it on Scala 2), when sealed traits decode into the wrong subtype, when an empty
  list prints as `tags: ` and fails with "Could't construct scala.collection.immutable.List from null", or "Key x
  doesn't exist in parsed document".
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings YAML derivation (`kindlings-yaml-derivation`)

Derives scala-yaml's `YamlEncoder` / `YamlDecoder` / `YamlCodec` at compile time with the same API on Scala 2.13 and
Scala 3 (scala-yaml's own derivation is Scala 3 only). Defaults match scala-yaml's `derives YamlCodec`; extra behaviour
(naming, discriminators, wrapped subtypes) is opt-in through `YamlConfig`.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/yaml-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-yaml-derivation" % "0.4.0" // %% on JVM-only builds
```

```scala
//> using dep com.kubuszok::kindlings-yaml-derivation:0.4.0
```

`org.virtuslab::scala-yaml` (0.3.3 at Kindlings 0.4.0) comes in transitively. JVM, Scala.js and Scala Native, Scala
2.13 and 3.

## Imports

```scala
import hearth.kindlings.yamlderivation._              // KindlingsYaml*, YamlConfig
import hearth.kindlings.yamlderivation.annotations._  // @fieldName, @transientField
import hearth.kindlings.yamlderivation.syntax._       // value.toYamlString, "...".fromYamlString[A]
import org.virtuslab.yaml._                           // scala-yaml's asYaml / as[A] keep working
```

## Core usage

`KindlingsYamlEncoder[A] extends YamlEncoder[A]`, `KindlingsYamlDecoder[A] extends YamlDecoder[A]`,
`KindlingsYamlCodec[A] extends YamlEncoder[A] with YamlDecoder[A]`, so derived instances work with scala-yaml's own API.

```scala
import hearth.kindlings.yamlderivation._
import org.virtuslab.yaml._

case class Person(name: String, age: Int = 18)

// Scala 2.13 (also valid on Scala 3)
implicit val personCodec: KindlingsYamlCodec[Person] = KindlingsYamlCodec.derived[Person]

// Scala 3
given KindlingsYamlCodec[Person] = KindlingsYamlCodec.derived
case class Person3(name: String) derives KindlingsYamlCodec   // or KindlingsYamlEncoder / KindlingsYamlDecoder

Person("Alice", 30).asYaml          // scala-yaml syntax, uses the derived instance
"name: Bob".as[Person]              // Right(Person(Bob,18)) - constructor default used
```

Inline one-shot helpers (derive and run in one call, no instance kept):

| Method | Returns |
|---|---|
| `KindlingsYamlEncoder.encode[A](value)` | `org.virtuslab.yaml.Node` |
| `KindlingsYamlEncoder.toYamlString[A](value)` | `String` |
| `KindlingsYamlDecoder.decode[A](node)` | `Either[ConstructError, A]` |
| `KindlingsYamlDecoder.fromYamlString[A](yaml)` | `Either[YamlError, A]` |
| `value.toYamlString` / `yaml.fromYamlString[A]` (`syntax._`) | as above |

Every method takes an implicit `YamlConfig` (default `YamlConfig.default`, found in its companion). Nested types
(fields, subtypes, collection elements) are derived recursively inside one macro expansion; instances you provide
(`implicit`/`given` `YamlEncoder[X]` / `YamlDecoder[X]`) win over derivation. `derived` is an implicit/given method on
the Kindlings companions ("sanely-automatic"), so `summon[KindlingsYamlEncoder[A]]` derives on demand; a plain
`YamlEncoder[A]` lookup does not see it, so define instances (or `derives`) for the root types you use with
`asYaml` / `as[A]`.

## Configuration (`YamlConfig`)

```scala
implicit val yamlConfig: YamlConfig = YamlConfig.default   // Scala 3: given YamlConfig = ...
  .withSnakeCaseMemberNames
  .withDiscriminator("type")
  .withSnakeCaseConstructorNames
```

| Builder | Effect | Default |
|---|---|---|
| `withSnakeCaseMemberNames` / `withKebabCaseMemberNames` / `withPascalCaseMemberNames` / `withScreamingSnakeCaseMemberNames` | field name transform | names as declared |
| `withTransformMemberNames(f: String => String)` | custom field names | |
| `withSnakeCaseConstructorNames` / `withKebabCaseConstructorNames` / `withTransformConstructorNames(f)` | subtype names (discriminator / wrapper key) | simple names as declared |
| `withDiscriminator(field)` | subtype name stored in `field` of the mapping | off (untagged) |
| `withWrappedSubtypes` | without discriminator: `{ Circle: { radius: 1.0 } }` | off |
| `withUntaggedSubtypes` | without discriminator: write the subtype's own value, decode by trying subtypes in order | **on** (as scala-yaml) |
| `withEnumAsStrings` | sealed families of case objects / Scala 3 enums as plain names | off |
| `withUseDefaults` / `withoutUseDefaults` | absent field with a constructor default uses it / fails | **use defaults** (as scala-yaml) |
| `withEmptyCollectionsAsFlow` / `withoutEmptyCollectionsAsFlow` | `toYamlString` prints empty `[]` / `{}` (also nested) | off (empty value, as scala-yaml) |
| `YamlConfig.kindlings03Defaults` | `withoutUseDefaults.withWrappedSubtypes` - Kindlings 0.3.x behaviour | |

There is no `withPascalCaseConstructorNames` in this module. Absent `Option` fields decode as `None`. Union types are
always wrapped; Java enums and `scala.Enumeration` values are written as their names.

## Annotations (`hearth.kindlings.yamlderivation.annotations`)

```scala
case class User(
  @fieldName("user_name") name: String,     // overrides the config's name transform
  @transientField internalId: Long = 0L     // skipped both ways; MUST have a default
)
```

## Differences from scala-yaml's `derives`

- Works on Scala 2.13 (scala-yaml derivation is Scala 3 only) and on Scala 3 Native.
- Same defaults (oracle-tested on Scala 3: same nodes, tags, decoded values and failure messages such as
  `Key x doesn't exist in parsed document`), plus opt-in config, `@fieldName` / `@transientField`, Java enums, named
  tuples, value classes, maps, recursive types.
- Untagged subtype order: Scala 3 tries subtypes in declaration order; Scala 2 in the order of the subtypes' names
  (Scala 2 class files do not record declaration order). The first subtype that decodes wins, so overlapping
  subtypes are ambiguous - use `withDiscriminator` or `withWrappedSubtypes` for unambiguous ADTs.
- A repeated key in a mapping decoded as a case class gives its **last** value, and a non-scalar key fails with
  `Parameter of a class must be a scalar value`, as scala-yaml (0.4.0: first value / key ignored).
- Derived encoders and decoders resolve field/subtype instances (e.g. an `implicit def` `YamlEncoder`) and, with a
  `YamlConfig` only known at runtime, the transformed field (`transformMemberNames`) and subtype names once per instance,
  not per call (after 0.4.0). Inline `KindlingsYamlEncoder.encode` / `KindlingsYamlDecoder.decode` compute them on every
  call.

## Gotchas

- **Wrong subtype decoded / ADT loses its type.** Default untagged encoding (as scala-yaml): `Circle(1.0)` is written as
  `r: 1.0` with no type info, and decoding picks the first subtype that fits. Fix: `withDiscriminator("type")` or
  `withWrappedSubtypes` on both writer and reader side.
- **Upgrading from Kindlings 0.3.x changes the wire format.** 0.4.0 switched to scala-yaml's defaults (untagged
  subtypes, constructor defaults on). To keep old YAML readable/writable use `implicit val c: YamlConfig =
  YamlConfig.kindlings03Defaults`.
- **Empty collection does not round-trip through text**: `toYamlString(Box(Nil))` prints `tags: `, which reads back as
  `null` → `Could't construct scala.collection.immutable.List from null`. Same as scala-yaml's printer. Fix:
  `YamlConfig.default.withEmptyCollectionsAsFlow` (prints `[]` / `{}`), or round-trip through `Node`
  (`decode(encode(v))`).
- **Missing field with a default fails** only under `withoutUseDefaults` / `kindlings03Defaults`.
- **`@transientField on field 'x' of T requires a default value`** (compile error): give the field a default.
- **Config ignored**: the implicit `YamlConfig` must be visible where `derived` / `toYamlString` is expanded (not just
  where the instance is used).
- **Ambiguous implicits**: do not keep scala-yaml's `derives YamlCodec` and a Kindlings instance for the same type, nor
  two Kindlings instances (`KindlingsYamlEncoder` + `KindlingsYamlCodec`) in the same scope.

## Debugging, timeouts, policy

- Settings namespace: `yamlDerivation`.
- Log one derivation: `import hearth.kindlings.yamlderivation.debug._`; project-wide:
  `scalacOptions += "-Xmacro-settings:yamlDerivation.logDerivation=true"`.
- Timeout (default 5 s): `-Xmacro-settings:yamlDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.yamlderivation.policy._` (`allowDerivationForYamlDerivation`).

Generic details: `kindlings-troubleshooting` (debug output, timeouts, error messages), `kindlings-derivation-policy`
(`yamlDerivation.policy.*`), `kindlings-integrations` (refined / iron / cats collections, no import needed).

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/yaml-derivation/>
- Feature parity (scala-yaml): <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#yaml-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/yaml-derivation/src/main>
