"use strict";
const a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=process.argv[2];a.ok(root&&fs.existsSync(root),"REPORT_DIRECTORY_REQUIRED");
const r=JSON.parse(fs.readFileSync(path.join(root,"seed-quality-report.json"),"utf8"));
const stage=JSON.parse(fs.readFileSync(path.join(root,"source-report.json"),"utf8"));
const lock=fs.readFileSync(path.join(__dirname,"requirements-win-py312-hashes.txt"));
a.equal(r.schema,"honey.st3-seeded-waveform-repro-v1");
a.equal(r.status,"SEEDED_VI_KO_TWO_RUNS_IDENTICAL_WAVEFORM_QA");
a.equal(r.model_revision,"3cadd1ee6394adea1bd021217a0e650ede09a323");
a.equal(r.voice,"M1 generic preset");
a.equal(r.seed_base,20261030);
a.equal(r.total_trials,4);
a.ok(r.load_seconds>0&&r.load_seconds<45);
a.ok(r.sample_rate>=16000&&r.sample_rate<=48000);
a.equal(stage.runtime_lock_sha256,crypto.createHash("sha256").update(lock).digest("hex"));
a.equal(stage.isolated_runtime_verified,true);
a.equal(stage.status,"SEEDED_QUALITY_EMITTED_NEEDS_INDEPENDENT_QA");
a.equal(stage.weight_hashes.length,4);
a.equal(stage.auxiliary_hashes.length,4);
a.equal(stage.wav_generated,false);
a.equal(stage.commercial_approved,false);
a.equal(r.pcm_wav_files_written,false);
for(const flag of ["native_listener_pass","male_premium_quality_pass","output_commercial_use_approved","owner_persona_or_cloned_voice","live_stream_or_production_approved"]){a.equal(r[flag],false,"FALSE_PRODUCT_ACCEPTANCE");}
a.equal(r.reproducibility_scope,"identical seed+model+process+machine+libraries only; cross-host not tested");
const seen=new Set();
for(const item of r.language_results){
 a.ok(["vi","ko"].includes(item.language)&&!seen.has(item.language),"INVALID_LANGUAGE");
 seen.add(item.language);a.equal(item.seeded_pcm_identical,true);
 a.ok(item.text_characters>20&&item.text_characters<150);
 a.equal(item.trials.length,2);
 const [first,second]=item.trials;
 a.equal(first.trial,1);a.equal(second.trial,2);
 a.equal(first.seed,second.seed);
 a.match(first.pcm_sha256,/^[a-f0-9]{64}$/);
 a.equal(first.pcm_sha256,second.pcm_sha256);
 a.equal(first.samples,second.samples);
 for(const t of item.trials){
   a.ok(t.samples>r.sample_rate&&t.samples<r.sample_rate*25);
   a.ok(t.duration_seconds>1&&t.duration_seconds<25);
   a.ok(t.elapsed_seconds>0&&t.elapsed_seconds<50);
   a.ok(t.rms>=.002&&t.rms<=.8);
   a.ok(t.peak>=.02&&t.peak<2);
   a.ok(Math.abs(t.dc_offset)<=.04);
   a.ok(t.near_fullscale_fraction<=.01&&t.fullscale_fraction<=.001);
   a.ok(t.activity_fraction>=.05&&t.activity_fraction<=1);
 }
}
a.deepEqual([...seen].sort(),["ko","vi"]);
a.notEqual(
 r.language_results.find(x=>x.language==="vi").trials[0].pcm_sha256,
 r.language_results.find(x=>x.language==="ko").trials[0].pcm_sha256,
 "TWO_DIFFERENT_LANGUAGES_CANNOT_SHARE_IDENTICAL_AUDIO"
);
for(const file of fs.readdirSync(root)){
 a.ok(!/\.(onnx|wav|whl)$/i.test(file),"AUDIO_OR_BINARY_MUST_NOT_BE_PUBLISHED");
}
console.log("ST3_INDEPENDENT_SEEDED_VI_KO_REPRO_WAVEFORM_QA_PASS="+JSON.stringify({
 languages:[...seen].sort(),trials:r.total_trials,seedBase:r.seed_base,
 vi:r.language_results.find(x=>x.language==="vi").trials[0],
 ko:r.language_results.find(x=>x.language==="ko").trials[0]
}));
console.log("ST3_SEEDED_BYTES_PASS_NOT_NATIVE_LISTENER_OR_PREMIUM_OR_COMMERCIAL_PASS");
