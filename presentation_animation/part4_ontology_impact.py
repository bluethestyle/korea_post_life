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
    C_IVORY,
    C_MINT,
    C_PANEL,
    C_PANEL_HI,
    C_SLATE,
    C_VIOLET,
    C_WHITE,
    PostLifeBaseScene,
    arrow_2d,
    bb_badge,
    capacity_ring,
    fact,
    fit,
    floor_grid_3d,
    glass_plane_3d,
    glow_dot,
    num,
    pillar_3d,
    pill,
    txt,
)


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
            "온톨로지와 단독 화면: 명칭 불일치와 매핑 대기를 푼 방법",
            "회사별 특약 이름 불일치, 매핑 대기 줄, 통합과 분리 구조 차이를 풀고 보험료 비교는 남은 과제로 두었습니다",
        )

        # -------------------------------------------------------------------
        # Beat 7A: Dynamic Spotlight-to-Dock Obstacle Tour -> 2x2 Diagnostic Board
        # -------------------------------------------------------------------
        res_box_7 = RoundedRectangle(
            corner_radius=0.09, width=3.38, height=4.72, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=2.1
        ).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_7 = pill("정본과 배포 조건", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=12.0, z=7).move_to([-4.38, 1.94, 0])

        rg7_1 = capacity_ring([-5.15, 0.72, 0], 0.60, C_GOLD, "운영 비용", f"{num(op_cost)}원 (무료 설계)", z=6)
        rg7_2 = capacity_ring([-3.62, 0.72, 0], 0.60, C_CYAN, "구글 시트 정본", f"{num(sheet_tabs)}탭", z=6)

        html_pill_7 = fit(pill("사본 자료를 실은 HTML 한 파일", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=10.8, z=7), max_w=3.06).move_to([-4.38, -0.78, 0])
        res_sub_7 = fit(txt(f"브라우저 점검 문제, 외부 요청 {num(br_problems)}건", size=10.4, color=C_INK_1, bold=True, z=7), max_w=3.06).move_to([-4.38, -1.50, 0])
        res_grp_7 = VGroup(res_box_7, res_hdr_7, rg7_1, rg7_2, html_pill_7, res_sub_7)
        vs_arr_7 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.8, tip=0.14, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.08, width=3.76, height=2.16, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=col, stroke_width=2.1
            ).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=11.8, color=col, bold=True, z=7), max_w=3.48).move_to([cx, cy + 0.78, 0])
            return VGroup(bx, th)

        q7_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 종형명, 특약명, 지급방식 상이")
        m7_l1 = fit(pill(base_var_name, fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.8, px=0.09, py=0.04), max_w=1.56).move_to([-1.05, 1.32, 0]).set_z_index(7)
        m7_r1_c = fit(pill(peer0_name, fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=9.6, px=0.09, py=0.04), max_w=1.60).move_to([0.88, 1.32, 0]).set_z_index(7)
        m7_l2 = fit(pill("수술 회당 지급", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.8, px=0.09, py=0.04), max_w=1.56).move_to([-1.05, 0.80, 0]).set_z_index(7)
        m7_r2_c = fit(pill("연간 한 번 지급", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.8, px=0.09, py=0.04), max_w=1.56).move_to([0.88, 0.80, 0]).set_z_index(7)
        m7_neqs = VGroup(
            txt("≠", size=16, color=C_CORAL, bold=True).move_to([-0.10, 1.32, 0]),
            txt("≠", size=16, color=C_CORAL, bold=True).move_to([-0.10, 0.80, 0]),
        ).set_z_index(7)
        q7_1_cap = fit(txt("단순 문자열과 금액 비교 불가능", size=10.2, color=C_INK_0, bold=True, z=7), max_w=3.48).move_to([-0.10, 0.40, 0])
        card7_1 = VGroup(q7_1, m7_l1, m7_r1_c, m7_l2, m7_r2_c, m7_neqs, q7_1_cap)

        q7_2 = diag_frame(3.88, 1.18, C_CORAL, f"문제 ② 처음 {num(dict_init)}개 사전과 한화 매핑 대기")
        cup_52 = VMobject(color=C_GOLD, stroke_width=2.4).set_z_index(7)
        cup_52.set_points_as_corners([[2.34, 1.38, 0], [2.34, 0.82, 0], [3.46, 0.82, 0], [3.46, 1.38, 0]])
        fun_lbl = txt(f"사전 {num(dict_init)}개", size=10.0, color=C_GOLD, bold=True, z=7).move_to([2.90, 1.06, 0])
        spill_dots = VGroup(
            *[Dot([3.78 + (k % 6) * 0.25, 1.38 - (k // 6) * 0.28, 0], radius=0.058, color=C_AMBER if k % 2 == 0 else C_CORAL) for k in range(12)]
        ).set_z_index(7)
        spill_tag = txt("(예시 그림)", size=8.8, color=C_INK_1, z=7).move_to([5.00, 0.80, 0])
        q7_2_cap = fit(
            txt(f"재추출 전 대기 {num(hw_pend_b['rows'])}줄({num(hw_pend_b['kinds'])}종류), 재추출 뒤 {num(hw_pend_a)}줄 대기", size=9.8, color=C_CORAL, bold=True, z=7),
            max_w=3.52,
        ).move_to([3.88, 0.42, 0])
        card7_2_base = VGroup(q7_2, cup_52, fun_lbl, spill_tag, q7_2_cap)
        card7_2_full = VGroup(card7_2_base, spill_dots)

        q7_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 통합 대 분리 오판, 대기 건 착시")
        int_chip = fit(pill("상대 통합특약 ◆", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.8, px=0.10, py=0.04), max_w=1.58).move_to([-1.06, -1.04, 0]).set_z_index(7)
        int_arr = arrow_2d([-0.26, -1.04, 0], [0.14, -1.04, 0], color=C_CORAL, sw=2.2, tip=0.10, z=7)
        false_stamp = fit(pill("미보유 오판 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.8, px=0.09, py=0.04), max_w=1.54).move_to([0.92, -1.04, 0]).set_z_index(7)
        q7_3_cap = fit(txt("우체국 분리특약 누락 위험, 매핑 대기를 미보유로 오인", size=10.0, color=C_INK_0, bold=True, z=7), max_w=3.48).move_to([-0.10, -1.74, 0])
        card7_3_base = VGroup(q7_3, int_chip, q7_3_cap)
        card7_3_full = VGroup(card7_3_base, int_arr, false_stamp)

        q7_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 공시 문서에 특약별 보험료 부재")
        no_prem = DashedVMobject(
            RoundedRectangle(corner_radius=0.05, width=3.24, height=0.62, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=1.8).move_to([3.88, -1.06, 0]),
            num_dashes=22,
        ).set_z_index(6)
        no_prem_t = fit(txt(f"특약별 보험료 예시: 사본 {num(prem_rows)}행 (다음 단계 과제)", size=10.2, color=C_CORAL, bold=True, z=7), max_w=3.06).move_to([3.88, -1.06, 0])
        q7_4_cap = fit(txt("요약서와 사업방법서에 특약 보험료가 없어 추정 표시 제외", size=9.8, color=C_INK_0, bold=True, z=7), max_w=3.48).move_to([3.88, -1.72, 0])
        card7_4 = VGroup(q7_4, no_prem, no_prem_t, q7_4_cap)

        # Save final docked centers, then stage Pair (①, ③) enlarged in the center-right spotlight
        pos_c7_1 = card7_1.get_center().copy()
        pos_c7_3 = card7_3_full.get_center().copy()
        pos_c7_2 = card7_2_full.get_center().copy()
        pos_c7_4 = card7_4.get_center().copy()

        sp7_scale = 1.18
        card7_1.scale(sp7_scale).move_to([1.85, 1.24, 0]).set_z_index(14)
        card7_3_full.scale(sp7_scale).move_to([1.85, -1.22, 0]).set_z_index(14)

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(res_grp_7, shift=RIGHT * 0.14),
                GrowArrow(vs_arr_7),
                FadeIn(card7_1, scale=0.92),
                FadeIn(card7_3_base, scale=0.92),
            ],
            rt=1.20,
        )
        self.play(
            m7_l1.animate.shift(RIGHT * 0.14),
            m7_r1_c.animate.shift(LEFT * 0.14),
            m7_l2.animate.shift(RIGHT * 0.14),
            m7_r2_c.animate.shift(LEFT * 0.14),
            rate_func=there_and_back,
            run_time=0.65,
        )
        self.play(
            GrowArrow(int_arr),
            FadeIn(false_stamp, scale=1.35),
            Flash(false_stamp.get_center(), color=C_CORAL, line_length=0.24, num_lines=8),
            run_time=0.80,
        )
        self.wait(2.20)

        # Dock Pair (①, ③) to left column while bringing Pair (②, ④) into enlarged spotlight
        card7_2_full.scale(sp7_scale).move_to([2.40, 1.24, 0]).set_z_index(14)
        card7_4.scale(sp7_scale).move_to([2.40, -1.22, 0]).set_z_index(14)

        self.play(
            card7_1.animate.scale(1.0 / sp7_scale).move_to(pos_c7_1).set_opacity(0.16).set_z_index(4),
            card7_3_full.animate.scale(1.0 / sp7_scale).move_to(pos_c7_3).set_opacity(0.16).set_z_index(4),
            FadeIn(card7_2_base, scale=0.92),
            FadeIn(card7_4, scale=0.92),
            run_time=1.15,
        )
        self.play(
            LaggedStart(*[FadeIn(sd, shift=RIGHT * 0.18 + DOWN * 0.12, scale=0.4) for sd in spill_dots], lag_ratio=0.05),
            Circumscribe(no_prem, color=C_CORAL, stroke_width=2.4, buff=0.04),
            run_time=1.05,
        )
        self.wait(2.20)

        # Dock Pair (②, ④) into final 2x2 diagnostic board
        self.play(
            card7_1.animate.set_opacity(1.0),
            card7_3_full.animate.set_opacity(1.0),
            card7_2_full.animate.scale(1.0 / sp7_scale).move_to(pos_c7_2).set_z_index(4),
            card7_4.animate.scale(1.0 / sp7_scale).move_to(pos_c7_4).set_z_index(4),
            run_time=0.95,
        )

        beat7a_all = VGroup(res_grp_7, vs_arr_7, card7_1, card7_2_full, card7_3_full, card7_4)
        self.check_bounds(beat7a_all, "CH7A ONTOLOGY DIAGNOSTIC")
        self.wait(2.60)

        # -------------------------------------------------------------------
        # Beat 7B: True 3D 3-Floor Vertical Elevator Fly-Through -> Pure 2D Three-Band Diagram
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 원천 사실과 표준 기준 위에, 빌드할 때 계산한 비교와 문장을 자료에 싣고 화면은 고른 조건의 값을 읽습니다",
            rt=0.45,
        )

        p3d_x = 1.50
        z_f1, z_f2, z_f3 = -1.12, 0.12, 1.36
        plane_fct_3d = glass_plane_3d(p3d_x, 0.0, z_f1, 5.65, 2.85, C_CYAN, fill_op=0.16, sw=2.2)
        plane_std_3d = glass_plane_3d(p3d_x, 0.0, z_f2, 5.65, 2.85, C_GOLD, fill_op=0.16, sw=2.2)
        plane_der_3d = glass_plane_3d(p3d_x, 0.0, z_f3, 5.65, 2.85, C_VIOLET, fill_op=0.16, sw=2.2)

        nodes_3d, edges_floor_3d, shafts_3d, pulses_3d = VGroup(), VGroup(), VGroup(), VGroup()
        shaft_xy = [
            (p3d_x - 2.05, -0.72, C_CYAN),
            (p3d_x - 0.68, 0.68, C_GOLD),
            (p3d_x + 0.68, -0.58, C_MINT),
            (p3d_x + 2.05, 0.62, C_VIOLET),
        ]
        for k in range(len(shaft_xy) - 1):
            x0, y0, _ = shaft_xy[k]
            x1, y1, _ = shaft_xy[k + 1]
            edges_floor_3d.add(
                Line([x0, y0, z_f1 + 0.08], [x1, y1, z_f1 + 0.08], color=C_CYAN, stroke_width=1.8, stroke_opacity=0.70),
                Line([x0, y0, z_f2 + 0.08], [x1, y1, z_f2 + 0.08], color=C_GOLD, stroke_width=2.0, stroke_opacity=0.84),
                Line([x0, y0, z_f3 + 0.08], [x1, y1, z_f3 + 0.08], color=C_VIOLET, stroke_width=2.0, stroke_opacity=0.84),
            )
        for sx, sy, scol in shaft_xy:
            shafts_3d.add(DashedLine([sx, sy, z_f1], [sx, sy, z_f3], dash_length=0.10, color=scol, stroke_width=2.2))
            nodes_3d.add(
                pillar_3d(sx, sy, 0.34, 0.34, 0.18, base_z=z_f1, col=C_CYAN, opacity=0.92, stroke_col=WHITE),
                pillar_3d(sx, sy, 0.32, 0.32, 0.22, base_z=z_f2, col=C_GOLD, opacity=0.94, stroke_col=WHITE).rotate(PI / 4, axis=OUT),
                pillar_3d(sx, sy, 0.36, 0.36, 0.24, base_z=z_f3, col=C_VIOLET, opacity=0.94, stroke_col=WHITE),
            )
            pulses_3d.add(Prism(dimensions=[0.22, 0.22, 0.22], fill_color=WHITE, fill_opacity=1.0, stroke_color=scol, stroke_width=1.6).move_to([sx, sy, z_f1]))

        bb_7b_f1 = fit(
            bb_badge(f"원천 사본: 화면 {num(site_org_cnt)}곳", f"급부 {num(ben_cnt_site)}건", fg=C_CYAN, bg="#060B11", border=C_CYAN, size=11.6, sub_size=10.2, sub_col=C_WHITE),
            max_w=2.40,
        ).move_to([p3d_x + 2.30, 0.55, z_f1 + 0.34])
        bb_7b_f2 = fit(
            bb_badge(f"표준담보 {num(cov_use)}개", f"{rel_kinds_str} 관계 {num(rel_cnt)}줄", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.6, sub_size=10.2, sub_col=C_DARK_INK),
            max_w=2.40,
        ).move_to([p3d_x + 2.30, 0.55, z_f2 + 0.34])
        bb_7b_f3 = fit(
            bb_badge("빌드 때 비교 계산", "단독 HTML, A4 카드", fg=WHITE, bg="#261E42", border=C_VIOLET, size=11.6, sub_size=10.2, sub_col=C_MINT),
            max_w=2.40,
        ).move_to([p3d_x + 2.30, 0.55, z_f3 + 0.36])
        bbs_7b = [bb_7b_f1, bb_7b_f2, bb_7b_f3]

        stack_3d_grp = VGroup(plane_fct_3d, plane_std_3d, plane_der_3d, edges_floor_3d, shafts_3d, nodes_3d)

        z_lbl_3d = VGroup(
            fit(pill("상단 계층: 비교, 인사이트 (빌드 때 계산해 자료에 싣고 화면은 읽음)", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.2), max_w=4.42).move_to([-4.06, 1.45, 0]),
            fit(pill(f"중간 계층: 표준 기준 (표준담보 {num(cov_use)}개, {rel_kinds_str} 관계)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.2), max_w=4.42).move_to([-4.06, 0.05, 0]),
            fit(pill(f"하단 계층: 원천 사실 (화면에 올린 {num(site_org_cnt)}개 회사와 시장 소식 사본)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.2), max_w=4.42).move_to([-4.06, -1.35, 0]),
        ).set_z_index(25)

        self.register_billboards(*bbs_7b)
        self.add_fixed_in_frame_mobjects(z_lbl_3d)
        self.cam_move(
            phi=60 * DEGREES,
            theta=-58 * DEGREES,
            zoom=0.92,
            center=[0.35, 0.0, 0.12],
            anims=[
                FadeOut(beat7a_all, shift=UP * 0.10),
                FadeIn(stack_3d_grp),
                FadeIn(VGroup(*bbs_7b)),
                FadeIn(z_lbl_3d, shift=RIGHT * 0.12),
            ],
            rt=1.45,
        )
        self.remove(beat7a_all)
        self.wait(1.60)

        self.add(pulses_3d)
        self.cam_move(
            phi=52 * DEGREES,
            theta=-26 * DEGREES,
            zoom=0.94,
            center=[0.35, 0.0, 0.25],
            anims=[*[MoveAlongPath(pulses_3d[k], Line([shaft_xy[k][0], shaft_xy[k][1], z_f1], [shaft_xy[k][0], shaft_xy[k][1], z_f3])) for k in range(len(shaft_xy))]],
            rt=2.20,
        )
        self.remove(pulses_3d, *pulses_3d)
        self.wait(2.20)

        def make_layer_band(y_c: float, h_b: float, col: str, fill_c: str, title_s: str, sub_s: str) -> tuple[RoundedRectangle, VGroup]:
            band = RoundedRectangle(corner_radius=0.08, width=11.90, height=h_b, fill_color=fill_c, fill_opacity=0.92, stroke_color=col, stroke_width=2.1).move_to([0.0, y_c, 0]).set_z_index(2)
            sep = Line([-3.25, y_c - h_b * 0.38, 0], [-3.25, y_c + h_b * 0.38, 0], color=col, stroke_width=1.6, stroke_opacity=0.70).set_z_index(4)
            hdr = fit(
                VGroup(txt(title_s, size=14.0, color=col, bold=True, z=7), txt(sub_s, size=11.2, color=C_INK_0, bold=True, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.06),
                max_w=2.48,
            ).move_to([-4.62, y_c, 0])
            return band, VGroup(sep, hdr)

        b_der, h_der = make_layer_band(1.62, 1.02, C_VIOLET, "#171528", "분석, 인사이트 계층", "빌드 때 계산, 화면은 읽음")
        d_n1 = pill("같은 심사유형 종형 대조", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=11.8, px=0.13, py=0.07).move_to([-1.85, 1.62, 0])
        d_n2 = pill("대응 특약과 지급조건 대조", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=11.8, px=0.13, py=0.07).move_to([1.25, 1.62, 0])
        d_n4 = pill("★ 영업 인사이트와 응대 카드", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=12.0, px=0.14, py=0.07).move_to([4.25, 1.62, 0])
        layer_der = VGroup(
            b_der, h_der, d_n1, d_n2, d_n4,
            arrow_2d(d_n1.get_right(), d_n2.get_left(), color=C_VIOLET, sw=2.0, tip=0.10, z=6),
            arrow_2d(d_n2.get_right(), d_n4.get_left(), color=C_GOLD, sw=2.0, tip=0.10, z=6),
        )

        b_std, h_std = make_layer_band(0.14, 1.10, C_GOLD, "#1E1B12", "표준 기준 계층", "특약과 심사기준 표준화")
        s_grade = pill("심사유형, 간편고지 등급 체계", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=11.6, px=0.12, py=0.07).move_to([-1.68, 0.14, 0])
        sd1 = Square(side_length=0.22, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.4).rotate(PI / 4).move_to([0.65, 0.34, 0]).set_z_index(7)
        sd2 = Square(side_length=0.20, fill_color=C_MINT, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([1.45, 0.46, 0]).set_z_index(7)
        sd3 = Square(side_length=0.20, fill_color=C_CYAN, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([1.45, 0.02, 0]).set_z_index(7)
        s_dag_grp = VGroup(
            Line(sd1.get_center(), sd2.get_center(), color=C_GOLD, stroke_width=2.2).set_z_index(6),
            Line(sd1.get_center(), sd3.get_center(), color=C_MINT, stroke_width=2.2).set_z_index(6),
            sd1, sd2, sd3,
            fit(txt(f"◆ 표준담보 {num(cov_use)}개 및 {rel_kinds_str} 관계", size=11.4, color=C_GOLD, bold=True, z=7), max_w=3.22).move_to([1.35, -0.24, 0]),
        )
        s_pay = pill(f"지급형태, 치료 {num(n_tr_stages)}단계 분류", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.6, px=0.12, py=0.07).move_to([4.32, 0.14, 0])
        layer_std = VGroup(b_std, h_std, s_grade, s_dag_grp, s_pay)

        b_fct, h_fct = make_layer_band(-1.38, 1.14, C_CYAN, "#101B24", "원천 사실 계층", f"화면 기준 {num(site_org_cnt)}개 회사 사본")
        f_org_s = RegularPolygon(n=6, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.4).scale(0.17).move_to([-2.48, -1.24, 0]).set_z_index(7)
        f_var_s = RoundedRectangle(corner_radius=0.04, width=0.32, height=0.28, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.4).move_to([-0.82, -1.24, 0]).set_z_index(7)
        f_rid_s = Circle(radius=0.15, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.4).move_to([1.00, -1.24, 0]).set_z_index(7)
        f_ben_s = Circle(radius=0.13, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.5).move_to([2.88, -1.24, 0]).set_z_index(7)
        f_nws_s = RegularPolygon(n=5, fill_color=C_VIOLET, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.4).scale(0.16).move_to([4.72, -1.24, 0]).set_z_index(7)
        layer_fct = VGroup(
            b_fct, h_fct, f_org_s, f_var_s, f_rid_s, f_ben_s, f_nws_s,
            txt(f"화면 {num(site_org_cnt)}개 기관", size=11.4, color=C_INK_0, bold=True, z=7).move_to([-2.48, -1.64, 0]),
            txt(f"{num(var_cnt_site)}개 상품 종형", size=11.4, color=C_INK_0, bold=True, z=7).move_to([-0.82, -1.64, 0]),
            txt(f"{num(rider_cnt_site)}개 특약", size=11.4, color=C_INK_0, bold=True, z=7).move_to([1.00, -1.64, 0]),
            txt(f"{num(ben_cnt_site)}건 세부 급부", size=11.4, color=C_GOLD, bold=True, z=7).move_to([2.88, -1.64, 0]),
            txt(f"시장 소식 {num(news_cnt)}건", size=11.4, color=C_VIOLET, bold=True, z=7).move_to([4.72, -1.64, 0]),
            arrow_2d(f_org_s.get_right(), f_var_s.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=6),
            arrow_2d(f_var_s.get_right(), f_rid_s.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=6),
            arrow_2d(f_rid_s.get_right(), f_ben_s.get_left(), color=C_GOLD, sw=2.0, tip=0.10, z=6),
            DashedLine(f_org_s.get_top() + UP * 0.04, f_nws_s.get_top() + UP * 0.04, dash_length=0.08, color=C_VIOLET, stroke_width=1.4).set_z_index(5),
        )

        up_coords = [
            ([-0.82, -0.80, 0], [-1.68, -0.40, 0], C_CYAN),
            ([2.88, -0.80, 0], [1.35, -0.40, 0], C_GOLD),
            ([2.88, -0.80, 0], [4.32, -0.40, 0], C_GOLD),
            ([-1.68, 0.70, 0], [-1.85, 1.12, 0], C_VIOLET),
            ([1.35, 0.70, 0], [1.25, 1.12, 0], C_MINT),
            ([4.32, 0.70, 0], [4.25, 1.12, 0], C_GOLD),
        ]
        cross_layer_arrows = VGroup(*[arrow_2d(p0, p1, color=col, sw=2.2, tip=0.12, z=8) for p0, p1, col in up_coords])
        foot_7b = fit(
            pill(
                f"정확성 원칙: 빌드할 때 코드가 비교와 문장을 계산하고, 공시에 없는 값(특약 보험료 {num(prem_rows)}행)은 추정 표시 제외 ✓",
                fg=C_MINT,
                bg=C_PANEL_HI,
                border=C_MINT,
                size=11.8,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.56, 0]).set_z_index(9)

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
            f"해결 ② 화면 대기 {num(ms_site['대기'])}건을 점선으로 구분하고, 사전을 {num(dict_init)}줄에서 {num(dict_exp2['before'])}줄, {num(cov_rows)}줄(사용 {num(cov_use)}개)로 넓혔습니다",
            rt=0.45,
        )

        G = nx.Graph()
        n_per_org, n_hubs = 15, 9
        total_v = n_per_org * site_org_cnt + n_hubs
        hub_start = n_per_org * site_org_cnt
        for h_i in range(n_hubs - 1):
            G.add_edge(hub_start + h_i, hub_start + h_i + 1)
        G.add_edge(hub_start, hub_start + 4)
        G.add_edge(hub_start + 1, hub_start + 6)
        G.add_edge(hub_start + 3, hub_start + 8)
        for c_idx in range(site_org_cnt):
            base = c_idx * n_per_org
            for k in range(1, 4):
                G.add_edge(base, base + k)
            for k in range(4, n_per_org):
                G.add_edge(base + 1 + ((k - 4) % 3), base + k)
                G.add_edge(base + k, hub_start + ((k * 2 + c_idx * 3) % n_hubs))

        raw_pos = nx.spring_layout(G, dim=3, seed=19, k=0.50, iterations=90)
        xs = np.array([raw_pos[i][0] for i in range(total_v)])
        ys = np.array([raw_pos[i][1] for i in range(total_v)])
        zs = np.array([raw_pos[i][2] for i in range(total_v)])
        xs = (xs - xs.mean()) / (xs.max() - xs.min() + 1e-6) * 9.8
        ys = (ys - ys.mean()) / (ys.max() - ys.min() + 1e-6) * 3.85 - 0.08
        zs = (zs - zs.mean()) / (zs.max() - zs.min() + 1e-6) * 3.10
        net_pts = {i: np.array([xs[i], ys[i], zs[i]]) for i in range(total_v)}

        radar_bg = VGroup(
            *[Circle(radius=rad, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=0.9, stroke_opacity=0.18).move_to([0, -0.08, 0]) for rad in [1.15, 2.30, 3.45, 4.65]],
            Line([-5.8, -0.08, 0], [5.8, -0.08, 0], color=C_CYAN, stroke_width=0.8, stroke_opacity=0.14),
            Line([0, -2.85, 0], [0, 2.75, 0], color=C_CYAN, stroke_width=0.8, stroke_opacity=0.14),
        ).set_z_index(1)

        hub_prisms = VGroup()
        billboard_nodes: list[Mobject] = []
        for i in range(total_v):
            pt = net_pts[i]
            if i >= hub_start:
                v_mob: Mobject = (
                    Prism(dimensions=[0.24, 0.24, 0.24], fill_color=C_GOLD, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.3)
                    .rotate(PI / 4, axis=OUT)
                    .rotate(PI / 5, axis=RIGHT)
                    .move_to(pt)
                )
                hub_prisms.add(v_mob)
            elif i % n_per_org == 0:
                c_col = C_GOLD if i == 0 else (C_CYAN if i == n_per_org else C_VIOLET)
                v_mob = RegularPolygon(n=6, fill_color=c_col, fill_opacity=0.96, stroke_color=WHITE, stroke_width=1.6).scale(0.18).move_to(pt)
                billboard_nodes.append(v_mob)
            else:
                c_col = C_GOLD if i < n_per_org else (C_CYAN if i < 2 * n_per_org else C_VIOLET)
                v_mob = Circle(radius=0.082, fill_color=c_col, fill_opacity=0.90, stroke_color=c_col, stroke_width=1.2).move_to(pt)
                billboard_nodes.append(v_mob)

        billboard_grp = VGroup(*billboard_nodes)

        bridge_pairs = [(u, v) for u, v in G.edges() if not ((u >= hub_start and v >= hub_start) or (u < hub_start and v < hub_start))]
        n_dashed_bridges = max(1, round(len(bridge_pairs) * (ms_site["대기"] / ben_cnt_site)))
        intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges = VGroup(), VGroup(), VGroup(), VGroup()
        bridge_counter = 0
        for u, v in G.edges():
            if u >= hub_start and v >= hub_start:
                dag_edges.add(Line(net_pts[u], net_pts[v], color=C_GOLD, stroke_width=2.4, stroke_opacity=0.94))
            elif u < hub_start and v < hub_start:
                intra_edges.add(Line(net_pts[u], net_pts[v], color=C_SLATE, stroke_width=1.2, stroke_opacity=0.56))
            else:
                bridge_counter += 1
                if bridge_counter <= n_dashed_bridges:
                    waiting_dashed_edges.add(DashedLine(net_pts[u], net_pts[v], dash_length=0.09, color=C_AMBER, stroke_width=2.0, stroke_opacity=0.95))
                else:
                    confirmed_bridge_edges.add(Line(net_pts[u], net_pts[v], color=C_MINT, stroke_width=1.5, stroke_opacity=0.76))

        build_banner = fit(
            pill(
                f"화면 {num(site_org_cnt)}개 회사 급부 {num(ben_cnt_site)}건 매핑(매핑 없는 급부 {num(no_map_cnt)}건): 자동확정 {num(ms_site['자동확정'])}건, 대상외 {num(ms_site['대상외'])}건, 대기 {num(ms_site['대기'])}건 (구조 예시 그림)",
                fg=C_GOLD,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=11.4,
            ),
            max_w=11.85,
        ).move_to([0, 2.70, 0]).set_z_index(25)
        build_legend = fit(
            VGroup(
                pill(f"◆ 포함 {num(rel_by_k['포함'])}, 통합 {num(rel_by_k['통합'])} (합계 {num(rel_cnt)}줄)", fg=C_GOLD, bg=C_PANEL, border=C_GOLD_DEEP, size=11.4),
                pill(f"●─● 자동확정 {num(ms_site['자동확정'])}건 (대상외 {num(ms_site['대상외'])}건)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=11.4),
                pill(f"●- -● 검토 대기 {num(ms_site['대기'])}건 (미보유 오판 방지)", fg=C_AMBER, bg=C_PANEL, border=C_AMBER, size=11.4),
            ).arrange(RIGHT, buff=0.14),
            max_w=11.85,
        ).move_to([0, -2.70, 0]).set_z_index(25)

        self.add_fixed_in_frame_mobjects(build_banner, build_legend)
        self.register_billboards(*billboard_nodes)

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
            rt=1.55,
        )
        self.remove(beat7b_all)

        self.cam_move(phi=48 * DEGREES, theta=-24 * DEGREES, zoom=1.04, center=[0.0, -0.05, 0.0], rt=2.60)
        self.wait(1.90)

        all_net_lines = VGroup(intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges)
        bg_cosmos = VGroup(radar_bg, all_net_lines, hub_prisms, billboard_grp)

        z1_card = RoundedRectangle(corner_radius=0.08, width=3.32, height=4.38, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.32, -0.05, 0]).set_z_index(4)
        z1_old = fit(pill(f"직전 개정 ({rev_old_no})", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=11.8, z=7), max_w=2.98).move_to([-4.32, 0.92, 0])
        z1_new = fit(pill(f"현행 개정 ({rev_new_no})", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=12.0, z=7), max_w=2.98).move_to([-4.32, -0.18, 0])
        exp_left = VGroup(
            z1_card,
            fit(txt("확장 ① 개정 계보와 비교 대상 확대", size=13.2, color=C_CYAN, bold=True, z=7), max_w=3.06).move_to([-4.32, 1.72, 0]),
            z1_old,
            z1_new,
            arrow_2d(z1_old.get_bottom(), z1_new.get_top(), color=C_GOLD, sw=2.4, tip=0.12, z=7),
            pill("특약계보키 연결", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=10.8, px=0.10, py=0.04, z=8).move_to([-4.32, 0.37, 0]),
            fit(pill(f"화면 {num(site_org_cnt)}곳(사본 {num(prod_org_cnt)}곳) -> 정한 대상 {num(target_total)}곳", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.4, z=7), max_w=3.06).move_to([-4.32, -0.88, 0]),
            fit(txt(f"대상은 총자산 기사 기준(공식 순위 미확정), 급부ID {num(inh_rows)}줄 지난 시험", size=9.4, color=C_INK_0, bold=True, z=7), max_w=3.08).move_to([-4.32, -1.62, 0]),
        )

        z2_card = RoundedRectangle(corner_radius=0.08, width=4.38, height=4.38, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_MINT, stroke_width=2.3).move_to([0.0, -0.05, 0]).set_z_index(4)
        z2_t = fit(txt(f"확장 ② 표준담보 사전 ({num(dict_init)} -> {num(dict_exp2['before'])} -> {num(cov_rows)}줄)", size=13.4, color=C_MINT, bold=True, z=7), max_w=4.10).move_to([0.0, 1.72, 0])
        z2_sub = fit(txt(f"{num(surv_orgs)}개 회사 요약서 급부 이름 조사 (약관 미대조, 사용 {num(cov_use)}개)", size=10.6, color=C_INK_0, bold=True, z=7), max_w=4.10).move_to([0.0, 1.28, 0])

        hub_centers_4c = [np.array([-1.22, 0.05, 0.0]), np.array([0.0, 0.35, 0.0]), np.array([1.22, 0.05, 0.0])]
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
            new_hub_lbls.add(fit(txt(h_nm, size=10.4, color=C_MINT if h_idx != 1 else C_GOLD, bold=True, z=9), max_w=1.56).move_to(hc + (DOWN * 0.72 if h_idx != 1 else UP * 0.64)))
        ex_diag_note = txt("(사전 수록 담보 연결 예시 그림)", size=9.2, color=C_INK_1, z=8).move_to([0.0, -1.08, 0])
        remap_ok = fit(
            pill(f"첫 확장 +{num(dict_add1)}줄({num(dict_exp2['before'])}줄), 둘째 확장 {num(cov_rows)}줄 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=11.0, z=9),
            max_w=4.10,
        ).move_to([0.0, -1.56, 0])

        z3_card = RoundedRectangle(corner_radius=0.08, width=3.32, height=4.38, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_VIOLET, stroke_width=2.0).move_to([4.32, -0.05, 0]).set_z_index(4)
        z3_rule1 = fit(pill(f"우체국 보유 또는 요약서 {num(add_rule['min_holder_orgs'])}개사 이상 보유", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.8, z=7), max_w=3.02).move_to([4.32, 0.85, 0])
        z3_rule2 = fit(pill("기존 담보와 같지 않을 때 사전에 추가", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=10.8, z=7), max_w=3.02).move_to([4.32, 0.02, 0])
        z3_todo = fit(pill("앞으로 할 일: 시장 소식과 후보 연결", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=10.6, z=7), max_w=3.02).move_to([4.32, -0.88, 0])
        exp_right = VGroup(
            z3_card,
            fit(txt("사전 추가 기준과 앞으로 할 일", size=13.2, color=C_VIOLET, bold=True, z=7), max_w=3.06).move_to([4.32, 1.72, 0]),
            z3_rule1,
            z3_rule2,
            z3_todo,
            arrow_2d(z3_rule1.get_bottom(), z3_rule2.get_top(), color=C_GOLD, sw=2.0, tip=0.10, z=6),
            fit(txt("시장 소식을 사전 후보로 자동 연결하는 기능은 미구현", size=9.8, color=C_INK_0, bold=True, z=7), max_w=3.06).move_to([4.32, -1.62, 0]),
        )

        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.44,
            center=[0.0, -0.05, 0],
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
        # 8장: 지식그래프 담보 분석과 응대 카드
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            fg_7c,
            hl,
            hr,
            hb,
            8,
            f"{rel_kinds_str} 관계 탐색과 실행: 담보 관계망부터 응대 카드까지",
            f"상대 회사는 통합특약 하나로, {org_names['EPOST']}은 분리특약 둘로 운영할 때 통합 관계로 대응 특약을 찾습니다",
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

        g8_floor = floor_grid_3d(-4.6, 4.6, -1.45, 1.45, z_val=-1.05, step_x=1.53, step_y=1.45, col=C_CYAN_DIM)

        # Upper 3D Inclusion Chain (z = +1.34, y = +1.08)
        inc_pts = [
            np.array([-3.22, 1.08, 1.34]),
            np.array([-1.08, 1.08, 1.34]),
            np.array([1.08, 1.08, 1.34]),
            np.array([3.22, 1.08, 1.34]),
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
                        size=11.4,
                        px=0.14,
                        py=0.07,
                    ),
                    max_w=2.06,
                ).move_to(ipt + OUT * 0.34)
            )
            if idx_i < len(inc_pts) - 1:
                inc_edges_3d.add(Line(inc_pts[idx_i], inc_pts[idx_i + 1], color=C_GOLD if idx_i == 0 else C_CYAN, stroke_width=2.4))

        # Main 3D Integration Bifurcation (X=탐색 단계, Y/Z=분리 특약 입체 분기)
        pt_peer = np.array([-4.08, -0.15, -0.15])
        pt_pben = np.array([-2.56, -0.15, -0.15])
        pt_hub = np.array([-1.05, -0.15, -0.15])
        pt_br = np.array([1.05, 0.78, 0.42])
        pt_ht = np.array([1.05, -0.92, -0.62])
        pt_ep1 = np.array([2.72, 0.78, 0.42])
        pt_ep2 = np.array([2.72, -0.92, -0.62])
        pt_epost = np.array([4.16, -0.15, -0.15])

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
            bb_badge(f"{peer_pair_str}", "통합특약 보유", fg=C_CYAN, bg="#060B11", border=C_CYAN, size=11.4, sub_size=10.0, sub_col=C_WHITE, px=0.14, py=0.07),
            max_w=2.30,
        ).move_to(pt_peer + OUT * 0.46)
        bb_hub = fit(
            bb_badge(f"◆ {nm_bs_surg}", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=12.0, px=0.15, py=0.08),
            max_w=2.30,
        ).move_to(pt_hub + OUT * 0.48)
        bb_br = fit(
            bb_badge(nm_bv_surg, fg=C_MINT, bg="#060B11", border=C_MINT, size=11.6, px=0.14, py=0.07),
            max_w=2.12,
        ).move_to(pt_br + OUT * 0.38)
        bb_ht = fit(
            bb_badge(nm_ht_surg, fg=C_MINT, bg="#060B11", border=C_MINT, size=11.6, px=0.14, py=0.07),
            max_w=2.12,
        ).move_to(pt_ht + OUT * 0.38)
        bb_ep1 = fit(
            bb_badge("우체국 분리특약①", fg=C_GOLD, bg="#060B11", border=C_GOLD, size=11.0, px=0.13, py=0.06),
            max_w=1.86,
        ).move_to(pt_ep1 + OUT * 0.36)
        bb_ep2 = fit(
            bb_badge("우체국 분리특약②", fg=C_GOLD, bg="#060B11", border=C_GOLD, size=11.0, px=0.13, py=0.06),
            max_w=1.86,
        ).move_to(pt_ep2 + OUT * 0.36)
        bb_epost = fit(
            bb_badge(f"우체국 {rev_new_no}", "분리 보유 확인 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.6, sub_size=10.2, sub_col=C_DARK_INK, px=0.14, py=0.07),
            max_w=2.36,
        ).move_to(pt_epost + OUT * 0.46)

        all_8a_bbs = [*inc_bbs, bb_peer, bb_hub, bb_br, bb_ht, bb_ep1, bb_ep2, bb_epost]
        graph_8a_3d = VGroup(
            g8_floor, inc_nodes_3d, inc_edges_3d,
            m_peer, m_pben, m_hub, m_br, m_ht, m_ep1, m_ep2, m_epost,
            e8_in1, e8_in2, e_hop1_a, e_hop1_b, e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b,
        )

        bad_arc_3d = DashedVMobject(
            CubicBezier(pt_hub, np.array([0.4, -1.1, -1.05]), np.array([2.7, -1.1, -1.05]), pt_epost, color=C_CORAL, stroke_width=3.0),
            num_dashes=24,
        )
        bad_1hop_lbl = fit(
            pill(f'단순 특약명 대조 시: "{nm_bs_surg} 특약이 없으니 미보유"로 오판 ×', fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.8, z=25),
            max_w=11.55,
        ).move_to([0.0, -2.54, 0])
        rel_cov = fact("relation_covered_coverages")
        hop_badge = fit(
            pill(
                f"포함 {num(rel_by_k['포함'])}건, 통합 {num(rel_by_k['통합'])}건 탐색 ✓: 기준 종형이 관계 담보로 덮는 표준담보 {num(rel_cov['count'])}개 (보유 담보 수에는 미포함, 직접 보유 아님)",
                fg=C_DARK_INK,
                bg=C_MINT,
                border=WHITE,
                size=11.0,
                z=25,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.54, 0])

        self.register_billboards(*all_8a_bbs)

        self.cam_move(
            phi=54 * DEGREES,
            theta=-74 * DEGREES,
            zoom=0.98,
            center=[0.0, -0.05, 0.10],
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
            zoom=1.02,
            center=[0.20, -0.05, 0.05],
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
            zoom=0.98,
            center=[0.15, -0.05, 0.05],
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
        # Beat 8B: Dynamic Spotlight Build -> Connected 2D Segment Map, Stages & Constraints
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
            f"고객군 지도 {num(seg_cells_n)}칸({base_var_name}), 치료 {num(n_tr_stages)}단계 보유 담보 막대, 결합 제약과 실제 지급액을 함께 분석합니다",
            rt=0.45,
        )

        pm_title = fit(
            txt(f"고객군 지도 요약 (전체 {num(len(seg_rows))}행×{num(len(seg_cols))}열={num(seg_cells_n)}칸, {base_var_name})", size=12.6, color=C_WHITE, bold=True, z=7),
            max_w=6.00,
        ).move_to([-3.05, 2.26, 0])

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
            ry = 1.25 - r_i * 0.78
            grp_n = len(grp)
            r_lbl = f"{grp[0]['row']} ({num(grp_n)}행)" if grp[0]["row"] == grp[-1]["row"] else f"{grp[0]['row']} ~ {grp[-1]['row']} ({num(grp_n)}행 묶음)"
            has_focus_in_row = any(c["label"] == seg_lbls[1] and c["gate_only"] for c in grp[0]["cells"])
            pm_cells.add(fit(txt(r_lbl, size=9.8, color=C_GOLD if has_focus_in_row else C_INK_0, bold=True, z=7), max_w=2.24).move_to([-5.12, ry, 0]))
            for c_i, c_info in enumerate(grp[0]["cells"]):
                cw_p = 1.48 if c_i == 0 else 2.28
                cx = -3.18 if c_i == 0 else -1.22
                cell_s = c_info["label"]
                is_open = cell_s in (seg_lbls[0], seg_lbls[1])
                is_gate = bool(c_info["gate_only"])
                is_hi = is_open and is_gate
                cell_r = RoundedRectangle(
                    corner_radius=0.05,
                    width=cw_p,
                    height=0.68,
                    fill_color="#383016" if is_hi else ("#182832" if is_open else C_PANEL_HI),
                    fill_opacity=0.96,
                    stroke_color=C_GOLD if is_hi else (C_AMBER if is_gate else (C_CYAN if is_open else C_SLATE)),
                    stroke_width=2.2 if is_hi else (1.7 if is_gate else 1.3),
                ).move_to([cx, ry, 0]).set_z_index(4)
                cell_col = C_GOLD if is_hi else (C_CYAN if is_open else C_INK_1)
                if is_gate:
                    ct = fit(txt(cell_s, size=10.0, color=cell_col, bold=True, z=7), max_w=cw_p - 0.14).move_to(cell_r.get_center() + UP * 0.14)
                    gt = fit(pill("관문전용 종형만 열림", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.4, px=0.06, py=0.02, z=8), max_w=cw_p - 0.14).move_to(cell_r.get_center() + DOWN * 0.16)
                    cell_grp = VGroup(cell_r, ct, gt)
                else:
                    ct = fit(txt(cell_s, size=10.4, color=cell_col, bold=is_open, z=7), max_w=cw_p - 0.14).move_to(cell_r)
                    cell_grp = VGroup(cell_r, ct)
                if is_hi:
                    focus_cell = cell_r
                pm_cells.add(cell_grp)

        pm_age_hdr = VGroup(
            txt(seg_cols[0], size=11.6, color=C_INK_1, bold=True, z=7).move_to([-3.18, 1.76, 0]),
            txt(seg_cols[1], size=11.6, color=C_INK_0, bold=True, z=7).move_to([-1.22, 1.76, 0]),
        )
        pm_foot = fit(
            txt(
                f"라벨 합계: 함께 열림 {num(seg_open_tog)}칸, 우리 간편 닫힘 {num(seg_closed)}칸, 우리 간편만 열림 {num(seg_ours_only)}칸 | 별도 집계: 관문전용 종형으로만 열린 칸 {num(seg_gate_only)}칸",
                size=9.6,
                color=C_INK_0,
                bold=True,
                z=7,
            ),
            max_w=6.20,
        ).move_to([-3.05, -1.62, 0])

        assert focus_cell is not None
        pin_pt = focus_cell.get_right() + LEFT * 0.20 + UP * 0.14
        target_cursor = VGroup(
            Circle(radius=0.15, fill_opacity=0.0, stroke_color=WHITE, stroke_width=2.4).move_to(pin_pt),
            Line(pin_pt + LEFT * 0.22, pin_pt + RIGHT * 0.22, color=WHITE, stroke_width=1.6),
            Line(pin_pt + DOWN * 0.22, pin_pt + UP * 0.22, color=WHITE, stroke_width=1.6),
            Dot(pin_pt, radius=0.045, color=C_GOLD),
        ).set_z_index(10)
        phase_map_grp = VGroup(pm_title, pm_age_hdr, pm_cells, pm_foot, target_cursor)

        cj_title = fit(txt(f"치료 {num(n_tr_stages)}단계별 보유 담보 수 (합계 {num(held_total)}개)", size=13.2, color=C_WHITE, bold=True, z=7), max_w=5.38).move_to([3.25, 2.26, 0])
        stage_cols = [C_CYAN, C_CYAN, C_MINT, C_GOLD, C_CORAL]
        cj_bars, cj_nodes = VGroup(), VGroup()
        cj_base_y = 0.44
        for s_i, s_nm in enumerate(tr_stages):
            s_cnt = held_by_stage[s_nm]
            s_col = stage_cols[s_i % len(stage_cols)]
            sx = 1.05 + s_i * 1.10
            slot_bg = RoundedRectangle(
                corner_radius=0.05, width=0.86, height=1.38, fill_color=C_PANEL_HI, fill_opacity=0.94,
                stroke_color=C_CORAL if s_cnt == 0 else C_SLATE, stroke_width=2.0 if s_cnt == 0 else 1.2,
            ).move_to([sx, cj_base_y + 0.69, 0]).set_z_index(3)
            if s_cnt > 0:
                bh = (s_cnt / max_stage_cnt) * 0.80
                bar = RoundedRectangle(corner_radius=0.04, width=0.58, height=bh, fill_color=s_col, fill_opacity=0.90, stroke_color=WHITE, stroke_width=1.1).move_to([sx, cj_base_y + 0.10 + bh / 2, 0]).set_z_index(5)
                cj_bars.add(VGroup(slot_bg, bar, txt(f"{num(s_cnt)}개", size=11.6, color=WHITE, bold=True, z=7).move_to([sx, cj_base_y + 0.10 + bh + 0.19, 0])))
            else:
                cj_bars.add(
                    VGroup(
                        slot_bg,
                        txt(f"{num(s_cnt)}개", size=13.4, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + UP * 0.13),
                        txt("미보유 구간", size=9.8, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + DOWN * 0.28),
                    )
                )
            cj_nodes.add(txt(s_nm, size=11.4, color=C_CORAL if s_cnt == 0 else C_INK_0, bold=True, z=7).move_to([sx, cj_base_y - 0.20, 0]))

        cj_links = VGroup(
            *[Line([1.05 + i * 1.10 + 0.45, cj_base_y + 0.69, 0], [1.05 + (i + 1) * 1.10 - 0.45, cj_base_y + 0.69, 0], color=C_CORAL if i == n_tr_stages - 2 else C_GOLD, stroke_width=2.4).set_z_index(6) for i in range(n_tr_stages - 1)]
        )
        care_journey_grp = VGroup(cj_title, cj_bars, cj_nodes, cj_links)

        rc_box = RoundedRectangle(corner_radius=0.07, width=5.38, height=1.88, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_SLATE, stroke_width=1.6).move_to([3.25, -1.18, 0]).set_z_index(3)
        nd_main = fit(pill(f"● 주계약 한도 {num(main_lim_mw)}만", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=10.6, px=0.09, py=0.05, z=7), max_w=1.64).move_to([1.48, -1.10, 0])
        nd_rider = fit(pill(f"● 기준 {num(basis_mw)}만에 지급 {num(pay_new_mw)}만", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.2, px=0.09, py=0.05, z=7), max_w=1.88).move_to([3.30, -1.10, 0])
        nd_excl = fit(pill(f"● 결합 제약 {num(comb_cnt)}건", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.6, px=0.09, py=0.05, z=7), max_w=1.44).move_to([5.10, -1.10, 0])
        constraint_grp = VGroup(
            rc_box,
            fit(txt("특약 결합 제약 및 실제 지급액 계산", size=12.4, color=C_GOLD, bold=True, z=7), max_w=5.06).move_to([3.25, -0.52, 0]),
            nd_main, nd_rider, nd_excl,
            arrow_2d(nd_main.get_right(), nd_rider.get_left(), color=C_MINT, sw=2.0, tip=0.09, z=7),
            DashedLine(nd_rider.get_right(), nd_excl.get_left(), dash_length=0.06, color=C_CORAL, stroke_width=2.0).set_z_index(6),
            fit(txt("주계약 연동 한도와 선행, 동시 가입 불가 규칙 반영 ✓", size=10.8, color=C_INK_0, bold=True, z=7), max_w=5.06).move_to([3.25, -1.72, 0]),
        )
        beat8b_all = VGroup(phase_map_grp, care_journey_grp, constraint_grp)

        # Step 1: Spotlight directly onto the left Segment Map and dynamically build its cells
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.34,
            center=[-3.05, 0.30, 0],
            anims=[
                FadeOut(graph_8a_3d),
                FadeOut(VGroup(*all_8a_bbs)),
                FadeOut(hop_badge),
                FadeIn(pm_title),
                FadeIn(pm_age_hdr),
                LaggedStart(*[FadeIn(c, shift=UP * 0.06) for c in pm_cells], lag_ratio=0.04),
                FadeIn(pm_foot, shift=UP * 0.06),
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
        self.wait(2.30)

        # Step 2: Spotlight onto the right Treatment Stages & Combination Constraints and animate stage flow
        self.cam_move(
            zoom=1.32,
            center=[3.25, 0.30, 0],
            anims=[
                FadeIn(cj_title, shift=DOWN * 0.06),
                LaggedStart(*[FadeIn(b, shift=UP * 0.10) for b in cj_bars], lag_ratio=0.10),
                FadeIn(cj_nodes),
                Create(cj_links, lag_ratio=0.10),
            ],
            rt=1.25,
        )
        cj_pulse = glow_dot([1.05, cj_base_y + 0.69, 0], color=C_GOLD, r=0.07, z=13)
        self.add(cj_pulse)
        self.play(
            MoveAlongPath(cj_pulse, Line([1.05, cj_base_y + 0.69, 0], [1.05 + (n_tr_stages - 1) * 1.10, cj_base_y + 0.69, 0])),
            Circumscribe(cj_bars[-1][0], color=C_CORAL, stroke_width=2.4, buff=0.04),
            Wiggle(cj_bars[-1][1], scale_value=1.18, rotation_angle=0.05 * TAU),
            FadeIn(constraint_grp, shift=UP * 0.10),
            run_time=1.25,
        )
        self.remove(cj_pulse)
        self.wait(2.30)

        # Step 3: Pull back to connect the full 2D synthesis chart
        self.reset_cam_2d(rt=1.00)
        self.check_bounds(beat8b_all, "CH8B PHASE & CARE CHARTS")
        self.wait(3.20)

        # -------------------------------------------------------------------
        # Beat 8C: Pure 2D 5 Sales Insight Categories -> Console & A4 Card
        # -------------------------------------------------------------------
        ins_cats = fact("sales_insight_categories")
        n_ins_cats = len(ins_cats)
        ins_by_cat = fact("sales_insight_by_category")
        ins_total = fact("sales_insight_count")
        card_ord = fact("card_category_order")
        lead_str = fact("lead_strengths")
        q_diff_peers = fact("gate_question_diff_peer_count")
        var_gen_name = fact("base_variants", 3, "name")
        var_gen_def_cnt = fact("briefing_by_base_variant", var_gen_name, "insights", "by_category", ins_cats[3])
        forb_cnt = len(fact("forbidden_words"))

        hb = self.update_subtitle(
            hb,
            f"분석 결과가 영업 인사이트 {num(n_ins_cats)}분류(합계 {num(ins_total)}건, {base_var_name})와 창구용 A4 한 장 응대 카드로 정리됩니다",
            rt=0.45,
        )

        def make_ins_card(cx: float, cy: float, w_c: float, h_c: float, col: str, title_s: str, desc_s: str) -> VGroup:
            box = RoundedRectangle(corner_radius=0.08, width=w_c, height=h_c, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=col, stroke_width=2.2).move_to([cx, cy, 0]).set_z_index(4)
            t_blk = fit(
                VGroup(
                    txt(title_s, size=12.8, color=col, bold=True, z=7),
                    txt(desc_s, size=10.8, color=WHITE, bold=True, z=7),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.11),
                max_w=w_c - 0.36,
            ).move_to([cx, cy, 0])
            return VGroup(box, t_blk)

        c_ins1 = make_ins_card(
            -3.85, 1.56, 3.88, 1.50, C_GOLD,
            f"① {ins_cats[0]} ({num(ins_by_cat[ins_cats[0]])}건)",
            f"고지 질문이 다른 상대 {num(q_diff_peers)}곳 비교 (우리 간편만 열림 {num(seg_ours_only)}칸)",
        )
        c_ins2 = make_ins_card(
            0.0, 1.56, 3.60, 1.50, C_MINT,
            f"② {ins_cats[1]} ({num(ins_by_cat[ins_cats[1]])}건)",
            f"대표 담보: {lead_str}",
        )
        c_ins3 = make_ins_card(
            3.85, 1.56, 3.88, 1.50, C_VIOLET,
            f"③ {ins_cats[2]} ({num(ins_by_cat[ins_cats[2]])}건)",
            f"{rel_kinds_str} 관계의 분리 특약과 상위 특약 연결 안내",
        )
        c_ins4 = make_ins_card(
            -2.95, -1.28, 5.20, 1.54, C_CYAN,
            f"④ {ins_cats[3]} (기준 {num(ins_by_cat[ins_cats[3]])}건, {var_gen_name} {num(var_gen_def_cnt)}건)",
            "감액 기간 경과 뒤 전액 지급 조건과 미단정 사유 분리",
        )
        c_ins5 = make_ins_card(
            2.95, -1.28, 5.20, 1.54, C_CORAL,
            f"⑤ {ins_cats[4]} ({num(ins_by_cat[ins_cats[4]])}건)",
            f"입원 {num(held_by_stage['입원'])}개 대비 통원 {num(held_by_stage['통원'])}개 등 미보유 담보 정리",
        )

        comp_c = np.array([0.0, 0.08, 0.0])
        comp_ring = Circle(radius=0.48, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.8).move_to(comp_c).set_z_index(10)
        comp_needle = Line(comp_c + DOWN * 0.36, comp_c + UP * 0.36, color=C_GOLD, stroke_width=2.8).rotate(PI / 4).set_z_index(12)
        comp_txt = fit(txt(f"{num(n_ins_cats)}분류", size=11.0, color=WHITE, bold=True, z=13), max_w=0.78).move_to(comp_c)
        compass_hub = VGroup(comp_ring, comp_needle, comp_txt)
        five_insights = VGroup(c_ins1, c_ins2, c_ins3, c_ins4, c_ins5, compass_hub)

        self.add(comp_needle)
        self.play(
            FadeOut(beat8b_all, scale=0.94),
            FadeIn(VGroup(comp_ring, comp_txt), scale=0.6),
            Rotate(comp_needle, angle=-TAU, about_point=comp_c),
            LaggedStart(*[FadeIn(q, shift=UP * 0.12) for q in [c_ins1, c_ins2, c_ins3, c_ins4, c_ins5]], lag_ratio=0.12),
            run_time=1.45,
        )
        self.remove(beat8b_all)
        self.wait(2.60)

        app_window = RoundedRectangle(corner_radius=0.10, width=8.05, height=4.75, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_INK_1, stroke_width=2.2).move_to([-2.05, -0.15, 0]).set_z_index(1)
        app_win_hdr = fit(pill("본부 상품, 영업지원 판단 화면 (오프라인 단독 HTML)", fg=WHITE, bg=C_PANEL_HI, border=C_SLATE, size=12.2), max_w=7.60).move_to([-2.05, 1.92, 0]).set_z_index(8)
        tpl_bar = fit(pill(f"금지 표현 {num(forb_cnt)}개 빌드 차단 ✓, 근거 문서와 쪽수를 함께 보임", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=11.6, px=0.14, py=0.07, z=8), max_w=7.60).move_to([-2.05, -1.32, 0])
        nlq_bar = fit(pill("앞으로 할 일(다음 버전): 자연어 조건 검색 입력 연동", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=11.4, px=0.14, py=0.07, z=8), max_w=7.60).move_to([-2.05, -1.98, 0])

        a4_box = Rectangle(width=2.98, height=4.75, fill_color=C_IVORY, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.4).move_to([4.48, -0.15, 0]).set_z_index(5)
        a4_top_bar = Line(a4_box.get_corner(UL), a4_box.get_corner(UR), color=C_CORAL, stroke_width=5.2).set_z_index(7)
        a4_badge = pill("대외 배포 금지, A4 한 장", fg=WHITE, bg=C_CORAL, border=C_CORAL, size=11.4).move_to([4.48, 1.82, 0]).set_z_index(7)
        a4_title = fit(txt("창구, 설계사 응대 카드", size=15.2, color=C_DARK_INK, bold=True, z=7), max_w=2.72).move_to([4.48, 1.34, 0])
        ord_cols = [C_GOLD_DEEP, "#1E6B7B", "#2D3748", "#4C3B78", "#8C3A3A"]
        circled_nums = ["①", "②", "③", "④", "⑤"]
        mini_cards = VGroup()
        for idx_c, c_cat in enumerate(card_ord):
            mb = RoundedRectangle(corner_radius=0.04, width=2.60, height=0.47, fill_color="#E5E4DC", fill_opacity=1.0, stroke_color="#C4C2B6", stroke_width=1.1).set_z_index(6)
            m_bar = Rectangle(width=0.11, height=0.47, fill_color=ord_cols[idx_c % len(ord_cols)], fill_opacity=1.0, stroke_width=0).move_to(mb.get_left() + RIGHT * 0.055).set_z_index(7)
            c_cnt = ins_by_cat[c_cat]
            mini_cards.add(
                VGroup(
                    mb,
                    m_bar,
                    fit(txt(f"{circled_nums[idx_c]} {c_cat} ({num(c_cnt)}건)", size=11.2, color=C_DARK_INK, bold=True, z=7), max_w=2.28).move_to(mb.get_center() + RIGHT * 0.05),
                )
            )
        mini_cards.arrange(DOWN, buff=0.085).move_to([4.48, -0.22, 0])
        a4_foot = Rectangle(width=2.98, height=0.48, fill_color=C_DARK_INK, fill_opacity=1.0, stroke_width=0).move_to(a4_box.get_bottom() + UP * 0.24).set_z_index(6)
        a4_foot_t = fit(txt("본부 판단 -> 현장 A4 한 장 전달", size=11.6, color=C_GOLD, bold=True, z=7), max_w=2.74).move_to(a4_foot)
        proj_beam = arrow_2d([2.04, -0.15, 0], [2.92, -0.15, 0], color=C_GOLD, sw=3.4, tip=0.18, z=8)
        a4_full = VGroup(a4_box, a4_top_bar, a4_badge, a4_title, mini_cards, a4_foot, a4_foot_t)

        a4_laser = Line([2.98, 2.15, 0], [5.98, 2.15, 0], color=C_GOLD, stroke_width=3.8).set_z_index(12)
        self.add(a4_laser)
        self.cam_move(
            zoom=1.32,
            center=[3.25, -0.15, 0],
            anims=[
                five_insights.animate.scale(0.42).move_to([-2.05, 0.52, 0]),
                FadeIn(app_window),
                FadeIn(app_win_hdr),
                FadeIn(tpl_bar, shift=UP * 0.08),
                FadeIn(nlq_bar, shift=UP * 0.08),
                GrowArrow(proj_beam),
                FadeIn(VGroup(a4_box, a4_top_bar, a4_title)),
                a4_laser.animate.move_to([4.48, -2.45, 0]),
                FadeIn(a4_badge, scale=1.2),
                LaggedStart(*[FadeIn(mc, shift=DOWN * 0.06) for mc in mini_cards], lag_ratio=0.10),
                FadeIn(VGroup(a4_foot, a4_foot_t)),
            ],
            rt=1.55,
        )
        self.remove(a4_laser)
        self.wait(2.00)
        self.reset_cam_2d(rt=0.95)

        ch8_stage = VGroup(app_window, app_win_hdr, five_insights, tpl_bar, nlq_bar, proj_beam, a4_full)
        self.check_bounds(ch8_stage, "CH8C CONSOLE & CARD")
        self.wait(3.40)

        # ===================================================================
        # 9장: 손으로 하던 방식과 이 앱으로 바뀐 점 (Dynamic Lane-by-Lane Build -> Full Chart)
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
        nym_list = fact("not_yet_measured")

        hl, hr, hb = self.switch_hud(
            ch8_stage,
            hl,
            hr,
            hb,
            9,
            "손으로 하던 방식과 이 앱으로 만든 구조",
            "수작업 대조에서 자동 수집, 검증, 단독 화면으로 바뀐 구조와 아직 재지 못한 과제를 함께 정리합니다",
        )

        col_hdr_before = pill("손으로 하던 방식", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=12.0, z=8).move_to([-4.32, 2.66, 0])
        col_hdr_after = pill("이 앱으로 (개념검증 구현 결과)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=12.0, z=8).move_to([2.16, 2.66, 0])

        def make_ba_lane(ly: float, b_title: str, b_vis: VGroup, tag_s: str, a_col: str, a_title: str, a_widgets: VGroup) -> tuple[VGroup, VGroup, VGroup]:
            bc = RoundedRectangle(corner_radius=0.08, width=3.64, height=1.26, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=1.9).move_to([-4.32, ly, 0]).set_z_index(4)
            bt = fit(txt(b_title, size=11.0, color=C_CORAL, bold=True, z=7), max_w=3.40).move_to([-4.32, ly + 0.38, 0])
            b_vis = fit(b_vis, max_w=3.38).move_to([-4.32, ly - 0.18, 0]).set_z_index(7)

            arr = arrow_2d([-2.42, ly, 0], [-1.56, ly, 0], color=a_col, sw=3.0, tip=0.15, z=7)
            albl = pill(tag_s, fg=C_DARK_INK, bg=a_col, border=WHITE, size=9.8, px=0.09, py=0.04, z=8).move_to([-1.99, ly + 0.35, 0])

            ac = RoundedRectangle(corner_radius=0.08, width=7.26, height=1.26, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=a_col, stroke_width=2.3).move_to([2.16, ly, 0]).set_z_index(5)
            at = fit(txt(a_title, size=11.4, color=a_col, bold=True, z=7), max_w=6.92).move_to([2.16, ly + 0.38, 0])
            a_widgets = fit(a_widgets, max_w=6.92).move_to([2.16, ly - 0.18, 0]).set_z_index(8)
            return VGroup(bc, bt, b_vis), VGroup(arr, albl), VGroup(ac, at, a_widgets)

        bv1 = VGroup(
            pill("문장 속 조건 대조", fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=9.6, px=0.08, py=0.04),
            pill("회사별 표기 상이", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.6, px=0.08, py=0.04),
        ).arrange(RIGHT, buff=0.10)

        ic_rad9_ring = Circle(radius=0.20, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_CYAN, stroke_width=1.9)
        ic_rad9_hand = Line([0, 0, 0], [0.14, 0.13, 0], color=C_GOLD, stroke_width=2.4)
        ic_rad9 = VGroup(ic_rad9_ring, ic_rad9_hand)
        ic_scr9 = RoundedRectangle(corner_radius=0.04, width=0.58, height=0.38, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.7)
        ic_a4_9 = VGroup(Rectangle(width=0.30, height=0.42, fill_color=C_IVORY, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.5), Line([-0.15, 0.21, 0], [0.15, 0.21, 0], color=C_CORAL, stroke_width=2.6))
        log_pill_9 = pill(f"화면 작업 로그 {num(wlog_site)}건", fg=C_GOLD, bg="#383016", border=C_GOLD, size=10.0, px=0.09, py=0.04)
        aw1 = VGroup(
            ic_rad9,
            txt(f"{num(news_inst_cnt)}개 기관, 운영비 {num(op_cost)}원(무료 설계)", size=10.0, color=C_CYAN, bold=True),
            log_pill_9,
            ic_scr9,
            arrow_2d([0, 0, 0], [0.24, 0, 0], color=C_GOLD, sw=2.0, tip=0.09),
            ic_a4_9,
            txt("A4 한 장", size=10.0, color=C_WHITE, bold=True),
        ).arrange(RIGHT, buff=0.10)
        b_l1, t_l1, a_l1 = make_ba_lane(
            1.36, "수백 쪽 공시 문서를 손으로 대조하는 부담", bv1, "구축 ✓", C_CYAN,
            f"① 정본 {num(sheet_tabs)}탭, 단독 HTML 화면, 창구 A4 한 장 응대 카드 구축", aw1,
        )
        ic_rad9_hand.set_z_index(11)

        bv2 = VGroup(
            Rectangle(width=0.30, height=0.38, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.5),
            txt(f"{num(img_pages)}쪽 그림 ×", size=9.8, color=C_CORAL, bold=True),
            txt(",", size=11, color=C_SLATE),
            txt("특약명 ≠", size=10.0, color=C_AMBER, bold=True),
        ).arrange(RIGHT, buff=0.08)

        aw2 = VGroup(
            pill(
                f"그림 {num(img_pages)}쪽: 두 판독 지급률, 금액 어긋남 {num(img_mismatches)}곳 (두 판독 일치)",
                fg=C_MINT,
                bg=C_BG_SUB,
                border=C_MINT,
                size=10.0,
                px=0.10,
                py=0.05,
            ),
            pill(
                f"일부러 뒤집은 {num(cal_flip['rows'])}줄 통과 {num(cal_flip['passed'])}줄 (우체국 요약서 좁은 표본)",
                fg=C_GOLD,
                bg="#383016",
                border=C_GOLD,
                size=10.0,
                px=0.10,
                py=0.05,
            ),
        ).arrange(RIGHT, buff=0.14)
        b_l2, t_l2, a_l2 = make_ba_lane(
            0.00, "그림 요약서와 회사마다 다른 특약 이름", bv2, "해결 ✓", C_GOLD,
            f"② 원문과 코드 분리 + 두 판독 교차 + {decide_model} + 표준담보 {num(cov_use)}개({rel_kinds_str} 관계)", aw2,
        )

        bv3 = VGroup(
            Dot([0, 0, 0], radius=0.07, color=C_AMBER),
            txt("대기=미보유 착시 위험", size=9.6, color=C_AMBER, bold=True),
            RegularPolygon(n=3, fill_color="#3D2B0D", fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.5).scale(0.16),
            txt("단정, 추정 주의", size=9.6, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.08)

        ic_sep9 = VGroup(Line([0, -0.16, 0], [0, 0.16, 0], color=C_MINT, stroke_width=2.4), DashedLine([0.14, -0.16, 0], [0.14, 0.16, 0], dash_length=0.06, color=C_AMBER, stroke_width=2.2))
        ic_shd9 = VGroup(RegularPolygon(n=6, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.9).scale(0.19), txt("✓", size=10.2, color=C_MINT, bold=True))
        aw3 = VGroup(
            ic_sep9,
            txt(f"화면 대기 {num(ms_site['대기'])}건, 미단정 {num(no_verd_sum)}쌍 분리", size=10.0, color=C_AMBER, bold=True),
            ic_shd9,
            txt(f"금지 표현 {num(forb_cnt)}개 차단, 보험료 추정 제외", size=10.0, color=C_MINT, bold=True),
            pill(f"근거 쪽수, 인사이트 {num(n_ins_cats)}분류 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=10.0, px=0.09, py=0.04),
        ).arrange(RIGHT, buff=0.12)
        b_l3, t_l3, a_l3 = make_ba_lane(
            -1.36, "매핑 대기 착시 위험과 단정, 추정 표현 주의", bv3, "보강 ✓", C_MINT,
            "③ 매핑 대기와 우열 미단정 분리 + 공시 부재 추정 차단 + 근거 문서와 쪽수 표시", aw3,
        )

        before_cards = VGroup(b_l1, b_l2, b_l3)
        trans_arrows = VGroup(t_l1, t_l2, t_l3)
        after_cards = VGroup(a_l1, a_l2, a_l3)

        finale_ribbon = fit(
            pill(
                f"점검: 자동 시험 {num(test_cnt)}개(발표 전 pytest로 재측정), 브라우저 점검 문제 {num(br_problems)}건, 보험료({num(prem_rows)}행)와 질병코드({num(dis_rows)}행) 탭은 비어 있음(다음 단계 과제)",
                fg=C_GOLD,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=11.0,
                z=9,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.38, 0])
        nym_ribbon = fit(
            txt(f"아직 재지 못한 성과: {', '.join(nym_list)}", size=10.0, color=C_INK_1, bold=True, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.86, 0])

        # Dynamic Lane ① Spotlight: Before -> Arrow Pulse -> After
        pulse9_1 = glow_dot([-2.42, 1.36, 0], color=C_CYAN, r=0.065, z=12)
        self.add(pulse9_1, ic_rad9_hand)
        self.cam_move(
            zoom=1.15,
            center=[0.0, 1.48, 0],
            anims=[
                FadeIn(col_hdr_before, shift=DOWN * 0.08),
                FadeIn(col_hdr_after, shift=DOWN * 0.08),
                FadeIn(b_l1, shift=RIGHT * 0.14),
                FadeIn(t_l1, scale=0.9),
                MoveAlongPath(pulse9_1, Line([-2.42, 1.36, 0], [-1.56, 1.36, 0])),
                FadeIn(VGroup(a_l1[0], a_l1[1], ic_rad9_ring, *aw1[1:]), shift=LEFT * 0.12),
                Rotate(ic_rad9_hand, angle=-TAU, about_point=ic_rad9_ring.get_center()),
            ],
            rt=1.50,
        )
        self.remove(pulse9_1)
        self.wait(2.20)

        # Dynamic Lane ② Spotlight: Before -> Arrow Pulse -> After
        pulse9_2 = glow_dot([-2.42, 0.00, 0], color=C_GOLD, r=0.065, z=12)
        self.add(pulse9_2)
        self.cam_move(
            zoom=1.15,
            center=[0.0, 0.12, 0],
            anims=[
                FadeIn(b_l2, shift=RIGHT * 0.14),
                FadeIn(t_l2, scale=0.9),
                MoveAlongPath(pulse9_2, Line([-2.42, 0.00, 0], [-1.56, 0.00, 0])),
                FadeIn(a_l2, shift=LEFT * 0.12),
            ],
            rt=1.45,
        )
        self.remove(pulse9_2)
        self.wait(2.20)

        # Dynamic Lane ③ Spotlight: Before -> Arrow Pulse -> After
        pulse9_3 = glow_dot([-2.42, -1.36, 0], color=C_MINT, r=0.065, z=12)
        self.add(pulse9_3)
        self.cam_move(
            zoom=1.15,
            center=[0.0, -1.08, 0],
            anims=[
                FadeIn(b_l3, shift=RIGHT * 0.14),
                FadeIn(t_l3, scale=0.9),
                MoveAlongPath(pulse9_3, Line([-2.42, -1.36, 0], [-1.56, -1.36, 0])),
                FadeIn(a_l3, shift=LEFT * 0.12),
                Flash(ic_shd9.get_center(), color=C_MINT, line_length=0.24, num_lines=8),
            ],
            rt=1.45,
        )
        self.remove(pulse9_3)
        self.wait(2.20)

        # Pull back to connect the complete 3-lane Before/After synthesis chart + Finale Ribbons
        self.reset_cam_2d(
            anims=[
                FadeIn(finale_ribbon, shift=UP * 0.06),
                FadeIn(nym_ribbon, shift=UP * 0.04),
                LaggedStart(*[Circumscribe(ac[0], color=C_GOLD, stroke_width=2.2, buff=0.03) for ac in after_cards], lag_ratio=0.12),
            ],
            rt=1.05,
        )

        ch9_stage = VGroup(col_hdr_before, col_hdr_after, before_cards, trans_arrows, after_cards, finale_ribbon, nym_ribbon)
        self.check_bounds(ch9_stage, "CH9 VISUAL BEFORE AFTER")
        self.wait(4.80)
