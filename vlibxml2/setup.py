from distutils.core import setup
from distutils.extension import Extension
from Pyrex.Distutils import build_ext
import os

'''
Note that libxml2 is linked by using xml2 as the library name.

The include path needs to be able to find libxml2 and the lib path needs to be
able to find libxml2.
'''
extensions = [
        Extension("vlibxml2_mod", ["src/extensions/vlibxml2_mod.pyx"],
        libraries = ['xml2'],
        include_dirs = ['/usr/include', '/usr/include/libxml2',],
        library_dirs = ['/usr/lib'],)
]

def getModules():
    import os
    pathGen = os.walk('src/vlibxml2')
    modules = []
    try:
        while True:
            (dirpath, dirnames, filenames) = pathGen.next()
            if '__init__.py' in filenames:
                modules.append(dirpath[4:])
    except StopIteration, stopIter:
        pass
    return modules


os.system("rm -rf MANIFEST")
setup(
        name = 'vlibxml2',
        package_dir = {'': 'src',}, # the package directory
        packages = getModules(),
        ext_modules=extensions,
        cmdclass = {'build_ext': build_ext},
        version='0.1.177',
)
