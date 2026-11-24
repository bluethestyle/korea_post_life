"""고해상도 정밀 벡터 인포그래픽 아이콘 및 복합 다이어그램 부품 모듈."""

from __future__ import annotations

import math
from typing import Any, Sequence
import numpy as np
from manim import *

from common import (
    C_BG_SUB,
    C_CORAL,
    C_CYAN,
    C_GOLD,
    C_GOLD_DEEP,
    C_INK_0,
    C_MINT,
    C_PANEL_HI,
    C_SLATE,
    C_WHITE,
    fit,
    pill,
    txt,
)


def _vpt(x: float, y: float) -> np.ndarray:
    """표준 24x24 뷰박스 좌표(좌상단 원점)를 중심 기준 Manim 평면 좌표로 변환한다."""
    return np.array([x - 12.0, 12.0 - y, 0.0])


# 인물 스틱 도형을 배제하고 산업 표준 인포그래픽 기호로 설계한 24x24 정밀 벡터 명세
# 각 도형 원소는 (kind, data, is_accent, fill_opacity) 튜플로 정의한다.
_ICON_SPECS: dict[str, list[tuple[str, Any, bool, float]]] = {
    # 창구, 지점 건물 파사드와 상담 데스크 카운터
    "branch_counter": [
        ("poly", [(3, 10), (12, 4), (21, 10)], True, 0.22),
        ("segs", [((2, 10), (22, 10))], False, 0.0),
        ("segs", [((5, 10), (5, 17)), ((9.5, 10), (9.5, 17)), ((14.5, 10), (14.5, 17)), ((19, 10), (19, 17))], False, 0.0),
        ("poly", [(2, 17), (22, 17), (22, 20.5), (2, 20.5)], False, 0.25),
        ("segs", [((10.5, 6.8), (13.5, 6.8)), ((12, 5.3), (12, 8.3))], True, 0.0),
    ],
    # 본부 분석 모니터와 차트
    "hq_console": [
        ("poly", [(3, 4), (21, 4), (21, 16), (3, 16)], False, 0.16),
        ("segs", [((8, 20), (16, 20)), ((12, 16), (12, 20))], False, 0.0),
        ("segs", [((7, 13), (7, 10)), ((11, 13), (11, 7.5)), ((15, 13), (15, 9)), ((18, 13), (18, 6.5))], True, 0.0),
    ],
    # 정밀 문서 (텍스트 행)
    "doc_text": [
        ("poly", [(6, 3), (15, 3), (19, 7), (19, 21), (6, 21)], False, 0.16),
        ("open", [(15, 3), (15, 7), (19, 7)], True, 0.0),
        ("segs", [((9, 11), (16, 11)), ((9, 14.5), (16, 14.5)), ((9, 18), (13.5, 18))], True, 0.0),
    ],
    # 이미지 스캔 요약서 (프레임과 픽셀 기호)
    "doc_image": [
        ("poly", [(5, 3), (15, 3), (19, 7), (19, 21), (5, 21)], False, 0.16),
        ("open", [(15, 3), (15, 7), (19, 7)], False, 0.0),
        ("poly", [(7.5, 18), (11, 13.5), (13.5, 16.2), (15.5, 14.2), (17, 18)], True, 0.28),
        ("circle", (10.0, 11.5, 1.3), True, 0.50),
    ],
    # 형식(PDF)과 쪽수 확인을 마친 문서
    "doc_check": [
        ("poly", [(5, 3), (15, 3), (19, 7), (19, 21), (5, 21)], False, 0.16),
        ("open", [(15, 3), (15, 7), (19, 7)], False, 0.0),
        ("open", [(8.8, 14.2), (11.2, 16.6), (15.8, 11.6)], True, 0.0),
    ],
    # 실린더 마스터 데이터베이스
    "database_master": [
        (
            "cubic",
            ((4, 6.5), [("C", 4, 4.6, 20, 4.6, 20, 6.5), ("C", 20, 8.4, 4, 8.4, 4, 6.5)], True),
            True,
            0.26,
        ),
        (
            "cubic",
            ((4, 6.5), [("L", 4, 17.5), ("C", 4, 19.4, 20, 19.4, 20, 17.5), ("L", 20, 6.5)], False),
            False,
            0.14,
        ),
        (
            "cubic",
            ((4, 12.0), [("C", 4, 13.9, 20, 13.9, 20, 12.0)], False),
            True,
            0.0,
        ),
    ],
    # 보안, 검증 방패
    "shield_check": [
        (
            "cubic",
            (
                (12, 3),
                [
                    ("L", 19.5, 6.2),
                    ("L", 19.5, 12.0),
                    ("C", 19.5, 16.8, 16.2, 19.8, 12.0, 21.4),
                    ("C", 7.8, 19.8, 4.5, 16.8, 4.5, 12.0),
                    ("L", 4.5, 6.2),
                ],
                True,
            ),
            False,
            0.18,
        ),
        ("open", [(8.8, 12.2), (11.1, 14.6), (15.6, 9.8)], True, 0.0),
    ],
    # 접속 차단, 방화벽 게이트
    "firewall_ban": [
        ("poly", [(3.5, 5), (20.5, 5), (20.5, 19), (3.5, 19)], False, 0.16),
        (
            "segs",
            [
                ((3.5, 9.6), (20.5, 9.6)),
                ((3.5, 14.3), (20.5, 14.3)),
                ((9.5, 5), (9.5, 9.6)),
                ((15.5, 9.6), (15.5, 14.3)),
                ((9.5, 14.3), (9.5, 19)),
            ],
            False,
            0.0,
        ),
        ("segs", [((9.2, 9.2), (14.8, 14.8)), ((14.8, 9.2), (9.2, 14.8))], True, 0.0),
    ],
    # 기관 공시, 시장 동향 탐색 글로브 레이더
    "search_globe": [
        ("circle", (11.0, 11.0, 7.0), False, 0.14),
        ("segs", [((4, 11), (18, 11))], False, 0.0),
        (
            "cubic",
            ((11, 4), [("C", 13.4, 6.2, 13.4, 15.8, 11, 18), ("C", 8.6, 15.8, 8.6, 6.2, 11, 4)], True),
            False,
            0.0,
        ),
        ("segs", [((16.2, 16.2), (20.5, 20.5))], True, 0.0),
    ],
    # 기간, 보관 기한, 슬라이딩 윈도우 시계
    "calendar_clock": [
        ("poly", [(4, 5.5), (18, 5.5), (18, 18.5), (4, 18.5)], False, 0.14),
        ("segs", [((4, 9.5), (18, 9.5)), ((8, 3.5), (8, 6.5)), ((14, 3.5), (14, 6.5))], False, 0.0),
        ("circle", (16.5, 17.2, 4.2), True, 0.24),
        ("open", [(16.5, 15.2), (16.5, 17.2), (18.1, 18.1)], True, 0.0),
    ],
    # 코드 수치 연산 모듈
    "code_calc": [
        ("poly", [(3.5, 4.5), (20.5, 4.5), (20.5, 19.5), (3.5, 19.5)], False, 0.16),
        ("open", [(8.8, 9.2), (5.8, 12.0), (8.8, 14.8)], True, 0.0),
        ("open", [(15.2, 9.2), (18.2, 12.0), (15.2, 14.8)], True, 0.0),
        ("segs", [((13.2, 8.5), (10.8, 15.5))], False, 0.0),
    ],
    # 비생성 판정 NPU 프로세서 칩
    "cpu_decide": [
        ("poly", [(6.5, 6.5), (17.5, 6.5), (17.5, 17.5), (6.5, 17.5)], False, 0.20),
        ("poly", [(9.5, 9.5), (14.5, 9.5), (14.5, 14.5), (9.5, 14.5)], True, 0.34),
        (
            "segs",
            [
                ((9, 3.5), (9, 6.5)),
                ((12, 3.5), (12, 6.5)),
                ((15, 3.5), (15, 6.5)),
                ((9, 17.5), (9, 20.5)),
                ((12, 17.5), (12, 20.5)),
                ((15, 17.5), (15, 20.5)),
                ((3.5, 9), (6.5, 9)),
                ((3.5, 12), (6.5, 12)),
                ((3.5, 15), (6.5, 15)),
                ((17.5, 9), (20.5, 9)),
                ((17.5, 12), (20.5, 12)),
                ((17.5, 15), (20.5, 15)),
            ],
            False,
            0.0,
        ),
    ],
    # 서브에이전트 워커 노드
    "agent_bot": [
        ("poly", [(5, 7.5), (19, 7.5), (19, 18.5), (5, 18.5)], False, 0.18),
        ("segs", [((12, 4), (12, 7.5)), ((10, 4), (14, 4))], True, 0.0),
        ("circle", (9.0, 12.2, 1.1), True, 0.65),
        ("circle", (15.0, 12.2, 1.1), True, 0.65),
        ("segs", [((9, 15.6), (15, 15.6))], False, 0.0),
    ],
    # 특약 계보, 분리 통합 분기
    "git_lineage": [
        ("circle", (6.0, 7.5, 2.0), True, 0.45),
        ("circle", (6.0, 18.5, 2.0), True, 0.45),
        ("circle", (18.0, 12.0, 2.0), True, 0.45),
        ("segs", [((6, 9.5), (6, 16.5))], False, 0.0),
        ("cubic", ((6, 9.5), [("C", 6, 12, 11, 12, 16, 12)], False), False, 0.0),
    ],
    # 표준담보 사전 북
    "book_dict": [
        (
            "cubic",
            (
                (4, 5),
                [
                    ("C", 4, 4, 8.5, 4, 12, 5.5),
                    ("C", 15.5, 4, 20, 4, 20, 5),
                    ("L", 20, 18.5),
                    ("C", 20, 17.5, 15.5, 17.5, 12, 19),
                    ("C", 8.5, 17.5, 4, 17.5, 4, 18.5),
                ],
                True,
            ),
            False,
            0.16,
        ),
        ("segs", [((12, 5.5), (12, 19))], True, 0.0),
        (
            "segs",
            [
                ((6.8, 9.2), (9.8, 9.2)),
                ((6.8, 12.5), (9.8, 12.5)),
                ((14.2, 9.2), (17.2, 9.2)),
                ((14.2, 12.5), (17.2, 12.5)),
            ],
            True,
            0.0,
        ),
    ],
    # 경고, 유의 삼각 배지
    "alert_warn": [
        ("poly", [(12, 4), (21, 19.5), (3, 19.5)], False, 0.20),
        ("segs", [((12, 9.5), (12, 14.2))], True, 0.0),
        ("circle", (12.0, 16.8, 0.55), True, 0.90),
    ],
    # A4 응대 화법 브리프 장표
    "brief_sheet": [
        ("poly", [(5.5, 3), (15.5, 3), (19, 6.5), (19, 21), (5.5, 21)], False, 0.18),
        ("segs", [((5.5, 5.2), (17.5, 5.2))], True, 0.0),
        ("segs", [((8.2, 9.5), (16.2, 9.5)), ((8.2, 13), (16.2, 13)), ((8.2, 16.5), (13.8, 16.5))], True, 0.0),
    ],
}


def _build_primitive(kind: str, data: Any, color: str, sw: float, fill_op: float) -> Mobject:
    if kind == "poly":
        m: Mobject = Polygon(*[_vpt(x, y) for x, y in data])
        m.set_stroke(color=color, width=sw).set_fill(color=color, opacity=fill_op)
        return m
    if kind == "open":
        vm = VMobject()
        vm.set_points_as_corners([_vpt(x, y) for x, y in data])
        vm.set_stroke(color=color, width=sw).set_fill(opacity=0.0)
        return vm
    if kind == "segs":
        return VGroup(*[Line(_vpt(*p0), _vpt(*p1), color=color, stroke_width=sw) for p0, p1 in data])
    if kind == "circle":
        cx, cy, rad = data
        c = Circle(radius=rad)
        c.move_to(_vpt(cx, cy)).set_stroke(color=color, width=sw).set_fill(color=color, opacity=fill_op)
        return c
    if kind == "cubic":
        start_xy, steps, is_closed = data
        vm = VMobject()
        vm.start_new_path(_vpt(*start_xy))
        for st in steps:
            if st[0] == "L":
                vm.add_line_to(_vpt(st[1], st[2]))
            elif st[0] == "C":
                vm.add_cubic_bezier_curve_to(_vpt(st[1], st[2]), _vpt(st[3], st[4]), _vpt(st[5], st[6]))
        if is_closed:
            vm.close_path()
        vm.set_stroke(color=color, width=sw).set_fill(color=color, opacity=fill_op)
        return vm
    raise ValueError(kind)


def svg_icon(
    name: str,
    size: float = 0.56,
    col: str = C_CYAN,
    accent: str | None = None,
    tile: bool = True,
    bg: str = C_BG_SUB,
    sw: float = 2.2,
    z: int = 8,
) -> VGroup:
    """표준 24x24 정밀 벡터 명세를 Manim 좌표계로 변환한 인포그래픽 아이콘."""
    acc = accent or col
    spec = _ICON_SPECS[name]

    ref_box = Rectangle(width=24.0, height=24.0).set_fill(opacity=0.0).set_stroke(opacity=0.0)
    paths_grp = VGroup(ref_box)
    for kind, data, is_acc, f_op in spec:
        c_use = acc if is_acc else col
        paths_grp.add(_build_primitive(kind, data, c_use, sw, f_op))

    inner_scale = (size * 0.68 if tile else size) / 24.0
    paths_grp.move_to(ORIGIN).scale(inner_scale).set_z_index(z + 1)
    paths_grp.remove(ref_box)

    if not tile:
        return paths_grp

    plate = RoundedRectangle(
        corner_radius=size * 0.22,
        width=size,
        height=size,
        fill_color=bg,
        fill_opacity=0.96,
        stroke_color=col,
        stroke_width=1.7,
    ).set_z_index(z)
    rim = RoundedRectangle(
        corner_radius=size * 0.22,
        width=size * 0.88,
        height=size * 0.88,
        fill_opacity=0.0,
        stroke_color=WHITE,
        stroke_width=0.7,
        stroke_opacity=0.18,
    ).set_z_index(z)
    return VGroup(plate, rim, paths_grp)


def make_claude_orchestrator_hub(
    center: Sequence[float] | np.ndarray,
    radius: float = 0.96,
    title_s: str = "총괄 지휘: Claude",
    sub_s: str = "",
    z: int = 8,
) -> tuple[VGroup, VMobject]:
    """3장 분업 컨트롤 플레인의 중앙 AI 오케스트레이터 허브 (정밀 대칭 회로 노드)."""
    pt = np.array(center, dtype=float)
    outer_orbit = DashedVMobject(
        Circle(radius=radius * 1.18, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.0, stroke_opacity=0.78).move_to(pt),
        num_dashes=32,
    ).set_z_index(z)
    halo = Circle(
        radius=radius * 1.06,
        fill_color="#1A160B",
        fill_opacity=0.55,
        stroke_color=C_CYAN,
        stroke_width=1.4,
        stroke_opacity=0.55,
    ).move_to(pt).set_z_index(z)
    core = Circle(
        radius=radius * 0.92,
        fill_color=C_PANEL_HI,
        fill_opacity=0.98,
        stroke_color=C_GOLD,
        stroke_width=2.8,
    ).move_to(pt).set_z_index(z + 1)
    inner_ring = Circle(
        radius=radius * 0.78,
        fill_opacity=0.0,
        stroke_color=WHITE,
        stroke_width=0.9,
        stroke_opacity=0.28,
    ).move_to(pt).set_z_index(z + 2)

    ports = VGroup()
    for k in range(8):
        ang = k * (math.pi / 4)
        p0 = pt + np.array([math.cos(ang) * radius * 0.92, math.sin(ang) * radius * 0.92, 0.0])
        p1 = pt + np.array([math.cos(ang) * radius * 1.06, math.sin(ang) * radius * 1.06, 0.0])
        p_col = C_GOLD if k % 2 == 0 else C_CYAN
        ports.add(
            Line(p0, p1, color=p_col, stroke_width=2.0).set_z_index(z + 2),
            Dot(p1, radius=0.036, color=p_col).set_z_index(z + 3),
        )

    ic = svg_icon("cpu_decide", size=radius * 0.56, col=C_GOLD, accent=C_CYAN, tile=False, sw=2.3, z=z + 3).move_to(
        pt + UP * (radius * 0.30 if sub_s else radius * 0.18)
    )
    lbl_items: list[Mobject] = [txt(title_s, size=11.6, color=C_GOLD, bold=True, z=z + 4)]
    if sub_s:
        lbl_items.append(txt(sub_s, size=10.8, color=C_WHITE, bold=True, z=z + 4))
    lbl_grp = fit(VGroup(*lbl_items).arrange(DOWN, buff=0.04), max_w=radius * 1.56).move_to(
        pt + DOWN * (radius * 0.34 if sub_s else radius * 0.30)
    )

    body = VGroup(halo, core, inner_ring, ports, ic, lbl_grp)
    return body, outer_orbit


def make_dark_a4_sheet(
    center: Sequence[float] | np.ndarray,
    w: float,
    h: float,
    badge_s: str,
    title_s: str,
    rows: list[tuple[str, str]],
    foot_s: str,
    z: int = 5,
) -> VGroup:
    """전체 다크 테마와 조화를 이루는 세련된 다크 슬레이트, 골드 A4 응대 화법 장표 인포그래픽."""
    pt = np.array(center, dtype=float)
    x0, y0 = pt[0], pt[1]
    fold = min(w, h) * 0.11
    left, right = x0 - w / 2, x0 + w / 2
    bot, top = y0 - h / 2, y0 + h / 2

    shadow = Polygon(
        [left + 0.07, bot - 0.07, 0],
        [right + 0.07, bot - 0.07, 0],
        [right + 0.07, top - fold - 0.07, 0],
        [right - fold + 0.07, top - 0.07, 0],
        [left + 0.07, top - 0.07, 0],
        fill_color="#03060A",
        fill_opacity=0.85,
        stroke_width=0,
    ).set_z_index(z - 1)

    sheet = Polygon(
        [left, bot, 0],
        [right, bot, 0],
        [right, top - fold, 0],
        [right - fold, top, 0],
        [left, top, 0],
        fill_color="#141F2C",
        fill_opacity=0.98,
        stroke_color=C_GOLD,
        stroke_width=2.3,
    ).set_z_index(z)

    dog_ear = Polygon(
        [right - fold, top, 0],
        [right - fold, top - fold, 0],
        [right, top - fold, 0],
        fill_color="#243447",
        fill_opacity=1.0,
        stroke_color=C_GOLD,
        stroke_width=1.6,
    ).set_z_index(z + 2)

    top_accent = Line([left + 0.02, top - 0.02, 0], [right - fold, top - 0.02, 0], color=C_CORAL, stroke_width=4.6).set_z_index(z + 2)
    bdg = fit(pill(badge_s, fg=C_WHITE, bg=C_CORAL, border=C_CORAL, size=11.0, px=0.10, py=0.035, z=z + 3), max_w=w - 0.32).move_to(
        [x0 - fold * 0.18, top - 0.36, 0]
    )
    hdr = fit(txt(title_s, size=13.8, color=C_GOLD, bold=True, z=z + 3), max_w=w - 0.28).move_to([x0, top - 0.80, 0])
    hdr_rule = Line([left + 0.18, top - 1.04, 0], [right - 0.18, top - 1.04, 0], color=C_GOLD_DEEP, stroke_width=1.3).set_z_index(z + 2)

    foot_h = 0.44
    foot_bg = Rectangle(
        width=w - 0.04,
        height=foot_h,
        fill_color="#0C131C",
        fill_opacity=1.0,
        stroke_color=C_GOLD_DEEP,
        stroke_width=1.0,
    ).move_to([x0, bot + foot_h / 2 + 0.02, 0]).set_z_index(z + 1)
    foot_t = fit(txt(foot_s, size=10.8, color=C_MINT, bold=True, z=z + 3), max_w=w - 0.24).move_to(foot_bg)

    avail_top = top - 1.16
    avail_bot = bot + foot_h + 0.14
    n_r = max(len(rows), 1)
    slot_step = (avail_top - avail_bot) / n_r
    row_h = min(0.48, slot_step * 0.82)

    row_mobs = VGroup()
    for idx, (r_col, r_txt) in enumerate(rows):
        ry = avail_top - (idx + 0.5) * slot_step
        r_box = RoundedRectangle(
            corner_radius=0.04,
            width=w - 0.30,
            height=row_h,
            fill_color="#1C2A3A",
            fill_opacity=0.96,
            stroke_color=C_SLATE,
            stroke_width=1.1,
        ).move_to([x0, ry, 0]).set_z_index(z + 1)
        r_bar = Rectangle(
            width=0.09,
            height=row_h,
            fill_color=r_col,
            fill_opacity=1.0,
            stroke_width=0,
        ).move_to(r_box.get_left() + RIGHT * 0.045).set_z_index(z + 2)
        r_lbl = fit(txt(r_txt, size=10.8, color=C_INK_0, bold=True, z=z + 3), max_w=w - 0.56).move_to(
            r_box.get_center() + RIGHT * 0.04
        )
        row_mobs.add(VGroup(r_box, r_bar, r_lbl))

    return VGroup(shadow, sheet, dog_ear, top_accent, bdg, hdr, hdr_rule, row_mobs, foot_bg, foot_t)
