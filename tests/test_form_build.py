"""작품설명서 빌더(proto_src/form/build.py) 시험. PDF 는 만들지 않고 HTML 까지만 본다."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "proto_src" / "form"
spec = importlib.util.spec_from_file_location("form_build", FORM / "build.py")
form_build = importlib.util.module_from_spec(spec)
sys.modules["form_build"] = form_build
spec.loader.exec_module(form_build)

CONTENT = json.loads((FORM / "content.json").read_text(encoding="utf-8"))
ATTACHMENTS = [f["file"] for f in CONTENT["output"]["files"]]
OPTIONS = CONTENT["form"]["kind"]["options"]


@pytest.fixture(scope="module")
def sample() -> tuple[str, dict]:
    return form_build.build_html(strict=True)


def test_sample_builds_in_strict_mode_without_identity(sample):
    doc, info = sample
    assert info["identity"] is False
    assert not re.findall(r"\{\{[^}]*\}\}|__[A-Z_]+__", doc)
    # 견본에는 양식의 안내 문구가 들어가고 출품 구분은 아무것도 체크하지 않는다
    assert CONTENT["form"]["dept"]["guide"] in doc
    assert doc.count('class="o on"') == 0
    # 표 형태: 쪽마다 머리 줄(항 목, 작 성 내 용)이 있다
    assert doc.count('<section class="page"') == info["pages"]
    assert doc.count(f'<div class="th l">{CONTENT["form"]["head"][0]}</div>') == info["pages"]
    for label in ("dept", "name", "kind", "title", "tools", "body", "output"):
        assert CONTENT["form"][label]["label"] in doc


def test_every_placeholder_is_filled_and_no_bare_digits(sample):
    _, info = sample
    assert info["digits"] == []


def test_bare_number_in_content_stops_strict_build(tmp_path):
    c = json.loads((FORM / "content.json").read_text(encoding="utf-8"))
    c["pages"][1]["blocks"]["headline"] += " 567쪽"
    p = tmp_path / "content.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="자리 표시 밖의 숫자"):
        form_build.build_html(p, strict=True)


def test_unknown_fact_stops_the_build(tmp_path):
    c = json.loads((FORM / "content.json").read_text(encoding="utf-8"))
    c["pages"][0]["blocks"]["lead"] = "{{fact:없는_열쇠}}"
    p = tmp_path / "content.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="없는_열쇠"):
        form_build.build_html(p)


def test_no_urls_and_no_clickable_links_only_attachment_names(sample):
    doc, _ = sample
    # 문서에는 주소(http)와 클릭 링크(<a>)가 하나도 없고, 첨부 파일 이름 둘로 안내한다
    assert "http" not in doc          # 대소문자를 구분한다(사진과 글꼴의 base64 글자가 우연히 HTTP 로 읽히는 경우는 제외)
    assert not re.search(r"https?:", doc, re.I)
    assert not re.search(r"<a[\s>]", doc, re.I)
    assert ATTACHMENTS == ["postlife_app.html", "postlife_deck.html"]
    for name in ATTACHMENTS:
        assert name in doc
    assert form_build.check_links(doc) == []
    # src, url(), @import 로 부르는 외부 자원은 없다
    assert not re.search(r"""\bsrc\s*=\s*["']?(?:https?:)?//""", doc, re.I)
    assert not re.search(r"""url\(\s*["']?(?:https?:)?//""", doc, re.I)
    assert "@import" not in doc


def test_body_uses_noun_style_without_polite_endings(sample):
    """개조식 문어체: 본문에 "~니다" 경어체 종결이 없다(양식 원문 안내와 화면에서 옮긴 문구에도 없다)."""
    doc, _ = sample
    text = re.sub(r"<style.*?</style>|<svg.*?</svg>|<script.*?</script>", "", doc, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    assert re.findall(r"[가-힣]*니다", text) == []


def test_progress_percentages_sum_to_one_hundred(sample):
    doc, _ = sample
    assert form_build.pct_split([2, 3, 2, 12], 19) == [10.5, 15.8, 10.5, 63.2]
    assert sum(form_build.pct_split([1, 1, 1], 3)) == pytest.approx(100.0)
    assert sum(form_build.pct_split([5, 7, 11, 13], 36)) == pytest.approx(100.0)
    assert form_build.pct_split([0, 0], 0) == [0.0, 0.0]
    # 진행 현황에는 상태별 가로 막대가 있고, 막대 안 비율의 합은 100.0
    pcts = [float(x) for x in re.findall(r'<span class="seg \w+" style="[^"]*"><span>([0-9.]+)%</span>', doc)]
    assert pcts and sum(pcts) == pytest.approx(100.0)


def test_identity_fills_the_head_rows_and_checks_one_option(tmp_path):
    p = tmp_path / "identity.json"
    p.write_text(json.dumps({"소속부서": "시험실 시험팀", "성명": "시험성명", "출품구분": OPTIONS[2]}, ensure_ascii=False), encoding="utf-8")
    doc, info = form_build.build_html(identity_path=p)
    assert info["identity"] is True
    assert "시험실 시험팀" in doc and "시험성명" in doc
    assert doc.count('class="o on"') == 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"소속부서": "가", "성명": "나", "출품구분": "다른 구분"}, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="출품구분"):
        form_build.build_html(identity_path=bad)


def test_state_text_follows_the_weekly_snapshot(tmp_path):
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "sys_상품종형.jsonl").write_text(json.dumps({"모상품ID": "EPOST_MORESIMPLE_CANCER"}, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    _, info = form_build.build_html(snapshot_dir=snap)
    assert info["states"] == {"moresimple": True, "hanarook": False}
    _, info = form_build.build_html(snapshot_dir=tmp_path / "없음")
    assert info["states"] == {"moresimple": False, "hanarook": False}


def test_form_assets_are_small_jpegs():
    files = sorted((FORM / "assets").glob("*"))
    assert files
    for f in files:
        assert f.suffix == ".jpg"
        assert f.stat().st_size <= 300 * 1024, f.name


CUTS = ("cut_kpi", "cut_gate", "cut_cover", "cut_insight", "cut_talk", "cut_head_a", "cut_head_b", "cut_copy_button", "cut_pending_chip")
FULLS = ("summary", "tab_gate", "tab_insight", "tab_graph", "cancer_surgery", "talk_preview")


def test_zoom_cuts_exist_and_are_used(sample):
    """확대 컷 파일이 있고(300KB 이하는 위 시험이 본다), 폭이 2배 배율 이상으로 찍혀 글자가 읽히며, 쪽에서 실제로 쓰인다."""
    _, info = sample
    for name in CUTS + FULLS:
        f = FORM / "assets" / f"{name}.jpg"
        assert f.is_file(), name
        assert name in info["images"], f"{name} 이 어느 쪽에서도 쓰이지 않음"
    # 2배 배율로 찍은 컷의 폭은 화면 폭(1280) 안 요소의 2배 이상이어야 한다: 가장 좁은 응대 화법 카드도 600px 이상
    for name in ("cut_kpi", "cut_gate", "cut_cover", "cut_insight", "cut_talk", "cut_head_a", "cut_head_b"):
        width = form_build.jpeg_size(FORM / "assets" / f"{name}.jpg")[0]
        assert width >= 600, (name, width)
    # 옛 머리 띠 캡처는 쓰지 않는다
    assert not (FORM / "assets" / "head_gate.jpg").exists()


def test_page_count_and_page_names(sample):
    doc, info = sample
    assert info["pages"] == 11
    assert doc.count('<section class="page"') == 11
    assert "확장과 한계" in doc
    assert "넓혀 쓰기와 한계" not in doc


def test_replaced_terms_do_not_come_back():
    text = (FORM / "content.json").read_text(encoding="utf-8")
    for bad in ("틀린 값", "틀리게", "정식 배포 전", "비교 상대", "뒤져", "지료 기준", "넓혀 쓰기와", "판올림", "스냅샷"):
        assert bad not in text.replace("'스냅샷'이라는 용어가", ""), bad
    assert "·" not in re.sub(r"AI담당관 제작 AI업무비서·AI에이전트|이미지·동영상|부서·업무|평가기준\(참신성·실용성·확장성·완성도\)", "", text).split('"labels"', 1)[1]


def _identity_file() -> Path | None:
    cands = []
    if os.environ.get("FORM_IDENTITY"):
        cands.append(Path(os.environ["FORM_IDENTITY"]))
    cands.append(ROOT / "local" / "submission" / "identity.json")
    try:
        common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        cands.append(Path(common).parent / "local" / "submission" / "identity.json")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return next((p for p in cands if p.is_file()), None)


def test_tracked_files_do_not_contain_identity_values():
    path = _identity_file()
    if path is None:
        pytest.skip("identity 파일이 없음(local/submission/identity.json)")
    data = json.loads(path.read_text(encoding="utf-8"))
    values = [str(data[k]).strip() for k in ("성명", "소속부서") if str(data.get(k, "")).strip()]
    names = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    hits = []
    for name in filter(None, names):
        f = ROOT / name
        if not f.is_file():
            continue
        body = f.read_bytes()
        for i, v in enumerate(values):
            if v.encode("utf-8") in body:
                hits.append(f"{name}(값 {i + 1})")      # 값 자체는 출력하지 않는다
    assert hits == []
