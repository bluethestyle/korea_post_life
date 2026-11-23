from __future__ import annotations

import math
import numpy as np
from manim import *

from common import (
    C_AMBER,
    C_BG_SUB,
    C_CORAL,
    C_CORAL_DIM,
    C_CYAN,
    C_DARK_INK,
    C_GOLD,
    C_GOLD_DEEP,
    C_INK_0,
    C_INK_1,
    C_INK_2,
    C_MINT,
    C_PANEL,
    C_PANEL_HI,
    C_SLATE,
    C_VIOLET,
    C_WHITE,
    PostLifeBaseScene,
    arrow_2d,
    fit,
    glow_dot,
    pill,
    txt,
)


class Part3DecisionScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        # ===================================================================
        # 5장 [~43s]: 쉬운 원리 설명 — 글짓기 AI vs 객관식 채점 전용 AI (Jev · decision-1)
        # ===================================================================
        hl, hr, hb = self.make_hud(
            5,
            "새로운 채점 전용 AI — 글짓기 없이 정답 확률만 바로 찍는 원리",
            "기존 AI는 문장을 한 글자씩 지어내느라 느리고 말을 꾸며내지만, 새로 나온 채점 전용 AI는 객관식 확률만 바로 찍습니다",
        )

        # -------------------------------------------------------------------
        # Beat 5A: Ticking Generative Stopwatch & Wobble Wave -> Pan to Instant Jev Stamp!
        # -------------------------------------------------------------------
        gen_card = RoundedRectangle(
            corner_radius=0.09, width=4.16, height=4.52, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_CORAL, stroke_width=2.0
        ).move_to([-4.02, 0.05, 0]).set_z_index(3)
        gen_hdr = fit(pill("기존 글짓기형 AI (대화 · 작문용)", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.2), max_w=3.80).move_to([-4.02, 1.86, 0]).set_z_index(6)

        # Animated Latency Stopwatch inside Left Card
        sw_c = np.array([-5.38, 1.14, 0.0])
        sw_ring = Circle(radius=0.26, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_AMBER, stroke_width=2.0).move_to(sw_c).set_z_index(7)
        sw_hand = Line(sw_c, sw_c + UP * 0.21, color=C_CORAL, stroke_width=2.4).set_z_index(8)

        gen_tok_row = fit(
            VGroup(
                pill('"이"', fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.6, px=0.08, py=0.04),
                pill('"특약은"', fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.6, px=0.08, py=0.04),
                pill('"아마..."', fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=10.6, px=0.08, py=0.04),
                pill('"면책?"', fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.6, px=0.08, py=0.04),
            ).arrange(RIGHT, buff=0.07),
            max_w=3.05,
        ).move_to([-3.52, 1.14, 0]).set_z_index(6)

        wob_fn = ParametricFunction(
            lambda u: np.array([-5.65 + u * 3.26, 0.28 + 0.24 * math.sin(10.0 * u) * math.sin(3.2 * u + 0.4), 0.0]),
            t_range=[0, 1, 0.02],
            color=C_CORAL,
            stroke_width=2.8,
        ).set_z_index(6)
        wob_lbl = fit(txt("문장을 한 글자씩 지어냄 → 느림(3.8초↑) · 글자당 요금", size=9.8, color=C_CORAL, bold=True, z=6), max_w=3.82).move_to([-4.02, -0.22, 0])

        gen_gauges = fit(
            VGroup(
                pill("느리고 비쌈 ↑", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.8, px=0.10, py=0.05),
                pill("답변 양식 깨짐 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.8, px=0.10, py=0.05),
                pill("없는 말 지어냄 !", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.8, px=0.10, py=0.05),
            ).arrange(RIGHT, buff=0.10),
            max_w=3.82,
        ).move_to([-4.02, -0.92, 0]).set_z_index(6)
        gen_foot = fit(pill("맞는지 틀리는지 채점하기엔 비효율적", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=10.0, z=6), max_w=3.82).move_to([-4.02, -1.64, 0])
        gen_grp = VGroup(gen_card, gen_hdr, sw_ring, sw_hand, gen_gauges, gen_foot)

        shift_arrow = arrow_2d([-1.82, 0.05, 0], [-0.96, 0.05, 0], color=C_GOLD, sw=2.8, tip=0.15, z=8)
        shift_lbl = pill("글짓기 생략!", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.8, px=0.09, py=0.04, z=9).move_to([-1.39, 0.48, 0])

        jev_card = RoundedRectangle(
            corner_radius=0.09, width=6.92, height=4.52, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=2.2
        ).move_to([2.62, 0.05, 0]).set_z_index(3)
        jev_top_row = fit(
            VGroup(
                pill("2026.09 TypeSafe AI", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, px=0.11, py=0.04),
                txt("객관식 채점 전용 AI 'Jev' 등장", size=14.0, color=C_GOLD, bold=True, z=7),
            ).arrange(RIGHT, buff=0.18),
            max_w=6.45,
        ).move_to([2.62, 1.86, 0]).set_z_index(7)

        jev_in = pill("약관 1번 읽기", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=10.6, px=0.11, py=0.06, z=7).move_to([0.22, 0.84, 0])
        jev_core = RoundedRectangle(
            corner_radius=0.08, width=1.92, height=0.98, fill_color="#1D2736", fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.2
        ).move_to([2.26, 0.84, 0]).set_z_index(6)
        jev_core_t = fit(
            VGroup(
                txt("Jev 즉시 채점", size=11.8, color=C_GOLD, bold=True, z=7),
                txt("0.05초 · 설명글 0글자", size=9.6, color=C_MINT, bold=True, z=7),
            ).arrange(DOWN, buff=0.05),
            max_w=1.76,
        ).move_to(jev_core)
        jev_in_arr = arrow_2d(jev_in.get_right(), jev_core.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=7)

        jev_bars, jev_out_arrs = VGroup(), VGroup()
        for b_i, (by, b_lbl, b_val, b_w, b_col) in enumerate(
            [(1.18, "보기 A", "94%", 1.12, C_GOLD), (0.84, "보기 B", "4%", 0.14, C_SLATE), (0.50, "보기 C", "2%", 0.08, C_SLATE)]
        ):
            jev_out_arrs.add(arrow_2d(jev_core.get_right(), [3.42, by, 0], color=C_GOLD if b_i == 0 else C_SLATE, sw=1.7, tip=0.09, z=6))
            lt = txt(b_lbl, size=10.0, color=C_INK_1 if b_i > 0 else WHITE, bold=(b_i == 0), z=7).move_to([3.82, by, 0])
            br = Rectangle(width=b_w, height=0.17, fill_color=b_col, fill_opacity=0.95, stroke_width=0).move_to([4.26 + b_w / 2, by, 0]).set_z_index(7)
            vt = txt(b_val, size=10.2, color=C_GOLD if b_i == 0 else C_INK_2, bold=(b_i == 0), z=7).next_to(br, RIGHT, buff=0.08)
            jev_bars.add(VGroup(lt, br, vt))

        jev_div = Line([-0.55, 0.06, 0], [5.80, 0.06, 0], color=C_SLATE, stroke_width=1.2).set_z_index(5)
        jev_use_hdr = txt("어디에 쓰면 좋을까? — 4가지 실무 활용처", size=11.2, color=C_WHITE, bold=True, z=7).move_to([2.62, -0.24, 0])

        def app_tile(tx: float, ty: float, col: str, icon_g: VGroup, label_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.06, width=3.06, height=0.66, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=col, stroke_width=1.6
            ).move_to([tx, ty, 0]).set_z_index(6)
            icon_g.move_to([tx - 1.15, ty, 0]).set_z_index(8)
            lb = fit(txt(label_s, size=10.2, color=col, bold=True, z=8), max_w=2.24).move_to([tx + 0.24, ty, 0])
            return VGroup(bx, icon_g, lb)

        ic_u1 = VGroup(
            arrow_2d([-0.16, 0, 0], [0.14, 0.14, 0], color=C_CYAN, sw=1.8, tip=0.07),
            arrow_2d([-0.16, 0, 0], [0.14, -0.14, 0], color=C_CYAN, sw=1.8, tip=0.07),
        )
        ic_u2 = VGroup(
            RegularPolygon(n=6, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.6).scale(0.18),
            txt("✓", size=9.5, color=C_GOLD, bold=True),
        )
        ic_u3 = VGroup(
            *[
                Rectangle(width=0.09, height=0.24, fill_color=c, fill_opacity=0.9, stroke_width=0).move_to([-0.12 + i * 0.12, 0, 0])
                for i, c in enumerate([C_MINT, C_CYAN, C_GOLD])
            ]
        )
        ic_u4 = VGroup(Circle(radius=0.16, fill_opacity=0.0, stroke_color=C_VIOLET, stroke_width=1.6), Dot([0, 0, 0], radius=0.05, color=C_GOLD))

        jev_uses = VGroup(
            app_tile(1.02, -0.82, C_CYAN, ic_u1, "① 어느 담당으로 보낼지 분류"),
            app_tile(4.24, -0.82, C_GOLD, ic_u2, "② 약관·규정에 맞는지 점검"),
            app_tile(1.02, -1.62, C_MINT, ic_u3, "③ 수천 건 문서 종류 나누기"),
            app_tile(4.24, -1.62, C_VIOLET, ic_u4, "④ 받아쓴 내용이 맞는지 채점"),
        )

        # Open zoomed onto Left Generative AI: Stopwatch spins 2 full turns while words print one by one
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES, zoom=1.30, frame_center=[-4.02, 0.05, 0])
        self.add(sw_hand)
        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(VGroup(gen_card, gen_hdr, sw_ring, gen_gauges, gen_foot), shift=RIGHT * 0.12),
                Rotate(sw_hand, angle=-2 * TAU, about_point=sw_c),
                LaggedStart(*[FadeIn(tk, shift=RIGHT * 0.08) for tk in gen_tok_row], lag_ratio=0.24),
                Create(wob_fn),
                FadeIn(wob_lbl),
            ],
            rt=1.40,
        )
        self.wait(0.75)

        # Pan Right to Jev: Instant Golden Flash stamps 94% probability bar with zero essay writing!
        self.cam_move(
            zoom=1.28,
            center=[2.45, 0.65, 0],
            anims=[
                GrowArrow(shift_arrow),
                FadeIn(shift_lbl, scale=0.85),
                FadeIn(VGroup(jev_card, jev_top_row, jev_in, jev_core, jev_core_t, jev_div, jev_use_hdr), shift=LEFT * 0.12),
                GrowArrow(jev_in_arr),
                Flash([2.26, 0.84, 0], color=C_GOLD, line_length=0.28, num_lines=10),
                LaggedStart(*[GrowArrow(oa) for oa in jev_out_arrs], lag_ratio=0.04),
                GrowFromEdge(jev_bars[0][1], LEFT),
                FadeIn(VGroup(jev_bars[0][0], jev_bars[0][2], jev_bars[1], jev_bars[2])),
            ],
            rt=1.25,
        )
        self.wait(0.80)

        self.reset_cam_2d(
            anims=[LaggedStart(*[FadeIn(u, shift=UP * 0.06, scale=0.95) for u in jev_uses], lag_ratio=0.08)],
            rt=1.05,
        )

        beat5a_all = VGroup(
            gen_grp,
            gen_tok_row,
            wob_fn,
            wob_lbl,
            shift_arrow,
            shift_lbl,
            jev_card,
            jev_top_row,
            jev_in,
            jev_in_arr,
            jev_core,
            jev_core_t,
            jev_out_arrs,
            jev_bars,
            jev_div,
            jev_use_hdr,
            jev_uses,
        )
        self.check_bounds(beat5a_all, "CH5A JEV INFOGRAPHIC")
        self.wait(1.90)

        # -------------------------------------------------------------------
        # Beat 5B: 3D Gyroscopic 'decision-1' Core -> Live 1,000-Q Burst & Honest Score Trace!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "2026년 11월 11일 구글이 출시한 decision-1은 두꺼운 약관을 통째로 읽고, 한 번에 1,000문제를 정직한 점수로 채점합니다",
            rt=0.40,
        )

        tl_bar = fit(
            VGroup(
                pill("2026.09 'Jev'가 채점 AI 개척", fg=C_INK_1, bg=C_PANEL, border=C_SLATE, size=10.6, z=8),
                arrow_2d([0, 0, 0], [0.55, 0, 0], color=C_GOLD, sw=2.2, tip=0.11, z=8),
                pill("2026.11.11 구글 'gemini-decision-1' 출시 (긴 약관 · 다문항 채점)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.8, z=8),
            ).arrange(RIGHT, buff=0.14),
            max_w=11.80,
        ).move_to([0.0, 2.58, 0]).set_z_index(8)

        d1_c = np.array([0.0, -0.18, 0.0])
        d1_ring = Circle(radius=1.08, fill_opacity=0.0, stroke_color=C_GOLD_DEEP, stroke_width=1.5).move_to(d1_c).set_z_index(6)
        d1_core = Circle(radius=0.94, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_VIOLET, stroke_width=3.0).move_to(d1_c).set_z_index(7)
        d1_txt = fit(
            VGroup(
                txt("decision-1", size=13.5, color=C_GOLD, bold=True, z=8),
                txt("설명글 0글자", size=10.4, color=C_MINT, bold=True, z=8),
                txt("하루 1만 번 무료", size=9.8, color=C_INK_1, z=8),
            ).arrange(DOWN, buff=0.06),
            max_w=1.62,
        ).move_to(d1_c)
        d1_hub_grp = VGroup(d1_ring, d1_core, d1_txt)

        orb_3d_a = (
            Circle(radius=1.24, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=1.8, stroke_opacity=0.72)
            .rotate(58 * DEGREES, axis=RIGHT)
            .rotate(24 * DEGREES, axis=UP)
            .move_to(d1_c)
        )
        orb_3d_b = (
            Circle(radius=1.24, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.8, stroke_opacity=0.72)
            .rotate(-54 * DEGREES, axis=RIGHT)
            .rotate(-26 * DEGREES, axis=UP)
            .move_to(d1_c)
        )
        d1_prism_3d = (
            Prism(dimensions=[0.58, 0.58, 0.58], fill_color=C_VIOLET, fill_opacity=0.24, stroke_color=C_GOLD, stroke_width=1.2)
            .rotate(PI / 4, axis=OUT)
            .move_to(d1_c + OUT * 0.36)
        )
        d1_3d_fx = VGroup(orb_3d_a, orb_3d_b, d1_prism_3d)

        def trait_quad(qx: float, qy: float, col: str, head_s: str, vis_g: VGroup, sub_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.08, width=4.35, height=1.96, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.0
            ).move_to([qx, qy, 0]).set_z_index(4)
            th = fit(txt(head_s, size=11.2, color=col, bold=True, z=7), max_w=4.05).move_to([qx, qy + 0.68, 0])
            vis_g.move_to([qx, qy - 0.02, 0]).set_z_index(7)
            ts = fit(txt(sub_s, size=9.4, color=C_INK_1, z=7), max_w=4.05).move_to([qx, qy - 0.70, 0])
            return VGroup(bx, th, vis_g, ts)

        tv1 = VGroup(
            pill("PDF 요약서", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.8, px=0.08, py=0.03).move_to([-1.10, 0.16, 0]),
            pill("표·그림 문서", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.8, px=0.08, py=0.03).move_to([-1.10, -0.20, 0]),
            arrow_2d([-0.40, 0.0, 0], [0.12, 0.0, 0], color=C_CYAN, sw=2.0, tip=0.09),
            pill("약 수백 쪽 분량", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.4, px=0.10, py=0.05).move_to([0.98, 0.0, 0]),
        )
        tq1 = trait_quad(-3.98, 1.02, C_CYAN, "특징 ① 두꺼운 문서·그림 통째로 입력", tv1, "글자와 표·그림이 섞인 긴 약관도 한 번에 읽음")

        q_dots = VGroup(*[Dot([0.15 + (k % 8) * 0.19, 0.24 - (k // 8) * 0.16, 0], radius=0.045, color=C_GOLD if k % 3 != 0 else C_MINT) for k in range(32)])
        tv2 = VGroup(
            pill("약관 1번", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.8, px=0.08, py=0.04).move_to([-1.18, 0.0, 0]),
            arrow_2d([-0.62, 0.0, 0], [-0.05, 0.0, 0], color=C_GOLD, sw=2.2, tip=0.09),
            q_dots,
        )
        tq2 = trait_quad(3.98, 1.02, C_GOLD, "특징 ② 한 번 읽고 최대 1,000문제 동시 채점", tv2, "같은 약관을 여러 번 보낼 필요 없이 한꺼번에 채점")

        tv3 = VGroup(
            pill("예 / 아니오", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.8, px=0.09, py=0.05),
            pill("객관식 고르기", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.8, px=0.09, py=0.05),
            pill("1~5점 척도", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.09, py=0.05),
        ).arrange(RIGHT, buff=0.12)
        tq3 = trait_quad(-3.98, -1.38, C_VIOLET, "특징 ③ 정해진 객관식 답만 반환", tv3, "정해진 보기 점수만 돌려줘 답변 깨짐 0건")

        cal_ax_x = Line([-1.15, -0.30, 0], [0.35, -0.30, 0], color=C_SLATE, stroke_width=1.6)
        cal_ax_y = Line([-1.15, -0.30, 0], [-1.15, 0.34, 0], color=C_SLATE, stroke_width=1.6)
        cal_diag = DashedLine([-1.15, -0.30, 0], [0.25, 0.30, 0], dash_length=0.06, color=C_MINT, stroke_width=1.8)
        cal_pts = VGroup(*[Dot([-1.05 + k * 0.30, -0.26 + k * 0.13, 0], radius=0.048, color=C_GOLD) for k in range(5)])
        tv4 = VGroup(
            cal_ax_x,
            cal_ax_y,
            cal_diag,
            cal_pts,
            pill("90점 = 90% 정답", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.09, py=0.04).move_to([1.12, 0.0, 0]),
        )
        tq4 = trait_quad(3.98, -1.38, C_MINT, "특징 ④ 점수가 곧 실제 정답 확률", tv4, "'90점'이면 실제로도 10번 중 9번 맞아 믿고 분류")

        spokes_5b = VGroup(
            arrow_2d(d1_c + np.array([-0.82, 0.55, 0]), [-1.78, 0.85, 0], color=C_CYAN, sw=2.0, tip=0.10, z=6),
            arrow_2d(d1_c + np.array([0.82, 0.55, 0]), [1.78, 0.85, 0], color=C_GOLD, sw=2.0, tip=0.10, z=6),
            arrow_2d(d1_c + np.array([-0.82, -0.55, 0]), [-1.78, -1.20, 0], color=C_VIOLET, sw=2.0, tip=0.10, z=6),
            arrow_2d(d1_c + np.array([0.82, -0.55, 0]), [1.78, -1.20, 0], color=C_MINT, sw=2.0, tip=0.10, z=6),
        )

        self.cam_move(
            phi=44 * DEGREES,
            theta=-62 * DEGREES,
            zoom=0.88,
            center=[0.0, -0.15, 0.10],
            anims=[
                FadeOut(beat5a_all, shift=UP * 0.10),
                FadeIn(d1_hub_grp, scale=0.85),
                FadeIn(d1_3d_fx, scale=0.80),
                LaggedStart(*[GrowArrow(sp) for sp in spokes_5b], lag_ratio=0.07),
                LaggedStart(*[FadeIn(tq, scale=0.94) for tq in [tq1, tq2, tq3, tq4]], lag_ratio=0.09),
            ],
            rt=1.25,
        )
        self.remove(beat5a_all)
        self.cam_move(
            theta=-50 * DEGREES,
            anims=[Rotate(orb_3d_a, angle=PI / 3, axis=OUT), Rotate(orb_3d_b, angle=-PI / 3, axis=OUT)],
            rt=0.90,
        )

        # Zoom into Right Quadrants: Ripple across 1,000-Q Dot Matrix & Trace Honest Score Line!
        cal_runner = glow_dot(cal_diag.get_start(), color=C_GOLD, r=0.06, z=14)
        self.add(cal_runner)
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.32,
            center=[3.85, -0.18, 0],
            anims=[
                FadeOut(d1_3d_fx),
                LaggedStart(*[Indicate(d, color=WHITE, scale_factor=1.6) for d in q_dots], lag_ratio=0.02),
                MoveAlongPath(cal_runner, Line(cal_diag.get_start(), cal_diag.get_end())),
                Circumscribe(tq2[0], color=C_GOLD, stroke_width=2.0, buff=0.03),
                Circumscribe(tq4[0], color=C_MINT, stroke_width=2.0, buff=0.03),
            ],
            rt=1.25,
        )
        self.remove(d1_3d_fx, cal_runner)
        self.wait(0.80)

        self.reset_cam_2d(anims=[FadeIn(tl_bar, shift=DOWN * 0.08)], rt=0.90)

        ch5_stage = VGroup(tl_bar, d1_hub_grp, spokes_5b, tq1, tq2, tq3, tq4)
        self.check_bounds(ch5_stage, "CH5B RADIAL TRAITS")
        self.wait(1.95)

        # ===================================================================
        # 6장 [~47s]: 검증·분류 단계 — 애매한 점수와 1분 글자 수 제한을 해결한 방법
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch5_stage,
            hl,
            hr,
            hb,
            6,
            "검증·분류 단계 — 애매한 점수와 1분 글자 수 제한을 해결한 방법",
            "실제로 써보니 점수가 애매하게 뭉치고, 여러 특약을 묶으면 오류가 숨고, 1분 글자 수 한도가 넘치는 문제가 생겼습니다",
        )
        print(f"[TIMING] Ch5 end: {self.renderer.time:.2f}s")

        # -------------------------------------------------------------------
        # Beat 6A: Kinetic 3-Stop Camera Pan across Colliding Curves, Sneaking Bundle, & Bursting Thermometer!
        # -------------------------------------------------------------------
        top_res_6 = fit(
            pill("주어진 조건 : 하루 1만 번 무료로 넉넉하지만, '1분에 읽을 수 있는 글자량(5만 단위)' 제한이 있음", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.0, z=9),
            max_w=11.80,
        ).move_to([0.0, 2.58, 0])

        def col_diag_card(cx: float, col: str, title_s: str, foot_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.09, width=3.76, height=4.28, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.1
            ).move_to([cx, -0.08, 0]).set_z_index(4)
            th = fit(txt(title_s, size=11.5, color=col, bold=True, z=7), max_w=3.44).move_to([cx, 1.66, 0])
            tf = fit(txt(foot_s, size=9.6, color=C_INK_1, z=7), max_w=3.44).move_to([cx, -1.74, 0])
            return VGroup(bx, th, tf)

        c6_1 = col_diag_card(-4.02, C_AMBER, "문제 ① '맞나요?' 물으면 점수가 애매함", "맞는 내용도 50~80점 사이에 몰려 구분 어려움")
        ax_c1 = Line([-5.55, -0.95, 0], [-2.50, -0.95, 0], color=C_SLATE, stroke_width=1.8).set_z_index(5)
        zone_mush = Rectangle(width=1.55, height=1.85, fill_color=C_AMBER, fill_opacity=0.18, stroke_color=C_AMBER, stroke_width=1.3).move_to([-3.85, -0.02, 0]).set_z_index(5)
        curve_t = ParametricFunction(
            lambda u: np.array([-5.40 + u * 2.75, -0.95 + 1.45 * math.exp(-(((u - 0.58) / 0.22) ** 2)), 0]),
            t_range=[0, 1, 0.02],
            color=C_GOLD,
            stroke_width=2.8,
        ).set_z_index(7)
        curve_f = ParametricFunction(
            lambda u: np.array([-5.40 + u * 2.75, -0.95 + 1.30 * math.exp(-(((u - 0.44) / 0.22) ** 2)), 0]),
            t_range=[0, 1, 0.02],
            color=C_CORAL,
            stroke_width=2.6,
        ).set_z_index(7)
        lbl_mush = pill("50~80점 애매 구간 !", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.2, px=0.09, py=0.03, z=8).move_to([-3.85, 1.08, 0])
        lbl_ax_c1 = txt("0점         50점  80점       100점", size=8.6, color=C_INK_2, z=6).move_to([-4.02, -1.20, 0])

        c6_2 = col_diag_card(0.0, C_CORAL, "문제 ② 여러 특약을 묶어 물으면 오류가 숨음", "틀린 특약 2개가 정상 특약 사이에 묻혀 통과")
        bundle_loop = DashedVMobject(Circle(radius=0.92, fill_opacity=0.0, stroke_color=C_AMBER, stroke_width=2.2).move_to([-0.38, 0.10, 0]), num_dashes=22).set_z_index(6)
        b_d1 = pill("정상 특약 ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, 0.62, 0])
        b_d2 = pill("정상 특약 ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, 0.24, 0])
        b_d3 = pill("틀린 특약 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, -0.14, 0])
        b_d4 = pill("틀린 특약 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, -0.52, 0])
        leak_arr = arrow_2d([0.58, 0.10, 0], [1.02, 0.10, 0], color=C_CORAL, sw=2.0, tip=0.09, z=7)
        leak_stamp = pill("80점\n통과?!", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.6, px=0.10, py=0.06, z=8).move_to([1.42, 0.10, 0])

        c6_3 = col_diag_card(4.02, C_VIOLET, "문제 ③ 약관을 매번 넣으면 1분 한도 폭발", "한도를 넘어 대기 줄 처리에 203분이나 밀림")
        therm_bg = RoundedRectangle(
            corner_radius=0.06, width=0.68, height=2.28, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.6
        ).move_to([3.28, 0.02, 0]).set_z_index(5)
        therm_fill = RoundedRectangle(corner_radius=0.05, width=0.56, height=2.14, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([3.28, -0.05, 0]).set_z_index(6)
        lim_50k = DashedLine([2.62, 0.28, 0], [5.42, 0.28, 0], dash_length=0.07, color=WHITE, stroke_width=2.2).set_z_index(8)
        lim_lbl = txt("1분 한도선", size=9.4, color=WHITE, bold=True, z=8).move_to([4.68, 0.50, 0])
        spike_tag = pill("한도 1.6배 초과 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.4, px=0.09, py=0.04, z=8).move_to([4.65, 1.02, 0])
        delay_tag = pill("203분 대기 !", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.4, px=0.09, py=0.04, z=8).move_to([4.65, -0.48, 0])

        # Stop 1: Zoom onto Overlapping Curves in Column 1!
        self.cam_move(
            zoom=1.36,
            center=[-3.80, -0.08, 0],
            anims=[
                FadeIn(top_res_6, shift=DOWN * 0.08),
                FadeIn(VGroup(c6_1, ax_c1, zone_mush, lbl_ax_c1)),
                Create(curve_t),
                Create(curve_f),
                FadeIn(lbl_mush, scale=1.15),
                FadeIn(VGroup(c6_2, bundle_loop, b_d1, b_d2, b_d3, b_d4)),
                FadeIn(VGroup(c6_3, therm_bg, lim_50k, lim_lbl)),
            ],
            rt=1.15,
        )
        self.wait(0.75)

        # Stop 2: Pan Right across Sneaking Bundle -> Bursting 1-Minute Limit Thermometer!
        self.cam_move(
            zoom=1.38,
            center=[2.15, -0.08, 0],
            anims=[
                Rotate(bundle_loop, angle=PI / 2),
                GrowArrow(leak_arr),
                FadeIn(leak_stamp, scale=1.35),
                GrowFromEdge(therm_fill, DOWN),
                Flash([3.28, 0.95, 0], color=C_CORAL, line_length=0.25, num_lines=10),
                FadeIn(spike_tag, shift=UP * 0.08),
                FadeIn(delay_tag),
            ],
            rt=1.25,
        )
        self.wait(0.80)
        self.reset_cam_2d(rt=0.85)

        beat6a_all = VGroup(
            top_res_6,
            c6_1,
            ax_c1,
            zone_mush,
            curve_t,
            curve_f,
            lbl_mush,
            lbl_ax_c1,
            c6_2,
            bundle_loop,
            b_d1,
            b_d2,
            b_d3,
            b_d4,
            leak_arr,
            leak_stamp,
            c6_3,
            therm_bg,
            therm_fill,
            lim_50k,
            lim_lbl,
            spike_tag,
            delay_tag,
        )
        self.check_bounds(beat6a_all, "CH6A VISUAL BOTTLENECKS")
        self.wait(1.75)

        # -------------------------------------------------------------------
        # Beat 6B: 3D Score Column Landscape -> Golden 3D Spire ("있음 vs 없음")!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ①·② 약관은 1번만 보내되 까다로운 조건은 1개씩 따로 묻고, '있음 vs 없음' 양자택일로 점수를 확실히 갈랐습니다",
            rt=0.40,
        )

        batch_card = RoundedRectangle(
            corner_radius=0.09, width=4.38, height=4.52, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-3.88, 0.05, 0]).set_z_index(4)
        batch_hdr = fit(txt("해결 ① 약관은 1번만 · 조건은 1개씩 질문", size=12.6, color=C_CYAN, bold=True, z=7), max_w=4.02).move_to([-3.88, 1.88, 0])

        in_node_6b = pill("약관 1번", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.8, px=0.10, py=0.05, z=8).move_to([-5.32, 0.18, 0])
        fan_targets = VGroup(
            pill("금액·면책 4항목 동시 채점", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.4, px=0.09, py=0.04, z=8).move_to([-3.12, 1.12, 0]),
            pill("76가지 공통 보장 짝짓기", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.4, px=0.09, py=0.04, z=8).move_to([-3.12, 0.50, 0]),
            pill("가입 제한 조건은 1개씩 질문", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.2, px=0.09, py=0.04, z=8).move_to([-3.12, -0.12, 0]),
            pill("주간 뉴스 중요도 분류", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=9.4, px=0.09, py=0.04, z=8).move_to([-3.12, -0.74, 0]),
        )
        fan_arrows = VGroup(*[arrow_2d(in_node_6b.get_right(), ft.get_left(), color=C_GOLD if idx == 2 else C_CYAN, sw=1.8, tip=0.08, z=7) for idx, ft in enumerate(fan_targets)])
        batch_foot = fit(txt("약관 반복 전송은 없애고, 숨기 쉬운 조건만 1개씩 검사", size=9.8, color=C_INK_1, z=7), max_w=4.04).move_to([-3.88, -1.68, 0])
        batch_grp = VGroup(batch_card, batch_hdr, in_node_6b, fan_targets, fan_arrows, batch_foot)

        spec_base_y = -1.18
        spec_axis = Line([-0.82, spec_base_y, 0], [5.85, spec_base_y, 0], color=C_INK_2, stroke_width=1.8).set_z_index(3)
        spec_y_axis = Line([-0.82, spec_base_y, 0], [-0.82, 2.05, 0], color=C_INK_2, stroke_width=1.8).set_z_index(3)
        spec_y_1 = txt("100점", size=10.2, color=C_INK_2, z=6).move_to([-1.24, 1.82, 0])
        spec_y_0 = txt("0점", size=10.2, color=C_INK_2, z=6).move_to([-1.24, spec_base_y, 0])
        spec_x_lbl = fit(txt("해결 ② 질문 방식 변경 : '맞나요?' 대신 '[조건 있음] vs [조건 없음]' 고르기", size=11.0, color=C_INK_1, z=6), max_w=6.80).move_to([2.48, -1.62, 0])

        n_bars, peak_idx = 24, 14
        bars_sharp = VGroup()
        prisms_mushy, prisms_sharp = VGroup(), VGroup()
        bx0, b_step = -0.58, 0.266
        for i in range(n_bars):
            bx = bx0 + i * b_step
            h_mush = 0.26 + 1.58 * math.exp(-((abs(i - 13.0) / 4.6) ** 2))
            z_mush = h_mush * 0.72
            pm = Prism(
                dimensions=[0.18, h_mush, z_mush],
                fill_color=C_AMBER,
                fill_opacity=0.68,
                stroke_color=C_AMBER,
                stroke_width=1.0,
            ).move_to([bx, spec_base_y + h_mush / 2, z_mush / 2])
            prisms_mushy.add(pm)

            if i == peak_idx:
                h1 = 2.54
                z1 = 1.58
                b1 = Rectangle(width=0.22, height=h1, fill_color=C_GOLD, fill_opacity=0.98, stroke_color=WHITE, stroke_width=1.3)
                ps = Prism(dimensions=[0.22, h1, z1], fill_color=C_GOLD, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.3).move_to(
                    [bx, spec_base_y + h1 / 2, z1 / 2]
                )
            elif abs(i - peak_idx) == 1:
                h1 = 0.13
                z1 = 0.10
                b1 = Rectangle(width=0.17, height=h1, fill_color=C_VIOLET, fill_opacity=0.45, stroke_width=0)
                ps = Prism(dimensions=[0.17, h1, z1], fill_color=C_VIOLET, fill_opacity=0.42, stroke_color=C_VIOLET, stroke_width=0.7).move_to(
                    [bx, spec_base_y + h1 / 2, z1 / 2]
                )
            else:
                h1 = 0.05
                z1 = 0.05
                b1 = Rectangle(width=0.17, height=h1, fill_color=C_SLATE, fill_opacity=0.40, stroke_width=0)
                ps = Prism(dimensions=[0.17, h1, z1], fill_color=C_SLATE, fill_opacity=0.35, stroke_color=C_SLATE, stroke_width=0.5).move_to(
                    [bx, spec_base_y + h1 / 2, z1 / 2]
                )
            b1.move_to([bx, spec_base_y + h1 / 2, 0]).set_z_index(5)
            bars_sharp.add(b1)
            prisms_sharp.add(ps)

        mushy_callout = fit(pill("바꾸기 전 ('맞나요?' 질문) → 50~80점대에 애매하게 뭉침", fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=11.4), max_w=6.80).move_to([2.48, 2.48, 0]).set_z_index(9)
        peak_callout = fit(
            pill('바꾼 뒤 ("있음 vs 없음" 선택) → 정답 94점↑ · 오답 6점↓ 확실히 분리!', fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.4),
            max_w=6.88,
        ).move_to([2.48, 2.48, 0]).set_z_index(9)
        calib_chip = fit(
            pill("검증 실험 : 일부러 틀리게 고친 437건을 넣었더니 통과된 건수 0건 (100% 차단 ✓)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=11.4),
            max_w=6.85,
        ).move_to([2.48, -2.35, 0])

        self.cam_move(
            phi=48 * DEGREES,
            theta=-58 * DEGREES,
            zoom=0.88,
            center=[0.45, -0.10, 0.25],
            anims=[
                FadeOut(beat6a_all, shift=UP * 0.10),
                FadeIn(VGroup(batch_card, batch_hdr, in_node_6b, batch_foot)),
                LaggedStart(*[GrowArrow(fa) for fa in fan_arrows], lag_ratio=0.06),
                LaggedStart(*[FadeIn(ft, shift=RIGHT * 0.08) for ft in fan_targets], lag_ratio=0.06),
                Create(spec_axis),
                Create(spec_y_axis),
                FadeIn(VGroup(spec_y_1, spec_y_0, spec_x_lbl)),
                FadeIn(prisms_mushy, lag_ratio=0.02),
                FadeIn(mushy_callout, shift=DOWN * 0.08),
            ],
            rt=1.25,
        )
        self.remove(beat6a_all)
        self.wait(0.75)

        self.cam_move(
            phi=42 * DEGREES,
            theta=-74 * DEGREES,
            zoom=0.90,
            center=[0.65, -0.05, 0.35],
            anims=[
                FadeOut(mushy_callout),
                FadeIn(peak_callout),
                ReplacementTransform(prisms_mushy, prisms_sharp),
            ],
            rt=1.20,
        )
        self.remove(mushy_callout)
        self.wait(0.75)

        self.reset_cam_2d(
            anims=[
                FadeOut(prisms_sharp),
                FadeIn(bars_sharp),
                FadeIn(calib_chip, shift=UP * 0.08),
            ],
            rt=0.90,
        )
        self.remove(prisms_sharp)

        beat6b_all = VGroup(batch_grp, spec_axis, spec_y_axis, spec_y_1, spec_y_0, spec_x_lbl, bars_sharp, peak_callout, calib_chip)
        self.check_bounds(beat6b_all, "CH6B POLARIZATION")
        self.wait(1.90)

        # -------------------------------------------------------------------
        # Beat 6C: 3-Tier Traffic-Light Gate + Live Sliding [1분 속도 조절기] Bracket!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ③·④ 점수대별 3단 신호등으로 잘못된 반영을 막고, '1분 속도 조절기'로 한도를 넘기지 않고 안정 운영합니다",
            rt=0.40,
        )

        nozzle = RoundedRectangle(
            corner_radius=0.08, width=1.52, height=1.06, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-5.15, 0.40, 0]).set_z_index(5)
        noz_txt = fit(
            VGroup(
                txt("해결 ③", size=10.8, color=C_CYAN, bold=True, z=7),
                txt("점수대별", size=12.4, color=C_VIOLET, bold=True, z=7),
                txt("3단 신호등", size=11.2, color=C_INK_1, z=7),
            ).arrange(DOWN, buff=0.03),
            max_w=1.34,
        ).move_to(nozzle)

        gate_x, th_high_y, th_low_y = -2.85, 1.25, -0.32
        meter_bar = Line([gate_x, -1.70, 0], [gate_x, 2.38, 0], color=C_SLATE, stroke_width=3.0).set_z_index(4)
        line_75 = DashedLine([-3.10, th_high_y, 0], [1.48, th_high_y, 0], dash_length=0.10, color=C_GOLD, stroke_width=1.7).set_z_index(3)
        line_40 = DashedLine([-3.10, th_low_y, 0], [1.48, th_low_y, 0], dash_length=0.10, color=C_CORAL, stroke_width=1.7).set_z_index(3)
        knob_75 = pill("75점 기준선", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.6, px=0.11, py=0.04).move_to([-2.85, th_high_y + 0.25, 0]).set_z_index(8)
        knob_40 = pill("40점 기준선", fg=WHITE, bg=C_CORAL, border=WHITE, size=10.6, px=0.11, py=0.04).move_to([-2.85, th_low_y - 0.25, 0]).set_z_index(8)

        z_top = RoundedRectangle(corner_radius=0.08, width=2.76, height=0.88, fill_color="#232B1E", fill_opacity=0.94, stroke_color=C_GOLD, stroke_width=2.1).move_to([0.12, 1.85, 0]).set_z_index(4)
        zt_lbl = fit(VGroup(txt("75점 이상 : 자동 통과", size=12.6, color=C_GOLD, bold=True, z=6), txt("검증된 기준표에 바로 반영", size=10.6, color=C_INK_1, z=6)).arrange(DOWN, buff=0.04), max_w=2.56).move_to(z_top)
        z_mid = RoundedRectangle(corner_radius=0.08, width=2.76, height=0.96, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_WHITE, stroke_width=2.1).move_to([0.12, 0.46, 0]).set_z_index(4)
        zm_lbl = fit(VGroup(txt("40~75점 : 사람이 직접 확인", size=12.0, color=C_WHITE, bold=True, z=6), txt("약관 몇 쪽인지 함께 표시", size=10.6, color=C_CYAN, z=6)).arrange(DOWN, buff=0.04), max_w=2.56).move_to(z_mid)
        excl_wall = Line([-1.05, -1.55, 0], [-1.05, -0.70, 0], color=C_CORAL, stroke_width=4.6).set_z_index(6)
        excl_lbl = fit(
            VGroup(txt("40점 미만 : 탈락 · 다시 읽기", size=11.8, color=C_CORAL, bold=True, z=6), txt("오류의 95.9% 포착 · 반영 차단", size=10.2, color=C_INK_1, z=6)).arrange(DOWN, buff=0.04),
            max_w=2.70,
        ).move_to([0.35, -1.12, 0])

        retry_arc = CubicBezier(
            np.array([-1.55, -1.08, 0]), np.array([-2.05, -2.05, 0]), np.array([-4.05, -2.05, 0]), np.array([-4.42, -0.08, 0]), color=C_VIOLET, stroke_width=2.0
        ).set_z_index(4)
        retry_lbl = pill("다른 AI로 다시 읽기", fg=C_VIOLET, bg=C_PANEL, border=C_VIOLET, size=10.2, px=0.10, py=0.04).move_to([-2.95, -1.96, 0]).set_z_index(7)

        mkt_card = RoundedRectangle(
            corner_radius=0.09, width=3.96, height=4.34, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_VIOLET, stroke_width=2.2
        ).move_to([3.92, 0.25, 0]).set_z_index(4)
        mkt_title = fit(txt("주간 보험 뉴스 분류 & 1분 속도 조절기", size=12.0, color=C_VIOLET, bold=True, z=7), max_w=3.68).move_to([3.92, 2.04, 0])

        # Live Sliding [1분 속도 조절기] Bracket over 12 Request Bars!
        tok_bars_60 = VGroup(
            *[
                Rectangle(width=0.18, height=0.14 + (k % 3) * 0.08, fill_color=C_MINT if k % 2 == 0 else C_CYAN, fill_opacity=0.85, stroke_width=0)
                .move_to([2.35 + k * 0.28, 1.54, 0])
                .set_z_index(6)
                for k in range(12)
            ]
        )
        win_bracket = RoundedRectangle(corner_radius=0.04, width=1.62, height=0.40, fill_color="#1A5642", fill_opacity=0.45, stroke_color=C_GOLD, stroke_width=2.0).move_to([3.05, 1.54, 0]).set_z_index(8)
        safe_txt = fit(txt("1분 속도 조절기 : 한도 넘기 전 자동 조절 ✓", size=9.2, color=C_MINT, bold=True, z=8), max_w=3.54).move_to([3.92, 1.16, 0])

        sig_rows = VGroup()
        for sy, s_col, s_head, s_desc in [
            (0.60, C_GOLD, "◆ 타사 독점 신담보 출시", "배타적사용권 기간 · 만료일 추적"),
            (-0.16, C_CORAL, "▲ 주력 보장 경쟁 변화", "가입 한도 상향 · 심사 완화 포착"),
            (-0.92, C_MINT, "★ 우체국에 없는 새 보장", "우리가 안 파는 담보 → 신설 검토"),
        ]:
            sb = RoundedRectangle(corner_radius=0.06, width=3.54, height=0.62, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=s_col, stroke_width=1.7).move_to([3.92, sy, 0]).set_z_index(6)
            stg = fit(
                VGroup(txt(s_head, size=11.0, color=s_col, bold=True, z=7), txt(s_desc, size=9.6, color=C_INK_1, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.03),
                max_w=3.28,
            ).move_to(sb)
            sig_rows.add(VGroup(sb, stg))

        mkt_foot = fit(txt("처음 대량 약관은 교차 확인 · 매주 새 소식에 집중 활용", size=9.4, color=C_GOLD, bold=True, z=7), max_w=3.64).move_to([3.92, -1.56, 0])
        mkt_group = VGroup(mkt_card, mkt_title, tok_bars_60, win_bracket, safe_txt, sig_rows, mkt_foot)

        quota_bar = fit(
            pill("검증·분류 완성 : 틀린 내용 통과 0건 + 1분 속도 자동 조절로 멈춤 없이 안정 운영 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0),
            max_w=11.85,
        ).move_to([0.0, -2.58, 0]).set_z_index(9)

        self.play(
            FadeOut(beat6b_all, shift=UP * 0.10),
            FadeIn(VGroup(nozzle, noz_txt), shift=RIGHT * 0.12),
            Create(meter_bar),
            Create(line_75),
            Create(line_40),
            FadeIn(knob_75),
            FadeIn(knob_40),
            FadeIn(VGroup(z_top, zt_lbl, z_mid, zm_lbl, excl_wall, excl_lbl)),
            Create(retry_arc),
            FadeIn(retry_lbl),
            FadeIn(mkt_group, shift=LEFT * 0.14),
            FadeIn(quota_bar, shift=UP * 0.08),
            run_time=1.10,
        )
        self.remove(beat6b_all)

        p_start = nozzle.get_right()
        particles, mkt_pulses = VGroup(), VGroup()
        stream_anims = []
        for k in range(5):
            end_y = 1.66 + (k % 3) * 0.19
            pt = glow_dot(p_start, color=C_GOLD, r=0.055, z=12)
            particles.add(pt)
            stream_anims.append(
                Succession(Wait(k * 0.08), MoveAlongPath(pt, CubicBezier(p_start, p_start + RIGHT * 1.1, np.array([-2.2, end_y, 0]), np.array([-1.28, end_y, 0])), run_time=0.98))
            )
        for k in range(3):
            end_y = 0.32 + (k % 2) * 0.26
            pt = glow_dot(p_start, color=C_CYAN, r=0.055, z=12)
            particles.add(pt)
            stream_anims.append(
                Succession(Wait(0.10 + k * 0.11), MoveAlongPath(pt, CubicBezier(p_start, p_start + RIGHT * 1.1, np.array([-2.2, end_y, 0]), np.array([-1.28, end_y, 0])), run_time=0.98))
            )
        for k, sy in enumerate([0.60, -0.16, -0.92]):
            mp = glow_dot([0.12, 1.85, 0], color=C_VIOLET, r=0.060, z=13)
            mkt_pulses.add(mp)
            stream_anims.append(
                Succession(
                    Wait(0.22 + k * 0.16),
                    MoveAlongPath(mp, CubicBezier(np.array([1.50, 1.85, 0]), np.array([1.85, sy + 0.4, 0]), np.array([1.85, sy, 0]), np.array([2.15, sy, 0])), run_time=0.90),
                )
            )

        blocked_pt = glow_dot(p_start, color=C_CORAL, r=0.058, z=12)
        rescue_pt = glow_dot(p_start, color=C_VIOLET, r=0.060, z=13)
        self.add(particles, mkt_pulses, blocked_pt, rescue_pt)

        # Zoom in onto the 3-Tier Traffic-Light Gate & Retry Loop while particles sort!
        self.cam_move(
            zoom=1.30,
            center=[-1.65, -0.12, 0],
            anims=[
                *stream_anims,
                MoveAlongPath(blocked_pt, CubicBezier(p_start, p_start + RIGHT * 1.0, np.array([-2.2, -1.08, 0]), np.array([-1.12, -1.08, 0])), run_time=0.90),
                MoveAlongPath(rescue_pt, CubicBezier(p_start, p_start + RIGHT * 0.9, np.array([-2.3, -1.08, 0]), np.array([-1.55, -1.08, 0])), run_time=0.80),
            ],
            rt=1.45,
        )
        self.wait(0.65)

        # Pan Right as the [1분 속도 조절기] Bracket glides smoothly across the request bars!
        self.cam_move(
            zoom=1.34,
            center=[2.65, 0.32, 0],
            anims=[
                FadeOut(blocked_pt, scale=0.3),
                FadeOut(mkt_pulses, scale=0.4),
                MoveAlongPath(rescue_pt, retry_arc, run_time=0.85),
                win_bracket.animate.move_to([4.78, 1.54, 0]),
                LaggedStart(*[Circumscribe(sr[0], color=C_GOLD, stroke_width=2.0, buff=0.03) for sr in sig_rows], lag_ratio=0.14),
            ],
            rt=1.15,
        )
        self.remove(blocked_pt, mkt_pulses, *mkt_pulses)
        self.wait(0.65)

        self.reset_cam_2d(
            anims=[
                MoveAlongPath(
                    rescue_pt,
                    CubicBezier(np.array([-4.42, -0.08, 0]), np.array([-3.2, 1.88, 0]), np.array([-2.0, 1.88, 0]), np.array([-1.28, 1.88, 0])),
                )
            ],
            rt=0.85,
        )

        ch6_stage = VGroup(
            nozzle,
            noz_txt,
            meter_bar,
            line_75,
            line_40,
            knob_75,
            knob_40,
            z_top,
            zt_lbl,
            z_mid,
            zm_lbl,
            excl_wall,
            excl_lbl,
            retry_arc,
            retry_lbl,
            particles,
            rescue_pt,
            mkt_group,
            quota_bar,
        )
        self.check_bounds(ch6_stage, "CH6C ROUTING & QUOTA")
        self.wait(2.10)
        print(f"[TIMING] Part 3 end: {self.renderer.time:.2f}s")

        self.fade_out_part(ch6_stage, hl, hr, hb)
