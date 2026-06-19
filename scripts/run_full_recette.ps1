param(
  [ValidateSet("full", "smoke")]
  [string]$Scope = "full"
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$TestTemp = Join-Path $Root ".tmp\pytest"
$PytestBaseTemp = $TestTemp -replace "\\", "/"

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

function Invoke-Checked {
  param(
    [scriptblock]$Command,
    [string]$Label
  )
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Label a echoue avec le code $LASTEXITCODE"
  }
}

if (!(Test-Path $Python)) {
  throw "Environnement Python introuvable: $Python. Creez le venv backend avant la recette."
}

Write-Host "CodeRoute Guinee - Recette automatique ($Scope)" -ForegroundColor Green
Write-Host "Racine: $Root"

New-Item -ItemType Directory -Force -Path $TestTemp | Out-Null
$env:TMP = $TestTemp
$env:TEMP = $TestTemp
$env:PYTEST_ADDOPTS = "--basetemp=$PytestBaseTemp"

Write-Step "Migration base de donnees"
Invoke-InDirectory $Backend {
  Invoke-Checked { & $Python -m alembic upgrade head } "Migration base de donnees"
}

if ($Scope -eq "full") {
  Write-Step "Tests backend complets"
  Invoke-InDirectory $Backend {
    Invoke-Checked { & $Python -m pytest -q } "Tests backend complets"
  }
}
else {
  Write-Step "Tests backend critiques"
  Invoke-InDirectory $Backend {
    Invoke-Checked { & $Python -m pytest `
      tests\test_e2e_candidate_center_multimedia_exam.py `
      tests\test_e2e_institutional_pilot_recipe.py `
      tests\test_e2e_candidate_full_flow.py `
      tests\test_operations_summary.py `
      tests\test_database_migrations.py `
      -q } "Tests backend critiques"
  }
}

Write-Step "Typecheck frontend"
Invoke-InDirectory $Frontend {
  Invoke-Checked { npm.cmd run typecheck } "Typecheck frontend"
}

Write-Step "Build frontend"
Invoke-InDirectory $Frontend {
  Invoke-Checked { npm.cmd run build } "Build frontend"
}

Write-Step "Tests E2E navigateur"
Invoke-InDirectory $Frontend {
  Invoke-Checked { npm.cmd run test:e2e } "Tests E2E navigateur"
}

Write-Host ""
Write-Host "Recette terminee avec succes." -ForegroundColor Green
Write-Host "Preview: http://127.0.0.1:4173/#/exam"
