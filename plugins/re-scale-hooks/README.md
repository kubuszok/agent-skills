# `re-scale-hooks` plugin

The guard hook from [re-scale](https://github.com/kubuszok/re-scale) **0.1.5**,
for any repository - porting or not. It stops an agent from using shell tools
that have a dedicated replacement (`grep`, `find`, `ls`, `sed`, `awk`, pipes
into `head`/`tail`/`wc`), bare `sbt`, `rm`, `kill`, destructive git commands
and secret files, and asks before unknown git subcommands and GitHub state
changes.

Install: `/plugin install re-scale-hooks@kubuszok` (Claude Code only; other
harnesses load only the skill). For the porting workflow add
[`re-scale-porting`](../re-scale-porting) as well.

## What it does

- **`SessionStart` hook** (`hooks/session-start.sh`): if `re-scale 0.1.5` is not
  on `PATH`, clones the `0.1.5` tag into `~/.local/share/re-scale/0.1.5` (or
  `$RESCALE_HOME`), builds it with `sbt install` (needs a JDK 22+, sbt and
  Clang), and adds its `bin/` to `PATH` for the session. The same script ships
  in `re-scale-porting`; running both is harmless, because it exits
  immediately when the right version is already on `PATH`.
- **`PreToolUse` hook** (`hooks/pre-tool-use.sh`, for Bash, Read, Edit,
  Write): runs `re-scale hook`, or does nothing when the binary is missing.

**It auto-approves.** Every call that no rule denies or asks about is answered
`allow`, so Claude Code skips its permission prompt for it - all Edit and
Write calls outside `.rescale/data/`, and every Bash command that is not on a
deny or ask list.

Projects add or override rules in `.rescale/claude-hooks.yaml`; no other
`.rescale/` file is needed.

## Skill

| Skill | Covers |
|---|---|
| `re-scale-hooks-guard` | The default deny/ask/allow rules, auto-approval, the `.rescale/claude-hooks.yaml` format, what to use instead of a denied command, installing the hook by hand |

## Moving from older names

This plugin and `re-scale-porting` replace the single `re-scale@kubuszok`
plugin and the `re-scale@kubuszok-tools` plugin from the re-scale
repository. Install both to keep the previous behaviour; install only this one
for the hook alone.
