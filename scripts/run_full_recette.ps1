param(
  [ValidateSet("full", "smoke")]
  [string]$Scope = "full"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-InDirectory {
  param(
    [string]$Path,
    [scriptblock]$Command
  )
  Push-Location $Path
  try {
    & $Command
  }
  finally {
    Pop-Location
  }
}

if (!(Test-Path $Python)) {
  throw "Environnement Python introuvable: $Python. Creez le venv backend avant la recette."
}

Write-Host "CodeRoute Guinee - Recette automatique ($Scope)" -ForegroundColor Green
Write-Host "Racine: $Root"

Write-Step "Migration base de donnees"
Invoke-InDirectory $Backend {
  & $Python -m alembic upgrade head
}

if ($Scope -eq "full") {
  Write-Step "Tests backend complets"
  Invoke-InDirectory $Backend {
    & $Python -m pytest -q
  }
}
else {
  Write-Step "Tests backend critiques"
  Invoke-InDirectory $Backend {
    & $Python -m pytest `
      tests\test_e2e_candidate_center_multimedia_exam.py `
      tests\test_e2e_institutional_pilot_recipe.py `
      tests\test_e2e_candidate_full_flow.py `
      tests\test_operations_summary.py `
      tests\test_database_migrations.py `
      -q
  }
}

Write-Step "Typecheck frontend"
Invoke-InDirectory $Frontend {
  npm.cmd run typecheck
}

Write-Step "Build frontend"
Invoke-InDirectory $Frontend {
  npm.cmd run build
}

Write-Step "Tests E2E navigateur"
Invoke-InDirectory $Frontend {
  npm.cmd run test:e2e
}

Write-Host ""
Write-Host "Recette terminee avec succes." -ForegroundColor Green
Write-Host "Preview: http://127.0.0.1:4173/#/exam"
