# Honey Studio Bảo V1 — private local-review station

Scope: isolated PR #8 DEV/TEST only. This is preparation, not permission to invite reviewers. No actual human listening, media upload, commercial approval or deployment occurred.

Station: studio_bao_v1/reviewer/review_station.html. It displays four original VI or four KO protocol phrases, requires a local session attestation and non-PII pseudonym, allows user-selected WAV for each phrase, requires playback and five numerical scores, and records standardized critical-error and remark codes. It checks RIFF/WAVE PCM16 mono 44.1kHz up to 25 MiB, computes WAV SHA256 locally via WebCrypto, and plays only through a browser object URL. Manual listening tick is not independent proof of a real person listening. Only after all four are complete may the user manually download a JSON file. It contains no WAV.

Browser CSP rejects outbound network connections, subresources, form submissions and embeds; there are no network fetches, analytics, persistent browser storage or automatic uploads. Reset drops scores and file references, revoking object URLs. A JSON the reviewer explicitly downloads remains on their local computer and requires controlled retention. A browser cannot verify real Owner consent or independently establish a secure operating environment; external authorization remains required before any real listening.

Contribution format: honey.st3-local-reviewer-contribution.v1, status LOCAL_SELF_ATTESTED_UNVERIFIED, always false external identity/consent/human signoff/commercial release fields. One reviewer only, four samples in exactly one language, each WAV SHA and bounded numerical scores. No free-text, phone, email or legal names collected. This is not a real human verification, not complete 2-reviewer-per-language acceptance. Existing listening_score_gate.js and legal review remain NOT_PROVEN.

Windows acceptance: Node adversarial WAV/score/schema/privacy unit tests and actual Chrome desktop/mobile navigation using fake ephemeral synthetic tones (no human voices), local-only JSON downloads, reset and zero HTTP(S) outbound. No model inference or publication, no paid API.

NEXT SAFE STEP: after Owner separately authorizes controlled access to actual samples and independent native reviewer engagement, external reviewers can use a properly secured machine and provide protected metadata for independent verification. Until then: NO third-party outreach, no WAV distribution, no Production, merge, live or commercial release.
