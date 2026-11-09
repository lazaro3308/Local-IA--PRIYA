$ErrorActionPreference = 'Continue'
Write-Host '=== PRIA / Windows ===' -ForegroundColor Cyan
[System.Environment]::OSVersion.VersionString
Write-Host "CPU: $([System.Environment]::GetEnvironmentVariable('PROCESSOR_IDENTIFIER'))"
Write-Host "Processadores lógicos: $env:NUMBER_OF_PROCESSORS"
Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Livre_GB';E={[math]::Round($_.Free/1GB,1)}}, Root | Format-Table -AutoSize
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = @()
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) { $pythonArgs += '-3' }
}
if ($pythonCommand) { & $pythonCommand.Source @pythonArgs --version } else { Write-Warning 'Python não encontrado' }
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCommand) { & $ollamaCommand.Source --version; & $ollamaCommand.Source list } else { Write-Warning 'Ollama não encontrado' }
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) { & $nvidia.Source --query-gpu=name,memory.total --format=csv,noheader } else { Write-Host 'nvidia-smi ausente; não foi possível confirmar GPU NVIDIA.' }
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    "RAM total (GiB): $([math]::Round($os.TotalVisibleMemorySize/1MB,1))"
} catch { Write-Warning 'Consulta CIM de RAM indisponível nesta sessão.' }
