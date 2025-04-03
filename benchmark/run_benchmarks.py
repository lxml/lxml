import collections
import io
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


BENCHMARKS_DIR = pathlib.Path(__file__).parent

BENCHMARK_FILES = sorted(BENCHMARKS_DIR.glob("bench_*.py"))

ALL_BENCHMARKS = [bm.stem for bm in BENCHMARK_FILES]

LIMITED_API_VERSION = max((3, 12), sys.version_info[:2])


try:
    from distutils import sysconfig
    DISTUTILS_CFLAGS = sysconfig.get_config_var('CFLAGS')
except ImportError:
    DISTUTILS_CFLAGS = ''


parse_timings = re.compile(
    r"(?P<lib>\w+):\s*"
    r"(?P<benchmark>\w+)\s+"
    r"\((?P<params>[^)]+)\)\s*"
    r"(?P<besttime>[0-9.]+)\s+"
    r"(?P<timings>.*)"
).match


def run(command, cwd=None, pythonpath=None, c_macros=None):
    env = None
    if pythonpath:
        env = os.environ.copy()
        env['PYTHONPATH'] = pythonpath
    if c_macros:
        env = env or os.environ.copy()
        env['CFLAGS'] = env.get('CFLAGS', '') + " " + ' '.join(f" -D{macro}" for macro in c_macros)

    try:
        return subprocess.run(command, cwd=cwd, check=True, capture_output=True, env=env)
    except subprocess.CalledProcessError as exc:
        logging.error(f"Command failed: {' '.join(map(str, command))}\nOutput:\n{exc.stderr.decode()}")
        raise


def copy_benchmarks(bm_dir: pathlib.Path, benchmarks=None):
    bm_files = []
    shutil.copy(BENCHMARKS_DIR / 'benchbase.py', bm_dir / 'benchbase.py')
    for bm_src_file in BENCHMARK_FILES:
        if benchmarks and bm_src_file.stem not in benchmarks:
            continue
        bm_file = bm_dir / bm_src_file.name
        for benchmark_file in BENCHMARKS_DIR.glob(bm_src_file.stem + ".*"):
            shutil.copy(benchmark_file, bm_dir / benchmark_file.name)
        bm_files.append(bm_file)

    return bm_files


def compile_lxml(lxml_dir: pathlib.Path, c_macros=None):
    rev_hash = get_git_rev(rev_dir=lxml_dir)
    logging.info(f"Compiling lxml gitrev {rev_hash}")
    run(
        [sys.executable, "setup.py", "build_ext", "-i", "-j6"],
        cwd=lxml_dir,
        c_macros=c_macros,
    )


def get_git_rev(revision=None, rev_dir=None):
    command = ["git", "describe", "--long"]
    if revision:
        command.append(revision)
    output = run(command, cwd=rev_dir)
    _, rev_hash = output.stdout.decode().strip().rsplit('-', 1)
    return rev_hash[1:]


def git_clone(rev_dir, revision):
    rev_hash = get_git_rev(revision)
    run(["git", "clone", "-n", "--no-single-branch", ".", str(rev_dir)])
    run(["git", "checkout", rev_hash], cwd=rev_dir)


def copy_profile(bm_dir, module_name, profiler):
    timestamp = int(time.time() * 1000)
    profile_input = bm_dir / "profile.out"
    data_file_name = f"{profiler}_{module_name}_{timestamp:X}.data"

    if profiler == 'callgrind':
        bm_dir_str = str(bm_dir) + os.sep
        with open(profile_input) as data_file_in:
            with open(data_file_name, mode='w') as data_file_out:
                for line in data_file_in:
                    if bm_dir_str in line:
                        # Remove absolute file paths to link to local file copy below.
                        line = line.replace(bm_dir_str, "")
                    data_file_out.write(line)
    else:
        shutil.move(profile_input, data_file_name)

    for result_file_name in (f"{module_name}.c", f"{module_name}.html"):
        result_file = bm_dir / result_file_name
        if result_file.exists():
            shutil.move(result_file, result_file_name)

    for ext in bm_dir.glob(f"{module_name}.*so"):
        shutil.move(str(ext), ext.name)


def run_benchmark(bm_dir, module_name, pythonpath=None, profiler=None):
    logging.info(f"Running benchmark '{module_name}'.")

    command = []

    if profiler:
        if profiler == 'perf':
            command = ["perf", "record", "--quiet", "-g", "--output=profile.out"]
        elif profiler == 'callgrind':
            command = [
                "valgrind", "--tool=callgrind",
                "--dump-instr=yes", "--collect-jumps=yes",
                "--callgrind-out-file=profile.out",
            ]

    command += [sys.executable, f"{module_name}.py"]

    output = run(command, cwd=bm_dir, pythonpath=pythonpath)

    if profiler:
        copy_profile(bm_dir, module_name, profiler)

    lines = filter(None, output.stdout.decode().splitlines())
    for line in lines:
        if line == "Setup times for trees in seconds:":
            break

    other_lines = []
    timings = []
    for line in lines:
        match = parse_timings(line)
        if match:
            timings.append((match['benchmark'], match['params'].strip(), match['lib'], float(match['besttime']), match['timings']))
        else:
            other_lines.append(line)

    return other_lines, timings


def run_benchmarks(bm_dir, benchmarks, pythonpath=None, profiler=None):
    timings = {}
    for benchmark in benchmarks:
        timings[benchmark] = run_benchmark(bm_dir, benchmark, pythonpath=pythonpath, profiler=profiler)
    return timings


def benchmark_revisions(benchmarks, revisions, profiler=None, limited_revisions=(), deps_zipfile=None):
    python_version = "Python %d.%d.%d" % sys.version_info[:3]
    logging.info(f"### Comparing revisions in {python_version}: {' '.join(revisions)}.")
    logging.info(f"CFLAGS={os.environ.get('CFLAGS', DISTUTILS_CFLAGS)}")

    hashes = {}
    timings = {}
    for revision in revisions:
        rev_hash = get_git_rev(revision)
        if rev_hash in hashes:
            logging.info(f"### Ignoring revision '{revision}': same as '{hashes[rev_hash]}'")
            continue
        hashes[rev_hash] = revision

        logging.info(f"### Preparing benchmark run for lxml '{revision}'.")
        timings[revision] = benchmark_revision(
            revision, benchmarks, profiler, deps_zipfile=deps_zipfile)

        if revision in limited_revisions:
            logging.info(
                f"### Preparing benchmark run for lxml '{revision}' (Limited API {LIMITED_API_VERSION[0]}.{LIMITED_API_VERSION[1]}).")
            timings['L-' + revision] = benchmark_revision(
                revision, benchmarks, profiler,
                c_macros=["Py_LIMITED_API=0x%02x%02x0000" % LIMITED_API_VERSION],
                deps_zipfile=deps_zipfile,
            )

    return timings


def cache_libs(lxml_dir, deps_zipfile):
    for dir_path, _, filenames in (lxml_dir / "build" / "tmp").walk():
        for filename in filenames:
            path = dir_path / filename
            deps_zipfile.write(path, path.relative_to(lxml_dir))


def benchmark_revision(revision, benchmarks, profiler=None, c_macros=None, deps_zipfile=None):
    with tempfile.TemporaryDirectory() as base_dir_str:
        base_dir = pathlib.Path(base_dir_str)
        lxml_dir = base_dir / "lxml" / revision
        bm_dir = base_dir / "benchmarks" / revision

        git_clone(lxml_dir, revision=revision)

        bm_dir.mkdir(parents=True)
        bm_files = copy_benchmarks(bm_dir, benchmarks)

        deps_zip_is_empty = deps_zipfile and not deps_zipfile.namelist()
        if deps_zipfile and not deps_zip_is_empty:
            deps_zipfile.extractall(lxml_dir)

        compile_lxml(lxml_dir, c_macros=c_macros)

        if deps_zipfile and deps_zip_is_empty:
            cache_libs(lxml_dir, deps_zipfile)

        logging.info(f"### Running benchmarks for {revision}: {' '.join(bm.stem for bm in bm_files)}")
        return run_benchmarks(bm_dir, benchmarks, pythonpath=f"{bm_dir}:{lxml_dir / 'src'}", profiler=profiler)


def report_revision_timings(rev_timings):
    units = {"nsec": 1e-9, "usec": 1e-6, "msec": 1e-3, "sec": 1.0}
    scales = [(scale, unit) for unit, scale in reversed(units.items())]  # biggest first

    def format_time(t):
        pos_t = abs(t)
        for scale, unit in scales:
            if pos_t >= scale:
                break
        else:
            raise RuntimeError(f"Timing is below nanoseconds: {t:f}")
        return f"{t / scale :+.3f} {unit}"

    timings_by_benchmark = collections.defaultdict(list)
    setup_times = []
    for revision_name, bm_timings in rev_timings.items():
        for benchmark_module, (output, timings) in bm_timings.items():
            setup_times.append((benchmark_module, revision_name, output))
            for benchmark_name, params, lib, best_time, result_text in timings:
                timings_by_benchmark[(benchmark_module, benchmark_name, params)].append((lib, revision_name, best_time, result_text))

    setup_times.sort()
    for timings in timings_by_benchmark.values():
        timings.sort()

    for benchmark_module, revision_name, output in setup_times:
        result = '\n'.join(output)
        logging.info(f"Setup times for trees in seconds - {benchmark_module} / {revision_name}:\n{result}")

    differences = collections.defaultdict(list)
    for (benchmark_module, benchmark_name, params), timings in timings_by_benchmark.items():
        logging.info(f"### Benchmark {benchmark_module} / {benchmark_name} ({params}):")
        base_line = timings[0][2]
        for lib, revision_name, bm_time, result_text in timings:
            diff_str = ""
            if base_line != bm_time:
                pdiff = bm_time * 100 / base_line - 100
                differences[(lib, revision_name)].append((abs(pdiff), pdiff, bm_time - base_line, benchmark_module, benchmark_name, params))
                diff_str = f"  {pdiff:+8.2f} %"
            logging.info(
                f"    {lib:3} / {revision_name[:25]:25} = {bm_time:8.4f} {result_text}{diff_str}"
            )

    for (lib, revision_name), diffs in differences.items():
        diffs.sort(reverse=True)
        diffs_by_sign = {True: [], False: []}
        for diff in diffs:
            diffs_by_sign[diff[1] < 0].append(diff)

        for is_win, diffs in diffs_by_sign.items():
            if not diffs or diffs[0][0] < 1.0:
                continue

            logging.info(f"Largest {'gains' if is_win else 'losses'} for {revision_name}:")
            cutoff = max(1.0, diffs[0][0] // 4)
            for absdiff, pdiff, tdiff, benchmark_module, benchmark_name, params in diffs:
                if absdiff < cutoff:
                    break
                logging.info(f"    {benchmark_module} / {benchmark_name:<25} ({params:>10})  {pdiff:+8.2f} %  /  {format_time(tdiff / 1000.0):>8}")


def parse_args(args):
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    parser = ArgumentParser(
        description="Run benchmarks against different lxml tags/revisions.",
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-b", "--benchmarks",
        dest="benchmarks", default=','.join(ALL_BENCHMARKS),
        help="The list of benchmark selectors to run, simple substrings, separated by comma.",
    )
    parser.add_argument(
        "--with-limited",
        dest="with_limited_api", action="append", default=[],
        help="Also run the benchmarks for REVISION against the Limited C-API.",
    )
    #parser.add_argument(
    #    "--with-elementtree",
    #    dest="with_elementtree",
    #    help="Include results for Python's xml.etree.ElementTree.",
    #)
    parser.add_argument(
        "--perf",
        dest="profiler", action="store_const", const="perf", default=None,
        help="Run Linux 'perf record' on the benchmark process.",
    )
    parser.add_argument(
        "--callgrind",
        dest="profiler", action="store_const", const="callgrind", default=None,
        help="Run Valgrind's callgrind profiler on the benchmark process.",
    )
    parser.add_argument(
        "revisions",
        nargs="*", default=[],
        help="The git revisions to check out and benchmark.",
    )

    return parser.parse_known_args(args)


if __name__ == '__main__':
    options, cythonize_args = parse_args(sys.argv[1:])

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    benchmark_selectors = set(bm.strip() for bm in options.benchmarks.split(","))
    benchmarks = [bm for bm in ALL_BENCHMARKS if any(selector in bm for selector in benchmark_selectors)]
    if benchmark_selectors and not benchmarks:
        logging.error("No benchmarks selected!")
        sys.exit(1)

    deps_zipfile = zipfile.ZipFile(io.BytesIO(), mode='w')

    revisions = list({rev: rev for rev in (options.revisions + options.with_limited_api)})  # deduplicate in order
    timings = benchmark_revisions(
        benchmarks, revisions,
        profiler=options.profiler,
        limited_revisions=options.with_limited_api,
        deps_zipfile=deps_zipfile,
    )
    report_revision_timings(timings)
