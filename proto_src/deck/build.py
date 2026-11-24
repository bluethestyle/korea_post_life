#!/usr/bin/env python3
"""발표 덱 빌드: content/NN.json + content/_deck.json + facts.json + refs.json + tpl.html → index.html(오프라인 단독 HTML 한 파일).

실행:
    python3 build.py                                   # 리포 기본값: content/ → out/index.html
    python3 build.py --out ../../site/deck/index.html  # 배포본
    python3 build.py --content-dir <폴더> --facts <facts.json> --out <index.html> --only 7,12-14 [--strict]

- 장마다 파일 하나(content/01.json ~ 26.json). 덱 공통 설정(챕터, 일곱 단계, 회사 칩, 용어 풀이 표)은 content/_deck.json.
  --content-dir 의 폴더에 _deck.json 이 없으면 이 파일 옆 content/_deck.json 을 쓴다(--deck 으로 따로 줄 수 있다).
- 글의 자리 표시를 채운다.
    {{fact:열쇠}}, {{fact:열쇠.하위키}}, {{fact:열쇠.0}}  facts.json 의 값(정수는 천 단위 쉼표, 목록은 쉼표로 이음)
    {{fact:열쇠|f2}}, {{fact:열쇠|f1}}, {{fact:열쇠|pct}} 실수의 형식(소수 둘째, 첫째 자리, 백분율 정수)
    {{len:열쇠}}  목록이나 사전의 길이,  {{asof:열쇠}}  그 값의 기준일
    {{ref:열쇠}}, {{ref:열쇠.하위키}}                     refs.json 의 외부 사실. kind 가 press 면 "보도 기준" 배지가 붙고,
                                                       꼬리말에 출처 도메인이 붙는다
    {{todo:내용}}                                       확인 필요 표시(점선 상자 안의 글)
    [[용어]]                                            용어 밑줄(풀이는 장의 terms 로 꼬리 위 띠에)
  facts.json, refs.json 에 없는 열쇠가 하나라도 있으면 빌드가 멈춘다.
- 부품(C1~C20)은 deckparts.py 가 빌드 때 HTML 과 SVG 로 그린다. 글자 수 상한을 넘으면 경고를 적는다(--strict 면 멈춘다).
- 사진은 assets/<이름>.jpg 가운데 장이 부른 것만 base64 로 한 번 심는다(tools/capture_app.py 가 만든다).
  덱 폴더 바로 위에 stills/ 가 있으면(작업 폴더 구성) 그 JPEG 도 이름으로 부를 수 있다. --assets 를 여러 번 줄 수 있다.
- 글꼴은 fonts_v4.css 에서 PLKo(SUIT 서브셋) @font-face 만 골라 넣는다.
- 결과 HTML 에 외부 주소를 부르는 src, href, url(), @import 가 있으면 멈춘다.
- 영상 장은 out 폴더에 media/partN.mp4 가 있을 때만 <video> 를 넣는다. mp4 를 out/media/ 에 넣은 뒤 다시 빌드한다.
- 같은 입력이면 같은 바이트가 나온다(시각, 난수를 쓰지 않는다).
- 덱이 쓴 facts 와 refs 열쇠를 장마다 facts_used.json 에 적는다.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import deckparts as P  # noqa: E402

KINDS = ("cover", "body", "video", "closing")
STATUSES = ("kept", "revised", "new", "video", "demo")
REF_KINDS = ("official", "academic", "press")


def find_upward(rel: str) -> Path | None:
    for base in [HERE, *HERE.parents]:
        cand = base / rel
        if cand.is_file():
            return cand
    return None


def parse_only(text: str | None) -> set[int] | None:
    if not text:
        return None
    out: set[int] = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(chunk))
    return out


def load_slides(content_dir: Path) -> list[dict]:
    files = sorted(p for p in content_dir.glob("*.json") if re.fullmatch(r"\d{2}\.json", p.name))
    if not files:
        raise SystemExit(f"장 파일(NN.json)이 없습니다: {content_dir}")
    slides = []
    for p in files:
        s = json.loads(p.read_text(encoding="utf-8"))
        no = int(p.stem)
        if s.get("no") != no:
            raise SystemExit(f"{p.name}: no 가 {s.get('no')!r} 이다(파일 번호 {no} 와 같아야 한다)")
        if s.get("kind", "body") not in KINDS:
            raise SystemExit(f"{p.name}: kind 는 {KINDS} 가운데 하나")
        if s.get("status") not in STATUSES:
            raise SystemExit(f"{p.name}: status 는 {STATUSES} 가운데 하나")
        if not isinstance(s.get("chapter"), int) or not 0 <= s["chapter"] <= 7:
            raise SystemExit(f"{p.name}: chapter 는 0(안내)~6, 7(마무리)")
        if not s.get("headline"):
            raise SystemExit(f"{p.name}: headline 이 없다")
        slides.append(s)
    return slides


def load_refs(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))["refs"]
    for key, r in data.items():
        if r.get("kind") not in REF_KINDS:
            raise SystemExit(f"refs.json {key}: kind 는 {REF_KINDS} 가운데 하나(확인하지 못한 사실은 싣지 않는다)")
        urls = r.get("urls") or []
        if not urls or not all(isinstance(u, str) and u.startswith("https://") for u in urls):
            raise SystemExit(f"refs.json {key}: urls 에 https 출처가 하나 이상 있어야 한다")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("checked", ""))):
            raise SystemExit(f"refs.json {key}: checked(확인한 날, YYYY-MM-DD)가 없다")
        if "value" not in r:
            raise SystemExit(f"refs.json {key}: value 가 없다")
    return data


# ---------------------------------------------------------------------------
# 장의 프레임
# ---------------------------------------------------------------------------
class Frame:
    def __init__(self, ctx: P.Ctx, total: int, media_root: Path):
        self.ctx = ctx
        self.total = total
        self.media_root = media_root
        self.videos: list[str] = []

    def blocks(self, s: dict, region: tuple[float, float, float, float]) -> str:
        rx, ry, rw, rh = region
        out = []
        for i, spec in enumerate(s.get("diagram", [])):
            where = f"diagram[{i}]"
            box = spec.get("box") or [0, 0, rw, rh]
            if len(box) != 4:
                self.ctx.warn(where, "box 는 [x, y, 폭, 높이]")
                box = [0, 0, rw, rh]
            # 폭이나 높이를 null 로 두면 영역의 오른쪽 끝, 아래 끝까지
            x, y = float(box[0]), float(box[1])
            w = rw - x if box[2] is None else float(box[2])
            h = rh - y if box[3] is None else float(box[3])
            if x < -0.5 or y < -0.5 or x + w > rw + 0.5 or y + h > rh + 0.5:
                self.ctx.warn(where, f"box {box} 가 도해 영역(0, 0, {P.px(rw)}, {P.px(rh)})을 벗어남")
            inner = P.render(self.ctx, spec, w, h, where)
            out.append(f'<div class="blk" style="{P.box_style(x, y, w, h)}">{inner}</div>')
        return (f'<div class="dg" data-region="{P.px(rw)}x{P.px(rh)}" style="{P.box_style(rx, ry, rw, rh)}">'
                f'{"".join(out)}</div>')

    def footer(self, s: dict) -> str:
        src = self.ctx.t(s.get("source", ""), None)
        doms = self.ctx.domains.get(self.ctx.slide, [])
        if doms:
            src = (src + " / " if src else "") + "외부 출처: " + ", ".join(doms)
        # 꼬리말은 한 행(20px, 폭 약 1,560px)에 들어가야 한다. 영문 도메인이 섞여 글자 수 대신 폭 어림으로 본다
        width = P.text_width(P.plain(src), 20)
        if width > P.SOURCE_WIDTH:
            self.ctx.warn("source", f"폭 약 {width:,.0f}px > {P.SOURCE_WIDTH:,}px(외부 출처 도메인 포함, 한글로 약 "
                                    f"{P.SOURCE_WIDTH // 19}자)")
        return (f'<footer class="ft"><p class="src">{src}</p>'
                f'<p class="pg">{s["no"]:02d} / {self.total:02d}</p></footer>')

    def notes(self, s: dict) -> str:
        return f'<aside class="notes">{self.ctx.t(s.get("notes", ""))}</aside>'

    def section(self, s: dict, cls: str, inner: str) -> str:
        title = P.plain(self.ctx.sub(s["headline"]))
        return (f'<section class="slide {cls}" id="s{s["no"]}" data-no="{s["no"]}" data-status="{P.esc(s["status"])}" '
                f'data-title="{P.esc(title)}" aria-roledescription="장" aria-label="{s["no"]} / {self.total}: {P.esc(title)}">'
                f'{inner}{self.notes(s)}</section>')

    def header(self, s: dict, dark: bool = False) -> str:
        return (f'<header class="hd"><p class="doc">{P.esc(self.ctx.deck.get("app_name", ""))}</p>'
                f'{P.chapter_bar(self.ctx, s["chapter"], dark)}</header>')

    def bands(self, s: dict) -> tuple[str, float]:
        """요점과 용어 풀이 띠. (HTML, 도해 영역의 아래 끝)"""
        html_ = []
        bottom = P.BAND_BOTTOM
        fn = s.get("footnote")
        if fn:
            # 각주: 꼬리말 바로 위 한두 행(20px). 역할별 모델 이름처럼 화면에 작게만 둘 글
            text = self.ctx.t(fn, None)
            width = P.text_width(P.plain(text), 20) * 0.9
            lines = 1 if width <= P.REGION_W else 2
            if width > P.REGION_W * 2:
                self.ctx.warn("footnote", f"폭 약 {width:,.0f}px > {P.REGION_W * 2:,}px(두 행)")
            bottom -= 26 * lines + 2
            html_.append(f'<p class="fn ax" style="top:{bottom}px;height:{26 * lines + 2}px">{text}</p>')
            bottom -= 8
        terms = s.get("terms", [])
        if terms:
            bottom -= 64
            html_.append(f'<div class="gl" style="top:{bottom}px">{P.gloss_band(self.ctx, terms, P.REGION_W)}</div>')
        pts = s.get("points", [])
        if len(pts) > P.LIMITS["points"]:
            self.ctx.warn("points", f"요점 {len(pts)}개 > {P.LIMITS['points']}개")
        if pts:
            bottom -= 40 * len(pts) + (8 if terms else 0)
            rows = "".join(f'<p>{self.ctx.t(p, P.LIMITS["point"], f"points[{i}]")}</p>' for i, p in enumerate(pts))
            html_.append(f'<div class="pts" style="top:{bottom}px">{rows}</div>')
        return "".join(html_), bottom - 16

    def headline(self, s: dict, limit: int, cls: str = "hl") -> str:
        tag = ""
        if s["status"] == "demo":
            tag = '<span class="hl-tag">시연</span>'
        return f'<h2 class="{cls}">{tag}{self.ctx.t(s["headline"], limit, "headline")}</h2>'

    def region_top(self, s: dict) -> float:
        """도해 영역의 위. 헤드라인이 한 줄로 들어갈 것 같으면(글자 폭 어림) 위로 당긴다. frame.top 으로 정할 수 있다."""
        if "top" in s.get("frame", {}):
            return float(s["frame"]["top"])
        width = P.headline_width(P.plain(self.ctx.sub(s["headline"])), s["status"] == "demo")
        return P.REGION_TOP_ONE_LINE if width <= 1740 else P.REGION_TOP

    def k_body(self, s: dict) -> str:
        bands, bottom = self.bands(s)
        top = self.region_top(s)
        region = (P.REGION_X, top, P.REGION_W, bottom - top)
        inner = (self.header(s) + self.headline(s, P.LIMITS["headline"]) + self.blocks(s, region) + bands)
        return self.section(s, "body-slide" + (" closing" if s.get("kind") == "closing" else ""), inner + self.footer(s))

    k_closing = k_body

    def k_cover(self, s: dict) -> str:
        d = self.ctx.deck
        sub = s.get("subtitle", d.get("cover_subtitle", ""))      # 부제(출품작 이름 아래). 리드는 장의 headline
        meta = "".join(f'<div class="cm"><p class="l">{self.ctx.t(m.get("l", ""), 8, f"meta[{i}].l")}</p>'
                       f'<p class="v">{self.ctx.t(m.get("v", ""), 24, f"meta[{i}].v")}</p></div>'
                       for i, m in enumerate(s.get("meta", [])))
        title = (f'<div class="cover-body"><p class="badge">{self.ctx.t(s.get("badge", d.get("badge", "")), 30, "badge")}</p>'
                 f'<h1 class="cover-h1">{d.get("cover_title") or P.esc(d.get("app_name", ""))}</h1>'
                 + (f'<p class="cover-sub">{self.ctx.t(sub, 40, "subtitle")}</p>' if sub else "") +
                 f'<p class="cover-lead">{self.ctx.t(s["headline"], P.LIMITS["cover_lead"], "headline")}</p>'
                 + (f'<div class="cover-meta">{meta}</div>' if meta else "") + "</div>")
        blocks = self.blocks(s, (0, 0, P.STAGE_W, P.STAGE_H)) if s.get("diagram") else ""
        board = ""
        if not s.get("no_board"):
            board = (f'<div class="dg" style="{P.box_style(80, 880, 1760, 120)}"><div class="blk" style="{P.box_style(0, 0, 1760, 120)}">'
                     f'{P.render(self.ctx, {"use": "C1", "mode": "board"}, 1760, 120, "board")}</div></div>')
        return self.section(s, "cover", '<div class="spine"></div>' + title + blocks + board)

    def k_video(self, s: dict) -> str:
        v = s.get("video", {})
        src = v.get("src", "")
        part = v.get("part")
        tag = f'<span class="vchip">영상 {P.esc(part)}</span>' if part is not None else '<span class="vchip">영상</span>'
        dur = f'<span class="vchip dur">{self.ctx.t(v["dur"], 10, "video.dur")}</span>' if v.get("dur") else ""
        q = f'<p class="vq">{self.ctx.t(v["q"], P.LIMITS["question"], "video.q")}</p>' if v.get("q") else ""
        video = ""
        if src and (self.media_root / src).is_file():
            video = (f'<video src="{P.esc(src)}" controls preload="metadata" playsinline '
                     f'aria-label="{P.esc(P.plain(self.ctx.sub(s["headline"])))}"></video>')
            self.videos.append(src)
        # 영상 자리: 정지 화면 한 컷을 어둡게 깔고 가운데에 재생 표시와 길이. 정지 화면 안의 작은 글자는 읽히지 않으므로
        # 컷을 여럿 늘어놓지 않는다(2026-11-24 화면 점검)
        stills = v.get("stills", [])
        if len(stills) > 1:
            self.ctx.warn("video.stills", f"정지 화면 {len(stills)}컷(한 컷)")
        st = "".join(f'<div class="vst {self.ctx.img(x, f"video.stills[{i}]")}" role="img" aria-label="영상의 정지 화면"></div>'
                     for i, x in enumerate(stills[:1]))
        play = ('<div class="vplay"><span class="vplay-b" aria-hidden="true"><svg width="72" height="72" viewBox="0 0 72 72">'
                '<path d="M24 14L60 36L24 58z"/></svg></span>'
                f'<p class="vplay-t">발표 때 이 자리에서 영상이 재생됩니다</p></div>')
        ph = f'<div class="vph{" has-st" if st else ""}">{st}{play}</div>'
        inner = (f'<div class="spine"></div>{self.header(s)}'
                 f'<div class="vhead">{tag}{dur}{self.headline(s, P.LIMITS["video_headline"], "vhl")}{q}</div>'
                 f'<div class="vframe">{video}{ph}</div>{self.footer(s)}')
        return self.section(s, "video", inner)

    def render(self, s: dict) -> str:
        self.ctx.slide = f"{s['no']:02d}"
        heroes, bigs = P.count_marks(s.get("diagram", []))
        if heroes > 1:
            self.ctx.warn("diagram", f"강조 {heroes}곳(한 장에 한 곳)")
        if bigs > 3:
            self.ctx.warn("diagram", f"큰 숫자 {bigs}개(한 장에 셋 이하)")
        return getattr(self, "k_" + s.get("kind", "body"))(s)


# ---------------------------------------------------------------------------
# 점검과 조립
# ---------------------------------------------------------------------------
EXTERNAL = [
    re.compile(r"""\b(?:src|href|poster|srcset|action|data|formaction)\s*=\s*["']?\s*(?:[a-z][a-z0-9+.-]*:|//)(?!data:)""", re.I),
    re.compile(r"""url\(\s*["']?\s*(?:https?:|//|ftp:)""", re.I),
    re.compile(r"@import", re.I),
]


def check_external(doc: str) -> list[str]:
    hits = []
    for rx in EXTERNAL:
        for m in rx.finditer(doc):
            snippet = doc[m.start():m.start() + 80]
            if re.match(r"""\w+\s*=\s*["']?\s*data:""", snippet, re.I):
                continue
            hits.append(snippet)
    return hits


SKIP_DIGIT_KEYS = {"no", "id", "kind", "status", "use", "box", "img", "src", "href", "stills", "legacy", "d", "axis", "frame",
                   "step", "from", "to", "on", "at", "n", "ref", "x", "y", "fig_h", "label_w", "limit", "zone", "chapter",
                   "tier", "offset", "part"}


def digits_outside(slides: list[dict]) -> list[str]:
    """자리 표시 밖에 숫자를 직접 적은 글(검토용 목록. 빌드를 멈추지 않는다)."""
    found = []

    def walk(o: Any, where: str) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in SKIP_DIGIT_KEYS:
                    continue
                walk(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")
        elif isinstance(o, str):
            bare = re.sub(r"<[^>]+>", "", P.PH.sub("", o))
            for m in re.finditer(r"[0-9][0-9.,~:-]*", bare):
                ctx = bare[max(0, m.start() - 8):m.end() + 6]
                found.append(f"{where}: {m.group(0)}  …{ctx}…")

    for s in slides:
        walk(s, f"{s['no']:02d}")
    return found


def font_faces(css_path: Path) -> str:
    css = css_path.read_text(encoding="utf-8")
    blocks = re.findall(r"@font-face\s*\{[^{}]*\}", css)
    keep = [b for b in blocks if re.search(r'font-family:\s*"PLKo"', b)]
    if not keep:
        raise SystemExit(f"PLKo @font-face 를 찾지 못했습니다: {css_path}")
    return "\n".join(keep)


FONT_NOTICE = ("<!-- 글꼴: SUIT (Regular 400, SemiBold 600), Copyright (c) 2022, SUNN (http://sun.fo/suit), "
               "with Reserved Font Name SUIT. SIL Open Font License 1.1 (https://openfontlicense.org). "
               "쓰는 글자만 남긴 서브셋이며, 글꼴 파일 안의 글꼴 이름은 \"PL Sub <원래 이름의 머리글자> <굵기>\" 꼴로 바꿨고 "
               "원래의 저작권과 라이선스 표기는 파일 안에 그대로 있다. -->")


@dataclass
class Result:
    html: str
    used: dict
    warnings: list[str]
    slides: list[dict]
    videos: list[str] = field(default_factory=list)
    digits: list[str] = field(default_factory=list)


def default_deck_path(content_dir: Path) -> Path:
    own = content_dir / "_deck.json"
    return own if own.is_file() else HERE / "content" / "_deck.json"


def build_deck(content_dir: Path, facts_path: Path, refs_path: Path, fonts_css: Path, tpl_path: Path = HERE / "tpl.html",
               assets_dir: Path | list[Path] = HERE / "assets", media_root: Path = HERE / "out", deck_path: Path | None = None,
               only: set[int] | None = None) -> Result:
    deck = json.loads((deck_path or default_deck_path(content_dir)).read_text(encoding="utf-8"))
    slides = load_slides(content_dir)
    total = len(slides)
    facts = json.loads(facts_path.read_text(encoding="utf-8"))["facts"]
    refs = load_refs(refs_path)
    dirs = assets_dir if isinstance(assets_dir, list) else [assets_dir]
    images = {}
    for d in dirs:
        for p in sorted(Path(d).glob("*.jpg")):
            images.setdefault(p.stem, str(p))
    ctx = P.Ctx(facts, refs, deck, images)
    frame = Frame(ctx, total, media_root)
    shown = [s for s in slides if only is None or s["no"] in only]
    slides_html = "\n".join(frame.render(s) for s in shown)
    if ctx.errors:
        raise SystemExit("빌드를 멈춥니다:\n  " + "\n  ".join(ctx.errors))

    css_images = "\n".join(
        f'.im-{re.sub(r"[^A-Za-z0-9_-]", "_", name)}{{background-image:url(data:image/jpeg;base64,'
        f'{base64.b64encode(Path(images[name]).read_bytes()).decode("ascii")})}}'
        for name in ctx.img_used)
    tpl = tpl_path.read_text(encoding="utf-8")
    doc = (tpl.replace("__HTML_TITLE__", P.esc(deck.get("html_title", "")))
              .replace("<!--__FONT_NOTICE__-->", FONT_NOTICE)
              .replace("/*__FONT_FACES__*/", font_faces(fonts_css))
              .replace("/*__IMAGES__*/", css_images)
              .replace("<!--__SPRITE__-->", P.sprite())
              .replace("<!--__SLIDES__-->", slides_html))
    leftovers = re.findall(r"__[A-Z_]+__|\{\{[^}]*\}\}", doc)
    if leftovers:
        raise SystemExit(f"채우지 못한 자리: {leftovers[:5]}")
    hits = check_external(doc)
    if hits:
        raise SystemExit("외부 요청이 될 주소:\n  " + "\n  ".join(hits))
    used = {"facts": ctx.used_facts, "refs": ctx.used_refs}
    return Result(doc, used, ctx.warnings, shown, frame.videos, digits_outside(shown))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content-dir", default=str(HERE / "content"), help="장 파일(NN.json) 폴더")
    ap.add_argument("--deck", default=None, help="덱 공통 설정(기본: 장 폴더의 _deck.json, 없으면 content/_deck.json)")
    ap.add_argument("--facts", default=None, help="facts.json(기본: 덱 폴더 위의 facts.json, 없으면 리포의 presentation_animation/facts.json)")
    ap.add_argument("--refs", default=str(HERE / "refs.json"))
    ap.add_argument("--fonts-css", default=None)
    ap.add_argument("--tpl", default=str(HERE / "tpl.html"))
    ap.add_argument("--assets", action="append", default=None, help="사진 폴더(여러 번 줄 수 있음. 기본: assets, 위 폴더의 stills)")
    ap.add_argument("--out", default=str(HERE / "out" / "index.html"))
    ap.add_argument("--used", default=None, help="쓴 열쇠 목록(기본: --content-dir 가 기본값일 때만 facts_used.json)")
    ap.add_argument("--only", default=None, help="이 장들만 빌드(예: 7,12-14). 쪽 번호는 전체 기준")
    ap.add_argument("--strict", action="store_true", help="글자 수 상한 경고가 있으면 1로 끝낸다")
    ap.add_argument("--digits", action="store_true", help="자리 표시 밖의 숫자(검토용)를 모두 보인다")
    a = ap.parse_args()

    # 기본값: 덱 폴더 바로 위의 facts.json, fonts_v4.css(작업 폴더 구성)가 있으면 그것, 없으면 리포 안의 파일
    facts_path = Path(a.facts) if a.facts else (
        HERE.parent / "facts.json" if (HERE.parent / "facts.json").is_file() else find_upward("presentation_animation/facts.json"))
    fonts_path = Path(a.fonts_css) if a.fonts_css else (
        HERE.parent / "fonts_v4.css" if (HERE.parent / "fonts_v4.css").is_file() else find_upward("proto_src/fonts/fonts_v4.css"))
    if not facts_path or not facts_path.is_file():
        raise SystemExit("facts.json 을 찾지 못했습니다. --facts 로 넘긴다")
    if not fonts_path or not fonts_path.is_file():
        raise SystemExit("fonts_v4.css 를 찾지 못했습니다. --fonts-css 로 넘긴다")
    out = Path(a.out)
    assets = [Path(x) for x in a.assets] if a.assets else [HERE / "assets"] + (
        [HERE.parent / "stills"] if (HERE.parent / "stills").is_dir() else [])
    res = build_deck(Path(a.content_dir), facts_path, Path(a.refs), fonts_path, Path(a.tpl), assets, out.parent,
                     Path(a.deck) if a.deck else None, parse_only(a.only))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(res.html.encode("utf-8"))
    used_path = a.used or (str(HERE / "facts_used.json") if Path(a.content_dir).resolve() == (HERE / "content").resolve()
                           and a.only is None else None)
    if used_path:
        Path(used_path).write_text(json.dumps(res.used, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out} {out.stat().st_size:,} 바이트, 장 {len(res.slides)}개, 외부 요청 0, "
          f"넣은 영상 {len(res.videos)}개{' ' + ', '.join(res.videos) if res.videos else ''}")
    print(f"글자 수 상한과 장 규칙 경고 {len(res.warnings)}건")
    for w in res.warnings:
        print("  " + w)
    if res.digits:
        print(f"자리 표시 밖의 숫자 {len(res.digits)}곳(검토용{', --digits 로 모두 보기' if not a.digits else ''})")
        for d in (res.digits if a.digits else res.digits[:10]):
            print("  " + d)
    if a.strict and res.warnings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
