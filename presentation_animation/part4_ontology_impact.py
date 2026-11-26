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
    fact,
    fit,
    floor_grid_3d,
    glass_plane_3d,
    glow_dot,
    label_ko,
    make_domain_glyph,
    num,
    pillar_3d,
    pill,
    set_3d_tier,
    txt,
)
from infographics import make_dark_a4_sheet, svg_icon


class Part4OntologyImpactScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        org_names = fact("org_names")
        op_cost = fact("operating_cost_won")
        sheet_tabs = fact("sheet_tab_count")
        br_problems = fact("site_browser_check_problems")
        base_var_name = fact("default_base_variant", "name")
        peer0_name = fact("peer_held_coverage", 0, "name")

        dict_init = fact("dictionary_initial_size")
        dict_add1 = fact("dictionary_first_expansion_added")
        dict_exp2 = fact("dictionary_second_expansion")
        cov_rows = fact("standard_coverage_rows")
        cov_use = fact("standard_coverage_in_use")
        hw_pend_b = fact("hanwha_pending_before_rerun")
        hw_pend_a = fact("hanwha_pending_after_rerun")
        hw_pend_now = fact("mapping_status_by_org", "HANWHALIFE", "대기")
        prem_rows = fact("premium_example_rows")
        dis_rows = fact("benefit_disease_code_rows")

        rel_cnt = fact("coverage_relation_count")
        rel_by_k = fact("coverage_relations_by_kind")
        rel_kinds_str = ", ".join(rel_by_k.keys())
        tr_stages = fact("treatment_stages")
        n_tr_stages = len(tr_stages)

        site_org_cnt = fact("site_org_count")
        var_cnt_site = fact("variant_count_site")
        rider_cnt_site = fact("rider_count_site")
        ben_cnt_site = fact("benefit_count_site")
        news_cnt = fact("market_news_count")
        no_map_cnt = fact("benefits_without_mapping")
        ms_site = fact("mapping_status_site")

        rev_old_no = fact("example_targeted_anticancer", "revisions", 0, "revision_no")
        rev_new = fact("example_targeted_anticancer", "revisions", -1)
        rev_new_no = rev_new["revision_no"]
        basis_mw = rev_new["basis_manwon"]
        pay_new_mw = rev_new["pay_manwon"]

        target_total = sum(fact("comparison_target_counts").values())
        prod_org_cnt = fact("product_org_count")
        inh_rows = fact("id_inherit_simulated_rows")
        surv_orgs = fact("dictionary_expansion_survey_org_count")
        add_rule = fact("dictionary_addition_rule")
        std_names = fact("standard_coverage_names")

        # ===================================================================
        # 7장: 온톨로지와 단독 화면 구조
        # ===================================================================
        hl, hr, hb = self.make_hud(
            7,
            f"온톨로지와 단독 화면: 명칭 불일치와 {TERM['map_wait']} 해결",
            f"회사별 특약명 불일치, {TERM['map_wait']} 행, 통합과 분리 구조 차이를 해결하고 보험료 비교는 차기 과제로 분리했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 7A: 상단 배포 규격 텔레메트리 바 + 3열 스키마 충돌 및 병목 진단 워크벤치
        # -------------------------------------------------------------------
        spec_bar_7 = RoundedRectangle(
            corner_radius=0.08,
            width=12.64,
            height=0.70,
            fill_color=C_PANEL_HI,
            fill_opacity=0.96,
            stroke_color=C_GOLD_DEEP,
            stroke_width=1.8,
        ).move_to([0.0, 2.72, 0]).set_z_index(24)
        spec_hdr_7 = pill(f"{TERM['master']}와 배포 조건", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.0, px=0.12, py=0.05, z=25)
        sp_chip_1 = VGroup(
            svg_icon("database_master", size=0.38, col=C_CYAN, accent=C_GOLD, z=25),
            txt(f"{TERM['sheet_master']} {num(sheet_tabs)}탭", size=12.8, color=C_CYAN, bold=True, z=25),
        ).arrange(RIGHT, buff=0.07)
        sp_chip_2 = VGroup(
            svg_icon("hq_console", size=0.38, col=C_MINT, accent=C_GOLD, z=25),
            txt(f"{TERM['snapshot']} 내장 단일 HTML (점검 오류, 외부 요청 {num(br_problems)}건)", size=12.8, color=C_MINT, bold=True, z=25),
        ).arrange(RIGHT, buff=0.07)
        sp_chip_3 = VGroup(
            svg_icon("shield_check", size=0.38, col=C_GOLD, accent=C_MINT, z=25),
            txt(f"운영 비용 {num(op_cost)}원(무료 설계)", size=12.8, color=C_GOLD, bold=True, z=25),
        ).arrange(RIGHT, buff=0.07)
        spec_items_7 = fit(VGroup(spec_hdr_7, sp_chip_1, sp_chip_2, sp_chip_3).arrange(RIGHT, buff=0.14), max_w=12.50).move_to(spec_bar_7)
        top_spec_7 = VGroup(spec_bar_7, spec_items_7)
        # 규칙 A: 배포 규격 바는 카메라와 함께 움직이지 않는 HUD 레이어에 두고, 열 단위 줌에서 열 머리보다 위(제목 바 아래)에 남긴다.
        self.add_fixed_in_frame_mobjects(top_spec_7)
        self.remove(top_spec_7)

        def make_mini_badge_2l(
            l1: str,
            l2: str,
            fg1: str,
            fg2: str,
            bg_c: str,
            bd_c: str,
            s1: float = 13.0,
            s2: float = 12.8,
            px: float = 0.12,
            py: float = 0.06,
            z: int = 7,
        ) -> VGroup:
            tg = VGroup(
                txt(l1, size=s1, color=fg1, bold=True, z=z + 1),
                txt(l2, size=s2, color=fg2, bold=True, z=z + 1),
            ).arrange(DOWN, buff=0.05)
            bx = RoundedRectangle(
                corner_radius=0.08,
                width=tg.width + px * 2,
                height=tg.height + py * 2,
                fill_color=bg_c,
                fill_opacity=0.97,
                stroke_color=bd_c,
                stroke_width=1.6,
            ).set_z_index(z)
            tg.move_to(bx)
            g = VGroup(bx, tg)
            g.set_z_index(z, family=False)
            return g

        def make_diag_col_7(cx: float, w_c: float, col: str, ic_name: str, title_s: str) -> tuple[RoundedRectangle, VGroup]:
            frame = RoundedRectangle(
                corner_radius=0.09,
                width=w_c,
                height=3.98,
                fill_color=C_PANEL,
                fill_opacity=0.96,
                stroke_color=col,
                stroke_width=2.2,
            ).move_to([cx, -0.44, 0]).set_z_index(4)
            ic = svg_icon(ic_name, size=0.40, col=col, accent=C_WHITE, z=7)
            th = fit(txt(title_s, size=14.2, color=col, bold=True, z=7), max_w=w_c - 0.62)
            hdr = VGroup(ic, th).arrange(RIGHT, buff=0.08).move_to([cx, 1.16, 0])
            rule = Line([cx - w_c / 2 + 0.16, 0.80, 0], [cx + w_c / 2 - 0.16, 0.80, 0], color=col, stroke_width=1.2, stroke_opacity=0.55).set_z_index(5)
            return frame, VGroup(hdr, rule)

        # Col 1 (x = -4.16): 종형명, 지급방식, 통합 대 분리 구조 상이
        c7_f1, c7_h1 = make_diag_col_7(-4.16, 3.96, C_AMBER, "git_lineage", "① 명칭, 지급방식, 구조 상이")
        peer0_p1, peer0_p2 = peer0_name.split(" ", 1) if " " in peer0_name else (peer0_name, "")
        m7_l1 = fit(pill(base_var_name, fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=13.0, px=0.10, py=0.06, z=7), max_w=1.74).move_to([-5.16, 0.34, 0])
        m7_r1 = fit(
            make_mini_badge_2l(peer0_p1, peer0_p2, C_GOLD, C_WHITE, C_BG_SUB, C_GOLD, s1=13.0, s2=12.8, px=0.11, py=0.05, z=7),
            max_w=1.78,
        ).move_to([-3.14, 0.34, 0])
        m7_l2 = fit(pill("수술 회당 지급", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=13.0, px=0.10, py=0.05, z=7), max_w=1.74).move_to([-5.16, -0.36, 0])
        m7_r2 = fit(pill("연간 일회 지급", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=13.0, px=0.10, py=0.05, z=7), max_w=1.74).move_to([-3.14, -0.36, 0])
        m7_neqs = VGroup(
            txt("≠", size=16.5, color=C_CORAL, bold=True, z=8).move_to([-4.16, 0.34, 0]),
            txt("≠", size=16.5, color=C_CORAL, bold=True, z=8).move_to([-4.16, -0.36, 0]),
        )
        int_chip = fit(pill(f"{TERM['peer']} 통합특약 ◆", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=13.0, px=0.10, py=0.05, z=7), max_w=1.74).move_to([-5.16, -1.00, 0])
        false_stamp = fit(pill("미보유 오판 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=13.0, px=0.10, py=0.05, z=8), max_w=1.74).move_to([-3.12, -1.00, 0])
        int_arr = arrow_2d(int_chip.get_right() + RIGHT * 0.04, false_stamp.get_left() + LEFT * 0.04, color=C_CORAL, sw=2.2, tip=0.10, z=8)
        c7_cap1 = fit(
            VGroup(
                txt("단순 문자열과 금액 직접 대조 불가능", size=12.8, color=C_INK_0, bold=True, z=7),
                txt(f"{TERM['ours']} 분리특약 누락 위험 발생", size=12.8, color=C_AMBER, bold=True, z=7),
            ).arrange(DOWN, buff=0.06),
            max_w=3.74,
        ).move_to([-4.16, -1.84, 0])
        col7_1_base = VGroup(c7_f1, c7_h1, m7_l1, m7_r1, m7_l2, m7_r2, m7_neqs, int_chip, c7_cap1)
        col7_1_full = VGroup(col7_1_base, int_arr, false_stamp)

        # Col 2 (x = 0.00): 한화생명 매핑 검수 대기 실측 막대 비교
        c7_f2, c7_h2 = make_diag_col_7(0.0, 3.98, C_CORAL, "book_dict", f"② 초기 {num(dict_init)}개 사전과 한화 {TERM['map_wait']}")
        max_pend_rows = hw_pend_b["rows"]
        bar_track_w = 3.58
        pend_specs = [
            (0.40, f"재추출 전 {TERM['review_wait']}: {num(hw_pend_b['rows'])}행 ({num(hw_pend_b['kinds'])}종)", hw_pend_b["rows"], C_CORAL),
            (-0.26, f"재추출 후(초기 {num(dict_init)}개 사전): {num(hw_pend_a)}행", hw_pend_a, C_AMBER),
            (-0.92, f"사전 확장 후 현재({org_names['HANWHALIFE']}): {num(hw_pend_now)}행", hw_pend_now, C_MINT),
        ]
        pend_tracks, pend_fills = VGroup(), VGroup()
        for py, p_lbl, p_val, p_col in pend_specs:
            lbl_m = fit(txt(p_lbl, size=12.8, color=p_col if p_col != C_AMBER else C_INK_0, bold=True, z=7), max_w=3.78).move_to([0.0, py + 0.18, 0])
            trk = RoundedRectangle(
                corner_radius=0.04,
                width=bar_track_w,
                height=0.21,
                fill_color=C_BG_SUB,
                fill_opacity=0.96,
                stroke_color=C_SLATE,
                stroke_width=1.1,
            ).move_to([0.0, py - 0.10, 0]).set_z_index(5)
            fw = max(0.06, (p_val / max_pend_rows) * bar_track_w)
            fl = RoundedRectangle(
                corner_radius=0.04,
                width=fw,
                height=0.21,
                fill_color=p_col,
                fill_opacity=0.94,
                stroke_color=WHITE,
                stroke_width=0.9,
            ).move_to([trk.get_left()[0] + fw / 2, py - 0.10, 0]).set_z_index(6)
            pend_tracks.add(VGroup(lbl_m, trk))
            pend_fills.add(fl)
        c7_cap2 = fit(
            make_mini_badge_2l(
                f"사전 확장 전 {TERM['map_wait']}를",
                "미보유로 오인할 위험 ×",
                C_CORAL,
                C_WHITE,
                C_CORAL_DIM,
                C_CORAL,
                s1=12.8,
                s2=12.8,
                px=0.14,
                py=0.06,
                z=7,
            ),
            max_w=3.76,
        ).move_to([0.0, -1.84, 0])
        col7_2_base = VGroup(c7_f2, c7_h2, pend_tracks, c7_cap2)
        col7_2_full = VGroup(col7_2_base, pend_fills)

        # Col 3 (x = +4.16): 공시 문서 내 특약별 보험료 부재와 추정 배제 원칙
        c7_f3, c7_h3 = make_diag_col_7(4.16, 3.96, C_VIOLET, "doc_text", "③ 공시 문서 내 특약 보험료 부재")
        src_docs_7 = VGroup(
            pill("상품요약서", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=13.2, px=0.13, py=0.06, z=7),
            pill("사업방법서", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=13.2, px=0.13, py=0.06, z=7),
        ).arrange(RIGHT, buff=0.18).move_to([4.16, 0.36, 0])
        src_arr_7 = arrow_2d([4.16, 0.08, 0], [4.16, -0.22, 0], color=C_VIOLET, sw=2.2, tip=0.10, z=7)
        no_prem_box = DashedVMobject(
            RoundedRectangle(corner_radius=0.06, width=3.66, height=0.94, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=2.0).move_to([4.16, -0.74, 0]),
            num_dashes=26,
        ).set_z_index(6)
        no_prem_inner = fit(
            VGroup(
                svg_icon("alert_warn", size=0.38, col=C_CORAL, accent=C_GOLD, tile=False, z=7),
                VGroup(
                    txt(f"특약별 보험료 예시: {TERM['snapshot']} {num(prem_rows)}행", size=13.2, color=C_CORAL, bold=True, z=7),
                    txt("차기 단계 과제로 분리", size=12.8, color=C_AMBER, bold=True, z=7),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.05),
            ).arrange(RIGHT, buff=0.12),
            max_w=3.48,
        ).move_to([4.16, -0.74, 0])
        c7_cap3 = fit(
            pill("원문에 없는 보험료 추정 표시 제외 ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=13.0, px=0.12, py=0.06, z=7),
            max_w=3.76,
        ).move_to([4.16, -1.84, 0])
        col7_3_full = VGroup(c7_f3, c7_h3, src_docs_7, src_arr_7, no_prem_box, no_prem_inner, c7_cap3)

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[FadeIn(top_spec_7, shift=DOWN * 0.10)],
            rt=0.95,
        )

        # Col 1 spotlight -> Col 2 proportional bar growth -> Col 3 blueprint lock -> Full 3-column workbench
        self.cam_move(
            zoom=1.18,
            center=[-2.50, -0.40, 0],
            anims=[FadeIn(col7_1_base, shift=UP * 0.10)],
            rt=1.05,
        )
        self.play(
            m7_l1.animate.shift(RIGHT * 0.08),
            m7_r1.animate.shift(LEFT * 0.08),
            m7_l2.animate.shift(RIGHT * 0.10),
            m7_r2.animate.shift(LEFT * 0.10),
            rate_func=there_and_back,
            run_time=0.60,
        )
        self.play(
            GrowArrow(int_arr),
            FadeIn(false_stamp, scale=1.3),
            Flash(false_stamp.get_center(), color=C_CORAL, line_length=0.22, num_lines=8),
            run_time=0.75,
        )
        self.wait(1.90)

        self.cam_move(
            zoom=1.18,
            center=[0.0, -0.40, 0],
            anims=[FadeIn(col7_2_base, shift=UP * 0.10)],
            rt=1.05,
        )
        self.play(
            LaggedStart(*[GrowFromEdge(fl, LEFT) for fl in pend_fills], lag_ratio=0.16),
            run_time=1.05,
        )
        self.wait(1.90)

        self.cam_move(
            zoom=1.18,
            center=[3.65, -0.40, 0],
            anims=[FadeIn(col7_3_full, shift=UP * 0.10)],
            rt=1.05,
        )
        self.play(Circumscribe(no_prem_box, color=C_CORAL, stroke_width=2.4, buff=0.04), run_time=0.75)
        self.wait(1.60)

        self.reset_cam_2d(rt=0.95)
        beat7a_cols = VGroup(col7_1_full, col7_2_full, col7_3_full)
        beat7a_all = VGroup(top_spec_7, beat7a_cols)
        self.check_bounds(beat7a_all, "CH7A ONTOLOGY DIAGNOSTIC")
        self.wait(2.50)

        # -------------------------------------------------------------------
        # Beat 7B: True 3D 3-Tier Vertical Fly-Through -> Pure 2D Three-Band Diagram
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 원천 사실과 표준 기준 계층 위에 빌드 시 계산한 비교 데이터를 적재하고 화면은 선택한 조건의 값을 표시합니다",
            rt=0.45,
        )

        p3d_x = 1.05
        z_f1, z_f2, z_f3 = -1.00, 0.22, 1.44
        plane_fct_3d = glass_plane_3d(p3d_x, 0.0, z_f1, 4.90, 2.36, C_CYAN, fill_op=0.16, sw=2.2, tier=-6.0)
        plane_std_3d = glass_plane_3d(p3d_x, 0.0, z_f2, 4.90, 2.36, C_GOLD, fill_op=0.16, sw=2.2, tier=-2.0)
        plane_der_3d = glass_plane_3d(p3d_x, 0.0, z_f3, 4.90, 2.36, C_VIOLET, fill_op=0.16, sw=2.2, tier=2.0)

        nodes_3d, edges_floor_3d, shafts_3d, pulses_3d = VGroup(), VGroup(), VGroup(), VGroup()
        shaft_xy = [
            (p3d_x - 1.72, -0.56, C_CYAN),
            (p3d_x - 0.56, 0.54, C_GOLD),
            (p3d_x + 0.56, -0.46, C_MINT),
            (p3d_x + 1.72, 0.50, C_VIOLET),
        ]
        for k in range(len(shaft_xy) - 1):
            x0, y0, _ = shaft_xy[k]
            x1, y1, _ = shaft_xy[k + 1]
            e_f1 = Line([x0, y0, z_f1 + 0.08], [x1, y1, z_f1 + 0.08], color=C_CYAN, stroke_width=1.8, stroke_opacity=0.70)
            e_f2 = Line([x0, y0, z_f2 + 0.08], [x1, y1, z_f2 + 0.08], color=C_GOLD, stroke_width=2.0, stroke_opacity=0.84)
            e_f3 = Line([x0, y0, z_f3 + 0.08], [x1, y1, z_f3 + 0.08], color=C_VIOLET, stroke_width=2.0, stroke_opacity=0.84)
            set_3d_tier(e_f1, -5.0, sub=0, sort_3d=True)
            set_3d_tier(e_f2, -1.0, sub=0, sort_3d=True)
            set_3d_tier(e_f3, 3.0, sub=0, sort_3d=True)
            edges_floor_3d.add(e_f1, e_f2, e_f3)
        for sx, sy, scol in shaft_xy:
            sh_low = DashedLine([sx, sy, z_f1], [sx, sy, z_f2], dash_length=0.10, color=scol, stroke_width=2.2)
            sh_high = DashedLine([sx, sy, z_f2], [sx, sy, z_f3], dash_length=0.10, color=scol, stroke_width=2.2)
            set_3d_tier(sh_low, -3.0, sub=0, sort_3d=True)
            set_3d_tier(sh_high, 1.0, sub=0, sort_3d=True)
            shafts_3d.add(sh_low, sh_high)
            nodes_3d.add(
                pillar_3d(sx, sy, 0.34, 0.34, 0.18, base_z=z_f1, col=C_CYAN, opacity=0.92, stroke_col=WHITE, tier=-5.0),
                pillar_3d(sx, sy, 0.32, 0.32, 0.22, base_z=z_f2, col=C_GOLD, opacity=0.94, stroke_col=WHITE, tier=-1.0).rotate(PI / 4, axis=OUT),
                pillar_3d(sx, sy, 0.36, 0.36, 0.24, base_z=z_f3, col=C_VIOLET, opacity=0.94, stroke_col=WHITE, tier=3.0),
            )
            p_mob = Prism(dimensions=[0.22, 0.22, 0.22], fill_color=WHITE, fill_opacity=1.0, stroke_color=scol, stroke_width=1.6).move_to([sx, sy, z_f1])
            set_3d_tier(p_mob, -3.0, sub=0, sort_3d=True)
            pulses_3d.add(p_mob)

        bb_7b_f1 = fit(
            bb_badge(f"원천 {TERM['snapshot']}: 화면 {num(site_org_cnt)}개사", f"급부 {num(ben_cnt_site)}건", fg=C_CYAN, bg="#060B11", border=C_CYAN, size=15.6, sub_size=14.2, sub_col=C_WHITE),
            max_w=2.86,
        ).move_to([p3d_x + 4.18, 0.32, z_f1 + 0.28])
        bb_7b_f2 = fit(
            bb_badge(f"표준담보 {num(cov_use)}개", f"{rel_kinds_str} 관계 {num(rel_cnt)}건", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=15.6, sub_size=14.2, sub_col=C_DARK_INK),
            max_w=2.86,
        ).move_to([p3d_x + 4.18, 0.32, z_f2 + 0.40])
        bb_7b_f3 = fit(
            bb_badge("빌드 시 비교 연산", f"단독 HTML, A4 {TERM['script_doc']}", fg=WHITE, bg="#261E42", border=C_VIOLET, size=15.6, sub_size=14.2, sub_col=C_MINT),
            max_w=2.86,
        ).move_to([p3d_x + 4.18, 0.32, z_f3 + 0.52])
        bbs_7b = [bb_7b_f1, bb_7b_f2, bb_7b_f3]

        leaders_7b = VGroup()
        for z_fk, bb_m, lcol in [(z_f1, bb_7b_f1, C_CYAN), (z_f2, bb_7b_f2, C_GOLD), (z_f3, bb_7b_f3, C_VIOLET)]:
            ln = Line([p3d_x + 2.45, 0.32, z_fk], bb_m.get_center(), color=lcol, stroke_width=1.8, stroke_opacity=0.88)
            set_3d_tier(ln, 12.0, sub=0, sort_3d=False)
            leaders_7b.add(ln)

        stack_3d_grp = VGroup(plane_fct_3d, plane_std_3d, plane_der_3d, edges_floor_3d, shafts_3d, nodes_3d, leaders_7b)

        def make_hud_tier_card_7b(yc: float, col: str, l1: str, l2: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.08,
                width=4.68,
                height=0.80,
                fill_color=C_PANEL_HI,
                fill_opacity=0.97,
                stroke_color=col,
                stroke_width=1.8,
            ).move_to([-3.98, yc, 0]).set_z_index(25)
            tg = fit(
                VGroup(
                    txt(l1, size=13.4, color=col, bold=True, z=26),
                    txt(l2, size=12.8, color=C_INK_0, bold=True, z=26),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.05),
                max_w=4.44,
            ).move_to(bx)
            return VGroup(bx, tg)

        z_lbl_3d = VGroup(
            make_hud_tier_card_7b(1.52, C_VIOLET, "상단 계층: 비교, 인사이트", "빌드 시 연산해 적재하고 화면이 표시"),
            make_hud_tier_card_7b(0.08, C_GOLD, "중간 계층: 표준 기준", f"표준담보 {num(cov_use)}개, {rel_kinds_str} 관계"),
            make_hud_tier_card_7b(-1.36, C_CYAN, "하단 계층: 원천 사실", f"{TERM['ours']} 포함 화면 {num(site_org_cnt)}개사와 {TERM['trend']} {TERM['snapshot']}"),
        ).set_z_index(25)

        self.register_billboards(*bbs_7b)
        self.add_fixed_in_frame_mobjects(z_lbl_3d)
        self.cam_move(
            phi=58 * DEGREES,
            theta=-60 * DEGREES,
            zoom=0.86,
            center=[0.35, -0.05, 0.08],
            anims=[
                FadeOut(beat7a_cols, shift=UP * 0.10),
                FadeOut(top_spec_7, shift=UP * 0.10),
                FadeIn(stack_3d_grp),
                FadeIn(VGroup(*bbs_7b)),
                FadeIn(z_lbl_3d, shift=RIGHT * 0.12),
            ],
            rt=1.45,
        )
        self.remove_fixed_in_frame_mobjects(top_spec_7)
        self.remove(beat7a_all, beat7a_cols, top_spec_7)
        self.wait(1.60)

        for p in pulses_3d:
            p.add_updater(lambda m: set_3d_tier(m, -3.0 if m.get_center()[2] < z_f2 else (1.0 if m.get_center()[2] < z_f3 - 0.04 else 3.5)))
        self.add(pulses_3d)
        self.cam_move(
            phi=50 * DEGREES,
            theta=-34 * DEGREES,
            zoom=0.84,
            center=[0.42, -0.12, -0.26],
            anims=[*[MoveAlongPath(pulses_3d[k], Line([shaft_xy[k][0], shaft_xy[k][1], z_f1], [shaft_xy[k][0], shaft_xy[k][1], z_f3])) for k in range(len(shaft_xy))]],
            rt=2.20,
        )
        for p in pulses_3d:
            p.clear_updaters()
        self.remove(pulses_3d, *pulses_3d)
        self.wait(2.20)

        def make_layer_band(y_c: float, h_b: float, col: str, fill_c: str, ic_nm: str, title_s: str, sub_s: str) -> tuple[RoundedRectangle, VGroup]:
            band = RoundedRectangle(corner_radius=0.08, width=12.48, height=h_b, fill_color=fill_c, fill_opacity=0.92, stroke_color=col, stroke_width=2.1).move_to([0.0, y_c, 0]).set_z_index(2)
            sep = Line([-2.92, y_c - h_b * 0.38, 0], [-2.92, y_c + h_b * 0.38, 0], color=col, stroke_width=1.6, stroke_opacity=0.70).set_z_index(4)
            ic_m = svg_icon(ic_nm, size=0.42, col=col, accent=C_WHITE, z=7)
            txt_m = VGroup(txt(title_s, size=15.0, color=col, bold=True, z=7), txt(sub_s, size=13.0, color=C_INK_0, bold=True, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
            hdr = fit(VGroup(ic_m, txt_m).arrange(RIGHT, buff=0.10), max_w=3.06).move_to([-4.58, y_c, 0])
            return band, VGroup(sep, hdr)

        b_der, h_der = make_layer_band(1.64, 1.06, C_VIOLET, "#171528", "hq_console", "분석, 인사이트 계층", "빌드 시 연산, 화면 표시")
        d_n1 = pill("동일 심사유형 종형 비교", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=13.4, px=0.13, py=0.07).move_to([-1.42, 1.64, 0])
        d_n2 = pill("대응 특약과 지급조건 비교", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=13.4, px=0.13, py=0.07).move_to([1.62, 1.64, 0])
        d_n4 = pill(f"★ 영업 인사이트와 {TERM['script_doc']}", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.6, px=0.14, py=0.07).move_to([4.66, 1.64, 0])
        layer_der = VGroup(
            b_der, h_der, d_n1, d_n2, d_n4,
            arrow_2d(d_n1.get_right(), d_n2.get_left(), color=C_VIOLET, sw=2.0, tip=0.10, z=6),
            arrow_2d(d_n2.get_right(), d_n4.get_left(), color=C_GOLD, sw=2.0, tip=0.10, z=6),
        )

        b_std, h_std = make_layer_band(0.14, 1.14, C_GOLD, "#1E1B12", "book_dict", "표준 기준 계층", "특약과 심사기준 표준화")
        s_grade = pill("심사유형, 간편고지 등급 체계", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=13.2, px=0.12, py=0.07).move_to([-1.32, 0.14, 0])
        sd1 = Square(side_length=0.22, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.4).rotate(PI / 4).move_to([1.02, 0.36, 0]).set_z_index(7)
        sd2 = Square(side_length=0.20, fill_color=C_MINT, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([1.82, 0.48, 0]).set_z_index(7)
        sd3 = Square(side_length=0.20, fill_color=C_CYAN, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([1.82, 0.04, 0]).set_z_index(7)
        s_dag_grp = VGroup(
            Line(sd1.get_center(), sd2.get_center(), color=C_GOLD, stroke_width=2.2).set_z_index(6),
            Line(sd1.get_center(), sd3.get_center(), color=C_MINT, stroke_width=2.2).set_z_index(6),
            sd1, sd2, sd3,
            fit(txt(f"◆ 표준담보 {num(cov_use)}개 및 {rel_kinds_str} 관계", size=13.2, color=C_GOLD, bold=True, z=7), max_w=3.42).move_to([1.72, -0.24, 0]),
        )
        s_pay = pill(f"지급형태, 치료 {num(n_tr_stages)}단계 분류", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=13.2, px=0.12, py=0.07).move_to([4.72, 0.14, 0])
        layer_std = VGroup(b_std, h_std, s_grade, s_dag_grp, s_pay)

        b_fct, h_fct = make_layer_band(-1.40, 1.18, C_CYAN, "#101B24", "database_master", "원천 사실 계층", f"{TERM['ours']} 포함 {num(site_org_cnt)}개사 {TERM['snapshot']}")
        f_org_s = make_domain_glyph("org", [-2.10, -1.20, 0], col=C_CYAN, z=7)
        f_var_s = make_domain_glyph("variant", [-0.36, -1.20, 0], col=C_CYAN, z=7)
        f_rid_s = make_domain_glyph("rider", [1.40, -1.20, 0], col=C_CYAN, z=7)
        f_ben_s = make_domain_glyph("benefit", [3.22, -1.20, 0], col=C_GOLD, z=7)
        f_nws_s = make_domain_glyph("news", [5.04, -1.20, 0], col=C_VIOLET, z=7)
        layer_fct = VGroup(
            b_fct, h_fct, f_org_s, f_var_s, f_rid_s, f_ben_s, f_nws_s,
            txt(f"화면 {num(site_org_cnt)}개사", size=13.2, color=C_INK_0, bold=True, z=7).move_to([-2.10, -1.68, 0]),
            txt(f"{num(var_cnt_site)}개 상품 종형", size=13.2, color=C_INK_0, bold=True, z=7).move_to([-0.36, -1.68, 0]),
            txt(f"{num(rider_cnt_site)}개 특약", size=13.2, color=C_INK_0, bold=True, z=7).move_to([1.40, -1.68, 0]),
            txt(f"{num(ben_cnt_site)}건 세부 급부", size=13.2, color=C_GOLD, bold=True, z=7).move_to([3.22, -1.68, 0]),
            txt(f"{TERM['trend']} {num(news_cnt)}건", size=13.2, color=C_VIOLET, bold=True, z=7).move_to([5.04, -1.68, 0]),
            arrow_2d(f_org_s.get_right(), f_var_s.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=6),
            arrow_2d(f_var_s.get_right(), f_rid_s.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=6),
            arrow_2d(f_rid_s.get_right(), f_ben_s.get_left(), color=C_GOLD, sw=2.0, tip=0.10, z=6),
            DashedLine(f_org_s.get_top() + UP * 0.04, f_nws_s.get_top() + UP * 0.04, dash_length=0.08, color=C_VIOLET, stroke_width=1.4).set_z_index(5),
        )

        up_coords = [
            ([-0.36, -0.80, 0], [-1.32, -0.42, 0], C_CYAN),
            ([3.22, -0.80, 0], [1.72, -0.42, 0], C_GOLD),
            ([3.22, -0.80, 0], [4.72, -0.42, 0], C_GOLD),
            ([-1.32, 0.72, 0], [-1.42, 1.12, 0], C_VIOLET),
            ([1.72, 0.72, 0], [1.62, 1.12, 0], C_MINT),
            ([4.72, 0.72, 0], [4.66, 1.12, 0], C_GOLD),
        ]
        cross_layer_arrows = VGroup(*[arrow_2d(p0, p1, color=col, sw=2.2, tip=0.12, z=8) for p0, p1, col in up_coords])
        foot_7b = fit(
            pill(
                f"정확성 원칙: 빌드 시 코드가 비교와 문구를 연산하고, 공시에 없는 값(특약 보험료 {num(prem_rows)}행)은 추정 표시 제외 ✓",
                fg=C_MINT,
                bg=C_PANEL_HI,
                border=C_MINT,
                size=13.0,
            ),
            max_w=12.48,
        ).move_to([0.0, -2.58, 0]).set_z_index(9)

        self.reset_cam_2d(
            anims=[
                FadeOut(stack_3d_grp),
                FadeOut(VGroup(*bbs_7b)),
                FadeOut(z_lbl_3d),
                FadeIn(layer_fct, shift=UP * 0.12),
            ],
            rt=1.10,
        )
        self.clear_billboards(*bbs_7b)
        self.remove_fixed_in_frame_mobjects(z_lbl_3d)
        self.remove(stack_3d_grp, z_lbl_3d)

        self.play(
            LaggedStart(*[GrowArrow(va) for va in cross_layer_arrows[:3]], lag_ratio=0.08),
            FadeIn(layer_std, shift=UP * 0.10),
            run_time=0.85,
        )
        self.play(
            LaggedStart(*[GrowArrow(va) for va in cross_layer_arrows[3:]], lag_ratio=0.08),
            FadeIn(layer_der, shift=UP * 0.10),
            FadeIn(foot_7b, shift=UP * 0.08),
            run_time=0.90,
        )
        self.play(Circumscribe(d_n4[0], color=WHITE, stroke_width=2.4, buff=0.04), run_time=0.65)

        beat7b_all = VGroup(layer_fct, layer_std, layer_der, cross_layer_arrows, foot_7b)
        self.check_bounds(beat7b_all, "CH7B THREE LAYERS")
        self.wait(3.20)

        # -------------------------------------------------------------------
        # Beat 7C: True 3D Knowledge-Graph Constellation -> Pure 2D Dictionary Expansion
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"해결 ② 화면 {TERM['review_wait']} {num(ms_site['대기'])}건을 점선으로 분리하고, 표준담보 사전을 {num(dict_init)}행에서 {num(dict_exp2['before'])}행, {num(cov_rows)}행(사용 {num(cov_use)}개)으로 확장했습니다",
            rt=0.45,
        )

        G = nx.Graph()
        n_per_org, n_hubs = 15, 9
        total_v = n_per_org * site_org_cnt + n_hubs
        hub_start = n_per_org * site_org_cnt
        # 표준담보 허브를 다면체 입체 코어로 연결하고 기관별 특약 노드를 구면 궤도에 분산 배치
        for h_i in range(1, n_hubs):
            G.add_edge(hub_start, hub_start + h_i)
            G.add_edge(hub_start + h_i, hub_start + 1 + (h_i % (n_hubs - 1)))
        G.add_edge(hub_start + 1, hub_start + 5)
        G.add_edge(hub_start + 2, hub_start + 6)
        G.add_edge(hub_start + 3, hub_start + 7)
        G.add_edge(hub_start + 4, hub_start + 8)
        for c_idx in range(site_org_cnt):
            base = c_idx * n_per_org
            for k in range(1, 4):
                G.add_edge(base, base + k)
            for k in range(4, n_per_org):
                G.add_edge(base + 1 + ((k - 4) % 3), base + k)
                G.add_edge(base + k, hub_start + ((k * 2 + c_idx * 3) % n_hubs))

        init_pos: dict[int, np.ndarray] = {hub_start: np.array([0.0, 0.0, 0.0])}
        golden_ang = np.pi * (3.0 - np.sqrt(5.0))
        for h_i in range(1, n_hubs):
            u_z = 1.0 - 2.0 * (h_i - 0.5) / (n_hubs - 1)
            r_xy = np.sqrt(max(0.0, 1.0 - u_z * u_z))
            ang_h = golden_ang * h_i * 2.3
            init_pos[hub_start + h_i] = np.array([r_xy * np.cos(ang_h) * 0.55, r_xy * np.sin(ang_h) * 0.55, u_z * 0.52])

        sector_angles = [-2.15, 0.08, 2.18]
        sector_z_bias = [0.26, -0.28, 0.20]
        for c_idx in range(site_org_cnt):
            base = c_idx * n_per_org
            ang0 = sector_angles[c_idx]
            zb = sector_z_bias[c_idx]
            init_pos[base] = np.array([np.cos(ang0) * 0.95, np.sin(ang0) * 0.95, zb])
            for k in range(1, n_per_org):
                sub_a = ang0 + ((k % 5) - 2.0) * 0.36
                sub_z = zb + (((k * 3) % 7) - 3.0) * 0.22
                rad_s = 0.74 + (k % 3) * 0.20
                init_pos[base + k] = np.array([np.cos(sub_a) * rad_s, np.sin(sub_a) * rad_s, sub_z])

        raw_pos = nx.spring_layout(G, dim=3, pos=init_pos, seed=42, k=0.72, iterations=70)
        pts_mat = np.array([raw_pos[i] for i in range(total_v)], dtype=float)
        pts_mat -= pts_mat.mean(axis=0, keepdims=True)

        # 특이값 분해 백색화로 대각선 편평화를 제거하고 공간 전체 축으로 고르게 확산
        _, s_vals, vt_mat = np.linalg.svd(pts_mat, full_matrices=False)
        pts_white = pts_mat @ vt_mat.T @ np.diag(1.0 / (s_vals + 1e-6)) @ vt_mat
        radii_w = np.linalg.norm(pts_white, axis=1, keepdims=True)
        pts_unit = pts_white / (np.percentile(radii_w, 95) + 1e-6)
        norm_u = np.linalg.norm(pts_unit, axis=1, keepdims=True)
        pts_ball = pts_unit * np.where(norm_u > 1.0, (1.0 + 0.06 * np.tanh(norm_u - 1.0)) / norm_u, 1.0)

        pts_ball[hub_start] = np.array([0.0, 0.0, 0.02])
        for h_i in range(1, n_hubs):
            u_z = 1.0 - 2.0 * (h_i - 0.5) / (n_hubs - 1)
            r_xy = np.sqrt(max(0.0, 1.0 - u_z * u_z))
            ang_f = golden_ang * h_i * 2.1 + 0.35
            fib_pt = np.array([r_xy * np.cos(ang_f) * 0.56, r_xy * np.sin(ang_f) * 0.58, u_z * 0.56])
            pts_ball[hub_start + h_i] = 0.28 * pts_ball[hub_start + h_i] + 0.72 * fib_pt

        for i in range(hub_start):
            r_i = float(np.linalg.norm(pts_ball[i]))
            if r_i < 0.64:
                pts_ball[i] = pts_ball[i] / (r_i + 1e-6) * (0.64 + 0.22 * r_i)
            elif i % n_per_org == 0 and r_i > 0.95:
                pts_ball[i] = pts_ball[i] / r_i * 0.95

        pts_ball -= pts_ball.mean(axis=0, keepdims=True)
        ang_w = np.deg2rad(41.0)
        u_horiz = np.array([np.cos(ang_w), np.sin(ang_w), 0.0])
        u_depth = np.array([-np.sin(ang_w), np.cos(ang_w), 0.0])
        u_vert = np.array([0.0, 0.0, 1.0])
        pts_3d = (
            np.outer(pts_ball[:, 0], u_horiz) * 5.60
            + np.outer(pts_ball[:, 1], u_depth) * 3.10
            + np.outer(pts_ball[:, 2], u_vert) * 1.95
        ) * 0.89715 + np.array([-0.25928, -0.22539, -0.07948])
        net_pts = {i: pts_3d[i].copy() for i in range(total_v)}

        radar_bg = VGroup(
            Circle(radius=1.45, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.0, stroke_opacity=0.16).scale([1.65, 0.95, 1.0]),
            Circle(radius=2.22, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.0, stroke_opacity=0.14).scale([1.68, 0.92, 1.0]),
            Circle(radius=1.88, fill_opacity=0.0, stroke_color=C_VIOLET, stroke_width=0.95, stroke_opacity=0.15).scale([1.55, 0.88, 1.0]).rotate(26 * DEGREES, axis=RIGHT).rotate(14 * DEGREES, axis=UP),
            Circle(radius=1.88, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=0.95, stroke_opacity=0.13).scale([1.55, 0.88, 1.0]).rotate(-26 * DEGREES, axis=RIGHT).rotate(-16 * DEGREES, axis=UP),
            Line([-4.15, 0, 0], [4.15, 0, 0], color=C_CYAN, stroke_width=0.8, stroke_opacity=0.13),
            Line([0, -2.05, 0], [0, 2.05, 0], color=C_CYAN, stroke_width=0.8, stroke_opacity=0.13),
            Line([0, 0, -1.32], [0, 0, 1.32], color=C_GOLD, stroke_width=0.9, stroke_opacity=0.16),
        ).set_z_index(1)
        set_3d_tier(radar_bg, -15.0, sub=0, sort_3d=False)

        hub_prisms = VGroup()
        billboard_nodes: list[Mobject] = []
        for i in range(total_v):
            pt = net_pts[i]
            if i >= hub_start:
                v_mob: Mobject = (
                    Prism(dimensions=[0.25, 0.25, 0.25], fill_color=C_GOLD, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.35)
                    .rotate(PI / 4, axis=OUT)
                    .rotate(PI / 5, axis=RIGHT)
                    .move_to(pt)
                )
                hub_prisms.add(v_mob)
            elif i % n_per_org == 0:
                c_col = C_GOLD if i == 0 else (C_CYAN if i == n_per_org else C_VIOLET)
                v_mob = RegularPolygon(n=6, fill_color=c_col, fill_opacity=0.97, stroke_color=WHITE, stroke_width=1.7).scale(0.20).move_to(pt)
                billboard_nodes.append(v_mob)
            else:
                c_col = C_GOLD if i < n_per_org else (C_CYAN if i < 2 * n_per_org else C_VIOLET)
                v_mob = Circle(radius=0.090, fill_color=c_col, fill_opacity=0.92, stroke_color=WHITE, stroke_width=0.9).move_to(pt)
                billboard_nodes.append(v_mob)

        billboard_grp = VGroup(*billboard_nodes)

        bridge_pairs = [(u, v) for u, v in G.edges() if not ((u >= hub_start and v >= hub_start) or (u < hub_start and v < hub_start))]
        n_dashed_bridges = max(5, round(len(bridge_pairs) * (ms_site["대기"] / ben_cnt_site)))
        intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges = VGroup(), VGroup(), VGroup(), VGroup()
        bridge_counter = 0
        for u, v in G.edges():
            if u >= hub_start and v >= hub_start:
                dag_edges.add(Line(net_pts[u], net_pts[v], color=C_GOLD, stroke_width=2.4, stroke_opacity=0.92))
            elif u < hub_start and v < hub_start:
                intra_edges.add(Line(net_pts[u], net_pts[v], color=C_SLATE, stroke_width=1.3, stroke_opacity=0.58))
            else:
                bridge_counter += 1
                if bridge_counter % 7 == 1 and len(waiting_dashed_edges) < n_dashed_bridges:
                    waiting_dashed_edges.add(DashedLine(net_pts[u], net_pts[v], dash_length=0.09, color=C_AMBER, stroke_width=2.2, stroke_opacity=0.96))
                else:
                    confirmed_bridge_edges.add(Line(net_pts[u], net_pts[v], color=C_MINT, stroke_width=1.5, stroke_opacity=0.74))

        build_banner = fit(
            pill(
                f"{TERM['ours']} 포함 화면 {num(site_org_cnt)}개사 급부 {num(ben_cnt_site)}건 매핑(미매핑 급부 {num(no_map_cnt)}건): 자동확정 {num(ms_site['자동확정'])}건, 대상외 {num(ms_site['대상외'])}건, {TERM['review_wait']} {num(ms_site['대기'])}건 (구조 예시 그림)",
                fg=C_GOLD,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=13.0,
            ),
            max_w=12.60,
        ).move_to([0, 2.78, 0]).set_z_index(25)
        build_legend = fit(
            VGroup(
                pill(f"◆ 포함 {num(rel_by_k['포함'])}, 통합 {num(rel_by_k['통합'])} (합계 {num(rel_cnt)}건)", fg=C_GOLD, bg=C_PANEL, border=C_GOLD_DEEP, size=12.8),
                pill(f"●─● 자동확정 {num(ms_site['자동확정'])}건 (대상외 {num(ms_site['대상외'])}건)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=12.8),
                pill(f"●- -● {TERM['review_wait']} {num(ms_site['대기'])}건 (미보유 오판 방지)", fg=C_AMBER, bg=C_PANEL, border=C_AMBER, size=12.8),
            ).arrange(RIGHT, buff=0.14),
            max_w=12.60,
        ).move_to([0, -2.78, 0]).set_z_index(25)

        self.add_fixed_in_frame_mobjects(build_banner, build_legend)
        self.register_billboards(*billboard_nodes)
        set_3d_tier(billboard_grp, 0.0, sub=0, sort_3d=True)

        self.cam_move(
            phi=60 * DEGREES,
            theta=-74 * DEGREES,
            zoom=0.86,
            center=[0.0, 0.0, 0.0],
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
            rt=1.55,
        )
        self.remove(beat7b_all)

        self.cam_move(phi=48 * DEGREES, theta=-24 * DEGREES, zoom=0.86, center=[0.0, 0.0, 0.0], rt=2.60)
        self.wait(1.90)

        all_net_lines = VGroup(intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges)
        bg_cosmos = VGroup(radar_bg, all_net_lines, hub_prisms, billboard_grp)

        z1_card = RoundedRectangle(corner_radius=0.08, width=3.92, height=4.56, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.30, -0.04, 0]).set_z_index(4)
        z1_hdr = fit(
            VGroup(
                svg_icon("git_lineage", size=0.40, col=C_CYAN, accent=C_GOLD, z=7),
                txt("확장 ① 개정 계보와 비교 확대", size=14.2, color=C_CYAN, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.68,
        ).move_to([-4.30, 1.80, 0])
        z1_old = fit(pill(f"직전 개정 ({rev_old_no})", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=13.2, z=7), max_w=3.64).move_to([-4.30, 1.04, 0])
        z1_new = fit(pill(f"현행 개정 ({rev_new_no})", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=13.2, z=7), max_w=3.64).move_to([-4.30, -0.08, 0])
        z1_scope_box = RoundedRectangle(
            corner_radius=0.07,
            width=3.68,
            height=0.64,
            fill_color=C_PANEL_HI,
            fill_opacity=0.97,
            stroke_color=C_CYAN,
            stroke_width=1.6,
        ).move_to([-4.30, -0.84, 0]).set_z_index(6)
        z1_scope_txt = fit(
            VGroup(
                txt(f"{TERM['ours']} 포함 {num(site_org_cnt)}개사 ({TERM['snapshot']} {num(prod_org_cnt)}개사)", size=13.0, color=C_CYAN, bold=True, z=7),
                txt(f"-> 비교 {TERM['peer']} {num(target_total)}개사", size=13.0, color=C_WHITE, bold=True, z=7),
            ).arrange(DOWN, buff=0.05),
            max_w=3.54,
        ).move_to(z1_scope_box)
        z1_scope_badge = VGroup(z1_scope_box, z1_scope_txt)
        z1_foot = fit(
            VGroup(
                txt("타사 선정: 총자산 기사 기준(공식 순위 미확정)", size=12.6, color=C_INK_0, bold=True, z=7),
                txt(f"급부ID {num(inh_rows)}행 승계: 과거 자료 모의 {TERM['test']}", size=12.6, color=C_INK_1, bold=True, z=7),
                txt("(실제 재추출에서는 미확인)", size=12.6, color=C_INK_1, bold=True, z=7),
            ).arrange(DOWN, buff=0.05),
            max_w=3.74,
        ).move_to([-4.30, -1.72, 0])
        exp_left = VGroup(
            z1_card,
            z1_hdr,
            z1_old,
            z1_new,
            arrow_2d(z1_old.get_bottom(), z1_new.get_top(), color=C_GOLD, sw=2.4, tip=0.12, z=7),
            pill("특약계보키 연결", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=12.8, px=0.11, py=0.04, z=8).move_to([-4.30, 0.48, 0]),
            z1_scope_badge,
            z1_foot,
        )

        z2_card = RoundedRectangle(corner_radius=0.08, width=4.36, height=4.56, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_MINT, stroke_width=2.3).move_to([0.0, -0.04, 0]).set_z_index(4)
        z2_t = fit(
            VGroup(
                svg_icon("book_dict", size=0.40, col=C_MINT, accent=C_GOLD, z=7),
                txt(f"확장 ② 표준담보 사전 ({num(dict_init)} -> {num(dict_exp2['before'])} -> {num(cov_rows)}행)", size=14.2, color=C_MINT, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=4.16,
        ).move_to([0.0, 1.80, 0])
        z2_sub = fit(txt(f"{num(surv_orgs)}개사 요약서 급부명 조사 (약관 미대조, 사용 {num(cov_use)}개)", size=12.8, color=C_INK_0, bold=True, z=7), max_w=4.16).move_to([0.0, 1.30, 0])

        hub_centers_4c = [np.array([-1.24, 0.04, 0.0]), np.array([0.0, 0.30, 0.0]), np.array([1.24, 0.04, 0.0])]
        hub_names_4c = [
            next(nm for nm in std_names["수술"] if "뇌·심장질환 수술비" == nm),
            next(nm for nm in std_names["수술"] if "전신마취" in nm),
            next(nm for nm in std_names["입원"] if "인실" in nm),
        ]
        drift_dots, remap_edges = VGroup(), VGroup()
        target_positions_4c: list[np.ndarray] = []
        rng_4c = np.random.default_rng(7)
        for hc in hub_centers_4c:
            for k in range(4):
                ang = math.pi / 4 + k * (math.pi / 2)
                t_pt = hc + np.array([0.46 * math.cos(ang), 0.42 * math.sin(ang), 0.0])
                target_positions_4c.append(t_pt)
                drift_dots.add(Dot(np.array([rng_4c.uniform(-1.65, 1.65), rng_4c.uniform(-0.85, 0.78), 0.0]), radius=0.072, color=C_AMBER).set_z_index(8))
                remap_edges.add(Line(hc, t_pt, color=C_MINT, stroke_width=2.0).set_z_index(6))

        new_hubs_4c, new_hub_lbls = VGroup(), VGroup()
        for h_idx, (hc, h_nm) in enumerate(zip(hub_centers_4c, hub_names_4c)):
            new_hubs_4c.add(Square(side_length=0.26, fill_color=C_MINT if h_idx != 1 else C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.6).rotate(PI / 4).move_to(hc).set_z_index(9))
            new_hub_lbls.add(fit(txt(h_nm, size=13.0, color=C_MINT if h_idx != 1 else C_GOLD, bold=True, z=9), max_w=1.92).move_to(hc + (DOWN * 0.72 if h_idx != 1 else UP * 0.62)))
        ex_diag_note = txt("(사전 수록 담보 연결 예시 그림)", size=12.6, color=C_INK_1, bold=True, z=8).move_to([0.0, -1.14, 0])
        remap_ok = fit(
            pill(f"일차 확장 +{num(dict_add1)}행({num(dict_exp2['before'])}행), 이차 확장 {num(cov_rows)}행 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=13.0, z=9),
            max_w=4.16,
        ).move_to([0.0, -1.68, 0])

        z3_card = RoundedRectangle(corner_radius=0.08, width=3.92, height=4.56, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_VIOLET, stroke_width=2.0).move_to([4.30, -0.04, 0]).set_z_index(4)
        z3_hdr = fit(
            VGroup(
                svg_icon("shield_check", size=0.40, col=C_VIOLET, accent=C_MINT, z=7),
                txt("사전 추가 기준과 차기 과제", size=14.2, color=C_VIOLET, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.68,
        ).move_to([4.30, 1.80, 0])
        z3_rule1 = fit(pill(f"{TERM['ours']} 보유 또는 요약서 {num(add_rule['min_holder_orgs'])}개사 이상 보유", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=13.0, px=0.11, py=0.06, z=7), max_w=3.68).move_to([4.30, 0.92, 0])
        z3_rule2 = fit(pill("기존 표준담보와 비중복 시 사전에 추가", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=13.0, px=0.11, py=0.06, z=7), max_w=3.68).move_to([4.30, 0.04, 0])
        z3_todo = fit(pill(f"차기 과제: {TERM['trend']}과 사전 후보 연결", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=13.0, px=0.11, py=0.06, z=7), max_w=3.68).move_to([4.30, -0.86, 0])
        exp_right = VGroup(
            z3_card,
            z3_hdr,
            z3_rule1,
            z3_rule2,
            z3_todo,
            arrow_2d(z3_rule1.get_bottom(), z3_rule2.get_top(), color=C_GOLD, sw=2.0, tip=0.10, z=6),
            fit(
                VGroup(
                    txt(f"{TERM['trend']}을 사전 후보로", size=12.8, color=C_INK_0, bold=True, z=7),
                    txt("자동 연결하는 기능은 미구현", size=12.8, color=C_INK_0, bold=True, z=7),
                ).arrange(DOWN, buff=0.05),
                max_w=3.68,
            ).move_to([4.30, -1.68, 0]),
        )

        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.32,
            center=[0.0, -0.04, 0],
            anims=[
                FadeOut(bg_cosmos),
                FadeOut(build_banner),
                FadeOut(build_legend),
                FadeIn(VGroup(z2_card, z2_t, z2_sub, drift_dots, ex_diag_note), scale=0.92),
            ],
            rt=1.20,
        )
        self.clear_billboards(*billboard_nodes)
        self.remove_fixed_in_frame_mobjects(build_banner, build_legend)
        self.remove(bg_cosmos, build_banner, build_legend)

        self.play(
            FadeIn(new_hubs_4c, scale=0.25),
            FadeIn(new_hub_lbls),
            *[drift_dots[idx].animate.move_to(target_positions_4c[idx]).set_color(C_GOLD if (idx // 4) == 1 else C_MINT) for idx in range(12)],
            Create(remap_edges, lag_ratio=0.03),
            Flash(hub_centers_4c[0], color=C_MINT, line_length=0.22, num_lines=8),
            Flash(hub_centers_4c[1], color=C_GOLD, line_length=0.26, num_lines=8),
            Flash(hub_centers_4c[2], color=C_MINT, line_length=0.22, num_lines=8),
            FadeIn(remap_ok, shift=UP * 0.08),
            run_time=1.45,
        )
        self.wait(2.30)

        self.reset_cam_2d(
            anims=[FadeIn(exp_left, shift=RIGHT * 0.16), FadeIn(exp_right, shift=LEFT * 0.16)],
            rt=1.20,
        )

        fg_7c = VGroup(exp_left, z2_card, z2_t, z2_sub, drift_dots, new_hubs_4c, new_hub_lbls, remap_edges, ex_diag_note, remap_ok, exp_right)
        self.check_bounds(fg_7c, "CH7C EXPANSION")
        self.wait(3.20)

        # ===================================================================
        # 8장: 지식그래프 담보 분석과 응대 화법
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            fg_7c,
            hl,
            hr,
            hb,
            8,
            f"{rel_kinds_str} 관계 탐색과 실행: 담보 관계망부터 {TERM['script_doc']}까지",
            f"{TERM['peer']}는 통합특약 하나로, {org_names['EPOST']}은 분리특약 둘로 운영할 때 통합 관계로 대응 특약을 탐색합니다",
        )

        # -------------------------------------------------------------------
        # Beat 8A: True 3D Multi-Hop Split-Rider Fly-Through (포함, 통합 입체 분기)
        # -------------------------------------------------------------------
        diag_covs = std_names["진단"]
        nm_bs_diag = next(nm for nm in diag_covs if nm == "뇌·심장질환 진단비")
        nm_bv_diag = next(nm for nm in diag_covs if nm == "뇌혈관질환 진단비")
        nm_st_diag = next(nm for nm in diag_covs if nm == "뇌졸중 진단비")
        nm_hm_diag = next(nm for nm in diag_covs if nm == "뇌출혈 진단비")

        surg_covs = std_names["수술"]
        nm_bs_surg = next(nm for nm in surg_covs if nm == "뇌·심장질환 수술비")
        nm_bv_surg = next(nm for nm in surg_covs if nm == "뇌혈관질환 수술비")
        nm_ht_surg = next(nm for nm in surg_covs if nm == "심장질환 수술비")
        peer_pair_str = ", ".join(org_names[o] for o in fact("site_orgs") if o != "EPOST")

        g8_floor = floor_grid_3d(-4.7, 4.7, -1.30, 1.40, z_val=-0.86, step_x=1.56, step_y=1.35, col=C_CYAN_DIM)

        # Upper 3D Inclusion Chain
        inc_pts = [
            np.array([-3.88, 1.24, 1.02]),
            np.array([-1.20, 1.24, 1.24]),
            np.array([1.36, 1.24, 1.48]),
            np.array([3.84, 1.24, 1.72]),
        ]
        inc_names = [nm_bs_diag, nm_bv_diag, nm_st_diag, nm_hm_diag]
        inc_cols = [C_GOLD, C_CYAN, C_CYAN, C_WHITE]
        inc_nodes_3d, inc_edges_3d = VGroup(), VGroup()
        inc_bbs: list[VGroup] = []
        for idx_i, (ipt, inm, icol) in enumerate(zip(inc_pts, inc_names, inc_cols)):
            inc_nodes_3d.add(
                Prism(dimensions=[0.24, 0.24, 0.24], fill_color=icol, fill_opacity=0.94, stroke_color=WHITE, stroke_width=1.3)
                .rotate(PI / 4, axis=OUT)
                .move_to(ipt)
            )
            inc_bbs.append(
                fit(
                    bb_badge(
                        f"포함: {inm}" if idx_i == 0 else inm,
                        fg=C_DARK_INK if icol in (C_GOLD, C_WHITE) else icol,
                        bg=icol if icol in (C_GOLD, C_WHITE) else "#060B11",
                        border=icol,
                        size=15.4,
                        px=0.14,
                        py=0.07,
                    ),
                    max_w=2.76,
                ).move_to(ipt + OUT * 0.36)
            )
            if idx_i < len(inc_pts) - 1:
                inc_edges_3d.add(Line(inc_pts[idx_i], inc_pts[idx_i + 1], color=C_GOLD if idx_i == 0 else C_CYAN, stroke_width=2.4))

        # Main 3D Integration Bifurcation
        pt_peer = np.array([-4.38, -0.06, -0.04])
        pt_pben = np.array([-2.86, -0.06, 0.00])
        pt_hub = np.array([-1.42, -0.06, 0.04])
        pt_br = np.array([0.74, 0.72, 0.56])
        pt_ht = np.array([0.74, -0.78, -0.34])
        pt_ep1 = np.array([2.94, 0.62, 0.42])
        pt_ep2 = np.array([2.88, -0.82, -0.34])
        pt_epost = np.array([4.48, -0.04, 0.18])

        m_peer = Prism(dimensions=[0.52, 0.42, 0.42], fill_color=C_CYAN, fill_opacity=0.90, stroke_color=WHITE, stroke_width=1.4).move_to(pt_peer)
        m_pben = Prism(dimensions=[0.32, 0.32, 0.32], fill_color=C_CYAN, fill_opacity=0.90, stroke_color=WHITE, stroke_width=1.3).move_to(pt_pben)
        m_hub = Prism(dimensions=[0.44, 0.44, 0.44], fill_color=C_GOLD, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.6).rotate(PI / 4, axis=OUT).rotate(PI / 5, axis=RIGHT).move_to(pt_hub)
        m_br = Prism(dimensions=[0.34, 0.34, 0.34], fill_color=C_MINT, fill_opacity=0.94, stroke_color=WHITE, stroke_width=1.4).rotate(PI / 4, axis=OUT).move_to(pt_br)
        m_ht = Prism(dimensions=[0.34, 0.34, 0.34], fill_color=C_MINT, fill_opacity=0.94, stroke_color=WHITE, stroke_width=1.4).rotate(PI / 4, axis=OUT).move_to(pt_ht)
        m_ep1 = Prism(dimensions=[0.32, 0.32, 0.32], fill_color=C_GOLD, fill_opacity=0.94, stroke_color=WHITE, stroke_width=1.3).move_to(pt_ep1)
        m_ep2 = Prism(dimensions=[0.32, 0.32, 0.32], fill_color=C_GOLD, fill_opacity=0.94, stroke_color=WHITE, stroke_width=1.3).move_to(pt_ep2)
        m_epost = Prism(dimensions=[0.54, 0.44, 0.44], fill_color=C_GOLD, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.6).move_to(pt_epost)

        e8_in1 = Line(pt_peer, pt_pben, color=C_CYAN, stroke_width=2.5)
        e8_in2 = Line(pt_pben, pt_hub, color=C_CYAN, stroke_width=2.5)
        e_hop1_a = Line(pt_hub, pt_br, color=C_SLATE, stroke_width=2.4)
        e_hop1_b = Line(pt_hub, pt_ht, color=C_SLATE, stroke_width=2.4)
        e_hop2_a = Line(pt_br, pt_ep1, color=C_SLATE, stroke_width=2.4)
        e_hop2_b = Line(pt_ht, pt_ep2, color=C_SLATE, stroke_width=2.4)
        e_hop3_a = Line(pt_ep1, pt_epost, color=C_SLATE, stroke_width=2.4)
        e_hop3_b = Line(pt_ep2, pt_epost, color=C_SLATE, stroke_width=2.4)

        bb_peer = fit(
            bb_badge(f"{peer_pair_str}", "통합특약 보유", fg=C_CYAN, bg="#060B11", border=C_CYAN, size=15.4, sub_size=14.0, sub_col=C_WHITE, px=0.14, py=0.07),
            max_w=2.56,
        ).move_to(pt_peer + np.array([-0.18, -0.08, 0.48]))
        bb_hub = fit(
            bb_badge(f"◆ {nm_bs_surg}", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=15.6, px=0.15, py=0.08),
            max_w=2.64,
        ).move_to(pt_hub + np.array([-0.40, 0.12, 0.58]))
        bb_br = fit(
            bb_badge(nm_bv_surg, fg=C_MINT, bg="#060B11", border=C_MINT, size=15.4, px=0.14, py=0.07),
            max_w=2.48,
        ).move_to(pt_br + np.array([-0.04, 0.10, 0.46]))
        bb_ht = fit(
            bb_badge(nm_ht_surg, fg=C_MINT, bg="#060B11", border=C_MINT, size=15.4, px=0.14, py=0.07),
            max_w=2.48,
        ).move_to(pt_ht + np.array([-0.12, -0.06, 0.38]))
        bb_ep1 = fit(
            bb_badge(f"{TERM['ours']} 분리특약①", fg=C_GOLD, bg="#060B11", border=C_GOLD, size=15.2, px=0.13, py=0.06),
            max_w=2.36,
        ).move_to(pt_ep1 + np.array([0.14, 0.04, 0.46]))
        bb_ep2 = fit(
            bb_badge(f"{TERM['ours']} 분리특약②", fg=C_GOLD, bg="#060B11", border=C_GOLD, size=15.2, px=0.13, py=0.06),
            max_w=2.36,
        ).move_to(pt_ep2 + np.array([0.04, -0.10, 0.32]))
        bb_epost = fit(
            bb_badge(f"{TERM['ours']} {rev_new_no}", "분리 보유 확인 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=15.4, sub_size=14.0, sub_col=C_DARK_INK, px=0.14, py=0.07),
            max_w=2.56,
        ).move_to(pt_epost + np.array([0.40, 0.22, 0.68]))

        all_8a_bbs = [*inc_bbs, bb_peer, bb_hub, bb_br, bb_ht, bb_ep1, bb_ep2, bb_epost]
        graph_8a_3d = VGroup(
            g8_floor, inc_nodes_3d, inc_edges_3d,
            m_peer, m_pben, m_hub, m_br, m_ht, m_ep1, m_ep2, m_epost,
            e8_in1, e8_in2, e_hop1_a, e_hop1_b, e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b,
        )

        bad_arc_3d = DashedVMobject(
            CubicBezier(pt_hub, np.array([0.4, -0.86, -0.78]), np.array([2.7, -0.86, -0.78]), pt_epost, color=C_CORAL, stroke_width=3.0),
            num_dashes=24,
        )
        set_3d_tier(bad_arc_3d, -5.0, sub=0, sort_3d=True)
        bad_1hop_lbl = fit(
            pill(f'단순 특약명 비교 시: "{nm_bs_surg} 특약 부재로 미보유" 오판 ×', fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=13.2, z=25),
            max_w=12.60,
        ).move_to([0.0, -2.76, 0])
        rel_cov = fact("relation_covered_coverages")
        hop_badge = fit(
            pill(
                f"포함 {num(rel_by_k['포함'])}건, 통합 {num(rel_by_k['통합'])}건 탐색 ✓: 기준 종형이 {TERM['rel_cov']}로 보장하는 표준담보 {num(rel_cov['count'])}개 (보유 담보 수에는 미포함, 직접 보유 아님)",
                fg=C_DARK_INK,
                bg=C_MINT,
                border=WHITE,
                size=13.0,
                z=25,
            ),
            max_w=12.60,
        ).move_to([0.0, -2.76, 0])

        self.register_billboards(*all_8a_bbs)

        self.cam_move(
            phi=54 * DEGREES,
            theta=-74 * DEGREES,
            zoom=0.94,
            center=[0.0, -0.02, 0.16],
            anims=[
                FadeIn(g8_floor),
                FadeIn(VGroup(inc_nodes_3d, inc_edges_3d)),
                FadeIn(VGroup(m_peer, m_pben, m_hub, m_br, m_ht, m_ep1, m_ep2, m_epost)),
                Create(VGroup(e8_in1, e8_in2, e_hop1_a, e_hop1_b, e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b), lag_ratio=0.04),
                FadeIn(VGroup(*all_8a_bbs)),
            ],
            rt=1.45,
        )
        self.wait(1.40)

        self.add_fixed_in_frame_mobjects(bad_1hop_lbl)
        self.play(Create(bad_arc_3d), FadeIn(bad_1hop_lbl, shift=UP * 0.08), run_time=1.05)
        self.wait(2.00)

        p_up_3d = Prism(dimensions=[0.20, 0.20, 0.20], fill_color=WHITE, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.8).move_to(pt_hub)
        p_dn_3d = Prism(dimensions=[0.20, 0.20, 0.20], fill_color=WHITE, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.8).move_to(pt_hub)
        self.add(p_up_3d, p_dn_3d)

        self.cam_move(
            phi=50 * DEGREES,
            theta=-62 * DEGREES,
            zoom=0.96,
            center=[0.20, -0.02, 0.14],
            anims=[
                FadeOut(bad_arc_3d),
                FadeOut(bad_1hop_lbl),
                MoveAlongPath(p_up_3d, e_hop1_a),
                MoveAlongPath(p_dn_3d, e_hop1_b),
                e_hop1_a.animate.set_stroke(color=C_MINT, width=3.8),
                e_hop1_b.animate.set_stroke(color=C_MINT, width=3.8),
            ],
            rt=1.10,
        )
        self.remove_fixed_in_frame_mobjects(bad_1hop_lbl)
        self.remove(bad_arc_3d, bad_1hop_lbl)

        self.cam_move(
            theta=-54 * DEGREES,
            anims=[
                MoveAlongPath(p_up_3d, e_hop2_a),
                MoveAlongPath(p_dn_3d, e_hop2_b),
                e_hop2_a.animate.set_stroke(color=C_GOLD, width=3.8),
                e_hop2_b.animate.set_stroke(color=C_GOLD, width=3.8),
            ],
            rt=0.95,
        )

        self.add_fixed_in_frame_mobjects(hop_badge)
        self.cam_move(
            phi=46 * DEGREES,
            theta=-46 * DEGREES,
            zoom=0.92,
            center=[0.15, -0.02, 0.14],
            anims=[
                MoveAlongPath(p_up_3d, e_hop3_a),
                MoveAlongPath(p_dn_3d, e_hop3_b),
                e_hop3_a.animate.set_stroke(color=C_GOLD, width=3.8),
                e_hop3_b.animate.set_stroke(color=C_GOLD, width=3.8),
                FadeIn(hop_badge, shift=UP * 0.08),
            ],
            rt=1.15,
        )
        self.remove(p_up_3d, p_dn_3d)
        self.check_bounds(hop_badge, "CH8A HUD")
        self.wait(3.40)

        # -------------------------------------------------------------------
        # Beat 8B: 인수기준 매트릭스 대시보드 + 치료 5단계 타임라인 + 지급액 계산 파이프라인
        # -------------------------------------------------------------------
        seg_rows = fact("segment_map_rows")
        seg_cols = fact("segment_map_columns")
        seg_lbls = fact("segment_map_labels")
        seg_cells_n = fact("segment_map_cell_count")
        seg_open_tog = fact("segment_map_open_together_cells")
        seg_closed = fact("segment_map_ours_closed_cells")
        seg_ours_only = fact("segment_map_ours_only_open_cells")
        seg_gate_only = fact("segment_map_gate_only_cells")

        held_total = fact("held_coverage_count")
        held_by_stage = fact("held_coverage_by_stage")
        max_stage_cnt = max(held_by_stage.values())
        main_lim_mw = fact("reference_main_contract_limit_manwon")
        comb_cnt = fact("combination_constraints_by_org", "EPOST")

        hb = self.update_subtitle(
            hb,
            f"{TERM['seg_status']}({base_var_name}), 치료 {num(n_tr_stages)}단계 보유 담보 막대, {TERM['rider_cond']}과 지급액을 함께 분석합니다",
            rt=0.45,
        )

        pm_frame = RoundedRectangle(
            corner_radius=0.09,
            width=6.52,
            height=5.04,
            fill_color=C_PANEL,
            fill_opacity=0.96,
            stroke_color=C_CYAN,
            stroke_width=2.0,
        ).move_to([-2.98, -0.04, 0]).set_z_index(2)
        pm_title = fit(
            VGroup(
                svg_icon("shield_check", size=0.40, col=C_CYAN, accent=C_GOLD, z=7),
                txt(f"{TERM['seg_status']} 요약 ({num(len(seg_rows))}×{num(len(seg_cols))}={num(seg_cells_n)}개 고객군, {base_var_name})", size=13.8, color=C_WHITE, bold=True, z=7),
            ).arrange(RIGHT, buff=0.09),
            max_w=6.24,
        ).move_to([-2.98, 2.14, 0])

        seg_grid = fact("segment_map_grid")
        grouped_seg: list[list[dict]] = []
        for row_obj in seg_grid:
            sig = tuple((c["label"], c["gate_only"]) for c in row_obj["cells"])
            if grouped_seg and tuple((c["label"], c["gate_only"]) for c in grouped_seg[-1][0]["cells"]) == sig:
                grouped_seg[-1].append(row_obj)
            else:
                grouped_seg.append([row_obj])

        pm_cells = VGroup()
        focus_cell = None
        for r_i, grp in enumerate(grouped_seg):
            ry = 1.14 - r_i * 0.72
            grp_n = len(grp)
            r0_s = label_ko(grp[0]["row"])
            r1_s = label_ko(grp[-1]["row"])
            has_focus_in_row = any(c["label"] == seg_lbls[1] and c["gate_only"] for c in grp[0]["cells"])
            r_col = C_GOLD if has_focus_in_row else C_INK_0
            if r0_s == r1_s:
                r_mob = fit(txt(r0_s, size=12.6, color=r_col, bold=True, z=7), max_w=2.26).move_to([-4.98, ry, 0])
            else:
                r_mob = fit(
                    VGroup(
                        txt(f"{r0_s} ~ ({num(grp_n)}구간)", size=12.6, color=r_col, bold=True, z=7),
                        txt(r1_s, size=12.6, color=r_col, bold=True, z=7),
                    ).arrange(DOWN, buff=0.04),
                    max_w=2.26,
                ).move_to([-4.98, ry, 0])
            pm_cells.add(r_mob)
            for c_i, c_info in enumerate(grp[0]["cells"]):
                cw_p = 1.84 if c_i == 0 else 2.04
                cx = -2.86 if c_i == 0 else -0.82
                raw_lbl = c_info["label"]
                disp_lbl = label_ko(raw_lbl)
                is_open = raw_lbl in (seg_lbls[0], seg_lbls[1])
                is_gate = bool(c_info["gate_only"])
                is_hi = is_open and is_gate
                cell_r = RoundedRectangle(
                    corner_radius=0.05,
                    width=cw_p,
                    height=0.66,
                    fill_color="#383016" if is_hi else ("#182832" if is_open else C_PANEL_HI),
                    fill_opacity=0.96,
                    stroke_color=C_GOLD if is_hi else (C_AMBER if is_gate else (C_CYAN if is_open else C_SLATE)),
                    stroke_width=2.2 if is_hi else (1.7 if is_gate else 1.3),
                ).move_to([cx, ry, 0]).set_z_index(4)
                cell_col = C_GOLD if is_hi else (C_CYAN if is_open else C_INK_1)
                if is_gate:
                    ct = fit(txt(disp_lbl, size=12.8, color=cell_col, bold=True, z=7), max_w=cw_p - 0.10).move_to(cell_r.get_center() + UP * 0.15)
                    gt = fit(pill(f"{TERM['peer']}: {TERM['uw_only']}", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=12.6, px=0.07, py=0.025, z=8), max_w=cw_p - 0.08).move_to(cell_r.get_center() + DOWN * 0.15)
                    cell_grp = VGroup(cell_r, ct, gt)
                else:
                    ct = fit(txt(disp_lbl, size=12.6, color=cell_col, bold=is_open, z=7), max_w=cw_p - 0.10).move_to(cell_r)
                    cell_grp = VGroup(cell_r, ct)
                if is_hi:
                    focus_cell = cell_r
                pm_cells.add(cell_grp)

        pm_age_hdr = VGroup(
            pill(seg_cols[0], fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=13.0, px=0.12, py=0.04, z=7).move_to([-2.86, 1.66, 0]),
            pill(seg_cols[1], fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=13.0, px=0.12, py=0.04, z=7).move_to([-0.82, 1.66, 0]),
        )
        pm_foot = fit(
            VGroup(
                txt(
                    f"집계: {TERM['open_both']} {num(seg_open_tog)}개, {TERM['ours_closed_short']} {num(seg_closed)}개,",
                    size=12.6,
                    color=C_INK_0,
                    bold=True,
                    z=7,
                ),
                txt(
                    f"{TERM['ours_only']} {num(seg_ours_only)}개 고객군",
                    size=12.6,
                    color=C_INK_0,
                    bold=True,
                    z=7,
                ),
                txt(
                    f"(별도 집계: {TERM['peer']}가 {TERM['uw_only']} 종형으로만 가입 가능한 고객군 {num(seg_gate_only)}개)",
                    size=12.6,
                    color=C_AMBER,
                    bold=True,
                    z=7,
                ),
            ).arrange(DOWN, buff=0.04),
            max_w=6.24,
        ).move_to([-2.98, -1.98, 0])

        assert focus_cell is not None
        pin_pt = focus_cell.get_right() + LEFT * 0.20 + UP * 0.14
        target_cursor = VGroup(
            Circle(radius=0.14, fill_opacity=0.0, stroke_color=WHITE, stroke_width=2.3).move_to(pin_pt),
            Line(pin_pt + LEFT * 0.20, pin_pt + RIGHT * 0.20, color=WHITE, stroke_width=1.5),
            Line(pin_pt + DOWN * 0.20, pin_pt + UP * 0.20, color=WHITE, stroke_width=1.5),
            Dot(pin_pt, radius=0.042, color=C_GOLD),
        ).set_z_index(10)
        phase_map_grp = VGroup(pm_frame, pm_title, pm_age_hdr, pm_cells, pm_foot, target_cursor)

        # Top-Right: 치료 단계별 보유 담보 수 타임라인 패널
        cj_frame = RoundedRectangle(
            corner_radius=0.09,
            width=5.68,
            height=2.60,
            fill_color=C_PANEL,
            fill_opacity=0.96,
            stroke_color=C_GOLD_DEEP,
            stroke_width=1.9,
        ).move_to([3.40, 1.18, 0]).set_z_index(2)
        cj_title = fit(
            VGroup(
                svg_icon("hq_console", size=0.38, col=C_GOLD, accent=C_CYAN, z=7),
                txt(f"치료 {num(n_tr_stages)}단계별 보유 담보 수 (합계 {num(held_total)}개)", size=14.0, color=C_WHITE, bold=True, z=7),
            ).arrange(RIGHT, buff=0.09),
            max_w=5.38,
        ).move_to([3.40, 2.14, 0])

        stage_cols = [C_CYAN, C_CYAN, C_MINT, C_GOLD, C_CORAL]
        cj_bars, cj_nodes = VGroup(), VGroup()
        cj_base_y = 0.44
        cj_axis = Line([0.82, cj_base_y, 0], [5.98, cj_base_y, 0], color=C_SLATE, stroke_width=1.8).set_z_index(4)
        unheld_parts = TERM["unheld_cov"].split(" ", 1) if " " in TERM["unheld_cov"] else [TERM["unheld_cov"]]
        for s_i, s_nm in enumerate(tr_stages):
            s_cnt = held_by_stage[s_nm]
            s_col = stage_cols[s_i % len(stage_cols)]
            sx = 1.28 + s_i * 1.06
            slot_bg = RoundedRectangle(
                corner_radius=0.05,
                width=0.90,
                height=1.22,
                fill_color=C_PANEL_HI,
                fill_opacity=0.94,
                stroke_color=C_CORAL if s_cnt == 0 else C_SLATE,
                stroke_width=2.0 if s_cnt == 0 else 1.1,
            ).move_to([sx, cj_base_y + 0.61, 0]).set_z_index(3)
            if s_cnt > 0:
                bh = (s_cnt / max_stage_cnt) * 0.72
                bar = RoundedRectangle(corner_radius=0.04, width=0.54, height=bh, fill_color=s_col, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.0).move_to([sx, cj_base_y + 0.08 + bh / 2, 0]).set_z_index(5)
                cj_bars.add(VGroup(slot_bg, bar, txt(f"{num(s_cnt)}개", size=13.4, color=WHITE, bold=True, z=7).move_to([sx, cj_base_y + 0.08 + bh + 0.18, 0])))
            else:
                unheld_t = fit(
                    VGroup(*[txt(up_s, size=13.8, color=C_CORAL, bold=True, z=7) for up_s in unheld_parts]).arrange(DOWN, buff=0.03),
                    max_w=0.86,
                ).move_to(slot_bg.get_center() + DOWN * 0.22)
                cj_bars.add(
                    VGroup(
                        slot_bg,
                        txt(f"{num(s_cnt)}개", size=13.6, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + UP * 0.30),
                        unheld_t,
                    )
                )
            cj_nodes.add(txt(s_nm, size=13.8, color=C_CORAL if s_cnt == 0 else C_INK_0, bold=True, z=7).move_to([sx, cj_base_y - 0.24, 0]))

        cj_links = VGroup(
            *[Line([1.28 + i * 1.06 + 0.47, cj_base_y + 0.61, 0], [1.28 + (i + 1) * 1.06 - 0.47, cj_base_y + 0.61, 0], color=C_CORAL if i == n_tr_stages - 2 else C_GOLD, stroke_width=2.2).set_z_index(6) for i in range(n_tr_stages - 1)]
        )
        care_journey_grp = VGroup(cj_frame, cj_title, cj_axis, cj_bars, cj_nodes, cj_links)

        # Bottom-Right: 특약 부가 조건 및 실제 지급액 계산 파이프라인
        rc_box = RoundedRectangle(corner_radius=0.09, width=5.68, height=2.24, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.9).move_to([3.40, -1.44, 0]).set_z_index(3)
        rc_hdr = fit(
            VGroup(
                svg_icon("code_calc", size=0.38, col=C_GOLD, accent=C_MINT, z=7),
                txt(f"{TERM['rider_cond']} 및 실제 지급액 계산", size=14.0, color=C_GOLD, bold=True, z=7),
            ).arrange(RIGHT, buff=0.09),
            max_w=5.38,
        ).move_to([3.40, -0.64, 0])

        def make_rc_badge(cx: float, w_b: float, col: str, l1: str, l2: str, bg_c: str = C_PANEL_HI) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.07,
                width=w_b,
                height=0.64,
                fill_color=bg_c,
                fill_opacity=0.97,
                stroke_color=col,
                stroke_width=1.6,
            ).move_to([cx, -1.36, 0]).set_z_index(6)
            tg = fit(
                VGroup(
                    txt(l1, size=12.8, color=col, bold=True, z=7),
                    txt(l2, size=12.8, color=C_WHITE, bold=True, z=7),
                ).arrange(DOWN, buff=0.05),
                max_w=w_b - 0.12,
            ).move_to(bx)
            return VGroup(bx, tg)

        nd_main = make_rc_badge(1.54, 1.68, C_GOLD, TERM["main_limit"], f"{num(main_lim_mw)}만 원")
        nd_rider = make_rc_badge(3.46, 1.88, C_CYAN, f"기준 {num(basis_mw)}만 원", f"-> 지급 {num(pay_new_mw)}만 원")
        nd_excl = make_rc_badge(5.34, 1.62, C_CORAL, TERM["rider_cond"], f"{num(comb_cnt)}건 반영", bg_c=C_CORAL_DIM)
        constraint_grp = VGroup(
            rc_box,
            rc_hdr,
            nd_main,
            nd_rider,
            nd_excl,
            arrow_2d(nd_main.get_right(), nd_rider.get_left(), color=C_MINT, sw=2.0, tip=0.09, z=7),
            arrow_2d(nd_rider.get_right(), nd_excl.get_left(), color=C_CORAL, sw=2.0, tip=0.09, z=7),
            fit(txt("주계약 연동 가입한도와 선행, 동시 가입 제한 규칙 반영 ✓", size=12.8, color=C_INK_0, bold=True, z=7), max_w=5.42).move_to([3.40, -2.14, 0]),
        )
        beat8b_all = VGroup(phase_map_grp, care_journey_grp, constraint_grp)

        # Step 1: Spotlight onto Left Underwriting Matrix Console
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.22,
            center=[-2.98, -0.04, 0],
            anims=[
                FadeOut(graph_8a_3d),
                FadeOut(VGroup(*all_8a_bbs)),
                FadeOut(hop_badge),
                FadeIn(pm_frame),
                FadeIn(pm_title),
                FadeIn(pm_age_hdr),
                LaggedStart(*[FadeIn(c, shift=UP * 0.05) for c in pm_cells], lag_ratio=0.04),
                FadeIn(pm_foot, shift=UP * 0.05),
            ],
            rt=1.30,
        )
        self.clear_billboards(*all_8a_bbs)
        self.remove_fixed_in_frame_mobjects(hop_badge)
        self.remove(graph_8a_3d, hop_badge)

        assert focus_cell is not None
        self.play(
            FadeIn(target_cursor, scale=1.5),
            Circumscribe(focus_cell, color=C_GOLD, stroke_width=2.4, buff=0.04),
            run_time=1.00,
        )
        self.wait(2.20)

        # Step 2: Spotlight onto Right Care-Journey & Payout Constraints
        self.cam_move(
            zoom=1.22,
            center=[3.40, -0.04, 0],
            anims=[
                FadeOut(phase_map_grp, shift=LEFT * 0.10),
                FadeIn(cj_frame),
                FadeIn(cj_title, shift=DOWN * 0.06),
                Create(cj_axis),
                LaggedStart(*[FadeIn(b, shift=UP * 0.10) for b in cj_bars], lag_ratio=0.10),
                FadeIn(cj_nodes),
                Create(cj_links, lag_ratio=0.10),
            ],
            rt=1.25,
        )
        cj_pulse = glow_dot([1.28, cj_base_y + 0.61, 0], color=C_GOLD, r=0.065, z=13)
        self.add(cj_pulse)
        self.play(
            MoveAlongPath(cj_pulse, Line([1.28, cj_base_y + 0.61, 0], [1.28 + (n_tr_stages - 1) * 1.06, cj_base_y + 0.61, 0])),
            Circumscribe(cj_bars[-1][0], color=C_CORAL, stroke_width=2.4, buff=0.04),
            FadeIn(constraint_grp, shift=UP * 0.10),
            run_time=1.25,
        )
        self.remove(cj_pulse)
        self.wait(2.20)

        # Step 3: Pull back to connect the full 2D Dashboard
        self.reset_cam_2d(anims=[FadeIn(phase_map_grp, shift=RIGHT * 0.10)], rt=1.00)
        self.check_bounds(beat8b_all, "CH8B PHASE & CARE CHARTS")
        self.wait(3.00)

        # -------------------------------------------------------------------
        # Beat 8C: 본부 영업 인사이트 가로형 데이터 콘솔(축소 없음) + 다크 A4 응대 화법 장표
        # -------------------------------------------------------------------
        ins_cats = fact("sales_insight_categories")
        n_ins_cats = len(ins_cats)
        ins_by_cat = fact("sales_insight_by_category")
        max_ins_cnt = max(ins_by_cat.values())
        ins_total = fact("sales_insight_count")
        card_ord = fact("card_category_order")
        lead_str = fact("lead_strengths")
        q_diff_peers = fact("gate_question_diff_peer_count")
        var_gen_name = fact("base_variants", 3, "name")
        var_gen_def_cnt = fact("briefing_by_base_variant", var_gen_name, "insights", "by_category", ins_cats[3])
        forb_cnt = len(fact("forbidden_words"))

        hb = self.update_subtitle(
            hb,
            f"분석 결과가 영업 인사이트 {num(n_ins_cats)}분류(합계 {num(ins_total)}건, {base_var_name})와 창구용 A4 단일 {TERM['script_doc']} 문서로 정리됩니다",
            rt=0.45,
        )

        app_window = RoundedRectangle(
            corner_radius=0.10,
            width=8.56,
            height=5.00,
            fill_color=C_PANEL,
            fill_opacity=0.96,
            stroke_color=C_CYAN,
            stroke_width=2.2,
        ).move_to([-1.96, -0.10, 0]).set_z_index(2)
        app_hdr_ic = svg_icon("hq_console", size=0.42, col=C_CYAN, accent=C_GOLD, z=7)
        app_hdr_t = txt(f"{SCREEN_TITLE} (오프라인 단독 HTML)", size=14.4, color=C_WHITE, bold=True, z=7)
        app_hdr_sum = pill(f"{num(n_ins_cats)}분류 합계 {num(ins_total)}건 ({base_var_name})", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.0, px=0.12, py=0.05, z=7)
        app_win_hdr = fit(VGroup(app_hdr_ic, app_hdr_t, app_hdr_sum).arrange(RIGHT, buff=0.14), max_w=8.28).move_to([-1.96, 2.02, 0])

        # 번호와 색은 분류(sales_insight_categories의 차례)에 고정해 콘솔과 A4 장표가 같은 분류에 같은 번호, 같은 색을 쓴다.
        cat_mark = {c_k: chr(ord("①") + c_i) for c_i, c_k in enumerate(ins_cats)}
        cat_col = dict(zip(ins_cats, [C_GOLD, C_MINT, C_VIOLET, C_CYAN, C_CORAL]))

        def cat_tag(c_k: str) -> str:
            return f"{cat_mark[c_k]} {label_ko(c_k)}"

        ins_row_specs = [
            (
                cat_col[ins_cats[0]],
                cat_tag(ins_cats[0]),
                ins_by_cat[ins_cats[0]],
                f"{num(ins_by_cat[ins_cats[0]])}건",
                f"{TERM['disc_item']} 상이 {TERM['peer']} {num(q_diff_peers)}개사({TERM['ours_only']} {num(seg_ours_only)}개 고객군)",
            ),
            (
                cat_col[ins_cats[1]],
                cat_tag(ins_cats[1]),
                ins_by_cat[ins_cats[1]],
                f"{num(ins_by_cat[ins_cats[1]])}건",
                f"대표 담보: {lead_str}",
            ),
            (
                cat_col[ins_cats[2]],
                cat_tag(ins_cats[2]),
                ins_by_cat[ins_cats[2]],
                f"{num(ins_by_cat[ins_cats[2]])}건",
                f"{rel_kinds_str} 관계 분리 특약과 상위 특약 연결 안내",
            ),
            (
                cat_col[ins_cats[3]],
                cat_tag(ins_cats[3]),
                ins_by_cat[ins_cats[3]],
                f"기준 {num(ins_by_cat[ins_cats[3]])}건",
                f"{var_gen_name} {num(var_gen_def_cnt)}건, 감액 조건과 {TERM['verdict_hold']} 분리",
            ),
            (
                cat_col[ins_cats[4]],
                cat_tag(ins_cats[4]),
                ins_by_cat[ins_cats[4]],
                f"{num(ins_by_cat[ins_cats[4]])}건",
                f"입원 {num(held_by_stage['입원'])}개 대비 통원 {num(held_by_stage['통원'])}개 등 {TERM['unheld_cov']} 정리",
            ),
        ]

        ins_row_Shells, ins_row_Bars = VGroup(), VGroup()
        bar_max_8c = 0.60
        for r_idx, (r_col, r_cat_s, r_cnt, r_cnt_s, r_desc_s) in enumerate(ins_row_specs):
            ry = 1.32 - r_idx * 0.59
            r_bg = RoundedRectangle(
                corner_radius=0.06,
                width=8.28,
                height=0.51,
                fill_color=C_PANEL_HI,
                fill_opacity=0.95,
                stroke_color=r_col,
                stroke_width=1.5,
            ).move_to([-1.96, ry, 0]).set_z_index(4)
            cat_lbl = fit(txt(r_cat_s, size=13.0, color=r_col, bold=True, z=7), max_w=1.70)
            cat_lbl.move_to([-5.98 + cat_lbl.width / 2, ry, 0])

            trk = RoundedRectangle(
                corner_radius=0.04,
                width=bar_max_8c,
                height=0.20,
                fill_color=C_BG_SUB,
                fill_opacity=0.96,
                stroke_color=C_SLATE,
                stroke_width=1.0,
            ).move_to([-3.90, ry, 0]).set_z_index(5)
            cnt_lbl = fit(txt(r_cnt_s, size=12.8, color=C_WHITE if r_cnt > 0 else C_INK_1, bold=True, z=7), max_w=0.86).move_to([-3.12, ry, 0])
            desc_lbl = fit(txt(r_desc_s, size=12.6, color=C_INK_0, bold=True, z=7), max_w=4.70)
            desc_lbl.move_to([-2.60 + desc_lbl.width / 2, ry, 0])
            ins_row_Shells.add(VGroup(r_bg, cat_lbl, trk, cnt_lbl, desc_lbl))

            if r_cnt > 0:
                bw_8c = max(0.08, (r_cnt / max_ins_cnt) * bar_max_8c)
                b_fill = RoundedRectangle(
                    corner_radius=0.04,
                    width=bw_8c,
                    height=0.20,
                    fill_color=r_col,
                    fill_opacity=0.94,
                    stroke_color=WHITE,
                    stroke_width=0.8,
                ).move_to([trk.get_left()[0] + bw_8c / 2, ry, 0]).set_z_index(6)
                ins_row_Bars.add(b_fill)

        guard_strip_8c = fit(
            VGroup(
                pill(f"금지 표현 {num(forb_cnt)}개 빌드 차단 ✓, 근거 문서와 쪽수 표시", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=12.6, px=0.10, py=0.05, z=7),
                pill("차기 과제(다음 버전): 자연어 조건 검색 입력 연동", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=12.6, px=0.10, py=0.05, z=7),
            ).arrange(RIGHT, buff=0.10),
            max_w=8.32,
        ).move_to([-1.96, -2.12, 0])

        # A4 장표는 card_category_order 차례로 싣되, 번호와 색은 콘솔과 같은 분류 고정 값을 쓴다.
        a4_rows_8c = [(cat_col[c_cat], f"{cat_tag(c_cat)} ({num(ins_by_cat[c_cat])}건)") for c_cat in card_ord]
        a4_full = make_dark_a4_sheet(
            center=[4.62, -0.10, 0],
            w=3.16,
            h=5.00,
            badge_s="대외 배포 금지, A4 단일 장표",
            title_s=f"창구, 설계사 {TERM['script_doc']}",
            rows=a4_rows_8c,
            foot_s=f"본부 판단 -> 현장 A4 {TERM['script_doc']} 전달",
            z=5,
        )
        proj_beam = arrow_2d([2.38, -0.10, 0], [2.96, -0.10, 0], color=C_GOLD, sw=3.2, tip=0.16, z=8)

        # Step 1: Spotlight onto the HQ Sales Insight Console (full-size crisp rows & data bars)
        self.cam_move(
            zoom=1.20,
            center=[-1.96, -0.08, 0],
            anims=[
                FadeOut(beat8b_all, scale=0.95),
                FadeIn(app_window),
                FadeIn(app_win_hdr, shift=DOWN * 0.06),
                LaggedStart(*[FadeIn(sh, shift=RIGHT * 0.10) for sh in ins_row_Shells], lag_ratio=0.08),
            ],
            rt=1.35,
        )
        self.remove(beat8b_all)
        self.play(
            LaggedStart(*[GrowFromEdge(bf, LEFT) for bf in ins_row_Bars], lag_ratio=0.10),
            FadeIn(guard_strip_8c, shift=UP * 0.08),
            run_time=1.05,
        )
        self.wait(2.40)

        # Step 2: Pan right and project into the Dark-Slate & Gold A4 Script Sheet with laser sweep
        console_8c_grp = VGroup(app_window, app_win_hdr, ins_row_Shells, ins_row_Bars, guard_strip_8c)
        a4_laser = Line([3.04, 2.34, 0], [6.20, 2.34, 0], color=C_GOLD, stroke_width=3.6).set_z_index(12)
        self.add(a4_laser)
        self.cam_move(
            zoom=1.20,
            center=[4.04, -0.10, 0],
            anims=[
                FadeOut(console_8c_grp, shift=LEFT * 0.10),
                GrowArrow(proj_beam),
                FadeIn(VGroup(*a4_full[:7])),
                a4_laser.animate.move_to([4.62, -2.54, 0]),
                LaggedStart(*[FadeIn(rm, shift=DOWN * 0.05) for rm in a4_full[7]], lag_ratio=0.10),
                FadeIn(VGroup(a4_full[8], a4_full[9])),
            ],
            rt=1.55,
        )
        self.remove(a4_laser)
        self.wait(1.90)

        self.reset_cam_2d(anims=[FadeIn(console_8c_grp, shift=RIGHT * 0.10)], rt=0.95)
        ch8_stage = VGroup(app_window, app_win_hdr, ins_row_Shells, ins_row_Bars, guard_strip_8c, proj_beam, a4_full)
        self.check_bounds(ch8_stage, "CH8C CONSOLE & CARD")
        self.wait(4.10)

        # ===================================================================
        # 9장: 기존 수작업 병목 대비 4단계 엔드투엔드 자동화 시스템 아키텍처
        # ===================================================================
        news_inst_cnt = fact("market_news_institution_count")
        wlog_site = fact("work_log_count_site")
        img_doc = fact("image_doc")
        img_pages = img_doc["pages"]
        img_mismatches = img_doc["amount_mismatches"]
        cal_flip = fact("calibration_flipped_rows")
        decide_model = fact("models", "decide")
        no_verd = fact("no_verdict_pairs")
        no_verd_sum = no_verd["other_rider"] + no_verd["payment_form"]
        test_cnt = fact("test_count")
        nym_list = [label_ko(s) for s in fact("not_yet_measured")]

        hl, hr, hb = self.switch_hud(
            ch8_stage,
            hl,
            hr,
            hb,
            9,
            "기존 수작업 방식과 본 시스템의 구현 구조",
            "수작업 대조에서 자동 수집, 검증, 단독 화면으로 전환한 구조와 미측정 과제를 함께 정리합니다",
        )

        # 상단: 기존 수작업 방식의 병목 모듈
        def make_manual_bottleneck_9(cx: float, ic_nm: str, t1: str, t2: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.08,
                width=3.96,
                height=1.04,
                fill_color=C_PANEL,
                fill_opacity=0.96,
                stroke_color=C_CORAL,
                stroke_width=1.9,
            ).move_to([cx, 2.22, 0]).set_z_index(4)
            ic = svg_icon(ic_nm, size=0.36, col=C_CORAL, accent=C_AMBER, bg=C_CORAL_DIM, z=7)
            top_r = fit(
                VGroup(ic, txt(t1, size=13.4, color=C_CORAL, bold=True, z=7)).arrange(RIGHT, buff=0.08),
                max_w=3.76,
            )
            bot_r = fit(txt(t2, size=12.6, color=C_INK_0, bold=True, z=7), max_w=3.78)
            grp = VGroup(top_r, bot_r).arrange(DOWN, buff=0.06).move_to(bx)
            return VGroup(bx, grp)

        mb9_1 = make_manual_bottleneck_9(-4.16, "doc_text", "기존 수작업 ① 서술형 공시 대조", "회사별 고지 범위, 지급기준 표기 상이")
        mb9_2 = make_manual_bottleneck_9(0.00, "doc_image", f"기존 수작업 ② 합계 {num(img_pages)}쪽 이미지 요약서", "수치 직접 추출 오독 및 특약명 불일치")
        mb9_3 = make_manual_bottleneck_9(4.16, "alert_warn", "기존 수작업 ③ 문장 속 조건 차이", "감액기간, 면책기간, 지급 배수를 손으로 대조")
        manual_row_9 = VGroup(mb9_1, mb9_2, mb9_3)

        # 상단 -> 중앙 전환 브리지 화살표
        down_bridges_9 = VGroup(
            arrow_2d([-4.16, 1.66, 0], [-4.16, 1.26, 0], color=C_CYAN, sw=2.6, tip=0.11, z=6),
            arrow_2d([4.16, 1.66, 0], [4.16, 1.26, 0], color=C_MINT, sw=2.6, tip=0.11, z=6),
            pill("개념검증 구현 아키텍처로 전환 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.0, px=0.14, py=0.05, z=8).move_to([0.0, 1.46, 0]),
        )

        # 중앙: 자동화 파이프라인 단계 노드
        def make_pipe_stage_9(
            cx: float,
            col: str,
            ic_nm: str,
            title_s: str,
            body_lines: tuple[str, ...],
            chip_s: str | tuple[str, str],
            chip_fg: str,
            chip_bg: str,
        ) -> VGroup:
            card = RoundedRectangle(
                corner_radius=0.09,
                width=2.92,
                height=2.34,
                fill_color=C_PANEL_HI,
                fill_opacity=0.97,
                stroke_color=col,
                stroke_width=2.3,
            ).move_to([cx, 0.04, 0]).set_z_index(5)
            hdr = fit(
                VGroup(
                    svg_icon(ic_nm, size=0.36, col=col, accent=C_WHITE, z=8),
                    txt(title_s, size=13.6, color=col, bold=True, z=8),
                ).arrange(RIGHT, buff=0.07),
                max_w=2.76,
            ).move_to([cx, 0.88, 0])
            rule = Line([cx - 1.28, 0.56, 0], [cx + 1.28, 0.56, 0], color=col, stroke_width=1.2, stroke_opacity=0.55).set_z_index(6)
            b_mobs = [
                txt(bl, size=12.8 if idx == 0 else 12.6, color=C_WHITE if idx == 0 else C_INK_1, bold=True, z=8)
                for idx, bl in enumerate(body_lines)
            ]
            body_t = fit(VGroup(*b_mobs).arrange(DOWN, buff=0.05), max_w=2.76).move_to([cx, 0.04, 0])
            if isinstance(chip_s, tuple):
                chip = fit(
                    make_mini_badge_2l(chip_s[0], chip_s[1], chip_fg, C_WHITE, chip_bg, col, s1=13.2, s2=13.4, px=0.10, py=0.04, z=8),
                    max_w=2.76,
                ).move_to([cx, -0.74, 0])
            else:
                chip = fit(pill(chip_s, fg=chip_fg, bg=chip_bg, border=col, size=12.6, px=0.09, py=0.05, z=8), max_w=2.76).move_to([cx, -0.74, 0])
            return VGroup(card, hdr, rule, body_t, chip)

        st9_1 = make_pipe_stage_9(
            -4.62,
            C_CYAN,
            "database_master",
            "① 수집, 마스터 적재",
            (
                f"{num(news_inst_cnt)}개 기관 {TERM['trend']} 선별",
                f"{TERM['master']} {num(sheet_tabs)}탭 적재",
            ),
            f"운영 비용 {num(op_cost)}원(무료 설계)",
            C_CYAN,
            C_BG_SUB,
        )
        st9_2 = make_pipe_stage_9(
            -1.54,
            C_GOLD,
            "code_calc",
            "② 원문 추출, 코드 계산",
            (
                f"원문 {TERM['extract']}과 코드 계산 분리",
                f"이미지 {num(img_pages)}쪽 {TERM['extract_dual']} {TERM['cross_verify']}",
            ),
            f"불일치 {num(img_mismatches)}건(상호 일치)",
            C_MINT,
            C_BG_SUB,
        )
        st9_3 = make_pipe_stage_9(
            1.54,
            C_VIOLET,
            "cpu_decide",
            "③ 비생성 확률 산정, 표준담보",
            (
                f"{decide_model} 정형 확률 산정",
                f"표준담보 {num(cov_use)}개 ({rel_kinds_str} 관계)",
            ),
            (f"모의 오류 {num(cal_flip['rows'])}행", f"통과 {num(cal_flip['passed'])}행(소규모 표본)"),
            C_GOLD,
            "#383016",
        )
        st9_4 = make_pipe_stage_9(
            4.62,
            C_MINT,
            "brief_sheet",
            f"④ 단독 화면, A4 {TERM['script_doc']}",
            (
                f"화면 {TERM['review_wait']} {num(ms_site['대기'])}건,",
                f"{TERM['verdict_hold']} {num(no_verd_sum)}건 분리",
                f"금지 표현 {num(forb_cnt)}개 차단, 인사이트 {num(n_ins_cats)}분류",
            ),
            f"화면 작업 로그 {num(wlog_site)}건 ✓",
            C_DARK_INK,
            C_MINT,
        )
        pipe_conns_9 = VGroup(
            arrow_2d(st9_1[0].get_right(), st9_2[0].get_left(), color=C_GOLD, sw=2.6, tip=0.09, z=7),
            arrow_2d(st9_2[0].get_right(), st9_3[0].get_left(), color=C_VIOLET, sw=2.6, tip=0.09, z=7),
            arrow_2d(st9_3[0].get_right(), st9_4[0].get_left(), color=C_MINT, sw=2.6, tip=0.09, z=7),
        )

        # 하단: 점검 지표 배너 및 미측정 과제 배너
        fin_box = RoundedRectangle(
            corner_radius=0.08,
            width=12.56,
            height=0.80,
            fill_color=C_PANEL_HI,
            fill_opacity=0.97,
            stroke_color=C_GOLD_DEEP,
            stroke_width=1.7,
        ).move_to([0.0, -1.66, 0]).set_z_index(8)
        fin_txt = fit(
            VGroup(
                txt(f"점검: 자동 {TERM['test']} {num(test_cnt)}건(발표 전 pytest 재측정), 브라우저 점검 오류 {num(br_problems)}건", size=12.8, color=C_GOLD, bold=True, z=9),
                txt(f"보험료({num(prem_rows)}행)와 질병코드({num(dis_rows)}행) 탭 공란 (차기 과제)", size=12.6, color=C_INK_0, bold=True, z=9),
            ).arrange(DOWN, buff=0.05),
            max_w=12.32,
        ).move_to(fin_box)
        finale_ribbon = VGroup(fin_box, fin_txt)

        nym_box = RoundedRectangle(
            corner_radius=0.08,
            width=12.56,
            height=0.82,
            fill_color=C_BG_SUB,
            fill_opacity=0.97,
            stroke_color=C_SLATE,
            stroke_width=1.6,
        ).move_to([0.0, -2.60, 0]).set_z_index(8)
        nym_txt = fit(
            VGroup(
                txt(f"미측정 과제: {nym_list[0]}", size=12.8, color=C_INK_0, bold=True, z=9),
                txt(f"{nym_list[1]}, {nym_list[2]}", size=12.6, color=C_INK_1, bold=True, z=9),
            ).arrange(DOWN, buff=0.05),
            max_w=12.32,
        ).move_to(nym_box)
        nym_ribbon = VGroup(nym_box, nym_txt)

        # Step 1: 상단 수작업 병목 제시
        self.play(
            LaggedStart(*[FadeIn(m, shift=DOWN * 0.10) for m in manual_row_9], lag_ratio=0.12),
            run_time=1.05,
        )
        self.wait(1.60)

        # Step 2: 좌측 파이프라인 Stage ① -> ② 스포트라이트 점화
        p9_a = glow_dot(st9_1[0].get_right(), color=C_GOLD, r=0.065, z=12)
        self.add(p9_a)
        self.cam_move(
            zoom=1.16,
            center=[-3.04, 0.34, 0],
            anims=[
                FadeOut(mb9_3, shift=RIGHT * 0.08),
                FadeIn(VGroup(down_bridges_9[0], down_bridges_9[2]), shift=DOWN * 0.08),
                FadeIn(st9_1, shift=UP * 0.12),
                GrowArrow(pipe_conns_9[0]),
                MoveAlongPath(p9_a, Line(st9_1[0].get_right(), st9_2[0].get_left())),
                FadeIn(st9_2, shift=UP * 0.12),
            ],
            rt=1.45,
        )
        self.remove(p9_a)
        self.wait(2.10)

        # Step 3: 우측 파이프라인 Stage ③ -> ④ 스포트라이트 점화
        left_p9_grp = VGroup(mb9_1, down_bridges_9[0], st9_1, pipe_conns_9[0])
        # 카메라 중심(가로)은 이 단계에 남는 카드 그룹(위 ②, ③과 아래 ②, ③, ④)의 경계 박스 가운데로 둔다.
        step3_cards_9 = VGroup(mb9_2, mb9_3, st9_2, st9_3, st9_4)
        p9_b = glow_dot(st9_2[0].get_right(), color=C_MINT, r=0.065, z=12)
        self.add(p9_b)
        self.cam_move(
            zoom=1.16,
            center=[step3_cards_9.get_center()[0], 0.34, 0],
            anims=[
                FadeOut(left_p9_grp, shift=LEFT * 0.08),
                FadeIn(mb9_3, shift=LEFT * 0.08),
                FadeIn(down_bridges_9[1], shift=DOWN * 0.08),
                GrowArrow(pipe_conns_9[1]),
                MoveAlongPath(p9_b, Line(st9_2[0].get_right(), st9_4[0].get_left())),
                FadeIn(st9_3, shift=UP * 0.12),
                GrowArrow(pipe_conns_9[2]),
                FadeIn(st9_4, shift=UP * 0.12),
            ],
            rt=1.50,
        )
        self.remove(p9_b)
        self.wait(2.20)

        # Step 4: 전체 엔드투엔드 파이프라인 + 하단 점검 도크 통합 연결
        self.reset_cam_2d(
            anims=[
                FadeIn(left_p9_grp, shift=RIGHT * 0.08),
                FadeIn(finale_ribbon, shift=UP * 0.06),
                FadeIn(nym_ribbon, shift=UP * 0.05),
                LaggedStart(*[Circumscribe(st[0], color=C_GOLD, stroke_width=2.2, buff=0.03) for st in [st9_1, st9_2, st9_3, st9_4]], lag_ratio=0.10),
            ],
            rt=1.05,
        )

        ch9_stage = VGroup(manual_row_9, down_bridges_9, st9_1, st9_2, st9_3, st9_4, pipe_conns_9, finale_ribbon, nym_ribbon)
        self.check_bounds(ch9_stage, "CH9 END TO END PIPELINE")
        self.wait(4.80)
