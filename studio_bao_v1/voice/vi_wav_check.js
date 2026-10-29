"use strict";
// Inspect independently generated WAV bytes. No ASR, voice/timbre, or commercial rights assertion.
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const root=process.argv[2];assert.ok(root && fs.existsSync(root),"VI_OUTPUT_MISSING");
const meta=JSON.parse(fs.readFileSync(path.join(root,"vi-synthesis-probe.json"),"utf8"));
assert.equal(meta.schema,"honey.vi-offline-synthesis-research.v1");
assert.equal(meta.language,"vi-VN");assert.equal(meta.voice_persona,"GENERIC_NON_OWNER");
assert.equal(meta.commercial_rights_approved,false);
assert.equal(meta.target_male_voice_accepted,false);
assert.equal(meta.native_listener_quality_verified,false);
assert.equal(meta.asr_vietnamese_verified,false);
assert.equal(meta.model_hash_verified,true);
assert.equal(meta.runtime_hash_verified,true);
assert.equal(meta.config_hash_verified,true);
assert.equal(meta.status,"WAV_EMITTED_NEEDS_INDEPENDENT_QA");
const wav=fs.readFileSync(path.join(root,"vi-research-speech.wav"));
assert.equal(wav.length,meta.wav_bytes);
assert.equal(crypto.createHash("sha256").update(wav).digest("hex"),meta.wav_sha256);
assert.equal(wav.toString("ascii",0,4),"RIFF");
assert.equal(wav.toString("ascii",8,12),"WAVE");
assert.equal(wav.readUInt32LE(4)+8,wav.length);
let off=12,rate=0,channels=0,bits=0,format=0,data=null;
while(off+8<=wav.length){
 const type=wav.toString("ascii",off,off+4),n=wav.readUInt32LE(off+4),p=off+8;
 assert.ok(n<=wav.length-p,"VI_WAV_CHUNK_OVERRUN");
 if(type==="fmt "){assert.ok(n>=16);format=wav.readUInt16LE(p);channels=wav.readUInt16LE(p+2);rate=wav.readUInt32LE(p+4);bits=wav.readUInt16LE(p+14);}
 if(type==="data"){assert.equal(data,null,"DUPLICATE_DATA");data=wav.subarray(p,p+n);}
 off=p+n+(n&1);
}
assert.equal(format,1,"MUST_BE_PCM");assert.equal(bits,16,"MUST_BE_PCM16");
assert.equal(channels,1,"MUST_BE_MONO");assert.equal(rate,22050,"UNEXPECTED_RATE");
assert.ok(data && data.length>rate*2,"VI_WAV_EMPTY");
const duration=data.length/(rate*channels*2);
assert.ok(duration>1 && duration<25,"VI_WAV_DURATION_INVALID");
let peak=0,active=0,sum=0;const samples=data.length/2;
for(let p=0;p<samples;p++){const v=data.readInt16LE(p*2);if(Math.abs(v)>512)active++;peak=Math.max(peak,Math.abs(v));sum+=v*v;}
const rms=Math.sqrt(sum/samples)/32768;
assert.ok(peak>1024 && rms>.003 && active/samples>.04,"VI_WAV_SILENT_OR_BROKEN");
console.log("VI_WAV_BYTE_QA_PASS="+JSON.stringify({durationSeconds:+duration.toFixed(2),rate,channels,peak,rms:+rms.toFixed(4),activeFraction:+(active/samples).toFixed(3),sha256:meta.wav_sha256}));
console.log("VI_VOICE_PRONUNCIATION_NATIVE_LISTENER_MALE_TIMBRE_NOT_PROVEN");
console.log("VI_COMMERCIAL_RIGHTS_NOT_ACCEPTED");
