#!/bin/bash
set -e -x
if [[ "${TRAVIS_OS_NAME}" == "osx" ]]; then
    if [[ -z "$(pyenv versions | grep ${PYENV_VERSION})" ]]; then
        brew update
        brew upgrade pyenv
        /usr/local/bin/pyenv install "${PYENV_VERSION}"
    fi
    eval "$(/usr/local/bin/pyenv init -)"
    pyenv global "${PYENV_VERSION}"
fi
python --version
pip --version

python -c "import sys; sys.exit(sys.version_info[:2] != (3,2))" 2>/dev/null || pip install -U pip wheel

pip install -r requirements.txt
pip install -U beautifulsoup4 cssselect

if [ ! -z "${DOCKER_IMAGE}" ]; then
    docker pull "${DOCKER_IMAGE}"
fi