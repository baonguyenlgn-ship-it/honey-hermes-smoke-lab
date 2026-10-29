"use strict";
/* Drives only the conceptual silhouette from verified LOCAL PCM energy, never phonemes. */
(function(){
 if(typeof document==="undefined")return;
 const mount=()=>{
  const avatar=document.querySelector(".avatar"),mouth=document.getElementById("avatar-mouth"),
    label=document.getElementById("mouth-preview-status"),audio=document.getElementById("local-audio-player");
  if(!avatar||!mouth||!label||!audio)return;
  let env=null,frame=0;
  const stop=()=>{if(frame){cancelAnimationFrame(frame);frame=0;}};
  const visual=n=>{
   const value=Number.isFinite(n)?Math.max(0,Math.min(1,n)):0;
   avatar.dataset.mouthOpen=value.toFixed(3);
   mouth.style.transform="translateX(-50%) scaleY("+(0.22+value*4.2).toFixed(3)+")";
  };
  const idle=()=>{stop();env=null;visual(0);mouth.hidden=true;label.textContent="KHẨU HÌNH: CHƯA CÓ WAV · CHƯA LIP-SYNC";};
  const tick=()=>{
   if(!env){visual(0);return;}
   const t=Math.max(0,Math.round(audio.currentTime*1000));
   const value=BaoMouthEnergy.valueAt(env,t);
   visual(value);
   label.textContent="KHẨU HÌNH THEO ÂM LƯỢNG · KHÔNG PHẢI LIP-SYNC · "+String(Math.round(t))+" ms";
  };
  const loop=()=>{stop();if(audio.paused||audio.ended||!env)return;tick();frame=requestAnimationFrame(loop);};
  document.addEventListener("honey:local-wav-cleared",idle);
  document.addEventListener("honey:verified-local-wav",event=>{
   stop();idle();
   try{
    if(event.detail?.verified!==true)throw Error("UNVERIFIED_WAV_EVENT");
    const probe=BaoMouthEnergy.envelope(event.detail.wavBytes);
    if(probe.durationMs!==event.detail.durationMs)throw Error("MOUTH_AUDIO_DURATION_MISMATCH");
    env=probe;mouth.hidden=false;tick();
   }catch(e){
    idle();label.textContent="KHẨU HÌNH ĐÃ CHẶN: "+String(e.message||e).slice(0,44);
   }
  });
  for(const e of ["timeupdate","seeked"])audio.addEventListener(e,tick);
  audio.addEventListener("play",loop);
  for(const e of ["pause","ended"])audio.addEventListener(e,()=>{stop();tick();});
  idle();
  globalThis.HoneyMouthPreview={snapshot:()=>({
   ready:!!env,open:Number(avatar.dataset.mouthOpen),bins:env?.open.length||0,
   method:env?.method||"NONE",actualLipSync:false,production:false})};
 };
 document.addEventListener("DOMContentLoaded",mount);
})();
