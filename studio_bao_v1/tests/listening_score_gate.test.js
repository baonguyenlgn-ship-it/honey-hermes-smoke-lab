"use strict";
const test=require("node:test"),a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const {evaluateReview,digestScripts}=require("../voice/listening_score_gate.js");
const dir=path.join(__dirname,"../voice");
const protocol=JSON.parse(fs.readFileSync(path.join(dir,"listening_qa_protocol.json"),"utf8"));
const empty=JSON.parse(fs.readFileSync(path.join(dir,"listening_qa_scoring_intake_template.json"),"utf8"));
const copy=x=>structuredClone(x);
function packet(){
 const p=copy(empty);
 p.status="SIMULATION_FIXTURE";
 p.simulation_only=true;
 for(const sample of protocol.samples){
   const sha=crypto.createHash("sha256").update("SYNTHETIC_NOT_REAL_AUDIO_"+sample.id).digest("hex");
   p.audio_sha256_by_sample[sample.id]=sha;
   for(let i=1;i<=2;i++){
     const reviewer_ref=sample.locale+"_reviewer0"+i;
     p.reviews.push({
       sample_id:sample.id,locale:sample.locale,reviewer_ref,audio_sha256:sha,
       listening_attested:true,
       scores:Object.fromEntries(protocol.evaluation.dimensions.map(k=>[k,4])),
       critical_error_codes:[],remark_code:"NONE"
     });
   }
 }
 return p;
}
test("empty protocol intake MUST remain BLOCKED, never a human PASS",()=>{
 a.equal(digestScripts(protocol),empty.protocol_script_sha256);
 const r=evaluateReview(copy(empty),protocol);
 a.equal(r.status,"BLOCKED_NO_AUDIO_OR_HUMAN_EVIDENCE");
 a.equal(r.screening_candidate,false);
 a.equal(r.human_listening_verified,false);
 a.equal(r.commercial_release_authorized,false);
});
test("synthetic 16 reviews can screen structure without proving any human listened",()=>{
 const p=packet(),r=evaluateReview(p,protocol);
 a.equal(r.status,"SYNTHETIC_ONLY_NEVER_HUMAN_PASS");
 a.equal(r.review_count,16);
 a.equal(r.language_count,2);
 a.equal(r.screening_candidate,true);
 a.equal(r.human_listening_verified,false);
 a.equal(r.commercial_release_authorized,false);
 a.equal(r.per_sample.length,8);
});
test("claimed non-synthetic review may only be screened pending external attestation",()=>{
 const p=packet();p.status="REVIEW_SUBMITTED_UNVERIFIED";p.simulation_only=false;
 const r=evaluateReview(p,protocol);
 a.equal(r.status,"SCREENING_ELIGIBLE_NEEDS_EXTERNAL_ATTESTATION");
 a.equal(r.human_listening_verified,false);
 a.equal(r.commercial_release_authorized,false);
});
const invalid=[
 ["falsely claim commercial authorization",p=>p.commercial_release_authorized=true],
 ["falsely claim independent human signoff",p=>p.human_signoff_verified=true],
 ["falsely claim external consent verification",p=>p.external_consent_verified=true],
 ["falsely claim external identity verification",p=>p.external_identity_verified=true],
 ["pretend waveform attached",p=>p.includes_audio=true],
 ["wrong eight-script digest",p=>p.protocol_script_sha256="f".repeat(64)],
 ["wrong model revision",p=>p.source_revision="main"],
 ["duplicate reviewer same script",p=>p.reviews[1].reviewer_ref=p.reviews[0].reviewer_ref],
 ["reviewer switches native language",p=>p.reviews[8].reviewer_ref=p.reviews[0].reviewer_ref],
 ["reviewer includes identity hint",p=>p.reviews[0].reviewer_ref="vi_email99"],
 ["out of bounds rating",p=>p.reviews[0].scores.prosody=6],
 ["fractional rating",p=>p.reviews[0].scores.prosody=3.5],
 ["missing score key",p=>delete p.reviews[0].scores.pronunciation],
 ["score without hearing attestation",p=>p.reviews[0].listening_attested=false],
 ["different sample audio SHA",p=>p.reviews[0].audio_sha256="a".repeat(64)],
 ["reuse exact audio across two sentences",p=>p.audio_sha256_by_sample[protocol.samples[1].id]=p.audio_sha256_by_sample[protocol.samples[0].id]],
 ["extra sample not in protocol",p=>p.audio_sha256_by_sample.EXTRA="b".repeat(64)],
 ["unrecognized review sample",p=>p.reviews[0].sample_id="VI-OTHER-99"],
 ["incorrect language tag",p=>p.reviews[0].locale="ko"],
 ["unsupported critical error code",p=>p.reviews[0].critical_error_codes=["APPROVED"]],
 ["free text reviewer name or private details",p=>p.reviews[0].reviewer_private_identity="Full Legal Name"],
 ["unsafe free text note",p=>p.reviews[0].remark_code="send to personal email"],
 ["fake audio URL field",p=>p.audio_url="https://example.com/private.wav"],
 ["invalid packet review mode",p=>p.status="APPROVED"],
 ["empty packet with claimed reviews",p=>{p.status="EMPTY_UNAUTHORIZED";p.simulation_only=false;}]
];
for(const [name,mutate] of invalid)test("fail closed: "+name,()=>{
 const p=packet();mutate(p);
 a.throws(()=>evaluateReview(p,protocol),name);
});
test("one reviewer missing cannot meet 2 independent review sources per sample",()=>{
 const p=packet();
 p.reviews=p.reviews.filter(r=>!(r.sample_id==="VI-FRUIT-02"&&r.reviewer_ref==="vi_reviewer02"));
 const r=evaluateReview(p,protocol);
 a.equal(r.screening_candidate,false);
 a.equal(r.human_listening_verified,false);
});
test("real human looking scores with critical delivery error require correction",()=>{
 const p=packet();p.reviews[11].critical_error_codes=["WRONG_DELIVERY"];
 const r=evaluateReview(p,protocol);
 a.ok(r.critical_errors>0);a.equal(r.screening_candidate,false);
});
test("discordant pronunciation reviews require human adjudication",()=>{
 const p=packet();
 p.reviews[0].scores.pronunciation=2;
 p.reviews[1].scores.pronunciation=5;
 const r=evaluateReview(p,protocol);
 a.equal(r.requires_adjudication,true);
 a.equal(r.screening_candidate,false);
});
test("intelligibility under 4 cannot be overridden by stronger total averages",()=>{
 const p=packet();
 p.reviews[0].scores.word_intelligibility=3;
 p.reviews[1].scores.word_intelligibility=5;
 const r=evaluateReview(p,protocol);
 a.equal(r.screening_candidate,false);
});
