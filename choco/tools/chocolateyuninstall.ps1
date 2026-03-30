$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$exePath  = Join-Path $toolsDir 'assgen.exe'

if (Test-Path $exePath) {
    Remove-Item $exePath -Force
}
