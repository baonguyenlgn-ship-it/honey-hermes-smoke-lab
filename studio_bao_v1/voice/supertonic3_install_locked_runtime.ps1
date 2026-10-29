# Hash-locked Windows CPython 3.12 runtime for LAB-only Supertonic 3.
# Downloads wheels with --require-hashes, installs offline into a fresh venv.
# NEVER installs to the runner's global Python or publishes wheels.
param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$lock=Join-Path $PSScriptRoot 'requirements-win-py312-hashes.txt'
$manifest=Get-Content -LiteralPath $lock -Raw -Encoding utf8
$lines=@($manifest -split '\r?\n' | Where-Object {$_})
if($lines.Count -ne 10){throw 'LOCK_EXPECTED_TEN_PACKAGES'}
$expected=@{}
foreach($line in $lines){
 if($line -notmatch '^([a-zA-Z0-9_-]+)==([0-9.]+) --hash=sha256:([a-f0-9]{64})$'){throw 'LOCK_LINE_INVALID'}
 $name=$Matches[1].Replace('_','-').ToLowerInvariant()
 if($expected.ContainsKey($name)){throw 'DUPLICATE_LOCK_PACKAGE'}
 $expected[$name]=[ordered]@{version=$Matches[2];sha256=$Matches[3]}
}
$report=[ordered]@{
 schema='honey.st3-locked-runtime-execution.v1';status='UNTESTED'
 platform='win32';python_series='3.12';venv_isolated=$false
 original_lock_sha256=(Get-FileHash -LiteralPath $lock -Algorithm SHA256).Hash.ToLowerInvariant()
 locked_count=$lines.Count;wheel_count=0;verified_wheels=@()
 offline_install_verified=$false;installed_versions_verified=$false
 global_python_modified=$false;model_or_voice_test_executed=$false
 commercial_or_production_acceptance=$false;failure_type=$null
}
$wheelDir=Join-Path $Out 'wheelhouse'
$venv=Join-Path $Out 'venv'
$reportFile=Join-Path $Out 'locked-runtime-report.json'
$problem=$null
try{
 $version=(& python -c 'import sys; print(str(sys.version_info.major)+"."+str(sys.version_info.minor)+";"+sys.platform)').Trim()
 if($LASTEXITCODE -ne 0 -or $version -ne '3.12;win32'){throw 'PYTHON_WINDOWS312_REQUIRED'}
 New-Item -ItemType Directory -Force -Path $wheelDir | Out-Null
 & python -m pip download --disable-pip-version-check --no-input --no-cache-dir --only-binary=:all: --require-hashes --dest $wheelDir -r $lock
 if($LASTEXITCODE -ne 0){throw ('WHEEL_HASH_CHECKED_DOWNLOAD_EXIT_'+$LASTEXITCODE)}
 $wheels=@(Get-ChildItem -LiteralPath $wheelDir -Filter '*.whl' -File)
 if($wheels.Count -ne 10){throw 'WHEEL_SET_INCOMPLETE_OR_EXTRA'}
 $total=0
 foreach($wheel in $wheels){
  if($wheel.Name -notmatch '^([a-zA-Z0-9_]+)-([0-9.]+)-'){throw 'INVALID_WHEEL_FILE_NAME'}
  $name=$Matches[1].Replace('_','-').ToLowerInvariant()
  $version=$Matches[2]
  if(-not $expected.ContainsKey($name)){throw 'WHEEL_NOT_IN_LOCK'}
  if($version -ne $expected[$name].version){throw 'WHEEL_VERSION_MISMATCH'}
  $size=$wheel.Length
  if($size -le 0 -or $size -gt 25000000){throw 'WHEEL_SIZE_EXCEEDED'}
  $total+=$size
  if($total -gt 65000000){throw 'TOTAL_WHEEL_BYTES_EXCEEDED'}
  $hash=(Get-FileHash -LiteralPath $wheel.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  if($hash -ne $expected[$name].sha256){throw ('WHEEL_SHA256_MISMATCH_'+$name)}
  $report.verified_wheels+=@([ordered]@{name=$name;version=$version;sha256=$hash;bytes=$size})
 }
 if(@($report.verified_wheels|Select-Object -ExpandProperty name -Unique).Count -ne 10){throw 'WHEEL_DUPLICATE'}
 $report.wheel_count=$report.verified_wheels.Count
 $report.total_wheel_bytes=$total
 & python -m venv $venv
 if($LASTEXITCODE -ne 0){throw 'ISOLATED_VENV_CREATE_FAILED'}
 $exe=Join-Path $venv 'Scripts/python.exe'
 if(-not(Test-Path -LiteralPath $exe)){throw 'ISOLATED_PYTHON_NOT_FOUND'}
 $env:PIP_NO_INDEX='1'
 & $exe -m pip install --disable-pip-version-check --no-input --no-index --only-binary=:all: --require-hashes --find-links $wheelDir -r $lock
 if($LASTEXITCODE -ne 0){throw ('OFFLINE_HASH_LOCK_INSTALL_EXIT_'+$LASTEXITCODE)}
 $report.offline_install_verified=$true
 # No model import or downloaded code in this stage. Validate imports in isolated venv.
 & $exe (Join-Path $PSScriptRoot 'supertonic3_locked_runtime_verify.py') $Out
 if($LASTEXITCODE -ne 0){throw 'VENV_IMPORT_AND_VERSIONS_NOT_VERIFIED'}
 $report.installed_versions_verified=$true
 $report.venv_isolated=$true
 $report.status='HASH_LOCKED_ISOLATED_WINDOWS_VENV_READY'
} catch {
 $problem=$_.Exception.GetType().Name+': '+$_.Exception.Message
 $report.status='HASH_LOCKED_RUNTIME_BLOCKED'
 $report.failure_type=$problem.Substring(0,[Math]::Min(230,$problem.Length))
} finally {
 Remove-Item -LiteralPath $wheelDir -Force -Recurse -ErrorAction SilentlyContinue
 $report | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $reportFile -Encoding utf8
 Write-Output ('ST3_LOCKED_RUNTIME_STATUS='+$report.status)
 Write-Output ('ST3_LOCKED_WHEEL_COUNT='+$report.wheel_count)
 Write-Output 'ST3_NO_MODEL_OR_VOICE_EXECUTED_DURING_RUNTIME_LOCK'
}
if($problem){throw $problem}
