---
name: kindlings-xml
description: >-
  Deriving XML encoders/decoders over scala-xml with kindlings-xml-derivation (Scala 2.13 and 3, JVM/JS/Native).
  Covers XmlEncoder, XmlDecoder, KindlingsXmlEncoder, KindlingsXmlDecoder, KindlingsXmlCodec (.derived, derives,
  encode/toXmlString, decode/fromXmlString), the syntax import, XmlConfig (withAttributesByDefault,
  withDiscriminator, withNoDiscriminator, withSnakeCaseFieldNames, withUseDefaults, withTransientNone,
  withTransientEmpty, withEnumAsStrings), annotations @xmlAttribute, @xmlElement, @xmlContent, @xmlName,
  @xmlWrapper, @xmlUnwrapped, @transientField, and XmlDecodingError (MissingElement, MissingAttribute, InvalidValue,
  UnknownDiscriminator, ...). Use when code imports hearth.kindlings.xmlderivation, when mapping case classes or
  sealed traits to scala.xml.Elem, choosing attributes vs child elements vs text content, or debugging XML decoding
  errors.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings XML derivation (`kindlings-xml-derivation`)

Kindlings' own XML type classes (no upstream library to replace): `XmlEncoder[A]` produces a `scala.xml.Elem`,
`XmlDecoder[A]` reads one into `Either[XmlDecodingError, A]`. Fields map to child elements, attributes or text content.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/xml-derivation/>.

## Dependencies

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-xml-derivation" % "0.4.0" // %% on JVM-only builds
```

```scala
//> using dep com.kubuszok::kindlings-xml-derivation:0.4.0
```

`org.scala-lang.modules::scala-xml` (2.5.0) and `com.kubuszok::scala-sax-parser` (0.1.1, used for parsing strings on
all platforms) come in transitively; pin them explicitly only to override versions.

## Imports

```scala
import hearth.kindlings.xmlderivation._              // XmlEncoder/XmlDecoder, Kindlings*, XmlConfig, XmlDecodingError
import hearth.kindlings.xmlderivation.annotations._  // @xmlAttribute, @xmlContent, ...
import hearth.kindlings.xmlderivation.syntax._       // value.toXmlString("name"), str.fromXmlString[A]
```

## Core usage

```scala
case class Book(@xmlAttribute isbn: String, title: String, tags: List[String])

// Scala 2.13 (also valid on Scala 3)
implicit val bookCodec: KindlingsXmlCodec[Book] = KindlingsXmlCodec.derived[Book]
// or separately: KindlingsXmlEncoder.derived[Book] / KindlingsXmlDecoder.derived[Book]

// Scala 3
given KindlingsXmlCodec[Book] = KindlingsXmlCodec.derived
case class Book3(title: String) derives KindlingsXmlCodec   // or KindlingsXmlEncoder / KindlingsXmlDecoder

val elem: scala.xml.Elem = bookCodec.encode(Book("1-2", "Scala", List("a")), "book") // root element name is an argument
// <book isbn="1-2"><title>Scala</title><tags><item>a</item></tags></book>
bookCodec.decode(elem)   // Either[XmlDecodingError, Book]
```

Type class shapes: `XmlEncoder[A] { def encode(value: A, elementName: String): scala.xml.Elem }`,
`XmlDecoder[A] { def decode(elem: scala.xml.Elem): Either[XmlDecodingError, A] }`; `KindlingsXmlCodec[A]` extends both.

Inline helpers (derive and run, no instance kept):

| Method | Returns |
|---|---|
| `KindlingsXmlEncoder.encode[A](value, elementName)` | `scala.xml.Elem` |
| `KindlingsXmlEncoder.toXmlString[A](value, elementName)` | `String` (indented; text kept exactly after 0.4.0) |
| `KindlingsXmlDecoder.decode[A](elem)` | `Either[XmlDecodingError, A]` |
| `KindlingsXmlDecoder.fromXmlString[A](xml)` | `Either[XmlDecodingError, A]` |
| `value.toXmlString(elementName)` / `xml.fromXmlString[A]` (`syntax._`, Scala 2 and 3) | as above |

All take an implicit `XmlConfig` (default `XmlConfig.default`). Nested types are derived recursively in one expansion;
your own `implicit`/`given` `XmlEncoder[X]` / `XmlDecoder[X]` are used instead of derivation. `derived` is an
implicit/given on the Kindlings companions ("sanely-automatic"), but a bare `XmlEncoder[A]` lookup does not reach it -
define instances for root types you pass around as `XmlEncoder`/`XmlDecoder`.

## Configuration (`XmlConfig`)

```scala
implicit val xmlConfig: XmlConfig = XmlConfig.default
  .withAttributesByDefault
  .withDiscriminator("kind")
  .withSnakeCaseConstructorNames
```

| Field (builder) | Default | Effect |
|---|---|---|
| `defaultFieldMode` (`withAttributesByDefault`, `withElementsByDefault`, `withDefaultFieldMode(XmlFieldMode.X)`) | `XmlFieldMode.Element` | single-value fields as child elements or as attributes (see Attribute mode) |
| `fieldNameMapper` (`withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`, `withScreamingSnakeCaseFieldNames`, `withFieldNameMapper(f)`) | identity | element/attribute names |
| `constructorNameMapper` (`withSnakeCaseConstructorNames`, `withKebabCaseConstructorNames`, `withConstructorNameMapper(f)`) | identity | subtype names in the discriminator |
| `discriminatorAttribute` (`withDiscriminator(attr)`, `withNoDiscriminator`) | `Some("type")` | `<shape type="Circle">...`; `None` = subtype element inside: `<shape><Circle>...</Circle></shape>` (0.4.0 wrote `<Circle><shape>..</shape></Circle>`, which did not decode) |
| `enumAsStrings` (`withEnumAsStrings`) | `false` | enums of singletons as the case name (see Sealed traits and enums); no effect in 0.4.0 |
| `useDefaults` (`withUseDefaults`) | `false` | constructor defaults for missing fields (child elements and, after 0.4.0, attributes) when decoding |
| `transientNone` (`withTransientNone`) | `false` | omit `None` fields when encoding |
| `transientEmpty` (`withTransientEmpty`) | `false` | omit empty collections when encoding (empty strings are still written) |

## Annotations (`hearth.kindlings.xmlderivation.annotations`)

| Annotation | Effect |
|---|---|
| `@xmlAttribute` | field as an attribute, whatever the mode; single text values only (below) |
| `@xmlElement` | field as a child element, whatever the mode (overrides `withAttributesByDefault`) |
| `@xmlContent` | field as the element's text content: `<a href="...">Scala</a>`; every other field is then an attribute |
| `@xmlName("n")` | element/attribute name of a field, or a subtype's name; used as is (not transformed by the mappers) |
| `@xmlDiscriminator("kind")` | on a sealed trait / Scala 3 enum: its discriminator attribute, overriding `withDiscriminator` and `withNoDiscriminator` (after 0.4.0) |
| `@xmlWrapper("n")` | field inside an outer element `n`; a collection there as one element per item, named after the field (after 0.4.0; ignored in 0.4.0) |
| `@xmlUnwrapped` | collection / `Map[String, V]` as one element per item named after the field, no collection element (after 0.4.0) |
| `@transientField` | skipped both ways; field must have a default |

`@xmlAttribute` / `@xmlContent` accept (after 0.4.0; 0.4.0 wrote `toString`) single text values: `String`, numbers,
`Boolean`, `Char`, `BigDecimal`, `BigInt`, value types over them, enums of singletons with `withEnumAsStrings` (the
case name), a type with a user `XmlEncoder`/`XmlDecoder` (the text of its element), and `Option`s of these. Anything
else is a compile-time error, as are a non-attribute field next to `@xmlContent` and conflicting annotations on one
field (only `@xmlElement` + `@xmlWrapper` combine). Attribute values of built-in types are decoded directly (a user
`XmlDecoder[Int]` is not consulted for attributes).

```scala
case class Link(@xmlAttribute href: String, @xmlContent text: String)
KindlingsXmlEncoder.encode(Link("https://scala-lang.org", "Scala"), "a")
// <a href="https://scala-lang.org">Scala</a>
```

## Attribute mode (`withAttributesByDefault`)

After 0.4.0 it is decoded too (0.4.0: encode-only, its output failed with `MissingElement`), with a compile-time or a
runtime config. Only single text values become attributes: `String`, primitives, `BigDecimal`, `BigInt`, value types
over them (written unwrapped: `id="5"`, not `id="UserId(5)"`), enums of singletons with `withEnumAsStrings`, and
`Option`s of these (the value for `Some`, omitted for `None`). Collections, maps, case classes, sealed traits, enums
without `withEnumAsStrings`, types with a user instance, and `@xmlWrapper`/`@xmlUnwrapped` fields stay child elements; nested case classes put their own text fields as attributes of their element.

```scala
implicit val c: XmlConfig = XmlConfig.default.withAttributesByDefault
case class Point(x: Int, y: Int)
case class Route(name: String, @xmlElement note: String, stops: List[Point])
// <route name="A"><note>scenic</note><stops><item x="1" y="2"/><item x="3" y="4"/></stops></route>
```

An absent attribute decodes like an absent element: `None`, the default with `withUseDefaults`, else
`MissingAttribute`. With `withUseDefaults`, an omitted `None` of an `Option` field whose default is not `None` decodes
as that default (as with `withTransientNone`).

## Whitespace (after 0.4.0)

- `String` and `Char` keep whitespace exactly in elements, attributes and `@xmlContent` (no option; 0.4.0 trimmed).
  Numbers, `Boolean`, `BigDecimal`, `BigInt` and value types over them are trimmed before parsing.
- `Option[String]`: only an empty element is `None`; `<n> </n>` is `Some(" ")`.
- `toXmlString` indents but keeps text exactly, so its output round-trips. `scala.xml.PrettyPrinter` (or any
  reformatting) collapses/wraps text: don't use it on documents with whitespace-sensitive `String`s.
- XML parsers turn tabs and newlines in attribute values into spaces: keep multi-line `String`s in elements.

## Collections, sealed traits and enums

| Field | XML |
|---|---|
| `tags: List[String]` | `<tags><item>a</item><item>b</item></tags>` |
| `@xmlWrapper("tags") tag: List[String]` | `<tags><tag>a</tag><tag>b</tag></tags>` |
| `@xmlUnwrapped tag: List[String]` | `<tag>a</tag><tag>b</tag>` |
| `props: Map[String, Int]` | `<props><entry key="a"><value>1</value></entry></props>` |

Item elements are named after the field (`@xmlName` or mapped name). An empty wrapped collection is `<tags/>`; an
absent wrapper decodes as empty / `None` / the default with `withUseDefaults`. `@xmlWrapper` on a non-collection
puts the field's element inside it. Two fields with one wrapper name are a compile-time error.

| Value | default | `withNoDiscriminator` | `withEnumAsStrings` |
|---|---|---|---|
| `Circle(5.0): Shape` | `<shape type="Circle"><radius>5.0</radius></shape>` | `<shape><Circle><radius>5.0</radius></Circle></shape>` | compile error (below) |
| `Red: Color` (case objects, Scala 3 / Java enum, `Enumeration`) | `<color type="Red"/>` | `<color><Red/></color>` | `<color>Red</color>`, `color="Red"` as attribute |

Nested sealed traits are flattened (the leaf's name is the discriminator). `@xmlDiscriminator` counts on the type the
value is encoded as (a field typed as the parent uses the parent's); Java enums cannot carry it. With
`withEnumAsStrings`, a sealed trait that has a case class fails: `enumAsStrings is enabled but Shape has cases that are
not singletons (Circle, ...)` at compile time; with a runtime-only config the encoder throws
`IllegalArgumentException` and the decoder returns `Left(General(...))`. Fix: derive that type's instance with a config
without `enumAsStrings` and put it in implicit scope.

Absent vs empty (after 0.4.0; `withTransientNone` / `withTransientEmpty` output round-trips with any decoder config):

- absent `Option` element or attribute -> `None` (the default instead with `withUseDefaults` and a default value);
- absent collection/map element -> empty collection (same `withUseDefaults` exception);
- any other absent element/attribute -> `MissingElement` / `MissingAttribute` (also for `String`);
- empty `String` element/attribute (`<name/>`, `label=""`) -> `""`;
- `Option` attribute: written as the value for `Some`, omitted for `None`;
- empty `Option` element -> `None` (that is how `None`, and also `Some("")`, is written without `withTransientNone`);
  with `withTransientNone` it is `Some("")` for an `Option[String]` (`None` if the empty element does not decode).

Unknown extra child elements are ignored; the root element's own name is not checked when decoding. Maps, value classes
(unwrapped), case objects, Scala 3 / Java enums, generic and recursive types are supported.

## Errors

`XmlDecodingError` (sealed, extends `Exception`): `MissingAttribute(attributeName, elementName)`,
`MissingElement(childName, parentName)`, `InvalidValue(value, expectedType, context)`,
`UnexpectedElement(elementName, context)`, `MissingContent(elementName)`,
`UnknownDiscriminator(discriminatorValue, knownSubtypes)`, `MissingDiscriminator(attributeName, elementName)`,
`Multiple(errors)`, `General(msg)`. `toString` is `XmlDecodingError: <message>`, e.g.
`Invalid value 'x' for type Int in attr`.

## Gotchas

- **Missing field with a default fails** (`Missing child element <x> in <p>`): defaults are off by default here, unlike
  most other Kindlings modules. Fix: `XmlConfig.default.withUseDefaults`.
- **0.4.0 only (fixed after 0.4.0)**: an absent `Option` element failed (`Missing child element <o> in <p>`, also for
  `withTransientNone` output; workaround `= None` + `withUseDefaults`); an absent collection element failed; an empty
  `String` failed with `MissingContent` (and `withTransientEmpty` dropped it); an `Option` attribute was written as
  `Some(v)` / `None`. Round-trip-test your config.
- **0.4.0 only (fixed after 0.4.0)**: `withAttributesByDefault` output did not decode (`MissingElement` for a field
  written as an attribute); with a runtime config an `Option` attribute was written as `Some(x)`; `String` values were
  trimmed (code relying on that must now trim itself); the runtime-config encoder of a wide case class ran the compiler
  out of memory.
- **0.4.0 only (fixed after 0.4.0, breaking)**: `withEnumAsStrings` had no effect; `@xmlWrapper` / `@xmlUnwrapped`
  were ignored (remove them to keep the `<field><item>..` format); `@xmlAttribute` on a non-text field wrote its
  `toString`; `withNoDiscriminator` and nested sealed traits wrote output that did not decode; fields next to
  `@xmlContent` were dropped; `private val` constructor fields were not written.
- **New compile errors after 0.4.0** (each names the field): `@xmlAttribute needs a single text value, X is not one` -
  remove the annotation (child element) or provide an `XmlEncoder`/`XmlDecoder`; `next to @xmlContent the other fields
  have to be attributes`; `@xmlUnwrapped needs a collection or a map`; `enumAsStrings is enabled but X has cases that
  are not singletons`; `@xmlAttribute on the enum X writes the case name, which needs withEnumAsStrings`; `... cannot
  be combined` (conflicting annotations); `X has more than one field with @xmlWrapper("n")`; `@xmlContent needs a single text value`.
- **Sealed trait decoding fails with `Missing discriminator attribute 'type' in element <s>`**: XML produced elsewhere
  has no `type` attribute. Set its name with `withDiscriminator("...")`, or use `withNoDiscriminator` (subtype-named
  wrapper element) - the same config on both sides.
- **Root element name**: `encode` needs it as an argument and `decode` does not check it; `@xmlName` renames fields
  and subtypes, not the root.
- **`Field 'x' is annotated with @transientField but has no default value`** (compile error): add a default.
- **Config not applied**: the implicit `XmlConfig` must be in scope where `derived` / `encode` expands.

## Debugging, timeouts, policy

- Settings namespace: `xmlDerivation`.
- Log one derivation: `import hearth.kindlings.xmlderivation.debug._`; project-wide:
  `scalacOptions += "-Xmacro-settings:xmlDerivation.logDerivation=true"`.
- Timeout (default 5 s): `-Xmacro-settings:xmlDerivation.timeout=30s`.
- Opt-in policy marker: `import hearth.kindlings.xmlderivation.policy._` (`allowDerivationForXmlDerivation`).

Generic details: `kindlings-troubleshooting`, `kindlings-derivation-policy`, `kindlings-integrations` (refined / iron /
cats collections).

## Links

- User guide: <https://kindlings.readthedocs.io/en/0.4.0/xml-derivation/>
- Feature parity: <https://kindlings.readthedocs.io/en/0.4.0/feature-parity/#xml-derivation>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/xml-derivation/src/main>
