# Surface phases and their `.conf` keys (engine master `ab8e129d`)

Names and keys are read off the engine's built-in factories
([`BuiltinFactories.scala`](https://github.com/kubuszok/balticporter/blob/master/balticporter/engine/src/main/scala/balticporter/runner/BuiltinFactories.scala)).
Behaviour and examples:
[Customizing the translation](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/customizing-translation.md).
A key not listed is not read, and an unread key fails the load. "scope" means the shared
`scope { except = [...] }` / `scope { only = [...] }` grammar.

| `transform` | keys | what it does |
|---|---|---|
| `collections` | `scope`, `retarget`, `retargetRewrites`, `retargetTypeArgs`, `reifiedCarriers`, `reflectiveSinks` | retype JDK (or nominated library) collections and rewrite their call sites. `retarget` maps a source type to a Scala target usable wherever the source was; `retargetRewrites` maps member calls (see below); `retargetTypeArgs` handles an arity-changing retarget; `reifiedCarriers` / `reflectiveSinks` name types whose type arguments a third party reads back at run time (Jackson, Gson), bridged at the use instead of retyped |
| `type-redirect` | `redirects { "a.B" = "c.D" }` or `"a.B" = { to, memberRenames { m = "n" }, scope }` | re-point every reference to one type at another, renaming members across their whole override family. A scoped entry retypes only declarations inside the scope; calls on a moved receiver bind to the TARGET's member (declare a parenless target member in `manifest.externalParenless`) |
| `call-site-substitution` | `calls { "a.B#m(int)" = "<template>" }`, `scoped = [ { call, template, scope } ]` | replace one resolved call with a template using `{recv}`, `{this}` (the enclosing named class's instance, `Outer.this` inside an anonymous class; refused in a static member), `{arg0}` …; literal braces are `{{` / `}}`. The most specific scope wins per call; an equal-specificity tie is refused |
| `method-body` | `bodies { "a.B#m()" = "{ … }" }`, `group` | keep the signature, replace the body verbatim. `group` names a second instance placed elsewhere in the pipeline |
| `add-members` | `fromReference { "<upstream owner>" = "name, name" }`, `members = [ { owner, specs = [ { name, arity, source, why } ] } ]` | append hand-written Scala members (verbatim `source`) to a generated class. Adds declarations, so the default scope is nowhere |
| `member-rename` | `renames { "a.B#close" = "closeWindow" }`, `derive` | rename a member across its whole override family; a key ending in `:field` names only the field |
| `static-forwarder` | `forwarders = [ { wrapper, receiver, members = [...] } ]` | treat a wrapper type's statics as another type's companion members; an entry with no `members` is refused |
| `class-table` | `scope`, `redirects { "a.B#forName" = "c.D#classFor" }`, `tables = [ { object, seeds, lookup, construct, missing { throw, notFound, notInstantiable } } ]` | re-point a reflective `Class.forName`-shaped lookup at an explicit table; with `tables` the engine writes the table from the seed class names |
| `registry` | `scope`, `entries = [ { callee, placement { object \| member, table, register, create }, scope, seeds, handles, miss, bound } ]`, `facadeMembers` | reflective instantiation → a `Class`-keyed registry minted at the placement. `miss` is `"null"`, `"jvm-reflect"`, `{ throw, message }` or `{ delegate }`. Adds declarations, default scope nowhere |
| `type-class-params` | `rules = [ { members, typeClass, create, instantiators, handles, spelling, classValue } ]` | a `Class<T>` parameter used only to construct a `T` becomes a context parameter on YOUR type class; every construction becomes a call on it, so no reflection runs on any platform. `spelling`: `type-argument` (default) or `keep-parameter`; `classValue`: `refuse` (default), `class-tag`, `member:<name>`. The whole override family converts or none. Remove any `registry` entry over the same callee |
| `class-tag-params` | `members = [...]`, `derive` | a `Class<T>` parameter becomes a `ClassTag[T]` context clause |
| `type-class-array` | `scope`, `subjects`, `witness`, `create`, `copyOf`, `copyOfRange`, `nullOut`, `nullOutRange`, `members`, `dropBound` | gives an array whose element type is a type parameter a witness to allocate, copy and clear through |
| `bean-properties` | `scope`, `pairs { "a.B#width" = "getWidth/setWidth" }`, `accessors`, `target`, `derive` | a getter/setter pair → a Scala property |
| `public-field-accessors` | `scope` | add `getX` / `setX` beside a public field for a reflective framework that needs them |
| `nullary-arity` | `scope` (default: nowhere), `force = [...]`, `derive` | drop `()` from getter-like nullary methods over the whole override family |
| `visibility` | `widen = [...]`, `narrow = [...]`, `derive`, `deriveNarrow` | ship listed members public, or a java `protected` member as Scala's subclass-only `protected` (refused where a non-subclass references it) |
| `nullability` | `scope`, `annotations = [...]`, `target` (`union` default, `named`, `option`), `wrapper` (required only for `named`), `nullableMembers = [...]`, `derive` | move a nullability annotation, or an explicitly listed member, into the type |
| `primitive-to-opaque` | `scope`, `fqn` (required), `underlying` (default `Int`), `hints`, `extraHints`, `carriers`, `derive`, `target` (`mint` default or `own-class`), `wrapName`, `unwrapName` | retype a primitive used as a distinct concept into an opaque type; `own-class` turns a Java constants class into the type itself |
| `globals-to-implicits` | `scope`, `holders = [ { holder, context { inject \| mint }, members, attach, reader, boundary, sites, selfSupplied, retain, cache, through, capture, requiredGivens, promoteToClass, attachClass, attachMethod } ]` | thread global mutable state through a context parameter. Read the scaladoc of [`GlobalsToImplicitsTransform`](https://github.com/kubuszok/balticporter/blob/master/balticporter/engine/src/main/scala/balticporter/transform/GlobalsToImplicitsTransform.scala) before using it |
| `thread-confined-statics` | `fields = [...]` | a `static final` scratch field → a companion method backed by a `ThreadLocal` |
| `class-to-trait` | `specs { "a.Pool" { params = [ { index, name } ] } }` | rewrite a nominated abstract class into a trait; usually paired with dropping the class and injecting the hand-written trait |
| `port-map-migration` | `bases = [...]` (required) | in a dependent: re-points references to a base's renamed types and members at the base's emitted names (read from the base's published `port-map.tsv`) and reports calls to members the base dropped |
| `remediation` | `classTables { "a.B#forName" = "c.D#classFor" }` | the menu of remedies for portability findings; which remedy applies at which location is chosen in `manifest.resolutions` |
| `discriminated-union` | `mutableFields` | a literal-discriminated union of object types → a sealed trait with case classes (non-Java frontends) |
| `defnode-normalization` | `class-builder { function, class-prefix, root-class }` | normalises runtime class-building conventions (non-Java frontends) |
| `test-framework` | `suite` (default `munit.FunSuite`), `testMember` (default `test`) | JUnit test classes → MUnit suites, structurally (`@Before`, expected exceptions, `@RunWith(Parameterized.class)`) |
| `mutable-params` | — | a reassigned parameter gets a local `var`; no policy |
| `panama-ffi` | — | Java foreign-function bindings; no policy |

## `collections` call-site rewrites

`retargetRewrites { "<source type>" { "<member>/<arity>" = … } }`. A member overloaded at one arity
needs a descriptor key `"name/(T1,T2)"` with types in the UPSTREAM namespace
(`"<init>/(int)"`, `"add/(float,float,float,float)"`); a descriptor key wins over an arity key.

| shape | `.conf` value |
|---|---|
| rename | a plain string: `"get/1" = "apply"` |
| boolean dispatch | `{ boolDispatch = <argIndex>, onTrue = "…", onFalse = "…" }` |
| construct | `{ companion = "…", factory = "…" }`, optional `dropTrailing = N`, `fillTypeArgs = true`, `typeVarEvidence` |
| for-each | `{ forEach = "…", arity = N }` |
| collect | `{ collect = "…", into = "…" }` |
| chain | `{ chain = ["m1", "m2"], parens = ["m1"], dropArgs = false }` |
| field write | `{ fieldWrite = "fieldName" }` |
| indexed field | `{ indexedField = "fieldName" }` |
| template | `{ template = "… $recv … $0 … $T0 … $Target …" }` — receiver, arguments, type arguments, the target FQN; an argument with side effects is bound to a temporary once |

```hocon
{ transform = "collections"
  retarget { "com.example.Bits" = "scala.collection.mutable.BitSet" }
  retargetRewrites {
    "com.example.Bits" {
      "get/1" = "apply"
      "set/1" = "addOne"
      "<init>/0" { companion = "scala.collection.mutable.BitSet", factory = "apply" }
    }
  }
  retargetTypeArgs { "com.example.IntMap" = ["scala.Int", "arg(0)"] }
}
```

Read the MUTABILITY of the source member before mapping it: Java's `Bits.xor` mutates `this`, Scala's
`BitSet.xor` returns a new set (use `^=` or a template). Translate inclusive/exclusive range bounds
too (`removeRange(start, end)`). Both compile and are silently wrong.
