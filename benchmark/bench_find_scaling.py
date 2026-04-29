"""Scale the document and measure find('item/name') to demonstrate
that the new implementation's cost is O(items * children-per-item)
while the old implementation's cost is O(1) (first item, first name)."""
import time
from lxml import etree


def make_doc(n_items, m_children_per_item):
    parts = ['<root>']
    for i in range(n_items):
        parts.append(f'<item id="{i}">')
        parts.append(f'<name>n{i}</name>')
        for j in range(m_children_per_item):
            parts.append(f'<child k="{j}"/>')
        parts.append('</item>')
    parts.append('</root>')
    return etree.fromstring(''.join(parts).encode('utf-8'))


def bench_find(root, iters=50000):
    # Warm-up
    for _ in range(100):
        root.find('item/name')
    t0 = time.perf_counter()
    for _ in range(iters):
        root.find('item/name')
    t1 = time.perf_counter()
    return (t1 - t0) / iters * 1e6


def bench_findfirst_descendant(root, iters=20000):
    for _ in range(100):
        root.find('.//child')
    t0 = time.perf_counter()
    for _ in range(iters):
        root.find('.//child')
    t1 = time.perf_counter()
    return (t1 - t0) / iters * 1e6


def main():
    print(f'lxml {etree.LXML_VERSION}')
    print()
    print(f'find("item/name") -- doc grows in items, name is always item[0]/name')
    print(f'{"items":>8s} {"children/item":>14s} {"us/op":>10s}')
    for n_items in [1, 10, 50, 100, 200, 500, 1000]:
        root = make_doc(n_items, m_children_per_item=20)
        per = bench_find(root)
        print(f'{n_items:>8d} {20:>14d} {per:>10.2f}')

    print()
    print(f'find("item/name") -- doc grows in children-per-item')
    print(f'{"items":>8s} {"children/item":>14s} {"us/op":>10s}')
    for m in [0, 5, 10, 20, 50, 100]:
        root = make_doc(200, m_children_per_item=m)
        per = bench_find(root)
        print(f'{200:>8d} {m:>14d} {per:>10.2f}')

    print()
    print(f'find(".//child") -- depth-first, first match is item[0]/child[0]')
    print(f'{"items":>8s} {"children/item":>14s} {"us/op":>10s}')
    for n_items in [1, 10, 50, 100, 200, 500, 1000]:
        root = make_doc(n_items, m_children_per_item=20)
        per = bench_findfirst_descendant(root)
        print(f'{n_items:>8d} {20:>14d} {per:>10.2f}')


if __name__ == '__main__':
    main()
