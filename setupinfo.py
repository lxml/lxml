import sys
import io
import os
import os.path
import subprocess

from setuptools.command.build_ext import build_ext as _build_ext
from distutils.core import Extension
from distutils.errors import CompileError, DistutilsOptionError
from versioninfo import get_base_dir

try:
    import Cython.Compiler.Version
    CYTHON_INSTALLED = True
except ImportError:
    CYTHON_INSTALLED = False

EXT_MODULES = ["lxml.etree", "lxml.objectify"]
COMPILED_MODULES = [
    "lxml.builder",
    "lxml._elementpath",
    "lxml.html.diff",
    "lxml.html.clean",
    "lxml.sax",
]
HEADER_FILES = ['etree.h', 'etree_api.h']

if hasattr(sys, 'pypy_version_info') or (
        getattr(sys, 'implementation', None) and sys.implementation.name != 'cpython'):
    # disable Cython compilation of Python modules in PyPy and other non-CPythons
    del COMPILED_MODULES[:]

SOURCE_PATH = "src"
INCLUDE_PACKAGE_PATH = os.path.join(SOURCE_PATH, 'lxml', 'includes')

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


def _prefer_reldirs(base_dir, dirs):
    return [
        os.path.relpath(path) if path.startswith(base_dir) else path
        for path in dirs
    ]

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
                zlib_version=OPTION_ZLIB_VERSION,
                multicore=OPTION_MULTICORE)

    modules = EXT_MODULES + COMPILED_MODULES
    if OPTION_WITHOUT_OBJECTIFY:
        modules = [entry for entry in modules if 'objectify' not in entry]

    module_files = list(os.path.join(SOURCE_PATH, *module.split('.')) for module in modules)
    c_files_exist = [os.path.exists(module + '.c') for module in module_files]

    use_cython = True
    if CYTHON_INSTALLED and (OPTION_WITH_CYTHON or not all(c_files_exist)):
        print("Building with Cython %s." % Cython.Compiler.Version.version)
        # generate module cleanup code
        from Cython.Compiler import Options
        Options.generate_cleanup_code = 3
        Options.clear_to_none = False
    elif not OPTION_WITHOUT_CYTHON and not all(c_files_exist):
        for exists, module in zip(c_files_exist, module_files):
            if not exists:
                raise RuntimeError(
                    "ERROR: Trying to build without Cython, but pre-generated '%s.c' "
                    "is not available (pass --without-cython to ignore this error)." % module)
    else:
        if not all(c_files_exist):
            for exists, module in zip(c_files_exist, module_files):
                if not exists:
                    print("WARNING: Trying to build without Cython, but pre-generated "
                          "'%s.c' is not available." % module)
        use_cython = False
        print("Building without Cython.")

    if not check_build_dependencies():
        raise RuntimeError("Dependency missing")

    base_dir = get_base_dir()
    _include_dirs = _prefer_reldirs(
        base_dir, include_dirs(static_include_dirs) + [
            SOURCE_PATH,
            INCLUDE_PACKAGE_PATH,
        ])
    _library_dirs = _prefer_reldirs(base_dir, library_dirs(static_library_dirs))
    _cflags = cflags(static_cflags)
    _ldflags = ['-isysroot', get_xcode_isysroot()] if sys.platform == 'darwin' else None
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

    if CYTHON_INSTALLED and OPTION_SHOW_WARNINGS:
        from Cython.Compiler import Errors
        Errors.LEVEL = 0

    cythonize_directives = {
        'binding': True,
    }
    if OPTION_WITH_COVERAGE:
        cythonize_directives['linetrace'] = True

    result = []
    for module, src_file in zip(modules, module_files):
        is_py = module in COMPILED_MODULES
        main_module_source = src_file + (
            '.c' if not use_cython else '.py' if is_py else '.pyx')
        result.append(
            Extension(
                module,
                sources = [main_module_source],
                depends = find_dependencies(module),
                extra_compile_args = _cflags,
                extra_link_args = None if is_py else _ldflags,
                extra_objects = None if is_py else static_binaries,
                define_macros = _define_macros,
                include_dirs = _include_dirs,
                library_dirs = None if is_py else _library_dirs,
                runtime_library_dirs = None if is_py else runtime_library_dirs,
                libraries = None if is_py else _libraries,
            ))
    if CYTHON_INSTALLED and OPTION_WITH_CYTHON_GDB:
        for ext in result:
            ext.cython_gdb = True

    if CYTHON_INSTALLED and use_cython:
        # build .c files right now and convert Extension() objects
        from Cython.Build import cythonize
        result = cythonize(result, compiler_directives=cythonize_directives)

    # for backwards compatibility reasons, provide "etree[_api].h" also as "lxml.etree[_api].h"
    for header_filename in HEADER_FILES:
        src_file = os.path.join(SOURCE_PATH, 'lxml', header_filename)
        dst_file = os.path.join(SOURCE_PATH, 'lxml', 'lxml.' + header_filename)
        if not os.path.exists(src_file):
            continue
        if os.path.exists(dst_file) and os.path.getmtime(dst_file) >= os.path.getmtime(src_file):
            continue

        with io.open(src_file, 'r', encoding='iso8859-1') as f:
            content = f.read()
        for filename in HEADER_FILES:
            content = content.replace('"%s"' % filename, '"lxml.%s"' % filename)
        with io.open(dst_file, 'w', encoding='iso8859-1') as f:
            f.write(content)

    return result


def find_dependencies(module):
    if not CYTHON_INSTALLED or 'lxml.html' in module:
        return []
    base_dir = get_base_dir()
    package_dir = os.path.join(base_dir, SOURCE_PATH, 'lxml')
    includes_dir = os.path.join(base_dir, INCLUDE_PACKAGE_PATH)

    pxd_files = [
        os.path.join(INCLUDE_PACKAGE_PATH, filename)
        for filename in os.listdir(includes_dir)
        if filename.endswith('.pxd')
    ]

    if module == 'lxml.etree':
        pxi_files = [
            os.path.join(SOURCE_PATH, 'lxml', filename)
            for filename in os.listdir(package_dir)
            if filename.endswith('.pxi') and 'objectpath' not in filename
        ]
        pxd_files = [
            filename for filename in pxd_files
            if 'etreepublic' not in filename
        ]
    elif module == 'lxml.objectify':
        pxi_files = [os.path.join(SOURCE_PATH, 'lxml', 'objectpath.pxi')]
    else:
        pxi_files = pxd_files = []

    return pxd_files + pxi_files


def extra_setup_args():
    class CheckLibxml2BuildExt(_build_ext):
        """Subclass to check whether libxml2 is really available if the build fails"""
        def run(self):
            try:
                _build_ext.run(self)  # old-style class in Py2
            except CompileError as e:
                print('Compile failed: %s' % e)
                if not seems_to_have_libxml2():
                    print_libxml_error()
                raise
    result = {'cmdclass': {'build_ext': CheckLibxml2BuildExt}}
    return result


def seems_to_have_libxml2():
    from distutils import ccompiler
    compiler = ccompiler.new_compiler()
    return compiler.has_function(
        'xmlXPathInit',
        include_dirs=include_dirs([]) + ['/usr/include/libxml2'],
        includes=['libxml/xpath.h'],
        library_dirs=library_dirs([]),
        libraries=['xml2'])


def print_libxml_error():
    print('*********************************************************************************')
    print('Could not find function xmlCheckVersion in library libxml2. Is libxml2 installed?')
    if sys.platform in ('darwin',):
        print('Perhaps try: xcode-select --install')
    print('*********************************************************************************')


def libraries():
    standard_libs = []
    if 'linux' in sys.platform:
        standard_libs.append('rt')
    if not OPTION_BUILD_LIBXML2XSLT:
        standard_libs.append('z')
    standard_libs.append('m')

    if sys.platform in ('win32',):
        libs = ['libxslt', 'libexslt', 'libxml2', 'iconv']
        if OPTION_STATIC:
            libs = ['%s_a' % lib for lib in libs]
        libs.extend(['zlib', 'WS2_32'])
    elif OPTION_STATIC:
        libs = standard_libs
    else:
        libs = ['xslt', 'exslt', 'xml2'] + standard_libs
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
    if OPTION_WITH_COVERAGE:
        macros.append(('CYTHON_TRACE_NOGIL', '1'))
    if OPTION_BUILD_LIBXML2XSLT:
        macros.append(('LIBXML_STATIC', None))
        macros.append(('LIBXSLT_STATIC', None))
    # Disable showing C lines in tracebacks, unless explicitly requested.
    macros.append(('CYTHON_CLINE_IN_TRACEBACK', '1' if OPTION_WITH_CLINES else '0'))
    return macros


def run_command(cmd, *args):
    if not cmd:
        return ''
    if args:
        cmd = ' '.join((cmd,) + args)

    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, errors = p.communicate()

    if p.returncode != 0 and errors:
        return ''
    return decode_input(stdout_data).strip()


def check_min_version(version, min_version, libname):
    if not version:
        # this is ok for targets like sdist etc.
        return True
    lib_version = tuple(map(int, version.split('.')[:3]))
    req_version = tuple(map(int, min_version.split('.')[:3]))
    if lib_version < req_version:
        print("Minimum required version of %s is %s. Your system has version %s." % (
            libname, min_version, version))
        return False
    return True


def get_library_version(prog, libname=None):
    if libname:
        return run_command(prog, '--modversion %s' % libname)
    else:
        return run_command(prog, '--version')


PKG_CONFIG = None
XML2_CONFIG = None
XSLT_CONFIG = None

def get_library_versions():
    global XML2_CONFIG, XSLT_CONFIG

    # Pre-built libraries
    if XML2_CONFIG and XSLT_CONFIG:
        xml2_version = get_library_version(XML2_CONFIG)
        xslt_version = get_library_version(XSLT_CONFIG)
        return xml2_version, xslt_version

    # Path to xml2-config and xslt-config specified on the command line
    if OPTION_WITH_XML2_CONFIG:
        xml2_version = get_library_version(OPTION_WITH_XML2_CONFIG)
        if xml2_version and OPTION_WITH_XSLT_CONFIG:
            xslt_version = get_library_version(OPTION_WITH_XSLT_CONFIG)
            if xslt_version:
                XML2_CONFIG = OPTION_WITH_XML2_CONFIG
                XSLT_CONFIG = OPTION_WITH_XSLT_CONFIG
                return xml2_version, xslt_version

    # Try pkg-config
    global PKG_CONFIG
    PKG_CONFIG = os.getenv('PKG_CONFIG', 'pkg-config')
    xml2_version = get_library_version(PKG_CONFIG, 'libxml-2.0')
    if xml2_version:
        xslt_version = get_library_version(PKG_CONFIG, 'libxslt')
        if xml2_version and xslt_version:
            return xml2_version, xslt_version

    # Try xml2-config and xslt-config
    XML2_CONFIG = os.getenv('XML2_CONFIG', 'xml2-config')
    xml2_version = get_library_version(XML2_CONFIG)
    if xml2_version:
        XSLT_CONFIG = os.getenv('XSLT_CONFIG', 'xslt-config')
        xslt_version = get_library_version(XSLT_CONFIG)
        if xml2_version and xslt_version:
            return xml2_version, xslt_version

    # One or both build dependencies not found. Fail on Linux platforms only.
    if sys.platform.startswith('win'):
        return '', ''
    print("Error: Please make sure the libxml2 and libxslt development packages are installed.")
    sys.exit(1)


def check_build_dependencies():
    xml2_version, xslt_version = get_library_versions()

    xml2_ok = check_min_version(xml2_version, '2.7.0', 'libxml2')
    xslt_ok = check_min_version(xslt_version, '1.1.23', 'libxslt')

    if not OPTION_BUILD_LIBXML2XSLT and xml2_version in ('2.9.11', '2.9.12'):
        print("\n"
              "WARNING: The stock libxml2 versions 2.9.11 and 2.9.12 are incompatible"
              " with this lxml version. "
              "They produce excess content on serialisation. "
              "Use a different library version or a static build."
              "\n")

    if xml2_version and xslt_version:
        print("Building against libxml2 %s and libxslt %s" % (xml2_version, xslt_version))
    else:
        print("Building against pre-built libxml2 andl libxslt libraries")

    return (xml2_ok and xslt_ok)


def get_flags(prog, option, libname=None):
    if libname:
        return run_command(prog, '--%s %s' % (option, libname))
    else:
        return run_command(prog, '--%s' % option)


def flags(option):
    if XML2_CONFIG:
        xml2_flags = get_flags(XML2_CONFIG, option)
        xslt_flags = get_flags(XSLT_CONFIG, option)
    else:
        xml2_flags = get_flags(PKG_CONFIG, option, 'libxml-2.0')
        xslt_flags = get_flags(PKG_CONFIG, option, 'libxslt')

    flag_list = xml2_flags.split()
    for flag in xslt_flags.split():
        if flag not in flag_list:
            flag_list.append(flag)
    return flag_list


def get_xcode_isysroot():
    return run_command('xcrun', '--show-sdk-path')


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


def option_value(name, deprecated_for=None):
    for index, option in enumerate(sys.argv):
        if option == '--' + name:
            if index+1 >= len(sys.argv):
                raise DistutilsOptionError(
                    'The option %s requires a value' % option)
            value = sys.argv[index+1]
            sys.argv[index:index+2] = []
            if deprecated_for:
                print_deprecated_option(name, deprecated_for)
            return value
        if option.startswith('--' + name + '='):
            value = option[len(name)+3:]
            sys.argv[index:index+1] = []
            if deprecated_for:
                print_deprecated_option(name, deprecated_for)
            return value
    env_name = name.upper().replace('-', '_')
    env_val = os.getenv(env_name)
    if env_val and deprecated_for:
        print_deprecated_option(env_name, deprecated_for.upper().replace('-', '_'))
    return env_val


def print_deprecated_option(name, new_name):
    print("WARN: Option '%s' is deprecated. Use '%s' instead." % (name, new_name))


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
OPTION_WITH_COVERAGE = has_option('with-coverage')
OPTION_WITH_CLINES = has_option('with-clines')
if OPTION_WITHOUT_CYTHON:
    CYTHON_INSTALLED = False
OPTION_STATIC = staticbuild or has_option('static')
OPTION_DEBUG_GCC = has_option('debug-gcc')
OPTION_SHOW_WARNINGS = has_option('warnings')
OPTION_AUTO_RPATH = has_option('auto-rpath')
OPTION_BUILD_LIBXML2XSLT = staticbuild or has_option('static-deps')
if OPTION_BUILD_LIBXML2XSLT:
    OPTION_STATIC = True
OPTION_WITH_XML2_CONFIG = option_value('with-xml2-config') or option_value('xml2-config', deprecated_for='with-xml2-config')
OPTION_WITH_XSLT_CONFIG = option_value('with-xslt-config') or option_value('xslt-config', deprecated_for='with-xslt-config')
OPTION_LIBXML2_VERSION = option_value('libxml2-version')
OPTION_LIBXSLT_VERSION = option_value('libxslt-version')
OPTION_LIBICONV_VERSION = option_value('libiconv-version')
OPTION_ZLIB_VERSION = option_value('zlib-version')
OPTION_MULTICORE = option_value('multicore')
OPTION_DOWNLOAD_DIR = option_value('download-dir')
if OPTION_DOWNLOAD_DIR is None:
    OPTION_DOWNLOAD_DIR = 'libs'
