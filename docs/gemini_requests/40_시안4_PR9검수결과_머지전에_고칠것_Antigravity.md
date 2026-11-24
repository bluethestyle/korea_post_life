# 요청 40. 시안 4 PR 9번 재검수 결과(커밋 03ba30b): 머지 전에 고칠 것 2건과 함께 고칠 것 6건 (Antigravity 개발 에이전트용)

분석 화면 시안 4(`site/proto/console4.html`)에 배포 화면 사용자 의견을 반영한 PR 9번(브랜치 `antigravity/console4-feedback`)의 최신 커밋 `03ba30b`를 `main`(`220689c`)에 머지한 결과로 다시 검수했습니다. 지시서는 요청 35(배포 화면 사용자 의견 반영 지시서, `docs/gemini_requests/35_시안4_배포화면_사용자의견_반영_Antigravity.md`)와 그 부록, 그리고 이 문서의 지난 내용(커밋 `6c7f5f3` 기준 검수 결과)입니다.

- 결과: 이번에도 머지하지 않습니다. `03ba30b`에서 새로 생긴 결함 두 건이 이유입니다.
  1. 담보 비교 차트의 스크롤 안내가 스크롤할 것이 없는데도 남아 분야 이름과 막대 이름표를 가립니다(1-1).
  2. Esc로 전체 요약에 나간 직후 같은 탭에 다시 들어오면 그 탭 화면 전체가 클릭되지 않는 경우가 생깁니다(1-2).
- 지난 검수(`6c7f5f3`)의 머지 조건 2건과 함께 고칠 것 11건 가운데 고쳐진 것은 이 문서에서 지웠습니다(7절에 짧게 적음). 일부만 고쳐진 것은 남은 부분만 2절에 새 번호로 실었습니다.
- `503f9e9`(문서 수치 정정)까지는 머지 기준을 모두 충족해 2026-11-25에 그 커밋까지를 `main`에 머지했습니다(커밋 `a65a015`). 그 뒤의 커밋(`03ba30b`)은 아래 두 건이 고쳐지면 머지합니다. 작업을 이어갈 때 `origin/main`을 머지하면 충돌 없이 합쳐집니다.
- 확인 방법: 재빌드 결과와 커밋한 `site/proto/console4.html`의 바이트 비교(6,375,421바이트, 같음), 전체 테스트(1,469 통과, 1 건너뜀), 데이터 파일 변경 여부(0건), Playwright로 해상도별 화면을 열어 프레임마다 위치를 기록하는 측정과 WAAPI 애니메이션을 멈추고 프레임마다 재는 측정, 실제 마우스와 휠 입력, 코드 대조. 머지 조건 두 건은 Claude가 직접 재현했습니다. 함께 고칠 것은 Claude가 직접 확인했거나(2-1, 2-4, 2-6) 점검 에이전트 둘 이상의 실행에서 같은 결과가 나온 것만 실었습니다.
- 행 번호는 `03ba30b`를 `main`에 머지한 결과 기준입니다. 측정 수치는 Claude 쪽 서버에서 애니메이션 설정 "켬"으로 잰 값입니다.

## 사람이 할 일

Antigravity에 이 지시를 넣습니다.

> 브랜치 `antigravity/console4-feedback`에서 `git fetch origin` 뒤 `origin/main`을 머지하고, `docs/gemini_requests/40_시안4_PR9검수결과_머지전에_고칠것_Antigravity.md`를 읽어 수정해 같은 PR(9번)에 커밋을 추가하라. 데이터 파일(`proto_src/console4/*.json`)은 수정하지 않는다.

## 머지 조건

- **머지 조건 2건** (1절): `03ba30b`에서 새로 생겼고 사용자가 바로 알아채는 것. 둘 다 Claude가 직접 재현했고, 직전 커밋 `503f9e9`에는 없습니다.
- **함께 고칠 것 6건** (2절): 머지를 막지 않지만 같은 PR에서 고치면 좋은 것. 고치지 않는 건은 PR 글에 이유를 적습니다.

아래에서 1-2, 2-3처럼 적은 것은 1절 2번, 2절 3번을 뜻합니다. 지난 문서의 번호와 다르며, 지난 번호는 각 항목에 괄호로 적었습니다.

---

## 1. 머지 조건

### 1-1. 담보 비교 차트의 스크롤 안내가 스크롤할 것이 없는데 보여 분야 이름과 겹침

- **현상**: 지난 문서의 2-9에 따라 새로 넣은 차트 아래 안내(`#zc-scroll-cue`, "아래로 스크롤해 기준선과 이름표 보기")가, 고객군과 시장, 인수기준 비교, 영업 인사이트 탭에서 담보 비교로 넘어오면 보입니다. 그때 차트 영역(`#z-center`)에는 안쪽 스크롤이 없습니다. 안내 상자가 차트 아래쪽의 분야 묶음 이름과 기울어진 막대 이름표 위에 놓여 글자를 가립니다. 담보 비교로 바로 들어가거나(`App.set({tab:'cover'})`) 전체 요약에서 들어가면 생기지 않습니다.
- **측정값** (4절 `check40b.py cue`):

  | 해상도 | `#z-center` scrollHeight / clientHeight | 안내 상자 [left, top, width, height] | 가려지는 글자 |
  | --- | --- | --- | --- |
  | 1920x1080 | 452 / 452 (스크롤 없음) | [48, 634, 1824, 24] | 분야 이름 "심장보장", 기울어진 막대 이름표 |
  | 1366x768 | 384 / 384 (스크롤 없음) | [32, 551, 1302, 24] | 분야 이름 "뇌혈관보장", "심장보장", 기울어진 막대 이름표 |

  스크롤이 실제로 있는 1280x800 조건 바꾸기 열림 상태에서도 안내의 아래 그라데이션이 분야 이름 줄과 기울어진 막대 이름표 일부를 가립니다(같은 스크립트의 `cue 1280 800 cond`로 재현, 차트 영역 scrollHeight 384 / clientHeight 373, 안내 상자 [32, 714, 1216, 24]). 직전 커밋 `503f9e9`에는 이 요소가 없습니다.
- **근거**: 화면 공통 기준인 글자 겹침 0. 지난 문서 2-9는 "안쪽 스크롤이 생기는 해상도에서" 아래로 더 있다는 표시를 두라고 했으므로, 스크롤이 없을 때 보이면 안 됩니다.
- **추정 원인과 코드 위치**: `core.js` 2367행 `syncZcScrollCue()`(안내 요소는 2370~2386행에서 만듦). 탭 전환 때 2278행에서 한 번 계산하는데, 앞 탭 화면의 퇴장 애니메이션이나 차트 배치가 끝나기 전의 `scrollHeight`로 판정해 보이게 되고, 배치가 끝난 뒤 다시 계산하지 않아 남는 것으로 보입니다(추정). 위치는 `zc.offsetTop + zc.clientHeight - 24`로 차트 영역 맨 아래 24px에 놓이는데, 그 자리가 분야 이름 줄입니다.
- **고치는 방향**:
  1. 탭에 들어올 때, 패널 애니메이션(조건 바꾸기, 범위 패널, 하단 상세 패널)이 끝날 때, 창 크기가 바뀔 때, 조건 바꾸기와 범위 패널이 바뀔 때, 스크롤할 때마다 다시 계산합니다. `scrollHeight`가 `clientHeight + 1` 이하이면 숨깁니다.
  2. 보일 때도 막대 이름표와 분야 이름 줄을 가리지 않는 자리에 둡니다. 예를 들어 차트 영역 밖(영역 아래 경계선 바로 아래)에 두거나, 안내를 글자 없이 아래 가장자리 그림자만으로 줄이고 그림자가 이름표 위에 걸리지 않게 합니다.

### 1-2. Esc로 전체 요약에 나간 직후 같은 탭에 다시 들어오면 화면 전체가 클릭되지 않음

- **현상**: 탭에서 Esc로 전체 요약에 나가고 약 100~250ms 안에 같은 탭으로 다시 들어오면, 그 탭의 `#view-<탭>`의 계산된 `pointer-events`가 `none`으로 남는 경우가 있습니다. 그러면 실제 마우스 클릭으로 담보나 셀을 선택할 수 없습니다. 4초 뒤에도 그대로이고, 다른 탭을 한 번 거쳐야 풀립니다. 점검 에이전트 기록으로는 그때 그 view의 `style` 속성은 비어 있었습니다.
- **측정값** (4절 `check40b.py reenter`, 대기 시간은 Esc와 재진입 사이):

  | 측정 | 조건 | `03ba30b` | `503f9e9` | `main` |
  | --- | --- | --- | --- | --- |
  | Claude | 1366x768, 대기 150ms, 탭마다 15회 | 담보 비교 2/15, 인수기준 비교 1/15, 고객군과 시장 4/15 (세 탭 모두 그때마다 실제 마우스 클릭으로 선택되지 않음) | 0/45 | 재지 않음 |
  | 점검 에이전트 | 1366x768과 1920x1080, 대기 150ms, 탭마다 20회 | 탭마다 1~6/20 | 0/20 | 0/20 |

  확률로 생기는 결함이라 실행마다 횟수가 다릅니다. 한 번이라도 나오면 재현입니다.
- **근거**: 탭 전환과 선택 동작. Esc를 눌렀다가 곧바로 같은 탭을 다시 클릭하는 것은 흔한 조작이고, 이때 화면이 멈춘 것처럼 보입니다. `main`과 `503f9e9`에서는 0회입니다.
- **추정 원인과 코드 위치** (코드로 확정하지 못함): 지난 문서 2-1(탭 전환에서 앞 화면이 한 프레임에 사라짐)을 고치며 넣은 앞 화면 불투명도 퇴장과, 같은 탭 재진입이 겹칠 때 정리가 빠지는 것으로 보입니다. `renderActiveScreen`(`core.js` 2114행)에서 앞 화면에 `pointerEvents = 'none'`을 주고(전체 요약 쪽 `#board` 2150~2172행, `#home-panel` 2185~2208행, 앞 화면 view 2279~2300행), `tabOutToken`과 `cleanupTabOutAnims`(2105행)로 정리합니다. 퇴장 애니메이션은 `fill: 'forwards'`로 남으므로, 정리 경로가 빠지면 애니메이션 효과나 상위 요소의 값이 남을 수 있습니다.
- **고치는 방향**: 탭에 들어올 때 그 view(와 `#board`, `#home-panel`)에 걸린 퇴장 애니메이션을 취소하고 `pointer-events`와 `opacity`를 되돌립니다. 퇴장 애니메이션의 끝 처리(`onfinish`와 정리 함수)에서는 그 요소가 지금 탭이면 아무것도 하지 않습니다.

---

## 2. 함께 고칠 것

1. **조건 바꾸기와 범위 패널을 열고 접을 때 아래 영역의 글자와 차트가 세로로 늘어남** (지난 1-2의 후속)
   - 현상: 아래쪽 가장자리 기준은 이제 지킵니다(7절). 그러나 FLIP 애니메이션이 아래 영역에 `scaleY`를 겁니다(`core.js` 1333행 열기, 1392~1393행 접기). 1366x768 고객군과 시장에서 열기 첫 프레임의 `#z-center` transform이 `matrix(1, 0, 0, 1.42551, 0, -161.439)`이라 글자와 차트가 세로로 약 1.43배 늘어났다가 400ms 동안 돌아옵니다(120ms에 1.345, 280ms에 1.276). 접기도 같은 방식이라 행 간격이 48px에서 57px까지 늘어 보입니다.
   - 근거: 요청 35 3절의 "부드러운 느낌". 지난 문서 2-3에서 `scaleY`로 글자가 찌그러지는 것을 고치라고 한 것과 같은 이유입니다.
   - 고치는 방향: 글자가 든 영역에는 scale을 걸지 않고, `clip-path`나 `translate`로 보이는 범위를 바꿉니다. 또는 자식에 역보정 scale을 걸어 글자 크기를 유지합니다.

2. **애니메이션 "켬"에서 선택한 막대가 차트 영역 아래로 잘림** (지난 2-9의 남은 부분)
   - 현상: 차트 아래 안내는 들어갔습니다(1-1의 결함은 별개). 그러나 선택한 막대를 보이는 위치로 옮기는 자동 스크롤이 애니메이션 "켬"의 1366x768에서 동작하지 않습니다. 선택할 수 있는 막대 4개 모두 막대 아래 가장자리(434px)가 차트 영역 아래(404px)를 넘어 30px 잘립니다. "끔"에서는 `scrollTop` 62로 동작합니다. 1280x800과 1600x900은 "켬"에서도 영역 안에 들어옵니다. 자동 스크롤이 사용자의 휠을 덮어쓰지는 않습니다(점검 에이전트 확인).
   - 추정 원인: 하단 상세 패널이 열리는 애니메이션 도중, 차트 영역 높이가 아직 줄지 않았을 때 `reveal()`(`core.js` 3324행)이 한 번만 계산하는 것으로 보입니다.
   - 고치는 방향: 하단 상세 패널 애니메이션이 끝난 뒤(또는 최종 높이 기준으로) 선택 막대 위치를 다시 계산해 스크롤합니다.

3. **1000px 미만 영업 인사이트의 추가 알림** (`03ba30b`에서 새로 생김, 지난 2-10의 후속)
   - 현상: 항목을 응대 화법에 추가하면 알림과 보기 버튼이 61~117ms 안에 보입니다(지난 2-10은 고쳐짐). 다만 세 가지가 남았습니다.
     - 보기 버튼(`.toast-act`)이 40x22px로 터치 대상이 작습니다(380x780에서 [229, 716, 40, 22]).
     - 알림이 `pointer-events: auto`(`style.css` 803행 `.toast.on.has-act`)가 되어, 4.2초 동안 아래의 목록 행 버튼(`.lrow-hit`)과 접이식 summary 일부를 가립니다. 직전 커밋까지는 `none`이었습니다.
     - 문구가 "추가했/습니다(9건)"처럼 어절 중간에서 줄바꿈됩니다.
   - 고치는 방향: 보기 버튼의 터치 대상을 44x44px 이상으로 넓힙니다(글자 크기는 그대로 두고 패딩이나 투명한 터치 영역으로). 알림 상자 자체는 `pointer-events: none`으로 두고 버튼에만 `auto`를 주거나, 알림이 목록을 가리지 않는 자리에 둡니다. 문구에는 `word-break: keep-all`을 줍니다.

4. **380x780 전체 요약에서 도움말(?) 버튼만 둘째 줄로 내려감** (`503f9e9`부터)
   - 현상: 화면 도구 버튼이 제목 줄에 들어오면서 줄이 넘쳐, 도움말 버튼 하나만 둘째 줄에 놓입니다. `main`은 한 줄입니다.
   - 고치는 방향: 380px에서 한 줄에 들어가게 간격이나 버튼 묶음을 조정합니다. 두 줄이 필요하면 버튼 하나만 따로 떨어지지 않게 묶음 단위로 내립니다.

5. **상세 패널 접이식 항목(`details.zr-det`)의 바깥 상자 높이가 한 프레임에 바뀜** (지난 2-3의 남은 부분)
   - 현상: 안쪽 본문(`.zr-det-b`)은 `clip-path`로 바꿔 글자 눌림과 사라짐이 없어졌습니다. 그러나 바깥 `details.zr-det`의 bottom이 열기 978.6px, 접기 950.6px 한 프레임에 바뀝니다(4절 `check40.py det`, 1920x1080). 그대로 둔 이유는 기록(`docs/antigravity_log.md` 요청 40 절)에만 있습니다.
   - 고치는 방향: 고치거나(애니메이션 처리는 `core.js` 4211행 부근), 그대로 둔 이유를 PR 글에도 적습니다.

6. **기록(`docs/antigravity_log.md`)의 수치 정정** (지난 2-11의 남은 부분, 행 번호는 `03ba30b`의 기록 파일 기준)

   | 위치 | 지금 적힌 값 | 다시 잰 값 |
   | --- | --- | --- |
   | 611행 부근, 다회사 표로 보기 고정 열의 "현행 실측" | 6곳 `2075 / 1690px`, 가상 23곳 `7360 / 1690px` | 6곳 `2106 / 1690px`, 가상 23곳 `7582 / 1690px` |
   | 625행 부근, 담보 비교 하단 상세 패널 열기 | `1920` `#z-right` `0px` | `top` 0px, `bottom` 350.0px 이동. 위쪽 가장자리만의 값이라는 것과 아래쪽 가장자리 값을 함께 적습니다 |

   기록은 이전 절을 지우지 말고, 고친 값 옆에 "요청 40 재검수에서 정정"을 적습니다.

---

## 3. 참고 (이번 요청에서 고치지 않는 것)

- **실시간 측정의 흔들림**: `requestAnimationFrame`으로 실시간 기록하는 측정은 서버 부하에 따라 프레임이 24~47ms 늦어져 한 프레임 이동 값이 커질 수 있습니다. 기준을 넘는 값이 나오면 WAAPI 애니메이션을 멈추고(`getAnimations()`로 찾아 `pause()` 뒤 `currentTime`을 16.7ms씩 옮김) 프레임마다 재는 측정을 함께 보고 둘 다 적습니다. 이번 검수의 1-2 가장자리 판정(7절)도 이 측정으로 했습니다.
- **33ms 넘는 프레임 수**: 같은 측정을 다시 하면 값이 흔들려 결함으로 단정하지 않습니다. 다시 잴 때는 3회 실행의 가장 나쁜 값을 그대로 적고, 실행한 PC의 CPU와 다른 프로그램 실행 여부를 함께 적습니다.
- **판정 칩의 옛 이름**: 하단 상세 패널과 표로 보기의 회사별 판정 칩은 아직 옛 이름(같음, 우체국 나음 등)입니다. `main`과 같고, 요청 37(화면 문구를 실무 용어로 바꾸는 요청, `docs/gemini_requests/37_시안4_화면문구를_실무용어로_Antigravity.md`)에서 처리합니다.
- **데스크톱에서 상세를 닫기 버튼으로 닫은 뒤 `#z-right`의 `is-picked`가 약 500ms 뒤에 풀림** (`503f9e9`부터): `main`은 즉시 풀립니다. 휠 차단은 재현되지 않았습니다. 고칠 때 함께 보면 됩니다.
- **380x780 영업 인사이트에서 시트를 닫으면 본문 스크롤이 22px 어긋남** (341에서 319, `main`부터): `main`은 수백 px 어긋났으므로 나아졌습니다.

---

## 4. 재현과 확인 스크립트

스크립트 두 개를 저장소 밖의 임시 폴더에 저장하고, 저장소 루트에서 실행합니다(`python <임시 폴더>/check40b.py cue 1920 1080`). Playwright(Chromium)가 필요합니다. 스크립트와 출력은 커밋하지 않습니다.

- `check40.py`: 지난 문서의 스크립트입니다. 코드는 그대로이고 회귀 확인용으로 씁니다. `table`은 여러 회사 화면 `out/console4_all.html`이 있어야 합니다(`proto_src/console4/API.md`의 "명령").
- `check40b.py`: 이번 머지 조건 둘과 2-1, 2-2를 재현합니다.

### `check40.py` (회귀 확인)

| 지난 항목 | 명령 인자 | `03ba30b` 출력(요약) |
| --- | --- | --- |
| 1-1 (고쳐짐) | `back` | `1024 768 메뉴로 접힘 s:STD_CA_TX_CHEMORADIO -> None` (세 해상도 모두 `-> None`) |
| 1-2 (고쳐짐) | `cond 1920 1080 market`, `cond 1366 768 market`, `cond 1366 768 cover`, `cond 1920 1080 brief`, `cond 1920 1080 market calm` | 고객군과 시장, 전체 요약의 아래 영역 `bottom 0.0px`, `top`은 12px 이하. 실시간 측정이라 프레임이 밀리면 12px를 넘을 수 있습니다(3절) |
| 2-1 (고쳐짐) | `tab` | `#view-cover ... 한 프레임에 사라짐 0` |
| 2-2 (고쳐짐) | `bottom 1920 1080`, `bottom 1366 768` | 열기 `#ev-unselected ... 한 프레임에 사라짐 0`, 닫기 `마지막 변화` 607~631ms(부하가 낮을 때) |
| 2-3 (이번 2-5) | `det` | `details.zr-det ... bottom 978.6px` |
| 2-5 (고쳐짐) | `lpcur` | `insight [['고지 범위 상이, 한화생명 간편가입형(1년)', 207, 207]]` 등 말줄임 없음 |
| 2-6 (고쳐짐) | `gate` | `[]` |
| 2-7 (고쳐짐) | `table` | `[['td.cv-n', 'rgb(234, 238, 242)'], …]` (세 배경 알파 1) |
| 2-9 (이번 2-2) | `chart 1600 900`, `chart 1366 768` | `{'scrollHeight': 398, 'clientHeight': 330}`, `{'scrollHeight': 384, 'clientHeight': 213}` (스크롤은 그대로 있고 안내가 들어감) |
| 2-10 (고쳐짐) | `m380` | `'보임': False` (미리 보기 카드 위치는 그대로이고, 대신 추가 뒤 61~117ms에 알림과 보기 버튼이 보임) |

### `check40b.py` (이번 항목)

| 항목 | 명령 인자 | `03ba30b` 출력(요약) | `503f9e9` 출력 |
| --- | --- | --- | --- |
| 1-1 | `cue 1920 1080`, `cue 1366 768` | 고객군과 시장, 인수기준 비교, 영업 인사이트를 거친 경로에서 `"안내": "보임", "스크롤 없음에 보임": true`, `rect` [48, 634, 1824, 24] / [32, 551, 1302, 24], `겹친글자`에 분야 이름. 바로 들어간 경로와 전체 요약 경로는 `"안내": "요소 없음"` | 여섯 경로 모두 `요소 없음` |
| 1-1 | `cue 1280 800 cond` | 스크롤이 있는 정당한 경우. `"스크롤 없음에 보임": false`이지만 `겹친글자`에 분야 이름과 막대 이름표 | |
| 1-2 | `reenter 1366 768 15 150` | 탭에 따라 `pointer-events none`이 몇 회(1-2의 표). 선택 대상에 따로 `pointer-events`가 걸린 탭은 클릭이 통과할 수 있으므로 `pointer-events none` 횟수를 먼저 봅니다 | 다섯 탭 모두 `0/15` |
| 2-1 | `scale 1366 768` | 열기 `scaleY 최대` 1.4 이상(Claude 측정 첫 프레임 1.42551), 접기도 1.02를 넘는 프레임이 이어짐 | |
| 2-2 | `autoscroll 1366 768` | `on`: 막대 4개 모두 `막대_bottom 434, 영역_bottom 404, scrollTop 0, 잘림 30`. `off`: `scrollTop 62, 잘림 0` | |

`cue`의 여섯 경로는 첫 화면(전체 요약)에서 차례로 `App.set`으로 옮겨 다닌 순서입니다. `reenter`의 실제 클릭 대상은 탭마다 첫 선택 대상(담보 막대, 인수기준 셀, 고객군 링, 영업 인사이트 행, 관계 그래프 노드)이고, 선택 성공은 `App.state.sel[탭]`이 비어 있지 않은 것으로 봅니다. `pointer-events none` 뒤의 괄호는 `none`이 어디서 왔는지(인라인 스타일을 가진 상위 요소, 없으면 CSS나 애니메이션)를 적습니다.

```python
"""요청 40 재검수(03ba30b)의 새 항목 재현과 완료 확인. 저장소 루트에서 실행: python check40b.py <항목> [인자]
항목: cue W H [cond] | reenter W H N D | scale W H | autoscroll W H
"""
import asyncio, sys, json
from pathlib import Path
from playwright.async_api import async_playwright

PAGE = Path('site/proto/console4.html').resolve().as_uri()
PICK = {'market': '#z-center .mk-ring', 'gate': '#z-center .gtf-cell', 'cover': '#z-center .cvp-slot:not(.is-miss)',
        'insight': '#z-center .ins-it .lrow-hit', 'graph': '#view-graph .gr-node'}

CUE = r"""() => { const c = document.querySelector('#zc-scroll-cue'), z = document.querySelector('#z-center');
  const sc = [z.scrollHeight, z.clientHeight, Math.round(z.scrollTop)];
  if (!c) return {안내: '요소 없음', 'scroll/client/top': sc};
  const cs = getComputedStyle(c), r = c.getBoundingClientRect();
  const vis = !(c.hidden || cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) && r.width > 0;
  const hits = [];
  if (vis) for (const e of document.querySelectorAll('#z-center *')) {
    if (e.children.length || !e.textContent.trim() || c.contains(e)) continue;
    const b = e.getBoundingClientRect();
    if (b.width && b.right > r.left && b.left < r.right && b.bottom > r.top && b.top < r.bottom) hits.push(e.textContent.trim().slice(0, 12)); }
  return {안내: vis ? '보임' : '숨김', '스크롤 없음에 보임': vis && z.scrollHeight <= z.clientHeight + 1,
    rect: [r.left, r.top, r.width, r.height].map(Math.round), 'scroll/client/top': sc, 겹친글자: hits.slice(0, 6)}; }"""

async def page(p, w, h, motion='on'):
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)
    await ctx.add_init_script(f"try{{localStorage.setItem('postlife-c4-motion','{motion}')}}catch(e){{}}")
    pg = await ctx.new_page(); await pg.goto(PAGE); await pg.wait_for_timeout(1300)
    return b, pg

async def main(a):
    async with async_playwright() as p:
        if a[0] == 'cue':   # 머지 조건 1: 스크롤할 것이 없는데 안내가 보이는가, 보일 때 글자와 겹치는가
            w, h = int(a[1]), int(a[2]); cond = len(a) > 3 and a[3] == 'cond'
            for path in [['cover'], ['brief', 'cover'], ['market', 'cover'], ['gate', 'cover'],
                         ['insight', 'cover'], ['brief', 'market', 'gate', 'cover']]:
                b, pg = await page(p, w, h)
                for t in path:
                    await pg.evaluate("t => App.set({tab: t})", t); await pg.wait_for_timeout(1000)
                if cond: await pg.click('#cond-sum')
                await pg.wait_for_timeout(1500)
                print(w, h, '->'.join(path) + (' +조건 바꾸기' if cond else ''), json.dumps(await pg.evaluate(CUE), ensure_ascii=False))
                await b.close()
        elif a[0] == 'reenter':   # 머지 조건 2: Esc 로 전체 요약에 나간 직후 같은 탭에 다시 들어온 뒤 클릭되는가
            w, h, n, d = int(a[1]), int(a[2]), int(a[3]), int(a[4])
            b, pg = await page(p, w, h)
            for t in ['market', 'gate', 'cover', 'insight', 'graph']:
                stuck = fail = 0; who = set()
                for i in range(n):
                    await pg.evaluate("t => App.set({tab: t})", t); await pg.wait_for_timeout(900)
                    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(d)
                    await pg.evaluate("t => App.set({tab: t})", t); await pg.wait_for_timeout(1500)
                    pe = await pg.evaluate("""t => { const v = document.getElementById('view-' + t);
                      if (getComputedStyle(v).pointerEvents !== 'none') return null;
                      let e = v; while (e && getComputedStyle(e).pointerEvents === 'none') {
                        if (e.style.pointerEvents === 'none') return '#' + e.id + ' (인라인)'; e = e.parentElement; }
                      return '#' + v.id + ' (CSS)'; }""", t)
                    if pe: stuck += 1; who.add(pe)
                    xy = await pg.evaluate("""s => { const e = [...document.querySelectorAll(s)].find(e => e.getBoundingClientRect().width > 0);
                      if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }""", PICK[t])
                    if xy:
                        await pg.mouse.click(*xy); await pg.wait_for_timeout(700)
                        if await pg.evaluate("t => App.state.sel[t] == null", t): fail += 1
                    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
                print(w, h, t, f'대기 {d}ms', f'pointer-events none {stuck}/{n}', f'실제 클릭 선택 실패 {fail}/{n}', sorted(who))
            await b.close()
        elif a[0] == 'scale':   # 2-1: 조건 바꾸기 열기와 접기 동안 #z-center 의 scaleY
            w, h = int(a[1]), int(a[2])
            b, pg = await page(p, w, h)
            await pg.evaluate("App.set({tab: 'market'})"); await pg.wait_for_timeout(1200)
            for name in ['열기', '접기']:
                await pg.evaluate("""() => { const z = document.querySelector('#z-center'); const t0 = performance.now(); window.__s = [];
                  const loop = () => { const m = new DOMMatrix(getComputedStyle(z).transform); const t = performance.now() - t0;
                    window.__s.push([Math.round(t), m.d]); if (t < 700) requestAnimationFrame(loop); }; requestAnimationFrame(loop); }""")
                await pg.click('#cond-sum'); await pg.wait_for_timeout(900)
                s = await pg.evaluate('window.__s')
                worst = max(s, key=lambda x: abs(x[1] - 1))
                print(w, h, name, f'scaleY 최대 {worst[1]:.3f} ({worst[0]}ms)', [x for x in s if abs(x[1] - 1) > 0.02][:3])
            await b.close()
        elif a[0] == 'autoscroll':   # 2-2: 애니메이션 켬에서 선택한 막대가 차트 영역 안에 보이는가
            w, h = int(a[1]), int(a[2])
            for motion in ['on', 'off']:
                b, pg = await page(p, w, h, motion)
                await pg.evaluate("App.set({tab: 'cover'})"); await pg.wait_for_timeout(1000)
                rows = []
                for i in range(4):
                    await pg.locator('#z-center .cvp-slot:not(.is-miss)').nth(i).click(); await pg.wait_for_timeout(1200)
                    rows.append(await pg.evaluate("""() => { const z = document.querySelector('#z-center'), s = z.querySelector('.cvp-slot.is-sel .cvp-bar');
                      const zr = z.getBoundingClientRect(), r = s.getBoundingClientRect();
                      return {막대_bottom: Math.round(r.bottom), 영역_bottom: Math.round(zr.bottom), scrollTop: Math.round(z.scrollTop), 잘림: Math.max(0, Math.round(r.bottom - zr.bottom))}; }"""))
                    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(700)
                print(w, h, motion, rows)
                await b.close()

asyncio.run(main(sys.argv[1:]))
```

`check40.py`의 본문은 지난 내용과 같습니다.

```python
"""요청 40 재현과 완료 확인. 저장소 루트에서 실행: python check40.py <항목> [인자]
항목: back | cond W H TAB [on|calm] | tab | bottom W H | det | lpcur | gate | table | chart W H | m380
"""
import asyncio, sys, json
from pathlib import Path
from playwright.async_api import async_playwright

PAGE = Path('site/proto/console4.html').resolve().as_uri()
ALL6 = Path('out/console4_all.html').resolve().as_uri()  # proto_src/console4/API.md 의 "명령"으로 만드는 여러 회사 화면

REC = r"""(sels) => {
  const box = s => { const e = document.querySelector(s); if (!e) return null;
    let o = 1, a = e; while (a && a.nodeType === 1) { const c = getComputedStyle(a);
      if (a.hidden || c.display === 'none' || c.visibility === 'hidden') return {hid: 1}; o *= +c.opacity; a = a.parentElement; }
    const r = e.getBoundingClientRect(); if (!r.height) return {hid: 1};
    return {top: r.top, bot: r.bottom, op: o}; };
  const t0 = performance.now();
  const snap = () => { const f = {t: performance.now() - t0}; for (const s of sels) f[s] = box(s); return f; };
  window.__f = [snap()];
  const loop = () => { const f = snap(), now = f.t;
    window.__f.push(f); if (now < 1400) requestAnimationFrame(loop); };
  requestAnimationFrame(loop); }"""

def summarize(frames, sels):
    out = {}
    key = lambda f: json.dumps([f.get(s) and {k: round(v, 1) for k, v in f[s].items()} for s in sels])
    last = max([b['t'] for a, b in zip(frames, frames[1:]) if key(a) != key(b)] or [0])
    out['마지막 변화'] = f'{last:.0f}ms'
    for s in sels:
        dt = db = 0; vanish = appear = 0
        for a, b in zip(frames, frames[1:]):
            x, y = a.get(s), b.get(s)
            if not x or not y: continue
            if 'top' in x and 'top' in y:
                dt = max(dt, abs(y['top'] - x['top'])); db = max(db, abs(y['bot'] - x['bot']))
            if 'top' in x and x['op'] > 0.5 and y.get('hid'): vanish += 1
            if x.get('hid') and 'top' in y and y['op'] > 0.5: appear += 1
        out[s] = f'top {dt:.1f}px, bottom {db:.1f}px, 한 프레임에 사라짐 {vanish}, 한 프레임에 나타남 {appear}'
    return out

async def page(p, w, h, motion='on', url=PAGE):
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)
    await ctx.add_init_script(f"try{{localStorage.setItem('postlife-c4-motion','{motion}')}}catch(e){{}}")
    pg = await ctx.new_page(); await pg.goto(url); await pg.wait_for_timeout(1200)
    return b, pg

async def record(pg, sels, trigger):
    await pg.evaluate(REC, sels); await pg.evaluate(trigger); await pg.wait_for_timeout(1500)
    return summarize(await pg.evaluate('window.__f'), sels)

async def main(a):
    async with async_playwright() as p:
        if a[0] == 'back':   # 머지 조건 1
            for w, h in [(1280, 800), (1180, 820), (1024, 768)]:
                b, pg = await page(p, w, h, 'off')
                await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(600)
                await pg.locator('#z-center .cvp-slot').nth(1).click(); await pg.wait_for_timeout(600)
                before = await pg.evaluate('App.state.sel.cover')
                menu = await pg.locator('#act-menu-btn').is_visible()
                if menu: await pg.click('#act-menu-btn'); await pg.wait_for_timeout(300)
                await pg.click('#act-back'); await pg.wait_for_timeout(600)
                print(w, h, '메뉴로 접힘' if menu else '펼침', before, '->', await pg.evaluate('App.state.sel.cover'))
                await b.close()
        elif a[0] == 'cond':   # 머지 조건 2
            w, h, tab = int(a[1]), int(a[2]), a[3]; motion = a[4] if len(a) > 4 else 'on'
            sels = ['#rtabs-wrap', '#home-panel', '#z-left', '#z-center', '#z-right']
            b, pg = await page(p, w, h, motion)
            if tab != 'brief': await pg.evaluate(f"App.set({{tab:'{tab}'}})")
            await pg.wait_for_timeout(1200)
            for name in ['열기', '접기']:
                s = await record(pg, sels, "document.querySelector('#cond-sum').click()")
                print(f'== {name}')
                for k, v in s.items(): print(' ', k, v)
            await b.close()
        elif a[0] == 'tab':
            b, pg = await page(p, 1920, 1080)
            await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(1200)
            s = await record(pg, ['#view-cover', '#view-gate'], "document.querySelector('#tab-gate').click()")
            for k, v in s.items(): print(k, v)
            await b.close()
        elif a[0] == 'bottom':
            w, h = int(a[1]), int(a[2]); sels = ['#ev-unselected']
            b, pg = await page(p, w, h)
            await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(1200)
            for name, trig in [('열기', "document.querySelector('.cvp-slot:not(.is-miss)').click()"),
                               ('닫기', "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")]:
                s = await record(pg, sels, trig)
                print(f'== {name}')
                for k, v in s.items(): print(' ', k, v)
            await b.close()
        elif a[0] == 'det':
            b, pg = await page(p, 1920, 1080)
            await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(1200)
            await pg.evaluate("document.querySelector('.cvp-slot:not(.is-miss)').click()"); await pg.wait_for_timeout(1200)
            await pg.evaluate("document.querySelector('details.zr-det').scrollIntoView({block:'center'})")
            s = await record(pg, ['details.zr-det'], "document.querySelector('details.zr-det > summary').click()")
            for k, v in s.items(): print(k, v)
            await b.close()
        elif a[0] == 'lpcur':
            b, pg = await page(p, 1366, 768, 'off')
            for tab, sel in [('market', '#z-center .mk-ring[data-grid-r="0"][data-grid-c="1"]'),
                             ('insight', '#z-center .ins-it .lrow-hit'), ('cover', '#z-center .cvp-slot')]:
                await pg.evaluate(f"App.set({{tab:'{tab}'}})"); await pg.wait_for_timeout(600)
                await pg.locator(sel).nth(1 if tab == 'cover' else 0).click(); await pg.wait_for_timeout(600)
                print(tab, await pg.evaluate("[...document.querySelectorAll('.lp-cur')].map(e => [e.textContent, e.clientWidth, e.scrollWidth])"))
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
            await b.close()
        elif a[0] == 'gate':
            b, pg = await page(p, 1920, 1080, 'off')
            await pg.evaluate("App.set({tab:'insight'})"); await pg.wait_for_timeout(800)
            print(await pg.evaluate("[...document.querySelectorAll('#z-right .icd-sm')].map(e => e.textContent).filter(t => /열림|닫힘/.test(t))"))
            await b.close()
        elif a[0] == 'table':
            b, pg = await page(p, 1920, 1080, 'off', ALL6)
            await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(600)
            await pg.click('#cv-btn-tbl'); await pg.wait_for_timeout(800)
            await pg.evaluate("document.querySelector('.cv-tw').scrollLeft = 260"); await pg.wait_for_timeout(300)
            print(await pg.evaluate("""() => ['td.cv-n', 'td.cv-vd-sticky', 'th.cv-n'].map(s =>
              [s, getComputedStyle(document.querySelector('#data-modal .cv-t ' + s)).backgroundColor])"""))
            await b.close()
        elif a[0] == 'chart':
            w, h = int(a[1]), int(a[2])
            b, pg = await page(p, w, h, 'off')
            await pg.evaluate("App.set({tab:'cover'})"); await pg.wait_for_timeout(600)
            await pg.evaluate("document.querySelector('.cvp-slot:not(.is-miss)').click()"); await pg.wait_for_timeout(800)
            print(w, h, await pg.evaluate("(() => { const z = document.querySelector('#z-center'); return {scrollHeight: z.scrollHeight, clientHeight: z.clientHeight}; })()"))
            await b.close()
        elif a[0] == 'm380':
            b, pg = await page(p, 380, 780, 'on')
            await pg.evaluate("App.set({tab:'insight'})"); await pg.wait_for_timeout(800)
            await pg.evaluate("document.querySelector('#z-center .ins-it input[type=checkbox]').click()"); await pg.wait_for_timeout(700)
            print(await pg.evaluate("(() => { const c = document.querySelector('#insight-card'); const r = c.getBoundingClientRect(); return {카드_top: Math.round(r.top), 화면높이: innerHeight, 보임: r.top < innerHeight && r.bottom > 0}; })()"))
            await b.close()

asyncio.run(main(sys.argv[1:]))
```

---

## 5. 수정할 수 있는 파일

요청 35의 8절과 같습니다.

- 수정 가능: `proto_src/console4/`의 `core.js`, `tab1.js`~`tab6.js`, `tab4.src.js`, `style.css`, `tab*.css`, `tpl.html`, `build.py`, `shoot.py`, 빌드 산출물 `site/proto/console4.html`, 기록 `docs/antigravity_log.md`.
- 수정 금지: 데이터 파일(`proto_src/console4/*.json`, 데이터 행을 스크립트가 만드는 부분), `proto_src/graph/`, `proto_src/deck/`, `src/`, `scripts/`, `tests/`, `data/`, `docs/`(기록 파일 제외), `presentation_animation/`.
- 화면에 필요한 값이 데이터에 없으면 화면에서 계산하지 말고 PR 글의 "데이터 요청"에 적습니다.

## 6. 완료 기준

### 머지 조건

1. **1-1**: `cue 1920 1080`과 `cue 1366 768`의 여섯 경로 모두 `"스크롤 없음에 보임": true`가 없습니다(안내가 `숨김`이거나 `요소 없음`). 스크롤이 있는 상태(`cue 1280 800 cond`, `cue 1366 768 cond`)에서 안내가 보이면 `겹친글자`가 `[]`입니다. 차트 영역을 끝까지 스크롤하면 안내가 숨습니다.
2. **1-2**: `reenter`를 1366x768과 1920x1080에서, 탭 다섯 x 20회 x 대기 100, 150, 250ms로 실행했을 때 `pointer-events none`이 모두 `0/20`이고 `실제 클릭 선택 실패`도 모두 `0/20`입니다.

### 함께 고칠 것 (고친 건만, 고치지 않은 건은 PR 글에 이유)

3. **2-1**: 애니메이션 "켬"에서 조건 바꾸기와 범위 패널을 열고 접는 동안 글자가 든 요소의 `scaleY`가 1±0.02입니다(`scale 1366 768`, `scale 1920 1080`). 아래 영역의 가장자리 기준(한 프레임 12px 이하, WAAPI를 멈추고 프레임마다 재는 측정)은 그대로 지킵니다.
4. **2-2**: `autoscroll 1366 768`의 `on` 행에서 막대 4개 모두 `잘림`이 0입니다. 1280x800과 1600x900도 0을 유지하고, 자동 스크롤이 사용자의 휠을 덮어쓰지 않습니다.
5. **2-3**: 380x780에서 보기 버튼의 터치 대상이 44x44px 이상(WCAG 2.5.5 권장 크기)이고, 알림이 보이는 동안 아래 목록 행 버튼과 summary가 클릭됩니다. 알림 문구가 어절 중간에서 줄바꿈되지 않습니다.
6. **2-4**: 380x780 전체 요약에서 도움말 버튼만 따로 다음 줄에 놓이지 않습니다. 가로 오버플로 0px.
7. **2-5**: `det`의 `details.zr-det` `bottom`이 12px 이하이거나, 그대로 둔 이유가 PR 글에 있습니다.
8. **2-6**: 2절 6번 표의 두 행이 고쳐져 있습니다.

### 그대로 유지할 것

9. 재빌드 결과가 커밋한 `site/proto/console4.html`과 바이트까지 같습니다. 전체 테스트가 통과합니다(`python -m pytest -q`, 이번 검수 1,469 통과, 1 건너뜀). 데이터 파일을 수정하지 않았습니다(`git diff origin/main --stat -- proto_src/console4/*.json`의 출력 없음).
10. 외부 요청 0건, 콘솔 오류 0건, 가로 오버플로 0px, 휠 스크롤 회귀 없음.
11. 모바일 380x780과 412x915의 상세 전체 화면 시트, 태블릿 1180x820과 1024x768의 동작(7절)이 그대로입니다.
12. 지난 1-2의 가장자리 기준이 유지됩니다. 애니메이션 "켬"에서 1920x1080과 1366x768의 여섯 탭 모두 열기와 접기의 `top`과 `bottom`이 한 프레임 12px 이하(380x780은 17.7px 이하), "줄임"에서 `bottom`이 `top`보다 크지 않습니다.
13. `check40.py`의 다른 항목 출력이 4절 표보다 나빠지지 않습니다.

## 7. 문제없던 것

이번 검수에서 통과한 것입니다. 고치면서 회귀가 생기지 않게 봅니다.

- 지난 문서에서 고쳐진 것:
  - 지난 1-1: 1024x768 메뉴 안의 뒤로 버튼이 `-> None`. 메뉴를 연 채 Esc 1회는 메뉴만 닫고, 2회째에 선택을 해제합니다.
  - 지난 1-2의 가장자리 기준: WAAPI를 멈추고 프레임마다 잰 측정에서 1920x1080 열기 5.0px, 접기 6.3px, 1366x768 9.0px, 11.3px, 380x780 14.8px, "줄임"에서 `bottom`이 `top` 이하. 1366x768 고객군과 시장 열기에서 `#z-center` 아래쪽이 746px에 고정되고 위쪽은 프레임당 9px 이하, 접기도 아래쪽 746px 고정. 범위 패널의 아래 영역 bottom 이동 0px.
  - 지난 2-1(앞 화면이 한 프레임에 사라짐 0), 2-2(열기 사라짐 0, 닫기 마지막 변화 607~631ms), 2-4(`.rtabs.from-home`이 `var(--ease-panel)`), 2-5(말줄임 0, `title` 있음), 2-6(출력 `[]`), 2-7(세 배경 알파 1, 캡처에 잔상 없음), 2-8(◇ 단독 줄바꿈 0/108), 2-10(380x780에서 추가 뒤 61~117ms에 알림과 보기 버튼).
- 휠 스크롤: 1920x1080, 1600x900, 1366x768, 1280x800에서 스크롤 요소 123건을 여러 점에서 끝까지 내리고 올림(실패 0). 상세 머리 위의 휠은 상세 본문을 스크롤하고, 상세 끝에서 더 굴려도 가운데 영역으로 새지 않습니다. 짧은 영역 위에서 굴린 직후 가운데 영역 스크롤 정상. 여섯 회사 표로 보기의 가로 휠과 shift+휠 정상. 점검 에이전트의 격자 99점 차단 0, 패널 개폐 애니메이션 도중 휠 막힘 0.
- 모바일 380x780과 412x915의 상세 전체 화면 시트(24/24): 닫기 버튼, 상세의 뒤로, 브라우저 뒤로 모두 닫힘, 시트 안 끝까지 스크롤, 뒤 본문으로 새지 않음, 닫은 뒤 본문 터치와 휠 스크롤 복귀.
- 태블릿 1180x820과 1024x768: 여섯 화면, 선택, 상세, 조건 바꾸기, 표로 보기, 화면 도구 메뉴 버튼 전부 동작.
- 요청 35 완료 기준 유지: 문서 높이 = 화면 높이, 제목 줄과 탭 줄 고정, 버튼 줄 28px, `#foot` 22px, 요약 바 툴팁, 드래그 탐색 없음, 눈금 클릭으로 선택되지 않음, `.ev-body` 352.3px / 304px, 영업 인사이트 요약 30px와 미리 보기 카드 530.2px.
- 막대 툴팁 판정 칩 389건 x 비교 범위 3종 불일치 0. 여섯 회사(삼성생명, KB라이프생명 포함) 화면과 가상 회사 화면에서 오류, 외부 요청, 가로 오버플로 0.

## 8. PR 글에 적을 것

- 이 문서의 번호(1-1, 1-2, 2절 1~6번)마다 수정 방법. 고치지 않은 것은 이유를 적습니다.
- 4절 두 스크립트의 출력(고치기 전과 후). `reenter`는 6절 2번의 조건 전부(두 해상도, 대기 세 가지)를 적습니다.
- 가장자리와 `scaleY`처럼 프레임 단위로 잰 값은 실시간 측정과 WAAPI를 멈춘 측정 중 어느 쪽인지 밝힙니다(3절).
