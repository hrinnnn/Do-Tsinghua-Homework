#!/usr/bin/env python3
"""Install these skills into a chosen Codex skill directory on any OS."""
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('do-tsinghua-homework', 'markdown-report-pdf', 'writer-tsinghua-report')


def files(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts
            and p.name != '.DS_Store' and p.suffix != '.pyc'}


def install(dest, names, replace=False, dry_run=False):
    sources = {name: ROOT / 'skills' / name for name in names}
    for name, source in sources.items():
        if not (source / 'SKILL.md').is_file():
            raise ValueError(f'Skill source missing: {name}')
    changes = []
    for name, source in sources.items():
        target = dest / name
        if target.is_dir() and files(source) == files(target):
            print(f'Already up to date: {name}')
            continue
        if target.exists() or target.is_symlink():
            if not replace:
                raise FileExistsError(f'{target} already exists and differs. Use --replace to back it up and update.')
        changes.append(name)
    if dry_run:
        for name in changes:
            print(f'Would install: {dest / name}')
        return
    if not changes:
        return
    dest.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = dest.parent / 'skill-backups' / timestamp
    with tempfile.TemporaryDirectory(prefix='.skills-install-', dir=dest.parent) as temporary:
        staging = Path(temporary)
        for name in changes:
            shutil.copytree(sources[name], staging / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        for name in changes:
            target = dest / name
            previous = backup / name
            existed = target.exists() or target.is_symlink()
            if existed and not replace:
                raise FileExistsError(f'{target} appeared during installation; no files overwritten.')
            if existed:
                backup.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(previous))
            try:
                shutil.move(str(staging / name), str(target))
            except Exception:
                if existed and not target.exists():
                    shutil.move(str(previous), str(target))
                raise
            print(f'Installed: {target}')
            if existed:
                print(f'Backup: {previous}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    home = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
    parser.add_argument('--dest', type=Path, default=home / 'skills', help='Destination skills directory')
    parser.add_argument('--skills', choices=SKILLS, nargs='+', default=list(SKILLS))
    parser.add_argument('--replace', action='store_true', help='Back up existing different skills and replace them')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        install(args.dest.expanduser().resolve(), list(dict.fromkeys(args.skills)), args.replace, args.dry_run)
    except (ValueError, FileExistsError) as error:
        parser.exit(1, f'{error}\n')
    if not args.dry_run:
        print('Skills are ready. Start your next Codex turn to use them.')


if __name__ == '__main__':
    main()
