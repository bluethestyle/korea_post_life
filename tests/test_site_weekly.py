"""화면 1 "이번 주 달라진 점"(src/postlife/site/weekly.py)의 시험.

가짜 자료는 test_site.py의 것을 쓴다. 지난주 사본은 아직 없으므로 가짜 자료를 고쳐 지어낸다.
- 정정: 개정판ID는 그대로이고 민영사 급부 값만 다르다 → 화면 1에 싣지 않고 건수만 센다(화면 6)
- 개정: 민영사 종형의 개정판ID(와 종형ID)가 다르고 종형계보키는 같다 → 화면 1에 싣는다
"""
import copy
import json
import subprocess
import sys
from datetime import datetime

import pytest

from postlife.site import build, overview, weekly
from postlife.site.model import Data
from postlife.snapshot import KST, write_snapshot
from test_site import NEW_A, NEW_B, OLD_A, PRIV, ROOT, fake_tables, log, row

NOW = "2026-11-18T17:00:00+09:00"
PREV = "2026-11-11T17:00:00+09:00"


def make(tables=None, at=NOW):
    return Data(tables if tables is not None else fake_tables(), {"snapshot_at": at})


# ---------- 이번 주 ----------
@pytest.mark.parametrize("stamp, week, monday, sunday, today", [
    ("2026-11-19T12:55:15+09:00", "2026-W47", "2026-11-16", "2026-11-22", "2026-11-19"),
    ("2026-11-15T15:30:00+00:00", "2026-W47", "2026-11-16", "2026-11-22", "2026-11-16"),   # UTC로는 일요일, 서울은 월요일
    ("2026-11-22T23:59:59+09:00", "2026-W47", "2026-11-16", "2026-11-22", "2026-11-22"),
    ("2026-11-22T15:00:00+00:00", "2026-W48", "2026-11-23", "2026-11-29", "2026-11-23"),
    ("2027-01-01T09:00:00+09:00", "2026-W53", "2026-12-28", "2027-01-03", "2027-01-01"),   # 해가 바뀌어도 ISO 주를 따른다
    ("2026-12-31T20:00:00-05:00", "2026-W53", "2026-12-28", "2027-01-03", "2027-01-01"),
    ("2026-11-19T08:00:00", "2026-W47", "2026-11-16", "2026-11-22", "2026-11-19"),         # 시간대가 없으면 서울 시간
])
def test_이번_주는_자료_기준_시각을_서울_시간으로_본_ISO_주다(stamp, week, monday, sunday, today):
    assert weekly.week_of(stamp) == {"id": week, "from": monday, "to": sunday, "today": today}


def test_자료_기준_시각이_없으면_이번_주도_없다():
    assert weekly.week_of(None) is None and weekly.week_of("") is None and weekly.week_of("어제") is None
    s1 = overview.build(Data(fake_tables(), {}))
    assert s1["week"] is None and s1["revisions"]["thisWeek"] == [] and s1["news"]["thisWeek"]["total"] == 0


# ---------- 개정판 ----------
def test_개정판은_개정판ID로_묶고_시작과_종료를_나눈다():
    rv = weekly.revision_events(make(at="2026-06-18T10:00:00+09:00"), weekly.week_of("2026-06-18T10:00:00+09:00"))
    assert [(e["rev"], e["kind"], e["date"], e["variants"]) for e in rv["thisWeek"]] == [
        ("EPOST_X_2606", "start", "2026-06-17", [NEW_A, NEW_B]),      # 종형 둘이 한 개정판으로 묶인다
        ("EPOST_X_2504", "end", "2026-06-16", [OLD_A]),
    ]
    assert rv["latest"] is None and rv["thisWeek"][0]["orgName"] == "우체국보험"


def test_이번_주_개정판이_없으면_가장_최근_한_건을_준다():
    data = make()
    rv = weekly.revision_events(data, weekly.week_of(NOW))
    assert rv["thisWeek"] == []
    assert (rv["latest"]["rev"], rv["latest"]["kind"], rv["latest"]["date"], rv["latest"]["variants"]) == (
        "HANWHA_Y_2610", "start", "2026-10-01", [PRIV])


def test_이번_주보다_뒤에_시작하는_개정판은_가장_최근_것이_아니다():
    rv = weekly.revision_events(make(), weekly.week_of("2026-09-01T09:00:00+09:00"))
    assert rv["latest"]["rev"] == "EPOST_X_2606" and rv["latest"]["date"] == "2026-06-17"


# ---------- 시장 소식 ----------
def trend(tid, week, published, prob, summary="소식"):
    return row("sys_시장동향", 동향ID=tid, 수집주차=week, 발표일자=published, 기관코드="MERITZ", 분류유형="신담보출시",
               핵심요약=summary, 매체명="시험매체", 출처URL=f"https://example.invalid/{tid}", 수집경로="검색", 판정확률=prob)


def news_tables():
    tables = fake_tables()       # TRD_1(W47, 0.9), TRD_2(W47, 0.5). 통과 기준 0.7
    tables["sys_시장동향"] += [trend("TRD_3", "2026-W47", "2026-11-11", None), trend("TRD_4", "2026-W46", "2026-11-03", 0.95)]
    return tables


def test_소식은_판정확률이_있고_통과_기준_이상인_것만_싣는다():
    data = make(news_tables())
    news = weekly.news(data, weekly.week_of(NOW))
    assert [n["id"] for n in news["items"]] == ["TRD_1"]
    assert news["week"] == "2026-W47" and news["fallback"] is False and news["threshold"] == 0.7
    assert news["thisWeek"] == {"total": 3, "passed": 1, "below": 1, "undecided": 1}   # 미판정 소식은 건수로만
    item = news["items"][0]
    assert (item["orgName"], item["kind"], item["date"], item["media"], item["via"], item["url"]) == (
        "메리츠화재", "신담보출시", "2026-11-12", None, "검색", "https://example.invalid/a")
    trends = overview.build(data)["trends"]
    assert trends["total"] == 4 and trends["shown"] == 2 and trends["undecided"] == 1       # 판정확률이 없는 소식은 통과시키지 않는다


def test_이번_주차_소식이_없으면_가장_최근_수집주차를_참고로_싣는다():
    news = weekly.news(make(news_tables(), "2026-11-25T09:00:00+09:00"), weekly.week_of("2026-11-25T09:00:00+09:00"))
    assert news["week"] == "2026-W47" and news["fallback"] is True and [n["id"] for n in news["items"]] == ["TRD_1"]
    assert news["thisWeek"] == {"total": 0, "passed": 0, "below": 0, "undecided": 0}


def test_이번_주차에_미판정_소식만_있으면_건수를_적고_지난_주차를_참고로_싣는다():
    tables = news_tables()
    tables["sys_시장동향"].append(trend("TRD_5", "2026-W48", "2026-11-24", None))
    news = weekly.news(make(tables, "2026-11-25T09:00:00+09:00"), weekly.week_of("2026-11-25T09:00:00+09:00"))
    assert news["fallback"] is True and news["week"] == "2026-W47"
    assert news["thisWeek"] == {"total": 1, "passed": 0, "below": 0, "undecided": 1}


def odd_week_tables():
    """수집주차가 비었거나(None, "") 한 자리 주차("2026-W5")로 적힌 통과 소식을 더한다."""
    tables = news_tables()       # 통과 소식: TRD_1(W47), TRD_4(W46)
    tables["sys_시장동향"] += [trend("TRD_6", None, "2026-11-01", 0.95), trend("TRD_7", "", "2026-11-02", 0.95),
                             trend("TRD_8", "2026-W5", "2026-01-28", 0.95)]
    return tables


def test_자료_기준_시각이_없으면_가장_최근_수집주차를_싣되_이번_주차에_없어서라고_하지_않는다():
    news = weekly.news(make(odd_week_tables(), None), None)
    assert news["week"] == "2026-W47" and [n["id"] for n in news["items"]] == ["TRD_1"]
    assert news["fallback"] is False                    # 이번 주차를 정하지 못했으니 "이번 주차에 없어서"가 아니다


@pytest.mark.parametrize("at, week, ids, fallback", [
    ("2026-12-23T09:00:00+09:00", "2026-W47", ["TRD_1"], True),     # 문자 순서로는 "2026-W5"가 "2026-W47"보다 뒤다
    ("2026-11-04T09:00:00+09:00", "2026-W05", ["TRD_8"], True),     # 빈 수집주차는 주차로 싣지 않는다
    ("2026-01-28T09:00:00+09:00", "2026-W05", ["TRD_8"], False),    # 한 자리 주차도 같은 주차다
])
def test_수집주차는_형식을_확인하고_주차_순서로_견준다(at, week, ids, fallback):
    news = weekly.news(make(odd_week_tables(), at), weekly.week_of(at))
    assert (news["week"], [n["id"] for n in news["items"]], news["fallback"]) == (week, ids, fallback)


def test_통과_기준이_없으면_어떤_소식도_싣지_않는다():
    tables = news_tables()
    tables["hum_기준값"] = [r for r in tables["hum_기준값"] if r["기준키"] != "기사선별_통과"]
    news = weekly.news(make(tables), weekly.week_of(NOW))
    assert news["items"] == [] and news["week"] is None and news["fallback"] is False
    assert news["thisWeek"]["below"] == 2 and news["thisWeek"]["undecided"] == 1


# ---------- 대표 조건의 우열 변화 ----------
def rep_tables():
    tables = fake_tables()
    tables["hum_기준값"] += [
        row("hum_기준값", 기준키="REP_WEEKLY_SEX_2", 기준분류="대표조건", 기준명="대표 성별 2", 문자값="F", 적용시작일="2026-11-18"),
        row("hum_기준값", 기준키="REP_WEEKLY_UW_1", 기준분류="대표조건", 기준명="대표 심사유형 1", 문자값="일반심사", 적용시작일="2026-11-18"),
    ]
    return tables


def with_private_pay(tables, pay):
    out = copy.deepcopy(tables)
    for b in out["sys_급부"]:
        if b["급부ID"] == f"{PRIV}_Tpc_Bca":
            b["기준지급금액만원"] = pay
    return out


def revised_private(tables):
    """민영사 종형이 다른 개정판이던 지난주: 종형ID와 개정판ID가 다르고 종형계보키는 같다."""
    text = json.dumps(tables, ensure_ascii=False)
    text = text.replace(PRIV, "HANWHALIFE_H0_eeeeee").replace("HANWHA_Y_2610", "HANWHA_Y_2604")
    return json.loads(text)


def test_지난주_사본이_없으면_비교하지_않고_대표_조건만_적는다():
    sh = weekly.shifts(make(rep_tables()), None)
    assert sh["available"] is False and sh["changes"] == [] and sh["corrections"] == 0
    assert sh["rep"] == {"age": 50, "sexes": ["M", "F"],
                         "uws": [{"spec": "일반심사", "label": "일반심사"}, {"spec": "325", "label": "간편심사 325"}]}


def test_대표_조건의_판정은_우체국_기준_종형과_심사_유형이_같은_다른_회사_종형끼리다():
    data = make(rep_tables())
    found = weekly.rep_verdicts(data, weekly.rep_conditions(data))
    pairs = {(v["base"], v["peer"]) for v in found.values()}
    assert pairs == {(NEW_B, PRIV)}                     # 일반심사끼리. 간편 325에는 민영사 종형이 없고, 판매가 끝난 종형은 뺀다
    assert found[("일반심사", data.variants[NEW_B]["종형계보키"], data.variants[PRIV]["종형계보키"], "STD_CA_DX_GENERAL", "M")]["code"][0] == "b"


def with_future_private(tables, start="2027-01-01"):
    """민영사 종형의 다음 개정판이 미리 들어와 있다: 종형계보키는 같고 적용시작일이 자료 기준일 뒤이며 급부 값이 다르다."""
    out = copy.deepcopy(tables)
    future = "HANWHALIFE_H9_ffffff"
    extra = json.loads(json.dumps({k: [r for r in out[k] if PRIV in json.dumps(r, ensure_ascii=False)]
                                   for k in ("sys_상품종형", "sys_특약", "sys_급부", "hum_담보매핑", "sys_가입조건")},
                                  ensure_ascii=False).replace(PRIV, future).replace("HANWHA_Y_2610", "HANWHA_Y_2701"))
    for v in extra["sys_상품종형"]:
        v["적용시작일"], v["판매종료일"] = start, None
    for b in extra["sys_급부"]:
        b["기준지급금액만원"] = 100
    for k, rows in extra.items():
        out[k] += rows
    return out, future


def test_적용_전인_개정판은_우열_비교에_넣지_않는다():
    data = make(with_future_private(rep_tables())[0])
    found = weekly.rep_verdicts(data, weekly.rep_conditions(data))
    key = ("일반심사", data.variants[NEW_B]["종형계보키"], data.variants[PRIV]["종형계보키"], "STD_CA_DX_GENERAL", "M")
    assert found[key]["peer"] == PRIV and found[key]["code"][0] == "b"      # 지금 판매 중인 개정판과 견준다


def ending_private(tables, end="2026-12-31"):
    """민영사 종형의 판매 종료 예정일이 적혀 있다. 자료 기준일(2026-11-18)에는 아직 판매 중이다."""
    out = copy.deepcopy(tables)
    for v in out["sys_상품종형"]:
        if v["종형ID"] == PRIV:
            v["판매종료일"] = end
    return out


def test_판매_중은_적용이_시작됐고_판매종료일이_지나지_않은_종형이다():
    tables, future = with_future_private(ending_private(fake_tables()))
    data = make(tables)
    on = {vid for vid, v in data.variants.items() if weekly.on_sale(v, "2026-11-18")}
    assert on == {NEW_A, NEW_B, PRIV}                                        # 판매가 끝난 OLD_A, 적용 전인 future는 뺀다
    assert weekly.on_sale(data.variants[PRIV], "2026-12-31") and not weekly.on_sale(data.variants[PRIV], "2027-01-01")
    assert weekly.on_sale(data.variants[future], "2027-01-01")
    # 화면 1의 판매 중 종형 수도 같은 기준으로 센다(판매 종료 예정인 종형은 넣고, 적용 전인 종형은 뺀다)
    assert overview.build(make(ending_private(fake_tables())))["counts"]["onSale"] == 3
    assert overview.build(make(with_future_private(fake_tables())[0]))["counts"]["onSale"] == 3
    # 자료 기준 시각이 없으면 날짜를 견줄 수 없어 판매종료일이 비어 있는 종형만 판매 중으로 센다
    assert overview.build(Data(tables, {}))["counts"]["onSale"] == 3          # NEW_A, NEW_B, future


def test_개정판이_그대로인데_판정이_바뀐_것은_정정으로_건수만_센다():
    now = rep_tables()
    sh = weekly.shifts(make(now), make(with_private_pay(now, 100), "2026-11-11T17:00:00+09:00"))
    assert sh["available"] is True and sh["changes"] == [] and sh["corrections"] == 1   # 남녀 두 조건이 한 건으로 묶인다
    assert sh["pairs"] == 1 and sh["previousAt"] == "2026-11-11T17:00:00+09:00"


def test_개정판이_바뀌어_판정이_바뀐_것은_화면1에_싣는다():
    now = rep_tables()
    before = revised_private(with_private_pay(now, 100))
    sh = weekly.shifts(make(now), make(before, "2026-11-11T17:00:00+09:00"))
    assert sh["corrections"] == 0 and len(sh["changes"]) == 1
    change = sh["changes"][0]
    assert (change["std"], change["uw"], change["sexes"], change["base"], change["peer"]) == (
        "STD_CA_DX_GENERAL", "일반심사", ["M", "F"], NEW_B, PRIV)
    assert change["before"][0] == "m" and change["after"][0] == "b"
    assert change["peerRevised"] is True and change["baseRevised"] is False
    assert change["prev"]["peer"]["rev"] == "HANWHA_Y_2604"


def with_base_revision(tables, cancer_pay=None):
    """우체국 2종이 다른 개정판이던 지난주. cancer_pay를 주면 그 판의 암진단 급부 값도 달랐다."""
    out = copy.deepcopy(tables)
    for v in out["sys_상품종형"]:
        if v["종형ID"] == NEW_B:
            v["개정판ID"] = "EPOST_X_2512"
    for b in out["sys_급부"]:
        if cancer_pay is not None and b["급부ID"] == f"{NEW_B}_Tcancer_Bca":
            b["기준지급금액만원"] = cancer_pay
    return out


def test_개정판이_바뀐_쪽의_그_담보_값이_그대로면_개정이_아니라_정정이다():
    now = rep_tables()
    # 기준 종형은 개정판만 바뀌고 암진단 값은 같다. 같은 주에 비교 종형의 값을 같은 개정판 안에서 고쳤다
    sh = weekly.shifts(make(now), make(with_base_revision(with_private_pay(now, 100)), PREV))
    assert sh["changes"] == [] and sh["corrections"] == 1 and sh["resolved"] == 0
    # 기준 종형 개정판에서 그 담보 값이 실제로 달라졌으면 개정 변화로 싣는다
    sh = weekly.shifts(make(now), make(with_base_revision(now, cancer_pay=2000), PREV))
    assert sh["corrections"] == 0 and len(sh["changes"]) == 1
    change = sh["changes"][0]
    assert (change["std"], change["baseRevised"], change["peerRevised"]) == ("STD_CA_DX_GENERAL", True, False)
    # 두 쪽 다 개정판이 바뀌었어도 값이 달라진 쪽만 까닭으로 적는다
    sh = weekly.shifts(make(now), make(revised_private(with_base_revision(with_private_pay(now, 100))), PREV))
    assert len(sh["changes"]) == 1 and (sh["changes"][0]["baseRevised"], sh["changes"][0]["peerRevised"]) == (False, True)


def pending_private(tables):
    """지난주에는 민영사 암진단 급부의 지급액이 사람 검토 대기였다."""
    out = copy.deepcopy(tables)
    out["sys_작업로그"].append(log(99, "2026-11-10T10:00:00+09:00", "사람검토이관", "sys_급부", f"{PRIV}_Tpc_Bca", "보류",
                                 "기준지급금액만원", 0.5, "gemini-decision-1"))
    return out


def waiting_private(tables):
    """지난주에는 민영사 암진단 급부의 표준담보 매핑이 검토 대기였다."""
    out = copy.deepcopy(tables)
    for m in out["hum_담보매핑"]:
        if m["급부ID"] == f"{PRIV}_Tpc_Bca":
            m.update(검토상태="대기", 확정표준담보ID=None, 추천표준담보ID="STD_CA_DX_GENERAL")
    return out


@pytest.mark.parametrize("before, code", [(pending_private, "p"), (waiting_private, "q"),
                                          (lambda t: revised_private(pending_private(t)), "p")])
def test_검토가_끝나_판정이_생긴_것은_개정도_정정도_아니다(before, code):
    now = rep_tables()
    old = make(before(now), PREV)
    key = ("일반심사", old.variants[NEW_B]["종형계보키"], data_line(old), "STD_CA_DX_GENERAL", "M")
    assert weekly.rep_verdicts(old, weekly.rep_conditions(old))[key]["code"] == code
    sh = weekly.shifts(make(now), old)
    assert sh["changes"] == [] and sh["corrections"] == 0 and sh["resolved"] == 1     # 남녀 두 조건이 한 건으로 묶인다


def data_line(data):
    return next(v["종형계보키"] for v in data.variants.values() if v["기관코드"] == "HANWHALIFE")


def test_판정이_그대로면_아무것도_싣지_않고_새로_생긴_짝은_따로_센다():
    now = rep_tables()
    assert weekly.shifts(make(now), make(now))["changes"] == [] and weekly.shifts(make(now), make(now))["corrections"] == 0
    before = copy.deepcopy(now)
    before["sys_상품종형"] = [v for v in before["sys_상품종형"] if v["종형ID"] != PRIV]
    sh = weekly.shifts(make(now), make(before))
    assert sh["pairs"] == 0 and sh["newPairs"] == 1 and sh["changes"] == [] and sh["corrections"] == 0


def test_지난주_사본_폴더를_주면_빌드가_우열_변화를_싣는다(tmp_path):
    now = rep_tables()
    write_snapshot(now, tmp_path / "now", datetime(2026, 11, 18, 17, tzinfo=KST))
    write_snapshot(revised_private(with_private_pay(now, 100)), tmp_path / "before", datetime(2026, 11, 11, 17, tzinfo=KST))
    info = build.build_site(tmp_path / "now", tmp_path / "site.html", previous_dir=tmp_path / "before")
    payload = build.read_payload((tmp_path / "site.html").read_text(encoding="utf-8"))
    assert info["previous_at"] == "2026-11-11T17:00:00+09:00"
    assert payload["s1"]["shifts"]["available"] is True and len(payload["s1"]["shifts"]["changes"]) == 1
    with pytest.raises(FileNotFoundError):
        build.build_site(tmp_path / "now", tmp_path / "x.html", previous_dir=tmp_path / "없는 폴더")
    # 명령줄: --previous를 받고, 주지 않으면 비교하지 않았다고 적는다
    script = ROOT / "scripts" / "build_site.py"
    done = subprocess.run([sys.executable, str(script), "--snapshot", str(tmp_path / "now"), "--out", str(tmp_path / "a.html"),
                           "--previous", str(tmp_path / "before")], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert done.returncode == 0 and "지난주 사본: " in done.stdout and "2026-11-11T17:00:00+09:00" in done.stdout, done.stderr
    done = subprocess.run([sys.executable, str(script), "--snapshot", str(tmp_path / "now"), "--out", str(tmp_path / "b.html")],
                          capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert done.returncode == 0 and "지난주 사본: 없음" in done.stdout and "경고:" not in done.stdout, done.stderr
