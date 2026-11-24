# 우체국보험 상품·청약 판단 지원 시스템: 발표 시연 애니메이션 스토리보드

본 영상은 모든 수치와 항목 이름을 `presentation_animation/facts.json`에서 조회하여 표시하며, 화면 용어는 `common.py`의 보험과 IT 실무 용어 상수(`TERM`, `label_ko`)로 통일합니다. 평면 카드와 비교표, A4 문서는 기울이지 않고 각 요소와 진단 항목을 먼저 화면 중앙에서 크게 동적으로 시연한 뒤 제자리로 배치해 최종 2차원 종합 차트로 연결합니다. 세 축(가로, 깊이, 높이)에 모두 구조적 의미가 있는 핵심 원리 구간만 3차원(`ThreeDScene`) 입체 기하와 고대비 정면 고정 빌보드 배지(`bb_badge`)로 연출하며, 발표자가 현장에서 설명하며 진행할 수 있도록 핵심 장면마다 충분한 정지 호흡을 둡니다.

전체 이야기는 다음 네 단계 흐름을 따릅니다.
1. **구축 목표 서비스와 전달 구조** (1장)
2. **구현한 운영 화면 구성** (2장)
3. **단계별 가용 자원과 발생 문제, 그리고 해결 구조** (3~8장)
4. **기존 수작업 방식과 구현된 비교 시스템의 전후 대조 및 미측정 과제** (9장)

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
- **1장. 구축 목표 서비스: 공시 문서 비교 화면과 현장 응대 화법**
  - **현실 문제**: 정밀 비교 대상 타사(`comparison_target_counts`), 대용량 상품요약서(`hanwha_summary_pages`), 텍스트가 이미지로 수록된 상품요약서(`image_doc.pages`)를 실측 쪽수 비례 높이의 3차원 문서 협곡과 정면 빌보드 배지로 비행 조감한 뒤, 정면 2차원 화면으로 전환해 고지항목 범위와 지급기준(`example_targeted_anticancer`, `benefits_by_org_basis`)이 상이한 구조와 창구 전달 단절 구간을 클로즈업합니다.
  - **목표 구조**: 기관 보도자료(`market_news_institution_count`)와 공시 문서가 정제 과정을 거쳐 구글 시트 마스터 데이터(`sheet_tab_count`)와 스냅샷(특정 시점의 데이터 복사본)에 적재되고, 기본 조건(`reference_condition`, `default_base_variant`)을 반영한 본부 오프라인 단독 HTML 화면(`operating_cost_won`, `site_browser_check_problems`, `standard_coverage_in_use`, `compared_coverage_pairs`, `forbidden_words`)과 창구용 A4 단일 응대 화법 문서(`card_category_order`, `lead_strengths`)로 연결됩니다.
- **2장. 구현한 운영 화면 구성**
  - 정면 2차원 구도에서 중앙 조건 다이얼이 회전하며 운영 화면(`site_screen_count`)으로 연결되고, 주간 시장 동향(`screen_market_news`), 인수기준(가입 심사 기준) 비교, 표준담보 비교표(`standard_coverage_in_use`), 특약 부가 조건 및 지급액, 개정 전후 비교(`example_targeted_anticancer`, `revision_changes`), 검증 및 작업 로그(`work_log_count_site`, `work_log_by_result`) 화면을 차례대로 시연합니다.

### Part 2. 수집 단계와 추출 단계 (`part2_collect_extract.py`)
- **3장. 수집 단계: 회사별 상품공시와 주간 시장 동향 수집**
  - **발생 문제**: 가용 자원(`daily_limit_search`, `actions_free_minutes_per_month`, `operating_cost_won`, `team_size`)과 함께 모델 미지정 서브에이전트 실행(`unpinned_agent_incident`), 목록 요청 차단(`hanwhafire_block_status`), 검색 후보 오류(`search_candidates_rejected`) 및 API 보관 상한(`news_api_storage_limit_days`), 초기 수집 시 대상 기간 외 시장 동향 유입(`first_collect_news`)을 정면 진단 카드로 정리합니다.
  - **해결 구조**: 사전 조사(`comparison_target_counts`), 총괄 지휘(`disclosure_pilot_org`, `disclosure_batch_org_count`), 수집 구현, 독립 점검(`disclosure_batch_auto_org_count`, 점검 모델 sonnet)의 정면 분업 흐름에 이어, 시범 기준 중심탑 둘레에 배치된 대상 보험사(`disclosure_batch_orgs`, `disclosure_batch_pdf_count`, `disclosure_batch_test_count`) 막대들이 두 차례 3차원 파동에 맞춰 대표 상품 문서 수집과 해시 점검 단계로 전환되는 입체 구도를 보여 주고, 정면 2차원의 요일별 검색 배분(`collect_daily_plan`) 및 기간 외, 대상 외 종목 필터링(`news_excluded_lines`, `news_excluded_topics`)으로 연결합니다.
- **4장. 추출 단계: 상품요약서와 사업방법서의 급부 및 가입한도 추출**
  - **발생 문제**: 한도와 도구(`daily_limit_extract`, `daily_limit_upper`), 초기 추출 호출 부담(`hanwha_first_extract`), 수치 직접 추출 오류(`targeted_anticancer_misread`, `text_switch_confirmed_rows`), 이미지형 요약서와 대조용 로컬 문자 인식(OCR) 결과(`image_doc`, `local_ocr_test`), 모의 시트 테스트의 특약 가입한도 초기화(`rider_limit_rows_protected`)를 정면에서 진단합니다.
  - **해결 구조**: 모델은 원문 텍스트만 추출하고 수치 계산은 코드가 수행하는 분리 원칙(`text_switch_confirmed_rows`, `samsungfire_crosscheck_rows`, `benefits_by_org`)을 설명 카드로 두고, 경과 기간, 개정 차수, 실제 지급액 세 축이 만나는 3차원 계단 지형(`example_targeted_anticancer`)을 조감한 뒤, 제미나이 패널과 sonnet 에이전트의 상하 2단 3차원 시트 이중 추출 교차 검증과 정면 확대경(`image_doc`, `image_doc_same_reader_repeat`, `id_inherit_simulated_rows`)으로 마무리합니다.

### Part 3. 판정 모델 원리와 검증, 분류 단계 (`part3_decision.py`)
- **5장. 판정 모델 원리와 적용 영역**
  - 정면 2차원 화면에서 일반 텍스트 생성 호출(생성형 방식)과 비생성 판정 모델(`models.decide`, `decision_model_release_date`, `decision_model_spec`)의 선택지별 확률 반환(`symmetric_choice_probability`) 및 적용 영역(`decision_model_uses`)을 대비하고, 입력 단위인 특약 단위(추출 단위)와 호출당 문항 사양, 정형 판정 방식, 표본 기반 임계값 보정(`calibration_flipped_rows`, `calibration_reextract_band`) 카드를 시연합니다.
- **6장. 검증, 분류 단계: 분당 토큰 한도와 확률 임계값 설계**
  - 정면에서 참/거짓 질의의 확률 중첩(`true_false_probability_range`), 특약 부가 조건 일괄 질의 시 오류 통과(`bundled_constraint_check`), 매핑 재질의 예상 소요 시간(`mapping_requery`)을 진단한 뒤, 확정 기준면과 재추출 기준면(`verify_confirm_threshold`, `verify_reextract_threshold`) 두 수평 기준면이 가로지르는 3차원 확률 공간에서 변경 전후 막대(`symmetric_choice_probability`, `bundled_constraint_check`, `calibration_flipped_rows`)가 상하로 분리되는 입체 구도를 보여 주고, 정면 2차원의 확률 임계값 분기(자동 확정, 검수 대기 이관, 타 모델 재추출)와 분당 토큰 대기 기준(`decide_token_window`, `decide_tokens_per_minute_guard`, `decide_per_minute_limit`), 시장 동향 분류(`market_news_categories`, `market_news_by_category`, `decide_quota_failures_logged`)로 이어집니다.

### Part 4. 온톨로지 구조, 관계 탐색, 전후 비교 (`part4_ontology_impact.py`)
- **7장. 온톨로지와 단독 화면: 명칭 불일치와 매핑 검수 대기 해결**
  - 정면에서 종형명과 특약명 불일치(`default_base_variant`, `peer_held_coverage`), 한화 매핑 검수 대기(`dictionary_initial_size`, `hanwha_pending_before_rerun`, `hanwha_pending_after_rerun`), 특약별 보험료 공시 부재(`premium_example_rows`)를 짚은 뒤, 원천 사실 계층에서 표준 기준 계층과 분석, 인사이트 계층으로 연결되는 3차원 세 계층 구조와 정면 3단 도식(`site_org_count`, `variant_count_site`, `rider_count_site`, `benefit_count_site`, `market_news_count`, `standard_coverage_in_use`, `coverage_relations_by_kind`), 3차원 성좌 관계망(`mapping_status_site`, `benefits_without_mapping`, `coverage_relation_count`), 정면 표준담보 사전 확장 카드(`dictionary_first_expansion_added`, `dictionary_second_expansion`, `standard_coverage_rows`, `dictionary_expansion_survey_org_count`, `dictionary_addition_rule`, `standard_coverage_names`, `product_org_count`, `id_inherit_simulated_rows`)를 표시합니다.
- **8장. 포함, 통합 관계 탐색과 실행: 담보 관계망부터 응대 화법까지**
  - 상단 포함 계보와 하단 통합 대 분리 입체 분기(`standard_coverage_names`, `coverage_relations_by_kind`, `relation_covered_coverages`)를 따라 두 경로의 3차원 광선이 분기한 뒤 우체국 상품으로 수렴하는 3차원 공간 탐색에 이어, 정면 2차원으로 전환해 고객군별 가입 가능 현황(`segment_map_rows`, `segment_map_columns`, `segment_map_cell_count`, `segment_map_labels`, `segment_map_grid`, `segment_map_open_together_cells`, `segment_map_ours_closed_cells`, `segment_map_ours_only_open_cells`, `segment_map_gate_only_cells`), 치료 단계별 보유 담보 막대(`treatment_stages`, `held_coverage_by_stage`, `held_coverage_count`), 특약 부가 조건 및 주계약 가입한도(`reference_main_contract_limit_manwon`, `combination_constraints_by_org`), 영업 인사이트 분류(`sales_insight_categories`, `sales_insight_by_category`, `briefing_by_base_variant`)와 창구용 A4 응대 화법 문서(`card_category_order`)를 표시합니다.
- **9장. 기존 수작업 방식과 본 시스템의 구현 구조**
  - 기존 수작업 방식 대비 마스터 데이터와 단독 HTML 화면, 작업 로그(`work_log_count_site`), 이미지형 요약서 이중 추출 교차 검증(`image_doc`)과 표본 임계값 보정(`calibration_flipped_rows`), 매핑 검수 대기(`mapping_status_site`)와 판정 보류(`no_verdict_pairs`) 분리 결과를 정리하고, 전체 자동 테스트 건수(`test_count`), 브라우저 점검(`site_browser_check_problems`), 차기 단계 과제(`premium_example_rows`, `benefit_disease_code_rows`), 미측정 과제(`not_yet_measured`)를 함께 명시합니다.
