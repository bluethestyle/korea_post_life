"""메리츠화재 공시실(meritzfire.com)의 '상품목록'에서 상품 목록과 기초서류를 받는다.

공시 화면(/disclosure/product-announcement/product-list.do, 화면 스크립트 default/app/biz/cu/ua/pdpban/salPdLst.js)이
쓰는 요청을 그대로 따른다 (2026-11-19 확인). 화면은 탭 넷으로 나뉜다: 판매상품("/"), 판매상품 검색("/01"),
판매중지 상품("/02"), 판매중지 상품 검색("/03"). notfYn이 판매상품 탭은 "Y", 판매중지 탭은 "N"이다.

조회는 모두 POST /json.smart?v=<시각> 한 주소로 간다(공통 호출 default/app/comm/http.js). 본문은 JSON이고
{"header": {..., "rcvmsgSrvId": 서비스ID, "encryDivCd": "0"}, "body": 조회 조건} 꼴이다. 응답은
{"header": {"prcesResultDivCd": "0"이면 성공}, "msg": {...}, "body": {...}} 꼴이다. 서비스ID 앞부분은
f.cg.he.cu.ua.o.bc.PbanBc. 이다.
- 분류와 상품명:   retrievePdList            {"notfYn", "srtSq": 분류 순번}
                   → body.pdList(분류 16개: 자동차보험 … 제도성특약), body.pdDtlList(그 분류의 상품명과 상품코드 nwPdCd)
- 상품명별 서류:   retrieveSalPdListForCdNm  {"notfYn", "nwPdCd": 상품코드}             → body.salPdList
- 분류별 서류:     retrieveSalPdList         {"cmPdDivCd": 분류 코드, "notfYn", "bcType": "SALPD_LST"} → body.salPdList
- 상품명 검색:     retrieveSalPdSchList      {"notfYn", "keyWord": 검색어}            → body.salPdList
                   ("보험"으로 판매상품 탭 2,241행, 2.2MB. 판매 중인 상품의 지난 판매기간도 함께 온다)
- 서류 내려받기:   POST /hp/fileDownload.do  (폼) path, id, orgFileName, check=Y  → {"resultMsg": ""}
                   GET  /hp/fileDownload.do?path=…&id=…&orgFileName=…&check=N  → PDF (application/octet-stream)
                   (화면의 fileUtil.download와 같은 두 단계)

로그인, 본인 인증, 요청 암호화, 토큰 헤더는 없다(header.encryDivCd "0"). 조회는 쿠키 없는 첫 요청으로도 응답이 온다.
다만 응답의 칸마다 "<칸>#[E]" 이름으로 서버가 암호화한 값이 함께 오고, 내려받기의 path와 id에는 이 값(file1#[E] 등)을
넣는다. 같은 칸의 암호값이 세션마다 달랐고, 다른 세션에서 받은 값을 쿠키 없는 새 세션으로 보냈더니 웹 방화벽 차단
화면(상태 200, text/html)이 왔다. 그래서 목록 조회와 내려받기는 반드시 같은 세션으로 한다.
상품코드(nwPdCd, 예: 6AFLT)는 상품명 목록에만 있고 서류 목록 행과 파일 경로(/cu/ctl/202611…U.pdf)에는 없다.
상품명은 개정 연월을 붙여 바뀐다(…2607 → …2610). 지난 개정판은 판매중지 탭에 있다.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, replace
from typing import Any

BASE = "https://www.meritzfire.com"
LIST_PAGE = BASE + "/disclosure/product-announcement/product-list.do"
SERVICE = BASE + "/json.smart"
DOWNLOAD = BASE + "/hp/fileDownload.do"
SRV = "f.cg.he.cu.ua.o.bc.PbanBc."
# 화면 pdfDown의 fileCnt와 내려받기 이름 꼬리. file4(상품설명서)는 화면에 있지만 응답에 온 적은 없다.
DOC_KINDS = {"file1": "약관", "file2": "사업방법서", "file3": "상품요약서", "file4": "상품설명서"}
_SUFFIX = {"file1": "약관.pdf", "file2": "사업방법서.pdf", "file3": "요약서.pdf", "file4": "상품설명서.pdf"}
# 탭별 화면 경로(header.lowrnkScreenId). 응답에는 영향이 없어 보이지만 화면과 같게 보낸다.
_VIEW = {(True, False): "/", (True, True): "/01", (False, False): "/02", (False, True): "/03"}
# http.js가 오류로 다루는 msg.standCd (사이트 통제, 중복 로그인, 권한 없음 등). 실제 응답으로 받아 본 적은 없다.
_ERROR_CODES = ("FNGFW100062", "FNGFW100048", "FCGCMH00004", "FCGCMH00005", "FCGCMH00006")
# 건강 보장 비교에 쓰는 분류. 종합 건강보험과 간편 건강보험이 '상해보험' 분류에 들어 있다(화면 분류일 뿐이다).
HEALTH = ("통합보험", "질병보험", "어린이보험", "암보험", "상해보험")
JSON_HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Referer": LIST_PAGE,
}
FORM_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": LIST_PAGE,
}


@dataclass(frozen=True)
class Category:
    """화면 왼쪽의 상품 분류. seq는 retrievePdList의 srtSq다."""
    seq: str
    name: str


@dataclass(frozen=True)
class Product:
    """상품명 목록(pdDtlList)의 한 행. 판매기간과 서류는 없다."""
    code: str                 # nwPdCd. 예: 6AFLT (옛 상품과 자동차보험은 숫자 다섯 자리: 71000)
    name: str
    category: str = ""        # 분류 이름(cdNm): 통합보험, 상해보험 …
    category_code: str = ""   # 분류 코드(cmCommCd). retrieveSalPdList의 cmPdDivCd로 쓴다
    selling: bool = True      # 판매상품 탭에서 왔는가


@dataclass(frozen=True)
class Period:
    """서류 목록(salPdList)의 한 행. 상품명 × 판매기간 한 건이고 서류 경로가 들어 있다."""
    seq: str                        # ntbdDtlSeq (게시글 번호)
    name: str
    start: str                      # 판매 개시일 YYYY-MM-DD (putupStDdTm)
    end: str | None = None          # 판매 종료일 (putupEdDdTm). 열린 기간이면 화면에 "-"로 오고 여기서는 None
    posted: str | None = None       # 게시일 (bgnDt). 개시일보다 늦은 날도 있다
    selling: bool = True            # 어느 탭에서 왔는가. 판매상품 탭에도 닫힌 지난 판매기간이 섞여 온다
    code: str = ""                  # 상품코드. 응답에 없어 list_documents가 넣어 준다
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)    # 서류 종류 → 경로
    tokens: dict[str, str] = field(default_factory=dict, compare=False, hash=False)   # 서류 종류 → 암호값(이 세션 한정)

    @property
    def open(self) -> bool:
        return self.end is None

    def documents(self) -> list[Document]:
        return [Document(self.seq, self.name, kind, path, self.tokens.get(kind, ""), self.start, self.end, self.code)
                for kind, path in self.files.items()]


@dataclass(frozen=True)
class Document:
    seq: str
    name: str
    kind: str          # 약관 / 사업방법서 / 상품요약서
    path: str          # 서버 안 경로(평문). 내려받기에는 쓰지 않는다
    token: str = field(default="", repr=False)   # 내려받기 path, id에 넣는 암호값. 받은 세션에서만 쓸 수 있다
    start: str = ""
    end: str | None = None
    code: str = ""

    @property
    def file_name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def download_name(self) -> str:
        """화면이 orgFileName으로 보내는 이름: 상품명 + "요약서.pdf" 등."""
        key = next(k for k, v in DOC_KINDS.items() if v == self.kind)
        return self.name + _SUFFIX[key]


def _date(text: Any) -> str | None:
    """20261031 → 2026-10-31. "-"나 빈칸은 None."""
    s = str(text or "").strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if len(s) == 8 and s.isdigit() else None


def _body(resp: Any) -> dict[str, Any]:
    """응답 봉투를 벗긴다. 화면 스크립트처럼 prcesResultDivCd가 "0"이 아니면 msg.standMsg를 오류로 알린다."""
    if not isinstance(resp, dict):
        raise ValueError(f"메리츠화재 응답이 JSON 객체가 아님: {type(resp).__name__}")
    header, msg = resp.get("header"), resp.get("msg") or {}
    if not isinstance(header, dict):
        raise ValueError(f"메리츠화재 응답에 header가 없음: {sorted(resp)}")
    if str(header.get("prcesResultDivCd")) != "0" or msg.get("standCd") in _ERROR_CODES:
        raise ValueError(f"메리츠화재 응답 오류 {msg.get('standCd', '')}: {msg.get('standMsg', '')} "
                         f"(prcesResultDivCd={header.get('prcesResultDivCd')!r})")
    body = resp.get("body")
    if not isinstance(body, dict):
        raise ValueError("메리츠화재 응답에 body가 없음")
    return body


def _list(body: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = body.get(key)
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError(f"메리츠화재 응답의 {key}가 목록이 아님: {type(rows).__name__}")
    return rows


def parse_categories(resp: Any) -> list[Category]:
    return [Category(str(r["srtSq"]), str(r.get("cdNm") or "").strip())
            for r in _list(_body(resp), "pdList") if r.get("srtSq") is not None]


def parse_products(resp: Any, selling: bool = True, seq: str | None = None) -> list[Product]:
    """상품명 목록. seq를 주면 화면처럼 그 분류(srtSq)의 행만 남긴다."""
    out = []
    for r in _list(_body(resp), "pdDtlList"):
        if seq is not None and str(r.get("srtSq")) != str(seq):
            continue
        code, name = str(r.get("nwPdCd") or "").strip(), str(r.get("ttlNm") or "").strip()
        if code and name:
            out.append(Product(code, name, str(r.get("cdNm") or "").strip(), str(r.get("cmCommCd") or "").strip(), selling))
    return out


def parse_periods(resp: Any, selling: bool = True, code: str = "") -> list[Period]:
    """서류 목록(검색, 상품명별, 분류별 모두 같은 꼴). 개시일이 없는 행은 버린다. 서류가 없는 칸은 빈 값으로 온다."""
    out = []
    for r in _list(_body(resp), "salPdList"):
        start = _date(r.get("putupStDdTm"))
        if not start or r.get("ntbdDtlSeq") is None:
            continue
        files = {kind: str(r[key]).strip() for key, kind in DOC_KINDS.items() if str(r.get(key) or "").strip()}
        tokens = {kind: str(r.get(key + "#[E]") or "") for key, kind in DOC_KINDS.items() if kind in files}
        out.append(Period(str(r["ntbdDtlSeq"]), str(r.get("ttlNm") or "").strip(), start, _date(r.get("putupEdDdTm")),
                          _date(r.get("bgnDt")), selling, code, files, tokens))
    return out


def pick_period(periods: list[Period], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: (p.start, p.seq)) if periods else None


def _envelope(service: str, body: dict[str, Any], view: str, now: float | None = None) -> dict[str, Any]:
    """화면 http.js의 inputFilter와 같은 요청 봉투."""
    t = time.time() if now is None else now
    stamp = time.strftime("%Y%m%d%H%M%S", time.localtime(t)) + f"{int(t * 1000) % 1000:03d}"
    header = {key: "" for key in (
        "globId", "resultRcvmsgSrvId", "esbIntfId", "exsIntfId", "ipv6Addr1", "ipv6Addr2", "teleMsgMacAdr",
        "envirInfoDivCd", "firstTranssLcatgBizafairCd", "transsLcatgBizafairCd", "prcesResultDivCd",
        "teleMsgRespnsDttm", "clienTrespnsDttm", "handcapLcatgBizafairCd", "teleMsgVerDivCd", "belongGrpCd",
        "empNo", "empId", "dptCd", "hgrkDptCd", "nxupDptCd", "resveLet")}
    header.update({"encryDivCd": "0", "rcvmsgSrvId": SRV + service, "reqRespnsDivCd": "Q", "syncDivCd": "S",
                   "teleMsgReqDttm": stamp, "langDivCd": "KR", "transGrpCd": "F",
                   "screenId": "/disclosure/product-announcement/product-list.do", "lowrnkScreenId": view})
    return {"header": header, "body": body}


def _post(session: Any, service: str, body: dict[str, Any], view: str = "/") -> Any:
    data = json.dumps(_envelope(service, body, view), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    r = session.post(f"{SERVICE}?v={int(time.time() * 1000)}", data=data, headers=JSON_HEADERS, timeout=120)
    r.raise_for_status()
    r.encoding = "utf-8"
    try:
        return r.json()
    except ValueError as e:   # 방화벽 차단 화면과 오류 화면은 상태 200, text/html로 온다
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"메리츠화재 응답이 JSON이 아님({r.headers.get('Content-Type', '')}): {head}") from e


def _flag(selling: bool) -> str:
    return "Y" if selling else "N"


def list_products(session: Any, selling: bool = True, categories: tuple[str, ...] | None = HEALTH) -> list[Product]:
    """분류마다 상품명과 상품코드를 조회한다(분류당 요청 한 번, 수 KB). categories는 분류 이름, None이면 전부.

    첫 요청은 화면처럼 srtSq "1"로 보내 분류 목록을 얻는다. 여러 분류에 나오는 상품코드는 처음 것만 남긴다.
    """
    first = _post(session, "retrievePdList", {"notfYn": _flag(selling), "srtSq": "1"}, _VIEW[(selling, False)])
    seen: dict[str, Product] = {}
    for cat in parse_categories(first):
        if categories is not None and cat.name not in categories:
            continue
        resp = first if cat.seq == "1" else _post(session, "retrievePdList", {"notfYn": _flag(selling), "srtSq": cat.seq},
                                                  _VIEW[(selling, False)])
        for p in parse_products(resp, selling, cat.seq):
            seen.setdefault(p.code, p)
    return list(seen.values())


def search_products(session: Any, keyword: str, selling: bool = True) -> list[Period]:
    """상품명에 keyword가 든 판매기간 전부(그 탭의 지난 판매기간 포함)와 서류. 상품코드는 비어 있다."""
    return parse_periods(_post(session, "retrieveSalPdSchList", {"notfYn": _flag(selling), "keyWord": keyword},
                               _VIEW[(selling, True)]), selling)


def list_periods(session: Any, code: str, selling: bool = True) -> list[Period]:
    """상품코드(nwPdCd)의 판매기간과 서류. selling은 상품이 들어 있는 탭과 맞춰 준다."""
    return parse_periods(_post(session, "retrieveSalPdListForCdNm", {"notfYn": _flag(selling), "nwPdCd": code},
                               _VIEW[(selling, False)]), selling, code)


def list_documents(session: Any, code: str, on: str | None = None, selling: bool = True) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 요청 한 번.

    돌려받은 Document의 token은 이 session에서만 쓸 수 있다. 같은 session으로 download를 부른다.
    """
    period = pick_period(list_periods(session, code, selling), on)
    return period.documents() if period else []


def documents_of(period: Period, code: str = "") -> list[Document]:
    """검색 결과의 판매기간에서 서류를 꺼낸다. 상품코드를 알면 넣어 준다."""
    return (replace(period, code=code) if code else period).documents()


def _uri_param(v: str) -> str:
    """화면 fileUtil.makeURIParam: 몇몇 글자를 미리 %xx로 바꾸고 "/"는 전각 "／"로 바꾼다."""
    for a, b in (("@", "%40"), (":", "%3A"), ("$", "%24"), (",", "%2C"), ("(", "%28"), (")", "%29"), ("/", "／")):
        v = v.replace(a, b)
    return v


def download(session: Any, doc: Document) -> bytes:
    """화면과 같은 두 단계로 받는다. 목록을 받은 session과 같은 session이어야 한다."""
    if not doc.token:
        raise ValueError(f"내려받기 암호값이 없음(목록 응답의 '#[E]' 칸): {doc.name} {doc.kind}")
    form = {"path": doc.token, "id": doc.token, "orgFileName": _uri_param(doc.download_name), "check": "Y"}
    r = session.post(DOWNLOAD, data=form, headers=FORM_HEADERS, timeout=60)
    r.raise_for_status()
    try:
        check = r.json()
    except ValueError as e:   # 다른 세션의 암호값을 보냈을 때 방화벽 차단 화면(상태 200, text/html)이 왔다
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"내려받기 확인 응답이 JSON이 아님({r.headers.get('Content-Type', '')}): {doc.name} {doc.kind} | {head}") from e
    if not isinstance(check, dict) or check.get("resultMsg") != "":
        raise ValueError(f"내려받기 확인 거절: {doc.name} {doc.kind} | {check}")
    r = session.get(DOWNLOAD, params={**form, "check": "N"}, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.name} {doc.kind} | {head}")
    return r.content[start:]
