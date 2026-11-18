# `re-scale-porting` plugin

Skills and agents for porting libraries to Scala 3 with
[re-scale](https://github.com/kubuszok/re-scale) **0.1.5**, a Scala Native CLI
that adds tracking databases, anti-shortcut scanners and covenant headers to a
porting project. re-scale reads project specifics from `.rescale/*.yaml` in
the repository being ported to; the skills here are generic, and each project
keeps its own type mappings and architecture notes in its own repository.

Docs: the [README at 0.1.5](https://github.com/kubuszok/re-scale/blob/0.1.5/README.md).

Install (Claude Code), together with the guard hook:

```
/plugin install re-scale-porting@kubuszok
/plugin install re-scale-hooks@kubuszok
```

The porting skills assume the rules of
[`re-scale-hooks`](../re-scale-hooks) (no shell `grep`/`sed`/`find`, `sbt
--client` only, no `rm`/`kill`, no direct `.rescale/data/` access). See the
[root README](../../README.md) for other harnesses.

## Skills

| Skill | Covers |
|---|---|
| `re-scale-porting-getting-started` | Installing the CLI, the `.rescale/` files, which command to use, full command reference |
| `re-scale-porting-guide-porting` | The 100% rule, implement -> audit -> fix loop, fixing a tracked issue test-first, documented skips, ratchets |
| `re-scale-porting-guide-conversion` | Java (step by step), Dart and Ruby mappings; Java constructs that compile in Scala but behave differently |
| `re-scale-porting-guide-nullable` | Replacing `null` with the project's `Nullable[A]`; null-related scanner hits |
| `re-scale-porting-guide-control-flow` | `return` / `break` / `continue` / labels / `switch` with `boundary`/`break`; breaks swallowed by `catch` |
| `re-scale-porting-guide-code-style` | License header and Migration notes, braces, split packages, `-Werror` flags, comments |
| `re-scale-porting-guide-verification` | Checklist before "done": compile, tests, shortcuts, compare, stale stubs, covenants, tracking |
| `re-scale-porting-convert-file` | Converting one upstream file end to end |
| `re-scale-porting-verify-file` | Quick check of one ported file |
| `re-scale-porting-audit-file` | Auditing one file against its original and recording the verdict |
| `re-scale-porting-audit-package` | Auditing a package and writing its audit document |
| `re-scale-porting-correct-package` | Audit -> fix -> re-audit -> commit for a package |
| `re-scale-porting-gap-fix` | Fixing scanner hits and missing methods in one file |
| `re-scale-porting-find-issues` | Sweeping the codebase for remaining problems; the full scanner pattern list |
| `re-scale-porting-audit-status` | Audit counts and unaudited files |
| `re-scale-porting-check-progress` | Migration, audit, covenant and shortcut numbers |
| `re-scale-porting-file-metadata` | `re-scale fileinfo`: query, filter and batch-update header properties |
| `re-scale-porting-lint` | Compiler lint flags, unused warnings, promoting warnings to errors |

The skills call the `re-scale` binary, which must be on `PATH`. In Claude Code
the plugin's session hook installs it; elsewhere, install it by hand
(`re-scale-porting-getting-started`).

## Agents and hooks (Claude Code only)

Other harnesses load only the skills.

- **Agents**: `re-scale-porting:port-implementer` (ports code, fixes audit
  findings) and `re-scale-porting:port-auditor` (read-only, compares port with
  original, records issues).
- **`SessionStart` hook** (`hooks/session-start.sh`): if `re-scale 0.1.5` is not
  on `PATH`, clones the `0.1.5` tag into `~/.local/share/re-scale/0.1.5` (or
  `$RESCALE_HOME`), builds it with `sbt install` (needs a JDK, sbt and Clang),
  and adds its `bin/` to `PATH` for the session.

There is no `PreToolUse` hook here; that is `re-scale-hooks`. Both plugins ship
the same installer, and running both is harmless: the script exits immediately
when `re-scale 0.1.5` is already on `PATH`, and otherwise reuses the same clone
and build.

## Moving from older names

- **`re-scale@kubuszok`** (the single plugin this one was split from) becomes
  two plugins: `re-scale-porting@kubuszok` (skills, agents, installer) and
  `re-scale-hooks@kubuszok` (the guard hook). Skill
  `re-scale-<topic>` is now `re-scale-porting-<topic>`, invoked as
  `/re-scale-porting:re-scale-porting-<topic>`; agents are
  `re-scale-porting:port-implementer` / `re-scale-porting:port-auditor`.
- **`re-scale@kubuszok-tools`** (the plugin from the re-scale repository)
  likewise becomes `re-scale-porting@kubuszok` plus `re-scale-hooks@kubuszok`.
  Its skills gained a prefix: `/re-scale:guide-x` becomes
  `/re-scale-porting:re-scale-porting-guide-x` (for example
  `/re-scale:guide-conversion` -> `/re-scale-porting:re-scale-porting-guide-conversion`,
  `audit-file` -> `re-scale-porting-audit-file`); `re-scale-porting-getting-started`
  is new. Agents `re-scale:port-implementer` / `re-scale:port-auditor` become
  `re-scale-porting:port-implementer` / `re-scale-porting:port-auditor`.

Update skill and agent references in your `CLAUDE.md` / `AGENTS.md`
accordingly.
