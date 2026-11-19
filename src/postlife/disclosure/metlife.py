"""메트라이프생명 공시실(brand.metlife.co.kr)의 '판매상품목록'과 '판매중지상품'에서 상품 목록과 기초서류를 받는다.

공시 화면이 쓰는 요청을 그대로 따른다 (2026-11-19 확인). 목록은 ajax 응답이 아니라 서버가 그려 보내는 HTML 표다.
표 한 장에 상품마다 모든 판매기간과 서류 링크가 들어 있어, 목록 요청 한 번이 판매기간 목록과 서류 목록을 겸한다.
- 판매상품 목록: GET  /pn/mcvrgProd/retrieveMcvrgProdMain.do  → 주보험 59개 상품, 691개 판매기간 (1.26MB, 쪽 나눔 없음)
- 판매상품 검색: POST 같은 주소, 폼 searchKeyword=<상품명 일부>&insProdSeq=&fnum=&seq= (UTF-8)
                 "360 종합보장"으로 3개 상품(83KB). 괄호가 든 전체 상품명으로도 그 상품 하나가 온다.
                 결과가 없으면 표 없이 "검색 결과가 없습니다." 상자가 온다. 화면은 빈 검색어를 보내지 않는다
- 판매중지 목록: GET  /pn/saleStop/retrieveSaleStopProdMain.do  → 349개 상품 (2MB). 검색은 POST로
                 searchCondition=0&searchKeyword=…를 보낸다. 이 표에는 상품요약서 칸이 없다
- 서류 내려받기: GET  /pn/mcvrgProd/mcvrgProdDownloadFile.do?insProdSeq=<상품 순번>&seq=<판매기간 순번>&fnum=<서류 번호>
                 fnum은 01 사업방법서, 02 상품요약서, 03 약관 (상품설명서 칸에 링크가 있는 행은 보지 못했다).
                 판매중지 목록의 링크도 같은 주소다. 응답 머리에 Content-Type이 없고 Content-Disposition에 원래 파일 이름이 온다.
                 없는 서류를 달라고 하면 상태 200, text/html 255바이트의 "에러가 발생했습니다!" 쪽이 온다
- 특약보기 팝업: GET  /pn/mcvrgProd/retrieveMcvrgProdPop.do?insProdSeq=&seq= → 특약 약관 링크만 5개씩 쪽 나눔으로 온다.
                 이 모듈은 쓰지 않는다. 360 종합보장보험(무해약환급금형)의 팝업 1, 2쪽에 그 상품 요약서의 상품 구성에 없는
                 "(간편)" 특약이 나와서, 팝업이 그 상품의 특약만 보여 주는지 확인하지 못했다.

로그인, 세션 쿠키, 토큰, 암호화는 필요 없다. 위 요청을 모두 쿠키 없이 보냈다(서버가 JSESSIONID를 내려 주지만 다시 보내지 않았다).
목록 GET과 판매중지 검색 POST는 Referer 없이도 응답이 왔다. 내려받기는 Referer를 붙인 채로만 성공을 확인했다.
상품코드는 목록에 따로 없다. insProdSeq는 공시실의 상품 순번으로 개정을 넘어 이어진다.
약관 파일 이름에 다섯 자리 숫자가 붙는데(…_12286_12288_12287_12289_20260701.pdf), 개정 때 바뀌는 상품도 있고
그대로인 상품도 있다. 뜻은 확인하지 않았다(Period.codes).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

BASE = "https://brand.metlife.co.kr"
LIST_PAGE = BASE + "/pn/mcvrgProd/retrieveMcvrgProdMain.do"
STOP_PAGE = BASE + "/pn/saleStop/retrieveSaleStopProdMain.do"
DOWNLOAD = BASE + "/pn/mcvrgProd/mcvrgProdDownloadFile.do"
# 서류 종류는 링크가 놓인 칸의 머리말로 정한다. 판매중지 표는 상품요약서 칸이 빠져 칸 순서가 다르다.
DOC_KINDS = ("사업방법서", "상품요약서", "약관", "상품설명서(남)", "상품설명서(여)")
NO_RESULT = "검색 결과가 없습니다"
_PERIOD = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(?:(\d{4})\.(\d{2})\.(\d{2}))?")
_POPUP = re.compile(r"popUpOpen\(\s*'[^']*'\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
_CODES = re.compile(r"(?<=_)\d{5}(?=_)")


@dataclass(frozen=True)
class Document:
    ins_prod_seq: str   # 상품 순번 (insProdSeq)
    seq: str            # 판매기간 순번 (seq)
    name: str
    kind: str           # 사업방법서 / 상품요약서 / 약관
    fnum: str           # 01 / 02 / 03
    file_name: str      # 목록에 적힌 파일 이름. 내려받을 때 Content-Disposition의 이름과 같았다
    start: str
    end: str | None

    @property
    def url(self) -> str:
        return DOWNLOAD + "?" + urlencode({"insProdSeq": self.ins_prod_seq, "seq": self.seq, "fnum": self.fnum})


@dataclass(frozen=True)
class Period:
    """판매기간 한 건. 개정 때마다 seq가 새로 붙는다. 지난 판매기간에는 상품요약서가 없는 경우가 많다."""
    ins_prod_seq: str
    seq: str
    name: str
    start: str                   # 판매 개시일 YYYY-MM-DD
    end: str | None = None       # 판매 종료일. 열린 기간이면 None
    documents: tuple[Document, ...] = field(default=(), compare=False, hash=False)

    @property
    def files(self) -> dict[str, str]:
        return {d.kind: d.file_name for d in self.documents}

    @property
    def codes(self) -> tuple[str, ...]:
        """약관 파일 이름의 다섯 자리 숫자들. 상품코드인지 확인하지 않았다."""
        return tuple(_CODES.findall(self.files.get("약관", "")))


@dataclass(frozen=True)
class Product:
    ins_prod_seq: str
    name: str
    category: str      # 표의 '구분': 보장 / 변액 / 연금
    selling: bool      # 판매상품 목록에서 왔으면 True, 판매중지 목록이면 False
    periods: tuple[Period, ...] = field(default=(), compare=False, hash=False)   # 화면 순서(최근 것부터)

    @property
    def current(self) -> Period | None:
        """종료일이 없는 판매기간. 판매상품 목록의 59개 상품은 모두 첫 판매기간이 열려 있었다.
        판매중지 목록에도 종료일이 없는 판매기간을 가진 상품이 하나 있었다(퇴직보험, 2011-06-01 ~). selling으로 가린다."""
        return next((p for p in self.periods if p.end is None), None)


class _Cell:
    def __init__(self, tag: str, attrs: dict[str, str | None]):
        self.tag = tag
        self.attrs = attrs
        self.text = ""
        self.links: list[dict[str, str]] = []   # {"href", "onclick", "text"}


class _TableParser(HTMLParser):
    """목록 표(table.tblList)의 머리행과 본문 행. 표 밖의 메뉴와 꼬리는 버린다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0          # 목록 표 안이면 1 이상
        self.part = ""          # thead / tbody
        self.head: list[list[_Cell]] = []
        self.body: list[tuple[dict[str, str | None], list[_Cell]]] = []
        self._row: list[_Cell] | None = None
        self._row_attrs: dict[str, str | None] = {}
        self._cell: _Cell | None = None
        self._link: dict[str, str] | None = None
        self.found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "table":
            if self.depth or "tblList" in (a.get("class") or "").split():
                self.depth += 1
                self.found = True
            return
        if not self.depth:
            return
        if tag in ("thead", "tbody"):
            self.part = tag
        elif tag == "tr":
            self._row, self._row_attrs = [], a
        elif tag in ("th", "td") and self._row is not None:
            self._cell = _Cell(tag, a)
        elif tag == "a" and self._cell is not None:
            self._link = {"href": a.get("href") or "", "onclick": a.get("onclick") or "", "text": ""}
            self._cell.links.append(self._link)

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if tag == "table":
            self.depth -= 1
        elif tag == "a":
            self._link = None
        elif tag in ("th", "td") and self._cell is not None and self._row is not None:
            self._cell.text = " ".join(self._cell.text.split())
            for link in self._cell.links:
                link["text"] = " ".join(link["text"].split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self.part == "thead":
                self.head.append(self._row)
            elif self.part == "tbody":
                self.body.append((self._row_attrs, self._row))
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.text += data
            if self._link is not None:
                self._link["text"] += data


def _columns(head: list[list[_Cell]]) -> list[str]:
    """머리행 두 줄을 칸 이름 목록으로 편다. 상품설명서(colspan 2) 아래의 남, 여는 '상품설명서(남)'처럼 붙인다."""
    if not head:
        return []
    below = iter(c.text for c in head[1]) if len(head) > 1 else iter(())
    out: list[str] = []
    for cell in head[0]:
        span = int(cell.attrs.get("colspan") or 1)
        out += [cell.text] if span == 1 else [f"{cell.text}({next(below, '')})" for _ in range(span)]
    return out


def _date(y: str | None, m: str | None, d: str | None) -> str | None:
    return f"{y}-{m}-{d}" if y else None


def _query(href: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(href).query).items()}


def _period(name: str, cells: dict[str, _Cell]) -> Period | None:
    m = _PERIOD.search(cells["판매기간"].text) if "판매기간" in cells else None
    if not m:
        return None
    start, end = _date(*m.groups()[:3]), _date(*m.groups()[3:])
    ids = next((_POPUP.search(l["onclick"]).groups() for c in cells.values() for l in c.links
                if _POPUP.search(l["onclick"])), None)
    docs = []
    for kind in DOC_KINDS:
        for link in cells[kind].links if kind in cells else ():
            q = _query(link["href"])
            if q.get("insProdSeq") and q.get("seq") and q.get("fnum"):
                docs.append(Document(q["insProdSeq"], q["seq"], name, kind, q["fnum"], link["text"], start, end))
                ids = ids or (q["insProdSeq"], q["seq"])
    if ids is None:
        return None
    return Period(ids[0], ids[1], name, start, end, tuple(docs))


def parse_list(text: str, selling: bool = True) -> list[Product]:
    """판매상품 목록이나 판매중지 목록 화면(또는 검색 결과)의 HTML에서 상품과 판매기간, 서류 링크를 읽는다.

    상품 행: <th id="row_…">구분</th><td rowspan=2>상품명</td><td>펼치기 단추</td>
    판매기간 행: 첫 행(지금 판매기간)은 판매기간 칸부터, 지난 행(class="row_…")은 구분과 상품명 칸을 앞에 한 번 더 둔다.
    그래서 행의 뒤쪽 칸을 머리행의 '판매기간' 이후 칸 이름에 맞춘다.
    """
    p = _TableParser()
    p.feed(text)
    p.close()
    if not p.found:
        if NO_RESULT in text:
            return []
        raise ValueError("메트라이프 목록 표(table.tblList)를 찾지 못함: " + " ".join(text[:200].split()))
    columns = _columns(p.head)
    if "판매기간" not in columns or "주보험상품명" not in columns:
        raise ValueError(f"메트라이프 목록 표의 머리행이 예상과 다름: {columns}")
    tail = columns[columns.index("판매기간"):]
    products: list[Product] = []
    current: dict[str, Any] | None = None

    def close() -> None:
        if current and current["periods"]:
            first = current["periods"][0]
            products.append(Product(first.ins_prod_seq, current["name"], current["category"], selling,
                                    tuple(current["periods"])))

    for attrs, row in p.body:
        if row and row[0].tag == "th" and (row[0].attrs.get("id") or "").startswith("row_"):
            close()
            current = {"category": row[0].text, "name": row[1].text if len(row) > 1 else "", "periods": []}
            continue
        if current is None or len(row) < len(tail):
            continue
        period = _period(current["name"], dict(zip(tail, row[-len(tail):])))
        if period:
            current["periods"].append(period)
    close()
    return products


def pick_period(periods: list[Period] | tuple[Period, ...], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _page(selling: bool) -> str:
    return LIST_PAGE if selling else STOP_PAGE


def list_products(session: Any, keyword: str = "", selling: bool = True) -> list[Product]:
    """keyword가 없으면 화면을 GET으로 열어 모든 상품을(판매중지는 2MB), 있으면 화면의 검색 폼을 POST로 보낸다."""
    url = _page(selling)
    if keyword:
        form = {"searchKeyword": keyword, "insProdSeq": "", "fnum": "", "seq": ""}
        if not selling:
            form = {"searchCondition": "0", **form}
        r = session.post(url, data=form, headers={"Referer": url}, timeout=120)
    else:
        r = session.get(url, timeout=120)
    r.raise_for_status()
    r.encoding = "utf-8"
    return parse_list(r.text, selling)


def find_product(products: list[Product], name: str) -> Product | None:
    """목록에서 상품명이 같은 상품. 빈칸 수만 다른 이름도 같은 것으로 본다(검색은 부분 일치라 여러 상품이 온다)."""
    key = " ".join(name.split())
    return next((p for p in products if " ".join(p.name.split()) == key), None)


def list_documents(session: Any, name: str, on: str | None = None, selling: bool = True) -> list[Document]:
    """상품명(목록에 적힌 그대로)으로 검색해 on(YYYY-MM-DD) 판매기간의 서류를 돌려준다. on이 없으면 가장 최근 판매기간. 요청 한 번."""
    product = find_product(list_products(session, name, selling), name)
    period = pick_period(product.periods, on) if product else None
    return list(period.documents) if period else []


def download(session: Any, doc: Document) -> bytes:
    r = session.get(doc.url, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    # 없는 서류도 상태 200으로 오류 HTML이 온다. 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = " ".join(r.content[:400].decode("utf-8", errors="replace").split())[:200]
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.kind} {doc.file_name} | {head}")
    return r.content[start:]
