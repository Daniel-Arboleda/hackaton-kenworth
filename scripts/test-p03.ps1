$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& python (Join-Path $repoRoot 'tests\acceptance_p03.py')
exit $LASTEXITCODE
