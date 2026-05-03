"""Cross-check: for several descendant-style paths, confirm that the
new lazy walker yields the *same set of nodes in the same order* as
the old (system) lxml's _elementpath.py against a deeply nested doc.

Run with:
    PYTHONPATH=src python benchmark/verify_descendant.py
"""
import os
import subprocess
import sys

DOC = b"""\
<root>
  <a>
    <b1>
      <c><leaf/><leaf/></c>
      <d>text<e/></d>
    </b1>
    <b2/>
    <b3>
      <c>text<leaf>x</leaf></c>
    </b3>
  </a>
  <f>
    <g>
      <c>
        <c><leaf/></c>
      </c>
    </g>
  </f>
  <leaf/>
</root>
"""

PATHS = [
    './/*',
    './/leaf',
    './/c',
    './/c/leaf',
    'a//leaf',
    'f//leaf',
    'a/b1//leaf',
    './/c//leaf',
]


def run(use_local):
    env = os.environ.copy()
    if use_local:
        env['PYTHONPATH'] = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
    elif 'PYTHONPATH' in env:
        del env['PYTHONPATH']
    code = """
import sys
from lxml import etree
DOC = %r
PATHS = %r
root = etree.fromstring(DOC)

def signature(elem):
    parent = elem.getparent()
    return (elem.tag, dict(elem.attrib),
            (signature(parent) if parent is not None else None))

for p in PATHS:
    hits = root.findall(p)
    print(p, len(hits))
    for h in hits:
        print('  ', signature(h))
""" % (DOC, PATHS)
    return subprocess.check_output([sys.executable, '-c', code], env=env, text=True)


def main():
    old = run(use_local=False)
    new = run(use_local=True)
    if old == new:
        print('IDENTICAL output for all', len(PATHS), 'paths.')
    else:
        print('=== OLD ===')
        print(old)
        print('=== NEW ===')
        print(new)
        sys.exit(1)


if __name__ == '__main__':
    main()
