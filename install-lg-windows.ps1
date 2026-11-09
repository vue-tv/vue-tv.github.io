# VUE - install / update on an LG webOS TV from Windows.
# Run in PowerShell:   irm https://vue-tv.github.io/install-lg-windows.ps1 | iex
# Needs: the TV and the PC on the same Wi-Fi, and the LG "Developer Mode" app on the TV
# with "Dev Mode Status" and "Key Server" switched ON.
$ErrorActionPreference = "Stop"
$Device = "vue-tv"
$IpkUrl = "https://vue-tv.github.io/downloads/VUE-LG-webOS-latest.ipk"
$AppId  = "sa.tlfzyonk.general"
$Prefix = Join-Path $env:USERPROFILE ".webos-cli"
$env:Path = "$Prefix;$env:Path"

function Say($t)  { Write-Host ""; Write-Host $t -ForegroundColor Cyan }
function Fail($t) { Write-Host ""; Write-Host "Could not finish: $t" -ForegroundColor Red; throw "VUE install stopped" }

Say "VUE - install on LG TV"

# 1) webOS tools (once)
if (-not (Get-Command ares-install -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "Install Node.js LTS from https://nodejs.org then open a NEW PowerShell window and run the command again."
  }
  Say "Installing LG tools (first time only, about a minute)..."
  npm install --global --prefix "$Prefix" "@webos-tools/cli@3" | Out-Null
  if ($LASTEXITCODE -ne 0) { Fail "LG tools could not be installed. Check the internet connection." }
}

# 2) TV definition (once)
$list = (& ares-setup-device --list 2>$null) -join "`n"
if ($list -notmatch "(?m)^$Device\s") {
  Say "First time: connect the TV"
  $ip = Read-Host "Type the TV IP Address (wireless) shown in the Developer Mode app"
  if ($ip -notmatch '^\d+\.\d+\.\d+\.\d+$') { Fail "That IP address is not valid (example: 192.168.1.20)." }
  & ares-setup-device --add $Device -i "username=prisoner" -i "host=$ip" -i "port=9922" | Out-Null
  Say "Now type the Passphrase shown in the Developer Mode app when asked:"
  & ares-novacom --device $Device --getkey
  if ($LASTEXITCODE -ne 0) { Fail "Could not get the TV key. Make sure Key Server is ON." }
}

# 3) download latest VUE
Say "Downloading the latest VUE..."
$ipk = Join-Path $env:TEMP "VUE-LG-webOS-latest.ipk"
Invoke-WebRequest -UseBasicParsing -Uri $IpkUrl -OutFile $ipk

# 4) install + launch (retry once with a fresh key)
Say "Installing VUE on the TV..."
# close any running VUE first, so the TV never keeps showing the previous version
foreach ($run in @($AppId, "sa.tlfzyonk.home", "sa.tlfzyonk.sport", "com.tlfzyonk.vue")) { & ares-launch --device $Device --close $run 2>$null | Out-Null }
& ares-install --device $Device $ipk
if ($LASTEXITCODE -ne 0) {
  Say "The TV key changed. Type the Passphrase shown in Developer Mode:"
  & ares-novacom --device $Device --getkey
  & ares-install --device $Device $ipk
  if ($LASTEXITCODE -ne 0) { Fail "Install failed. Make sure Dev Mode Status is ON and the session has not expired." }
}
# 5) remove old VUE apps from the first versions (they also show as "VUE" on the TV)
$installed = (& ares-install --device $Device --list 2>$null) -join "`n"
foreach ($old in @("sa.tlfzyonk.home", "sa.tlfzyonk.sport", "com.tlfzyonk.vue")) {
  if ($installed -match "(?m)^$([regex]::Escape($old))") { Say "Removing old VUE app ($old)..."; & ares-install --device $Device --remove $old 2>$null | Out-Null }
}
& ares-launch --device $Device $AppId 2>$null | Out-Null
Remove-Item $ipk -ErrorAction SilentlyContinue

Say "Done - VUE is installed and running on the TV."
Write-Host "Reminder: open Developer Mode on the TV and press Extend Session Time before it runs out."
