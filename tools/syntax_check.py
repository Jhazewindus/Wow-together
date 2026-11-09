"""Compile every declared addon source with Lua 5.1 without executing it."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
from build_release import toc_sources


def main():
    root = Path(__file__).resolve().parents[1]
    load = LuaRuntime(unpack_returned_tuples=True).eval('loadstring')
    count = 0
    for package in sorted(root.glob('WowTogether*')):
        if not package.is_dir() or not (package / (package.name + '.toc')).is_file():
            continue
        for name in toc_sources(package):
            result = load((package / name).read_text(), '@' + str(package / name))
            if isinstance(result, tuple):
                raise ValueError(result[1])
            count += 1
    print(f'All {count} Lua files compile under Lua 5.1')


if __name__ == '__main__':
    main()
