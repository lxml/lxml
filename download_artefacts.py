#!/usr/bin/python3

import itertools
import json
import logging
import re
import shutil
import datetime

from concurrent.futures import ProcessPoolExecutor as Pool, as_completed
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin

logger = logging.getLogger()

PARALLEL_DOWNLOADS = 6
GITHUB_PACKAGE_URL = "https://github.com/lxml/lxml-wheels"
APPVEYOR_PACKAGE_URL = "https://ci.appveyor.com/api/projects/scoder/lxml"
APPVEYOR_BUILDJOBS_URL = "https://ci.appveyor.com/api/buildjobs"


def find_github_files(version, base_package_url=GITHUB_PACKAGE_URL):
    url = f"{base_package_url}/releases/tag/lxml-{version}"
    with urlopen(url) as p:
        page = p.read().decode()

    for wheel_url, _ in itertools.groupby(sorted(re.findall(r'href="([^"]+\.whl)"', page))):
        yield urljoin(base_package_url, wheel_url)


def find_appveyor_files(version, base_package_url=APPVEYOR_PACKAGE_URL, base_job_url=APPVEYOR_BUILDJOBS_URL):
    url = f"{base_package_url}/history?recordsNumber=20"
    with urlopen(url) as p:
        builds = json.load(p)["builds"]

    tag = f"lxml-{version}"
    for build in builds:
        if build['isTag'] and build['tag'] == tag:
            build_id = build['buildId']
            break
    else:
        logger.warning(f"No appveyor build found for tag '{tag}'")
        return

    build_url = f"{base_package_url}/builds/{build_id}"
    with urlopen(build_url) as p:
        jobs = json.load(p)["build"]["jobs"]

    for job in jobs:
        artifacts_url = f"{base_job_url}/{job['jobId']}/artifacts/"

        with urlopen(artifacts_url) as p:
            for artifact in json.load(p):
                yield urljoin(artifacts_url, artifact['fileName'])


def download1(wheel_url, dest_dir):
    wheel_name = wheel_url.rsplit("/", 1)[1]
    logger.info(f"Downloading {wheel_url} ...")
    with urlopen(wheel_url) as w:
        file_path = dest_dir / wheel_name
        if (file_path.exists()
                and "Content-Length" in w.headers
                and file_path.stat().st_size == int(w.headers["Content-Length"])):
            logger.info(f"Already have {wheel_name}")
        else:
            temp_file_path = file_path.with_suffix(".tmp")
            try:
                with open(temp_file_path, "wb") as f:
                    shutil.copyfileobj(w, f)
            except:
                if temp_file_path.exists():
                    temp_file_path.unlink()
                raise
            else:
                temp_file_path.replace(file_path)
                logger.info(f"Finished downloading {wheel_name}")
    return wheel_name


def download(urls, dest_dir, jobs=PARALLEL_DOWNLOADS):
    with Pool(max_workers=jobs) as pool:
        futures = [pool.submit(download1, url, dest_dir) for url in urls]
        try:
            for future in as_completed(futures):
                wheel_name = future.result()
                yield wheel_name
        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            raise


def dedup(it):
    seen = set()
    for value in it:
        if value not in seen:
            seen.add(value)
            yield value


def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    from itertools import cycle, islice
    num_active = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            # Remove the iterator we just exhausted from the cycle.
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))


def main(*args):
    if not args:
        print("Please pass the version to download")
        return

    version = args[0]
    dest_dir = Path("dist") / version
    if not dest_dir.is_dir():
        dest_dir.mkdir()

    start_time = datetime.datetime.now().replace(microsecond=0)
    urls = roundrobin(*map(dedup, [
        find_github_files(version),
        find_appveyor_files(version),
    ]))
    count = sum(1 for _ in enumerate(download(urls, dest_dir)))
    duration = datetime.datetime.now().replace(microsecond=0) - start_time
    logger.info(f"Downloaded {count} files in {duration}.")


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)-15s  %(message)s",
    )
    main(*sys.argv[1:])
