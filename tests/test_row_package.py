"""행 패키지(src/postlife/extract/row_package.py와 두 적재 스크립트의 --rows-out, --rows-in).

조각, 값 파일, 대상 설정, 사업방법서 쪽 글자는 기존 적재 시험(test_load_reader_product.py, test_load_reader_conditions.py)의
지어낸 자료를 그대로 쓴다. 저장소 뿌리는 임시 폴더로 바꿔, 대상 설정과 값 파일을 그 안의 data/ 아래에 둔다.
"""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

import load_reader_conditions as LC  # noqa: E402
import load_reader_product as L  # noqa: E402
import test_load_reader_conditions as TC  # noqa: E402
import test_load_reader_product as TP  # noqa: E402
from postlife.extract import reader_rows as RR  # noqa: E402
from postlife.extract import row_package as P  # noqa: E402

ORG = "testorg"          # 패키지의 회사 이름이자 값 파일 이름의 앞머리


def jsonl(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    return path


def docs_folder(tmp_path, index):
    folder = tmp_path / "out"
    folder.mkdir()
    for e in index:
        (folder / f"{e['저장이름']}.pdf").write_bytes(b"%PDF-1.4 test")
    (folder / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return folder


class Repo:
    """임시 저장소: data/targets/<회사>.json과 data/crosscheck/의 값 파일."""

    def __init__(self, root, targets):
        self.root = root
        self.targets = root / "data" / "targets" / f"{ORG}.json"
        self.targets.parent.mkdir(parents=True, exist_ok=True)
        self.targets.write_text(json.dumps(targets, ensure_ascii=False), encoding="utf-8")
        self.crosscheck = root / "data" / "crosscheck"


# ---------------------------------------------------------------- 급부 패키지

@pytest.fixture
def benefits(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (TP.views(), {}))
    repo = Repo(tmp_path / "repo", TP.targets())
    values = {"Z1": jsonl(repo.crosscheck / f"{ORG}_Z1_benefits_2reader.jsonl", TP.VALUES)}
    return repo, docs_folder(tmp_path, TP.INDEX), values


def make_benefit_package(repo, docs, values, path=None):
    built = L.build(TP.targets(), TP.INDEX, docs, values)
    package = L.package_of(built, ORG, repo.targets, list(values.values()), TP.INDEX, repo.root)
    path = path or P.default_path(repo.root, ORG, P.BENEFITS)
    P.write(path, package)
    return path, package


def sheet_with_limits(repo, docs, values):
    """시트에 가입 한도가 적힌 특약 행과 다른 회사 행이 있는 상태."""
    built = L.build(TP.targets(), TP.INDEX, docs, values)
    rider = {**built.rows["sys_특약"][0], "최소가입금액만원": 100.0, "최대가입금액만원": 1000.0, "합산한도기준키": None}
    return {"sys_상품종형": [r for r in built.rows["sys_상품종형"] if r["종형ID"] == TP.VID], "sys_특약": [rider]}, rider


def test_benefit_package_round_trip_writes_the_same_sheet_as_the_document_path(benefits):
    repo, docs, values = benefits
    path, package = make_benefit_package(repo, docs, values)
    rows, rider = sheet_with_limits(repo, docs, values)

    by_docs = TP.store_with(rows)
    first = L.load(by_docs, TP.targets(), TP.INDEX, docs, values, TP.NOW)
    by_package = TP.store_with(rows)
    second = L.finish(by_package, L.read_package(path, ORG, repo.targets, repo.root), TP.NOW)

    assert first.written and second.written
    assert by_docs.read() == by_package.read()
    sheet = by_package.read()
    # 시트에 있던 가입 한도는 패키지에 없지만 쓸 때 잇는다
    assert next(r for r in sheet["sys_특약"] if r["특약ID"] == rider["특약ID"])["최대가입금액만원"] == 1000.0
    assert package["행수"] == {"sys_상품종형": len(package["행"]["sys_상품종형"]), "sys_특약": len(package["행"]["sys_특약"]),
                             "sys_급부": len(package["행"]["sys_급부"]), "sys_작업로그": len(package["작업로그"])}
    # 금액 없는 급부의 추출 기록은 패키지에서 와서 쓸 때 로그ID와 실행일시를 채운다
    extract_logs = [x for x in sheet["sys_작업로그"] if x["대상열"] == L.NO_AMOUNT_COLUMN]
    assert len(extract_logs) == len(package["작업로그"]) >= 1
    assert all(x["로그ID"] and x["실행일시"] == TP.NOW.isoformat(timespec="seconds") for x in extract_logs)


def test_same_input_gives_the_same_package_bytes_without_run_values(benefits, tmp_path):
    repo, docs, values = benefits
    a, _ = make_benefit_package(repo, docs, values, tmp_path / "a.json")
    b, package = make_benefit_package(repo, docs, values, tmp_path / "b.json")
    assert a.read_bytes() == b.read_bytes()
    assert all(x["로그ID"] is None and x["실행일시"] is None for x in package["작업로그"])
    text = a.read_text(encoding="utf-8")
    assert TP.SENTENCE not in text                     # 요약서의 지급사유 문장은 들어가지 않는다
    assert str(repo.root) not in text and str(docs) not in text      # 경로는 저장소 안 상대 경로만
    assert package["값파일"] == [{"경로": f"data/crosscheck/{ORG}_Z1_benefits_2reader.jsonl",
                                "sha256": P.sha256_of(values["Z1"])}]
    assert package["대상설정"]["경로"] == f"data/targets/{ORG}.json"


@pytest.mark.parametrize("change, message", [
    ("targets", "대상 설정"),
    ("values", "값 파일"),
    ("new_values", "값 파일 묶음"),
])
def test_a_package_stops_when_the_checkout_files_differ(benefits, change, message):
    repo, docs, values = benefits
    path, _ = make_benefit_package(repo, docs, values)
    if change == "targets":
        data = json.loads(repo.targets.read_text(encoding="utf-8"))
        data["상품"][0]["갱신형특약주기년"] = 10
        repo.targets.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    elif change == "values":
        jsonl(values["Z1"], TP.VALUES[:-1])
    else:                                                  # 패키지를 만든 뒤 다른 코드의 값 파일이 생김
        jsonl(repo.crosscheck / f"{ORG}_Z2_benefits_2reader.jsonl", TP.VALUES[:1])
    with pytest.raises(P.PackageError, match=message):
        L.read_package(path, ORG, repo.targets, repo.root)


def test_a_package_of_another_company_or_kind_is_refused(benefits):
    repo, docs, values = benefits
    path, _ = make_benefit_package(repo, docs, values)
    with pytest.raises(P.PackageError, match="회사"):
        L.read_package(path, "otherorg", repo.targets, repo.root)
    with pytest.raises(P.PackageError, match="종류"):
        P.read(path, P.CONDITIONS, ORG, repo.targets, repo.root)


def tampered(path, edit):
    package = json.loads(path.read_text(encoding="utf-8"))
    edit(package)
    path.write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")


def test_row_counts_that_do_not_match_stop_the_package(benefits):
    repo, docs, values = benefits
    path, _ = make_benefit_package(repo, docs, values)
    tampered(path, lambda p: p["행"]["sys_급부"].pop())
    with pytest.raises(P.PackageError, match="행수"):
        L.read_package(path, ORG, repo.targets, repo.root)


def test_format_errors_in_a_package_are_caught_like_the_document_path(benefits):
    repo, docs, values = benefits
    path, _ = make_benefit_package(repo, docs, values)

    def bad_rider(p):
        p["행"]["sys_특약"][0]["갱신여부"] = "예"
    tampered(path, bad_rider)
    store = TP.store_with()
    report = L.finish(store, L.read_package(path, ORG, repo.targets, repo.root), TP.NOW)
    assert report.errors.get("sys_특약") and not report.written
    assert store.read()["sys_특약"] == []

    path, package = make_benefit_package(repo, docs, values)
    target = package["행"]["sys_급부"][0]["급부ID"]

    def bad_benefit(p):
        p["행"]["sys_급부"][0]["기준지급금액만원"] = "많이"
    tampered(path, bad_benefit)
    store = TP.store_with()
    report = L.finish(store, L.read_package(path, ORG, repo.targets, repo.root), TP.NOW)
    assert report.written                                   # 급부 행은 그 행만 빼고 쓴다(기존 길과 같다)
    sheet = store.read()
    assert target not in {r["급부ID"] for r in sheet["sys_급부"]}
    assert any(x["대상행ID"] == target and x["결과"] == "반려" for x in sheet["sys_작업로그"])


def test_repeated_ids_in_a_package_write_nothing(benefits):
    repo, docs, values = benefits
    path, _ = make_benefit_package(repo, docs, values)

    def repeat(p):
        p["행"]["sys_급부"].append({**p["행"]["sys_급부"][0], "원시급부명": "다른 이름"})
        p["행수"]["sys_급부"] += 1
    tampered(path, repeat)
    store = TP.store_with()
    report = L.finish(store, L.read_package(path, ORG, repo.targets, repo.root), TP.NOW)
    assert report.clashes.get("sys_급부") and not report.written


def test_rows_dropping_off_the_sheet_are_counted(benefits):
    repo, docs, values = benefits
    path, package = make_benefit_package(repo, docs, values)
    gone = {**package["행"]["sys_특약"][0], "특약ID": package["행"]["sys_특약"][0]["특약ID"] + "x", "원시특약명": "없어진 특약"}
    store = TP.store_with({"sys_특약": [gone]})
    report = L.finish(store, L.read_package(path, ORG, repo.targets, repo.root), TP.NOW, dry_run=True)
    assert report.dropped["sys_특약"] == 1 and not report.written


# ---------------------------------------------------------------- 가입조건 패키지

@pytest.fixture
def conditions(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "read_pieces", lambda pdf, layout: (RR.load_pieces(TC.PIECES), {}))
    monkeypatch.setattr(LC, "read_pages", lambda docs, stem, wanted: {n: TC.PAGES[n] for n in wanted if n in TC.PAGES})
    repo = Repo(tmp_path / "repo", TC.targets())
    values = jsonl(repo.crosscheck / f"{ORG}_main_conditions_2reader.jsonl", TC.both())
    return repo, docs_folder(tmp_path, TC.INDEX), values


def make_condition_package(repo, docs, values, path=None):
    prepared = LC.prepare(TC.targets(), TC.INDEX, docs, values)
    package = LC.package_of(prepared, ORG, repo.targets, values, TC.INDEX, repo.root)
    path = path or P.default_path(repo.root, ORG, P.CONDITIONS)
    P.write(path, package)
    return path, package


def main_rider_on_sheet():
    """정밀비교 종형의 주계약 행이 이미 시트에 있는 상태(급부 패키지를 먼저 쓴 뒤)."""
    built = RR.build_rows(TC.VID, RR.load_pieces(TC.PIECES), {}, None, {})
    return {"sys_특약": [r for r in built.riders if r["담보구분"] == "주계약"]}


@pytest.mark.parametrize("rows", [None, "main"])
def test_condition_package_round_trip_writes_the_same_sheet_as_the_document_path(conditions, rows):
    repo, docs, values = conditions
    path, package = make_condition_package(repo, docs, values)
    start = main_rider_on_sheet() if rows else None
    by_docs = TC.store_with(start)
    first = LC.load(by_docs, TC.targets(), TC.INDEX, docs, values, TC.NOW)
    by_package = TC.store_with(start)
    second = LC.finish(by_package, LC.read_package(path, ORG, repo.targets, repo.root), TC.NOW)
    assert first.written and second.written
    assert by_docs.read() == by_package.read()
    assert [r["특약ID"] for r in second.new_mains] == ([TC.GATE_MAIN_ID] if rows else
                                                      [TC.MAIN_ID, TC.GATE_MAIN_ID])
    assert package["행수"] == {"종형": 2, "sys_가입조건": 4, "주계약후보": 2}


def test_same_input_gives_the_same_condition_package_bytes(conditions, tmp_path):
    repo, docs, values = conditions
    a, _ = make_condition_package(repo, docs, values, tmp_path / "a.json")
    b, _ = make_condition_package(repo, docs, values, tmp_path / "b.json")
    assert a.read_bytes() == b.read_bytes()


def test_a_condition_package_stops_when_the_value_file_differs(conditions):
    repo, docs, values = conditions
    path, _ = make_condition_package(repo, docs, values)
    jsonl(values, TC.both(top=66))
    with pytest.raises(P.PackageError, match="값 파일"):
        LC.read_package(path, ORG, repo.targets, repo.root)


def test_a_condition_package_with_rows_of_another_variant_or_unknown_fields_is_refused(conditions):
    repo, docs, values = conditions
    path, _ = make_condition_package(repo, docs, values)

    def other_variant(p):
        p["종형"][0]["가입조건"][0]["종형ID"] = TC.OTHER_VID
    tampered(path, other_variant)
    with pytest.raises(P.PackageError, match="다른 종형"):
        LC.read_package(path, ORG, repo.targets, repo.root)

    path, _ = make_condition_package(repo, docs, values)
    tampered(path, lambda p: p["종형"][0].update({"모르는칸": 1}))
    with pytest.raises(P.PackageError, match="꼴"):
        LC.read_package(path, ORG, repo.targets, repo.root)


def test_a_bad_condition_row_in_a_package_is_left_out_like_the_document_path(conditions):
    repo, docs, values = conditions
    path, package = make_condition_package(repo, docs, values)
    target = package["종형"][0]["가입조건"][0]["조건행ID"]

    def too_old(p):
        p["종형"][0]["가입조건"][0]["최저가입나이"] = 99
    tampered(path, too_old)
    store = TC.store_with()
    report = LC.finish(store, LC.read_package(path, ORG, repo.targets, repo.root), TC.NOW)
    assert report.written
    sheet = TC.read(store)
    assert target not in {r["조건행ID"] for r in sheet["sys_가입조건"]}
    assert any(x["대상행ID"] == target and x["결과"] == "반려" for x in sheet["sys_작업로그"])


# ---------------------------------------------------------------- 커밋된 패키지

COMMITTED = {"samsunglife": {"종형": 6, "특약": 153, "급부": 600, "가입조건": 36},
             "kblife": {"종형": 3, "특약": 212, "급부": 366, "가입조건": 24}}


@pytest.mark.parametrize("org", sorted(COMMITTED))
def test_committed_packages_match_the_checkout(org, tmp_path, monkeypatch):
    """커밋된 패키지가 저장소의 대상 설정, 값 파일과 맞는다. 대상 설정이나 값 파일을 고치면 패키지를 다시 만들어야 한다."""
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("SPREADSHEET_ID", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    want = COMMITTED[org]
    targets = f"data/targets/{org}.json"
    monkeypatch.chdir(ROOT)
    out = tmp_path / "b.json"
    assert L.main(["--rows-in", f"data/backfill_rows/{org}_benefits.json", "--org", org, "--targets", targets,
                   "--dry-run", "--result", str(out)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["종형 행"] == want["종형"]
    assert sum(c["특약"] for c in result["종형"].values()) == want["특약"]
    assert sum(c["급부"] for c in result["종형"].values()) == want["급부"]
    assert not result["ID 겹침"] and not result["형식 오류"]
    out = tmp_path / "c.json"
    assert LC.main(["--rows-in", f"data/backfill_rows/{org}_conditions.json", "--org", org, "--targets", targets,
                    "--dry-run", "--result", str(out)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["가입조건 행"] == want["가입조건"] and not result["쓰지 않은 종형"]
