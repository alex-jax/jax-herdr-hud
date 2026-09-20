#!/usr/bin/python3
"""Record Snapcraft runtime package metadata from its build manifest."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
# Snapcraft writes a complete manifest during packing; keep a build-time package
# inventory as well. The rootless builder writes a richer authenticated inventory.
import subprocess
entries = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\t${Version}\t${source:Package}\t${source:Version}\n'], text=True)
rows = [dict(zip(('package', 'version', 'source', 'source_version'), line.split('\t')))
        for line in entries.splitlines() if (root / 'usr/share/doc' / line.split('\t')[0]).exists()]
out = root / 'usr/share/doc/herdr-hud/runtime-packages.json'
out.write_text(json.dumps(rows, indent=2) + '\n')
