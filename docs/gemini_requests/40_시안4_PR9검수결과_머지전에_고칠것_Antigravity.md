# 요청 40. 시안 4 PR 9번 검수 결과: 머지 전에 고칠 것 2건과 함께 고칠 것 11건 (Antigravity 개발 에이전트용)

분석 화면 시안 4(`site/proto/console4.html`)에 사용자의 배포 화면 의견을 반영한 PR 9번(브랜치 `antigravity/console4-feedback`, 커밋 `6c7f5f3`)을 `main`에 머지한 결과로 검수했습니다. 지시서는 요청 35(`docs/gemini_requests/35_시안4_배포화면_사용자의견_반영_Antigravity.md`)와 그 부록입니다.

- 결과: 요청 35의 대부분이 반영됐고 앞 검수에서 남은 11건도 확인했습니다(아래 6절 "문제없던 것"). 다만 머지 조건 2건이 남아 이번에는 머지하지 않습니다.
- 확인 방법: 재빌드 결과와 커밋한 `site/proto/console4.html`의 바이트 비교, 전체 테스트, Playwright로 해상도별 화면을 열어 `requestAnimationFrame`으로 프레임마다 위치를 기록하는 측정, 코드 대조. 점검 에이전트 넷의 지적 가운데 Claude가 같은 명령으로 다시 재서 같은 값이 나온 것만 실었습니다. 측정할 때마다 값이 흔들리는 것은 3절 "참고"로 따로 적었습니다.
- 행 번호는 커밋 `6c7f5f3`을 `main`에 머지한 결과 기준입니다. 측정 수치는 Claude 쪽 서버에서 애니메이션 설정 "켬"으로 잰 값입니다.

## 사람이 할 일

Antigravity에 이 지시를 넣습니다.

> 브랜치 `antigravity/console4-feedback`에서 `git fetch origin` 뒤 `origin/main`을 머지하고, `docs/gemini_requests/40_시안4_PR9검수결과_머지전에_고칠것_Antigravity.md`를 읽어 수정해 같은 PR(9번)에 커밋을 추가하라. 데이터 파일(`proto_src/console4/*.json`)은 수정하지 않는다.

## 머지 조건

- **머지 조건 2건** (1절): 지시서의 완료 기준에 어긋나 사용자가 바로 알아채는 것. 메뉴 안의 뒤로 버튼이 동작하지 않는 것(1번), 조건 바꾸기 패널을 열고 접을 때 아래 영역의 아래쪽 가장자리가 한 프레임에 바뀌는 것(2번).
- **함께 고칠 것 11건** (2절): 머지를 막지 않지만 같은 PR에서 고치면 좋은 것. 고치지 않는 건은 PR 글에 이유를 적습니다.

아래에서 1-2, 2-3처럼 적은 것은 1절 2번, 2절 3번을 뜻합니다.

---

## 1. 머지 조건

### 1-1. 가로 1,000~1,139px에서 메뉴 안의 뒤로 버튼이 동작하지 않음

- **현상**: 1024x768처럼 화면 버튼 그룹이 메뉴 버튼(`#act-menu-btn`)으로 접히는 폭에서, 메뉴를 열고 그 안의 뒤로(`#act-back`)를 클릭하면 메뉴만 닫히고 선택 해제나 단계 이동이 일어나지 않습니다. 다시 메뉴를 열고 눌러도 같습니다. 같은 메뉴의 표로 보기, 요약 복사 같은 다른 버튼은 동작합니다.
- **측정값** (담보 비교에서 둘째 막대를 선택한 뒤 뒤로를 클릭, 4절 스크립트의 `back`):

  | 해상도 | 버튼 그룹 | 클릭 전 `App.state.sel.cover` | 클릭 뒤 |
  | --- | --- | --- | --- |
  | 1280x800 | 펼침 | `s:STD_CA_TX_CHEMORADIO` | `null` (선택 해제) |
  | 1180x820 | 펼침 | `s:STD_CA_TX_CHEMORADIO` | `null` (선택 해제) |
  | 1024x768 | 메뉴로 접힘 | `s:STD_CA_TX_CHEMORADIO` | `s:STD_CA_TX_CHEMORADIO` (그대로, 세 번 눌러도 같음) |

- **근거**: 요청 35 2절 완료 기준 "표의 버튼이 모두 제목 줄에서 동작합니다(화면마다 클릭 결과가 지금과 같음)"와 "1,024x768에서는 화면 버튼 그룹을 메뉴 버튼으로 접은 상태로 한 줄을 유지합니다". PR 글의 "내부 단추 동작 확인"과도 다릅니다.
- **원인**: `#act-back`은 `data-layer-up` 클릭 처리(`core.js` 3692~3693행)에서 `stepUp()`을 부릅니다. `stepUp()`(2949행)의 첫 줄이 `if (closeActMenu()) { ...; return true; }`라서, 버튼을 누르는 순간 메뉴가 열려 있으면 메뉴 닫기 한 단계로 끝납니다.
- **고치는 방향**: 메뉴 안의 버튼을 클릭했을 때는 메뉴를 닫고 그 버튼의 동작을 이어서 실행합니다. 예를 들어 `data-layer-up` 클릭 처리에서 클릭한 버튼이 메뉴(`#th-act-btns`) 안에 있으면 `closeActMenu()`를 먼저 부르고 `stepUp()`을 실행합니다. Esc(3822~3823행)는 지금처럼 메뉴가 열려 있으면 메뉴만 닫습니다(한 번에 한 단계씩 올라가는 Esc 규칙은 유지).

### 1-2. 조건 바꾸기 패널을 열고 접을 때 아래 영역의 아래쪽 가장자리가 한 프레임에 바뀜

- **현상**: 패널과 탭 줄은 요청 35대로 이어서 움직입니다. 그러나 화면 높이에 맞춰 늘어난 아래 영역(`#z-center`, `#z-right`, 전체 요약의 `#home-panel`)은 열 때 첫 프레임에 아래쪽 가장자리가 패널 높이만큼 위로 올라가, 그 아래가 빈 채로 보였다가 위아래가 함께 내려옵니다. 접을 때는 반대로 애니메이션이 끝나는 프레임에 아래쪽 가장자리가 한 번에 내려갑니다. 머지 전 화면은 영역 전체가 한 프레임에 97px 이동했으므로 위쪽 가장자리는 나아졌지만, 사용자가 말한 갑작스러움이 아래쪽 가장자리에 남았습니다.
- **프레임 기록** (1920x1080, 고객군과 시장, 열기, `#z-center`의 `[top, bottom]` px): 클릭 전 `[208, 1058]`, 첫 프레임 `[208, 961]`(아래쪽만 -97px), 그 뒤 위아래가 함께 프레임당 1~5px씩 내려가 `[305, 1058]`에서 멈춥니다. 최종 레이아웃을 먼저 잡고 `translate`로 위쪽만 이어 보이게 해서, 아래쪽 97px가 첫 프레임에 비었다가 채워지는 것입니다.
- **측정값** (4절 스크립트의 `cond`, 한 프레임 최대 이동, 위쪽 가장자리 / 아래쪽 가장자리):

  | 해상도, 탭 | 요소 | 열기 | 접기 |
  | --- | --- | --- | --- |
  | 1920x1080 고객군과 시장, 인수기준 비교, 영업 인사이트, 관계 그래프 | `#z-center`, `#z-right` | 5.1px / **97.0px** | 6.3px / **96.9px** |
  | 1920x1080 전체 요약 | `#home-panel` | 5.1px / **97.0px** | 6.3px / **96.9px** |
  | 1920x1080 담보 비교 | `#z-center`, `#z-right` | 5.1px / 5.1px | 6.3px / 6.3px |
  | 1366x768 고객군과 시장 | `#z-center`, `#z-right` | 9.1px / **173.6px** | 11.3px / **173.4px** |
  | 1366x768 전체 요약 | `#home-panel` | 9.1px / **173.6px** | 11.3px / **173.4px** |
  | 1366x768 담보 비교 | `#z-center` | 9.1px / **42.9px** | 11.3px / **42.7px** |
  | 1920x1080 고객군과 시장, 애니메이션 "줄임" | `#z-center` | 9.1px / **97.0px** | 11.2px / **94.1px** |
  | 1366x768 고객군과 시장, 애니메이션 "줄임" | `#z-center` | 16.5px / **173.6px** | 20.1px / **168.4px** |

  380x780은 위쪽과 아래쪽 가장자리 모두 17.6px 이하로, 이 현상이 없습니다.
- **근거**: 요청 35 3절 바꿀 내용 4번("패널이 열릴 때 아래 영역이 어떻게 줄어드는지도 같은 방식으로 이어지게 합니다")과 완료 기준(한 프레임 최대 이동 12px 이하, 닫기에도 한 프레임에 끝나는 변화 없음). PR 글 2절 전환별 측정표의 1366x768 두 행 패널 값(9.05px, 11.26px)은 `#rtabs-wrap` 한 요소의 값이고 아래 영역의 아래쪽 가장자리는 빠져 있습니다.
- **원인**: `core.js` 1273행 `animateTopBand`. 열 때는 `#cond`를 보이게 해서 최종 레이아웃을 잡은 뒤 아래 요소(`belowElementsOf`, 1245행)에 `translate`만 줍니다. 아래 영역은 요청 35 1절에 따라 높이가 화면에 맞춰지므로 패널이 열리면 높이가 줄고(1920x1080에서 850px에서 753px), 그 차이가 첫 프레임에 아래쪽 가장자리에 나타납니다. 접을 때는 애니메이션 동안 패널을 남겨 두었다가 끝(`onfinish`, 1367행 `el.hidden = true`)에서 숨기므로 그 프레임에 높이가 한 번에 늘어납니다.
- **고치는 방향**: 요청 35 3절 4번의 규칙(위치와 크기는 `transform`, `opacity`, `clip-path`로만 애니메이션하고 높이를 직접 전환하지 않음)을 지키면서, 보이는 아래쪽 가장자리가 화면 아래에 붙어 있게 합니다. 한 가지 방법은 다음과 같습니다.
  1. 애니메이션을 시작할 때 아래 영역의 높이를 열기 전과 뒤 가운데 큰 값(`H`)으로 한 번 정해 두고, 끝날 때 한 번 풉니다. 높이를 프레임마다 바꾸는 것이 아니므로 높이 전환에 해당하지 않습니다.
  2. 위쪽 가장자리는 지금처럼 `translateY`로 이전 위치에서 새 위치로 옮기고, 같은 곡선과 시간으로 `clip-path: inset(0 0 d 0)`의 `d`를 바꿔 `위쪽 위치 + H - d`가 매 프레임 화면 아래(1920x1080에서 1058px)와 같게 합니다. 열 때는 `d`가 0에서 패널 높이만큼, 접을 때는 패널 높이에서 0으로 갑니다.
  3. 끝나는 프레임에 높이 고정과 `clip-path`를 함께 풀어, 보이는 위치가 바뀌지 않게 합니다.

  다른 방법을 써도 됩니다. 아래 6-2의 기준을 지키면 됩니다. 영역 안의 내용(차트, 목록)이 높이 고정을 풀 때 다시 배치되며 움직이지 않는지도 함께 봅니다.

---

## 2. 함께 고칠 것

1. **탭 전환에서 앞 화면이 한 프레임에 사라짐**
   - 현상: 담보 비교에서 인수기준 비교 탭을 클릭하면 앞 화면(`#view-cover`)은 클릭 다음 프레임에 숨고, 새 화면(`#view-gate`)은 불투명도 0에서 400ms로 들어옵니다. 새 화면의 불투명도가 16.7ms에 0.01, 50ms에 0.07, 100ms에 0.2, 200ms에 0.5라서 처음 100ms 남짓은 본문이 거의 빈 화면으로 보입니다.
   - 측정값: 1920x1080 담보 비교에서 인수기준 비교와 영업 인사이트로, 전체 요약에서 담보 비교로 가는 세 전환 모두 앞 화면이 한 프레임에 사라집니다(4절 `tab`: `#view-cover` 한 프레임에 사라짐 1). 1366x768도 같습니다.
   - 근거: 요청 35 3절 완료 기준 "닫기에도 열기와 같은 종류의 애니메이션이 있습니다(한 프레임에 사라지는 전환 0개)", 부록 4.1절의 탭 전환. PR 글 2절 전환별 측정표의 탭 전환 행은 들어오는 쪽의 수치만 적었습니다.
   - 원인: `core.js` 2099행 `v.hidden = x !== st.tab`.
   - 고치는 방향: 앞 화면을 짧게(예: 120~160ms) 불투명도로 내보내면서 새 화면이 들어오게 겹치거나(크로스페이드), 새 화면이 첫 프레임부터 충분히 보이게 시작 불투명도와 곡선을 조정해 빈 화면 구간을 없앱니다.

2. **담보 비교 하단 상세 패널: 안내 문구가 한 프레임에 사라지고, 닫기 전체 시간이 600ms를 넘음**
   - 현상: 막대를 선택해 하단 상세 패널을 열면 그 자리의 한 행짜리 안내 문구(`#ev-unselected`, 높이 32.3px)가 첫 프레임에 사라집니다. 닫을 때는 600ms 접힘이 끝난 뒤 안내 문구가 이어서 나타나 전체가 600ms를 넘습니다.
   - 측정값: 4절 `bottom`. 열기에서 `#ev-unselected` 한 프레임에 사라짐 1(1920x1080, 1366x768). 닫기 마지막 변화 시각 820~858ms(Claude 재측정 여러 번), 점검 에이전트 측정 801~839ms. 패널 본문(`#zr-in`)은 기준을 지킵니다.
   - 근거: 요청 35 3절 완료 기준(한 프레임에 사라지는 전환 0개, 시간은 600ms 이하). PR 글 2절 전환별 측정표는 1920x1080의 `#z-right` 한 프레임 이동을 0px로 적었는데, 보이는 상자에서는 안내 문구 32.3px가 한 프레임에 빠집니다.
   - 원인: `core.js` 2382행 `setEvPicked`. 오른쪽 열 배치(`side`)에서는 안내 문구를 불투명도로 내보내지만(`fadeUnsel`), 담보 비교의 아래 배치(`band`)에서는 2405행에서 `unsel.hidden = true`로 바로 숨깁니다.
   - 고치는 방향: 아래 배치에서도 안내 문구를 불투명도로 내보냅니다. 닫을 때는 안내 문구가 들어오는 애니메이션을 접힘과 겹쳐 전체가 600ms 안에 끝나게 합니다.

3. **(경미) 상세 패널의 접이식 항목(`details.zr-det`) 높이가 한 프레임에 바뀜**
   - 현상: 접이식 항목을 열면 본문(`.zr-det-b`)만 `scaleY(0)`에서 `scaleY(1)`로 움직이고(`core.js` 3622~3636행), `details` 상자의 높이는 한 프레임에 978.6px 바뀝니다(4절 `det`, 1920x1080). 스크롤 영역 안이고 아래에 요소가 없어 눈에 띄는 이동은 거의 없지만, 스크롤 막대 길이가 한 번에 바뀌고 펼치는 동안 글자가 세로로 눌렸다가 늘어납니다.
   - 근거: 높이 직접 전환 금지는 지켰습니다. `scaleY`로 글자가 찌그러지는 것은 요청 35 3절의 "부드러운 느낌"에 맞지 않습니다.
   - 고치는 방향: 본문을 `scaleY` 대신 `clip-path: inset(0 0 100% 0)`에서 `inset(0)`으로 펼치고 불투명도를 함께 바꿉니다. 그대로 둔다면 PR 글에 이유를 적습니다.

4. **(경미) 탭 줄 입장 애니메이션의 곡선**
   - 현상: 전체 요약에서 탭으로 들어갈 때의 탭 줄 애니메이션(`style.css` 298행 `.rtabs.from-home`, `rtabsShrinkIn` 240ms)이 요청 28의 들어옴 곡선(`var(--ease)`, `cubic-bezier(0.16, 1, 0.3, 1)`)을 씁니다. 다른 큰 영역 전환(조건 바꾸기, 범위 패널, 팝오버, 모달, 상세 패널, 필터)은 모두 `--ease-panel`입니다.
   - 근거: 요청 35 3절 2번은 큰 영역 전환에 요청 28의 곡선을 쓰지 않고, 도형 애니메이션에는 그대로 쓴다고 했습니다. 탭 줄의 위치와 크기를 바꾸는 이 애니메이션이 어느 쪽인지 지시서만으로는 분명하지 않습니다.
   - 고치는 방향: 탭 줄은 큰 영역이므로 `var(--ease-panel)`로 바꾸는 것을 권합니다. 요청 28 곡선을 유지한다면 PR 글에 도형 애니메이션으로 본 이유를 적습니다.

5. **제목 줄 경로(`.lp-cur`)에 말줄임이 새로 생김**
   - 현상: 버튼 줄이 제목 줄로 올라오면서 경로 마지막 항목의 폭이 줄었습니다. 1366x768에서 영업 인사이트 항목을 선택하면 "고지 범위 상이, 한화생명 간편가입형(1년)"이 "고지 범위 상이, 한화생…"으로 보입니다.
   - 측정값 (4절 `lpcur`, 1366x768, `clientWidth / scrollWidth` px): 고객군과 시장 124 / 126, 영업 인사이트 124 / 207, 담보 비교 146 / 148. 머지 전 화면은 126 / 126, 207 / 207, 148 / 148로 잘림이 없었습니다. 1180x820과 1024x768에서는 폭이 64~86px입니다.
   - 근거: 요청 35 2절 완료 기준 "버튼과 조건 요약 문장이 잘리지 않습니다". 제목과 상세 패널에 전체 이름이 있어 읽을 수는 있습니다.
   - 고치는 방향: 2px 차이는 경로 영역의 최소 폭이나 간격 조정으로 없앱니다. 긴 이름이 잘리는 경우는 `title` 속성(호버 툴팁)으로 전체 이름을 보이게 합니다(`style.css` 860행).

6. **응대 화법 미리 보기의 인수기준 문장에 "함께 열림"이 남음**
   - 현상: 영업 인사이트 오른쪽 미리 보기의 문장이 "50세 남성, 이력 없음: 함께 열림. 우체국 가입 가능, 한화생명 가입 가능, 삼성화재 가입 가능. …"입니다(4절 `gate`, 1920x1080). 같은 문장에서 회사 상태는 "가입 가능"으로 바꿨는데 앞부분의 고객군 라벨만 바뀌지 않았습니다.
   - 근거: 요청 35 9절(열림, 닫힘은 가입 가능, 가입 제한). 이번 PR이 손댄 문장입니다. `sales.json`의 `표시명`에 `"함께 열림": "함께 가입 가능"`이 이미 있습니다.
   - 원인: `tab5.js` 244행 `gateLine()`이 `${cell['라벨']}`을 표시명 사전을 거치지 않고 씁니다.
   - 고치는 방향: 같은 파일 18행의 `dispMap`을 거쳐 `${dispMap[cell['라벨']] || cell['라벨']}`로 씁니다. 요청 37의 교체표도 이 자리를 `App.label(cell['라벨'])`로 바꾸는데, 두 방식의 결과 글자는 같습니다.

7. **표로 보기의 고정 열 배경이 반투명**
   - 현상: 여러 회사 화면(`out/console4_all.html`, `proto_src/console4/API.md`의 "명령"으로 만드는 화면)과 가상 23곳 화면의 표로 보기에서 가로로 밀면, 고정한 담보 열과 판정 열 뒤로 회사 열의 값이 흐릿하게 비칩니다(예: 암 수술비 행에 "1년 50%" 잔상, 담보 머리글 뒤에 회사 머리글 잔상). 표 좌우 여백(`.cv-tw`의 `padding: 0 10px`)에는 밀려난 셀의 잘린 글자("30" 등)와 빗금 셀이 잘린 채 보입니다.
   - 측정값: 4절 `table`. `td.cv-n`, `td.cv-vd-sticky`, `th.cv-n`의 배경이 모두 `rgba(234, 238, 242, 0.95)`입니다.
   - 원인: `tab4.css` 235~236행의 고정 열 배경이 `var(--panel-t)`(밝은 화면 `rgba(234,238,242,.95)`, 다크 모드 `rgba(20,27,35,.96)`)입니다.
   - 고치는 방향: 고정 열에는 불투명한 배경을 씁니다(밝은 화면과 다크 모드 모두). 좌우 여백으로 밀려난 셀이 보이지 않게 여백 쪽도 가립니다.

8. **(경미) 세 회사 표로 보기의 삼성화재 열에서 ◇ 표식만 줄바꿈됨**
   - 현상: 1280x800 세 회사 화면의 표로 보기에서 삼성화재 열의 "가입금액의 100%" 뒤 ◇ 표식만 줄바꿈되어 셀의 둘째 행 맨 앞에 놓입니다(암 수술비, 유방암 절제수술비, 암 로봇수술비, 암 입원일당 등). 가로 스크롤 없이 판정 열까지 넣으려 열 폭을 줄인 결과로 보이며 값은 읽힙니다.
   - 고치는 방향: 금액과 ◇ 표식을 `white-space: nowrap`으로 묶어 함께 줄바꿈되게 합니다.

9. **1600x900에서도 차트 영역 안쪽 스크롤이 생기는데 스크롤 안내가 없음**
   - 현상: 담보 비교에서 막대를 선택해 하단 상세 패널을 열면 차트 영역(`#z-center`)에 안쪽 세로 스크롤이 생깁니다. 1366x768에서는 선택한 막대의 아래쪽(y 385~434)이 차트 영역 아래 끝(y 404)에서 잘리고, 기준선과 이름표는 스크롤해야 보입니다. 아래에 더 있다는 표시가 없고 스크롤 막대는 얇습니다(`scrollbar-width: thin`).
   - 측정값 (4절 `chart`, `scrollHeight / clientHeight` px): 1920x1080 452 / 452(스크롤 없음), 1600x900 398 / 330, 1366x768 384 / 213, 1280x800 384 / 245. 1600x900에서는 세 회사 화면의 담보 389건 모두 안쪽 스크롤이 생깁니다.
   - 근거: 요청 35 5절은 1366x768과 1280x800에서 안쪽 스크롤을 허용했고, 부록 7.5절은 1600x900이 여백 축소로 들어간다고 계산했습니다. PR 글도 1366x768과 1280x800만 적었습니다(1절의 "`5절`" 항목).
   - 고치는 방향: 1600x900은 여백을 줄여 스크롤 없이 들어가게 하거나, 들어가지 않으면 PR 글에 적습니다. 안쪽 스크롤이 생기는 해상도에서는 아래로 더 있다는 표시(아래 가장자리 그림자 등)를 두고, 선택한 막대가 잘리면 보이는 위치로 스크롤합니다.

10. **(참고 수준) 380x780 영업 인사이트에서 항목을 추가해도 미리 보기가 보이지 않음**
    - 현상: 380x780에서는 미리 보기 카드가 목록 아래 페이지 맨 끝(y 약 9,650px)에 있어, 항목을 응대 화법에 추가해도 화면 안에서 아무 변화가 보이지 않습니다(4절 `m380`: `보임: False`).
    - 근거: 요청 35 6절 5번의 기준(추가 뒤 600ms 안에 미리 보기가 보임)은 데스크톱에 적용하는 기준이라 기준 위반은 아닙니다. 데스크톱 네 해상도에서는 통과했습니다.
    - 고치는 방향: 380px에서는 추가한 뒤 짧은 알림(예: "응대 화법에 추가했습니다(N건). 보기" 버튼)으로 추가 결과를 알리고, 버튼을 누르면 미리 보기로 이동합니다. 고치지 않는다면 PR 글에 적습니다.

11. **기록(`docs/antigravity_log.md`)과 PR 글의 수치 정정**

    | 위치 | 지금 적힌 값 | 다시 잰 값 |
    | --- | --- | --- |
    | PR 글 2절 전환별 측정표, 조건 바꾸기 1366x768 두 행 패널 | 한 프레임 최대 이동 9.05px, 11.26px | `#rtabs-wrap`는 9.1px, 11.3px로 같으나 같은 전환에서 아래 영역의 아래쪽 가장자리가 173.6px(담보 비교 `#z-center`는 42.9px) 한 프레임에 바뀜. 1-2를 고친 뒤 아래 영역의 위쪽과 아래쪽 가장자리를 함께 적습니다 |
    | PR 글 2절 전환별 측정표, 담보 비교 하단 상세 | 1920x1080 `#z-right` 0px | 보이는 상자에서 안내 문구 32.3px가 한 프레임에 빠짐(2절 2번) |
    | PR 글 2절 전환별 측정표, 표로 보기 모달 열기 | 100ms 진행률 7.9% | 16.6~20.1%(1920x1080, 1366x768 각 3회). 기준 50% 이하는 지킵니다 |
    | PR 글 2절 전환별 측정표, 탭 전환 | 들어오는 쪽만 적음 | 앞 화면이 한 프레임에 사라짐(2절 1번) |
    | PR 글 1절의 "`5절` 전수 담보 첫 구역 표시" 항목 | 차트 안쪽 스크롤을 1366x768, 1280x800만 적음 | 1600x900도 389건 모두 안쪽 스크롤(398 / 330px, 2절 9번) |
    | PR 글 1절의 "`7-1` 다회사 표로 보기" 항목, 기록 611행 | 여러 회사 화면 표 `scrollWidth` 2094px(1920x1080, 1366x768), 가상 23곳 7380px | 2126px, 7602px |
    | 기록 494행(이전 절) | 응대 카드 윗변 1920x1080 369.5px, 1600x900 392.8px | 머지 전 화면 실측 394.8px, 394.8px(요청 35 7절 6번에서 1366x768 한 행만 고쳤고 이 두 값이 남음) |
    | 기록 619행 | 조건 바꾸기 접기의 33ms 넘는 프레임 "0개 (연속 부하 시 1개)" | PR 글은 "0개". 두 곳을 같은 값으로 맞춥니다 |
    | 기록 557행, 561행 | 인수기준 비교(기록 표기 "가입 관문") 본문 텍스트 노드 수의 대상 "4곳, 가상 21곳", "재검수 스크립트 기준 50" | 지금의 `out/` 화면은 6곳과 가상 23곳이고, `shoot.py` 재측정 값은 6곳 47, 가상 23곳 47, 3곳 58. 50은 다시 재면 나오지 않습니다. 대상 화면 이름을 지금 화면으로 고치고, 50은 앞 검수 때의 값이라는 것을 밝힙니다 |

    기록은 이전 절을 지우지 말고, 고친 값 옆에 "요청 40에서 정정"을 적습니다.

---

## 3. 참고 (이번 요청에서 고치지 않는 것)

- **33ms 넘는 프레임 수**: 같은 측정을 다시 하면 값이 흔들립니다. Claude 재측정(보통 속도, 3회)에서 담보 선택은 회마다 3, 5, 5개(점검 에이전트는 2, 2, 2개), 조건 바꾸기 열기는 1, 0, 0개, 접기는 0, 0, 1개였습니다. PR 글의 `shoot.py --frames` 3회 최악값(`cover_step` 0개, `cover_scrub` 0개, `gate_pick` 1개, `graph_expand` 1개)도 점검 에이전트의 재실행(최대 1, 2, 0, 0개)과 다르고, CPU 4배 느림의 최악값(`cover_pick` 11, `cover_scrub` 19 등)은 점검 에이전트와 Claude의 재실행에서 재현되지 않았습니다(최대 4개). 머신과 부하 차이일 수 있어 결함으로 단정하지 않습니다. 다시 잴 때는 3회 실행의 가장 나쁜 값을 그대로 적고, 실행한 PC의 CPU와 다른 프로그램 실행 여부를 함께 적습니다.
- **380x780 조건 바꾸기 패널의 아래 영역**: 점검 에이전트의 면적 지표로는 `#z-center` 494.9px가 한 프레임에 바뀌는 것으로 나왔지만, 위쪽과 아래쪽 가장자리를 프레임마다 직접 재면 17.6px 이하입니다(4절 `cond 380 780 cover`). 이번 머지 조건에서 뺐습니다. 1-2를 고친 뒤 이 값이 나빠지지 않는지만 봅니다.
- **담보 비교 하단 상세 패널의 회사별 판정 칩**: 막대 툴팁의 판정 칩은 판정표의 표시명(동일, 우체국 우위, 단순 비교 불가 등)과 389건 모두 일치합니다. 하단 상세 패널과 표로 보기의 회사별 칩은 아직 옛 판정 이름(같음, 우체국 나음, 우열을 매기지 않음 등)입니다. `main`과 같고 이번 PR이 건드리지 않았으며, 요청 37(`docs/gemini_requests/37_시안4_화면문구를_실무용어로_Antigravity.md`)의 5-4절과 판정 칩 함수 `ui.verdict`를 거치는 출력 자리 표에서 처리합니다.

---

## 4. 재현과 확인 스크립트

아래 스크립트를 저장소 밖의 임시 폴더에 `check40.py`로 저장하고, 저장소 루트에서 실행합니다(`python <임시 폴더>/check40.py back`). Playwright(Chromium)가 필요합니다. `table`은 여러 회사 화면 `out/console4_all.html`이 있어야 합니다(`proto_src/console4/API.md`의 "명령"). 스크립트와 출력은 커밋하지 않습니다.

| 항목 | 명령 인자 | 지금 출력(요약) |
| --- | --- | --- |
| 1-1 | `back` | `1024 768 메뉴로 접힘 s:STD_CA_TX_CHEMORADIO -> s:STD_CA_TX_CHEMORADIO` |
| 1-2 | `cond 1920 1080 market`, `cond 1366 768 market`, `cond 1366 768 cover`, `cond 1920 1080 brief`, `cond 1920 1080 market calm` | `#z-center top 5.1px, bottom 97.0px` 등(1-2의 표) |
| 2-1 | `tab` | `#view-cover ... 한 프레임에 사라짐 1` |
| 2-2 | `bottom 1920 1080`, `bottom 1366 768` | 열기 `#ev-unselected ... 한 프레임에 사라짐 1`, 닫기 `마지막 변화 820~858ms` |
| 2-3 | `det` | `details.zr-det ... bottom 978.6px` |
| 2-5 | `lpcur` | `insight [['고지 범위 상이, 한화생명 간편가입형(1년)', 124, 207]]` 등 |
| 2-6 | `gate` | `['50세 남성, 이력 없음: 함께 열림. …']` |
| 2-7 | `table` | `[['td.cv-n', 'rgba(234, 238, 242, 0.95)'], …]` |
| 2-9 | `chart 1600 900`, `chart 1366 768` | `{'scrollHeight': 398, 'clientHeight': 330}` 등 |
| 2-10 | `m380` | `{'카드_top': 9656, '화면높이': 780, '보임': False}` |

`cond`의 탭 이름은 `brief`(전체 요약), `market`(고객군과 시장), `gate`(인수기준 비교), `cover`(담보 비교), `insight`(영업 인사이트), `graph`(관계 그래프)입니다. 다섯째 인자 `calm`은 애니메이션 설정 "줄임"입니다. 한 프레임 이동은 연속한 두 `requestAnimationFrame` 기록 사이의 차이라서, 프레임이 빠지면 값이 커질 수 있습니다. 기준을 넘는 값이 나오면 두세 번 다시 잽니다.

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

1. **1-1**: `back`의 1024x768 행이 `메뉴로 접힘 s:STD_CA_TX_CHEMORADIO -> None`입니다. 1280x800과 1180x820 행은 지금처럼 `-> None`입니다. 1024x768에서 메뉴를 연 채 Esc를 누르면 메뉴만 닫히고, 한 번 더 누르면 선택이 해제됩니다.
2. **1-2**: 애니메이션 설정 "켬"에서 `cond`를 1920x1080과 1366x768의 여섯 탭(`brief`, `market`, `gate`, `cover`, `insight`, `graph`) 모두에 실행했을 때, 열기와 접기 모두 `#rtabs-wrap`, `#home-panel`, `#z-left`, `#z-center`, `#z-right`의 `top`과 `bottom`이 12px 이하입니다(세 번 실행한 가장 나쁜 값). 380x780은 17.7px 이하(요청 35 3절의 이동 거리 3.5% 기준)를 유지합니다. "줄임"(`calm`)에서는 이동 거리 기준을 적용하지 않고, 같은 요소의 `bottom`이 `top`보다 크지 않습니다(아래쪽 가장자리가 위쪽 가장자리와 함께 움직임).

### 함께 고칠 것 (고친 건만)

3. **2-1**: `tab`에서 `#view-cover`의 "한 프레임에 사라짐"이 0입니다. 전체 요약에서 담보 비교, 담보 비교에서 영업 인사이트로 가는 전환도 앞 화면이 한 프레임에 사라지지 않습니다.
4. **2-2**: `bottom 1920 1080`과 `bottom 1366 768`에서 열기의 `#ev-unselected` "한 프레임에 사라짐"이 0이고, 닫기의 "마지막 변화"가 633ms(600ms에 두 프레임을 더한 값) 이하입니다.
5. **2-3**: `det`의 `details.zr-det` `bottom`이 12px 이하이거나, 그대로 둔 이유가 PR 글에 있습니다.
6. **2-4**: `.rtabs.from-home`이 `var(--ease-panel)`을 쓰거나, 요청 28 곡선을 둔 이유가 PR 글에 있습니다.
7. **2-5**: `lpcur`의 세 행 모두 `clientWidth`가 `scrollWidth` 이상이거나, 잘리는 행에 전체 이름의 `title`이 있습니다.
8. **2-6**: `gate`의 출력이 `[]`입니다(미리 보기 문장에 "열림", "닫힘"이 없음).
9. **2-7**: `table`의 세 배경의 알파 값이 1이고, 밝은 화면과 다크 모드에서 가로로 260px 민 표의 캡처에 고정 열 뒤 잔상과 좌우 여백의 잘린 글자가 없습니다.
10. **2-8**: 1280x800 세 회사 표로 보기에서 ◇ 표식만 따로 줄바꿈된 셀이 0개입니다.
11. **2-9**: `chart 1600 900`의 `scrollHeight`가 `clientHeight` 이하이거나, 안쪽 스크롤이 생기는 해상도에서 아래로 더 있다는 표시가 보이고 선택한 막대 전체가 차트 영역 안에 보입니다.
12. **2-10**: 380x780에서 항목을 추가한 뒤 700ms 안에 추가 결과가 화면 안에 보이거나(미리 보기 또는 알림), 고치지 않은 이유가 PR 글에 있습니다.
13. **2-11**: 2절 11번 표의 모든 행이 고쳐져 있습니다.

### 그대로 유지할 것

14. 재빌드 결과가 커밋한 `site/proto/console4.html`과 바이트까지 같습니다. 전체 테스트가 통과합니다(`python -m pytest -q`, 이번 검수 1,469 통과, 1 건너뜀). 데이터 파일을 수정하지 않았습니다(`git diff origin/main --stat -- proto_src/console4/*.json`의 출력 없음).
15. 외부 요청 0건, 콘솔 오류 0건, 가로 오버플로 0px, 휠 스크롤 회귀 없음(6절의 통과 항목)을 유지합니다.
16. 3절 측정표의 다른 전환(범위 패널, 팝오버, 오른쪽 상세 패널, 표로 보기 모달, 필터)이 지금보다 나빠지지 않습니다.

## 7. 문제없던 것

이번 검수에서 통과한 것입니다. 고치면서 회귀가 생기지 않게 봅니다.

- 파일 범위(요청 35 8절 밖의 변경 없음), 재빌드 바이트 일치, 전체 테스트 1,469 통과와 1 건너뜀, 외부 요청 0건, 콘솔 오류 0건, 휠 스크롤 회귀 없음.
- 요청 35 1절: 1920x1080, 1600x900, 1366x768, 1280x800에서 여섯 화면의 기본과 선택 상태 모두 문서 높이와 화면 높이가 같고, 제목 줄과 탭 줄이 제자리에 있습니다. `#foot` 22px.
- 요청 35 2절: `#actbar` 없음, 버튼 줄 28px 한 줄, 1180x820 한 줄 유지, 키보드 Tab 순서.
- 요청 35 3절: 조건 바꾸기 패널과 탭 줄 자체의 애니메이션(1920x1080 열기 5.1px, 접기 6.3px, 100ms 진행률 50% 이하), 범위 패널, 팝오버, 오른쪽 상세 패널, 표로 보기 모달, 필터, 애니메이션 "끔"의 즉시 전환, 시간과 이징을 CSS 변수 한 곳에서 정한 것.
- 요청 35 4절: 요약 바의 툴팁, 드래그 탐색 제거, 눈금 클릭으로 선택되지 않음, 부록의 K1~K12.
- 요청 35 5절: 하단 상세 패널 `.ev-body` 높이 1920x1080 352.3px, 1600x900 이하 304px, 첫 구역이 안쪽 스크롤 없이 보임.
- 요청 35 6절: 영업 인사이트 요약 한 행(30px), 구역 이동 버튼 없음, 오른쪽 미리 보기(1920x1080 카드 폭 530.2px, 추가 뒤 600ms 안에 보임).
- 요청 35 7절 1번: 세 회사 표로 보기는 가로 스크롤 없음, 여러 회사 화면은 담보 열과 판정 열 고정, 분야 머리행 이름도 가로로 밀어도 보입니다.

## 8. PR 글에 적을 것

- 이 문서의 번호(1-1, 1-2, 2절 1~11번)마다 수정 방법. 고치지 않은 것은 이유를 적습니다.
- PR 글 2절의 전환별 측정표(요청 35 3절)를 고친 뒤 다시 재서 바꿉니다. 조건 바꾸기와 범위 패널 행에는 패널, 탭 줄과 함께 아래 영역(`#z-left`, `#z-center`, `#z-right`, `#home-panel`)의 위쪽과 아래쪽 가장자리를 따로 적습니다.
- 4절 스크립트의 출력(고치기 전과 후).
- 33ms 넘는 프레임은 3회 실행의 가장 나쁜 값과 실행 환경(3절 "참고").
