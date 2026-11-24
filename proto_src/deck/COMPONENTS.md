# 발표 덱 도해 부품 사용 설명서 (C1~C20, 인용, 인라인 그림)

## 실행 방법(챕터 담당자 작업 폴더)

작업 폴더는 프로젝트 폴더 안의 `local/backfill/deck_v2/work/`(git 제외 폴더)다. 구성은 `deck/`(이 폴더 전체의 복사본), `facts.json`(재생성한 사실 자료), `fonts_v4.css`(글꼴), `media/`(영상), `stills/`(영상 정지 화면)이다. `deck/build.py`는 바로 위 폴더의 `facts.json`과 `fonts_v4.css`를 기본값으로 읽는다. 파이썬은 프로젝트의 가상환경(playwright 와 Pillow 가 든 `.venv`)을 쓴다.

```bash
cd local/backfill/deck_v2/work/deck            # 프로젝트 폴더에서
PY=../../../../../.venv/bin/python             # 프로젝트의 가상환경

$PY build.py                                   # content/ 26장 → out/index.html (경고와 검토용 숫자 목록을 출력)
$PY build.py --only 7,12-14 --out out/part.html  # 7, 12, 13, 14장만(쪽 번호는 전체 기준)
$PY build.py --content-dir samples --out out/samples.html   # 부품 견본 27장(27, 28장은 디자인 시스템에서 더한 장치)
$PY build.py --facts ../facts.json --strict    # 경고가 있으면 1로 끝냄(제출 빌드)

$PY tools/shot.py 7 12-14 --out-dir shots      # 그 장들만 빌드해 shots/07.png 따위(1920x1080)로 찍고 겹침, 잘림, 작은 글자를 센다
$PY tools/shot.py all --content-dir samples --out-dir shots_samples
$PY tools/shot.py 7 --out-dir shots_tab --size 1180x820   # 태블릿 크기(창에 보이는 글자 높이 13px 미만이면 tiny)
$PY tools/check_deck.py out/index.html check  # 전 장을 1920x1080, 1366x768, 1180x820(태블릿)으로 찍고 키보드, 전체 보기, 노트, 인쇄까지 점검
$PY tools/check_glyphs.py out/index.html      # 심은 글꼴(PLKo)에 없는 글자 찾기
```

- 리포 안에서는 `python proto_src/deck/build.py --out site/deck/index.html` 이 배포본을 만들고 `facts_used.json`을 고친다(테스트가 바이트 일치를 본다).
- `build.py` 인자: `--content-dir`(장 폴더), `--deck`(덱 공통 설정, 기본은 장 폴더의 `_deck.json`, 없으면 `content/_deck.json`), `--facts`, `--refs`, `--fonts-css`, `--assets`, `--out`, `--used`, `--only`, `--strict`, `--digits`(자리 표시 밖 숫자를 모두 보기).
- 장 파일을 고친 뒤에는 `tools/shot.py`로 그 장을 찍어 직접 본다. 문제 0건이 나와야 한다.
- 작업 폴더의 `stills/`(영상 정지 화면 JPEG)는 빌드가 사진 폴더로 함께 읽는다. 장에서 `"stills": ["part1_1"]`처럼 파일 이름으로 부른다(한 컷)(덱에 심을 사진은 장당 250KB 이하).
- 영상은 HTML 옆 `media/` 에 있어야 재생된다. 작업 폴더에서는 `mkdir -p out && ln -s ../../media out/media` 로 이어 두면 `out/index.html` 빌드에 `<video>`가 들어간다. 파일이 없으면 정지 화면이나 안내 글만 보인다.
- 여러 담당자가 같은 폴더를 쓰므로, 자기 챕터의 `content/NN.json`만 고친다. `_deck.json`, `deckparts.py`, `tpl.html`을 고칠 일이 생기면 고친 내용과 이유를 따로 적어 넘긴다. 공통 파일을 고치지 않고 그림을 보태려면 인라인 그림 블록(`svg`, 2절 보조 블록)을 쓴다.

## 1. 장 파일의 형식(content/NN.json)

장마다 파일 하나다. 파일 번호와 `no`가 같아야 한다.

```json
{
 "no": 7, "id": "cancer-surgery", "kind": "body", "chapter": 2, "status": "new",
 "headline": "암 수술비 하나를 세 회사 문서에서 찾아 같은 행에 놓고 비교합니다",
 "diagram": [ {"use": "C3", "box": [0, 0, 1760, 500], "nodes": [ ... ]} ],
 "points": ["기준 가입금액이 달라 금액만으로 우열을 말하지 않습니다"],
 "terms": ["담보", "표준담보", "면책기간"],
 "source": "출처: 담보 비교 자료, 자료 기준 {{asof:example_cancer_surgery}}",
 "notes": "발표자 노트(화면에 보이지 않고 N 키로 연다)",
 "legacy": {"about": "지금 덱에서 옮겨 온 재료. 빌드는 읽지 않는다", "slides": []}
}
```

| 열쇠 | 뜻 | 상한 |
| --- | --- | --- |
| `kind` | `cover`(1장), `body`, `video`(5, 13, 16, 21장), `closing`(26장) | |
| `chapter` | 0 안내, 1~6 챕터, 7 마무리. 머리의 챕터 바(C1)가 이 값을 켠다 | |
| `status` | `kept`, `revised`, `new`, `video`, `demo`. `demo`면 헤드라인 앞에 "시연" 칩이 붙는다 | |
| `headline` | 평이한 한 문장 | 50자(공백 포함) |
| `diagram` | 부품 블록 목록. 블록마다 `use`(부품 이름)와 `box`([x, y, 폭, 높이], 도해 영역 기준 px) | 강조(hero) 한 곳, 큰 숫자 셋 |
| `points` | 요점, 한 줄에 하나 | 두 줄, 줄마다 30자 |
| `terms` | 용어 풀이 칩(C14, 22px, 띠 높이 72px)으로 보일 용어. `_deck.json`의 `glossary`에 있어야 한다 | 셋, 풀이마다 30자 |
| `source` | 꼬리말 출처 한 행(22px). `{{ref:}}`를 쓴 장은 "외부 출처: 도메인"이 자동으로 붙는다 | 한 행 폭(약 1,560px, 한글 약 73자) |
| `notes` | 발표자 노트 | 없음 |
| `footnote` | 꼬리말 바로 위의 작은 회색 각주(22px, 한두 행). 모델 이름처럼 작게만 덧붙일 글. 도해 영역이 그만큼(한 행 40px, 두 행 70px) 줄어든다 | 두 행 폭 |
| `frame.top` | 도해 영역의 위(무대 y). 정하지 않으면 헤드라인 길이(브라우저 실측에 맞춘 폭 어림)로 240 또는 320 | |
| `legacy` | 지금 덱(18장)에서 옮겨 온 재료. 빌드는 읽지 않는다. 다시 쓴 뒤 지운다 | |

글자 수는 자리 표시를 채운 뒤 화면에 보일 글자(공백 포함, 배지와 태그 제외)로 센다. 상한을 넘으면 빌드가 `[NN] 위치: 52자 > 50자` 형식으로 경고한다.

### 1.1 도해 영역과 box 좌표

무대는 1920x1080이다. 머리(챕터 바) y 44~100, 헤드라인 y 124부터, 꼬리말 y 1000부터다. 도해 영역은 가로 x 80~1840(폭 1760)이고, 세로는 헤드라인 줄 수와 아래 띠(요점, 용어 풀이)에 따라 정해진다. `box`는 이 영역의 왼쪽 위를 (0, 0)으로 잡는다. 폭이나 높이를 `null`로 두면 영역의 오른쪽 끝, 아래 끝까지다. 영역을 벗어난 box는 빌드가 경고한다. 빌드한 HTML의 `.dg` 요소에 `data-region="1760x664"`처럼 영역 크기가 적혀 있다.

| 헤드라인 | 아래 띠 없음 | 요점 1줄 | 용어 풀이 | 용어 풀이와 요점 1줄 | 용어 풀이와 요점 2줄 |
| --- | --- | --- | --- | --- | --- |
| 한 줄(영역 위 y 240) | 1760x728 | 1760x688 | 1760x656 | 1760x608 | 1760x568 |
| 두 줄(영역 위 y 320) | 1760x648 | 1760x608 | 1760x576 | 1760x528 | 1760x488 |

(2026-11-24 글자 크기 상향으로 용어 풀이 띠가 64px 에서 72px 로 높아져, 용어 풀이가 있는 장의 도해 영역이 8px 줄었다.)

헤드라인이 한 줄인지는 글자 폭 어림으로 정한다. 어림과 실제가 다르면 `tools/shot.py`가 헤드라인과 도해의 겹침을 알린다. 그때는 `frame.top`을 320으로 둔다.

표지(`kind: cover`)는 도해 영역이 무대 전체(1920x1080)이고, 왼쪽 x 128~1048에 배지, 출품작 이름(`_deck.json`의 `cover_title`, 없으면 `app_name`), 부제(장의 `subtitle`, 없으면 `_deck.json`의 `cover_subtitle`, 40자), 리드(헤드라인), 메타가 서고, 아래 y 880~1000에 챕터 바 큰 판이 자동으로 선다(`no_board: true`면 끈다). 메타는 `"meta": [{"l": "자료 기준", "v": "{{asof:snapshot_at}}"}]`(라벨 8자, 값 24자).

영상 장(`kind: video`)은 `"video": {"part": 1, "src": "media/part1.mp4", "q": "볼 곳이나 핵심 한 문장", "stills": ["part1_1"], "dur": "{{fact:video_length_label.part1}}"}`를 받는다(부품 C13). 영상 길이는 facts 의 `video_seconds`(초)와 `video_length_label`("1분 15초")이고, `assets/stills_timings.json`(정지 화면을 뽑은 렌더 기록)에서 `scripts/export_presentation_facts.py`가 만든다. 영상을 다시 렌더하면 이 기록과 정지 화면을 함께 바꾸고 facts 를 다시 만든다.

### 1.2 자리 표시

| 형식 | 채우는 값 |
| --- | --- |
| `{{fact:열쇠}}`, `{{fact:열쇠.하위키}}`, `{{fact:열쇠.0}}` | `facts.json`의 값. 정수는 천 단위 쉼표, 목록은 쉼표로 이음 |
| `{{fact:열쇠\|f1}}`, `\|f2`, `\|pct` | 실수를 소수 첫째, 둘째 자리로, `pct`는 0.5 → 50 |
| `{{len:열쇠}}`, `{{asof:열쇠}}` | 목록이나 사전의 길이, 그 값의 기준일 |
| `{{ref:열쇠}}`, `{{ref:열쇠.하위키}}` | `refs.json`의 외부 사실. `kind`가 `press`면 값 뒤에 "보도 기준" 배지가 붙고, 꼬리말에 출처 도메인이 붙는다 |
| `{{todo:내용}}` | 글 안의 확인 필요 표시(점선 상자) |
| `{{name:열쇠}}` | `_deck.json`의 `names`에 적은 도구와 모델 이름(Claude Code, Antigravity, Gemini 구독 패널, Opus, Sonnet, Haiku, GitHub). 여러 장이 같은 철자를 쓰게 한다 |
| `[[용어]]` | 점선 밑줄(풀이는 `terms`로 아래 띠에) |
| `<b>`, `<br>`, `<u>`(빨강 밑줄), `<u class="g">`(회색 밑줄), `<span class="red">` | 그대로 HTML |

없는 열쇠나 하위키가 하나라도 있으면 빌드가 멈춘다. 숫자는 손으로 적지 않는다. 빌드가 자리 표시 밖의 숫자를 "검토용"으로 보여 준다.

### 1.3 덱 공통 설정(content/_deck.json)

`app_name`(머리 왼쪽의 출품작 이름), `html_title`, `cover_title`(표지의 출품작 이름, `<br>`로 줄을 나눔), `cover_subtitle`(표지 부제), `chapters`(번호, 짧은 이름, 질문), `steps`(일곱 단계의 이름, 한 문장, 아이콘), `weekly_after`와 `weekly_label`(④→⑤ 화살표 라벨), `lane_roles`(단계마다 일하는 역할, C2 회색 미리 보기), `panel_heads`(C6 머리글 셋), `orgs`(회사 칩: 이름과 스타일 `epost`, `peer1`, `peer2`), `demo`(데모 버튼), `names`(`{{name:열쇠}}`로 부르는 도구와 모델 이름), `glossary`(용어 풀이 표). 용어 풀이 표는 구성안 1.2절의 표를 30자 안으로 줄인 것이다.

### 1.4 공통 규칙

- 강조는 블록이나 노드의 `"hero": true`로 한 장에 한 곳. 둘 이상이면 경고. C7의 `big`, C16의 합계, C17의 목 라벨은 기본이 강조다(`"hero": false`나 `"hero": "none"`으로 끈다).
- 큰 숫자(C10, C11, C7의 big, C16 합계)는 한 장에 셋 이하.
- 글자 크기(2026-11-24 상향, 1920x1080 무대 기준): 내용을 전하는 글(본문 라벨, 표의 값, 도해의 라벨, 요점)은 26px 이상, 보조 글(축 눈금, 꼬리말의 출처, 각주, 용어 풀이, 칩과 배지, 범례, 쪽 번호, 작은 회색 한 줄 note 와 scope)은 22px 이상, 슬라이드 안에 22px 미만 글자는 두지 않는다. 헤드라인(64px)과 큰 숫자는 그대로다. 부품의 CSS(`tpl.html`)가 이미 맞춰 두었고, 보조 글로 치는 클래스 목록은 `tools/shot.py`의 `AUX`에 있다. `tools/shot.py`가 어긋난 곳을 알린다(small: 22px 미만, label: 내용 글이 26px 미만, 태블릿 크기 `--size 1180x820`에서는 tiny: 창에 보이는 글자 높이 13px 미만).
- 글자가 커져 넘치면 글자를 줄이지 않고 글을 줄이거나 항목을 줄이거나 도해를 나눈다. 부품의 글자 수 상한은 새 크기에 맞춰 줄였다(아래 부품마다의 상한). 항목마다 `limit`을 올려 상한을 피하지 않는다(상자가 넓을 때만 쓴다).
- 아이콘: 한 장에 6개 이하(장 파일이 놓은 `icon`과 인라인 그림의 아이콘. 일곱 단계 구조도 C2 와 역할 칩 C20 은 세지 않는다). 넘으면 빌드가 경고한다. 아이콘 옆에는 늘 글자를 둔다(아이콘만으로 뜻을 전하지 않는다).

## 2. 부품

입력 예의 숫자는 모두 사실 자료 자리로 적는다. 아래 예는 `samples/`의 견본 장(파일 번호가 구성안의 장 번호)에서 옮겼다. 견본은 `$PY tools/shot.py all --content-dir samples`로 찍어 볼 수 있다.

### C1 챕터 바

- 머리: 장의 `chapter`로 자동. 번호 원 여섯(지금 원만 빨강, 번호 22px), 지금 질문(22px). 영상 장은 어두운 변형.
- 큰 판(표지 자동): `{"use": "C1", "mode": "board"}`. 여섯 질문을 가로로(26px).
- 답 판(26장): `{"use": "C1", "mode": "answers", "answers": [{"n": 1, "a": "차이는 수백 쪽 문서 속 문장에 있습니다", "ref": [2]}]}`. 행 높이 최대 90. 근거 장은 짧게 적는다(`[22, 23, 24]` → "22~24장", `[14, 17]` → "14, 17장").
- 상한: 질문 18자(`_deck.json`), 답 40자. 쓰는 장: 1(큰 판), 2~25(머리), 26(답 판).

### C2 일곱 단계 구조도

```json
{"use": "C2", "mode": "full", "roles_preview": true, "bracket": {"from": 6, "to": 7, "label": "결과물: 지점 창구와 설계사에게 전달"}}
{"use": "C2", "mode": "mini", "on": [3]}
{"use": "C2", "mode": "tiny", "on": [2, 3]}
{"use": "C2", "mode": "lanes", "lanes": {"AI": [{"step": 2, "label": "글자 옮기기"}], "코드": [{"step": 3, "label": "원문 대조"}], "사람": [{"step": 4, "label": "기준값 정하기"}]}}
```

- `full`: 상자 일곱(아이콘, 이름 28px, 한 문장 26px)과 화살표, ④→⑤ 위 "매주 스냅샷". `on`은 위치 강조(빨강 테두리), `bracket`은 빨강 괄호, `roles_preview`는 상자 아래 회색 역할 아이콘. 높이 300 이상 권장.
- `mini`: 칩 일곱(높이 44). 열 머리나 마무리 장의 지도로.
- `tiny`: 번호 원 일곱(번호 22px)과 켠 단계의 이름(22px). 패널 안 미니(높이 64).
- `mini` 칩과 `lanes` 칩의 글자는 26px. `lanes`: 칩 머리 아래 AI, 코드, 사람 레인(C20). 한 레인의 한 단계에 칩 하나(칩이 좁아 두 줄로 접힐 수 있다).
- 상한: 단계 이름 8자, 한 문장 24자, 괄호 라벨 24자, 레인 칩 9자. 쓰는 장: 4(full), 12(lanes), 14, 18, 19(tiny), 26(mini).

### C3 흐름 화살표

```json
{"use": "C3", "dir": "h", "nodes": [
  {"num": "1", "label": "찾기", "sub": "요약서 {{fact:example_cancer_surgery.orgs.EPOST.doc_page}}쪽", "icon": "search"},
  {"num": "2", "label": "맞추기", "figure": {"use": "C9", "layout": "converge", "cards": [{"org": "EPOST"}], "target": {"label": "암 수술비"}}, "fig_h": 220},
  {"label": "비교", "icon": "table", "hero": true}]}
{"use": "C3", "nodes": [{"label": "들어오는 자료"}], "branch": {"at": 1, "label": "양이 많은가", "hero": true,
  "up_label": "적음", "down_label": "많음", "up": [{"label": "매주 새 자료"}], "down": [{"label": "기존 상품 첫 적재"}]}}
```

- 노드 2~7개(분기 없을 때). `dir`은 `h`(가로)나 `v`(세로). 노드 안에 아이콘(`icon`, C18 이름) 또는 다른 부품(`figure`와 높이 `fig_h`)을 넣는다. `"compact": true`면 아이콘이 48px.
- 카드 묶음: `"arrows": false`면 화살표 없이 같은 크기의 회색 카드로 놓는다(순서가 없는 묶음. 아이콘과 라벨, 보조 글. 보조 글 상한 40자). `"joiner": "또는"`이면 화살표 자리에 그 글을 둔다(서로 대안인 경로). `sub_limit`로 보조 글 상한을 바꾼다. `"align": "top"`이면 노드 안 내용을 위에서부터 놓아, 아래 글의 줄 수가 달라도 번호와 아이콘의 높이가 카드끼리 맞는다.
- 분기: `at` 번째 노드 다음에 마름모, 오른쪽에 위 경로와 아래 경로.
- 라벨 28px, 보조 글 26px. 노드의 `note`는 보조 글 아래 작은 회색 한 줄(22px). 단계마다 쓰는 모델 이름처럼 작게만 덧붙일 글(예: `"note": "{{fact:models.extract}}"`).
- 상한: 라벨 18자, 보조 22자(카드 묶음 36자), 번호 4자, 마름모 8자, 분기 라벨 6자, 노트 26자. 쓰는 장: 1(세로), 7, 11, 12, 18(분기), 23, 25.

### C4 회사 3열 비교

```json
{"use": "C4", "head": "간편심사 고지사항: 같은 질문도 회사마다 다릅니다", "cols": ["EPOST", "HANWHALIFE", "SAMSUNGFIRE"], "label_w": 200,
 "rows": [{"label": "묻는 병력", "limit": 20, "values": ["{{fact:simple_uw_questions_by_org.EPOST.period_question}}", "입원 또는 <u>수술</u>(제왕절개 포함)", "입원 또는 <u>수술</u>"]},
          {"label": "면책기간", "same": true, "values": ["{{fact:example_cancer_surgery.orgs.EPOST.waiting_days}}일"]},
          {"label": "지급액", "values": ["...", "...", "..."], "chip": {"col": 2, "text": "금액으로 비교하지 않음"}, "hero": true}],
 "tag": "세 상품 가운데 우체국만 수술 이력을 묻지 않습니다"}
{"use": "C4", "mode": "result", "cond": "예: 50세 남성, 입원 3개월~1년 전",
 "rows": [{"org": "EPOST", "state": "closed", "text": "일반심사 대상"}, {"org": "HANWHALIFE", "state": "open", "text": "간편심사 유형 3.0.5로 가입", "hero": true}],
 "note": "입원 1~2년 전이면 함께 가입 가능"}
```

- 같은 값은 `same`으로 한 칸에 합치고 회색 "동일" 알약(화면 용어 terms.DISPLAY 를 따름, `same_label`로 바꿈). 알약 글자는 22px(보조 글). 행 라벨, 결과 글, 꼬리표는 26px, 값은 28px. `chip`은 그 열의 칸에 비교 보류 칩. 값 안의 `<u>`는 빨강 밑줄.
- 결과 칩 변형: 가입 가능은 채운 원, 가입 제한은 빈 원에 사선(색만으로 구분하지 않음).
- 상한: 머리 30자, 행 라벨 9자, 값 18자(행마다 `limit`으로 바꿈), 비교 보류 칩 12자, 꼬리표 36자, 조건 칩 22자, 결과 글 20자, 결과 아래 글 30자. 쓰는 장: 2, 7, 8.

### C5 전후 비교

```json
{"use": "C5", "labels": ["겪은 일", "세운 기준"], "rows": [{"before": "...", "after": "...", "tag": "...", "hero": true}]}
{"use": "C5", "orientation": "v", "labels": ["고민", "방향"], "rows": [{"before": "...", "after": "...", "icon": "a4"}]}
{"use": "C5", "labels": ["지금까지", "이 도구로"],
 "before_merged": {"text": "수백 쪽 공시 문서를 사람이 손으로 대조", "icon": "stack", "todo": "걸리는 시간과 방법: 확인 후 채움"},
 "badgeCol": {"label": "효과", "badge": "측정 전", "note": "실무자 사용검증으로 잽니다"},
 "rows": [{"head": "경쟁사 비교 보고", "after": "근거 문서와 쪽수가 붙은 비교표 복사", "hero": true}]}
```

- 가로형(기본): 왼쪽 회색 카드, 화살표, 오른쪽 위 빨강 선 카드. 행 1~4. `head`가 있으면 행 머리 열, `before_merged`는 왼쪽 칸을 행 전부에 걸쳐 하나로, `badgeCol`은 오른쪽 배지 열(C15 측정 전). `badgeCol.once`가 참이면 행마다 배지를 되풀이하지 않고 오른쪽 열 머리에 `label`과 배지 하나만 둔다(배지 열은 없앰). 강조(`hero`)가 아닌 카드의 윗선은 짙은 회색이고, 빨강은 강조 카드 하나에만 쓴다. 행은 상자 높이를 나눠 채운다(`"fill": false`면 내용 높이).
- 세로형: 열마다 위 말풍선, 아래 화살표, 아래 카드. 카드의 `icon`은 카드 오른쪽 위에 놓여 상자 높이와 상관없이 카드 안에 남는다.
- 왼쪽 칸과 행 머리 26px, 오른쪽 카드 26px, 꼬리표 22px. 행의 `note`는 꼬리표 아래 작은 회색 한 줄(22px, 가로형과 세로형 모두). 역할마다 쓴 모델 등급처럼 작게만 덧붙일 글.
- 전과 후의 대비(디자인 시스템의 대조 페어)는 이 부품으로 그린다.
- 상한: 왼쪽 28자, 오른쪽 32자, 꼬리표 28자, 행 노트 36자, 행 머리 13자, 합친 칸 28자와 확인 필요 40자, 배지 열 아래 글 36자. 쓰는 장: 3(세로), 11, 14(패널 안), 24.

### C6 기술 세 패널

```json
{"use": "C6", "panels": [
  {"figure": {"use": "C7", "size": "mini", "thresholds": ["{{fact:verify_reextract_threshold}}", "{{fact:verify_confirm_threshold}}"]},
   "chip": "객관식 채점관", "line": "질문과 보기를 정해 주면 보기마다 확률만 돌려줍니다", "src": "출처: Google Decisions API 문서"},
  {"figure": {"use": "C5", "labels": ["글로 답하는 AI", "판정 모델"], "rows": [{"before": "...", "after": "..."}]}, "line": "..."},
  {"figure": {"use": "C2", "mode": "tiny", "on": [1, 3, 4]}, "line": "..."}]}
```

- 같은 폭 패널 셋. 머리글은 `_deck.json`의 `panel_heads`("이게 무엇인가", "왜 새로운가", "우리는 어디에 썼나"). 그림 자리에 다른 부품을 넣는다(그림 높이는 패널 높이에서 머리글, 한 문장 세 줄, 칩, 출처를 뺀 값). 부품 여럿은 `"figures": [{"use": "C2", "mode": "tiny", "on": [3], "h": 72}, {"use": "C20", "dir": "v", "chips": [...]}]`처럼 세로로 쌓는다(`h`가 없는 부품은 남은 높이를 나눔).
- 상한: 한 문장 44자, 비유 칩 12자, 출처 36자. 쓰는 장: 14, 19.

### C7 확률 계기판

```json
{"use": "C7", "thresholds": ["{{fact:verify_reextract_threshold}}", "{{fact:verify_confirm_threshold}}"],
 "zones": ["다른 AI로 다시 추출", "사람이 검수", "자동 확정"],
 "stack": {"label": "일부러 오류를 넣은 값 {{fact:calibration_flipped_rows.rows}}건", "segments": [
   {"zone": 0, "pct": "{{fact:calibration_reextract_band.wrong_caught_pct}}", "text": "{{fact:calibration_reextract_band.wrong_caught_pct|f1}}%"},
   {"zone": 1, "pct": "{{fact:calibration_review_band_pct}}", "text": "{{fact:calibration_review_band_pct|f1}}%(계산값)", "computed": true}]},
 "big": {"zone": 2, "text": "{{fact:calibration_flipped_rows.passed}}건"}}
{"use": "C7", "size": "mini", "thresholds": [...], "markers": [{"v": "{{fact:symmetric_choice_probability.correct_min}}", "label": "맞게 옮긴 값", "hero": true}]}
```

- 큰 판: 위 100% 누적 막대(계산값 구간은 빗금), 가운데 큰 숫자, 아래 0~1 막대와 기준선 점선, 구간 라벨. 높이 380 이상. 누적 막대가 있으면 0~1 막대는 위에서 `gap`(기본 260)px에 놓고, 남는 높이는 위아래로 나눠 가운데에 둔다. 누적 막대 없이 구간 막대만 둘 수도 있다(높이 200이면 충분). `"tick_labels": false`면 기준선 아래 숫자(0.40, 0.75)를 감춘다.
- 미니: 막대와 점 표시(높이 60 이상).
- 구간 라벨, 누적 막대 라벨과 구간 글 26px, 미니의 라벨 22px.
- 상한: 구간 12자, 누적 막대 라벨 22자, 구간 글 11자, 큰 숫자 6자, 점 라벨 13자. 쓰는 장: 14(미니), 17(큰 판), 18(미니).

### C8 타임라인

```json
{"use": "C8", "axis": ["2026-11-18", "2026-11-19"], "bars": [{"d": "2026-11-18", "v": "{{fact:commits_by_date.2026-11-18}}"}],
 "flags": [{"d": "2026-11-20", "label": "청약에서 영업 인사이트까지 한 흐름으로", "tag": "실무자 지적", "who": "human", "hero": true}]}
{"use": "C8", "dots": [{"d": "{{ref:jev_release.date}}", "label": "판정만 하는 AI {{ref:jev_release.model}} 공개", "src": "TypeSafe AI"}]}
```

- 막대와 깃발: 날짜 축(MM-DD로 표시), 날짜별 막대와 값, 깃발 상자(층을 나눠 겹치지 않게 놓음, 같은 날 깃발은 세로선을 함께 쓰고, 위층 상자의 선은 아래층 상자의 윗변에서 멈춰 다른 상자 뒤로 지나가지 않음). `who`가 `human`이면 실무자 태그(빨강 바탕), 아니면 AI 태그. 상자 폭 `flag_w`(기본은 날짜 칸 폭의 1.4배, 200~300).
- 점 연표: 폭 700 이상이면 가로(`"alternate": true`면 위아래 번갈아), 좁으면 세로. `press: true`면 보도 기준 배지.
- 막대의 `"bar_unit": "건"`은 막대 위 숫자 뒤에 단위를 붙인다(숫자만으로는 무엇을 센 값인지 모르므로). 점의 `tag`는 점 상자 안의 작은 태그(예: "이 앱이 씀", 강조 점이면 빨강 바탕). 연표 라벨은 refs 의 `short` 하위키(34자 안)를 쓴다.
- 깃발 글, 점 날짜와 라벨, 막대 위 숫자 26px, 태그와 점 출처 22px.
- 상한: 깃발 20자, 태그 12자, 점 라벨 30자, 점 출처 20자, 점 태그 8자, 막대 단위 4자. 쓰는 장: 10(막대와 깃발), 15(점 넷), 19(패널 안 점 셋).

### C9 점과 선

```json
{"use": "C9", "layout": "org", "nodes": [{"id": "u", "tier": 0, "label": "실무자(출품자)", "sub": "방향과 결정"},
  {"id": "cc", "tier": 1, "label": "Claude Code", "sub": "지휘와 최종 검수"}, {"id": "gh", "side": true, "label": "GitHub 저장소"}],
 "edges": [{"from": "u", "to": "cc"}, {"from": "cc", "to": "gh", "label": "요청서 {{fact:request_doc_count}}건"}],
 "ring": {"node": "cc", "label": "결과는 다시 실행해 확인", "hero": true}}
{"use": "C9", "layout": "ladder", "nodes": [{"label": "급부", "count": "{{fact:graph_nodes_by_kind.급부}}"}, {"label": "표준담보", "hero": true}]}
{"use": "C9", "layout": "converge", "cards": [{"org": "EPOST", "text": "{{fact:example_cancer_surgery_names.EPOST}}"}],
 "target": {"label": "암 수술비", "sub": "표준담보"}, "chip": "자동 확정: 판정 모델 {{fact:mapping_auto_confirm_threshold|f2}} 이상 또는 AI 둘의 결과 일치"}
{"use": "C9", "layout": "legend", "captions": ["온톨로지 = 범례", "지식그래프 = 노선도"],
 "node_kinds": [{"label": "회사", "shape": "square"}], "edge_kinds": [{"label": "포함", "style": "dash"}],
 "graph": {"nodes": [{"id": "a", "label": "우체국", "shape": "square"}], "edges": [{"from": "a", "to": "c", "style": "dash"}]}}
```

- `org`: `tier` 0, 1, 2 줄과 오른쪽 `side` 열. 선은 꺾인 선과 화살표, 선 라벨은 가운데. `ring`은 노드 왼쪽을 도는 되돌림 화살표와 라벨. 노드의 `note`는 보조 글 아래 작은 회색 한 줄(22px, 26자. 모델 이름처럼 작게만 덧붙일 글).
- `converge`의 목표 노드는 작은 상자(C3 노드 안 미니)에서 높이 64 이상, 폭이 좁으면 26px 글자로 한 줄에 둔다. 카드에 `org`가 없으면 회사 칩 자리를 두지 않는다. `legend`의 미니 그래프 선은 범례와 같은 `solid`, `dash`, `dot` 셋.
- `ladder`: 세로 사슬과 오른쪽 수. `converge`: 이름 카드(회사 칩과 원문 26px, 카드마다 `limit`, 기본 50자) 셋이 오른쪽 노드 하나로 모임. `legend`: 범례 상자와 미니 그래프(점 다섯 이하, 모양 `square`, `circle`, `diamond`. 선이 모두 아래로 나가는 점은 이름을 점 위에 두어 선이 이름 글자를 지나지 않게 한다). 한 장을 크게 쓸 때는 `"size": "large"`(라벨 26px, 점과 선을 크게)와 `"legend_w": 400`(범례 상자 폭의 상한)을 준다.
- 노드 라벨, 링 라벨, 수렴 칩, 캡션 26px, 보조 글, 선 라벨, 범례 22px.
- 상한: 노드 라벨 14자, 보조 28자, 선 라벨 13자, 링 라벨 18자, 수 8자, 칩 34자, 범례 항목 8자, 캡션 14자. 쓰는 장: 7(수렴 미니), 9(조직도), 19(범례, 사다리), 20(수렴).

### C10 큰 숫자

`{"use": "C10", "value": "{{fact:hanwha_summary_pages}}", "unit": "쪽", "caption": "한화생명 상품 하나의 상품요약서", "size": "small", "hero": false}`

- 값 120px(작은 판 72px), 단위 40px, 설명 26px. `"align": "center"`면 상자 가운데에 맞춘다(구간 막대 아래에 구간마다 숫자 하나를 놓을 때). `scope`는 설명 아래 작은 회색 한 줄(22px)로 그 숫자를 잰 범위(어느 문서, 몇 건, 어떤 표본)를 적는다.
- 큰 숫자 타일(디자인 시스템의 KPI 타일): `"tile": true`면 테두리 상자에 넣고, `"icon"`(아이콘 칩)과 `"tile_label"`(이름 한 줄, 26px, 12자)을 머리에 둔다. `hero`면 빨강 면에 흰 글자. 타일 여럿을 나란히 둘 때 쓴다(큰 숫자 셋 이하 규칙은 그대로).
  `{"use": "C10", "tile": true, "icon": "담보", "tile_label": "결합 제약", "value": "{{fact:combination_constraints_by_org.EPOST}}", "unit": "건", "caption": "우체국만 적재"}`
- 상한: 값 8자, 단위 6자, 설명 20자, 범위 26자, 타일 이름 12자. 쓰는 장: 2, 6, 7, 10, 17, 18, 19, 20, 23.

### C11 링 차트

`{"use": "C11", "value": "{{fact:goldset_epost_benefit.items}}", "total": "{{fact:goldset_epost_benefit.items}}", "split": [{"v": "{{fact:goldset_epost_benefit.auto_match}}"}, {"v": "{{fact:goldset_epost_benefit.manual_match}}", "hatch": true}], "caption": "우체국 정답표(보장금액, 면책, 감액)", "legend": ["자동 일치", "직접 확인"]}`

- 큰 판 지름 280(가운데 56px), `"size": "small"`은 160. `hero`면 링이 빨강. 설명 26px. `scope`는 설명 아래 작은 회색 한 줄(22px)로 대조한 범위(어느 문서의 몇 항목)를 적는다. 범례 글에 건수를 함께 적을 수 있다(`"legend": ["자동 일치 {{fact:goldset_epost_benefit.auto_match}}", ...]`). 상한: 값과 전체 6자, 설명 22자, 범위 26자, 범례 13자. 쓰는 장: 6, 22.

### C12 화면 캡처 주석

`{"use": "C12", "img": "tab_market", "alt": "고객군과 시장 탭", "marks": [{"n": 1, "x": 0.81, "y": 0.08, "label": "조건 바꾸기"}], "caption": "..."}`

- `img`는 `assets/<이름>.jpg`의 이름(`tools/capture_app.py`가 만든 summary, tab_market, tab_gate, tab_cover, tab_insight, tab_graph, talk_preview, cancer_surgery). 사진은 덱에 한 번만 심긴다. `x`, `y`는 사진 안 비율. 번호가 있으면 오른쪽 300px 열에 라벨(26px)과 리더 선, 없으면 썸네일(가운데 맞춤). 라벨 칸은 짚는 곳의 높이 순서로 놓는다(리더 선이 엇갈리지 않게).
- 구역 짚기(디자인 시스템의 an-zone): `"zones": [{"n": "A", "x": 0.52, "y": 0.13, "w": 0.46, "h": 0.1, "label": "인쇄와 글 복사"}]`. 사진 안 비율의 상자를 빨강 테두리와 옅은 빨강 면으로 짚고, 왼쪽 위에 번호 칩을 붙인다. 점(`marks`)과 함께 쓸 수 있고, 번호는 합쳐 넷 이하. 화면의 한 영역(버튼 묶음, 표 한 칸)을 가리킬 때 점보다 낫다.
- 상한: 번호 넷(점과 구역 합계), 라벨 10자, 캡션 28자. 쓰는 장: 1(썸네일), 6(썸네일 넷), 8(큰 판).

### C13 영상 슬롯

장의 `kind: video`와 `video` 항목으로 쓴다(1.1절). 앞뒤 장과 같은 밝은 바탕에 영상 칩과 길이 칩, 헤드라인, 한 줄 요약(`q`, 청자가 영상에서 볼 곳이나 핵심 한 문장), 가운데 1280x720 어두운 영상 자리. `out/media/partN.mp4`가 있을 때만 `<video>`를 넣는다. 영상이 없거나 인쇄할 때는 정지 화면 한 컷(`stills`, assets 이름 하나)을 어둡고 흐리게 깔고 가운데에 재생 표시와 "발표 때 이 자리에서 영상이 재생됩니다"를 둔다. 정지 화면 안의 작은 글자는 화면에서 읽히지 않으므로 컷을 여럿 늘어놓지 않는다(2026-11-24 화면 점검, 두 컷 이상이면 경고). 상한: 헤드라인 50자, 질문 50자. 쓰는 장: 5, 13, 16, 21.

### C14 용어 풀이 칩

장의 `terms`로 아래 띠에 칩을 놓는다(가장 흔한 쓰임). 블록으로 둘 때는 `{"use": "C14", "terms": ["판정 모델", "확률"]}`. 풀이는 `_deck.json`의 `glossary`에서 읽는다. 본문 안 용어에는 `[[용어]]`로 점선 밑줄. 상한: 한 장에 셋, 풀이 30자. 쓰는 장: 구성안 1.2절 표의 첫 장.

### C15 플레이스홀더와 배지

`{"use": "C15", "kind": "todo", "text": "GitHub Actions 무료 범위: 공식 문서 확인 필요"}`, `{"use": "C15", "kind": "unmeasured"}`, `{"use": "C15", "kind": "press"}`

- `todo`: 빨강 점선 상자와 "확인 필요" 태그. 글 안에서는 `{{todo:내용}}`. `unmeasured`: "측정 전" 알약. `press`: "보도 기준" 알약(refs 의 press 값에는 자동으로 붙는다).
- 확인 필요 상자의 글 26px(패널 안 작은 상자 `sm` 은 22px).
- 상한: 확인 필요 50자. 쓰는 장: 3, 9, 15, 23, 24, 25.

### C16 영수증과 주간 일정

```json
{"use": "C16", "items": [{"label": "자동 실행(GitHub Actions)", "won": "{{fact:operating_cost_won}}원", "todo": "무료 범위 확인"}],
 "total": "{{fact:operating_cost_won}}원", "caption": "주간 운영의 API 비용 기준입니다",
 "week": {"daily": {"time": "{{fact:schedule_collect_kst.time}}", "label": "시장 동향 수집"},
          "sun": {"time": "{{fact:schedule_weekly_close_kst.time}}", "label": "주간 마감과 스냅샷"}, "after": "화면 빌드 → 공개 주소 갱신"}}
```

- 아래가 톱니인 영수증(폭 560)과 월~일 일곱 칸. `"part": "receipt"`나 `"week"`로 한쪽만. 합계는 기본 강조.
- `week.manual`(`{"label": "사람이 실행", "text": "공시 문서 수집, 추출, 매핑, 화면 빌드"}`)은 예약 실행이 아니라 필요할 때 사람이 실행하는 일을 셋째 범례 줄(사람 아이콘)에 적는다. 있으면 끝 화살표 글이 한 줄 아래로 내려간다.
- 항목, 범례 줄, 끝 화살표 글 26px, 메모와 확인 필요 22px.
- 상한: 항목 22자, 금액 8자, 메모 20자, 확인 필요 13자, 캡션 22자, 일정 시각 6자와 라벨 15자, 사람 실행 라벨 10자와 글 28자, 끝 화살표 글 20자. 쓰는 장: 23.

### C17 모래시계

`{"use": "C17", "top": "한화생명 검수 대기 {{fact:mapping_requery.rows}}행", "neck": "분당 {{fact:decide_per_minute_limit.tokens}} 토큰", "bottom": "다시 묻는 데 약 {{fact:mapping_requery.estimated_minutes}}분", "hero": "neck"}`

- 왼쪽 모래시계, 오른쪽 세 높이의 라벨(26px). `hero`는 `"neck"`(기본, 목 라벨 빨강)이나 `"none"`. 상한: 라벨 24자. 쓰는 장: 18.

### C18 아이콘 세트

- 블록: `{"use": "C18", "icon": "stack", "pages": "{{fact:hanwha_summary_pages}}", "scale_pages": 600, "label": "..."}`(문서 더미, 높이가 쪽수에 비례) 또는 `{"use": "C18", "icon": "monitor", "size": 64}`.
- 아이콘은 세 가지 이름으로 부른다. C3 노드의 `icon`, C5의 `icon`, C2 단계의 `icon`, C10 타일의 `icon`, 인용의 `icon`, 인라인 그림의 `{{icon:}}`에 같은 이름을 쓴다.
  1. 개념 이름(먼저 쓴다): `_deck.json`의 `icons`(덱 아이콘 사전)에 있는 개념. 공시 문서, 추출, 검증, 자동 확정, 사람 검수, 코드, 마스터 데이터, 관계 그래프, 비교 화면, 응대 화법, 스냅샷, 담보, 우체국, 계산, 연동, 비용, 일정, 기간, 걸리는 시간, 목표. 같은 개념은 덱 전체에서 같은 아이콘이 된다.
  2. 디자인 시스템 "발표용(우체국)"의 Lucide 아이콘 55종의 이름(`icons/*.svg`, 예: `file-text`, `network`, `coins`). 뜻은 디자인 시스템 사전(`reference/icons-logos.md` 5절)을 따르고, 사전에 없는 개념에 비슷한 아이콘을 빌려 쓰지 않는다. 라이선스는 `icons/LICENSE.txt`(ISC).
  3. 덱 자체 아이콘: stack, ai, code, person, search, table, monitor, a4, copy, print, camera, clock, building, video, arrow, dot, square. doc, check, graph 는 디자인 시스템 도안(file-text, badge-check, network)으로 그린다.
- 빌드는 장에서 실제로 쓴 아이콘만 스프라이트에 심는다. 모르는 이름이면 빌드가 멈춘다. 상한: 라벨 13자(26px). 쓰는 장: 전 장.

### C19 A4 미리보기

`{"use": "C19", "size": "m", "hero": true, "blocks": ["인수기준", "구성 요약", "예상 질문과 답"]}`

- 작은 판 180x254, 중간 판 300x424(상자에 맞춰 줄어듦). 폭 220 미만이면 글자(22px) 없이 회색 막대만(작은 판은 늘 막대만). 머리 표식은 "대외 배포 금지"(화면의 실제 표식 문구는 노트로). 상한: 블록 라벨 7자. 쓰는 장: 1, 6, 7.

### C20 역할 레인과 배지

C2의 `lanes`로 쓴다(칩 글자 26px). 칩만 따로 둘 때는 `{"use": "C20", "chips": [{"role": "AI", "label": "글자 옮기기"}, {"role": "코드", "label": "원문 대조"}, {"role": "사람", "label": "기준값 정하기"}]}`(`"dir": "v"`면 세로로 한 줄씩). AI 칩은 진한 바탕, 코드 칩은 테두리, 사람 칩은 회색 바탕(빨강은 쓰지 않음). 상한: 9자. 쓰는 장: 4(회색 미리 보기, C2의 roles_preview), 12.

### 보조 블록

| 블록 | 입력 | 상한 |
| --- | --- | --- |
| `text` | `{"use": "text", "text": "...", "size": "l\|m\|s", "tone": "ink\|muted\|red", "limit": 40}`(l 36px, m 28px, s 26px) | l 30자, m 40자, s 50자(`limit`로 바꿈) |
| `chip` | `{"use": "chip", "text": "...", "tone": "paper\|ink\|red", "align": "left\|center\|right"}`(26px, align 은 box 안의 가로 자리) | 30자 |
| `button` | `{"use": "button", "label": "데모 열기", "href": "../proto/console4.html"}`(생략하면 `_deck.json`의 `demo`) | 10자 |
| `links` | `{"use": "links", "items": [{"l": "데모", "v": "proto/console4.html"}]}`(라벨 22px, 값 26px) | 라벨 8자, 값 56자 |
| `quote` | 인용(디자인 시스템의 인용 슬라이드). 아래 설명 | 글 60자, 말한 사람 24자, 출처 36자 |
| `svg` | 장 파일 안에 적는 작은 인라인 그림. 아래 설명 | `<text>` 하나 24자(`limit`) |

#### 인용(quote)

```json
{"use": "quote", "box": [0, 0, 1000, 300], "kind": "gist", "text": "회사마다 필수 특약과 가입금액이 달라 같은 보장을 나란히 비교하기 어렵습니다",
 "who": "보험영업 실무자 {{fact:practice_respondents}}명", "src": "실무자 응답(사용자 전달)"}
```

- 왼쪽 빨강 세로선, 글 36px(`"size": "m"`이면 30px), 아래에 말한 사람과 출처(22px). `icon`을 주면 출처 앞에 아이콘.
- `kind`: `verbatim`(실제로 한 말을 그대로 옮김. 빨강 큰따옴표)과 `gist`(요지. "응답 요지" 칩, 기본값). 원문을 저장소에 옮기지 않은 응답(예: 실무자 응답의 4번)은 `gist`로 쓴다. 지어낸 문장을 인용처럼 싣지 않고, 말한 사람은 실명 대신 역할로 적는다. 한 덱에 한두 번만 쓴다.

#### 인라인 그림(svg)

```json
{"use": "svg", "box": [0, 340, 1760, 220], "vb": [1760, 220], "alt": "그림이 보이는 것 한 문장",
 "svg": "<rect x='0' y='20' width='520' height='180' class='sv-paper'/><use href='{{icon:공시 문서}}' x='40' y='70' width='64' height='64'/><text x='130' y='112'>회사별 문서</text>"}
```

- 공통 파일을 고치지 않고 장 파일 안에서 작은 그림(전후 대비, 단계 그림, 크기 비교, 화살표로 잇기)을 그릴 때 쓴다. `svg`는 바깥 `<svg>` 없이 도형만 적는다. 빌드가 box 크기의 `<svg viewBox="0 0 vb">`로 감싼다(`vb`를 주지 않으면 box 크기, 배율 1).
- 글자: `<text>`는 기본 26px, `class="aux"`면 22px 회색(보조 글), `class="b"` 굵게, `class="red"` 빨강. 좌표계 배율(box 폭 / vb 폭)을 곱한 화면 크기가 26px(보조 글 22px) 아래면 빌드가 경고한다. 그래서 `vb`는 box 와 같은 크기로 두는 것이 가장 쉽다. 숫자는 `<text>` 안에서도 `{{fact:}}` 자리로 적는다(빌드가 `<text>` 안의 숫자를 검토 목록에 올린다).
- 색: 클래스로 토큰 색만 쓴다. 선 `sv-ink`, `sv-red`, `sv-muted`, `sv-line`, 면 `sv-paper`, `sv-deep`, `sv-redbg`, `sv-fill-ink`, `sv-fill-red`. 화살촉은 `marker-end='url(#ah)'`(회색)과 `url(#ah-r)`(빨강). 그 밖의 색 값을 적으면 경고한다.
- 아이콘: `<use href='{{icon:개념 이름}}' x y width height/>`(위 C18 의 이름). 장의 아이콘 6개 이하에 함께 센다.
- 외부 주소(href, url()), `<script>`, `<image>`, `<a>`, `<style>`, 중첩 `<svg>`, `<foreignObject>`, 이벤트 속성(onclick 따위)은 빌드를 멈춘다. box 밖으로 나간 도형은 `tools/shot.py`가 overflow 로 알린다.
- 강조(`"hero": true`)와 등장 순서(`"build"`)는 다른 블록과 같다.

#### 블록 등장 순서(build)

어느 블록이든 `"build": 1~8`을 주면, 장이 열릴 때 그 순서로 아래에서 떠오르며 나타난다(디자인 시스템의 덱 빌드 시퀀스. 단계마다 0.32초, 같은 수는 함께, 8단계 이하). 설명 순서대로 보여 줄 때만 쓴다. 움직임 줄임 설정, 인쇄, 전체 보기, `tools/shot.py`의 캡처에서는 처음부터 모두 보인다.

## 3. 사실 자료와 외부 출처

- `facts.json`(리포의 `presentation_animation/facts.json`)은 `scripts/export_presentation_facts.py`가 만든다. 손으로 고치지 않는다. 덱이 쓰려고 더한 열쇠: `display_names`, `sales_insight_category_names`, `sales_insight_by_category_display`, `graph_nodes_by_kind`, `graph_edges_by_kind`, `graph_counts`, `coverage_major_class_count`, `coverage_relation_examples`, `example_cancer_surgery`, `example_cancer_surgery_names`, `example_text_to_number`, `example_gate_6months`, `mapping_auto_confirm_by_route`, `calibration_review_band_pct`, `schedule_collect_kst`, `schedule_weekly_close_kst`, `request_doc_count`, `simple_uw_questions_by_org`, `hanwha_rerun_verify_result`, `review_not_applied_items`, `site_file_size_mb`, 덱 v3(점검 답 반영)에서 범위와 출처를 밝히려고 더한 `simple_uw_product_short`, `calibration_score_overlap`, `calibration_correct_to_review`, `calibration_flip_methods`, `epost_summary_rows_by_doc`, `goldset_item_totals`, `goldset_epost_conditions`, `goldset_epost_constraints`, `goldset_not_scored`, `samsungfire_benefit_reader`, `next_load_orgs`, `graph_company_nodes_with_variants`, `request_docs_by_recipient`, `console4_tabs`, `workflow_triggers`, `symmetric_choice_item`, `comparison_targets_loaded`, 사용자가 준 `subscription_claude_usd_per_month`, `subscription_gemini_krw_per_month`, 실무자 1명의 응답 `practice_compare_source`, `practice_compare_time`, `practice_compare_frequency`, `practice_respondents`(측정값이 아니라 응답이므로 화면에 "실무자 1명 응답"을 함께 적는다), 그리고 git 과 GitHub 에서 센 `commit_count`, `commits_by_date`, `commits_by_author`, `project_days`, `pr_counts`, `pages_status`(제출 직전에 다시 센다).
- 외부 사실은 `refs.json`에 있다(열쇠, 값, 출처 URL, 구분 `official`, `academic`, `press`, 확인한 날). 확인하지 못한 사실(unverified)은 싣지 않는다. GitHub Actions 무료 범위는 2026-11-24에 GitHub 공식 문서로 확인해 `github_actions_public_free`로 실었다(공개 저장소의 표준 러너는 무료, 예약 실행은 저장소 활동이 60일 없으면 꺼짐). 연표 점 라벨에는 `openai_calibration_2023.short`처럼 `short` 하위키를 쓴다.
- 자료의 옛 이름(`우리 간편 닫힘`, `시장 소식`, `관문 차이` 따위)을 화면에 보일 때는 `display_names`나 `sales_insight_category_names`의 화면 이름을 쓴다.
