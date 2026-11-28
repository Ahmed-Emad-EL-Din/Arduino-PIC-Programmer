$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Sketch = Join-Path $Root 'firmware/source/ProgramPic'
$OutRoot = Join-Path $Root 'firmware/precompiled'
New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null

$Targets = @(
  @{ Key = 'uno'; Fqbn = 'arduino:avr:uno' },
  @{ Key = 'nano_new'; Fqbn = 'arduino:avr:nano:cpu=atmega328' },
  @{ Key = 'nano_old'; Fqbn = 'arduino:avr:nano:cpu=atmega328old' },
  @{ Key = 'pro_mini_5v'; Fqbn = 'arduino:avr:pro:cpu=16MHzatmega328' },
  @{ Key = 'mega2560'; Fqbn = 'arduino:avr:mega' },
  @{ Key = 'leonardo'; Fqbn = 'arduino:avr:leonardo' },
  @{ Key = 'micro'; Fqbn = 'arduino:avr:micro' }
)

foreach ($Target in $Targets) {
  $BuildPath = Join-Path $env:RUNNER_TEMP "picprog-$($Target.Key)"
  New-Item -ItemType Directory -Force -Path $BuildPath | Out-Null
  arduino-cli compile --fqbn $Target.Fqbn --build-path $BuildPath $Sketch
  $Hex = Join-Path $BuildPath 'ProgramPic.ino.hex'
  if (!(Test-Path $Hex)) { throw "Firmware output missing for $($Target.Key): $Hex" }
  Copy-Item $Hex (Join-Path $OutRoot "$($Target.Key).hex") -Force
}

$ArduinoData = Join-Path $env:LOCALAPPDATA 'Arduino15/packages/arduino/tools/avrdude'
$Avrdude = Get-ChildItem $ArduinoData -Recurse -File -Filter 'avrdude.exe' | Select-Object -First 1
if (!$Avrdude) { throw "avrdude.exe was not found under $ArduinoData" }
$Conf = Get-ChildItem $ArduinoData -Recurse -File -Filter 'avrdude.conf' | Select-Object -First 1
if (!$Conf) { throw "avrdude.conf was not found beside $($Avrdude.FullName)" }
$Tools = Join-Path $Root 'tools'
$AvrdudeBundle = Join-Path $Tools 'avrdude'
New-Item -ItemType Directory -Force -Path $AvrdudeBundle | Out-Null
# Keep adjacent DLLs with avrdude and flatten the configuration to a known path.
Copy-Item (Join-Path $Avrdude.DirectoryName '*') $AvrdudeBundle -Recurse -Force
Copy-Item $Avrdude.FullName (Join-Path $AvrdudeBundle 'avrdude.exe') -Force
Copy-Item $Conf.FullName (Join-Path $AvrdudeBundle 'avrdude.conf') -Force
$PackageRoot = Split-Path $Avrdude.DirectoryName -Parent
$AvrLicense = Get-ChildItem $PackageRoot -Recurse -File -Include 'LICENSE*','COPYING*' | Select-Object -First 1
if ($AvrLicense) { Copy-Item $AvrLicense.FullName (Join-Path $AvrdudeBundle 'AVRDUDE-LICENSE.txt') -Force }
Write-Host 'Compiled firmware and staged avrdude for Windows packaging.'
