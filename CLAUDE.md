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
- 위임할 수 있는 일은 제미나이에 위임하고(교차 확인을 겸한다), 병렬로 할 수 있는 일은 서브에이전트로 나눈다. 최종 검수는 직접 한다: 위임 결과는 원문과 대조하고, 서브에이전트 결과는 시험·재현으로 확인한 뒤에만 커밋한다.

## 절대 하지 말 것

- 이 저장소는 공개 저장소다. API 키, 서비스 계정 키, OAuth 비밀값, 스프레드시트 ID, 사용자 실명을 파일·커밋·문서 어디에도 쓰지 않는다. 키는 환경변수(`GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `SPREADSHEET_ID`)로만 넘긴다.
- 공시 문서 원본(PDF)과 원문 글자 파일을 커밋하지 않는다. 저장소 밖 작업 폴더에 둔다.
- 이미 시트에 있는 ID(종형ID·특약ID·특약계보키·급부ID·조건행ID·제약ID)를 바꾸는 수정을 하지 않는다. `hum_담보매핑`이 급부ID로 이어져 있다. `src/postlife/ids.py`를 고치면 `data/snapshot/` 전 행에서 전후 ID가 같은지 확인한다.
- 시험 출력을 `| head`·`| tail`로 가린 채 커밋하지 않는다. 통과 수를 눈으로 확인하고 커밋한다.

## 자주 쓰는 명령

```bash
python3 -m pytest -q                         # 전체 시험
python3 scripts/build_site.py                # data/snapshot → site/index.html
python3 scripts/dev/check_site_browser.py site/index.html <사진 폴더>   # 380px·1280px 화면 점검 (playwright)
python3 scripts/score_goldset.py             # 정답셋 채점
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
