#!/usr/bin/env python3
"""Safety guard for README V2.

README V2 is already a complete replacement file. The legacy patcher used to
prepend duplicate card blocks. This guard refuses that destructive operation.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2_MARKER = '<!-- MUHAMMAD SOHAIL | PROFILE README V2 -->'


def patch(old: str) -> str:
    if V2_MARKER in old:
        return old
    raise ValueError('README V2 is a full replacement; back up your README and copy the provided README.md instead of running the legacy patcher.')


def main() -> None:
    p = ROOT / 'README.md'
    content = p.read_text(encoding='utf-8')
    patch(content)
    print('README V2 detected and preserved. No patch or duplicate cards added.')


if __name__ == '__main__':
    main()
