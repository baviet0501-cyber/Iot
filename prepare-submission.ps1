$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$staging = Join-Path $env:TEMP ("iot-classroom-submission-" + [guid]::NewGuid().ToString("N"))
$outputZip = Join-Path $projectRoot "iot-classroom-submission.zip"

$files = @(
  "README.md",
  "WOKWI.md",
  "wokwi.toml",
  "start-wokwi.ps1",
  "slide_project_iot_an_toan.pptx",
  "backend\app.py",
  "backend\models.py",
  "backend\requirements.txt",
  "backend\.env.example",
  "firmware\esp_sensor.ino",
  "firmware\config_example.h",
  "firmware\config_wokwi_example.h",
  "firmware\wokwi\diagram.json",
  "firmware\wokwi\libraries.txt",
  "firmware\wokwi\sketch.ino",
  "firmware\wokwi\wokwi.toml"
)

$directories = @(
  "backend\templates",
  "backend\static"
)

if (Test-Path -LiteralPath $outputZip) {
  Remove-Item -LiteralPath $outputZip -Force
}

New-Item -ItemType Directory -Path $staging | Out-Null

foreach ($file in $files) {
  $source = Join-Path $projectRoot $file
  if (-not (Test-Path -LiteralPath $source)) {
    continue
  }

  $target = Join-Path $staging $file
  New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
  Copy-Item -LiteralPath $source -Destination $target -Force
}

foreach ($directory in $directories) {
  $source = Join-Path $projectRoot $directory
  if (-not (Test-Path -LiteralPath $source)) {
    continue
  }

  $target = Join-Path $staging $directory
  New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
  Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $outputZip -Force
Remove-Item -LiteralPath $staging -Recurse -Force

Write-Host "Created clean submission zip: $outputZip"
Write-Host "Excluded: .env, databases, virtualenvs, build outputs, tools, logs, and Python caches."
