# CodecMakerConfig -> JsoniterConfig (Kindlings 0.4.0)

jsoniter-scala's `JsonCodecMaker.make[A](CodecMakerConfig....)` becomes
`KindlingsJsonValueCodec.derived[A](JsoniterConfig....)` (Scala 3: `derived[A](using JsoniterConfig....)`), or an
implicit `JsoniterConfig` in scope.

**Builder style differs.** Upstream builders take a value (`withTransientDefault(false)`); most Kindlings builders take
no argument and switch a flag **on**. To switch one off (e.g. after a preset), use the case-class `copy`:
`JsoniterConfig.jsoniterScalaDefaults.copy(transientDefault = false)` or the constructor with named arguments.

**Defaults differ** in 7 fields (marked **bold** below). `JsoniterConfig.jsoniterScalaDefaults` restores all of them.

| `CodecMakerConfig` | Upstream default | `JsoniterConfig` field (Kindlings default) | Kindlings builder |
|---|---|---|---|
| `withFieldNameMapper(pf)` | `identity` | `fieldNameMapper` (`identity`) | `withFieldNameMapper(f or pf)`, `withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`, `withScreamingSnakeCaseFieldNames` |
| `withAdtLeafClassNameMapper(f)` | `simpleClassName` (receives the FQN) | `adtLeafClassNameMapper` (`JsoniterConfig.simpleClassName`, receives the FQN) | `withAdtLeafClassNameMapper(f or pf)`, `withSnakeCaseAdtLeafClassNames`, `withKebabCaseAdtLeafClassNames` |
| `withJavaEnumValueNameMapper(pf)` | `identity` | `javaEnumValueNameMapper` (`identity`) | `withJavaEnumValueNameMapper(f or pf)` |
| `withDiscriminatorFieldName(opt)` | **`Some("type")`** | `discriminatorFieldName` (**`None`**: wrapper objects, case objects as strings) | `withDiscriminator("type")`, `withDiscriminatorFieldName(opt)` |
| `withRequireDiscriminatorFirst(b)` | `true` | `requireDiscriminatorFirst` (`true`) | `withRequireDiscriminatorFirst(b)` |
| `withAlwaysEmitDiscriminator(b)` | `false` | `alwaysEmitDiscriminator` (`false`) | `withAlwaysEmitDiscriminator` |
| `withCirceLikeObjectEncoding(b)` | `false` | `circeLikeObjectEncoding` (`false`) | `withCirceLikeObjectEncoding` |
| `withSkipUnexpectedFields(b)` | `true` | `skipUnexpectedFields` (`true`) | `withSkipUnexpectedFields(b)` |
| `withIsStringified(b)` | `false` | `isStringified` (`false`) | `withStringified` |
| `withMapAsArray(b)` | `false` | `mapAsArray` (`false`) | `withMapAsArray` |
| `withTransientDefault(b)` | **`true`** | `transientDefault` (**`false`**) | `withTransientDefault` |
| `withTransientEmpty(b)` | **`true`** | `transientEmpty` (**`false`**) | `withTransientEmpty` |
| `withTransientNone(b)` | **`true`** | `transientNone` (**`false`**: `None` written as `null`) | `withTransientNone` |
| `withTransientNull(b)` (Scala 3 `T \| Null`) | `false` | `transientNull` (`false`, no-op on Scala 2) | `withTransientNull` |
| `withRequireCollectionFields(b)` | `false` | `requireCollectionFields` (`false`) | `withRequireCollectionFields` |
| `withRequireDefaultFields(b)` | `false` | `requireDefaultFields` (`false`) | `withRequireDefaultFields` |
| `withCheckFieldDuplication(b)` | **`true`** | `checkFieldDuplication` (**`false`**) | `withCheckFieldDuplication` |
| `withUseScalaEnumValueId(b)` | `false` | `useScalaEnumValueId` (`false`) | `withUseScalaEnumValueId` |
| `withScalaTransientSupport(b)` | `false` | `scalaTransientSupport` (`false`) | `withScalaTransientSupport` |
| `withSkipNestedOptionValues(b)` | `false` | `skipNestedOptionValues` (`false`) | `withSkipNestedOptionValues` |
| `withInlineOneValueClasses(b)` | `false` | `inlineOneValueClasses` (`false`) | `withInlineOneValueClasses` |
| `withDecodingOnly(b)` / `withEncodingOnly(b)` | `false` | `decodingOnly` / `encodingOnly` (`false`) | `withDecodingOnly` / `withEncodingOnly` |
| `withBigDecimalPrecision(n)` | `34` | `bigDecimalPrecision` (`34`) | `withBigDecimalPrecision(n)` |
| `withBigDecimalScaleLimit(n)` | `6178` | `bigDecimalScaleLimit` (`6178`) | `withBigDecimalScaleLimit(n)` |
| `withBigDecimalDigitsLimit(n)` | `308` | `bigDecimalDigitsLimit` (`308`) | `withBigDecimalDigitsLimit(n)` |
| `withBigIntDigitsLimit(n)` | `308` | `bigIntDigitsLimit` (`308`) | `withBigIntDigitsLimit(n)` |
| `withBitSetValueLimit(n)` | `1024` | `bitSetValueLimit` (`1024`) | `withBitSetValueLimit(n)` |
| `withMapMaxInsertNumber(n)` | **`1024`** | `mapMaxInsertNumber` (**`Int.MaxValue`**) | `withMapMaxInsertNumber(n)` |
| `withSetMaxInsertNumber(n)` | **`1024`** | `setMaxInsertNumber` (**`Int.MaxValue`**, limits only sets) | `withSetMaxInsertNumber(n)` |
| `withAllowRecursiveTypes(b)` | `false` | - (recursive types always allowed) | - |
| - | - | `enumAsStrings` (`false`): case-object-only ADTs as strings also **with** a discriminator | `withEnumAsStrings` |
| - | - | `emptyCollectionsAsDefault` (`true`, as upstream): `[]`/`{}` of a collection field with a default decodes as the default | `withEmptyCollectionsAsEmpty` / `withEmptyCollectionsAsDefault(b)` |

Upstream's DoS limits (`mapMaxInsertNumber`, `setMaxInsertNumber` = 1024) are **off** by default in Kindlings: set them
explicitly (or use `jsoniterScalaDefaults`) for codecs that read untrusted input.

## Entry points

| jsoniter-scala | Kindlings |
|---|---|
| `JsonCodecMaker.make[A]` | `KindlingsJsonValueCodec.derived[A](JsoniterConfig.jsoniterScalaDefaults)` for identical output; plain `derived[A]` uses Kindlings' defaults |
| `JsonCodecMaker.make[A](cfg)` | `KindlingsJsonValueCodec.derived[A](JsoniterConfig.jsoniterScalaDefaults.with...)` |
| `makeWithoutDiscriminator` | `JsoniterConfig.makeWithoutDiscriminator` |
| `makeWithRequiredCollectionFields` | `JsoniterConfig.makeWithRequiredCollectionFields` |
| `makeWithRequiredCollectionFieldsAndNameAsDiscriminatorFieldName` | `JsoniterConfig.makeWithRequiredCollectionFieldsAndNameAsDiscriminatorFieldName` |
| `makeWithRequiredDefaultFields` | `JsoniterConfig.makeWithRequiredDefaultFields` |
| `makeWithSkipNestedOptionValues` | `JsoniterConfig.makeWithSkipNestedOptionValues` |
| `makeCirceLike` / `makeCirceLikeSnakeCased` | `JsoniterConfig.makeCirceLike` / `JsoniterConfig.makeCirceLikeSnakeCased` |
| `makeOpenapiLike`, `makeOpenapiLike(discr)`, `makeOpenapiLike(discr, mapper)`, `makeOpenapiLikeWithoutDiscriminator` | `JsoniterConfig.makeOpenapiLike`, `makeOpenapiLike(discr)`, `makeOpenapiLike(discr, mapper)` (mapper gets simple names), `makeOpenapiLikeWithoutDiscriminator` |
| `JsonCodecMaker.enforce_snake_case`, `enforce_snake_case2`, `` `enforce-kebab-case` ``, `` `enforce-kebab-case2` ``, `EnforcePascalCase`, `enforceCamelCase`, `simpleClassName` | same names on `JsoniterConfig` (plus `JsoniterConfig.screamingSnakeCase`) |

## Annotations

| jsoniter-scala (`com.github.plokhotnyuk.jsoniter_scala.macros`) | Kindlings (`hearth.kindlings.jsoniterderivation.annotations`) |
|---|---|
| `@named("x")` on a field or ADT leaf | `@named("x")` (or `@fieldName("x")` on a field) |
| `@transient` | `@transientField` (needs a default value); `scala.transient` only with `withScalaTransientSupport` |
| `@stringified` | `@stringified` |

Upstream annotations are **not** read by Kindlings: change the imports.

## Remaining behavioural differences (design decisions)

- Recursive types need no flag.
- Without a discriminator a case object is also read from `{"Leaf":{}}` (superset).
- A Scala 3 `T | Null` field holding `null` is written as `null` without `transientNull` (upstream throws an NPE).
- With `checkFieldDuplication = false`, a repeated key's decoder gets the field default (upstream: the earlier value).
- Error for another JSON type in a field with a default says `expected '{'` (upstream `expected '{' or null`).
- Where upstream's Scala 2 and Scala 3 macros report different errors, Kindlings reports what upstream reports on the
  same Scala version.

Source of truth: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#jsoniter-derivation
