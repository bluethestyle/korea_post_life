"""발표 영상(presentation_animation)이 화면에 띄우는 숫자와 사실을 한 파일로 만든다.

쓰기: python scripts/export_presentation_facts.py            # presentation_animation/facts.json 을 다시 쓴다
      python scripts/export_presentation_facts.py --check    # 다시 만든 것과 커밋된 파일이 다르면 1로 끝난다

영상 코드는 숫자를 글자로 박지 않고 이 파일에서 읽는다(docs/gemini_requests/29_발표영상_사실자료와_고칠곳_Antigravity.md).
파일은 손으로 고치지 않는다. 사본이나 문서가 바뀌면 이 스크립트를 다시 돌린다.

값의 출처는 넷이다(항목마다 source.kind 에 적는다).
- snapshot, config, schema, seed, code: 사본(data/snapshot), 설정(src/postlife/config.py), 시트 정의(src/postlife/schema.py),
  시드(data/seed), 화면 코드의 상수에서 이 스크립트가 센다. as_of 는 사본 기준일이다.
- screen_data: 시안 4의 화면 자료(proto_src/console4/sales.json, 담보 비교 자료 cover.json)에 이미 계산돼 있는 값을 그대로
  옮긴다. 다시 계산하지 않는다. 화면 자료의 자료 시각이 사본과 다르면 멈춘다(scripts/export_app_data.py 를 먼저 돌린다).
- document: 사본에서 셀 수 없고 문서에만 있는 값. 아래 DOC_FACTS 표에 손으로 적었고, 값마다 문서 경로, 절 제목, 근거 문구를 둔다.
  근거 문구가 그 절에 글자 그대로 없으면 멈춘다(문서가 바뀌었으니 값을 다시 확인하라는 뜻). as_of 는 그 문서나 절의 기준일이다.
- manual: 실행해서 얻지 않고 적어 둔 값(전체 시험 수). note 에 다시 세는 방법을 적는다.

같은 사본, 같은 문서에서는 바이트까지 같은 파일이 나온다(시각이나 실행 환경을 싣지 않는다).
사본과 화면 자료는 읽기만 한다. 모델 호출, 시트 쓰기는 하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from postlife import config, schema  # noqa: E402
from postlife.site import orgs as site_orgs  # noqa: E402
from postlife.site.sales import FORBIDDEN  # noqa: E402
from postlife.snapshot import read_snapshot  # noqa: E402
from postlife.validate import NO_AMOUNT_BASES  # noqa: E402

OUT = Path("presentation_animation") / "facts.json"
SNAPSHOT = Path("data") / "snapshot"
SALES = Path("proto_src") / "console4" / "sales.json"
COVER = Path("proto_src") / "console4" / "cover.json"
RELATIONS = Path("data") / "seed" / "표준담보_관계.jsonl"

FORMAT = 1
ABOUT = ("발표 영상(presentation_animation)이 화면에 띄우는 숫자와 사실입니다. scripts/export_presentation_facts.py 가 만들고, "
         "손으로 고치지 않습니다. 영상 코드는 숫자를 글자로 박지 않고 facts 의 value 를 읽습니다.")
AS_OF_RULE = ("사본, 설정, 시드, 화면 자료에서 센 값의 as_of 는 사본 기준일이고, 문서에서 옮긴 값의 as_of 는 그 문서나 절이 밝힌 "
              "기준일입니다. 사이트 범위(_site)는 화면에 올린 회사(config.SITE_ORGS)만 센 값입니다.")

# 기관 순서: 우체국을 맨 앞에 두고 config 의 생명보험, 손해보험 차례
ORG_ORDER = ("EPOST", *config.LIFE, *config.NONLIFE)
# 지급기준구분: 비면 금액. 금액과 가입금액비율은 금액 하나로 담기는 급부, 나머지 넷은 담기지 않는 급부(validate.NO_AMOUNT_BASES)
BASIS_ORDER = ("금액", "가입금액비율", *NO_AMOUNT_BASES)
STATE_ORDER = ("자동확정", "승인", "수정", "대상외", "대기", "오류")
STAGE_ORDER = ("추출", "코드대조", "판정", "재추출", "사람검토이관")
RESULT_ORDER = ("통과", "보류", "반려")
WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")

# 개정 전후 예시로 쓰는 특약계보키(우체국 표적항암약물허가치료특약. docs/submission.md 9절의 시연 순서와 같은 특약).
# 시트의 ID 는 바꾸지 않으므로(CLAUDE.md) 계보키를 그대로 적는다.
EXAMPLE_LINEAGE = "afe7dff94ada"

# 검증 구간과 법정 한도(hum_기준값의 기준키 → 열쇠, 이름)
THRESHOLDS = (
    ("추출검증_통과", "verify_confirm_threshold", "추출값 검증: 이 확률 이상이면 자동 확정"),
    ("추출검증_재추출", "verify_reextract_threshold", "추출값 검증: 이 확률 미만이면 다른 모델로 다시 뽑음(사이는 사람 검토)"),
    ("담보매핑_자동확정", "mapping_auto_confirm_threshold", "담보 매핑: 이 확률 이상이면 자동 확정"),
    ("담보매핑_대상외", "mapping_out_of_scope_threshold", "담보 매핑: 해당 없음 확률이 이 값 이상이면 대상외"),
    ("기사선별_통과", "news_pass_threshold", "시장 소식 선별: 이 확률 이상이면 기록"),
    ("기사선별_보류", "news_hold_threshold", "시장 소식 선별: 이 확률 미만이면 버림(사이는 사람 검토)"),
    ("중복판정_동일", "news_duplicate_threshold", "중복 소식: 이 확률 이상이면 같은 사건으로 합침"),
    ("LIMIT_POST_CONTRACT", "post_contract_limit_manwon", "우체국보험 계약보험금 한도(만 원)"),
)


# ---------------------------------------------------------------------------
# 문서에서 옮긴 값. (열쇠, 값, 이름, 기준일, 문서, 절 제목, 근거 문구들, 메모)
# 근거 문구는 그 절에 글자 그대로 있어야 한다. 문서 원문(공시 문서)이 아니라 이 저장소의 문서에서 옮긴 문구다.
# ---------------------------------------------------------------------------
SUB, LIM, PRO, HAN, PLA = "docs/submission.md", "docs/limitations.md", "docs/progress.md", "docs/handoff.md", "docs/planning.md"
SUB_SCOPE_DATE, LIM_DATE = "2026-11-23", "2026-11-20"
PRO_EXPAND = "비교 대상 확대: 회사별 상품공시 접속 모듈 (2026-11-19, Claude Code)"
PRO_MAPPING = "매핑 실행, 매핑 결과 검토와 규칙 손질 (2026-11-20, Claude Code)"
PRO_MERITZ = "메리츠화재 시범: 급부 두 판독 869줄, 카본 검토 반영, 화면용 자료 값 2차 (2026-11-23 15시 10분)"

LIFE_TARGETS = ["한화생명", "삼성생명", "교보생명", "신한라이프", "NH농협생명", "동양생명", "KB라이프생명", "미래에셋생명",
                "메트라이프생명", "흥국생명"]
NONLIFE_TARGETS = ["삼성화재", "DB손해보험", "현대해상", "KB손해보험", "메리츠화재", "한화손해보험", "롯데손해보험",
                   "NH농협손해보험", "흥국화재"]
BATCH_ORGS = ["삼성생명", "교보생명", "신한라이프", "NH농협생명", "동양생명", "KB라이프생명", "미래에셋생명", "메트라이프생명",
              "흥국생명", "현대해상", "KB손해보험", "메리츠화재", "한화손해보험", "롯데손해보험", "NH농협손해보험", "흥국화재"]

DOC_FACTS: list[tuple[str, Any, str, str, str, str, tuple[str, ...], str | None]] = [
    # 범위와 사람
    ("team_size", 1, "만든 사람 수", SUB_SCOPE_DATE, SUB, "1. 소개", ("개념검증 단계로 1인이 만들었습니다",), None),
    ("site_screen_count", 6, "운영 화면의 화면 수", SUB_SCOPE_DATE, SUB, "분석 화면의 탭 6개",
     ("기획이 정한 판단 10개 가운데 1단계 판단 6개를 다룹니다",), None),
    ("comparison_target_counts", {"생명보험": 10, "손해보험": 9}, "정밀 비교 대상으로 정한 회사 수(우체국 제외)", "2026-11-19",
     PLA, "2.1 정밀 비교 대상", ("정밀 비교 대상 회사는 생명보험 10곳과 손해보험 9곳입니다",),
     "총자산 기준으로 골랐고 출처가 기사라 순위는 공식 통계로 확정하지 못했습니다(같은 절)."),
    ("comparison_target_names", {"생명보험": LIFE_TARGETS, "손해보험": NONLIFE_TARGETS}, "정밀 비교 대상 회사 이름", "2026-11-19",
     PLA, "2.1 정밀 비교 대상",
     ("| 한화생명 |", "삼성생명, 교보생명, 신한라이프, NH농협생명, 동양생명, KB라이프생명, 미래에셋생명, 메트라이프생명, 흥국생명",
      "| 삼성화재 |", "DB손해보험, 현대해상, KB손해보험, 메리츠화재, 한화손해보험, 롯데손해보험, NH농협손해보험, 흥국화재"), None),
    # 공시 접속 모듈을 한꺼번에 만든 일
    ("disclosure_pilot_org", "DB손해보험", "공시 접속 모듈을 시범으로 먼저 만든 회사", "2026-11-19", SUB, "Claude Code와 서브에이전트",
     ("DB손해보험 하나로 공시 접속 모듈을 먼저 만들어 검수한 뒤, 나머지 16개 회사를 워크플로로 한꺼번에 실행했습니다",), None),
    ("disclosure_batch_orgs", BATCH_ORGS, "시범 뒤 워크플로로 한꺼번에 돌린 회사", "2026-11-19", PRO, PRO_EXPAND,
     ("나머지 16개 회사를 워크플로로 한꺼번에 돌렸습니다", *(f"| {n} |" for n in BATCH_ORGS)),
     "한화생명, 삼성화재(먼저 만든 회사)와 DB손해보험(시범)은 이 목록에 없습니다."),
    ("disclosure_batch_org_count", 16, "시범 뒤 워크플로로 한꺼번에 돌린 회사 수", "2026-11-19", SUB, "Claude Code와 서브에이전트",
     ("나머지 16개 회사를 워크플로로 한꺼번에 실행했습니다",), None),
    ("disclosure_batch_auto_org_count", 15, "그 가운데 로그인이나 토큰 없이 문서를 받은 회사 수", "2026-11-19", SUB,
     "Claude Code와 서브에이전트", ("16개 회사 가운데 15곳은 로그인이나 토큰 없이 문서를 받았습니다",),
     "남은 한 곳(한화손해보험)은 자동 접속 차단에 걸려 사람이 내려받습니다."),
    ("disclosure_batch_pdf_count", 58, "그때 받은 문서 수(모두 PDF, 쪽수 직접 확인)", "2026-11-19", SUB, "Claude Code와 서브에이전트",
     ("받은 문서 58개가 모두 PDF이고 쪽수가 보고와 같은지를 직접 확인했습니다",), None),
    ("disclosure_batch_test_count", 579, "그때(2026-11-19) 전체 시험 통과 수", "2026-11-19", SUB, "Claude Code와 서브에이전트",
     ("전체 테스트(579개 통과)",), "지금의 전체 시험 수는 test_count 입니다."),
    ("hanwhafire_block_status", 400, "한화손해보험 상품 목록 요청이 돌려받은 상태 번호(자동 접속 차단)", LIM_DATE, LIM,
     "2. 비교 대상과 범위", ("상품 목록 요청이 자동 접속 차단에 걸려 상태 400이 돌아옵니다",), "차단을 우회하지 않기로 했습니다."),
    ("unpinned_agent_incident", "모델을 지정하지 않은 구현 에이전트 하나가 최상위 모델로 돌았음", "서브에이전트 모델 지정 기준을 세운 계기",
     SUB_SCOPE_DATE, SUB, "Claude Code와 서브에이전트", ("처음 실행한 구현 에이전트 하나는 모델을 지정하지 않았습니다",),
     "한도를 얼마나 썼는지는 문서에 없습니다."),
    # 호출 한도
    ("daily_limit_search", 20, "시장 소식 검색 모델의 하루 한도(회)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("| 시장 소식 검색 | gemini-2.5-flash-lite | 20회 |",), None),
    ("daily_limit_extract", 500, "추출 모델의 하루 한도(회)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("| 추출, 소식 정형화 | gemini-3.5-flash-lite | 500회 |",), None),
    ("daily_limit_extract_alt", 500, "1차 재추출 모델의 하루 한도(회)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("| 1차 재추출 | gemini-3.1-flash-lite | 500회 |",), None),
    ("daily_limit_upper", 20, "마지막 재추출(상위) 모델의 하루 한도(회)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("| 마지막 재추출 | gemini-3.8-flash | 20회 |",), None),
    ("daily_limit_decide", 10000, "확률 산정 모델의 하루 한도(회)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("| 확률 산정 | gemini-decision-1 | 10,000회 |",), None),
    ("decide_per_minute_limit", {"calls": 200, "tokens": 50000}, "확률 산정 모델의 분당 한도(호출 수, 입력 토큰 수)", "2026-11-18", PLA,
     "6.1 작업별 배정", ("| 담보 매핑 분기, 기사 선별, 추출값 정합성 채점 | gemini-decision-1 | 10,000회 | 200회, 5만 토큰 |",),
     "AI Studio 한도 화면에서 읽은 무료 티어 값입니다(같은 절)."),
    ("actions_free_minutes_per_month", 2000, "GitHub Actions 무료 계정에 든 한 달 실행 시간(분)", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("GitHub Actions(무료 계정 월 2,000분 포함)",), None),
    ("operating_cost_won", 0, "운영 비용(원). 무료 도구만으로 짠 설계 기준", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("운영 비용이 들지 않게 짰습니다",), "무료 한도는 AI Studio 화면에서 읽은 값입니다(같은 문단)."),
    ("news_api_storage_limit_days", 21, "네이버 검색 API 약관의 서버 보관 상한(일). 그래서 쓰지 않음", "2026-11-18", PLA,
     "4.2 시장 동향 수집 경로", ("네이버 검색 API는 쓰지 않습니다. 개정 약관이 검색 결과를 AI 답변 생성에 쓰는 것과 21일을 넘는 서버 보관을 제한합니다.",),
     None),
    # 수집
    ("search_candidates_rejected", {"models": 2, "error_status": 503, "error_tries": 4, "sources_found": 0},
     "직접 불러 보고 뺀 검색 후보 모델(Gemma 4): 모델 수, 한 모델이 돌려준 오류 번호와 시도 수, 다른 모델이 찾은 출처 수", SUB_SCOPE_DATE, SUB,
     "작업별 모델 배정",
     ("검색 후보였던 Gemma 4 두 모델은 직접 불러 보고 뺐습니다", "하나는 네 번 모두 503 오류였고, 다른 하나는 검색을 하지 않았습니다(출처 0건)"),
     None),
    ("first_collect_news", {"structured": 27, "out_of_window": 23}, "첫 실제 수집: 정형화된 소식 수와 그 가운데 수집 구간 밖이라 코드가 버린 수",
     "2026-11-18", SUB, "6. 안전장치가 실제로 걸러 낸 사례", ("정형화된 소식 27건 가운데 수집 구간 밖 23건을 코드의 날짜 확인이 버렸습니다",),
     None),
    # 추출
    ("hanwha_summary_pages", 567, "한화생명 한 상품의 요약서 쪽수", LIM_DATE, LIM, "2. 비교 대상과 범위",
     ("한화생명 한 상품의 요약서가 567쪽이고, 첫 급부 추출 한 번에 76분과 추출 호출 341회가 들었습니다",), None),
    ("hanwha_first_extract", {"calls": 341, "minutes": 76}, "한화생명 첫 급부 추출 한 번에 든 추출 호출 수와 시간(분)", LIM_DATE, LIM,
     "2. 비교 대상과 범위", ("한화생명 한 상품의 요약서가 567쪽이고, 첫 급부 추출 한 번에 76분과 추출 호출 341회가 들었습니다",), None),
    ("text_switch_confirmed_rows", {"total": 49, "before": 22, "after": 39},
     "금액을 원문 글자로 받게 바꾼 뒤 2606 요약서의 확정 줄 수(전체, 바꾸기 전, 바꾼 뒤)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("2606 요약서 49행 가운데 확정 행이 22행에서 39행으로 늘었습니다",), None),
    ("targeted_anticancer_misread", {"misread_pay_manwon": 1000, "misread_reduced_manwon": 1000, "correct_pay_manwon": 2000,
                                     "correct_reduced_manwon": 1000},
     "표적항암약물허가치료특약: 가벼운 모델 둘이 잘못 적은 값과, 코드 대조가 잡아 상위 모델로 바로잡은 값(만 원)", SUB_SCOPE_DATE, SUB,
     "6. 안전장치가 실제로 걸러 낸 사례",
     ("가벼운 모델 둘 다 1,000만 원을 지급액과 감액 양쪽에 적었습니다", "2,000만 원(1년 미만 1,000만 원)으로 바로잡혔습니다"),
     "감액 1,000만 원은 1년 미만 지급액입니다."),
    ("rider_limit_rows_protected", 166, "급부만 다시 뽑을 때 비워질 뻔한 우체국 특약 한도 줄 수(가짜 시트에서 0줄이 됨)", SUB_SCOPE_DATE, SUB,
     "6. 안전장치가 실제로 걸러 낸 사례", ("가짜 시트에서 실행하면 우체국 특약 한도 166행이 0행이 됐습니다",
                                    "실제 우체국 급부 재추출에서 166줄이 그대로인 것을 확인했습니다"), None),
    ("id_inherit_simulated_rows", 1039, "지난 한화 자료로 시험해 이어받은 급부ID 줄 수", LIM_DATE, LIM, "3. 추출과 검증",
     ("어제 한화 자료에 적용해 보면 1,039줄을 잇고",), "지난 자료로 시험한 값입니다. 실제 재추출에서 통하는지는 아직 확인하지 않았습니다."),
    ("code_review_items", 26, "제미나이가 짚은 추출, 검증 코드 검토 건수(모두 재현됨)", SUB_SCOPE_DATE, SUB, "6. 안전장치가 실제로 걸러 낸 사례",
     ("제미나이의 추출, 검증 코드 검토 26건을 서브에이전트가 지적마다 재현, 수정, 시험했고, 재현되지 않은 지적은 없었습니다",), None),
    ("samsungfire_crosscheck_rows", 681, "삼성화재 급부 표를 규칙 추출과 제미나이 독립 구조화로 줄마다 대조한 줄 수", "2026-11-19", HAN,
     "6. 제미나이와 나눠 한 방식", ("파이프라인과 따로 같은 표를 구조화하게 하고 줄마다 대조(삼성화재 681줄, 오류 0)",),
     "THE FIT 8종 339줄과 새로고침 7종 342줄입니다. 지금 사본의 삼성화재 급부는 benefits_by_org 에 있습니다."),
    # 그림으로 된 문서
    ("image_doc", {"pages": 308, "chars": 314492, "amount_mismatches": 0},
     "미래에셋생명 요약서 두 개(글자가 그림): 쪽수, 확정한 글자 수(공백 뺌), 두 판독의 지급률과 금액이 어긋난 곳", SUB_SCOPE_DATE, SUB,
     "글자가 그림으로 든 문서: 두 모델이 따로 읽고 교차 검증하기",
     ("두 요약서 308쪽(공백을 뺀 314,492자)을 확정했습니다", "지급률과 금액은 두 추출 결과가 한 군데도 어긋나지 않았습니다"),
     "정답과 견준 오차율이 아니라 서로 다른 두 판독이 같았다는 뜻입니다. 어긋난 글자는 Claude가 원본을 확대해 보고 확인했습니다."),
    ("image_doc_same_reader_repeat", {"pages": 20, "wrong_same_way": 9}, "같은 판독기를 새로 띄워 다시 읽혔을 때 첫 판독과 같은 식으로 틀린 쪽 수",
     SUB_SCOPE_DATE, SUB, "글자가 그림으로 든 문서: 두 모델이 따로 읽고 교차 검증하기", ("20쪽 가운데 9쪽에서 첫 추출과 같은 식으로 틀렸습니다",), None),
    ("image_doc_opus_reread_chars", 25048, "sonnet 이 틀렸던 20쪽을 opus 가 다시 읽어 확정본과 한 글자도 다르지 않았던 글자 수",
     SUB_SCOPE_DATE, SUB, "글자가 그림으로 든 문서: 두 모델이 따로 읽고 교차 검증하기", ("25,048자가 확정본과 한 글자도 다르지 않았고",),
     "공백과 따옴표 종류는 빼고 견줬습니다."),
    ("local_ocr_test", {"chars": 1123, "missed": 100, "wrong": 110}, "로컬 OCR(tesseract)을 글자가 풀리는 대조용 쪽에서 견준 결과(글자 수)",
     SUB_SCOPE_DATE, SUB, "글자가 그림으로 든 문서: 두 모델이 따로 읽고 교차 검증하기", ("1,123자 가운데 100자를 빠뜨리고 110자를 잘못 넣어",),
     "미래에셋 쪽이 아니라 글자를 풀 수 있는 대조용 쪽에서 잰 값입니다. 그래서 값에는 쓰지 않고 급부 표가 있는 쪽을 찾는 데만 씁니다."),
    # 확률 산정 모델
    ("decision_model_release_date", "2026-11-11", "gemini-decision-1 이 나온 날", SUB_SCOPE_DATE, SUB, "확률 산정 전용 모델을 검증기로",
     ("2026-11-11에 나온 확률 산정 전용 모델입니다",), None),
    ("decision_model_spec", {"choices_min": 2, "choices_max": 255, "items_per_call": 1000, "output_tokens": 0},
     "확률 산정 모델의 사양: 선택지 수 범위, 한 번에 받는 문항 수, 출력 토큰", SUB_SCOPE_DATE, SUB, "확률 산정 전용 모델을 검증기로",
     ("정해진 선택지(2~255개)에 확률만 매기며, 출력 토큰이 0이고 한 번에 1,000문항까지 받습니다",), None),
    ("decision_model_uses", ["추출값 정합성 검증", "표준담보 매핑", "시장 소식 선별", "중복 소식 병합"], "이 앱이 확률 산정 모델을 쓴 일",
     SUB_SCOPE_DATE, SUB, "확률 산정 전용 모델을 검증기로",
     ("이 모델을 추출값 정합성 검증, 표준담보 매핑, 시장 소식 선별, 중복 소식 병합에 넣었습니다",),
     "기존 상품의 초기 적재는 확률 산정 모델 없이 두 판독의 교차 확인으로 합니다(docs/planning.md 6.1)."),
    ("decide_token_window", {"window_seconds": 60, "margin_pct": 10},
     "확률 산정 호출 전에 최근 몇 초 동안 보낸 토큰을 세는지와, 한도에 두는 여유(%)", LIM_DATE, LIM, "3. 추출과 검증",
     ("최근 60초 동안 보낸 토큰을 본문 글자 수로 추정해 세고 한도(여유 10%) 아래에서 기다리게 고쳤고",),
     "기다리는 규칙이고, 고친 뒤 잰 사용량은 문서에 없습니다."),
    ("true_false_probability_range", {"low": 0.5, "high": 0.8}, "면책 조건을 참 거짓으로 물었을 때 맞는 줄이 머문 확률 범위",
     SUB_SCOPE_DATE, SUB, "확률 산정 전용 모델을 검증기로", ("맞는 행도 0.5~0.8에 머물렀습니다",), None),
    ("symmetric_choice_probability", {"correct_min": 0.94, "flipped_max": 0.06},
     "\"조건 있음 / 없음\" 가운데 고르게 바꾼 뒤 맞는 값과 뒤집은 값의 확률", SUB_SCOPE_DATE, SUB, "확률 산정 전용 모델을 검증기로",
     ("맞는 값은 0.94 이상, 뒤집은 값은 0.06 이하로 갈렸습니다",), None),
    ("calibration_flipped_rows", {"rows": 437, "passed": 0}, "경계값 보정: 일부러 틀리게 바꾼 줄 수와 그 가운데 확정을 통과한 줄 수",
     SUB_SCOPE_DATE, SUB, "7. 성과 지표", ("일부러 틀리게 바꾼 437행 가운데 통과 0행",),
     "우체국 요약서 2건으로만 맞춘 좁은 표본입니다(docs/limitations.md 3절)."),
    ("calibration_reextract_band", {"wrong_caught_pct": 95.9, "correct_rows": 101, "correct_rows_caught": 0},
     "재추출 경계 아래로 떨어진 비율: 틀린 줄 가운데 비율(%), 맞는 줄 수와 그 가운데 떨어진 줄 수", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("틀린 행의 95.9%, 맞는 101행 가운데 0행",), "우체국 요약서 2건으로만 맞춘 좁은 표본입니다(docs/limitations.md 3절)."),
    ("bundled_constraint_check", {"wrong_riders": 2, "bundled_probability": 0.8, "separated_probabilities": [0.42, 0.47]},
     "결합 제약을 묶어 물었을 때 통과한 잘못 끼어든 특약 수와 확률, 따로 물었을 때의 확률", SUB_SCOPE_DATE, SUB,
     "6. 안전장치가 실제로 걸러 낸 사례", ("잘못 끼어든 특약 2개가 0.80으로 통과했습니다. 특약마다 따로 묻자 0.42와 0.47로 걸렸습니다.",), None),
    ("decide_tokens_per_minute_peak_k", 79.98, "확률 산정 모델 분당 입력 토큰 최고값(천 토큰). 한도는 5만", "2026-11-19", LIM, "3. 추출과 검증",
     ("분당 토큰 최고값이 79.98K(한도 5만)였습니다",), "2026-11-19 사용량 화면의 값입니다."),
    ("decide_quota_failures_logged", 0, "재추출 두 번의 확률 산정 기록에 남은 분당 한도 초과 실패 수", LIM_DATE, LIM, "3. 추출과 검증",
     ("한도 초과로 실패한 기록은 한 건도 없습니다", "다시 시도해 성공한 호출은 기록에 남지 않아"),
     "다시 시도해 성공한 호출은 기록에 남지 않아, 한도를 넘겼다가 다시 시도로 넘어간 것인지는 알 수 없습니다. "
     "\"한도 초과 0건\"이나 \"무중단\"으로 쓰지 않습니다."),
    ("mapping_requery", {"rows": 2212, "estimated_minutes": 203, "waiting_minutes": 49},
     "한화 매핑 대기 줄을 다시 묻는 실행: 줄 수, 어림한 시간(분), 그 가운데 분당 토큰 창 때문에 기다린 시간(분)", "2026-11-20", PRO,
     PRO_MAPPING, ("대기 2,212줄(예전 대기 1,973과 첫 실행의 대기 239)", "약 203분으로 어림됩니다(분당 토큰 창 때문에 기다리는 49분 포함)",
                   "11:22 시작", "결과(14:46 종료)"), "어림한 값이고, 실제로는 11:22에 시작해 14:46에 끝났습니다."),
    # 사전과 매핑의 경과
    ("dictionary_initial_size", 52, "처음 표준담보 사전의 담보 수(우체국 상품 기준)", LIM_DATE, LIM, "2. 비교 대상과 범위",
     ("지금 시트의 사전 52개는 우체국 상품 기준으로 짠 것입니다",), None),
    ("dictionary_first_expansion_added", 25, "첫 사전 확장(2026-11-20)에서 더한 줄 수", "2026-11-20", PRO, PRO_MAPPING,
     ("표준담보 사전 탭에 25행을 더하고 심혈관질환 진단비를 쓰지 않음으로 바꿨습니다",), "52에서 77줄이 됐고, 한 줄은 쓰지 않음으로 바꿨습니다."),
    ("dictionary_second_expansion", {"before": 77, "after": 87}, "둘째 사전 확장(2026-11-23) 전후의 사전 줄 수", "2026-11-23", PRO,
     PRO_MERITZ, ("표준담보 사전에 열 줄을 더함(77 → 87",), "지금 사전 줄 수는 standard_coverage_rows 입니다."),
    ("dictionary_addition_rule", {"min_holder_orgs": 3, "or_epost_holds": True},
     "둘째 사전 확장에서 담보를 더한 기준: 우체국이 가졌거나, 요약서에서 이 수 이상의 회사가 가진 담보(기존 담보와 같지 않을 때)", "2026-11-23",
     PRO, PRO_MERITZ, ("기준(우체국이 가졌거나 세 곳 이상이 가짐, 기존 담보와 같지 않음)",), None),
    ("dictionary_expansion_survey_org_count", 19, "둘째 사전 확장에서 보유 회사를 센 회사 수(요약서의 급부 이름으로 셈)", "2026-11-23", PRO,
     PRO_MERITZ, ("보유 회사는 19개 회사 요약서의 급부 이름으로 셌고 약관과는 대조하지 않았습니다",), "약관과는 대조하지 않았습니다."),
    ("hanwha_pending_before_rerun", {"rows": 2172, "kinds": 388}, "재추출 전 한화 매핑 대기: 줄 수와 특약 기본 이름으로 묶은 종류 수",
     LIM_DATE, LIM, "2. 비교 대상과 범위", ("재추출 전(3,416줄)에는 대기가 2,172줄이었고, 특약 기본 이름으로 묶으면 388종류였으며",),
     "388종류의 짝은 2,172줄입니다(1,951줄은 재추출 뒤의 대기 줄 수)."),
    ("hanwha_pending_after_rerun", 1951, "재추출 뒤 한화 매핑 대기 줄 수(사전 확장 전)", LIM_DATE, LIM, "2. 비교 대상과 범위",
     ("3,067줄에서 대기가 1,951줄입니다",), "지금 매핑 상태는 mapping_status_by_org 입니다."),
    # 정답셋과 점검
    ("epost_summary_rows_matched", {"matched": 101, "total": 101}, "우체국 요약서 2건의 급부를 원문 표와 한 줄씩 대조한 결과", SUB_SCOPE_DATE,
     SUB, "7. 성과 지표", ("101행 모두 일치 (2606 49행, 통합 2504 52행)",), None),
    ("goldset_epost_benefit", {"items": 30, "auto_match": 28, "manual_match": 2}, "우체국 정답셋(보장금액, 면책, 감액) 정답 대조", SUB_SCOPE_DATE,
     SUB, "7. 성과 지표", ("30항목 중 28항목 자동 일치, 2항목 직접 확인으로 일치",), None),
    ("goldset_hanwha_benefit", {"items": 14, "match": 14}, "한화생명 정답셋(보장금액, 면책, 감액) 정답 대조", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("| 한화생명 정답셋 보장금액, 면책, 감액 | 14항목 모두 일치",), None),
    ("site_browser_check_problems", 0, "운영 화면 380px, 1280px 브라우저 점검에서 나온 넘침, 잘림, 겹침, 콘솔 오류, 외부 요청 수", SUB_SCOPE_DATE,
     SUB, "7. 성과 지표", ("380px와 1280px 폭의 브라우저 점검에서 오버플로, 잘림, 겹침, 콘솔 오류, 외부 요청이 모두 0건입니다",), None),
    ("not_yet_measured", ["정답셋 기준으로 검증과 재추출을 거치기 전후의 정확도 차이", "문서에 없는 값을 묻는 항목에서 빈값으로 답한 비율",
                          "신상품 비교표를 만드는 시간이 얼마나 줄었는지"],
     "아직 재지 못한 성과(영상에서 효과를 수치로 말하지 않는 것)", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("정답셋 100항목 기준으로 한 번 추출했을 때와 검증, 재추출을 거쳤을 때의 정확도 차이", "문서에 없는 값을 묻는 항목 전체에서 빈값으로 답한 비율",
      "신상품 비교표 작성 시간의 단축 폭(현업의 기존 소요 시간을 아직 측정하지 않았습니다)"), None),
    ("site_size_test_limit_mb", 50, "운영 화면 파일 크기를 시험이 보는 기준(MB, GitHub 경고선)", "2026-11-23", HAN,
     "0. 2026-11-20 밤의 상태 (먼저 읽기)",
     ("운영 화면의 파일 크기 기준(내부에서 4MB로 정했던 것)은 2026-11-23에 없앴습니다", "테스트는 GitHub의 경고선인 50MB만 봅니다"),
     "예전의 4MB 기준은 근거가 없어 없앴습니다. 영상에 4MB 상한이나 그 안에 든 크기를 쓰지 않습니다."),
]

DOC_FACTS += [
    # 발표 덱(proto_src/deck)이 더 쓰는 문서 값
    ("simple_uw_questions_by_org",
     {"EPOST": {"product": "우체국간편한건강보험 2606", "period_question": "최근 1년, 2년, 5년 이내 입원만", "major_diseases": 6},
      "HANWHALIFE": {"product": "한화생명 시그니처 H통합보험", "period_question": "입원 또는 수술(제왕절개 포함)", "major_diseases": 7},
      "SAMSUNGFIRE": {"product": "삼성화재 간편보험 새로고침", "period_question": "입원 또는 수술", "major_diseases": 5}},
     "간편심사 고지사항의 회사별 차이: 기간 질문이 묻는 병력과 중대질병 질문의 질병 수", SUB_SCOPE_DATE, SUB, "2. 풀려는 문제",
     ("| 우체국간편한건강보험 2606 | 최근 1년, 2년, 5년 이내 입원만 | 6대 질병 |",
      "| 한화생명 시그니처 H통합보험 | 입원 또는 수술(제왕절개 포함) | 7개 질병 |",
      "| 삼성화재 간편보험 새로고침 | 입원 또는 수술 | 5개 질병 |"), None),
    ("hanwha_rerun_verify_result", {"rows": 1437, "confirmed": 1323, "review": 109, "excluded": 5},
     "한화 급부 재추출(2026-11-19 저녁)의 검증 결과: 전체 줄, 확정, 사람 검토, 제외", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("| 한화 급부 재추출 1,437행 (2026-11-19 저녁) | 확정 1,323행, 사람 검토 109행, 제외 5행",), None),
    ("review_not_applied_items", 8, "제미나이의 표 추출기 검토 가운데 반영하지 않은 지적 수(실제 문서에서 패치가 안정되지 않음)", "2026-11-20", PRO,
     "버전 1 방향 결정과 삼성화재 적재 (2026-11-20 오후, Claude Code)",
     ("여덟 건을 세 갈래로 나눠 opus가 재현하고 sonnet이 점검했습니다", "고친 패치는 재점검 때마다 고치기 전보다 나빠지는 반례가 새로 나와 안정되지 않았습니다"),
     "지어낸 입력으로는 모두 재현됐지만 실제 문서 세 개에서 해당하는 자리는 한 곳뿐이었습니다(같은 절)."),
    ("site_file_size_mb", 6, "운영 화면 단독 파일의 크기(MB, 약)", "2026-11-23", "docs/validation/진행자_메모.md", "보내기 전에",
     ("`site/proto/console4.html` 한 파일(약 6MB)",), "어림값입니다. 화면에는 \"약\"을 붙여 씁니다."),
]

# 발표 덱 v3(점검 답 반영)이 범위와 출처를 밝히려고 더 쓰는 문서 값
PRO_EXTRACT = "급부 추출과 검증 (2026-11-18)"
PRO_NEXT = "다음 세션에서 이어 할 일 (2026-11-24 오후, 세션을 닫으며)"
DOC_FACTS += [
    ("simple_uw_product_short",
     {"EPOST": "우체국간편한건강보험", "HANWHALIFE": "한화생명 시그니처 H통합보험", "SAMSUNGFIRE": "삼성화재 간편보험 새로고침"},
     "간편심사 고지사항을 견준 회사별 상품 이름(우체국 상품명 뒤의 개정 코드를 뺀 것)", SUB_SCOPE_DATE, SUB, "2. 풀려는 문제",
     ("| 우체국간편한건강보험 2606 |", "| 한화생명 시그니처 H통합보험 |", "| 삼성화재 간편보험 새로고침 |"),
     "우체국 상품명 뒤의 2606 은 개정 코드(2026-06 판매 개시)라 화면에서는 빼고, 노트에는 simple_uw_questions_by_org.EPOST.product 를 씁니다."),
    ("calibration_score_overlap", {"correct_min": 0.59, "correct_median": 0.91, "wrong_max": 0.68, "wrong_amount_max": 0.49},
     "경계값 보정(모든 문항을 합친 줄 단위): 맞는 줄의 최저와 중앙값, 틀리게 바꾼 줄의 최고(감액 기간을 바꾼 경우)와 금액을 바꾼 경우의 최고",
     "2026-11-18", PRO, PRO_EXTRACT,
     ("맞는 줄의 최저 확률은 0.59, 중앙값 0.91입니다. 틀린 줄은 최고 0.68(감액 기간을 바꾼 경우)이고, 금액을 바꾼 경우는 최고 0.49입니다.",),
     "맞는 줄의 최저와 틀린 줄의 최고가 겹칩니다. symmetric_choice_probability(0.94, 0.06)는 면책 문항 한 가지의 값입니다."),
    ("calibration_correct_to_review", {"threshold": 0.75, "rows": 7, "of": 101},
     "확정 경계 0.75 에서 맞는 줄 가운데 사람 검토로 간 줄 수(전체 맞는 줄 수)", "2026-11-18", PRO, PRO_EXTRACT,
     ("| 0.75 | 0 / 437 | 7 / 101 |",), "우체국 요약서 2건으로만 맞춘 좁은 표본입니다(같은 절의 한계)."),
    ("calibration_flip_methods",
     ["금액 두 배", "다른 줄의 금액", "감액 누락", "감액과 지급액 뒤바꿈", "감액 기간 바꿈", "없는 감액 추가", "면책 뒤집음"],
     "경계값 보정에서 맞는 줄을 일부러 틀리게 바꾼 방식(scripts/calibrate_verify.py)", "2026-11-18", PRO, PRO_EXTRACT,
     ("(금액 두 배, 다른 줄의 금액, 감액 누락, 감액과 지급액 뒤바꿈, 감액 기간 바꿈, 없는 감액 추가, 면책 뒤집음)",),
     "실제 운영에서 생긴 오류가 아니라 일부러 만든 오류입니다."),
    ("epost_summary_rows_by_doc", {"간편한건강보험 2606": 49, "통합건강보험 2504": 52},
     "원문 표와 한 줄씩 대조한 우체국 요약서 2건의 급부 줄 수(문서별)", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("101행 모두 일치 (2606 49행, 통합 2504 52행)",), "합계는 epost_summary_rows_matched.total 입니다."),
    ("goldset_item_totals", {"EPOST": 85, "HANWHALIFE": 25, "SAMSUNGFIRE": 50},
     "회사별 정답셋 전체 항목 수(보장금액, 가입조건, 결합 제약 따위를 합친 수)", SUB_SCOPE_DATE, SUB, "제미나이: 추출기와 따로 보는 교차 확인",
     ("정답셋(우체국 85항목, 한화생명 25항목, 삼성화재 50항목)",),
     "보장금액, 면책, 감액 영역의 정답 대조는 goldset_epost_benefit(30항목), goldset_hanwha_benefit(14항목)입니다."),
    ("goldset_epost_conditions", {"items": 20, "match": 16}, "우체국 정답셋 가입조건 정답 대조(일치 항목 수)", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("| 우체국 정답셋 가입조건 | 20항목 중 16항목 일치",), "1항목은 종형 속성에 들어 있고 나머지는 스키마 밖입니다(같은 표)."),
    ("goldset_epost_constraints", {"items": 10, "match": 5}, "우체국 정답셋 결합 제약 정답 대조(일치 항목 수)", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("| 우체국 정답셋 결합 제약 | 10항목 중 5항목 일치",), "나머지는 스키마 밖입니다(같은 표)."),
    ("goldset_not_scored", {"SAMSUNGFIRE": 50}, "아직 정답과 대조하지 않은 정답셋(회사와 항목 수)", SUB_SCOPE_DATE, SUB, "7. 성과 지표",
     ("삼성화재 정답셋 50항목 정답 대조",), None),
    ("samsungfire_benefit_reader", "코드 규칙", "삼성화재 급부표를 읽는 방법(모델을 쓰지 않음)", SUB_SCOPE_DATE, SUB, "작업별 모델 배정",
     ("| 삼성화재 급부표 | 코드 규칙 |",), "extract/tables.py 와 extract/table_rules.py 입니다."),
    ("next_load_orgs", {"names": ["교보생명", "현대해상"], "stage": "추출과 원문 표본 대조까지 끝났고 시트 적재 전"},
     "다음에 시트에 적재할 회사와 지금 단계", "2026-11-24", PRO, PRO_NEXT,
     ("교보생명과 현대해상의 후속 수정은 워크플로가 끝났지만 커밋하지 않았습니다", "그 뒤 카본 표본, 시트 적재, 매핑 순서로 갑니다."),
     "사본(data/snapshot)에는 아직 없습니다. 적재하면 product_orgs 에 들어옵니다."),
]

# git 과 GitHub 에서 센 값. 사본에서 셀 수 없고 커밋할 때마다 바뀌므로 손으로 적고, note 에 다시 세는 명령을 적는다.
GIT_COUNTED_AT = "2026-11-24"
MANUAL_FACTS: list[tuple[str, Any, str, str, str]] = [
    ("test_count", 1515, "전체 자동 시험 수", "2026-11-25",
     "메인 세션이 2026-11-25(한국 시간) main 에서 센 값이고 문서에는 아직 없습니다. 발표 전에 `python -m pytest -q` 로 다시 셉니다."),
    ("commit_count", 287, "main 의 커밋 수", GIT_COUNTED_AT,
     "2026-11-24 main(544137848bee)에서 `git rev-list --count main` 으로 센 값입니다. 제출 직전에 다시 셉니다."),
    ("commits_by_date", {"2026-11-18": 41, "2026-11-19": 54, "2026-11-20": 63, "2026-11-21": 8, "2026-11-22": 0,
                         "2026-11-23": 87, "2026-11-24": 34},
     "main 의 날짜별 커밋 수(한국 시간)", GIT_COUNTED_AT,
     "`TZ=Asia/Seoul git log main --format=%ad --date=format-local:%Y-%m-%d | sort | uniq -c` 로 센 값입니다(커밋이 없는 날은 0). "
     "제출 직전에 다시 셉니다."),
    ("commits_by_author", {"Claude": 245, "Antigravity": 31, "github-actions[bot]": 11}, "main 의 작성자별 커밋 수", GIT_COUNTED_AT,
     "`git shortlog -sn main` 으로 센 값입니다. github-actions[bot] 은 주간 스냅샷과 시장 동향 수집의 자동 커밋입니다."),
    ("project_days", {"first": "2026-11-18", "last": "2026-11-24", "days": 7}, "첫 커밋 날부터 셈한 날까지의 날 수(양 끝 포함, 한국 시간)",
     GIT_COUNTED_AT, "commits_by_date 의 첫 날과 센 날입니다. 제출 직전에 commits_by_date 와 함께 다시 셉니다."),
    ("pr_counts", {"total": 8, "merged": 7, "open": 1}, "Antigravity 가 연 PR 수(전체, 머지, 열림)", GIT_COUNTED_AT,
     "`gh pr list --state all` 로 센 값입니다. 열린 하나는 PR 7(발표 애니메이션)입니다."),
    ("pages_status", {"status": "built", "url": "https://bluethestyle.github.io/korea_post_life/"},
     "GitHub Pages 배포 상태와 공개 주소", GIT_COUNTED_AT,
     "`gh api repos/bluethestyle/korea_post_life/pages` 의 status 와 html_url 입니다. 데모는 url 뒤에 proto/console4.html 을 붙입니다."),
    # 사용자가 준 값(2026-11-24). 통화를 바꾸거나 더하지 않고 준 그대로 싣는다
    ("subscription_claude_usd_per_month", 200, "개발과 초기 적재에 쓴 Claude 구독 요금제의 월 금액(달러)", "2026-11-24",
     "사용자 확인 2026-11-24. 개발과 초기 적재에 쓴 구독 도구의 요금제 금액이고 매주 자동 실행의 비용이 아닙니다."),
    ("subscription_gemini_krw_per_month", 119000, "개발과 초기 적재에 쓴 Gemini 구독 요금제(Ultra)의 월 금액(원)", "2026-11-24",
     "사용자 확인 2026-11-24. 개발과 초기 적재에 쓴 구독 도구의 요금제 금액이고 매주 자동 실행의 비용이 아닙니다. "
     "Antigravity 의 금액은 사용자 확인 중이라 따로 싣지 않습니다."),
    # 실무자 응답(사용자가 전달한 값, 2026-11-24). 실무자 1명이 보기에서 고른 답이라 측정값이 아니다
    ("practice_compare_source", "각 회사 공시실의 상품요약서, 사업방법서, 약관", "실무자가 타사 상품을 비교할 때 주로 보는 자료", "2026-11-24",
     "실무자 응답(사용자 전달) 2026-11-24. 실무자 1명이 보기에서 고른 답이고 측정값이 아닙니다. 응답자가 늘면 고칩니다."),
    ("practice_compare_time", "2~3일", "타사 상품 하나를 우리 상품과 담보별로 비교표로 정리하는 데 걸리는 시간(실무자 답)", "2026-11-24",
     "실무자 응답(사용자 전달) 2026-11-24. 실무자 1명이 보기에서 고른 답이고 측정값이 아닙니다. 응답자가 늘면 고칩니다."),
    ("practice_compare_frequency", "분기 1~2회", "이런 비교를 하는 빈도(실무자 답)", "2026-11-24",
     "실무자 응답(사용자 전달) 2026-11-24. 실무자 1명이 보기에서 고른 답이고 측정값이 아닙니다. 응답자가 늘면 고칩니다."),
    ("practice_respondents", 1, "위 실무자 응답의 응답자 수", "2026-11-24",
     "실무자 응답(사용자 전달) 2026-11-24. 실무자 1명이 보기에서 고른 답이고 측정값이 아닙니다. 응답자가 늘면 고칩니다."),
]


class FactsError(RuntimeError):
    """사실 자료를 만들 수 없다(화면 자료와 사본의 시각이 다르거나, 문서의 근거 문구가 없거나, 자료의 꼴이 예상과 다르다)."""


# ---------------------------------------------------------------------------
# 문서
# ---------------------------------------------------------------------------
def section_text(path: Path, title: str) -> str:
    """제목이 title 인 절(그 줄부터 같은 수준이나 더 높은 수준의 다음 제목 앞까지)의 글. 없으면 FactsError."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(#+) (.+?)\s*$", line)
        if m and m.group(2) == title:
            level = len(m.group(1))
            end = len(lines)
            for j in range(i + 1, len(lines)):
                n = re.match(r"^(#+) ", lines[j])
                if n and len(n.group(1)) <= level:
                    end = j
                    break
            return "\n".join(lines[i:end])
    raise FactsError(f"{path.name}: 절 제목 '{title}'이 없다")


def missing_quotes(root: Path, path: str, section: str, quotes: tuple[str, ...]) -> list[str]:
    """그 절에 글자 그대로 없는 근거 문구."""
    text = section_text(root / path, section)
    return [q for q in quotes if q not in text]


def doc_facts(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, value, label, as_of, path, section, quotes, note in DOC_FACTS:
        if not (root / path).exists():
            raise FactsError(f"{key}: 문서 {path} 가 없다")
        lost = missing_quotes(root, path, section, quotes)
        if lost:
            raise FactsError(f"{key}: {path} '{section}' 절에 근거 문구가 없다(문서가 바뀌었으면 값을 다시 확인): {lost}")
        out[key] = fact(value, label, as_of, {"kind": "document", "path": path, "section": section, "quotes": list(quotes)}, note)
    return out


# ---------------------------------------------------------------------------
# 도우미
# ---------------------------------------------------------------------------
def fact(value: Any, label: str, as_of: str, source: dict[str, Any], note: str | None = None) -> dict[str, Any]:
    out = {"value": value, "label": label, "as_of": as_of, "source": source}
    if note:
        out["note"] = note
    return out


def ordered(counter: Counter, order: tuple[str, ...]) -> dict[str, int]:
    """order 차례로, 그 밖의 값은 이름 차례로. 0인 값은 싣지 않는다."""
    keys = [k for k in order if counter.get(k)] + sorted(k for k in counter if k not in order and counter[k])
    return {k: counter[k] for k in keys}


def by_org(counter: Counter) -> dict[str, int]:
    return ordered(counter, ORG_ORDER)


def nested_by_org(pairs: Counter, inner_order: tuple[str, ...]) -> dict[str, dict[str, int]]:
    orgs = by_org(Counter(org for (org, _), n in pairs.items() if n))
    return {org: ordered(Counter({k: n for (o, k), n in pairs.items() if o == org}), inner_order) for org in orgs}


def total(counts: dict[str, int], orgs: tuple[str, ...] | None = None) -> int:
    return sum(n for org, n in counts.items() if orgs is None or org in orgs)


def snap_source(file: str, method: str) -> dict[str, str]:
    return {"kind": "snapshot", "file": (SNAPSHOT / file).as_posix(), "method": method}


def screen_source(path: str, file: Path = SALES) -> dict[str, str]:
    return {"kind": "screen_data", "file": file.as_posix(), "path": path}


def config_source(name: str) -> dict[str, str]:
    return {"kind": "config", "file": "src/postlife/config.py", "name": name}


# ---------------------------------------------------------------------------
# 사본, 설정, 시드
# ---------------------------------------------------------------------------
class Snapshot:
    """사본의 행과, 행에서 기관코드를 찾는 길."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]]):
        self.t = tables
        self.variant_org = {r["종형ID"]: r["기관코드"] for r in tables["sys_상품종형"]}
        self.rider = {r["특약ID"]: r for r in tables["sys_특약"]}
        self.benefit = {r["급부ID"]: r for r in tables["sys_급부"]}

    def org_of_rider(self, tid: str) -> str:
        return self.variant_org[self.rider[tid]["종형ID"]]

    def org_of_benefit(self, bid: str) -> str:
        return self.org_of_rider(self.benefit[bid]["특약ID"])


def main_condition(snap: Snapshot, row: dict[str, Any]) -> bool:
    """주계약 가입조건 행: 특약ID 가 비었거나 주계약 특약을 가리킨다."""
    tid = row.get("특약ID")
    return not tid or snap.rider.get(tid, {}).get("담보구분") == "주계약"


def snapshot_facts(root: Path, tables: dict[str, list[dict[str, Any]]], as_of: str) -> dict[str, dict[str, Any]]:
    snap = Snapshot(tables)
    site = tuple(config.SITE_ORGS)
    site_tables = site_orgs.filter_tables(tables, site)
    out: dict[str, dict[str, Any]] = {}

    # 기관
    product_orgs = list(by_org(Counter(snap.variant_org.values())))
    names = {c: config.INSTITUTIONS.get(c, c) for c in dict.fromkeys([*product_orgs, *site])}
    out["org_names"] = fact(names, "기관코드와 기관 이름(상품 자료가 든 기관과 화면에 올린 기관)", as_of, config_source("INSTITUTIONS"))
    out["product_orgs"] = fact(product_orgs, "상품 자료가 사본에 든 기관", as_of,
                               snap_source("sys_상품종형.jsonl", "기관코드의 서로 다른 값"))
    out["product_org_count"] = fact(len(product_orgs), "상품 자료가 사본에 든 기관 수", as_of,
                                    snap_source("sys_상품종형.jsonl", "기관코드의 서로 다른 값의 수"))
    out["site_orgs"] = fact(list(site), "화면에 올린 기관", as_of, config_source("SITE_ORGS"))
    out["site_org_count"] = fact(len(site), "화면에 올린 기관 수", as_of, config_source("SITE_ORGS"))

    # 종형
    v_org = Counter(r["기관코드"] for r in tables["sys_상품종형"])
    v_role = Counter((r["기관코드"], r["비교역할구분"]) for r in tables["sys_상품종형"])
    out["variants_by_org"] = fact(by_org(v_org), "기관별 상품 종형 수", as_of, snap_source("sys_상품종형.jsonl", "기관코드별 행 수"))
    out["variants_by_org_role"] = fact(nested_by_org(v_role, ("정밀비교", "관문전용", "직전개정시연")), "기관별, 비교역할구분별 종형 수",
                                       as_of, snap_source("sys_상품종형.jsonl", "기관코드와 비교역할구분별 행 수"))
    out["variant_count_all"] = fact(total(by_org(v_org)), "사본의 상품 종형 수(모든 기관)", as_of,
                                    snap_source("sys_상품종형.jsonl", "행 수"))
    out["variant_count_site"] = fact(total(by_org(v_org), site), "화면에 올린 기관의 상품 종형 수", as_of,
                                     snap_source("sys_상품종형.jsonl", "SITE_ORGS 기관의 행 수"))
    # 판매 중과 판매 종료(화면에 올린 기관). 판매 종료 종형은 개정 전후 비교에만 쓴다(비교역할구분 직전개정시연)
    site_rows = [r for r in tables["sys_상품종형"] if r["기관코드"] in site]
    ended = [r for r in site_rows if r.get("판매종료일")]
    on_sale = [r for r in site_rows if not r.get("판매종료일")]

    def product_short(r: dict[str, Any]) -> str:
        """공시상품명에서 무배당, 괄호, 개정 번호 뒤의 종 이름을 뺀 상품 이름과 개정 번호(예: 우체국간편건강보험 2504)."""
        text = re.sub(r"\([^)]*\)", "", r["공시상품명"]).replace("무배당", " ")
        m = re.match(r"\s*(.+?)\s*(\d{4})\b", text)
        return f"{m.group(1).strip()} {m.group(2)}" if m else r["공시상품명"]

    out["variant_sale_status_site"] = fact(
        {"total": len(site_rows), "on_sale": len(on_sale), "ended": len(ended),
         "on_sale_by_role": dict(Counter(r["비교역할구분"] for r in on_sale)),
         "ended_by_role": dict(Counter(r["비교역할구분"] for r in ended)),
         "ended_products": sorted({product_short(r) for r in ended}),
         "ended_variants": [r["종형명"] for r in ended],
         "ended_dates": sorted({r["판매종료일"] for r in ended})},
        "화면에 올린 기관의 상품 종형을 판매 중(판매종료일 없음)과 판매 종료로 나눈 수, 비교역할구분별 수, 판매 종료 상품 이름과 판매종료일",
        as_of, snap_source("sys_상품종형.jsonl", "SITE_ORGS 기관의 행을 판매종료일이 있는지로 나눔. 상품 이름은 공시상품명에서 "
                           "무배당과 괄호를 빼고 개정 번호까지"),
        "판매 종료 종형(비교역할 직전개정시연, 화면 이름 직전 개정 상품)은 개정 전후 비교에만 쓰고 담보 비교의 기준 종형이나 타사로 "
        "쓰지 않습니다.")

    # 특약
    r_org = by_org(Counter(snap.variant_org[r["종형ID"]] for r in tables["sys_특약"]))
    out["riders_by_org"] = fact(r_org, "기관별 특약 수(주계약 줄 포함)", as_of,
                                snap_source("sys_특약.jsonl", "종형ID로 기관코드를 찾아 기관별 행 수"))
    out["rider_count_all"] = fact(total(r_org), "사본의 특약 수(모든 기관, 주계약 줄 포함)", as_of, snap_source("sys_특약.jsonl", "행 수"))
    out["rider_count_site"] = fact(total(r_org, site), "화면에 올린 기관의 특약 수(주계약 줄 포함)", as_of,
                                   snap_source("sys_특약.jsonl", "SITE_ORGS 기관의 행 수"))

    # 급부
    basis = Counter((snap.org_of_rider(b["특약ID"]), b.get("지급기준구분") or "금액") for b in tables["sys_급부"])
    by_basis = nested_by_org(basis, BASIS_ORDER)
    kind = {org: {"amount": sum(n for k, n in d.items() if k not in NO_AMOUNT_BASES),
                  "non_amount": sum(n for k, n in d.items() if k in NO_AMOUNT_BASES)} for org, d in by_basis.items()}
    b_org = {org: d["amount"] + d["non_amount"] for org, d in kind.items()}
    out["benefits_by_org"] = fact(b_org, "기관별 급부 수", as_of, snap_source("sys_급부.jsonl", "특약ID로 기관코드를 찾아 기관별 행 수"))
    out["benefits_by_org_kind"] = fact(
        kind, "기관별 급부 수를 금액 급부(amount: 금액, 가입금액비율)와 금액 하나로 담기지 않는 급부(non_amount)로 나눈 것", as_of,
        snap_source("sys_급부.jsonl", "지급기준구분(비면 금액)으로 가름. 담기지 않는 꼴은 validate.NO_AMOUNT_BASES"))
    out["benefits_by_org_basis"] = fact(by_basis, "기관별, 지급기준구분별 급부 수(비면 금액)", as_of,
                                        snap_source("sys_급부.jsonl", "기관코드와 지급기준구분별 행 수"))
    out["benefit_count_all"] = fact(total(b_org), "사본의 급부 수(모든 기관)", as_of, snap_source("sys_급부.jsonl", "행 수"))
    out["benefit_count_site"] = fact(total(b_org, site), "화면에 올린 기관의 급부 수", as_of,
                                     snap_source("sys_급부.jsonl", "SITE_ORGS 기관의 행 수"))

    # 가입조건과 결합 제약
    main_rows = by_org(Counter(snap.variant_org[r["종형ID"]] for r in tables["sys_가입조건"] if main_condition(snap, r)))
    rider_rows = by_org(Counter(snap.variant_org[r["종형ID"]] for r in tables["sys_가입조건"] if not main_condition(snap, r)))
    out["main_condition_rows_by_org"] = fact(main_rows, "기관별 주계약 가입조건 행 수", as_of,
                                             snap_source("sys_가입조건.jsonl", "특약ID 가 비었거나 주계약 특약을 가리키는 행을 기관별로 셈"))
    out["rider_condition_rows_by_org"] = fact(rider_rows, "기관별 특약 가입조건 행 수", as_of,
                                              snap_source("sys_가입조건.jsonl", "특약ID 가 주계약이 아닌 특약을 가리키는 행을 기관별로 셈"))
    out["combination_constraints_by_org"] = fact(
        by_org(Counter(snap.variant_org[r["종형ID"]] for r in tables["sys_결합제약"])), "기관별 결합 제약 행 수", as_of,
        snap_source("sys_결합제약.jsonl", "종형ID로 기관코드를 찾아 기관별 행 수"))

    # 담보 매핑
    states = Counter()
    orphan = 0
    for m in tables["hum_담보매핑"]:
        if m["급부ID"] in snap.benefit:
            states[(snap.org_of_benefit(m["급부ID"]), m["검토상태"])] += 1
        else:
            orphan += 1
    st_org = nested_by_org(states, STATE_ORDER)

    def sum_states(orgs: tuple[str, ...] | None) -> dict[str, int]:
        c: Counter = Counter()
        for (o, k), n in states.items():
            if orgs is None or o in orgs:
                c[k] += n
        return ordered(c, STATE_ORDER)

    mapped = {m["급부ID"] for m in tables["hum_담보매핑"]}
    out["mapping_status_by_org"] = fact(st_org, "기관별, 검토상태별 담보 매핑 수", as_of,
                                        snap_source("hum_담보매핑.jsonl", "급부ID로 기관코드를 찾아 기관과 검토상태별 행 수"))
    out["mapping_status_all"] = fact(sum_states(None), "검토상태별 담보 매핑 수(모든 기관)", as_of,
                                     snap_source("hum_담보매핑.jsonl", "검토상태별 행 수(급부가 있는 줄)"))
    out["mapping_status_site"] = fact(sum_states(site), "검토상태별 담보 매핑 수(화면에 올린 기관)", as_of,
                                      snap_source("hum_담보매핑.jsonl", "SITE_ORGS 기관의 검토상태별 행 수"))
    out["benefits_without_mapping"] = fact(sum(1 for b in snap.benefit if b not in mapped), "매핑 줄이 없는 급부 수", as_of,
                                           snap_source("sys_급부.jsonl", "hum_담보매핑 에 급부ID 가 없는 급부 행 수"))
    out["mapping_rows_without_benefit"] = fact(orphan, "급부가 없는 매핑 줄 수", as_of,
                                               snap_source("hum_담보매핑.jsonl", "sys_급부 에 급부ID 가 없는 매핑 행 수"))

    # 표준담보 사전과 관계
    std = tables["hum_표준담보사전"]
    out["standard_coverage_rows"] = fact(len(std), "표준담보 사전 줄 수", as_of, snap_source("hum_표준담보사전.jsonl", "행 수"))
    in_use = [r for r in std if r.get("사용여부") is not False]
    out["standard_coverage_in_use"] = fact(len(in_use), "표준담보 사전에서 쓰는 담보 수", as_of,
                                           snap_source("hum_표준담보사전.jsonl", "사용여부가 거짓이 아닌 행 수"))
    out["standard_coverage_names"] = fact({t: [r["표준담보명"] for r in in_use if r["급부유형"] == t]
                                           for t in dict.fromkeys(r["급부유형"] for r in in_use)},
                                          "표준담보 사전에서 쓰는 담보 이름(급부유형별, 사본의 행 차례)", as_of,
                                          snap_source("hum_표준담보사전.jsonl", "사용여부가 거짓이 아닌 행의 표준담보명을 급부유형별로"))
    rel = [json.loads(line) for line in (root / RELATIONS).read_text(encoding="utf-8").splitlines() if line.strip()]
    rel_kind = ordered(Counter(r["관계"] for r in rel), ("포함", "통합"))
    seed_source = {"kind": "seed", "file": RELATIONS.as_posix(), "method": "행 수(관계별)"}
    out["coverage_relation_count"] = fact(len(rel), "표준담보 사이의 관계 줄 수(포함과 통합)", as_of, seed_source)
    out["coverage_relations_by_kind"] = fact(rel_kind, "관계별 표준담보 관계 줄 수", as_of, seed_source)

    # 작업 로그
    log = tables["sys_작업로그"]
    out["work_log_count"] = fact(len(log), "작업 로그 건수(모든 기관)", as_of, snap_source("sys_작업로그.jsonl", "행 수"))
    out["work_log_count_site"] = fact(len(site_tables["sys_작업로그"]), "화면에 실리는 작업 로그 건수(화면에 올린 기관)", as_of,
                                      snap_source("sys_작업로그.jsonl", "site/orgs.py 의 filter_tables 로 SITE_ORGS 밖 회사의 줄을 뺀 행 수"))
    out["work_log_by_stage"] = fact(ordered(Counter(r["작업단계"] for r in log), STAGE_ORDER), "작업단계별 작업 로그 건수(모든 기관)",
                                    as_of, snap_source("sys_작업로그.jsonl", "작업단계별 행 수"))
    out["work_log_by_result"] = fact(ordered(Counter(r["결과"] for r in log), RESULT_ORDER), "결과별 작업 로그 건수(모든 기관)", as_of,
                                     snap_source("sys_작업로그.jsonl", "결과별 행 수"))

    # 시장 소식
    news = tables["sys_시장동향"]
    out["market_news_count"] = fact(len(news), "사본의 시장 소식 건수", as_of, snap_source("sys_시장동향.jsonl", "행 수"))
    out["market_news_by_week"] = fact(dict(sorted(Counter(r["수집주차"] for r in news).items())), "수집주차별 시장 소식 건수", as_of,
                                      snap_source("sys_시장동향.jsonl", "수집주차별 행 수"))
    out["market_news_by_category"] = fact(ordered(Counter(r["분류유형"] for r in news), tuple(config.CATEGORIES)),
                                          "분류유형별 시장 소식 건수", as_of, snap_source("sys_시장동향.jsonl", "분류유형별 행 수"))

    # 빈 탭
    out["premium_example_rows"] = fact(len(tables["sys_보험료예시"]), "보험료 예시 행 수(2단계 과제)", as_of,
                                       snap_source("sys_보험료예시.jsonl", "행 수"))
    out["benefit_disease_code_rows"] = fact(len(tables["sys_급부질병코드"]), "급부 질병코드 행 수(2단계 과제)", as_of,
                                            snap_source("sys_급부질병코드.jsonl", "행 수"))

    # 기준값(검증 구간과 법정 한도)
    base = {r["기준키"]: r for r in tables["hum_기준값"]}
    for src_key, key, label in THRESHOLDS:
        if src_key not in base or base[src_key].get("수치값") is None:
            raise FactsError(f"hum_기준값에 {src_key} 의 수치값이 없다")
        out[key] = fact(base[src_key]["수치값"], label, as_of, snap_source("hum_기준값.jsonl", f"기준키 {src_key} 의 수치값"))

    # 개정 전후 예시(표적항암약물허가치료특약의 주급부)
    out["example_targeted_anticancer"] = fact(
        revision_example(tables, snap), "개정 전후 예시: 우체국 표적항암약물허가치료특약 주급부의 지급액, 면책, 감액, 근거 쪽", as_of,
        snap_source("sys_급부.jsonl", f"특약계보키 {EXAMPLE_LINEAGE} 인 우체국 특약의 주급부를 개정판ID별로 묶음(값이 개정판 안에서 같은지 확인)"),
        "기준 가입금액 1,000만 원에 대한 지급액입니다. 감액은 계약일부터 그 개월 수 안에 지급 사유가 생기면 그 비율로 지급합니다.")
    return out


def revision_example(tables: dict[str, list[dict[str, Any]]], snap: Snapshot) -> dict[str, Any]:
    variants = {r["종형ID"]: r for r in tables["sys_상품종형"]}
    groups: dict[str, list[tuple[dict, dict, dict]]] = {}
    for b in tables["sys_급부"]:
        r = snap.rider[b["특약ID"]]
        v = variants[r["종형ID"]]
        if v["기관코드"] == "EPOST" and r["특약계보키"] == EXAMPLE_LINEAGE and b["급부역할"] == "주급부":
            groups.setdefault(v["개정판ID"], []).append((v, r, b))
    if len(groups) != 2:
        raise FactsError(f"개정 전후 예시의 개정판이 둘이 아니다: {sorted(groups)}")
    revisions = []
    cols = ("기준가입금액만원", "기준지급금액만원", "면책기간일수", "감액개월1", "감액지급률1", "감액개월2", "감액지급률2")
    for rev_id, rows in groups.items():
        values = {tuple(b[c] for c in cols) for _, _, b in rows}
        benefit_names = {b["원시급부명"] for _, _, b in rows}
        starts = {v["적용시작일"] for v, _, _ in rows}
        ends = {v.get("판매종료일") for v, _, _ in rows}
        doc_kinds = {b["근거문서종류"] for _, _, b in rows}
        if len(values) != 1 or len(benefit_names) != 1 or len(starts) != 1 or len(ends) != 1 or len(doc_kinds) != 1:
            raise FactsError(f"개정 전후 예시: {rev_id} 안에서 값이 갈린다")
        base_amt, pay, wait, m1, p1, m2, p2 = values.pop()
        revisions.append({
            "revision_id": rev_id,
            "revision_no": rev_id.rsplit("_", 1)[-1],
            "products": sorted({v["공시상품명"] for v, _, _ in rows}),
            "riders": sorted({r["원시특약명"] for _, r, _ in rows}),
            "benefit": benefit_names.pop(),
            "sale_start": starts.pop(),
            "sale_end": ends.pop(),
            "basis_manwon": base_amt,
            "pay_manwon": pay,
            "waiting_days": wait,
            "reduce": [{"months": m, "rate": p} for m, p in ((m1, p1), (m2, p2)) if m is not None and p is not None],
            "doc_kind": doc_kinds.pop(),
            "doc_pages": sorted({b["근거문서쪽수"] for _, _, b in rows if b.get("근거문서쪽수") is not None}),
        })
    revisions.sort(key=lambda x: x["sale_start"])
    return {"rider_lineage_key": EXAMPLE_LINEAGE, "revisions": revisions}


def config_facts(as_of: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    out["sheet_tab_count"] = fact(len(schema.TABS), "구글 시트 정본의 탭 수", as_of,
                                  {"kind": "schema", "file": "src/postlife/schema.py", "name": "TABS"})
    out["market_news_institution_count"] = fact(len(config.TREND_INSTITUTIONS), "시장 소식을 모으는 기관 수", as_of,
                                                config_source("TREND_INSTITUTIONS"))
    out["market_news_institutions_by_sector"] = fact(
        {"생명보험": len(config.TREND_LIFE), "손해보험": len(config.NONLIFE), "우체국": len(config.POST)}, "시장 소식을 모으는 기관 수(업권별)",
        as_of, config_source("TREND_LIFE, NONLIFE, POST"))
    out["market_news_institution_names"] = fact(
        {"생명보험": list(config.TREND_LIFE.values()), "손해보험": list(config.NONLIFE.values()), "우체국": list(config.POST.values())},
        "시장 소식을 모으는 기관 이름", as_of, config_source("TREND_LIFE, NONLIFE, POST"))
    out["market_news_categories"] = fact(list(config.CATEGORIES), "모으는 시장 소식의 분류유형", as_of, config_source("CATEGORIES"))
    out["market_news_category_count"] = fact(len(config.CATEGORIES), "모으는 시장 소식의 분류유형 수", as_of, config_source("CATEGORIES"))
    out["news_excluded_topics"] = fact(config.EXCLUDED_TOPICS.split(", "), "버리는 소식 주제", as_of, config_source("EXCLUDED_TOPICS"))
    out["news_excluded_lines"] = fact(config.EXCLUDED_LINES.split(", "), "버리는 보험 종목(사람의 건강, 생명 보장과 무관)", as_of,
                                      config_source("EXCLUDED_LINES"))
    plan = {}
    for day, queries in config.DAILY_PLAN.items():
        orgs = list(dict.fromkeys(c for q in queries for c in q.orgs))
        plan[WEEKDAYS[day]] = {"orgs": [config.ALL_ORGS[c] for c in orgs], "queries": len(queries)}
    out["collect_daily_plan"] = fact(plan, "요일별 시장 소식 검색 대상 기관과 검색 질의 수", as_of, config_source("DAILY_PLAN"),
                                     "일요일은 실패 건 재수집과 주간 마감에 씁니다(config.py 주석).")
    out["search_daily_limit_config"] = fact(config.SEARCH_DAILY_LIMIT, "검색 모델 하루 한도(회). 코드가 지키는 값", as_of,
                                            config_source("SEARCH_DAILY_LIMIT"))
    out["upper_model_calls_per_run"] = fact(config.EXTRACT_ESCALATIONS_PER_RUN, "한 번 실행에서 상위 모델로 다시 뽑는 횟수 상한", as_of,
                                            config_source("EXTRACT_ESCALATIONS_PER_RUN"))
    out["decide_tokens_per_minute_guard"] = fact(config.TOKENS_PER_MINUTE[config.MODEL_DECIDE],
                                                 "확률 산정 모델 호출 전에 최근 60초 입력 토큰(어림)을 이 값 아래로 맞춤(한도 5만에 여유 10%)",
                                                 as_of, config_source("TOKENS_PER_MINUTE"), "기다리는 기준이고 잰 사용량이 아닙니다.")
    out["models"] = fact({"search": config.MODEL_SEARCH, "extract": config.MODEL_EXTRACT, "extract_alt": config.MODEL_EXTRACT_ALT,
                          "decide": config.MODEL_DECIDE, "upper": config.MODEL_SUMMARY},
                         "작업별 모델 이름(검색, 추출, 보조 재추출, 확률 산정, 상위)", as_of,
                         config_source("MODEL_SEARCH, MODEL_EXTRACT, MODEL_EXTRACT_ALT, MODEL_DECIDE, MODEL_SUMMARY"))
    out["forbidden_words"] = fact(list(FORBIDDEN), "화면의 분석 문장에 쓰지 않는 말(빌드가 막음)", as_of,
                                  {"kind": "code", "file": "src/postlife/site/sales.py", "name": "FORBIDDEN"})
    return out


# ---------------------------------------------------------------------------
# 화면 자료(sales.json). 다시 계산하지 않고 옮긴다
# ---------------------------------------------------------------------------
INSIGHT_KEYS = {"관문 차이": "관문차이수", "앞세울 강점": "앞세울수", "관련 담보 안내": "관련담보수", "조건 열위 방어": "조건열위수",
                "개정 검토 후보": "개정검토수"}


def briefing(sales: dict[str, Any], vid: str) -> dict[str, Any]:
    """기준 종형 하나의 브리핑 값(대표 조건). 열쇠를 영문으로 옮길 뿐 값은 그대로다."""
    base = sales["기준별"][vid]
    lines = {x["줄"]: x["값"] for x in base["브리핑"]}
    ga, da, ra, ma = lines["가"], lines["다"], lines["라"], lines["마"]
    stages = base["치료여정"]["열"]
    if set(INSIGHT_KEYS) != set(sales["분류"]):
        raise FactsError(f"영업 인사이트 분류가 바뀌었다: {sales['분류']}")
    insights = {c: ma[INSIGHT_KEYS[c]] for c in sales["분류"]}
    if sum(insights.values()) != ma["전체수"]:
        raise FactsError(f"{vid}: 영업 인사이트 분류별 수의 합이 전체수와 다르다")
    return {
        "segment_map": {"cells": ga["전체칸수"], "ours_only_open": ga["우리간편만열림칸수"], "open_together": ga["함께열림칸수"],
                        "ours_closed": ga["우리간편닫힘칸수"], "all_closed": ga["간편모두닫힘칸수"], "no_data": ga["자료없음칸수"],
                        "gate_only": ga["관문만칸수"]},
        "gate": {"age_min": da["우리최저"], "age_max": da["우리최고"], "main_limit_manwon": int(str(da["주계약한도만원"]).replace(",", "")),
                 "question_diff_peer_count": da["관문차이수"], "question_diff_peers": da["관문차이상대"],
                 "structure_diff_peer_count": da["구조다름회사수"]},
        "coverage": {"common_pairs": ra["공통담보쌍"], "compared_pairs": ra["견준쌍"], "excluded_pending_pairs": ra["뺀비교쌍"],
                     "held": ra["보유수"], "held_by_stage": {s: ra[f"{s}수"] for s in stages},
                     "no_verdict_other_rider": ra["단정보류수"], "no_verdict_payment_form": ra["지급형태다름수"],
                     "peer_held": [{"name": p["이름"], "held": p["보유수"]} for p in ra["상대보유"]]},
        "insights": {"total": ma["전체수"], "by_category": insights, "lead_strengths": ma["대표강점요약"]},
    }


def screen_facts(sales: dict[str, Any], as_of: str) -> dict[str, dict[str, Any]]:
    bases = sales["기준종형"]
    first = bases[0]["종형ID"]
    b0 = briefing(sales, first)
    base_path = "기준별[기준종형[0].종형ID]"
    out: dict[str, dict[str, Any]] = {}
    ref = sales["기준조건"]
    out["reference_condition"] = fact({"age": ref["나이"], "sex": ref["성별"], "history": ref["이력"]},
                                      "브리핑 값을 계산한 대표 조건(sex M 은 남성, history null 은 이력 없음)", as_of, screen_source("기준조건"))
    out["base_variants"] = fact([{"id": b["종형ID"], "name": b["이름"], "underwriting": b["심사"], "renewal": b["갱신"]} for b in bases],
                                "기준으로 고를 수 있는 우체국 종형(첫째가 화면이 처음 여는 종형)", as_of, screen_source("기준종형"))
    out["default_base_variant"] = fact({"id": first, "name": bases[0]["이름"], "underwriting": bases[0]["심사"]},
                                       "화면이 처음 여는 기준 종형", as_of, screen_source("기준종형[0]"))
    seg, gate, cov, ins = b0["segment_map"], b0["gate"], b0["coverage"], b0["insights"]
    rows = [
        ("segment_map_cell_count", seg["cells"], "고객군 지도 칸 수", "브리핑[줄=가].값.전체칸수"),
        ("segment_map_open_together_cells", seg["open_together"], "고객군 지도: 우리 간편과 상대가 함께 열린 칸 수", "브리핑[줄=가].값.함께열림칸수"),
        ("segment_map_ours_closed_cells", seg["ours_closed"], "고객군 지도: 우리 간편이 닫혀 일반심사로 확인할 칸 수",
         "브리핑[줄=가].값.우리간편닫힘칸수"),
        ("segment_map_ours_only_open_cells", seg["ours_only_open"], "고객군 지도: 우리 간편만 열린 칸 수", "브리핑[줄=가].값.우리간편만열림칸수"),
        ("segment_map_gate_only_cells", seg["gate_only"], "고객군 지도: 상대가 우리에게 없는 고지 유형(관문만 수집한 종형)으로만 열린 칸 수",
         "브리핑[줄=가].값.관문만칸수"),
        ("reference_age_range", [gate["age_min"], gate["age_max"]], "기준 종형의 가입나이(최저, 최고)", "브리핑[줄=다].값.우리최저, 우리최고"),
        ("reference_main_contract_limit_manwon", gate["main_limit_manwon"], "대표 조건 나이의 주계약 한도(만 원)",
         "브리핑[줄=다].값.주계약한도만원"),
        ("gate_question_diff_peer_count", gate["question_diff_peer_count"], "고지 질문 범위가 다른 상대 회사 수", "브리핑[줄=다].값.관문차이수"),
        ("common_coverage_pairs", cov["common_pairs"], "공통 담보 쌍 수", "브리핑[줄=라].값.공통담보쌍"),
        ("compared_coverage_pairs", cov["compared_pairs"], "견준 담보 쌍 수(검토 대기 쌍을 뺌)", "브리핑[줄=라].값.견준쌍"),
        ("excluded_pending_pairs", cov["excluded_pending_pairs"], "검토 대기라 견주지 않은 담보 쌍 수", "브리핑[줄=라].값.뺀비교쌍"),
        ("held_coverage_count", cov["held"], "기준 종형이 가진 담보 수(확정 급부 기준)", "브리핑[줄=라].값.보유수"),
        ("held_coverage_by_stage", cov["held_by_stage"], "치료 단계별 기준 종형의 보유 담보 수", "브리핑[줄=라].값.진단수 따위(치료여정.열 차례)"),
        ("no_verdict_pairs", {"other_rider": cov["no_verdict_other_rider"], "payment_form": cov["no_verdict_payment_form"]},
         "우열을 단정하지 않은 비교 수(조건이 다른 특약을 함께 판매, 지급 형태가 다름)", "브리핑[줄=라].값.단정보류수, 지급형태다름수"),
        ("peer_held_coverage", cov["peer_held"], "맞붙는 상대 종형이 가진 담보 수", "브리핑[줄=라].값.상대보유"),
        ("sales_insight_count", ins["total"], "영업 인사이트 건수", "브리핑[줄=마].값.전체수"),
        ("sales_insight_by_category", ins["by_category"], "분류별 영업 인사이트 건수", "브리핑[줄=마].값.관문차이수 따위"),
        ("lead_strengths", ins["lead_strengths"], "앞세울 강점의 대표 담보", "브리핑[줄=마].값.대표강점요약"),
    ]
    for key, value, label, path in rows:
        out[key] = fact(value, label + " (화면이 처음 여는 기준 종형, 대표 조건)", as_of, screen_source(f"{base_path}.{path}"))
    out["briefing_by_base_variant"] = fact({b["이름"]: briefing(sales, b["종형ID"]) for b in bases},
                                           "기준 종형마다의 브리핑 값(대표 조건). 위 항목과 같은 값을 종형마다 모은 것", as_of,
                                           screen_source("기준별[종형ID].브리핑"))
    out["treatment_stages"] = fact(sales["기준별"][first]["치료여정"]["열"], "치료 단계(차례대로)", as_of,
                                   screen_source(f"{base_path}.치료여정.열"))
    out["sales_insight_categories"] = fact(list(sales["분류"]), "영업 인사이트 분류", as_of, screen_source("분류"))
    out["card_category_order"] = fact(list(sales["카드분류차례"]), "응대 카드에 싣는 분류의 차례", as_of, screen_source("카드분류차례"))
    out["segment_map_labels"] = fact(list(sales["라벨"]), "고객군 지도 칸의 라벨", as_of, screen_source("라벨"))
    m = sales["지도"]["전체"]
    out["segment_map_rows"] = fact([r["이름"] for r in m["행"]], "고객군 지도의 행(입원과 수술 이력)", as_of, screen_source("지도.전체.행[].이름"))
    out["segment_map_columns"] = fact([f"{c['lo']}~{c['hi']}세" for c in m["열"]], "고객군 지도의 열(가입나이 구간)", as_of,
                                      screen_source("지도.전체.열[].lo, hi"))
    out["segment_map_grid"] = fact(segment_grid(m), "고객군 지도의 칸마다의 값(행은 segment_map_rows, 칸은 segment_map_columns 차례). "
                                   "label 은 칸의 라벨, sub 는 칸의 보조 줄, gate_only 는 그 칸의 상대가 우리에게 없는 고지 유형"
                                   "(관문만 수집한 종형)으로만 열렸는지", as_of,
                                   screen_source("지도.전체.칸[행][열].라벨, 보조, 관문만수집(비지 않으면 gate_only 참)"))
    news = sales["시장소식"]
    out["screen_market_news"] = fact({"week": news["주차"], "count": news["건수"]}, "화면 1이 싣는 이번 주차와 그 주차의 시장 소식 건수", as_of,
                                     screen_source("시장소식.주차, 건수"))
    out["revision_changes"] = fact(dict(sales["개정변동"]["수"]), "직전 개정과 견주어 달라진 담보 수(신설, 변경, 종료, 전체)", as_of,
                                   screen_source("개정변동.수"))
    return out


def segment_grid(m: dict[str, Any]) -> list[dict[str, Any]]:
    """고객군 지도(sales.json 의 지도.전체)의 칸을 행마다 옮긴다. 라벨과 보조 줄은 그대로, gate_only 는 칸의 관문만수집이 비었는지다
    (브리핑 (가)의 관문만칸수가 세는 칸과 같다). 다시 판정하지 않는다."""
    cols = [f"{c['lo']}~{c['hi']}세" for c in m["열"]]
    if any(len(line) != len(cols) for line in m["칸"]) or len(m["칸"]) != len(m["행"]):
        raise FactsError("고객군 지도의 칸이 행과 열의 수와 맞지 않는다")
    return [{"row": r["이름"], "cells": [{"column": col, "label": x["라벨"], "sub": x.get("보조"), "gate_only": bool(x.get("관문만수집"))}
                                       for col, x in zip(cols, line)]}
            for r, line in zip(m["행"], m["칸"])]


def cover_facts(sales: dict[str, Any], cover: dict[str, Any], as_of: str) -> dict[str, dict[str, Any]]:
    """담보 비교 자료(cover.json)에서 옮기는 값. 기준 종형의 칸(rows[k][1][0])을 읽기만 한다."""
    first = sales["기준종형"][0]["종형ID"]
    base = cover["b"][first]
    if base["cols"][0] != first:
        raise FactsError(f"cover.json 의 첫 열이 기준 종형({first})이 아니다")
    names = sales["표준담보"]
    items = []
    for sid, cells, *_ in base["rows"]:
        ours = cells[0]
        # 우리 칸이 객체이고 확정 급부(i)도 매핑 대기(w)도 없이 관계 담보(c)만 있으면 관계 담보로 덮는 담보다(API.md)
        if isinstance(ours, dict) and not ours.get("i") and not ours.get("w") and ours.get("c"):
            kind, via, partial = ours["c"]
            items.append({"id": sid, "name": names[sid]["이름"], "kind": kind, "via": [names[v]["이름"] for v in via], "partial": partial})
    return {"relation_covered_coverages": fact(
        {"count": len(items), "items": items},
        "기준 종형이 그 담보의 확정 급부도 매핑 대기 급부도 없이 관계 담보(넓은 담보, 부분 담보)로만 덮는 표준담보 "
        "(화면이 처음 여는 기준 종형). via 는 덮는 우리 담보, partial 은 부분 담보 가운데 일부만 가졌는지", as_of,
        screen_source("b[기준종형[0].종형ID].rows[k][1][0] 가운데 i, w 없이 c 만 있는 칸", COVER),
        "보유 담보 수(held_coverage_count)에 들지 않습니다. 관계 담보로 덮는 것이지 그 담보를 가진 것은 아닙니다.")}


# ---------------------------------------------------------------------------
# 발표 덱(proto_src/deck)이 더 쓰는 값. 사본, 화면 자료, 관계 그래프 자료, 설정, 코드에서 센다
# ---------------------------------------------------------------------------
GRAPH = Path("proto_src") / "graph" / "graph.json"
WORKFLOWS = Path(".github") / "workflows"
REQUESTS = Path("docs") / "gemini_requests"
VIDEO_TIMINGS = Path("proto_src") / "deck" / "assets" / "stills_timings.json"   # 덱의 영상 정지 화면을 뽑은 렌더 기록
EXAMPLE_STD = "STD_CA_SURG"                    # 암 수술비. 덱이 처음부터 끝까지 따라가는 담보 예
EXAMPLE_SPLIT_BROAD = "STD_CV_SURG"             # 뇌·심장질환 수술비. 타사는 통합 특약 하나, 우체국은 나눈 특약 둘로 가진 예
EXAMPLE_SPLIT_NARROW = ("STD_BR_SURG", "STD_HT_SURG")   # 뇌혈관질환 수술비, 심장질환 수술비
EXAMPLE_GATE_ROW, EXAMPLE_GATE_ROW_LATER = "입원 3개월~1년 전", "입원 1~2년 전"   # 6개월 전 입원 고객 예와 1년 반 전 입원
TEXT_EXAMPLE = {"amount": "1,000만원", "reduced_period": "1년미만", "reduced_amount": "500만원"}
TEXT_EXAMPLE_QUOTE = "\"1년미만 500만원 / 1년이상 1,000만원\""


def whole(x: float | None) -> float | int | None:
    """정수로 떨어지는 실수는 정수로(1000.0 → 1000). 덱이 "1,000"으로 적게 한다."""
    return int(x) if isinstance(x, float) and x.is_integer() else x


def derived_source(keys: list[str], method: str) -> dict[str, Any]:
    return {"kind": "derived", "from": keys, "method": method}


def repo_source(file: str, method: str) -> dict[str, str]:
    return {"kind": "repo", "file": file, "method": method}


def kst_schedule(root: Path, file: str) -> dict[str, str]:
    """워크플로의 cron(UTC)을 한국 시간(UTC+9)의 시각과 요일로. 분, 시, 요일 칸만 본다."""
    text = (root / WORKFLOWS / file).read_text(encoding="utf-8")
    m = re.search(r'cron:\s*"(\d+) (\d+) \* \* (\*|\d)"', text)
    if not m:
        raise FactsError(f"{file}: cron 을 읽지 못했다")
    minute, hour, dow = int(m.group(1)), int(m.group(2)), m.group(3)
    hour_kst = hour + 9
    shift = hour_kst // 24
    hour_kst %= 24
    # cron 의 요일: 0=일, 1=월 … 6=토
    days = "매일" if dow == "*" else ("일", "월", "화", "수", "목", "금", "토")[(int(dow) + shift) % 7]
    return {"time": f"{hour_kst:02d}:{minute:02d}", "days": days, "cron_utc": m.group(0).split('"')[1]}


def cover_cell_benefit(cover: dict[str, Any], cell: Any) -> list | None:
    """담보 비교 칸(cover.json rows[k][1][i])이 대표로 쓰는 급부(ben 순번 r). 칸이 비었거나 대표가 없으면 None."""
    if isinstance(cell, dict) and cell.get("r") is not None:
        return cover["ben"][cell["r"]]
    return None


def deck_facts(root: Path, tables: dict[str, list[dict[str, Any]]], sales: dict[str, Any], cover: dict[str, Any],
               snapshot_at: str, as_of: str) -> dict[str, dict[str, Any]]:
    from postlife.extract import benefits as B
    from postlife.site import terms

    out: dict[str, dict[str, Any]] = {}
    code_terms = {"kind": "code", "file": "src/postlife/site/terms.py"}

    # 화면 용어의 표시 이름(자료의 옛 값 → 화면 이름). 덱은 facts 의 옛 값을 이 표로 바꿔 보인다
    out["display_names"] = fact(dict(terms.DISPLAY), "자료의 값과 화면에 보일 이름(사용자 승인 용어, 2026-11-24)", as_of,
                                dict(code_terms, name="DISPLAY"))
    cats = list(sales["분류"])
    out["sales_insight_category_names"] = fact({c: terms.name(c) for c in cats},
                                               "영업 인사이트 분류의 자료 이름과 화면 이름(분류 차례)", as_of,
                                               dict(code_terms, name="DISPLAY_GROUPS['영업 인사이트 분류']"))
    out["sales_insight_by_category_display"] = fact(
        {terms.name(c): n for c, n in briefing(sales, sales["기준종형"][0]["종형ID"])["insights"]["by_category"].items()},
        "분류별 영업 인사이트 건수를 화면 이름으로(화면이 처음 여는 기준 종형, 대표 조건)", as_of,
        screen_source("기준별[기준종형[0].종형ID].브리핑[줄=마].값 와 terms.DISPLAY"))

    # 관계 그래프 자료의 노드와 엣지
    graph = json.loads((root / GRAPH).read_text(encoding="utf-8"))
    if graph.get("snapshot_at") != snapshot_at:
        raise FactsError(f"관계 그래프 자료의 자료 시각({graph.get('snapshot_at')})이 사본({snapshot_at})과 다르다. "
                         "python proto_src/graph/build_data.py 를 먼저 돌린다")
    kinds, ekinds = graph["kinds"], graph["ekinds"]
    nodes = Counter(kinds[n[1]] for n in graph["nodes"])
    edges = Counter(ekinds[e[2]] for e in graph["edges"])
    graph_src = screen_source("nodes[].1 (kinds 의 번호)", GRAPH)
    out["graph_nodes_by_kind"] = fact({k: nodes[k] for k in kinds}, "관계 그래프의 종류별 노드 수(kinds 차례)", as_of, graph_src)
    out["graph_edges_by_kind"] = fact({k: edges[k] for k in ekinds}, "관계 그래프의 종류별 엣지 수(ekinds 차례)", as_of,
                                      screen_source("edges[].2 (ekinds 의 번호)", GRAPH))
    out["graph_counts"] = fact({"nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "node_kinds": len(kinds),
                                "edge_kinds": len(ekinds)}, "관계 그래프의 노드 수, 엣지 수, 노드 종류 수, 엣지 종류 수", as_of,
                               screen_source("nodes, edges, kinds, ekinds 의 길이", GRAPH))
    if "보장 대분류" not in nodes:
        raise FactsError("관계 그래프에 보장 대분류 노드가 없다")
    out["coverage_major_class_count"] = fact(nodes["보장 대분류"], "보장 대분류 수(관계 그래프의 보장 대분류 노드)", as_of, graph_src)
    # 회사 노드에는 업계 공통, 감독기관, 시장 동향에 나온 회사도 있다. 계층(회사 → 종형)의 회사는 종형과 판매 엣지로 이어진 노드만 센다
    sell = ekinds.index("판매")
    sellers = sorted({e[0] for e in graph["edges"] if e[2] == sell and kinds[graph["nodes"][e[0]][1]] == "회사"
                      and kinds[graph["nodes"][e[1]][1]] == "종형"})
    out["graph_company_nodes_with_variants"] = fact(
        {"count": len(sellers), "names": [graph["nodes"][i][2] for i in sellers]},
        "관계 그래프에서 종형과 판매 엣지로 이어진 회사 노드(계층의 맨 위)의 수와 이름", as_of,
        screen_source("edges[] 가운데 판매 엣지의 회사 쪽 노드", GRAPH),
        "graph_nodes_by_kind.회사 는 업계 공통, 금융위원회, 시장 동향에 나온 회사까지 센 값이라 계층의 회사 수로 쓰지 않습니다. "
        "특약 노드 수(graph_nodes_by_kind.특약)가 rider_count_site 보다 작은 것은 인수기준만 수집한 종형의 특약을 그래프에 싣지 않기 "
        "때문입니다(proto_src/graph/build_data.py 의 GATE_ONLY).")

    # 담보 관계의 예(넓은 담보마다 좁은 담보)
    rel = [json.loads(line) for line in (root / RELATIONS).read_text(encoding="utf-8").splitlines() if line.strip()]
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rel:
        g = groups.setdefault((r["관계"], r["넓은담보ID"]), {"relation": r["관계"], "broad": r["넓은담보"], "narrow": []})
        g["narrow"].append(r["좁은담보"])
    out["coverage_relation_examples"] = fact(
        {kind: [g for g in groups.values() if g["relation"] == kind] for kind in ("포함", "통합")},
        "담보 관계를 넓은 담보마다 묶은 것(포함: 넓은 담보가 좁은 담보를 포함, 통합: 좁은 담보들이 넓은 담보 하나를 채움)", as_of,
        {"kind": "seed", "file": RELATIONS.as_posix(), "method": "관계와 넓은담보ID 로 묶어 좁은담보를 행 차례대로"})

    # 암 수술비 예(화면이 처음 여는 기준 종형의 담보 비교 행. 칸의 대표 급부 r 을 그대로 읽는다)
    first = sales["기준종형"][0]["종형ID"]
    base = cover["b"][first]
    row = next((r for r in base["rows"] if r[0] == EXAMPLE_STD), None)
    if row is None:
        raise FactsError(f"담보 비교 자료에 {EXAMPLE_STD} 행이 없다")
    std_name = sales["표준담보"][EXAMPLE_STD]["이름"]
    per_org: dict[str, Any] = {}
    for vid, cell in zip(base["cols"], row[1]):
        ben = cover_cell_benefit(cover, cell)
        if ben is None:
            raise FactsError(f"{EXAMPLE_STD}: {vid} 칸에 대표 급부가 없다")
        name, _rid, _role, pay, basis, ratio, wait, reduce, _limit, _exc, doc, page, *_rest = ben
        org = sales["종형"][vid]["기관코드"]
        per_org[org] = {"variant": sales["종형"][vid]["종형명"], "benefit": name, "pay_manwon": pay, "basis_manwon": basis,
                        "pay_is_ratio": bool(ratio), "waiting_days": wait,
                        "reduce": [{"months": m, "rate": p} for m, p in reduce], "doc_kind": doc, "doc_page": page,
                        "pay_form": ben[15]}
    pairs = {sales["종형"][vid]["기관코드"]: {"items": [{"item": it[0], "ours": it[1], "peer": it[2], "verdict": terms.name(it[3])}
                                                     for it in p["it"]],
                                           "excluded": bool(p.get("x"))}
             for vid, p in row[2].items()}
    names = sales["표준담보"]

    def held(cell: Any) -> bool:
        return isinstance(cell, dict) and bool(cell.get("i"))

    missing = [names[sid]["이름"] for sid, cells, *_ in base["rows"]
               if names[sid]["급부유형"] == "치료" and not held(cells[0]) and all(held(c) for c in cells[1:])]
    cover_src = screen_source(f"b[기준종형[0].종형ID].rows[{EXAMPLE_STD}] 의 칸마다 대표 급부(r)와 비교쌍(it)", COVER)
    out["example_cancer_surgery"] = fact(
        {"standard_coverage": std_name, "standard_coverage_id": EXAMPLE_STD, "orgs": per_org, "pairs": pairs,
         "missing_treatment_both_peers": {"count": len(missing), "names": missing}},
        "암 수술비 예: 화면이 처음 여는 기준 종형의 담보 비교 행에서 회사마다 대표 급부의 이름, 지급액, 기준 가입금액, 면책, 감액, "
        "근거 문서와 쪽, 비교쌍의 항목별 비교 결과. 그리고 치료 단계에서 우체국에 없고 두 타사가 모두 가진 담보", as_of, cover_src,
        "pay_is_ratio 가 참이면 pay_manwon 은 가입금액 대비 비율(%)입니다. 기준 가입금액이 회사마다 달라 금액만으로 우열을 말하지 않습니다.")
    out["example_cancer_surgery_names"] = fact({org: v["benefit"] for org, v in per_org.items()},
                                               "암 수술비 예의 회사별 급부 이름(원문 급부명 그대로)", as_of, cover_src)

    # 나눈 특약과 통합 특약의 예(뇌·심장질환 수술비). 화면이 처음 여는 기준 종형의 담보 비교 행을 읽는다
    by_id = {r[0]: r for r in base["rows"]}
    for sid in (EXAMPLE_SPLIT_BROAD, *EXAMPLE_SPLIT_NARROW):
        if sid not in by_id:
            raise FactsError(f"담보 비교 자료에 {sid} 행이 없다")
    rel_kinds = {(r["넓은담보ID"], r["좁은담보ID"]): r["관계"] for r in rel}
    kinds_found = {rel_kinds.get((EXAMPLE_SPLIT_BROAD, n)) for n in EXAMPLE_SPLIT_NARROW}
    if len(kinds_found) != 1 or None in kinds_found:
        raise FactsError(f"{EXAMPLE_SPLIT_BROAD} 와 좁은 담보의 관계가 표준담보 관계 자료에 하나로 있지 않다: {kinds_found}")

    def ben_view(cell: Any, where: str) -> dict[str, Any]:
        ben = cover_cell_benefit(cover, cell)
        if ben is None:
            raise FactsError(f"{where}: 대표 급부가 없다")
        return {"benefit": ben[0], "rider": cover["rid"][ben[1]][0], "doc_kind": ben[10], "doc_page": ben[11]}

    def verdicts(sid: str) -> dict[str, str]:
        return {org: terms.name(k) for k, orgs_ in base["판정기관코드"][sid].items() for org in orgs_}

    narrow = []
    for sid in EXAMPLE_SPLIT_NARROW:
        v = ben_view(by_id[sid][1][0], f"{sid} 우체국 칸")
        narrow.append(dict(v, id=sid, name=names[sid]["이름"], verdicts=verdicts(sid)))
    ours_broad = by_id[EXAMPLE_SPLIT_BROAD][1][0]
    if not (isinstance(ours_broad, dict) and ours_broad.get("c") and not ours_broad.get("i")):
        raise FactsError(f"{EXAMPLE_SPLIT_BROAD}: 우체국 칸이 관계 담보로 덮는 칸이 아니다")
    peers = {}
    for vid, cell in zip(base["cols"][1:], by_id[EXAMPLE_SPLIT_BROAD][1][1:]):
        peers[sales["종형"][vid]["기관코드"]] = dict(ben_view(cell, f"{EXAMPLE_SPLIT_BROAD} {vid} 칸"),
                                                    variant=sales["종형"][vid]["종형명"])
    out["example_split_rider"] = fact(
        {"broad": {"id": EXAMPLE_SPLIT_BROAD, "name": names[EXAMPLE_SPLIT_BROAD]["이름"], "verdicts": verdicts(EXAMPLE_SPLIT_BROAD),
                   "ours_cover": ours_broad["c"][0]},
         "relation": kinds_found.pop(), "narrow": narrow, "peers": peers, "ours_variant": sales["종형"][first]["종형명"]},
        "나눈 특약과 통합 특약의 예: 우체국은 좁은 담보 둘(narrow)을 특약 둘로, 타사는 넓은 담보(broad) 하나로 가진 경우. "
        "칸마다 대표 급부의 원문 이름, 특약 이름, 근거 문서와 쪽, 담보마다 타사별 비교 결과(화면 이름). ours_cover 는 넓은 담보 행의 "
        "우체국 칸이 관계 담보로 덮는 종류(부분 담보)", as_of,
        screen_source(f"b[기준종형[0].종형ID].rows[{EXAMPLE_SPLIT_BROAD}, {', '.join(EXAMPLE_SPLIT_NARROW)}] 의 대표 급부(r), "
                      "rid, 판정기관코드", COVER),
        "관계는 data/seed/표준담보_관계.jsonl 의 행입니다. 화면 기준 종형(화면이 처음 여는 것)에서 센 값입니다.")

    # 관계가 있어 "관련 담보로 보장"으로 보이는 비교 건(관계가 없으면 그 타사에 담보가 없어 우체국 단독 보유로 보였을 것)
    covered = [(sid, org) for sid, *_ in base["rows"] for org in base["판정기관코드"][sid].get("관계 담보로 덮음", [])]
    out["relation_covered_pairs"] = fact(
        {"pairs": len(covered), "coverages": len({s for s, _ in covered}),
         "names": list(dict.fromkeys(names[s]["이름"] for s, _ in covered)),
         "by_org": dict(Counter(org for _, org in covered))},
        "기준 종형의 담보 비교에서 비교 결과가 관련 담보로 보장(우체국은 그 담보를 가졌고 타사는 넓은 담보나 부분 담보로 보장)인 "
        "비교 건 수(담보와 타사의 짝), 담보 수와 이름, 타사별 수(화면이 처음 여는 기준 종형)", as_of,
        screen_source("b[기준종형[0].종형ID].판정기관코드[표준담보ID]['관계 담보로 덮음']", COVER),
        "담보 관계 자료가 없으면 이 타사 칸에는 그 담보가 없어 우체국 단독 보유로 셉니다(API.md 의 쌍판정 절).")
    out["coverage_major_class_names"] = fact(
        [n[2] for n in graph["nodes"] if kinds[n[1]] == "보장 대분류"], "보장 대분류의 이름(관계 그래프 노드 차례)", as_of, graph_src)

    # AI 가 옮긴 글자를 코드가 숫자로 읽는 예. 추출 기록은 저장소에 없어 추출 지시문의 예시 글자를 실제 코드로 읽는다
    src_text = (root / "src" / "postlife" / "extract" / "benefits.py").read_text(encoding="utf-8")
    if TEXT_EXAMPLE_QUOTE not in src_text:
        raise FactsError("benefits.py 지시문에서 감액 예시 글자를 찾지 못했다")
    ep = per_org.get("EPOST")
    out["example_text_to_number"] = fact(
        {"source": "지시문 예시", "text": TEXT_EXAMPLE,
         "read": {"pay_manwon": whole(B.parse_money(TEXT_EXAMPLE["amount"])),
                  "reduced_manwon": whole(B.parse_money(TEXT_EXAMPLE["reduced_amount"])),
                  "reduce_months": B.parse_months(TEXT_EXAMPLE["reduced_period"])},
         "epost_row": {"benefit": ep["benefit"], "pay_manwon": ep["pay_manwon"], "basis_manwon": ep["basis_manwon"],
                       "reduce": ep["reduce"], "doc_kind": ep["doc_kind"], "doc_page": ep["doc_page"]}},
        "AI 가 원문 글자로 옮긴 금액과 감액 기간을 코드가 숫자로 읽는 예. text 는 추출 지시문의 예시 글자이고 read 는 "
        "extract/benefits.py 의 parse_money, parse_months 가 읽은 값. epost_row 는 우체국 암 수술비 행에서 코드가 읽어 둔 값", as_of,
        {"kind": "code", "file": "src/postlife/extract/benefits.py", "name": "parse_money, parse_months (지시문 예시 글자)"},
        "추출 기록(원문 글자)은 저장소에 없어 지시문 예시를 썼습니다. 화면에는 \"지시문 예시\"라고 밝혀 씁니다.")

    # 6개월 전 입원 고객 예(고객군별 가입 가능 현황의 입원 3개월~1년 전 행, 대표 조건 나이가 든 열)
    m = sales["지도"]["전체"]
    age = sales["기준조건"]["나이"]
    col = next((i for i, c in enumerate(m["열"]) if c["lo"] <= age <= c["hi"]), None)
    rows = {r["이름"]: i for i, r in enumerate(m["행"])}
    if col is None or EXAMPLE_GATE_ROW not in rows or EXAMPLE_GATE_ROW_LATER not in rows:
        raise FactsError("고객군 지도에서 6개월 전 입원 예의 칸을 찾지 못했다")

    def cell_view(row_name: str) -> dict[str, Any]:
        x = m["칸"][rows[row_name]][col]
        only = [{"org": g["기관코드"], "variant": sales["종형"][g["종형ID"]]["종형명"],
                 "simple_type": sales["종형"][g["종형ID"]]["간편고지약칭"], "note": g.get("안내")} for g in x.get("관문만수집") or []]
        return {"row": row_name, "column": f"{m['열'][col]['lo']}~{m['열'][col]['hi']}세", "label": terms.name(x["라벨"]),
                "sub": x.get("보조") or None, "orgs": {org: terms.name(st) for org, st in x["회사"].items()}, "gate_only": only}

    out["example_gate_6months"] = fact(
        {"age": age, "sex": sales["기준조건"]["성별"], "cell": cell_view(EXAMPLE_GATE_ROW), "later": cell_view(EXAMPLE_GATE_ROW_LATER)},
        "6개월 전 입원 고객 예: 대표 조건 나이의 고객군 칸(입원 3개월~1년 전)과 1년 반 전 입원 칸(입원 1~2년 전)의 회사별 가입 가능 여부. "
        "라벨과 상태는 화면 이름(terms.DISPLAY)으로 바꿔 실었다", as_of,
        screen_source(f"지도.전체.칸[{EXAMPLE_GATE_ROW}, {EXAMPLE_GATE_ROW_LATER}][나이 열].회사, 라벨, 관문만수집"))

    # 담보 매핑 자동 확정의 두 경로(확률 산정 결과가 있는 줄, 교차 검증으로 확정해 확률이 빈 줄)
    def routes(orgs: tuple[str, ...] | None) -> dict[str, int]:
        snap = Snapshot(tables)
        auto = [r for r in tables["hum_담보매핑"] if r["검토상태"] == "자동확정" and r["급부ID"] in snap.benefit
                and (orgs is None or snap.org_of_benefit(r["급부ID"]) in orgs)]
        with_p = sum(1 for r in auto if r.get("매핑확률") is not None)
        return {"total": len(auto), "decision_model": with_p, "cross_check": len(auto) - with_p}

    out["mapping_auto_confirm_by_route"] = fact(
        {"all": routes(None), "site": routes(tuple(config.SITE_ORGS))},
        "자동 확정 매핑을 경로로 나눈 수: 확률 산정 결과가 있는 줄(decision_model)과 두 판독 일치로 확정해 확률이 빈 줄(cross_check). "
        "all 은 모든 기관, site 는 화면에 올린 기관", as_of,
        snap_source("hum_담보매핑.jsonl", "검토상태가 자동확정인 행을 매핑확률이 있는지로 나눔(급부가 있는 줄)"))

    # 검증 기준선 보정: 검수 구간에 남은 비율(재추출 구간 비율과 자동 확정 0건에서 계산)
    doc_values = {k: v for k, v, *_ in DOC_FACTS}
    caught_pct = doc_values["calibration_reextract_band"]["wrong_caught_pct"]
    if doc_values["calibration_flipped_rows"]["passed"] != 0:
        raise FactsError("자동 확정을 통과한 줄이 0이 아니면 검수 구간 비율의 계산을 다시 본다")
    out["calibration_review_band_pct"] = fact(
        round(100 - caught_pct, 1),
        "일부러 틀리게 바꾼 줄 가운데 사람 검수 구간(0.40 이상 0.75 미만)에 남은 비율(%). 100에서 재추출 구간 비율을 뺀 계산값(자동 확정 0줄)", as_of,
        derived_source(["calibration_reextract_band", "calibration_flipped_rows"], "100 - wrong_caught_pct (passed 가 0)"),
        "문서에 적힌 값이 아니라 계산값입니다. 화면에는 \"계산값\"이라고 밝힙니다.")

    # 배치 일정(워크플로 cron)
    out["schedule_collect_kst"] = fact(kst_schedule(root, "collect.yml"), "시장 동향 수집 일정(한국 시간)", as_of,
                                       {"kind": "config", "file": (WORKFLOWS / "collect.yml").as_posix(), "name": "on.schedule.cron"})
    out["schedule_weekly_close_kst"] = fact(kst_schedule(root, "weekly-close.yml"), "주간 마감과 스냅샷 일정(한국 시간)", as_of,
                                            {"kind": "config", "file": (WORKFLOWS / "weekly-close.yml").as_posix(),
                                             "name": "on.schedule.cron"})

    # 요청서 수(Antigravity 와 제미나이에 넘긴 지시문 파일. 부록은 본문과 한 건)
    reqs = sorted(p.name for p in (root / REQUESTS).glob("*.md") if re.match(r"\d", p.name) and "부록" not in p.name)
    out["request_doc_count"] = fact(len(reqs), "docs/gemini_requests 의 요청서 수(번호가 붙은 파일, 부록은 본문과 한 건으로 셈)", as_of,
                                    repo_source(REQUESTS.as_posix(), "숫자로 시작하는 .md 파일 가운데 이름에 부록이 없는 것"))
    # 요청서를 받은 쪽으로 나눈 수(파일 이름의 끝). 이름 끝이 없는 것은 Claude Code 로 옮기기 전후에 제미나이(웹, 구독 패널)에 넘긴 요청문
    by_to = {"antigravity": sum(1 for n in reqs if n.endswith("_Antigravity.md")),
             "browser_agent": sum(1 for n in reqs if n.endswith("_브라우저에이전트.md"))}
    by_to["gemini_web_or_panel"] = len(reqs) - by_to["antigravity"] - by_to["browser_agent"]
    out["request_docs_by_recipient"] = fact(
        by_to, "요청서를 받은 쪽으로 나눈 수: Antigravity 지시문, 브라우저 에이전트 점검, 제미나이(웹과 구독 패널) 요청문", as_of,
        repo_source(REQUESTS.as_posix(), "request_doc_count 의 파일을 이름 끝(_Antigravity, _브라우저에이전트, 그 밖)으로 나눔"),
        "합계는 request_doc_count 입니다. 브라우저 에이전트 점검도 사용자 PC의 Antigravity 에 붙여 넣은 것이고(README), 제미나이 요청문에는 "
        "Claude Code 로 옮기기 전 대화 세션에서 쓴 것이 섞여 있습니다.")

    # 데모 화면(시안 4)의 탭. 자료 탭 다섯(sales.json 의 탭, 화면 이름으로)과 관계 그래프 탭
    tabs = [terms.name(t) for t in sales["탭"]] + [terms.TAB_GRAPH]
    out["console4_tabs"] = fact({"count": len(tabs), "names": tabs}, "데모 화면(시안 4)의 탭 수와 탭 이름(화면 이름, 탭 차례)", as_of,
                                dict(code_terms, name="DISPLAY_GROUPS['탭'] 과 TAB_GRAPH (sales.json 탭 차례)"),
                                "site_screen_count 는 옛 운영 화면(초기 버전, site/v1/index.html)의 화면 수라 이 값과 다릅니다. "
                                "응대 화법 미리 보기는 탭이 아니라 영업 인사이트 탭 안의 패널입니다.")

    # 워크플로를 시작하는 방법으로 나눔(예약 실행, 푸시, 사람만). 워크플로의 name 으로 적는다
    trig: dict[str, list[str]] = {"scheduled": [], "on_push": [], "manual_only": []}
    for wf in sorted((root / WORKFLOWS).glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        name_m = re.search(r"^name:\s*(.+?)\s*$", text, re.M)
        on_m = re.search(r"^on:\s*\n((?:[ \t]+.*\n|\s*\n)+)", text, re.M)
        if not name_m or not on_m:
            raise FactsError(f"{wf.name}: name 이나 on 을 읽지 못했다")
        keys = set(re.findall(r"^  ([a-z_]+):", on_m.group(1), re.M))
        group = "scheduled" if "schedule" in keys else ("on_push" if keys & {"push", "pull_request"} else "manual_only")
        trig[group].append(name_m.group(1))
    out["workflow_triggers"] = fact(trig, "GitHub Actions 워크플로를 시작하는 방법으로 나눈 이름: 예약 실행, 푸시(시험, 배포), 사람이 실행", as_of,
                                    repo_source(WORKFLOWS.as_posix(), "워크플로마다 on 의 열쇠(schedule, push, pull_request, workflow_dispatch)"),
                                    "예약 실행은 시장 동향 수집과 주간 마감(스냅샷 커밋)뿐이고, 공시 문서 수집, 추출, 매핑은 사람이 실행합니다. "
                                    "화면 배포는 site/ 에 푸시할 때 돌고, 화면 빌드는 사람이 합니다.")

    # 확률 산정 문항 예: 면책기간 문항의 보기(0.94, 0.06 을 잰 문항)
    from postlife.extract import verify as V
    verify_text = (root / "src" / "postlife" / "extract" / "verify.py").read_text(encoding="utf-8")
    if "'○○보장개시일 이후'라는 조건이 들어 있는가" not in verify_text:
        raise FactsError("verify.py 의 면책기간 문항 글이 바뀌었다")
    out["symmetric_choice_item"] = fact(
        {"item": "면책기간", "question": "급부의 지급사유에 '○○보장개시일 이후' 조건이 들어 있는가", "choices": [V.AFTER_START, V.FROM_DAY_ONE]},
        "symmetric_choice_probability 를 측정한 확률 산정 문항: 문항 이름, 묻는 말(줄임), 보기 둘", as_of,
        {"kind": "code", "file": "src/postlife/extract/verify.py", "name": "checks() 의 면책기간일수 문항, AFTER_START, FROM_DAY_ONE"},
        "묻는 말은 문항 지시문을 줄인 것입니다. 0.94 와 0.06 은 이 문항 한 가지의 값입니다.")

    # 발표 영상의 길이(덱의 영상 장 길이 칩). 정지 화면을 뽑은 렌더 기록을 읽는다. 영상을 다시 렌더하면 기록도 함께 바꾼다
    timing_path = root / VIDEO_TIMINGS
    if timing_path.exists():
        videos = json.loads(timing_path.read_text(encoding="utf-8"))["videos"]
        secs = {part: int(round(v["seconds"])) for part, v in sorted(videos.items())}
        timing_src = repo_source(VIDEO_TIMINGS.as_posix(), "videos.<part>.seconds 를 반올림")
        out["video_seconds"] = fact(secs, "발표 영상(part1~part4)의 길이(초, 반올림)", as_of, timing_src)
        out["video_length_label"] = fact({p: (f"{s // 60}분 {s % 60}초" if s % 60 else f"{s // 60}분") if s >= 60 else f"{s}초"
                                          for p, s in secs.items()},
                                         "발표 영상의 길이를 화면에 적는 글(분과 초)", as_of, timing_src)
    return out


# ---------------------------------------------------------------------------
def build(root: Path = ROOT) -> dict[str, Any]:
    meta = json.loads((root / SNAPSHOT / "meta.json").read_text(encoding="utf-8"))
    snapshot_at = meta["snapshot_at"]
    as_of = snapshot_at[:10]
    sales = json.loads((root / SALES).read_text(encoding="utf-8"))
    if sales.get("자료시각") != snapshot_at:
        raise FactsError(f"화면 자료의 자료 시각({sales.get('자료시각')})이 사본({snapshot_at})과 다르다. "
                         "python scripts/export_app_data.py 를 먼저 돌린다")
    cover = json.loads((root / COVER).read_text(encoding="utf-8"))
    if cover.get("t") != snapshot_at:
        raise FactsError(f"담보 비교 자료의 자료 시각({cover.get('t')})이 사본({snapshot_at})과 다르다. "
                         "python scripts/export_app_data.py 를 먼저 돌린다")
    tables = read_snapshot(root / SNAPSHOT)
    facts: dict[str, dict[str, Any]] = {}
    facts["snapshot_at"] = fact(snapshot_at, "자료 기준 시각(사본을 뜬 시각)", as_of, {"kind": "snapshot", "file": (SNAPSHOT / "meta.json").as_posix(),
                                                                          "method": "snapshot_at"})
    for part in (snapshot_facts(root, tables, as_of), config_facts(as_of), screen_facts(sales, as_of), cover_facts(sales, cover, as_of),
                 doc_facts(root), deck_facts(root, tables, sales, cover, snapshot_at, as_of)):
        dup = set(part) & set(facts)
        if dup:
            raise FactsError(f"열쇠가 겹친다: {sorted(dup)}")
        facts.update(part)
    for key, value, label, as_of_manual, note in MANUAL_FACTS:
        facts[key] = fact(value, label, as_of_manual, {"kind": "manual"}, note)
    # 정밀 비교 대상(목표) 가운데 시트에 적재한 회사와 화면에 올린 회사(이름으로 맞춤)
    names = facts["org_names"]["value"]
    targets = [n for group in facts["comparison_target_names"]["value"].values() for n in group]
    sheet = [names[c] for c in facts["product_orgs"]["value"] if c in names and names[c] in targets]
    site = [names[c] for c in facts["site_orgs"]["value"] if c in names and names[c] in targets]
    facts["comparison_targets_loaded"] = fact(
        {"targets": len(targets), "sheet": len(sheet), "site": len(site), "sheet_names": sheet, "site_names": site},
        "정밀 비교 대상(목표, 우체국 제외) 가운데 시트 사본에 적재한 회사와 화면에 올린 회사", as_of,
        derived_source(["comparison_target_names", "product_orgs", "site_orgs", "org_names"],
                       "comparison_target_names 의 이름과 org_names 로 바꾼 product_orgs, site_orgs 의 이름이 같은 것"),
        "목표는 생명보험 10곳, 손해보험 9곳이고 지금 화면은 우체국과 그 가운데 site 의 회사만 보입니다.")
    bad = [k for k in facts if not re.fullmatch(r"[a-z][a-z0-9_]*", k)]
    if bad:
        raise FactsError(f"열쇠는 영문 소문자 스네이크 표기여야 한다: {bad}")
    return {"format": FORMAT, "about": ABOUT, "as_of_rule": AS_OF_RULE, "snapshot_at": snapshot_at, "facts": facts}


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=ROOT / OUT, help="쓸 파일")
    p.add_argument("--check", action="store_true", help="쓰지 않고, 다시 만든 것이 --out 과 다르면 1로 끝낸다")
    args = p.parse_args()
    try:
        text = render(build(ROOT))
    except FactsError as e:
        print(f"멈춤: {e}", file=sys.stderr)
        return 2
    if args.check:
        same = args.out.exists() and args.out.read_text(encoding="utf-8") == text
        print("같음" if same else f"다름: {args.out} 를 다시 만든다(python scripts/export_presentation_facts.py)")
        return 0 if same else 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    n = len(json.loads(text)["facts"])
    print(f"{args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}: 항목 {n}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
