"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const {auditLegalResearch}=require("../voice/supertonic3_openrail_gate.js");
const base=JSON.parse(fs.readFileSync(path.join(__dirname,"../voice/supertonic3_openrail_preflight.json"),"utf8"));
const clone=()=>structuredClone(base);
test("accurate conditional SaaS classification with no false legal clearance",()=>{
 const x=auditLegalResearch(clone());assert.equal(x.requirements,10);assert.equal(x.cleared,0);
});
const failures=[
["code MIT incorrectly applied to weights",o=>o.source.weights_license="MIT"],
["false flat ban on commercial usage",o=>o.source.commercial_use_inherently_forbidden=true],
["fake user terms pass",o=>o.requirements[0].status="PASS"],
["fake licensing evidence",o=>o.requirements[1].evidence="verified"],
["missing distribution notice",o=>o.requirements.splice(2,1)],
["license copy clause changed",o=>o.requirements[1].clause="none"],
["AI disclosure waived",o=>o.requirements[4].status="NOT_REQUIRED"],
["voice impersonation consent automatically accepted",o=>o.independent_signoff.authorized_owner_sample_or_persona_consent=true],
["legal reviewer signoff fabricated",o=>o.independent_signoff.legal_reviewer_approval=true],
["commercial terms approval fabricated",o=>o.independent_signoff.customer_service_terms_approved=true],
["production approval fabricated",o=>o.independent_signoff.production_or_broadcast_authorized=true],
["customer outreach approval fabricated",o=>o.independent_signoff.customer_outreach_approved=true],
["native KO approval fabricated",o=>o.independent_signoff.native_ko_review_completed=true],
["claimed remote hosted service already deployed",o=>o.scope.third_party_tts_enabled=true],
["claimed publish synthetic speech",o=>o.scope.synthetic_speech_published=true],
["revision changed to floating main",o=>o.source.revision="main"],
["license link tampered",o=>o.source.license_url="https://example.com/made-up"],
["claimed commercially cleared",o=>o.conclusion="APPROVED"]
];
for(const [name,mutator] of failures)test("reject "+name,()=>{
 const v=clone();mutator(v);assert.throws(()=>auditLegalResearch(v));
});
