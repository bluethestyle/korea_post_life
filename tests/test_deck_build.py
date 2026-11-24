"""발표 덱(site/deck/index.html)이 소스(proto_src/deck)에서 그대로 재빌드되는지, 오프라인 단독 파일인지 본다."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "proto_src" / "deck"
OUT = ROOT / "site" / "deck" / "index.html"


def test_committed_deck_is_what_the_source_builds(tmp_path):
    out = tmp_path / "index.html"
    used = tmp_path / "facts_used.json"
    subprocess.run([sys.executable, str(SRC / "build.py"), "--out", str(out), "--used", str(used)],
                   check=True, cwd=ROOT, capture_output=True)
    assert out.read_bytes() == OUT.read_bytes(), "python proto_src/deck/build.py --out site/deck/index.html 로 다시 빌드한다"
    assert json.loads(used.read_text(encoding="utf-8")) == json.loads((SRC / "facts_used.json").read_text(encoding="utf-8"))


def test_deck_is_a_standalone_offline_file():
    html = OUT.read_text(encoding="utf-8")
    assert "{{" not in html, "치환되지 않은 사실 자료 자리가 남아 있다"
    outside = re.findall(
        r"""<(?:script|img|iframe|link|source|video|audio|embed|object)\b[^>]*\s(?:src|href|data)\s*=\s*["']?(?:https?:)?//[^\s"'>]+"""
        r"""|url\(\s*["']?(?:https?:)?//[^)\s]+|@import\s+[^;]+""", html, flags=re.I)
    assert outside == []
    assert OUT.stat().st_size < 50_000_000


def test_every_number_placeholder_names_a_fact():
    facts = json.loads((ROOT / "presentation_animation" / "facts.json").read_text(encoding="utf-8"))["facts"]
    content = (SRC / "content.json").read_text(encoding="utf-8")
    keys = {m.split(".")[0] for m in re.findall(r"\{\{(?:fact|asof):([A-Za-z0-9_.\-]+)\}\}", content)}
    assert keys and keys <= set(facts), sorted(keys - set(facts))
