# Golden files (Kindlings 0.4.0, munit)

Verified with munit 1.3.6 on Scala 3.8.3 and 2.13.18. Goldens live in `src/test/resources/golden/` (scala-cli:
`//> using test.resourceDir resources`) and are read from the classpath; they are rewritten only when the
`UPDATE_GOLDEN` environment variable points at the directory to write to.

```scala
trait GoldenFiles { self: munit.FunSuite =>

  def assertGolden(name: String, obtained: String)(implicit loc: munit.Location): Unit =
    sys.env.get("UPDATE_GOLDEN") match {
      case Some(dir) => // e.g. UPDATE_GOLDEN=$PWD/src/test/resources/golden
        val file = java.nio.file.Paths.get(dir, name)
        java.nio.file.Files.createDirectories(file.getParent)
        java.nio.file.Files.write(file, obtained.getBytes("UTF-8"))
      case None =>
        val stream = getClass.getResourceAsStream(s"/golden/$name")
        assert(stream != null, s"missing golden file golden/$name, run with UPDATE_GOLDEN=<resources>/golden")
        val expected = try new String(stream.readAllBytes(), "UTF-8") finally stream.close()
        assertNoDiff(obtained, expected) // munit's line-based String diff
    }
}

class OrderGoldenFileSuite extends munit.FunSuite with GoldenFiles {
  test("Order golden file") {
    assertGolden("order.json", Order(1L, Nil, Money(5), Some("gift"), Status.Active).asJson.spaces2)
  }
}
```

Notes:

- Pass an absolute directory in `UPDATE_GOLDEN` (`$PWD/<module>/src/test/resources/golden`): the working directory of
  the test JVM depends on the build tool and on forking.
- After regenerating, run the tests again without the variable (the classpath copy of the resources is refreshed on
  the next build) and review the changed files in the pull request diff: that diff is the format change.
- A missing file must fail; creating it on the fly makes CI pass goldens that nobody reviewed.
- Prefer a human-readable encoding of binary goldens: hex (`bytes.map("%02x".format(_)).mkString`) or Base64 for Avro /
  UBJSON, `spaces2` for JSON. `.spaces2` output of circe is identical on Scala 2.13 and 3, so one file serves both.
- Name files after the type and the scenario (`order-suspended.json`, `order-v1.json`) and keep payloads produced by
  older releases (`*-v1.json`) to test that they still decode.

## Avro: schema, bytes and compatibility

```scala
import hearth.kindlings.avroderivation._
import org.apache.avro.{Schema, SchemaCompatibility}

final case class ItemAdded(name: String, qty: Int, note: Option[String] = None) // in package shop.events

class AvroGoldenSuite extends munit.FunSuite {
  // the previous release's schema (checked in, or fetched from the schema registry)
  val v1 = new Schema.Parser().parse(
    """{"type":"record","name":"ItemAdded","namespace":"shop.events","fields":[{"name":"name","type":"string"},{"name":"qty","type":"int"}]}"""
  )

  test("the current schema can read data written with v1") {
    val result = SchemaCompatibility.checkReaderWriterCompatibility(AvroSchemaFor.schemaOf[ItemAdded], v1)
    assertEquals(result.getType, SchemaCompatibility.SchemaCompatibilityType.COMPATIBLE, result.getDescription)
  }

  test("binary encoding") {
    assertEquals(AvroIO.toBinary(ItemAdded("apple", 2)).map("%02x".format(_)).mkString, "0a6170706c650400")
  }
}
```

`AvroSchemaFor.schemaOf[ItemAdded].toString` gives
`{"type":"record","name":"ItemAdded","namespace":"shop.events","fields":[...,{"name":"note","type":["null","string"],"default":null}]}`
on both Scala versions. Use `toString` (the `toString(Boolean)` overload is deprecated in Avro 1.12). Types in the
empty package get `"namespace":"`<empty>`"` on Scala 2.13 and no namespace on Scala 3 (0.4.0) - one more reason to
keep models in packages and run goldens on every Scala version.
