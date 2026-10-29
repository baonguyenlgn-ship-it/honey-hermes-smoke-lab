"use strict";
(function(){
const p=globalThis.HoneyReviewProtocol,c=globalThis.HoneyReviewCore;
const q=id=>document.getElementById(id);
const session=q("session-authorized"),locale=q("locale"),reviewer=q("reviewer");
const list=q("sample-list"),exportBtn=q("export"),reset=q("reset"),info=q("export-status");
const progress=q("progress"),bar=q("progress-bar"),badge=q("overall-status");
const LBL={word_intelligibility:"Độ rõ từ · 명료도",pronunciation:"Phát âm · 발음",
 prosody:"Ngữ điệu · 억양",naturalness:"Tự nhiên · 자연스러움",
 male_presenting_timbre:"Cảm nhận giọng nam · 남성 음색"};
const TOPICS={ai_disclosure:"Thông báo giọng AI · AI 음성 알림",
 fruit_names:"Tên trái cây · 과일명",delivery:"Giao hàng · 배송",
 confirmation:"Xác nhận đơn · 주문 확인"};
let rows={},hash="";
function el(tag,cl,text){const e=document.createElement(tag);if(cl)e.className=cl;if(text!==undefined)e.textContent=text;return e;}
function forget(){
 for(const row of Object.values(rows)){if(row.url)URL.revokeObjectURL(row.url);}
 rows={};
 exportBtn.disabled=true;info.textContent="Chưa đủ dữ liệu nghe, SHA và điểm chấm.";
}
function setStatus(e,msg,cl){e.textContent=msg;e.className="state"+(cl?" "+cl:"");}
function update(){
 const items=p.samples.filter(x=>x.locale===locale.value);
 const complete=items.filter(s=>{
  const r=rows[s.id];return !!(r?.listened&&r?.ended&&r?.audioSha256&&c.DIMS.every(k=>Number.isInteger(r.scores[k])&&r.scores[k]>=1&&r.scores[k]<=5));
 }).length;
 progress.textContent=complete+" / 4";bar.style.width=String(complete*25)+"%";
 exportBtn.disabled=!(session.checked&&hash&&c.safeReviewerId(reviewer.value.trim())&&complete===4);
 badge.textContent="CHƯA NGHIỆM THU · NOT PROVEN";
}
function makeSelect(options,initial){const s=el("select");for(const [value,label] of options){const o=document.createElement("option");o.value=value;o.textContent=label;s.append(o);}s.value=initial;return s;}
function sampleCard(s){
 const row={scores:{},errors:[],remark:"NONE",audioSha256:null,ended:false,listened:false,url:null};rows[s.id]=row;
 const card=el("article","card");
 const id=el("div","id",s.id+" · "+TOPICS[s.domain]);const title=el("h3","",s.locale==="vi"?"Mẫu giọng Việt":"한국어 음성 샘플");
 const sentence=el("div","text-sample",s.text);
 const input=el("input");input.type="file";input.accept=".wav,audio/wav,audio/x-wav";input.disabled=!session.checked;input.setAttribute("aria-label","Chọn WAV cục bộ cho "+s.id);
 const fileRow=el("div","file-row");fileRow.append(input);
 const status=el("div","state","Chưa có WAV cục bộ · 로컬 음성 없음");
 const audio=el("audio");audio.controls=true;audio.preload="none";audio.hidden=true;audio.setAttribute("aria-label","Nghe "+s.id);
 const digest=el("div","digest","SHA-256: chưa có");
 const ratingWrap=el("div","ratings");
 for(const field of c.DIMS){
  const l=el("label","rating",LBL[field]);
  const select=makeSelect([["","—"],...[1,2,3,4,5].map(n=>[String(n),n+"/5"])],"");
  select.disabled=true;select.setAttribute("aria-label",field+" "+s.id);
  select.addEventListener("change",()=>{row.scores[field]=select.value?Number(select.value):null;update();});
  l.append(select);ratingWrap.append(l);
  row[field+"Element"]=select;
 }
 const extras=el("div","extras");
 const errorLabel=el("label","", "Lỗi nghiêm trọng / 주요 오류");
 const err=makeSelect([["","Không có · 없음"],...c.ERRORS.map(e=>[e,e])],"");err.disabled=true;
 err.addEventListener("change",()=>{row.errors=err.value?[err.value]:[];update();});
 errorLabel.append(err);
 const remarkLabel=el("label","", "Nhận xét dạng mã / 코멘트");
 const remark=makeSelect(c.REMARKS.map(e=>[e,e]),"NONE");remark.disabled=true;
 remark.addEventListener("change",()=>{row.remark=remark.value;update();});
 remarkLabel.append(remark);extras.append(errorLabel,remarkLabel);
 const att=el("label","listened");
 const done=el("input");done.type="checkbox";done.disabled=true;
 att.append(done,el("span","", "Tôi đã nghe hết mẫu và tự chấm điểm · 끝까지 들었습니다"));
 const resetRow=()=>{
  if(row.url){URL.revokeObjectURL(row.url);row.url=null;}
  row.audioSha256=null;row.ended=false;row.listened=false;row.scores={};row.errors=[];row.remark="NONE";
  audio.pause();audio.removeAttribute("src");audio.hidden=true;done.checked=false;done.disabled=true;
  err.value="";err.disabled=true;remark.value="NONE";remark.disabled=true;
  for(const k of c.DIMS){row[k+"Element"].value="";row[k+"Element"].disabled=true;}
  digest.textContent="SHA-256: chưa có";update();
 };
 input.addEventListener("change",async()=>{
  resetRow();
  const file=input.files?.[0];
  if(!file)return;
  setStatus(status,"Đang kiểm tra WAV cục bộ…");
  try{
   if(!session.checked)throw Error("SESSION_NOT_AUTHORIZED");
   if(!globalThis.crypto?.subtle)throw Error("LOCAL_SHA256_UNAVAILABLE");
   if(file.size>c.MAX_WAV)throw Error("WAV_TOO_LARGE");
   const bytes=await file.arrayBuffer();
   const shape=c.parseWav(bytes);
   if(!session.checked)throw Error("SESSION_NO_LONGER_AUTHORIZED");
   const sha=await crypto.subtle.digest("SHA-256",bytes);
   row.audioSha256=Array.from(new Uint8Array(sha),b=>b.toString(16).padStart(2,"0")).join("");
   row.url=URL.createObjectURL(file);
   audio.src=row.url;audio.hidden=false;
   digest.textContent="SHA-256: "+row.audioSha256;
   setStatus(status,"Đã nạp WAV ("+shape.duration_seconds+" giây), chưa nghe · 미청취","good");
   for(const k of c.DIMS)row[k+"Element"].disabled=false;
   err.disabled=false;remark.disabled=false;
  }catch(ex){resetRow();setStatus(status,"Bị chặn: "+String(ex.message||ex),"bad");}
  update();
 });
 audio.addEventListener("ended",()=>{row.ended=true;done.disabled=false;setStatus(status,"Đã phát đến cuối. Xác nhận nghe nếu thực sự nghe được.","good");});
 done.addEventListener("change",()=>{row.listened=done.checked;update();});
 card.append(id,title,sentence,fileRow,audio,status,digest,ratingWrap,extras,att,);
 return card;
}
function render(){
 forget();list.replaceChildren();
 for(const s of p.samples.filter(s=>s.locale===locale.value))list.append(sampleCard(s));
 update();
}
async function boot(){
 if(!p||!c){info.textContent="Thiếu thư viện nghiệm thu, không thể chạy.";return;}
 try {
  if(!globalThis.crypto?.subtle)throw Error("WEBCRYPTO_SHA256_UNAVAILABLE");
  const buf=new TextEncoder().encode(JSON.stringify(p.samples));
  const dig=await crypto.subtle.digest("SHA-256",buf);
  hash=Array.from(new Uint8Array(dig),b=>b.toString(16).padStart(2,"0")).join("");
  if(hash!=="5475ca26774f39250a8a57d108feaf9955a8cfec0b6db38d0cfaac4c34660c4d")throw Error("PROTOCOL_SCRIPT_HASH_MISMATCH");
  render();
  session.addEventListener("change",()=>{
   locale.disabled=!session.checked;reviewer.disabled=!session.checked;
   reset.disabled=!session.checked;
   if(!session.checked)reviewer.value="";
   render();
  });
  locale.addEventListener("change",render);
  reviewer.addEventListener("input",update);
  reset.addEventListener("click",()=>{session.checked=false;locale.value="vi";reviewer.value="";locale.disabled=true;reviewer.disabled=true;reset.disabled=true;render();info.textContent="Đã xóa toàn bộ dữ liệu phiên khỏi trang.";});
  exportBtn.addEventListener("click",()=>{
   try{
    const packet=c.buildContribution({protocol:p,scriptHash:hash,
     reviewerRef:reviewer.value.trim(),locale:locale.value,rows,sessionAttested:session.checked});
    const content=JSON.stringify(packet,null,2);
    const file=new Blob([content],{type:"application/json"});
    const url=URL.createObjectURL(file),link=document.createElement("a");
    link.href=url;link.download="honey-st3-"+locale.value+"-local-unverified-review.json";
    document.body.appendChild(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1200);
    info.textContent="Đã tạo hồ sơ JSON trên máy này, chưa gửi và chưa xác minh người nghe. Không kèm WAV.";
   }catch(e){info.textContent="Từ chối xuất: "+String(e.message||e);}
  });
  window.addEventListener("pagehide",forget,{once:true});
  globalThis.HoneyReviewStationReady=true;
 }catch(e){
  info.textContent="TỪ CHỐI KHỞI ĐỘNG: "+String(e.message||e);
  badge.textContent="BLOCKED · Chưa thể chạy";
 }
}
document.addEventListener("DOMContentLoaded",boot);
})();
