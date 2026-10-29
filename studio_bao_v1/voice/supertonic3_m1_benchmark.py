"""Honey isolated 5-request concurrency feasibility. No audio files, no owner impersonation."""
import concurrent.futures, hashlib, importlib.metadata, json, os, sys, time
from pathlib import Path
import numpy as np
from st3_helper_pinned import load_text_to_speech, load_voice_style
from win_process_memory import working_memory

assert sys.platform == "win32", "WINDOWS_ONLY"
model=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
MAX_WORKERS=5
texts=[
 ("vi","Xin chào! Đây là thử nghiệm giọng nói nhân tạo."),
 ("ko","안녕하세요! 인공지능 음성 시험입니다."),
 ("vi","Hôm nay chúng tôi giới thiệu trái xoài tươi."),
 ("ko","상품 정보는 주문 전에 확인해 주세요."),
 ("vi","Vui lòng xác nhận thời gian giao hàng trước khi đặt mua.")
]
start=time.perf_counter()
before=working_memory()
tts=load_text_to_speech(str(model/"onnx"),use_gpu=False)
style=load_voice_style([str(model/"voice_styles"/"M1.json")])
load_seconds=time.perf_counter()-start
after_load=working_memory()
print("ST3_COLD_LOAD_SECONDS",round(load_seconds,3),flush=True)
def one(idx,language,text):
    begin=time.perf_counter()
    audio,_=tts(text,language,style,total_step=5,speed=1.05)
    a=np.asarray(audio,dtype=np.float32).reshape(-1)
    if a.size<10000 or a.size>tts.sample_rate*25 or not np.isfinite(a).all():
        raise AssertionError("INVALID_AUDIO_ARRAY")
    peak=float(np.max(np.abs(a)))
    rms=float(np.sqrt(np.mean(a*a)))
    fullscale=float(np.mean(np.abs(a)>=1.0))
    if peak<.005 or rms<.002 or fullscale>.02:
        raise AssertionError("SILENT_OR_HEAVILY_CLIPPED_ARRAY")
    duration=float(a.size/tts.sample_rate)
    wall=time.perf_counter()-begin
    # Digest only, never persist audio arrays or voice recordings.
    digest=hashlib.sha256(a.tobytes()).hexdigest()
    return {"request_id":idx,"language":language,"text_character_count":len(text),
            "speech_seconds":round(duration,4),"wall_seconds":round(wall,4),
            "realtime_factor":round(wall/duration,4),
            "rms":round(rms,5),"peak":round(peak,5),
            "clip_fraction":round(fullscale,6),"ephemeral_array_sha256":digest}
batch_start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS,thread_name_prefix="honey-m1-lab") as executor:
    futures=[executor.submit(one,i,lang,text) for i,(lang,text) in enumerate(texts)]
    # Use bounded future waits; do not claim success if 5 requests cannot all complete.
    results=[future.result(timeout=100) for future in futures]
batch_elapsed=time.perf_counter()-batch_start
after=working_memory()
speech=sum(x["speech_seconds"] for x in results)
print("ST3_CONCURRENT_FIVE_COMPLETED",len(results),round(batch_elapsed,3),
      "peak_MB",round(after["peak_working_set_bytes"]/1048576,2),flush=True)
report={
 "schema":"honey.supertonic3-bounded-cpu-load.v1",
 "model_revision":"3cadd1ee6394adea1bd021217a0e650ede09a323",
 "voice":"M1 generic preset",
 "platform":"windows-latest CPU",
 "languages":["vi","ko"],
 "requested_concurrency":5,
 "completed_count":len(results),
 "model_load_seconds":round(load_seconds,4),
 "batch_wall_seconds":round(batch_elapsed,4),
 "speech_seconds_total":round(speech,4),
 "aggregate_audio_per_wall_ratio":round(speech/batch_elapsed,4),
 "memory_before":before,"memory_after_load":after_load,"memory_after_concurrent":after,
 "requests":results,
 "runtime_versions":{"python":sys.version.split()[0],
   "onnxruntime":importlib.metadata.version("onnxruntime"),
   "numpy":importlib.metadata.version("numpy"),
   "wheel_transitive_sha_locked":False},
 "audio_artifacts_written":False,
 "voice_identity":"UNAFFILIATED_GENERIC_PRESET",
 "native_listener_pronunciation_pass":False,
 "male_premium_quality_pass":False,
 "rights_approved_for_commercial_use":False,
 "real_customer_load_verified":False,
 "production_approved":False,
 "conclusion":"RESOURCE_MEASUREMENT_ONLY_NOT_PRODUCT_ACCEPTANCE"}
(out/"benchmark.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("ST3_CPU_5_REQUEST_BENCHMARK_RECORDED",flush=True)
