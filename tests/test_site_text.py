"""해설 글(src/postlife/site/commentary.py, calc.js의 fillText·commentItems)과 응대 카드 자료(card.py)의 시험."""
import json
import re
import subprocess

import pytest

from postlife.site import build, card, commentary
from postlife.site.model import Data, load
from test_site import CALC_JS, NODE, ROOT, SNAPSHOT, fake_tables, needs_node, row

APP_JS = ROOT / "src" / "postlife" / "site" / "assets" / "app.js"


def repo_raw():
    return json.loads(commentary.DEFAULT_PATH.read_text(encoding="utf-8"))


def load_from(tmp_path, raw):
    path = tmp_path / "commentary.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return commentary.load(path)


# ---------- 검사 ----------
def test_저장소의_해설_글은_하나도_버려지지_않는다():
    raw = repo_raw()
    texts, warnings = commentary.load()
    assert warnings == []
    assert set(texts) == set(commentary.ALLOWED) == {"s1", "s2", "s3", "s4", "s5", "s6"}
    for screen, entry in texts.items():
        assert set(entry) == set(commentary.ITEMS) | {commentary.EMPTY}, screen
        assert entry == raw[screen]                                   # 검사를 거쳐도 그대로다
    assert set(texts["s3"]["결론"]) == set(texts["s3"]["이유"]) == {"우위", "대등", "열위"}


def test_변수_자리_밖에_숫자가_있는_글은_버린다(tmp_path):
    raw = repo_raw()
    raw["s1"]["결론"] = "{snapshotDate} 기준 {orgCount}개 기관 가운데 3곳을 점검했습니다."
    raw["s2"]["이유"] = "나이 구간을 ５세 단위로 묶습니다."                    # 전각 숫자도 숫자다
    texts, warnings = load_from(tmp_path, raw)
    assert "결론" not in texts["s1"] and "이유" not in texts["s2"]
    assert texts["s1"]["읽는법"] == raw["s1"]["읽는법"] and texts["s1"]["없을때"] == raw["s1"]["없을때"]
    assert any("s1 결론" in w and "숫자" in w for w in warnings) and any("s2 이유" in w for w in warnings)
    assert len(warnings) == 2


def test_그_화면에_허용되지_않은_변수를_쓴_글은_버린다(tmp_path):
    raw = repo_raw()
    raw["s2"]["읽는법"] = "{baseLabel} 종형의 가입 나이를 봅니다."              # 화면 3의 변수
    raw["s3"]["결론"]["우위"] = "{snapshotDate} 기준으로 {baseLabel} 종형이 낫습니다."
    raw["s6"]["없을때"]["결론"] = "{unknownCount}건이 없습니다."
    texts, warnings = load_from(tmp_path, raw)
    assert "읽는법" not in texts["s2"]
    assert set(texts["s3"]["결론"]) == {"대등", "열위"}                           # 세 벌 가운데 걸린 한 벌만 버린다
    assert "결론" not in texts["s6"]["없을때"] and texts["s6"]["없을때"]["이유"] == raw["s6"]["없을때"]["이유"]
    assert [w for w in warnings if "허용되지 않은 변수" in w] == [
        "해설 글 버림: s2 읽는법 (이 화면에 허용되지 않은 변수: baseLabel)",
        "해설 글 버림: s3 결론.우위 (이 화면에 허용되지 않은 변수: snapshotDate)",
        "해설 글 버림: s6 없을때.결론 (이 화면에 허용되지 않은 변수: unknownCount)"]


def test_중괄호_짝이_맞지_않거나_비어_있는_글은_버린다(tmp_path):
    raw = repo_raw()
    raw["s4"]["결론"] = "{condLabel 조건에서 고른 조합입니다."
    raw["s5"]["출처"] = ""
    raw["s3"]["이유"] = "세 벌이 아닌 글"
    texts, warnings = load_from(tmp_path, raw)
    assert "결론" not in texts["s4"] and "출처" not in texts["s5"] and "이유" not in texts["s3"]
    assert len(warnings) == 3


def test_파일이_없거나_깨지면_해설_없이_빌드한다(tmp_path):
    texts, warnings = commentary.load(tmp_path / "없음.json")
    assert texts == {} and warnings and "없음" in warnings[0]
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    texts, warnings = commentary.load(tmp_path / "broken.json")
    assert texts == {} and "읽지 못함" in warnings[0]
    data = Data(fake_tables(), {"snapshot_at": "2026-11-18T17:00:00+09:00"})
    assert build.read_payload(build.render(data, texts={}))["commentary"] == {"texts": {}, "s3Margin": 0}


def test_화면이_쓰는_변수는_app_js가_모두_계산한다():
    app = APP_JS.read_text(encoding="utf-8")
    for screen, names in commentary.ALLOWED.items():
        for name in names:
            assert re.search(r"\b" + name + r"\s*:", app), f"{screen}의 {name} 값을 app.js가 계산하지 않음"


def test_화면3의_벌을_가르는_문턱은_기준값_탭에_있으면_그_값이다():
    tables = fake_tables()
    data = Data(tables, {"snapshot_at": "2026-11-18T17:00:00+09:00"})
    assert build.payload(data)["commentary"]["s3Margin"] == 0
    tables["hum_기준값"].append(row("hum_기준값", 기준키="COMMENT_S3_MARGIN", 기준분류="해설", 기준명="문턱", 수치값=2, 적용시작일="2026-11-18"))
    assert build.payload(Data(tables, {"snapshot_at": "2026-11-18T17:00:00+09:00"}))["commentary"]["s3Margin"] == 2


# ---------- 변수 끼우기 (calc.js) ----------
HARNESS = """
const calc = require(process.argv[1]);
let text = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => text += c).on('end', () => {
  const cases = JSON.parse(text);
  process.stdout.write(JSON.stringify(cases.map(c => c.fill !== undefined ? calc.fillText(c.fill, c.values)
    : calc.commentItems(c.entry, c.values, c.variant))));
});
"""


def run_cases(cases):
    done = subprocess.run([NODE, "-e", HARNESS, str(CALC_JS)], input=json.dumps(cases, ensure_ascii=False),
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def as_map(items):
    return {x["item"]: x["text"] for x in items}


S4 = {"condLabel": "50세 남성", "variantLabel": "시험보험 1종", "mainAmount": "4,000만원", "riderTotalCount": 1234,
      "pickedRiderCount": 3, "stdPayoutCount": 5, "ruleCount": 7, "noLimitCount": 0}


@needs_node
def test_변수_값을_끼우고_숫자는_쉼표를_찍는다():
    texts = commentary.load()[0]
    out = run_cases([{"fill": "{a}개와 {b}", "values": {"a": 12345, "b": "이름"}}, {"fill": "{a}개", "values": {"a": None}},
                     {"fill": "{a}개", "values": {}}, {"fill": None, "values": {}}, {"fill": "{a}개", "values": {"a": 0}},
                     {"entry": texts["s4"], "values": S4}])
    assert out[:5] == ["12,345개와 이름", None, None, None, "0개"]        # 값이 0이면 0으로 쓴다. 비어 있을 때만 값이 없다
    got = as_map(out[5])
    assert list(got) == ["결론", "읽는법", "이유", "유의점", "출처"]
    assert got["결론"] == ("50세 남성 조건에서 시험보험 1종 종형의 주계약 4,000만원과 특약 1,234개 가운데 3개를 조합해 "
                         "표준담보 5개의 실제 지급액을 계산했습니다.")


@needs_node
def test_변수_값이_없으면_없을때_글을_쓰고_그것도_없으면_항목을_내지_않는다():
    texts = commentary.load()[0]
    s2 = {"condLabel": "50세 남성", "shownCount": 6, "knownCount": 5, "okCount": 5, "noCondCount": 1, "simpleCount": 3}
    cases = [
        {"entry": texts["s4"], "values": {**S4, "mainAmount": None}},           # 주계약에 가입할 수 없는 나이
        {"entry": texts["s2"], "values": {**s2, "condLabel": None, "okCount": None}},   # 나이를 비움
        {"entry": texts["s2"], "values": {**s2, "noCondCount": None}},           # 유의점에는 없을때 글이 없다
        {"entry": {k: v for k, v in texts["s4"].items() if k != "결론"}, "values": S4},   # 검사에서 버린 결론
        {"entry": texts["s5"], "values": {}},                                     # 개정 전후 짝이 없음
        {"entry": None, "values": {}},
    ]
    out = [as_map(x) for x in run_cases(cases)]
    empty4 = texts["s4"]["없을때"]
    assert out[0]["결론"] == empty4["결론"].replace("{condLabel}", "50세 남성").replace("{variantLabel}", "시험보험 1종")
    assert out[0]["이유"] == empty4["이유"]                                  # 결론이 없을때 글이면 이유도 없을때 글이다
    assert out[0]["읽는법"] == texts["s4"]["읽는법"]
    assert out[1]["결론"] == texts["s2"]["없을때"]["결론"].replace("{shownCount}", "6") and "유의점" in out[1]
    assert "유의점" not in out[2] and out[2]["결론"].startswith("50세 남성 조건에서")
    assert "결론" not in out[3] and out[3]["이유"].startswith("특약의 가입금액과")       # 버린 글 대신 없을때 글을 쓰지 않는다
    assert out[4] == {"결론": texts["s5"]["없을때"]["결론"], "읽는법": texts["s5"]["읽는법"], "이유": texts["s5"]["없을때"]["이유"],
                      "유의점": texts["s5"]["유의점"], "출처": texts["s5"]["출처"]}
    assert out[5] == {}
    assert not any("{" in t or "}" in t for x in out for t in x.values())


@needs_node
def test_화면3은_고른_벌의_결론과_이유를_쓴다():
    texts = commentary.load()[0]
    values = {"condLabel": "50세 남성", "baseLabel": "우체국 1종", "peerLabel": "민영 1종", "baseBetterCount": 4,
              "peerBetterCount": 1, "sameCount": 2, "mixedCount": 1, "gapCount": 3}
    out = [as_map(x) for x in run_cases([{"entry": texts["s3"], "values": values, "variant": v} for v in ("우위", "대등", "열위", "없을때")])]
    for got, v in zip(out[:3], ("우위", "대등", "열위")):
        assert got["결론"].startswith("50세 남성 조건에서 기준인 우체국 1종 종형")
        assert got["결론"] == texts["s3"]["결론"][v].format(**values) and got["이유"] == texts["s3"]["이유"][v].format(**values)
    assert out[3]["결론"] == texts["s3"]["없을때"]["결론"].format(**values) and out[3]["이유"] == texts["s3"]["없을때"]["이유"]
    assert out[3]["읽는법"] == texts["s3"]["읽는법"]


# ---------- 응대 카드 자료 ----------
def test_응대_카드_자료():
    real = card.build(load(SNAPSHOT))
    banner = next(json.loads(line)["문자값"] for line in (SNAPSHOT / "hum_기준값.jsonl").read_text(encoding="utf-8").splitlines()
                  if json.loads(line)["기준키"] == "TEXT_CARD_BANNER")
    assert real["banner"] == banner                                          # 맨 위 표식은 기준값 탭의 글자
    assert sum(real["caps"].values()) == card.TOTAL_LINES == 35               # 묶음 일곱의 줄 수 상한이 A4 한 장 안
    assert real["rows"] == real["caps"]["table"] - 1 == 12 and real["names"] == 5
    assert len(real["footer"]) == 3 and not any(re.search(r"[0-9]", t) for t in real["footer"])
    assert "심사 결과에 따릅니다" in real["footer"][1] and "배포" in real["footer"][0]
    # 기준값 탭에 표식이 없으면 기획 3.5의 글을 쓴다
    fake = card.build(Data(fake_tables(), {}))
    assert fake["banner"] == card.DEFAULT_BANNER


def test_실제_자료의_화면에는_해설과_카드_자료가_실린다():
    data = load(SNAPSHOT)
    payload = build.payload(data)
    assert payload["commentary"]["texts"] == commentary.load()[0] and payload["commentary"]["s3Margin"] == 0
    assert payload["card"]["banner"] == data.setting_text("TEXT_CARD_BANNER")
