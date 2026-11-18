# `UBJsonConfig` reference (Kindlings 0.4.0)

`final case class UBJsonConfig(...)`, `implicit val default: UBJsonConfig = UBJsonConfig()` in the companion. Every
builder returns a copy. Semantics follow jsoniter-scala's `CodecMakerConfig` unless marked "Kindlings-only".

| Field | Default | Builder(s) | Effect |
|---|---|---|---|
| `fieldNameMapper` | `identity` | `withFieldNameMapper(f)` (`String => String` or `PartialFunction`), `withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`, `withScreamingSnakeCaseFieldNames` | field names |
| `adtLeafClassNameMapper` | `UBJsonConfig.simpleClassName` | `withAdtLeafClassNameMapper(f)`, `withSnakeCaseAdtLeafClassNames`, `withKebabCaseAdtLeafClassNames` | subtype names; `f` receives the fully qualified name (`pkg.Outer.Leaf`, Scala 3 enum cases `pkg.Enum.Case`) |
| `javaEnumValueNameMapper` | `identity` | `withJavaEnumValueNameMapper(f)` | Java enum constant names |
| `discriminatorFieldName` | `None` | `withDiscriminator(field)`, `withDiscriminatorFieldName(opt)` | `None` = wrapper object `{"Leaf":{...}}` |
| `requireDiscriminatorFirst` | `true` | `withRequireDiscriminatorFirst(b)` | `false`: discriminator may appear anywhere in the object |
| `circeLikeObjectEncoding` | `false` | `withCirceLikeObjectEncoding` | case objects as `{"Leaf":{}}` instead of `"Leaf"` (needs no discriminator) |
| `enumAsStrings` | `false` | `withEnumAsStrings` | all-case-object ADTs stay strings also with a discriminator |
| `useScalaEnumValueId` | `false` | `withUseScalaEnumValueId` | `scala.Enumeration` values as ids instead of names |
| `skipUnexpectedFields` | `true` | `withSkipUnexpectedFields(b)` | `false`: unknown fields fail decoding |
| `checkFieldDuplication` | `false` | `withCheckFieldDuplication` | duplicate keys fail decoding |
| `transientDefault` | `false` | `withTransientDefault` | do not write fields equal to their default |
| `transientEmpty` | `false` | `withTransientEmpty` | do not write empty collections |
| `transientNone` | `false` | `withTransientNone` | do not write `None` |
| `transientNull` | `false` | `withTransientNull` | do not write `null` of Scala 3 `T \| Null` fields |
| `scalaTransientSupport` | `false` | `withScalaTransientSupport` | `@scala.transient` fields behave like `@transientField` |
| `requireCollectionFields` | `false` | `withRequireCollectionFields` | missing collection/map field without default fails |
| `requireDefaultFields` | `false` | `withRequireDefaultFields` | missing field with a default fails; `null`/empty no longer replaced by the default |
| `emptyCollectionsAsDefault` | `true` | `withEmptyCollectionsAsDefault(b)`, `withEmptyCollectionsAsEmpty` (Kindlings-only) | empty array/object for a collection field with a default decodes as that default (`true`) or as empty (`false`) |
| `skipNestedOptionValues` | `false` | `withSkipNestedOptionValues` | `Option[Option[A]]` encoded as a plain `Option` (`Some(None)` becomes `null`) |
| `bigDecimalPrecision` | `34` | `withBigDecimalPrecision(n)` | DoS limit |
| `bigDecimalScaleLimit` | `6178` | `withBigDecimalScaleLimit(n)` | DoS limit |
| `bigDecimalDigitsLimit` | `308` | `withBigDecimalDigitsLimit(n)` | DoS limit |
| `bigIntDigitsLimit` | `308` | `withBigIntDigitsLimit(n)` | DoS limit |
| `mapMaxInsertNumber` | `Int.MaxValue` | `withMapMaxInsertNumber(n)` | DoS limit |
| `setMaxInsertNumber` | `Int.MaxValue` | `withSetMaxInsertNumber(n)` | DoS limit |

Name-mapper helpers on the companion (as in jsoniter-scala): `UBJsonConfig.simpleClassName`, `enforceCamelCase`,
`EnforcePascalCase`, `enforce_snake_case`, `enforce_snake_case2`, `` `enforce-kebab-case` ``, `` `enforce-kebab-case2` ``,
`screamingSnakeCase`. `UBJsonConfig.configError(config): Option[String]` / `UBJsonConfig.validate(config)` expose the
contradictory-settings check.

Contradictions (compile error when the config is known at compile time, else `IllegalArgumentException` at codec
creation): `requireCollectionFields` + `transientEmpty`; `requireDefaultFields` + `transientDefault`;
`circeLikeObjectEncoding` + a discriminator.
