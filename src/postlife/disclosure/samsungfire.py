"""삼성화재 상품공시(samsungfire.com)에서 상품 목록과 기초서류를 받는다.

공시 화면(/vh/page/VH.HPIF0103.do)이 쓰는 요청을 그대로 따른다 (2026-11-18 확인).
- 상품 목록:   POST /vh/data/VH.HDIF0103.do   header={"tranId":"VH.HDIF0103"}            (전 상품·전 판매기간, 약 3.9MB)
- 상품명 검색: POST /vh/data/VH.HDIF0114.do   header={...}&body={"kwd":검색어,"cate":"","from":"","to":""}
- 서류 목록:   따로 없다. 목록의 각 행(상품코드 × 판매기간)에 prdfilename1~4로 서류 경로가 들어 있다.
- 서류 내려받기: GET  /publication/pdf/<상품코드>_<jongGb>_<판매개시일>_file<N>.pdf  (로그인·세션 불필요)

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 응답은 {"responseMessage": {"header": ..., "body": {"result": "S",
"data": {"list": [...]}}}} 꼴이다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

BASE = "https://www.samsungfire.com"
LIST_PAGE = BASE + "/vh/page/VH.HPIF0103.do"
TRAN_LIST = "VH.HDIF0103"
TRAN_SEARCH = "VH.HDIF0114"
# prdfilenameN 의 N. 화면 스크립트(IH_IF_Terms.js)의 단추 연결과 같다.
DOC_KINDS = {1: "약관", 2: "사업방법서", 3: "상품요약서", 4: "상품설명서"}
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Referer": LIST_PAGE,
    # 화면이 붙여 보내는 값. 없어도 응답이 오는 것을 확인했지만 화면과 같게 둔다.
    "pagenumber": "J_030_020_000",
    "ssf-chnl": "PC",
    "ssf-device": "PC",
}
OPEN_END = "99991231"
_FILE = re.compile(r"/([^/_]+)_([^/_]+)_(\d{8})_file(\d)\.pdf$", re.IGNORECASE)


@dataclass(frozen=True)
class Product:
    """상품코드 × 종 구분 × 판매기간 한 건. 같은 상품코드가 판매기간마다 여러 번 나온다."""
    code: str
    name: str
    start: str               # 판매 개시일 YYYY-MM-DD
    end: str | None          # 판매 종료일. 판매 중이면 None
    jong: str = "0"          # jongGb. 요즘 상품은 종마다 상품코드가 달라 늘 "0", 옛 상품은 한 코드에 1·2…가 붙는다
    category: str = ""       # 자동차 / 장기 / 일반보험 / 퇴직연금 / 퇴직보험
    group: str = ""          # 건강, 상해, 통합형 … (장기·대면 외에는 비어 있기도 하다)
    channel: str = ""        # 대면, TM/홈쇼핑, 인터넷, 방카슈랑스, 제도성 특약 …
    selling: bool = True     # 공시 화면의 '판매상품' 탭 기준 현재 판매 여부
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 서류 종류 → 경로


@dataclass(frozen=True)
class Document:
    code: str
    kind: str       # 약관 / 사업방법서 / 상품요약서 / 상품설명서
    file_name: str
    path: str
    registered: str  # 해당 판매기간의 개시일 YYYY-MM-DD (서류 등록일은 응답에 없다)


def _date(ymd: str) -> str | None:
    ymd = (ymd or "").strip()
    if len(ymd) != 8 or not ymd.isdigit() or ymd == OPEN_END:
        return None
    return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"


def _rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    """응답 봉투를 벗겨 행 목록을 돌려준다. 서버가 오류를 실어 보내면 그대로 알린다."""
    msg = body.get("responseMessage") or {}
    err = (msg.get("header") or {}).get("errorMsg")
    if err:
        raise ValueError(f"삼성화재 응답 오류 {err.get('errorCode')}: {err.get('displayMsg')}")
    inner = msg.get("body") or {}
    if inner.get("result") != "S":
        raise ValueError(f"삼성화재 응답이 성공이 아님: result={inner.get('result')!r}")
    return list((inner.get("data") or {}).get("list") or [])


def _files(row: dict[str, Any]) -> dict[str, str]:
    out = {}
    for n, kind in DOC_KINDS.items():
        path = str(row.get(f"prdfilename{n}") or "").strip()
        if path:
            out[kind] = path
    return out


def parse_products(body: dict[str, Any]) -> list[Product]:
    """목록(HDIF0103)·검색(HDIF0114) 응답을 판매기간별 상품으로 바꾼다.

    검색 응답에는 상품코드·종 구분이 없어 서류 경로에서 읽어 낸다. 같은 (상품코드, 종 구분, 판매개시일) 행이
    겹쳐 오면 하나만 남기되 판매 중인 행을 앞세운다.
    """
    seen: dict[tuple[str, str, str], Product] = {}
    for r in _rows(body):
        files = _files(r)
        code = str(r.get("prdCode") or "").strip()
        jong = str(r.get("jongGb") or "").strip()
        if not code:
            m = next((m for m in map(_FILE.search, files.values()) if m), None)
            code, jong = (m.group(1), m.group(2)) if m else ("", "")
        start = _date(str(r.get("saleStDt") or ""))
        if not code or not start:
            continue
        end_raw = str(r.get("saleEnDt") or "").strip()
        # 화면 규칙: displayGb 1은 '판매상품' 탭 고정(판매 중 상품의 지난 판매기간 포함), 2는 '판매중지' 탭 고정,
        # 그 밖에는 종료일이 99991231인지로 가른다. 현재 판매 중인 기간은 종료일이 열려 있고 2가 아닌 행이다.
        selling = end_raw == OPEN_END and str(r.get("displayGb") or "") != "2"
        key = (code, jong or "0", start)
        if key not in seen or (selling and not seen[key].selling):
            seen[key] = Product(
                code, str(r.get("prdName") or "").strip(), start, _date(end_raw), jong or "0",
                str(r.get("prdGun") or "").strip(), str(r.get("prdGb") or "").strip(),
                str(r.get("saleChannel") or "").strip(), selling, files)
    return sorted(seen.values(), key=lambda p: (p.code, p.jong, p.start))


def parse_documents(code: str, products: list[Product], on: str | None = None,
                    jong: str = "0") -> list[Document]:
    """상품코드의 판매기간 가운데 기준일(on, YYYY-MM-DD)이 속한 기간의 서류. on이 없으면 가장 최근 기간."""
    periods = [p for p in products if p.code == code and p.jong == jong]
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    if not periods:
        return []
    p = max(periods, key=lambda x: x.start)
    return [Document(code, kind, path.rsplit("/", 1)[-1], path, p.start) for kind, path in p.files.items()]


def _form(tran: str, body: dict[str, Any] | None = None) -> bytes:
    """화면과 같은 본문: header=<JSON>&body=<JSON> (encodeURIComponent 방식으로 인코딩)."""
    dump = lambda o: quote(json.dumps(o, ensure_ascii=False, separators=(",", ":")), safe="")  # noqa: E731
    text = "header=" + dump({"tranId": tran})
    if body:
        text += "&body=" + dump(body)
    return text.encode("ascii")


def _post(session: Any, tran: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    r = session.post(f"{BASE}/vh/data/{tran}.do", data=_form(tran, body), headers=AJAX, timeout=120)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def list_products(session: Any, selling: bool = True) -> list[Product]:
    """전 상품 목록. selling=True면 현재 판매 중인 판매기간만, False면 그 밖(판매 종료·지난 기간)만 돌려준다."""
    return [p for p in parse_products(_post(session, TRAN_LIST)) if p.selling == selling]


def search_products(session: Any, keyword: str) -> list[Product]:
    """상품명에 keyword가 들어간 판매기간 전부(판매 중·종료 모두). 응답이 작아 한두 상품만 볼 때 쓴다.

    검색 응답에는 displayGb가 없어 selling은 종료일만으로 판단한 값이다.
    """
    return parse_products(_post(session, TRAN_SEARCH, {"kwd": keyword, "cate": "", "from": "", "to": ""}))


def list_documents(session: Any, code: str, on: str | None = None,
                   products: list[Product] | None = None, jong: str = "0") -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 이미 받은 목록이 있으면 products로 넘겨 재요청을 피한다."""
    if products is None:
        products = parse_products(_post(session, TRAN_LIST))
    return parse_documents(code, products, on, jong)


def download(session: Any, doc: Document) -> bytes:
    r = session.get(BASE + doc.path, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}): {doc.path} | {head}")
    return r.content[start:]
