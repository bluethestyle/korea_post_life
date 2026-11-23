from __future__ import annotations

import math
import numpy as np
from manim import *

# ---------------------------------------------------------------------------
# 3Blue1Brown Clarity x Post Life Architectural Palette
# ---------------------------------------------------------------------------
C_BG = "#090D12"
C_BG_SUB = "#101720"
C_GRID = "#1E2936"

C_CYAN = "#58C4DD"       # Collection, fact layer, deterministic code
C_CYAN_DIM = "#1E4E5C"
C_GOLD = "#E2C878"       # Verified truth, shared standard, Post Life strength
C_GOLD_DEEP = "#8F7B3E"
C_AMBER = "#F59E0B"      # Constraint / pending review / caution
C_AMBER_DIM = "#3D2B0D"
C_CORAL = "#FF5C5C"      # Bottleneck, error, blocked access, coverage gap
C_CORAL_DIM = "#4D1F24"
C_VIOLET = "#A78BFA"     # Decision model, market trend, live insight
C_VIOLET_DIM = "#261E42"
C_MINT = "#6EE7B7"       # Solved architecture, verified match, active defense
C_MINT_DIM = "#16382C"

C_INK_0 = "#F2F5F8"
C_INK_1 = "#C2CBD4"
C_INK_2 = "#7F8C99"
C_WHITE = "#FFFFFF"
C_PANEL = "#131B24"
C_PANEL_HI = "#1B2633"
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
    size: float = 14,
    bold: bool = True,
    px: float = 0.16,
    py: float = 0.08,
    z: int = 6,
) -> VGroup:
    t = txt(label, size=size, color=fg, bold=bold, z=z + 1)
    b = RoundedRectangle(
        corner_radius=0.08,
        width=t.width + px * 2,
        height=t.height + py * 2,
        fill_color=bg,
        fill_opacity=0.95,
        stroke_color=border,
        stroke_width=1.3,
    ).set_z_index(z)
    t.move_to(b.get_center())
    g = VGroup(b, t)
    g.set_z_index(z)
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
    ratio: float,
    col: str,
    top_txt: str,
    sub_txt: str,
    z: int = 7,
) -> VGroup:
    p = np.array(pos, dtype=float)
    bg_ring = Circle(radius=radius, fill_color=C_BG_SUB, fill_opacity=0.92, stroke_color=C_SLATE, stroke_width=3.2).move_to(p).set_z_index(z)
    arc = Arc(
        radius=radius,
        start_angle=math.pi / 2,
        angle=-2 * math.pi * min(max(ratio, 0.05), 1.0),
        color=col,
        stroke_width=4.2,
    ).move_center_to_arc_center if False else Arc(
        radius=radius,
        start_angle=math.pi / 2,
        angle=-2 * math.pi * min(max(ratio, 0.05), 1.0),
        color=col,
        stroke_width=4.2,
    )
    arc.shift(p - arc.get_arc_center()).set_z_index(z + 1)
    t1 = txt(top_txt, size=11.0, color=col, bold=True, z=z + 2)
    t2 = txt(sub_txt, size=9.6, color=C_INK_1, z=z + 2)
    tg = fit(VGroup(t1, t2).arrange(DOWN, buff=0.04), max_w=radius * 1.68).move_to(p)
    return VGroup(bg_ring, arc, tg)


def build_canvas() -> VGroup:
    bg = VGroup()
    base = Rectangle(width=15.0, height=8.6, fill_color=C_BG, fill_opacity=1.0, stroke_width=0)
    bg.add(base)

    grid = VGroup()
    for x in np.arange(-6.5, 6.6, 1.0):
        grid.add(Line([x, -3.28, 0], [x, 3.28, 0], color=C_GRID, stroke_width=0.7, stroke_opacity=0.32))
    for y in np.arange(-3.0, 3.1, 1.0):
        grid.add(Line([-7.1, y, 0], [7.1, y, 0], color=C_GRID, stroke_width=0.7, stroke_opacity=0.32))
    bg.add(grid)

    top_bar = Rectangle(width=14.6, height=0.72, fill_color="#06090D", fill_opacity=0.96, stroke_width=0).move_to([0, 3.64, 0])
    bot_bar = Rectangle(width=14.6, height=0.72, fill_color="#06090D", fill_opacity=0.96, stroke_width=0).move_to([0, -3.64, 0])
    top_line = Line([-7.15, 3.28, 0], [7.15, 3.28, 0], color=C_SLATE, stroke_width=1.1)
    bot_line = Line([-7.15, -3.28, 0], [7.15, -3.28, 0], color=C_SLATE, stroke_width=1.1)
    bg.add(top_bar, bot_bar, top_line, bot_line)
    bg.set_z_index(0)
    return bg


class PostLifeBaseScene(Scene):
    def make_hud(self, ch_num: int, title: str, subtitle: str) -> tuple[VGroup, VGroup, VGroup]:
        is_finale = ch_num == TOTAL_CHAPTERS
        badge = RoundedRectangle(
            corner_radius=0.05,
            width=0.68,
            height=0.30,
            fill_color=C_GOLD if is_finale else C_CYAN_DIM,
            fill_opacity=0.95,
            stroke_color=C_GOLD if is_finale else C_CYAN,
            stroke_width=1.2,
        )
        b_txt = txt(f"{ch_num}장", size=13, color=C_DARK_INK if is_finale else C_CYAN, bold=True, z=21).move_to(badge)
        tag = VGroup(badge.set_z_index(20), b_txt)
        t_mob = txt(title, size=17.0, color=C_INK_0, bold=True, z=21)
        left = VGroup(tag, t_mob).arrange(RIGHT, buff=0.16)
        fit(left, max_w=7.65)
        left.move_to([-6.18 + left.width / 2, 3.63, 0]).set_z_index(20)

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
        app_lbl = txt("우체국보험 상품·청약 판단 지원", size=12.6, color=C_INK_2, z=21)
        right = VGroup(app_lbl, dots).arrange(RIGHT, buff=0.16)
        right.move_to([6.18 - right.width / 2, 3.63, 0]).set_z_index(20)

        sub_mob = fit(txt(subtitle, size=15.6, color=C_INK_1, bold=False, z=21), max_w=12.4)
        sub_mob.move_to([0, -3.63, 0])
        bot = VGroup(sub_mob).set_z_index(20)
        return left, right, bot

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
        self.play(
            FadeOut(outgoing_stage, shift=UP * 0.12, run_time=0.50),
            Succession(FadeOut(hl, shift=UP * 0.05, run_time=0.22), FadeIn(nl, shift=UP * 0.05, run_time=0.28)),
            ReplacementTransform(hr[1], nr[1], run_time=0.50),
            FadeOut(hr[0], run_time=0.25),
            FadeIn(nr[0], run_time=0.25),
            Succession(FadeOut(hb, shift=DOWN * 0.05, run_time=0.22), FadeIn(nb, shift=UP * 0.05, run_time=0.28)),
        )
        self.remove(outgoing_stage)
        return nl, nr, nb

    def fade_out_part(self, stage: Mobject, hl: VGroup, hr: VGroup, hb: VGroup) -> None:
        self.play(
            FadeOut(stage, shift=UP * 0.10),
            FadeOut(hl, shift=UP * 0.05),
            FadeOut(hr, shift=UP * 0.05),
            FadeOut(hb, shift=DOWN * 0.05),
            run_time=0.45,
        )
        self.remove(stage, hl, hr, hb)
        self.wait(0.10)

    def update_subtitle(self, hb: VGroup, new_sub: str, rt: float = 0.38) -> VGroup:
        new_mob = fit(txt(new_sub, size=15.6, color=C_INK_1, bold=False, z=21), max_w=12.4).move_to([0, -3.63, 0])
        nb = VGroup(new_mob).set_z_index(20)
        self.play(Succession(FadeOut(hb, run_time=rt * 0.45), FadeIn(nb, run_time=rt * 0.55)))
        self.remove(hb)
        return nb

    def check_bounds(self, m: Mobject, name: str) -> None:
        lx, rx = m.get_left()[0], m.get_right()[0]
        by, ty = m.get_bottom()[1], m.get_top()[1]
        if lx < -6.38 or rx > 6.38 or by < -3.24 or ty > 3.24:
            print(f"[BOUNDS WARNING] {name}: x=[{lx:.2f}, {rx:.2f}], y=[{by:.2f}, {ty:.2f}]")
