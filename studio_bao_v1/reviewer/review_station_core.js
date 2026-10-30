"use strict";
/* Research-only review station core. No fetch, network, persistence, or identity collection. */
(function(root){
 const MAX_WAV=25*1024*1024;
 const DIMS=["word_intelligibility","pronunciation","prosody","naturalness","male_presenting_timbre"];
 const ERRORS=["WRONG_PRODUCT","WRONG_DELIVERY","WRONG_ORDER_STATUS","UNINTELLIGIBLE_KEYWORD"];
 const REMARKS=["NONE","ACCENT","PACING","PHONEME","VOICE_QUALITY","OTHER"];
 const SAFE_ID=/^[a-z0-9_-]{8,32}$/;
 const HEX=/^[a-f0-9]{64}$/;
 function assert(v,message){if(!v)throw Error(message);}
 function parseWav(b){
   assert(b instanceof ArrayBuffer,"WAV_ARRAYBUFFER_REQUIRED");
   assert(b.byteLength>=44 && b.byteLength<=MAX_WAV,"WAV_LENGTH_INVALID");
   const a=new DataView(b);
   function tag(i){return String.fromCharCode(...new Uint8Array(b,i,4));}
   assert(tag(0)==="RIFF"&&tag(8)==="WAVE","WAV_RIFF_REQUIRED");
   assert(a.getUint32(4,true)+8===b.byteLength,"WAV_RIFF_LENGTH_MISMATCH");
   let offset=12,fmt=null,data=0;
   while(offset+8<=b.byteLength){
     const name=tag(offset),size=a.getUint32(offset+4,true),start=offset+8;
     assert(size<=b.byteLength-start,"WAV_CHUNK_OVERFLOW");
     if(name==="fmt "){
       assert(size>=16,"WAV_FMT_SIZE");
       fmt={format:a.getUint16(start,true),channels:a.getUint16(start+2,true),
         rate:a.getUint32(start+4,true),bits:a.getUint16(start+14,true)};
     }
     if(name==="data")data+=size;
     offset=start+size+(size%2);
   }
   assert(fmt&&fmt.format===1&&fmt.channels===1&&fmt.bits===16,"WAV_PCM_MONO_16_REQUIRED");
   assert(fmt.rate===44100,"WAV_SAMPLE_RATE_MUST_44100");
   assert(data>fmt.rate*2/2&&data<fmt.rate*2*30,"WAV_DURATION_LIMIT");
   assert(data%2===0,"WAV_ODD_SAMPLE_BYTES");
   return {sample_rate:fmt.rate,duration_seconds:+(data/2/fmt.rate).toFixed(3),bytes:b.byteLength};
 }
 function safeReviewerId(x){return typeof x==="string"&&SAFE_ID.test(x)&&!/email|phone|owner|admin|bao|@/i.test(x);}
 function validateContribution(c,p){
   assert(c&&typeof c==="object"&&!Array.isArray(c),"REVIEW_INVALID");
   const keys=["schema","status","local_review_only","protocol_script_sha256","source_revision","reviewer_ref","locale","audio_sha256_by_sample","reviews","external_identity_verified","external_consent_verified","human_signoff_verified","commercial_release_authorized","includes_audio"];
   assert(JSON.stringify(Object.keys(c).sort())===JSON.stringify(keys.sort()),"REVIEW_SCHEMA_EXTRA_KEYS");
   assert(c.schema==="honey.st3-local-reviewer-contribution.v1","REVIEW_SCHEMA");
   assert(c.status==="LOCAL_SELF_ATTESTED_UNVERIFIED","REVIEW_CANNOT_BE_APPROVED");
   assert(c.local_review_only===true,"REVIEW_LOCAL_ONLY");
   assert(c.source_revision===p.model_revision,"REVIEW_MODEL_CHANGED");
   assert(c.protocol_script_sha256===p.script_sha256,"REVIEW_SCRIPT_HASH_CHANGED");
   assert(safeReviewerId(c.reviewer_ref),"REVIEWER_PSEUDONYM_INVALID");
   assert(["vi","ko"].includes(c.locale),"LOCALE_INVALID");
   for(const f of ["external_identity_verified","external_consent_verified","human_signoff_verified","commercial_release_authorized","includes_audio"])
     assert(c[f]===false,"FALSE_EXTERNAL_APPROVAL_"+f);
   const target=p.samples.filter(s=>s.locale===c.locale);
   assert(target.length===4&&c.reviews?.length===4,"FOUR_REVIEWS_REQUIRED");
   assert(c.audio_sha256_by_sample && Object.keys(c.audio_sha256_by_sample).length===4,"FOUR_HASHES_REQUIRED");
   for(let i=0;i<4;i++){
     const s=target[i],r=c.reviews[i];
     assert(r.sample_id===s.id&&r.locale===s.locale,"WRONG_ORDER_OR_LOCALE");
     assert(r.reviewer_ref===c.reviewer_ref,"REVIEWER_MISMATCH");
     assert(HEX.test(r.audio_sha256)&&r.audio_sha256===c.audio_sha256_by_sample[s.id],"FILE_HASH_NOT_BOUND");
     assert(r.listening_attested===true,"ACTUAL_LOCAL_LISTENING_ATTESTATION_MISSING");
     assert(r.scores&&Object.keys(r.scores).sort().join()===DIMS.slice().sort().join(),"SCORES_INCOMPLETE");
     for(const v of DIMS)assert(Number.isInteger(r.scores[v])&&r.scores[v]>=1&&r.scores[v]<=5,"INVALID_RATING");
     assert(Array.isArray(r.critical_error_codes)&&r.critical_error_codes.length<=3&&
       r.critical_error_codes.every(e=>ERRORS.includes(e)),"INVALID_CRITICAL_ERRORS");
     assert(REMARKS.includes(r.remark_code),"INVALID_REMARK");
     assert(Object.keys(r).sort().join()===["sample_id","locale","reviewer_ref","audio_sha256","listening_attested","scores","critical_error_codes","remark_code"].sort().join(),"REVIEW_EXTRA_KEYS");
   }
   assert(new Set(Object.values(c.audio_sha256_by_sample)).size===4,"REUSED_AUDIO_FILES");
   return {status:"LOCAL_SELF_ATTESTED_UNVERIFIED",samples:4,release:false};
 }
 function buildContribution({protocol,scriptHash,locale,reviewerRef,rows,sessionAttested}){
   assert(sessionAttested===true,"EXPLICIT_PRIVATE_SESSION_REQUIRED");
   assert(safeReviewerId(reviewerRef),"PSEUDONYM_INVALID");
   assert(protocol&&typeof scriptHash==="string"&&HEX.test(scriptHash),"PROTOCOL_PROVENANCE_MISSING");
   const chosen=protocol.samples.filter(s=>s.locale===locale);
   assert(chosen.length===4,"LANGUAGE_NOT_FOUND");
   const hashes={};
   const reviews=chosen.map(s=>{
     const row=rows[s.id];
     assert(row&&row.listened===true&&row.ended===true&&HEX.test(row.audioSha256),"LISTENED_WAV_REQUIRED_"+s.id);
     hashes[s.id]=row.audioSha256;
     return {sample_id:s.id,locale:s.locale,reviewer_ref:reviewerRef,audio_sha256:row.audioSha256,
       listening_attested:true,scores:Object.fromEntries(DIMS.map(d=>[d,Number(row.scores?.[d])])),
       critical_error_codes:row.errors||[],remark_code:row.remark||"NONE"};
   });
   const packet={schema:"honey.st3-local-reviewer-contribution.v1",
     status:"LOCAL_SELF_ATTESTED_UNVERIFIED",local_review_only:true,
     protocol_script_sha256:scriptHash,source_revision:protocol.model_revision,
     reviewer_ref:reviewerRef,locale,audio_sha256_by_sample:hashes,reviews,
     external_identity_verified:false,external_consent_verified:false,
     human_signoff_verified:false,commercial_release_authorized:false,includes_audio:false};
   validateContribution(packet,{...protocol,script_sha256:scriptHash});
   return packet;
 }
 const exports={MAX_WAV,DIMS,ERRORS,REMARKS,parseWav,safeReviewerId,validateContribution,buildContribution};
 if(typeof module!=="undefined"&&module.exports)module.exports=exports;
 root.HoneyReviewCore=exports;
})(typeof globalThis!=="undefined"?globalThis:this);
