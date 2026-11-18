# `re-scale` plugin

Skills, agents and hooks for porting libraries to Scala 3 with
[re-scale](https://github.com/kubuszok/re-scale) **0.1.5**, a Scala Native CLI
that adds tracking databases, anti-shortcut scanners and covenant headers to a
porting project. re-scale reads project specifics from `.rescale/*.yaml` in
the repository being ported to; the skills here are generic, and each project
keeps its own type mappings and architecture notes in its own repository.

Docs: the [README at 0.1.5](https://github.com/kubuszok/re-scale/blob/0.1.5/README.md).

Install: `/plugin install re-scale@kubuszok` (Claude Code). See the
[root README](../../README.md) for other harnesses.

## Skills

| Skill | Covers |
|---|---|
| `re-scale-getting-started` | Installing the CLI, the `.rescale/` files, what the hook denies, which command to use, full command reference |
| `re-scale-guide-porting` | The 100% rule, implement -> audit -> fix loop, fixing a tracked issue test-first, documented skips, ratchets |
| `re-scale-guide-conversion` | Java (step by step), Dart and Ruby mappings; Java constructs that compile in Scala but behave differently |
| `re-scale-guide-nullable` | Replacing `null` with the project's `Nullable[A]`; null-related scanner hits |
| `re-scale-guide-control-flow` | `return` / `break` / `continue` / labels / `switch` with `boundary`/`break`; breaks swallowed by `catch` |
| `re-scale-guide-code-style` | License header and Migration notes, braces, split packages, `-Werror` flags, comments |
| `re-scale-guide-verification` | Checklist before "done": compile, tests, shortcuts, compare, stale stubs, covenants, tracking |
| `re-scale-convert-file` | Converting one upstream file end to end |
| `re-scale-verify-file` | Quick check of one ported file |
| `re-scale-audit-file` | Auditing one file against its original and recording the verdict |
| `re-scale-audit-package` | Auditing a package and writing its audit document |
| `re-scale-correct-package` | Audit -> fix -> re-audit -> commit for a package |
| `re-scale-gap-fix` | Fixing scanner hits and missing methods in one file |
| `re-scale-find-issues` | Sweeping the codebase for remaining problems; the full scanner pattern list |
| `re-scale-audit-status` | Audit counts and unaudited files |
| `re-scale-check-progress` | Migration, audit, covenant and shortcut numbers |
| `re-scale-file-metadata` | `re-scale fileinfo`: query, filter and batch-update header properties |
| `re-scale-lint` | Compiler lint flags, unused warnings, promoting warnings to errors |

The skills call the `re-scale` binary, which must be on `PATH`. In Claude Code
the plugin's session hook installs it; elsewhere, install it by hand
(`re-scale-getting-started`).

## Agents and hooks (Claude Code only)

Other harnesses load only the skills.

- **Agents**: `port-implementer` (ports code, fixes audit findings) and
  `port-auditor` (read-only, compares port with original, records issues).
  Referenced as `re-scale:port-implementer` / `re-scale:port-auditor`.
- **`SessionStart` hook** (`hooks/session-start.sh`): if `re-scale 0.1.5` is not
  on `PATH`, clones the `0.1.5` tag into `~/.local/share/re-scale/0.1.5` (or
  `$RESCALE_HOME`), builds it with `sbt install` (needs a JDK, sbt and Clang),
  and adds its `bin/` to `PATH` for the session.
- **`PreToolUse` hook** (`hooks/pre-tool-use.sh`, for Bash, Read, Edit,
  Write): runs `re-scale hook` when the binary is available. It denies shell
  search/edit tools (`grep`, `find`, `ls`, `sed`, `awk`, ...), bare `sbt`,
  `rm`, `kill`, destructive git commands and direct access to
  `.rescale/data/`. It also **approves** every call no rule denies or asks
  about - those calls skip Claude Code's permission prompt. Projects add rules
  in `.rescale/claude-hooks.yaml`.

## Moving from the old plugin

This plugin replaces the one in the re-scale repository
(`re-scale@kubuszok-tools`). Skills are renamed with a `re-scale-` prefix:
`guide-nullable` -> `re-scale-guide-nullable`, `audit-file` ->
`re-scale-audit-file`, and so on; `re-scale-getting-started` is new. Update
skill references in your `CLAUDE.md` (for example `/re-scale:guide-conversion`
becomes `/re-scale:re-scale-guide-conversion`). Agent names are unchanged.
