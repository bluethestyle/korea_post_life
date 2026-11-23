from __future__ import annotations

import math
import networkx as nx
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
    C_IVORY,
    C_MINT,
    C_PANEL,
    C_PANEL_HI,
    C_SLATE,
    C_VIOLET,
    C_WHITE,
    PostLifeBaseScene,
    arrow_2d,
    capacity_ring,
    fit,
    glow_dot,
    pill,
    txt,
)


class Part4OntologyImpactScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        # ===================================================================
        # 7장 [~48s]: 기준 연결과 화면 제작 — 회사마다 다른 특약 이름을 하나의 지도로 묶는 법
        # ===================================================================
        hl, hr, hb = self.make_hud(
            7,
            "기준 연결과 화면 제작 — 회사마다 다른 특약 이름을 하나의 지도로 묶는 법",
            "파일 1개 크기 4MB 제한 안에서, 회사마다 제각각인 특약 이름과 넘치는 보장 종류를 동시에 정리해야 했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 7A: Kinetic 2-Stop Obstacle Tour (Colliding Chips & Overflowing 52-Cup!)
        # -------------------------------------------------------------------
        res_box_7 = RoundedRectangle(
            corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=2.0
        ).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_7 = pill("화면 파일 제약", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, z=7).move_to([-4.38, 1.92, 0])

        rg7_1 = capacity_ring([-5.15, 0.72, 0], 0.58, 0.74, C_GOLD, "파일 1개", "4MB 이하 제한", z=6)
        rg7_2 = capacity_ring([-3.62, 0.72, 0], 0.58, 0.12, C_CYAN, "서버 비용", "0원 (기준표 13개)", z=6)

        size_bg = RoundedRectangle(corner_radius=0.04, width=2.84, height=0.24, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.4).move_to([-4.38, -0.62, 0]).set_z_index(6)
        size_fg = RoundedRectangle(corner_radius=0.03, width=2.08, height=0.16, fill_color=C_MINT, fill_opacity=0.92, stroke_width=0).move_to([-4.74, -0.62, 0]).set_z_index(7)
        size_lbl = fit(txt("현재 파일 크기 2.97MB / 4.0MB 통과 ✓", size=9.2, color=C_MINT, bold=True, z=7), max_w=3.02).move_to([-4.38, -1.04, 0])
        res_sub_7 = fit(txt("설치 없이 파일 1개에 데이터·화면 내장", size=9.2, color=C_INK_2, z=7), max_w=3.02).move_to([-4.38, -1.56, 0])
        res_grp_7 = VGroup(res_box_7, res_hdr_7, rg7_1, rg7_2, size_bg, size_fg, size_lbl, res_sub_7)
        vs_arr_7 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=1.9).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=10.8, color=col, bold=True, z=7), max_w=3.44).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        q7_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 회사마다 특약 이름·지급 기준이 다름")
        m7_l1 = pill('"315 간편"', fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.6, px=0.08, py=0.03).move_to([-1.05, 1.32, 0]).set_z_index(7)
        m7_r1_c = pill('"간편가입형(1년)"', fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.6, px=0.08, py=0.03).move_to([0.92, 1.32, 0]).set_z_index(7)
        m7_l2 = pill("수술 때마다 지급", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.08, py=0.03).move_to([-1.02, 0.80, 0]).set_z_index(7)
        m7_r2_c = pill("1년에 1번 지급", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.6, px=0.08, py=0.03).move_to([0.92, 0.80, 0]).set_z_index(7)
        m7_neqs = VGroup(
            txt("≠", size=14, color=C_CORAL, bold=True).move_to([-0.10, 1.32, 0]),
            txt("≠", size=14, color=C_CORAL, bold=True).move_to([-0.10, 0.80, 0]),
        ).set_z_index(7)
        q7_1_cap = fit(txt("글자나 금액만 단순 비교하면 엉뚱한 결과", size=9.0, color=C_INK_1, z=7), max_w=3.44).move_to([-0.10, 0.42, 0])

        q7_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 처음 만든 52종 그릇에서 1,951건 넘침")
        cup_52 = VMobject(color=C_GOLD, stroke_width=2.2).set_z_index(7)
        cup_52.set_points_as_corners([[2.35, 1.38, 0], [2.35, 0.82, 0], [3.45, 0.82, 0], [3.45, 1.38, 0]])
        fun_lbl = txt("52종 그릇", size=8.4, color=C_GOLD, bold=True, z=7).move_to([2.90, 1.06, 0])
        spill_dots = VGroup(
            *[Dot([3.78 + (k % 6) * 0.25, 1.42 - (k // 6) * 0.30, 0], radius=0.055, color=C_AMBER if k % 2 == 0 else C_CORAL) for k in range(12)]
        ).set_z_index(7)
        q7_2_cap = fit(txt("한화생명 보장 1,951건이 분류되지 못하고 넘침", size=9.0, color=C_CORAL, bold=True, z=7), max_w=3.44).move_to([3.88, 0.44, 0])

        q7_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ '합친 특약 vs 나눈 특약'을 없다고 착각")
        int_chip = pill("타사 통합특약 ◆", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.6, px=0.08, py=0.03).move_to([-1.06, -1.04, 0]).set_z_index(7)
        int_arr = arrow_2d([-0.30, -1.04, 0], [0.16, -1.04, 0], color=C_CORAL, sw=1.8, tip=0.08, z=7)
        false_stamp = pill("우체국엔 없음? ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.4, px=0.07, py=0.03).move_to([0.92, -1.04, 0]).set_z_index(7)
        q7_3_cap = fit(txt("나눠 파는 우리 특약을 놓치고, 확인 중인 건도 누락 착각", size=8.8, color=C_INK_1, z=7), max_w=3.46).move_to([-0.10, -1.74, 0])

        q7_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 비교글을 미리 다 적으면 4MB 초과")
        ov_bar_bg = RoundedRectangle(corner_radius=0.04, width=1.85, height=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.2).move_to([3.05, -0.96, 0]).set_z_index(6)
        ov_bar_fg = Rectangle(width=2.18, height=0.16, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([3.22, -0.96, 0]).set_z_index(7)
        ov_lim = Line([3.78, -1.16, 0], [3.78, -0.76, 0], color=WHITE, stroke_width=2.2).set_z_index(8)
        ov_tag = txt(">4MB ×", size=8.8, color=C_CORAL, bold=True, z=8).move_to([4.88, -0.96, 0])
        no_prem = DashedVMobject(RoundedRectangle(corner_radius=0.04, width=2.98, height=0.38, fill_opacity=0.0, stroke_color=C_INK_2, stroke_width=1.4).move_to([3.88, -1.56, 0]), num_dashes=20).set_z_index(6)
        no_prem_t = fit(txt("특약별 보험료 : 공시 약관에 원래 없음", size=8.8, color=C_INK_2, bold=True, z=7), max_w=2.82).move_to([3.88, -1.56, 0])

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(VGroup(res_box_7, res_hdr_7, rg7_1[0], rg7_1[2], rg7_2[0], rg7_2[2], size_bg, size_lbl, res_sub_7), shift=RIGHT * 0.12),
                Create(rg7_1[1]),
                Create(rg7_2[1]),
                GrowFromEdge(size_fg, LEFT),
                GrowArrow(vs_arr_7),
                FadeIn(VGroup(q7_1, m7_l1, m7_r1_c, m7_l2, m7_r2_c, m7_neqs, q7_1_cap)),
                FadeIn(VGroup(q7_2, cup_52, fun_lbl, q7_2_cap)),
                FadeIn(VGroup(q7_3, int_chip, q7_3_cap)),
                FadeIn(VGroup(q7_4, ov_bar_bg, ov_lim, no_prem, no_prem_t)),
            ],
            rt=1.15,
        )

        # Stop 1: Zoom Left Quadrants — Colliding Chips & False 'Missing' Stamp!
        self.cam_move(
            zoom=1.38,
            center=[-0.10, 0.02, 0],
            anims=[
                GrowArrow(int_arr),
                FadeIn(false_stamp, scale=1.35),
                Flash(false_stamp.get_center(), color=C_CORAL, line_length=0.20, num_lines=8),
            ],
            rt=0.95,
        )
        self.play(
            m7_l1.animate.shift(RIGHT * 0.14),
            m7_r1_c.animate.shift(LEFT * 0.14),
            m7_l2.animate.shift(RIGHT * 0.14),
            m7_r2_c.animate.shift(LEFT * 0.14),
            rate_func=there_and_back,
            run_time=0.55,
        )
        self.wait(0.65)

        # Stop 2: Pan Right — 52-Cup Spills 12 Unclassified Dots & >4MB Bar Breaks Ceiling!
        self.cam_move(
            zoom=1.40,
            center=[3.88, 0.02, 0],
            anims=[
                LaggedStart(*[FadeIn(sd, shift=RIGHT * 0.18 + DOWN * 0.12, scale=0.4) for sd in spill_dots], lag_ratio=0.04),
                GrowFromEdge(ov_bar_fg, LEFT),
                Flash([3.78, -0.96, 0], color=C_CORAL, line_length=0.20, num_lines=8),
                FadeIn(ov_tag),
            ],
            rt=1.10,
        )
        self.wait(0.75)
        self.reset_cam_2d(rt=0.85)

        beat7a_all = VGroup(
            res_grp_7,
            vs_arr_7,
            q7_1,
            m7_l1,
            m7_r1_c,
            m7_l2,
            m7_r2_c,
            m7_neqs,
            q7_1_cap,
            q7_2,
            cup_52,
            fun_lbl,
            spill_dots,
            q7_2_cap,
            q7_3,
            int_chip,
            int_arr,
            false_stamp,
            q7_3_cap,
            q7_4,
            ov_bar_bg,
            ov_bar_fg,
            ov_lim,
            ov_tag,
            no_prem,
            no_prem_t,
        )
        self.check_bounds(beat7a_all, "CH7A ONTOLOGY DIAGNOSTIC")
        self.wait(1.55)

        # -------------------------------------------------------------------
        # Beat 7B: True 3D 3-Floor Structure -> Unfold into Crisp 2D 3-Band Diagram!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 원문 사실과 공통 기준표만 파일에 가볍게 담고(2.97MB), 비교 결과는 화면에서 조건을 고를 때 즉석 계산합니다",
            rt=0.40,
        )

        p3d_x = 1.25
        plane_fct_3d = RoundedRectangle(corner_radius=0.14, width=6.6, height=3.5, fill_color="#101B24", fill_opacity=0.68, stroke_color=C_CYAN, stroke_width=2.2).move_to([p3d_x, 0.0, -1.25])
        plane_std_3d = RoundedRectangle(corner_radius=0.14, width=6.6, height=3.5, fill_color="#1E1B12", fill_opacity=0.68, stroke_color=C_GOLD, stroke_width=2.2).move_to([p3d_x, 0.0, 0.00])
        plane_der_3d = RoundedRectangle(corner_radius=0.14, width=6.6, height=3.5, fill_color="#171528", fill_opacity=0.68, stroke_color=C_VIOLET, stroke_width=2.2).move_to([p3d_x, 0.0, 1.25])

        nodes_3d, shafts_3d, pulses_3d = VGroup(), VGroup(), VGroup()
        shaft_xy = [
            (p3d_x - 2.1, -0.75, C_CYAN),
            (p3d_x - 0.7, 0.65, C_GOLD),
            (p3d_x + 0.7, -0.55, C_MINT),
            (p3d_x + 2.1, 0.55, C_VIOLET),
        ]
        for sx, sy, scol in shaft_xy:
            shafts_3d.add(DashedLine([sx, sy, -1.25], [sx, sy, 1.25], dash_length=0.10, color=scol, stroke_width=2.0))
            for sz, zcol in [(-1.25, C_CYAN), (0.0, C_GOLD), (1.25, C_VIOLET)]:
                nodes_3d.add(Prism(dimensions=[0.26, 0.26, 0.14], fill_color=zcol, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.0).move_to([sx, sy, sz + 0.07]))
            pulses_3d.add(Prism(dimensions=[0.18, 0.18, 0.18], fill_color=WHITE, fill_opacity=1.0, stroke_color=scol, stroke_width=1.4).move_to([sx, sy, -1.25]))

        stack_3d_grp = VGroup(plane_fct_3d, plane_std_3d, plane_der_3d, shafts_3d, nodes_3d)

        z_lbl_3d = VGroup(
            fit(pill("3층 : 비교 결과·추천 전략 (저장 용량 0MB · 화면 즉석 계산)", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=10.4), max_w=4.35).move_to([-4.05, 1.45, 0]),
            fit(pill("2층 : 공통 기준표 (제각각인 이름을 76가지 기준으로 통일)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.4), max_w=4.35).move_to([-4.05, 0.05, 0]),
            fit(pill("1층 : 검증된 약관 사실 (파일 안에 2.97MB로 가볍게 내장)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.4), max_w=4.35).move_to([-4.05, -1.35, 0]),
        ).set_z_index(25)

        self.add_fixed_in_frame_mobjects(z_lbl_3d)
        self.cam_move(
            phi=60 * DEGREES,
            theta=-52 * DEGREES,
            zoom=0.96,
            center=[0.25, 0.0, 0.0],
            anims=[FadeOut(beat7a_all, shift=UP * 0.10), FadeIn(stack_3d_grp), FadeIn(z_lbl_3d, shift=RIGHT * 0.10)],
            rt=1.20,
        )
        self.remove(beat7a_all)

        self.add(pulses_3d)
        self.cam_move(
            phi=56 * DEGREES,
            theta=-34 * DEGREES,
            zoom=0.98,
            center=[0.25, 0.0, 0.0],
            anims=[*[MoveAlongPath(pulses_3d[k], Line([shaft_xy[k][0], shaft_xy[k][1], -1.25], [shaft_xy[k][0], shaft_xy[k][1], 1.25])) for k in range(len(shaft_xy))]],
            rt=1.25,
        )
        self.remove(pulses_3d, *pulses_3d)
        self.wait(0.65)

        def make_layer_band(y_c: float, h_b: float, col: str, fill_c: str, title_s: str, sub_s: str) -> tuple[RoundedRectangle, VGroup]:
            band = RoundedRectangle(corner_radius=0.08, width=11.90, height=h_b, fill_color=fill_c, fill_opacity=0.90, stroke_color=col, stroke_width=2.0).move_to([0.0, y_c, 0]).set_z_index(2)
            sep = Line([-3.25, y_c - h_b * 0.38, 0], [-3.25, y_c + h_b * 0.38, 0], color=col, stroke_width=1.4, stroke_opacity=0.65).set_z_index(4)
            hdr = fit(
                VGroup(txt(title_s, size=13.5, color=col, bold=True, z=7), txt(sub_s, size=10.4, color=C_INK_1, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.05),
                max_w=2.40,
            ).move_to([-4.62, y_c, 0])
            return band, VGroup(sep, hdr)

        b_der, h_der = make_layer_band(1.62, 1.00, C_VIOLET, "#171528", "3층 비교 · 전략", "저장 없이 화면 즉석 계산")
        d_n1 = pill("같은 심사 조건 상품 찾기", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.2, px=0.11, py=0.06).move_to([-1.85, 1.62, 0])
        d_n2 = pill("맞대응 특약 · 지급조건 비교", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=11.2, px=0.11, py=0.06).move_to([1.25, 1.62, 0])
        d_n4 = pill("★ 창구 · 상품기획 행동 지침", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.4, px=0.13, py=0.06).move_to([4.25, 1.62, 0])
        layer_der = VGroup(
            b_der, h_der, d_n1, d_n2, d_n4,
            arrow_2d(d_n1.get_right(), d_n2.get_left(), color=C_VIOLET, sw=1.8, tip=0.10, z=6),
            arrow_2d(d_n2.get_right(), d_n4.get_left(), color=C_GOLD, sw=1.8, tip=0.10, z=6),
        )

        b_std, h_std = make_layer_band(0.14, 1.08, C_GOLD, "#1E1B12", "2층 공통 기준표", "회사별 다른 이름 통일")
        s_grade = pill("가입 심사 유형 · 병력 기준 통일", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=11.0, px=0.11, py=0.06).move_to([-1.68, 0.14, 0])
        sd1 = Square(side_length=0.20, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([0.65, 0.34, 0]).set_z_index(7)
        sd2 = Square(side_length=0.18, fill_color=C_MINT, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.2).rotate(PI / 4).move_to([1.45, 0.46, 0]).set_z_index(7)
        sd3 = Square(side_length=0.18, fill_color=C_CYAN, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.2).rotate(PI / 4).move_to([1.45, 0.02, 0]).set_z_index(7)
        s_dag_grp = VGroup(
            Line(sd1.get_center(), sd2.get_center(), color=C_GOLD, stroke_width=2.0).set_z_index(6),
            Line(sd1.get_center(), sd3.get_center(), color=C_MINT, stroke_width=2.0).set_z_index(6),
            sd1, sd2, sd3,
            txt("◆ 공통 보장 기준 76종 & 포함·합산 연결", size=10.8, color=C_GOLD, bold=True, z=7).move_to([1.35, -0.24, 0]),
        )
        s_pay = pill("지급 방식 · 치료 5단계 분류", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, px=0.11, py=0.06).move_to([4.32, 0.14, 0])
        layer_std = VGroup(b_std, h_std, s_grade, s_dag_grp, s_pay)

        b_fct, h_fct = make_layer_band(-1.38, 1.12, C_CYAN, "#101B24", "1층 검증된 사실", "공시 약관 · 주간 뉴스 원본")
        f_org_s = RegularPolygon(n=6, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).scale(0.16).move_to([-2.48, -1.24, 0]).set_z_index(7)
        f_var_s = RoundedRectangle(corner_radius=0.04, width=0.30, height=0.26, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).move_to([-0.82, -1.24, 0]).set_z_index(7)
        f_rid_s = Circle(radius=0.14, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).move_to([1.00, -1.24, 0]).set_z_index(7)
        f_ben_s = Circle(radius=0.12, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.4).move_to([2.88, -1.24, 0]).set_z_index(7)
        f_nws_s = RegularPolygon(n=5, fill_color=C_VIOLET, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).scale(0.15).move_to([4.72, -1.24, 0]).set_z_index(7)
        layer_fct = VGroup(
            b_fct, h_fct, f_org_s, f_var_s, f_rid_s, f_ben_s, f_nws_s,
            txt("19개 보험사", size=10.8, color=C_INK_0, bold=True, z=7).move_to([-2.48, -1.64, 0]),
            txt("23개 주력 상품", size=10.8, color=C_INK_0, bold=True, z=7).move_to([-0.82, -1.64, 0]),
            txt("2,747개 특약", size=10.8, color=C_INK_0, bold=True, z=7).move_to([1.00, -1.64, 0]),
            txt("6,615건 세부 보장", size=10.8, color=C_GOLD, bold=True, z=7).move_to([2.88, -1.64, 0]),
            txt("주간 보험 뉴스", size=10.8, color=C_VIOLET, bold=True, z=7).move_to([4.72, -1.64, 0]),
            arrow_2d(f_org_s.get_right(), f_var_s.get_left(), color=C_CYAN, sw=1.8, tip=0.10, z=6),
            arrow_2d(f_var_s.get_right(), f_rid_s.get_left(), color=C_CYAN, sw=1.8, tip=0.10, z=6),
            arrow_2d(f_rid_s.get_right(), f_ben_s.get_left(), color=C_GOLD, sw=1.8, tip=0.10, z=6),
            DashedLine(f_org_s.get_top() + UP * 0.04, f_nws_s.get_top() + UP * 0.04, dash_length=0.08, color=C_VIOLET, stroke_width=1.3).set_z_index(5),
        )

        up_coords = [
            ([-0.82, -0.82, 0], [-1.68, -0.40, 0], C_CYAN),
            ([2.88, -0.82, 0], [1.35, -0.40, 0], C_GOLD),
            ([2.88, -0.82, 0], [4.32, -0.40, 0], C_GOLD),
            ([-1.68, 0.68, 0], [-1.85, 1.12, 0], C_VIOLET),
            ([1.35, 0.68, 0], [1.25, 1.12, 0], C_MINT),
            ([4.32, 0.68, 0], [4.25, 1.12, 0], C_GOLD),
        ]
        cross_layer_arrows = VGroup(*[arrow_2d(p0, p1, color=col, sw=2.0, tip=0.11, z=8) for p0, p1, col in up_coords])
        foot_7b = fit(
            pill("용량·정확성 동시 해결 : 파일 크기 2.97MB(4MB 미만) 유지 · 약관에 없는 특약별 보험료는 억지로 추측해 적지 않음 ✓", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=11.0),
            max_w=11.85,
        ).move_to([0.0, -2.56, 0]).set_z_index(9)

        self.reset_cam_2d(
            anims=[
                FadeOut(stack_3d_grp),
                FadeOut(z_lbl_3d),
                FadeIn(layer_fct),
                FadeIn(layer_std),
                FadeIn(layer_der),
                LaggedStart(*[GrowArrow(va) for va in cross_layer_arrows], lag_ratio=0.05),
                FadeIn(foot_7b, shift=UP * 0.08),
            ],
            rt=1.00,
        )
        self.remove_fixed_in_frame_mobjects(z_lbl_3d)
        self.remove(stack_3d_grp, z_lbl_3d)
        self.play(Circumscribe(d_n4[0], color=WHITE, stroke_width=2.2, buff=0.04), run_time=0.55)

        beat7b_all = VGroup(layer_fct, layer_std, layer_der, cross_layer_arrows, foot_7b)
        self.check_bounds(beat7b_all, "CH7B THREE LAYERS")
        self.wait(1.85)

        # -------------------------------------------------------------------
        # Beat 7C: 3D Connection-Map Constellation Orbit -> Magnetic Capture Zoom (52 -> 76종)!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 아직 사람이 확인 중인 672건은 점선으로 구분해 착각을 막고, 기준표를 52종에서 76종으로 넓혀 986건을 흡수했습니다",
            rt=0.40,
        )

        G = nx.Graph()
        n_per_org, n_hubs = 15, 9
        total_v = n_per_org * 3 + n_hubs
        for h_i in range(n_hubs - 1):
            G.add_edge(45 + h_i, 45 + h_i + 1)
        G.add_edge(45, 49)
        G.add_edge(46, 51)
        G.add_edge(48, 53)
        for c_idx in range(3):
            base = c_idx * n_per_org
            for k in range(1, 4):
                G.add_edge(base, base + k)
            for k in range(4, n_per_org):
                G.add_edge(base + 1 + ((k - 4) % 3), base + k)
                G.add_edge(base + k, 45 + ((k * 2 + c_idx * 3) % n_hubs))

        raw_pos = nx.spring_layout(G, dim=3, seed=19, k=0.50, iterations=90)
        xs = np.array([raw_pos[i][0] for i in range(total_v)])
        ys = np.array([raw_pos[i][1] for i in range(total_v)])
        zs = np.array([raw_pos[i][2] for i in range(total_v)])
        xs = (xs - xs.mean()) / (xs.max() - xs.min() + 1e-6) * 9.8
        ys = (ys - ys.mean()) / (ys.max() - ys.min() + 1e-6) * 3.85 - 0.08
        zs = (zs - zs.mean()) / (zs.max() - zs.min() + 1e-6) * 3.10
        net_pts = {i: np.array([xs[i], ys[i], zs[i]]) for i in range(total_v)}

        radar_bg = VGroup(
            *[Circle(radius=rad, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=0.8, stroke_opacity=0.16).move_to([0, -0.08, 0]) for rad in [1.15, 2.30, 3.45, 4.65]],
            Line([-5.8, -0.08, 0], [5.8, -0.08, 0], color=C_CYAN, stroke_width=0.7, stroke_opacity=0.12),
            Line([0, -2.85, 0], [0, 2.75, 0], color=C_CYAN, stroke_width=0.7, stroke_opacity=0.12),
        ).set_z_index(1)

        hub_prisms = VGroup()
        billboard_nodes: list[Mobject] = []
        for i in range(total_v):
            pt = net_pts[i]
            if i >= 45:
                v_mob: Mobject = (
                    Prism(dimensions=[0.22, 0.22, 0.22], fill_color=C_GOLD, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.2)
                    .rotate(PI / 4, axis=OUT)
                    .rotate(PI / 5, axis=RIGHT)
                    .move_to(pt)
                )
                hub_prisms.add(v_mob)
            elif i % 15 == 0:
                c_col = C_GOLD if i == 0 else (C_CYAN if i == 15 else C_VIOLET)
                v_mob = RegularPolygon(n=6, fill_color=c_col, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.5).scale(0.16).move_to(pt)
                billboard_nodes.append(v_mob)
            else:
                c_col = C_GOLD if i < 15 else (C_CYAN if i < 30 else C_VIOLET)
                v_mob = Circle(radius=0.076, fill_color=c_col, fill_opacity=0.88, stroke_color=c_col, stroke_width=1.1).move_to(pt)
                billboard_nodes.append(v_mob)

        billboard_grp = VGroup(*billboard_nodes)

        intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges = VGroup(), VGroup(), VGroup(), VGroup()
        bridge_counter = 0
        for u, v in G.edges():
            if u >= 45 and v >= 45:
                dag_edges.add(Line(net_pts[u], net_pts[v], color=C_GOLD, stroke_width=2.2, stroke_opacity=0.92))
            elif u < 45 and v < 45:
                intra_edges.add(Line(net_pts[u], net_pts[v], color=C_SLATE, stroke_width=1.1, stroke_opacity=0.52))
            else:
                bridge_counter += 1
                if bridge_counter % 4 == 0:
                    waiting_dashed_edges.add(DashedLine(net_pts[u], net_pts[v], dash_length=0.09, color=C_AMBER, stroke_width=1.8, stroke_opacity=0.90))
                else:
                    confirmed_bridge_edges.add(Line(net_pts[u], net_pts[v], color=C_MINT, stroke_width=1.4, stroke_opacity=0.72))

        build_banner = fit(
            pill("공통 기준 연결 지도 : 3개사 6,615건 보장을 빠짐없이 연결 · 확인 끝난 3,807건(실선)과 사람 확인 중 672건(점선) 구분", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.4),
            max_w=11.85,
        ).move_to([0, 2.70, 0]).set_z_index(25)
        build_legend = fit(
            VGroup(
                pill("◆ 포함·합산 관계 연결 (31건)", fg=C_GOLD, bg=C_PANEL, border=C_GOLD_DEEP, size=11.0),
                pill("●─● 확인 끝난 보장 (실선 3,807건)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=11.0),
                pill("●- -● 사람 확인 중 (점선 672건 · '보장 없음' 착각 방지)", fg=C_AMBER, bg=C_PANEL, border=C_AMBER, size=11.0),
            ).arrange(RIGHT, buff=0.14),
            max_w=11.85,
        ).move_to([0, -2.70, 0]).set_z_index(25)

        self.add_fixed_in_frame_mobjects(build_banner, build_legend)
        self.add_billboard(*billboard_nodes)

        self.cam_move(
            phi=56 * DEGREES,
            theta=-64 * DEGREES,
            zoom=0.98,
            center=[0.0, -0.05, 0.0],
            anims=[
                FadeOut(beat7b_all, shift=UP * 0.10),
                FadeIn(radar_bg),
                FadeIn(hub_prisms, lag_ratio=0.03),
                FadeIn(billboard_grp, lag_ratio=0.01),
                Create(intra_edges, lag_ratio=0.01),
                Create(dag_edges, lag_ratio=0.03),
                Create(confirmed_bridge_edges, lag_ratio=0.01),
                Create(waiting_dashed_edges, lag_ratio=0.02),
                FadeIn(build_banner, shift=DOWN * 0.08),
                FadeIn(build_legend, shift=UP * 0.08),
            ],
            rt=1.30,
        )
        self.remove(beat7b_all)

        self.cam_move(phi=48 * DEGREES, theta=-24 * DEGREES, zoom=1.04, center=[0.0, -0.05, 0.0], rt=2.10)

        all_net_lines = VGroup(intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges)
        z1_card = RoundedRectangle(corner_radius=0.08, width=3.30, height=4.35, fill_color=C_PANEL, fill_opacity=0.88, stroke_color=C_CYAN, stroke_width=1.9).move_to([-4.32, -0.05, 0]).set_z_index(4)
        z1_old = fit(pill("옛 상품 (간편건강 2504)", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=11.2, z=7), max_w=2.95).move_to([-4.32, 0.92, 0])
        z1_new = fit(pill("새 상품 (간편한건강 2606)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.4, z=7), max_w=2.95).move_to([-4.32, -0.18, 0])
        exp_left = VGroup(
            z1_card,
            fit(txt("확장 ① 옛 상품 → 새 상품 자동 연결", size=13.0, color=C_CYAN, bold=True, z=7), max_w=3.02).move_to([-4.32, 1.72, 0]),
            z1_old,
            z1_new,
            arrow_2d(z1_old.get_bottom(), z1_new.get_top(), color=C_GOLD, sw=2.2, tip=0.12, z=7),
            pill("특약 연결 자동 이어받기", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=10.1, px=0.10, py=0.03, z=8).move_to([-4.32, 0.37, 0]),
            fit(pill("비교 대상 3개사 → 19개사 단계 확대", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.6, z=7), max_w=2.95).move_to([-4.32, -0.92, 0]),
            fit(txt("바뀐 약관만 다시 읽고 기존 확인분 유지", size=10.4, color=C_INK_1, z=7), max_w=2.98).move_to([-4.32, -1.62, 0]),
        )

        z2_card = RoundedRectangle(corner_radius=0.08, width=4.36, height=4.35, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_MINT, stroke_width=2.2).move_to([0.0, -0.05, 0]).set_z_index(4)
        z2_t = fit(txt("확장 ② 공통 기준표 넓히기 (52 → 76가지)", size=13.2, color=C_MINT, bold=True, z=7), max_w=4.05).move_to([0.0, 1.72, 0])
        z2_sub = fit(txt("18개 보험사 요약서 35종을 조사해 새 기준 추가", size=10.6, color=C_INK_1, z=7), max_w=4.02).move_to([0.0, 1.28, 0])

        hub_centers_4c = [np.array([-1.22, 0.05, 0.0]), np.array([0.0, 0.35, 0.0]), np.array([1.22, 0.05, 0.0])]
        hub_names_4c = ["뇌·심장 통합", "전신마취·산정특례", "1인실·응급실"]
        drift_dots, remap_edges = VGroup(), VGroup()
        target_positions_4c: list[np.ndarray] = []
        rng_4c = np.random.default_rng(7)
        for hc in hub_centers_4c:
            for k in range(4):
                ang = math.pi / 4 + k * (math.pi / 2)
                t_pt = hc + np.array([0.46 * math.cos(ang), 0.42 * math.sin(ang), 0.0])
                target_positions_4c.append(t_pt)
                drift_dots.add(Dot(np.array([rng_4c.uniform(-1.65, 1.65), rng_4c.uniform(-0.85, 0.78), 0.0]), radius=0.068, color=C_AMBER).set_z_index(8))
                remap_edges.add(Line(hc, t_pt, color=C_MINT, stroke_width=1.8).set_z_index(6))

        new_hubs_4c, new_hub_lbls = VGroup(), VGroup()
        for h_idx, (hc, h_nm) in enumerate(zip(hub_centers_4c, hub_names_4c)):
            new_hubs_4c.add(Square(side_length=0.24, fill_color=C_MINT if h_idx != 1 else C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.5).rotate(PI / 4).move_to(hc).set_z_index(9))
            new_hub_lbls.add(txt(h_nm, size=10.5, color=C_MINT if h_idx != 1 else C_GOLD, bold=True, z=9).move_to(hc + (DOWN * 0.72 if h_idx != 1 else UP * 0.64)))
        remap_ok = fit(pill("새 기준 25가지 추가 → 갈 곳 없던 보장 986건 흡수 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=10.8, z=9), max_w=4.05).move_to([0.0, -1.52, 0])

        z3_card = RoundedRectangle(corner_radius=0.08, width=3.30, height=4.35, fill_color=C_PANEL, fill_opacity=0.88, stroke_color=C_VIOLET, stroke_width=1.9).move_to([4.32, -0.05, 0]).set_z_index(4)
        z3_news = fit(pill("타사 신상품 · 독점 담보 뉴스", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.0, z=7), max_w=2.95).move_to([4.32, 0.95, 0])
        z3_xr = pill("독점 담보", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.2, px=0.09, py=0.05, z=7).move_to([3.52, 0.08, 0])
        z3_cand = pill("새 기준 후보", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=10.5, px=0.10, py=0.05, z=7).move_to([5.08, 0.08, 0])
        z3_prom = fit(pill("◆ 다음 기준표 추가 후보", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.0, z=7), max_w=2.95).move_to([4.32, -0.85, 0])
        exp_right = VGroup(
            z3_card,
            fit(txt("확장 ③ 주간 뉴스 → 새 기준 후보 발굴", size=13.0, color=C_VIOLET, bold=True, z=7), max_w=3.02).move_to([4.32, 1.72, 0]),
            z3_news, z3_xr, z3_cand, z3_prom,
            arrow_2d(z3_news.get_bottom() + LEFT * 0.35, z3_xr.get_top(), color=C_VIOLET, sw=1.7, tip=0.10, z=6),
            arrow_2d(z3_news.get_bottom() + RIGHT * 0.35, z3_cand.get_top(), color=C_MINT, sw=1.7, tip=0.10, z=6),
            arrow_2d(z3_cand.get_bottom(), z3_prom.get_top() + RIGHT * 0.35, color=C_GOLD, sw=2.0, tip=0.11, z=6),
            fit(txt("여러 보험사가 잇따라 출시하면 정식 기준 등록", size=10.2, color=C_INK_1, z=7), max_w=3.02).move_to([4.32, -1.62, 0]),
        )

        # Level from 3D Constellation straight into Close-up of the Magnetic Dot Capture Chamber!
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.46,
            center=[0.0, -0.05, 0],
            anims=[
                all_net_lines.animate.set_stroke(opacity=0.14),
                hub_prisms.animate.set_opacity(0.16),
                billboard_grp.animate.set_opacity(0.16),
                FadeOut(build_banner),
                FadeOut(build_legend),
                FadeIn(VGroup(z2_card, z2_t, z2_sub, drift_dots), scale=0.92),
            ],
            rt=0.95,
        )
        self.remove_fixed_in_frame_mobjects(build_banner, build_legend)
        self.remove(build_banner, build_legend)

        # Magnetic Gravity-Wells Pull in 12 Unclassified Dots in Close-up!
        self.play(
            FadeIn(new_hubs_4c, scale=0.25),
            FadeIn(new_hub_lbls),
            *[drift_dots[idx].animate.move_to(target_positions_4c[idx]).set_color(C_GOLD if (idx // 4) == 1 else C_MINT) for idx in range(12)],
            Create(remap_edges, lag_ratio=0.02),
            Flash(hub_centers_4c[0], color=C_MINT, line_length=0.20, num_lines=8),
            Flash(hub_centers_4c[1], color=C_GOLD, line_length=0.24, num_lines=8),
            Flash(hub_centers_4c[2], color=C_MINT, line_length=0.20, num_lines=8),
            FadeIn(remap_ok, shift=UP * 0.08),
            run_time=1.20,
        )
        self.wait(0.75)

        # Pull back to reveal Left Lineage & Right Market Candidate engines
        self.reset_cam_2d(
            anims=[FadeIn(exp_left, shift=RIGHT * 0.14), FadeIn(exp_right, shift=LEFT * 0.14)],
            rt=0.90,
        )

        bg_cosmos = VGroup(radar_bg, all_net_lines, hub_prisms, billboard_grp)
        fg_7c = VGroup(exp_left, z2_card, z2_t, z2_sub, drift_dots, new_hubs_4c, new_hub_lbls, remap_edges, remap_ok, exp_right)
        self.check_bounds(fg_7c, "CH7C EXPANSION")
        self.wait(1.90)

        # ===================================================================
        # 8장 [~48s]: 연결 지도로 숨은 보장 찾기 — 합산 보장 탐색부터 창구 요약 카드까지
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            fg_7c,
            hl,
            hr,
            hb,
            8,
            "연결 지도로 숨은 보장 찾기 — 합산 보장 탐색부터 창구 요약 카드까지",
            "타사는 '뇌·심장 통합특약' 1개로 팔고 우체국은 '뇌혈관 + 심장' 2개로 나눠 팔 때, 지도를 따라가 합산 보장을 찾아냅니다",
        )
        print(f"[TIMING] Ch7 end: {self.renderer.time:.2f}s")

        # -------------------------------------------------------------------
        # Beat 8A: Camera Dive + Camera Riding the Twin Split-Rider Pulses!
        # -------------------------------------------------------------------
        def graph_hub(label: str, pos: list[float], col: str = C_GOLD, r: float = 0.22, lbl_dir: np.ndarray = DOWN) -> VGroup:
            dm = Square(side_length=r * 1.5, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.5).rotate(PI / 4).move_to(pos).set_z_index(8)
            core = Square(side_length=r * 0.55, fill_color=col, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to(pos).set_z_index(9)
            lb = pill(label, fg=col, bg=C_BG_SUB, border=col, size=12.0, px=0.12, py=0.05, z=9).next_to(dm, lbl_dir, buff=0.11)
            return VGroup(dm, core, lb)

        def graph_entity(label: str, sub: str, pos: list[float], col: str, is_square: bool = True) -> VGroup:
            if is_square:
                sh: Mobject = RoundedRectangle(corner_radius=0.07, width=1.64, height=0.68, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).move_to(pos).set_z_index(8)
                tg = fit(VGroup(txt(label, size=12.6, color=WHITE, bold=True, z=9), txt(sub, size=10.2, color=col, z=9)).arrange(DOWN, buff=0.04), max_w=1.48).move_to(pos)
                return VGroup(sh, tg)
            sh = Circle(radius=0.31, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).move_to(pos).set_z_index(8)
            return VGroup(sh, txt(label, size=11.0, color=WHITE, bold=True, z=9).move_to(pos), txt(sub, size=10.4, color=col, bold=True, z=9).next_to(sh, DOWN, buff=0.09))

        cv1 = pill("◆ 뇌·심장 진단", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.6, px=0.12, py=0.05, z=8).move_to([-1.85, 2.22, 0])
        cv2 = pill("◆ 뇌혈관 진단", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.6, px=0.12, py=0.05, z=8).move_to([0.22, 2.22, 0])
        cv3 = pill("◆ 뇌졸중", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.6, px=0.12, py=0.05, z=8).move_to([2.10, 2.22, 0])
        cv4 = pill("◆ 뇌출혈", fg=C_WHITE, bg=C_PANEL_HI, border=C_WHITE, size=11.6, px=0.12, py=0.05, z=8).move_to([3.82, 2.22, 0])
        top_chain_grp = VGroup(
            fit(txt("넓은 보장 → 좁은 보장 포함 관계 :", size=11.6, color=C_GOLD, bold=True, z=9), max_w=2.95).move_to([-4.45, 2.22, 0]),
            cv1, cv2, cv3, cv4,
            arrow_2d(cv1.get_right(), cv2.get_left(), color=C_GOLD, sw=2.0, tip=0.10, z=8),
            arrow_2d(cv2.get_right(), cv3.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=8),
            arrow_2d(cv3.get_right(), cv4.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=8),
        )

        n_peer_rider = graph_entity("타사 상품", "통합형 특약 판매", [-5.05, -0.25, 0], C_CYAN, is_square=True)
        n_peer_ben = graph_entity("타사 특약", "통합수술", [-3.35, -0.25, 0], C_CYAN, is_square=False)
        h_integrated = graph_hub("뇌·심장질환 수술비", [-1.45, -0.25, 0], C_GOLD, r=0.25, lbl_dir=UP)
        sel_ring = DashedVMobject(Circle(radius=0.52, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.0).move_to([-1.45, -0.25, 0]), num_dashes=24).set_z_index(7)
        h_part_br = graph_hub("뇌혈관질환 수술비", [0.85, 0.72, 0], C_MINT, r=0.21, lbl_dir=UP)
        h_part_ht = graph_hub("심장질환 수술비", [0.85, -1.22, 0], C_MINT, r=0.21, lbl_dir=DOWN)
        n_ep_ben1 = graph_entity("특약①", "우체국 보유", [2.95, 0.72, 0], C_GOLD, is_square=False)
        n_ep_ben2 = graph_entity("특약②", "우체국 보유", [2.95, -1.22, 0], C_GOLD, is_square=False)
        n_ep_prod = graph_entity("우체국 2606", "2개 합쳐 보장", [4.95, -0.25, 0], C_GOLD, is_square=True)

        e_hop1_a = Line([-1.12, -0.05, 0], [0.55, 0.62, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop1_b = Line([-1.12, -0.45, 0], [0.55, -1.12, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop2_a = Line([1.16, 0.72, 0], [2.62, 0.72, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop2_b = Line([1.16, -1.22, 0], [2.62, -1.22, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop3_a = Line([3.27, 0.62, 0], [4.13, -0.02, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop3_b = Line([3.27, -1.12, 0], [4.13, -0.48, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)

        fg_subgraph = VGroup(
            top_chain_grp, n_peer_rider, n_peer_ben, h_integrated, sel_ring, h_part_br, h_part_ht, n_ep_ben1, n_ep_ben2, n_ep_prod,
            arrow_2d(n_peer_rider[0].get_right(), n_peer_ben[0].get_left(), color=C_CYAN, sw=2.0, tip=0.11, z=7),
            arrow_2d(n_peer_ben[0].get_right(), [-1.82, -0.25, 0], color=C_CYAN, sw=2.0, tip=0.11, z=7),
            e_hop1_a, e_hop1_b,
            pill("나눈 특약 합쳐서 비교", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=9.4, px=0.08, py=0.03, z=9).move_to([-0.08, 0.46, 0]),
            pill("나눈 특약 합쳐서 비교", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=9.4, px=0.08, py=0.03, z=9).move_to([-0.08, -0.96, 0]),
            e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b,
        )

        # Dive into Central Hub -> Show False Name-Only Error -> Ride Twin Pulses Right to 우체국 2606!
        self.cam_move(
            zoom=1.52,
            center=[-1.45, -0.25, 0],
            anims=[FadeIn(h_integrated, scale=0.8), FadeIn(sel_ring)],
            rt=0.80,
        )
        self.reset_cam_2d(
            anims=[
                FadeIn(
                    VGroup(
                        top_chain_grp, n_peer_rider, n_peer_ben, h_part_br, h_part_ht, n_ep_ben1, n_ep_ben2, n_ep_prod,
                        fg_subgraph[10], fg_subgraph[11], e_hop1_a, e_hop1_b, fg_subgraph[14], fg_subgraph[15], e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b,
                    ),
                    lag_ratio=0.03,
                )
            ],
            rt=0.90,
        )

        bad_arc = DashedVMobject(
            CubicBezier(np.array([-1.45, -0.62, 0]), np.array([0.2, -2.55, 0]), np.array([3.2, -2.55, 0]), np.array([4.95, -0.62, 0]), color=C_CORAL, stroke_width=2.4),
            num_dashes=28,
        ).set_z_index(10)
        bad_1hop_lbl = fit(pill('이름만 단순 비교할 때 : "통합수술비라는 이름이 없으니 우체국엔 없다"고 잘못 판단 ×', fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.4, z=11), max_w=9.20).move_to([1.55, -2.38, 0])
        self.play(Create(bad_arc), FadeIn(bad_1hop_lbl, shift=UP * 0.08), run_time=0.75)
        self.wait(0.85)

        hop_badge = fit(
            pill("연결 지도 탐색 결과 ✓ : 겉보기에 없어 보이던 29가지 중 25가지가 우체국에도 보장됨을 확인!", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=11.6, z=12),
            max_w=9.30,
        ).move_to([1.45, -2.38, 0])
        p_up, p_dn = glow_dot([-1.12, -0.05, 0], color=C_MINT, r=0.072, z=14), glow_dot([-1.12, -0.45, 0], color=C_MINT, r=0.072, z=14)
        self.add(p_up, p_dn)

        # Camera zooms & tracks right alongside the splitting & reconverging pulses!
        self.cam_move(
            zoom=1.28,
            center=[0.45, -0.25, 0],
            anims=[
                FadeOut(bad_arc),
                FadeOut(bad_1hop_lbl),
                Rotate(sel_ring, angle=PI / 3),
                MoveAlongPath(p_up, e_hop1_a),
                MoveAlongPath(p_dn, e_hop1_b),
                e_hop1_a.animate.set_stroke(color=C_MINT, width=3.4),
                e_hop1_b.animate.set_stroke(color=C_MINT, width=3.4),
            ],
            rt=0.75,
        )
        self.remove(bad_arc, bad_1hop_lbl)
        self.cam_move(
            zoom=1.30,
            center=[2.95, -0.25, 0],
            anims=[
                MoveAlongPath(p_up, e_hop2_a),
                MoveAlongPath(p_dn, e_hop2_b),
                e_hop2_a.animate.set_stroke(color=C_GOLD, width=3.4),
                e_hop2_b.animate.set_stroke(color=C_GOLD, width=3.4),
            ],
            rt=0.65,
        )
        self.reset_cam_2d(
            anims=[
                MoveAlongPath(p_up, e_hop3_a),
                MoveAlongPath(p_dn, e_hop3_b),
                e_hop3_a.animate.set_stroke(color=C_GOLD, width=3.4),
                e_hop3_b.animate.set_stroke(color=C_GOLD, width=3.4),
                Flash([4.95, -0.25, 0], color=C_MINT, line_length=0.26, num_lines=10),
                Circumscribe(n_ep_prod[0], color=C_MINT, stroke_width=2.4, buff=0.03),
                FadeIn(hop_badge, shift=UP * 0.08),
            ],
            rt=0.85,
        )
        self.remove(p_up, p_dn)
        self.wait(1.85)

        # -------------------------------------------------------------------
        # Beat 8B: Eligibility Table Crosshair Zoom -> Pan to Care Journey 0종 Gap -> Pull Back
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "고객 나이·병력별 가입 가능 표와 치료 5단계별 보유 보장 차트, 함께 가입해야 하는 조건을 한눈에 보여줍니다",
            rt=0.40,
        )

        pm_title = txt("고객 나이 · 병력별 가입 가능 여부", size=13.5, color=C_WHITE, bold=True, z=7).move_to([-3.05, 2.22, 0])
        hist_labels = ["최근 입원 이력", "수술만 (입원 없음)", "2~5년 지난 병력", "병력 해당 없음"]
        pm_cells = VGroup()
        gold_corridor_cell = None
        for r_i, h_lbl in enumerate(hist_labels):
            ry = 1.25 - r_i * 0.82
            pm_cells.add(txt(h_lbl, size=11.2, color=C_GOLD if r_i == 1 else C_INK_1, bold=(r_i == 1), z=7).move_to([-5.20, ry, 0]))
            for c_i, cw_p in enumerate([1.28, 2.68]):
                cx = -3.65 if c_i == 0 else -1.55
                is_gold_open = r_i == 1 and c_i == 1
                is_both_open = r_i >= 2 and c_i == 1
                cell_r = RoundedRectangle(
                    corner_radius=0.05,
                    width=cw_p,
                    height=0.68,
                    fill_color="#383016" if is_gold_open else ("#182832" if is_both_open else C_PANEL_HI),
                    fill_opacity=0.95,
                    stroke_color=C_GOLD if is_gold_open else (C_CYAN if is_both_open else C_SLATE),
                    stroke_width=2.2 if is_gold_open else 1.2,
                ).move_to([cx, ry, 0]).set_z_index(4)
                if is_gold_open:
                    ct = fit(txt("▲ 우체국 가입 가능!", size=10.8, color=C_GOLD, bold=True, z=7), max_w=2.00)
                    ct.move_to(cell_r.get_left() + RIGHT * (0.12 + ct.width / 2))
                    gold_corridor_cell = cell_r
                elif is_both_open:
                    ct = txt("간편심사 가입 가능", size=11.0, color=C_CYAN, z=7).move_to(cell_r)
                elif c_i == 0:
                    ct = txt("일반심사 안내", size=10.6, color=C_INK_2, z=7).move_to(cell_r)
                else:
                    ct = txt("간편가입 제한 ×", size=10.6, color=C_CORAL, z=7).move_to(cell_r)
                pm_cells.add(VGroup(cell_r, ct))

        pm_age_hdr = VGroup(txt("15~19세", size=11.5, color=C_INK_2, z=7).move_to([-3.65, 1.76, 0]), txt("20~80세", size=11.5, color=C_INK_1, bold=True, z=7).move_to([-1.55, 1.76, 0]))
        pin_pt = np.array([-0.46, 0.43, 0.0])
        target_cursor = VGroup(
            Circle(radius=0.16, fill_opacity=0.0, stroke_color=WHITE, stroke_width=2.4).move_to(pin_pt),
            Line(pin_pt + LEFT * 0.22, pin_pt + RIGHT * 0.22, color=WHITE, stroke_width=1.5),
            Line(pin_pt + DOWN * 0.22, pin_pt + UP * 0.22, color=WHITE, stroke_width=1.5),
            Dot(pin_pt, radius=0.045, color=C_GOLD),
        ).set_z_index(10)
        phase_map_grp = VGroup(pm_title, pm_age_hdr, pm_cells, target_cursor)

        cj_title = txt("치료 5단계별 우체국 보유 보장 수", size=13.5, color=C_WHITE, bold=True, z=7).move_to([3.25, 2.22, 0])
        cj_stages = [("진단", 7, C_CYAN), ("수술", 6, C_CYAN), ("치료", 4, C_MINT), ("입원·간병", 8, C_GOLD), ("통원", 0, C_CORAL)]
        cj_bars, cj_nodes = VGroup(), VGroup()
        cj_base_y = 0.44
        for s_i, (s_nm, s_cnt, s_col) in enumerate(cj_stages):
            sx = 1.05 + s_i * 1.10
            slot_bg = RoundedRectangle(
                corner_radius=0.05, width=0.84, height=1.36, fill_color=C_PANEL_HI, fill_opacity=0.92,
                stroke_color=C_CORAL if s_cnt == 0 else C_SLATE, stroke_width=1.8 if s_cnt == 0 else 1.1,
            ).move_to([sx, cj_base_y + 0.68, 0]).set_z_index(3)
            if s_cnt > 0:
                bh = (s_cnt / 8.0) * 0.80
                bar = RoundedRectangle(corner_radius=0.04, width=0.56, height=bh, fill_color=s_col, fill_opacity=0.86, stroke_color=WHITE, stroke_width=1.0).move_to([sx, cj_base_y + 0.10 + bh / 2, 0]).set_z_index(5)
                cj_bars.add(VGroup(slot_bg, bar, txt(f"{s_cnt}종", size=11.2, color=WHITE, bold=True, z=7).move_to([sx, cj_base_y + 0.10 + bh + 0.18, 0])))
            else:
                cj_bars.add(
                    VGroup(
                        slot_bg,
                        txt("0종", size=13.2, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + UP * 0.12),
                        txt("보완 필요", size=9.4, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + DOWN * 0.28),
                    )
                )
            cj_nodes.add(txt(s_nm, size=11.0, color=C_CORAL if s_cnt == 0 else C_INK_1, bold=(s_cnt == 0), z=7).move_to([sx, cj_base_y - 0.20, 0]))

        cj_links = VGroup(
            *[Line([1.05 + i * 1.10 + 0.44, cj_base_y + 0.68, 0], [1.05 + (i + 1) * 1.10 - 0.44, cj_base_y + 0.68, 0], color=C_CORAL if i == 3 else C_GOLD, stroke_width=2.2).set_z_index(6) for i in range(4)]
        )
        care_journey_grp = VGroup(cj_title, cj_bars, cj_nodes, cj_links)

        rc_box = RoundedRectangle(corner_radius=0.07, width=5.35, height=1.85, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_SLATE, stroke_width=1.4).move_to([3.25, -1.18, 0]).set_z_index(3)
        nd_main = pill("● 주계약 4,000만", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=10.4, px=0.09, py=0.05, z=7).move_to([1.48, -1.10, 0])
        nd_rider = pill("● 표적항암 2,000만", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.4, px=0.09, py=0.05, z=7).move_to([3.25, -1.10, 0])
        nd_excl = pill("● 동시 가입 불가", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.4, px=0.09, py=0.05, z=7).move_to([5.02, -1.10, 0])
        constraint_grp = VGroup(
            rc_box,
            fit(txt("함께 가입해야 하는 조건 반영 실수령액 계산", size=12.0, color=C_GOLD, bold=True, z=7), max_w=5.00).move_to([3.25, -0.52, 0]),
            nd_main, nd_rider, nd_excl,
            arrow_2d(nd_main.get_right(), nd_rider.get_left(), color=C_MINT, sw=1.9, tip=0.09, z=7),
            DashedLine(nd_rider.get_right(), nd_excl.get_left(), dash_length=0.06, color=C_CORAL, stroke_width=1.9).set_z_index(6),
            fit(txt("주계약 비례 한도 자동 반영 ✓ · 같이 못 드는 특약 자동 차단 ×", size=10.2, color=C_INK_1, z=7), max_w=5.00).move_to([3.25, -1.72, 0]),
        )
        beat8b_all = VGroup(phase_map_grp, care_journey_grp, constraint_grp)

        self.play(
            FadeOut(bg_cosmos),
            FadeOut(fg_subgraph),
            FadeOut(hop_badge),
            FadeIn(pm_title),
            FadeIn(pm_age_hdr),
            LaggedStart(*[FadeIn(c, shift=UP * 0.05) for c in pm_cells], lag_ratio=0.025),
            FadeIn(care_journey_grp, shift=LEFT * 0.12),
            FadeIn(constraint_grp, shift=UP * 0.10),
            run_time=1.10,
        )
        self.remove_billboard(*billboard_nodes)
        self.remove(bg_cosmos, fg_subgraph, hop_badge)

        assert gold_corridor_cell is not None
        self.cam_move(
            zoom=1.42,
            center=[-2.90, 0.35, 0],
            anims=[FadeIn(target_cursor, scale=1.5), Circumscribe(gold_corridor_cell, color=C_GOLD, stroke_width=2.2, buff=0.03)],
            rt=0.95,
        )
        self.wait(0.75)

        cj_pulse = glow_dot([1.05, cj_base_y + 0.68, 0], color=C_GOLD, r=0.065, z=13)
        self.add(cj_pulse)
        self.cam_move(
            zoom=1.38,
            center=[3.25, 0.85, 0],
            anims=[
                MoveAlongPath(cj_pulse, Line([1.05, cj_base_y + 0.68, 0], [1.05 + 4 * 1.10, cj_base_y + 0.68, 0])),
                Circumscribe(cj_bars[4][0], color=C_CORAL, stroke_width=2.2, buff=0.03),
                Wiggle(cj_bars[4][1], scale_value=1.18, rotation_angle=0.05 * TAU),
            ],
            rt=1.00,
        )
        self.remove(cj_pulse)
        self.wait(0.75)
        self.reset_cam_2d(rt=0.80)

        self.check_bounds(beat8b_all, "CH8B PHASE & CARE CHARTS")
        self.wait(1.75)

        # -------------------------------------------------------------------
        # Beat 8C: Spinning 4-Guide Compass -> Console Dock -> Close-up A4 Laser Print!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "분석 결과가 4가지 알기 쉬운 실무 지침으로 정리되어 본부 화면과 창구 직원용 A4 1장 요약 카드로 출력됩니다",
            rt=0.40,
        )

        def make_strat_quad(cx: float, cy: float, col: str, title_s: str, action_s: str, icon_mob: VGroup) -> VGroup:
            box = RoundedRectangle(corner_radius=0.09, width=5.46, height=1.96, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=col, stroke_width=2.2).move_to([cx, cy, 0]).set_z_index(4)
            div = Line([cx - 1.18, cy - 0.72, 0], [cx - 1.18, cy + 0.72, 0], color=col, stroke_width=1.2, stroke_opacity=0.55).set_z_index(5)
            icon_mob.move_to([cx - 1.95, cy, 0]).set_z_index(7)
            t_blk = fit(
                VGroup(txt(title_s, size=13.0, color=col, bold=True, z=7), txt(action_s, size=12.0, color=WHITE, bold=True, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.14),
                max_w=3.58,
            ).move_to([cx + 0.78, cy, 0])
            return VGroup(box, div, icon_mob, t_blk)

        ic1 = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.16, height=0.38, fill_color=C_CORAL_DIM, fill_opacity=0.9, stroke_color=C_CORAL, stroke_width=1.4).move_to([0, 0.30, 0]),
            txt("타사 입원·수술 ×", size=8.6, color=C_CORAL, bold=True, z=8).move_to([0, 0.30, 0]),
            RoundedRectangle(corner_radius=0.04, width=1.16, height=0.42, fill_color="#383016", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.8).move_to([0, -0.26, 0]),
            txt("우체국 입원만 ✓", size=9.0, color=C_GOLD, bold=True, z=8).move_to([0, -0.26, 0]),
        )
        q_s1 = make_strat_quad(-3.15, 1.32, C_GOLD, "지침 ① [누구에게 권할까]", "수술만 했고 입원 없는 20~80세 고객께 우선 안내", ic1)

        ic2 = VGroup(
            Line([-0.38, 0, 0], [0.38, 0.36, 0], color=C_MINT, stroke_width=2.0),
            Line([-0.38, 0, 0], [0.38, 0.0, 0], color=C_MINT, stroke_width=2.0),
            Line([-0.38, 0, 0], [0.38, -0.36, 0], color=C_MINT, stroke_width=2.0),
            Dot([-0.38, 0, 0], radius=0.11, color=C_MINT),
            Square(side_length=0.16, fill_color=C_GOLD, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to([0.38, 0.36, 0]),
            Square(side_length=0.16, fill_color=C_GOLD, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to([0.38, 0.0, 0]),
            Square(side_length=0.16, fill_color=C_GOLD, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to([0.38, -0.36, 0]),
        )
        q_s2 = make_strat_quad(3.15, 1.32, C_MINT, "지침 ② [어떤 강점을 앞세울까]", "우체국만 가진 6가지 보장(뇌·심장 입원일당 등) 강조", ic2)

        ic3_step = VMobject(color=C_CYAN, stroke_width=2.8)
        ic3_step.set_points_as_corners([[-0.52, -0.32, 0], [-0.05, -0.32, 0], [-0.05, 0.26, 0], [0.52, 0.26, 0]])
        ic3 = VGroup(
            Line([-0.55, -0.42, 0], [0.55, -0.42, 0], color=C_SLATE, stroke_width=1.4),
            ic3_step,
            txt("1년 후 100%", size=8.8, color=C_GOLD, bold=True, z=8).move_to([0.22, 0.46, 0]),
        )
        q_s3 = make_strat_quad(-3.15, -1.24, C_CYAN, "지침 ③ [불리한 조건은 어떻게 설명할까]", "나눈 특약 합산 금액과 1년 뒤 100% 지급 조건 안내", ic3)

        ic4 = VGroup(
            RoundedRectangle(corner_radius=0.04, width=0.46, height=0.64, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=1.4).move_to([-0.32, 0.04, 0]),
            txt("입원8", size=8.8, color=C_GOLD, bold=True, z=8).move_to([-0.32, 0.04, 0]),
            RoundedRectangle(corner_radius=0.04, width=0.48, height=0.64, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.8).move_to([0.34, 0.04, 0]),
            txt("통원0", size=8.8, color=C_CORAL, bold=True, z=8).move_to([0.34, 0.04, 0]),
        )
        q_s4 = make_strat_quad(3.15, -1.24, C_CORAL, "지침 ④ [다음 상품 때 무엇을 보강할까]", "비어 있는 '통원일당' 신설 · 15~19세 가입 확대 건의", ic4)

        comp_c = np.array([0.0, 0.04, 0.0])
        comp_ring = Circle(radius=0.46, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.6).move_to(comp_c).set_z_index(10)
        comp_needle = Line(comp_c + DOWN * 0.34, comp_c + UP * 0.34, color=C_GOLD, stroke_width=2.6).rotate(PI / 4).set_z_index(12)
        comp_txt = fit(txt("4가지 지침", size=9.4, color=WHITE, bold=True, z=13), max_w=0.76).move_to(comp_c)
        compass_hub = VGroup(comp_ring, comp_needle, comp_txt)
        four_strategies = VGroup(q_s1, q_s2, q_s3, q_s4, compass_hub)

        self.add(comp_needle)
        self.play(
            FadeOut(beat8b_all, scale=0.94),
            FadeIn(VGroup(comp_ring, comp_txt), scale=0.6),
            Rotate(comp_needle, angle=-TAU, about_point=comp_c),
            LaggedStart(*[FadeIn(q, shift=UP * 0.10) for q in [q_s1, q_s2, q_s4, q_s3]], lag_ratio=0.12),
            run_time=1.20,
        )
        self.remove(beat8b_all)
        self.wait(1.15)

        app_window = RoundedRectangle(corner_radius=0.10, width=8.05, height=4.75, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_INK_1, stroke_width=2.2).move_to([-2.05, -0.15, 0]).set_z_index(1)
        app_win_hdr = fit(pill("본부 상품 · 영업지원 화면 (설치 없는 파일 1개 · 2.97MB)", fg=WHITE, bg=C_PANEL_HI, border=C_SLATE, size=11.6), max_w=7.60).move_to([-2.05, 1.92, 0]).set_z_index(8)
        tpl_bar = fit(pill("과장 · 단정 문구 자동 차단 ✓ · 모든 문장에 약관 몇 쪽인지 바로 표시", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=11.0, px=0.14, py=0.06, z=8), max_w=7.60).move_to([-2.05, -1.32, 0])
        nlq_bar = fit(pill('쉬운 검색 연동 : "50세 수술이력 뇌혈관 비교" 입력 → 비교표 · 카드 즉시 완성', fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=10.8, px=0.14, py=0.06, z=8), max_w=7.60).move_to([-2.05, -1.98, 0])

        a4_box = Rectangle(width=2.98, height=4.75, fill_color=C_IVORY, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.4).move_to([4.48, -0.15, 0]).set_z_index(5)
        a4_top_bar = Line(a4_box.get_corner(UL), a4_box.get_corner(UR), color=C_CORAL, stroke_width=5.0).set_z_index(7)
        a4_badge = pill("직원 참고용 · A4 1장", fg=WHITE, bg=C_CORAL, border=C_CORAL, size=11.0).move_to([4.48, 1.76, 0]).set_z_index(7)
        a4_title = fit(txt("창구 · 설계사 요약 카드", size=15.4, color=C_DARK_INK, bold=True, z=7), max_w=2.70).move_to([4.48, 1.24, 0])
        mini_cards = VGroup()
        for m_lbl, m_col in [("① 수술 이력 가입 기준 차이", C_GOLD_DEEP), ("② 우리만의 강점 · 맞대응 특약", "#1E6B7B"), ("③ 감액 기간 조건 · 약관 쪽수", "#2D3748")]:
            mb = RoundedRectangle(corner_radius=0.05, width=2.58, height=0.74, fill_color="#E5E4DC", fill_opacity=1.0, stroke_color="#C4C2B6", stroke_width=1.1).set_z_index(6)
            m_bar = Rectangle(width=0.10, height=0.74, fill_color=m_col, fill_opacity=1.0, stroke_width=0).move_to(mb.get_left() + RIGHT * 0.05).set_z_index(7)
            mini_cards.add(VGroup(mb, m_bar, fit(txt(m_lbl, size=11.2, color=C_DARK_INK, bold=True, z=7), max_w=2.24).move_to(mb.get_center() + RIGHT * 0.05)))
        mini_cards.arrange(DOWN, buff=0.14).move_to([4.48, -0.22, 0])
        a4_foot = Rectangle(width=2.98, height=0.48, fill_color=C_DARK_INK, fill_opacity=1.0, stroke_width=0).move_to(a4_box.get_bottom() + UP * 0.24).set_z_index(6)
        a4_foot_t = fit(txt("본부 정밀 분석 → 창구 A4 1장 전달", size=11.2, color=C_GOLD, bold=True, z=7), max_w=2.72).move_to(a4_foot)
        proj_beam = arrow_2d([2.04, -0.15, 0], [2.92, -0.15, 0], color=C_GOLD, sw=3.2, tip=0.18, z=8)
        a4_full = VGroup(a4_box, a4_top_bar, a4_badge, a4_title, mini_cards, a4_foot, a4_foot_t)

        # Dock into Console & Zoom onto the Freshly Printed Ivory A4 Field Card!
        a4_laser = Line([2.98, 2.15, 0], [5.98, 2.15, 0], color=C_GOLD, stroke_width=3.6).set_z_index(12)
        self.add(a4_laser)
        self.cam_move(
            zoom=1.36,
            center=[3.25, -0.15, 0],
            anims=[
                four_strategies.animate.scale(0.43).move_to([-2.05, 0.52, 0]),
                FadeIn(app_window),
                FadeIn(app_win_hdr),
                FadeIn(tpl_bar, shift=UP * 0.08),
                FadeIn(nlq_bar, shift=UP * 0.08),
                GrowArrow(proj_beam),
                FadeIn(VGroup(a4_box, a4_top_bar, a4_title)),
                a4_laser.animate.move_to([4.48, -2.45, 0]),
                FadeIn(a4_badge, scale=1.2),
                LaggedStart(*[FadeIn(mc, shift=DOWN * 0.08) for mc in mini_cards], lag_ratio=0.12),
                FadeIn(VGroup(a4_foot, a4_foot_t)),
            ],
            rt=1.35,
        )
        self.remove(a4_laser)
        self.wait(0.80)
        self.reset_cam_2d(rt=0.85)

        ch8_stage = VGroup(app_window, app_win_hdr, four_strategies, tpl_bar, nlq_bar, proj_beam, a4_full)
        self.check_bounds(ch8_stage, "CH8C CONSOLE & CARD")
        self.wait(1.90)

        # ===================================================================
        # 9장 [~34s]: 도입 전과 도입 후 — 없던 것은 새로 만들고, 안 되던 것은 풀고, 불안하던 것은 고쳤습니다
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch8_stage,
            hl,
            hr,
            hb,
            9,
            "도입 전과 도입 후 — 없던 것은 새로 만들고, 안 되던 것은 풀고, 불안하던 것은 고쳤습니다",
            "수작업과 감에 의존하던 기존 업무가 어떻게 더 정확하고 편리하게 바뀌었는지 한눈에 정리합니다",
        )
        print(f"[TIMING] Ch8 end: {self.renderer.time:.2f}s")

        col_hdr_before = pill("도입 전 어려움 (Before)", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.0, z=8).move_to([-4.32, 2.60, 0])
        col_hdr_after = pill("도입 후 달라진 모습 (After)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.2, z=8).move_to([2.16, 2.60, 0])

        def make_ba_lane(ly: float, b_title: str, b_vis: VGroup, tag_s: str, a_col: str, a_title: str, a_widgets: VGroup) -> tuple[VGroup, VGroup, VGroup]:
            bc = RoundedRectangle(corner_radius=0.08, width=3.62, height=1.34, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.7).move_to([-4.32, ly, 0]).set_z_index(4)
            bt = fit(txt(b_title, size=10.2, color=C_CORAL, bold=True, z=7), max_w=3.36).move_to([-4.32, ly + 0.42, 0])
            b_vis = fit(b_vis, max_w=3.34).move_to([-4.32, ly - 0.18, 0]).set_z_index(7)

            arr = arrow_2d([-2.42, ly, 0], [-1.56, ly, 0], color=a_col, sw=2.8, tip=0.14, z=7)
            albl = pill(tag_s, fg=C_DARK_INK, bg=a_col, border=WHITE, size=9.2, px=0.09, py=0.03, z=8).move_to([-1.99, ly + 0.36, 0])

            ac = RoundedRectangle(corner_radius=0.08, width=7.24, height=1.34, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=a_col, stroke_width=2.2).move_to([2.16, ly, 0]).set_z_index(5)
            at = fit(txt(a_title, size=10.8, color=a_col, bold=True, z=7), max_w=6.88).move_to([2.16, ly + 0.44, 0])
            a_widgets = fit(a_widgets, max_w=6.85).move_to([2.16, ly - 0.16, 0]).set_z_index(8)
            return VGroup(bc, bt, b_vis), VGroup(arr, albl), VGroup(ac, at, a_widgets)

        bv1 = VGroup(
            Circle(radius=0.18, fill_opacity=0.0, stroke_color=C_SLATE, stroke_width=1.4),
            txt("수동 검색 ?", size=8.6, color=C_INK_2, bold=True),
            DashedVMobject(Rectangle(width=0.32, height=0.44, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=1.4), num_dashes=10),
            txt("요약카드 ×", size=8.6, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.12)

        ic_rad9_ring = Circle(radius=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_CYAN, stroke_width=1.8)
        ic_rad9_hand = Line([0, 0, 0], [0.15, 0.14, 0], color=C_GOLD, stroke_width=2.2)
        ic_rad9 = VGroup(ic_rad9_ring, ic_rad9_hand)
        ic_scr9 = RoundedRectangle(corner_radius=0.04, width=0.66, height=0.44, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.6)
        ic_a4_9 = VGroup(Rectangle(width=0.34, height=0.46, fill_color=C_IVORY, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.4), Line([-0.17, 0.23, 0], [0.17, 0.23, 0], color=C_CORAL, stroke_width=2.6))
        log_pill_9 = pill("AI 점검기록 13,671건", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.0, px=0.09, py=0.04)
        aw1 = VGroup(
            ic_rad9,
            txt("19개사 · 비용 0원", size=9.2, color=C_CYAN, bold=True),
            log_pill_9,
            ic_scr9,
            arrow_2d([0, 0, 0], [0.28, 0, 0], color=C_GOLD, sw=1.8, tip=0.08),
            ic_a4_9,
            txt("A4 1장", size=9.2, color=C_WHITE, bold=True),
        ).arrange(RIGHT, buff=0.12)
        b_l1, t_l1, a_l1 = make_ba_lane(1.24, "× [없던 체계] 일일이 수동 확인 · 창구 자료 없음", bv1, "신설 ✓", C_CYAN, "① 서버비 0원 자동 수집·검증 기준표 & 본부 화면 ↔ 창구 A4 요약 카드 신설", aw1)
        ic_rad9_hand.set_z_index(11)

        bv2 = VGroup(
            Rectangle(width=0.32, height=0.40, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.4),
            txt("308쪽 그림 ×", size=8.6, color=C_CORAL, bold=True),
            txt("·", size=12, color=C_SLATE),
            txt("특약 이름 ≠", size=8.8, color=C_AMBER, bold=True),
        ).arrange(RIGHT, buff=0.10)

        donut_arcs: list[Arc] = []

        def mini_donut(ratio: float, col: str, top_s: str, bot_s: str) -> VGroup:
            r = 0.26
            c0 = Circle(radius=r, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=2.4)
            arc = Arc(radius=r, start_angle=PI / 2, angle=-2 * PI * ratio, arc_center=ORIGIN, color=col, stroke_width=3.6)
            donut_arcs.append(arc)
            pct = txt(top_s, size=8.2, color=col, bold=True).move_to(c0)
            lbl = txt(bot_s, size=9.0, color=C_INK_0, bold=True)
            return VGroup(VGroup(c0, arc, pct), lbl).arrange(RIGHT, buff=0.08)

        aw2 = VGroup(
            mini_donut(1.0, C_MINT, "100%", "308쪽 계산오차 0건"),
            mini_donut(1.0, C_GOLD, "100%", "틀린 437건 전량 차단"),
            mini_donut(0.86, C_CYAN, "86%", "숨은 보장 29→25종 발굴"),
        ).arrange(RIGHT, buff=0.20)
        b_l2, t_l2, a_l2 = make_ba_lane(-0.20, "× [안 되던 비교] 그림 약관 · 제각각인 특약 이름", bv2, "해결 ✓", C_GOLD, "② AI 교차 읽기 + 계산 공식 분리 + 채점 전용 AI + 76종 연결 지도로 해결", aw2)

        bv3 = VGroup(
            Dot([0, 0, 0], radius=0.07, color=C_AMBER),
            txt("확인중=없음 착각", size=8.6, color=C_AMBER, bold=True),
            RegularPolygon(n=3, fill_color="#3D2B0D", fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.4).scale(0.16),
            txt("과장 위험 !", size=8.6, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.10)

        ic_sep9 = VGroup(Line([0, -0.18, 0], [0, 0.18, 0], color=C_MINT, stroke_width=2.2), DashedLine([0.14, -0.18, 0], [0.14, 0.18, 0], dash_length=0.06, color=C_AMBER, stroke_width=2.0))
        ic_shd9 = VGroup(RegularPolygon(n=6, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.8).scale(0.20), txt("✓", size=9.5, color=C_MINT, bold=True))
        aw3 = VGroup(
            ic_sep9,
            txt("확인중 672건 점선 구분", size=9.0, color=C_AMBER, bold=True),
            ic_shd9,
            txt("추측·과장 문구 차단", size=9.0, color=C_MINT, bold=True),
            pill("약관 쪽수 · 4가지 지침 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=9.0, px=0.09, py=0.04),
        ).arrange(RIGHT, buff=0.14)
        b_l3, t_l3, a_l3 = make_ba_lane(-1.64, "× [불안한 판단] 보장 누락 착각 · 과장 설명 위험", bv3, "개선 ✓", C_MINT, "③ 확인 중인 672건 점선 구분 + 없는 보험료 추측 금지 + 약관 쪽수 직결", aw3)

        before_cards = VGroup(b_l1, b_l2, b_l3)
        trans_arrows = VGroup(t_l1, t_l2, t_l3)
        after_cards = VGroup(a_l1, a_l2, a_l3)

        finale_ribbon = fit(
            pill("완성도 점검 완료 : 자동 점검 608개 통과 · 화면 오류 0건 · 앞으로 보험료·질병코드표까지 넓힐 기반 완성 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.68, 0])

        # 1) Zoom onto Before Friction!
        self.cam_move(
            zoom=1.24,
            center=[-4.15, 0.25, 0],
            anims=[
                FadeIn(col_hdr_before, shift=DOWN * 0.08),
                LaggedStart(*[FadeIn(bc, shift=RIGHT * 0.12) for bc in before_cards], lag_ratio=0.10),
            ],
            rt=1.15,
        )
        self.wait(1.30)

        # 2) Track Right as Golden Pulses cross & Donut Gauges Live-Sweep 0 -> 100% / 100% / 86%!
        pulses_9 = VGroup(
            glow_dot([-2.42, 1.24, 0], color=C_CYAN, r=0.06, z=12),
            glow_dot([-2.42, -0.20, 0], color=C_GOLD, r=0.06, z=12),
            glow_dot([-2.42, -1.64, 0], color=C_MINT, r=0.06, z=12),
        )
        self.add(pulses_9, ic_rad9_hand)
        self.cam_move(
            zoom=1.24,
            center=[1.95, 0.20, 0],
            anims=[
                FadeIn(col_hdr_after, shift=DOWN * 0.08),
                LaggedStart(*[FadeIn(ta, scale=0.9) for ta in trans_arrows], lag_ratio=0.10),
                MoveAlongPath(pulses_9[0], Line([-2.42, 1.24, 0], [-1.56, 1.24, 0])),
                MoveAlongPath(pulses_9[1], Line([-2.42, -0.20, 0], [-1.56, -0.20, 0])),
                MoveAlongPath(pulses_9[2], Line([-2.42, -1.64, 0], [-1.56, -1.64, 0])),
                FadeIn(VGroup(a_l1[0], a_l1[1], ic_rad9_ring, *aw1[1:]), shift=LEFT * 0.10),
                Rotate(ic_rad9_hand, angle=-TAU, about_point=ic_rad9_ring.get_center()),
                FadeIn(VGroup(a_l2[0], a_l2[1], aw2[0][0][0], aw2[0][0][2], aw2[0][1], aw2[1][0][0], aw2[1][0][2], aw2[1][1], aw2[2][0][0], aw2[2][0][2], aw2[2][1])),
                *[Create(da) for da in donut_arcs],
                FadeIn(a_l3, shift=LEFT * 0.12),
                Flash(ic_shd9.get_center(), color=C_MINT, line_length=0.22, num_lines=8),
            ],
            rt=1.50,
        )
        self.remove(pulses_9, *pulses_9)
        self.wait(1.50)

        # 3) Pull back to Grand Panoramic Finale!
        self.reset_cam_2d(
            anims=[
                FadeIn(finale_ribbon, shift=UP * 0.08),
                LaggedStart(*[Circumscribe(ac[0], color=C_GOLD, stroke_width=2.0, buff=0.03) for ac in after_cards], lag_ratio=0.12),
            ],
            rt=1.05,
        )

        ch9_stage = VGroup(col_hdr_before, col_hdr_after, before_cards, trans_arrows, after_cards, finale_ribbon)
        self.check_bounds(ch9_stage, "CH9 VISUAL BEFORE AFTER")
        self.wait(3.80)
        print(f"[TIMING] Part 4 end: {self.renderer.time:.2f}s")
