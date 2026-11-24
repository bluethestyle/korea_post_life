"""시안 4를 한 파일로 합친다: tpl.html + style.css + tabN.css + core.js + tabN.js + sales.json + d.json(const D) + 글꼴.

쓰기: python proto_src/console4/build.py [출력 경로] [--src 폴더] [--banner 글]
      출력 경로를 주지 않으면 site/proto/console4.html 에 쓴다.
      --src 를 주면 원본과 자료를 그 폴더에서 읽는다(기본은 이 파일이 있는 proto_src/console4). 글꼴은 늘 저장소에서 읽는다.
      --banner 를 주면 맨 위 고지 줄의 고지 글(#notice-t) 바로 앞과 창 제목 앞에 그 글을 끼운다(tpl.html 은 고치지 않는다).
      끼운 글은 줄어들지 않고 늘 다 보이며, 좁은 화면(380px)에서는 고지 글이 줄임표로 줄어든다.
      가상 사본으로 회사 수에 매이지 않는 화면을 시험할 때 쓴다(scripts/dev/build_console4_synthetic.py).
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

import argparse
import base64
import html
import io
import json
import re
import sys
from pathlib import Path

import terms_check

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
OUT_DEFAULT = ROOT / 'site/proto/console4.html'
FONTS = ROOT / 'proto_src/fonts/fonts_v4.css'
FONT_NOTICE = ROOT / 'proto_src/fonts/fonts_v4_notice.txt'
GRAPH_DEFAULT = ROOT / 'proto_src/graph/graph.json'
SRC = HERE                             # 원본과 자료를 읽는 폴더(--src 로 바꾼다)
D_JSON = SRC / 'd.json'                # const D. scripts/export_app_data.py 가 만든다(src/postlife/site/lineup.py)
NOTICE_SPAN = '<span id="notice-t">'   # tpl.html 의 맨 위 고지 자리. --banner 의 글은 이 span 바로 앞에 끼운다
# --banner 때 고지 글에 붙이는 꼴: 끼운 글에 밀려 좁은 화면에서 넘치면 줄임표로 줄어든다(.nt 는 flex 라 고지 글에 직접 준다)
NOTICE_FIT = ' style="min-width:0;overflow:hidden;text-overflow:ellipsis"'
EXPORT_CMD = 'python scripts/export_app_data.py'
TABS = [1, 2, 3, 4, 5, 6]
ALLOWED_DOT = ['교육·비교', '입원·수술']  # 기획 확정본 표식 문구와 용어 자체 표기("입원·수술")
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
        p = SRC / name
        if p.exists():
            take(name, lambda p=p: json.loads(read(p))['자료시각'])
    head = 'const CV = '
    take('tab4.js', lambda: json.loads(read(SRC / 'tab4.js').split('\n', 1)[0][len(head):].rstrip(';'))['t'])
    if D_JSON.exists():
        take(D_JSON.name, lambda: json.loads(read(D_JSON))['asOf'])
    return out


def check_tab4() -> None:
    """tab4.js 는 cover.json 한 줄과 tab4.src.js 를 합친 것이다. build 는 tab4.js 를 실으므로, 다르면 합치기를 잊은 것이라
    멈춘다(tab4.src.js 만 고친 것이 화면에 들어가지 않은 채 합쳐지지 않게)."""
    parts = [SRC / 'cover.json', SRC / 'tab4.src.js', SRC / 'tab4.js']
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


def with_banner(tpl: str, banner: str) -> str:
    """맨 위 고지 줄의 고지 글(#notice-t) 바로 앞과 창 제목 앞에 banner 를 끼운 tpl. 고지 자리가 없으면 오류로 멈춘다.
    고지 줄(.notice .nt)은 한 줄(nowrap)에 넘치는 것을 자른다(overflow hidden). 끼운 글을 고지 글 뒤에 두면 380px 에서
    "가상 자료(화면 배..."까지만 보여서, 앞에 두고 줄어들지 않게(flex:none) 하고 고지 글이 줄임표로 줄어들게 한다."""
    a = tpl.find(NOTICE_SPAN)
    if a < 0:
        errors.append(f'tpl.html 에 {NOTICE_SPAN} 가 없어 --banner 의 글을 끼우지 못했다')
        return tpl
    text = html.escape(banner)
    flag = (f'<span id="banner-t" class="banner" style="flex:none;font-weight:700;color:#c62828;white-space:nowrap">'
            f'{text}</span>')
    tpl = tpl[:a] + flag + NOTICE_SPAN[:-1] + NOTICE_FIT + '>' + tpl[a + len(NOTICE_SPAN):]
    return re.sub(r'<title>', f'<title>[{text}] ', tpl, count=1)


def main() -> int:
    global SRC, D_JSON
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', type=Path, default=OUT_DEFAULT, help='출력 경로(기본 site/proto/console4.html)')
    ap.add_argument('--src', type=Path, default=HERE, help='원본과 자료를 읽는 폴더(기본 proto_src/console4)')
    ap.add_argument('--banner', help='맨 위 고지 줄 옆에 끼울 글(가상 자료 표시)')
    args = ap.parse_args()
    out = args.out
    SRC = args.src.resolve()
    D_JSON = SRC / 'd.json'
    tpl = read(SRC / 'tpl.html')
    style = read(SRC / 'style.css')
    tab_css = []
    for n in TABS:
        p = SRC / f'tab{n}.css'
        if p.exists():
            tab_css.append((p.name, read(p)))
    core = read(SRC / 'core.js')
    tab_js = []
    for n in TABS:
        p = SRC / f'tab{n}.js'
        if not p.exists():
            errors.append(f'{p.name} 가 없다')
            continue
        tab_js.append((p.name, read(p)))
    sales = read(SRC / 'sales.json')

    for name, text in [('tpl.html', tpl), ('style.css', style), ('core.js', core)] + tab_css + tab_js:
        check_authored(name, text)
    errors.extend(terms_check.check_console4_sources(SRC, FONT_NOTICE if FONT_NOTICE.exists() else None))
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

    graph_file = (SRC / 'graph.json') if (SRC / 'graph.json').exists() else GRAPH_DEFAULT
    if graph_file.exists():
        graph_raw = read(graph_file)
    else:
        graph_raw = '{"snapshot_at":"","kinds":[],"ekinds":[],"nodes":[],"edges":[],"keys":[]}'
        warns.append(f'관계망 자료 파일이 없다({graph_file}). 빈 자료로 둔다')

    js = core + '\n' + '\n'.join(f';(function () {{\n\'use strict\';\n/* {n} */\n{t}\n}})();' for n, t in tab_js) + '\nApp.boot();\n'
    css = style + '\n' + '\n'.join(f'/* {n} */\n{t}' for n, t in tab_css)
    sales_safe = sales.replace('</', '<\\/').replace('<!--', '<\\!--')
    graph_safe = graph_raw.replace('</', '<\\/').replace('<!--', '<\\!--')
    for key in ['/*__FONTS__*/', '/*__STYLE__*/', '/*__SALES__*/', '/*__GRAPH__*/', '/*__D__*/', '/*__SCRIPTS__*/', '/*__FONT_NOTICE__*/']:
        if tpl.count(key) != 1:
            errors.append(f'tpl.html 에 {key} 가 {tpl.count(key)}번 있다')
    if args.banner:
        tpl = with_banner(tpl, args.banner)
    page = (tpl.replace('/*__FONTS__*/', fonts.strip())
               .replace('/*__STYLE__*/', css)
               .replace('/*__SALES__*/', sales_safe)
               .replace('/*__GRAPH__*/', graph_safe)
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
    out.write_text(page, encoding='utf-8', newline='\n')
    size = len(page.encode('utf-8'))
    print(f'썼다: {out} ({size:,}바이트, {size / 1024:.0f}KB). 글꼴 {"심음" if fonts else "없음"}, 탭 파일 {len(tab_js)}개, 탭 css {len(tab_css)}개')
    return 0


if __name__ == '__main__':
    sys.exit(main())
