"""Partition the full host suite by file across isolated CI runners."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def shard_files(root, shard, total):
    if total < 1 or not 0 <= shard < total:
        raise ValueError('Shard must be between zero and total minus one')
    files = set((root / 'tests').rglob('test_*.py')) | set((root / 'tests').rglob('*_test.py'))
    return sorted(files)[shard::total]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--total', type=int, required=True)
    args = parser.parse_args()
    files = shard_files(ROOT, args.shard, args.total)
    if not files:
        raise SystemExit('This shard has no test files')
    result = subprocess.run([sys.executable, '-m', 'pytest', *(str(p.relative_to(ROOT)) for p in files)], cwd=ROOT)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
