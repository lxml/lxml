import os, re, sys
from distutils import log, sysconfig

try:
    from urlparse import urlsplit, urljoin
    from urllib import urlretrieve
except ImportError:
    from urllib.parse import urlsplit, urljoin
    from urllib.request import urlretrieve

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

def download_and_extract_zlatkovic_binaries(destdir):
    url = 'ftp://ftp.zlatkovic.com/pub/libxml/'
    libs = dict(
        libxml2  = None,
        libxslt  = None,
        zlib     = None,
        iconv    = None,
    )
    for fn in ftp_listdir(url):
        for libname in libs:
            if fn.startswith(libname):
                assert libs[libname] is None, 'duplicate listings?'
                assert fn.endswith('.win32.zip')
                libs[libname] = fn

    if not os.path.exists(destdir): os.makedirs(destdir)
    for libname, libfn in libs.items():
        srcfile = urljoin(url, libfn)
        destfile = os.path.join(destdir, libfn)
        print('Retrieving "%s" to "%s"' % (srcfile, destfile))
        urlretrieve(srcfile, destfile)
        d = unpack_zipfile(destfile, destdir)
        libs[libname] = d

    return libs

def unpack_zipfile(zipfn, destdir):
    assert zipfn.endswith('.zip')
    import zipfile
    print('Unpacking %s into %s' % (os.path.basename(zipfn), destdir))
    f = zipfile.ZipFile(zipfn)
    try:
        f.extractall(path=destdir)
    finally:
        f.close()
    edir = os.path.join(destdir, os.path.basename(zipfn)[:-len('.zip')])
    assert os.path.exists(edir), 'missing: %s' % edir
    return edir

def get_prebuilt_libxml2xslt(download_dir, static_include_dirs, static_library_dirs):
    assert sys.platform.startswith('win')
    libs = download_and_extract_zlatkovic_binaries(download_dir)
    for libname, path in libs.items():
        i = os.path.join(path, 'include')
        l = os.path.join(path, 'lib')
        assert os.path.exists(i), 'does not exist: %s' % i
        assert os.path.exists(l), 'does not exist: %s' % l
        static_include_dirs.append(i)
        static_library_dirs.append(l)


## Routines to download and build libxml2/xslt from sources:

LIBXML2_LOCATION = 'ftp://xmlsoft.org/libxml2/'
LIBICONV_LOCATION = 'ftp://ftp.gnu.org/pub/gnu/libiconv/'
match_libfile_version = re.compile('^[^-]*-([.0-9-]+)[.].*').match

def ftp_listdir(url):
    import ftplib, posixpath
    scheme, netloc, path, qs, fragment = urlsplit(url)
    assert scheme.lower() == 'ftp'
    server = ftplib.FTP(netloc)
    server.login()
    files = [posixpath.basename(fn) for fn in server.nlst(path)]
    return files

def tryint(s):
    try:
        return int(s)
    except ValueError:
        return s

def download_libxml2(dest_dir, version=None):
    """Downloads libxml2, returning the filename where the library was downloaded"""
    version_re = re.compile(r'^LATEST_LIBXML2_IS_(.*)$')
    filename = 'libxml2-%s.tar.gz'
    return download_library(dest_dir, LIBXML2_LOCATION, 'libxml2',
                            version_re, filename, version=version)

def download_libxslt(dest_dir, version=None):
    """Downloads libxslt, returning the filename where the library was downloaded"""
    version_re = re.compile(r'^LATEST_LIBXSLT_IS_(.*)$')
    filename = 'libxslt-%s.tar.gz'
    return download_library(dest_dir, LIBXML2_LOCATION, 'libxslt',
                            version_re, filename, version=version)

def download_libiconv(dest_dir, version=None):
    """Downloads libiconv, returning the filename where the library was downloaded"""
    version_re = re.compile(r'^libiconv-([0-9.]+[0-9]).tar.gz$')
    filename = 'libiconv-%s.tar.gz'
    return download_library(dest_dir, LIBICONV_LOCATION, 'libiconv',
                            version_re, filename, version=version)

def download_library(dest_dir, location, name, version_re, filename, 
                     version=None):
    if version is None:
        try:
            fns = ftp_listdir(location)
            versions = []
            for fn in fns:
                match = version_re.search(fn)
                if match:
                    version_string = match.group(1)
                    versions.append((tuple(map(tryint, version_string.split('.'))),
                                     version_string))
            if versions:
                versions.sort()
                version = versions[-1][-1]
                print('Latest version of %s is %s' % (name, version))
            else:
                raise Exception(
                    "Could not find the most current version of the %s from the files: %s"
                    % (name, fns))
        except IOError:
            # network failure - maybe we have the files already?
            latest = (0,0,0)
            fns = os.listdir(dest_dir)
            for fn in fns:
                if fn.startswith(name+'-'):
                    match = match_libfile_version(fn)
                    if match:
                        version = tuple(map(tryint, match.group(1).split('.')))
                        if version > latest:
                            latest = version
                            filename = fn
                            break
            else:
                raise
    filename = filename % version
    full_url = urljoin(location, filename)
    dest_filename = os.path.join(dest_dir, filename)
    if os.path.exists(dest_filename):
        print('Using existing %s downloaded into %s (delete this file if you want to re-download the package)'
              % (name, dest_filename))
    else:
        print('Downloading %s into %s' % (name, dest_filename))
        urlretrieve(full_url, dest_filename)
    return dest_filename

## Backported method of tarfile.TarFile.extractall (doesn't exist in 2.4):
def _extractall(self, path=".", members=None):
    """Extract all members from the archive to the current working
       directory and set owner, modification time and permissions on
       directories afterwards. `path' specifies a different directory
       to extract to. `members' is optional and must be a subset of the
       list returned by getmembers().
    """
    import copy
    is_ignored_file = re.compile(
        r'''[\\/]((test|results?)[\\/]
                  |doc[\\/].*(Log|[.](out|imp|err|png|ent|gif|tif|pdf))$
                  |tests[\\/](.*[\\/])?(?!Makefile)[^\\/]*$
                  |python[\\/].*[.]py$
                 )
        ''', re.X).search

    directories = []

    if members is None:
        members = self

    for tarinfo in members:
        if is_ignored_file(tarinfo.name):
            continue
        if tarinfo.isdir():
            # Extract directories with a safe mode.
            directories.append((tarinfo.name, tarinfo))
            tarinfo = copy.copy(tarinfo)
            tarinfo.mode = 448 # 0700
        self.extract(tarinfo, path)

    # Reverse sort directories.
    directories.sort()
    directories.reverse()

    # Set correct owner, mtime and filemode on directories.
    for name, tarinfo in directories:
        dirpath = os.path.join(path, name)
        try:
            self.chown(tarinfo, dirpath)
            self.utime(tarinfo, dirpath)
            self.chmod(tarinfo, dirpath)
        except tarfile.ExtractError:
            if self.errorlevel > 1:
                raise
            else:
                self._dbg(1, "tarfile: %s" % sys.exc_info()[1])

def unpack_tarball(tar_filename, dest):
    import tarfile
    print('Unpacking %s into %s' % (os.path.basename(tar_filename), dest))
    tar = tarfile.open(tar_filename)
    base_dir = None
    for member in tar:
        base_name = member.name.split('/')[0]
        if base_dir is None:
            base_dir = base_name
        else:
            if base_dir != base_name:
                print('Unexpected path in %s: %s' % (tar_filename, base_name))
    _extractall(tar, dest)
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

def build_libxml2xslt(download_dir, build_dir,
                      static_include_dirs, static_library_dirs,
                      static_cflags, static_binaries,
                      libxml2_version=None, libxslt_version=None, libiconv_version=None,
                      multicore=None):
    safe_mkdir(download_dir)
    safe_mkdir(build_dir)
    libiconv_dir = unpack_tarball(download_libiconv(download_dir, libiconv_version), build_dir)
    libxml2_dir  = unpack_tarball(download_libxml2(download_dir, libxml2_version), build_dir)
    libxslt_dir  = unpack_tarball(download_libxslt(download_dir, libxslt_version), build_dir)
    prefix = os.path.join(os.path.abspath(build_dir), 'libxml2')
    safe_mkdir(prefix)

    call_setup = {}
    env_setup = None
    if sys.platform in ('darwin',):
        import platform
        # We compile Universal if we are on a machine > 10.3
        major_version, minor_version = tuple(map(int, platform.mac_ver()[0].split('.')[:2]))
        if major_version > 7:
            env = os.environ.copy()
            if minor_version < 6:
                env.update({
                    'CFLAGS' : "-arch ppc -arch i386 -isysroot /Developer/SDKs/MacOSX10.4u.sdk -O2",
                    'LDFLAGS' : "-arch ppc -arch i386 -isysroot /Developer/SDKs/MacOSX10.4u.sdk",
                    'MACOSX_DEPLOYMENT_TARGET' : "10.3"
                    })
            else:
                env.update({
                    'CFLAGS' : "-arch ppc -arch i386 -arch x86_64 -O2",
                    'LDFLAGS' : "-arch ppc -arch i386 -arch x86_64",
                    'MACOSX_DEPLOYMENT_TARGET' : "10.6"
                    })
            call_setup['env'] = env

    configure_cmd = ['./configure',
                     '--disable-dependency-tracking',
                     '--disable-shared',
                     '--prefix=%s' % prefix,
                     ]

    # build libiconv
    cmmi(configure_cmd, libiconv_dir, multicore, **call_setup)

    # build libxml2
    libxml2_configure_cmd = configure_cmd + [
        '--without-python',
        '--with-iconv=%s' % prefix]
    try:
        if libxml2_version and tuple(map(tryint, libxml2_version.split('.'))) >= (2,7,3):
            libxml2_configure_cmd.append('--enable-rebuild-docs=no')
    except Exception:
        pass # this isn't required, so ignore any errors
    cmmi(libxml2_configure_cmd, libxml2_dir, multicore, **call_setup)

    # build libxslt
    libxslt_configure_cmd = configure_cmd + [
        '--without-python',
        '--with-libxml-prefix=%s' % prefix,
        ]
    if sys.platform in ('darwin',):
        libxslt_configure_cmd += [
            '--without-crypto',
            ]
    cmmi(libxslt_configure_cmd, libxslt_dir, multicore, **call_setup)

    # collect build setup for lxml
    xslt_config = os.path.join(prefix, 'bin', 'xslt-config')
    xml2_config = os.path.join(prefix, 'bin', 'xml2-config')

    lib_dir = os.path.join(prefix, 'lib')
    static_include_dirs.extend([
            os.path.join(prefix, 'include'),
            os.path.join(prefix, 'include', 'libxml2'),
            os.path.join(prefix, 'include', 'libxslt'),
            os.path.join(prefix, 'include', 'libexslt')])
    static_library_dirs.append(lib_dir)

    for filename in os.listdir(lib_dir):
        if [l for l in ['iconv', 'libxml2', 'libxslt', 'libexslt'] if l in filename]:
            if [ext for ext in ['.a'] if filename.endswith(ext)]:
                static_binaries.append(os.path.join(lib_dir,filename))

    return (xml2_config, xslt_config)
