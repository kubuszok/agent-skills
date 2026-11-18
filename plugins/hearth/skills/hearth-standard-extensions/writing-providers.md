# Writing a Hearth standard-extension provider (Hearth 0.4.5)

An integration module teaches `IsCollection`/`IsMap`/`IsOption`/`IsEither`/`IsValueType` about a library's types. Every Hearth-based macro that uses the standard extensions picks it up when the module is on the compile classpath - no imports.

Create one only for container-shaped or wrapper types. Types that need full derivation (several fields, sealed hierarchies) belong in a derivation rule instead.

## 1. Module and service registration

- Depend on `hearth` (and the library you integrate) in `Compile` scope; cross-compile like any Hearth macro module (plugin on Scala 3 if you use Cross Quotes).
- Register each extension class in `src/main/resources/META-INF/services/hearth.std.StandardMacroExtension`, one fully-qualified class name per line:

```
mylib.integration.internal.MyCollectionProviders
mylib.integration.internal.MyValueTypeProviders
```

(Hearth and Kindlings generate this file with a build plugin of their own; it is not published - write it by hand or with your own generator.) Extensions are loaded with `java.util.ServiceLoader` from the compiler's classpath, so the class must have a public no-arg constructor.

## 2. The extension

```scala
package mylib.integration.internal

import hearth.MacroCommons
import hearth.fp.data.NonEmptyList
import hearth.std.{ProviderResult, StandardMacroExtension, StdExtensions}

final class MyValueTypeProviders extends StandardMacroExtension { loader =>

  // Higher = registered (and matched) earlier. Built-ins are 0 (the default), Hearth's opaque-type provider is -1000.
  // Raise it above 0 only to beat a built-in provider (e.g. the AnyVal one, if mylib.Refined is a value class).
  override def priority: Int = 1000

  @scala.annotation.nowarn("msg=is never used")
  override def extend(ctx: MacroCommons & StdExtensions): Unit = {
    import ctx.*

    // Helper with REGULAR type parameters: quotes inside never see path-dependent `inner.Underlying`
    def mk[A, In, P](AT: Type[A], InT: Type[In], PT: Type[P]): IsValueType[A] = {
      implicit val A: Type[A] = AT
      implicit val In: Type[In] = InT
      implicit val P: Type[P] = PT
      val wrapCtor = CtorLikeOf.EitherStringOrValue[In, A](
        (in: Expr[In]) => Expr.quote(mylib.Refined.validate[In, P](Expr.splice(in)).asInstanceOf[Either[String, A]]),
        None
      )
      Existential[IsValueTypeOf[A, *], In](new IsValueTypeOf[A, In] {
        override val unwrap: Expr[A] => Expr[In] = a => Expr.quote(Expr.splice(a).asInstanceOf[mylib.Refined[In, P]].value)
        override val wrap: CtorLikeOf[In, A] = wrapCtor
        override lazy val ctors = NonEmptyList.one(Existential[CtorLikeOf[*, A], In](wrapCtor))
      })
    }

    IsValueType.registerProvider(new IsValueType.Provider {
      override def name: String = s"${loader.getClass.getName}#Refined"

      private lazy val RefinedCtor = Type.Ctor2.of[mylib.Refined]   // lazy: paid only when queried

      // optional cheap and SOUND pre-filter: false only if parse could never match
      override def mightMatch[A](tpe: Type[A]): Boolean = true

      override def parse[A](tpe: Type[A]): ProviderResult[IsValueType[A]] =
        RefinedCtor.unapply(tpe) match {
          case Some((inner, pred)) => ProviderResult.Matched(mk(tpe, inner.Underlying, pred.Underlying))
          case None                => skippedLazily(s"${tpe.prettyPrint} is not Refined") // message built only if read
        }
    })
  }
}
```

Collections implement `IsCollectionOf[A, E]` (`asIterable`, `type CtorResult` + `implicit val CtorResult: Type[CtorResult]`, `factory: Expr[Factory[E, CtorResult]]`, `build: CtorLikeOf[Builder[E, CtorResult], A]`, optionally `foreach`, `sizeHintForBuilder` only if O(1) and non-consuming) and are wrapped as `Existential[IsCollectionOf[A, *], E](...)`. A convenient `CtorResult` is `List[E]`, converted to the target (with a `Left` for invalid input, e.g. empty for a non-empty collection) in `build`. Map-like types implement `IsMapOf[A, Pair]` (any pair type, e.g. `(K, V)` or `java.util.Map.Entry[K, V]`; members `Key`, `Value`, `key`, `value`, `pair`) and are registered on **`IsCollection`**, wrapped as `Existential[IsCollectionOf[A, *], Pair]` - `IsMap` reads through it via `asMap`. Options: `IsOptionOf` (`empty`, `of`, `fold`, `getOrElse`, `orElse`); eithers: `IsEither` with `IsEitherOf`.

Inside `parse` only return `Matched` for a type you can actually build; decline with `skippedLazily(reason)` and report construction errors with `failed(throwable)`. Bottom types (`Nothing`/`Null`) are filtered out before providers run.

## 3. Patterns and pitfalls

- **Helper-method pattern** (Scala 2 "not found: value elem"): types from `ctor.unapply` are path-dependent; move every `Expr.quote` into a method whose element types are regular type parameters (as `mk` above).
- **Runtime-helper pattern**: when a type cannot be written inside a Scala 2 quote (e.g. newtype aliases like Cats `NonEmptyChain` -> "not found: value data"), put the logic in a small runtime object taking/returning `Any` and only call it from the quote. Keep that object binary compatible (MiMa).
- **Cast inside the quote, not outside**: `Expr.quote(helper(Expr.splice(v)).asInstanceOf[Iterable[E]])`, not `(Expr.quote(helper(...)): Expr[Any]).asInstanceOf[Expr[Iterable[E]]]` - Scala 3 `-Xcheck-macros` rejects trees whose type differs from the `Expr` type.
- **Summon what construction needs** (e.g. `Ordering`/`Order[E]` for sorted types) in `parse` with `Expr.summonImplicit`, and decline with a reason when it is missing.
- **Opaque types**: Hearth's opaque provider (priority -1000) matches any opaque type with a companion constructor, so a provider adding validation for an opaque wrapper already wins at the default priority 0. `Type.CtorN.of[F].unapply` also matches subtypes of the constructor (it reads the base type) on both Scala versions.
- **Wrappers that are type members of an object** (`Foo.Type` newtypes): get the object with `Type.pseudoCompanionObject[A]`, read the wrapped type from its base type (`Type.Ctor1.of[Newtype].unapply`) or from a member's signature through the `Method` API, and check that signature mentions `A` itself.
- **Avoid `Type.of[A]` bootstrap cycles**: never `implicit val X: Type[X] = Type.of[X]` where the only source would be that val; take `Type`s as explicit parameters (as in `mk`). Do not `import ctx3.{*, given}` of the platform commons in a Scala 3 provider - the plugin then rewrites `implicit val AT: Type[A] = tpe` into a self-reference ("Infinite loop in function body").
- **Custom macro traits**: `MacroExtension[A & B & C]` checks `ctx` against a single erased class (the intersection's `ClassTag`), not all components; extend `MacroExtension[MacroCommons & StdExtensions]` and match `ctx` against your trait inside `extend`.
- **Test** with a module that depends on your integration and on some Hearth-based derivation: encode, decode valid, decode invalid (validated wrappers, empty non-empty collections), round trip, and that a user-provided instance still wins.

## Reference implementations (Kindlings 0.4.0)

- Collections and maps: [CatsCollectionAndMapProviders](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/compiletime/CatsCollectionAndMapProviders.scala) with runtime helper [CatsConversions](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/runtime/CatsConversions.scala); either-like: [IsEitherProviderForValidated](https://github.com/kubuszok/kindlings/blob/0.4.0/cats-integration/src/main/scala/hearth/kindlings/catsintegration/internal/compiletime/IsEitherProviderForValidated.scala).
- Value types: [Refined](https://github.com/kubuszok/kindlings/blob/0.4.0/refined-integration/src/main/scala/hearth/kindlings/refinedintegration/internal/compiletime/IsValueTypeProviderForRefined.scala), [Iron](https://github.com/kubuszok/kindlings/blob/0.4.0/iron-integration/src/main/scala/hearth/kindlings/ironintegration/internal/compiletime/IsValueTypeProviderForIron.scala), [neotype](https://github.com/kubuszok/kindlings/blob/0.4.0/neotype-integration/src/main/scala/hearth/kindlings/neotypeintegration/internal/compiletime/IsValueTypeProviderForNeotype.scala).
- Hearth built-ins: [hearth/std/extensions](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scala/hearth/std/extensions), [JVM-only](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scalajvm/hearth/std/extensions), [Scala 3-only](https://github.com/kubuszok/hearth/tree/0.4.5/hearth/src/main/scala-3/hearth/std/extensions).
