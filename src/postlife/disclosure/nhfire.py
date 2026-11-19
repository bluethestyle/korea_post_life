"""NH농협손해보험 보험상품공시(nhfire.co.kr)에서 상품 목록과 기초서류를 받는다.

공시 화면(/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
화면은 공통 호출 함수 devon.xSync(/js/xsync.js)의 fire()로 POST를 보낸다. 본문은 application/x-www-form-urlencoded
(이름과 값을 encodeURIComponent로 싼 것)이고, 응답은 application/xml 이다. xsync.js에는 XecureWeb 암호화 분기가 있지만
document.XecureWeb(옛 ActiveX)이 있을 때만 타므로 지금 브라우저에서는 평문이 간다.
- 상품구분 목록: POST /front/announce/retrievePdtDcd.ajax  type=ajax&pdtSelYn=Y&pdtGrCd=01
                 → 상품구분(pdtDcd, pdtDcdNm): 01 화재/재물, 05 건강/어린이 …
- 상품명 목록:   POST /front/announce/retrievePdtCd.ajax   type=ajax&pdtSelYn=Y&pdtGrCd=01&pdtDcd=(빈 값이면 상품군 전체)
                 판매중지 탭(pdtSelYn=N)은 basicDate=20120302&flag=A(2012-03-02 이후) 또는 20120301/B(이전)를 덧붙인다
                 → 상품코드(pdtCd), 상품명(pdtNm, addPdtNm, ntgDivdYn). 종마다, 개정판마다 상품코드가 따로 있다
                 (장기보험 판매상품 전체 112행 31KB, 판매중지 건강/어린이 531행 142KB)
- 서류 목록:     POST /front/announce/retrievePdtInfo.ajax  type=ajax&fileType=05&pdtCd=<상품코드>
                 → 판매기간마다 fileId 하나와 서류별 순번(plcnd 약관, smmr 상품요약서, ntclt 상품안내장, bzMtd 사업방법서,
                 fireMtd 업무방법서)과 파일 이름. 순번은 파일이 없어도 오고, 화면은 파일 이름이 빈 칸이면 '-'로 둔다
- 서류 내려받기: POST /imageView/downloadFile.ajax  fileId=<fileId>&afileSeqn=<순번>
                 → application/octet-stream, 파일 이름은 Content-Disposition에 있다.
                 없는 서류는 302(Location: http://www.nhfire.co.kr/file/downloadFile.nhfire, filename="nullnull")가 온다

응답 XML은 <xsync><LMultiData onAfterAction="…">칸 이름마다 같은 이름의 요소가 줄지어 온다</LMultiData></xsync> 꼴이다.
i번째 요소끼리 한 행이다. 화면은 기준 칸(상품구분은 pdtDcd, 서류는 fileId)의 개수만큼 돈다. 상품구분 응답은 pdtGrCd가
한 개 더 오기도 했다(8개 대 7개). 빈 값은 빈 CDATA로 온다.

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 새 세션의 첫 요청(쿠키 없음, Referer 없음)으로 같은 응답이 왔다.
웹 화면의 상품명 검색(retrieveInsuranceProductsAnnounceSearch.nhfire)은 400KB짜리 HTML 화면을 통째로 돌려주므로 쓰지 않고,
상품군 전체 목록을 받아 이름으로 거른다(find_products).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

BASE = "https://www.nhfire.co.kr"
LIST_PAGE = BASE + "/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire"
AJAX_CATEGORIES = "/front/announce/retrievePdtDcd.ajax"
AJAX_PRODUCTS = "/front/announce/retrievePdtCd.ajax"
AJAX_PERIODS = "/front/announce/retrievePdtInfo.ajax"
DOWNLOAD = BASE + "/imageView/downloadFile.ajax"
# 화면 1단계 '상품군'. 화면 HTML에 고정으로 적혀 있다
GROUPS = {"01": "장기보험", "02": "일반보험", "03": "자동차보험", "04": "농작물재해보험"}
# (응답 칸 이름 앞부분, 서류 종류). 화면 표의 칸 순서와 같다. 업무방법서는 농작물재해보험(상품코드 H…)에만 칸이 있다
DOC_KINDS = (("plcnd", "약관"), ("smmr", "상품요약서"), ("ntclt", "상품안내장"), ("bzMtd", "사업방법서"),
             ("fireMtd", "업무방법서"))
# 판매중지 탭의 기준일 단추: 2012년 3월 2일 이후(A, 화면 기본값)와 3월 1일 이전(B)
STOPPED_AFTER = ("20120302", "A")
STOPPED_BEFORE = ("20120301", "B")
OPEN_END = {"29991231", "99991231"}   # 화면이 '-'로 보이는 종료일
FORM = {"Content-Type": "application/x-www-form-urlencoded", "Referer": LIST_PAGE}


@dataclass(frozen=True)
class Category:
    """상품구분(화면 2단계)."""
    group: str      # 상품군 코드: 01 장기보험 …
    code: str       # 상품구분 코드(pdtDcd)
    name: str       # 화재/재물, 건강/어린이 …
    selling: bool


@dataclass(frozen=True)
class Product:
    """상품명 목록(화면 3단계)의 한 행. 종마다, 개정판마다 상품코드가 다르다."""
    code: str               # 상품코드(pdtCd). 예: D311887
    name: str               # 화면에 보이는 이름 그대로: ("(무)" if ntgDivdYn) + pdtNm + addPdtNm
    group: str = ""         # 상품군 코드
    category: str = ""      # 상품구분 코드. 제도성 특약 같은 행은 비어 온다
    selling: bool = True    # 판매상품 탭에서 왔는가


@dataclass(frozen=True)
class Period:
    """판매기간 한 건(서류 목록의 한 행). 같은 상품코드에 판매기간이 여러 번 붙는다(2026-04-01, 2026-07-01 …)."""
    code: str
    name: str
    start: str                      # 판매 개시일 YYYY-MM-DD
    end: str | None                 # 판매 종료일. 열린 기간이면 None
    file_id: str
    files: dict[str, tuple[str, str]] = field(default_factory=dict, compare=False, hash=False)  # 종류 → (순번, 파일 이름)


@dataclass(frozen=True)
class Document:
    code: str
    name: str
    kind: str          # 약관 / 상품요약서 / 상품안내장 / 사업방법서 / 업무방법서
    file_id: str
    seq: str           # afileSeqn
    file_name: str     # 공시실이 보여 주는 파일 이름 (내려받기 요청에는 쓰지 않는다)
    start: str
    end: str | None


def _date(text: str) -> str | None:
    digits = re.sub(r"\D", "", text or "")
    if len(digits) != 8 or digits in OPEN_END:
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def parse_columns(body: bytes | str) -> dict[str, list[str]]:
    """xsync 응답을 {칸 이름: 값 목록}으로 푼다. 오류 표시(xsync error 속성)나 XML이 아닌 응답은 ValueError."""
    raw = body.encode("utf-8") if isinstance(body, str) else bytes(body or b"")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        head = raw[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"NH농협손해보험 응답이 XML이 아님({e}): {head}") from None
    if root.tag != "xsync":
        raise ValueError(f"NH농협손해보험 응답의 뿌리 요소가 xsync가 아님: {root.tag}")
    if root.get("error"):   # 화면 스크립트(xsync.js callback)가 처리하는 오류 꼴. 실제 응답으로 받아 본 적은 없다
        raise ValueError(f"NH농협손해보험 응답 오류: {''.join(root.itertext()).strip()}")
    block = root.find("LMultiData")
    if block is None:
        raise ValueError(f"NH농협손해보험 응답에 LMultiData가 없음: {[c.tag for c in root]}")
    cols: dict[str, list[str]] = {}
    for el in block:
        cols.setdefault(el.tag, []).append(el.text or "")
    return cols


def _rows(cols: dict[str, list[str]], key: str) -> list[dict[str, str]]:
    """기준 칸(key)의 개수만큼 행을 만든다. 다른 칸이 모자라면 빈 값으로 채운다(화면의 eq(i)와 같다)."""
    n = len(cols.get(key, []))
    return [{k: (v[i] if i < len(v) else "") for k, v in cols.items()} for i in range(n)]


def display_name(row: dict[str, str]) -> str:
    """화면(fnSetPdtCdList)이 이름을 만드는 방식. pdtNm에 이미 "(무) "가 들어 있는 행도 있어 그대로 둔다."""
    prefix = "(무)" if row.get("ntgDivdYn") == "Y" else ""
    return (prefix + row.get("pdtNm", "") + row.get("addPdtNm", "")).strip()


def parse_categories(body: bytes | str, group: str = "") -> list[Category]:
    out = []
    for r in _rows(parse_columns(body), "pdtDcd"):
        if r["pdtDcd"]:
            out.append(Category(r.get("pdtGrCd") or group, r["pdtDcd"], r.get("pdtDcdNm", "").strip(),
                                r.get("pdtSelYn", "Y") != "N"))
    return out


def parse_products(body: bytes | str, selling: bool = True) -> list[Product]:
    out = []
    for r in _rows(parse_columns(body), "pdtCd"):
        code = r["pdtCd"].strip()
        if code:
            out.append(Product(code, display_name(r), r.get("pdtGrCd", ""), r.get("pdtDcd", ""), selling))
    return out


def parse_periods(body: bytes | str) -> list[Period]:
    """서류 목록. 화면처럼 cfmtYn이 Y나 빈 값인 행만 남긴다. 파일 이름이 빈 서류는 뺀다. 개시일 순으로 돌려준다."""
    cols = parse_columns(body)
    rows = _rows(cols, "fileId")
    # 화면은 상품코드와 이름을 첫 행 값으로 쓴다
    code = (cols.get("pdtCd") or [""])[0]
    name = display_name({k: (v[0] if v else "") for k, v in cols.items()})
    out = []
    for r in rows:
        start = _date(r.get("pdtSelStDt", ""))
        if not start or not r["fileId"] or r.get("cfmtYn", "") not in ("Y", ""):
            continue
        files = {kind: (r.get(f"{key}AfileSeqn", "").strip(), r.get(f"{key}AfileNm", "").strip())
                 for key, kind in DOC_KINDS if r.get(f"{key}AfileNm", "").strip()}
        out.append(Period(code, name, start, _date(r.get("pdtSelEdDt", "")), r["fileId"].strip(), files))
    return sorted(out, key=lambda p: p.start)


def documents_of(period: Period) -> list[Document]:
    return [Document(period.code, period.name, kind, period.file_id, seq, file_name, period.start, period.end)
            for kind, (seq, file_name) in period.files.items() if seq]


def pick_period(periods: list[Period], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def find_products(products: list[Product], *words: str) -> list[Product]:
    """이름에 words가 모두 든 상품. 빈칸은 무시하고 비교한다."""
    keys = [re.sub(r"\s+", "", w) for w in words]
    return [p for p in products if all(k in re.sub(r"\s+", "", p.name) for k in keys)]


def _form(fields: list[tuple[str, str]]) -> bytes:
    """xsync.addQuery와 같은 본문: encodeURIComponent(이름)=encodeURIComponent(값)를 &로 잇는다."""
    enc = lambda s: quote(str(s), safe="-_.!~*'()")  # noqa: E731
    return "&".join(f"{enc(k)}={enc(v)}" for k, v in fields).encode("ascii")


def _post(session: Any, path: str, fields: list[tuple[str, str]]) -> bytes:
    r = session.post(BASE + path, data=_form(fields), headers=FORM, timeout=60)
    r.raise_for_status()
    return r.content


def list_categories(session: Any, group: str = "01", selling: bool = True) -> list[Category]:
    return parse_categories(_post(session, AJAX_CATEGORIES, [("type", "ajax"), ("pdtSelYn", "Y" if selling else "N"),
                                                             ("pdtGrCd", group)]), group)


def list_products(session: Any, group: str = "01", category: str = "", selling: bool = True,
                  before_2012: bool = False) -> list[Product]:
    """상품군(group)의 상품명 목록. category를 비우면 상품군 전체가 한 번에 온다(화면의 '전체').

    판매중지 탭은 기준일 단추에 따라 2012-03-02 이후(기본) 또는 이전 상품만 온다.
    """
    fields = [("type", "ajax"), ("pdtSelYn", "Y" if selling else "N"), ("pdtGrCd", group), ("pdtDcd", category)]
    if not selling:
        date, flag = STOPPED_BEFORE if before_2012 else STOPPED_AFTER
        fields += [("basicDate", date), ("flag", flag)]
    return parse_products(_post(session, AJAX_PRODUCTS, fields), selling)


def list_periods(session: Any, code: str) -> list[Period]:
    """상품코드의 판매기간과 서류. 판매 중·중지 상품 모두 같은 요청이다."""
    return parse_periods(_post(session, AJAX_PERIODS, [("type", "ajax"), ("fileType", "05"), ("pdtCd", code)]))


def list_documents(session: Any, code: str, on: str | None = None) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 요청 한 번."""
    period = pick_period(list_periods(session, code), on)
    return documents_of(period) if period else []


def download(session: Any, doc: Document) -> bytes:
    # 없는 서류는 302로 다른 화면에 보낸다. 따라가지 않고 오류로 알린다
    r = session.post(DOWNLOAD, data=_form([("fileId", doc.file_id), ("afileSeqn", doc.seq)]), headers=FORM,
                     timeout=300, allow_redirects=False)
    if 300 <= r.status_code < 400:
        raise ValueError(f"PDF가 아닌 응답(상태 {r.status_code}, {r.headers.get('Location', '')}): "
                         f"{doc.file_id}/{doc.seq} {doc.file_name}")
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.file_id}/{doc.seq} {doc.file_name} | {head}")
    return r.content[start:]
