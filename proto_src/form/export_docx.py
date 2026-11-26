#!/usr/bin/env python3
"""작품설명서를 편집 가능한 Word 파일(.docx)로 내보낸다. 제출본은 PDF 이고, 이 파일은 사용자가 글을 직접 고칠 때 쓰는 편집용이다.

실행(리포 루트에서, python-docx 와 playwright 가 든 파이썬):
    PYTHONPATH=src .venv/bin/python proto_src/form/export_docx.py --identity local/submission/identity.json --out local/submission/작품설명서.docx
    (--identity 를 주지 않으면 성명과 소속 자리에 양식의 안내 문구가 든 견본을 만든다)
    버전 2(4쪽 판)는 --content proto_src/form/content_v2.json 을 더한다. 내용 파일의 "variant" 가 "v2" 이면 여섯 절 구성으로 내보낸다.

- 글은 build.py 의 해석 함수(Form.t, content.json 의 자리 표시)로 PDF 와 같은 문구를 만든다. 문구를 새로 쓰지 않는다.
  쪽 참조({{pg:…}})만 Word 에서 쪽이 달라지므로 절 번호와 이름으로 바꾼다.
- 글(문단, 글머리표, 표)은 Word 의 글자로, 도해와 화면 캡처는 그림으로 넣는다. 그림으로 넣은 도해 블록 아래에는 소제목과 핵심 문장을
  글자로도 적는다. 그림에는 대체 텍스트를 넣는다.
- 도해 그림은 견본 HTML(성명과 소속 없음)을 playwright 로 열어 요소를 2배 배율로 찍은 것이다. 그림 파일은 임시 폴더(--work)에만 둔다.
- 성명, 소속부서 값은 이 파일 어디에도 출력하지 않는다.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build as B  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.style import WD_STYLE_TYPE  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Mm, Pt, RGBColor, Twips  # noqa: E402

FONT = "맑은 고딕"
RED = RGBColor(0xB9, 0x22, 0x17)        # 덱 틀의 --kp-red-600(PDF 의 절 제목 색)
INK = RGBColor(0x16, 0x16, 0x16)
MUTED = RGBColor(0x5C, 0x56, 0x50)
PAPER = "F6F4F1"                          # --kp-paper
PAPER_DEEP = "E9E4DC"                     # --kp-paper-deep 에 가까운 채움
TW_PER_MM = 1440 / 25.4
COL_L = round(30 * TW_PER_MM)             # 항목 열 약 30mm
COL_R = round(150 * TW_PER_MM)            # 작성내용 열 약 150mm
CELL_PAD_TW = 100                         # 칸 좌우 안쪽 여백(twips)
IMG_MAX_MM = 144.0                        # 작성내용 칸 안쪽 폭(150mm - 여백) 이하
RIGHT_INNER_MM = 146.0


# ---------------------------------------------------------------------------
# 글 풀기
# ---------------------------------------------------------------------------
def plain(h: str) -> str:
    """build.py 가 만든 HTML 조각을 보이는 글로. 화살표 그림은 → 로, <br> 은 공백으로."""
    h = h.replace(B.ARROW, "→")
    h = re.sub(r"<br\s*/?>", " ", h)
    h = re.sub(r'<span class="pb">[^<]*</span>', "", h)
    h = re.sub(r"<[^>]+>", "", h)
    return re.sub(r"[ \t]+", " ", htmllib.unescape(h)).strip()


def make_form(identity_path: Path | None, content_path: Path | None = None) -> B.Form:
    content = json.loads((content_path or B.HERE / "content.json").read_text(encoding="utf-8"))
    facts = json.loads((B.ROOT / "presentation_animation" / "facts.json").read_text(encoding="utf-8"))["facts"]
    refs = B.deck_build.load_refs(B.DECK / "refs.json")
    deck = json.loads((B.DECK / "content" / "_deck.json").read_text(encoding="utf-8"))
    identity = B.load_identity(identity_path, content["form"]["kind"]["options"])
    return B.Form(content, facts, refs, deck, identity, B.snapshot_parents(B.ROOT / "data" / "snapshot"),
                  [B.HERE / "assets", B.DECK / "assets"])


class Text:
    """content.json 의 문구를 PDF 와 같게 풀되, 쪽 참조는 절 참조로 바꾼다."""

    NAMED_REF = {"p7.limits"}          # 절 번호 뒤에 블록 이름을 함께 적는 참조

    def __init__(self, form: B.Form):
        self.f = form
        self.pages = form.pages

    def sec_ref(self, key: str) -> str:
        sec = int(re.match(r"p(\d+)", key).group(1))
        if key in self.NAMED_REF:
            blk = key.split(".", 1)[1]
            return f"{sec}절 {self.pages[sec - 1]['blocks'][blk]['head']}"
        return f"{sec}절"

    def refs(self, s: str) -> str:
        s = s.replace("{{pg:shots}}쪽 이후의 화면 캡처", "생성물의 화면 캡처")
        return re.sub(r"\{\{pg:([^{}]+)\}\}쪽?", lambda m: self.sec_ref(m.group(1).strip()), s)

    def __call__(self, s: Any) -> str:
        if s is None:
            return ""
        return plain(self.f.t(self.refs(str(s))))

    def crit_secs(self, name: str) -> list[int]:
        """평가기준의 주된 근거 블록(crit 의 *)이 있는 절 번호."""
        out: set[int] = set()

        def walk(o: Any, sec: int) -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "crit":
                        for c in (v if isinstance(v, list) else [v]):
                            if c.endswith("*") and c.rstrip("*") == name:
                                out.add(sec)
                    else:
                        walk(v, sec)
            elif isinstance(o, list):
                for v in o:
                    walk(v, sec)

        for bid, keys in B.BLOCK_CRIT.items():
            sec = B.sec_of(bid)
            for key in keys:
                walk(self.pages[sec - 1]["blocks"].get(key, {}), sec)
        return sorted(out)


# ---------------------------------------------------------------------------
# 그림 찍기(견본 HTML 의 요소)
# ---------------------------------------------------------------------------
RECT_JS = """([blk, sels]) => {
  const root = document.querySelector(`[data-blk="${blk}"]`);
  if (!root) return null;
  // 선택자 "기준@N|하위": 기준과 맞는 요소 중 N 번째(0부터)의 하위 요소
  const pick = s => {
    if (!s) return root;
    const [head, sub] = s.split('|');
    const [base, n] = head.split('@');
    const el = n === undefined ? root.querySelector(base) : root.querySelectorAll(base)[Number(n)];
    return el && sub ? el.querySelector(sub) : el;
  };
  const els = sels.map(pick);
  if (els.some(e => !e)) return null;
  els[0].scrollIntoView({block: 'start'});
  window.scrollBy(0, -24);
  let L = 1e9, T = 1e9, R = -1e9, Bt = -1e9;
  for (const el of els) {
    const r = el.getBoundingClientRect();
    L = Math.min(L, r.left); T = Math.min(T, r.top); R = Math.max(R, r.right); Bt = Math.max(Bt, r.bottom);
  }
  return {L, T, R, B: Bt, text: els.map(e => (e.innerText || '').replace(/\\s+/g, ' ').trim()).join(' ')};
}"""


class Shooter:
    def __init__(self, html_path: Path, out_dir: Path):
        from playwright.sync_api import sync_playwright
        self.out = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        ctx = self._browser.new_context(viewport={"width": 1000, "height": 1500}, device_scale_factor=2)
        self.page = ctx.new_page()
        self.page.goto(html_path.resolve().as_uri())
        self.page.emulate_media(media="print")
        self.page.evaluate("document.fonts.ready")
        self.page.wait_for_timeout(400)
        self.n = 0

    def shoot(self, blk: str, sels: list[str | None], pad_mm: tuple[float, float, float, float] = (1, 1, 1, 1)) -> dict:
        """블록 안의 요소(들)를 감싸는 직사각형을 2배 배율로 찍는다. pad_mm: 위, 오른쪽, 아래, 왼쪽."""
        info = self.page.evaluate(RECT_JS, [blk, sels])
        if not info:
            raise SystemExit(f"그림으로 찍을 요소를 찾지 못했습니다: {blk} {sels}")
        px = 96 / 25.4
        t, r, b, l = (v * px for v in pad_mm)
        x, y = max(0.0, info["L"] - l), max(0.0, info["T"] - t)
        w, h = info["R"] - info["L"] + l + r, info["B"] - info["T"] + t + b
        self.n += 1
        path = self.out / f"fig{self.n:02d}_{re.sub(r'[^A-Za-z0-9]+', '_', blk)}.png"
        self.page.screenshot(path=str(path), clip={"x": x, "y": y, "width": w, "height": h})
        return {"path": path, "w_mm": w / px, "h_mm": h / px, "text": info["text"]}

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()


# ---------------------------------------------------------------------------
# docx 부품
# ---------------------------------------------------------------------------
def set_fonts(rpr, name: str = FONT) -> None:
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for k in list(rf.attrib):
        del rf.attrib[k]
    for a in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn(f"w:{a}"), name)


def style_font(style, size: float, bold: bool | None = None, color: RGBColor | None = None) -> None:
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color
    set_fonts(style.element.get_or_add_rPr())


def setup_styles(doc) -> None:
    st = doc.styles
    # 문서 기본값: 글꼴(한글 포함)과 언어
    rpr_def = st.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
    set_fonts(rpr_def)
    lang = rpr_def.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr_def.append(lang)
    lang.set(qn("w:val"), "ko-KR")
    lang.set(qn("w:eastAsia"), "ko-KR")
    normal = st["Normal"]
    style_font(normal, 10, color=INK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.15

    def add(name: str, base: str = "Normal") -> Any:
        s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = st[base]
        return s

    t = add("문서 제목")
    style_font(t, 16, True, INK)
    t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.paragraph_format.space_after = Pt(8)
    t.paragraph_format.keep_with_next = True

    h1 = st["Heading 1"]                      # 절 제목
    style_font(h1, 12, True, RED)
    h1.paragraph_format.space_before = Pt(2)
    h1.paragraph_format.space_after = Pt(3)
    h1.paragraph_format.keep_with_next = False      # 왼쪽 칸의 절 제목에 걸면 LibreOffice 가 행 전체를 다음 쪽으로 넘긴다
    h1.paragraph_format.line_spacing = 1.15
    h2 = st["Heading 2"]                      # 소제목
    style_font(h2, 11, True, INK)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.paragraph_format.keep_with_next = True
    h2.paragraph_format.line_spacing = 1.15

    hl = add("쪽 제목 문장")
    style_font(hl, 13, True, INK)
    hl.paragraph_format.space_after = Pt(4)
    hl.paragraph_format.keep_with_next = True

    sm = add("보조 글")
    style_font(sm, 9, False, MUTED)
    sm.paragraph_format.space_after = Pt(2)

    cap = add("그림 설명", "보조 글")
    cap.paragraph_format.space_after = Pt(4)

    lab = add("항목 이름")
    style_font(lab, 10, True, INK)

    bl = st["List Bullet"]
    style_font(bl, 10, False, INK)
    bl.paragraph_format.space_after = Pt(1)
    bl.paragraph_format.line_spacing = 1.15


def shade(cell, fill: str) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    for old in tcpr.findall(qn("w:shd")):
        tcpr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def border_el(tag: str, sz: int, color: str) -> Any:
    e = OxmlElement(f"w:{tag}")
    e.set(qn("w:val"), "single")
    e.set(qn("w:sz"), str(sz))
    e.set(qn("w:space"), "0")
    e.set(qn("w:color"), color)
    return e


def fix_table(tbl, widths: list[int], border_sz: int = 6, border_color: str = "161616", inner_sz: int | None = None,
              cell_pad: int = CELL_PAD_TW, v_pad: int = 50, cant_split: bool = False) -> None:
    """표 폭과 열 폭을 명시하고 고정 배치, 실선 테두리, 칸 안쪽 여백을 정한다."""
    tblpr = tbl._tbl.tblPr
    for tag in ("w:tblStyle", "w:tblW", "w:tblLayout", "w:tblBorders", "w:tblCellMar", "w:tblLook"):
        for e in tblpr.findall(qn(tag)):
            tblpr.remove(e)
    tblw = OxmlElement("w:tblW")
    tblw.set(qn("w:w"), str(sum(widths)))
    tblw.set(qn("w:type"), "dxa")
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    bd = OxmlElement("w:tblBorders")
    inner = inner_sz or border_sz
    for tag, sz in (("top", border_sz), ("left", border_sz), ("bottom", border_sz), ("right", border_sz),
                    ("insideH", inner), ("insideV", inner)):
        bd.append(border_el(tag, sz, border_color))
    mar = OxmlElement("w:tblCellMar")
    for tag, v in (("top", v_pad), ("left", cell_pad), ("bottom", v_pad), ("right", cell_pad)):
        e = OxmlElement(f"w:{tag}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    # tblPr 자식 순서: tblStyle, tblpPr, tblOverlap, bidiVisual, tblStyleRowBandSize, tblStyleColBandSize, tblW, jc, tblCellSpacing,
    # tblInd, tblBorders, shd, tblLayout, tblCellMar, tblLook
    for e in (tblw, bd, lay, mar):
        tblpr.append(e)
    grid = tbl._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(w))
    for row in tbl.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = Twips(w)
        trpr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "1" if cant_split else "0")   # 바깥 표의 행은 쪽 경계에서 나뉘는 것을 허용
        trpr.insert(0, cs)


def repeat_header(row) -> None:
    trpr = row._tr.get_or_add_trPr()
    trpr.append(OxmlElement("w:tblHeader"))


class Cell:
    """칸 하나에 문단, 글머리표, 그림, 중첩 표를 차례로 넣는 도우미."""

    def __init__(self, cell, width_mm: float = RIGHT_INNER_MM):
        self.c = cell
        self.fresh = True
        self.width_mm = width_mm
        self.last_is_table = False

    def _para(self, style: str | None = None):
        if self.fresh:
            p = self.c.paragraphs[-1]
            self.fresh = False
        else:
            p = self.c.add_paragraph()
        if style:
            p.style = style
        return p

    @staticmethod
    def runs(p, segs, size: float | None = None, bold: bool | None = None, color: RGBColor | None = None) -> None:
        """segs: 글 하나 또는 (글, {b, i, size, color}) 목록."""
        if isinstance(segs, str):
            segs = [segs]
        for seg in segs:
            text, opt = (seg, {}) if isinstance(seg, str) else seg
            r = p.add_run(text)
            if opt.get("b", bold) is not None:
                r.bold = opt.get("b", bold)
            if opt.get("i"):
                r.italic = True
            sz = opt.get("size", size)
            if sz:
                r.font.size = Pt(sz)
            col = opt.get("color", color)
            if col is not None:
                r.font.color.rgb = col

    def p(self, segs, style: str | None = None, size: float | None = None, bold: bool | None = None,
          color: RGBColor | None = None, align=None, keep_next: bool = False, after: float | None = None, before: float | None = None):
        p = self._para(style)
        self.runs(p, segs, size, bold, color)
        if align is not None:
            p.alignment = align
        if keep_next:
            p.paragraph_format.keep_with_next = True
        if after is not None:
            p.paragraph_format.space_after = Pt(after)
        if before is not None:
            p.paragraph_format.space_before = Pt(before)
        self.last_is_table = False
        return p

    def h1(self, text: str):
        return self.p(text, "Heading 1")

    def h2(self, text: str, crit: Any = None):
        segs: list = [text]
        items = crit if isinstance(crit, list) else ([crit] if crit else [])
        for c in items[:2]:
            segs.append((f" [{c.rstrip('*')}]", {"size": 9.5, "color": MUTED}))
        return self.p(segs, "Heading 2")

    def headline(self, text: str):
        return self.p(text, "쪽 제목 문장")

    def small(self, segs, **kw):
        return self.p(segs, "보조 글", **kw)

    def bullet(self, segs, size: float | None = None):
        p = self._para("List Bullet")
        self.runs(p, segs, size)
        self.last_is_table = False
        return p

    def kv(self, label: str, text: str):
        return self.p([(label + "  ", {"b": True}), text])

    def image(self, path: Path, width_mm: float, alt: str, keep_next: bool = True, align=None) -> Any:
        p = self._para()
        r = p.add_run()
        pic = r.add_picture(str(path), width=Mm(min(width_mm, IMG_MAX_MM)))
        pic._inline.docPr.set("descr", alt)
        pic._inline.docPr.set("title", alt[:60])
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        if keep_next:
            p.paragraph_format.keep_with_next = True
        if align is not None:
            p.alignment = align
        self.last_is_table = False
        return p

    def images(self, items: list[tuple[Path, float, str]]) -> Any:
        """그림 여러 장을 한 줄에 놓는다(폭의 합이 칸 안쪽 폭 이하여야 한다)."""
        p = self._para()
        for i, (path, w, alt) in enumerate(items):
            if i:
                p.add_run("  ")
            pic = p.add_run().add_picture(str(path), width=Mm(w))
            pic._inline.docPr.set("descr", alt)
            pic._inline.docPr.set("title", alt[:60])
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.line_spacing = 1.0
        self.last_is_table = False
        return p

    def table(self, widths_mm: list[float], nrows: int):
        widths = [round(w * TW_PER_MM) for w in widths_mm]
        tbl = self.c.add_table(rows=nrows, cols=len(widths))
        fix_table(tbl, widths, border_sz=4, border_color="8A847D", cell_pad=70, v_pad=30, cant_split=True)
        self.fresh = True                      # 표 뒤의 빈 문단을 다음 글에 쓴다
        self.last_is_table = True
        return tbl

    def finish(self) -> None:
        if self.last_is_table and not getattr(self, "_finished", False):   # 칸은 문단으로 끝나야 한다. 표 뒤 빈 문단은 작게
            self._finished = True
            p = self.c.paragraphs[-1]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = Pt(3)
            for r in p.runs:
                r.font.size = Pt(2)
            p._p.get_or_add_pPr()
            rpr = OxmlElement("w:rPr")
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), "4")
            rpr.append(sz)
            p._p.pPr.append(rpr)


def add_field(run, instr: str) -> None:
    for kind in ("begin", None, "separate", "text", "end"):
        if kind is None:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            run._r.append(it)
        elif kind == "text":
            t = OxmlElement("w:t")
            t.text = "1"
            run._r.append(t)
        else:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            run._r.append(fc)


def add_footer(doc, name: str) -> None:
    sec = doc.sections[0]
    p = sec.footer.paragraphs[0]
    p.style = doc.styles["보조 글"]
    pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Mm(180), alignment=2)           # 오른쪽 맞춤
    p.add_run(name)
    p.add_run("\t")
    add_field(p.add_run(), "PAGE")
    p.add_run(" / ")
    add_field(p.add_run(), "NUMPAGES")


# ---------------------------------------------------------------------------
# 문서 내용
# ---------------------------------------------------------------------------
class Exporter:
    def __init__(self, form: B.Form, shooter: Shooter):
        self.form = form
        self.c = form.c
        self.t = Text(form)
        self.sh = shooter
        self.doc = Document()
        zoom = self.doc.settings.element.find(qn("w:zoom"))
        if zoom is not None and zoom.get(qn("w:percent")) is None:
            zoom.set(qn("w:percent"), "100")
        self.figs: list[str] = []           # 그림으로 넣은 블록 기록
        self.rows: list[str] = []
        setup_styles(self.doc)
        s = self.doc.sections[0]
        s.page_width, s.page_height = Mm(210), Mm(297)
        s.top_margin = s.bottom_margin = Mm(15)
        s.left_margin = s.right_margin = Mm(15)
        s.footer_distance = Mm(6)
        s.header_distance = Mm(6)
        add_footer(self.doc, self.c["footer_name"])
        cp = self.doc.core_properties
        cp.title = self.c["html_title"]
        cp.author = ""
        cp.last_modified_by = ""
        cp.comments = ""
        self.pages = form.pages
        self.table = None
        self.sec_seen: set[int] = set()

    # 표 틀 -----------------------------------------------------------------
    def start(self) -> None:
        f = self.c["form"]
        tp = self.doc.add_paragraph(f["doc_title"], style="문서 제목")
        tp.paragraph_format.space_before = Pt(0)
        self.table = self.doc.add_table(rows=1, cols=2)
        fix_table(self.table, [COL_L, COL_R])
        head = self.table.rows[0]
        repeat_header(head)
        for cell, txt in zip(head.cells, f["head"]):
            shade(cell, PAPER_DEEP)
            w = Cell(cell)
            w.p(txt, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            w.finish()

    def row(self, left_fill: bool = True, whole: bool = False) -> tuple[Cell, Cell]:
        """whole: 한 쪽에 들어가는 그림 행은 쪽 경계에서 나누지 않는다(제목만 앞 쪽에 남는 것을 막는다)."""
        r = self.table.add_row()
        trpr = r._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "1" if whole else "0")
        trpr.insert(0, cs)
        for cell, w in zip(r.cells, (COL_L, COL_R)):
            cell.width = Twips(w)
        if left_fill:
            shade(r.cells[0], PAPER)
        return Cell(r.cells[0], 28.0), Cell(r.cells[1])

    def label(self, left: Cell, text: str, guide: str | None = None) -> None:
        left.p(text, "항목 이름")
        if guide:
            left.small(guide)

    # 위쪽 다섯 행 ------------------------------------------------------------
    def top_rows(self) -> None:
        f = self.c["form"]
        idt = self.form.identity
        guide_style = {"i": True, "color": MUTED}

        l, r = self.row()
        self.label(l, f["dept"]["label"])
        r.p(idt["소속부서"] if idt else [(f["dept"]["guide"], guide_style)])
        l.finish(); r.finish()
        self.rows.append("소속부서")

        l, r = self.row()
        self.label(l, f["name"]["label"])
        r.p(idt["성명"] if idt else [(f["name"]["guide"], guide_style)])
        l.finish(); r.finish()
        self.rows.append("성명")

        l, r = self.row()
        self.label(l, f["kind"]["label"])
        for o in f["kind"]["options"]:
            on = bool(idt and idt["출품구분"] == o)
            r.p(("☑ " if on else "☐ ") + o)
        l.finish(); r.finish()
        self.rows.append("출품 구분")

        l, r = self.row()
        self.label(l, f["title"]["label"])
        r.p(self.t(self.c["title"]["main"]), size=12, bold=True)
        r.p(self.t(self.c["title"]["sub"]))
        l.finish(); r.finish()
        self.rows.append("제목")

        l, r = self.row()
        self.label(l, f["tools"]["label"], f["tools"]["guide"])
        tl = self.c["tools"]
        for x in tl["lines"]:
            r.kv(self.t(x["label"]), self.t(x["text"]))
        r.small(self.t(tl["note"]))
        l.finish(); r.finish()
        self.rows.append("활용 AI도구")

    # 본문 행 ---------------------------------------------------------------
    def sec_left(self, left: Cell, sec: int, first_row: bool) -> None:
        name = f"{sec}. {self.pages[sec - 1]['topic']}"
        if first_row:
            left.h1(name)
        else:
            left.p(name + " (계속)", "항목 이름")

    def body_row(self, sec: int, build, first: bool | None = None, whole: bool = False) -> None:
        """절의 행 하나. 절의 첫 행은 왼쪽 칸에 절 번호와 이름, 이어지는 행은 '(계속)'을 적는다."""
        l, r = self.row(whole=whole)
        first_row = sec not in self.sec_seen if first is None else first
        self.sec_seen.add(sec)
        self.sec_left(l, sec, first_row)
        build(r)
        l.finish(); r.finish()
        self.rows.append(f"{sec}. {self.pages[sec - 1]['topic']}" + ("" if first_row else " (계속)"))

    def blocks(self, sec: int) -> dict:
        return self.pages[sec - 1]["blocks"]

    def fig(self, name: str, kind: str) -> None:
        self.figs.append(f"{name}: {kind}")

    # 1절 -------------------------------------------------------------------
    def sec1(self) -> None:
        b = self.blocks(1)
        f = self.c["form"]["body"]
        t = self.t
        l, r = self.row()
        self.sec_seen.add(1)
        l.p(f["label"], "항목 이름")
        l.small(f["guide_head"])
        for g in f["guide"]:
            l.small(g["text"])
            l.p([("→ " + t(g["go"]), {"b": True, "color": RED})], size=9, after=4)
        # 오른쪽: 1절 첫 부분
        r.h1(f"1. {self.pages[0]['topic']}")
        r.headline(t(b["lead"]))
        for x in b["intro"]:
            r.kv(t(x["label"]), t(x["text"]))
        fl = b["flow"]
        r.h2(fl["head"], fl.get("crit"))
        img = self.sh.shoot("p1.flow", [".p1-flow"])
        nodes = fl["nodes"]
        cap = (f"{t(fl['head'])}: {t(nodes[0]['label'])} {t('{{fact:hanwha_summary_pages}}')}쪽({t(nodes[0]['sub'])}) → "
               f"[{t(fl['arrows'][0])}] → {t(nodes[1]['label'])}({t(nodes[1]['sub'])}) → "
               f"[{t(fl['arrows'][1])}] → {t(nodes[2]['label'])}({t(nodes[2]['sub'])})")
        r.image(img["path"], img["w_mm"], cap)
        r.p(cap, "그림 설명")
        self.fig("1절 문서에서 화면까지의 흐름", "도해")
        op = b["open"]
        r.p([(t(op["label"]) + "  ", {"b": True}), (op["file"] + "  ", {"b": True}), t(op["text"])])
        l.finish(); r.finish()
        self.rows.append("활용 내용 및 설명 / 1. 개요")

        def more(r: Cell) -> None:
            for tile in b["tiles"]:
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"])])
            r.h2(b["cards_head"])
            for cd in b["cards"]:
                secs = t.crit_secs(cd["crit"])
                go = f"{t(self.c['labels']['crit_go'])} → " + ", ".join(f"{n}절" for n in secs) if secs else ""
                r.p([(cd["crit"], {"b": True}), (f"  ({go})" if go else "", {"size": 9, "color": MUTED})], keep_next=True, after=0)
                r.p(t(cd["text"]))
            r.small(t(b["caution"]), before=4)

        self.body_row(1, more, first=False)

    # 2절 -------------------------------------------------------------------
    def sec2(self) -> None:
        b = self.blocks(2)
        t = self.t
        f = self.form

        def a(r: Cell) -> None:
            r.headline(t(b["headline"]))
            r.kv(t(b["situation"]["label"]), t(b["situation"]["text"]))
            fa = b["facts"]
            r.h2(fa["head"], fa.get("crit"))
            for c in fa["chips"]:
                r.bullet([(t(c["label"]) + ": ", {"b": True}), t(c["value"])])
            r.small(t(fa["note"]))
            r.h2(b["why_head"])
            w = b["why"]
            r.p([(f"1. {t(w[0]['title'])}", {"b": True})], keep_next=True, after=0)
            r.p([(f"{t(w[0]['value'])}{t(w[0]['unit'])}: ", {"b": True}), t(w[0]["caption"])], after=0)
            r.small(t(w[0]["note"]))
            r.p([(f"2. {t(w[1]['title'])}", {"b": True})], keep_next=True, after=0)
            r.small(t(w[1]["caption"]), after=1)
            for code in B.ORGS3:
                q = t("{{fact:simple_uw_questions_by_org." + code + ".period_question}}")
                r.bullet([(f.org(code) + " ", {"b": True}),
                          (t("{{fact:simple_uw_product_short." + code + "}}") + ": ", {"size": 9, "color": MUTED}), q])
            r.p(t(w[1]["tag"]), bold=True)
            r.p([(f"3. {t(w[2]['title'])}", {"b": True})], keep_next=True, after=0)
            r.small(t(w[2]["caption"]), after=1)
            for code in B.ORGS3:
                r.bullet([(f.org(code) + ": ", {"b": True}), t("{{fact:example_cancer_surgery_names." + code + "}}")])
            q = b["quote"]
            r.p(t(q["text"]), bold=True, before=6, after=0)
            crit = " ".join(f"[{c.rstrip('*')}]" for c in q.get("crit", [])[:2])
            r.small(f"[{t(self.c['labels']['gist'])}] {t(q['who'])} {crit}".strip())
            for n in b["notes"]:
                r.p(t(n))

        self.body_row(2, a)

        def needs(r: Cell) -> None:
            nd = b["needs"]
            r.h2(nd["head"], nd.get("crit"))
            for i, c in enumerate(nd["cols"], 1):
                r.p([(f"{i}. {t(c['ask'])}", {"b": True})], keep_next=True, after=0)
                r.p([(f"{t(c['tab'])} {t(self.c['labels']['tab_suffix'])}: ", {"b": True}), t(c["text"])])
                if c.get("tag"):
                    r.small(t(c["tag"]))
                if c.get("cue"):
                    name = c["cue"]["img"]
                    r.image(self.form.images[name], 90.0, t(c["cue"]["note"]))
                    r.small(t(c["cue"]["note"]))
            r.small(t(nd["cue_go"]), before=2)

        self.body_row(2, needs, first=False)

    # 3절 -------------------------------------------------------------------
    def sec3(self) -> None:
        b = self.blocks(3)
        t = self.t

        def a(r: Cell) -> None:
            r.headline(t(b["headline"]))
            r.p(t(b["legend"]))
            st = b["steps"]
            r.h2(st["head"], st.get("crit"))
            for i, s in enumerate(st["items"], 1):
                roles = " ".join(f"[{x}]" for x in s["roles"])
                r.p([(f"{i}. {t(s['name'])} ", {"b": True}), (roles, {"size": 9.5, "color": MUTED})], keep_next=True, after=0)
                r.p(t(s["text"]), after=0)
                tool = t(s["tool"])
                if s.get("big"):
                    tool += f" ({t(s['big'])}{t(s['big_unit'])})"
                r.small(tool, after=3)

        self.body_row(3, a)

        def users(r: Cell) -> None:
            us = b["users"]
            r.h2(us["head"], us.get("crit"))
            for u in us["items"]:
                r.p([(t(u["title"]) + ": ", {"b": True}), t(u["text"])])
                if u.get("img"):
                    path = self.form.images[u["img"]]
                    asp = self.form.aspect(u["img"])
                    r.image(path, 60.0 * asp, t(u["img_note"]))
                    r.small(t(u["img_note"]))
            cd = b["cond"]
            r.p([(t(cd["head"]) + ": ", {"b": True}), t(cd["text"])])
            r.small(t(cd["note"]))
            r.h2(self.c["labels"]["head_shot"])
            for row in b["shot"]["rows"]:
                path = self.form.images[row["img"]]
                alt = f"{row['n']}. {t(row['label'])}"
                r.image(path, 142.0, alt)
                r.small(alt)
            od = b["order"]
            r.h2(od["head"], od.get("crit"))
            for i, o in enumerate(od["items"], 1):
                tabs = " ".join(f"[{t(x)}]" for x in o["tabs"])
                r.p([(f"{i}. {t(o['name'])}  ", {"b": True}), tabs, "  " + t(o["text"])])

        self.body_row(3, users, first=False)

    # 4절 -------------------------------------------------------------------
    def sec4(self) -> None:
        b = self.blocks(4)
        t = self.t
        fl = b["flow"]

        def a(r: Cell) -> None:
            r.headline(t(b["headline"]))
            r.h2(fl["head"], fl.get("crit"))
            for x in fl["legend"]:
                r.bullet(t(x))

        self.body_row(4, a)

        def flow(r: Cell) -> None:
            img = self.sh.shoot("p4.flow", [".lane-wrap"], pad_mm=(0.5, 0.5, 0.5, 0.5))
            alt = f"{t(fl['head'])}: " + img["text"]
            r.image(img["path"], 130.0, alt)
            r.p(f"{t(fl['head'])}: {t(b['headline'])}", "그림 설명")
            self.fig("4절 역할별 처리 흐름도", "도해")

        self.body_row(4, flow, first=False, whole=True)

        def bottom(r: Cell) -> None:
            wk = b["week"]
            r.h2(wk["head"], wk.get("crit"))
            r.bullet(t(wk["daily"]))
            r.bullet(t(wk["sun"]))
            r.bullet(t(wk["manual"]))
            rc = b["receipt"]
            r.h2(rc["head"], rc.get("crit"))
            for it in rc["items"]:
                r.bullet(f"{t(it['label'])}: {t(it['won'])}")
            r.p([(f"{t(rc['total_label'])}: {t(rc['total'])}", {"b": True})])
            r.small(t(b["note"]), before=3)

        self.body_row(4, bottom, first=False)

    # 다섯 단계의 전후 비교 표(13쪽 판 5절, 버전 2 2절에서 함께 쓴다) --------------------------
    def five_step(self, r: Cell, tb: dict, secname: str, conv_blk: str | None = None, last: bool = True) -> None:
        """중첩 표. conv_blk 를 주면 세 번째 단계의 예시 그림(원문 명칭 세 건 → 표준담보)을 그림으로도 넣는다."""
        f = self.form
        t = self.t
        fg = tb["fig"]
        widths = [22.0, 34.0, 48.0, 40.0]
        rows = tb["rows"]
        nrows = 1 + len(rows) + 2
        nt = r.table(widths, nrows)
        for j, (cell, txt) in enumerate(zip(nt.rows[0].cells, tb["cols"])):
            shade(cell, PAPER_DEEP)
            w = Cell(cell, widths[j] - 2.5)
            w.p(t(txt), size=9, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            w.finish()
        repeat_header(nt.rows[0])
        ri = 1
        for i, row in enumerate(rows):
            if i in (0, 3):                  # 묶음 제목 행
                g = nt.rows[ri]
                m = g.cells[0].merge(g.cells[3])
                shade(m, PAPER)
                w = Cell(m, 140)
                w.p(t(tb["groups"][0 if i == 0 else 1]), size=9, bold=True)
                w.finish()
                ri += 1
            cells = nt.rows[ri].cells
            ri += 1
            w = Cell(cells[0], widths[0] - 2.5)
            w.p(f"{i + 1}. {t(row['name'])}", size=9, bold=True)
            w.finish()
            w = Cell(cells[1], widths[1] - 2.5)
            w.p(t(row["before"]), size=9)
            w.finish()
            w = Cell(cells[2], widths[2] - 2.5)
            w.p([(f"[{row['role']}] ", {"b": True}), t(row["after"])], size=9, after=1)
            w.p([(t(self.c["labels"]["human"]) + " ", {"b": True}), t(row["human"])], size=9)
            w.finish()
            w = Cell(cells[3], widths[3] - 2.5)
            if i == 0:
                for code in B.ORGS3:
                    w.p(f"{f.org(code)} {t('{{fact:example_cancer_surgery.orgs.' + code + '.doc_page}}')}쪽", size=9, after=0)
            elif i == 1:
                w.p([(f"{t(fg['pay'])}{t(fg['pay_unit'])}", {"b": True, "size": 11})], after=0)
                w.p(t(fg["pay_sub"]), size=9, after=0)
                w.small(t(fg["pay_note"]))
            elif i == 2:
                if conv_blk:
                    img = self.sh.shoot(conv_blk, [".p5t .fg@2|div"], pad_mm=(0.5, 0.5, 0.5, 0.5))
                    alt = f"{t(self.c['labels']['conv_note'])}: {t(fg['target'])}"
                    w.image(img["path"], min(img["w_mm"], 28.0), alt, keep_next=False)
                w.p(t(self.c["labels"]["conv_note"]), size=9, after=0)
                w.p([(t(fg["target"]), {"b": True})], size=9)
            elif i == 3:
                w.image(f.images["cut_copy_button"], 27.0, t(fg["copy"]))
                w.small(t(fg["copy"]))
            else:
                w.image(f.images["cut_pending_chip"], 27.0, t(fg["pending"]))
                w.small(t(fg["pending"]))
            w.finish()
        if last:                              # 표 뒤에 글이 더 이어지면 표 뒤 문단을 줄이지 않는다(글이 겹친다)
            r.finish()
        self.fig(f"{secname} 다섯 단계 비교 표의 화면 캡처 둘(복사 버튼, 검수 대기 칩)", "화면 캡처")

    # 5절 -------------------------------------------------------------------
    def sec5(self) -> None:
        b = self.blocks(5)
        t = self.t
        f = self.form
        tb = b["table"]
        fg = tb["fig"]

        def a(r: Cell) -> None:
            r.headline(t(b["headline"]))
            r.p(t(b["situation"]))
            r.h2(tb["head"], tb.get("crit"))
            self.five_step(r, tb, "5절")

        self.body_row(5, a)

        def shot(r: Cell) -> None:
            sh = b["shot"]
            r.h2(sh["head"], sh.get("crit"))
            img = self.sh.shoot("p5.shot", [".shot"], pad_mm=(1.5, 1, 1, 3.5))
            legend = ", ".join(f"{m['n']} {t(m['label'])}" for m in sh["marks"])
            r.image(img["path"], img["w_mm"], f"{t(sh['caption'])}. {legend}")
            r.small(f"{legend}")
            r.small(t(sh["caption"]))
            for code in B.ORGS3[1:]:
                same, txt = f.pair_text(code)
                r.bullet(plain(txt))
            r.small(t(sh["result_note"]))
            ef = b["effect"]
            r.h2(self.c["labels"]["effect"], ef.get("crit"))
            r.p([(t(ef["now_label"]) + ": ", {"b": True}), (t(ef["now_value"]), {"b": True, "size": 11}), "  " + t(ef["now_sub"])], after=0)
            r.small(t(ef["now_note"]))
            r.p([(t(ef["tool_label"]) + " ", {"b": True}), (f"[{t(ef['tool_badge'])}] ", {"size": 9.5, "color": MUTED}), t(ef["tool_text"])], after=0)
            r.p(t(ef["tool_struct"]), bold=True, after=0)
            r.small(t(ef["tool_struct_note"]), after=0)
            r.small(t(ef["tool_note"]))
            r.p(t(ef["go"]), bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
            self.fig("5절 암 수술비 확대 컷(번호 표시 포함)", "화면 캡처")

        self.body_row(5, shot, first=False)

    # 6절 -------------------------------------------------------------------
    def sec6(self) -> None:
        b = self.blocks(6)
        t = self.t
        f = self.form

        def roles(r: Cell) -> None:
            r.headline(t(b["headline"]))
            ro = b["roles"]
            r.h2(ro["head"], ro.get("crit"))
            for c in ro["chips"]:
                r.bullet([(f"[{c['role']}] ", {"b": True}), t(c["text"])])
            r.p(t(ro["ex1_label"]), bold=True, before=3, after=0)
            r.p(" / ".join(t(x) for x in ro["ex1_in"]) + " → " + t(self.c["labels"]["code_reads"]) + " → " + t(ro["ex1_out"]))
            r.p(t(ro["ex2_label"]), bold=True, before=3, after=0)
            r.p(f"{t(ro['ex2_in'])} → {t(ro['ex2_mid'])} → {t(ro['ex2_out'])}")

        self.body_row(6, roles)

        def gauge(r: Cell) -> None:
            g = b["gauge"]
            r.h2(g["head"], g.get("crit"))
            r.p(t(g["stack_label"]), bold=True, after=0)
            r.p(f"{t(g['seg_re'])}, {t(g['seg_rv'])}")
            img = self.sh.shoot("p6.g1", [".p6g > div:nth-child(2) > p.sm", ".p6g > div:nth-child(2) > div:nth-of-type(2)"],
                                pad_mm=(0.5, 1, 1.5, 1))
            cap = f"{t(g['head'])}: {t(g['big_label'])} {t(g['big'])}, 구간 {t(g['zones'][0])}, {t(g['zones'][1])}, {t(g['zones'][2])}"
            r.image(img["path"], img["w_mm"], f"{cap}. " + img["text"])
            r.p(cap, "그림 설명")
            self.fig("6절 확률 산정 모의 테스트 막대", "도해")
            r.p(t(g["line"]))
            r.small(t(g["chip"]))
            r.small(t(g["scope"]))

        self.body_row(6, gauge, first=False)

        def onto(r: Cell) -> None:
            on = b["onto"]
            r.h2(on["head"], on.get("crit"))
            img = self.sh.shoot("p6.g2", [".p6g > div:nth-child(1) > div:nth-of-type(1)"], pad_mm=(1, 1, 1, 1))
            names = ", ".join(f"{f.org(c)} {t('{{fact:example_cancer_surgery_names.' + c + '}}')}" for c in B.ORGS3)
            cap = f"{t(on['head'])}: {names} → {t(on['target'])}({t(on['target_sub'])})"
            r.image(img["path"], img["w_mm"], cap)
            r.p(cap, "그림 설명")
            self.fig("6절 표준담보 연결 그림", "도해")
            r.p(t(on["chip"]))
            for tile in on["tiles"]:
                sub = f" ({t(tile['sub'])})" if tile.get("sub") else ""
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"]) + sub])
            gd = b["gold"]
            r.h2(gd["head"], gd.get("crit"))
            img = self.sh.shoot("p6.g2", [".rings"], pad_mm=(1, 1, 1, 1))
            parts = []
            for rg in gd["rings"]:
                val = t("{{fact:goldset_epost_benefit.auto_match}}") + "+" + t(rg["hatch"]) if rg.get("hatch") else t(rg["value"])
                parts.append(f"{t(rg['label'])} {val}/{t(rg['total'])}")
            cap = f"{t(gd['head'])}: " + ", ".join(parts)
            r.image(img["path"], img["w_mm"], cap + ". " + img["text"])
            r.p(cap, "그림 설명")
            self.fig("6절 정답표 대조 링", "도해")
            r.small(t(gd["rings"][1]["legend"]))
            r.small(t(gd["ring_note"]))
            r.p(t(gd["weak_head"]), bold=True, before=3)
            for br in gd["bars"]:
                r.bullet(f"{t(br['label'])}: {t(br['match'])}/{t(br['items'])}")
            us = gd["unscored"]
            r.bullet([f"{t(us['label'])}: ", (f"[{t(us['badge'])}] ", {"size": 9.5, "color": MUTED}), t(us["text"])])

        self.body_row(6, onto, first=False)

        def team(r: Cell) -> None:
            tm = b["team"]
            r.h2(tm["head"], tm.get("crit"))
            img = self.sh.shoot("p6.team", ["h3 + div"], pad_mm=(1, 1, 1, 1))
            ch = [t(tm["me"]) + " " + t(tm["me_sub"]), f"{t(tm['cc'])} {t(tm['cc_sub'])}", f"{t(tm['gem'])} {t(tm['gem_sub'])}",
                  f"{t(tm['ag'])} {t(tm['ag_sub'])}"] + [f"{t(s['name'])} {t(s['sub'])}" for s in tm["subs"]] + [
                      f"{t(tm['gh'])} {t(tm['gh_sub'])}", t(tm["ring"])]
            cap = f"{t(tm['head'])}: " + ", ".join(ch)
            r.image(img["path"], min(img["w_mm"], 120.0), cap)
            r.p(cap, "그림 설명")
            self.fig("6절 개발 체계도", "도해")
            r.small(t(tm["asof"]))
            for tile in tm["tiles"]:
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"])])

        self.body_row(6, team, first=False)

    # 7절 -------------------------------------------------------------------
    def sec7(self) -> None:
        b = self.blocks(7)
        t = self.t

        def orgs(r: Cell) -> None:
            r.headline(t(b["headline"]))
            og = b["orgs"]
            r.h2(og["head"], og.get("crit"))
            for n in og["nodes"]:
                badge = f" [{t(n['badge'])}]" if n.get("badge") else ""
                r.bullet([(t(n["name"]) + badge + ": ", {"b": True}), t(n["sub"])])
            for x in og["notes"]:
                r.small(t(x))
            pg = og["progress"]
            r.p(t(pg["head"]), bold=True, before=4, after=1)
            img = self.sh.shoot("p7.orgs", [".prog > div", ".prog .pbar"], pad_mm=(1, 1, 1, 1))
            key = [plain(e) for e in self.sh.page.evaluate(
                "() => Array.from(document.querySelectorAll('[data-blk=\"p7.orgs\"] .prog p.sm .nw')).map(e => e.innerText)")]
            cap = f"{t(pg['head'])}: " + ", ".join(key)
            r.image(img["path"], img["w_mm"], cap)
            self.fig("7절 목표 회사 진행 현황(점과 막대)", "도해")
            for k in key:
                r.bullet(k)
            for tile in og["tiles"]:
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"])])

        self.body_row(7, orgs)

        def uses(r: Cell) -> None:
            us = b["uses"]
            r.h2(us["head"], us.get("crit"))
            for c in us["cards"]:
                r.p([(t(c["name"]), {"b": True})], keep_next=True, after=0)
                r.p(t(c["text"]), after=0)
                r.small(t(c["note"]), after=0)
                r.small([t(us["tabs_label"]) + " ", " ".join(f"[{t(x)}]" for x in c["tabs"])], after=3)
            r.small(t(us["out"]))
            lm = b["limits"]
            r.h2(lm["head"], lm.get("crit"))
            r.p(t(lm["left_head"]), bold=True, after=1)
            for x in lm["left"]:
                r.bullet(t(x))
            r.p(t(lm["right_head"]), bold=True, before=3, after=1)
            for x in lm["right"]:
                r.bullet(t(x))
            r.p(t(lm["unmeasured_head"]), bold=True, before=3, after=1)
            for x in lm["unmeasured"]:
                r.bullet([(f"[{t(lm['badge'])}] ", {"size": 9.5, "color": MUTED}), t(x)])

        self.body_row(7, uses, first=False)

    # 8절 -------------------------------------------------------------------
    def sec8(self) -> None:
        b = self.blocks(8)
        t = self.t
        f = self.form
        rc = b["record"]

        def pill_of(row: dict) -> str:
            if row.get("state"):
                return self.c["states"][row["state"]]["on" if f.states[row["state"]] else "off"]["pill"]
            return row["pill"]

        def a(r: Cell) -> None:
            r.headline(t(b["headline"]))
            r.h2(rc["head"], rc.get("crit"))
            r.p([(t(self.c["labels"]["no_record"]) + "  ", {"b": True}), t(rc["none"])])
            r.p(t(rc["evidence_head"]), bold=True, before=3, after=1)
            done = sum(1 for x in rc["rows"] if pill_of(x) in ("반영", "일부 반영"))
            gold = (f.num("{{fact:goldset_epost_benefit.auto_match}}") + f.num("{{fact:goldset_epost_benefit.manual_match}}")
                    + f.num("{{fact:goldset_hanwha_benefit.match}}"))
            gold_all = f.num("{{fact:goldset_epost_benefit.items}}") + f.num("{{fact:goldset_hanwha_benefit.items}}")
            calc = {"opinions": f"{done}/{len(rc['rows'])}", "goldset": f"{int(gold)}/{int(gold_all)}"}
            for e in rc["evidence"]:
                val = calc[e["calc"]] if e.get("calc") else t(e["value"])
                r.bullet([(f"{val}{t(e['unit'])}: ", {"b": True}), t(e["label"])])

        self.body_row(8, a)

        def table(r: Cell) -> None:
            r.p(t(rc["have"]))
            widths = [62.0, 58.0, 24.0]
            nt = r.table(widths, 1 + len(rc["rows"]))
            for j, (cell, txt) in enumerate(zip(nt.rows[0].cells, rc["cols"])):
                shade(cell, PAPER_DEEP)
                w = Cell(cell, widths[j] - 2.5)
                w.p(t(txt), size=9, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
                w.finish()
            repeat_header(nt.rows[0])
            for i, row in enumerate(rc["rows"], 1):
                cells = nt.rows[i].cells
                for j, txt in enumerate((t(row["ask"]), t(row["done"]), pill_of(row))):
                    w = Cell(cells[j], widths[j] - 2.5)
                    w.p(txt, size=9, bold=(j == 2))
                    w.finish()
            r.p(t(rc["next"]), bold=True, before=3)
            r.finish()

        self.body_row(8, table, first=False)

    # 생성물 ----------------------------------------------------------------
    def outputs(self) -> None:
        o = self.c["output"]
        fo = self.c["form"]["output"]
        t = self.t
        f = self.form

        l, r = self.row()
        self.label(l, fo["label"], fo["guide"])
        if o.get("head"):
            r.h2(o["head"])
        for x in o["files"]:
            r.p([(t(x["name"]) + "  ", {"b": True}), (x["file"], {"b": True}), "  " + t(x["note"])])
        oh = o["open_how"]
        r.p([(t(oh["name"]) + "  ", {"b": True}), t(oh["text"])], after=0)
        r.small(t(oh["note"]))
        l.finish(); r.finish()
        self.rows.append("생성물 (첨부 파일 안내)")

        def cont_row(build) -> None:
            l2, r2 = self.row(whole=True)
            l2.p(fo["cont"], "항목 이름")
            l2.small(fo["guide"])
            build(r2)
            l2.finish(); r2.finish()

        def videos(rr: Cell) -> None:
            rr.h2(o["videos_head"])
            for v in o["videos"]:
                cap = f"{t(v['label'])} ({t(v['len'])})"
                rr.image(f.images[v["img"]], 80.0, f"설명 영상 장면: {cap}")
                rr.p(cap, "그림 설명")
            rr.small(t(o["videos_note"]))
            self.fig("생성물 설명 영상 장면 넷", "화면 캡처(영상 장면)")

        if o.get("videos"):
            cont_row(videos)
            self.rows.append("생성물 (계속: 설명 영상)")

        n = len(o.get("shots", []))
        for i, s in enumerate(o.get("shots", [])):
            def shot(rr: Cell, i: int = i, s: dict = s) -> None:
                if i == 0:
                    rr.h2(o["shots_head"])
                rr.p([(f"{i + 1}. {t(s['label'])}", {"b": True})], keep_next=True, after=0)
                rr.small(t(s["text"]), keep_next=True)
                fw = B.Form.FULL_W[s["img"]]
                alt = f"{t(s['label'])}: {t(s['text'])}"
                if not s.get("cut"):
                    rr.image(f.images[s["img"]], fw, alt)
                else:
                    cw = B.Form.CUT_W[s["cut"]]
                    if fw + cw <= 146:                       # 세로로 긴 응대 화법 카드: 전체와 확대 컷을 한 줄에
                        rr.images([(f.images[s["img"]], 62.0, alt), (f.images[s["cut"]], 62.0, alt + " (확대 컷)")])
                    else:
                        rr.image(f.images[s["img"]], fw, alt)
                        rr.image(f.images[s["cut"]], cw, alt + " (확대 컷)")
                if i == n - 1:
                    rr.small(t(o["shots_note"]), before=3)
            cont_row(shot)
            self.rows.append(f"생성물 (계속: 화면 캡처 {i + 1}. {t(s['label'])})")
        if n:
            self.fig("생성물 화면 캡처와 확대 컷 여섯 화면", "화면 캡처")

    # 버전 2(content_v2.json 의 "variant": "v2") ------------------------------------------------------------
    # 절은 여섯 개(1 개요, 2 활용 업무와 기존 방식 대비 변화, 3 사용 AI와 기술과 사용 방법, 4 신뢰 근거, 5 확장과 한계, 6 사용 실적)와
    # 생성물 행이다. 평가기준 표시가 없어 소제목에 꼬리표를 붙이지 않는다(crit 를 넘기지 않는다).
    def v2_sec1(self) -> None:
        b = self.blocks(1)
        f = self.c["form"]["body"]
        t = self.t
        l, r = self.row()
        self.sec_seen.add(1)
        l.p(f["label"], "항목 이름")
        l.small(f["guide_head"])
        for g in f["guide"]:
            l.small(g["text"])
            l.p([("→ " + t(g["go"]), {"b": True, "color": RED})], size=9, after=4)
        r.h1(f"1. {self.pages[0]['topic']}")
        r.headline(t(b["lead"]))
        for x in b["intro"]:
            r.kv(t(x["label"]), t(x["text"]))
        fl = b["flow"]
        r.h2(fl["head"])
        img = self.sh.shoot("p1.flow", [".p1-flow"])
        nodes = fl["nodes"]
        cap = (f"{t(fl['head'])}: {t(nodes[0]['label'])} {t('{{fact:hanwha_summary_pages}}')}쪽({t(nodes[0]['sub'])}) → "
               f"[{t(fl['arrows'][0])}] → {t(nodes[1]['label'])}({t(nodes[1]['sub'])}) → "
               f"[{t(fl['arrows'][1])}] → {t(nodes[2]['label'])}({t(nodes[2]['sub'])})")
        r.image(img["path"], img["w_mm"], cap)
        r.p(cap, "그림 설명")
        self.fig("1절 문서에서 화면까지의 흐름", "도해")
        op = b["open"]
        r.p([(t(op["label"]) + "  ", {"b": True}), (op["file"] + "  ", {"b": True}), t(op["text"])])
        l.finish(); r.finish()
        self.rows.append("활용 내용 및 설명 / 1. 개요")

        def more(r: Cell) -> None:
            for tile in b["tiles"]:
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"])])
            r.small(t(b["caution"]), before=4)

        self.body_row(1, more, first=False, whole=True)

    def v2_sec2(self) -> None:
        b = self.blocks(2)
        t = self.t
        f = self.form

        def a(r: Cell) -> None:
            if b.get("headline"):
                r.headline(t(b["headline"]))
            r.kv(t(b["situation"]["label"]), t(b["situation"]["text"]))
            fa = b["facts"]
            for c in fa["chips"]:
                r.bullet([(t(c["label"]) + ": ", {"b": True}), t(c["value"])])
            r.small(t(fa["note"]))
            r.h2(b["why_head"])
            w = b["why"]
            r.p([(f"1. {t(w[0]['title'])}", {"b": True})], keep_next=True, after=0)
            r.p([(f"{t(w[0]['value'])}{t(w[0]['unit'])}: ", {"b": True}), t(w[0]["caption"])], after=0)
            r.small(t(w[0]["note"]))
            r.p([(f"2. {t(w[1]['title'])}", {"b": True})], keep_next=True, after=0)
            r.small(t(w[1]["caption"]), after=1)
            for code in B.ORGS3:
                q = t("{{fact:simple_uw_questions_by_org." + code + ".period_question}}")
                r.bullet([(f.org(code) + " ", {"b": True}), q])
            r.p(t(w[1]["tag"]), bold=True)
            r.p([(f"3. {t(w[2]['title'])}", {"b": True})], keep_next=True, after=0)
            r.small(t(w[2]["caption"]), after=1)
            for code in B.ORGS3:
                r.bullet([(f.org(code) + ": ", {"b": True}), t("{{fact:example_cancer_surgery_names." + code + "}}")])
            for n in b.get("notes", []):
                r.p(t(n))

        self.body_row(2, a)

        def table(r: Cell) -> None:
            tb = b["table"]
            r.h2(tb["head"])
            r.small(t(tb["situation"]))
            self.five_step(r, tb, "2절", conv_blk="p2.table", last=False)
            ef = b["effect"]
            lab = t(self.c["labels"]["effect"])
            r.p([(f"{lab}: {t(ef['now_label'])}", {"b": True})], keep_next=True, before=4, after=0)
            r.p([(t(ef["now_value"]), {"b": True, "size": 11}), "  " + t(ef["now_sub"])], after=0)
            r.small(t(ef["now_note"]))
            r.p([(f"{lab}: {t(ef['tool_label'])}", {"b": True})], keep_next=True, before=2, after=0)
            r.p([(f"[{t(ef['tool_badge'])}] ", {"size": 9.5, "color": MUTED}), t(ef["tool_text"])], after=0)
            r.p([(t(ef["tool_struct"]), {"b": True}), (f" ({t(ef['tool_struct_note'])})", {"size": 9, "color": MUTED})])

        self.body_row(2, table, first=False)

    def v2_sec3(self) -> None:
        b = self.blocks(3)
        t = self.t

        def a(r: Cell) -> None:
            if b.get("headline"):
                r.headline(t(b["headline"]))
            items = b["steps"]["items"]
            widths = [27.0, 18.0, 44.0, 55.0]
            nt = r.table(widths, len(items))
            for i, (row, s) in enumerate(zip(nt.rows, items)):
                texts = [(f"{i + 1}. {t(s['name'])}", True), (" ".join(f"[{x}]" for x in s["roles"]), False),
                         (t(s["text"]), False), (t(s["tool"]), False)]
                for j, (cell, (txt, bold)) in enumerate(zip(row.cells, texts)):
                    if s.get("hero"):
                        shade(cell, PAPER)
                    w = Cell(cell, widths[j] - 2.5)
                    w.p(txt, size=9, bold=bold if j == 0 else None, color=MUTED if j == 3 else None)
                    w.finish()
            au = b["auto"]
            r.kv(t(au["label"]), t(au["text"])).paragraph_format.space_before = Pt(4)
            r.small(t(au["note"]))
            od = b["order"]
            r.h2(od["head"])
            for i, o in enumerate(od["items"], 1):
                tabs = " ".join(f"[{t(x)}]" for x in o["tabs"])
                r.p([(f"{i}. {t(o['name'])}  ", {"b": True}), tabs + ("  " + t(o["text"]) if o.get("text") else "")])

        self.body_row(3, a, whole=True)

    def v2_sec4(self) -> None:
        b = self.blocks(4)
        t = self.t
        f = self.form

        def a(r: Cell) -> None:
            if b.get("headline"):
                r.headline(t(b["headline"]))
            g = b["gauge"]
            r.h2(g["head"])
            r.p(t(g["stack_label"]), bold=True, after=0)
            r.p(f"{t(g['seg_re'])}, {t(g['seg_rv'])}")
            img = self.sh.shoot("p4.g1", [".p6g > div:nth-child(1) > p.sm", ".p6g > div:nth-child(1) > div:nth-of-type(2)"],
                                pad_mm=(0.5, 1, 1.5, 1))
            cap = f"{t(g['head'])}: {t(g['big_label'])} {t(g['big'])}, 구간 {t(g['zones'][0])}, {t(g['zones'][1])}, {t(g['zones'][2])}"
            r.image(img["path"], img["w_mm"], f"{cap}. " + img["text"])
            r.p(cap, "그림 설명")
            self.fig("4절 확률 산정 모의 테스트 막대", "도해")
            r.p(t(g["line"]))
            r.small(t(g["scope"]))
            gd = b["gold"]
            r.h2(gd["head"])
            img = self.sh.shoot("p4.g1", [".rings"], pad_mm=(1, 1, 1, 1))
            parts = []
            for rg in gd["rings"]:
                val = t("{{fact:goldset_epost_benefit.auto_match}}") + "+" + t(rg["hatch"]) if rg.get("hatch") else t(rg["value"])
                parts.append(f"{t(rg['label'])} {val}/{t(rg['total'])}")
            cap = f"{t(gd['head'])}: " + ", ".join(parts)
            r.image(img["path"], img["w_mm"], cap + ". " + img["text"])
            r.p(cap, "그림 설명")
            self.fig("4절 정답표 대조 링", "도해")
            r.small(t(gd["rings"][1]["legend"]))
            r.small(t(gd["ring_note"]))
            r.p(t(gd["weak_head"]), bold=True, before=3)
            for br in gd["bars"]:
                r.bullet(f"{t(br['label'])}: {t(br['match'])}/{t(br['items'])}")
            us = gd["unscored"]
            r.bullet([f"{t(us['label'])}: ", (f"[{t(us['badge'])}] ", {"size": 9.5, "color": MUTED}), t(us["text"])])

        self.body_row(4, a)

        def rest(r: Cell) -> None:
            ro = b["roles"]
            r.h2(ro["head"])
            for c in ro["chips"]:
                r.bullet([(f"[{c['role']}] ", {"b": True}), t(c["text"])])
            on = b["onto"]
            r.h2(on["head"])
            for tile in on["tiles"]:
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"])])
            tm = b["team"]
            r.h2(tm["head"])
            for x in tm["lines"]:
                r.p([(t(x["who"]) + "  ", {"b": True}), t(x["role"])], after=1)
            r.small(t(tm["note"]))
            for tile in tm["tiles"]:
                r.bullet([(f"{t(tile['value'])}{t(tile['unit'])}: ", {"b": True}), t(tile["label"])])

        self.body_row(4, rest, first=False)

    def v2_sec5(self) -> None:
        b = self.blocks(5)
        t = self.t

        def orgs(r: Cell) -> None:
            og = b["orgs"]
            r.h2(og["head"])
            r.p(t(og["next"]))
            for x in og.get("notes", []):
                r.small(t(x))
            pg = og["progress"]
            r.p(t(pg["head"]), bold=True, before=4, after=1)
            img = self.sh.shoot("p5.orgs", [".prog > div", ".prog .pbar"], pad_mm=(1, 1, 1, 1))
            key = [plain(e) for e in self.sh.page.evaluate(
                "() => Array.from(document.querySelectorAll('[data-blk=\"p5.orgs\"] .prog p.sm .nw')).map(e => e.innerText)")]
            cap = f"{t(pg['head'])}: " + ", ".join(key)
            r.image(img["path"], img["w_mm"], cap)
            self.fig("5절 목표 회사 진행 현황(점과 막대)", "도해")
            for k in key:
                r.bullet(k)

        self.body_row(5, orgs)

        def uses(r: Cell) -> None:
            us = b["uses"]
            r.h2(us["head"])
            for c in us["items"]:
                r.bullet([(t(c["name"]) + ": ", {"b": True}), t(c["text"])])
            r.small(t(us["out"]))
            lm = b["limits"]
            r.h2(lm["head"])
            r.p(t(lm["left_head"]), bold=True, after=1)
            for x in lm["left"]:
                r.bullet(t(x))
            r.p(t(lm["right_head"]), bold=True, before=3, after=1)
            for x in lm["right"]:
                r.bullet(t(x))
            r.p(t(lm["unmeasured_head"]), bold=True, before=3, after=1)
            for x in lm["unmeasured"]:
                r.bullet([(f"[{t(lm['badge'])}] ", {"size": 9.5, "color": MUTED}), t(x)])

        self.body_row(5, uses, first=False)

    def v2_sec6(self) -> None:
        b = self.blocks(6)
        t = self.t
        f = self.form
        rc = b["record"]

        def pill_of(x: str) -> str:
            if x.startswith("state:"):
                return self.c["states"][x[6:]]["on" if f.states[x[6:]] else "off"]["pill"]
            return x

        def a(r: Cell) -> None:
            if b.get("headline"):
                r.headline(t(b["headline"]))
            r.p([(t(self.c["labels"]["no_record"]) + "  ", {"b": True}), t(rc["none"])])
            pills = [pill_of(x) for x in rc["status_all"]]       # 확인한 사항 전체의 상태(표에는 대표 사례만 적는다)
            done = sum(1 for x in pills if x in ("반영", "일부 반영"))
            gold = (f.num("{{fact:goldset_epost_benefit.auto_match}}") + f.num("{{fact:goldset_epost_benefit.manual_match}}")
                    + f.num("{{fact:goldset_hanwha_benefit.match}}"))
            gold_all = f.num("{{fact:goldset_epost_benefit.items}}") + f.num("{{fact:goldset_hanwha_benefit.items}}")
            calc = {"opinions": f"{done}/{len(pills)}", "goldset": f"{int(gold)}/{int(gold_all)}"}
            for e in rc["evidence"]:
                val = calc[e["calc"]] if e.get("calc") else t(e["value"])
                r.bullet([(f"{val}{t(e['unit'])}: ", {"b": True}), t(e["label"])])
            r.p(t(rc["have"]), before=3)
            widths = [62.0, 58.0, 24.0]
            nt = r.table(widths, 1 + len(rc["rows"]))
            for j, (cell, txt) in enumerate(zip(nt.rows[0].cells, rc["cols"])):
                shade(cell, PAPER_DEEP)
                w = Cell(cell, widths[j] - 2.5)
                w.p(t(txt), size=9, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
                w.finish()
            repeat_header(nt.rows[0])
            for i, row in enumerate(rc["rows"], 1):
                pill = pill_of("state:" + row["state"]) if row.get("state") else row["pill"]
                cells = nt.rows[i].cells
                for j, txt in enumerate((t(row["ask"]), t(row["done"]), pill)):
                    w = Cell(cells[j], widths[j] - 2.5)
                    w.p(txt, size=9, bold=(j == 2))
                    w.finish()
            r.p(t(rc["next"]), bold=True, before=3)
            r.finish()

        self.body_row(6, a)

    def build_v2(self) -> None:
        for fn in (self.v2_sec1, self.v2_sec2, self.v2_sec3, self.v2_sec4, self.v2_sec5, self.v2_sec6, self.outputs):
            fn()

    def build(self) -> Document:
        self.start()
        self.top_rows()
        if self.c.get("variant") == "v2":
            self.build_v2()
            return self.doc
        self.sec1()
        for fn in (self.sec2, self.sec3, self.sec4, self.sec5, self.sec6, self.sec7, self.sec8, self.outputs):
            fn()
        return self.doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identity", default=None, help="소속부서, 성명, 출품구분이 든 JSON(없으면 안내 문구를 넣은 견본)")
    ap.add_argument("--content", default=None, help="내용 파일(없으면 content.json, 버전 2 는 content_v2.json)")
    ap.add_argument("--out", required=True, help="docx 경로")
    ap.add_argument("--work", default=None, help="그림과 견본 HTML 을 둘 폴더(없으면 임시 폴더를 만들어 지운다)")
    a = ap.parse_args()

    work_ctx = None
    if a.work:
        work = Path(a.work)
        work.mkdir(parents=True, exist_ok=True)
    else:
        work_ctx = tempfile.TemporaryDirectory(prefix="docx_export_")
        work = Path(work_ctx.name)
    try:
        # 그림은 성명과 소속이 없는 견본 HTML 에서 찍는다
        content_path = Path(a.content).resolve() if a.content else B.HERE / "content.json"
        doc_html, info = B.build_html(content_path=content_path, strict=True)
        sample = work / "sample.html"
        sample.write_bytes(doc_html.encode("utf-8"))
        form = make_form(Path(a.identity) if a.identity else None, content_path)
        shooter = Shooter(sample, work / "fig")
        try:
            ex = Exporter(form, shooter)
            doc = ex.build()
        finally:
            shooter.close()
        errors = form.errors + form.ctx.errors
        if errors:
            raise SystemExit("글 해석 오류:\n  " + "\n  ".join(errors))
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out))
        kind = "제출본(identity 값 넣음)" if form.identity else "견본(안내 문구)"
        print(f"{out} {out.stat().st_size:,} 바이트, {kind}, 그림으로 넣은 도해 {len([x for x in ex.figs if x.endswith('도해')])}개")
        for x in ex.figs:
            print("  그림: " + x)
    finally:
        if work_ctx:
            work_ctx.cleanup()


if __name__ == "__main__":
    main()
