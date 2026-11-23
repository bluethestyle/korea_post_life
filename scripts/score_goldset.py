"""뽑은 결과를 정답셋(data/goldset)과 맞춰 본다.

정답은 문장으로 적혀 있어, 정답 문장 속의 값이 뽑은 행에 있는지를 본다.
기계로 가릴 수 없는 항목(여러 급부를 더한 금액 등)은 "직접 확인"으로 남긴다.

- 보장금액·면책·감액(기본): 정답 속 금액, 면책 날수, 감액 기간, 일수 한도, 지급 횟수가 `sys_급부` 행에 있는가.
- 가입조건: 주계약의 가입나이와 가입한도를 묻는 항목만 본다. 나이는 `sys_가입조건`의 최저가입나이와 최고가입나이,
  최고 한도는 그 나이 구간의 구간최대가입금액만원, 최저 한도는 `sys_특약` 주계약 행의 최소가입금액만원과 맞춘다.
  특약의 가입조건, 보험기간과 납입기간의 종류처럼 다른 것을 묻는 항목은 "직접 확인"으로 남긴다.

종형: 정답 항목이 가리키는 종형마다 따로 채점해 가장 나쁜 판정을 낸다.
`상품과종`이 "상품 · 가입유형 범위" 꼴(한화생명)이면 범위 안의 종형("13개 가입유형 공통"이면 전부)을 보고,
그 꼴이 아니면 이름이 그대로 적힌 종형("4종(일반가입)"), 다음으로 "1~4종"처럼 번호로 적힌 종형들을 보고,
둘 다 없으면 상품 이름이 맞는 첫 종형을 본다. 범위 안의 종형이 결과에 하나도 없으면 "대상 없음"이다.

  python scripts/score_goldset.py --result 간편한건강보험=<결과 JSON> --result 통합건강보험=<결과 JSON>
  python scripts/score_goldset.py --gold data/goldset/hanwha_goldset.jsonl --numbers 101-114 --result 시그니처H통합보험=<결과 JSON>
  python scripts/score_goldset.py --gold data/goldset/hanwha_conditions_goldset.jsonl --area 가입조건 --result 시그니처H통합보험=<결과 JSON>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from postlife.extract.benefits import _WON, _amounts, squash  # noqa: E402

GOLD = Path(__file__).resolve().parents[1] / "data/goldset/epost_goldset.jsonl"
AREAS = ("보장금액·면책·감액", "가입조건")
RANK = {"일치": 0, "직접 확인": 1, "불일치": 2}


def money_values(text: str) -> list[float]:
    """정답 속 금액(만 원). "5,000원"처럼 원으로만 적힌 금액도 읽는다."""
    flat = squash(text)
    values = [value for _, value in _amounts(flat) if value]
    return values + [int(m.group(1)) / 10000 for m in _WON.finditer(flat) if int(m.group(1))]


def norm(text: str) -> str:
    return re.sub(r"[\s·∙ㆍⅡⅢII]", "", text)


def loose(text: str) -> str:
    """지급 횟수 문구를 견줄 때 쓰는 글자. 빈칸, 구두점, 괄호, "지급"을 뗀다."""
    return re.sub(r"[\s·∙ㆍ,()\[\]]|지급", "", text or "")


def _months(n: int, unit: str) -> int:
    return n * 12 if unit == "년" else n if unit == "개월" else max(1, round(n / 30))


def score(item: dict, riders: list[dict], benefits: list[dict]) -> tuple[str, str]:
    """보장금액·면책·감액 항목 하나를 한 종형의 특약·급부 행과 맞춘다."""
    # 급부 이름에 가운뎃점이 든 경우(항암방사선·약물치료보험금)를 위해 특약 이름은 " · " 앞까지만 본다
    head, _, tail = item["특약급부명"].partition(" · ")
    names = [n.strip() for n in tail.split(",")] if tail else [head.strip()]
    rider_ids = {r["특약ID"] for r in riders if norm(r["원시특약명"]) == norm(head)} if tail else {r["특약ID"] for r in riders}
    rows = [b for b in benefits if b["특약ID"] in rider_ids and any(norm(b["원시급부명"]).startswith(norm(n)) for n in names)]
    if item["정답"].strip() == "문서에 없음":
        return ("일치", "해당 급부를 뽑지 않음") if not rows else ("불일치", f"문서에 없는 급부를 {len(rows)}줄 뽑음")
    if not rows:
        return "불일치", "해당 급부를 찾지 못함"
    have: set[float] = set()
    for b in rows:
        if b.get("기준지급금액만원") is None:      # 금액 하나로 담기지 않는 급부(지급기준구분 차등지급 따위)는 금액이 없다
            continue
        have.add(float(b["기준지급금액만원"]))
        for rate in (b.get("감액지급률1"), b.get("감액지급률2")):
            if rate is not None:
                have.add(round(float(b["기준지급금액만원"]) * float(rate), 4))
    wanted = money_values(item["정답"])
    missing: list = [w for w in wanted if w not in have]
    derived = [w for w in missing if any(abs(a + b - w) < 1e-6 for a in have for b in have)]
    missing = [w for w in missing if w not in derived]
    notes, passed = [], []
    answer = squash(item["정답"])
    for n, unit in re.findall(r"(\d+)(일|년)이지난", answer):         # 보장개시일: "90일이 지난 날의 다음 날"
        days = int(n) * (365 if unit == "년" else 1)
        if any(b["면책기간일수"] == days for b in rows):
            passed.append(f"면책 {days}일")
        else:
            missing.append(f"면책 {days}일")
    if answer == "계약일":                                           # 보장개시일이 계약일이면 면책이 없다
        (passed if any(b["면책기간일수"] == 0 for b in rows) else missing).append("면책 0일")
    for n, unit in re.findall(r"(\d+)(년|개월|일)미만", answer):      # 감액 기간: "2년 미만"
        months = _months(int(n), unit)
        if any(months in (b.get("감액개월1"), b.get("감액개월2")) for b in rows):
            passed.append(f"감액 {months}개월")
        else:
            missing.append(f"감액 {n}{unit} 미만")
    for days in re.findall(r"(\d+)일한도", answer):
        if any(f"{days}일" in squash(str(b.get("지급횟수제한") or "")) for b in rows):
            passed.append(f"{days}일 한도")
        else:
            notes.append(f"{days}일 한도가 지급횟수제한 칸에 없음")
    if "감액없음" in answer:
        if any(b.get("감액지급률1") is not None for b in rows):
            missing.append("감액 없음")
        else:
            passed.append("감액 없음")
    if not wanted and re.search(r"\d+회", answer):                   # 금액 없이 지급 횟수만 묻는 정답: "최초 1회한"
        limits = sorted({str(b.get("지급횟수제한") or "") for b in rows})
        if any(loose(answer) in loose(x) for x in limits):
            passed.append("지급횟수제한 같음")
        elif any(set(re.findall(r"(\d+)회", squash(x))) == set(re.findall(r"(\d+)회", answer)) for x in limits):
            notes.append(f"지급횟수제한 칸의 글이 다름: {limits}")
        else:
            missing.append(f"지급횟수제한 {limits}")
    if missing:
        return "불일치", f"뽑은 행에 없는 값: {missing}"
    if derived or notes:
        return "직접 확인", "; ".join(([f"더해서 나오는 금액 {derived}"] if derived else []) + notes)
    if wanted:
        return "일치", f"금액 {sorted(set(wanted))}"
    if passed:
        return "일치", ", ".join(passed)
    return "직접 확인", "정답에 기계로 맞춰 볼 값이 없음"


_TERM = re.compile(r"\d+세만기|\d+년만기|종신")
_PAY = re.compile(r"\d+년납|전기납|일시납")
_AGE_COND = re.compile(r"(\d+)세(이하|이상|미만|초과)|(\d+)세~(\d+)세")


def _in_band(cond: dict, m: re.Match) -> bool:
    lo, hi = cond["최저가입나이"], cond["최고가입나이"]
    if m.group(1):
        n = int(m.group(1))
        return {"이하": hi <= n, "미만": hi < n, "이상": lo >= n, "초과": lo > n}[m.group(2)]
    return lo >= int(m.group(3)) and hi <= int(m.group(4))


def _limit(question: str, answer: str, rows: list[dict], rider: dict | None) -> tuple[str, str]:
    """주계약 가입한도. 정답을 나이 구간("61세 이상")으로 나눠 구간마다 최고 한도와 최저 한도를 맞춘다."""
    text = re.sub(r"\(?\d+만원단위\)?|\(고정\)", "", answer)
    marks = list(_AGE_COND.finditer(text))
    if marks:
        parts = [(None, text[:marks[0].start()])] + [
            (m, text[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(text)]) for i, m in enumerate(marks)]
    else:
        parts = [(_AGE_COND.search(question), text)]                 # 나이 구간이 질문에만 있다: "70세 이하일 때"
    missing, notes, passed = [], [], []
    for m, part in parts:
        values = money_values(part)
        if not values:
            continue
        if len(values) > 2:
            return "직접 확인", f"한 구간에 금액이 셋 이상: {values}"
        label = re.sub(r"세(이하|이상|미만|초과)", r"세 \1", m.group(0)) if m else "기본"
        band = [c for c in rows if _in_band(c, m)] if m else rows
        tops = {float(c["구간최대가입금액만원"]) for c in band if c.get("구간최대가입금액만원") is not None}
        if not tops:
            missing.append(f"{label} 가입조건 행 없음")
            continue
        top = max(tops) if m is None else (tops.pop() if len(tops) == 1 else None)
        if top != values[-1]:
            missing.append(f"{label} 최고 {values[-1]:g}만원 (행: {sorted({float(c['구간최대가입금액만원']) for c in band})})")
        else:
            passed.append(f"{label} 최고 {top:g}만원")
        if len(values) == 2:
            low = rider.get("최소가입금액만원") if rider else None
            if low is None:
                notes.append(f"{label} 최저 {values[0]:g}만원은 맞춰 볼 칸이 없음")
            elif float(low) != values[0]:
                missing.append(f"{label} 최저 {values[0]:g}만원 (주계약 최소가입금액 {float(low):g}만원)")
            else:
                passed.append(f"{label} 최저 {values[0]:g}만원")
    if missing:
        return "불일치", f"맞지 않음: {missing}"
    if notes:
        return "직접 확인", "; ".join(notes)
    return ("일치", ", ".join(passed)) if passed else ("직접 확인", "정답에서 금액을 읽지 못함")


def _age(question: str, answer: str, rows: list[dict]) -> tuple[str, str]:
    """주계약 가입나이. 질문의 보험기간, 납입기간, 성별에 맞는 행의 최저가입나이와 최고가입나이로 맞춘다."""
    low, high = min(c["최저가입나이"] for c in rows), max(c["최고가입나이"] for c in rows)
    ages = [int(n) for n in re.findall(r"(\d+)세", answer)]
    span = re.search(r"(\d+)세?~(\d+)세", answer)
    if "최저" in question and "최고" not in question:
        wanted = [("최저", ages[0], low)]
    elif "최고" in question and "최저" not in question:
        wanted = [("최고", ages[0], high)]
    elif span:
        wanted = [("최저", int(span.group(1)), low), ("최고", int(span.group(2)), high)]
    else:
        return "직접 확인", "정답에서 나이 범위를 읽지 못함"
    missing = [f"{what} {want}세 (행: {got}세)" for what, want, got in wanted if want != got]
    for term in _TERM.findall(answer):                              # 나이와 함께 답한 보험기간: "만15~80세, 20년만기"
        if not any(squash(c["보험기간구분"]).startswith(term) for c in rows):
            missing.append(f"보험기간 {term}")
    if missing:
        return "불일치", f"맞지 않음: {missing}"
    return "일치", ", ".join(f"{what} {want}세" for what, want, _ in wanted)


def score_condition(item: dict, riders: list[dict], conds: list[dict]) -> tuple[str, str]:
    """가입조건 항목 하나를 한 종형의 주계약 가입조건 행과 맞춘다."""
    head = item["특약급부명"].partition(" · ")[0].strip()
    if not head.startswith("주계약"):
        return "직접 확인", "특약의 가입조건은 채점하지 않음"
    question, answer = squash(item["질문"]), squash(item["정답"])
    term = next(iter(_TERM.findall(question)), None)
    pay = next(iter(_PAY.findall(question)), None)
    sexes = [s for s, pattern in (("M", "남자|남성"), ("F", "여자|여성")) if re.search(pattern, question)]
    sex = sexes[0] if len(sexes) == 1 else None                      # 둘 다 물으면 성별로 가르지 않는다
    rows = [c for c in conds if not c.get("특약ID")
            and (term is None or squash(c["보험기간구분"]).startswith(term))
            and (pay is None or c["납입기간구분"] == pay)
            and (sex is None or c.get("성별") in (sex, None))]
    asked = " ".join(x for x in (term, pay, {"M": "남자", "F": "여자"}.get(sex or "")) if x)
    if answer == "문서에없음":
        if not (term or pay):
            return "직접 확인", "문서에 없음을 맞춰 볼 조건이 질문에 없음"
        return ("일치", f"{asked} 가입조건 행이 없음") if not rows else ("불일치", f"문서에 없는 조건({asked})의 행 {len(rows)}줄")
    if "한도" in question and ("가입한도" in question or "가입금액" in question):
        rider = next((r for r in riders if r.get("담보구분") == "주계약"), None)
        return _limit(question, answer, rows, rider)
    if "나이" in question and re.search(r"\d+세", answer):
        if not rows:
            return "불일치", f"조건({asked or '없음'})에 맞는 주계약 가입조건 행이 없음"
        return _age(question, answer, rows)
    return "직접 확인", "주계약 가입나이나 가입한도를 묻는 항목이 아님"


def scope_names(scope: str) -> set[str] | None:
    """한화생명 `상품과종`의 " · " 뒤 가입유형 범위를 종형명 묶음으로. "공통"이면 None(전부).

    "간편가입형(0·1·2·3·4·5·10년), 일반가입형, 건강가입형(6~10년)" → {간편가입형(0년), …, 일반가입형, 건강가입형(6년), …}
    """
    text = re.sub(r"\s", "", scope)
    if re.search(r"(전|\d+개)가입유형공통", text):
        return None
    names: set[str] = set()
    for base, inner in re.findall(r"([가-힣]+형)(?:\(([^()]*)\))?", text):
        if base == "가입유형":
            continue
        if not inner:
            names.add(base)
            continue
        for part in re.split(r"[·∙ㆍ]", inner):                     # "0·1·2·3·4·5·10년"은 끝의 "년"을 함께 쓴다
            m = re.fullmatch(r"(\d+)(?:~(\d+))?년?", part) if inner.endswith("년") else None
            if m:
                names.update(f"{base}({n}년)" for n in range(int(m.group(1)), int(m.group(2) or m.group(1)) + 1))
            else:
                names.add(f"{base}({part})")
    return names


def pick_types(product: str, types: list[dict]) -> list[dict]:
    """정답 항목의 `상품과종`이 가리키는 종형들."""
    if len(types) == 1 and types[0]["종형ID"] is None:              # 종형 구분이 없는 결과
        return types
    _, sep, scope = product.partition(" · ")
    if sep:
        names = scope_names(scope)
        return list(types) if names is None else [t for t in types if squash(t["종형명"]) in names]
    flat = squash(product)
    named = [t for t in types if t["종형명"] and squash(t["종형명"]) in flat]
    if named:
        return named
    m = re.search(r"(?<![\d.])(\d{1,2})~(\d{1,2})종", product)       # 빈칸을 떼면 "2606 1~4종"이 "26061~4종"이 된다
    if m:
        numbered = [t for t in types if any(t["종형명"].startswith(f"{n}종") for n in range(int(m.group(1)), int(m.group(2)) + 1))]
        if numbered:
            return numbered
    return types[:1]


def combine(scored: list[tuple[dict, tuple[str, str]]]) -> tuple[str, str]:
    """종형마다 낸 판정을 하나로. 가장 나쁜 판정과 그 종형을 적는다."""
    if len(scored) == 1:
        return scored[0][1]
    worst = max(RANK[verdict] for _, (verdict, _) in scored)
    hits = [(t, why) for t, (verdict, why) in scored if RANK[verdict] == worst]
    verdict = next(v for v, r in RANK.items() if r == worst)
    if verdict == "일치" or len({why for _, why in hits}) == 1:
        where = f"종형 {len(scored)}개 모두" if len(hits) == len(scored) else ", ".join(t["종형명"] for t, _ in hits)
        return verdict, f"{hits[0][1]} ({where})"
    return verdict, "; ".join(f"{t['종형명']}: {why}" for t, why in hits)


def load_result(key: str, path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows") or {"sys_특약": data["riders"], "sys_급부": data["benefits"]}
    if rows.get("sys_상품종형"):      # 여러 상품이 든 결과면 이름이 맞는 상품의 종형만 본다
        types = [v for v in rows["sys_상품종형"] if key in squash(v["공시상품명"])]
    else:
        types = [{"종형ID": None, "종형명": ""}]
    return {"types": types, "riders": rows["sys_특약"], "benefits": rows["sys_급부"], "conds": rows.get("sys_가입조건") or []}


def score_item(item: dict, result: dict, area: str) -> tuple[str, str]:
    if not result["types"]:
        return "대상 없음", "결과에 이 상품의 종형이 없음"
    targets = pick_types(item["상품과종"], result["types"])
    if not targets:
        return "대상 없음", f"결과에 이 종형이 없음 ({item['상품과종'].partition(' · ')[2] or item['상품과종']})"
    scored = []
    for t in targets:
        riders = [r for r in result["riders"] if t["종형ID"] is None or r["종형ID"] == t["종형ID"]]
        if area == "가입조건":
            conds = [c for c in result["conds"] if t["종형ID"] is None or c["종형ID"] == t["종형ID"]]
            scored.append((t, score_condition(item, riders, conds)))
        else:
            scored.append((t, score(item, riders, result["benefits"])))
    return combine(scored)


def parse_numbers(text: str) -> set[int]:
    """"101-114,120" → {101, …, 114, 120}. 거꾸로 적은 범위("114-101")는 받지 않는다."""
    numbers: set[int] = set()
    for part in text.split(","):
        low, _, high = part.strip().partition("-")
        try:
            low_n, high_n = int(low), int(high or low)
        except ValueError:
            raise argparse.ArgumentTypeError(f"번호 범위를 읽지 못함: {text} (예: 101-114,120)")
        if low_n > high_n:                                           # 빈 묶음이 되면 번호 거름이 꺼진다
            raise argparse.ArgumentTypeError(f"번호 범위가 거꾸로임: {part.strip()} (작은 번호를 앞에, 예: {high_n}-{low_n})")
        numbers.update(range(low_n, high_n + 1))
    return numbers


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--result", action="append", required=True, metavar="상품명에 든 글자=결과 JSON")
    p.add_argument("--gold", type=Path, default=GOLD, help="정답셋 JSONL (기본: 우체국 정답셋)")
    p.add_argument("--numbers", type=parse_numbers, metavar="101-114", help="이 번호들만 채점한다. 쉼표로 여럿")
    p.add_argument("--area", default=AREAS[0], choices=AREAS)
    args = p.parse_args(argv)
    results = {}
    for pair in args.result:
        key, path = pair.split("=", 1)
        results[key] = load_result(key, Path(path))
    tally: dict[str, int] = {}
    for line in args.gold.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item["영역"] != args.area or (args.numbers is not None and int(item["번호"]) not in args.numbers):
            continue
        key = next((k for k in results if k in squash(item["상품과종"])), None)
        if key is None:
            continue
        verdict, why = score_item(item, results[key], args.area)
        tally[verdict] = tally.get(verdict, 0) + 1
        print(f"{item['번호']:>3} {verdict} | {item['특약급부명'][:44]} | {why}")
    print(tally)
    return 0


if __name__ == "__main__":
    sys.exit(main())
