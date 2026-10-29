# Supertonic 3 — Bảo V1 VI/KO voice candidate (research-only)

Checked 2026-10-30 KST. Canonical source: https://huggingface.co/Supertone/supertonic-3
Official pinned HF revision: 3cadd1ee6394adea1bd021217a0e650ede09a323
Official model metadata reports ONNX assets (~411.5MB total repository storage), CPU inference, 31 languages including Vietnamese (vi) and Korean (ko); preset male-labelled styles M1–M5.
Separate licenses: example code MIT; ONNX weights BigScience OpenRAIL-M. Not equivalent. Rights require full acceptance, especially if offering AI voice as a service.
Primary model license: https://huggingface.co/Supertone/supertonic-3/blob/3cadd1ee6394adea1bd021217a0e650ede09a323/LICENSE
License section 4 permits hosted third-party access only with notice, reproduction of license, retention of relevant notices and downstream use restrictions. Section 5 / Attachment A bans nonconsensual impersonation, harmful activities, and publishing machine-generated content without intelligible disclosure.
License section 6 claims no model-vendor rights in output except for applicable restrictions; commercial/identity implications still need legal review.
Required ONNX model files, configs and M1-style paths are listed in supertonic3_preflight.json. Full snapshot revision is pinned, but no file SHA256 values are currently measured. No model binary may execute before file-level hashes are verified.
Next permitted phase: first assess model/license/restrictions and CPU cost, then staged download to temporary Windows runner directory with size cap, record model/config/style file SHA, no execution. After integrity checks, separately test VI and KO generic original sentences with M1, run independent byte+native-language pronunciation tests, only accept quality based on real listening and/or verified ASR.
Do NOT use Owner voice/face, custom cloning, untrusted pickle, paid service, live stream, production, or marketing without independent approval.
Current status RESEARCH_ONLY; no inference, no model download, no premium quality or commerce verdict.
