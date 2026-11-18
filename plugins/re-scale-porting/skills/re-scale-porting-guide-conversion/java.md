# Java to Scala 3: step by step

Generic steps; the project's type-mapping doc replaces the collection and
exception rows with its own choices.

1. **File setup.** License header (see `re-scale-porting-guide-code-style`), split
   package clauses, file in the module the project's path mapping names.
2. **Class structure.**
   `class Foo extends Bar implements Baz` -> `class Foo extends Bar with Baz`;
   `interface` -> `trait`; `abstract class` stays; `final class` stays;
   `enum` -> Scala 3 `enum` (`extends java.lang.Enum[E]` when Java parity matters).
3. **Statics.** Static methods, fields and nested static classes move to the
   companion object (create it). Nested types declared in an interface move to
   the trait's companion.
4. **Access.** Drop `public`. `private`/`protected` stay. Package-private ->
   `private[pkg]`. Java `protected` also grants package access; use
   `protected[pkg]` when same-package callers rely on it.
5. **Fields.** No-logic getter/setter pair -> `var x`; getter only on a final
   field -> `val x`; with logic -> `def x` + `def x_=(v)`. Uninitialised `var`
   -> `= scala.compiletime.uninitialized`. `final` field -> `final val` (Java
   fields are hidden, not overridden).
6. **Primitive types.** `int`/`Integer` -> `Int`, `long` -> `Long`,
   `boolean` -> `Boolean`, `double` -> `Double`, `float` -> `Float`, `byte` ->
   `Byte`, `short` -> `Short`, `char` -> `Char`, `void` -> `Unit`,
   `Object` -> `AnyRef` (or `Any`), `T[]` -> `Array[T]`. A boxed type that can
   be null -> `Nullable[...]`.
7. **Collections** (unless the project maps them elsewhere):
   `ArrayList`/`List` -> `mutable.ArrayBuffer`/`mutable.Buffer`;
   `HashMap`/`Map` -> `mutable.HashMap`/`mutable.Map`; `LinkedHashMap` ->
   `mutable.LinkedHashMap`; `HashSet`/`Set` -> `mutable.HashSet`/`mutable.Set`;
   `Iterator` -> `Iterator`; `Collections.emptyList()` -> `Nil`/`List.empty`.
   Keep mutability: if Java mutates it, the Scala type must be mutable.
8. **Null.** `@Nullable` parameters/returns and `== null` checks -> see
   `re-scale-porting-guide-nullable`.
9. **Control flow.** `return`/`break`/`continue`/`switch` -> see
   `re-scale-porting-guide-control-flow`. `for (int i = 0; i < n; i++)` ->
   `for (i <- 0 until n)` or a `while` with an index in hot code;
   `for (T x : xs)` -> `for (x <- xs)`.
10. **Generics.** `<T extends Foo>` -> `[T <: Foo]`; `<? super T>` -> `[? >: T]`;
    `<?>` -> `[?]`; `<T extends A & B>` -> `[T <: A & B]`.
11. **Exceptions.** Drop `throws`. Keep exception types and messages; custom
    exceptions extend the same JDK base class.
12. **Anonymous classes and lambdas.** `new I() { ... }` -> `new I { ... }`, or
    a lambda when `I` is a single-abstract-method type; `(x) -> e` -> `x => e`.
13. **Strings.** `+` concatenation may become `s"..."`; `String.format` with
    flags -> `f"..."` or keep `String.format`.
14. **Annotations.** `@Override` -> `override`; `@Deprecated` ->
    `@deprecated("reason", "since")`; `@SuppressWarnings` -> targeted `@nowarn`.
15. **Inner classes.** Non-static inner classes become nested classes (they
    capture the outer instance just like Java's).
16. **Comparison.** `instanceof` -> pattern match or `isInstanceOf`;
    `Comparable<T>` -> `Ordered[T]` or a `given Ordering[T]`;
    `Comparator<T>` -> `Ordering[T]`.
17. **Concurrency.** `synchronized (x) { }` -> `x.synchronized { }`;
    `volatile` -> `@volatile`.
18. **Final review.** No `public`, `static`, `implements`, raw `null`,
    `return`; every original member present; comments preserved;
    `re-scale enforce shortcuts --file` clean.
