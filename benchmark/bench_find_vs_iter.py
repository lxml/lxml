"""find()/findall() vs iterchildren()/iterdescendants() head-to-head.

Both are lxml's native C-level paths now: iterchildren is a long-standing
C iterator, and find/findall after the cython-elementpath rewrite are a
C tokenizer plus the lazy DFS cursor walker.

Run with:
    PYTHONPATH=src python benchmark/bench_find_vs_iter.py
"""
import sys
import time
from lxml import etree


def make_doc(n=200, m=20):
    parts = ['<root xmlns:ns="http://example.com/ns">']
    for i in range(n):
        parts.append(f'<item id="{i}" type="{"odd" if i&1 else "even"}">')
        parts.append(f'<name>n{i}</name>')
        for j in range(m):
            parts.append(f'<child k="k{j}" pos="{j}">'
                         f'<ns:tag>{i*j}</ns:tag></child>')
        parts.append('</item>')
    parts.append('</root>')
    return etree.fromstring(''.join(parts).encode('utf-8'))


def bench(label, fn, iters):
    for _ in range(100):
        fn()
    t0 = time.perf_counter()
    for _ in range(iters):
        fn()
    t1 = time.perf_counter()
    return (t1 - t0) / iters * 1e6


def main():
    print(f'lxml {etree.LXML_VERSION}  python {sys.version.split()[0]}')
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    root = make_doc(n=200, m=20)
    item0 = root[0]

    cases = [
        # ------ first-match (find vs next(iter...)) ------
        ('first-child  find("item")',
            lambda: root.find('item')),
        ('first-child  next(iterchildren("item"))',
            lambda: next(root.iterchildren('item'), None)),
        ('first-child  next(iterchildren("*"))',
            lambda: next(root.iterchildren(), None)),
        ('first-child  find("*")',
            lambda: root.find('*')),

        ('first-desc   find(".//child")',
            lambda: root.find('.//child')),
        ('first-desc   next(iterdescendants("child"))',
            lambda: next(root.iterdescendants('child'), None)),

        ('two-step     find("item/name")',
            lambda: root.find('item/name')),
        ('two-step     next(iterchildren("name") on first item)',
            lambda: next(item0.iterchildren('name'), None)),

        # ------ all-matches (findall vs list(iter...)) ------
        ('all-children findall("item")',
            lambda: root.findall('item')),
        ('all-children list(iterchildren("item"))',
            lambda: list(root.iterchildren('item'))),
        ('all-children findall("*")',
            lambda: root.findall('*')),
        ('all-children list(iterchildren())',
            lambda: list(root.iterchildren())),

        ('all-desc     findall(".//child")',
            lambda: root.findall('.//child')),
        ('all-desc     list(iterdescendants("child"))',
            lambda: list(root.iterdescendants('child'))),
    ]

    print(f'iterations per case: {iters}')
    print()
    print(f'{"case":<55s} {"us/op":>10s}')
    print('-' * 70)
    for label, fn in cases:
        per = bench(label, fn, iters)
        print(f'{label:<55s} {per:>10.2f}')


if __name__ == '__main__':
    main()
