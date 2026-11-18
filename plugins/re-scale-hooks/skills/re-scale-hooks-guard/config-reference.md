# `.rescale/claude-hooks.yaml` reference (re-scale 0.1.5)

Checked against
[RuleConfig.scala](https://github.com/kubuszok/re-scale/blob/0.1.5/src/main/scala/rescale/hook/RuleConfig.scala)
and
[RuleEvaluator.scala](https://github.com/kubuszok/re-scale/blob/0.1.5/src/main/scala/rescale/hook/RuleEvaluator.scala)
at 0.1.5.

## Document

```yaml
rules:            # list, evaluated top-down, placed before the default rules
  - when: <condition>          # required
    action: allow|ask|deny|pass   # optional
    reason: "text"             # optional; shown to the agent/user
    nested:                    # optional list of rules, same shape
      - when: ...
        action: ...
```

| `action` | Result |
|---|---|
| `allow` | allowed, permission prompt skipped (a non-empty `reason` turns it into `pass`) |
| `pass` | allowed, `reason` shown |
| `ask` | Claude Code asks the user |
| `deny` | blocked; `reason` is returned to the agent |

A rule matches when its `when` matches. Then its `nested` rules are tried in
order; the first that matches decides. If none does, the rule's own `action`
decides; if it has no `action`, the rule counts as not matching and
evaluation moves on to the next rule.

## Conditions

Each condition node sets exactly one of these keys. "Tokens" are the program
name (path stripped), its arguments, and redirect targets of one simple
command.

| Key | Value | Matches when |
|---|---|---|
| `program-in` | list | the program (last path segment) is one of the values |
| `starts-with` | list | program and leading arguments equal the list (`[git, push]` matches `git push origin`) |
| `has-any` | list | any value equals a token |
| `has-all` | list | every value equals some token |
| `has-any-suffix` | list | a token ends with one of the values |
| `has-any-contains` | list | a token contains one of the values |
| `has-redirect` | string | the command has that redirect operator (`">"`, `">>"`, `"2>&1"`, ...) |
| `has-redirect-target-prefix` | list | a redirect target starts with one of the values |
| `and` | list of conditions | all match |
| `or` | list of conditions | any matches |
| `not` | condition | it does not match |
| `followed-by` | condition | the next simple command on the line matches (after `\|`, `&&`, `\|\|` or `;`) |
| `preceded-by` | condition | the previous simple command on the line matches |
| `ignoring` | `{flags: [[flag, arity], ...], when: condition}` | `when` matches after removing each listed flag and the next `arity` arguments (`[["-C", "1"]]` turns `git -C repo stash` into `git stash`) |

## Composition over a command line

A Bash command line is split into simple commands at pipes, `&&`, `||`, `;`
and `( ... )` subshells; a `$(...)` or backtick substitution inside an
argument stays part of that argument's token. Each one gets its own decision from the first matching
rule (no match means allow), and the line gets the strongest: deny, then ask,
then pass, then allow. One denied part denies the whole line.
