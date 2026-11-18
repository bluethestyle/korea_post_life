"""한화생명 상품공시실(hanwhalife.com)에서 상품 목록과 기초서류를 받는다.

공시실 화면이 쓰는 요청을 그대로 따른다 (2026-11-18 확인).
- 상품구분 목록: POST /main/disclosure/goods/goodslist/getList.do   sellFlag=Y|N, schText
- 상품 목록:     POST /main/disclosure/goods/goodslist/getList2.do  sellFlag, sellType, goodsType, schText
- 서류 목록:     POST /main/disclosure/goods/goodslist/getList3.do  goodsIndex=<상품번호>
- 서류 내려받기: POST https://file.hanwhalife.com/www/announce/goods/download_chk.asp  file_name (EUC-KR)

암호화나 토큰은 없다. 화면의 hwlife.secure.ajax는 폼을 그대로 보내면서 __MENU_ID와 _r_(난수)만
덧붙이는데, 둘 다 없어도 응답이 같았다. 쿠키 없이 첫 요청으로 보내도 된다.
X-Requested-With와 Referer는 붙인 채로만 확인했으므로 그대로 붙여 보낸다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

BASE = "https://www.hanwhalife.com"
FILE_BASE = "https://file.hanwhalife.com"
LIST_PAGE = (BASE + "/main/disclosure/goods/disclosurenotice/DF_GDDN000_P10000.do"
             "?MENU_ID1=DF_GDGL000&MENU_ID2=DF_GDGL000_P10000")
API = BASE + "/main/disclosure/goods/goodslist/"
DOWNLOAD = FILE_BASE + "/www/announce/goods/download_chk.asp"
# FILE_NAME4(주요내용요약서)도 응답에 오지만 비교에 쓰는 세 가지만 받는다.
DOC_KINDS = {"FILE_NAME1": "상품요약서", "FILE_NAME2": "사업방법서", "FILE_NAME3": "약관"}
FORM = "application/x-www-form-urlencoded"
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": LIST_PAGE,
    "Content-Type": FORM + "; charset=UTF-8",
}


@dataclass(frozen=True)
class Product:
    code: str        # 공시실 상품번호(IDX)
    name: str
    selling: bool    # 판매상품 목록에서 왔으면 True, 판매중지상품 목록이면 False
    category: str    # 상품구분과 종류. 예: "개인 보장성"


@dataclass(frozen=True)
class Document:
    code: str
    kind: str        # 상품요약서 / 사업방법서 / 약관
    file_name: str   # 내려받기 요청에 그대로 넣는 이름
    start: str       # 이 서류가 적용되는 판매 시작일 YYYY-MM-DD
    end: str | None  # 판매 종료일. 지금 판매 중인 판이면 None


def _date(text: Any) -> str | None:
    text = str(text or "").strip()   # 판매 중이면 종료일이 빈칸 10개로 온다
    return text or None


def _rows(body: dict[str, Any], key: str) -> list[dict[str, Any]]:
    status = body.get("status") or {}
    if status.get("code") != "0000":
        raise ValueError(f"공시실 조회 실패: {status}")
    return body.get(key) or []


def parse_categories(body: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(sellType, goodsType, 표시 이름) 목록. 예: ("SA", "GA", "개인 보장성")"""
    return [(str(r["SELL_TYPE"]), str(r["GOODS_TYPE"]), f'{r.get("SELL_TYPE_NM", "")} {r.get("GOODS_TYPE_NM", "")}'.strip())
            for r in _rows(body, "list1")]


def parse_products(body: dict[str, Any], selling: bool, category: str = "") -> list[Product]:
    return [Product(str(r["IDX"]), str(r.get("GOODS_NAME", "")).strip(), selling, category)
            for r in _rows(body, "list2") if r.get("IDX") is not None]


def parse_documents(code: str, body: dict[str, Any]) -> list[Document]:
    """판매기간별 서류를 모두 돌려준다. 순서는 응답 그대로(최근 판이 먼저).

    상품요약서는 지금 판매 중인 판에만 있고, 지난 판에는 사업방법서와 약관만 있다.
    """
    out = []
    for row in _rows(body, "list3"):
        start = _date(row.get("SELL_START_DT"))
        if not start:
            continue
        for key, kind in DOC_KINDS.items():
            name = row.get(key)
            if name:
                out.append(Document(code, kind, str(name), start, _date(row.get("SELL_END_DT"))))
    return out


def pick_version(docs: list[Document], on: str | None = None) -> list[Document]:
    """on(YYYY-MM-DD)에 판매 중이던 판의 서류만 남긴다. on이 없으면 가장 최근 판."""
    if not docs:
        return []
    if on is None:
        start = max(d.start for d in docs)
        return [d for d in docs if d.start == start]
    return [d for d in docs if d.start <= on and (d.end is None or on <= d.end)]


def _post(session: Any, name: str, **params: str) -> dict[str, Any]:
    form = {"PType": "1", "sellFlag": "Y", "goodsType": "", "sellType": "", "goodsIndex": "", "schText": "", **params}
    r = session.post(API + name, data=urlencode(form, quote_via=quote), headers=AJAX, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def list_products(session: Any, selling: bool = True, search: str = "") -> list[Product]:
    """search는 상품명 일부(화면 입력칸은 20자까지). 비우면 전체 목록.

    getList.do는 상품구분 목록 전체와 '첫 번째 상품구분'의 상품만 돌려주므로,
    나머지 상품구분은 getList2.do로 하나씩 조회한다.
    """
    flag = "Y" if selling else "N"
    first = _post(session, "getList.do", sellFlag=flag, schText=search)
    seen: dict[str, Product] = {}
    for i, (sell_type, goods_type, label) in enumerate(parse_categories(first)):
        body = first if i == 0 else _post(session, "getList2.do", sellFlag=flag, sellType=sell_type,
                                          goodsType=goods_type, schText=search)
        for p in parse_products(body, selling, label):
            seen.setdefault(p.code, p)
    return list(seen.values())


def list_documents(session: Any, code: str, on: str | None = None) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 비우면 가장 최근 판. 판매중지 상품도 같은 요청으로 조회된다."""
    return pick_version(parse_documents(code, _post(session, "getList3.do", goodsIndex=str(code))), on)


def download(session: Any, doc: Document) -> bytes:
    # 파일 서버는 이름을 EUC-KR로 받는다. UTF-8로 보내면 "파일이 존재하지 않아" 안내 화면이 온다.
    try:
        body = "file_name=" + quote(doc.file_name, encoding="cp949")
    except UnicodeEncodeError as e:
        raise ValueError(f"EUC-KR로 옮길 수 없는 파일 이름: {doc.file_name}") from e
    r = session.post(DOWNLOAD, data=body, headers={**AJAX, "Content-Type": FORM}, timeout=600)
    r.raise_for_status()
    # 파일이 없어도 상태 코드는 200이고 본문만 안내 화면(EUC-KR)이다. 문서 시작 표식으로 가린다.
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("cp949", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}): {doc.file_name} | {head}")
    return r.content[start:]
