---
name: kindlings-avro
description: >-
  Kindlings Avro derivation (kindlings-avro-derivation, JVM-only, package hearth.kindlings.avroderivation) -
  deriving Apache Avro schemas, encoders and decoders with AvroSchemaFor.derived / schemaOf, AvroEncoder.derived /
  encode, AvroDecoder.derived / decode, AvroIO.toBinary/fromBinary/toJson/fromJson, AvroConfig (withNamespace,
  withSnakeCaseFieldNames, withDecimalConfig, withInstantPrecision, withLocalDateTimePrecision,
  withOffsetDateTimeAsIsoString, withoutScalaDefaultsInSchema, avro4sDefaults) and annotations (@avroName,
  @avroNamespace, @avroDoc, @avroDefault, @avroNoDefault, @avroAlias, @avroFixed, @avroScalePrecision,
  @avroSortPriority, @avroEnumDefault, @fieldName, @transientField). Use when replacing avro4s (SchemaFor, Encoder,
  Decoder, AvroSchema, @AvroName, ScalePrecision) with Kindlings, on schema-registry compatibility or schema
  evolution questions, BigDecimal/OffsetDateTime/tuple schema differences, "Method too large" for wide case classes
  (issue 308, fixed after 0.4.0), or avroDerivation timeouts.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings Avro derivation

Derives Avro `Schema`s plus encoders/decoders (to and from Avro generic values such as `GenericRecord`) for case
classes, sealed traits, Scala 3 enums, Java enums, `Enumeration`s, value classes, tuples, `Either`, named tuples,
opaque and union types, with one API on Scala 2.13 and 3. It replaces avro4s (4.x on Scala 2, 5.x on Scala 3).
**JVM only** (Apache Avro is JVM-only).

**Version:** written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
https://kindlings.readthedocs.io/en/0.4.0/avro-derivation/ (replace `0.4.0` with the version used).

Generic topics: `kindlings-getting-started`, `kindlings-troubleshooting` (errors, timeouts, debug output),
`kindlings-derivation-policy`, `kindlings-migration`, `kindlings-integrations` (refined/iron, cats collections).
Full annotation reference and avro4s mapping: [annotations-and-avro4s.md](annotations-and-avro4s.md).

## Dependency

```scala
libraryDependencies += "com.kubuszok" %% "kindlings-avro-derivation" % "0.4.0" // %% only: JVM
//> using dep com.kubuszok::kindlings-avro-derivation:0.4.0
```

`org.apache.avro:avro` comes transitively. Remove avro4s from code using Kindlings.

## Core usage

```scala
import hearth.kindlings.avroderivation._

case class Person(name: String, age: Int, email: Option[String] = None)
object Person {
  implicit val encoder: AvroEncoder[Person] = AvroEncoder.derived[Person]
  implicit val decoder: AvroDecoder[Person] = AvroDecoder.derived[Person]
}

val schema: org.apache.avro.Schema = Person.encoder.schema // or AvroSchemaFor.schemaOf[Person]
val record: Any = Person.encoder.encode(Person("Ann", 30))   // a GenericRecord
val back: Person = Person.decoder.decode(record)
val bytes: Array[Byte] = AvroIO.toBinary(Person("Bob", 25))
val p: Person = AvroIO.fromBinary[Person](bytes)
```

Scala 3: `case class Person(...) derives AvroEncoder, AvroDecoder` (also `AvroSchemaFor`), or
`given AvroEncoder[Person] = AvroEncoder.derived`. Scala 3 only: `import hearth.kindlings.avroderivation.syntax.*` for
`value.toAvroBinary`, `value.toAvroJson`, `bytes.fromAvroBinary[A]`, `json.fromAvroJson[A]`.

| API | Result |
|---|---|
| `AvroSchemaFor.derived[A]` / `AvroSchemaFor.schemaOf[A]` | `AvroSchemaFor[A]` (`.schema`) / `org.apache.avro.Schema` |
| `AvroEncoder.derived[A]` / `AvroEncoder.encode[A](a)` | `AvroEncoder[A]` (`encode(a): Any`, `.schema`) / `Any` |
| `AvroDecoder.derived[A]` / `AvroDecoder.decode[A](v)` | `AvroDecoder[A]` (`decode(v: Any): A`, `.schema`) / `A` |
| `AvroIO.toBinary`, `fromBinary`, `toJson`, `fromJson` | binary / Avro-JSON with the instance's own schema |

`AvroEncoder` and `AvroDecoder` extend `AvroSchemaFor`. All derivations take an implicit/`using` `AvroConfig` (default
`AvroConfig.default`); pass one with `derived[A](cfg)` (Scala 2) / `derived[A](using cfg)` (Scala 3). **Derive the
encoder, decoder and schema of a type with the same config**, otherwise their schemas differ.

## Configuration

```scala
implicit val config: AvroConfig = AvroConfig.default
  .withNamespace("com.example")
  .withSnakeCaseFieldNames
  .withDecimalConfig(precision = 10, scale = 2)
```

| Field (Kindlings default) | Builder | Notes |
|---|---|---|
| `namespace` (`None`: the package) | `withNamespace(ns)` | precedence: field `@avroNamespace` > type `@avroNamespace` > config > package |
| `transformFieldNames` (`identity`) | `withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`, `withTransformFieldNames(f)` | |
| `transformConstructorNames` (`identity`) | `withTransformConstructorNames(f)` | sealed subtypes |
| `decimalConfig` (**`None`: `BigDecimal` as STRING**) | `withDecimalConfig(precision, scale)` | BYTES + `decimal` logical type |
| `instantPrecision` (`TimestampPrecision.Millis`) | `withInstantPrecision(TimestampPrecision.Micros)` | also `java.sql.Timestamp` |
| `localDateTimePrecision` (`TimestampPrecision.Nanos`, as avro4s) | `withLocalDateTimePrecision(p)` | |
| `offsetDateTimeAsIsoString` (**`false`: UTC `timestamp-millis` long**) | `withOffsetDateTimeAsIsoString` | avro4s: ISO-8601 string |
| `scalaDefaultsInSchema` (`true`) | `withoutScalaDefaultsInSchema` / `withScalaDefaultsInSchema` | |

`AvroConfig.avro4sDefaults` switches every default-value difference to avro4s' behaviour (`BigDecimal` as
`decimal(8, 2)`, `OffsetDateTime` as an ISO string); chain other builders on it.

Logical types: `UUID` -> string/`uuid`, `Instant` -> long/`timestamp-millis`, `LocalDate` -> int/`date`, `LocalTime`
-> long/`time-micros`, `LocalDateTime` -> long/`timestamp-nanos`, `java.sql.Date` -> `date`. `Option[A]` is
`UNION(null, A)`, sealed traits are UNIONs (`@avroSortPriority`, higher first), sealed families of case objects and
Java enums are ENUMs, generic records are named `Name__A_B`.

Key annotations (`import hearth.kindlings.avroderivation.annotations._`): `@avroName` (type), `@fieldName` (field),
`@avroNamespace`, `@avroDoc`, `@avroAlias` / `@avroProp` (stackable), `@avroDefault("json")`, `@avroNoDefault`,
`@transientField` (needs a default), `@avroFixed(size)`, `@avroScalePrecision(precision, scale)`,
`@avroSortPriority(n: Int)`, `@avroEnumDefault("X")`, `@avroError`, `@avroErasedName`, `@avroFqnParamNames`. Details:
[annotations-and-avro4s.md](annotations-and-avro4s.md).

## Defaults and schema evolution

- Scala default values become schema defaults (as avro4s; for a union, the default's branch is moved first).
  `@avroDefault("json")` overrides the value, `@avroNoDefault` removes it, `withoutScalaDefaultsInSchema` keeps only
  `@avroDefault` ones.
- Defaults in the schema are what lets Avro schema resolution read **old data with a newer reader schema** that added
  fields. With `withoutScalaDefaultsInSchema` that fails with `missing required field`.
- Decoding a `GenericRecord` directly: a field with a Scala default gets the default when absent or undecodable; a
  missing field without a default fails, a missing `Option` field is `None`.
- Renames: keep the old name readable with `@avroAlias("oldName")` on the field or type.
- Integral widening (`Int` -> `Long`, ...) is accepted when decoding; `Float` -> `Double` is not (as avro4s).
- `AvroIO.fromBinary` / `fromJson` read with the decoder's own schema as **both** writer and reader schema. For data
  written with an older schema, read it with Avro's `GenericDatumReader(writerSchema, decoder.schema)` and pass the
  resulting record to `decoder.decode`.

## Differences from avro4s

Checked against avro4s 4.x (Scala 2.13) and 5.x (Scala 3): schemas, binary encodings, cross-decoding, invalid records,
schema evolution. Differences:

| Topic | avro4s | Kindlings | To match avro4s |
|---|---|---|---|
| `BigDecimal` | BYTES `decimal(8, 2)` | STRING | `withDecimalConfig(8, 2)` or `avro4sDefaults` |
| `OffsetDateTime` | ISO-8601 STRING (`datetime-with-offset`) | `timestamp-millis` LONG, UTC (offset dropped) | `withOffsetDateTimeAsIsoString` or `avro4sDefaults` |
| Tuple record names | `scala.Tuple2` for every tuple | `scala.Tuple2__A_B` (different tuples no longer collide) | none (design decision) |
| `@AvroEnumDefault`, `@AvroScalePrecision` on avro4s 5 | ignored | honoured on both Scala versions | - |
| avro4s 5 gaps (recursive types, value classes, `Enumeration`, `FieldMapper`) | unsupported on 5.x | supported | - |
| `@avroScalePrecision` parameter order | avro4s 5: `(scale, precision)` | `(precision, scale)` | swap arguments |
| `@avroSortPriority` type | `Float` | `Int` | - |
| Namespace of a type in the empty package | avro4s 5: none; avro4s 4: `empty` (records) / `<empty>` (enums, invalid Avro) | none on both Scala versions (0.4.0 on Scala 2: `<empty>`) | `@avroNamespace` |
| Shapeless `Coproduct` UNIONs, avro4s-cats/-refined/-kafka | yes | not ported (use Kindlings integration modules) | - |

On Scala 2, ENUM symbols and subtype order follow names (Scala 2 class files keep no declaration order); on Scala 3
the declaration order.

**Migrating with a schema registry:** compare old and new schemas before deploying. Use `AvroConfig.avro4sDefaults`
and check tuples (renamed records) - otherwise the new schemas may be incompatible with registered ones.

## Settings and debugging

- Settings namespace: `avroDerivation`, e.g. `-Xmacro-settings:avroDerivation.timeout=30s`,
  `avroDerivation.logDerivation=true`, `avroDerivation.policy.*`.
- Debug one scope: `import hearth.kindlings.avroderivation.debug._`.
- Policy opt-in import: `import hearth.kindlings.avroderivation.policy.allowDerivationForAvroDerivation`.

## Gotchas

- **`Method too large: ...decode_<Type>$macro...` (issue #308, 0.4.0 only, fixed after 0.4.0)** - the `AvroDecoder`
  of a case class with ~88+ fields **with default values** exceeds the JVM's 64 KB method limit (from ~26 defaulted
  fields it is too big to be JIT-compiled). On 0.4.0: group fields into nested case classes (changes the schema) or
  hand-write the decoder for that type.
- A field instance given by a user `implicit def` is evaluated once per derived encoder/decoder, not per call (after
  0.4.0).
- **Schema differs between writer and reader** - encoder and decoder derived with different `AvroConfig`s or
  annotations; derive both with the same config.
- **`BigDecimal` written as a string** - Kindlings default; set `withDecimalConfig` or `@avroScalePrecision`.
- **Old records fail with `missing required field`** - the new field has no schema default (`@avroNoDefault`,
  `withoutScalaDefaultsInSchema`) or `AvroIO` read old bytes with the new schema as writer schema (see above).
- **Scala.js / Scala Native** - not supported (JVM only).
- **`@transientField` compile error** - the field needs a default value.
- **Scala 2: `HearthAssertionError: Hearth assertion failed: MIO timeout is already set`** - a `val` holding a derived
  instance has no explicit type (`val enc = AvroEncoder.derived[A]`) and the same file derives a type with a sealed-trait
  field: Scala 2 types the un-annotated `val` while the other derivation is running. Give such vals an explicit
  type (always do so for `implicit val`s).

## Links

- Guide: https://kindlings.readthedocs.io/en/0.4.0/avro-derivation/
- Differences: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#avro-derivation
- Source: https://github.com/kubuszok/kindlings/tree/0.4.0/avro-derivation/src/main
- Issue #308: https://github.com/kubuszok/kindlings/issues/308
