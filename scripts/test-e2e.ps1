$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& python (Join-Path $repoRoot 'tests\acceptance_e2e.py')
exit $LASTEXITCODE
