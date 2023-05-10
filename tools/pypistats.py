#!/usr/bin/env python3
import json
from collections import defaultdict
from urllib.request import urlopen
import ssl

PACKAGE = "lxml"


def get_stats(stats_type, package=PACKAGE, period="month"):
    stats_url = f"https://www.pypistats.org/api/packages/{package}/{stats_type}?period={period}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urlopen(stats_url, context=ctx) as stats:
        data = json.load(stats)
    return data


def aggregate(stats):
    counts = defaultdict(int)
    days = defaultdict(int)
    for entry in stats['data']:
        category = entry['category']
        counts[category] += entry['downloads']
        days[category] += 1
    return {category: counts[category] / days[category] for category in counts}


def version_sorter(version_and_count):
    version = version_and_count[0]
    return tuple(map(int, version.split("."))) if version.replace(".", "").isdigit() else (2**32,)


def system_sorter(name_and_count):
    order = ('linux', 'windows', 'darwin')
    system = name_and_count[0]
    try:
        return order.index(system.lower())
    except ValueError:
        return len(order)


def print_agg_stats(stats, sort_key=None):
    total = sum(stats.values())
    max_len = max(len(category) for category in stats)
    agg_sum = 0.0
    for category, count in sorted(stats.items(), key=sort_key, reverse=True):
        agg_sum += count
        print(f"  {category:{max_len}}: {count:-12.1f} / day ({agg_sum / total * 100:-5.1f}%)")


def main():
    import sys
    package_name = sys.argv[1] if len(sys.argv) > 1 else PACKAGE

    counts = get_stats("python_minor", package=package_name)
    stats = aggregate(counts)
    print("Downloads by Python version:")
    print_agg_stats(stats, sort_key=version_sorter)

    print()
    counts = get_stats("system", package=package_name)
    stats = aggregate(counts)
    print("Downloads by system:")
    print_agg_stats(stats, sort_key=system_sorter)

    total = sum(stats.values())
    days = {"month": 30, "week": 7, "day": 1}
    print(f"Total downloads: {total * days['month']:-12,.1f}")


if __name__ == '__main__':
    main()
