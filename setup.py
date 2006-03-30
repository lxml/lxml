import os

def flags(cmd):
    wf, rf, ef = os.popen3(cmd)
    return rf.read().strip().split(' ')

setup_args = {}
changelog_text = ""
version = open('version.txt').read().strip()

try:
    from setuptools import setup
    from setuptools.extension import Extension
    setup_args['zip_safe'] = False
except ImportError:
    from distutils.core import setup
    from distutils.extension import Extension

try:
    from Pyrex.Distutils import build_ext as build_pyx
    sources = ["src/lxml/etree.pyx"]
    setup_args['cmdclass'] = {'build_ext' : build_pyx}
except ImportError:
    print "*NOTE*: Trying to build without Pyrex, needs pre-generated 'src/lxml/etree.c' !"
    sources = ["src/lxml/etree.c"]

try:
    changelog = open("CHANGES.txt", 'r')
except:
    print "*NOTE*: couldn't open CHANGES.txt !"
else:
    inside = 0
    changelog_lines = []
    for line in changelog:
        if line.startswith('====='):
            inside += 1
            if inside > 3:
                break
        if inside > 1:
            changelog_lines.append(line)
        elif version in line:
            changelog_lines.append(line)
            inside += 1

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
    ext_modules = [ Extension(
        "lxml.etree", 
        sources = sources,
        extra_compile_args = ['-w'] + flags('xslt-config --cflags'),
        extra_link_args = flags('xslt-config --libs')
    )],
    **setup_args
)
