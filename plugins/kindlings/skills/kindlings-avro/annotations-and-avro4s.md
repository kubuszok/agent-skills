# kindlings-avro: annotations and avro4s mapping (Kindlings 0.4.0)

All annotations: `import hearth.kindlings.avroderivation.annotations._`.

## Annotations

| Kindlings | Target | Effect | avro4s equivalent |
|---|---|---|---|
| `@avroName("Name")` | type | schema name; wins over `@avroErasedName` / `@avroFqnParamNames` | `@AvroName` |
| `@fieldName("name")` | field | Avro field name (wins over `transformFieldNames`) | `@AvroName` on a field |
| `@avroNamespace("ns")` | type, field | namespace (field > type > `AvroConfig.namespace` > package) | `@AvroNamespace` |
| `@avroDoc("text")` | type, field | `doc` | `@AvroDoc` |
| `@avroProp("key", "value")` | type, field | custom property, stackable | `@AvroProp` |
| `@avroAlias("old")` | type, field | alias for evolution, stackable | `@AvroAlias` |
| `@avroDefault("json")` | field | schema default as a JSON literal (`"8080"`, `"\"info\""`) | none (avro4s uses constructor defaults only) |
| `@avroNoDefault` | field | no schema default even with a Scala default | `@AvroNoDefault` |
| `@transientField` | field | not in the schema; decoded as its (required) default | `@AvroTransient` |
| `@avroFixed(size)` | `Array[Byte]` field | FIXED instead of BYTES | `@AvroFixed` |
| `@avroScalePrecision(precision, scale)` | `BigDecimal` field | per-field decimal; note the order | `@AvroScalePrecision(scale, precision)` (ignored by avro4s 5) / implicit `ScalePrecision` |
| `@avroSortPriority(n: Int)` | subtype | UNION/ENUM order, higher first | `@AvroSortPriority(Float)` |
| `@avroEnumDefault("X")` | sealed trait of case objects | ENUM default | `@AvroEnumDefault` (avro4s 4 only) |
| `@avroError` | type | record marked as Avro error | `@AvroError` (avro4s 5 only) |
| `@avroErasedName` | generic type | no `__A_B` suffix in the name | `@AvroErasedName` |
| `@avroFqnParamNames` | generic type | fully-qualified type-argument names in the name | none |

## avro4s API mapping

| avro4s | Kindlings |
|---|---|
| `AvroSchema[A]` / `SchemaFor[A].schema` | `AvroSchemaFor.schemaOf[A]` / `AvroSchemaFor.derived[A].schema` |
| `Encoder[A]` / `Decoder[A]` (derived automatically) | `AvroEncoder.derived[A]` / `AvroDecoder.derived[A]` (put them in companions or use `derives`) |
| `ToRecord[A].to(a)` / `FromRecord[A].from(r)` | `encoder.encode(a)` (returns `Any`, a `GenericRecord` for case classes) / `decoder.decode(r)` |
| `AvroOutputStream.binary` / `AvroInputStream.binary` | `AvroIO.toBinary` / `AvroIO.fromBinary` (single values, schema-less binary) |
| `AvroOutputStream.json` / `AvroInputStream.json` | `AvroIO.toJson` / `AvroIO.fromJson` |
| `FieldMapper` (`SnakeCase`) | `AvroConfig.withSnakeCaseFieldNames` / `withTransformFieldNames(f)` |
| implicit `ScalePrecision` | `AvroConfig.withDecimalConfig(precision, scale)` |
| custom `SchemaFor` for `timestamp-micros` / `-nanos` | `withInstantPrecision` / `withLocalDateTimePrecision` |
| default `BigDecimal` / `OffsetDateTime` encodings | `AvroConfig.avro4sDefaults` |

Avro container files (`DataFileWriter` with an embedded schema) are not wrapped: use Avro's API with
`encoder.schema` and `encoder.encode(a)`.

## Type support (parity with avro4s 4.x unless noted)

UUID, `java.time` logical types, `java.sql.Date`/`Timestamp`, value classes (unwrapped), case classes -> RECORD,
sealed traits -> UNION, case-object families and Java enums -> ENUM, `scala.Enumeration` -> ENUM (named after the
enumeration object), `Either` -> UNION, `Option` -> UNION(null, T), `Array[Byte]`/`Seq[Byte]`/`ByteBuffer` -> BYTES,
recursive types, generic record names `Name__A_B`. Extra: Scala 3 named tuples, union types, literal types, opaque
types; refined/iron/neotype/newtype via Kindlings integration modules.

Source of truth: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#avro-derivation
