#!/usr/bin/env bash
set -euo pipefail

NANVIX_ZUTIL_VERSION="0.7.43"
NANVIX_ZUTIL_VERSION="${NANVIX_ZUTIL_VERSION#v}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! python3 -c "import nanvix.zutil" 2>/dev/null; then
    WHEEL_URL="https://github.com/nanvix/zutil/releases/download/v${NANVIX_ZUTIL_VERSION}/nanvix_zutil-${NANVIX_ZUTIL_VERSION}-py3-none-any.whl"
    echo "[z] Installing nanvix-zutil ${NANVIX_ZUTIL_VERSION} ..."
    pip install --quiet "nanvix-zutil[lint] @ ${WHEEL_URL}"
fi

exec python3 "${SCRIPT_DIR}/.nanvix/z.py" "$@"
