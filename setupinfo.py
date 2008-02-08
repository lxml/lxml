import sys, os
from distutils.core import Extension

try:
    from Cython.Distutils import build_ext as build_pyx
    import Cython.Compiler.Version
    print("Building with Cython %s." % Cython.Compiler.Version.version)
    CYTHON_INSTALLED = True
except ImportError:
    CYTHON_INSTALLED = False

EXT_MODULES = ["lxml.etree", "lxml.objectify","lxml.pyclasslookup"]

def env_var(name):
    value = os.getenv(name, '')
    return value.split(os.pathsep)

def ext_modules(static_include_dirs, static_library_dirs, static_cflags): 
    if CYTHON_INSTALLED:
        source_extension = ".pyx"
    else:
        print ("NOTE: Trying to build without Cython, pre-generated "
               "'src/lxml/etree.c' needs to be available.")
        source_extension = ".c"

    if OPTION_WITHOUT_OBJECTIFY:
        modules = [ entry for entry in EXT_MODULES
                    if 'objectify' not in entry[0] ]
    else:
        modules = EXT_MODULES

    _include_dirs = include_dirs(static_include_dirs)
    _library_dirs = library_dirs(static_library_dirs)
    _cflags = cflags(static_cflags)
    _define_macros = define_macros()
    _libraries = libraries()

    if OPTION_AUTO_RPATH:
        runtime_library_dirs = _library_dirs
    else:
        runtime_library_dirs = []
    
    result = []
    for module in modules:
        result.append(
            Extension(
            module,
            sources = ["src/lxml/" + module + source_extension],
            extra_compile_args = ['-w'] + _cflags,
            define_macros = _define_macros,
            include_dirs = _include_dirs,
            library_dirs = _library_dirs,
            runtime_library_dirs = runtime_library_dirs,
            libraries = _libraries,
            ))
    return result

def extra_setup_args():
    result = {}
    if CYTHON_INSTALLED:
        result['cmdclass'] = {'build_ext': build_pyx}
    return result

def libraries():
    if sys.platform in ('win32',):
        libs = ['libxslt', 'libexslt', 'libxml2', 'iconv']
    else:
        libs = ['xslt', 'exslt', 'xml2', 'z', 'm']
    if OPTION_STATIC:
        if sys.platform in ('win32',):
            libs = ['%s_a' % lib for lib in libs]
    if sys.platform in ('win32',):
        libs.extend(['zlib', 'WS2_32'])
    return libs

def library_dirs(static_library_dirs):
    if OPTION_STATIC:
        if not static_library_dirs:
            static_library_dirs = env_var('LIBRARY')
        assert static_library_dirs, "Static build not configured, see doc/build.txt"
        return static_library_dirs
    # filter them from xslt-config --libs
    result = []
    possible_library_dirs = flags('libs')
    for possible_library_dir in possible_library_dirs:
        if possible_library_dir.startswith('-L'):
            result.append(possible_library_dir[2:])
    return result

def include_dirs(static_include_dirs):
    if OPTION_STATIC:
        if not static_include_dirs:
            static_include_dirs = env_var('INCLUDE')
        assert static_include_dirs, "Static build not configured, see doc/build.txt"
        return static_include_dirs
    # filter them from xslt-config --cflags
    result = []
    possible_include_dirs = flags('cflags')
    for possible_include_dir in possible_include_dirs:
        if possible_include_dir.startswith('-I'):
            result.append(possible_include_dir[2:])
    return result

def cflags(static_cflags):
    result = []
    if OPTION_DEBUG_GCC:
        result.append('-g2')

    if OPTION_STATIC:
        if not static_cflags:
            static_cflags = env_var('CFLAGS')
        assert static_cflags, "Static build not configured, see doc/build.txt"
        result.extend(static_cflags)
        return result

    # anything from xslt-config --cflags that doesn't start with -I
    possible_cflags = flags('cflags')
    for possible_cflag in possible_cflags:
        if not possible_cflag.startswith('-I'):
            result.append(possible_cflag)
    return result

def define_macros():
    macros = []
    if OPTION_WITHOUT_ASSERT:
        macros.append(('PYREX_WITHOUT_ASSERTIONS', None))
    if OPTION_WITHOUT_THREADING:
        macros.append(('WITHOUT_THREADING', None))
    return macros

def flags(option):
    cmd = "%s --%s" % (find_xslt_config(), option)
    try:
        import subprocess
    except ImportError:
        # Python 2.3
        _, rf, ef = os.popen3(cmd)
    else:
        # Python 2.4+
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rf, ef = p.stdout, p.stderr
    errors = ef.read()
    if errors:
        print("ERROR: %s" % errors)
        print("** make sure the development packages of libxml2 and libxslt are installed **\n")
    return str(rf.read()).split()

XSLT_CONFIG = None

def find_xslt_config():
    global XSLT_CONFIG
    if XSLT_CONFIG:
        return XSLT_CONFIG
    option = '--with-xslt-config='
    for arg in sys.argv:
        if arg.startswith(option):
            sys.argv.remove(arg)
            XSLT_CONFIG = arg[len(option):]
            return XSLT_CONFIG
    else:
        XSLT_CONFIG = 'xslt-config'
    return XSLT_CONFIG

def has_option(name):
    try:
        sys.argv.remove('--%s' % name)
        return True
    except ValueError:
        return False

# pick up any commandline options
OPTION_WITHOUT_OBJECTIFY = has_option('without-objectify')
OPTION_WITHOUT_ASSERT = has_option('without-assert')
OPTION_WITHOUT_THREADING = has_option('without-threading')
OPTION_STATIC = has_option('static')
OPTION_DEBUG_GCC = has_option('debug-gcc')
OPTION_AUTO_RPATH = has_option('auto-rpath')
