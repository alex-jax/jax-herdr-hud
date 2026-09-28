"""Collect VTE's typelib and native library (not supplied by PyInstaller)."""
from PyInstaller.utils.hooks.gi import GiModuleInfo


def hook(hook_api):
    info = GiModuleInfo('Vte', '2.91', hook_api=hook_api)
    if not info.available:
        raise RuntimeError('VTE 2.91 is required for the Mac build')
    binaries, datas, imports = info.collect_typelib_data()
    hook_api.add_binaries(binaries)
    hook_api.add_datas(datas)
    hook_api.add_imports(*imports)
