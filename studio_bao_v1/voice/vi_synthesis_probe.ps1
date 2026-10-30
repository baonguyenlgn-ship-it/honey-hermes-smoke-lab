# Honey Studio VI TTS proof, research only. Hash all external bytes BEFORE executing Piper.
param([Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$reportPath=Join-Path $OutputDir 'vi-synthesis-probe.json'
$wavPath=Join-Path $OutputDir 'vi-research-speech.wav'
$line='Xin chào, đây là bản thử giọng tiếng Việt của Honey.'
$report=[ordered]@{
 schema='honey.vi-offline-synthesis-research.v1'; status='UNTESTED'; language='vi-VN'
 engine='Piper 2023.11.14-2'; model='vi_VN-vais1000-medium'
 model_lineage='VAIS1000 from en_US lessac: research-only pending commercial rights review'
 voice_persona='GENERIC_NON_OWNER'; target_male_voice_accepted=$false
 expected_text=$line; wav_sha256=$null; wav_bytes=0
 runtime_sha256='f3c58906402b24f3a96d92145f58acba6d86c9b5db896d207f78dc80811efcea'
 model_sha256='ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab'
 config_sha256='fafb9da1354ed4b77c31af228ed41fb41cd825c14cffa105454b25e6ae751ee0'
 model_hash_verified=$false; runtime_hash_verified=$false; config_hash_verified=$false
 wav_qa_passed=$false; asr_vietnamese_verified=$false; native_listener_quality_verified=$false; commercial_rights_approved=$false
 network_activity='download only before synthesis; no network/API required for inference'
 failure_type=$null
}
function FetchAndCheck([string]$Url,[string]$Out,[long]$Limit,[string]$Expected) {
 Invoke-WebRequest -Uri $Url -OutFile $Out -MaximumRedirection 5 -TimeoutSec 210 -ErrorAction Stop
 $f=Get-Item -LiteralPath $Out
 if($f.Length -le 0 -or $f.Length -gt $Limit){throw 'ASSET_SIZE_BOUNDS_FAILED'}
 $got=(Get-FileHash -LiteralPath $Out -Algorithm SHA256).Hash.ToLowerInvariant()
 if($got -ne $Expected){throw ('PINNED_SHA256_MISMATCH: '+[IO.Path]::GetFileName($Out))}
}
$failure=$null
try {
 $archive=Join-Path $OutputDir 'piper-windows.zip'
 FetchAndCheck 'https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip' $archive 27000000 $report.runtime_sha256
 $report.runtime_hash_verified=$true
 $model=Join-Path $OutputDir 'vi_VN-vais1000-medium.onnx'
 FetchAndCheck 'https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx' $model 70000000 $report.model_sha256
 $report.model_hash_verified=$true
 $config=Join-Path $OutputDir 'vi_VN-vais1000-medium.onnx.json'
 FetchAndCheck 'https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json' $config 65536 $report.config_sha256
 $report.config_hash_verified=$true
 $cfg=Get-Content -LiteralPath $config -Encoding UTF8 -Raw | ConvertFrom-Json
 if($cfg.language.code -ne 'vi_VN' -or $cfg.audio.sample_rate -ne 22050){throw 'PINNED_CONFIG_INVALID'}
 Add-Type -AssemblyName System.IO.Compression
 $zip=[System.IO.Compression.ZipFile]::OpenRead($archive)
 try {
  if($zip.Entries.Count -gt 500){throw 'ARCHIVE_TOO_MANY_ENTRIES'}
  foreach($entry in $zip.Entries) {
   $n=$entry.FullName
   if($n.StartsWith('/') -or $n.StartsWith('\\') -or $n.Contains('..') -or $n.Contains(':')){throw 'UNSAFE_ARCHIVE_ENTRY'}
  }
 } finally {$zip.Dispose()}
 $dest=Join-Path $OutputDir 'piper-bin'
 [System.IO.Compression.ZipFile]::ExtractToDirectory($archive,$dest)
 $bins=@(Get-ChildItem -LiteralPath $dest -Recurse -File -Filter 'piper.exe')
 if($bins.Count -ne 1){throw 'PINNED_PIPER_BINARY_NOT_UNIQUE'}
 $exe=$bins[0].FullName
 $inputPath=Join-Path $OutputDir 'vi-research-input.txt'
 [IO.File]::WriteAllText($inputPath,$line,[Text.UTF8Encoding]::new($false))
 $utf8=[Text.UTF8Encoding]::new($false)
 [Console]::OutputEncoding=$utf8
 $inputText=Get-Content -LiteralPath $inputPath -Encoding UTF8 -Raw
 $inputText | & $exe --model $model --config $config --output_file $wavPath
 if($LASTEXITCODE -ne 0){throw ('PIPER_EXIT_'+$LASTEXITCODE)}
 if(-not(Test-Path -LiteralPath $wavPath)){throw 'PIPER_WAV_MISSING'}
 $w=Get-Item -LiteralPath $wavPath
 if($w.Length -lt 8000 -or $w.Length -gt 3000000){throw 'PIPER_WAV_SIZE_OUT_OF_BOUNDS'}
 $report.wav_bytes=$w.Length
 $report.wav_sha256=(Get-FileHash -LiteralPath $wavPath -Algorithm SHA256).Hash.ToLowerInvariant()
 $report.status='WAV_EMITTED_NEEDS_INDEPENDENT_QA'
} catch {
 $failure=$_.Exception.GetType().Name+': '+$_.Exception.Message
 $report.status='VI_SYNTHESIS_BLOCKED'
 $report.failure_type=$failure.Substring(0,[Math]::Min(260,$failure.Length))
} finally {
 $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
 # Do not publish archive/model/WAV; runner.temp is disposable.
 foreach($f in @('piper-windows.zip','vi_VN-vais1000-medium.onnx','vi_VN-vais1000-medium.onnx.json','vi-research-input.txt')){
  Remove-Item -LiteralPath (Join-Path $OutputDir $f) -Force -ErrorAction SilentlyContinue
 }
 $binDir=Join-Path $OutputDir 'piper-bin'
 if(Test-Path -LiteralPath $binDir){Remove-Item -LiteralPath $binDir -Force -Recurse -ErrorAction SilentlyContinue}
 Write-Output ('VI_SYNTHESIS_STATUS='+$report.status)
 Write-Output ('VI_SYNTHESIS_SHA256='+$report.wav_sha256)
 Write-Output 'VI_COMMERCIAL_RIGHTS_NOT_APPROVED; MALE_AND_AUDIO_QUALITY_NOT_CERTIFIED'
}
if($failure){throw ('VI_SYNTHESIS_PROBE_FAILED: '+$failure)}
