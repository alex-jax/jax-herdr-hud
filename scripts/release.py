#!/usr/bin/python3
"""Assemble reviewable local release artifacts. Never uploads or registers names."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from app_info import VERSION, SNAP_NAME, EXTENSION_UUID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snap', type=Path, help='Snapcraft artifact to copy into dist')
    parser.add_argument('--output', type=Path, default=SOURCE / 'dist',
                        help='Release artifact directory')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.snap:
        target = out / args.snap.name
        if args.snap.resolve() != target.resolve():
            shutil.copy2(args.snap, target)
    metadata = json.loads((SOURCE / 'extension/metadata.json').read_text())
    if metadata['uuid'] != EXTENSION_UUID:
        raise SystemExit('Extension UUID differs from app_info.py')
    zip_path = out / (EXTENSION_UUID + '.shell-extension.zip')
    files = {name: SOURCE / 'extension' / name for name in ('extension.js', 'metadata.json', 'stylesheet.css')}
    files.update({'LICENSE': SOURCE / 'LICENSE', 'Alex-Finn-MIT.txt': SOURCE / 'licenses/Alex-Finn-MIT.txt'})
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    prefix = 'jax-herdr-hud-' + VERSION
    source_files = [p for p in SOURCE.iterdir() if p.is_file() and
                    (p.suffix in ('.py', '.md') or p.name in ('LICENSE', '.gitignore'))]
    for folder in ('extension', 'packaging', 'scripts', 'snap', 'tests', 'licenses', 'docs'):
        source_files.extend(p for p in (SOURCE / folder).rglob('*') if p.is_file()
                            and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.log'))
    with (out / (prefix + '-source.tar.gz')).open('wb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for path in sorted(source_files):
                    info = archive.gettarinfo(str(path), prefix + '/' + str(path.relative_to(SOURCE)))
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    with path.open('rb') as source:
                        archive.addfile(info, source)
    shutil.copytree(SOURCE / 'docs', out / 'review-materials', dirs_exist_ok=True)
    for name in ('LICENSE', 'NOTICE.md'):
        shutil.copy2(SOURCE / name, out / name)
    artifacts = [p for p in out.rglob('*') if p.is_file() and p.name != 'SHA256SUMS']
    checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' +
                        str(p.relative_to(out)) + '\n' for p in sorted(artifacts))
    (out / 'SHA256SUMS').write_text(checksums)
    print('Prepared extension ZIP, project source, review materials and checksums in ' + str(out))


if __name__ == '__main__':
    main()
