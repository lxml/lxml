import sys, os, os.path, re

EXT_MODULES = [
    ("etree",       "lxml.etree"),
    ("objectify",   "lxml.objectify")
    ]

setup_args = {}
ext_args   = {}
DEFINES = []

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

# This is called if the '--rpath' option is passed
def setupRpathBuild(xslt_libs, ext_args):
    libdirs   = []
    libs      = []
    libflags  = []
    rpathdirs = []
    for option in xslt_libs:
        content = option[2:]
        if option.startswith('-L'):
            if not content.startswith('/usr'):
                rpathdirs.append(content)
            libdirs.append(content)
        elif option.startswith('-l'):
            libs.append(content)
        else:
            libflags.append(option)

    ext_args['libraries']            = libs
    ext_args['library_dirs']         = libdirs
    ext_args['extra_link_args']      = libflags
    ext_args['runtime_library_dirs'] = rpathdirs

def flags(cmd):
    wf, rf, ef = os.popen3(cmd)
    return rf.read().split()

def fix_alphabeta(version, alphabeta):
    if '.'+alphabeta in version:
        return version
    return version.replace(alphabeta, '.'+alphabeta)

# determine version number and create lxml-version.h

src_dir = os.path.join(os.getcwd(), os.path.dirname(sys.argv[0]))
version = open(os.path.join(src_dir, 'version.txt')).read().strip()
branch_version = version[:3]

try:
    svn_entries = open(os.path.join(src_dir, '.svn', 'entries')).read()
except IOError:
    svn_version = version
else:
    revision = re.search('<entry[^>]*name=""[^>]*revision="([^"]+)"',
                         svn_entries).group(1)
    svn_version = version + '-' + revision

if 'dev' in version:
    svn_version = fix_alphabeta(svn_version, 'dev')
    dev_status = 'Development Status :: 3 - Alpha'
elif 'alpha' in version:
    svn_version = fix_alphabeta(svn_version, 'alpha')
    dev_status = 'Development Status :: 3 - Alpha'
elif 'beta' in version:
    svn_version = fix_alphabeta(svn_version, 'beta')
    dev_status = 'Development Status :: 4 - Beta'
else:
    dev_status = 'Development Status :: 5 - Production/Stable'

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
    source_extension = ".pyx"
    setup_args['cmdclass'] = {'build_ext' : build_pyx}
except ImportError:
    print "*NOTE*: Trying to build without Pyrex, needs pre-generated 'src/lxml/etree.c' !"
    source_extension = ".c"

if '--static' in sys.argv:
    # use the static setup as configured in setupStaticBuild
    sys.argv.remove('--static')
    cflags, xslt_libs = setupStaticBuild()
    ext_args['extra_link_args'] = xslt_libs
else:
    cflags    = flags('xslt-config --cflags')
    xslt_libs = flags('xslt-config --libs')
    # compile also against libexslt!
    for i, libname in enumerate(xslt_libs):
        if 'exslt' in libname:
            break
        if 'xslt' in libname:
            xslt_libs.insert(i, libname.replace('xslt', 'exslt'))
            break

    if '--rpath' in sys.argv:
        # compile with --rpath under gcc
        sys.argv.remove('--rpath')
        setupRpathBuild(xslt_libs, ext_args)
    else:
        ext_args['extra_link_args'] = xslt_libs

try:
    sys.argv.remove('--without-assert')
    DEFINES.append( ('PYREX_WITHOUT_ASSERTIONS', None) )
except ValueError:
    pass

ext_modules = []

for module, package in EXT_MODULES:
    ext_modules.append(
	Extension(
	package,
	sources = ["src/lxml/" + module + source_extension],
	extra_compile_args = ['-w'] + cflags,
	define_macros = DEFINES,
	**ext_args
	))

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
        elif line.startswith(version):
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

In case you want to use the current in-development version of lxml, you can
get it from the subversion repository at http://codespeak.net/svn/lxml/trunk .
Running ``easy_install lxml==dev`` will install it from
http://codespeak.net/svn/lxml/trunk#egg=lxml-dev

Current bug fixes for the stable version are at
http://codespeak.net/svn/lxml/branch/lxml-%(branch_version)s .
Running ``easy_install lxml==lxml-%(branch_version)sbugfix`` will install this
version from
http://codespeak.net/svn/lxml/branch/lxml-%(branch_version)s#egg=lxml-%(branch_version)sbugfix

""" % {"branch_version":branch_version} + changelog_text,

    classifiers = [
    dev_status,
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
