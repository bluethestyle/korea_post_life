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
    C_CYAN_DIM,
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
    build_canvas,
    capacity_ring,
    fit,
    glow_dot,
    pill,
    txt,
)


class Part4OntologyImpactScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.add(build_canvas())

        # ===================================================================
        # 7장 [~35s]: 온톨로지·단독 화면 프로세스 — 2x2 난제 보드와 3계층·관계망 해법
        # ===================================================================
        hl, hr, hb = self.make_hud(
            7,
            "온톨로지·단독 화면 프로세스 — 용량 제약과 명칭 불일치를 넘은 방법",
            "단일 파일 4MB 상한 안에서 회사별 명칭 불일치와 대량 미매핑, 미보유 오판 위험을 동시에 풀어야 했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 7A: Left Resource Gauges + Right 2x2 Visual Comparison Obstacles
        # -------------------------------------------------------------------
        res_box_7 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=2.0).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_7 = pill("저장 · 배포 제약", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, z=7).move_to([-4.38, 1.92, 0])

        rg7_1 = capacity_ring([-5.15, 0.72, 0], 0.58, 0.74, C_GOLD, "단독 HTML", "4MB 상한 제약", z=6)
        rg7_2 = capacity_ring([-3.62, 0.72, 0], 0.58, 0.12, C_CYAN, "서버 예산", "0원 (시트 13탭)", z=6)

        size_bg = RoundedRectangle(corner_radius=0.04, width=2.84, height=0.24, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.4).move_to([-4.38, -0.62, 0]).set_z_index(6)
        size_fg = RoundedRectangle(corner_radius=0.03, width=2.08, height=0.16, fill_color=C_MINT, fill_opacity=0.92, stroke_width=0).move_to([-4.74, -0.62, 0]).set_z_index(7)
        size_lbl = txt("현재 빌드 2.97MB / 4.0MB 통과 ✓", size=9.2, color=C_MINT, bold=True, z=7).move_to([-4.38, -1.04, 0])
        res_sub_7 = txt("정적 파일 1개에 정본·화면 내장", size=9.4, color=C_INK_2, z=7).move_to([-4.38, -1.56, 0])
        res_grp_7 = VGroup(res_box_7, res_hdr_7, rg7_1, rg7_2, size_bg, size_fg, size_lbl, res_sub_7)
        vs_arr_7 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=1.9).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=10.8, color=col, bold=True, z=7), max_w=3.44).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        # Q1 (-0.10, 1.18): Name & Payout-type mismatch chips
        q7_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 특약명 · 고지약칭 · 지급방식 상이")
        m7_r1 = VGroup(
            pill('"315 간편"', fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.6, px=0.08, py=0.03).move_to([-1.05, 1.32, 0]),
            txt("≠", size=14, color=C_CORAL, bold=True).move_to([-0.10, 1.32, 0]),
            pill('"간편가입형(1년)"', fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.6, px=0.08, py=0.03).move_to([0.92, 1.32, 0]),
        ).set_z_index(7)
        m7_r2 = VGroup(
            pill("수술 회당 지급", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.08, py=0.03).move_to([-1.02, 0.80, 0]),
            txt("≠", size=14, color=C_CORAL, bold=True).move_to([-0.10, 0.80, 0]),
            pill("연간 1회 지급", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.6, px=0.08, py=0.03).move_to([0.92, 0.80, 0]),
        ).set_z_index(7)
        q7_1_cap = txt("단순 문자열·금액 비교 불가능", size=9.0, color=C_INK_1, z=7).move_to([-0.10, 0.42, 0])

        # Q2 (3.88, 1.18): 52-std small funnel overflowing with 1,951 unmapped rows!
        q7_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 초기 52종 사전 → 1,951줄 미매핑")
        fun_box = pill("기존 사전 52종", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=8.8, px=0.09, py=0.04, z=7).move_to([2.92, 1.12, 0])
        spill_dots = VGroup(*[Dot([3.95 + (k % 5) * 0.26, 1.38 - (k // 5) * 0.26, 0], radius=0.055, color=C_AMBER if k % 2 == 0 else C_CORAL) for k in range(10)]).set_z_index(7)
        q7_2_cap = txt("한화 급부 388종류(1,951줄) 대기 적체", size=9.0, color=C_CORAL, bold=True, z=7).move_to([3.88, 0.44, 0])

        # Q3 (-0.10, -1.14): Integrated vs Split false 'Missing' stamp
        q7_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 통합 대 분리 오판 · 대기 건 착시")
        int_vs_spl = VGroup(
            pill("타사 통합특약 ◆", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.6, px=0.08, py=0.03).move_to([-1.06, -1.04, 0]),
            arrow_2d([-0.30, -1.04, 0], [0.16, -1.04, 0], color=C_CORAL, sw=1.8, tip=0.08),
            pill("미보유 오판 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.6, px=0.08, py=0.03).move_to([0.92, -1.04, 0]),
        ).set_z_index(7)
        q7_3_cap = txt("당사 분리특약 보유분 누락 · 대기 건을 공백으로 오인", size=8.8, color=C_INK_1, z=7).move_to([-0.10, -1.74, 0])

        # Q4 (3.88, -1.14): Pre-bake blowing past 4MB + Missing rider premium slot
        q7_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 사전 저장 시 4MB 초과 · 보험료 부재")
        ov_bar_bg = RoundedRectangle(corner_radius=0.04, width=1.85, height=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.2).move_to([3.05, -0.96, 0]).set_z_index(6)
        ov_bar_fg = Rectangle(width=2.15, height=0.16, fill_color=C_CORAL, fill_opacity=0.92, stroke_width=0).move_to([3.20, -0.96, 0]).set_z_index(7)
        ov_lim = Line([3.78, -1.14, 0], [3.78, -0.78, 0], color=WHITE, stroke_width=2.0).set_z_index(8)
        ov_tag = txt(">4MB ×", size=8.6, color=C_CORAL, bold=True, z=8).move_to([4.88, -0.96, 0])
        no_prem = DashedVMobject(RoundedRectangle(corner_radius=0.04, width=2.92, height=0.38, fill_opacity=0.0, stroke_color=C_INK_2, stroke_width=1.4).move_to([3.88, -1.56, 0]), num_dashes=20).set_z_index(6)
        no_prem_t = txt("특약별 보험료 : 공시 문서에 부재", size=8.8, color=C_INK_2, bold=True, z=7).move_to([3.88, -1.56, 0])

        self.play(
            FadeIn(hl, shift=DOWN * 0.08), FadeIn(hr, shift=DOWN * 0.08), FadeIn(hb, shift=UP * 0.08),
            FadeIn(VGroup(res_box_7, res_hdr_7, rg7_1[0], rg7_1[2], rg7_2[0], rg7_2[2], size_bg, size_lbl, res_sub_7), shift=RIGHT * 0.12),
            Create(rg7_1[1]), Create(rg7_2[1]), GrowFromEdge(size_fg, LEFT),
            GrowArrow(vs_arr_7),
            FadeIn(VGroup(q7_1, m7_r1, m7_r2, q7_1_cap)),
            FadeIn(VGroup(q7_2, fun_box, q7_2_cap)),
            LaggedStart(*[FadeIn(sd, scale=0.4) for sd in spill_dots], lag_ratio=0.03),
            run_time=1.10,
        )
        self.play(
            FadeIn(VGroup(q7_3, int_vs_spl, q7_3_cap), shift=UP * 0.08),
            FadeIn(VGroup(q7_4, ov_bar_bg, ov_lim, ov_tag, no_prem, no_prem_t), shift=UP * 0.08),
            GrowFromEdge(ov_bar_fg, LEFT),
            run_time=1.05,
        )
        beat7a_all = VGroup(
            res_grp_7, vs_arr_7,
            q7_1, m7_r1, m7_r2, q7_1_cap,
            q7_2, fun_box, spill_dots, q7_2_cap,
            q7_3, int_vs_spl, q7_3_cap,
            q7_4, ov_bar_bg, ov_bar_fg, ov_lim, ov_tag, no_prem, no_prem_t,
        )
        self.check_bounds(beat7a_all, "CH7A ONTOLOGY DIAGNOSTIC")
        self.wait(2.55)

        # -------------------------------------------------------------------
        # Beat 7B: Solution 1 - 3-Layer Ontology Architecture + Ascending Pulses
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 원천 사실과 표준 기준만 정본으로 담고(2.97MB), 비교·시사점은 화면에서 조건 선택 즉시 산출합니다",
            rt=0.38,
        )

        def make_layer_band(y_c: float, h_b: float, col: str, fill_c: str, title_s: str, sub_s: str) -> tuple[RoundedRectangle, VGroup]:
            band = RoundedRectangle(corner_radius=0.08, width=11.90, height=h_b, fill_color=fill_c, fill_opacity=0.90, stroke_color=col, stroke_width=2.0).move_to([0.0, y_c, 0]).set_z_index(2)
            sep = Line([-3.25, y_c - h_b * 0.38, 0], [-3.25, y_c + h_b * 0.38, 0], color=col, stroke_width=1.4, stroke_opacity=0.65).set_z_index(4)
            hdr = fit(VGroup(txt(title_s, size=13.5, color=col, bold=True, z=7), txt(sub_s, size=10.4, color=C_INK_1, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.05), max_w=2.40).move_to([-4.62, y_c, 0])
            return band, VGroup(sep, hdr)

        b_der, h_der = make_layer_band(1.62, 1.00, C_VIOLET, "#171528", "분석 · 시사점 계층", "저장 없이 화면 즉시 산출")
        d_n1 = pill("동일 심사등급 경쟁종형 대조", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.2, px=0.11, py=0.06).move_to([-1.85, 1.62, 0])
        d_n2 = pill("대응 특약 · 지급조건 대조", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=11.2, px=0.11, py=0.06).move_to([1.25, 1.62, 0])
        d_n4 = pill("★ 영업 · 상품기획 시사점 도출", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.4, px=0.13, py=0.06).move_to([4.25, 1.62, 0])
        layer_der = VGroup(b_der, h_der, d_n1, d_n2, d_n4, arrow_2d(d_n1.get_right(), d_n2.get_left(), color=C_VIOLET, sw=1.8, tip=0.10, z=6), arrow_2d(d_n2.get_right(), d_n4.get_left(), color=C_GOLD, sw=1.8, tip=0.10, z=6))

        b_std, h_std = make_layer_band(0.14, 1.08, C_GOLD, "#1E1B12", "표준 기준 계층", "타사 특약 · 심사기준 표준화")
        s_grade = pill("심사유형 · 간편고지 등급 체계", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=11.0, px=0.11, py=0.06).move_to([-1.68, 0.14, 0])
        sd1 = Square(side_length=0.20, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([0.65, 0.34, 0]).set_z_index(7)
        sd2 = Square(side_length=0.18, fill_color=C_MINT, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.2).rotate(PI / 4).move_to([1.45, 0.46, 0]).set_z_index(7)
        sd3 = Square(side_length=0.18, fill_color=C_CYAN, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.2).rotate(PI / 4).move_to([1.45, 0.02, 0]).set_z_index(7)
        s_dag_grp = VGroup(Line(sd1.get_center(), sd2.get_center(), color=C_GOLD, stroke_width=2.0).set_z_index(6), Line(sd1.get_center(), sd3.get_center(), color=C_MINT, stroke_width=2.0).set_z_index(6), sd1, sd2, sd3, txt("◆ 표준담보 76종 및 포함·합산 관계", size=11.0, color=C_GOLD, bold=True, z=7).move_to([1.35, -0.24, 0]))
        s_pay = pill("지급형태 · 치료 5단계 분류", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, px=0.11, py=0.06).move_to([4.32, 0.14, 0])
        layer_std = VGroup(b_std, h_std, s_grade, s_dag_grp, s_pay)

        b_fct, h_fct = make_layer_band(-1.38, 1.12, C_CYAN, "#101B24", "원천 사실 계층", "공시 문서 · 시장동향 정본")
        f_org_s = RegularPolygon(n=6, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).scale(0.16).move_to([-2.48, -1.24, 0]).set_z_index(7)
        f_var_s = RoundedRectangle(corner_radius=0.04, width=0.30, height=0.26, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).move_to([-0.82, -1.24, 0]).set_z_index(7)
        f_rid_s = Circle(radius=0.14, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).move_to([1.00, -1.24, 0]).set_z_index(7)
        f_ben_s = Circle(radius=0.12, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.4).move_to([2.88, -1.24, 0]).set_z_index(7)
        f_nws_s = RegularPolygon(n=5, fill_color=C_VIOLET, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).scale(0.15).move_to([4.72, -1.24, 0]).set_z_index(7)
        layer_fct = VGroup(
            b_fct, h_fct, f_org_s, f_var_s, f_rid_s, f_ben_s, f_nws_s,
            txt("19개 보험기관", size=10.8, color=C_INK_0, bold=True, z=7).move_to([-2.48, -1.64, 0]),
            txt("23개 상품 종형", size=10.8, color=C_INK_0, bold=True, z=7).move_to([-0.82, -1.64, 0]),
            txt("2,747개 특약", size=10.8, color=C_INK_0, bold=True, z=7).move_to([1.00, -1.64, 0]),
            txt("6,615건 세부 급부", size=10.8, color=C_GOLD, bold=True, z=7).move_to([2.88, -1.64, 0]),
            txt("주간 시장동향", size=10.8, color=C_VIOLET, bold=True, z=7).move_to([4.72, -1.64, 0]),
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
            pill("용량·정확성 동시 해결 : 단독 파일 2.97MB(4MB 미만) 유지 · 공시 부재 값(특약 보험료·미적재 한도)은 추정 표시 제외 ✓", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=11.0),
            max_w=11.85,
        ).move_to([0.0, -2.56, 0]).set_z_index(9)

        self.play(FadeOut(beat7a_all, shift=UP * 0.10), FadeIn(layer_fct, shift=UP * 0.12), FadeIn(layer_std, shift=UP * 0.12), FadeIn(layer_der, shift=UP * 0.12), run_time=1.00)
        self.remove(beat7a_all)

        up_pulses = VGroup(*[glow_dot(p0, color=col, r=0.055, z=14) for p0, _, col in up_coords])
        self.add(up_pulses)
        self.play(
            LaggedStart(*[GrowArrow(va) for va in cross_layer_arrows], lag_ratio=0.06),
            *[MoveAlongPath(up_pulses[k], Line(up_coords[k][0], up_coords[k][1])) for k in range(6)],
            FadeIn(foot_7b, shift=UP * 0.08),
            Circumscribe(d_n4[0], color=WHITE, stroke_width=2.2, buff=0.04),
            run_time=1.00,
        )
        self.remove(up_pulses, *up_pulses)
        beat7b_all = VGroup(layer_fct, layer_std, layer_der, cross_layer_arrows, foot_7b)
        self.check_bounds(beat7b_all, "CH7B THREE LAYERS")
        self.wait(2.40)

        # -------------------------------------------------------------------
        # Beat 7C: Network Graph (Pending 672 Dashed) & Standard Dictionary 52 -> 76
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 검토 대기 672건은 점선으로 분리해 오판을 막고, 표준담보 사전을 52종에서 76종으로 넓혀 986건을 흡수했습니다",
            rt=0.38,
        )

        G = nx.Graph()
        n_per_org, n_hubs = 15, 9
        total_v = n_per_org * 3 + n_hubs
        for h_i in range(n_hubs - 1):
            G.add_edge(45 + h_i, 45 + h_i + 1)
        G.add_edge(45, 49); G.add_edge(46, 51); G.add_edge(48, 53)
        for c_idx in range(3):
            base = c_idx * n_per_org
            for k in range(1, 4):
                G.add_edge(base, base + k)
            for k in range(4, n_per_org):
                G.add_edge(base + 1 + ((k - 4) % 3), base + k)
                G.add_edge(base + k, 45 + ((k * 2 + c_idx * 3) % n_hubs))

        raw_pos = nx.spring_layout(G, seed=19, k=0.46, iterations=90)
        xs = np.array([raw_pos[i][0] for i in range(total_v)])
        ys = np.array([raw_pos[i][1] for i in range(total_v)])
        xs = (xs - xs.mean()) / (xs.max() - xs.min() + 1e-6) * 10.2
        ys = (ys - ys.mean()) / (ys.max() - ys.min() + 1e-6) * 4.05 - 0.08
        net_pts = {i: np.array([xs[i], ys[i], 0.0]) for i in range(total_v)}

        radar_bg = VGroup(
            *[Circle(radius=rad, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=0.8, stroke_opacity=0.14).move_to([0, -0.08, 0]) for rad in [1.15, 2.30, 3.45, 4.65]],
            Line([-5.8, -0.08, 0], [5.8, -0.08, 0], color=C_CYAN, stroke_width=0.7, stroke_opacity=0.10),
            Line([0, -2.85, 0], [0, 2.75, 0], color=C_CYAN, stroke_width=0.7, stroke_opacity=0.10),
        ).set_z_index(1)

        net_vertices = VGroup()
        for i in range(total_v):
            pt = net_pts[i]
            if i >= 45:
                v_mob: Mobject = Square(side_length=0.20, fill_color=C_GOLD, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.5).rotate(PI / 4).move_to(pt)
            elif i % 15 == 0:
                c_col = C_GOLD if i == 0 else (C_CYAN if i == 15 else C_VIOLET)
                v_mob = RegularPolygon(n=6, fill_color=c_col, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.6).scale(0.16).move_to(pt)
            else:
                c_col = C_GOLD if i < 15 else (C_CYAN if i < 30 else C_VIOLET)
                v_mob = Circle(radius=0.074, fill_color=c_col, fill_opacity=0.88, stroke_color=c_col, stroke_width=1.2).move_to(pt)
            v_mob.set_z_index(5)
            net_vertices.add(v_mob)

        intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges = VGroup(), VGroup(), VGroup(), VGroup()
        bridge_counter = 0
        for u, v in G.edges():
            if u >= 45 and v >= 45:
                dag_edges.add(Line(net_pts[u], net_pts[v], color=C_GOLD, stroke_width=2.2, stroke_opacity=0.92).set_z_index(4))
            elif u < 45 and v < 45:
                intra_edges.add(Line(net_pts[u], net_pts[v], color=C_SLATE, stroke_width=1.1, stroke_opacity=0.52).set_z_index(3))
            else:
                bridge_counter += 1
                if bridge_counter % 4 == 0:
                    waiting_dashed_edges.add(DashedLine(net_pts[u], net_pts[v], dash_length=0.09, color=C_AMBER, stroke_width=1.7, stroke_opacity=0.88).set_z_index(4))
                else:
                    confirmed_bridge_edges.add(Line(net_pts[u], net_pts[v], color=C_MINT, stroke_width=1.4, stroke_opacity=0.72).set_z_index(3))

        build_banner = fit(
            pill("온톨로지 관계망 : 6,615건 급부 전량 1대1 매핑 연결 (누락 0건) · 매핑 확정 3,807건 실선 vs 검토 대기 672건 점선 분리", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.4),
            max_w=11.85,
        ).move_to([0, 2.70, 0]).set_z_index(12)
        build_legend = fit(
            VGroup(
                pill("◆ 담보 포함·합산 관계 (31건)", fg=C_GOLD, bg=C_PANEL, border=C_GOLD_DEEP, size=11.0),
                pill("●─● 매핑 확정 급부 (실선 3,807건)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=11.0),
                pill("●- -● 검토 대기 급부 (점선 672건 · 미보유 오판 방지)", fg=C_AMBER, bg=C_PANEL, border=C_AMBER, size=11.0),
            ).arrange(RIGHT, buff=0.14),
            max_w=11.85,
        ).move_to([0, -2.70, 0]).set_z_index(12)

        self.play(
            FadeOut(beat7b_all, shift=UP * 0.10),
            FadeIn(radar_bg), FadeIn(net_vertices, lag_ratio=0.01),
            Create(intra_edges, lag_ratio=0.01), Create(dag_edges, lag_ratio=0.03),
            Create(confirmed_bridge_edges, lag_ratio=0.01), Create(waiting_dashed_edges, lag_ratio=0.02),
            FadeIn(build_banner, shift=DOWN * 0.08), FadeIn(build_legend, shift=UP * 0.08),
            run_time=1.30,
        )
        self.remove(beat7b_all)
        self.wait(2.05)

        all_net_lines = VGroup(intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges)
        self.play(all_net_lines.animate.set_stroke(opacity=0.14), net_vertices.animate.set_opacity(0.16), FadeOut(build_banner), FadeOut(build_legend), run_time=0.40)
        self.remove(build_banner, build_legend)

        z1_card = RoundedRectangle(corner_radius=0.08, width=3.30, height=4.35, fill_color=C_PANEL, fill_opacity=0.88, stroke_color=C_CYAN, stroke_width=1.9).move_to([-4.32, -0.05, 0]).set_z_index(4)
        z1_old = fit(pill("직전 상품 (간편건강 2504)", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=11.2, z=7), max_w=2.95).move_to([-4.32, 0.92, 0])
        z1_new = fit(pill("현행 상품 (간편한건강 2606)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.4, z=7), max_w=2.95).move_to([-4.32, -0.18, 0])
        exp_left = VGroup(
            z1_card, fit(txt("확장 ① 상품 개정 전후 계보 연결", size=13.2, color=C_CYAN, bold=True, z=7), max_w=3.02).move_to([-4.32, 1.72, 0]),
            z1_old, z1_new, arrow_2d(z1_old.get_bottom(), z1_new.get_top(), color=C_GOLD, sw=2.2, tip=0.12, z=7),
            pill("특약 계보 자동 승계", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=10.3, px=0.10, py=0.03, z=8).move_to([-4.32, 0.37, 0]),
            fit(pill("정밀비교 3개사 → 19개사 단계 확대", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.6, z=7), max_w=2.95).move_to([-4.32, -0.92, 0]),
            fit(txt("변경 약관만 재추출 · 기존 검수분 유지", size=10.4, color=C_INK_1, z=7), max_w=2.98).move_to([-4.32, -1.62, 0]),
        )

        z2_card = RoundedRectangle(corner_radius=0.08, width=4.36, height=4.35, fill_color=C_PANEL, fill_opacity=0.90, stroke_color=C_MINT, stroke_width=2.2).move_to([0.0, -0.05, 0]).set_z_index(4)
        z2_t = fit(txt("확장 ② 표준담보 사전 확장 (52 → 76종)", size=13.5, color=C_MINT, bold=True, z=7), max_w=4.05).move_to([0.0, 1.72, 0])
        z2_sub = fit(txt("18개 보험사 요약서 35종 조사로 신종 담보 보강", size=10.8, color=C_INK_1, z=7), max_w=4.02).move_to([0.0, 1.28, 0])

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
        remap_ok = fit(pill("신규 표준담보 25종 신설 → 미분류 급부 986건 편입 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=11.0, z=9), max_w=4.05).move_to([0.0, -1.52, 0])

        z3_card = RoundedRectangle(corner_radius=0.08, width=3.30, height=4.35, fill_color=C_PANEL, fill_opacity=0.88, stroke_color=C_VIOLET, stroke_width=1.9).move_to([4.32, -0.05, 0]).set_z_index(4)
        z3_news = fit(pill("타사 신상품 · 배타적사용권 보도", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.0, z=7), max_w=2.95).move_to([4.32, 0.95, 0])
        z3_xr = pill("배타적사용권", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.2, px=0.09, py=0.05, z=7).move_to([3.52, 0.08, 0])
        z3_cand = pill("신규 담보 후보", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=10.5, px=0.10, py=0.05, z=7).move_to([5.08, 0.08, 0])
        z3_prom = fit(pill("◆ 차기 표준담보 편입 후보", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.0, z=7), max_w=2.95).move_to([4.32, -0.85, 0])
        exp_right = VGroup(
            z3_card, fit(txt("확장 ③ 시장동향 → 신규 담보 후보", size=13.2, color=C_VIOLET, bold=True, z=7), max_w=3.02).move_to([4.32, 1.72, 0]),
            z3_news, z3_xr, z3_cand, z3_prom,
            arrow_2d(z3_news.get_bottom() + LEFT * 0.35, z3_xr.get_top(), color=C_VIOLET, sw=1.7, tip=0.10, z=6),
            arrow_2d(z3_news.get_bottom() + RIGHT * 0.35, z3_cand.get_top(), color=C_MINT, sw=1.7, tip=0.10, z=6),
            arrow_2d(z3_cand.get_bottom(), z3_prom.get_top() + RIGHT * 0.35, color=C_GOLD, sw=2.0, tip=0.11, z=6),
            fit(txt("다수 보험사 출시 확인 시 정식 표준담보 등록", size=10.4, color=C_INK_1, z=7), max_w=3.02).move_to([4.32, -1.62, 0]),
        )

        self.play(FadeIn(exp_left, shift=UP * 0.12), FadeIn(VGroup(z2_card, z2_t, z2_sub, drift_dots), shift=UP * 0.12), FadeIn(exp_right, shift=UP * 0.12), run_time=0.85)
        self.play(
            FadeIn(new_hubs_4c, scale=0.3), FadeIn(new_hub_lbls),
            *[drift_dots[idx].animate.move_to(target_positions_4c[idx]).set_color(C_GOLD if (idx // 4) == 1 else C_MINT) for idx in range(12)],
            Create(remap_edges, lag_ratio=0.02), FadeIn(remap_ok, shift=UP * 0.08),
            run_time=1.00,
        )
        bg_cosmos = VGroup(radar_bg, all_net_lines, net_vertices)
        fg_7c = VGroup(exp_left, z2_card, z2_t, z2_sub, drift_dots, new_hubs_4c, new_hub_lbls, remap_edges, remap_ok, exp_right)
        self.check_bounds(fg_7c, "CH7C EXPANSION")
        self.wait(2.35)

        # ===================================================================
        # 8장 [~34s]: 지식그래프 담보 해석 · 관문·치료여정 차트 · 4대 전략과 A4 카드
        # ===================================================================
        nl8, nr8, nb8 = self.make_hud(
            8,
            "지식그래프 담보 분석과 실행 — 합산 탐색·관문 차트부터 응대 카드까지",
            "타사는 통합특약 하나로, 우체국은 분리특약 두 개로 운영하는 경우 포함·합산 관계로 실질 보장을 찾아냅니다",
        )
        self.play(
            FadeOut(fg_7c, shift=UP * 0.12, run_time=0.50),
            Succession(FadeOut(hl, shift=UP * 0.05, run_time=0.22), FadeIn(nl8, shift=UP * 0.05, run_time=0.28)),
            ReplacementTransform(hr[1], nr8[1], run_time=0.50),
            FadeOut(hr[0], run_time=0.25), FadeIn(nr8[0], run_time=0.25),
            Succession(FadeOut(hb, shift=DOWN * 0.05, run_time=0.22), FadeIn(nb8, shift=UP * 0.05, run_time=0.28)),
        )
        self.remove(fg_7c)
        hl, hr, hb = nl8, nr8, nb8
        print(f"[TIMING] Ch7 end: {self.renderer.time:.2f}s")

        # -------------------------------------------------------------------
        # Beat 8A: Multi-Hop Coverage Graph Traversal
        # -------------------------------------------------------------------
        def graph_hub(label: str, pos: list[float], col: str = C_GOLD, r: float = 0.22, lbl_dir: np.ndarray = DOWN) -> VGroup:
            dm = Square(side_length=r * 1.5, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.5).rotate(PI / 4).move_to(pos).set_z_index(8)
            core = Square(side_length=r * 0.55, fill_color=col, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to(pos).set_z_index(9)
            lb = pill(label, fg=col, bg=C_BG_SUB, border=col, size=12.0, px=0.12, py=0.05, z=9).next_to(dm, lbl_dir, buff=0.11)
            return VGroup(dm, core, lb)

        def graph_entity(label: str, sub: str, pos: list[float], col: str, is_square: bool = True) -> VGroup:
            if is_square:
                sh: Mobject = RoundedRectangle(corner_radius=0.07, width=1.58, height=0.68, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).move_to(pos).set_z_index(8)
                tg = fit(VGroup(txt(label, size=12.8, color=WHITE, bold=True, z=9), txt(sub, size=10.5, color=col, z=9)).arrange(DOWN, buff=0.04), max_w=1.42).move_to(pos)
                return VGroup(sh, tg)
            sh = Circle(radius=0.31, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).move_to(pos).set_z_index(8)
            return VGroup(sh, txt(label, size=11.2, color=WHITE, bold=True, z=9).move_to(pos), txt(sub, size=10.6, color=col, bold=True, z=9).next_to(sh, DOWN, buff=0.09))

        cv1 = pill("◆ 뇌·심장 진단", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=12.0, px=0.13, py=0.06, z=8).move_to([-2.15, 2.22, 0])
        cv2 = pill("◆ 뇌혈관 진단", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.0, px=0.13, py=0.06, z=8).move_to([0.00, 2.22, 0])
        cv3 = pill("◆ 뇌졸중", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.0, px=0.13, py=0.06, z=8).move_to([1.95, 2.22, 0])
        cv4 = pill("◆ 뇌출혈", fg=C_WHITE, bg=C_PANEL_HI, border=C_WHITE, size=12.0, px=0.13, py=0.06, z=8).move_to([3.70, 2.22, 0])
        top_chain_grp = VGroup(
            txt("보장 범위 포함 관계 :", size=12.2, color=C_GOLD, bold=True, z=9).move_to([-4.62, 2.22, 0]),
            cv1, cv2, cv3, cv4,
            arrow_2d(cv1.get_right(), cv2.get_left(), color=C_GOLD, sw=2.0, tip=0.11, z=8),
            arrow_2d(cv2.get_right(), cv3.get_left(), color=C_CYAN, sw=2.0, tip=0.11, z=8),
            arrow_2d(cv3.get_right(), cv4.get_left(), color=C_CYAN, sw=2.0, tip=0.11, z=8),
        )

        n_peer_rider = graph_entity("타사 상품", "통합형 특약 운영", [-5.05, -0.25, 0], C_CYAN, is_square=True)
        n_peer_ben = graph_entity("특약", "통합수술", [-3.35, -0.25, 0], C_CYAN, is_square=False)
        h_integrated = graph_hub("뇌·심장질환 수술비", [-1.45, -0.25, 0], C_GOLD, r=0.25, lbl_dir=UP)
        sel_ring = DashedVMobject(Circle(radius=0.52, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.0).move_to([-1.45, -0.25, 0]), num_dashes=24).set_z_index(7)
        h_part_br = graph_hub("뇌혈관질환 수술비", [0.85, 0.72, 0], C_MINT, r=0.21, lbl_dir=UP)
        h_part_ht = graph_hub("심장질환 수술비", [0.85, -1.22, 0], C_MINT, r=0.21, lbl_dir=DOWN)
        n_ep_ben1 = graph_entity("특약①", "당사 운영", [2.95, 0.72, 0], C_GOLD, is_square=False)
        n_ep_ben2 = graph_entity("특약②", "당사 운영", [2.95, -1.22, 0], C_GOLD, is_square=False)
        n_ep_prod = graph_entity("우체국 2606", "분리 특약 보장", [4.95, -0.25, 0], C_GOLD, is_square=True)

        e_hop1_a = Line([-1.12, -0.05, 0], [0.55, 0.62, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop1_b = Line([-1.12, -0.45, 0], [0.55, -1.12, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop2_a = Line([1.16, 0.72, 0], [2.62, 0.72, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop2_b = Line([1.16, -1.22, 0], [2.62, -1.22, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop3_a = Line([3.27, 0.62, 0], [4.16, -0.02, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop3_b = Line([3.27, -1.12, 0], [4.16, -0.48, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)

        fg_subgraph = VGroup(
            top_chain_grp, n_peer_rider, n_peer_ben, h_integrated, sel_ring, h_part_br, h_part_ht, n_ep_ben1, n_ep_ben2, n_ep_prod,
            arrow_2d(n_peer_rider[0].get_right(), n_peer_ben[0].get_left(), color=C_CYAN, sw=2.0, tip=0.11, z=7),
            arrow_2d(n_peer_ben[0].get_right(), [-1.82, -0.25, 0], color=C_CYAN, sw=2.0, tip=0.11, z=7),
            e_hop1_a, e_hop1_b,
            pill("분리특약 합산 대응", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=9.6, px=0.08, py=0.03, z=9).move_to([-0.08, 0.46, 0]),
            pill("분리특약 합산 대응", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=9.6, px=0.08, py=0.03, z=9).move_to([-0.08, -0.96, 0]),
            e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b,
        )
        self.play(FadeIn(fg_subgraph, lag_ratio=0.03), run_time=0.90)

        bad_arc = DashedVMobject(CubicBezier(np.array([-1.45, -0.62, 0]), np.array([0.2, -2.55, 0]), np.array([3.2, -2.55, 0]), np.array([4.95, -0.62, 0]), color=C_CORAL, stroke_width=2.4), num_dashes=28).set_z_index(10)
        bad_1hop_lbl = fit(pill('단순 특약명 대조 시 : "통합수술비 특약이 없으니 미보유"로 오판 ×', fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.6, z=11), max_w=8.50).move_to([1.65, -2.38, 0])
        self.play(Create(bad_arc), FadeIn(bad_1hop_lbl, shift=UP * 0.08), run_time=0.65)

        hop_badge = fit(pill("합산 관계 탐색 ✓ : 외견상 미보유 29종 중 25종이 분리·상위 특약으로 실질 보장 확인!", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=11.6, z=12), max_w=9.20).move_to([1.45, -2.38, 0])
        p_up, p_dn = glow_dot([-1.12, -0.05, 0], color=C_MINT, r=0.068, z=14), glow_dot([-1.12, -0.45, 0], color=C_MINT, r=0.068, z=14)
        self.add(p_up, p_dn)
        self.play(FadeOut(bad_arc), FadeOut(bad_1hop_lbl), Rotate(sel_ring, angle=PI / 3), MoveAlongPath(p_up, e_hop1_a), MoveAlongPath(p_dn, e_hop1_b), e_hop1_a.animate.set_stroke(color=C_MINT, width=3.4), e_hop1_b.animate.set_stroke(color=C_MINT, width=3.4), run_time=0.60)
        self.remove(bad_arc, bad_1hop_lbl)
        self.play(MoveAlongPath(p_up, e_hop2_a), MoveAlongPath(p_dn, e_hop2_b), e_hop2_a.animate.set_stroke(color=C_GOLD, width=3.4), e_hop2_b.animate.set_stroke(color=C_GOLD, width=3.4), run_time=0.50)
        self.play(MoveAlongPath(p_up, e_hop3_a), MoveAlongPath(p_dn, e_hop3_b), e_hop3_a.animate.set_stroke(color=C_GOLD, width=3.4), e_hop3_b.animate.set_stroke(color=C_GOLD, width=3.4), Circumscribe(n_ep_prod[0], color=C_MINT, stroke_width=2.2, buff=0.03), FadeIn(hop_badge, shift=UP * 0.08), run_time=0.65)
        self.remove(p_up, p_dn)
        self.wait(1.90)

        # -------------------------------------------------------------------
        # Beat 8B: Visual Phase Map (4x2 UW Matrix) + Care Journey 5-Stage Bar Chart + Constraint Graph!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "고객군별 간편심사 관문 격자, 치료 여정 5단계 보유 담보 막대, 결합 제약 네트워크를 한눈에 분석합니다",
            rt=0.38,
        )

        pm_title = txt("고객군별 간편심사 관문 분석 (연령 × 병력)", size=13.5, color=C_WHITE, bold=True, z=7).move_to([-3.05, 2.22, 0])
        hist_labels = ["최근 입원 이력", "수술만 (입원 없음)", "2~5년 경과 이력", "고지 해당 없음"]
        pm_cells = VGroup()
        gold_corridor_cell = None
        for r_i, h_lbl in enumerate(hist_labels):
            ry = 1.25 - r_i * 0.82
            pm_cells.add(txt(h_lbl, size=11.2, color=C_GOLD if r_i == 1 else C_INK_1, bold=(r_i == 1), z=7).move_to([-5.20, ry, 0]))
            for c_i, cw_p in enumerate([1.28, 2.68]):
                cx = -3.65 if c_i == 0 else -1.55
                is_gold_open = r_i == 1 and c_i == 1
                is_both_open = r_i >= 2 and c_i == 1
                cell_r = RoundedRectangle(corner_radius=0.05, width=cw_p, height=0.68, fill_color="#383016" if is_gold_open else ("#182832" if is_both_open else C_PANEL_HI), fill_opacity=0.95, stroke_color=C_GOLD if is_gold_open else (C_CYAN if is_both_open else C_SLATE), stroke_width=2.2 if is_gold_open else 1.2).move_to([cx, ry, 0]).set_z_index(4)
                if is_gold_open:
                    ct = fit(txt("▲ 우체국 적격 (입원만)", size=10.6, color=C_GOLD, bold=True, z=7), max_w=2.00)
                    ct.move_to(cell_r.get_left() + RIGHT * (0.12 + ct.width / 2))
                    gold_corridor_cell = cell_r
                elif is_both_open:
                    ct = txt("간편심사 청약 가능", size=11.0, color=C_CYAN, z=7).move_to(cell_r)
                elif c_i == 0:
                    ct = txt("일반심사 대상", size=10.6, color=C_INK_2, z=7).move_to(cell_r)
                else:
                    ct = txt("간편고지 제한 ×", size=10.6, color=C_CORAL, z=7).move_to(cell_r)
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

        cj_title = txt("치료 여정 5단계별 우체국 보유 담보 수", size=13.5, color=C_WHITE, bold=True, z=7).move_to([3.25, 2.22, 0])
        cj_stages = [("진단", 7, C_CYAN), ("수술", 6, C_CYAN), ("치료", 4, C_MINT), ("입원·간병", 8, C_GOLD), ("통원", 0, C_CORAL)]
        cj_bars, cj_nodes = VGroup(), VGroup()
        cj_base_y = 0.44
        for s_i, (s_nm, s_cnt, s_col) in enumerate(cj_stages):
            sx = 1.05 + s_i * 1.10
            slot_bg = RoundedRectangle(corner_radius=0.05, width=0.84, height=1.36, fill_color=C_PANEL_HI, fill_opacity=0.92, stroke_color=C_CORAL if s_cnt == 0 else C_SLATE, stroke_width=1.8 if s_cnt == 0 else 1.1).move_to([sx, cj_base_y + 0.68, 0]).set_z_index(3)
            if s_cnt > 0:
                bh = (s_cnt / 8.0) * 0.80
                bar = RoundedRectangle(corner_radius=0.04, width=0.56, height=bh, fill_color=s_col, fill_opacity=0.86, stroke_color=WHITE, stroke_width=1.0).move_to([sx, cj_base_y + 0.10 + bh / 2, 0]).set_z_index(5)
                cj_bars.add(VGroup(slot_bg, bar, txt(f"{s_cnt}종", size=11.2, color=WHITE, bold=True, z=7).move_to([sx, cj_base_y + 0.10 + bh + 0.18, 0])))
            else:
                cj_bars.add(VGroup(slot_bg, txt("0종", size=13.2, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + UP * 0.12), txt("공백 구간", size=9.4, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + DOWN * 0.28)))
            cj_nodes.add(txt(s_nm, size=11.0, color=C_CORAL if s_cnt == 0 else C_INK_1, bold=(s_cnt == 0), z=7).move_to([sx, cj_base_y - 0.20, 0]))

        cj_links = VGroup(*[Line([1.05 + i * 1.10 + 0.44, cj_base_y + 0.68, 0], [1.05 + (i + 1) * 1.10 - 0.44, cj_base_y + 0.68, 0], color=C_CORAL if i == 3 else C_GOLD, stroke_width=2.2).set_z_index(6) for i in range(4)])
        care_journey_grp = VGroup(cj_title, cj_bars, cj_nodes, cj_links)

        rc_box = RoundedRectangle(corner_radius=0.07, width=5.35, height=1.85, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_SLATE, stroke_width=1.4).move_to([3.25, -1.18, 0]).set_z_index(3)
        nd_main = pill("● 주계약 4,000만", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=10.6, px=0.10, py=0.05, z=7).move_to([1.50, -1.10, 0])
        nd_rider = pill("● 표적항암 2,000만", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.6, px=0.10, py=0.05, z=7).move_to([3.28, -1.10, 0])
        nd_excl = pill("● 배타선택 차단", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.6, px=0.10, py=0.05, z=7).move_to([5.02, -1.10, 0])
        constraint_grp = VGroup(
            rc_box, txt("특약 결합 제약 및 실수령액 산출", size=12.2, color=C_GOLD, bold=True, z=7).move_to([3.25, -0.52, 0]),
            nd_main, nd_rider, nd_excl,
            arrow_2d(nd_main.get_right(), nd_rider.get_left(), color=C_MINT, sw=1.9, tip=0.09, z=7),
            DashedLine(nd_rider.get_right(), nd_excl.get_left(), dash_length=0.06, color=C_CORAL, stroke_width=1.9).set_z_index(6),
            txt("주계약 연동 한도 반영 ✓ · 중복 불가 조합 자동 차단 ×", size=10.4, color=C_INK_1, z=7).move_to([3.25, -1.72, 0]),
        )
        beat8b_all = VGroup(phase_map_grp, care_journey_grp, constraint_grp)

        self.play(
            FadeOut(bg_cosmos), FadeOut(fg_subgraph), FadeOut(hop_badge),
            FadeIn(pm_title), FadeIn(pm_age_hdr),
            LaggedStart(*[FadeIn(c, shift=UP * 0.05) for c in pm_cells], lag_ratio=0.025),
            FadeIn(care_journey_grp, shift=LEFT * 0.12),
            FadeIn(constraint_grp, shift=UP * 0.10),
            run_time=1.10,
        )
        self.remove(bg_cosmos, fg_subgraph, hop_badge)
        assert gold_corridor_cell is not None
        cj_pulse = glow_dot([1.05, cj_base_y + 0.68, 0], color=C_GOLD, r=0.065, z=13)
        self.add(cj_pulse)
        self.play(
            FadeIn(target_cursor, scale=1.5),
            Circumscribe(gold_corridor_cell, color=C_GOLD, stroke_width=2.2, buff=0.03),
            MoveAlongPath(cj_pulse, Line([1.05, cj_base_y + 0.68, 0], [1.05 + 4 * 1.10, cj_base_y + 0.68, 0])),
            Circumscribe(cj_bars[4][0], color=C_CORAL, stroke_width=2.2, buff=0.03),
            run_time=0.95,
        )
        self.remove(cj_pulse)
        self.check_bounds(beat8b_all, "CH8B PHASE & CARE CHARTS")
        self.wait(2.10)

        # -------------------------------------------------------------------
        # Beat 8C: 4 Practical Strategies Compass -> Dock into Console & A4 Card
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "이 시각 분석이 4대 실무 전략으로 수렴해 본부 단독 화면과 창구·FC용 A4 1매 응대 카드로 출력됩니다",
            rt=0.38,
        )

        def make_strat_quad(cx: float, cy: float, col: str, title_s: str, action_s: str, icon_mob: VGroup) -> VGroup:
            box = RoundedRectangle(corner_radius=0.09, width=5.46, height=1.96, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=col, stroke_width=2.2).move_to([cx, cy, 0]).set_z_index(4)
            div = Line([cx - 1.18, cy - 0.72, 0], [cx - 1.18, cy + 0.72, 0], color=col, stroke_width=1.2, stroke_opacity=0.55).set_z_index(5)
            icon_mob.move_to([cx - 1.95, cy, 0]).set_z_index(7)
            t_blk = fit(VGroup(txt(title_s, size=13.2, color=col, bold=True, z=7), txt(action_s, size=12.2, color=WHITE, bold=True, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.14), max_w=3.58).move_to([cx + 0.78, cy, 0])
            return VGroup(box, div, icon_mob, t_blk)

        ic1 = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.16, height=0.38, fill_color=C_CORAL_DIM, fill_opacity=0.9, stroke_color=C_CORAL, stroke_width=1.4).move_to([0, 0.30, 0]),
            txt("타사 입원·수술 ×", size=8.6, color=C_CORAL, bold=True, z=8).move_to([0, 0.30, 0]),
            RoundedRectangle(corner_radius=0.04, width=1.16, height=0.42, fill_color="#383016", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.8).move_to([0, -0.26, 0]),
            txt("우체국 입원만 ✓", size=9.0, color=C_GOLD, bold=True, z=8).move_to([0, -0.26, 0]),
        )
        q_s1 = make_strat_quad(-3.15, 1.32, C_GOLD, "전략 ① [청약 타깃 발굴]", "수술 이력만 있는 20~80세 고객군 중점 안내", ic1)

        ic2 = VGroup(
            Line([-0.38, 0, 0], [0.38, 0.36, 0], color=C_MINT, stroke_width=2.0),
            Line([-0.38, 0, 0], [0.38, 0.0, 0], color=C_MINT, stroke_width=2.0),
            Line([-0.38, 0, 0], [0.38, -0.36, 0], color=C_MINT, stroke_width=2.0),
            Dot([-0.38, 0, 0], radius=0.11, color=C_MINT),
            Square(side_length=0.16, fill_color=C_GOLD, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to([0.38, 0.36, 0]),
            Square(side_length=0.16, fill_color=C_GOLD, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to([0.38, 0.0, 0]),
            Square(side_length=0.16, fill_color=C_GOLD, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to([0.38, -0.36, 0]),
        )
        q_s2 = make_strat_quad(3.15, 1.32, C_MINT, "전략 ② [앞세울 강점 · 단독 6종]", "뇌혈관·심장 입원일당 및 혈전용해 우선 제안", ic2)

        ic3_step = VMobject(color=C_CYAN, stroke_width=2.8)
        ic3_step.set_points_as_corners([[-0.52, -0.32, 0], [-0.05, -0.32, 0], [-0.05, 0.26, 0], [0.52, 0.26, 0]])
        ic3 = VGroup(Line([-0.55, -0.42, 0], [0.55, -0.42, 0], color=C_SLATE, stroke_width=1.4), ic3_step, txt("1년 후 100%", size=8.8, color=C_GOLD, bold=True, z=8).move_to([0.22, 0.46, 0]))
        q_s3 = make_strat_quad(-3.15, -1.24, C_CYAN, "전략 ③ [조건 열위 방어]", "분리특약 합산 · 감액 경과 안내 (단정 보류 분리)", ic3)

        ic4 = VGroup(
            RoundedRectangle(corner_radius=0.04, width=0.46, height=0.64, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=1.4).move_to([-0.32, 0.04, 0]),
            txt("입원8", size=8.8, color=C_GOLD, bold=True, z=8).move_to([-0.32, 0.04, 0]),
            RoundedRectangle(corner_radius=0.04, width=0.48, height=0.64, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.8).move_to([0.34, 0.04, 0]),
            txt("통원0", size=8.8, color=C_CORAL, bold=True, z=8).move_to([0.34, 0.04, 0]),
        )
        q_s4 = make_strat_quad(3.15, -1.24, C_CORAL, "전략 ④ [상품 개정 검토]", "미운영 '통원일당' 신설 · 간편 15~19세 확대 건의", ic4)

        compass_hub = VGroup(
            Circle(radius=0.40, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.6),
            txt("4대", size=11.8, color=C_GOLD, bold=True, z=12).shift(UP * 0.10),
            txt("실무전략", size=10.5, color=WHITE, bold=True, z=12).shift(DOWN * 0.11),
        ).move_to([0.0, 0.04, 0]).set_z_index(11)
        four_strategies = VGroup(q_s1, q_s2, q_s3, q_s4, compass_hub)

        self.play(FadeOut(beat8b_all, scale=0.94), FadeIn(compass_hub, scale=0.6), LaggedStart(*[FadeIn(q, shift=UP * 0.10) for q in [q_s1, q_s2, q_s3, q_s4]], lag_ratio=0.10), run_time=1.05)
        self.remove(beat8b_all)
        self.wait(1.65)

        app_window = RoundedRectangle(corner_radius=0.10, width=8.05, height=4.75, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_INK_1, stroke_width=2.2).move_to([-2.05, -0.15, 0]).set_z_index(1)
        app_win_hdr = pill("본부 상품 · 영업지원 판단 화면 (단독 HTML · 2.97MB)", fg=WHITE, bg=C_PANEL_HI, border=C_SLATE, size=11.8).move_to([-2.05, 1.92, 0]).set_z_index(8)
        tpl_bar = fit(pill("단정·과장 표현 빌드 차단 ✓ · 전 문장 약관·사업방법서 쪽수 직결", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=11.0, px=0.14, py=0.06, z=8), max_w=7.60).move_to([-2.05, -1.32, 0])
        nlq_bar = fit(pill('자연어·조건 연동 : "50세 수술이력 뇌혈관 비교" → 화면 ②·③·④ 즉시 산출', fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=10.8, px=0.14, py=0.06, z=8), max_w=7.60).move_to([-2.05, -1.98, 0])

        a4_box = Rectangle(width=2.98, height=4.75, fill_color=C_IVORY, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.4).move_to([4.48, -0.15, 0]).set_z_index(5)
        a4_top_bar = Line(a4_box.get_corner(UL), a4_box.get_corner(UR), color=C_CORAL, stroke_width=5.0).set_z_index(7)
        a4_badge = pill("대외 배포 금지 · A4 1매", fg=WHITE, bg=C_CORAL, border=C_CORAL, size=11.0).move_to([4.48, 1.76, 0]).set_z_index(7)
        a4_title = txt("창구 · FC 응대 카드", size=16.0, color=C_DARK_INK, bold=True, z=7).move_to([4.48, 1.24, 0])
        mini_cards = VGroup()
        for m_lbl, m_col in [("① 수술이력 간편심사 고지 차이", C_GOLD_DEEP), ("② 당사 단독 담보 · 대응 특약", "#1E6B7B"), ("③ 감액 경과 조건 · 근거 쪽수", "#2D3748")]:
            mb = RoundedRectangle(corner_radius=0.05, width=2.58, height=0.74, fill_color="#E5E4DC", fill_opacity=1.0, stroke_color="#C4C2B6", stroke_width=1.1).set_z_index(6)
            m_bar = Rectangle(width=0.10, height=0.74, fill_color=m_col, fill_opacity=1.0, stroke_width=0).move_to(mb.get_left() + RIGHT * 0.05).set_z_index(7)
            mini_cards.add(VGroup(mb, m_bar, fit(txt(m_lbl, size=11.2, color=C_DARK_INK, bold=True, z=7), max_w=2.24).move_to(mb.get_center() + RIGHT * 0.05)))
        mini_cards.arrange(DOWN, buff=0.14).move_to([4.48, -0.22, 0])
        a4_foot = Rectangle(width=2.98, height=0.48, fill_color=C_DARK_INK, fill_opacity=1.0, stroke_width=0).move_to(a4_box.get_bottom() + UP * 0.24).set_z_index(6)
        proj_beam = arrow_2d([2.04, -0.15, 0], [2.92, -0.15, 0], color=C_GOLD, sw=3.2, tip=0.18, z=8)
        a4_full = VGroup(a4_box, a4_top_bar, a4_badge, a4_title, mini_cards, a4_foot, fit(txt("본부 정밀 판단 → 현장 A4 1매 전달", size=11.4, color=C_GOLD, bold=True, z=7), max_w=2.72).move_to(a4_foot))

        self.play(
            four_strategies.animate.scale(0.43).move_to([-2.05, 0.52, 0]),
            FadeIn(app_window), FadeIn(app_win_hdr), FadeIn(tpl_bar, shift=UP * 0.08), FadeIn(nlq_bar, shift=UP * 0.08),
            GrowArrow(proj_beam), FadeIn(a4_full, shift=LEFT * 0.16),
            run_time=1.15,
        )
        ch8_stage = VGroup(app_window, app_win_hdr, four_strategies, tpl_bar, nlq_bar, proj_beam, a4_full)
        self.check_bounds(ch8_stage, "CH8C CONSOLE & CARD")
        self.wait(2.20)

        # ===================================================================
        # 9장 [~26s]: 최종 업무 혁신 인포그래픽 — 신설 · 해결 · 개선 시각 대변환!
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch8_stage,
            hl,
            hr,
            hb,
            9,
            "최종 업무 혁신 결과 — 새로 만들고, 안 되던 것을 풀고, 더 좋게 개선한 변화",
            "기존에는 없거나, 불가능하거나, 오류가 생기기 쉽던 실무가 수치와 시각 지표로 어떻게 달라졌는지 확인합니다",
        )
        print(f"[TIMING] Ch8 end: {self.renderer.time:.2f}s")

        col_hdr_before = pill("도입 전 업무 한계 (Before)", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.0, z=8).move_to([-4.32, 2.60, 0])
        col_hdr_after = pill("도입 후 업무 혁신 인포그래픽 (After)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.2, z=8).move_to([2.16, 2.60, 0])

        def make_ba_lane(ly: float, b_title: str, b_vis: VGroup, tag_s: str, a_col: str, a_title: str, a_widgets: VGroup) -> tuple[VGroup, VGroup, VGroup]:
            bc = RoundedRectangle(corner_radius=0.08, width=3.62, height=1.34, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.7).move_to([-4.32, ly, 0]).set_z_index(4)
            bt = fit(txt(b_title, size=10.2, color=C_CORAL, bold=True, z=7), max_w=3.36).move_to([-4.32, ly + 0.42, 0])
            b_vis.move_to([-4.32, ly - 0.18, 0]).set_z_index(7)

            arr = arrow_2d([-2.42, ly, 0], [-1.56, ly, 0], color=a_col, sw=2.8, tip=0.14, z=7)
            albl = pill(tag_s, fg=C_DARK_INK, bg=a_col, border=WHITE, size=9.2, px=0.09, py=0.03, z=8).move_to([-1.99, ly + 0.36, 0])

            ac = RoundedRectangle(corner_radius=0.08, width=7.24, height=1.34, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=a_col, stroke_width=2.2).move_to([2.16, ly, 0]).set_z_index(5)
            at = fit(txt(a_title, size=10.8, color=a_col, bold=True, z=7), max_w=6.88).move_to([2.16, ly + 0.44, 0])
            a_widgets.move_to([2.16, ly - 0.16, 0]).set_z_index(8)
            return VGroup(bc, bt, b_vis), VGroup(arr, albl), VGroup(ac, at, a_widgets)

        # Lane 1: Newly Created — Radar Icon + 13,671 Log Counter + Console->A4 Icon!
        bv1 = VGroup(
            Circle(radius=0.18, fill_opacity=0.0, stroke_color=C_SLATE, stroke_width=1.4),
            txt("수동조회 ?", size=8.6, color=C_INK_2, bold=True),
            DashedVMobject(Rectangle(width=0.32, height=0.44, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=1.4), num_dashes=10),
            txt("현장카드 ×", size=8.6, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.12)

        ic_rad9 = VGroup(Circle(radius=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_CYAN, stroke_width=1.8), Line([0, 0, 0], [0.14, 0.14, 0], color=C_GOLD, stroke_width=2.0))
        ic_scr9 = RoundedRectangle(corner_radius=0.04, width=0.66, height=0.44, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.6)
        ic_a4_9 = VGroup(Rectangle(width=0.34, height=0.46, fill_color=C_IVORY, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.4), Line([-0.17, 0.23, 0], [0.17, 0.23, 0], color=C_CORAL, stroke_width=2.6))
        aw1 = VGroup(
            ic_rad9,
            txt("19개사 · 운영비 0원", size=9.2, color=C_CYAN, bold=True),
            pill("검증로그 13,671건", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.0, px=0.09, py=0.04),
            ic_scr9,
            arrow_2d([0, 0, 0], [0.28, 0, 0], color=C_GOLD, sw=1.8, tip=0.08),
            ic_a4_9,
            txt("A4 1매", size=9.2, color=C_WHITE, bold=True),
        ).arrange(RIGHT, buff=0.12)
        b_l1, t_l1, a_l1 = make_ba_lane(1.24, "× [없던 체계] 모니터링 · 현장 카드 부재", bv1, "신설 ✓", C_CYAN, "① 무서버 상시 수집·검증 정본 & 본부 화면 ↔ 창구 A4 카드 구축", aw1)

        # Lane 2: Solved — 3 Mini Donut Metric Rings (100% / 100% / 86%)!
        bv2 = VGroup(
            Rectangle(width=0.32, height=0.40, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.4),
            txt("308p 그림 ×", size=8.6, color=C_CORAL, bold=True),
            txt("·", size=12, color=C_SLATE),
            txt("특약명 ≠", size=8.8, color=C_AMBER, bold=True),
        ).arrange(RIGHT, buff=0.10)

        def mini_donut(ratio: float, col: str, top_s: str, bot_s: str) -> VGroup:
            r = 0.26
            c0 = Circle(radius=r, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=2.4)
            arc = Arc(radius=r, start_angle=PI / 2, angle=-2 * PI * ratio, color=col, stroke_width=3.4)
            arc.shift(c0.get_center() - arc.get_arc_center())
            pct = txt(top_s, size=8.2, color=col, bold=True).move_to(c0)
            lbl = txt(bot_s, size=9.0, color=C_INK_0, bold=True)
            return VGroup(VGroup(c0, arc, pct), lbl).arrange(RIGHT, buff=0.08)

        aw2 = VGroup(
            mini_donut(1.0, C_MINT, "100%", "308쪽 오차 0건"),
            mini_donut(1.0, C_GOLD, "100%", "오류 437건 차단"),
            mini_donut(0.86, C_CYAN, "86%", "미보유 29→25종 해명"),
        ).arrange(RIGHT, buff=0.22)
        b_l2, t_l2, a_l2 = make_ba_lane(-0.20, "× [안 되던 비교] 그림 문서 · 이질적 특약", bv2, "해결 ✓", C_GOLD, "② 원문·코드 분리 + 교차판독 + decision-1 + 76종 합산 탐색", aw2)

        # Lane 3: Improved — Dashed Separator Icon + Shield Icon + Verified Stamp!
        bv3 = VGroup(
            Dot([0, 0, 0], radius=0.07, color=C_AMBER),
            txt("대기=공백 착각", size=8.6, color=C_AMBER, bold=True),
            RegularPolygon(n=3, fill_color="#3D2B0D", fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.4).scale(0.16),
            txt("구두과장 !", size=8.6, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.10)

        ic_sep9 = VGroup(Line([0, -0.18, 0], [0, 0.18, 0], color=C_MINT, stroke_width=2.2), DashedLine([0.14, -0.18, 0], [0.14, 0.18, 0], dash_length=0.06, color=C_AMBER, stroke_width=2.0))
        ic_shd9 = VGroup(RegularPolygon(n=6, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.8).scale(0.20), txt("✓", size=9.5, color=C_MINT, bold=True))
        aw3 = VGroup(
            ic_sep9,
            txt("대기 672건·단정주의 분리", size=9.0, color=C_AMBER, bold=True),
            ic_shd9,
            txt("추정·금지어 자동 차단", size=9.0, color=C_MINT, bold=True),
            pill("약관 쪽수 · 4대 전략 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=9.0, px=0.09, py=0.04),
        ).arrange(RIGHT, buff=0.14)
        b_l3, t_l3, a_l3 = make_ba_lane(-1.64, "× [문제 있던 판단] 오판 · 억지비교 · 과장", bv3, "개선 ✓", C_MINT, "③ 정직한 분리 안전장치 + 공시 부재 추정 차단 + 근거 직결 4대 전략", aw3)

        before_cards = VGroup(b_l1, b_l2, b_l3)
        trans_arrows = VGroup(t_l1, t_l2, t_l3)
        after_cards = VGroup(a_l1, a_l2, a_l3)

        finale_ribbon = fit(
            pill("완성도 검증 완료 : 자동 시험 608개 통과 · 화면 오류·외부 요청 0건 · 2단계 보험료·질병코드 별표 확장 기반 완비 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.68, 0])

        self.play(FadeIn(col_hdr_before, shift=DOWN * 0.08), LaggedStart(*[FadeIn(bc, shift=RIGHT * 0.12) for bc in before_cards], lag_ratio=0.10), run_time=1.00)
        self.wait(0.45)

        pulses_9 = VGroup(
            glow_dot([-2.42, 1.24, 0], color=C_CYAN, r=0.06, z=12),
            glow_dot([-2.42, -0.20, 0], color=C_GOLD, r=0.06, z=12),
            glow_dot([-2.42, -1.64, 0], color=C_MINT, r=0.06, z=12),
        )
        self.add(pulses_9)
        self.play(
            FadeIn(col_hdr_after, shift=DOWN * 0.08),
            LaggedStart(*[FadeIn(ta, scale=0.9) for ta in trans_arrows], lag_ratio=0.10),
            MoveAlongPath(pulses_9[0], Line([-2.42, 1.24, 0], [-1.56, 1.24, 0])),
            MoveAlongPath(pulses_9[1], Line([-2.42, -0.20, 0], [-1.56, -0.20, 0])),
            MoveAlongPath(pulses_9[2], Line([-2.42, -1.64, 0], [-1.56, -1.64, 0])),
            LaggedStart(*[FadeIn(ac, shift=LEFT * 0.14) for ac in after_cards], lag_ratio=0.10),
            run_time=1.30,
        )
        self.remove(pulses_9, *pulses_9)
        self.play(
            FadeIn(finale_ribbon, shift=UP * 0.08),
            LaggedStart(*[Circumscribe(ac[0], color=C_GOLD, stroke_width=2.0, buff=0.03) for ac in after_cards], lag_ratio=0.12),
            run_time=1.05,
        )

        ch9_stage = VGroup(col_hdr_before, col_hdr_after, before_cards, trans_arrows, after_cards, finale_ribbon)
        self.check_bounds(ch9_stage, "CH9 VISUAL BEFORE AFTER")
        self.wait(3.80)
        print(f"[TIMING] Part 4 end: {self.renderer.time:.2f}s")
