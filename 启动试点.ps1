# 读取 试点配置.txt 后启动试点。不打印配置内容。
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$config = Join-Path $root "试点配置.txt"
if (-not (Test-Path -LiteralPath $config)) {
    Write-Host "缺少 试点配置.txt。请先复制 试点配置.example.txt 再填写。"
    exit 1
}
Get-Content -LiteralPath $config -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $split = $line.IndexOf("=")
    if ($split -lt 1) { return }
    $name = $line.Substring(0, $split).Trim()
    $value = $line.Substring($split + 1).Trim().Trim('"').Trim("'")
    if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$' -or -not $value) { return }
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}
$local = Join-Path $root ".venv\Scripts\python.exe"
$sibling = Join-Path (Split-Path $root -Parent) "torsion_pendulum_tutor\.venv\Scripts\python.exe"
if (Test-Path -LiteralPath $local) {
    $python = $local
} elseif (Test-Path -LiteralPath $sibling) {
    $python = $sibling
} else {
    Write-Host "找不到 Python 虚拟环境。可在本目录创建 .venv，或使用旁边的单机目录里已有的 .venv。"
    exit 1
}
& $python (Join-Path $root "app.py")
exit $LASTEXITCODE
