"""흥국생명 공시실(heungkuklife.co.kr)의 '상품공시 > 판매상품, 판매중지상품'에서 상품 목록과 기초서류를 받는다.

공시 화면(/front/public/saleProduct.do?searchFlgSale=Y)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
- 목록 요청:     POST /front/public/saleProductAjax.do  (application/x-www-form-urlencoded, 공통 스크립트 /js/ajax.js)
                 searchFlgSale=Y|N, beforeYn("" 판매상품, "N" 판매중지상품), searchCdPublicPrtType1(I101 개인,
                 I102 단체, I103 방카슈랑스), searchCdPublicPrtType2(I201 연금 … 빈 값은 전체),
                 searchCdPublicPrtType3(상품명), searchText(검색어)
                 상품명과 검색어는 화면처럼 escape(encodeURIComponent(x))로 두 번 싸서 보낸다.
                 응답은 EUC-KR 글자 하나: "상품명 목록%||%null%||%서류 행 목록". 행은 %|%, 칸은 %,%로 가른다.
                 상품명을 주면 그 상품의 판매기간별 서류 행이 오고, 상품명이 없거나 맞지 않으면 서류 행 자리가 빈다.
                 검색어는 상품명 목록만 거른다(서류 행은 오지 않는다).
- 서류 행 칸:    판매 시작, 판매 종료(판매 중이면 빈칸), 상품코드, 행 번호, 약관 암호값, 약관 파일 이름,
                 사업방법서 암호값, 사업방법서 파일 이름, 상품요약서 암호값, 상품요약서 파일 이름
- 내려받기:      POST /servlet/DownLoadEnc.do  multipart/form-data. 화면은 폼(frmPage)을 FormData로 그대로 보내며
                 encValue에 서류 행의 암호값을 넣는다. 성공하면 Content-Disposition에 서버 파일 이름이 온다.
                 실패해도 상태 코드는 200이고 alert 스크립트(text/html)가 온다. 화면 스크립트는 파일 이름이
                 "DOWN_LIMIT"이면 '일일 다운로드 회수 초과'로 알린다(이 응답은 받아 보지 않았다).

로그인, 세션 쿠키, 토큰은 필요 없다. 쿠키 없는 새 세션의 첫 요청으로 목록과 서류를 받았고, 몇 분 전 다른 세션에서 받은
암호값으로도 내려받기가 됐다. 암호값은 서버가 만든 값이라 풀지 않고 그대로 보낸다. 같은 파일도 행마다 값이 다르며,
언제까지 유효한지는 확인하지 않았다.
상품코드 칸은 범위(P0001901~P0002201)와 덧붙임("<br>갱신형", " 태아 암보장")이 섞여 온다. 2026년 6월 상품코드 체계가
바뀌어 그 전 판매기간은 다른 코드(P2203000~P2203500, 옛 표기 22030~22035)로 적혀 있다.
화면은 판매 중인 판매기간에만 상품요약서 단추를 보이지만, 지난 판매기간의 암호값으로도 요약서를 받을 수 있었다.
판매 중인 판매기간에 상품요약서 파일 이름이 비어 있는 상품도 있다(다사랑통합보험V2의 2026-11-02 판매기간).
한 상품의 서류 행이 정확히 100행으로 온 적이 있다(다사랑통합보험V2). 서버가 100행에서 자르는지는 확인하지 않았다.
판매중지 화면의 2003년 이전 상품(beforeYn=Y, 약관만 있음)은 다루지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

BASE = "https://www.heungkuklife.co.kr"
LIST_PAGE = BASE + "/front/public/saleProduct.do?searchFlgSale=Y"
LIST_AJAX = BASE + "/front/public/saleProductAjax.do"
DOWNLOAD = BASE + "/servlet/DownLoadEnc.do"
ENCODING = "cp949"   # 응답 머리는 charset=EUC-KR. 그 상위 집합인 cp949로 푼다
# 화면 1단계 '구분선택'과 2단계 '보험유형선택'의 값
GROUPS = {"I101": "개인", "I102": "단체", "I103": "방카슈랑스"}
TYPES = {"I201": "연금", "I202": "보장성", "I203": "생사혼합", "I204": "저축", "I205": "개인연금",
         "I206": "교육", "I207": "양로", "I208": "변액", "I209": "기타"}
# 서류 행에서 (암호값 칸, 파일 이름 칸). 화면 스크립트(doSearchAjax)의 단추 연결과 같다.
DOC_COLUMNS = {"약관": (4, 5), "사업방법서": (6, 7), "상품요약서": (8, 9)}
FORM = {"Content-Type": "application/x-www-form-urlencoded", "Referer": LIST_PAGE}
_PART, _ROW, _COL = "%||%", "%|%", "%,%"
_CODE = re.compile(r"[Pp]\d{7}")
# JavaScript escape()가 그대로 두는 글자
_ESCAPE_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./")


def escape_twice(text: str) -> str:
    """화면의 escape(encodeURIComponent(x)). 한글은 %25EB%25AC%25B4처럼, 괄호는 %28처럼 된다."""
    once = quote(text, safe="-_.!~*'()")
    return "".join(c if c in _ESCAPE_SAFE else f"%{ord(c):02X}" for c in once)


@dataclass(frozen=True)
class Product:
    """상품명 목록의 한 줄. 목록에는 상품명만 있고 상품코드와 판매기간은 서류 행에 있다."""
    name: str
    selling: bool = True     # 판매상품 탭에서 왔는가
    group: str = "I101"      # 구분: I101 개인, I102 단체, I103 방카슈랑스


@dataclass(frozen=True)
class Document:
    name: str          # 목록에 적힌 상품명(요청에 보낸 이름)
    kind: str          # 약관 / 사업방법서 / 상품요약서
    file_name: str     # 공시 화면의 파일 이름. 내려받기에는 쓰지 않는다
    enc: str           # 내려받기 요청의 encValue
    start: str         # 판매 시작일 YYYY-MM-DD
    end: str | None    # 판매 종료일. 판매 중이면 None
    code: str          # 상품코드 칸 원문(<br>은 빈칸으로). 예: "P0001501~P0001801 갱신형"
    seq: str           # 서류 행 번호(4번째 칸)

    @property
    def codes(self) -> tuple[str, ...]:
        """상품코드 칸에 적힌 코드. 범위면 양 끝 두 개. 소문자 p로 적힌 행도 있어 대문자로 맞춘다."""
        return tuple(c.upper() for c in _CODE.findall(self.code))


def _date(text: str) -> str | None:
    """2026.11.02 → 2026-11-02."""
    digits = re.sub(r"\D", "", text or "")
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}" if len(digits) == 8 else None


def _parts(text: str) -> list[str]:
    parts = text.split(_PART)
    if len(parts) < 3:
        head = text[:120].replace("\n", " ")
        raise ValueError(f"흥국생명 목록 응답의 꼴이 다름(%||% 구분 {len(parts) - 1}개): {head}")
    return parts


def _rows(part: str) -> list[list[str]]:
    return [[c.strip() for c in row.split(_COL)] for row in part.split(_ROW) if row.strip()]


def parse_names(text: str) -> list[str]:
    """상품명 목록(응답 첫 부분). 각 줄은 "상품명%,%" 꼴이다. 빈 목록이면 "null"이 온다."""
    return [r[0] for r in _rows(_parts(text)[0]) if r[0] and r[0] != "null"]


def parse_documents(name: str, text: str) -> list[Document]:
    """서류 행(응답 셋째 부분)을 서류 하나씩 펼친다. 파일 이름이 빈 칸은 버린다. 순서는 응답 그대로(최근 판매기간이 먼저)."""
    out = []
    for r in _rows(_parts(text)[2]):
        start = _date(r[0])
        if len(r) < 10 or not start:
            continue
        code = re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", r[2], flags=re.IGNORECASE)).strip()
        for kind, (enc_col, file_col) in DOC_COLUMNS.items():
            if r[file_col]:
                out.append(Document(name, kind, r[file_col], r[enc_col], start, _date(r[1]), code, r[3]))
    return out


def pick_version(docs: list[Document], on: str | None = None, fill_summary: bool = True) -> list[Document]:
    """on(YYYY-MM-DD)에 판매 중이던 판매기간의 서류. on이 없으면 시작일이 가장 늦은 판매기간.

    한 판매기간에 상품코드 행이 여럿(갱신형, 비갱신형, 형별) 있을 수 있어 모두 돌려준다.
    fill_summary면, 고른 판매기간에 상품요약서가 없는 상품코드 행은 같은 상품코드의 앞 판매기간 요약서 가운데
    가장 최근 것을 대신 넣는다. 넣은 문서의 start와 end는 그 요약서가 속한 판매기간이다.
    """
    if not docs:
        return []
    if on is None:
        start = max(d.start for d in docs)
        chosen = [d for d in docs if d.start == start]
    else:
        chosen = [d for d in docs if d.start <= on and (d.end is None or on <= d.end)]
    if not fill_summary or not chosen:
        return chosen
    have = {d.code for d in chosen if d.kind == "상품요약서"}
    first = min(d.start for d in chosen)
    for code in dict.fromkeys(d.code for d in chosen):
        if code in have:
            continue
        earlier = [d for d in docs if d.kind == "상품요약서" and d.code == code and d.start < first]
        if earlier:
            chosen.append(max(earlier, key=lambda d: d.start))
    return chosen


def _post_list(session: Any, selling: bool, group: str, kind: str, name: str, search: str) -> str:
    body = (f"searchFlgSale={'Y' if selling else 'N'}&beforeYn={'' if selling else 'N'}"
            f"&searchCdPublicPrtType1={group}&searchCdPublicPrtType2={kind}"
            f"&searchCdPublicPrtType3={escape_twice(name.replace('+', '%2b'))}&searchText={escape_twice(search)}")
    r = session.post(LIST_AJAX, data=body.encode("ascii"), headers=FORM, timeout=60)
    r.raise_for_status()
    return r.content.decode(ENCODING, errors="replace")


def list_products(session: Any, selling: bool = True, group: str = "I101", kind: str = "",
                  search: str = "") -> list[Product]:
    """구분(group)과 보험유형(kind, 빈 값은 전체)의 상품명 목록. search는 상품명 일부. 요청 한 번(수 KB~수십 KB)."""
    return [Product(n, selling, group) for n in parse_names(_post_list(session, selling, group, kind, "", search))]


def documents(session: Any, name: str, selling: bool = True, group: str = "I101") -> list[Document]:
    """상품명(목록에 적힌 그대로)의 모든 판매기간 서류. selling과 group은 상품이 들어 있는 탭과 맞춘다.
    이름이 맞지 않으면 빈 목록이 온다."""
    return parse_documents(name, _post_list(session, selling, group, "", name, ""))


def list_documents(session: Any, name: str, on: str | None = None, selling: bool = True,
                   group: str = "I101") -> list[Document]:
    """on: 조회 기준일 YYYY-MM-DD. 없으면 가장 최근 판매기간. 요청 한 번."""
    return pick_version(documents(session, name, selling, group), on)


def download(session: Any, doc: Document, selling: bool = True, group: str = "I101") -> bytes:
    # 화면의 FormData(frmPage)와 같은 칸, 같은 순서. 상품명 칸은 화면이 그때 들고 있는 값이다
    fields = [("searchFlgSale", "Y" if selling else "N"), ("searchCdPublicPrtType1", group),
              ("searchCdPublicPrtType2", ""), ("searchCdPublicPrtType3", doc.name.replace("+", "%2b")),
              ("beforeYn", "" if selling else "N"), ("encValue", doc.enc), ("searchText", "")]
    files = [(k, (None, v.encode("utf-8"))) for k, v in fields]
    r = session.post(DOWNLOAD, files=files, headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    disposition = r.headers.get("Content-Disposition", "")
    if "DOWN_LIMIT" in disposition:
        raise ValueError(f"흥국생명 일일 내려받기 횟수 초과: {doc.file_name}")
    # 실패해도 상태 코드는 200이고 alert 스크립트가 온다. 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        text = r.content[:400].decode(ENCODING, errors="replace")
        alert = re.search(r"alert\('([^']*)'", text)
        detail = alert.group(1).replace("\\n", " ") if alert else text[:200].replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.kind} {doc.file_name or '(파일 이름 없음)'} | {detail}")
    return r.content[start:]
