# 요청 40. 시안 4 PR 9번 검수 뒤 남은 것: 선택 막대 자동 스크롤 1건 (Antigravity 개발 에이전트용)

PR 9번은 모두 머지했고(2026-11-25, 머지 커밋 `207cd6b`), 아래는 남은 것입니다. PR 9번(브랜치 `antigravity/console4-feedback`)은 분석 화면 시안 4(`site/proto/console4.html`)에 배포 화면 사용자 의견을 반영한 PR이고, 머지됨 상태로 닫혔습니다. 지시서는 요청 35(배포 화면 사용자 의견 반영 지시서, `docs/gemini_requests/35_시안4_배포화면_사용자의견_반영_Antigravity.md`)와 그 부록, 그리고 이 문서의 지난 내용입니다.

- 검수 경과: `6c7f5f3`은 머지하지 않았습니다. `503f9e9`(문서 수치 정정)까지는 머지 기준을 충족해 커밋 `a65a015`로 머지했습니다. 그 뒤의 `03ba30b`는 새로 생긴 결함 2건(스크롤할 것이 없는데 보이는 스크롤 안내, Esc 직후 같은 탭 재진입에서 클릭되지 않음)으로 머지를 막았습니다. 2026-11-25 07:55의 커밋 `2797b0c`에서 두 건이 고쳐지고 함께 고칠 것 6건 가운데 5건이 해소되어(나머지 1건은 일부만 고쳐짐), 세 번째 검수를 거쳐 머지했습니다.
- 이번 검수에서 고쳐졌다고 확인한 것은 이 문서에서 지우고 6절에 한 줄씩 남겼습니다. 일부만 고쳐진 것(선택 막대 자동 스크롤)은 남은 부분만 1절에 실었습니다.
- 확인 방법: 재빌드 결과와 커밋한 `site/proto/console4.html`의 바이트 비교(6,381,538바이트, 같음), 전체 테스트(1,512 통과, 1 건너뜀), Playwright로 해상도별 화면을 열어 재는 재현과 실제 마우스와 휠 입력. 측정 수치는 Claude 쪽 서버에서 애니메이션 설정 "켬"으로 잰 값입니다.

## 사람이 할 일

Antigravity에 이 지시를 넣습니다.

> 요청 37(화면 문구를 실무 용어로 바꾸는 요청)의 PR이 머지된 뒤 `git fetch origin`을 하고 `origin/main`에서 브랜치 `antigravity/console4-feedback-2`를 만들어(`git switch -c antigravity/console4-feedback-2 origin/main`), `docs/gemini_requests/40_시안4_PR9검수결과_머지전에_고칠것_Antigravity.md`를 읽어 수정한 뒤 PR을 연다. 데이터 파일(`proto_src/console4/*.json`)은 수정하지 않는다.

---

## 1. 고칠 것 (1건)

### 담보 막대를 선택한 직후 하단 상세 패널이 열리는 동안 휠을 굴리면 선택 막대가 30px 잘린 채 남음

지난 문서의 "애니메이션 켬에서 선택한 막대가 차트 영역 아래로 잘림"(지난 2-2)의 남은 부분입니다. 휠을 굴리지 않는 경우는 고쳐졌습니다(6절).

- **현상**: 애니메이션 "켬", 1366x768, 담보 비교에서 두 번째 막대(`#z-center .cvp-slot` nth(1))를 클릭하고 120ms 뒤 차트 영역 가운데서 휠(deltaY 200)을 25ms 간격으로 3번 굴리면, 2초 뒤 `#z-center`의 `scrollTop`이 0(스크롤 여유 171)이고 선택 막대 아래 가장자리 434px가 차트 영역 아래 404px를 넘어 30px 잘립니다. 휠을 굴리지 않으면 `scrollTop` 40, 막대 아래 394px로 잘림이 없습니다. Claude가 3회 실행해 3회 모두 같은 값이었습니다. 휠을 다시 굴리면 풀립니다.
- **근거**: 선택한 막대는 차트 영역 안에 보여야 합니다(지난 문서의 자동 스크롤 기준). 막대를 선택하자마자 휠을 굴리는 것은 흔한 조작이고, 그때 휠이 차트 영역을 실제로 움직이지 못했는데도 선택 막대가 잘린 채 남습니다.
- **추정 원인과 코드 위치** (코드로 확정하지 못함): 하단 상세 패널이 열리는 애니메이션 동안의 휠 입력은 차트 영역을 움직이지 못하는데도, `tab4.src.js`의 `userScrolledZc`(175행)가 `true`가 되어 `ev-settled` 뒤의 자동 스크롤(`scrollSelectedBarIntoCenter`, 661행)을 건너뛰는 것으로 보입니다. 이 함수는 `#z-center`의 `wheel`과 `touchmove` 이벤트가 오면 `scrollTop`이 바뀌었는지와 상관없이 `userScrolledZc`를 `true`로 둡니다.
- **고치는 방향**: 사용자가 실제로 `scrollTop`을 바꿨을 때만(휠 전후의 `scrollTop` 비교나 `scroll` 이벤트) 자동 스크롤을 건너뛰게 합니다. 자동 스크롤이 사용자의 휠을 덮어쓰지 않는 성질(선택 700ms 이후나 1500ms 뒤의 휠은 그대로 유지됨)은 지킵니다.

---

## 2. 참고 (이번 요청에서 고치지 않는 것)

- **실시간 측정의 흔들림**: `requestAnimationFrame`으로 실시간 기록하는 측정은 서버 부하에 따라 프레임이 24~47ms 늦어져 한 프레임 이동 값이 커질 수 있습니다. 기준을 넘는 값이 나오면 WAAPI 애니메이션을 멈추고(`getAnimations()`로 찾아 `pause()` 뒤 `currentTime`을 16.7ms씩 옮김) 프레임마다 재는 측정을 함께 보고 둘 다 적습니다. 지난 검수의 가장자리 판정도 이 측정으로 했습니다.
- **33ms 넘는 프레임 수**: 같은 측정을 다시 하면 값이 흔들려 결함으로 단정하지 않습니다. 다시 잴 때는 3회 실행의 가장 나쁜 값을 그대로 적고, 실행한 PC의 CPU와 다른 프로그램 실행 여부를 함께 적습니다.
- **판정 칩의 옛 이름**: 하단 상세 패널과 표로 보기의 회사별 판정 칩은 아직 옛 이름(같음, 우체국 나음 등)입니다. 요청 37(화면 문구를 실무 용어로 바꾸는 요청, `docs/gemini_requests/37_시안4_화면문구를_실무용어로_Antigravity.md`)에서 처리합니다.
- **데스크톱에서 상세를 닫기 버튼으로 닫은 뒤 `#z-right`의 `is-picked`가 약 500ms 뒤에 풀림** (`503f9e9`부터): `main`(PR 9번 머지 전)은 즉시 풀렸습니다. 이번 검수(`2797b0c`)에서도 점검 에이전트의 같은 시험에서 지난번과 같은 결과였습니다(담보 비교, 1366x768, 1600x900, 1920x1080). 휠 차단은 재현되지 않았습니다. 고칠 때 함께 보면 됩니다.
- **380x780 영업 인사이트에서 시트를 닫으면 본문 스크롤이 22px 어긋남**: 이번에도 307에서 285로 어긋났습니다(닫기 버튼, 상세의 뒤로, 브라우저 뒤로 모두). PR 9번 머지 전의 `main`은 수백 px 어긋났으므로 나아졌습니다.
- **모바일에서 화면 장식 눈금이 본문 글자 위에 겹쳐 보임** (이번 검수에서 새로 적음): 화면 장식 눈금(`i.tk.red`, 14x3px, `position: absolute`)이 본문 글자 위에 놓입니다. 380x780 영업 인사이트에서 viewport y 174(머지 후)에 있고, PR 9번 머지 전의 `main`에도 y 208에 같은 요소가 있어 이 PR에서 생긴 것은 아닙니다. 고칠 때 함께 보면 됩니다.

---

## 3. 재현 스크립트

스크립트를 저장소 밖의 임시 폴더에 저장하고, 저장소 루트에서 실행합니다(`python <임시 폴더>/check40c.py`). Playwright(Chromium)가 필요합니다. 스크립트와 출력은 커밋하지 않습니다.

```python
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
URL=Path('site/proto/console4.html').resolve().as_uri()
Q="()=>{const z=document.querySelector('#z-center');const b=document.querySelector('#z-center .cvp-slot.is-sel .cvp-bar');const zr=z.getBoundingClientRect();return {top:Math.round(z.scrollTop),room:z.scrollHeight-z.clientHeight,bar_bottom:b&&Math.round(b.getBoundingClientRect().bottom),area_bottom:Math.round(zr.bottom)}}"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for (w,h) in [(1366,768)]:
      for wheel in (False,True):
        ctx=await b.new_context(viewport={'width':w,'height':h})
        await ctx.add_init_script("try{localStorage.setItem('postlife-c4-skin','light');localStorage.setItem('postlife-c4-motion','on')}catch(e){}")
        pg=await ctx.new_page(); await pg.goto(URL); await pg.wait_for_timeout(1000)
        await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(1000)
        await pg.locator('#z-center .cvp-slot').nth(1).click(); await pg.wait_for_timeout(120)
        if wheel:
          r=await pg.locator('#z-center').bounding_box(); await pg.mouse.move(r['x']+r['width']/2,r['y']+r['height']/2)
          for i in range(3): await pg.mouse.wheel(0,200); await pg.wait_for_timeout(25)
        await pg.wait_for_timeout(2000); print('wheel',wheel,await pg.evaluate(Q))
        await ctx.close()
    await b.close()
asyncio.run(main())
```

`2797b0c` 머지 결과의 출력입니다.

```
wheel False {'top': 40, 'room': 171, 'bar_bottom': 394, 'area_bottom': 404}
wheel True {'top': 0, 'room': 171, 'bar_bottom': 434, 'area_bottom': 404}
```

"그대로 유지할 것"(5절)을 확인할 때 쓰는 지난 스크립트 `check40.py`와 `check40b.py`는 git 이력의 커밋 `01772c8`에 있는 이 문서의 지난 내용 4절에 있습니다(`git show 01772c8:docs/gemini_requests/40_시안4_PR9검수결과_머지전에_고칠것_Antigravity.md`).

---

## 4. 수정할 수 있는 파일

요청 35의 8절과 같습니다.

- 수정 가능: `proto_src/console4/`의 `core.js`, `tab1.js`~`tab6.js`, `tab4.src.js`, `style.css`, `tab*.css`, `tpl.html`, `build.py`, `shoot.py`, 빌드 산출물 `site/proto/console4.html`, 기록 `docs/antigravity_log.md`.
- 수정 금지: 데이터 파일(`proto_src/console4/*.json`, 데이터 행을 스크립트가 만드는 부분), `proto_src/graph/`, `proto_src/deck/`, `src/`, `scripts/`, `tests/`, `data/`, `docs/`(기록 파일 제외), `presentation_animation/`.
- 화면에 필요한 값이 데이터에 없으면 화면에서 계산하지 말고 PR 글의 "데이터 요청"에 적습니다.

## 5. 완료 기준

### 고칠 것

1. 3절 스크립트의 `wheel True` 행에서도 `bar_bottom`이 `area_bottom` 이하입니다. `wheel False` 행은 지금처럼 잘림이 없습니다. 선택 700ms 이후나 1500ms 뒤에 굴린 휠의 위치는 자동 스크롤이 덮어쓰지 않습니다.

### 그대로 유지할 것

2. 재빌드 결과가 커밋한 `site/proto/console4.html`과 바이트까지 같습니다. 전체 테스트가 통과합니다(`python -m pytest -q`, 이번 검수 1,512 통과, 1 건너뜀). 데이터 파일을 수정하지 않았습니다(`git diff origin/main --stat -- proto_src/console4/*.json`의 출력 없음).
3. 외부 요청 0건, 콘솔 오류 0건, 가로 오버플로 0px, 휠 스크롤 회귀 없음.
4. 모바일 380x780과 412x915의 상세 전체 화면 시트(닫기 버튼, 상세의 뒤로, 브라우저 뒤로로 닫힘, 뒤 본문으로 스크롤이 새지 않음), 태블릿 1180x820과 1024x768의 동작이 그대로입니다.
5. 지난 1-2의 가장자리 기준이 유지됩니다. 애니메이션 "켬"에서 1920x1080과 1366x768의 여섯 탭 모두 열기와 접기의 `top`과 `bottom`이 한 프레임 12px 이하(380x780은 17.7px 이하), "줄임"에서 `bottom`이 `top`보다 크지 않습니다.
6. 이번에 고쳐진 것(6절)이 다시 나빠지지 않습니다.
   - 스크롤 안내: 스크롤할 것이 없을 때 보이지 않고, 보일 때 글자와 버튼에 겹치지 않으며, 맨 아래로 내리거나 다른 탭으로 가면 숨습니다.
   - Esc 재진입: Esc로 전체 요약에 나간 직후 같은 탭에 다시 들어와도 `pointer-events none` 0회, 실제 마우스 클릭 실패 0회입니다.
   - FLIP의 scaleY: 조건 바꾸기와 범위 패널을 열고 접는 동안 `#z-center`의 `scaleY`가 1.000이고, 아래 영역 가장자리의 한 프레임 이동이 12px 이하입니다.
   - 선택 막대 자동 스크롤: 휠을 굴리지 않을 때 네 해상도에서 잘림 0입니다.
   - 1000px 미만 추가 알림: 보기 버튼 44x44px 이상, 알림 상자는 `pointer-events: none`이고 버튼만 `auto`, 어절 중간 줄바꿈 없음.
   - 380x780 도움말(?) 버튼: 380x780과 412x915의 여섯 화면 모두 제목 줄 한 줄.
   - 접이식 항목 바깥 상자: `details.zr-det`의 `top`과 `bottom` 이동 0.0px.
   - 기록 수치 정정: `docs/antigravity_log.md`에 정정한 값과 "요청 40 재검수에서 정정" 표시가 남아 있습니다.

## 6. 고쳐진 것 (이번 검수에서 확인)

- 스크롤 안내(지난 1-1): 글자 없는 화살표(22x26)로 바뀌어 차트 영역 오른쪽 바깥에 놓입니다. 1920x1080, 1600x900, 1366x768, 1280x800에서 여섯 경로, 조건 바꾸기를 연 상태, 담보 선택 상태를 재어 스크롤할 것이 없는데 보이는 경우 0, 문서 전체의 글자와 버튼에 겹치는 경우 0, 맨 아래로 내리면 숨고 다른 탭으로 가면 숨습니다. 스크롤이 실제로 있는 1366x768 조건 바꾸기(384/341), 1280x800(384/373), 담보 선택 상태(1366x768 384/213, 1600x900 398/330, 1280x800 384/245)에서만 보입니다.
- Esc 재진입 클릭(지난 1-2): 지난 스크립트로 네 데스크톱 해상도에서 해상도마다 45회(대기 150ms) `pointer-events none` 0회, 클릭 실패 0회. 다섯 탭으로 넓혀 매회 실제 마우스 클릭까지 본 테스트도 해상도마다 50회 실패 0회, 1366x768 대기 100ms와 250ms 각 50회도 0회.
- FLIP의 scaleY(지난 2-1): 조건 바꾸기와 범위 패널 열기와 접기에서 `#z-center` `scaleY` 1.000(1366x768, 1920x1080). 아래 영역 가장자리의 한 프레임 이동은 WAAPI를 멈춘 측정으로 최대 11.3px(1920x1080 열기 5.0, 접기 6.3, 1366x768 열기 9.0, 접기 11.3). PR 9번 머지 전의 `main`은 1366x768에서 한 프레임에 173.6px였습니다. 프레임별 캡처에서 고객군과 시장의 링 차트가 찌그러지지 않음을 직접 봤습니다.
- 애니메이션 켬의 선택 막대 자동 스크롤(지난 2-2): 휠을 굴리지 않을 때 네 해상도에서 잘림 0(1366x768 막대 아래 394 대 영역 아래 404, `scrollTop` 40). 휠을 굴리는 경우는 1절에 남았습니다.
- 1000px 미만 영업 인사이트 추가 알림(지난 2-3): 보기 버튼 48x44(380x780, 412x915), 알림 상자 `pointer-events: none`이고 버튼만 `auto`, 알림 아래 목록 행을 탭하면 그 행이 선택됨, 문구 줄바꿈 `['응대 화법에', '추가했습니다(9건)']`으로 어절 중간 줄바꿈 없음.
- 380x780 도움말(?) 버튼(지난 2-4): 380x780과 412x915의 여섯 화면 모두 제목 줄 한 줄(? 버튼 top 131, 다른 버튼 128). PR 9번 머지 전의 `main`은 둘째 줄(top 166).
- 접이식 항목 바깥 상자(지난 2-5): `details.zr-det` top 0.0px, bottom 0.0px 이동, 한 프레임 변화 0.
- 기록 수치 정정(지난 2-6): 611행 부근 6곳 `2106 / 1690px`, 가상 23곳 `7582 / 1690px`, 625행 부근 `#z-right` `top` 0.0px과 `bottom` 350.0px이 "요청 40 재검수에서 정정" 표시와 함께 반영, 이전 절 삭제 없음.

## 7. PR 글에 적을 것

- 1절 고칠 것의 수정 방법. 고치지 않았으면 이유를 적습니다.
- 3절 스크립트의 출력(고치기 전과 후), 그리고 선택 700ms 이후나 1500ms 뒤의 휠이 덮어써지지 않음을 확인한 방법과 결과.
- 5절 "그대로 유지할 것"을 확인한 방법. 프레임 단위로 잰 값은 실시간 측정과 WAAPI를 멈춘 측정 중 어느 쪽인지 밝힙니다(2절).
- 2절 참고 항목을 함께 고쳤다면 그 내용.
