"use strict";
const fs=require("node:fs"),path=require("node:path"),a=require("node:assert/strict");
const root=process.argv[2];
a.ok(root && fs.existsSync(root),"BENCH_REPORT_DIR_MISSING");
const r=JSON.parse(fs.readFileSync(path.join(root,"benchmark.json"),"utf8"));
const s=JSON.parse(fs.readFileSync(path.join(root,"source-report.json"),"utf8"));
a.equal(s.status,"BENCHMARK_EMITTED_NEEDS_INDEPENDENT_QA","SOURCE_STAGE_NOT_COMPLETE");
a.equal(s.weight_hashes.length,4);
a.equal(s.auxiliary_hashes.length,4);
a.equal(s.commercial_approved,false);
a.equal(r.schema,"honey.supertonic3-bounded-cpu-load.v1");
a.equal(r.model_revision,"3cadd1ee6394adea1bd021217a0e650ede09a323");
a.equal(r.voice,"M1 generic preset");a.equal(r.platform,"windows-latest CPU");
a.deepEqual(r.languages,["vi","ko"]);
a.equal(r.requested_concurrency,5);a.equal(r.completed_count,5);
a.equal(r.requests.length,5);
a.equal(r.audio_artifacts_written,false);
a.equal(r.voice_identity,"UNAFFILIATED_GENERIC_PRESET");
for(const flag of ["native_listener_pronunciation_pass","male_premium_quality_pass",
"rights_approved_for_commercial_use","real_customer_load_verified","production_approved"]){a.equal(r[flag],false,flag);}
a.equal(r.runtime_versions.wheel_transitive_sha_locked,false);
a.equal(r.runtime_versions.onnxruntime,"1.23.1");
a.equal(r.runtime_versions.numpy,"2.2.6");
a.ok(r.model_load_seconds>0&&r.model_load_seconds<180);
a.ok(r.batch_wall_seconds>0&&r.batch_wall_seconds<120);
a.ok(r.speech_seconds_total>0&&r.aggregate_audio_per_wall_ratio>0);
a.ok(r.memory_after_concurrent.peak_working_set_bytes>=r.memory_after_load.peak_working_set_bytes);
a.ok(r.memory_after_concurrent.peak_working_set_bytes>100*1024*1024);
const ids=new Set(),langs=new Set();let cumulative=0;
for(const req of r.requests){
 a.ok(Number.isInteger(req.request_id)&&req.request_id>=0&&req.request_id<5&&!ids.has(req.request_id),"DUPLICATE_OR_BAD_ID");
 ids.add(req.request_id);langs.add(req.language);
 a.ok(req.text_character_count>15&&req.text_character_count<140);
 a.ok(req.speech_seconds>0.5&&req.speech_seconds<25);
 a.ok(req.wall_seconds>0&&req.wall_seconds<120);
 a.ok(req.realtime_factor>0);
 a.ok(req.rms>.002&&req.peak>.005&&req.clip_fraction<=.02);
 a.match(req.ephemeral_array_sha256,/^[a-f0-9]{64}$/);
 cumulative+=req.speech_seconds;
}
a.ok(langs.has("vi")&&langs.has("ko"));
a.ok(Math.abs(cumulative-r.speech_seconds_total)<.005);
for(const entry of fs.readdirSync(root)){
 a.ok(!entry.endsWith(".onnx")&&!entry.endsWith(".wav"),"NO_BINARY_OR_WAV_AFTER_TEST");
}
console.log("SUPER3_BOUNDED_FIVE_REQUEST_BENCHMARK_QA_PASS="+JSON.stringify({
  count:r.completed_count,loadSeconds:r.model_load_seconds,batchWallSeconds:r.batch_wall_seconds,
  sumAudioSeconds:r.speech_seconds_total,peakWorkingSetMB:+(r.memory_after_concurrent.peak_working_set_bytes/1048576).toFixed(2)}));
console.log("SUPER3_NO_PREMIUM_NATIVE_ASR_COMMERCIAL_OR_PRODUCTION_ACCEPTANCE");
