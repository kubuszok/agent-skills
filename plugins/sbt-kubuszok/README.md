# `sbt-kubuszok` plugin

Skills for **using** [sbt-kubuszok](https://github.com/kubuszok/sbt-kubuszok) **0.2.6**, the sbt plugin that bundles
and configures the build tooling of kubuszok Scala projects: git versioning, Maven Central publishing (`ci-release`),
scalafmt, scoverage, sbt-projectmatrix/commandmatrix, Scala.js, Scala Native, sbt-pgp, MiMa, IDE settings.

The skills are written so that an agent adding the plugin to a repository (or writing its GitHub Actions) does not
re-configure what the plugin already does, and does not hit the failures seen on first snapshot/release publishes.

Install: `/plugin install sbt-kubuszok@kubuszok` (Claude Code). See the [root README](../../README.md) for other harnesses.

## Skills

| Skill | Covers |
|---|---|
| `sbt-kubuszok-setup` | sbt/plugin version compatibility, `plugins.sbt`, what the plugin configures (do not repeat it), `projectType`, root and `KubuszokRootPlugin`, `Aliases`, `DevProperties`/`dev.properties`, sbt 1.x vs 2.x differences, migration checklist, `build.sbt` templates |
| `sbt-kubuszok-github-actions` | `ci.yml` (formatting check, platform x Scala matrix over `ci-*` aliases) and `release.yml` (`sbt ci-release`, GPG, Central secrets), release procedure via git tags, Scala Steward/Dependabot |
| `sbt-kubuszok-troubleshooting` | Error messages from failed CI and publish runs, with cause and fix |
