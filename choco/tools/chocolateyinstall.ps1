$ErrorActionPreference = 'Stop'

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

$packageArgs = @{
    packageName    = 'assgen'
    url64bit       = 'https://github.com/aallbrig/assgen/releases/download/{{TAG}}/assgen-{{TAG}}-windows-x64.exe'
    checksum64     = '{{CHECKSUM}}'
    checksumType64 = 'sha256'
    fileFullPath   = Join-Path $toolsDir 'assgen.exe'
}

Get-ChocolateyWebFile @packageArgs
