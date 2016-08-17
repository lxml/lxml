#/!/bin/bash
#
# Called inside the manylinux image
echo "Started $0 $@"

set -e -x
REQUIREMENTS=/io/requirements.txt
WHEELHOUSE=/io/wheelhouse

build_wheel() {
    env STATIC_DEPS=true \
        LDFLAGS="$LDFLAGS -fPIC" \
        CFLAGS="$CFLAGS -fPIC" \
        ${PYBIN}/pip \
            wheel \
            /io \
            -w $WHEELHOUSE
}

assert_importable() {
    # Install packages and test
    for PYBIN in /opt/python/*/bin/; do
        ${PYBIN}/pip install lxml --no-index -f $WHEELHOUSE

        (cd $HOME; ${PYBIN}/python -c 'import lxml')
    done
}

prepare_system() {
    yum install -y zlib-devel
    # Remove Python 2.6 symlinks
    rm /opt/python/cp26*
}

build_wheels() {
    # Compile wheels for all python versions
    for PYBIN in /opt/python/*/bin; do
        # Install requirements if file exists
        test ! -e $REQUIREMENTS \
            || ${PYBIN}/pip install -r $REQUIREMENTS

        build_wheel
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
