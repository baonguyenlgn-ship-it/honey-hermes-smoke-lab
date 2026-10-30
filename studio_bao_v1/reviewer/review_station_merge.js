"use strict";
/* Offline reviewer contribution reconciliation. It NEVER establishes real human identity or rights. */
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),a=require("node:assert/strict");
const core=require("./review_station_core.js");
const protocol=require("./review_protocol_data.js");
const humanProtocol=require("../voice/listening_qa_protocol.json");
const {evaluateReview}=require("../voice/listening_score_gate.js");
const sampleDigest=crypto.createHash("sha256").update(JSON.stringify(protocol.samples)).digest("hex");
function reconcile(contributions,{simulation=false}={}){
 a.equal(contributions?.length,4,"EXACTLY_FOUR_CONTRIBUTIONS_TWO_PER_LANGUAGE");
 a.equal(typeof simulation,"boolean");
 const sampleMap=new Map(),reviewerRefs=new Set(),byLocale={vi:[],ko:[]};
 for(const contribution of contributions){
  core.validateContribution(contribution,{...protocol,script_sha256:sampleDigest});
  const ref=contribution.reviewer_ref;
  a.ok(!reviewerRefs.has(ref),"DUPLICATE_RATER_PSEUDONYM");reviewerRefs.add(ref);
  a.ok(ref.startsWith(contribution.locale+"_"),"REVIEWER_LOCALE_MISMATCH");
  byLocale[contribution.locale].push(contribution);
  for(const review of contribution.reviews){
   const prior=sampleMap.get(review.sample_id);
   if(prior)a.equal(prior,review.audio_sha256,"REVIEWERS_HEARD_DIFFERENT_BYTES_FOR_SAME_SAMPLE");
   sampleMap.set(review.sample_id,review.audio_sha256);
  }
 }
 a.equal(byLocale.vi.length,2,"VI_TWO_INDEPENDENT_REFERENCES_REQUIRED");
 a.equal(byLocale.ko.length,2,"KO_TWO_INDEPENDENT_REFERENCES_REQUIRED");
 a.equal(sampleMap.size,8,"ALL_EIGHT_SAMPLES_REQUIRED");
 a.equal(new Set(sampleMap.values()).size,8,"SAME_AUDIO_USED_FOR_DIFFERENT_SENTENCES");
 const packet={
  schema:"honey.st3-metadata-review-intake.v1",
  status:simulation?"SIMULATION_FIXTURE":"REVIEW_SUBMITTED_UNVERIFIED",
  simulation_only:simulation,
  protocol_script_sha256:sampleDigest,
  source_revision:protocol.model_revision,
  audio_sha256_by_sample:Object.fromEntries(protocol.samples.map(s=>[s.id,sampleMap.get(s.id)])),
  reviews:protocol.samples.flatMap(s=>contributions.filter(c=>c.locale===s.locale)
    .map(c=>c.reviews.find(x=>x.sample_id===s.id))),
  external_identity_verified:false,external_consent_verified:false,
  human_signoff_verified:false,commercial_release_authorized:false,includes_audio:false
 };
 const screening=evaluateReview(packet,humanProtocol);
 a.equal(screening.human_listening_verified,false);
 a.equal(screening.commercial_release_authorized,false);
 return {packet,screening,provenance:{
  schema:"honey.st3-local-reconciliation.v1",
  contribution_count:4,vi_reviewers:2,ko_reviewers:2,
  review_rows:16,matching_sample_hashes:8,
  true_human_qualification_or_consent_verified:false,
  actual_sample_origin_independently_verified:false,
  local_only:true,commercial_release_authorized:false,
  result:"STRUCTURALLY_RECONCILED_NOT_VERIFIED_HUMAN_EVIDENCE"}};
}
if(require.main===module){
 try{
  const args=process.argv.slice(2);
  const simulation=args[0]==="--simulation";
  const rest=simulation?args.slice(1):args;
  if(rest.length!==5)throw Error("USAGE: node review_station_merge.js [--simulation] four-input-review-JSON-files output-new-json-file");
  const inputs=rest.slice(0,4).map(f=>JSON.parse(fs.readFileSync(f,"utf8")));
  const merged=reconcile(inputs,{simulation});
  // Never overwrite an existing report or print reviewer identifiers/audio SHA in CI.
  fs.writeFileSync(rest[4],JSON.stringify(merged,null,2)+"\n",{encoding:"utf8",flag:"wx",mode:0o600});
  console.log("HONEY_OFFLINE_REVIEW_JOIN_SCREEN_ONLY="+JSON.stringify({
   contributions:4,reviews:16,scripts:8,screeningStatus:merged.screening.status,
   trueHumanAccepted:false,legalRelease:false}));
 }catch(e){console.error("REVIEW_JOIN_BLOCKED: "+String(e.message||e));process.exitCode=1;}
}
module.exports={reconcile,sampleDigest};
