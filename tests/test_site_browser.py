"""판단 화면을 지어낸 자료로 만들어 브라우저로 열고, 화면(app.js)이 쓰는 글이 자료와 서로 맞는지 본다.

자료 가공은 test_site.py와 test_site_weekly.py가 보고, 여기서는 화면이 그 자료로 세고 적는 글을 본다.
scripts/dev/check_site_browser.py처럼 만든 HTML을 file://로 열고 바깥 요청을 막는다. playwright나 chromium이 없으면 건너뛴다.
"""
import copy
import re

import pytest

from postlife.site import build
from postlife.site.model import BASIS_COLUMN, RATIO_BASIS, Data
from test_site import (NEW_A, NEW_B, PRIV, SF, SF_OLD, benefit, fake_tables, mapped, no_limit_tables, ratio_revision_tables,
                       ratio_tables, rider, variant)
from test_site_weekly import PREV, pending_private, rep_tables

sync_api = pytest.importorskip("playwright.sync_api")

NOW = {"snapshot_at": "2026-11-18T17:00:00+09:00"}
MERITZ = "MERITZ_M1_gggggg"


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
    """site(tables, meta, previous)는 그 자료로 만든 화면을 연 page를 돌려준다. 콘솔 오류가 하나라도 나면 시험이 끝날 때 실패한다."""
    opened = []

    def open_site(tables, meta=NOW, previous=None):
        path = tmp_path / f"site{len(opened)}.html"
        path.write_text(build.render(Data(tables, meta), previous), encoding="utf-8")
        context = browser.new_context(viewport={"width": 1280, "height": 900}, offline=True)
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
