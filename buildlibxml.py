import os, re, sys, subprocess, platform
import tarfile
from distutils import log, version
from contextlib import closing
from ftplib import FTP

try:
    from urlparse import urljoin, unquote, urlparse
    from urllib import urlretrieve, urlopen, urlcleanup
except ImportError:
    from urllib.parse import urljoin, unquote, urlparse
    from urllib.request import urlretrieve, urlopen, urlcleanup

multi_make_options = []
try:
    import multiprocessing
    cpus = multiprocessing.cpu_count()
    if cpus > 1:
        if cpus > 5:
            cpus = 5
        multi_make_options = ['-j%d' % (cpus+1)]
except:
    pass


# use pre-built libraries on Windows

def download_and_extract_windows_binaries(destdir):
    url = "https://github.com/mhils/libxml2-win-binaries/releases"
    filenames = list(_list_dir_urllib(url))

    release_path = "/download/%s/" % find_max_version(
        "library release", filenames, re.compile(r"/releases/tag/([0-9.]+[0-9])$"))
    url += release_path
    filenames = [
        filename.rsplit('/', 1)[1]
        for filename in filenames
        if release_path in filename
    ]

    if platform.machine() == 'ARM64':
        arch = "win-arm64"
    elif sys.maxsize > 2**32:
        arch = "win64"
    else:
        arch = "win32"

    if sys.version_info < (3, 5):
        arch = 'vs2008.' + arch

    libs = {}
    for libname in ['libxml2', 'libxslt', 'zlib', 'iconv']:
        libs[libname] = "%s-%s.%s.zip" % (
            libname,
            find_max_version(libname, filenames),
            arch,
        )

    if not os.path.exists(destdir):
        os.makedirs(destdir)

    for libname, libfn in libs.items():
        srcfile = urljoin(url, libfn)
        destfile = os.path.join(destdir, libfn)
        if os.path.exists(destfile + ".keep"):
            print('Using local copy of  "{}"'.format(srcfile))
        else:
            print('Retrieving "%s" to "%s"' % (srcfile, destfile))
            urlcleanup()  # work around FTP bug 27973 in Py2.7.12+
            urlretrieve(srcfile, destfile)
        d = unpack_zipfile(destfile, destdir)
        libs[libname] = d

    return libs


def find_top_dir_of_zipfile(zipfile):
    topdir = None
    files = [f.filename for f in zipfile.filelist]
    dirs = [d for d in files if d.endswith('/')]
    if dirs:
        dirs.sort(key=len)
        topdir = dirs[0]
        topdir = topdir[:topdir.index("/")+1]
        for path in files:
            if not path.startswith(topdir):
                topdir = None
                break
    assert topdir, (
        "cannot determine single top-level directory in zip file %s" %
        zipfile.filename)
    return topdir.rstrip('/')


def unpack_zipfile(zipfn, destdir):
    assert zipfn.endswith('.zip')
    import zipfile
    print('Unpacking %s into %s' % (os.path.basename(zipfn), destdir))
    f = zipfile.ZipFile(zipfn)
    try:
        extracted_dir = os.path.join(destdir, find_top_dir_of_zipfile(f))
        f.extractall(path=destdir)
    finally:
        f.close()
    assert os.path.exists(extracted_dir), 'missing: %s' % extracted_dir
    return extracted_dir


def get_prebuilt_libxml2xslt(download_dir, static_include_dirs, static_library_dirs):
    assert sys.platform.startswith('win')
    libs = download_and_extract_windows_binaries(download_dir)
    for libname, path in libs.items():
        i = os.path.join(path, 'include')
        l = os.path.join(path, 'lib')
        assert os.path.exists(i), 'does not exist: %s' % i
        assert os.path.exists(l), 'does not exist: %s' % l
        static_include_dirs.append(i)
        static_library_dirs.append(l)


## Routines to download and build libxml2/xslt from sources:

LIBXML2_LOCATION = 'http://xmlsoft.org/sources/'
LIBICONV_LOCATION = 'https://ftp.gnu.org/pub/gnu/libiconv/'
ZLIB_LOCATION = 'https://zlib.net/'
match_libfile_version = re.compile('^[^-]*-([.0-9-]+)[.].*').match


def _find_content_encoding(response, default='iso8859-1'):
    from email.message import Message
    content_type = response.headers.get('Content-Type')
    if content_type:
        msg = Message()
        msg.add_header('Content-Type', content_type)
        charset = msg.get_content_charset(default)
    else:
        charset = default
    return charset


def remote_listdir(url):
    try:
        return _list_dir_urllib(url)
    except IOError:
        assert url.lower().startswith('ftp://')
        print("Requesting with urllib failed. Falling back to ftplib. "
              "Proxy argument will be ignored for %s" % url)
        return _list_dir_ftplib(url)


def _list_dir_ftplib(url):
    parts = urlparse(url)
    ftp = FTP(parts.netloc)
    try:
        ftp.login()
        ftp.cwd(parts.path)
        data = []
        ftp.dir(data.append)
    finally:
        ftp.quit()
    return parse_text_ftplist("\n".join(data))


def _list_dir_urllib(url):
    with closing(urlopen(url)) as res:
        charset = _find_content_encoding(res)
        content_type = res.headers.get('Content-Type')
        data = res.read()

    data = data.decode(charset)
    if content_type and content_type.startswith('text/html'):
        files = parse_html_filelist(data)
    else:
        files = parse_text_ftplist(data)
    return files


def http_listfiles(url, re_pattern):
    with closing(urlopen(url)) as res:
        charset = _find_content_encoding(res)
        data = res.read()
    files = re.findall(re_pattern, data.decode(charset))
    return files


def parse_text_ftplist(s):
    for line in s.splitlines():
        if not line.startswith('d'):
            # -rw-r--r--   1 ftp      ftp           476 Sep  1  2011 md5sum.txt
            # Last (9th) element is 'md5sum.txt' in the above example, but there
            # may be variations, so we discard only the first 8 entries.
            yield line.split(None, 8)[-1]


def parse_html_filelist(s):
    re_href = re.compile(
        r'<a\s+(?:[^>]*\s+)?href=["\']([^;?"\']+?)[;?"\']',
        re.I|re.M)
    links = set(re_href.findall(s))
    for link in links:
        if not link.endswith('/'):
            yield unquote(link)


def tryint(s):
    try:
        return int(s)
    except ValueError:
        return s


def download_libxml2(dest_dir, version=None):
    """Downloads libxml2, returning the filename where the library was downloaded"""
    #version_re = re.compile(r'LATEST_LIBXML2_IS_([0-9.]+[0-9](?:-[abrc0-9]+)?)')
    version_re = re.compile(r'libxml2-([0-9.]+[0-9]).tar.gz')
    filename = 'libxml2-%s.tar.gz'
    return download_library(dest_dir, LIBXML2_LOCATION, 'libxml2',
                            version_re, filename, version=version)


def download_libxslt(dest_dir, version=None):
    """Downloads libxslt, returning the filename where the library was downloaded"""
    #version_re = re.compile(r'LATEST_LIBXSLT_IS_([0-9.]+[0-9](?:-[abrc0-9]+)?)')
    version_re = re.compile(r'libxslt-([0-9.]+[0-9]).tar.gz')
    filename = 'libxslt-%s.tar.gz'
    return download_library(dest_dir, LIBXML2_LOCATION, 'libxslt',
                            version_re, filename, version=version)


def download_libiconv(dest_dir, version=None):
    """Downloads libiconv, returning the filename where the library was downloaded"""
    version_re = re.compile(r'libiconv-([0-9.]+[0-9]).tar.gz')
    filename = 'libiconv-%s.tar.gz'
    return download_library(dest_dir, LIBICONV_LOCATION, 'libiconv',
                            version_re, filename, version=version)


def download_zlib(dest_dir, version):
    """Downloads zlib, returning the filename where the library was downloaded"""
    version_re = re.compile(r'zlib-([0-9.]+[0-9]).tar.gz')
    filename = 'zlib-%s.tar.gz'
    return download_library(dest_dir, ZLIB_LOCATION, 'zlib',
                            version_re, filename, version=version)


def find_max_version(libname, filenames, version_re=None):
    if version_re is None:
        version_re = re.compile(r'%s-([0-9.]+[0-9](?:-[abrc0-9]+)?)' % libname)
    versions = []
    for fn in filenames:
        match = version_re.search(fn)
        if match:
            version_string = match.group(1)
            versions.append((tuple(map(tryint, version_string.split('.'))),
                             version_string))
    if not versions:
        raise Exception(
            "Could not find the most current version of %s from the files: %s" % (
                libname, filenames))
    versions.sort()
    version_string = versions[-1][-1]
    print('Latest version of %s is %s' % (libname, version_string))
    return version_string


def download_library(dest_dir, location, name, version_re, filename, version=None):
    if version is None:
        try:
            if location.startswith('ftp://'):
                fns = remote_listdir(location)
            else:
                fns = http_listfiles(location, '(%s)' % filename.replace('%s', '(?:[0-9.]+[0-9])'))
            version = find_max_version(name, fns, version_re)
        except IOError:
            # network failure - maybe we have the files already?
            latest = (0,0,0)
            fns = os.listdir(dest_dir)
            for fn in fns:
                if fn.startswith(name+'-'):
                    match = match_libfile_version(fn)
                    if match:
                        version_tuple = tuple(map(tryint, match.group(1).split('.')))
                        if version_tuple > latest:
                            latest = version_tuple
                            filename = fn
                            version = None
            if latest == (0,0,0):
                raise
    if version:
        filename = filename % version
    full_url = urljoin(location, filename)
    dest_filename = os.path.join(dest_dir, filename)
    if os.path.exists(dest_filename):
        print(('Using existing %s downloaded into %s '
               '(delete this file if you want to re-download the package)') % (
            name, dest_filename))
    else:
        print('Downloading %s into %s from %s' % (name, dest_filename, full_url))
        urlcleanup()  # work around FTP bug 27973 in Py2.7.12
        urlretrieve(full_url, dest_filename)
    return dest_filename


def unpack_tarball(tar_filename, dest):
    print('Unpacking %s into %s' % (os.path.basename(tar_filename), dest))
    tar = tarfile.open(tar_filename)
    base_dir = None
    for member in tar:
        base_name = member.name.split('/')[0]
        if base_dir is None:
            base_dir = base_name
        elif base_dir != base_name:
            print('Unexpected path in %s: %s' % (tar_filename, base_name))
    tar.extractall(dest)
    tar.close()
    return os.path.join(dest, base_dir)


def call_subprocess(cmd, **kw):
    import subprocess
    cwd = kw.get('cwd', '.')
    cmd_desc = ' '.join(cmd)
    log.info('Running "%s" in %s' % (cmd_desc, cwd))
    returncode = subprocess.call(cmd, **kw)
    if returncode:
        raise Exception('Command "%s" returned code %s' % (cmd_desc, returncode))


def safe_mkdir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def cmmi(configure_cmd, build_dir, multicore=None, **call_setup):
    print('Starting build in %s' % build_dir)
    call_subprocess(configure_cmd, cwd=build_dir, **call_setup)
    if not multicore:
        make_jobs = multi_make_options
    elif int(multicore) > 1:
        make_jobs = ['-j%s' % multicore]
    else:
        make_jobs = []
    call_subprocess(
        ['make'] + make_jobs,
        cwd=build_dir, **call_setup)
    call_subprocess(
        ['make'] + make_jobs + ['install'],
        cwd=build_dir, **call_setup)


def configure_darwin_env(env_setup):
    import platform
    # configure target architectures on MacOS-X (x86_64 only, by default)
    major_version, minor_version = tuple(map(int, platform.mac_ver()[0].split('.')[:2]))
    if major_version > 7:
        env_default = {
            'CFLAGS': "-arch x86_64 -O2",
            'LDFLAGS': "-arch x86_64",
            'MACOSX_DEPLOYMENT_TARGET': "10.6"
        }
        env_default.update(os.environ)
        env_setup['env'] = env_default


def build_libxml2xslt(download_dir, build_dir,
                      static_include_dirs, static_library_dirs,
                      static_cflags, static_binaries,
                      libxml2_version=None,
                      libxslt_version=None,
                      libiconv_version=None,
                      zlib_version=None,
                      multicore=None):
    safe_mkdir(download_dir)
    safe_mkdir(build_dir)
    zlib_dir = unpack_tarball(download_zlib(download_dir, zlib_version), build_dir)
    libiconv_dir = unpack_tarball(download_libiconv(download_dir, libiconv_version), build_dir)
    libxml2_dir  = unpack_tarball(download_libxml2(download_dir, libxml2_version), build_dir)
    libxslt_dir  = unpack_tarball(download_libxslt(download_dir, libxslt_version), build_dir)
    prefix = os.path.join(os.path.abspath(build_dir), 'libxml2')
    lib_dir = os.path.join(prefix, 'lib')
    safe_mkdir(prefix)

    lib_names = ['libxml2', 'libexslt', 'libxslt', 'iconv', 'libz']
    existing_libs = {
        lib: os.path.join(lib_dir, filename)
        for lib in lib_names
        for filename in os.listdir(lib_dir)
        if lib in filename and filename.endswith('.a')
    } if os.path.isdir(lib_dir) else {}

    def has_current_lib(name, build_dir, _build_all_following=[False]):
        if _build_all_following[0]:
            return False  # a dependency was rebuilt => rebuilt this lib as well
        lib_file = existing_libs.get(name)
        found = lib_file and os.path.getmtime(lib_file) > os.path.getmtime(build_dir)
        if found:
            print("Found pre-built '%s'" % name)
        else:
            # also rebuild all following libs (which may depend on this one)
            _build_all_following[0] = True
        return found

    call_setup = {}
    if sys.platform == 'darwin':
        configure_darwin_env(call_setup)

    configure_cmd = ['./configure',
                     '--disable-dependency-tracking',
                     '--disable-shared',
                     '--prefix=%s' % prefix,
                     ]

    # build zlib
    zlib_configure_cmd = [
        './configure',
        '--prefix=%s' % prefix,
    ]
    if not has_current_lib("libz", zlib_dir):
        cmmi(zlib_configure_cmd, zlib_dir, multicore, **call_setup)

    # build libiconv
    if not has_current_lib("iconv", libiconv_dir):
        cmmi(configure_cmd, libiconv_dir, multicore, **call_setup)

    # build libxml2
    libxml2_configure_cmd = configure_cmd + [
        '--without-python',
        '--with-iconv=%s' % prefix,
        '--with-zlib=%s' % prefix,
    ]

    if not libxml2_version:
        libxml2_version = os.path.basename(libxml2_dir).split('-', 1)[-1]

    if tuple(map(tryint, libxml2_version.split('-', 1)[0].split('.'))) >= (2, 9, 5):
        libxml2_configure_cmd.append('--without-lzma')  # can't currently build that

    try:
        if tuple(map(tryint, libxml2_version.split('-', 1)[0].split('.'))) >= (2, 7, 3):
            libxml2_configure_cmd.append('--enable-rebuild-docs=no')
    except Exception:
        pass # this isn't required, so ignore any errors
    if not has_current_lib("libxml2", libxml2_dir):
        cmmi(libxml2_configure_cmd, libxml2_dir, multicore, **call_setup)

    # Fix up libxslt configure script (needed up to and including 1.1.34)
    # https://gitlab.gnome.org/GNOME/libxslt/-/commit/90c34c8bb90e095a8a8fe8b2ce368bd9ff1837cc
    with open(os.path.join(libxslt_dir, "configure"), 'rb') as f:
        config_script = f.read()
    if b' --libs print ' in config_script:
        config_script = config_script.replace(b' --libs print ', b' --libs ')
        with open(os.path.join(libxslt_dir, "configure"), 'wb') as f:
            f.write(config_script)

    # build libxslt
    libxslt_configure_cmd = configure_cmd + [
        '--without-python',
        '--with-libxml-prefix=%s' % prefix,
        '--without-crypto',
    ]
    if not (has_current_lib("libxslt", libxslt_dir) and has_current_lib("libexslt", libxslt_dir)):
        cmmi(libxslt_configure_cmd, libxslt_dir, multicore, **call_setup)

    # collect build setup for lxml
    xslt_config = os.path.join(prefix, 'bin', 'xslt-config')
    xml2_config = os.path.join(prefix, 'bin', 'xml2-config')

    static_include_dirs.extend([
            os.path.join(prefix, 'include'),
            os.path.join(prefix, 'include', 'libxml2'),
            os.path.join(prefix, 'include', 'libxslt'),
            os.path.join(prefix, 'include', 'libexslt')])
    static_library_dirs.append(lib_dir)

    listdir = os.listdir(lib_dir)
    static_binaries += [os.path.join(lib_dir, filename)
        for lib in lib_names
        for filename in listdir
        if lib in filename and filename.endswith('.a')]

    return xml2_config, xslt_config
