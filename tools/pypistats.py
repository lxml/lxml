#!/usr/bin/env python3
import json
from collections import defaultdict
from urllib.request import urlopen
import ssl

PACKAGE = "lxml"


def get_pyver_stats(package=PACKAGE, period="month"):
    stats_url = f"https://www.pypistats.org/api/packages/{package}/python_minor?period={period}"

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


def main():
    import sys
    package_name = sys.argv[1] if len(sys.argv) > 1 else PACKAGE

    counts = get_pyver_stats(package=package_name)
    stats = aggregate(counts)
    total = sum(stats.values())

    agg_sum = 0.0
    for version, count in sorted(stats.items(), key=version_sorter):
        agg_sum += count
        print(f"{version:4}: {count:-12.1f} / day ({agg_sum / total * 100:-5.1f}%)")


if __name__ == '__main__':
    main()
