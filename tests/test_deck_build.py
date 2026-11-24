"""발표 덱(site/deck/index.html)이 소스(proto_src/deck)에서 그대로 재빌드되는지, 오프라인 단독 파일인지, 장 파일과 부품의
글자 수 상한을 지키는지 본다."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "proto_src" / "deck"
OUT = ROOT / "site" / "deck" / "index.html"
FACTS = ROOT / "presentation_animation" / "facts.json"
FONTS = ROOT / "proto_src" / "fonts" / "fonts_v4.css"
REFS = SRC / "refs.json"

spec = importlib.util.spec_from_file_location("deck_build", SRC / "build.py")
deck_build = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = deck_build          # dataclass 가 모듈을 찾을 수 있게
spec.loader.exec_module(deck_build)

PLACEHOLDER = re.compile(r"\{\{(fact|asof|len|ref):([A-Za-z0-9_.\-]+)(?:\|[a-z0-9]+)?\}\}")
COMPONENTS = {f"C{i}" for i in range(1, 21)}


def build(content_dir: Path, only=None):
    return deck_build.build_deck(content_dir, FACTS, REFS, FONTS, only=only)


def write_slides(folder: Path, slides: list[dict]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for s in slides:
        (folder / f"{s['no']:02d}.json").write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    return folder


def body(no: int, **kw) -> dict:
    s = {"no": no, "kind": "body", "chapter": 1, "status": "new", "headline": "짧은 헤드라인"}
    s.update(kw)
    return s


def test_committed_deck_is_what_the_source_builds(tmp_path):
    out = tmp_path / "index.html"
    used = tmp_path / "facts_used.json"
    r = subprocess.run([sys.executable, str(SRC / "build.py"), "--out", str(out), "--used", str(used), "--strict"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_bytes() == OUT.read_bytes(), "python proto_src/deck/build.py --out site/deck/index.html 로 다시 빌드한다"
    assert json.loads(used.read_text(encoding="utf-8")) == json.loads((SRC / "facts_used.json").read_text(encoding="utf-8"))


def test_deck_is_a_standalone_offline_file():
    html = OUT.read_text(encoding="utf-8")
    assert "{{" not in html, "치환되지 않은 사실 자료 자리가 남아 있다"
    outside = re.findall(
        r"""<(?:script|img|iframe|link|source|video|audio|embed|object)\b[^>]*\s(?:src|href|data)\s*=\s*["']?(?:https?:)?//[^\s"'>]+"""
        r"""|url\(\s*["']?(?:https?:)?//[^)\s]+|@import\s+[^;]+""", html, flags=re.I)
    assert outside == []
    assert deck_build.check_external(html) == []
    assert OUT.stat().st_size < 50_000_000


def test_deck_has_26_slide_files_in_order():
    files = sorted(p.name for p in (SRC / "content").glob("[0-9][0-9].json"))
    assert files == [f"{n:02d}.json" for n in range(1, 27)]
    slides = deck_build.load_slides(SRC / "content")
    assert [s["no"] for s in slides] == list(range(1, 27))
    assert slides[0]["kind"] == "cover" and slides[-1]["kind"] == "closing"
    assert [s["no"] for s in slides if s["kind"] == "video"] == [5, 13, 16, 21]
    assert {s["chapter"] for s in slides[1:-1]} == {1, 2, 3, 4, 5, 6}
    html = OUT.read_text(encoding="utf-8")
    assert len(re.findall(r'<section class="slide ', html)) == 26


def test_every_placeholder_names_a_fact_or_a_ref():
    facts = json.loads(FACTS.read_text(encoding="utf-8"))["facts"]
    refs = json.loads(REFS.read_text(encoding="utf-8"))["refs"]
    for folder in (SRC / "content", SRC / "samples"):
        text = "".join(p.read_text(encoding="utf-8") for p in sorted(folder.glob("*.json")))
        found = PLACEHOLDER.findall(text)
        keys = {k.split(".")[0] for kind, k in found if kind != "ref"}
        ref_keys = {k.split(".")[0] for kind, k in found if kind == "ref"}
        assert keys <= set(facts), (folder.name, sorted(keys - set(facts)))
        assert ref_keys <= set(refs), (folder.name, sorted(ref_keys - set(refs)))


def test_deck_builds_without_limit_warnings():
    res = build(SRC / "content")
    assert res.warnings == []
    assert len(res.slides) == 26


def test_samples_use_every_component_and_build_without_warnings():
    res = build(SRC / "samples")
    assert res.warnings == [], res.warnings
    used = set()

    def walk(o):
        if isinstance(o, dict):
            if o.get("use"):
                used.add(o["use"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for s in res.slides:
        walk(s.get("diagram", []))
    # C1(머리, 큰 판), C13(영상 장), C14(용어 풀이 띠)는 프레임이 그리기도 한다
    kinds = {s["kind"] for s in res.slides}
    frame = {"C1"} | ({"C13"} if "video" in kinds else set()) | ({"C14"} if any(s.get("terms") for s in res.slides) else set())
    assert COMPONENTS <= used | frame, sorted(COMPONENTS - used - frame)


def test_over_limit_text_is_warned(tmp_path):
    long = "가" * 60
    folder = write_slides(tmp_path / "c", [
        body(1, headline=long),
        body(2, diagram=[{"use": "C4", "cols": ["EPOST", "HANWHALIFE", "SAMSUNGFIRE"],
                          "rows": [{"label": "면책기간", "values": ["가" * 19, "90일", "90일"]}]}],
             points=["나" * 31], terms=["공시 문서", "고지사항", "간편심사", "인수기준"]),
        body(3, diagram=[{"use": "C10", "value": "1", "hero": True}, {"use": "C10", "value": "2", "hero": True}]),
    ])
    w = "\n".join(build(folder).warnings)
    assert "[01] headline: 60자 > 50자" in w
    assert "[02] diagram[0].C4.rows[0].values[0]: 19자 > 18자" in w
    assert "[02] points[0]: 31자 > 30자" in w
    assert "[02] terms: 용어 4개 > 3개" in w
    assert "[03] diagram: 강조 2곳" in w


def test_box_outside_the_region_is_warned(tmp_path):
    folder = write_slides(tmp_path / "c", [body(1, diagram=[{"use": "C10", "value": "1", "box": [0, 0, 1800, 100]}])])
    assert any("도해 영역" in x for x in build(folder).warnings)


def test_press_ref_gets_the_badge_and_its_domain_in_the_footer(tmp_path):
    folder = write_slides(tmp_path / "c", [body(1, diagram=[{"use": "text", "text": "{{ref:insurance_underwriting_example}}"}]),
                                           body(2, diagram=[{"use": "text", "text": "{{ref:jev_release.date}}"}])])
    res = build(folder)
    s1, s2 = res.html.split('id="s2"')
    assert '<span class="pb">보도 기준</span>' in s1 and "외부 출처: siliconangle.com" in s1
    assert "보도 기준" not in s2.split("<aside")[0] and "외부 출처: typesafe.ai" in s2
    assert res.used["refs"] == {"01": ["insurance_underwriting_example"], "02": ["jev_release"]}


def test_missing_fact_or_ref_stops_the_build(tmp_path):
    for text in ("{{ref:no_such_ref}}", "{{fact:no_such_fact}}", "{{fact:hanwha_summary_pages.nope}}"):
        folder = write_slides(tmp_path / text.strip("{}").replace(":", "_"), [body(1, headline=text)])
        with pytest.raises(SystemExit):
            build(folder)


def test_only_builds_the_named_slides_with_full_page_numbers():
    res = build(SRC / "content", only={2, 3})
    assert [s["no"] for s in res.slides] == [2, 3]
    assert "02 / 26" in res.html and "03 / 26" in res.html and 'data-no="4"' not in res.html


def test_refs_are_checked_sources_only():
    refs = json.loads(REFS.read_text(encoding="utf-8"))["refs"]
    assert refs
    for key, r in refs.items():
        assert r["kind"] in {"official", "academic", "press"}, key
        assert r["urls"] and all(u.startswith("https://") for u in r["urls"]), key
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["checked"]), key
        assert "unverified" not in json.dumps(r, ensure_ascii=False).lower(), key
    assert deck_build.load_refs(REFS) == refs


def test_assets_are_small_jpegs():
    jpgs = sorted((SRC / "assets").glob("*.jpg"))
    assert {p.stem for p in jpgs} >= {"summary", "tab_market", "tab_gate", "tab_cover", "tab_insight", "tab_graph",
                                       "talk_preview", "cancer_surgery"}
    for p in jpgs:
        assert p.read_bytes()[:3] == b"\xff\xd8\xff", p.name
        assert p.stat().st_size <= 250 * 1024, p.name


def test_same_input_gives_same_bytes():
    assert build(SRC / "samples").html == build(SRC / "samples").html
