#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "skill-manifest.json"
errors = []

if not MANIFEST.exists():
    errors.append("skill-manifest.json is missing")
    manifest = {"skills": []}
else:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"skill-manifest.json is invalid JSON: {exc}")
        manifest = {"skills": []}

manifest_entries = manifest.get("skills", [])
manifest_names = [item.get("name") for item in manifest_entries]
if len(manifest_names) != len(set(manifest_names)):
    errors.append("skill-manifest.json contains duplicate skill names")

skill_files = sorted(SKILLS.glob("*/SKILL.md"))
actual_names = [path.parent.name for path in skill_files]

if set(manifest_names) != set(actual_names):
    missing_in_manifest = sorted(set(actual_names) - set(manifest_names))
    missing_on_disk = sorted(set(manifest_names) - set(actual_names))
    if missing_in_manifest:
        errors.append("skills missing from manifest: " + ", ".join(missing_in_manifest))
    if missing_on_disk:
        errors.append("manifest entries missing on disk: " + ", ".join(missing_on_disk))

for item in manifest_entries:
    name = item.get("name", "")
    path = item.get("path", "")
    expected = f"skills/{name}/SKILL.md"
    if path != expected:
        errors.append(f"manifest path for {name!r} must be {expected!r}, got {path!r}")
    for dep in item.get("recommended_with", []):
        if dep not in manifest_names:
            errors.append(f"manifest dependency {name!r} -> {dep!r} does not exist")
        if dep == name:
            errors.append(f"manifest skill {name!r} recommends itself")

for path in skill_files:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{path}: missing YAML front matter")
        continue

    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, flags=re.S)
    if not match:
        errors.append(f"{path}: invalid front matter")
        continue

    fm, body = match.groups()
    meta = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()

    for key in ("name", "description"):
        if not meta.get(key):
            errors.append(f"{path}: missing front matter field '{key}'")

    folder = path.parent.name
    if meta.get("name") and meta["name"] != folder:
        errors.append(f"{path}: name '{meta['name']}' must match folder '{folder}'")

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", folder):
        errors.append(f"{path}: folder name must be kebab-case")

    if not re.fullmatch(r"\d+\.\d+\.\d+", meta.get("version", "").strip('"\'')):
        errors.append(f"{path}: version must use semantic versioning, e.g. 1.0.0")

    if "## Anti-Patterns" not in body:
        errors.append(f"{path}: missing '## Anti-Patterns' section")

    if not body.strip():
        errors.append(f"{path}: skill body is empty")

    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body):
        if "://" in link or link.startswith("#"):
            continue
        target = link.split("#", 1)[0]
        if target and not (path.parent / target).exists():
            errors.append(f"{path}: broken local reference: {link}")

if not skill_files:
    errors.append("No skills found")

required_docs = [
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/core-vs-extension.md",
    "extensions/README.md",
]
for rel in required_docs:
    if not (ROOT / rel).exists():
        errors.append(f"required repository file is missing: {rel}")

if errors:
    print("Skill validation failed:\n")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(f"OK: validated {len(skill_files)} skills and manifest consistency")
