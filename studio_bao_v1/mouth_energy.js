"use strict";
/* Audio-energy puppet preview. Explicitly NOT phoneme lip-sync or a human likeness. */
const BaoMouthEnergy=(()=>{
 const HOP_MS=20,MAX_BINS=6000;
 const ascii=(d,o,n)=>Array.from({length:n},(_,i)=>String.fromCharCode(d.getUint8(o+i))).join("");
 function envelope(bytes){
  if(!(bytes instanceof ArrayBuffer)||bytes.byteLength<44||bytes.byteLength>8*1024*1024)
   throw Error("MOUTH_WAV_SIZE_INVALID");
  const d=new DataView(bytes);
  if(ascii(d,0,4)!=="RIFF"||ascii(d,8,4)!=="WAVE"||d.getUint32(4,true)+8!==bytes.byteLength)
   throw Error("MOUTH_WAV_RIFF_INVALID");
  let off=12,fmt=null,span=null;
  while(off+8<=bytes.byteLength){
   const tag=ascii(d,off,4),size=d.getUint32(off+4,true),start=off+8;
   if(size>bytes.byteLength-start)throw Error("MOUTH_WAV_CHUNK_TRUNCATED");
   if(tag==="fmt "){
    if(fmt||size<16)throw Error("MOUTH_FMT_INVALID");
    const format=d.getUint16(start,true),channels=d.getUint16(start+2,true),
    rate=d.getUint32(start+4,true),byteRate=d.getUint32(start+8,true),
    block=d.getUint16(start+12,true),bits=d.getUint16(start+14,true);
    if(format!==1||bits!==16||![1,2].includes(channels)||rate<8000||rate>48000||
       byteRate!==rate*channels*2||block!==channels*2)throw Error("MOUTH_WAV_PCM16_REQUIRED");
    fmt={channels,rate,block};
   }
   if(tag==="data"){
    if(span||size<=0)throw Error("MOUTH_DUPLICATE_OR_EMPTY_DATA");
    span={start,size};
   }
   off=start+size+(size%2);
  }
  if(off!==bytes.byteLength||!fmt||!span||span.size%fmt.block)
   throw Error("MOUTH_WAV_STRUCTURE_INVALID");
  const frames=span.size/fmt.block,durationMs=Math.round(frames/fmt.rate*1000);
  if(durationMs<600||durationMs>120000)throw Error("MOUTH_DURATION_BOUNDS");
  const hop=Math.max(1,Math.round(fmt.rate*HOP_MS/1000)),count=Math.ceil(frames/hop);
  if(count>MAX_BINS)throw Error("MOUTH_BIN_BOUNDS");
  const rms=[];
  for(let n=0;n<count;n++){
   let sum=0,num=0;
   for(let j=n*hop;j<Math.min(frames,(n+1)*hop);j++){
    let mono=0;
    for(let c=0;c<fmt.channels;c++)mono+=d.getInt16(span.start+(j*fmt.channels+c)*2,true)/32768;
    mono/=fmt.channels;sum+=mono*mono;num++;
   }
   rms.push(Math.sqrt(sum/num));
  }
  const peak=Math.max(...rms);
  const open=rms.map(v=>{
   if(peak<.012||v<.008)return 0;
   const normalized=Math.max(0,Math.min(1,(v-.008)/Math.max(.04,peak*.85)));
   return Math.round(normalized*1000)/1000;
  });
  return Object.freeze({hopMs:HOP_MS,durationMs,sampleRate:fmt.rate,frames,channels:fmt.channels,
    peakRms:+peak.toFixed(6),open:Object.freeze(open),method:"PCM_RMS_20MS_NOT_PHONEMES"});
 }
 function valueAt(env,ms){
  if(!env||!Number.isFinite(ms)||ms<0||ms>=env.durationMs)return 0;
  return env.open[Math.min(env.open.length-1,Math.floor(ms/env.hopMs))]||0;
 }
 return Object.freeze({envelope,valueAt,HOP_MS,MAX_BINS});
})();
if(typeof module!=="undefined"&&module.exports)module.exports=BaoMouthEnergy;
