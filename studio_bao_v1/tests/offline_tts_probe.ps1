# Isolated GitHub-hosted Windows SAPI probe: NO AI inference, NO download, NO voice cloning.
param([Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$reportPath=Join-Path $OutputDir "offline-tts-probe.json"
$wavPath=Join-Path $OutputDir "offline-voice-test.wav"
$report=[ordered]@{
  status="UNTESTED"; engine="System.Speech.Synthesis.SpeechSynthesizer"
  engine_installed=$false; voice_count=0; voice_name=$null; voice_culture=$null
  available_cultures=@(); has_vi_voice=$false; has_ko_voice=$false
  test_text_language="en-US"; test_text="Honey studio offline test. This is a generic sample voice, not Bao."
  audio_sha256=$null; audio_bytes=0; note="DEMO ONLY. No verified speech quality, owner likeness or commercial rights."
}
$synth=$null
try {
  Add-Type -AssemblyName System.Speech -ErrorAction Stop
  $report.engine_installed=$true
  $synth=[System.Speech.Synthesis.SpeechSynthesizer]::new()
  $voices=@($synth.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo })
  $report.voice_count=$voices.Count
  $report.available_cultures=@($voices | ForEach-Object { $_.Culture.Name } | Sort-Object -Unique)
  $report.has_vi_voice=@($voices | Where-Object { $_.Culture.Name -match "^vi-" }).Count -gt 0
  $report.has_ko_voice=@($voices | Where-Object { $_.Culture.Name -match "^ko-" }).Count -gt 0
  if ($voices.Count -eq 0) {
    $report.status="NO_INSTALLED_SYSTEM_SPEECH_VOICES"
  } else {
    $english=@($voices | Where-Object { $_.Culture.Name -match "^en-" })
    if ($english.Count -eq 0) {
      $report.status="NO_ENGLISH_VOICE_FOR_SAFE_TEST"
    } else {
      $voice=$english[0]
      $report.voice_name=$voice.Name
      $report.voice_culture=$voice.Culture.Name
      $synth.SelectVoice($voice.Name)
      $synth.SetOutputToWaveFile($wavPath)
      try {
        $synth.Speak([string]$report.test_text)
      } finally {
        $synth.SetOutputToNull()
      }
      if (-not (Test-Path -LiteralPath $wavPath)) {throw "SAPI_DID_NOT_EMIT_WAV"}
      $file=Get-Item -LiteralPath $wavPath
      $report.audio_bytes=$file.Length
      $report.audio_sha256=(Get-FileHash -LiteralPath $wavPath -Algorithm SHA256).Hash.ToLowerInvariant()
      $report.status="WAV_EMITTED_NEEDS_INDEPENDENT_CHECK"
    }
  }
} catch {
  $report.status="SAPI_PROBE_NOT_AVAILABLE"
  $report.note="SAPI failed or unavailable. No claims of voice generation. ReasonType: "+$_.Exception.GetType().Name
  Remove-Item -LiteralPath $wavPath -ErrorAction SilentlyContinue
} finally {
  if ($null -ne $synth) { $synth.Dispose() }
  $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
}
Write-Output ("OFFLINE_TTS_PROBE_STATUS="+$report.status)
Write-Output ("OFFLINE_TTS_INSTALLED_VOICE_COUNT="+$report.voice_count)
Write-Output ("OFFLINE_TTS_HAS_VI="+$report.has_vi_voice+" HAS_KO="+$report.has_ko_voice)
Write-Output ("OFFLINE_TTS_REPORT="+$reportPath)
