---
name: kindlings-mock
description: >-
  Cross-platform test mocks with kindlings-mock, a ScalaMock-style API generated at compile time without reflection
  or bytecode proxies (JVM, Scala.js, Scala Native). Covers Mock.mock[T] (strict) and Mock.stub[T] (lenient),
  MockContext, MockSuite, withExpectations, the faithful (m.method _).expects(...).returning(...) / .when / .verify
  DSL from hearth.kindlings.mock.syntax, the name-keyed ctx.expecting("method", args) / ctx.when / ctx.verify DSL,
  call counts (once, twice, never, atLeastOnce, repeat), ArgMatcher (any, where, argThat, epsilon, capture),
  Capture, inSequence / inAnyOrder, Defaultable. Use when code imports hearth.kindlings.mock, when replacing
  ScalaMock (org.scalamock, MockFactory, mock[T], stub[T]) to run tests on Scala.js/Native, or on errors like "No
  implicit MockContext is in scope", "Unexpected call:", "Unsatisfied expectation(s)", "`.expects` must be applied
  to a method reference", "Cannot mock".
license: Apache-2.0
metadata:
  library: kindlings
  library-version: "0.4.0"
---

# Kindlings Mock (`kindlings-mock`)

A from-scratch mocking library with a ScalaMock-like API. `Mock.mock[A]` / `Mock.stub[A]` generate an anonymous
subclass of `A` at compile time (Hearth `AnonymousInstance`) whose abstract members forward to a small runtime
`MockContext`, so the same tests run on JVM, Scala.js and Scala Native, Scala 2.13 and 3. It does not depend on
ScalaMock.

Version: written for Kindlings 0.4.0. Check the version in the user's build (`build.sbt` / `build.mill` /
`project.scala` `//> using dep`); if it differs, prefer the docs for that version:
<https://kindlings.readthedocs.io/en/0.4.0/mock/>.

## Dependency (test scope)

```scala
libraryDependencies += "com.kubuszok" %%% "kindlings-mock" % "0.4.0" % Test
```

```scala
//> using test.dep com.kubuszok::kindlings-mock:0.4.0
```

Works with any test framework (MUnit, ScalaTest, utest, ...); failures are thrown as `MockExpectationException`.

## Imports

```scala
import hearth.kindlings.mock._        // Mock, MockContext, MockSuite, ArgMatcher, Capture, Defaultable, ...
import hearth.kindlings.mock.syntax._ // faithful DSL: (m.method _).expects / .when / .verify
```

## Strict mocks

Every call must match an expectation; unmet expectations fail at verification.

```scala
import hearth.kindlings.mock._
import hearth.kindlings.mock.syntax._

trait Greeter { def greet(name: String): String }

implicit val ctx: MockContext = new MockContext // Scala 3: given MockContext = new MockContext
val greeter = Mock.mock[Greeter]

(greeter.greet _).expects("world").returning("hello, world") // faithful ScalaMock spelling
ctx.expecting("greet", "bob").returning("hi, bob")           // name-keyed spelling, same context

greeter.greet("world")
greeter.greet("bob")
ctx.verifyExpectations() // throws MockExpectationException if any expectation is unsatisfied
```

Auto-verification instead of calling `verifyExpectations()` yourself:

```scala
ctx.withExpectations { /* create mocks, set expectations, exercise code */ } // verifies, then reset()s

class MySpec extends munit.FunSuite with MockSuite { // MockSuite provides `implicit val mockContext`
  test("adds") {
    withExpectations {
      val calc = Mock.mock[Calc]
      mockContext.expecting("add", 2, 3).returning(5)
      assertEquals(calc.add(2, 3), 5)
    }
  }
}
```

`ctx.reset()` clears expectations and recorded calls so a context can be reused.

## Expectation API (`CallHandler`)

| Kind | Methods |
|---|---|
| result | `returning(v)` / `returns(v)`, `throwing(t)` / `throws(t)`, `onCall(args => ...)` (args is `Seq[Any]`), `onCall1[A](a => ...)`, `onCall2[A, B]((a, b) => ...)` |
| count (default: exactly once) | `once()`, `twice()`, `never()`, `anyNumberOfTimes()`, `atLeastOnce()`, `atLeast(n)`, `atMost(n)`, `noMoreThanOnce()`, `noMoreThanTwice()`, `repeat(n)`, `repeat(range)` |

Without `returning`/`throwing`/`onCall` a matched call returns the return type's default (`Defaultable`, else `null`).
Several expectations for the same method/arguments are consumed in declaration order, each up to its count.

### Argument matchers

Literal expected arguments are compared with `==`. Use `ArgMatcher` for anything else:

```scala
ctx.expecting("greet", ArgMatcher.any)                           // anything, including null
ctx.expecting("greet", ArgMatcher.where[String](s => s.nonEmpty))  // predicate (alias: argThat)
ctx.expecting("greet", ArgMatcher.argThatDescribed[String]("non empty")(s => s.nonEmpty))
ctx.expecting("measure", ArgMatcher.epsilon(1.0, 0.05))          // numeric tolerance (default 0.001)
ctx.expectingSeq("pair", ArgMatcher.where2[Int, Int](_ < _))     // predicate over two args (returns Seq[ArgMatcher])
ctx.expecting("greet", ArgMatcher.from(myMatcher))               // custom Matcher[A]

val name = new Capture[String]
ctx.expecting("greet", ArgMatcher.capture(name)).returning("hi")
greeter.greet("Alice")
name.value   // "Alice" (last); name.values = all; name.hasValue
```

`ctx.expecting("m")` with **no** arguments matches any arguments of any arity.

### Ordering

Expectations match in any order by default.

```scala
ctx.inSequence {
  ctx.expecting("open").returning(())
  ctx.inAnyOrder {
    ctx.expecting("write", "a").returning(())
    ctx.expecting("write", "b").returning(())
  }
  ctx.expecting("close").returning(())
}
```

Sequences may span several mocks created with the same context.

## Lenient stubs

`Mock.stub[A]` never fails on unexpected calls: un-preset methods return a default, and you verify afterwards.

```scala
trait Calculator { def add(a: Int, b: Int): Int }

implicit val ctx: MockContext = new MockContext
val calc = Mock.stub[Calculator]

(calc.add _).when(2, 3).returning(5)   // or ctx.when("add", 2, 3).returning(5)
calc.add(2, 3)                         // 5
calc.add(9, 9)                         // 0 (Defaultable[Int])

(calc.add _).verify(2, 3).once()       // or ctx.verify("add", 2, 3).once()
(calc.add _).verify(1, 1).never()      // VerifyTarget: once, twice, never, wasCalled(n), atLeastOnce, atLeast(n), atMost(n)
ctx.verifyInSequence("add" -> Seq(2, 3), "add" -> Seq(9, 9))
```

Defaults come from `Defaultable[A]`: `0`/`false`/`' '`/`""`/`()`, `None`, empty `List`/`Vector`/`Seq`/`Set`/`Map`;
any other type gets `null`. Provide your own: `implicit val d: Defaultable[Money] = Defaultable.of(Money.zero)`.

## What can be mocked

Traits and (non-final) classes; abstract `def`s and abstract `lazy val`s are mocked, concrete members are kept as-is.
Abstract (eager) `val`s are overridden with their `Defaultable` default in both `mock` and `stub`, not mocked (after
0.4.0; in 0.4.0 a strict mock threw `Unexpected call` while being constructed).
Supported shapes include overloads, curried parameter lists (args are flattened: `ctx.expecting("curried", 10, 1.5)`),
varargs (arrive as one `Seq`), by-name params, implicit/using params (packed like normal args), polymorphic methods,
`this.type` returns, symbolic names, parameterized traits applied at the use site, and on Scala 3 union/intersection,
opaque and context-function types. Mocking a **class** runs its real constructor with default/`null` arguments.

## Differences from ScalaMock

- Pure compile-time code generation: no `java.lang.reflect.Proxy`/bytecode, so it works on Scala.js and Scala Native.
- An extra **name-keyed** DSL (`ctx.expecting("m", ...)`, `ctx.when`, `ctx.verify`) usable without call-site macros.
- The mock factory is an explicit `MockContext` (implicit) rather than `MockFactory`; `MockSuite` +
  `withExpectations` replace ScalaMock's automatic per-test verification.
- `ArgMatcher.any` instead of ScalaMock's `*` wildcard; `ArgMatcher.epsilon` instead of `~`; ordering via
  `ctx.inSequence`/`ctx.inAnyOrder`.
- Not ported: `mockFunction`/`stubFunction` (use `Mock.mock[A => B]`), the call log, the new `stubs` API, the ZIO /
  cats-effect integrations, Java proxy mocks.
- Members typed with an inner type of the mocked trait are not supported (Hearth limitation).
- Only abstract members are mocked; concrete members keep their implementation (ScalaMock mocks them too).
- Results are untyped (`returning(value: Any)`): a wrong-typed value compiles and fails at the call with a
  `ClassCastException`.

## Debugging

`import hearth.kindlings.mock.debug._` in the test file, or `-Xmacro-settings:mock.logGeneration=true`, prints the
overridden members and the generated mock at compile time. No derivation timeout or derivation policy applies. For
general macro troubleshooting see the `kindlings-troubleshooting` skill.

## Gotchas

- **`No implicit MockContext is in scope for .expects`** - the faithful DSL needs an implicit `MockContext` (the one
  the mock was created with). Declare `implicit val ctx: MockContext` / `given MockContext`, or mix in `MockSuite`.
- **Test passes although a mocked method was never called** - nothing verifies automatically. Call
  `ctx.verifyExpectations()`, or wrap the test in `withExpectations { ... }`.
- **Expectations leak between tests with `MockSuite`** - it holds one `mockContext` per suite instance; frameworks such
  as MUnit reuse that instance for every test. Always use `withExpectations` (it resets) or call `mockContext.reset()`.
- **`MockExpectationException: Unexpected call: m(args)`** - a strict mock got a call that matched no expectation (wrong
  args, count exhausted, or out of `inSequence` order). The message lists the expected calls. Use `Mock.stub` if
  lenient behaviour is wanted.
- **Typos in name-keyed expectations** - `ctx.expecting("gret", ...)` is not checked at compile time; it shows up as an
  unexpected call plus an unsatisfied expectation. Prefer `(m.greet _).expects(...)`.
- **Overloads in the faithful DSL** - `(m.foo _)` is ambiguous; write the shape explicitly: `(m.foo(_: Int)).expects(...)`
  or `(m.foo(_: Int, _: Int)).expects(...)` (the reference's arity selects the overload).
- **`` `.expects` must be applied to a method reference of the form `(m.method _)` ``** - pass an eta-expanded method,
  not a value.
- **Stub returns `null` for a custom type** - add an implicit `Defaultable[YourType]`.
- **`Cannot mock X: ...`** - Hearth could not build an anonymous subclass of `X` (the reason follows the colon, e.g. a
  final class). Mock a trait/interface instead.
- **A concrete method is not intercepted** - only *abstract* members are overridden; concrete `def`s/`val`s (also on
  classes) keep their real implementation, unlike ScalaMock which overrides every method. Mock a trait that declares
  the method abstract.
- **Side effects or NPEs when mocking a class** - the real constructor runs with dummy arguments; extract a trait.
- **Value-discard / non-unit-statement warnings** on `(... ).expects(...).returning(...)` lines under `-Werror`: the
  expression returns a `CallHandler`; write `val _ = ...` as the official examples do.

## Links

- Guide: <https://kindlings.readthedocs.io/en/0.4.0/mock/>
- Debugging: <https://kindlings.readthedocs.io/en/0.4.0/debugging/>
- Source: <https://github.com/kubuszok/kindlings/tree/0.4.0/mock>
