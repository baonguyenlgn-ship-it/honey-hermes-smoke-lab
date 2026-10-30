"use strict";
/* Read-only WAV byte and manual timecode contract. NO proof of speech alignment. */
const BaoAudioTiming = (() => {
 const MAX_WAV_BYTES=8*1024*1024;
 const LANGS=Object.freeze(["vi","ko","en","zh"]);
 const PRODUCTS=Object.freeze(["mango","coconut","pomelo"]);
 const ascii=(d,offset,n)=>Array.from({length:n},(_,i)=>String.fromCharCode(d.getUint8(offset+i))).join("");
 function parseWav(bytes){
  if(!(bytes instanceof ArrayBuffer)||bytes.byteLength<44||bytes.byteLength>MAX_WAV_BYTES)throw Error("WAV_SIZE_INVALID");
  const d=new DataView(bytes);
  if(ascii(d,0,4)!=="RIFF"||ascii(d,8,4)!=="WAVE"||d.getUint32(4,true)+8!==bytes.byteLength)throw Error("WAV_RIFF_INVALID");
  let off=12,fmt=null,dataLength=null;
  while(off+8<=bytes.byteLength){
   const name=ascii(d,off,4),length=d.getUint32(off+4,true),start=off+8;
   if(length>bytes.byteLength-start)throw Error("WAV_TRUNCATED");
   if(name==="fmt "){
    if(fmt||length<16)throw Error("WAV_FMT_INVALID");
    const compression=d.getUint16(start,true),channels=d.getUint16(start+2,true);
    const rate=d.getUint32(start+4,true),byteRate=d.getUint32(start+8,true);
    const blockAlign=d.getUint16(start+12,true),bits=d.getUint16(start+14,true);
    if(compression!==1||bits!==16||![1,2].includes(channels)||rate<8000||rate>48000||
       blockAlign!==channels*2||byteRate!==rate*blockAlign)throw Error("WAV_PCM16_REQUIRED");
    fmt={sampleRate:rate,channels,blockAlign};
   }
   if(name==="data"){
    if(dataLength!==null||length===0)throw Error("WAV_DATA_INVALID");
    dataLength=length;
   }
   off=start+length+(length%2);
  }
  if(!fmt||dataLength===null||dataLength%fmt.blockAlign!==0||off!==bytes.byteLength)throw Error("WAV_STRUCTURE_INVALID");
  const sampleCount=dataLength/fmt.blockAlign,durationMs=Math.round(sampleCount*1000/fmt.sampleRate);
  if(durationMs<600||durationMs>120000)throw Error("WAV_DURATION_BOUNDS");
  return Object.freeze({sampleRate:fmt.sampleRate,channels:fmt.channels,sampleCount,durationMs});
 }
 async function hashBytes(bytes){
  if(!globalThis.crypto?.subtle)throw Error("WEB_CRYPTO_UNAVAILABLE");
  const digest=await globalThis.crypto.subtle.digest("SHA-256",bytes);
  return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");
 }
 async function verify({wavBytes,manifest,language,product,beats}){
  if(!LANGS.includes(language)||!PRODUCTS.includes(product)||!Array.isArray(beats)||beats.length!==3)throw Error("TIMING_SCOPE_INVALID");
  if(!manifest||typeof manifest!=="object"||Array.isArray(manifest)||
    manifest.version!==1||manifest.method!=="manual_unverified_alignment"||
    manifest.language!==language||manifest.product!==product)throw Error("MANIFEST_SCOPE_INVALID");
  if(Object.keys(manifest).sort().join(",")!=="cues,durationMs,language,method,product,sha256,version")throw Error("MANIFEST_EXTRA_FIELDS");
  if(typeof manifest.sha256!=="string"||!/^[a-f0-9]{64}$/.test(manifest.sha256))throw Error("MANIFEST_SHA_INVALID");
  const audio=parseWav(wavBytes);
  if(manifest.durationMs!==audio.durationMs)throw Error("MANIFEST_DURATION_MISMATCH");
  if(await hashBytes(wavBytes)!==manifest.sha256)throw Error("WAV_SHA_MISMATCH");
  if(!Array.isArray(manifest.cues)||manifest.cues.length!==3)throw Error("TIMING_COUNT_INVALID");
  let next=0;
  const cues=manifest.cues.map((cue,index)=>{
   if(!cue||typeof cue!=="object"||Object.keys(cue).sort().join(",")!=="endMs,startMs,text"||
      !Number.isInteger(cue.startMs)||!Number.isInteger(cue.endMs)||
      cue.startMs!==next||cue.endMs>audio.durationMs||cue.endMs-cue.startMs<250)
    throw Error("TIMING_GAP_OVERLAP_OR_BOUNDS");
   if(cue.text!==beats[index].subtitle||/[\r\n]/.test(cue.text)||cue.text.includes("-->"))
    throw Error("TIMING_TEXT_MISMATCH");
   next=cue.endMs;
   return Object.freeze({index:index+1,startMs:cue.startMs,endMs:cue.endMs,text:cue.text});
  });
  if(next!==audio.durationMs)throw Error("TIMING_INCOMPLETE");
  return Object.freeze({language,product,audioSha256:manifest.sha256,audio,cues:Object.freeze(cues),
   integrity:"WAV_SHA256_MATCHED",alignment:"MANUAL_NOT_VERIFIED_WITH_SPEECH",rights:"NOT_VERIFIED"});
 }
 return Object.freeze({MAX_WAV_BYTES,LANGS,PRODUCTS,parseWav,hashBytes,verify});
})();
if(typeof module!=="undefined"&&module.exports)module.exports=BaoAudioTiming;
