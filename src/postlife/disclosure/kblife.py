"""KB라이프생명 상품공시실(kblife.co.kr '공시실 > 상품공시실 > 상품목록')에서 상품 목록과 기초서류를 받는다.

공시 화면(/customer-common/productList.do)과 화면 스크립트(/res/pc/js/customer-common/productList.js)가 쓰는 요청을
그대로 따른다 (2026-11-19 확인).
- 상품 목록:     POST /customer-common/API/productList1.do  (폼, application/x-www-form-urlencoded)
                 pageSize, paGroupCnt, pageIndex, tabType, srchType(상품구분 코드, 비우면 전체), pdNm(상품명 일부)
                 → {"pagingVO": {...}, "list": [...]}. 한 행이 판매기간 하나이고, 상품마다 HEADER 1, 2, …로 이어진다.
                 pageSize는 행 수가 아니라 상품 수다. 화면은 20을 쓰지만 200을 보내도 그대로 받아 판매상품 160개(667행,
                 약 380KB)가 한 번에 왔다. 서류 파일 경로(UPFILE…)와 상품코드(P_CODE)가 같은 행에 있다.
- 서류 내려받기: GET  /api/archive/archives/download/<product-explain|product-terms>/<SEQNO>/<칸 번호>
                 화면은 먼저 같은 주소를 ajax로 불러 응답 머리에 text/plain이 있으면 "파일이 존재하지 않습니다"를 띄운다.
                 없는 파일을 불렀을 때 실제로 온 것은 상태 200, Content-Type 없음, 본문 0바이트였다.
                 Content-Disposition의 파일 이름은 UTF-8 바이트를 latin-1로 읽은 꼴로 온다
                 (예: 20261001_상품요약서_KB 딱좋은 요즘 건강보험 무배당(해약환급금 미지급형, 표준형)_v1.0.pdf).

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키 없는 새 세션의 첫 요청으로 목록과 PDF가 왔다.
공통 호출 함수(http.js의 http.ajax)는 cmmUtil.vestData로 본문을 싸지만, 이 화면은 그 함수를 쓰지 않고 $.ajax에
폼 값을 그대로 넘긴다. X-Requested-With와 Referer는 붙인 채로만 확인했으므로 그대로 붙여 보낸다.

tabType: "1" 판매상품, "2" 판매중지(KB라이프생명), "3" (구)KB생명, "4" (구)푸르덴셜생명, "5" (구)한일생명.
화면은 cpType 숨은 칸도 채우지만 요청에는 넣지 않는다. "1"과 "2"만 실제로 불러 보았다.
판매중지 탭의 행에는 상품요약서(UPFILE)가 없다. 판매상품 탭의 지난 판매기간 행에는 UPFILE이 있기도 한데,
화면은 판매종료일이 지난 행의 요약서 단추를 그리지 않는다. 그런 행(2026-07-01~09-30 판매기간)을 불러 보니 PDF가 왔으므로
이 모듈은 응답에 경로가 있는 서류를 모두 돌려준다.
상품마다 서류가 따로 등록되지만 내용은 같을 수 있다. 딱좋은 요즘 건강보험의 일반심사형(335000106)과
간편심사형(3.5.5)(331000106) 행에서 받은 요약서와 사업방법서는 바이트까지 같았다(한 서류가 모든 종을 다룬다).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib.parse import urlencode

BASE = "https://www.kblife.co.kr"
LIST_PAGE = BASE + "/customer-common/productList.do"
LIST_API = BASE + "/customer-common/API/productList1.do"
DOWNLOAD = BASE + "/api/archive/archives/download/"

SELLING, STOPPED, STOPPED_KB, STOPPED_PRUDENTIAL, STOPPED_HANIL = "1", "2", "3", "4", "5"
# 상품구분(srchType). 화면은 공통코드 INS_GROUP을 따로 받아 고르게 한다. 아래는 목록 응답의 TYPE_CODE에서 본 값이고,
# 걸러지는 것은 INS03만 확인했다.
CATEGORIES = {"INS02": "연금", "INS03": "보장", "INS06": "변액", "INS08": "단체", "INS09": "퇴직연금", "INS10": "특약"}
# 응답 칸 → (서류 이름, 주소의 fileno, 주소의 칸 번호). 화면 스크립트의 단추 연결과 같다.
# 표 머리는 요약서, 설명서, 방법서, 약관이다. UPFILE3, UPFILE4는 약관 칸에 단추를 하나 더 그리는 값인데 무엇인지 확인하지 않았다.
DOC_KINDS = {
    "UPFILE": ("상품요약서", "product-explain", "0"),
    "UPFILE5": ("상품설명서", "product-explain", "100"),
    "UPFILE1": ("사업방법서", "product-explain", "1"),
    "UPFILE2": ("약관", "product-terms", "2"),
    "UPFILE3": ("약관 추가1", "product-terms", "8"),
    "UPFILE4": ("약관 추가2", "product-terms", "9"),
}
FORM = "application/x-www-form-urlencoded; charset=UTF-8"
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": FORM,
    "Referer": LIST_PAGE,
}
PAGE_SIZE = 200


@dataclass(frozen=True)
class Period:
    """목록의 한 행 = 판매기간 하나. 개정마다 SEQNO가 새로 붙고, 상품코드(P_CODE)도 끝자리가 바뀌기도 한다."""
    seqno: str
    code: str                       # P_CODE. 제도성 특약에는 "NULL", "Z123456"처럼 여러 상품이 같은 값을 쓰는 것도 있다
    name: str
    start: str                      # 판매 개시일 YYYY-MM-DD
    end: str | None = None          # 판매 종료일. 열린 기간이면 None
    category: str = ""              # 구분(TYPE): 보장, 특약, 연금, 변액, 단체, 퇴직연금
    category_code: str = ""         # TYPE_CODE: INS03 …
    group_policy: bool = False      # PER_TYPE이 "G"(단체)인가. 개인은 "P"
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 서류 이름 → 서버 파일 경로


@dataclass(frozen=True)
class Product:
    """같은 상품의 판매기간을 모은 것. 응답에서 상품마다 HEADER가 1부터 이어진다. 상품명이 열쇠다."""
    name: str
    category: str
    periods: tuple[Period, ...]     # 응답 순서 그대로(최근 판매기간이 먼저)

    @property
    def code(self) -> str:
        return latest(self.periods).code if self.periods else ""

    @property
    def start(self) -> str:
        return latest(self.periods).start if self.periods else ""

    @property
    def open(self) -> bool:
        return any(p.end is None for p in self.periods)


@dataclass(frozen=True)
class Document:
    seqno: str
    code: str
    name: str
    kind: str          # 상품요약서 / 사업방법서 / 약관 …
    path: str          # 응답의 서버 파일 경로. 내려받기 주소에는 쓰지 않는다
    start: str
    end: str | None
    fileno: str = "product-explain"
    box: str = "0"

    @property
    def url(self) -> str:
        return f"{DOWNLOAD}{self.fileno}/{self.seqno}/{self.box}"


def _date(text: Any) -> str | None:
    """20260930 또는 2026/09/30 → 2026-09-30."""
    digits = re.sub(r"\D", "", str(text or ""))
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def _sale_dates(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """판매상품 탭은 "2026/10/01 ~ ", 판매중지 탭은 "2026/04/01~2026/06/30"처럼 온다. 종료일은 PROD_SALE_END_DATE를 먼저 본다."""
    parts = str(row.get("SALE_DATE") or "").split("~")
    start = _date(parts[0])
    end = _date(row.get("PROD_SALE_END_DATE")) or (_date(parts[1]) if len(parts) > 1 else None)
    return start, end


def _rows(body: Any) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        raise ValueError(f"KB라이프생명 응답이 JSON 객체가 아님: {type(body).__name__}")
    if body.get("_errCd") or body.get("code"):   # 공통 호출 함수(http.js)가 처리하는 오류 꼴. 이 화면에서 받아 본 적은 없다
        raise ValueError(f"KB라이프생명 응답 오류 {body.get('_errCd') or body.get('code')}: {body.get('message', '')}")
    rows = body.get("list")
    if not isinstance(rows, list):
        raise ValueError(f"KB라이프생명 응답에 list 목록이 없음: {sorted(body)}")
    return rows


def _files(row: dict[str, Any]) -> dict[str, str]:
    return {kind: str(row[key]).strip() for key, (kind, _, _) in DOC_KINDS.items() if str(row.get(key) or "").strip()}


def parse_periods(body: Any) -> list[Period]:
    """목록 응답의 행을 판매기간으로. 개시일이나 SEQNO가 없는 행은 버린다. 순서는 응답 그대로."""
    out = []
    for r in _rows(body):
        start, end = _sale_dates(r)
        if not start or r.get("SEQNO") is None:
            continue
        out.append(Period(str(r["SEQNO"]), str(r.get("P_CODE") or "").strip(), str(r.get("NAME") or "").strip(),
                          start, end, str(r.get("TYPE") or "").strip(), str(r.get("TYPE_CODE") or "").strip(),
                          str(r.get("PER_TYPE")) == "G", _files(r)))
    return out


def page_info(body: Any) -> tuple[int, int, int]:
    """(지금 쪽, 마지막 쪽, 상품 수). pageTotalCnt는 행 수가 아니라 상품 수다."""
    vo = body.get("pagingVO") if isinstance(body, dict) else None
    if not isinstance(vo, dict):
        raise ValueError("KB라이프생명 응답에 pagingVO가 없음")
    return int(vo.get("currentPgNo") or 1), int(vo.get("finalPgNo") or 1), int(vo.get("pageTotalCnt") or 0)


def group_products(periods: Iterable[Period]) -> list[Product]:
    """판매기간을 상품명으로 묶는다. 같은 상품의 행은 응답에서 이어져 온다. 처음 나온 순서를 지킨다."""
    groups: dict[str, list[Period]] = {}
    for p in periods:
        groups.setdefault(p.name, []).append(p)
    return [Product(name, ps[0].category, tuple(ps)) for name, ps in groups.items()]


def latest(periods: Iterable[Period]) -> Period:
    return max(periods, key=lambda p: p.start)


def pick_period(periods: Iterable[Period], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    periods = list(periods)
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return latest(periods) if periods else None


def documents_of(period: Period) -> list[Document]:
    """판매기간 한 행의 서류. 내려받기 주소는 파일 경로가 아니라 SEQNO와 칸 번호로 만든다."""
    by_kind = {kind: (fileno, box) for kind, fileno, box in DOC_KINDS.values()}
    return [Document(period.seqno, period.code, period.name, kind, path, period.start, period.end, *by_kind[kind])
            for kind, path in period.files.items()]


def _form(tab: str, category: str, name: str, page: int, page_size: int) -> str:
    # 화면의 paramCond와 같은 차례. jQuery처럼 빈칸은 +로 바꾼다
    return urlencode({"pageSize": page_size, "paGroupCnt": 10, "pageIndex": page, "tabType": tab,
                      "srchType": category, "pdNm": name})


def _post(session: Any, form: str) -> Any:
    r = session.post(LIST_API, data=form.encode("utf-8"), headers=AJAX, timeout=120)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def list_periods(session: Any, tab: str = SELLING, category: str = "", name: str = "",
                 page_size: int = PAGE_SIZE) -> list[Period]:
    """한 탭의 모든 판매기간. name은 상품명 일부(서버가 거른다), category는 상품구분 코드(INS03 …).
    판매상품 전체는 page_size 200이면 요청 한 번이다."""
    out: list[Period] = []
    page = 1
    while True:
        body = _post(session, _form(tab, category, name, page, page_size))
        out.extend(parse_periods(body))
        _, final, _ = page_info(body)
        if page >= final:
            return out
        page += 1


def list_products(session: Any, tab: str = SELLING, category: str = "", name: str = "",
                  page_size: int = PAGE_SIZE) -> list[Product]:
    return group_products(list_periods(session, tab, category, name, page_size))


_SPECIAL = re.compile(r"[()\[\]{}<>&'\"%]")


def keyword_of(name: str) -> str:
    """서버 검색에 보낼 상품명 일부. 괄호가 든 검색어는 이름이 그대로 같아도 0건이 왔다
    ("…무배당(간편심사형(3.5.5))(…)" → 0건, "딱좋은 요즘" → 18개). 첫 특수문자 앞까지만 보낸다."""
    return _SPECIAL.split(name, 1)[0].strip()


def list_documents(session: Any, name: str, on: str | None = None, tab: str = SELLING) -> list[Document]:
    """상품명(목록에 나온 그대로)의 서류. on: 조회 기준일 YYYY-MM-DD, 없으면 가장 최근 판매기간. 요청 한 번.
    서버에는 괄호 앞까지만 보내 거르고, 이름이 정확히 같은 행만 남긴다."""
    periods = [p for p in list_periods(session, tab, name=keyword_of(name)) if p.name == name.strip()]
    period = pick_period(periods, on)
    return documents_of(period) if period else []


def download(session: Any, doc: Document) -> bytes:
    r = session.get(doc.url, headers={"Referer": LIST_PAGE}, timeout=600)
    r.raise_for_status()
    # 파일이 없으면 화면은 응답 머리의 text/plain으로 가린다. 상태 코드에 기대지 않고 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.status_code}, {r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.url} | {head}")
    return r.content[start:]
