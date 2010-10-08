import sys, os

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
http://codespeak.net/svn/lxml/branch/lxml-%(branch_version)s .
Running ``easy_install lxml==%(branch_version)sbugfix`` will install
the unreleased branch state from
http://codespeak.net/svn/lxml/branch/lxml-%(branch_version)s#egg=lxml-%(branch_version)sbugfix
as soon as a maintenance branch has been established.
"""

if versioninfo.is_pre_release():
    branch_link = ""


extra_options.update(setupinfo.extra_setup_args())

setup(
    name = "lxml",
    version = versioninfo.version(),
    author="lxml dev team",
    author_email="lxml-dev@codespeak.net",
    maintainer="lxml dev team",
    maintainer_email="lxml-dev@codespeak.net",
    url="http://codespeak.net/lxml",
    download_url="http://pypi.python.org/packages/source/l/lxml/lxml-%s.tar.gz" % versioninfo.version(),

    description="Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API.",

    long_description=((("""\
lxml is a Pythonic, mature binding for the libxml2 and libxslt libraries.  It
provides safe and convenient access to these libraries using the ElementTree
API.

It extends the ElementTree API significantly to offer support for XPath,
RelaxNG, XML Schema, XSLT, C14N and much more.

To contact the project, go to the `project home page
<http://codespeak.net/lxml/>`_ or see our bug tracker at
https://launchpad.net/lxml

In case you want to use the current in-development version of lxml,
you can get it from the subversion repository at
http://codespeak.net/svn/lxml/trunk .  Note that this requires Cython
to build the sources, see the build instructions on the project home
page.  To the same end, running Running ``easy_install lxml==dev``
will install lxml from
http://codespeak.net/svn/lxml/trunk#egg=lxml-dev

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

    package_dir = {'': 'src'},
    packages = ['lxml', 'lxml.html', 'lxml.isoschematron'],
    package_data = {'lxml.isoschematron':
                    ['resources/rng/iso-schematron.rng',
                     'resources/xsl/*.xsl', 
                     'resources/xsl/iso-schematron-xslt1/*.xsl',
                     'resources/xsl/iso-schematron-xslt1/readme.txt']},
    ext_modules = setupinfo.ext_modules(
        STATIC_INCLUDE_DIRS, STATIC_LIBRARY_DIRS,
        STATIC_CFLAGS, STATIC_BINARIES),
    **extra_options
)

if OPTION_RUN_TESTS:
    print("Running tests.")
    import test
    sys.exit( test.main(sys.argv[:1]) )
