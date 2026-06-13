"""Run bench_elementpath.py against both the system lxml (old) and the
local rebuild (new) and print a side-by-side table."""
import os
import re
import subprocess
import sys

ROW = re.compile(r'^\s+(.+?)\s+\d+ iters\s+[\d.]+ ms\s+([\d.]+) us/op')

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_LXML_SRC = os.path.normpath(os.path.join(HERE, '..', 'src'))
BENCH_SCRIPT = os.path.join(HERE, 'bench_elementpath.py')


def run(use_local_build):
    env = os.environ.copy()
    if use_local_build:
        env['PYTHONPATH'] = LOCAL_LXML_SRC
    elif 'PYTHONPATH' in env:
        del env['PYTHONPATH']
    out = subprocess.check_output(
        [sys.executable, BENCH_SCRIPT, sys.argv[1] if len(sys.argv) > 1 else '5000'],
        env=env, text=True)
    return out


def parse(out):
    rows = {}
    for line in out.splitlines():
        m = ROW.match(line)
        if m:
            label = m.group(1).strip()
            us = float(m.group(2))
            rows[label] = us
    return rows


def main():
    print('Running system lxml (old _elementpath.py) ...')
    old_out = run(use_local_build=False)
    print('Running local lxml (new Cython pxi) ...')
    new_out = run(use_local_build=True)

    old = parse(old_out)
    new = parse(new_out)

    print()
    print(f'{"case":<48s} {"old us/op":>12s} {"new us/op":>12s} {"speedup":>10s}')
    print('-' * 86)
    for label in old:
        if label not in new:
            continue
        o, n = old[label], new[label]
        ratio = o / n if n else float('inf')
        marker = '++' if ratio >= 2 else '+' if ratio > 1.05 else '-' if ratio < 0.95 else ''
        print(f'{label:<48s} {o:>12.2f} {n:>12.2f} {ratio:>9.2f}x {marker}')


if __name__ == '__main__':
    main()
