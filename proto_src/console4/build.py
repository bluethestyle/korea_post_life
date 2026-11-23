"""시안 4를 한 파일로 합친다: tpl.html + style.css + tabN.css + core.js + tabN.js + sales.json + d.json(const D) + 글꼴.

쓰기: python proto_src/console4/build.py [출력 경로]
      출력 경로를 주지 않으면 site/proto/console4.html 에 쓴다.
자료(sales.json, combo.json, gate.json, cover.json, d.json 과 tab3.js 의 자료 줄, tab4.js)는 먼저
python scripts/export_app_data.py 로 같은 사본에서 만든다.

build 때 검사한다(오류면 쓰지 않고 멈춘다)
- 손으로 쓴 원본(tpl.html, *.css, *.js): 외부 주소(http, https, //, @import), 가운뎃점 나열(정해 둔 표식 문구는 뺀다),
  엠대시와 가로 막대, "판올림", "~됨" 압축, "준비 중".
- 자료: d.json 이 없거나 읽히지 않음, 자료 파일들의 자료 시각이 서로 다름,
  tab4.js 가 cover.json + tab4.src.js 와 다름(build 는 tab4.js 를 싣는다. tab4.src.js 만 고치면 화면에 들어가지 않는다).
- 합친 파일: 외부 요청(src, href, url() 의 바깥 주소, <link>, @import), noindex 메타 태그.
경고만 찍는다
- 글꼴 파일이 없음(기기 글꼴로 둔다), 자리 표시가 남은 탭, 글꼴에 없는 한글.
"""
from __future__ import annotations

import base64
import html
import io
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
OUT_DEFAULT = ROOT / 'site/proto/console4.html'
FONTS = ROOT / 'proto_src/fonts/fonts_v4.css'
FONT_NOTICE = ROOT / 'proto_src/fonts/fonts_v4_notice.txt'
D_JSON = HERE / 'd.json'              # const D. scripts/export_app_data.py 가 만든다(src/postlife/site/lineup.py)
EXPORT_CMD = 'python scripts/export_app_data.py'
TABS = [1, 2, 3, 4, 5]
ALLOWED_DOT = ['교육·비교']           # 기획 확정본의 표식 문구 "내부 교육·비교 참고용(대외 배포 금지)"
PLACEHOLDER = '이 탭은 다음 단계에서 채운다'

errors: list[str] = []
warns: list[str] = []


def read(p: Path) -> str:
    return p.read_text(encoding='utf-8')


def check_authored(name: str, text: str) -> None:
    lines = text.split('\n')
    for i, ln in enumerate(lines, 1):
        bare = ln
        for ok in ALLOWED_DOT:
            bare = bare.replace(ok, '')
        if re.search(r'https?://|(?<![:\w])//[a-z0-9.-]+\.[a-z]{2,}/|@import', bare):
            # SVG 이름공간은 주소가 아니라 이름이라 뺀다
            if 'www.w3.org/2000/svg' not in bare:
                errors.append(f'{name}:{i} 외부 주소: {ln.strip()[:120]}')
        if re.search(r'[가-힣A-Za-z0-9)\]]\s*·\s*[가-힣A-Za-z(\[]', bare):
            errors.append(f'{name}:{i} 가운뎃점 나열: {ln.strip()[:120]}')
        if '—' in ln or '―' in ln:
            errors.append(f'{name}:{i} 엠대시: {ln.strip()[:120]}')
        if '판올림' in ln or '판 올림' in ln:
            errors.append(f'{name}:{i} "판올림": {ln.strip()[:120]}')
        if '됨' in ln:
            errors.append(f'{name}:{i} "~됨" 압축: {ln.strip()[:120]}')
        if '준비 중' in ln:
            errors.append(f'{name}:{i} "준비 중": {ln.strip()[:120]}')


def d_line() -> str:
    """d.json 을 "const D = <자료>;" 한 줄로. 파일이 없으면 다른 자료로 대신하지 않고 오류로 멈춘다."""
    if not D_JSON.exists():
        errors.append(f'{D_JSON.name} 이 없다. {EXPORT_CMD} 로 자료를 다시 만든 뒤 합친다')
        return 'const D = null;'
    text = read(D_JSON)
    try:
        d = json.loads(text)
    except ValueError as e:
        errors.append(f'{D_JSON.name} 을 JSON 으로 읽지 못했다: {e}')
        return 'const D = null;'
    if not isinstance(d, dict) or not {'orgs', 'std'} <= set(d):
        errors.append(f'{D_JSON.name} 에 orgs, std 열쇠가 없다. {EXPORT_CMD} 로 다시 만든다')
    return 'const D = ' + text.replace('</', '<\\/').replace('<!--', '<\\!--') + ';'


def data_times(sales: str) -> dict[str, object]:
    """자료 파일마다 자료 시각. 같은 사본에서 만들었으면 모두 같다."""
    out: dict[str, object] = {}

    def take(name: str, get) -> None:
        try:
            out[name] = get()
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            out[name] = '읽지 못함'

    take('sales.json', lambda: json.loads(sales)['자료시각'])
    for name in ('combo.json', 'gate.json'):
        p = HERE / name
        if p.exists():
            take(name, lambda p=p: json.loads(read(p))['자료시각'])
    head = 'const CV = '
    take('tab4.js', lambda: json.loads(read(HERE / 'tab4.js').split('\n', 1)[0][len(head):].rstrip(';'))['t'])
    if D_JSON.exists():
        take(D_JSON.name, lambda: json.loads(read(D_JSON))['asOf'])
    return out


def check_tab4() -> None:
    """tab4.js 는 cover.json 한 줄과 tab4.src.js 를 합친 것이다. build 는 tab4.js 를 실으므로, 다르면 합치기를 잊은 것이라
    멈춘다(tab4.src.js 만 고친 것이 화면에 들어가지 않은 채 합쳐지지 않게)."""
    parts = [HERE / 'cover.json', HERE / 'tab4.src.js', HERE / 'tab4.js']
    if not all(p.exists() for p in parts):
        return
    cover, src, tab4 = (read(p) for p in parts)
    if tab4 != 'const CV = ' + cover + ';\n' + src:
        errors.append('tab4.js 가 cover.json 과 tab4.src.js 를 합친 것과 다르다. python proto_src/console4/gen_cover.py --assemble 로 다시 합친다')


def font_cmap(css: str) -> set[int]:
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return set()
    out: set[int] = set()
    for m in re.finditer(r'font-family:\s*"PLKo";[^}]*?url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)', css):
        f = TTFont(io.BytesIO(base64.b64decode(m.group(1))))
        out |= set(f.getBestCmap())
    return out


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT
    tpl = read(HERE / 'tpl.html')
    style = read(HERE / 'style.css')
    tab_css = []
    for n in TABS:
        p = HERE / f'tab{n}.css'
        if p.exists():
            tab_css.append((p.name, read(p)))
    core = read(HERE / 'core.js')
    tab_js = []
    for n in TABS:
        p = HERE / f'tab{n}.js'
        if not p.exists():
            errors.append(f'{p.name} 가 없다')
            continue
        tab_js.append((p.name, read(p)))
    sales = read(HERE / 'sales.json')

    for name, text in [('tpl.html', tpl), ('style.css', style), ('core.js', core)] + tab_css + tab_js:
        check_authored(name, text)
    for name, text in tab_js:
        if PLACEHOLDER in text:
            warns.append(f'{name}: 자리 표시가 남았다("{PLACEHOLDER}")')
    times = data_times(sales)
    if len(set(map(str, times.values()))) > 1:
        errors.append('자료 시각이 서로 다르다(' + ', '.join(f'{k} {v}' for k, v in times.items())
                      + f'). {EXPORT_CMD} 로 같은 사본에서 다시 만든다')
    check_tab4()

    if FONTS.exists():
        fonts = read(FONTS)
    else:
        fonts = ''
        warns.append(f'글꼴 파일이 없다({FONTS}). 기기 글꼴로 둔다. 마지막 build 전에 다시 본다')
    notice = html.escape(read(FONT_NOTICE).strip()) if FONT_NOTICE.exists() else 'SUIT, Saira Semi Condensed (SIL Open Font License 1.1)'

    js = core + '\n' + '\n'.join(f';(function () {{\n\'use strict\';\n/* {n} */\n{t}\n}})();' for n, t in tab_js) + '\nApp.boot();\n'
    css = style + '\n' + '\n'.join(f'/* {n} */\n{t}' for n, t in tab_css)
    sales_safe = sales.replace('</', '<\\/').replace('<!--', '<\\!--')
    for key in ['/*__FONTS__*/', '/*__STYLE__*/', '/*__SALES__*/', '/*__D__*/', '/*__SCRIPTS__*/', '/*__FONT_NOTICE__*/']:
        if tpl.count(key) != 1:
            errors.append(f'tpl.html 에 {key} 가 {tpl.count(key)}번 있다')
    page = (tpl.replace('/*__FONTS__*/', fonts.strip())
               .replace('/*__STYLE__*/', css)
               .replace('/*__SALES__*/', sales_safe)
               .replace('/*__D__*/', d_line())
               .replace('/*__SCRIPTS__*/', js.replace('</script', '<\\/script'))
               .replace('/*__FONT_NOTICE__*/', notice))

    # 합친 파일 검사: 외부 요청이 없어야 한다
    for pat, what in [(r'''(?:src|href)\s*=\s*["']?\s*(?:https?:)?//''', 'src/href 외부 주소'),
                      (r'''url\(\s*["']?\s*(?:https?:)?//''', 'url() 외부 주소'),
                      (r'<link\b', '<link> 태그'), (r'@import', '@import')]:
        for m in re.finditer(pat, page, flags=re.I):
            errors.append(f'합친 파일에 {what}: {page[max(0, m.start() - 40):m.end() + 40]!r}')
    if '<meta name="robots" content="noindex, nofollow">' not in page:
        errors.append('noindex, nofollow 메타 태그가 없다')

    # 글꼴에 없는 한글(합친 파일의 글자 전체)
    if fonts:
        cmap = font_cmap(fonts)
        if cmap:
            body = page.replace(fonts.strip(), '')
            missing = sorted({c for c in body if '가' <= c <= '힣' and ord(c) not in cmap})
            if missing:
                warns.append(f'PLKo 글꼴에 없는 한글 {len(missing)}자(기기 글꼴로 그려진다): {"".join(missing[:80])}')

    for w in warns:
        print('경고:', w)
    if errors:
        for e in errors:
            print('오류:', e)
        print(f'오류 {len(errors)}건. 쓰지 않았다.')
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8')
    size = len(page.encode('utf-8'))
    print(f'썼다: {out} ({size:,}바이트, {size / 1024:.0f}KB). 글꼴 {"심음" if fonts else "없음"}, 탭 파일 {len(tab_js)}개, 탭 css {len(tab_css)}개')
    return 0


if __name__ == '__main__':
    sys.exit(main())
