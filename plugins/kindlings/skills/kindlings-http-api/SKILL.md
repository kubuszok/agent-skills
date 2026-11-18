---
name: kindlings-http-api
description: >-
  Recipe for tapir HTTP APIs built with Kindlings so the JSON wire format, the tapir Schema and the generated OpenAPI
  document agree - jsonBody with tapir-json-circe (sttp.tapir.json.circe) or tapir-jsoniter-scala
  (sttp.tapir.json.jsoniter), codecs from kindlings-circe-derivation / kindlings-jsoniter-derivation, schemas from
  kindlings-tapir-schema-derivation (KindlingsSchema.derived[A].schema) following the same Configuration /
  JsoniterConfig (snake_case fields, discriminator, wrapped ADTs, optional fields, enums as strings), one config per
  API in companions, PreferSchemaConfig, rendering OpenAPI with kindlings-tapir-openapi-jsoniter (TapirOpenApi) vs
  openapi-circe, refined/Iron validators, consistency and golden tests. Use when OpenAPI/Swagger docs do not match
  the JSON, when mixing Schema.derived or sttp.tapir.generic.auto._ with Kindlings, on "Multiple JSON library
  configurations found: circe, jsoniter-scala", or "field":null for an Option the schema calls optional.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# HTTP APIs with tapir and Kindlings

How to wire Kindlings JSON codecs, Kindlings tapir schemas and OpenAPI rendering together in a tapir API so that what
the server reads/writes and what the documentation says come from **one configuration**. Module details live in the
sibling skills: `kindlings-jsoniter` (codecs, `JsoniterConfig`, and `json-ast-and-openapi.md` for
`kindlings-tapir-openapi-jsoniter`), `kindlings-circe` (codecs, `Configuration`), `kindlings-tapir-schema`
(schema rules: required/optional table, wrapped ADTs, annotations, differences from tapir), `kindlings-integrations`
(refined/Iron/neotype/cats types and their tapir validators).

**Version:** written for Kindlings 0.4.0 (built against tapir 1.13.33, sttp-apispec 0.11.10, jsoniter-scala 2.42.3,
circe 0.14.17). Check the version in the user's build (`build.sbt` / `build.mill` / `project.scala` `//> using dep`);
if it differs, prefer the docs for that version: https://kindlings.readthedocs.io/en/latest/http-api/ (use the
versioned docs `en/<version>/` when they exist for the version used).

## Choosing the JSON library

`jsonBody[A]` needs a codec **and** a tapir `Schema[A]` for the body type.

| | jsoniter-scala | circe |
|---|---|---|
| Codecs | `kindlings-jsoniter-derivation` | `kindlings-circe-derivation` |
| tapir module / import | `tapir-jsoniter-scala` / `sttp.tapir.json.jsoniter._` | `tapir-json-circe` / `sttp.tapir.json.circe._` |
| Config type | `hearth.kindlings.jsoniterderivation.JsoniterConfig` | `hearth.kindlings.circederivation.Configuration` |
| `None` field | `null` unless `withTransientNone` | `null` unless the printer drops nulls |
| With `kindlings-tapir-openapi-jsoniter` | just works, no circe/cats at all | needs `PreferSchemaConfig` (see Gotchas) |

One JSON library per API. Prefer jsoniter when the user wants a circe-free stack.

```scala
// jsoniter flavour (use %%% for Scala.js / Native where available)
libraryDependencies ++= Seq(
  "com.kubuszok"                %% "kindlings-jsoniter-derivation"     % "0.4.0",
  "com.kubuszok"                %% "kindlings-tapir-schema-derivation" % "0.4.0",
  "com.kubuszok"                %% "kindlings-tapir-openapi-jsoniter"  % "0.4.0", // JVM + JS (TapirOpenApi)
  "com.softwaremill.sttp.tapir" %% "tapir-jsoniter-scala"              % "1.13.33"
)
// circe flavour: kindlings-circe-derivation + tapir-json-circe instead of the jsoniter pair
```

## The recipe

1. **One configuration per API**, in an `object` imported where instances are derived (Scala 2 and 3), or a top-level
   `given` in the package (Scala 3).
2. **Codec and schema side by side in the companion** of every type used directly as a request/response body. Nested
   field and subtype types are derived recursively with the same config - no instances needed for them.
3. **Schema = `KindlingsSchema.derived[A].schema`**. Never `Schema.derived`, `sttp.tapir.generic.auto._` or
   `sttp.tapir.generic.Configuration`.
4. **Render docs** with `TapirOpenApi` (jsoniter) or tapir's `OpenAPIDocsInterpreter` + `openapi-circe`.
5. **Test the agreement**: encode samples and compare them with the published component schemas, and/or golden-test
   the OpenAPI JSON - see [consistency-tests.md](consistency-tests.md).

## Complete example (jsoniter, Scala 2.13 and 3)

Verified with scala-cli on Scala 2.13.18 and 3.8.3 (identical output).

```scala
import hearth.kindlings.jsoniterderivation._
import hearth.kindlings.tapirschemaderivation._
import com.github.plokhotnyuk.jsoniter_scala.core._
import sttp.tapir._
import sttp.tapir.json.jsoniter._

object ApiConfig {
  implicit val config: JsoniterConfig = JsoniterConfig.default
    .withSnakeCaseFieldNames         // accountIban -> account_iban
    .withSnakeCaseAdtLeafClassNames  // BankTransfer -> bank_transfer
    .withDiscriminator("type")
    .withTransientNone               // omit None (schema: optional, not nullable)
}
import ApiConfig._

sealed trait Payment
object Payment {
  implicit val codec: JsonValueCodec[Payment] = KindlingsJsonValueCodec.derived[Payment]
  implicit val schema: Schema[Payment] = KindlingsSchema.derived[Payment].schema
}
case class CardPayment(cardNumber: String, expiryMonth: Int) extends Payment
case class BankTransfer(accountIban: String, reference: Option[String]) extends Payment

case class PaymentId(paymentId: String)
object PaymentId {
  implicit val codec: JsonValueCodec[PaymentId] = KindlingsJsonValueCodec.derived[PaymentId]
  implicit val schema: Schema[PaymentId] = KindlingsSchema.derived[PaymentId].schema
}

val createPayment = endpoint.post.in("payments").in(jsonBody[Payment]).out(jsonBody[PaymentId])

writeToString[Payment](BankTransfer("DE89370400440532013000", None))
// {"type":"bank_transfer","account_iban":"DE89370400440532013000"}

import hearth.kindlings.tapiropenapijsoniter._
import hearth.kindlings.tapiropenapijsoniter.OpenApiJsoniter.openapi_3_1._ // JsonValueCodec[SchemaLike], [OpenAPI]
import sttp.apispec.openapi.Info

val components = TapirOpenApi.toOpenAPI(createPayment, Info("Payments", "1.0")).components.get.schemas
writeToString(components("BankTransfer"))
// {"title":"BankTransfer","type":"object","required":["account_iban","type"],"properties":{"account_iban":
//  {"type":"string"},"reference":{"type":"string"},"type":{"type":"string","const":"bank_transfer"}}}
writeToString(components("Payment"))
// {"title":"Payment","oneOf":[{"$ref":"#/components/schemas/BankTransfer"},{"$ref":"#/components/schemas/CardPayment"}],
//  "discriminator":{"propertyName":"type","mapping":{"bank_transfer":"#/components/schemas/BankTransfer",
//  "card_payment":"#/components/schemas/CardPayment"}}}
TapirOpenApi.endpointsToJson(List(createPayment), Info("Payments", "1.0")) // the whole document
```

Scala 3 with `derives` (verified): `derives KindlingsSchema` gives a `KindlingsSchema[A]`, but `jsonBody` needs a
`Schema[A]`, so unwrap it in the companion; the config must be visible at the type's definition site.

```scala
given JsoniterConfig = JsoniterConfig.default.withSnakeCaseFieldNames.withDiscriminator("type")

sealed trait Payment derives KindlingsJsonValueCodec, KindlingsSchema
object Payment:
  given Schema[Payment] = summon[KindlingsSchema[Payment]].schema
```

## circe flavour (verified on 2.13 and 3)

```scala
import hearth.kindlings.circederivation._
import hearth.kindlings.tapirschemaderivation._
import io.circe.{Codec, Printer}
import sttp.tapir._
import sttp.tapir.json.circe.TapirJsonCirce

object ApiConfig {
  implicit val config: Configuration = Configuration.default
    .withSnakeCaseMemberNames.withSnakeCaseConstructorNames.withDiscriminator("type")
  // only needed when kindlings-jsoniter-derivation is also on the classpath
  // (kindlings-tapir-openapi-jsoniter depends on it):
  implicit val preferCirce: PreferSchemaConfig[Configuration] = PreferSchemaConfig[Configuration]
}
import ApiConfig._

object ApiJson extends TapirJsonCirce { // use instead of sttp.tapir.json.circe._
  override def jsonPrinter: Printer = Printer.noSpaces.copy(dropNullValues = true)
}
import ApiJson._

sealed trait Payment
object Payment {
  implicit val codec: Codec.AsObject[Payment] = KindlingsCodecAsObject.derived[Payment]
  implicit val schema: Schema[Payment] = KindlingsSchema.derived[Payment].schema
}
// jsonBody[Payment].codec.encode(BankTransfer("DE89...", None)) == {"account_iban":"DE89...","type":"bank_transfer"}
```

`PreferSchemaConfig` may also be replaced by `scalacOptions += "-Xmacro-settings:tapirSchemaDerivation.preferConfig=circe"`.
It is read where the schema is derived; an imported implicit (as above) works.

## Where configuration and instances go

- The config is resolved **where each instance is derived**. A schema derived where the API config is not visible
  falls back to the companion default (`JsoniterConfig.default` / `Configuration.default`) - no error, just camelCase
  docs for snake_case JSON (verified). Deriving codec and schema in the same companion under the same import avoids it.
- A companion instance exists once. If another API needs a different wire format for the same type, derive that API's
  codec *and* schema together in that API's object with its own config, not in the companion.
- Scala 2: a config in an `object` member is a runtime config - works the same, only compile-time config validation
  is skipped. Always give `implicit val`s an explicit type (un-annotated vals can trigger
  `HearthAssertionError: ... MIO timeout is already set`, see `kindlings-tapir-schema`).
- Scala 3: a top-level `given` or a `given` in an imported object works for `derives` and `derived`.

## Rendering the OpenAPI document

| | `kindlings-tapir-openapi-jsoniter` | tapir + sttp-apispec circe |
|---|---|---|
| Deps | `"com.kubuszok" %% "kindlings-tapir-openapi-jsoniter" % "0.4.0"` | `tapir-openapi-docs` + `"com.softwaremill.sttp.apispec" %% "openapi-circe"` (or `openapi-circe-yaml`) |
| JSON | `TapirOpenApi.endpointsToJson(endpoints, info)`, `toJson(doc)`, `toJson30(doc)` | `OpenAPIDocsInterpreter().toOpenAPI(es, info).asJson` with `import sttp.apispec.openapi.circe._` |
| YAML | none | `doc.toYaml` with `import sttp.apispec.openapi.circe.yaml._` |
| Platforms | `TapirOpenApi`: JVM + Scala.js; `OpenApiJsoniter` codecs: also Native | JVM + Scala.js |

Output is identical (verified: `TapirOpenApi.toJson(doc) == doc.asJson.deepDropNullValues.noSpaces`). Note:
`tapir-swagger-ui-bundle` pulls `openapi-circe-yaml` and circe; `tapir-swagger-ui` (`SwaggerUI[F](yaml: String)`)
does not. API details: `kindlings-jsoniter` skill, file `json-ast-and-openapi.md`.

## Validators from refined / Iron

The integration jars make codecs validate on decode, but `KindlingsSchema` shows the underlying type's schema. Add
tapir's integration and import it **where the schema is derived** (verified on 2.13 and 3 with refined):

```scala
case class OrderLine(sku: String, quantity: Int Refined Positive)
object OrderLine {
  import sttp.tapir.codec.refined._ // tapir-refined; Iron (Scala 3): tapir-iron + import sttp.tapir.codec.iron.given
  implicit val codec: JsonValueCodec[OrderLine] = KindlingsJsonValueCodec.derived[OrderLine] // + kindlings-refined-integration
  implicit val schema: Schema[OrderLine] = KindlingsSchema.derived[OrderLine].schema
}
// component: "quantity":{"type":"integer","format":"int32","exclusiveMinimum":0}
```

Full table (neotype, newtype, cats non-empty collections): `kindlings-integrations` skill.

## Gotchas

- **Docs use camelCase / wrong discriminator while the JSON is snake_case** - (a) tapir's `Schema.derived`,
  `sttp.tapir.generic.auto._` or a hand-written schema for some type: user instances always win, including a nested
  type's `Schema.derived`; (b) the schema was derived where the API config is not visible (companion default used).
  Fix: `KindlingsSchema.derived` under the same config import as the codec. Remove `generic.auto._`: Kindlings still
  derives nested types itself, but a body type without its own Kindlings schema silently gets tapir's schema instead
  of a compile error.
- **`Multiple JSON library configurations found: circe, jsoniter-scala.`** - both Kindlings JSON modules are on the
  classpath; usually circe codecs + `kindlings-tapir-openapi-jsoniter` (which depends on
  `kindlings-jsoniter-derivation`). Add `PreferSchemaConfig[hearth.kindlings.circederivation.Configuration]` (or
  `...jsoniterderivation.JsoniterConfig`). The error's own hint prints `PreferSchemaConfig[circeConfig]` /
  `PreferSchemaConfig()`, which does not compile - write the real type and `PreferSchemaConfig[T]`.
- **`"field":null` for `None` while the schema has the field optional but not nullable** (strict validators and
  generated clients reject it) - jsoniter: `withTransientNone`; circe: `TapirJsonCirce` with `jsonPrinter` using
  `dropNullValues = true` (plain `asJson.noSpaces` elsewhere still prints nulls).
- **Enum values differ between docs and JSON** - use `KindlingsSchema.derived` for sealed traits of case objects; it
  follows `withEnumAsStrings` + `withSnakeCaseConstructorNames` (circe) and jsoniter's leaf name mappers.
  `KindlingsSchema.derivedEnumeration` always uses the plain case names (`InProgress` vs wire `in_progress`, verified).
- **`type mismatch: KindlingsSchema[A]` where `Schema[A]` required** - add `.schema` / a `given Schema[A]`.
- **Collections required with circe** - correct: circe decoders reject missing collections (jsoniter does not). See
  the required/optional table in `kindlings-tapir-schema`.
- **Platforms** - schema and codec modules: JVM, Scala.js, Native. `TapirOpenApi` (and tapir's docs interpreter): JVM
  and Scala.js only; on Native only `OpenApiJsoniter` codecs for a model built elsewhere.
- **Version skew** - Kindlings 0.4.0 depends on `tapir-core` 1.13.33, so an older `tapir-json-*` gets a newer
  `tapir-core` through eviction (1.13.21 worked in testing). Keep all tapir modules on one version, at least 1.13.33.

## Links

- Guide: https://kindlings.readthedocs.io/en/latest/http-api/
- Schemas: https://kindlings.readthedocs.io/en/0.4.0/tapir-schema-derivation/
- OpenAPI rendering: https://kindlings.readthedocs.io/en/0.4.0/tapir-openapi-jsoniter/
- tapir JSON support: https://tapir.softwaremill.com/en/latest/endpoint/json.html
