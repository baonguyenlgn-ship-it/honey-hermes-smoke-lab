# Studio Bảo V1 — Native Vietnamese and Korean listening acceptance protocol

**Status: PREPARED ONLY, not reviewed.** Canonical scope PR #8, generic Supertonic 3 M1 research voice, snapshot `3cadd1ee6394adea1bd021217a0e650ede09a323`. No real person's voice/face. Earlier Windows #40964059913 proved waveform repeatability on identical model/CPU/seed. It did NOT prove intelligible native-language speech.

## Procedure (no listening event is authorized by this document)

Prepare eight **original, non-customer** scripts, four per language: (1) explicit AI-speech disclosure, (2) fruit names, (3) delivery and Korean `택배`, (4) order confirmation. For any future user-authorized review, use an ephemeral, access-controlled, logged listening method with a defined expiry and no downloadable public URL. Only authorized audio that complies with the model's license may be presented, clearly labeled as AI-generated. Reviewers must be independent, native or professionally fluent in the target language and free of conflicts; verify credentials **outside the public repository**, without collecting legal names, phone numbers, email or identity documents in GitHub.

At least **two distinct human reviewers per language** listen independently, without viewing each other's judgments. Record the audible sample's exact SHA-256, script ID and pinned model/runtime/seed; neutral reviewer pseudonyms and attestation (with protected provenance outside GitHub). Require informed listening consent, access approval, no voice file republication, retention rule and deletion confirmation. A rating **must never be generated from a waveform amplitude, ASR alone, a synthetic fixture, or AI self-reported evaluation**.

Score *word intelligibility, pronunciation, prosody, naturalness, male-presenting timbre* separately from 1 (unusable) to 5 (excellent). Write verbatim perceived words/ambiguous phonemes and describe unnatural tone, pauses, accent or wrong fruit/product names. Proposed screening: median >=4 on each criterion, per-sample intelligibility >=4, **zero critical errors** for meaning, products, dates or delivery; disagreement or one critical error escalates to a third independent native rater. This is a candidate-review rubric, **not a commercial release formula**. Rights, consent, disclosure, privacy, legal and production checks remain independent non-bypassable gates.

## Current evidence

`listening_qa_protocol.json` specifies all eight unique original cases and restrictions. `listening_qa_evidence_template.json` is intentionally empty. `listening_qa_gate.js` and negative tests fail closed on fake approval, missing language, altered samples, PII, fake scores, unauthorized audio distribution and lowered reviewer requirements. A CI PASS here means ONLY that the review packet and safeguards were checked. **No human listening, native pronunciation quality, premium MC acceptance or rights review has occurred.**

**Owner action for this step:** none. **Future boundary:** authorization of access to actual audio and independently qualified human reviewers; do not assume consent or recruit/message reviewers without explicit approval. Continue in DEV/TEST only; $0 new paid services, no Production/live/merge.
