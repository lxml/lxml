#!/usr/bin/bash

set -x

GCC_VERSION=${GCC_VERSION:=9}
TEST_CFLAGS=
EXTRA_CFLAGS=
EXTRA_LDFLAGS=
SAVED_GITHUB_API_TOKEN="${GITHUB_API_TOKEN}"
unset GITHUB_API_TOKEN  # remove from env

# Set up compilers
if [ -z "${OS_NAME##ubuntu*}" ]; then
  echo "Installing requirements [apt]"
  sudo apt-add-repository -y "ppa:ubuntu-toolchain-r/test"
  sudo apt-get update -y -q
  sudo apt-get install -y -q ccache gcc-$GCC_VERSION || exit 1
  if [ -n "${STATIC_DEPS##true}" ]; then
    # Ubuntu 22.04 has libxml2 2.9.13, Ubuntu 24.04 has 2.9.14
    sudo apt-get install -y -q "libxml2=2.9.14*" "libxml2-dev=2.9.14*" libxslt1.1 libxslt1-dev  \
    ||  sudo apt-get install -y -q "libxml2=2.9.13*" "libxml2-dev=2.9.13*" libxslt1.1 libxslt1-dev
  fi
  sudo /usr/sbin/update-ccache-symlinks
  echo "/usr/lib/ccache" >> $GITHUB_PATH # export ccache to path

  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-$GCC_VERSION 60

  export CC="gcc"
  export PATH="/usr/lib/ccache:$PATH"
  TEST_CFLAGS="-Og -g -fPIC"
  EXTRA_CFLAGS="-Wall -Wextra -D__lxml_DEBUG_ATOMICS=1"

elif [ -z "${OS_NAME##macos*}" ]; then
  export CC="clang -Wno-deprecated-declarations"
  TEST_CFLAGS="-Og -g -fPIC -arch arm64 -arch x86_64"
  EXTRA_LDFLAGS="-arch arm64 -arch x86_64"
  EXTRA_CFLAGS="-Wall -Wextra -arch arm64 -arch x86_64 -D__lxml_DEBUG_ATOMICS=1"
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
python -m pip install -U pip setuptools

if [ -z "${PYTHON_VERSION##*-dev}" ];
  then CYTHON_COMPILE=false  python -m pip install https://github.com/cython/cython/archive/master.zip;
  else python -m pip install -r requirements.txt;
fi

python -m pip install -U beautifulsoup4 cssselect html5lib rnc2rng ${EXTRA_DEPS} || exit 1
python -m pip install --no-deps lxml_html_clean || exit 1

if [[ "$COVERAGE" == "true" ]]; then
  python -m pip install "coverage<5" || exit 1
fi

# Build
GITHUB_API_TOKEN="${SAVED_GITHUB_API_TOKEN}" \
      CFLAGS="$CFLAGS $TEST_CFLAGS $EXTRA_CFLAGS" \
      LDFLAGS="$LDFLAGS $EXTRA_LDFLAGS" \
      python -u setup.py build_ext --inplace --warnings -j7 \
      $(if [[ "$COVERAGE" == "true" ]]; then echo -n " --with-coverage"; fi ) \
      || exit 1

# Run tests
echo "Running the tests ..."
GITHUB_API_TOKEN="${SAVED_GITHUB_API_TOKEN}" \
      CFLAGS="$TEST_CFLAGS $EXTRA_CFLAGS" \
      LDFLAGS="$LDFLAGS $EXTRA_LDFLAGS" \
      PYTHONUNBUFFERED=x \
      make test || exit 1

ccache -s || true
