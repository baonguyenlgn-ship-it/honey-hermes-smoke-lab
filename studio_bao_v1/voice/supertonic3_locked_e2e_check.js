"use strict";
const fs=require("node:fs"),path=require("node:path"),a=require("node:assert/strict"),crypto=require("node:crypto");
const [runtime,voice]=process.argv.slice(2);a.ok(runtime&&voice);
const lock=fs.readFileSync(path.join(__dirname,"requirements-win-py312-hashes.txt"));
const r=JSON.parse(fs.readFileSync(path.join(runtime,"locked-runtime-report.json"),"utf8"));
const s=JSON.parse(fs.readFileSync(path.join(voice,"source-report.json"),"utf8"));
const m=JSON.parse(fs.readFileSync(path.join(voice,"inference.json"),"utf8"));
a.equal(r.status,"HASH_LOCKED_ISOLATED_WINDOWS_VENV_READY");
a.equal(r.original_lock_sha256,crypto.createHash("sha256").update(lock).digest("hex"));
a.equal(r.offline_install_verified,true);a.equal(r.installed_versions_verified,true);
a.equal(s.runtime_lock_sha256,r.original_lock_sha256);
a.equal(s.isolated_runtime_verified,true);
a.equal(s.status,"INFERENCE_EMITTED_NEEDS_INDEPENDENT_QA");
a.equal(s.weight_hashes.length,4);a.equal(s.auxiliary_hashes.length,4);
a.equal(m.results.length,2);a.deepEqual(m.languages,["vi","ko"]);
a.equal(m.commercial_accepted,false);a.equal(m.quality_accepted,false);a.equal(m.native_listener_checked,false);
a.equal(m.owner_identity,false);a.equal(s.commercial_approved,false);
for(const x of m.results){a.match(x.wav_sha256,/^[a-f0-9]{64}$/);a.ok(x.duration_seconds>1&&x.elapsed_seconds>0);}
console.log("ST3_M1_VI_KO_LOCKED_VENV_REAL_WAV_E2E_PASS="+JSON.stringify({
  revision:s.revision,lockSha:r.original_lock_sha256,
  languages:m.results.map(x=>({locale:x.locale,duration:x.duration_seconds,sha256:x.wav_sha256}))}));
console.log("ST3_NO_NATIVE_LISTENING_PREMIUM_IDENTITY_COMMERCIAL_OR_PRODUCTION_ACCEPTANCE");
