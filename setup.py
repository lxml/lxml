import os

try:
    from setuptools import setup
    from setuptools.extension import Extension
except ImportError:
    from distutils.core import setup
    from distutils.extension import Extension

from Pyrex.Distutils import build_ext as build_pyx

def flags(cmd):
    wf, rf, ef = os.popen3(cmd)
    return rf.read().strip().split(' ')

setup(
    name = "lxml",
    version = open('version.txt').read().strip(),
    author="lxml dev team",
    author_email="lxml-dev@codespeak.net",
    maintainer="lxml dev team",
    maintainer_email="lxml-dev@codespeak.net",
    url="http://codespeak.net/lxml",
    description="Powerful and Pythonic XML processing library based on libxml2/libxslt with an ElementTree API",
    long_description="""\
lxml is a Pythonic binding for the libxml2 and libxslt libraries. It provides
safe and convenient access to these libraries using the ElementTree API.
It extends the ElementTree API significantly to offer support for
XPath, Relax NG, XML Schema, XSLT, c14n and much more.
""",

    package_dir = {'': 'src'},
    packages = ['lxml', 'lxml.tests'],
    ext_modules = [
        Extension(
            "lxml.etree", 
            sources = ["src/lxml/etree.pyx"], 
            extra_compile_args = ['-w'] + flags('xslt-config --cflags'),
            extra_link_args = flags('xslt-config --libs'))],
    cmdclass = {'build_ext': build_pyx}
)
