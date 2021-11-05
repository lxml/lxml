#!/bin/bash
#
# Called inside the manylinux image
echo "Started $0 $@"

set -e -x
REQUIREMENTS=/io/requirements.txt
[ -n "$WHEELHOUSE" ] || WHEELHOUSE=wheelhouse
SDIST=$1
PACKAGE=$(basename ${SDIST%-*})
SDIST_PREFIX=$(basename ${SDIST%%.tar.gz})
[ -z "$PYTHON_BUILD_VERSION" ] && PYTHON_BUILD_VERSION="*"

build_wheel() {
    pybin="$1"
    source="$2"
    [ -n "$source" ] || source=/io

    env STATIC_DEPS=true \
        RUN_TESTS=true \
        LDFLAGS="$LDFLAGS -fPIC" \
        CFLAGS="$CFLAGS -fPIC" \
        ACLOCAL_PATH=/usr/share/aclocal/ \
        ${pybin}/pip \
            wheel \
            "$source" \
            -w /io/$WHEELHOUSE
}

run_tests() {
    # Install packages and test
    for PYBIN in /opt/python/${PYTHON_BUILD_VERSION}/bin/; do
        ${PYBIN}/python -m pip install $PACKAGE --no-index -f /io/$WHEELHOUSE || exit 1

        # check import as a quick test
        (cd $HOME; ${PYBIN}/python -c 'import lxml.etree, lxml.objectify')
    done
}

prepare_system() {
    #yum install -y zlib-devel
    #rm -fr /opt/python/cp34-*
    echo "Python versions found: $(cd /opt/python && echo cp* | sed -e 's|[^ ]*-||g')"
    ${CC:-gcc} --version
}

build_wheels() {
    # Compile wheels for all python versions
    test -e "$SDIST" && source="$SDIST" || source=
    FIRST=
    SECOND=
    THIRD=
    for PYBIN in /opt/python/${PYTHON_BUILD_VERSION}/bin; do
        # Install build requirements if we need them and file exists
        test -n "$source" -o ! -e "$REQUIREMENTS" \
            || ${PYBIN}/python -m pip install -r "$REQUIREMENTS"

        echo "Starting build with $($PYBIN/python -V)"
        build_wheel "$PYBIN" "$source" &
        THIRD=$!

        [ -z "$FIRST" ] || wait ${FIRST}
        if [ "$(uname -m)" == "aarch64" ]; then FIRST=$THIRD; else FIRST=$SECOND; fi
        SECOND=$THIRD
    done
    wait || exit 1
}

repair_wheels() {
    # Bundle external shared libraries into the wheels
    for whl in /io/$WHEELHOUSE/${SDIST_PREFIX}-*.whl; do
        auditwheel repair $whl -w /io/$WHEELHOUSE || exit 1
    done
}

show_wheels() {
    ls -l /io/$WHEELHOUSE/${SDIST_PREFIX}-*.whl
}

prepare_system
build_wheels
repair_wheels
run_tests
show_wheels
