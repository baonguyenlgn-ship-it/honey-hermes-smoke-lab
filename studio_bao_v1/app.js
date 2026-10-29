"use strict";
/* HONEY STUDIO BẢO V1 — pure, offline demonstration. Never import real customer data. */
const PRODUCTS = Object.freeze(["mango","coconut","pomelo"]);
const LANGS = Object.freeze(["vi","ko","en","zh"]);
const COPY = Object.freeze({
 vi:{
  labels:{"stageHeading":"Người dẫn kỹ thuật số","productsHeading":"Sản phẩm giới thiệu","scriptHeading":"Lời thoại giới thiệu","commentsHeading":"Bình luận mô phỏng","timeline":"KỊCH BẢN DEMO","productNote":"DỮ LIỆU GIẢ LẬP","transport":"CHỈ MÔ PHỎNG","draftStatus":"BẢN NHÁP"},
  subtitles:{"mango":"Xoài Việt Nam — vui lòng xác nhận loại và ngày giao.","coconut":"Dừa tươi Việt Nam — xác nhận tình trạng và lịch giao.","pomelo":"Bưởi Việt Nam — xác nhận quy cách trước khi đặt."},
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
  labels:{"stageHeading":"디지털 진행자","productsHeading":"상품 소개","scriptHeading":"진행 대본","commentsHeading":"댓글 시뮬레이터","timeline":"시연 스토리보드","productNote":"모의 상품 데이터","transport":"시뮬레이션 전용","draftStatus":"초안"},
  subtitles:{"mango":"베트남 망고 — 품종과 배송일을 확인해 주세요.","coconut":"베트남 코코넛 — 재고와 배송일은 확인이 필요합니다.","pomelo":"베트남 포멜로 — 규격을 확인해 주세요."},
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
  labels:{"stageHeading":"Digital presenter","productsHeading":"Product spotlight","scriptHeading":"Talking points","commentsHeading":"Comment simulator","timeline":"DEMO STORYBOARD","productNote":"MOCK PRODUCT DATA","transport":"SIMULATION ONLY","draftStatus":"DRAFT"},
  subtitles:{"mango":"Vietnamese mango — confirm the variety and delivery date.","coconut":"Fresh coconut — confirm availability and delivery.","pomelo":"Vietnamese pomelo — confirm grading before ordering."},
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
  labels:{"stageHeading":"数字主播","productsHeading":"商品展示","scriptHeading":"讲解文案","commentsHeading":"评论模拟器","timeline":"演示分镜","productNote":"模拟商品数据","transport":"仅供模拟","draftStatus":"草稿"},
  subtitles:{"mango":"越南芒果 — 请先确认品种和配送日期。","coconut":"越南椰子 — 请确认库存和配送安排。","pomelo":"越南柚子 — 请先确认规格。"},
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
const SCENE_UI = Object.freeze({"vi":{"scene":"CẢNH","titles":["CHÀO KHÁCH","GIỚI THIỆU","XÁC NHẬN GIAO"],"prev":"Cảnh trước","next":"Cảnh tiếp"},"ko":{"scene":"장면","titles":["인사","상품 설명","배송 확인"],"prev":"이전 장면","next":"다음 장면"},"en":{"scene":"SCENE","titles":["WELCOME","PRODUCT","DELIVERY CHECK"],"prev":"Previous","next":"Next scene"},"zh":{"scene":"场景","titles":["欢迎","商品介绍","配送确认"],"prev":"上一场","next":"下一场"}});
const STORYBOARD = Object.freeze({
 vi: Object.freeze({
  mango: Object.freeze([{script:COPY.vi.scripts.mango,subtitle:COPY.vi.subtitles.mango},{"script":"Xoài có nhiều giống, độ chín và quy cách khác nhau. Trước khi báo giá, nhân viên cần kiểm tra thông tin lô hàng.","subtitle":"Xoài: kiểm tra giống và độ chín trước khi tư vấn."},{"script":"Khách hỏi 택배: chỉ xác nhận sau khi kiểm tra khu vực, lịch giao và đóng gói. Bản DEMO không tiếp nhận đơn.","subtitle":"택배: xác nhận địa chỉ, lịch giao trước khi đặt."}]),
  coconut: Object.freeze([{script:COPY.vi.scripts.coconut,subtitle:COPY.vi.subtitles.coconut},{"script":"Dừa tươi có quy cách và tình trạng khác nhau. Nhân viên cần đối chiếu nguồn hàng thực tế trước khi tư vấn.","subtitle":"Dừa tươi: kiểm tra quy cách và hàng thực tế."},{"script":"Nếu khách hỏi 택배, phải kiểm tra khu vực giao và đóng gói phù hợp. Chỉ tạo bản nháp, không gửi hay chốt đơn.","subtitle":"Dừa: xác nhận khả năng 택배 trước khi đặt."}]),
  pomelo: Object.freeze([{script:COPY.vi.scripts.pomelo,subtitle:COPY.vi.subtitles.pomelo},{"script":"Bưởi Việt Nam có kích cỡ và quy cách riêng. Cần kiểm tra từng lô, không tự cam kết hàng sẵn có.","subtitle":"Bưởi: kiểm tra cỡ quả và quy cách."},{"script":"Vui lòng xác nhận địa chỉ, khả năng 택배 và lịch giao với nhân viên. Giao diện DEMO không nhận đơn.","subtitle":"Bưởi: chỉ xác nhận giao khi đã kiểm tra."}]),
 }),
 ko: Object.freeze({
  mango: Object.freeze([{script:COPY.ko.scripts.mango,subtitle:COPY.ko.subtitles.mango},{"script":"망고는 품종, 숙도, 포장 규격이 다양합니다. 가격 안내 전 직원이 실제 상품을 확인해야 합니다.","subtitle":"망고 품종과 숙도를 먼저 확인해 주세요."},{"script":"택배 가능 지역, 포장, 배송 일정은 직원 확인 후 안내합니다. 이 화면에서는 주문을 접수하지 않습니다.","subtitle":"택배 주소와 일정 확인 후 주문을 안내합니다."}]),
  coconut: Object.freeze([{script:COPY.ko.scripts.coconut,subtitle:COPY.ko.subtitles.coconut},{"script":"코코넛은 규격과 상태가 다를 수 있습니다. 안내 전에 실제 상품과 재고를 확인해야 합니다.","subtitle":"코코넛 규격과 상품 상태를 확인해 주세요."},{"script":"택배 포장 및 배송 가능 여부는 직원 확인이 필요합니다. 데모에서는 주문을 생성하지 않습니다.","subtitle":"코코넛 택배 가능 여부 확인이 필요합니다."}]),
  pomelo: Object.freeze([{script:COPY.ko.scripts.pomelo,subtitle:COPY.ko.subtitles.pomelo},{"script":"베트남 포멜로는 크기와 규격이 다를 수 있습니다. 실제 상품 확인 전 재고를 보장하지 않습니다.","subtitle":"포멜로 크기와 규격을 확인해 주세요."},{"script":"배송지와 택배 일정을 확인한 뒤 안내합니다. 이 화면은 상담 초안만 만듭니다.","subtitle":"포멜로 택배와 배송 일정은 확인이 필요합니다."}]),
 }),
 en: Object.freeze({
  mango: Object.freeze([{script:COPY.en.scripts.mango,subtitle:COPY.en.subtitles.mango},{"script":"Mango variety, ripeness and pack sizes vary. Staff must check the actual lot before giving a quote.","subtitle":"Mango: verify variety and ripeness first."},{"script":"Parcel delivery areas, packaging and timing need staff confirmation. This DEMO cannot take orders.","subtitle":"Parcel delivery needs address and date confirmation."}]),
  coconut: Object.freeze([{script:COPY.en.scripts.coconut,subtitle:COPY.en.subtitles.coconut},{"script":"Coconuts vary in size and condition. Check the actual goods before advising a customer.","subtitle":"Coconut: confirm grading and actual stock."},{"script":"Staff must confirm parcel packaging and delivery eligibility. No real orders are created.","subtitle":"Coconut parcel delivery requires confirmation."}]),
  pomelo: Object.freeze([{script:COPY.en.scripts.pomelo,subtitle:COPY.en.subtitles.pomelo},{"script":"Vietnamese pomelo comes in different grades and sizes. Stock cannot be guaranteed in this preview.","subtitle":"Pomelo: check fruit size and specifications."},{"script":"Confirm the destination and parcel schedule with staff. This is a draft-only simulation.","subtitle":"Pomelo delivery requires staff confirmation."}]),
 }),
 zh: Object.freeze({
  mango: Object.freeze([{script:COPY.zh.scripts.mango,subtitle:COPY.zh.subtitles.mango},{"script":"芒果的品种、成熟度和包装规格各不相同。报价前需由员工确认实际批次。","subtitle":"芒果：请先确认品种及成熟度。"},{"script":"快递范围、包装和配送时间必须由员工核实。演示界面不接受真实订单。","subtitle":"快递：先确认地址和配送时间。"}]),
  coconut: Object.freeze([{script:COPY.zh.scripts.coconut,subtitle:COPY.zh.subtitles.coconut},{"script":"椰子的规格和状态可能不同。介绍前需要核实实际货品。","subtitle":"椰子：请先核实规格及商品状态。"},{"script":"快递包装和可配送范围需要人工确认。演示不生成订单。","subtitle":"椰子快递须先确认。"}]),
  pomelo: Object.freeze([{script:COPY.zh.scripts.pomelo,subtitle:COPY.zh.subtitles.pomelo},{"script":"越南柚子的大小与规格有所不同。本预览不保证实时库存。","subtitle":"柚子：请确认大小和规格。"},{"script":"配送地址及快递日期须由员工确认。本界面只生成模拟草稿。","subtitle":"柚子配送须由员工确认。"}]),
 }),
});
const EXPORT_UI = Object.freeze({"vi":{"title":"PHỤ ĐỀ · MỐC THỜI GIAN ƯỚC TÍNH","desc":"30 giây DEMO · chưa đồng bộ giọng nói/video","srt":"Xuất SRT","vtt":"Xuất VTT"},"ko":{"title":"자막 · 예상 타임코드","desc":"30초 데모 · 실제 음성/영상과 미동기화","srt":"SRT 내보내기","vtt":"VTT 내보내기"},"en":{"title":"SUBTITLES · ESTIMATED TIMING","desc":"30-second DEMO · not synced to voice/video","srt":"Export SRT","vtt":"Export VTT"},"zh":{"title":"字幕 · 估算时间码","desc":"30秒演示 · 未与真实语音/视频同步","srt":"导出 SRT","vtt":"导出 VTT"}});
function initialState(){return {language:"vi",product:"mango",playing:false,sceneIndex:0,replied:false,draftCount:0};}
function transition(state,action){
  if(!state || !action || typeof action.type!=="string")throw new Error("BAD_DEMO_ACTION");
  switch(action.type){
   case "LANGUAGE":return LANGS.includes(action.value)?{...state,language:action.value,replied:false}:state;
   case "PRODUCT":return PRODUCTS.includes(action.value)?{...state,product:action.value,sceneIndex:0}:state;
   case "PLAY":return {...state,playing:!state.playing};
   case "NEXT_SCENE":return state.playing&&state.sceneIndex<2?{...state,sceneIndex:state.sceneIndex+1}:state;
   case "PREV_SCENE":return state.playing&&state.sceneIndex>0?{...state,sceneIndex:state.sceneIndex-1}:state;
   case "REPLY":return {...state,replied:true};
   case "DRAFT":return {...state,draftCount:Math.min(5,state.draftCount+1)};
   case "RESET":return {...initialState(),language:state.language};
   default:throw new Error("UNKNOWN_DEMO_ACTION");
  }
}
function viewModel(state){
 const lang=LANGS.includes(state.language)?state.language:"vi";
 const t=COPY[lang],ui=SCENE_UI[lang],beats=STORYBOARD[lang][state.product];
 const index=Math.max(0,Math.min(2,state.sceneIndex));
 const beat=beats[index];
 return {language:lang,status:state.playing?t.playing:t.stage,playText:state.playing?t.pause:t.play,
  product:t.products[state.product],script:state.playing?beat.script:t.scripts[state.product],
  subtitle:state.playing?beat.subtitle:t.subtitle,replyText:state.replied?t.replyText:"—",
  draftCount:state.draftCount,copy:t,sceneNumber:index+1,sceneTotal:3,
  sceneTitle:ui.titles[index],sceneCounter:String(index+1).padStart(2,"0")+" / 03",
  sceneLabel:ui.scene,prevSceneLabel:ui.prev,nextSceneLabel:ui.next,
  previousDisabled:!state.playing||index===0,nextDisabled:!state.playing||index===2};
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
  set("subtitle",m.subtitle);set("play-copy",m.playText);
  set("scene-caption",m.sceneLabel+" · "+m.sceneTitle);
  set("scene-counter",m.sceneCounter);
  const exportText=EXPORT_UI[state.language];
  set("export-title",exportText.title);set("export-note",exportText.desc);
  set("srt-label",exportText.srt);set("vtt-label",exportText.vtt);
  set("prev-scene-copy",m.prevSceneLabel);set("next-scene-copy",m.nextSceneLabel);
  get("prev-scene-btn").disabled=m.previousDisabled;
  get("next-scene-btn").disabled=m.nextDisabled;
  for(const [id,key] of [["stage-heading","stageHeading"],["products-heading","productsHeading"],["script-heading","scriptHeading"],["comments-heading","commentsHeading"],["timeline-caption","timeline"],["product-note","productNote"],["transport-note","transport"]])set(id,t.labels[key]);
  set("p-mango",t.products.mango);set("p-coconut",t.products.coconut);set("p-pomelo",t.products.pomelo);
  set("script-help",t.scriptHelp);set("script-content",m.script);set("script-state",t.labels.draftStatus+" · "+state.language.toUpperCase());
  set("comment-one",t.comment1);set("comment-two",t.comment2);set("reply-copy",t.reply);
  set("reply-label",t.replyLabel);set("reply-content",m.replyText);
  set("intent-heading",t.intentHeading);set("intent-copy",t.intent);
  set("draft-copy",t.draft);set("draft-count",m.draftCount);set("footer-safety",t.footer);
  const btn=get("play-btn");if(btn)btn.setAttribute("aria-pressed",String(state.playing));
  const progress=get("progress");if(progress)progress.style.width=state.playing?String(Math.round(m.sceneNumber/m.sceneTotal*100))+"%":"0%";
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
 get("prev-scene-btn").addEventListener("click",()=>dispatch({type:"PREV_SCENE"}));
 const exportCaptions=format=>{
  const media=BaoSubtitles.createExport({beats:STORYBOARD[state.language][state.product],language:state.language,product:state.product,format});
  const objectUrl=URL.createObjectURL(new Blob([media.text],{type:media.mime}));
  const anchor=doc.createElement("a");
  anchor.href=objectUrl;anchor.download=media.filename;
  doc.body.appendChild(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);
 };
 get("export-srt-btn").addEventListener("click",()=>exportCaptions("srt"));
 get("export-vtt-btn").addEventListener("click",()=>exportCaptions("vtt"));
 get("next-scene-btn").addEventListener("click",()=>dispatch({type:"NEXT_SCENE"}));
 get("reply-btn").addEventListener("click",()=>dispatch({type:"REPLY"}));
 get("draft-btn").addEventListener("click",()=>dispatch({type:"DRAFT"}));
 for(const b of doc.querySelectorAll("[data-product]"))b.addEventListener("click",()=>dispatch({type:"PRODUCT",value:b.getAttribute("data-product")}));
 render();
 return {snapshot:()=>({...state}),dispatch};
}
if(typeof module!=="undefined"&&module.exports)module.exports={PRODUCTS,LANGS,COPY,SCENE_UI,STORYBOARD,initialState,transition,viewModel,mount};
if(typeof document!=="undefined")document.addEventListener("DOMContentLoaded",()=>mount(document));
