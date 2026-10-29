"use strict";
// Metadata-only human listening review triage. No evidence of actual listening is manufactured.
const a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const FIELDS=["word_intelligibility","pronunciation","prosody","naturalness","male_presenting_timbre"];
const PACKET_KEYS=["schema","status","simulation_only","protocol_script_sha256","source_revision","audio_sha256_by_sample","reviews","external_identity_verified","external_consent_verified","human_signoff_verified","commercial_release_authorized","includes_audio"];
const REVIEW_KEYS=["sample_id","locale","reviewer_ref","audio_sha256","listening_attested","scores","critical_error_codes","remark_code"];
function exactKeys(obj,keys,code){
 a.ok(obj&&typeof obj==="object"&&!Array.isArray(obj),code);
 a.deepEqual(Object.keys(obj).sort(),keys.slice().sort(),code+"_EXTRA_OR_MISSING_KEYS");
}
function digestScripts(protocol){return crypto.createHash("sha256").update(JSON.stringify(protocol.samples)).digest("hex");}
function median(values){const s=values.slice().sort((x,y)=>x-y);const n=s.length;return n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2;}
function evaluateReview(packet,protocol){
 a.equal(protocol.schema,"honey.st3-native-listening-protocol.v1");
 a.equal(protocol.status,"PREPARED_NO_AUDIO_NO_HUMAN_REVIEW");
 a.equal(protocol.samples.length,8);
 exactKeys(packet,PACKET_KEYS,"PACKET");
 a.equal(packet.schema,"honey.st3-metadata-review-intake.v1");
 a.ok(["EMPTY_UNAUTHORIZED","SIMULATION_FIXTURE","REVIEW_SUBMITTED_UNVERIFIED"].includes(packet.status));
 a.equal(typeof packet.simulation_only,"boolean");
 a.equal(packet.protocol_script_sha256,digestScripts(protocol),"MISMATCHED_REVIEW_SCRIPT_HASH");
 a.equal(packet.source_revision,protocol.source.revision);
 for(const k of ["external_identity_verified","external_consent_verified","human_signoff_verified","commercial_release_authorized","includes_audio"]){
   a.equal(packet[k],false,"THIS_MODULE_CANNOT_VERIFY_OR_AUTHORIZE_"+k);
 }
 a.ok(Array.isArray(packet.reviews)&&packet.reviews.length<=24,"TOO_MANY_REVIEWS");
 const samples=protocol.samples,ids=samples.map(x=>x.id),expectedIds=new Set(ids);
 const hashes=packet.audio_sha256_by_sample;
 a.ok(hashes&&typeof hashes==="object"&&!Array.isArray(hashes),"INVALID_HASH_MAP");
 if(packet.status==="EMPTY_UNAUTHORIZED"){
   a.equal(packet.simulation_only,false);
   a.deepEqual(packet.reviews,[]);
   a.deepEqual(hashes,{});
   return {status:"BLOCKED_NO_AUDIO_OR_HUMAN_EVIDENCE",review_count:0,language_count:0,critical_errors:0,
     screening_candidate:false,human_listening_verified:false,commercial_release_authorized:false};
 }
 if(packet.status==="SIMULATION_FIXTURE")a.equal(packet.simulation_only,true);
 if(packet.status==="REVIEW_SUBMITTED_UNVERIFIED")a.equal(packet.simulation_only,false);
 a.deepEqual(Object.keys(hashes).sort(),ids.slice().sort(),"MISSING_OR_EXTRA_SAMPLE_HASH");
 const hashesSeen=new Set();
 for(const id of ids){
   a.match(hashes[id],/^[a-f0-9]{64}$/,"INVALID_AUDIO_DIGEST");
   a.ok(!hashesSeen.has(hashes[id]),"REUSED_AUDIO_ACROSS_DIFFERENT_SENTENCES");
   hashesSeen.add(hashes[id]);
 }
 const bySample=new Map(ids.map(id=>[id,[]]));
 const reviewersPerLanguage={vi:new Set(),ko:new Set()};
 const individualPairs=new Set();
 const ratersUsedFor=new Map();
 for(const review of packet.reviews){
   exactKeys(review,REVIEW_KEYS,"REVIEW");
   a.ok(expectedIds.has(review.sample_id),"UNKNOWN_SAMPLE_ID");
   const sample=samples.find(x=>x.id===review.sample_id);
   a.equal(review.locale,sample.locale,"LOCALE_DOES_NOT_MATCH_SCRIPT");
   a.match(review.reviewer_ref,/^[a-z0-9_-]{8,32}$/,"UNSAFE_REVIEWER_PSEUDONYM");
   a.ok(!review.reviewer_ref.includes("email")&&!review.reviewer_ref.includes("phone"),"IDENTITY_LEAK_RISK");
   a.equal(review.audio_sha256,hashes[review.sample_id],"REVIEW_AUDIO_SHA_MISMATCH");
   a.equal(review.listening_attested,true,"UNHEARD_SCORE");
   exactKeys(review.scores,FIELDS,"SCORES");
   for(const f of FIELDS){
     a.ok(Number.isInteger(review.scores[f])&&review.scores[f]>=1&&review.scores[f]<=5,"INVALID_SCORE_"+f);
   }
   a.ok(Array.isArray(review.critical_error_codes)&&review.critical_error_codes.length<=3,"CRITICAL_ERRORS_INVALID");
   for(const err of review.critical_error_codes)a.ok(["WRONG_PRODUCT","WRONG_DELIVERY","WRONG_ORDER_STATUS","UNINTELLIGIBLE_KEYWORD"].includes(err),"UNKNOWN_CRITICAL_ERROR");
   a.ok(["NONE","ACCENT","PACING","PHONEME","VOICE_QUALITY","OTHER"].includes(review.remark_code),"UNSAFE_FREE_TEXT");
   const pair=review.sample_id+":"+review.reviewer_ref;
   a.ok(!individualPairs.has(pair),"DUPLICATE_REVIEWER_FOR_SAMPLE");
   individualPairs.add(pair);
   const oldLang=ratersUsedFor.get(review.reviewer_ref);
   a.ok(!oldLang||oldLang===review.locale,"REVIEWER_CROSSOVER_LANGUAGE");
   ratersUsedFor.set(review.reviewer_ref,review.locale);
   reviewersPerLanguage[review.locale].add(review.reviewer_ref);
   bySample.get(review.sample_id).push(review);
 }
 if(packet.reviews.length===0){
   return {status:"BLOCKED_NO_REVIEW_ROWS",review_count:0,language_count:0,critical_errors:0,
     screening_candidate:false,human_listening_verified:false,commercial_release_authorized:false};
 }
 // Complete packets need two independently referenced reviewers for every sample. A
 // pseudonym alone does NOT prove real-world independence; external verification stays false.
 const incomplete=ids.some(id=>bySample.get(id).length<2);
 const critical=packet.reviews.reduce((sum,r)=>sum+r.critical_error_codes.length,0);
 let screeningCandidate=!incomplete,needAdjudication=false;
 const perSample=[];
 for(const id of ids){
   const reviews=bySample.get(id);
   if(!reviews.length){screeningCandidate=false;continue;}
   if(reviews.length>3)throw Error("EXCESSIVE_SCORES_FOR_SAMPLE");
   const medians={};
   for(const f of FIELDS){
     const scores=reviews.map(x=>x.scores[f]);
     medians[f]=median(scores);
     if(medians[f]<protocol.evaluation.draft_thresholds.per_dimension_median_min)screeningCandidate=false;
     if(Math.max(...scores)-Math.min(...scores)>=2)needAdjudication=true;
   }
   if(reviews.some(x=>x.scores.word_intelligibility<protocol.evaluation.draft_thresholds.per_sample_intelligibility_min))screeningCandidate=false;
   perSample.push({sample_id:id,review_count:reviews.length,medians});
 }
 if(reviewersPerLanguage.vi.size<2||reviewersPerLanguage.ko.size<2)screeningCandidate=false;
 if(critical>protocol.evaluation.draft_thresholds.critical_language_or_product_error_max)screeningCandidate=false;
 if(needAdjudication)screeningCandidate=false;
 const status=packet.simulation_only?"SYNTHETIC_ONLY_NEVER_HUMAN_PASS":
   (incomplete?"INCOMPLETE_PENDING_REAL_REVIEW":
    (screeningCandidate?"SCREENING_ELIGIBLE_NEEDS_EXTERNAL_ATTESTATION":"NEEDS_REPAIR_OR_ADJUDICATION"));
 return {status,review_count:packet.reviews.length,language_count:Number(reviewersPerLanguage.vi.size>0)+Number(reviewersPerLanguage.ko.size>0),
   critical_errors:critical,requires_adjudication:needAdjudication,screening_candidate:screeningCandidate,
   per_sample:perSample,
   human_listening_verified:false,commercial_release_authorized:false,
   note:"Only score structure and draft thresholds screened. No person/consent/source authenticity or audible provenance verified."};
}
if(require.main===module){
 const proto=JSON.parse(fs.readFileSync(path.join(__dirname,"listening_qa_protocol.json"),"utf8"));
 const pkt=JSON.parse(fs.readFileSync(path.join(__dirname,"listening_qa_scoring_intake_template.json"),"utf8"));
 console.log("ST3_SCORE_INTAKE_EMPTY_FAIL_CLOSED_PASS="+JSON.stringify(evaluateReview(pkt,proto)));
}
module.exports={evaluateReview,digestScripts};
