import os, sys, re

def version():
    return open(os.path.join(get_src_dir(), 'version.txt')).read().strip()

def branch_version():
    return version()[:3]

def svn_version():
    _version = version()
    try:
        svn_entries = open(
            os.path.join(get_src_dir(), '.svn', 'entries')).read()
        revision = re.search('<entry[^>]*name=""[^>]*revision="([^"]+)"',
                             svn_entries).group(1)
        result = _version + '-' + revision
    except IOError:
        result = _version

    if 'dev' in _version:
        result = fix_alphabeta(result, 'dev')
    elif 'alpha' in _version:
        result = fix_alphabeta(result, 'alpha')
    if 'beta' in _version:
        result = fix_alphabeta(result, 'beta')

    return result

def dev_status():
    _version = version()
    if 'dev' in _version:
        return 'Development Status :: 3 - Alpha'
    elif 'alpha' in _version:
        return 'Development Status :: 3 - Alpha'
    elif 'beta' in _version:
        return 'Development Status :: 4 - Beta'
    else:
        return 'Development Status :: 5 - Production/Stable'

def changes():
    """Extract part of changelog pertaining to version.
    """
    _version = version()
    f = open(os.path.join(get_src_dir(), "CHANGES.txt"), 'r')
    lines = []
    for line in f:
        if line.startswith('====='):
            if len(lines) > 1:
                break
        if lines:
            lines.append(line)
        elif line.startswith(_version):
            lines.append(line)
    f.close()
    return ''.join(lines[:-1])

def create_version_h(svn_version):
    """Create lxml-version.h
    """
    version_h = open(
        os.path.join(get_src_dir(), 'src', 'lxml', 'lxml-version.h'),
        'w')
    version_h.write('''\
#ifndef LXML_VERSION_STRING
#define LXML_VERSION_STRING "%s"
#endif
''' % svn_version)
    version_h.close()

def get_src_dir():
    return os.path.join(os.getcwd(), os.path.dirname(sys.argv[0]))

def fix_alphabeta(version, alphabeta):
    if ('.' + alphabeta) in version:
        return version
    return version.replace(alphabeta, '.' + alphabeta)
