"""
Benchmark for the ElementPath implementation behind
_Element.find/findall/iterfind/findtext.

Run on a build of lxml: it just times the public API, so it works for
both the old Python _elementpath.py and the new Cython _elementpath.pxi.

Usage:
    python bench_elementpath.py [iterations]

Default iterations: tuned per-case so each run takes ~0.2s.
"""
import sys
import time
from lxml import etree


# A reasonably-sized test document with mixed shapes:
# - many siblings of the same tag
# - nested tags
# - attributes
# - mixed text content
# - a simple namespace
def make_doc(n=200, m=20):
    parts = ['<root xmlns:ns="http://example.com/ns">']
    for i in range(n):
        parts.append(f'<item id="{i}" type="{"odd" if i&1 else "even"}">')
        parts.append(f'<name>item-{i}</name>')
        for j in range(m):
            parts.append(
                f'<child key="k{j}" pos="{j}">child-{i}-{j}'
                f'<ns:tag>{i*j}</ns:tag></child>')
        parts.append('</item>')
    parts.append('</root>')
    return etree.fromstring(''.join(parts).encode('utf-8'))


def bench(label, fn, iters):
    # Warm-up
    for _ in range(3):
        fn()
    t0 = time.perf_counter()
    for _ in range(iters):
        fn()
    t1 = time.perf_counter()
    total = t1 - t0
    per = total / iters * 1e6  # microseconds
    print(f'  {label:<48s} {iters:>7d} iters  {total*1000:8.2f} ms  {per:8.2f} us/op')
    return per


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f'lxml {etree.LXML_VERSION}  python {sys.version.split()[0]}')
    print(f'iterations per case: {iters}')

    root = make_doc(n=200, m=20)
    namespaces = {'ns': 'http://example.com/ns'}

    cases = [
        ('findall("item")',                  lambda: root.findall('item')),
        ('findall("*")',                     lambda: root.findall('*')),
        ('findall(".//child")',              lambda: root.findall('.//child')),
        ('findall(".//*")',                  lambda: root.findall('.//*')),
        ('findall("item/child")',            lambda: root.findall('item/child')),
        ('findall("item/name")',             lambda: root.findall('item/name')),
        ('find("item")',                     lambda: root.find('item')),
        ('find(".//child")',                 lambda: root.find('.//child')),
        ('find("item/name")',                lambda: root.find('item/name')),
        ('findtext("item/name")',            lambda: root.findtext('item/name')),
        ('findall("item[@id]")',             lambda: root.findall('item[@id]')),
        ('findall("item[@type=\\"odd\\"]")',  lambda: root.findall('item[@type="odd"]')),
        ('findall("item[1]")',               lambda: root.findall('item[1]')),
        ('findall("item[last()]")',          lambda: root.findall('item[last()]')),
        ('findall("item[name]")',            lambda: root.findall('item[name]')),
        ('findall(".//ns:tag", namespaces)', lambda: root.findall('.//ns:tag', namespaces)),
        ('findall(".//child[@key=\\"k5\\"]")', lambda: root.findall('.//child[@key="k5"]')),
        ('iterfind(".//child") consume',     lambda: list(root.iterfind('.//child'))),
        ('miss: findall("nope")',            lambda: root.findall('nope')),
    ]

    print()
    for label, fn in cases:
        bench(label, fn, iters)


if __name__ == '__main__':
    main()
