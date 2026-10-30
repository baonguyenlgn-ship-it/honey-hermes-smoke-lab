# Offline reviewer contribution merge — no media and no human verification

Run only in an Owner-authorized secure local environment after actual reviewer interactions are separately permitted. This CLI does not host audio, contact people, or obtain identity/consent evidence.

Input: exactly four local JSON contributions exported by the private browser review station, two unique pseudonyms per language (VI and KO), each covering four original scripts. All inputs must match pinned revision, script set/hash, eight per-sample WAV SHA digests, and allowed numerical/critical-error fields. It refuses same person pseudonym reused, missing samples, different bytes per two reviewers for the same phrase, a WAV reused for distinct phrases, fake rights signoff, unknown keys or model drift.

Usage: node studio_bao_v1/reviewer/review_station_merge.js [--simulation] r1.json r2.json r3.json r4.json new-result.json

This writes a **new** local JSON report (never overwrites an existing file) containing metadata only, existing score-gate output and provenance marked NOT VERIFIED. Simulation flag marks synthetic UI fixtures and can NEVER become genuine human evidence. In non-simulation mode a complete high-scoring packet is only SCREENING_ELIGIBLE_NEEDS_EXTERNAL_ATTESTATION. It does not certify reviewers' identities, qualifications or independence, audio origin, informed consent, model commercial rights, or release. All of those need independent authenticated evidence and Owner authorization outside this LAB.

Do not upload real sample audio, reviewer private identities or contribution files into a public repo. No network dependency, paid TTS, production, customer messaging or automatic deployment.
