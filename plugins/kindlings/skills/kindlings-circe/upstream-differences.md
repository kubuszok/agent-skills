# kindlings-circe: differences from upstream circe (Kindlings 0.4.0)

Kindlings is checked against circe-generic (`deriveCodec`), circe-generic-extras (`deriveConfiguredCodec`,
`deriveEnumerationCodec`, `deriveUnwrappedCodec`, `deriveExtrasCodec`, `.patch`/`.incomplete`, `@JsonKey`) and, on
Scala 3, circe-core's `ConfiguredCodec`/`ConfiguredEnumCodec`: encoded JSON (key order included), `decodeJson` and
`decodeAccumulating` results on valid and broken inputs. Everything not listed here behaves like upstream.
Source of truth: https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#circe-derivation

## Differences (wire format or behaviour)

| Topic | Upstream | Kindlings |
|---|---|---|
| `AnyVal` case classes | circe-generic / generic-extras (Scala 2): products `{"value":5}`; Scala 3: not derivable (no `Mirror`) | Unwrapped by default (`5`); `withoutValueClassUnwrapping` (`unwrapValueClasses = false`) gives `{"value":5}`, also for value-class sum children (`{"IntId":{"v":5}}`) |
| Value class over `Option` as an absent field | product: missing-field failure | default: wrapped `None` (derived decoder; the field default with `useDefaults`), missing-field failure with a user decoder; `withoutValueClassUnwrapping`: missing field |
| Hand-written instance of an intermediate sealed trait | Scala 3 core: used under the intermediate's name; generic-extras: ignored (shapeless flattens to leaves) | Used under the intermediate's name on Scala 2 and 3 |
| Wrapper object with superfluous keys (non-strict) | Scala 3 core: first key in JSON order naming a constructor; Scala 2: first constructor in alphabetical order found among keys | Scala 3 core behaviour on both versions |
| Wrapper object with several keys + strict decoding | Scala 3 core: rejected; generic-extras: accepted (strict only inside case classes) | Rejected on both versions |
| Discriminator + child that is not a JSON object | generic-extras: written wrapped `{"Name":..}`, not read back; Scala 3 core: value dropped (`{"type":"Name"}`) | Written wrapped and read back |
| Error messages / cursor history | Scala 2 shapeless wording differs (`JSON decoding to CNil should never happen`, ...) | Scala 3 core wording on both versions (`type Shape has no class/object/case named 'X'.`, `Strict decoding Person - unexpected fields: a, b; valid fields: name, age.`, ...) |
| `enumAsStrings` on non-singleton cases | compile-time error | compile-time error when the config is known at compile time; otherwise `DecodingFailure` / `IllegalArgumentException` at runtime |
| Patch decoder with `useDefaults` | generic-extras throws `ClassCastException` | defaults ignored, absent key keeps the value |

## Improvements (opt-in or additive)

| Topic | Upstream | Kindlings |
|---|---|---|
| One API on Scala 2.13 and 3 | different modules and APIs | same API |
| Per-field rename | `@JsonKey`, Scala 2 only | `@fieldName`, both |
| Transient field | none | `@transientField` (needs a default) |
| `enumAsStrings` | Scala 2 `deriveEnumeration*`, Scala 3 `ConfiguredEnum*` | one flag, both versions, also Java enums / `Enumeration`s |
| Recursive types | Scala 2 needs `Lazy`; Scala 3 `generic.auto` broken (circe #1980) | work |
| Map keys | manual `KeyEncoder`/`KeyDecoder` for value classes and enums | automatic (enum keys = constructor name with `transformConstructorNames`); user/circe key codecs still win |
| Named tuples, opaque types, Java enums, literal types, union types | no | yes |
| Compile-time configuration | n/a | evaluated at compile time when possible (compile-time checks, no runtime config checks) |

## Parity worth knowing

- `useDefaults`: absent field, or a `null` the field decoder rejects, uses the default; a `Decoder[Option[X]]` that
  decodes an absent key to a value keeps that value.
- Absent `Option[A]` field (no `useDefaults`): `None`, whatever `A` is.
- Discriminator appended after the fields; nested hierarchies flattened; diamonds written once.
- Strict decoding: discriminator is an expected key; case objects reject extra keys; `decodeAccumulating` reports the
  strict failure first, then field errors.
- Tuples are JSON arrays of exact arity; `Decoder[Unit]` accepts `null`, `{}`, `[]`.
- Case classes with several parameter lists are rejected at compile time.
- Cross-platform: JVM, Scala.js, Scala Native.

## Wire-format changes vs earlier Kindlings versions (data written by older releases)

- Leaves of nested sealed hierarchies used to be written under the intermediate's name (`{"Parent":{"Child":{..}}}`);
  now under their own name and the old form is no longer read.
- A user `KeyEncoder` for `Int`/`Long`/`Double`/`Short`/`Byte` keys is now used also when values are derived.
- `useDefaults` + a `Decoder[Option[X]]` decoding an absent key to a value now wins over the default.
- Case objects outside a sum reject extra keys under strict decoding.
- More configurations are evaluated at compile time, so some runtime failures became compile errors.
