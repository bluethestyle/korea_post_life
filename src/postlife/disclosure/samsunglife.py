"""삼성생명 상품공시(samsunglife.com)의 '보험상품목록'에서 상품 목록과 기초서류를 받는다.

공시 화면(/individual/products/disclosure/sales/PDO-PRPRI010110M, 로그인 단계 0)이 쓰는 요청을 따른다 (2026-11-19 확인).
목록 요청은 모두 POST이고 본문은 폼(application/x-www-form-urlencoded)이다. 화면의 탭 셋이 주소만 다르다.
- 전체:       POST /gw/api/product/disclosure/product/prdt/salesAllPrdtList
- 판매상품:   POST /gw/api/product/disclosure/product/prdt/salesPrdtList
- 판매중지:   POST /gw/api/product/disclosure/product/prdt/salesStopPrdtList
  본문: mCode, gCode, sCode(대·중·소분류, 전체는 빈칸 한 글자), searchYear, goodsName(상품명 일부), pageNo, pageRows
  → {"code": "200", "message": "SUCCESS", "response": [행 …]}. 행 하나가 상품코드 × 판매기간이고, 서류 번호
  filename1(상품요약서), filename2(사업방법서), filename3(약관)이 들어 있다. pageRows=3000으로 판매상품 288행이 한 번에 왔다.
  실패해도 상태 코드는 200이고 code가 "9999" 같은 값이며 response.description에 안내문이 온다.
- 서류 목록: 따로 없다. 목록의 각 행에 서류 번호가 있다. 화면은 이 번호로 뷰어 창을 연다
  (pcms.samsunglife.com/partnerpage/CustomerPage_Unit.jsp?goodsCode=&docType=101|401|301&saleDate=&pageGubun=prdt).
- 서류 내려받기: GET https://pcms.samsunglife.com/XView.do?docID=<서류 번호>&name=<상품명>… 가 돌려주는 뷰어 HTML의
  "downloadURL"(../uploadDir/doc/<연>/<월일>/<상품코드 앞 9자>/<docType>/<서류 번호>.pdf)을 받는다. 폴더 이름의 규칙을
  짐작해 주소를 만들지 않고 뷰어 HTML에서 읽는다(요청 두 번).

화면 스크립트는 /gw 요청에 dcpChnlTyp 머리를 붙이고, 그 머리가 있으면 본문을 VestWeb(yettiesoft)으로 암호화해 보낸다.
그 머리 없이 평문 폼으로 보내도 서버가 같은 꼴로 응답했다(쿠키 없는 첫 요청). 로그인, 세션 쿠키, 토큰은 필요 없었다.
법인 상품 행은 서류를 filepath/filename으로 주고 다른 뷰어(CustomerPage_Corp.jsp)를 쓴다. 그 꼴은 받아 보지 않아 다루지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlencode, urljoin

BASE = "https://www.samsunglife.com"
PCMS = "https://pcms.samsunglife.com"
LIST_PAGE = BASE + "/individual/products/disclosure/sales/PDO-PRPRI010110M"
API = BASE + "/gw/api/product/disclosure/product/prdt/"
TABS = {"all": "salesAllPrdtList", "sales": "salesPrdtList", "stop": "salesStopPrdtList"}
VIEWER = PCMS + "/XView.do"
# filenameN의 N → (서류 종류, 화면이 뷰어에 넘기는 docType). 화면 스크립트의 단추 연결과 같다.
DOC_KINDS = {1: ("상품요약서", "101"), 2: ("사업방법서", "401"), 3: ("약관", "301")}
ALL = " "            # 분류 '전체'. 화면은 빈칸 한 글자를 보낸다
OPEN_END = "99999999"
CORP = "법인상품"
# 화면은 status가 이 둘일 때만 서류 단추를 연다
VIEWABLE = ("상품운용", "상품수정")
AJAX = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE,
    "Referer": LIST_PAGE,
}
_DOWNLOAD_URL = re.compile(r"""["']downloadURL["']\s*:\s*["']([^"']+\.pdf)["']""", re.IGNORECASE)


@dataclass(frozen=True)
class Period:
    """목록의 한 행: 상품코드 × 판매기간. 개정마다 상품코드가 바뀌고, 같은 코드 안에서 판매기간이 여러 번 나뉜다."""
    code: str                 # goodsCode. 예: LP0842003AB01V10A01
    name: str
    start: str                # 이 판매기간의 시작일 YYYY-MM-DD
    end: str | None           # 끝난 날. 열린 기간(99999999)이면 None
    selling: bool             # lCode가 "판매중"인가. 행 단위 값이다(같은 코드의 지난 기간은 "판매중지"로 오기도 한다)
    status: str = ""          # 상품운용 / 상품수정 …
    channel: str = ""         # 대분류(mCode): 개인, 온라인, 방카슈랑스, 제도성특약, 단체상품, 법인상품 …
    group: str = ""           # 중분류(gCode): 보장성, 저축성 … (온라인·방카슈랑스는 비어 있다)
    kind: str = ""            # 소분류(sCode): 건강, 종신, 실손 …
    category: str = ""        # 화면의 '종류' 칸(gubun). 예: "개인>보장성>건강"
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 서류 종류 → 서류 번호

    @property
    def corporate(self) -> bool:
        return self.channel == CORP


@dataclass(frozen=True)
class Document:
    code: str
    name: str
    kind: str        # 상품요약서 / 사업방법서 / 약관
    doc_id: str      # 서류 번호(filenameN). 뷰어 요청에 그대로 넣는다
    doc_type: str    # 101 / 401 / 301
    start: str
    end: str | None


def _date(text: Any) -> str | None:
    digits = re.sub(r"\D", "", str(text or ""))
    if len(digits) != 8 or digits == OPEN_END:
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def _rows(body: Any) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        raise ValueError(f"삼성생명 응답이 JSON 객체가 아님: {type(body).__name__}")
    if str(body.get("code")) != "200":
        inner = body.get("response") if isinstance(body.get("response"), dict) else {}
        raise ValueError(f"삼성생명 응답 오류 {body.get('code')}: {inner.get('description') or body.get('message')}")
    rows = body.get("response")
    if rows is None:      # 결과가 없을 때의 꼴은 받아 보지 않았다. 빈 목록으로 본다
        return []
    if not isinstance(rows, list):
        raise ValueError(f"삼성생명 응답의 response가 목록이 아님: {type(rows).__name__}")
    return rows


def _files(row: dict[str, Any]) -> dict[str, str]:
    if str(row.get("mCode") or "") == CORP:
        return {}
    out = {}
    for n, (kind, _) in DOC_KINDS.items():
        doc_id = str(row.get(f"filename{n}") or "").strip()
        if doc_id:
            out[kind] = doc_id
    return out


def parse_periods(body: Any) -> list[Period]:
    """목록 응답(세 탭 모두 같은 꼴)을 판매기간 행으로 바꾼다. 순서는 응답 그대로다."""
    out = []
    for r in _rows(body):
        code = str(r.get("goodsCode") or "").strip()
        start = _date(r.get("fromdate"))
        if not code or not start:
            continue
        out.append(Period(code, str(r.get("goodsName") or "").strip(), start, _date(r.get("todate")),
                          str(r.get("lCode") or "").strip() == "판매중", str(r.get("status") or "").strip(),
                          str(r.get("mCode") or "").strip(), str(r.get("gCode") or "").strip(),
                          str(r.get("sCode") or "").strip(), str(r.get("gubun") or "").strip(), _files(r)))
    return out


def total_rows(body: Any) -> int:
    rows = _rows(body)
    return int(rows[0].get("totalRows") or 0) if rows else 0


def documents_of(period: Period) -> list[Document]:
    """행 하나의 서류. 상품요약서가 없는 행이 있다(판매상품 288행 가운데 97행)."""
    types = {kind: t for kind, t in DOC_KINDS.values()}
    return [Document(period.code, period.name, kind, doc_id, types[kind], period.start, period.end)
            for kind, doc_id in period.files.items()]


def first_start(periods: list[Period], code: str) -> str | None:
    """상품코드의 판매 개시일: 그 코드의 판매기간 가운데 가장 이른 시작일. 전체 탭 응답으로 봐야 지난 기간까지 들어 있다."""
    starts = [p.start for p in periods if p.code == code]
    return min(starts) if starts else None


def pick_period(periods: list[Period], code: str | None = None, on: str | None = None) -> Period | None:
    """code(상품코드)의 판매기간 가운데 on(YYYY-MM-DD)이 속한 것. on이 없으면 시작일이 가장 늦은 것."""
    if code:
        periods = [p for p in periods if p.code == code]
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _post(session: Any, tab: str, form: dict[str, str]) -> Any:
    if tab not in TABS:
        raise ValueError(f"탭은 {sorted(TABS)} 가운데 하나: {tab!r}")
    # 화면(qs.stringify)과 같게 빈칸을 %20으로 싼다
    r = session.post(API + TABS[tab], data=urlencode(form, quote_via=quote), headers=AJAX, timeout=120)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def _form(keyword: str, m_code: str, g_code: str, s_code: str, year: str, page: int, rows: int) -> dict[str, str]:
    return {"mCode": m_code, "gCode": g_code, "sCode": s_code, "searchYear": year, "goodsName": keyword,
            "pageNo": str(page), "pageRows": str(rows)}


def list_products(session: Any, tab: str = "sales", keyword: str = "", m_code: str = ALL, g_code: str = ALL,
                  s_code: str = ALL, year: str = "", page_rows: int = 3000) -> list[Period]:
    """탭(all/sales/stop)의 판매기간 행. keyword는 상품명 일부. 응답의 totalRows만큼 쪽을 넘겨 모은다.

    판매상품 탭 전체가 한 쪽(약 150KB)에 왔다. 판매 개시일까지 보려면 tab="all"과 keyword로 좁혀 받는다.
    """
    out: list[Period] = []
    page = 1
    while True:
        body = _post(session, tab, _form(keyword, m_code, g_code, s_code, year, page, page_rows))
        rows = parse_periods(body)
        out += rows
        total = total_rows(body)
        if not rows or len(_rows(body)) < page_rows or page * page_rows >= total:
            return out
        page += 1


def search_products(session: Any, keyword: str, tab: str = "all") -> list[Period]:
    """상품명에 keyword가 든 판매기간 전부. 기본은 전체 탭(판매 중·중지 모두)이다."""
    return list_products(session, tab, keyword)


def list_documents(session: Any, code: str, keyword: str, on: str | None = None) -> list[Document]:
    """상품코드의 서류. keyword(상품명 일부)로 전체 탭을 검색해 그 코드의 판매기간을 고른다. on이 없으면 가장 최근 기간."""
    period = pick_period(search_products(session, keyword), code, on)
    return documents_of(period) if period else []


def viewer_url(doc: Document) -> str:
    """화면의 뷰어 창이 iframe에 여는 주소. name은 encodeURI 방식(쉼표와 괄호는 그대로)으로 싼다."""
    name = quote(doc.name, safe="-_.!~*'();/?:@&=+$,#")
    return (f"{VIEWER}?docID={quote(doc.doc_id, safe='')}&name={name}"
            "&isDown=false&loadingType=1&contentType=&docKey=&tsId=")


def pdf_url(viewer_html: str, viewer: str = VIEWER) -> str:
    """뷰어 HTML의 downloadURL을 절대 주소로. 없으면 ValueError."""
    m = _DOWNLOAD_URL.search(viewer_html or "")
    if not m:
        head = re.sub(r"\s+", " ", (viewer_html or "")[:200])
        raise ValueError(f"뷰어 응답에 downloadURL이 없음: {head}")
    return urljoin(viewer, m.group(1))


def download(session: Any, doc: Document) -> bytes:
    """뷰어 HTML을 받아 PDF 주소를 읽고 PDF를 받는다(요청 두 번). PDF가 아닌 응답은 ValueError."""
    page = viewer_url(doc)
    r = session.get(page, headers={"Referer": PCMS + "/partnerpage/CustomerPage_Unit.jsp"}, timeout=60)
    r.raise_for_status()
    url = pdf_url(r.content.decode("utf-8", errors="replace"), page)
    r = session.get(url, headers={"Referer": page}, timeout=300)
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): {url} | {head}")
    return r.content[start:]
