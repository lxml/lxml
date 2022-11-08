#!/usr/bin/bash

GCC_VERSION=${GCC_VERSION:=8}
TEST_CFLAGS=
EXTRA_CFLAGS=

# Set up compilers
if [ -z "${OS_NAME##ubuntu*}" ]; then
  echo "Installing requirements [apt]"
  sudo apt-add-repository -y "ppa:ubuntu-toolchain-r/test"
  sudo apt-get update -y -q
  sudo apt-get install -y -q ccache gcc-$GCC_VERSION "libxml2=2.9.13*" "libxml2-dev=2.9.13*" libxslt1.1 libxslt1-dev || exit 1
  sudo /usr/sbin/update-ccache-symlinks
  echo "/usr/lib/ccache" >> $GITHUB_PATH # export ccache to path

  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-$GCC_VERSION 60

  export CC="gcc"
  export PATH="/usr/lib/ccache:$PATH"
  TEST_CFLAGS="-Og -g -fPIC"
  EXTRA_CFLAGS="$TEST_CFLAGS -Wall -Wextra"

elif [ -z "${OS_NAME##macos*}" ]; then
  export CC="clang -Wno-deprecated-declarations"
  TEST_CFLAGS="-Og -g -fPIC"
  EXTRA_CFLAGS="$TEST_CFLAGS -Wall -Wextra"
fi

# Log versions in use
echo "===================="
echo "|VERSIONS INSTALLED|"
echo "===================="
python -c 'import sys; print("Python %s" % (sys.version,))'
if [[ "$CC" ]]; then
  which ${CC%% *}
  ${CC%% *} --version
fi
if [ -z "${OS_NAME##win*}" ]; then
    pkg-config --modversion libxml-2.0 libxslt
fi
echo "===================="

ccache -s || true

# Install python requirements
echo "Installing requirements [python]"
python -m pip install -U pip setuptools wheel
if [ -z "${PYTHON_VERSION##*-dev}" ];
  then python -m pip install --install-option=--cython-compile-minimal https://github.com/cython/cython/archive/master.zip;
  else python -m pip install -r requirements.txt;
fi
if [ -z "${PYTHON_VERSION##2*}" ]; then
  python -m pip install -U beautifulsoup4==4.9.3 cssselect==1.1.0 html5lib==1.1 rnc2rng==2.6.5 ${EXTRA_DEPS} || exit 1
else
  python -m pip install -U beautifulsoup4 cssselect html5lib rnc2rng ${EXTRA_DEPS} || exit 1
fi
if [[ "$COVERAGE" == "true" ]]; then
  python -m pip install "coverage<5" || exit 1
  python -m pip install --pre 'Cython>=3.0a0' || exit 1
fi

# Build
CFLAGS="$CFLAGS $EXTRA_CFLAGS" python -u setup.py build_ext --inplace \
      $(if [ -n "${PYTHON_VERSION##2.*}" ]; then echo -n " -j7 "; fi ) \
      $(if [[ "$COVERAGE" == "true" ]]; then echo -n " --with-coverage"; fi ) \
      || exit 1

ccache -s || true

# Run tests
CFLAGS="$TEST_CFLAGS" PYTHONUNBUFFERED=x make test || exit 1

python setup.py install || exit 1
python -c "from lxml import etree" || exit 1

CFLAGS="-O3 -g1 -mtune=generic -fPIC -flto" \
  LDFLAGS="-flto" \
  make clean wheel || exit 1

ccache -s || true
