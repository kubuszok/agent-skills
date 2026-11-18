---
name: multiarch-scala-browser-packaging
description: >-
  Packaging the Scala.js row of a multiarch-scala projectMatrix for the browser with plain sbt-scalajs:
  scalaJSUseMainModuleInitializer, ModuleKind (NoModule, CommonJSModule, ESModule), fastLinkJS vs fullLinkJS and
  scalaJSLinkerOutputDirectory, a hand-written index.html, copying assets next to the bundle or embedding them with
  multiarch-resources, serving over HTTP, and the experimental WebAssembly backend. Covers failures such as a blank
  page over file://, "ReferenceError: document is not defined" from sbt run on Node.js, 404 for assets, and ES module
  tests on Node. Use when a cross-platform app also has to run in a browser.
license: Apache-2.0
metadata:
  library: multiarch-scala
  library-version: "0.4.0"
---

# Browser packaging for the Scala.js row

Version: written alongside multiarch-scala **0.4.0**. multiarch-scala has **no browser packaging task**: this is
plain [sbt-scalajs](https://www.scala-js.org/doc/project/), plus `multiarch-resources` for assets. Check the user's
sbt-scalajs version and prefer the Scala.js docs for that version when they disagree with this skill.

## Linking

```scala
import org.scalajs.linker.interface.ModuleKind

.jsPlatform(scalaVersions = Seq(scala3), settings = Seq(
  scalaJSUseMainModuleInitializer := true,                          // run `main` on load (applications)
  scalaJSLinkerConfig ~= (_.withModuleKind(ModuleKind.ESModule))   // <script type="module">
))
```

| Task | Use | Notes |
|---|---|---|
| `fastLinkJS` | development | incremental, unoptimised, large |
| `fullLinkJS` | release | optimised, much smaller, slower |

The output is a directory (`main.js`, source maps, more modules with ES module splitting), given by
`show <projectJS>/Compile/fullLinkJS/scalaJSLinkerOutputDirectory`.

| `ModuleKind` | Load with | Notes |
|---|---|---|
| `NoModule` (default) | `<script src="main.js">` | simplest |
| `CommonJSModule` | Node.js / a bundler | not loadable directly in a browser |
| `ESModule` | `<script type="module" src="main.js">` | browser-native; required by the WebAssembly backend |

`scalaJSUseMainModuleInitializer := true` needs an object with an ordinary `def main(args: Array[String]): Unit`
(and `Compile / mainClass` when there are several).

## A distribution directory

sbt-scalajs writes JS only; the HTML page and assets are yours.

```scala
lazy val packageBrowser = taskKey[File]("Browser distribution: JS, index.html, assets")

packageBrowser := {
  val _      = (Compile / fullLinkJS).value
  val jsDir  = (Compile / fullLinkJS / scalaJSLinkerOutputDirectory).value
  val out    = target.value / "browser-dist"
  IO.delete(out)
  IO.copyDirectory(jsDir, out)
  val res = (Compile / resourceDirectory).value
  if (res.exists()) IO.copyDirectory(res, out / "assets")
  IO.write(out / "index.html",
    """<!DOCTYPE html>
      |<html><head><meta charset="UTF-8"><title>My App</title></head>
      |<body><canvas id="canvas"></canvas><script type="module" src="main.js"></script></body></html>
      |""".stripMargin)
  out
}
```

The browser cannot list a directory over HTTP; if the app must discover assets, also write a manifest file (e.g.
`assets.txt` with one path per line) and read it first.

### Assets without HTTP requests

For small files the code reads synchronously (shaders, fonts, data tables), embed them in the JS bundle with
`multiarch-resources` and read them with `PlatformResources` exactly as on the JVM - see the
`multiarch-scala-resources-serviceloader` skill. Large media is better served as files and fetched.

## Serving and running

- Serve the directory over HTTP (`npx http-server <dir> -c-1`, or any static server); ES modules do not load from
  `file://`.
- `sbt <projectJS>/run` runs on **Node.js**, which has no DOM; use it only for code that does not touch browser APIs.
- Watch mode: `~<projectJS>/fastLinkJS` in sbt and a static server on the `fastLinkJS` output directory.
- Browser tests: `Test / jsEnv` with `scalajs-env-selenium` or `scalajs-env-jsdom-nodejs`, or drive the packaged
  page with Playwright.

## WebAssembly backend (experimental)

```scala
scalaJSLinkerConfig ~= (_.withExperimentalUseWebAssembly(true).withModuleKind(ModuleKind.ESModule))
```

Needs ES modules and a recent Node.js/browser; Node may need flags such as `--experimental-wasm-exnref` in
`jsEnv`. Check the Scala.js docs of the version in use for the current list.

Loading **pre-built** `.wasm` files (a `wasm-provider-*` JAR, e.g. tree-sitter grammars) is a different thing:
multiarch-scala has no wasm provider type and does not extract them. Unpack the JAR yourself and pass the directory
to the code, e.g. through an environment variable on `Test / jsEnv`:

```scala
Test / jsEnv := new org.scalajs.jsenv.nodejs.NodeJSEnv(
  org.scalajs.jsenv.nodejs.NodeJSEnv.Config().withEnv(Map("MY_WASM_DIR" -> sys.env.getOrElse("MY_WASM_DIR", "/tmp/my-wasm")))
)
```

(sbt 2.x: wrap the value in `Def.uncached(...)`; a `JSEnv` cannot be cached.)

## Gotchas

- **Blank page, console shows CORS or MIME type errors** - opened through `file://` or served with a wrong
  content type. Serve over HTTP; `.js` must be `text/javascript`, `.wasm` `application/wasm`.
- **`ReferenceError: document is not defined`** - the code ran on Node.js (`run` or `test`), which has no DOM. Use
  a browser or a jsdom environment.
- **`fetch("assets/x.png")` returns 404** - assets were not copied next to `main.js`, or the path is relative to the
  wrong page URL.
- **`getResourceAsStream` returns `null` in the browser** - Scala.js has no classpath; embed with
  `multiarch-resources` or fetch the file.
- **Node.js tests fail to load ES module output** - give tests their own module kind:
  `Test / scalaJSLinkerConfig ~= (_.withModuleKind(ModuleKind.CommonJSModule))`.
- **Main does not run** - `scalaJSUseMainModuleInitializer` is not set on the JS row.
