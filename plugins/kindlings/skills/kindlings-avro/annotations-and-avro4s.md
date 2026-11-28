# kindlings-avro: annotations and avro4s mapping (Kindlings 0.4.0)

All annotations: `import hearth.kindlings.avroderivation.annotations._`.

## Annotations

| Kindlings | Target | Effect | avro4s equivalent |
|---|---|---|---|
| `@avroName("Name")` | type, case object (ENUM symbol, after 0.4.0) | schema name; wins over `@avroErasedName` / `@avroFqnParamNames`; also used in generic names of types using it as an argument | `@AvroName` |
| `@fieldName("name")` | field | Avro field name (wins over `transformFieldNames`) | `@AvroName` on a field |
| `@avroNamespace("ns")` | type, field | namespace (field > type > `AvroConfig.namespace` > package); on a field it moves every named type below it, on a sealed trait it is inherited by subtypes (after 0.4.0) | `@AvroNamespace` |
| `@avroDoc("text")` | type, field | `doc` | `@AvroDoc` |
| `@avroProp("key", "value")` | type, field | custom property, stackable; the value is a plain String (after 0.4.0; 0.4.0 parsed JSON) | `@AvroProp` (avro4s 4) |
| `@avroAlias("old")` | type, field | alias for evolution, stackable | `@AvroAlias` |
| `@avroDefault("json")` | field | schema default as a JSON literal (`"8080"`, `"\"info\""`) | none (avro4s uses constructor defaults only) |
| `@avroNoDefault` | field | no schema default even with a Scala default | `@AvroNoDefault` |
| `@transientField` | field | not in the schema; decoded as its (required) default | `@AvroTransient` |
| `@avroFixed(size)` | `Array[Byte]` field; after 0.4.0 also `String` fields and value classes | FIXED instead of BYTES; shorter values padded with zeros (after 0.4.0) | `@AvroFixed` |
| `@avroScalePrecision(precision, scale[, roundingMode])` | `BigDecimal` field | per-field decimal; note the order; the rounding mode (after 0.4.0) wins over the config | `@AvroScalePrecision(scale, precision)` (ignored by avro4s 5) / implicit `ScalePrecision` |
| `@avroSortPriority(n: Int)` | subtype | UNION/ENUM order, higher first | `@AvroSortPriority(Float)` |
| `@avroUnionPosition(n)` (after 0.4.0) | subtype | UNION/ENUM position, lower first; `@avroSortPriority` wins | `@AvroUnionPosition` |
| `@AvroJavaName`, `@AvroJavaNamespace`, `@AvroJavaProp`, `@AvroJavaEnumDefault` (after 0.4.0) | Java enum / constant | ENUM name, namespace, property, default symbol | avro4s' Java annotations |
| `@avroEnumDefault("X")` | sealed trait of case objects | ENUM default | `@AvroEnumDefault` (avro4s 4 only) |
| `@avroError` | type, field (after 0.4.0: the field's record) | record marked as Avro error | `@AvroError` (avro4s 5 only) |
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
| implicit `RoundingMode` (avro4s 4) | `AvroConfig.default.withRoundingMode(mode)` (after 0.4.0) |
| `AvroOutputStream.data` / `AvroInputStream.data` | `AvroIO.toDataFile` / `AvroIO.fromDataFile` (after 0.4.0) |
| custom `SchemaFor` for `timestamp-micros` / `-nanos` | `withInstantPrecision` / `withLocalDateTimePrecision` |
| default `BigDecimal` / `OffsetDateTime` encodings | `AvroConfig.avro4sDefaults` |

Avro container files: `AvroIO.toDataFile` / `fromDataFile` after 0.4.0; on 0.4.0 use Avro's `DataFileWriter` with
`encoder.schema` and `encoder.encode(a)`.

## Type support (parity with avro4s 4.x unless noted)

UUID, `java.time` logical types, `java.sql.Date`/`Timestamp`, value classes (unwrapped), case classes -> RECORD,
sealed traits -> UNION, case-object families and Java enums -> ENUM, `scala.Enumeration` -> ENUM (named after the
enumeration object), `Either` -> UNION, `Option` -> UNION(null, T), `Array[Byte]`/`Seq[Byte]`/`ByteBuffer` -> BYTES,
recursive types, generic record names `Name__A_B`. Extra: Scala 3 named tuples, union types, literal types, opaque
types; refined/iron/neotype/newtype via Kindlings integration modules.

Source of truth: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#avro-derivation
