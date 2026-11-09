$ErrorActionPreference = 'Stop'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = @()
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) { $pythonArgs += '-3' }
}
if (-not $pythonCommand) { throw 'Python 3.10+ não encontrado. Instale Python e reabra o terminal.' }
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try { & $pythonCommand.Source @pythonArgs -m pria.main } finally { Pop-Location }
