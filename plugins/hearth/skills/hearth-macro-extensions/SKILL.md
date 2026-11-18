---
name: hearth-macro-extensions
description: >-
  Hearth macro extensions (plugin SPI) for Scala 2.13 / Scala 3 macro authors - hearth.MacroExtension, defining your
  own extension point (an abstract extension class your macro loads), Environment.loadMacroExtensions[E],
  loadMacroExtensionsExcluding, loadMacroExtensionsWhen, ExtensionLoadingResult (AllLoaded / SomeFailed /
  LoaderFailed, fold, toEither, toMIO(allowFailures)), reporting extension failures, META-INF/services registration via
  java.util.ServiceLoader, priority, load-once-per-expansion ("Extension ... was already loaded in this macro
  expansion"), the ClassTag-of-intersection pitfall, StandardMacroExtension and loadStandardExtensions, compile
  classpath requirements (separate compilation unit, Provided scope, Scala.js / Native) and testing. Use when a macro
  should be extensible by jars on the classpath, when an extension is never picked up, or when "The outer reference
  in this type test cannot be checked at run time" appears when matching ExtensionLoadingResult.
license: Apache-2.0
metadata:
  library: hearth
  library-version: "0.4.5"
---

# Hearth macro extensions

How to make your own Hearth-based macro pluggable: other jars on the compile classpath contribute code that your macro
loads during expansion through `java.util.ServiceLoader`. Writing a provider for the built-in `IsCollection` /
`IsOption` / `IsEither` / `IsMap` / `IsValueType` shapes is covered by the `hearth-standard-extensions` skill (its
`writing-providers.md`); this skill covers the mechanism underneath and defining **your own** extension point.

**Version.** Written for Hearth 0.4.5. Check the version in the user's build (build.sbt / build.mill / project.scala
`//> using dep`); if it differs, prefer the docs for that version:
https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#macro-extensions (replace `0.4.5`).

## Which mechanism

| You want to... | Use |
|---|---|
| Teach every Hearth-based macro about a collection, map, option, either or wrapper type | a `StandardMacroExtension` provider: `hearth-standard-extensions` skill |
| Let other jars plug things into *your* macro (naming hints, extra rules, config discovery, N inner types, recursion) | your own `MacroExtension` subclass, as below |
| Use the built-in shapes from your macro | call `Environment.loadStandardExtensions()`: `hearth-standard-extensions` skill |

The `Is*` shapes are fixed-arity (one inner type, or two for `IsMap`/`IsEither`). Anything else needs your own
extension point.

## The pieces

```scala
abstract class MacroExtension[Macro: ClassTag] extends PartialFunction[Any, Unit] {
  def priority: Int = 0            // higher = applied first; same priority keeps ServiceLoader discovery order
  def extend(ctx: Macro): Unit     // mutate the macro context (register something in it)
}
```

- `isDefinedAt(ctx)` checks `classTag[Macro].runtimeClass.isAssignableFrom(ctx.getClass)`. `ctx` is the macro
  bundle instance (your `MacroCommonsScala2` / `MacroCommonsScala3` subclass).
- `extend` returns `Unit`. An extension can only contribute by calling something on `ctx`, usually a registry that
  your macro owns.
- Extensions are found with `ServiceLoader` from the class loader that loaded the macro bundle. Each implementation is
  listed in `META-INF/services/<fully qualified name of the extension point>`, one class name per line, and needs a
  public no-arg constructor.
- The instance is created once and **cached per compiler class loader**, so the same object serves every expansion.
  Do not keep `Type`/`Expr`/per-expansion state in fields of the extension class. Create it inside `extend` (or in
  objects created there).

## Defining your own extension point (verified on 2.13.18 and 3.8.3)

Shared macro logic. The trait **extends** `MacroCommons` instead of using a self-type, so extensions that receive it as
a value can `import ctx.*` and use `Type`, `Expr`, `Environment`...:

```scala
package describe

import hearth.{MacroCommons, MacroExtension}
import hearth.std.StdExtensions

trait DescribeMacro extends MacroCommons with StdExtensions {

  trait Describer { def describe[A: Type]: Option[String] }      // what an extension contributes

  private val describers = scala.collection.mutable.ListBuffer.empty[Describer]
  final def registerDescriber(describer: Describer): Unit = describers += describer

  private var extensionsLoaded = false
  private def loadExtensionsOnce(): Unit = if (!extensionsLoaded) {
    extensionsLoaded = true
    // fold instead of `match`: matching these path-dependent case classes warns on Scala 2
    Environment.loadMacroExtensions[DescribeExtension].fold(_ => ()) { (_, errors) =>
      val details = errors.toNonEmptyVector.toVector.map { case (ext, error) =>
        s"  - ${ext.getClass.getName}: ${error.getMessage}"
      }
      Environment.reportErrorAndAbort(("Failed to load describe extensions:" +: details).mkString("\n"))
    } { error =>
      Environment.reportErrorAndAbort(s"Cannot load describe extensions: ${error.getMessage}")
    }
  }

  def deriveDescription[A: Type]: Expr[String] = {
    loadExtensionsOnce()
    val found = describers.iterator.flatMap(_.describe[A].iterator).nextOption()
    Expr(found.getOrElse(s"${Type[A].plainPrint} (no describer)"))
  }
}

/** The extension point. Implementations go to META-INF/services/describe.DescribeExtension */
abstract class DescribeExtension extends MacroExtension[DescribeMacro]
```

Platform adapters, as for any cross-compiled Hearth macro (see `hearth-getting-started`):

```scala
// Scala 2 (compile with -Xsource:3)
import scala.language.experimental.macros
class DescribeMacros(val c: scala.reflect.macros.blackbox.Context) extends hearth.MacroCommonsScala2 with DescribeMacro {
  def describeImpl[A: c.WeakTypeTag]: c.Expr[String] = deriveDescription[A]
}
object Describe { def describe[A]: String = macro DescribeMacros.describeImpl[A] }

// Scala 3
import scala.quoted.*
class DescribeMacros(q: Quotes) extends hearth.MacroCommonsScala3(using q), DescribeMacro
object DescribeMacros {
  def describeImpl[A: Type](using q: Quotes): Expr[String] = new DescribeMacros(q).deriveDescription[A]
}
object Describe { inline def describe[A]: String = ${ DescribeMacros.describeImpl[A] } }
```

An extension, in **another** jar:

```scala
package describe.uuid

final class UuidDescriber extends describe.DescribeExtension {
  override def extend(ctx: describe.DescribeMacro): Unit = {
    import ctx.*
    registerDescriber(new Describer {
      private lazy val Uuid = Type.of[java.util.UUID]     // created per expansion, not cached in the extension
      def describe[A: Type]: Option[String] = if (Type[A] =:= Uuid) Some("a UUID (36 characters)") else None
    })
  }
}
```

```
# src/main/resources/META-INF/services/describe.DescribeExtension
describe.uuid.UuidDescriber
```

With that jar on the classpath `Describe.describe[java.util.UUID]` returns `"a UUID (36 characters)"`, without it
`"java.util.UUID (no describer)"`. An extension that throws in `extend` aborts the expansion with
`Failed to load describe extensions:\n  - describe.broken.BrokenDescriber: boom`.

Build of the extension jar: depends on the jar with the extension point (which brings `hearth`); on Scala 3 add the
`hearth-cross-quotes` compiler plugin if it uses `Type.of`/`Expr.quote`, on Scala 2 `-Xsource:3`.

If your macro trait must keep a self-type (`this: MacroCommons & StdExtensions =>`), use the pattern of Hearth's
`StandardMacroExtension` and Kindlings' `JsonSchemaConfigExtension`: extend `MacroExtension[MacroCommons &
StdExtensions]` and narrow inside `extend` with `ctx match { case _: MyMacro => ...; case _ => () }`.

## Loading

All are methods of `Environment` (available in `MacroCommons`) and need a `ClassTag` of the extension point:

| Call | Loads |
|---|---|
| `loadMacroExtensions[E]` | every implementation of `E` |
| `loadMacroExtensionsExcluding[E]("com.x.Foo", ...)` | all but the listed fully-qualified class names |
| `loadMacroExtensionsWhen[E](clazz => ...)` | those whose `java.lang.Class[?]` satisfies the predicate |

Each sorts by `priority` (descending), calls `extend(ctx)` on every implementation that applies to this bundle, and
returns `ExtensionLoadingResult[E]`:

| Case | Meaning |
|---|---|
| `AllLoaded(loadedExtensions)` | every `extend` succeeded (also when none were found: empty `ListSet`) |
| `SomeFailed(loadedExtensions, errors)` | some `extend` threw, or the bundle is not an instance of the extension's `Macro` type; `errors: NonEmptyMap[E, Throwable]` |
| `LoaderFailed(error)` | `ServiceLoader` itself failed, or no implementation could be instantiated at all |

Helpers: `fold(allLoaded)(someFailed)(loaderFailed)`, `toEither: Either[NonEmptyVector[Throwable], ListSet[E]]`,
`toOption`, `hasFailures`, `loadedExtensions`. In an `MIO` program:
`Environment.loadMacroExtensions[E].toMIO(allowFailures = false)` logs the loaded class names (`<E> - Successfully
loaded N extensions:`) into the derivation log and fails the `MIO` with the errors (with `allowFailures = true` it logs
them and continues).

An implementation that cannot even be instantiated (class missing, constructor throws, incompatible TASTy) is skipped
silently when others load, so one broken jar does not break every expansion. If nothing could be instantiated you
get `LoaderFailed` with the first cause.

Always handle `SomeFailed` and `LoaderFailed` (abort with `reportErrorAndAbort`, or log and continue on purpose).
Ignoring the result hides a broken extension.

## Load once per expansion

Hearth remembers which extension objects were applied to the current bundle instance and does not apply them twice.
A second call still scans the classpath and reports
`Extension ... was already loaded in this macro expansion, skipping re-initialization` as an info message for each
extension. A macro gets one info message per position, so that message can take the slot and hide the rendered
derivation log you wanted to see. Load at a
single entry point, or guard with a `private var loaded = false` in the bundle/trait (as above), when several entry
points share one bundle (e.g. a codec deriving an encoder and a decoder). `extend` should still be idempotent and
must not depend on other extensions' order. Use `priority` when the order really matters.

## Standard extensions are the same mechanism

```scala
trait StandardMacroExtension extends MacroExtension[MacroCommons & StdExtensions]
def loadStandardExtensions(): ExtensionLoadingResult[StandardMacroExtension] =
  environment.loadMacroExtensions[StandardMacroExtension]                     // META-INF/services/hearth.std.StandardMacroExtension
```

Loading your own extension point does **not** load the standard ones, and the other way round: a macro that uses
both calls both (each once). One jar may register implementations for several extension points (one services file
per extension point). Built-in providers use priority `0` (`IsValueTypeProviderForOpaque`: `-1000`).

## Classpath requirements

- The extension must be on the **compile** classpath of the code where the macro **expands**, not of the macro
  module. In sbt add it to the module that calls the macro (`dependsOn(ext)` or `libraryDependencies`). A `% Test`
  dependency only affects test sources.
- It must be compiled in an earlier compilation unit (another module or jar). Classes compiled together with the
  macro call do not exist yet when the macro runs.
- A compile-time-only extension can be `% Provided` (scala-cli: `//> using compileOnly.dep`), so it stays off the
  runtime classpath. Anything that generated code calls at runtime must stay a normal dependency.
- Scala.js / Scala Native: macros still run in the JVM compiler, but `%%%` resolves the platform artifact. Publish the
  extension for every platform your users build for.
- Compile the extension with a Scala version not newer than the users' compiler (the usual library rule).
- Generating `META-INF/services`: Hearth and Kindlings generate it with an unpublished sbt plugin of their own. Write the
  file by hand in `src/main/resources`, or generate it in your build.

## Testing

- Put the extension point, an extension and the macro call in **three** compilation units (e.g. modules `engine`,
  `ext`, and `ext`'s tests or an `app`). sbt test sources are compiled after main sources, so a module's own tests see
  its `src/main/resources/META-INF/services` file.
- Test with the extension present, without it (fallback path), with a throwing extension (`SomeFailed` is reported),
  and that two entry points in one expansion load it once.
- Inspect what was loaded with `toMIO` logging, or by reporting `loadedExtensions.map(_.getClass.getName)` with
  `Environment.reportInfo` while debugging.

## Gotchas

- **Extension never applied, no error** -> missing or misspelled `META-INF/services/<extension point FQCN>` file
  (it must name the *extension point* class, e.g. `describe.DescribeExtension`, not `hearth.MacroExtension`), the jar
  is not on the compile classpath where the macro expands, or it is compiled in the same unit as the call site.
- **`Instance of X cannot be applied to Y` in `SomeFailed`** -> the bundle class is not an instance of the extension's
  `Macro` type (wrong `ClassTag`, see next item).
- **`MacroExtension[A & B]` checks only one type** -> the `ClassTag` of an intersection is its erasure: on Scala 2 the
  first component, on Scala 3 the one the erasure rules choose (checked with Scala 3.8.3: `MacroCommons & StdExtensions`
  -> `MacroCommons`, but `MacroCommons & MyTrait` -> `MyTrait`). Use a single trait as `Macro`, or
  `MacroCommons & StdExtensions` plus a runtime match inside `extend` (also `hearth-cross-compilation-pitfalls`,
  pitfalls.md section 19).
- **`extend(ctx: MyMacro)` cannot call `Type`/`Expr`** -> `MyMacro` declares `MacroCommons` only as a self-type, which
  is invisible from outside. Make it extend `MacroCommons` (as above) or use the intersection-plus-match pattern.
- **`The outer reference in this type test cannot be checked at run time` (Scala 2)** -> pattern matching
  `ExtensionLoadingResult.AllLoaded(...)` etc., which are path-dependent. Use `fold` / `toEither`, or silence that
  warning with `-Wconf`.
- **Stale types or state from another expansion** -> `Type`/`Expr` (or anything else per-expansion) cached in a
  field of the extension class, which is a singleton shared by all expansions. Create them inside `extend`.
- **`was already loaded` info messages instead of the derivation log, slow compilation** -> extensions loaded in
  several places of one expansion. Load once.
- **`loadMacroExtensions[E] match { case Right(()) => ... }` does not compile** -> it returns
  `ExtensionLoadingResult`, not `Either` (an older docs example shows `Either`). Use `.toEither`, `.fold`, `.toOption`
  or `.toMIO(allowFailures = ...)`.
- **Works in sbt, fails with scala-cli `--server=false`** -> in a check with scala-cli 1.19.0 a provider in the same
  project's main scope was not visible to test-scope macros without the Bloop server. Use the default server or a
  separate module/jar.

## Reference

- Docs: [Macro Extensions](https://scala-hearth.readthedocs.io/en/0.4.5/basic-utilities/#macro-extensions),
  [Standard Macro Extensions](https://scala-hearth.readthedocs.io/en/0.4.5/standard-extensions/#standard-macro-extensions).
- Sources (0.4.5): [MacroExtension.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/MacroExtension.scala),
  [Environments.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/Environments.scala)
  (`loadMacroExtensions*`, `ExtensionLoadingResult`),
  [loader.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/loader.scala),
  [MIOIntegrations.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/MIOIntegrations.scala) (`toMIO`),
  [StandardMacroExtension.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/std/StandardMacroExtension.scala).
- A real custom extension point: Kindlings 0.4.0
  [JsonSchemaConfigExtension](https://github.com/kubuszok/kindlings/blob/0.4.0/json-schema-config-macro-providers/src/main/scala/hearth/kindlings/jsonschemaconfigs/JsonSchemaConfigExtension.scala)
  with its registry [JsonSchemaConfigs](https://github.com/kubuszok/kindlings/blob/0.4.0/json-schema-config-macro-providers/src/main/scala/hearth/kindlings/jsonschemaconfigs/JsonSchemaConfigs.scala)
  (circe and jsoniter derivations register their configuration so Tapir schema derivation can read it).
- Related skills: `hearth-standard-extensions` (using `Is*` and writing providers), `hearth-cross-compilation-pitfalls`, `hearth-getting-started`
  (bundle setup), `hearth-debugging` (derivation logs).
