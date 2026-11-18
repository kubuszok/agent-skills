# kubuszok agent skills

Agent skills for **using** [kubuszok](https://github.com/kubuszok)'s Scala libraries. They teach coding agents
(Claude Code, Codex, OpenCode, Cursor, GitHub Copilot, Gemini CLI, ...) the current API, configuration, gotchas and
differences from upstream libraries, so the agent writes code that compiles and behaves as intended.

Each library is a separate plugin. Install only the ones your project uses.

| Plugin | Library version | For |
|---|---|---|
| [`hearth`](plugins/hearth) | [Hearth](https://github.com/kubuszok/hearth) 0.4.5 | Writing your own Scala 2.13 / Scala 3 macros with Hearth: cross-quotes, `MIO`, `CaseClass`/`Enum`, type class derivation, standard extensions, debugging, testing; Hearth's runtime utilities (`TypeName`, source location) |
| [`kindlings`](plugins/kindlings) | [Kindlings](https://github.com/kubuszok/kindlings) 0.4.0 | Using Kindlings derivation (circe, jsoniter-scala, cats, avro, pureconfig, sconfig, tapir, yaml, xml, ubjson, scalacheck, diff, fast-show-pretty), its integrations, and the di / mock / optics / parser modules |
| [`sbt-kubuszok`](plugins/sbt-kubuszok) | [sbt-kubuszok](https://github.com/kubuszok/sbt-kubuszok) 0.2.4 | Adding the sbt-kubuszok plugin to a build: what it already configures, `projectType`/`Aliases`/`DevProperties`, GitHub Actions CI and release workflows, troubleshooting failed snapshot/release publishes |
| [`baltic-porter`](plugins/baltic-porter) | [Baltic Porter](https://github.com/kubuszok/balticporter) engine master `ab8e129d` | A repository that generates Scala 3 sources from Java with Baltic Porter: configuring and customizing a port, reading what a run could not handle, tracing a generated defect to its rule, bumping the engine pin, cross-platform rows, CI and caching. Includes guard hooks (Claude Code only) |
| [`multiarch-scala`](plugins/multiarch-scala) | [multiarch-scala](https://github.com/kubuszok/multiarch-scala) 0.4.0 | Cross-platform JVM / Scala.js / Scala Native builds: native library provider JARs, `NativeLibLoader`, Panama FFM, zig cross-linking, JVM release packaging, Android APKs without Gradle, cross-platform resources and `ServiceLoader` |
| [`re-scale-hooks`](plugins/re-scale-hooks) | [re-scale](https://github.com/kubuszok/re-scale) 0.1.5 | Any repository: a guard hook that denies shell `grep`/`find`/`sed`, bare `sbt`, `rm`, `kill` and destructive git, asks before unknown git and GitHub state changes, and auto-approves everything else; project rules in `.rescale/claude-hooks.yaml`. Hooks are Claude Code only |
| [`re-scale-porting`](plugins/re-scale-porting) | [re-scale](https://github.com/kubuszok/re-scale) 0.1.5 | Porting a library to Scala 3 with the re-scale CLI: conversion guides (Java, Dart, Ruby), shortcut and stub scans, file-header metadata, migration / audit / issue tracking, the implement-audit loop. Includes agents (Claude Code only); use with `re-scale-hooks` |

The skills describe the library version shown above. They also tell the agent to check the version in your build
and to consult the documentation of that version when it differs.

These skills are for library **users**. Skills for maintaining or contributing to a library live in that library's
repository.

## Installation

In the commands below, replace `kindlings` with the plugin you want (`hearth`, `kindlings`, ...). The marketplace is
called `kubuszok`.

### Claude Code

```
/plugin marketplace add kubuszok/agent-skills
/plugin install kindlings@kubuszok
```

or from the shell:

```bash
claude plugin marketplace add kubuszok/agent-skills
claude plugin install kindlings@kubuszok --scope project   # or --scope user
```

Skills from a plugin are namespaced, e.g. `/kindlings:kindlings-circe`. Claude loads them automatically when they are
relevant. To update later, run `/plugin marketplace update kubuszok`.

**Sharing the setup with your team.** Commit this to `.claude/settings.json` in your project:

```json
{
  "extraKnownMarketplaces": {
    "kubuszok": {
      "source": { "source": "github", "repo": "kubuszok/agent-skills" }
    }
  },
  "enabledPlugins": {
    "kindlings@kubuszok": true
  }
}
```

Teammates are offered the marketplace after they trust the folder. Each of them then installs the plugin once with
`claude plugin install kindlings@kubuszok --scope project`.

### OpenAI Codex

Codex reads the same marketplace:

```bash
codex plugin marketplace add kubuszok/agent-skills
codex plugin add kindlings@kubuszok
```

In the TUI, `/plugins` lets you browse the marketplace. You can also install a single skill with the bundled
`$skill-installer` skill. Give it a skill folder from this repository, e.g. `skills/kindlings/kindlings-circe`.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add kubuszok/agent-skills
copilot plugin install kindlings@kubuszok
```

### Cursor

Open *Customize* → *Plugins* → *From GitHub Repository* and enter `kubuszok/agent-skills`. Then pick the plugins you
want. Cursor reads `.cursor-plugin/marketplace.json`.

### OpenCode, Gemini CLI and other harnesses

These harnesses read plain skill folders: OpenCode reads `.opencode/skills`, `.claude/skills` and `.agents/skills`,
Gemini CLI reads `.gemini/skills` and `.agents/skills`. The simplest way to install skills there is the
[`skills`](https://github.com/vercel-labs/skills) CLI. It knows where each agent looks for skills:

```bash
# all skills of one plugin, for OpenCode, into the current project
npx skills add https://github.com/kubuszok/agent-skills/tree/master/skills/kindlings -a opencode

# pick skills interactively, for several agents at once
npx skills add kubuszok/agent-skills -a opencode -a gemini-cli -a codex

# list what is available
npx skills add kubuszok/agent-skills --list
```

Add `-g` to install for your user instead of the project. Run `npx skills update` to update later.

Other options:

- **OpenCode without `npx`**: clone this repository and add the plugin's skills folder to `opencode.json`:
  `{ "skills": ["/path/to/agent-skills/skills/kindlings"] }`.
- **Gemini CLI**: `gemini skills install https://github.com/kubuszok/agent-skills.git --path skills/kindlings/kindlings-circe`.
- **GitHub CLI**: `gh skill install kubuszok/agent-skills kindlings-circe --agent <agent>`.
- **Manually**: copy (or symlink) `skills/<plugin>/*` into the skills directory of your agent.
  `.agents/skills/` in your project is read by most harnesses.

## Repository layout

```
.claude-plugin/marketplace.json   # Claude Code, Codex, Copilot CLI, npx skills
.cursor-plugin/marketplace.json   # Cursor
skills/<library>                  # symlink to plugins/<library>/skills - the plain skill set
plugins/<library>/
  .claude-plugin/plugin.json
  .cursor-plugin/plugin.json
  skills/<library>-<topic>/SKILL.md
```

Skills use the open [Agent Skills](https://agentskills.io/specification) format, with only portable frontmatter.

## Contributing

Corrections are welcome, especially when a skill led an agent astray. Please open an issue or a PR with the
library version, what the agent did, and what it should have done. See [AGENTS.md](AGENTS.md) for the authoring
rules and the release-update checklist. Run `python3 scripts/validate.py` before you submit.

## License

[Apache License 2.0](LICENSE)
