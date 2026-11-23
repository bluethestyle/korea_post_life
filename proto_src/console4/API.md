# 시안 4 규약 (탭을 채우는 에이전트용)

이 폴더의 원본을 `build.py`가 한 파일(`site/proto/console4.html`)로 합친다. 탭 1(브리핑)과 공통 부분은 끝났고, 탭 2~5를 이 규약대로 채운다.

## 1. 약속

- 탭마다 자기 파일만 고친다: 탭 2 `tab2.js`(+`tab2.css`), 탭 3 `tab3.js`(+`tab3.css`), 탭 4 `tab4.js`(+`tab4.css`), 탭 5 `tab5.js`(+`tab5.css`). `tabN.css`는 새로 만들면 build가 알아서 넣는다.
- `core.js`, `style.css`, `tpl.html`, `tab1.*`, `build.py`는 고치지 않는다. 공통 부품이 모자라면 탭 파일 안에 만들고, 공통으로 올릴 것은 보고에 적는다. (2026-11-20 보완 때 공통 부품을 이 규약대로 올렸다: 표 행 ›, 구역 머리, 지금 조건 배지, 빨강 넓이, 고른 행 몸통, 쪽 표지, 근거 기둥의 `.evl`, `.kv`)
- 탭 CSS의 선택자는 `#view-<탭id>` 아래로 가둔다(예: `#view-market .map{...}`). 공통 클래스 이름을 다시 정의하지 않는다.
- 값과 문장은 `App.S`(sales.json)와 `App.D`(d.json, 간편 세 등급 x 세 회사 비교 자료)에서 읽는다. 숫자와 판정을 화면에서 지어내지 않는다. 판정과 문장은 sales.json을 따른다(R10).
- 탭 파일은 build가 `(function(){ 'use strict'; ... })()`로 감싼다. 전역 이름을 만들지 않는다.
- 자리 표시 글("이 탭은 다음 단계에서 채운다")은 지운다. build가 남은 것을 경고한다.

## 2. 명령

```bash
# 자료 다시 만들기(사본이 바뀌었을 때). sales.json, combo.json, gate.json, cover.json, d.json 과 tab3.js 의 자료 줄,
# tab4.js 를 같은 사본으로 한 번에 쓴다. 손으로 쓴 코드(tab3.js 의 표식 밖, tab4.src.js)는 고치지 않는다
python scripts/export_app_data.py
# 탭 4 코드(tab4.src.js)만 고쳤을 때 tab4.js 다시 합치기
python proto_src/console4/gen_cover.py --assemble
# 합치기(검사 포함, 오류면 쓰지 않는다). 출력 경로를 주면 거기에 쓴다
python proto_src/console4/build.py
# 사진과 잰 값(흰 면, 빨강 넓이, 명암비, 가로 넘침, 콘솔 오류, 외부 요청). 둘째 인자는 이름 거르개
python proto_src/console4/shoot.py "" w1920
# 회사가 많을 때의 화면 시험(가상 자료). 우체국, 한화생명, 삼성화재에 가상 생명보험사 9곳과 손해보험사 8곳을 더한 사본
# (상대 19곳)을 out/synthetic_snapshot 에 만들고, 작업 폴더에 이 폴더를 복사해 그 사본의 자료를 내보낸 뒤 out/console4_synthetic.html
# 로 합친다. 이 폴더의 원본과 자료는 건드리지 않는다. --work out/console4_synthetic_work 를 주면 작업 폴더를 남긴다
# (가상 사본 폴더와 작업 폴더가 이미 있으면 이 명령이 만든 폴더일 때만 지우고 다시 만든다. 다른 폴더를 주면 멈춘다)
python scripts/dev/build_console4_synthetic.py
# shoot.py 는 site/proto/console4.html 만 연다. 가상 자료 화면은 브라우저로 out/console4_synthetic.html 을 직접 연다
```

가상 자료 화면(`out/console4_synthetic.html`)은 회사 수에 매이지 않는 화면을 시험하는 자료다. 회사 이름은 "가상생명 01", "가상화재 01" 따위이고 기관코드는 `SYNLIFE01`, `SYNFIRE01` 따위다. 한화생명과 삼성화재의 행을 본떠 회사마다 특약과 급부 일부를 빼고, 간편 종형의 고지 유형(입원수술 기간의 범위, 0년 유형 유무, 수술 포함 여부, 중대질병 수, 소견 범위), 면책과 감액, 가입나이를 사본에 있는 값 안에서 바꿨다. 값은 실제 회사 자료가 아니다. 맨 위 고지 줄의 고지 글 앞과 창 제목에 "가상 자료(화면 배치 시험용, 실제 회사 자료 아님)"가 붙는다(`build.py --banner`. 이 글은 어느 폭에서나 다 보이고, 380px 처럼 좁으면 고지 글 쪽이 줄임표로 줄어든다). out/ 은 저장소에 커밋하지 않고, 이 화면을 site/ 아래에 두지 않는다(공개 배포되면 안 된다). `build.py --src 폴더`는 원본과 자료를 그 폴더에서 읽어 합친다(글꼴은 저장소에서 읽는다).

`shoot.py`는 지금 브리핑 위주로 찍는다. 탭을 채우면 그 탭의 상태(고른 행, 좁은 화면의 판)를 찍는 줄을 `shoot.py`에 더해도 된다(이 파일은 함께 쓴다. 남의 줄은 지우지 않는다).

build 검사: 손으로 쓴 원본에 외부 주소(http, https, //, @import), 가운뎃점 나열(표식 문구 "내부 교육·비교 참고용(대외 배포 금지)"만 예외), 엠대시, "판올림", "됨", "준비 중"이 있으면 멈춘다. 합친 파일에 외부 요청(src, href, url()의 바깥 주소, link 태그)이 있거나 noindex 메타 태그가 없으면 멈춘다. d.json 이 없거나 자료 파일들(sales.json, combo.json, gate.json, tab4.js, d.json)의 자료 시각이 서로 다르면 멈춘다(`python scripts/export_app_data.py`로 다시 만든다). build 는 `tab4.js`를 실으므로, `tab4.js`가 cover.json 과 `tab4.src.js`를 합친 것과 다르면 멈춘다(`python proto_src/console4/gen_cover.py --assemble`로 다시 합친다). 글꼴(PLKo)에 없는 한글은 경고한다.

## 3. 탭 등록

```js
App.registerTab({
  id: 'market',                 // brief | market | gate | cover | insight
  kicker: '넓게 본다',            // 제목 위 13px 상위 이름. 제목은 탭 이름(App.TAB_NAME)
  render(body, ctx) {},         // 처음 보일 때와, 이 탭이 보이는 동안 조건이 바뀌었는데 update 가 없거나 false 를 돌려줄 때
  update(body, ctx) {},         // 선택. 조건이 바뀌었을 때 부분만 고치고 true 를 돌려주면 render 를 건너뛴다
  pick(key, ctx) {},            // 선택. 고른 항목의 근거 기둥 내용(아래 5절)을 돌려준다. null 이면 고르기를 푼다
  evidence(ctx) {},             // 선택. 아무것도 고르지 않았을 때의 근거 기둥 내용. 없으면 공통 기본(범위와 읽는 법, 범례)
  focus(key, body, ctx) {},     // 선택. App.go('market', {focus:'news'}) 로 들어올 때 그 영역으로 옮긴다
  enter(body, ctx) {},          // 선택. 탭으로 들어올 때마다(주인공 도형을 그리는 움직임)
});
```

- 화면 틀: core가 `<section id="view-<id>">` 안에 `<header class="vhead">`(제목 묶음 + 오른쪽 빈 칸 `ctx.aside`)와 `<div class="vbody">`(= `body`)를 만든다. 제목 묶음(상위 이름, 제목, 16x4 빨강 막대와 회색 점 넷)은 core가 그린다. 탭은 `body`를 채우고, 제목 옆에 큰 숫자나 띠를 둘 때만 `ctx.aside`를 쓴다.
- `body` 맨 위는 그 탭이 맡은 단계의 결론 한 줄이다(설계안 5절 (다) 3번). `<p class="concl">…</p>`(한쪽이 풀리는 띠 위의 17px 600 글, 왼쪽 3px 먹색 막대)로 쓴다.
- 다시 그릴 때마다 이벤트를 다시 붙이지 않도록 `body._bound` 같은 표시를 쓰거나, 아래 4절의 위임 속성을 쓴다.

`ctx`의 꼴

| 이름 | 뜻 |
| --- | --- |
| `S`, `D` | sales.json 전체, d.json 전체(`const D`) |
| `st` | 상태 복사본(아래 표) |
| `changed` | 이번에 바뀐 상태 이름의 Set (`age`, `sex`, `since`, `surg`, `base`, `renewal`, `tab`) |
| `baseId`, `base`, `baseInfo` | 기준 종형 ID, `S.기준별[baseId]`, `S.종형[baseId]` |
| `peerIds`, `peers` | 맞붙는 종형 ID 목록과 그 `S.종형` 항목 |
| `seg` | 지금 조건의 고객군 지도 칸: `{map, ri, ci, row, col, cell, reason, sexNote}`. 칸이 없으면 `cell` 이 null 이고 `reason` 에 까닭(R8) |
| `limit` | 지금 나이와 성별의 기준 종형 주계약 한도: `{table, hit:{lo,hi,max,pend}|null, lo, hi}` |
| `ref`, `isRef` | 기준별 값을 계산한 대표 조건(`S.기준조건`)과, 지금 조건이 그것과 같은지 |
| `ui`, `txt` | 그림 부품과 글 도우미(아래 6, 7절) |
| `aside`, `view` | render, update 에서만: 제목 옆 칸과 탭 section |

상태(`App.state`, 읽기 전용 복사본)

| 이름 | 값 |
| --- | --- |
| `tab` | `brief`, `market`, `gate`, `cover`, `insight` |
| `age` | 1~100 |
| `sex` | `M`, `F` |
| `since` | `null`(이력 없음), `0.25`, `1`, `2`, `3`, `4`, `5`(마지막 입원이나 수술이 몇 년 전보다 오래됐나) |
| `surg` | 입원 없이 수술만(`since` 가 null 이면 늘 false) |
| `base` | 기준 종형 ID(`S.기준종형`의 종형ID) |
| `renewal` | `null`(전체), `갱신`, `비갱신`. 고객군 지도(`S.지도[전체|갱신|비갱신]`)에만 쓴다 |
| `sel` | 탭별로 고른 항목의 key |
| `skin`, `motion` | `light`/`dark`, `on`/`off` |

조건 바꾸기는 `App.set({age:70, since:1, surg:true})`. 바뀌면 조건 줄, 범위 띠, 지금 탭이 다시 그려지고 다른 탭은 다음에 열 때 그린다. 탭과 조건은 주소의 `#` 뒤에 남고 뒤로 가기가 된다(근거 판이 열려 있으면 판부터 닫힌다). 지도 칸에서 조건을 바꿀 때는 칸을 누르면 먼저 근거 기둥에 요약을 띄우고, 그 안의 "이 고객군으로 조건 바꾸기" 단추에서 `App.set({...})`을 부른다(합의안 6번).

알림: `App.on('change', ctx => {})`, `App.on('tab', id => {})`, `App.on('select', (tab, key) => {})`, `App.on('resize', mode => {})`.

## 4. 고르기와 위임 속성

고를 수 있는 항목에 `data-pick="<key>"`를 단다. 누르면 core가 `App.select(key)`를 부르고, 같은 key 의 모든 요소에 `.is-sel`을 붙이고, 탭의 `pick(key, ctx)`가 돌려준 내용을 근거 기둥에 넣고, 중간 폭이면 기둥을 밀어 넣고, 좁은 화면이면 아래 판을 열고 그 행이 판에 가리지 않게 옮긴다(R7). Esc 나 판의 닫기는 고르기를 푼다. 조건이 바뀌어 다시 그려도 고른 표시와 근거는 다시 찍힌다.

목록 행(눌리는 행은 행 전체가 눌리고 오른쪽 끝에 ›가 늘 보인다, R6)

```html
<ul class="lrows">
  <li class="lrow selbar" data-pick="STD_CA_DX">
    <button type="button" class="lrow-hit" aria-pressed="false" aria-label="일반암 진단비 근거 보기"></button>
    <!-- 내용(눌림을 받지 않는다). 행 안에서 눌려야 하는 단추는 <span class="live"> 로 감싼다 -->
    <span class="sub">보조 글</span>
    <span class="lrow-chev">›(App.ui.IC.chevR)</span>
  </li>
</ul>
```

- `.selbar`가 붙은 요소가 고른 빨강 막대가 된다(글자보다 왼쪽으로 24px 더 나가고, 왼쪽에서 180ms 에 차오른다). 행의 일부만 막대로 쓰려면 그 부분에 `.selbar`를 단다(머리 줄만 막대로 쓰는 것이 기본이다).
- 빨강 넓이(S3, 2.5% 이하)는 core 의 `App.fitSel()`이 지킨다. 막대 높이로 빨강이 차지할 길이를 셈해 `--sel-red`에 두고, 그보다 긴 막대는 오른쪽이 슬레이트(`--sel-fade`)로 이어진다. 1920 화면의 한 줄 막대는 거의 끝까지 빨강이고, 좁은 창이나 키 큰 행일수록 슬레이트가 길어진다. 고른 행의 몸통(막대 아래 줄)은 core 가 옅은 면과 왼쪽 3px 빨강 선으로 칠한다. 탭이 `.is-sel`을 직접 바꿨으면 `App.fitSel()`을 부른다.
- 고른 행 안의 글자는 모두 흰색, `.sub`는 rgba(255,255,255,.88)로 바뀌고, 칩(`.vd`, `.scb`, `.tag`)과 표식에는 1px 흰 테두리가 붙는다. 탭 CSS에서 이 색을 덮지 않는다.
- 표의 행은 `App.ui.table({..., pick: i => key})`로 만들면 `tr.pick[data-pick]`이 되고 마지막 칸 끝에 ›(`ui.RCHEV`)가 붙는다. 표를 손으로 만들 때도 마지막 칸에 `ui.RCHEV`를 넣는다. 고른 행은 행 전체 막대(위와 같은 빨강 길이), 가리켜도 막대가 그대로다.
- 네모 칸(지도 칸, 기술 나무 칸)은 `<button class="sq m-only" data-pick="r6c1">` 에 꺾쇠 `<i class="cur t"></i><i class="cur r"></i><i class="cur b"></i><i class="cur l"></i>`를 넣는다. 고르면 바깥 3px 빨강 테두리, 안쪽 2px 흰 윤곽, 꺾쇠가 보인다.
- 빨강은 고른 것 하나와 작은 눈금, 원문 확인 표식에만 쓴다(1920 화면 넓이 2.5% 이하). 두 번째 빨강 면을 만들지 않는다.

위임 속성(core가 처리한다. 탭에서 이벤트를 붙이지 않아도 된다)

| 속성 | 동작 |
| --- | --- |
| `data-go="cover"` (+ `data-focus="journey"`) | 그 탭으로 가서 `focus(key)`를 부른다 |
| `button[data-copy="<table id>"]` (+ `data-title`) | 그 표를 탭으로 구분한 글자로 복사(첫 줄 범위 머리말, 둘째 줄 머리글). 칸마다 복사할 원문 글자는 칸의 `data-cp`(또는 `data-copy`)에 둔다. 칸의 속성은 행 고르기를 막지 않는다(위임은 단추에만 건다). `tr.no-copy`(묶음 머리 줄)는 빼고 복사한다 |
| `button[data-print="<요소 id>"]` (+ `data-card="1"`, `data-title`) | 그 영역만 흰 바탕 먹색으로 인쇄(짙은 스킨에서도 쪽 여백까지 흰 바탕). `data-card="1"`이면 머리에 시연용 고지와 "내부 교육·비교 참고용(대외 배포 금지)" 표식 |
| `data-act="..."` | core는 건드리지 않는다(탭이 직접 처리). 단 `data-act="base-to" data-v="<종형ID>"`는 기준 종형을 바꾼다 |

브리핑에서 들어오는 `focus` 열쇠: 탭 2 `map`(고객군 지도), `news`(개정과 시장 소식). 탭 4 `journey`(치료 여정 격자). 탭 3과 5는 열쇠 없이 들어온다. 이 열쇠를 받는 `focus`를 만든다.

## 5. 근거 기둥

`pick(key, ctx)`와 `evidence(ctx)`가 돌려주는 꼴

```js
{
  kicker: '선택 종형',          // 13px 상태 라벨
  title: '일반암 진단비',       // 18px 제목
  badges: [App.ui.scope('base'), App.ui.verdict('worse')],   // 결론 배지
  body: '<div class="ev-sec">...</div>...',                  // HTML 문자열이나 DOM 노드
  after(bodyEl) {},           // 선택. 넣은 뒤 부르는 함수(관계 그림 그리기 등)
}
```

- 기둥 안 차례는 고정이다: 머리띠(kicker, title, badges), 문장, 관계 그림, 근거(문서와 쪽), 뺀 것. 구역마다 `<div class="ev-sec"><h3>제목</h3>...</div>`, 근거와 뺀 것처럼 셋째 층은 `ev-sec lo`(한 기둥 안에서 테두리 없이 명도로 나눈 세 층).
- 본문과 판정이 같아야 한다(R10). 단정 주의(`기준별[].단정주의`)에 든 담보는 기둥에서도 `verdict('diff')`("우열을 매기지 않음")와 까닭을 보인다. `원문대조`가 참이면 본문 줄에 `ui.flag()`, 기둥에 `ui.flagText()`, 카드에도 붙인다.
- 고르지 않고 내용만 바꾸려면 `App.ev.show(spec)`.

## 6. 공통 부품 (`App.ui`)

| 부품 | 함수 또는 클래스 | 메모 |
| --- | --- | --- |
| 패널 | `.panel`(쿨그레이 .82, 위 3px 흰 선), `.panel.slate`(강조, 흰 글자), `.panel.tbl-wrap`(표 .9), `.panel-h`(`.k` 상태 라벨 + `h2` 18px + `.r` 오른쪽), `.panel-f` | 짙은 머리 띠를 쓰지 않는다 |
| 옅은 기둥 | `.pillar`(+`.tl` 위 2px 흰 선) | 제목과 큰 숫자만 얹는다. 본문과 표는 얹지 않는다 |
| 제목 묶음 | `ui.title(id, kicker, text)` | core가 이미 그린다 |
| 목록 행 | `.lrows`, `.lrow`, `.lrow-hit`, `.lrow-chev`, `.selbar`, `.sub`, `.live` | 4절 |
| 판정 칩 일곱 | `ui.verdict(kind, text?)`: `better` 우체국 나음 ▲, `only` 우체국에만 있음 ◆, `worse` 우체국 못함 ▼, `same` 같음 =, `diff` 우열을 매기지 않음 ⇄, `none` 우체국에 없음, `unknown` 모름 ? | 기호는 SVG. 주어를 빼지 않는다(R4). 상대 회사 줄 끝에 주어 없는 기호만 붙이지 않는다 |
| 판정 칸 선 | `.vl-better`(왼쪽 3px 금색 선), `.vl-worse`(왼쪽 3px 먹색 선) | |
| 그 밖의 표지 | `ui.tag(text, title)` → `.tag` | 대표, 갱신, 문서 쪽. 짙은 면을 쓰지 않는다 |
| 원문 확인 표식 | `ui.flag(text?)`(부모 `position:relative`의 왼쪽 위 16x16 빨간 직각삼각형), `ui.flagText(text?)`(글 꼴) | 기본 글 "사업방법서 원문 확인 필요" |
| 범위 배지 | `ui.scope('all')` 전체 고객군, `ui.scope('base')` 선택 종형, `ui.scope('now')` 지금 조건(점선 테두리) | R11. 구역 머리마다 단다. 나이, 성별, 이력으로 바뀌는 값(관문 나무, 한도, 구성 예시)은 `now` |
| 구역 머리 | `ui.band({kicker, title, sc, stats:[{n, d, u, l, bar:[v,max,cls], title}], eq, note})` → `.sband` | 표와 목록이 길게 이어지는 구역 위에 둔다. 왼쪽은 옅은 기둥 위 제목, 오른쪽은 안개 위 큰 숫자 칸(40px)과 6px 막대. `sc` 는 배지 하나나 배열. 같은 수를 아래 패널에 다시 쓰지 않는다 |
| 큰 숫자 | `ui.big(n, d, unit)` → `.big .n .d .u` | 48px 400, 분모 .65배 |
| 진행 고리 | `ui.ring({v, max, size:72, lead, segs:[{v, cls:'gold'}], pct, sel, label})`, `ui.drawRings(root)` | 못 채운 호는 방사형 잔눈금, `lead`는 네 귀 45도 사선, `sel`은 빨강 원 |
| 수평 막대 | `ui.hbar(v, max, cls)` → `.hbar > i`(6px, `#151D24`, `.gold`, `.other`) | 칸칸이 끊긴 막대는 쓰지 않는다 |
| 줄무늬 없는 표 | `ui.table({id, head, rows, num:[열], caption, pick})` → `.tbl` | 1px 옅은 행선, 값은 `.v` 오른쪽 맞춤 고정폭 |
| 관계 식(R5) | `ui.eq({total:{t,n}, parts:[{t,n}], tail, nonAdd})` | 더해지지 않는 수는 `nonAdd`에 까닭을 적는다(`.nadd`) |
| 칸 띠 | `ui.cells(['m-only','cmp','wait',...])`, `ui.swatch(label)`, `ui.MAP_CLS[label]` | 지도 라벨 색: `.m-only`(금빛 #D8CCA0, 우리 간편만 열림), `.m-both`, `.m-ours`, `.m-all`, `.m-none`(빗금). 지도 칸에 우열 판정어와 판정 색을 쓰지 않는다 |
| 꺾쇠 선택기 | `ui.chevSel({label, options:[{v,t,title}], value, onChange, w})` → DOM(`.set(v)`) | 선택지 다섯 이하일 때. 누르는 자리 40px |
| 숫자 입력 | `ui.stepper({label, value, min, max, unit, onChange})` → DOM | |
| 흰 칩 단추 | `ui.btn(text, {main, sm, ghost, icon:'copy'|'print'|..., chev, attrs})` | 주 단추는 왼쪽 4px 빨강 막대, 가리키면 빨강 면에 흰 글자 |
| 한쪽이 풀리는 띠 | `ui.fadeBand(html, {slate})` → `.fade-band` | .88 에서 0 으로 약 400px |
| 네모 칸 | `.sq` + `.is-sel` + `.cur.t/.r/.b/.l` | 4절 |
| 짙은 결과 카드 | `.rcard`(`.k`, `h3`, `.gold-t`, `.sec`, `p`) | 위 2.5px 금색 선, #12171D. 인쇄하면 흰 바탕 먹색 |
| 아이콘 | `ui.IC.chevR/chevL/chevD/better/only/worse/same/diff/none/unknown/lock/copy/print/grid/pin/open/check/hatch/arrow` | SVG 문자열 |
| 범례 | `App.ev.legend()` | 접지 않고 늘 보인다 |

색과 면의 규칙(합의안 S1~S13 요약)
- 거의 흰 면(`--white`)은 입력 칸과 응대 카드 미리 보기에만 쓴다(화면 넓이 10% 안쪽). 목록, 패널, 표는 쿨그레이 면.
- 빨강(`--red`, 막대는 `--red-hi`에서 `--red-deep`으로)은 고른 것, 작은 눈금, 원문 확인 표식에만. 판정에 쓰지 않는다.
- 금색 면 `--gold`(그 위 글자 #151D24), 금색 선 `--gold-line`. 우체국 나음과 우리 간편만 열림에만.
- 글자 `--ink-0`(본문), `--ink-1`, `--ink-2`(작은 라벨), `--ink-3`(가장 흐림, 패널 위에서만). 안개 위에는 `--ink-2`보다 흐린 글자를 두지 않는다. 슬레이트 면 위 본문은 흰색.
- 모서리 반경 0(진행 고리만 원). 빛 번짐 없음. 짙은 스킨은 같은 토큰이 바뀌므로 색 값을 직접 쓰지 말고 토큰을 쓴다.

탭별 주인공 도형(S10)과 움직임 시간 토큰: 고객군과 시장 = 구역 지도(12행 3열, 칸이 왼쪽 위에서 번져 나옴 `--t-map` 400ms), 가입 관문 = 기술 나무(세 회사 세 갈래, 56px 칸, 1.5px 직선이 자람 `--t-tree` 400ms), 담보 비교 = 6px 수평 막대와 줄무늬 없는 표와 직각 꺾은선 관계도(갈림 자리 9px ◇, 막대가 참 `--t-bar` 300ms), 영업 인사이트 = 응대 카드 `.rcard`와 다섯 분류 묶음. 움직임은 `App.motionOn()`이 참일 때만, `:root[data-motion="off"]`이면 core가 모든 전환을 0으로 만든다. 움직이는 동안에도 누를 수 있고 글자가 읽혀야 한다.

## 7. 글 도우미 (`App.txt`)와 글의 규칙

| 함수 | 쓰임 |
| --- | --- |
| `josa(word, '과'|'와'|'은'|'는'|'이'|'가'|'을'|'를'|'으로'|'로'|'이나'|'이며'|'이고')` | R2. 화면이 만드는 글의 조사. 끝의 괄호 묶음(겹친 괄호 포함)을 빼고 그 앞 낱말의 받침으로 고른다("3종(간편가입355)" → "으로"). 값 뒤에 조사를 손으로 붙이지 않는다 |
| `fixJosa(text)` | 자료 문장의 괄호 뒤 조사를 같은 규칙으로 바로잡는다. core 가 sales.json 을 읽을 때 모든 글에 한 번 건다(sales.py 의 문장 틀을 고치기 전까지의 화면 쪽 처리) |
| `pageText(doc, page)`, `PAGE_WHY` | 문서 쪽 표지. 쪽이 없으면 "사업방법서: 쪽 번호 자료 없음"(R8), 근거 기둥에는 `PAGE_WHY`로 까닭을 적는다 |
| `shortName(name, {brackets})` → `{short, full, changed}`, `ui.name(full, opts)` | R1. 겹친 괄호를 안쪽부터 지우고 짝이 안 맞으면 원문. 줄인 이름은 `title`과 근거 기둥에 원문을 둔다 |
| `sameSummary({EPOST:v, HANWHALIFE:v, SAMSUNGFIRE:v})` | R3. 값이 없는 회사가 끼면 "값이 있는 두 회사 같음" |
| `stateWhy(org, state)` | R8. "나이 자료 없음: 삼성화재의 가입나이 자료가 아직 들어오지 않았습니다" |
| `vname(id)`, `vkind(id)`, `vinfo(id)`, `orgShort(code)`, `sinceText(since)`, `sexText(sex)` | 종형과 회사 이름 |

- 나열은 쉼표로(가운뎃점 금지), 엠대시 금지, "~됨" 압축 금지, 버전의 뜻으로 "판" 금지, 번역투 금지. 표지는 줄바꿈하지 않는다(R9, `.tag`, `.vd`, `.scb`는 이미 nowrap).
- 여러 수를 나란히 보일 때 전체와 부분의 관계를 적는다(R5, `ui.eq`).
- 가리켜야만 보이는 정보를 두지 않는다(R6, 태블릿). `title`은 덤이고, 같은 내용이 화면이나 근거 기둥에 있어야 한다.
- 자료 없음에는 까닭을 적는다(R8).
- 한글 글자는 13px 아래로 쓰지 않는다(표지, 칩, 범례, 근거 기둥의 표 머리, SVG 글자 포함). 숫자만 든 글은 12px 까지 쓴다.
- 가장 흐린 글자는 `--ink-2`(#4A535D)다. `--ink-3`은 글자에 쓰지 않는다(셋째 층 위에서 4.5:1 에 못 미친다).

## 8. 화면 폭

| 폭 | 배치 | 근거 기둥 |
| --- | --- | --- |
| 1600px 이상 | 좌우 64px, 본문과 근거 기둥(424px)을 나란히 | 늘 보임(위 끝은 본문 위 끝에 맞춰 고정) |
| 1000~1599px | 좌우 32px. 조건 줄은 묶음 머리 글과 비교 상대를 접어 한 줄(1280 기준), 범위 띠는 한 줄 요약과 "자세히" | 고르면 밀려 들어오고 본문이 좁아진다. 닫기, Esc, 뒤로 가기로 닫힌다 |
| 1000px 미만 | 좌우 16px, 한 열. 조건 줄은 요약 단추로, 범위 띠는 한 줄 요약과 "자세히"로 접힌다 | 아래에서 올라오는 판(62vh). 판 높이만큼 본문 아래 여백(`--sheet-h`) |

- `App.mode()`는 `wide`, `push`, `sheet`. 좁은 화면에서 탭 안의 영역을 바꾼 뒤에는 `App.reveal(el)`로 그 영역을 보이게 옮긴다(R7).
- 고정된 위 띠 아래로 옮겨 갈 때 제목이 가려지지 않게 `id`가 있는 요소에는 `scroll-margin-top`이 이미 걸려 있다(R9).
- 1280px 에서 깨지지 않는지, 380px 에서 글자가 잘리거나 겹치거나 가로로 넘치지 않는지 사진으로 본다(`shoot.py` 의 `넘침` 값이 0px).

## 9. 예제: 줄무늬 없는 표와 고르기, 복사

```js
App.registerTab((function () {
  const { ui, txt } = App;
  function render(body, ctx) {
    const rows = ctx.base['개정검토'].map(g => [ui.esc(g['중분류']), String(g['담보수']), ui.esc(g['담보'].map(d => d['담보']).join(', '))]);
    body.innerHTML = `
      <p class="concl">개정 검토 후보 ${ctx.base['분류집계']['개정 검토 후보']}건을 보장 중분류 ${rows.length}줄로 접었습니다.</p>
      <section class="panel tbl-wrap">
        <div class="panel-h"><div><span class="k">${ui.scope('base')}</span><h2>개정 검토 목록</h2></div>
          <div class="r">${ui.btn('표 복사', { sm: true, ghost: true, icon: 'copy', attrs: 'data-copy="rev-tbl" data-title="개정 검토 목록"' })}</div></div>
        ${ui.table({ id: 'rev-tbl', head: ['중분류', '담보 수', '담보'], rows, num: [1], pick: i => 'rev' + i })}
      </section>`;
  }
  function pick(key, ctx) {
    const g = ctx.base['개정검토'][+key.slice(3)];
    if (!g) return null;
    return { kicker: '개정 검토 후보', title: g['중분류'], badges: [ui.scope('base')],
      body: `<div class="ev-sec"><p>${ui.esc(txt.josa(g['중분류'], '은'))} 가진 상대 ${g['담보'][0]['가진상대수']}곳입니다.</p></div>` };
  }
  return { id: 'insight', kicker: '인사이트와 산출물', render, pick };
})());
```

## 10. 자료 메모

- `S.기준별[종형ID]`: `맞붙는종형`, `범위`(비교쌍, 뺀비교쌍, 상대별 머리말 번호), `관문`(대표 조건의 관문), `포인트`(ID 목록, 본문은 `S.포인트[ID]`), `분류집계`, `세부집계`, `먼저`(`브리핑`, `카드`: pick 규칙의 처음 선택), `뺀포인트`, `단정주의`, `개정검토`, `치료여정`, `보류요약`, `브리핑`.
- `S.포인트[ID]`: `분류`, `세부`, `문장`(본문용 분석 문장), `카드질문`과 `카드답`(응대 카드 미리 보기 안에서만), `머리말`(`S.글`의 번호), `근거`, `원문대조`, `원문대조글`, `목적`.
- `S.지도[전체|갱신|비갱신]`: 남성 기준만 있다. 여성이면 `ctx.seg.sexNote`를 보인다. 칸: `라벨`, `보조`, `닫힌사유`, `회사`(회사별 관문 상태), `대표`, `상대대표`, `분류수`, `자료없음`, `열린종형`, `관문기준`, `관문포인트`, 그리고 회사가 많을 때 이름 대신 보일 수(2026-11-23 추가): `상대수`, `열린상대수`, `닫힌상대수`(닫힘과 심사로 확인), `모르는상대수`(나이 자료 없음, 질문 자료 없음), `관문만열린상대수`(관문만 수집한 종형으로만 열린 회사. 열린상대수에도 든다). 셋의 합이 상대수다.

### 회사가 많을 때 (2026-11-23 추가)

비교 회사는 생명보험 10곳과 손해보험 9곳(우체국을 더해 20곳)으로 늘어난다. 자료(sales.json)는 셋까지는 지금과 같고, 상대 회사가 넷 이상이면 이렇게 바뀐다(계산은 `src/postlife/site/sales.py`).
- 문장에서 회사나 종형 이름을 잇는 곳은 "A, B, C 등 19곳"(종형은 "등 19개")으로 줄인다. 근거(`근거`), `비교종형ID`, `범위.상대`의 목록은 줄이지 않는다. 화면이 회사 목록을 보일 때는 이 목록을 읽는다.
- `범위.문장`의 첫 문장은 "견준 상품은 생명보험 10곳, 손해보험 9곳의 상품 19개입니다." 꼴이다. 업권별 수는 `범위.업권별`(`생명보험`, `손해보험`, 업권을 모르면 `업권 모름`)에도 있다.
- 포인트와 단정 주의의 `머리말`은 상품마다 적지 않고 "수집한 19곳의 상품 19개 기준(2026-07-01~2026-10-01)" 꼴이다. 상품마다의 머리말은 `범위.상대[].머리말`에 있다.
- 브리핑 (가)의 `값.열린상대수분포`(`최소`, `중앙`, `최대`): 지도 칸마다 열린 상대 수의 분포다. (라)는 상대마다의 보유 수 대신 "상대 19곳의 보유 담보는 43~57개(중앙값 52개)" 꼴로 적고, 값에 `상대회사수`, `상대보유분포`, `상대보유요약`을 더한다. 상대마다의 보유 수는 `값.상대보유`에 그대로 있다.
- 회사 이름은 `S.종형[ID].회사`와 d.json 의 `orgs`(세 회사 밖의 회사는 짧은 이름이 기관 이름이다)에 있다. 가상 자료로 시험할 때 화면이 세 회사를 가정한 곳은 위 "명령"의 가상 자료 화면에서 드러난다.
- `S.한도표`, `S.개정변동`, `S.시장소식`(`인용안내`를 함께 보인다), `S.목적`(화면 이름 "암", "3대 질병", "입원과 수술", "보장 대분류 기준"), `S.분류`, `S.카드분류차례`, `S.라벨`.
- `App.D`: d.json(간편 3.1.5, 3.2.5, 3.5.5 세 등급 x 세 회사 종형의 비교 자료). `scripts/export_app_data.py`가 사본에서 만들고(계산은 `src/postlife/site/lineup.py`), build 가 `const D = <d.json>;`으로 싣는다. d.json 이 없으면 build 가 멈춘다. 지금 읽는 곳은 회사 짧은 이름(`orgs`, core)뿐이다. 탭 2의 개정 변동 근거(보장대분류와 급부유형)는 `S.표준담보`를, 담보 비교표와 관계 그림은 `CV`(cover.json)를 읽는다. 판정과 문장은 sales.json 을 따른다.
- 자료 파일의 열쇠와 꼴은 `tests/test_console4_data.py`가 본다(사본으로 새로 만든 자료와 커밋된 자료 파일 둘 다. 커밋된 자료의 자료 시각이 사본과 같으면 바이트까지 같아야 하고, 사본이 더 새것이면 그 시험은 건너뛰며 다시 만들라고 알린다). 합친 결과가 커밋된 `site/proto/console4.html`과 같은지는 `tests/test_console4_build.py`가 본다.
- 기준별 값과 문장은 대표 조건(`S.기준조건`, 50세 남성, 이력 없음)으로 계산한 값이다. 조건을 바꿔도 그대로인 값에는 왜 그대로인지 적는다(R11, 브리핑의 안내 줄 참고).

## 지도 칸을 조건 값으로 바꾸기 (2026-11-23 추가)

지도 칸에서 "이 고객군으로 조건 바꾸기"를 만들 때는 탭마다 따로 계산하지 않고 core의 함수를 씁니다. 브리핑의 24칸 격자와 고객군과 시장 탭의 지도가 같은 칸에서 같은 조건으로 바뀌어야 하기 때문입니다.

- `App.segPatch(지도, 행 번호, 열 번호)`: 그 칸에 해당하는 조건 값(나이, 이력 시점, 수술만 여부, 필요하면 기준 종형)을 돌려줍니다. `App.set`에 그대로 넘깁니다.
- `App.segPatchText(조건 값)`: 단추 아래 안내 글("누르면 조건 줄이 …으로 바뀝니다")에 쓰는 글자입니다.
- `App.samePatch(조건 값)`: 지금 조건이 이미 그 칸인지 봅니다(같으면 단추 대신 안내를 보입니다).
- 격자에서 "지금 조건" 칸을 찾을 때는 그리는 지도와 같은 지도로 찾습니다. 전체 지도로 그리는 격자는 `App.cellOf({...App.state, renewal: null})`로 찾습니다(갱신 유형 거르개의 지도는 나이 구간이 달라 열 번호가 어긋납니다).
