"""판단 화면을 지어낸 자료로 만들어 브라우저로 열고, 화면(app.js)이 쓰는 글이 자료와 서로 맞는지 본다.

자료 가공은 test_site.py와 test_site_weekly.py가 보고, 여기서는 화면이 그 자료로 세고 적는 글을 본다.
scripts/dev/check_site_browser.py처럼 만든 HTML을 file://로 열고 바깥 요청을 막는다. playwright나 chromium이 없으면 건너뛴다.
"""
import ast
import copy
import re

import pytest

from postlife.site import build
from postlife.site.model import BASIS_COLUMN, RATIO_BASIS, Data, load
from test_site import (NEW_A, NEW_B, PRIV, ROOT, SF, SF_OLD, SNAPSHOT, benefit, condition, fake_tables, mapped,
                       no_limit_tables, ratio_revision_tables, ratio_tables, rider, variant)
from test_site_weekly import PREV, pending_private, rep_tables

sync_api = pytest.importorskip("playwright.sync_api")

NOW = {"snapshot_at": "2026-11-18T17:00:00+09:00"}
MERITZ = "MERITZ_M1_gggggg"
# 펼치기 전 화면 높이 한도는 브라우저 점검 스크립트의 값을 그대로 읽는다(한 곳에서만 정한다)
LIMIT = ast.literal_eval(re.search(r"^LIMIT = (\{.*?\})", (ROOT / "scripts/dev/check_site_browser.py").read_text(encoding="utf-8"),
                                   re.M).group(1))
# 화면 4 결과를 접을 때 남기는 양(표의 줄 수, 급부유형마다 막대 수)도 화면 코드의 값을 그대로 읽는다
PREVIEW = {name: int(value) for name, value in re.findall(r"const (PREVIEW_\w+) = (\d+);",
                                                         (ROOT / "src/postlife/site/assets/app.js").read_text(encoding="utf-8"))}


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            chromium = p.chromium.launch()
        except Exception as error:          # 브라우저 파일이 없는 환경
            pytest.skip(f"chromium을 띄우지 못함: {error}")
        yield chromium
        chromium.close()


@pytest.fixture()
def site(browser, tmp_path):
    """site(tables, meta, previous, width)는 그 자료로 만든 화면을 그 폭으로 연 page를 돌려준다.
    콘솔 오류가 하나라도 나면 시험이 끝날 때 실패한다."""
    opened = []

    def open_site(tables, meta=NOW, previous=None, width=1280):
        path = tmp_path / f"site{len(opened)}.html"
        path.write_text(build.render(Data(tables, meta), previous), encoding="utf-8")
        context = browser.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1, offline=True)
        page = context.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(path.as_uri())
        opened.append((context, errors))
        return page

    yield open_site
    for context, _ in opened:
        context.close()
    assert [e for _, errors in opened for e in errors] == []


def heads(page):
    """해설 맨 앞 줄(결론, 결론을 채우지 못했으면 대신 쓴 안내)."""
    return page.locator("#main .comment > p").all_inner_texts()


def comment(page, sid):
    """해설을 펼쳐 {항목 이름: 글}로 읽는다."""
    page.click(f'[data-key="fold-cm-{sid}"]')
    dl = page.locator("#main .comment details.fold[open] dl.kv")
    return dict(zip(dl.locator("dt").all_inner_texts(), dl.locator("dd").all_inner_texts()))


def without_caps(tables, vid):
    """그 종형의 특약 가입 한도와 가입 나이 자료를 비운다(공시 문서에 한도가 없는 꼴)."""
    out = copy.deepcopy(tables)
    for r in out["sys_특약"]:
        if r["종형ID"] == vid:
            r["최소가입금액만원"] = r["최대가입금액만원"] = None
    out["sys_가입조건"] = [r for r in out["sys_가입조건"] if r["종형ID"] != vid]
    return out


def with_private_stroke(tables):
    """민영사 종형에만 있는 담보(뇌졸중 진단비)를 더한다."""
    out = copy.deepcopy(tables)
    out["sys_특약"].append(rider(PRIV, "st", "뇌졸중진단특약", 500, 3000))
    b = benefit(PRIV, "st", "st", "뇌졸중진단비", "주급부", 1000, 90)
    out["sys_급부"].append(b)
    out["hum_담보매핑"].append(mapped(b["급부ID"], "자동확정", "STD_BR_DX_STROKE"))
    return out


def with_capped_private(tables):
    """가입 한도가 공시된 민영사 종형(메리츠)을 더한다. 우체국 2종과 심사 유형이 같고, 회사 순서로는 한화 뒤다."""
    out = copy.deepcopy(tables)
    out["sys_상품종형"].append(variant(MERITZ, "MERITZ", "MERITZ_Q_2609", "MERITZ_Q|일반심사|일반|갱신|표준형", "메리츠 시험보험", "1종",
                                     "정밀비교", "일반심사", "일반", (None, None, None, None, None), "2026-09-01", None, "hm", "mm"))
    out["sys_특약"] += [rider(MERITZ, "main", "주계약", 1000, 5000, "주계약"), rider(MERITZ, "pc", "암진단특약", 500, 3000)]
    b = benefit(MERITZ, "pc", "ca", "암진단비", "주급부", 1000, 90)
    out["sys_급부"].append(b)
    out["hum_담보매핑"].append(mapped(b["급부ID"], "자동확정", "STD_CA_DX_GENERAL"))
    return out


# ---------- 응대 카드 ----------
def open_card(page, age, peer):
    page.click("#tab-s3")
    page.fill("#age", str(age))
    box = page.locator(f'[data-key="s3-col-{peer}"]')
    if not box.is_checked():        # 처음 열은 회사마다 기준과 맞붙는 종형 하나라, 심사 유형이 다른 비교 종형은 체크로 더한다
        box.check()
    page.click('[data-key="s3-card"]')
    page.wait_for_selector("#card[open] .sheet")
    if page.locator(f'[data-key="card-peer-{peer}"]').count():
        page.click(f'[data-key="card-peer-{peer}"]')
    return page.inner_text("#card-body .sheet")


def test_응대_카드의_판정_집계는_모든_표준담보를_빠짐없이_센다(site):
    page = site(with_private_stroke(fake_tables()))
    for age in (50, 75):        # 50세: 비교 종형에만 있는 담보가 있음, 75세: 비교 종형 주계약에 가입할 수 없는 나이
        open_card(page, age, PRIV)
        tally = page.inner_text("#card-body .sheet .c-tally")
        head, rest = tally.split("기준:")
        total = int(re.search(r"표준담보 (\d+)개", head).group(1))
        assert sum(int(n) for n in re.findall(r"\d+", rest)) == total, tally
        page.click("#card-close")


def test_응대_카드의_한쪽에만_있는_담보는_위쪽_집계와_같은_범위에서_센다(site):
    page = site(with_private_stroke(fake_tables()))
    text = open_card(page, 50, PRIV)                    # 처음 보장 분야는 암보장이다
    tally = page.inner_text("#card-body .sheet .c-tally")
    assert re.search(r"기준 종형에만 있는 담보 (\d+)개", text).group(1) == re.search(r"빈자리 (\d+)", tally).group(1)
    only = re.search(r"비교 종형에만 있음 (\d+)", tally)
    assert re.search(r"비교 종형에만 있는 담보 (\d+)개", text).group(1) == (only.group(1) if only else "0")
    assert "뇌졸중 진단비" in text                        # 뇌혈관보장 담보도 센다


# ---------- 화면 3 ----------
def test_화면3_처음_열은_기준_종형을_바꾸면_다시_정하고_체크로_고친_뒤에는_그대로_둔다(site):
    page = site(fake_tables())
    page.click("#tab-s3")
    checked = lambda: page.eval_on_selector_all('[data-key^="s3-col-"]:checked', "els => els.map(e => e.dataset.key.slice(7))")
    assert checked() == [NEW_A]                                # 기준(간편 3.2.5)과 심사 유형이 같은 한화 종형이 없다
    page.click(f'[data-key="s3-base-{NEW_B}"]')
    assert checked() == [NEW_B, PRIV]                          # 기준 종형을 바꾸면 같은 규칙으로 다시 정한다(일반심사끼리)
    page.check(f'[data-key="s3-col-{NEW_A}"]')
    page.click(f'[data-key="s3-base-{NEW_A}"]')
    assert checked() == [NEW_A, NEW_B, PRIV]                   # 체크로 고친 뒤에는 기준 종형을 바꿔도 그 선택을 둔다
    page.click('[data-key="s3-cols-peers"]')
    assert checked() == [NEW_A]                                # "회사마다 맞붙는 종형만"으로 처음 열로 돌아간다


def test_기준_종형의_가입_한도가_없어_판정하지_않은_담보는_가입_한도_자료_없음으로_적는다(site):
    page = site(without_caps(fake_tables(), NEW_B))
    page.click("#tab-s3")
    page.click(f'[data-key="s3-base-{NEW_B}"]')
    row = page.locator(".sumrow", has_text="민영 시험보험").inner_text()
    assert "가입 한도 자료 없음 1" in row and "금액 자료 없음" not in row, row
    cell = page.inner_text(f'[data-key="c-STD_CA_DX_GENERAL-{PRIV}"]')
    assert "기준 종형 가입 한도 자료 없음" in cell, cell
    page.click('[data-key="s3-card"]')
    page.wait_for_selector("#card[open] .sheet")
    assert "금액 자료가 없어 판정하지 않은 담보" not in page.inner_text("#card-body .sheet")


def test_화면3_해설은_판정할_수_있는_담보가_있는_열과_견주고_그_이름을_적는다(site):
    page = site(with_capped_private(no_limit_tables()))      # 한화는 한도 미공시라 판정 0건, 메리츠는 판정이 있다
    page.click("#tab-s3")
    page.click(f'[data-key="s3-base-{NEW_B}"]')
    found = heads(page)
    assert len(found) == 1 and "메리츠 시험보험" in found[0] and "비교 담보가 없습니다" not in found[0], found
    # 판정할 수 있는 열이 없으면 지금처럼 첫 민영사 열과 견주고, 판정할 담보가 없다는 결론에도 그 종형 이름을 적는다
    page.click(f'[data-key="s3-col-{MERITZ}"]')
    found = heads(page)
    assert len(found) == 1 and "민영 시험보험" in found[0] and "비교 담보가 없습니다" in found[0], found
    page.click('[data-key="s3-card"]')
    page.wait_for_selector("#card[open] .sheet")
    assert "민영 시험보험" in page.inner_text("#card-body .sheet .c-concl")
    page.click("#card-close")
    # 비교 열을 모두 빼도 결론 자리가 비지 않는다
    page.click(f'[data-key="s3-col-{PRIV}"]')
    found = heads(page)
    assert len(found) == 1 and "비교할 종형" in found[0], found


# ---------- 화면 1 ----------
@pytest.mark.parametrize("meta", [{}, {"snapshot_at": "어제"}])
def test_자료_기준_시각이_없어도_화면1_결론이_있고_소식을_이번_주차_탓으로_돌리지_않는다(site, meta):
    page = site(fake_tables(), meta)
    found = heads(page)
    assert len(found) == 1 and "자료 기준 시각이 없어" in found[0], found
    text = page.inner_text("#main")
    assert "이번 주차에는 선별을 통과한 소식이 없어" not in text and "시험 소식" in text


def test_검토가_끝나_판정이_생긴_것은_정정과_따로_적는다(site):
    now = rep_tables()
    page = site(now, previous=Data(pending_private(now), {"snapshot_at": PREV}))
    text = page.inner_text("#main")
    assert "자료 정정이라" not in text and "검토가 끝나 판정이 생긴 1건" in text
    page.click("#tab-s6")
    assert "검토가 끝나 판정이 생김" in page.inner_text("#main .tiles")


# ---------- 화면 2 ----------
def test_화면2는_입원과_수술의_기간_질문이_없는_간편_종형을_0년이나_자료_없음으로_적지_않는다(site):
    # 고지입원수술년수 0은 기간 질문이 없다는 뜻이고(고지수술포함여부도 비어 있다), 빈칸만 자료 없음이다(점검 결함)
    tables = copy.deepcopy(fake_tables())
    zero, blank = "HANWHALIFE_HZ_zzzzzz", "HANWHALIFE_HB_zzzzzz"
    for vid, kind, hosp in ((zero, "간편가입형(0년)", 0), (blank, "간편가입형(빈칸)", None)):
        tables["sys_상품종형"].append(variant(vid, "HANWHALIFE", "HANWHA_Z_2610", f"HANWHA_Z|간편심사|{kind}", "민영 관문 시험보험",
                                         kind, "관문전용", "간편심사", "3.0.5", (3, hosp, 5, None, 7), "2026-10-01", None, "hz", "mz"))
        tables["sys_특약"].append(rider(vid, "main", "주계약", 300, 1000, "주계약"))
        tables["sys_가입조건"].append(condition(vid, None, 15, 80, 1000))
    page = site(tables)
    page.click("#tab-s2")
    page.wait_for_selector("#screen-s2")
    rows = {kind: page.locator("#screen-s2 tr", has_text=kind).first.inner_text() for kind in ("간편가입형(0년)", "간편가입형(빈칸)")}
    assert "입원과 수술의 기간 질문 없음" in rows["간편가입형(0년)"], rows
    assert "0년 이내" not in rows["간편가입형(0년)"] and "자료 없음" not in rows["간편가입형(0년)"], rows
    assert "자료 없음" in rows["간편가입형(빈칸)"] and "기간 질문 없음" not in rows["간편가입형(빈칸)"], rows


# ---------- 화면 4 ----------
def test_화면4_해설은_한도_없는_특약_수가_주계약을_포함한다고_밝힌다(site):
    page = site(no_limit_tables())                     # 한화는 주계약과 특약 모두 한도 자료가 없다
    page.click("#tab-s4")
    page.click('[data-key="s4-variant-org-HANWHALIFE"]')
    page.click('[data-key="s4-max"]')
    total = int(re.search(r"특약 (\d+)개 가운데", heads(page)[0]).group(1))          # 결론의 특약 수는 주계약을 뺀다
    note = comment(page, "s4")["실무 유의점"]
    assert "가입 한도 자료가 없는 특약" not in note                                 # 주계약까지 센 수를 "특약 N개"로 적지 않는다
    no_limit = int(re.search(r"주계약과 특약 가운데 가입 한도 자료가 없는 (\d+)개", note).group(1))
    assert (total, no_limit) == (1, 2)


def test_화면4_해설은_비율_급부_특약에_예시_금액을_넣는다고_적는다(site):
    page = site(ratio_tables())
    page.click("#tab-s4")
    page.click('[data-key="s4-variant-org-SAMSUNGFIRE"]')
    assert "기준 가입금액이 따로 없습니다" in page.inner_text("#main p.notice")
    assert "계산용 예시 금액" in comment(page, "s4")["실무 유의점"]


def test_기준_가입금액이_없는_특약이_섞여도_비율_급부_종형은_예시_금액으로_담는다(site):
    tables = ratio_tables()
    tables["sys_특약"].append(rider(SF, "day", "질병 입원일당", None, None))
    b = benefit(SF, "day", "day", "질병 입원일당", "주급부", None, base=None)      # 급부표에 지급률도 기준 가입금액도 없다
    b[BASIS_COLUMN] = RATIO_BASIS
    tables["sys_급부"].append(b)
    tables["hum_담보매핑"].append(mapped(b["급부ID"], "대상외"))
    page = site(tables)
    page.click("#tab-s4")
    page.click('[data-key="s4-variant-org-SAMSUNGFIRE"]')
    assert page.inner_text('[data-key="s4-max"]') == "예시 금액으로 모두 담기"
    text = page.inner_text("#main")
    assert "급부표의 기준 가입금액으로 담습니다" not in text and "급부표의 기준 가입금액을 넣어 두며" not in text
    assert "기준 가입금액도 없는 특약 1개" in page.inner_text("#main p.notice")


# ---------- 화면 4: 특약이 수백 개인 종형을 모두 담아도 펼치기 전 화면이 한도 안이다 ----------
HANWHA = "HANWHALIFE"
WIDE = "일반가입형"        # 한화 시그니처 H통합보험의 특약이 가장 많은 종형(실제 사본에서 2백 개가 넘는다)


@pytest.fixture(scope="module")
def real():
    return load(SNAPSHOT)


def wide_variant(tables):
    return next(v["종형ID"] for v in tables["sys_상품종형"] if v["기관코드"] == HANWHA and v["종형명"] == WIDE)


def doubled(tables):
    """한화 일반가입형의 특약(주계약 빼고)과 급부, 가입조건, 매핑, 표준담보 사전을 한 벌 더 붙인 지어낸 사본. 특약과 표준담보 줄 수가 두 배가 된다."""
    out = copy.deepcopy(tables)
    vid = wide_variant(out)
    copy_id = lambda value: None if value is None else f"{value}X2"
    riders = [r for r in out["sys_특약"] if r["종형ID"] == vid and r["담보구분"] != "주계약"]
    tids = {r["특약ID"] for r in riders}
    bids = {b["급부ID"] for b in out["sys_급부"] if b["특약ID"] in tids}
    out["hum_표준담보사전"] += [dict(s, 표준담보ID=copy_id(s["표준담보ID"]), 표준담보명=s["표준담보명"] + " 복제")
                           for s in out["hum_표준담보사전"]]
    out["sys_특약"] += [dict(r, 특약ID=copy_id(r["특약ID"]), 특약계보키=copy_id(r["특약계보키"]), 원시특약명=r["원시특약명"] + " 복제")
                      for r in riders]
    out["sys_급부"] += [dict(b, 급부ID=copy_id(b["급부ID"]), 특약ID=copy_id(b["특약ID"])) for b in out["sys_급부"] if b["특약ID"] in tids]
    out["hum_담보매핑"] += [dict(m, 급부ID=copy_id(m["급부ID"]), 확정표준담보ID=copy_id(m.get("확정표준담보ID")),
                             추천표준담보ID=copy_id(m.get("추천표준담보ID"))) for m in out["hum_담보매핑"] if m["급부ID"] in bids]
    out["sys_가입조건"] += [dict(c, 조건행ID=copy_id(c["조건행ID"]), 특약ID=copy_id(c["특약ID"]))
                         for c in out["sys_가입조건"] if c["특약ID"] in tids]
    return out


def fill_wide(page):
    """화면 4에서 한화 일반가입형을 골라 특약을 모두 담는다."""
    page.click("#tab-s4")
    page.click(f'[data-key="s4-variant-org-{HANWHA}"]')
    kinds = page.locator('[data-key^="s4-variant-"]:not([data-key*="-org-"]):not([data-key*="-rev-"])', has_text=WIDE)
    if kinds.count():
        kinds.first.click()
    assert WIDE in page.inner_text(".picked strong")
    page.click('[data-key="s4-max"]')


def s4_totals(page):
    """접든 펼치든 같아야 하는 합계와 핵심 결과: 해설 결론, 구획 제목(특약 수, 표준담보 수), 급부유형별 요약, 유의 문구."""
    screen = "#screen-s4"
    return {"head": heads(page), "blocks": page.locator(f"{screen} section.block > h3").all_inner_texts(),
            "summary": page.locator(f"{screen} .tiles").all_inner_texts(), "notice": page.locator(f"{screen} p.notice").all_inner_texts(),
            "notes": page.locator(f"{screen} p.note").all_inner_texts()}


def std_total(page):
    head = page.locator("#screen-s4 section.block > h3", has_text="표준담보별 실제 지급액").inner_text()
    return int(re.search(r"표준담보 (\d+)개", head).group(1))


def check_folding(page, width):
    """펼치기 전 높이가 한도 안이고, 단추로 펼치면 표준담보가 막대와 표에 모두 보이며, 합계 표시는 접든 펼치든 같은지 본다.
    표준담보 수를 돌려준다."""
    height = page.evaluate("document.documentElement.scrollHeight")
    assert height <= LIMIT[width], f"{width}px 폭에서 펼치기 전 높이 {height}px가 한도 {LIMIT[width]}px를 넘음"
    total = std_total(page)
    folded_rows = page.locator("#s4-pay tbody tr").all_inner_texts()
    assert len(folded_rows) < total and page.locator("#s4-bars .barrow").count() < total, "접어 둘 만큼 줄이 많은데 모두 그림"
    before = s4_totals(page)
    for key in ("s4-more-bars", "s4-more-pay"):
        button = page.locator(f'[data-key="{key}"]')
        assert button.get_attribute("aria-expanded") == "false"
        button.click()
        assert page.get_attribute(f'[data-key="{key}"]', "aria-expanded") == "true"
    rows = page.locator("#s4-pay tbody tr").all_inner_texts()
    names = page.locator("#s4-pay tbody th[scope=row]").all_inner_texts()
    bars = page.locator("#s4-bars .barlabel").all_inner_texts()
    assert len(rows) == total and len(set(names)) == total and sorted(bars) == sorted(names), "펼쳤는데 빠진 표준담보가 있음"
    assert rows[:len(folded_rows)] == folded_rows                           # 접힌 상태는 펼친 표의 앞부분이다
    assert s4_totals(page) == before, "접힌 상태와 펼친 상태의 합계 표시가 다름"
    # 키보드: 단추에 초점을 두고 Enter로 접고 Space로 다시 펼친다. 다시 그려도 초점은 그 단추에 남는다
    more = '[data-key="s4-more-pay"]'
    page.focus(more)
    page.keyboard.press("Enter")
    assert page.get_attribute(more, "aria-expanded") == "false" and page.locator("#s4-pay tbody tr").count() == len(folded_rows)
    assert page.evaluate("() => document.activeElement.dataset.key") == "s4-more-pay"
    page.keyboard.press("Space")
    assert page.get_attribute(more, "aria-expanded") == "true" and page.locator("#s4-pay tbody tr").count() == total
    return total


@pytest.mark.parametrize("width", sorted(LIMIT))
def test_화면4는_특약이_가장_많은_종형을_모두_담아도_펼치기_전_높이가_한도_안이다(site, real, width):
    page = site(real.tables, real.meta, width=width)
    fill_wide(page)
    riders = int(re.search(r"특약 (\d+)개 가운데", page.locator("#screen-s4 section.block > h3").first.inner_text()).group(1))
    assert riders > 200                                                   # 문제가 났던 크기의 종형을 그대로 본다
    check_folding(page, width)


@pytest.mark.parametrize("width", sorted(LIMIT))
def test_화면4는_특약과_표준담보가_두_배인_사본에서도_펼치기_전_높이가_한도_안이다(site, real, width):
    page = site(real.tables, real.meta, width=width)
    fill_wide(page)
    total = std_total(page)
    riders = int(re.search(r"특약 (\d+)개 가운데", page.locator("#screen-s4 section.block > h3").first.inner_text()).group(1))
    page = site(doubled(real.tables), real.meta, width=width)
    fill_wide(page)
    assert int(re.search(r"특약 (\d+)개 가운데", page.locator("#screen-s4 section.block > h3").first.inner_text()).group(1)) == 2 * riders
    # 복제 특약에는 결합 제약을 붙이지 않았으므로 원래 특약보다 더 담길 수는 있어도 덜 담기지는 않는다
    assert check_folding(page, width) >= 2 * total


def more_buttons(page):
    """화면 4 결과의 "모두 보기" 단추: {data-key: aria-expanded}."""
    return dict(page.locator('[data-key^="s4-more-"]').evaluate_all("els => els.map(e => [e.dataset.key, e.getAttribute('aria-expanded')])"))


@pytest.mark.parametrize("width", sorted(LIMIT))
def test_화면4_모두_보기를_누르면_새로_보이는_줄이_단추_아래에_나온다(site, real, width):
    """단추를 화면에 둔 채 누르면, 새로 보이는 막대와 표의 줄이 모두 단추 아래(화면 위쪽 끝보다 아래)에 놓여 위로 올리지 않고 읽어 내려갈 수 있다."""
    page = site(real.tables, real.meta, width=width)
    fill_wide(page)
    for key, items in (("s4-more-bars", "#s4-bars .barlabel"), ("s4-more-pay", "#s4-pay tbody th[scope=row]")):
        button = page.locator(f'[data-key="{key}"]')
        button.scroll_into_view_if_needed()
        before = set(page.locator(items).all_inner_texts())
        button.click()
        top = page.locator(f'[data-key="{key}"]').bounding_box()["y"]
        assert 0 <= top < 900, f"{key}: 누른 단추가 화면 밖({top:.0f}px)으로 밀림"
        tops = page.locator(items).evaluate_all("els => els.map(e => [e.innerText, e.getBoundingClientRect().top])")
        new = [(text, y) for text, y in tops if text not in before]
        assert new, f"{key}: 눌렀는데 새로 보이는 줄이 없음"
        above = [(text, round(y)) for text, y in new if y < top]
        assert not above, f"{width}px {key}: 새로 보이는 줄 {len(above)}개가 단추({top:.0f}px)보다 위에 놓임, 첫 줄 {above[0]}"


def test_화면4는_종형을_바꾸거나_특약을_새로_담으면_결과를_접은_채로_보여_준다(site, real):
    page = site(real.tables, real.meta)
    kinds = '[data-key^="s4-variant-"]:not([data-key*="-org-"]):not([data-key*="-rev-"])'

    def expand():
        for key in list(more_buttons(page)):
            if page.get_attribute(f'[data-key="{key}"]', "aria-expanded") == "false":
                page.click(f'[data-key="{key}"]')
        assert set(more_buttons(page).values()) == {"true"}

    def folded(where):
        buttons = more_buttons(page)
        assert buttons and set(buttons.values()) == {"false"}, f"{where}: 펼친 채로 시작함 {buttons}"
        assert page.locator("#s4-pay tbody tr").count() == PREVIEW["PREVIEW_ROWS"] < std_total(page)

    fill_wide(page)
    expand()
    page.locator(kinds, has_text="간편가입형(1년)").first.click()          # 같은 상품의 다른 종형
    page.click('[data-key="s4-max"]')
    folded("다른 종형으로 바꾼 뒤")
    expand()
    page.click('[data-key="s4-variant-org-EPOST"]')                      # 다른 회사의 종형
    page.click('[data-key="s4-max"]')
    folded("다른 회사로 바꾼 뒤")
    expand()
    page.click('[data-key="s4-clear"]')
    page.click('[data-key="s4-max"]')
    folded("특약을 모두 뺐다가 다시 담은 뒤")
    expand()
    page.click('[data-key="s4-max"]')
    folded("모두 담기를 다시 누른 뒤")
    # 탭을 오가는 것은 조합을 바꾸지 않으므로 다른 접어 두는 구획처럼 펼친 상태를 그대로 둔다
    expand()
    page.click("#tab-s3")
    page.click("#tab-s4")
    assert set(more_buttons(page).values()) == {"true"}


def sparse(tables):
    """한화 일반가입형 급부의 매핑을 한 급부유형의 표준담보 몇 개만 남기고 지운 지어낸 사본.
    표준담보 수는 표를 접는 줄 수보다 적지만, 그 급부유형 하나에는 막대를 접는 수보다 많다."""
    out = copy.deepcopy(tables)
    vid = wide_variant(out)
    tids = {r["특약ID"] for r in out["sys_특약"] if r["종형ID"] == vid}
    bids = {b["급부ID"] for b in out["sys_급부"] if b["특약ID"] in tids}
    kind = {s["표준담보ID"]: s["급부유형"] for s in out["hum_표준담보사전"]}
    rows = [m for m in out["hum_담보매핑"] if m["급부ID"] in bids and m.get("확정표준담보ID") in kind]
    by_kind = {}
    for m in rows:
        by_kind.setdefault(kind[m["확정표준담보ID"]], set()).add(m["확정표준담보ID"])
    keep = set(sorted(max(by_kind.values(), key=len))[:PREVIEW["PREVIEW_ROWS"] - 1])
    for m in rows:
        if m["확정표준담보ID"] not in keep:
            m["확정표준담보ID"] = None
    return out


def test_화면4는_표준담보가_적어_표를_다_보여_주면_막대도_다_보여_주고_단추를_내지_않는다(site, real):
    page = site(sparse(real.tables), real.meta)
    fill_wide(page)
    total = std_total(page)
    per_kind = [int(re.search(r"표준담보 (\d+)개", t).group(1)) for t in page.locator("#s4-bars .bargroup h4").all_inner_texts()]
    assert total <= PREVIEW["PREVIEW_ROWS"] and max(per_kind) > PREVIEW["PREVIEW_BARS"], (total, per_kind)   # 문제가 났던 조합인지 먼저 본다
    assert more_buttons(page) == {}, "표는 모두 보이는데 접기 단추가 있음"
    assert page.locator("#s4-bars .barrow").count() == page.locator("#s4-pay tbody tr").count() == total


# ---------- 화면 5 ----------
def test_새_개정판의_적용시작일이_비어도_개정_전후_쌍이_없다고_하지_않는다(site):
    tables = fake_tables()
    for v in tables["sys_상품종형"]:
        if v["종형ID"] == NEW_A:
            v["적용시작일"] = None
    page = site(tables)
    page.click("#tab-s5")
    found = heads(page)
    assert len(found) == 1 and "쌍이 없어" not in found[0] and "값이 달라진 급부" in found[0], found
    assert not comment(page, "s5")["이유"].startswith("개정 전후 비교는")      # 없을때 글이 아니다


def test_비율_급부의_개정_전후는_같은_지급률을_달라짐으로_적지_않는다(site):
    page = site(ratio_revision_tables())
    page.click("#tab-s5")
    page.locator('[data-key^="s5-pair-"]', has_text="시험화재").click()
    rows = page.locator("#main table tbody tr").all_inner_texts()
    assert not [r for r in rows if r.count("가입금액의 100%") == 2], rows
    assert [r for r in rows if "상해사망" in r and "가입 100만원에 100만원" in r and "가입금액의 100%" in r], rows
