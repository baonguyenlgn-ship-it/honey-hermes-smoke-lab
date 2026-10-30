# Windows-only, generic Korean research speech; no cloud API, no owner likeness.
# Run exact pinned upstream MSI with administrative extraction ONLY into runner.temp.
param([Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
New-Item -Force -ItemType Directory -Path $OutputDir | Out-Null
$reportPath=Join-Path $OutputDir 'ko-offline-synthesis-probe.json'
$wavPath=Join-Path $OutputDir 'ko-research-speech.wav'
$msiPath=Join-Path $OutputDir 'espeak-ng.msi'
$expectedHash='7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9'
$line='안녕하세요. 허니 스튜디오의 한국어 음성 시험입니다.'
$report=[ordered]@{
  schema='honey.ko-offline-synthesis-research.v1'
  status='UNTESTED'
  language='ko-KR'
  engine='eSpeak NG 1.52.0 (GPL-3.0-or-later)'
  model='ko language data in upstream installer'
  voice_persona='GENERIC_NON_OWNER'
  speech_text=$line
  package_url='https://github.com/espeak-ng/espeak-ng/releases/download/1.52.0/espeak-ng.msi'
  package_expected_sha256=$expectedHash
  package_sha256=$null
  package_bytes=0
  package_pin_verified=$false
  korean_voice_detected=$false
  wav_sha256=$null
  wav_bytes=0
  asr_verified=$false
  native_listener_quality_verified=$false
  premium_male_voice_verified=$false
  commercial_integration_approved=$false
  license_review='GPL-3.0-or-later; commercial embedding/distribution obligations NOT REVIEWED'
  no_paid_inference=$true
  failure_type=$null
}
$failure=$null
try {
  Invoke-WebRequest -Uri $report.package_url -OutFile $msiPath -MaximumRedirection 5 -TimeoutSec 120
  $file=Get-Item -LiteralPath $msiPath
  if ($file.Length -lt 1000000 -or $file.Length -gt 20000000){throw 'KO_INSTALLER_SIZE_OUT_OF_BOUNDS'}
  $report.package_bytes=$file.Length
  $report.package_sha256=(Get-FileHash -LiteralPath $msiPath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($report.package_sha256 -ne $expectedHash){throw 'KO_INSTALLER_PIN_MISMATCH'}
  $report.package_pin_verified=$true
  $extract=Join-Path $OutputDir 'unpacked'
  New-Item -ItemType Directory -Force -Path $extract | Out-Null
  $msilog=Join-Path $OutputDir 'extraction.log'
  $proc=Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/a',('"' + $msiPath + '"'),'/qn',('TARGETDIR="' + $extract + '"'),'/norestart',('/L*v "' + $msilog + '"')) -PassThru -Wait -NoNewWindow
  if($proc.ExitCode -ne 0){throw ('KO_ADMIN_EXTRACTION_EXIT_'+$proc.ExitCode)}
  $bins=@(Get-ChildItem -Path $extract -Recurse -File -Filter espeak-ng.exe)
  if($bins.Count -ne 1){throw 'KO_ESPEAK_BINARY_NOT_UNIQUE'}
  $exe=$bins[0].FullName
  $dirs=@(Get-ChildItem -Path $extract -Recurse -Directory -Filter espeak-ng-data)
  if($dirs.Count -ne 1){throw 'KO_VOICE_DATA_NOT_FOUND'}
  $env:ESPEAK_DATA_PATH=$dirs[0].FullName
  $voices=(& $exe --voices=ko 2>&1 | Out-String)
  if($LASTEXITCODE -ne 0){throw 'KO_VOICE_LIST_FAILED'}
  if($voices -notmatch '(?m)^\s*\d+\s+ko\s'){throw 'KO_VOICE_NOT_LISTED'}
  $report.korean_voice_detected=$true
  $textFile=Join-Path $OutputDir 'ko-original-utf8.txt'
  [IO.File]::WriteAllText($textFile,$line,[Text.UTF8Encoding]::new($false))
  & $exe -v ko -s 135 -f $textFile -w $wavPath
  if($LASTEXITCODE -ne 0){throw ('KO_TTS_EXIT_'+$LASTEXITCODE)}
  if(-not(Test-Path -LiteralPath $wavPath)){throw 'KO_TTS_WAV_NOT_WRITTEN'}
  $audio=Get-Item -LiteralPath $wavPath
  if($audio.Length -lt 8000 -or $audio.Length -gt 3000000){throw 'KO_WAV_SIZE_OUT_OF_BOUNDS'}
  $report.wav_bytes=$audio.Length
  $report.wav_sha256=(Get-FileHash -LiteralPath $wavPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $report.status='KO_WAV_EMITTED_PENDING_INDEPENDENT_QA'
} catch {
  $failure=($_.Exception.GetType().Name+': '+$_.Exception.Message)
  $report.failure_type=$failure.Substring(0,[Math]::Min(240,$failure.Length))
  $report.status='KO_SYNTHESIS_BLOCKED'
} finally {
  $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
  foreach($name in @('espeak-ng.msi','ko-original-utf8.txt','extraction.log')){
    Remove-Item -LiteralPath (Join-Path $OutputDir $name) -Force -ErrorAction SilentlyContinue
  }
  $temp=Join-Path $OutputDir 'unpacked'
  if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
  Write-Output ('KO_SYNTHESIS_STATUS='+$report.status)
  Write-Output ('KO_VOICE_DETECTED='+$report.korean_voice_detected)
  Write-Output ('KO_SYNTHESIS_WAV_SHA256='+$report.wav_sha256)
  Write-Output 'KO_COMMERCIAL_INTEGRATION_NOT_ACCEPTED; KO_NATIVE_LISTENER_QUALITY_NOT_PROVEN'
}
if($failure){throw ('KO_OFFLINE_RESEARCH_FAILED: '+$failure)}
