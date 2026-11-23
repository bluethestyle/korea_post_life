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
        # 5장 [~36s]: 기술 배경 — 지연 시계 vs 즉시 판정 패닝 & 3D 코어 · 보정 곡선 주행
        # ===================================================================
        hl, hr, hb = self.make_hud(
            5,
            "판정 전용 AI의 등장 — Jev가 연 패러다임과 Google decision-1 출시",
            "문장을 한 글자씩 생성하는 비효율을 없애고 선택지 확률만 즉시 산출하는 '판정 전용 AI' 분야가 열렸습니다",
        )

        # -------------------------------------------------------------------
        # Beat 5A: Ticking Generative Stopwatch & Wobble Wave -> Whip-Pan to Instant Jev Stamp!
        # -------------------------------------------------------------------
        gen_card = RoundedRectangle(
            corner_radius=0.09, width=4.16, height=4.52, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_CORAL, stroke_width=2.0
        ).move_to([-4.02, 0.05, 0]).set_z_index(3)
        gen_hdr = fit(pill("기존 생성형 AI (대화 · 작성 모델)", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.2), max_w=3.80).move_to([-4.02, 1.86, 0]).set_z_index(6)

        # Animated Latency Stopwatch inside Left Card!
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
        wob_lbl = txt("토큰 순차 생성 → 지연 3.8초 ↑ · 출력 과금", size=9.8, color=C_CORAL, bold=True, z=6).move_to([-4.02, -0.22, 0])

        gen_gauges = fit(
            VGroup(
                pill("지연·비용 ↑", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.8, px=0.10, py=0.05),
                pill("양식 깨짐 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.8, px=0.10, py=0.05),
                pill("환각 위험 !", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.8, px=0.10, py=0.05),
            ).arrange(RIGHT, buff=0.10),
            max_w=3.82,
        ).move_to([-4.02, -0.92, 0]).set_z_index(6)
        gen_foot = pill("진위 판별 · 분류 · 검수에는 비효율", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=10.0, z=6).move_to([-4.02, -1.64, 0])
        gen_grp = VGroup(gen_card, gen_hdr, sw_ring, sw_hand, gen_gauges, gen_foot)

        shift_arrow = arrow_2d([-1.82, 0.05, 0], [-0.96, 0.05, 0], color=C_GOLD, sw=2.8, tip=0.15, z=8)
        shift_lbl = pill("생성 제거", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.0, px=0.10, py=0.04, z=9).move_to([-1.39, 0.48, 0])

        jev_card = RoundedRectangle(
            corner_radius=0.09, width=6.92, height=4.52, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=2.2
        ).move_to([2.62, 0.05, 0]).set_z_index(3)
        jev_top_row = fit(
            VGroup(
                pill("2026.09 TypeSafe AI", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, px=0.11, py=0.04),
                txt("비생성 판정 전용 모델 'Jev' 등장", size=14.0, color=C_GOLD, bold=True, z=7),
            ).arrange(RIGHT, buff=0.18),
            max_w=6.45,
        ).move_to([2.62, 1.86, 0]).set_z_index(7)

        jev_in = pill("원문 1회 입력", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=10.6, px=0.11, py=0.06, z=7).move_to([0.22, 0.84, 0])
        jev_core = RoundedRectangle(
            corner_radius=0.08, width=1.88, height=0.98, fill_color="#1D2736", fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.2
        ).move_to([2.26, 0.84, 0]).set_z_index(6)
        jev_core_t = fit(
            VGroup(
                txt("Jev 즉시 판정", size=11.8, color=C_GOLD, bold=True, z=7),
                txt("0.05초 · 출력 토큰 0", size=9.8, color=C_MINT, bold=True, z=7),
            ).arrange(DOWN, buff=0.05),
            max_w=1.72,
        ).move_to(jev_core)
        jev_in_arr = arrow_2d(jev_in.get_right(), jev_core.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=7)

        jev_bars, jev_out_arrs = VGroup(), VGroup()
        for b_i, (by, b_lbl, b_val, b_w, b_col) in enumerate(
            [(1.18, "선택지 A", "0.94", 1.12, C_GOLD), (0.84, "선택지 B", "0.04", 0.14, C_SLATE), (0.50, "선택지 C", "0.02", 0.08, C_SLATE)]
        ):
            jev_out_arrs.add(arrow_2d(jev_core.get_right(), [3.42, by, 0], color=C_GOLD if b_i == 0 else C_SLATE, sw=1.7, tip=0.09, z=6))
            lt = txt(b_lbl, size=9.8, color=C_INK_1 if b_i > 0 else WHITE, bold=(b_i == 0), z=7).move_to([3.82, by, 0])
            br = Rectangle(width=b_w, height=0.17, fill_color=b_col, fill_opacity=0.95, stroke_width=0).move_to([4.26 + b_w / 2, by, 0]).set_z_index(7)
            vt = txt(b_val, size=10.0, color=C_GOLD if b_i == 0 else C_INK_2, bold=(b_i == 0), z=7).next_to(br, RIGHT, buff=0.08)
            jev_bars.add(VGroup(lt, br, vt))

        jev_div = Line([-0.55, 0.06, 0], [5.80, 0.06, 0], color=C_SLATE, stroke_width=1.2).set_z_index(5)
        jev_use_hdr = txt("어디에 쓰이는가? — 4대 실무 판단 영역", size=11.0, color=C_WHITE, bold=True, z=7).move_to([2.62, -0.24, 0])

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
            app_tile(1.02, -0.82, C_CYAN, ic_u1, "① 작업 경로 분기 (라우팅)"),
            app_tile(4.24, -0.82, C_GOLD, ic_u2, "② 약관 · 규정 준수 점검"),
            app_tile(1.02, -1.62, C_MINT, ic_u3, "③ 대량 문서 · 민원 분류"),
            app_tile(4.24, -1.62, C_VIOLET, ic_u4, "④ 추출 정합성 자동 채점"),
        )

        # Open zoomed onto Left Generative AI: Stopwatch spins 2 full turns while tokens print sequentially!
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
            rt=1.25,
        )

        # Whip-Pan Right to Jev: Instant Golden Flash stamps 0.94 probability bar with zero output tokens!
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
            rt=1.15,
        )

        self.reset_cam_2d(
            anims=[LaggedStart(*[FadeIn(u, shift=UP * 0.06, scale=0.95) for u in jev_uses], lag_ratio=0.08)],
            rt=0.95,
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
        self.wait(1.45)

        # -------------------------------------------------------------------
        # Beat 5B: 3D Gyroscopic 'decision-1' Core -> Live 1,000-Q Burst & y=x Calibration Trace!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "2026년 11월 11일 출시된 Google decision-1은 26만 토큰 문서 입력과 1,000문항 일괄 판정, 정밀 확률 보정을 갖췄습니다",
            rt=0.38,
        )

        tl_bar = fit(
            VGroup(
                pill("2026.09 TypeSafe 'Jev' 개척", fg=C_INK_1, bg=C_PANEL, border=C_SLATE, size=10.6, z=8),
                arrow_2d([0, 0, 0], [0.55, 0, 0], color=C_GOLD, sw=2.2, tip=0.11, z=8),
                pill("2026.11.11 Google 'gemini-decision-1' 출시 (문서·다문항 확장)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.8, z=8),
            ).arrange(RIGHT, buff=0.14),
            max_w=11.80,
        ).move_to([0.0, 2.58, 0]).set_z_index(8)

        d1_c = np.array([0.0, -0.18, 0.0])
        d1_ring = Circle(radius=1.08, fill_opacity=0.0, stroke_color=C_GOLD_DEEP, stroke_width=1.5).move_to(d1_c).set_z_index(6)
        d1_core = Circle(radius=0.94, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_VIOLET, stroke_width=3.0).move_to(d1_c).set_z_index(7)
        d1_txt = fit(
            VGroup(
                txt("decision-1", size=13.5, color=C_GOLD, bold=True, z=8),
                txt("출력 토큰 0", size=10.4, color=C_MINT, bold=True, z=8),
                txt("일 1만 회 무료", size=9.8, color=C_INK_1, z=8),
            ).arrange(DOWN, buff=0.06),
            max_w=1.60,
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
            pill("이미지·표", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.8, px=0.08, py=0.03).move_to([-1.10, -0.20, 0]),
            arrow_2d([-0.42, 0.0, 0], [0.12, 0.0, 0], color=C_CYAN, sw=2.0, tip=0.09),
            pill("최대 26만 토큰", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.4, px=0.10, py=0.05).move_to([0.96, 0.0, 0]),
        )
        tq1 = trait_quad(-3.98, 1.02, C_CYAN, "특성 ① 대용량 복합 문서 직접 입력", tv1, "텍스트·이미지 혼합 공시 문서를 통째로 입력")

        q_dots = VGroup(*[Dot([0.15 + (k % 8) * 0.19, 0.24 - (k // 8) * 0.16, 0], radius=0.045, color=C_GOLD if k % 3 != 0 else C_MINT) for k in range(32)])
        tv2 = VGroup(
            pill("원문 1회", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.8, px=0.08, py=0.04).move_to([-1.18, 0.0, 0]),
            arrow_2d([-0.62, 0.0, 0], [-0.05, 0.0, 0], color=C_GOLD, sw=2.2, tip=0.09),
            q_dots,
        )
        tq2 = trait_quad(3.98, 1.02, C_GOLD, "특성 ② 1회 입력 → 최대 1,000문항 일괄 판정", tv2, "같은 원문을 한 번만 읽고 수백 문항 동시 채점")

        tv3 = VGroup(
            pill("예 / 아니오", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.8, px=0.09, py=0.05),
            pill("2~255지선다", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.8, px=0.09, py=0.05),
            pill("1~5 등급척도", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.09, py=0.05),
        ).arrange(RIGHT, buff=0.12)
        tq3 = trait_quad(-3.98, -1.38, C_VIOLET, "특성 ③ 3가지 정형 판정 방식", tv3, "정해진 선택지 확률만 반환 (응답 양식 오류 0건)")

        cal_ax_x = Line([-1.15, -0.30, 0], [0.35, -0.30, 0], color=C_SLATE, stroke_width=1.6)
        cal_ax_y = Line([-1.15, -0.30, 0], [-1.15, 0.34, 0], color=C_SLATE, stroke_width=1.6)
        cal_diag = DashedLine([-1.15, -0.30, 0], [0.25, 0.30, 0], dash_length=0.06, color=C_MINT, stroke_width=1.8)
        cal_pts = VGroup(*[Dot([-1.05 + k * 0.30, -0.26 + k * 0.13, 0], radius=0.048, color=C_GOLD) for k in range(5)])
        tv4 = VGroup(
            cal_ax_x,
            cal_ax_y,
            cal_diag,
            cal_pts,
            pill("확률 = 실제 신뢰도", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.09, py=0.04).move_to([1.12, 0.0, 0]),
        )
        tq4 = trait_quad(3.98, -1.38, C_MINT, "특성 ④ 정교한 확률 보정 (기준선 직결)", tv4, "예측 확률이 실제 정답률과 부합해 자동 분기 가능")

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
            rt=1.15,
        )
        self.remove(beat5a_all)
        self.cam_move(
            theta=-50 * DEGREES,
            anims=[Rotate(orb_3d_a, angle=PI / 3, axis=OUT), Rotate(orb_3d_b, angle=-PI / 3, axis=OUT)],
            rt=0.75,
        )

        # Zoom into Right Quadrants: Ripple across 1,000-Q Dot Matrix & Trace y=x Calibration Line!
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
            rt=1.15,
        )
        self.remove(d1_3d_fx, cal_runner)

        self.reset_cam_2d(anims=[FadeIn(tl_bar, shift=DOWN * 0.08)], rt=0.80)

        ch5_stage = VGroup(tl_bar, d1_hub_grp, spokes_5b, tq1, tq2, tq3, tq4)
        self.check_bounds(ch5_stage, "CH5B RADIAL TRAITS")
        self.wait(1.50)

        # ===================================================================
        # 6장 [~39s]: 검증·분류 프로세스 — 분포 충돌·은폐·온도계 폭발 · 3D 황금 첨탑 · 슬라이딩 토큰 창
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch5_stage,
            hl,
            hr,
            hb,
            6,
            "검증·분류 프로세스 — 분당 토큰 제약과 모호한 확률 문제를 넘은 방법",
            "실제 투입 과정에서 확률 뭉개짐, 묶음 질문의 오류 은폐, 분당 5만 토큰 한도 초과라는 세 가지 병목을 겪었습니다",
        )
        print(f"[TIMING] Ch5 end: {self.renderer.time:.2f}s")

        # -------------------------------------------------------------------
        # Beat 6A: Kinetic 3-Stop Camera Pan across Colliding Curves, Sneaking Bundle, & Bursting Thermometer!
        # -------------------------------------------------------------------
        top_res_6 = fit(
            pill("가용 자원 · 제약 : 호출 횟수는 일 10,000회로 넉넉하지만, 입력량은 '분당 50,000토큰' 상한 존재", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.0, z=9),
            max_w=11.80,
        ).move_to([0.0, 2.58, 0])

        def col_diag_card(cx: float, col: str, title_s: str, foot_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.09, width=3.76, height=4.28, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.1
            ).move_to([cx, -0.08, 0]).set_z_index(4)
            th = fit(txt(title_s, size=11.5, color=col, bold=True, z=7), max_w=3.44).move_to([cx, 1.66, 0])
            tf = fit(txt(foot_s, size=9.6, color=C_INK_1, z=7), max_w=3.44).move_to([cx, -1.74, 0])
            return VGroup(bx, th, tf)

        c6_1 = col_diag_card(-4.02, C_AMBER, "문제 ① 참/거짓 질문 시 확률 뭉개짐", "정답 줄도 0.50~0.80에 머물러 경계 모호")
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
        lbl_mush = pill("0.50~0.80 겹침 !", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.2, px=0.09, py=0.03, z=8).move_to([-3.85, 1.08, 0])
        lbl_ax_c1 = txt("0.0            0.5    0.8          1.0", size=8.6, color=C_INK_2, z=6).move_to([-4.02, -1.20, 0])

        c6_2 = col_diag_card(0.0, C_CORAL, "문제 ② 묶음 질문의 오류 특약 은폐", "선행·배타 특약을 뭉뚱그리면 오류 2개 통과")
        bundle_loop = DashedVMobject(Circle(radius=0.92, fill_opacity=0.0, stroke_color=C_AMBER, stroke_width=2.2).move_to([-0.38, 0.10, 0]), num_dashes=22).set_z_index(6)
        b_d1 = pill("정상 특약 ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, 0.62, 0])
        b_d2 = pill("정상 특약 ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, 0.24, 0])
        b_d3 = pill("오류 특약 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, -0.14, 0])
        b_d4 = pill("오류 특약 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.6, px=0.07, py=0.03, z=7).move_to([-0.38, -0.52, 0])
        leak_arr = arrow_2d([0.58, 0.10, 0], [1.02, 0.10, 0], color=C_CORAL, sw=2.0, tip=0.09, z=7)
        leak_stamp = pill("0.80\n통과?!", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.6, px=0.10, py=0.06, z=8).move_to([1.42, 0.10, 0])

        c6_3 = col_diag_card(4.02, C_VIOLET, "문제 ③ 원문 동봉 시 5만 토큰 초과", "대기 2,212줄 처리에 203분 병목 발생")
        therm_bg = RoundedRectangle(
            corner_radius=0.06, width=0.68, height=2.28, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.6
        ).move_to([3.28, 0.02, 0]).set_z_index(5)
        therm_fill = RoundedRectangle(corner_radius=0.05, width=0.56, height=2.14, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([3.28, -0.05, 0]).set_z_index(6)
        lim_50k = DashedLine([2.62, 0.28, 0], [5.42, 0.28, 0], dash_length=0.07, color=WHITE, stroke_width=2.2).set_z_index(8)
        lim_lbl = txt("분당 50K 상한", size=9.2, color=WHITE, bold=True, z=8).move_to([4.68, 0.50, 0])
        spike_tag = pill("최고 79.98K / 분 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.4, px=0.09, py=0.04, z=8).move_to([4.65, 1.02, 0])
        delay_tag = pill("203분 지연 !", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.4, px=0.09, py=0.04, z=8).move_to([4.65, -0.48, 0])

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
            rt=1.05,
        )

        # Stop 2: Pan Right across Sneaking Bundle -> Bursting 79.98K/min Thermometer!
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
            rt=1.15,
        )
        self.reset_cam_2d(rt=0.75)

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
        self.wait(1.30)

        # -------------------------------------------------------------------
        # Beat 6B: 3Blue1Brown 3D Probability Column Landscape -> Golden 3D Spire!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ①·② 원문 1회 입력에 다항목을 묶되 결합 제약은 개별 분리하고, 대칭 선택지로 정답·오답 확률을 갈랐습니다",
            rt=0.38,
        )

        batch_card = RoundedRectangle(
            corner_radius=0.09, width=4.38, height=4.52, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-3.88, 0.05, 0]).set_z_index(4)
        batch_hdr = fit(txt("해결 ① 원문 1회 입력 · 문항 단위 정밀 분리", size=12.6, color=C_CYAN, bold=True, z=7), max_w=4.02).move_to([-3.88, 1.88, 0])

        in_node_6b = pill("원문 1회", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.8, px=0.10, py=0.05, z=8).move_to([-5.32, 0.18, 0])
        fan_targets = VGroup(
            pill("급부 4항목 동시채점", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.4, px=0.09, py=0.04, z=8).move_to([-3.12, 1.12, 0]),
            pill("76종 표준담보 매핑", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.4, px=0.09, py=0.04, z=8).move_to([-3.12, 0.50, 0]),
            pill("결합제약 개별분리 (0.42 적발)", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.2, px=0.09, py=0.04, z=8).move_to([-3.12, -0.12, 0]),
            pill("주간 동향 · 중복 병합", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=9.4, px=0.09, py=0.04, z=8).move_to([-3.12, -0.74, 0]),
        )
        fan_arrows = VGroup(*[arrow_2d(in_node_6b.get_right(), ft.get_left(), color=C_GOLD if idx == 2 else C_CYAN, sw=1.8, tip=0.08, z=7) for idx, ft in enumerate(fan_targets)])
        batch_foot = fit(txt("반복 원문 전송 제거 · 묶으면 새는 제약은 1건씩 분리", size=9.8, color=C_INK_1, z=7), max_w=4.04).move_to([-3.88, -1.68, 0])
        batch_grp = VGroup(batch_card, batch_hdr, in_node_6b, fan_targets, fan_arrows, batch_foot)

        spec_base_y = -1.18
        spec_axis = Line([-0.90, spec_base_y, 0], [5.85, spec_base_y, 0], color=C_INK_2, stroke_width=1.8).set_z_index(3)
        spec_y_axis = Line([-0.90, spec_base_y, 0], [-0.90, 2.05, 0], color=C_INK_2, stroke_width=1.8).set_z_index(3)
        spec_y_1 = txt("1.00", size=11.0, color=C_INK_2, z=6).move_to([-1.25, 1.82, 0])
        spec_y_0 = txt("0.00", size=11.0, color=C_INK_2, z=6).move_to([-1.25, spec_base_y, 0])
        spec_x_lbl = fit(txt("해결 ② 대칭 선택지 문항 설계 : '참/거짓' 대신 '조건 있음 vs 없음' 선택", size=11.0, color=C_INK_1, z=6), max_w=6.85).move_to([2.48, -1.62, 0])

        n_bars, peak_idx = 24, 14
        bars_sharp = VGroup()
        prisms_mushy, prisms_sharp = VGroup(), VGroup()
        bx0, b_step = -0.62, 0.268
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

        mushy_callout = fit(pill("변경 전 진위형 질문 → 확률 0.50~0.80 구간 정체", fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=11.4), max_w=6.85).move_to([2.48, 2.48, 0]).set_z_index(9)
        peak_callout = fit(
            pill('변경 후 대칭 선택지 ("있음 vs 없음") → 정답 0.94↑ · 오답 0.06↓ 분리!', fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.4),
            max_w=6.95,
        ).move_to([2.48, 2.48, 0]).set_z_index(9)
        calib_chip = fit(
            pill("보정 검증 결과 : 일부러 틀리게 바꾼 437줄 가운데 확정 통과 0줄 (전량 차단 ✓)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=11.4),
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
            rt=1.15,
        )
        self.remove(beat6a_all)
        self.wait(0.45)

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
            rt=1.10,
        )
        self.remove(mushy_callout)
        self.wait(0.45)

        self.reset_cam_2d(
            anims=[
                FadeOut(prisms_sharp),
                FadeIn(bars_sharp),
                FadeIn(calib_chip, shift=UP * 0.08),
            ],
            rt=0.80,
        )
        self.remove(prisms_sharp)

        beat6b_all = VGroup(batch_grp, spec_axis, spec_y_axis, spec_y_1, spec_y_0, spec_x_lbl, bars_sharp, peak_callout, calib_chip)
        self.check_bounds(beat6b_all, "CH6B POLARIZATION")
        self.wait(1.50)

        # -------------------------------------------------------------------
        # Beat 6C: 3-Tier Particle Gate + Live Sliding [60s Window] Bracket over Token Pulses!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ③·④ 3단계 확률 분기로 오확정을 막고, 최근 60초 슬라이딩 토큰 창 제어로 분당 한도를 안전하게 지킵니다",
            rt=0.38,
        )

        nozzle = RoundedRectangle(
            corner_radius=0.08, width=1.52, height=1.06, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-5.15, 0.40, 0]).set_z_index(5)
        noz_txt = fit(
            VGroup(
                txt("해결 ③", size=10.8, color=C_CYAN, bold=True, z=7),
                txt("보정 확률", size=12.4, color=C_VIOLET, bold=True, z=7),
                txt("3단계 분기", size=11.2, color=C_INK_1, z=7),
            ).arrange(DOWN, buff=0.03),
            max_w=1.34,
        ).move_to(nozzle)

        gate_x, th_high_y, th_low_y = -2.85, 1.25, -0.32
        meter_bar = Line([gate_x, -1.70, 0], [gate_x, 2.38, 0], color=C_SLATE, stroke_width=3.0).set_z_index(4)
        line_75 = DashedLine([-3.10, th_high_y, 0], [1.48, th_high_y, 0], dash_length=0.10, color=C_GOLD, stroke_width=1.7).set_z_index(3)
        line_40 = DashedLine([-3.10, th_low_y, 0], [1.48, th_low_y, 0], dash_length=0.10, color=C_CORAL, stroke_width=1.7).set_z_index(3)
        knob_75 = pill("확률 0.75 기준", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.6, px=0.11, py=0.04).move_to([-2.85, th_high_y + 0.25, 0]).set_z_index(8)
        knob_40 = pill("확률 0.40 기준", fg=WHITE, bg=C_CORAL, border=WHITE, size=10.6, px=0.11, py=0.04).move_to([-2.85, th_low_y - 0.25, 0]).set_z_index(8)

        z_top = RoundedRectangle(corner_radius=0.08, width=2.76, height=0.88, fill_color="#232B1E", fill_opacity=0.94, stroke_color=C_GOLD, stroke_width=2.1).move_to([0.12, 1.85, 0]).set_z_index(4)
        zt_lbl = VGroup(txt("0.75 이상 : 자동 확정", size=12.8, color=C_GOLD, bold=True, z=6), txt("정본 시트 즉시 반영", size=10.8, color=C_INK_1, z=6)).arrange(DOWN, buff=0.04).move_to(z_top)
        z_mid = RoundedRectangle(corner_radius=0.08, width=2.76, height=0.96, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_WHITE, stroke_width=2.1).move_to([0.12, 0.46, 0]).set_z_index(4)
        zm_lbl = VGroup(txt("0.40~0.75 : 담당자 검토 이관", size=12.0, color=C_WHITE, bold=True, z=6), txt("원문 근거 쪽수와 함께 제시", size=10.6, color=C_CYAN, z=6)).arrange(DOWN, buff=0.04).move_to(z_mid)
        excl_wall = Line([-1.05, -1.55, 0], [-1.05, -0.70, 0], color=C_CORAL, stroke_width=4.6).set_z_index(6)
        excl_lbl = fit(
            VGroup(txt("0.40 미만 : 보류 · 재추출", size=11.8, color=C_CORAL, bold=True, z=6), txt("틀린 줄의 95.9% 포착 · 미반영", size=10.2, color=C_INK_1, z=6)).arrange(DOWN, buff=0.04),
            max_w=2.70,
        ).move_to([0.35, -1.12, 0])

        retry_arc = CubicBezier(
            np.array([-1.55, -1.08, 0]), np.array([-2.05, -2.05, 0]), np.array([-4.05, -2.05, 0]), np.array([-4.42, -0.08, 0]), color=C_VIOLET, stroke_width=2.0
        ).set_z_index(4)
        retry_lbl = pill("다른 모델 재추출", fg=C_VIOLET, bg=C_PANEL, border=C_VIOLET, size=10.4, px=0.10, py=0.04).move_to([-2.95, -1.96, 0]).set_z_index(7)

        mkt_card = RoundedRectangle(
            corner_radius=0.09, width=3.96, height=4.34, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_VIOLET, stroke_width=2.2
        ).move_to([3.92, 0.25, 0]).set_z_index(4)
        mkt_title = txt("주간 시장동향 3유형 & 60초 토큰 창", size=12.2, color=C_VIOLET, bold=True, z=7).move_to([3.92, 2.04, 0])

        # Live Sliding [60초 창] Bracket over 12 Token Request Bars!
        tok_bars_60 = VGroup(
            *[
                Rectangle(width=0.18, height=0.14 + (k % 3) * 0.08, fill_color=C_MINT if k % 2 == 0 else C_CYAN, fill_opacity=0.85, stroke_width=0)
                .move_to([2.35 + k * 0.28, 1.54, 0])
                .set_z_index(6)
                for k in range(12)
            ]
        )
        win_bracket = RoundedRectangle(corner_radius=0.04, width=1.62, height=0.40, fill_color="#1A5642", fill_opacity=0.45, stroke_color=C_GOLD, stroke_width=2.0).move_to([3.05, 1.54, 0]).set_z_index(8)
        safe_txt = fit(txt("슬라이딩 60초 창 : 42K / 50K 안전 유지 ✓", size=9.0, color=C_MINT, bold=True, z=8), max_w=3.48).move_to([3.92, 1.16, 0])

        sig_rows = VGroup()
        for sy, s_col, s_head, s_desc in [
            (0.60, C_GOLD, "◆ 배타적사용권 획득 · 신청", "독점 판매 기간 · 만료 시점 추적"),
            (-0.16, C_CORAL, "▲ 주력 담보 경쟁 심화", "가입한도 상향 · 고지 요건 완화 포착"),
            (-0.92, C_MINT, "★ 미보유 신담보 출시", "당사 미운영 보장 → 개정 검토 등록"),
        ]:
            sb = RoundedRectangle(corner_radius=0.06, width=3.54, height=0.62, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=s_col, stroke_width=1.7).move_to([3.92, sy, 0]).set_z_index(6)
            stg = fit(
                VGroup(txt(s_head, size=11.0, color=s_col, bold=True, z=7), txt(s_desc, size=9.6, color=C_INK_1, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.03),
                max_w=3.28,
            ).move_to(sb)
            sig_rows.add(VGroup(sb, stg))

        mkt_foot = txt("초기 대량분은 교차판독 · 주간 증분에 집중 투입", size=9.6, color=C_GOLD, bold=True, z=7).move_to([3.92, -1.56, 0])
        mkt_group = VGroup(mkt_card, mkt_title, tok_bars_60, win_bracket, safe_txt, sig_rows, mkt_foot)

        quota_bar = fit(
            pill("검증·분류 완결 : 오확정 0건 정밀 분기 + 60초 토큰 창 자동 조절로 분당 5만 한도 안에서 무중단 운영 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0),
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
            run_time=1.00,
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

        # Zoom in onto the 3-Tier Gate & Retry Loop while particles sort!
        self.cam_move(
            zoom=1.30,
            center=[-1.65, -0.12, 0],
            anims=[
                *stream_anims,
                MoveAlongPath(blocked_pt, CubicBezier(p_start, p_start + RIGHT * 1.0, np.array([-2.2, -1.08, 0]), np.array([-1.12, -1.08, 0])), run_time=0.90),
                MoveAlongPath(rescue_pt, CubicBezier(p_start, p_start + RIGHT * 0.9, np.array([-2.3, -1.08, 0]), np.array([-1.55, -1.08, 0])), run_time=0.80),
            ],
            rt=1.40,
        )

        # Pan Right as the [60초 창] Bracket glides smoothly across the token bars!
        self.cam_move(
            zoom=1.34,
            center=[2.65, 0.32, 0],
            anims=[
                FadeOut(blocked_pt, scale=0.3),
                FadeOut(mkt_pulses, scale=0.4),
                MoveAlongPath(rescue_pt, retry_arc, run_time=0.80),
                win_bracket.animate.move_to([4.78, 1.54, 0]),
                LaggedStart(*[Circumscribe(sr[0], color=C_GOLD, stroke_width=2.0, buff=0.03) for sr in sig_rows], lag_ratio=0.14),
            ],
            rt=1.00,
        )
        self.remove(blocked_pt, mkt_pulses, *mkt_pulses)

        self.reset_cam_2d(
            anims=[
                MoveAlongPath(
                    rescue_pt,
                    CubicBezier(np.array([-4.42, -0.08, 0]), np.array([-3.2, 1.88, 0]), np.array([-2.0, 1.88, 0]), np.array([-1.28, 1.88, 0])),
                )
            ],
            rt=0.75,
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
        self.wait(1.60)
        print(f"[TIMING] Part 3 end: {self.renderer.time:.2f}s")

        self.fade_out_part(ch6_stage, hl, hr, hb)
