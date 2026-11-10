# VUE - install on Android TV / Google TV from Windows and make VUE the Home app
# (so the Home button cannot leave a locked VUE Kids; outside Kids VUE forwards Home to the TV home).
# Run in PowerShell:   irm https://vue-tv.github.io/install-android-windows.ps1 | iex
# Needs: the TV and the PC on the same Wi-Fi, and Developer options on the TV with
# "Network debugging" or "Wireless debugging" switched ON.
$ErrorActionPreference = "Stop"
$ApkUrl = "https://vue-tv.github.io/vue.apk"
$Pkg = "com.tlfzyonk.tvhome"
$HomeAct = "$Pkg/$Pkg.KidsHomeGuard"
$Tools = Join-Path $env:USERPROFILE ".vue-adb"
$Adb = Join-Path $Tools "platform-tools\adb.exe"

function Say($t) { Write-Host ""; Write-Host $t -ForegroundColor Cyan }
function Fail($t) { Write-Host ""; Write-Host "Could not finish: $t" -ForegroundColor Red; throw $t }

Say "VUE - install on Android TV / Google TV"

# 1) Android platform tools (adb), once
if (-not (Test-Path $Adb)) {
  Say "Downloading the official Android tool (adb) for the first time..."
  New-Item -ItemType Directory -Force -Path $Tools | Out-Null
  $zip = Join-Path $env:TEMP "vue-platform-tools.zip"
  Invoke-WebRequest -UseBasicParsing -Uri "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile $zip
  Expand-Archive -Force -Path $zip -DestinationPath $Tools
  Remove-Item $zip -ErrorAction SilentlyContinue
}
& $Adb start-server | Out-Null

function Connected { ((& $Adb devices) | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice$" }).Count -gt 0 }

# 2) connect to the TV
if (-not (Connected)) {
  $savedFile = Join-Path $Tools "tv-ip"
  $saved = if (Test-Path $savedFile) { Get-Content $savedFile } else { "" }
  $ip = Read-Host "Type the TV IP address (Settings > Network) [$saved]"
  if (-not $ip) { $ip = $saved }
  if ($ip -notmatch '^\d+\.\d+\.\d+\.\d+$') { Fail "That IP address is not valid (example: 192.168.1.30)." }
  Set-Content -Path $savedFile -Value $ip
  Say "Connecting... (if the TV asks to allow debugging, choose Always allow)"
  & $Adb connect "$($ip):5555" | Out-Null; Start-Sleep -Seconds 3
  if (-not (Connected)) {
    Say "Google TV: open 'Wireless debugging' > 'Pair device with pairing code' on the TV."
    $pair = Read-Host "Type the IP:port shown under the pairing code (example 192.168.1.30:41235)"
    $code = Read-Host "Type the 6-digit pairing code"
    & $Adb pair $pair $code
    $conn = Read-Host "Type the IP:port shown on the 'Wireless debugging' screen itself (not the pairing port)"
    & $Adb connect $conn | Out-Null; Start-Sleep -Seconds 3
    if (-not (Connected)) { Fail "Could not connect. Make sure the TV and the PC are on the same network." }
  }
}

# 3) install the latest VUE
Say "Downloading and installing the latest VUE..."
$apk = Join-Path $env:TEMP "VUE.apk"
Invoke-WebRequest -UseBasicParsing -Uri $ApkUrl -OutFile $apk
$out = (& $Adb install -r $apk 2>&1) -join "`n"
if ($out -notmatch "Success") {
  if ($out -match "UPDATE_INCOMPATIBLE|signatures do not match") {
    Say "Old version with a different signature - removing it, then installing..."
    & $Adb uninstall $Pkg | Out-Null
    $out = (& $Adb install $apk 2>&1) -join "`n"
  }
  if ($out -notmatch "Success") { Write-Host $out; Fail "Install failed." }
}
Remove-Item $apk -ErrorAction SilentlyContinue

# 4) VUE as the Home app
Say "Making VUE the Home app..."
& $Adb shell pm enable $HomeAct | Out-Null
& $Adb shell cmd package set-home-activity $HomeAct | Out-Null
$now = ((& $Adb shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME) | Select-Object -Last 1).Trim()
& $Adb shell monkey -p $Pkg -c android.intent.category.LEANBACK_LAUNCHER 1 | Out-Null

if ($now -like "$Pkg/*") {
  Say "Done. VUE is installed and is the Home app."
  Write-Host "In VUE Kids with the lock on, Home asks for the parent PIN. Outside Kids, Home goes to the TV home screen as usual."
} else {
  Say "VUE is installed, but the TV refused to change the Home app (now: $now)."
  Write-Host "Some Google TV devices do not allow it. Use a Kid profile in the Google TV settings instead."
}
