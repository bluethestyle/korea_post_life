"""신한라이프 공시실(shinhanlife.co.kr)의 '상품공시 > 전체상품'에서 상품 목록과 기초서류를 받는다.

공시 화면(/hp/cdhi0030.do 판매중, /hp/cdhi0040t01.do 판매중지)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
화면 스크립트는 공통 함수 dp.Ajax.send(dp.common.js)로 부른다. 이 함수는 trId에 ".pwkjson"을 붙인 주소로
{"elData": 조회 조건, "userHeader": {"scrnId": 화면 ID, "appliDtptDutjCd": "DH"}}를 JSON으로 POST하고,
머리에 X-AJAX-CALL, Proworks-Body, Proworks-Lang을 붙인다. 응답은 {"elHeader": {"resSuc": ...}, "elData": {...}} 꼴이다.
- 상품 목록:   POST /co/wcms/nodeInfoListPage.pwkjson  elData {"catId": CAT_ID, "method": "selectListGoods",
               "meta06": "TRUE"(판매중) | "FALSE"(판매중지), "meta02": 상품구분, "meta03": 보장구분, "title": 상품명 일부,
               "pageSize", "pageIndex"}. 판매중지는 "meta01": 회사 탭("신한라이프", "신한생명", "오렌지라이프")을 더 보낸다.
               → nodeInfoVoList: 상품(상품명 × 상품구분)마다 가장 최근 판매기간 한 행. listCount, totalPageCount가 함께 온다.
               판매중 전체가 pageSize 1000 요청 한 번에 123행(168KB)으로 왔다. 화면은 50행씩 넘긴다
- 판매기간 이력: POST /co/wcms/nodeInfoList.pwkjson    elData {"method": "selectAllListGoods", "meta05": 상품명,
               "meta02", "meta03", 나머지는 목록 조건 그대로} → 목록 행을 뺀 지난 판매기간들(종료일 있음, 최근 것이 먼저)
- 서류 내려받기: GET  /bizxpress/<경로>  목록 행의 meta09(상품요약서), meta10(사업방법서), meta11(약관)이
               "/repo/DigitalPlattform/cdh/cdhi/gd/pr/__etc/사업방법서_….pdf" 꼴로 오고, 화면(dp.Utils.getFileObject)은
               앞의 "/repo/<wsId>"를 "/bizxpress"로 바꾼 뒤 encodeURI로 싸서 새 창으로 연다

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키 없는 첫 요청으로 목록이 왔다(응답이 JSESSIONID 등 쿠키를 심지만
다음 요청에 쓰지 않았다). 응답의 sessionTokenKey, securityData, e2e_data1 칸은 모두 null이었다.
상품코드(meta04, 예: 7000375)는 손으로 넣는 값으로 보인다. 지난 판매기간에는 비어 있거나 다른 값(7000317)이고,
같은 코드가 여러 상품명(원(ONE)과 원(ONE)Core)에 붙고, 자릿수가 틀린 값(700327, 70004300)도 있다.
요약서는 지금 판매기간 행에만 있고, 지난 판매기간과 판매중지 상품 행에는 사업방법서와 약관만 있다.
같은 상품이 상품구분(일반, TM …)마다 따로 한 행씩 나온다. 원(ONE)의 일반, TM 행은 세 서류 파일이 같았다.
없는 서류 주소는 302로 /error.html에 넘어간다. 응답 머리의 inOutDataEnc가 true지만 요청과 응답 본문은 평문 JSON이었다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

BASE = "https://www.shinhanlife.co.kr"
LIST_PAGE = BASE + "/hp/cdhi0030.do"
STOPPED_PAGE = BASE + "/hp/cdhi0040t01.do"
LIST_TR = "/co/wcms/nodeInfoListPage.pwkjson"
HISTORY_TR = "/co/wcms/nodeInfoList.pwkjson"
FILE_ROOT = "/bizxpress"
CAT_ID = "M160991914330045272"          # 화면 스크립트(cdhi0030.js, cdhi0040t01.js)에 박힌 상품공시 카테고리
# 화면의 단추 연결과 같다. meta13(실손)도 단추가 있지만 판매중 목록에 값이 온 행은 없었다.
DOC_KINDS = {"meta09": "상품요약서", "meta10": "사업방법서", "meta11": "약관"}
# 화면 검색 조건의 선택지. 상품구분 "일반"이 대면 채널이다
CHANNELS = ("일반", "CM", "TM", "인터넷모바일", "방카", "단체", "중도부가특약", "특약")
KINDS = ("보장", "생사혼합/저축", "연금", "제도성특약")
COMPANIES = ("신한라이프", "신한생명", "오렌지라이프")   # 판매중지 화면의 탭. (구)신한생명, (구)오렌지라이프 상품
AJAX = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json; charset=UTF-8",
    "X-AJAX-CALL": "true",
    "Proworks-Body": "Y",
    "Proworks-Lang": "ko",
}
_OPEN_END = "99991231"


@dataclass(frozen=True)
class Product:
    """목록의 한 행 = 상품 하나의 판매기간 하나. 목록 요청은 가장 최근 판매기간을, 이력 요청은 지난 판매기간을 준다."""
    name: str                       # meta05. "<br>"이 든 이름도 있다(화면은 innerHTML로 넣는다)
    code: str                       # meta04. 비어 있을 수 있고 상품마다 하나라는 보장도 없다
    channel: str                    # meta02 상품구분: 일반(대면), TM, CM, 인터넷모바일, 방카, 단체 …
    kind: str                       # meta03 보장구분: 보장, 연금, 생사혼합/저축, 제도성특약
    start: str                      # meta07 판매 개시일 YYYY-MM-DD
    end: str | None                 # meta08. 99991231이면 None(지금 열린 기간)
    selling: bool                   # meta06 "TRUE"/"FALSE". 판매중 목록이면 지난 판매기간 행도 TRUE다
    periods: int = 1                # meta15 판매기간 수(지금 것 포함). 1보다 크면 화면에 상세 단추가 생긴다
    company: str = ""               # meta01 신한라이프 / 신한생명 / 오렌지라이프
    node: str = ""                  # ndId
    ws: str = "DigitalPlattform"    # wsId. 서류 경로의 /repo/<wsId>를 /bizxpress로 바꾸는 데 쓴다
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 서류 종류 → 경로

    @property
    def documents(self) -> list[Document]:
        return [Document(self.name, self.code, kind, path, self.start, self.end, self.ws) for kind, path in self.files.items()]


@dataclass(frozen=True)
class Document:
    name: str
    code: str
    kind: str          # 상품요약서 / 사업방법서 / 약관
    path: str          # 응답에 온 경로 그대로 (/repo/DigitalPlattform/…)
    start: str
    end: str | None
    ws: str = "DigitalPlattform"

    @property
    def file_name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def url(self) -> str:
        return file_url(self.path, self.ws)


def file_url(path: str, ws: str = "DigitalPlattform") -> str:
    """화면의 dp.Utils.getFileObject와 encodeURI를 따른다. 빈칸, 한글, 대괄호는 바꾸고 쉼표와 괄호는 그대로 둔다."""
    prefix = "/repo/" + ws
    if path.startswith(prefix):
        path = FILE_ROOT + path[len(prefix):]
    return BASE + quote(path, safe=";,/?:@&=+$!*'()#")


def _date(text: Any) -> str | None:
    """20260804000000 → 2026-08-04. 99991231…(열린 기간)과 빈 값은 None."""
    digits = re.sub(r"\D", "", str(text or ""))[:8]
    if len(digits) != 8 or digits == _OPEN_END:
        return None
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def _int(text: Any) -> int:
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return 1


def _data(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError(f"신한라이프 응답이 JSON 객체가 아님: {type(body).__name__}")
    head = body.get("elHeader")
    if not isinstance(head, dict):
        raise ValueError(f"신한라이프 응답에 elHeader가 없음: {sorted(body)}")
    if head.get("resSuc") is not True:   # 화면 스크립트(dp.Ajax.send)가 실패로 보는 꼴
        vo = head.get("resMsgVo") or {}
        code = vo.get("msgId") or head.get("resCode")
        msg = vo.get("basicMsgCtt") or head.get("resMsg")
        raise ValueError(f"신한라이프 응답 오류 {code}: {msg}")
    data = body.get("elData")
    if not isinstance(data, dict) or not isinstance(data.get("nodeInfoVoList"), list):
        raise ValueError(f"신한라이프 응답에 nodeInfoVoList 목록이 없음: {sorted(data) if isinstance(data, dict) else data}")
    return data


def _files(row: dict[str, Any]) -> dict[str, str]:
    return {kind: str(row[key]).strip() for key, kind in DOC_KINDS.items() if str(row.get(key) or "").strip()}


def parse_products(body: Any) -> list[Product]:
    """목록(selectListGoods)과 이력(selectAllListGoods) 응답의 행. 개시일이 없는 행은 버린다."""
    out = []
    for r in _data(body)["nodeInfoVoList"]:
        start = _date(r.get("meta07"))
        name = str(r.get("meta05") or "").strip()
        if not start or not name:
            continue
        out.append(Product(name, str(r.get("meta04") or "").strip(), str(r.get("meta02") or "").strip(),
                           str(r.get("meta03") or "").strip(), start, _date(r.get("meta08")),
                           str(r.get("meta06") or "").upper() == "TRUE", _int(r.get("meta15")),
                           str(r.get("meta01") or "").strip(), str(r.get("ndId") or ""),
                           str(r.get("wsId") or "DigitalPlattform"), _files(r)))
    return out


def page_count(body: Any) -> int:
    return _int(_data(body).get("totalPageCount"))


def pick_period(periods: list[Product], on: str | None = None) -> Product | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _post(session: Any, path: str, screen: str, el: dict[str, Any]) -> Any:
    body = {"elData": {**el, "scrnId": screen}, "userHeader": {"scrnId": screen, "appliDtptDutjCd": "DH"}}
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")   # 화면의 JSON.stringify와 같은 꼴
    r = session.post(BASE + path, data=data, headers={**AJAX, "Referer": f"{BASE}/hp/{screen}.do"}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def _list_el(selling: bool, channel: str, kind: str, search: str, company: str, page_size: int, page: int) -> dict[str, Any]:
    el: dict[str, Any] = {"catId": CAT_ID, "pageSize": page_size, "pageIndex": page, "method": "selectListGoods",
                          "meta02": channel, "meta03": kind, "title": search, "meta06": "TRUE" if selling else "FALSE"}
    if not selling:
        el["meta01"] = company
    return el


def _screen(selling: bool) -> str:
    return "cdhi0030" if selling else "cdhi0040t01"


def list_products(session: Any, selling: bool = True, channel: str = "", kind: str = "", search: str = "",
                  company: str = "신한라이프", page_size: int = 1000) -> list[Product]:
    """판매중(또는 판매중지) 목록. channel, kind는 화면 선택지 값(빈칸이면 전체), search는 상품명 일부.

    company는 판매중지 목록에서만 쓴다. 쪽이 여럿이면 totalPageCount만큼 넘긴다(쪽 넘김은 실제로 돌려 보지 않았다).
    """
    out: list[Product] = []
    page, pages = 1, 1
    while page <= pages:
        body = _post(session, LIST_TR, _screen(selling), _list_el(selling, channel, kind, search, company, page_size, page))
        out += parse_products(body)
        pages = page_count(body)
        page += 1
    return out


def list_periods(session: Any, product: Product) -> list[Product]:
    """상품의 모든 판매기간(목록 행 + 지난 판매기간). 개시일 순. 판매기간이 하나뿐이면 요청하지 않는다."""
    if product.periods <= 1:
        return [product]
    el = {**_list_el(product.selling, "", "", "", product.company or "신한라이프", 50, 1),
          "method": "selectAllListGoods", "detailRow": "0",
          "meta05": product.name, "meta02": product.channel, "meta03": product.kind}
    past = parse_products(_post(session, HISTORY_TR, _screen(product.selling), el))
    rows = {(p.start, p.end): p for p in [*past, product]}
    return sorted(rows.values(), key=lambda p: p.start)


def find_product(products: list[Product], name: str, channel: str = "일반") -> Product | None:
    """목록에서 상품명(그대로)과 상품구분이 같은 행."""
    return next((p for p in products if p.name == name and (not channel or p.channel == channel)), None)


def list_documents(session: Any, name: str, on: str | None = None, channel: str = "일반", selling: bool = True) -> list[Document]:
    """상품명의 서류. on(YYYY-MM-DD)이 없거나 지금 판매기간에 들면 요청 한 번, 지난 판매기간이면 두 번."""
    product = find_product(list_products(session, selling, channel=channel, search=name), name, channel)
    if product is None:
        return []
    period = product if on is None or pick_period([product], on) else pick_period(list_periods(session, product), on)
    return period.documents if period else []


def download(session: Any, doc: Document) -> bytes:
    """없는 파일이면 서버가 302로 /error.html에 넘기고, 따라가면 상태 200의 HTML이 온다. 본문이 PDF인지로 가린다."""
    r = session.get(doc.url, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.status_code}, {r.headers.get('Content-Type', '')}, {len(r.content)}바이트, "
                         f"{getattr(r, 'url', '')}): {doc.file_name} | {head}")
    return r.content[start:]
