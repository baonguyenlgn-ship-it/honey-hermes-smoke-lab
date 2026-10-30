# Independent test-of-tests for seeded M1 VI/KO waveform gate
2026-10-30, PR #8 only.

The last Windows run #40964059913 PASS proved deterministic seeded **in-process** PCM16 SHA equality for two VI and two KO trials, plus amplitude/clip/DC checks, using the verified hash-locked Windows Python/ONNX model. The prior CI included only five source-level guard assertions, not adversarial black-box checks.

This follow-up adds a **cheap, no-model, no-WAV** test using synthetic *structurally valid report fixtures* and invokes the actual independent CLI checker with a fresh temp directory. One baseline must PASS. Thirteen separate tampered reports must be REJECTED, covering mismatched sample SHA/length, clipping, DC bias, false quality/commercial acceptance, altered runtime SHA, missing weights/language and claimed WAV publication. Do not infer speech quality from this report-fixture test: it only proves the acceptance checker is fail-closed against these tamper classes.

Prior heavy seeded and locked-runtime successes are frozen. No paid inference, Production, external publication, voice identity or customer data.
