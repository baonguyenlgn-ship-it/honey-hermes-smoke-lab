"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const IDS=["SERVICE_TERMS_RESTRICTIONS","LICENSE_COPY","MODEL_ATTRIBUTION_NOTICES","MODIFICATION_NOTICE","AI_AUDIO_DISCLOSURE","CONSENT_NONIMPERSONATION","BOUNDING_ORDERS","PRIVACY_AND_PII","NONMISLEADING_BRAND","JURISDICTION_REVIEW"];
const signoffs=["legal_reviewer_approval","native_vi_review_completed","native_ko_review_completed","authorized_owner_sample_or_persona_consent","customer_service_terms_approved","customer_outreach_approved","commercial_distribution_authorized","production_or_broadcast_authorized"];
function auditLegalResearch(d){
 assert.equal(d.schema,"honey.st3-openrail-m-commercial-preflight.v1");
 assert.equal(d.stage,"LEGAL_AND_PRODUCT_REVIEW_REQUIRED");
 assert.equal(d.source.model,"Supertone/supertonic-3");
 assert.equal(d.source.revision,"3cadd1ee6394adea1bd021217a0e650ede09a323");
 assert.equal(d.source.license_url,
 "https://huggingface.co/Supertone/supertonic-3/blob/3cadd1ee6394adea1bd021217a0e650ede09a323/LICENSE");
 assert.equal(d.source.model_card_url,"https://huggingface.co/Supertone/supertonic-3");
 assert.equal(d.source.weights_license,"BigScience Open RAIL-M");
 assert.equal(d.source.sample_code_license,"MIT");
 assert.equal(d.source.hosted_saas_classification,"CONDITIONAL_DISTRIBUTION_SECTIONS_1G_AND_4");
 assert.equal(d.source.commercial_use_inherently_forbidden,false,"UNJUSTIFIED_ABSOLUTE_BAN");
 assert.equal(d.scope.dev_test_only,true);
 for(const k of ["owner_voice_cloning","third_party_tts_enabled","synthetic_speech_published","production_changes"])assert.equal(d.scope[k],false,"UNAUTHORIZED_ACTION_"+k);
 assert.equal(d.requirements.length,10);
 assert.deepEqual(d.requirements.map(x=>x.id),IDS);
 for(const item of d.requirements){
   assert.ok(typeof item.clause==="string"&&item.clause.length>0);
   assert.ok(typeof item.reason==="string"&&item.reason.length>20);
   assert.equal(item.status,"PENDING","LEGAL_SIGNOFF_NOT_PROVEN_"+item.id);
   assert.equal(item.evidence,null);
 }
 const clauses=Object.fromEntries(d.requirements.map(x=>[x.id,x.clause]));
 assert.equal(clauses.AI_AUDIO_DISCLOSURE,"Attachment A(e)");
 assert.equal(clauses.CONSENT_NONIMPERSONATION,"Attachment A(g)");
 assert.equal(clauses.BOUNDING_ORDERS,"Attachment A(h)");
 assert.equal(clauses.SERVICE_TERMS_RESTRICTIONS,"4(a),5,Attachment A");
 assert.equal(clauses.LICENSE_COPY,"4(b)");
 assert.equal(clauses.MODEL_ATTRIBUTION_NOTICES,"4(d)");
 assert.equal(clauses.MODIFICATION_NOTICE,"4(c)");
 assert.equal(clauses.NONMISLEADING_BRAND,"8");
 for(const field of signoffs)assert.equal(d.independent_signoff[field],false,"FORGED_SIGNOFF_"+field);
 assert.equal(Object.keys(d.independent_signoff).length,signoffs.length);
 assert.equal(d.conclusion,"NOT_LICENSE_CLEARED_FOR_HONEY_COMMERCIAL_OR_LIVE_USE");
 return {stage:d.stage,requirements:d.requirements.length,cleared:0,
  hostedSaas:"CONDITIONALLY_PERMITTED_SUBJECT_TO_REVIEW",
  verdict:d.conclusion};
}
if(require.main===module){
const obj=JSON.parse(fs.readFileSync(path.join(__dirname,"supertonic3_openrail_preflight.json"),"utf8"));
console.log("ST3_MODEL_LICENSE_PRELAUNCH_GATE_PASS="+JSON.stringify(auditLegalResearch(obj)));
console.log("ST3_LEGAL_REVIEW_NOT_COMPLETE_NO_COMMERCIAL_OR_PRODUCTION_RELEASE");
}
module.exports={auditLegalResearch};
