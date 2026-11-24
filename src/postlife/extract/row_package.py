"""행 패키지: 두 판독 초기 적재(scripts/load_reader_product.py, load_reader_conditions.py)가 문서로 만든 행을 파일로 남기고,
문서 없이 그 파일에서 행을 읽어 시트에 쓰는 길.

GitHub Actions 러너에서 공시실 접속이 막히는 회사(삼성생명, KB라이프생명. 2026-11-24 실행에서 PDF 다운로드 417, 목록 응답이
JSON이 아님)는 Actions가 문서를 다시 받지 못한다. 그래서 로컬에서 받은 문서로 평소처럼 행을 만들고(지문 대조, 기계 검사,
ID 중복 검사를 모두 거친 결과), 그 행을 저장소(data/backfill_rows/)에 커밋한다. Actions는 패키지를 검증한 뒤 시트에 쓴다.

패키지에 들어가는 것은 시트에 들어갈 행 그대로다(주간 스냅샷 data/snapshot으로 어차피 공개되는 값). 공시 원문 PDF와 글자 파일은
들어가지 않는다. 실행 시각, 로그ID처럼 실행마다 바뀌는 값은 넣지 않고 쓸 때 채운다. 같은 입력이면 같은 바이트가 나온다.

메타데이터
- 회사, 종류(급부, 가입조건)
- 대상설정: 대상 설정 파일의 저장소 안 경로와 sha256
- 값파일: 두 판독 검증 결과 파일(data/crosscheck/…_2reader.jsonl)의 저장소 안 경로와 sha256
- 문서: 공시 수집 결과(index.json)의 문서별 상품코드, 문서, 저장이름, sha256(행을 만든 문서가 무엇이었는지의 기록. 읽을 때는 문서가
  없으므로 대조하지 않는다)
- 행수: 탭별 행 수

읽을 때는 대상 설정과 값 파일의 해시가 체크아웃된 저장소의 파일과 같아야 한다. 다르면 행을 만든 뒤 값이 바뀐 것이므로 중단한다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "postlife.backfill_rows/1"
FOLDER = Path("data") / "backfill_rows"
BENEFITS, CONDITIONS = "급부", "가입조건"
SUFFIX = {BENEFITS: "benefits", CONDITIONS: "conditions"}


class PackageError(Exception):
    """패키지가 체크아웃된 저장소와 맞지 않거나 꼴이 틀렸다. 시트에 쓰지 않고 멈춘다."""


def default_path(root: Path, org: str, kind: str) -> Path:
    """data/backfill_rows/<회사>_benefits.json, <회사>_conditions.json"""
    return root / FOLDER / f"{org}_{SUFFIX[kind]}.json"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_path(path: Path, root: Path) -> str:
    """저장소 안 경로(슬래시). 저장소 밖 파일은 Actions의 체크아웃에 없으므로 패키지에 적을 수 없다."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        raise PackageError(f"저장소 밖의 파일이라 패키지에 적을 수 없음: {path}") from None


def documents(index: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """공시 수집 결과의 문서별 해시. 같은 입력이면 같은 차례가 되게 정렬한다."""
    out = [{"상품코드": e.get("상품코드"), "문서": e.get("문서"), "저장이름": e.get("저장이름"),
            "sha256": e.get("sha256") or e.get("해시")} for e in index]
    return sorted(out, key=lambda e: (str(e["상품코드"]), str(e["문서"]), str(e["저장이름"])))


def header(kind: str, org: str, targets: Path, value_files: Sequence[Path], index: Iterable[Mapping[str, Any]],
           root: Path) -> dict[str, Any]:
    files = sorted({repo_path(p, root) for p in value_files})
    return {
        "형식": FORMAT, "종류": kind, "회사": org,
        "대상설정": {"경로": repo_path(targets, root), "sha256": sha256_of(targets)},
        "값파일": [{"경로": f, "sha256": sha256_of(Path(root) / f)} for f in files],
        "문서": documents(index),
    }


def dumps(package: Mapping[str, Any]) -> str:
    return json.dumps(package, ensure_ascii=False, indent=1, default=_plain) + "\n"


def _plain(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"패키지에 담을 수 없는 값: {type(value).__name__}")


def write(path: Path, package: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(package), encoding="utf-8")


def read(path: Path, kind: str, org: str, targets: Path, root: Path,
         expected_values: Iterable[Path] | None = None) -> dict[str, Any]:
    """패키지를 읽고 체크아웃된 저장소와 맞춰 본다. 맞지 않으면 PackageError.

    - 형식, 종류, 회사가 같아야 한다.
    - 대상 설정(targets)의 sha256이 패키지의 값과 같아야 한다.
    - 패키지에 적힌 값 파일이 저장소에 있고 sha256이 같아야 한다.
    - expected_values(지금 저장소에서 그 회사가 쓸 값 파일 가운데 있는 것)를 주면, 패키지에 적힌 값 파일과 같은 묶음이어야 한다
      (패키지를 만든 뒤 값 파일이 새로 생긴 경우를 잡는다).
    """
    path = Path(path)
    if not path.exists():
        raise PackageError(f"행 패키지가 없음: {path}")
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PackageError(f"행 패키지를 읽지 못함: {e}") from None
    if not isinstance(package, dict) or package.get("형식") != FORMAT:
        raise PackageError(f"행 패키지의 형식이 {FORMAT}가 아님")
    if package.get("종류") != kind:
        raise PackageError(f"행 패키지의 종류가 '{package.get('종류')}'임('{kind}' 패키지가 필요함)")
    if package.get("회사") != org:
        raise PackageError(f"행 패키지의 회사가 '{package.get('회사')}'임(--org {org})")
    want = package.get("대상설정") or {}
    if not Path(targets).exists():
        raise PackageError(f"대상 설정이 없음: {targets}")
    if sha256_of(targets) != want.get("sha256"):
        raise PackageError(f"대상 설정({repo_path(targets, root)})의 sha256이 패키지를 만들 때({want.get('경로')})와 다름. "
                           "로컬에서 패키지를 다시 만들어야 함")
    recorded = set()
    for item in package.get("값파일") or []:
        file = Path(root) / item["경로"]
        recorded.add(item["경로"])
        if not file.exists():
            raise PackageError(f"값 파일이 저장소에 없음: {item['경로']}")
        if sha256_of(file) != item.get("sha256"):
            raise PackageError(f"값 파일({item['경로']})의 sha256이 패키지를 만들 때와 다름. 로컬에서 패키지를 다시 만들어야 함")
    if expected_values is not None:
        now = {repo_path(p, root) for p in expected_values}
        if now != recorded:
            raise PackageError(f"저장소의 값 파일 묶음이 패키지를 만들 때와 다름: 더 있음 {sorted(now - recorded)}, "
                               f"빠짐 {sorted(recorded - now)}")
    return package


def check_counts(package: Mapping[str, Any], counted: Mapping[str, int]) -> None:
    """패키지의 행수와 실제 행 수가 같아야 한다."""
    want = package.get("행수") or {}
    if dict(want) != dict(counted):
        raise PackageError(f"행 패키지의 행수 {dict(want)}가 실제 행 수 {dict(counted)}와 다름")
