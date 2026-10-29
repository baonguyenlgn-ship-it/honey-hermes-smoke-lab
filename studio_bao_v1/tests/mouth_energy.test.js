"use strict";
const test=require("node:test"),a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const mouth=require("../mouth_energy.js");
function wav({rate=8000,duration=1,channels=1,bits=16,silent=false,format=1}={}){
 const frames=Math.round(rate*duration),length=frames*channels*bits/8;
 const b=Buffer.alloc(44+length);
 b.write("RIFF",0);b.writeUInt32LE(b.length-8,4);b.write("WAVE",8);
 b.write("fmt ",12);b.writeUInt32LE(16,16);b.writeUInt16LE(format,20);
 b.writeUInt16LE(channels,22);b.writeUInt32LE(rate,24);
 b.writeUInt32LE(rate*channels*bits/8,28);b.writeUInt16LE(channels*bits/8,32);
 b.writeUInt16LE(bits,34);b.write("data",36);b.writeUInt32LE(length,40);
 if(bits===16){
  for(let i=0;i<frames;i++)for(let c=0;c<channels;c++){
   const n=silent||i<frames/2?0:Math.round(15000*Math.sin(2*Math.PI*220*i/rate));
   b.writeInt16LE(n,44+(i*channels+c)*2);
  }
 }
 return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);
}
test("silence then voiced PCM produces deterministic bounded mouth openings",()=>{
 const env=mouth.envelope(wav());
 a.equal(env.durationMs,1000);a.equal(env.hopMs,20);a.equal(env.channels,1);
 a.equal(env.method,"PCM_RMS_20MS_NOT_PHONEMES");
 a.equal(mouth.valueAt(env,200),0);
 a.equal(mouth.valueAt(env,499),0);
 a.ok(mouth.valueAt(env,700)>.25);
 a.equal(mouth.valueAt(env,1000),0);
 a.equal(mouth.valueAt(env,-4),0);
 a.equal(mouth.valueAt(env,Number.NaN),0);
 a.deepEqual(env.open,mouth.envelope(wav()).open,"IN_PROCESS_ENVELOPE_DETERMINISTIC");
});
test("pure silence never animates silhouette",()=>{
 const x=mouth.envelope(wav({silent:true}));a.ok(x.open.every(v=>v===0));
});
test("stereo PCM16 supported via bounded mono mixing",()=>{
 const x=mouth.envelope(wav({channels:2}));a.equal(x.channels,2);a.ok(mouth.valueAt(x,720)>.15);
});
const invalid=[
 ["empty",()=>new ArrayBuffer(0)],
 ["corrupt RIFF",()=>{const b=wav();new Uint8Array(b)[0]=0;return b;}],
 ["wrong declared RIFF length",()=>{const b=wav();new DataView(b).setUint32(4,123,true);return b;}],
 ["unsupported sample format",()=>wav({format:3})],
 ["too many channels",()=>wav({channels:3})],
 ["invalid bit depth",()=>wav({bits:8})],
 ["invalid sample rate",()=>wav({rate:4000})],
 ["truncated PCM",()=>{const b=wav();new DataView(b).setUint32(40,999999,true);return b;}],
 ["missing data",()=>{const b=wav();new Uint8Array(b).set([88,88,88,88],36);return b;}],
 ["too short",()=>wav({duration:.3})]
];
for(const [name,fn] of invalid)test("fail closed WAV "+name,()=>a.throws(()=>mouth.envelope(fn())));
test("existing verified audio UI only activates through the local WAV event and clears",()=>{
 const app=fs.readFileSync(path.resolve(__dirname,"../app.js"),"utf8");
 const html=fs.readFileSync(path.resolve(__dirname,"../index.html"),"utf8");
 const js=fs.readFileSync(path.resolve(__dirname,"../mouth_preview.js"),"utf8");
 a.match(app,/honey:verified-local-wav/);
 a.match(app,/honey:local-wav-cleared/);
 a.match(js,/honey:verified-local-wav/);a.match(js,/honey:local-wav-cleared/);
 a.match(js,/actualLipSync:false/);
 a.match(html,/id="avatar-mouth"/);a.match(html,/id="mouth-preview-status"/);
 a.match(html,/mouth_energy\.js/);a.match(html,/mouth_preview\.js/);
 a.doesNotMatch(js,/\bfetch\(|WebSocket|XMLHttpRequest|localStorage|sendBeacon/);
});
