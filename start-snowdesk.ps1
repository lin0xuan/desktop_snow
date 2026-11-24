Set-Location $PSScriptRoot
$py = $null
$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd) { $py = $cmd.Source }
if (-not $py) {
    $bundled = Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $bundled) { $py = $bundled }
}
if (-not $py) {
    Write-Error "Need Python 3.11+ with numpy and Pillow. Run: pip install -r requirements.txt"
    exit 1
}
& $py -m snowdesk
