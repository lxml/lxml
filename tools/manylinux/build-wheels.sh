#!/bin/bash
#
# Called inside the manylinux image
echo "Started $0 $@"

set -e -x
REQUIREMENTS=/io/requirements.txt
WHEELHOUSE=/io/wheelhouse
SDIST=$1

build_wheel() {
    source="$1"
    [ -n "$source" ] || source=/io

    env STATIC_DEPS=true \
        LDFLAGS="$LDFLAGS -fPIC" \
        CFLAGS="$CFLAGS -fPIC" \
        ${PYBIN}/pip \
            wheel \
            "$source" \
            -w $WHEELHOUSE
}

assert_importable() {
    # Install packages and test
    for PYBIN in /opt/python/*/bin/; do
        ${PYBIN}/pip install lxml --no-index -f $WHEELHOUSE

        (cd $HOME; ${PYBIN}/python -c 'import lxml.etree, lxml.objectify')
    done
}

prepare_system() {
    yum install -y zlib-devel
    # Remove Python 2.6 symlinks
    rm -f /opt/python/cp26*
}

build_wheels() {
    # Compile wheels for all python versions
    test -e "$SDIST" && source="$SDIST" || source=
    FIRST=
    SECOND=
    for PYBIN in /opt/python/*/bin; do
        # Install build requirements if we need them and file exists
        test -n "$source" -o ! -e "$REQUIREMENTS" \
            || ${PYBIN}/pip install -r "$REQUIREMENTS"

        build_wheel "$source" &
        SECOND=$!

        [ -z "$FIRST" ] || wait ${FIRST}
        FIRST=$SECOND
    done
}

repair_wheels() {
    # Bundle external shared libraries into the wheels
    for whl in $WHEELHOUSE/*.whl; do
        auditwheel repair $whl -w $WHEELHOUSE
    done
}

show_wheels() {
    ls -l $WHEELHOUSE
}

prepare_system
build_wheels
repair_wheels
assert_importable
show_wheels
