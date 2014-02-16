import os
import re
import sys
import fnmatch

# for command line options and supported environment variables, please
# see the end of 'setupinfo.py'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import versioninfo
import setupinfo

# override these and pass --static for a static build. See
# doc/build.txt for more information. If you do not pass --static
# changing this will have no effect.
STATIC_INCLUDE_DIRS = []
STATIC_LIBRARY_DIRS = []
STATIC_CFLAGS = []
STATIC_BINARIES = []

# create lxml-version.h file
svn_version = versioninfo.svn_version()
versioninfo.create_version_h(svn_version)
print("Building lxml version %s." % svn_version)

OPTION_RUN_TESTS = setupinfo.has_option('run-tests')

branch_link = """
After an official release of a new stable series, bug fixes may become
available at
https://github.com/lxml/lxml/tree/lxml-%(branch_version)s .
Running ``easy_install lxml==%(branch_version)sbugfix`` will install
the unreleased branch state from
https://github.com/lxml/lxml/tarball/lxml-%(branch_version)s#egg=lxml-%(branch_version)sbugfix
as soon as a maintenance branch has been established.  Note that this
requires Cython to be installed at an appropriate version for the build.

"""

if versioninfo.is_pre_release():
    branch_link = ""


extra_options = {}
if 'setuptools' in sys.modules:
    extra_options['zip_safe'] = False

    try:
        import pkg_resources
    except ImportError:
        pass
    else:
        f = open("requirements.txt", "r")
        try:
            deps = [str(req) for req in pkg_resources.parse_requirements(f)]
        finally:
            f.close()
        extra_options['extras_require'] = {
            'source': deps,
            'cssselect': 'cssselect>=0.7',
            'html5': 'html5lib',
            'htmlsoup': 'BeautifulSoup4',
        }

extra_options.update(setupinfo.extra_setup_args())

extra_options['package_data'] = {
    'lxml': [
        'lxml.etree.h',
        'lxml.etree_api.h',
    ],
    'lxml.includes': [
        '*.pxd', '*.h'
        ],
    'lxml.isoschematron':  [
        'resources/rng/iso-schematron.rng',
        'resources/xsl/*.xsl',
        'resources/xsl/iso-schematron-xslt1/*.xsl',
        'resources/xsl/iso-schematron-xslt1/readme.txt'
        ],
    }

extra_options['package_dir'] = {
        '': 'src'
    }

extra_options['packages'] = [
        'lxml', 'lxml.includes', 'lxml.html', 'lxml.isoschematron'
    ]


def setup_extra_options():
    is_interesting_package = re.compile('^(libxml|libxslt|libexslt)$').match
    def extract_files(directories, pattern='*'):
        def get_files(root, dir_path, files):
            return [ (root, dir_path, filename)
                     for filename in fnmatch.filter(files, pattern) ]

        file_list = []
        for dir_path in directories:
            dir_path = os.path.realpath(dir_path)
            for root, dirs, files in os.walk(dir_path):
                rel_dir = root[len(dir_path)+1:]
                if is_interesting_package(rel_dir):
                    file_list.extend(get_files(root, rel_dir, files))
        return file_list

    def build_packages(files):
        packages = {}
        seen = set()
        for root_path, rel_path, filename in files:
            if filename in seen:
                # libxml2/libxslt header filenames are unique
                continue
            seen.add(filename)
            package_path = '.'.join(rel_path.split(os.sep))
            if package_path in packages:
                root, package_files = packages[package_path]
                if root != root_path:
                    print("conflicting directories found for include package '%s': %s and %s"
                          % (package_path, root_path, root))
                    continue
            else:
                package_files = []
                packages[package_path] = (root_path, package_files)
            package_files.append(filename)

        return packages

    # Copy Global Extra Options
    extra_opts = dict(extra_options)

    # Build ext modules
    ext_modules = setupinfo.ext_modules(
                    STATIC_INCLUDE_DIRS, STATIC_LIBRARY_DIRS,
                    STATIC_CFLAGS, STATIC_BINARIES)
    extra_opts['ext_modules'] = ext_modules

    packages = extra_opts.get('packages', list())
    package_dir = extra_opts.get('package_dir', dict())
    package_data = extra_opts.get('package_data', dict())

    # Add lxml.include with (lxml, libxslt headers...)
    #   python setup.py build --static --static-deps install
    #   python setup.py bdist_wininst --static
    if setupinfo.OPTION_STATIC:
        include_dirs = [] # keep them in order
        for extension in ext_modules:
            for inc_dir in extension.include_dirs:
                if inc_dir not in include_dirs:
                    include_dirs.append(inc_dir)

        header_packages = build_packages(extract_files(include_dirs))

        for package_path, (root_path, filenames) in header_packages.items():
            if package_path:
                package = 'lxml.includes.' + package_path
                packages.append(package)
            else:
                package = 'lxml.includes'
            package_data[package] = filenames
            package_dir[package] = root_path

    return extra_opts

setup(
    name = "lxml",
    version = versioninfo.version(),
    author="lxml dev team",
    author_email="lxml-dev@lxml.de",
    maintainer="lxml dev team",
    maintainer_email="lxml-dev@lxml.de",
    url="http://lxml.de/",
    download_url="http://pypi.python.org/packages/source/l/lxml/lxml-%s.tar.gz" % versioninfo.version(),
    bugtrack_url="https://bugs.launchpad.net/lxml",

    description="Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API.",

    long_description=((("""\
lxml is a Pythonic, mature binding for the libxml2 and libxslt libraries.  It
provides safe and convenient access to these libraries using the ElementTree
API.

It extends the ElementTree API significantly to offer support for XPath,
RelaxNG, XML Schema, XSLT, C14N and much more.

To contact the project, go to the `project home page
<http://lxml.de/>`_ or see our bug tracker at
https://launchpad.net/lxml

In case you want to use the current in-development version of lxml,
you can get it from the github repository at
https://github.com/lxml/lxml .  Note that this requires Cython to
build the sources, see the build instructions on the project home
page.  To the same end, running ``easy_install lxml==dev`` will
install lxml from
https://github.com/lxml/lxml/tarball/master#egg=lxml-dev if you have
an appropriate version of Cython installed.

""" + branch_link) % { "branch_version" : versioninfo.branch_version() }) +
                      versioninfo.changes()),
    classifiers = [
    versioninfo.dev_status(),
    'Intended Audience :: Developers',
    'Intended Audience :: Information Technology',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Cython',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.4',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.1',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: C',
    'Operating System :: OS Independent',
    'Topic :: Text Processing :: Markup :: HTML',
    'Topic :: Text Processing :: Markup :: XML',
    'Topic :: Software Development :: Libraries :: Python Modules'
    ],

    **setup_extra_options()
)

if OPTION_RUN_TESTS:
    print("Running tests.")
    import test
    sys.exit( test.main(sys.argv[:1]) )
