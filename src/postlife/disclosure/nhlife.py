"""NH농협생명 공시실(nhlife.co.kr)의 '전체상품공시'에서 상품 목록과 기초서류를 받는다.

공시 화면(/ho/on/HOON0004M00.nhl)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
목록과 서류 목록은 JSON이 아니라 서버가 그린 HTML이다. 둘 다 폼(application/x-www-form-urlencoded) POST이고,
화면은 같은 폼(frm: prsPagcn, selProdNm, useyn, prodDcd, prodnm)을 두 주소에 보낸다.
- 상품 목록:   POST /ho/on/HOON0004M00.nhl   useyn(""|Y|N), prodDcd(보험종류 CTGRxx, ""=전체), prodnm(상품명 검색어),
               prsPagcn(쪽 번호) → 한 쪽 10행 표(보험종류, 상품명, 판매여부)와 "전체 N 건", 쪽 단추 linkPage(n)
- 서류 목록:   POST /ho/on/HOON0004P10.nhl   같은 폼에 selProdNm=상품명 → 판매기간마다 한 행(한 쪽 5행, 새 기간이 위)
               popupPdfViewer('FILE_000000000024583', '0') 꼴로 첨부파일 묶음 번호와 순번이 상품요약서, 사업방법서,
               보험약관 칸에 하나씩 온다. 이 응답은 화면에 끼워 넣는 HTML 조각이 아니라 문서 한 벌이다.
- 서류 내려받기: GET /pdfViewer.nhl?apdFlid=<묶음 번호>&fileSeqn=<순번>
               보기 화면(/pdfViewerPopup.nhl)의 tspdfviewer.js가 PDF.js로 여는 주소다. 응답은 application/octet-stream이고
               Content-Disposition에 원래 파일 이름("[상품요약서]건강플러스NH통합보험(무배당)_2609_vf.pdf")이 온다.

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키 없는 첫 요청으로 목록, 서류 목록, PDF가 모두 왔다.
목록과 서류 목록은 Referer를 붙여서만 확인했으므로 화면과 같게 붙여 보낸다.
실패도 상태 200으로 온다: 없는 순번을 내려받으면 text/html 오류 화면("네트워크 장애로 서비스를 이용하실 수 없습니다",
1,797바이트)이 오고, 검색 결과가 없으면 "전체 0 건"과 "데이터가 없습니다." 한 행이 온다.
상품명에는 HTML 엔티티가 없었다(판매중 건강/재해 22건, 판매중지 첫 쪽). 그래도 풀어서 쓴다.
상품코드는 공시실 응답에 없다. 보험상품 메뉴(/ho/ig/HOIG0010M00.nhl)의 goPage('N0001217')가 상품 소개 화면
(/ho/ig/HOIG0001M00.nhl?prodCd=N0001217)의 코드이고, 이름이 공시실 목록과 글자 그대로 같았다(판매 중 대면 상품 29개 메뉴).
첨부파일 묶음 번호(FILE_…)는 판매기간마다 새로 붙는 번호라 상품코드로 쓰지 않는다.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

BASE = "https://www.nhlife.co.kr"
LIST_PAGE = BASE + "/ho/on/HOON0004M00.nhl"
POPUP = BASE + "/ho/on/HOON0004P10.nhl"
VIEWER_PAGE = BASE + "/pdfViewerPopup.nhl"
VIEWER = BASE + "/pdfViewer.nhl"
MENU = BASE + "/ho/ig/HOIG0010M00.nhl"
PAGE_SIZE = 10          # 상품 목록 한 쪽의 행 수
POPUP_PAGE_SIZE = 5     # 서류 목록 한 쪽의 행 수
# 서류 목록 표의 칸 순서. 순번(fileSeqn)은 지금까지 본 행 모두 이 순서대로 0, 1, 2였지만, 종류는 칸 위치로 정한다
DOC_COLUMNS = ("상품요약서", "사업방법서", "약관")
# 화면의 '보험종류' 선택 목록 (2026-11-19). CTGR07은 화면에 없다
CATEGORIES = {
    "CTGR01": "종신/정기보험", "CTGR02": "연금보험", "CTGR03": "저축보험", "CTGR04": "건강/재해보험",
    "CTGR05": "어린이보험", "CTGR06": "농업인관련보험", "CTGR08": "보장성공제", "CTGR09": "연금공제",
    "CTGR10": "저축성공제", "CTGR11": "TM공제", "CTGR12": "농협특색상품", "CTGR13": "수신연계상품",
    "CTGR14": "디지털보험",
}
FORM = {"Referer": LIST_PAGE, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

_TOTAL = re.compile(r"전체\s*(?:<strong>)?\s*([\d,]+)\s*(?:</strong>)?\s*건")
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<t([hd])\b[^>]*>(.*?)</t\1>", re.S)
_ROW_NAME = re.compile(r"goAnonm\(this\.value,\s*'\d+'\);\"\s*value=\"([^\"]*)\"")
_VIEW = re.compile(r"popupPdfViewer\('([^']+)',\s*'(\d+)'\)")
_PERIOD = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2}|현재)")
_MENU_ITEM = re.compile(r"onclick=\"(goTotPage|goPage)\('([A-Z]+\d+)'\);?\"[^>]*>([^<]+)</a>")


@dataclass(frozen=True)
class Product:
    """상품 목록의 한 행. 이 단계에는 상품코드도 판매기간도 없다."""
    name: str
    kind: str = ""          # 보험종류 칸: 건강/재해보험, 종신/정기보험, 온라인보험 … (선택 목록에 없는 '온라인보험'도 온다)
    selling: bool = True    # 판매여부 칸이 '판매중'인가. 판매중 상품의 서류 목록에 '~ 현재' 기간이 있는지는 따로 봐야 한다


@dataclass(frozen=True)
class Document:
    name: str
    kind: str          # 상품요약서 / 사업방법서 / 약관
    file_id: str       # 첨부파일 묶음 번호(apdFlid). 판매기간 하나에 하나
    seq: str           # 묶음 안 순번(fileSeqn)
    start: str         # 판매 개시일 YYYY-MM-DD
    end: str | None    # 판매 종료일. '~ 현재'이면 None


@dataclass(frozen=True)
class Period:
    """서류 목록의 한 행(판매기간 하나)."""
    name: str
    start: str
    end: str | None
    documents: tuple[Document, ...] = ()

    def document(self, kind: str) -> Document | None:
        return next((d for d in self.documents if d.kind == kind), None)


@dataclass(frozen=True)
class Page:
    """목록 응답 한 쪽. total은 "전체 N 건", pages는 쪽 단추에서 읽은 마지막 쪽 번호."""
    rows: tuple[Any, ...]
    total: int
    pages: int


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _total(body: str, what: str) -> int:
    m = _TOTAL.search(body)
    if not m:
        head = _text(body[:400])[:120]
        raise ValueError(f"NH농협생명 {what} 응답에 '전체 N 건'이 없음 (점검 화면이나 오류 화면일 수 있음): {head}")
    return int(m.group(1).replace(",", ""))


def _pages(body: str, func: str, total: int, size: int) -> int:
    """쪽 단추(linkPage(n), popLinkPage(n))의 가장 큰 번호. 단추가 없으면 건수로 셈한다."""
    nums = [int(n) for n in re.findall(func + r"\((\d+)\)", body)]
    return max(nums + [1 if total else 0, -(-total // size)])


def _tbody(body: str) -> str:
    i = body.find("<tbody>")
    return body[i:body.find("</tbody>", i)] if i >= 0 else ""


def parse_list(body: str) -> Page:
    """상품 목록 한 쪽. 이름은 '확인' 단추의 value(화면이 서류 목록 요청에 그대로 보내는 값)를 쓴다."""
    total = _total(body, "상품 목록")
    rows = []
    for tr in _TR.findall(_tbody(body)):
        m = _ROW_NAME.search(tr)
        if not m:
            continue
        cells = [_text(c) for _, c in _CELL.findall(tr)]
        kind = cells[0] if cells else ""
        selling = len(cells) > 2 and cells[2] == "판매중"
        rows.append(Product(html.unescape(m.group(1)).strip(), kind, selling))
    return Page(tuple(rows), total, _pages(body, "linkPage", total, PAGE_SIZE))


def parse_popup(body: str) -> Page:
    """서류 목록 한 쪽. 서류가 없는 칸은 건너뛴다."""
    m = re.search(r'class="product_title">([^<]*)<', body)
    if not m:
        raise ValueError(f"NH농협생명 서류 목록 응답에 상품명이 없음: {_text(body[:400])[:120]}")
    name = html.unescape(m.group(1)).strip()
    total = _total(body, "서류 목록")
    periods = []
    for tr in _TR.findall(_tbody(body)):
        cells = [c for _, c in _CELL.findall(tr)]
        span = _PERIOD.search(_text(cells[0])) if cells else None
        if not span:
            continue
        start, end = span.group(1), (None if span.group(2) == "현재" else span.group(2))
        docs = []
        for kind, cell in zip(DOC_COLUMNS, cells[1:]):
            v = _VIEW.search(cell)
            if v:
                docs.append(Document(name, kind, v.group(1), v.group(2), start, end))
        periods.append(Period(name, start, end, tuple(docs)))
    return Page(tuple(periods), total, _pages(body, "popLinkPage", total, POPUP_PAGE_SIZE))


def parse_menu_codes(body: str) -> dict[str, tuple[str, str]]:
    """보험상품 메뉴(HOIG0010M00)에서 {상품명: (상품코드, 보험종류)}. 메뉴에는 판매 중인 대면 상품만 있다."""
    out: dict[str, tuple[str, str]] = {}
    kind = ""
    for func, code, label in _MENU_ITEM.findall(body):
        label = html.unescape(label).strip()
        if func == "goTotPage":
            kind = label
        else:
            out.setdefault(label, (code, kind))
    return out


def pick_period(periods: list[Period] | tuple[Period, ...], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _flag(selling: bool | None) -> str:
    return "" if selling is None else ("Y" if selling else "N")


def _form(page: int, selling: bool | None, category: str, keyword: str, name: str = "") -> dict[str, str]:
    # 화면 frm의 필드 순서 그대로
    return {"prsPagcn": str(page), "selProdNm": name, "useyn": _flag(selling), "prodDcd": category, "prodnm": keyword}


def _post(session: Any, url: str, form: dict[str, str], headers: dict[str, str] | None = None) -> str:
    r = session.post(url, data=form, headers={**FORM, **(headers or {})}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def list_page(session: Any, page: int = 1, selling: bool | None = True, category: str = "", keyword: str = "") -> Page:
    return parse_list(_post(session, LIST_PAGE, _form(page, selling, category, keyword)))


def list_products(session: Any, selling: bool | None = True, category: str = "", keyword: str = "",
                  max_pages: int | None = None) -> list[Product]:
    """상품 목록을 끝 쪽까지 읽는다. 한 쪽 10행이라 범위를 좁혀 쓴다(판매중 건강/재해보험은 22건, 3쪽).

    selling: True 판매중, False 판매중지, None 전체. category: CATEGORIES의 코드. keyword: 상품명에 든 글자.
    """
    first = list_page(session, 1, selling, category, keyword)
    rows = list(first.rows)
    last = first.pages if max_pages is None else min(first.pages, max_pages)
    for n in range(2, last + 1):
        rows.extend(list_page(session, n, selling, category, keyword).rows)
    return rows


def list_periods(session: Any, name: str, selling: bool | None = None, category: str = "") -> list[Period]:
    """상품명(목록의 '확인' 단추 값 그대로)의 판매기간과 서류. 기간이 5개를 넘으면 다음 쪽도 읽는다.

    화면은 목록을 걸러 둔 판매여부와 분류 값도 함께 보내지만, 같은 상품을 (Y, CTGR04)와 (빈 값, 빈 값)으로
    보냈을 때 같은 판매기간 4건이 왔다. 그래서 기본은 빈 값이다.
    """
    out: list[Period] = []
    page, pages = 1, 1
    while page <= pages:
        got = parse_popup(_post(session, POPUP, _form(page, selling, category, "", name),
                                {"X-Requested-With": "XMLHttpRequest"}))
        out.extend(got.rows)
        pages, page = got.pages, page + 1
    return out


def list_documents(session: Any, name: str, on: str | None = None, selling: bool | None = None) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간."""
    period = pick_period(list_periods(session, name, selling), on)
    return list(period.documents) if period else []


def product_codes(session: Any) -> dict[str, tuple[str, str]]:
    """보험상품 메뉴의 {상품명: (상품코드, 보험종류)}. 요청 한 번(약 130KB)."""
    r = session.get(MENU, params={"hmpgProdDcd": "CTGR04"}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return parse_menu_codes(r.text)


def download_url(doc: Document) -> str:
    return f"{VIEWER}?apdFlid={quote(doc.file_id)}&fileSeqn={quote(doc.seq)}"


def download(session: Any, doc: Document) -> bytes:
    referer = f"{VIEWER_PAGE}?apdFlid={quote(doc.file_id)}&fileSeqn={quote(doc.seq)}"
    r = session.get(download_url(doc), headers={"Referer": referer}, timeout=300)
    r.raise_for_status()
    # 실패해도 상태 200으로 오는지 확인하려고 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.name} {doc.kind} {doc.file_id}/{doc.seq} | {head}")
    return r.content[start:]


def file_name_of(headers: Any) -> str:
    """내려받기 응답의 Content-Disposition에서 원래 파일 이름. 서버가 UTF-8 바이트를 그대로 보내 requests가
    latin-1로 읽은 글자를 되돌린다."""
    value = str((headers or {}).get("Content-Disposition", ""))
    m = re.search(r'filename="?([^";]+)"?', value)
    if not m:
        return ""
    name = m.group(1)
    try:
        return name.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name
