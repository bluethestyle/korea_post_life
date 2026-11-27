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
- 결과 HTML 에는 주소(URL)와 클릭 링크(<a>)를 두지 않는다. 외부 주소를 부르는 src, href, url(), @import 가 있으면 멈춘다.
  제출할 때 PDF 와 함께 첨부하는 HTML 파일 두 개는 content.json 의 output.files 이름으로 안내한다.
- --strict: 자리 표시 밖에 적은 숫자(양식 원래 문구와 literal_digits 제외), 채우지 못한 자리 표시, PDF 단계의 넘침(칸 밖으로 나간 글,
  9pt 미만 글자)을 오류로 본다.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import re
import struct
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
                   "rows_from", "names_from", "table_img", "html_title", "layout", "variant"}


def sec_of(bid: str) -> int:
    """블록 id("p3.grid")가 속한 절 번호. 생성물 행의 블록("out.…")은 0."""
    m = re.match(r"p(\d+)\.", bid)
    return int(m.group(1)) if m else 0


# 블록 → 평가기준(crit)이 적힌 content.json 블록 이름
BLOCK_CRIT = {
    "p1.flow": ("flow",), "p2.facts": ("facts",), "p2.quote": ("quote",), "p2.needs": ("needs",),
    "p3.steps": ("steps",), "p3.users": ("users",), "p3.order": ("order",), "p4.flow": ("flow",), "p4.bottom": ("week", "receipt"),
    "p5.table": ("table",), "p5.shot": ("shot",), "p5.effect": ("effect",), "p6.g1": ("roles", "gauge"),
    "p6.g2": ("onto", "gold"), "p6.team": ("team",), "p7.orgs": ("orgs",), "p7.uses": ("uses",), "p7.limits": ("limits",),
    "p8.record": ("record",),
}

TEAM_ZOOM = 1.45   # 6쪽 개발 체계 그림의 배율(글자도 함께 커진다)
P4_KY = 1.15      # 4쪽 흐름도의 세로 배율(1.0 = 설계 단위 그대로). 쪽 높이에 맞춰 키운다

# 글꼴 표기는 덱과 같되 주소는 뺀다(이 문서에는 주소를 두지 않는다. 저작권과 라이선스 이름은 그대로 둔다)
FONT_NOTICE = re.sub(r"\s*\(https?://[^)]*\)", "", deck_build.FONT_NOTICE)

ARROW = ('<svg class="arw" viewBox="0 0 10 6" aria-hidden="true">'
         '<path d="M0.5 3H8.6M6.4 0.9L8.8 3L6.4 5.1" fill="none" stroke="currentColor" stroke-width="1.1" '
         'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def jpeg_size(path: Path) -> tuple[int, int]:
    """JPEG 의 폭과 높이를 표준 라이브러리만으로 읽는다(테스트를 실행하는 CI 에는 Pillow 가 없다)."""
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise ValueError(f"JPEG 가 아닙니다: {path}")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    raise ValueError(f"JPEG 크기를 읽지 못했습니다: {path}")


def esc(s: Any) -> str:
    return P.esc(s)


# 어절 중간에서 줄이 바뀌지 않게 한다(2026-11-26 사용자 지시). 한글 어절은 word-break: keep-all 로 공백에서만 끊기지만, 어절 안의 괄호, 쉼표,
# 가운뎃점, 빗금, 하이픈, % 앞뒤는 브라우저가 줄을 바꿀 수 있다. 그 자리에만 WORD JOINER(U+2060, 화면에 보이지 않는 글자)를 넣어
# 줄바꿈을 막고(그 밖의 글자 사이에는 넣지 않아 글자 검색에 지장이 없다), 칸보다 긴 어절(16자 이상)만 같은 자리에 <wbr> 를 넣어
# 그 자리에서만 끊기게 한다. 양식 원문과 본문의 글자는 바꾸지 않는다.
WJ = "\u2060"
LONG_TOKEN = 16
_UNIT = re.compile(r"&#?\w+;|\S|\s+")
_MARKUP = re.compile(r"(<!--.*?-->|<style.*?</style>|<script.*?</script>|<svg.*?</svg>|<[^>]+>)", re.S)
_AFTER = set(")]·/,-%")
_BEFORE = set("([")
_NO_BREAK_BEFORE = set(".,;:·)]!?%")


def _glue_text(chunk: str) -> str:
    out: list[str] = []
    token: list[str] = []

    def flush() -> None:
        if not token:
            return
        long_ = len(token) >= LONG_TOKEN
        for i, u in enumerate(token):
            out.append(u)
            if i == len(token) - 1:
                continue
            nxt = token[i + 1]
            if not (u in _AFTER or nxt in _BEFORE):
                continue                                  # 줄이 바뀔 자리가 아니다
            if long_ and ((u in _AFTER and u not in "-/%" and nxt not in _NO_BREAK_BEFORE) or (nxt == "(" and u not in "([")):
                out.append("<wbr>")
            else:
                out.append(WJ)
        token.clear()

    for u in _UNIT.findall(chunk):
        if u.isspace():
            flush()
            out.append(u)
        else:
            token.append(u)
    flush()
    return "".join(out)


def glue(html: str) -> str:
    return "".join(part if i % 2 else _glue_text(part) for i, part in enumerate(_MARKUP.split(html)))


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
def pct_split(counts: list[int], total: int) -> list[float]:
    """건수를 전체 대비 비율(%)로, 소수 첫째 자리까지. 반올림한 합이 항상 100.0 이 되도록 큰 나머지 순으로 0.1 을 배분한다."""
    if total <= 0:
        return [0.0 for _ in counts]
    raw = [c * 1000 / total for c in counts]            # 0.1% 단위
    base = [int(r) for r in raw]
    short = 1000 - sum(base)
    order = sorted(range(len(counts)), key=lambda i: raw[i] - base[i], reverse=True)
    for i in order[:short]:
        base[i] += 1
    return [v / 10 for v in base]


class Form:
    def __init__(self, content: dict, facts: dict, refs: dict, deck: dict, identity: dict | None,
                 parents: set[str], image_dirs: list[Path]):
        self.c = content
        self.ctx = P.Ctx(facts, refs, deck, {})
        self.identity = identity
        self.pages = content["pages"]
        self.errors: list[str] = []
        # 쪽 배치(content.json 의 layout): 쪽마다 블록 id 의 목록. 글자 크기에 맞춰 쪽을 나눈 결과다
        # 항목은 블록 id 의 목록이거나, 블록 사이 간격(mm)을 키우는 {"gap": 3.2, "blocks": [...]} 이다
        self.layout: list[list[str]] = [e["blocks"] if isinstance(e, dict) else e for e in content["layout"]]
        self.gaps: list[float | None] = [e.get("gap") if isinstance(e, dict) else None for e in content["layout"]]
        self.total = len(self.layout)
        self.page_no: dict[str, int] = {}
        for i, ids in enumerate(self.layout):
            for bid in ids:
                # 블록 id 로도 쪽을 가리킬 수 있다({{pg:p7.limits}}). 절이 두 쪽에 걸칠 때 그 블록이 놓인 쪽을 적기 위해서다
                self.page_no[bid] = i + 1
                if bid.endswith(".head"):
                    self.page_no[bid.split(".")[0]] = i + 1
                elif bid == "out.shot0":
                    self.page_no["shots"] = i + 1
        self.L = content.get("labels", {})
        self.states = {name: any(x.startswith(s["prefix"]) for x in parents) for name, s in content.get("states", {}).items()}
        self.images: dict[str, Path] = {}
        for d in image_dirs:
            for p in sorted(Path(d).glob("*.jpg")):
                self.images.setdefault(p.stem, p)
        self.img_used: list[str] = []
        self.img_size: dict[str, tuple[int, int]] = {}
        # 평가기준 표시(소제목 옆 알약, 꼬리말의 근거 알약): 기본은 표시. 내용 파일의 "show_criteria": false 로 끈다(버전 2)
        self.show_crit = bool(content.get("show_criteria", True))
        self.crit_marks = self._crit_marks() if self.show_crit else {}

    # 평가기준 표식 -------------------------------------------------------
    def _crit_marks(self) -> dict[int, dict[str, bool]]:
        """쪽 번호 → {기준: 주된 근거인가}. 쪽에 놓인 블록(BLOCK_CRIT)의 crit 만 센다."""
        out: dict[int, dict[str, bool]] = {}

        def walk(o: Any, no: int, sec: int) -> None:
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
                            if sec == 1 and not isinstance(v, list):
                                continue          # 1쪽 기준 카드는 근거가 아니라 안내다
                            cur = out.setdefault(no, {})
                            cur[name] = cur.get(name, False) or prim
                    else:
                        walk(v, no, sec)
            elif isinstance(o, list):
                for v in o:
                    walk(v, no, sec)

        for i, ids in enumerate(self.layout):
            for bid in ids:
                sec = sec_of(bid)
                if not sec:
                    continue
                for key in BLOCK_CRIT.get(bid, ()):
                    walk(self.pages[sec - 1]["blocks"].get(key, {}), i + 1, sec)
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
            self.img_size[name] = jpeg_size(Path(self.images[name]))
        w, h = self.img_size.get(name, (16, 9))
        return w / h

    def crit_pills(self, crit: Any) -> str:
        if not self.show_crit:
            return ""
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
    def rail(self, cur: set[int]) -> str:
        items = []
        for i, p in enumerate(self.pages):
            on = " on" if i + 1 in cur else ""
            items.append(f'<li class="it{on}"><span class="n">{i + 1}</span><span>{esc(p["topic"])}</span></li>')
        return f'<ul class="rail" aria-label="활용 내용 및 설명의 쪽 구성">{"".join(items)}</ul>'

    def footer(self, no: int) -> str:
        if not self.show_crit:
            return (f'<footer class="ft"><span>{esc(self.c["footer_name"])}</span>'
                    f'<span class="pgno">{no} / {self.total}</span></footer>')
        marks = self.crit_marks.get(no, {})
        pills = "".join(f'<span class="cp {"on" if c in marks else "off"}">{c}</span>' for c in CRITERIA)
        return (f'<footer class="ft"><span>{esc(self.c["footer_name"])}</span>'
                f'<span class="crit"><span class="lab">{self.lab("crit_footer")}</span>{pills}</span>'
                f'<span class="pgno">{no} / {self.total}</span></footer>')

    def frame(self, rows: list[tuple[str, str, str, str]], grid_rows: str) -> str:
        f = self.c["form"]
        cells = [f'<div class="th l">{esc(f["head"][0])}</div><div class="th">{esc(f["head"][1])}</div>']
        for i, (lcls, lhtml, rcls, rhtml, *rstyle) in enumerate(rows):
            last = " last" if i == len(rows) - 1 else ""
            st = f' style="{rstyle[0]}"' if rstyle and rstyle[0] else ""
            cells.append(f'<div class="lc {lcls}{last}">{lhtml}</div><div class="rc {rcls}{last}"{st}>{rhtml}</div>')
        return f'<div class="frame" style="grid-template-rows:{grid_rows}">{"".join(cells)}</div>'

    def page(self, no: int, frame: str, first: bool = False) -> str:
        title = f'<h1 class="doctitle">{esc(self.c["form"]["doc_title"])}</h1>' if first else ""
        return f'<section class="page" id="pg{no}" data-no="{no}">{title}{frame}{self.footer(no)}</section>'

    def cont_left(self, secs: list[int]) -> str:
        """왼쪽 열: 쪽의 첫 절 이름과 목차(이 쪽에 든 절 모두 강조)."""
        f = self.c["form"]["body"]
        words = esc(self.pages[secs[0] - 1]["topic"]).split(" ")
        if len(words) >= 3 and len(words[-1]) <= 2:      # 마지막 줄에 짧은 한 단어만 남지 않게 뒤의 두 단어를 함께 내린다
            topic = " ".join(words[:-2]) + "<br>" + " ".join(words[-2:])
        else:
            topic = " ".join(words)
        return (f'<p class="cont">{esc(f["cont"]).replace(" (계속)", "<br>(계속)")}</p><p class="topic">{topic}</p>{self.rail(set(secs))}')

    def body_head(self, no: int, headline: str | None, cont: bool = False) -> str:
        tag = f'<p class="tag">{no}. {esc(self.pages[no - 1]["topic"])}{" (계속)" if cont else ""}</p>'
        hl = f'<h2 class="hl">{self.t(headline)}</h2>' if headline else ""
        return f'<div>{tag}{hl}</div>'

    # 1쪽 -------------------------------------------------------------------
    def p1(self, body: str, style: str = "") -> str:
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
        left6 = (f'<p>{esc(b["label"])}</p><p class="guide">{esc(b["guide_head"])}</p><p class="guide">{gl}</p>{self.rail({1})}')
        rows = [
            ("", esc(f["dept"]["label"]), "", dept),
            ("", esc(f["name"]["label"]), "", name),
            ("", esc(f["kind"]["label"]), "", f'<div class="check">{opts}</div>'),
            ("", esc(f["title"]["label"]), "", title),
            ("", f'{esc(f["tools"]["label"])}<span class="guide">{esc(f["tools"]["guide"])}</span>', "", tools),
            ("top", left6, "body", body, style),
        ]
        return self.page(1, self.frame(rows, "auto auto auto auto auto auto 1fr"), first=True)

    def p1_body(self) -> list[tuple[str, str]]:
        b = self.pages[0]["blocks"]
        intro = "".join(f'<span class="k">{self.t(x["label"])}</span><span>{self.t(x["text"])}</span>' for x in b["intro"])
        fl = b["flow"]
        pages = self.num("{{fact:hanwha_summary_pages}}")
        FH = 27
        n0 = (f'<div class="node" style="width:36mm"><div class="fig" style="height:{FH}mm;gap:1mm;align-items:flex-end">{self.stack_svg(pages, 17, FH)}'
              f'<span class="big" style="padding-bottom:1mm">{self.t("{{fact:hanwha_summary_pages}}")}<span class="u">쪽</span></span></div>'
              f'<p class="lab">{self.t(fl["nodes"][0]["label"])}</p><p class="sub">{self.t(fl["nodes"][0]["sub"])}</p></div>')
        sw = FH * self.aspect("summary")
        n1 = (f'<div class="node" style="width:{sw + 2:.1f}mm"><div class="fig" style="height:{FH}mm">{self.shot("summary", sw, hero=True)}</div>'
              f'<p class="lab">{self.t(fl["nodes"][1]["label"])}</p><p class="sub">{self.t(fl["nodes"][1]["sub"])}</p></div>')
        tw = FH * self.aspect("talk_preview")
        n2 = (f'<div class="node" style="width:30mm"><div class="fig" style="height:{FH}mm">{self.shot("talk_preview", tw)}</div>'
              f'<p class="lab">{self.t(fl["nodes"][2]["label"])}</p><p class="sub">{self.t(fl["nodes"][2]["sub"])}</p></div>')
        arr = lambda s: f'<div class="arr"><p class="t">{self.t(s)}</p>{self.arrow_svg(9, 3)}</div>'  # noqa: E731
        flow = f'<div class="p1-flow">{n0}{arr(fl["arrows"][0])}{n1}{arr(fl["arrows"][1])}{n2}</div>'
        op = b["open"]
        openl = (f'<p class="openl">{self.ic("monitor-cog", 4.6)}<b>{self.t(op["label"])}</b>'
                 f'<span class="fn">{esc(op["file"])}</span><span>{self.t(op["text"])}</span></p>')
        tiles = f'<div class="tiles" style="grid-template-columns:repeat({len(b["tiles"])},1fr)">' + "".join(self.tile(t) for t in b["tiles"]) + "</div>"
        cards = []
        for cd in b.get("cards", []):
            pgs = self.crit_pages(cd["crit"])
            go = f'{self.lab("crit_go")} {ARROW} ' + ", ".join(str(p) for p in pgs) + "쪽" if pgs else ""
            if not pgs:
                self.errors.append(f"1쪽 기준 카드 {cd['crit']}: 주된 근거 블록(crit 의 *)이 있는 쪽이 없음")
            cards.append(f'<div class="ccard"><div class="h"><span class="n">{esc(cd["crit"])}</span><span class="go">{go}</span></div>'
                         f'<p>{self.t(cd["text"])}</p></div>')
        return [("p1.head", self.body_head(1, None)),
                ("p1.lead", f'<p class="p1-lead">{self.t(b["lead"])}</p>'),
                ("p1.intro", f'<div class="p1-intro">{intro}</div>'),
                ("p1.flow", f'<div>{self.bh(fl["head"], fl.get("crit"))}{flow}{openl}</div>'),
                *([("p1.cards", f'<div>{self.bh(b["cards_head"])}<div class="p1-cards">{"".join(cards)}</div></div>')] if cards else []),
                ("p1.tiles", tiles),
                ("p1.caution", f'<p class="caution">{self.ic("info", 3.6)}<span>{self.t(b["caution"])}</span></p>')]

    # 2쪽 -------------------------------------------------------------------
    def org(self, code: str) -> str:
        return self.t("{{fact:org_names." + code + "}}")

    def p2_body(self) -> list[tuple[str, str]]:
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
        notes = "".join(f'<p style="font-size:10pt;line-height:1.4">{self.t(n)}</p>' for n in b["notes"])
        nd = b["needs"]
        cols = []
        for c in nd["cols"]:
            tag = f'<p class="sm" style="margin-top:auto"><span class="badge-um" style="white-space:normal;line-height:1.3">{self.t(c["tag"])}</span></p>' if c.get("tag") else ""
            cue = ""
            if c.get("cue"):
                cue = (f'<div class="cue">{self.shot(c["cue"]["img"], 41)}<p class="sm mut">{self.t(c["cue"]["note"])}</p></div>')
            cols.append(f'<div class="need"><p class="ask">{self.t(c["ask"])}</p><div class="down">{self.down_svg(5)}</div>'
                        f'<div class="card"><p class="tab">{self.ic(c["icon"], 5)}{self.t(c["tab"])} {self.lab("tab_suffix")}</p><p>{self.t(c["text"])}</p>{tag}{cue}</div></div>')
        return [("p2.head", self.body_head(2, b["headline"])),
                ("p2.situation", f'<p class="band"><span class="k">{self.t(b["situation"]["label"])}</span><span>{self.t(b["situation"]["text"])}</span></p>'),
                ("p2.facts", f'<div>{self.bh(fa["head"], fa.get("crit"))}<div class="p2-chips">{chips}</div><p class="sm mut" style="margin-top:0.8mm">{self.t(fa["note"])}</p></div>'),
                ("p2.why", f'<div>{self.bh(b["why_head"])}<div class="p2-why">{c1}{c2}{c3}</div></div>'),
                ("p2.quote", quote),
                ("p2.notes", f'<div>{notes}</div>'),
                ("p2.needs", f'<div>{self.bh(nd["head"], nd.get("crit"))}<div class="p2-needs">{"".join(cols)}</div>'
                             f'<p class="sm mut" style="margin-top:1.2mm">{self.t(nd["cue_go"])}</p></div>')]

    def order_html(self, od: dict, flex: list[float] | None = None) -> str:
        """사용 순서(네 단계 상자). flex 를 주면 상자 폭의 비율을 바꾼다(버전 2)."""
        nodes = []
        for i, o in enumerate(od["items"]):
            tabs = "".join(f'<span class="chip line">{self.t(x)}</span>' for x in o["tabs"])
            fx = f' style="flex:{flex[i]}"' if flex else ""
            text = f'<p>{self.t(o["text"])}</p>' if o.get("text") else ""
            nodes.append(f'<div class="nd"{fx}><p class="nm"><span class="no">{i + 1}</span>{self.t(o["name"])}</p>'
                         f'<div class="tabs">{tabs}</div>{text}</div>')
        order = f'<div class="order">{(chr(10)).join(nodes[:1])}' + "".join(
            f'<div class="ar">{self.arrow_svg(4, 3)}</div>{n}' for n in nodes[1:]) + "</div>"
        return order

    # 3쪽 -------------------------------------------------------------------
    def p3_body(self) -> list[tuple[str, str]]:
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
                img = (f'<div style="display:flex;gap:2mm;align-items:flex-end;margin-top:1mm">{self.shot(u["img"], 30 * self.aspect(u["img"]))}'
                       f'<span class="chip line">{self.t(u["img_note"])}</span></div>')
            ucards.append(f'<div class="ucard{" tall" if img else ""}"><p class="t">{self.t(u["title"])}</p><p>{self.t(u["text"])}</p>{img}</div>')
        cd = b["cond"]
        cond = (f'<div class="ucard cond"><p class="t">{self.t(cd["head"])}</p>'
                f'<p>{self.t(cd["text"])}</p><p class="sm mut" style="margin-top:0.6mm">{self.t(cd["note"])}</p></div>')
        sh = b["shot"]
        widths = {"cut_head_a": 142, "cut_head_b": 142}
        rws = []
        for r in sh["rows"]:
            rws.append(f'<div class="hrow"><span class="hn">{esc(r["n"])}</span><div>{self.shot(r["img"], widths[r["img"]])}'
                       f'<p class="sm hl2">{self.t(r["label"])}</p></div></div>')
        shot = f'<div class="hrows">{"".join(rws)}</div>'
        od = b["order"]
        order = self.order_html(od)
        legend = (f'<p class="legendline">{self.role("AI")}{self.role("코드")}{self.role("사람")}<span>{self.t(b["legend"])}</span></p>')
        return [("p3.head", self.body_head(3, b["headline"])),
                ("p3.legend", legend),
                ("p3.steps", f'<div>{self.bh(st["head"], st.get("crit"))}<div class="ladder">{"".join(steps)}</div></div>'),
                ("p3.users", f'<div>{self.bh(us["head"], us.get("crit"))}<div class="ucards3">{"".join(ucards)}{cond}</div></div>'),
                ("p3.shot", f'<div>{self.bh(self.L.get("head_shot", ""))}{shot}</div>'),
                ("p3.order", f'<div>{self.bh(od["head"], od.get("crit"))}{order}</div>')]

    # 4쪽 -------------------------------------------------------------------
    def p4_body(self) -> list[tuple[str, str]]:
        b = self.pages[3]["blocks"]
        fl = b["flow"]
        # 좌표는 설계 단위(mm)로 적고 Y()로 세로 배율을 적용한다. 글자 크기는 배율과 무관하게 9pt 이상으로 둔다.
        KY = P4_KY
        HEAD = 24.0                                   # 레인 머리(아이콘, 이름, 설명)가 차지하는 높이
        Y = lambda v: round((v - 18) * KY + HEAD, 2)  # noqa: E731
        W = 150.0
        H = Y(188)
        LX = [0, 30, 60, 90, 120]
        heads = "".join(f'<div class="lane-head" style="left:{x}mm;top:0;width:30mm"><span class="ci">{self.ic(l["icon"], 5)}</span>'
                        f'<span class="n">{self.t(l["name"])}</span><span class="s">{self.t(l["sub"])}</span></div>'
                        for x, l in zip(LX, fl["lanes"]))
        boxes: list[str] = []
        lines: list[str] = []

        def bx(lane: int, y: float, h: float, text: str, cls: str = "auto", x_off: float = 1, w: float = 28) -> None:
            boxes.append(f'<div class="bx {cls}" style="left:{LX[lane] + x_off}mm;top:{Y(y)}mm;width:{w}mm;height:{round(h * KY, 2)}mm">{self.t(text)}</div>')

        def nb(lane: int, y: float, label: str, cls: str = "") -> None:
            boxes.append(f'<span class="nb {cls}" style="left:{LX[lane] - 1.6}mm;top:{Y(y) - 3.6}mm">{esc(label)}</span>')

        def ln(d: str, red: bool = False, dash: bool = False) -> None:
            """경로의 y 좌표는 설계 단위로 적고, M x y H x V y 형식만 쓴다."""
            col = "#da291c" if red else "#3d3935"
            mk = "ah-r" if red else "ah"
            da = ' stroke-dasharray="1 0.8"' if dash else ""
            lines.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{0.9 if red else 0.3}"{da} marker-end="url(#{mk})"/>')

        def hline(x0: float, y: float, x1: float, **kw: Any) -> None:
            ln(f"M{x0} {Y(y)}H{x1}", **kw)

        def vline(x: float, y0: float, y1: float) -> None:
            ln(f"M{x} {Y(y0)}V{Y(y1)}")

        # 1 매일 시장 동향: 주 흐름과 별개라 얇은 띠로 구분한다
        y = 21
        boxes.append(f'<div class="band1" style="left:0;top:{Y(y - 2.4)}mm;width:{W}mm;height:{round(17.6 * KY, 2)}mm"></div>')
        boxes.append(f'<div class="bx plain note1" style="left:1mm;top:{Y(y)}mm;width:56mm;height:{round(11 * KY, 2)}mm">{self.t(fl["t1_note"])}</div>')
        bx(2, y, 11.5, fl["t1a"]); bx(3, y, 14, fl["t1b"]); bx(4, y, 11.5, fl["t1c"])
        nb(2, y, "1")
        hline(89, y + 5.7, 90.6); hline(119, y + 5.7, 120.6)
        # 2 수집과 추출 실행
        y = 40
        bx(0, y, 11.5, fl["t2a"], "hum"); bx(2, y, 11.5, fl["t2b"])
        nb(0, y, "2")
        hline(29, y + 5.7, 60.6)
        # 3 AI 와 코드
        y3 = 57
        for i, (txt, cls) in enumerate(zip(fl["t3"], ("chipai", "chipcode", "chipai"))):
            bx(3, y3 + i * 9, 6.4, txt, cls)
            if i:
                vline(105, y3 + i * 9 - 2.6, y3 + i * 9 - 0.2)
        nb(3, y3, "3")
        ln(f"M75 {Y(51.7)}V{Y(y3 + 3.2)}H90.6")
        # 4 확률 분기
        dy = 86
        dcx, dhw, dhh = 105, 12, 7
        dyc = Y(dy + dhh)
        dh2 = dhh * KY
        diamond = (f'<path d="M{dcx} {Y(dy)}L{dcx + dhw} {dyc}L{dcx} {round(dyc + dh2, 2)}L{dcx - dhw} {dyc}Z" fill="#ffffff" stroke="#3d3935" stroke-width="0.35"/>'
                   f'<text x="{dcx}" y="{round(dyc + 1.2, 2)}" text-anchor="middle" font-size="3.4" font-weight="600" fill="#161616">{self.t(fl["t4d"])}</text>')
        vline(105, y3 + 2 * 9 + 6.4, dy - 0.3)
        nb(3, dy, "4")
        bx(4, dy + 1, 12, fl["t4hi"])
        hline(dcx + dhw, dy + dhh, 120.6)
        boxes.append(f'<div class="bx redt" style="left:61mm;top:{Y(dy - 0.4)}mm;width:28mm;height:{round(6 * KY, 2)}mm">{self.t(fl["t4mid"])}</div>')
        lines.append(f'<path d="M{dcx - dhw} {dyc}H62.2" fill="none" stroke="#da291c" stroke-width="0.9"/>'
                     f'<path d="M63.2 {round(dyc - 1.8, 2)}L59.6 {dyc}L63.2 {round(dyc + 1.8, 2)}Z" fill="#da291c"/>')
        bx(1, dy + 1, 12.5, fl["t5a"], "hum")
        bx(3, dy + 2 * dhh + 3, 14, fl["t4lo"], "plain", x_off=1.5, w=27)
        vline(105, dy + 2 * dhh, dy + 2 * dhh + 2.7)
        # 5 검수 결과 저장
        y5 = 126
        bx(4, y5, 11.5, fl["t5b"])
        nb(1, dy + 1, "5")
        ln(f"M45 {Y(dy + 13.5)}V{Y(y5 + 5.7)}H120.6")
        # 6 주간 마감
        y6 = 144
        bx(2, y6, 11.5, fl["t6a"]); bx(4, y6, 11.5, fl["t6b"])
        nb(2, y6, "6")
        hline(89, y6 + 5.7, 120.6)
        # 7 화면 배포와 실무자의 확인
        y7 = 163
        bx(2, y7, 11.5, fl["t7a"])
        bx(0, y7 - 2, 16.5, fl["t7b"], "goal")
        nb(2, y7, "7")
        ln(f"M135 {Y(y6 + 11.5)}V{Y(y7 + 5.7)}H89.4")
        hline(61, y7 + 5.7, 29.4)
        # 8 상시: 기준값과 사전
        y8 = 182
        bx(1, y8, 11.5, fl["t8a"], "dash"); bx(4, y8, 11.5, fl["t8b"], "dash")
        nb(1, y8, fl["always"], "al")
        hline(59, y8 + 5.7, 120.6, dash=True)
        seps = "".join(f'<path d="M{x} {HEAD - 1}V{H}" stroke="#c9c3be" stroke-width="0.25" stroke-dasharray="0.8 0.8"/>' for x in LX[1:])
        svg = (f'<svg style="position:absolute;left:0;top:0;width:{W}mm;height:{H}mm" viewBox="0 0 {W} {H}" aria-hidden="true">'
               f'{seps}{"".join(lines)}{diamond}</svg>')
        sw = ['<span class="sw" style="border:0.35mm solid var(--kp-ink)"></span>',
              '<span class="sw" style="background:var(--kp-paper-deep)"></span>',
              '<span class="sw" style="border:0.3mm dashed var(--kp-ink)"></span>',
              '<span class="sw" style="border-bottom:0.9mm solid var(--kp-red);height:1.6mm"></span>']
        legend = '<p class="legend4">' + "".join(f'<span>{s}{self.t(t)}</span>' for s, t in zip(sw, fl["legend"])) + "</p>"
        lanes = (f'<div style="width:{W}mm;height:{H}mm"><div class="lane-wrap" style="width:{W}mm;height:{H}mm">'
                 f'{svg}{heads}{"".join(boxes)}</div></div>')
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
        return [("p4.head", self.body_head(4, b["headline"])),
                ("p4.bottom", f'<div class="p4-bottom">{week}{receipt}</div>'),
                ("p4.note", f'<p class="sm mut">{self.t(b["note"])}</p>'),
                ("p4.flow", f'<div>{self.bh(fl["head"], fl.get("crit"))}{legend}<div style="margin-top:1.8mm">{lanes}</div></div>')]

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

    def five_step_table(self, tb: dict) -> str:
        """다섯 단계의 전후 비교 표(기존 방식, 적용 후, 예시 그림)."""
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
             f'display:flex;align-items:center;justify-content:center;font-size:9pt;font-weight:600;line-height:1.05;text-align:center">{self.t(fg["target"])}</span></div>'
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
        return table

    def p5_body(self) -> list[tuple[str, str]]:
        b = self.pages[4]["blocks"]
        tb = b["table"]
        table = self.five_step_table(tb)
        sh = b["shot"]
        legend = "".join(f'<span class="nw"><b class="red">{m["n"]}</b> {self.t(m["label"])}</span>' for m in sh["marks"])
        results = []
        for code in ORGS3[1:]:
            same, txt = self.pair_text(code)
            mark = ('<svg style="width:3.6mm;height:3.6mm;flex:none;margin-top:0.4mm" viewBox="0 0 4 4"><circle cx="2" cy="2" r="1.6" fill="#3d3935"/></svg>' if same else
                    '<svg style="width:3.6mm;height:3.6mm;flex:none;margin-top:0.4mm" viewBox="0 0 4 4"><circle cx="2" cy="2" r="1.6" fill="#fff" stroke="#3d3935" stroke-width="0.35"/><path d="M0.9 3.1L3.1 0.9" stroke="#3d3935" stroke-width="0.35"/></svg>')
            results.append(f'<div class="res{" same" if same else ""}">{mark}<span>{txt}</span></div>')
        mid = (f'<div style="margin-left:5mm">{self.shot(sh["img"], 145, marks=sh["marks"])}'
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
        return [("p5.head", self.body_head(5, b["headline"])),
                ("p5.situation", f'<p class="band"><span>{self.t(b["situation"])}</span></p>'),
                ("p5.table", f'<div>{self.bh(tb["head"], tb.get("crit"))}{table}</div>'),
                ("p5.shot", f'<div>{self.bh(sh["head"], sh.get("crit"))}{mid}</div>'),
                ("p5.effect", effect)]

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

    def gauge_html(self, g: dict, compact: bool = False) -> str:
        """확률 산정 모의 테스트 막대와 구간 눈금. compact 이면 초기 적재 매핑 문구를 뺀다."""
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
        chip = "" if compact else f'<p class="sm" style="margin-top:0.6mm">{self.t(g["chip"])}</p>'
        gauge = (f'<div>{self.bh(g["head"], g.get("crit"), "확률 산정 모델")}'
                 f'<p class="sm" style="font-weight:600">{self.t(g["stack_label"])}</p>{stack}'
                 f'<p class="sm" style="display:flex;justify-content:space-between;margin-top:0.4mm"><span>{self.t(g["seg_re"])}</span><span>{self.t(g["seg_rv"])}</span></p>'
                 f'<div style="display:flex;align-items:center;gap:2.4mm;margin:1.4mm 0 5mm"><span class="gbig">{self.t(g["big"])}</span>'
                 f'<span style="font-weight:600">{self.t(g["big_label"])}</span></div>{scale}'
                 f'<p style="margin-top:1mm">{self.t(g["line"])}</p>{chip}'
                 f'<p class="sm mut">{self.t(g["scope"])}</p></div>')
        return gauge

    def gold_html(self, gd: dict, ring_d: float = 22) -> str:
        """정답표 대조 링과 일치율이 낮은 영역의 막대."""
        rings = []
        for r in gd["rings"]:
            v = self.num(r["value"]); tot = self.num(r["total"]); hv = self.num(r["hatch"]) if r.get("hatch") else 0
            val = self.t(r["value"]) if not r.get("hatch") else self.t("{{fact:goldset_epost_benefit.auto_match}}") + "+" + self.t(r["hatch"])
            lg = f'<p class="sm mut">{self.t(r["legend"])}</p>' if r.get("legend") else ""
            rings.append(f'<div><div style="position:relative;display:inline-block">{self.ring(v, tot, hv, ring_d)}'
                         f'<span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:9pt">'
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
        return gold

    def p6_body(self) -> list[tuple[str, str]]:
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
        gauge = self.gauge_html(g)
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
                f'<div class="tiles" style="grid-template-columns:1fr 1fr">{"".join(self.tile(t, "mini") for t in on["tiles"])}</div></div>')
        gd = b["gold"]
        gold = self.gold_html(gd)
        tm = b["team"]
        team = self.p6_team(tm)
        return [("p6.head", self.body_head(6, b["headline"])),
                ("p6.g1", f'<div class="p6g">{roles}{gauge}</div>'),
                ("p6.g2", f'<div class="p6g">{onto}{gold}</div>'),
                ("p6.team", team)]

    def p6_team(self, tm: dict) -> str:
        W, H = 96.0, 60.0

        def node(x, y, w, h, title, sub, cls=""):
            style = {"me": "background:var(--kp-paper-deep)", "cc": "border:0.5mm solid var(--kp-ink);background:#fff",
                     "": "border:0.25mm solid var(--kp-ink);background:#fff", "gh": "border:0.25mm dashed var(--kp-ink);background:#fff"}[cls]
            return (f'<div style="position:absolute;left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;{style};display:flex;flex-direction:column;'
                    f'align-items:center;justify-content:center;text-align:center;line-height:1.2;padding:0.6mm">'
                    f'<b style="font-size:10pt">{self.t(title)}</b><span class="sm mut">{self.t(sub)}</span></div>')
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
                f'font-size:9pt;font-weight:600">{loop}{self.t(tm["ring"])}</div>')
        chart = f'<div style="position:relative;width:{W}mm;height:{H}mm">{svg}{"".join(parts)}{ring}</div>'
        tiles = "".join(self.tile(t) for t in tm["tiles"])
        return (f'<div>{self.bh(tm["head"], tm.get("crit"))}<div style="zoom:{TEAM_ZOOM};width:{W}mm;margin:0 auto">{chart}</div>'
                f'<p class="sm mut" style="margin:1.6mm 0 0.8mm">{self.t(tm["asof"])}</p>'
                f'<div class="tiles" style="grid-template-columns:repeat({len(tm["tiles"])},1fr)">{tiles}</div></div>')

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
        pct = pct_split([counts[st["key"]] for st in pg["states"]], targets)
        key = "".join(
            f'<span class="nw"><svg style="width:4.6mm;height:4.6mm;vertical-align:-1mm;margin-right:0.6mm" viewBox="0 0 6 6" aria-hidden="true">{look[st["key"]].format(cx="3")}</svg>'
            f'{self.t(st["label"])} <b>{counts[st["key"]]}곳</b> ({pct[i]:.1f}%)</span>'
            for i, st in enumerate(pg["states"]))
        seg = "".join(
            f'<span class="seg {st["key"]}" style="flex:{counts[st["key"]]} 1 0"><span>{pct[i]:.1f}%</span></span>'
            for i, st in enumerate(pg["states"]) if counts[st["key"]])
        return (f'<div class="prog"><p class="sh">{self.t(pg["head"])}</p><div style="display:flex;align-items:center;gap:3mm">{svg}</div>'
                f'<div class="pbar" role="img">{seg}</div>'
                f'<p class="sm" style="display:flex;flex-wrap:wrap;gap:0.6mm 4.4mm;margin-top:0.8mm">{key}</p></div>')

    def p7_body(self) -> list[tuple[str, str]]:
        b = self.pages[6]["blocks"]
        og = b["orgs"]
        nodes = []
        for k, n in enumerate(og["nodes"]):
            bd = f'<span class="bd">{self.t(n["badge"])}</span>' if n.get("badge") else ""
            nodes.append(f'<div class="nd {n["state"]}" style="flex:{1.45 if k == 2 else 1}">{bd}{self.ic(n["icon"], 5.4)}<p class="nm">{self.t(n["name"])}</p><p class="sb">{self.t(n["sub"])}</p></div>')
        flow = '<div class="orgflow">' + nodes[0] + "".join(f'<div class="ar">{self.arrow_svg(4, 3)}</div>{x}' for x in nodes[1:]) + "</div>"
        notes = "".join(f'<p class="sm mut">{self.t(x)}</p>' for x in og["notes"])
        tiles = f'<div class="tiles" style="grid-template-columns:1fr 1fr 1fr">{"".join(self.tile(t, "ev") for t in og["tiles"])}</div>'
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
        return [("p7.head", self.body_head(7, b["headline"])),
                ("p7.orgs", f'<div>{self.bh(og["head"], og.get("crit"), "우체국")}<div style="padding-top:2.6mm">{flow}</div><div style="margin:1.2mm 0">{notes}</div>{progress}{tiles}</div>'),
                ("p7.uses", f'<div>{self.bh(us["head"], us.get("crit"))}<div class="ucards">{cards}</div>'
                            f'<p class="sm" style="margin-top:1.4mm;border:0.25mm dashed var(--border-default);padding:1mm 1.6mm;color:var(--fg-muted)">{self.t(us["out"])}</p></div>'),
                ("p7.limits", f'<div>{self.bh(lm["head"], lm.get("crit"))}<div class="lims"><div><p class="sh">{self.t(lm["left_head"])}</p><ul>{left}</ul></div>'
                              f'<div><p class="sh">{self.t(lm["right_head"])}</p><ul>{right}</ul></div></div>'
                              f'<p class="sh" style="font-weight:600;margin:1.2mm 0 0.8mm">{self.t(lm["unmeasured_head"])}</p><div class="umg">{um}</div></div>')]

    # 8쪽 -------------------------------------------------------------------
    def p8_body(self) -> list[tuple[str, str]]:
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
        return [("p8.head", self.body_head(8, b["headline"])),
                ("p8.record", f'<div>{self.bh(rc["head"], rc.get("crit"), "users")}'
                              f'<div class="rec-none"><span class="zero">{self.lab("no_record")}</span><p>{self.t(rc["none"])}</p></div>'
                              f'<div style="margin-top:1.6mm">{evidence}</div></div>'),
                ("p8.table", f'<div><p style="margin:0 0 1mm">{self.t(rc["have"])}</p>'
                             f'<table class="rtab"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
                             f'<p style="margin-top:1.6mm;font-weight:600">{self.t(rc["next"])}</p></div>')]

    def output_blocks(self) -> list[tuple[str, str]]:
        o = self.c["output"]
        sep = " " if self.c.get("variant") == "v2" else "<br>"          # 버전 2 는 파일 이름과 설명을 한 줄에 쓴다
        links = "".join(f'<div class="l">{self.ic(l["icon"], 5)}<span class="nm">{self.t(l["name"])}</span>'
                        f'<span><span class="fn">{esc(l["file"])}</span>{sep}<span class="nt">{self.t(l["note"])}</span></span></div>'
                        for l in o["files"])
        oh = o["open_how"]
        links += (f'<div class="l">{self.ic(oh["icon"], 5)}<span class="nm">{self.t(oh["name"])}</span>'
                  f'<span>{self.t(oh["text"])}<br><span class="nt">{self.t(oh["note"])}</span></span></div>')
        play = ('<svg class="play" viewBox="0 0 10 10" aria-hidden="true"><circle cx="5" cy="5" r="4.6" fill="#161616" fill-opacity="0.72"/>'
                '<path d="M4 3L7.2 5L4 7z" fill="#ffffff"/></svg>')
        vids = "".join(f'<div class="s"><div class="im {self.img_cls(v["img"])}" role="img">{play}<span class="vl">{self.t(v["len"])}</span></div>'
                       f'<p class="lb">{self.t(v["label"])}</p></div>'
                       for v in o.get("videos", []))
        out = [("out.files", f'<div>{self.bh(o["head"]) if o.get("head") else ""}<div class="links">{links}</div></div>')]
        if vids:
            out.append(("out.videos", f'<div>{self.bh(o["videos_head"])}<div class="shots vids">{vids}</div></div>'))
        n = len(o.get("shots", []))
        for i, s_ in enumerate(o.get("shots", [])):
            html = f'<div class="srows">{self.shot_row(i, s_)}</div>'
            if i == 0:
                html = f'{self.bh(o["shots_head"])}{html}'
            if i == n - 1:
                html += f'<p class="sm mut" style="margin-top:2mm">{self.t(o["shots_note"])}</p>'
            out.append((f"out.shot{i}", f"<div>{html}</div>"))
        return out

    # 화면 캡처 쪽(2026-11-26 사용자 지시): 화면 이름과 설명이 먼저 오고, 다음 줄에 전체 캡처, 그 아래에 확대 컷을 둔다.
    # 전체 캡처(가로형)는 작성내용 칸의 폭(150mm)을 가득 쓴다. 확대 컷은 안의 글자가 인쇄 크기에서 7pt 이상이 되는 폭이다
    # (화면 글자 13px, 2배 배율로 찍은 컷의 css 폭이 W px 이면 W x 7pt / 13px x 0.3528mm 이상). 세로로 긴 비교 요약지 카드만
    # 전체 그림과 확대 컷을 나란히 둔다.
    FULL_W = {"summary": 150, "tab_gate": 150, "cancer_surgery": 147, "tab_insight": 147, "talk_preview": 72, "tab_graph": 150}
    CUT_W = {"cut_kpi": 126, "cut_gate": 130, "cut_cover": 128.4, "cut_insight": 124.6, "cut_talk": 72}

    def shot_row(self, i: int, s: dict) -> str:
        """화면 하나: 화면 이름과 설명, 다음 줄에 전체 캡처, 그 아래에 확대 컷."""
        title = f'<div class="st"><p class="lb">{i + 1}. {self.t(s["label"])}</p><p class="sm mut">{self.t(s["text"])}</p></div>'
        full = f'<div class="pf">{self.shot(s["img"], self.FULL_W[s["img"]])}</div>'
        if not s.get("cut"):
            return f'<div class="srow">{title}{full}</div>'
        cw = self.CUT_W[s["cut"]]
        cut = f'<div class="pc">{self.shot(s["cut"], cw)}</div>'
        if self.FULL_W[s["img"]] + cw <= 146:
            return f'<div class="srow">{title}<div class="pair">{full}{cut}</div></div>'
        return f'<div class="srow">{title}{full}{cut}</div>'

    # 버전 2: 평가기준 표시 없이 4쪽 이내로 줄인 판(content_v2.json 의 "variant": "v2") ----------------------------
    # 블록 id 의 절 번호는 content_v2.json 의 pages 순서(1 개요 … 6 사용 실적)를 따른다. 13쪽 판의 블록 함수는 그대로 두고,
    # 줄인 블록만 아래에서 따로 만든다. 도해 부품(타일, 막대, 링, 점 그림, 단계 표)은 13쪽 판의 것을 그대로 쓴다.
    def p2_body_v2(self) -> list[tuple[str, str]]:
        b = self.pages[1]["blocks"]
        fa = b["facts"]
        chips = "".join(f'<div class="c"><p class="k">{self.t(c["label"])}</p><p class="v">{self.t(c["value"])}</p></div>' for c in fa["chips"])
        w = b["why"]
        pages = self.num(w[0]["value"])
        c1 = (f'<div class="wcard"><p class="t"><span class="i">1</span>{self.t(w[0]["title"])}</p>'
              f'<div style="display:flex;align-items:flex-end;gap:1mm">{self.stack_svg(pages, 13, 13)}'
              f'<p class="big" style="font-size:20pt">{self.t(w[0]["value"])}<span class="u">{self.t(w[0]["unit"])}</span></p></div>'
              f'<p class="wl">{self.t(w[0]["caption"])}</p><p class="sm mut">{self.t(w[0]["note"])}</p></div>')
        rows = []
        for code in ORGS3:
            q = self.t("{{fact:simple_uw_questions_by_org." + code + ".period_question}}").replace("수술", "<u>수술</u>")
            rows.append(f'<p class="wl"><b>{self.org(code)}</b> {q}</p>')
        c2 = (f'<div class="wcard"><p class="t"><span class="i">2</span>{self.t(w[1]["title"])}</p>'
              f'<p class="sm mut">{self.t(w[1]["caption"])}</p>{"".join(rows)}<p class="sm" style="font-weight:600">{self.t(w[1]["tag"])}</p></div>')
        names = "".join(f'<p class="wl"><b>{self.org(code)}</b> {self.t("{{fact:example_cancer_surgery_names." + code + "}}")}</p>' for code in ORGS3)
        c3 = (f'<div class="wcard"><p class="t"><span class="i">3</span>{self.t(w[2]["title"])}</p>'
              f'<p class="sm mut">{self.t(w[2]["caption"])}</p>{names}</div>')
        tb = b["table"]
        ef = b["effect"]
        effect = (f'<div class="effect v2">'
                  f'<div class="side"><p class="k">{self.lab("effect")}: {self.t(ef["now_label"])}</p>'
                  f'<p class="ln"><span class="big">{self.t(ef["now_value"])}</span><span>{self.t(ef["now_sub"])}</span></p>'
                  f'<p class="sm mut">{self.t(ef["now_note"])}</p></div>'
                  f'<div class="ar" style="display:flex;align-items:center;justify-content:center">{self.arrow_svg(6, 3)}</div>'
                  f'<div class="side"><p class="k">{self.lab("effect")}: {self.t(ef["tool_label"])}</p>'
                  f'<p class="tl"><span class="badge-um">{self.t(ef["tool_badge"])}</span> {self.t(ef["tool_text"])}</p>'
                  f'<p class="struct"><b>{self.t(ef["tool_struct"])}</b> <span class="sm mut">({self.t(ef["tool_struct_note"])})</span></p></div></div>')
        out = [("p2.head", self.body_head(2, b.get("headline"))),
               ("p2.situation", f'<p class="band"><span class="k">{self.t(b["situation"]["label"])}</span><span>{self.t(b["situation"]["text"])}</span></p>'),
               ("p2.facts", f'<div><div class="p2-chips">{chips}</div><p class="sm mut" style="margin-top:0.8mm">{self.t(fa["note"])}</p></div>'),
               ("p2.why", f'<div>{self.bh(b["why_head"])}<div class="p2-why v2">{c1}{c2}{c3}</div></div>')]
        if b.get("notes"):
            notes = "".join(f'<p style="font-size:10pt;line-height:1.4">{self.t(n)}</p>' for n in b["notes"])
            out.append(("p2.notes", f'<div>{notes}</div>'))
        out += [("p2.table", f'<div class="t5">{self.bh(tb["head"])}<p class="sm mut" style="margin:0 0 1.2mm">{self.t(tb["situation"])}</p>'
                             f'{self.five_step_table(tb)}</div>'),
                ("p2.effect", effect)]
        return out

    def p3_body_v2(self) -> list[tuple[str, str]]:
        b = self.pages[2]["blocks"]
        st = b["steps"]
        cells = ""
        for i, s_ in enumerate(st["items"]):
            hero = " hero" if s_.get("hero") else ""
            roles = "".join(self.role(r) for r in s_["roles"])
            cells += (f'<div class="nm{hero}"><span class="no">{i + 1}</span><span>{self.t(s_["name"])}</span>{roles}</div>'
                      f'<div class="tx{hero}">{self.t(s_["text"])}</div><div class="tl{hero}">{self.t(s_["tool"])}</div>')
        au = b["auto"]
        auto = (f'<div><p class="band" style="padding:0.9mm 2.4mm"><span class="k">{self.t(au["label"])}</span><span>{self.t(au["text"])}</span></p>'
                f'<p class="sm mut" style="margin-top:0.8mm">{self.t(au["note"])}</p></div>')
        od = b["order"]
        return [("p3.head", self.body_head(3, b.get("headline"))),
                ("p3.steps", f'<div><div class="stab">{cells}</div></div>'),
                ("p3.auto", auto),
                ("p3.order", f'<div>{self.bh(od["head"])}{self.order_html(od, od.get("flex"))}</div>')]

    def p4_body_v2(self) -> list[tuple[str, str]]:
        b = self.pages[3]["blocks"]
        ro = b["roles"]
        chips = "".join(f'<p class="rl">{self.role(c["role"])}<span>{self.t(c["text"])}</span></p>' for c in ro["chips"])
        roles = f'<div class="rls"><p class="lb">{self.t(ro["head"])}</p><div>{chips}</div></div>'
        on = b["onto"]
        onto = (f'<div style="margin-top:1.6mm">{self.bh(on["head"], None, "관계 그래프")}'
                f'<div class="tiles" style="grid-template-columns:1fr 1fr">{"".join(self.tile({k: v for k, v in t.items() if k != "sub"}, "mini") for t in on["tiles"])}</div></div>')
        tm = b["team"]
        lines = "".join(f'<p class="tr"><b>{self.t(x["who"])}</b> {self.t(x["role"])}</p>' for x in tm["lines"])
        team = (f'<div>{self.bh(tm["head"])}{lines}<p class="sm mut" style="margin:0.6mm 0 1.2mm">{self.t(tm["note"])}</p>'
                f'<div class="tiles" style="grid-template-columns:repeat({len(tm["tiles"])},1fr)">{"".join(self.tile(t, "mini") for t in tm["tiles"])}</div></div>')
        return [("p4.head", self.body_head(4, b.get("headline"))),
                ("p4.g1", f'<div class="p6g">{self.gauge_html(b["gauge"], compact=True)}{self.gold_html(b["gold"], 19)}</div>'),
                ("p4.g2", f'<div class="p6g"><div>{roles}{onto}</div>{team}</div>')]

    def p5_body_v2(self) -> list[tuple[str, str]]:
        b = self.pages[4]["blocks"]
        og = b["orgs"]
        notes = "".join(f'<p class="sm mut">{self.t(x)}</p>' for x in og.get("notes", []))
        us = b["uses"]
        rows = "".join(f'<div class="nmc">{self.ic(c["icon"], 4.8)}<b>{self.t(c["name"])}</b></div><div class="txc">{self.t(c["text"])}</div>' for c in us["items"])
        lm = b["limits"]
        left = "".join(f"<li>{self.t(x)}</li>" for x in lm["left"])
        right = "".join(f"<li>{self.t(x)}</li>" for x in lm["right"])
        um = "".join(f'<p class="um"><span class="badge-um">{self.t(lm["badge"])}</span><span>{self.t(x)}</span></p>' for x in lm["unmeasured"])
        return [("p5.head", self.body_head(5, b.get("headline"))),
                ("p5.orgs", f'<div>{self.bh(og["head"], None, "우체국")}<p style="margin-bottom:1mm">{self.t(og["next"])}</p>{self.org_progress(og["progress"])}'
                            f'{f"<div style=margin-top:1mm>{notes}</div>" if notes else ""}</div>'),
                ("p5.uses", f'<div>{self.bh(us["head"])}<div class="urows">{rows}</div>'
                            f'<p class="sm mut" style="margin-top:1mm">{self.t(us["out"])}</p></div>'),
                ("p5.limits", f'<div>{self.bh(lm["head"])}<div class="lims"><div><p class="sh">{self.t(lm["left_head"])}</p><ul>{left}</ul></div>'
                              f'<div><p class="sh">{self.t(lm["right_head"])}</p><ul>{right}</ul></div></div>'
                              f'<p class="sh" style="font-weight:600;margin:0.6mm 0 0.8mm">{self.t(lm["unmeasured_head"])}</p><div class="umg">{um}</div></div>')]

    def p6_body_v2(self) -> list[tuple[str, str]]:
        b = self.pages[5]["blocks"]
        rc = b["record"]

        def pill_of(x: str) -> str:
            if x.startswith("state:"):
                return self.c["states"][x[6:]]["on" if self.states[x[6:]] else "off"]["pill"]
            return x
        rows = []
        for r in rc["rows"]:
            pill = pill_of("state:" + r["state"]) if r.get("state") else r["pill"]
            pcls = "chip ink" if pill == "반영" else ("chip line" if pill in ("일부 반영", "진행 중") else "chip dash")
            rows.append(f'<tr><td class="a">{self.t(r["ask"])}</td><td class="d">{self.t(r["done"])}</td>'
                        f'<td class="s"><span class="{pcls}">{esc(pill)}</span></td></tr>')
        head = "".join(f"<th>{self.t(c)}</th>" for c in rc["cols"])
        pills = [pill_of(x) for x in rc["status_all"]]       # 확인한 사항 전체의 상태(표에는 대표 사례만 적는다)
        done = sum(1 for x in pills if x in ("반영", "일부 반영"))
        gold = (self.num("{{fact:goldset_epost_benefit.auto_match}}") + self.num("{{fact:goldset_epost_benefit.manual_match}}")
                + self.num("{{fact:goldset_hanwha_benefit.match}}"))
        gold_all = self.num("{{fact:goldset_epost_benefit.items}}") + self.num("{{fact:goldset_hanwha_benefit.items}}")
        calc = {"opinions": f"{done}/{len(pills)}", "goldset": f"{int(gold)}/{int(gold_all)}"}
        ev = "".join(self.tile({**t, "value": calc[t["calc"]] if t.get("calc") else t["value"]}, "ev") for t in rc["evidence"])
        return [("p6.head", self.body_head(6, b.get("headline"))),
                ("p6.record", f'<div class="rec-none"><span class="zero">{self.lab("no_record")}</span><p>{self.t(rc["none"])}</p>'
                              f'<div class="tiles" style="flex:none;width:{rc.get("tile_w", 34)}mm">{ev}</div></div>'),
                ("p6.table", f'<div><p style="margin:0 0 1mm">{self.t(rc["have"])}</p>'
                             f'<table class="rtab"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
                             f'<p style="margin-top:0.8mm;font-weight:600">{self.t(rc["next"])}</p></div>')]

    # 조립 -----------------------------------------------------------------
    def all_blocks(self) -> dict[str, str]:
        bodies = [self.p1_body, self.p2_body, self.p3_body, self.p4_body, self.p5_body, self.p6_body, self.p7_body, self.p8_body,
                  self.output_blocks]
        if self.c.get("variant") == "v2":
            bodies = [self.p1_body, self.p2_body_v2, self.p3_body_v2, self.p4_body_v2, self.p5_body_v2, self.p6_body_v2, self.output_blocks]
        blocks: dict[str, str] = {}
        for fn in bodies:
            for bid, html in fn():
                blocks[bid] = html
        return blocks

    def pages_html(self) -> str:
        blocks = self.all_blocks()
        flat = [bid for ids in self.layout for bid in ids]
        if flat != list(blocks):
            missing = [b for b in blocks if b not in flat]
            extra = [b for b in flat if b not in blocks]
            self.errors.append(f"layout 이 블록 순서와 다름: 빠진 블록 {missing}, 없는 블록 {extra}" + ("" if missing or extra else ", 순서가 바뀜"))
            return ""
        f = self.c["form"]["output"]
        out = []
        out_started = False
        for pi, ids in enumerate(self.layout):
            no = pi + 1
            body_ids = [b for b in ids if sec_of(b)]
            out_ids = [b for b in ids if not sec_of(b)]
            html = []
            if body_ids and not body_ids[0].endswith(".head") and no > 1:
                html.append(f'<div class="blk hd">{self.body_head(sec_of(body_ids[0]), None, cont=True)}</div>')
            html += [f'<div class="blk{" hd" if b.endswith(".head") else ""}" data-blk="{b}">{blocks[b]}</div>' for b in body_ids]
            body_html = "".join(html)
            gap = self.gaps[pi]
            style = f"--gap:{gap}mm;gap:var(--gap)" if gap else ""
            if no == 1:
                out.append(self.p1(body_html, style))
                continue
            secs = list(dict.fromkeys(sec_of(b) for b in body_ids))
            rows = []
            if body_ids:
                rows.append(("top", self.cont_left(secs), "body", body_html, style))
            if out_ids:
                label = (f'<p class="cont">{esc(f["cont"]).replace(" (계속)", "<br>(계속)")}</p>' if out_started else f'<p>{esc(f["label"])}</p>') + f'<p class="guide">{esc(f["guide"])}</p>'
                out_started = True
                rows.append(("top", label, "body", "".join(f'<div class="blk" data-blk="{b}">{blocks[b]}</div>' for b in out_ids)))
            out.append(self.page(no, self.frame(rows, "auto " + "auto " * (len(rows) - 1) + "1fr")))
        return "\n".join(out)


# ---------------------------------------------------------------------------
# 빌드
# ---------------------------------------------------------------------------
def tokens_from_deck(tpl: Path) -> str:
    m = re.search(r":root\s*\{[^{}]*\}", tpl.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"덱 틀에서 :root 토큰을 찾지 못했습니다: {tpl}")
    return m.group(0)


def check_links(doc: str) -> list[str]:
    """외부 요청이 될 주소와 클릭 링크(<a>), 주소 글자(http)를 모두 찾는다. 문서에는 하나도 없어야 한다."""
    hits = deck_build.check_external(doc)
    hits += [m.group(0) for m in re.finditer(r"<a[\s>][^>]*>", doc, re.I)]
    hits += [doc[m.start():m.start() + 60] for m in re.finditer(r"https?:", doc, re.I)]
    return hits


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
    pages = glue(form.pages_html())
    errors = form.errors + form.ctx.errors
    if errors:
        raise SystemExit("빌드를 멈춥니다:\n  " + "\n  ".join(errors))
    digits = digits_outside(content)
    css_images = "\n".join(
        f'.im-{re.sub(r"[^A-Za-z0-9_-]", "_", n)}{{background-image:url(data:image/jpeg;base64,'
        f'{base64.b64encode(form.images[n].read_bytes()).decode("ascii")})}}' for n in form.img_used)
    tpl = tpl_path.read_text(encoding="utf-8")
    if content.get("variant") == "v2":
        tpl = tpl.replace("</style>", V2_CSS + "</style>", 1)
    doc = (tpl.replace("__HTML_TITLE__", esc(content["html_title"]))
              .replace("<!--__FONT_NOTICE__-->", FONT_NOTICE)
              .replace("/*__FONT_FACES__*/", deck_build.font_faces(fonts_css))
              .replace("/*__TOKENS__*/", tokens_from_deck(DECK / "tpl.html"))
              .replace("/*__IMAGES__*/", css_images)
              .replace("<!--__SPRITE__-->", P.sprite())
              .replace("<!--__PAGES__-->", pages))
    leftovers = re.findall(r"__[A-Z_]+__|\{\{[^}]*\}\}", doc)
    if leftovers:
        raise SystemExit(f"채우지 못한 자리: {leftovers[:5]}")
    hits = check_links(doc)
    if hits:
        raise SystemExit("외부 요청이 될 주소:\n  " + "\n  ".join(hits))
    if strict and digits:
        raise SystemExit("자리 표시 밖의 숫자:\n  " + "\n  ".join(digits))
    info = {"pages": form.total, "images": list(form.img_used), "digits": digits, "facts_used": form.ctx.used_facts,
            "states": form.states, "identity": identity is not None}
    return doc, info


# 버전 2 전용 스타일(tpl.html 은 13쪽 판과 함께 쓰므로 바꾸지 않고, 버전 2 를 만들 때만 덧붙인다). 글자 크기는 9pt 이상.
V2_CSS = """
.p2-why.v2 { grid-template-columns: 0.72fr 1.1fr 1.38fr; gap: 2mm; }
.p2-why.v2 .wcard { padding: 1.2mm 1.8mm 1.4mm; gap: 0.8mm; }
.wl { font-size: 10pt; line-height: 1.32; margin: 0; }
.t5 .p5t { grid-template-columns: 16mm 1.1fr 3mm 1.5fr 28mm; column-gap: 1.2mm; row-gap: 0.9mm; }
.t5 .p5t .bf { padding: 0.9mm 1.6mm; }
.t5 .p5t .af { padding: 0.8mm 1.6mm; }
.effect.v2 { grid-template-columns: 0.8fr 7mm 1.5fr; }
.effect.v2 .side { padding: 1.2mm 2.2mm; gap: 0.6mm; }
.effect.v2 .ln { display: flex; align-items: baseline; gap: 2mm; }
.stab { display: grid; grid-template-columns: 38mm minmax(0, 1fr) 60mm; border-top: 0.35mm solid var(--kp-ink); }
.stab > div { padding: 0.5mm 1.6mm; border-bottom: 0.25mm solid var(--border-subtle); }
.stab > .h { font-size: 9pt; font-weight: 600; color: var(--fg-muted); padding-top: 0.5mm; padding-bottom: 0.5mm; }
.stab > .nm { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6mm 1.2mm; font-weight: 600; font-size: 10.5pt; line-height: 1.2; }
.stab .no { width: 5.4mm; height: 5.4mm; border-radius: 50%; background: var(--kp-ink); color: #fff; font-size: 9pt; display: inline-flex; align-items: center; justify-content: center; flex: none; }
.stab > .tx { display: flex; align-items: center; line-height: 1.34; }
.stab > .tl { font-size: 9pt; color: var(--fg-muted); line-height: 1.3; display: flex; align-items: center; }
.stab > .hero { background: var(--kp-paper); }
.stab > .nm.hero { box-shadow: inset 0.8mm 0 0 var(--kp-red); }
.stab > .nm.hero .no { background: var(--kp-red); }
.bh { padding-bottom: 0.3mm; margin-bottom: 0.9mm; font-size: 10.5pt; }
.hbar { margin-top: 0.4mm; }
.rtab td.a { width: 44%; }
.rec-none { padding: 1.2mm 3mm; }
.band.v2 .k { flex: none; }
.order .nd { padding: 1.2mm 2mm; gap: 0.8mm; }
.rls { background: var(--kp-paper); padding: 1.2mm 2mm; display: grid; grid-template-columns: 17mm minmax(0, 1fr); column-gap: 1.2mm; align-items: center; }
.rls .lb { font-size: 9pt; font-weight: 600; line-height: 1.3; }
.rls .rl .role { min-width: 10mm; }
.rls .rl { display: flex; gap: 1.6mm; align-items: center; line-height: 1.32; margin: 0 0 0.5mm; }
.tr { line-height: 1.34; margin: 0 0 0.4mm; }
.urows { display: grid; grid-template-columns: 34mm minmax(0, 1fr); }
.urows > div { padding: 0.8mm 1.4mm; border-bottom: 0.25mm solid var(--border-subtle); line-height: 1.34; display: flex; align-items: center; gap: 1.2mm; }
.urows > .txc { display: block; }
"""


LAYOUT_JS = """() => {
  const out = [];
  const PT9 = 9 * 96 / 72 - 0.05;
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
        if (sz < PT9) out.push(`${no}쪽: 9pt 미만 글자(그림 안) "${n.textContent.trim().slice(0, 20)}"`);
        continue;
      }
      if (fs < PT9) out.push(`${no}쪽: 9pt 미만 글자 ${(fs * 72 / 96).toFixed(1)}pt "${n.textContent.trim().slice(0, 20)}"`);
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
    ap.add_argument("--strict", action="store_true", help="자리 표시 밖 숫자, 채우지 못한 자리, 넘침과 9pt 미만 글자를 오류로")
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
