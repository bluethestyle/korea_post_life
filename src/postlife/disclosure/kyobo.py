"""교보생명 공시실(kyobo.com)의 '전체상품조회'에서 상품 목록과 기초서류를 받는다.

공시 화면(/dgt/web/product-official/all-product/search, 화면 코드 PDSDRNL9001PS)이 쓰는 요청을 그대로 따른다
(2026-11-19 확인). 화면의 공통 호출 함수(kyobo.common.js kyobo.ajax.json)는 객체를 JSON.stringify 해서 POST로 보내고
_NOW_PAGE_CD 머리(화면 코드)만 덧붙인다. 응답은 {"header": {"code", "message"}, "body": ...} 꼴이다.
- 상품 목록/검색: POST /dtc/product-official/find-allProductSearch
                 {"dgtPdtAtrDvCd": "M", "dgtPdtAtrMclCd": 보험종류, "dgtPdtAtrSmclCd": 소분류, "saleYn": "Y"|"N"|"99",
                  "searchTxt": 검색어, "currentPage", "pagePerSize", ...}
                 → body.list. 한 행이 공시 목록 한 줄이고, 최근 판매기간의 서류 파일 이름(a1 상품요약서, a2 약관,
                 a3 사업방법서)이 들어 있다. pagePerSize 1000도 받아 주어 판매중 206행이 요청 한 번에 왔다(363KB)
- 서류 목록:     POST /dtc/product-official/find-allProductSearchDetail  {"dgtPdtPdSeqtId": 목록 행의 dgtPdtAtrSeqtId}
                 → body.list(판매기간: saleStDt, saleEdDt)와 body.list2(같은 순서로 temp01~03 파일 이름).
                 최근 판매기간이 먼저 오고, 상품요약서(temp01)는 대개 가장 최근 판매기간에만 있다
- 서류 내려받기: GET  /file/ajax/download?fName=/dtc/pdf/mm/<encodeURI(temp 파일 이름)>
                 없는 파일이면 상태 404와 {"header": {"code": "404", "message": "FAIL"}, "body": null}이 온다

로그인, 세션 쿠키, 토큰, 암호화는 없다. 쿠키 없이 첫 요청으로 보냈고, 서류 목록은 _NOW_PAGE_CD와 Accept 머리 없이도
같은 꼴로 왔다(머리는 화면과 같게 붙여 보낸다). 요청이 잘못되면 상태 200에 header.code "FAIL", body null이 온다.

상품코드(dgtPdtCd)는 한 상품에 하나가 아니다. 세대가 바뀐 상품(교보마이플랜건강보험 → 교보마이플랜건강보험Ⅱ가 모두
1001031)과 중도부가특약 행이 같은 코드를 쓴다. 목록 한 줄을 가리키는 번호는 dgtPdtAtrSeqtId(Product.seq)다.
응답에는 담당자 이름(rgrNm)과 직원 번호(fsInUsrId 등)도 오는데, 이 모듈은 읽지 않는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib.parse import quote

BASE = "https://www.kyobo.com"
LIST_PAGE = BASE + "/dgt/web/product-official/all-product/search"
PAGE_CODE = "PDSDRNL9001PS"
SEARCH = BASE + "/dtc/product-official/find-allProductSearch"
DETAIL = BASE + "/dtc/product-official/find-allProductSearchDetail"
DOWNLOAD = BASE + "/file/ajax/download?fName=/dtc/pdf/mm/"
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json; charset=UTF-8",
    "Referer": LIST_PAGE,
    "_NOW_PAGE_CD": PAGE_CODE,
}
# 화면의 '보험종류' 선택 상자. 대면 채널 상품은 PAMS04(보장성보험)에, 같은 상품의 다이렉트판("[D]")은 PAMS06에 있다
CATEGORIES = {
    "PAMS01": "교육보험", "PAMS02": "연금보험", "PAMS03": "저축보험", "PAMS04": "보장성보험", "PAMS05": "기업보험",
    "PAMS06": "통신판매전용상품", "PAMS07": "방카슈랑스전용상품", "PAMS08": "퇴직연금", "PAMS09": "퇴직보험",
    "PAMS10": "온라인보험",
}
SUBCATEGORIES = {
    "PAMS02": {"01": "적격", "02": "비적격", "03": "계약인수", "04": "기타"},
    "PAMS04": {"01": "재해상해", "02": "암/건강", "03": "종신/정기", "04": "중도부가특약/기타"},
    "PAMS05": {"01": "보장", "02": "저축", "03": "연금"},
    "PAMS08": {"01": "운용관리계약", "02": "보험자산관리계약"},
}
# 화면의 '기간별 다운로드' 표와 같은 순서. 퇴직연금·퇴직보험(PAMS08, PAMS09)은 첫 칸이 계약서다.
# 목록 행(a1~a7)과 서류 목록(temp01~05)에는 칸이 더 있지만 화면은 세 칸만 쓰고, 연금 상품은 a4~a7을 다른 뜻으로 쓴다
DOC_KINDS = ("상품요약서", "약관", "사업방법서")
_CONTRACT_FIRST = ("PAMS08", "PAMS09")
_OPEN_END = "0001-01-01 BC"   # 화면 스크립트가 '종료일 없음'으로 다루는 값. 실제 응답에서 본 적은 없다
# 화면의 fileDownload는 encodeURI를 쓴다. 다만 &, +, #는 주소의 뜻을 바꾸므로 싸서 보낸다(지금까지 본 이름에는 없었다)
_URI_SAFE = "-_.!~*'();/?:@=$,"


def _kinds(category: str) -> tuple[str, str, str]:
    return ("계약서",) + DOC_KINDS[1:] if category in _CONTRACT_FIRST else DOC_KINDS


@dataclass(frozen=True)
class Product:
    """공시 목록 한 줄."""
    seq: str                  # dgtPdtAtrSeqtId. 서류 목록 요청에 넣는 번호
    code: str                 # dgtPdtCd. 세대가 바뀐 상품, 중도부가특약 행과 같이 쓰므로 고유하지 않다
    name: str
    selling: bool             # saleYn == "Y"
    category: str = ""        # 보험종류 코드 PAMS04 …
    subcategory: str = ""     # 소분류 코드 02 … (PAMS02·04·05·08만 쓴다)
    start: str | None = None  # 목록의 saleStDt. 판매중 행은 최근 판매기간 개시일과 맞았다. 판매중지 행은 마지막
                              # 판매기간과 다르게 오기도 하므로(종료 다음날) 판매기간은 list_documents로 본다
    rider_addon: bool = False  # dgtMseAddiPsYn == "Y": 기존 계약에 덧붙이는 '중도부가특약' 행
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 최근 판매기간 서류 종류 → 파일 이름

    @property
    def label(self) -> str:
        """화면 목록의 '보험종류' 칸. 예: 보장성보험(암/건강)"""
        sub = SUBCATEGORIES.get(self.category, {}).get(self.subcategory, "")
        return CATEGORIES.get(self.category, "") + (f"({sub})" if sub else "")


@dataclass(frozen=True)
class Document:
    seq: str            # 상품 목록 행 번호 (Product.seq)
    period: str         # 판매기간 번호 (dgtPdtPdSeqtId)
    kind: str           # 상품요약서 / 약관 / 사업방법서 (퇴직연금·퇴직보험은 상품요약서 자리가 계약서)
    file_name: str      # 내려받기 요청에 그대로 넣는 이름(temp). 앞에 "ZjE2MDZkYWUt_" 같은 저장 키가 붙어 있다
    real_name: str      # 화면에 보이는 원래 파일 이름(real)
    start: str          # 판매기간 개시일 YYYY-MM-DD
    end: str | None     # 판매기간 종료일. 지금 판매 중인 기간이면 None
    name: str = ""      # 상품명 (Product에서 넘겨받았을 때만)


def _date(text: Any) -> str | None:
    text = str(text or "").strip()
    if not text or text == _OPEN_END:
        return None
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _body(resp: Any) -> Any:
    """응답 머리가 SUCCESS인지 보고 body를 돌려준다. 실패는 상태 200에 header.code "FAIL"로 온다."""
    if not isinstance(resp, dict) or not isinstance(resp.get("header"), dict):
        raise ValueError(f"교보생명 응답 꼴이 다름: {type(resp).__name__} {sorted(resp) if isinstance(resp, dict) else ''}")
    head = resp["header"]
    if head.get("code") != "SUCCESS":
        raise ValueError(f"교보생명 응답 오류 {head.get('code')}: {head.get('message')}")
    return resp.get("body")


def _files(row: dict[str, Any], prefix: str, category: str) -> dict[str, str]:
    """a1~a3 또는 temp01~03 칸을 서류 종류별 파일 이름으로."""
    keys = ("a1", "a2", "a3") if prefix == "a" else (f"{prefix}01", f"{prefix}02", f"{prefix}03")
    return {kind: _text(row.get(key)) for key, kind in zip(keys, _kinds(category)) if _text(row.get(key))}


def parse_products(resp: Any) -> list[Product]:
    body = _body(resp)
    rows = body.get("list") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise ValueError("교보생명 목록 응답에 list가 없음")
    out = []
    for r in rows:
        name = _text(r.get("dgtPdtAtrNm"))
        if r.get("dgtPdtAtrSeqtId") is None or not name:
            continue
        category = _text(r.get("dgtPdtAtrMclCd"))
        out.append(Product(str(r["dgtPdtAtrSeqtId"]), _text(r.get("dgtPdtCd")), name, r.get("saleYn") == "Y",
                           category, _text(r.get("dgtPdtAtrSmclCd")), _date(r.get("saleStDt")),
                           r.get("dgtMseAddiPsYn") == "Y", _files(r, "a", category)))
    return out


def page_count(resp: Any) -> int:
    info = (_body(resp) or {}).get("pageInfo") or {}
    return int(info.get("totPageCnt") or 1)


def parse_documents(resp: Any, product: Product | None = None) -> list[Document]:
    """서류 목록 응답. 판매기간(list)과 파일 이름(list2)이 같은 순서로 온다. 순서는 응답 그대로(최근 판매기간이 먼저)."""
    body = _body(resp)
    periods = body.get("list") if isinstance(body, dict) else None
    files = body.get("list2") if isinstance(body, dict) else None
    if not isinstance(periods, list) or not isinstance(files, list):
        raise ValueError("교보생명 서류 목록 응답에 list/list2가 없음")
    if len(periods) != len(files):
        raise ValueError(f"교보생명 서류 목록의 판매기간({len(periods)})과 파일 행({len(files)}) 수가 다름")
    category = product.category if product else ""
    out = []
    for p, f in zip(periods, files):
        start = _date(p.get("saleStDt"))
        if not start:
            continue
        seq = str(p.get("dgtPdtAtrSeq") or (product.seq if product else ""))
        temps, reals = _files(f, "temp", category), _files(f, "real", category)
        for kind, temp in temps.items():
            out.append(Document(seq, str(p.get("dgtPdtPdSeqtId") or ""), kind, temp, reals.get(kind, temp),
                                start, _date(p.get("saleEdDt")), product.name if product else ""))
    return out


def pick_version(docs: Iterable[Document], on: str | None = None) -> list[Document]:
    """on(YYYY-MM-DD)에 판매 중이던 판매기간의 서류만 남긴다. on이 없으면 개시일이 가장 늦은 판매기간."""
    docs = list(docs)
    if on is not None:
        docs = [d for d in docs if d.start <= on and (d.end is None or on <= d.end)]
    if not docs:
        return []
    start = max(d.start for d in docs)
    return [d for d in docs if d.start == start]


def _post(session: Any, url: str, body: dict[str, Any]) -> Any:
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")   # 화면의 JSON.stringify와 같은 꼴
    r = session.post(url, data=data, headers=AJAX, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def _flag(selling: bool | None) -> str:
    return "99" if selling is None else ("Y" if selling else "N")


def search_products(session: Any, keyword: str = "", selling: bool | None = True, category: str = "99",
                    subcategory: str = "99", page_size: int = 1000) -> list[Product]:
    """화면의 검색과 같다. keyword는 상품명 일부, selling None은 판매여부 '전체'. 쪽이 여럿이면 끝까지 넘긴다."""
    out: list[Product] = []
    page = 1
    while True:
        resp = _post(session, SEARCH, {
            "dgtPdtAtrDvCd": "M", "dgtPdtAtrLclCd": "", "dgtPdtAtrMclCd": category, "dgtPdtAtrSmclCd": subcategory,
            "saleYn": _flag(selling), "dgtMseAddiPsYn": "", "searchTxt": keyword,
            "currentPage": page, "pagePerSize": page_size, "pageNumber": 10, "deviceDv": "pc",
        })
        out += parse_products(resp)
        if page >= page_count(resp) or page >= 100:
            return out
        page += 1


def list_products(session: Any, selling: bool | None = True) -> list[Product]:
    """판매중(또는 판매중지, None이면 전체) 상품 전부. 판매중은 요청 한 번(206행, 2026-11-19)."""
    return search_products(session, "", selling)


def all_documents(session: Any, product: Product | str) -> list[Document]:
    """모든 판매기간의 서류. product는 Product나 목록 행 번호(dgtPdtAtrSeqtId)."""
    seq = product.seq if isinstance(product, Product) else str(product)
    return parse_documents(_post(session, DETAIL, {"dgtPdtPdSeqtId": seq}),
                           product if isinstance(product, Product) else None)


def list_documents(session: Any, product: Product | str, on: str | None = None) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 판매중지 상품도 같은 요청으로 조회된다."""
    return pick_version(all_documents(session, product), on)


def file_url(file_name: str) -> str:
    return DOWNLOAD + quote(file_name, safe=_URI_SAFE)


def download(session: Any, doc: Document | str) -> bytes:
    file_name = doc.file_name if isinstance(doc, Document) else doc
    r = session.get(file_url(file_name), headers={"Referer": LIST_PAGE}, timeout=600)
    # 없는 파일은 상태 404와 JSON으로 온다. 상태 코드보다 먼저 문서 시작 표식으로 가려 서버의 안내 글을 오류에 싣는다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답(상태 {r.status_code}, {r.headers.get('Content-Type', '')}, "
                         f"{len(r.content)}바이트): {file_name} | {head}")
    return r.content[start:]
