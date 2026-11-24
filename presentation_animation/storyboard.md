# 우체국보험 상품·청약 판단 지원 앱: 발표 시연 애니메이션 스토리보드

본 영상은 모든 수치와 항목 이름을 `presentation_animation/facts.json`에서 읽어 표시합니다. 평면 카드와 표, A4 문서는 억지로 기울이지 않고 정면 2차원 클로즈업과 패닝으로 보여 주며, 세 축(가로, 깊이, 높이)에 모두 구조적 의미가 있는 핵심 원리 구간만 진정한 3차원(`ThreeDScene`) 입체 기하와 정면 고정 빌보드 라벨로 연출합니다.

전체 이야기는 다음 네 단계 흐름을 따릅니다.
1. **우리가 만들려는 서비스** (1장)
2. **구현한 운영 화면 구성** (2장)
3. **각 단계에서 활용 가능한 자원과 부딪힌 문제, 그리고 푼 방법** (3~8장)
4. **손으로 하던 방식과 비교해 이 앱으로 만든 구조와 남은 과제** (9장)

---

## 파일 구성 (1920x1080, 60fps, H.264 MP4)

- **분할본 Part 1 (1~2장)**: `우체국보험_발표시연_Part1_서비스목표와_구현기능_1080p60.mp4`
- **분할본 Part 2 (3~4장)**: `우체국보험_발표시연_Part2_자원제약과_난제해결_수집추출_1080p60.mp4`
- **분할본 Part 3 (5~6장)**: `우체국보험_발표시연_Part3_판정AI배경과_검증분류_해법_1080p60.mp4`
- **분할본 Part 4 (7~9장)**: `우체국보험_발표시연_Part4_온톨로지해석과_업무혁신결과_1080p60.mp4`
- **전체 통합본 (1~9장 연속, `README.md`의 FFmpeg concat 명령으로 생성)**: `우체국보험_발표시연_애니메이션_1080p60.mp4`

---

## 장별 참조 열쇠와 시각 연출 설계

### Part 1. 서비스 목표와 운영 화면 구성 (`part1_service.py`)
- **1장. 우리가 만들려는 서비스: 공시 문서 비교 화면과 현장 응대 카드**
  - **현실 문제**: 정밀 비교 대상(`comparison_target_counts`), 대용량 요약서(`hanwha_summary_pages`), 글자가 그림인 요약서(`image_doc.pages`)를 실측 쪽수 비례 높이의 3차원 문서 협곡과 정면 빌보드 배지로 비행 조감한 뒤, 정면 2차원 화면으로 전환해 고지 질문 범위와 지급 기준(`example_targeted_anticancer`, `benefits_by_org_basis`)이 다른 상자와 창구 전달 단절 구간을 클로즈업 패닝합니다.
  - **목표 구조**: 기관 보도(`market_news_institution_count`)와 공시 문서가 정련 깔때기를 거쳐 구글 시트 정본(`sheet_tab_count`)에 담기고, 대표 조건(`reference_condition`, `default_base_variant`)을 반영한 본부 단독 HTML 화면(`operating_cost_won`, `site_browser_check_problems`, `standard_coverage_in_use`, `compared_coverage_pairs`, `forbidden_words`)과 창구용 A4 한 장 응대 카드(`card_category_order`, `lead_strengths`)로 정면에서 이어집니다.
- **2장. 구현한 운영 화면 구성**
  - 정면 2차원 구도에서 중앙 조건 다이얼 바늘이 회전하며 운영 화면(`site_screen_count`)으로 광선을 보내고, 주간 시장 소식(`screen_market_news`), 가입 관문 비교, 표준담보 비교표(`standard_coverage_in_use`), 특약 조합별 실제 지급액, 개정 전후 비교(`example_targeted_anticancer`, `revision_changes`), 검증과 작업 로그(`work_log_count_site`, `work_log_by_result`) 카드를 기울임 없이 클로즈업 투어합니다.

### Part 2. 수집 단계와 추출 단계 (`part2_collect_extract.py`)
- **3장. 수집 단계: 공시 문서와 시장 소식 수집**
  - **부딪힌 문제**: 가용 자원(`daily_limit_search`, `actions_free_minutes_per_month`, `operating_cost_won`, `team_size`)과 함께 모델 미지정 실행(`unpinned_agent_incident`), 목록 요청 차단(`hanwhafire_block_status`), 검색 후보 탈락(`search_candidates_rejected`) 및 API 보관 상한(`news_api_storage_limit_days`), 첫 수집 구간 밖 소식 유입(`first_collect_news`)을 정면 진단 카드로 짚습니다.
  - **푼 방법**: 조사(`comparison_target_counts`), 총괄 지휘(`disclosure_pilot_org`, `disclosure_batch_org_count`), 수집 구현, 독립 점검(`disclosure_batch_auto_org_count`, 점검 모델 sonnet)의 정면 분업 기구에 이어, 시범 중심탑 둘레에 원형으로 배치된 일괄 실행 대상(`disclosure_batch_orgs`, `disclosure_batch_pdf_count`, `disclosure_batch_test_count`) 기둥들이 두 차례 3차원 원형 파동에 맞춰 수집과 해시 점검 높이로 솟아오르는 입체 원형 경기장을 보여 주고, 정면 2차원의 요일별 검색 배분(`collect_daily_plan`) 및 날짜, 무관 종목 필터(`news_excluded_lines`, `news_excluded_topics`)로 잇습니다.
- **4장. 추출 단계: 요약서와 사업방법서에서 급부와 한도를 뽑는 방법**
  - **부딪힌 문제**: 한도와 도구(`daily_limit_extract`, `daily_limit_upper`), 첫 추출 호출 수(`hanwha_first_extract`), 숫자 직접 추출 오독(`targeted_anticancer_misread`, `text_switch_confirmed_rows`), 그림 요약서와 대조용 로컬 OCR 결과(`image_doc`, `local_ocr_test`), 가짜 시트 시험의 특약 한도 초기화(`rider_limit_rows_protected`)를 정면에서 보여줍니다.
  - **푼 방법**: 모델 원문 전달과 코드 계산 규칙(`text_switch_confirmed_rows`, `samsungfire_crosscheck_rows`, `benefits_by_org`)은 고정 설명 카드로 두고, 경과 기간, 개정 전후 차수, 실제 지급액 세 축이 만나는 3차원 계단 지형(`example_targeted_anticancer`)을 공전 조감한 뒤, 제미나이 패널과 sonnet 에이전트의 상하 2단 3차원 시트 교차 검증과 정면 확대경(`image_doc`, `image_doc_same_reader_repeat`, `id_inherit_simulated_rows`)으로 마무리합니다.

### Part 3. 판정 모델 원리와 검증, 분류 단계 (`part3_decision.py`)
- **5장. 판정 모델 원리와 적용 영역**
  - 정면 2차원 화면에서 기존 생성형 모델의 순차 단어 생성과 비생성 판정 모델(`models.decide`, `decision_model_release_date`, `decision_model_spec`)의 선택지 확률 반환(`symmetric_choice_probability`) 및 실제 활용처(`decision_model_uses`)를 대비하고, 입력 단위와 문항 사양, 정형 판정 방식, 표본 경계값 검증(`calibration_flipped_rows`, `calibration_reextract_band`) 카드를 정면 클로즈업 패닝으로 보여줍니다.
- **6장. 검증, 분류 단계: 분당 토큰 한도와 모호한 확률 문제를 푼 방법**
  - 정면에서 참/거짓 질문 확률 범위(`true_false_probability_range`), 결합 제약 묶음 질문의 오류 통과(`bundled_constraint_check`), 매핑 재질의 실행 전 시간 어림(`mapping_requery`)을 진단한 뒤, 확정 기준면과 재추출 기준면(`verify_confirm_threshold`, `verify_reextract_threshold`) 두 수평 반투명 기준면이 가로지르는 3차원 확률 공간에서 변경 전후 기둥(`symmetric_choice_probability`, `bundled_constraint_check`, `calibration_flipped_rows`)이 위아래로 갈라지는 입체 구도를 보여 주고, 정면 2차원의 확률 분기 흐름과 분당 토큰 대기 규칙(`decide_token_window`, `decide_tokens_per_minute_guard`, `decide_per_minute_limit`), 시장 소식 분류(`market_news_categories`, `market_news_by_category`, `decide_quota_failures_logged`)로 이어집니다.

### Part 4. 온톨로지 구조, 관계 탐색, 전후 비교 (`part4_ontology_impact.py`)
- **7장. 온톨로지와 단독 화면: 명칭 불일치와 매핑 대기를 푼 방법**
  - 정면에서 종형과 특약 이름 불일치(`default_base_variant`, `peer_held_coverage`), 한화 매핑 대기(`dictionary_initial_size`, `hanwha_pending_before_rerun`, `hanwha_pending_after_rerun`), 보험료 예시 부재(`premium_example_rows`)를 짚은 뒤, 원천 사실층에서 표준 기준층과 인사이트층으로 빛줄기를 따라 수직 상승 비행하는 3차원 세 계층 건축 구도와 정면 3단 도식(`site_org_count`, `variant_count_site`, `rider_count_site`, `benefit_count_site`, `market_news_count`, `standard_coverage_in_use`, `coverage_relations_by_kind`), 3차원 성좌 관계망(`mapping_status_site`, `benefits_without_mapping`, `coverage_relation_count`), 정면 사전 확장 카드(`dictionary_first_expansion_added`, `dictionary_second_expansion`, `standard_coverage_rows`, `dictionary_expansion_survey_org_count`, `dictionary_addition_rule`, `standard_coverage_names`)를 보여줍니다.
- **8장. 포함, 통합 관계 탐색과 실행**
  - 상단 포함 계보와 하단 통합 대 분리 입체 갈림길(`standard_coverage_names`, `coverage_relations_by_kind`)을 따라 두 갈래 3차원 광선이 분기했다가 우체국 상품으로 수렴하는 3차원 공간 탐색에 이어, 정면 2차원으로 전환해 고객군 지도 요약(`segment_map_rows`, `segment_map_columns`, `segment_map_cell_count`, `segment_map_labels`), 치료 단계별 보유 담보 막대(`treatment_stages`, `held_coverage_by_stage`), 결합 제약(`reference_main_contract_limit_manwon`, `combination_constraints_by_org`), 영업 인사이트 분류(`sales_insight_categories`, `sales_insight_by_category`, `briefing_by_base_variant`)와 A4 한 장 응대 카드(`card_category_order`)를 보여줍니다.
- **9장. 손으로 하던 방식과 이 앱으로 만든 구조**
  - 손으로 하던 방식 대비 정본과 단독 화면, 작업 로그(`work_log_count_site`), 그림 요약서 교차 판독(`image_doc`)과 표본 경계 보정(`calibration_flipped_rows`), 매핑 대기(`mapping_status_site`)와 우열 미단정(`no_verdict_pairs`) 분리 결과를 정리하고, 전체 시험 수(`test_count`), 브라우저 점검(`site_browser_check_problems`), 다음 단계 과제(`premium_example_rows`, `benefit_disease_code_rows`), 아직 재지 못한 성과(`not_yet_measured`)를 함께 밝힙니다.
