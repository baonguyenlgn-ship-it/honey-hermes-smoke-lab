param([Parameter(Mandatory=$true)][string]$Out,[ValidateSet('Wav','Benchmark')][string]$Mode='Wav',[Parameter(Mandatory=$true)][string]$RuntimeDir)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$m=Get-Content (Join-Path $PSScriptRoot 'supertonic3_official_digests.json') -Raw | ConvertFrom-Json
$runtimeExe=Join-Path $RuntimeDir 'venv/Scripts/python.exe'
$runtimeReport=Join-Path $RuntimeDir 'locked-runtime-report.json'
if(-not(Test-Path -LiteralPath $runtimeExe) -or -not(Test-Path -LiteralPath $runtimeReport)){throw 'NO_PINNED_ISOLATED_RUNTIME'}
$runtimeProof=Get-Content -LiteralPath $runtimeReport -Raw -Encoding utf8 | ConvertFrom-Json
$lockHash=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'requirements-win-py312-hashes.txt') -Algorithm SHA256).Hash.ToLowerInvariant()
if($runtimeProof.status -ne 'HASH_LOCKED_ISOLATED_WINDOWS_VENV_READY' -or $runtimeProof.original_lock_sha256 -ne $lockHash -or -not $runtimeProof.offline_install_verified -or -not $runtimeProof.installed_versions_verified -or -not $runtimeProof.venv_isolated){throw 'RUNTIME_SHA_LOCK_GATE_FAILED'}
$root=Join-Path $Out 'model'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$r=[ordered]@{status='UNTESTED';revision=$m.revision;weight_hashes=@();auxiliary_hashes=@();bytes=0;wav_generated=$false;commercial_approved=$false;error_type=$null}
$problem=$null
try{
 if($m.revision -ne '3cadd1ee6394adea1bd021217a0e650ede09a323' -or $m.assets.Count -ne 4){throw 'SNAPSHOT_MISMATCH'}
 $assets=@($m.assets)
 foreach($p in @('onnx/tts.json','onnx/unicode_indexer.json','voice_styles/M1.json','LICENSE')){
   $assets+=@([pscustomobject]@{path=$p;sha256=$null;max_bytes=1000000})
 }
 foreach($a in $assets){
   $rel=[string]$a.path
   if($rel -notmatch '^(onnx/(duration_predictor|text_encoder|vector_estimator|vocoder)\.onnx|onnx/(tts|unicode_indexer)\.json|voice_styles/M1\.json|LICENSE)$'){throw 'UNEXPECTED_ASSET'}
   $file=Join-Path $root ($rel -replace '/',[IO.Path]::DirectorySeparatorChar)
   New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($file)) | Out-Null
   Invoke-WebRequest -Uri ('https://huggingface.co/Supertone/supertonic-3/resolve/'+$m.revision+'/'+$rel) -OutFile $file -TimeoutSec 220 -MaximumRedirection 5
   $n=(Get-Item -LiteralPath $file).Length
   if($n -lt 100 -or $n -gt [long]$a.max_bytes){throw ('SIZE_BOUND_'+$rel)}
   $r.bytes+=$n
   if($r.bytes -gt 470000000){throw 'TOTAL_DOWNLOAD_LIMIT'}
   $digest=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
   if($null -ne $a.sha256 -and $digest -ne $a.sha256){throw ('ONNX_SHA_MISMATCH_'+$rel)}
   $entry=[ordered]@{path=$rel;bytes=$n;sha256=$digest}
   if($rel.EndsWith('.onnx')){$r.weight_hashes+=@($entry)}else{$r.auxiliary_hashes+=@($entry)}
 }
 foreach($p in @('onnx/tts.json','onnx/unicode_indexer.json','voice_styles/M1.json')){
   $cfg=Get-Content -LiteralPath (Join-Path $root ($p -replace '/',[IO.Path]::DirectorySeparatorChar)) -Raw | ConvertFrom-Json
   if($null -eq $cfg){throw 'AUX_JSON_INVALID'}
 }
 $r.status='ASSETS_VERIFIED'
 $r | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $Out 'source-report.json') -Encoding utf8
 $r.runtime_lock_sha256=$lockHash
 $r.isolated_runtime_verified=$true
 # Python dependencies were already verified and installed OFFLINE in a fresh venv.
 $r.status='RUNTIME_READY'
 if($Mode -eq 'Benchmark'){
   & $runtimeExe (Join-Path $PSScriptRoot 'supertonic3_m1_benchmark.py') $root $Out
   if($LASTEXITCODE -ne 0){throw ('CPU_BENCHMARK_EXIT_'+$LASTEXITCODE)}
   if(-not(Test-Path -LiteralPath (Join-Path $Out 'benchmark.json'))){throw 'BENCHMARK_REPORT_MISSING'}
   $r.status='BENCHMARK_EMITTED_NEEDS_INDEPENDENT_QA'
   $r.wav_generated=$false
 } else {
   & $runtimeExe (Join-Path $PSScriptRoot 'supertonic3_m1_cpu.py') $root $Out
   if($LASTEXITCODE -ne 0){throw ('CPU_INFERENCE_EXIT_'+$LASTEXITCODE)}
   if(-not (Test-Path -LiteralPath (Join-Path $Out 'inference.json'))){throw 'INFERENCE_REPORT_MISSING'}
   $r.status='INFERENCE_EMITTED_NEEDS_INDEPENDENT_QA'
   $r.wav_generated=$true
 }
}catch{
 $problem=$_.Exception.GetType().Name+': '+$_.Exception.Message
 $r.error_type=$problem.Substring(0,[Math]::Min(220,$problem.Length))
 $r.status='BLOCKED'
}finally{
 Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
 $r | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $Out 'source-report.json') -Encoding utf8
 Write-Output ('SUPER3_CPU_STAGE='+$r.status+' ONNX_COUNT='+$r.weight_hashes.Count)
 Write-Output 'SUPER3_NO_PUBLIC_AUDIO_NO_COMMERCIAL_VOICE_CLAIM'
}
if($problem){throw $problem}
exit 0
