#!/usr/bin/bash

# Set up compilers
if [ -z "${OS_NAME##ubuntu*}" ]; then
  echo "Installing requirements [apt]"
  sudo apt-add-repository -y "ppa:ubuntu-toolchain-r/test"
  sudo apt update -y -q
  sudo apt install -y -q ccache gdb python-dbg python3-dbg gcc-8 libxml2 libxml2-dev libxslt1.1 libxslt1-dev || exit 1
  sudo /usr/sbin/update-ccache-symlinks
  echo "/usr/lib/ccache" >> $GITHUB_PATH # export ccache to path

  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-8 60 $(if [ -z "${BACKEND##*cpp*}" ]; then echo " --slave /usr/bin/g++ g++ /usr/bin/g++-8"; fi)

  export CC="gcc"
elif [ -z "${OS_NAME##macos*}" ]; then
  export CC="clang -Wno-deprecated-declarations"
fi

# Log versions in use
echo "===================="
echo "|VERSIONS INSTALLED|"
echo "===================="
python -c 'import sys; print("Python %s" % (sys.version,))'
if [ "$CC" ]; then
  which ${CC%% *}
  ${CC%% *} --version
fi
if [ "$CXX" ]; then
  which ${CXX%% *}
  ${CXX%% *} --version
fi
echo "===================="

ccache -s || true

# Install python requirements
echo "Installing requirements [python]"
python -m pip install -U pip wheel
if [ -z "${PYTHON_VERSION##*-dev}" ];
  then python -m pip install --install-option=--no-cython-compile https://github.com/cython/cython/archive/master.zip;
  else python -m pip install -r requirements.txt;
fi
python -m pip install -U beautifulsoup4 cssselect html5lib rnc2rng ${EXTRA_DEPS} || exit 1
if [ "$COVERAGE" == "true" ]; then
  python -m pip install coverage || exit 1
  python -m pip install --pre 'Cython>=3.0a0' || exit 1
fi

# Build
CFLAGS="-O0 -g -fPIC" python -u setup.py build_ext --inplace \
      $(if [ -n "${PYTHON_VERSION##2.*}" ]; then echo -n " -j7 "; fi ) \
      $(if [ "$COVERAGE" == "true" ]; then echo -n "--with-coverage"; fi ) \
      || exit 1

ccache -s || true

# Run tests
CFLAGS="-O0 -g -fPIC" PYTHONUNBUFFERED=x make test || exit 1

python setup.py install || exit 1
python -c "from lxml import etree" || exit 1

ccache -s || true
