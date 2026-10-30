"use strict";
/* Real Chrome UI test on Windows: synthetic PCM fixture only, no model or real reviewer. */
const a=require("node:assert/strict"),fs=require("node:fs"),os=require("node:os"),
 path=require("node:path"),{spawn}=require("node:child_process"),{pathToFileURL}=require("node:url");
const core=require("../reviewer/review_station_core.js"),p=require("../reviewer/review_protocol_data.js");
const url=pathToFileURL(path.resolve(__dirname,"../reviewer/review_station.html")).href;
const candidates=[process.env.CHROME_PATH,path.join(process.env.PROGRAMFILES||"C:\\Program Files","Google","Chrome","Application","chrome.exe"),
path.join(process.env.PROGRAMFILES||"C:\\Program Files","Microsoft","Edge","Application","msedge.exe")].filter(Boolean);
const exe=candidates.find(fs.existsSync);if(!exe)throw Error("WINDOWS_CHROME_MISSING");
const sleep=n=>new Promise(r=>setTimeout(r,n));
const profile=fs.mkdtempSync(path.join(os.tmpdir(),"honey-review-cdp-"));
const downloads=fs.mkdtempSync(path.join(os.tmpdir(),"honey-review-download-"));
let browser,ws;
async function main(){
 browser=spawn(exe,["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
  "--no-proxy-server","--disable-background-networking","--disable-extensions",
  "--remote-debugging-port=0","--user-data-dir="+profile,url],{stdio:"ignore",windowsHide:true});
 let port=0;
 for(let i=0;i<120;i++){
  if(browser.exitCode!==null)throw Error("BROWSER_EXIT_"+browser.exitCode);
  const f=path.join(profile,"DevToolsActivePort");
  if(fs.existsSync(f)){port=Number(fs.readFileSync(f,"utf8").split("\n")[0]);if(port>0)break;}
  await sleep(200);
 }
 a.ok(port,"CHROME_DEVTOOLS_TIMEOUT");
 let targets;
 for(let i=0;i<45;i++){
  try{const r=await fetch("http://127.0.0.1:"+port+"/json/list");if(r.ok){targets=await r.json();if(targets.some(t=>t.type==="page"))break;}}catch{}
  await sleep(150);
 }
 const target=targets?.find(t=>t.type==="page"&&t.url.startsWith("file:"))||targets?.find(t=>t.type==="page");
 a.ok(target?.webSocketDebuggerUrl);
 ws=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(Error("CDP_TIMEOUT")),12000);
  ws.addEventListener("open",()=>{clearTimeout(timer);resolve();},{once:true});
  ws.addEventListener("error",()=>reject(Error("CDP_ERROR")),{once:true});
 });
 let seq=0;const pending=new Map(),outbound=[],errors=[];
 ws.addEventListener("message",event=>{
  const d=JSON.parse(String(event.data));
  if(d.id&&pending.has(d.id)){const x=pending.get(d.id);pending.delete(d.id);d.error?x.reject(Error(d.error.message)):x.resolve(d.result);}
  if(d.method==="Network.requestWillBeSent"){
   const u=d.params?.request?.url||"";
   if(/^https?:/i.test(u)&&!/^http:\/\/127\.0\.0\.1:/i.test(u))outbound.push(u);
  }
  if(d.method==="Runtime.exceptionThrown")errors.push(d.params?.exceptionDetails?.text||"JS_EXCEPTION");
 });
 const cmd=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
 const ev=async exp=>{
  const r=await cmd("Runtime.evaluate",{expression:exp,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails)throw Error("BROWSER_JS_EXCEPTION: "+JSON.stringify(r.exceptionDetails));
  return r.result.value;
 };
 const until=async(exp,want=true)=>{
  for(let i=0;i<100;i++){if(await ev(exp)===want)return;await sleep(100);}
  throw Error("BROWSER_POLL_TIMEOUT "+exp);
 };
 await cmd("Page.enable");await cmd("Runtime.enable");await cmd("Network.enable");
 await cmd("Page.navigate",{url});await until("window.HoneyReviewStationReady===true");
 a.equal(await ev("document.getElementById('export').disabled"),true);
 a.equal(await ev("document.querySelectorAll('input[type=file]:disabled').length"),4);
 await cmd("Browser.setDownloadBehavior",{behavior:"allow",downloadPath:downloads,eventsEnabled:true});
 await ev("document.getElementById('session-authorized').click()");
 await until("document.getElementById('locale').disabled===false");
 for(const lang of ["vi","ko"]){
  const change="(()=>{const l=document.getElementById('locale');l.value='"+lang+"';l.dispatchEvent(new Event('change'));const r=document.getElementById('reviewer');r.value='"+lang+"_reviewer01';r.dispatchEvent(new Event('input'));return true;})()";
  await ev(change);
  a.equal(await ev("document.getElementById('export').disabled"),true);
  for(let i=0;i<4;i++){
   const inject="(()=>{const input=document.querySelectorAll('.card input[type=file]')["+i+"];const rate=44100,n=Math.floor(rate*1.4),b=new ArrayBuffer(44+n*2),v=new DataView(b),u=new Uint8Array(b);function str(o,s){for(let k=0;k<s.length;k++)u[o+k]=s.charCodeAt(k);}str(0,'RIFF');v.setUint32(4,b.byteLength-8,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,n*2,true);for(let k=0;k<n;k++)v.setInt16(44+k*2,Math.round(6000*Math.sin(2*Math.PI*"+(220+i*35)+"*k/rate)),true);const file=new File([b],'synthetic-"+lang+"-"+i+".wav',{type:'audio/wav'}),dt=new DataTransfer();dt.items.add(file);input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));return true;})()";
   a.equal(await ev(inject),true);
   await until("document.querySelectorAll('.card .digest')["+i+"].textContent.length===73");
   const score="(()=>{const card=document.querySelectorAll('.card')["+i+"];card.querySelector('audio').dispatchEvent(new Event('ended'));card.querySelector('.listened input').click();for(const s of card.querySelectorAll('.rating select')){s.value='4';s.dispatchEvent(new Event('change'));}return true;})()";
   await ev(score);
  }
  a.equal(await ev("document.getElementById('progress').textContent"),"4 / 4");
  a.equal(await ev("document.getElementById('export').disabled"),false);
  await ev("document.getElementById('export').click()");
  const file=path.join(downloads,"honey-st3-"+lang+"-local-unverified-review.json");
  for(let i=0;i<80;i++){if(fs.existsSync(file))break;await sleep(100);}
  a.ok(fs.existsSync(file),"NO_METADATA_DOWNLOAD_"+lang);
  const packet=JSON.parse(fs.readFileSync(file,"utf8"));
  a.equal(packet.locale,lang);a.equal(packet.reviews.length,4);
  a.equal(packet.includes_audio,false);a.equal(packet.commercial_release_authorized,false);
  a.equal(core.validateContribution(packet,{...p,script_sha256:packet.protocol_script_sha256}).release,false);
  console.log("HONEY_REVIEW_CHROME_"+lang.toUpperCase()+"_LOCAL_JSON_PASS");
 }
 await cmd("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
 const layout=await ev("({w:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,cards:document.querySelectorAll('.card').length})");
 a.ok(layout.scroll<=layout.w+1,"MOBILE_OVERFLOW "+JSON.stringify(layout));a.equal(layout.cards,4);
 await ev("document.getElementById('reset').click()");
 a.equal(await ev("document.getElementById('export').disabled"),true);
 a.equal(await ev("document.getElementById('session-authorized').checked"),false);
 a.deepEqual(outbound,[],"OUTBOUND_NETWORK_DETECTED");a.deepEqual(errors,[],"JS_UNHANDLED_EXCEPTION");
 a.equal(fs.readdirSync(downloads).filter(x=>/\.wav$/i.test(x)).length,0);
 console.log("HONEY_REVIEW_CHROME_DESKTOP_MOBILE_NO_NETWORK_PASS="+JSON.stringify({layout,jsonExports:2,noAudio:true}));
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
 try{ws?.close();}catch{}try{browser?.kill();}catch{}
 await sleep(100);fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(downloads,{recursive:true,force:true});
});
