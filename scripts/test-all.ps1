$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runner = Join-Path $repoRoot 'tests\acceptance_p01.py'
$tests = Join-Path $repoRoot 'tests'
$events = Join-Path $repoRoot 'Kenworth_Recursos_de_Prueba\02_Datos\eventos_normalizados.csv'

if (-not (Test-Path -LiteralPath $events) -or -not (Test-Path -LiteralPath $runner)) {
    Write-Error 'BLOCKED: faltan recursos o ejecutor P01.'
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

Write-Host 'Ejecutando unittest...'
& $pythonExecutable @pythonArguments -m unittest discover -s $tests -p 'test_*.py' -v
$unitExit = $LASTEXITCODE
Write-Host 'Ejecutando P01...'
& $pythonExecutable @pythonArguments $runner
$p01Exit = $LASTEXITCODE
Write-Host "RESUMEN: UNIT_TESTS=$($(if ($unitExit -eq 0) {'PASS'} else {'FAIL'})) P01=$($(if ($p01Exit -eq 0) {'PASS'} else {'FAIL'}))"
if ($unitExit -ne 0 -or $p01Exit -ne 0) { exit 1 }
exit 0
