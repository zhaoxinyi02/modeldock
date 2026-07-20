param(
    [string]$VersionTag = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not $VersionTag) {
    $VersionTag = python -c "import sys; sys.path.insert(0,'src'); from constants import APP_VERSION; print(APP_VERSION)"
}
$AppVersion = $VersionTag.TrimStart('V','v')
$BackendDist = Join-Path $Root "build\native-backend-dist"
$BackendWork = Join-Path $Root "build\native-backend-work"
$PublishDir = Join-Path $Root "dist\windows-publish"

python -m PyInstaller native-backend.spec --noconfirm --distpath $BackendDist --workpath $BackendWork
dotnet publish native\windows\ModelDock.WinUI.csproj -c Release -r win-x64 --self-contained true -o $PublishDir

$BackendTarget = Join-Path $PublishDir "Backend"
if (Test-Path $BackendTarget) { Remove-Item $BackendTarget -Recurse -Force }
Copy-Item (Join-Path $BackendDist "ModelDockBackend") $BackendTarget -Recurse -Force

$Inno = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Inno)) { throw "Inno Setup 6 not found: $Inno" }
& $Inno "/DSourceDir=$PublishDir" "/DOutputDir=$(Join-Path $Root 'dist')" "/DAppVersion=$AppVersion" "/DVersionTag=$VersionTag" scripts\installer.iss

$Setup = Join-Path $Root "dist\ModelDock_${VersionTag}_Windows_x64_Setup.exe"
if (-not (Test-Path $Setup)) { throw "Windows setup was not created: $Setup" }
Write-Host "Built: $Setup"
