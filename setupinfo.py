import sys, os, os.path
from distutils.core import Extension
from distutils.errors import DistutilsOptionError
from versioninfo import get_base_dir, split_version

try:
    from Cython.Distutils import build_ext as build_pyx
    import Cython.Compiler.Version
    CYTHON_INSTALLED = True
except ImportError:
    CYTHON_INSTALLED = False

EXT_MODULES = ["lxml.etree", "lxml.objectify"]

PACKAGE_PATH = "src%slxml%s" % (os.path.sep, os.path.sep)
INCLUDE_PACKAGE_PATH = PACKAGE_PATH + 'includes'

if sys.version_info[0] >= 3:
    _system_encoding = sys.getdefaultencoding()
    if _system_encoding is None:
        _system_encoding = "iso-8859-1" # :-)
    def decode_input(data):
        if isinstance(data, str):
            return data
        return data.decode(_system_encoding)
else:
    def decode_input(data):
        return data

def env_var(name):
    value = os.getenv(name)
    if value:
        value = decode_input(value)
        if sys.platform == 'win32' and ';' in value:
            return value.split(';')
        else:
            return value.split()
    else:
        return []

def ext_modules(static_include_dirs, static_library_dirs,
                static_cflags, static_binaries):
    global XML2_CONFIG, XSLT_CONFIG
    if OPTION_BUILD_LIBXML2XSLT:
        from buildlibxml import build_libxml2xslt, get_prebuilt_libxml2xslt
        if sys.platform.startswith('win'):
            get_prebuilt_libxml2xslt(
                OPTION_DOWNLOAD_DIR, static_include_dirs, static_library_dirs)
        else:
            XML2_CONFIG, XSLT_CONFIG = build_libxml2xslt(
                OPTION_DOWNLOAD_DIR, 'build/tmp',
                static_include_dirs, static_library_dirs,
                static_cflags, static_binaries,
                libiconv_version=OPTION_LIBICONV_VERSION,
                libxml2_version=OPTION_LIBXML2_VERSION,
                libxslt_version=OPTION_LIBXSLT_VERSION,
                multicore=OPTION_MULTICORE)

    if OPTION_WITHOUT_OBJECTIFY:
        modules = [ entry for entry in EXT_MODULES
                    if 'objectify' not in entry ]
    else:
        modules = EXT_MODULES

    c_files_exist = [ os.path.exists('%s%s.c' % (PACKAGE_PATH, module)) for module in modules ]

    if CYTHON_INSTALLED and (OPTION_WITH_CYTHON or False in c_files_exist):
        source_extension = ".pyx"
        print("Building with Cython %s." % Cython.Compiler.Version.version)
        # generate module cleanup code
        from Cython.Compiler import Options
        Options.generate_cleanup_code = 3
        Options.clear_to_none = False
    elif not OPTION_WITHOUT_CYTHON and False in c_files_exist:
        for exists, module in zip(c_files_exist, modules):
            if not exists:
                raise RuntimeError(
                    "ERROR: Trying to build without Cython, but pre-generated '%s%s.c' "
                    "is not available (pass --without-cython to ignore this error)." % (
                        PACKAGE_PATH, module))
    else:
        if False in c_files_exist:
            for exists, module in zip(c_files_exist, modules):
                if not exists:
                    print("WARNING: Trying to build without Cython, but pre-generated "
                          "'%s%s.c' is not available." % (PACKAGE_PATH, module))
        source_extension = ".c"
        print("Building without Cython.")

    lib_versions = get_library_versions()
    versions_ok = True
    if lib_versions[0]:
        print("Using build configuration of libxml2 %s and libxslt %s" %
              lib_versions)
        versions_ok = check_min_version(lib_versions[0], (2, 7, 0), 'libxml2')
    else:
        print("Using build configuration of libxslt %s" %
              lib_versions[1])
    versions_ok |= check_min_version(lib_versions[1], (1, 1, 23), 'libxslt')
    if not versions_ok:
        raise RuntimeError("Dependency missing")

    _include_dirs = include_dirs(static_include_dirs)
    _library_dirs = library_dirs(static_library_dirs)
    _cflags = cflags(static_cflags)
    _define_macros = define_macros()
    _libraries = libraries()

    _include_dirs.append(os.path.join(get_base_dir(), INCLUDE_PACKAGE_PATH))

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

    if CYTHON_INSTALLED and OPTION_SHOW_WARNINGS:
        from Cython.Compiler import Errors
        Errors.LEVEL = 0

    result = []
    for module in modules:
        main_module_source = PACKAGE_PATH + module + source_extension
        result.append(
            Extension(
                module,
                sources = [main_module_source],
                depends = find_dependencies(module),
                extra_compile_args = _cflags,
                extra_objects = static_binaries,
                define_macros = _define_macros,
                include_dirs = _include_dirs,
                library_dirs = _library_dirs,
                runtime_library_dirs = runtime_library_dirs,
                libraries = _libraries,
            ))
    if CYTHON_INSTALLED and OPTION_WITH_CYTHON_GDB:
        for ext in result:
            ext.cython_gdb = True

    if CYTHON_INSTALLED and source_extension == '.pyx':
        # build .c files right now and convert Extension() objects
        from Cython.Build import cythonize
        result = cythonize(result)

    return result

def find_dependencies(module):
    if not CYTHON_INSTALLED:
        return []
    base_dir = get_base_dir()
    package_dir = os.path.join(base_dir, PACKAGE_PATH)
    includes_dir = os.path.join(base_dir, INCLUDE_PACKAGE_PATH)
    pxd_files = [ os.path.join(includes_dir, filename)
                  for filename in os.listdir(includes_dir)
                  if filename.endswith('.pxd') ]

    if 'etree' in module:
        pxi_files = [ os.path.join(PACKAGE_PATH, filename)
                      for filename in os.listdir(package_dir)
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
        if OPTION_STATIC:
            libs = ['%s_a' % lib for lib in libs]
        libs.extend(['zlib', 'WS2_32'])
    elif OPTION_STATIC:
        libs = ['z', 'm']
    else:
        libs = ['xslt', 'exslt', 'xml2', 'z', 'm']
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
    if not OPTION_SHOW_WARNINGS:
        result.append('-w')
    if OPTION_DEBUG_GCC:
        result.append('-g2')

    if OPTION_STATIC:
        if not static_cflags:
            static_cflags = env_var('CFLAGS')
        result.extend(static_cflags)
    else:
        # anything from xslt-config --cflags that doesn't start with -I
        possible_cflags = flags('cflags')
        for possible_cflag in possible_cflags:
            if not possible_cflag.startswith('-I'):
                result.append(possible_cflag)

    if sys.platform in ('darwin',):
        for opt in result:
            if 'flat_namespace' in opt:
                break
        else:
            result.append('-flat_namespace')

    return result

def define_macros():
    macros = []
    if OPTION_WITHOUT_ASSERT:
        macros.append(('PYREX_WITHOUT_ASSERTIONS', None))
    if OPTION_WITHOUT_THREADING:
        macros.append(('WITHOUT_THREADING', None))
    if OPTION_WITH_REFNANNY:
        macros.append(('CYTHON_REFNANNY', None))
    if OPTION_WITH_UNICODE_STRINGS:
        macros.append(('LXML_UNICODE_STRINGS', '1'))
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
        sf, rf, ef = os.popen3(cmd)
        sf.close()
        errors = ef.read()
        stdout_data = rf.read()
    else:
        # Python 2.4+
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_data, errors = p.communicate()
    global _ERROR_PRINTED
    if errors and not _ERROR_PRINTED:
        _ERROR_PRINTED = True
        print("ERROR: %s" % errors)
        print("** make sure the development packages of libxml2 and libxslt are installed **\n")
    return decode_input(stdout_data).strip()


def check_min_version(version, min_version, error_name):
    if not version:
        # this is ok for targets like sdist etc.
        return True
    version = tuple(map(int, version.split('.')[:3]))
    min_version = tuple(min_version)
    if version < min_version:
        print("Minimum required version of %s is %s, found %s" % (
            error_name, '.'.join(map(str, version)), '.'.join(map(str, min_version))))
        return False
    return True


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

## Option handling:

def has_option(name):
    try:
        sys.argv.remove('--%s' % name)
        return True
    except ValueError:
        pass
    # allow passing all cmd line options also as environment variables
    env_val = os.getenv(name.upper().replace('-', '_'), 'false').lower()
    if env_val == "true":
        return True
    return False

def option_value(name):
    for index, option in enumerate(sys.argv):
        if option == '--' + name:
            if index+1 >= len(sys.argv):
                raise DistutilsOptionError(
                    'The option %s requires a value' % option)
            value = sys.argv[index+1]
            sys.argv[index:index+2] = []
            return value
        if option.startswith('--' + name + '='):
            value = option[len(name)+3:]
            sys.argv[index:index+1] = []
            return value
    env_val = os.getenv(name.upper().replace('-', '_'))
    return env_val

staticbuild = bool(os.environ.get('STATICBUILD', ''))
# pick up any commandline options and/or env variables
OPTION_WITHOUT_OBJECTIFY = has_option('without-objectify')
OPTION_WITH_UNICODE_STRINGS = has_option('with-unicode-strings')
OPTION_WITHOUT_ASSERT = has_option('without-assert')
OPTION_WITHOUT_THREADING = has_option('without-threading')
OPTION_WITHOUT_CYTHON = has_option('without-cython')
OPTION_WITH_CYTHON = has_option('with-cython')
OPTION_WITH_CYTHON_GDB = has_option('cython-gdb')
OPTION_WITH_REFNANNY = has_option('with-refnanny')
if OPTION_WITHOUT_CYTHON:
    CYTHON_INSTALLED = False
OPTION_STATIC = staticbuild or has_option('static')
OPTION_DEBUG_GCC = has_option('debug-gcc')
OPTION_SHOW_WARNINGS = has_option('warnings')
OPTION_AUTO_RPATH = has_option('auto-rpath')
OPTION_BUILD_LIBXML2XSLT = staticbuild or has_option('static-deps')
if OPTION_BUILD_LIBXML2XSLT:
    OPTION_STATIC = True
OPTION_LIBXML2_VERSION = option_value('libxml2-version')
OPTION_LIBXSLT_VERSION = option_value('libxslt-version')
OPTION_LIBICONV_VERSION = option_value('libiconv-version')
OPTION_MULTICORE = option_value('multicore')
OPTION_DOWNLOAD_DIR = option_value('download-dir')
if OPTION_DOWNLOAD_DIR is None:
    OPTION_DOWNLOAD_DIR = 'libs'
