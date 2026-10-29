"use strict";
/* HONEY STUDIO BẢO V1 — pure, offline demonstration. Never import real customer data. */
const PRODUCTS = Object.freeze(["mango","coconut","pomelo"]);
const LANGS = Object.freeze(["vi","ko","en","zh"]);
const COPY = Object.freeze({
 vi:{
  notice:"Bản dựng giao diện nội bộ. Không phát sóng, không gửi tin nhắn hoặc tạo đơn hàng thật.",
  language:"NGÔN NGỮ",stage:"CHƯA PHÁT SÓNG",playing:"ĐANG MÔ PHỎNG",
  kicker:"NÔNG SẢN VIỆT · HÀN QUỐC",avatar:"Vị trí nhân vật · Chờ hình ảnh được phê duyệt",
  subtitle:"Chào mừng đến Honey Trái Cây Việt - Hàn!",play:"Chạy mô phỏng",pause:"Dừng mô phỏng",
  products:{mango:"Xoài Việt Nam",coconut:"Dừa tươi",pomelo:"Bưởi Việt Nam"},
  scriptHelp:"Kịch bản thử để người dẫn giới thiệu sản phẩm đang chọn.",
  scripts:{mango:"Mời cả nhà khám phá xoài Việt Nam cùng Honey. Vui lòng xác nhận loại và ngày giao trước khi đặt hàng.",coconut:"Honey giới thiệu dừa tươi Việt Nam. Thông tin giao hàng và tình trạng sản phẩm phải được nhân viên xác nhận.",pomelo:"Cùng khám phá bưởi Việt Nam. Honey sẽ xác nhận quy cách và tình trạng trước khi nhận đơn."},
  comment1:"Có giao 택배 không?",comment2:"Xoài có loại chín không?",
  reply:"Soạn phản hồi mẫu",replyLabel:"BẢN NHÁP · CHƯA GỬI",
  replyText:"Dạ Honey có hỗ trợ tư vấn giao 택배. Địa chỉ và lịch giao cần được xác nhận trước khi đặt hàng. (DEMO — chưa gửi)",
  intentHeading:"Hộp thư xem xét",intent:"Chỉ là nháp mô phỏng. Không ghi ERP.",draft:"Thêm ý định mua giả lập",
  footer:"KHÔNG LIVE · KHÔNG TẠO ĐƠN · KHÔNG KẾT NỐI NGOÀI"
 },
 ko:{
  notice:"내부 개발용 화면입니다. 실제 방송, 메시지 발송, 주문 생성은 하지 않습니다.",
  language:"언어",stage:"방송 중 아님",playing:"시뮬레이션 중",
  kicker:"베트남 농산물 · 한국",avatar:"진행자 자리 · 승인된 이미지 미연결",
  subtitle:"Honey 베트남·한국 과일에 오신 것을 환영합니다!",play:"시뮬레이션 시작",pause:"시뮬레이션 정지",
  products:{mango:"베트남 망고",coconut:"신선한 코코넛",pomelo:"베트남 포멜로"},
  scriptHelp:"선택한 상품에 대한 테스트 안내 문구입니다.",
  scripts:{mango:"베트남 망고를 소개합니다. 종류와 배송 가능 여부는 주문 전에 꼭 확인해 주세요.",coconut:"신선한 베트남 코코넛을 소개합니다. 배송과 재고는 직원 확인이 필요합니다.",pomelo:"베트남 포멜로를 소개합니다. 규격과 재고는 주문 전에 확인합니다."},
  comment1:"택배 배송 가능해요?",comment2:"잘 익은 망고 있나요?",
  reply:"예시 답변 작성",replyLabel:"초안 · 전송 안 됨",
  replyText:"Honey 택배 상담은 가능하지만 배송 가능 여부와 일정 확인이 필요합니다. (DEMO — 미전송)",
  intentHeading:"문의 검토함",intent:"테스트 초안만 생성합니다. ERP 기록 없음.",draft:"테스트 구매 의도 추가",
  footer:"실제 방송 없음 · 주문 생성 없음 · 외부 연결 없음"
 },
 en:{
  notice:"Internal development preview. No live broadcast, outbound messages or real orders.",
  language:"LANGUAGE",stage:"NOT LIVE",playing:"SIMULATING",
  kicker:"VIETNAMESE PRODUCE · KOREA",avatar:"Presenter placeholder · Approved image not connected",
  subtitle:"Welcome to Honey Vietnam–Korea Fruit!",play:"Play simulation",pause:"Pause simulation",
  products:{mango:"Vietnamese mango",coconut:"Fresh coconut",pomelo:"Vietnamese pomelo"},
  scriptHelp:"Demo talking points for the selected product.",
  scripts:{mango:"Discover Vietnamese mango with Honey. Variety and delivery must be confirmed before ordering.",coconut:"Meet fresh Vietnamese coconuts. Staff must confirm availability and delivery.",pomelo:"Explore Vietnamese pomelo. Grade and stock require confirmation before a sale."},
  comment1:"Do you offer parcel delivery?",comment2:"Do you have ripe mangoes?",
  reply:"Draft example response",replyLabel:"DRAFT · NOT SENT",
  replyText:"Honey can discuss parcel delivery, but the address and delivery date require confirmation. (DEMO — not sent)",
  intentHeading:"Intent review",intent:"Simulated draft only. No ERP write.",draft:"Add mock purchase intent",
  footer:"NO LIVE · NO ORDER WRITES · NO EXTERNAL CONNECTION"
 },
 zh:{
  notice:"仅供内部开发预览。不直播、不发送消息、不生成真实订单。",
  language:"语言",stage:"未开播",playing:"模拟中",
  kicker:"越南农产品 · 韩国",avatar:"主播占位 · 尚未接入已批准形象",
  subtitle:"欢迎来到 Honey 越韩水果！",play:"开始模拟",pause:"暂停模拟",
  products:{mango:"越南芒果",coconut:"新鲜椰子",pomelo:"越南柚子"},
  scriptHelp:"所选商品的演示介绍文案。",
  scripts:{mango:"欢迎了解越南芒果。下单前请确认品种和配送安排。",coconut:"为您介绍新鲜越南椰子。库存与配送需由工作人员确认。",pomelo:"欢迎了解越南柚子。规格与库存需在下单前确认。"},
  comment1:"支持快递吗？",comment2:"有熟芒果吗？",
  reply:"生成示例回复",replyLabel:"草稿 · 未发送",
  replyText:"可咨询快递配送，但需要先确认地址和送达时间。（演示 — 未发送）",
  intentHeading:"意向审核",intent:"仅模拟草稿，不写入 ERP。",draft:"添加模拟购买意向",
  footer:"未直播 · 不创建订单 · 无外部连接"
 }
});
function initialState(){return {language:"vi",product:"mango",playing:false,replied:false,draftCount:0};}
function transition(state,action){
  if(!state || !action || typeof action.type!=="string")throw new Error("BAD_DEMO_ACTION");
  switch(action.type){
   case "LANGUAGE":return LANGS.includes(action.value)?{...state,language:action.value,replied:false}:state;
   case "PRODUCT":return PRODUCTS.includes(action.value)?{...state,product:action.value}:state;
   case "PLAY":return {...state,playing:!state.playing};
   case "REPLY":return {...state,replied:true};
   case "DRAFT":return {...state,draftCount:Math.min(5,state.draftCount+1)};
   case "RESET":return {...initialState(),language:state.language};
   default:throw new Error("UNKNOWN_DEMO_ACTION");
  }
}
function viewModel(state){
 const t=COPY[state.language]||COPY.vi;
 return {language:state.language,status:state.playing?t.playing:t.stage,playText:state.playing?t.pause:t.play,product:t.products[state.product],script:t.scripts[state.product],replyText:state.replied?t.replyText:"—",draftCount:state.draftCount,copy:t};
}
function mount(doc){
 let state=initialState();
 const get=id=>doc.getElementById(id);
 const set=(id,value)=>{const el=get(id);if(el)el.textContent=String(value);};
 function render(){
  const m=viewModel(state),t=m.copy;
  doc.documentElement.lang=state.language==="zh"?"zh":state.language;
  set("notice-copy",t.notice);set("lang-caption",t.language);
  set("stage-status",m.status);set("scene-kicker",t.kicker);set("avatar-disclaimer",t.avatar);
  set("subtitle",t.subtitle);set("play-copy",m.playText);
  set("p-mango",t.products.mango);set("p-coconut",t.products.coconut);set("p-pomelo",t.products.pomelo);
  set("script-help",t.scriptHelp);set("script-content",m.script);set("script-state","DRAFT · "+state.language.toUpperCase());
  set("comment-one",t.comment1);set("comment-two",t.comment2);set("reply-copy",t.reply);
  set("reply-label",t.replyLabel);set("reply-content",m.replyText);
  set("intent-heading",t.intentHeading);set("intent-copy",t.intent);
  set("draft-copy",t.draft);set("draft-count",m.draftCount);set("footer-safety",t.footer);
  const btn=get("play-btn");if(btn)btn.setAttribute("aria-pressed",String(state.playing));
  const progress=get("progress");if(progress)progress.style.width=state.playing?"55%":"0%";
  const choice=get("lang");if(choice)choice.value=state.language;
  for(const b of doc.querySelectorAll("[data-product]")){
   const yes=b.getAttribute("data-product")===state.product;
   b.classList.toggle("active",yes);b.setAttribute("aria-pressed",String(yes));
  }
 }
 const dispatch=a=>{state=transition(state,a);render();};
 get("lang").addEventListener("change",e=>dispatch({type:"LANGUAGE",value:e.target.value}));
 get("play-btn").addEventListener("click",()=>dispatch({type:"PLAY"}));
 get("reset-btn").addEventListener("click",()=>dispatch({type:"RESET"}));
 get("reply-btn").addEventListener("click",()=>dispatch({type:"REPLY"}));
 get("draft-btn").addEventListener("click",()=>dispatch({type:"DRAFT"}));
 for(const b of doc.querySelectorAll("[data-product]"))b.addEventListener("click",()=>dispatch({type:"PRODUCT",value:b.getAttribute("data-product")}));
 render();
 return {snapshot:()=>({...state}),dispatch};
}
if(typeof module!=="undefined"&&module.exports)module.exports={PRODUCTS,LANGS,COPY,initialState,transition,viewModel,mount};
if(typeof document!=="undefined")document.addEventListener("DOMContentLoaded",()=>mount(document));
