"""덱 HTML 의 보이는 글자가 심은 글꼴(PLKo)에 모두 있는지 본다. 실행: python tools/check_glyphs.py <out/index.html>"""
import base64, io, re, sys, html as H
from fontTools.ttLib import TTFont
doc = open(sys.argv[1], encoding="utf-8").read()
cmaps = []
for b64 in re.findall(r'font-family:\s*"PLKo".*?url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)', doc, re.S):
    f = TTFont(io.BytesIO(base64.b64decode(b64)))
    cmaps.append(set(f.getBestCmap().keys()))
common = set.intersection(*cmaps)
body = doc.split("<main", 1)[1].split("</main>", 1)[0]
body = re.sub(r'src="data:[^"]+"', "", body)
text = H.unescape(re.sub(r"<[^>]+>", " ", body))
ui = doc.split("</main>", 1)[1]
ui = H.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", ui, flags=re.S)))
missing = sorted({c for c in text + ui if not c.isspace() and ord(c) not in common})
print("글꼴 수:", len(cmaps), "없는 글자:", " ".join(f"{c}(U+{ord(c):04X})" for c in missing) or "없음")
