#!/usr/bin/env python3
"""Install selected skills; stage copies before replacing existing folders."""
from pathlib import Path
import argparse
import json
import shutil
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]

def overlaps(a, b):
    return a == b or a in b.parents or b in a.parents

def install(source, dest):
    if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
        raise ValueError(f'Unsafe destination: {dest}')
    with tempfile.TemporaryDirectory(prefix='.skill-install-', dir=dest.parent) as temp:
        stage = Path(temp) / 'new'
        backup = Path(temp) / 'old'
        shutil.copytree(source, stage)
        had_old = dest.exists()
        if had_old:
            dest.rename(backup)
        try:
            stage.rename(dest)
        except BaseException:
            if had_old:
                backup.rename(dest)
            raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skills', nargs='*')
    parser.add_argument('--target', required=True)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.all and args.skills:
        parser.error('use skill names OR --all')
    data = json.loads((ROOT / 'skill-manifest.json').read_text(encoding='utf-8'))
    valid = {}
    for item in data['skills']:
        name = item['name']
        if item['path'] != f'skills/{name}/SKILL.md' or '/' in name or '\\' in name or name in ('.', '..'):
            parser.error(f'invalid manifest entry: {name}')
        source = (ROOT / item['path']).parent.resolve()
        if source.parent != (ROOT / 'skills').resolve() or not (source / 'SKILL.md').is_file():
            parser.error(f'invalid source: {name}')
        valid[name] = source
    selected = list(valid) if args.all else list(dict.fromkeys(args.skills))
    if not selected:
        parser.error('provide skill names or --all')
    if any(name not in valid for name in selected):
        parser.error('unknown skill name')
    target = Path(args.target).expanduser().resolve()
    # Check every source, including unselected skills, before any mutation.
    if any(overlaps(target, source) for source in valid.values()):
        parser.error('target must not overlap source skill directories')
    for name in selected:
        dest = target / name
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            parser.error(f'unsafe destination: {dest}')
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)
    for name in selected:
        dest = target / name
        if dest.exists() and not args.force:
            print(f'SKIP {name}: already exists (use --force)')
            continue
        if args.dry_run:
            print(f'PLAN {name} -> {dest}')
            continue
        install(valid[name], dest)
        print(f'INSTALLED {name} -> {dest}')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f'Installation failed: {exc}', file=sys.stderr)
        sys.exit(1)
