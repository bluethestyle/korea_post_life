"""표준담보 사이의 관계(포함, 통합)와, 표준담보 하나가 다른 종형의 보유 집합으로 덮이는지(온톨로지 설계안 2판 5절, 8절).

관계 자료는 data/seed/표준담보_관계.jsonl 이다. 줄마다 관계, 넓은담보ID, 넓은담보, 좁은담보ID, 좁은담보를 둔다.
- 포함: 넓은 담보가 좁은 담보를 포함한다(뇌졸중 진단비 ⊃ 뇌출혈 진단비). 넓은 담보를 가지면 좁은 담보의 지급 사유도 받는다.
- 통합: 통합 담보(넓은담보 칸) 하나를 부분 담보(좁은담보 칸) 여럿이 함께 채운다. 같은 통합 담보를 넓은담보로 둔 줄이 한 묶음이다.
  통합 담보를 가지면 부분 담보 하나하나를 받는 것으로 보고, 부분 담보를 모두 가지면 통합 담보를 가진 것으로 본다.
한 담보가 포함의 넓은 담보이면서 통합 담보일 수 있다(뇌·심장질환 수술비, 뇌·심장질환 주요치료비).

덮임은 네 갈래다(Relations.cover).
1. 같은 담보: 상대가 그 담보를 가진다.
2. 넓은 담보: 상대가 그 담보를 포함하는 넓은 담보나, 그 담보를 부분으로 둔 통합 담보를 가진다. 관계를 건너뛴 단계까지
   따라간다(뇌·심장질환 진단비 ⊃ 뇌혈관질환 진단비 ⊃ 뇌졸중 진단비 ⊃ 뇌출혈 진단비). 넓은 쪽을 따라갈 때는 두 관계를 함께 쓴다.
3. 부분 담보: 그 담보가 통합 담보이고 상대가 부분 담보를 모두 가진다. 부분 담보 하나하나는 같은 담보, 넓은 담보, 부분 담보 순으로
   따진다. 일부만 가지면 partial로 따로 표시하고 빠진 부분 담보를 missing에 적는다.
4. 없음. 덮지는 못해도 상대가 가진 좁은 담보(포함의 좁은 쪽, 통합의 부분 쪽, 건너뛴 단계 포함)는 narrower에 적는다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
RELATIONS_PATH = ROOT / "data" / "seed" / "표준담보_관계.jsonl"

INCLUDE, UNION = "포함", "통합"
KINDS = (INCLUDE, UNION)
FIELDS = ("관계", "넓은담보ID", "넓은담보", "좁은담보ID", "좁은담보")

SAME, BROADER, PARTS, NONE = "같은 담보", "넓은 담보", "부분 담보", "없음"


class RelationError(ValueError):
    """관계 자료가 사전과 맞지 않거나, 관계에 고리가 있다."""


def rows_from_names(rows: Iterable[dict[str, Any]], dictionary: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """표준담보명으로 적은 관계 줄(두 판독 의견)을 시드 꼴로 바꾼다. ID는 사전에서 이름으로 찾는다.

    사전에 없는 이름이 하나라도 있으면 RelationError를 낸다. 관계가 포함이나 통합이 아니어도 RelationError다.
    """
    rows = list(rows)
    by_name = {s["표준담보명"]: s["표준담보ID"] for s in dictionary}
    missing = sorted({r[k] for r in rows for k in ("넓은담보", "좁은담보") if r.get(k) not in by_name})
    if missing:
        raise RelationError("사전에 없는 표준담보명: " + ", ".join(map(str, missing)))
    wrong = sorted({str(r.get("관계")) for r in rows if r.get("관계") not in KINDS})
    if wrong:
        raise RelationError("관계는 포함이나 통합이어야 한다: " + ", ".join(wrong))
    return [{"관계": r["관계"], "넓은담보ID": by_name[r["넓은담보"]], "넓은담보": r["넓은담보"],
             "좁은담보ID": by_name[r["좁은담보"]], "좁은담보": r["좁은담보"]} for r in rows]


@dataclass(frozen=True)
class Cover:
    """표준담보 하나가 보유 집합으로 덮이는 모양.

    kind: 같은 담보 / 넓은 담보 / 부분 담보 / 없음
    via: 덮는 데 쓴 보유 담보ID(같은 담보면 그 담보 자신)
    partial: 부분 담보 가운데 일부만 가짐. 이때 missing에 빠진 부분 담보ID를 적는다
    narrower: 덮지 못할 때 보유 집합에 든 좁은 담보ID(정보로만 적는다)
    """
    kind: str
    via: tuple[str, ...] = ()
    partial: bool = False
    missing: tuple[str, ...] = ()
    narrower: tuple[str, ...] = ()

    @property
    def held(self) -> bool:
        """같은 담보, 넓은 담보, 부분 담보(일부 포함) 가운데 하나로 덮인다."""
        return self.kind != NONE


class Relations:
    """관계 줄을 읽어 넓은 쪽과 좁은 쪽, 통합 담보의 부분 담보를 찾는다."""

    def __init__(self, rows: Iterable[dict[str, Any]] = ()):
        self.rows = [dict(r) for r in rows]
        self.up: dict[str, set[str]] = {}          # 좁은 담보 → 바로 위 넓은 담보(포함의 넓은 쪽, 통합 담보)
        self.down: dict[str, set[str]] = {}        # 넓은 담보 → 바로 아래 좁은 담보
        self.parts: dict[str, list[str]] = {}      # 통합 담보 → 부분 담보(줄 순서)
        for r in self.rows:
            kind, wide, narrow = r.get("관계"), r.get("넓은담보ID"), r.get("좁은담보ID")
            if kind not in KINDS:
                raise RelationError(f"관계는 포함이나 통합이어야 한다: {kind!r}")
            if not wide or not narrow or wide == narrow:
                raise RelationError(f"넓은담보ID와 좁은담보ID가 비었거나 같다: {r}")
            self.up.setdefault(narrow, set()).add(wide)
            self.down.setdefault(wide, set()).add(narrow)
            if kind == UNION and narrow not in self.parts.setdefault(wide, []):
                self.parts[wide].append(narrow)
        loops = sorted(s for s in self.up if s in self.ancestors(s))
        if loops:
            raise RelationError("관계에 고리가 있다: " + ", ".join(loops))

    def __len__(self) -> int:
        return len(self.rows)

    @staticmethod
    def _walk(start: str, step: dict[str, set[str]]) -> set[str]:
        seen: set[str] = set()
        todo = list(step.get(start, ()))
        while todo:
            sid = todo.pop()
            if sid in seen:
                continue
            seen.add(sid)
            todo.extend(step.get(sid, ()))
        return seen

    def ancestors(self, sid: str) -> set[str]:
        """sid를 포함하거나 부분으로 둔 담보 전부(건너뛴 단계까지)."""
        return self._walk(sid, self.up)

    def descendants(self, sid: str) -> set[str]:
        """sid가 포함하거나 부분으로 둔 담보 전부(건너뛴 단계까지)."""
        return self._walk(sid, self.down)

    def check(self, dictionary: Iterable[dict[str, Any]]) -> list[str]:
        """사전과 맞지 않는 곳. ID가 사전에 없거나, 줄에 적은 이름이 사전의 이름과 다르면 적는다. 맞으면 빈 목록."""
        names = {s["표준담보ID"]: s["표준담보명"] for s in dictionary}
        out = []
        for r in self.rows:
            for id_col, name_col in (("넓은담보ID", "넓은담보"), ("좁은담보ID", "좁은담보")):
                sid = r[id_col]
                if sid not in names:
                    out.append(f"{sid}: 사전에 없음")
                elif r.get(name_col) is not None and names[sid] != r[name_col]:
                    out.append(f"{sid}: 줄의 이름 {r[name_col]!r}, 사전의 이름 {names[sid]!r}")
        return out

    def _covering(self, sid: str, held: set[str], seen: frozenset[str]) -> set[str]:
        """sid를 온전히 덮는 보유 담보. 같은 담보, 넓은 담보, 부분 담보를 모두 가짐 순으로 본다. 덮지 못하면 빈 집합."""
        if sid in held:
            return {sid}
        wide = self.ancestors(sid) & held
        if wide:
            return wide
        parts = self.parts.get(sid)
        if not parts or sid in seen:
            return set()
        got: set[str] = set()
        for p in parts:
            c = self._covering(p, held, seen | {sid})
            if not c:
                return set()
            got |= c
        return got

    def cover(self, sid: str, held: Iterable[str]) -> Cover:
        """표준담보 sid가 보유 집합 held로 덮이는 모양(모듈 설명의 네 갈래)."""
        held = set(held)
        if sid in held:
            return Cover(SAME, (sid,))
        wide = self.ancestors(sid) & held
        if wide:
            return Cover(BROADER, tuple(sorted(wide)))
        narrow = tuple(sorted(self.descendants(sid) & held))
        parts = self.parts.get(sid)
        if parts:
            via: set[str] = set()
            missing = []
            for p in parts:
                c = self._covering(p, held, frozenset({sid}))
                if c:
                    via |= c
                else:
                    missing.append(p)
            if len(missing) < len(parts):
                return Cover(PARTS, tuple(sorted(via)), partial=bool(missing), missing=tuple(missing), narrower=narrow)
        return Cover(NONE, narrower=narrow)


def read_rows(path: Path = RELATIONS_PATH) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_relations(path: Path = RELATIONS_PATH) -> Relations:
    """시드 파일의 관계. 파일이 없으면 관계가 없는 것으로 본다."""
    return Relations(read_rows(path))
