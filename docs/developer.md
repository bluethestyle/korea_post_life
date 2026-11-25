# 개발자를 위한 안내

저장소의 구조, 구현한 것, 실행 방법, 자동 실행 일정을 모은 문서입니다. 이 도구가 무엇을 하는지는 [README](../README.md)에, 기획 전문은 [planning.md](planning.md)에, 공모전 제출 설명은 [submission.md](submission.md)에 있습니다. 명령은 모두 저장소 루트에서 실행합니다.

## 구조

| 구성 요소 | 위치 | 역할 |
| --- | --- | --- |
| 마스터 데이터, 담당자 검토 | 구글 시트 (탭 13개) | 서비스 계정으로 읽고 씁니다 |
| 코드, 기획 문서, 주간 스냅샷 | 이 저장소 | 스냅샷의 커밋 이력이 곧 개정 이력입니다 |
| 시장 소식 수집, 주간 마감 | GitHub Actions | 매일 소량 수집, 일요일 마감 |
| 공시 문서 수집과 추출 | GitHub Actions (수동 실행) | 우체국과 한화생명은 모델 추출과 검증을 거쳐 시트에 쓰고, 삼성화재는 급부 표를 코드 규칙으로 읽어 급부와 주계약 가입조건을 시트에 씁니다. 메리츠화재, 삼성생명, KB라이프생명, 교보생명, 현대해상은 두 모델이 따로 읽은 검증 결과 파일(`data/crosscheck/`)로 적재합니다(`scripts/load_reader_product.py`) |
| 분석 화면 (제출 데모) | `site/proto/console4.html` (원본 `proto_src/console4/`), [공개 주소](https://bluethestyle.github.io/korea_post_life/proto/console4.html) | 탭 6개(전체 요약, 고객군과 시장, 인수기준 비교, 담보 비교, 영업 인사이트, 관계 그래프)와 영업 인사이트 탭 안의 응대 화법 A4 패널. 자료와 CSS, JS, 글꼴을 모두 담은 HTML 한 파일이라 오프라인에서 열어도 동작합니다 |
| 발표 덱 | `site/deck/index.html` (원본 `proto_src/deck/`), [공개 주소](https://bluethestyle.github.io/korea_post_life/deck/) | 발표 슬라이드 26장. 숫자는 사실 자료(`presentation_animation/facts.json`)에서 읽습니다 |
| 관계 그래프 화면 | `site/proto/graph2.html` (원본 `proto_src/graph/`), [공개 주소](https://bluethestyle.github.io/korea_post_life/proto/graph2.html) | 회사, 종형, 특약, 급부, 표준담보의 연결을 따라가는 단독 화면 |
| 초기 버전 | `site/v1/index.html`, [공개 주소](https://bluethestyle.github.io/korea_post_life/v1/) | 처음 만든 판단 화면. 화면 6개, 해설 글, 응대 카드 |
| 안내 화면 | `site/index.html`, [공개 주소](https://bluethestyle.github.io/korea_post_life/) | 위 네 화면으로 가는 링크만 있는 루트 화면. GitHub Pages에는 `site/` 폴더 전체를 배포합니다 |

## 지금 상태 (2026-11-25)

| 항목 | 상태 |
| --- | --- |
| 시트 (화면에 올린 세 회사) | 상품종형 23(우체국 8, 한화생명 8, 삼성화재 7, 역할별로는 정밀비교 16, 관문전용 4, 직전개정시연 3), 특약 2,747(우체국 166, 한화생명 856, 삼성화재 1,725), 급부 6,615(우체국 383, 한화생명 3,585, 삼성화재 2,647), 가입조건 832(우체국 594, 한화생명 220, 삼성화재 18)와 결합 제약 79(우체국), 표준담보 87(사용 86), 담보 매핑 6,615, 시장 동향 26, 작업로그 13,975행 |
| 시트 전체 | 화면에 올리지 않은 메리츠화재, 삼성생명, KB라이프생명까지 여섯 회사. 상품종형 47, 특약 4,021, 급부 9,100, 가입조건 994, 담보 매핑 8,134, 작업로그 15,964행. 교보생명과 현대해상은 검증 결과 파일까지 만들었고 시트에는 아직 넣지 않았습니다 |
| 우체국 | 3개 상품의 급부, 가입조건, 결합 제약, 담보 매핑을 마쳤고 정답셋을 통과했습니다 |
| 한화생명 | 급부 1,420행 추출(확정 1,306, 사람 검토 67, 제외 47). 스냅샷에는 시그니처 H통합보험 8종(정밀비교 4, 관문전용 4), 급부 3,585행, 주계약 가입조건 220행 적재 |
| 삼성화재 | 표 추출기와 규칙 추출기를 만들고 문서 수집을 연결했습니다. 규칙 추출 결과를 제미나이의 독립 구조화와 줄마다 대조해 THE FIT 339줄 중 337줄, 새로고침 342줄 중 334줄 일치. 가입조건과 결합 제약도 제미나이가 따로 구조화해 대조 자료로 두었습니다(`data/crosscheck/`). 스냅샷에 3개 상품 7종, 특약 1,725행, 급부 2,647행, 주계약 가입조건 18행을 적재했고 특약 가입조건은 적재 전 |
| 테스트와 점검 | 테스트 1,515개 통과. 분석 화면은 다섯 해상도(1920x1080부터 380x780까지)에서 스크린샷과 측정값으로 점검하고(`proto_src/console4/shoot.py`), 초기 버전은 380px와 1280px 폭에서 점검합니다(`scripts/dev/check_site_browser.py`) |
| 남은 일 | 삼성화재 특약 가입조건과 결합 제약 시트 연결(급부 2,647행, 주계약 가입조건, 새로고침 8종은 적재 완료), 시트에 넣은 다른 회사를 화면에 올리는 일, 지난주 스냅샷과 비교한 우열 변화 |

지금 화면은 2026-11-24 14:29 스냅샷(화면에 올린 세 회사, 종형 23개, 급부 6,615행)으로 빌드했습니다. 알려진 한계는 [docs/limitations.md](limitations.md), 경과와 수치는 [docs/progress.md](progress.md), 인계 상태는 [docs/handoff.md](handoff.md)에 있습니다.

## AI 도구를 쓴 방식

앱 안에서는 추출 모델이 원문 글자만 옮기고, 숫자 계산과 원문 대조는 코드가, 채점은 글을 쓰지 않고 확률만 매기는 판정 전용 모델(`gemini-decision-1`)이 맡습니다. 개발에서는 Claude Code가 작업 순서, 구현, 테스트와 재현으로 하는 최종 검수를 맡고, 정답셋 만들기와 독립 구조화, 코드 검토 같은 교차 확인은 제미나이에, 구현과 점검 일부는 모델을 지정한 서브에이전트에 넘겼습니다. 화면의 구현과 개선은 사용자 PC의 Antigravity(Gemini 에이전트)가 브랜치와 PR로 넘기고, Claude가 재현으로 검수해 머지했습니다. 위임 결과는 원문 대조와 시험으로 확인한 것만 반영했습니다. 정답셋은 `data/goldset/`, 교차 확인 자료는 `data/crosscheck/`에 있고, 자세한 방식은 [docs/submission.md](submission.md)와 [CLAUDE.md](../CLAUDE.md)에 있습니다.

## 지금까지 구현한 것

| 파일 (모듈은 `src/postlife/` 기준) | 내용 |
| --- | --- |
| `schema.py` | 시트 탭 13개의 열 정의. 기획 문서 5.5와 같은지 테스트가 대조 |
| `ids.py` | 다시 추출해도 바뀌지 않는 ID, 개정 전후를 잇는 계보키 |
| `sheets_io.py` | 시트 읽기와 쓰기. 종형 단위 부분 교체, 누적 탭 덧붙이기 |
| `kcd.py` | 질병코드 구간 비교 (세 자리 끝코드가 세부코드를 포함) |
| `validate.py` | 시트에 쓰기 전에 코드가 먼저 보는 자료형, 허용값, 논리 점검 |
| `worklog.py` | 단계별 통과, 반려, 보류 기록(`sys_작업로그`) |
| `snapshot.py` | 시트 마스터 데이터를 정렬된 JSON Lines 스냅샷으로 저장 |
| `gemini.py` | 생성, 검색 그라운딩, 판정 전용 모델 호출 |
| `collect.py` | 시장 소식 수집: 검색 → 정형화 → 날짜 확인 → 선별과 분류 → 중복 병합 → 기록 |
| `config.py` | 시장 동향 수집 대상 19개 기관, 기관 이름표 22곳, 화면에 올릴 회사(`SITE_ORGS`, 지금은 우체국, 한화생명, 삼성화재), 요일별 수집 계획, 모델 배정 |
| `disclosure/epost.py` | 우체국보험 공시실: 화면이 보내는 요청을 따라 목록과 서류 받기 |
| `disclosure/hanwha.py` | 한화생명 상품공시실: 폼 요청으로 목록과 서류 받기 |
| `disclosure/samsungfire.py` | 삼성화재 상품공시: 목록 요청 한 번으로 전 상품과 서류 경로 받기 |
| `disclosure/<회사>.py` | 그 밖의 회사 공시실 접속 모듈(우체국 포함 19개 회사). 공시실 접속 세션은 `disclosure/http.py`, 수집 스크립트가 회사별 모듈을 찾는 자리는 `disclosure/sources.py` |
| `extract/benefits.py` | 특약 조각에서 급부 추출. 금액과 기간은 원문 글자로 받고 숫자는 코드가 계산 |
| `extract/verify.py` | 판정 전용 모델로 추출값을 원문과 대조 |
| `extract/conditions.py` | 사업방법서에서 가입나이, 보험기간, 납입기간, 가입금액 한도와 결합 제약 추출 |
| `extract/job.py` | 문서 묶음 하나를 종형, 특약, 급부, 가입조건 순으로 시트에 반영 |
| `extract/mapping.py` | 급부를 표준담보 사전에 잇기 (`hum_담보매핑`) |
| `extract/tables.py` | 삼성화재 요약서의 급부 표를 PDF에서 직접 읽어 특약 단위로 자르기 |
| `extract/table_rules.py` | 삼성화재 표 문구를 모델 없이 코드 규칙으로 읽기. 읽지 못한 형태는 "확신 없음" |
| `site/console4.py` | 분석 화면이 읽는 자료(영업 인사이트, 인수기준, 담보 비교, 비교 자료)를 스냅샷에서 한 번에 만들기 |
| `site/insights.py`, `site/sales.py` | 기준 종형을 타사 종형과 비교해 규칙으로 뽑는 시사점, 그것을 영업 인사이트 분류와 문장으로 옮기기. 금지어가 든 문장은 빌드에서 막음 |
| `site/relations.py` | 표준담보 사이의 관계(포함, 통합)와 다른 종형의 보유 담보로 덮이는지 판단 |
| `site/lineup.py` | 분석 화면이 읽는 간편심사 세 등급의 회사별 비교 자료 |
| `site/orgs.py`, `site/terms.py` | 화면에 올릴 회사만 거르기, 화면에 내는 용어(표시 이름) |
| `site/build.py` | 초기 버전: 스냅샷으로 외부 주소를 부르지 않는 HTML 한 파일 만들기 |
| `site/weekly.py` | 초기 버전 화면 1: 이번 주 달라진 점 |
| `site/eligibility.py` | 초기 버전 화면 2: 가입 적격과 간편심사 고지 관문 |
| `site/compare.py` | 초기 버전 화면 3: 표준담보별 비교표 |
| `site/combo.py` | 초기 버전 화면 4: 특약 조합별 실제 지급액 |
| `site/revision.py` | 초기 버전 화면 5: 개정 전후 비교 |
| `site/worklog.py` | 초기 버전 화면 6: AI 작업 내역 |
| `site/commentary.py` | 초기 버전의 화면별 해설 글 검사. 변수 밖에 숫자가 있는 글은 빌드에서 제외 |
| `site/card.py` | 초기 버전의 응대 카드: 화면 3에서 고른 두 종형을 A4 세로 한 장으로 인쇄 |
| `scripts/fetch_disclosure.py` | 공시 문서 받기와 글자 뽑기. 삼성화재는 급부 표 조각 JSON까지 |
| `scripts/extract_product.py` | 추출, 검증, 시트 쓰기 실행 (`extract.yml`에서 실행) |
| `scripts/load_reader_product.py`, `scripts/load_reader_conditions.py` | 두 모델의 검증 결과 파일로 급부와 주계약 가입조건을 시트에 쓰기 (`extract.yml`에서 실행) |
| `scripts/apply_mapping_opinion.py` | 두 모델의 표준담보 의견 파일을 `hum_담보매핑`에 반영 (`apply-opinion.yml`에서 실행) |
| `scripts/export_app_data.py` | `data/snapshot/`으로 분석 화면 자료(`proto_src/console4/`) 만들기 |
| `scripts/export_presentation_facts.py` | 발표 덱과 영상이 읽는 사실 자료 `presentation_animation/facts.json` 만들기 |
| `scripts/build_site.py` | `data/snapshot/`으로 초기 버전 `site/v1/index.html` 만들기 |

## 시장 소식 수집 흐름

1. 검색: `gemini-2.5-flash-lite`에 검색 그라운딩을 붙여 그날 요일의 기관을 조회합니다. 질의에는 "최근" 같은 말 대신 날짜를 적습니다.
2. 정형화: `gemini-3.5-flash-lite`가 검색 결과를 발행일, 기관, 요약, 출처 번호로 정리합니다.
3. 코드 확인: 발행일이 수집 구간 밖이거나 출처가 없는 건을 코드가 버립니다.
4. 선별과 분류: 판정 전용 모델 `gemini-decision-1`이 대상 소식인지(확률)와 일곱 분류 중 어디인지를 가립니다. 글을 쓰지 않고 확률만 돌려주는 모델입니다.
5. 중복 병합: 같은 기관 안에서 주소나 요약이 거의 같으면 코드가, 표현이 다르면 판정 모델이 같은 사건인지 가립니다.
6. 기록: 소식은 `sys_시장동향`에, 단계별 통과, 반려, 보류는 `sys_작업로그`에 남깁니다. 화면에는 선별 확률이 통과 기준을 넘은 소식만 내고, 그 아래는 검토 대기로 보여 줍니다.

2026-11-18 테스트 실행(질의 1건)에서 검색 모델이 돌려준 6건 가운데 5건이 수집 구간 밖이어서 코드가 버렸고, 1건이 선별 확률 0.96으로 기록 대상이 됐습니다.

## 급부 추출과 검증

공시 문서에서 종형, 특약, 급부와 가입조건, 결합 제약을 뽑아 시트에 쓰는 흐름입니다. Actions의 `extract.yml`이 회사를 골라 실행합니다. 우체국과 한화생명은 아래 흐름으로 모델이 추출하고, 삼성화재는 표 규칙으로, 메리츠화재, 삼성생명, KB라이프생명, 교보생명, 현대해상은 두 모델의 검증 결과 파일로 씁니다.

1. 상품요약서를 특약 단위로 자르고(한화생명은 가입유형별 표까지 나눕니다), 추출 모델이 급부 줄을 만듭니다. 금액, 감액 기간, 보장개시일은 원문 글자로 받고 숫자는 코드가 계산합니다.
2. 코드 대조: 금액과 기간 글자가 원문에 그대로 있는지, 값끼리 앞뒤가 맞는지 봅니다.
3. 판정: 판정 전용 모델이 줄마다 지급액, 감액, 보장개시일 조건, 지급 한도에 확률을 매깁니다.
4. 0.75 이상은 확정, 0.40 이상 0.75 미만은 시트에 쓰되 사람 검토로 넘기고, 0.40 미만은 다른 모델로, 그래도 어긋나면 상위 모델로 다시 뽑습니다. 그래도 0.40 미만이면 시트에 쓰지 않습니다.
5. 가입조건과 결합 제약은 사업방법서에서 같은 방식으로 뽑습니다. 단계마다 `sys_작업로그`에 남기고, 문서에 없는 값은 만들지 않고 사람 검토로 넘깁니다. 시트에 쓴 급부는 `map.yml`이 표준담보 사전에 잇습니다.

삼성화재는 담보 수백 개가 표 하나에 이어져 있어 PDF 표를 직접 읽고, 문구가 규칙적이라 모델 없이 코드 규칙으로 뽑습니다(급부와 주계약 가입조건은 시트에 연결했고 특약 가입조건은 연결 전). 우체국 요약서 2건에서 뽑은 급부 101줄을 원문과 대조해 모두 맞는 것을 확인했고, 그 줄을 일부러 틀리게 바꾼 437줄로 확정 경계를 맞췄습니다(0.75에서 틀린 줄 통과 0건). 한화생명 정답셋의 보장금액, 면책, 감액 14항목도 모두 맞았습니다. 자세한 수치는 `docs/progress.md`에 있습니다.

## 실행

```bash
pip install -r requirements.txt pdfplumber playwright   # pdfplumber는 공시 문서 수집과 화면 점검, playwright는 화면 점검에 씁니다
python -m playwright install chromium
pytest -q

# 시트 없이 흐름만 확인 (검색 1회, 정형화 1회, 판정 몇 회 호출)
export GEMINI_API_KEY=...        # 파일에 적지 않습니다
python scripts/collect_trends.py --dry-run --max-queries 1

python scripts/extract_benefits.py --text <요약서 글자 파일> --variant V1 --out out.json   # 추출과 검증만 (시트에 쓰지 않습니다)
python scripts/score_goldset.py --result 간편한건강보험=out.json                # 정답셋 채점
python scripts/calibrate_verify.py --pair <요약서 글자 파일> out.json --out calib.json   # 판정 경계 다시 재기

python scripts/fetch_disclosure.py --org samsungfire --out <폴더>   # 삼성화재 문서와 급부 표 조각 (키 불필요, --list-only는 목록만)
python scripts/export_app_data.py                                    # 분석 화면 자료: data/snapshot → proto_src/console4
python proto_src/console4/build.py                                   # 분석 화면 빌드: proto_src/console4 → site/proto/console4.html
python proto_src/console4/shoot.py <사진 폴더>                        # 분석 화면 여러 해상도 점검
python scripts/export_presentation_facts.py                          # 발표 사실 자료: presentation_animation/facts.json
python proto_src/deck/build.py --out site/deck/index.html --used proto_src/deck/facts_used.json --strict   # 발표 덱
python scripts/build_site.py                                         # 초기 버전: data/snapshot → site/v1/index.html
python scripts/dev/check_site_browser.py site/v1/index.html <사진 폴더>   # 초기 버전 380px, 1280px 폭 브라우저 점검
```

## 비밀값

저장소가 공개 상태이므로 키는 파일에 적지 않고 Actions 비밀값(Settings → Secrets and variables → Actions)에만 넣습니다. 비밀값이 없으면 예약 실행은 아무것도 하지 않고 끝납니다.

| 이름 | 내용 |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API 키 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 구글 서비스 계정 키 파일(JSON)의 내용 전체 |
| `SPREADSHEET_ID` | 마스터 시트의 ID |

시트 공유는 "제한됨"으로 두고 서비스 계정 이메일만 편집자로 추가합니다.

## 작업 흐름

| 파일 | 실행 시점 | 하는 일 |
| --- | --- | --- |
| `ci.yml` | main 푸시, PR | 테스트 실행 |
| `access-check.yml` | 수동, `scripts/check_access.py`나 이 파일이 main에서 바뀔 때 | 국내 공시실, 협회 사이트 접속 테스트 |
| `collect.yml` | 매일 06:10 (한국 시간), 수동 | 그날 요일의 기관 소식 수집. 일요일은 실패한 질의만 재수집 |
| `weekly-close.yml` | 일요일 23:40 (한국 시간), 수동 | 시트 마스터 데이터를 `data/snapshot/`에 스냅샷으로 저장하고 커밋 |
| `fetch-disclosure.yml` | 수동 (회사 선택) | 고른 회사(14곳 가운데 하나)의 공시 문서를 받아 글자를 뽑고 하루 보관. 삼성화재는 급부 표의 추출 단위(JSON)까지 |
| `extract.yml` | 수동 (회사, 공시상품코드, 실행할 부분) | 고른 회사(8곳 가운데 하나)의 문서를 받아 추출, 검증하고 시트에 기록. 메리츠화재, 삼성생명, KB라이프생명, 교보생명, 현대해상은 검증 결과 파일로 적재 |
| `map.yml` | 수동 | 급부를 표준담보 사전에 잇기. 담당자가 손댄 행은 그대로 둡니다 |
| `pages.yml` | `site/`나 이 파일이 main에서 바뀔 때, 수동 | `site/` 폴더 전체(안내 화면, 분석 화면, 발표 덱, 관계 그래프 화면, 초기 버전)를 Pages에 배포합니다. 올리기 전에 안내 화면과 초기 버전의 외부 자원을 검사합니다 |
| `probe.yml` | 수동 (주소 목록) | 공시실 화면이 문서 주소를 내려 주는 방식을 확인하는 점검 도구 |
| `apply-opinion.yml` | 수동 | 두 모델의 표준담보 의견 파일을 `hum_담보매핑`에 반영. 두 의견이 같으면 자동확정, 둘 다 해당없음이면 대상외, 다르면 대기 |
| `add-column.yml` | 수동 | 스키마에 더한 열을 시트의 머리행과 기존 행에 빈칸으로 넣고 머리글을 점검 |
| `sync-variant-attrs.yml` | 수동 | 대상 설정(`data/targets/`)에 적힌 종형의 고지 열을 시트의 기존 종형 행에 맞춤 |
| `sheet-check.yml` | 수동 | 시트를 읽기만 해서 머리글이 스키마와 같은지, 저장소의 스냅샷과 어디가 다른지 확인 |
| `after-reset.yml` | 수동 | 무료 한도가 풀린 뒤의 확인 실행(상위 모델 확인 호출, 한화 재추출 dry_run). 시트에는 쓰지 않음 |

`collect.yml`, `extract.yml`, `map.yml`은 수동 실행 때 `dry_run`을 켜면 시트에 쓰지 않습니다. 원본 PDF는 저장소에 올리지 않고 공시 문서 수집 결과물로 하루만 보관하며, 출처 링크와 추출 결과만 남깁니다.
