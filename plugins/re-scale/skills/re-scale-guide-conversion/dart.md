# Dart to Scala 3

`re-scale enforce compare` understands `.dart` sources, so method parity can
be checked the same way as for Java.

## Types

| Dart | Scala 3 |
|---|---|
| `int` | `Int`, or `Long` where values exceed 32 bits (Dart VM ints are 64-bit) |
| `double` / `num` | `Double` (or a union where `num` really mixes) |
| `bool` / `String` | `Boolean` / `String` |
| `dynamic` / `Object` | `Any` / `AnyRef` |
| `void` / `Never` | `Unit` / `Nothing` |
| `final x = ...` / `const x = ...` | `val x = ...` (`final val` for constants) |
| `late var x` / `late final x` | `var x = uninitialized` / `lazy val x` |

## Null safety

`T?` -> `Nullable[T]`; `x!` -> `get`/`nn`; `x?.m()` -> `x.map(_.m())`;
`x ?? d` -> `x.getOrElse(d)`; `x ??= v` -> `if (x.isEmpty) x = Nullable(v)`.
See `re-scale-guide-nullable`.

## Classes

| Dart | Scala 3 |
|---|---|
| `class A extends B with M` | same |
| `mixin M on B` | `trait M { self: B => }` |
| `sealed class` | `sealed trait` / `sealed abstract class` |
| `extension type` | opaque type |
| `factory A.named()` | companion `def named()` (or `apply`) |
| `A._()` private constructor | `private` constructor |
| `static` members | companion object |
| `_name` (library-private) | `private[pkg]` - Dart privacy is per library (file), not per class |
| `@visibleForTesting` | `private[pkg]` |

## Collections

`List<T>` -> `ArrayBuffer[T]` when mutated, else `List`/`IndexedSeq`;
`Map<K,V>` -> `mutable.LinkedHashMap[K,V]` (Dart map literals keep insertion
order); `Set<T>` -> `mutable.LinkedHashSet[T]` (same reason).
`add` -> `+=`, `removeAt(i)` -> `remove(i)`, `where` -> `filter`,
`firstWhere` -> `find` (Dart throws when nothing matches unless `orElse` is
given), `expand` -> `flatMap`, `fold(init, f)` -> `foldLeft(init)(f)`.

## Async and generators

`Future<T>` -> `scala.concurrent.Future[T]`; `Completer` -> `Promise`;
`Stream<T>` -> `Iterator`/`LazyList`; `sync*` generator with `yield` /
`yield*` -> `Iterator` built with `++`/`flatMap`. Keep laziness where the
original relies on it.

## Other

- `switch` / `if (x case P())` -> `match`; `is T` / `as T` ->
  `case _: T` / `asInstanceOf[T]`.
- `'$v ${e}'` -> `s"$v ${e}"`; `'''...'''` -> `"""..."""`.
- `enum C { a(1); final int v; const C(this.v); }` ->
  `enum C(val v: Int) { case A extends C(1) }`.
- Cascades `a..x()..y()` -> a block with a `val` and two calls, returning the `val`.
