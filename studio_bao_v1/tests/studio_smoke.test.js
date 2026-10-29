"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const studio = require("../app.js");
const root = path.resolve(__dirname,"..");
const html = fs.readFileSync(path.join(root,"index.html"),"utf8");
const css = fs.readFileSync(path.join(root,"style.css"),"utf8");
const js = fs.readFileSync(path.join(root,"app.js"),"utf8");

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
 for(const source of [html,js]){
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
