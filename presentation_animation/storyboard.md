# 우체국보험 상품-영업 분석: 발표 시연 애니메이션 스토리보드

본 영상은 모든 수치와 항목 이름을 `presentation_animation/facts.json`에서 조회하여 표시하며, 화면 용어는 `common.py`의 보험과 IT 실무 용어 상수(`TERM`, `label_ko`)로 통일합니다. 단순 인물 도형과 반복형 박스 격자를 배제하고 `infographics.py`의 정밀 SVG 벡터 인포그래픽 아이콘과 다크 슬레이트, 골드 A4 장표를 사용하며, 각 장의 내용에 맞는 고유한 시각 구조(흐름 관로, 대칭 오케스트레이션 회로, 문서 해부 워크벤치, 패킷 청사진, 분포와 누적 막대, 스키마 진단 보드, 엔드투엔드 파이프라인)로 연출합니다. 세 축(가로, 깊이, 높이)에 모두 구조적 의미가 있는 핵심 원리 구간은 3차원(`ThreeDScene`) 입체 기하와 고대비 정면 고정 빌보드 배지(`bb_badge`)로 시연하며, 발표자가 현장에서 설명하며 진행할 수 있도록 핵심 장면마다 충분한 정지 호흡을 둡니다.

전체 이야기는 다음 네 단계 흐름을 따릅니다.
1. **구축 목표 서비스와 전달 구조** (1장)
2. **구현한 운영 화면 구성** (2장)
3. **단계별 가용 자원과 발생 문제, 그리고 해결 구조** (3~8장)
4. **기존 수작업 병목 대비 4단계 엔드투엔드 시스템 구조 및 미측정 과제** (9장)

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
  - **현실 문제**: 정밀 비교 대상 타사(`comparison_target_counts`), 대용량 상품요약서(`hanwha_summary_pages`), 텍스트가 이미지로 수록된 상품요약서(`image_doc.pages`)를 실측 쪽수 비례 높이의 3차원 문서 협곡과 정면 빌보드 배지로 비행 조감한 뒤, 정면 2차원 화면으로 전환해 고지항목 범위와 지급기준(`example_targeted_anticancer`, `benefits_by_org_basis`)이 상이한 구조와 창구 지점 인포그래픽 구간의 전달 단절을 클로즈업합니다.
  - **목표 구조**: 기관 보도자료(`market_news_institution_count`)와 공시 문서가 정제 과정을 거쳐 구글 시트 마스터 데이터(`sheet_tab_count`)와 스냅샷(특정 시점의 데이터 복사본)에 적재되고, 기본 조건(`reference_condition`, `default_base_variant`)을 반영한 상품-영업 분석 오프라인 단독 HTML 화면(`operating_cost_won`, `site_browser_check_problems`, `standard_coverage_in_use`, `compared_coverage_pairs`, `forbidden_words`)과 다크 테마에 맞춘 창구용 A4 단일 응대 화법 장표(`card_category_order`, `lead_strengths`)로 연결됩니다.
- **2장. 구현한 운영 화면 구성 (`site_screen_count`)**
  - 정면 2차원 구도에서 중앙 기본 조건 다이얼(`reference_condition`, `default_base_variant`)이 회전하며 벡터 아이콘 헤더를 갖춘 운영 화면(`site_screen_count`)으로 연결됩니다. 선택한 조건과 기준 종형에 연동되어 값이 함께 바뀌는 조건 연동 화면은 인수기준(가입 심사 기준) 비교, 표준담보(`standard_coverage_in_use`, `compared_coverage_pairs`)와 미보유 담보 비교 및 A4 단일 응대 화법 출력, 특약 부가 조건과 감액기간을 반영한 특약 조합별 실제 지급액, 개정 전후 비교(`example_targeted_anticancer`, `revision_changes`) 화면이며, 실선 화살표로 연결합니다. 선택한 조건과 무관한 화면은 종합 요약과 주간 시장 동향(`screen_market_news`, `market_news_institution_count`: 우열 변화는 기본 조건 산출)과 AI 작업 내역(`work_log_count_site`: 화면에 올린 기관 기준 로그 건수, 결과별 막대는 전체 기관 기준 `work_log_by_result`) 화면이며, 점선으로 구분해 시연합니다.

### Part 2. 수집 단계와 추출 단계 (`part2_collect_extract.py`)
- **3장. 수집 단계: 회사별 상품공시와 주간 시장 동향 수집**
  - **발생 문제**: 상단 자원 텔레메트리 바(`daily_limit_search`, `actions_free_minutes_per_month`, `operating_cost_won`, `team_size`) 아래에서 좌우 수집 관로를 따라 모델 미지정 구현 에이전트 실행(`unpinned_agent_incident`), 목록 요청 방화벽 차단(`hanwhafire_block_status`), 검색 후보 오류(`search_candidates_rejected`) 및 API 보관 상한(`news_api_storage_limit_days`), 초기 수집 시 대상 기간 외 시장 동향 유입(`first_collect_news`) 네 병목 구간을 순차 시연합니다.
  - **해결 구조**: 상단 사전 조사(`comparison_target_counts`)에서 중앙 대칭 회로형 Claude 총괄 오케스트레이터 허브(`disclosure_pilot_org`, `disclosure_batch_org_count`)를 거쳐 좌측 대상사 수집 모듈 행렬과 우측 이중 PDF 해시 검증기(`disclosure_batch_auto_org_count`, 점검 모델 sonnet)로 분기하는 컨트롤 플레인에 이어, 시범 기준 중심탑 둘레에 배치된 대상 보험사(`disclosure_batch_orgs`, `disclosure_batch_pdf_count`, `disclosure_batch_test_count`) 막대들의 3차원 파동 조감도와 정면 2차원의 요일별 검색 배분(`collect_daily_plan`) 및 기간 외, 대상 외 종목 필터링(`news_excluded_lines`, `news_excluded_topics`)으로 연결합니다.
- **4장. 추출 단계: 상품요약서와 사업방법서의 급부 및 가입한도 추출**
  - **발생 문제**: 상단 한도 바(`daily_limit_extract`, `daily_limit_upper`) 아래 3열 문서 해부 워크벤치에서 초기 추출 호출 비중(`hanwha_first_extract`) 및 이미지형 요약서와 대조용 로컬 문자 인식(OCR) 한계(`image_doc`, `local_ocr_test`), 수치 직접 추출 오독 대비 원문 전환 확정 증가(`targeted_anticancer_misread`, `text_switch_confirmed_rows`), 모의 시트 테스트의 특약 가입한도 초기화와 보호 잠금(`rider_limit_rows_protected`)을 정밀 대조합니다.
  - **해결 구조**: 모델은 원문 텍스트만 추출하고 수치 계산은 코드가 수행하는 분리 원칙(`text_switch_confirmed_rows`, `samsungfire_crosscheck_rows`, `benefits_by_org`)에 이어, 경과 기간, 개정 차수, 실제 지급액 세 축이 만나는 3차원 계단 지형(`example_targeted_anticancer`)을 조감한 뒤, 제미나이 패널과 sonnet 에이전트의 상하 2단 3차원 시트 이중 추출 교차 검증과 정면 확대경(`image_doc`, `image_doc_same_reader_repeat`, `id_inherit_simulated_rows`)으로 마무리합니다.

### Part 3. 판정 모델 원리와 검증, 분류 단계 (`part3_decision.py`)
- **5장. 판정 모델 원리와 적용 영역**
  - 상하 이중 트랙 아키텍처로 순차 토큰 생성 방식과 비생성 판정 모델(`models.decide`, `decision_model_release_date`, `decision_model_spec`)의 병렬 선택지 확률 산출(`symmetric_choice_probability`) 및 우측 4대 적용 영역 버스(`decision_model_uses`)를 대비한 뒤, 좌에서 우로 흐르는 1회 호출 패킷 청사진을 통해 특약 단위(추출 단위) 입력 엔벨로프, 정형 채점 사양, 표본 기반 임계값 보정 결과(`calibration_flipped_rows`, `calibration_reextract_band`)를 시연합니다.
- **6장. 검증, 분류 단계: 분당 토큰 한도와 확률 임계값 설계**
  - 3분할 수리 데이터 뷰포트에서 참/거짓 질의의 확률 분포 중첩 곡선(`true_false_probability_range`), 특약 부가 조건 일괄 질의 캡슐 누수(`bundled_constraint_check`), 매핑 재질의 예상 소요 시간 비례 누적 막대(`mapping_requery`)를 진단한 뒤, 확정 기준면과 재추출 기준면(`verify_confirm_threshold`, `verify_reextract_threshold`)이 가로지르는 3차원 확률 공간에서 변경 전후 막대(`symmetric_choice_probability`, `bundled_constraint_check`, `calibration_flipped_rows`)가 분리되는 입체 구도를 보여 주고, 정면 2차원의 프로세서 임계값 분기 라우터와 분당 토큰 슬라이딩 윈도우(`decide_token_window`, `decide_tokens_per_minute_guard`, `decide_per_minute_limit`), 시장 동향 유형별 실측 가로 막대 차트(`market_news_categories`, `market_news_by_category`, `decide_quota_failures_logged`)로 이어집니다.

### Part 4. 온톨로지 구조, 관계 탐색, 엔드투엔드 아키텍처 (`part4_ontology_impact.py`)
- **7장. 온톨로지와 단독 화면: 명칭 불일치와 매핑 검수 대기 해결**
  - 상단 배포 규격 바(`operating_cost_won`, `sheet_tab_count`, `site_browser_check_problems`) 아래 3열 스키마 진단 보드에서 명칭, 지급방식, 분리 구조 상이(`default_base_variant`, `peer_held_coverage`), 한화생명 매핑 검수 대기 감소 막대(`dictionary_initial_size`, `hanwha_pending_before_rerun`, `hanwha_pending_after_rerun`, `mapping_status_by_org`), 특약별 보험료 공시 부재(`premium_example_rows`)를 짚은 뒤, 3차원 세 계층 구조와 정면 3단 도식(`site_org_count`, `variant_count_site`, `rider_count_site`, `benefit_count_site`, `market_news_count`, `standard_coverage_in_use`, `coverage_relations_by_kind`), 3차원 성좌 관계망(`mapping_status_site`, `benefits_without_mapping`, `coverage_relation_count`), 표준담보 사전 확장 패널(`dictionary_first_expansion_added`, `dictionary_second_expansion`, `standard_coverage_rows`, `dictionary_expansion_survey_org_count`, `dictionary_addition_rule`, `standard_coverage_names`, `product_org_count`, `id_inherit_simulated_rows`)을 표시합니다.
- **8장. 포함, 통합 관계 탐색과 실행: 담보 관계망부터 응대 화법까지**
  - 상단 포함 계보와 하단 통합 대 분리 입체 분기(`standard_coverage_names`, `coverage_relations_by_kind`, `relation_covered_coverages`)를 따라 두 경로의 3차원 광선이 분기한 뒤 우체국 상품으로 수렴하는 3차원 공간 탐색에 이어, 정면 2차원 인수기준 대시보드에서 고객군별 가입 가능 현황(`segment_map_rows`, `segment_map_columns`, `segment_map_cell_count`, `segment_map_labels`, `segment_map_grid`, `segment_map_open_together_cells`, `segment_map_ours_closed_cells`, `segment_map_ours_only_open_cells`, `segment_map_gate_only_cells`), 치료 단계별 보유 담보 타임라인(`treatment_stages`, `held_coverage_by_stage`, `held_coverage_count`), 특약 부가 조건 및 주계약 가입한도(`reference_main_contract_limit_manwon`, `combination_constraints_by_org`), 그리고 축소 없는 상품-영업 분석 화면의 영업 인사이트 가로형 데이터 콘솔(`sales_insight_categories`, `sales_insight_by_category`, `briefing_by_base_variant`)과 다크 슬레이트 A4 응대 화법 장표(`card_category_order`)를 표시합니다.
- **9장. 기존 수작업 방식과 본 시스템의 구현 구조**
  - 상단의 기존 수작업 3대 병목이 4단계 엔드투엔드 자동화 파이프라인(① 수집 및 마스터 적재, ② 원문 추출 및 코드 계산, ③ 비생성 판정 및 표준담보, ④ 단독 화면 및 A4 응대 화법: `work_log_count_site`, `image_doc`, `calibration_flipped_rows`, `mapping_status_site`, `no_verdict_pairs`)으로 전환되는 아키텍처를 시연하고, 하단 점검 도크에 전체 자동 테스트 건수(`test_count`), 브라우저 점검(`site_browser_check_problems`), 차기 단계 과제(`premium_example_rows`, `benefit_disease_code_rows`), 미측정 과제(`not_yet_measured`)를 함께 명시합니다.
