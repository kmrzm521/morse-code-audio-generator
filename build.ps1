$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "没有找到项目虚拟环境，请先创建并安装开发依赖。"
}

& $VenvPython -c "import PyInstaller, cryptography, lameenc"
if ($LASTEXITCODE -ne 0) {
    throw "缺少构建依赖，请先安装开发依赖。"
}

Push-Location $ProjectRoot
try {
    & $VenvPython -m PyInstaller --clean --noconfirm ".\morse-generator.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "主程序构建失败，退出代码：$LASTEXITCODE"
    }
    $Output = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot "dist") -Filter "*.exe" | Select-Object -First 1
    if ($null -eq $Output) {
        throw "构建结束，但没有找到主程序。"
    }
    Write-Host "主程序构建成功：$($Output.FullName)"

    $OwnerKey = Join-Path $ProjectRoot "owner-private-key.txt"
    if (-not (Test-Path -LiteralPath $OwnerKey)) {
        throw "所有者私钥文件不存在，无法生成会员激活工具。"
    }
    $OwnerOutput = Join-Path $ProjectRoot "owner-release"
    & $VenvPython -m PyInstaller --clean --noconfirm --distpath $OwnerOutput ".\license-admin.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "会员激活码生成工具构建失败，退出代码：$LASTEXITCODE"
    }
    Copy-Item -LiteralPath $OwnerKey -Destination (Join-Path $OwnerOutput "owner-private-key.txt") -Force
    $AdminExe = Join-Path $OwnerOutput "会员激活码生成工具.exe"
    if (-not (Test-Path -LiteralPath $AdminExe)) {
        throw "构建结束，但没有找到会员激活码生成工具。"
    }
    Write-Host "会员激活码生成工具构建成功：$AdminExe"
}
finally {
    Pop-Location
}
