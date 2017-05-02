#!/bin/bash
set -x -e


if [ -z "${DOCKER_IMAGE}" ]; then

    if [[ "${TRAVIS_OS_NAME}" == "osx" ]]; then
        eval "$(/usr/local/bin/pyenv init -)"
        pyenv global "${PYENV_VERSION}"
    fi

    iconv --version
    python --version
    pip --version
    python -u setup.py clean
    CFLAGS="-O0 -g" python -u setup.py build_ext --inplace
    CFLAGS="-O0 -g" PYTHONUNBUFFERED=x make test

    if [[ "${TRAVIS_OS_NAME}" == "osx" ]]; then
        python setup.py bdist_wheel




    fi
else
   make wheel_manylinux
fi
