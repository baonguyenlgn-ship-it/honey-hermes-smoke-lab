"use strict";
/* Strict synthetic/manual viseme timing contract. Never infers phonemes or validates speech. */
const BaoVisemeTiming=(()=>{
 const ALLOWED=Object.freeze(["REST","BMP","AA","EE","OO","FV","L"]);
 const MAX_SEGMENTS=256;
 const fields=x=>Object.keys(x||{}).sort().join(",");
 const keyed=(x,names)=>x&&typeof x==="object"&&!Array.isArray(x)&&fields(x)===names.slice().sort().join(",");
 function verify({track,verifiedAudio}){
  if(!keyed(track,["version","method","provenance","language","product","audioSha256","durationMs","segments"]))
   throw Error("VISEME_MANIFEST_FIELDS_INVALID");
  if(track.version!==1||track.method!=="manual_viseme_cues_unverified"||
    !["synthetic_dev_fixture","manually_annotated_not_audited"].includes(track.provenance))
   throw Error("VISEME_PROVENANCE_UNVERIFIED_REQUIRED");
  if(!verifiedAudio||verifiedAudio.integrity!=="WAV_SHA256_MATCHED"||
    verifiedAudio.alignment!=="MANUAL_NOT_VERIFIED_WITH_SPEECH"||verifiedAudio.rights!=="NOT_VERIFIED")
   throw Error("VISEME_NEEDS_EXISTING_VERIFIED_WAV");
  if(!["vi","ko","en","zh"].includes(track.language)||!["mango","coconut","pomelo"].includes(track.product)||
    track.language!==verifiedAudio.language||track.product!==verifiedAudio.product)
   throw Error("VISEME_SCOPE_MISMATCH");
  if(typeof track.audioSha256!=="string"||!(/^[a-f0-9]{64}$/.test(track.audioSha256))||
    track.audioSha256!==verifiedAudio.audioSha256)
   throw Error("VISEME_AUDIO_HASH_MISMATCH");
  if(!Number.isInteger(track.durationMs)||track.durationMs!==verifiedAudio.audio.durationMs||
    track.durationMs<600||track.durationMs>120000)
   throw Error("VISEME_WAV_DURATION_MISMATCH");
  if(!Array.isArray(track.segments)||track.segments.length<2||track.segments.length>MAX_SEGMENTS)
   throw Error("VISEME_SEGMENT_COUNT_INVALID");
  let previous=0;
  const normalized=track.segments.map((seg,i)=>{
   if(!keyed(seg,["startMs","endMs","shape"]))throw Error("VISEME_SEGMENT_FIELDS_INVALID");
   if(!Number.isInteger(seg.startMs)||!Number.isInteger(seg.endMs)||
     seg.startMs!==previous||seg.endMs<=seg.startMs||seg.endMs-seg.startMs<30||
     seg.endMs>track.durationMs)throw Error("VISEME_SEGMENT_GAP_OVERLAP_OR_SHORT");
   if(!ALLOWED.includes(seg.shape))throw Error("VISEME_SHAPE_UNKNOWN");
   if(i===0&&seg.shape!=="REST")throw Error("VISEME_MUST_START_CLOSED");
   previous=seg.endMs;
   return Object.freeze({startMs:seg.startMs,endMs:seg.endMs,shape:seg.shape});
  });
  if(previous!==track.durationMs||normalized[normalized.length-1].shape!=="REST")
   throw Error("VISEME_MUST_END_CLOSED_AT_WAV_BOUNDARY");
  return Object.freeze({method:"MANUAL_VISEME_TIMELINE_UNVERIFIED",provenance:track.provenance,
    language:track.language,product:track.product,audioSha256:track.audioSha256,
    durationMs:track.durationMs,segments:Object.freeze(normalized),
    actualPhonemeAlignment:false,actualLipSync:false,commercialApproved:false});
 }
 function shapeAt(timeline,timeMs){
  if(!timeline||!Number.isFinite(timeMs)||timeMs<0||timeMs>=timeline.durationMs)return "REST";
  const segments=timeline.segments;
  let left=0,right=segments.length-1;
  while(left<=right){
   const mid=(left+right)>>1,s=segments[mid];
   if(timeMs<s.startMs)right=mid-1;
   else if(timeMs>=s.endMs)left=mid+1;
   else return s.shape;
  }
  return "REST";
 }
 return Object.freeze({ALLOWED,MAX_SEGMENTS,verify,shapeAt});
})();
if(typeof module!=="undefined"&&module.exports)module.exports=BaoVisemeTiming;
