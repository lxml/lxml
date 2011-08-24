import sys, os
import fnmatch
import glob

# for command line options and supported environment variables, please
# see the end of 'setupinfo.py'

extra_options = {}

try:
    import Cython
    # may need to work around setuptools bug by providing a fake Pyrex
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fake_pyrex"))
except ImportError:
    pass

try:
    import pkg_resources
    try:
        pkg_resources.require("setuptools>=0.6c5")
    except pkg_resources.VersionConflict:
        from ez_setup import use_setuptools
        use_setuptools(version="0.6c5")
    #pkg_resources.require("Cython==0.9.6.10")
    from setuptools import setup
    extra_options["zip_safe"] = False
except ImportError:
    # no setuptools installed
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


extra_options.update(setupinfo.extra_setup_args())

extra_options['package_data'] = {
    'lxml': [
        'etreepublic.pxd',
        'tree.pxd',
        'etree_defs.h'
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
        'lxml', 'lxml.html', 'lxml.isoschematron'
    ]

extra_options['package_dir'] = {
        '': 'src'
    }

extra_options['packages'] = [
        'lxml', 'lxml.html', 'lxml.isoschematron'
    ]


def setup_extra_options():
    try:
        set
    except NameError:
        from sets import Set as set

    def basePath(paths):
        if not len(paths):
            return ''

        base_path = paths[0]
        while base_path:
            base_path = os.path.dirname(base_path)
            for p in paths:
                if not p.startswith(base_path):
                    break
            else:
                return base_path
        return base_path

    def removeBaseDirs(directories):
        filtered_dirs = []
        for dir_path in directories:
            for p in directories:
                if dir_path is not p and p.startswith(dir_path):
                    break
            else:
                filtered_dirs.append(dir_path)
        return filtered_dirs

    def extractFiles(directories, pattern='*'):
        get_files = lambda root, files: [os.path.join(root, f) for f in files]

        file_list = []
        for dir_path in directories:
            for root, dirs, files in os.walk(dir_path):
                file_list.extend(get_files(root, fnmatch.filter(files, pattern)))
                file_list.extend(extractFiles(get_files(root, dirs), pattern))
        return file_list

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

    if sys.version_info < (2, 4):
        # Python 2.3 hasn't package_data:
        # Migrate from package_data to data_files
        def _packageDataToDataFiles(key, values):
            key_path = key.replace('.', '/')
            dst_path = os.path.join(install_base_dir, key_path)
            src = 'src/' + key_path
            files = [f for v in values for f in glob.glob(os.path.join(src, v))]
            return (dst_path, files)

        from distutils.sysconfig import get_python_lib
        install_base_dir = get_python_lib(prefix='')
        data_files = extra_opts.setdefault('data_files', [])
        package_data = extra_opts.pop('package_data')
        for key, values in package_data.iteritems():
            data_files.append(_packageDataToDataFiles(key, values))

    # Add lxml.include with (lxml, libxslt headers...)
    #   python setup.py build --static --static-deps install
    #   python setup.py bdist_wininst --static
    if setupinfo.OPTION_STATIC:
        include_dirs = set()
        for extension in ext_modules:
            include_dirs |= set(extension.include_dirs)
        include_dirs = removeBaseDirs(include_dirs)

        include_base = basePath(include_dirs)
        headers = [path for path in extractFiles(include_dirs)]

        if sys.version_info < (2, 4):
            def _headersToDataFiles(key, fheaders):
                key_path = key.replace('.', '/')
                dst_path = os.path.join(install_base_dir, key_path)
                headers = {}
                for full_path in fheaders:
                    fpath, fhead = os.path.split(full_path)
                    fpath, fdir = os.path.split(fpath)
                    dst_dir = os.path.join(dst_path, fdir)
                    headers.setdefault(dst_dir, []).append(full_path)
                return headers.items()

            data_files.extend(_headersToDataFiles('lxml.include', headers))
        else:
            files = {}
            for full_path in headers:
                fpath, fhead = os.path.split(full_path)
                _, fdir = os.path.split(fpath)
                files.setdefault((fpath, fdir), []).append(fhead)

            package_dir['lxml.include'] = include_base
            packages.append('lxml.include')
            for (fpath, fdir), fhs in files.iteritems():
                kdir = 'lxml.include.' + fdir
                package_data[kdir] = fhs
                package_dir[kdir] = fpath
                packages.append(kdir)

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
    'Programming Language :: Python :: 2.3',
    'Programming Language :: Python :: 2.4',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.0',
    'Programming Language :: Python :: 3.1',
    'Programming Language :: Python :: 3.2',
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
