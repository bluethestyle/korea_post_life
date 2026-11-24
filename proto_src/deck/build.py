#!/usr/bin/env python3
"""발표 덱 빌드: content.json + facts.json + tpl.html → out/index.html (오프라인 단독 HTML 한 파일).

실행:
    python3 build.py [--facts <facts.json>] [--fonts-css <fonts_v4.css>] [--out <index.html>]

- content.json 의 글에 든 자리 표시를 facts.json 의 값으로 채운다.
    {{fact:열쇠}}, {{fact:열쇠.하위키}}, {{fact:열쇠.0}}  값(정수는 천 단위 쉼표, 목록은 쉼표로 이음)
    {{fact:열쇠|f2}}                                        실수를 소수 둘째 자리로
    {{len:열쇠}}                                            목록이나 사전의 길이
    {{asof:열쇠}}                                           그 값의 기준일(as_of)
  facts.json 에 없는 열쇠나 하위키가 하나라도 있으면 빌드가 멈춘다.
- 화면 사진은 assets/<이름>.jpg 를 base64 로 넣는다(tools/prep_images.py 가 만든다).
- 글꼴은 fonts_v4.css 에서 PLKo(SUIT 서브셋) @font-face 만 골라 넣는다.
- 결과 HTML 에 외부 주소를 부르는 src, href, url(), @import 가 있으면 멈춘다.
- 영상 장은 out 폴더에 media/partN.mp4 가 있을 때만 <video> 를 넣고, 없으면 플레이스홀더만 둔다.
  mp4 를 out/media/ 에 넣은 뒤 다시 빌드한다.
- 같은 입력이면 같은 바이트가 나온다(시각, 난수를 쓰지 않는다).
- 덱이 쓴 facts 열쇠를 장마다 facts_used.json 에 적는다.
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PH = re.compile(r"\{\{(fact|len|asof):([^{}|]+?)(?:\|([a-z0-9]+))?\}\}")
IMG_NAMES = ("first", "market", "cover", "graph")


def find_upward(rel: str) -> Path | None:
    for base in [HERE, *HERE.parents]:
        cand = base / rel
        if cand.is_file():
            return cand
    return None


class Facts:
    def __init__(self, path: Path):
        self.facts = json.loads(path.read_text(encoding="utf-8"))["facts"]
        self.errors: list[str] = []
        self.used: dict[str, list[str]] = {}
        self.slide = "(덱)"

    def _lookup(self, path: str):
        key, *rest = path.split(".")
        if key not in self.facts:
            raise KeyError(f"열쇠 없음: {key}")
        entry = self.facts[key]
        value = entry["value"]
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
        return key, entry, value

    @staticmethod
    def _fmt(value, spec):
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
            if spec:
                raise TypeError(f"모르는 형식: {spec}")
            return repr(value)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join(Facts._fmt(v, spec) for v in value)
        raise TypeError(f"글로 적을 수 없는 값: {type(value).__name__}")

    def sub(self, text: str) -> str:
        def repl(m):
            kind, path, spec = m.group(1), m.group(2).strip(), m.group(3)
            try:
                key, entry, value = self._lookup(path)
                if kind == "fact":
                    out = self._fmt(value, spec)
                elif kind == "len":
                    if not isinstance(value, (list, dict)):
                        raise TypeError(f"길이를 셀 수 없는 값: {path}")
                    out = f"{len(value):,}"
                else:
                    out = entry["as_of"]
            except (KeyError, TypeError) as exc:
                self.errors.append(f"[{self.slide}] {m.group(0)}: {exc}")
                return m.group(0)
            used = self.used.setdefault(self.slide, [])
            if key not in used:
                used.append(key)
            return html.escape(out, quote=False)

        return PH.sub(repl, text)


def esc_attr(text: str) -> str:
    return html.escape(text, quote=True)


def strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


ARROW = ('<svg viewBox="0 0 40 16" aria-hidden="true"><path d="M0 8H34" stroke="currentColor" '
         'stroke-width="2" fill="none"/><path d="M28 2L37 8L28 14" stroke="currentColor" '
         'stroke-width="2" fill="none"/></svg>')
OPEN_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6" '
             'stroke="currentColor" stroke-width="2" fill="none"/></svg>')


class Builder:
    def __init__(self, content: dict, facts: Facts, images: dict[str, str], media_root: Path):
        self.c = content
        self.f = facts
        self.images = images
        self.media_root = media_root
        self.videos: list[str] = []
        self.total = len(content["slides"])

    def t(self, text: str) -> str:
        return self.f.sub(text)

    def img(self, key: str, alt: str, extra: str = "") -> str:
        if key not in self.images:
            raise SystemExit(f"사진 없음: assets/{key}.jpg")
        return f'<img src="{self.images[key]}" alt="{esc_attr(strip_tags(self.t(alt)))}"{extra}>'

    def chrome(self, s: dict, idx: int) -> tuple[str, str]:
        head = (f'<header class="hd"><p class="doc">{self.t(self.c["doc_name"])}</p>'
                f'<p class="chap">{self.t(s["chapter"])}</p></header>')
        foot_src = self.t(s.get("footer", ""))
        foot = (f'<footer class="ft"><p class="src">{foot_src}</p>'
                f'<p class="pg">{idx:02d} / {self.total:02d}</p></footer>')
        return head, foot

    def title_block(self, s: dict) -> str:
        return (f'<p class="eb rise">{self.t(s["eyebrow"])}</p>'
                f'<h2 class="ttl rise d1">{self.t(s["title"])}</h2>')

    def question(self, q: dict, d: str = "d5") -> str:
        return (f'<div class="q rise {d}"><p class="l">{self.t(q["label"])}</p>'
                f'<p class="t">{self.t(q["text"])}</p></div>')

    # 본문 배치
    def lay_data(self, s):
        b, side = s["big"], s["side"]
        items = "".join(f"<li>{self.t(x)}</li>" for x in side["items"])
        return (f'<div class="data"><div class="rise d2"><div class="big-row"><p class="big">{self.t(b["value"])}</p>'
                f'<p class="big-u">{self.t(b["unit"])}</p></div><p class="big-c">{self.t(b["caption"])}</p></div>'
                f'<div class="rise d3"><p class="side-lead">{self.t(side["lead"])}</p><ul class="ls">{items}</ul></div></div>')

    def lay_flow(self, s):
        parts = []
        for i, n in enumerate(s["nodes"]):
            d = f"d{min(i + 2, 6)}"
            if i:
                parts.append(f'<div class="arw rise {d}">{ARROW}</div>')
            sub = f'<p class="s">{self.t(n["sub"])}</p>' if n.get("sub") else ""
            hero = " hero" if n.get("hero") else ""
            parts.append(f'<div class="node{hero} rise {d}"><h3>{self.t(n["title"])}</h3>'
                         f'<p class="t">{self.t(n["text"])}</p>{sub}</div>')
        return f'<div class="flow">{"".join(parts)}</div>' + self.question(s["question"], "d6")

    def lay_shots(self, s):
        cells = []
        for i, sh in enumerate(s["shots"]):
            cells.append(f'<div class="shot rise d{i + 2}">{self.img(sh["img"], sh["alt"])}'
                         f'<h3>{self.t(sh["title"])}</h3><p>{self.t(sh["text"])}</p></div>')
        return f'<div class="shots">{"".join(cells)}</div>'

    def lay_table(self, s):
        tb = s["table"]
        head = "".join(f'<th style="width:{w}">{self.t(h)}</th>' for h, w in zip(tb["head"], tb["widths"]))
        rows = "".join("<tr>" + "".join(f"<td>{self.t(c)}</td>" for c in r) + "</tr>" for r in tb["rows"])
        return f'<table class="tb rise d2"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'

    def lay_cards(self, s):
        cells = []
        for i, c in enumerate(s["cards"]):
            no = f'<p class="no">{self.t(c["no"])}</p>' if c.get("no") else ""
            val = ""
            if c.get("value"):
                unit = f'<p class="u">{self.t(c["unit"])}</p>' if c.get("unit") else ""
                val = f'<div class="vr"><p class="v">{self.t(c["value"])}</p>{unit}</div>'
            cells.append(f'<div class="card rise d{i + 2}">{no}<h3>{self.t(c["title"])}</h3>{val}'
                         f'<p>{self.t(c["text"])}</p></div>')
        out = f'<div class="cards">{"".join(cells)}</div>'
        if s.get("question"):
            out += self.question(s["question"])
        return out

    def lay_compare(self, s):
        rows = "".join(f'<div class="kv-r"><p class="kv-v">{self.t(k["value"])}</p><p class="kv-t">{self.t(k["text"])}</p></div>'
                       for k in s["kv"])
        im = s["image"]
        return (f'<div class="cmp"><div class="rise d2">{rows}<p class="kv-n">{self.t(s["note"])}</p></div>'
                f'<figure class="fig rise d3" style="margin:0">{self.img(im["img"], im["alt"])}'
                f'<figcaption class="cap">{self.t(im["caption"])}</figcaption></figure></div>'
                + self.question(s["question"]))

    def lay_kpis(self, s):
        cells = []
        for i, k in enumerate(s["kpis"]):
            hero = " hero" if k.get("hero") else ""
            cells.append(f'<div class="k{hero} rise d{i + 2}"><p class="l">{self.t(k["label"])}</p>'
                         f'<div class="vr"><p class="v">{self.t(k["value"])}</p><p class="u">{self.t(k["unit"])}</p></div>'
                         f'<p>{self.t(k["text"])}</p></div>')
        return f'<div class="kpis">{"".join(cells)}</div><p class="line rise d6">{self.t(s["line"])}</p>'

    def lay_lists(self, s):
        cols = []
        for i, col in enumerate(s["columns"]):
            items = "".join(f"<li>{self.t(x)}</li>" for x in col["items"])
            cols.append(f'<div class="col rise d{i + 2}"><h3>{self.t(col["title"])}</h3><ul class="ls">{items}</ul></div>')
        return f'<div class="cols">{"".join(cols)}</div>'

    def lay_grid4(self, s):
        cells = "".join(f'<div class="pc rise d{i + 2}"><h3>{self.t(c["title"])}</h3><p>{self.t(c["text"])}</p></div>'
                        for i, c in enumerate(s["cells"]))
        return f'<div class="g4">{cells}</div><p class="line rise d6">{self.t(s["line"])}</p>'

    # 장 종류
    def notes(self, s):
        return f'<aside class="notes">{self.t(s.get("notes", ""))}</aside>'

    def section(self, s, idx, cls, inner):
        title = strip_tags(self.t(s["title"])) if s.get("title") else f'애니메이션 파트 {s.get("part", "")}'
        return (f'<section class="slide {cls}" id="s{idx}" data-id="{esc_attr(s["id"])}" '
                f'data-title="{esc_attr(title)}" aria-roledescription="장" '
                f'aria-label="{idx} / {self.total}: {esc_attr(title)}">{inner}{self.notes(s)}</section>')

    def k_body(self, s, idx):
        head, foot = self.chrome(s, idx)
        body = getattr(self, "lay_" + s["layout"])(s)
        return self.section(s, idx, "body-slide", f'{head}{self.title_block(s)}<div class="body">{body}</div>{foot}')

    def k_demo(self, s, idx):
        head, foot = self.chrome(s, idx)
        btn = s["button"]
        top = (f'<div class="eb-row rise"><p class="eb">{self.t(s["eyebrow"])}</p>'
               f'<a class="btn" href="{esc_attr(btn["href"])}" target="_blank" rel="noopener">{OPEN_ICON}{self.t(btn["label"])}</a></div>'
               f'<h2 class="ttl rise d1">{self.t(s["title"])}</h2>')
        heads = "".join(f'<div class="h">{self.t(h)}</div>' for h in ["", *s["heads"]])
        rows = []
        for i, st in enumerate(s["steps"], 1):
            rows.append(f'<div class="c n"><span>{i}</span></div><div class="c op">{self.t(st["op"])}</div>'
                        f'<div class="c">{self.t(st["q"])}</div><div class="c">{self.t(st["a"])}</div>')
        body = (f'<div class="steps rise d2" role="table" aria-label="시연 시나리오">{heads}{"".join(rows)}</div>'
                f'<p class="demo-url rise d3">{self.t(s["url_text"])}</p>')
        return self.section(s, idx, "demo-slide", f'{head}{top}<div class="body">{body}</div>{foot}')

    def k_video(self, s, idx):
        s2 = dict(s, title="", footer=s.get("footer", ""))
        head, foot = self.chrome(s2, idx)
        tag = f'애니메이션 파트 {self.t(s["part"])}, {self.t(s["length"])}'
        # 영상 파일이 index.html 옆에 있을 때만 <video> 를 넣는다. 없는 파일을 부르면
        # 브라우저 콘솔에 읽기 실패 오류가 남기 때문이다. mp4 를 넣은 뒤 다시 빌드하면 재생 장이 된다.
        video = ""
        if (self.media_root / s["src"]).is_file():
            video = (f'<video src="{esc_attr(s["src"])}" controls preload="metadata" playsinline '
                     f'aria-label="{esc_attr(tag)}"></video>')
            self.videos.append(s["src"])
        inner = (f'<div class="spine"></div>{head}<div class="vwrap"><div class="vframe">{video}'
                 f'<div class="vph"><p class="t1">{tag}, 파일 준비 중</p><p class="t2">{self.t(s["line"])}</p></div></div>'
                 f'<p class="vcap"><b>{tag}</b>. {self.t(s["line"])}</p></div>{foot}')
        return self.section(s, idx, "video", inner)

    def k_cover(self, s, idx):
        meta = "".join(f'<div class="cm"><p class="l">{self.t(m["l"])}</p><p class="v">{self.t(m["v"])}</p></div>'
                       for m in s["meta"])
        tl = s["tiles"]

        def num(n, cls):
            return (f'<div class="tile {cls}"><p class="l">{self.t(n["label"])}</p><div class="vr">'
                    f'<p class="v">{self.t(n["value"])}</p><p class="u">{self.t(n["unit"])}</p></div></div>')

        tiles = (f'<div class="tiles rise d3"><div class="tile ink wide"><p class="l">{self.t(tl["names_label"])}</p>'
                 f'<p class="s">{self.t(tl["names"])}</p></div>{num(tl["num1"], "paper")}{num(tl["num2"], "spot")}'
                 f'<div class="tile media wide"><p class="l">{self.t(tl["media"]["label"])}</p>'
                 f'{self.img(tl["media"]["img"], tl["media"]["alt"])}</div></div>')
        body = (f'<div class="spine"></div><div class="cover-body"><p class="badge rise">{self.t(s["badge"])}</p>'
                f'<h1 class="cover-h1 rise d1">{self.t(s["title"])}</h1>'
                f'<p class="cover-lead rise d2">{self.t(s["lead"])}</p>'
                f'<div class="cover-meta rise d3">{meta}</div></div>{tiles}')
        return self.section(s, idx, "cover", body)

    def k_closing(self, s, idx):
        links = "".join(f'<p class="l">{self.t(x["l"])}</p><p class="v">{self.t(x["v"])}</p>' for x in s["links"])
        btn = s["button"]
        body = (f'<div class="spine"></div><div class="close-body"><p class="eb rise">{self.t(s["eyebrow"])}</p>'
                f'<h1 class="cover-h1 rise d1">{self.t(s["title"])}</h1>'
                f'<p class="close-lead rise d2">{self.t(s["lead"])}</p>'
                f'<div class="links rise d3">{links}</div>'
                f'<div class="close-row rise d4"><a class="btn" href="{esc_attr(btn["href"])}" target="_blank" rel="noopener">'
                f'{OPEN_ICON}{self.t(btn["label"])}</a><p class="small">{self.t(s["small"])}</p></div></div>')
        return self.section(s, idx, "closing", body)

    def build(self) -> str:
        out = []
        for idx, s in enumerate(self.c["slides"], 1):
            self.f.slide = s["id"]
            out.append(getattr(self, "k_" + s["kind"])(s, idx))
        return "\n".join(out)


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


def digits_outside(content: dict) -> list[str]:
    """자리 표시 밖에 숫자를 직접 적은 글(검토용 목록. 빌드를 멈추지 않는다)."""
    found = []

    def walk(o, where):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("id", "kind", "layout", "img", "src", "href", "widths", "format"):
                    continue
                walk(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")
        elif isinstance(o, str):
            bare = re.sub(r"<[^>]+>", "", PH.sub("", o))
            for m in re.finditer(r"[0-9][0-9.,~:-]*", bare):
                ctx = bare[max(0, m.start() - 8):m.end() + 6]
                found.append(f"{where}: {m.group(0)}  …{ctx}…")

    walk(content.get("slides", []), "slides")
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=str(HERE / "content.json"))
    ap.add_argument("--facts", default=None)
    ap.add_argument("--fonts-css", default=None)
    ap.add_argument("--tpl", default=str(HERE / "tpl.html"))
    ap.add_argument("--assets", default=str(HERE / "assets"))
    ap.add_argument("--out", default=str(HERE / "out" / "index.html"))
    ap.add_argument("--used", default=str(HERE / "facts_used.json"))
    a = ap.parse_args()

    facts_path = Path(a.facts) if a.facts else find_upward("presentation_animation/facts.json")
    fonts_path = Path(a.fonts_css) if a.fonts_css else find_upward("proto_src/fonts/fonts_v4.css")
    if not facts_path or not facts_path.is_file():
        raise SystemExit("facts.json 을 찾지 못했습니다. --facts 로 넘긴다")
    if not fonts_path or not fonts_path.is_file():
        raise SystemExit("fonts_v4.css 를 찾지 못했습니다. --fonts-css 로 넘긴다")

    content = json.loads(Path(a.content).read_text(encoding="utf-8"))
    facts = Facts(facts_path)
    images = {}
    for name in IMG_NAMES:
        p = Path(a.assets) / f"{name}.jpg"
        if p.is_file():
            images[name] = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")

    out = Path(a.out)
    builder = Builder(content, facts, images, out.parent)
    slides_html = builder.build()
    if facts.errors:
        print("facts.json 에 없는 자리 표시:", file=sys.stderr)
        for e in facts.errors:
            print("  " + e, file=sys.stderr)
        raise SystemExit(1)

    tpl = Path(a.tpl).read_text(encoding="utf-8")
    doc = (tpl.replace("__HTML_TITLE__", esc_attr(content["html_title"]))
              .replace("<!--__FONT_NOTICE__-->", FONT_NOTICE)
              .replace("/*__FONT_FACES__*/", font_faces(fonts_path))
              .replace("<!--__SLIDES__-->", slides_html))
    leftovers = re.findall(r"__[A-Z_]+__|\{\{[^}]*\}\}", doc)
    if leftovers:
        raise SystemExit(f"채우지 못한 자리: {leftovers[:5]}")
    hits = check_external(doc)
    if hits:
        print("외부 요청이 될 주소:", file=sys.stderr)
        for h in hits:
            print("  " + h, file=sys.stderr)
        raise SystemExit(1)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(doc.encode("utf-8"))
    Path(a.used).write_text(json.dumps(facts.used, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{out} {out.stat().st_size:,} 바이트, 장 {len(content['slides'])}개, 외부 요청 0, "
          f"넣은 영상 {len(builder.videos)}개{' ' + ', '.join(builder.videos) if builder.videos else ''}")
    digits = digits_outside(content)
    if digits:
        print(f"자리 표시 밖의 숫자 {len(digits)}곳(검토용):")
        for d in digits:
            print("  " + d)


if __name__ == "__main__":
    main()
