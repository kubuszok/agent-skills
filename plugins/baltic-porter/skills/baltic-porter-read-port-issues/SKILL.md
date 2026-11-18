---
name: baltic-porter-read-port-issues
description: >-
  Reading what a Baltic Porter run could NOT handle automatically and classifying each item before
  any fix: the run-latest report directory (findings.tsv, counts.tsv, report.md, decisions.tsv,
  srcmap.tsv, members.tsv, port-map.tsv, dropped-types.tsv), errors.tsv and its four lanes (EngineGap,
  Approx, Declared, Unmapped), every check (signature, omissions, portability, remediation,
  substitution(dangling), policy, manifest, port-map, porter-notes, trivia, collection-*), policy
  entries that never fired (NeverMatched, Unverifiable, Malformed), "N key(s) nobody read", the
  `/* porter: */` notes, and test-failure anchors. Use when a port reports findings, fails to compile
  or fails a test, before designing any fix.
license: Apache-2.0
metadata:
  library: baltic-porter
  library-version: "0.2.0"
---

# Reading what the port could not do

Version: written against Baltic Porter engine master `ab8e129d`. The consumer pins the engine in
`project/plugins.sbt` as `"com.kubuszok" %% "balticporter-engine" % "<full commit hash>-SNAPSHOT"`.
The full reference is the engine's
[Reading the report](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/reading-the-report.md);
this skill is the order to read it in and the question to answer for each item.

Not covered here: making the change (`baltic-porter-customize-port`), tracing one member's spelling
(`baltic-porter-root-cause-port`), the debug flags that show WHERE a construct came from
([Debugging a port](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/debugging.md)).

## 0. Before you design any fix

- **Consult the reference port.** sge is a hand-written port of libGDX and ssg holds hand-ported
  Java libraries. `grep -rn "<the construct>"` in the reference tree (or its git history) before
  concluding no faithful translation exists, and record whether it SOLVED the construct or merely
  SKIPPED it. A construct that vanished from the hand port tells you only that it is still open.
- **Where the report is.** Each run writes `<reportDir>/run-latest/`. Inside sbt the generator must
  set `balticporter.reportDir` (or `balticporter.report=on`), otherwise no report is written at all.
  sge: `target/balticporter-reports/<label>/run-latest/`; ssg:
  `target/balticporter/port-report/<label>/run-latest/`.
- The run log ends with `[<label>] wrote N Scala files (… dropped, … injected) -> …`. If that line is
  missing the run did not re-emit, and the report you are reading is an old one.

## 1. The one question every issue must answer

Which of three kinds is it? This decides which repository the fix lives in:

| kind | what it means | where the fix goes |
|---|---|---|
| (a) universal | the engine is wrong or incomplete for EVERY library | the engine repository, unconditional. Report it; do not work around it locally |
| (b) configure an existing phase | the mechanism exists; supply this library's values | this repository's `.conf` / manifest / policy code |
| (c) library-specific rule | knowledge that could only ever apply to this library | a `Phase` + `TransformFactory` (or an injected file) in this repository |

Reach for (c) only after establishing that the mechanism cannot be shared; most things that look
library-specific are (b) with the policy written inline. The engine classifies where it can: every
`decisions.tsv` row and most findings carry the kind. Bare compiler errors do not, which is what
`errors.tsv` is for.

## 2. `errors.tsv`: compiler errors, located

Never open an emitted file to work out which member an error is in. `srcmap.tsv` maps each emitted
line range to its member and Java line, and `balticporter.tir.CorrelateMain` (in the engine jar:
`--srcmap [main=|test=]<srcmap.tsv> --scalac <compiler log> --out <dir>`) joins a whole compiler log
through it into `errors.tsv`: `lane  file  line  code  unit  member  javaPath  javaLine  message`.
`baltic-porter-root-cause-port` has a one-line `awk` lookup for a single error.

| lane | meaning | do |
|---|---|---|
| `Approx` | at a region the engine MARKED as approximate | expected; read the remediation attached to the marker in `report.md` |
| `EngineGap` | anywhere else in emitted code, located to a member and its Java | classify it: usually (a), sometimes a (b) you have not configured |
| `Unmapped` | in a file the source map does not cover: injected Scala, a hand-written replacement, a runtime shim | NOT an engine gap. The file is one you wrote or copied in; fix it there |
| `Declared` | the engine's own `scala.compiletime.error`, written under `preview = true` because it had no faithful Scala | the port telling you, at the site, what it could not do |

`Unmapped` is the one most often misread: a dropped type has no source-map entry by construction, so
an error inside its injected replacement is always `Unmapped`. One `Unmapped` error can stop the
compile before any generated file is typed, so a small error count can be measuring nothing.

## 3. `findings.tsv`: one row per check finding

Columns: `id  check  kind  owner  path  line  detail`. The `id` hashes the check, kind, owner and
detail, not the line number, so an upstream whitespace edit does not orphan a baseline entry.
`report.md` is the same content grouped per check, with the engine's classification paragraph at the
head of each group; `diff.txt` compares the run with `baseline/`; `counts.tsv` has one count per
check.

Per check, what a non-zero number tells you:

- **`signature`**: a call site disagrees with its declaration; the port is internally inconsistent.
  Fix this first — every other number is measured over a broken tree.
- **`omissions`**: the engine's model carried a construct and emission lost it. Invisible to a
  compile. Kind (a): report it.
- **`portability(all|emitted|injected)`**: a JVM-only JDK API. Kind (b)/(c): drop the type and
  inject a replacement, re-point it (`static-forwarder`, `class-table`, `call-site-substitution`), or
  accept it if the port targets the JVM only. `injected` non-zero means a replacement YOU ship is
  unportable. See `baltic-porter-cross-platform-port`.
- **`remediation`**: the same portability sites grouped into "this one seam would fix these", ranked.
- **`substitution(emitted)`**: a type you dropped that the emitter wrote a file for anyway; check the
  drop key against what was generated.
- **`substitution(dangling)`**: a dropped type with neither an injected (or provided) replacement nor
  its uses rewritten away, still referenced from code by N files. Fatal. Supply a replacement at that
  fully-qualified name, or rewrite its uses away.
- **`substitution(doc-mention)`**: not fatal; an upstream comment still names a dropped type. Edit
  the comment or accept it.
- **`policy`**: a policy entry that never fired; see section 4 below.
- **`manifest`**: this module and its base disagree (a drop, rename or signature-shaping phase in one
  and not the other; one phase twice with different policy; a dependent that declared no base). See
  [Multi-module ports](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/multi-module-ports.md).
- **`port-map`**: a reference into a base module that the base's published port map says it does
  not emit.
- **`porter-notes`**: a decision with no `/* porter: */` note in the code, or a note with no decision
  behind it. Kind (a).
- **`trivia`**: a Java comment that did not reach the Scala. Kind (a), and not cosmetic: a licence
  notice among these is a licence problem.
- **`collection-closure` / `collection-boundary` / `collection-retarget`** (only with the
  `collections` phase): a mapped supertype with an unmapped subtype; a slot the phase's scope left
  stranded; a value the JDK produces at a type the port retargeted (counted, never silently coerced).

## 4. Policy that never fired: the silent no-op

A misspelt policy entry is a rule that quietly did not run. Two gates catch the two halves:

- **A bad KEY is refused at load**, before anything is generated:
  `port config: …: 1 key(s) nobody read: manifest.dropType. … Fix the spelling, or delete the key.`
  (A hand-written `PortRun(...)` has no such gate; its keys are checked by the compiler.)
- **A bad VALUE reaches the run** (a `dropTypes` entry naming a type that does not exist, a redirect
  naming a member that is gone after an upstream release) and is reported by the `policy` check:
  `[lib] POLICY (declared keys that never fired): N`. Three flavours: `never matched` (a typo or a
  leftover from an upstream rename), `matched, but unverifiable` (the engine cannot prove the match
  is the one you meant), `malformed` (not in the shape the phase documents). Every one is kind (b):
  the fix is in your manifest, never in the engine.

The opposite failure — a drop that fired and left a dangling reference — is
`substitution(dangling)`.

## 5. `decisions.tsv` and the porter notes: the WHY

```
#kind  subjectFqn  reasonClass  reasonDetail  origin  line  detail
AddedMember  com.badlogic.gdx.utils.Array  configured  add-members:com.badlogic.gdx.utils.Array#$minus$eq  com/badlogic/gdx/utils/Array.java  30  arity=1; …
```

`reasonClass` is always `universal`, `configured` or `library-rule` — the three kinds above. For a
`configured` row, `reasonDetail` carries the manifest key verbatim: the string you edit to change the
outcome. One row per DECLARATION whose emitted form a decision changed, never per expression, so it
is the best first thing to skim after an unfamiliar run.

The same facts are written beside the code:

```
grep -rn '/\* porter:' <portRoot>/src_managed
/* porter: renamed-package reason=configured phase=package-rename key="com.example.mylib -> mylib" … */
```

That grep is the complete inventory of non-mechanical translation in a port.

## 6. Test failures: the only evidence of behaviour

Java constructs that translate to valid Scala meaning something else (reference `==`, `x++` as a
value, `switch` fall-through, labelled jumps, class initialisers, …) never move a compile count; only
tests see them. The list is
[Java semantics Scala does not share](https://github.com/kubuszok/balticporter/blob/master/docs/user-guide/java-semantics.md).
A failure inside generated library code that matches one of those rows is an engine bug (kind a).

Correlating a test log (`CorrelateMain --tests <log>`) gives:

- `tests.tsv` (`suite  test  status`) and `tests-diff.txt` against the baseline; `NEWLY FAILING` and
  `NEWLY SKIPPED` are the gates (a skip moves neither the pass nor the fail count);
- `test-failures.tsv`, each failure anchored on the first stack frame in ported code:
  `main-frame` (inside the ported library — the guilty member, exact), `test-frame` (the test body —
  where the failure was observed, not what caused it), then weaker fallbacks (`assert-site`, …);
- a failure whose stack reaches a type in `dropTypes` is expected by derivation (from
  `dropped-types.tsv`), not a regression. `baseline/expected-failures.tsv` is only for a failure no
  drop explains and is normally empty.

A test that stopped running is reported as such, never as a pass.

## 7. Then fix something

Answer the (a)/(b)/(c) question, check the reference port for what a human wrote, then go to
`baltic-porter-customize-port`. Change one thing, then regenerate and measure.
