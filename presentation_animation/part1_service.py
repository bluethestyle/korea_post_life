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
    cross_mark,
    fit,
    glow_dot,
    pill,
    txt,
)


class Part1ServiceScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        # ===================================================================
        # 1장 [~29s]: 3D 공시 문서 협곡 → 기준 충돌 심층 줌인 → 정련 깔때기·실시간 콘솔·A4 레이저 인쇄
        # ===================================================================
        hl, hr, hb = self.make_hud(
            1,
            "우리가 만들려는 서비스 — 상품·청약 비교 판단과 현장 응대 연결",
            "19개 보험사의 수백 쪽 공시 문서 숲을 손으로 뒤지고, 본부와 창구가 단절된 현실에서 출발합니다",
        )

        # Start in dramatic 3D perspective overlooking the 19-insurer Document Canyon!
        self.set_camera_orientation(phi=56 * DEGREES, theta=-54 * DEGREES, zoom=0.92, frame_center=[-0.6, 0.0, 0.2])

        monoliths = VGroup()
        tower_specs = [
            (-5.25, 1.05, 1.85, C_CYAN),
            (-4.45, 1.10, 2.25, C_AMBER),
            (-3.68, 0.95, 1.40, C_SLATE),
            (-5.20, 0.08, 1.55, C_VIOLET),
            (-4.40, 0.05, 1.95, C_CYAN),
            (-3.65, 0.02, 1.25, C_SLATE),
            (-5.15, -0.92, 1.35, C_SLATE),
            (-4.35, -0.95, 1.70, C_GOLD),
            (-3.60, -0.90, 1.15, C_VIOLET),
        ]
        for tx, ty, th, tcol in tower_specs:
            pr = Prism(
                dimensions=[0.56, 0.56, th],
                fill_color=tcol,
                fill_opacity=0.38 if tcol != C_SLATE else 0.26,
                stroke_color=tcol,
                stroke_width=1.3,
            ).move_to([tx, ty, th / 2])
            monoliths.add(pr)

        doc_tag_top = pill("19개 기관 · 최대 567쪽", fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=10.2, px=0.10, py=0.04, z=9).move_to([-4.45, 1.86, 0])
        doc_tag_img = pill("308쪽 조각 그림 포함", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=9.8, px=0.10, py=0.04, z=9).move_to([-4.45, -1.78, 0])

        tangle_3d = VGroup(
            CubicBezier([-3.45, 0.95, 1.3], [-2.55, 1.25, 1.8], [-2.10, -0.45, 0.6], [-2.20, 0.55, 0.0], color=C_CORAL, stroke_width=2.2),
            CubicBezier([-3.45, 0.05, 1.6], [-2.50, -0.95, 1.1], [-2.05, 0.95, 0.5], [-2.20, 0.10, 0.0], color=C_AMBER, stroke_width=2.2),
            CubicBezier([-3.45, -0.85, 1.1], [-2.50, 0.45, 1.4], [-2.10, -0.85, 0.4], [-2.20, -0.40, 0.0], color=C_VIOLET, stroke_width=2.0),
        )

        chamber = RoundedRectangle(
            corner_radius=0.10, width=3.56, height=3.65, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_CORAL, stroke_width=2.0
        ).move_to([-0.42, 0.12, 0]).set_z_index(3)
        ch_hdr = pill("회사마다 다른 기준 충돌", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.8, z=7).move_to([-0.42, 1.62, 0])

        mis_rows = VGroup()
        mis_lefts, mis_rights = [], []
        for my, l_s, l_c, r_s, r_c, sub_s in [
            (0.78, "입원만 고지", C_GOLD, "입원·수술 고지", C_CYAN, "심사 질문 상이"),
            (-0.12, "통합수술 특약", C_VIOLET, "뇌 + 심장 분리", C_MINT, "특약 단위 상이"),
            (-1.02, "정액 2,000만", C_GOLD, "가입금액 50%", C_AMBER, "지급 표기 상이"),
        ]:
            lp = pill(l_s, fg=l_c, bg=C_PANEL_HI, border=l_c, size=9.8, px=0.09, py=0.04, z=7).move_to([-1.36, my + 0.08, 0])
            rp = pill(r_s, fg=r_c, bg=C_PANEL_HI, border=r_c, size=9.8, px=0.09, py=0.04, z=7).move_to([0.52, my + 0.08, 0])
            neq = txt("≠", size=16, color=C_CORAL, bold=True, z=8).move_to([-0.42, my + 0.08, 0])
            st = txt(sub_s, size=9.2, color=C_INK_2, z=7).move_to([-0.42, my - 0.28, 0])
            mis_lefts.append(lp)
            mis_rights.append(rp)
            mis_rows.add(VGroup(lp, neq, rp, st))

        brk_l = Line([1.42, 0.12, 0], [2.12, 0.12, 0], color=C_CORAL, stroke_width=3.2).set_z_index(6)
        brk_r = Line([2.68, 0.12, 0], [3.38, 0.12, 0], color=C_SLATE, stroke_width=3.2).set_z_index(6)
        chasm_x = cross_mark([2.40, 0.12, 0], size=0.18, color=C_CORAL, sw=3.6, z=10)
        chasm_lbl = pill("현장 전달 단절", fg=C_CORAL, bg=C_PANEL_HI, border=C_CORAL, size=9.8, px=0.09, py=0.03, z=9).move_to([2.40, 0.62, 0])

        field_ring = RoundedRectangle(corner_radius=0.10, width=2.48, height=3.65, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_SLATE, stroke_width=1.8).move_to([4.68, 0.12, 0]).set_z_index(3)
        field_hdr = pill("창구 · 설계사(FC)", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.8, z=7).move_to([4.68, 1.62, 0])
        p_head = Circle(radius=0.20, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=C_INK_1, stroke_width=2.0).move_to([4.15, 0.68, 0]).set_z_index(6)
        p_body = Arc(radius=0.32, start_angle=0, angle=PI, color=C_INK_1, stroke_width=2.2).move_to([4.15, 0.25, 0]).set_z_index(6)
        q_bub = RoundedRectangle(corner_radius=0.08, width=1.12, height=0.58, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.8).move_to([5.08, 0.68, 0]).set_z_index(7)
        q_txt = txt("가입 가능?", size=10.2, color=C_CORAL, bold=True, z=8).move_to(q_bub)
        warn_tri = RegularPolygon(n=3, fill_color="#3D2B0D", fill_opacity=0.95, stroke_color=C_AMBER, stroke_width=2.0).scale(0.32).move_to([4.68, -0.45, 0]).set_z_index(7)
        warn_bang = txt("!", size=15, color=C_AMBER, bold=True, z=8).move_to(warn_tri.get_center() + DOWN * 0.04)
        warn_cap = fit(txt("약관 쪽수 근거 없는 구두 안내 위험", size=9.8, color=C_AMBER, bold=True, z=7), max_w=2.22).move_to([4.68, -1.12, 0])
        field_vis = VGroup(field_ring, field_hdr, p_head, p_body, q_bub, q_txt, warn_tri, warn_bang, warn_cap)

        foot_1a = fit(
            pill("출발점 : 수백 쪽 약관 수작업 대조 병목과 본부 분석 ↔ 창구 상담 사이의 단절 해소 필요", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=11.0, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.55, 0])

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                LaggedStart(*[FadeIn(m, shift=OUT * 0.4) for m in monoliths], lag_ratio=0.06),
                Create(tangle_3d, lag_ratio=0.12),
                FadeIn(VGroup(chamber, ch_hdr)),
                FadeIn(VGroup(brk_l, brk_r, chasm_x, field_vis)),
            ],
            rt=1.20,
        )

        # Camera Dive into Microscopic Clause Mismatches + Physical Repulsion Bounce!
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.62,
            center=[-0.42, 0.12, 0],
            anims=[
                LaggedStart(*[FadeIn(mr, scale=0.88) for mr in mis_rows], lag_ratio=0.10),
                FadeIn(doc_tag_top),
                FadeIn(doc_tag_img),
            ],
            rt=1.20,
        )
        # Physical collision & recoil of mismatched standards!
        self.play(
            *[lp.animate.shift(RIGHT * 0.14) for lp in mis_lefts],
            *[rp.animate.shift(LEFT * 0.14) for rp in mis_rights],
            rate_func=there_and_back,
            run_time=0.55,
        )

        # Whip-Pan Right across Broken Bridge as a signal dies at the chasm!
        dead_sig = glow_dot([1.42, 0.12, 0], color=C_GOLD, r=0.065, z=12)
        self.add(dead_sig)
        self.cam_move(
            zoom=1.50,
            center=[3.55, 0.12, 0],
            anims=[
                MoveAlongPath(dead_sig, Line([1.42, 0.12, 0], [2.36, 0.12, 0])),
                FadeIn(chasm_lbl, shift=UP * 0.06),
                Flash([2.40, 0.12, 0], color=C_CORAL, line_length=0.22, num_lines=8),
                Wiggle(VGroup(warn_tri, warn_bang), scale_value=1.18, rotation_angle=0.08 * TAU),
            ],
            rt=1.05,
        )
        self.play(FadeOut(dead_sig, scale=0.2), Circumscribe(q_bub, color=C_CORAL, stroke_width=2.2, buff=0.04), run_time=0.45)
        self.remove(dead_sig)

        self.reset_cam_2d(anims=[FadeIn(foot_1a, shift=UP * 0.08)], rt=0.85)
        beat1a_all = VGroup(
            monoliths, doc_tag_top, doc_tag_img, tangle_3d,
            chamber, ch_hdr, mis_rows,
            brk_l, brk_r, chasm_x, chasm_lbl, field_vis, foot_1a,
        )
        self.check_bounds(VGroup(doc_tag_top, chamber, field_vis, foot_1a), "CH1A PAIN MACRO")
        self.wait(0.95)

        # -------------------------------------------------------------------
        # Beat 1B: Geometric Refinery Funnel -> Live Interactive Console -> Laser-Printed A4 Card!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "공개 공시·동향 정본을 바탕으로 본부는 단독 화면에서 즉시 판단하고, 창구·FC에는 A4 1매 응대 카드로 연결합니다",
            rt=0.38,
        )

        srv_top_pill = fit(
            pill("목표 서비스 : 『우체국보험 상품·청약 판단 지원 앱』 — 서버·DB 운영비 0원 · 공개 근거 100% 직결", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.4, z=10),
            max_w=11.85,
        ).move_to([0.0, 2.60, 0])

        # Left: Visual Refinery Funnel + 13-Tab Illuminated Golden Matrix (instead of 3 plain boxes!)
        raw_docs = VGroup(
            *[
                RoundedRectangle(corner_radius=0.03, width=0.34, height=0.44, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_CYAN if k % 2 == 0 else C_VIOLET, stroke_width=1.5).move_to(
                    [-5.65 + k * 0.38, 1.56 + (k % 2) * 0.12, 0]
                )
                for k in range(5)
            ]
        ).set_z_index(6)
        raw_lbl = txt("19개사 공시 · 주간 동향", size=10.2, color=C_CYAN, bold=True, z=7).move_to([-4.90, 2.04, 0])

        funnel_poly = Polygon(
            [-5.92, 1.14, 0],
            [-3.88, 1.14, 0],
            [-4.52, 0.22, 0],
            [-5.28, 0.22, 0],
            fill_color="#132634",
            fill_opacity=0.92,
            stroke_color=C_CYAN,
            stroke_width=2.0,
        ).set_z_index(5)
        funnel_txt = txt("검증 · 표준 정련", size=9.8, color=WHITE, bold=True, z=7).move_to([-4.90, 0.72, 0])

        ledger_frame = RoundedRectangle(corner_radius=0.08, width=2.28, height=1.82, fill_color="#13251E", fill_opacity=0.96, stroke_color=C_MINT, stroke_width=2.0).move_to([-4.90, -0.96, 0]).set_z_index(4)
        ledger_hdr = txt("구글 시트 정본 13탭", size=10.4, color=C_MINT, bold=True, z=7).move_to([-4.90, -0.26, 0])
        ledger_cells = VGroup()
        for k in range(13):
            rr, cc = divmod(k, 5)
            cell_c = C_GOLD if k in (0, 3, 6, 11) else (C_MINT if k % 2 == 0 else C_CYAN)
            ledger_cells.add(
                RoundedRectangle(corner_radius=0.03, width=0.32, height=0.24, fill_color=cell_c, fill_opacity=0.88, stroke_width=0)
                .move_to([-5.66 + cc * 0.38, -0.68 - rr * 0.34, 0])
                .set_z_index(6)
            )
        ledger_sub = txt("검증 통과분만 적재 ✓", size=9.0, color=C_INK_1, z=7).move_to([-4.90, -1.66, 0])
        left_refinery = VGroup(raw_docs, raw_lbl, funnel_poly, funnel_txt, ledger_frame, ledger_hdr, ledger_cells, ledger_sub)

        # Center: Interactive HQ Console with Live Animated Gate, Heatmap Wave, & Growing Step Bars
        dash_frame = RoundedRectangle(corner_radius=0.10, width=5.24, height=3.86, fill_color=C_PANEL, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.4).move_to([-0.24, 0.04, 0]).set_z_index(4)
        dash_title = fit(pill("① 본부 판단 화면 (무설치 단독 HTML · 외부 통신 0건)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.8, z=7), max_w=4.88).move_to([-0.24, 1.60, 0])
        c_age = pill("50세", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.8, px=0.10, py=0.03, z=7)
        c_sex = pill("남성", fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=9.8, px=0.10, py=0.03, z=7)
        c_uw = pill("간편심사 2년형 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.8, px=0.11, py=0.03, z=7)
        cond_strip = VGroup(c_age, c_sex, c_uw).arrange(RIGHT, buff=0.12).move_to([-0.24, 1.06, 0])

        w1_box = RoundedRectangle(corner_radius=0.06, width=1.54, height=1.88, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=C_GOLD_DEEP, stroke_width=1.4).move_to([-1.92, -0.18, 0]).set_z_index(5)
        w1_h = txt("청약 관문", size=10.0, color=C_GOLD, bold=True, z=7).move_to([-1.92, 0.52, 0])
        w1_g_open = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.24, height=0.40, fill_color="#383016", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.8),
            txt("우체국 입원만 ▲", size=8.6, color=C_GOLD, bold=True, z=8),
        ).move_to([-1.92, 0.02, 0]).set_z_index(7)
        w1_g_shut = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.24, height=0.40, fill_color=C_CORAL_DIM, fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=1.4),
            txt("민영 입원·수술 ×", size=8.4, color=C_CORAL, bold=True, z=8),
        ).move_to([-1.92, -0.54, 0]).set_z_index(7)

        w2_box = RoundedRectangle(corner_radius=0.06, width=1.64, height=1.88, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=1.4).move_to([-0.24, -0.18, 0]).set_z_index(5)
        w2_h = txt("76종 담보 우열", size=10.0, color=C_CYAN, bold=True, z=7).move_to([-0.24, 0.52, 0])
        hm_cells = VGroup(
            *[
                RoundedRectangle(corner_radius=0.03, width=0.36, height=0.26, fill_color=hcol, fill_opacity=0.88, stroke_width=0)
                .move_to([-0.66 + (k % 3) * 0.42, 0.12 - (k // 3) * 0.32, 0])
                .set_z_index(7)
                for k, hcol in enumerate([C_GOLD, C_CYAN, C_GOLD, C_MINT, C_GOLD, C_CORAL, C_MINT, C_CYAN, C_GOLD])
            ]
        )
        w2_pg = pill("약관 p.142 직결", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=8.4, px=0.08, py=0.03, z=8).move_to([-0.24, -0.84, 0])

        w3_box = RoundedRectangle(corner_radius=0.06, width=1.54, height=1.88, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=C_MINT, stroke_width=1.4).move_to([1.44, -0.18, 0]).set_z_index(5)
        w3_h = txt("실수령액 산출", size=10.0, color=C_MINT, bold=True, z=7).move_to([1.44, 0.52, 0])
        w3_ax = Line([0.84, -0.68, 0], [2.04, -0.68, 0], color=C_SLATE, stroke_width=1.5).set_z_index(6)
        w3_b1 = Rectangle(width=0.32, height=0.42, fill_color=C_CYAN, fill_opacity=0.85, stroke_width=0).move_to([1.18, -0.47, 0]).set_z_index(7)
        w3_b2 = Rectangle(width=0.36, height=0.88, fill_color=C_GOLD, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.0).move_to([1.68, -0.24, 0]).set_z_index(7)
        w3_cap = txt("감액 → 100%", size=8.6, color=C_MINT, bold=True, z=7).move_to([1.44, -0.90, 0])
        dash_foot = txt("변수 밖 숫자 · 금지 단정어 빌드 자동 차단 ✓", size=9.8, color=C_MINT, bold=True, z=7).move_to([-0.24, -1.52, 0])
        hq_dash_grp = VGroup(dash_frame, dash_title, cond_strip, w1_box, w1_h, w1_g_open, w1_g_shut, w2_box, w2_h, hm_cells, w2_pg, w3_box, w3_h, w3_ax, w3_b1, w3_b2, w3_cap, dash_foot)

        feed_to_dash = arrow_2d([-3.68, -0.55, 0], [-2.90, -0.15, 0], color=C_MINT, sw=2.6, tip=0.13, z=7)
        bridge_to_a4 = arrow_2d([2.42, 0.04, 0], [3.34, 0.04, 0], color=C_GOLD, sw=3.2, tip=0.16, z=8)
        bridge_lbl = pill("A4 1장 출력", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.4, px=0.08, py=0.03, z=9).move_to([2.88, 0.42, 0])

        a4_srv = Rectangle(width=2.58, height=3.86, fill_color=C_IVORY, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.3).move_to([4.72, 0.04, 0]).set_z_index(5)
        a4_red_top = Line(a4_srv.get_corner(UL), a4_srv.get_corner(UR), color=C_CORAL, stroke_width=4.8).set_z_index(7)
        a4_tag = pill("대외 배포 금지 · A4 1매", fg=WHITE, bg=C_CORAL, border=C_CORAL, size=9.6, px=0.09, py=0.03, z=8).move_to([4.72, 1.56, 0])
        a4_hdr = txt("② 창구·FC 응대 카드", size=13.2, color=C_DARK_INK, bold=True, z=7).move_to([4.72, 1.08, 0])
        a4_bars = VGroup()
        for ay, acol, albl in [(0.48, C_GOLD_DEEP, "▲ 수술이력 청약 적격"), (-0.14, "#1E6B7B", "◆ 단독·분리특약 안내"), (-0.76, "#2D3748", "§ 감액조건 · 약관 쪽수")]:
            abg = RoundedRectangle(corner_radius=0.04, width=2.24, height=0.46, fill_color="#E5E4DC", fill_opacity=1.0, stroke_color="#C4C2B6", stroke_width=1.0).move_to([4.72, ay, 0]).set_z_index(6)
            abar = Rectangle(width=0.09, height=0.46, fill_color=acol, fill_opacity=1.0, stroke_width=0).move_to(abg.get_left() + RIGHT * 0.045).set_z_index(7)
            a4_bars.add(VGroup(abg, abar, fit(txt(albl, size=10.0, color=C_DARK_INK, bold=True, z=7), max_w=1.96).move_to(abg.get_center() + RIGHT * 0.04)))
        a4_bot = Rectangle(width=2.58, height=0.44, fill_color=C_DARK_INK, fill_opacity=1.0, stroke_width=0).move_to([4.72, -1.67, 0]).set_z_index(6)
        a4_bot_txt = fit(txt("상담 현장 즉시 활용 ✓", size=10.2, color=C_GOLD, bold=True, z=7), max_w=2.32).move_to(a4_bot)
        a4_srv_grp = VGroup(a4_srv, a4_red_top, a4_tag, a4_hdr, a4_bars, a4_bot, a4_bot_txt)

        scope_foot = fit(pill("원칙 : 비공개 자료(실제 인수·손해율·시책)는 다루지 않고, 공시 문서와 시장 동향 사실만으로 판단을 지원합니다", fg=C_INK_1, bg=C_PANEL, border=C_SLATE, size=10.8, z=8), max_w=11.85).move_to([0.0, -2.56, 0])

        # 1) Zoom onto Left Refinery Funnel as raw docs pour in & 13-tab ledger lights up!
        self.cam_move(
            zoom=1.45,
            center=[-4.55, 0.15, 0],
            anims=[
                FadeOut(beat1a_all, shift=UP * 0.10),
                FadeIn(raw_lbl),
                LaggedStart(*[FadeIn(rd, shift=DOWN * 0.18) for rd in raw_docs], lag_ratio=0.07),
                FadeIn(VGroup(funnel_poly, funnel_txt)),
                FadeIn(VGroup(ledger_frame, ledger_hdr, ledger_sub)),
                LaggedStart(*[FadeIn(lc, scale=0.3) for lc in ledger_cells], lag_ratio=0.04),
            ],
            rt=1.05,
        )
        self.remove(beat1a_all)

        # 2) Pan Right into the HQ Console as clicking [간편심사 2년형] animates all 3 live widgets!
        self.cam_move(
            zoom=1.46,
            center=[-0.24, 0.04, 0],
            anims=[
                GrowArrow(feed_to_dash),
                FadeIn(VGroup(dash_frame, dash_title, c_age, c_sex, dash_foot)),
                FadeIn(c_uw, scale=1.22),
                FadeIn(VGroup(w1_box, w1_h)),
                FadeIn(w1_g_open, shift=UP * 0.12),
                FadeIn(w1_g_shut, shift=DOWN * 0.10),
                FadeIn(VGroup(w2_box, w2_h, w2_pg)),
                LaggedStart(*[FadeIn(hc, scale=0.4) for hc in hm_cells], lag_ratio=0.04),
                FadeIn(VGroup(w3_box, w3_h, w3_ax, w3_cap)),
                GrowFromEdge(w3_b1, DOWN),
                GrowFromEdge(w3_b2, DOWN),
            ],
            rt=1.20,
        )

        # 3) Track Right onto the Ivory A4 Card as a Golden Laser Print-Head sweeps top-to-bottom!
        print_laser = Line([3.38, 1.88, 0], [6.06, 1.88, 0], color=C_GOLD, stroke_width=3.6).set_z_index(12)
        self.add(print_laser)
        self.cam_move(
            zoom=1.42,
            center=[3.95, 0.04, 0],
            anims=[
                GrowArrow(bridge_to_a4),
                FadeIn(bridge_lbl, scale=0.88),
                FadeIn(VGroup(a4_srv, a4_red_top, a4_hdr)),
                print_laser.animate.move_to([4.72, -1.85, 0]),
                FadeIn(a4_tag, scale=1.25),
                LaggedStart(*[FadeIn(ab, shift=DOWN * 0.08) for ab in a4_bars], lag_ratio=0.14),
                FadeIn(VGroup(a4_bot, a4_bot_txt)),
            ],
            rt=1.15,
        )
        self.remove(print_laser)

        # 4) Pull back to crisp full-system view
        self.reset_cam_2d(
            anims=[FadeIn(srv_top_pill, shift=DOWN * 0.08), FadeIn(scope_foot, shift=UP * 0.08)],
            rt=0.85,
        )

        ch1_stage = VGroup(srv_top_pill, left_refinery, feed_to_dash, hq_dash_grp, bridge_to_a4, bridge_lbl, a4_srv_grp, scope_foot)
        self.check_bounds(ch1_stage, "CH1B SERVICE INFOGRAPHIC")
        self.wait(1.40)

        # ===================================================================
        # 2장 [~28s]: 기계식 조건 다이얼 바늘 회전 · 충격파 점화 · 실시간 카운터 클로즈업 투어
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch1_stage,
            hl,
            hr,
            hb,
            2,
            "구현하려는 핵심 기능 — 조건 다이얼 하나로 맞물리는 6대 기능",
            "중앙 조건 다이얼을 돌리면 6방향 충격파와 함께 6개 화면의 차트·수치가 실시간으로 맞물려 반응합니다",
        )

        hub_c = np.array([0.0, 0.22, 0.0])
        hub_orbit_3d = Circle(radius=1.24, fill_opacity=0.0, stroke_color=C_GOLD_DEEP, stroke_width=1.8).rotate(PI / 5, axis=RIGHT).move_to(hub_c + OUT * 0.22)
        hub_outer_ring = DashedVMobject(Circle(radius=1.04, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.2).move_to(hub_c), num_dashes=28).set_z_index(7)
        hub_core = Circle(radius=0.86, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.8).move_to(hub_c).set_z_index(8)

        # Mechanical rotating dial needle on the outer bezel!
        dial_needle = Arrow(hub_c + UP * 0.62, hub_c + UP * 1.06, buff=0, color=C_GOLD, stroke_width=3.2, tip_length=0.14).set_z_index(12)
        hub_txt = fit(
            VGroup(
                txt("공통 조건 다이얼", size=10.4, color=C_GOLD, bold=True, z=9),
                pill("50세 · 남성", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.8, px=0.08, py=0.03, z=9),
                pill("간편 2년형", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.8, px=0.08, py=0.03, z=9),
            ).arrange(DOWN, buff=0.07),
            max_w=1.42,
        ).move_to(hub_c)
        central_hub = VGroup(hub_orbit_3d, hub_outer_ring, hub_core, dial_needle, hub_txt)

        def make_radial_module(cx: float, cy: float, col: str, badge_s: str, title_s: str, cap_s: str, widget: VGroup) -> VGroup:
            card = RoundedRectangle(corner_radius=0.09, width=3.48, height=1.52, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.0).move_to([cx, cy, 0]).set_z_index(4)
            dark_fg = col in (C_GOLD, C_MINT, C_CYAN, C_AMBER, "#93C5FD")
            bdg = pill(badge_s, fg=C_DARK_INK if dark_fg else WHITE, bg=col, border=WHITE, size=9.2, px=0.08, py=0.025, z=7)
            hdr = fit(VGroup(bdg, txt(title_s, size=11.4, color=col, bold=True, z=7)).arrange(RIGHT, buff=0.09), max_w=3.22).move_to([cx, cy + 0.50, 0])
            widget.move_to([cx, cy - 0.04, 0]).set_z_index(7)
            cap = fit(txt(cap_s, size=9.4, color=C_INK_1, z=7), max_w=3.22).move_to([cx, cy - 0.54, 0])
            return VGroup(card, hdr, widget, cap)

        wg1 = VGroup(
            Line([-1.15, 0, 0], [1.15, 0, 0], color=C_SLATE, stroke_width=2.0),
            pill("개정 개시", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.4, px=0.07, py=0.03).move_to([-0.72, 0.0, 0]),
            pill("19개사 동향", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.4, px=0.07, py=0.03).move_to([0.05, 0.0, 0]),
            pill("우열 변동 ▲", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.4, px=0.07, py=0.03).move_to([0.82, 0.0, 0]),
        )
        m_1 = make_radial_module(-4.35, 1.92, C_VIOLET, "화면 ①", "이번 주 달라진 점", "신규·종료 개정 · 주간 동향 · 우열 변동 포착", wg1)

        wg2 = VGroup(
            pill("우체국 : 입원만 ▲", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.8, px=0.09, py=0.04).move_to([-0.72, 0, 0]),
            txt("vs", size=9.5, color=C_INK_2, bold=True).move_to([0.08, 0, 0]),
            pill("민영 : 입원·수술 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.8, px=0.09, py=0.04).move_to([0.84, 0, 0]),
        )
        m_2 = make_radial_module(-4.35, 0.22, C_GOLD, "화면 ②", "가입 적격 · 간편심사 관문", "연령별 한도 · 회사별 고지 질문 통과 대조", wg2)

        wg3_step = VMobject(color=C_MINT, stroke_width=2.6)
        wg3_step.set_points_as_corners([[0.25, -0.18, 0], [0.58, -0.18, 0], [0.58, 0.18, 0], [1.08, 0.18, 0]])
        wg3 = VGroup(
            pill("주계약", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.4, px=0.07, py=0.03).move_to([-1.00, 0, 0]),
            arrow_2d([-0.66, 0, 0], [-0.36, 0, 0], color=C_MINT, sw=1.6, tip=0.07),
            pill("특약연동", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.4, px=0.07, py=0.03).move_to([0.00, 0, 0]),
            wg3_step,
        )
        m_3 = make_radial_module(-4.35, -1.48, C_MINT, "화면 ④", "특약 조합별 실수령액", "선행·연동·배타 제약 반영 실제·감액 지급액", wg3)

        wg4_cells = VGroup(
            *[RoundedRectangle(corner_radius=0.03, width=0.28, height=0.28, fill_color=c, fill_opacity=0.9, stroke_width=0).move_to([-1.05 + idx * 0.34, 0, 0]) for idx, c in enumerate([C_GOLD, C_CYAN, C_MINT, C_CORAL])]
        )
        wg4 = VGroup(
            wg4_cells,
            arrow_2d([0.18, 0, 0], [0.46, 0, 0], color=C_GOLD, sw=1.6, tip=0.07),
            pill("약관 p.쪽수 · 카드 인쇄", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.4, px=0.08, py=0.03).move_to([1.02, 0, 0]),
        )
        m_4 = make_radial_module(4.35, 1.92, C_CYAN, "화면 ③", "표준담보 76종 비교표", "지급·면책·감액 우열 판별 및 응대 카드 출력", wg4)

        wg5 = VGroup(
            pill("2504 (1천만·2년)", fg=C_INK_1, bg=C_BG_SUB, border=C_SLATE, size=8.4, px=0.07, py=0.03).move_to([-0.82, 0, 0]),
            arrow_2d([-0.14, 0, 0], [0.18, 0, 0], color=C_AMBER, sw=2.0, tip=0.08),
            pill("2606 (2천만·1년 ▲)", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.4, px=0.07, py=0.03).move_to([0.86, 0, 0]),
        )
        m_5 = make_radial_module(4.35, 0.22, C_AMBER, "화면 ⑤", "개정 전후 계보 시간선", "특약 계보 연결로 지급 상향·감액 단축 추적", wg5)

        wg6_bars = VGroup(
            Rectangle(width=0.20, height=0.38, fill_color=C_GOLD, fill_opacity=0.95, stroke_width=0).move_to([-1.02, 0.02, 0]),
            Rectangle(width=0.20, height=0.24, fill_color=C_CYAN, fill_opacity=0.90, stroke_width=0).move_to([-0.76, -0.05, 0]),
            Rectangle(width=0.20, height=0.12, fill_color=C_CORAL, fill_opacity=0.90, stroke_width=0).move_to([-0.50, -0.11, 0]),
        )
        wg6 = VGroup(
            wg6_bars,
            pill("판정 확률 · 로그 13,671건 공개", fg="#93C5FD", bg=C_BG_SUB, border="#93C5FD", size=8.6, px=0.09, py=0.03).move_to([0.48, 0, 0]),
        )
        m_6 = make_radial_module(4.35, -1.48, "#93C5FD", "화면 ⑥", "AI 작업·검증 내역 공개", "추출·코드 대조·재추출·검토 이력 전량 공개", wg6)

        modules_6 = VGroup(m_1, m_2, m_3, m_4, m_5, m_6)
        spoke_pairs = [
            (hub_c + np.array([-0.82, 0.56, 0]), np.array([-2.58, 1.82, 0]), C_VIOLET),
            (hub_c + np.array([-0.98, 0.0, 0]), np.array([-2.58, 0.22, 0]), C_GOLD),
            (hub_c + np.array([-0.82, -0.56, 0]), np.array([-2.58, -1.38, 0]), C_MINT),
            (hub_c + np.array([0.82, 0.56, 0]), np.array([2.58, 1.82, 0]), C_CYAN),
            (hub_c + np.array([0.98, 0.0, 0]), np.array([2.58, 0.22, 0]), C_AMBER),
            (hub_c + np.array([0.82, -0.56, 0]), np.array([2.58, -1.38, 0]), "#93C5FD"),
        ]
        spokes = VGroup(*[arrow_2d(s0, s1, color=scol, sw=2.0, tip=0.10, z=6) for s0, s1, scol in spoke_pairs])
        guard_ribbon = fit(
            pill("정직한 표시 안전장치 : 변수 밖 임의 숫자·금지어 자동 차단 · 공시 없는 값(특약 보험료 등) 억지 추정 표시 제외 ✓", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=10.8, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.62, 0])

        # 1) 3D Orbital Ignition + Rotating Mechanical Dial + Expanding Shockwave & 6 Traveling Pulses!
        shockwave = Circle(radius=0.85, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=3.6, stroke_opacity=0.95).move_to(hub_c).set_z_index(11)
        spoke_pulses = VGroup(*[glow_dot(s0, color=scol, r=0.065, z=14) for s0, _, scol in spoke_pairs])

        self.cam_move(
            phi=46 * DEGREES,
            theta=-64 * DEGREES,
            zoom=0.92,
            center=[0.0, 0.10, 0.0],
            anims=[
                FadeIn(central_hub, scale=0.82),
                LaggedStart(*[GrowArrow(sp) for sp in spokes], lag_ratio=0.04),
                LaggedStart(*[FadeIn(md, scale=0.92) for md in modules_6], lag_ratio=0.06),
            ],
            rt=1.15,
        )
        self.add(shockwave, spoke_pulses)
        self.cam_move(
            theta=-48 * DEGREES,
            anims=[
                Rotate(dial_needle, angle=-2 * PI / 3, about_point=hub_c),
                Rotate(hub_outer_ring, angle=PI / 3, about_point=hub_c),
                Rotate(hub_orbit_3d, angle=PI / 2, axis=OUT),
                shockwave.animate.scale(5.2).set_stroke(opacity=0.0),
                *[MoveAlongPath(spoke_pulses[k], Line(spoke_pairs[k][0], spoke_pairs[k][1])) for k in range(6)],
            ],
            rt=0.95,
        )
        self.remove(shockwave, spoke_pulses, *spoke_pulses)

        # 2) Kinetic 3-Stop Zoom-Pan Tour across Live Reacting Modules!
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.50,
            center=[-4.20, 0.95, 0],
            anims=[
                Indicate(m_1[2], color=C_VIOLET, scale_factor=1.08),
                Circumscribe(m_2[0], color=C_GOLD, stroke_width=2.4, buff=0.03),
                Indicate(m_2[2][0], color=C_GOLD, scale_factor=1.12),
            ],
            rt=1.05,
        )
        self.cam_move(
            zoom=1.50,
            center=[4.20, 0.95, 0],
            anims=[
                Circumscribe(m_4[0], color=C_CYAN, stroke_width=2.4, buff=0.03),
                Indicate(m_5[2][2], color=C_GOLD, scale_factor=1.14),
            ],
            rt=1.05,
        )
        self.cam_move(
            zoom=1.45,
            center=[4.20, -1.42, 0],
            anims=[
                Circumscribe(m_6[0], color="#93C5FD", stroke_width=2.2, buff=0.03),
                Indicate(m_6[2][1], color=WHITE, scale_factor=1.10),
            ],
            rt=0.85,
        )

        hb = self.update_subtitle(
            hb,
            "이제 수집·추출·검증·온톨로지 각 단계의 현실 난제를 어떻게 기구적 구조로 풀었는지 들어가 보겠습니다",
            rt=0.38,
        )
        self.reset_cam_2d(anims=[FadeIn(guard_ribbon, shift=UP * 0.08)], rt=0.85)

        ch2_stage = VGroup(central_hub, spokes, modules_6, guard_ribbon)
        self.check_bounds(ch2_stage, "CH2 RADIAL INFOGRAPHIC")
        self.wait(1.40)
        print(f"[TIMING] Part 1 end: {self.renderer.time:.2f}s")

        self.fade_out_part(ch2_stage, hl, hr, hb)
