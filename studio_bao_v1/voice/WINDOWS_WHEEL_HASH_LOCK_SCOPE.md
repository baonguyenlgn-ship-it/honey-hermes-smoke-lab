# Supertonic3 CPU dependencies — Windows CPython 3.12 x64 SHA256 lock

Scope: only isolated GitHub Windows CI on PR #8. Prior inference, Chrome, and five-request resource runs are frozen. Capture wheel SHA256s of the **exact 10 runtime dependencies** observed in successful run #40960164053; enforce `pip --require-hashes --no-index` with local wheelhouse in a separate test installation before declaring integrity PASS. Only built-in Python + pip; no model asset or API speech calls.

A successful wheel lock is **platform-specific** and protects the selected wheel files against alteration for the tested Windows CPython 3.12 build; it does not prove upstream software is malware-free, commercial voice rights, production deployment safety, or availability of all wheels across platforms. Transitive wheels and their SHA256 must be committed into the PR once inspected; never publish packages, voice data, private recordings, secrets, or claims of approved production runtime.

The first Windows benchmark attempt failed in the memory meter, not the model. The repaired run #40960164053 passed five simultaneous short requests with cold load 0.8514s, batch 3.8449s, sum audio 24.0326s, and measured process peak working set 540.55MiB. These are limited synthetic measurements, not capacity or commercial SLA guarantees.
