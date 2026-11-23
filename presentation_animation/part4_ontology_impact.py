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
    fact,
    fit,
    glow_dot,
    num,
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
            "회사별 특약 이름 불일치, 매핑 대기 줄, 통합과 분리 구조 차이, 보험료 자료 부재를 함께 풀었습니다",
        )

        # -------------------------------------------------------------------
        # Beat 7A: 2-Stop Obstacle Tour
        # -------------------------------------------------------------------
        res_box_7 = RoundedRectangle(
            corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=2.0
        ).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_7 = pill("정본과 배포 조건", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.8, z=7).move_to([-4.38, 1.92, 0])

        rg7_1 = capacity_ring([-5.15, 0.72, 0], 0.58, C_GOLD, "운영 비용", f"{num(op_cost)}원 (무료 설계)", z=6)
        rg7_2 = capacity_ring([-3.62, 0.72, 0], 0.58, C_CYAN, "구글 시트 정본", f"{num(sheet_tabs)}탭", z=6)

        html_pill_7 = fit(pill("사본 자료를 실은 HTML 한 파일", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.4, z=7), max_w=3.02).move_to([-4.38, -0.78, 0])
        res_sub_7 = fit(txt(f"브라우저 점검 문제, 외부 요청 {num(br_problems)}건", size=9.0, color=C_INK_2, z=7), max_w=3.02).move_to([-4.38, -1.48, 0])
        res_grp_7 = VGroup(res_box_7, res_hdr_7, rg7_1, rg7_2, html_pill_7, res_sub_7)
        vs_arr_7 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=1.9).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=10.4, color=col, bold=True, z=7), max_w=3.44).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        q7_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 종형명, 특약명, 지급방식 상이")
        m7_l1 = fit(pill(base_var_name, fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.2, px=0.07, py=0.03), max_w=1.52).move_to([-1.05, 1.32, 0]).set_z_index(7)
        m7_r1_c = fit(pill(peer0_name, fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.0, px=0.07, py=0.03), max_w=1.58).move_to([0.88, 1.32, 0]).set_z_index(7)
        m7_l2 = pill("수술 회당 지급", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.4, px=0.07, py=0.03).move_to([-1.05, 0.80, 0]).set_z_index(7)
        m7_r2_c = pill("연간 한 번 지급", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.4, px=0.07, py=0.03).move_to([0.88, 0.80, 0]).set_z_index(7)
        m7_neqs = VGroup(
            txt("≠", size=14, color=C_CORAL, bold=True).move_to([-0.10, 1.32, 0]),
            txt("≠", size=14, color=C_CORAL, bold=True).move_to([-0.10, 0.80, 0]),
        ).set_z_index(7)
        q7_1_cap = fit(txt("단순 문자열과 금액 비교 불가능", size=8.8, color=C_INK_1, z=7), max_w=3.44).move_to([-0.10, 0.42, 0])

        q7_2 = diag_frame(3.88, 1.18, C_CORAL, f"문제 ② 처음 {num(dict_init)}개 사전과 한화 매핑 대기")
        cup_52 = VMobject(color=C_GOLD, stroke_width=2.2).set_z_index(7)
        cup_52.set_points_as_corners([[2.35, 1.38, 0], [2.35, 0.82, 0], [3.45, 0.82, 0], [3.45, 1.38, 0]])
        fun_lbl = txt(f"사전 {num(dict_init)}개", size=8.4, color=C_GOLD, bold=True, z=7).move_to([2.90, 1.06, 0])
        spill_dots = VGroup(
            *[Dot([3.78 + (k % 6) * 0.25, 1.38 - (k // 6) * 0.28, 0], radius=0.052, color=C_AMBER if k % 2 == 0 else C_CORAL) for k in range(12)]
        ).set_z_index(7)
        spill_tag = txt("(예시 그림)", size=7.4, color=C_INK_2, z=7).move_to([5.02, 0.82, 0])
        q7_2_cap = fit(
            txt(f"재추출 전 대기 {num(hw_pend_b['rows'])}줄({num(hw_pend_b['kinds'])}종류), 재추출 뒤 {num(hw_pend_a)}줄 대기", size=8.2, color=C_CORAL, bold=True, z=7),
            max_w=3.50,
        ).move_to([3.88, 0.44, 0])

        q7_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 통합 대 분리 오판, 대기 건 착시")
        int_chip = pill("상대 통합특약 ◆", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.4, px=0.08, py=0.03).move_to([-1.06, -1.04, 0]).set_z_index(7)
        int_arr = arrow_2d([-0.30, -1.04, 0], [0.16, -1.04, 0], color=C_CORAL, sw=1.8, tip=0.08, z=7)
        false_stamp = pill("미보유 오판 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.4, px=0.07, py=0.03).move_to([0.92, -1.04, 0]).set_z_index(7)
        q7_3_cap = fit(txt("우체국 분리특약 누락 위험, 매핑 대기를 미보유로 오인", size=8.6, color=C_INK_1, z=7), max_w=3.46).move_to([-0.10, -1.74, 0])

        q7_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 공시 문서에 특약별 보험료 부재")
        no_prem = DashedVMobject(RoundedRectangle(corner_radius=0.05, width=3.18, height=0.58, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=1.6).move_to([3.88, -1.06, 0]), num_dashes=22).set_z_index(6)
        no_prem_t = fit(txt(f"특약별 보험료 예시: 사본 {num(prem_rows)}행 (다음 단계 과제)", size=8.6, color=C_CORAL, bold=True, z=7), max_w=2.98).move_to([3.88, -1.06, 0])
        q7_4_cap = fit(txt("요약서와 사업방법서에 특약 보험료가 없어 추정 표시 제외", size=8.4, color=C_INK_1, z=7), max_w=3.46).move_to([3.88, -1.72, 0])

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(res_grp_7, shift=RIGHT * 0.12),
                GrowArrow(vs_arr_7),
                FadeIn(VGroup(q7_1, m7_l1, m7_r1_c, m7_l2, m7_r2_c, m7_neqs, q7_1_cap)),
                FadeIn(VGroup(q7_2, cup_52, fun_lbl, spill_tag, q7_2_cap)),
                FadeIn(VGroup(q7_3, int_chip, q7_3_cap)),
                FadeIn(VGroup(q7_4, no_prem, no_prem_t, q7_4_cap)),
            ],
            rt=1.10,
        )

        self.cam_move(
            zoom=1.38,
            center=[-0.10, 0.02, 0],
            anims=[
                GrowArrow(int_arr),
                FadeIn(false_stamp, scale=1.35),
                Flash(false_stamp.get_center(), color=C_CORAL, line_length=0.20, num_lines=8),
            ],
            rt=0.90,
        )
        self.play(
            m7_l1.animate.shift(RIGHT * 0.12),
            m7_r1_c.animate.shift(LEFT * 0.12),
            m7_l2.animate.shift(RIGHT * 0.12),
            m7_r2_c.animate.shift(LEFT * 0.12),
            rate_func=there_and_back,
            run_time=0.50,
        )
        self.wait(0.60)

        self.cam_move(
            zoom=1.40,
            center=[3.88, 0.02, 0],
            anims=[
                LaggedStart(*[FadeIn(sd, shift=RIGHT * 0.18 + DOWN * 0.12, scale=0.4) for sd in spill_dots], lag_ratio=0.04),
                Circumscribe(no_prem, color=C_CORAL, stroke_width=2.0, buff=0.03),
            ],
            rt=1.00,
        )
        self.wait(0.65)
        self.reset_cam_2d(rt=0.80)

        beat7a_all = VGroup(
            res_grp_7, vs_arr_7,
            q7_1, m7_l1, m7_r1_c, m7_l2, m7_r2_c, m7_neqs, q7_1_cap,
            q7_2, cup_52, fun_lbl, spill_dots, spill_tag, q7_2_cap,
            q7_3, int_chip, int_arr, false_stamp, q7_3_cap,
            q7_4, no_prem, no_prem_t, q7_4_cap,
        )
        self.check_bounds(beat7a_all, "CH7A ONTOLOGY DIAGNOSTIC")
        self.wait(1.30)

        # -------------------------------------------------------------------
        # Beat 7B: 3D Stacked Layers -> 2D Three-Band Diagram
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 원천 사실과 표준 기준 위에, 빌드할 때 계산한 비교와 문장을 자료에 싣고 화면은 고른 조건의 값을 읽습니다",
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
            fit(pill("상단 계층: 비교, 인사이트 (빌드 때 계산해 자료에 싣고 화면은 읽음)", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=10.0), max_w=4.42).move_to([-4.05, 1.45, 0]),
            fit(pill(f"중간 계층: 표준 기준 (표준담보 {num(cov_use)}개, {rel_kinds_str} 관계)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.0), max_w=4.42).move_to([-4.05, 0.05, 0]),
            fit(pill(f"하단 계층: 원천 사실 (화면에 올린 {num(site_org_cnt)}개 회사와 시장 소식 사본)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.0), max_w=4.42).move_to([-4.05, -1.35, 0]),
        ).set_z_index(25)

        self.add_fixed_in_frame_mobjects(z_lbl_3d)
        self.cam_move(
            phi=60 * DEGREES,
            theta=-52 * DEGREES,
            zoom=0.96,
            center=[0.25, 0.0, 0.0],
            anims=[FadeOut(beat7a_all, shift=UP * 0.10), FadeIn(stack_3d_grp), FadeIn(z_lbl_3d, shift=RIGHT * 0.10)],
            rt=1.15,
        )
        self.remove(beat7a_all)

        self.add(pulses_3d)
        self.cam_move(
            phi=56 * DEGREES,
            theta=-34 * DEGREES,
            zoom=0.98,
            center=[0.25, 0.0, 0.0],
            anims=[*[MoveAlongPath(pulses_3d[k], Line([shaft_xy[k][0], shaft_xy[k][1], -1.25], [shaft_xy[k][0], shaft_xy[k][1], 1.25])) for k in range(len(shaft_xy))]],
            rt=1.15,
        )
        self.remove(pulses_3d, *pulses_3d)
        self.wait(0.55)

        def make_layer_band(y_c: float, h_b: float, col: str, fill_c: str, title_s: str, sub_s: str) -> tuple[RoundedRectangle, VGroup]:
            band = RoundedRectangle(corner_radius=0.08, width=11.90, height=h_b, fill_color=fill_c, fill_opacity=0.90, stroke_color=col, stroke_width=2.0).move_to([0.0, y_c, 0]).set_z_index(2)
            sep = Line([-3.25, y_c - h_b * 0.38, 0], [-3.25, y_c + h_b * 0.38, 0], color=col, stroke_width=1.4, stroke_opacity=0.65).set_z_index(4)
            hdr = fit(
                VGroup(txt(title_s, size=13.0, color=col, bold=True, z=7), txt(sub_s, size=10.0, color=C_INK_1, z=7)).arrange(DOWN, aligned_edge=LEFT, buff=0.05),
                max_w=2.44,
            ).move_to([-4.62, y_c, 0])
            return band, VGroup(sep, hdr)

        b_der, h_der = make_layer_band(1.62, 1.00, C_VIOLET, "#171528", "분석, 인사이트 계층", "빌드 때 계산, 화면은 읽음")
        d_n1 = pill("같은 심사유형 종형 대조", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=10.8, px=0.11, py=0.06).move_to([-1.85, 1.62, 0])
        d_n2 = pill("대응 특약과 지급조건 대조", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=10.8, px=0.11, py=0.06).move_to([1.25, 1.62, 0])
        d_n4 = pill("★ 영업 인사이트와 응대 카드", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.0, px=0.12, py=0.06).move_to([4.25, 1.62, 0])
        layer_der = VGroup(
            b_der, h_der, d_n1, d_n2, d_n4,
            arrow_2d(d_n1.get_right(), d_n2.get_left(), color=C_VIOLET, sw=1.8, tip=0.10, z=6),
            arrow_2d(d_n2.get_right(), d_n4.get_left(), color=C_GOLD, sw=1.8, tip=0.10, z=6),
        )

        b_std, h_std = make_layer_band(0.14, 1.08, C_GOLD, "#1E1B12", "표준 기준 계층", "특약과 심사기준 표준화")
        s_grade = pill("심사유형, 간편고지 등급 체계", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.6, px=0.10, py=0.06).move_to([-1.68, 0.14, 0])
        sd1 = Square(side_length=0.20, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.3).rotate(PI / 4).move_to([0.65, 0.34, 0]).set_z_index(7)
        sd2 = Square(side_length=0.18, fill_color=C_MINT, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.2).rotate(PI / 4).move_to([1.45, 0.46, 0]).set_z_index(7)
        sd3 = Square(side_length=0.18, fill_color=C_CYAN, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.2).rotate(PI / 4).move_to([1.45, 0.02, 0]).set_z_index(7)
        s_dag_grp = VGroup(
            Line(sd1.get_center(), sd2.get_center(), color=C_GOLD, stroke_width=2.0).set_z_index(6),
            Line(sd1.get_center(), sd3.get_center(), color=C_MINT, stroke_width=2.0).set_z_index(6),
            sd1, sd2, sd3,
            fit(txt(f"◆ 표준담보 {num(cov_use)}개 및 {rel_kinds_str} 관계", size=10.4, color=C_GOLD, bold=True, z=7), max_w=3.20).move_to([1.35, -0.24, 0]),
        )
        s_pay = pill(f"지급형태, 치료 {num(n_tr_stages)}단계 분류", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.6, px=0.10, py=0.06).move_to([4.32, 0.14, 0])
        layer_std = VGroup(b_std, h_std, s_grade, s_dag_grp, s_pay)

        b_fct, h_fct = make_layer_band(-1.38, 1.12, C_CYAN, "#101B24", "원천 사실 계층", "화면 기준 세 회사 사본")
        f_org_s = RegularPolygon(n=6, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).scale(0.16).move_to([-2.48, -1.24, 0]).set_z_index(7)
        f_var_s = RoundedRectangle(corner_radius=0.04, width=0.30, height=0.26, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).move_to([-0.82, -1.24, 0]).set_z_index(7)
        f_rid_s = Circle(radius=0.14, fill_color=C_CYAN, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).move_to([1.00, -1.24, 0]).set_z_index(7)
        f_ben_s = Circle(radius=0.12, fill_color=C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.4).move_to([2.88, -1.24, 0]).set_z_index(7)
        f_nws_s = RegularPolygon(n=5, fill_color=C_VIOLET, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.3).scale(0.15).move_to([4.72, -1.24, 0]).set_z_index(7)
        layer_fct = VGroup(
            b_fct, h_fct, f_org_s, f_var_s, f_rid_s, f_ben_s, f_nws_s,
            txt(f"화면 {num(site_org_cnt)}개 기관", size=10.4, color=C_INK_0, bold=True, z=7).move_to([-2.48, -1.64, 0]),
            txt(f"{num(var_cnt_site)}개 상품 종형", size=10.4, color=C_INK_0, bold=True, z=7).move_to([-0.82, -1.64, 0]),
            txt(f"{num(rider_cnt_site)}개 특약", size=10.4, color=C_INK_0, bold=True, z=7).move_to([1.00, -1.64, 0]),
            txt(f"{num(ben_cnt_site)}건 세부 급부", size=10.4, color=C_GOLD, bold=True, z=7).move_to([2.88, -1.64, 0]),
            txt(f"시장 소식 {num(news_cnt)}건", size=10.4, color=C_VIOLET, bold=True, z=7).move_to([4.72, -1.64, 0]),
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
            pill(
                f"정확성 원칙: 빌드할 때 코드가 비교와 문장을 계산하고, 공시에 없는 값(특약 보험료 {num(prem_rows)}행)은 추정 표시 제외 ✓",
                fg=C_MINT,
                bg=C_PANEL_HI,
                border=C_MINT,
                size=10.6,
            ),
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
            rt=0.95,
        )
        self.remove_fixed_in_frame_mobjects(z_lbl_3d)
        self.remove(stack_3d_grp, z_lbl_3d)
        self.play(Circumscribe(d_n4[0], color=WHITE, stroke_width=2.2, buff=0.04), run_time=0.50)

        beat7b_all = VGroup(layer_fct, layer_std, layer_der, cross_layer_arrows, foot_7b)
        self.check_bounds(beat7b_all, "CH7B THREE LAYERS")
        self.wait(1.50)

        # -------------------------------------------------------------------
        # Beat 7C: 3D Knowledge-Graph Constellation & Dictionary Expansion
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"해결 ② 화면 대기 {num(ms_site['대기'])}건을 점선으로 구분하고, 사전을 {num(dict_init)}줄에서 {num(dict_exp2['before'])}줄, {num(cov_rows)}줄(사용 {num(cov_use)}개)로 넓혔습니다",
            rt=0.40,
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
            *[Circle(radius=rad, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=0.8, stroke_opacity=0.16).move_to([0, -0.08, 0]) for rad in [1.15, 2.30, 3.45, 4.65]],
            Line([-5.8, -0.08, 0], [5.8, -0.08, 0], color=C_CYAN, stroke_width=0.7, stroke_opacity=0.12),
            Line([0, -2.85, 0], [0, 2.75, 0], color=C_CYAN, stroke_width=0.7, stroke_opacity=0.12),
        ).set_z_index(1)

        hub_prisms = VGroup()
        billboard_nodes: list[Mobject] = []
        for i in range(total_v):
            pt = net_pts[i]
            if i >= hub_start:
                v_mob: Mobject = (
                    Prism(dimensions=[0.22, 0.22, 0.22], fill_color=C_GOLD, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.2)
                    .rotate(PI / 4, axis=OUT)
                    .rotate(PI / 5, axis=RIGHT)
                    .move_to(pt)
                )
                hub_prisms.add(v_mob)
            elif i % n_per_org == 0:
                c_col = C_GOLD if i == 0 else (C_CYAN if i == n_per_org else C_VIOLET)
                v_mob = RegularPolygon(n=6, fill_color=c_col, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.5).scale(0.16).move_to(pt)
                billboard_nodes.append(v_mob)
            else:
                c_col = C_GOLD if i < n_per_org else (C_CYAN if i < 2 * n_per_org else C_VIOLET)
                v_mob = Circle(radius=0.076, fill_color=c_col, fill_opacity=0.88, stroke_color=c_col, stroke_width=1.1).move_to(pt)
                billboard_nodes.append(v_mob)

        billboard_grp = VGroup(*billboard_nodes)

        bridge_pairs = [(u, v) for u, v in G.edges() if not ((u >= hub_start and v >= hub_start) or (u < hub_start and v < hub_start))]
        n_dashed_bridges = max(1, round(len(bridge_pairs) * (ms_site["대기"] / ben_cnt_site)))
        intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges = VGroup(), VGroup(), VGroup(), VGroup()
        bridge_counter = 0
        for u, v in G.edges():
            if u >= hub_start and v >= hub_start:
                dag_edges.add(Line(net_pts[u], net_pts[v], color=C_GOLD, stroke_width=2.2, stroke_opacity=0.92))
            elif u < hub_start and v < hub_start:
                intra_edges.add(Line(net_pts[u], net_pts[v], color=C_SLATE, stroke_width=1.1, stroke_opacity=0.52))
            else:
                bridge_counter += 1
                if bridge_counter <= n_dashed_bridges:
                    waiting_dashed_edges.add(DashedLine(net_pts[u], net_pts[v], dash_length=0.09, color=C_AMBER, stroke_width=1.8, stroke_opacity=0.92))
                else:
                    confirmed_bridge_edges.add(Line(net_pts[u], net_pts[v], color=C_MINT, stroke_width=1.4, stroke_opacity=0.72))

        build_banner = fit(
            pill(
                f"화면 세 회사 급부 {num(ben_cnt_site)}건 매핑(매핑 없는 급부 {num(no_map_cnt)}건): 자동확정 {num(ms_site['자동확정'])}건, 대상외 {num(ms_site['대상외'])}건, 대기 {num(ms_site['대기'])}건 (구조 예시 그림)",
                fg=C_GOLD,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=10.4,
            ),
            max_w=11.85,
        ).move_to([0, 2.70, 0]).set_z_index(25)
        build_legend = fit(
            VGroup(
                pill(f"◆ 포함 {num(rel_by_k['포함'])}, 통합 {num(rel_by_k['통합'])} (합계 {num(rel_cnt)}줄)", fg=C_GOLD, bg=C_PANEL, border=C_GOLD_DEEP, size=10.4),
                pill(f"●─● 자동확정 {num(ms_site['자동확정'])}건 (대상외 {num(ms_site['대상외'])}건)", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=10.4),
                pill(f"●- -● 검토 대기 {num(ms_site['대기'])}건 (미보유 오판 방지)", fg=C_AMBER, bg=C_PANEL, border=C_AMBER, size=10.4),
            ).arrange(RIGHT, buff=0.12),
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
            rt=1.20,
        )
        self.remove(beat7b_all)

        self.cam_move(phi=48 * DEGREES, theta=-24 * DEGREES, zoom=1.04, center=[0.0, -0.05, 0.0], rt=1.80)

        all_net_lines = VGroup(intra_edges, dag_edges, confirmed_bridge_edges, waiting_dashed_edges)
        site_peers_n = site_org_cnt - 1
        z1_card = RoundedRectangle(corner_radius=0.08, width=3.30, height=4.35, fill_color=C_PANEL, fill_opacity=0.88, stroke_color=C_CYAN, stroke_width=1.9).move_to([-4.32, -0.05, 0]).set_z_index(4)
        z1_old = fit(pill(f"직전 개정 ({rev_old_no})", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=10.8, z=7), max_w=2.95).move_to([-4.32, 0.92, 0])
        z1_new = fit(pill(f"현행 개정 ({rev_new_no})", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.0, z=7), max_w=2.95).move_to([-4.32, -0.18, 0])
        exp_left = VGroup(
            z1_card,
            fit(txt("확장 ① 개정 계보와 비교 대상 확대", size=12.4, color=C_CYAN, bold=True, z=7), max_w=3.02).move_to([-4.32, 1.72, 0]),
            z1_old,
            z1_new,
            arrow_2d(z1_old.get_bottom(), z1_new.get_top(), color=C_GOLD, sw=2.2, tip=0.12, z=7),
            pill("특약계보키 연결", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=9.8, px=0.09, py=0.03, z=8).move_to([-4.32, 0.37, 0]),
            fit(pill(f"우체국과 상대 {num(site_peers_n)}곳 -> 대상 {num(target_total)}곳 (사본 {num(prod_org_cnt)}곳)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=9.6, z=7), max_w=3.02).move_to([-4.32, -0.92, 0]),
            fit(txt(f"바뀐 문서만 다시 뽑음 (급부ID {num(inh_rows)}줄은 지난 자료 시험)", size=8.8, color=C_INK_1, z=7), max_w=3.02).move_to([-4.32, -1.62, 0]),
        )

        z2_card = RoundedRectangle(corner_radius=0.08, width=4.36, height=4.35, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_MINT, stroke_width=2.2).move_to([0.0, -0.05, 0]).set_z_index(4)
        z2_t = fit(txt(f"확장 ② 표준담보 사전 ({num(dict_init)} -> {num(dict_exp2['before'])} -> {num(cov_rows)}줄)", size=12.4, color=C_MINT, bold=True, z=7), max_w=4.05).move_to([0.0, 1.72, 0])
        z2_sub = fit(txt(f"{num(surv_orgs)}개 회사 요약서 급부 이름 조사 (약관 미대조, 사용 {num(cov_use)}개)", size=9.4, color=C_INK_1, z=7), max_w=4.04).move_to([0.0, 1.28, 0])

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
                drift_dots.add(Dot(np.array([rng_4c.uniform(-1.65, 1.65), rng_4c.uniform(-0.85, 0.78), 0.0]), radius=0.068, color=C_AMBER).set_z_index(8))
                remap_edges.add(Line(hc, t_pt, color=C_MINT, stroke_width=1.8).set_z_index(6))

        new_hubs_4c, new_hub_lbls = VGroup(), VGroup()
        for h_idx, (hc, h_nm) in enumerate(zip(hub_centers_4c, hub_names_4c)):
            new_hubs_4c.add(Square(side_length=0.24, fill_color=C_MINT if h_idx != 1 else C_GOLD, fill_opacity=1.0, stroke_color=WHITE, stroke_width=1.5).rotate(PI / 4).move_to(hc).set_z_index(9))
            new_hub_lbls.add(fit(txt(h_nm, size=9.2, color=C_MINT if h_idx != 1 else C_GOLD, bold=True, z=9), max_w=1.52).move_to(hc + (DOWN * 0.72 if h_idx != 1 else UP * 0.64)))
        ex_diag_note = txt("(사전 수록 담보 연결 예시 그림)", size=8.0, color=C_INK_2, z=8).move_to([0.0, -1.08, 0])
        remap_ok = fit(
            pill(f"첫 확장 +{num(dict_add1)}줄({num(dict_exp2['before'])}줄, 한 줄 미사용), 둘째 확장 {num(cov_rows)}줄 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=9.8, z=9),
            max_w=4.06,
        ).move_to([0.0, -1.56, 0])

        z3_card = RoundedRectangle(corner_radius=0.08, width=3.30, height=4.35, fill_color=C_PANEL, fill_opacity=0.88, stroke_color=C_VIOLET, stroke_width=1.9).move_to([4.32, -0.05, 0]).set_z_index(4)
        z3_rule1 = fit(pill(f"우체국 보유 또는 요약서 {num(add_rule['min_holder_orgs'])}개사 이상 보유", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=9.8, z=7), max_w=2.98).move_to([4.32, 0.85, 0])
        z3_rule2 = fit(pill("기존 담보와 같지 않을 때 사전에 추가", fg=C_MINT, bg=C_PANEL_HI, border=C_MINT, size=9.8, z=7), max_w=2.98).move_to([4.32, 0.02, 0])
        z3_todo = fit(pill("앞으로 할 일: 시장 소식과 후보 연결", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=9.6, z=7), max_w=2.98).move_to([4.32, -0.88, 0])
        exp_right = VGroup(
            z3_card,
            fit(txt("사전 추가 기준과 앞으로 할 일", size=12.4, color=C_VIOLET, bold=True, z=7), max_w=3.02).move_to([4.32, 1.72, 0]),
            z3_rule1,
            z3_rule2,
            z3_todo,
            arrow_2d(z3_rule1.get_bottom(), z3_rule2.get_top(), color=C_GOLD, sw=1.8, tip=0.10, z=6),
            fit(txt("시장 소식을 사전 후보로 자동 연결하는 기능은 미구현", size=8.8, color=C_INK_1, z=7), max_w=3.02).move_to([4.32, -1.62, 0]),
        )

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
                FadeIn(VGroup(z2_card, z2_t, z2_sub, drift_dots, ex_diag_note), scale=0.92),
            ],
            rt=0.90,
        )
        self.remove_fixed_in_frame_mobjects(build_banner, build_legend)
        self.remove(build_banner, build_legend)

        self.play(
            FadeIn(new_hubs_4c, scale=0.25),
            FadeIn(new_hub_lbls),
            *[drift_dots[idx].animate.move_to(target_positions_4c[idx]).set_color(C_GOLD if (idx // 4) == 1 else C_MINT) for idx in range(12)],
            Create(remap_edges, lag_ratio=0.02),
            Flash(hub_centers_4c[0], color=C_MINT, line_length=0.20, num_lines=8),
            Flash(hub_centers_4c[1], color=C_GOLD, line_length=0.24, num_lines=8),
            Flash(hub_centers_4c[2], color=C_MINT, line_length=0.20, num_lines=8),
            FadeIn(remap_ok, shift=UP * 0.08),
            run_time=1.10,
        )
        self.wait(0.65)

        self.reset_cam_2d(
            anims=[FadeIn(exp_left, shift=RIGHT * 0.14), FadeIn(exp_right, shift=LEFT * 0.14)],
            rt=0.85,
        )

        bg_cosmos = VGroup(radar_bg, all_net_lines, hub_prisms, billboard_grp)
        fg_7c = VGroup(exp_left, z2_card, z2_t, z2_sub, drift_dots, new_hubs_4c, new_hub_lbls, remap_edges, ex_diag_note, remap_ok, exp_right)
        self.check_bounds(fg_7c, "CH7C EXPANSION")
        self.wait(1.60)

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
        # Beat 8A: Inclusion & Integration Relation Graph Traversal
        # -------------------------------------------------------------------
        def graph_hub(label: str, pos: list[float], col: str = C_GOLD, r: float = 0.22, lbl_dir: np.ndarray = DOWN) -> VGroup:
            dm = Square(side_length=r * 1.5, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.5).rotate(PI / 4).move_to(pos).set_z_index(8)
            core = Square(side_length=r * 0.55, fill_color=col, fill_opacity=1.0, stroke_width=0).rotate(PI / 4).move_to(pos).set_z_index(9)
            lb = pill(label, fg=col, bg=C_BG_SUB, border=col, size=11.4, px=0.11, py=0.05, z=9).next_to(dm, lbl_dir, buff=0.11)
            return VGroup(dm, core, lb)

        def graph_entity(label: str, sub: str, pos: list[float], col: str, is_square: bool = True) -> VGroup:
            if is_square:
                sh: Mobject = RoundedRectangle(corner_radius=0.07, width=1.68, height=0.68, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).move_to(pos).set_z_index(8)
                tg = fit(VGroup(txt(label, size=11.6, color=WHITE, bold=True, z=9), txt(sub, size=9.8, color=col, z=9)).arrange(DOWN, buff=0.04), max_w=1.52).move_to(pos)
                return VGroup(sh, tg)
            sh = Circle(radius=0.31, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=col, stroke_width=2.3).move_to(pos).set_z_index(8)
            return VGroup(sh, txt(label, size=10.6, color=WHITE, bold=True, z=9).move_to(pos), txt(sub, size=9.8, color=col, bold=True, z=9).next_to(sh, DOWN, buff=0.09))

        diag_covs = std_names["진단"]
        nm_bs_diag = next(nm for nm in diag_covs if nm == "뇌·심장질환 진단비")
        nm_bv_diag = next(nm for nm in diag_covs if nm == "뇌혈관질환 진단비")
        nm_st_diag = next(nm for nm in diag_covs if nm == "뇌졸중 진단비")
        nm_hm_diag = next(nm for nm in diag_covs if nm == "뇌출혈 진단비")

        cv1 = pill(f"◆ {nm_bs_diag}", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.2, px=0.10, py=0.05, z=8).move_to([-2.05, 2.22, 0])
        cv2 = pill(f"◆ {nm_bv_diag}", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.2, px=0.10, py=0.05, z=8).move_to([0.20, 2.22, 0])
        cv3 = pill(f"◆ {nm_st_diag}", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.2, px=0.10, py=0.05, z=8).move_to([2.25, 2.22, 0])
        cv4 = pill(f"◆ {nm_hm_diag}", fg=C_WHITE, bg=C_PANEL_HI, border=C_WHITE, size=10.2, px=0.10, py=0.05, z=8).move_to([4.12, 2.22, 0])
        top_chain_grp = VGroup(
            fit(txt("포함 관계 예:", size=11.4, color=C_GOLD, bold=True, z=9), max_w=2.10).move_to([-4.62, 2.22, 0]),
            cv1, cv2, cv3, cv4,
            arrow_2d(cv1.get_right(), cv2.get_left(), color=C_GOLD, sw=2.0, tip=0.10, z=8),
            arrow_2d(cv2.get_right(), cv3.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=8),
            arrow_2d(cv3.get_right(), cv4.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=8),
        )

        surg_covs = std_names["수술"]
        nm_bs_surg = next(nm for nm in surg_covs if nm == "뇌·심장질환 수술비")
        nm_bv_surg = next(nm for nm in surg_covs if nm == "뇌혈관질환 수술비")
        nm_ht_surg = next(nm for nm in surg_covs if nm == "심장질환 수술비")
        peer_pair_str = ", ".join(org_names[o] for o in fact("site_orgs") if o != "EPOST")

        n_peer_rider = graph_entity(peer_pair_str, "통합형 특약 운영", [-5.05, -0.25, 0], C_CYAN, is_square=True)
        n_peer_ben = graph_entity("특약", "통합수술", [-3.35, -0.25, 0], C_CYAN, is_square=False)
        h_integrated = graph_hub(nm_bs_surg, [-1.45, -0.25, 0], C_GOLD, r=0.25, lbl_dir=UP)
        sel_ring = DashedVMobject(Circle(radius=0.52, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.0).move_to([-1.45, -0.25, 0]), num_dashes=24).set_z_index(7)
        h_part_br = graph_hub(nm_bv_surg, [0.85, 0.72, 0], C_MINT, r=0.21, lbl_dir=UP)
        h_part_ht = graph_hub(nm_ht_surg, [0.85, -1.22, 0], C_MINT, r=0.21, lbl_dir=DOWN)
        n_ep_ben1 = graph_entity("특약①", "우체국 운영", [2.95, 0.72, 0], C_GOLD, is_square=False)
        n_ep_ben2 = graph_entity("특약②", "우체국 운영", [2.95, -1.22, 0], C_GOLD, is_square=False)
        n_ep_prod = graph_entity(f"우체국 {rev_new_no}", "분리 특약 보유", [4.95, -0.25, 0], C_GOLD, is_square=True)

        e_hop1_a = Line([-1.12, -0.05, 0], [0.55, 0.62, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop1_b = Line([-1.12, -0.45, 0], [0.55, -1.12, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop2_a = Line([1.16, 0.72, 0], [2.62, 0.72, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop2_b = Line([1.16, -1.22, 0], [2.62, -1.22, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop3_a = Line([3.27, 0.62, 0], [4.11, -0.02, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)
        e_hop3_b = Line([3.27, -1.12, 0], [4.11, -0.48, 0], color=C_SLATE, stroke_width=2.0).set_z_index(6)

        fg_subgraph = VGroup(
            top_chain_grp, n_peer_rider, n_peer_ben, h_integrated, sel_ring, h_part_br, h_part_ht, n_ep_ben1, n_ep_ben2, n_ep_prod,
            arrow_2d(n_peer_rider[0].get_right(), n_peer_ben[0].get_left(), color=C_CYAN, sw=2.0, tip=0.11, z=7),
            arrow_2d(n_peer_ben[0].get_right(), [-1.82, -0.25, 0], color=C_CYAN, sw=2.0, tip=0.11, z=7),
            e_hop1_a, e_hop1_b,
            pill("통합 관계 연결", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=9.2, px=0.08, py=0.03, z=9).move_to([-0.08, 0.46, 0]),
            pill("통합 관계 연결", fg=C_MINT, bg=C_PANEL, border=C_MINT, size=9.2, px=0.08, py=0.03, z=9).move_to([-0.08, -0.96, 0]),
            e_hop2_a, e_hop2_b, e_hop3_a, e_hop3_b,
        )

        self.cam_move(
            zoom=1.52,
            center=[-1.45, -0.25, 0],
            anims=[FadeIn(h_integrated, scale=0.8), FadeIn(sel_ring)],
            rt=0.75,
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
            rt=0.85,
        )

        bad_arc = DashedVMobject(
            CubicBezier(np.array([-1.45, -0.62, 0]), np.array([0.2, -2.55, 0]), np.array([3.2, -2.55, 0]), np.array([4.95, -0.62, 0]), color=C_CORAL, stroke_width=2.4),
            num_dashes=28,
        ).set_z_index(10)
        bad_1hop_lbl = fit(
            pill(f'단순 특약명 대조 시: "{nm_bs_surg} 특약이 없으니 미보유"로 오판 ×', fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=11.0, z=11),
            max_w=9.20,
        ).move_to([1.55, -2.38, 0])
        self.play(Create(bad_arc), FadeIn(bad_1hop_lbl, shift=UP * 0.08), run_time=0.70)
        self.wait(0.75)

        hop_badge = fit(
            pill(f"포함 {num(rel_by_k['포함'])}건, 통합 {num(rel_by_k['통합'])}건 관계 탐색 ✓: 분리 특약과 상위 특약 보유 사실을 연결해 안내", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=11.0, z=12),
            max_w=9.30,
        ).move_to([1.45, -2.38, 0])
        p_up, p_dn = glow_dot([-1.12, -0.05, 0], color=C_MINT, r=0.072, z=14), glow_dot([-1.12, -0.45, 0], color=C_MINT, r=0.072, z=14)
        self.add(p_up, p_dn)

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
            rt=0.70,
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
            rt=0.60,
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
            rt=0.80,
        )
        self.remove(p_up, p_dn)
        self.wait(1.50)

        # -------------------------------------------------------------------
        # Beat 8B: Segment Map (24 cells), Treatment Stages (5), & Combination Constraints
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
            rt=0.40,
        )

        pm_title = fit(
            txt(f"고객군 지도 요약 (전체 {num(len(seg_rows))}행×{num(len(seg_cols))}열={num(seg_cells_n)}칸, {base_var_name})", size=11.6, color=C_WHITE, bold=True, z=7),
            max_w=5.95,
        ).move_to([-3.05, 2.26, 0])

        lbl_open_tog = seg_lbls[1]
        lbl_ours_closed = seg_lbls[2]
        grouped_rows = [
            (f"{seg_rows[0]}~{seg_rows[1]} ({num(2)}행 묶음)", lbl_ours_closed, lbl_ours_closed, False),
            (f"{seg_rows[2]} 외 ({num(4)}행 묶음)", lbl_ours_closed, lbl_open_tog, True),
            (f"{seg_rows[6]}~{seg_rows[7]} ({num(2)}행 묶음)", lbl_ours_closed, f"{lbl_open_tog} (상대 관문전용)", True),
            (f"{seg_rows[8]} 외 ({num(4)}행 묶음)", lbl_ours_closed, lbl_open_tog, True),
        ]
        pm_cells = VGroup()
        focus_cell = None
        for r_i, (r_lbl, c0_txt, c1_txt, is_c1_open) in enumerate(grouped_rows):
            ry = 1.25 - r_i * 0.78
            pm_cells.add(fit(txt(r_lbl, size=8.8, color=C_GOLD if r_i == 2 else C_INK_1, bold=(r_i == 2), z=7), max_w=2.12).move_to([-5.12, ry, 0]))
            for c_i, cw_p in enumerate([1.22, 2.48]):
                cx = -3.36 if c_i == 0 else -1.42
                is_hi = r_i == 2 and c_i == 1
                is_open = c_i == 1 and is_c1_open
                cell_r = RoundedRectangle(
                    corner_radius=0.05,
                    width=cw_p,
                    height=0.64,
                    fill_color="#383016" if is_hi else ("#182832" if is_open else C_PANEL_HI),
                    fill_opacity=0.95,
                    stroke_color=C_GOLD if is_hi else (C_CYAN if is_open else C_SLATE),
                    stroke_width=2.1 if is_hi else 1.2,
                ).move_to([cx, ry, 0]).set_z_index(4)
                cell_s = c0_txt if c_i == 0 else c1_txt
                cell_col = C_GOLD if is_hi else (C_CYAN if is_open else C_INK_2)
                ct = fit(txt(cell_s, size=9.4, color=cell_col, bold=is_hi, z=7), max_w=cw_p - 0.16).move_to(cell_r)
                if is_hi:
                    focus_cell = cell_r
                pm_cells.add(VGroup(cell_r, ct))

        pm_age_hdr = VGroup(
            txt(seg_cols[0], size=10.8, color=C_INK_2, z=7).move_to([-3.36, 1.76, 0]),
            txt(seg_cols[1], size=10.8, color=C_INK_1, bold=True, z=7).move_to([-1.42, 1.76, 0]),
        )
        pm_foot = fit(
            txt(
                f"함께 열림 {num(seg_open_tog)}칸, 우리 간편 닫힘 {num(seg_closed)}칸, 우리 간편만 열림 {num(seg_ours_only)}칸 (상대 관문전용만 열림 {num(seg_gate_only)}칸)",
                size=8.4,
                color=C_INK_1,
                z=7,
            ),
            max_w=6.05,
        ).move_to([-3.05, -1.62, 0])

        pin_pt = np.array([-0.36, -0.31, 0.0])
        target_cursor = VGroup(
            Circle(radius=0.14, fill_opacity=0.0, stroke_color=WHITE, stroke_width=2.2).move_to(pin_pt),
            Line(pin_pt + LEFT * 0.20, pin_pt + RIGHT * 0.20, color=WHITE, stroke_width=1.4),
            Line(pin_pt + DOWN * 0.20, pin_pt + UP * 0.20, color=WHITE, stroke_width=1.4),
            Dot(pin_pt, radius=0.04, color=C_GOLD),
        ).set_z_index(10)
        phase_map_grp = VGroup(pm_title, pm_age_hdr, pm_cells, pm_foot, target_cursor)

        cj_title = fit(txt(f"치료 {num(n_tr_stages)}단계별 보유 담보 수 (합계 {num(held_total)}개)", size=12.4, color=C_WHITE, bold=True, z=7), max_w=5.35).move_to([3.25, 2.26, 0])
        stage_cols = [C_CYAN, C_CYAN, C_MINT, C_GOLD, C_CORAL]
        cj_bars, cj_nodes = VGroup(), VGroup()
        cj_base_y = 0.44
        for s_i, s_nm in enumerate(tr_stages):
            s_cnt = held_by_stage[s_nm]
            s_col = stage_cols[s_i % len(stage_cols)]
            sx = 1.05 + s_i * 1.10
            slot_bg = RoundedRectangle(
                corner_radius=0.05, width=0.84, height=1.36, fill_color=C_PANEL_HI, fill_opacity=0.92,
                stroke_color=C_CORAL if s_cnt == 0 else C_SLATE, stroke_width=1.8 if s_cnt == 0 else 1.1,
            ).move_to([sx, cj_base_y + 0.68, 0]).set_z_index(3)
            if s_cnt > 0:
                bh = (s_cnt / max_stage_cnt) * 0.80
                bar = RoundedRectangle(corner_radius=0.04, width=0.56, height=bh, fill_color=s_col, fill_opacity=0.86, stroke_color=WHITE, stroke_width=1.0).move_to([sx, cj_base_y + 0.10 + bh / 2, 0]).set_z_index(5)
                cj_bars.add(VGroup(slot_bg, bar, txt(f"{num(s_cnt)}개", size=10.8, color=WHITE, bold=True, z=7).move_to([sx, cj_base_y + 0.10 + bh + 0.18, 0])))
            else:
                cj_bars.add(
                    VGroup(
                        slot_bg,
                        txt(f"{num(s_cnt)}개", size=12.6, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + UP * 0.12),
                        txt("미보유 구간", size=8.8, color=C_CORAL, bold=True, z=7).move_to(slot_bg.get_center() + DOWN * 0.28),
                    )
                )
            cj_nodes.add(txt(s_nm, size=10.6, color=C_CORAL if s_cnt == 0 else C_INK_1, bold=(s_cnt == 0), z=7).move_to([sx, cj_base_y - 0.20, 0]))

        cj_links = VGroup(
            *[Line([1.05 + i * 1.10 + 0.44, cj_base_y + 0.68, 0], [1.05 + (i + 1) * 1.10 - 0.44, cj_base_y + 0.68, 0], color=C_CORAL if i == n_tr_stages - 2 else C_GOLD, stroke_width=2.2).set_z_index(6) for i in range(n_tr_stages - 1)]
        )
        care_journey_grp = VGroup(cj_title, cj_bars, cj_nodes, cj_links)

        rc_box = RoundedRectangle(corner_radius=0.07, width=5.35, height=1.85, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_SLATE, stroke_width=1.4).move_to([3.25, -1.18, 0]).set_z_index(3)
        nd_main = fit(pill(f"● 주계약 한도 {num(main_lim_mw)}만", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=9.2, px=0.08, py=0.05, z=7), max_w=1.62).move_to([1.48, -1.10, 0])
        nd_rider = fit(pill(f"● 기준 {num(basis_mw)}만에 지급 {num(pay_new_mw)}만", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=8.8, px=0.08, py=0.05, z=7), max_w=1.86).move_to([3.30, -1.10, 0])
        nd_excl = fit(pill(f"● 결합 제약 {num(comb_cnt)}건", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.2, px=0.08, py=0.05, z=7), max_w=1.42).move_to([5.10, -1.10, 0])
        constraint_grp = VGroup(
            rc_box,
            fit(txt("특약 결합 제약 및 실제 지급액 계산", size=11.6, color=C_GOLD, bold=True, z=7), max_w=5.00).move_to([3.25, -0.52, 0]),
            nd_main, nd_rider, nd_excl,
            arrow_2d(nd_main.get_right(), nd_rider.get_left(), color=C_MINT, sw=1.8, tip=0.08, z=7),
            DashedLine(nd_rider.get_right(), nd_excl.get_left(), dash_length=0.06, color=C_CORAL, stroke_width=1.8).set_z_index(6),
            fit(txt("주계약 연동 한도와 선행, 동시 가입 불가 규칙 반영 ✓", size=9.8, color=C_INK_1, z=7), max_w=5.00).move_to([3.25, -1.72, 0]),
        )
        beat8b_all = VGroup(phase_map_grp, care_journey_grp, constraint_grp)

        self.play(
            FadeOut(bg_cosmos),
            FadeOut(fg_subgraph),
            FadeOut(hop_badge),
            FadeIn(pm_title),
            FadeIn(pm_age_hdr),
            FadeIn(pm_foot),
            LaggedStart(*[FadeIn(c, shift=UP * 0.05) for c in pm_cells], lag_ratio=0.025),
            FadeIn(care_journey_grp, shift=LEFT * 0.12),
            FadeIn(constraint_grp, shift=UP * 0.10),
            run_time=1.05,
        )
        self.remove_billboard(*billboard_nodes)
        self.remove(bg_cosmos, fg_subgraph, hop_badge)

        assert focus_cell is not None
        self.cam_move(
            zoom=1.40,
            center=[-2.90, 0.10, 0],
            anims=[FadeIn(target_cursor, scale=1.5), Circumscribe(focus_cell, color=C_GOLD, stroke_width=2.2, buff=0.03)],
            rt=0.90,
        )
        self.wait(0.65)

        cj_pulse = glow_dot([1.05, cj_base_y + 0.68, 0], color=C_GOLD, r=0.065, z=13)
        self.add(cj_pulse)
        self.cam_move(
            zoom=1.38,
            center=[3.25, 0.85, 0],
            anims=[
                MoveAlongPath(cj_pulse, Line([1.05, cj_base_y + 0.68, 0], [1.05 + (n_tr_stages - 1) * 1.10, cj_base_y + 0.68, 0])),
                Circumscribe(cj_bars[-1][0], color=C_CORAL, stroke_width=2.2, buff=0.03),
                Wiggle(cj_bars[-1][1], scale_value=1.18, rotation_angle=0.05 * TAU),
            ],
            rt=0.95,
        )
        self.remove(cj_pulse)
        self.wait(0.65)
        self.reset_cam_2d(rt=0.75)

        self.check_bounds(beat8b_all, "CH8B PHASE & CARE CHARTS")
        self.wait(1.50)

        # -------------------------------------------------------------------
        # Beat 8C: 5 Sales Insight Categories -> Console & A4 Card
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
            rt=0.40,
        )

        def make_ins_card(cx: float, cy: float, w_c: float, h_c: float, col: str, title_s: str, desc_s: str) -> VGroup:
            box = RoundedRectangle(corner_radius=0.08, width=w_c, height=h_c, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.0).move_to([cx, cy, 0]).set_z_index(4)
            t_blk = fit(
                VGroup(
                    txt(title_s, size=11.6, color=col, bold=True, z=7),
                    txt(desc_s, size=9.8, color=WHITE, z=7),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.10),
                max_w=w_c - 0.36,
            ).move_to([cx, cy, 0])
            return VGroup(box, t_blk)

        c_ins1 = make_ins_card(
            -3.85, 1.56, 3.88, 1.48, C_GOLD,
            f"① {ins_cats[0]} ({num(ins_by_cat[ins_cats[0]])}건)",
            f"고지 질문이 다른 상대 {num(q_diff_peers)}곳 비교 (우리 간편만 열림 {num(seg_ours_only)}칸)",
        )
        c_ins2 = make_ins_card(
            0.0, 1.56, 3.60, 1.48, C_MINT,
            f"② {ins_cats[1]} ({num(ins_by_cat[ins_cats[1]])}건)",
            f"대표 담보: {lead_str}",
        )
        c_ins3 = make_ins_card(
            3.85, 1.56, 3.88, 1.48, C_VIOLET,
            f"③ {ins_cats[2]} ({num(ins_by_cat[ins_cats[2]])}건)",
            f"{rel_kinds_str} 관계의 분리 특약과 상위 특약 연결 안내",
        )
        c_ins4 = make_ins_card(
            -2.95, -1.28, 5.20, 1.52, C_CYAN,
            f"④ {ins_cats[3]} (기준 {num(ins_by_cat[ins_cats[3]])}건, {var_gen_name} {num(var_gen_def_cnt)}건)",
            "감액 기간 경과 뒤 전액 지급 조건과 미단정 사유 분리",
        )
        c_ins5 = make_ins_card(
            2.95, -1.28, 5.20, 1.52, C_CORAL,
            f"⑤ {ins_cats[4]} ({num(ins_by_cat[ins_cats[4]])}건)",
            f"입원 {num(held_by_stage['입원'])}개 대비 통원 {num(held_by_stage['통원'])}개 등 미보유 담보 정리",
        )

        comp_c = np.array([0.0, 0.08, 0.0])
        comp_ring = Circle(radius=0.46, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.6).move_to(comp_c).set_z_index(10)
        comp_needle = Line(comp_c + DOWN * 0.34, comp_c + UP * 0.34, color=C_GOLD, stroke_width=2.6).rotate(PI / 4).set_z_index(12)
        comp_txt = fit(txt(f"{num(n_ins_cats)}분류", size=9.6, color=WHITE, bold=True, z=13), max_w=0.74).move_to(comp_c)
        compass_hub = VGroup(comp_ring, comp_needle, comp_txt)
        five_insights = VGroup(c_ins1, c_ins2, c_ins3, c_ins4, c_ins5, compass_hub)

        self.add(comp_needle)
        self.play(
            FadeOut(beat8b_all, scale=0.94),
            FadeIn(VGroup(comp_ring, comp_txt), scale=0.6),
            Rotate(comp_needle, angle=-TAU, about_point=comp_c),
            LaggedStart(*[FadeIn(q, shift=UP * 0.10) for q in [c_ins1, c_ins2, c_ins3, c_ins4, c_ins5]], lag_ratio=0.10),
            run_time=1.15,
        )
        self.remove(beat8b_all)
        self.wait(0.95)

        app_window = RoundedRectangle(corner_radius=0.10, width=8.05, height=4.75, fill_color=C_PANEL, fill_opacity=0.92, stroke_color=C_INK_1, stroke_width=2.2).move_to([-2.05, -0.15, 0]).set_z_index(1)
        app_win_hdr = fit(pill("본부 상품, 영업지원 판단 화면 (오프라인 단독 HTML)", fg=WHITE, bg=C_PANEL_HI, border=C_SLATE, size=11.2), max_w=7.60).move_to([-2.05, 1.92, 0]).set_z_index(8)
        tpl_bar = fit(pill(f"금지 표현 {num(forb_cnt)}개 빌드 차단 ✓, 근거 문서와 쪽수를 함께 보임", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=10.6, px=0.13, py=0.06, z=8), max_w=7.60).move_to([-2.05, -1.32, 0])
        nlq_bar = fit(pill("앞으로 할 일(다음 버전): 자연어 조건 검색 입력 연동", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=10.4, px=0.13, py=0.06, z=8), max_w=7.60).move_to([-2.05, -1.98, 0])

        a4_box = Rectangle(width=2.98, height=4.75, fill_color=C_IVORY, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.4).move_to([4.48, -0.15, 0]).set_z_index(5)
        a4_top_bar = Line(a4_box.get_corner(UL), a4_box.get_corner(UR), color=C_CORAL, stroke_width=5.0).set_z_index(7)
        a4_badge = pill("대외 배포 금지, A4 한 장", fg=WHITE, bg=C_CORAL, border=C_CORAL, size=10.6).move_to([4.48, 1.82, 0]).set_z_index(7)
        a4_title = fit(txt("창구, 설계사 응대 카드", size=14.6, color=C_DARK_INK, bold=True, z=7), max_w=2.70).move_to([4.48, 1.34, 0])
        ord_cols = [C_GOLD_DEEP, "#1E6B7B", "#2D3748", "#4C3B78", "#8C3A3A"]
        circled_nums = ["①", "②", "③", "④", "⑤"]
        mini_cards = VGroup()
        for idx_c, c_cat in enumerate(card_ord):
            mb = RoundedRectangle(corner_radius=0.04, width=2.58, height=0.46, fill_color="#E5E4DC", fill_opacity=1.0, stroke_color="#C4C2B6", stroke_width=1.0).set_z_index(6)
            m_bar = Rectangle(width=0.10, height=0.46, fill_color=ord_cols[idx_c % len(ord_cols)], fill_opacity=1.0, stroke_width=0).move_to(mb.get_left() + RIGHT * 0.05).set_z_index(7)
            c_cnt = ins_by_cat[c_cat]
            mini_cards.add(
                VGroup(
                    mb,
                    m_bar,
                    fit(txt(f"{circled_nums[idx_c]} {c_cat} ({num(c_cnt)}건)", size=10.2, color=C_DARK_INK, bold=True, z=7), max_w=2.24).move_to(mb.get_center() + RIGHT * 0.05),
                )
            )
        mini_cards.arrange(DOWN, buff=0.09).move_to([4.48, -0.22, 0])
        a4_foot = Rectangle(width=2.98, height=0.46, fill_color=C_DARK_INK, fill_opacity=1.0, stroke_width=0).move_to(a4_box.get_bottom() + UP * 0.23).set_z_index(6)
        a4_foot_t = fit(txt("본부 판단 -> 현장 A4 한 장 전달", size=10.8, color=C_GOLD, bold=True, z=7), max_w=2.72).move_to(a4_foot)
        proj_beam = arrow_2d([2.04, -0.15, 0], [2.92, -0.15, 0], color=C_GOLD, sw=3.2, tip=0.18, z=8)
        a4_full = VGroup(a4_box, a4_top_bar, a4_badge, a4_title, mini_cards, a4_foot, a4_foot_t)

        a4_laser = Line([2.98, 2.15, 0], [5.98, 2.15, 0], color=C_GOLD, stroke_width=3.6).set_z_index(12)
        self.add(a4_laser)
        self.cam_move(
            zoom=1.36,
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
                LaggedStart(*[FadeIn(mc, shift=DOWN * 0.06) for mc in mini_cards], lag_ratio=0.09),
                FadeIn(VGroup(a4_foot, a4_foot_t)),
            ],
            rt=1.25,
        )
        self.remove(a4_laser)
        self.wait(0.75)
        self.reset_cam_2d(rt=0.80)

        ch8_stage = VGroup(app_window, app_win_hdr, five_insights, tpl_bar, nlq_bar, proj_beam, a4_full)
        self.check_bounds(ch8_stage, "CH8C CONSOLE & CARD")
        self.wait(1.60)

        # ===================================================================
        # 9장: 손으로 하던 방식과 이 앱으로 바뀐 점 (개념검증 결과와 미측정 과제)
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

        col_hdr_before = pill("손으로 하던 방식", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.8, z=8).move_to([-4.32, 2.66, 0])
        col_hdr_after = pill("이 앱으로 (개념검증 구현 결과)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.8, z=8).move_to([2.16, 2.66, 0])

        def make_ba_lane(ly: float, b_title: str, b_vis: VGroup, tag_s: str, a_col: str, a_title: str, a_widgets: VGroup) -> tuple[VGroup, VGroup, VGroup]:
            bc = RoundedRectangle(corner_radius=0.08, width=3.62, height=1.24, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.7).move_to([-4.32, ly, 0]).set_z_index(4)
            bt = fit(txt(b_title, size=9.8, color=C_CORAL, bold=True, z=7), max_w=3.36).move_to([-4.32, ly + 0.38, 0])
            b_vis = fit(b_vis, max_w=3.34).move_to([-4.32, ly - 0.18, 0]).set_z_index(7)

            arr = arrow_2d([-2.42, ly, 0], [-1.56, ly, 0], color=a_col, sw=2.8, tip=0.14, z=7)
            albl = pill(tag_s, fg=C_DARK_INK, bg=a_col, border=WHITE, size=8.8, px=0.08, py=0.03, z=8).move_to([-1.99, ly + 0.34, 0])

            ac = RoundedRectangle(corner_radius=0.08, width=7.24, height=1.24, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=a_col, stroke_width=2.2).move_to([2.16, ly, 0]).set_z_index(5)
            at = fit(txt(a_title, size=10.2, color=a_col, bold=True, z=7), max_w=6.88).move_to([2.16, ly + 0.38, 0])
            a_widgets = fit(a_widgets, max_w=6.88).move_to([2.16, ly - 0.18, 0]).set_z_index(8)
            return VGroup(bc, bt, b_vis), VGroup(arr, albl), VGroup(ac, at, a_widgets)

        bv1 = VGroup(
            Circle(radius=0.16, fill_opacity=0.0, stroke_color=C_SLATE, stroke_width=1.4),
            txt("수동 조회 ?", size=8.4, color=C_INK_2, bold=True),
            DashedVMobject(Rectangle(width=0.30, height=0.40, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=1.4), num_dashes=10),
            txt("현장 카드 ×", size=8.4, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.10)

        ic_rad9_ring = Circle(radius=0.20, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_CYAN, stroke_width=1.8)
        ic_rad9_hand = Line([0, 0, 0], [0.14, 0.13, 0], color=C_GOLD, stroke_width=2.2)
        ic_rad9 = VGroup(ic_rad9_ring, ic_rad9_hand)
        ic_scr9 = RoundedRectangle(corner_radius=0.04, width=0.58, height=0.38, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.6)
        ic_a4_9 = VGroup(Rectangle(width=0.30, height=0.42, fill_color=C_IVORY, fill_opacity=1.0, stroke_color=C_GOLD, stroke_width=1.4), Line([-0.15, 0.21, 0], [0.15, 0.21, 0], color=C_CORAL, stroke_width=2.4))
        log_pill_9 = pill(f"화면 작업 로그 {num(wlog_site)}건", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.8, px=0.08, py=0.04)
        aw1 = VGroup(
            ic_rad9,
            txt(f"{num(news_inst_cnt)}개 기관, 운영비 {num(op_cost)}원(무료 설계)", size=8.8, color=C_CYAN, bold=True),
            log_pill_9,
            ic_scr9,
            arrow_2d([0, 0, 0], [0.24, 0, 0], color=C_GOLD, sw=1.8, tip=0.08),
            ic_a4_9,
            txt("A4 한 장", size=8.8, color=C_WHITE, bold=True),
        ).arrange(RIGHT, buff=0.10)
        b_l1, t_l1, a_l1 = make_ba_lane(
            1.36, "× 상시 소식 수집과 현장 카드 양식 부재", bv1, "구축 ✓", C_CYAN,
            f"① 정본 {num(sheet_tabs)}탭, 단독 HTML 화면, 창구 A4 한 장 응대 카드 구축", aw1,
        )
        ic_rad9_hand.set_z_index(11)

        bv2 = VGroup(
            Rectangle(width=0.30, height=0.38, fill_color=C_CORAL_DIM, fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.4),
            txt(f"{num(img_pages)}쪽 그림 ×", size=8.4, color=C_CORAL, bold=True),
            txt(",", size=10, color=C_SLATE),
            txt("특약명 ≠", size=8.6, color=C_AMBER, bold=True),
        ).arrange(RIGHT, buff=0.08)

        aw2 = VGroup(
            pill(
                f"그림 {num(img_pages)}쪽: 두 판독 지급률, 금액 어긋남 {num(img_mismatches)}곳 (두 판독 일치)",
                fg=C_MINT,
                bg=C_BG_SUB,
                border=C_MINT,
                size=8.6,
                px=0.09,
                py=0.05,
            ),
            pill(
                f"일부러 뒤집은 {num(cal_flip['rows'])}줄 통과 {num(cal_flip['passed'])}줄 (요약서 두 건 표본)",
                fg=C_GOLD,
                bg="#383016",
                border=C_GOLD,
                size=8.6,
                px=0.09,
                py=0.05,
            ),
        ).arrange(RIGHT, buff=0.14)
        b_l2, t_l2, a_l2 = make_ba_lane(
            0.00, "× 그림 요약서와 이질적인 특약 이름", bv2, "해결 ✓", C_GOLD,
            f"② 원문과 코드 분리 + 두 판독 교차 + {decide_model} + 표준담보 {num(cov_use)}개({rel_kinds_str} 관계)", aw2,
        )

        bv3 = VGroup(
            Dot([0, 0, 0], radius=0.065, color=C_AMBER),
            txt("대기=공백 오인", size=8.4, color=C_AMBER, bold=True),
            RegularPolygon(n=3, fill_color="#3D2B0D", fill_opacity=0.95, stroke_color=C_CORAL, stroke_width=1.4).scale(0.15),
            txt("구두 과장 !", size=8.4, color=C_CORAL, bold=True),
        ).arrange(RIGHT, buff=0.10)

        ic_sep9 = VGroup(Line([0, -0.16, 0], [0, 0.16, 0], color=C_MINT, stroke_width=2.2), DashedLine([0.14, -0.16, 0], [0.14, 0.16, 0], dash_length=0.06, color=C_AMBER, stroke_width=2.0))
        ic_shd9 = VGroup(RegularPolygon(n=6, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_MINT, stroke_width=1.8).scale(0.18), txt("✓", size=9.2, color=C_MINT, bold=True))
        aw3 = VGroup(
            ic_sep9,
            txt(f"화면 대기 {num(ms_site['대기'])}건, 미단정 {num(no_verd_sum)}쌍 분리", size=8.6, color=C_AMBER, bold=True),
            ic_shd9,
            txt(f"금지 표현 {num(forb_cnt)}개 차단, 보험료 추정 제외", size=8.6, color=C_MINT, bold=True),
            pill(f"근거 쪽수, 인사이트 {num(n_ins_cats)}분류 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=8.6, px=0.08, py=0.04),
        ).arrange(RIGHT, buff=0.12)
        b_l3, t_l3, a_l3 = make_ba_lane(
            -1.36, "× 미보유 오판과 억지 비교, 과장 위험", bv3, "보강 ✓", C_MINT,
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
                size=9.8,
                z=9,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.38, 0])
        nym_ribbon = fit(
            txt(f"아직 재지 못한 성과: {', '.join(nym_list)}", size=8.6, color=C_INK_2, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.86, 0])

        self.cam_move(
            zoom=1.24,
            center=[-4.15, 0.25, 0],
            anims=[
                FadeIn(col_hdr_before, shift=DOWN * 0.08),
                LaggedStart(*[FadeIn(bc, shift=RIGHT * 0.12) for bc in before_cards], lag_ratio=0.10),
            ],
            rt=1.05,
        )
        self.wait(0.95)

        pulses_9 = VGroup(
            glow_dot([-2.42, 1.36, 0], color=C_CYAN, r=0.06, z=12),
            glow_dot([-2.42, 0.00, 0], color=C_GOLD, r=0.06, z=12),
            glow_dot([-2.42, -1.36, 0], color=C_MINT, r=0.06, z=12),
        )
        self.add(pulses_9, ic_rad9_hand)
        self.cam_move(
            zoom=1.24,
            center=[1.95, 0.20, 0],
            anims=[
                FadeIn(col_hdr_after, shift=DOWN * 0.08),
                LaggedStart(*[FadeIn(ta, scale=0.9) for ta in trans_arrows], lag_ratio=0.10),
                MoveAlongPath(pulses_9[0], Line([-2.42, 1.36, 0], [-1.56, 1.36, 0])),
                MoveAlongPath(pulses_9[1], Line([-2.42, 0.00, 0], [-1.56, 0.00, 0])),
                MoveAlongPath(pulses_9[2], Line([-2.42, -1.36, 0], [-1.56, -1.36, 0])),
                FadeIn(VGroup(a_l1[0], a_l1[1], ic_rad9_ring, *aw1[1:]), shift=LEFT * 0.10),
                Rotate(ic_rad9_hand, angle=-TAU, about_point=ic_rad9_ring.get_center()),
                FadeIn(a_l2, shift=LEFT * 0.10),
                FadeIn(a_l3, shift=LEFT * 0.12),
                Flash(ic_shd9.get_center(), color=C_MINT, line_length=0.22, num_lines=8),
            ],
            rt=1.35,
        )
        self.remove(pulses_9, *pulses_9)
        self.wait(1.10)

        self.reset_cam_2d(
            anims=[
                FadeIn(finale_ribbon, shift=UP * 0.06),
                FadeIn(nym_ribbon, shift=UP * 0.04),
                LaggedStart(*[Circumscribe(ac[0], color=C_GOLD, stroke_width=2.0, buff=0.03) for ac in after_cards], lag_ratio=0.12),
            ],
            rt=0.90,
        )

        ch9_stage = VGroup(col_hdr_before, col_hdr_after, before_cards, trans_arrows, after_cards, finale_ribbon, nym_ribbon)
        self.check_bounds(ch9_stage, "CH9 VISUAL BEFORE AFTER")
        self.wait(2.80)
