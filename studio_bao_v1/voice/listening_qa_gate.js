"use strict";
// Integrity of the research-only native listening packet. This is NOT an acoustic evaluator.
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),a=require("node:assert/strict");
const root=__dirname;
const expectedDomains=["ai_disclosure","fruit_names","delivery","confirmation"];
const sampleIds=["VI-DISC-01","VI-FRUIT-02","VI-SHIP-03","VI-CONF-04","KO-DISC-01","KO-FRUIT-02","KO-SHIP-03","KO-CONF-04"];
const prohibited=/https?:\/\/|www\.|@|(?:\+?\d[\s-]*){9,}|password|api[_ -]?key|token\s*[:=]/i;
function auditProtocol(p){
 a.equal(p.schema,"honey.st3-native-listening-protocol.v1");
 a.equal(p.status,"PREPARED_NO_AUDIO_NO_HUMAN_REVIEW");
 a.equal(p.source.model,"Supertone/supertonic-3");
 a.equal(p.source.revision,"3cadd1ee6394adea1bd021217a0e650ede09a323");
 a.equal(p.source.voice,"M1 generic preset");
 a.equal(p.source.runtime_lock,"studio_bao_v1/voice/requirements-win-py312-hashes.txt");
 a.equal(p.samples.length,8);a.deepEqual(p.samples.map(x=>x.id),sampleIds);
 const seeds=new Set(),texts=new Set(),counts={vi:0,ko:0};
 for(const sample of p.samples){
  a.ok(["vi","ko"].includes(sample.locale));
  a.ok(sample.id.startsWith(sample.locale.toUpperCase()+"-"));
  a.equal(sample.domain,expectedDomains[counts[sample.locale]]);
  counts[sample.locale]++;
  a.ok(Number.isSafeInteger(sample.seed)&&sample.seed>=20261030&&sample.seed<20269999);
  a.ok(!seeds.has(sample.seed),"DUPLICATE_SEED");seeds.add(sample.seed);
  a.ok(typeof sample.text==="string");
  a.equal(sample.text,sample.text.normalize("NFC"),"NOT_UTF8_NFC");
  a.ok(sample.text.length>=22&&sample.text.length<=160,"TEXT_LENGTH_BOUNDS");
  a.ok(!prohibited.test(sample.text),"PII_OR_SECRET_IN_SAMPLE");
  a.ok(!texts.has(sample.text),"DUPLICATED_TEST_UTTERANCE");texts.add(sample.text);
  if(sample.locale==="ko")a.match(sample.text,/[\uAC00-\uD7A3]{2,}/,"KOREAN_HANGUL_ABSENT");
  if(sample.locale==="vi")a.match(sample.text,/[àáảãạăâđêôơưíìịệướổ]/i,"VIETNAMESE_DIACRITICS_ABSENT");
 }
 a.deepEqual(counts,{vi:4,ko:4});a.equal(seeds.size,8);
 const e=p.evaluation;
 a.equal(e.minimum_independent_native_reviewers_per_locale,2);
 a.deepEqual(e.dimensions,["word_intelligibility","pronunciation","prosody","naturalness","male_presenting_timbre"]);
 a.equal(e.scale.min,1);a.equal(e.scale.max,5);
 for(let score=1;score<=5;score++)a.ok(typeof e.scale.anchors[score]==="string"&&e.scale.anchors[score].length>6);
 a.equal(e.draft_thresholds.per_dimension_median_min,4);
 a.equal(e.draft_thresholds.per_sample_intelligibility_min,4);
 a.equal(e.draft_thresholds.critical_language_or_product_error_max,0);
 a.equal(e.thresholds_are_proposals_not_human_or_legal_acceptance,true);
 a.equal(e.allow_rating_without_listening,false);
 const priv=p.privacy;
 for(const field of ["sound_release_authorized","third_party_distribution_authorized","collect_reviewer_identity_in_repo","store_review_audio_in_repo"])a.equal(priv[field],false);
 a.equal(priv.no_owner_voice_or_face,true);
 a.equal(priv.sample_storage,"NO_SAMPLE_AUDIO_CREATED_BY_THIS_PROTOCOL");
 a.equal(priv.proposed_method,"OWNER_APPROVED_SHORT_LIVED_ACCESS_CONTROLLED_IN_PERSON_OR_PRIVATE_LISTENING_ONLY");
 const f=p.acceptance;
 a.equal(f.native_vi_listening,"NOT_PROVEN");a.equal(f.native_ko_listening,"NOT_PROVEN");
 a.equal(f.quality,"NOT_PROVEN");a.equal(f.commercial_rights,"NOT_APPROVED");
 a.equal(f.identity,"GENERIC_NOT_OWNER");a.equal(f.live_or_production,"BLOCKED");
 return {cases:sampleIds.length,perLanguage:counts,reviewersPerLanguage:2,
         status:"NATIVE_LISTENING_PROTOCOL_ONLY_NOT_HUMAN_PASS",
         scriptDigest:crypto.createHash("sha256").update(JSON.stringify(p.samples)).digest("hex")};
}
function auditEmptyIntake(i){
 a.equal(i.schema,"honey.st3-native-listening-evidence.v1");
 a.equal(i.status,"NOT_PROVEN");
 a.equal(i.protocol,"studio_bao_v1/voice/listening_qa_protocol.json");
 for(const field of ["authorized_audio_sample_hashes","reviewers","review_sessions"])a.deepEqual(i[field],[],"UNAUTHORIZED_REVIEW_OR_AUDIO_EVIDENCE_"+field);
 for(const field of ["reviewer_consent_verified","audible_sample_access_authorized","native_qualification_verified","critical_errors_reviewed","independent_signoff","deployment_authorized","automated_quality_pass"])a.equal(i[field],false,"FALSE_HUMAN_OR_RELEASE_PASS_"+field);
 a.match(i.notes,/No human actually listened/);
 return {state:"NO_HUMAN_LISTENING_EVIDENCE_AND_NO_RELEASE"};
}
if(require.main===module){
 const protocol=JSON.parse(fs.readFileSync(path.join(root,"listening_qa_protocol.json"),"utf8"));
 const intake=JSON.parse(fs.readFileSync(path.join(root,"listening_qa_evidence_template.json"),"utf8"));
 console.log("ST3_BILINGUAL_NATIVE_LISTENING_PROTOCOL_QA_PASS="+JSON.stringify(auditProtocol(protocol)));
 console.log("ST3_NATIVE_LISTENING_INTAKE_FAIL_CLOSED_PASS="+JSON.stringify(auditEmptyIntake(intake)));
 console.log("ST3_NO_AUDIO_NO_NATIVE_LISTENER_NO_COMMERCIAL_RELEASE");
}
module.exports={auditProtocol,auditEmptyIntake};
