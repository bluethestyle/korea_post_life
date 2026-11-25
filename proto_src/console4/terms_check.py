"""화면 원본과 빌드 산출물의 지금 용어 재유입 검사 및 확정 이름 직접 기재 검사 (요청 37 6-2, 8-1).

실행:
  python proto_src/console4/terms_check.py            # 화면 원본 검사
  python proto_src/console4/terms_check.py --built    # 화면 원본 + 빌드된 HTML(console4.html, graph2.html) 검사
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

OLD_SCREEN_TERMS: list[tuple[str, str]] = [
    (r"영업 분석 콘솔", "1"),
    (r"브리핑", "3"),
    (r"관문", "5, 12, 22, 33~38, 40"),
    (r"관계 지도", "8"),
    (r"고객군 지도|고객군 지형|지도", "9, 10"),
    (r"(?<!상품 )개정과 시장", "11"),
    (r"포지션", "13"),
    (r"여정|격자", "14"),
    (r"범위 띠|읽기 띠|읽기 영역", "15, 16"),
    (r"확대 구역|단계 확대", "17"),
    (r"층 경로|(?:금색|중립|먹색|빗금) 층", "18, 170"),
    (r"구역 이동", "19"),
    (r"일러두기", "20"),
    (r"고지\.", "21"),
    (r"열림|닫힘|열린|닫힌|열리|닫히|열려|닫혀", "23, 24, 26~32"),
    (r"심사로 확인|일반심사 확인", "25"),
    (r"멈춘|멈춤|걸림|걸리|걸린", "39, 51"),
    (r"질문", "42, 47~51, 63"),
    (r"고지 유형", "43"),
    (r"간편 고지", "44"),
    (r"열쇠", "45"),
    (r"최근 소견", "46"),
    (r"묻습니다|묻는|묻지", "51"),
    (r"수술만", "53, 54"),
    (r"입원이나 수술|입원과 수술 질문", "47, 55, 56"),
    (r"이력의 종류", "57"),
    (r"넘음|넘게", "58"),
    (r"(?:년|개월|\}) 안(?![가-힣])|(?:년|개월) 안의", "59"),
    (r"일반 고지", "60"),
    (r"나이 자료 없음", "62"),
    (r"가입나이(?:\([^)]*\))? 밖", "64"),
    (r"최대 가입금액", "65"),
    (r"최소 가입금액", "66"),
    (r"주계약 한도|나이 한도|한도 검토", "67"),
    (r"결합 제약", "68"),
    (r"의무 부가", "69"),
    (r"목적 안|목적 밖", "70"),
    (r"담은|담으면|담지|담았|담음", "71"),
    (r"(?<!해약)환급 구조", "74"),
    (r"구조 다름", "75"),
    (r"나음|못함|(?:조건이|조건) (?:나은|못한|못하)", "77, 78, 125"),
    (r"같음", "79, 81"),
    (r"다름", "75, 80"),
    (r"값이 있는|값이 있음", "81"),
    (r"엇갈", "82"),
    (r"단정|우열을 매기지|우열 보류", "83, 84"),
    (r"특약 함께 판매|함께 팔|팝니다", "85, 189"),
    (r"우체국에만 있음|우체국만 가진", "87"),
    (r"우체국에 없음|우체국에 없는 담보", "88"),
    (r"상대", "89, 92~94"),
    (r"둘 다 없음", "90"),
    (r"모름", "91"),
    (r"맞붙", "92"),
    (r"우리", "95"),
    (r"견주|견준|견줄|견줘|견줬|견줌", "96"),
    (r"쌍", "97"),
    (r"선택 종형", "98"),
    (r"지금", "99"),
    (r"대표 조건", "100"),
    (r"다른 것만", "102"),
    (r"조건이 다른 담보|판정이 갈린", "103"),
    (r"관계 담보", "104"),
    (r"덮음|덮습니다|덮는", "105"),
    (r"검토 대기|검토대기", "110, 113"),
    (r"매핑 대기|작업 로그", "111, 112"),
    (r"뺀|빼고|뺐|빼면|뺌", "114, 129"),
    (r"검토상태", "115"),
    (r"대상외", "116"),
    (r"미연결|이어지|이어진|이어집|이어짐|이어졌", "117, 176"),
    (r"사본", "118"),
    (r"앞세울", "120"),
    (r"열위 방어", "121"),
    (r"개정 검토 후보", "122"),
    (r"관련 담보 안내", "123"),
    (r"강점 담보|조건 열위 응대|개정 검토 대상", "120~122(권고안 이름, 사용자 확정 이름으로 대체)"),
    (r"따로 주는|따로 있는", "124, 191"),
    (r"빈자리", "127"),
    (r"카드", "128, 129"),
    (r"싣기|실은|실었|싣는|실려|실음", "129"),
    (r"처음 선택", "130"),
    (r"창구 말투", "131"),
    (r"소식", "133"),
    (r"개정 변동", "134"),
    (r"짝", "135"),
    (r"(?<!판매)종료", "136"),
    (r"연결선", "139"),
    (r"보는 틀", "140"),
    (r"지나온 길", "141"),
    (r"이름 찾기", "142"),
    (r"처음으로|되돌리기", "143"),
    (r"이웃", "144"),
    (r"홉", "145"),
    (r"담보 대응", "146"),
    (r"담보 길", "147"),
    (r"일으킴|일으킨", "148"),
    (r"속함", "149"),
    (r"보장분야|보장 분야", "153"),
    (r"식별자", "154"),
    (r"직각 칸", "155"),
    (r"움직임", "156"),
    (r"절제", "157"),
    (r"짙은 화면|밝은 화면|짙게|밝게", "159"),
    (r"조건 줄", "160"),
    (r"바꾸|바꿔|바꿨|바꿀", "161"),
    (r"누르|누른|눌러|눌렀|누름", "162"),
    (r"고르|고른|골라|고름", "163, 165"),
    (r"올리거나|올린", "164"),
    (r"거르|걸러", "166"),
    (r"묶음|묶은|묶인", "167, 168"),
    (r"기둥", "169"),
    (r"(?<!카테)고리", "171"),
    (r"띠", "172"),
    (r"마디", "173"),
    (r"무대|도형", "174"),
    (r"빨강 (?:마름모|원)|네 귀", "175"),
    (r"표지", "177"),
    (r"화면 열기", "178"),
    (r"뜻 보기", "179"),
    (r"풀이", "180"),
    (r"앞 값|하나 줄이기|하나 늘리기", "181"),
    (r"그리다 멈", "182"),
    (r"생명보험만|손해보험만|직접 고른", "183"),
    (r"그대로인", "184"),
    (r"(?:\}|\d|</b>)곳|두 곳", "185"),
    (r"칸", "186"),
    (r"(?:\}|\d|</span>)줄|(?:급부|대표|합계|그|아래|위쪽|아래쪽|다른|큰|엄격한) 줄|줄을|줄이 여럿", "187"),
    (r"까닭", "188"),
    (r"모은|모았", "190"),
    (r"뽑은|뽑아", "192"),
    (r"청약 뒤|정해집니다", "193"),
    (r"무관하게", "194"),
    (r"갈래|(?<!글)꼴|누를 차례|걸음|판독|단추|조준|문지르|정본|뼈대|넘침", "CLAUDE.md 용어 교체표"),
    (r"갈림|갈 곳|길 찾기|행동 띠|두 판독", "1절 4번에서 정한 말(분기, 이동 화면, 경로 탐색, 작업 바, 담보 관계 제안)"),
]

# 키로 남긴 값과 자료 키 이름: 문자열 하나가 통째로 이 값이면 허용
KEPT_VALUES: set[str] = {
    "가입 관문", "간편 모두 닫힘", "같음", "개정 검토 후보", "갱신", "검토 대기", "검토상태", "고객군과 시장",
    "관계 담보로 덮음", "관련 담보 안내", "관문 차이", "관문전용", "나음", "나이 자료 없음", "다름", "단정 주의",
    "닫힘", "담보 비교", "대상외", "둘 다 없음", "멈춘값", "못함", "변경", "브리핑",
    "비갱신", "상대에 없음", "수술만", "수술만행", "신설", "심사로 확인", "앞세울 강점", "엇갈림",
    "열림", "영업 인사이트", "우리 간편 닫힘", "우리 간편만 열림", "우열을 매기지 않음", "우체국 나음", "우체국 못함", "우체국에 없음",
    "우체국에만 있음", "인수기준비교", "일반심사", "일부 나이만 열림", "입원", "자료 없음", "전체", "조건 열위 방어",
    "종료", "지급 형태 다름", "지도전제", "직전개정시연", "질문 자료 없음", "판정 보류", "함께 열림",
}

# 화면에 그대로 두는 구절(지운 뒤 검사)
ALLOWED_PHRASES: list[str] = ["판매종료", "예상 질문", "개정과 시장", "금색 마름모", "입원·수술", "한 줄"]

# 확정 이름 직접 기재 검사(console4 화면만). core.js의 TERM 정의 블록과 tpl.html의 <title>은 뺀다
NAME_LITERALS: list[tuple[str, str]] = [
    (r"상품-영업 분석", "TERM.app"),
    (r"관계 그래프", "TERM.graph"),
    (r"고객군별 가입 가능 현황", "TERM.seg"),
    (r"(?<!고객군별 )(?<!종형별 )가입 가능 현황", "TERM.segShort"),
    (r"응대 화법", "TERM.talk"),
    (r"단순 비교 불가", "TERM.noCompare (자료 표시명)"),
    (r"인수기준 비교", "TERM.gate (자료 표시명)"),
    (r"인수기준 차이", "TERM.catGate (자료 표시명)"),
    (r"우위 담보", "TERM.catStrong (자료 표시명)"),
    (r"열위 담보", "TERM.catWeak (자료 표시명)"),
    (r"(?<!우체국 )미보유 담보", "TERM.catMiss (자료 표시명)"),
]

COMPILED_OLD = [(re.compile(pat), row) for pat, row in OLD_SCREEN_TERMS]
COMPILED_NAME = [(re.compile(pat), ref) for pat, ref in NAME_LITERALS]

REGEX_PREV_KW = {
    "return", "typeof", "void", "delete", "throw", "case", "in", "of", "instanceof", "new", "yield", "await",
}
REGEX_PREV_CHARS = set("(,=:[!&|?{};+-*%~^<>")


def _line_offsets(src: str) -> list[int]:
    offs = [0]
    pos = 0
    while True:
        idx = src.find("\n", pos)
        if idx < 0:
            break
        offs.append(idx + 1)
        pos = idx + 1
    return offs


def _line_at(offs: list[int], idx: int) -> int:
    lo, hi = 0, len(offs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if offs[mid] <= idx:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi + 1


def _can_start_regex(src: str, pos: int) -> bool:
    j = pos - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    if j < 0:
        return True
    ch = src[j]
    if ch in REGEX_PREV_CHARS:
        return True
    if ch.isalpha() or ch in "_$":
        k = j
        while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
            k -= 1
        word = src[k + 1 : j + 1]
        return word in REGEX_PREV_KW
    return False


def _is_bracket_prop_lookup(src: str, quote_start: int, quote_end: int) -> bool:
    """x['관문만수집'] 처럼 대괄호로 자료 키를 읽는 자리인지 판정한다."""
    j = quote_start - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    if j < 0 or src[j] != "[":
        return False
    p = j - 1
    while p >= 0 and src[p] in " \t\r\n":
        p -= 1
    if p < 0:
        return False
    prev_ch = src[p]
    if not (prev_ch.isalnum() or prev_ch in "_$)]"):
        return False
    # 앞 토큰이 return, case 등 키워드이면 배열 리터럴이다
    if prev_ch.isalpha() or prev_ch in "_$":
        k = p
        while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
            k -= 1
        if src[k + 1 : p + 1] in REGEX_PREV_KW:
            return False
    m = quote_end
    while m < len(src) and src[m] in " \t\r\n":
        m += 1
    return m < len(src) and src[m] == "]"


def _unescape_js(raw: str) -> str:
    return (
        raw.replace(r"\\", "\\")
        .replace(r"\'", "'")
        .replace(r"\"", '"')
        .replace(r"\`", "`")
        .replace(r"\n", "\n")
        .replace(r"\t", "\t")
    )


def _find_term_block_range(src: str) -> tuple[int, int] | None:
    """core.js 안의 `const TERM = { ... };` 범위를 찾는다."""
    m = re.search(r"\bconst\s+TERM\s*=\s*\{", src)
    if not m:
        return None
    i = m.end()
    depth = 1
    n = len(src)
    while i < n and depth > 0:
        ch = src[i]
        if ch in ("'", '"', "`"):
            q = ch
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i + 2)
            i = n if nl < 0 else nl + 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return (m.start(), i)


def extract_js_strings(
    src: str, base_line: int = 1, skip_name_span: tuple[int, int] | None = None
) -> list[tuple[int, str, bool, bool]]:
    """JS 코드에서 문자열 토큰 (line, text, is_template_with_expr, skip_name_check) 목록을 뽑는다."""
    offs = _line_offsets(src)
    out: list[tuple[int, str, bool, bool]] = []
    n = len(src)

    def scan_range(start: int, end: int) -> int:
        i = start
        while i < end:
            ch = src[i]
            if ch == "/" and i + 1 < end and src[i + 1] == "/":
                nl = src.find("\n", i + 2, end)
                i = end if nl < 0 else nl + 1
                continue
            if ch == "/" and i + 1 < end and src[i + 1] == "*":
                ce = src.find("*/", i + 2, end)
                i = end if ce < 0 else ce + 2
                continue
            if ch in ("'", '"'):
                q = ch
                q_start = i
                i += 1
                buf: list[str] = []
                while i < end:
                    c = src[i]
                    if c == "\\":
                        if i + 1 < end:
                            buf.append(src[i : i + 2])
                            i += 2
                        else:
                            i += 1
                        continue
                    if c == q:
                        i += 1
                        break
                    buf.append(c)
                    i += 1
                q_end = i
                if not _is_bracket_prop_lookup(src, q_start, q_end):
                    ln = base_line + _line_at(offs, q_start) - 1
                    in_term = bool(skip_name_span and skip_name_span[0] <= q_start < skip_name_span[1])
                    out.append((ln, _unescape_js("".join(buf)), False, in_term))
                continue
            if ch == "`":
                t_start = i
                i += 1
                seg_line = base_line + _line_at(offs, t_start) - 1
                cur_chars: list[str] = []
                has_expr = False
                in_term = bool(skip_name_span and skip_name_span[0] <= t_start < skip_name_span[1])
                while i < end:
                    c = src[i]
                    if c == "\\":
                        if i + 1 < end:
                            cur_chars.append(src[i : i + 2])
                            i += 2
                        else:
                            i += 1
                        continue
                    if c == "`":
                        i += 1
                        break
                    if c == "$" and i + 1 < end and src[i + 1] == "{":
                        has_expr = True
                        cur_chars.append("${}")
                        i += 2
                        # ${ ... } 내부를 JS 로 스캔하며 중괄호 짝을 찾는다
                        expr_start = i
                        depth = 1
                        j = i
                        while j < end and depth > 0:
                            cj = src[j]
                            if cj == "/" and j + 1 < end and src[j + 1] == "/":
                                nl = src.find("\n", j + 2, end)
                                j = end if nl < 0 else nl + 1
                                continue
                            if cj == "/" and j + 1 < end and src[j + 1] == "*":
                                ce = src.find("*/", j + 2, end)
                                j = end if ce < 0 else ce + 2
                                continue
                            if cj in ("'", '"', "`"):
                                # 중첩 문자열/템플릿 건너뛰기(아래 재귀 호출이 정확히 처리)
                                if cj in ("'", '"'):
                                    qq = cj
                                    j += 1
                                    while j < end:
                                        if src[j] == "\\":
                                            j += 2
                                            continue
                                        if src[j] == qq:
                                            j += 1
                                            break
                                        j += 1
                                else:
                                    j += 1
                                    td = 0
                                    while j < end:
                                        if src[j] == "\\":
                                            j += 2
                                            continue
                                        if src[j] == "`" and td == 0:
                                            j += 1
                                            break
                                        if src[j] == "$" and j + 1 < end and src[j + 1] == "{":
                                            td += 1
                                            j += 2
                                            continue
                                        if src[j] == "}" and td > 0:
                                            td -= 1
                                        j += 1
                                continue
                            if cj == "/" and _can_start_regex(src[:end], j):
                                j += 1
                                in_cls = False
                                while j < end:
                                    if src[j] == "\\":
                                        j += 2
                                        continue
                                    if src[j] == "[":
                                        in_cls = True
                                    elif src[j] == "]":
                                        in_cls = False
                                    elif src[j] == "/" and not in_cls:
                                        j += 1
                                        while j < end and src[j].isalpha():
                                            j += 1
                                        break
                                    elif src[j] == "\n":
                                        break
                                    j += 1
                                continue
                            if cj == "{":
                                depth += 1
                            elif cj == "}":
                                depth -= 1
                                if depth == 0:
                                    break
                            j += 1
                        scan_range(expr_start, j)
                        i = j + 1 if j < end else end
                        continue
                    cur_chars.append(c)
                    i += 1
                raw_tpl = "".join(cur_chars)
                for offset_ln, part in enumerate(raw_tpl.split("\n")):
                    out.append((seg_line + offset_ln, _unescape_js(part), has_expr, in_term))
                continue
            if ch == "/" and _can_start_regex(src[:end], i):
                i += 1
                in_cls = False
                while i < end:
                    if src[i] == "\\":
                        i += 2
                        continue
                    if src[i] == "[":
                        in_cls = True
                    elif src[i] == "]":
                        in_cls = False
                    elif src[i] == "/" and not in_cls:
                        i += 1
                        while i < end and src[i].isalpha():
                            i += 1
                        break
                    elif src[i] == "\n":
                        break
                    i += 1
                continue
            i += 1
        return i

    scan_range(0, n)
    return out


def strip_t3_data(src: str) -> str:
    """tab3.js 의 /*__T3DATA_BEGIN__*/ ... /*__T3DATA_END__*/ 구간을 줄바꿈 수만 남기고 지운다."""
    def repl(m: re.Match[str]) -> str:
        return "\n" * m.group(0).count("\n")

    return re.sub(r"/\*__T3DATA_BEGIN__\*/.*?/\*__T3DATA_END__\*/", repl, src, flags=re.S)


def extract_html_tokens(html: str, is_built_console4: bool = False) -> list[tuple[int, str, bool, bool]]:
    """HTML 파일에서 태그 밖 글자, 속성 값, 인라인 JS 문자열을 (line, text, has_expr, skip_name_check)로 추출한다."""
    offs = _line_offsets(html)
    tokens: list[tuple[int, str, bool, bool]] = []

    # 1. 주석 제거(줄 번호 유지)
    clean = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), html, flags=re.S)

    # 2. <script> 추출 및 본문 마스킹
    def handle_script(m: re.Match[str]) -> str:
        open_tag, body = m.group(1), m.group(2)
        body_start = m.start(2)
        base_ln = _line_at(offs, body_start)
        low_tag = open_tag.lower()
        if "application/json" in low_tag:
            return "\n" * m.group(0).count("\n")
        if "text/plain" in low_tag:
            if is_built_console4 and 'id="app-bundle"' in low_tag:
                # 빌드된 console4.html 의 app-bundle: const CV = ...; 줄과 T3 자료 구간 제외
                cleaned_js = strip_t3_data(body)
                cleaned_js = re.sub(
                    r"^const CV = .*?;$",
                    "",
                    cleaned_js,
                    flags=re.M,
                )
                # const D 검사 제외와 동일하게 core.js 의 TERM 정의 블록도 스킵
                term_span = _find_term_block_range(cleaned_js)
                tokens.extend(extract_js_strings(cleaned_js, base_line=base_ln, skip_name_span=term_span))
            return "\n" * m.group(0).count("\n")
        # const D = ...; 단독 자료 스크립트는 제외
        if is_built_console4 and body.lstrip().startswith("const D = "):
            return "\n" * m.group(0).count("\n")
        tokens.extend(extract_js_strings(body, base_line=base_ln))
        return "\n" * m.group(0).count("\n")

    clean = re.sub(r"(<script\b[^>]*>)(.*?)(</script>)", handle_script, clean, flags=re.I | re.S)

    # 3. <style> 제거(줄 번호 유지)
    clean = re.sub(r"<style\b[^>]*>.*?</style>", lambda m: "\n" * m.group(0).count("\n"), clean, flags=re.I | re.S)

    # 4. <title>...</title> 별도 추출(NAME_LITERALS 스킵, OLD_SCREEN_TERMS 검사)
    def handle_title(m: re.Match[str]) -> str:
        ln = _line_at(offs, m.start(1))
        txt = m.group(1).strip()
        if txt:
            tokens.append((ln, txt, False, True))
        return "\n" * m.group(0).count("\n")

    clean = re.sub(r"<title\b[^>]*>(.*?)</title>", handle_title, clean, flags=re.I | re.S)

    # 5. 태그 속성 값 추출 및 태그 제거 후 밖 글자 추출
    for tm in re.finditer(r"<[a-zA-Z][^>]*>", clean, flags=re.S):
        tag_str = tm.group(0)
        tag_start = tm.start()
        for am in re.finditer(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""", tag_str):
            val = am.group(2) if am.group(2) is not None else am.group(3)
            if val:
                ln = _line_at(offs, tag_start + am.start())
                tokens.append((ln, val, False, False))

    text_only = re.sub(r"<[^>]+>", lambda m: " " + ("\n" * m.group(0).count("\n")) + " ", clean, flags=re.S)
    for ln_no, line in enumerate(text_only.split("\n"), 1):
        s = line.strip()
        if not s or s in ("/*__FONTS__*/", "/*__STYLE__*/", "/*__SALES__*/", "/*__GRAPH__*/", "/*__D__*/", "/*__SCRIPTS__*/", "/*__FONT_NOTICE__*/", "__DATA__"):
            continue
        tokens.append((ln_no, s, False, False))

    tokens.sort(key=lambda x: x[0])
    return tokens


def check_tokens(
    label_name: str,
    tokens: list[tuple[int, str, bool, bool]],
    check_names: bool,
) -> tuple[list[str], list[str]]:
    old_errs: list[str] = []
    name_errs: list[str] = []
    for ln, raw_text, has_expr, skip_name in tokens:
        if not raw_text:
            continue
        if not has_expr and raw_text in KEPT_VALUES:
            continue
        cleaned = raw_text
        for phrase in ALLOWED_PHRASES:
            cleaned = cleaned.replace(phrase, "")
        for rx, row_ref in COMPILED_OLD:
            m = rx.search(cleaned)
            if m:
                old_errs.append(
                    f"{label_name}:{ln} 지금 용어 {m.group(0)!r} (대조표 {row_ref}): {raw_text.strip()[:120]}"
                )
        if check_names and not skip_name:
            for rx, term_ref in COMPILED_NAME:
                m = rx.search(cleaned)
                if m:
                    name_errs.append(
                        f"{label_name}:{ln} 확정 이름 직접 기재 {m.group(0)!r} ({term_ref} 사용): {raw_text.strip()[:120]}"
                    )
    return old_errs, name_errs


def check_console4_sources(src_dir: Path, font_notice_path: Path | None = None) -> list[str]:
    """console4 원본 파일(tpl.html, core.js, tab1~3, tab4.src.js, tab5~6, 글꼴 고지)을 검사한다."""
    errs: list[str] = []
    tpl_p = src_dir / "tpl.html"
    if tpl_p.exists():
        o, n = check_tokens("tpl.html", extract_html_tokens(tpl_p.read_text(encoding="utf-8")), check_names=True)
        errs.extend(o)
        errs.extend(n)

    js_files = [
        ("core.js", src_dir / "core.js"),
        ("tab1.js", src_dir / "tab1.js"),
        ("tab2.js", src_dir / "tab2.js"),
        ("tab3.js", src_dir / "tab3.js"),
        ("tab4.src.js", src_dir / "tab4.src.js"),
        ("tab5.js", src_dir / "tab5.js"),
        ("tab6.js", src_dir / "tab6.js"),
    ]
    for name, p in js_files:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if name == "tab3.js":
            text = strip_t3_data(text)
        term_span = _find_term_block_range(text) if name == "core.js" else None
        toks = extract_js_strings(text, base_line=1, skip_name_span=term_span)
        o, n = check_tokens(name, toks, check_names=True)
        errs.extend(o)
        errs.extend(n)

    if font_notice_path and font_notice_path.exists():
        fn_lines = font_notice_path.read_text(encoding="utf-8").split("\n")
        toks = [(i, ln, False, True) for i, ln in enumerate(fn_lines, 1) if ln.strip()]
        o, _ = check_tokens(font_notice_path.name, toks, check_names=False)
        errs.extend(o)

    return errs


def check_graph_sources(tpl_path: Path) -> list[str]:
    """관계망 시안 2 원본(proto_src/graph/tpl.html)을 검사한다(NAME_LITERALS 제외)."""
    if not tpl_path.exists():
        return []
    toks = extract_html_tokens(tpl_path.read_text(encoding="utf-8"), is_built_console4=False)
    o, _ = check_tokens("graph/tpl.html", toks, check_names=False)
    return o


def check_built_html(console4_html: Path, graph2_html: Path) -> list[str]:
    """빌드된 console4.html 및 graph2.html 에서 자료 블록을 제외하고 검사한다 (8절 1번)."""
    errs: list[str] = []
    if console4_html.exists():
        toks = extract_html_tokens(console4_html.read_text(encoding="utf-8"), is_built_console4=True)
        o, n = check_tokens(str(console4_html.relative_to(ROOT)).replace("\\", "/"), toks, check_names=True)
        errs.extend(o)
        errs.extend(n)
    if graph2_html.exists():
        toks = extract_html_tokens(graph2_html.read_text(encoding="utf-8"), is_built_console4=False)
        o, _ = check_tokens(str(graph2_html.relative_to(ROOT)).replace("\\", "/"), toks, check_names=False)
        errs.extend(o)
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=HERE)
    ap.add_argument("--built", action="store_true", help="빌드된 site/proto/*.html 도 함께 검사")
    args = ap.parse_args()

    c4_errs = check_console4_sources(args.src, ROOT / "proto_src/fonts/fonts_v4_notice.txt")
    gr_errs = check_graph_sources(ROOT / "proto_src/graph/tpl.html")
    built_errs = (
        check_built_html(ROOT / "site/proto/console4.html", ROOT / "site/proto/graph2.html")
        if args.built
        else []
    )
    all_errs = c4_errs + gr_errs + built_errs
    print(
        f"원본 검사: console4 {len(c4_errs)}건, graph {len(gr_errs)}건"
        + (f", 빌드 HTML {len(built_errs)}건" if args.built else "")
    )
    for e in all_errs[:60]:
        print(" ", e)
    if len(all_errs) > 60:
        print(f"  ... 외 {len(all_errs) - 60}건")
    return 1 if all_errs else 0


if __name__ == "__main__":
    sys.exit(main())
