"use strict";
// Offline only. This is a truthful evidence/claim gate, NOT a TTS or license certification.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const registryFile = path.join(__dirname, "candidates.json");
const locales = new Set(["vi-VN", "ko-KR"]);
const engines = new Set(["Piper", "MeloTTS"]);
function audit(registry) {
  assert.equal(registry.schema, "honey.offline-voice-candidates.v1");
  assert.equal(registry.policy.network_in_ci, "none");
  assert.equal(registry.policy.commercial_use, "BLOCKED_UNTIL_INDEPENDENT_REVIEW");
  assert.equal(registry.policy.owner_voice_clone, "FORBIDDEN");
  assert.equal(registry.policy.asset_publication, "FORBIDDEN");
  assert.ok(Array.isArray(registry.candidates));
  assert.equal(registry.candidates.length, 2, "REQUIRE_EXACTLY_TWO_LANGUAGE_CANDIDATES");
  const ids = new Set(), seen = new Set();
  for (const c of registry.candidates) {
    assert.match(c.id, /^[a-z][a-z0-9-]{5,64}$/);
    assert.ok(!ids.has(c.id), "DUPLICATE_VOICE_CANDIDATE");
    ids.add(c.id);
    assert.ok(locales.has(c.locale), "UNEXPECTED_LANGUAGE");
    assert.ok(!seen.has(c.locale), "DUPLICATE_LANGUAGE");
    seen.add(c.locale);
    assert.ok(engines.has(c.engine), "UNKNOWN_ENGINE");
    for (const field of ["research_source", "license_evidence"]) {
      assert.ok(typeof c[field] === "string" && /^https:\/\//.test(c[field]), "MISSING_PROVENANCE_" + field);
    }
    assert.ok(typeof c.public_license_signal === "string" && c.public_license_signal.length >= 35, "MISSING_LICENSE_CAVEAT");
    assert.equal(c.readiness, "RESEARCH_ONLY", "FALSE_CLAIM_OF_AUDIO_OR_COMMERCIAL_READINESS");
    for (const field of ["model_sha256", "runtime_sha256", "config_sha256", "wav_sha256", "windows_run_id"]) {
      assert.equal(c[field], null, "UNVERIFIED_EVIDENCE_MUST_BE_NULL_" + field);
    }
    for (const field of ["source_and_dependency_rights_review", "male_voice_review", "native_language_quality_review"]) {
      assert.equal(c[field], "PENDING", "UNVERIFIED_REVIEW_MUST_BE_PENDING_" + field);
    }
    assert.equal(c.commercial_acceptance, "BLOCKED", "COMMERCIAL_NOT_APPROVED");
  }
  assert.ok(seen.has("vi-VN") && seen.has("ko-KR"), "MISSING_LANGUAGE");
  return {passed:true,candidates:registry.candidates.map(c => ({id:c.id,locale:c.locale,readiness:"RESEARCH_ONLY",audio:"NOT_PROVEN",commercial:"NOT_ACCEPTED"}))};
}
if (require.main === module) {
  const result = audit(JSON.parse(fs.readFileSync(registryFile, "utf8")));
  console.log("VI_KO_CANDIDATE_EVIDENCE_GATE_PASS");
  console.log(JSON.stringify(result));
  console.log("NO_MODEL_DOWNLOADED_NO_WAV_GENERATED_NO_COMMERCIAL_CLEARANCE");
}
module.exports = {audit};
