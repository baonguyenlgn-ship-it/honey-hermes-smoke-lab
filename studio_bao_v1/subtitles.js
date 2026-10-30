"use strict";
/* DEV-only timed caption files. Estimates, NEVER calibrated to spoken audio/video. */
const BaoSubtitles = (() => {
 const DURATION_MS=Object.freeze([9000,11000,10000]);
 const LANGS=Object.freeze(["vi","ko","en","zh"]);
 const PRODUCTS=Object.freeze(["mango","coconut","pomelo"]);
 const FORMAT=Object.freeze(["srt","vtt"]);
 function clock(ms,format){
  if(!Number.isInteger(ms)||ms<0||ms>359999999)throw Error("BAD_TIMECODE_MS");
  const hh=String(Math.floor(ms/3600000)).padStart(2,"0");
  const mm=String(Math.floor(ms/60000)%60).padStart(2,"0");
  const ss=String(Math.floor(ms/1000)%60).padStart(2,"0");
  const ff=String(ms%1000).padStart(3,"0");
  return hh+":"+mm+":"+ss+(format==="srt"?",":".")+ff;
 }
 function buildCues(beats){
  if(!Array.isArray(beats)||beats.length!==3)throw Error("BAD_STORYBOARD_BEATS");
  let offset=0;
  const cues=beats.map((beat,i)=>{
   const t=beat?.subtitle;
   if(typeof t!=="string"||t.trim().length<5||t.length>160||/[\r\n]/.test(t)||t.includes("-->"))throw Error("UNSAFE_SUBTITLE_TEXT");
   const entry=Object.freeze({index:i+1,startMs:offset,endMs:offset+DURATION_MS[i],text:t.trim()});
   offset=entry.endMs;return entry;
  });
  if(cues.some((c,i)=>c.endMs<=c.startMs||(i>0&&c.startMs!==cues[i-1].endMs)))throw Error("TIMELINE_OVERLAP_OR_GAP");
  return Object.freeze(cues);
 }
 function render(cues,format){
  if(!FORMAT.includes(format))throw Error("BAD_SUBTITLE_FORMAT");
  const body=cues.map(c=>[
   ...(format==="srt"?[String(c.index)]:[]),
   clock(c.startMs,format)+" --> "+clock(c.endMs,format),
   c.text
  ].join("\n")).join("\n\n");
  return (format==="vtt"?"WEBVTT\n\n":"")+body+"\n";
 }
 function createExport({beats,language,product,format}){
  if(!LANGS.includes(language)||!PRODUCTS.includes(product)||!FORMAT.includes(format))throw Error("BAD_EXPORT_SCOPE");
  const cues=buildCues(beats);
  return Object.freeze({
   filename:"honey-bao-v1-"+product+"-"+language+"-demo."+format,
   mime:format==="vtt"?"text/vtt;charset=utf-8":"application/x-subrip;charset=utf-8",
   text:render(cues,format),cues,estimatedTotalMs:cues[cues.length-1].endMs,
   disclaimer:"DEMO_ESTIMATED_TIME_NOT_AUDIO_SYNC"
  });
 }
 return Object.freeze({DURATION_MS,LANGS,PRODUCTS,clock,buildCues,render,createExport});
})();
if(typeof module!=="undefined"&&module.exports)module.exports=BaoSubtitles;
