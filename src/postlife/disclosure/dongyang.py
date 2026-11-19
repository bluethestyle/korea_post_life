"""동양생명 상품공시실(pbano.myangel.co.kr)에서 판매상품 목록과 기초서류를 받는다.

공시실은 본 누리집(www.myangel.co.kr, 화면을 스크립트로 그리는 SPA)과 따로 있는 JSP 사이트다. 본 누리집 머리말의
"공시실" 링크가 /notice/product/WE_PA_AP_01_00_00.jsp를 열고, 거기서 '판매상품' 화면으로 간다 (2026-11-19 확인).
- 판매상품 목록:   POST /paging/WE_AC_WEPAAP020100L  폼(mainform). 응답은 서버가 그린 HTML 표이고 10행씩 온다.
                   첫 쪽은 _biz_op_code=IQY, 다음 쪽은 화면의 PP_Query처럼 _biz_op_code=_Q, _paging_action=PP,
                   _paging_dw_name=dw_99, _paging_page_idx=N. _paging_dw_99_ds_fetch_count를 100으로 보내도 10행씩 왔다.
                   거르기: sale_kind(판매채널 코드), goods_kind(구분 코드), nameStr(상품명 일부). 모두 "ALL"/""이면 전체.
- 지난 판매기간:   POST /process/WE_AC_WEPAAP020100D  _biz_op_code=IQY_D, GOODS_NM=상품명, SALE_KIND=판매채널 코드
                   → {"isLogin": false, "dw": {"dw_00": [...]}}. JSON 앞에 빈 줄이 여러 개 붙어 온다.
                   닫힌 판매기간만 오고, 지금 열린 판매기간은 목록 행에만 있다. 목록 행에 이 요청을 부르는 링크
                   (selectDetailGoods)가 있는 상품만 지난 판매기간이 있다.
- 서류 내려받기:   POST /process/CO_ComDownload  _biz_op_code=FDL, FILE_GRP_ID=<서류 값>, FILE_PATH, FILE_NAME,
                   USER_FILE_NM(셋 다 빈칸). 화면의 MasFiledownload와 같다. 파일 이름은 Content-Disposition에
                   UTF-8 바이트로 온다(requests가 latin-1로 읽은 꼴). 없는 값을 보내면 상태 404와 안내 HTML이 온다.

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키 없는 새 세션의 첫 요청으로 목록 쪽, 지난 판매기간, 내려받기가
모두 됐다. 서류 값(FILE_GRP_ID, 32자)은 세션을 바꿔 받아도 같았다(첫 쪽 30개 대조).
상품코드는 공시실 응답에도, 상품요약서와 사업방법서 글자에도 없다. 목록의 '번호'는 화면 순번일 뿐이다.
판매중지상품 화면(/paging/WE_AC_WEPAAP020201L)은 주소만 확인했고 요청은 보내 보지 않았다.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Any

BASE = "https://pbano.myangel.co.kr"
LIST_PAGE = BASE + "/paging/WE_AC_WEPAAP020100L"
HISTORY = BASE + "/process/WE_AC_WEPAAP020100D"
DOWNLOAD = BASE + "/process/CO_ComDownload"
# 목록 표의 서류 칸 순서(머리행: 상품요약서, 사업방법서, 보험약관, 운용관리계약서)와 지난 판매기간 응답의 FILE_GRP_ID1~4.
# FILE_GRP_ID5도 응답에 오지만 화면이 쓰지 않고 값이 온 적도 없다.
DOC_KINDS = ("상품요약서", "사업방법서", "약관", "운용관리계약서")
# 화면 '판매채널 선택'의 값. 지난 판매기간 요청의 SALE_KIND도 같은 값이다(목록 행의 selectDetailGoods 넷째 값).
CHANNELS = {"01": "일반보험", "02": "단체보험", "03": "제휴/서비스보험", "04": "방카슈랑스", "05": "온라인보험", "06": "기타"}
GOODS_KINDS = {"01": "보장성", "02": "저축성", "03": "연금", "05": "퇴직연금/보험", "08": "제도성특약"}
PAGE_SIZE = 10
_FORM = {   # 화면의 mainform 그대로. 쪽마다 _biz_op_code, _paging_action, _paging_dw_name, _paging_page_idx만 바뀐다
    "_biz_op_code": "IQY", "_biz_dw_00": "", "pagenum": "1", "sale_kind": "ALL", "goods_kind": "ALL", "nameStr": "",
    "_paging_action": "null", "_paging_dw_name": "null", "_paging_row_idx": "0", "_paging_page_idx": "1",
    "_paging_dw_99_row_idx": "-1", "_paging_dw_99_page_idx": "-1", "_paging_dw_99_total_row_count": "-1",
    "_paging_dw_list": "dw_99", "_paging_dw_99_ds_fetch_count": str(PAGE_SIZE),
    "saleCode": "ALL", "goodsCode": "ALL", "searchWord": "",
}
_AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": LIST_PAGE,
}
_TOTAL = re.compile(r"총\s*<strong>\s*(\d+)\s*</strong>\s*건")
_TBODY = re.compile(r"<tbody>(.*?)</tbody>", re.S)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_FILE = re.compile(r"MasFiledownload\(\s*'[^']*'\s*,\s*'([^']+)'")
_DETAIL = re.compile(r"selectDetailGoods\(\s*this\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']*)'")
_TAG = re.compile(r"<[^>]+>")
_NOISE = re.compile(r"<(script|style)\b.*?</\1>|<!--.*?-->", re.S | re.I)
# 상품명으로 거르면 이름 속 검색어를 <b>로 감싸 온다: 무배당우리WON하는간편<b>보장보험</b>(갱신형). 글자 사이 태그는 빈칸 없이 지운다
_INLINE = re.compile(r"</?(?:b|strong|span|font|em|i|u|mark)\b[^>]*>", re.I)


@dataclass(frozen=True)
class Product:
    """판매상품 목록의 한 행. 지금 열린 판매기간 하나와 그 서류 값이 들어 있다."""
    name: str
    channel: str                    # 판매채널: 일반보험(설계사 채널), 단체보험, 제휴/서비스보험, 방카슈랑스, 온라인보험, 기타
    kind: str                       # 구분: 보장성, 저축성, 연금, 퇴직연금/보험, 제도성특약
    start: str                      # 지금 판매기간의 개시일 YYYY-MM-DD
    end: str | None = None          # 판매상품 목록에서는 늘 비어 왔다
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)   # 서류 종류 → FILE_GRP_ID
    sale_kind: str = ""             # 지난 판매기간 요청에 보내는 판매채널 코드. 지난 판매기간이 없는 상품은 ""
    no: str = ""                    # 화면 순번. 상품코드가 아니고, 검색 결과마다 다시 매긴다

    @property
    def has_history(self) -> bool:
        return bool(self.sale_kind)


@dataclass(frozen=True)
class Period:
    """지난 판매기간 한 건(닫힌 기간). 같은 서류가 여러 판매기간에 걸쳐 다시 걸리기도 한다(파일 이름의 날짜가 앞선다)."""
    name: str
    start: str
    end: str | None
    channel: str = ""
    kind: str = ""
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)        # 서류 종류 → FILE_GRP_ID
    file_names: dict[str, str] = field(default_factory=dict, compare=False, hash=False)   # 서류 종류 → 파일 이름


@dataclass(frozen=True)
class Document:
    name: str
    kind: str          # 상품요약서 / 사업방법서 / 약관 / 운용관리계약서
    file_id: str       # FILE_GRP_ID. 내려받기 요청에 그대로 넣는 값
    start: str
    end: str | None
    file_name: str = ""   # 지난 판매기간 응답에만 있다. 지금 판매기간의 이름은 내려받을 때 응답 머리로 온다


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", _INLINE.sub("", _NOISE.sub(" ", cell))))).strip()


def _date(text: Any) -> str | None:
    """2026.10.01 또는 20261001 → 2026-10-01."""
    digits = re.sub(r"\D", "", str(text or ""))
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def parse_list(page_html: str) -> tuple[int, list[Product]]:
    """판매상품 목록 한 쪽 → (전체 건수, 행들). 목록 표가 없는 응답(오류 화면 등)이면 ValueError."""
    total = _TOTAL.search(page_html)
    body = _TBODY.search(page_html)
    if not total or not body:
        raise ValueError(f"동양생명 판매상품 목록 표가 없는 응답: {_text(page_html)[:150]}")
    out = []
    for tr in _TR.findall(body.group(1)):
        tds = _TD.findall(tr)
        if len(tds) < 9:
            continue
        start = _date(_text(tds[4]))
        name = _text(tds[3])
        if not (name and start):
            continue
        files = {}
        for kind, cell in zip(DOC_KINDS, tds[6:10]):
            m = _FILE.search(cell)
            if m:          # 서류가 없는 칸은 "-"이거나 alert('준비중입니다…') 링크다
                files[kind] = m.group(1)
        detail = _DETAIL.search(tds[3])
        out.append(Product(name, _text(tds[1]), _text(tds[2]), start, _date(_text(tds[5])), files,
                           detail.group(1) if detail else "", _text(tds[0])))
    return int(total.group(1)), out


def _history_body(text: str) -> Any:
    try:
        return json.loads(text.strip())       # 응답 앞에 빈 줄이 붙어 온다
    except json.JSONDecodeError as e:
        raise ValueError(f"동양생명 지난 판매기간 응답이 JSON이 아님: {text.strip()[:120]!r}") from e


def parse_history(body: Any) -> list[Period]:
    """지난 판매기간 응답(JSON 객체 또는 응답 글자) → 판매기간들. 응답 순서 그대로(최근 것이 먼저)."""
    if isinstance(body, (str, bytes)):
        body = _history_body(body.decode("utf-8") if isinstance(body, bytes) else body)
    rows = (body.get("dw") or {}).get("dw_00") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"동양생명 지난 판매기간 응답에 dw.dw_00 목록이 없음: {sorted(body) if isinstance(body, dict) else type(body).__name__}")
    out = []
    for r in rows:
        start = _date(r.get("SALE_START_DT"))
        if not start:
            continue
        files, names = {}, {}
        for i, kind in enumerate(DOC_KINDS, 1):
            file_id = str(r.get(f"FILE_GRP_ID{i}") or "").strip()
            if file_id:
                files[kind] = file_id
                names[kind] = str(r.get(f"FILE_NM{i}") or "").strip()
        out.append(Period(html.unescape(str(r.get("GOODS_NM") or "")).strip(), start, _date(r.get("SALE_FINISH_DT")),
                          str(r.get("SALE_KIND_NM") or "").strip(), str(r.get("GOODS_KIND_NM") or "").strip(), files, names))
    return out


def documents_of(item: Product | Period) -> list[Document]:
    """한 판매기간의 서류들. 순서는 DOC_KINDS."""
    names = getattr(item, "file_names", {})
    return [Document(item.name, kind, item.files[kind], item.start, item.end, names.get(kind, ""))
            for kind in DOC_KINDS if kind in item.files]


def attachment_name(content_disposition: str | None) -> str:
    """내려받기 응답의 Content-Disposition에서 파일 이름. 서버는 UTF-8 바이트를 그대로 보내고 requests는 latin-1로 읽는다."""
    m = re.search(r'filename="?([^";]+)"?', content_disposition or "")
    if not m:
        return ""
    raw = m.group(1).strip()
    try:
        return raw.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return raw


def _post_list(session: Any, form: dict[str, str]) -> str:
    r = session.post(LIST_PAGE, data=form, headers={"Referer": LIST_PAGE}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def list_products(session: Any, sale_kind: str = "ALL", goods_kind: str = "ALL", search: str = "",
                  max_pages: int = 30) -> list[Product]:
    """판매상품 목록 전체(쪽마다 요청 한 번, 2026-11-19 기준 59행 6쪽). sale_kind는 CHANNELS, goods_kind는 GOODS_KINDS의 코드."""
    form = {**_FORM, "sale_kind": sale_kind, "goods_kind": goods_kind, "nameStr": search,
            "saleCode": sale_kind, "goodsCode": goods_kind, "searchWord": search}
    total, products = parse_list(_post_list(session, form))
    page = 1
    while len(products) < total and page < max_pages:
        page += 1
        _, rows = parse_list(_post_list(session, {**form, "_biz_op_code": "_Q", "_paging_action": "PP",
                                                  "_paging_dw_name": "dw_99", "_paging_page_idx": str(page)}))
        if not rows:
            break
        products += rows
    return products


def list_history(session: Any, product: Product) -> list[Period]:
    """상품의 지난(닫힌) 판매기간들. 목록 행에 지난 판매기간 링크가 없는 상품은 요청하지 않고 빈 목록."""
    if not product.has_history:
        return []
    r = session.post(HISTORY, data={"_biz_op_code": "IQY_D", "GOODS_NM": product.name, "SALE_KIND": product.sale_kind},
                     headers=_AJAX, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return parse_history(r.text)


def list_documents(session: Any, product: Product, on: str | None = None) -> list[Document]:
    """on(YYYY-MM-DD)에 판매 중이던 판매기간의 서류. on이 없거나 지금 판매기간 안이면 요청 없이 목록 행의 서류."""
    if on is None or on >= product.start:
        return documents_of(product)
    for period in list_history(session, product):
        if period.start <= on and (period.end is None or on <= period.end):
            return documents_of(period)
    return []


def download(session: Any, doc: Document) -> bytes:
    form = {"_biz_op_code": "FDL", "FILE_GRP_ID": doc.file_id, "FILE_PATH": "", "FILE_NAME": "", "USER_FILE_NM": ""}
    r = session.post(DOWNLOAD, data=form, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()      # 없는 값이면 404
    # 상태 200이라도 PDF가 아니면 오류로 본다. 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = _text(r.content[:4000].decode("utf-8", errors="replace"))[:150]
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.name} {doc.kind} | {head}")
    return r.content[start:]
