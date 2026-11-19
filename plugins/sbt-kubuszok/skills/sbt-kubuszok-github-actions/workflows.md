# Workflow templates for sbt-kubuszok 0.2.6

The release workflow follows kubuszok/sbt-kubuszok's own `.github/workflows/release.yml`; the CI workflow follows
kubuszok/kindlings and kubuszok/hearth. Not every kubuszok repo matches these templates yet; the templates are the
target. The action versions were current when this was written; Dependabot keeps them up to date.

## `.github/workflows/ci.yml`

```yaml
name: CI Build

on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  check-formatting:
    runs-on: ubuntu-latest
    name: Check formatting
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0          # .scalafmt.conf `project.git = true` needs git
      - uses: coursier/setup-action@v3.1.0
        with:
          apps: scalafmt          # uses the version from .scalafmt.conf; covers build.sbt too
      - run: scalafmt --check

  build:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        scala: [ '2_13', '3' ]               # must match alias suffixes: ci-<platform>-<scala>
        platform: [ 'jvm', 'js', 'native' ]
        jvm: [ 'temurin:1.17.0.15' ]         # pin; sbt 2 needs 17+
        # exclude cells the build does not define, e.g.:
        # exclude:
        #   - scala: '2_13'
        #     platform: 'native'
    name: "Scala ${{ matrix.scala == '2_13' && '2.13' || '3' }} / ${{ matrix.platform }} / ${{ matrix.jvm }}"
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: coursier/cache-action@v9
      - uses: coursier/setup-action@v3.1.0
        with:
          jvm: ${{ matrix.jvm }}
          apps: sbt
      # only if Scala Native code links against system libraries:
      # - if: matrix.platform == 'native'
      #   run: sudo apt-get update && sudo apt-get install -y libidn2-dev
      - name: Clean, compile, test (+ coverage on JVM)
        run: sbt ci-${{ matrix.platform }}-${{ matrix.scala }}
      # optional: the JVM ci-* alias already ran coverageAggregate
      # - if: matrix.platform == 'jvm'
      #   uses: codecov/codecov-action@v7
      #   with:
      #     token: ${{ secrets.CODECOV_TOKEN }}
```

For a JDK matrix (for example 11/17/21/25), add values to `jvm` and exclude the combinations that cannot work:
Scala 2.13.16 does not run on JDK 25, and Scala 3.8+ and sbt 2 need 17+.

## `.github/workflows/release.yml`

```yaml
name: Sonatype Release

on:
  pull_request:
    branches: [ master ]
  push:
    branches: [ master ]
    tags: [ '*' ]

jobs:
  release:
    # PR snapshots let a change be tested before merging. Bot (Dependabot, Scala Steward) and fork PRs get no
    # secrets, so only trusted authors' PRs publish. Never drop this guard while `pull_request` is a trigger.
    if: >-
      github.event_name != 'pull_request' ||
      contains(fromJSON('["OWNER", "MEMBER", "COLLABORATOR"]'), github.event.pull_request.author_association)
    runs-on: ubuntu-latest
    name: ${{ startsWith(github.ref, 'refs/tags/') && 'Publish Tag as Release' || 'Publish Snapshot' }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0          # required: version and release/snapshot decision come from git tags
      - uses: coursier/cache-action@v9
      - name: Import GPG key for signing the release
        uses: crazy-max/ghaction-import-gpg@v7
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}
      - uses: coursier/setup-action@v3.1.0
        with:
          jvm: 'temurin:1.17.0.15'   # 'temurin:1.11.0.28' is fine for sbt 1.x builds targeting JDK 11
          apps: sbt
      - name: Publish all projects
        run: sbt ci-release
        env:
          SONATYPE_USERNAME: ${{ secrets.SONATYPE_USERNAME }}
          SONATYPE_PASSWORD: ${{ secrets.SONATYPE_PASSWORD }}
```

PR snapshots get a version like `<tag>-<n>-g<sha>-SNAPSHOT` from the PR merge commit (see "Testing a change from a
PR snapshot" in SKILL.md). `ci-release` builds every matrix cell (JVM, JS and Native), and `ubuntu-latest` has the clang that Scala Native needs.
If ci.yml installs extra native libraries, install them here as well.

## Variants

### sbt 2: run sbt in the foreground

Add after `coursier/setup-action` (in every workflow, or once in a composite setup action):

```yaml
      - name: Make `sbt` run in the foreground (sbt 2 thin client starts a background server)
        shell: bash
        run: |
          dir="$RUNNER_TEMP/sbt-foreground"; mkdir -p "$dir"
          printf '#!/usr/bin/env bash\nexec "%s" --server "$@"\n' "$(command -v sbt)" > "$dir/sbt"
          chmod +x "$dir/sbt"; echo "$dir" >> "$GITHUB_PATH"
```

Windows runners also need an `sbt.bat` wrapper (see kubuszok/lls `.github/actions/setup-scala/action.yml`).

### Scaladoc NPE on JDK 24/25

Scala 3 Scaladoc before 3.9.0 can throw a `NullPointerException` in `SignatureBuilder` on JDK 24/25 (a C2 JIT
miscompilation). Prefer JDK 17 for the release job. If a newer JDK is required, keep the class out of the JIT in
`.jvmopts`:

```
-XX:CompileCommand=quiet
-XX:CompileCommand=exclude,dotty/tools/scaladoc/translators/SignatureBuilder.*
```

### Native libraries in published JARs

Build or download the natives in the release job before `sbt ci-release`, exactly as CI does, and in CI verify that
the packaged JAR contains them (`unzip -l`). A missing library does not fail packaging.

### More heap for the release build

`ci-release` builds Scaladoc for every module × platform × Scala cell in one sbt JVM. With a large build, the
`-Xmx` in `.jvmopts` may not be enough. Raise it on the runner only:

```yaml
      - name: Give the release build more heap
        run: sed -i 's/^-Xmx.*/-Xmx8G/' .jvmopts && git update-index --assume-unchanged .jvmopts && cat .jvmopts
```

Place it before `sbt ci-release`. `assume-unchanged` keeps the edit out of `git status`.

### Without PR snapshots

If the maintainer explicitly does not want PR snapshots, drop the `pull_request` trigger together with the `if:`
guard. Never keep the trigger without the guard.

### Publish only after CI is green

Put the release job in ci.yml with `needs: [ check-formatting, build ]` and
`if: github.event_name == 'push'` (with `tags: ['*']` added to ci.yml's `push` trigger). Or keep release.yml
separate and accept that a red commit can still produce a snapshot.

### Several sbt commands in one step

```yaml
        run: sbt "scalafmtCheckAll ; ci-release"     # one argument; `sbt a b` fails on sbt 2 with "Expected ';'"
```

### Nested sbt build

```yaml
      - name: Publish the build plugin
        working-directory: my-build
        run: sbt ci-release
        env: { SONATYPE_USERNAME: ..., SONATYPE_PASSWORD: ... }
```

### Checking the version in a workflow

Use git, not sbt (on sbt 2.0, `sbt 'print x/version'` printed an empty string):

```bash
tag=$(git describe --tags --exact-match HEAD)   # fails if HEAD is not tagged
test -z "$(git status --porcelain)"
```

## `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```
