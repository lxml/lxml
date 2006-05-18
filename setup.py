import sys, os, os.path, re

setup_args = {}
try:
    from setuptools import setup
    from setuptools.extension import Extension
    # prevent setuptools from making local etree.so copies:
    setup_args['zip_safe'] = False
except ImportError:
    from distutils.core import setup
    from distutils.extension import Extension

# This is called if the '--static' option is passed
def setupStaticBuild():
    "See doc/build.txt to make this work."
    cflags = [
        ]
    xslt_libs = [
        ]
    result = (cflags, xslt_libs)
    # return result
    raise NotImplementedError, \
          "Static build not configured, see doc/build.txt"

def flags(cmd):
    wf, rf, ef = os.popen3(cmd)
    return rf.read().strip().split(' ')


src_dir = os.path.join(os.getcwd(), os.path.dirname(sys.argv[0]))
version = open(os.path.join(src_dir, 'version.txt')).read().strip()

try:
    svn_entries = open(os.path.join(src_dir, '.svn', 'entries')).read()
except IOError:
    svn_version = version
else:
    revision = re.search('<entry[^>]*name=""[^>]*revision="([^"]+)"',
                         svn_entries).group(1)
    svn_version = version + '-' + revision

version_h = open(os.path.join(src_dir, 'src', 'lxml', 'lxml-version.h'), 'w')
version_h.write('''\
#ifndef LXML_VERSION_STRING
#define LXML_VERSION_STRING "%s"
#endif
''' % svn_version)
version_h.close()

print "Building lxml version", svn_version

# setup etree extension building

try:
    from Pyrex.Distutils import build_ext as build_pyx
    sources = ["src/lxml/etree.pyx"]
    setup_args['cmdclass'] = {'build_ext' : build_pyx}
except ImportError:
    print "*NOTE*: Trying to build without Pyrex, needs pre-generated 'src/lxml/etree.c' !"
    sources = ["src/lxml/etree.c"]

try:
    sys.argv.remove('--static')
except ValueError:
    # we are not compiling statically
    cflags    = flags('xslt-config --cflags')
    xslt_libs = flags('xslt-config --libs')

    # compile also against libexslt!
    for i, libname in enumerate(xslt_libs):
        if 'exslt' in libname:
            break
        if 'xslt' in libname:
            xslt_libs.insert(i, libname.replace('xslt', 'exslt'))
            break
else:
    # use the static setup as configured in setupStaticBuild
    cflags, xslt_libs = setupStaticBuild()

ext_modules = [ Extension(
    "lxml.etree",
    sources = sources,
    extra_compile_args = ['-w'] + cflags,
    extra_link_args = xslt_libs
    )]


# setup ChangeLog entry

changelog_text = ""
try:
    changelog = open(os.path.join(src_dir, "CHANGES.txt"), 'r')
except:
    print "*NOTE*: couldn't open CHANGES.txt !"
else:
    changelog_lines = []
    for line in changelog:
        if line.startswith('====='):
            if len(changelog_lines) > 1:
                break
        if changelog_lines:
            changelog_lines.append(line)
        elif version in line:
            changelog_lines.append(line)

    if changelog_lines:
        changelog_text = ''.join(changelog_lines[:-1])

    changelog.close()


setup(
    name = "lxml",
    version = version,
    author="lxml dev team",
    author_email="lxml-dev@codespeak.net",
    maintainer="lxml dev team",
    maintainer_email="lxml-dev@codespeak.net",
    url="http://codespeak.net/lxml",

    description="Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API.",

    long_description="""\
lxml is a Pythonic binding for the libxml2 and libxslt libraries.  It provides
safe and convenient access to these libraries using the ElementTree API.

It extends the ElementTree API significantly to offer support for XPath,
RelaxNG, XML Schema, XSLT, C14N and much more.

""" + changelog_text,

    classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Intended Audience :: Information Technology',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python',
    'Programming Language :: C',
    'Operating System :: OS Independent',
    'Topic :: Text Processing :: Markup :: XML',
    'Topic :: Software Development :: Libraries :: Python Modules'
    ],

    package_dir = {'': 'src'},
    packages = ['lxml'],
    ext_modules = ext_modules,
    **setup_args
)
