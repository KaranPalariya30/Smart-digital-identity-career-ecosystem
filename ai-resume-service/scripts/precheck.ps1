# Run before every push:   .\scripts\precheck.ps1      (from the ai-resume-service folder, venv active)
# Tests -> smoke test (if the server is running) -> git hygiene. Never pushes anything itself.

$failed = $false

Write-Host "`n[1/3] Unit + API tests" -ForegroundColor Cyan
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "Tests FAILED" -ForegroundColor Red; $failed = $true }

Write-Host "`n[2/3] Smoke test against the running server" -ForegroundColor Cyan
python scripts/smoke_test.py
switch ($LASTEXITCODE) {
    0 { }
    2 { Write-Host "Server not running - skipped. Start it in another terminal to include this check." -ForegroundColor Yellow }
    default { Write-Host "Smoke test FAILED" -ForegroundColor Red; $failed = $true }
}

Write-Host "`n[3/3] Git hygiene (staged + untracked files)" -ForegroundColor Cyan
$files = @(git diff --cached --name-only) + @(git ls-files --others --exclude-standard)
$bad = $files | Where-Object { $_ -match '(\.venv/|__pycache__|\.pytest_cache|\.env$|\.zip$|node_modules|idf_corpus\.json|\.pyc$)' }
if ($bad) {
    Write-Host "Do NOT commit these:" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host "  $_" }
    $failed = $true
} else {
    Write-Host "No forbidden files staged or untracked." -ForegroundColor Green
}
git status -sb

if ($failed) { Write-Host "`nPRECHECK FAILED - fix the items above before pushing." -ForegroundColor Red; exit 1 }
Write-Host "`nPRECHECK PASSED - safe to commit and push." -ForegroundColor Green