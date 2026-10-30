"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),a=require("node:assert/strict");
const root=process.argv[2];a.ok(root,"NO_OUTPUT_ROOT");
const r=JSON.parse(fs.readFileSync(path.join(root,"inference.json"),"utf8"));
const s=JSON.parse(fs.readFileSync(path.join(root,"source-report.json"),"utf8"));
a.equal(s.status,"INFERENCE_EMITTED_NEEDS_INDEPENDENT_QA");
a.equal(s.weight_hashes.length,4);a.equal(s.auxiliary_hashes.length,4);
a.equal(s.commercial_approved,false);
a.deepEqual(r.languages,["vi","ko"]);a.equal(r.voice,"M1 generic preset");
a.equal(r.quality_accepted,false);a.equal(r.native_listener_checked,false);
a.equal(r.commercial_accepted,false);a.equal(r.owner_identity,false);
a.equal(r.results.length,2);
for(const item of r.results){
  const file=path.join(root,"st3-m1-"+item.locale+".wav");
  const w=fs.readFileSync(file);
  a.equal(w.length,item.wav_bytes);a.equal(crypto.createHash("sha256").update(w).digest("hex"),item.wav_sha256);
  a.equal(w.toString("ascii",0,4),"RIFF");a.equal(w.toString("ascii",8,12),"WAVE");
  a.equal(w.readUInt32LE(4)+8,w.length);
  let off=12,fmt=0,bits=0,channels=0,rate=0,pcm=null;
  while(off+8<=w.length){const name=w.toString("ascii",off,off+4),size=w.readUInt32LE(off+4),pos=off+8;a.ok(size<=w.length-pos);
    if(name==="fmt "){fmt=w.readUInt16LE(pos);channels=w.readUInt16LE(pos+2);rate=w.readUInt32LE(pos+4);bits=w.readUInt16LE(pos+14);}
    if(name==="data")pcm=w.subarray(pos,pos+size);off=pos+size+(size&1);
  }
  a.equal(fmt,1);a.equal(channels,1);a.equal(bits,16);a.equal(rate,r.sample_rate);a.ok(pcm);
  const n=pcm.length/2,dur=n/rate;a.ok(dur>0.8&&dur<25);let sum=0,active=0,peak=0;
  for(let i=0;i<n;i++){let v=pcm.readInt16LE(i*2),z=Math.abs(v);sum+=v*v;peak=Math.max(peak,z);if(z>512)active++;}
  const rms=Math.sqrt(sum/n)/32768;a.ok(rms>0.002&&peak>1000&&active/n>.03,"AUDIO_NOT_VERIFIED");
  a.ok(item.elapsed_seconds>=0 && item.realtime_factor>=0);
  console.log("SUPER3_REAL_AUDIO_BYTES_PASS="+JSON.stringify({language:item.locale,durationSeconds:+dur.toFixed(2),elapsed:item.elapsed_seconds,rtf:item.realtime_factor,rms:+rms.toFixed(4),sha256:item.wav_sha256}));
}
console.log("SUPER3_M1_NATIVE_PRONUNCIATION_PREMIUM_VOICE_AND_COMMERCIAL_RIGHTS_NOT_ACCEPTED");
