"""미래에셋생명 공시실(life.miraeasset.com)의 '상품목록'에서 상품 목록과 기초서류를 받는다.

공시 화면(/micro/disclosure/product/PC-HO-080301-000000.do)과 그 스크립트(comExcelDraw.js, comUtil.js)가 쓰는 요청을
그대로 따른다 (2026-11-19 확인). 목록 요청은 모두 POST 폼(application/x-www-form-urlencoded; charset=UTF-8)이고
응답은 JSON이다. 탭 값 text1은 판매 중 탭이 "판매중인상품", 판매중지 탭이 "판매중지상품"이다.
- 상품분류 목록: POST /micro/disclosure/selectProdDvsnGroup.do  workDvsn=D, text1=탭
                 → {"prodDvsnData": [{"text2": "보장성▷건강/암", "seq"}]}
- 상품 목록:     POST /micro/disclosure/selectWorkDvsnDataPaging.do  workDvsn=D, text1=탭, text2=상품분류(빈칸은 전체),
                 text3=상품명 일부(빈칸은 전체), pageNum=0부터
                 → {"list": [...], "rows": 전체 행 수, "pageNum": 1부터, "totalPage"}. 한 번에 100행까지 온다.
                 행 하나가 판매기간 하나이고, 칸 값은 행의 jsonData(JSON 글)에 cell0~cell8로 들어 있다.
                 판매중인상품 탭: cell0 분류, cell1 상품명, cell2 시작일, cell3 종료일(열린 기간은 ""), cell4 상품요약서,
                 cell5 약관, cell6 사업방법서, cell7 경로. 판매중지상품 탭은 cell4가 최종판매일이고 서류와 경로가 한 칸씩 밀린다.
                 상품명 검색은 이름 일부 일치다("M-케어 건강보험(간편고지)"로 해약환급금이 없는 유형까지 18행이 오고,
                 "(간편고지, 갱신형)"은 오지 않았다).
- 서류 내려받기: POST /micro/cmmnFileDown.do  pathType=gongci_u1, fileName=파일 이름, orgFileName=파일 이름,
                 filePath="/uploadwas/life/" + 경로. 경로가 "/"로 시작해 "//"가 생기지만 화면과 같게 그대로 보낸다.
                 파일이 없으면 상태 200, text/html 화면(alert "파일이 존재하지 않습니다.")이 온다.

로그인, 세션 쿠키, 토큰, 암호화는 필요 없다. 새 세션의 첫 요청으로 목록과 PDF가 왔다.
다만 Accept 머리에 application/json이 없으면 상태 200으로 "페이지: " 뒤에 HTML 안내 화면이 온다
(curl로 Accept만 바꿔 가며 확인했다. Accept-Language와 charset은 상관이 없었다).

목록은 공시 담당자가 올린 엑셀을 옮긴 것이다(행마다 title "2026년 08월공시", file_nm "...xlsx"가 붙어 온다).
2026-11-19 조회 때 모든 행이 2026-08-19에 올린 파일 하나에서 왔다. 그 뒤의 개정은 목록에 없을 수 있다.

상품코드는 목록에 없고 서류 파일 이름("상품명_상품요약서_20260711.pdf")에도 없다. 사업방법서 표지의 상품코드 표
(A3729 등)와 누리집 상품안내 메뉴(/home/prod/getProdList.do)의 publicCd가 같은 값이었다. 상품안내 메뉴에는
누리집에서 안내하는 상품만 있다. 파일 이름의 날짜는 판매 시작일과 다를 수 있다(2026-07-11 기간의 사업방법서가 _20260701).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

BASE = "https://life.miraeasset.com"
LIST_PAGE = BASE + "/micro/disclosure/product/PC-HO-080301-000000.do"
GROUPS = "/micro/disclosure/selectProdDvsnGroup.do"
PAGING = "/micro/disclosure/selectWorkDvsnDataPaging.do"
DOWNLOAD = BASE + "/micro/cmmnFileDown.do"
PRODUCT_MENU = BASE + "/home/prod/getProdList.do"
SELLING_TAB = "판매중인상품"
STOPPED_TAB = "판매중지상품"
WORK = "D"               # 화면의 workDvsn. 상품목록 엑셀의 업무 구분이다
PATH_PREFIX = "/uploadwas/life/"
PATH_TYPE = "gongci_u1"  # 화면 스크립트에 "임시"라고 적혀 있다. 바뀌면 내려받기가 실패한다
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",   # 없으면 JSON 대신 안내 화면이 온다
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": LIST_PAGE,
}
# 탭마다 서류 칸의 자리가 다르다 (칸 이름 → 서류 종류). 경로 칸도 다르다.
_CELLS = {
    True: ({"cell4": "상품요약서", "cell5": "약관", "cell6": "사업방법서"}, "cell7"),
    False: ({"cell5": "상품요약서", "cell6": "약관", "cell7": "사업방법서"}, "cell8"),
}


@dataclass(frozen=True)
class Document:
    name: str
    kind: str         # 상품요약서 / 사업방법서 / 약관
    file_name: str    # 내려받기 요청에 그대로 넣는 이름
    path: str         # 목록의 경로 칸. 예: /html/gongci/upload/1/
    start: str
    end: str | None


@dataclass(frozen=True)
class Period:
    """상품 목록의 한 행. 판매기간 하나와 그 기간의 서류 파일 이름."""
    name: str
    category: str                   # 상품분류. 예: 보장성▷건강/암, 보장성▷간편고지/간편심사
    start: str                      # 판매 개시일 YYYY-MM-DD
    end: str | None = None          # 판매 종료일. 열린 기간이면 None
    selling: bool = True            # 판매중인상품 탭에서 왔는가. 이 탭에도 닫힌 지난 기간이 함께 온다
    path: str = ""
    last_sale: str | None = None    # 판매중지상품 탭의 최종판매일
    seq: str = ""                   # 행 번호(응답의 seq)
    source: str = ""                # 행이 온 공시 자료의 제목. 예: 2026년 08월공시
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)   # 서류 종류 → 파일 이름 칸

    def documents(self) -> list[Document]:
        """화면처럼 한 칸에 줄바꿈으로 여러 파일이 오면 따로 나눈다(화면 스크립트에 그 처리가 있다. 실제로 본 적은 없다)."""
        return [Document(self.name, kind, f.strip(), self.path, self.start, self.end)
                for kind, cell in self.files.items() for f in cell.split("\n") if f.strip()]


@dataclass(frozen=True)
class Page:
    periods: list[Period]
    rows: int         # 조건에 맞는 전체 행 수
    page: int         # 1부터 센 쪽 번호(응답 그대로)
    pages: int        # 전체 쪽 수


def _date(text: Any) -> str | None:
    """2026-07-11, 20260711, 2026.07.11 → 2026-07-11. 빈칸이면 None."""
    digits = re.sub(r"\D", "", str(text or ""))
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def _json(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        head = re.sub(r"\s+", " ", text[:200])
        raise ValueError(f"미래에셋생명 응답이 JSON이 아님({len(raw)}바이트): {head}") from None


def _object(body: Any, key: str) -> list[Any]:
    if not isinstance(body, dict):
        raise ValueError(f"미래에셋생명 응답이 JSON 객체가 아님: {type(body).__name__}")
    rows = body.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"미래에셋생명 응답에 {key} 목록이 없음: {sorted(body)}")
    return rows


def parse_categories(body: Any) -> list[str]:
    """상품분류 목록. 화면처럼 빈 값은 버린다."""
    return [str(r.get("text2") or "").strip() for r in _object(body, "prodDvsnData") if str(r.get("text2") or "").strip()]


def _cells(item: dict[str, Any]) -> list[dict[str, Any]]:
    """행의 jsonData를 푼다. 화면은 $(JSON.parse(jsonData)).each로 돌므로 객체 하나와 목록 둘 다 받는다."""
    data = item.get("jsonData")
    data = json.loads(data) if isinstance(data, str) else data
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    raise ValueError(f"미래에셋생명 목록 행의 jsonData를 읽을 수 없음: {str(item.get('jsonData'))[:100]}")


def parse_period(cells: dict[str, Any], selling: bool, seq: str = "", source: str = "") -> Period | None:
    """칸 값(cell0~cell8) 하나를 판매기간으로. 시작일이 없는 행은 None."""
    start = _date(cells.get("cell2"))
    name = str(cells.get("cell1") or "").strip()
    if not start or not name:
        return None
    doc_cells, path_cell = _CELLS[selling]
    files = {kind: str(cells[c]).strip() for c, kind in doc_cells.items() if str(cells.get(c) or "").strip()}
    return Period(name, str(cells.get("cell0") or "").strip(), start, _date(cells.get("cell3")), selling,
                  str(cells.get(path_cell) or "").strip(), _date(cells.get("cell4")) if not selling else None,
                  seq, source, files)


def parse_page(body: Any, selling: bool = True) -> Page:
    """상품 목록 한 쪽. 행의 탭 이름(sheetNm)이 요청한 탭과 다르면 그 행의 칸 자리를 따른다."""
    periods = []
    for item in _object(body, "list"):
        for cells in _cells(item):
            tab = str(cells.get("sheetNm") or "")
            row_selling = selling if tab not in (SELLING_TAB, STOPPED_TAB) else tab == SELLING_TAB
            p = parse_period(cells, row_selling, str(item.get("seq") or ""), str(item.get("title") or "").strip())
            if p:
                periods.append(p)
    return Page(periods, int(body.get("rows") or 0), int(body.get("pageNum") or 0), int(body.get("totalPage") or 0))


def parse_codes(body: Any) -> dict[str, str]:
    """누리집 상품안내 메뉴 응답에서 공시 상품명(publicNm) → 상품코드(publicCd).

    화면의 공통 호출(cmmnUtil.js ajaxCmmn)은 응답에 sCmmnEncrypt가 있으면 풀어서 쓴다. 2026-11-19에는 평문이 왔다.
    암호화된 응답이 오면 풀지 않고 오류로 알린다.
    """
    if isinstance(body, dict) and body.get("sCmmnEncrypt"):
        raise ValueError("미래에셋생명 상품안내 응답이 암호화되어 왔음(sCmmnEncrypt)")
    out = {}
    for r in _object(body, "prodInfo"):
        data = r.get("JSON_DATA")
        try:
            data = json.loads(data) if isinstance(data, str) else (data or {})
        except ValueError:
            data = {}
        name = str(data.get("publicNm") or "").strip()
        code = str(data.get("publicCd") or r.get("PROD_CD") or "").strip()
        if name and code:
            out[name] = code
    return out


def pick_period(periods: list[Period], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _post(session: Any, path: str, form: dict[str, str]) -> Any:
    r = session.post(BASE + path, data=form, headers=AJAX, timeout=60)
    r.raise_for_status()
    return _json(r.content)


def _tab(selling: bool) -> str:
    return SELLING_TAB if selling else STOPPED_TAB


def list_categories(session: Any, selling: bool = True) -> list[str]:
    return parse_categories(_post(session, GROUPS, {"workDvsn": WORK, "text1": _tab(selling)}))


def list_page(session: Any, selling: bool = True, category: str = "", keyword: str = "", page: int = 0) -> Page:
    """상품 목록 한 쪽(100행까지). page는 0부터 센다. 응답의 page는 1부터 센다."""
    form = {"workDvsn": WORK, "text1": _tab(selling), "text2": category, "text3": keyword, "pageNum": str(page)}
    return parse_page(_post(session, PAGING, form), selling)


def list_products(session: Any, selling: bool = True, category: str = "", keyword: str = "") -> list[Period]:
    """조건에 맞는 모든 판매기간. 분류와 검색어를 다 비우면 탭 전체(판매 중 탭 1,055행, 11번 요청)를 돈다."""
    first = list_page(session, selling, category, keyword, 0)
    out = list(first.periods)
    for n in range(1, first.pages):
        out += list_page(session, selling, category, keyword, n).periods
    return out


def search_products(session: Any, keyword: str, selling: bool = True) -> list[Period]:
    """상품명에 keyword가 든 판매기간. 이름 일부 일치라 다른 상품이 섞일 수 있다."""
    return list_products(session, selling, "", keyword)


def list_documents(session: Any, name: str, on: str | None = None, selling: bool = True) -> list[Document]:
    """상품명(목록에 나온 그대로)의 서류. on은 조회 기준일 YYYY-MM-DD이고, 없으면 가장 최근 판매기간."""
    wanted = name.strip()
    period = pick_period([p for p in search_products(session, wanted, selling) if p.name == wanted], on)
    return period.documents() if period else []


def product_codes(session: Any) -> dict[str, str]:
    """누리집 상품안내 메뉴의 공시 상품명 → 상품코드. 누리집에서 안내하는 상품만 있다."""
    r = session.post(PRODUCT_MENU, data={"nowHash": ""}, headers={**AJAX, "Referer": BASE + "/home/index.do"}, timeout=60)
    r.raise_for_status()
    return parse_codes(_json(r.content))


def download(session: Any, doc: Document) -> bytes:
    form = {"pathType": PATH_TYPE, "fileName": doc.file_name, "orgFileName": doc.file_name,
            "filePath": PATH_PREFIX + doc.path}
    r = session.post(DOWNLOAD, data=form, headers={"Referer": LIST_PAGE}, timeout=600)
    r.raise_for_status()
    # 파일이 없어도 상태 코드는 200이고 본문이 안내 화면(HTML)이다. 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        text = r.content.decode("utf-8", errors="replace")
        alert = re.search(r'alert\("([^"]{1,100})"\)', text)
        head = alert.group(1) if alert else re.sub(r"\s+", " ", text[:200])
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): {doc.file_name} | {head}")
    return r.content[start:]
