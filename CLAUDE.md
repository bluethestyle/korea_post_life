# 작업 지침 (Claude Code용)

우체국보험 상품·청약 판단 지원 앱. AI 도구·에이전트 활용 공모전 제출용이다. 공시 문서(상품요약서·사업방법서)에서 급부와 가입조건을 뽑아 Google Sheets(정본)에 쓰고, 그 스냅샷으로 오프라인 단일 HTML 화면을 만든다.

처음 이어받을 때는 `docs/handoff.md`를 먼저 읽는다. 설계는 `docs/planning.md`, 지금까지 한 일과 결정 이유는 `docs/progress.md`에 있다.

## 사용자와 일하는 방식

- 답변과 문서는 항상 한국어. 번역투("~됨" 식 압축, 직역 용어)를 쓰지 않고 실무에서 쓰는 말로 쓴다.
- 묻지 말고 끝까지 진행하고, 사용자가 직접 해야 할 일만 따로 알린다.
- 조사한 수치·사실에는 출처를 단다.
- 묻지 않은 문서·스키마를 임의로 고치지 않는다. 스키마(`src/postlife/schema.py`, `docs/planning.md`) 변경은 사용자 승인 후에만 한다.
- 담당자 탭(`hum_담보매핑`, `hum_표준담보사전`, `hum_기준값`, `hum_표준질병군`)의 값은 사용자가 정한다. 자동 확정 기준을 바꾸거나 사전에 줄을 더하는 일은 사용자 말이 있어야 한다.
- 하지 않은 일을 한 것처럼 말하지 않는다. 뒤에서 돌리겠다고 했으면 실제로 돌린다.
- 위임할 수 있는 일은 제미나이에 적극적으로 위임한다(교차 확인을 겸한다). 서브에이전트는 꼭 필요할 때만 쓴다. 최종 관리자는 Claude다: 위임 결과는 원문과 대조하고, 서브에이전트 결과는 시험·재현으로 확인한 뒤에만 커밋한다. 자세한 기준은 아래 "제미나이와 서브에이전트 운용".

## 절대 하지 말 것

- 이 저장소는 공개 저장소다. API 키, 서비스 계정 키, OAuth 비밀값, 스프레드시트 ID, 사용자 실명을 파일·커밋·문서 어디에도 쓰지 않는다. 키는 환경변수(`GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `SPREADSHEET_ID`)로만 넘긴다.
- 공시 문서 원본(PDF)과 원문 글자 파일을 커밋하지 않는다. 프로젝트 폴더의 `local/`(gitignore 대상)에 두고, `git add -f`로 올리지 않는다. 시험 자료에도 원문을 옮기지 않는다.
- 이미 시트에 있는 ID(종형ID·특약ID·특약계보키·급부ID·조건행ID·제약ID)를 바꾸는 수정을 하지 않는다. `hum_담보매핑`이 급부ID로 이어져 있다. `src/postlife/ids.py`를 고치면 `data/snapshot/` 전 행에서 전후 ID가 같은지 확인한다.
- 시험 출력을 `| head`·`| tail`로 가린 채 커밋하지 않는다. 통과 수를 눈으로 확인하고 커밋한다.

## 제미나이와 서브에이전트 운용

아끼는 대상은 메인 세션이 쓰는 최상위 모델(Fable)의 사용량이다. 주간 한도 전체는 넉넉하지만 최상위 모델 한도가 빠듯하다. 그래서 메인 세션은 지휘와 검수에 쓰고, 넘길지 망설여지는 일은 제미나이에, 리포에서 실행이 필요한 구현과 점검은 모델을 낮춰 지정한 서브에이전트에 넘긴다. 메인 세션이 큰 파일을 직접 읽거나 긴 글을 직접 쓰는 일을 줄인다.

역할 나눔

| 누가 | 맡는 일 |
| --- | --- |
| Claude (메인 세션) | 작업 순서와 범위 결정, 구현, 시험과 재현으로 하는 최종 검수, 커밋 |
| 제미나이 (구독 패널, `gemini-sub` 스킬) | 웹 검색으로 하는 자료 조사와 수집, 의견 제시(설계안과 구성안, 코드 검토), 단순 작업(문서 대조, 정답셋 만들기, 표 구조화, 글 초안) |
| 서브에이전트 (모델 명시) | 제미나이가 할 수 없는 일: 리포를 고치는 구현과 수정, 시험과 스크립트 실행, 화면 점검 |

제미나이에 넘길 때

- 패널의 제미나이는 git 제외 파일(`local/`)을 읽지 못하고, 스크립트 실행, 파일 내려받기, 리포 수정을 못 한다. 원문이 필요하면 필요한 쪽만 질문 파일에 스크립트로 붙인다. 질문 파일은 리포 밖 임시 폴더에 쓴다.
- 답이 짧고 기계로 뽑아 쓸 수 있는 꼴이 되게 질문을 짠다: 번호를 붙여 "빠짐없이, 순서대로, 표 하나만", 자료에 없으면 "확인 필요". 한 번에 한 주제만 넘긴다(`docs/handoff.md` 6절의 요령).
- 답은 그대로 믿지 않는다. 근거 문구와 숫자가 원문의 그 쪽에 있는지 기계로 대조하고, 코드 지적은 재현되는 것만 고친다.
- 최종 검수자는 Claude다. 제미나이의 지적과 제안은 Claude가 직접 확인해(실행해 재현, 해당 코드나 원문을 직접 읽음, 공식 출처를 직접 조회) 동의한 것만 반영한다. 확인하지 못한 것은 반영하지 않고 "미확인"으로 남기고, 동의하지 않는 것은 이유를 적고 기각한다. 보고에는 건별로 동의한 근거를 적는다.
- 질문마다 사용자가 패널에 직접 입력해야 답이 온다. 다음 질문 파일을 미리 만들어 두어 기다리는 시간을 줄인다.

서브에이전트를 띄울 때

- 모델을 항상 명시한다(Agent 도구, Workflow의 agent() 모두). 지정하지 않으면 메인 모델을 물려받아 가장 비싸게 돈다.

| 역할 | 모델 | 맡는 일 |
| --- | --- | --- |
| 수행 | opus | 코드 구현과 수정, 문서 초안, 깊이 읽어야 하는 코드 분석 |
| 점검 | sonnet | 규격과 정합성 검증, 지적에 대한 반박 검증, 기계적 탐색, 실행과 시험 확인 |
| 기계 점검 | haiku | 결과를 기계로 검증할 수 있는 일(grep, 파일 존재, 수치 일치, 목록 만들기) |

- 값이 정해진 기계적 수정은 에이전트 없이 직접 한다. 쉬운 단계는 추론 강도(effort)를 낮추고, 작은 점검 여럿은 호출 하나로 모은다(호출 하나의 바닥 비용이 크다).
- 점검은 확실한 결함만 보고하게 한다. 코드 결함은 실행 근거(실패하는 시험, 재현 명령과 출력)가 붙은 것만 받는다.
- 수정과 재시도는 새 에이전트에 맡기고, 원래 지시와 추가 지시와 직전 보고를 함께 적는다. 같은 파일을 두 에이전트가 동시에 고치지 않게 범위를 나눈다.
- 에이전트의 완료 보고를 그대로 옮기지 않는다. diff와 산출 파일을 직접 열어 확인하고, 커밋 전 전체 시험은 메인 세션이 돌린다.
- 같은 지시문으로 다섯 이상 띄울 때는 한 건을 먼저 끝까지 돌려 본다. 중단 뒤에는 디스크의 산출물을 다시 판정해 끝난 것은 건너뛴다.

## 자주 쓰는 명령

```bash
# 시스템 파이썬에 pip이 없는 PC에서는: uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt pdfplumber playwright
python3 -m pytest -q                         # 전체 시험
python3 scripts/fetch_disclosure.py --org samsungfire --out <폴더>   # 삼성화재 문서와 급부 표 조각 받기 (--list-only는 목록만)
python3 scripts/build_site.py                # data/snapshot → site/index.html
python3 scripts/dev/check_site_browser.py site/index.html <사진 폴더>   # 380px·1280px 화면 점검 (playwright)
python3 scripts/score_goldset.py --result <상품명에 든 글자>=<결과 JSON>   # 정답셋 채점 (--result는 필수)
python3 scripts/compare_table_rules.py <표 조각.json> --against data/crosscheck/<파일>.jsonl   # 삼성화재 규칙 추출 대조

# 배치는 GitHub Actions에서 돈다 (시트 쓰기 포함)
gh api -X POST repos/bluethestyle/korea_post_life/actions/workflows/extract.yml/dispatches \
  -f ref=main -f 'inputs[org]=hanwha'                     # 급부+가입조건
gh api -X POST .../workflows/extract.yml/dispatches -f ref=main -f 'inputs[org]=epost' -f 'inputs[parts]=급부'
gh api -X POST .../workflows/map.yml/dispatches -f ref=main -F 'inputs[prune]=true'
gh run list --limit 5 ; gh run view <id> --log ; gh run download <id> -n <artifact> -D <폴더>
```

## 구조에서 꼭 알 것

- 모델은 글자만 옮기고, 숫자는 코드가 읽는다. 원문 대조(코드) → 판정 모델 확률 → 확정(0.75 이상)/검토/재추출(0.40 미만). 재추출은 보조 모델, 그다음 상위 모델. 그래도 안 되면 제외(시트에 쓰지 않음).
- Gemini 무료 한도: 추출 `gemini-3.5-flash-lite` 하루 500회, 상위 `gemini-3.8-flash` 하루 20회, 판정 `gemini-decision-1`. 하루 한도는 **한국 시간 17시**에 풀린다. 배치를 돌리기 전에 로컬 시험 호출로 상위 모델 한도를 쓰지 않는다.
- 시트 쓰기는 RAW, 머리글이 스키마와 글자 그대로 같아야 한다. 열을 더할 때는 `scripts/add_column.py`.
- 회사별 문서 꼴이 다르다. 우체국·한화는 모델 추출(`extract/benefits.py`, `pipeline.py`), 삼성화재는 PDF 표를 읽어(`extract/tables.py`) 문구 규칙으로 뽑는다(`extract/table_rules.py`). 회사별 주의점은 `docs/handoff.md`.
- 화면은 오프라인 단독 HTML 하나(`site/index.html`)다. 외부 요청이 없어야 하고, 잘리거나 겹치는 글자가 없어야 한다. 고친 뒤에는 브라우저 점검을 돌린다.

## 커밋

한국어로, 무엇을 왜 바꿨는지 적는다. 생성물(`data/snapshot/*`, `site/index.html`)이 충돌하면 손으로 합치지 말고 다시 만든다.
