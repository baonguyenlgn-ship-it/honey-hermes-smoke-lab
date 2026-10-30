"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const root=process.argv[2];assert.ok(root,"METADATA_DIRECTORY_REQUIRED");
const report=JSON.parse(fs.readFileSync(path.join(root,"st3-hashes.json"),"utf8"));
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,"supertonic3_official_digests.json"),"utf8"));
assert.equal(report.status,"FOUR_ONNX_BYTES_SHA_VERIFIED");
assert.equal(report.revision,manifest.revision);
assert.equal(report.executed,false);assert.equal(report.audio,false);
assert.equal(report.commercial,false);
assert.equal(report.files.length,4);
assert.equal(manifest.assets.length,4);
assert.ok(report.bytes>390000000 && report.bytes<470000000,"MODEL_BYTES_LIMIT");
let total=0;const seen=new Set();
for(const a of report.files) {
  assert.ok(!seen.has(a.path),"DUPLICATE_HASH");seen.add(a.path);
  const upstream=manifest.assets.find(x=>x.path===a.path);
  assert.ok(upstream,"UNEXPECTED_MODEL");
  assert.equal(a.sha256,upstream.sha256,"SHA256_NOT_EQUAL");
  assert.equal(a.match,true);
  assert.ok(a.bytes>0&&a.bytes<=upstream.max_bytes);total+=a.bytes;
}
assert.equal(total,report.bytes);
for(const entry of fs.readdirSync(root))assert.ok(!entry.endsWith(".onnx"),"MODEL_BINARY_NOT_REMOVED");
console.log("SUPER3_INDEPENDENT_HASH_AUDIT_PASS="+JSON.stringify({count:seen.size,bytes:total}));
console.log("SUPER3_NO_RUNTIME_NO_VOICE_NO_LICENSE_APPROVAL");
