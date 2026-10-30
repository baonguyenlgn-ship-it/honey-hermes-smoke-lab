"use strict";
const fs=require("node:fs"),path=require("node:path"),a=require("node:assert/strict");
const folder=process.argv[2];a.ok(folder&&fs.existsSync(folder));
const r=JSON.parse(fs.readFileSync(path.join(folder,"wheel-lock-report.json"),"utf8"));
const lock=fs.readFileSync(path.join(folder,"requirements-win-py312-hashes.txt"),"utf8");
const expected={onnxruntime:"1.23.1",numpy:"2.2.6",coloredlogs:"15.0.1",flatbuffers:"25.12.19",
  humanfriendly:"10.0",mpmath:"1.3.0",protobuf:"7.36.2",pyreadline3:"3.5.6",sympy:"1.14.0",packaging:"26.3"};
a.equal(r.schema,"honey.m1-windows-wheel-hash-lock.v1");
a.equal(r.status,"WINDOWS_WHEEL_HASH_LOCK_OFFLINE_INSTALL_VERIFIED");
a.equal(r.python_runtime.startsWith("3.12."),true);
a.equal(r.platform,"win32");
a.equal(r.package_count_expected,10);
a.equal(r.wheel_count,10);a.equal(r.wheel_hashes.length,10);
a.ok(r.total_wheel_bytes>30000000&&r.total_wheel_bytes<=65000000);
a.equal(r.fully_offline_install_pass,true);
a.equal(r.production_supply_chain_approved,false);
a.equal(r.model_or_audio_executed,false);
a.equal(r.wheels_discarded,true);
const lines=lock.trim().split(/\r?\n/),seen=new Set();
const committedLock=fs.readFileSync(path.join(__dirname,"requirements-win-py312-hashes.txt"),"utf8")
  .trim().split(/\r?\n/);
a.deepEqual(lines,committedLock,"GENERATED_LOCK_DIFFERS_FROM_COMMITTED_SHA256_PINS");
a.equal(lines.length,10);
let sum=0;
for(const w of r.wheel_hashes){
  a.ok(expected[w.name]===w.version,"UNEXPECTED_DEPENDENCY_VERSION");
  a.ok(!seen.has(w.name),"DUPLICATE_DEPENDENCY");
  seen.add(w.name);
  a.match(w.sha256,/^[a-f0-9]{64}$/);
  a.ok(w.bytes>0&&w.bytes<25000000);
  a.ok(w.filename.endsWith(".whl"));
  sum+=w.bytes;
  a.ok(lines.includes(w.name+"=="+w.version+" --hash=sha256:"+w.sha256),"HASH_LOCK_LINE_MISSING");
}
a.equal(sum,r.total_wheel_bytes);
a.ok(!fs.existsSync(path.join(folder,"wheelhouse")),"WHEEL_BYTES_WERE_RETAINED");
a.ok(!fs.existsSync(path.join(folder,"installed-target")),"UNNECESSARY_INSTALLED_WHEELS_RETAINED");
console.log("HONEY_WINDOWS_PY312_TRANSITIVE_WHEEL_HASH_LOCK_PASS="+JSON.stringify({
 packages:seen.size,wheelBytes:r.total_wheel_bytes,offlineInstall:r.fully_offline_install_pass}));
console.log("HONEY_WHEEL_LOCK_PLATFORM_SPECIFIC_NO_PRODUCT_RELEASE_APPROVAL");
