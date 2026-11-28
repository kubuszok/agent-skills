# `Method` and `Parameter` API reference (Hearth 0.4.5)

Verified against [Methods.scala](https://github.com/kubuszok/hearth/blob/0.4.5/hearth/src/main/scala/hearth/typed/Methods.scala)
and compile-checked (Scala 3.3.7, 2.13.16). How to *call* a method (`fold`, `foldF`, the builder chain) is shown in
`hearth-case-classes-and-enums`; argument maps are `Map[String, Expr_??]` keyed by parameter name.

## Obtaining

| Companion | Extension | Result | Notes |
|---|---|---|---|
| `Method.primaryConstructorOf[A]` | `Type[A].primaryConstructor` | `Option[Method]` | |
| - | `Type[A].defaultConstructor` | `Option[Method]` | the nullary constructor |
| `Method.constructorsOf[A]` | `Type[A].constructors` | `List[Method]` | |
| `Method.methodsOf[A]` | `Type[A].methods` | `List[Method]` | declared, inherited, synthetic; stable order; sorting is expensive |
| `Method.unsortedMethodsOf[A]` | `Type[A].unsortedMethods` | `List[Method]` | unspecified order |
| `Method.unsortedMethodsNamed[A](n)` | `Type[A].unsortedMethodsNamed(n)` | `List[Method]` | only overloads named `n`; cheapest |
| `Method.sort(ms)` / `Method.sortBy(xs)(toMethod)` | | | `sort(xs.filter(p)) == sort(xs).filter(p)` |
| | `Class[A].method(n)` | `List[Method]` | overloads named `n`, stable order |

Listings are memoized per type within an expansion.

## Shape of the call

| Member | Type | Meaning |
|---|---|---|
| `expectations` | `List[MethodExpectation]` | `NeedsInstance`, `NeedsTypes(typeParameters)`, `NeedsValues(parameters)` per step |
| `totalParameters` | `List[ListMap[String, Parameter]]` | all value parameters, grouped by source clause; unchanged along the chain |
| `parameters` | same | parameters the current `ApplyValues` step expects (empty on other steps) |
| `knownReturning` | `Option[??]` | `None` before type arguments are applied, or when the member's type is still being inferred |
| `arity`, `isNullary`, `isUnary`, `isBinary`, `isNAry(n)` | | count of all value parameters |
| `Instance` | `Type[Instance]` | receiver type |

Step merging rules: consecutive value lists form one `NeedsValues`; an `implicit`/`using` list is always its own step;
a list whose types mention an earlier parameter (`(b: Box)(t: b.T)`) starts a new step; Scala 3 interleaved type
clauses add steps. Keep applying while the next step is `ApplyValues`.

A Scala 3 extension method (`extension (v: Vec) def copy(x: Double = v.x)`, listed among `Type[Vec].methods` when
it is in the companion) takes its receiver as its first parameter list: `def copy(v: Vec)(x: Double = <default>)`.
Pass the receiver as an argument (`"v" -> vec`) like any other parameter; defaults reading it get it.

Chain classes: `Method.OnInstance` (`apply(instance)`, `applyUntyped`), `Method.ApplyTypes` (`apply(typeArgs)`),
`Method.ApplyValues` (`apply(arguments)`), `Method.Result[R]` (`build(): Either[String, Expr[R]]`). Constructors and
static/object methods start without `OnInstance`.

## Predicates

| Group | Members |
|---|---|
| Kind | `isConstructor`, `isVal` (also stable abstract accessors and inherited constructor vals), `isVar`, `isLazy`, `isDef`, `isImplicit` |
| Origin | `isDeclared`, `isInherited`, `isSynthetic`, `isCaseField` (not for singletons), `isConstructorArgument` |
| Modifiers | `isFinal`, `isAbstract`, `isOverride` (`Object` members: `true` on Scala 2, `false` on Scala 3) |
| Visibility | `isPrivate` / `isProtected` (unqualified only), `privateWithin` / `protectedWithin` (`Some("pkg")` for `private[pkg]`), `isAvailable(Everywhere \| AtCallSite \| Anywhere)` |
| Annotations | `annotations: List[Expr_??]`, `annotationsOfType[Ann]: List[Expr[Ann]]`, `hasAnnotationOfType[Ann]` (`<:<` matching) |

## Accessors

| Member | `true` for | Name |
|---|---|---|
| `isScalaGetter` | `val` / `var` / `lazy val` (not the setter) | `scalaAccessorName` = member name |
| `isScalaSetter` | unary `x_=` (its parameter is named `x$1`) | `scalaAccessorName` = name without `_=` |
| `isJavaGetter` | instance nullary `getX` (`X` upper-case) returning non-`Unit`, or `isX` returning `Boolean`; includes `getClass` | `javaAccessorName` = `x` (decapitalized) |
| `isJavaSetter` | instance unary `setX` returning `Unit` | `javaAccessorName` |
| `isScalaAccessor`, `isJavaAccessor`, `isAccessor` | unions | `accessorName` = Scala name, else Java name |

## `Parameter`

| Member | Type | Notes |
|---|---|---|
| `name`, `index`, `position` | `String`, `Int`, `Option[Position]` | |
| `tpe` | `??` | by-name: `` scala.`<byname>`[T] `` on Scala 2, `=> T` on Scala 3; vararg: `scala.collection.immutable.Seq[A]` |
| `byNameUnderlying` | `Option[??]` | `T` of `=> T`, same on both versions |
| `isByName`, `isVararg`, `isImplicit` | `Boolean` | pass an `Expr[Seq[A]]` for a vararg parameter |
| `hasDefault`, `defaultValue` | `Boolean`, `Option[Method]` | the default getter as a builder chain |
| `annotations`, `annotationsOfType[Ann]`, `hasAnnotationOfType[Ann]` | | |
| `asUntyped` | `UntypedParameter` | |

## Rendering

`method.plainPrint` / `prettyPrint` (ANSI) render the signature with the instance type:
`demo.Api: def poly[T](t: T): scala.collection.immutable.List[T]`, `demo.Api: var w_=(x$1: scala.Int): scala.Unit`,
constructors as `new demo.Foo(a: scala.Int, b: java.lang.String = <default>)`. `toString` appends what has been
applied (`(on instance, applied (a = 42), returning ...)`). Path-dependent types print differently
(`demo.Box#T` on Scala 2, `b.T` on Scala 3) - do not compare signatures across versions.
