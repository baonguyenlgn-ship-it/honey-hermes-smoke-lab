"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const studio = require("../app.js");
const captions = require("../subtitles.js");
const root = path.resolve(__dirname,"..");
const html = fs.readFileSync(path.join(root,"index.html"),"utf8");
const css = fs.readFileSync(path.join(root,"style.css"),"utf8");
const js = fs.readFileSync(path.join(root,"app.js"),"utf8");
const subtitleSource = fs.readFileSync(path.join(root,"subtitles.js"),"utf8");

test("all preview assets are standalone UTF-8 text",()=>{
 assert.ok(html.startsWith("<!doctype html>"));
 assert.ok(css.includes(".stage-canvas"));
 assert.ok(js.includes("function mount(doc)"));
 assert.ok(!html.includes("\uFFFD"));
});
test("all four localized catalogs are available",()=>{
 assert.deepEqual(studio.LANGS,["vi","ko","en","zh"]);
 for(const lang of studio.LANGS)for(const k of studio.PRODUCTS){
  assert.ok(studio.COPY[lang].products[k]);
  assert.ok(studio.COPY[lang].scripts[k]);
 }
});
test("Bảo V1 branding and explicit demo warning",()=>{
 for(const text of ["Bảo V1","DEV PREVIEW","SIMULATION ONLY","NOT LIVE","NO LIVE"])assert.ok(html.includes(text),text);
});
test("approved avatar photo is not invented",()=>{
 assert.match(html,/Approved Bảo visual not connected/);
 assert.match(html,/avatar-disclaimer/);
 assert.ok(!html.includes("https://"));
});
test("browser loads only local CSS and JS resources",()=>{
 assert.match(html,/href="\.\/style\.css"/);
 assert.match(html,/src="\.\/app\.js"/);
 assert.doesNotMatch(html,/<script[^>]+https?:/i);
 assert.doesNotMatch(css,/@import\s+url\(['"]?https?:/i);
});
test("no real broadcast, storage, network calls or external sends",()=>{
 for(const source of [html,js,subtitleSource]){
  assert.doesNotMatch(source,/\bfetch\s*\(/);
  assert.doesNotMatch(source,/\bXMLHttpRequest\b|\bWebSocket\b|\bsendBeacon\s*\(/);
  assert.doesNotMatch(source,/\blocalStorage\b|\bsessionStorage\b/);
 }
});
test("state is initialized offline with no orders",()=>{
 const s=studio.initialState();
 assert.deepEqual(s,{language:"vi",product:"mango",playing:false,sceneIndex:0,replied:false,draftCount:0});
});
test("play is a reversible local storyboard state",()=>{
 const s=studio.initialState();
 const active=studio.transition(s,{type:"PLAY"});
 assert.equal(active.playing,true);
 assert.equal(studio.transition(active,{type:"PLAY"}).playing,false);
 assert.equal(s.playing,false);
});
test("product switch selects bounded demo catalog only",()=>{
 const s=studio.initialState();
 assert.equal(studio.transition(s,{type:"PRODUCT",value:"coconut"}).product,"coconut");
 assert.strictEqual(studio.transition(s,{type:"PRODUCT",value:"real-inventory-id"}),s);
});
test("locale switch preserves per-product script and reply resets",()=>{
 let s=studio.transition(studio.initialState(),{type:"REPLY"});
 s=studio.transition(s,{type:"LANGUAGE",value:"ko"});
 assert.equal(s.replied,false);
 assert.match(studio.viewModel(s).script,/망고/);
 assert.strictEqual(studio.transition(s,{type:"LANGUAGE",value:"ru"}),s);
});
test("mock reply is never an external send",()=>{
 const x=studio.transition(studio.initialState(),{type:"REPLY"});
 assert.equal(x.replied,true);
 assert.match(studio.viewModel(x).replyText,/DEMO/);
});
test("draft intents are locally capped and cannot produce actual orders",()=>{
 let s=studio.initialState();
 for(let i=0;i<40;i++)s=studio.transition(s,{type:"DRAFT"});
 assert.equal(s.draftCount,5);
 assert.match(studio.COPY.ko.intent,/ERP/);
});
test("reset preserves selected language and clears ephemeral actions",()=>{
 let s=studio.initialState();
 for(const a of [{type:"LANGUAGE",value:"zh"},{type:"PRODUCT",value:"pomelo"},{type:"PLAY"},{type:"REPLY"},{type:"DRAFT"}])s=studio.transition(s,a);
 const reset=studio.transition(s,{type:"RESET"});
 assert.equal(reset.language,"zh");
 assert.equal(reset.product,"mango");
 assert.equal(reset.playing,false);
 assert.equal(reset.draftCount,0);
 assert.equal(reset.replied,false);
});
test("invalid state actions fail closed",()=>{
 assert.throws(()=>studio.transition(null,{type:"PLAY"}),/BAD_DEMO_ACTION/);
 assert.throws(()=>studio.transition(studio.initialState(),{type:"SEND_ORDER"}),/UNKNOWN_DEMO_ACTION/);
});
test("all interactive controls exist in the HTML",()=>{
 for(const id of ["lang","play-btn","reset-btn","reply-btn","draft-btn","products","subtitle","script-content","reply-content","draft-count"])
  assert.ok(html.includes('id="'+id+'"'),id);
});

test("all user-facing studio headings and prototype captions are localized in 4 languages",()=>{
 for(const lang of studio.LANGS){
  const copy=studio.COPY[lang];
  for(const key of ["stageHeading","productsHeading","scriptHeading","commentsHeading","timeline","productNote","transport","draftStatus"])
   assert.ok(copy.labels[key]?.trim(),lang+" missing "+key);
  for(const product of studio.PRODUCTS)assert.ok(copy.subtitles[product]?.trim(),lang+" missing "+product);
 }
});
test("playing demo subtitle follows product and language; reset uses greeting",()=>{
 let s=studio.initialState();
 assert.equal(studio.viewModel(s).subtitle,studio.COPY.vi.subtitle);
 s=studio.transition(s,{type:"PLAY"});
 assert.equal(studio.viewModel(s).subtitle,studio.COPY.vi.subtitles.mango);
 s=studio.transition(s,{type:"PRODUCT",value:"coconut"});
 assert.equal(studio.viewModel(s).subtitle,studio.COPY.vi.subtitles.coconut);
 s=studio.transition(s,{type:"LANGUAGE",value:"ko"});
 assert.equal(studio.viewModel(s).subtitle,studio.COPY.ko.subtitles.coconut);
 s=studio.transition(s,{type:"RESET"});
 assert.equal(studio.viewModel(s).subtitle,studio.COPY.ko.subtitle);
});

test("all 4 languages contain exactly 3 narrative beats for each of 3 fruit products",()=>{
 for(const lang of studio.LANGS){
  assert.equal(studio.SCENE_UI[lang].titles.length,3);
  for(const product of studio.PRODUCTS){
   const beats=studio.STORYBOARD[lang][product];
   assert.equal(beats.length,3,lang+" "+product);
   for(const beat of beats)for(const key of ["script","subtitle"])
    assert.ok(typeof beat[key]==="string"&&beat[key].trim().length>=8,lang+" "+product+" "+key);
   assert.notEqual(beats[0].subtitle,beats[1].subtitle);
   assert.notEqual(beats[1].subtitle,beats[2].subtitle);
  }
 }
});
test("scene commands are gated until play and cannot overrun 3 beats",()=>{
 let state=studio.initialState();
 assert.strictEqual(studio.transition(state,{type:"NEXT_SCENE"}),state);
 assert.equal(studio.viewModel(state).nextDisabled,true);
 state=studio.transition(state,{type:"PLAY"});
 for(let n=0;n<10;n++)state=studio.transition(state,{type:"NEXT_SCENE"});
 assert.equal(state.sceneIndex,2);
 assert.equal(studio.viewModel(state).sceneCounter,"03 / 03");
 assert.equal(studio.viewModel(state).nextDisabled,true);
 for(let n=0;n<10;n++)state=studio.transition(state,{type:"PREV_SCENE"});
 assert.equal(state.sceneIndex,0);
 assert.equal(studio.viewModel(state).previousDisabled,true);
});
test("product change returns to first beat and language preserves selected beat",()=>{
 let state=studio.transition(studio.initialState(),{type:"PLAY"});
 state=studio.transition(state,{type:"NEXT_SCENE"});
 const viCaption=studio.viewModel(state).subtitle;
 state=studio.transition(state,{type:"LANGUAGE",value:"ko"});
 assert.equal(state.sceneIndex,1);
 assert.notEqual(studio.viewModel(state).subtitle,viCaption);
 assert.equal(studio.viewModel(state).subtitle,studio.STORYBOARD.ko.mango[1].subtitle);
 state=studio.transition(state,{type:"PRODUCT",value:"pomelo"});
 assert.equal(state.sceneIndex,0);
 assert.equal(studio.viewModel(state).subtitle,studio.STORYBOARD.ko.pomelo[0].subtitle);
});
test("pause resumes current beat but shows safe greeting while paused",()=>{
 let state=studio.transition(studio.initialState(),{type:"PLAY"});
 state=studio.transition(state,{type:"NEXT_SCENE"});
 state=studio.transition(state,{type:"PLAY"});
 assert.equal(state.sceneIndex,1);
 assert.equal(studio.viewModel(state).subtitle,studio.COPY.vi.subtitle);
 assert.strictEqual(studio.transition(state,{type:"NEXT_SCENE"}),state);
 state=studio.transition(state,{type:"PLAY"});
 assert.equal(studio.viewModel(state).subtitle,studio.STORYBOARD.vi.mango[1].subtitle);
 state=studio.transition(state,{type:"RESET"});
 assert.equal(state.sceneIndex,0);
 assert.equal(state.playing,false);
});
test("navigation controls are present and mock-only",()=>{
 for(const id of ["prev-scene-btn","next-scene-btn","scene-counter","scene-caption"])
  assert.ok(html.includes('id="'+id+'"'),id);
 assert.ok(html.includes("Demo storyboard scenes"));
});

test("timecode formatting for SRT and VTT is locale-independent",()=>{
 assert.equal(captions.clock(0,"srt"),"00:00:00,000");
 assert.equal(captions.clock(9000,"vtt"),"00:00:09.000");
 assert.equal(captions.clock(30000,"srt"),"00:00:30,000");
 assert.throws(()=>captions.clock(-1,"srt"),/BAD_TIMECODE_MS/);
});
test("all 12 product-language combinations export 3 contiguous nonoverlapping timed cues",()=>{
 for(const language of studio.LANGS)for(const product of studio.PRODUCTS){
  for(const format of ["srt","vtt"]){
   const report=captions.createExport({beats:studio.STORYBOARD[language][product],language,product,format});
   assert.match(report.filename,/^honey-bao-v1-(mango|coconut|pomelo)-(vi|ko|en|zh)-demo\.(srt|vtt)$/);
   assert.equal(report.cues.length,3);
   assert.equal(report.estimatedTotalMs,30000);
   assert.equal(report.cues[0].startMs,0);
   assert.equal(report.cues[0].endMs,report.cues[1].startMs);
   assert.equal(report.cues[1].endMs,report.cues[2].startMs);
   assert.equal(report.cues[2].endMs,30000);
   assert.ok(report.text.includes(" --> "));
   assert.ok(report.text.includes(studio.STORYBOARD[language][product][1].subtitle));
   assert.equal(report.disclaimer,"DEMO_ESTIMATED_TIME_NOT_AUDIO_SYNC");
  }
 }
});
test("SRT and WebVTT are standard plain-text caption formats",()=>{
 const beats=studio.STORYBOARD.vi.mango;
 const srt=captions.createExport({beats,language:"vi",product:"mango",format:"srt"}).text;
 const vtt=captions.createExport({beats,language:"vi",product:"mango",format:"vtt"}).text;
 assert.match(srt,/^1\n00:00:00,000 --> 00:00:09,000\n/);
 assert.match(srt,/\n\n2\n00:00:09,000 --> 00:00:20,000\n/);
 assert.match(srt,/\n\n3\n00:00:20,000 --> 00:00:30,000\n/);
 assert.match(vtt,/^WEBVTT\n\n00:00:00.000 --> 00:00:09.000\n/);
 assert.equal(vtt.includes("00:00:00,000"),false);
});
test("untrusted text, invalid export scopes, or malformed cue arrays fail closed",()=>{
 const base=studio.STORYBOARD.vi.mango;
 assert.throws(()=>captions.createExport({beats:base,language:"ru",product:"mango",format:"srt"}),/BAD_EXPORT_SCOPE/);
 assert.throws(()=>captions.createExport({beats:base,language:"vi",product:"mango",format:"exe"}),/BAD_EXPORT_SCOPE/);
 assert.throws(()=>captions.buildCues([{subtitle:"hello"}]),/BAD_STORYBOARD_BEATS/);
 assert.throws(()=>captions.buildCues(base.map(x=>({subtitle:x.subtitle+"\nX"}))),/UNSAFE_SUBTITLE_TEXT/);
 assert.throws(()=>captions.buildCues(base.map(x=>({subtitle:x.subtitle+" -->"}))),/UNSAFE_SUBTITLE_TEXT/);
});
test("export control is available offline, clearly DEMO and not an audio sync claim",()=>{
 assert.ok(html.includes('id="export-srt-btn"'));
 assert.ok(html.includes('id="export-vtt-btn"'));
 assert.ok(html.includes('src="./subtitles.js"'));
 assert.ok(html.includes("chưa đồng bộ giọng nói/video"));
 assert.ok(subtitleSource.includes("DEMO_ESTIMATED_TIME_NOT_AUDIO_SYNC"));
});

const audioTiming=require("../audio_timing.js");
const {createHash}=require("node:crypto");
function silentFixture(){
 const pcmBytes=16000,bytes=Buffer.alloc(pcmBytes+44);
 bytes.write("RIFF",0);bytes.writeUInt32LE(bytes.length-8,4);bytes.write("WAVE",8);
 bytes.write("fmt ",12);bytes.writeUInt32LE(16,16);bytes.writeUInt16LE(1,20);
 bytes.writeUInt16LE(1,22);bytes.writeUInt32LE(8000,24);
 bytes.writeUInt32LE(16000,28);bytes.writeUInt16LE(2,32);bytes.writeUInt16LE(16,34);
 bytes.write("data",36);bytes.writeUInt32LE(pcmBytes,40);
 return bytes;
}
function fixtureManifest(bytes){
 const names=studio.STORYBOARD.vi.mango.map(x=>x.subtitle);
 return {version:1,method:"manual_unverified_alignment",language:"vi",product:"mango",
  durationMs:1000,sha256:createHash("sha256").update(bytes).digest("hex"),
  cues:[{startMs:0,endMs:300,text:names[0]},{startMs:300,endMs:700,text:names[1]},{startMs:700,endMs:1000,text:names[2]}]};
}
function arrayBuffer(buffer){return buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength)}
test("native PCM WAV metadata derives from bytes rather than claimed manifest",()=>{
 const wav=silentFixture(),meta=audioTiming.parseWav(arrayBuffer(wav));
 assert.equal(meta.durationMs,1000);assert.equal(meta.sampleCount,8000);
 assert.equal(meta.channels,1);assert.equal(meta.sampleRate,8000);
 const tampered=Buffer.from(wav);tampered.write("BAD!",0);
 assert.throws(()=>audioTiming.parseWav(arrayBuffer(tampered)),/WAV_RIFF_INVALID/);
});
test("valid synthetic silence verifies SHA but NEVER spoken alignment or rights",async()=>{
 const wav=silentFixture(),manifest=fixtureManifest(wav);
 const report=await audioTiming.verify({wavBytes:arrayBuffer(wav),manifest,language:"vi",product:"mango",beats:studio.STORYBOARD.vi.mango});
 assert.equal(report.integrity,"WAV_SHA256_MATCHED");
 assert.equal(report.alignment,"MANUAL_NOT_VERIFIED_WITH_SPEECH");
 assert.equal(report.rights,"NOT_VERIFIED");
 assert.equal(report.audio.durationMs,1000);
 assert.match(captions.render(report.cues,"vtt"),/00:00:00.700 --> 00:00:01.000/);
});
test("audio duration SHA transcript language and unknown fields fail closed",async()=>{
 const wav=silentFixture(),manifest=fixtureManifest(wav),args={wavBytes:arrayBuffer(wav),language:"vi",product:"mango",beats:studio.STORYBOARD.vi.mango};
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,durationMs:1001}}),/MANIFEST_DURATION_MISMATCH/);
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,sha256:"0".repeat(64)}}),/WAV_SHA_MISMATCH/);
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,language:"ko"}}),/MANIFEST_SCOPE_INVALID/);
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,extra:true}}),/MANIFEST_EXTRA_FIELDS/);
 const cues=manifest.cues.map((c,i)=>i===0?{...c,text:"wrong product claim"}:c);
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,cues}}),/TIMING_TEXT_MISMATCH/);
});
test("manual timing gap incomplete coverage unsupported PCM fail closed",async()=>{
 const wav=silentFixture(),manifest=fixtureManifest(wav),args={wavBytes:arrayBuffer(wav),language:"vi",product:"mango",beats:studio.STORYBOARD.vi.mango};
 const gap=manifest.cues.map((c,i)=>i===1?{...c,startMs:325}:c);
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,cues:gap}}),/TIMING_GAP_OVERLAP_OR_BOUNDS/);
 const short=manifest.cues.map((c,i)=>i===2?{...c,endMs:950}:c);
 await assert.rejects(audioTiming.verify({...args,manifest:{...manifest,cues:short}}),/TIMING_INCOMPLETE/);
 const invalid=Buffer.from(wav);invalid.writeUInt16LE(24,34);
 assert.throws(()=>audioTiming.parseWav(arrayBuffer(invalid)),/WAV_PCM16_REQUIRED/);
});
test("audio contract has no network and explicitly rejects voice/rights certification",()=>{
 const code=fs.readFileSync(path.join(root,"audio_timing.js"),"utf8");
 assert.doesNotMatch(code,/fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon/);
 assert.match(code,/MANUAL_NOT_VERIFIED_WITH_SPEECH/);
 assert.match(code,/rights:"NOT_VERIFIED"/);
});

test("local WAV + JSON controls are bound but not actual voice verification",()=>{
 const audioSource=fs.readFileSync(path.join(root,"audio_timing.js"),"utf8");
 assert.match(html,/id="audio-wav-input"/);
 assert.match(html,/id="audio-json-input"/);
 assert.match(html,/id="verify-audio-btn"/);
 assert.match(html,/id="audio-verify-status"/);
 assert.match(html,/src="\.\/audio_timing\.js"/);
 assert.match(audioSource,/MANUAL_NOT_VERIFIED_WITH_SPEECH/);
 assert.ok(js.includes('verifiedAudio=null'));
 assert.ok(js.includes("importGeneration"));
 assert.doesNotMatch(audioSource,/fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon/);
});
test("manual-bound caption export must never silently advertise audio/video alignment",()=>{
 assert.ok(js.includes("-wav-matched-manual-not-synced."));
 assert.ok(js.includes('verifiedAudio.cues'));
 assert.ok(js.includes("AUDIO_UI"));
 assert.equal(Object.keys(studio.STORYBOARD).length,4);
});

test("local verified WAV playback uses only blob URL, native media and manual cues",()=>{
 assert.match(html,/id="local-audio-player"/);
 assert.match(html,/preload="metadata" controls hidden/);
 assert.match(html,/id="local-audio-caption"/);
 assert.match(js,/NOT SPEECH-SYNCED/);
 assert.match(html,/not validated speech alignment/);
 assert.ok(js.includes("URL.createObjectURL(new Blob([bytes]"));
 assert.ok(js.includes("URL.revokeObjectURL(playbackUrl)"));
 assert.ok(js.includes('audioPlayer.addEventListener("loadedmetadata"'));
 assert.ok(js.includes("resetPlayback();verifiedAudio=null"));
 assert.ok(!js.includes("audioPlayer.autoplay"));
});
