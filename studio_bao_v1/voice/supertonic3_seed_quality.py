"""Pinned M1 VI/KO seeded repeatability + bounded waveform quality research.
No file audio, no cloud inference, no identity cloning, no claims about pronunciation.
"""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
from st3_helper_pinned import load_text_to_speech,load_voice_style

model=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
assert sys.platform=="win32" and sys.version_info[:2]==(3,12),"WINDOWS_PY312_REQUIRED"
seed_base=20261030
samples=[
  ("vi","Xin chào. Đây là bản thử giọng tiếng Việt của Honey.",seed_base+101),
  ("ko","안녕하세요. 허니 스튜디오의 한국어 음성 시험입니다.",seed_base+202),
]
start=time.perf_counter()
tts=load_text_to_speech(str(model/"onnx"),use_gpu=False)
voice=load_voice_style([str(model/"voice_styles"/"M1.json")])
load_elapsed=time.perf_counter()-start
runs=[]
for lang,text,seed in samples:
    samples_here=[]
    for trial in range(2):
        np.random.seed(seed)
        t0=time.perf_counter()
        wave,_=tts(text,lang,voice,total_step=5,speed=1.05)
        elapsed=time.perf_counter()-t0
        arr=np.asarray(wave,dtype=np.float32).reshape(-1)
        if arr.size<tts.sample_rate or arr.size>tts.sample_rate*25 or not np.isfinite(arr).all():
            raise AssertionError("AUDIO_LENGTH_OR_NONFINITE")
        abs_wave=np.abs(arr)
        fullscale=float(np.mean(abs_wave>=1.0))
        near_max=float(np.mean(abs_wave>=0.98))
        rms=float(np.sqrt(np.mean(arr*arr)))
        dc=float(np.mean(arr))
        peak=float(np.max(abs_wave))
        activity=float(np.mean(abs_wave>=0.015))
        # Avoid a new WAV artifact. Audio bytes exist only in the Python process.
        clipped=np.clip(arr,-1.0,1.0)
        pcm=(clipped*32767).astype("<i2").tobytes()
        digest=hashlib.sha256(pcm).hexdigest()
        if rms<0.002 or peak<0.02 or activity<0.05:
            raise AssertionError("WAVEFORM_TOO_QUIET_OR_INACTIVE")
        if fullscale>0.001 or near_max>0.01:
            raise AssertionError("WAVEFORM_CLIPPING_LIMIT")
        if abs(dc)>0.04:raise AssertionError("WAVEFORM_DC_OFFSET_LIMIT")
        samples_here.append({
            "trial":trial+1,"seed":seed,"pcm_sha256":digest,
            "samples":int(arr.size),"duration_seconds":round(arr.size/tts.sample_rate,4),
            "elapsed_seconds":round(elapsed,4),
            "rms":round(rms,6),"peak":round(peak,6),
            "dc_offset":round(dc,6),
            "near_fullscale_fraction":round(near_max,7),
            "fullscale_fraction":round(fullscale,7),
            "activity_fraction":round(activity,5)
        })
    same=(samples_here[0]["pcm_sha256"]==samples_here[1]["pcm_sha256"]
          and samples_here[0]["samples"]==samples_here[1]["samples"])
    runs.append({"language":lang,"text_characters":len(text),"trials":samples_here,
                 "seeded_pcm_identical":same})
    print("ST3_SEED_REPETITION",lang,"identical",same,
          "sha",samples_here[0]["pcm_sha256"],flush=True)
    if not same:raise AssertionError("SEEDED_REPRODUCIBILITY_FAILED_"+lang)
report={
  "schema":"honey.st3-seeded-waveform-repro-v1",
  "status":"SEEDED_VI_KO_TWO_RUNS_IDENTICAL_WAVEFORM_QA",
  "model_revision":"3cadd1ee6394adea1bd021217a0e650ede09a323",
  "voice":"M1 generic preset","seed_base":seed_base,
  "load_seconds":round(load_elapsed,4),"sample_rate":int(tts.sample_rate),
  "language_results":runs,"total_trials":sum(len(x["trials"]) for x in runs),
  "pcm_wav_files_written":False,
  "native_listener_pass":False,"male_premium_quality_pass":False,
  "output_commercial_use_approved":False,"owner_persona_or_cloned_voice":False,
  "live_stream_or_production_approved":False,
  "reproducibility_scope":"identical seed+model+process+machine+libraries only; cross-host not tested"
}
(out/"seed-quality-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("ST3_SEEDED_QUALITY_REPORT_CREATED",flush=True)
