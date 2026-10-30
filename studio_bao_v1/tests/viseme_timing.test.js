"use strict";
const test=require("node:test"),a=require("node:assert/strict");
const BaoVisemeTiming=require("../viseme_timing.js");
const sha="a".repeat(64);
const audio=Object.freeze({integrity:"WAV_SHA256_MATCHED",alignment:"MANUAL_NOT_VERIFIED_WITH_SPEECH",
 rights:"NOT_VERIFIED",language:"vi",product:"mango",audioSha256:sha,
 audio:Object.freeze({durationMs:1000})});
const fixture=()=>({
 version:1,method:"manual_viseme_cues_unverified",provenance:"synthetic_dev_fixture",
 language:"vi",product:"mango",audioSha256:sha,durationMs:1000,
 segments:[
  {startMs:0,endMs:200,shape:"REST"},
  {startMs:200,endMs:450,shape:"BMP"},
  {startMs:450,endMs:700,shape:"AA"},
  {startMs:700,endMs:950,shape:"OO"},
  {startMs:950,endMs:1000,shape:"REST"}
 ]
});
test("bounded exact WAV-bound synthetic track maps closed/BMP/AA/OO and never claims lip-sync",()=>{
 const x=BaoVisemeTiming.verify({track:fixture(),verifiedAudio:audio});
 a.equal(x.method,"MANUAL_VISEME_TIMELINE_UNVERIFIED");
 a.equal(x.actualLipSync,false);a.equal(x.actualPhonemeAlignment,false);
 a.equal(x.commercialApproved,false);
 a.equal(BaoVisemeTiming.shapeAt(x,0),"REST");
 a.equal(BaoVisemeTiming.shapeAt(x,300),"BMP");
 a.equal(BaoVisemeTiming.shapeAt(x,500),"AA");
 a.equal(BaoVisemeTiming.shapeAt(x,810),"OO");
 a.equal(BaoVisemeTiming.shapeAt(x,999),"REST");
 for(const t of [-10,1000,5000,NaN])a.equal(BaoVisemeTiming.shapeAt(x,t),"REST");
});
const tamper=[
 ["unverified WAV",x=>{x.a.integrity="UNKNOWN"}],
 ["fake verified alignment",x=>{x.a.alignment="REAL_NATIVE_LIP_SYNC_PASS"}],
 ["fake rights",x=>{x.a.rights="APPROVED"}],
 ["wrong SHA",x=>{x.t.audioSha256="f".repeat(64)}],
 ["wrong language",x=>{x.t.language="ko"}],
 ["wrong product",x=>{x.t.product="pomelo"}],
 ["wrong duration",x=>{x.t.durationMs=1100}],
 ["extra unsafe metadata",x=>{x.t.publicUrl="https://not-allowed"}],
 ["fake model verified",x=>{x.t.provenance="native_verified"}],
 ["fake source method",x=>{x.t.method="forced_align_verified"}],
 ["zero segments",x=>{x.t.segments=[]}],
 ["segment overlaps",x=>{x.t.segments[1].startMs=100}],
 ["segment gap",x=>{x.t.segments[2].startMs=460}],
 ["segment out of bounds",x=>{x.t.segments[4].endMs=1100}],
 ["negative start",x=>{x.t.segments[0].startMs=-1}],
 ["fractional timestamp",x=>{x.t.segments[2].endMs=700.7}],
 ["too short segment",x=>{x.t.segments[4].startMs=980}],
 ["not closed at beginning",x=>{x.t.segments[0].shape="AA"}],
 ["not closed at end",x=>{x.t.segments[4].shape="BMP"}],
 ["arbitrary viseme shape",x=>{x.t.segments[2].shape="<script>"}],
 ["extra segment field",x=>{x.t.segments[0].confidence=1}],
 ["extra audio retention claim",x=>{x.t.audioBytes=123}],
 ["audio missing",x=>{x.a=null}]
];
for(const [label,mutation] of tamper)test("reject forged/malformed track: "+label,()=>{
 const x={t:fixture(),a:structuredClone(audio)};mutation(x);
 a.throws(()=>BaoVisemeTiming.verify({track:x.t,verifiedAudio:x.a}),label);
});
test("code only allows manual/unverified source, never auto assertion",()=>{
 a.deepEqual(BaoVisemeTiming.ALLOWED,["REST","BMP","AA","EE","OO","FV","L"]);
 a.equal(BaoVisemeTiming.MAX_SEGMENTS,256);
});
