$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runner = Join-Path $repoRoot 'tests\acceptance_p01.py'
$events = Join-Path $repoRoot 'Kenworth_Recursos_de_Prueba\02_Datos\eventos_normalizados.csv'

if (-not (Test-Path -LiteralPath $events)) {
    Write-Error "BLOCKED: falta el CSV original: $events"
    exit 2
}
if (-not (Test-Path -LiteralPath $runner)) {
    Write-Error "BLOCKED: falta el ejecutor: $runner"
    exit 2
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonExecutable = $pythonCommand.Source
    $pythonArguments = @()
} else {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if (-not $pyCommand) {
        Write-Error 'BLOCKED: Python no está disponible.'
        exit 2
    }
    $pythonExecutable = $pyCommand.Source
    $pythonArguments = @('-3')
}

Write-Host "P01: ejecutando con $pythonExecutable"
& $pythonExecutable @pythonArguments $runner
$result = $LASTEXITCODE
Write-Host "P01: código de salida $result"
exit $result
