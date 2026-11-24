from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Sequence
import cairo
import numpy as np
from manim import *

_FACTS = json.loads(Path(__file__).with_name("facts.json").read_bytes())["facts"]


def fact(key: str, *path):
    """facts.json 의 값. 열쇠가 없으면 KeyError 로 멈춘다(기본값을 두지 않는다)."""
    value = _FACTS[key]["value"]
    for p in path:
        value = value[p]
    return value


def num(n) -> str:
    """천 단위 쉼표. 1274 -> "1,274"."""
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Clinical Insurance & IT Terminology Constants (실무 용어 상수 및 표시 매핑)
# ---------------------------------------------------------------------------
TERM: dict[str, str] = {
    "master": "마스터 데이터",
    "sheet_master": "구글 시트 마스터 데이터",
    "snapshot": "스냅샷",
    "snapshot_first": "스냅샷(특정 시점의 데이터 복사본)",
    "uw": "인수기준",
    "uw_first": "인수기준(가입 심사 기준)",
    "uw_cmp": "인수기준 비교",
    "uw_only": "인수기준만 수집",
    "open": "가입 가능",
    "closed": "가입 제한",
    "ours_only": "우체국 간편만 가입 가능",
    "open_both": "함께 가입 가능",
    "ours_closed": "우체국 간편심사 가입 제한",
    "ours_closed_short": "우체국 간편 가입 제한",
    "all_closed": "간편 모두 가입 제한",
    "ours": "우체국",
    "peer": "타사",
    "extract": "추출",
    "extract_init": "초기 추출",
    "extract_dual": "이중 추출",
    "cross_verify": "교차 검증",
    "ocr": "문자 인식(OCR)",
    "extractor": "추출 모델",
    "test": "테스트",
    "mock_test": "모의 시트 테스트",
    "batch_query": "일괄 질의",
    "unit_first": "특약 단위(추출 단위)",
    "unit": "특약 단위",
    "verdict": "우열 판정",
    "verdict_hold": "판정 보류",
    "unheld_cov": "미보유 담보",
    "review_wait": "검수 대기",
    "map_wait": "매핑 검수 대기",
    "trend": "시장 동향",
    "rider_cond": "특약 부가 조건",
    "disc_item": "고지항목",
    "disc_range": "고지 범위",
    "base_cond": "기본 조건",
    "seg_status": "고객군별 가입 가능 현황",
    "script_doc": "응대 화법",
    "main_limit": "주계약 가입한도",
    "rider_limit": "특약 가입한도",
    "rel_cov": "관련 담보",
    "ins_uw": "인수기준 차이",
    "ins_strength": "우위 담보",
    "ins_defense": "열위 담보",
    "ins_revise": "미보유 담보",
    "use_news_filter": "시장 동향 선별",
    "use_news_merge": "중복 동향 병합",
}

_FACT_DISPLAY_MAP: dict[str, str] = {
    fact("segment_map_labels", 0): TERM["ours_only"],
    fact("segment_map_labels", 1): TERM["open_both"],
    fact("segment_map_labels", 2): TERM["ours_closed_short"],
    fact("segment_map_labels", 3): TERM["all_closed"],
    fact("sales_insight_categories", 0): TERM["ins_uw"],
    fact("sales_insight_categories", 1): TERM["ins_strength"],
    fact("sales_insight_categories", 2): TERM["rel_cov"],
    fact("sales_insight_categories", 3): TERM["ins_defense"],
    fact("sales_insight_categories", 4): TERM["ins_revise"],
    fact("decision_model_uses", 2): TERM["use_news_filter"],
    fact("decision_model_uses", 3): TERM["use_news_merge"],
    fact("unpinned_agent_incident"): "모델 미지정 구현 에이전트의 최상위 모델 실행",
    fact("not_yet_measured", 2): "신상품 비교표 작성 시간 단축 폭",
}


def label_ko(raw: str) -> str:
    """자료 파일의 내부 라벨을 화면용 보험과 IT 실무 표기로 변환한다."""
    if raw in _FACT_DISPLAY_MAP:
        return _FACT_DISPLAY_MAP[raw]
    return raw.replace("수술만", "통원수술").replace("넘음이나 없음", "초과 또는 없음")


# ---------------------------------------------------------------------------
# Color Palette
# ---------------------------------------------------------------------------
C_BG = "#070B10"
C_BG_SUB = "#101720"
C_GRID = "#1B2634"

C_CYAN = "#58C4DD"
C_CYAN_DIM = "#1A4350"
C_GOLD = "#E2C878"
C_GOLD_DEEP = "#8F7B3E"
C_AMBER = "#F59E0B"
C_AMBER_DIM = "#3D2B0D"
C_CORAL = "#FF5C5C"
C_CORAL_DIM = "#4D1F24"
C_VIOLET = "#A78BFA"
C_VIOLET_DIM = "#261E42"
C_MINT = "#6EE7B7"
C_MINT_DIM = "#16382C"

C_INK_0 = "#F2F5F8"
C_INK_1 = "#C2CBD4"
C_INK_2 = "#7F8C99"
C_WHITE = "#FFFFFF"
C_PANEL = "#111922"
C_PANEL_HI = "#192431"
C_SLATE = "#334150"
C_IVORY = "#F4F3EE"
C_DARK_INK = "#141B22"

FONT_KO = "Noto Sans KR"
TOTAL_CHAPTERS = 9


# ---------------------------------------------------------------------------
# Core Visual Primitives
# ---------------------------------------------------------------------------
def txt(
    s: str,
    size: float = 18,
    color: str = C_INK_0,
    bold: bool = False,
    z: int = 6,
) -> Text:
    t = Text(s, font=FONT_KO, font_size=size, color=color, weight=BOLD if bold else NORMAL)
    t.set_z_index(z)
    return t


def fit(m: Mobject, max_w: float | None = None, max_h: float | None = None) -> Mobject:
    if max_w is not None and m.width > max_w and m.width > 1e-6:
        m.scale(max_w / m.width)
    if max_h is not None and m.height > max_h and m.height > 1e-6:
        m.scale(max_h / m.height)
    return m


def pill(
    label: str,
    fg: str = C_INK_0,
    bg: str = C_PANEL_HI,
    border: str = C_SLATE,
    size: float = 15,
    bold: bool = True,
    px: float = 0.18,
    py: float = 0.09,
    z: int = 6,
) -> VGroup:
    t = txt(label, size=size, color=fg, bold=bold, z=z + 1)
    b = RoundedRectangle(
        corner_radius=0.09,
        width=t.width + px * 2,
        height=t.height + py * 2,
        fill_color=bg,
        fill_opacity=0.97,
        stroke_color=border,
        stroke_width=1.6,
    ).set_z_index(z)
    t.move_to(b.get_center())
    g = VGroup(b, t)
    g.set_z_index(z, family=False)
    return g


def bb_badge(
    label: str,
    sub: str | None = None,
    fg: str = C_WHITE,
    bg: str = "#060B11",
    border: str = C_GOLD,
    size: float = 13.5,
    sub_size: float = 11.2,
    sub_col: str = C_INK_1,
    px: float = 0.20,
    py: float = 0.11,
    z: int = 18,
) -> VGroup:
    """삼차원 공간 위에서도 선명하게 읽히는 고대비 정면 빌보드 배지."""
    t1 = txt(label, size=size, color=fg, bold=True, z=z + 2)
    if sub is not None:
        t2 = txt(sub, size=sub_size, color=sub_col, bold=True, z=z + 2)
        t_grp: Mobject = VGroup(t1, t2).arrange(DOWN, buff=0.05)
    else:
        t_grp = t1
    rim = RoundedRectangle(
        corner_radius=0.11,
        width=t_grp.width + px * 2 + 0.06,
        height=t_grp.height + py * 2 + 0.06,
        fill_color="#020407",
        fill_opacity=0.88,
        stroke_width=0,
    ).set_z_index(z)
    box = RoundedRectangle(
        corner_radius=0.09,
        width=t_grp.width + px * 2,
        height=t_grp.height + py * 2,
        fill_color=bg,
        fill_opacity=0.98,
        stroke_color=border,
        stroke_width=2.2,
    ).set_z_index(z + 1)
    t_grp.move_to(box.get_center())
    rim.move_to(box.get_center())
    g = VGroup(rim, box, t_grp)
    g.set_z_index(z, family=False)
    return g


def arrow_2d(
    p0: np.ndarray | list[float],
    p1: np.ndarray | list[float],
    color: str = C_INK_1,
    sw: float = 2.2,
    tip: float = 0.14,
    z: int = 5,
) -> Arrow:
    a = Arrow(
        np.array(p0, dtype=float),
        np.array(p1, dtype=float),
        buff=0.0,
        color=color,
        stroke_width=sw,
        max_tip_length_to_length_ratio=0.38,
        tip_length=tip,
    )
    a.set_z_index(z)
    return a


def glow_dot(pos: np.ndarray | list[float], color: str = C_GOLD, r: float = 0.065, z: int = 12) -> VGroup:
    p = np.array(pos, dtype=float)
    halo = Circle(
        radius=r * 2.1,
        fill_color=color,
        fill_opacity=0.28,
        stroke_color=color,
        stroke_width=1.0,
        stroke_opacity=0.55,
    ).move_to(p)
    core = Dot(p, radius=r, color=WHITE if color != C_CORAL else "#FFD6D6")
    ring = Circle(radius=r * 1.15, stroke_color=color, stroke_width=2.0, fill_opacity=0.0).move_to(p)
    g = VGroup(halo, ring, core)
    g.set_z_index(z)
    return g


def cross_mark(pos: np.ndarray | list[float], size: float = 0.13, color: str = C_CORAL, sw: float = 2.8, z: int = 10) -> VGroup:
    p = np.array(pos, dtype=float)
    l1 = Line(p + np.array([-size, -size, 0]), p + np.array([size, size, 0]), color=color, stroke_width=sw)
    l2 = Line(p + np.array([-size, size, 0]), p + np.array([size, -size, 0]), color=color, stroke_width=sw)
    g = VGroup(l1, l2)
    g.set_z_index(z)
    return g


def capacity_ring(
    pos: np.ndarray | list[float],
    radius: float,
    col: str,
    top_txt: str,
    sub_txt: str,
    ratio: float | None = None,
    z: int = 7,
) -> VGroup:
    """한도 배지. 두 사실 값으로 계산한 양수 비율이 있을 때만 호를 그린다."""
    p = np.array(pos, dtype=float)
    bg_ring = (
        Circle(
            radius=radius,
            fill_color=C_BG_SUB,
            fill_opacity=0.92,
            stroke_color=col if ratio is None else C_SLATE,
            stroke_width=2.4 if ratio is None else 3.2,
        )
        .move_to(p)
        .set_z_index(z)
    )
    t1 = txt(top_txt, size=12.4, color=col, bold=True, z=z + 2)
    t2 = txt(sub_txt, size=10.8, color=C_INK_0, bold=True, z=z + 2)
    tg = fit(VGroup(t1, t2).arrange(DOWN, buff=0.05), max_w=radius * 1.74).move_to(p)
    if ratio is not None and ratio > 0.0:
        arc = Arc(
            radius=radius,
            start_angle=math.pi / 2,
            angle=-2 * math.pi * min(ratio, 1.0),
            arc_center=p,
            color=col,
            stroke_width=4.2,
        ).set_z_index(z + 1)
        return VGroup(bg_ring, arc, tg)
    return VGroup(bg_ring, tg)


# ---------------------------------------------------------------------------
# Bespoke Infographic Vector Components (고품격 절차형 벡터 부품)
# ---------------------------------------------------------------------------
def make_doc_icon(
    w: float = 0.40,
    h: float = 0.52,
    col: str = C_CYAN,
    fill: str = C_PANEL_HI,
    is_image: bool = False,
    badge_txt: str | None = None,
    z: int = 6,
) -> VGroup:
    """접힌 귀퉁이와 내부 문서 줄(또는 그림 기호)을 갖춘 문서 아이콘."""
    hw, hh = w / 2, h / 2
    fold = min(w, h) * 0.28
    page = Polygon(
        [-hw, -hh, 0],
        [hw, -hh, 0],
        [hw, hh - fold, 0],
        [hw - fold, hh, 0],
        [-hw, hh, 0],
        fill_color=fill,
        fill_opacity=0.97,
        stroke_color=col,
        stroke_width=1.8,
    ).set_z_index(z)
    flap = Polygon(
        [hw - fold, hh, 0],
        [hw - fold, hh - fold, 0],
        [hw, hh - fold, 0],
        fill_color=col,
        fill_opacity=0.35,
        stroke_color=col,
        stroke_width=1.4,
    ).set_z_index(z + 1)
    parts: list[Mobject] = [page, flap]
    if is_image:
        frame = RoundedRectangle(
            corner_radius=0.02,
            width=w * 0.72,
            height=h * 0.48,
            fill_color="#1A1024",
            fill_opacity=0.90,
            stroke_color=col,
            stroke_width=1.1,
        ).move_to([0, -h * 0.08, 0]).set_z_index(z + 1)
        mtn = Polygon(
            [-w * 0.28, -h * 0.28, 0],
            [-w * 0.06, -h * 0.02, 0],
            [w * 0.08, -h * 0.18, 0],
            [w * 0.18, -h * 0.06, 0],
            [w * 0.28, -h * 0.28, 0],
            fill_color=col,
            fill_opacity=0.55,
            stroke_color=col,
            stroke_width=1.1,
        ).set_z_index(z + 2)
        sun = Circle(radius=w * 0.075, fill_color=C_GOLD, fill_opacity=0.95, stroke_width=0).move_to([w * 0.14, h * 0.05, 0]).set_z_index(z + 2)
        parts.extend([frame, mtn, sun])
    else:
        hdr_bar = Line([-hw * 0.68, hh * 0.42, 0], [hw * 0.20, hh * 0.42, 0], color=col, stroke_width=2.2).set_z_index(z + 1)
        l1 = Line([-hw * 0.68, hh * 0.08, 0], [hw * 0.62, hh * 0.08, 0], color=C_INK_1, stroke_width=1.4, stroke_opacity=0.80).set_z_index(z + 1)
        l2 = Line([-hw * 0.68, -hh * 0.20, 0], [hw * 0.62, -hh * 0.20, 0], color=C_INK_1, stroke_width=1.4, stroke_opacity=0.75).set_z_index(z + 1)
        l3 = Line([-hw * 0.68, -hh * 0.48, 0], [hw * 0.34, -hh * 0.48, 0], color=C_INK_2, stroke_width=1.4, stroke_opacity=0.70).set_z_index(z + 1)
        parts.extend([hdr_bar, l1, l2, l3])
    if badge_txt is not None:
        rib = RoundedRectangle(
            corner_radius=0.03,
            width=w * 0.86,
            height=h * 0.30,
            fill_color=col,
            fill_opacity=0.95,
            stroke_color=WHITE,
            stroke_width=1.0,
        ).move_to([0, -hh * 0.32, 0]).set_z_index(z + 2)
        rt = fit(txt(badge_txt, size=8.6, color=C_DARK_INK if col in (C_GOLD, C_MINT, C_CYAN) else WHITE, bold=True, z=z + 3), max_w=w * 0.78).move_to(rib)
        parts.extend([rib, rt])
    g = VGroup(*parts)
    g.set_z_index(z)
    return g


def make_refinery_funnel(
    cx: float,
    top_y: float,
    bot_y: float,
    top_w: float = 2.16,
    neck_w: float = 0.56,
    col: str = C_CYAN,
    accent: str = C_GOLD,
    label_mob: Mobject | None = None,
    z: int = 5,
) -> VGroup:
    """입체 타원 입구와 곡선 투명 벽면, 다단 거름망, 노즐 칼라를 갖춘 정련 퍼널."""
    h_tot = top_y - bot_y
    spout_y = bot_y + h_tot * 0.26
    tl = np.array([cx - top_w / 2, top_y, 0.0])
    tr = np.array([cx + top_w / 2, top_y, 0.0])
    nl = np.array([cx - neck_w / 2, spout_y, 0.0])
    nr = np.array([cx + neck_w / 2, spout_y, 0.0])
    bl = np.array([cx - neck_w * 0.42, bot_y, 0.0])
    br = np.array([cx + neck_w * 0.42, bot_y, 0.0])

    body = VMobject(fill_color="#0E2230", fill_opacity=0.95, stroke_color=col, stroke_width=2.3).set_z_index(z)
    body.start_new_path(tl)
    body.add_cubic_bezier_curve_to(
        tl + DOWN * (h_tot * 0.30),
        nl + UP * (h_tot * 0.24) + LEFT * 0.06,
        nl,
    )
    body.add_line_to(bl)
    body.add_line_to(br)
    body.add_line_to(nr)
    body.add_cubic_bezier_curve_to(
        nr + UP * (h_tot * 0.24) + RIGHT * 0.06,
        tr + DOWN * (h_tot * 0.30),
        tr,
    )
    body.close_path()

    mouth_outer = Ellipse(
        width=top_w,
        height=top_w * 0.16,
        fill_color="#08131C",
        fill_opacity=0.98,
        stroke_color=col,
        stroke_width=2.2,
    ).move_to([cx, top_y, 0]).set_z_index(z + 2)
    mouth_inner = Ellipse(
        width=top_w * 0.84,
        height=top_w * 0.095,
        fill_opacity=0.0,
        stroke_color=accent,
        stroke_width=1.2,
        stroke_opacity=0.75,
    ).move_to([cx, top_y, 0]).set_z_index(z + 3)

    y_r1 = top_y - h_tot * 0.33
    w_r1 = top_w * 0.68
    sieve_1 = DashedLine([cx - w_r1 / 2, y_r1, 0], [cx + w_r1 / 2, y_r1, 0], dash_length=0.06, color=col, stroke_width=1.5, stroke_opacity=0.65).set_z_index(z + 1)

    y_r2 = top_y - h_tot * 0.58
    w_r2 = top_w * 0.42
    sieve_2 = DashedLine([cx - w_r2 / 2, y_r2, 0], [cx + w_r2 / 2, y_r2, 0], dash_length=0.05, color=C_MINT, stroke_width=1.6, stroke_opacity=0.75).set_z_index(z + 1)

    collar = RoundedRectangle(
        corner_radius=0.04,
        width=neck_w * 1.24,
        height=0.11,
        fill_color=C_PANEL_HI,
        fill_opacity=0.98,
        stroke_color=accent,
        stroke_width=1.8,
    ).move_to([cx, spout_y, 0]).set_z_index(z + 2)

    nozzle_tip = Ellipse(
        width=neck_w * 0.84,
        height=0.10,
        fill_color=C_MINT,
        fill_opacity=0.85,
        stroke_color=WHITE,
        stroke_width=1.2,
    ).move_to([cx, bot_y, 0]).set_z_index(z + 2)

    sheen = VMobject(fill_opacity=0.0, stroke_color=WHITE, stroke_width=1.8, stroke_opacity=0.38).set_z_index(z + 2)
    sheen.start_new_path(tl + RIGHT * (top_w * 0.11) + DOWN * 0.10)
    sheen.add_cubic_bezier_curve_to(
        tl + RIGHT * (top_w * 0.13) + DOWN * (h_tot * 0.30),
        nl + RIGHT * 0.08 + UP * (h_tot * 0.20),
        nl + RIGHT * 0.08 + UP * 0.06,
    )

    grp = VGroup(body, sieve_1, sieve_2, sheen, collar, nozzle_tip, mouth_outer, mouth_inner)
    if label_mob is not None:
        label_mob.move_to([cx, top_y - h_tot * 0.42, 0]).set_z_index(z + 4)
        grp.add(label_mob)
    return grp


def make_counselor_desk(pos: np.ndarray | list[float], col: str = C_INK_0, accent: str = C_AMBER, z: int = 6) -> VGroup:
    """창구 상담사와 단말기, 카운터 데스크 일러스트."""
    p = np.array(pos, dtype=float)
    head = Circle(radius=0.18, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=col, stroke_width=2.1).move_to(p + UP * 0.34).set_z_index(z + 1)
    shoulders = VMobject(fill_color="#1B2634", fill_opacity=0.98, stroke_color=col, stroke_width=2.0).set_z_index(z)
    shoulders.start_new_path(p + np.array([-0.34, -0.18, 0]))
    shoulders.add_cubic_bezier_curve_to(
        p + np.array([-0.34, 0.12, 0]),
        p + np.array([0.34, 0.12, 0]),
        p + np.array([0.34, -0.18, 0]),
    )
    shoulders.close_path()
    collar_v = VGroup(
        Line(p + np.array([-0.08, 0.08, 0]), p + np.array([0.0, -0.06, 0]), color=accent, stroke_width=1.8),
        Line(p + np.array([0.08, 0.08, 0]), p + np.array([0.0, -0.06, 0]), color=accent, stroke_width=1.8),
    ).set_z_index(z + 1)
    monitor = RoundedRectangle(
        corner_radius=0.03,
        width=0.34,
        height=0.24,
        fill_color=C_BG_SUB,
        fill_opacity=1.0,
        stroke_color=C_CYAN,
        stroke_width=1.6,
    ).move_to(p + np.array([0.34, -0.04, 0])).set_z_index(z + 2)
    stand = Line(p + np.array([0.34, -0.16, 0]), p + np.array([0.34, -0.22, 0]), color=C_SLATE, stroke_width=2.2).set_z_index(z + 1)
    desk = Line(p + np.array([-0.46, -0.22, 0]), p + np.array([0.56, -0.22, 0]), color=accent, stroke_width=2.6).set_z_index(z + 2)
    return VGroup(shoulders, collar_v, head, stand, monitor, desk)


def make_speech_callout(
    pos: np.ndarray | list[float],
    w: float,
    h: float,
    text_mob: Mobject,
    col: str = C_CORAL,
    bg: str = C_CORAL_DIM,
    z: int = 7,
) -> VGroup:
    """말풍선 꼬리가 달린 현장 질문 콜아웃."""
    p = np.array(pos, dtype=float)
    bub = RoundedRectangle(
        corner_radius=0.10,
        width=w,
        height=h,
        fill_color=bg,
        fill_opacity=0.97,
        stroke_color=col,
        stroke_width=2.1,
    ).move_to(p).set_z_index(z)
    tail = Polygon(
        p + np.array([-w / 2 + 0.02, -0.04, 0]),
        p + np.array([-w / 2 - 0.18, -0.14, 0]),
        p + np.array([-w / 2 + 0.06, -0.20, 0]),
        fill_color=bg,
        fill_opacity=0.98,
        stroke_color=col,
        stroke_width=2.0,
    ).set_z_index(z)
    text_mob.move_to(bub).set_z_index(z + 2)
    return VGroup(tail, bub, text_mob)


def make_hazard_badge(pos: np.ndarray | list[float], scale_f: float = 1.0, col: str = C_AMBER, z: int = 7) -> VGroup:
    """이중 테두리와 발광 후광을 갖춘 주의 배지."""
    p = np.array(pos, dtype=float)
    halo = Circle(radius=0.34 * scale_f, fill_color=col, fill_opacity=0.14, stroke_color=col, stroke_width=1.2, stroke_opacity=0.45).move_to(p).set_z_index(z)
    outer = RoundedRectangle(
        corner_radius=0.07 * scale_f,
        width=0.46 * scale_f,
        height=0.46 * scale_f,
        fill_color="#3D2B0D",
        fill_opacity=0.98,
        stroke_color=col,
        stroke_width=2.3,
    ).rotate(PI / 4).move_to(p).set_z_index(z + 1)
    inner = RoundedRectangle(
        corner_radius=0.04 * scale_f,
        width=0.34 * scale_f,
        height=0.34 * scale_f,
        fill_opacity=0.0,
        stroke_color=WHITE,
        stroke_width=1.0,
        stroke_opacity=0.55,
    ).rotate(PI / 4).move_to(p).set_z_index(z + 2)
    bang = txt("!", size=17 * scale_f, color=col, bold=True, z=z + 3).move_to(p)
    return VGroup(halo, outer, inner, bang)


def make_shield_icon(
    pos: np.ndarray | list[float],
    scale_f: float = 1.0,
    col: str = C_MINT,
    bg: str = "#112820",
    mark_mob: Mobject | None = None,
    z: int = 7,
) -> VGroup:
    """곡선 베지어 외곽선과 내부 광택선을 갖춘 보안과 검증 방패 아이콘."""
    p = np.array(pos, dtype=float)
    s = scale_f
    sh = VMobject(fill_color=bg, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).set_z_index(z)
    top_l = p + np.array([-0.24 * s, 0.24 * s, 0])
    top_c = p + np.array([0.0, 0.29 * s, 0])
    top_r = p + np.array([0.24 * s, 0.24 * s, 0])
    mid_r = p + np.array([0.24 * s, -0.02 * s, 0])
    bot_c = p + np.array([0.0, -0.30 * s, 0])
    mid_l = p + np.array([-0.24 * s, -0.02 * s, 0])
    sh.start_new_path(top_l)
    sh.add_cubic_bezier_curve_to(p + np.array([-0.12 * s, 0.28 * s, 0]), p + np.array([-0.05 * s, 0.29 * s, 0]), top_c)
    sh.add_cubic_bezier_curve_to(p + np.array([0.05 * s, 0.29 * s, 0]), p + np.array([0.12 * s, 0.28 * s, 0]), top_r)
    sh.add_line_to(mid_r)
    sh.add_cubic_bezier_curve_to(p + np.array([0.22 * s, -0.16 * s, 0]), p + np.array([0.10 * s, -0.25 * s, 0]), bot_c)
    sh.add_cubic_bezier_curve_to(p + np.array([-0.10 * s, -0.25 * s, 0]), p + np.array([-0.22 * s, -0.16 * s, 0]), mid_l)
    sh.close_path()

    inner = sh.copy().scale(0.78, about_point=p).set_fill(opacity=0.0).set_stroke(color=WHITE, width=1.0, opacity=0.45).set_z_index(z + 1)
    grp = VGroup(sh, inner)
    if mark_mob is not None:
        mark_mob.move_to(p + DOWN * 0.01 * s).set_z_index(z + 2)
        grp.add(mark_mob)
    return grp


def make_mini_portal(pos: np.ndarray | list[float], variant: str = "table", col: str = C_CYAN, z: int = 6) -> VGroup:
    """회사마다 다른 웹 공시 화면 레이아웃을 표현하는 미니 포털 카드."""
    p = np.array(pos, dtype=float)
    w, h = 0.42, 0.44
    frame = RoundedRectangle(corner_radius=0.04, width=w, height=h, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=col, stroke_width=1.7).move_to(p).set_z_index(z)
    top_b = Line(p + np.array([-w / 2 + 0.03, h / 2 - 0.09, 0]), p + np.array([w / 2 - 0.03, h / 2 - 0.09, 0]), color=col, stroke_width=1.3, stroke_opacity=0.8).set_z_index(z + 1)
    dots = VGroup(*[Dot(p + np.array([-w / 2 + 0.06 + i * 0.05, h / 2 - 0.045, 0]), radius=0.015, color=col) for i in range(3)]).set_z_index(z + 2)
    inner = VGroup()
    if variant == "table":
        for r in range(3):
            ry = p[1] + 0.04 - r * 0.09
            inner.add(Line([p[0] - 0.15, ry, 0], [p[0] + 0.15, ry, 0], color=col, stroke_width=1.2, stroke_opacity=0.75))
        inner.add(Line([p[0] - 0.03, p[1] + 0.07, 0], [p[0] - 0.03, p[1] - 0.17, 0], color=col, stroke_width=1.1, stroke_opacity=0.65))
    elif variant == "tree":
        inner.add(
            Line([p[0] - 0.12, p[1] + 0.05, 0], [p[0] - 0.12, p[1] - 0.15, 0], color=col, stroke_width=1.4),
            Line([p[0] - 0.12, p[1] + 0.02, 0], [p[0] + 0.12, p[1] + 0.02, 0], color=col, stroke_width=1.3),
            Line([p[0] - 0.12, p[1] - 0.07, 0], [p[0] + 0.08, p[1] - 0.07, 0], color=col, stroke_width=1.3),
            Line([p[0] - 0.12, p[1] - 0.15, 0], [p[0] + 0.14, p[1] - 0.15, 0], color=col, stroke_width=1.3),
        )
    else:
        inner.add(
            RoundedRectangle(corner_radius=0.02, width=0.28, height=0.18, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=col, stroke_width=1.2).move_to(p + DOWN * 0.05),
            Line([p[0] - 0.08, p[1] - 0.05, 0], [p[0] + 0.08, p[1] - 0.05, 0], color=WHITE, stroke_width=1.2, stroke_opacity=0.8),
        )
    inner.set_z_index(z + 2)
    return VGroup(frame, top_b, dots, inner)


def make_firewall_barrier(pos: np.ndarray | list[float], h: float = 0.78, col: str = C_CORAL, z: int = 8) -> VGroup:
    """사선 경고 줄무늬와 정지 배지를 갖춘 접속 차단 게이트."""
    p = np.array(pos, dtype=float)
    post = RoundedRectangle(
        corner_radius=0.04,
        width=0.22,
        height=h,
        fill_color=C_CORAL_DIM,
        fill_opacity=0.98,
        stroke_color=col,
        stroke_width=2.0,
    ).move_to(p).set_z_index(z)
    stripes = VGroup()
    for i in range(4):
        sy = p[1] - h * 0.34 + i * (h * 0.22)
        stripes.add(Line([p[0] - 0.08, sy - 0.05, 0], [p[0] + 0.08, sy + 0.05, 0], color=col, stroke_width=2.0))
    stripes.set_z_index(z + 1)
    stop_oct = RegularPolygon(n=8, fill_color=col, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).scale(0.14).move_to(p).set_z_index(z + 2)
    stop_bar = Line(p + LEFT * 0.065, p + RIGHT * 0.065, color=WHITE, stroke_width=2.4).set_z_index(z + 3)
    return VGroup(post, stripes, stop_oct, stop_bar)


def make_filter_gate(gx: float, y_bot: float = -1.38, y_top: float = 1.38, gap_half: float = 0.48, col: str = C_CYAN, z: int = 6) -> VGroup:
    """상하 정밀 챔퍼 기둥과 중앙 레이저 슬릿을 갖춘 선별 게이트."""
    w = 0.22
    hw = w / 2
    top_pillar = Polygon(
        [gx - hw, y_top, 0],
        [gx + hw, y_top, 0],
        [gx + hw, gap_half + 0.10, 0],
        [gx + hw * 0.45, gap_half, 0],
        [gx - hw * 0.45, gap_half, 0],
        [gx - hw, gap_half + 0.10, 0],
        fill_color=C_PANEL_HI,
        fill_opacity=0.97,
        stroke_color=col,
        stroke_width=2.0,
    ).set_z_index(z)
    bot_pillar = Polygon(
        [gx - hw * 0.45, -gap_half, 0],
        [gx + hw * 0.45, -gap_half, 0],
        [gx + hw, -gap_half - 0.10, 0],
        [gx + hw, y_bot, 0],
        [gx - hw, y_bot, 0],
        [gx - hw, -gap_half - 0.10, 0],
        fill_color=C_PANEL_HI,
        fill_opacity=0.97,
        stroke_color=col,
        stroke_width=2.0,
    ).set_z_index(z)
    cap_t = RoundedRectangle(corner_radius=0.02, width=w * 1.45, height=0.08, fill_color=col, fill_opacity=0.88, stroke_width=0).move_to([gx, y_top, 0]).set_z_index(z + 1)
    cap_b = RoundedRectangle(corner_radius=0.02, width=w * 1.45, height=0.08, fill_color=col, fill_opacity=0.88, stroke_width=0).move_to([gx, y_bot, 0]).set_z_index(z + 1)
    beam_glow = Line([gx, -gap_half, 0], [gx, gap_half, 0], color=col, stroke_width=5.5, stroke_opacity=0.22).set_z_index(z - 1)
    beam_core = DashedLine([gx, -gap_half, 0], [gx, gap_half, 0], dash_length=0.06, color=col, stroke_width=2.0).set_z_index(z + 1)
    node_t = Dot([gx, gap_half, 0], radius=0.042, color=WHITE).set_z_index(z + 2)
    node_b = Dot([gx, -gap_half, 0], radius=0.042, color=WHITE).set_z_index(z + 2)
    return VGroup(beam_glow, top_pillar, bot_pillar, cap_t, cap_b, beam_core, node_t, node_b)


def make_silo_pool(pos: np.ndarray | list[float], w: float = 1.48, h: float = 2.04, col: str = C_GOLD, accent: str = C_MINT, z: int = 4) -> VGroup:
    """상하 타원 림과 내부 적재 층위를 갖춘 원통형 데이터 사일로."""
    p = np.array(pos, dtype=float)
    eh = w * 0.17
    body = Rectangle(
        width=w,
        height=h - eh,
        fill_color="#13251F",
        fill_opacity=0.96,
        stroke_color=col,
        stroke_width=2.2,
    ).move_to(p).set_z_index(z)
    bot_rim = Ellipse(width=w, height=eh, fill_color="#183228", fill_opacity=0.98, stroke_color=col, stroke_width=2.2).move_to(p + DOWN * ((h - eh) / 2)).set_z_index(z + 1)
    top_rim = Ellipse(width=w, height=eh, fill_color="#0B1714", fill_opacity=0.98, stroke_color=col, stroke_width=2.2).move_to(p + UP * ((h - eh) / 2)).set_z_index(z + 2)
    strata = VGroup()
    for i in range(4):
        sy = p[1] - h * 0.34 + i * 0.16
        strata.add(
            RoundedRectangle(
                corner_radius=0.03,
                width=w * 0.76,
                height=0.09,
                fill_color=accent if i < 3 else col,
                fill_opacity=0.32 + i * 0.14,
                stroke_width=0,
            ).move_to([p[0], sy, 0])
        )
    strata.set_z_index(z + 1)
    sheen = Line(p + np.array([-w * 0.36, -h * 0.34, 0]), p + np.array([-w * 0.36, h * 0.30, 0]), color=WHITE, stroke_width=1.5, stroke_opacity=0.30).set_z_index(z + 2)
    return VGroup(bot_rim, body, strata, sheen, top_rim)


def make_loupe(
    center: np.ndarray | list[float],
    radius: float = 1.56,
    col: str = C_GOLD,
    cone_origin: np.ndarray | list[float] | None = None,
    z: int = 6,
) -> VGroup:
    """이중 금속 베젤과 반사광 호, 눈금선, 손잡이, 확대 광원뿔을 갖춘 정밀 루페."""
    c = np.array(center, dtype=float)
    parts: list[Mobject] = []
    if cone_origin is not None:
        o = np.array(cone_origin, dtype=float)
        t_up = c + np.array([-radius * 0.62, radius * 0.78, 0])
        t_dn = c + np.array([-radius * 0.62, -radius * 0.78, 0])
        cone = Polygon(o, t_up, t_dn, fill_color=col, fill_opacity=0.09, stroke_width=0).set_z_index(z - 2)
        ray_u = DashedLine(o, t_up, dash_length=0.08, color=col, stroke_width=1.6, stroke_opacity=0.75).set_z_index(z - 1)
        ray_d = DashedLine(o, t_dn, dash_length=0.08, color=col, stroke_width=1.6, stroke_opacity=0.75).set_z_index(z - 1)
        parts.extend([cone, ray_u, ray_d])

    ang_h = -0.68
    u_vec = np.array([math.cos(ang_h), math.sin(ang_h), 0.0])
    collar = RoundedRectangle(corner_radius=0.04, width=0.22, height=0.28, fill_color=C_SLATE, fill_opacity=1.0, stroke_color=col, stroke_width=1.8).rotate(ang_h + PI / 2).move_to(c + u_vec * (radius + 0.11)).set_z_index(z)
    grip = RoundedRectangle(corner_radius=0.08, width=0.26, height=0.78, fill_color="#1D2632", fill_opacity=1.0, stroke_color=col, stroke_width=2.2).rotate(ang_h + PI / 2).move_to(c + u_vec * (radius + 0.54)).set_z_index(z)

    outer_bezel = Circle(radius=radius * 1.055, fill_color="#1A222D", fill_opacity=0.98, stroke_color=C_GOLD_DEEP, stroke_width=2.2).move_to(c).set_z_index(z)
    lens = Circle(radius=radius, fill_color="#0D151F", fill_opacity=0.97, stroke_color=col, stroke_width=3.0).move_to(c).set_z_index(z + 1)
    inner_ring = Circle(radius=radius * 0.93, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.2, stroke_opacity=0.55).move_to(c).set_z_index(z + 2)
    glare = Arc(radius=radius * 0.85, start_angle=2.05, angle=0.72, arc_center=c, color=WHITE, stroke_width=2.6, stroke_opacity=0.36).set_z_index(z + 2)
    ticks = VGroup(
        *[
            Line(c + np.array([math.cos(a) * radius * 0.90, math.sin(a) * radius * 0.90, 0]), c + np.array([math.cos(a) * radius * 0.98, math.sin(a) * radius * 0.98, 0]), color=col, stroke_width=1.6, stroke_opacity=0.75)
            for a in (0, PI / 2, PI, 3 * PI / 2)
        ]
    ).set_z_index(z + 2)
    parts.extend([collar, grip, outer_bezel, lens, inner_ring, glare, ticks])
    return VGroup(*parts)


def make_stopwatch(center: np.ndarray | list[float], r: float = 0.28, col: str = C_AMBER, z: int = 7) -> tuple[VGroup, Line]:
    """크라운 버튼과 눈금 다이얼을 갖춘 크로노그래프 초시계 본체와 바늘."""
    c = np.array(center, dtype=float)
    stem = Rectangle(width=r * 0.24, height=r * 0.24, fill_color=C_SLATE, fill_opacity=1.0, stroke_color=col, stroke_width=1.4).move_to(c + UP * (r * 1.10)).set_z_index(z)
    crown = RoundedRectangle(corner_radius=0.02, width=r * 0.56, height=r * 0.16, fill_color=col, fill_opacity=0.95, stroke_width=0).move_to(c + UP * (r * 1.26)).set_z_index(z + 1)
    pusher = Line(c + np.array([r * 0.72, r * 0.72, 0]), c + np.array([r * 0.94, r * 0.94, 0]), color=col, stroke_width=2.4).set_z_index(z)
    dial = Circle(radius=r, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=col, stroke_width=2.2).move_to(c).set_z_index(z + 1)
    ticks = VGroup(
        *[
            Line(c + np.array([math.cos(k * PI / 4) * r * 0.74, math.sin(k * PI / 4) * r * 0.74, 0]), c + np.array([math.cos(k * PI / 4) * r * 0.92, math.sin(k * PI / 4) * r * 0.92, 0]), color=C_INK_1, stroke_width=1.2)
            for k in range(8)
        ]
    ).set_z_index(z + 2)
    pin = Dot(c, radius=r * 0.12, color=WHITE).set_z_index(z + 4)
    hand = Line(c, c + UP * (r * 0.72), color=col, stroke_width=2.6).set_z_index(z + 3)
    return VGroup(stem, crown, pusher, dial, ticks, pin), hand


def make_npu_chip(
    pos: np.ndarray | list[float],
    w: float = 2.08,
    h: float = 1.04,
    col: str = C_GOLD,
    accent: str = C_CYAN,
    label_mob: Mobject | None = None,
    z: int = 6,
) -> VGroup:
    """회로 리드 핀과 내부 실리콘 다이 프레임을 갖춘 판정 모델 칩."""
    p = np.array(pos, dtype=float)
    pins = VGroup()
    for i in range(6):
        px = p[0] - w * 0.36 + i * (w * 0.72 / 5)
        pins.add(
            Line([px, p[1] + h / 2, 0], [px, p[1] + h / 2 + 0.10, 0], color=col, stroke_width=2.2),
            Line([px, p[1] - h / 2, 0], [px, p[1] - h / 2 - 0.10, 0], color=col, stroke_width=2.2),
        )
    for j in range(3):
        py = p[1] - h * 0.28 + j * (h * 0.28)
        pins.add(
            Line([p[0] - w / 2 - 0.10, py, 0], [p[0] - w / 2, py, 0], color=accent, stroke_width=2.0),
            Line([p[0] + w / 2, py, 0], [p[0] + w / 2 + 0.10, py, 0], color=accent, stroke_width=2.0),
        )
    pins.set_z_index(z)
    pkg = RoundedRectangle(corner_radius=0.09, width=w, height=h, fill_color="#16202E", fill_opacity=0.98, stroke_color=col, stroke_width=2.4).move_to(p).set_z_index(z + 1)
    die = RoundedRectangle(corner_radius=0.05, width=w * 0.88, height=h * 0.80, fill_color="#1D2A3C", fill_opacity=0.96, stroke_color=accent, stroke_width=1.2, stroke_opacity=0.75).move_to(p).set_z_index(z + 2)
    grp = VGroup(pins, pkg, die)
    if label_mob is not None:
        label_mob.move_to(p).set_z_index(z + 3)
        grp.add(label_mob)
    return grp


def make_emitter_nozzle(
    pos: np.ndarray | list[float],
    w: float = 1.66,
    h: float = 1.12,
    col: str = C_CYAN,
    accent: str = C_VIOLET,
    label_mob: Mobject | None = None,
    z: int = 5,
) -> VGroup:
    """압력 챔버와 수렴 노즐 콘, 방출 조리개 링을 갖춘 확률 분사 노즐."""
    p = np.array(pos, dtype=float)
    lx = p[0] - w / 2
    mx = p[0] + w * 0.16
    rx = p[0] + w / 2
    hh = h / 2
    nh = h * 0.24

    body = VMobject(fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=col, stroke_width=2.2).set_z_index(z)
    body.start_new_path(np.array([lx, p[1] + hh, 0]))
    body.add_line_to(np.array([mx, p[1] + hh, 0]))
    body.add_cubic_bezier_curve_to(np.array([mx + 0.22, p[1] + hh, 0]), np.array([rx - 0.18, p[1] + nh, 0]), np.array([rx, p[1] + nh, 0]))
    body.add_line_to(np.array([rx, p[1] - nh, 0]))
    body.add_cubic_bezier_curve_to(np.array([rx - 0.18, p[1] - nh, 0]), np.array([mx + 0.22, p[1] - hh, 0]), np.array([mx, p[1] - hh, 0]))
    body.add_line_to(np.array([lx, p[1] - hh, 0]))
    body.close_path()

    rear_cap = RoundedRectangle(corner_radius=0.04, width=0.10, height=h * 0.86, fill_color=accent, fill_opacity=0.85, stroke_width=0).move_to([lx + 0.05, p[1], 0]).set_z_index(z + 1)
    collar = Line([mx, p[1] - hh * 0.88, 0], [mx, p[1] + hh * 0.88, 0], color=accent, stroke_width=1.6, stroke_opacity=0.75).set_z_index(z + 1)
    aperture = Ellipse(width=0.12, height=nh * 2.0, fill_color=C_GOLD, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.4).move_to([rx, p[1], 0]).set_z_index(z + 2)
    grp = VGroup(body, rear_cap, collar, aperture)
    if label_mob is not None:
        label_mob.move_to([lx + (mx - lx) * 0.54, p[1], 0]).set_z_index(z + 3)
        grp.add(label_mob)
    return grp


def make_hopper_vessel(
    cx: float,
    top_y: float,
    bot_y: float,
    top_w: float = 1.22,
    slot_w: float = 0.72,
    col: str = C_GOLD,
    label_mob: Mobject | None = None,
    z: int = 7,
) -> VGroup:
    """좁은 사전 용량을 직관적으로 보여 주는 병목 호퍼 용기."""
    tl = np.array([cx - top_w / 2, top_y, 0])
    tr = np.array([cx + top_w / 2, top_y, 0])
    bl = np.array([cx - slot_w / 2, bot_y, 0])
    br = np.array([cx + slot_w / 2, bot_y, 0])
    h_v = top_y - bot_y

    vessel = VMobject(fill_color="#251F10", fill_opacity=0.94, stroke_color=col, stroke_width=2.2).set_z_index(z)
    vessel.start_new_path(tl)
    vessel.add_cubic_bezier_curve_to(tl + DOWN * (h_v * 0.45), bl + UP * (h_v * 0.35), bl)
    vessel.add_line_to(br)
    vessel.add_cubic_bezier_curve_to(br + UP * (h_v * 0.35), tr + DOWN * (h_v * 0.45), tr)

    rim = Ellipse(width=top_w, height=0.13, fill_color="#121008", fill_opacity=0.96, stroke_color=col, stroke_width=2.0).move_to([cx, top_y, 0]).set_z_index(z + 1)
    base_bar = RoundedRectangle(corner_radius=0.03, width=slot_w * 1.18, height=0.08, fill_color=col, fill_opacity=0.90, stroke_width=0).move_to([cx, bot_y, 0]).set_z_index(z + 1)
    grp = VGroup(vessel, rim, base_bar)
    if label_mob is not None:
        label_mob.move_to([cx, (top_y + bot_y) / 2 - 0.04, 0]).set_z_index(z + 2)
        grp.add(label_mob)
    return grp


def make_mini_browser(pos: np.ndarray | list[float], w: float = 0.66, h: float = 0.44, col: str = C_GOLD, z: int = 7) -> VGroup:
    """상단 창 표시줄과 미니 막대 차트를 갖춘 단독 HTML 화면 축소 아이콘."""
    p = np.array(pos, dtype=float)
    win = RoundedRectangle(corner_radius=0.04, width=w, height=h, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=col, stroke_width=1.7).move_to(p).set_z_index(z)
    hbar = Line(p + np.array([-w / 2 + 0.03, h / 2 - 0.10, 0]), p + np.array([w / 2 - 0.03, h / 2 - 0.10, 0]), color=C_SLATE, stroke_width=1.2).set_z_index(z + 1)
    dots = VGroup(
        Dot(p + np.array([-w / 2 + 0.07, h / 2 - 0.05, 0]), radius=0.016, color=C_CORAL),
        Dot(p + np.array([-w / 2 + 0.13, h / 2 - 0.05, 0]), radius=0.016, color=C_GOLD),
        Dot(p + np.array([-w / 2 + 0.19, h / 2 - 0.05, 0]), radius=0.016, color=C_MINT),
    ).set_z_index(z + 2)
    bars = VGroup(
        Rectangle(width=0.08, height=0.11, fill_color=C_CYAN, fill_opacity=0.92, stroke_width=0).move_to(p + np.array([-0.14, -0.09, 0])),
        Rectangle(width=0.08, height=0.19, fill_color=col, fill_opacity=0.96, stroke_width=0).move_to(p + np.array([-0.02, -0.05, 0])),
        Rectangle(width=0.08, height=0.15, fill_color=C_MINT, fill_opacity=0.92, stroke_width=0).move_to(p + np.array([0.10, -0.07, 0])),
    ).set_z_index(z + 2)
    return VGroup(win, hbar, dots, bars)


def make_domain_glyph(kind: str, pos: np.ndarray | list[float], col: str = C_CYAN, z: int = 7) -> VGroup:
    """기관, 종형, 특약, 급부, 시장 소식을 나타내는 도메인 맞춤 벡터 기호."""
    p = np.array(pos, dtype=float)
    if kind == "org":
        roof = Polygon(p + [-0.20, 0.08, 0], p + [0.0, 0.20, 0], p + [0.20, 0.08, 0], fill_color=col, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.2)
        pillars = VGroup(*[Rectangle(width=0.045, height=0.18, fill_color=col, fill_opacity=0.88, stroke_width=0).move_to(p + [-0.11 + i * 0.11, -0.02, 0]) for i in range(3)])
        base = Rectangle(width=0.38, height=0.05, fill_color=col, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.0).move_to(p + [0.0, -0.14, 0])
        g = VGroup(pillars, roof, base)
    elif kind == "variant":
        back = RoundedRectangle(corner_radius=0.03, width=0.28, height=0.26, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=col, stroke_width=1.3).move_to(p + [0.05, 0.05, 0])
        front = RoundedRectangle(corner_radius=0.03, width=0.28, height=0.26, fill_color=col, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.3).move_to(p + [-0.04, -0.03, 0])
        ln = Line(p + [-0.12, -0.03, 0], p + [0.04, -0.03, 0], color=C_DARK_INK, stroke_width=1.8)
        g = VGroup(back, front, ln)
    elif kind == "rider":
        g = make_shield_icon(p, scale_f=0.68, col=col, bg="#10222E", mark_mob=txt("+", size=11, color=WHITE, bold=True), z=z)
    elif kind == "benefit":
        outer = RegularPolygon(n=6, fill_color=col, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.4).scale(0.18).move_to(p)
        inner = RegularPolygon(n=6, fill_opacity=0.0, stroke_color=C_DARK_INK, stroke_width=1.2).scale(0.11).move_to(p)
        core = Dot(p, radius=0.035, color=WHITE)
        g = VGroup(outer, inner, core)
    else:
        dot = Dot(p + [-0.08, -0.08, 0], radius=0.045, color=col)
        w_a = Arc(radius=0.14, start_angle=0.0, angle=PI / 2, arc_center=p + [-0.08, -0.08, 0], color=col, stroke_width=2.0)
        w_b = Arc(radius=0.24, start_angle=0.0, angle=PI / 2, arc_center=p + [-0.08, -0.08, 0], color=WHITE, stroke_width=1.8)
        g = VGroup(dot, w_a, w_b)
    g.set_z_index(z)
    return g


def make_compass_rose(center: np.ndarray | list[float], r: float = 0.48, col: str = C_GOLD, z: int = 10) -> tuple[VGroup, VGroup]:
    """눈금 베젤을 갖춘 아스트롤라베 링과 투톤 다이아몬드 나침반 바늘."""
    c = np.array(center, dtype=float)
    outer = Circle(radius=r * 1.10, fill_color="#0D141E", fill_opacity=0.98, stroke_color=C_GOLD_DEEP, stroke_width=1.8).move_to(c).set_z_index(z)
    ring = Circle(radius=r, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.6).move_to(c).set_z_index(z + 1)
    ticks = VGroup(
        *[
            Line(c + np.array([math.cos(k * PI / 4) * r * 0.82, math.sin(k * PI / 4) * r * 0.82, 0]), c + np.array([math.cos(k * PI / 4) * r * 0.98, math.sin(k * PI / 4) * r * 0.98, 0]), color=col if k % 2 == 0 else C_SLATE, stroke_width=1.8 if k % 2 == 0 else 1.2)
            for k in range(8)
        ]
    ).set_z_index(z + 2)
    n_up = Polygon(c + LEFT * (r * 0.16), c + UP * (r * 0.78), c + RIGHT * (r * 0.16), fill_color=col, fill_opacity=0.98, stroke_color=WHITE, stroke_width=1.2)
    n_dn = Polygon(c + LEFT * (r * 0.16), c + DOWN * (r * 0.78), c + RIGHT * (r * 0.16), fill_color=C_CYAN_DIM, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=1.2)
    needle = VGroup(n_dn, n_up).rotate(PI / 4, about_point=c).set_z_index(z + 3)
    return VGroup(outer, ring, ticks), needle


def set_3d_tier(mob: Mobject, tier: float, sub: int = 0, sort_3d: bool = True) -> Mobject:
    """삼차원 카메라 렌더링 시 수평 분리 계층(tier)과 세부 순서(sub)를 하위 도형 전체에 부여한다."""
    for submob in mob.get_family():
        setattr(submob, "_depth_tier", float(tier))
        setattr(submob, "_depth_sub", int(sub))
        setattr(submob, "_depth_sort", bool(sort_3d))
    return mob


def build_world_grid(span_x: float = 11.0, span_y: float = 6.5) -> VGroup:
    """세계 좌표 격자."""
    grid = VGroup()
    for x in np.arange(-span_x, span_x + 0.1, 1.0):
        is_ax = abs(x) < 1e-6
        grid.add(
            Line(
                [x, -span_y, 0],
                [x, span_y, 0],
                color=C_CYAN_DIM if is_ax else C_GRID,
                stroke_width=1.1 if is_ax else 0.75,
                stroke_opacity=0.42 if is_ax else 0.30,
            )
        )
    for y in np.arange(-span_y, span_y + 0.1, 1.0):
        is_ax = abs(y) < 1e-6
        grid.add(
            Line(
                [-span_x, y, 0],
                [span_x, y, 0],
                color=C_CYAN_DIM if is_ax else C_GRID,
                stroke_width=1.1 if is_ax else 0.75,
                stroke_opacity=0.42 if is_ax else 0.30,
            )
        )
    grid.set_z_index(-5)
    set_3d_tier(grid, -20.0, sub=0, sort_3d=False)
    return grid


def floor_grid_3d(
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    z_val: float = 0.0,
    step_x: float = 1.0,
    step_y: float = 1.0,
    col: str = C_CYAN_DIM,
) -> VGroup:
    """삼차원 공간 바닥 기준 격자."""
    plate = Rectangle(
        width=x_max - x_min,
        height=y_max - y_min,
        fill_color="#0A121B",
        fill_opacity=0.72,
        stroke_color=col,
        stroke_width=1.4,
        stroke_opacity=0.65,
    ).move_to([(x_min + x_max) / 2, (y_min + y_max) / 2, z_val])
    lines = VGroup()
    for x in np.arange(x_min, x_max + 1e-4, step_x):
        lines.add(Line([x, y_min, z_val], [x, y_max, z_val], color=col, stroke_width=0.9, stroke_opacity=0.38))
    for y in np.arange(y_min, y_max + 1e-4, step_y):
        lines.add(Line([x_min, y, z_val], [x_max, y, z_val], color=col, stroke_width=0.9, stroke_opacity=0.38))
    set_3d_tier(plate, -10.0, sub=0, sort_3d=False)
    set_3d_tier(lines, -10.0, sub=1, sort_3d=False)
    return VGroup(plate, lines)


def pillar_3d(
    x: float,
    y: float,
    w: float,
    d: float,
    h: float,
    base_z: float = 0.0,
    col: str = C_CYAN,
    opacity: float = 0.80,
    stroke_col: str | None = None,
    sw: float = 1.3,
    tier: float = 0.0,
) -> Prism:
    """바닥 높이 base_z 에서 위로 솟는 삼차원 기둥."""
    eff_h = max(h, 0.04)
    p = Prism(
        dimensions=[w, d, eff_h],
        fill_color=col,
        fill_opacity=opacity,
        stroke_color=stroke_col if stroke_col is not None else col,
        stroke_width=sw,
    ).move_to([x, y, base_z + eff_h / 2])
    set_3d_tier(p, tier, sub=0, sort_3d=True)
    return p


def pillar_3d_sliced(
    x: float,
    y: float,
    w: float,
    d: float,
    h: float,
    base_z: float = 0.0,
    cuts: Sequence[tuple[float, float]] = (),
    top_tier: float = 0.0,
    col: str = C_CYAN,
    opacity: float = 0.88,
    stroke_col: str | None = None,
    sw: float = 1.3,
) -> VGroup:
    """수평 기준면 높이(cuts)마다 기둥을 분할해 기준면 아래는 비치고 위 돌출부만 올라오게 만든다."""
    eff_h = max(h, 0.04)
    z0, z1 = base_z, base_z + eff_h
    sorted_cuts = sorted(cuts, key=lambda item: item[0])
    pts = [z0]
    for zc, _ in sorted_cuts:
        if z0 + 1e-4 < zc < z1 - 1e-4:
            pts.append(zc)
    pts.append(z1)

    segs = VGroup()
    for za, zb in zip(pts[:-1], pts[1:]):
        mid = 0.5 * (za + zb)
        seg_tier = top_tier
        for zc, tb in sorted_cuts:
            if mid <= zc:
                seg_tier = tb
                break
        seg = Prism(
            dimensions=[w, d, zb - za],
            fill_color=col,
            fill_opacity=opacity,
            stroke_color=stroke_col if stroke_col is not None else col,
            stroke_width=sw,
        ).move_to([x, y, mid])
        set_3d_tier(seg, seg_tier, sub=0, sort_3d=True)
        segs.add(seg)
    return segs


def glass_plane_3d(
    cx: float,
    cy: float,
    z_val: float,
    w: float,
    d: float,
    col: str,
    fill_op: float = 0.16,
    sw: float = 2.0,
    tier: float = 0.0,
) -> RoundedRectangle:
    """삼차원 공간을 가로지르는 반투명 수평 기준면."""
    plane = RoundedRectangle(
        corner_radius=0.10,
        width=w,
        height=d,
        fill_color=col,
        fill_opacity=fill_op,
        stroke_color=col,
        stroke_width=sw,
        stroke_opacity=0.90,
    ).move_to([cx, cy, z_val])
    set_3d_tier(plane, tier, sub=0, sort_3d=False)
    return plane


def build_hud_chrome() -> VGroup:
    """상하단 고정 자막 배경 바."""
    top_bar = Rectangle(width=14.6, height=0.74, fill_color="#05080C", fill_opacity=0.96, stroke_width=0).move_to([0, 3.65, 0])
    bot_bar = Rectangle(width=14.6, height=0.74, fill_color="#05080C", fill_opacity=0.96, stroke_width=0).move_to([0, -3.65, 0])
    top_line = Line([-7.15, 3.28, 0], [7.15, 3.28, 0], color=C_SLATE, stroke_width=1.15)
    bot_line = Line([-7.15, -3.28, 0], [7.15, -3.28, 0], color=C_SLATE, stroke_width=1.15)
    chrome = VGroup(top_bar, bot_bar, top_line, bot_line)
    chrome.set_z_index(30)
    return chrome


class PostLifeBaseScene(ThreeDScene):
    """고정 상하단 자막 바와 계층형 삼차원 깊이 정렬 도우미를 갖춘 장면."""

    def get_moving_mobjects(self, *animations: Animation) -> list[Mobject]:
        if abs(self.renderer.camera.get_phi()) > 1e-4:
            return list(self.mobjects)
        return super().get_moving_mobjects(*animations)

    def init_cinema_canvas(self) -> tuple[VGroup, VGroup]:
        self.camera.background_color = C_BG
        cam = self.camera

        def _origin_locked_get_cairo_context(pixel_array: np.ndarray) -> cairo.Context:
            cached_ctx = cam.get_cached_cairo_context(pixel_array)
            if cached_ctx:
                return cached_ctx
            pw, ph = cam.pixel_width, cam.pixel_height
            fw, fh = cam.frame_width, cam.frame_height
            surface = cairo.ImageSurface.create_for_data(pixel_array.data, cairo.FORMAT_ARGB32, pw, ph)
            ctx = cairo.Context(surface)
            ctx.set_matrix(cairo.Matrix(pw / fw, 0, 0, -(ph / fh), pw / 2, ph / 2))
            cam.cache_cairo_context(pixel_array, ctx)
            return ctx

        def _tiered_get_mobjects_to_display(*args, **kwargs) -> list[Mobject]:
            base_mobs = Camera.get_mobjects_to_display(cam, *args, **kwargs)
            if (
                abs(cam.get_phi()) < 1e-4
                and abs(cam.get_theta() + math.pi / 2) < 1e-4
                and abs(cam.get_gamma()) < 1e-4
            ):
                return base_mobs

            rot_matrix = cam.get_rotation_matrix()
            view_axis = rot_matrix[2]
            fixed_frame = cam.fixed_in_frame_mobjects
            fixed_orient = cam.fixed_orientation_mobjects

            def _key(item: tuple[int, Mobject]) -> tuple[float, int, float, float, int]:
                idx, mob = item
                if mob in fixed_frame:
                    return (30.0, 0, 0.0, float(mob.z_index), idx)
                if mob in fixed_orient:
                    tier_b = float(getattr(mob, "_depth_tier", 20.0))
                    sub_b = int(getattr(mob, "_depth_sub", 0))
                    c_pt = fixed_orient[mob]()
                    cam_d = round(float(np.dot(c_pt, view_axis)), 5)
                    return (tier_b, sub_b, cam_d, float(mob.z_index), idx)
                if mob.z_index < 0 and not hasattr(mob, "_depth_tier"):
                    return (-20.0, 0, 0.0, float(mob.z_index), idx)

                tier = float(getattr(mob, "_depth_tier", 0.0))
                sub = int(getattr(mob, "_depth_sub", 0))
                sort_3d = bool(getattr(mob, "_depth_sort", True))
                if sort_3d:
                    cam_d = float(np.dot(mob.get_z_index_reference_point(), view_axis))
                else:
                    cam_d = 0.0
                return (tier, sub, cam_d, float(mob.z_index), idx)

            return [mob for _, mob in sorted(enumerate(base_mobs), key=_key)]

        cam.get_cairo_context = _origin_locked_get_cairo_context  # type: ignore[method-assign]
        cam.get_mobjects_to_display = _tiered_get_mobjects_to_display  # type: ignore[method-assign]
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES, gamma=0 * DEGREES, zoom=1.0, frame_center=ORIGIN)
        world_grid = build_world_grid()
        hud_chrome = build_hud_chrome()
        self.add(world_grid)
        self.add_fixed_in_frame_mobjects(hud_chrome)
        self._hud_chrome = hud_chrome
        self._world_grid = world_grid
        return world_grid, hud_chrome

    def cam_move(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        center: Sequence[float] | np.ndarray | None = None,
        anims: Iterable[Animation] = (),
        rt: float = 1.10,
        rate_func=smooth,
    ) -> None:
        fc = np.array(center, dtype=float) if center is not None else None
        self.move_camera(
            phi=phi,
            theta=theta,
            gamma=gamma,
            zoom=zoom,
            frame_center=fc,
            added_anims=list(anims),
            run_time=rt,
            rate_func=rate_func,
        )

    def reset_cam_2d(self, anims: Iterable[Animation] = (), rt: float = 0.90) -> None:
        self.cam_move(phi=0 * DEGREES, theta=-90 * DEGREES, gamma=0 * DEGREES, zoom=1.0, center=ORIGIN, anims=anims, rt=rt)

    def snap_cam_2d(self) -> None:
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES, gamma=0 * DEGREES, zoom=1.0, frame_center=ORIGIN)

    def add_billboard(self, *mobs: Mobject) -> None:
        self.add_fixed_orientation_mobjects(*mobs)

    def remove_billboard(self, *mobs: Mobject) -> None:
        self.remove_fixed_orientation_mobjects(*mobs)
        self.remove(*mobs)

    def register_billboards(self, *mobs: Mobject) -> None:
        self.renderer.camera.add_fixed_orientation_mobjects(*mobs)

    def clear_billboards(self, *mobs: Mobject) -> None:
        self.renderer.camera.remove_fixed_orientation_mobjects(*mobs)
        self.remove(*mobs)

    def make_hud(self, ch_num: int, title: str, subtitle: str) -> tuple[VGroup, VGroup, VGroup]:
        is_finale = ch_num == TOTAL_CHAPTERS
        badge = RoundedRectangle(
            corner_radius=0.06,
            width=0.76,
            height=0.34,
            fill_color=C_GOLD if is_finale else C_CYAN_DIM,
            fill_opacity=0.98,
            stroke_color=C_GOLD if is_finale else C_CYAN,
            stroke_width=1.5,
        )
        b_txt = txt(f"{ch_num}장", size=14.5, color=C_DARK_INK if is_finale else C_CYAN, bold=True, z=32).move_to(badge)
        tag = VGroup(badge.set_z_index(31), b_txt)
        t_mob = txt(title, size=18.8, color=C_WHITE, bold=True, z=32)
        left = VGroup(tag, t_mob).arrange(RIGHT, buff=0.16)
        fit(left, max_w=8.10)
        left.move_to([-6.18 + left.width / 2, 3.63, 0]).set_z_index(31)

        dots = VGroup()
        for i in range(1, TOTAL_CHAPTERS + 1):
            col = C_GOLD if i == ch_num else (C_CYAN if i < ch_num else C_SLATE)
            w = 0.28 if i == ch_num else 0.11
            dots.add(
                RoundedRectangle(
                    corner_radius=0.04,
                    width=w,
                    height=0.09,
                    fill_color=col,
                    fill_opacity=1.0 if i <= ch_num else 0.45,
                    stroke_width=0,
                )
            )
        dots.arrange(RIGHT, buff=0.055)
        app_lbl = txt("우체국보험 상품·청약 판단 지원", size=13.2, color=C_INK_1, z=32)
        right = VGroup(app_lbl, dots).arrange(RIGHT, buff=0.16)
        right.move_to([6.18 - right.width / 2, 3.63, 0]).set_z_index(31)

        sub_mob = fit(txt(subtitle, size=17.2, color=C_INK_0, bold=True, z=32), max_w=12.5)
        sub_mob.move_to([0, -3.63, 0])
        bot = VGroup(sub_mob).set_z_index(31)
        return left, right, bot

    def show_initial_hud(self, hl: VGroup, hr: VGroup, hb: VGroup, extra_anims: Iterable[Animation] = (), rt: float = 0.95) -> None:
        self.add_fixed_in_frame_mobjects(hl, hr, hb)
        self.play(
            FadeIn(hl, shift=DOWN * 0.06),
            FadeIn(hr, shift=DOWN * 0.06),
            FadeIn(hb, shift=UP * 0.06),
            *list(extra_anims),
            run_time=rt,
        )

    def switch_hud(
        self,
        outgoing_stage: Mobject,
        hl: VGroup,
        hr: VGroup,
        hb: VGroup,
        ch_num: int,
        title: str,
        subtitle: str,
    ) -> tuple[VGroup, VGroup, VGroup]:
        nl, nr, nb = self.make_hud(ch_num, title, subtitle)
        self.add_fixed_in_frame_mobjects(nl, nr, nb)
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            gamma=0 * DEGREES,
            zoom=1.0,
            center=ORIGIN,
            anims=[
                FadeOut(outgoing_stage, shift=UP * 0.12),
                FadeOut(hl, shift=UP * 0.04),
                FadeIn(nl, shift=UP * 0.04),
                FadeOut(hr),
                FadeIn(nr),
                FadeOut(hb, shift=DOWN * 0.04),
                FadeIn(nb, shift=UP * 0.04),
            ],
            rt=0.60,
        )
        self.remove_fixed_in_frame_mobjects(hl, hr, hb)
        self.remove(outgoing_stage, hl, hr, hb)
        return nl, nr, nb

    def fade_out_part(self, stage: Mobject, hl: VGroup, hr: VGroup, hb: VGroup) -> None:
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            gamma=0 * DEGREES,
            zoom=1.0,
            center=ORIGIN,
            anims=[
                FadeOut(stage, shift=UP * 0.10),
                FadeOut(hl, shift=UP * 0.04),
                FadeOut(hr, shift=UP * 0.04),
                FadeOut(hb, shift=DOWN * 0.04),
            ],
            rt=0.50,
        )
        self.remove_fixed_in_frame_mobjects(hl, hr, hb)
        self.remove(stage, hl, hr, hb)
        self.wait(0.10)

    def update_subtitle(self, hb: VGroup, new_sub: str, rt: float = 0.48) -> VGroup:
        new_mob = fit(txt(new_sub, size=17.2, color=C_INK_0, bold=True, z=32), max_w=12.5).move_to([0, -3.63, 0])
        nb = VGroup(new_mob).set_z_index(31)
        self.add_fixed_in_frame_mobjects(nb)
        self.play(FadeOut(hb, run_time=rt * 0.45), FadeIn(nb, run_time=rt * 0.55))
        self.remove_fixed_in_frame_mobjects(hb)
        self.remove(hb)
        return nb

    def check_bounds(self, m: Mobject, name: str) -> None:
        lx, rx = m.get_left()[0], m.get_right()[0]
        by, ty = m.get_bottom()[1], m.get_top()[1]
        if lx < -6.38 or rx > 6.38 or by < -3.24 or ty > 3.24:
            print(f"[BOUNDS WARNING] {name}: x=[{lx:.2f}, {rx:.2f}], y=[{by:.2f}, {ty:.2f}]")
