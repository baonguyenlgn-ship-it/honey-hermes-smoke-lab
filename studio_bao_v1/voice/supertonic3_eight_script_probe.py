"""Eight original VI/KO reviewer-script Supertonic M1 CPU feasibility.
Only ephemeral in-memory audio; no WAV, no review contact, no public audio.
"""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
from st3_helper_pinned import load_text_to_speech,load_voice_style

model=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
protocol=json.loads((Path(__file__).parent/"listening_qa_protocol.json").read_text(encoding="utf8"))
assert sys.platform=="win32" and sys.version_info[:2]==(3,12),"LOCKED_WINDOWS_ONLY"
assert protocol["schema"]=="honey.st3-native-listening-protocol.v1"
assert len(protocol["samples"])==8
assert protocol["source"]["revision"]=="3cadd1ee6394adea1bd021217a0e650ede09a323"
start=time.perf_counter()
tts=load_text_to_speech(str(model/"onnx"),use_gpu=False)
voice=load_voice_style([str(model/"voice_styles"/"M1.json")])
load_seconds=time.perf_counter()-start
items=[]
for s in protocol["samples"]:
    assert s["locale"] in ("vi","ko")
    seed=int(s["seed"])
    np.random.seed(seed)
    begun=time.perf_counter()
    waveform,_=tts(s["text"],s["locale"],voice,total_step=5,speed=1.05)
    synthesis_seconds=time.perf_counter()-begun
    arr=np.asarray(waveform,dtype=np.float32).reshape(-1)
    sr=int(tts.sample_rate)
    if not 0.8*sr<arr.size<30*sr or not np.isfinite(arr).all():
        raise AssertionError("INVALID_WAVEFORM_LENGTH_OR_NAN_"+s["id"])
    abs_arr=np.abs(arr)
    rms=float(np.sqrt(np.mean(arr*arr)))
    peak=float(np.max(abs_arr))
    dc=float(np.mean(arr))
    near=float(np.mean(abs_arr>=0.98))
    clip=float(np.mean(abs_arr>=1.0))
    active=float(np.mean(abs_arr>=0.015))
    if rms<=0.002 or peak<=0.02 or active<=0.025:
        raise AssertionError("AUDIO_SILENCE_OR_UNDERPOWER_"+s["id"])
    if clip>0.001 or near>0.01 or abs(dc)>0.04:
        raise AssertionError("AUDIO_DISTORTION_OR_DC_"+s["id"])
    pcm=(np.clip(arr,-1,1)*32767).astype("<i2").tobytes()
    item={
        "id":s["id"],"locale":s["locale"],"seed":seed,
        "text_sha256":hashlib.sha256(s["text"].encode("utf8")).hexdigest(),
        "pcm_sha256":hashlib.sha256(pcm).hexdigest(),
        "duration_seconds":round(arr.size/sr,4),
        "synthesis_seconds":round(synthesis_seconds,4),
        "rms":round(rms,6),"peak":round(peak,6),"dc_offset":round(dc,6),
        "near_fullscale_fraction":round(near,7),
        "fullscale_fraction":round(clip,7),"activity_fraction":round(active,5)
    }
    items.append(item)
    print("ST3_NATIVE_SCRIPT_CPU_PROOF",item["id"],item["locale"],
          item["duration_seconds"],item["pcm_sha256"],flush=True)
report={
    "schema":"honey.st3-eight-script-in-memory-feasibility.v1",
    "status":"EIGHT_GENERIC_SCRIPT_SIGNALS_GENERATED_NOT_HUMAN_APPROVED",
    "model_revision":protocol["source"]["revision"],
    "voice":"M1 generic preset","sample_rate":int(tts.sample_rate),
    "model_load_seconds":round(load_seconds,4),
    "total_script_count":len(items),
    "scripts":items,"wav_files_written":False,"model_audio_published":False,
    "native_vi_listening_verified":False,"native_ko_listening_verified":False,
    "legal_commercial_release_authorized":False,"production_authorized":False
}
(out/"eight-script-signal-qa.json").write_text(
  json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print("ST3_EIGHT_SCRIPT_IN_MEMORY_REPORT_PREPARED",flush=True)
