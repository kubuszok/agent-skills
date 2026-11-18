# kindlings-jsoniter-json and kindlings-tapir-openapi-jsoniter (Kindlings 0.4.0)

Two small companion artifacts for jsoniter-scala users who do not want circe/cats on the classpath. Neither one is a
derivation macro.

## kindlings-jsoniter-json: a JSON AST for jsoniter-scala

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-jsoniter-json" % "0.4.0" // JVM / JS / Native
```

Only dependency: `jsoniter-scala-core`. Replaces circe's `Json` + jsoniter-scala-circe when you only need a raw JSON
value (pass-through payloads, ad-hoc edits).

```scala
import hearth.kindlings.jsoniterjson._
import hearth.kindlings.jsoniterjson.codec.JsonCodec._ // implicit JsonValueCodec[Json]
import hearth.kindlings.jsoniterjson.optics._
import com.github.plokhotnyuk.jsoniter_scala.core._

val json: Json = readFromString[Json]("""{"name":"Alice","age":30}""")
val name: Option[String] = JsonPath.root.field("name").get(json).flatMap(_.asString)
val older: Json = JsonPath.root.field("age").modify {
  case Json.Num(n) => Json.fromInt(n.toInt.getOrElse(0) + 1)
  case other       => other
}(json)
writeToString(Json.obj("ok" -> Json.True, "xs" -> Json.arr(Json.fromInt(1))))
```

- `Json` cases: `Json.Null`, `Json.Bool`, `Json.Num` (a `JsonNumber`, kept as text), `Json.Str`, `Json.Arr`
  (`Vector[Json]`), `Json.Obj` (a `JsonObject`). Constructors `fromInt/fromLong/fromDouble/fromFloat/fromBigDecimal/
  fromBigInt/fromString/fromBoolean/fromValues/fromJsonObject`, `Json.obj(...)`, `Json.arr(...)`, `Json.True/False`;
  `isX` / `asX` (returning `Option`) and `fold(onNull, onBoolean, onNumber, onString, onArray, onObject)`.
- `JsonNumber`: `toInt`, `toLong`, `toBigInt`, `toBigDecimal`, `toDouble`, `toFloat` all return `Option`;
  `JsonNumber.fromString` accepts only valid JSON numbers.
- `JsonObject`: ordered fields; `apply(key)`, `add`, `remove`, `mapValues`, `keys`, `values`, `toMap`,
  `JsonObject.empty`, `JsonObject.fromIterable`.
- Optics: `JsonPath.root.field(..).index(..)` with `get`/`set`/`modify`; `JsonOptic.field/index/each` composed with
  `andThen`; `JsonTraversal.getAll/modify/set`.
- Codec: `hearth.kindlings.jsoniterjson.codec.JsonCodec.jsonValueCodec` (max nesting depth 128, as
  jsoniter-scala-circe; `JsonCodec.withMaxDepth(n)` for another limit). To use `Json` as a field of a derived case
  class, import `hearth.kindlings.jsoniterjson.codec.JsonCodec._` where the Kindlings codec is derived (it is not in
  `Json`'s companion). Note the object name clashes with jsoniter-scala's `JsonCodec` trait; import it qualified.

Differences from circe's `Json` (by design): duplicate keys are kept (`apply` returns the last value, `add` appends);
equality is structural (numbers by text, objects by ordered fields); `toDouble`/`toFloat` return `Option`;
`JsonNumber.fromString` rejects `01` and `.5`.

## kindlings-tapir-openapi-jsoniter: OpenAPI docs to JSON without circe

```scala
libraryDependencies += "com.kubuszok" %% "kindlings-tapir-openapi-jsoniter" % "0.4.0"
```

Hand-written jsoniter codecs for the whole sttp-apispec OpenAPI / JSON Schema model, byte-for-byte compatible with
sttp-apispec's `openapi-circe`. Replaces `tapir-openapi-circe` / `openapi-circe` for rendering docs.

```scala
import hearth.kindlings.tapiropenapijsoniter._
import sttp.apispec.openapi.Info
import sttp.tapir._

val health = endpoint.get.in("health").out(stringBody)
val json: String = TapirOpenApi.endpointToJson(health, Info("Health API", "1.0"))
```

`TapirOpenApi` (JVM and Scala.js; depends on `tapir-openapi-docs`): `toOpenAPI(endpoint(s), info)`,
`toOpenAPI(endpoint(s), title, version)`, `toJson(doc)` (OpenAPI 3.1), `toJson30(doc)` (OpenAPI 3.0.3),
`endpointToJson(endpoint, info)`, `endpointsToJson(endpoints, info)`, `withOptions(OpenAPIDocsOptions)`.

`OpenApiJsoniter` (JVM, JS and Native) - codecs for a model you already have:

```scala
import hearth.kindlings.tapiropenapijsoniter.OpenApiJsoniter
import OpenApiJsoniter.openapi_3_1._ // or openapi_3_0._, openapi_3_1_objectAny._
import com.github.plokhotnyuk.jsoniter_scala.core._

def render(doc: sttp.apispec.openapi.OpenAPI): String = writeToString(doc)
```

`OpenApiJsoniter.custom(openApi30Flag, anyEncoding)` builds other combinations. Schemas themselves come from tapir; to
derive them with Kindlings (matching a `JsoniterConfig`), see the `kindlings-tapir-schema` skill.

Docs: https://kindlings.readthedocs.io/en/0.4.0/jsoniter-json/ and
https://kindlings.readthedocs.io/en/0.4.0/tapir-openapi-jsoniter/
