import os
import sys

# change these to your local installation of libxml2
libxml2_include_dir = '/home/faassen/tmp/local/include/libxml2'
libxslt_include_dir = '/home/faassen/tmp/local/include/'
include_dirs = [libxml2_include_dir, libxslt_include_dir]
library_dirs = ['/home/faassen/tmp/local/lib']
libraries = ['xml2', 'xslt']
runtime_library_dirs = ['/home/faassen/tmp/local/lib']
extra_compile_args = ['-w']

# Provide a bunch of custom components that make it possible to build and
# install non-.py files into the package destinations.
from distutils import dir_util
from distutils.command.build import build as buildcmd
from distutils.command.install_lib import install_lib as installcmd
from distutils.core import setup
from distutils.dist import Distribution
from distutils.extension import Extension
from lxmldistutils import build_ext

# We have to snoop for file types that distutils doesn't copy correctly when
# doing a non-build-in-place.
EXTS = ['.conf', '.css', '.dtd', '.gif', '.jpg', '.html',
        '.js',   '.mo',  '.png', '.pt', '.stx', '.ref',
        '.txt',  '.xml', '.zcml', '.mar', '.in', '.sample',
        ]

# This class serves multiple purposes.  It walks the file system looking for
# auxiliary files that distutils doesn't install properly, and it actually
# copies those files (when hooked into by distutils).  It also walks the file
# system looking for candidate packages for distutils to install as normal.
# The key here is that the package must have an __init__.py file.
class Finder:
    def __init__(self, exts, prefix):
        self._files = []
        self._pkgs = {}
        self._exts = exts
        # We're finding packages in lib/python in the source dir, but we're
        # copying them directly under build/lib.<plat>.  So we need to lop off
        # the prefix when calculating the package names from the file names.
        self._plen = len(prefix)

    def visit(self, ignore, dir, files):
        for file in files:
            # First see if this is one of the packages we want to add, or if
            # we're really skipping this package.
            if '__init__.py' in files:
                aspkg = dir[self._plen:].replace(os.sep, '.')
                self._pkgs[aspkg] = True
            # Add any extra files we're interested in
            base, ext = os.path.splitext(file)
            if ext in self._exts:
                self._files.append(os.path.join(dir, file))

    def copy_files(self, cmd, outputbase):
        for file in self._files:
            dest = os.path.join(outputbase, file[self._plen:])
            # Make sure the destination directory exists
            dir = os.path.dirname(dest)
            if not os.path.exists(dir):
                dir_util.mkpath(dir)
            cmd.copy_file(file, dest)

    def get_packages(self):
        return self._pkgs.keys()

def remove_stale_bytecode(arg, dirname, names):
    names = map(os.path.normcase, names)
    for name in names:
        if name.endswith(".pyc") or name.endswith(".pyo"):
            srcname = name[:-1]
            if srcname not in names:
                fullname = os.path.join(dirname, name)
                print "Removing stale bytecode file", fullname
                os.unlink(fullname)

# Create the finder instance, which will be used in lots of places.  `finder'
# is the global we're most interested in.
basedir = 'src/'
finder = Finder(EXTS, basedir)
os.path.walk(basedir, finder.visit, None)
packages = finder.get_packages()

# Distutils hook classes
class MyBuilder(buildcmd):
    def run(self):
        os.path.walk(os.curdir, remove_stale_bytecode, None)
        buildcmd.run(self)
        finder.copy_files(self, self.build_lib)

class MyExtBuilder(build_ext):
    # Override the default build_ext to remove stale bytecodes.
    # Technically, removing bytecode has nothing to do with
    # building extensions, but the build_ext -i variant
    # is used to build lxml in place.
    def run(self):
        os.path.walk(os.curdir, remove_stale_bytecode, None)
        build_ext.run(self)

    def get_pxd_include_paths(self):
        """lxml specific pxd paths.
        """
        return ['src/lxml']
    
class MyLibInstaller(installcmd):
    def run(self):
        installcmd.run(self)
        finder.copy_files(self, self.install_dir)

class MyDistribution(Distribution):
    # To control the selection of MyLibInstaller and MyPyBuilder, we
    # have to set it into the cmdclass instance variable, set in
    # Distribution.__init__().
    def __init__(self, *attrs):
        Distribution.__init__(self, *attrs)
        self.cmdclass['build'] = MyBuilder
        self.cmdclass['build_ext'] = MyExtBuilder
        self.cmdclass['install_lib'] = MyLibInstaller

ext_modules = [
    Extension('lxml.etree',
              sources=['src/lxml/etree.pyx'],
              include_dirs=include_dirs,
              runtime_library_dirs=runtime_library_dirs,
              library_dirs=library_dirs,
              libraries=libraries,
              extra_compile_args = extra_compile_args
              ),
    Extension('lxml.c14n',
              sources=['src/lxml/c14n.pyx'],
              include_dirs=include_dirs,
              runtime_library_dirs=runtime_library_dirs,
              library_dirs=library_dirs,
              libraries=libraries,
              extra_compile_args = extra_compile_args
              ),
    ]

setup(name="lxml",
      version="0.1",
      maintainer="Infrae",
      maintainer_email="faassen@infrae.com",
      ext_modules = ext_modules,
      platforms = ["any"],
      packages = packages,
      package_dir = {'': 'src'},
      distclass = MyDistribution,
      )
