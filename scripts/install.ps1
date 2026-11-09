param()
$ErrorActionPreference = 'Stop'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = @()
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) { $pythonArgs += '-3' }
}
if (-not $pythonCommand) {
    throw 'Python 3.10+ não encontrado. Instale Python para Windows e reabra o terminal.'
}
& $pythonCommand.Source @pythonArgs --version
if ($LASTEXITCODE -ne 0) { throw 'Python não iniciou corretamente.' }
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) { throw 'Ollama não encontrado. Instale Ollama para Windows pela fonte oficial e reabra o terminal.' }
& $ollama.Source --version
Write-Host 'Modelo necessário: qwen2.5:7b.' -ForegroundColor Green
Write-Host 'Se ainda não estiver instalado, execute: ollama pull qwen2.5:7b' -ForegroundColor Yellow
Write-Host 'Não há pacotes Python adicionais nesta fase.' -ForegroundColor Green
