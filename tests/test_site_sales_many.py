"""회사가 많을 때의 영업 인사이트(site/sales.py): 이름 나열 줄이기, 지도 칸의 상대 수, 브리핑의 분포, 범위 문장과 머리말.

자료는 test_site_sales.py 의 지어낸 세 회사에 가상 회사 셋(가상생명 01, 02, 가상화재 01)을 더해 상대가 다섯 곳이다.
가상 회사의 이름과 업권은 사본의 meta.json 이 싣는 이름 표(기관이름, 기관업권)로 준다. 공시 원문은 옮기지 않는다.
세 회사 사본의 출력이 그대로인지는 test_site_sales.py(지금 문장)와 test_console4_data.py(실제 사본, 더한 열쇠만 다름)가 본다.
"""
import pytest

from postlife.site import sales as S
from postlife.site.model import Data
from test_site_sales import (E1, EG, H1, NAMES, REL, S1, UNPAID, Book, P, forbidden_hits, std)

L1, L2, F1 = "SYNLIFE01_L1_dddddd", "SYNLIFE02_L2_eeeeee", "SYNFIRE01_F1_ffffff"
META = {"기관이름": {"SYNLIFE01": "가상생명 01", "SYNLIFE02": "가상생명 02", "SYNFIRE01": "가상화재 01"},
        "기관업권": {"SYNLIFE01": "생명보험", "SYNLIFE02": "생명보험", "SYNFIRE01": "손해보험"}}
PEERS5 = (H1, S1, F1, L1, L2)          # 화면 차례(기관코드 차례)


def extra(l1_ages=((15, 80),)):
    return [
        (L1, "SYNLIFE01", "간편가입형(1년)", "간편심사", "3.1.5", (3, 1, 5, True, 7), "비갱신", UNPAID, "2026-10-01", list(l1_ages)),
        (L2, "SYNLIFE02", "간편가입형(1년)", "간편심사", "3.1.5", (3, 1, 5, True, 7), "비갱신", UNPAID, "2026-10-01", [(16, 80)]),
        (F1, "SYNFIRE01", "7종(간편315)", "간편심사", "3.1.5", (3, 1, 5, True, 5), "갱신", UNPAID, "2026-07-01", [(17, 79)]),
    ]


def many_book(l1_ages=((15, 80),)) -> Book:
    b = Book(extra=extra(l1_ages))
    b.t["hum_표준담보사전"] = [std(sid, *v) for sid, v in NAMES.items()]
    for v in PEERS5:
        b.ben(v, "STD_CA_GAP")                     # 다섯 곳 모두 가진 담보(우체국에 없음): Q2
    b.ben(E1, "STD_HT_ONLY")                       # 우체국에만 있는 입원 담보: A1
    b.ben(E1, "STD_BR_C", red=(12, 0.5))           # 우체국만 감액: Q3(상대 넷)
    for v in (H1, F1, L1, L2):
        b.ben(v, "STD_BR_C")
    return b


@pytest.fixture()
def data():
    return Data(many_book().t, META)


# ---------- 이름 나열 ----------
def test_join_shortens_four_or_more_names_only_with_a_unit():
    four = ["가", "나", "다", "라"]
    # 회사 수는 "개사"로 센다(용어 대조표 185)
    assert S.and_join(four, S.UNIT_ORG) == "가, 나, 다 등 4개사"
    assert S.or_join(four, S.UNIT_ORG) == "가, 나, 다 등 4개사"
    assert S.and_join(four, S.UNIT_KIND) == "가, 나, 다 등 4개"
    # 셋까지, 그리고 단위를 주지 않은 이름(표준담보, 조건 항목)은 지금 그대로다
    assert S.and_join(four[:3], S.UNIT_ORG) == S.and_join(four[:3]) == "가, 나와 다"
    assert S.or_join(four[:2], S.UNIT_ORG) == "가나 나"
    assert S.and_join(four) == "가, 나, 다와 라"
    # 줄인 이름 뒤의 조사는 "개사", "개"의 받침을 따른다
    assert S.render("G1_상대_기간", {"상대": S.and_join(four, S.UNIT_KIND), "상대기간": 1, "상대범위": "입원"}) == \
        "가, 나, 다 등 4개는 1년 이내의 입원을 고지 대상으로 합니다."
    assert S.render("Q3_질문", {"담보": "암 진단비", "상대회사": S.or_join(four, S.UNIT_ORG)}) == \
        "암 진단비는 가, 나, 다 등 4개사와 지급 조건이 다르다던데요."


def test_org_names_and_sectors_come_from_the_meta_table_first(data):
    assert data.org_name("SYNLIFE01") == "가상생명 01" and data.org_name("HANWHALIFE") == "한화생명"
    assert data.org_sector("SYNFIRE01") == "손해보험" and data.org_sector("HANWHALIFE") == "생명보험"
    assert data.org_sector("SAMSUNGFIRE") == "손해보험" and data.org_sector("EPOST") is None
    bare = Data(many_book().t)                       # 이름 표가 없으면 기관코드 그대로(지어내지 않는다)
    assert bare.org_name("SYNLIFE01") == "SYNLIFE01" and bare.org_sector("SYNLIFE01") is None


# ---------- 범위 문장과 머리말 ----------
def test_scope_sentence_counts_companies_by_sector(data):
    pts = S.points(data, E1, P(), None, REL)
    assert pts["맞붙는종형"] == list(PEERS5)
    s = pts["범위"]
    assert s["문장"].startswith("비교한 상품은 생명보험 3개사, 손해보험 2개사의 상품 5개입니다. 갱신과 해약환급금 구조는 우체국이 "
                              "갱신, 표준형이고 한화생명, 가상생명 01과 가상생명 02는 비갱신, 해약환급금 미지급형, 삼성화재와 "
                              "가상화재 01은 갱신, 해약환급금 미지급형입니다.")
    assert s["업권별"] == {"생명보험": 3, "손해보험": 2}
    assert [r["종형ID"] for r in s["상대"]] == list(PEERS5)          # 목록은 값에 그대로 둔다
    assert all(r["머리말"].startswith("비교 기준: ") for r in s["상대"])
    assert s["머리말"].startswith("비교 기준: 5개사 상품 5개(2026-07-01~2026-10-01) / 구조 상이: 우체국 갱신, 표준형 대 ")
    # 업권을 모르는 상대가 있으면 구분을 빼고 회사 수만 적는다
    meta = {"기관이름": META["기관이름"], "기관업권": {"SYNFIRE01": "손해보험"}}
    unknown = S.points(Data(many_book().t, meta), E1, P(), None, REL)["범위"]
    assert unknown["문장"].startswith("비교한 상품은 타사 5개사의 상품 5개입니다.")
    assert unknown["업권별"] == {"생명보험": 1, "손해보험": 2, S.SECTOR_UNKNOWN: 2}


# ---------- 포인트 문장 ----------
def by_code(pts, code, sid=None):
    return [x for x in pts["포인트"] if x["세부"] == code and (sid is None or x["표준담보ID"] == sid)]


def test_point_sentences_shorten_company_lists_but_keep_evidence(data):
    pts = S.points(data, E1, P(), None, REL)
    q2 = by_code(pts, "Q2", "STD_CA_GAP")[0]
    assert q2["문장"] == "한화생명, 삼성화재, 가상화재 01 등 5개사에 있는 암 빈자리는 우체국 1종(간편가입315)에 없습니다."
    assert q2["카드질문"] == "한화생명, 삼성화재, 가상화재 01 등 5개사에는 암 빈자리가 있던데요."
    assert q2["비교종형ID"] == list(PEERS5)
    assert {e["종형ID"] for e in q2["근거"]} == {*PEERS5}                  # 근거 목록은 줄이지 않는다
    assert q2["머리말"].startswith("비교 기준: 5개사 상품 5개")
    a1 = by_code(pts, "A1", "STD_HT_ONLY")[0]
    assert a1["문장"].startswith("심장 입원은 우체국 1종(간편가입315)에 있는 별도 담보입니다. "
                               "비교한 한화생명, 삼성화재, 가상화재 01 등 5개사의 상품에는 이 담보를 보장하는 별도 급부가 없습니다.")
    q3 = by_code(pts, "Q3", "STD_BR_C")[0]
    assert "한화생명 간편가입형(1년), 가상화재 01 7종(간편315), 가상생명 01 간편가입형(1년) 등 4개는 감액기간이 없습니다" \
        in q3["문장"]
    assert q3["카드질문"] == "뇌 조건은 한화생명, 가상화재 01, 가상생명 01 등 4개사와 지급 조건이 다르다던데요."


def test_g2_groups_open_peers_by_age_span(data):
    # 17세: 우체국 간편 종형(20~80세)은 나이로 닫히고 상대 넷이 열린다(삼성화재는 나이 자료가 없다)
    g2 = by_code(S.points(data, E1, P(age=17, sex="M"), None, REL), "G2")[0]
    assert g2["문장"] == ("17세는 우체국 1종(간편가입315)의 가입나이(20~80세) 범위 밖입니다. "
                         "한화생명 간편가입형(1년)과 가상생명 01 간편가입형(1년)의 가입나이는 15~80세입니다. "
                         "가상화재 01 7종(간편315)의 가입나이는 17~79세입니다. 가상생명 02 간편가입형(1년)의 가입나이는 16~80세입니다. "
                         "우체국에서는 일반심사 종형(4종(일반가입), 15~65세)으로 인수심사를 받을 수 있습니다.")
    assert set(g2["비교종형ID"]) == {H1, F1, L1, L2}
    # 가입나이가 넷 이상으로 갈리면 하한과 상한의 범위만 적는다
    spread_data = Data(many_book(l1_ages=((15, 78),)).t, META)
    g2 = by_code(S.points(spread_data, E1, P(age=17, sex="M"), None, REL), "G2")[0]
    assert ("한화생명 간편가입형(1년), 가상화재 01 7종(간편315), 가상생명 01 간편가입형(1년) 등 4개의 가입나이 하한은 15~17세, "
            "상한은 78~80세입니다.") in g2["문장"]
    assert len(g2["근거"]) == 5                                              # 기준 종형과 상대 넷


# ---------- 지도 칸과 브리핑 ----------
def test_peer_tally_counts_states():
    states = {"EPOST": S.OPEN, "A": S.OPEN, "B": S.REVIEW, "C": S.CLOSED, "D": S.NO_AGE, "E": S.NO_QUESTION, "F": S.PARTIAL}
    gate_only = [{"기관코드": "A", "종형ID": "A_1"}, {"기관코드": "A", "종형ID": "A_2"}]
    assert S.peer_tally(states, gate_only) == {"상대수": 6, "열린상대수": 1, "닫힌상대수": 2, "모르는상대수": 2,
                                               "관문만열린상대수": 1, "일부열린상대수": 1}
    assert S.peer_codes(states, gate_only) == {"열린상대코드": ["A"], "관문만열린상대코드": ["A"], "닫힌상대코드": ["B", "C"],
                                               "모르는상대코드": ["D", "E"], "일부열린상대코드": ["F"]}


# ---------- 지도의 나이 열(우리 기관의 가입나이로만 끊는다) ----------
def test_map_columns_come_from_our_ages_only(data):
    """상대가 다섯 곳이고 가입나이가 15~80, 16~80, 17~79세로 달라도 열은 세 회사 자료와 같다(우리 종형 20~80, 15~65세)."""
    three = Data(Book().t)
    many = S.segment_map(data, "M", None, None, REL)
    assert many["열"] == S.segment_map(three, "M", None, None, REL)["열"] == [
        {"lo": 15, "hi": 19}, {"lo": 20, "hi": 65}, {"lo": 66, "hi": 80}]
    assert S.home_age_edges(data) == [15, 20, 66, 81]
    # 15~19세 이력 없음: 가상생명 02(16~80세)와 가상화재 01(17~79세)은 그 열의 일부 나이에서만 열린다
    x = many["칸"][2][0]
    assert x["회사"]["SYNLIFE02"] == x["회사"]["SYNFIRE01"] == S.PARTIAL
    assert x["일부열린나이"] == {"SYNLIFE02": [[16, 19]], "SYNFIRE01": [[17, 19]]}
    assert (x["일부열린상대수"], S.peer_codes(x["회사"], x["관문만수집"])["일부열린상대코드"]) == (2, ["SYNFIRE01", "SYNLIFE02"])
    assert x["열린상대수"] == 2 and not x["일부나이로만열림"]                  # 한화생명, 가상생명 01은 15~19세 모두 열린다
    # 66~80세: 가상화재 01은 79세까지
    assert many["칸"][2][2]["일부열린나이"] == {"SYNFIRE01": [[66, 79]]}
    # 넷(열린, 일부 열린, 닫힌, 모르는)은 겹치지 않고 합하면 상대수다
    for line in many["칸"]:
        for c in line:
            assert c["열린상대수"] + c["일부열린상대수"] + c["닫힌상대수"] + c["모르는상대수"] == c["상대수"] == 5


def test_partial_peer_counts_as_open_and_marks_the_cell():
    """열린 상대가 일부 나이만 열린 상대뿐이면 라벨은 열린 상대가 있는 것으로 치고 칸에 표시(일부나이로만열림)를 남긴다.
    칸의 세부 값은 칸의 라벨과 같은 라벨이 나오는 나이(17세)에서 계산하고, 브리핑 (가)의 둘째 문장 끝에 그 칸 수를 적는다."""
    only = (L2, "SYNLIFE02", "간편가입형(1년)", "간편심사", "3.1.5", (3, 1, 5, True, 7), "비갱신", UNPAID, "2026-10-01",
            [(17, 80)])
    b = Book(skip=(H1, "HANWHALIFE_HG_bbbbbb", S1, "SAMSUNGFIRE_SA_cccccc", "SAMSUNGFIRE_SB_cccccc"), extra=[only])
    d = Data(b.t, META)
    seg = S.segment_map(d, "M", None, None, REL)
    x = seg["칸"][2][0]                                     # 15~19세 이력 없음: 우리 간편(20세부터)은 나이로 닫힌다
    assert x["라벨"] == S.LABELS[S.ONLY_CLOSED] and x["회사"]["SYNLIFE02"] == S.PARTIAL
    assert (x["열린상대수"], x["일부열린상대수"], x["일부나이로만열림"], x["세부나이"], x["대표구간"]) == (0, 1, True, 17, [17, 19])
    assert seg["칸"][2][1]["대표구간"] == [20, 65]
    assert x["상대대표"] == {"SYNLIFE02": L2}                # 17세에서 견준 짝
    line = S.briefing(d, E1, P(age=30), None, REL, seg=seg)[0]
    assert line["값"]["일부열림칸수"] >= line["값"]["일부나이로만열림칸수"] >= 1
    assert line["틀"][-1] == "가_일부나이만" and line["문장"].count(". ") <= 1
    assert line["문장"].endswith(f"그 가운데 {line['값']['일부나이로만열림칸수']}개 고객군은 가입 가능한 타사가 그 타사뿐입니다.")


def test_notice_attributes_count_values_inside_a_key(data):
    attrs = S.notice_attributes(data)
    assert list(attrs) == ["3·1·5", S.GENERAL]
    a = attrs["3·1·5"]
    assert a["수술포함별"] == [{"값": True, "상대수": 5, "상대코드": sorted(S._org(data, v) for v in PEERS5), "종형수": 5}]
    assert a["중대질병수별"] == [{"값": 5, "상대수": 2, "상대코드": ["SAMSUNGFIRE", "SYNFIRE01"], "종형수": 2},
                             {"값": 7, "상대수": 3, "상대코드": ["HANWHALIFE", "SYNLIFE01", "SYNLIFE02"], "종형수": 3}]
    assert a["가입나이별"]["M"] == [
        {"값": [15, 80], "상대수": 2, "상대코드": ["HANWHALIFE", "SYNLIFE01"], "종형수": 2},
        {"값": [16, 80], "상대수": 1, "상대코드": ["SYNLIFE02"], "종형수": 1},
        {"값": [17, 79], "상대수": 1, "상대코드": ["SYNFIRE01"], "종형수": 1},
        {"값": None, "상대수": 1, "상대코드": ["SAMSUNGFIRE"], "종형수": 1}]        # 삼성화재 315는 가입나이 자료가 없다


def test_notice_key_and_groups(data):
    assert S.notice_key(data, E1) == "3·1·5" and S.notice_key(data, EG) == S.GENERAL
    blank = Data(many_book().t, META)
    blank.variants[L2] = dict(blank.variants[L2], 고지입원수술년수=None)
    zero = dict(blank.variants[F1], 고지입원수술년수=0)
    blank.variants[F1] = zero
    assert S.notice_key(blank, L2) == S.NOTICE_UNKNOWN and S.notice_key(blank, F1) == "3·0·5"
    groups = S.notice_groups(data, E1, list(PEERS5))
    mine = [g for g in groups if g["기준"]]
    assert [g["열쇠"] for g in mine] == ["3·1·5"] and mine[0]["맞붙는종형수"] == 5
    assert mine[0]["상대코드"] == sorted({S._org(data, v) for v in PEERS5}) and mine[0]["상대수"] == len(mine[0]["상대코드"])
    assert [g["열쇠"] for g in groups][-1] == S.GENERAL      # 간편 열쇠 다음에 일반심사


def test_map_cells_count_peers_and_briefing_adds_the_spread(data):
    seg = S.segment_map(data, "M", None, None, REL)
    cells = [x for line in seg["칸"] for x in line]
    for x in cells:
        assert x["상대수"] == 5 == x["열린상대수"] + x["일부열린상대수"] + x["닫힌상대수"] + x["모르는상대수"]
        assert x["열린상대수"] == sum(1 for o, s in x["회사"].items() if o != "EPOST" and s == S.OPEN)
        assert x["일부열린상대수"] == sum(1 for o, s in x["회사"].items() if o != "EPOST" and s == S.PARTIAL)
    lines = S.briefing(data, E1, P(age=30), None, REL)
    opened = sorted(x["열린상대수"] for x in cells)
    assert lines[0]["값"]["열린상대수분포"] == {"최소": opened[0], "중앙": S.spread(opened)["중앙"], "최대": opened[-1]}
    ra = lines[3]
    held = sorted(r["보유수"] for r in ra["값"]["상대보유"])
    assert ra["값"]["상대회사수"] == 5 and ra["값"]["상대보유분포"]["최소"] == held[0]
    assert ra["틀"][1] == "라_보유_상대많음"
    assert ra["문장"].endswith(f"타사 5개사의 보유 담보는 {ra['값']['상대보유요약']}입니다.")
    assert ra["값"]["상대보유요약"] in (f"{held[0]}~{held[-1]}개(중앙값 {S.spread(held)['중앙']}개)", f"모두 {held[0]}개")
    assert S.spread([1, 2, 3, 10]) == {"최소": 1, "중앙": 2.5, "최대": 10} and S.spread([]) is None


def test_export_with_five_peers_passes_the_forbidden_word_check(data):
    out = S.export(data, None, REL)
    assert forbidden_hits(data, out) == []
    for m in out["지도"].values():
        for line in m["칸"]:
            for c in line:
                assert set(S.PEER_TALLY) <= set(c)
                assert len(c["열린상대코드"]) == c["열린상대수"] and len(c["닫힌상대코드"]) == c["닫힌상대수"]
                assert len(c["모르는상대코드"]) == c["모르는상대수"] and len(c["관문만열린상대코드"]) == c["관문만열린상대수"]
    for p in out["포인트"].values():
        assert p["관련기관코드"] == sorted({out["종형"][v]["기관코드"] for v in p["비교종형ID"]} - {"EPOST"})
    b = out["기준별"][E1]
    assert b["범위"]["업권별"] == {"생명보험": 3, "손해보험": 2}
    assert out["종형"][L1]["회사"] == "가상생명 01"
    # 일반심사 기준 종형도 상대 다섯 곳으로 같은 규칙을 탄다
    assert out["기준별"][EG]["범위"]["문장"].startswith("비교한 상품은 ")
