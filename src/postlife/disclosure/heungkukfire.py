"""흥국화재 상품공시(heungkukfire.co.kr)의 '보험상품공시'에서 상품 목록과 기초서류를 받는다.

공시 화면(/FRW/announce/insGoodsGongsiSale.do)이 쓰는 요청을 그대로 따른다 (2026-11-19 확인).
목록은 ajax 응답이 아니라 서버가 그린 HTML 표다. 화면은 폼(frm)을 같은 주소로 POST해 탭과 쪽을 바꾼다.
- 상품 목록:   POST /FRW/announce/insGoodsGongsiSale.do  page=<쪽>&mode=go|stop&type=1|2|3&searchvalue=<검색어>
               mode는 판매 "go", 판매중지 "stop". type은 장기보험 "1", 일반보험 "2", 자동차보험 "3".
               쪽마다 10행이고, 응답은 메뉴를 포함해 쪽마다 약 270KB다(장기보험 판매 탭은 7쪽 64행).
               행의 칸: 구분(의료/건강 …), 판매년도, 상품명, 판매일, 첨부파일. 판매일은 판매 탭에서 개시일 하나
               ("2026-11-01"), 판매중지 탭에서 "2026-10-01 ~ 2026-10-31"이다.
               searchvalue는 서버가 상품명으로 거른다. 괄호가 든 상품명 전체를 넣어도 그 행만 왔다.
- 서류 목록:   따로 없다. 목록 행의 첨부파일 단추마다 onclick="fn_filedownX('/Upload/gongsi/goods/', 원래 이름, 저장 이름)"이
               있다. 단추 글자는 상품약관, 사업방법서, 상품요약서다. '사업방법서' 단추의 파일은 '사업방법서 별지'다.
- 서류 내려받기: POST /common/download.do?temp=<밀리초>  filePath, fileRealName, fileSaveName, mode=View
               (cyber_common.js fn_filedownX). 화면은 fileEncYn=undefined도 보내지만 빼고 보내도 같은 파일이 왔다.
               성공하면 Content-Type application/octet-stream으로 PDF가 온다. 파일이 없으면 상태 200,
               text/html 194바이트의 alert('파일을 다운로드하는데 실패했습니다…') 스크립트가 온다.

로그인, 세션 쿠키, 암호화, 토큰은 필요 없다. 쿠키 없는 새 세션의 첫 요청으로 목록과 서류가 왔고, 내려받기는 Referer 없이도
됐다(화면과 같게 붙여 보낸다). 상품코드는 목록에도 파일 이름에도 없다. 저장 이름(1794469287104249.pdf)은 올린 시각으로
보이는 숫자일 뿐이다. 한 상품이 종(1종/2종, 갱신형/비갱신형)마다 다른 행으로 올라오고, 원래 이름이 같은 요약서가 행마다
다른 저장 이름으로 따로 올라온다(든든한 3N5, The건강한 4565에서 두 행의 요약서가 바이트까지 같았다).
"""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from typing import Any

BASE = "https://www.heungkukfire.co.kr"
LIST_PAGE = BASE + "/FRW/announce/insGoodsGongsiSale.do"
DOWNLOAD = BASE + "/common/download.do"
FILE_PATH = "/Upload/gongsi/goods/"
INS_TYPES = {"1": "장기보험", "2": "일반보험", "3": "자동차보험"}
# 첨부파일 단추 글자 → 서류 종류
DOC_KINDS = {"상품약관": "약관", "사업방법서": "사업방법서", "상품요약서": "상품요약서"}
_TBODY = re.compile(r"<tbody>(.*?)</tbody>", re.S)
_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_BUTTON = re.compile(r"fn_filedownX\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*\)[^>]*>([^<]*)</a>")
_GO_PAGE = re.compile(r"goPage\((\d+)\)")
_ON_PAGE = re.compile(r'class="on"><span>(\d+)</span>')
_MODE = re.compile(r'id="mode" value="([^"]*)"')
_ALERT = re.compile(r"alert\('([^']*)'")


@dataclass(frozen=True)
class Document:
    name: str          # 목록 행의 상품명
    kind: str          # 약관 / 사업방법서(별지) / 상품요약서
    file_name: str     # 원래 이름(fileRealName). 상품명과 띄어쓰기가 다르기도 하다
    save_name: str     # 저장 이름(fileSaveName). 내려받기 요청에 그대로 넣는다
    path: str = FILE_PATH
    start: str = ""
    end: str | None = None


@dataclass(frozen=True)
class Product:
    """목록 한 행. 종이나 갱신 여부마다 행이 따로 있다. 판매중지 탭에는 지난 개정판이 판매기간마다 한 행씩 있다."""
    name: str
    category: str               # 구분: 의료/건강, 운전자/상해, 연금/저축 …
    year: str                   # 판매년도
    start: str                  # 판매 개시일 YYYY-MM-DD
    end: str | None             # 판매 종료일. 판매 탭이면 None
    selling: bool               # 판매 탭(mode=go)에서 왔는가
    ins_type: str = "1"         # 1 장기보험, 2 일반보험, 3 자동차보험
    documents: tuple[Document, ...] = field(default=(), compare=False, hash=False)

    @property
    def files(self) -> dict[str, Document]:
        return {d.kind: d for d in self.documents}


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell))).strip()


def _period(text: str) -> tuple[str, str | None]:
    """'2026-11-01' 또는 '2026-10-01 ~ 2026-10-31' → (개시일, 종료일)."""
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if not dates:
        return "", None
    return dates[0], dates[1] if len(dates) > 1 else None


def _form_part(page: str) -> str:
    """목록 폼(id="frm") 부분. 화면의 나머지는 메뉴와 팝업이다. 목록 화면이 아니면 ValueError."""
    at = page.find('id="frm"')
    end = page.find("</form>", at)
    if at < 0 or end < 0 or _TBODY.search(page, at, end) is None:
        head = re.sub(r"\s+", " ", page[:200])
        raise ValueError(f"흥국화재 상품공시 목록 화면이 아님: {head}")
    return page[at:end]


def parse_list(page: str, ins_type: str = "1") -> tuple[list[Product], int]:
    """목록 화면 HTML → (행 목록, 마지막 쪽 번호). 판매/판매중지는 폼의 mode 값으로 가린다."""
    part = _form_part(page)
    body = _TBODY.search(part).group(1)
    mode = _MODE.search(part)
    selling = (mode.group(1) if mode else "go") != "stop"
    products = []
    for row in _ROW.findall(body):
        cells = _CELL.findall(row)
        if len(cells) < 5:          # 결과가 없을 때의 안내 행 등
            continue
        category, year, name, sold = (_text(c) for c in cells[:4])
        start, end = _period(sold)
        if not name or not start:
            continue
        docs = tuple(
            Document(name, DOC_KINDS.get(label.strip(), label.strip()), html.unescape(real).strip(),
                     html.unescape(save).strip(), html.unescape(path).strip() or FILE_PATH, start, end)
            for path, real, save, label in _BUTTON.findall(cells[4]))
        products.append(Product(name, category, year, start, end, selling, ins_type, docs))
    # 쪽 링크는 표 아래 paginate 칸에 있다. 마지막 쪽이 아니면 '마지막으로' 링크가 goPage(마지막 쪽)이다
    paging = part[part.find("paginate"):] if "paginate" in part else ""
    numbers = [int(n) for n in _GO_PAGE.findall(paging)] + [int(n) for n in _ON_PAGE.findall(paging)]
    return products, max(numbers, default=1)


def _get_page(session: Any, page: int, selling: bool, ins_type: str, keyword: str) -> str:
    form = {"page": str(page), "mode": "go" if selling else "stop", "type": ins_type, "searchvalue": keyword}
    r = session.post(LIST_PAGE, data=form, headers={"Referer": LIST_PAGE}, timeout=60)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def list_products(session: Any, selling: bool = True, ins_type: str = "1", keyword: str = "",
                  max_pages: int = 100) -> list[Product]:
    """탭(판매/판매중지, 보험 종류)의 모든 쪽을 차례로 받는다. 쪽마다 요청 한 번(약 270KB).

    판매중지 탭은 지난 개정판마다 행이 있어 쪽이 많을 수 있으니 keyword로 좁혀 쓴다(전체 쪽 수는 확인하지 않았다).
    """
    products: list[Product] = []
    page, last = 1, 1
    while page <= min(last, max_pages):
        found, last = parse_list(_get_page(session, page, selling, ins_type, keyword), ins_type)
        products += found
        page += 1
    return products


def search_products(session: Any, keyword: str, selling: bool = True, ins_type: str = "1") -> list[Product]:
    """상품명에 keyword가 든 행. 탭은 하나씩 고른다(판매 중과 판매중지를 함께 주는 검색은 없다)."""
    return list_products(session, selling, ins_type, keyword)


def list_documents(session: Any, name: str, selling: bool = True, ins_type: str = "1") -> list[Document]:
    """목록에 적힌 상품명과 똑같은 행의 서류. 상품명 전체로 검색해 받는다(보통 요청 한 번).

    판매중지 탭에서는 같은 이름이 판매기간마다 여러 행일 수 있어, 개시일이 가장 늦은 행을 고른다.
    """
    rows = [p for p in search_products(session, name, selling, ins_type) if p.name == name.strip()]
    if not rows:
        return []
    return list(max(rows, key=lambda p: p.start).documents)


def download(session: Any, doc: Document) -> bytes:
    form = {"filePath": doc.path, "fileRealName": doc.file_name, "fileSaveName": doc.save_name, "mode": "View"}
    r = session.post(DOWNLOAD, params={"temp": str(int(time.time() * 1000))}, data=form,
                     headers={"Referer": LIST_PAGE}, timeout=300)
    r.raise_for_status()
    # 파일이 없어도 상태 코드는 200이고 alert 스크립트가 온다. 문서 시작 표식으로 가린다
    start = r.content[:2048].find(b"%PDF-")
    if start < 0:
        text = r.content[:400].decode("utf-8", errors="replace")
        alert = _ALERT.search(text)
        head = alert.group(1).replace("\\n", " ") if alert else text[:200].replace("\n", " ")
        raise ValueError(f"PDF가 아닌 응답({r.headers.get('Content-Type', '')}, {len(r.content)}바이트): "
                         f"{doc.file_name} ({doc.save_name}) | {head}")
    return r.content[start:]
