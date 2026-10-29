"use strict";
const test=require("node:test"),a=require("node:assert/strict");
const fs=require("node:fs"),os=require("node:os"),path=require("node:path"),crypto=require("node:crypto"),cp=require("node:child_process");
const voiceDir=path.join(__dirname,"../voice");
const checker=path.join(voiceDir,"supertonic3_seed_quality_check.js");
const lock=fs.readFileSync(path.join(voiceDir,"requirements-win-py312-hashes.txt"));
const lockSha=crypto.createHash("sha256").update(lock).digest("hex");
const digests={vi:"a".repeat(64),ko:"b".repeat(64)};
function correctTrial(lang,idx) {
 const dur=lang==="vi"?5.1548:4.8762;
 return {
   trial:idx,seed:lang==="vi"?20261131:20261232,pcm_sha256:digests[lang],
   samples:lang==="vi"?227328:215040,duration_seconds:dur,
   elapsed_seconds:1.1,rms:.05,peak:.5,dc_offset:0,
   near_fullscale_fraction:0,fullscale_fraction:0,activity_fraction:.4
 };
}
function fixture() {
 return {
   report:{
     schema:"honey.st3-seeded-waveform-repro-v1",
     status:"SEEDED_VI_KO_TWO_RUNS_IDENTICAL_WAVEFORM_QA",
     model_revision:"3cadd1ee6394adea1bd021217a0e650ede09a323",
     voice:"M1 generic preset",seed_base:20261030,load_seconds:.8,sample_rate:44000,
     language_results:["vi","ko"].map(language=>({
       language,text_characters:55,
       seeded_pcm_identical:true,
       trials:[correctTrial(language,1),correctTrial(language,2)]
     })),
     total_trials:4,pcm_wav_files_written:false,
     native_listener_pass:false,male_premium_quality_pass:false,
     output_commercial_use_approved:false,owner_persona_or_cloned_voice:false,
     live_stream_or_production_approved:false,
     reproducibility_scope:"identical seed+model+process+machine+libraries only; cross-host not tested"
   },
   source:{
     status:"SEEDED_QUALITY_EMITTED_NEEDS_INDEPENDENT_QA",
     runtime_lock_sha256:lockSha,isolated_runtime_verified:true,
     weight_hashes:[{},{},{},{}],auxiliary_hashes:[{},{},{},{}],
     wav_generated:false,commercial_approved:false
   }
 };
}
function run(mutator=()=>{}) {
 const obj=fixture();mutator(obj);
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"honey-st3-tamper-test-"));
 try {
   fs.writeFileSync(path.join(dir,"seed-quality-report.json"),JSON.stringify(obj.report));
   fs.writeFileSync(path.join(dir,"source-report.json"),JSON.stringify(obj.source));
   const result=cp.spawnSync(process.execPath,[checker,dir],{encoding:"utf8",timeout:10000});
   if(result.error)throw result.error;
   return {code:result.status,stdout:result.stdout,stderr:result.stderr};
 } finally {fs.rmSync(dir,{recursive:true,force:true});}
}
test("synthetic valid-shaped baseline must PASS gate",()=>{
 const r=run();
 a.equal(r.code,0,"BASELINE_FIXTURE_INVALID "+r.stderr);
 a.match(r.stdout,/ST3_INDEPENDENT_SEEDED_VI_KO_REPRO_WAVEFORM_QA_PASS/);
});
const reject=[
 ["mismatching same-seed PCM hash",o=>o.report.language_results[0].trials[1].pcm_sha256="c".repeat(64)],
 ["mismatching same-seed sample count",o=>o.report.language_results[1].trials[1].samples+=2],
 ["duplicate audio across different languages",o=>o.report.language_results[1].trials.forEach(t=>t.pcm_sha256=digests.vi)],
 ["excessive fullscale clipping",o=>o.report.language_results[0].trials[0].fullscale_fraction=.02],
 ["near fullscale saturation",o=>o.report.language_results[1].trials[0].near_fullscale_fraction=.05],
 ["excessive DC bias",o=>o.report.language_results[0].trials[1].dc_offset=.3],
 ["false commercial approval",o=>o.report.output_commercial_use_approved=true],
 ["false premium claim",o=>o.report.male_premium_quality_pass=true],
 ["false native listening",o=>o.report.native_listener_pass=true],
 ["false Owner impersonation",o=>o.report.owner_persona_or_cloned_voice=true],
 ["wrong locked runtime hash",o=>o.source.runtime_lock_sha256="f".repeat(64)],
 ["missing verified ONNX",o=>o.source.weight_hashes.pop()],
 ["missing Korean QA",o=>o.report.language_results.splice(1,1)],
 ["fake written voice files",o=>o.report.pcm_wav_files_written=true]
];
for(const [name,mutator] of reject){
 test("fail-closed against "+name,()=>{
  const r=run(mutator);
  a.notEqual(r.code,0,"FALSE_PASS_FOR_"+name);
  a.match(r.stderr,/AssertionError|Error/);
 });
}
