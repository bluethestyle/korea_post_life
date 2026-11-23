from __future__ import annotations

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
    PostLifeBaseScene,
    arrow_2d,
    cross_mark,
    fact,
    fit,
    glow_dot,
    num,
    pill,
    txt,
)


class Part1ServiceScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        org_names = fact("org_names")
        epost_name = org_names["EPOST"]
        peer_site_names = ", ".join(org_names[o] for o in fact("site_orgs") if o != "EPOST")
        target_counts = fact("comparison_target_counts")
        target_total = sum(target_counts.values())
        hw_pages = fact("hanwha_summary_pages")
        img_pages = fact("image_doc", "pages")

        rev_old = fact("example_targeted_anticancer", "revisions", 0)
        rev_new = fact("example_targeted_anticancer", "revisions", -1)
        basis_mw = rev_new["basis_manwon"]
        pay_new_mw = rev_new["pay_manwon"]
        red_months = rev_new["reduce"][0]["months"]
        red_rate = rev_new["reduce"][0]["rate"]
        red_pct = round(red_rate * 100)
        doc_kind = rev_new["doc_kind"]
        doc_page = rev_new["doc_pages"][0]

        op_cost = fact("operating_cost_won")
        news_inst_cnt = fact("market_news_institution_count")
        sheet_tabs = fact("sheet_tab_count")
        browser_problems = fact("site_browser_check_problems")
        ref_cond = fact("reference_condition")
        ref_age = ref_cond["age"]
        ref_sex_ko = "남성" if ref_cond["sex"] == "M" else "여성"
        base_var_name = fact("default_base_variant", "name")
        cov_in_use = fact("standard_coverage_in_use")
        cmp_pairs = fact("compared_coverage_pairs")
        forb_cnt = len(fact("forbidden_words"))
        prem_rows = fact("premium_example_rows")
        card_order = fact("card_category_order")
        lead_str = fact("lead_strengths")
        scr_cnt = fact("site_screen_count")
        wk_news = fact("screen_market_news")
        rev_chg_total = fact("revision_changes", "전체")
        wlog_site = fact("work_log_count_site")
        wlog_res = fact("work_log_by_result")

        # ===================================================================
        # 1장: 우리가 만들려는 서비스
        # ===================================================================
        hl, hr, hb = self.make_hud(
            1,
            "우리가 만들려는 서비스: 공시 문서 비교 화면과 현장 응대 카드",
            f"정밀 비교 대상 {num(target_total)}곳의 공시 문서를 같은 기준으로 맞추고, 본부 판단을 창구 응대 카드까지 잇습니다",
        )

        self.set_camera_orientation(phi=54 * DEGREES, theta=-54 * DEGREES, zoom=0.92, frame_center=[-0.6, 0.0, 0.2])

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

        doc_tag_top = fit(
            pill(f"정밀 비교 대상 {num(target_total)}곳, 한화생명 요약서 {num(hw_pages)}쪽", fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=9.8, px=0.10, py=0.04, z=9),
            max_w=2.95,
        ).move_to([-4.45, 1.88, 0])
        doc_tag_img = fit(
            pill(f"글자가 그림으로 든 요약서 {num(img_pages)}쪽", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=9.8, px=0.10, py=0.04, z=9),
            max_w=2.95,
        ).move_to([-4.45, -1.80, 0])

        tangle_3d = VGroup(
            CubicBezier([-3.45, 0.95, 1.3], [-2.55, 1.25, 1.8], [-2.10, -0.45, 0.6], [-2.20, 0.55, 0.0], color=C_CORAL, stroke_width=2.2),
            CubicBezier([-3.45, 0.05, 1.6], [-2.50, -0.95, 1.1], [-2.05, 0.95, 0.5], [-2.20, 0.10, 0.0], color=C_AMBER, stroke_width=2.2),
            CubicBezier([-3.45, -0.85, 1.1], [-2.50, 0.45, 1.4], [-2.10, -0.85, 0.4], [-2.20, -0.40, 0.0], color=C_VIOLET, stroke_width=2.0),
        )

        chamber = RoundedRectangle(
            corner_radius=0.10, width=3.68, height=3.68, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_CORAL, stroke_width=2.0
        ).move_to([-0.42, 0.12, 0]).set_z_index(3)
        ch_hdr = fit(pill("왜 비교가 어렵나: 회사마다 기준과 표기가 다름", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.2, z=7), max_w=3.42).move_to([-0.42, 1.62, 0])

        mis_rows = VGroup()
        mis_lefts, mis_rights = [], []
        for my, l_s, l_c, r_s, r_c, sub_s in [
            (0.78, f"{epost_name}: 입원만 질문", C_GOLD, f"{peer_site_names}: 입원 또는 수술", C_CYAN, "간편심사 고지 질문 범위가 다름"),
            (-0.12, "상대: 뇌·심장질환 수술비", C_VIOLET, f"{epost_name}: 뇌혈관, 심장 분리", C_MINT, "특약을 묶거나 나눈 단위가 다름"),
            (-1.02, f"기준 {num(basis_mw)}만에 지급 {num(pay_new_mw)}만", C_GOLD, f"{org_names['SAMSUNGFIRE']}: 가입금액의 N%", C_AMBER, "지급액을 금액 또는 가입금액비율로 표기"),
        ]:
            lp = fit(pill(l_s, fg=l_c, bg=C_PANEL_HI, border=l_c, size=9.2, px=0.07, py=0.04, z=7), max_w=1.54).move_to([-1.34, my + 0.08, 0])
            rp = fit(pill(r_s, fg=r_c, bg=C_PANEL_HI, border=r_c, size=9.2, px=0.07, py=0.04, z=7), max_w=1.54).move_to([0.50, my + 0.08, 0])
            neq = txt("≠", size=16, color=C_CORAL, bold=True, z=8).move_to([-0.42, my + 0.08, 0])
            st = fit(txt(sub_s, size=9.0, color=C_INK_1, z=7), max_w=3.36).move_to([-0.42, my - 0.28, 0])
            mis_lefts.append(lp)
            mis_rights.append(rp)
            mis_rows.add(VGroup(lp, neq, rp, st))

        brk_l = Line([1.46, 0.12, 0], [2.12, 0.12, 0], color=C_CORAL, stroke_width=3.2).set_z_index(6)
        brk_r = Line([2.68, 0.12, 0], [3.38, 0.12, 0], color=C_SLATE, stroke_width=3.2).set_z_index(6)
        chasm_x = cross_mark([2.40, 0.12, 0], size=0.18, color=C_CORAL, sw=3.6, z=10)
        chasm_lbl = pill("창구 전달 끊김", fg=C_CORAL, bg=C_PANEL_HI, border=C_CORAL, size=9.8, px=0.09, py=0.03, z=9).move_to([2.40, 0.62, 0])

        field_ring = RoundedRectangle(corner_radius=0.10, width=2.48, height=3.68, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_SLATE, stroke_width=1.8).move_to([4.68, 0.12, 0]).set_z_index(3)
        field_hdr = pill("창구, 설계사 현장", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.8, z=7).move_to([4.68, 1.62, 0])
        p_head = Circle(radius=0.20, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=C_INK_1, stroke_width=2.0).move_to([4.15, 0.68, 0]).set_z_index(6)
        p_body = Arc(radius=0.32, start_angle=0, angle=PI, color=C_INK_1, stroke_width=2.2).move_to([4.15, 0.25, 0]).set_z_index(6)
        q_bub = RoundedRectangle(corner_radius=0.08, width=1.18, height=0.58, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.8).move_to([5.08, 0.68, 0]).set_z_index(7)
        q_txt = txt("청약 기준은?", size=10.0, color=C_CORAL, bold=True, z=8).move_to(q_bub)
        warn_tri = RegularPolygon(n=3, fill_color="#3D2B0D", fill_opacity=0.95, stroke_color=C_AMBER, stroke_width=2.0).scale(0.32).move_to([4.68, -0.45, 0]).set_z_index(7)
        warn_bang = txt("!", size=15, color=C_AMBER, bold=True, z=8).move_to(warn_tri.get_center() + DOWN * 0.04)
        warn_cap = fit(txt("근거 문서와 쪽수 없이 구두 안내 위험", size=9.6, color=C_AMBER, bold=True, z=7), max_w=2.24).move_to([4.68, -1.12, 0])
        field_vis = VGroup(field_ring, field_hdr, p_head, p_body, q_bub, q_txt, warn_tri, warn_bang, warn_cap)

        foot_1a = fit(
            pill("해결 과제: 요약서와 사업방법서를 같은 기준으로 정리하고, 본부 비교 결과를 창구 요약 카드까지 연결합니다", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.8, z=9),
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
            rt=1.25,
        )

        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.56,
            center=[-0.42, 0.12, 0],
            anims=[
                LaggedStart(*[FadeIn(mr, scale=0.9) for mr in mis_rows], lag_ratio=0.14),
                FadeIn(doc_tag_top),
                FadeIn(doc_tag_img),
            ],
            rt=1.25,
        )
        self.play(
            *[lp.animate.shift(RIGHT * 0.12) for lp in mis_lefts],
            *[rp.animate.shift(LEFT * 0.12) for rp in mis_rights],
            rate_func=there_and_back,
            run_time=0.60,
        )
        self.wait(0.95)

        dead_sig = glow_dot([1.46, 0.12, 0], color=C_GOLD, r=0.065, z=12)
        self.add(dead_sig)
        self.cam_move(
            zoom=1.48,
            center=[3.55, 0.12, 0],
            anims=[
                MoveAlongPath(dead_sig, Line([1.46, 0.12, 0], [2.36, 0.12, 0])),
                FadeIn(chasm_lbl, shift=UP * 0.06),
                Flash([2.40, 0.12, 0], color=C_CORAL, line_length=0.22, num_lines=8),
            ],
            rt=1.10,
        )
        self.play(FadeOut(dead_sig, scale=0.2), Circumscribe(q_bub, color=C_CORAL, stroke_width=2.2, buff=0.04), run_time=0.50)
        self.remove(dead_sig)
        self.wait(0.80)

        self.reset_cam_2d(anims=[FadeIn(foot_1a, shift=UP * 0.08)], rt=0.90)
        beat1a_all = VGroup(
            monoliths, doc_tag_top, doc_tag_img, tangle_3d,
            chamber, ch_hdr, mis_rows,
            brk_l, brk_r, chasm_x, chasm_lbl, field_vis, foot_1a,
        )
        self.check_bounds(VGroup(doc_tag_top, chamber, field_vis, foot_1a), "CH1A PAIN MACRO")
        self.wait(1.60)

        # -------------------------------------------------------------------
        # Beat 1B: Service Flow (Refinery -> HQ Screen -> A4 Card)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "구글 시트 정본을 스냅샷으로 담아 본부에는 오프라인 단독 HTML 화면을, 창구에는 A4 한 장 응대 카드를 제공합니다",
            rt=0.40,
        )

        srv_top_pill = fit(
            pill(
                f"운영 비용 {num(op_cost)}원(무료 도구 설계, AI Studio 무료 한도 기준), 칸을 누르면 원문 특약명과 근거 문서, 쪽수가 열림",
                fg=C_DARK_INK,
                bg=C_GOLD,
                border=WHITE,
                size=10.8,
                z=10,
            ),
            max_w=11.85,
        ).move_to([0.0, 2.60, 0])

        raw_docs = VGroup(
            *[
                RoundedRectangle(corner_radius=0.03, width=0.34, height=0.44, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_CYAN if k % 2 == 0 else C_VIOLET, stroke_width=1.5).move_to(
                    [-5.65 + k * 0.38, 1.56 + (k % 2) * 0.12, 0]
                )
                for k in range(5)
            ]
        ).set_z_index(6)
        raw_lbl = fit(txt(f"{num(news_inst_cnt)}개 기관 보도, 공시 문서", size=10.0, color=C_CYAN, bold=True, z=7), max_w=2.24).move_to([-4.90, 2.04, 0])

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
        funnel_txt = txt("검증과 표준화", size=9.8, color=WHITE, bold=True, z=7).move_to([-4.90, 0.72, 0])

        ledger_frame = RoundedRectangle(corner_radius=0.08, width=2.28, height=1.82, fill_color="#13251E", fill_opacity=0.96, stroke_color=C_MINT, stroke_width=2.0).move_to([-4.90, -0.96, 0]).set_z_index(4)
        ledger_hdr = fit(txt(f"구글 시트 정본 {num(sheet_tabs)}탭", size=10.4, color=C_MINT, bold=True, z=7), max_w=2.08).move_to([-4.90, -0.26, 0])
        ledger_cells = VGroup()
        for k in range(sheet_tabs):
            rr, cc = divmod(k, 5)
            cell_c = C_GOLD if k in (0, 3, 6, 11) else (C_MINT if k % 2 == 0 else C_CYAN)
            ledger_cells.add(
                RoundedRectangle(corner_radius=0.03, width=0.32, height=0.24, fill_color=cell_c, fill_opacity=0.88, stroke_width=0)
                .move_to([-5.66 + cc * 0.38, -0.68 - rr * 0.34, 0])
                .set_z_index(6)
            )
        ledger_sub = fit(txt(f"브라우저 점검 외부 요청 {num(browser_problems)}건 ✓", size=8.8, color=C_INK_1, z=7), max_w=2.12).move_to([-4.90, -1.66, 0])
        left_refinery = VGroup(raw_docs, raw_lbl, funnel_poly, funnel_txt, ledger_frame, ledger_hdr, ledger_cells, ledger_sub)

        dash_frame = RoundedRectangle(corner_radius=0.10, width=5.24, height=3.86, fill_color=C_PANEL, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.4).move_to([-0.24, 0.04, 0]).set_z_index(4)
        dash_title = fit(pill("① 본부 판단 화면 (사본 자료를 실은 오프라인 단독 HTML)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.4, z=7), max_w=4.92).move_to([-0.24, 1.60, 0])
        c_age = pill(f"{num(ref_age)}세", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.6, px=0.09, py=0.03, z=7)
        c_sex = pill(ref_sex_ko, fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=9.6, px=0.09, py=0.03, z=7)
        c_uw = pill(f"{base_var_name} ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.4, px=0.10, py=0.03, z=7)
        cond_strip = fit(VGroup(c_age, c_sex, c_uw).arrange(RIGHT, buff=0.10), max_w=4.88).move_to([-0.24, 1.06, 0])

        w1_box = RoundedRectangle(corner_radius=0.06, width=1.54, height=1.88, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=C_GOLD_DEEP, stroke_width=1.4).move_to([-1.92, -0.18, 0]).set_z_index(5)
        w1_h = txt("가입 관문 비교", size=9.8, color=C_GOLD, bold=True, z=7).move_to([-1.92, 0.52, 0])
        w1_g_open = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.34, height=0.40, fill_color="#383016", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.8),
            fit(txt(f"{epost_name}: 입원만 ▲", size=8.4, color=C_GOLD, bold=True, z=8), max_w=1.22),
        ).move_to([-1.92, 0.02, 0]).set_z_index(7)
        w1_g_shut = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.34, height=0.40, fill_color=C_CORAL_DIM, fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=1.4),
            fit(txt(f"{peer_site_names}: 입원 또는 수술 ×", size=8.2, color=C_CORAL, bold=True, z=8), max_w=1.24),
        ).move_to([-1.92, -0.54, 0]).set_z_index(7)

        w2_box = RoundedRectangle(corner_radius=0.06, width=1.64, height=1.88, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=1.4).move_to([-0.24, -0.18, 0]).set_z_index(5)
        w2_h = fit(txt(f"표준담보 {num(cov_in_use)}개, 견준 쌍 {num(cmp_pairs)}개", size=9.2, color=C_CYAN, bold=True, z=7), max_w=1.50).move_to([-0.24, 0.52, 0])
        hm_cells = VGroup(
            *[
                RoundedRectangle(corner_radius=0.03, width=0.36, height=0.26, fill_color=hcol, fill_opacity=0.88, stroke_width=0)
                .move_to([-0.66 + (k % 3) * 0.42, 0.12 - (k // 3) * 0.32, 0])
                .set_z_index(7)
                for k, hcol in enumerate([C_GOLD, C_CYAN, C_GOLD, C_MINT, C_GOLD, C_CORAL, C_MINT, C_CYAN, C_GOLD])
            ]
        )
        w2_pg = fit(pill(f"{doc_kind} {num(doc_page)}쪽 열림", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=8.4, px=0.08, py=0.03, z=8), max_w=1.48).move_to([-0.24, -0.84, 0])

        w3_box = RoundedRectangle(corner_radius=0.06, width=1.54, height=1.88, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_color=C_MINT, stroke_width=1.4).move_to([1.44, -0.18, 0]).set_z_index(5)
        w3_h = txt("실제 지급액", size=9.8, color=C_MINT, bold=True, z=7).move_to([1.44, 0.52, 0])
        w3_ax = Line([0.84, -0.68, 0], [2.04, -0.68, 0], color=C_SLATE, stroke_width=1.5).set_z_index(6)
        full_bar_h = 0.88
        red_bar_h = full_bar_h * red_rate
        w3_b1 = Rectangle(width=0.32, height=red_bar_h, fill_color=C_CYAN, fill_opacity=0.85, stroke_width=0).move_to([1.18, -0.68 + red_bar_h / 2, 0]).set_z_index(7)
        w3_b2 = Rectangle(width=0.36, height=full_bar_h, fill_color=C_GOLD, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.0).move_to([1.68, -0.68 + full_bar_h / 2, 0]).set_z_index(7)
        w3_cap = fit(txt(f"계약일 {num(red_months)}개월 {num(red_pct)}% 뒤 전액", size=8.2, color=C_MINT, bold=True, z=7), max_w=1.42).move_to([1.44, -0.90, 0])
        dash_foot = fit(txt(f"금지 표현 {num(forb_cnt)}개 빌드 차단, 기준 가입 {num(basis_mw)}만 원 예시 ✓", size=9.2, color=C_MINT, bold=True, z=7), max_w=4.90).move_to([-0.24, -1.52, 0])
        hq_dash_grp = VGroup(dash_frame, dash_title, cond_strip, w1_box, w1_h, w1_g_open, w1_g_shut, w2_box, w2_h, hm_cells, w2_pg, w3_box, w3_h, w3_ax, w3_b1, w3_b2, w3_cap, dash_foot)

        feed_to_dash = arrow_2d([-3.68, -0.55, 0], [-2.90, -0.15, 0], color=C_MINT, sw=2.6, tip=0.13, z=7)
        bridge_to_a4 = arrow_2d([2.42, 0.04, 0], [3.34, 0.04, 0], color=C_GOLD, sw=3.2, tip=0.16, z=8)
        bridge_lbl = pill("A4 한 장 출력", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.2, px=0.08, py=0.03, z=9).move_to([2.88, 0.42, 0])

        a4_srv = Rectangle(width=2.58, height=3.86, fill_color=C_IVORY, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.3).move_to([4.72, 0.04, 0]).set_z_index(5)
        a4_red_top = Line(a4_srv.get_corner(UL), a4_srv.get_corner(UR), color=C_CORAL, stroke_width=4.8).set_z_index(7)
        a4_tag = pill("대외 배포 금지, A4 한 장", fg=WHITE, bg=C_CORAL, border=C_CORAL, size=9.2, px=0.09, py=0.03, z=8).move_to([4.72, 1.56, 0])
        a4_hdr = fit(txt("② 창구, 설계사 응대 카드", size=12.4, color=C_DARK_INK, bold=True, z=7), max_w=2.36).move_to([4.72, 1.08, 0])
        a4_bars = VGroup()
        for ay, acol, albl in [
            (0.48, C_GOLD_DEEP, f"▲ {card_order[0]}: 수술 이력 고지 차이"),
            (-0.14, "#1E6B7B", f"◆ {card_order[1]}: {lead_str}"),
            (-0.76, "#2D3748", f"§ {card_order[2]}: 근거 문서와 쪽수"),
        ]:
            abg = RoundedRectangle(corner_radius=0.04, width=2.24, height=0.46, fill_color="#E5E4DC", fill_opacity=1.0, stroke_color="#C4C2B6", stroke_width=1.0).move_to([4.72, ay, 0]).set_z_index(6)
            abar = Rectangle(width=0.09, height=0.46, fill_color=acol, fill_opacity=1.0, stroke_width=0).move_to(abg.get_left() + RIGHT * 0.045).set_z_index(7)
            a4_bars.add(VGroup(abg, abar, fit(txt(albl, size=9.2, color=C_DARK_INK, bold=True, z=7), max_w=1.96).move_to(abg.get_center() + RIGHT * 0.04)))
        a4_bot = Rectangle(width=2.58, height=0.44, fill_color=C_DARK_INK, fill_opacity=1.0, stroke_width=0).move_to([4.72, -1.67, 0]).set_z_index(6)
        a4_bot_txt = fit(txt("창구 내부 참고용 A4 한 장 전달 ✓", size=9.8, color=C_GOLD, bold=True, z=7), max_w=2.34).move_to(a4_bot)
        a4_srv_grp = VGroup(a4_srv, a4_red_top, a4_tag, a4_hdr, a4_bars, a4_bot, a4_bot_txt)

        scope_foot = fit(
            pill("원칙: 비공개 자료 없이 공개된 상품요약서, 사업방법서, 보도자료의 사실만 사용합니다", fg=C_INK_1, bg=C_PANEL, border=C_SLATE, size=10.6, z=8),
            max_w=11.85,
        ).move_to([0.0, -2.56, 0])

        self.cam_move(
            zoom=1.42,
            center=[-4.55, 0.15, 0],
            anims=[
                FadeOut(beat1a_all, shift=UP * 0.10),
                FadeIn(raw_lbl),
                LaggedStart(*[FadeIn(rd, shift=DOWN * 0.18) for rd in raw_docs], lag_ratio=0.08),
                FadeIn(VGroup(funnel_poly, funnel_txt)),
                FadeIn(VGroup(ledger_frame, ledger_hdr, ledger_sub)),
                LaggedStart(*[FadeIn(lc, scale=0.3) for lc in ledger_cells], lag_ratio=0.04),
            ],
            rt=1.15,
        )
        self.remove(beat1a_all)
        self.wait(0.75)

        self.cam_move(
            zoom=1.42,
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
            rt=1.25,
        )
        self.wait(0.90)

        print_laser = Line([3.38, 1.88, 0], [6.06, 1.88, 0], color=C_GOLD, stroke_width=3.6).set_z_index(12)
        self.add(print_laser)
        self.cam_move(
            zoom=1.40,
            center=[3.95, 0.04, 0],
            anims=[
                GrowArrow(bridge_to_a4),
                FadeIn(bridge_lbl, scale=0.88),
                FadeIn(VGroup(a4_srv, a4_red_top, a4_hdr)),
                print_laser.animate.move_to([4.72, -1.85, 0]),
                FadeIn(a4_tag, scale=1.2),
                LaggedStart(*[FadeIn(ab, shift=DOWN * 0.08) for ab in a4_bars], lag_ratio=0.14),
                FadeIn(VGroup(a4_bot, a4_bot_txt)),
            ],
            rt=1.25,
        )
        self.remove(print_laser)
        self.wait(0.85)

        self.reset_cam_2d(
            anims=[FadeIn(srv_top_pill, shift=DOWN * 0.08), FadeIn(scope_foot, shift=UP * 0.08)],
            rt=0.90,
        )

        ch1_stage = VGroup(srv_top_pill, left_refinery, feed_to_dash, hq_dash_grp, bridge_to_a4, bridge_lbl, a4_srv_grp, scope_foot)
        self.check_bounds(ch1_stage, "CH1B SERVICE INFOGRAPHIC")
        self.wait(1.80)

        # ===================================================================
        # 2장: 구현한 운영 화면 구성
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch1_stage,
            hl,
            hr,
            hb,
            2,
            f"구현한 {num(scr_cnt)}개 화면: 기준 조건으로 함께 바뀌는 구성",
            f"대표 조건과 기준 종형을 고르면 {num(scr_cnt)}개 화면이 같은 사본 기준으로 맞춰집니다 (화면 기준 세 회사)",
        )

        hub_c = np.array([0.0, 0.22, 0.0])
        hub_orbit_3d = Circle(radius=1.24, fill_opacity=0.0, stroke_color=C_GOLD_DEEP, stroke_width=1.8).rotate(PI / 5, axis=RIGHT).move_to(hub_c + OUT * 0.22)
        hub_outer_ring = DashedVMobject(Circle(radius=1.04, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.2).move_to(hub_c), num_dashes=28).set_z_index(7)
        hub_core = Circle(radius=0.86, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.8).move_to(hub_c).set_z_index(8)
        dial_needle = Arrow(hub_c + UP * 0.62, hub_c + UP * 1.06, buff=0, color=C_GOLD, stroke_width=3.2, tip_length=0.14).set_z_index(12)
        hub_txt = fit(
            VGroup(
                txt("대표 조건, 기준 종형", size=10.2, color=C_GOLD, bold=True, z=9),
                pill(f"{num(ref_age)}세, {ref_sex_ko}", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.6, px=0.08, py=0.03, z=9),
                pill(base_var_name, fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.2, px=0.08, py=0.03, z=9),
            ).arrange(DOWN, buff=0.07),
            max_w=1.46,
        ).move_to(hub_c)
        central_hub = VGroup(hub_orbit_3d, hub_outer_ring, hub_core, dial_needle, hub_txt)

        def make_radial_module(cx: float, cy: float, col: str, badge_s: str, title_s: str, cap_s: str, widget: VGroup) -> VGroup:
            card = RoundedRectangle(corner_radius=0.09, width=3.52, height=1.52, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.0).move_to([cx, cy, 0]).set_z_index(4)
            dark_fg = col in (C_GOLD, C_MINT, C_CYAN, C_AMBER, "#93C5FD")
            bdg = pill(badge_s, fg=C_DARK_INK if dark_fg else WHITE, bg=col, border=WHITE, size=9.2, px=0.08, py=0.025, z=7)
            hdr = fit(VGroup(bdg, txt(title_s, size=11.2, color=col, bold=True, z=7)).arrange(RIGHT, buff=0.09), max_w=3.26).move_to([cx, cy + 0.50, 0])
            widget = fit(widget, max_w=3.22).move_to([cx, cy - 0.04, 0]).set_z_index(7)
            cap = fit(txt(cap_s, size=9.2, color=C_INK_1, z=7), max_w=3.26).move_to([cx, cy - 0.54, 0])
            return VGroup(card, hdr, widget, cap)

        wg1 = VGroup(
            pill(f"{wk_news['week']} 소식 {num(wk_news['count'])}건", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.4, px=0.07, py=0.03),
            pill("신담보출시, 상품개정", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.4, px=0.07, py=0.03),
        ).arrange(RIGHT, buff=0.10)
        m_1 = make_radial_module(
            -4.35, 1.92, C_VIOLET, "화면 ①", "주간 시장 소식",
            f"{num(news_inst_cnt)}개 기관 소식 정리 (우열 변화는 지난주 사본 누적 뒤 표시)", wg1,
        )

        wg2 = VGroup(
            pill(f"{epost_name}: 입원만 ▲", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.4, px=0.08, py=0.04),
            txt("vs", size=9.2, color=C_INK_2, bold=True),
            pill(f"{peer_site_names}: 입원 또는 수술 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.2, px=0.08, py=0.04),
        ).arrange(RIGHT, buff=0.07)
        m_2 = make_radial_module(-4.35, 0.22, C_GOLD, "화면 ②", "가입 관문 비교", "병력과 나이 구간별 고지 질문 차이를 대조", wg2)

        wg3_step = VMobject(color=C_MINT, stroke_width=2.6)
        wg3_step.set_points_as_corners([[0.25, -0.18, 0], [0.58, -0.18, 0], [0.58, 0.18, 0], [1.08, 0.18, 0]])
        wg3 = VGroup(
            pill("주계약", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.4, px=0.07, py=0.03).move_to([-1.00, 0, 0]),
            arrow_2d([-0.66, 0, 0], [-0.36, 0, 0], color=C_MINT, sw=1.6, tip=0.07),
            pill("특약 선택", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.4, px=0.07, py=0.03).move_to([0.00, 0, 0]),
            wg3_step,
        )
        m_3 = make_radial_module(-4.35, -1.48, C_MINT, "화면 ④", "특약 조합별 실제 지급액", "결합 제약과 감액 기간을 반영한 실제 지급액 계산", wg3)

        wg4_cells = VGroup(
            *[RoundedRectangle(corner_radius=0.03, width=0.28, height=0.28, fill_color=c, fill_opacity=0.9, stroke_width=0).move_to([-1.05 + idx * 0.34, 0, 0]) for idx, c in enumerate([C_GOLD, C_CYAN, C_MINT, C_CORAL])]
        )
        wg4 = VGroup(
            wg4_cells,
            arrow_2d([0.18, 0, 0], [0.46, 0, 0], color=C_GOLD, sw=1.6, tip=0.07),
            pill("근거 문서와 쪽수, 카드 인쇄", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.2, px=0.08, py=0.03).move_to([1.08, 0, 0]),
        )
        m_4 = make_radial_module(
            4.35, 1.92, C_CYAN, "화면 ③", f"표준담보 {num(cov_in_use)}개 비교표",
            f"견준 담보 쌍 {num(cmp_pairs)}개 비교 및 A4 한 장 카드 출력", wg4,
        )

        old_yr = rev_old["reduce"][0]["months"] // 12
        new_yr = rev_new["reduce"][0]["months"] // 12
        wg5 = VGroup(
            pill(f"{rev_old['revision_no']} ({num(rev_old['pay_manwon'])}만, {num(old_yr)}년)", fg=C_INK_1, bg=C_BG_SUB, border=C_SLATE, size=8.2, px=0.07, py=0.03),
            arrow_2d([0, 0, 0], [0.26, 0, 0], color=C_AMBER, sw=2.0, tip=0.08),
            pill(f"{rev_new['revision_no']} ({num(rev_new['pay_manwon'])}만, {num(new_yr)}년 ▲)", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.2, px=0.07, py=0.03),
        ).arrange(RIGHT, buff=0.07)
        m_5 = make_radial_module(
            4.35, 0.22, C_AMBER, "화면 ⑤", "개정 전후 비교",
            f"기준 가입 {num(basis_mw)}만 원 예시, 달라진 담보 {num(rev_chg_total)}개 연결", wg5,
        )

        max_wlog_r = max(wlog_res.values())
        h_pass = max((wlog_res["통과"] / max_wlog_r) * 0.38, 0.03)
        h_hold = max((wlog_res["보류"] / max_wlog_r) * 0.38, 0.03)
        h_rej = max((wlog_res["반려"] / max_wlog_r) * 0.38, 0.03)
        wg6_bars = VGroup(
            Rectangle(width=0.20, height=h_pass, fill_color=C_GOLD, fill_opacity=0.95, stroke_width=0).move_to([-1.02, -0.17 + h_pass / 2, 0]),
            Rectangle(width=0.20, height=h_hold, fill_color=C_CYAN, fill_opacity=0.90, stroke_width=0).move_to([-0.76, -0.17 + h_hold / 2, 0]),
            Rectangle(width=0.20, height=h_rej, fill_color=C_CORAL, fill_opacity=0.90, stroke_width=0).move_to([-0.50, -0.17 + h_rej / 2, 0]),
        )
        wg6 = VGroup(
            wg6_bars,
            pill(f"작업 로그 {num(wlog_site)}건 공개 (화면 세 회사)", fg="#93C5FD", bg=C_BG_SUB, border="#93C5FD", size=8.2, px=0.08, py=0.03).move_to([0.48, 0, 0]),
        )
        m_6 = make_radial_module(4.35, -1.48, "#93C5FD", "화면 ⑥", "검증과 작업 로그", "추출, 코드 대조, 판정, 사람 검토 이관 기록 공개", wg6)

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
            pill(
                f"안전장치: 금지 표현 {num(forb_cnt)}개 빌드 차단, 공시에 없는 특약 보험료(적재 {num(prem_rows)}행)는 추정해 적지 않음 ✓",
                fg=C_MINT,
                bg=C_PANEL_HI,
                border=C_MINT,
                size=10.6,
                z=9,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.62, 0])

        shockwave = Circle(radius=0.85, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=3.6, stroke_opacity=0.95).move_to(hub_c).set_z_index(11)
        spoke_pulses = VGroup(*[glow_dot(s0, color=scol, r=0.065, z=14) for s0, _, scol in spoke_pairs])

        self.cam_move(
            phi=44 * DEGREES,
            theta=-64 * DEGREES,
            zoom=0.92,
            center=[0.0, 0.10, 0.0],
            anims=[
                FadeIn(central_hub, scale=0.82),
                LaggedStart(*[GrowArrow(sp) for sp in spokes], lag_ratio=0.05),
                LaggedStart(*[FadeIn(md, scale=0.92) for md in modules_6], lag_ratio=0.07),
            ],
            rt=1.25,
        )
        self.add(shockwave, spoke_pulses)
        self.cam_move(
            theta=-48 * DEGREES,
            anims=[
                Rotate(dial_needle, angle=-2 * PI / 3, about_point=hub_c),
                Rotate(hub_outer_ring, angle=PI / 3, about_point=hub_c),
                Rotate(hub_orbit_3d, angle=PI / 2, axis=OUT),
                shockwave.animate.scale(5.2).set_stroke(opacity=0.0),
                *[MoveAlongPath(spoke_pulses[k], Line(spoke_pairs[k][0], spoke_pairs[k][1])) for k in range(scr_cnt)],
            ],
            rt=1.05,
        )
        self.remove(shockwave, spoke_pulses, *spoke_pulses)

        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.42,
            center=[-4.20, 0.35, 0],
            anims=[Circumscribe(m_2[0], color=C_GOLD, stroke_width=2.4, buff=0.03)],
            rt=1.10,
        )
        self.wait(0.85)
        self.cam_move(
            zoom=1.42,
            center=[4.20, 0.35, 0],
            anims=[Circumscribe(m_4[0], color=C_CYAN, stroke_width=2.4, buff=0.03)],
            rt=1.10,
        )
        self.wait(0.85)

        hb = self.update_subtitle(
            hb,
            "이어서 수집, 추출, 판정 검증, 표준담보 연결 각 단계에서 부딪힌 문제와 푼 방법을 살펴봅니다",
            rt=0.40,
        )
        self.reset_cam_2d(anims=[FadeIn(guard_ribbon, shift=UP * 0.08)], rt=0.90)

        ch2_stage = VGroup(central_hub, spokes, modules_6, guard_ribbon)
        self.check_bounds(ch2_stage, "CH2 RADIAL INFOGRAPHIC")
        self.wait(1.80)

        self.fade_out_part(ch2_stage, hl, hr, hb)
