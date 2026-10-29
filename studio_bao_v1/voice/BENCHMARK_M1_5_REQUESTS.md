# Five-request CPU resource benchmark — QA scope

This is **not a commercial throughput or concurrency certification**. Conduct one isolated bounded GitHub-hosted Windows run at exact PR #8 SHA, using the previously SHA-pinned Supertonic3 ONNX snapshot, anonymous M1 style and original short Vietnamese/Korean test phrases.

Metrics: load wall time, process working set (before/after/peak), five concurrently submitted requests, total utterance/audio seconds, wall latency per request and batch, realtime factor, plus non-silent / clipping-safe array measurements. The probe generates waveforms in memory only and records SHA-256 of transient arrays, **no WAV written or published**. Native language pronunciation, timbre, commercial rights, real customer load, and multi-tenant cost remain **NOT_PROVEN**.

Supply-chain caveat: the prior pip entrypoint pins ONNX Runtime 1.23.1 and NumPy 2.2.6, but transitive dependencies are not SHA256-locked; no production runtime acceptance. After measurement, a separate supply-chain hardening job should lock all wheels/hashes and forbid network during inference.

Stop if model hash, Python runtime, memory instrumentation, completion count or QA integrity fails. Jobs already green for EN/VI/KO TTS, Studio Chrome and original M1 WAV remain frozen.
