"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),a=require("node:assert/strict");
const protocol=JSON.parse(fs.readFileSync(path.join(__dirname,"listening_qa_protocol.json"),"utf8"));
function audit(report,stage){
 a.equal(report.schema,"honey.st3-eight-script-in-memory-feasibility.v1");
 a.equal(report.status,"EIGHT_GENERIC_SCRIPT_SIGNALS_GENERATED_NOT_HUMAN_APPROVED");
 a.equal(report.model_revision,protocol.source.revision);
 a.equal(report.voice,"M1 generic preset");
 a.ok(report.sample_rate>=16000&&report.sample_rate<=48000);
 a.ok(report.model_load_seconds>0&&report.model_load_seconds<80);
 a.equal(report.total_script_count,8);a.equal(report.scripts.length,8);
 for(const f of ["wav_files_written","model_audio_published","native_vi_listening_verified","native_ko_listening_verified",
 "legal_commercial_release_authorized","production_authorized"])a.equal(report[f],false,"FALSE_ACCEPTANCE_"+f);
 a.equal(stage.status,"EIGHT_SCRIPT_SIGNALS_NEED_INDEPENDENT_QA");
 a.equal(stage.weight_hashes.length,4);a.equal(stage.auxiliary_hashes.length,4);
 a.equal(stage.wav_generated,false);a.equal(stage.commercial_approved,false);
 a.equal(stage.isolated_runtime_verified,true);
 const lock=fs.readFileSync(path.join(__dirname,"requirements-win-py312-hashes.txt"));
 a.equal(stage.runtime_lock_sha256,crypto.createHash("sha256").update(lock).digest("hex"));
 const seenHashes=new Set();
 for(let i=0;i<8;i++){
   const x=report.scripts[i],source=protocol.samples[i];
   a.equal(x.id,source.id);a.equal(x.locale,source.locale);a.equal(x.seed,source.seed);
   a.equal(x.text_sha256,crypto.createHash("sha256").update(source.text,"utf8").digest("hex"));
   a.match(x.pcm_sha256,/^[a-f0-9]{64}$/);
   a.ok(!seenHashes.has(x.pcm_sha256),"DUPLICATED_AUDIO_DIFFERENT_SCRIPT");
   seenHashes.add(x.pcm_sha256);
   a.ok(x.duration_seconds>=.8&&x.duration_seconds<=30);
   a.ok(x.synthesis_seconds>0&&x.synthesis_seconds<90);
   a.ok(x.rms>.002&&x.rms<=1);
   a.ok(x.peak>.02&&x.peak<2);
   a.ok(Math.abs(x.dc_offset)<=.04);
   a.ok(x.near_fullscale_fraction<=.01&&x.fullscale_fraction<=.001);
   a.ok(x.activity_fraction>.025&&x.activity_fraction<=1);
 }
 return {clips:seenHashes.size,vi:report.scripts.filter(x=>x.locale==="vi").length,
   ko:report.scripts.filter(x=>x.locale==="ko").length,
   waveformsOnly:true,realListenerApproval:false};
}
if(require.main===module){
 const dir=process.argv[2];a.ok(dir&&fs.existsSync(dir));
 const report=JSON.parse(fs.readFileSync(path.join(dir,"eight-script-signal-qa.json"),"utf8"));
 const stage=JSON.parse(fs.readFileSync(path.join(dir,"source-report.json"),"utf8"));
 const result=audit(report,stage);
 for(const f of fs.readdirSync(dir))a.ok(!/\.(wav|onnx|whl)$/i.test(f),"BINARY_PUBLISHED");
 console.log("ST3_EIGHT_VI_KO_SCRIPT_SIGNALS_INDEPENDENT_QA_PASS="+JSON.stringify(result));
 console.log("ST3_NO_NATIVE_LISTENER_NO_COMMERCIAL_OR_PRODUCTION_ACCEPTANCE");
}
module.exports={audit};
