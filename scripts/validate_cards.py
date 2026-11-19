#!/usr/bin/env python3
"""Validate card XML and basic self-containment/security constraints."""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
files=sorted((ROOT/'cards').glob('*.svg'))
if not files:
    raise SystemExit('No cards found')
for f in files:
    s=f.read_text(encoding='utf-8')
    ET.fromstring(s)
    if '<script' in s.lower() or '<foreignObject' in s or re.search(r'<image\b[^>]+href="https?://',s):
        raise SystemExit(f'Unsafe SVG contents: {f}')
    if 'data:font/woff;base64,' not in s:
        raise SystemExit(f'Missing embedded WOFF font: {f}')
    if 'prefers-reduced-motion' not in s:
        raise SystemExit(f'Missing reduced-motion CSS: {f}')
    if f.stat().st_size>2_000_000:
        raise SystemExit(f'SVG exceeds 2 MB: {f}')
print(f'Validated {len(files)} self-contained SVG files')
