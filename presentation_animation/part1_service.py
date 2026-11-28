from __future__ import annotations

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
    C_MINT,
    C_PANEL,
    C_PANEL_HI,
    C_SLATE,
    C_VIOLET,
    C_WHITE,
    SCREEN_TITLE,
    PostLifeBaseScene,
    TERM,
    arrow_2d,
    bb_badge,
    console_tabs,
    cross_mark,
    fact,
    fit,
    floor_grid_3d,
    glow_dot,
    label_ko,
    make_doc_icon,
    make_refinery_funnel,
    num,
    pillar_3d,
    pill,
    set_3d_tier,
    txt,
)
from infographics import make_dark_a4_sheet, svg_icon


class Part1ServiceScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        org_names = fact("org_names")
        epost_name = org_names["EPOST"]
        peer_site_names = ", ".join(org_names[o] for o in fact("site_orgs") if o != "EPOST")
        target_counts = fact("comparison_target_counts")
        target_total = sum(target_counts.values())
        site_org_cnt = fact("site_org_count")
        prod_org_cnt = fact("product_org_count")
        hw_pages = fact("hanwha_summary_pages")
        img_pages = fact("image_doc", "pages")

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
        card_order = fact("card_category_order")
        c4_tabs = console_tabs()
        c4_cnt = c4_tabs["count"]
        t_names = c4_tabs["names"]
        seg_cnt = fact("segment_map_cell_count")
        rev_chg_total = fact("revision_changes", "전체")
        mnews_cnt = fact("market_news_count")
        main_lim = fact("reference_main_contract_limit_manwon")
        ep_comb = fact("combination_constraints_by_org", "EPOST")
        pend_site = fact("mapping_status_site", "대기")
        n_ins_cats = len(fact("sales_insight_categories"))
        ins_cnt = fact("sales_insight_count")
        g_cnts = fact("graph_counts")

        # ===================================================================
        # 1장: 구현 목표 서비스
        # ===================================================================
        hl, hr, hb = self.make_hud(
            1,
            f"구현 목표 서비스: 공시 문서 비교 화면과 현장 {TERM['script_doc']}",
            f"우체국 포함 화면 {num(site_org_cnt)}개사, {TERM['snapshot_first']} {num(prod_org_cnt)}개사의 공시 문서를 동일 기준으로 비교합니다",
        )

        # -------------------------------------------------------------------
        # Beat 1A-1: True 3D Document Canyon (실측 요약서 막대만 색상 부여, 상품요약서 행 일치)
        # -------------------------------------------------------------------
        base_z = -0.92
        canyon_floor = floor_grid_3d(-4.5, 4.5, -1.75, 1.75, z_val=base_z, step_x=1.125, step_y=0.875, col=C_CYAN_DIM)

        h_hw = 1.86
        h_img = h_hw * (img_pages / hw_pages)
        h_ref = 0.54

        bg_towers = VGroup()
        for gx in [-3.75, -2.45, -1.20, 0.15, 1.45, 2.75, 3.85]:
            for gy in [0.86, -0.86]:
                if gy > 0 and gx in (-1.20, 1.45):
                    continue
                bg_towers.add(pillar_3d(gx, gy, 0.60, 0.52, h_ref, base_z=base_z, col=C_SLATE, opacity=0.22, stroke_col=C_SLATE, sw=1.0))

        tower_hw = pillar_3d(-1.20, 0.86, 0.86, 0.74, h_hw, base_z=base_z, col=C_AMBER, opacity=0.86, stroke_col=WHITE, sw=1.8)
        tower_img = pillar_3d(1.45, 0.86, 0.86, 0.74, h_img, base_z=base_z, col=C_VIOLET, opacity=0.86, stroke_col=WHITE, sw=1.8)

        hw_slabs = VGroup(
            *[
                Line(
                    [-1.63, 0.48, base_z + (k + 1) * (h_hw / 6)],
                    [-0.77, 0.48, base_z + (k + 1) * (h_hw / 6)],
                    color=WHITE,
                    stroke_width=1.3,
                    stroke_opacity=0.60,
                )
                for k in range(5)
            ]
        )
        img_slabs = VGroup(
            *[
                Line(
                    [1.02, 0.48, base_z + (k + 1) * (h_img / 4)],
                    [1.88, 0.48, base_z + (k + 1) * (h_img / 4)],
                    color=WHITE,
                    stroke_width=1.3,
                    stroke_opacity=0.60,
                )
                for k in range(3)
            ]
        )

        set_3d_tier(hw_slabs, 0.0, sub=0, sort_3d=True)
        set_3d_tier(img_slabs, 0.0, sub=0, sort_3d=True)

        tangle_3d = VGroup(
            CubicBezier(
                [-1.20, 0.86, base_z + h_hw],
                [-0.20, 1.25, base_z + h_hw + 0.46],
                [0.55, 1.15, base_z + h_img + 0.52],
                [1.45, 0.86, base_z + h_img],
                color=C_CORAL,
                stroke_width=2.8,
            ),
            CubicBezier(
                [-1.20, -0.86, base_z + h_ref],
                [-0.10, -0.25, base_z + 1.68],
                [0.55, 0.35, base_z + 1.56],
                [1.45, 0.86, base_z + h_img],
                color=C_CYAN,
                stroke_width=2.3,
            ),
        )
        set_3d_tier(tangle_3d, 2.0, sub=0, sort_3d=True)

        bb_hw = bb_badge(
            "한화생명 상품요약서",
            f"단일 상품 실측 {num(hw_pages)}쪽",
            fg=C_DARK_INK,
            bg=C_GOLD,
            border=WHITE,
            size=15.2,
            sub_size=13.8,
            sub_col=C_DARK_INK,
            px=0.14,
            py=0.07,
        ).move_to([-1.26, 0.86, base_z + h_hw + 0.40])

        bb_img = bb_badge(
            "이미지형 상품요약서",
            f"미래에셋 복수 요약서 합계 {num(img_pages)}쪽",
            fg=C_WHITE,
            bg="#261844",
            border=C_VIOLET,
            size=15.0,
            sub_size=13.6,
            sub_col=C_GOLD,
            px=0.14,
            py=0.07,
        ).move_to([1.74, 0.86, base_z + h_img + 0.46])

        bb_row_sum = bb_badge("뒤쪽 행: 상품요약서", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=13.8, px=0.13, py=0.06).move_to([-5.25, -0.45, base_z + 0.88])
        bb_row_biz = bb_badge("앞쪽 행: 사업방법서", fg=C_GOLD, bg="#151208", border=C_GOLD, size=13.8, px=0.13, py=0.06).move_to([-4.35, -1.65, base_z + 0.24])
        canyon_bbs = [bb_hw, bb_img, bb_row_sum, bb_row_biz]

        canyon_hud_top = bb_badge(
            f"비교 대상 {TERM['peer']} {num(target_total)}개사(총자산 기사 기준, 공식 순위 미확정) | 현재 우체국 포함 화면 {num(site_org_cnt)}개사, {TERM['snapshot']} {num(prod_org_cnt)}개사",
            "실측 쪽수 막대: 한화생명은 단일 상품, 미래에셋생명은 복수 요약서 합계 (회색 막대는 예시 그림)",
            fg=C_GOLD,
            bg="#091018",
            border=C_GOLD_DEEP,
            size=13.8,
            sub_size=12.8,
            sub_col=C_INK_0,
            px=0.16,
            py=0.06,
            z=25,
        ).move_to([0.0, 2.68, 0])
        fit(canyon_hud_top, max_w=12.50)

        self.set_camera_orientation(phi=58 * DEGREES, theta=-62 * DEGREES, zoom=0.94, frame_center=[0.05, 0.08, 0.42])
        self.register_billboards(*canyon_bbs)

        canyon_3d_grp = VGroup(canyon_floor, bg_towers, tower_hw, tower_img, hw_slabs, img_slabs, tangle_3d)
        self.add_fixed_in_frame_mobjects(canyon_hud_top)
        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(canyon_floor),
                LaggedStart(*[FadeIn(bt, shift=OUT * 0.25) for bt in bg_towers], lag_ratio=0.04),
                FadeIn(VGroup(bb_row_sum, bb_row_biz)),
                FadeIn(canyon_hud_top, shift=DOWN * 0.08),
            ],
            rt=1.50,
        )
        self.wait(1.40)

        self.play(
            FadeIn(VGroup(tower_hw, hw_slabs), shift=OUT * 0.55),
            FadeIn(bb_hw, shift=OUT * 0.20),
            run_time=1.40,
        )
        self.wait(1.60)

        self.cam_move(
            phi=52 * DEGREES,
            theta=-32 * DEGREES,
            zoom=0.94,
            center=[0.10, 0.08, 0.42],
            anims=[
                FadeIn(VGroup(tower_img, img_slabs), shift=OUT * 0.45),
                FadeIn(bb_img, shift=OUT * 0.20),
                Create(tangle_3d, lag_ratio=0.15),
            ],
            rt=2.20,
        )
        self.wait(3.60)

        # -------------------------------------------------------------------
        # Beat 1A-2: 기준 불일치 스트립 -> 창구, 설계사 현장 벡터 인포그래픽 (인물 스틱 도형 배제)
        # -------------------------------------------------------------------
        sp_chamber = RoundedRectangle(
            corner_radius=0.12, width=9.36, height=4.78, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=2.3
        ).move_to([0.0, 0.22, 0]).set_z_index(3)
        sp_hdr = fit(
            pill("단순 비교가 어려운 이유: 회사별 인수기준과 표기 단위 상이", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=18.0, px=0.14, py=0.06, z=7),
            max_w=8.96,
        ).move_to([0.0, 2.12, 0])

        mis_rows = VGroup()
        for my, ic_nm, l_s, l_c, r_s, r_c, sub_s in [
            (1.04, "shield_check", f"{epost_name}: 입원만 고지", C_GOLD, f"{peer_site_names}: 입원 또는 수술", C_CYAN, f"간편심사 {TERM['disc_item']} 범위 상이"),
            (-0.16, "git_lineage", f"{TERM['peer']}: 뇌·심장질환 수술비", C_VIOLET, f"{epost_name}: 뇌혈관, 심장 분리", C_MINT, "통합특약 대 분리특약 구성 단위 상이"),
            (-1.36, "code_calc", f"기준 {num(basis_mw)}만에 지급 {num(pay_new_mw)}만", C_GOLD, f"{org_names['SAMSUNGFIRE']}: 가입금액의 N%", C_AMBER, "정액 지급 또는 가입금액비율 표기 상이"),
        ]:
            ic_m = svg_icon(ic_nm, size=0.46, col=l_c, accent=r_c, z=8).move_to([-4.18, my + 0.16, 0])
            lp = fit(pill(l_s, fg=l_c, bg=C_PANEL_HI, border=l_c, size=17.8, px=0.10, py=0.055, z=7), max_w=3.56).move_to([-2.04, my + 0.16, 0])
            rp = fit(pill(r_s, fg=r_c, bg=C_PANEL_HI, border=r_c, size=17.8, px=0.10, py=0.055, z=7), max_w=4.16).move_to([2.36, my + 0.16, 0])
            neq = txt("≠", size=23, color=C_CORAL, bold=True, z=8).move_to([0.04, my + 0.16, 0])
            st = fit(txt(sub_s, size=17.6, color=C_INK_0, bold=True, z=7), max_w=8.40).move_to([0.16, my - 0.32, 0])
            mis_rows.add(VGroup(ic_m, lp, neq, rp, st))

        self.reset_cam_2d(
            anims=[
                FadeOut(canyon_3d_grp),
                FadeOut(VGroup(*canyon_bbs)),
                FadeOut(canyon_hud_top),
                FadeIn(VGroup(sp_chamber, sp_hdr), scale=0.95),
            ],
            rt=1.20,
        )
        self.clear_billboards(*canyon_bbs)
        self.remove_fixed_in_frame_mobjects(canyon_hud_top)
        self.remove(canyon_3d_grp, canyon_hud_top)

        for r_grp in mis_rows:
            ic_i, lp_i, neq_i, rp_i, st_i = r_grp
            self.play(
                FadeIn(ic_i, scale=0.8),
                FadeIn(lp_i, shift=RIGHT * 0.30),
                FadeIn(rp_i, shift=LEFT * 0.30),
                FadeIn(neq_i, scale=1.4),
                FadeIn(st_i, shift=UP * 0.06),
                run_time=1.05,
            )
            self.play(
                lp_i.animate.shift(RIGHT * 0.14),
                rp_i.animate.shift(LEFT * 0.14),
                rate_func=there_and_back,
                run_time=0.55,
            )
            self.wait(1.35)

        chamber_full = VGroup(sp_chamber, sp_hdr, mis_rows)

        brk_l = Line([0.75, 0.22, 0], [1.45, 0.22, 0], color=C_CORAL, stroke_width=3.6).set_z_index(6)
        brk_r = Line([2.03, 0.22, 0], [2.72, 0.22, 0], color=C_SLATE, stroke_width=3.6).set_z_index(6)
        chasm_x = cross_mark([1.74, 0.22, 0], size=0.20, color=C_CORAL, sw=4.0, z=10)
        chasm_lbl = pill("창구 전달 단절", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=13.8, px=0.11, py=0.05, z=9).move_to([1.74, 0.82, 0])

        # 우측 창구, 설계사 현장 벡터 인포그래픽 보드 (사람 모양 도형 대신 지점 파사드, 근거 단절, 위험 인포그래픽)
        field_ring = RoundedRectangle(
            corner_radius=0.10, width=3.56, height=4.10, fill_color=C_PANEL, fill_opacity=0.97, stroke_color=C_AMBER, stroke_width=2.2
        ).move_to([4.53, 0.22, 0]).set_z_index(3)
        field_ic_top = svg_icon("branch_counter", size=0.64, col=C_GOLD, accent=C_CORAL, bg="#1E1910", z=7).move_to([3.32, 1.62, 0])
        field_hdr_t = fit(
            VGroup(
                txt("창구, 설계사 현장", size=15.0, color=C_GOLD, bold=True, z=7),
                txt("실시간 상담 응대 접점", size=12.8, color=C_INK_1, bold=True, z=7),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.045),
            max_w=2.42,
        ).move_to([4.94, 1.62, 0])
        field_div = Line([2.90, 1.08, 0], [6.16, 1.08, 0], color=C_SLATE, stroke_width=1.2).set_z_index(5)

        f_row1_bg = RoundedRectangle(corner_radius=0.06, width=3.34, height=1.14, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=1.5).move_to([4.53, 0.36, 0]).set_z_index(5)
        f_ic_doc = svg_icon("doc_text", size=0.46, col=C_SLATE, accent=C_CORAL, z=7).move_to([3.20, 0.36, 0])
        f_row1_t = fit(
            VGroup(
                txt("원문 근거 쪽수 미표시", size=13.8, color=C_CORAL, bold=True, z=7),
                txt("수백 쪽 공시 문서 즉시 대조 불가", size=12.8, color=C_INK_0, bold=True, z=7),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.05),
            max_w=2.58,
        ).move_to([4.82, 0.36, 0])

        f_row2_bg = RoundedRectangle(corner_radius=0.06, width=3.34, height=1.14, fill_color="#261A0B", fill_opacity=0.96, stroke_color=C_AMBER, stroke_width=1.6).move_to([4.53, -0.96, 0]).set_z_index(5)
        f_ic_warn = svg_icon("alert_warn", size=0.46, col=C_AMBER, accent=C_CORAL, bg="#1C1308", z=7).move_to([3.20, -0.96, 0])
        f_row2_t = fit(
            VGroup(
                txt("구두 추정 안내 위험", size=13.8, color=C_AMBER, bold=True, z=7),
                txt(f"표준화된 {TERM['script_doc']} 부재", size=12.8, color=C_WHITE, bold=True, z=7),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.05),
            max_w=2.58,
        ).move_to([4.82, -0.96, 0])
        field_vis = VGroup(field_ring, field_ic_top, field_hdr_t, field_div, f_row1_bg, f_ic_doc, f_row1_t, f_row2_bg, f_ic_warn, f_row2_t)

        foot_1a = fit(
            pill(
                f"해결 과제: 상품요약서와 사업방법서를 동일 기준으로 정리해 본부 화면과 창구 {TERM['script_doc']}까지 연결",
                fg=C_WHITE,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=13.4,
                px=0.14,
                py=0.055,
                z=9,
            ),
            max_w=12.40,
        ).move_to([0.0, -2.58, 0])

        dead_sig = glow_dot([0.75, 0.22, 0], color=C_GOLD, r=0.075, z=12)
        self.play(
            chamber_full.animate.scale(0.75).move_to([-2.78, 0.22, 0]),
            FadeIn(VGroup(brk_l, brk_r, chasm_x, field_vis), shift=LEFT * 0.15),
            run_time=1.35,
        )
        self.add(dead_sig)
        self.play(
            MoveAlongPath(dead_sig, Line([0.75, 0.22, 0], [1.67, 0.22, 0])),
            FadeIn(chasm_lbl, shift=UP * 0.08),
            Flash([1.74, 0.22, 0], color=C_CORAL, line_length=0.26, num_lines=10),
            run_time=1.10,
        )
        self.play(
            FadeOut(dead_sig, scale=0.2),
            Circumscribe(f_row2_bg, color=C_AMBER, stroke_width=2.6, buff=0.04),
            FadeIn(foot_1a, shift=UP * 0.08),
            run_time=0.95,
        )
        self.remove(dead_sig)

        beat1a_all = VGroup(chamber_full, brk_l, brk_r, chasm_x, chasm_lbl, field_vis, foot_1a)
        self.check_bounds(beat1a_all, "CH A PAIN MACRO")
        self.wait(4.20)

        # -------------------------------------------------------------------
        # Beat 1B: 벡터 파이프라인 + 다크 슬레이트 A4 비교 요약지 장표로 2D 아키텍처 완성
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"{TERM['sheet_master']}를 {TERM['snapshot']}로 보관해 본부 단독 HTML 화면과 실무용 A4 {TERM['script_doc']}를 제공합니다",
        )

        srv_top_pill = fit(
            pill(
                f"운영 비용 {num(op_cost)}원(무료 도구 설계, AI Studio 무료 한도 기준), 항목을 클릭하면 원문 특약명과 근거 문서, 쪽수 표시",
                fg=C_DARK_INK,
                bg=C_GOLD,
                border=WHITE,
                size=13.4,
                px=0.13,
                py=0.055,
                z=10,
            ),
            max_w=12.50,
        ).move_to([0.0, 2.62, 0])

        raw_docs = VGroup(
            svg_icon("search_globe", size=0.52, col=C_CYAN, accent=C_GOLD, z=6).move_to([-5.64, 1.56, 0]),
            svg_icon("doc_text", size=0.52, col=C_CYAN, accent=C_MINT, z=6).move_to([-4.96, 1.62, 0]),
            svg_icon("doc_image", size=0.52, col=C_VIOLET, accent=C_GOLD, z=6).move_to([-4.28, 1.56, 0]),
        )
        raw_lbl = fit(txt(f"{num(news_inst_cnt)}개 기관 보도, 공시 문서", size=13.6, color=C_CYAN, bold=True, z=7), max_w=2.56).move_to([-4.96, 2.08, 0])

        refinery_funnel = make_refinery_funnel(
            -4.96,
            1.14,
            0.14,
            top_w=2.24,
            neck_w=0.62,
            col=C_CYAN,
            accent=C_GOLD,
            label_mob=txt("검증과 표준화", size=13.0, color=WHITE, bold=True),
            z=5,
        )

        ledger_frame = RoundedRectangle(corner_radius=0.08, width=2.58, height=1.96, fill_color="#11221C", fill_opacity=0.96, stroke_color=C_MINT, stroke_width=2.2).move_to([-4.96, -0.96, 0]).set_z_index(4)
        db_ic = svg_icon("database_master", size=0.42, col=C_MINT, accent=C_GOLD, z=7).move_to([-5.90, -0.30, 0])
        ledger_hdr = fit(txt(f"시트 {TERM['master']} {num(sheet_tabs)}탭", size=13.6, color=C_MINT, bold=True, z=7), max_w=1.96).move_to([-4.66, -0.30, 0])
        ledger_cells = VGroup()
        for k in range(sheet_tabs):
            rr, cc = divmod(k, 5)
            cell_c = C_GOLD if k in (0, 3, 6, 11) else (C_MINT if k % 2 == 0 else C_CYAN)
            ledger_cells.add(
                RoundedRectangle(corner_radius=0.03, width=0.33, height=0.22, fill_color=cell_c, fill_opacity=0.90, stroke_width=0)
                .move_to([-5.72 + cc * 0.38, -0.76 - rr * 0.31, 0])
                .set_z_index(6)
            )
        ledger_sub = fit(txt(f"외부 요청 {num(browser_problems)}건 ✓", size=13.2, color=C_INK_0, bold=True, z=7), max_w=2.38).move_to([-4.96, -1.68, 0])
        left_refinery = VGroup(raw_docs, raw_lbl, refinery_funnel, ledger_frame, db_ic, ledger_hdr, ledger_cells, ledger_sub).shift(LEFT * 0.08)

        dash_frame = RoundedRectangle(corner_radius=0.10, width=5.32, height=4.00, fill_color=C_PANEL, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.5).move_to([-0.56, 0.04, 0]).set_z_index(4)
        dash_title = fit(
            VGroup(
                svg_icon("hq_console", size=0.44, col=C_GOLD, accent=C_CYAN, z=8),
                pill(f"① {SCREEN_TITLE} (오프라인 단독 HTML)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=14.6, px=0.12, py=0.05, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=5.08,
        ).move_to([-0.56, 1.64, 0])
        c_age = pill(f"{num(ref_age)}세", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=13.0, px=0.10, py=0.04, z=7)
        c_sex = pill(ref_sex_ko, fg=C_WHITE, bg=C_BG_SUB, border=C_SLATE, size=13.0, px=0.10, py=0.04, z=7)
        c_uw = pill(f"{base_var_name} ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.0, px=0.11, py=0.04, z=7)
        c_tabs = pill(f"{num(c4_cnt)}개 탭 통합 비교", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=13.0, px=0.10, py=0.04, z=7)
        cond_strip = fit(VGroup(c_age, c_sex, c_uw, c_tabs).arrange(RIGHT, buff=0.08), max_w=5.08).move_to([-0.56, 1.06, 0])

        w1_box = RoundedRectangle(corner_radius=0.06, width=1.74, height=1.96, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_GOLD_DEEP, stroke_width=1.5).move_to([-2.26, -0.18, 0]).set_z_index(5)
        w1_h = txt(TERM["uw_cmp"], size=13.4, color=C_GOLD, bold=True, z=7).move_to([-2.26, 0.56, 0])
        w1_g_open = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.64, height=0.48, fill_color="#383016", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.8),
            fit(txt(f"{epost_name}: 입원만 ▲", size=12.8, color=C_GOLD, bold=True, z=8), max_w=1.60),
        ).move_to([-2.26, 0.02, 0]).set_z_index(7)
        w1_g_shut = VGroup(
            RoundedRectangle(corner_radius=0.04, width=1.64, height=0.48, fill_color=C_CORAL_DIM, fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=1.5),
            fit(txt(f"{TERM['peer']}: 입원·수술 ×", size=12.8, color=C_CORAL, bold=True, z=8), max_w=1.60),
        ).move_to([-2.26, -0.58, 0]).set_z_index(7)

        w2_box = RoundedRectangle(corner_radius=0.06, width=1.70, height=1.96, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=1.5).move_to([-0.46, -0.18, 0]).set_z_index(5)
        w2_h = fit(txt(f"담보 {num(cov_in_use)}개, 비교 {num(cmp_pairs)}건", size=13.4, color=C_CYAN, bold=True, z=7), max_w=1.62).move_to([-0.46, 0.56, 0])
        hm_cells = VGroup(
            *[
                RoundedRectangle(corner_radius=0.03, width=0.35, height=0.26, fill_color=hcol, fill_opacity=0.90, stroke_width=0)
                .move_to([-0.87 + (k % 3) * 0.41, 0.12 - (k // 3) * 0.32, 0])
                .set_z_index(7)
                for k, hcol in enumerate([C_GOLD, C_CYAN, C_GOLD, C_MINT, C_GOLD, C_CORAL, C_MINT, C_CYAN, C_GOLD])
            ]
        )
        w2_pg = fit(pill(f"{doc_kind} {num(doc_page)}쪽 표시", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.8, px=0.08, py=0.035, z=8), max_w=1.60).move_to([-0.46, -0.86, 0])

        w3_box = RoundedRectangle(corner_radius=0.06, width=1.56, height=1.96, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_MINT, stroke_width=1.5).move_to([1.24, -0.18, 0]).set_z_index(5)
        w3_h = txt("실제 지급액", size=13.4, color=C_MINT, bold=True, z=7).move_to([1.24, 0.56, 0])
        w3_ax = Line([0.62, -0.64, 0], [1.86, -0.64, 0], color=C_SLATE, stroke_width=1.6).set_z_index(6)
        full_bar_h = 0.86
        red_bar_h = full_bar_h * red_rate
        w3_b1 = Rectangle(width=0.34, height=red_bar_h, fill_color=C_CYAN, fill_opacity=0.88, stroke_width=0).move_to([0.98, -0.64 + red_bar_h / 2, 0]).set_z_index(7)
        w3_b2 = Rectangle(width=0.38, height=full_bar_h, fill_color=C_GOLD, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.1).move_to([1.48, -0.64 + full_bar_h / 2, 0]).set_z_index(7)
        w3_cap = fit(txt(f"{num(red_months)}개월 {num(red_pct)}% 감액", size=12.8, color=C_MINT, bold=True, z=7), max_w=1.48).move_to([1.24, -0.90, 0])
        dash_foot = fit(txt(f"금지 표현 {num(forb_cnt)}개 빌드 차단, 기준 가입금액 {num(basis_mw)}만 원 예시 ✓", size=13.0, color=C_MINT, bold=True, z=7), max_w=5.08).move_to([-0.56, -1.56, 0])
        hq_dash_grp = VGroup(dash_frame, dash_title, cond_strip, w1_box, w1_h, w1_g_open, w1_g_shut, w2_box, w2_h, hm_cells, w2_pg, w3_box, w3_h, w3_ax, w3_b1, w3_b2, w3_cap, dash_foot).shift(LEFT * 0.22)

        feed_to_dash = arrow_2d([-3.71, -0.55, 0], [-3.47, -0.18, 0], color=C_MINT, sw=2.8, tip=0.14, z=7)
        bridge_to_a4 = arrow_2d([1.93, 0.04, 0], [2.96, 0.04, 0], color=C_GOLD, sw=3.4, tip=0.16, z=8)
        bridge_lbl_bg = RoundedRectangle(corner_radius=0.06, width=0.90, height=0.58, fill_color=C_GOLD, fill_opacity=0.98, stroke_color=WHITE, stroke_width=1.5).move_to([2.445, 0.56, 0]).set_z_index(9)
        bridge_lbl_tx = fit(
            VGroup(
                txt("A4", size=13.0, color=C_DARK_INK, bold=True, z=10),
                txt(TERM["script_doc"], size=12.8, color=C_DARK_INK, bold=True, z=10),
            ).arrange(DOWN, buff=0.03),
            max_w=0.82,
        ).move_to(bridge_lbl_bg)
        bridge_lbl = VGroup(bridge_lbl_bg, bridge_lbl_tx)

        a4_srv_grp = make_dark_a4_sheet(
            [4.64, 0.04, 0],
            w=3.26,
            h=4.00,
            badge_s="내부 교육, 비교 참고용 (대외 배포 금지)",
            title_s=f"② 창구, 설계사 {TERM['script_doc']}",
            rows=[
                (C_GOLD, f"▲ {label_ko(card_order[0])}: 통원수술 고지"),
                (C_MINT, f"◆ {label_ko(card_order[1])}: 입원일당"),
                (C_CYAN, f"§ {label_ko(card_order[2])}: 근거 쪽수"),
            ],
            foot_s=f"현장 참고용 A4 {TERM['script_doc']} ✓",
            z=5,
        )

        scope_foot = fit(
            pill("원칙: 비공개 자료 없이 공개된 상품요약서, 사업방법서, 보도자료의 사실만 사용", fg=C_INK_0, bg=C_PANEL, border=C_SLATE, size=13.4, px=0.13, py=0.055, z=8),
            max_w=12.40,
        ).move_to([0.0, -2.58, 0])

        funnel_drops = VGroup(
            *[glow_dot([-5.04, 0.12, 0], color=C_MINT if k % 2 == 0 else C_GOLD, r=0.052, z=11) for k in range(3)]
        )
        self.add(funnel_drops)
        self.cam_move(
            zoom=1.34,
            center=[-4.68, 0.12, 0],
            anims=[
                FadeOut(beat1a_all, shift=UP * 0.10),
                FadeIn(raw_lbl),
                LaggedStart(*[FadeIn(rd, shift=DOWN * 0.18) for rd in raw_docs], lag_ratio=0.12),
                FadeIn(refinery_funnel, shift=DOWN * 0.08),
                *[
                    Succession(
                        Wait(0.35 + k * 0.22),
                        MoveAlongPath(funnel_drops[k], Line([-5.04, 0.12, 0], [-5.04, -0.45, 0]), run_time=0.65),
                    )
                    for k in range(3)
                ],
                FadeIn(VGroup(ledger_frame, db_ic, ledger_hdr, ledger_sub)),
                LaggedStart(*[FadeIn(lc, scale=0.3) for lc in ledger_cells], lag_ratio=0.05),
            ],
            rt=1.60,
        )
        self.remove(beat1a_all, funnel_drops, *funnel_drops)
        self.wait(2.10)

        # 규칙 A: 본부 화면으로 초점이 이동하는 동안 왼쪽 정제 열(라벨, 깔때기, 시트 박스)이 좌측 경계 안에 남도록 중심을 정함
        self.cam_move(
            zoom=1.34,
            center=[-2.04, 0.04, 0],
            anims=[
                GrowArrow(feed_to_dash),
                FadeIn(VGroup(dash_frame, dash_title, c_age, c_sex, c_tabs, dash_foot)),
                FadeIn(c_uw, scale=1.22),
                FadeIn(VGroup(w1_box, w1_h)),
                FadeIn(w1_g_open, shift=UP * 0.12),
                FadeIn(w1_g_shut, shift=DOWN * 0.10),
                FadeIn(VGroup(w2_box, w2_h, w2_pg)),
                LaggedStart(*[FadeIn(hc, scale=0.4) for hc in hm_cells], lag_ratio=0.05),
                FadeIn(VGroup(w3_box, w3_h, w3_ax, w3_cap)),
                GrowFromEdge(w3_b1, DOWN),
                GrowFromEdge(w3_b2, DOWN),
            ],
            rt=1.80,
        )
        self.wait(2.40)

        print_laser = Line([3.02, 1.96, 0], [6.26, 1.96, 0], color=C_GOLD, stroke_width=4.0).set_z_index(12)
        self.add(print_laser)
        # 규칙 A: A4 장표로 초점이 이동하는 동안 본부 화면(제목 pill, 인수기준 비교, 나이 칩)이 좌측 경계에서 잘리지 않도록 중심과 배율을 정함
        self.cam_move(
            zoom=1.36,
            center=[1.46, 0.04, 0],
            anims=[
                feed_to_dash.animate.set_opacity(0.0),
                GrowArrow(bridge_to_a4),
                FadeIn(bridge_lbl, scale=0.88),
                FadeIn(a4_srv_grp[:7]),
                print_laser.animate.move_to([4.64, -1.90, 0]),
                LaggedStart(*[FadeIn(ab, shift=DOWN * 0.08) for ab in a4_srv_grp[7]], lag_ratio=0.15),
                FadeIn(a4_srv_grp[8:]),
            ],
            rt=1.70,
        )
        self.remove(print_laser)
        self.wait(2.10)

        self.reset_cam_2d(
            anims=[
                feed_to_dash.animate.set_opacity(1.0),
                FadeIn(srv_top_pill, shift=DOWN * 0.08),
                FadeIn(scope_foot, shift=UP * 0.08),
            ],
            rt=1.20,
        )

        ch1_stage = VGroup(srv_top_pill, left_refinery, feed_to_dash, hq_dash_grp, bridge_to_a4, bridge_lbl, a4_srv_grp, scope_foot)
        self.check_bounds(ch1_stage, "CH B SERVICE INFOGRAPHIC")
        self.wait(4.80)

        # ===================================================================
        # 2장: 제출 데모 상단 통합 조건 바 및 6개 분석 탭 아키텍처
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch1_stage,
            hl,
            hr,
            hb,
            2,
            f"구현한 분석 화면 ({num(c4_cnt)}개 탭): 상단 조건 제어 바와 탭별 핵심 기능",
            f"상단 제어 바에서 조건({num(ref_age)}세 {ref_sex_ko}, {base_var_name})과 비교 {TERM['peer']}를 선택하면 {num(c4_cnt)}개 탭이 한 화면에서 연동됩니다",
        )

        # 상단 통합 조건, 비교 타사 제어 바 (부분 줌 동안에도 제목 바 아래에 고정 유지)
        tb_bg = RoundedRectangle(
            corner_radius=0.09,
            width=12.52,
            height=0.68,
            fill_color=C_PANEL_HI,
            fill_opacity=0.98,
            stroke_color=C_GOLD,
            stroke_width=2.0,
        ).move_to([0.0, 2.52, 0]).set_z_index(24)
        tb_c0 = pill(f"{SCREEN_TITLE} 제어 바", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.2, px=0.13, py=0.05, z=25)
        tb_c1 = pill(f"조건: {num(ref_age)}세 {ref_sex_ko} | {base_var_name}", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=13.0, px=0.12, py=0.05, z=25)
        tb_c2 = pill(f"비교 {TERM['peer']}: {epost_name} 포함 {num(site_org_cnt)}개사", fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=13.0, px=0.12, py=0.05, z=25)
        tb_c3 = pill("단일 뷰포트 탭 전환 ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=13.0, px=0.12, py=0.05, z=25)
        tb_chips = fit(VGroup(tb_c0, tb_c1, tb_c2, tb_c3).arrange(RIGHT, buff=0.22), max_w=12.16).move_to(tb_bg)
        toolbar = VGroup(tb_bg, tb_chips)
        self.add_fixed_in_frame_mobjects(toolbar)
        self.remove(toolbar)

        # 상단 제어 바에서 3열 x 2행 탭 카드로 내려가는 병렬 버스 배선
        bus_trunk = VGroup(
            Line([0.0, 2.18, 0], [0.0, 2.05, 0], color=C_GOLD, stroke_width=2.4).set_z_index(5),
            Dot([0.0, 2.05, 0], radius=0.045, color=C_GOLD).set_z_index(6),
        )
        bus_r1_left_arm = VGroup(
            Line([0.0, 2.05, 0], [-4.18, 2.05, 0], color=C_CYAN, stroke_width=2.0).set_z_index(5),
            arrow_2d([-4.18, 2.05, 0], [-4.18, 1.92, 0], color=C_CYAN, sw=2.0, tip=0.08, z=6),
        )
        drop_2 = arrow_2d([0.0, 2.05, 0], [0.0, 1.92, 0], color=C_VIOLET, sw=2.0, tip=0.08, z=6)
        bus_r1_left = VGroup(bus_r1_left_arm, drop_2)
        bus_r1_right = VGroup(
            Line([0.0, 2.05, 0], [4.18, 2.05, 0], color=C_AMBER, stroke_width=2.0).set_z_index(5),
            arrow_2d([4.18, 2.05, 0], [4.18, 1.92, 0], color=C_AMBER, sw=2.0, tip=0.08, z=6),
        )
        bus_risers = VGroup(
            Line([-2.09, 2.05, 0], [-2.09, -0.35, 0], color=C_SLATE, stroke_width=1.8).set_z_index(4),
            Line([2.09, 2.05, 0], [2.09, -0.35, 0], color=C_SLATE, stroke_width=1.8).set_z_index(4),
            Dot([-2.09, 2.05, 0], radius=0.040, color=C_CYAN).set_z_index(6),
            Dot([2.09, 2.05, 0], radius=0.040, color=C_AMBER).set_z_index(6),
            Dot([-2.09, -0.35, 0], radius=0.040, color=C_MINT).set_z_index(6),
            Dot([2.09, -0.35, 0], radius=0.040, color=C_GOLD).set_z_index(6),
        )
        bus_r2_left_arm = VGroup(
            Line([-2.09, -0.35, 0], [-4.18, -0.35, 0], color=C_MINT, stroke_width=2.0).set_z_index(5),
            Line([-2.09, -0.35, 0], [0.0, -0.35, 0], color=C_GOLD, stroke_width=2.2).set_z_index(5),
            arrow_2d([-4.18, -0.35, 0], [-4.18, -0.50, 0], color=C_MINT, sw=2.0, tip=0.08, z=6),
        )
        drop_5 = arrow_2d([0.0, -0.35, 0], [0.0, -0.50, 0], color=C_GOLD, sw=2.2, tip=0.08, z=6)
        bus_r2_left = VGroup(bus_r2_left_arm, drop_5)
        bus_r2_right = VGroup(
            Line([0.0, -0.35, 0], [4.18, -0.35, 0], color=C_CYAN, stroke_width=2.0).set_z_index(5),
            arrow_2d([4.18, -0.35, 0], [4.18, -0.50, 0], color=C_CYAN, sw=2.0, tip=0.08, z=6),
        )
        bus_all = VGroup(bus_trunk, bus_r1_left, bus_r1_right, bus_risers, bus_r2_left, bus_r2_right)

        def make_tab_card(
            cx: float,
            cy: float,
            col: str,
            ic_nm: str,
            tab_no: str,
            title_s: str,
            mini_viz: Mobject,
            mid_s: str,
            bot_s: str,
            highlight: bool = False,
        ) -> VGroup:
            frame = RoundedRectangle(
                corner_radius=0.09,
                width=4.00,
                height=2.12,
                fill_color="#1A180E" if highlight else C_PANEL,
                fill_opacity=0.97,
                stroke_color=col,
                stroke_width=3.0 if highlight else 2.1,
            ).move_to([cx, cy, 0]).set_z_index(4)
            dark_fg = col in (C_GOLD, C_MINT, C_CYAN, C_AMBER)
            ic_m = svg_icon(ic_nm, size=0.40, col=col, accent=C_GOLD, z=8)
            no_pill = pill(tab_no, fg=C_DARK_INK if dark_fg else C_WHITE, bg=col, border=WHITE, size=13.0, px=0.09, py=0.03, z=7)
            hdr = fit(
                VGroup(ic_m, no_pill, txt(title_s, size=14.6, color=col, bold=True, z=7)).arrange(RIGHT, buff=0.09),
                max_w=3.76,
            ).move_to([cx, cy + 0.72, 0])
            div = Line([cx - 1.82, cy + 0.41, 0], [cx + 1.82, cy + 0.41, 0], color=col, stroke_width=1.2, stroke_opacity=0.50).set_z_index(5)
            mid_pill = pill(mid_s, fg=C_WHITE, bg=C_BG_SUB, border=col, size=13.2, px=0.10, py=0.045, z=7)
            mid_row = fit(VGroup(mini_viz, mid_pill).arrange(RIGHT, buff=0.12), max_w=3.76).move_to([cx, cy - 0.04, 0]).set_z_index(7)
            bot_t = fit(
                txt(bot_s, size=12.8, color=C_GOLD if highlight else C_INK_0, bold=True, z=7),
                max_w=3.76,
            ).move_to([cx, cy - 0.68, 0])
            return VGroup(frame, hdr, div, mid_row, bot_t)

        # 탭 ① 전체 요약: 5개 미니 가로 막대 + 5대 분석 영역 기준축 요약
        t1_bars = VGroup(
            *[
                RoundedRectangle(
                    corner_radius=0.02,
                    width=bw,
                    height=0.065,
                    fill_color=bc,
                    fill_opacity=0.94,
                    stroke_width=0,
                ).move_to([bw / 2, -idx * 0.105, 0])
                for idx, (bw, bc) in enumerate(
                    [(0.52, C_CYAN), (0.40, C_GOLD), (0.46, C_MINT), (0.30, C_VIOLET), (0.36, C_AMBER)]
                )
            ]
        ).set_z_index(7)
        tab_1 = make_tab_card(
            -4.18,
            0.86,
            C_CYAN,
            "hq_console",
            "탭 ①",
            t_names[0],
            t1_bars,
            f"{num(n_ins_cats)}대 분석 영역 기준축 요약",
            "핵심 결론 문장 및 요약표 확인",
        )

        # 탭 ② 고객군과 시장: 미니 링/도넛 차트 + 48개 고객군 가입 가능 링 차트
        t2_ring = VGroup(
            Circle(radius=0.23, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_SLATE, stroke_width=3.6),
            Arc(radius=0.23, start_angle=0.2, angle=2.8, color=C_MINT, stroke_width=4.4),
            Arc(radius=0.23, start_angle=3.1, angle=1.7, color=C_GOLD, stroke_width=4.4),
            Arc(radius=0.23, start_angle=4.9, angle=1.1, color=C_VIOLET, stroke_width=4.4),
            Dot(ORIGIN, radius=0.045, color=C_VIOLET),
        ).set_z_index(7)
        tab_2 = make_tab_card(
            0.0,
            0.86,
            C_VIOLET,
            "search_globe",
            "탭 ②",
            t_names[1],
            t2_ring,
            f"{num(seg_cnt)}개 고객군 가입 가능 링 차트",
            f"개정 변경 {num(rev_chg_total)}건, {TERM['trend']} {num(mnews_cnt)}건",
        )

        # 탭 ③ 인수기준 비교: 통과 단계 막대 기호 + 고지항목 통과 단계, 한도 4,000만 원
        t3_steps = VGroup(
            RoundedRectangle(corner_radius=0.03, width=0.46, height=0.14, fill_color=C_MINT, fill_opacity=0.90, stroke_color=WHITE, stroke_width=0.9).move_to([0, 0.12, 0]),
            RoundedRectangle(corner_radius=0.03, width=0.36, height=0.14, fill_color=C_AMBER, fill_opacity=0.92, stroke_color=WHITE, stroke_width=0.9).move_to([-0.05, -0.10, 0]),
        ).set_z_index(7)
        tab_3 = make_tab_card(
            4.18,
            0.86,
            C_AMBER,
            "shield_check",
            "탭 ③",
            t_names[2],
            t3_steps,
            f"{TERM['disc_item']} 통과 단계, 한도 {num(main_lim)}만 원",
            f"목적별 특약 구성, {TERM['rider_cond']} {num(ep_comb)}건",
        )

        # 탭 ④ 담보 비교: 고정 헤더 미니 비교표 격자 + 표준담보 86개, 공통 비교 20건
        t4_hdr = RoundedRectangle(corner_radius=0.02, width=0.56, height=0.10, fill_color=C_MINT, fill_opacity=0.92, stroke_width=0)
        t4_grid = VGroup(
            *[
                RoundedRectangle(corner_radius=0.02, width=0.25, height=0.14, fill_color=hc, fill_opacity=0.90, stroke_width=0)
                for hc in (C_GOLD, C_CYAN, C_MINT, C_CORAL)
            ]
        ).arrange_in_grid(rows=2, cols=2, buff=0.04)
        t4_tbl = VGroup(t4_hdr, t4_grid).arrange(DOWN, buff=0.04).set_z_index(7)
        tab_4 = make_tab_card(
            -4.18,
            -1.56,
            C_MINT,
            "book_dict",
            "탭 ④",
            t_names[3],
            t4_tbl,
            f"표준담보 {num(cov_in_use)}개, 공통 비교 {num(cmp_pairs)}건",
            f"고정 헤더 비교표 복사, {TERM['review_wait']} {num(pend_site)}건 분리",
        )

        # 탭 ⑤ 영업 인사이트 (금색 강조 테두리): 미니 A4 시트 + 5분류 35건 도출
        t5_sheet = make_doc_icon(w=0.38, h=0.46, col=C_GOLD, fill="#221D0E", z=7)
        tab_5 = make_tab_card(
            0.0,
            -1.56,
            C_GOLD,
            "brief_sheet",
            "탭 ⑤",
            t_names[4],
            t5_sheet,
            f"{num(n_ins_cats)}분류 {num(ins_cnt)}건 도출, 원문 쪽수 표시",
            f"우측 패널 A4 {TERM['script_doc']} 인쇄, 복사 ✓",
            highlight=True,
        )

        # 탭 ⑥ 관계 그래프: 미니 3노드 삼각 연결 + 노드 9,881개, 엣지 14,349개 탐색
        g_p0, g_p1, g_p2 = [0.0, 0.22, 0], [-0.22, -0.16, 0], [0.22, -0.16, 0]
        t6_graph = VGroup(
            Line(g_p0, g_p1, color=C_CYAN, stroke_width=2.0),
            Line(g_p0, g_p2, color=C_GOLD, stroke_width=2.0),
            Line(g_p1, g_p2, color=C_MINT, stroke_width=2.0),
            Dot(g_p0, radius=0.065, color=C_GOLD),
            Dot(g_p1, radius=0.065, color=C_CYAN),
            Dot(g_p2, radius=0.065, color=C_MINT),
        ).set_z_index(7)
        tab_6 = make_tab_card(
            4.18,
            -1.56,
            C_CYAN,
            "git_lineage",
            "탭 ⑥",
            t_names[5],
            t6_graph,
            f"노드 {num(g_cnts['nodes'])}개, 엣지 {num(g_cnts['edges'])}개 탐색",
            "담보 연결, 종형 구성, 동향 뷰",
        )

        # Beat 2A: 상단 조건 도구줄 등장 및 조건, 타사 선택 강조 (3.35s)
        self.play(FadeIn(toolbar, shift=DOWN * 0.08), Create(bus_trunk), run_time=1.20)
        self.play(
            Circumscribe(tb_c1, color=C_CYAN, stroke_width=2.4, buff=0.04),
            Circumscribe(tb_c2, color=C_GOLD, stroke_width=2.4, buff=0.04),
            run_time=0.85,
        )
        self.wait(1.30)

        # Beat 2B: 상단 행 좌, 중(탭 ① 전체 요약, 탭 ② 고객군과 시장) 줌 시연 (3.40s)
        self.cam_move(
            zoom=1.38,
            center=[-2.09, 1.18, 0],
            anims=[
                Create(bus_r1_left),
                FadeIn(tab_1, shift=UP * 0.10),
                FadeIn(tab_2, shift=UP * 0.10),
            ],
            rt=1.30,
        )
        self.wait(2.10)

        # Beat 2C: 상단 행 중, 우(탭 ③ 인수기준 비교) 줌 시연 - 규칙 A로 좌측 탭 ① 일시 FadeOut (3.20s)
        self.cam_move(
            zoom=1.38,
            center=[2.09, 1.18, 0],
            anims=[
                FadeOut(VGroup(tab_1, bus_r1_left_arm), shift=LEFT * 0.10),
                Create(bus_r1_right),
                FadeIn(tab_3, shift=UP * 0.10),
            ],
            rt=1.20,
        )
        self.wait(2.00)

        hb = self.update_subtitle(
            hb,
            f"{t_names[0]}부터 {t_names[4]}(A4 {TERM['script_doc']}), {t_names[5]}까지 공시 근거와 함께 확인합니다",
        )

        # Beat 2D: 하단 행 좌, 중(탭 ④ 담보 비교, 탭 ⑤ 영업 인사이트) 줌 시연 - 규칙 A로 상단 행 일시 FadeOut (3.65s)
        self.cam_move(
            zoom=1.38,
            center=[-2.09, -1.24, 0],
            anims=[
                FadeOut(VGroup(tab_2, tab_3, bus_trunk, drop_2, bus_r1_right), shift=UP * 0.10),
                Create(bus_r2_left),
                FadeIn(tab_4, shift=UP * 0.10),
                FadeIn(tab_5, shift=UP * 0.10),
            ],
            rt=1.35,
        )
        self.wait(2.30)

        # Beat 2E: 하단 행 중, 우(탭 ⑥ 관계 그래프) 줌 시연 - 규칙 A로 좌측 탭 ④ 일시 FadeOut (3.55s)
        self.cam_move(
            zoom=1.38,
            center=[2.09, -1.24, 0],
            anims=[
                FadeOut(VGroup(tab_4, bus_r2_left_arm), shift=LEFT * 0.10),
                Create(bus_r2_right),
                FadeIn(tab_6, shift=UP * 0.10),
            ],
            rt=1.25,
        )
        self.wait(2.30)

        # Beat 2F: 전체 6개 탭 통합 뷰포트 복원 및 조건 연동 펄스 시연 (9.07s + fade_out 0.60s)
        self.reset_cam_2d(
            anims=[
                FadeIn(VGroup(tab_1, tab_2, tab_3, tab_4, bus_trunk, bus_r1_left_arm, drop_2, bus_r1_right, bus_risers, bus_r2_left_arm), shift=DOWN * 0.06),
            ],
            rt=1.20,
        )

        pulse_paths = [
            (Line([0.0, 2.05, 0], [-4.18, 2.05, 0]), C_CYAN),
            (Line([0.0, 2.05, 0], [4.18, 2.05, 0]), C_AMBER),
            (Line([-2.09, -0.35, 0], [-4.18, -0.35, 0]), C_MINT),
            (Line([0.0, -0.35, 0], [4.18, -0.35, 0]), C_CYAN),
        ]
        bus_pulses = VGroup(*[glow_dot(lp.get_start(), color=lc, r=0.060, z=14) for lp, lc in pulse_paths])
        self.add(bus_pulses)
        self.play(
            *[MoveAlongPath(bus_pulses[k], pulse_paths[k][0]) for k in range(len(pulse_paths))],
            Circumscribe(tab_5[0], color=C_GOLD, stroke_width=2.8, buff=0.04),
            run_time=1.25,
        )
        self.remove(bus_pulses, *bus_pulses)

        tabs_6 = VGroup(tab_1, tab_2, tab_3, tab_4, tab_5, tab_6)
        ch2_world = VGroup(bus_all, tabs_6)
        self.check_bounds(toolbar, "MAIN TOOLBAR")
        self.check_bounds(ch2_world, "TAB ARCHITECTURE")
        self.wait(6.62)

        ch2_stage = VGroup(toolbar, ch2_world)
        self.fade_out_part(ch2_stage, hl, hr, hb)
        self.remove_fixed_in_frame_mobjects(toolbar)
        self.remove(toolbar)
