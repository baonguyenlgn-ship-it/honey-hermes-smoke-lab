param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
New-Item -ItemType Directory -Path $Out -Force | Out-Null
$m=Get-Content (Join-Path $PSScriptRoot 'supertonic3_official_digests.json') -Raw | ConvertFrom-Json
if($m.revision -ne '3cadd1ee6394adea1bd021217a0e650ede09a323' -or $m.assets.Count -ne 4){throw 'MANIFEST_INVALID'}
$r=[ordered]@{status='NOT_PROVEN';revision=$m.revision;files=@();bytes=0;executed=$false;audio=$false;commercial=$false;error_type=$null}
$e=$null
try {
 foreach($a in $m.assets) {
  if($a.path -notmatch '^onnx/(duration_predictor|text_encoder|vector_estimator|vocoder)\.onnx$'){throw 'BAD_PATH'}
  $dest=Join-Path $Out (Split-Path $a.path -Leaf)
  $url='https://huggingface.co/Supertone/supertonic-3/resolve/'+$m.revision+'/'+$a.path
  Invoke-WebRequest -Uri $url -OutFile $dest -TimeoutSec 240 -MaximumRedirection 5
  $n=(Get-Item $dest).Length
  if($n -lt 100000 -or $n -gt [long]$a.max_bytes){throw ('SIZE_MISMATCH_'+$a.path)}
  $sha=(Get-FileHash $dest -Algorithm SHA256).Hash.ToLowerInvariant()
  if($sha -ne $a.sha256){throw ('SHA_MISMATCH_'+$a.path)}
  $r.bytes+=$n
  if($r.bytes -gt 470000000){throw 'TOTAL_SIZE_EXCEEDED'}
  $r.files+=@([ordered]@{path=$a.path;bytes=$n;sha256=$sha;match=$true})
  Remove-Item -LiteralPath $dest -Force
  Write-Output ('HASH_MATCH '+$a.path+' '+$n)
 }
 if($r.files.Count -ne 4){throw 'INCOMPLETE'}
 $r.status='FOUR_ONNX_BYTES_SHA_VERIFIED'
} catch {
 $e=$_.Exception.GetType().Name+': '+$_.Exception.Message
 $r.error_type=$e.Substring(0,[Math]::Min(190,$e.Length))
 $r.status='BLOCKED'
} finally {
 Get-ChildItem -LiteralPath $Out -File -Filter '*.onnx' | Remove-Item -Force -ErrorAction SilentlyContinue
 $r | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $Out 'st3-hashes.json') -Encoding utf8
 Write-Output ('SUPER3_STAGE='+$r.status+' COUNT='+$r.files.Count)
}
if($e){throw $e}
Write-Output 'SUPER3_SOURCE_HASH_RUN_COMPLETED'
exit 0
