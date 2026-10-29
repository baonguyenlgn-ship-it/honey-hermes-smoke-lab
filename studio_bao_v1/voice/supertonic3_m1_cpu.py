# Pinned upstream MIT helper: source commit 1e9799e964ea4c0dad7cde993b65c3c813a7b373
# Local, anonymous pre-set M1. No voice cloning, no cloud calls, no model auto-download.
import hashlib,json,sys,time,wave
from pathlib import Path
import numpy as np
from st3_helper_pinned import load_text_to_speech,load_voice_style
model=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
start=time.perf_counter()
tts=load_text_to_speech(str(model/'onnx'),use_gpu=False)
style=load_voice_style([str(model/'voice_styles'/'M1.json')])
results=[]
texts=[('vi','Xin chào. Đây là bản thử giọng tiếng Việt của Honey.'),('ko','안녕하세요. 허니 스튜디오의 한국어 음성 시험입니다.')]
for lang,sentence in texts:
    begin=time.perf_counter()
    audio,seconds=tts(sentence,lang,style,total_step=5,speed=1.05)
    arr=np.asarray(audio,dtype=np.float32).reshape(-1)
    if arr.size<16000 or arr.size>tts.sample_rate*25 or not np.isfinite(arr).all(): raise ValueError('AUDIO_ARRAY_INVALID')
    if np.max(np.abs(arr))<0.01: raise ValueError('SILENT_AUDIO')
    raw=np.clip(arr,-1,1)
    pcm=(raw*32767).astype('<i2').tobytes()
    wavfile=out/('st3-m1-'+lang+'.wav')
    with wave.open(str(wavfile),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(tts.sample_rate);w.writeframes(pcm)
    digest=hashlib.sha256(wavfile.read_bytes()).hexdigest()
    duration=arr.size/tts.sample_rate
    elapsed=time.perf_counter()-begin
    results.append(dict(locale=lang,text=sentence,wav_sha256=digest,wav_bytes=wavfile.stat().st_size,duration_seconds=round(duration,3),elapsed_seconds=round(elapsed,3),realtime_factor=round(elapsed/duration,3)))
    print('SUPER3_CPU_WAV_EMITTED',lang,round(duration,2),'seconds',digest,flush=True)
report=dict(engine='Supertonic 3 ONNX',voice='M1 generic preset',languages=['vi','ko'],results=results,total_seconds=round(time.perf_counter()-start,3),sample_rate=tts.sample_rate,quality_accepted=False,native_listener_checked=False,commercial_accepted=False,owner_identity=False)
(out/'inference.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
