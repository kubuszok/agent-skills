# Kindlings 0.4.0 vs upstream: differences you must know

Condensed from the Kindlings feature-parity page
(<https://kindlings.readthedocs.io/en/0.4.0/feature-parity/>), which is backed by differential "oracle" tests against
each upstream. Everything not listed here behaves like upstream. Kindlings-only additions are opt-in unless stated.

## All modules: order of sealed subtypes

Where the order is observable (Avro ENUM symbols/UNION members, schema subtypes, order subtypes are tried in when
decoding untagged values, generators, `Order` across subtypes, names in error messages):

- **Scala 3**: declaration order (as upstream's `Mirror`-based derivations).
- **Scala 2**: subtypes sorted by name (simple name in natural order, then full name), identical in every build.
  Upstream Scala 2 derivations (shapeless, Magnolia) sort by *full* name - the two differ only for numbered names
  (`Item2` vs `Item10`) and subtypes declared in different scopes. Java enum constants keep declaration order.

## circe

Replaces circe-generic, circe-generic-extras and Scala 3 core `ConfiguredEncoder/Decoder/Codec`. Nothing is "not
ported".

| Topic | Upstream | Kindlings |
|---|---|---|
| `AnyVal` case classes | Scala 2 generic(-extras): object `{"value":5}`; Scala 3: not derivable | **unwrapped by default** (`5`); `withoutValueClassUnwrapping` restores the object form (also for value-class sum children) |
| Value class over `Option`, field absent | product: missing-field error | default: wrapped `None` (or the field default with `useDefaults`); `withoutValueClassUnwrapping`: missing field |
| Hand-written instance for an intermediate sealed trait | Scala 3 core: used under the intermediate's name; generic-extras: ignored (flattened) | used under the intermediate's name on both Scala versions |
| Wrapper object with several keys (non-strict) | Scala 3: first JSON key naming a constructor; Scala 2: first constructor alphabetically; Scala 2 strict accepts it | Scala 3 behaviour on both; strict decoding rejects it |
| Discriminator + child that is not a JSON object | generic-extras writes `{"Name": value}` but cannot read it; Scala 3 core drops the value | written as `{"Name": value}` and read back |
| Enum map keys | manual `KeyEncoder`/`KeyDecoder` | constructor name (with `transformConstructorNames`) automatically |
| Error messages / cursor history | Scala 2 shapeless wording differs | Scala 3 core wording on both versions |
| `enumAsStrings` on a sum with case classes | compile error | compile error when the config is known at compile time; otherwise runtime failure (decoder `DecodingFailure`, encoder `IllegalArgumentException`) |
| Recursive types | Scala 2 needs `Lazy`; Scala 3 auto broken (circe#1980) | work without wrappers |
| Per-field rename | `@JsonKey` (Scala 2 only) | `@fieldName` (both) |
| Patch decoder with `useDefaults` | generic-extras throws `ClassCastException` | `useDefaults` ignored by `patch` |

Same as upstream: `useDefaults` rules, strict decoding rules, absent `Option` -> `None`, discriminator appended after
fields, tuples as arrays, accumulating decoding, case classes with several parameter lists rejected.

## jsoniter-scala

| Config field | jsoniter-scala default | Kindlings default |
|---|---|---|
| `discriminatorFieldName` | `Some("type")` | `None` (single-key wrapper objects; case objects as strings) |
| `transientDefault` / `transientEmpty` / `transientNone` | `true` | `false` (fields always written) |
| `checkFieldDuplication` | `true` | `false` |
| `mapMaxInsertNumber` / `setMaxInsertNumber` | `1024` | `Int.MaxValue` (no DoS limit unless set) |

`JsoniterConfig.jsoniterScalaDefaults` restores all upstream defaults; the `make*` presets are built on it.

Design differences (not configurable):

- recursive types always allowed (no `allowRecursiveTypes`);
- without a discriminator a case object is also read from `{"Leaf":{}}`;
- a Scala 3 `T | Null` field holding `null` is written as `null` without `transientNull` (upstream throws an NPE);
- with `checkFieldDuplication = false` a repeated key's decoder receives the field default, not the earlier value;
- type-mismatch errors for fields with a default say `expected '{'` (upstream `expected '{' or null`);
- runtime (non-compile-time) configs with contradictory flags throw `IllegalArgumentException` when the codec is created;
- Iron: a missing refined field is a missing required field (upstream with iron-jsoniter decodes `null`).

Everything else (name mappers, `isStringified`, `@named`, `@stringified`, key codecs, `java.time`, tuples, named tuples,
`::`, literal types, plain classes, multiple parameter lists, `nullValue` semantics, limits) matches upstream.

## kittens

- `Show` of zero-field case classes and case objects: `Name()` on both Scala versions (kittens 3: `Name`; kittens 2:
  runtime class name for objects).
- `reduceRightTo` never evaluates later fields when the function short-circuits (kittens evaluates them first).
- `ConsK` is derived for case classes (head + nested tail), **not** for list-like sealed traits (kittens 2 does that).
- A wrapped field whose type constructor is another case class to derive (e.g. `middle: Nel[A]`) needs that instance
  in scope (`implicit val … = Reducible.derived[Nel]`); kittens derives it.
- Apply/Applicative derive for recursive types without overflowing the stack (kittens 3 overflows).
- Additions: `@sensitiveData` redaction in `Show`/`ShowPretty`; Bifunctor/Bifoldable/Bitraverse, Band, Semilattice,
  Group, NonEmptyAlternative, Alternative also on Scala 2.
- Not ported: `cats.sequence` / `lift` / `replicateH`, `MkIterable`.
- Hash values differ from kittens' (only consistency with `Eq` is guaranteed).

## cats-tagless

- No macro annotations (`@autoFunctorK`, `@finalAlg`, `@autoInstrument`) - use `.derived` in a companion.
- No `@experimental` needed on Scala 3; case-class algebras supported on Scala 2 and 3.
- Only `Instrument` from `aop` (no general `Aspect`); no `Derive.const` / `void` / `readerT`, no
  `Derive.semigroupK` / `monoidK`.
- Behaviour of derived instances: no differences found by the oracle tests.

## avro4s

| Topic | avro4s | Kindlings | Upstream behaviour |
|---|---|---|---|
| `BigDecimal` | BYTES + `decimal(8, 2)` | STRING | `withDecimalConfig(8, 2)` or `AvroConfig.avro4sDefaults` |
| `OffsetDateTime` | ISO-8601 STRING (`datetime-with-offset`) | `timestamp-millis` LONG in UTC (offset dropped) | `withOffsetDateTimeAsIsoString` or `avro4sDefaults` |
| Tuple record names | `scala.Tuple2` for every tuple | `scala.Tuple2__A_B` (type arguments) | not configurable (avro4s collides) |
| `@AvroSortPriority` | `Float` | `@avroSortPriority(Int)`; higher first, as upstream | - |
| `@AvroScalePrecision` | `(scale, precision)` (ignored in avro4s 5) | `@avroScalePrecision(precision, scale)`, honoured | - |
| `@AvroEnumDefault`, recursive types, value classes, `Enumeration`, working field mappers | avro4s 5 lacks them | supported on Scala 2 and 3 | - |
| Namespace of a type in the empty package | avro4s 5: none; avro4s 4: `empty` / `<empty>` (enums) | none on both versions (after 0.4.0; 0.4.0 Scala 2: `<empty>`) | `@avroNamespace` |

Scala default values become schema defaults (as avro4s); `withoutScalaDefaultsInSchema` keeps only `@avroDefault`
ones. Not ported: shapeless `Coproduct` unions, `avro4s-cats` / `-refined` / `-kafka` (use Kindlings integrations for
cats/refined).

## pureconfig

No expected differences in reading/writing semantics (failures, paths, `KeyNotFound` candidates, discriminator rules,
empty `Option` omitted on write). Differences in **API**:

- configuration via the global `PureConfig` class and `KindlingsProductHint` / `KindlingsCoproductHint`;
  upstream `ProductHint` / `CoproductHint` implicits, and custom hint implementations, are **not read**;
- annotations `@configKey` and `@transientField` (Kindlings-only);
- `withWrappedSubtypes` for non-enum families (no upstream counterpart);
- the case-object family read from strings needs `withWrappedSubtypes` (no discriminator), like
  `deriveEnumerationReader`; with the default discriminator they are `{ type = name }` objects, like upstream's
  default `FieldCoproductHint`.

Not ported: `pureconfig-cats/-magnolia/-shapeless`, format adapters (`pureconfig-yaml`...), `ConfigSource` (keep
using upstream's).

## tapir

| Topic | tapir | Kindlings |
|---|---|---|
| Required vs optional fields | `Option`s and collections optional | optional exactly when the decoder for the same JSON config accepts the field missing (circe: collections required) |
| Naming / discriminator config | separate `sttp.tapir.generic.Configuration` | read from the circe `Configuration` / `JsoniterConfig` in scope |
| Iron / refined / neotype constraints | validators via tapir-iron / tapir-refined / neotype-tapir | underlying type's schema; import those integrations' schemas to get the validators |
| Maps keyed by scala-newtype (2.13) | `Map_Type_Int` | `Map_Name_Int` |
| Type aliases in names (`NonEmpty`) | alias name | dealiased (`Not[Empty]`) |
| Recursive types on Scala 3 | must use `implicit def`, deadlock risk | work |

Not ported: `Schema.oneOfWrapped`, the full `Schema.derivedEnumeration` builder (`.defaultStringBased`, custom
encode); `.modify(_.path)` is tapir core and still works on the result.

## scala-yaml

Defaults match scala-yaml since 0.4.0 (untagged sealed traits decoded by trying subtypes in order, constructor defaults
used, absent `Option` -> `None`). Opt-ins: `withoutUseDefaults`, `withWrappedSubtypes`, `withDiscriminator(field)`,
`withEmptyCollectionsAsFlow` (prints `[]`/`{}` so empty collections round-trip; upstream prints an empty value that
decodes as `null`). Kindlings also supports Scala 2, Scala 3 Native, Java enums, named tuples, field renames
(`@fieldName`, `@transientField`). Repeated keys (last value wins) and non-scalar keys (`Parameter of a class must
be a scalar value`) behave as scala-yaml after 0.4.0 (0.4.0: first value / key ignored).

## scalacheck (scalacheck-shapeless on 2.13, scalacheck-derived on 3)

- Size 0 (Scala 3): Kindlings still generates a value where scalacheck-derived returns `Gen.fail`.
- Shrinking sealed traits shrinks only within the value's subtype (scalacheck-shapeless also tries other subtypes).
- `Cogen` for sealed traits perturbs with the subtype's `Cogen` then its index (like scalacheck-derived).
- No configuration and no annotations (not needed for generators).

## quicklens

- `.index(i)` with a negative index is a no-op (quicklens for Scala 2 throws `IndexOutOfBoundsException`).
- `.each` works on any container Hearth understands (`Set`, `Array`, Java and cats collections), not only `Seq` /
  `Option` / `Map`.
- Classes with a hand-written `copy` that are neither case classes nor sealed hierarchies are not supported.

## macwire

- `DI.plan` is Kindlings' own endpoint (recursive, cached, configurable); `wire` / `wireRec` / `autowire` follow macwire.
- No request/session proxy scopes (JVM bytecode proxies).
- Only the parameters of the closest enclosing method are candidates (macwire also uses outer methods and lambdas);
  local `val`s before the call site only on Scala 2.
- Only the immediately enclosing class exposes `this`; members of outer enclosing classes are not reachable
  (enclosing objects are).

## ScalaMock

An independent reimplementation of the API (does not depend on ScalaMock): mocks are generated anonymous subclasses,
no reflection/bytecode, so it runs on Scala.js and Native. Mocks need an implicit `MockContext` (or `MockSuite`) instead
of mixing `MockFactory` into a ScalaTest suite; verification is `ctx.verifyExpectations()` or `withExpectations { }`.
Both `(m.f _).expects(...)` and the name-keyed `ctx.expecting("f", ...)` DSLs exist.
