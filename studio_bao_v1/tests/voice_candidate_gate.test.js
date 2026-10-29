"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {audit} = require("../voice/voice_candidate_gate.js");
const base = JSON.parse(fs.readFileSync(path.join(__dirname,"../voice/candidates.json"),"utf8"));
const copy = () => structuredClone(base);
test("truthful offline registry gate accepts only research readiness", () => {
  const out=audit(copy());
  assert.equal(out.passed,true);assert.equal(out.candidates.length,2);
  for (const c of out.candidates) assert.equal(c.audio,"NOT_PROVEN");
});
test("fail closed if Korean candidate is removed",()=>{
  const x=copy();x.candidates.pop();assert.throws(()=>audit(x),/REQUIRE_EXACTLY_TWO/);
});
test("fail closed on duplicated language",()=>{
  const x=copy();x.candidates[1].locale="vi-VN";assert.throws(()=>audit(x),/DUPLICATE_LANGUAGE/);
});
test("fail closed on fabricated commercial-ready claim",()=>{
  const x=copy();x.candidates[0].readiness="COMMERCIAL_READY";assert.throws(()=>audit(x),/FALSE_CLAIM/);
});
test("fail closed on fabricated audio hash",()=>{
  const x=copy();x.candidates[0].wav_sha256="abc";assert.throws(()=>audit(x),/UNVERIFIED_EVIDENCE/);
});
test("fail closed on faked male timbre QA",()=>{
  const x=copy();x.candidates[1].male_voice_review="PASS";assert.throws(()=>audit(x),/UNVERIFIED_REVIEW/);
});
test("fail closed on faked commercial acceptance",()=>{
  const x=copy();x.candidates[1].commercial_acceptance="APPROVED";assert.throws(()=>audit(x),/COMMERCIAL_NOT_APPROVED/);
});
test("fail closed if voice provenance missing",()=>{
  const x=copy();x.candidates[0].license_evidence="";assert.throws(()=>audit(x),/MISSING_PROVENANCE/);
});
test("fail closed if CI claims network-enabled model download",()=>{
  const x=copy();x.policy.network_in_ci="allow";assert.throws(()=>audit(x),/none/);
});
test("fail closed if owner voice cloning policy altered",()=>{
  const x=copy();x.policy.owner_voice_clone="ALLOWED";assert.throws(()=>audit(x),/FORBIDDEN/);
});
