"""화면 흐름도(site/proto/flow.html)를 틀과 글꼴로 조립한다.

돌리기(저장소 루트에서): python proto_src/flow/build.py  (fonttools와 brotli가 있으면 글자 검사까지 한다: pip install fonttools brotli)
글꼴(합의안 10번)을 base64로 심고, 쓴 글자가 글꼴에 모두 있는지, 쓰지 않기로 한 글자가 없는지,
고지 줄과 검색 수집을 막는 메타 태그가 있는지 확인한다.

- 한글과 글자: SUIT 400, 600 (PLBody, 한글 2,350자)
- 숫자: Saira Semi Expanded 500, 600. 본문 속 숫자도 Saira로 그리도록 숫자(U+0030-0039)만 담은
  PLDigit 를 본문 글꼴 앞에 둔다. 숫자만 따로 쓰는 곳은 PLNum. 둘 다 tabular-nums.
- 짧은 영문 대문자 구역 색인: Michroma 400 (PLIdx)
"""
import base64
import html
import pathlib
import re
import sys

try:
    from fontTools.ttLib import TTFont
except ImportError:        # 없으면 글꼴에 글자가 있는지 보는 검사만 건너뛴다
    TTFont = None

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONTS = ROOT / 'proto_src/fonts'
OUT = ROOT / 'site/proto/flow.html'
DIGITS = 'U+0030-0039'
# Saira 숫자를 SUIT 숫자 높이(0의 높이 0.735em)에 맞추고(0.704em → 104%), 줄 높이는 SUIT 값에 맞춘다
SAIRA_FIT = 'size-adjust:104%;ascent-override:95%;descent-override:25%;line-gap-override:0%;'
# (글꼴 이름, 굵기, 파일, unicode-range, 덧붙일 서술자)
FACES = [
    ('PLBody', 400, 'SUIT-Regular.woff2', None, ''),
    ('PLBody', 600, 'SUIT-SemiBold.woff2', None, ''),
    ('PLDigit', 400, 'SairaSemiExpanded-Medium.woff2', DIGITS, SAIRA_FIT),
    ('PLDigit', 600, 'SairaSemiExpanded-SemiBold.woff2', DIGITS, SAIRA_FIT),
    ('PLNum', 500, 'SairaSemiExpanded-Medium.woff2', None, SAIRA_FIT),
    ('PLNum', 600, 'SairaSemiExpanded-SemiBold.woff2', None, SAIRA_FIT),
    ('PLIdx', 400, 'Michroma-Regular.woff2', None, ''),
]
NOTICE = '공모전 시연용 화면이며 영업 자료가 아닙니다'
ROBOTS = '<meta name="robots" content="noindex, nofollow">'
# 가운뎃점, 엠대시, 엔대시는 쓰지 않는다
BANNED = {'·': '가운뎃점', '—': '엠대시', '–': '엔대시', '・': '가운뎃점'}


def visible_text(src: str) -> str:
    """style을 걷어낸 글자. 태그 안의 속성 값(aria-label, data-v)도 화면에 찍히므로 남긴다."""
    s = re.sub(r'<style[\s\S]*?</style>', ' ', src)
    s = re.sub(r'<(?:/?[a-zA-Z][\w-]*)', ' ', s)
    return html.unescape(s)


def idx_text(src: str) -> str:
    """Michroma로 그리는 구역 색인(class="idx")의 글자."""
    return ''.join(re.findall(r'<span class="idx"[^>]*>([^<]*)</span>', src))


def main() -> int:
    tpl = (HERE / 'flow.tpl.html').read_text(encoding='utf-8')
    assert tpl.count('<style id="fonts"></style>') == 1
    if ROBOTS not in tpl:
        print('검색 수집을 막는 메타 태그가 없다')
        return 1
    if NOTICE not in tpl:
        print('시연용 고지가 없다')
        return 1

    text = visible_text(tpl)
    bad = sorted({BANNED[c] for c in text if c in BANNED})
    if bad:
        print('쓰지 않기로 한 글자:', ', '.join(bad))
        return 1
    if re.search(r'(?<![가-힣])판(?![가-힣])', text):
        print('"판"이 홀로 쓰였다')
        return 1
    if re.search(r'\b(?:src|href)\s*=\s*["\']?(?:https?:)?//', tpl):
        print('외부 주소를 부르는 src나 href가 있다')
        return 1

    if TTFont is None:
        print('fonttools가 없어 글꼴에 글자가 있는지 보는 검사를 건너뛴다(pip install fonttools brotli)')
    else:
        body = set(TTFont(FONTS / FACES[0][2]).getBestCmap())
        digit = set(TTFont(FONTS / FACES[2][2]).getBestCmap())
        missing = sorted({c for c in text if c.strip() and ord(c) not in body and ord(c) not in digit})
        if missing:
            print('본문 글꼴에 없는 글자:', ' '.join(f'{c}(U+{ord(c):04X})' for c in missing))
            return 1
        idx = set(TTFont(FONTS / 'Michroma-Regular.woff2').getBestCmap())
        it = idx_text(tpl)
        if not it or any(not ('A' <= c <= 'Z') for c in it if c.strip()) or any(ord(c) not in idx for c in it if c.strip()):
            print('구역 색인은 Michroma에 있는 영문 대문자만 쓴다:', repr(it))
            return 1

    css = '\n'.join(
        f'@font-face{{font-family:"{fam}";font-style:normal;font-weight:{w};font-display:block;{extra}'
        + (f'unicode-range:{ur};' if ur else '')
        + f'src:url(data:font/woff2;base64,{base64.b64encode((FONTS / fn).read_bytes()).decode()}) format("woff2")}}'
        for fam, w, fn, ur, extra in FACES)
    out = tpl.replace('<style id="fonts"></style>', '<style id="fonts">\n' + css + '\n</style>')
    OUT.write_text(out, encoding='utf-8')
    print('written', OUT, len(out.encode('utf-8')), 'bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
