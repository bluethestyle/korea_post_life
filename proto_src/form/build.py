#!/usr/bin/env python3
"""작품설명서 빌드: content.json + facts.json + refs.json + tpl.html (+ identity 파일) → A4 HTML 한 파일과 PDF.

실행(리포 루트에서, playwright 가 든 파이썬):
    python proto_src/form/build.py --html out/작품설명서.html --out out/작품설명서.pdf [--identity <identity.json>]
                                   [--preview <PNG 폴더>] [--strict]

- 양식은 "2026년 PoSID AI 공모전 왕중왕전 작품설명서"의 두 열 표(항 목 | 작 성 내 용)다. 쪽마다 바깥 테두리와 두 열이 이어지고,
  첫 쪽에 소속부서, 성명, 출품 구분, 제목, 활용 AI도구 행이 오며, "활용 내용 및 설명" 행이 여러 쪽에 걸친 뒤 "생성물" 행으로 끝난다.
- 글의 수치는 content.json 의 자리 표시({{fact:}}, {{ref:}}, {{len:}}, {{asof:}}, {{name:}})를 덱 빌더의 함수(deckparts.Ctx)로 채운다.
  {{pg:쪽id}} 는 쪽 번호, {{state:이름}} 은 주간 마감 자료(data/snapshot/sys_상품종형.jsonl)에 그 상품이 있는지에 따라 고른 글이다.
- 성명, 소속부서, 출품 구분은 --identity 로 준 JSON(열쇠: 소속부서, 성명, 출품구분)에서 읽어 HTML 과 PDF 에만 넣는다.
  파일을 주지 않으면 양식의 안내 문구를 넣은 견본을 만든다. 이 값은 화면에 출력하지 않는다.
- 색과 글꼴은 발표 덱의 틀(proto_src/deck/tpl.html 의 :root)과 심은 글꼴(PLKo)을, 아이콘은 덱의 아이콘 세트를 그대로 쓴다.
- 사진은 proto_src/form/assets/ 를 먼저, 없으면 proto_src/deck/assets/ 를 찾는다(proto_src/form/shoot.py 가 다시 찍는다).
- 결과 HTML 에 외부 주소를 부르는 src, href, url(), @import 가 있으면 멈춘다. 예외는 content.json 의 output.links 네 주소를
  가리키는 <a href> 뿐이다(PDF 에서 클릭되는 링크).
- --strict: 자리 표시 밖에 적은 숫자(양식 원래 문구와 literal_digits 제외), 채우지 못한 자리 표시, PDF 단계의 넘침(칸 밖으로 나간 글,
  8pt 미만 글자)을 오류로 본다.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DECK = ROOT / "proto_src" / "deck"
if str(DECK) not in sys.path:
    sys.path.insert(0, str(DECK))
import deckparts as P  # noqa: E402

_spec = importlib.util.spec_from_file_location("deck_build_for_form", DECK / "build.py")
deck_build = sys.modules.get("deck_build_for_form") or importlib.util.module_from_spec(_spec)
if "deck_build_for_form" not in sys.modules:
    sys.modules["deck_build_for_form"] = deck_build
    _spec.loader.exec_module(deck_build)

CRITERIA = ("참신성", "실용성", "확장성", "완성도")
ORGS3 = ("EPOST", "HANWHALIFE", "SAMSUNGFIRE")
ROLE_CLS = {"AI": "ai", "코드": "code", "사람": "hum"}
IDENTITY_KEYS = ("소속부서", "성명", "출품구분")
LOCAL_PH = re.compile(r"\{\{(pg|state):([^{}]+)\}\}")
ANY_PH = re.compile(r"\{\{[^{}]*\}\}")
SKIP_DIGIT_KEYS = {"form", "literal_digits", "format", "id", "img", "icon", "url", "prefix", "marks", "zones_xy", "state",
                   "rows_from", "names_from", "table_img", "html_title"}


ARROW = ('<svg class="arw" viewBox="0 0 10 6" aria-hidden="true">'
         '<path d="M0.5 3H8.6M6.4 0.9L8.8 3L6.4 5.1" fill="none" stroke="currentColor" stroke-width="1.1" '
         'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def esc(s: Any) -> str:
    return P.esc(s)


def circled(text: str) -> str:
    """양식 문구의 동그라미 숫자(①)는 심은 글꼴에 없어 동그라미 안의 숫자로 그린다."""
    return re.sub("[①-⑨]", lambda m: f'<span class="circ">{ord(m.group(0)) - 0x245F}</span>', text)


# ---------------------------------------------------------------------------
# 입력
# ---------------------------------------------------------------------------
def load_identity(path: Path | None, options: list[str]) -> dict | None:
    """identity 파일을 읽는다. 값은 화면에 찍지 않는다."""
    if path is None:
        return None
    if not path.is_file():
        raise SystemExit("--identity 로 준 파일이 없습니다")
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in IDENTITY_KEYS if not str(data.get(k, "")).strip()]
    if missing:
        raise SystemExit(f"identity 파일에 값이 없는 열쇠: {', '.join(missing)}")
    if data["출품구분"] not in options:
        raise SystemExit("identity 파일의 출품구분 값이 양식의 세 선택지 가운데 하나와 글자까지 같아야 합니다")
    return {k: str(data[k]).strip() for k in IDENTITY_KEYS}


def snapshot_parents(snapshot_dir: Path) -> set[str]:
    path = snapshot_dir / "sys_상품종형.jsonl"
    out: set[str] = set()
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out.add(str(row.get("모상품ID") or ""))
    return out


def digits_outside(content: dict) -> list[str]:
    """자리 표시 밖에 직접 적은 숫자(양식 원래 문구와 literal_digits 는 뺀다)."""
    allowed = sorted((d["text"] for d in content.get("literal_digits", [])), key=len, reverse=True)
    found: list[str] = []

    def walk(o: Any, where: str) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k not in SKIP_DIGIT_KEYS:
                    walk(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")
        elif isinstance(o, str):
            bare = ANY_PH.sub("", o)
            for a in allowed:
                bare = bare.replace(a, "")
            for m in re.finditer(r"[0-9]+", bare):
                found.append(f"{where}: {m.group(0)} …{bare[max(0, m.start() - 10):m.end() + 6]}…")

    walk(content, "content")
    return found


# ---------------------------------------------------------------------------
# 그리기 도구
# ---------------------------------------------------------------------------
class Form:
    def __init__(self, content: dict, facts: dict, refs: dict, deck: dict, identity: dict | None,
                 parents: set[str], image_dirs: list[Path]):
        self.c = content
        self.ctx = P.Ctx(facts, refs, deck, {})
        self.identity = identity
        self.pages = content["pages"]
        self.page_no = {p["id"]: i + 1 for i, p in enumerate(self.pages)}
        self.n_body = len(self.pages)          # "활용 내용 및 설명" 행이 끝나는 쪽(이 쪽에서 "생성물" 행이 시작한다)
        self.shot_groups = content["output"]["shots_pages"]
        self.total = self.n_body + len(self.shot_groups)   # 뒤의 쪽들은 "생성물 (계속)": 화면 캡처
        self.page_no["shots"] = self.n_body + 1
        self.L = content.get("labels", {})
        self.states = {name: any(x.startswith(s["prefix"]) for x in parents) for name, s in content.get("states", {}).items()}
        self.images: dict[str, Path] = {}
        for d in image_dirs:
            for p in sorted(Path(d).glob("*.jpg")):
                self.images.setdefault(p.stem, p)
        self.img_used: list[str] = []
        self.img_size: dict[str, tuple[int, int]] = {}
        self.errors: list[str] = []
        self.crit_marks = self._crit_marks()
        self.links_ok = [l["url"] for l in content["output"]["links"]]

    # 평가기준 표식 -------------------------------------------------------
    def _crit_marks(self) -> dict[int, dict[str, bool]]:
        """쪽 번호 → {기준: 주된 근거인가}."""
        out: dict[int, dict[str, bool]] = {}

        def walk(o: Any, no: int) -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "crit":
                        items = v if isinstance(v, list) else [v]
                        for c in items:
                            name = c.rstrip("*")
                            if name not in CRITERIA:
                                self.errors.append(f"모르는 평가기준: {c}")
                                continue
                            prim = c.endswith("*")
                            if no == 1 and not isinstance(v, list):
                                continue          # 1쪽 기준 카드는 근거가 아니라 안내다
                            cur = out.setdefault(no, {})
                            cur[name] = cur.get(name, False) or prim
                    else:
                        walk(v, no)
            elif isinstance(o, list):
                for v in o:
                    walk(v, no)

        for i, p in enumerate(self.pages):
            walk(p.get("blocks", {}), i + 1)
        return out

    def crit_pages(self, name: str) -> list[int]:
        return [no for no, m in sorted(self.crit_marks.items()) if m.get(name)]

    # 글 -----------------------------------------------------------------
    def pre(self, text: str) -> str:
        for _ in range(4):
            def repl(m: re.Match) -> str:
                kind, key = m.group(1), m.group(2).strip()
                if kind == "pg":
                    if key not in self.page_no:
                        self.errors.append(f"{m.group(0)}: 없는 쪽 id")
                        return m.group(0)
                    return str(self.page_no[key])
                st = self.c.get("states", {}).get(key)
                if st is None:
                    self.errors.append(f"{m.group(0)}: content.json states 에 없음")
                    return m.group(0)
                return st["on" if self.states[key] else "off"]["text"]
            new = LOCAL_PH.sub(repl, text)
            if new == text:
                break
            text = new
        return text

    def t(self, text: Any) -> str:
        if text is None:
            return ""
        # 글꼴(PLKo)의 화살표 글자는 작아 꺾쇠처럼 보여서 인라인 그림으로 바꾼다
        return self.ctx.t(self.pre(str(text))).replace("→", ARROW)

    def lab(self, key: str) -> str:
        if key not in self.L:
            self.errors.append(f"content.json labels 에 없음: {key}")
            return ""
        return self.t(self.L[key])

    def fact(self, path: str) -> Any:
        try:
            v = self.ctx.value("fact", path)
        except KeyError as exc:
            self.errors.append(str(exc))
            return None
        self.ctx._note(self.ctx.used_facts, path.split(".")[0])
        return v

    def num(self, text: str) -> float:
        return self.ctx.num(self.pre(text), "num")

    # 부품 -----------------------------------------------------------------
    def ic(self, name: str, mm: float = 4.5, cls: str = "") -> str:
        sid = P.resolve_icon(name)
        if sid is None:
            self.errors.append(f"모르는 아이콘: {name}")
            sid = "i-doc"
        P.mark_icon(sid)
        return (f'<svg class="ic {cls}" style="width:{mm}mm;height:{mm}mm" viewBox="0 0 48 48" aria-hidden="true">'
                f'<use href="#{sid}"/></svg>')

    def img_cls(self, name: str) -> str:
        if name not in self.images:
            self.errors.append(f"사진 없음: {name}.jpg")
        elif name not in self.img_used:
            self.img_used.append(name)
        return f"im-{re.sub(r'[^A-Za-z0-9_-]', '_', name)}"

    def aspect(self, name: str) -> float:
        if name not in self.img_size and name in self.images:
            from PIL import Image
            with Image.open(self.images[name]) as im:
                self.img_size[name] = im.size
        w, h = self.img_size.get(name, (16, 9))
        return w / h

    def crit_pills(self, crit: Any) -> str:
        items = crit if isinstance(crit, list) else ([crit] if crit else [])
        out = []
        for c in items[:2]:
            prim = c.endswith("*")
            out.append(f'<span class="cp {"bm" if prim else "b"}">{esc(c.rstrip("*"))}</span>')
        return "".join(out)

    def bh(self, title: str, crit: Any = None, icon: str | None = None) -> str:
        ic = self.ic(icon, 4.6) if icon else ""
        return f'<h3 class="bh">{ic}<span>{self.t(title)}</span><span class="sp"></span>{self.crit_pills(crit)}</h3>'

    def role(self, r: str) -> str:
        return f'<span class="role {ROLE_CLS[r]}">{esc(r)}</span>'

    def arrow_svg(self, w: float = 6, h: float = 3, cls: str = "") -> str:
        return (f'<svg style="width:{w}mm;height:{h}mm" viewBox="0 0 {w} {h}" aria-hidden="true">'
                f'<path d="M0.2 {h / 2}H{w - 0.5}" stroke="#5c5650" stroke-width="0.3" fill="none" marker-end="url(#ah)"/></svg>')

    def down_svg(self, h: float = 5) -> str:
        return (f'<svg style="width:3mm;height:{h}mm" viewBox="0 0 3 {h}" aria-hidden="true">'
                f'<path d="M1.5 0.2V{h - 0.4}" stroke="#5c5650" stroke-width="0.3" fill="none" marker-end="url(#ah)"/></svg>')

    def stack_svg(self, pages: float, w: float, h: float) -> str:
        """문서 더미(C18 stack 의 인쇄판). 높이가 쪽수에 비례(600쪽 = h)."""
        depth = 3.0                                   # 윗면의 깊이(비스듬히 본 종이)
        pile = max(2.0, min(h - depth - 0.5, pages / 600 * (h - depth - 0.5)))
        x0, pw = 0.5, w - depth - 1
        bottom = h - 0.3
        top = bottom - pile
        out = [f'<path d="M{x0} {top}L{x0 + depth} {top - depth}H{x0 + depth + pw}L{x0 + pw} {top}Z" fill="#f6f4f1" stroke="#3d3935" stroke-width="0.25"/>',
               f'<path d="M{x0 + pw} {top}L{x0 + pw + depth} {top - depth}V{bottom - depth}L{x0 + pw} {bottom}Z" fill="#e9e4dc" stroke="#3d3935" stroke-width="0.25"/>',
               f'<rect x="{x0}" y="{top}" width="{pw}" height="{pile}" fill="#ffffff" stroke="#3d3935" stroke-width="0.3"/>']
        step = 0.9
        y = top + step
        while y < bottom - 0.4:
            out.append(f'<path d="M{x0 + 0.3} {y:.2f}H{x0 + pw - 0.3}" stroke="#c9c3be" stroke-width="0.15"/>')
            y += step
        return (f'<svg style="width:{w}mm;height:{h}mm" viewBox="0 0 {w} {h}" aria-hidden="true">{"".join(out)}</svg>')

    def check_box(self, on: bool) -> str:
        mark = '<path d="M0.8 1.9L1.6 2.7L3 1.0" stroke="#ffffff" stroke-width="0.45" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        return (f'<svg style="width:3.6mm;height:3.6mm" viewBox="0 0 3.8 3.8" aria-hidden="true">'
                f'<rect x="0.2" y="0.2" width="3.4" height="3.4" fill="{"#3d3935" if on else "#ffffff"}" stroke="#161616" stroke-width="0.25"/>'
                f'{mark if on else ""}</svg>')

    def tile(self, t: dict, cls: str = "") -> str:
        sub = f'<p class="sub">{self.t(t["sub"])}</p>' if t.get("sub") else ""
        return (f'<div class="tile {cls}"><p class="big"><span class="num">{self.t(t["value"])}</span>'
                f'<span class="u">{self.t(t.get("unit", ""))}</span></p><p class="cap">{self.t(t["label"])}</p>{sub}</div>')

    def shot(self, name: str, w_mm: float, hero: bool = False, marks: list | None = None, zones: list | None = None,
             extra: str = "") -> str:
        cls = self.img_cls(name)
        h_mm = w_mm / self.aspect(name)
        inner = []
        for m in marks or []:
            inner.append(f'<span class="dot" style="left:{m["x"] * 100:.1f}%;top:{m["y"] * 100:.1f}%">{m["n"]}</span>')
        for z in zones or []:
            below = {"below": ' style="top:auto;bottom:-4.8mm"', "left": ' style="top:-0.35mm;left:-5mm"'}.get(z.get("chip", ""), "")
            inner.append(f'<span class="zone" style="left:{z["x"] * 100:.1f}%;top:{z["y"] * 100:.1f}%;width:{z["w"] * 100:.1f}%;'
                         f'height:{z["h"] * 100:.1f}%"><span class="zn"{below}>{esc(z["n"])}</span></span>')
        return (f'<div class="shot {cls}{" hero" if hero else ""}" role="img" style="width:{w_mm:.1f}mm;height:{h_mm:.1f}mm;{extra}">'
                f'{"".join(inner)}</div>')

    # 쪽 틀 -----------------------------------------------------------------
    def rail(self, cur: int) -> str:
        items = []
        for i, p in enumerate(self.pages):
            on = " on" if i + 1 == cur else ""
            items.append(f'<li class="it{on}"><span class="n">{i + 1}</span><span>{esc(p["topic"])}</span></li>')
        return f'<ul class="rail" aria-label="활용 내용 및 설명의 쪽 구성">{"".join(items)}</ul>'

    def footer(self, no: int) -> str:
        marks = self.crit_marks.get(no, {})
        pills = "".join(f'<span class="cp {"on" if c in marks else "off"}">{c}</span>' for c in CRITERIA)
        return (f'<footer class="ft"><span>{esc(self.c["footer_name"])}</span>'
                f'<span class="crit"><span class="lab">{self.lab("crit_footer")}</span>{pills}</span>'
                f'<span class="pgno">{no} / {self.total}</span></footer>')

    def frame(self, rows: list[tuple[str, str, str, str]], grid_rows: str) -> str:
        f = self.c["form"]
        cells = [f'<div class="th l">{esc(f["head"][0])}</div><div class="th">{esc(f["head"][1])}</div>']
        for i, (lcls, lhtml, rcls, rhtml) in enumerate(rows):
            last = " last" if i == len(rows) - 1 else ""
            cells.append(f'<div class="lc {lcls}{last}">{lhtml}</div><div class="rc {rcls}{last}">{rhtml}</div>')
        return f'<div class="frame" style="grid-template-rows:{grid_rows}">{"".join(cells)}</div>'

    def page(self, no: int, frame: str, first: bool = False) -> str:
        title = f'<h1 class="doctitle">{esc(self.c["form"]["doc_title"])}</h1>' if first else ""
        return f'<section class="page" id="pg{no}" data-no="{no}">{title}{frame}{self.footer(no)}</section>'

    def cont_left(self, no: int) -> str:
        f = self.c["form"]["body"]
        return (f'<p class="cont">{esc(f["cont"])}</p><p class="topic">{esc(self.pages[no - 1]["topic"])}</p>{self.rail(no)}')

    def body_head(self, no: int, headline: str | None) -> str:
        tag = f'<p class="tag">{no}. {esc(self.pages[no - 1]["topic"])}</p>'
        hl = f'<h2 class="hl">{self.t(headline)}</h2>' if headline else ""
        return f'<div>{tag}{hl}</div>'

    # 1쪽 -------------------------------------------------------------------
    def p1(self) -> str:
        f = self.c["form"]
        idt = self.identity
        guide = lambda s: f'<span class="guide-in">{esc(s)}</span>'  # noqa: E731
        dept = esc(idt["소속부서"]) if idt else guide(f["dept"]["guide"])
        name = esc(idt["성명"]) if idt else guide(f["name"]["guide"])
        opts = "".join(f'<span class="o{" on" if idt and idt["출품구분"] == o else ""}">'
                       f'{self.check_box(bool(idt and idt["출품구분"] == o))}{circled(esc(o))}</span>' for o in f["kind"]["options"])
        title = (f'<p class="title-main">{self.t(self.c["title"]["main"])}</p>'
                 f'<p class="title-sub">{self.t(self.c["title"]["sub"])}</p>')
        tl = self.c["tools"]
        tools = ('<div class="tools">' + "".join(f'<span class="k">{self.t(x["label"])}</span><span class="v">{self.t(x["text"])}</span>'
                                                 for x in tl["lines"])
                 + f'</div><p class="mut toolnote">{self.t(tl["note"])}</p>')
        b = f["body"]
        gl = "".join(f'{esc(g["text"])}<span class="go">{ARROW}{self.t(g["go"])}</span>' for g in b["guide"])
        left6 = (f'<p>{esc(b["label"])}</p><p class="guide">{esc(b["guide_head"])}</p><p class="guide">{gl}</p>{self.rail(1)}')
        rows = [
            ("", esc(f["dept"]["label"]), "", dept),
            ("", esc(f["name"]["label"]), "", name),
            ("", esc(f["kind"]["label"]), "", f'<div class="check">{opts}</div>'),
            ("", esc(f["title"]["label"]), "", title),
            ("", f'{esc(f["tools"]["label"])}<span class="guide">{esc(f["tools"]["guide"])}</span>', "", tools),
            ("top", left6, "body", self.p1_body()),
        ]
        return self.page(1, self.frame(rows, "auto auto auto auto auto auto 1fr"), first=True)

    def p1_body(self) -> str:
        b = self.pages[0]["blocks"]
        intro = "".join(f'<span class="k">{self.t(x["label"])}</span><span>{self.t(x["text"])}</span>' for x in b["intro"])
        fl = b["flow"]
        pages = self.num("{{fact:hanwha_summary_pages}}")
        FH = 22
        n0 = (f'<div class="node" style="width:40mm"><div class="fig" style="height:{FH}mm;gap:1mm;align-items:flex-end">{self.stack_svg(pages, 17, FH)}'
              f'<span class="big" style="padding-bottom:1mm">{self.t("{{fact:hanwha_summary_pages}}")}<span class="u">쪽</span></span></div>'
              f'<p class="lab">{self.t(fl["nodes"][0]["label"])}</p><p class="sub">{self.t(fl["nodes"][0]["sub"])}</p></div>')
        sw = FH * self.aspect("summary")
        n1 = (f'<div class="node" style="width:{sw + 2:.1f}mm"><div class="fig" style="height:{FH}mm">{self.shot("summary", sw, hero=True)}</div>'
              f'<p class="lab">{self.t(fl["nodes"][1]["label"])}</p><p class="sub">{self.t(fl["nodes"][1]["sub"])}</p></div>')
        tw = FH * self.aspect("talk_preview")
        n2 = (f'<div class="node" style="width:32mm"><div class="fig" style="height:{FH}mm">{self.shot("talk_preview", tw)}</div>'
              f'<p class="lab">{self.t(fl["nodes"][2]["label"])}</p><p class="sub">{self.t(fl["nodes"][2]["sub"])}</p></div>')
        arr = lambda s: f'<div class="arr"><p class="t">{self.t(s)}</p>{self.arrow_svg(9, 3)}</div>'  # noqa: E731
        flow = f'<div class="p1-flow">{n0}{arr(fl["arrows"][0])}{n1}{arr(fl["arrows"][1])}{n2}</div>'
        op = b["open"]
        openl = (f'<p class="openl">{self.ic("monitor-cog", 4.6)}<b>{self.t(op["label"])}</b>'
                 f'<a href="{esc(self.links_ok[0])}">{esc(self.links_ok[0])}</a></p>')
        tiles = f'<div class="tiles" style="grid-template-columns:repeat({len(b["tiles"])},1fr)">' + "".join(self.tile(t) for t in b["tiles"]) + "</div>"
        cards = []
        for cd in b["cards"]:
            pgs = self.crit_pages(cd["crit"])
            go = f'{self.lab("crit_go")} {ARROW} ' + ", ".join(str(p) for p in pgs) + "쪽" if pgs else ""
            if not pgs:
                self.errors.append(f"1쪽 기준 카드 {cd['crit']}: 주된 근거 블록(crit 의 *)이 있는 쪽이 없음")
            cards.append(f'<div class="ccard"><div class="h"><span class="n">{esc(cd["crit"])}</span><span class="go">{go}</span></div>'
                         f'<p>{self.t(cd["text"])}</p></div>')
        return (self.body_head(1, None)
                + f'<p class="p1-lead">{self.t(b["lead"])}</p>'
                + f'<div class="p1-intro">{intro}</div>'
                + f'<div>{self.bh(fl["head"], fl.get("crit"))}{flow}{openl}</div>'
                + tiles
                + f'<div>{self.bh(b["cards_head"])}<div class="p1-cards">{"".join(cards)}</div></div>'
                + f'<p class="caution">{self.ic("info", 3.6)}<span>{self.t(b["caution"])}</span></p>')

    # 2쪽 -------------------------------------------------------------------
    def org(self, code: str) -> str:
        return self.t("{{fact:org_names." + code + "}}")

    def p2_body(self) -> str:
        b = self.pages[1]["blocks"]
        fa = b["facts"]
        chips = "".join(f'<div class="c"><p class="k">{self.t(c["label"])}</p><p class="v">{self.t(c["value"])}</p></div>' for c in fa["chips"])
        w = b["why"]
        pages = self.num(w[0]["value"])
        c1 = (f'<div class="wcard"><p class="t"><span class="i">1</span>{self.t(w[0]["title"])}</p>'
              f'<div style="display:flex;align-items:flex-end;gap:1mm">{self.stack_svg(pages, 18, 24)}'
              f'<p class="big" style="font-size:22pt">{self.t(w[0]["value"])}<span class="u">{self.t(w[0]["unit"])}</span></p></div>'
              f'<p>{self.t(w[0]["caption"])}</p><p class="sm mut">{self.t(w[0]["note"])}</p></div>')
        rows = []
        for code in ORGS3:
            q = self.t("{{fact:simple_uw_questions_by_org." + code + ".period_question}}").replace("수술", "<u>수술</u>")
            rows.append(f'<div class="qrow"><p class="o"><b>{self.org(code)}</b></p>'
                        f'<p class="sm mut">{self.t("{{fact:simple_uw_product_short." + code + "}}")}</p><p>{q}</p></div>')
        c2 = (f'<div class="wcard"><p class="t"><span class="i">2</span>{self.t(w[1]["title"])}</p>'
              f'<p class="sm mut">{self.t(w[1]["caption"])}</p>{"".join(rows)}<p class="sm" style="font-weight:600">{self.t(w[1]["tag"])}</p></div>')
        names = "".join(f'<div class="ncard"><span class="o">{self.org(code)}</span>'
                        f'{self.t("{{fact:example_cancer_surgery_names." + code + "}}")}</div>' for code in ORGS3)
        c3 = (f'<div class="wcard"><p class="t"><span class="i">3</span>{self.t(w[2]["title"])}</p>'
              f'<p class="sm mut">{self.t(w[2]["caption"])}</p>{names}</div>')
        q = b["quote"]
        quote = (f'<div class="quote"><p class="q">{self.t(q["text"])}</p><p class="w"><span class="chip paper">{self.lab("gist")}</span>'
                 f'{self.t(q["who"])}<span class="sp" style="flex:1"></span>{self.crit_pills(q.get("crit"))}</p></div>')
        notes = "".join(f'<p class="sm mut">{self.t(n)}</p>' for n in b["notes"])
        nd = b["needs"]
        cols = []
        for c in nd["cols"]:
            tag = f'<p class="sm" style="margin-top:auto"><span class="badge-um" style="white-space:normal;line-height:1.3">{self.t(c["tag"])}</span></p>' if c.get("tag") else ""
            cue = ""
            if c.get("cue"):
                cue = (f'<div class="cue">{self.shot(c["cue"]["img"], 41)}<p class="sm mut">{self.t(c["cue"]["note"])}</p></div>')
            cols.append(f'<div class="need"><p class="ask">{self.t(c["ask"])}</p><div class="down">{self.down_svg(5)}</div>'
                        f'<div class="card"><p class="tab">{self.ic(c["icon"], 5)}{self.t(c["tab"])} {self.lab("tab_suffix")}</p><p>{self.t(c["text"])}</p>{tag}{cue}</div></div>')
        return (self.body_head(2, b["headline"])
                + f'<p class="band"><span class="k">{self.t(b["situation"]["label"])}</span><span>{self.t(b["situation"]["text"])}</span></p>'
                + f'<div>{self.bh(fa["head"], fa.get("crit"))}<div class="p2-chips">{chips}</div><p class="sm mut" style="margin-top:0.8mm">{self.t(fa["note"])}</p></div>'
                + f'<div>{self.bh(b["why_head"])}<div class="p2-why">{c1}{c2}{c3}</div></div>'
                + quote + f'<div>{notes}</div>'
                + f'<div>{self.bh(nd["head"], nd.get("crit"))}<div class="p2-needs">{"".join(cols)}</div>'
                + f'<p class="sm mut" style="margin-top:1.2mm">{self.t(nd["cue_go"])}</p></div>')

    # 3쪽 -------------------------------------------------------------------
    def p3_body(self) -> str:
        b = self.pages[2]["blocks"]
        st = b["steps"]
        steps = []
        for i, s in enumerate(st["items"]):
            roles = "".join(self.role(r) for r in s["roles"])
            big = (f'<span class="bg">{self.t(s["big"])}<span class="u">{self.t(s["big_unit"])}</span></span>' if s.get("big") else "")
            icon = self.ic(s["icon"], 5) if s.get("icon") else ""
            steps.append(f'<div class="step{" hero" if s.get("hero") else ""}"><span class="no">{i + 1}</span>'
                         f'<div><p class="nm">{self.t(s["name"])}{roles}</p><p class="tx">{self.t(s["text"])}</p>'
                         f'<p class="tl">{self.t(s["tool"])}</p></div><div class="ri">{icon}{big}</div></div>')
        us = b["users"]
        ucards = []
        for u in us["items"]:
            img = ""
            if u.get("img"):
                img = (f'<div style="display:flex;gap:2mm;align-items:flex-end;margin-top:1mm">{self.shot(u["img"], 24 * self.aspect(u["img"]))}'
                       f'<span class="chip line">{self.t(u["img_note"])}</span></div>')
            ucards.append(f'<div class="ucard"><p class="t">{self.t(u["title"])}</p><p>{self.t(u["text"])}</p>{img}</div>')
        cd = b["cond"]
        cond = (f'<div class="ucard" style="background:var(--kp-paper);border-color:var(--kp-paper)"><p class="t">{self.t(cd["head"])}</p>'
                f'<p>{self.t(cd["text"])}</p><p class="sm mut" style="margin-top:0.6mm">{self.t(cd["note"])}</p></div>')
        sh = b["shot"]
        widths = {"cut_head_a": 112, "cut_head_b": 144}
        rws = []
        for r in sh["rows"]:
            rws.append(f'<div class="hrow"><span class="hn">{esc(r["n"])}</span><div>{self.shot(r["img"], widths[r["img"]])}'
                       f'<p class="sm hl2">{self.t(r["label"])}</p></div></div>')
        shot = f'<div class="hrows">{"".join(rws)}</div>'
        od = b["order"]
        nodes = []
        for i, o in enumerate(od["items"]):
            tabs = "".join(f'<span class="chip line">{self.t(x)}</span>' for x in o["tabs"])
            nodes.append(f'<div class="nd"><p class="nm"><span class="no">{i + 1}</span>{self.t(o["name"])}</p>'
                         f'<div class="tabs">{tabs}</div><p>{self.t(o["text"])}</p></div>')
        order = f'<div class="order">{(chr(10)).join(nodes[:1])}' + "".join(
            f'<div class="ar">{self.arrow_svg(4, 3)}</div>{n}' for n in nodes[1:]) + "</div>"
        legend = (f'<p class="legendline">{self.role("AI")}{self.role("코드")}{self.role("사람")}<span>{self.t(b["legend"])}</span></p>')
        return (self.body_head(3, b["headline"]) + legend
                + f'<div class="p3-grid"><div>{self.bh(st["head"], st.get("crit"))}<div class="ladder">{"".join(steps)}</div></div>'
                + f'<div>{self.bh(us["head"], us.get("crit"))}<div style="display:flex;flex-direction:column;gap:1.8mm">{"".join(ucards)}{cond}</div></div></div>'
                + f'<div>{self.bh(self.L.get("head_shot", ""))}{shot}</div>'
                + f'<div>{self.bh(od["head"], od.get("crit"))}{order}</div>')

    # 4쪽 -------------------------------------------------------------------
    def p4_body(self) -> str:
        b = self.pages[3]["blocks"]
        fl = b["flow"]
        W, H = 150.0, 186.0
        LX = [0, 30, 60, 90, 120]
        heads = "".join(f'<div class="lane-head" style="left:{x}mm;top:0;width:30mm"><span class="ci">{self.ic(l["icon"], 5)}</span>'
                        f'<span class="n">{self.t(l["name"])}</span><span class="s">{self.t(l["sub"])}</span></div>'
                        for x, l in zip(LX, fl["lanes"]))
        boxes: list[str] = []
        lines: list[str] = []

        def bx(lane: int, y: float, h: float, text: str, cls: str = "auto", x_off: float = 1, w: float = 28) -> None:
            boxes.append(f'<div class="bx {cls}" style="left:{LX[lane] + x_off}mm;top:{y}mm;width:{w}mm;height:{h}mm">{self.t(text)}</div>')

        def nb(lane: int, y: float, label: str, cls: str = "") -> None:
            boxes.append(f'<span class="nb {cls}" style="left:{LX[lane] - 1.6}mm;top:{y - 3.6}mm">{esc(label)}</span>')

        def ln(d: str, red: bool = False, dash: bool = False) -> None:
            col = "#da291c" if red else "#3d3935"
            mk = "ah-r" if red else "ah"
            da = ' stroke-dasharray="1 0.8"' if dash else ""
            lines.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{0.9 if red else 0.3}"{da} marker-end="url(#{mk})"/>')

        # 1 매일 시장 동향: 주 흐름과 별개라 얇은 띠로 구분한다
        y = 21
        boxes.append(f'<div class="band1" style="left:0;top:{y - 2.4}mm;width:{W}mm;height:16.6mm"></div>')
        boxes.append(f'<div class="bx plain note1" style="left:1mm;top:{y}mm;width:57mm;height:11mm">{self.t(fl["t1_note"])}</div>')
        bx(2, y, 11, fl["t1a"]); bx(3, y, 14, fl["t1b"]); bx(4, y, 11, fl["t1c"])
        nb(2, y, "1")
        ln(f"M89 {y + 5.5}H90.6"); ln(f"M119 {y + 5.5}H120.6")
        # 2 수집과 추출 실행
        y = 39
        bx(0, y, 11, fl["t2a"], "hum"); bx(2, y, 11, fl["t2b"])
        nb(0, y, "2")
        ln(f"M29 {y + 5.5}H60.6")
        # 3 AI 와 코드
        y3 = 55
        for i, (txt, cls) in enumerate(zip(fl["t3"], ("chipai", "chipcode", "chipai"))):
            bx(3, y3 + i * 8.5, 6, txt, cls)
            if i:
                ln(f"M105 {y3 + i * 8.5 - 2.5}V{y3 + i * 8.5 - 0.2}")
        nb(3, y3, "3")
        ln(f"M75 50V{y3 + 3}H90.6")
        # 4 확률 분기
        dy = 83
        dcx, dhw, dhh = 105, 12, 7
        diamond = (f'<path d="M{dcx} {dy}L{dcx + dhw} {dy + dhh}L{dcx} {dy + 2 * dhh}L{dcx - dhw} {dy + dhh}Z" fill="#ffffff" stroke="#3d3935" stroke-width="0.35"/>'
                   f'<text x="{dcx}" y="{dy + dhh + 1.2}" text-anchor="middle" font-size="3.4" font-weight="600" fill="#161616">{self.t(fl["t4d"])}</text>')
        ln(f"M105 {y3 + 2 * 8.5 + 6}V{dy - 0.3}")
        nb(3, dy, "4")
        bx(4, dy + 1, 12, fl["t4hi"])
        ln(f"M{dcx + dhw} {dy + dhh}H120.6")
        boxes.append(f'<div class="bx redt" style="left:61mm;top:{dy - 0.2}mm;width:28mm;height:6mm">{self.t(fl["t4mid"])}</div>')
        lines.append(f'<path d="M{dcx - dhw} {dy + dhh}H62.2" fill="none" stroke="#da291c" stroke-width="0.9"/>'
                     f'<path d="M63.2 {dy + dhh - 1.8}L59.6 {dy + dhh}L63.2 {dy + dhh + 1.8}Z" fill="#da291c"/>')
        bx(1, dy + 1, 12, fl["t5a"], "hum")
        bx(3, dy + 2 * dhh + 3, 14, fl["t4lo"], "plain", x_off=1.5, w=27)
        ln(f"M105 {dy + 2 * dhh}V{dy + 2 * dhh + 2.7}")
        # 5 검수 결과 저장
        y5 = 121
        bx(4, y5, 11, fl["t5b"])
        nb(1, dy + 1, "5")
        ln(f"M45 {dy + 13}V{y5 + 5.5}H120.6")
        # 6 주간 마감
        y6 = 138
        bx(2, y6, 11, fl["t6a"]); bx(4, y6, 11, fl["t6b"])
        nb(2, y6, "6")
        ln(f"M89 {y6 + 5.5}H120.6")
        # 7 화면 배포와 실무자의 확인
        y7 = 156
        bx(2, y7, 11, fl["t7a"])
        bx(0, y7 - 2, 15, fl["t7b"], "goal")
        nb(2, y7, "7")
        ln(f"M135 {y6 + 11}V{y7 + 5.5}H89.4")
        ln(f"M61 {y7 + 5.5}H29.4")
        # 8 상시: 기준값과 사전
        y8 = 175
        bx(1, y8, 11, fl["t8a"], "dash"); bx(4, y8, 11, fl["t8b"], "dash")
        nb(1, y8, fl["always"], "al")
        ln(f"M59 {y8 + 5.5}H120.6", dash=True)
        seps = "".join(f'<path d="M{x} 18V{H}" stroke="#c9c3be" stroke-width="0.25" stroke-dasharray="0.8 0.8"/>' for x in LX[1:])
        svg = (f'<svg style="position:absolute;left:0;top:0;width:{W}mm;height:{H}mm" viewBox="0 0 {W} {H}" aria-hidden="true">'
               f'{seps}{"".join(lines)}{diamond}</svg>')
        sw = ['<span class="sw" style="border:0.35mm solid var(--kp-ink)"></span>',
              '<span class="sw" style="background:var(--kp-paper-deep)"></span>',
              '<span class="sw" style="border:0.3mm dashed var(--kp-ink)"></span>',
              '<span class="sw" style="border-bottom:0.9mm solid var(--kp-red);height:1.6mm"></span>']
        legend = '<p class="legend4">' + "".join(f'<span>{s}{self.t(t)}</span>' for s, t in zip(sw, fl["legend"])) + "</p>"
        lanes = f'<div class="lane-wrap" style="width:{W}mm;height:{H}mm">{svg}{heads}{"".join(boxes)}</div>'
        wk = b["week"]
        days = "".join(f'<span class="d{" sun" if i == 6 else ""}">{self.t(d)}</span>' for i, d in enumerate(wk["days"]))
        def dots(on: list[bool]) -> str:
            cs = "".join(f'<circle cx="{1.6 + i * 3.2:.1f}" cy="1.6" r="1.1" fill="{"#3d3935" if o else "#ffffff"}" stroke="#3d3935" stroke-width="0.25"/>'
                         for i, o in enumerate(on))
            return f'<svg style="width:22.4mm;height:3.2mm;flex:none" viewBox="0 0 22.4 3.2" aria-hidden="true">{cs}</svg>'
        week = (f'<div>{self.bh(wk["head"], wk.get("crit"), "일정")}<div class="week">{days}</div>'
                f'<p class="wline">{dots([True] * 7)}<span>{self.t(wk["daily"])}</span></p>'
                f'<p class="wline">{dots([False] * 6 + [True])}<span>{self.t(wk["sun"])}</span></p>'
                f'<p class="wline">{self.ic("person", 4.4)}<span>{self.t(wk["manual"])}</span></p></div>')
        rc = b["receipt"]
        items = "".join(f'<p class="r"><span>{self.t(i["label"])}</span><span class="nw">{self.t(i["won"])}</span></p>' for i in rc["items"])
        teeth = "".join(f"L{x + 1.5:.1f} 2.2L{x + 3:.1f} 0" for x in range(0, 60, 3))
        receipt = (f'<div>{self.bh(rc["head"], rc.get("crit"), "비용")}<div class="receipt">{items}'
                   f'<p class="tot"><b>{self.t(rc["total_label"])}</b><span class="big">{self.t(rc["total"])}</span></p></div>'
                   f'<svg style="width:100%;height:2.4mm;display:block" viewBox="0 0 60 2.4" preserveAspectRatio="none" aria-hidden="true">'
                   f'<path d="M0 0{teeth}" fill="#ffffff" stroke="#c9c3be" stroke-width="0.25"/></svg></div>')
        return (self.body_head(4, b["headline"])
                + f'<div>{self.bh(fl["head"], fl.get("crit"))}{legend}<div style="margin-top:1.8mm">{lanes}</div></div>'
                + f'<div class="p4-bottom">{week}{receipt}</div>'
                + f'<p class="sm mut">{self.t(b["note"])}</p>')

    # 5쪽 -------------------------------------------------------------------
    def pair_text(self, code: str) -> tuple[bool, str]:
        pair = self.fact(f"example_cancer_surgery.pairs.{code}") or {}
        items = pair.get("items", [])
        same = [i["item"] for i in items if i.get("verdict") == "동일"]
        diff = [i for i in items if i.get("verdict") != "동일"]
        org = self.org(code)
        if not diff:
            return True, f"{org}: {esc(', '.join(same))} 동일"
        d = ", ".join(f'{esc(i["item"])} 상이(우체국 {esc(i["ours"])}, {org} {esc(i["peer"])})' for i in diff)
        return False, f"{org}: {esc(', '.join(same))} 동일, {d}"

    def p5_body(self) -> str:
        b = self.pages[4]["blocks"]
        tb = b["table"]
        fg = tb["fig"]
        pg_chips = "".join(f'<span class="chip paper">{self.org(c)} {self.t("{{fact:example_cancer_surgery.orgs." + c + ".doc_page}}")}쪽</span>'
                           for c in ORGS3)
        conv = ('<svg style="width:28mm;height:13mm" viewBox="0 0 28 13" aria-hidden="true">'
                + "".join(f'<rect x="0" y="{0.6 + i * 4.2}" width="9" height="3" fill="#f6f4f1" stroke="#c9c3be" stroke-width="0.25"/>'
                          f'<path d="M9 {2.1 + i * 4.2}L15.4 6.5" stroke="#5c5650" stroke-width="0.3" fill="none"/>' for i in range(3))
                + '<rect x="15.6" y="3.4" width="12.2" height="6.2" fill="#ffffff" stroke="#3d3935" stroke-width="0.4"/></svg>')
        figs = [
            f'<div style="display:flex;flex-direction:column;gap:0.6mm;align-items:center">{pg_chips}</div>',
            (f'<p class="big" style="font-size:15pt">{self.t(fg["pay"])}<span class="u">{self.t(fg["pay_unit"])}</span></p>'
             f'<p class="sm">{self.t(fg["pay_sub"])}</p><p class="sm mut">{self.t(fg["pay_note"])}</p>'),
            (f'<div style="position:relative">{conv}<span style="position:absolute;left:15.6mm;top:3.4mm;width:12.2mm;height:6.2mm;'
             f'display:flex;align-items:center;justify-content:center;font-size:8pt;font-weight:600;line-height:1.05;text-align:center">{self.t(fg["target"])}</span></div>'
             f'<p class="sm mut">{self.lab("conv_note")}</p>'),
            f'{self.shot("cut_copy_button", 27)}<p class="sm mut">{self.t(fg["copy"])}</p>',
            f'{self.shot("cut_pending_chip", 27)}<p class="sm mut">{self.t(fg["pending"])}</p>',
        ]
        hdr = "".join(f'<span class="h{" after" if i == 2 else ""}">{self.t(c)}</span>' + ('<span></span>' if i == 1 else "")
                      for i, c in enumerate(tb["cols"]))
        cells = [hdr]
        for i, r in enumerate(tb["rows"]):
            if i == 0:
                cells.append(f'<p class="grp">{self.t(tb["groups"][0])}</p>')
            if i == 3:
                cells.append(f'<p class="grp red">{self.t(tb["groups"][1])}</p>')
            cells.append(f'<div class="rh"><span class="no">{i + 1}</span>{self.ic(r["icon"], 4.6)}<span class="nm">{self.t(r["name"])}</span></div>'
                         f'<div class="bf">{self.t(r["before"])}</div><div class="ar">{self.arrow_svg(3.4, 3)}</div>'
                         f'<div class="af{" hero" if r.get("hero") else ""}"><p>{self.role(r["role"])} {self.t(r["after"])}</p>'
                         f'<p class="hm"><b>{self.lab("human")}</b> {self.t(r["human"])}</p></div><div class="fg">{figs[i]}</div>')
        table = f'<div class="p5t">{"".join(cells)}</div>'
        sh = b["shot"]
        legend = "".join(f'<span class="nw"><b class="red">{m["n"]}</b> {self.t(m["label"])}</span>' for m in sh["marks"])
        results = []
        for code in ORGS3[1:]:
            same, txt = self.pair_text(code)
            mark = ('<svg style="width:3.6mm;height:3.6mm;flex:none;margin-top:0.4mm" viewBox="0 0 4 4"><circle cx="2" cy="2" r="1.6" fill="#3d3935"/></svg>' if same else
                    '<svg style="width:3.6mm;height:3.6mm;flex:none;margin-top:0.4mm" viewBox="0 0 4 4"><circle cx="2" cy="2" r="1.6" fill="#fff" stroke="#3d3935" stroke-width="0.35"/><path d="M0.9 3.1L3.1 0.9" stroke="#3d3935" stroke-width="0.35"/></svg>')
            results.append(f'<div class="res{" same" if same else ""}">{mark}<span>{txt}</span></div>')
        mid = (f'<div>{self.shot(sh["img"], 150, marks=sh["marks"])}'
               f'<p class="sm" style="display:flex;gap:4mm;margin-top:0.8mm">{legend}<span class="mut">{self.t(sh["caption"])}</span></p></div>'
               f'<div class="p5-res">{"".join(results)}<p class="sm mut">{self.t(sh["result_note"])}</p></div>')
        ef = b["effect"]
        effect = (f'<div>{self.bh(self.L.get("effect", ""), ef.get("crit"), "걸리는 시간")}<div class="effect">'
                  f'<div class="side"><p class="k">{self.t(ef["now_label"])}</p><p class="big">{self.t(ef["now_value"])}</p>'
                  f'<p>{self.t(ef["now_sub"])}</p><p class="sm mut">{self.t(ef["now_note"])}</p></div>'
                  f'<div class="ar" style="display:flex;align-items:center;justify-content:center">{self.arrow_svg(6, 3)}</div>'
                  f'<div class="side"><p class="k">{self.t(ef["tool_label"])}</p>'
                  f'<p class="tl"><span class="badge-um">{self.t(ef["tool_badge"])}</span> {self.t(ef["tool_text"])}</p>'
                  f'<p class="struct"><b>{self.t(ef["tool_struct"])}</b><br><span class="sm mut">{self.t(ef["tool_struct_note"])}</span></p>'
                  f'<p class="sm mut">{self.t(ef["tool_note"])}</p>'
                  f'<p class="sm" style="text-align:right;font-weight:600;margin-top:auto">{self.t(ef["go"])}</p></div></div></div>')
        return (self.body_head(5, b["headline"])
                + f'<p class="band"><span>{self.t(b["situation"])}</span></p>'
                + f'<div>{self.bh(tb["head"], tb.get("crit"))}{table}</div>'
                + f'<div>{self.bh(sh["head"], sh.get("crit"))}{mid}</div>'
                + effect)

    # 6쪽 -------------------------------------------------------------------
    def ring(self, value: float, total: float, hatch: float = 0, d: float = 22) -> str:
        r = 8.6
        c = 2 * 3.14159265 * r
        a = c * value / total if total else 0
        hb = c * hatch / total if total else 0
        segs = [f'<circle cx="10" cy="10" r="{r}" fill="none" stroke="#f6f4f1" stroke-width="2"/>',
                f'<circle cx="10" cy="10" r="{r}" fill="none" stroke="#3d3935" stroke-width="2" stroke-dasharray="{a:.2f} {c:.2f}" transform="rotate(-90 10 10)"/>']
        if hb:
            segs.append(f'<circle cx="10" cy="10" r="{r}" fill="none" stroke="url(#hf)" stroke-width="2" '
                        f'stroke-dasharray="0 {a:.2f} {hb:.2f} {c:.2f}" transform="rotate(-90 10 10)"/>')
        return f'<svg style="width:{d}mm;height:{d}mm" viewBox="0 0 20 20" aria-hidden="true">{"".join(segs)}</svg>'

    def p6_body(self) -> str:
        b = self.pages[5]["blocks"]
        ro = b["roles"]
        chips = "".join(f'<div class="rchip">{self.role(c["role"])}<span>{self.t(c["text"])}</span></div>' for c in ro["chips"])
        ex1 = "".join(f'<span class="in">{self.t(x)}</span>' for x in ro["ex1_in"])
        roles = (f'<div>{self.bh(ro["head"], ro.get("crit"))}{chips}'
                 f'<div class="exband"><p class="lb">{self.t(ro["ex1_label"])}</p><div class="exrow">{ex1}<span class="via">{self.lab("code_reads")}</span>{self.arrow_svg(4, 3)}'
                 f'<span class="out">{self.t(ro["ex1_out"])}</span></div></div>'
                 f'<div class="exband"><p class="lb">{self.t(ro["ex2_label"])}</p><div class="exrow"><span class="in bad">{self.t(ro["ex2_in"])}</span>'
                 f'{self.arrow_svg(4, 3)}<span class="out">{self.t(ro["ex2_out"])}</span></div><p class="sm mut" style="margin-top:0.6mm">{self.t(ro["ex2_mid"])}</p></div></div>')
        g = b["gauge"]
        re_pct = self.num("{{fact:calibration_reextract_band.wrong_caught_pct}}")
        rv_pct = self.num("{{fact:calibration_review_band_pct}}")
        lo = self.num("{{fact:verify_reextract_threshold}}")
        hi = self.num("{{fact:verify_confirm_threshold}}")
        stack = (f'<svg style="width:100%;height:6mm;display:block" viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true">'
                 f'<rect x="0" y="0" width="{re_pct:.2f}" height="6" fill="#3d3935"/>'
                 f'<rect x="{re_pct:.2f}" y="0" width="{rv_pct:.2f}" height="6" fill="url(#hf)" stroke="#3d3935" stroke-width="0.2"/>'
                 f'<rect x="0" y="0" width="100" height="6" fill="none" stroke="#3d3935" stroke-width="0.3"/></svg>')
        scale = (f'<div style="position:relative;height:9.6mm;margin-top:1.2mm">'
                 f'<div style="position:absolute;left:0;right:0;top:0;height:3mm;background:linear-gradient(90deg,var(--kp-paper-deep) 0 {lo * 100:.0f}%,var(--kp-paper) {lo * 100:.0f}% {hi * 100:.0f}%,var(--kp-paper-deep) {hi * 100:.0f}%)"></div>'
                 + "".join(f'<div style="position:absolute;left:{v * 100:.1f}%;top:-1mm;height:5mm;border-left:0.35mm dashed var(--kp-ink)"></div>'
                           f'<span class="sm" style="position:absolute;left:{v * 100:.1f}%;top:4mm;transform:translateX(-50%);font-weight:600">{self.t(t)}</span>'
                           for v, t in ((lo, "{{fact:verify_reextract_threshold|f2}}"), (hi, "{{fact:verify_confirm_threshold|f2}}")))
                 + "".join(f'<span class="sm mut" style="position:absolute;left:{x:.1f}%;top:-4.4mm;transform:translateX(-50%);white-space:nowrap">{self.t(z)}</span>'
                           for x, z in ((lo * 50, g["zones"][0]), ((lo + hi) * 50, g["zones"][1]), ((hi + 1) * 50, g["zones"][2])))
                 + '</div>')
        gauge = (f'<div>{self.bh(g["head"], g.get("crit"), "확률 산정 모델")}'
                 f'<p class="sm" style="font-weight:600">{self.t(g["stack_label"])}</p>{stack}'
                 f'<p class="sm" style="display:flex;justify-content:space-between;margin-top:0.4mm"><span>{self.t(g["seg_re"])}</span><span>{self.t(g["seg_rv"])}</span></p>'
                 f'<div style="display:flex;align-items:center;gap:2.4mm;margin:1.4mm 0 5mm"><span class="gbig">{self.t(g["big"])}</span>'
                 f'<span style="font-weight:600">{self.t(g["big_label"])}</span></div>{scale}'
                 f'<p style="margin-top:1mm">{self.t(g["line"])}</p><p class="sm" style="margin-top:0.6mm">{self.t(g["chip"])}</p>'
                 f'<p class="sm mut">{self.t(g["scope"])}</p></div>')
        on = b["onto"]
        names = "".join(f'<div class="ncard" style="margin-bottom:1mm"><span class="o">{self.org(c)}</span>'
                        f'{self.t("{{fact:example_cancer_surgery_names." + c + "}}")}</div>' for c in ORGS3)
        conv = ('<svg style="width:8mm;height:100%;display:block" viewBox="0 0 8 30" preserveAspectRatio="none" aria-hidden="true">'
                '<path d="M0 5L7.6 15M0 15H7.6M0 25L7.6 15" stroke="#5c5650" stroke-width="0.3" fill="none"/></svg>')
        onto = (f'<div>{self.bh(on["head"], on.get("crit"), "관계 그래프")}'
                f'<div style="display:grid;grid-template-columns:1fr 8mm 20mm;align-items:stretch"><div>{names}</div>{conv}'
                f'<div style="display:flex;flex-direction:column;justify-content:center"><div style="border:0.5mm solid var(--kp-ink);padding:1.4mm 1mm;text-align:center">'
                f'<p style="font-weight:600;line-height:1.2">{self.t(on["target"])}</p><p class="sm mut">{self.t(on["target_sub"])}</p></div></div></div>'
                f'<p class="sm" style="margin:0.6mm 0 1.4mm"><span class="chip paper" style="white-space:normal">{self.t(on["chip"])}</span></p>'
                f'<div class="tiles" style="grid-template-columns:1fr 1fr">{"".join(self.tile(t, "t6") for t in on["tiles"])}</div></div>')
        gd = b["gold"]
        rings = []
        for r in gd["rings"]:
            v = self.num(r["value"]); tot = self.num(r["total"]); hv = self.num(r["hatch"]) if r.get("hatch") else 0
            val = self.t(r["value"]) if not r.get("hatch") else self.t("{{fact:goldset_epost_benefit.auto_match}}") + "+" + self.t(r["hatch"])
            lg = f'<p class="sm mut">{self.t(r["legend"])}</p>' if r.get("legend") else ""
            rings.append(f'<div><div style="position:relative;display:inline-block">{self.ring(v, tot, hv)}'
                         f'<span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:8.5pt">'
                         f'{val}/{self.t(r["total"])}</span></div><p class="lb">{self.t(r["label"])}</p>{lg}</div>')
        bars = []
        for br in gd["bars"]:
            m, it = self.num(br["match"]), self.num(br["items"])
            bars.append(f'<div class="hbar"><span>{self.t(br["label"])}</span><span class="trk"><span class="fil" style="width:{m / it * 100 if it else 0:.1f}%"></span></span>'
                        f'<span class="num">{self.t(br["match"])}/{self.t(br["items"])}</span></div>')
        us = gd["unscored"]
        bars.append(f'<div class="hbar"><span>{self.t(us["label"])}</span><span class="trk dash"></span><span class="badge-um">{self.t(us["badge"])}</span></div>'
                    f'<p class="sm mut" style="text-align:right">{self.t(us["text"])}</p>')
        gold = (f'<div>{self.bh(gd["head"], gd.get("crit"), "자동 확정")}<div class="rings">{"".join(rings)}</div>'
                f'<p class="sm mut" style="margin-top:0.8mm">{self.t(gd["ring_note"])}</p>'
                f'<p class="sm" style="font-weight:600;margin-top:1.6mm">{self.t(gd["weak_head"])}</p>{"".join(bars)}</div>')
        tm = b["team"]
        team = self.p6_team(tm)
        return (self.body_head(6, b["headline"])
                + f'<div class="p6g">{roles}{gauge}{onto}{gold}</div>' + team)

    def p6_team(self, tm: dict) -> str:
        W, H = 96.0, 60.0

        def node(x, y, w, h, title, sub, cls=""):
            style = {"me": "background:var(--kp-paper-deep)", "cc": "border:0.5mm solid var(--kp-ink);background:#fff",
                     "": "border:0.25mm solid var(--kp-ink);background:#fff", "gh": "border:0.25mm dashed var(--kp-ink);background:#fff"}[cls]
            return (f'<div style="position:absolute;left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;{style};display:flex;flex-direction:column;'
                    f'align-items:center;justify-content:center;text-align:center;line-height:1.2;padding:0.6mm">'
                    f'<b style="font-size:9pt">{self.t(title)}</b><span class="sm mut">{self.t(sub)}</span></div>')
        parts = [
            node(33, 0, 30, 9, tm["me"], tm["me_sub"], "me"),
            node(0, 15, 29, 11, tm["gem"], tm["gem_sub"]),
            node(33.5, 15, 29, 11, tm["cc"], tm["cc_sub"], "cc"),
            node(67, 15, 29, 11, tm["ag"], tm["ag_sub"]),
        ]
        for i, s in enumerate(tm["subs"]):
            parts.append(node(21 + i * 18.5, 33, 17, 9, s["name"], s["sub"]))
        parts.append(node(0, 51, W, 9, tm["gh"], tm["gh_sub"], "gh"))
        ink = 'stroke="#3d3935" stroke-width="0.3" fill="none"'
        lines = [f'<path d="M48 9V11.5H14.5V14.7M48 11.5V14.7M48 11.5H81.5V14.7" {ink} marker-end="url(#ah)"/>',
                 f'<path d="M48 26V29.3H29.5V32.7M48 29.3V32.7M48 29.3H66.5V32.7" {ink} marker-end="url(#ah)"/>',
                 f'<path d="M14.5 26V50.7M81.5 26V50.7" {ink} stroke-dasharray="0.8 0.6" marker-end="url(#ah)"/>']
        svg = (f'<svg style="position:absolute;left:0;top:0;width:{W}mm;height:{H}mm" viewBox="0 0 {W} {H}" aria-hidden="true">{"".join(lines)}</svg>')
        loop = ('<svg style="width:4mm;height:4mm;flex:none" viewBox="0 0 6 6" aria-hidden="true"><path d="M4.9 2.2A2.3 2.3 0 1 0 4.9 4" '
                'stroke="#161616" stroke-width="0.6" fill="none" marker-end="url(#ah)"/></svg>')
        ring = (f'<div style="position:absolute;left:21mm;top:43.6mm;width:55mm;display:flex;gap:1mm;align-items:center;justify-content:center;'
                f'font-size:8.5pt;font-weight:600">{loop}{self.t(tm["ring"])}</div>')
        chart = f'<div style="position:relative;width:{W}mm;height:{H}mm">{svg}{"".join(parts)}{ring}</div>'
        tiles = "".join(self.tile(t) for t in tm["tiles"])
        return (f'<div>{self.bh(tm["head"], tm.get("crit"))}<div style="display:grid;grid-template-columns:{W}mm 1fr;gap:4mm">{chart}'
                f'<div><p class="sm mut" style="margin-bottom:0.8mm">{self.t(tm["asof"])}</p><div class="tiles" style="grid-template-columns:1fr 1fr">{tiles}</div></div></div></div>')

    # 7쪽 -------------------------------------------------------------------
    def org_progress(self, pg: dict) -> str:
        """목표 회사 수만큼의 점을 진행 상태(화면 반영, 시트 적재, 추출 완료, 예정)로 나눠 그린다. 수는 사실 자료에서 센다."""
        targets = int(self.num("{{fact:comparison_targets_loaded.targets}}"))
        site = int(self.num("{{fact:comparison_targets_loaded.site}}"))
        sheet = int(self.num("{{fact:comparison_targets_loaded.sheet}}"))
        ext = len(self.fact("next_load_orgs.names") or [])
        counts = {"site": site, "sheet": sheet - site, "ext": ext, "plan": targets - sheet - ext}
        if min(counts.values()) < 0 or sum(counts.values()) != targets:
            self.errors.append(f"목표 회사 진행 현황의 수가 맞지 않음: {counts}")
        look = {"site": '<circle cx="{cx}" cy="3" r="2.3" fill="#3d3935"/>',
                "sheet": '<circle cx="{cx}" cy="3" r="2.3" fill="url(#hf)" stroke="#3d3935" stroke-width="0.4"/>',
                "ext": '<circle cx="{cx}" cy="3" r="2.1" fill="#ffffff" stroke="#3d3935" stroke-width="0.9"/>',
                "plan": '<circle cx="{cx}" cy="3" r="2.1" fill="#ffffff" stroke="#8a847d" stroke-width="0.4" stroke-dasharray="0.7 0.6"/>'}
        dots, x = [], 3.0
        for st in pg["states"]:
            for _ in range(counts[st["key"]]):
                dots.append(look[st["key"]].format(cx=f"{x:.1f}"))
                x += 6.2
            x += 2.4
        W = x
        svg = f'<svg style="width:{W:.1f}mm;height:6mm;flex:none" viewBox="0 0 {W:.1f} 6" aria-hidden="true">{"".join(dots)}</svg>'
        key = "".join(
            f'<span class="nw"><svg style="width:4.6mm;height:4.6mm;vertical-align:-1mm;margin-right:0.6mm" viewBox="0 0 6 6" aria-hidden="true">{look[st["key"]].format(cx="3")}</svg>'
            f'{self.t(st["label"])} <b>{counts[st["key"]]}</b></span>' for st in pg["states"])
        return (f'<div class="prog"><p class="sh">{self.t(pg["head"])}</p><div style="display:flex;align-items:center;gap:3mm">{svg}</div>'
                f'<p class="sm" style="display:flex;flex-wrap:wrap;gap:0.6mm 4.4mm;margin-top:0.6mm">{key}</p></div>')

    def p7_body(self) -> str:
        b = self.pages[6]["blocks"]
        og = b["orgs"]
        nodes = []
        for n in og["nodes"]:
            bd = f'<span class="bd">{self.t(n["badge"])}</span>' if n.get("badge") else ""
            nodes.append(f'<div class="nd {n["state"]}">{bd}{self.ic(n["icon"], 5.4)}<p class="nm">{self.t(n["name"])}</p><p class="sb">{self.t(n["sub"])}</p></div>')
        flow = '<div class="orgflow">' + nodes[0] + "".join(f'<div class="ar">{self.arrow_svg(4, 3)}</div>{x}' for x in nodes[1:]) + "</div>"
        notes = "".join(f'<p class="sm mut">{self.t(x)}</p>' for x in og["notes"])
        tiles = f'<div class="tiles" style="grid-template-columns:1fr 1fr 1fr">{"".join(self.tile(t) for t in og["tiles"])}</div>'
        progress = self.org_progress(og["progress"])
        us = b["uses"]
        cards = "".join(f'<div class="c"><p class="nm">{self.ic(c["icon"], 5)}{self.t(c["name"])}</p><p>{self.t(c["text"])}</p>'
                        f'<p class="sm mut">{self.t(c["note"])}</p>'
                        f'<p class="tabs"><span class="sm mut">{self.t(us["tabs_label"])}</span>'
                        + "".join(f'<span class="chip line">{self.t(x)}</span>' for x in c["tabs"]) + '</p></div>' for c in us["cards"])
        lm = b["limits"]
        left = "".join(f"<li>{self.t(x)}</li>" for x in lm["left"])
        right = "".join(f"<li>{self.t(x)}</li>" for x in lm["right"])
        um = "".join(f'<p class="um"><span class="badge-um">{self.t(lm["badge"])}</span><span>{self.t(x)}</span></p>' for x in lm["unmeasured"])
        return (self.body_head(7, b["headline"])
                + f'<div>{self.bh(og["head"], og.get("crit"), "우체국")}<div style="padding-top:2.6mm">{flow}</div><div style="margin:1.2mm 0">{notes}</div>{progress}{tiles}</div>'
                + f'<div>{self.bh(us["head"], us.get("crit"))}<div class="ucards">{cards}</div>'
                + f'<p class="sm" style="margin-top:1.4mm;border:0.25mm dashed var(--border-default);padding:1mm 1.6mm;color:var(--fg-muted)">{self.t(us["out"])}</p></div>'
                + f'<div>{self.bh(lm["head"], lm.get("crit"))}<div class="lims"><div><p class="sh">{self.t(lm["left_head"])}</p><ul>{left}</ul></div>'
                + f'<div><p class="sh">{self.t(lm["right_head"])}</p><ul>{right}</ul></div></div>'
                + f'<p class="sh" style="font-weight:600;margin:1.2mm 0 0.8mm">{self.t(lm["unmeasured_head"])}</p>{um}</div>')

    # 8쪽 -------------------------------------------------------------------
    def p8_body(self) -> str:
        b = self.pages[7]["blocks"]
        rc = b["record"]
        rows = []
        for r in rc["rows"]:
            if r.get("state"):
                st = self.c["states"][r["state"]]["on" if self.states[r["state"]] else "off"]
                pill = st["pill"]
            else:
                pill = r["pill"]
            pcls = "chip ink" if pill == "반영" else ("chip line" if pill in ("일부 반영", "진행 중") else "chip dash")
            rows.append(f'<tr><td class="a">{self.t(r["ask"])}</td><td class="d">{self.t(r["done"])}</td>'
                        f'<td class="s"><span class="{pcls}">{esc(pill)}</span></td></tr>')
        head = "".join(f"<th>{self.t(c)}</th>" for c in rc["cols"])
        done = sum(1 for r in rc["rows"] if (self.c["states"][r["state"]]["on" if self.states[r["state"]] else "off"]["pill"] if r.get("state") else r["pill"]) in ("반영", "일부 반영"))
        gold = (self.num("{{fact:goldset_epost_benefit.auto_match}}") + self.num("{{fact:goldset_epost_benefit.manual_match}}")
                + self.num("{{fact:goldset_hanwha_benefit.match}}"))
        gold_all = self.num("{{fact:goldset_epost_benefit.items}}") + self.num("{{fact:goldset_hanwha_benefit.items}}")
        calc = {"opinions": f"{done}/{len(rc['rows'])}", "goldset": f"{int(gold)}/{int(gold_all)}"}
        ev = "".join(self.tile({**t, "value": calc[t["calc"]] if t.get("calc") else t["value"]}, "ev") for t in rc["evidence"])
        evidence = f'<div><p class="sh evh">{self.t(rc["evidence_head"])}</p><div class="tiles" style="grid-template-columns:repeat({len(rc["evidence"])},1fr)">{ev}</div></div>'
        return (self.body_head(8, b["headline"])
                + f'<div>{self.bh(rc["head"], rc.get("crit"), "users")}'
                + f'<div class="rec-none"><span class="zero">{self.lab("no_record")}</span><p>{self.t(rc["none"])}</p></div>'
                + f'<div style="margin-top:1.6mm">{evidence}</div>'
                + f'<p style="margin:2mm 0 1mm">{self.t(rc["have"])}</p>'
                + f'<table class="rtab"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
                + f'<p style="margin-top:1.6mm;font-weight:600">{self.t(rc["next"])}</p></div>')

    def output_body(self) -> str:
        o = self.c["output"]
        links = "".join(f'<div class="l">{self.ic(l["icon"], 5)}<span class="nm">{self.t(l["name"])}</span>'
                        f'<span><a href="{esc(l["url"])}">{esc(l["url"])}</a><br><span class="nt">{self.t(l["note"])}</span></span></div>'
                        for l in o["links"])
        play = ('<svg class="play" viewBox="0 0 10 10" aria-hidden="true"><circle cx="5" cy="5" r="4.6" fill="#161616" fill-opacity="0.72"/>'
                '<path d="M4 3L7.2 5L4 7z" fill="#ffffff"/></svg>')
        vids = "".join(f'<div class="s"><div class="im {self.img_cls(v["img"])}" role="img">{play}<span class="vl">{self.t(v["len"])}</span></div>'
                       f'<p class="lb">{self.t(v["label"])}</p></div>'
                       for v in o.get("videos", []))
        video = f'<div>{self.bh(o["videos_head"])}<div class="shots vids">{vids}</div></div>' if vids else ""
        return f'<div>{self.bh(o["head"])}<div class="links">{links}</div></div>' + video

    # 읽히는 폭(mm): 확대 컷 안의 글자가 인쇄 크기에서 7pt 안팎이 되도록 컷마다 정한다(본문 칸의 폭은 150mm)
    CUT_W = {"cut_kpi": 78, "cut_gate": 126, "cut_cover": 150, "cut_insight": 114, "cut_talk": 68}
    FULL_W = {"summary": 60, "tab_gate": 68, "cancer_surgery": 68, "tab_insight": 68, "talk_preview": 36, "tab_graph": 84}

    def shot_row(self, i: int, s: dict) -> str:
        """화면 하나: 전체 캡처(모양)와 확대 컷(글자)을 짝으로 보이고 설명 한 줄을 붙인다."""
        full = self.shot(s["img"], self.FULL_W[s["img"]])
        fullw = f'<div class="pf"><span class="nb2">{i + 1}</span>{full}</div>'
        title = f'<div class="st"><p class="lb">{i + 1}. {self.t(s["label"])}</p><p class="sm mut">{self.t(s["text"])}</p></div>'
        if not s.get("cut"):
            # 확대 컷이 없으면 설명을 전체 캡처 오른쪽에 둔다
            return f'<div class="srow"><div class="pair">{fullw}{title}</div></div>'
        cw = self.CUT_W[s["cut"]]
        cut = self.shot(s["cut"], cw)
        if cw + self.FULL_W[s["img"]] <= 142:
            return f'<div class="srow"><div class="pair">{fullw}<div class="pc">{cut}</div></div>{title}</div>'
        # 확대 컷이 넓으면 전체 캡처 오른쪽에 설명을 두고, 확대 컷은 그 아래에 본문 폭으로 놓는다(캡처 옆을 비워 두지 않는다)
        return f'<div class="srow"><div class="pair">{fullw}{title}</div><div class="pc wide">{cut}</div></div>'

    def shots_page(self, group: list[int]) -> str:
        o = self.c["output"]
        rows = "".join(self.shot_row(i, o["shots"][i]) for i in group)
        return f'<div>{self.bh(o["shots_head"])}<div class="srows">{rows}</div></div>'

    # 조립 -----------------------------------------------------------------
    def pages_html(self) -> str:
        out = [self.p1()]
        bodies = {2: self.p2_body, 3: self.p3_body, 4: self.p4_body, 5: self.p5_body, 6: self.p6_body, 7: self.p7_body}
        for no in range(2, self.n_body):
            rows = [("top", self.cont_left(no), "body", bodies[no]())]
            out.append(self.page(no, self.frame(rows, "auto 1fr")))
        f = self.c["form"]["output"]
        no = self.n_body
        rows = [("top", self.cont_left(no), "body", self.p8_body()),
                ("top", f'<p>{esc(f["label"])}</p><p class="guide">{esc(f["guide"])}</p>', "body", self.output_body())]
        out.append(self.page(no, self.frame(rows, "auto auto 1fr")))
        for k, group in enumerate(self.shot_groups):
            body = self.shots_page(group)
            if k == len(self.shot_groups) - 1:
                body += f'<p class="sm mut">{self.t(self.c["output"]["shots_note"])}</p>'
            rows = [("top", f'<p class="cont">{esc(f["cont"])}</p><p class="guide">{esc(f["guide"])}</p>', "body", body)]
            out.append(self.page(self.n_body + 1 + k, self.frame(rows, "auto 1fr")))
        return "\n".join(out)


# ---------------------------------------------------------------------------
# 빌드
# ---------------------------------------------------------------------------
def tokens_from_deck(tpl: Path) -> str:
    m = re.search(r":root\s*\{[^{}]*\}", tpl.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"덱 틀에서 :root 토큰을 찾지 못했습니다: {tpl}")
    return m.group(0)


def check_links(doc: str, allowed: list[str]) -> list[str]:
    stripped = doc
    for u in allowed:
        stripped = stripped.replace(f'<a href="{esc(u)}">', "<a>")
    return deck_build.check_external(stripped)


def build_html(content_path: Path = HERE / "content.json", facts_path: Path | None = None, refs_path: Path = DECK / "refs.json",
               deck_path: Path = DECK / "content" / "_deck.json", fonts_css: Path | None = None, tpl_path: Path = HERE / "tpl.html",
               identity_path: Path | None = None, snapshot_dir: Path = ROOT / "data" / "snapshot",
               image_dirs: list[Path] | None = None, strict: bool = False) -> tuple[str, dict]:
    content = json.loads(content_path.read_text(encoding="utf-8"))
    facts_path = facts_path or ROOT / "presentation_animation" / "facts.json"
    fonts_css = fonts_css or ROOT / "proto_src" / "fonts" / "fonts_v4.css"
    facts = json.loads(facts_path.read_text(encoding="utf-8"))["facts"]
    refs = deck_build.load_refs(refs_path)
    deck = json.loads(deck_path.read_text(encoding="utf-8"))
    identity = load_identity(identity_path, content["form"]["kind"]["options"])
    form = Form(content, facts, refs, deck, identity, snapshot_parents(snapshot_dir),
                image_dirs or [HERE / "assets", DECK / "assets"])
    pages = form.pages_html()
    errors = form.errors + form.ctx.errors
    if errors:
        raise SystemExit("빌드를 멈춥니다:\n  " + "\n  ".join(errors))
    digits = digits_outside(content)
    css_images = "\n".join(
        f'.im-{re.sub(r"[^A-Za-z0-9_-]", "_", n)}{{background-image:url(data:image/jpeg;base64,'
        f'{base64.b64encode(form.images[n].read_bytes()).decode("ascii")})}}' for n in form.img_used)
    tpl = tpl_path.read_text(encoding="utf-8")
    doc = (tpl.replace("__HTML_TITLE__", esc(content["html_title"]))
              .replace("<!--__FONT_NOTICE__-->", deck_build.FONT_NOTICE)
              .replace("/*__FONT_FACES__*/", deck_build.font_faces(fonts_css))
              .replace("/*__TOKENS__*/", tokens_from_deck(DECK / "tpl.html"))
              .replace("/*__IMAGES__*/", css_images)
              .replace("<!--__SPRITE__-->", P.sprite())
              .replace("<!--__PAGES__-->", pages))
    leftovers = re.findall(r"__[A-Z_]+__|\{\{[^}]*\}\}", doc)
    if leftovers:
        raise SystemExit(f"채우지 못한 자리: {leftovers[:5]}")
    hits = check_links(doc, form.links_ok)
    if hits:
        raise SystemExit("외부 요청이 될 주소:\n  " + "\n  ".join(hits))
    if strict and digits:
        raise SystemExit("자리 표시 밖의 숫자:\n  " + "\n  ".join(digits))
    info = {"pages": form.total, "images": list(form.img_used), "digits": digits, "facts_used": form.ctx.used_facts,
            "states": form.states, "identity": identity is not None}
    return doc, info


LAYOUT_JS = """() => {
  const out = [];
  const PT8 = 8 * 96 / 72 - 0.05;
  for (const pg of document.querySelectorAll('.page')) {
    const no = pg.dataset.no;
    const pr = pg.getBoundingClientRect();
    if (pg.scrollHeight > pg.clientHeight + 1) out.push(`${no}쪽: 쪽 높이를 넘침`);
    for (const rc of pg.querySelectorAll('.rc, .lc')) {
      if (rc.scrollHeight > rc.clientHeight + 1) out.push(`${no}쪽: 칸 안 내용이 넘침(${Math.round(rc.scrollHeight - rc.clientHeight)}px)`);
      if (rc.scrollWidth > rc.clientWidth + 1) out.push(`${no}쪽: 칸 안 내용이 옆으로 넘침`);
    }
    const walker = document.createTreeWalker(pg, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      if (!n.textContent.trim()) continue;
      const el = n.parentElement;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (el.closest('svg')) {
        const svg = el.closest('svg'); const vb = svg.viewBox.baseVal; const r = svg.getBoundingClientRect();
        const scale = vb && vb.width ? r.width / vb.width : 1;
        const sz = parseFloat(el.getAttribute('font-size') || fs) * scale;
        if (sz < PT8) out.push(`${no}쪽: 8pt 미만 글자(그림 안) "${n.textContent.trim().slice(0, 20)}"`);
        continue;
      }
      if (fs < PT8) out.push(`${no}쪽: 8pt 미만 글자 ${(fs * 72 / 96).toFixed(1)}pt "${n.textContent.trim().slice(0, 20)}"`);
      const range = document.createRange(); range.selectNodeContents(n);
      for (const r of range.getClientRects()) {
        if (r.right > pr.right + 0.5 || r.bottom > pr.bottom + 0.5) { out.push(`${no}쪽: 쪽 밖으로 나간 글 "${n.textContent.trim().slice(0, 20)}"`); break; }
      }
      // 칸(.rc, .lc) 밖으로 나간 글
      const cell = el.closest('.rc, .lc');
      if (cell) {
        const cr = cell.getBoundingClientRect();
        for (const r of range.getClientRects()) {
          if (r.right > cr.right + 0.5 || r.bottom > cr.bottom + 0.5) { out.push(`${no}쪽: 칸 밖으로 나간 글 "${n.textContent.trim().slice(0, 20)}"`); break; }
        }
      }
    }
  }
  return out;
}"""


def render_pdf(html_path: Path, pdf_path: Path) -> list[str]:
    """HTML 을 A4 PDF 로. 넘침과 작은 글자 목록을 돌려준다. 외부 요청은 막고 있으면 멈춘다."""
    from playwright.sync_api import sync_playwright
    external: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})

        def route(r):
            if r.request.url.startswith(("file:", "data:", "blob:")):
                r.continue_()
            else:
                external.append(r.request.url)
                r.abort()
        page.route("**/*", route)
        page.goto(html_path.resolve().as_uri())
        page.emulate_media(media="print")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        problems = page.evaluate(LAYOUT_JS)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True,
                 margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()
    if external:
        raise SystemExit(f"외부 요청: {external[:3]}")
    return problems


def previews(pdf_path: Path, out_dir: Path, dpi: int = 110) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("page-*.png"):
        old.unlink()
    exe = shutil.which("pdftoppm")
    if not exe:
        raise SystemExit("pdftoppm 이 없어 미리보기를 만들지 못했습니다")
    subprocess.run([exe, "-r", str(dpi), "-png", str(pdf_path), str(out_dir / "page")], check=True)
    return sorted(out_dir.glob("page-*.png"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identity", default=None, help="소속부서, 성명, 출품구분이 든 JSON(없으면 안내 문구를 넣은 견본)")
    ap.add_argument("--out", default=None, help="PDF 경로(주지 않으면 PDF 를 만들지 않는다)")
    ap.add_argument("--html", default=None, help="HTML 경로(기본: --out 옆 같은 이름의 .html)")
    ap.add_argument("--preview", default=None, help="쪽마다 PNG 미리보기를 만들 폴더(--out 필요)")
    ap.add_argument("--facts", default=None)
    ap.add_argument("--content", default=str(HERE / "content.json"))
    ap.add_argument("--snapshot", default=str(ROOT / "data" / "snapshot"))
    ap.add_argument("--strict", action="store_true", help="자리 표시 밖 숫자, 채우지 못한 자리, 넘침과 8pt 미만 글자를 오류로")
    a = ap.parse_args()
    doc, info = build_html(Path(a.content), Path(a.facts) if a.facts else None,
                           identity_path=Path(a.identity) if a.identity else None, snapshot_dir=Path(a.snapshot), strict=a.strict)
    html_path = Path(a.html) if a.html else (Path(a.out).with_suffix(".html") if a.out else HERE / "out" / "form.html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_bytes(doc.encode("utf-8"))
    kind = "제출본(identity 값 넣음)" if info["identity"] else "견본(안내 문구)"
    print(f"{html_path} {html_path.stat().st_size:,} 바이트, {info['pages']}쪽, {kind}, 사진 {len(info['images'])}장, 외부 요청 0")
    print("주간 마감 자료로 고른 글: " + ", ".join(f"{k}={'반영' if v else '미반영'}" for k, v in info["states"].items()))
    if info["digits"]:
        print(f"자리 표시 밖의 숫자 {len(info['digits'])}곳")
        for d in info["digits"]:
            print("  " + d)
    if a.out:
        problems = render_pdf(html_path, Path(a.out))
        print(f"{a.out} 만듦, 넘침과 작은 글자 {len(problems)}건")
        for p_ in problems:
            print("  " + p_)
        if a.preview:
            files = previews(Path(a.out), Path(a.preview))
            print(f"미리보기 {len(files)}장: {a.preview}")
        if a.strict and problems:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
