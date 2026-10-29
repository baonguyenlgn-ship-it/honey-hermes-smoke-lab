"use strict";
// Canonical reviewer-only speech scripts. No WAV, no identity or customer data.
(function(root){
const protocol={
  "schema": "honey.st3-native-listening-protocol.v1",
  "model_revision": "3cadd1ee6394adea1bd021217a0e650ede09a323",
  "voice": "M1 generic preset",
  "samples": [
    {
      "id": "VI-DISC-01",
      "locale": "vi",
      "domain": "ai_disclosure",
      "seed": 20261401,
      "text": "Xin chào. Đây là giọng nói thử nghiệm được tạo bằng trí tuệ nhân tạo."
    },
    {
      "id": "VI-FRUIT-02",
      "locale": "vi",
      "domain": "fruit_names",
      "seed": 20261402,
      "text": "Hôm nay chúng tôi giới thiệu xoài, bưởi và dừa tươi."
    },
    {
      "id": "VI-SHIP-03",
      "locale": "vi",
      "domain": "delivery",
      "seed": 20261403,
      "text": "Vui lòng kiểm tra ngày giao hàng và địa chỉ trước khi đặt mua."
    },
    {
      "id": "VI-CONF-04",
      "locale": "vi",
      "domain": "confirmation",
      "seed": 20261404,
      "text": "Đơn hàng chỉ được xác nhận sau khi hệ thống ghi nhận thành công."
    },
    {
      "id": "KO-DISC-01",
      "locale": "ko",
      "domain": "ai_disclosure",
      "seed": 20261501,
      "text": "안녕하세요. 이 음성은 인공지능으로 생성한 시험 음성입니다."
    },
    {
      "id": "KO-FRUIT-02",
      "locale": "ko",
      "domain": "fruit_names",
      "seed": 20261502,
      "text": "오늘은 망고, 포멜로, 코코넛을 소개합니다."
    },
    {
      "id": "KO-SHIP-03",
      "locale": "ko",
      "domain": "delivery",
      "seed": 20261503,
      "text": "택배 배송 날짜와 주소를 주문 전에 확인해 주세요."
    },
    {
      "id": "KO-CONF-04",
      "locale": "ko",
      "domain": "confirmation",
      "seed": 20261504,
      "text": "주문은 시스템에 저장된 후 확인 절차를 거쳐 접수됩니다."
    }
  ],
  "evaluation": {
    "minimum_independent_native_reviewers_per_locale": 2,
    "dimensions": [
      "word_intelligibility",
      "pronunciation",
      "prosody",
      "naturalness",
      "male_presenting_timbre"
    ],
    "scale": {
      "min": 1,
      "max": 5,
      "anchors": {
        "1": "unusable or wrong",
        "2": "many defects",
        "3": "understandable with noticeable issues",
        "4": "good with minor issues",
        "5": "clear, natural and suitable for the specific criterion"
      }
    },
    "draft_thresholds": {
      "per_dimension_median_min": 4,
      "per_sample_intelligibility_min": 4,
      "critical_language_or_product_error_max": 0
    },
    "thresholds_are_proposals_not_human_or_legal_acceptance": true,
    "allow_rating_without_listening": false
  }
};
if(typeof module==="object"&&module.exports)module.exports=protocol;
root.HoneyReviewProtocol=protocol;
})(typeof globalThis!=="undefined"?globalThis:this);
