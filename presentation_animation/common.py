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
    t1 = txt(top_txt, size=11.0, color=col, bold=True, z=z + 2)
    t2 = txt(sub_txt, size=9.6, color=C_INK_1, z=z + 2)
    tg = fit(VGroup(t1, t2).arrange(DOWN, buff=0.04), max_w=radius * 1.68).move_to(p)
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
) -> Prism:
    """바닥 높이 base_z 에서 위로 솟는 삼차원 기둥."""
    eff_h = max(h, 0.04)
    return Prism(
        dimensions=[w, d, eff_h],
        fill_color=col,
        fill_opacity=opacity,
        stroke_color=stroke_col if stroke_col is not None else col,
        stroke_width=sw,
    ).move_to([x, y, base_z + eff_h / 2])


def glass_plane_3d(
    cx: float,
    cy: float,
    z_val: float,
    w: float,
    d: float,
    col: str,
    fill_op: float = 0.16,
    sw: float = 2.0,
) -> RoundedRectangle:
    """삼차원 공간을 가로지르는 반투명 수평 기준면."""
    return RoundedRectangle(
        corner_radius=0.10,
        width=w,
        height=d,
        fill_color=col,
        fill_opacity=fill_op,
        stroke_color=col,
        stroke_width=sw,
        stroke_opacity=0.90,
    ).move_to([cx, cy, z_val])


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
    """고정 상하단 자막 바와 카메라 이동 도우미를 갖춘 장면."""

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

        cam.get_cairo_context = _origin_locked_get_cairo_context  # type: ignore[method-assign]
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
            corner_radius=0.05,
            width=0.68,
            height=0.30,
            fill_color=C_GOLD if is_finale else C_CYAN_DIM,
            fill_opacity=0.95,
            stroke_color=C_GOLD if is_finale else C_CYAN,
            stroke_width=1.2,
        )
        b_txt = txt(f"{ch_num}장", size=13, color=C_DARK_INK if is_finale else C_CYAN, bold=True, z=32).move_to(badge)
        tag = VGroup(badge.set_z_index(31), b_txt)
        t_mob = txt(title, size=17.0, color=C_INK_0, bold=True, z=32)
        left = VGroup(tag, t_mob).arrange(RIGHT, buff=0.16)
        fit(left, max_w=7.65)
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
        app_lbl = txt("우체국보험 상품·청약 판단 지원", size=12.6, color=C_INK_2, z=32)
        right = VGroup(app_lbl, dots).arrange(RIGHT, buff=0.16)
        right.move_to([6.18 - right.width / 2, 3.63, 0]).set_z_index(31)

        sub_mob = fit(txt(subtitle, size=15.6, color=C_INK_1, bold=False, z=32), max_w=12.4)
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

    def update_subtitle(self, hb: VGroup, new_sub: str, rt: float = 0.38) -> VGroup:
        new_mob = fit(txt(new_sub, size=15.6, color=C_INK_1, bold=False, z=32), max_w=12.4).move_to([0, -3.63, 0])
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
