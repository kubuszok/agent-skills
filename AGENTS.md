# Maintaining `kubuszok/agent-skills`

This repository is a marketplace of agent skills for **using** kubuszok libraries (Hearth, Kindlings, ...) in
other people's projects. Every library is a separate plugin, so a user installs only what they work with.

What does **not** belong here: skills for maintaining or contributing to a library (build commands, release process,
repository layout, internal test conventions). Those stay in the library's own repository
(e.g. `kindlings/docs/contributing/`, `hearth/docs/contributing/`).

## Layout

The Claude Code marketplace is named `kubuszok` (`agent-skills` is a reserved marketplace name), so plugins are
installed as `<plugin>@kubuszok`.

```
.claude-plugin/marketplace.json     # read by Claude Code, Codex, Copilot CLI and `npx skills`
.cursor-plugin/marketplace.json     # read by Cursor
plugins/<library>/
  .claude-plugin/plugin.json        # read by Claude Code, Codex, Copilot CLI
  .cursor-plugin/plugin.json        # read by Cursor (same content as .claude-plugin/plugin.json)
  README.md                         # what the plugin covers, which library version
  skills/<library>-<topic>/SKILL.md # one folder per skill (Agent Skills format)
  skills/<library>-<topic>/*.md     # optional supporting files, linked from SKILL.md
scripts/validate.py                 # structural checks, run in CI
```

The `skills/` folders follow the open [Agent Skills](https://agentskills.io/specification) format, so harnesses
without a plugin system (OpenCode, Cursor, Gemini CLI, Copilot, ...) can use them by copying/symlinking the folders,
or through `npx skills add`.

## Skill authoring rules

1. **Frontmatter: only portable fields.** `name` (must equal the folder name, lowercase, digits and `-`, at most
   64 chars) and `description` (at most 1024 chars). Optionally `license` and `metadata`. Do **not** use
   harness-specific fields (`paths`, `user-invocable`, `allowed-tools`, `model`, ...) - other harnesses reject or
   ignore them.
2. **Prefix names with the library** (`hearth-...`, `kindlings-...`): harnesses without namespacing install every
   skill into one flat folder.
3. **The description decides when the skill loads.** Say *what* it covers and *when* to use it, with the words a user
   or the code would contain (artifact names, imports, type names, error messages). Third person, no marketing.
4. **For users, not maintainers.** Write from the perspective of someone who added the library to their build. Never
   reference the library's internal file paths as if they were local; link to GitHub
   (`https://github.com/kubuszok/<repo>/blob/<tag>/...`) or to the published docs instead.
5. **Pin the version.** Each `SKILL.md` states which library version it describes (`metadata.library-version` in
   frontmatter plus a sentence near the top), and tells the agent to check the version in the user's build and
   consult the versioned docs when it differs.
6. **Be concise; push details into supporting files.** Keep `SKILL.md` under ~400 lines. Put long tables/reference
   material into sibling `.md` files and link them with relative links, so they load only when needed.
7. **Correct over complete.** Every API, config key, import and default must be verified against the library source
   or its docs at the pinned version. When something is a known difference from an upstream library, say so
   explicitly. When unsure, link to the docs instead of guessing.
8. **Cover the pain points.** Gotchas users actually hit (issues, third-party skills, FAQ) belong in a
   "Gotchas" section, each with the symptom (error text if possible), the cause and the fix.

## Updating after a library release

1. Diff the library between the previously pinned tag and the new one (user docs, public API, changelog).
2. Update affected skills and bump `metadata.library-version` in them.
3. Bump the plugin `version` in `plugins/<lib>/.claude-plugin/plugin.json` and `plugins/<lib>/.cursor-plugin/plugin.json`
   (versions live only in the plugin manifests, never in the marketplace entries). The plugin version
   follows the library version; use a `-N` suffix (e.g. `0.4.0-1`) for skill-only fixes between releases.
4. Run `python3 scripts/validate.py` (also runs in CI) and, if available, `claude plugin validate .`.

## Adding a new library plugin

1. Create `plugins/<lib>/` with both plugin manifests, a `README.md` and `skills/`.
2. Add the plugin to `.claude-plugin/marketplace.json` and `.cursor-plugin/marketplace.json`, with
   `"source": "./plugins/<lib>"` (the `./` prefix is required by `npx skills`; do not set `metadata.pluginRoot`).
3. Add it to the table in the root `README.md`.
4. Run the validator.
