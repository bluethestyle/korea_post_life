# 요청 29. 발표 영상(PR 7번)의 숫자를 사실 자료에서 읽게 고치기 (Antigravity 개발 에이전트용)

PR 7번(`presentation_animation/`, Manim 발표 영상)을 Claude가 검수했습니다. 영상에 띄우는 숫자와 주장이 코드에 글자로 박혀 있고, 그 가운데 여럿이 지금 자료와 맞지 않거나 저장소에 근거가 없습니다. 화면과 같은 규칙으로 고칩니다. 숫자, 판정, 문장은 Claude 쪽 계산에서 나오고 영상은 자료 파일을 읽기만 합니다. 그래서 `main`에 사실 자료 `presentation_animation/facts.json`과 그것을 만드는 `scripts/export_presentation_facts.py`를 올렸습니다. 이 문서는 그 파일을 읽는 규칙과, 지금 코드에서 고칠 곳의 목록입니다.

## 사람이 할 일

Antigravity에 이 한 줄을 넣습니다.

> `git fetch origin` 뒤 작업 가지 `antigravity/presentation-animation`을 `origin/main` 위에 올리고, `docs/gemini_requests/29_발표영상_사실자료와_고칠곳_Antigravity.md`를 읽어 그대로 고쳐라. `presentation_animation/facts.json`은 고치지 않는다.

---

## 1. 규칙

1. 영상에 띄우는 숫자는 모두 `presentation_animation/facts.json`에서 읽습니다. `common.py`에 읽는 함수를 하나 두고 모든 장면이 그것만 씁니다.

   ```python
   import json
   from pathlib import Path

   _FACTS = json.loads(Path(__file__).with_name("facts.json").read_text(encoding="utf-8"))["facts"]


   def fact(key: str, *path):
       """facts.json 의 값. 열쇠가 없으면 KeyError 로 멈춘다(기본값을 두지 않는다)."""
       value = _FACTS[key]["value"]
       for p in path:
           value = value[p]
       return value


   def num(n) -> str:
       """천 단위 쉼표. 1274 → "1,274"."""
       return f"{n:,}"
   ```

   쓰는 예: `txt(f"급부 {num(fact('benefit_count_site'))}줄")`, `fact("mapping_status_site", "대기")`, `fact("example_targeted_anticancer", "revisions", -1, "pay_manwon")`.
2. 코드에 숫자를 글자로 박지 않습니다. 화면 글의 숫자는 f-string 자리에 facts 값을 넣어서만 나옵니다. 두 값으로 계산하는 것(차, 비율, 개월을 년으로 바꾸기, 만 단위 반올림)은 코드에서 해도 되지만, 계산에 쓰는 수는 facts 값이어야 합니다. 축 끝의 0과 1, 좌표, 크기, 시간처럼 사실이 아닌 수는 그대로 둡니다.
3. `facts.json`은 Claude 쪽에서 만들고 Antigravity는 고치지 않습니다. 열쇠마다 `value`(값), `label`(짧은 이름), `as_of`(기준일), `source`(사본이면 파일과 세는 방법, 문서면 경로와 절과 근거 문구)가 있고, 일부에는 `note`(쓸 때 같이 적어야 하는 단서)가 있습니다. note가 있는 값은 note의 뜻을 영상에 함께 적거나, 적을 자리가 없으면 그 값을 쓰지 않습니다.
4. 자료에 없는 수가 필요하면 지어내지 말고 PR 글에 "필요한 값"으로 적습니다(무엇을, 어느 장면에, 왜). Claude가 사본이나 화면 자료에서 세어 facts.json에 더합니다. 외부 사실(다른 회사의 모델 출시 같은 것)을 쓰고 싶으면 공개 출처 주소를 PR 글의 "필요한 사실"에 적습니다. Claude가 확인하기 전에는 영상에 넣지 않습니다.
5. 장식으로 쓰는 게이지, 도넛, 점 행렬, 관계망의 점선 비율, 막대 분포도 실제 값이 없으면 수치처럼 보이게 그리지 않습니다. 채움 비율은 facts 값 둘로 계산할 수 있을 때만 쓰고(예: 한화생명 첫 추출 호출 수 나누기 추출 모델 하루 한도), 그 두 수를 함께 적습니다. 그렇지 않으면 채움 없는 배지로 그리거나 "예시 그림"이라고 표시합니다.
6. 사본 전체와 화면 기준을 섞지 않습니다. 열쇠 끝이 `_site`이면 화면에 올린 세 회사(우체국, 한화생명, 삼성화재)만 센 값이고, `_all`이면 사본에 든 모든 회사(지금은 메리츠화재까지 넷)를 센 값입니다. 끝말이 없는 `work_log_count`, `benefits_by_org` 같은 열쇠는 label에 범위를 적었습니다. 한 장면 안에서는 한쪽으로 맞추고 어느 쪽인지 적습니다.
7. 화면 자료에서 옮긴 값(`source.kind`가 `screen_data`)은 대표 조건(`reference_condition`, 50세 남성, 이력 없음)과 화면이 처음 여는 기준 종형(`default_base_variant`)의 값입니다. 다른 기준 종형의 값은 `briefing_by_base_variant`에 있습니다. 다른 종형을 쓰면 그 종형 이름을 영상에 적습니다.

고칠 수 있는 파일: `presentation_animation/` 아래의 `*.py`, `README.md`, `storyboard.md`, `requirements.txt`, `.gitignore`.
고치면 안 되는 파일: `presentation_animation/facts.json`, `scripts/export_presentation_facts.py`, `tests/test_presentation_facts.py`, 그리고 `data/`, `proto_src/`, `site/`, `src/`, `docs/`(이 문서 포함). 자료가 틀려 보이면 고치지 말고 PR 글에 적습니다.

## 2. 고칠 곳

줄 번호는 PR 7번 가지의 지금 파일 기준입니다. 파일 이름은 `part1`(`part1_service.py`), `part2`(`part2_collect_extract.py`), `part3`(`part3_decision.py`), `part4`(`part4_ontology_impact.py`), `common`(`common.py`)으로 줄여 적습니다. "열쇠"는 facts.json의 열쇠입니다. 숫자가 맞는 줄도 코드에 박혀 있으므로 모두 열쇠에서 읽게 바꿉니다.

### 공통 부품

| 자리 | 지금 글 | 문제 | 고칠 방법 |
| --- | --- | --- | --- |
| common:138-166 `capacity_ring` | 채움 비율 `ratio`를 받아 호를 그리고 `min(max(ratio, 0.05), 1.0)`으로 자른다 | 실제 값이 없는 비율도 게이지처럼 그려지고, 0이어도 5%가 채워진다 | 규칙 5대로 고친다. 비율 인자를 빼고 한도 숫자만 보이는 배지로 바꾸거나, facts 값 둘로 계산한 비율만 받는다. 0은 0으로 그린다 |

### 1장과 2장 (`part1`)

| 자리 | 지금 글 | 문제 | 고칠 방법 |
| --- | --- | --- | --- |
| part1:77 | `19개 기관 · 최대 567쪽` | 19는 시장 소식을 모으는 기관 수라 "수백 쪽 공시 문서" 장면과 범위가 섞였다 | 쪽수는 `hanwha_summary_pages`(한화생명 한 상품의 요약서). 회사 수를 같이 쓰려면 `comparison_target_counts`의 합을 "정밀 비교 대상"이라고 적어 쓴다 |
| part1:78 | `308쪽 조각 그림 포함` | 값은 맞다. "조각 그림"은 뜻이 흐리다 | `image_doc`의 `pages`. "글자가 그림으로 든 요약서" |
| part1:102 | `가입금액 50%`, `정액 2,000만` | 출처 없는 예시 숫자다 | 정액 예는 `example_targeted_anticancer`의 `revisions[-1].pay_manwon`(기준 가입금액 `basis_manwon`에 대한 지급액). 비율 쪽은 숫자 없이 "가입금액의 N%" 꼴만 보이거나, `benefits_by_org_basis`로 비율로 적는 회사를 보인다 |
| part1:189 | `서버·DB 운영비 0원 · 공개 근거 100% 직결` | "공개 근거 100% 직결"은 근거가 없다 | 0원은 `operating_cost_won`(note대로 무료 도구만으로 짠 설계라고 적는다). "100% 직결"은 지우고 "칸을 누르면 원문 특약명, 근거 문서, 쪽수가 열림"으로 바꾼다 |
| part1:208 | `19개 기관 보도·개정` | 뜻은 맞다 | `market_news_institution_count` |
| part1:214 | `구글 시트 정본 13탭` | 값은 맞다 | `sheet_tab_count` |
| part1:225 | `외부 통신 0건` | 값은 맞다 | `site_browser_check_problems`(브라우저 점검의 외부 요청 수) |
| part1:230-232, 358-360 | `50세`, `남성`, `간편심사 2년형 ✓`, `50세 · 남성`, `간편 2년형` | "2년형"인 종형은 없다. 화면이 처음 여는 기준 종형은 다른 이름이다 | `reference_condition`의 `age`, `sex`(M은 남성), `default_base_variant`의 `name` |
| part1:240, 244, 390, 392 | `우체국 입원만 ▲`, `민영 입원·수술 ×`, `우체국 : 입원만 ▲`, `민영 : 입원·수술 ×` | 내용은 맞다(`docs/submission.md` 2절의 표). "민영"은 견준 회사를 가리키지 않는다 | 회사 이름은 `site_orgs`에서 우체국을 뺀 회사의 `org_names`. "입원·수술"은 "입원 또는 수술" |
| part1:248, 417 | `76종 담보 우열`, `표준담보 76종 비교표` | 사전은 지금 87줄이고 쓰는 담보는 86개다. 우열은 견준 쌍에서만 매긴다 | `standard_coverage_in_use`, 단위는 "개". 우열 수를 쓰려면 `compared_coverage_pairs` |
| part1:257 | `약관 p.142 직결` | 지어낸 쪽 번호다. 이 앱은 약관이 아니라 요약서와 사업방법서의 쪽을 단다 | `example_targeted_anticancer`의 `revisions[-1].doc_kind`, `doc_pages`("요약서 16쪽" 꼴) |
| part1:264 | `감액 → 100%` | 예시 값이다 | 감액 개월 수와 비율은 `example_targeted_anticancer`의 `revisions[-1].reduce`. 그 뒤는 숫자 없이 "전액" |
| part1:266, 450 | `변수 밖 숫자 · 금지 단정어 빌드 자동 차단 ✓`, `... 공시 없는 값(특약 보험료 등) 억지 추정 표시 제외 ✓` | 내용은 맞다 | 금지어 수를 쓰려면 `forbidden_words`의 길이. 보험료 자료가 없다는 것은 `premium_example_rows` |
| part1:277, 282 | `A4 1장 출력`, `대외 배포 금지 · A4 1매` | "1장", "1매"가 박힌 숫자다 | "A4 한 장" |
| part1:287 | `▲ 수술이력 청약 적격` | 화면은 가입 여부를 단정하지 않는다(가입 여부는 청약 뒤 심사로 정해지고, "가입됩니다"는 화면 금지어) | "수술 이력 고객의 고지 질문 차이"처럼 관문 차이로 적는다. 카드의 차례는 `card_category_order` |
| part1:289, 415 | `§ 감액조건 · 약관 쪽수`, `약관 p.쪽수 · 카드 인쇄` | 약관 쪽이 아니다 | "근거 문서와 쪽수" |
| part1:348, 349 | `6대 기능`, `6개 시각 모듈` | 값은 맞다 | `site_screen_count` |
| part1:383, 386 | `19개사 동향`, `우열 변동 ▲`, `신규·종료 개정 · 주간 동향 · 우열 변동 포착` | 19는 우체국을 포함한 기관 수라 "개사"가 아니다. 우열 변화는 지난주 사본과 견줘야 나온다(`docs/limitations.md` 5절) | `market_news_institution_count`와 "기관". 운영 화면 1에 우열 변화가 실제로 나오는지 확인하고, 나오지 않으면 "지난주 사본이 쌓이면 보임"으로 적거나 지운다. 이번 주 소식은 `screen_market_news` |
| part1:405 | `특약 조합별 실수령액` | "실수령액"은 이 앱의 말이 아니다 | "실제 지급액" |
| part1:421, 423 | `2504 (1천만·2년)`, `2606 (2천만·1년 ▲)` | 값은 맞다 | `example_targeted_anticancer`의 `revisions[i]`에서 `revision_no`, `pay_manwon`, `reduce[0].months`(개월을 년으로 바꾸는 것은 코드에서). 달라진 담보 수는 `revision_changes` |
| part1:435 | `판정 확률 · 로그 13,671건 공개` | 옛 사본의 값이다 | 화면 6에 실리는 건수 `work_log_count_site`(사본 전체는 `work_log_count`) |

### 3장과 4장 (`part2`)

| 자리 | 지금 글 | 문제 | 고칠 방법 |
| --- | --- | --- | --- |
| part2:47, 88, 180 | `19개사 공시 장벽`, `19개사 규격 상이`, `19개사 선정` | 정밀 비교 대상 수인데 박혀 있다 | `comparison_target_counts`의 합 |
| part2:48 | `27건 중 23건의 기간 경과 기사 유입` | 값은 맞다 | `first_collect_news`의 `structured`, `out_of_window` |
| part2:59 | `최상위 AI`, `주간 한도 빠듯`, 채움 0.84 | 채움 0.84는 근거가 없다 | 채움 없이 글로만(근거는 `CLAUDE.md`의 "최상위 모델 한도가 빠듯하다") |
| part2:60 | `무료 검색`, `일 20회 상한`, 채움 0.20 | 채움 0.20은 근거가 없다 | `daily_limit_search`, 채움 없음 |
| part2:63 | `무서버 배치 (월 2,000분 무료)` | 값은 맞다 | `actions_free_minutes_per_month` |
| part2:64 | `유료 크롤링·뉴스 API 예산 0원` | 값은 맞다 | `operating_cost_won` |
| part2:65 | `1인 체제 · 19개 기관 상시 점검` | 값은 맞다 | `team_size`, `market_news_institution_count` |
| part2:80, 85 | `문제 ① 모델 미지정 시 최상위 한도 급감`, `최상위 모델 자동 호출 소모 · 구두 보고 불신` | 한도가 얼마나 줄었는지는 문서에 없다 | `unpinned_agent_incident`의 뜻(모델을 지정하지 않은 구현 에이전트 하나가 최상위 모델로 돌았다)으로 바꾸고 "급감"은 지운다 |
| part2:94 | `400 차단 ×` | 값은 맞다 | `hanwhafire_block_status` |
| part2:99, 100 | `후보A : 503 오류 ×`, `후보B : 출처 0건 ×` | 값은 맞다 | `search_candidates_rejected`의 `error_status`, `sources_found` |
| part2:103 | `포털 API 보관제한` | 뜻은 맞다 | `news_api_storage_limit_days`("서버 보관 21일 제한" 꼴) |
| part2:106, 108-110, 116, 439 | `27건 중 23건 기간 경과`, `range(27)`, `k >= 23`, `붉은 점 23건 기간 밖 기사 · 유효 기사 단 4건`, `27건 중 기간 밖 23건 차단 ×` | 값은 맞고 박혀 있다. 4건은 구간 안이라는 뜻일 뿐 쓸 만한 기사인지는 아니다 | `first_collect_news`의 두 값. 남은 수는 두 값의 차로 계산하고 "구간 안 N건" |
| part2:160 | `4단계 에이전트 분업` | 숫자가 박혀 있다 | 단계 목록의 길이로 세거나 "조사, 총괄, 구현, 점검으로 나눈 분업" |
| part2:182 | `생보 10 · 손보 9곳 확정` | 값은 맞다 | `comparison_target_counts`. note(총자산 기준이고 출처가 기사라 순위는 확정하지 못함)를 작은 글씨로 |
| part2:187 | `DB손보 시범표준` | 값은 맞다 | `disclosure_pilot_org` |
| part2:190 | `파일 충돌 0건 · 16개사 배분` | "파일 충돌 0건"은 근거가 없다 | 지운다. 16은 `disclosure_batch_org_count`. 총괄은 메인 세션(Claude)이 맡았다 |
| part2:201, 209, 259-261 | `15곳 자동 · 차단 1곳 수동분리`, `③ 수집 구현 ×16`, `④ 독립 검증 ×16`, `검증 전용 경량 모델`, `③ 수집 에이전트 ×16`, `④ 검증 에이전트 ×16` | 접속 모듈이 없는 한화손해보험은 실제 호출 점검을 할 수 없어 점검은 15곳이다. 점검 모델은 sonnet이고 가벼운 모델이 아니다 | 구현은 `disclosure_batch_org_count`, 점검은 `disclosure_batch_auto_org_count`, 차단된 곳은 둘의 차. "점검 모델(sonnet)" |
| part2:194, 320, 347 | `range(16)` | 박힌 수다 | `len(fact("disclosure_batch_orgs"))` |
| part2:221, 306 | `전체 시험 579건 통과 · 공시 문서 58종 PDF 진본·쪽수 직접 확인 ✓`, `15개사 무인증 자동수집·해시검증 완료 · 1개사(한화손보) 수동 분리 · 문서 58종 진본 확정 ✓` | 579는 그때의 전체 시험 수다. 58은 문서 수라 "종"이 아니다 | `disclosure_batch_test_count`("그때"라고 적는다), `disclosure_batch_pdf_count`("문서 58개" 꼴), `disclosure_batch_auto_org_count` |
| part2:250 | `16개 보험사에 ... 접속 차단 1곳은 우회 없이 수동 분리합니다` | 위와 같다 | 위와 같다. "사람이 내려받습니다" |
| part2:269-272, 283-284 | 타일 `DB손보`, `삼성화재`, `한화생명`, `삼성생명` ... `미래에셋` | 16개 타일에 삼성화재, 한화생명, DB손해보험이 들어 있고 KB라이프생명, 메트라이프생명, 흥국화재가 빠졌다 | 타일은 `disclosure_batch_orgs`에서 읽는다. DB손해보험(`disclosure_pilot_org`)은 시범으로 따로 둔다. 차단 표시는 한화손해보험 |
| part2:386, 420 | `하루 20회 검색 한도에 맞춰 ... 기간 밖 23건을 걸러냈습니다`, `일 20회 무료 한도 안에서 19개 기관 순환 점검` | 값은 맞다 | `daily_limit_search`, `first_collect_news`, `market_news_institution_count` |
| part2:400-401 | `월 대형 생보`, `화 대형 손보`, `수 주력 손보`, `목 중견 생보`, `금 우체국·손보`, `토 배타적사용권`, `일 누락분 보완` | "대형, 주력, 중견"은 근거 없는 판단이다(회사 순위는 확정하지 못했다) | `collect_daily_plan`의 요일별 기관 이름과 질의 수. 일요일은 질의가 0이고 note대로 "실패 건 재수집과 주간 마감" |
| part2:440 | `반려동물·운전자·단순 홍보 제외` | "운전자", "단순 홍보"는 설정에 없다 | `news_excluded_lines`, `news_excluded_topics` |
| part2:500, 524, 526, 529-530, 막대 `b_1doc`, `b_all` | `567쪽 한도 초과`, `문제 ① 567쪽 대용량 · 일일 한도 초과`, `일 500회 상한`, `1권 341회`, `19개사 초과!` | 첫 추출 341회는 하루 한도 500회 안이라 "초과"가 아니다. "19개사 초과"는 문서에 없는 어림이다 | `hanwha_summary_pages`, `hanwha_first_extract`의 `calls`, `daily_limit_extract`. 막대 높이는 두 값의 비율로. "19개사 초과"를 지우고, 그래서 기존 상품의 초기 적재를 API 한도를 쓰지 않는 길로 바꿨다고 적는다(`docs/planning.md` 6.1) |
| part2:510, 511 | `경량 추출 AI`, `일 500회 무료`, 채움 0.55, `상위 재추출`, `일 20회 상한`, 채움 0.16 | 채움은 근거가 없다 | `daily_limit_extract`, `daily_limit_upper`. 채움을 쓰려면 규칙 5대로 두 값으로 계산한 것만 |
| part2:516, 600, 608 | `정형 표 + 비정형 약관 혼재 환경`, `기존 대량 약관 초기 적재는 구독 패널·규칙 파서로 처리`, `약관 원문 문구` | 추출기는 약관이 아니라 요약서와 사업방법서를 읽는다(`docs/limitations.md` 1절). 초기 적재는 서브에이전트 두 판독도 쓴다 | "요약서", "기존 상품". 초기 적재는 "코드 규칙, 서브에이전트 두 판독, 제미나이 패널"(`docs/planning.md` 6.1) |
| part2:533, 541 | `문제 ② 숫자 직접 추출 오독 (확정 22/49줄)`, `초기 확정 줄 45% 정체 (22 / 49줄)` | 22/49줄과 오독 예(535, 537)는 서로 다른 일이다. 45%는 계산해 박은 값이다 | `text_switch_confirmed_rows`의 `before`, `total`. 비율 대신 "49줄 가운데 22줄" |
| part2:535, 537 | `원문 2천만·50%`, `1천만·1천만 ×` | 값은 맞다(표적항암약물허가치료특약 사례) | `targeted_anticancer_misread`. 50%는 `example_targeted_anticancer`의 `revisions[-1].reduce[0].rate` |
| part2:544, 553 | `문제 ③ 미래에셋 308쪽 조각 그림 문서`, `텍스트 분리 불가 · 자체 문자판독 210자 오류 ×` | 210은 빠뜨린 100자와 잘못 넣은 110자를 더한 값이고, 미래에셋 쪽이 아니라 글자가 풀리는 대조용 쪽에서 잰 값이다 | `image_doc`의 `pages`, `local_ocr_test`의 `chars`, `missed`, `wrong`. "로컬 OCR(tesseract)" |
| part2:546-551 | 모자이크 12칸 가운데 4칸을 오류로 칠함 | 장식 칸의 비율이 오류율처럼 보인다 | 규칙 5. 비율을 뜻하지 않게 하거나 `local_ocr_test`로 계산한다 |
| part2:557, 559 | `특약 한도 166줄`, `0줄 초기화 ×` | 값은 맞다. 실제로 잃은 것이 아니라 가짜 시트 시험에서 0줄이 된 결함을 실제 실행 전에 고쳤다 | `rider_limit_rows_protected`. "가짜 시트 시험에서" |
| part2:604-606, 613, 630-634 | `진단보험금 2,000만원`, `1년 미만 50% 감액`, `90일 면책기간`, `"2,000만원 / 1년미만 50% / 90일"`, 계단 그래프의 `1,000만`, `2,000만`, `90일 면책(0원)`, `1년 미만 (50% 감액)`, `1년 경과 (100% 지급)` | 급부 이름이 실제와 다르다(진단보험금이 아니라 표적항암약물허가치료보험금). 따옴표가 공시 원문 인용처럼 보인다 | `example_targeted_anticancer`의 `revisions[-1]`에서 `benefit`, `pay_manwon`, `waiting_days`, `reduce`. 감액 기간 지급액은 `pay_manwon`에 `reduce[0].rate`를 곱해 코드에서 계산. 따옴표 없이 값으로 보인다 |
| part2:612 | `확정 줄 22줄 → 39줄로 즉시 향상 ✓` | "즉시"는 근거가 없다 | `text_switch_confirmed_rows`의 `before`, `after` |
| part2:621 | `(삼성화재 681건 AI 없이 직접 추출)` | 681은 규칙 추출과 제미나이 독립 구조화를 줄마다 대조한 줄 수다. 지금 사본의 삼성화재 급부는 그보다 많다 | 대조를 말하면 `samsungfire_crosscheck_rows`, 규칙으로 읽은 전체를 말하면 `benefits_by_org`의 `SAMSUNGFIRE`. 어느 뜻인지 글에 적는다 |
| part2:670 | `재추출 유실 방지 장치를 더했습니다` | 실제 재추출에서는 아직 확인하지 않았다(`docs/limitations.md` 3절) | "지난 자료로 시험"이라고 덧붙인다 |
| part2:688, 689 | `1차 독립 판독 (모델 A)`, `2차 교차 판독 (다른 계열 모델 B)` | 실제로는 제미나이 구독 패널과 sonnet 에이전트가 따로 읽었다 | 두 판독기 이름으로 적는다. 같은 판독기를 되풀이하면 오류가 안 잡힌 근거는 `image_doc_same_reader_repeat` |
| part2:723, 725 | `오독: 1,000만원`, `원문 확정: 2,000만원 ✓` | 지어낸 장면이다. 두 판독의 지급률과 금액은 한 곳도 어긋나지 않았다 | 지운다. 대신 `image_doc`의 `amount_mismatches`와 "어긋난 글자 줄만 원본을 확대해 Claude가 판정" |
| part2:727 | `이미지 요약서 308쪽(31만 자) 지급액 불일치 0건 · 결과 파일 선보존 · 재추출 시 기존 확정 줄·급부ID(1,039줄) 보호 ✓` | 쪽수, 글자 수, 0은 맞다. 1,039줄은 지난 자료로 시험한 값이고 확정 줄 지키기는 실제 재추출에서 확인 전이다 | `image_doc`의 `pages`, `chars`(만 단위 반올림은 코드에서), `amount_mismatches`. `id_inherit_simulated_rows`와 그 note |

### 5장과 6장 (`part3`)

| 자리 | 지금 글 | 문제 | 고칠 방법 |
| --- | --- | --- | --- |
| part3:46, 90-91, 98, 169, 171 | `Jev가 연 패러다임과 Google decision-1 출시`, `2026.09 TypeSafe AI`, `비생성 판정 전용 모델 'Jev' 등장`, `Jev 판정 엔진`, `2026.09 TypeSafe 'Jev' 개척`, `(문서·다문항 확장)` | 저장소 문서에 근거가 없다 | 지운다. 남기려면 공개 출처 주소를 PR 글의 "필요한 사실"에 적는다(규칙 4). 모델 이름은 `models`의 `decide`, 나온 날은 `decision_model_release_date` |
| part3:47 | `'판정 전용 AI' 분야가 열렸습니다` | 업계 흐름에 대한 주장이고 근거가 없다 | "판정 모델은 글을 쓰지 않고 정해진 선택지마다 확률만 돌려준다"(`docs/submission.md` 5절) |
| part3:98, 183 | `출력 토큰 = 0`, `출력 토큰 0` | 값은 맞다 | `decision_model_spec`의 `output_tokens` |
| part3:102 | 막대 `0.94`, `0.04`, `0.02` | 0.04와 0.02는 지어낸 값이다 | 선택지 둘에 `symmetric_choice_probability`의 `correct_min`, `flipped_max`를 쓰거나 "예시"라고 표시 |
| part3:110, 125-128 | `어디에 쓰이는가? — 4대 실무 판단 영역`, `① 작업 경로 분기 (라우팅)` ~ `④ 추출 정합성 자동 채점` | 네 영역은 근거가 없다 | `decision_model_uses`(이 앱이 실제로 쓴 일) |
| part3:163 | `26만 토큰 문서 입력과 1,000문항 일괄 판정, 정밀 확률 보정을 갖췄습니다` | 26만 토큰과 정밀 확률 보정은 근거가 없다 | `decision_model_release_date`, `decision_model_spec`의 `items_per_call`. 나머지는 지운다 |
| part3:184 | `일 1만 회 무료` | 값은 맞다 | `daily_limit_decide` |
| part3:199-204 | `PDF 요약서`, `이미지·표`, `최대 26만 토큰`, `텍스트·이미지 혼합 공시 문서를 통째로 입력`, `특성 ① 대용량 복합 문서 직접 입력` | 근거가 없다. 이 앱은 특약 조각의 원문 글과 그 조각의 문항을 함께 보낸다(`docs/limitations.md` 3절) | 특성 ①을 그 내용으로 바꾸거나 지운다 |
| part3:209, 213 | `원문 1회`, `같은 원문을 한 번만 읽고 수백 문항 동시 채점`, `1회 입력 → 최대 1,000문항 일괄 판정` | 1,000은 모델 사양이다. "수백 문항 동시 채점"은 근거가 없다 | `decision_model_spec`의 `items_per_call`("한 번에 받을 수 있는 문항 수"). "수백 문항"은 지운다 |
| part3:217-221 | `예 / 아니오`, `2~255지선다`, `1~5 등급척도`, `정해진 선택지 확률만 반환 (응답 양식 오류 0건)`, `특성 ③ 3가지 정형 판정 방식` | 등급척도와 "응답 양식 오류 0건"은 근거가 없다 | `decision_model_spec`의 `choices_min`, `choices_max`. 등급척도 칸과 "0건"을 지우고 방식의 수는 남은 칸의 수로 |
| part3:230, 232 | `확률 = 실제 신뢰도`, `예측 확률이 실제 정답률과 부합해 자동 분기 가능`, `특성 ④ 정교한 확률 보정 (기준선 직결)` | 근거가 없다 | 우리 표본에서 잰 것으로 바꾼다: `calibration_flipped_rows`, `calibration_reextract_band`와 그 note(우체국 요약서 2건의 좁은 표본) |
| part3:269, 277, 311 | `분당 5만 토큰 한도 초과`, `호출 횟수는 일 10,000회로 넉넉하지만, 입력량은 '분당 50,000토큰' 상한 존재`, `분당 50K 상한` | 값은 맞다 | `decide_per_minute_limit`의 `tokens`, `daily_limit_decide` |
| part3:288, 293, 294, 388 | `정답 줄도 0.50~0.80에 머물러 경계 모호`, `0.50~0.80 겹침 !`, 눈금 `0.0 0.5 0.8 1.0`, `확률 0.50~0.80 구간 정체` | 값은 맞다 | `true_false_probability_range`. 축 끝 0과 1은 코드의 수로 두고 f-string으로 찍는다 |
| part3:297, 299-302, 304 | `선행·배타 특약을 뭉뚱그리면 오류 2개 통과`, 정상 둘과 오류 둘의 타일, `0.80 통과?!` | 2와 0.80은 맞다. 정상 특약 둘은 예시다. "선행·배타"는 문서에 없다 | `bundled_constraint_check`의 `wrong_riders`, `bundled_probability`. "결합 제약을 묶어 물으면" |
| part3:307, 313 | `대기 2,212줄 처리에 203분 병목 발생`, `203분 지연 !` | 203분은 실행 전에 어림한 값이고(기다림 49분 포함), 2026-11-20의 매핑 실행이다. 79.98K는 2026-11-19 사용량 화면의 값이라 다른 날의 일이다 | `mapping_requery`의 `rows`, `estimated_minutes`, `waiting_minutes`. "약 N분으로 어림". 79.98K와 한 장면에 묶지 않는다 |
| part3:312 | `최고 79.98K / 분 ×` | 값은 맞다 | `decide_tokens_per_minute_peak_k` |
| part3:343, 348, 351, 359 | `원문 1회 입력`, `원문 1회`, `1건씩 분리` | 숫자가 박혀 있다 | "원문을 한 번", "하나씩" |
| part3:353 | `급부 4항목 동시채점` | 문서에 수가 없다. 코드(`src/postlife/extract/verify.py`의 `checks`)는 지급액, 감액, 면책, 지급한도를 따로 묻고, 원문에 그대로 있으면 묻지 않는다 | 수를 빼고 "지급액, 감액, 면책, 한도를 따로 묻기" |
| part3:354 | `76종 표준담보 매핑` | 지금은 86개다 | `standard_coverage_in_use` |
| part3:355 | `결합제약 개별분리 (0.42 적발)` | 값은 맞다 | `bundled_constraint_check`의 `separated_probabilities` |
| part3:365, 366 | `1.00`, `0.00` | 축 끝이다 | f-string으로 찍는다 |
| part3:368-386 | 막대 24개의 분포(`n_bars`, `peak_idx`) | 실제 분포가 아닌 그림이다 | "예시 그림"으로 표시하거나 두 값만 보인다 |
| part3:389 | `정답 0.94↑ · 오답 0.06↓ 분리!` | 값은 맞다 | `symmetric_choice_probability`. "맞는 값, 뒤집은 값" |
| part3:390 | `일부러 틀리게 바꾼 437줄 가운데 확정 통과 0줄 (전량 차단 ✓)` | 값은 맞다 | `calibration_flipped_rows`와 그 note를 작은 글씨로 |
| part3:419, 449 | `최근 60초 토큰 창 제어`, `60초 토큰 창 제어 : 42K / 50K 안전 유지 ✓` | 42K와 "안전 유지"는 근거가 없다 | `decide_token_window`의 `window_seconds`, `decide_tokens_per_minute_guard`(기다리는 기준), `decide_per_minute_limit`의 `tokens`. 잰 사용량처럼 보이지 않게 그린다 |
| part3:430-438 | `확률 0.75 기준`, `확률 0.40 기준`, `0.75 이상 : 자동 확정`, `0.40~0.75 : 담당자 검토 이관`, `0.40 미만 : 보류 · 재추출`, `틀린 줄의 95.9% 포착 · 미반영` | 값은 맞다 | `verify_confirm_threshold`, `verify_reextract_threshold`, `calibration_reextract_band`의 `wrong_caught_pct` |
| part3:444 | `주간 시장동향 3유형 분류 & 토큰 제어` | 소식 분류는 일곱 가지다 | `market_news_categories`, `market_news_category_count`, 건수는 `market_news_by_category` |
| part3:453-455 | `◆ 배타적사용권 획득 · 신청`, `독점 판매 기간 · 만료 시점 추적`, `▲ 주력 담보 경쟁 심화`, `가입한도 상향 · 고지 요건 완화 포착`, `★ 미보유 신담보 출시`, `당사 미운영 보장 → 개정 검토 등록` | 분류 이름이 설정과 다르다. 만료 시점 추적과 개정 검토 등록은 없는 기능이다. "독점"은 화면 금지어다 | 분류 이름은 `market_news_categories`. 없는 기능은 지운다 |
| part3:465 | `검증·분류 완결 : 오확정 0건 정밀 분기 + 60초 토큰 창 자동 조절로 분당 5만 한도 안에서 무중단 운영 ✓` | "오확정 0건"과 "무중단 운영"은 근거가 없다 | `calibration_flipped_rows`(표본의 결과임을 적음)로 바꾸고 "무중단"은 지운다. 한도 초과 기록을 말하려면 `decide_quota_failures_logged`와 그 note를 함께 |

### 7장, 8장, 9장 (`part4`)

| 자리 | 지금 글 | 문제 | 고칠 방법 |
| --- | --- | --- | --- |
| part4:48, 49, 56, 58, 63, 103, 107, 142, 196, 616 | `용량 제약과 명칭 불일치를 넘은 방법`, `단일 파일 4MB 상한 안에서`, `저장 · 배포 제약`, `4MB 상한 제약`(채움 0.74), `현재 빌드 2.97MB / 4.0MB 통과 ✓`, `문제 ④ 사전 저장 시 4MB 초과 · 보험료 부재`, `>4MB ×`, `(2.97MB)`, `단독 파일 2.97MB(4MB 미만) 유지`, `(단독 HTML · 2.97MB)` | 4MB 기준은 2026-11-23에 없앴고 지금 운영 화면은 약 4.3MB다 | 파일 크기와 상한은 영상에 쓰지 않는다(`site_size_test_limit_mb`의 note). 문제 ④는 "특약별 보험료가 공시 문서에 없음"(`premium_example_rows`)만 남긴다. 7장 제목과 부제에서 용량을 뺀다 |
| part4:59 | `서버 예산`, `0원 (시트 13탭)`, 채움 0.12 | 값은 맞고 채움은 근거가 없다 | `operating_cost_won`, `sheet_tab_count`, 채움 없음 |
| part4:64 | `정적 파일 1개에 정본·화면 내장` | 정본은 구글 시트이고 HTML에는 사본 자료가 실린다 | "사본 자료를 실은 HTML 한 파일" |
| part4:76, 78 | `"315 간편"`, `"간편가입형(1년)"` | 이름이 박혀 있다 | 우체국 쪽은 `default_base_variant`의 `name`, 한화생명 쪽은 `peer_held_coverage[0].name` |
| part4:81, 83 | `수술 회당 지급`, `연간 1회 지급` | 예시다 | 숫자 없이 "연간 한 번" |
| part4:88, 89, 91 | `문제 ② 초기 52종 사전 → 1,951줄 미매핑`, `기존 사전 52종`, `한화 급부 388종류(1,951줄) 대기 적체` | 388종류의 짝은 재추출 전 2,172줄이고, 1,951줄은 재추출 뒤의 대기다. 매핑이 없던 것이 아니라 매핑 대기였다 | `dictionary_initial_size`, `hanwha_pending_before_rerun`의 `kinds`, `rows`. 재추출 뒤 수를 쓰려면 `hanwha_pending_after_rerun`. "미매핑"은 "매핑 대기" |
| part4:142, 152 | `비교·시사점은 화면에서 조건 선택 즉시 산출합니다`, `저장 없이 화면 즉시 산출` | 이 앱은 비교, 판정, 문장을 빌드할 때 코드가 계산해 자료 파일에 싣고 화면은 읽기만 한다(시안 4의 브리핑 값은 대표 조건으로 계산, `proto_src/console4/API.md` 10절) | "빌드할 때 계산해 자료에 싣고 화면은 고른 조건의 값을 읽음" |
| part4:163 | `◆ 표준담보 76종 및 포함·합산 관계` | 쓰는 담보는 86개이고 관계 이름은 포함과 통합이다 | `standard_coverage_in_use`, `coverage_relations_by_kind`의 열쇠 |
| part4:164, 464, 502 | `지급형태 · 치료 5단계 분류`, `치료 여정 5단계 보유 담보 막대`, `치료 여정 5단계별 우체국 보유 담보 수` | 숫자가 박혀 있다 | `len(fact("treatment_stages"))` |
| part4:175-179 | `19개 보험기관`, `23개 상품 종형`, `2,747개 특약`, `6,615건 세부 급부`, `주간 시장동향` | 23, 2,747, 6,615는 화면에 올린 세 회사의 값이라 맞지만 19는 시장 소식 기관 수다 | 화면 기준으로 맞춘다: `site_org_count`, `variant_count_site`, `rider_count_site`, `benefit_count_site`, `market_news_count`. 사본 전체를 말하려면 `product_org_count`, `variant_count_all`, `rider_count_all`, `benefit_count_all`로 바꾸고 그렇게 적는다 |
| part4:222, 282, 288, 289 | `검토 대기 672건은 점선으로 분리해 ... 52종에서 76종으로 넓혀 986건을 흡수했습니다`, `6,615건 급부 전량 1대1 매핑 연결 (누락 0건) · 매핑 확정 3,807건 실선 vs 검토 대기 672건 점선 분리`, `●─● 매핑 확정 급부 (실선 3,807건)`, `●- -● 검토 대기 급부 (점선 672건 · 미보유 오판 방지)` | 3,807과 672는 옛 사본의 값이다. 986은 근거가 없다. 사전은 52줄에서 77줄, 87줄로 늘었다 | `benefit_count_site`, `benefits_without_mapping`, `mapping_status_site`의 자동확정과 대기(대상외도 있다). 사전 경과는 `dictionary_initial_size`, `dictionary_first_expansion_added`, `dictionary_second_expansion`, 지금은 `standard_coverage_rows`, `standard_coverage_in_use`. 986은 지운다 |
| part4:226-279 | 관계망에서 다리 선 넷 가운데 하나를 점선(`bridge_counter % 4`) | 점선 비율이 대기 비율처럼 보이지만 실제 대기는 화면 기준 급부의 1%쯤이다 | 비율을 `mapping_status_site`로 맞추거나 "그림의 비율은 실제 비율이 아님"을 적는다 |
| part4:287 | `◆ 담보 포함·합산 관계 (31건)` | 지금 32줄이다 | `coverage_relation_count`, `coverage_relations_by_kind` |
| part4:310, 311, 425 | `직전 상품 (간편건강 2504)`, `현행 상품 (간편한건강 2606)`, `우체국 2606` | 번호가 박혀 있다 | `example_targeted_anticancer`의 `revisions[0].revision_no`(직전), `revisions[-1].revision_no`(현행) |
| part4:316 | `정밀비교 3개사 → 19개사 단계 확대` | 3은 우체국을 포함한 화면 회사 수이고 19는 우체국을 뺀 대상 수라 기준이 다르다 | "우체국과 상대 N곳"(N은 `site_org_count`에서 1을 뺀 값)에서 "우체국과 정밀 비교 대상 M곳"(M은 `comparison_target_counts`의 합)으로. 지금 사본에 든 회사는 `product_org_count` |
| part4:317 | `변경 약관만 재추출 · 기존 검수분 유지` | 약관이 아니다. 기존 확정 줄 지키기는 실제 재추출에서 확인 전이다 | "바뀐 문서만 다시 뽑음", `id_inherit_simulated_rows`의 note를 함께 |
| part4:321 | `확장 ② 표준담보 사전 확장 (52 → 76종)` | 위 222줄과 같다 | 위와 같다 |
| part4:322 | `18개 보험사 요약서 35종 조사로 신종 담보 보강` | 18과 35는 문서에서 확인되지 않는다 | `dictionary_expansion_survey_org_count`(보유 회사를 센 회사 수), `dictionary_addition_rule` |
| part4:325 | `1인실·응급실`, `뇌·심장 통합`, `전신마취·산정특례` | 사전의 담보 이름과 다르다. 어느 확장에서 더했는지는 facts.json에 없다 | `standard_coverage_names`에 있는 이름만 쓴다. "새로 더한 담보"라고 쓰려면 PR 글에 필요한 값으로 적는다 |
| part4:341 | `신규 표준담보 25종 신설 → 미분류 급부 986건 편입 ✓` | 25는 맞고 986은 근거가 없다 | `dictionary_first_expansion_added`. 986은 지운다 |
| part4:344-354 | `타사 신상품 · 배타적사용권 보도`, `신규 담보 후보`, `◆ 차기 표준담보 편입 후보`, `확장 ③ 시장동향 → 신규 담보 후보`, `다수 보험사 출시 확인 시 정식 표준담보 등록` | 시장 소식을 사전 후보로 잇는 기능은 없다(화면 1의 "표준담보에 이어진 소식"도 지금 0건). 사전에 담보를 더하는 기준은 요약서에서 센 보유 회사 수다 | 지우거나 "앞으로 할 일"로 표시한다. 더하는 기준은 `dictionary_addition_rule` |
| part4:374, 375, 439, 440 | `합산 탐색·관문 차트부터 응대 카드까지`, `포함·합산 관계로 실질 보장을 찾아냅니다`, `분리특약 합산 대응` | 관계 이름은 포함과 통합이다 | "포함, 통합 관계". 우체국이 뇌혈관질환 수술비와 심장질환 수술비를 따로 갖고 한화생명과 삼성화재가 뇌·심장질환 수술비를 갖는 예는 사본과 맞다 |
| part4:449 | `합산 관계 탐색 ✓ : 외견상 미보유 29종 중 25종이 분리·상위 특약으로 실질 보장 확인!` | 근거가 없다 | 지운다. 수가 필요하면 PR 글에 "관계로 덮이는 담보 수"를 필요한 값으로 적는다 |
| part4:468, 469 | `고객군별 간편심사 관문 분석 (연령 × 병력)`, `2~5년 경과 이력`, `고지 해당 없음`, `수술만 (입원 없음)`, `최근 입원 이력` | 지도의 행은 열두 줄(입원 여섯, 수술만 여섯)이고 칸은 24개다 | `segment_map_rows`, `segment_map_columns`, `segment_map_cell_count`. 줄여 그리려면 묶은 기준을 화면에 적는다 |
| part4:481-489 | `▲ 우체국 적격 (입원만)`, `간편심사 청약 가능`, `일반심사 대상`, `간편고지 제한 ×` | 화면의 칸 라벨과 다르고 가입 여부를 단정한다 | `segment_map_labels` |
| part4:492 | `15~19세`, `20~80세` | 값은 맞다 | `segment_map_columns` |
| part4:503, 510, 512, 514 | `cj_stages`의 7, 6, 4, 8, 0과 `"입원·간병"`, 막대 높이 `s_cnt / 8.0`, `f"{s_cnt}종"`, `0종` | 수가 박혀 있고 "입원·간병"은 자료의 "입원"과 다르다. 막대 최댓값 8도 박혀 있다. 담보 수의 단위는 "개"다 | `treatment_stages`와 `held_coverage_by_stage`. 막대 최댓값은 그 값들의 최댓값 |
| part4:521-523 | `● 주계약 4,000만`, `● 표적항암 2,000만`, `● 배타선택 차단` | 4,000만은 대표 조건의 주계약 한도와 맞다. 표적항암 2,000만은 기준 가입금액 1,000만 원에 대한 지급액이지 조합의 가입금액이 아니다 | `reference_main_contract_limit_manwon`. 표적항암 값은 지우거나 `example_targeted_anticancer`로 "기준 가입 N만 원에 지급 M만 원" |
| part4:525 | `특약 결합 제약 및 실수령액 산출` | "실수령액"은 이 앱의 말이 아니다 | "실제 지급액" |
| part4:561, 578, 589, 594, 602, 606, 607, 735, 737 | `4대 실무 전략`, `전략 ① [청약 타깃 발굴]` ~ `전략 ④ [상품 개정 검토]`, `4대`, `실무전략`, `약관 쪽수 · 4대 전략 ✓`, `근거 직결 4대 전략` | 화면의 영업 인사이트 분류는 다섯이다 | `sales_insight_categories`, 건수는 `sales_insight_by_category`, 응대 카드의 차례는 `card_category_order` |
| part4:574, 576, 578 | `타사 입원·수술 ×`, `우체국 입원만 ✓`, `수술 이력만 있는 20~80세 고객군 중점 안내` | 대표 조건의 지도에서 우리 간편만 열리는 칸은 0칸이다. 수술만 받은 20~80세 칸은 한화생명 간편가입형(0년)도 열려 "함께 열림"이다 | `segment_map_ours_only_open_cells`, `segment_map_gate_only_cells`. 대상 고객군을 말하려면 화면의 관문 차이 문장을 쓴다(필요하면 PR 글에 요청) |
| part4:589 | `뇌혈관·심장 입원일당 및 혈전용해 우선 제안`, `전략 ② [앞세울 강점 · 단독 6종]` | 대표 강점에 혈전용해는 없다. "단독 6종"은 근거가 없다. "우선 제안"은 권유다(화면은 "추천", "권하세요"를 쓰지 않는다) | `lead_strengths`, `sales_insight_by_category`의 "앞세울 강점" |
| part4:593, 594 | `1년 후 100%`, `분리특약 합산 · 감액 경과 안내 (단정 보류 분리)`, `전략 ③ [조건 열위 방어]` | 처음 여는 종형의 조건 열위 방어는 0건이다 | `sales_insight_by_category`의 "조건 열위 방어". 0이면 0으로 보이거나, 값이 있는 종형을 `briefing_by_base_variant`에서 골라 그 종형 이름을 적는다. 감액 뒤 지급은 숫자 없이 "전액" |
| part4:598, 600, 602 | `입원8`, `통원0`, `미운영 '통원일당' 신설 · 간편 15~19세 확대 건의` | 8과 0은 맞다. "건의"는 이 앱이 하지 않는 권유다 | `held_coverage_by_stage`. 건의 문구는 지우고 개정 검토 후보 수(`sales_insight_by_category`의 "개정 검토 후보")로 |
| part4:617 | `단정·과장 표현 빌드 차단 ✓ · 전 문장 약관·사업방법서 쪽수 직결` | "전 문장 ... 직결"은 과장이고 약관이 아니다 | "근거 문서와 쪽수를 함께 보임", 금지어는 `forbidden_words` |
| part4:618 | `자연어·조건 연동 : "50세 수술이력 뇌혈관 비교" → 화면 ②·③·④ 즉시 산출` | 말로 묻는 입력은 아직 없다(버전 1에 넣기로 한 기능, `docs/progress.md`) | 지우거나 "앞으로 할 일"로 |
| part4:622, 632, 692 | `대외 배포 금지 · A4 1매`, `본부 정밀 판단 → 현장 A4 1매 전달`, `A4 1매` | "1매"가 박힌 숫자다 | "A4 한 장" |
| part4:625 | `① 수술이력 간편심사 고지 차이`, `② 당사 단독 담보 · 대응 특약`, `③ 감액 경과 조건 · 근거 쪽수` | 카드의 차례가 자료와 다르다 | `card_category_order` |
| part4:653, 654, 658, 659 | `최종 업무 혁신 결과`, `수치와 시각 지표로 어떻게 달라졌는지`, `도입 전 업무 한계 (Before)`, `도입 후 업무 혁신 인포그래픽 (After)` | 실제 업무에 들인 적이 없고(개념검증), 시간 단축 같은 효과는 아직 재지 않았다 | "손으로 하던 방식", "이 앱으로". `not_yet_measured`를 작은 글씨로 함께 적는다 |
| part4:687, 688 | `19개사 · 운영비 0원`, `검증로그 13,671건` | 19의 뜻이 흐리고 13,671은 옛 값이다 | `market_news_institution_count`("기관"), `operating_cost_won`, `work_log_count_site` |
| part4:699 | `308p 그림 ×` | 값은 맞다 | `image_doc`의 `pages` |
| part4:714-716 | 도넛 셋(채움 1.0, 1.0, 0.86)과 `100%`, `308쪽 오차 0건`, `100%`, `오류 437건 차단`, `86%`, `미보유 29→25종 해명` | 308쪽 0건은 두 판독이 서로 같았다는 뜻이지 정답 대비 오차율이 아니다. 437은 일부러 틀리게 바꾼 줄이다. 86%와 29→25는 근거가 없다 | 도넛을 없앤다. `image_doc`의 `amount_mismatches`("두 판독의 지급률과 금액 어긋남 0곳"), `calibration_flipped_rows`("일부러 틀리게 바꾼 437줄 가운데 통과 0줄"). 셋째는 지운다 |
| part4:718 | `② 원문·코드 분리 + 교차판독 + decision-1 + 76종 합산 탐색` | 86개이고 관계 이름은 포함과 통합이다 | `standard_coverage_in_use`, "포함, 통합 관계" |
| part4:732 | `대기 672건·단정주의 분리` | 옛 값이다 | `mapping_status_site`의 대기, 단정하지 않은 비교는 `no_verdict_pairs` |
| part4:744 | `완성도 검증 완료 : 자동 시험 608개 통과 · 화면 오류·외부 요청 0건 · 2단계 보험료·질병코드 별표 확장 기반 완비 ✓` | 608은 옛 값이다. 보험료와 질병코드 탭은 비어 있어 "기반 완비"는 과장이다 | `test_count`(note대로 발표 전에 다시 센다), `site_browser_check_problems`, `premium_example_rows`, `benefit_disease_code_rows`. "탭은 만들었고 비어 있음(2단계 과제)" |

### 문서 (`README.md`, `storyboard.md`)

| 자리 | 지금 글 | 문제 | 고칠 방법 |
| --- | --- | --- | --- |
| storyboard.md 전체, README.md 서사 구성 | `13,671건`, `608개`, `2.97MB / 4.0MB`, `42K < 50K`, `26만 토큰`, `29→25종`, `52→76종`, `76종`, `7·6·4·8·0종`, `50세 · 남성 · 간편 2년형`, `Jev → gemini-decision-1` 따위 | 위 표의 문제가 문서에도 그대로 있다 | 문서에는 숫자를 적지 않고 facts.json의 열쇠 이름으로 가리키거나 지운다. Jev는 지운다 |

## 3. 그 밖

1. 통합본을 만드는 명령이 없습니다. `README.md`는 "4부 분할본 + 전체 통합본"이라 하고 `storyboard.md`는 통합 mp4의 파일 이름까지 적었지만, `postlife_demo.py`는 네 장면을 다시 내보낼 뿐이고 이어 붙이는 명령이 없습니다. 통합본이 필요하면 네 장면을 렌더링한 뒤 이어 붙이는 명령(예: FFmpeg의 concat)을 README에 적고, 만든 파일 이름이 storyboard의 이름과 같게 맞춥니다. 필요 없으면 두 문서에서 통합본을 지웁니다. `postlife_demo.py`의 설명 글은 `from __future__` 뒤에 있어 모듈 설명으로 읽히지 않으니 맨 위로 옮기고, 장면을 그대로 이어받기만 하는 클래스 넷은 import로 바꿔도 됩니다.
2. README의 실행 안내를 새 PC에서 그대로 따라 해 보고 고칩니다. 이 폴더 안에 따로 `.venv`를 만드는 방식이라 저장소 루트의 가상환경(`uv venv --python 3.12 .venv`)과 다르다는 것, 필요한 시스템 도구(FFmpeg, 한글 글꼴)와 그 확인 방법, 실제로 렌더링에 쓴 manim과 networkx의 버전(`requirements.txt`를 `>=` 대신 그 버전으로)을 적습니다. facts.json은 Claude 쪽에서 `python scripts/export_presentation_facts.py`로 만들고 영상 쪽에서는 고치지 않는다는 것도 한 줄 적습니다.
3. 화면 글의 한국어 규칙
   - 여러 항목을 나열할 때 가운뎃점(·)으로 잇지 않고 쉼표로 구분합니다. `상품·청약`처럼 앱 이름에 든 것과 `뇌·심장질환 수술비`처럼 자료의 이름에 든 것은 그대로 둡니다.
   - 엠대시(`—`)를 쓰지 않습니다. 열한 곳(part1:47, 189, 348, part2:47, 499, part3:46, 110, 268, part4:48, 374, 653)이 엠대시로 앞뒤 말을 이었습니다. 쌍점이나 줄바꿈으로 나눕니다.
   - 번역투와 조어를 쓰지 않습니다. 예: "직면했습니다"는 "부딪혔습니다", "넘은 방법"은 "푼 방법", "포착"은 "찾음", "규명", "해명", "완비", "무중단 운영"은 지우고 사실대로, "실수령액"은 "실제 지급액", "수동반입", "수동 분리"는 "사람이 내려받음", "선기재", "절단"(part2:432)은 "발표일을 먼저 적게 함", "코드가 날짜를 확인해 구간 밖을 버림".
   - 화면의 분석 문장에 쓰지 않는 말(`forbidden_words`, 예: "독점", "추천", "가입됩니다")을 영상의 영업 문장에도 쓰지 않습니다. "최고값"처럼 잰 값을 말하는 데 쓰는 것은 괜찮습니다.
   - 용어는 지금 화면과 같은 말을 씁니다(고객군 지도의 라벨, 영업 인사이트 분류, 치료 단계 이름). 화면 용어는 나중에 실무 용어로 한 번에 바꿀 예정이라, 영상에서 따로 새 말을 만들지 않습니다.
4. 죽은 코드와 쓰지 않는 import
   - common:149-155: `Arc(...).move_center_to_arc_center if False else Arc(...)`는 같은 호를 두 번 적은 죽은 식입니다. 하나만 남깁니다.
   - `print(f"[TIMING] ...")` 여덟 곳(part1:503, part2:502, 741, part3:271, 523, part4:386, 656, 776)을 지웁니다. 길이를 재야 하면 렌더링 기록에서 봅니다.
   - 쓰지 않는 import: part1의 `math`(3줄), `C_CYAN_DIM`, `C_WHITE`(7줄의 묶음), part2의 `C_WHITE`, `cross_mark`(7줄의 묶음), part3의 `C_CYAN_DIM`, `cross_mark`(7줄의 묶음), part4의 `C_CYAN_DIM`(8줄의 묶음).

## 4. 끝내는 기준

1. 화면 글에 박힌 숫자가 0개입니다. 저장소 루트에서 아래를 돌려 마지막 줄이 `숫자가 든 글: 0`이어야 합니다. f-string 자리(`{...}`)에 넣은 값, 색 값, 독스트링, `check_bounds`의 이름, "A4"는 세지 않습니다.

   ```bash
   python - <<'EOF'
   import ast, pathlib, re
   hits = 0
   for f in sorted(pathlib.Path("presentation_animation").glob("*.py")):
       tree = ast.parse(f.read_text(encoding="utf-8"))
       skip = set()
       for n in ast.walk(tree):
           if isinstance(n, ast.JoinedStr):
               skip |= {id(v) for v in ast.walk(n) if v is not n}
           body = getattr(n, "body", None)
           if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
               skip.add(id(body[0].value))
           if isinstance(n, ast.Call):
               name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
               if name == "check_bounds":
                   skip |= {id(a) for a in n.args}
       for n in ast.walk(tree):
           if id(n) in skip:
               continue
           if isinstance(n, ast.Constant) and isinstance(n.value, str):
               s = n.value
           elif isinstance(n, ast.JoinedStr):
               s = re.sub(r"\{[^{}]*\}", "", ast.unparse(n))
           else:
               continue
           if re.fullmatch(r"#[0-9A-Fa-f]{6}", s):
               continue
           if re.search(r"\d", s.replace("A4", "")):
               hits += 1
               print(f"{f}:{n.lineno}: {s!r}")
   print("숫자가 든 글:", hits)
   EOF
   ```

   지금 PR 7번의 코드에서는 219개가 나옵니다.
2. 위 검사가 보지 못하는 정수와 비율 자리(표에 적은 `capacity_ring`의 채움, part2의 `range(27)`, `k >= 23`, `range(16)`, 막대 높이, part3의 막대 분포와 확률 막대, part4의 `cj_stages`, `s_cnt / 8.0`, 도넛 채움, 관계망의 점선 비율)를 표대로 고쳤는지 PR 글에 줄마다 적습니다.
3. facts.json과 만드는 쪽 파일을 고치지 않았습니다. `git diff origin/main --stat -- presentation_animation/facts.json scripts/export_presentation_facts.py tests/test_presentation_facts.py`가 비어 있어야 합니다. `python scripts/export_presentation_facts.py --check`가 `같음`을 찍어야 합니다.
4. 네 장면이 렌더링됩니다. `presentation_animation` 폴더에서 `manim -ql postlife_demo.py Part1ServiceScene Part2CollectExtractScene Part3DecisionScene Part4OntologyImpactScene`이 오류 없이 끝나고, `[BOUNDS WARNING]` 줄이 없어야 합니다. 장면마다 길이와 대표 장면 사진 한 장씩을 PR에 붙입니다.
5. PR 글에 넣을 것: 위 표의 줄마다 고친 방법(지운 것과 바꿔 쓴 것을 나눠서), "필요한 값"과 "필요한 사실"의 목록, 3절에서 고친 것.
