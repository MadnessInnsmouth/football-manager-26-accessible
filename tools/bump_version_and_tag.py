from __future__ import annotations
import argparse
import re
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / 'VERSION'


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding='utf-8').strip()
    return '0.1.0'


def write_version(version: str) -> None:
    VERSION_FILE.write_text(version + '\n', encoding='utf-8')


def bump_version(version: str, bump: str) -> str:
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
    if not m:
        return '0.1.0'
    major, minor, patch = map(int, m.groups())
    if bump == 'major':
        return f'{major + 1}.0.0'
    if bump == 'minor':
        return f'{major}.{minor + 1}.0'
    return f'{major}.{minor}.{patch + 1}'


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--bump', choices=['patch', 'minor', 'major'], default='patch')
    args = parser.parse_args()

    current = read_version()
    new_version = bump_version(current, args.bump)
    write_version(new_version)
    run('git', 'add', 'VERSION')
    run('git', 'commit', '-m', f'chore: release v{new_version}')
    run('git', 'tag', f'v{new_version}')
    print(f'Tag created: v{new_version} at {datetime.utcnow().isoformat()}Z')


if __name__ == '__main__':
    main()
