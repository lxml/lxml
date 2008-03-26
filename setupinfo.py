import sys, os, os.path
from distutils.core import Extension

from versioninfo import get_base_dir, split_version

try:
    from Cython.Distutils import build_ext as build_pyx
    import Cython.Compiler.Version
    CYTHON_INSTALLED = True
except ImportError:
    CYTHON_INSTALLED = False

EXT_MODULES = ["lxml.etree", "lxml.objectify"]

PACKAGE_PATH = "src/lxml/"

def env_var(name):
    value = os.getenv(name, '')
    return value.split(os.pathsep)

def ext_modules(static_include_dirs, static_library_dirs, static_cflags): 
    if CYTHON_INSTALLED:
        source_extension = ".pyx"
        print("Building with Cython %s." % Cython.Compiler.Version.version)
    else:
        print ("NOTE: Trying to build without Cython, pre-generated "
               "'%setree.c' needs to be available." % PACKAGE_PATH)
        source_extension = ".c"

    if OPTION_WITHOUT_OBJECTIFY:
        modules = [ entry for entry in EXT_MODULES
                    if 'objectify' not in entry ]
    else:
        modules = EXT_MODULES

    lib_versions = get_library_versions()
    if lib_versions[0]:
        print("Using build configuration of libxml2 %s and libxslt %s" % 
              lib_versions)
    else:
        print("Using build configuration of libxslt %s" % 
              lib_versions[1])

    _include_dirs = include_dirs(static_include_dirs)
    _library_dirs = library_dirs(static_library_dirs)
    _cflags = cflags(static_cflags)
    _define_macros = define_macros()
    _libraries = libraries()

    if _library_dirs:
        message = "Building against libxml2/libxslt in "
        if len(_library_dirs) > 1:
            print(message + "one of the following directories:")
            for dir in _library_dirs:
                print("  " + dir)
        else:
            print(message + "the following directory: " +
                  _library_dirs[0])

    if OPTION_AUTO_RPATH:
        runtime_library_dirs = _library_dirs
    else:
        runtime_library_dirs = []
    
    result = []
    for module in modules:
        main_module_source = PACKAGE_PATH + module + source_extension
        dependencies = find_dependencies(module)
        result.append(
            Extension(
            module,
            sources = [main_module_source] + dependencies,
            extra_compile_args = ['-w'] + _cflags,
            define_macros = _define_macros,
            include_dirs = _include_dirs,
            library_dirs = _library_dirs,
            runtime_library_dirs = runtime_library_dirs,
            libraries = _libraries,
            ))
    return result

def find_dependencies(module):
    if not CYTHON_INSTALLED:
        return []
    from Cython.Compiler.Version import version
#    if split_version(version) <= (0,9,6,12):
#        return []

    package_dir = os.path.join(get_base_dir(), PACKAGE_PATH)
    files = os.listdir(package_dir)
    pxd_files = [ os.path.join(PACKAGE_PATH, filename) for filename in files
                  if filename.endswith('.pxd') ]

    if 'etree' in module:
        pxi_files = [ os.path.join(PACKAGE_PATH, filename)
                      for filename in files
                      if filename.endswith('.pxi')
                      and 'objectpath' not in filename ]
        pxd_files = [ filename for filename in pxd_files
                      if 'etreepublic' not in filename ]
    elif 'objectify' in module:
        pxi_files = [ os.path.join(PACKAGE_PATH, 'objectpath.pxi') ]
    else:
        pxi_files = []

    return pxd_files + pxi_files

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

_ERROR_PRINTED = False

def run_command(cmd, *args):
    if not cmd:
        return ''
    if args:
        cmd = ' '.join((cmd,) + args)
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
    global _ERROR_PRINTED
    if errors and not _ERROR_PRINTED:
        _ERROR_PRINTED = True
        print("ERROR: %s" % errors)
        print("** make sure the development packages of libxml2 and libxslt are installed **\n")
    output = rf.read()
    return (output or '').strip()

def get_library_versions():
    xml2_version = run_command(find_xml2_config(), "--version")
    xslt_version = run_command(find_xslt_config(), "--version")
    return xml2_version, xslt_version

def flags(option):
    xml2_flags = run_command(find_xml2_config(), "--%s" % option)
    xslt_flags = run_command(find_xslt_config(), "--%s" % option)

    flag_list = xml2_flags.split()
    for flag in xslt_flags.split():
        if flag not in flag_list:
            flag_list.append(flag)
    return flag_list

XSLT_CONFIG = None
XML2_CONFIG = None

def find_xml2_config():
    global XML2_CONFIG
    if XML2_CONFIG:
        return XML2_CONFIG
    option = '--with-xml2-config='
    for arg in sys.argv:
        if arg.startswith(option):
            sys.argv.remove(arg)
            XML2_CONFIG = arg[len(option):]
            return XML2_CONFIG
    else:
        # default: do nothing, rely only on xslt-config
        XML2_CONFIG = os.getenv('XML2_CONFIG', '')
    return XML2_CONFIG

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
        XSLT_CONFIG = os.getenv('XSLT_CONFIG', 'xslt-config')
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
