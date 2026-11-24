"""공시 문서 수집의 생명보험 아홉 곳 연결(postlife.disclosure.sources의 find 함수).

네트워크 없이 돈다. 접속 모듈의 요청 함수(list_products 등)를 지어낸 행을 돌려주는 가짜로 바꿔 끼우고, sources가
그 행에서 대상 코드의 판매기간과 서류를 어떻게 고르는지만 본다. 응답을 읽는 일은 회사마다의 접속 모듈 시험이 본다.
상품코드, 상품명, 파일 이름은 지어낸 것이다.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from postlife import config
from postlife.config import INSTITUTIONS
from postlife.disclosure import (dongyang, heungkuklife, kblife, kyobo, metlife, miraeasset, nhlife, samsunglife,
                                 shinhanlife, sources)

ROOT = Path(__file__).resolve().parents[1]
ON = "2026-11-23"
LIFE = ("samsunglife", "kyobo", "shinhanlife", "nhlife", "dongyang", "kblife", "miraeasset", "metlife", "heungkuklife")


@pytest.fixture
def rests(monkeypatch):
    """find 안의 요청 사이 쉬기를 기록으로 바꾼다."""
    got = []
    monkeypatch.setattr(sources, "pause", got.append)
    return got


def find(key, code, name=None, on=ON):
    return sources.SOURCES[key].find(object(), code, on, name)


def kinds(found):
    name, docs = found
    return name, [(d.kind, d.file_name, d.start, d.end) for d in docs]


# ---------------------------------------------------------------------------
# 등록
# ---------------------------------------------------------------------------

def test_life_companies_are_registered_with_known_org_codes():
    assert set(LIFE) <= set(sources.SOURCES)
    # 모든 회사의 기관코드가 config에 있다. 동향 수집 대상이 아닌 세 회사는 정밀 비교에만 들어가는 회사 표에 있다
    assert all(s.org in INSTITUTIONS for s in sources.SOURCES.values())
    assert {s.org for s in sources.SOURCES.values() if s.org not in config.TREND_INSTITUTIONS} == set(config.COMPARE_ONLY_LIFE)
    assert all(config.LIFE[code] for code in config.COMPARE_ONLY_LIFE)       # 업권은 생명보험
    assert sources.SOURCES["dongyang"].org == "TONGYANG" and sources.SOURCES["kyobo"].org == "KYOBO"
    assert all(s.lookup for s in sources.SOURCES.values())


# ---------------------------------------------------------------------------
# 삼성생명: 상품코드
# ---------------------------------------------------------------------------

def sl_period(code, start, end=None, files=None, name="가나건강보험(2611)"):
    return samsunglife.Period(code, name, start, end, True, "상품운용", "개인", "보장성", "건강", "",
                              files if files is not None else {"상품요약서": f"S{start}", "사업방법서": f"B{start}",
                                                               "약관": f"T{start}"})


def test_samsunglife_picks_the_period_of_the_code_on_the_day(monkeypatch, rests):
    asked = []
    rows = [sl_period("LP01", "2026-08-01", "2026-09-22"), sl_period("LP01", "2026-09-23"), sl_period("LP02", "2026-10-01")]
    monkeypatch.setattr(samsunglife, "list_products", lambda s, tab, keyword: asked.append((tab, keyword)) or rows)
    name, docs = kinds(find("samsunglife", "LP01"))
    assert name == "가나건강보험(2611)" and asked == [("sales", "")]
    assert sorted(docs) == [("사업방법서", "B2026-09-23.pdf", "2026-09-23", None), ("상품요약서", "S2026-09-23.pdf", "2026-09-23", None),
                            ("약관", "T2026-09-23.pdf", "2026-09-23", None)]
    find("samsunglife", "LP01", "가나건강")          # 공시상품명이 있으면 그 이름으로 좁혀 받는다
    assert asked[-1] == ("sales", "가나건강") and rests == []
    assert find("samsunglife", "LP09") is None


# ---------------------------------------------------------------------------
# 교보생명: 상품코드가 겹치면 주계약 행, 그래도 여럿이면 공시상품명
# ---------------------------------------------------------------------------

def ky_product(seq, code, name, rider=False):
    return kyobo.Product(seq, code, name, True, "PAMS04", "02", "2026-08-26", rider, {})


def ky_docs(product, on=None):
    return [kyobo.Document(product.seq, "9", kind, f"KEY_{product.seq}_{kind}", f"{product.name} {kind}.pdf",
                           "2026-08-26", None, product.name) for kind in ("상품요약서", "약관", "사업방법서")]


def test_kyobo_uses_the_main_row_of_the_code_and_rests_between_requests(monkeypatch, rests):
    searched, detailed = [], []
    rows = [ky_product("1", "100", "가나건강보험Ⅱ"), ky_product("2", "100", "가나건강보험 중도부가특약", rider=True),
            ky_product("3", "101", "다라건강보험")]
    monkeypatch.setattr(kyobo, "search_products", lambda s, kw, selling: searched.append((kw, selling)) or rows)
    monkeypatch.setattr(kyobo, "list_documents", lambda s, p, on: detailed.append((p.seq, on)) or ky_docs(p))
    name, docs = kinds(find("kyobo", "100"))
    assert name == "가나건강보험Ⅱ" and searched == [("", True)] and detailed == [("1", ON)]
    assert ("상품요약서", "가나건강보험Ⅱ 상품요약서.pdf", "2026-08-26", None) in docs
    assert rests == [sources.GAP]
    assert find("kyobo", "999") is None


def test_kyobo_same_code_twice_needs_the_product_name(monkeypatch, rests):
    rows = [ky_product("1", "100", "가나건강보험Ⅱ"), ky_product("4", "100", "가나건강보험Ⅱ [D]")]
    monkeypatch.setattr(kyobo, "search_products", lambda s, kw, selling: rows)
    monkeypatch.setattr(kyobo, "list_documents", lambda s, p, on: ky_docs(p))
    with pytest.raises(ValueError, match="2개"):
        find("kyobo", "100")
    assert find("kyobo", "100", "가나건강보험Ⅱ [D]")[1][0].handle.seq == "4"


# ---------------------------------------------------------------------------
# 신한라이프: 상품코드 칸, 공시상품명이 있으면 이름
# ---------------------------------------------------------------------------

def sh_product(name, code, start="2026-08-04", end=None, periods=1, channel="일반"):
    return shinhanlife.Product(name, code, channel, "보장", start, end, True, periods, "신한라이프", "", "DigitalPlattform",
                               {"상품요약서": f"/repo/DigitalPlattform/x/요약_{start}.pdf",
                                "사업방법서": f"/repo/DigitalPlattform/x/방법_{start}.pdf"})


def test_shinhanlife_finds_by_code_in_the_face_to_face_channel(monkeypatch, rests):
    asked = []
    rows = [sh_product("가나통합건강보험", "7001"), sh_product("다라통합건강보험", "7002")]
    monkeypatch.setattr(shinhanlife, "list_products",
                        lambda s, selling, channel, search: asked.append((selling, channel, search)) or rows)
    name, docs = kinds(find("shinhanlife", "7002"))
    assert name == "다라통합건강보험" and asked == [(True, "일반", "")]
    assert docs == [("상품요약서", "요약_2026-08-04.pdf", "2026-08-04", None), ("사업방법서", "방법_2026-08-04.pdf", "2026-08-04", None)]
    assert rests == [] and find("shinhanlife", "7009") is None


def test_shinhanlife_name_must_agree_with_the_code(monkeypatch, rests):
    monkeypatch.setattr(shinhanlife, "list_products", lambda s, selling, channel, search: [sh_product("가나통합건강보험", "7001")])
    assert find("shinhanlife", "7001", "가나통합건강보험")[0] == "가나통합건강보험"
    with pytest.raises(ValueError, match="7001"):
        find("shinhanlife", "7005", "가나통합건강보험")


def test_shinhanlife_past_day_reads_the_period_history(monkeypatch, rests):
    now = sh_product("가나통합건강보험", "7001", "2026-10-12", periods=2)
    old = sh_product("가나통합건강보험", "", "2026-04-01", "2026-10-11")
    monkeypatch.setattr(shinhanlife, "list_products", lambda s, selling, channel, search: [now])
    monkeypatch.setattr(shinhanlife, "list_periods", lambda s, p: [old, now])
    name, docs = kinds(find("shinhanlife", "7001", on="2026-09-01"))
    assert docs[0][2:] == ("2026-04-01", "2026-10-11") and rests == [sources.GAP]


# ---------------------------------------------------------------------------
# NH농협생명: 메뉴의 상품코드로 상품명을 찾고 그 이름으로 서류 목록
# ---------------------------------------------------------------------------

def nh_period(name, start, end=None):
    docs = tuple(nhlife.Document(name, kind, f"FILE_{start}", str(i), start, end)
                 for i, kind in enumerate(("상품요약서", "사업방법서", "약관")))
    return nhlife.Period(name, start, end, docs)


def test_nhlife_code_to_name_then_documents(monkeypatch, rests):
    menu, popups = [], []
    monkeypatch.setattr(nhlife, "product_codes", lambda s: menu.append(1) or {"가나NH건강보험_2609": ("N01", "건강"),
                                                                              "다라NH건강보험": ("N02", "건강")})
    monkeypatch.setattr(nhlife, "list_periods", lambda s, name: popups.append(name) or
                        [nh_period(name, "2026-09-01"), nh_period(name, "2026-03-01", "2026-08-31")])
    name, docs = kinds(find("nhlife", "N01"))
    assert name == "가나NH건강보험_2609" and popups == ["가나NH건강보험_2609"] and rests == [sources.GAP]
    assert docs[1] == ("사업방법서", "FILE_2026-09-01_1", "2026-09-01", None)
    find("nhlife", "N01", "가나NH건강보험_2609")         # 공시상품명이 있으면 메뉴를 건너뛴다
    assert len(menu) == 1 and len(rests) == 1
    assert find("nhlife", "N09") is None and len(popups) == 2


# ---------------------------------------------------------------------------
# 동양생명: 코드가 없어 상품명
# ---------------------------------------------------------------------------

def dy_product(name, channel="일반보험", start="2026-10-01", tag="A"):
    return dongyang.Product(name, channel, "보장성", start, None, {"상품요약서": f"{tag}S", "사업방법서": f"{tag}B"}, "", "1")


def test_dongyang_finds_by_exact_name_and_prefers_the_agent_channel(monkeypatch, rests):
    searched = []
    rows = [dy_product("무배당가나보장보험(갱신형)", tag="R"), dy_product("무배당가나보장보험", "방카슈랑스", tag="K"),
            dy_product("무배당가나보장보험", tag="A")]
    monkeypatch.setattr(dongyang, "list_products", lambda s, search: searched.append(search) or rows)
    name, docs = kinds(find("dongyang", "무배당가나보장보험"))
    assert name == "무배당가나보장보험" and searched == ["무배당가나보장보험"]
    assert docs == [("상품요약서", "AS", "2026-10-01", None), ("사업방법서", "AB", "2026-10-01", None)]
    # 공시상품명이 있으면 공시상품코드 자리의 값 대신 그 이름으로 찾는다
    assert find("dongyang", "DY-임시", "무배당가나보장보험(갱신형)")[1][0].file_name == "RS"
    assert rests == [] and find("dongyang", "무배당없는보험") is None


# ---------------------------------------------------------------------------
# KB라이프생명: 상품코드
# ---------------------------------------------------------------------------

def kb_period(seq, code, name, start, end=None):
    return kblife.Period(seq, code, name, start, end, "보장", "INS03", False,
                         {"상품요약서": f"/up/{seq}S.pdf", "사업방법서": f"/up/{seq}B.pdf"})


def test_kblife_picks_the_code_period_on_the_day(monkeypatch, rests):
    asked = []
    rows = [kb_period("12", "335", "KB 가나 건강보험(일반심사형)", "2026-10-01"),
            kb_period("11", "335", "KB 가나 건강보험(일반심사형)", "2026-07-01", "2026-09-30"),
            kb_period("13", "331", "KB 가나 건강보험(간편심사형)", "2026-10-01")]
    monkeypatch.setattr(kblife, "list_periods", lambda s, tab, name: asked.append((tab, name)) or rows)
    assert kinds(find("kblife", "335"))[1][0] == ("상품요약서", "12S.pdf", "2026-10-01", None)
    assert kinds(find("kblife", "335", on="2026-08-01"))[1][0][1] == "11S.pdf"
    assert asked[0] == (kblife.SELLING, "")
    find("kblife", "331", "KB 가나 건강보험(간편심사형)")       # 서버에는 괄호 앞까지만 보낸다
    assert asked[-1] == (kblife.SELLING, "KB 가나 건강보험")
    assert find("kblife", "331", "KB 가나 건강보험(일반심사형)") is None and rests == []


# ---------------------------------------------------------------------------
# 미래에셋생명: 상품안내 메뉴의 상품코드로 상품명, 그 이름과 글자 그대로 같은 행만
# ---------------------------------------------------------------------------

def mi_period(name, start, end=None):
    return miraeasset.Period(name, "보장성▷건강/암", start, end, True, "/html/up/",
                             files={"상품요약서": f"{name}_요약_{start}.pdf", "사업방법서": f"{name}_방법_{start}.pdf"})


def test_miraeasset_code_to_name_and_exact_name_rows(monkeypatch, rests):
    searched = []
    monkeypatch.setattr(miraeasset, "product_codes", lambda s: {"M-가나 건강보험 무배당": "A01", "M-가나 건강보험(간편) 무배당": "A02"})
    monkeypatch.setattr(miraeasset, "search_products", lambda s, kw: searched.append(kw) or
                        [mi_period("M-가나 건강보험 무배당", "2026-07-11"), mi_period("M-가나 건강보험 무배당", "2026-04-01", "2026-07-10"),
                         mi_period("M-가나 건강보험 무배당 [옛 유형]", "2026-07-11")])
    name, docs = kinds(find("miraeasset", "A01"))
    assert name == "M-가나 건강보험 무배당" and searched == ["M-가나 건강보험 무배당"] and rests == [sources.GAP]
    assert docs[0] == ("상품요약서", "M-가나 건강보험 무배당_요약_2026-07-11.pdf", "2026-07-11", None)
    assert find("miraeasset", "A09") is None


# ---------------------------------------------------------------------------
# 메트라이프생명: 상품 순번
# ---------------------------------------------------------------------------

def mt_product(seq, name, periods):
    made = []
    for pseq, start, end in periods:
        docs = (metlife.Document(seq, pseq, name, "사업방법서", "01", f"방법_{pseq}.pdf", start, end),
                metlife.Document(seq, pseq, name, "상품요약서", "02", f"요약_{pseq}.pdf", start, end))
        made.append(metlife.Period(seq, pseq, name, start, end, docs))
    return metlife.Product(seq, name, "보장", True, tuple(made))


def test_metlife_finds_by_product_sequence(monkeypatch, rests):
    asked = []
    rows = [mt_product("733", "무배당 가나 종합보장보험", [("4172", "2026-07-01", None), ("3900", "2026-01-01", "2026-06-30")]),
            mt_product("857", "무배당 간편 가나 종합보장보험", [("4177", "2026-07-01", None)])]
    monkeypatch.setattr(metlife, "list_products", lambda s, kw, selling: asked.append(kw) or rows)
    name, docs = kinds(find("metlife", "733"))
    assert name == "무배당 가나 종합보장보험" and docs[1] == ("상품요약서", "요약_4172.pdf", "2026-07-01", None)
    assert kinds(find("metlife", "733", on="2026-03-01"))[1][0][1] == "방법_3900.pdf"
    assert asked == ["", ""] and find("metlife", "999") is None
    assert find("metlife", "857", "무배당  간편 가나 종합보장보험")[1][0].file_name == "방법_4177.pdf"   # 빈칸 수만 다른 이름
    with pytest.raises(ValueError, match="857"):
        find("metlife", "733", "무배당 간편 가나 종합보장보험")


# ---------------------------------------------------------------------------
# 흥국생명: 상품명으로 서류 행을 받고 상품코드 칸으로 행을 고른다
# ---------------------------------------------------------------------------

def hk_doc(kind, start, end, code, file_name):
    return heungkuklife.Document("(무)가나통합보험", kind, file_name, f"ENC-{file_name}", start, end, code, "1")


HK_ROWS = [
    hk_doc("사업방법서", "2026-11-02", None, "P0000101~P0000301", "가나_방법(202611).pdf"),
    hk_doc("사업방법서", "2026-11-02", None, "P0000501~P0000601 갱신형", "가나갱신_방법(202611).pdf"),
    hk_doc("상품요약서", "2026-11-02", None, "P0000501~P0000601 갱신형", "가나갱신_요약(20261102).pdf"),
    hk_doc("사업방법서", "2026-08-10", "2026-11-01", "P0000101~P0000301", "가나_방법(202608).pdf"),
    hk_doc("상품요약서", "2026-08-10", "2026-11-01", "P0000101~P0000301", "가나_요약(20260810).pdf"),
]


def test_heungkuklife_needs_the_name_and_picks_the_code_group(monkeypatch, rests):
    asked = []
    monkeypatch.setattr(heungkuklife, "documents", lambda s, name: asked.append(name) or HK_ROWS)
    with pytest.raises(ValueError, match="공시상품명"):
        find("heungkuklife", "P0000101")
    assert asked == []
    name, docs = kinds(find("heungkuklife", "p0000501", "(무)가나통합보험"))
    assert name == "(무)가나통합보험" and asked == ["(무)가나통합보험"]
    assert docs == [("사업방법서", "가나갱신_방법(202611).pdf", "2026-11-02", None),
                    ("상품요약서", "가나갱신_요약(20261102).pdf", "2026-11-02", None)]
    # 지금 판매기간에 요약서가 없는 코드 행은 같은 코드 행의 앞 판매기간 요약서를 쓴다
    name, docs = kinds(find("heungkuklife", "P0000301", "(무)가나통합보험"))
    assert docs == [("사업방법서", "가나_방법(202611).pdf", "2026-11-02", None),
                    ("상품요약서", "가나_요약(20260810).pdf", "2026-08-10", "2026-11-01")]
    assert find("heungkuklife", "P0000901", "(무)가나통합보험") is None and rests == []


# ---------------------------------------------------------------------------
# 수집 스크립트: 대상 설정의 공시상품명을 find에 넘긴다
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location("fetch_disclosure_life", ROOT / "scripts/fetch_disclosure.py")
fd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fd)


def test_script_passes_the_product_name_and_skips_codes_with_two_names(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(fd, "pdf_pages", lambda data: ["첫 쪽"])
    monkeypatch.setattr(fd, "pause", lambda s: None)
    monkeypatch.setattr(fd, "session", lambda: object())
    asked, got = [], []
    monkeypatch.setattr(heungkuklife, "documents", lambda s, name: asked.append(name) or HK_ROWS)
    monkeypatch.setattr(heungkuklife, "download", lambda s, doc: got.append(doc.file_name) or b"%PDF-1.7\n" + doc.enc.encode())
    products = [{"모상품ID": "A", "종형": [{"공시상품코드": "P0000501", "종형명": "갱신형", "공시상품명": "(무)가나통합보험"}]},
                {"모상품ID": "B", "종형": [{"공시상품코드": "P0000101", "종형명": "1종", "공시상품명": "(무)가나통합보험"},
                                          {"공시상품코드": "P0000101", "종형명": "2종", "공시상품명": "(무)가나통합보험2"}]}]
    target = tmp_path / "t.json"
    target.write_text(json.dumps({"기관코드": "HEUNGKUKLIFE", "상품": products}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["fetch_disclosure.py", "--org", "heungkuklife", "--out", str(out), "--targets", str(target)])
    assert fd.main() == 1                          # P0000101은 공시상품명이 둘이라 받지 않는다
    assert asked == ["(무)가나통합보험"] and got == ["가나갱신_방법(202611).pdf", "가나갱신_요약(20261102).pdf"]
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert [(e["기관"], e["상품코드"], e["문서"], e["저장이름"]) for e in index] == [
        ("HEUNGKUKLIFE", "P0000501", "사업방법서", "heungkuklife_P0000501_사업방법서"),
        ("HEUNGKUKLIFE", "P0000501", "상품요약서", "heungkuklife_P0000501_상품요약서")]
    printed = capsys.readouterr().out
    assert "| P0000101 | | 공시상품명이 종형마다 다름 | (무)가나통합보험, (무)가나통합보험2 | | | |" in printed
    assert printed.splitlines()[-1] == "갖추지 못한 상품: P0000101(사업방법서, 상품요약서)"
