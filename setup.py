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
    maintainer = 'Infrae',
    maintainer_email="faassen@infrae.com",
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
