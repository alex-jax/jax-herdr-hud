#!/usr/bin/env python3
"""Reject non-relocatable or wrong-architecture macOS app bundles."""
import argparse
import json
from pathlib import Path
import plistlib
import subprocess

MACHO = {b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}


def audit(bundle):
    bundle = bundle.resolve()
    info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
    assert info['LSMinimumSystemVersion'] == '26.0', info
    count = 0
    for path in bundle.rglob('*'):
        if path.is_symlink():
            assert path.resolve().is_relative_to(bundle), f'External symlink: {path}'
        if not path.is_file() or path.is_symlink():
            continue
        with path.open('rb') as stream:
            if stream.read(4) not in MACHO:
                continue
        count += 1
        arches = subprocess.check_output(['lipo', '-archs', str(path)], text=True).split()
        assert arches == ['arm64'], f'{path}: {arches}'
        dependencies = subprocess.check_output(['otool', '-L', str(path)], text=True)
        for line in dependencies.splitlines()[1:]:
            dependency = line.strip().split(' (', 1)[0]
            assert dependency.startswith(('@rpath/', '@loader_path/', '@executable_path/',
                                          '/System/Library/', '/usr/lib/')), f'{path}: {dependency}'
        loads = subprocess.check_output(['otool', '-l', str(path)], text=True)
        lines = loads.splitlines()
        for index, line in enumerate(lines):
            if line.strip() == 'cmd LC_RPATH':
                rpath = lines[index + 2].strip().split(' ')[1]
                assert rpath.startswith(('@loader_path', '@executable_path')), f'{path}: {rpath}'
            if line.strip().startswith(('minos ', 'version ')):
                # The deployment minimum may be older, but never newer than 26.0.
                if any('LC_BUILD_VERSION' in s or 'LC_VERSION_MIN_MACOSX' in s
                       for s in lines[max(0, index - 4):index]):
                    version = tuple(map(int, line.split()[1].split('.')))
                    assert version[:2] <= (26, 0), f'{path}: minimum {version}'
    assert count, 'No Mach-O executables found'
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
    return {'bundle': bundle.name, 'mach_o_files': count, 'architecture': 'arm64',
            'minimum_macos': '26.0', 'signature': 'ad-hoc; not notarized'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.bundle), indent=2))
