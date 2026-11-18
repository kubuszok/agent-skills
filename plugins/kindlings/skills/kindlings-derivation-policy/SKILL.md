---
name: kindlings-derivation-policy
description: >-
  Restricting where Kindlings may derive instances - the per-library derivation policy configured with
  -Xmacro-settings:<ns>.policy.enabled=opt-in, <ns>.policy.allowedScopes=com.acme.json;com.acme.Codecs and
  <ns>.policy.optInByImport, plus the AllowDerivation marker imports
  (hearth.kindlings.<module>.policy.allowDerivationFor...). Explains what stays unconditional (instances already in
  implicit scope) and what is gated, how to get the "semi-automatic only / explicit instances only / no automatic
  derivation" behaviour teams ask for (circe semiauto-style, Kindlings issue 85), why Kindlings has no separate
  semiauto API, and the error text "Derivation of X[T] is enabled only in the following scopes" / "is globally
  disabled". Use when a team wants codecs defined in one place, when reviewing build settings containing
  policy.enabled, or when that compile error appears.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings derivation policy (opt-in mode)

A compile-time, per-library switch that limits **where** Kindlings may structurally derive instances for case classes,
sealed hierarchies and enums. It is the Kindlings answer to "I want semi-automatic only": derivation stays a single
recursive mechanism, but you choose the places where it is allowed to happen.

Version: written for Kindlings 0.4.0 (the policy exists since 0.3.1). Check the version in the user's build
(`build.sbt` / `build.mill` / `project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/derivation-policy/>.

## Settings

All keys are `-Xmacro-settings` under the module's namespace (the same one as its timeout, table below). Each library
is independent: you can lock down JSON codecs while leaving `Show`/`Eq` derivation open.

| Key | Values | Default |
|---|---|---|
| `<ns>.policy.enabled` | `always-allowed` (aliases `always-allow`, `always`, `allowed`) or `opt-in` (alias `optin`) | `always-allowed` |
| `<ns>.policy.allowedScopes` | fully-qualified packages / objects / classes separated by `;` or `|` (never `,`) | none |
| `<ns>.policy.optInByImport` | `true` / `false` | `true` |

An unrecognised `enabled` value emits a warning and means `always-allowed`.

```scala
// build.sbt - one -Xmacro-settings option per key
Compile / scalacOptions ++= Seq(
  "-Xmacro-settings:circeDerivation.policy.enabled=opt-in",
  "-Xmacro-settings:circeDerivation.policy.allowedScopes=com.acme.json;com.acme.model"
)
```

Scala 3 splits one `-Xmacro-settings:a,b` option on commas and Scala 2 does not, hence `;` / `|` inside
`allowedScopes` and one option per key. Mill / scala-cli forms: see `kindlings-troubleshooting`.

## How a location is decided

Once per macro expansion, at the first type for which the macro would generate code instead of using an existing
implicit:

1. `always-allowed` -> allowed.
2. `opt-in`: if any enclosing package / object / class of the expansion point matches an `allowedScopes` entry ->
   allowed. Matching is prefix-aware: `com.acme.json` covers `com.acme.json.v2.Codecs`; an object/class entry covers
   everything inside it.
3. Otherwise, if `optInByImport=true` and the library's marker implicit is in scope -> allowed.
4. Otherwise -> compile error.

The decision covers the whole recursive expansion: if the root is allowed, every nested case class / enum it reaches is
derived too (recursion is not optional); if denied, nothing is generated.

**Never gated**: using an instance that already exists in implicit scope (your `implicit val` / `given`, upstream
built-ins such as circe's `Encoder[List[A]]`) and references to types already being derived in the same expansion.
The user guide describes the policy as gating only product/sum derivation, with built-ins, collections, `Option`,
value types and named tuples unconditional. In the 0.4.0 source, though, the single check sits right after the
"use an existing implicit" rule and before every other rule, and the root type of `X.derived[T]` / an inline helper
never goes through implicit search (the macro would find itself). So at a denied site **any** explicit derivation is
rejected - also `KindlingsEncoder.derived[List[User]]` - while summoning the upstream type class
(`Encoder[List[User]]`, `asJson`) works whenever the element instances exist. Inline helpers
(`KindlingsEncoder.encode(x)`, `writeToString`, ...) derive too and are gated the same way. A Scala 3 `derives` clause
expands in the type's companion, so the type's own package/companion must be allowed (or the file must import the
marker).

## Opt-in markers

| Module | Namespace | Marker import |
|---|---|---|
| circe | `circeDerivation` | `hearth.kindlings.circederivation.policy.allowDerivationForCirceDerivation` |
| jsoniter | `jsoniterDerivation` | `hearth.kindlings.jsoniterderivation.policy.allowDerivationForJsoniterDerivation` |
| tapir schema | `tapirSchemaDerivation` | `hearth.kindlings.tapirschemaderivation.policy.allowDerivationForTapirSchemaDerivation` |
| pureconfig | `pureconfigDerivation` | `hearth.kindlings.pureconfigderivation.policy.allowDerivationForPureconfigDerivation` |
| sconfig | `sconfigDerivation` | `hearth.kindlings.sconfigderivation.policy.allowDerivationForSconfigDerivation` |
| avro | `avroDerivation` | `hearth.kindlings.avroderivation.policy.allowDerivationForAvroDerivation` |
| yaml | `yamlDerivation` | `hearth.kindlings.yamlderivation.policy.allowDerivationForYamlDerivation` |
| xml | `xmlDerivation` | `hearth.kindlings.xmlderivation.policy.allowDerivationForXmlDerivation` |
| ubjson | `ubjsonDerivation` | `hearth.kindlings.ubjsonderivation.policy.allowDerivationForUbjsonDerivation` |
| cats | `catsDerivation` | `hearth.kindlings.catsderivation.policy.allowDerivationForCatsDerivation` |
| cats-tagless | `catsTaglessDerivation` | `hearth.kindlings.catstaglessderivation.policy.allowDerivationForCatsTaglessDerivation` |
| scalacheck | `scalacheckDerivation` | `hearth.kindlings.scalacheckderivation.policy.allowDerivationForScalacheckDerivation` |
| diff | `diffDerivation` | `hearth.kindlings.diffderivation.policy.allowDerivationForDiffDerivation` |
| fast-show-pretty | `fastShowPrettyDerivation` | `hearth.kindlings.fastshowpretty.policy.allowDerivationForFastShowPretty` |

`import hearth.kindlings.circederivation.policy._` works as well. The markers are plain `implicit val`s, so Scala 3
`import ...policy.*` brings them in. `di`, `mock`, `optics` and `parser` are not type-class derivation and have no
policy.

## Recipes

**"Instances only in the companion of each model type"** (the usual semi-auto discipline):

```text
-Xmacro-settings:circeDerivation.policy.enabled=opt-in
-Xmacro-settings:circeDerivation.policy.allowedScopes=com.acme.model
-Xmacro-settings:circeDerivation.policy.optInByImport=false
```

```scala
package com.acme.model
import hearth.kindlings.circederivation._
import io.circe.{Decoder, Encoder}

final case class User(id: Long, name: String, address: Address)
final case class Address(city: String)
object User {
  implicit val enc: Encoder[User] = KindlingsEncoder.derived[User] // allowed: inside com.acme.model; Address derived inline
  implicit val dec: Decoder[User] = KindlingsDecoder.derived[User]
}
```

```scala
package com.acme.http
import io.circe.syntax._
def render(u: com.acme.model.User) = u.asJson          // fine: uses User.enc, nothing is derived here
// KindlingsEncoder.encode(u)  - compile error: com.acme.http is not an allowed scope
```

**"All codecs in one object"**: `allowedScopes=com.acme.json.Codecs` and define every `implicit val` there; import
`Codecs._` where needed.

**"Allowed by exception"**: keep `optInByImport=true` (default) and add the marker import in the few files that may
derive ad hoc (tests, scripts).

**"Disable everywhere"**: `enabled=opt-in` with no `allowedScopes` and `optInByImport=false` - only hand-written or
otherwise existing instances are accepted.

**"Every nested type must have its own explicit instance"** - not what the policy does (nested types of an allowed
derivation are derived inline). Define instances for the nested types explicitly (they are then used instead of being
re-derived). cats-derivation additionally has an undocumented `hearth.kindlings.catsderivation.StrictDerivation`
marker (`implicit val strict: StrictDerivation = StrictDerivation.instance`) that makes monomorphic cats derivations
(Show, Eq, Order, Hash, Semigroup, Monoid, ...) fail when a field's instance would have to be derived; other modules
have nothing equivalent.

## The error

```text
Derivation of FastShowPretty[com.acme.show.User] is enabled only in the following scopes:
 - com.acme.show

Currently you are in the following scope: com.acme.web.Handler.

You are allowed to enable this derivation locally by adding the import:
import hearth.kindlings.fastshowpretty.policy.allowDerivationForFastShowPretty
```

With no `allowedScopes`: `Derivation of X[T] is globally disabled.` The import hint is shown only when
`optInByImport=true`. Fix: use the canonical instance (import it / put it in implicit scope), move the derivation into
an allowed scope, or import the marker.

## Why there is no separate semiauto API (FAQ, in brief)

- The auto/semi split only ever governs case classes and sealed hierarchies - primitives, collections, `Option`,
  newtypes always "just work" - so the line is an implementation detail leaking into the API.
- Two import sets where swapping one silently changes semantics hurt newcomers most.
- Semi-auto does not guarantee coherence anyway: a stray import or a new companion instance can change behaviour.
  Golden tests guard wire contracts; the policy guards where instances come from.
- `derived[A]` is also recursive, so a single expansion derives all nested types (faster than per-type instances
  plus `Lazy` knots), and automatic use costs no more than explicit use.

Discussion: [issue #85](https://github.com/kubuszok/kindlings/issues/85); FAQ:
<https://kindlings.readthedocs.io/en/0.4.0/faq/#why-not-separate-automatic-and-semi-automatic-derivation>.

## Gotchas

- **Policy seems ignored** - wrong namespace (fast-show-pretty uses `fastShowPrettyDerivation`), scopes separated with
  commas, or several keys in one `-Xmacro-settings` option. Check with the `<ns>.timeout=1ms` canary from
  `kindlings-troubleshooting`.
- **Error in a test file** - scopes are matched by package/object name, not by source set, so tests in another
  package are denied when the settings also apply to test compilation. Add the marker import in tests (keep
  `optInByImport=true`), list the test package, or apply the settings to main sources only (sbt: `Compile /
  scalacOptions`, and check the build does not copy them into `Test`).
- **Existing instance not used, derivation attempted instead** - the instance is not in implicit scope at that call
  site (e.g. defined in an unrelated object that is not imported). The policy error points at exactly these places.
