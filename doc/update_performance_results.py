import operator
import re

_parse_result_line = re.compile(
    "\s*(?P<library>\w+):\s*(?P<name>\w+)\s+\((?P<config>[-\w]+\s[\w,]+)\s*\)\s+(?P<time>[0-9.]+\s+msec/pass)"
).match

_make_key = operator.itemgetter('library', 'name', 'config')


def read_benchmark_results(benchmark_files):
    benchmark_results = {}
    for file_path in benchmark_files:
        with open(file_path) as f:
            for line in f:
                result = _parse_result_line(line)
                if not result:
                    continue
                d = result.groupdict()
                benchmark_results[_make_key(d)] = d['time']

    return benchmark_results


def update_results(text_file, benchmark_results):
    with open(text_file) as f:
        for line in f:
            match = _parse_result_line(line)
            if not match:
                yield line
                continue

            d = match.groupdict()
            key = _make_key(d)
            try:
                new_time = benchmark_results[key]
            except KeyError:
                print("Failed to update benchmark results of %r" % d)
                yield line
            else:
                yield line.replace(d['time'], new_time)


def main(log_files, doc_file="doc/performance.txt"):
    results = read_benchmark_results(log_files)
    if not results:
        return

    print("Found %d benchmark results" % len(results))
    new_text = "".join(update_results(doc_file, results))
    with open(doc_file, 'w') as f:
        f.write(new_text)
    print("Updated benchmark results in %s" % doc_file)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
