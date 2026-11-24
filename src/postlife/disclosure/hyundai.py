"""현대해상 공시실(hi.co.kr)의 '보험상품공시'에서 상품 목록과 기초서류를 받는다.

공시 화면(메뉴 100932, 화면 bin/PA/03/HHPA03021M)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
화면의 요청은 모두 공통 함수 doRequest(전문번호, 요청값)를 거쳐 POST /ajax.xhi 로 간다. 본문은 JSON이고
{"header": {"gId", "tranId": 전문번호, "channelId": "HI-HOME", "clientIp": "127.0.0.1", "menuId", "loginId": null},
"request": 요청값} 꼴이다. 응답은 {"data": {...}, "messages": [...], "responseStatus": {"exception", "exceptionOccurred"}}.
- 상품 목록:   HHCA0310M38S  {}  → data.slYProdList(판매 중), data.slNProdList(판매 중지). 전 상품·전 판매기간이
               한 번에 온다 (2026-11-19: 2,390행 + 4,583행, 약 6MB). 화면은 처음 열 때 이 요청 한 번으로 분류 나무를 만든다
- 상품명 검색: HHCA0310M38S  {"searchData": 검색어, "searchDate": ""|YYYYMMDD, "searchType": "0"|"1", "searchKeyword": 1}
               searchType "1"은 가입일+상품명 검색이다. 응답 꼴은 상품 목록과 같다
- 서류 정보:   HHCA0310M26S  {"apnflId": 첨부 ID}  → data.savPath, data.savFileNm, data.flExts, data.originalFileNm
               목록의 각 행에 약관(clauApnflId), 사업방법서(userMthdApnflId), 상품요약서(prodSmryApnflId),
               상품설명서(prodNoteApnflId)의 첨부 ID가 들어 있다
- 내려받기:    POST /FileActionServlet/preview/0<savPath>/<encodeURIComponent(savFileNm)>.<flExts>  (본문 없음)
               화면 공통 함수 getRestDownloadUrl 과 같은 주소다. 파일 이름의 +는 %2B로 바꾼다

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키 없는 새 세션의 첫 요청으로 목록, 서류 정보, 파일이 각각 왔다
(X-Requested-With와 Referer는 화면과 같게 붙여 보냈고, 빼고 보내 보지는 않았다). 접속은 http.session()으로 한다.
curl 기본 설정은 TLS 연결 단계에서 끊겼다.
실패해도 상태 코드는 200이다. 없는 첨부 ID는 값이 모두 null인 data가, 없는 파일은 경고창 스크립트(text/html)가 온다.
상품코드는 응답에 없다(insCd는 모든 행이 null). repInsCd는 화면이 '연관상품' 조회에 쓰는 대표코드로,
같은 상품의 판매채널판(예: 퍼펙트플러스와 하이콜퍼펙트)이 같은 값을 쓴다. 상품을 하나로 가리는 코드가 아니다.
그래도 짧고 개정을 넘어 대체로 같아서 공시상품코드 자리에는 이 값을 쓰고, 행은 공시상품명(개정 표시를 뗀 상품명)으로 고른다
(2026-11-24 결정, postlife.disclosure.sources).
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

BASE = "https://www.hi.co.kr"
AJAX_URL = BASE + "/ajax.xhi"
LIST_PAGE = BASE + "/serviceAction.do"          # 화면은 view=bin/PA/03/HHPA03021M 을 POST로 보내 연다
MENU_ID = "100932"
CHANNEL = "HI-HOME"
TRAN_LIST = "HHCA0310M38S"
TRAN_FILE = "HHCA0310M26S"
DOWNLOAD = BASE + "/FileActionServlet/preview/0"
# 목록 행의 첨부 ID 칸 → 서류 종류. 화면의 표 칸 순서(약관, 사업방법서, 상품요약서, 상품설명서)와 같다
DOC_KINDS = {"clauApnflId": "약관", "userMthdApnflId": "사업방법서", "prodSmryApnflId": "상품요약서",
             "prodNoteApnflId": "상품설명서"}
# prodCatCd. 장기보험은 "03" + 보험유형 두 자리다 (화면의 분류 단추 값)
CATEGORIES = {
    "0100": "일반보험", "0200": "자동차보험", "0400": "퇴직보험", "0500": "퇴직연금",
    "0301": "장기보험/재물성", "0302": "장기보험/상해성", "0303": "장기보험/어린이", "0304": "장기보험/의료",
    "0305": "장기보험/질병성", "0306": "장기보험/저축성", "0307": "장기보험/연금", "0308": "장기보험/종합성",
    "0309": "장기보험/제도성특약",
}
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "Referer": LIST_PAGE,
}


@dataclass(frozen=True)
class Product:
    """목록의 한 행: 상품 × 판매기간. 개정이나 판매기간이 바뀔 때마다 행이 새로 생기고 첨부 ID도 새로 붙는다.

    한 상품의 종(1종, 2종 …)이 행을 따로 쓰기도 하고(서류도 따로), 여러 종을 한 행에 적기도 한다.
    """
    name: str
    start: str                  # 판매 개시일 YYYY-MM-DD
    end: str | None             # 판매 중지일. 판매 중 목록 행은 대개 None이다
    selling: bool               # 판매 중 목록(slYProdList)에서 왔는가. 후속 개정판이 나왔는데 이 목록에 남은 행도 있다
    category: str = ""          # prodCatCd: 0302 …
    rep_code: str = ""          # repInsCd (연관상품 대표코드, 상품코드가 아니다)
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)   # 서류 종류 → 첨부 ID

    @property
    def category_name(self) -> str:
        return CATEGORIES.get(self.category, "")


@dataclass(frozen=True)
class Document:
    apnfl_id: str
    kind: str                   # 약관 / 사업방법서 / 상품요약서 / 상품설명서
    name: str                   # 상품명
    start: str
    end: str | None


@dataclass(frozen=True)
class FileInfo:
    """서류 정보(HHCA0310M26S) 응답. 내려받기 주소를 만든다."""
    apnfl_id: str
    save_path: str              # /data/202611
    save_name: str              # 20261102135115454 (확장자 없음)
    ext: str                    # pdf
    original_name: str = ""     # 올린 사람이 붙인 파일 이름. 상품명과 서류 종류가 들어 있다
    size: int | None = None     # fileSz (바이트)

    @property
    def url(self) -> str:
        # 화면: savPath + "/" + encodeURIComponent(savFileNm) + "." + flExts 를 /FileActionServlet/preview/0 뒤에 붙이고 +를 %2B로
        path = self.save_path if self.save_path.startswith("/") else "/" + self.save_path
        return (DOWNLOAD + path.rstrip("/") + "/" + quote(self.save_name, safe="-_.!~*'()") + "." + self.ext).replace("+", "%2B")


def _date(text: Any) -> str | None:
    """'20261021  ' → 2026-10-21. 시작일에 빈칸이 붙어 온다."""
    digits = re.sub(r"\D", "", str(text or ""))
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def _name(text: Any) -> str:
    """상품명 앞에 탭이 붙어 오는 행이 있다(내삶엔 세만기형 일부). 안쪽 빈칸은 그대로 둔다."""
    return str(text or "").strip()


def _data(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError(f"현대해상 응답이 JSON 객체가 아님: {type(body).__name__}")
    status = body.get("responseStatus") or {}
    if isinstance(status, list):
        status = status[0] if status else {}
    if status.get("exceptionOccurred") or status.get("exception"):
        exc = status.get("exception")
        raise ValueError(f"현대해상 응답 오류: {exc.get('message', exc) if isinstance(exc, dict) else exc}")
    for m in body.get("messages") or []:
        if isinstance(m, dict) and str(m.get("type", "")).lower() in ("error", "warn"):
            raise ValueError(f"현대해상 응답 오류 {m.get('code', '')}: {m.get('message', '')}")
    data = body.get("data")
    if isinstance(data, list):     # 화면 공통 함수(setResponseData)는 목록이면 첫 값을 쓴다
        data = data[0] if data else None
    if not isinstance(data, dict):
        raise ValueError(f"현대해상 응답에 data가 없음: {sorted(body)}")
    return data


def _rows(value: Any) -> list[dict[str, Any]]:
    """화면의 generateValidJson과 같다: 없으면 빈 목록, 객체 하나면 목록으로 싼다."""
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def _product(r: dict[str, Any], selling: bool) -> Product | None:
    name, start = _name(r.get("prodNm")), _date(r.get("slStDt"))
    if not name or not start:
        return None
    files = {kind: str(r[key]).strip() for key, kind in DOC_KINDS.items() if str(r.get(key) or "").strip()}
    return Product(name, start, _date(r.get("slEdDt")), selling, str(r.get("prodCatCd") or ""),
                   str(r.get("repInsCd") or "").strip(), files)


def parse_products(body: Any) -> list[Product]:
    """상품 목록·검색 응답. 판매 중 행 다음에 판매 중지 행. 판매 개시일이 없는 행은 버린다."""
    data = _data(body)
    if "slYProdList" not in data and "slNProdList" not in data:
        raise ValueError(f"현대해상 응답에 상품 목록이 없음: {sorted(data)}")
    out = []
    for key, selling in (("slYProdList", True), ("slNProdList", False)):
        out += [p for p in (_product(r, selling) for r in _rows(data.get(key))) if p]
    return out


def parse_file_info(body: Any) -> FileInfo:
    data = _data(body)
    missing = [k for k in ("savPath", "savFileNm", "flExts") if not str(data.get(k) or "").strip()]
    if missing:
        raise ValueError(f"현대해상 서류 정보에 {', '.join(missing)} 없음 (apnflId={data.get('apnflId')})")
    size = data.get("fileSz")
    return FileInfo(str(data.get("apnflId") or ""), str(data["savPath"]).strip(), str(data["savFileNm"]).strip(),
                    str(data["flExts"]).strip(), str(data.get("originalFileNm") or "").strip(),
                    int(size) if isinstance(size, (int, float)) else None)


def documents_of(product: Product, kinds: tuple[str, ...] | None = None) -> list[Document]:
    """목록 행에 든 첨부 ID를 서류로 푼다. 요청을 보내지 않는다."""
    return [Document(i, k, product.name, product.start, product.end)
            for k, i in product.files.items() if kinds is None or k in kinds]


def find(products: list[Product], keyword: str, on: str | None = None, selling: bool | None = True) -> list[Product]:
    """상품명에 keyword가 든 행. on(YYYY-MM-DD)을 주면 그날이 판매기간에 드는 행만. 개시일 순."""
    out = [p for p in products if keyword in p.name and (selling is None or p.selling == selling)
           and (on is None or (p.start <= on and (p.end is None or on <= p.end)))]
    return sorted(out, key=lambda p: (p.start, p.name))


# 상품명 앞의 배당 표시와 회사 이름, 이름 안의 개정 표시. 목록의 상품명은 개정마다 "(Hi2607)" → "(Hi2610)"처럼 바뀌고,
# 지난 개정의 상품명은 회사 이름 없이("무배당가나다라…") 적히거나 배당 표시가 "(무)"와 "무배당"으로 갈리기도 한다 (2026-11-19 목록)
_DIVIDEND = re.compile(r"^\s*(?:\(\s*무배당\s*\)|\(\s*무\s*\)|무배당)\s*")
_COMPANY = re.compile(r"^현대해상\s*")
_REVISION = re.compile(r"\(\s*Hi\s*\d{4}\s*\)")


def series_name(name: str) -> str:
    """개정을 넘어 바뀌지 않는 상품 이름. 배당 표시, 회사 이름, 개정 표시("(Hi2610)")를 떼고 빈칸을 하나로 줄인다.

    "무배당현대해상가나다라보험(세만기형)(Hi9999) 1종(가형), 2종(나형)"
    → "가나다라보험(세만기형) 1종(가형), 2종(나형)"(지어낸 이름). 종 구성("1종(가형), 2종(나형)")은 남긴다.
    대상 설정의 공시상품명(개정 표시를 뗀 목록 상품명)과 목록 행을 비교할 때 쓴다(postlife.disclosure.sources). 대표코드(repInsCd)가
    같은 행 가운데 종 구성과 판매채널 상품(하이콜)이 다른 행을 이 이름으로 가른다.
    """
    text = _COMPANY.sub("", _DIVIDEND.sub("", _name(name)))
    return re.sub(r"\s+", " ", _REVISION.sub(" ", text)).strip()


def same_series(name: str, series: str) -> bool:
    """목록 상품명이 이 이름(series_name)의 상품인가. 빈칸은 비교하지 않는다("1종(가형),2종"처럼 붙여 적은 행이 있다)."""
    return re.sub(r"\s+", "", series_name(name)) == re.sub(r"\s+", "", series_name(series))


def is_rep_code(code: str) -> bool:
    """대표코드(repInsCd. 예: 131A, 11F0)처럼 생긴 값인가. 영문과 숫자 3~5자다. 대상 설정의 공시상품코드는 이 값이어야 한다."""
    return re.fullmatch(r"[0-9A-Za-z]{3,5}", code.strip()) is not None


def keyword_of(series: str) -> str:
    """서버 검색에 보낼 상품명 일부. 첫 괄호나 빈칸 앞까지다("가나다라보험(세만기형) 1종…" → "가나다라보험").

    괄호 없는 이름("가나보험 1종(…)")은 목록 상품명에서 이름과 종 구성 사이에 개정 표시가 끼어 있어 빈칸에서도 자른다.
    """
    return re.split(r"[\s(]", series_name(series), maxsplit=1)[0]


def pick_period(products: list[Product], on: str) -> Product | None:
    """on(YYYY-MM-DD)이 판매기간에 드는 행. 여럿이면 개시일이 가장 늦은 행이다.

    같은 이름의 판매기간 행이 겹쳐 실리기도 한다(2025년 행들. 판매 중지 목록). 개시일까지 같은데 첨부 서류가 다르면
    어느 것인지 모르므로 ValueError.
    """
    rows = [p for p in products if p.start <= on and (p.end is None or on <= p.end)]
    if not rows:
        return None
    latest = max(p.start for p in rows)
    rows = [p for p in rows if p.start == latest]
    if len({tuple(sorted(p.files.items())) for p in rows}) > 1:
        raise ValueError(f"현대해상: {rows[0].name}의 {latest} 판매기간 행이 {len(rows)}개이고 서류가 서로 다름")
    return rows[0]


def _gid() -> str:
    # 화면: 무작위 12자 + 18자리 숫자. 서버가 값을 따지는지는 확인하지 않았다
    return f"{random.getrandbits(48):012x}{random.randrange(10 ** 18):018d}"


def _post(session: Any, tran_id: str, request: dict[str, Any], timeout: int = 60) -> Any:
    body = {"header": {"gId": _gid(), "tranId": tran_id, "channelId": CHANNEL, "clientIp": "127.0.0.1",
                       "menuId": MENU_ID, "loginId": None},
            "request": request}
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")   # 화면의 JSON.stringify와 같은 꼴
    r = session.post(AJAX_URL, data=data, headers=AJAX, timeout=timeout)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def list_products(session: Any) -> list[Product]:
    """전 상품·전 판매기간(판매 중, 판매 중지). 응답이 6MB쯤 되므로 한 번 받아 걸러 쓴다."""
    return parse_products(_post(session, TRAN_LIST, {}, timeout=300))


def search_products(session: Any, keyword: str, on: str | None = None) -> list[Product]:
    """상품명 검색. 판매 중·중지 모든 판매기간이 온다("간편한3.10.10"으로 판매 중 4행, 판매 중지 80행).

    on(YYYY-MM-DD)을 주면 화면의 '가입일+상품명' 검색(searchType "1")이 된다. 이 꼴은 화면 스크립트대로 만든 것이고
    실제로 보내 보지는 않았다.
    """
    request = {"searchData": keyword, "searchDate": (on or "").replace("-", ""), "searchType": "1" if on else "0",
               "searchKeyword": 1}
    return parse_products(_post(session, TRAN_LIST, request, timeout=300))


def file_info(session: Any, doc: Document | str) -> FileInfo:
    apnfl_id = doc.apnfl_id if isinstance(doc, Document) else str(doc)
    return parse_file_info(_post(session, TRAN_FILE, {"apnflId": apnfl_id}))


def fetch(session: Any, info: FileInfo) -> bytes:
    r = session.post(info.url, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{info.original_name or info.save_name} | {head}")
    return r.content[start:]


def download(session: Any, doc: Document) -> bytes:
    """요청 두 번(서류 정보, 내려받기)."""
    return fetch(session, file_info(session, doc))
