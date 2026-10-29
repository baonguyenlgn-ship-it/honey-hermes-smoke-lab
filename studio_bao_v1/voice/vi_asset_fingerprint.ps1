# RESEARCH-ONLY: stage exact external bytes, print SHA256, NEVER execute, extract or publish artifacts.
param([Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$reportPath=Join-Path $OutputDir 'vi-asset-fingerprint.json'
$report=[ordered]@{
 schema='honey.vi-offline-asset-fingerprint.v1'; status='UNTESTED'
 branch_scope='studio-bao-v1/windows-preview-20261030'
 action='DOWNLOAD_HASH_ONLY'; language='vi-VN'; evidence_only=$true
 model_download_url='https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx'
 model_expected_sha256='ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab'
 model_sha256=$null; model_bytes=0
 config_download_url='https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json'
 config_sha256=$null; config_bytes=0
 runtime_release_url='https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip'
 runtime_zip_sha256=$null; runtime_zip_bytes=0; runtime_archive_has_piper=$false
 actual_wav_created=$false; male_voice_verified=$false; commercial_rights_approved=$false
 note='Research-only and unexecuted. Source lineage includes Lessac research-only concern; all commercial/persona permissions remain blocked.'
 failure_type=$null
}
$failure=$null
function Get-FileFromPinnedSource ([string]$u,[string]$dest,[long]$limit) {
 Invoke-WebRequest -Uri $u -OutFile $dest -MaximumRedirection 5 -TimeoutSec 210 -ErrorAction Stop
 if (-not (Test-Path -LiteralPath $dest)) {throw 'DOWNLOAD_FILE_MISSING'}
 $f=Get-Item -LiteralPath $dest
 if ($f.Length -le 0 -or $f.Length -gt $limit) {throw 'DOWNLOAD_SIZE_OUT_OF_BOUNDS'}
 return $f
}
try {
 $runtimePath=Join-Path $OutputDir 'piper_windows_amd64.zip'
 $runtimeFile=Get-FileFromPinnedSource 'https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip' $runtimePath 27000000
 $report.runtime_zip_bytes=$runtimeFile.Length
 $report.runtime_zip_sha256=(Get-FileHash -LiteralPath $runtimePath -Algorithm SHA256).Hash.ToLowerInvariant()
 Add-Type -AssemblyName System.IO.Compression
 $zip=[System.IO.Compression.ZipFile]::OpenRead($runtimePath)
 try {
  if ($zip.Entries.Count -lt 1 -or $zip.Entries.Count -gt 500) {throw 'UNEXPECTED_RUNTIME_ARCHIVE_ENTRY_COUNT'}
  $names=@($zip.Entries | ForEach-Object {$_.FullName})
  foreach($n in $names) {
   if($n.StartsWith('/') -or $n.StartsWith('\\') -or $n.Contains('..') -or $n.Contains(':')) {throw 'UNSAFE_RUNTIME_ARCHIVE_PATH'}
  }
  $report.runtime_archive_has_piper=@($names|Where-Object {$_ -match '(^|/)piper[.]exe$'}).Count -ge 1
  if(-not $report.runtime_archive_has_piper){throw 'PIPER_EXECUTABLE_ABSENT'}
 } finally {$zip.Dispose()}
 $modelPath=Join-Path $OutputDir 'vi_VN-vais1000-medium.onnx'
 $modelFile=Get-FileFromPinnedSource 'https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx' $modelPath 70000000
 $report.model_bytes=$modelFile.Length
 $report.model_sha256=(Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant()
 if($report.model_sha256 -ne $report.model_expected_sha256) {throw 'MODEL_SHA256_MISMATCH'}
 $configPath=Join-Path $OutputDir 'vi_VN-vais1000-medium.onnx.json'
 $configFile=Get-FileFromPinnedSource 'https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json' $configPath 65536
 $report.config_bytes=$configFile.Length
 $report.config_sha256=(Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant()
 $config=Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
 if ($config.language.code -ne 'vi_VN' -or $config.audio.sample_rate -ne 22050) {throw 'MODEL_CONFIG_LANGUAGE_OR_RATE_MISMATCH'}
 $report.status='DOWNLOAD_HASH_ONLY_VERIFIED'
} catch {
 $failure=$_.Exception.GetType().Name+': '+$_.Exception.Message
 $report.status='STAGING_BLOCKED'
 $report.failure_type=$failure.Substring(0,[Math]::Min(260,$failure.Length))
} finally {
 $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
 # Temporary workspace files are not uploaded; cleanup after hashing.
 foreach($f in @('piper_windows_amd64.zip','vi_VN-vais1000-medium.onnx','vi_VN-vais1000-medium.onnx.json')) {
  Remove-Item -LiteralPath (Join-Path $OutputDir $f) -Force -ErrorAction SilentlyContinue
 }
 Write-Output ('VI_ASSET_FINGERPRINT_STATUS='+$report.status)
 Write-Output ('VI_RUNTIME_SHA256='+$report.runtime_zip_sha256)
 Write-Output ('VI_MODEL_SHA256='+$report.model_sha256)
 Write-Output ('VI_CONFIG_SHA256='+$report.config_sha256)
 Write-Output 'VI_NO_EXECUTION_NO_WAV_NO_COMMERCIAL_PERMISSION'
}
if ($failure) {throw 'VI_ASSET_FINGERPRINT_STAGING_BLOCKED: '+$failure}
