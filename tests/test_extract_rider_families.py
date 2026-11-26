"""한 특약을 갱신형과 비갱신형 두 가지로 파는 문서(우체국하나로OK보험 2609 형식)의 가입조건을 종형에 맞게 싣는지.

- 가입한도 표는 두 가지를 묶은 이름 하나("무배당 가나특약 2609")로 적는다. 두 특약 모두의 한도로 싣는다(Target.members).
- 주계약 보험기간 칸이 "종신, 90세,100세만기"처럼 단위의 앞부분만 적은 조각을 섞어 쓴다(expand).
- 종형명은 "1종(일반가입)[표준형, 종신]"처럼 종 표기 뒤에 대괄호 표시를 붙이고, 표는 "1종(일반가입)"으로만 가른다(_applies).
글자는 형식만 본떴고 특약명과 금액은 지어낸 것이다.
"""
from postlife import ids
from postlife.extract import conditions as C

RENEW = "무배당 가나특약(20년갱신형) 2609"
PLAIN = "무배당 가나특약N(비갱신형) 2609"
SOLO = "무배당 다라특약(10년갱신형) 2609"
NAMES = ["1종(일반가입)[표준형, 종신]", "2종(간편가입)[표준형, 종신]", "1종(일반가입)[해약환급금50%지급형, 90,100세]",
         "2종(간편가입)[해약환급금50%지급형, 90,100세]"]


def _rows(vid: str, names: list[str]) -> list[dict]:
    main = {"특약ID": ids.rider_id(vid, "주계약"), "종형ID": vid, "특약계보키": ids.rider_lineage_key("주계약"),
            "담보구분": "주계약", "원시특약명": "주계약 (보험가입금액 1,000만원 기준)"}
    return [main] + [{"특약ID": ids.rider_id(vid, n), "종형ID": vid, "특약계보키": ids.rider_lineage_key(n),
                      "담보구분": "선택특약", "원시특약명": n} for n in names]


def _targets(names=(RENEW, PLAIN, SOLO)) -> list[C.Target]:
    rows = [r for i in range(len(NAMES)) for r in _rows(f"V{i}", list(names))]
    return [C.target_of(f"V{i}", n, rows) for i, n in enumerate(NAMES)]


def test_expand_fills_the_rest_of_the_unit():
    assert C.expand("종신, 90세,100세만기") == ["종신", "90세만기", "100세만기"]
    assert C.expand("10년,20년만기(갱신형)") == ["10년만기(갱신형)", "20년만기(갱신형)"]
    # 이미 단위를 다 적은 조각과 숫자만 적은 조각은 지금과 같다
    assert C.expand("종신, 90세만기") == ["종신", "90세만기"] and C.expand("90,100세만기") == ["90세만기", "100세만기"]
    assert C.expand("10년납, 15년납, 20년납, 30년납, 80세납") == ["10년납", "15년납", "20년납", "30년납", "80세납"]
    assert C.expand("80세납,90세만기") == ["80세납", "90세만기"]


def test_members_finds_both_renewal_kinds_of_one_rider():
    t = _targets()[0]
    both = (ids.rider_id("V0", RENEW), ids.rider_id("V0", PLAIN))
    assert t.rider("무배당 가나특약 2609") == (False, None)
    assert set(t.members("무배당 가나특약 2609")) == set(both) and set(t.members("(무)가나특약 2609")) == set(both)
    # 갱신 표시가 붙은 특약이 하나뿐인 이름, 없는 이름은 묶지 않는다
    assert t.members("무배당 다라특약 2609") == () and t.members("무배당 마바특약 2609") == ()


def test_exact_name_wins_over_family():
    """묶은 이름과 같은 이름의 특약이 따로 있으면 그 특약 하나로 찾는다(rider가 먼저다)."""
    bare = "무배당 가나특약 2609"
    t = _targets((RENEW, PLAIN, bare))[0]
    assert t.rider(bare) == (True, ids.rider_id("V0", bare))
    built = C.build_rows([t], [], [C.LimitItem([bare], "", "500만원", "1,000만원", "")], [])
    assert built.amounts == {ids.rider_id("V0", bare): (500.0, 1000.0)}


def test_family_limit_rows_and_constraints():
    targets = _targets()
    ages = [C.AgeItem([RENEW], "2종(간편가입)", "최초계약", "", "20~70세", "20년", "전기납"),
            C.AgeItem([PLAIN], "2종(간편가입)", "최초계약", "", "20~70세", "90,100세만기", "20년납")]
    limits = [C.LimitItem(["무배당 가나특약 2609"], "65세 이하", "500만원", "2,000만원", "", "2종(간편가입)"),
              C.LimitItem(["무배당 가나특약 2609"], "66세 이상", "500만원", "1,000만원", "", "2종(간편가입)"),
              C.LimitItem(["무배당 가나특약 2609"], "", "500만원", "2,000만원", "", "1종(일반가입)")]
    rules = [C.ConstraintItem("주계약", ["무배당 가나특약 2609"], "최대연동", "주계약 보험가입금액 이내에서", "주계약 보험가입금액 이내에서")]
    built = C.build_rows(targets, ages, limits, rules)
    for i, t in enumerate(targets):
        both = {ids.rider_id(t.variant_id, RENEW), ids.rider_id(t.variant_id, PLAIN)}
        mine = [r for r in built.conditions if r["종형ID"] == t.variant_id]
        assert {rid: built.amounts[rid] for rid in both} == {rid: (500.0, 2000.0) for rid in both}
        assert {c["대상특약ID"] for c in built.constraints if c["종형ID"] == t.variant_id} == both
        if NAMES[i].startswith("2종"):
            # 2종 가입나이 줄은 한도가 바뀌는 66세에서 나뉘고, 두 특약 모두 구간 한도를 갖는다
            got = sorted((r["특약ID"] == ids.rider_id(t.variant_id, RENEW), r["최저가입나이"], r["최고가입나이"],
                          r["구간최대가입금액만원"]) for r in mine)
            # 비갱신형은 90세만기, 100세만기 두 줄씩이다
            assert got == sorted([(True, 20, 65, 2000.0), (True, 66, 70, 1000.0)]
                                 + [(False, 20, 65, 2000.0), (False, 66, 70, 1000.0)] * 2)
        else:
            assert mine == []           # 가입나이 줄이 2종에만 있다
    assert not [n for n in built.notes if "가나특약 2609" in n]


def test_bracket_marks_on_variant_names():
    """종형명 끝의 대괄호 표시(환급유형, 보험기간)는 떼고 표의 종 구분과 견준다."""
    targets = _targets()
    assert [C._applies("1종(일반가입)", t, targets) for t in targets] == [True, False, True, False]
    assert [C._applies("2종(간편가입) 66세 이상", t, targets) for t in targets] == [False, True, False, True]
    assert [C._applies("1종(일반가입), 2종(간편가입)", t, targets) for t in targets] == [True] * 4
    assert [C._applies("종신", t, targets) for t in targets] == [None] * 4
    marked = f"{RENEW} [1종(일반가입), 2종(간편가입)]"
    assert [t.rider(marked) for t in targets] == [(True, ids.rider_id(t.variant_id, RENEW)) for t in targets]
