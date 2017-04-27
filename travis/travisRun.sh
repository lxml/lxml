#!/bin/bash
set -x -e

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
python setup.py bdist_wheel