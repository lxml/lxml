#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$NANVIX_ZUTIL_VERSION = "0.7.43"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$canImport = python3 -c "import nanvix.zutil" 2>$null
if ($LASTEXITCODE -ne 0) {
    $WheelUrl = "https://github.com/nanvix/zutil/releases/download/v${NANVIX_ZUTIL_VERSION}/nanvix_zutil-${NANVIX_ZUTIL_VERSION}-py3-none-any.whl"
    Write-Host "[z] Installing nanvix-zutil ${NANVIX_ZUTIL_VERSION} ..."
    pip install --quiet "nanvix-zutil[lint] @ ${WheelUrl}"
}

python3 "$ScriptDir/.nanvix/z.py" @args
