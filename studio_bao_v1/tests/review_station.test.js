"use strict";
const test=require("node:test"),a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const base=path.resolve(__dirname,"../reviewer"),core=require("../reviewer/review_station_core.js");
const protocol=require("../reviewer/review_protocol_data.js");
const actual=JSON.parse(fs.readFileSync(path.join(__dirname,"../voice/listening_qa_protocol.json"),"utf8"));
const hash=crypto.createHash("sha256").update(JSON.stringify(protocol.samples)).digest("hex");
const copy=x=>structuredClone(x);
function makeWav({rate=44100,channels=1,format=1,sample=16,seconds=1.5}={}){
 const frames=Math.ceil(rate*seconds),dataSize=frames*channels*(sample/8),buf=Buffer.alloc(44+dataSize);
 buf.write("RIFF",0);buf.writeUInt32LE(buf.length-8,4);buf.write("WAVEfmt ",8);buf.writeUInt32LE(16,16);
 buf.writeUInt16LE(format,20);buf.writeUInt16LE(channels,22);buf.writeUInt32LE(rate,24);
 buf.writeUInt32LE(rate*channels*(sample/8),28);buf.writeUInt16LE(channels*(sample/8),32);
 buf.writeUInt16LE(sample,34);buf.write("data",36);buf.writeUInt32LE(dataSize,40);
 for(let n=0;n<frames;n++)buf.writeInt16LE(Math.round(4000*Math.sin(2*Math.PI*220*n/rate)),44+n*2);
 return buf.buffer.slice(buf.byteOffset,buf.byteOffset+buf.byteLength);
}
function rowsFor(locale){
 const rows={};let i=1;
 for(const s of protocol.samples.filter(s=>s.locale===locale)){
  rows[s.id]={listened:true,ended:true,audioSha256:crypto.createHash("sha256").update(s.id).digest("hex"),
   scores:Object.fromEntries(core.DIMS.map(k=>[k,4])),errors:[],remark:"NONE"};i++;
 }
 return rows;
}
function build(locale="vi"){return core.buildContribution({protocol,scriptHash:hash,locale,reviewerRef:locale+"_reviewer01",rows:rowsFor(locale),sessionAttested:true});}
test("four VI and four KO fixed scripts match canonical protocol, SHA",()=>{
 a.equal(protocol.samples.length,8);a.deepEqual(protocol.samples,actual.samples);
 a.equal(hash,"5475ca26774f39250a8a57d108feaf9955a8cfec0b6db38d0cfaac4c34660c4d");
 a.equal(protocol.model_revision,actual.source.revision);
});
test("synthetic mono PCM16 WAV has recognized finite 44.1kHz format",()=>{
 const wav=core.parseWav(makeWav());a.equal(wav.sample_rate,44100);a.equal(wav.duration_seconds,1.5);
});
const cases=[
 ["RIFF corruption",b=>new Uint8Array(b)[0]=0],
 ["wrong sample rate",b=>new DataView(b).setUint32(24,48000,true)],
 ["fake non-PCM",b=>new DataView(b).setUint16(20,3,true)],
 ["stereo file",b=>new DataView(b).setUint16(22,2,true)],
 ["wrong bit depth",b=>new DataView(b).setUint16(34,8,true)],
 ["truncated riff reported length",b=>new DataView(b).setUint32(4,33,true)],
 ["oversized data chunk",b=>new DataView(b).setUint32(40,999999999,true)]
];
for(const [label,fn] of cases)test("reject malformed WAV "+label,()=>{const b=makeWav();fn(b);a.throws(()=>core.parseWav(b));});
test("valid local reviewer contribution is JSON-only and always unverified",()=>{
 for(const lang of ["vi","ko"]){
  const c=build(lang);a.equal(c.reviews.length,4);
  a.equal(c.status,"LOCAL_SELF_ATTESTED_UNVERIFIED");a.equal(c.external_identity_verified,false);
  a.equal(c.external_consent_verified,false);a.equal(c.human_signoff_verified,false);
  a.equal(c.commercial_release_authorized,false);a.equal(c.includes_audio,false);
  a.equal(core.validateContribution(c,{...protocol,script_sha256:hash}).release,false);
  a.ok(!JSON.stringify(c).includes("RIFF"));
 }
});
test("reject unauthorized session",()=>a.throws(()=>core.buildContribution({protocol,scriptHash:hash,locale:"vi",reviewerRef:"vi_reviewer01",rows:rowsFor("vi"),sessionAttested:false})));
test("reject unplayed or not self-attested sample",()=>{
 const rows=rowsFor("vi");rows["VI-FRUIT-02"].ended=false;
 a.throws(()=>core.buildContribution({protocol,scriptHash:hash,locale:"vi",reviewerRef:"vi_reviewer01",rows,sessionAttested:true}));
 rows["VI-FRUIT-02"].ended=true;rows["VI-FRUIT-02"].listened=false;
 a.throws(()=>core.buildContribution({protocol,scriptHash:hash,locale:"vi",reviewerRef:"vi_reviewer01",rows,sessionAttested:true}));
});
test("reject duplicate local WAV audio hash across scripts",()=>{
 const c=build();c.audio_sha256_by_sample["VI-FRUIT-02"]=c.audio_sha256_by_sample["VI-DISC-01"];
 c.reviews[1].audio_sha256=c.reviews[0].audio_sha256;
 a.throws(()=>core.validateContribution(c,{...protocol,script_sha256:hash}));
});
test("reject missing scores and fake commercial approvals",()=>{
 const c=build();delete c.reviews[0].scores.pronunciation;
 a.throws(()=>core.validateContribution(c,{...protocol,script_sha256:hash}));
 const d=build();d.commercial_release_authorized=true;
 a.throws(()=>core.validateContribution(d,{...protocol,script_sha256:hash}));
});
test("reject PII-ish pseudonym and wrong model/script provenance",()=>{
 a.equal(core.safeReviewerId("vi_reviewer01"),true);
 for(const name of ["bao_nguyen","admin_account","email_test01","0977123456@","nguyen bao","x"])a.equal(core.safeReviewerId(name),false);
 const c=build();c.source_revision="main";a.throws(()=>core.validateContribution(c,{...protocol,script_sha256:hash}));
});
test("static browser code is local-only, no external network or persistent storage",()=>{
 const page=fs.readFileSync(path.join(base,"review_station.html"),"utf8");
 const client=fs.readFileSync(path.join(base,"review_station_ui.js"),"utf8");
 const css=fs.readFileSync(path.join(base,"review_station.css"),"utf8");
 a.match(page,/connect-src 'none'/);a.match(page,/default-src 'none'/);
 a.match(page,/media-src blob:/);a.match(page,/script-src 'self'/);
 a.doesNotMatch(page,/<script(?![^>]*src=)[^>]*>/i);
 a.doesNotMatch(page,/<iframe|<form|https?:\/\//i);
 a.doesNotMatch(client,/\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bsendBeacon\b|localStorage|indexedDB|serviceWorker|navigator\.mediaDevices/);
 a.doesNotMatch(css,/@import|url\s*\(\s*https?:/i);
 for(const file of ["review_protocol_data.js","review_station_core.js","review_station_ui.js","review_station.css"])a.ok(fs.existsSync(path.join(base,file)));
});
