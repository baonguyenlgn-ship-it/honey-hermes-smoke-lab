"use strict";
// Independent byte-level QA only: does NOT certify Korean pronunciation or commercial rights.
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const root=process.argv[2];
assert.ok(root && fs.existsSync(root),"KO_OUTPUT_DIR_ABSENT");
const meta=JSON.parse(fs.readFileSync(path.join(root,"ko-offline-synthesis-probe.json"),"utf8"));
assert.equal(meta.schema,"honey.ko-offline-synthesis-research.v1");
assert.equal(meta.language,"ko-KR");
assert.equal(meta.engine,"eSpeak NG 1.52.0 (GPL-3.0-or-later)");
assert.equal(meta.voice_persona,"GENERIC_NON_OWNER");
assert.equal(meta.package_pin_verified,true);
assert.equal(meta.korean_voice_detected,true);
assert.equal(meta.native_listener_quality_verified,false);
assert.equal(meta.premium_male_voice_verified,false);
assert.equal(meta.commercial_integration_approved,false);
assert.equal(meta.asr_verified,false);
assert.equal(meta.status,"KO_WAV_EMITTED_PENDING_INDEPENDENT_QA");
const wav=fs.readFileSync(path.join(root,"ko-research-speech.wav"));
assert.equal(wav.length,meta.wav_bytes);
assert.equal(crypto.createHash("sha256").update(wav).digest("hex"),meta.wav_sha256);
assert.equal(wav.toString("ascii",0,4),"RIFF");
assert.equal(wav.toString("ascii",8,12),"WAVE");
assert.equal(wav.readUInt32LE(4)+8,wav.length);
let off=12,rate=0,channels=0,bits=0,format=0,block=0,data=null;
while(off+8<=wav.length){
 const typ=wav.toString("ascii",off,off+4),size=wav.readUInt32LE(off+4),pos=off+8;
 assert.ok(size<=wav.length-pos,"KO_WAV_CHUNK_OVERRUN");
 if(typ==="fmt "){
   assert.ok(size>=16);
   format=wav.readUInt16LE(pos);channels=wav.readUInt16LE(pos+2);
   rate=wav.readUInt32LE(pos+4);block=wav.readUInt16LE(pos+12);bits=wav.readUInt16LE(pos+14);
 }
 if(typ==="data"){assert.equal(data,null,"KO_DUPLICATE_AUDIO_DATA");data=wav.subarray(pos,pos+size);}
 off=pos+size+(size&1);
}
assert.equal(format,1,"KO_EXPECTED_PCM");
assert.equal(bits,16,"KO_EXPECTED_16BIT");
assert.equal(channels,1,"KO_EXPECTED_MONO");
assert.ok(rate>=16000 && rate<=48000,"KO_RATE_INVALID");
assert.equal(block,2,"KO_BLOCK_ALIGNMENT");
assert.ok(data && data.length>=rate && data.length%2===0,"KO_WAV_EMPTY");
const n=data.length/2,duration=n/rate;
assert.ok(duration>=1 && duration<=25,"KO_DURATION_UNEXPECTED");
let max=0,sumsq=0,active=0,fullscale=0;
for(let i=0;i<n;i++){
 const v=data.readInt16LE(i*2),a=Math.abs(v);
 max=Math.max(max,a);sumsq+=v*v;
 if(a>512)active++;
 if(a>=32760)fullscale++;
}
const rms=Math.sqrt(sumsq/n)/32768;
assert.ok(rms>.003 && max>1024 && active/n>.04,"KO_SILENT_OR_INVALID_AUDIO");
console.log("KO_WAV_BYTE_QA_PASS="+JSON.stringify({durationSeconds:+duration.toFixed(2),sampleRate:rate,channels,peak:max,rms:+rms.toFixed(4),activeFraction:+(active/n).toFixed(3),fullscaleFraction:+(fullscale/n).toFixed(4),sha256:meta.wav_sha256}));
console.log("KO_ASR_PRONUNCIATION_MALE_PREMIUM_QUALITY_NOT_PROVEN");
console.log("KO_GPL_COMMERCIAL_INTEGRATION_NOT_ACCEPTED");
