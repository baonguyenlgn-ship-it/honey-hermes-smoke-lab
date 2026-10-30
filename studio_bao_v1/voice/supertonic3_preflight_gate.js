"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const REV="3cadd1ee6394adea1bd021217a0e650ede09a323";
function audit(c){
  assert.equal(c.schema,"honey.supertonic3-preflight.v1");
  assert.equal(c.state,"RESEARCH_ONLY");
  assert.equal(c.source.repo,"Supertone/supertonic-3");
  assert.equal(c.source.revision,REV);
  assert.ok(c.source.license.includes(REV+"/LICENSE"));
  assert.deepEqual(c.languages,["vi","ko"]);
  assert.deepEqual(c.voice_presets,["M1","M2","M3","M4","M5"]);
  assert.equal(c.model_type,"ONNX");
  assert.equal(c.license_code,"MIT");
  assert.equal(c.license_weights,"OpenRAIL-M");
  for(const file of ["onnx/text_encoder.onnx","onnx/vocoder.onnx","voice_styles/M1.json"]){
    assert.ok(c.file_paths.includes(file),"MISSING_EXPECTED_ASSET");
  }
  for(const [key,v] of Object.entries({
    read_full_license:true,disclose_generated_speech:true,no_owner_impersonation:true,
    no_untrusted_pickle:true,no_remote_code:true,no_auto_download:true,
    commercial_clearance:false,model_hash_verified:false,native_listening_pass:false,
    voice_timbre_pass:false,authorized_production:false
  })){
    assert.equal(c.constraints[key],v,"INVALID_GATE_"+key);
  }
  assert.deepEqual(c.sha256_assets,{},"UNPROVEN_ASSET_SHA");
  assert.equal(c.observed_audio,null,"NO_SYNTHESIS_YET");
  assert.match(c.notes,/OpenRAIL-M/);
  return {result:"SUPERTONIC3_RESEARCH_ONLY",languages:c.languages,revision:REV,ready_for_paid_or_production_use:false};
}
if(require.main===module){
  const data=JSON.parse(fs.readFileSync(path.join(__dirname,"supertonic3_preflight.json"),"utf8"));
  console.log("SUPERTONIC3_FAIL_CLOSED_PREFLIGHT_PASS="+JSON.stringify(audit(data)));
  console.log("NO_MODEL_DOWNLOADED_NO_WAV_NO_LICENSE_ACCEPTANCE");
}
module.exports={audit};
