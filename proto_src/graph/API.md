# 관계망 탐색 시안 2 (`site/proto/graph2.html`)

회사, 종형, 특약, 급부, 표준담보, 보장분야, 시장 소식을 노드로 잇고, 노드를 누르면 이웃을 펼쳐 가며 따라가는 화면이다. 2026-11-20에 만든 시안의 원본을 저장소로 옮긴 것이다.

## 다시 만드는 명령

```bash
# 1. 자료: data/snapshot(과 data/seed/hum_표준담보사전.jsonl, data/proposals/표준담보_관계_두판독.jsonl)에서 graph.json
python proto_src/graph/build_data.py            # 출력 경로를 주면 거기에 쓴다(기본 proto_src/graph/graph.json)
# 2. 합치기: tpl.html + graph.json + proto_src/fonts/fonts_graph2.css → site/proto/graph2.html
python proto_src/graph/build.py                 # 출력 경로, --data <graph.json> 을 줄 수 있다
```

- 같은 입력이면 두 명령 모두 같은 바이트를 쓴다.
- `build_data.py`의 `WANT`는 견줄 종형 여섯(세 회사의 간편 종형 하나와 일반 종형 하나씩)이다. 사본에서 한 줄로 집히지 않으면 멈추므로, 사본의 상품명이나 종형명이 바뀌면 같은 뜻의 종형으로 고친다.
- `build.py`는 합친 파일에 외부 요청(src, href, url()의 바깥 주소, `<link>`, `@import`)이 있으면 쓰지 않고 멈춘다.
- 화면 일은 `tpl.html`만 고친다. `graph.json`과 `site/proto/graph2.html`은 생성물이라 손으로 고치지 않는다.

## graph.json 구조

```json
{"snapshot_at": "...", "kinds": [...], "ekinds": [...], "nodes": [...], "edges": [...], "keys": [...]}
```

- `snapshot_at`: 사본의 자료 시각(`data/snapshot/meta.json`). 화면 오른쪽 위 SNAPSHOT 자리에 나온다.
- `kinds`(노드 종류, 번호 순): 0 회사, 1 종형, 2 특약, 3 급부, 4 표준담보, 5 보장분야, 6 소식
- `ekinds`(엣지 종류, 번호 순): 0 판매(회사→종형), 1 포함(종형→특약, 특약→급부), 2 해당(급부→표준담보, `hum_담보매핑`의 검토상태가 자동확정, 승인, 수정인 줄), 3 속함(표준담보→보장분야), 4 관계(좁은 표준담보→넓은 표준담보), 5 일으킴(회사→소식)
- `nodes`: 노드 하나가 `[ID, 종류 번호, 이름, 기관코드 또는 null, 속성]` 배열이다. ID는 사본의 종형ID, 특약ID, 급부ID, 표준담보ID, 동향ID를 그대로 쓰고, 회사는 `ORG:<기관코드>`, 보장분야는 `CAT:<보장대분류>`이다.
- `edges`: 엣지 하나가 `[출발 노드 번호, 도착 노드 번호, 종류 번호, 속성]` 배열이다. 노드 번호는 `nodes` 배열의 자리(0부터)다.
- `keys`: 속성 이름 목록. 노드와 엣지의 속성은 `{"<keys 의 번호>": 값}` 꼴로 줄여 담았다. 값이 없는 속성은 넣지 않는다.

노드 종류별 속성

| 종류 | 속성 |
| --- | --- |
| 회사 | 기관코드 |
| 종형 | 공시상품명, 종형명, 간편고지, 갱신유형, 갱신주기년, 심사유형, 환급유형, 적용시작일 |
| 특약 | 담보구분, 갱신여부(갱신/비갱신), 갱신주기년, 최소가입금액만원, 최대가입금액만원 |
| 급부 | 기준지급액(예: "1000만원", "가입금액의 20%"), 기준가입금액만원, 면책일수, 감액(예: "12개월 이내 50%", 없으면 "없음"), 지급횟수제한, 근거("<근거문서종류> <쪽>쪽") |
| 표준담보 | 보장대분류, 보장중분류, 급부유형, 비교기준단위만원 |
| 보장분야 | 없음 |
| 소식 | 핵심요약, 분류유형, 발표일자, 매체명, 출처URL, 판정확률 (이름은 핵심요약 앞 40자) |

엣지 종류별 속성: 포함(종형→특약)은 담보구분, 갱신. 포함(특약→급부)은 급부역할. 해당은 검토상태, 매핑확률(없으면 "교차 확인"). 속함은 보장중분류. 관계는 관계, 확신_gemini, 확신_claude. 일으킴은 분류유형, 발표일. 판매는 없음.

## 화면이 자료를 읽는 자리

- `tpl.html`의 `<script type="application/json" id="gdata">__DATA__</script>`에 `build.py`가 graph.json을 넣는다(`</`는 `<\/`로 바꿔 넣는다).
- 스크립트 첫머리에서 `RAW=JSON.parse(#gdata)`로 읽고, `KIND=RAW.kinds`, `EK=RAW.ekinds`, `KEYS=RAW.keys`로 받은 뒤 `N`(노드), `E`(엣지)로 풀어 쓴다. 속성은 `dec()`가 `keys`로 이름을 되돌린다.
- 회사 색과 배지는 `MAIN=['EPOST','HANWHALIFE','SAMSUNGFIRE']`와 CSS 변수 `--o-<기관코드>`로 정하고, 나머지 회사는 `--o-OTHER`로 그린다.
- 시작 버튼은 `STARTS`(표준담보 이름 목록)다.
- 글꼴은 `<style>/*__FONTS__*/</style>` 자리에 `proto_src/fonts/fonts_graph2.css`가 들어간다(PLDisplay, PLBody, PLNum, PLWide).
