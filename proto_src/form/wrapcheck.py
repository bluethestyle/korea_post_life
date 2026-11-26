"""작품설명서 HTML 에서 단어 중간에 줄이 바뀐 곳과, 마지막 줄에 짧은 한 단어만 남은 곳을 찾는다.

실행(playwright 가 든 파이썬, 리포 루트에서):
    python proto_src/form/build.py --strict --html <견본.html>      # identity 없이 만든 견본
    python proto_src/form/wrapcheck.py <견본.html>
"""
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright
JS = r"""() => {
  const out = {split: [], orphan: []};
  const pages = Array.from(document.querySelectorAll('section.page'));
  for (const pg of pages) {
    const no = pg.getAttribute('data-no');
    const walker = document.createTreeWalker(pg, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const txt = n.textContent;
      if (!txt.trim()) continue;
      const el = n.parentElement;
      if (!el || el.closest('svg')) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const re = /\S+/g; let m;
      const lines = [];
      while ((m = re.exec(txt))) {
        const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
        const rects = Array.from(r.getClientRects()).filter(x => x.width > 0.5);
        if (!rects.length) continue;
        const tops = Array.from(new Set(rects.map(x => Math.round(x.top))));
        if (tops.length > 1) out.split.push({no, word: m[0], ctx: txt.trim().slice(0, 60)});
        lines.push({top: Math.round(rects[0].top), w: m[0]});
      }
      // 마지막 줄에 한 단어(4자 이하)만 남은 경우: 같은 블록 요소의 마지막 텍스트 노드일 때만
      if (lines.length >= 3 && n === (function last(e){let w=document.createTreeWalker(e,NodeFilter.SHOW_TEXT),l=null,x;while((x=w.nextNode())){if(x.textContent.trim())l=x}return l})(el)) {
        const lastTop = lines[lines.length - 1].top;
        const lastLine = lines.filter(l => l.top === lastTop);
        const firstTop = lines[0].top;
        if (lastTop !== firstTop && lastLine.length === 1 && lastLine[0].w.replace(/[^가-힣A-Za-z0-9]/g,'').length <= 3)
          out.orphan.push({no, word: lastLine[0].w, ctx: txt.trim().slice(-50)});
      }
    }
  }
  return out;
}"""
path = Path(sys.argv[1]).resolve()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 1600})
    pg.goto(path.as_uri()); pg.wait_for_timeout(500)
    pg.emulate_media(media="print")
    res = pg.evaluate(JS); b.close()
print("단어 중간 줄바꿈", len(res["split"]))
for x in res["split"]: print(f"  {x['no']}쪽 | {x['word']} | {x['ctx']}")
print("마지막 줄에 짧은 한 단어", len(res["orphan"]))
for x in res["orphan"]: print(f"  {x['no']}쪽 | {x['word']} | …{x['ctx']}")
