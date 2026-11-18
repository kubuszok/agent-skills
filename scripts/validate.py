#!/usr/bin/env python3
"""Structural checks for the marketplace. No dependencies beyond the Python standard library.

Checks:
- both marketplace files list the same plugins, with `./plugins/<name>` sources that exist;
- `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json` of each plugin are identical and named after the folder;
- versions are set only in plugin manifests;
- every skill folder has a SKILL.md with portable frontmatter (name == folder, description <= 1024 chars,
  only name/description/license/compatibility/metadata keys), a `metadata.library-version` equal to the plugin
  version (ignoring a `-N` skill-fix suffix), skill names are unique across plugins and prefixed with the plugin name;
- relative Markdown links inside skills point to existing files.
"""
import json
import pathlib
import re
import sys

try:  # optional: strict YAML check when PyYAML is installed (it is in CI)
    import yaml
except ImportError:
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def load_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        err(f"{path.relative_to(ROOT)}: cannot parse JSON: {e}")
        return None


def parse_frontmatter(text: str, where: str):
    """Minimal YAML subset parser: `key: value`, `key: >`/`|` blocks, one level of nested mapping."""
    if not text.startswith("---\n"):
        err(f"{where}: missing frontmatter")
        return None
    end = text.find("\n---", 4)
    if end < 0:
        err(f"{where}: unterminated frontmatter")
        return None
    lines = text[4:end].split("\n")
    data: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith(" "):
            err(f"{where}: unexpected indentation in frontmatter: {line!r}")
            i += 1
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        i += 1
        block: list[str] = []
        while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
            block.append(lines[i])
            i += 1
        if value in (">", "|", ">-", "|-"):
            joiner = " " if value.startswith(">") else "\n"
            data[key] = joiner.join(b.strip() for b in block if b.strip())
        elif value == "" and block:
            nested = {}
            for b in block:
                if not b.strip():
                    continue
                k, _, v = b.strip().partition(":")
                v = v.split(" #", 1)[0].strip()
                nested[k.strip()] = v.strip("\"'")
            data[key] = nested
        else:
            quoted = value[:1] in "\"'" and value[-1:] == value[:1]
            if not quoted and (" #" in value or ": " in value):
                err(f"{where}: unquoted value of {key!r} contains ' #' or ': ' (invalid in plain YAML); "
                    "use a folded block scalar (`key: >-`)")
            data[key] = value.strip("\"'")
    return data


def base_version(v: str) -> str:
    return re.sub(r"-\d+$", "", v)


def main() -> int:
    claude_mp = load_json(ROOT / ".claude-plugin/marketplace.json")
    cursor_mp = load_json(ROOT / ".cursor-plugin/marketplace.json")
    if claude_mp is None or cursor_mp is None:
        return report()

    if claude_mp.get("name") == "agent-skills":
        err("marketplace name 'agent-skills' is reserved by Claude Code")
    if claude_mp.get("name") != cursor_mp.get("name"):
        err("marketplace names differ between .claude-plugin and .cursor-plugin")

    def entries(mp, label):
        out = {}
        for e in mp.get("plugins", []):
            n = e.get("name")
            src = e.get("source")
            if src != f"./plugins/{n}":
                err(f"{label}: plugin {n!r} must have source './plugins/{n}', got {src!r}")
            if "version" in e:
                err(f"{label}: plugin {n!r} sets 'version'; keep versions in plugin.json only")
            if not e.get("description"):
                err(f"{label}: plugin {n!r} has no description")
            out[n] = e
        return out

    claude_entries = entries(claude_mp, ".claude-plugin/marketplace.json")
    cursor_entries = entries(cursor_mp, ".cursor-plugin/marketplace.json")
    if set(claude_entries) != set(cursor_entries):
        err(f"marketplaces list different plugins: {sorted(claude_entries)} vs {sorted(cursor_entries)}")

    plugin_dirs = {p.name for p in (ROOT / "plugins").iterdir() if p.is_dir()}
    if plugin_dirs != set(claude_entries):
        err(f"plugins/ folders {sorted(plugin_dirs)} do not match marketplace entries {sorted(claude_entries)}")

    seen_skills: dict[str, str] = {}
    for plugin in sorted(plugin_dirs):
        pdir = ROOT / "plugins" / plugin
        cm = load_json(pdir / ".claude-plugin/plugin.json")
        cu = load_json(pdir / ".cursor-plugin/plugin.json")
        if cm is None or cu is None:
            continue
        if cm != cu:
            err(f"plugins/{plugin}: .claude-plugin/plugin.json and .cursor-plugin/plugin.json differ")
        if cm.get("name") != plugin:
            err(f"plugins/{plugin}: plugin.json name {cm.get('name')!r} != folder name")
        version = cm.get("version")
        if not version:
            err(f"plugins/{plugin}: plugin.json has no version")
        if not (pdir / "README.md").exists():
            err(f"plugins/{plugin}: missing README.md")
        skills_dir = pdir / "skills"
        skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir()) if skills_dir.exists() else []
        if not skill_dirs:
            err(f"plugins/{plugin}: no skills")
        for sdir in skill_dirs:
            where = str((sdir / "SKILL.md").relative_to(ROOT))
            if not (sdir / "SKILL.md").exists():
                err(f"{where}: missing")
                continue
            text = (sdir / "SKILL.md").read_text()
            fm = parse_frontmatter(text, where)
            if fm is None:
                continue
            if yaml is not None:
                try:
                    strict = yaml.safe_load(text[4 : text.find("\n---", 4)])
                    if strict.get("description") != fm.get("description") or strict.get("name") != fm.get("name"):
                        err(f"{where}: frontmatter parses differently with a strict YAML parser")
                except Exception as e:  # noqa: BLE001
                    err(f"{where}: invalid YAML frontmatter: {e}")
            extra = set(fm) - ALLOWED_KEYS
            if extra:
                err(f"{where}: non-portable frontmatter keys {sorted(extra)}")
            name = fm.get("name", "")
            if name != sdir.name:
                err(f"{where}: name {name!r} != folder name {sdir.name!r}")
            if not NAME_RE.match(name) or len(name) > 64:
                err(f"{where}: invalid name {name!r}")
            if not name.startswith(plugin + "-") and name != plugin:
                err(f"{where}: name must be prefixed with '{plugin}-'")
            if name in seen_skills:
                err(f"{where}: duplicate skill name, also in {seen_skills[name]}")
            seen_skills[name] = where
            desc = fm.get("description", "")
            if not desc:
                err(f"{where}: empty description")
            elif len(desc) > 1024:
                err(f"{where}: description is {len(desc)} chars (max 1024)")
            meta = fm.get("metadata")
            if not isinstance(meta, dict) or not meta.get("library-version"):
                err(f"{where}: metadata.library-version is required")
            elif version and meta["library-version"] != base_version(version):
                err(f"{where}: metadata.library-version {meta['library-version']} != plugin version {version}")
            for md in sdir.rglob("*.md"):
                prose = re.sub(r"^(```|~~~).*?^\1", "", md.read_text(), flags=re.S | re.M)
                prose = re.sub(r"`[^`\n]*`", "", prose)
                for target in re.findall(r"\]\(([^)\s]+)\)", prose):
                    if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                        continue
                    path = target.split("#", 1)[0]
                    if path and not (md.parent / path).exists():
                        err(f"{md.relative_to(ROOT)}: broken relative link {target!r}")
            n_lines = text.count("\n")
            if n_lines > 500:
                err(f"{where}: {n_lines} lines; keep SKILL.md under 500 lines (move details to sibling files)")

    return report()


def report() -> int:
    if errors:
        print("Validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
