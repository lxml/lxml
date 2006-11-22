import sys, os
from setuptools.extension import Extension

try:
    from Pyrex.Distutils import build_ext as build_pyx
    PYREX_INSTALLED = True
except ImportError:
    PYREX_INSTALLED = False

EXT_MODULES = [
    ("etree",       "lxml.etree"),
    ("objectify",   "lxml.objectify")
    ]

def ext_modules(static_libs, static_cflags): 
    if PYREX_INSTALLED:
        source_extension = ".pyx"
    else:
        print ("NOTE: Trying to build without Pyrex, pre-generated "
               "'src/lxml/etree.c' needs to be available.")
        source_extension = ".c"
    
    result = []
    _ext_args = ext_args(static_libs)
    _cflags = cflags(static_cflags)
    _define_macros = define_macros()
    for module, package in EXT_MODULES:
        result.append(
            Extension(
            package,
            sources = ["src/lxml/" + module + source_extension],
            extra_compile_args = ['-w'] + _cflags,
            define_macros = _define_macros,
            **_ext_args
            ))
    return result

def extra_setup_args():
    result = {}
    if PYREX_INSTALLED:
        result['cmdclass'] = {'build_ext': build_pyx}
    return result

def cflags(static_cflags):
    if OPTION_STATIC:
        assert static_cflags, "Static build not configured, see doc/build.txt"
        result = static_cflags
    else:
        result = flags('xslt-config --cflags')
    if OPTION_DEBUG_GCC:
        result.append('-g2')
    return result

def define_macros():
    if OPTION_WITHOUT_ASSERT:
        return [('PYREX_WITHOUT_ASSERTIONS', None)]
    return []

def ext_args(static_libs):
    if OPTION_STATIC:
        assert static_libs, "Static build not configured, see doc/build.txt"
        return {'extra_link_args': static_libs}

    xslt_libs = flags('xslt-config --libs')
    add_libexslt(xslt_libs)
    
    if OPTION_AUTO_RPATH:
        return ext_args_rpath(xslt_libs)
    else:
        return {'extra_link_args': xslt_libs}
    
def flags(cmd):
    wf, rf, ef = os.popen3(cmd)
    return rf.read().split()

def add_libexslt(lib_flags):
    if '-lxslt' in lib_flags:
        xslt, exslt = '-lxslt', '-lexslt'
    else:
        xslt, exslt = 'xslt', 'exslt'
    for i, libname in enumerate(lib_flags):
        if exslt in libname:
            return
        if xslt in libname:
            lib_flags.insert(i, libname.replace(xslt, exslt))
            return

def ext_args_rpath(xslt_libs):
    library_dirs = []
    libraries = []
    extra_link_args = []
    runtime_library_dirs = []
    
    for option in xslt_libs:
        content = option[2:]
        if option.startswith('-L'):
            if not content.startswith('/usr'):
                runtime_library_dirs.append(content)
            library_dirs.append(content)
        elif option.startswith('-l'):
            libraries.append(content)
        else:
            extra_link_args.append(option)

    return {
        'libraries': libraries,
        'library_dirs': library_dirs,
        'extra_link_args': extra_link_args,
        'runtime_library_dirs': runtime_library_dirs,
        }

def has_option(name):
    try:
        sys.argv.remove('--%s' % name)
        return True
    except ValueError:
        return False

# pick up any commandline options
OPTION_WITHOUT_ASSERT = has_option('without-assert')
OPTION_STATIC = has_option('static')
OPTION_DEBUG_GCC = has_option('debug-gcc')
OPTION_AUTO_RPATH = has_option('auto-rpath')
