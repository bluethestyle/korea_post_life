"""발표 덱의 도해 부품(C1~C20)과 장의 공통 프레임.

build.py 가 읽는다. 부품은 모두 빌드 때 HTML 과 인라인 SVG 로 그린다(브라우저의 스크립트로 그리지 않는다).
도형과 선은 SVG, 글자는 SVG 위에 얹은 HTML 이다. 색은 tpl.html 의 :root 토큰만 쓴다.

부품 함수의 형식: fn(ctx, spec, w, h, where) -> str
- spec: 장 파일(content/NN.json)의 diagram 항목 하나. "use" 가 부품 이름이다.
- w, h: 부품이 차지할 상자의 폭과 높이(px, 1920x1080 무대 기준).
- where: 경고에 적을 위치(예: "diagram[0].C4.rows[1]").
글자는 모두 ctx.t(글, 상한, 위치)로 넣는다. 자리 표시({{fact:}} 따위)를 채우고, 글자 수가 상한을 넘으면 경고를 남긴다.
부품의 입력 형식과 글자 수 상한은 COMPONENTS.md 에 있다.
"""
from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

STAGE_W, STAGE_H = 1920, 1080
REGION_X, REGION_W = 80, 1760          # 본문 도해 영역의 가로(무대 좌표)
REGION_TOP = 320                       # 본문 도해 영역의 위(헤드라인 두 줄)
REGION_TOP_ONE_LINE = 240              # 헤드라인이 한 줄일 때
BAND_BOTTOM = 984                      # 요점과 용어 풀이 띠의 아래 끝(꼬리말 위)
FOOTER_TOP = 1000
SOURCE_WIDTH = 1560                    # 꼬리말 출처 한 행의 폭(px)
# 글자 크기 기준(2026-11-24 상향). tpl.html 의 CSS 와 tools/shot.py 의 SMALL_PX, LABEL_PX 와 같다
LABEL_PX = 26                          # 내용을 전하는 글의 하한
AUX_PX = 22                            # 보조 글(축 눈금, 꼬리말, 각주, 용어 풀이, 칩과 배지)의 하한, 슬라이드 안 글자의 하한
GLOSS_H = 72                           # 용어 풀이 띠의 높이(22px 두 행)
BUILD_STEPS = 8                        # 블록 등장 순서(build)의 최대 단계. 디자인 시스템 덱 빌드 예산(8단계, 4초 이하)

PH = re.compile(r"\{\{(fact|len|asof|ref|todo|name):([^{}|]+?)(?:\|([a-z0-9]+))?\}\}")
TERM = re.compile(r"\[\[([^\[\]]+)\]\]")

# 장 단위 상한
LIMITS = {
    "headline": 50, "video_headline": 50, "cover_lead": 50, "point": 30, "points": 2, "source": 80, "terms": 3, "gloss": 30,
    "question": 50,
}


def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def plain(text: str) -> str:
    """화면에 보일 글자만(배지 글자와 태그를 뺌). 글자 수를 셀 때 쓴다."""
    text = re.sub(r'<span class="pb">[^<]*</span>', "", text)
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def px(v: float) -> str:
    return f"{round(v, 1):g}"


# ---------------------------------------------------------------------------
# 사실 자료와 외부 출처 채우기, 경고
# ---------------------------------------------------------------------------
class Ctx:
    def __init__(self, facts: dict, refs: dict, deck: dict, images: dict[str, str]):
        self.facts = facts                    # 열쇠 → {value, as_of, ...}
        self.refs = refs                      # 열쇠 → {value, kind, urls, ...}
        self.deck = deck
        self.images = images                  # 이름 → 파일 경로(있는 것만)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.used_facts: dict[str, list[str]] = {}
        self.used_refs: dict[str, list[str]] = {}
        self.domains: dict[str, list[str]] = {}
        self.img_used: list[str] = []
        self.slide = "덱"
        self.terms_on_slide: list[str] = []
        icon_reset(deck.get("icons"))

    # 값 찾기
    @staticmethod
    def _walk(value: Any, rest: list[str], path: str) -> Any:
        for part in rest:
            if isinstance(value, list):
                if not re.fullmatch(r"-?\d+", part) or not -len(value) <= int(part) < len(value):
                    raise KeyError(f"목록 첨자 없음: {path}")
                value = value[int(part)]
            elif isinstance(value, dict):
                if part not in value:
                    raise KeyError(f"하위키 없음: {path}")
                value = value[part]
            else:
                raise KeyError(f"하위키를 둘 수 없는 값: {path}")
        return value

    @staticmethod
    def fmt(value: Any, spec: str | None) -> str:
        if isinstance(value, bool) or value is None:
            raise TypeError(f"글로 적을 수 없는 값: {value!r}")
        if isinstance(value, int):
            if spec:
                raise TypeError("정수에는 형식을 붙이지 않는다")
            return f"{value:,}"
        if isinstance(value, float):
            if spec == "f2":
                return f"{value:,.2f}"
            if spec == "f1":
                return f"{value:,.1f}"
            if spec == "pct":
                return f"{value * 100:,.0f}"
            if spec:
                raise TypeError(f"모르는 형식: {spec}")
            return repr(value)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join(Ctx.fmt(v, spec) for v in value)
        raise TypeError(f"글로 적을 수 없는 값: {type(value).__name__}")

    def _note(self, table: dict[str, list[str]], key: str) -> None:
        used = table.setdefault(self.slide, [])
        if key not in used:
            used.append(key)

    def value(self, kind: str, path: str) -> Any:
        """자리 표시 하나의 값(형식을 붙이기 전). 없으면 KeyError."""
        key, *rest = path.split(".")
        if kind == "ref":
            if key not in self.refs:
                raise KeyError(f"refs.json 에 열쇠 없음: {key}")
            return self._walk(self.refs[key]["value"], rest, path)
        if key not in self.facts:
            raise KeyError(f"facts.json 에 열쇠 없음: {key}")
        return self._walk(self.facts[key]["value"], rest, path)

    def sub(self, text: str) -> str:
        def repl(m: re.Match) -> str:
            kind, path, spec = m.group(1), m.group(2).strip(), m.group(3)
            if kind == "todo":
                return f'<span class="todo-i"><b>확인 필요</b> {esc(path)}</span>'
            if kind == "name":
                # 여러 장이 함께 쓰는 도구와 모델 이름(_deck.json 의 names). 철자를 한 곳에서 정한다
                names = self.deck.get("names", {})
                if path == "about" or not isinstance(names.get(path), str):
                    self.errors.append(f"[{self.slide}] {m.group(0)}: _deck.json names 에 열쇠 없음: {path}")
                    return m.group(0)
                return esc(names[path])
            key = path.split(".")[0]
            try:
                v = self.value(kind, path)
                if kind == "len":
                    if not isinstance(v, (list, dict)):
                        raise TypeError(f"길이를 셀 수 없는 값: {path}")
                    out = f"{len(v):,}"
                elif kind == "asof":
                    out = self.facts[key]["as_of"]
                else:
                    out = self.fmt(v, spec)
            except (KeyError, TypeError) as exc:
                self.errors.append(f"[{self.slide}] {m.group(0)}: {exc}")
                return m.group(0)
            if kind == "ref":
                ref = self.refs[key]
                self._note(self.used_refs, key)
                for u in ref.get("urls", []):
                    host = urlparse(u).netloc.removeprefix("www.")
                    doms = self.domains.setdefault(self.slide, [])
                    if host and host not in doms:
                        doms.append(host)
                badge = '<span class="pb">보도 기준</span>' if ref.get("kind") == "press" else ""
                return html.escape(out, quote=False) + badge
            self._note(self.used_facts, key)
            return html.escape(out, quote=False)

        return PH.sub(repl, text)

    def t(self, text: Any, limit: int | None = None, where: str = "") -> str:
        """글 하나를 채워 HTML 로. 글자 수(공백 포함, 배지와 태그 제외)가 limit 를 넘으면 경고."""
        if text is None:
            return ""
        text = str(text)
        out = self.sub(text)
        out = TERM.sub(lambda m: f'<span class="term">{m.group(1)}</span>', out)
        if limit is not None:
            n = len(plain(out))
            if n > limit:
                self.warn(where, f"{n}자 > {limit}자: {plain(out)[:24]}")
        return out

    def num(self, v: Any, where: str = "") -> float:
        """숫자 자리(막대 높이, 비율 따위). 자리 표시면 채워서 숫자로."""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        if isinstance(v, str):
            m = PH.fullmatch(v.strip())
            if m and m.group(1) in ("fact", "ref"):
                try:
                    val = self.value(m.group(1), m.group(2).strip())
                except KeyError as exc:
                    self.errors.append(f"[{self.slide}] {where} {v}: {exc}")
                    return 0.0
                self._note(self.used_refs if m.group(1) == "ref" else self.used_facts, m.group(2).split(".")[0].strip())
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    return float(val)
            try:
                return float(plain(self.sub(v)).replace(",", ""))
            except ValueError:
                pass
        self.errors.append(f"[{self.slide}] {where}: 숫자로 읽을 수 없는 값 {v!r}")
        return 0.0

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"[{self.slide}] {where}: {msg}")

    def img(self, name: str, where: str) -> str:
        """사진 이름(assets/<이름>.jpg). 덱에 한 번만 심고 CSS 클래스로 부른다."""
        name = re.sub(r"^assets/|\.jpe?g$", "", str(name))
        if name not in self.images:
            self.errors.append(f"[{self.slide}] {where}: 사진 없음 assets/{name}.jpg")
        elif name not in self.img_used:
            self.img_used.append(name)
        return f"im-{re.sub(r'[^A-Za-z0-9_-]', '_', name)}"


# ---------------------------------------------------------------------------
# C18 아이콘 세트(한 번 정의하고 <use> 로 다시 씀)
# 아이콘은 두 묶음이다.
# - 덱 자체 아이콘(ICONS, 48 격자, 선 3): 디자인 시스템에 같은 뜻의 도안이 없는 것(AI, 코드, 사람, 문서 더미, 표, A4 따위)
# - 디자인 시스템 "발표용(우체국)"의 Lucide 아이콘 55종(icons/*.svg, 24 격자, 선 2, ISC 라이선스는 icons/LICENSE.txt)
# 장 파일의 "icon" 에는 덱 아이콘 사전(_deck.json 의 icons, 개념 → 아이콘 이름)의 개념 이름, Lucide 이름, 덱 자체 이름
# 가운데 하나를 쓴다. 같은 개념은 덱 전체에서 같은 아이콘이 되도록 개념 이름을 먼저 쓴다.
# 덱 자체 이름 가운데 디자인 시스템에 같은 뜻의 도안이 있는 것(ICON_ALIASES)은 디자인 시스템 도안으로 그린다.
# 빌드는 장에서 실제로 쓴 아이콘만 스프라이트에 심는다(sprite()).
# ---------------------------------------------------------------------------
ICONS = {
    "doc": '<path d="M12 5h17l9 9v29H12z"/><path d="M29 5v9h9"/><path d="M18 24h14M18 31h14M18 38h9"/>',
    "stack": '<path d="M16 9h22v30H16z"/><path d="M12 13v30h22"/><path d="M8 17v30h22" opacity=".6"/><path d="M21 18h12M21 25h12M21 32h8"/>',
    "ai": '<rect x="13" y="13" width="22" height="22" rx="3"/><path d="M19 13V7M29 13V7M19 41v-6M29 41v-6M13 19H7M13 29H7M41 19h-6M41 29h-6"/>'
          '<path d="M19.5 29.5l4.5-11 4.5 11M21 26h6"/>',
    "code": '<path d="M18 8c-4 0-5 2-5 6v5c0 3-2 5-5 5 3 0 5 2 5 5v5c0 4 1 6 5 6"/><path d="M30 8c4 0 5 2 5 6v5c0 3 2 5 5 5-3 0-5 2-5 5v5c0 4-1 6-5 6"/>',
    "person": '<circle cx="24" cy="15" r="7"/><path d="M9 42c0-9 7-14 15-14s15 5 15 14"/>',
    "search": '<circle cx="21" cy="21" r="12"/><path d="M30 30l11 11"/>',
    "check": '<path d="M9 25l10 10 20-21"/>',
    "table": '<rect x="6" y="9" width="36" height="30" rx="2"/><path d="M6 18h36M6 28h36M18 9v30"/>',
    "graph": '<circle cx="11" cy="13" r="5"/><circle cx="37" cy="11" r="5"/><circle cx="23" cy="36" r="5"/><circle cx="40" cy="34" r="4"/>'
             '<path d="M15 16l6 15M33 13l-8 19M16 13h16M28 36h8"/>',
    "monitor": '<rect x="5" y="8" width="38" height="25" rx="2"/><path d="M18 42h12M24 33v9"/>',
    "a4": '<path d="M12 4h24v40H12z"/><path d="M17 12h14M17 19h14M17 26h14M17 33h8"/>',
    "copy": '<rect x="15" y="15" width="24" height="26" rx="2"/><path d="M10 33V8h22"/>',
    "print": '<path d="M14 18V6h20v12"/><rect x="6" y="18" width="36" height="16" rx="2"/><path d="M14 28h20v14H14z"/>',
    "camera": '<path d="M6 15h9l3-5h12l3 5h9v24H6z"/><circle cx="24" cy="27" r="7"/>',
    "clock": '<circle cx="24" cy="24" r="17"/><path d="M24 13v11l8 5"/>',
    "building": '<path d="M6 42h36M9 18h30M24 6l16 10H8z"/><path d="M13 22v16M21 22v16M27 22v16M35 22v16"/>',
    "video": '<rect x="5" y="10" width="38" height="28" rx="3"/><path d="M20 17v14l11-7z"/>',
    "arrow": '<path d="M6 24h34M30 14l10 10-10 10"/>',
    "dot": '<circle cx="24" cy="24" r="13" fill="currentColor"/>',
    "square": '<rect x="11" y="11" width="26" height="26" fill="currentColor"/>',
}
# 덱 자체 아이콘 가운데 디자인 시스템 사전(reference/icons-logos.md 5절)에 같은 뜻의 도안이 있는 것: 디자인 시스템 것을 쓴다
ICON_ALIASES = {"doc": "file-text", "check": "badge-check", "graph": "network"}
ICON_DIR = Path(__file__).resolve().parent / "icons"
LUCIDE_STROKE = 2          # 디자인 시스템 규칙: 24 격자에 선 2


def _load_lucide() -> dict[str, str]:
    """icons/*.svg(lucide-static)의 안쪽 도형만 읽는다. 주석과 바깥 <svg> 는 버린다."""
    out: dict[str, str] = {}
    if not ICON_DIR.is_dir():
        return out
    for p in sorted(ICON_DIR.glob("*.svg")):
        text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
        m = re.search(r"<svg\b[^>]*>(.*)</svg>", text, flags=re.S)
        if m:
            out[p.stem] = re.sub(r"\s+", " ", m.group(1)).replace("> <", "><").strip()
    return out


LUCIDE = _load_lucide()

# 빌드 한 번의 아이콘 상태(Ctx 가 만들어질 때 비운다): 덱 아이콘 사전, 쓴 아이콘, 모르는 이름
ICON_STATE: dict[str, Any] = {"dict": {}, "used": [], "unknown": []}


def icon_reset(deck_icons: dict | None) -> None:
    ICON_STATE["dict"] = {k: v for k, v in (deck_icons or {}).items() if not k.startswith("_")}
    ICON_STATE["used"] = []
    ICON_STATE["unknown"] = []


def resolve_icon(name: str) -> str | None:
    """개념 이름(덱 아이콘 사전), Lucide 이름, 덱 자체 이름을 스프라이트 id 로. 모르면 None."""
    name = str(name).strip()
    name = ICON_STATE["dict"].get(name, name)
    name = ICON_ALIASES.get(name, name)
    if name in LUCIDE:
        return f"ic-{name}"
    if name in ICONS:
        return f"i-{name}"
    return None


def mark_icon(sid: str) -> None:
    if sid not in ICON_STATE["used"]:
        ICON_STATE["used"].append(sid)


def sprite() -> str:
    """패턴과 화살촉, 그리고 이번 빌드에서 쓴 아이콘만(이름순으로 늘 같은 바이트)."""
    syms = []
    for sid in sorted(ICON_STATE["used"]):
        kind, name = sid.split("-", 1)
        if kind == "ic":
            syms.append(f'<symbol id="{sid}" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-width="{LUCIDE_STROKE}" stroke-linecap="round" stroke-linejoin="round">{LUCIDE[name]}</g></symbol>')
        else:
            syms.append(f'<symbol id="{sid}" viewBox="0 0 48 48">{ICONS[name]}</symbol>')
    return ('<svg class="sprite" width="0" height="0" aria-hidden="true" focusable="false"><defs>'
            '<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<rect width="10" height="10" fill="#ffffff"/><path d="M0 0v10" stroke="#3d3935" stroke-width="3"/></pattern>'
            '<pattern id="hatch-m" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<path d="M0 0v8" stroke="#5c5650" stroke-width="2"/></pattern>'
            '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0 0L10 5L0 10z" fill="#5c5650"/></marker>'
            '<marker id="ah-r" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0 0L10 5L0 10z" fill="#da291c"/></marker>'
            f'</defs>{"".join(syms)}</svg>')


def icon(name: str, size: int = 48, cls: str = "") -> str:
    sid = resolve_icon(name)
    if sid is None:
        if name not in ICON_STATE["unknown"]:
            ICON_STATE["unknown"].append(str(name))
        sid = "i-doc"
    mark_icon(sid)
    extra = f" {cls}" if cls and cls != "ic" else ""
    return (f'<svg class="ic{extra}" width="{size}" height="{size}" viewBox="0 0 48 48" aria-hidden="true">'
            f'<use href="#{sid}"/></svg>')


def text_width(text: str, size: float) -> float:
    """글자 폭 어림(px). 한글은 글자 크기만큼, 영문과 숫자는 0.58배, 빈칸은 0.3배."""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += size * 0.3
        elif ord(ch) >= 0x1100:
            w += size * 0.96
        else:
            w += size * 0.6
    return w


def headline_width(text: str, demo: bool = False) -> float:
    """헤드라인(64px, 굵게, 자간 -0.02em)의 한 줄 폭 어림. 브라우저에서 잰 폭이 text_width 의 0.87배 안팎이었다
    (2026-11-24, 21장 실측). 시연 장은 앞의 "시연" 칩 폭을 더한다."""
    return text_width(text, 64) * 0.87 + (120 if demo else 0)


def clamp_center(cx: float, text: str, size: float, w: float) -> float:
    """가운데 맞춤 라벨이 상자 밖으로 나가지 않게 가운데 x 를 옮긴다."""
    half = text_width(text, size) / 2 + 4
    return min(max(cx, half), max(half, w - half))


def chevron(direction: str = "r", size: int = 40, cls: str = "chev") -> str:
    d = {"r": "M10 6l16 14-16 14", "d": "M6 10l14 16 14-16"}[direction]
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 40 40" aria-hidden="true">'
            f'<path d="{d}" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ---------------------------------------------------------------------------
# 렌더링 도우미
# ---------------------------------------------------------------------------
RENDER: dict[str, Callable[..., str]] = {}


def part(name: str):
    def deco(fn):
        RENDER[name] = fn
        return fn
    return deco


def render(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    use = spec.get("use")
    if use not in RENDER:
        ctx.errors.append(f"[{ctx.slide}] {where}: 모르는 부품 {use!r}")
        return ""
    return RENDER[use](ctx, spec, w, h, f"{where}.{use}")


def box_style(x: float, y: float, w: float, h: float) -> str:
    return f"left:{px(x)}px;top:{px(y)}px;width:{px(w)}px;height:{px(h)}px"


def org_chip(ctx: Ctx, code: str, extra: str = "") -> str:
    org = ctx.deck.get("orgs", {}).get(code, {"name": code, "style": "other"})
    return f'<span class="org org-{esc(org.get("style", "other"))}{extra}">{esc(org["name"])}</span>'


def state_mark(state: str, size: int = 28) -> str:
    """가입 가능은 채운 원, 가입 제한은 빈 원에 사선(색만으로 구분하지 않는다)."""
    r = size / 2 - 2
    c = size / 2
    if state == "open":
        return (f'<svg class="sm" width="{size}" height="{size}" aria-hidden="true">'
                f'<circle cx="{c}" cy="{c}" r="{r}" fill="#3d3935"/></svg>')
    off = r * 0.7
    return (f'<svg class="sm" width="{size}" height="{size}" aria-hidden="true"><circle cx="{c}" cy="{c}" r="{r}" fill="none" '
            f'stroke="#5c5650" stroke-width="2.5"/><path d="M{c - off} {c + off}L{c + off} {c - off}" stroke="#5c5650" stroke-width="2.5"/></svg>')


# ---------------------------------------------------------------------------
# C1 챕터 바
# ---------------------------------------------------------------------------
def chapter_bar(ctx: Ctx, chapter: int, dark: bool = False) -> str:
    """머리 오른쪽의 번호 원 여섯과 지금 챕터 이름. chapter 0(안내)과 7(마무리)은 켠 원이 없다."""
    chs = ctx.deck["chapters"]
    n = len(chs)
    d, gap = 36, 72
    wsvg = d + gap * (n - 1) + 4
    circles = []
    for i, ch in enumerate(chs):
        cx = 2 + d / 2 + gap * i
        on = ch["n"] == chapter
        if i:
            circles.append(f'<path d="M{cx - gap + d / 2 + 6} 20H{cx - d / 2 - 6}" class="cb-ln"/>')
        cls = "cb-on" if on else "cb-off"
        circles.append(f'<circle cx="{cx}" cy="20" r="{d / 2 - 1}" class="{cls}"/>'
                       f'<text x="{cx}" y="27" text-anchor="middle" class="{cls}-t">{ch["n"]}</text>')
    label = ""
    cur = next((c for c in chs if c["n"] == chapter), None)
    if cur:
        label = f'<span class="cb-l">{ctx.t(cur["q"], 18, "chapters.q")}</span>'
    elif chapter == 7:
        label = f'<span class="cb-l">{esc(ctx.deck.get("closing_label", "마무리"))}</span>'
    dk = " cb-dark" if dark else ""
    return (f'<div class="cb{dk}">{label}<svg class="cb-svg" width="{wsvg}" height="40" viewBox="0 0 {wsvg} 40" '
            f'aria-label="챕터 {chapter} / {n}">{"".join(circles)}</svg></div>')


def ref_pages(refs: list) -> str:
    """근거 장 번호 목록을 짧게: [22, 23, 24] → "22~24장", [14, 17] → "14, 17장"(셋 이상 이어지면 물결로 묶음)."""
    nums = sorted({int(r) for r in refs})
    runs: list[list[int]] = []
    for n in nums:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    parts = [f"{r[0]}~{r[-1]}" if len(r) >= 3 else ", ".join(map(str, r)) for r in runs]
    return (", ".join(parts) + "장") if parts else ""


@part("C1")
def c1(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    mode = spec.get("mode", "board")
    chs = ctx.deck["chapters"]
    if mode == "board":
        cells = "".join(f'<div class="c1b-i"><span class="c1-n">{c["n"]}</span>'
                        f'<span class="c1b-q">{ctx.t(c["q"], 18, f"{where}.chapters[{i}].q")}</span></div>'
                        for i, c in enumerate(chs))
        return f'<div class="c1b">{cells}</div>'
    rows = []
    answers = spec.get("answers", [])
    if len(answers) > len(chs):
        ctx.warn(where, f"답이 {len(answers)}행 > {len(chs)}행")
    rh = min(90, h / max(1, len(answers)))
    for i, a in enumerate(answers):
        ch = next((c for c in chs if c["n"] == a.get("n")), {"q": "", "n": a.get("n")})
        refs = ref_pages(a.get("ref", []))
        hero = " hero" if a.get("hero") else ""
        rows.append(f'<div class="c1a-r{hero}" style="height:{px(rh)}px"><span class="c1-n">{esc(ch["n"])}</span>'
                    f'<span class="c1a-q">{ctx.t(ch["q"], 18, f"{where}.q")}</span>'
                    f'<span class="c1a-a">{ctx.t(a.get("a", ""), 40, f"{where}.answers[{i}].a")}</span>'
                    f'<span class="c1a-ref ax">{esc(refs)}</span></div>')
    return f'<div class="c1a">{"".join(rows)}</div>'


# ---------------------------------------------------------------------------
# C2 일곱 단계 구조도와 C20 역할 레인
# ---------------------------------------------------------------------------
ROLE_ICON = {"AI": "ai", "코드": "code", "사람": "person"}
ROLE_CLS = {"AI": "ai", "코드": "code", "사람": "hum"}


def role_chip(ctx: Ctx, role: str, label: str, where: str, width: float | None = None) -> str:
    style = f' style="width:{px(width)}px"' if width else ""
    return (f'<span class="rc rc-{ROLE_CLS.get(role, "code")}"{style}>{icon(ROLE_ICON.get(role, "code"), 24, "rc-ic")}'
            f'<span>{ctx.t(label, 9, where)}</span></span>')


@part("C2")
def c2(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    steps = ctx.deck["steps"]
    on = set(spec.get("on", []))
    mode = spec.get("mode", "full")
    n = len(steps)
    if mode == "tiny":
        d = 32
        gap = (w - d) / (n - 1)
        parts = [f'<path d="M{d / 2} {d / 2}H{w - d / 2}" stroke="#c9c3be" stroke-width="2"/>']
        labels = []
        for i, s in enumerate(steps):
            cx = d / 2 + gap * i
            cls = "c2t-on" if s["n"] in on else "c2t-off"
            parts.append(f'<circle cx="{px(cx)}" cy="{d / 2}" r="{d / 2 - 2}" class="{cls}"/>'
                         f'<text x="{px(cx)}" y="{d / 2 + 6}" text-anchor="middle" class="{cls}-t">{s["n"]}</text>')
            if s["n"] in on:
                labels.append(f'<span class="c2t-l ax" style="left:{px(cx)}px">{ctx.t(s["label"], 8, f"{where}.steps")}</span>')
        return (f'<div class="c2t" style="height:{px(h)}px"><svg width="{px(w)}" height="{d}" viewBox="0 0 {px(w)} {d}" '
                f'aria-hidden="true">{"".join(parts)}</svg>{"".join(labels)}</div>')
    if mode in ("mini", "lanes"):
        head_w = 150 if mode == "lanes" else 0
        cw = (w - head_w) / n
        chips = "".join(f'<span class="c2m-c{" on" if s["n"] in on else ""}" style="left:{px(head_w + cw * i + 4)}px;width:{px(cw - 8)}px">'
                        f'<b>{s["n"]}</b> {ctx.t(s["label"], 8, f"{where}.steps[{i}].label")}</span>'
                        for i, s in enumerate(steps))
        out = [f'<div class="c2m" style="height:44px">{chips}</div>']
        if mode == "lanes":
            lanes = spec.get("lanes", {})
            lh = min(110, (h - 56) / max(1, len(lanes)))
            for li, (role, items) in enumerate(lanes.items()):
                seen: set[int] = set()
                cells = []
                for j, it in enumerate(items):
                    k = int(it["step"])
                    if k in seen:
                        ctx.warn(f"{where}.lanes.{role}[{j}]", f"{k}단계에 칩이 둘 이상")
                    seen.add(k)
                    x = head_w + cw * (k - 1) + 6
                    cells.append(f'<div class="c2l-chip" style="left:{px(x)}px;width:{px(cw - 12)}px">'
                                 f'{role_chip(ctx, role, it["label"], f"{where}.lanes.{role}[{j}].label", cw - 12)}</div>')
                out.append(f'<div class="c2l" style="top:{px(56 + lh * li)}px;height:{px(lh)}px">'
                           f'<div class="c2l-h">{icon(ROLE_ICON.get(role, "code"), 40)}<span>{esc(role)}</span></div>{"".join(cells)}</div>')
        return f'<div class="c2" style="height:{px(h)}px">{"".join(out)}</div>'

    # full
    gap = 40
    bw = (w - gap * (n - 1)) / n
    extra = (64 if spec.get("roles_preview") else 0) + (84 if spec.get("bracket") else 0)
    bh = max(160, min(300, h - 40 - extra))
    top = max(40.0, (h - (bh + extra)) / 2)
    boxes, svg = [], []
    for i, s in enumerate(steps):
        x = (bw + gap) * i
        cls = " on" if s["n"] in on else ""
        boxes.append(f'<div class="c2-b{cls}" style="{box_style(x, top, bw, bh)}">{icon(s.get("icon", "doc"), 56)}'
                     f'<p class="c2-l"><b>{s["n"]}</b> {ctx.t(s["label"], 8, f"{where}.steps[{i}].label")}</p>'
                     f'<p class="c2-s">{ctx.t(s["line"], 24, f"{where}.steps[{i}].line")}</p></div>')
        if i:
            cx = x - gap / 2
            svg.append(f'<path d="M{px(cx - 9)} {px(top + bh / 2 - 11)}l11 11-11 11" class="c2-arw"/>')
    wk = int(ctx.deck.get("weekly_after", 4))
    if 1 <= wk < n:
        cx = (bw + gap) * wk - gap / 2
        boxes.append(f'<span class="c2-wk ax" style="left:{px(cx)}px;top:{px(top - 40)}px">'
                     f'{ctx.t(ctx.deck.get("weekly_label", ""), 10, f"{where}.weekly")}</span>')
        svg.append(f'<path d="M{px(cx)} {px(top - 12)}V{px(top + bh / 2 - 16)}" class="c2-wkl"/>')
    y = top + bh + 12
    if spec.get("roles_preview"):
        roles_by_step = ctx.deck.get("lane_roles", {})
        for i, s in enumerate(steps):
            x = (bw + gap) * i
            icons = "".join(icon(ROLE_ICON[r], 36, "c2-rp") for r in roles_by_step.get(str(s["n"]), []) if r in ROLE_ICON)
            boxes.append(f'<div class="c2-rps" style="{box_style(x, y, bw, 44)}">{icons}</div>')
        y += 64
    br = spec.get("bracket")
    if br:
        a, b = int(br["from"]), int(br["to"])
        x0, x1 = (bw + gap) * (a - 1), (bw + gap) * (b - 1) + bw
        svg.append(f'<path d="M{px(x0)} {px(y)}v14H{px(x1)}v-14M{px((x0 + x1) / 2)} {px(y + 14)}v10" class="c2-br"/>')
        label = ctx.t(br["label"], 24, f"{where}.bracket.label")
        lw = min(w, max(x1 - x0, text_width(plain(label), 26) + 16))
        lx = min(max((x0 + x1) / 2 - lw / 2, 0), w - lw)
        boxes.append(f'<p class="c2-brl" style="left:{px(lx)}px;width:{px(lw)}px;top:{px(y + 30)}px">{label}</p>')
    return (f'<div class="c2" style="height:{px(h)}px"><svg class="c2-svg" width="{px(w)}" height="{px(h)}" aria-hidden="true">'
            f'{"".join(svg)}</svg>{"".join(boxes)}</div>')


@part("C20")
def c20(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    chips = "".join(role_chip(ctx, c.get("role", "AI"), c.get("label", ""), f"{where}.chips[{i}].label")
                    for i, c in enumerate(spec.get("chips", [])))
    return f'<div class="c20{" v" if spec.get("dir") == "v" else ""}">{chips}</div>'


# ---------------------------------------------------------------------------
# C3 흐름 화살표
# ---------------------------------------------------------------------------
def flow_node(ctx: Ctx, nd: dict, where: str, fig_w: float, compact: bool = False, sub_limit: int = 22,
              cls: str = "c3-n") -> str:
    hero = " hero" if nd.get("hero") else ""
    num = f'<span class="c3-num">{ctx.t(nd["num"], 4, f"{where}.num")}</span>' if nd.get("num") else ""
    fig = ""
    if nd.get("figure"):
        fh = float(nd.get("fig_h", 140))
        fig = f'<div class="c3-fig" style="width:{px(fig_w)}px;height:{px(fh)}px">{render(ctx, nd["figure"], fig_w, fh, f"{where}.figure")}</div>'
    elif nd.get("icon"):
        fig = icon(nd["icon"], 48 if compact else 64, "c3-ic")
    sub = f'<p class="c3-s">{ctx.t(nd["sub"], sub_limit, f"{where}.sub")}</p>' if nd.get("sub") else ""
    label = f'<p class="c3-l">{ctx.t(nd.get("label", ""), 18, f"{where}.label")}</p>' if nd.get("label") else ""
    # note: 보조 글 아래 작은 회색 한 줄(22px). 단계마다 쓰는 모델 이름처럼 작게만 덧붙일 글
    note = f'<p class="c3-note ax">{ctx.t(nd["note"], 26, f"{where}.note")}</p>' if nd.get("note") else ""
    return f'<div class="{cls}{hero}">{num}{fig}{label}{sub}{note}</div>'


def flow_row(ctx: Ctx, nodes: list[dict], where: str, w: float, direction: str = "h", compact: bool = False,
             arrows: bool = True, joiner: str = "", sub_limit: int = 22, cls: str = "c3-n") -> str:
    """노드를 한 줄로. arrows 가 거짓이면 화살표 없이 같은 크기 카드로 놓고(순서가 없는 묶음),
    joiner 가 있으면 화살표 자리에 그 글(예: "또는")을 둔다(서로 대안인 경로)."""
    n = max(1, len(nodes))
    if joiner:
        aw = 88 if direction == "h" else 0
    elif arrows:
        aw = 48 if direction == "h" else 0
    else:
        aw = 24 if direction == "h" else 0
    fig_w = (w - aw * (n - 1)) / n - 40 if direction == "h" else w - 40
    parts = []
    for i, nd in enumerate(nodes):
        if i:
            if joiner:
                parts.append(f'<div class="c3-j c3-a{direction}"><span>{ctx.t(joiner, 4, f"{where}.joiner")}</span></div>')
            elif arrows:
                parts.append(f'<div class="c3-a c3-a{direction}">{chevron("r" if direction == "h" else "d", 36)}</div>')
            else:
                parts.append(f'<div class="c3-gap c3-a{direction}"></div>')
        parts.append(flow_node(ctx, nd, f"{where}.nodes[{i}]", fig_w, compact, sub_limit, cls))
    return f'<div class="c3-row c3-{direction}">{"".join(parts)}</div>'


@part("C3")
def c3(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    nodes = spec.get("nodes", [])
    br = spec.get("branch")
    if not br and not 2 <= len(nodes) <= 7:
        ctx.warn(where, f"노드 {len(nodes)}개(2~7개)")
    if not br:
        d = spec.get("dir", "h")
        arrows = spec.get("arrows", True) is not False
        cls = "c3-n" if arrows or spec.get("joiner") else "c3-n card"
        if spec.get("align") == "top":      # 번호와 아이콘의 높이를 카드끼리 맞춘다(아래 글 줄 수가 달라도)
            cls += " top"
        row = flow_row(ctx, nodes, where, w, d, bool(spec.get("compact")), arrows, spec.get("joiner", ""),
                       int(spec.get("sub_limit", 22 if arrows else 36)), cls)
        return f'<div class="c3" style="height:{px(h)}px">{row}</div>'
    # 분기: 앞 노드들 → 마름모 → 위 경로와 아래 경로
    at = int(br.get("at", len(nodes)))
    pre = nodes[:at]
    up, down = br.get("up", []), br.get("down", [])
    pre_w = min(240 * max(1, len(pre)), w * 0.3) if pre else 0
    dia = 160
    right_x = pre_w + 48 + dia + 110
    right_w = w - right_x
    cy = h / 2
    rh = (h - 24) / 2
    pre_html = ""
    if pre:
        pre_html = f'<div class="c3-pre" style="{box_style(0, cy - rh / 2, pre_w, rh)}">{flow_row(ctx, pre, where, pre_w, "h", True)}</div>'
    dx = pre_w + 48
    hero = " hero" if br.get("hero") else ""
    dia_html = (f'<div class="c3-dia{hero}" style="{box_style(dx, cy - dia / 2, dia, dia)}"><svg width="{dia}" height="{dia}" aria-hidden="true">'
                f'<path d="M{dia / 2} 3L{dia - 3} {dia / 2}L{dia / 2} {dia - 3}L3 {dia / 2}z"/></svg>'
                f'<p>{ctx.t(br.get("label", ""), 8, f"{where}.branch.label")}</p></div>')
    rows = (f'<div class="c3-br" style="{box_style(right_x, 0, right_w, rh)}">{flow_row(ctx, up, f"{where}.branch.up", right_w, "h", True)}</div>'
            f'<div class="c3-br" style="{box_style(right_x, rh + 24, right_w, rh)}">{flow_row(ctx, down, f"{where}.branch.down", right_w, "h", True)}</div>')
    yu, yd = rh / 2, rh + 24 + rh / 2
    lines = [f'<path d="M{px(dx + dia)} {px(cy)}H{px(dx + dia + 20)}V{px(yu)}H{px(right_x - 6)}" class="c3-ln" marker-end="url(#ah)"/>',
             f'<path d="M{px(dx + dia + 20)} {px(cy)}V{px(yd)}H{px(right_x - 6)}" class="c3-ln" marker-end="url(#ah)"/>']
    if pre:
        lines.append(f'<path d="M{px(pre_w + 4)} {px(cy)}H{px(dx - 6)}" class="c3-ln" marker-end="url(#ah)"/>')
    lab = []
    for key, yy in (("up_label", yu), ("down_label", yd)):
        if br.get(key):
            lab.append(f'<span class="c3-bl ax" style="left:{px(dx + dia + 32)}px;top:{px(yy - 40)}px">{ctx.t(br[key], 6, f"{where}.branch.{key}")}</span>')
    return (f'<div class="c3" style="height:{px(h)}px"><svg class="c3-svg" width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(lines)}</svg>'
            f'{pre_html}{dia_html}{rows}{"".join(lab)}</div>')


# ---------------------------------------------------------------------------
# C4 회사 3열 비교
# ---------------------------------------------------------------------------
STATE_FACT = re.compile(r"\{\{fact:([^{}|]+)\}\}")


def c4_state(ctx: Ctx, state: str, where: str) -> str:
    """결과 행의 상태(open, closed). 자리 표시 하나({{fact:...}})면 사실 자료의 값을 쓴다(화면 자료가 바뀌어도 표시와 글이
    어긋나지 않게). open, closed 밖의 값이면 경고를 남기고 closed 로 본다."""
    m = STATE_FACT.fullmatch(str(state).strip())
    if m:
        path = m.group(1).strip()
        ctx._note(ctx.used_facts, path.split(".")[0])
        state = ctx.value("fact", path)
    if state not in ("open", "closed"):
        ctx.warn(where, f"상태 값이 open, closed 가 아님: {state}")
        return "closed"
    return state


@part("C4")
def c4(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    if spec.get("mode") == "result":
        out = []
        if spec.get("cond"):
            out.append(f'<p class="c4r-cond">{ctx.t(spec["cond"], 22, f"{where}.cond")}</p>')
        for i, r in enumerate(spec.get("rows", [])):
            st = c4_state(ctx, r.get("state", "closed"), f"{where}.rows[{i}].state")
            name = "가입 가능" if st == "open" else "가입 제한"
            hero = " hero" if r.get("hero") else ""
            out.append(f'<div class="c4r-r{hero}">{org_chip(ctx, r.get("org", ""))}{state_mark(st)}'
                       f'<span class="c4r-st">{name}</span><span class="c4r-t">{ctx.t(r.get("text", ""), 20, f"{where}.rows[{i}].text")}</span></div>')
        if spec.get("note"):
            out.append(f'<p class="c4r-note ax">{ctx.t(spec["note"], 30, f"{where}.note")}</p>')
        return f'<div class="c4r">{"".join(out)}</div>'
    cols = spec.get("cols", [])
    label_w = float(spec.get("label_w", 240))
    grid = f"grid-template-columns:{px(label_w)}px repeat({len(cols)},1fr)"
    rows = []
    if spec.get("head"):
        rows.append(f'<p class="c4-head">{ctx.t(spec["head"], 30, f"{where}.head")}</p>')
    rows.append(f'<div class="c4-r c4-hr" style="{grid}"><span></span>' + "".join(f'<span>{org_chip(ctx, c)}</span>' for c in cols) + "</div>")
    for i, r in enumerate(spec.get("rows", [])):
        hero = " hero" if r.get("hero") else ""
        label = f'<span class="c4-l">{ctx.t(r.get("label", ""), 9, f"{where}.rows[{i}].label")}</span>'
        vals = r.get("values", [])
        vlim = int(r.get("limit", spec.get("limit", 18)))
        if r.get("same"):
            # 알약 문구는 화면 용어(terms.DISPLAY 의 판정 값 "같음" → "동일")를 따른다. 행마다 same_label 로 바꿀 수 있다
            same = ctx.t(r.get("same_label", spec.get("same_label", "동일")), 6, f"{where}.rows[{i}].same_label")
            cells = (f'<span class="c4-v c4-same" style="grid-column:2 / span {len(cols)}">'
                     f'{ctx.t(vals[0] if vals else "", vlim, f"{where}.rows[{i}].values[0]")}<span class="pill">{same}</span></span>')
        else:
            if len(vals) != len(cols):
                ctx.warn(f"{where}.rows[{i}]", f"값 {len(vals)}개, 열 {len(cols)}개")
            chip = r.get("chip") or {}
            cl = []
            for j, v in enumerate(vals):
                extra = f'<span class="pill pill-hold">{ctx.t(chip.get("text", ""), 12, f"{where}.rows[{i}].chip")}</span>' \
                    if chip and int(chip.get("col", -1)) == j else ""
                cl.append(f'<span class="c4-v">{ctx.t(v, vlim, f"{where}.rows[{i}].values[{j}]")}{extra}</span>')
            cells = "".join(cl)
        rows.append(f'<div class="c4-r{hero}" style="{grid}">{label}{cells}</div>')
    if spec.get("tag"):
        rows.append(f'<p class="c4-tag">{ctx.t(spec["tag"], 36, f"{where}.tag")}</p>')
    return f'<div class="c4">{"".join(rows)}</div>'


# ---------------------------------------------------------------------------
# C5 전후 비교
# ---------------------------------------------------------------------------
@part("C5")
def c5(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    rows = spec.get("rows", [])
    labels = spec.get("labels", ["", ""])
    if not 1 <= len(rows) <= 4:
        ctx.warn(where, f"행 {len(rows)}개(1~4개)")
    if spec.get("orientation") == "v":
        cols = []
        for i, r in enumerate(rows):
            hero = " hero" if r.get("hero") else ""
            # 아이콘은 카드 오른쪽 위에 둔다(카드 높이와 상관없이 카드 안에 남는다)
            ic = icon(r["icon"], 44, "c5v-ic") if r.get("icon") else ""
            has_ic = " has-ic" if ic else ""
            cols.append(f'<div class="c5v-c"><div class="c5v-b"><span class="c5-k ax">{esc(labels[0])}</span>'
                        f'{ctx.t(r.get("before", ""), 28, f"{where}.rows[{i}].before")}</div>'
                        f'<div class="c5v-a">{chevron("d", 36)}</div>'
                        f'<div class="c5v-card{hero}{has_ic}">{ic}<span class="c5-k ax">{esc(labels[1])}</span>'
                        f'<p>{ctx.t(r.get("after", ""), 32, f"{where}.rows[{i}].after")}</p>'
                        + (f'<p class="c5-tag ax">{ctx.t(r["tag"], 28, f"{where}.rows[{i}].tag")}</p>' if r.get("tag") else "")
                        + (f'<p class="c5-note ax">{ctx.t(r["note"], 36, f"{where}.rows[{i}].note")}</p>' if r.get("note") else "")
                        + "</div></div>")
        return f'<div class="c5v" style="grid-template-columns:repeat({len(rows)},1fr)">{"".join(cols)}</div>'
    has_head = any(r.get("head") for r in rows)
    merged = spec.get("before_merged")
    badge = spec.get("badgeCol")
    # badgeCol.once: 행마다 배지를 되풀이하지 않고 오른쪽 열 머리에 배지 하나만 둔다(열은 없앰)
    once = bool(badge and badge.get("once"))
    tmpl = ([ "280px"] if has_head else []) + ["1fr", "72px", "1.35fr"] + (["200px"] if badge and not once else [])
    grid = f"grid-template-columns:{' '.join(tmpl)}"
    after_hd = esc(labels[1])
    if once:
        after_hd = (f'<span class="c5-hdr">{after_hd}<span class="c5-hdb">{esc(badge.get("label", ""))}'
                    f'{badge_html("unmeasured", badge.get("badge", "측정 전"))}</span></span>')
    head = (["<span></span>"] if has_head else []) + [f'<span class="c5-hd">{esc(labels[0])}</span>', "<span></span>",
                                                       f'<span class="c5-hd">{after_hd}</span>']
    if badge and not once:
        head.append(f'<span class="c5-hd">{esc(badge.get("label", ""))}</span>')
    cells = []
    n = len(rows)
    for i, r in enumerate(rows):
        row = i + 2
        if has_head:
            cells.append(f'<span class="c5-rh" style="grid-row:{row}">{ctx.t(r.get("head", ""), 13, f"{where}.rows[{i}].head")}</span>')
        if merged:
            if i == 0:
                ic = icon(merged["icon"], 64, "c5-mic") if merged.get("icon") else ""
                todo = (f'<div class="c15-todo sm"><b>확인 필요</b> {ctx.t(merged["todo"], 40, f"{where}.before_merged.todo")}</div>'
                        if merged.get("todo") else "")
                cells.append(f'<div class="c5-b c5-merged" style="grid-row:2 / span {n}">{ic}'
                             f'<p>{ctx.t(merged.get("text", ""), 28, f"{where}.before_merged.text")}</p>{todo}</div>')
        else:
            cells.append(f'<div class="c5-b" style="grid-row:{row}">{ctx.t(r.get("before", ""), 28, f"{where}.rows[{i}].before")}</div>')
        cells.append(f'<div class="c5-a" style="grid-row:{row}">{chevron("r", 36)}</div>')
        hero = " hero" if r.get("hero") else ""
        tag = f'<p class="c5-tag ax">{ctx.t(r["tag"], 28, f"{where}.rows[{i}].tag")}</p>' if r.get("tag") else ""
        # note: 꼬리표 아래 작은 회색 한 줄(22px). 역할마다 쓴 모델 등급처럼 작게만 덧붙일 글
        tag += f'<p class="c5-note ax">{ctx.t(r["note"], 36, f"{where}.rows[{i}].note")}</p>' if r.get("note") else ""
        cells.append(f'<div class="c5-c{hero}" style="grid-row:{row}"><p>{ctx.t(r.get("after", ""), 32, f"{where}.rows[{i}].after")}</p>{tag}</div>')
        if badge and not once:
            cells.append(f'<div class="c5-bd" style="grid-row:{row}">{badge_html("unmeasured", badge.get("badge", "측정 전"))}</div>')
    foot = f'<p class="c5-foot ax">{ctx.t(badge["note"], 36, f"{where}.badgeCol.note")}</p>' if badge and badge.get("note") else ""
    gh = h - (40 if foot else 0)
    rows_css = f";height:{px(gh)}px;grid-template-rows:auto repeat({max(1, n)}, minmax(0, 1fr))" if spec.get("fill", True) else ""
    return f'<div class="c5" style="{grid}{rows_css}">{"".join(head)}{"".join(cells)}</div>{foot}'


# ---------------------------------------------------------------------------
# C6 기술 세 패널
# ---------------------------------------------------------------------------
def panel_figures(ctx: Ctx, figs: list[dict], w: float, h: float, where: str) -> str:
    """패널의 그림 자리에 부품 여럿을 세로로 쌓는다. 부품마다 "h"(px)를 주면 그 높이, 없으면 남은 높이를 나눈다."""
    if not figs:
        return ""
    if len(figs) == 1 and "h" not in figs[0]:
        return render(ctx, figs[0], w, h, f"{where}.figure")
    gap = 14
    fixed = sum(float(f["h"]) for f in figs if "h" in f)
    free = [f for f in figs if "h" not in f]
    rest = max(0.0, h - fixed - gap * (len(figs) - 1))
    each = rest / len(free) if free else 0
    if fixed + gap * (len(figs) - 1) > h + 0.5:
        ctx.warn(f"{where}.figures", f"그림 높이 합 {px(fixed)}px > 그림 자리 {px(h)}px")
    out, y = [], 0.0
    for k, f in enumerate(figs):
        fh = float(f["h"]) if "h" in f else each
        out.append(f'<div class="c6-sub" style="{box_style(0, y, w, fh)}">{render(ctx, f, w, fh, f"{where}.figures[{k}]")}</div>')
        y += fh + gap
    return "".join(out)


@part("C6")
def c6(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    heads = spec.get("heads") or ctx.deck.get("panel_heads", ["", "", ""])
    panels = spec.get("panels", [])
    if len(panels) != 3:
        ctx.warn(where, f"패널 {len(panels)}개(3개)")
    gap = 40
    pw = (w - gap * 2) / 3
    out = []
    for i, p in enumerate(panels[:3]):
        line_h = 3 * 28 * 1.4
        chip_h = 52 if p.get("chip") else 0
        src_h = 34 if p.get("src") else 0
        fig_h = h - 64 - 40 - line_h - chip_h - src_h - 12
        figs = p.get("figures") or ([p["figure"]] if p.get("figure") else [])
        fig = panel_figures(ctx, figs, pw - 40, fig_h, f"{where}.panels[{i}]")
        chip = f'<span class="c6-chip">{ctx.t(p["chip"], 12, f"{where}.panels[{i}].chip")}</span>' if p.get("chip") else ""
        src = f'<p class="c6-src ax">{ctx.t(p["src"], 36, f"{where}.panels[{i}].src")}</p>' if p.get("src") else ""
        out.append(f'<div class="c6-p" style="{box_style((pw + gap) * i, 0, pw, h)}"><p class="c6-h">{esc(heads[i])}</p>'
                   f'<div class="c6-fig" style="height:{px(fig_h)}px">{fig}</div>'
                   f'<div class="c6-chipr" style="height:{chip_h}px">{chip}</div>'
                   f'<p class="c6-line">{ctx.t(p.get("line", ""), 44, f"{where}.panels[{i}].line")}</p>{src}</div>')
    return f'<div class="c6" style="height:{px(h)}px">{"".join(out)}</div>'


# ---------------------------------------------------------------------------
# C7 확률 계기판
# ---------------------------------------------------------------------------
@part("C7")
def c7(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    th = [ctx.num(t, f"{where}.thresholds") for t in spec.get("thresholds", [0.4, 0.75])]
    zones = spec.get("zones", ["다시 추출", "사람이 검수", "자동 확정"])
    edges = [0.0, *th, 1.0]
    mini = spec.get("size") == "mini"
    pad = 0 if mini else 40
    bw = w - pad * 2
    zcls = ["z0", "z1", "z2"]
    svg, html_ = [], []
    if mini:
        bar_h = 24
        bar_y = max(34 if spec.get("markers") else 4, (h - bar_h) / 2 - 10)
    else:
        # 큰 판: 누적 막대(위)와 0~1 막대 사이를 넓히지 않는다. 상자가 크면 둘을 묶어 세로 가운데에 둔다
        bar_h = 48
        bar_y = h - 150 if not spec.get("stack") else min(h - 150, float(spec.get("gap", 260)))
    oy = 0.0 if mini else max(0.0, (h - (bar_y + 130)) / 2)
    for i in range(len(edges) - 1):
        x0, x1 = pad + bw * edges[i], pad + bw * edges[i + 1]
        svg.append(f'<rect x="{px(x0)}" y="{px(bar_y)}" width="{px(x1 - x0)}" height="{bar_h}" class="c7-{zcls[min(i, 2)]}"/>')
        if not mini or h >= bar_y + bar_h + 30:
            zl = ctx.t(zones[min(i, len(zones) - 1)], 12, f"{where}.zones[{i}]")
            zx = clamp_center((x0 + x1) / 2, plain(zl), 18 if mini else 24, w)
            html_.append(f'<span class="c7-zl{" ax" if mini else ""}" style="left:{px(zx)}px;top:{px(bar_y + bar_h + (8 if mini else 44))}px">'
                         f'{zl}</span>')
    top_line = 0 if mini else 30
    for t in th:
        x = pad + bw * t
        svg.append(f'<path d="M{px(x)} {px(top_line if not mini else bar_y - 4)}V{px(bar_y + bar_h + 4)}" class="c7-th"/>')
        if not mini and spec.get("tick_labels", True) is not False:
            html_.append(f'<span class="c7-tl ax" style="left:{px(x)}px;top:{px(bar_y + bar_h + 8)}px">{ctx.fmt(t, "f2")}</span>')
    st = spec.get("stack")
    if st and not mini:
        sy, sh = 40, 56
        html_.append(f'<p class="c7-sl" style="left:{pad}px;top:0">{ctx.t(st.get("label", ""), 22, f"{where}.stack.label")}</p>')
        x = pad
        for i, sg in enumerate(st.get("segments", [])):
            pct = ctx.num(sg.get("pct", 0), f"{where}.stack.segments[{i}].pct") if sg.get("pct") is not None else 0.0
            sw = bw * pct / 100
            z = int(sg.get("zone", i))
            hatch = " hatch" if sg.get("computed") else ""
            if sw > 0:
                svg.append(f'<rect x="{px(x)}" y="{sy}" width="{px(sw)}" height="{sh}" class="c7-s{z}{hatch}"/>')
            if sg.get("text"):
                txt = ctx.t(sg["text"], 11, f"{where}.stack.segments[{i}].text")
                if sw > text_width(plain(txt), 24) + 24:      # 막대 안 가운데
                    style, cls = f"left:{px(x + sw / 2)}px;top:{px(sy + 13)}px", "mid" + (" in" if z == 0 else "")
                else:                                          # 막대 위, 구간 끝에 오른쪽을 맞춤
                    style, cls = f"right:{px(w - (x + sw))}px;top:{px(sy - 34)}px", "above"
                html_.append(f'<span class="c7-st {cls}" style="{style}">{txt}</span>')
            x += sw
    big = spec.get("big")
    if big and not mini:
        z = int(big.get("zone", 2))
        cx = pad + bw * (edges[z] + edges[z + 1]) / 2
        hero = " hero" if big.get("hero", True) else ""
        html_.append(f'<span class="c7-big{hero}" style="left:{px(cx)}px;top:{px(bar_y - 110)}px">{ctx.t(big.get("text", ""), 6, f"{where}.big")}</span>')
    for i, mk in enumerate(spec.get("markers", [])):
        v = ctx.num(mk.get("v", 0), f"{where}.markers[{i}].v")
        x = pad + bw * v
        hero = " hero" if mk.get("hero") else ""
        svg.append(f'<circle cx="{px(x)}" cy="{px(bar_y + bar_h / 2)}" r="{9 if mini else 12}" class="c7-mk{hero}"/>')
        ml = ctx.t(mk.get("label", ""), 13, f"{where}.markers[{i}].label")
        mx = clamp_center(x, plain(ml), 20, w)
        html_.append(f'<span class="c7-ml ax{hero}" style="left:{px(mx)}px;top:{px(bar_y - 30)}px">{ml}</span>')
    inner = f'<svg width="{px(w)}" height="{px(h - oy)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(html_)}'
    if oy > 0:
        inner = f'<div class="c7-in" style="{box_style(0, oy, w, h - oy)}">{inner}</div>'
    return f'<div class="c7{" mini" if mini else ""}" style="height:{px(h)}px">{inner}</div>'


# ---------------------------------------------------------------------------
# C8 타임라인
# ---------------------------------------------------------------------------
def short_date(ctx: Ctx, d: Any) -> str:
    s = plain(ctx.sub(str(d)))
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", s)
    if not m:
        return esc(s)
    return f"{m.group(2)}-{m.group(3)}" if m.group(3) else f"{m.group(1)}-{m.group(2)}"


def dot_tag(ctx: Ctx, dt: dict, where: str) -> str:
    """점 연표의 작은 태그(예: "이 앱이 씀"). 강조 점이면 빨강 바탕, 아니면 회색 바탕."""
    if not dt.get("tag"):
        return ""
    who = "hum" if dt.get("hero") else "ai"
    return f'<span class="c8-tag c8-{who}">{ctx.t(dt["tag"], 8, f"{where}.tag")}</span>'


@part("C8")
def c8(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    if spec.get("dots") and (spec.get("dir") == "v" or (spec.get("dir") != "h" and w < 700)):
        # 좁은 상자: 세로 연표(점은 왼쪽 선 위, 글은 오른쪽)
        dots = spec["dots"]
        n = len(dots)
        rh = h / n
        svg = [f'<path d="M14 {px(rh / 2)}V{px(h - rh / 2)}" class="c8-ax"/>']
        out = []
        for i, dt in enumerate(dots):
            cy = rh * (i + 0.5)
            hero = " hero" if dt.get("hero") else ""
            svg.append(f'<circle cx="14" cy="{px(cy)}" r="10" class="c8-dot{hero}"/>')
            date = plain(ctx.sub(str(dt.get("d", ""))))
            src = f'<p class="c8-src ax">{ctx.t(dt["src"], 20, f"{where}.dots[{i}].src")}</p>' if dt.get("src") else ""
            press = badge_html("press") if dt.get("press") else ""
            press += dot_tag(ctx, dt, f"{where}.dots[{i}]")
            out.append(f'<div class="c8-db v{hero}" style="left:40px;width:{px(w - 40)}px;top:{px(cy)}px">'
                       f'<p class="c8-dd">{esc(date)}</p><p class="c8-dl">{ctx.t(dt.get("label", ""), 30, f"{where}.dots[{i}].label")}</p>'
                       f'{src}{press}</div>')
        return f'<div class="c8" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'
    if spec.get("dots"):
        dots = spec["dots"]
        n = len(dots)
        cw = w / n
        alt = bool(spec.get("alternate"))
        ay = h * 0.45 if alt else 70
        svg = [f'<path d="M0 {px(ay)}H{px(w)}" class="c8-ax"/>']
        out = []
        for i, dt in enumerate(dots):
            cx = cw * (i + 0.5)
            hero = " hero" if dt.get("hero") else ""
            svg.append(f'<circle cx="{px(cx)}" cy="{px(ay)}" r="10" class="c8-dot{hero}"/>')
            below = (i % 2 == 1) if alt else True
            y = ay + 26 if below else None
            if alt:
                # 위아래로 번갈아 두고, 상자의 왼쪽 선을 점에 맞춘다(같은 쪽 상자는 두 칸 떨어져 겹치지 않는다)
                bx = max(0.0, cx - 14)
                bw_ = min(380, cw * 2 - 28, w - bx)
                if bw_ < 180:
                    bw_ = min(380, cw * 2 - 28)
                    bx = w - bw_
            else:
                bw_ = min(380, cw - 20)
                bx = min(max(cx - bw_ / 2, 0), w - bw_)
            date = plain(ctx.sub(str(dt.get("d", ""))))
            src = f'<p class="c8-src ax">{ctx.t(dt["src"], 20, f"{where}.dots[{i}].src")}</p>' if dt.get("src") else ""
            press = badge_html("press") if dt.get("press") else ""
            press += dot_tag(ctx, dt, f"{where}.dots[{i}]")
            pos = f"top:{px(y)}px" if below else f"bottom:{px(h - ay + 26)}px"
            out.append(f'<div class="c8-db{hero}" style="left:{px(bx)}px;width:{px(bw_)}px;{pos}">'
                       f'<p class="c8-dd">{esc(date)}</p><p class="c8-dl">{ctx.t(dt.get("label", ""), 30, f"{where}.dots[{i}].label")}</p>'
                       f'{src}{press}</div>')
        return f'<div class="c8" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'
    axis = spec.get("axis", [])
    n = max(1, len(axis))
    cw = w / n
    xs = {plain(ctx.sub(str(d))): cw * (i + 0.5) for i, d in enumerate(axis)}
    ay = h - 44
    svg = [f'<path d="M0 {px(ay)}H{px(w)}" class="c8-ax"/>']
    out = [f'<span class="c8-tick" style="left:{px(x)}px;top:{px(ay + 8)}px">{short_date(ctx, d)}</span>' for d, x in xs.items()]
    # 깃발 상자의 층 나누기(겹치지 않게)
    fw, fh = float(spec.get("flag_w", min(300.0, max(200.0, cw * 1.4)))), 118
    flags = spec.get("flags", [])
    placed: list[tuple[int, dict, float, float, int]] = []

    def fits(cx: float, bx: float, lv: int) -> bool:
        for _i, _f, ocx, obx, olv in placed:
            same_day = abs(ocx - cx) < 1      # 같은 날의 깃발은 세로선을 함께 쓴다(위 상자의 선이 아래 상자 뒤로 지나감)
            if olv == lv and not (bx + fw + 16 <= obx or obx + fw + 16 <= bx):
                return False            # 같은 층에서 겹침
            if not same_day and olv < lv and obx - 8 <= cx <= obx + fw + 8:
                return False            # 내 세로선이 아래층 상자를 지남
            if not same_day and olv > lv and bx - 8 <= ocx <= bx + fw + 8:
                return False            # 위층 상자의 세로선이 내 상자를 지남
        return True

    for idx, f in sorted(enumerate(flags), key=lambda t: xs.get(plain(ctx.sub(str(t[1].get("d", "")))), 0)):
        cx = xs.get(plain(ctx.sub(str(f.get("d", "")))))
        if cx is None:
            ctx.warn(f"{where}.flags[{idx}]", f"축에 없는 날짜 {f.get('d')}")
            continue
        cands = [min(max(c, 0), w - fw) for c in (cx - fw / 2, cx - 24, cx - fw + 24)]
        spot = next(((bx, lv) for lv in range(6) for bx in cands if fits(cx, bx, lv)), None)
        if spot is None:
            ctx.warn(f"{where}.flags[{idx}]", "깃발 상자를 겹치지 않게 놓을 자리가 없음(flag_w 를 줄인다)")
            spot = (cands[0], max([p[4] for p in placed], default=-1) + 1)
        placed.append((idx, f, cx, spot[0], spot[1]))
    nlv = max([p[4] for p in placed], default=0) + 1
    bars = spec.get("bars", [])
    bar_top_space = nlv * (fh + 18) + 10
    max_bar = max(40.0, ay - bar_top_space - 34)
    vals = [ctx.num(b.get("v", 0), f"{where}.bars[{i}].v") for i, b in enumerate(bars)]
    vmax = max(vals) if vals else 1
    bar_tops = {}
    bw_ = min(120, cw * 0.55)
    for b, v in zip(bars, vals):
        d = plain(ctx.sub(str(b.get("d", ""))))
        cx = xs.get(d)
        if cx is None:
            continue
        bh = max_bar * v / vmax if vmax else 0
        bar_tops[d] = ay - bh
        svg.append(f'<rect x="{px(cx - bw_ / 2)}" y="{px(ay - bh)}" width="{px(bw_)}" height="{px(bh)}" class="c8-bar"/>')
        # bar_unit: 막대 위 숫자 뒤에 붙일 단위(예: "건"). 숫자만 보이면 무엇을 센 값인지 모르므로
        unit = ctx.t(spec["bar_unit"], 4, f"{where}.bar_unit") if spec.get("bar_unit") else ""
        out.append(f'<span class="c8-bv" style="left:{px(cx)}px;top:{px(ay - bh - 32)}px">{ctx.fmt(int(v) if v.is_integer() else v, None)}{unit}</span>')
    for idx, f, cx, bx, lv in placed:
        y = (nlv - 1 - lv) * (fh + 18)
        d = plain(ctx.sub(str(f.get("d", ""))))
        y_end = bar_tops.get(d, ay) - (36 if d in bar_tops else 0)
        # 같은 날의 아래층 상자가 세로선 위에 있으면 선을 그 상자의 윗변에서 멈춘다(선이 다른 상자 뒤로 지나가지 않게)
        below = [(nlv - 1 - olv) * (fh + 18) for _i, _f, ocx, obx, olv in placed
                 if olv < lv and abs(ocx - cx) < 1 and obx - 1 <= cx <= obx + fw + 1]
        if below:
            y_end = min(y_end, min(below))
        hero = " hero" if f.get("hero") else ""
        svg.append(f'<path d="M{px(cx)} {px(y + fh)}V{px(y_end)}" class="c8-fl{hero}"/>')
        who = "hum" if f.get("who", "ai") in ("human", "사람") else "ai"
        tag = f'<span class="c8-tag c8-{who}">{ctx.t(f["tag"], 12, f"{where}.flags[{idx}].tag")}</span>' if f.get("tag") else ""
        out.append(f'<div class="c8-fb{hero}" style="{box_style(bx, y, fw, fh)}"><p>{ctx.t(f.get("label", ""), 20, f"{where}.flags[{idx}].label")}</p>{tag}</div>')
    return f'<div class="c8" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'


# ---------------------------------------------------------------------------
# C9 점과 선
# ---------------------------------------------------------------------------
def node_html(ctx: Ctx, nd: dict, where: str, x: float, y: float, w: float, h: float, cls: str = "c9-n") -> str:
    hero = " hero" if nd.get("hero") else ""
    sub = f'<span class="c9-s ax">{ctx.t(nd["sub"], 28, f"{where}.sub")}</span>' if nd.get("sub") else ""
    # note: 보조 글 아래 작은 회색 한 줄(모델 이름처럼 작게만 덧붙일 글)
    note = f'<span class="c9-note ax">{ctx.t(nd["note"], 26, f"{where}.note")}</span>' if nd.get("note") else ""
    return (f'<div class="{cls}{hero}" style="{box_style(x, y, w, h)}"><span class="c9-l">{ctx.t(nd.get("label", ""), 14, f"{where}.label")}</span>'
            f'{sub}{note}</div>')


@part("C9")
def c9(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    lay = spec.get("layout", "org")
    nodes = spec.get("nodes", [])
    svg, out = [], []
    if lay == "ladder":
        n = max(1, len(nodes))
        gap = 22
        nh = min(64, (h - gap * (n - 1)) / n)
        nw = min(400, w - 150)
        for i, nd in enumerate(nodes):
            y = i * (nh + gap)
            out.append(node_html(ctx, nd, f"{where}.nodes[{i}]", 0, y, nw, nh, "c9-n lad"))
            if nd.get("count") is not None:
                out.append(f'<span class="c9-cnt" style="left:{px(nw + 16)}px;top:{px(y + nh / 2)}px">{ctx.t(nd["count"], 8, f"{where}.nodes[{i}].count")}</span>')
            if i:
                svg.append(f'<path d="M{px(nw / 2)} {px(y - gap + 2)}V{px(y - 2)}" class="c9-e" marker-end="url(#ah)"/>')
        return f'<div class="c9" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'
    if lay == "converge":
        cards = spec.get("cards", [])
        target = spec.get("target", {})
        n = max(1, len(cards))
        link = max(56.0, min(240.0, w * 0.18))
        cw = min(560.0, (w - link) * 0.6)
        tw = min(360.0, w - cw - link)
        gap = 22 if h > 300 else 10
        ch = min(120.0, (h - gap * (n - 1)) / n)
        # 목표 노드: 작은 상자(C3 노드 안 미니)에서도 라벨이 한 줄로 들어가게 높이를 64 이상으로, 폭이 좁으면 글자를 줄인다
        th = min(120.0, h, max(h * 0.5, 64.0))
        small = " sm" if tw < 180 or th < 80 else ""
        tx, ty = w - tw, h / 2 - th / 2
        y0 = (h - (ch * n + gap * (n - 1))) / 2
        for i, c in enumerate(cards):
            y = y0 + i * (ch + gap)
            text = f'<p>{ctx.t(c["text"], int(c.get("limit", 50)), f"{where}.cards[{i}].text")}</p>' if c.get("text") else ""
            chip = org_chip(ctx, c["org"]) if c.get("org") else ""      # 회사가 없는 카드는 칩 자리를 두지 않는다
            out.append(f'<div class="c9-card" style="{box_style(0, y, cw, ch)}">{chip}{text}</div>')
            yc = y + ch / 2
            k = link * 0.45
            svg.append(f'<path d="M{px(cw + 4)} {px(yc)}C{px(cw + k)} {px(yc)} {px(tx - k)} {px(h / 2)} {px(tx - 8)} {px(h / 2)}" '
                       f'class="c9-e" marker-end="url(#ah)"/>')
        target = dict(target, hero=target.get("hero", True))
        out.append(node_html(ctx, target, f"{where}.target", tx, ty, tw, th, "c9-n tgt" + small))
        if spec.get("chip"):
            out.append(f'<p class="c9-chip ax" style="{box_style(tx - 40, ty + th + 14, tw + 40, 90)}">{ctx.t(spec["chip"], 34, f"{where}.chip")}</p>')
        return f'<div class="c9" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'
    if lay == "legend":
        side = w >= 480
        lw = (w - 24) * 0.46 if side else w
        if side and spec.get("legend_w"):
            lw = min(lw, float(spec["legend_w"]))       # 넓은 상자에서 범례를 좁게 두고 노선도를 크게
        lh = h if side else h * 0.46
        items = []
        for i, k in enumerate(spec.get("node_kinds", [])):
            items.append(f'<span class="c9-li"><i class="c9-sh sh-{esc(k.get("shape", "circle"))}"></i>{ctx.t(k.get("label", ""), 8, f"{where}.node_kinds[{i}]")}</span>')
        eitems = []
        for i, k in enumerate(spec.get("edge_kinds", [])):
            eitems.append(f'<span class="c9-li"><i class="c9-ls ls-{esc(k.get("style", "solid"))}"></i>{ctx.t(k.get("label", ""), 8, f"{where}.edge_kinds[{i}]")}</span>')
        caps = spec.get("captions", ["", ""])
        out.append(f'<div class="c9-leg" style="left:0;top:0;width:{px(lw)}px;max-height:{px(lh)}px"><p class="c9-cap">{ctx.t(caps[0], 14, f"{where}.captions[0]")}</p>'
                   f'<div class="c9-lg">{"".join(items)}</div><div class="c9-lg">{"".join(eitems)}</div></div>')
        gx, gy = (lw + 24, 0) if side else (0, lh + 16)
        gw, gh = (w - lw - 24, h) if side else (w, h - lh - 16)
        g = spec.get("graph", {})
        pos = [(0.18, 0.22), (0.78, 0.18), (0.5, 0.55), (0.2, 0.85), (0.82, 0.82)]
        gn = g.get("nodes", [])[:5]
        ids = {nd.get("id", str(i)): i for i, nd in enumerate(gn)}
        top_pad = 40
        for e in g.get("edges", []):
            a, b = ids.get(e.get("from")), ids.get(e.get("to"))
            if a is None or b is None:
                continue
            (ax_, ay_), (bx_, by_) = pos[a], pos[b]
            # 선 모양은 범례(ls-solid, ls-dash, ls-dot)와 같은 셋
            dash = {"dash": ' stroke-dasharray="6 5"', "dot": ' stroke-dasharray="1 6" stroke-linecap="round" stroke-width="3.5"'}.get(
                e.get("style", "solid"), "")
            svg.append(f'<path d="M{px(gx + ax_ * gw)} {px(gy + top_pad + ay_ * (gh - top_pad - 20))}L{px(gx + bx_ * gw)} {px(gy + top_pad + by_ * (gh - top_pad - 20))}" class="c9-e"{dash}/>')
        downs: dict[int, list[bool]] = {}
        for e in g.get("edges", []):
            a, b = ids.get(e.get("from")), ids.get(e.get("to"))
            if a is None or b is None:
                continue
            downs.setdefault(a, []).append(pos[b][1] > pos[a][1])
            downs.setdefault(b, []).append(pos[a][1] > pos[b][1])
        for i, nd in enumerate(gn):
            x, y = pos[i]
            shape = nd.get("shape", "circle")
            # 선이 모두 아래로 나가는 점은 이름을 점 위에 둔다(선이 이름 글자를 지나지 않게)
            up = " up" if downs.get(i) and all(downs[i]) else ""
            out.append(f'<span class="c9-gn sh-{esc(shape)}{up}{" hero" if nd.get("hero") else ""}" style="left:{px(gx + x * gw)}px;top:{px(gy + top_pad + y * (gh - top_pad - 20))}px">'
                       f'<i></i><b class="ax">{ctx.t(nd.get("label", ""), 8, f"{where}.graph.nodes[{i}].label")}</b></span>')
        out.append(f'<p class="c9-cap" style="{box_style(gx, gy, gw, 30)}">{ctx.t(caps[1] if len(caps) > 1 else "", 14, f"{where}.captions[1]")}</p>')
        large = " lg" if spec.get("size") == "large" else ""
        return f'<div class="c9{large}" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'

    # org: tier 0, 1, 2 와 오른쪽 side 노드
    side_nodes = [nd for nd in nodes if nd.get("side")]
    tiers: dict[int, list[dict]] = {}
    for nd in nodes:
        if not nd.get("side"):
            tiers.setdefault(int(nd.get("tier", 0)), []).append(nd)
    side_w = 300 if side_nodes else 0
    main_w = w - (side_w + 60 if side_nodes else 0)
    nt = max(1, len(tiers))
    nh = min(120, (h - 70 * (nt - 1)) / nt)
    vgap = (h - nh * nt) / max(1, nt - 1) if nt > 1 else 0
    geo: dict[str, tuple[float, float, float, float]] = {}
    for ti, (_t, row) in enumerate(sorted(tiers.items())):
        k = len(row)
        nw = min(340, (main_w - 40 * (k - 1)) / k)
        total = nw * k + 40 * (k - 1)
        x0 = (main_w - total) / 2
        y = ti * (nh + vgap)
        for j, nd in enumerate(row):
            geo[nd["id"]] = (x0 + j * (nw + 40), y, nw, nh)
    for j, nd in enumerate(side_nodes):
        sh = min(150, h / max(1, len(side_nodes)) - 20)
        y = h / 2 - sh / 2 + j * (sh + 20)
        geo[nd["id"]] = (w - side_w, y, side_w, sh)
    for i, e in enumerate(spec.get("edges", [])):
        a, b = geo.get(e.get("from")), geo.get(e.get("to"))
        if not a or not b:
            ctx.warn(f"{where}.edges[{i}]", "없는 노드를 잇는 선")
            continue
        ax_, ay_, aw, ah = a
        bx_, by_, bw2, bh2 = b
        if bx_ >= ax_ + aw - 1:          # 오른쪽으로(통로 노드)
            x1, y1 = ax_ + aw, ay_ + ah / 2
            x2, y2 = bx_, by_ + bh2 / 2 + (e.get("offset", 0))
            mx = (x1 + x2) / 2
            d = f"M{px(x1)} {px(y1)}H{px(mx)}V{px(y2)}H{px(x2 - 6)}"
            lx, ly = mx, (y1 + y2) / 2
        else:
            x1, y1 = ax_ + aw / 2, ay_ + ah
            x2, y2 = bx_ + bw2 / 2, by_
            my = (y1 + y2) / 2
            d = f"M{px(x1)} {px(y1)}V{px(my)}H{px(x2)}V{px(y2 - 6)}"
            lx, ly = x2, my
        svg.append(f'<path d="{d}" class="c9-e" marker-end="url(#ah)"/>')
        if e.get("label"):
            out.append(f'<span class="c9-el ax" style="left:{px(lx)}px;top:{px(ly)}px">{ctx.t(e["label"], 13, f"{where}.edges[{i}].label")}</span>')
    for i, nd in enumerate(nodes):
        if nd.get("id") in geo:
            x, y, nw, nh2 = geo[nd["id"]]
            out.append(node_html(ctx, nd, f"{where}.nodes[{i}]", x, y, nw, nh2))
    ring = spec.get("ring")
    if ring and ring.get("node") in geo:
        x, y, nw, nh2 = geo[ring["node"]]
        # 노드 왼쪽을 도는 되돌림 화살표(위 가장자리에서 나가 왼쪽을 돌아 아래 가장자리로 들어옴)
        hero = " hero" if ring.get("hero", True) else ""
        sx = x + nw * 0.22
        bulge = x - 74
        svg.append(f'<path d="M{px(sx)} {px(y - 4)}C{px(sx - 40)} {px(y - 40)} {px(bulge)} {px(y - 30)} {px(bulge)} {px(y + nh2 / 2)}'
                   f'S{px(sx - 40)} {px(y + nh2 + 40)} {px(sx)} {px(y + nh2 + 8)}" class="c9-ring{hero}" '
                   f'marker-end="url(#ah{"-r" if hero else ""})"/>')
        out.append(f'<span class="c9-rl{hero}" style="right:{px(w - bulge + 16)}px;top:{px(y + nh2 / 2)}px">'
                   f'{ctx.t(ring.get("label", ""), 18, f"{where}.ring.label")}</span>')
    return f'<div class="c9" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>{"".join(out)}</div>'


# ---------------------------------------------------------------------------
# C10 큰 숫자, C11 링 차트
# ---------------------------------------------------------------------------
@part("C10")
def c10(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    small = " small" if spec.get("size") == "small" else ""
    small += " center" if spec.get("align") == "center" else ""
    hero = " hero" if spec.get("hero") else ""
    # tile: 디자인 시스템의 큰 숫자 타일(KPI 타일). 테두리 상자, 머리에 아이콘 칩과 이름 한 줄. 강조 타일은 빨강 면에 흰 글자
    tile = " tile" if spec.get("tile") else ""
    head = ""
    if tile and (spec.get("icon") or spec.get("tile_label")):
        ic = f'<span class="c10-ic">{icon(spec["icon"], 36)}</span>' if spec.get("icon") else ""
        tl = f'<span>{ctx.t(spec["tile_label"], 12, f"{where}.tile_label")}</span>' if spec.get("tile_label") else ""
        head = f'<p class="c10-tl">{ic}{tl}</p>'
    unit = f'<span class="c10-u">{ctx.t(spec["unit"], 6, f"{where}.unit")}</span>' if spec.get("unit") else ""
    cap = f'<p class="c10-c">{ctx.t(spec["caption"], 20, f"{where}.caption")}</p>' if spec.get("caption") else ""
    # scope: 설명 아래 작은 회색 한 줄(22px). 그 숫자를 잰 범위(어느 문서, 몇 건, 어떤 표본)
    cap += f'<p class="c10-sc ax">{ctx.t(spec["scope"], 26, f"{where}.scope")}</p>' if spec.get("scope") else ""
    return (f'<div class="c10{small}{hero}{tile}">{head}<p class="c10-r"><span class="c10-v">{ctx.t(spec.get("value", ""), 8, f"{where}.value")}</span>{unit}</p>'
            f'{cap}</div>')


@part("C11")
def c11(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    small = spec.get("size") == "small"
    d = 160 if small else 280
    sw = 18 if small else 28
    r = (d - sw) / 2
    c = d / 2
    total = ctx.num(spec.get("total", 1), f"{where}.total") or 1
    circ = 2 * math.pi * r
    arcs = [f'<circle cx="{c}" cy="{c}" r="{px(r)}" class="c11-bg" stroke-width="{sw}"/>']
    split = spec.get("split") or [{"v": spec.get("value", 0)}]
    start = 0.0
    hero = spec.get("hero")
    for i, sg in enumerate(split):
        v = ctx.num(sg.get("v", 0), f"{where}.split[{i}].v")
        frac = max(0.0, min(1.0, v / total))
        cls = "c11-h" if sg.get("hatch") else ("c11-hero" if hero else "c11-v")
        dash = f"{px(circ * frac)} {px(circ)}"
        arcs.append(f'<circle cx="{c}" cy="{c}" r="{px(r)}" class="{cls}" stroke-width="{sw}" stroke-dasharray="{dash}" '
                    f'stroke-dashoffset="{px(-circ * start)}" transform="rotate(-90 {c} {c})"/>')
        start += frac
    cap = f'<p class="c11-c">{ctx.t(spec["caption"], 22, f"{where}.caption")}</p>' if spec.get("caption") else ""
    # scope: 설명 아래 작은 회색 한 줄(22px). 대조한 범위(어느 문서의 몇 항목)
    cap += f'<p class="c11-sc ax">{ctx.t(spec["scope"], 26, f"{where}.scope")}</p>' if spec.get("scope") else ""
    legend = ""
    if spec.get("legend"):
        legend = "".join(f'<span class="c11-lg ax"><i class="{"h" if i else "v"}"></i>{ctx.t(t, 13, f"{where}.legend[{i}]")}</span>'
                         for i, t in enumerate(spec["legend"]))
        legend = f'<p class="c11-lgs">{legend}</p>'
    return (f'<div class="c11{" small" if small else ""}"><div class="c11-ring" style="width:{d}px;height:{d}px">'
            f'<svg width="{d}" height="{d}" aria-hidden="true">{"".join(arcs)}</svg>'
            f'<p class="c11-t"><b>{ctx.t(spec.get("value", ""), 6, f"{where}.value")}</b><span>/{ctx.t(spec.get("total", ""), 6, f"{where}.total")}</span></p></div>'
            f'{cap}{legend}</div>')


# ---------------------------------------------------------------------------
# C12 화면 캡처 주석
# ---------------------------------------------------------------------------
@part("C12")
def c12(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    """화면 캡처에 번호를 붙여 짚는다. marks 는 점(번호 원), zones 는 구역(빨강 테두리 상자와 번호 칩, 디자인 시스템의
    an-zone). 둘 다 오른쪽 라벨 열(300px)에 번호와 라벨을 단다. 번호는 합쳐 넷 이하."""
    cls = ctx.img(spec.get("img", ""), f"{where}.img")
    marks = [dict(m, _kind="mark") for m in spec.get("marks", [])]
    zones = [dict(z, _kind="zone") for z in spec.get("zones", [])]
    for j, m in enumerate(marks):
        m["_idx"], m["_y"] = j, float(m.get("y", 0.5))
    for j, z in enumerate(zones):
        z["_idx"], z["_y"] = j, float(z.get("y", 0.1)) + float(z.get("h", 0.3)) / 2
    # 라벨 칸은 짚는 곳의 높이 순서로 놓는다(리더 선이 서로 엇갈리지 않게)
    items = sorted(marks + zones, key=lambda m: m["_y"])
    if len(items) > 4:
        ctx.warn(where, f"번호 {len(items)}개(점과 구역을 합쳐 넷 이하)")
    label_w = 300 if items else 0
    cap_h = 34 if spec.get("caption") else 0
    iw = min(w - label_w - (24 if items else 0), (h - cap_h) * 16 / 9)
    ih = iw * 9 / 16
    ix = 0 if items else (w - iw) / 2
    img = (f'<div class="c12-im {cls}" role="img" aria-label="{esc(plain(ctx.sub(spec.get("alt", "화면 캡처"))))}" '
           f'style="{box_style(ix, 0, iw, ih)}"></div>')
    out = []
    svg = []
    lx = iw + 24
    gap = (ih - 56 * len(items)) / max(1, len(items) + 1) if items else 0
    for i, mk in enumerate(items):
        n = esc(mk.get("n", i + 1))
        kind, idx = mk["_kind"], mk["_idx"]
        ly = gap + i * (56 + gap) + 28
        if kind == "zone":
            zx, zy = iw * float(mk.get("x", 0.1)), ih * float(mk.get("y", 0.1))
            zw, zh = iw * float(mk.get("w", 0.3)), ih * float(mk.get("h", 0.3))
            zx, zy = max(0.0, min(zx, iw - 8)), max(0.0, min(zy, ih - 8))
            zw, zh = min(zw, iw - zx), min(zh, ih - zy)
            svg.append(f'<rect x="{px(zx)}" y="{px(zy)}" width="{px(zw)}" height="{px(zh)}" class="c12-zn"/>')
            sx, sy = zx + zw, zy + zh / 2
            lead = mk.get("lead")
            if lead:
                # 리더 선이 사진 속 글자를 지나지 않게: 구역의 윗변이나 아랫변의 x 에서 나와 lead 의 y 까지 세로로 간 뒤 가로로
                fx, fy = iw * float(lead[0]), ih * float(lead[1])
                ey = zy if fy < zy else zy + zh
                mid = max(fx, sx) + (lx - max(fx, sx)) * 0.5
                svg.append(f'<path d="M{px(fx)} {px(ey)}V{px(fy)}H{px(mid)}V{px(ly)}H{px(lx)}" class="c12-ld"/>')
            else:
                svg.append(f'<path d="M{px(sx)} {px(sy)}H{px(sx + (lx - sx) * 0.5)}V{px(ly)}H{px(lx)}" class="c12-ld"/>')
            # 번호 칩: 기본은 구역의 왼쪽 위 안쪽. 작은 버튼을 짚을 때는 칩이 대상을 가리지 않게 구역 밖에 둔다
            kx, ky = zx, zy
            chip = mk.get("chip", "tl")
            if chip == "above":
                ky = zy - 46
            elif chip == "below":
                ky = zy + zh + 6
            elif chip == "left":
                kx, ky = zx - 46, zy + zh / 2 - 20
            elif chip == "right":
                kx = zx + zw + 6
            out.append(f'<span class="c12-zk" style="left:{px(kx)}px;top:{px(ky)}px">{n}</span>')
        else:
            mx, my = iw * float(mk.get("x", 0.5)), ih * float(mk.get("y", 0.5))
            svg.append(f'<path d="M{px(mx + 22)} {px(my)}H{px(mx + 22 + (lx - mx - 22) * 0.5)}V{px(ly)}H{px(lx)}" class="c12-ld"/>')
            out.append(f'<span class="c12-mk" style="left:{px(mx)}px;top:{px(my)}px">{n}</span>')
        out.append(f'<span class="c12-lb" style="left:{px(lx)}px;top:{px(ly)}px;width:{px(label_w)}px">'
                   f'<i>{n}</i>{ctx.t(mk.get("label", ""), 10, f"{where}.{kind}s[{idx}].label")}</span>')
    if spec.get("caption"):
        out.append(f'<p class="c12-cap ax" style="{box_style(ix, ih + 6, iw, 28)}">{ctx.t(spec["caption"], 28, f"{where}.caption")}</p>')
    return (f'<div class="c12" style="height:{px(h)}px">{img}<svg width="{px(w)}" height="{px(h)}" aria-hidden="true">{"".join(svg)}</svg>'
            f'{"".join(out)}</div>')


# ---------------------------------------------------------------------------
# C14 용어 풀이 칩, C15 플레이스홀더와 배지
# ---------------------------------------------------------------------------
def gloss_band(ctx: Ctx, terms: list[str], width: float) -> str:
    glossary = ctx.deck.get("glossary", {})
    if len(terms) > LIMITS["terms"]:
        ctx.warn("terms", f"용어 {len(terms)}개 > {LIMITS['terms']}개")
    chips = []
    for i, term in enumerate(terms):
        if term not in glossary:
            ctx.warn(f"terms[{i}]", f"용어 풀이 표에 없는 말: {term}")
            continue
        chips.append(f'<p class="gl-c"><span><b>{esc(term)}</b> {ctx.t(glossary[term], LIMITS["gloss"], f"glossary.{term}")}</span></p>')
    return "".join(chips)


@part("C14")
def c14(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    return f'<div class="c14">{gloss_band(ctx, spec.get("terms", []), w)}</div>'


def badge_html(kind: str, text: str | None = None) -> str:
    if kind == "unmeasured":
        return f'<span class="bd-um">{esc(text or "측정 전")}</span>'
    if kind == "press":
        return '<span class="pb">보도 기준</span>'
    return ""


@part("C15")
def c15(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    kind = spec.get("kind", "todo")
    if kind == "todo":
        return f'<div class="c15-todo"><b>확인 필요</b> {ctx.t(spec.get("text", ""), 50, f"{where}.text")}</div>'
    if kind == "unmeasured":
        return f'<div class="c15-b">{badge_html("unmeasured", plain(ctx.t(spec.get("text") or "측정 전", 10, f"{where}.text")))}</div>'
    return f'<div class="c15-b">{badge_html("press")}</div>'


# ---------------------------------------------------------------------------
# C16 영수증과 주간 일정
# ---------------------------------------------------------------------------
@part("C16")
def c16(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    partname = spec.get("part", "both")
    out = []
    rw = min(560, w) if partname != "week" else 0
    if partname in ("both", "receipt"):
        items = spec.get("items", [])
        rows = []
        for i, it in enumerate(items):
            todo = f'<span class="c16-todo"><b>확인 필요</b> {ctx.t(it["todo"], 13, f"{where}.items[{i}].todo")}</span>' if it.get("todo") else ""
            note = f'<span class="c16-n ax">{ctx.t(it["note"], 20, f"{where}.items[{i}].note")}</span>' if it.get("note") else ""
            rows.append(f'<div class="c16-r"><span class="c16-l">{ctx.t(it.get("label", ""), 22, f"{where}.items[{i}].label")}{note}{todo}</span>'
                        f'<span class="c16-w">{ctx.t(it.get("won", ""), 8, f"{where}.items[{i}].won")}</span></div>')
        total = (f'<div class="c16-t"><span>{esc(spec.get("total_label", "합계"))}</span>'
                 f'<b class="{"hero" if spec.get("hero", True) else ""}">{ctx.t(spec.get("total", ""), 8, f"{where}.total")}</b></div>')
        rh = h - (40 if spec.get("caption") else 0)
        teeth = max(4, int(rw // 20))
        step = rw / teeth
        zig = "".join(f"L{px(rw - step * (k + 0.5))} {px(rh - 14)}L{px(rw - step * (k + 1))} {px(rh - 1)}" for k in range(teeth))
        out.append(f'<div class="c16-rc" style="{box_style(0, 0, rw, rh)}"><svg width="{px(rw)}" height="{px(rh)}" aria-hidden="true">'
                   f'<path d="M1 1H{px(rw - 1)}V{px(rh - 1)}{zig}Z" class="c16-paper"/></svg>'
                   f'<div class="c16-in"><p class="c16-hd">{esc(spec.get("title", "주간 운영 비용"))}</p>{"".join(rows)}{total}</div></div>')
        if spec.get("caption"):
            out.append(f'<p class="c16-cap ax" style="{box_style(0, rh + 8, rw, 30)}">{ctx.t(spec["caption"], 22, f"{where}.caption")}</p>')
    if partname in ("both", "week") and spec.get("week"):
        wk = spec["week"]
        x0 = rw + 80 if partname == "both" else 0
        ww = w - x0
        cw = ww / 7
        days = ["월", "화", "수", "목", "금", "토", "일"]
        cells = []
        for i, dname in enumerate(days):
            sun = i == 6
            marks = icon("dot", 28, "c16-dot")
            if sun:
                marks += icon("square", 28, "c16-sq")
            cells.append(f'<div class="c16-d{" sun" if sun else ""}" style="{box_style(x0 + cw * i + 4, 0, cw - 8, 150)}">'
                         f'<b>{dname}</b><span class="c16-mk">{marks}</span></div>')
        daily, sun = wk.get("daily", {}), wk.get("sun", {})
        leg = (f'<p class="c16-lg" style="{box_style(x0, 170, ww, 36)}">{icon("dot", 24, "c16-dot")}'
               f'<b>{ctx.t(daily.get("time", ""), 6, f"{where}.week.daily.time")}</b> {ctx.t(daily.get("label", ""), 15, f"{where}.week.daily.label")}</p>'
               f'<p class="c16-lg" style="{box_style(x0, 214, ww, 36)}">{icon("square", 24, "c16-sq")}'
               f'<b>{ctx.t(sun.get("time", ""), 6, f"{where}.week.sun.time")}</b> {ctx.t(sun.get("label", ""), 15, f"{where}.week.sun.label")}</p>')
        # manual: 예약 실행이 아니라 필요할 때 사람이 실행하는 일(셋째 범례 줄, 사람 아이콘). 있으면 끝 화살표 글을 한 줄 내린다
        manual = wk.get("manual")
        if manual:
            leg += (f'<p class="c16-lg" style="{box_style(x0, 258, ww, 36)}">{icon("person", 24, "c16-dot")}'
                    f'<b>{ctx.t(manual.get("label", ""), 10, f"{where}.week.manual.label")}</b> '
                    f'{ctx.t(manual.get("text", ""), 28, f"{where}.week.manual.text")}</p>')
        after = ""
        if wk.get("after"):
            ax_ = x0 + cw * 6.5
            ay_ = 310 if manual else 266
            after = (f'<svg class="c16-svg" style="left:0;top:0" width="{px(w)}" height="{px(h)}" aria-hidden="true">'
                     f'<path d="M{px(ax_)} 152V{ay_}" class="c16-arw" marker-end="url(#ah)"/></svg>'
                     f'<p class="c16-after" style="right:0;top:{ay_ + 10}px">{ctx.t(wk["after"], 20, f"{where}.week.after")}</p>')
        out.append("".join(cells) + leg + after)
    return f'<div class="c16" style="height:{px(h)}px">{"".join(out)}</div>'


# ---------------------------------------------------------------------------
# C17 모래시계
# ---------------------------------------------------------------------------
@part("C17")
def c17(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    gw = min(220, w * 0.4)
    gh = h - 20
    neck = 14
    top_y, mid_y, bot_y = 10, 10 + gh / 2, 10 + gh
    path = (f"M4 {top_y}H{px(gw - 4)}L{px(gw / 2 + neck)} {px(mid_y)}L{px(gw - 4)} {px(bot_y)}H4"
            f"L{px(gw / 2 - neck)} {px(mid_y)}z")
    sand_top = f"M{px(gw * 0.2)} {px(top_y + gh * 0.16)}H{px(gw * 0.8)}L{px(gw / 2 + neck - 3)} {px(mid_y - 4)}H{px(gw / 2 - neck + 3)}z"
    sand_bot = f"M{px(gw * 0.3)} {px(bot_y - 4)}Q{px(gw / 2)} {px(bot_y - gh * 0.16)} {px(gw * 0.7)} {px(bot_y - 4)}z"
    hero_neck = spec.get("hero", "neck") == "neck"
    svg = (f'<svg width="{px(gw)}" height="{px(h)}" aria-hidden="true"><path d="{sand_top}" class="c17-sand"/>'
           f'<path d="{sand_bot}" class="c17-sand"/><path d="{path}" class="c17-o"/>'
           f'<path d="M{px(gw / 2)} {px(mid_y - 4)}V{px(bot_y - gh * 0.1)}" class="c17-fall"/></svg>')
    lx = gw + 28
    lw = w - lx
    labels = []
    for key, y in (("top", top_y + gh * 0.12), ("neck", mid_y), ("bottom", bot_y - gh * 0.12)):
        hero = " hero" if key == "neck" and hero_neck else ""
        labels.append(f'<p class="c17-l{hero}" style="left:{px(lx)}px;top:{px(y)}px;width:{px(lw)}px">{ctx.t(spec.get(key, ""), 24, f"{where}.{key}")}</p>')
    return f'<div class="c17" style="height:{px(h)}px">{svg}{"".join(labels)}</div>'


# ---------------------------------------------------------------------------
# C18 아이콘(문서 더미), C19 A4 미리보기
# ---------------------------------------------------------------------------
@part("C18")
def c18(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    name = spec.get("icon", "doc")
    label = f'<p class="c18-l">{ctx.t(spec["label"], 13, f"{where}.label")}</p>' if spec.get("label") else ""
    lab_h = 44 if label else 0
    if name != "stack" or spec.get("pages") is None:
        size = int(min(w, h - lab_h, spec.get("size", 64)))
        return f'<div class="c18">{icon(name, size)}{label}</div>'
    pages = ctx.num(spec["pages"], f"{where}.pages")
    scale = ctx.num(spec.get("scale_pages", pages) or pages, f"{where}.scale_pages") or 1
    area = h - lab_h - 6
    # 옆에서 본 종이 더미: 높이가 쪽수에 비례하고, 맨 위 장은 비스듬한 면으로 보인다
    sw = min(w * 0.8, 320.0)
    top_h = min(60.0, sw * 0.22)
    pile = max(16.0, (area - top_h) * min(1.0, pages / scale))
    x0 = (w - sw) / 2
    y_top = area - pile - top_h
    sheets = max(6, min(48, int(pile / 9)))
    lines = "".join(f'<path d="M{px(x0)} {px(y_top + top_h + pile * k / sheets)}H{px(x0 + sw - 18)}" class="c18-ln"/>'
                    for k in range(1, sheets))
    svg = (f'<path d="M{px(x0 + 18)} {px(y_top)}H{px(x0 + sw)}L{px(x0 + sw - 18)} {px(y_top + top_h)}H{px(x0)}Z" class="c18-top"/>'
           f'<path d="M{px(x0)} {px(y_top + top_h)}H{px(x0 + sw - 18)}V{px(area)}H{px(x0)}Z" class="c18-side"/>'
           f'<path d="M{px(x0 + sw - 18)} {px(y_top + top_h)}L{px(x0 + sw)} {px(y_top)}V{px(area - top_h)}L{px(x0 + sw - 18)} {px(area)}Z" class="c18-edge"/>'
           f'{lines}'
           f'<path d="M{px(x0 + sw * 0.3)} {px(y_top + top_h * 0.35)}H{px(x0 + sw * 0.75)}M{px(x0 + sw * 0.26)} {px(y_top + top_h * 0.62)}H{px(x0 + sw * 0.6)}" class="c18-ln"/>')
    return (f'<div class="c18 stack" style="height:{px(h)}px"><svg width="{px(w)}" height="{px(area)}" aria-hidden="true">'
            f'{svg}</svg>{label}</div>')


@part("C19")
def c19(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    size = spec.get("size", "s")
    cw, ch = (300, 424) if size == "m" else (180, 254)
    k = min(1.0, w / cw, h / ch)
    cw, ch = cw * k, ch * k
    hero = " hero" if spec.get("hero") else ""
    blocks = spec.get("blocks", ["인수기준", "구성 요약", "예상 질문과 답"])
    tiny = cw < 220          # 글자(22px)를 넣을 수 없는 작은 카드는 회색 막대만(작은 판 180px 은 늘 막대만)
    parts_ = []
    for i, b in enumerate(blocks):
        label = "" if tiny else "<span>" + ctx.t(b, 7, f"{where}.blocks[{i}]") + "</span>"
        parts_.append(f'<div class="c19-bk">{label}<i></i><i></i></div>')
    bl = "".join(parts_)
    head = "" if tiny else esc(spec.get("header", "대외 배포 금지"))
    return (f'<div class="c19-w" style="height:{px(h)}px"><div class="c19 {esc(size)}{hero}{" tiny" if tiny else ""}" '
            f'style="width:{px(cw)}px;height:{px(ch)}px"><p class="c19-hd">{head}</p>{bl}</div></div>')


# ---------------------------------------------------------------------------
# 보조 블록: 글, 칩, 버튼, 링크
# ---------------------------------------------------------------------------
@part("text")
def p_text(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    size = spec.get("size", "m")
    tone = spec.get("tone", "ink")
    limit = int(spec.get("limit", {"l": 30, "m": 40, "s": 50}.get(size, 40)))
    return f'<p class="tx tx-{esc(size)} tone-{esc(tone)}">{ctx.t(spec.get("text", ""), limit, f"{where}.text")}</p>'


@part("chip")
def p_chip(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    tone = spec.get("tone", "paper")
    chip = f'<span class="chip chip-{esc(tone)}">{ctx.t(spec.get("text", ""), int(spec.get("limit", 30)), f"{where}.text")}</span>'
    align = spec.get("align", "left")          # left, center, right: box 안에서 칩의 가로 자리
    if align in ("center", "right"):
        return f'<div class="chip-w" style="text-align:{align}">{chip}</div>'
    return chip


@part("button")
def p_button(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    href = plain(ctx.sub(spec.get("href", ctx.deck.get("demo", {}).get("href", "#"))))
    label = ctx.t(spec.get("label", ctx.deck.get("demo", {}).get("label", "데모 열기")), 10, f"{where}.label")
    return (f'<a class="btn" href="{esc(href)}" target="_blank" rel="noopener">{icon("arrow", 24, "btn-ic")}{label}</a>')


@part("links")
def p_links(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    rows = "".join(f'<p class="lk-l">{ctx.t(x.get("l", ""), 8, f"{where}.items[{i}].l")}</p>'
                   f'<p class="lk-v">{ctx.t(x.get("v", ""), 56, f"{where}.items[{i}].v")}</p>'
                   for i, x in enumerate(spec.get("items", [])))
    return f'<div class="lk">{rows}</div>'


# ---------------------------------------------------------------------------
# 강조와 큰 숫자 세기(장 단위 규칙)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 인용(디자인 시스템의 인용 슬라이드 SlideQuote 를 블록으로)
# ---------------------------------------------------------------------------
@part("quote")
def p_quote(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    """실무자의 말 한 문장을 크게. kind 는 "verbatim"(그대로 옮긴 말, 빨강 큰따옴표) 또는 "gist"(요지, "응답 요지" 칩).
    실제로 한 말만 verbatim 으로 쓴다. 원문을 저장소에 옮기지 않은 응답은 gist 로 쓴다. 말한 사람은 실명 대신 역할로."""
    kind = spec.get("kind", "gist")
    if kind not in ("verbatim", "gist"):
        ctx.warn(f"{where}.kind", f"{kind!r}: verbatim 이나 gist")
        kind = "gist"
    size = " m" if spec.get("size") == "m" else ""
    hero = " hero" if spec.get("hero") else ""
    lead = ('<span class="qt-mark" aria-hidden="true">“</span>' if kind == "verbatim"
            else f'<span class="qt-gist">{ctx.t(spec.get("gist_label", "응답 요지"), 8, f"{where}.gist_label")}</span>')
    text = ctx.t(spec.get("text", ""), int(spec.get("limit", 60)), f"{where}.text")
    who = ctx.t(spec.get("who", ""), 24, f"{where}.who")
    src = ctx.t(spec.get("src", ""), 36, f"{where}.src")
    cite = " / ".join(x for x in (who, src) if x)
    ic = f'<span class="qt-ic">{icon(spec["icon"], 40)}</span>' if spec.get("icon") else ""
    return (f'<figure class="qt{size}{hero}" style="height:{px(h)}px">{lead}<blockquote class="qt-t">{text}</blockquote>'
            + (f'<figcaption class="qt-cite">{ic}<span>{cite}</span></figcaption>' if cite or ic else "") + '</figure>')


# ---------------------------------------------------------------------------
# 인라인 그림(장 파일 안에 작은 SVG 를 직접 적는 블록)
# ---------------------------------------------------------------------------
TOKEN_COLORS = {"#3d3935", "#da291c", "#b92217", "#fdf1ef", "#f6f4f1", "#e9e4dc", "#ffffff", "#fff", "#161616", "#5c5650",
                "#c9c3be", "#e8e2dd", "none", "currentcolor", "transparent", "url"}
SVG_FORBIDDEN = [
    (re.compile(r"<\s*(script|foreignobject|image|iframe|a|style|svg|object|embed)\b", re.I), "쓸 수 없는 요소"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "이벤트 속성"),
    (re.compile(r"javascript:|@import|<!", re.I), "스크립트나 외부 참조"),
    (re.compile(r"url\(\s*(?!#)", re.I), "url() 은 #id 만"),
    (re.compile(r"""(?:xlink:)?href\s*=\s*["'](?!#)""", re.I), "href 는 #id 만(외부 주소 금지)"),
]
ICON_PH = re.compile(r"\{\{icon:([^{}]+)\}\}")


@part("svg")
def p_svg(ctx: Ctx, spec: dict, w: float, h: float, where: str) -> str:
    """장 파일의 "svg"(도형 마크업, 바깥 <svg> 없이)를 box 크기의 <svg> 안에 넣는다. "vb": [폭, 높이] 는 좌표계(기본은 box 크기).
    - 글자: <text> 기본 26px(class="aux" 면 22px, 회색). 좌표계 배율을 곱한 화면 크기가 26px(보조 글 22px) 아래면 경고.
      <text> 하나의 글자 수 상한은 "limit"(기본 24). 자리 표시({{fact:}} 따위)를 쓸 수 있다.
    - 아이콘: <use href="{{icon:공시 문서}}" x=".." y=".." width="48" height="48"/>(덱 아이콘 사전의 개념 이름이나 아이콘 이름).
    - 색: class 로 토큰 색(sv-ink, sv-red, sv-muted, sv-line, sv-paper, sv-deep, sv-redbg, 글자는 red, muted, b). 그 밖의 색 값은 경고.
    - 외부 주소, 스크립트, 이벤트 속성, 이미지, 중첩 <svg> 는 빌드를 멈춘다."""
    raw = str(spec.get("svg", ""))

    def icon_ref(m: re.Match) -> str:
        sid = resolve_icon(m.group(1))
        if sid is None:
            ctx.errors.append(f"[{ctx.slide}] {where}.svg: 모르는 아이콘 {m.group(1)!r}")
            return "#i-doc"
        mark_icon(sid)
        return "#" + sid

    body = ICON_PH.sub(icon_ref, raw)
    for rx, why in SVG_FORBIDDEN:
        m = rx.search(body)
        if m:
            ctx.errors.append(f"[{ctx.slide}] {where}.svg: {why}: {body[max(0, m.start() - 10):m.end() + 20]!r}")
            return ""
    for m in re.finditer(r"""href=["']#((?:ic|i)-[a-z0-9-]+)["']""", body):
        sid = m.group(1)
        kind_, name = sid.split("-", 1)
        if (kind_ == "ic" and name not in LUCIDE) or (kind_ == "i" and name not in ICONS):
            ctx.errors.append(f"[{ctx.slide}] {where}.svg: 모르는 아이콘 {sid!r}")
        else:
            mark_icon(sid)
    body = ctx.sub(body)
    vw, vh = (float(x) for x in spec.get("vb", [w, h]))
    k = min(w / vw, h / vh) if vw and vh else 1.0
    limit = int(spec.get("limit", 24))
    for i, m in enumerate(re.finditer(r"<text\b([^>]*)>(.*?)</text>", body, flags=re.S)):
        attrs, inner = m.group(1), m.group(2)
        aux = re.search(r"""class=["'][^"']*\baux\b""", attrs) is not None
        fs = re.search(r"""font-size\s*[:=]\s*["']?\s*([\d.]+)""", attrs)
        size = float(fs.group(1)) if fs else (AUX_PX if aux else LABEL_PX)
        shown = size * k
        text = plain(inner)
        if shown < AUX_PX - 0.01:
            ctx.warn(f"{where}.text[{i}]", f"글자 {shown:.1f}px < {AUX_PX}px: {text[:16]}")
        elif shown < LABEL_PX - 0.01 and not aux:
            ctx.warn(f"{where}.text[{i}]", f"글자 {shown:.1f}px < {LABEL_PX}px(보조 글이면 class=\"aux\"): {text[:16]}")
        if len(text) > limit:
            ctx.warn(f"{where}.text[{i}]", f"{len(text)}자 > {limit}자: {text[:24]}")
    for m in re.finditer(r"""font-size\s*[:=]\s*["']?\s*([\d.]+)""", re.sub(r"<text\b[^>]*>", "", body)):
        if float(m.group(1)) * k < AUX_PX - 0.01:
            ctx.warn(f"{where}.svg", f"글자 {float(m.group(1)) * k:.1f}px < {AUX_PX}px")
    for m in re.finditer(r"""(?:fill|stroke|color|stop-color)\s*[:=]\s*["']?\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[a-z]+)""", body):
        if m.group(1).lower() not in TOKEN_COLORS:
            ctx.warn(f"{where}.svg", f"토큰 밖의 색 {m.group(1)}(class 의 토큰 색을 쓴다)")
    alt = plain(ctx.sub(spec.get("alt", "")))
    label = f'role="img" aria-label="{esc(alt)}"' if alt else 'aria-hidden="true"'
    return (f'<svg class="svgb" width="{px(w)}" height="{px(h)}" viewBox="0 0 {px(vw)} {px(vh)}" {label}>{body}</svg>')


ICONS_PER_SLIDE = 6        # 디자인 시스템 규칙: 한 화면에 아이콘 6개 이하


def count_icons(spec: Any) -> int:
    """장 파일이 직접 놓은 아이콘 수("icon" 값, 인라인 그림 블록의 아이콘 참조). C2(일곱 단계)와 C20(역할 칩)은 빼고 센다."""
    if isinstance(spec, dict):
        if spec.get("use") in ("C2", "C20"):
            return 0
        n = 0
        for k, v in spec.items():
            if k == "icon" and isinstance(v, str):
                n += 1
            elif k == "svg" and isinstance(v, str):
                n += len(re.findall(r"""href=["']#(?:ic|i)-[a-z0-9-]+""", v)) + len(re.findall(r"\{\{icon:[^{}]+\}\}", v))
            elif k != "legacy":
                n += count_icons(v)
        return n
    if isinstance(spec, list):
        return sum(count_icons(v) for v in spec)
    return 0


def count_marks(spec: Any) -> tuple[int, int]:
    """(강조 수, 큰 숫자 수). 강조는 hero 가 참인 곳, 큰 숫자는 C10, C11 블록과 C7 의 big."""
    heroes, bigs = 0, 0
    if isinstance(spec, dict):
        if spec.get("hero") is True:
            heroes += 1
        if spec.get("use") in ("C10", "C11"):
            bigs += 1
        if spec.get("use") == "C7" and spec.get("big"):
            bigs += 1
            if spec["big"].get("hero", True):
                heroes += 1
        if spec.get("use") == "C17" and spec.get("hero", "neck") == "neck":
            heroes += 1
        if spec.get("use") == "C16" and spec.get("total") is not None and spec.get("part", "both") != "week":
            bigs += 1
            if spec.get("hero", True):
                heroes += 1
        for k, v in spec.items():
            if k in ("hero", "legacy"):
                continue
            a, b = count_marks(v)
            heroes, bigs = heroes + a, bigs + b
    elif isinstance(spec, list):
        for v in spec:
            a, b = count_marks(v)
            heroes, bigs = heroes + a, bigs + b
    return heroes, bigs
