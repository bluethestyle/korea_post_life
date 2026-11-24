"""공시 문서 수집(scripts/fetch_disclosure.py)이 회사 열쇠로 접속 모듈을 찾는 자리.

초기 적재 회사는 여기에 한 줄씩 더한다. 회사마다 접속 모듈의 함수 꼴이 달라서(상품코드로 찾는 곳, 상품명으로 찾는
곳, 목록 한 번에 서류 경로가 다 오는 곳) 여기서 두 함수로 맞춘다.
- find(session, 공시상품코드, 기준일, 공시상품명) → 그날 판매 중인 판매기간의 상품명과 서류 목록(Listed). 판매기간이
  없으면 None. 공시상품명은 대상 설정 종형의 "공시상품명"(없으면 None)이고, 상품을 찾는 데만 쓴다(ID의 재료가 아니다)
- download(session, Listed) → PDF 바이트

회사마다 공시상품코드 자리의 값이 무엇인지(공시실의 상품코드, 게시 번호, 상품명)는 SOURCES의 각 줄 위에 적었다.
상품명으로만 찾을 수 있는 회사는 공시상품명이 있어야 하고, 동양생명은 공시상품명이 없으면 공시상품코드 자리의 값을
상품명으로 본다. 상품명은 공시 목록에 적힌 그대로(빈칸, 괄호 포함) 적는다.
한 번의 find가 요청을 두 번 보내는 회사(상품코드로 상품명을 먼저 찾는 곳 등)는 그 사이에도 GAP초 쉰다.

받는 서류는 kinds(기본 사업방법서와 상품요약서)와 optional이다. optional은 받으면 쓰고, 목록에 없거나 받지 못해도
갖추지 못한 상품으로 세지 않는다. KB라이프생명은 약관을 optional로 받는다(입원 특약의 "1일당"이 요약서에 없고 약관의
특약 조항에만 있어, 급부 적재가 판정값의 지급단위근거로 그 쪽을 본다). 상품설명서는 받지 않는다.
급부 표 조각은 만들지 않는다(삼성화재 경로에만 있다).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from postlife.disclosure import (dongyang, heungkuklife, kblife, kyobo, meritz, metlife, miraeasset, nhlife,
                                 samsunglife, shinhanlife)

KINDS = ("사업방법서", "상품요약서")
GAP = 1.0            # find 안에서 같은 공시실에 요청을 두 번 보낼 때 그 사이에 쉬는 초
pause = time.sleep   # 시험에서 바꿔 끼운다


@dataclass(frozen=True)
class Listed:
    """공시 목록의 서류 한 건. handle은 접속 모듈의 서류 객체이고 download에 그대로 넘긴다."""
    code: str
    name: str
    kind: str
    file_name: str
    start: str
    end: str | None = None
    registered: str | None = None
    handle: Any = field(default=None, compare=False, repr=False)


Found = tuple[str, list[Listed]] | None


@dataclass(frozen=True)
class Source:
    key: str          # --org 값이자 저장 파일 이름의 앞머리
    org: str          # 기관코드 (postlife.config.INSTITUTIONS의 열쇠. 정밀 비교에만 들어가는 회사는 COMPARE_ONLY_LIFE에도 있다)
    label: str        # 실행 요약에 쓰는 회사 이름
    find: Callable[[Any, str, str, str | None], Found]
    download: Callable[[Any, Listed], bytes]
    kinds: tuple[str, ...] = KINDS
    optional: tuple[str, ...] = ()   # 받으면 쓰고 없어도 갖추지 못한 상품으로 세지 않는 서류
    pause: float = 1.0   # 같은 공시실에 보내는 요청(목록 조회, 서류 받기) 사이의 쉬는 초
    lookup: str = ""     # 공시상품코드 자리에 넣는 값(실행 요약과 오류 글에 쓴다)

    @property
    def targets(self) -> str:
        return f"data/targets/{self.key}.json"


def _rest() -> None:
    if GAP > 0:
        pause(GAP)


def _listed(code: str, name: str, docs: list[Any], file_name: Callable[[Any], str]) -> tuple[str, list[Listed]]:
    """접속 모듈의 서류 객체(kind, start, end를 가진 것)를 Listed로. 받지 않는 서류도 그대로 넘긴다(고르는 것은 수집 쪽)."""
    return name, [Listed(code, name, d.kind, file_name(d), d.start, d.end, d.start, d) for d in docs]


def _one(rows: list[Any], what: str, label: str) -> Any | None:
    """조건에 맞는 행이 하나면 그것, 없으면 None, 둘 이상이면 어느 것인지 모르므로 ValueError."""
    if len(rows) > 1:
        raise ValueError(f"{label}: {what}에 맞는 상품이 {len(rows)}개라 하나로 고를 수 없음. 대상 설정에 공시상품명을 적는다")
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# 메리츠화재: 공시상품코드 = 판매상품 목록의 상품코드(nwPdCd. 예: 6AFLT)
# ---------------------------------------------------------------------------

def _meritz_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    """상품코드(nwPdCd)로 판매상품 탭의 판매기간을 조회해 on이 속한 기간을 고른다(요청 한 번).

    서류의 암호값(token)은 이 session에서만 쓸 수 있으므로, 같은 session으로 download를 불러야 한다.
    """
    period = meritz.pick_period(meritz.list_periods(session, code, selling=True), on)
    if period is None:
        return None
    return period.name, [Listed(code, period.name, d.kind, d.file_name, period.start, period.end,
                                period.posted or period.start, d) for d in meritz.documents_of(period, code)]


# ---------------------------------------------------------------------------
# 삼성생명: 공시상품코드 = 목록의 상품코드(goodsCode. 예: LP0842003AB01V10A01). 개정마다 바뀐다
# ---------------------------------------------------------------------------

def _samsunglife_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    """판매상품 탭 전체(요청 한 번, 약 150KB)에서 그 코드의 판매기간을 고른다. 공시상품명이 있으면 그 이름으로 좁혀 받는다.
    법인 상품 행은 서류가 비어 있어 서류 없는 판매기간으로 나온다."""
    period = samsunglife.pick_period(samsunglife.list_products(session, "sales", name or ""), code, on)
    if period is None:
        return None
    return _listed(code, period.name, samsunglife.documents_of(period), lambda d: f"{d.doc_id}.pdf")


# ---------------------------------------------------------------------------
# 교보생명: 공시상품코드 = 목록의 상품코드(dgtPdtCd. 예: 1001031). 세대가 바뀐 상품과 중도부가특약 행이 같은 코드를
# 쓰므로 판매중 목록의 주계약 행으로 좁히고, 그래도 여럿이면 공시상품명으로 고른다
# ---------------------------------------------------------------------------

def _kyobo_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    """판매중 목록(요청 한 번, 약 360KB)에서 코드가 같은 주계약 행을 찾고, 그 행의 판매기간 서류를 받는다(요청 한 번)."""
    rows = [p for p in kyobo.search_products(session, name or "", selling=True)
            if p.code == code and not p.rider_addon and (name is None or p.name == name)]
    product = _one(rows, f"상품코드 {code}", "교보생명")
    if product is None:
        return None
    _rest()
    docs = kyobo.list_documents(session, product, on)
    if not docs:
        return None
    return _listed(code, product.name, docs, lambda d: d.real_name)


# ---------------------------------------------------------------------------
# 신한라이프: 공시상품코드 = 목록의 상품코드 칸(meta04. 예: 7000375). 손으로 넣는 값이라 비거나 겹칠 수 있어,
# 공시상품명이 있으면 이름으로 찾고 코드가 맞는지 본다. 상품구분은 '일반'(대면) 행만 본다
# ---------------------------------------------------------------------------

def _shinhanlife_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    products = shinhanlife.list_products(session, True, channel="일반", search=name or "")
    rows = [p for p in products if (name is None or p.name == name) and (p.code == code or (name and not p.code))]
    if name and not rows and any(p.name == name for p in products):
        found = sorted({p.code for p in products if p.name == name})
        raise ValueError(f"신한라이프: {name}의 상품코드 칸이 {found}이고 대상 설정의 {code}와 다름")
    product = _one(rows, f"상품코드 {code}", "신한라이프")
    if product is None:
        return None
    if shinhanlife.pick_period([product], on):
        period = product
    else:
        _rest()
        period = shinhanlife.pick_period(shinhanlife.list_periods(session, product), on)
    if period is None:
        return None
    return _listed(code, period.name, period.documents, lambda d: d.file_name)


# ---------------------------------------------------------------------------
# NH농협생명: 공시상품코드 = 보험상품 메뉴의 상품코드(prodCd. 예: N0001217). 공시실 응답에는 코드가 없어
# 메뉴에서 상품명을 찾은 뒤(요청 한 번) 그 이름으로 서류 목록을 받는다. 공시상품명이 있으면 메뉴를 건너뛴다
# ---------------------------------------------------------------------------

def _nhlife_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    if name is None:
        names = [n for n, (c, _) in nhlife.product_codes(session).items() if c == code]
        name = _one(names, f"상품코드 {code}", "NH농협생명")
        if name is None:
            return None
        _rest()
    period = nhlife.pick_period(nhlife.list_periods(session, name), on)
    if period is None:
        return None
    return _listed(code, period.name, list(period.documents), lambda d: f"{d.file_id}_{d.seq}")


# ---------------------------------------------------------------------------
# 동양생명: 상품코드가 공시실 응답에도 서류에도 없다. 상품명(공시 목록 그대로)으로 찾는다.
# 공시상품명이 없으면 공시상품코드 자리의 값을 상품명으로 본다. 같은 이름이 판매채널마다 있으면 일반보험 행을 쓴다
# ---------------------------------------------------------------------------

def _dongyang_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    name = name or code
    rows = [p for p in dongyang.list_products(session, search=name) if p.name == name]
    if len(rows) > 1:
        rows = [p for p in rows if p.channel == dongyang.CHANNELS["01"]] or rows
    product = _one(rows, f"상품명 {name}", "동양생명")
    if product is None:
        return None
    if not (on is None or on >= product.start):
        _rest()
    docs = dongyang.list_documents(session, product, on)
    if not docs:
        return None
    return _listed(code, product.name, docs, lambda d: d.file_name or d.file_id)


# ---------------------------------------------------------------------------
# KB라이프생명: 공시상품코드 = 목록의 상품코드(P_CODE. 예: 335000106). 판매상품 탭 전체가 요청 한 번(약 380KB)이다.
# 공시상품명이 있으면 그 이름으로 좁혀 받는다
# ---------------------------------------------------------------------------

def _kblife_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    keyword = kblife.keyword_of(name) if name else ""
    periods = [p for p in kblife.list_periods(session, kblife.SELLING, name=keyword)
               if p.code == code and (name is None or p.name == name.strip())]
    period = kblife.pick_period(periods, on)
    if period is None:
        return None
    return _listed(code, period.name, kblife.documents_of(period), lambda d: d.path.rsplit("/", 1)[-1])


# ---------------------------------------------------------------------------
# 미래에셋생명: 공시상품코드 = 누리집 상품안내 메뉴의 상품코드(publicCd. 예: A3729). 사업방법서 표지의 상품코드 표에도
# 같은 값이 있다. 공시실 목록에는 코드가 없어 메뉴에서 상품명을 찾은 뒤(요청 한 번) 그 이름으로 검색한다.
# 공시상품명이 있으면 메뉴를 건너뛴다. 문서가 그림이라 글자가 풀리지 않는다(받기만 한다)
# ---------------------------------------------------------------------------

def _miraeasset_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    if name is None:
        names = [n for n, c in miraeasset.product_codes(session).items() if c == code]
        name = _one(names, f"상품코드 {code}", "미래에셋생명")
        if name is None:
            return None
        _rest()
    wanted = name.strip()
    period = miraeasset.pick_period([p for p in miraeasset.search_products(session, wanted) if p.name == wanted], on)
    if period is None:
        return None
    return _listed(code, period.name, period.documents(), lambda d: d.file_name)


# ---------------------------------------------------------------------------
# 메트라이프생명: 공시상품코드 = 공시실의 상품 순번(insProdSeq. 예: 733). 상품코드가 목록에 없고, 이 순번은 개정을
# 넘어 이어진다. 공시상품명이 있으면 그 이름으로 검색하고(약 80KB), 없으면 판매상품 목록 전체(약 1.3MB)에서 찾는다
# ---------------------------------------------------------------------------

def _metlife_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    products = metlife.list_products(session, name or "", selling=True)
    if name:
        product = metlife.find_product(products, name)
        if product is not None and product.ins_prod_seq != code:
            raise ValueError(f"메트라이프생명: {name}의 상품 순번이 {product.ins_prod_seq}이고 대상 설정의 {code}와 다름")
    else:
        product = _one([p for p in products if p.ins_prod_seq == code], f"상품 순번 {code}", "메트라이프생명")
    period = metlife.pick_period(product.periods, on) if product else None
    if period is None:
        return None
    return _listed(code, product.name, list(period.documents), lambda d: d.file_name)


# ---------------------------------------------------------------------------
# 흥국생명: 공시상품코드 = 서류 행의 상품코드 칸에 적힌 코드 하나(범위면 첫 코드. 예: P0001901). 공시실은 상품명으로만
# 서류 행을 주므로 공시상품명이 있어야 한다. 한 판매기간에 상품코드 행이 여럿(갱신형, 비갱신형)이고 서류가 서로 다르다.
# 고른 판매기간에 상품요약서가 없으면 같은 상품코드 행의 앞 판매기간 요약서를 쓴다(heungkuklife.pick_version)
# ---------------------------------------------------------------------------

def _heungkuklife_find(session: Any, code: str, on: str, name: str | None = None) -> Found:
    if not name:
        raise ValueError(f"흥국생명: 상품명으로만 서류를 찾을 수 있어 대상 설정의 {code} 종형에 공시상품명이 있어야 함")
    wanted = code.strip().upper()
    docs = [d for d in heungkuklife.documents(session, name) if wanted in d.codes or d.code.upper() == wanted]
    docs = heungkuklife.pick_version(docs, on)
    if not docs:
        return None
    return _listed(code, name, docs, lambda d: d.file_name)


SOURCES: dict[str, Source] = {
    "meritz": Source("meritz", "MERITZ", "메리츠화재", _meritz_find, lambda s, item: meritz.download(s, item.handle),
                     lookup="상품코드(nwPdCd)"),
    "samsunglife": Source("samsunglife", "SAMSUNGLIFE", "삼성생명", _samsunglife_find,
                          lambda s, item: samsunglife.download(s, item.handle), lookup="상품코드(goodsCode)"),
    "kyobo": Source("kyobo", "KYOBO", "교보생명", _kyobo_find, lambda s, item: kyobo.download(s, item.handle),
                    lookup="상품코드(dgtPdtCd)"),
    "shinhanlife": Source("shinhanlife", "SHINHANLIFE", "신한라이프", _shinhanlife_find,
                          lambda s, item: shinhanlife.download(s, item.handle), lookup="상품코드 칸(meta04)"),
    "nhlife": Source("nhlife", "NHLIFE", "NH농협생명", _nhlife_find, lambda s, item: nhlife.download(s, item.handle),
                     lookup="보험상품 메뉴의 상품코드(prodCd)"),
    "dongyang": Source("dongyang", "TONGYANG", "동양생명", _dongyang_find,
                       lambda s, item: dongyang.download(s, item.handle), lookup="상품명(코드 없음)"),
    "kblife": Source("kblife", "KBLIFE", "KB라이프생명", _kblife_find, lambda s, item: kblife.download(s, item.handle),
                     optional=("약관",), lookup="상품코드(P_CODE)"),
    "miraeasset": Source("miraeasset", "MIRAEASSET", "미래에셋생명", _miraeasset_find,
                         lambda s, item: miraeasset.download(s, item.handle), lookup="상품안내 메뉴의 상품코드(publicCd)"),
    "metlife": Source("metlife", "METLIFE", "메트라이프생명", _metlife_find,
                      lambda s, item: metlife.download(s, item.handle), lookup="상품 순번(insProdSeq)"),
    "heungkuklife": Source("heungkuklife", "HEUNGKUKLIFE", "흥국생명", _heungkuklife_find,
                           lambda s, item: heungkuklife.download(s, item.handle), lookup="상품코드 칸의 코드(공시상품명 필요)"),
}
