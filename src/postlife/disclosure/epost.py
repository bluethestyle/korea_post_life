"""우체국보험 공시실(epostlife.go.kr)에서 상품 목록과 기초서류를 받는다.

공시실 화면이 쓰는 요청을 그대로 따른다 (2026-11-18 확인).
- 상품 목록:   POST /ASISDM000TR01.do    {"INSU_NTSL_YN": "Y"|"N"}
- 서류 목록:   POST /CMDMDM0000R02.do    srchGubun=1, insuGdsCd, insuJoinYmd
- 서류 내려받기: POST /pdfviewer.do        fileName, localFilePath
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BASE = "https://www.epostlife.go.kr"
LIST_PAGE = BASE + "/ASISDM00AT.do"
DOC_KINDS = {"01": "사업방법서", "03": "약관", "04": "상품요약서"}
AJAX = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": LIST_PAGE,
}


@dataclass(frozen=True)
class Product:
    code: str
    name: str
    start: str      # 판매 시작일 YYYY-MM-DD
    end: str | None  # 판매 종료일. 판매 중이면 None


@dataclass(frozen=True)
class Document:
    code: str
    kind: str       # 사업방법서 / 약관 / 상품요약서
    file_name: str
    path: str
    registered: str


def _date(ymd: str) -> str | None:
    ymd = (ymd or "").strip()
    if len(ymd) != 8 or ymd == "99991231":
        return None
    return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"


def parse_products(rows: list[dict[str, Any]]) -> list[Product]:
    """목록 응답에는 서류 종류마다 같은 상품이 여러 번 나온다. 상품코드로 하나만 남긴다."""
    seen: dict[str, Product] = {}
    for r in rows:
        code = str(r.get("GDS_CD", "")).strip()
        if code and code not in seen:
            seen[code] = Product(code, str(r.get("GDS_NM", "")).strip(),
                                 _date(str(r.get("GDS_BGNG_YMD", ""))) or "", _date(str(r.get("GDS_END_YMD", ""))))
    return sorted(seen.values(), key=lambda p: p.code)


def parse_documents(code: str, body: dict[str, Any]) -> list[Document]:
    out = []
    for d in body.get("docsList") or []:
        kind = DOC_KINDS.get(str(d.get("insuBascDocuCd")))
        path = d.get("strgFileNm")
        if kind and path and d.get("useYn", "Y") == "Y" and d.get("delYn", "N") == "N":
            out.append(Document(code, kind, str(d.get("orgnFileNm") or path.rsplit("/", 1)[-1]), str(path),
                                str(d.get("frstRegDt") or "")[:10]))
    return out


def list_products(session: Any, selling: bool = True) -> list[Product]:
    r = session.post(BASE + "/ASISDM000TR01.do", data=('{"INSU_NTSL_YN":"%s"}' % ("Y" if selling else "N")),
                     headers={**AJAX, "Content-Type": "application/json; charset=UTF-8"}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return parse_products(r.json())


def list_documents(session: Any, code: str, on: str) -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 판매가 끝난 상품은 판매 중이던 날짜를 넣는다."""
    r = session.post(BASE + "/CMDMDM0000R02.do",
                     data={"srchGubun": "1", "insuGdsCd": code, "insuJoinYmd": on.replace("-", "")},
                     headers={**AJAX, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return parse_documents(code, r.json())


def download(session: Any, doc: Document) -> bytes:
    form = {**AJAX, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    r = session.post(BASE + "/pdfviewer.do", data={"fileName": doc.path.rsplit("/", 1)[-1], "localFilePath": doc.path},
                     headers=form, timeout=180)
    r.raise_for_status()
    if r.content[:5] != b"%PDF-":
        head = r.content[:200].decode("utf-8", errors="replace").replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}): {doc.path} | {head}")
    return r.content
