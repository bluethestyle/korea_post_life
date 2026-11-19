"""DB손해보험 공시실(idbins.com)의 '상품목록 및 기초서류'에서 상품 목록과 기초서류를 받는다.

공시 화면(/FWMAIV1534.do 판매상품, /FWMAIV1535.do 판매중지 상품)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
목록 요청은 모두 POST이고 본문은 JSON(application/json)이다. 응답은 {"result": [...]} 꼴인데,
응답 머리의 Content-Type은 text/html이다. arc_pdc_sl_yn은 판매상품 탭이 "1", 판매중지 탭이 "0"이다.
- 상품명 목록:   POST /insuPcPbanFindProductStep2_AX.do  {"arc_knd_lgcg_nm": 상품군, "sl_chn_nm": 채널,
                 "arc_knd_mdcg_nm": 분류, "arc_pdc_sl_yn": "1"}            → [{"PDC_NM"}]
- 판매기간 목록: POST /insuPcPbanFindProductStep3_AX.do  {"pdc_nm": 상품명, "arc_pdc_sl_yn": "1"}
                 → [{"SQNO", "SL_STR_DT", "SL_FIN_DT"(닫힌 기간만)}]. 탭 값이 상품과 맞지 않으면 빈 목록이 온다
- 서류 목록:     POST /insuPcPbanFindProductStep4_AX.do  {"sqno": 판매기간 번호, "arc_pdc_sl_yn": "1"}
                 → 사업방법서(BIZ_MDDC_FINM), 상품요약서(CNSL_SMAR_FINM), 약관(INPL_FINM) 파일 이름. 탭 값과 무관하다
- 상품명 검색:   POST /insuPcPbanFindProductStep5_AX.do  {"searchCheck": "0", "keyword": 검색어, "beginDate": "", "endDate": ""}
                 → 판매 중·중지 모든 판매기간과 파일 이름이 한 번에 온다. 종료일은 없다 ("종합보험"으로 805행, 330KB)
- 서류 내려받기: GET  /cYakgwanDown.do?FilePath=InsProduct/<encodeURIComponent(파일 이름)>
                 파일이 없으면 상태 200, 본문 0바이트가 온다

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 새 세션의 첫 요청으로, X-Requested-With와 Referer 없이도 같은 응답이 왔다
(화면과 같게 붙여 보낸다). 상품코드는 응답에 따로 없고 서류 파일 이름에 들어 있다: 요약_30633(25)_20260701.pdf → 30633.
첫 화면의 상담 신청 스크립트와 다이렉트 가입 주소(searchPdcCd)가 같은 다섯 자리 값을 쓴다. 괄호 안 숫자의 뜻은 확인하지 않았다.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

BASE = "https://www.idbins.com"
LIST_PAGE = BASE + "/FWMAIV1534.do"
STEP_NAMES = "/insuPcPbanFindProductStep2_AX.do"
STEP_PERIODS = "/insuPcPbanFindProductStep3_AX.do"
STEP_DOCS = "/insuPcPbanFindProductStep4_AX.do"
STEP_SEARCH = "/insuPcPbanFindProductStep5_AX.do"
DOWNLOAD = BASE + "/cYakgwanDown.do?FilePath=InsProduct/"
# 화면 스크립트의 단추 연결과 같다. 검색 결과 표에는 상품설명서(PDC_EXPP_FINM) 칸도 있지만 응답에 그 값이 온 적은 없다.
DOC_KINDS = {"BIZ_MDDC_FINM": "사업방법서", "CNSL_SMAR_FINM": "상품요약서", "INPL_FINM": "약관"}
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json; charset=utf-8",
    "Referer": LIST_PAGE,
}
# 화면 1단계 '상품군' 나무 가운데 장기보험 부분 (상품군, 채널, 분류). 대면 채널 값은 "Off-Line"이고, 채널이 없는 상품군은 "99"다.
# 자동차·일반·퇴직 상품군도 화면에 있지만 건강 보장 비교와 무관해 넣지 않았다.
_KINDS = ("간병", "건강", "상해", "연금", "운전자", "재물", "저축")
LONG_TERM: tuple[tuple[str, str, str], ...] = (
    *(("장기보험", "Off-Line", k) for k in _KINDS + ("질병",)),
    *(("장기보험", "TM/CM", k) for k in _KINDS + ("질병",)),
    *(("장기보험", "방카슈랑스", k) for k in _KINDS + ("00",)),
    ("통합보험", "99", "컨버전스"),
    ("제도성 특별약관", "99", "제도성 특별약관"),
)
# 2019년 이후 파일: 요약_30633(25)_20260701.pdf. 옛 파일: 10513_20181001_사업_아파트종합보험(0).pdf (앞 숫자를 코드로 보지만 대조하지 않았다)
_CODE = re.compile(r"^(?:[^_\d]+_)?(\d+)(?:\((\d+)\))?_")


def code_of(file_name: str) -> tuple[str, str]:
    """서류 파일 이름에서 (상품코드, 괄호 안 숫자). 꼴이 맞지 않으면 ("", "")."""
    m = _CODE.match(file_name or "")
    return (m.group(1), m.group(2) or "") if m else ("", "")


@dataclass(frozen=True)
class Product:
    """상품명 목록(2단계)의 한 행. 이 단계에는 상품코드도 판매기간도 없다."""
    name: str
    group: str = ""          # 상품군: 장기보험, 통합보험 …
    channel: str = ""        # Off-Line(대면), TM/CM, 방카슈랑스. 채널이 없는 상품군은 "99"
    kind: str = ""           # 분류: 건강, 상해, 질병 … (화면 분류일 뿐이다. 종합 건강보험이 '상해'에 들어 있다)
    selling: bool = True     # 판매상품 탭에서 왔는가. 판매기간이 모두 닫혔는데 이 탭에 남아 있는 상품도 있다


@dataclass(frozen=True)
class Period:
    """판매기간 한 건. 판매기간 목록(3단계)과 검색(5단계)에서 온다. 개정마다 SQNO가 새로 붙는다."""
    sqno: str
    name: str
    start: str                      # 판매 개시일 YYYY-MM-DD
    end: str | None = None          # 판매 종료일. 열린 기간이거나 검색 응답이면 None
    selling: bool | None = None     # 검색 응답의 ARC_PDC_SL_YN. 상품 단위 값이라 지난 판매기간도 "1"로 온다
    group: str = ""                 # 검색 응답의 상품군(ARC_KND_LGCG_NM): 장기보험, 일반, 자동차보험 …
    files: dict[str, str] = field(default_factory=dict, compare=False, hash=False)  # 서류 종류 → 파일 이름 (검색 응답만)

    @property
    def code(self) -> str:
        return next((c for c in (code_of(f)[0] for f in self.files.values()) if c), "")


@dataclass(frozen=True)
class Document:
    sqno: str
    name: str
    kind: str         # 사업방법서 / 상품요약서 / 약관
    file_name: str    # 내려받기 요청에 그대로 넣는 이름
    start: str
    end: str | None

    @property
    def code(self) -> str:
        return code_of(self.file_name)[0]


def _date(text: Any) -> str | None:
    """20260701 또는 2026.07.01 → 2026-07-01."""
    digits = re.sub(r"\D", "", str(text or ""))
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def _name(text: Any) -> str:
    """응답의 상품명은 &가 &amp;로 온다. 화면은 HTML로 풀린 이름을 다시 보내고, &amp;를 그대로 보내면 빈 목록이 온다."""
    return html.unescape(str(text or "")).strip()


def _rows(body: Any) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        raise ValueError(f"DB손해보험 응답이 JSON 객체가 아님: {type(body).__name__}")
    err = body.get("errMsg")
    if err:   # 화면 스크립트(comnUtil.js callAjaxParams)가 처리하는 오류 꼴
        raise ValueError(f"DB손해보험 응답 오류 {err.get('rspnCd') if isinstance(err, dict) else ''}: "
                         f"{err.get('rspnMsgCtnt') if isinstance(err, dict) else err}")
    rows = body.get("result")
    if not isinstance(rows, list):
        raise ValueError(f"DB손해보험 응답에 result 목록이 없음: {sorted(body)}")
    return rows


def _files(row: dict[str, Any]) -> dict[str, str]:
    return {kind: str(row[key]).strip() for key, kind in DOC_KINDS.items() if str(row.get(key) or "").strip()}


def parse_products(body: Any, group: str = "", channel: str = "", kind: str = "", selling: bool = True) -> list[Product]:
    return [Product(n, group, channel, kind, selling) for n in (_name(r.get("PDC_NM")) for r in _rows(body)) if n]


def parse_periods(name: str, body: Any) -> list[Period]:
    """판매기간 목록(3단계). 화면처럼 개시일이 8자리가 아닌 행은 버린다. 개시일 순으로 돌려준다."""
    out = []
    for r in _rows(body):
        start = _date(r.get("SL_STR_DT")) if len(str(r.get("SL_STR_DT") or "")) == 8 else None
        if start and r.get("SQNO") is not None:
            out.append(Period(str(r["SQNO"]), name, start, _date(r.get("SL_FIN_DT"))))
    return sorted(out, key=lambda p: p.start)


def parse_search(body: Any) -> list[Period]:
    """검색(5단계) 응답. 판매 중·중지 상품의 모든 판매기간이 온다. 종료일은 없다."""
    out = []
    for r in _rows(body):
        start = _date(r.get("SALE_BEGIN_DAY"))
        if start and r.get("SQNO") is not None:
            out.append(Period(str(r["SQNO"]), _name(r.get("PDC_NM")), start, None, str(r.get("ARC_PDC_SL_YN")) == "1",
                              str(r.get("ARC_KND_LGCG_NM") or "").strip(), _files(r)))
    return out


def parse_documents(body: Any) -> list[Document]:
    """서류 목록(4단계). 판매기간 하나에 서류가 셋까지 온다. 상품요약서가 없는 판매기간도 있다."""
    out = []
    for r in _rows(body):
        start = _date(r.get("SL_STR_DT"))
        if r.get("SQNO") is None or not start:
            continue
        for kind, file_name in _files(r).items():
            out.append(Document(str(r["SQNO"]), _name(r.get("PDC_NM")), kind, file_name, start, _date(r.get("SL_FIN_DT"))))
    return out


def pick_period(periods: list[Period], on: str | None = None) -> Period | None:
    """on(YYYY-MM-DD)이 속한 판매기간. on이 없으면 개시일이 가장 늦은 판매기간."""
    if on:
        periods = [p for p in periods if p.start <= on and (p.end is None or on <= p.end)]
    return max(periods, key=lambda p: p.start) if periods else None


def _post(session: Any, path: str, body: dict[str, Any]) -> Any:
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")   # 화면의 JSON.stringify와 같은 꼴
    r = session.post(BASE + path, data=data, headers=AJAX, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def _flag(selling: bool) -> str:
    return "1" if selling else "0"


def list_products(session: Any, selling: bool = True,
                  categories: tuple[tuple[str, str, str], ...] = LONG_TERM) -> list[Product]:
    """상품군 나무를 한 칸씩 조회한다(기본은 장기보험 26칸, 요청마다 수 KB). 여러 칸에 나오는 이름은 처음 것만 남긴다."""
    seen: dict[str, Product] = {}
    for group, channel, kind in categories:
        body = _post(session, STEP_NAMES, {"arc_knd_lgcg_nm": group, "sl_chn_nm": channel, "arc_knd_mdcg_nm": kind,
                                           "arc_pdc_sl_yn": _flag(selling)})
        for p in parse_products(body, group, channel, kind, selling):
            seen.setdefault(p.name, p)
    return list(seen.values())


def search_products(session: Any, keyword: str) -> list[Period]:
    """상품명에 keyword가 든 모든 판매기간(판매 중·중지)과 서류 파일 이름. 응답이 클 수 있어 검색어를 좁혀 쓴다."""
    return parse_search(_post(session, STEP_SEARCH, {"searchCheck": "0", "keyword": keyword, "beginDate": "", "endDate": ""}))


def list_periods(session: Any, name: str, selling: bool = True) -> list[Period]:
    """상품명(목록에 나온 그대로, &amp;는 푼 것)의 판매기간. selling은 상품이 들어 있는 탭과 맞아야 한다."""
    return parse_periods(name, _post(session, STEP_PERIODS, {"pdc_nm": name, "arc_pdc_sl_yn": _flag(selling)}))


def documents_for(session: Any, sqno: str) -> list[Document]:
    """판매기간 번호(SQNO)의 서류. 검색 응답에 이미 파일 이름이 있으면 이 요청 없이 Period.files를 써도 된다."""
    return parse_documents(_post(session, STEP_DOCS, {"sqno": str(sqno), "arc_pdc_sl_yn": "1"}))


def list_documents(session: Any, name: str, on: str | None = None, selling: bool = True) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 요청 두 번(판매기간 목록, 서류 목록)."""
    period = pick_period(list_periods(session, name, selling), on)
    return documents_for(session, period.sqno) if period else []


def download(session: Any, doc: Document) -> bytes:
    # 화면은 encodeURIComponent로 이름을 싼다. 괄호는 그대로 두고 한글과 빈칸만 바꾼다
    url = DOWNLOAD + quote(doc.file_name, safe="-_.!~*'()")
    r = session.get(url, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    # 파일이 없어도 상태 코드는 200이고 본문이 비어 온다. 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): {doc.file_name} | {head}")
    return r.content[start:]
