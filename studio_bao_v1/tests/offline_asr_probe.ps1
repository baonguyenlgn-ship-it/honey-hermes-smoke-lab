# Offline Windows dictation-only recognizer probe; records no microphone data.
param([Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference='Stop'
$reportPath=Join-Path $OutputDir 'offline-asr-probe.json'
$wavPath=Join-Path $OutputDir 'offline-voice-test.wav'
$report=[ordered]@{
 status="NOT_CHECKED"; engine="System.Speech.Recognition.SpeechRecognitionEngine"
 recognizer_count=0; supported_cultures=@(); transcript=$null; confidence=$null
 normalized_word_overlap=$null; note="Dictation-only independent audio content proxy, NOT acoustic/aesthetic/identity/licensing acceptance."
}
$engine=$null
try {
 if (-not (Test-Path -LiteralPath $wavPath)){
  $report.status="NO_GENERATED_WAV_FOR_ASR"
 } else {
  Add-Type -AssemblyName System.Speech -ErrorAction Stop
  $recognizers=@([System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers())
  $report.recognizer_count=$recognizers.Count
  $report.supported_cultures=@($recognizers | ForEach-Object {$_.Culture.Name} | Sort-Object -Unique)
  $english=@($recognizers | Where-Object {$_.Culture.Name -eq "en-US"})
  if($english.Count -eq 0){$report.status="NO_EN_US_OFFLINE_RECOGNIZER"}
  else {
    $engine=[System.Speech.Recognition.SpeechRecognitionEngine]::new($english[0].Culture)
    $engine.LoadGrammar([System.Speech.Recognition.DictationGrammar]::new())
    $engine.SetInputToWaveFile($wavPath)
    $heard=$engine.Recognize([TimeSpan]::FromSeconds(15))
    if($null -eq $heard){$report.status="NO_DICTATION_RESULT"}
    else {
      $report.transcript=$heard.Text
      $report.confidence=[Math]::Round([double]$heard.Confidence,4)
      $expectedWords=@("honey","studio","offline","test","this","is","a","generic","sample","voice","not","bao")
      $heardWords=@([regex]::Matches($heard.Text.ToLowerInvariant(),'[a-z]+') | ForEach-Object {$_.Value} | Select-Object -Unique)
      $matched=@($expectedWords | Where-Object { $heardWords -contains $_ }).Count
      $report.normalized_word_overlap=[Math]::Round(($matched/$expectedWords.Count),3)
      $report.status="DICTATION_TRANSCRIPT_MEASURED_NOT_ACOUSTIC_CERTIFICATION"
    }
  }
 }
}catch{
 $report.status="ASR_ENGINE_UNAVAILABLE"
 $report.note="Offline ASR failed: "+$_.Exception.GetType().Name+". No intelligibility claims."
}finally{
 if($engine){$engine.Dispose()}
 $report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $reportPath -Encoding utf8
}
Write-Output ("OFFLINE_ASR_PROBE_STATUS="+$report.status)
Write-Output ("OFFLINE_ASR_INSTALLED_COUNT="+$report.recognizer_count)
Write-Output ("OFFLINE_ASR_OVERLAP="+$report.normalized_word_overlap)
