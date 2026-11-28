---
name: kindlings-custom-integration
description: >-
  Supporting your own types (validated ids, wrapper/newtype libraries, smart-constructor wrappers, custom collections,
  Option-like or Either-like types) in every Kindlings derivation at once - circe, jsoniter, avro, pureconfig, yaml,
  xml, tapir, cats, fast-show-pretty - with a small integration module holding a Hearth StandardMacroExtension
  provider (IsValueType, IsCollection, IsMap, IsOption, IsEither) listed in
  META-INF/services/hearth.std.StandardMacroExtension, instead of one implicit per library. Covers when to write one
  (AnyVal and Scala 3 opaque types are built in), sbt module layout (hearth dependency, cross-quotes plugin,
  kind-projector), verifying with logDerivation, precedence vs user implicits and provider priority, testing,
  Provided scope and runtime footprint. Use on "was not handled by any ... derivation rule" or "is not a value type"
  for your own type, or when writing something like kindlings-refined-integration for another library.
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Your own types in every Kindlings derivation

Kindlings asks Hearth "is this a wrapper / collection / option / either?" through the standard extensions, and the
answers come from providers found on the compile classpath. A small module with a provider for your type makes every
Kindlings derivation (and every other Hearth-based macro) handle it, with no imports at the use site. This is how
`kindlings-refined-integration`, `-iron-`, `-neotype-`, `-newtype-` and `-cats-integration` work.

Version: written for Kindlings 0.4.0 (built on Hearth 0.4.5). Check the version in the user's build (`build.sbt` /
`build.mill` / `project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/custom-integrations/> (fall back to `en/latest`). The provider must be
compiled against the Hearth version that the user's Kindlings version depends on (0.4.0: Hearth 0.4.5; the next
Kindlings release: the Hearth release after 0.4.5).

Provider mechanics in depth: `hearth-standard-extensions` (with its `writing-providers.md`) and
`hearth-macro-extensions`. Existing integrations: `kindlings-integrations`.

## Decision guide

| Situation | Do this |
|---|---|
| `final case class X(value: T) extends AnyVal` | nothing: built in, (un)wrapped as `T`. The decoder calls the **constructor**, so a validating `X.from` is **not** used |
| Scala 3 `opaque type X = T` with a companion method `T => X`, `T => Either[String, X]` or `T => Either[Iterable[String], X]` | nothing: built in, decoding runs that method and reports its `Left` |
| Type from refined, Iron, neotype, scala-newtype, cats | add the matching `kindlings-*-integration` (skill `kindlings-integrations`) |
| Your type, used with 1-2 libraries | write implicits (`Encoder`/`Decoder`, `JsonValueCodec`, ...) in its companion. They always win |
| Your wrapper/collection used with many libraries or across many projects | a provider module (below) |
| Validated `AnyVal` that must run its smart constructor | a provider with `priority` above 0 (beats the built-in AnyVal provider) |
| A type with several fields or a sealed hierarchy | not a provider: Kindlings derives it already, or give implicits |

Which shape to implement:

| Your type looks like | Provider | Decoding gets |
|---|---|---|
| wrapper of one value (id, newtype, refined) | `IsValueType` with `unwrap` + `wrap` | `CtorLikeOf.PlainValue` (cannot fail) or `EitherStringOrValue` / `EitherIterableStringOrValue` / `EitherThrowableOrValue` / `EitherIterableThrowableOrValue` (validated) |
| collection of `E` | `IsCollection` (`asIterable`, `factory`, `build`) | `build` may fail (e.g. non-empty) |
| map `K -> V` | `IsMapOf`, registered on `IsCollection` | as above |
| optional value | `IsOption` | - |
| two-sided result | `IsEither` | - |

## Module layout and build (sbt, verified with sbt 1.13.1 on 2.13.18 and 3.8.3)

```scala
val hearthVersion    = "0.4.5" // the Hearth version of your Kindlings version
val kindlingsVersion = "0.4.0"

ThisBuild / scalaVersion       := "3.8.3"
ThisBuild / crossScalaVersions := Seq("3.8.3", "2.13.18")

lazy val mylib = project // your types; no Hearth, no Kindlings

lazy val mylibKindlings = project
  .in(file("mylib-kindlings"))
  .dependsOn(mylib)
  .settings(
    libraryDependencies += "com.kubuszok" %% "hearth" % hearthVersion,
    libraryDependencies ++= (CrossVersion.partialVersion(scalaVersion.value) match {
      case Some((3, _)) => Seq(compilerPlugin("com.kubuszok" %% "hearth-cross-quotes" % hearthVersion))
      case _            => Seq(compilerPlugin("org.typelevel" % "kind-projector" % "0.13.4" cross CrossVersion.full))
    }),
    scalacOptions ++= (CrossVersion.partialVersion(scalaVersion.value) match {
      case Some((3, _)) => Seq("-Xkind-projector") // for IsValueTypeOf[A, *]
      case _            => Seq("-Xsource:3")
    }),
    libraryDependencies ++= Seq(
      "com.kubuszok"  %% "kindlings-circe-derivation" % kindlingsVersion % Test,
      "io.circe"      %% "circe-parser"               % "0.14.15"        % Test,
      "org.scalameta" %% "munit"                      % "1.2.1"          % Test
    )
  )

lazy val app = project.dependsOn(mylib, mylibKindlings % Provided) // compile-time only, see "Runtime footprint"
```

Files of `mylib-kindlings`:

```
src/main/scala/mylib/kindlings/internal/compiletime/IsValueTypeProviderForUserId.scala
src/main/resources/META-INF/services/hearth.std.StandardMacroExtension   # one line per provider class:
    mylib.kindlings.internal.compiletime.IsValueTypeProviderForUserId
```

For Scala.js / Native users publish the module for those platforms too (`%%%`); it still runs in the JVM compiler.

## The provider (validated wrapper, verified on 2.13.18 and 3.8.3)

The type: `final class UserId private (val value: Long)` with
`object UserId { def from(value: Long): Either[String, UserId] }` (not an `AnyVal`, not a case class).

```scala
package mylib.kindlings.internal.compiletime

import hearth.MacroCommons
import hearth.fp.data.NonEmptyList
import hearth.std.{ProviderResult, StandardMacroExtension, StdExtensions}

final class IsValueTypeProviderForUserId extends StandardMacroExtension { loader =>

  // override def priority: Int = 1000   // needed only to beat a built-in provider (e.g. for an AnyVal)

  override def extend(ctx: MacroCommons & StdExtensions): Unit = {
    import ctx.*

    IsValueType.registerProvider(new IsValueType.Provider {

      override def name: String = loader.getClass.getName

      private lazy val UserIdType: Type[mylib.UserId] = Type.of[mylib.UserId]
      private lazy val LongType: Type[Long] = Type.of[Long]

      override def parse[A](tpe: Type[A]): ProviderResult[IsValueType[A]] =
        if (tpe =:= UserIdType) {
          implicit val A: Type[A] = tpe
          implicit val L: Type[Long] = LongType

          val ctor = CtorLikeOf.EitherStringOrValue[Long, A](
            (value: Expr[Long]) =>
              Expr.quote(mylib.UserId.from(Expr.splice(value)).asInstanceOf[Either[String, A]]),
            None
          )
          ProviderResult.Matched(
            Existential[IsValueTypeOf[A, *], Long](new IsValueTypeOf[A, Long] {
              override val unwrap: Expr[A] => Expr[Long] =
                (outer: Expr[A]) => Expr.quote(Expr.splice(outer).asInstanceOf[mylib.UserId].value)
              override val wrap: CtorLikeOf[Long, A] = ctor
              override lazy val ctors: CtorLikes[A] = NonEmptyList.one(Existential[CtorLikeOf[*, A], Long](ctor))
            })
          )
        } else skippedLazily(s"${tpe.prettyPrint} is not mylib.UserId")
    })
  }
}
```

For a wrapper that cannot fail use `CtorLikeOf.PlainValue[Long, A](value => Expr.quote(...), None)`. For generic
wrappers (`Wrapper[T]`) match with `Type.Ctor1.of[Wrapper].unapply(tpe)` and move the quotes into a helper method with
ordinary type parameters (see `hearth-standard-extensions/writing-providers.md`).

Result with `kindlings-circe-derivation` and `kindlings-jsoniter-derivation` 0.4.0, for `case class User(id: UserId,
name: String)`: encodes `{"id":42,"name":"Alice"}`; decoding `{"id":-1,...}` gives
`Left(DecodingFailure at .id: UserId must be positive, got -1)` (circe) and `JsonReaderException` "UserId must be
positive, got 0, offset: ..." (jsoniter). `Map[UserId, String]` keys, `List[UserId]`, `Option[UserId]` work too
(`{"owners":{"1":"x"},"members":[1],"lead":1}`), and `FastShowPretty` renders the underlying value (`1L`).

## Verify that Kindlings picked it up

Enable logging for one module (`-Xmacro-settings:circeDerivation.logDerivation=true`, or
`import hearth.kindlings.circederivation.debug._`; namespaces per module in `kindlings-troubleshooting`). Look for:

```
hearth.std.StandardMacroExtension - Successfully loaded 36 extensions:
  - mylib.kindlings.internal.compiletime.IsValueTypeProviderForUserId
...
Attempting to handle mylib.UserId as a value type
...
Derived encoder for mylib.UserId: encode_Long(userid.asInstanceOf[mylib.UserId].value, configuration)
```

(In 0.4.0 the extension list shows up in the decoder / jsoniter codec logs, the circe encoder log does not print it.)
Without the provider the error lists `The type mylib.UserId is not a value type` under "handle as value type".

## Precedence

1. **Implicits in scope win**: Kindlings tries "use implicit when available" before value types/collections. An
   `implicit val e: Encoder[UserId]` changes the output (`{"id":"user-5",...}` verified) even with the provider present.
2. **Between providers** the higher `priority` is asked first (default 0). Built-in AnyVal provider: 0; Scala 3 opaque
   types: -1000; Kindlings' integrations: 1000. Equal priorities follow classpath order - do not rely on it.
3. Provider-handled types are not "structural derivation", so a derivation policy of `opt-in` (skill
   `kindlings-derivation-policy`) does not block them.
4. tapir schema derivation uses the underlying type's schema with no validators. Add an implicit `Schema` for the
   wrapper when you want constraints documented.

## Testing

Test sources compile after main sources, so the provider module can test itself (shown in the build above):

```scala
final class UserIdProviderSpec extends munit.FunSuite {
  case class User(id: UserId, name: String)
  implicit val encoder: Encoder[User] = KindlingsEncoder.derived[User]
  implicit val decoder: Decoder[User] = KindlingsDecoder.derived[User]

  test("encodes as the underlying Long") {
    assertEquals(encoder(User(UserId.from(42L).toOption.get, "Alice")).noSpaces, """{"id":42,"name":"Alice"}""")
  }
  test("validates on decoding") {
    val result = io.circe.parser.decode[User]("""{"id":0,"name":"Alice"}""")
    assert(result.left.exists(_.getMessage.contains("UserId must be positive")), result)
  }
}
```

Also test a round trip, every Kindlings module you support, both Scala versions (`+test`), and that a user implicit
still wins.

## Runtime footprint

The provider runs only inside the compiler. The generated code calls your library (`UserId.from`, `.value`), not the
provider. So:

- Consumers can add it as `% Provided` (sbt) / `//> using compileOnly.dep` (scala-cli). Verified: the app runs without
  it on the runtime classpath. Downstream modules that derive instances need it on their own compile classpath.
- If generated code calls a helper of yours at runtime (needed e.g. for types a Scala 2 quote cannot name), put that
  helper in a separate `internal.runtime` package and keep the dependency in `Compile` scope. Keep that helper
  binary-compatible.
- For fat jars, `internal.compiletime` and `META-INF/services/hearth.*` can be discarded like Kindlings' own (FAQ:
  <https://kindlings.readthedocs.io/en/0.4.0/faq/>).

## Gotchas

- **`The type X was not handled by any ... derivation rule` / `X is not a value type`** -> the provider jar is not on
  the compile classpath where the derivation expands (added only `% Test`, or only to another module), the services
  file is missing or misspelled (`META-INF/services/hearth.std.StandardMacroExtension`), or the provider is compiled in
  the same compilation unit as the derivation.
- **AnyVal smart constructor ignored, invalid values decode** -> the built-in AnyVal provider calls the constructor.
  Give your provider `priority` > 0, or provide implicits.
- **`ClassCastException: scala.util.Right cannot be cast to ...` from `DeriveArbitrary.derived`** -> bug in
  `kindlings-scalacheck-derivation` 0.4.0 (fixed after 0.4.0): for value types with a validating constructor
  (`Either...` `CtorLikeOf`, also refined and Scala 3 opaque types with an `Either` smart constructor) the generator
  returns the `Either` instead of the value. On 0.4.0 provide an `Arbitrary` for the wrapper yourself.
- **Other types suddenly derived through your provider, or broken generated code** -> `parse` returned `Matched` for
  types it cannot build. Match only your exact type, decline with `skippedLazily(reason)` (or `failed(throwable)`),
  and summon what construction needs inside `parse` (decline if missing) instead of failing later in a quote.
- **`IsValueTypeOf[A, *]` does not compile** -> kind-projector missing (Scala 2 plugin, Scala 3 `-Xkind-projector`).
- **Scala 3: `Expr.quote` errors or not rewritten** -> the `hearth-cross-quotes` compiler plugin is missing.
- **Works with sbt, not with scala-cli tests in the same project** -> scala-cli 1.19.0 with `--server=false` did not
  see the main-scope provider from test-scope macros; use the default Bloop server or a separate module.

## Reference implementations (Kindlings 0.4.0)

- [IsValueTypeProviderForRefined](https://github.com/kubuszok/kindlings/blob/0.4.0/refined-integration/src/main/scala/hearth/kindlings/refinedintegration/internal/compiletime/IsValueTypeProviderForRefined.scala) (summons `Validate`, `EitherStringOrValue`)
- [IsValueTypeProviderForIron](https://github.com/kubuszok/kindlings/blob/0.4.0/iron-integration/src/main/scala/hearth/kindlings/ironintegration/internal/compiletime/IsValueTypeProviderForIron.scala), [IsValueTypeProviderForNeotype](https://github.com/kubuszok/kindlings/blob/0.4.0/neotype-integration/src/main/scala/hearth/kindlings/neotypeintegration/internal/compiletime/IsValueTypeProviderForNeotype.scala) (Scala 3 only)
- [IsValueTypeProviderForNewtype](https://github.com/kubuszok/kindlings/blob/0.4.0/newtype-integration/src/main/scala/hearth/kindlings/newtypeintegration/internal/compiletime/IsValueTypeProviderForNewtype.scala) (wrappers as type members of an object)
- cats: [collections and maps](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/compiletime/CatsCollectionAndMapProviders.scala) with [runtime helper](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/runtime/CatsConversions.scala), [Validated as IsEither](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/compiletime/IsEitherProviderForValidated.scala), [Const as IsValueType](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/compiletime/IsValueTypeProviderForConst.scala)
- Docs: <https://kindlings.readthedocs.io/en/0.4.0/custom-integrations/>, Hearth
  [Standard Extensions](https://scala-hearth.readthedocs.io/en/0.4.5/standard-extensions/).
