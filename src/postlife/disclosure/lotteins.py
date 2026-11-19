"""롯데손해보험 공시실(lotteins.co.kr)의 '보험상품약관' 화면에서 상품 목록과 기초서류를 받는다.

공시 화면(/web/C/D/H/cdh190.jsp, 누리집 하단 공시정보 메뉴의 '보험상품약관')이 쓰는 요청을 그대로 따른다
(2026-11-19 확인). '상품공시'(cdh170.jsp)는 안내 화면이고, 사업방법서, 상품요약서, 약관은 이 화면에만 있다.
화면은 폼(myform)을 숨은 iframe으로 보내고, 응답(rtnUri의 cdh190_result.jsp)은 부모 화면의 칸을 innerHTML로
바꾸는 스크립트가 든 HTML이다. JSON이 아니다. 요청 본문과 응답은 모두 EUC-KR(cp949)이다.

목록 요청은 모두 POST /CChannelSvl, 본문은 폼(application/x-www-form-urlencoded)이다.
공통 필드는 ops_tc=dfi.c.d.g.cmd.Cdg079Cmd, rtnUri=/web/C/D/H/cdh190_result.jsp, issale=Y(판매상품)|N(판매중지 상품).
- 상품 목록 (2단계): task=gostep2issale|gostep2isnotsale, lcode, mcode (장기보험 > 상해,질병 = 03, 01)
                    → step3('03','01','1110') 과 상품명. scode는 사이트의 상품 순번이다
- 판매기간 (3단계): task=gostep3issale|…isnotsale, scode → step4('03','01','1110','20260801') 과 "2026.08.01 ~ 현재"
- 서류 목록 (4단계): task=gostep4issale|…isnotsale, scode, startdate → 사업방법서, 상품요약서, 약관 경로
                    (/upload/C/newProduct/forman_sb_08.pdf 꼴)
- 상품명 검색:       task=searchKey, srcPrdNm(EUC-KR) → '판매상품', '판매종료상품' 두 표가 한 번에 온다. 행마다 상품군,
                    상품명, 판매기간(종료일 또는 '현재'), 약관, 사업방법서, 상품요약서 경로. 지난 판매기간도 모두 온다
                    ("건강"으로 550행, 420KB). 상품 순번(scode)은 오지 않는다
- 서류 내려받기:     GET <경로> (정적 파일). 없는 파일은 상태 404와 HTML 안내 화면이 온다

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키와 Referer 없이 보낸 첫 요청에 같은 응답이 왔다(Referer는 화면과 같게 붙인다).
화면 스크립트(anySign4PCInterface.js)가 응답에 함께 실리지만 목록 요청에는 쓰이지 않는다.

상품코드는 응답에도, 파일 이름에도, 사업방법서와 상품요약서 본문에도 없다. 상품을 가리키는 값은 사이트의 상품 순번(scode)뿐이다.
순번은 두 탭이 한 줄로 이어진다(판매상품 1104와 1106 사이의 1105가 판매중지 탭에 있다). 판매중지 탭은 '0001'처럼 0을 채운다.
판매상품 탭의 상품이라도 지난 판매기간이 함께 오고, 판매종료상품 표에도 '~ 현재'로 열린 판매기간이 있다
(예: (무) let:care 생활상해종합보험(주택플러스)(2601)). 어느 탭에 있는지와 열린 판매기간이 있는지는 따로 본다.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, quote_plus, urlencode

BASE = "https://www.lotteins.co.kr"
LIST_PAGE = BASE + "/web/C/D/H/cdh190.jsp"
ENDPOINT = BASE + "/CChannelSvl"
OPS_TC = "dfi.c.d.g.cmd.Cdg079Cmd"
RTN_URI = "/web/C/D/H/cdh190_result.jsp"
CHARSET = "cp949"      # 화면은 EUC-KR이다. 브라우저는 EUC-KR 폼을 cp949로 보낸다
FORM = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": LIST_PAGE,
}
DOC_KINDS = ("사업방법서", "상품요약서", "약관")
# 화면 1단계 '상품군' 가운데 장기보험 (lcode, mcode, 이름). 건강 보장 상품은 모두 '상해,질병'에 있다.
# 자동차보험(01), 일반보험(02), 공통(04)도 화면에 있지만 건강 보장 비교와 무관해 넣지 않았다.
LONG_TERM: tuple[tuple[str, str, str], ...] = (
    ("03", "01", "상해,질병"), ("03", "02", "저축"), ("03", "03", "운전자"),
    ("03", "04", "재물"), ("03", "05", "연금보험"), ("03", "06", "제도성특약"),
)
HEALTH = LONG_TERM[:1]

_STEP3 = re.compile(r"step3\('(\d+)','(\d+)','(\d+)'\);[^>]*>\s*<span>(.*?)</span>", re.S)
_STEP4 = re.compile(r"step4\('(\d+)','(\d+)','(\d+)','(\d{8})'\);[^>]*>\s*<span>([^<]*)", re.S)
_PERIOD = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(?:<br>\s*)?(?:(\d{4})\.(\d{2})\.(\d{2})|현재)")
_LINK = re.compile(r"href=([^\s>]+)\s+title='새창열림_([^' ]+) PDF보기'")
_COUNT = re.compile(r"\(총\s*(\d+)건\)")


@dataclass(frozen=True)
class Product:
    """상품 목록(2단계)의 한 행. 이 단계에는 판매기간도 서류도 없다."""
    scode: str                 # 사이트의 상품 순번. 상품코드가 아니다
    name: str                  # 개정 연월이 붙은 이름: (무) let:smile 종합건강보험(더끌림 포맨)(2604)
    lcode: str = "03"
    mcode: str = "01"
    kind: str = ""             # 1단계 상품군 이름: 상해,질병, 저축 …
    selling: bool = True       # 판매상품 탭에서 왔는가


@dataclass(frozen=True)
class Document:
    name: str
    kind: str              # 사업방법서 / 상품요약서 / 약관
    path: str              # 내려받기 경로: /upload/C/newProduct/forman_yoyak_08.pdf
    start: str             # 판매 개시일 YYYY-MM-DD
    end: str | None        # 판매 종료일. 화면에 '현재'로 적힌 열린 기간이면 None
    scode: str = ""

    @property
    def file_name(self) -> str:
        return self.path.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Period:
    """판매기간 한 건. 판매기간 목록(3단계)과 검색에서 온다. 개정 연월이 같아도 판매기간마다 파일이 다를 수 있다."""
    name: str
    start: str                      # 판매 개시일 YYYY-MM-DD
    end: str | None = None          # 판매 종료일. '현재'면 None
    scode: str = ""                 # 3단계에서 온 행만 있다
    selling: bool | None = None     # 검색 응답: 판매상품 표(True)인가 판매종료상품 표(False)인가
    group: str = ""                 # 검색 응답의 상품군: 장기, 일반, 자동차 …
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 서류 종류 → 경로 (검색 응답만)

    @property
    def is_open(self) -> bool:
        return self.end is None

    @property
    def documents(self) -> list[Document]:
        """검색 응답의 파일 경로를 Document로. 서류가 없는 칸(링크 없이 그림만 있는 칸)은 빠진다."""
        return [Document(self.name, kind, path, self.start, self.end, self.scode)
                for kind in DOC_KINDS if (path := self.files.get(kind))]


def _ymd(y: str, m: str, d: str) -> str:
    return f"{y}-{m}-{d}"


def _period(text: str) -> tuple[str, str | None]:
    """'2026.04.01 ~ <br>2026.06.30' 또는 '2026.08.01 ~ 현재' → (개시일, 종료일 또는 None)."""
    m = _PERIOD.search(text or "")
    if not m:
        raise ValueError(f"롯데손해보험 판매기간 꼴이 다름: {text!r}")
    return _ymd(*m.group(1, 2, 3)), (_ymd(*m.group(4, 5, 6)) if m.group(4) else None)


def _text(fragment: str) -> str:
    """태그를 걷고 엔티티를 풀고 빈칸을 하나로. 받은 응답에는 엔티티가 없었지만 다른 회사 공시실에서 &amp;가 온 적이 있다."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def _assigned(body: str, view: str) -> str:
    """응답 스크립트가 부모 화면의 view 칸에 넣는 HTML. 칸을 비우는 줄이 먼저 오고 내용을 넣는 줄이 뒤에 온다.

    view 칸에 넣는 줄이 하나도 없으면 공시 응답이 아니다(오류 화면 등). 상태 코드는 200일 수 있어 여기서 가린다.
    """
    found = re.findall(r'getElementById\("%s"\)\.innerHTML\s*=\s*"((?:[^"\\]|\\.)*)"' % re.escape(view), body)
    if not found:
        head = re.sub(r"\s+", " ", body[:200])
        raise ValueError(f"롯데손해보험 응답에 {view} 칸이 없음: {head}")
    return found[-1]


def parse_products(body: str, lcode: str = "03", mcode: str = "01", kind: str = "", selling: bool = True) -> list[Product]:
    """상품 목록(2단계). 화면 순서(판매상품 탭은 순번 순) 그대로 돌려준다."""
    out = []
    for lc, mc, scode, name in _STEP3.findall(_assigned(body, "step2view")):
        name = _text(name)
        if name:
            out.append(Product(scode, name, lc or lcode, mc or mcode, kind, selling))
    return out


def parse_periods(name: str, body: str) -> list[Period]:
    """판매기간 목록(3단계). 화면은 최근 기간부터 적는다. 개시일 순으로 돌려준다."""
    out = []
    for _lc, _mc, scode, startdate, label in _STEP4.findall(_assigned(body, "step3view")):
        start, end = _period(label)
        if start.replace("-", "") != startdate:
            raise ValueError(f"롯데손해보험 판매기간 표시({label})와 요청 값({startdate})이 다름")
        out.append(Period(name, start, end, scode))
    return sorted(out, key=lambda p: p.start)


def parse_documents(body: str, scode: str = "") -> list[Document]:
    """서류 목록(4단계). 상품명과 판매기간, 서류 링크가 한 칸에 온다. 서류가 없으면 링크 없이 그림만 있다."""
    view = _assigned(body, "step4view")
    name = re.search(r"<dt>상품명</dt>\s*<dd><span>(.*?)</span>", view, re.S)
    label = re.search(r"판매기간</dt>\s*<dd><span>(.*?)</span>", view, re.S)
    if not name or not _text(name.group(1)):
        return []      # 아무것도 고르지 않은 상태의 빈 칸
    start, end = _period(label.group(1) if label else "")
    return [Document(_text(name.group(1)), kind, path, start, end, scode)
            for path, kind in _LINK.findall(view) if kind in DOC_KINDS]


def parse_search(body: str) -> list[Period]:
    """상품명 검색. 판매상품 표와 판매종료상품 표의 모든 행(판매기간마다 한 행). 표 위의 '(총 N건)'과 행 수를 맞춰 본다."""
    out = []
    for view, selling in (("searchviewissale", True), ("searchviewisnotsale", False)):
        table = _assigned(body, view)
        rows = []
        for tr in re.findall(r"<tr>(.*?)</tr>", table, re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(tds) != 6:       # 머리행(th)과 '검색된 판매상품이 없습니다.'(colspan=6) 행
                continue
            start, end = _period(tds[2])
            files = {kind: path for cell in tds[3:] for path, kind in _LINK.findall(cell) if kind in DOC_KINDS}
            rows.append(Period(_text(tds[1]), start, end, "", selling, _text(tds[0]), files))
        count = _COUNT.search(table)
        if count and int(count.group(1)) != len(rows):
            raise ValueError(f"롯데손해보험 검색 {view}: 표 위 건수 {count.group(1)}와 읽은 행 {len(rows)}이 다름")
        out += rows
    return out


def pick_period(periods: list[Period], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _form(task: str, selling: bool = True, lcode: str = "", mcode: str = "", scode: str = "",
          startdate: str = "", keyword: str = "") -> bytes:
    """화면의 myform과 같은 필드, 같은 순서. '/'는 그대로 두었다(그대로 보낸 요청으로 확인했다)."""
    fields = {"ops_tc": OPS_TC, "task": task, "rtnUri": RTN_URI, "lcode": lcode, "mcode": mcode, "scode": scode,
              "startdate": startdate, "issale": "Y" if selling else "N", "srcPrdNm": keyword}
    return urlencode(fields, safe="/", encoding=CHARSET, quote_via=quote_plus).encode("ascii")


def _post(session: Any, body: bytes) -> str:
    r = session.post(ENDPOINT, data=body, headers=FORM, timeout=120)
    r.raise_for_status()
    return r.content.decode(CHARSET, errors="replace")


def _task(step: int, selling: bool) -> str:
    return f"gostep{step}{'issale' if selling else 'isnotsale'}"


def list_products(session: Any, selling: bool = True,
                  categories: tuple[tuple[str, str, str], ...] = LONG_TERM) -> list[Product]:
    """상품군을 한 칸씩 조회한다(기본은 장기보험 6칸). 판매중지 탭의 상해,질병 칸은 1,082행, 150KB다."""
    out: list[Product] = []
    for lcode, mcode, kind in categories:
        body = _post(session, _form(_task(2, selling), selling, lcode, mcode))
        out += parse_products(body, lcode, mcode, kind, selling)
    return out


def search_products(session: Any, keyword: str) -> list[Period]:
    """상품명에 keyword가 든 모든 판매기간(판매상품, 판매종료상품)과 서류 경로. 판매 탭과 무관하게 두 표가 다 온다."""
    return parse_search(_post(session, _form("searchKey", True, keyword=keyword)))


def list_periods(session: Any, product: Product) -> list[Period]:
    body = _post(session, _form(_task(3, product.selling), product.selling, product.lcode, product.mcode, product.scode))
    return parse_periods(product.name, body)


def documents_for(session: Any, product: Product, start: str) -> list[Document]:
    """start: 판매 개시일 YYYY-MM-DD (3단계에서 온 값)."""
    body = _post(session, _form(_task(4, product.selling), product.selling, product.lcode, product.mcode,
                                product.scode, start.replace("-", "")))
    return parse_documents(body, product.scode)


def list_documents(session: Any, product: Product, on: str | None = None) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 요청 두 번(판매기간 목록, 서류 목록)."""
    period = pick_period(list_periods(session, product), on)
    return documents_for(session, product, period.start) if period else []


def download(session: Any, doc: Document | str) -> bytes:
    """서류 경로를 그대로 GET한다. 없는 파일은 404와 HTML 안내 화면이 오므로 문서 시작 표식으로 가린다."""
    path = doc.path if isinstance(doc, Document) else doc
    url = path if path.startswith("http") else BASE + quote(path, safe="/()-_.,~!*'")
    r = session.get(url, headers={"Referer": LIST_PAGE}, timeout=300)
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode(CHARSET, errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답(상태 {r.status_code}, {r.headers.get('Content-Type', '')}, "
                         f"{len(r.content)}바이트): {path} | {head}")
    return r.content[start:]
