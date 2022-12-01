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


def main():
    stats = get_pyver_stats()
    for version, count in sorted(aggregate(stats).items()):
        print(f"{version:4}: {count:-12.1f} / day")


if __name__ == '__main__':
    main()
