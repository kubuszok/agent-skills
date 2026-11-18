---
name: re-scale-hooks-guard
description: >-
  The re-scale PreToolUse guard hook (`re-scale hook`) - which Bash commands its default rules deny (grep, rg,
  find, ls, sed, awk, perl, sort, xargs, python, node, bare sbt, rm, kill, pkill, adb, git reset/rebase/clean,
  force push, git config writes, pipes into head/tail/wc/grep, .env/.pem/.key access, writes under /etc or /usr),
  which ask (unknown git subcommands, gh pr create/merge, archive downloads), that every other call is
  auto-approved, how to add or override rules in `.rescale/claude-hooks.yaml`, and what to use instead when a call
  is denied. Use when a tool call is denied or asked about with a re-scale reason, when writing
  .rescale/claude-hooks.yaml, or when installing the hook by hand.
license: Apache-2.0
metadata:
  library: re-scale
  library-version: "0.1.5"
---

# re-scale guard hook

`re-scale hook` is a Claude Code `PreToolUse` validator from
[re-scale](https://github.com/kubuszok/re-scale) **0.1.5**. It steers an agent
away from shell tools that have a dedicated, reviewable replacement and from
commands that destroy state. It works in any repository; nothing in it is
specific to porting or to Scala.

This skill describes 0.1.5. Check `re-scale --version`; if it differs, read
[DefaultRules.scala](https://github.com/kubuszok/re-scale/blob/0.1.5/src/main/scala/rescale/hook/DefaultRules.scala)
at the matching tag.

## How a call is decided

The `re-scale-hooks` plugin runs the hook for the **Bash, Read, Edit and
Write** tools. Other tools (Grep, Glob, WebFetch, MCP tools, ...) never reach
it and go through Claude Code's normal permission flow.

- **Read / Edit / Write**: denied when the path contains `.rescale/data/`,
  otherwise answered `allow`.
- **Bash**: the command is parsed into simple commands (pipelines, `&&`, `||`,
  `;` and `( ... )` subshells are split apart; a `$(...)` or backtick
  substitution inside an argument stays part of that argument). Each simple command is checked
  against the rules top-down, first match wins; then the strongest result
  wins for the whole line (deny > ask > allow). A path prefix on the program
  is ignored: `/usr/bin/grep` is `grep`.
- **Auto-approve**: a call no rule denies or asks about is answered `allow`,
  and Claude Code then **skips its permission prompt** for it. That covers
  every Edit and Write outside `.rescale/data/` and every Bash command that
  falls through to the final catch-all (`make`, `docker`, `curl` without a
  request body, ...). Install this plugin only where that is acceptable.
- If `re-scale` is not on `PATH` the hook prints nothing and exits 0, so
  Claude Code falls back to its normal permission prompts.

## Default rules

Checked against `DefaultRules.scala` at 0.1.5, in evaluation order
(first match wins per simple command):

| Command | Decision | Reason given |
|---|---|---|
| `re-scale`, `ssg-dev`, `sge-dev` | allow | the tool itself |
| `scala-cli`, `cs`, `coursier`, `npm`, `npx`, `cargo`; `java -version`/`--version` | allow | trusted tools |
| `sbt --client ...` | allow | |
| `sbt` without `--client` | **deny** | use `sbt --client` |
| `rm` (any form) | **deny** | needs human confirmation |
| `curl`/`wget` with `-X`, `--request`, `-d`, `--data*` | **deny** | HTTP mutation |
| `kill`, `killall`, `pkill` | **deny** | use `re-scale proc` |
| `adb`, `fastboot` | **deny** | opt in via `claude-hooks.yaml` |
| any redirect into `/etc/`, `/usr/`, `/System/`, `/Library/` | **deny** | system directory |
| an argument ending in `.env`/`.pem`/`.key` or containing `/.env`, `credentials.`, `secret` | **deny** | secret files |
| any command followed by `head`, `tail`, `wc`, `grep`, `rg` | **deny** | write output to a file, then Read it |
| `grep`, `rg`, `ripgrep` | **deny** | Grep tool |
| `find`, `ls` | **deny** | Glob tool |
| `echo ... >` / `>>` | **deny** | Write/Edit tool |
| `sed`, `awk`, `perl` | **deny** | Edit tool |
| `sort`, `uniq`, `cut`, `tr`, `xargs` | **deny** | dedicated tools |
| `python`, `python3`, `ruby`, `node` | **deny** | no ad-hoc scripting |
| `curl`/`wget` of a `.jar`, `.tar.gz`, `.tgz`, `.zip` | ask | archive download |
| `git status/diff/log/show/blame/ls-files/ls-tree/cat-file/rev-parse/describe/shortlog/reflog/name-rev/merge-base/grep`, `git config --get/--list/-l/--edit` | allow | read-only git |
| `git reset/restore/clean/rebase` | **deny** | rewrites local state |
| `git commit --amend` | **deny** | make a new commit |
| `git push --force/-f/--force-with-lease` | **deny** | rewrites remote |
| `git branch -d/-D/-m/-M`, `git tag -d/-f` | **deny** | overwrites data |
| other `git config` | **deny** | settings write |
| `git add/commit/fetch/pull/clone/init/cherry-pick/merge/switch/branch/tag/push` | allow | |
| any other `git` subcommand (`stash`, `checkout`, `worktree`, `rm`, `mv`, ...) | ask | unknown git subcommand |
| `gh pr list/view/diff/checks/status`, `gh issue list/view/status`, `gh release list/view`, `gh run list/view`, `gh repo view`, `gh api` | allow | |
| `gh pr create/merge/close`, `gh issue create/close` | ask | shared state on GitHub |
| `cd`, `pwd`, `mkdir`, `mv`, `cp`, `ln`, `touch`, `chmod`, `tar`, `unzip`, `echo`, `printf`, `tee`, `env`, `export`, ... | allow | safe utilities |
| anything else (`cat`, `wc file`, `make`, `docker`, ...) | allow | catch-all |

Git rules ignore the global flags `-C <path>`, `-c <k=v>`, `--git-dir`,
`--work-tree`, `--namespace`, `--bare`, `--no-replace-objects` and
`--no-optional-locks`, so `git -C repo reset` is still denied.

## When a call is denied

Read the reason; it names the replacement. Do not route around the rule with
another program (`bash -c`, a script file, an alias): if the command is really
needed, ask the user to add a project rule.

| Denied | Do instead |
|---|---|
| `grep`, `rg`, `cmd \| grep` | the Grep tool; for command output, redirect to a file (`cmd > out.txt`) and Grep or Read the file |
| `find`, `ls` | the Glob tool |
| `cmd \| head/tail/wc` | `cmd > out.txt`, then Read it (with offset/limit) |
| `sed`, `awk`, `perl`, `echo > file` | the Edit / Write tools |
| `sort`, `uniq`, `cut`, `tr`, `xargs`, `python`, `node` | the dedicated tools, or ask the user for a project rule |
| bare `sbt ...` | `sbt --client ...` |
| `kill`, `pkill`, `killall` | `re-scale proc list [--kind sbt\|java\|metals] [--dir DIR]`, then `re-scale proc kill --pid N` or `re-scale proc kill --kind sbt --dir <repo>`; for one sbt server, `sbt --client shutdown` in its directory |
| `rm` | ask the user; for tracked files `git rm` (asks for confirmation) |
| `git reset/restore/clean/rebase`, `--amend`, force push | ask the user to run it |
| `Read`/`Edit` under `.rescale/data/` | `re-scale db ...` (porting projects; see the `re-scale-porting` plugin) |

Two re-scale wrappers work without any `.rescale/` file: `re-scale proc ...`
and `re-scale git ...` (thin pass-through to `git`/`gh`). `re-scale build ...`
and `re-scale test ...` also wrap `sbt --client`, but they expect sbt modules
with `src/main/scala` (or `.rescale/modules.txt`), so outside a Scala project
call `sbt --client` directly.

## Project rules: `.rescale/claude-hooks.yaml`

Rules in this file are put **in front of** the defaults, so the first match
wins and a project rule overrides any default. A default cannot be removed,
only shadowed by an earlier rule. Example:

```yaml
rules:
  - when:
      program-in: [adb]
    action: allow
    reason: "This project deploys to Android test devices"

  - when:
      and:
        - starts-with: [git, push]
        - has-any: [--no-verify]
    action: deny
    reason: "Do not bypass git hooks"

  - when:                       # gate, then sub-rules, then fallback
      ignoring:
        flags: [["-C", "1"]]
        when:
          starts-with: [git, stash]
    nested:
      - when:
          has-any: [list, show]
        action: allow
    action: ask
    reason: "git stash changes the working tree"
```

Each rule has `when` (required), `action` (`allow`, `ask`, `deny` or `pass`;
`pass` is `allow` with the reason shown), `reason`, and `nested` (sub-rules
tried when `when` matches; the outer `action` is the fallback; with no
`action` and no matching sub-rule, evaluation continues with the next rule).
Every condition node sets **exactly one** key; full list:
[config-reference.md](config-reference.md).

Only Bash commands go through these rules; the `.rescale/data/` check for
Read/Edit/Write is fixed.

### Is any other `.rescale/` file needed?

No. Verified against `HookCmd`, `RuleConfig` and `Paths` at 0.1.5: the hook
reads only `.rescale/claude-hooks.yaml`, and that file is optional - without
it the defaults apply. No `.rescale/` directory is needed at all for the
defaults. The minimal setup for custom rules is one file,
`.rescale/claude-hooks.yaml`, at the repository root.

## Installing by hand (outside the plugin)

Needs a JDK 22+, sbt and Clang/LLVM:

```bash
git clone --branch 0.1.5 https://github.com/kubuszok/re-scale.git ~/.local/share/re-scale/0.1.5
cd ~/.local/share/re-scale/0.1.5 && sbt install    # builds .build/re-scale-bin
export PATH="$HOME/.local/share/re-scale/0.1.5/bin:$PATH"   # add to your shell rc
re-scale --version                                  # re-scale 0.1.5
```

Always call the `bin/re-scale` wrapper (it caps the heap at 1 GB). To use the
hook in Claude Code without the plugin, add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Read|Edit|Write",
        "hooks": [{ "type": "command", "command": "re-scale hook" }]
      }
    ]
  }
}
```

`re-scale hook` reads one PreToolUse event (JSON) on stdin and prints Claude
Code's `hookSpecificOutput` response, so another harness can use it only if it
sends and accepts that format. Test a rule by hand:

```bash
printf '{"tool_name":"Bash","tool_input":{"command":"git stash"}}' | re-scale hook
```

## Gotchas

- **`cd dir && tail log` is denied with the "don't pipe" reason.** The
  `followed-by` check looks at the next simple command on the line, and `&&`,
  `||` and `;` count as well as `|`. Run the second command on its own.
- **Rules ignored after editing `claude-hooks.yaml`.** A file that fails to
  parse (an unknown `action`, two condition keys in one node, a node with no
  known key) is ignored as a whole; the hook prints `re-scale hook: ignoring
  <file> (<error>)` on stderr and uses the defaults. A misspelled key next to
  a valid one is silently dropped instead. Run the `printf ... | re-scale hook`
  test above to check a new rule.
- **Rules not picked up in a subdirectory.** The project root is the nearest
  directory, walking up from the current directory, that contains one of
  `.rescale`, `build.sbt`, `build.sc`, `pom.xml`, `Cargo.toml`, `package.json`,
  `pyproject.toml`, `.git`. A nested project or submodule with its own
  `build.sbt` or `.git` becomes the root, and the outer `.rescale/` is not seen.
- **`has-any` matches whole tokens.** `has-any: [--force]` does not match
  `--force=true`; use `has-any-contains` for substrings.
- **Absolute paths do not bypass rules.** `/usr/bin/grep` and
  `./node_modules/.bin/foo` are matched by their last path segment.
