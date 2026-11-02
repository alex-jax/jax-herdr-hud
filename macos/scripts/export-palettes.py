#!/usr/bin/env python3
"""Regenerate bundled palettes from the Ubuntu source. Build-time tool only."""
import ast
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from terminal_themes import palettes

# Read the two classic return literals without importing GTK-dependent hud.py.
tree = ast.parse((root / 'hud.py').read_text())
method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'terminal_colors')
variants = []
for node in ast.walk(method):
    if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
        try:
            fg, bg, colors = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        variants.append(dict(foreground=fg, background=bg, cursor=fg, colors=colors))
# ast.walk visits the unconditional light return before the nested dark return.
assert len(variants) == 2
result = dict(palettes())
result['hud'] = dict(name='Hud classic', light=variants[0], dark=variants[1])
(root / 'macos/Sources/HerdrHud/Resources/palettes.json').write_text(json.dumps(result, sort_keys=True))
