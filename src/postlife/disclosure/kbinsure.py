"""KB손해보험 공시실(kbinsure.co.kr)의 '상품목록(약관)'에서 상품 목록과 기초서류를 받는다.

공시 화면(/CG802030001.ec, 공시실 > 보험상품공시 > 상품목록(약관))이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
ajax 호출은 없고, 화면이 폼을 POST로 다시 보내 서버가 그린 HTML(EUC-KR)을 받는 방식이다.
- 상품 목록(검색): POST /CG802030001.ec  폼(EUC-KR) {onsaleYn: " "전체/"Y"판매 중/"N"판매 중지, gubun: 보험종류,
                   goodsNm: 상품명 일부, bojongNo: 상품코드, devonTargetRow: 첫 행 번호, devonRowSize: 쪽 크기 …}
                   → 표의 행: 판매중지여부, 보험종류, 상품코드, <a href="javascript:detail('코드','종류값','순번')">상품명</a>
                   화면은 쪽마다 10행을 보이지만 devonRowSize를 붙이면 그만큼 한 번에 온다("건강"·판매 중 96행이 한 번에 왔다)
- 판매기간·서류:   POST /CG802030002.ec  폼 {bojongNo, gubun, bojongSeq} (화면의 detail() 함수와 같다)
                   → 판매기간마다 한 행: 판매시작일, 판매종료일(열린 기간은 빈칸), 보험약관, 사업방법서, 상품요약서, 비고
                   간편심사 상품은 같은 판매기간에 "간편심사형"과 "일반심사형" 두 행이 있다(비고 칸으로 가른다)
- 서류 내려받기:   GET  /CG802030003.ec?fileNm=<파일 이름>   파일 이름은 25443_2_3.Pdf, 25422_2_3(간편).pdf 꼴이다
                   (상품코드_판매기간 차례_서류 번호. 1 약관, 2 사업방법서, 3 상품요약서. 확장자 대소문자가 섞여 있다)
                   한글은 화면 문자셋(EUC-KR)으로 싸서 보낸다. 파일이 없으면 상태 200에 HTML 오류 화면
                   ("해당 파일이 존재하지 않습니다.")이 온다

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 목록, 상세, 내려받기 모두 쿠키 없는 새 세션의 첫 요청으로 응답이 왔다.
상품코드(다섯 자리)는 목록에 따로 칸이 있다. 보험종류 값은 화면 선택 상자와 같다(BOJONG_KINDS). 판매 중인 건강보험은
대부분 '상해보험'(c)에 있고, '제휴'(g)에는 다이렉트 상품과 다른 이름으로 파는 같은 상품이 들어 있다.
사업방법서에 "판매채널에 따라 명칭을 다르게 할 수 있음"이라고 적고 같은 서류를 이름만 바꿔 여러 코드로 공시한다
(KB Yes!365 건강보험 25442와 KB 닥터플러스 건강보험 25443의 사업방법서는 바이트까지 같았다).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlencode

BASE = "https://www.kbinsure.co.kr"
LIST_PAGE = BASE + "/CG802030001.ec"
DETAIL_PAGE = BASE + "/CG802030002.ec"
DOWNLOAD = BASE + "/CG802030003.ec?fileNm="
ENCODING = "cp949"          # 화면은 euc-kr이라 적는다. 브라우저가 쓰는 euc-kr은 cp949와 같다
FORM = {"Content-Type": "application/x-www-form-urlencoded", "Referer": LIST_PAGE}
# 화면 '보험종류' 선택 상자. 값이 " "이면 전체다.
BOJONG_KINDS = {
    "1": "일반보험", "3": "퇴직보험", "4": "자동차보험", "5": "단체보험", "6": "개인연금", "7": "퇴직연금",
    "a": "통합보험", "b": "운전자보험", "c": "상해보험", "d": "질병보험", "e": "화재/재물보험", "f": "방카슈랑스",
    "g": "제휴", "h": "저축성보험", "i": "독립특별약관", "j": "제도성 특별약관", "k": "기타보험",
}
ALL = " "
DOC_COLUMNS = ("약관", "사업방법서", "상품요약서")     # 상세 표의 서류 칸 차례. 설명서 칸은 화면에서 주석 처리되어 있다
_MISSING = "해당 파일이 존재하지 않습니다"

_ROW = re.compile(
    r"<tr>\s*<td>(?P<status>.*?)</td>\s*<td>(?P<kind>.*?)</td>\s*<td>(?P<code>.*?)</td>\s*<td[^>]*>\s*"
    r"<a href=\"javascript:detail\('(?P<b>[^']*)','(?P<g>[^']*)','(?P<s>[^']*)'\);\">(?P<name>.*?)</a>", re.S)
_PAGE = re.compile(r"goPage\('(\d+)'\)")
_TITLE = re.compile(r"<td class=\"tit\">\s*(.*?)\s*</td>", re.S)
_DETAIL_TABLE = re.compile(r"<table class=\"tb_default04\".*?<tbody>(.*?)</tbody>", re.S)
_TR = re.compile(r"<tr>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_FILE = re.compile(r"fileNm=([^\"'&>]+)")
# 25443_2_3.Pdf → (25443, 2, 3, ""), 25422_2_3(간편).pdf → (25422, 2, 3, "간편")
_FILE_NAME = re.compile(r"^(\d+)_(\d+)_(\d+)(?:\(([^)]*)\))?\.pdf$", re.IGNORECASE)


@dataclass(frozen=True)
class Product:
    """상품 목록의 한 행. 상품코드는 개정판(예: (26.09))마다 새로 붙는다."""
    code: str
    name: str
    kind: str = ""          # 보험종류: 상해보험, 질병보험, 제휴, 방카슈랑스 …
    gubun: str = ""         # 보험종류 값(BOJONG_KINDS). 상세 요청에 그대로 넣는다
    seq: str = "1"          # detail()의 세 번째 인자(bojongSeq). 지금까지 본 행은 모두 "1"이었다
    selling: bool = True    # '판매중'이면 True. 판매기간이 열려 있는지는 상세에서 따로 본다


@dataclass(frozen=True)
class Period:
    """상세 표의 한 행. 판매기간 하나에 서류 묶음 하나. 간편심사 상품은 같은 기간에 행이 둘이다."""
    start: str                      # 판매시작일 YYYY-MM-DD
    end: str | None = None          # 판매종료일. 열린 기간이면 None
    note: str = ""                  # 비고 칸: "간편심사형", "일반심사형" 또는 빈칸
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)   # 서류 종류 → 파일 이름


@dataclass(frozen=True)
class Document:
    code: str
    name: str
    kind: str          # 약관 / 사업방법서 / 상품요약서
    file_name: str     # 내려받기 요청에 넣는 이름(화면 그대로, 확장자 대소문자 포함)
    start: str
    end: str | None
    note: str = ""     # 간편심사형 / 일반심사형

    @property
    def period_no(self) -> str:
        """파일 이름의 판매기간 차례. 꼴이 다르면 빈 글."""
        m = _FILE_NAME.match(self.file_name)
        return m.group(2) if m else ""


def file_parts(file_name: str) -> tuple[str, str, str, str]:
    """파일 이름에서 (상품코드, 판매기간 차례, 서류 번호, 괄호 안 구분). 꼴이 맞지 않으면 빈 글 넷."""
    m = _FILE_NAME.match((file_name or "").strip())
    return (m.group(1), m.group(2), m.group(3), m.group(4) or "") if m else ("", "", "", "")


def _text(fragment: str) -> str:
    """HTML 조각의 글자. 태그를 떼고 엔티티를 풀고 빈칸을 하나로 줄인다."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def _date(text: str) -> str | None:
    digits = re.sub(r"\D", "", text or "")
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def _decode(body: bytes | str) -> str:
    return body if isinstance(body, str) else body.decode(ENCODING, errors="replace")


def _check_page(page: str, what: str) -> None:
    """오류 화면이면 알린다. 이 누리집은 오류도 상태 200의 HTML 화면으로 돌려준다."""
    if "jsp=error.jsp" in page or "tit_error_sorry" in page:
        m = re.search(r'xTrackerError\([^,]*,[^,]*,[^,]*,"([^"]*)"', page)
        raise ValueError(f"KB손해보험 {what} 응답이 오류 화면: {m.group(1) if m else '내용 없음'}")


def parse_products(body: bytes | str) -> list[Product]:
    """목록 화면의 표에서 상품 행을 읽는다. 조회 결과가 없으면 빈 목록."""
    page = _decode(body)
    _check_page(page, "목록")
    if 'id="prdtList"' not in page:
        raise ValueError("KB손해보험 목록 화면이 아님: 상품목록 폼(prdtList)이 없다")
    out = []
    for m in _ROW.finditer(page):
        code = _text(m.group("code")) or m.group("b").strip()
        out.append(Product(code, _text(m.group("name")), _text(m.group("kind")), m.group("g").strip(),
                           m.group("s").strip() or "1", _text(m.group("status")) == "판매중"))
    return out


def next_row(body: bytes | str, current: int) -> int | None:
    """쪽 넘김 단추에서 다음 쪽의 첫 행 번호. 마지막 쪽이면 None."""
    later = [int(n) for n in _PAGE.findall(_decode(body)) if int(n) > current]
    return min(later) if later else None


def parse_detail(body: bytes | str) -> tuple[str, list[Period]]:
    """상세 화면에서 (제목, 판매기간 목록). 제목은 "[상해보험] 상품명" 꼴이다. 판매시작일 순으로 돌려준다."""
    page = _decode(body)
    _check_page(page, "상세")
    title = _TITLE.search(page)
    table = _DETAIL_TABLE.search(page)
    if not title or not table:
        raise ValueError("KB손해보험 상세 화면이 아님: 제목 칸이나 서류 표가 없다")
    periods = []
    for row in _TR.findall(table.group(1)):
        cells = _TD.findall(row)
        start = _date(_text(cells[0])) if cells else None
        if not start or len(cells) < 2 + len(DOC_COLUMNS):
            continue
        files = {}
        for kind, cell in zip(DOC_COLUMNS, cells[2:2 + len(DOC_COLUMNS)]):
            m = _FILE.search(cell)
            if m:                     # 파일이 없는 칸은 화면에서 stop()을 부르거나 비어 있다
                files[kind] = html.unescape(m.group(1)).strip()
        note = _text(cells[2 + len(DOC_COLUMNS)]) if len(cells) > 2 + len(DOC_COLUMNS) else ""
        periods.append(Period(start, _date(_text(cells[1])), note, files))
    return _text(title.group(1)), sorted(periods, key=lambda p: p.start)


def split_title(title: str) -> tuple[str, str]:
    """"[상해보험] KB 닥터플러스 건강보험(…)" → ("상해보험", "KB 닥터플러스 건강보험(…)")."""
    m = re.match(r"^\[([^\]]*)\]\s*(.*)$", title or "")
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", (title or "").strip())


def pick_periods(periods: list[Period], on: str | None = None) -> list[Period]:
    """on(YYYY-MM-DD)이 속한 판매기간의 행들. on이 없으면 개시일이 가장 늦은 행들(간편·일반심사형이 함께 온다)."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    if not periods:
        return []
    last = max(p.start for p in periods)
    return [p for p in periods if p.start == last]


def _post(session: Any, url: str, fields: dict[str, str]) -> bytes:
    r = session.post(url, data=urlencode(fields, encoding=ENCODING), headers=FORM, timeout=60)
    r.raise_for_status()
    return r.content


def list_products(session: Any, keyword: str = "", selling: bool | None = True, gubun: str = ALL,
                  code: str = "", rows: int = 200, max_pages: int = 30) -> list[Product]:
    """상품명에 keyword가 든 상품. selling=None이면 판매 중·중지 모두. 쪽마다 rows행씩 받아 끝까지 넘긴다.

    keyword 없이 전체를 부르면 4천 행이 넘으니 검색어나 보험종류로 좁혀 쓴다.
    """
    flag = ALL if selling is None else ("Y" if selling else "N")
    out: list[Product] = []
    target = 1
    for _ in range(max_pages):
        fields = {
            "devonTargetRow": str(target), "devonOrderBy": "", "devonRowSize": str(rows),
            "gubun": gubun, "goodsNm": keyword, "onsaleYn": flag, "bojongNo": code, "bojongSeq": "",
            # 화면은 검색 칸 값(search_*)을 숨은 칸에 옮겨 둘 다 보낸다
            "search_onsale_yn": flag, "search_bojong_no": code, "search_gubun": gubun, "search_goods_nm": keyword,
        }
        body = _post(session, LIST_PAGE, fields)
        out += parse_products(body)
        target = next_row(body, target)
        if target is None:
            break
    return out


def list_periods(session: Any, product: Product) -> list[Period]:
    """상품의 판매기간과 서류 파일 이름(요청 한 번)."""
    fields = {"devonTargetRow": "1", "devonOrderBy": "", "gubun": product.gubun, "goodsNm": "", "onsaleYn": "",
              "bojongNo": product.code, "bojongSeq": product.seq, "search_onsale_yn": ALL, "search_bojong_no": "",
              "search_gubun": ALL, "search_goods_nm": ""}
    return parse_detail(_post(session, DETAIL_PAGE, fields))[1]


def documents_of(product: Product, periods: list[Period], on: str | None = None, note: str | None = None) -> list[Document]:
    """판매기간 목록에서 on이 속한 기간(없으면 최근 기간)의 서류. note("간편심사형" 등)를 주면 그 행만."""
    out = []
    for p in pick_periods(periods, on):
        if note is not None and p.note != note:
            continue
        for kind, file_name in p.files.items():
            out.append(Document(product.code, product.name, kind, file_name, p.start, p.end, p.note))
    return out


def list_documents(session: Any, product: Product, on: str | None = None, note: str | None = None) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 요청 한 번."""
    return documents_of(product, list_periods(session, product), on, note)


def download_url(file_name: str) -> str:
    # 화면 링크는 한글을 그대로 둔다. 브라우저는 질의 문자열을 문서 문자셋으로 싸서 보낸다: (간편) → (%B0%A3%C6%ED)
    return DOWNLOAD + quote(file_name, safe="()._-", encoding=ENCODING)


def download(session: Any, doc: Document) -> bytes:
    r = session.get(download_url(doc.file_name), headers={"Referer": DETAIL_PAGE}, timeout=300)
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        page = _decode(r.content[:60000])
        why = _MISSING if _MISSING in page else page[:200].replace("\n", " ").strip()
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): {doc.file_name} | {why}")
    return r.content[start:]
