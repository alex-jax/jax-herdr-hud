#!/usr/bin/python3
"""Build a local classic snap from authenticated Ubuntu 26.04 APT packages.

Alternative to Snapcraft for machines without a privileged build provider.
Never installs packages or changes the host package database. Requires python3-apt,
python3-yaml, dpkg-deb, glib-compile-schemas and snap (pack needs no daemon).
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import apt
import yaml

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
import importlib.util
spec = importlib.util.spec_from_file_location('stage', SOURCE / 'packaging/stage.py')
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


def main():
    release = platform.freedesktop_os_release()
    if release.get('ID') != 'ubuntu' or release.get('VERSION_ID') != '26.04' or platform.machine() != 'x86_64':
        raise SystemExit('Rootless build requires Ubuntu 26.04 x86-64. Use Snapcraft elsewhere.')
    recipe = yaml.safe_load((SOURCE / 'snap/snapcraft.yaml').read_text())
    work = SOURCE / 'build/rootless'
    archives = work / 'archives'
    root = work / 'prime'
    archives.mkdir(parents=True, exist_ok=True)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    cache = apt.Cache()
    chosen = {}

    def include(version):
        name = version.package.name
        if name in chosen:
            if chosen[name].version != version.version:
                raise RuntimeError('Conflicting versions for ' + name)
            return
        if not any(origin.trusted and origin.origin == 'Ubuntu' for origin in version.origins):
            raise RuntimeError('Refusing non-Ubuntu/untrusted package: ' + name)
        chosen[name] = version
        for group in version.get_dependencies('PreDepends', 'Depends'):
            alternatives = group.or_dependencies
            # Prefer a version already selected, then the first dependency with
            # a candidate satisfying APT's version constraint.
            targets = [v for dep in alternatives for v in dep.target_versions
                       if v.architecture in ('amd64', 'all') and v.package.candidate and v.version == v.package.candidate.version]
            satisfied = next((v for v in targets if v.package.name in chosen), None)
            target = satisfied or next(iter(targets), None)
            if target is None:
                raise RuntimeError('Cannot resolve ' + str(group) + ' for ' + name)
            include(target)

    for name in recipe['parts']['hud']['stage-packages']:
        include(cache[name].candidate)
    print(f'Downloading/extracting {len(chosen)} Ubuntu runtime packages', flush=True)
    inventory = []
    for name, version in sorted(chosen.items()):
        archive = Path(version.fetch_binary(str(archives)))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != version.record['SHA256']:
            raise RuntimeError('Archive checksum mismatch: ' + name)
        subprocess.run(['dpkg-deb', '-x', str(archive), str(root)], check=True)
        inventory.append({'package': name, 'version': version.version,
                          'source': version.source_name, 'source_version': version.source_version,
                          'sha256': digest, 'uri': version.uri})
    doc = staging.stage(root)
    (doc / 'runtime-packages.json').write_text(json.dumps(inventory, indent=2) + '\n')
    metadata = {key: recipe[key] for key in ('name', 'base', 'version', 'summary', 'description', 'grade', 'confinement', 'license')}
    metadata.update(architectures=['amd64'], apps={recipe['name']: {'command': 'usr/bin/herdr-hud'}})
    (root / 'meta/snap.yaml').write_text(yaml.safe_dump(metadata, sort_keys=False))
    # No hooks, services or per-user installation scripts enter the artifact.
    out = SOURCE / 'dist'
    out.mkdir(exist_ok=True)
    subprocess.run(['snap', 'pack', '--check-skeleton', str(root)], check=True)
    subprocess.run(['snap', 'pack', str(root), str(out)], check=True)
    shutil.copy2(doc / 'runtime-packages.json', out / 'runtime-packages.json')
    print('Local build complete; snap installation/lifecycle tests still require a disposable VM.', flush=True)


if __name__ == '__main__':
    main()
