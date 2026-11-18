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
| `KindlingsXmlEncoder.toXmlString[A](value, elementName)` | `String` (pretty-printed) |
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
| `defaultFieldMode` (`withAttributesByDefault`, `withElementsByDefault`, `withDefaultFieldMode(XmlFieldMode.X)`) | `XmlFieldMode.Element` | fields as child elements or as attributes |
| `fieldNameMapper` (`withSnakeCaseFieldNames`, `withKebabCaseFieldNames`, `withPascalCaseFieldNames`, `withScreamingSnakeCaseFieldNames`, `withFieldNameMapper(f)`) | identity | element/attribute names |
| `constructorNameMapper` (`withSnakeCaseConstructorNames`, `withKebabCaseConstructorNames`, `withConstructorNameMapper(f)`) | identity | subtype names in the discriminator |
| `discriminatorAttribute` (`withDiscriminator(attr)`, `withNoDiscriminator`) | `Some("type")` | `<shape type="Circle">...`; `None` = subtype-named wrapper: `<Circle><shape>...</shape></Circle>` |
| `enumAsStrings` (`withEnumAsStrings`) | `false` | case-object enums as text content |
| `useDefaults` (`withUseDefaults`) | `false` | constructor defaults for missing fields when decoding |
| `transientNone` (`withTransientNone`) | `false` | omit `None` fields when encoding |
| `transientEmpty` (`withTransientEmpty`) | `false` | omit empty collections when encoding |

## Annotations (`hearth.kindlings.xmlderivation.annotations`)

| Annotation | Effect |
|---|---|
| `@xmlAttribute` | field as an attribute |
| `@xmlElement` | field as a child element (overrides `withAttributesByDefault`) |
| `@xmlContent` | field as the element's text content: `<a href="...">Scala</a>` |
| `@xmlName("n")` | element/attribute name of a field or subtype |
| `@xmlWrapper("n")` | wrap a collection field in an extra element |
| `@xmlUnwrapped` | collection items inlined directly, no wrapper element |
| `@transientField` | skipped both ways; field must have a default |

```scala
case class Link(@xmlAttribute href: String, @xmlContent text: String)
KindlingsXmlEncoder.encode(Link("https://scala-lang.org", "Scala"), "a")
// <a href="https://scala-lang.org">Scala</a>
```

Collections are written as a field element with `<item>` children by default (`<tags><item>a</item></tags>`).
`Option` fields: `None` is written as an empty element (`<name/>`) and `<name/>` decodes as `None`, but an **absent**
`Option` element fails (`MissingElement`) unless the field has a default and `withUseDefaults` is on. Unknown extra
child elements are ignored; the root element's own name is not checked when decoding. Maps, value classes
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
- **Absent `Option` element fails** (`Missing child element <o> in <p>`), also for XML written with `withTransientNone`:
  such output does not decode back. Fix: give the field `= None` and decode with `withUseDefaults` (or do not use
  `withTransientNone` for data you read back). Round-trip-test your config.
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
