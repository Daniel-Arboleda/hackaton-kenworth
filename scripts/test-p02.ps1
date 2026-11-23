$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
& python (Join-Path $repoRoot 'tests\acceptance_p02.py')
exit $LASTEXITCODE
