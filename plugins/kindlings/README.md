# `kindlings` plugin

Skills for **using** [Kindlings](https://github.com/kubuszok/kindlings) **0.4.0**. Kindlings provides sanely-automatic
type class derivation for Scala 2.13 and Scala 3, built on [Hearth](https://github.com/kubuszok/hearth). Docs:
<https://kindlings.readthedocs.io/en/0.4.0/>.

Install: `/plugin install kindlings@kubuszok` (Claude Code). See the [root README](../../README.md) for other harnesses.

## Skills

**Start here**

| Skill | Covers |
|---|---|
| `kindlings-getting-started` | Module map, dependencies, how `derived` / `derives` / inline helpers work, where to put instances, generic types, which upstream imports to remove |
| `kindlings-troubleshooting` | Derivation errors, debug logging, timeouts and `-Xmacro-settings`, known bugs and the versions that fixed them |
| `kindlings-derivation-policy` | Restricting where automatic derivation may happen (opt-in, allowed scopes, `AllowDerivation`) |
| `kindlings-migration` | Migrating from circe-generic, jsoniter `JsonCodecMaker`, kittens, avro4s, pureconfig-generic, tapir, scala-yaml, macwire, ScalaMock, quicklens; differences from each; upgrading between Kindlings versions |
| `kindlings-integrations` | Cats collections, refined, iron, neotype, scala-newtype support |
| `kindlings-custom-integration` | Making your own types (wrappers, collections, Option/Either-like) work in every Kindlings derivation through a Hearth provider module |
| `kindlings-testing` | Testing derived instances: golden wire-format tests, round-trip properties with derived `Arbitrary`, `Diff` assertions, differential tests during migration, compile-time and policy tests |
| `kindlings-http-api` | tapir HTTP APIs where Kindlings JSON codecs, tapir `Schema`s and the OpenAPI document share one configuration |

**Derivation modules**

| Skill | Module(s) |
|---|---|
| `kindlings-circe` | `kindlings-circe-derivation` |
| `kindlings-jsoniter` | `kindlings-jsoniter-derivation`, `kindlings-jsoniter-json`, `kindlings-tapir-openapi-jsoniter` |
| `kindlings-tapir-schema` | `kindlings-tapir-schema-derivation` |
| `kindlings-pureconfig` | `kindlings-pureconfig-derivation` (JVM only) |
| `kindlings-sconfig` | `kindlings-sconfig-derivation` |
| `kindlings-avro` | `kindlings-avro-derivation` (JVM only) |
| `kindlings-yaml` | `kindlings-yaml-derivation` |
| `kindlings-xml` | `kindlings-xml-derivation` |
| `kindlings-ubjson` | `kindlings-ubjson-derivation` |
| `kindlings-cats` | `kindlings-cats-derivation` |
| `kindlings-cats-tagless` | `kindlings-cats-tagless-derivation` |
| `kindlings-scalacheck` | `kindlings-scalacheck-derivation` |
| `kindlings-diff` | `kindlings-diff-derivation` |
| `kindlings-fast-show-pretty` | `kindlings-fast-show-pretty` |

**Macro utilities**

| Skill | Module(s) |
|---|---|
| `kindlings-di` | `kindlings-di`, `kindlings-di-cats` |
| `kindlings-mock` | `kindlings-mock` |
| `kindlings-optics` | `kindlings-optics` |
| `kindlings-parser` | `kindlings-parser`, `kindlings-parser-cats-effect`, `kindlings-parser-fs2` |
