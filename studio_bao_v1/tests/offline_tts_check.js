"use strict";
/* Independent byte-level verification only, NOT acoustic intelligibility evaluation. */
const fs=require("node:fs"), path=require("node:path"), crypto=require("node:crypto");
const assert=require("node:assert/strict");
const root=process.argv[2];
assert.ok(root&&fs.existsSync(root),"PROBE_OUTPUT_DIR_MISSING");
const report=JSON.parse(fs.readFileSync(path.join(root,"offline-tts-probe.json"),"utf8"));
const file=path.join(root,"offline-voice-test.wav");
const statuses=new Set(["WAV_EMITTED_NEEDS_INDEPENDENT_CHECK","NO_INSTALLED_SYSTEM_SPEECH_VOICES","NO_ENGLISH_VOICE_FOR_SAFE_TEST","SAPI_PROBE_NOT_AVAILABLE"]);
assert.ok(statuses.has(report.status),"UNKNOWN_PROBE_STATUS");
assert.equal(report.engine,"System.Speech.Synthesis.SpeechSynthesizer");
assert.equal(report.test_text_language,"en-US");
assert.ok(typeof report.note==="string"&&report.note.length>8,"MISSING_CLASSIFICATION_NOTE");
const waveAnalyzer=(b)=>{
 assert.ok(b.length>=44&&b.length<8*1024*1024,"WAV_SIZE_BAD");
 assert.equal(b.toString("ascii",0,4),"RIFF");assert.equal(b.toString("ascii",8,12),"WAVE");
 assert.equal(b.readUInt32LE(4)+8,b.length,"RIFF_LENGTH_BAD");
 let off=12,channels=0,rate=0,bits=0,audioFormat=0,bytesPerSample=0,data=null;
 while(off+8<=b.length){
  const chunk=b.toString("ascii",off,off+4),n=b.readUInt32LE(off+4),start=off+8;
  assert.ok(n<=b.length-start,"CHUNK_TRUNCATED");
  if(chunk==="fmt "){
    assert.ok(n>=16,"FMT_TOO_SHORT");
    audioFormat=b.readUInt16LE(start);channels=b.readUInt16LE(start+2);
    rate=b.readUInt32LE(start+4);bits=b.readUInt16LE(start+14);
    bytesPerSample=b.readUInt16LE(start+12);
  }
  if(chunk==="data"){assert.equal(data,null,"DUPLICATE_DATA");data=b.subarray(start,start+n);}
  off=start+n+(n&1);
 }
 assert.equal(audioFormat,1,"NON_PCM_WAV");
 assert.equal(bits,16,"NOT_16_BIT_PCM");assert.ok(channels===1||channels===2,"BAD_CHANNELS");
 assert.ok(rate>=8000&&rate<=48000,"BAD_SAMPLE_RATE");
 assert.equal(bytesPerSample,channels*2,"INVALID_BLOCK_ALIGNMENT");
 assert.ok(data&&data.length>=rate/2&&data.length%bytesPerSample===0,"EMPTY_OR_SHORT_WAV");
 const duration=data.length/bytesPerSample/rate;
 assert.ok(duration>.5&&duration<=30,"UNEXPECTED_DURATION");
 const samples=data.length/2;
 let nonzero=0,peak=0,sum=0;
 for(let i=0;i<samples;i++){
  const v=data.readInt16LE(i*2);if(Math.abs(v)>512)nonzero++;
  peak=Math.max(peak,Math.abs(v));sum+=v*v;
 }
 const rms=Math.sqrt(sum/samples)/32768;
 const active=nonzero/samples;
 assert.ok(rms>.003&&peak>1024&&active>.04,"SILENT_OR_NEAR_SILENT_WAV");
 return {durationSeconds:Number(duration.toFixed(2)),sampleRate:rate,channels,rms:Number(rms.toFixed(4)),nonSilenceFraction:Number(active.toFixed(3)),peak};
};
if(report.status==="WAV_EMITTED_NEEDS_INDEPENDENT_CHECK"){
 assert.equal(fs.existsSync(file),true,"WAV_MISSING");
 const b=fs.readFileSync(file);
 assert.equal(crypto.createHash("sha256").update(b).digest("hex"),report.audio_sha256,"SHA_READBACK_MISMATCH");
 assert.equal(b.length,report.audio_bytes,"WAV_LENGTH_MISMATCH");
 const m=waveAnalyzer(b);
 console.log("OFFLINE_TTS_WAV_BYTES_NON_SILENT_PASS="+JSON.stringify(m));
 console.log("OFFLINE_TTS_QUALITY_OR_PRONUNCIATION_NOT_PROVEN");
}else{
 assert.equal(fs.existsSync(file),false,"UNEXPECTED_UNVERIFIED_WAV");
 console.log("OFFLINE_TTS_NO_SUPPORTED_INSTALLED_ENGLISH_VOICE="+report.status);
}
console.log("OFFLINE_TTS_PROBE_CHECKS_PASS");
