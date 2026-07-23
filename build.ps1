$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Missing .venv. Create it and install requirements-dev.txt first."
}

& $VenvPython -c "import PyInstaller, lameenc"
if ($LASTEXITCODE -ne 0) {
    throw "Missing build dependencies. Run: .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt"
}

Push-Location $ProjectRoot
try {
    & $VenvPython -m PyInstaller --clean --noconfirm ".\morse-generator.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
    $Output = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot "dist") -Filter "*.exe" | Select-Object -First 1
    if ($null -eq $Output) {
        throw "Build finished but no EXE was found in dist."
    }
    Write-Host "Build succeeded: $($Output.FullName)"
}
finally {
    Pop-Location
}
