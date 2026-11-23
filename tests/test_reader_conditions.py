"""초기 적재 주계약 가입조건 두 판독의 꼴 검사, 견줌, 기계 검사, 행 만들기. 쪽 글자와 표는 지어낸 것이다."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compare_condition_readers as script  # noqa: E402
from postlife import ids  # noqa: E402
from postlife.extract import reader_conditions as RC  # noqa: E402
from postlife.validate import check_rows  # noqa: E402

ORG = "GANA"
NAMES = ["2형 1종 가가간편형", "2형 1종 나나간편형"]
VIDS = [ids.variant_id(ORG, "X1", n) for n in NAMES]

# 지어낸 쪽 글자. 5쪽은 1형 표, 6쪽은 2형 표(식으로 적은 최고나이), 9쪽은 가입한도
PAGES = {
    "사업방법서": {
        5: "[가나건강보험-1형(지급형)]\n순번 보장 보험기간 납입기간 가입나이\n·기본계약(가나보장)\n"
           "80세만기 20년납 0세∼70세\n30년납 0세∼60세",
        6: "[가나건강보험-2형(미지급형)]\n순번 보장 보험기간 납입기간 가입나이\n·기본계약(가나보장)\n"
           "20년납 20세~(76-납\n80세만기\n30년납 입기간)세\n"
           "90세만기 20년납 20세~(86-납\n30년납 입기간)세",
        9: "가. 기본계약 가입한도\n15세~60세 1,000만원\n61세 이상 500만원",
    },
}


def task() -> dict:
    return {
        "형식": RC.TASK_FORMAT, "일감": "X1_간편", "기관코드": ORG, "쪽범위": [3, 10],
        "사업방법서": {}, "상품요약서": {},
        "종형": [{"종형ID": vid, "공시상품코드": "X1", "종형명": name} for vid, name in zip(VIDS, NAMES)],
    }


def line(term: str, pay: str, lo: int, hi: int, formula: str = "", page: int = 6, sex: str = "구분없음") -> dict:
    return {"쪽": page, "성별": sex, "보험기간": term, "납입기간": pay, "최저나이": lo, "최고나이": hi, "최고나이식": formula}


def reading(who: str = "sonnet", **table_changes) -> dict:
    table = {
        "표": "가", "근거쪽": 6, "근거낱말": ["2형", "미지급형"],
        "줄": [line("80세만기", "20년납", 20, 56, "76-납입기간"), line("80세만기", "30년납", 20, 46, "76-납입기간"),
               line("90세만기", "20년납", 20, 66, "86-납입기간"), line("90세만기", "30년납", 20, 56, "86-납입기간")],
        "한도없음": True, "한도": [], "모름": [],
    }
    table.update(table_changes)
    return {"형식": RC.FORMAT, "일감": "X1_간편", "판독자": who, "표": [table],
            "종형": [{"종형ID": vid, "표": "가", "모름": []} for vid in VIDS]}


def test_variant_entries_make_ids_like_variants_build():
    targets = {"기관코드": ORG, "상품": [{"비교역할구분": "정밀비교", "환급유형": "표준형", "종형": [
        {"공시상품코드": "X1", "종형명": NAMES[0], "심사유형": "간편심사", "간편고지약칭": "3.1.5"},
        {"공시상품코드": "Y2", "종형명": "일반형", "심사유형": "일반심사", "간편고지약칭": "일반", "비교역할구분": "관문전용"}]}]}
    got = RC.variant_entries(targets, ["Y2", "X1"])
    assert [e["종형ID"] for e in got] == [ids.variant_id(ORG, "Y2", "일반형"), VIDS[0]]
    assert got[0]["비교역할구분"] == "관문전용" and got[1]["비교역할구분"] == "정밀비교"


def test_task_with_a_wrong_variant_id_is_rejected():
    t = task()
    assert RC.check_task(t) == []
    t["종형"][0]["종형ID"] = "GANA_X1_000000"
    assert any("종형ID" in p for p in RC.check_task(t))


def test_clean_reading_passes_the_format_check():
    assert RC.check_file(task(), reading()) == []


def test_format_check_catches_bad_values_missing_variants_and_long_words():
    bad = reading(근거낱말=["가" * 21])
    bad["표"][0]["줄"].append(line("80세만기", "20년납", 15, 59))          # 같은 열쇠의 줄이 두 번
    bad["표"][0]["줄"].append(line("80세 만기", "20년", 15, 59))           # 납입기간 꼴이 아님
    bad["표"][0]["줄"].append({**line("90세만기", "10년납", 15, 79), "성별": "남"})
    problems = "\n".join(RC.check_file(task(), bad))
    assert "근거낱말" in problems and "두 번" in problems and "납입기간이" in problems and "성별이" in problems
    one = reading()
    one["종형"].pop()
    assert any("판독이 없는 종형 1개" in p for p in RC.check_file(task(), one))
    both = reading(한도=[{"쪽": 9, "문서": "사업방법서", "최저나이": 15, "최고나이": 60, "최고금액만원": 1000}])
    assert any("한도없음이 참인데" in p for p in RC.check_file(task(), both))
    blank = reading(한도없음=False)
    assert any("한도없음이 거짓인데" in p for p in RC.check_file(task(), blank))


def test_variant_without_a_table_needs_a_reason():
    r = reading()
    r["종형"][1] = {"종형ID": VIDS[1], "표": ""}
    assert any("모름에 이유가 없음" in p for p in RC.check_file(task(), r))
    r["종형"][1]["모름"] = [{"칸": "표", "이유": "이 간편형의 표를 찾지 못함"}]
    assert RC.check_file(task(), r) == []


def test_same_readings_with_clean_checks_are_confirmed():
    result = RC.compare_task(task(), {"sonnet": reading(), "opus": reading("opus")}, ["sonnet", "opus"], PAGES)
    assert [x["자동판정"] for x in result["줄"]] == [RC.CONFIRMED, RC.CONFIRMED]
    first = result["줄"][0]
    assert first["일치"] == {"줄": RC.SAME, "한도": RC.SAME, "근거쪽": RC.SAME}
    assert first["기계검사"]["sonnet"] == {"문제": [], "표시": []}


def test_a_different_age_or_missing_line_needs_judgement():
    other = reading("opus")
    other["표"][0]["줄"][0]["최고나이"] = 66
    other["표"][0]["줄"][0]["최고나이식"] = "86-납입기간"
    other["표"][0]["줄"].pop()
    result = RC.compare_task(task(), {"sonnet": reading(), "opus": other}, ["sonnet", "opus"], PAGES)
    x = result["줄"][0]
    assert x["자동판정"] == RC.NEEDS_JUDGE and x["일치"]["줄"] == RC.DIFF
    assert "구분없음/80세만기/20년납: 20~56세와 20~66세" in x["다른줄"]
    assert "구분없음/90세만기/30년납: 한쪽에만 있음" in x["다른줄"]
    # 둘째 판독의 식은 숫자가 맞게 계산됐지만 86은 80세만기 줄의 식이 아니다. 식의 숫자는 그 쪽에 있으므로 다름으로만 잡힌다
    assert "판정필요" in script.summary([result])


def test_machine_checks_catch_numbers_not_on_the_page_and_wrong_formula():
    t = reading()["표"][0]
    t["줄"][0]["최고나이"] = 55                                   # 76 - 20 = 56이 아님
    t["줄"][1]["최고나이식"] = ""                                 # 식 없이 적은 46세는 6쪽에 없다
    t["줄"][2]["최저나이"] = 16
    t["근거낱말"] = ["3형"]
    problems, marks = RC.machine_checks(t, PAGES, [3, 10])
    text = "\n".join(problems)
    assert "식으로 계산한 56세와 다름" in text
    assert "최고나이 46세가 6쪽에 없음" in text
    assert "최저나이 16세가 6쪽에 없음" in text
    assert "근거낱말 '3형'" in text
    assert marks == []


def test_machine_checks_mark_pages_and_impossible_ages():
    t = reading()["표"][0]
    t["줄"] = [line("80세만기", "20년납", 0, 70, page=5), line("80세만기", "30년납", 61, 60, page=5)]
    problems, marks = RC.machine_checks(t, PAGES, [6, 10])
    assert any("최저나이 61세가 최고나이 60세보다 큼" in p for p in problems)
    assert any("쪽 범위 밖" in m for m in marks) and any("근거쪽 6쪽보다 앞" in m for m in marks)
    t["줄"] = [line("80세만기", "20년납", 0, 80, page=6)]
    assert any("만기 나이 이상" in p for p in RC.machine_checks(t, PAGES)[0])


def test_title_words_that_point_to_another_type_are_marked():
    """두 판독이 같은 잘못된 형의 표를 골라도 근거낱말의 형 번호가 종형명과 다르면 확정하지 않는다."""
    wrong = {"근거쪽": 5, "근거낱말": ["1형", "지급형"],
             "줄": [line("80세만기", "20년납", 0, 70, page=5), line("80세만기", "30년납", 0, 60, page=5)]}
    a, b = reading(**wrong), reading("opus", **wrong)
    assert RC.machine_checks(a["표"][0], PAGES) == ([], [])
    result = RC.compare_task(task(), {"sonnet": a, "opus": b}, ["sonnet", "opus"], PAGES)
    x = result["줄"][0]
    assert x["일치"]["줄"] == RC.SAME and x["자동판정"] == RC.NEEDS_JUDGE
    assert "근거: 근거낱말 '1형'의 형이나 종 번호가 종형명에 없음" in x["기계검사"]["sonnet"]["표시"]
    assert RC.title_marks({"근거낱말": ["다라형"]}, NAMES[0]) == ["근거: 근거낱말이 종형명에 하나도 없음"]
    assert RC.title_marks({"근거낱말": ["2형", "미지급형"]}, NAMES[0]) == []


def test_missing_page_text_blocks_confirmation():
    result = RC.compare_task(task(), {"sonnet": reading(), "opus": reading("opus")}, ["sonnet", "opus"], None)
    assert all(x["자동판정"] == RC.NEEDS_JUDGE for x in result["줄"])
    assert any("글자가 없어" in p for p in result["줄"][0]["기계검사"]["sonnet"]["문제"])


def test_limits_are_checked_against_the_page_and_compared():
    limits = [{"쪽": 9, "문서": "사업방법서", "최저나이": 15, "최고나이": 60, "최저금액만원": None, "최고금액만원": 1000},
              {"쪽": 9, "문서": "사업방법서", "최저나이": 61, "최고나이": None, "최고금액만원": 500}]
    a = reading(한도없음=False, 한도=limits)
    assert RC.machine_checks(a["표"][0], PAGES) == ([], [])
    wrong = copy.deepcopy(limits)
    wrong[1]["최고금액만원"] = 700
    wrong[1]["최저나이"] = 60                                        # 앞 구간과 겹친다
    problems = RC.machine_checks(reading(한도없음=False, 한도=wrong)["표"][0], PAGES)[0]
    assert any("700" in p for p in problems) and any("겹침" in p for p in problems)
    result = RC.compare_task(task(), {"sonnet": a, "opus": reading("opus")}, ["sonnet", "opus"], PAGES)
    assert result["줄"][0]["일치"]["한도"] == RC.DIFF


def test_unknown_in_one_reading_needs_judgement_and_reasons_are_not_stored():
    other = reading("opus", 모름=[{"칸": "한도", "이유": "가입한도 절을 찾지 못함"}])
    result = RC.compare_task(task(), {"sonnet": reading(), "opus": other}, ["sonnet", "opus"], PAGES)
    x = result["줄"][0]
    assert x["일치"]["한도"] == RC.ONE_UNKNOWN and x["자동판정"] == RC.NEEDS_JUDGE
    assert x["opus"]["모름"] == ["한도"]
    assert "찾지 못함" not in json.dumps(x, ensure_ascii=False)


def test_rows_use_the_condition_id_rule_and_split_at_limit_ages():
    limits = [{"쪽": 9, "문서": "사업방법서", "최저나이": 15, "최고나이": 60, "최저금액만원": None, "최고금액만원": 1000},
              {"쪽": 9, "문서": "사업방법서", "최저나이": 61, "최고나이": None, "최고금액만원": 500}]
    value = RC.stored_value(reading(한도없음=False, 한도=limits)["표"][0], {"종형ID": VIDS[0], "표": "가"})
    built = RC.build_rows(task()["종형"], {VIDS[0]: value, VIDS[1]: None})
    assert built.done == [VIDS[0]] and any(VIDS[1] in n for n in built.notes)
    rows = {(r["보험기간구분"], r["납입기간구분"], r["최저가입나이"], r["최고가입나이"]): r for r in built.conditions}
    assert set(rows) == {("80세만기", "20년납", 20, 56), ("80세만기", "30년납", 20, 46),
                         ("90세만기", "20년납", 20, 60), ("90세만기", "20년납", 61, 66),
                         ("90세만기", "30년납", 20, 56)}
    split = rows[("90세만기", "20년납", 61, 66)]
    assert split["조건행ID"] == ids.condition_id(VIDS[0], "90세만기", "20년납", "", "", "61-66")
    assert split["특약ID"] is None and split["성별"] is None and split["구간최대가입금액만원"] == 500
    assert rows[("80세만기", "20년납", 20, 56)]["구간최대가입금액만원"] == 1000
    assert check_rows("sys_가입조건", built.conditions) == {}


def test_rows_keep_sex_and_scope_limits_to_their_period():
    value = {"줄": [line("90세만기", "20년납", 15, 69, sex="남자"), line("90세만기", "20년납", 15, 66, sex="여자"),
                   line("80세만기", "20년납", 15, 59)],
             "한도": [{"최저나이": 0, "최고나이": None, "보험기간": "90세만기", "납입기간": "", "최저금액만원": None,
                     "최고금액만원": 300}]}
    rows = RC.build_rows(task()["종형"][:1], {VIDS[0]: value}).conditions
    male = next(r for r in rows if r["성별"] == "M")
    assert male["조건행ID"] == ids.condition_id(VIDS[0], "90세만기", "20년납", "", "M", "15-69")
    assert male["구간최대가입금액만원"] == 300
    assert next(r for r in rows if r["보험기간구분"] == "80세만기")["구간최대가입금액만원"] is None


def test_final_value_follows_the_verdict():
    line_ = {"판정": "", "sonnet": {"줄": [1]}, "opus": {"줄": [2]}, "판정값": {"줄": [3]}}
    assert RC.final_value(line_, ["sonnet", "opus"]) is None
    assert RC.final_value({**line_, "판정": "확정"}, ["sonnet", "opus"]) == {"줄": [1]}
    assert RC.final_value({**line_, "판정": "opus"}, ["sonnet", "opus"]) == {"줄": [2]}
    assert RC.final_value({**line_, "판정": "수정"}, ["sonnet", "opus"]) == {"줄": [3]}


def test_script_checks_compares_and_writes_values_and_rows(tmp_path, capsys):
    text = tmp_path / "method.json"
    text.write_text(json.dumps({str(k): v for k, v in PAGES["사업방법서"].items()}, ensure_ascii=False), encoding="utf-8")
    t = task()
    t["사업방법서"] = {"글자": str(text)}
    task_path = tmp_path / "X1_간편.json"
    task_path.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    answers = tmp_path / "reads"
    answers.mkdir()
    for who in ("sonnet", "opus"):
        (answers / f"X1_간편.{who}.json").write_text(json.dumps(reading(who), ensure_ascii=False), encoding="utf-8")

    assert script.main([str(task_path), "--check", str(answers / "X1_간편.sonnet.json")]) == 0
    assert "꼴 문제 없음" in capsys.readouterr().out

    out, rows = tmp_path / "values.jsonl", tmp_path / "rows.jsonl"
    assert script.main([str(task_path), "--answers", str(answers), "--readers", "sonnet", "opus",
                        "--out", str(out), "--rows", str(rows)]) == 0
    printed = capsys.readouterr().out
    assert "자동판정: 확정 2, 판정필요 0" in printed
    values = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert [v["판정"] for v in values] == ["확정", "확정"]
    written = [json.loads(x) for x in rows.read_text(encoding="utf-8").splitlines()]
    assert len(written) == 8 and {r["종형ID"] for r in written} == set(VIDS)

    # 판정을 채운 값 파일로 행만 다시 만든다
    values[1]["판정"] = ""
    out.write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in values), encoding="utf-8")
    assert script.main([str(task_path), "--values", str(out), "--readers", "sonnet", "opus", "--rows", str(rows)]) == 0
    assert len(rows.read_text(encoding="utf-8").splitlines()) == 4
