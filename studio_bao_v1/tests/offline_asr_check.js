"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const dir=process.argv[2];
assert.ok(dir&&fs.existsSync(dir));
const r=JSON.parse(fs.readFileSync(path.join(dir,"offline-asr-probe.json"),"utf8"));
assert.equal(r.engine,"System.Speech.Recognition.SpeechRecognitionEngine");
const allowed=new Set(["NO_GENERATED_WAV_FOR_ASR","NO_EN_US_OFFLINE_RECOGNIZER","NO_DICTATION_RESULT","DICTATION_TRANSCRIPT_MEASURED_NOT_ACOUSTIC_CERTIFICATION","ASR_ENGINE_UNAVAILABLE"]);
assert.ok(allowed.has(r.status),"ASR_UNKNOWN_STATUS");
assert.ok(Number.isInteger(r.recognizer_count)&&r.recognizer_count>=0&&r.recognizer_count<100);
assert.ok(Array.isArray(r.supported_cultures));
if(r.status==="DICTATION_TRANSCRIPT_MEASURED_NOT_ACOUSTIC_CERTIFICATION"){
 assert.ok(typeof r.transcript==="string"&&r.transcript.length>0);
 assert.ok(typeof r.confidence==="number"&&r.confidence>=0&&r.confidence<=1);
 assert.ok(typeof r.normalized_word_overlap==="number"&&r.normalized_word_overlap>=0&&r.normalized_word_overlap<=1);
 console.log("OFFLINE_TTS_ASR_TRANSCRIPT_MEASURED="+JSON.stringify({confidence:r.confidence,wordOverlap:r.normalized_word_overlap,transcript:r.transcript}));
 console.log("OFFLINE_TTS_SPEECH_INTELLIGIBILITY_ONLY_PROXY_NOT_VERIFIED_QUALITY");
}else{
 assert.equal(r.transcript,null);
 console.log("OFFLINE_TTS_ASR_NOT_AVAILABLE="+r.status);
}
console.log("OFFLINE_ASR_PROBE_CONTRACT_PASS");
