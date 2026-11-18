# Testing that JSON, Schema and OpenAPI agree (Kindlings 0.4.0)

Two complementary tests for a tapir API whose codecs and schemas come from Kindlings (see `SKILL.md`). Both were
verified with scala-cli on Scala 2.13.18 and 3.8.3.

## 1. Encode samples, compare with the published component schemas

Uses only what the jsoniter recipe already has on the classpath: `kindlings-tapir-openapi-jsoniter` (which brings the
`kindlings-jsoniter-json` AST) and the API's own codecs. It checks the leaf schema selected by the discriminator:
no undocumented keys, no missing required keys, no `null` where the schema does not allow it.

```scala
import hearth.kindlings.tapiropenapijsoniter.TapirOpenApi
import hearth.kindlings.jsoniterjson.Json
import hearth.kindlings.jsoniterjson.codec.JsonCodec.jsonValueCodec // JsonValueCodec[Json]
import com.github.plokhotnyuk.jsoniter_scala.core._
import sttp.apispec.{Schema => JsonSchema, SchemaType} // explicit import beats sttp.tapir._'s SchemaType

val components = TapirOpenApi.toOpenAPI(createPayment, "Payments", "1.0").components.get.schemas
def component(name: String): JsonSchema = components(name).asInstanceOf[JsonSchema]

def problems(value: Payment, schemaName: String): List[String] = {
  val obj = readFromString[Json](writeToString(value)).asObject.get // writeToString with the API's codec
  val root = component(schemaName)
  val leaf = root.discriminator.fold(root) { d =>
    val tag = obj(d.propertyName).flatMap(_.asString).get
    component(d.mapping.get(tag).stripPrefix("#/components/schemas/"))
  }
  def allowsNull(k: String) = leaf.properties.get(k).exists {
    case s: JsonSchema => s.`type`.exists(_.contains(SchemaType.Null))
    case _             => false
  }
  val keys = obj.keys.toSet
  (keys -- leaf.properties.keySet).toList.map(k => s"field '$k' is not in the schema") ++
    leaf.required.filterNot(keys).map(k => s"required field '$k' is missing") ++
    obj.toMap.collect { case (k, Json.Null) if !allowsNull(k) => s"field '$k' is null, the schema does not allow it" }
}

problems(BankTransfer("DE89370400440532013000", Some("invoice 7")), "Payment") // List()
// with a JsoniterConfig lacking withTransientNone:
problems(BankTransfer("DE89370400440532013000", None), "Payment")
// List(field 'reference' is null, the schema does not allow it)
```

Assert `problems(sample, "<BodyType>")` is empty for a sample of every subtype of every body type (samples can come
from `kindlings-scalacheck` derived `Arbitrary`). For a circe API, encode with the endpoint's body codec
(`jsonBody[A].codec.encode(a)`, which applies tapir's `jsonPrinter`) and parse with circe or the same `Json` AST.
For nested values and formats, a full JSON Schema validator can replace this shallow comparison.

## 2. Golden OpenAPI document

Commit the rendered document; any change in configuration, field names or optionality shows up as a diff in review.

```scala
import hearth.kindlings.tapiropenapijsoniter.TapirOpenApi
import sttp.apispec.openapi.Info
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8

class OpenApiGoldenSpec extends munit.FunSuite {
  test("OpenAPI document matches the committed golden file") {
    val actual = TapirOpenApi.endpointsToJson(Api.endpoints, Info("Payments", "1.0"))
    val golden = Paths.get("src/test/resources/openapi.golden.json")
    if (!Files.exists(golden)) Files.write(golden, actual.getBytes(UTF_8)) // first run records it
    assertEquals(actual, new String(Files.readAllBytes(golden), UTF_8))
  }
}
```

With circe-rendered docs use `OpenAPIDocsInterpreter().toOpenAPI(endpoints, info).asJson.deepDropNullValues.noSpaces`
(`import sttp.apispec.openapi.circe._`), which produces the same string as `TapirOpenApi.toJson`.
