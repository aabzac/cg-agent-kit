#!/usr/bin/env python3
"""Validate this kit's deliberately small, portable skill format (no dependencies)."""
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys


def load_sync():
    spec = importlib.util.spec_from_file_location('cg_kit_sync', Path(__file__).resolve().with_name('sync.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_paths(root, sources):
    """List kit sources as the next commit would contain them, including files not added yet."""
    listing = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others',
                              '--exclude-standard', '--', *sources], capture_output=True, timeout=60)
    if listing.returncode:
        raise RuntimeError(listing.stderr.decode('utf-8', errors='replace').strip())
    names = set(listing.stdout.decode('utf-8').split('\0')) - {''}
    return sorted(name for name in names if os.path.lexists(root / name))


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    sync = load_sync()
    try:
        # The same rules as sync.py, so a layout that would break consumer updates fails here first.
        names = source_paths(root, sync.KIT_SOURCES)
        sync.check_kit_paths(names)
        errors += [f'{name}: kit sources must be regular files, not links'
                   for name in names if (root / name).is_symlink()]
    except (OSError, RuntimeError, UnicodeError, subprocess.SubprocessError, sync.SyncError) as exc:
        errors.append(f'Kit sources: {exc}')
    skills = sorted((root / 'skills').glob('*/SKILL.md'))
    if not skills:
        errors.append('No skills found')
    for path in skills:
        text = path.read_text(encoding='utf-8')
        lines = text.splitlines()
        if not lines or lines[0] != '---' or '---' not in lines[1:]:
            errors.append(f'{path.parent.name}: missing YAML frontmatter')
            continue
        end = lines.index('---', 1)
        fields = {}
        for line in lines[1:end]:
            key, sep, value = line.partition(':')
            if not sep or key not in {'name', 'description'} or key in fields:
                errors.append(f'{path.parent.name}: use only name and description, one line each')
            fields[key] = value.strip()
        name = fields.get('name', '')
        if name != path.parent.name or len(name) > 64 or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
            errors.append(f'{path.parent.name}: invalid or mismatched name')
        description = fields.get('description', '')
        if not description or len(description) > 1024:
            errors.append(f'{name}: description must be 1..1024 characters')
        if ': ' in description and not (description.startswith('"') and description.endswith('"')):
            errors.append(f'{name}: quote a description containing a colon')
        if len(lines) >= 500 or not '\n'.join(lines[end + 1:]).strip():
            errors.append(f'{name}: empty or overly long skill body')
        if re.search(r'\bTODO\b|\[INSERT', text):
            errors.append(f'{name}: unfinished template')
        for link in re.findall(r'\]\(([^)]+)\)', text):
            if '://' not in link and not link.startswith('#'):
                target = (path.parent / link.split('#')[0]).resolve()
                if not target.is_relative_to(path.parent.resolve()) or not target.exists():
                    errors.append(f'{name}: missing or external local resource {link}')
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f'OK: {len(skills)} portable skills and kit sources')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
