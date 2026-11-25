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
    # 영상은 배포본 옆(site/deck/media)에 있다. 다른 곳에 빌드하므로 영상 폴더를 배포본 폴더로 가리킨다
    r = subprocess.run([sys.executable, str(SRC / "build.py"), "--out", str(out), "--media-root", str(OUT.parent),
                        "--used", str(used), "--strict"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_bytes() == OUT.read_bytes(), "python proto_src/deck/build.py --out site/deck/index.html 로 다시 빌드한다"
    assert json.loads(used.read_text(encoding="utf-8")) == json.loads((SRC / "facts_used.json").read_text(encoding="utf-8"))


VIDEO_MAX_BYTES = 10_000_000          # 영상 한 편(배포본의 site/deck/media/partN.mp4)
VIDEO_TOTAL_BYTES = 40_000_000        # 네 편 합계


def test_video_slides_play_the_media_next_to_the_deck_and_keep_the_still(tmp_path):
    html = OUT.read_text(encoding="utf-8")
    srcs = re.findall(r'<video src="([^"]+)"', html)
    assert srcs == [f"media/part{n}.mp4" for n in range(1, 5)]
    sizes = [(OUT.parent / src).stat().st_size for src in srcs]
    assert max(sizes) <= VIDEO_MAX_BYTES and sum(sizes) <= VIDEO_TOTAL_BYTES, sizes
    # 영상이 있어도 정지 화면은 남는다(인쇄, 전체 장 보기, 영상을 읽지 못할 때)
    assert html.count('<div class="vph has-st"><div class="vst im-part') == 4
    # 영상 폴더에 파일이 없으면 <video> 없이 정지 화면만 남는다
    res = deck_build.build_deck(SRC / "content", FACTS, REFS, FONTS, media_root=tmp_path, only={5, 13, 16, 25})
    assert res.videos == [] and "<video" not in res.html
    assert res.html.count('<div class="vph has-st"><div class="vst im-part') == 4


def test_deck_is_a_standalone_offline_file():
    html = OUT.read_text(encoding="utf-8")
    assert "{{" not in html, "치환되지 않은 사실 자료 자리가 남아 있다"
    outside = re.findall(
        r"""<(?:script|img|iframe|link|source|video|audio|embed|object)\b[^>]*\s(?:src|href|data)\s*=\s*["']?(?:https?:)?//[^\s"'>]+"""
        r"""|url\(\s*["']?(?:https?:)?//[^)\s]+|@import\s+[^;]+""", html, flags=re.I)
    assert outside == []
    assert deck_build.check_external(html) == []
    assert OUT.stat().st_size < 50_000_000


def test_deck_has_32_slide_files_in_order():
    files = sorted(p.name for p in (SRC / "content").glob("[0-9][0-9].json"))
    assert files == [f"{n:02d}.json" for n in range(1, 33)]
    slides = deck_build.load_slides(SRC / "content")
    assert [s["no"] for s in slides] == list(range(1, 33))
    assert slides[0]["kind"] == "cover" and slides[-1]["kind"] == "closing"
    assert [s["no"] for s in slides if s["kind"] == "video"] == [5, 13, 16, 25]
    assert {s["chapter"] for s in slides[1:-1]} == {1, 2, 3, 4, 5, 6}
    html = OUT.read_text(encoding="utf-8")
    assert len(re.findall(r'<section class="slide ', html)) == 32


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
    assert len(res.slides) == 32


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


def test_name_placeholder_reads_deck_names_and_missing_name_stops(tmp_path):
    folder = write_slides(tmp_path / "ok", [body(1, diagram=[{"use": "text", "text": "{{name:claude_code}}, {{name:antigravity}}"}])])
    res = build(folder)
    assert "Claude Code, Antigravity" in res.html and "{{name:" not in res.html
    for bad in ("{{name:no_such_tool}}", "{{name:about}}"):
        folder = write_slides(tmp_path / bad.strip("{}").replace(":", "_"), [body(1, headline=bad)])
        with pytest.raises(SystemExit):
            build(folder)


def test_optional_scope_and_note_labels_render_and_are_limited(tmp_path):
    folder = write_slides(tmp_path / "c", [
        body(1, diagram=[{"use": "C10", "value": "1", "caption": "설명", "scope": "범위 글", "box": [0, 0, 400, 200]},
                         {"use": "C11", "value": "1", "total": "2", "scope": "대조 범위", "box": [500, 0, 400, 400]},
                         {"use": "C3", "box": [0, 420, 1760, 160], "nodes": [{"label": "가", "note": "작은 이름"}, {"label": "나"}]}]),
        body(2, diagram=[{"use": "C8", "box": [0, 0, 1760, 300], "dots": [{"d": "2026-11-11", "label": "점", "tag": "이 앱이 씀", "hero": True},
                                                                           {"d": "2026-09-15", "label": "점"}]},
                         {"use": "C5", "box": [0, 320, 1760, 200], "rows": [{"before": "가", "after": "나", "note": "모델 등급"}]}]),
        body(3, diagram=[{"use": "C16", "box": [0, 0, 1760, 500], "items": [], "total": "0원",
                          "week": {"daily": {"time": "06:10", "label": "수집"}, "manual": {"label": "사람이 실행", "text": "추출"},
                                   "after": "커밋"}},
                         {"use": "C10", "value": "1", "scope": "가" * 31, "box": [0, 520, 400, 100]}]),
    ])
    res = build(folder)
    for cls, text in (("c10-sc", "범위 글"), ("c11-sc", "대조 범위"), ("c3-note", "작은 이름"), ("c5-note", "모델 등급"), ("c8-tag", "이 앱이 씀")):
        assert re.search(rf'class="{cls}[^"]*">{text}<', res.html), cls
    assert "사람이 실행</b> 추출" in res.html and "152V310" in res.html
    assert any("[03] diagram[1].C10.scope: 31자 > 26자" in w for w in res.warnings)


def test_only_builds_the_named_slides_with_full_page_numbers():
    res = build(SRC / "content", only={2, 3})
    assert [s["no"] for s in res.slides] == [2, 3]
    assert "02 / 32" in res.html and "03 / 32" in res.html and 'data-no="4"' not in res.html


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


def test_sprite_holds_only_the_icons_the_slides_use(tmp_path):
    folder = write_slides(tmp_path / "c", [body(1, diagram=[{"use": "C3", "nodes": [{"label": "가", "icon": "공시 문서"},
                                                                                    {"label": "나", "icon": "stack"}]}])])
    html = build(folder).html
    # 개념 이름은 덱 아이콘 사전(_deck.json icons)으로, 디자인 시스템 도안(Lucide)은 ic- 로 심는다
    assert 'id="ic-file-text"' in html and 'href="#ic-file-text"' in html and 'id="i-stack"' in html
    assert 'id="i-camera"' not in html and 'id="ic-coins"' not in html
    # 덱 자체 이름 가운데 디자인 시스템에 같은 뜻의 도안이 있는 것은 디자인 시스템 도안으로 그린다
    folder = write_slides(tmp_path / "d", [body(1, diagram=[{"use": "C18", "icon": "doc"}])])
    assert 'href="#ic-file-text"' in build(folder).html


def test_unknown_icon_stops_the_build(tmp_path):
    folder = write_slides(tmp_path / "c", [body(1, diagram=[{"use": "C18", "icon": "없는 개념"}])])
    with pytest.raises(SystemExit):
        build(folder)


def test_icons_are_lucide_with_the_license_notice():
    icons = sorted((SRC / "icons").glob("*.svg"))
    assert len(icons) == 55
    notice = (SRC / "icons" / "LICENSE.txt").read_text(encoding="utf-8")
    assert "ISC License" in notice and "Lucide" in notice
    for p in icons:
        text = p.read_text(encoding="utf-8")
        assert "lucide" in text and "<script" not in text and "http" not in text.replace("http://www.w3.org/2000/svg", ""), p.name


def test_inline_svg_block_checks_text_size_and_refuses_external_references(tmp_path):
    ok = {"use": "svg", "box": [0, 0, 800, 200], "vb": [800, 200], "alt": "그림",
          "svg": "<rect x='0' y='0' width='800' height='200' class='sv-paper'/><text x='20' y='60'>{{fact:practice_compare_time}}</text>"
                 "<text x='20' y='120' class='aux'>보조 글</text><use href='{{icon:비용}}' x='600' y='40' width='48' height='48'/>"}
    small = {"use": "svg", "box": [0, 220, 400, 100], "vb": [800, 200], "svg": "<text x='0' y='40'>작게 보이는 글</text>"}
    folder = write_slides(tmp_path / "c", [body(1, diagram=[ok, small])])
    res = build(folder)
    assert '<svg class="svgb"' in res.html and "2~3일" in res.html and 'id="ic-coins"' in res.html
    assert any("[01] diagram[1].svg.text[0]: 글자 13.0px < 22px" in w for w in res.warnings), res.warnings
    assert not any("diagram[0]" in w for w in res.warnings), res.warnings
    for bad in ("<image href='https://example.com/a.png'/>", "<a href='https://example.com'><text>가</text></a>",
                "<use href='https://example.com/s.svg#x'/>", "<text onclick='x()'>가</text>", "<script>1</script>",
                "<rect style='fill:url(https://example.com/p)'/>"):
        folder = write_slides(tmp_path / f"bad{abs(hash(bad))}", [body(1, diagram=[{"use": "svg", "svg": bad}])])
        with pytest.raises(SystemExit):
            build(folder)


def test_quote_zones_tiles_and_build_order(tmp_path):
    folder = write_slides(tmp_path / "c", [body(1, diagram=[
        {"use": "quote", "box": [0, 0, 900, 260], "text": "회사마다 필수 특약이 다릅니다", "who": "실무자 1명", "build": 1},
        {"use": "C12", "img": "talk_preview", "box": [0, 280, 1000, 300],
         "zones": [{"n": "A", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2, "label": "인쇄"}], "marks": [{"n": 2, "x": 0.5, "y": 0.6, "label": "표식"}],
         "build": 2},
        {"use": "C10", "box": [1100, 0, 400, 260], "tile": True, "icon": "담보", "tile_label": "결합 제약", "value": "79", "build": 9}])])
    res = build(folder)
    assert '<span class="qt-gist">응답 요지</span>' in res.html and "\u201c" not in res.html
    assert 'class="c12-zn"' in res.html and '<span class="c12-zk"' in res.html
    assert 'class="c10 tile"' in res.html and 'id="ic-shield-alert"' in res.html
    assert 'data-build="1"' in res.html and 'data-build="2"' in res.html
    assert any("diagram[2].build: 9: 1~8" in w for w in res.warnings), res.warnings


def test_more_than_six_icons_on_a_slide_is_warned(tmp_path):
    nodes = [{"label": str(i), "icon": "stack"} for i in range(7)]
    folder = write_slides(tmp_path / "c", [body(1, diagram=[{"use": "C3", "arrows": False, "nodes": nodes}])])
    assert any("아이콘 7개" in w for w in build(folder).warnings)


def test_layout_options_keep_cards_aligned_and_lines_off_labels(tmp_path):
    folder = write_slides(tmp_path / "c", [body(1, diagram=[
        {"use": "C3", "align": "top", "box": [0, 0, 1760, 200], "nodes": [{"label": "가", "sub": "한 줄"}, {"label": "나"}]},
        {"use": "C5", "box": [0, 220, 1760, 300], "badgeCol": {"label": "효과", "badge": "측정 전", "once": True},
         "rows": [{"before": "가", "after": "나", "hero": True}, {"before": "다", "after": "라"}]},
        {"use": "C9", "layout": "legend", "box": [0, 540, 900, 60], "captions": ["범례", "노선도"],
         "graph": {"nodes": [{"id": "a", "label": "위"}, {"id": "b", "label": "옆"}, {"id": "c", "label": "가운데"}],
                   "edges": [{"from": "a", "to": "c"}]}}])])
    res = build(folder)
    assert 'class="c3-n top"' in res.html
    # 배지는 열 머리에 한 번만 두고 배지 열은 없다
    assert res.html.count('class="bd-um"') == 1 and 'class="c5-bd"' not in res.html
    # 선이 아래로만 나가는 점(위)은 이름을 점 위에, 위에서 선이 들어오는 점(가운데)은 점 아래에
    assert re.search(r'class="c9-gn sh-circle up"[^>]*><i></i><b class="ax">위<', res.html)
    assert re.search(r'class="c9-gn sh-circle"[^>]*><i></i><b class="ax">가운데<', res.html)
