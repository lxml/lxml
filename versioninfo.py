import io
import os
import sys

__LXML_VERSION = None


def version():
    global __LXML_VERSION
    if __LXML_VERSION is None:
        with open(os.path.join(get_base_dir(), 'version.txt')) as f:
            __LXML_VERSION = f.read().strip()
    return __LXML_VERSION


def branch_version():
    return version()[:3]


def is_pre_release():
    version_string = version()
    return "a" in version_string or "b" in version_string


def dev_status():
    _version = version()
    if 'a' in _version:
        return 'Development Status :: 3 - Alpha'
    elif 'b' in _version or 'c' in _version:
        return 'Development Status :: 4 - Beta'
    else:
        return 'Development Status :: 5 - Production/Stable'


def changes():
    """Extract part of changelog pertaining to version.
    """
    _version = version()
    with io.open(os.path.join(get_base_dir(), "CHANGES.txt"), 'r', encoding='utf8') as f:
        lines = []
        for line in f:
            if line.startswith('====='):
                if len(lines) > 1:
                    break
            if lines:
                lines.append(line)
            elif line.startswith(_version):
                lines.append(line)
    return ''.join(lines[:-1])


def create_version_h():
    """Create lxml-version.h
    """
    lxml_version = version()
    # make sure we have a triple part version number
    parts = lxml_version.split('-')
    while parts[0].count('.') < 2:
        parts[0] += '.0'
    lxml_version = '-'.join(parts).replace('a', '.alpha').replace('b', '.beta')

    version_h = open(
        os.path.join(get_base_dir(), 'src', 'lxml', 'includes', 'lxml-version.h'),
        'w')
    version_h.write('''\
#ifndef LXML_VERSION_STRING
#define LXML_VERSION_STRING "%s"
#endif
''' % lxml_version)
    version_h.close()


def get_base_dir():
    return os.path.abspath(os.path.dirname(sys.argv[0]))
