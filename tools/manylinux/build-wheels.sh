#!/bin/bash
#
# Called inside the manylinux image
echo "Started $0 $@"

set -e -x
REQUIREMENTS=/io/requirements.txt
WHEELHOUSE=/io/wheelhouse
SDIST=$1
PACKAGE=$(basename ${SDIST%-*})

build_wheel() {
    pybin="$1"
    source="$2"
    [ -n "$source" ] || source=/io

    env STATIC_DEPS=true \
        LDFLAGS="$LDFLAGS -fPIC" \
        CFLAGS="$CFLAGS -fPIC" \
        ${pybin}/pip \
            wheel \
            "$source" \
            -w $WHEELHOUSE
}

assert_importable() {
    # Install packages and test
    for PYBIN in /opt/python/*/bin/; do
        ${PYBIN}/pip install $PACKAGE --no-index -f $WHEELHOUSE

        (cd $HOME; ${PYBIN}/python -c 'import lxml.etree, lxml.objectify')
    done
}

prepare_system() {
    #yum install -y zlib-devel
    # Remove Python 2.6 symlinks
    rm -f /opt/python/cp26*
    echo "Python versions found: $(cd /opt/python && echo cp* | sed -e 's|[^ ]*-||g')"
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

        build_wheel "$PYBIN" "$source" &
        SECOND=$!

        [ -z "$FIRST" ] || wait ${FIRST}
        FIRST=$SECOND
    done
    wait
}

repair_wheels() {
    # Bundle external shared libraries into the wheels
    for whl in $WHEELHOUSE/*.whl; do
        auditwheel repair $whl -w $WHEELHOUSE
    done
}

show_wheels() {
    filename=${SDIST##*/}
    ls -l $WHEELHOUSE/${filename%%.tar.gz}*
}

prepare_system
build_wheels
repair_wheels
assert_importable
show_wheels
