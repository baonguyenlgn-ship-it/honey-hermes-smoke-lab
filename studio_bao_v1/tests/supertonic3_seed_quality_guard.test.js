"use strict";
const test=require("node:test"),a=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const check=fs.readFileSync(path.join(__dirname,"../voice/supertonic3_seed_quality_check.js"),"utf8");
test("checker must bind to locked runtime",()=>a.match(check,/runtime_lock_sha256/));
test("checker requires identical seeded byte hashes",()=>a.match(check,/a\.equal\(first\.pcm_sha256,second\.pcm_sha256\)/));
test("checker fail-closes false product acceptance",()=>a.match(check,/FALSE_PRODUCT_ACCEPTANCE/));
test("checker rejects dangerous waveform peak",()=>a.match(check,/near_fullscale_fraction<=\.01/));
test("checker rejects leaked wav",()=>a.match(check,/AUDIO_OR_BINARY_MUST_NOT_BE_PUBLISHED/));
