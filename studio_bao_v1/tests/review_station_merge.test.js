"use strict";
const test=require("node:test"),a=require("node:assert/strict"),fs=require("node:fs"),os=require("node:os"),
 path=require("node:path"),crypto=require("node:crypto"),cp=require("node:child_process");
const core=require("../reviewer/review_station_core.js"),proto=require("../reviewer/review_protocol_data.js");
const {reconcile,sampleDigest}=require("../reviewer/review_station_merge.js");
function makeRater(lang,idx){
 const rows={};for(const s of proto.samples.filter(x=>x.locale===lang)){
   rows[s.id]={audioSha256:crypto.createHash("sha256").update("ONLY_SYNTHETIC_"+s.id).digest("hex"),
     scores:Object.fromEntries(core.DIMS.map(d=>[d,4])),remark:"NONE",errors:[],listened:true,ended:true};
 }
 return core.buildContribution({protocol:proto,scriptHash:sampleDigest,locale:lang,
   reviewerRef:lang+"_reviewer0"+idx,rows,sessionAttested:true});
}
const fixture=()=>[makeRater("vi",1),makeRater("vi",2),makeRater("ko",1),makeRater("ko",2)];
const copy=x=>structuredClone(x);
test("four synthetic reviewer contributions become 16-row screening packet, never human accepted",()=>{
 const r=reconcile(fixture(),{simulation:true});
 a.equal(r.packet.reviews.length,16);a.equal(r.packet.simulation_only,true);
 a.equal(r.screening.status,"SYNTHETIC_ONLY_NEVER_HUMAN_PASS");
 a.equal(r.screening.screening_candidate,true);
 a.equal(r.screening.human_listening_verified,false);
 a.equal(r.provenance.matching_sample_hashes,8);
 a.equal(r.provenance.actual_sample_origin_independently_verified,false);
 a.equal(r.provenance.commercial_release_authorized,false);
});
test("an allegedly real set may be screened but never authenticated by the tool",()=>{
 const r=reconcile(fixture());
 a.equal(r.packet.status,"REVIEW_SUBMITTED_UNVERIFIED");
 a.equal(r.screening.status,"SCREENING_ELIGIBLE_NEEDS_EXTERNAL_ATTESTATION");
 a.equal(r.screening.human_listening_verified,false);
 a.equal(r.packet.human_signoff_verified,false);
 a.equal(r.packet.external_consent_verified,false);
});
const bad=[
 ["fewer than four contribution files",x=>x.pop()],
 ["duplicate reviewer pseudonym",x=>x[1]=copy(x[0])],
 ["same locale four times",x=>x[2]=makeRater("vi",3)],
 ["reviewer claims other language",x=>x[2].reviewer_ref="vi_badcross01"],
 ["changed WAV hash for one reviewer",x=>{
    x[1].audio_sha256_by_sample["VI-SHIP-03"]="a".repeat(64);
    x[1].reviews[2].audio_sha256="a".repeat(64);
 }],
 ["reused audio between different scripts",x=>{
    const shared=x[0].audio_sha256_by_sample["VI-DISC-01"];
    for(const i of [0,1]){
      x[i].audio_sha256_by_sample["VI-FRUIT-02"]=shared;
      x[i].reviews[1].audio_sha256=shared;
    }
 }],
 ["fake external identity acceptance",x=>x[0].external_identity_verified=true],
 ["fake audio embedded",x=>x[0].includes_audio=true],
 ["fake legal commercial authorization",x=>x[3].commercial_release_authorized=true],
 ["fake model version",x=>x[0].source_revision="latest"],
 ["missing one script",x=>x[0].reviews.pop()],
 ["invalid reviewer rating",x=>x[0].reviews[0].scores.pronunciation=7],
 ["duplicate review in contribution",x=>x[0].reviews[1].sample_id=x[0].reviews[0].sample_id],
 ["listener falsely never heard file",x=>x[1].reviews[2].listening_attested=false]
];
for(const [name,mutate] of bad)test("reject "+name,()=>{
 const x=fixture();mutate(x);a.throws(()=>reconcile(x,{simulation:true}),name);
});
test("critical delivery error forces repair despite perfect other scores",()=>{
 const x=fixture();x[0].reviews[2].critical_error_codes=["WRONG_DELIVERY"];
 const r=reconcile(x,{simulation:true});a.equal(r.screening.screening_candidate,false);
 a.ok(r.screening.critical_errors>0);
});
test("disagreement forces adjudication even when average looks acceptable",()=>{
 const x=fixture();
 x[0].reviews[0].scores.pronunciation=2;x[1].reviews[0].scores.pronunciation=5;
 const r=reconcile(x,{simulation:true});
 a.equal(r.screening.requires_adjudication,true);
 a.equal(r.screening.screening_candidate,false);
});
test("CLI exports metadata only, refuses overwriting existing report",()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"honey-review-merge-"));
 try{
  const inputs=fixture().map((x,i)=>{
   const file=path.join(dir,"r"+i+".json");fs.writeFileSync(file,JSON.stringify(x));return file;
  });
  const out=path.join(dir,"screened.json"),args=[path.join(__dirname,"../reviewer/review_station_merge.js"),"--simulation",...inputs,out];
  const result=cp.spawnSync(process.execPath,args,{encoding:"utf8",timeout:10000});
  a.equal(result.status,0,result.stderr);
  const obj=JSON.parse(fs.readFileSync(out,"utf8"));
  a.equal(obj.packet.reviews.length,16);a.equal(obj.screening.human_listening_verified,false);
  a.equal(obj.packet.includes_audio,false);a.equal(obj.provenance.local_only,true);
  a.equal(fs.readdirSync(dir).filter(x=>/\.(wav|onnx|whl)$/i.test(x)).length,0);
  const repeat=cp.spawnSync(process.execPath,args,{encoding:"utf8",timeout:10000});
  a.notEqual(repeat.status,0,"OVERWRITE_MUST_BE_REJECTED");
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
