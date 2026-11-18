# Case study: a decoder that breaks at 88 fields

## How it happened

A decoder had to use a field's default value when the field was absent or failed to decode. The macro emitted
that logic for each defaulted field directly as a constructor argument:

```scala
new A(
  decodeF0(record.get("f0")),
  if (record.hasField("f1")) try decodeF1(record.get("f1")) catch { case NonFatal(_) => default1 } else default1,
  if (record.hasField("f2")) try decodeF2(record.get("f2")) catch { case NonFatal(_) => default2 } else default2,
  ...
)
```

It compiled, and every behavioural test passed. Then:
- from about 26 defaulted fields, the method was over 8000 B, so HotSpot never JIT-compiled it and decoding was 5x
  slower;
- at 88 fields, compilation failed with "Method too large" (64 KB), and users had no workaround.

**Why it grows quadratically.**
- When a `try` appears inside an argument list, the compiler first spills every argument already evaluated into
  locals, and then reloads them all. Field K therefore costs O(K) bytes.
- Every branch nested in an expression needs a stack-map frame that lists all live values. On Scala 2.13 this made
  the StackMapTable of a 100-field class about 1.1 MB.

**Why nobody saw it.** The behaviour tests and the differential tests against the upstream library checked results,
not bytecode. The benchmarks used 5-field types, where quadratic growth is invisible. Nothing compiled a wide type
and measured it.

## How to detect it

- **Guard test (do this).**
  - Derive instances for a 100-field fixture with defaults and `Option`s in a dedicated object, then fail if any of
    its methods exceeds 8000 B.
  - Run it on Scala 2.13 and 3, and with a compile-time config and a runtime config.
  - Keep the fixture at about 100 fields: much wider ones can run the compiler out of memory.
  - To read method sizes without a dependency, read the `.class` resource with a `DataInputStream`. Skip the
    constant pool, keeping the UTF-8 entries; tags 5 and 6 take two slots. Then, in each method, find the `Code`
    attribute. Its `code_length` is the `u4` after `max_stack` and `max_locals`.
- **By hand.**
  - Run `javap -c -p 'Outer$.class'`. The last instruction offset of a method is roughly its size.
  - Run `javap -v` to see the `StackMapTable` sizes.
  - Look in quotes for `try`, `if` or `match` inside constructor arguments, `::`, or builder calls.
- **Benchmark a wide type** next to the small ones. A throughput cliff at a given width means a method stopped being
  JIT-compiled.

## The fix

Give each field its own local `def` and bind each result with a flat statement. The macro recursion is nested; the
generated code is not:

```scala
// macro side (fail-fast); results are Either[E, Any]
def loop(fields: List[Expr[Either[E, Any]]], prev: Option[Expr[Either[E, Any]]], acc: List[Expr[Either[E, Any]]]): Expr[Either[E, A]] =
  fields match {
    case field :: rest =>
      ValDefs.createDef(field, FreshName.FromPrefix("field")).use { fieldDef =>
        val result = prev.fold(fieldDef)(p => Expr.quote(if (Expr.splice(p).isRight) Expr.splice(fieldDef) else Expr.splice(p)))
        ValDefs.createVal(result, FreshName.FromPrefix("result")).use(r => loop(rest, Some(r), r :: acc))
      }
    case Nil => // if (last.isRight) Right(new A(<each result's value>.asInstanceOf[Fi], ...)) else <last as Either[E, A]>
  }
```

Generated code:

```scala
def field0 = decodeF0(record.get("f0"))
val result0 = field0
def field1 = { val v = record.get("f1"); if (v == null) Right(default1) else try decodeF1(v) catch { case NonFatal(_) => Right(default1) } }
val result1 = if (result0.isRight) field1 else result0
...
if (resultN.isRight) Right(new A(result0.value.asInstanceOf[F0], ...)) else resultN.asInstanceOf[Either[E, A]]
```

- **Accumulating mode.** Use `val eK = Helpers.merge(eK-1, resultK)`, with `null` meaning "no failure yet", where
  `merge` is a MiMa-checked runtime helper. Finish with `if (eN == null) ... else Left(eN)`.
- **Fresh names.** Use `FreshName.FromPrefix` for every name: Scala 2 quotes are not hygienic.
- **Result.** For 100 fields the largest method went from over 64 KB to about 600 B for this decoder, and to 3-5 KB
  for fail-fast plus accumulating JSON decoders. Throughput returned to the earlier level.

## The same mistake in other shapes

| Shape | Fix |
|---|---|
| `if (opt.isEmpty) null else w(opt)` inside `(key, value) :: acc` | `if (...) builder.put(key, w(opt))` as a statement |
| `r0.flatMap(a0 => r1.flatMap(a1 => ...))`, or a fold nesting each field | flat `val rK = if (rK-1 ok) fieldK else rK-1` |
| `if (config.useDefaults) ... else ...` per field, config known to the macro | branch in the macro and emit one branch |
| one method with `if (failFast)` around every field | two methods, chosen once |
| a decoder expression passed as a "type witness" to cast a field | `value.asInstanceOf[Field]` |
| local `lazy val` in per-call code | local `def`, or a `lazy val` of the instance |
| schema, regex, alias list or key `Set` built per call | `lazy val` of the instance, or compute it in the macro |
| a dispatch lambda spliced into two or three places | bind it once and refer to it |

## Don't repeat it

- Every change that adds behaviour to generated code is checked twice: for behaviour (tests, oracles) and for cost
  (the size guard, plus a benchmark on a wide type).
- Generated code grows by a constant per field and per subtype.
- Nothing the macro already knows is decided at runtime.
