"use strict";
/* Drives only the conceptual silhouette from verified LOCAL PCM energy, never phonemes. */
(function(){
 if(typeof document==="undefined")return;
 const mount=()=>{
  const avatar=document.querySelector(".avatar"),mouth=document.getElementById("avatar-mouth"),
    label=document.getElementById("mouth-preview-status"),audio=document.getElementById("local-audio-player");
  if(!avatar||!mouth||!label||!audio)return;
  let env=null,track=null,frame=0;
  const stop=()=>{if(frame){cancelAnimationFrame(frame);frame=0;}};
  const visual=n=>{
   const value=Number.isFinite(n)?Math.max(0,Math.min(1,n)):0;
   avatar.dataset.mouthOpen=value.toFixed(3);
   mouth.style.transform="translateX(-50%) scaleY("+(0.22+value*4.2).toFixed(3)+")";
  };
  const shapes={REST:[0,.22],BMP:[.7,.24],AA:[1.15,3.9],EE:[1.45,1.6],OO:[.65,3.3],FV:[1.2,.52],L:[1.15,2.1]};
  const visualShape=shape=>{
   const pair=shapes[shape]||shapes.REST;
   mouth.dataset.viseme=shape;
   mouth.style.transform="translateX(-50%) scaleX("+pair[0]+") scaleY("+pair[1]+")";
   avatar.dataset.mouthOpen=String(Math.min(1,pair[1]/4));
  };
  const idle=()=>{stop();env=null;track=null;visual(0);mouth.dataset.viseme="REST";mouth.hidden=true;label.textContent="KHẨU HÌNH: CHƯA CÓ WAV · CHƯA LIP-SYNC";};
  const tick=()=>{
   if(!env){visual(0);return;}
   const t=Math.max(0,Math.round(audio.currentTime*1000));
   if(track){
    const shape=BaoVisemeTiming.shapeAt(track,t);
    visualShape(shape);
    label.textContent="VISEME THỦ CÔNG CHƯA KIỂM ĐỊNH · KHÔNG PHẢI LIP-SYNC · "+shape+" · "+String(t)+" ms";
   }else{
    const value=BaoMouthEnergy.valueAt(env,t);
    mouth.dataset.viseme="ENERGY";
    visual(value);
    label.textContent="KHẨU HÌNH THEO ÂM LƯỢNG · KHÔNG PHẢI LIP-SYNC · "+String(t)+" ms";
   }
  };
  const loop=()=>{stop();if(audio.paused||audio.ended||!env)return;tick();frame=requestAnimationFrame(loop);};
  document.addEventListener("honey:local-wav-cleared",idle);
  document.addEventListener("honey:verified-local-wav",event=>{
   stop();idle();
   try{
    if(event.detail?.verified!==true)throw Error("UNVERIFIED_WAV_EVENT");
    const probe=BaoMouthEnergy.envelope(event.detail.wavBytes);
    if(probe.durationMs!==event.detail.durationMs)throw Error("MOUTH_AUDIO_DURATION_MISMATCH");
    env=probe;
    if(event.detail.visemeTrack){
     track=BaoVisemeTiming.verify({track:event.detail.visemeTrack,verifiedAudio:event.detail.verifiedAudio});
     if(track.durationMs!==env.durationMs)throw Error("VISEME_ENERGY_DURATION_MISMATCH");
    }
    mouth.hidden=false;tick();
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
   method:track?.method||env?.method||"NONE",
   viseme:mouth.dataset.viseme||"REST",actualLipSync:false,production:false})};
 };
 document.addEventListener("DOMContentLoaded",mount);
})();
