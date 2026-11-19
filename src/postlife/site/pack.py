"""화면에 싣는 자료를 줄여 적는다. 내용은 하나도 빼지 않는다.

build.py가 만든 자료를 pack()으로 줄여 HTML에 넣고, 화면은 calc.js의 unpack()으로 원래 모양을 되살린다.
시험(tests/test_site.py)이 "줄였다 되살린 것 == 원래 자료"를 Python과 calc.js 양쪽에서 확인한다.
규칙을 고치면 calc.js의 unpack도 함께 고친다.

줄이는 방법
- 여러 번 나오는 글자(ID, 특약명, 사유 문장, 키 이름)는 목록 "s"에 한 번만 적고 "~번호"(36진수)로 가리킨다.
- " · "로 이어 붙인 이름은 조각으로 나눠 적는다. 작업 기록의 대상 이름이 종형명·특약명을 되풀이하기 때문이다.
- 키가 같은 묶음이 줄지어 있으면 키를 한 번만 적은 표로 바꾼다.
- 같은 값이 이어지는 배열은 값과 개수로 적는다.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

VERSION = 1
MARK = "~"
RUN, ROWS, KEYED, JOINED = "~=", "~#", "~@", "~+"   # 같은 값 반복 / 묶음의 배열 / 묶음의 묶음 / 이어 붙인 글자
SPECIAL = (RUN, ROWS, KEYED, JOINED)
SEP = " · "
RUN_MIN = 4
_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _code(n: int) -> str:
    out = ""
    while True:
        out = _DIGITS[n % 36] + out
        n //= 36
        if n == 0:
            return out


def _worth(text: str, count: int) -> bool:
    """목록에 올려 가리키는 편이 짧아지는 글자인지. 가리키는 글자는 따옴표까지 6바이트쯤으로 잡는다."""
    size = len(text.encode("utf-8"))
    return count >= 2 and (size + 2) * count > (size + 3) + count * 6


def _scalar(value: Any) -> bool:
    return not isinstance(value, (list, dict))


def _same_keys(items: list[Any]) -> bool:
    return (len(items) >= 2 and all(isinstance(x, dict) for x in items) and bool(items[0])
            and all(list(x) == list(items[0]) for x in items))


def pack(data: Any) -> dict[str, Any]:
    whole: Counter[str] = Counter()

    def count(node: Any) -> None:
        if isinstance(node, str):
            whole[node] += 1
        elif isinstance(node, list):
            for x in node:
                count(x)
        elif isinstance(node, dict):
            for key, value in node.items():
                whole[key] += 1
                count(value)

    count(data)
    pieces: Counter[str] = Counter(whole)
    for text, n in whole.items():
        if SEP in text and not _worth(text, n):
            for part in text.split(SEP):
                pieces[part] += n
    table = sorted((s for s, n in pieces.items() if _worth(s, n)), key=lambda s: (-pieces[s], s))
    ref = {s: MARK + _code(i) for i, s in enumerate(table)}

    def word(text: str) -> str:
        if text in ref:
            return ref[text]
        return MARK + text if text.startswith(MARK) else text

    def enc(node: Any) -> Any:
        if isinstance(node, str):
            if node not in ref and SEP in node:
                parts = node.split(SEP)
                if any(p in ref for p in parts):
                    return {JOINED: [word(p) for p in parts]}
            return word(node)
        if isinstance(node, list):
            if len(node) >= RUN_MIN and all(_scalar(x) and type(x) is type(node[0]) and x == node[0] for x in node):
                return {RUN: [enc(node[0]), len(node)]}
            if _same_keys(node):
                return {ROWS: [[word(k) for k in node[0]]] + [[enc(v) for v in x.values()] for x in node]}
            return [enc(x) for x in node]
        if isinstance(node, dict):
            values = list(node.values())
            if _same_keys(values):
                return {KEYED: [[word(k) for k in values[0]]] + [[word(k)] + [enc(v) for v in x.values()] for k, x in node.items()]}
            return {word(k): enc(v) for k, v in node.items()}
        return node

    return {"v": VERSION, "s": table, "d": enc(data)}


def unpack(packed: dict[str, Any]) -> Any:
    table = packed["s"]

    def word(text: str) -> str:
        if not text.startswith(MARK):
            return text
        if text.startswith(MARK + MARK):
            return text[1:]
        return table[int(text[1:], 36)]

    def dec(node: Any) -> Any:
        if isinstance(node, str):
            return word(node)
        if isinstance(node, list):
            return [dec(x) for x in node]
        if isinstance(node, dict):
            if len(node) == 1:
                kind, body = next(iter(node.items()))
                if kind == RUN:
                    return [dec(body[0])] * body[1]
                if kind == JOINED:
                    return SEP.join(word(p) for p in body)
                if kind == ROWS:
                    keys = [word(k) for k in body[0]]
                    return [{k: dec(v) for k, v in zip(keys, row)} for row in body[1:]]
                if kind == KEYED:
                    keys = [word(k) for k in body[0]]
                    return {word(row[0]): {k: dec(v) for k, v in zip(keys, row[1:])} for row in body[1:]}
            return {word(k): dec(v) for k, v in node.items()}
        return node

    return dec(packed["d"])
