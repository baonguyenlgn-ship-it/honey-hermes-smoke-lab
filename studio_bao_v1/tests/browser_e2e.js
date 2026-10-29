"use strict";
/* Native Chrome/DevTools Protocol E2E: zero npm installs, no inference, no real orders. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {spawn} = require("node:child_process");
const {pathToFileURL} = require("node:url");
const {createHash} = require("node:crypto");

const here = path.resolve(__dirname,"..");
const pageUrl = pathToFileURL(path.join(here,"index.html")).href;
const screenshots = path.resolve(process.env.RUNNER_TEMP||os.tmpdir(),"honey-studio-bao-v1");
const sleep = ms=>new Promise(resolve=>setTimeout(resolve,ms));
const candidates = [
 process.env.CHROME_PATH,
 path.join(process.env.PROGRAMFILES||"C:\\Program Files","Google","Chrome","Application","chrome.exe"),
 path.join(process.env["PROGRAMFILES(X86)"]||"C:\\Program Files (x86)","Google","Chrome","Application","chrome.exe"),
 path.join(process.env.PROGRAMFILES||"C:\\Program Files","Microsoft","Edge","Application","msedge.exe")
].filter(Boolean);
const browser = candidates.find(p=>fs.existsSync(p));
if(!browser)throw new Error("BROWSER_NOT_FOUND_ON_WINDOWS_RUNNER");
fs.mkdirSync(screenshots,{recursive:true});
const profile = fs.mkdtempSync(path.join(os.tmpdir(),"honey-studio-cdp-"));
let processHandle,ws;
async function main(){
 const outbound = [],errors = [];
 const args = [
  "--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
  "--no-proxy-server","--disable-background-networking","--disable-extensions",
  "--remote-debugging-port=0","--user-data-dir="+profile,
  pageUrl
 ];
 processHandle=spawn(browser,args,{stdio:"ignore",windowsHide:true});
 let port;
 for(let i=0;i<120;i++){
  if(processHandle.exitCode!==null)throw new Error("BROWSER_EXIT_"+processHandle.exitCode);
  const f=path.join(profile,"DevToolsActivePort");
  if(fs.existsSync(f)){
   const n=Number(fs.readFileSync(f,"utf8").split(String.fromCharCode(10))[0]);
   if(Number.isInteger(n)&&n>0){port=n;break;}
  }
  await sleep(250);
 }
 assert.ok(port,"CHROME_DEVTOOLS_PORT_TIMEOUT");
 let targets;
 for(let i=0;i<40;i++){
  try{
   const r=await fetch("http://127.0.0.1:"+port+"/json/list");
   if(r.ok){
    targets=await r.json();
    if(targets.find(t=>t.type==="page"&&t.webSocketDebuggerUrl))break;
   }
  }catch{}
  await sleep(250);
 }
 const target=targets?.find(t=>t.type==="page"&&t.url.startsWith("file:"))||targets?.find(t=>t.type==="page");
 assert.ok(target?.webSocketDebuggerUrl,"NO_CDP_PAGE_TARGET");
 ws=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{
  const timeout=setTimeout(()=>reject(new Error("CDP_CONNECT_TIMEOUT")),12000);
  ws.addEventListener("open",()=>{clearTimeout(timeout);resolve()},{once:true});
  ws.addEventListener("error",()=>{clearTimeout(timeout);reject(new Error("CDP_CONNECT_ERROR"))},{once:true});
 });
 let id=0;const pending=new Map();
 ws.addEventListener("message",event=>{
  const data=JSON.parse(String(event.data));
  if(data.id&&pending.has(data.id)){
   const p=pending.get(data.id);pending.delete(data.id);
   if(data.error)p.reject(new Error(data.error.message));else p.resolve(data.result);
  }
  if(data.method==="Network.requestWillBeSent"){
   const url=data.params?.request?.url||"";
   if(!/^(file:|data:|about:|devtools:)/i.test(url))outbound.push(url);
  }
  if(data.method==="Runtime.exceptionThrown")errors.push(data.params?.exceptionDetails?.text||"JavaScript exception");
 });
 const send=(method,params={})=>new Promise((resolve,reject)=>{
  const key=++id;pending.set(key,{resolve,reject});
  ws.send(JSON.stringify({id:key,method,params}));
 });
 const evaluate=async expression=>{
  const r=await send("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails)throw new Error("BROWSER_JAVASCRIPT_EXCEPTION: "+JSON.stringify(r.exceptionDetails));
  return r.result.value;
 };
 const until=async(expression,expected=true)=>{
  for(let i=0;i<60;i++){
   const r=await evaluate(expression);
   if(r===expected)return r;
   await sleep(100);
  }
  throw new Error("BROWSER_WAIT_FAILED: "+expression);
 };
 const shot=async name=>{
  const r=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});
  const b=Buffer.from(r.data,"base64");
  fs.writeFileSync(path.join(screenshots,name+".png"),b);
  return {name,bytes:b.length,sha256:createHash("sha256").update(b).digest("hex")};
 };
 await send("Page.enable");
 await send("Runtime.enable");
 await send("Network.enable");
 await send("Emulation.setDeviceMetricsOverride",{width:1440,height:900,deviceScaleFactor:1,mobile:false});
 await send("Page.navigate",{url:pageUrl});
 await until("document.readyState === 'complete'");
 await until("document.getElementById('play-btn')?.getAttribute('aria-pressed') === 'false'");
 assert.equal(await evaluate("document.title.includes('Bảo V1')"),true);
 const desktop=await evaluate("({viewport:document.documentElement.clientWidth,content:document.documentElement.scrollWidth,stage:document.querySelector('.stage-canvas').getBoundingClientRect().width,products:document.querySelectorAll('[data-product]').length})");
 assert.ok(desktop.content<=desktop.viewport+1,"DESKTOP_HORIZONTAL_OVERFLOW: "+JSON.stringify(desktop));
 assert.equal(desktop.products,3);
 const desktopScreenshot=await shot("desktop-1440");
 const downloads=path.join(screenshots,"downloads");
 fs.mkdirSync(downloads,{recursive:true});
 await send("Browser.setDownloadBehavior",{behavior:"allow",downloadPath:downloads,eventsEnabled:true});
 const waitDownload=async name=>{
  const outputPath=path.join(downloads,name);
  for(let n=0;n<100;n++){
   if(fs.existsSync(outputPath)&&fs.statSync(outputPath).size>20)return fs.readFileSync(outputPath,"utf8");
   await sleep(100);
  }
  throw new Error("BROWSER_CAPTION_DOWNLOAD_MISSING: "+name);
 };
 await evaluate("document.getElementById('export-srt-btn').click();true");
 const srtData=await waitDownload("honey-bao-v1-mango-vi-demo.srt");
 assert.match(srtData,/^1\n00:00:00,000 --> 00:00:09,000/);
 assert.match(srtData,/\n\n3\n00:00:20,000 --> 00:00:30,000/);
 await evaluate("document.getElementById('export-vtt-btn').click();true");
 const vttData=await waitDownload("honey-bao-v1-mango-vi-demo.vtt");
 assert.match(vttData,/^WEBVTT\n\n00:00:00.000 --> 00:00:09.000/);
 assert.ok(!vttData.includes("http:"));
 console.log("BROWSER_LOCAL_CAPTION_DOWNLOADS=SRT_VTT_PASS");

 /* Supply 1-second synthetic silent PCM WAV + exact JSON cues entirely inside Chrome. */
 const pcm=Buffer.alloc(44+16000);
 pcm.write("RIFF",0);pcm.writeUInt32LE(pcm.length-8,4);pcm.write("WAVE",8);
 pcm.write("fmt ",12);pcm.writeUInt32LE(16,16);pcm.writeUInt16LE(1,20);
 pcm.writeUInt16LE(1,22);pcm.writeUInt32LE(8000,24);pcm.writeUInt32LE(16000,28);
 pcm.writeUInt16LE(2,32);pcm.writeUInt16LE(16,34);pcm.write("data",36);pcm.writeUInt32LE(16000,40);
 const sha=createHash("sha256").update(pcm).digest("hex");
 const captionsForWav=await evaluate("STORYBOARD.vi.mango.map(x=>x.subtitle)");
 const manifest={version:1,method:"manual_unverified_alignment",language:"vi",product:"mango",
  sha256:sha,durationMs:1000,cues:[
    {startMs:0,endMs:300,text:captionsForWav[0]},
    {startMs:300,endMs:700,text:captionsForWav[1]},
    {startMs:700,endMs:1000,text:captionsForWav[2]}
  ]};
 async function installSyntheticFiles(localManifest){
  const expression="(()=>{"
   +"const wavBinary=atob("+JSON.stringify(pcm.toString("base64"))+");"
   +"const wav=Uint8Array.from(wavBinary,c=>c.charCodeAt(0));"
   +"const w=new DataTransfer();w.items.add(new File([wav],'test-silent.wav',{type:'audio/wav'}));"
   +"const j=new DataTransfer();j.items.add(new File(["+JSON.stringify(JSON.stringify(localManifest))+"],'manual.json',{type:'application/json'}));"
   +"document.getElementById('audio-wav-input').files=w.files;"
   +"document.getElementById('audio-json-input').files=j.files;return true;})()";
  assert.equal(await evaluate(expression),true);
 }
 assert.equal(await evaluate("!!globalThis.crypto && !!globalThis.crypto.subtle"),true,
  "CHROME_FILE_ORIGIN_WEBCRYPTO_NOT_AVAILABLE");
 await installSyntheticFiles(manifest);
 await evaluate("document.getElementById('verify-audio-btn').click();true");
 await until("document.getElementById('audio-verify-status').textContent.includes('SHA-256')");
 assert.equal(await evaluate("document.getElementById('local-audio-player').hidden"),false);
 await until("document.getElementById('local-audio-player').readyState >= 1");
 assert.equal(await evaluate("document.getElementById('local-audio-player').src.startsWith('blob:')"),true);
 await evaluate("(()=>{const a=document.getElementById('local-audio-player');a.currentTime=0.45;a.dispatchEvent(new Event('timeupdate'));return true})()");
 await until("document.getElementById('local-audio-caption').textContent.includes('Xoài:')");
 await evaluate("(()=>{const a=document.getElementById('local-audio-player');a.currentTime=0.81;a.dispatchEvent(new Event('timeupdate'));return true})()");
 await until("document.getElementById('local-audio-caption').textContent.includes('택배')");
 await evaluate("document.getElementById('export-vtt-btn').click();true");
 const wavBoundVtt=await waitDownload("honey-bao-v1-mango-vi-wav-matched-manual-not-synced.vtt");
 assert.match(wavBoundVtt,/00:00:00.700 --> 00:00:01.000/);
 await installSyntheticFiles({...manifest,sha256:"0".repeat(64)});
 await evaluate("document.getElementById('verify-audio-btn').click();true");
 await until("document.getElementById('audio-verify-status').textContent.includes('WAV_SHA_MISMATCH')");
 assert.equal(await evaluate("document.getElementById('local-audio-player').hidden"),true);
 assert.equal(await evaluate("document.getElementById('local-audio-player').hasAttribute('src')"),false);
 assert.equal(await evaluate("document.getElementById('local-audio-caption').textContent"),"—");
 await evaluate("document.getElementById('export-srt-btn').click();true");
 const revertedSrt=await waitDownload("honey-bao-v1-mango-vi-demo.srt");
 assert.match(revertedSrt,/00:00:20,000 --> 00:00:30,000/);
 console.log("BROWSER_LOCAL_AUDIO_WAV_PLAYER_SEEK_CAPTIONS_AND_INVALID_SHA_CLEANUP_PASS_SYNTHETIC_SILENCE");

 await evaluate("(()=>{let s=document.getElementById('lang');s.value='ko';s.dispatchEvent(new Event('change',{bubbles:true}));return true})()");
 assert.equal(await evaluate("document.getElementById('script-content').textContent.includes('망고')"),true);
 assert.equal(await evaluate("document.getElementById('stage-heading').textContent"),"디지털 진행자");
 assert.equal(await evaluate("document.getElementById('comments-heading').textContent"),"댓글 시뮬레이터");
 await evaluate("document.getElementById('play-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('subtitle').textContent.includes('망고')"),true);
 assert.equal(await evaluate("document.getElementById('scene-counter').textContent"),"01 / 03");
 assert.equal(await evaluate("document.getElementById('next-scene-btn').disabled"),false);
 await evaluate("document.getElementById('next-scene-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('scene-counter').textContent"),"02 / 03");
 assert.equal(await evaluate("document.getElementById('subtitle').textContent.includes('품종')"),true);
 await evaluate("document.getElementById('next-scene-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('scene-counter').textContent"),"03 / 03");
 assert.equal(await evaluate("document.getElementById('next-scene-btn').disabled"),true);
 assert.equal(await evaluate("document.getElementById('subtitle').textContent.includes('택배')"),true);
 await evaluate("document.getElementById('prev-scene-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('scene-counter').textContent"),"02 / 03");
 assert.equal(await evaluate("document.getElementById('play-btn').getAttribute('aria-pressed')"),"true");
 await evaluate("document.querySelector('[data-product=coconut]').click(); true");
 assert.equal(await evaluate("document.getElementById('scene-counter').textContent"),"01 / 03");
 assert.equal(await evaluate("document.getElementById('script-content').textContent.includes('코코넛')"),true);
 assert.equal(await evaluate("document.getElementById('subtitle').textContent.includes('코코넛')"),true);
 await evaluate("document.getElementById('reply-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('reply-content').textContent.includes('DEMO')"),true);
 await evaluate("document.getElementById('draft-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('draft-count').textContent"),"1");
 await evaluate("document.getElementById('reset-btn').click(); true");
 assert.equal(await evaluate("document.getElementById('draft-count').textContent"),"0");
 assert.equal(await evaluate("document.documentElement.lang"),"ko");
 const mobileSizes=[];
 for(const width of [390,320]){
  await send("Emulation.setDeviceMetricsOverride",{width,height:844,deviceScaleFactor:1,mobile:true});
  await send("Page.reload",{ignoreCache:true});
  await until("document.readyState === 'complete'");
  await until("document.getElementById('play-btn')?.getAttribute('aria-pressed') === 'false'");
  const x=await evaluate("({viewport:document.documentElement.clientWidth,content:document.documentElement.scrollWidth,stage:document.querySelector('.stage-canvas').getBoundingClientRect().width})");
  assert.ok(x.content<=x.viewport+1,"MOBILE_HORIZONTAL_OVERFLOW_"+width+": "+JSON.stringify(x));
  const visual=await evaluate("(()=>{const rail=document.querySelector('.rail');const btn=document.getElementById('play-btn');const heading=document.getElementById('stage-heading');return {rail:getComputedStyle(rail).display,buttonWhiteSpace:getComputedStyle(btn).whiteSpace,buttonHeight:btn.getBoundingClientRect().height,headingHeight:heading.getBoundingClientRect().height}})()");
  assert.equal(visual.rail,"none","DECORATIVE_MOBILE_RAIL_STILL_VISIBLE_"+width);
  assert.equal(visual.buttonWhiteSpace,"nowrap","MOBILE_PRIMARY_ACTION_WRAPS_"+width);
  assert.ok(visual.buttonHeight<=55,"MOBILE_PRIMARY_ACTION_TOO_TALL_"+width+": "+JSON.stringify(visual));
  assert.ok(visual.headingHeight<=30,"MOBILE_STAGE_HEADING_WRAPS_"+width+": "+JSON.stringify(visual));
  mobileSizes.push({width,...x,visual});
  if(width===390)await shot("mobile-390");
 }
 assert.deepEqual(outbound,[],"UNEXPECTED_EXTERNAL_REQUESTS");
 assert.deepEqual(errors,[],"BROWSER_RUNTIME_EXCEPTION");
 console.log("BROWSER_CHROME_PATH="+browser);
 console.log("BROWSER_DESKTOP="+JSON.stringify(desktop));
 console.log("BROWSER_MOBILE="+JSON.stringify(mobileSizes));
 console.log("BROWSER_DESKTOP_SCREENSHOT="+JSON.stringify(desktopScreenshot));
 console.log("BROWSER_REAL_INTERACTIONS=local-WAV-JSON-synthetic-sha-guard,local-SRT-VTT-downloads,ko-language,storyboard-3-beats,prev-next-limits,play,pause-reset,product-switch,mock-reply,mock-draft");
 console.log("BROWSER_NETWORK=NO_EXTERNAL_REQUESTS");
 console.log("STUDIO_BROWSER_WINDOWS_PASS");
}
main().catch(e=>{console.error("STUDIO_BROWSER_WINDOWS_FAIL:",e.stack||e);process.exitCode=1}).finally(async()=>{
 try{ws?.close()}catch{}
 try{processHandle?.kill()}catch{}
 try{await sleep(350);fs.rmSync(profile,{recursive:true,force:true,maxRetries:3,retryDelay:300})}catch{}
});
