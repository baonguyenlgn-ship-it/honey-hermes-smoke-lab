"use strict";
const test=require("node:test"),a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const {auditProtocol,auditEmptyIntake}=require("../voice/listening_qa_gate.js");
const protocol=JSON.parse(fs.readFileSync(path.join(__dirname,"../voice/listening_qa_protocol.json"),"utf8"));
const intake=JSON.parse(fs.readFileSync(path.join(__dirname,"../voice/listening_qa_evidence_template.json"),"utf8"));
const copy=v=>structuredClone(v);
test("real packet has eight native-language review scripts, no audio",()=>{
 a.equal(auditProtocol(copy(protocol)).cases,8);
 a.equal(auditEmptyIntake(copy(intake)).state,"NO_HUMAN_LISTENING_EVIDENCE_AND_NO_RELEASE");
});
const bad=[
 ["missing KO sample",x=>x.samples.pop()],
 ["swapped language tag",x=>x.samples[0].locale="ko"],
 ["missing Vietnamese diacritics",x=>x.samples[1].text="Today we have fruit for sale, thank you."],
 ["no Korean Hangul",x=>x.samples[7].text="Hello, no real Korean sample is included."],
 ["duplicate sample text",x=>x.samples[1].text=x.samples[0].text],
 ["duplicate seed",x=>x.samples[1].seed=x.samples[0].seed],
 ["PII phone number",x=>x.samples[2].text="Vui lòng gọi đến số 01012345678 để kiểm tra đơn hàng."],
 ["personal email",x=>x.samples[2].text="Vui lòng liên hệ email example@example.com để gửi đơn hàng."],
 ["changed model identity",x=>x.source.voice="Owner Bao cloned voice"],
 ["lower reviewer count",x=>x.evaluation.minimum_independent_native_reviewers_per_locale=1],
 ["raise fake release score",x=>x.acceptance.quality="PASS"],
 ["approve third party media",x=>x.privacy.third_party_distribution_authorized=true],
 ["no AI disclosure in protocol",x=>x.evaluation.allow_rating_without_listening=true],
 ["fake native VI listening",x=>x.acceptance.native_vi_listening="PASS"],
 ["weaken intelligibility bar",x=>x.evaluation.draft_thresholds.per_sample_intelligibility_min=1]
];
for(const [name,mutate] of bad)test("reject protocol: "+name,()=>{
 const copyInput=copy(protocol);mutate(copyInput);a.throws(()=>auditProtocol(copyInput));
});
const fake=[
 ["fake reviewer score",x=>x.review_sessions=[{score:5}]],
 ["fake audio available",x=>x.authorized_audio_sample_hashes=["a".repeat(64)]],
 ["fake reviewer",x=>x.reviewers=[{language:"vi",native:true}]],
 ["fake consent",x=>x.reviewer_consent_verified=true],
 ["fake independent signoff",x=>x.independent_signoff=true],
 ["fake commercial deployment",x=>x.deployment_authorized=true],
 ["fake automated high-quality claim",x=>x.automated_quality_pass=true]
];
for(const [name,mutate] of fake)test("reject evidence: "+name,()=>{
 const copyInput=copy(intake);mutate(copyInput);a.throws(()=>auditEmptyIntake(copyInput));
});
