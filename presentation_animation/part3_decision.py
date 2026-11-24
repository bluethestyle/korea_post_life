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
    C_MINT,
    C_PANEL,
    C_PANEL_HI,
    C_SLATE,
    C_VIOLET,
    C_WHITE,
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
    make_npu_chip,
    make_stopwatch,
    num,
    pill,
    pillar_3d_sliced,
    txt,
)
from infographics import svg_icon


class Part3DecisionScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        decide_model = fact("models", "decide")
        rel_date = fact("decision_model_release_date")
        d_spec = fact("decision_model_spec")
        d_uses = [label_ko(u) for u in fact("decision_model_uses")]
        lim_decide = fact("daily_limit_decide")
        pm_lim = fact("decide_per_minute_limit")
        sym_prob = fact("symmetric_choice_probability")
        tf_rng = fact("true_false_probability_range")
        cal_flip = fact("calibration_flipped_rows")
        cal_band = fact("calibration_reextract_band")
        bnd_chk = fact("bundled_constraint_check")
        m_req = fact("mapping_requery")
        cov_in_use = fact("standard_coverage_in_use")
        v_conf = fact("verify_confirm_threshold")
        v_reex = fact("verify_reextract_threshold")
        win_cfg = fact("decide_token_window")
        guard_tok = fact("decide_tokens_per_minute_guard")
        cat_list = fact("market_news_categories")
        cat_cnt = fact("market_news_category_count")
        cats_by_cnt = fact("market_news_by_category")
        news_total = fact("market_news_count")
        quota_fails = fact("decide_quota_failures_logged")

        # ===================================================================
        # 5장: 판정 모델의 원리와 단일 호출 아키텍처
        # ===================================================================
        hl, hr, hb = self.make_hud(
            5,
            f"판정 모델 {decide_model}: 선택지 확률 반환 방식",
            "판정 모델은 텍스트를 생성하지 않고 지정된 선택지별 확률만 반환합니다",
        )

        # -------------------------------------------------------------------
        # Beat 5A: 상하 듀얼 트랙(생성형 토큰 스트림 vs 비생성 확률 엔진) + 우측 4대 적용 버스
        # -------------------------------------------------------------------
        gen_lane = RoundedRectangle(
            corner_radius=0.09, width=7.56, height=1.88, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_SLATE, stroke_width=2.0
        ).move_to([-2.12, 1.38, 0]).set_z_index(3)
        gen_hdr = fit(pill("비교 기준: 일반 텍스트 생성 호출 (생성형 방식)", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=11.4), max_w=4.40).move_to([-3.42, 1.98, 0]).set_z_index(6)
        gen_tag = pill("문장 출력 토큰 연속 소모", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=10.2, px=0.10, py=0.035, z=6).move_to([0.22, 1.98, 0])

        sw_c = np.array([-5.12, 1.15, 0.0])
        sw_ring, sw_hand = make_stopwatch(sw_c, r=0.28, col=C_AMBER, z=7)
        gen_tok_row = fit(
            VGroup(
                pill('"특약"', fg=C_WHITE, bg=C_PANEL_HI, border=C_SLATE, size=11.2, px=0.10, py=0.04),
                arrow_2d([0, 0, 0], [0.24, 0, 0], color=C_SLATE, sw=1.8, tip=0.07),
                pill('"검수"', fg=C_WHITE, bg=C_PANEL_HI, border=C_SLATE, size=11.2, px=0.10, py=0.04),
                arrow_2d([0, 0, 0], [0.24, 0, 0], color=C_AMBER, sw=1.8, tip=0.07),
                pill('"생성..."', fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=11.2, px=0.10, py=0.04),
                pill("(예시 그림)", fg=C_INK_1, bg=C_BG_SUB, border=C_SLATE, size=9.8, px=0.08, py=0.035),
            ).arrange(RIGHT, buff=0.08),
            max_w=4.55,
        ).move_to([-2.22, 1.24, 0]).set_z_index(6)
        wob_fn = ParametricFunction(
            lambda u: np.array([-4.48 + u * 5.65, 0.72 + 0.10 * math.sin(10.0 * u), 0.0]),
            t_range=[0, 1, 0.02],
            color=C_AMBER,
            stroke_width=2.2,
        ).set_z_index(6)

        vs_down = arrow_2d([-2.12, 0.38, 0], [-2.12, -0.02, 0], color=C_GOLD, sw=3.0, tip=0.12, z=8)
        vs_pill = pill("텍스트 생성 생략 -> 확률 직접 반환", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.4, px=0.12, py=0.035, z=9).move_to([-2.12, 0.18, 0])

        dec_lane = RoundedRectangle(
            corner_radius=0.09, width=7.56, height=2.24, fill_color=C_PANEL, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.4
        ).move_to([-2.12, -1.16, 0]).set_z_index(3)
        dec_hdr_row = fit(
            VGroup(
                pill(f"{rel_date} 출시", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, px=0.10, py=0.035),
                txt(f"비생성 판정 모델 {decide_model} (최대 {num(d_spec['items_per_call'])}문항 사양)", size=12.6, color=C_GOLD, bold=True, z=7),
            ).arrange(RIGHT, buff=0.12),
            max_w=7.10,
        ).move_to([-2.12, -0.36, 0]).set_z_index(7)

        dec_in = pill("특약 원문 + 문항", fg=C_WHITE, bg=C_PANEL_HI, border=C_CYAN, size=10.8, px=0.10, py=0.05, z=7).move_to([-4.92, -1.32, 0])
        dec_core = make_npu_chip([-2.68, -1.32, 0], w=2.02, h=0.96, col=C_GOLD, accent=C_CYAN, z=6)
        dec_core_t = fit(
            VGroup(
                txt(decide_model, size=11.6, color=C_GOLD, bold=True, z=9),
                txt(f"출력 토큰 = {num(d_spec['output_tokens'])}", size=10.8, color=C_MINT, bold=True, z=9),
            ).arrange(DOWN, buff=0.04),
            max_w=1.80,
        ).move_to([-2.68, -1.32, 0])
        dec_in_arr = arrow_2d(dec_in.get_right(), [-3.78, -1.32, 0], color=C_CYAN, sw=2.2, tip=0.10, z=7)

        w_scale = 1.12
        w_corr = w_scale * sym_prob["correct_min"]
        w_flip = w_scale * sym_prob["flipped_max"]
        dec_bars, dec_out_arrs = VGroup(), VGroup()
        for b_i, (by, b_lbl, b_val, b_w, b_col) in enumerate(
            [
                (-1.06, "정상 값", f"{sym_prob['correct_min']:.2f}↑", w_corr, C_GOLD),
                (-1.58, "반전 오류값", f"{sym_prob['flipped_max']:.2f}↓", w_flip, C_SLATE),
            ]
        ):
            dec_out_arrs.add(arrow_2d([-1.56, -1.32, 0], [-1.32, by, 0], color=C_GOLD if b_i == 0 else C_SLATE, sw=1.9, tip=0.08, z=6))
            lt = txt(b_lbl, size=10.6, color=C_INK_0 if b_i > 0 else WHITE, bold=True, z=7).move_to([-0.78, by, 0])
            br = Rectangle(width=b_w, height=0.22, fill_color=b_col, fill_opacity=0.96, stroke_width=0).move_to([-0.16 + b_w / 2, by, 0]).set_z_index(7)
            vt = txt(b_val, size=10.6, color=C_GOLD if b_i == 0 else C_INK_1, bold=True, z=7).next_to(br, RIGHT, buff=0.07)
            dec_bars.add(VGroup(lt, br, vt))

        # 우측 4대 적용 파이프라인 스택
        use_hdr = fit(
            pill(f"판정 모델 적용 {num(len(d_uses))}개 영역", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.6, z=8),
            max_w=3.88,
        ).move_to([4.02, 2.08, 0])
        use_specs = [
            ("shield_check", C_CYAN, f"① {d_uses[0]}"),
            ("book_dict", C_GOLD, f"② {d_uses[1]}"),
            ("search_globe", C_MINT, f"③ {d_uses[2]}"),
            ("git_lineage", C_VIOLET, f"④ {d_uses[3]}"),
        ]
        use_nodes, use_links = VGroup(), VGroup()
        bus_spine = Line([1.88, -1.32, 0], [1.88, 1.32, 0], color=C_GOLD_DEEP, stroke_width=2.2).set_z_index(4)
        bus_feed = Line([1.66, -1.32, 0], [1.88, -1.32, 0], color=C_GOLD, stroke_width=2.4).set_z_index(5)
        for idx_u, (u_ic, u_col, u_lbl) in enumerate(use_specs):
            uy = 1.32 - idx_u * 0.88
            u_box = RoundedRectangle(corner_radius=0.07, width=3.74, height=0.68, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=u_col, stroke_width=1.9).move_to([4.06, uy, 0]).set_z_index(5)
            ic_m = svg_icon(u_ic, size=0.44, col=u_col, accent=C_GOLD, z=8).move_to([2.54, uy, 0])
            lb_m = fit(txt(u_lbl, size=11.4, color=u_col, bold=True, z=8), max_w=2.86).move_to([4.34, uy, 0])
            use_nodes.add(VGroup(u_box, ic_m, lb_m))
            use_links.add(arrow_2d([1.88, uy, 0], [2.16, uy, 0], color=u_col, sw=2.0, tip=0.09, z=6))
        use_foot = fit(
            txt(f"(기존 상품 초기 적재는 {TERM['extract_dual']} {TERM['cross_verify']})", size=10.0, color=C_INK_1, bold=True, z=7),
            max_w=3.86,
        ).move_to([4.06, -1.96, 0])

        self.add(sw_hand)
        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(VGroup(gen_lane, gen_hdr, gen_tag, sw_ring), shift=DOWN * 0.10),
                Rotate(sw_hand, angle=-2 * TAU, about_point=sw_c),
                LaggedStart(*[FadeIn(tk, shift=RIGHT * 0.08) for tk in gen_tok_row], lag_ratio=0.16),
                Create(wob_fn),
            ],
            rt=1.55,
        )
        self.wait(1.80)

        self.play(
            GrowArrow(vs_down),
            FadeIn(vs_pill, scale=0.88),
            FadeIn(VGroup(dec_lane, dec_hdr_row, dec_in, dec_core, dec_core_t), shift=UP * 0.12),
            GrowArrow(dec_in_arr),
            Flash([-2.38, -1.32, 0], color=C_GOLD, line_length=0.28, num_lines=10),
            LaggedStart(*[GrowArrow(oa) for oa in dec_out_arrs], lag_ratio=0.08),
            GrowFromEdge(dec_bars[0][1], LEFT),
            FadeIn(VGroup(dec_bars[0][0], dec_bars[0][2], dec_bars[1])),
            run_time=1.65,
        )
        self.wait(1.90)

        self.play(
            Create(bus_feed),
            Create(bus_spine),
            FadeIn(use_hdr, shift=DOWN * 0.06),
            LaggedStart(*[GrowArrow(ul) for ul in use_links], lag_ratio=0.10),
            LaggedStart(*[FadeIn(un, shift=LEFT * 0.10) for un in use_nodes], lag_ratio=0.10),
            FadeIn(use_foot),
            run_time=1.40,
        )

        beat5a_all = VGroup(
            gen_lane, gen_hdr, gen_tag, sw_ring, sw_hand, gen_tok_row, wob_fn,
            vs_down, vs_pill,
            dec_lane, dec_hdr_row, dec_in, dec_in_arr, dec_core, dec_core_t, dec_out_arrs, dec_bars,
            bus_feed, bus_spine, use_hdr, use_links, use_nodes, use_foot,
        )
        self.check_bounds(beat5a_all, "CH5A DUAL TRACK & BUS")
        self.wait(3.20)

        # -------------------------------------------------------------------
        # Beat 5B: 단일 호출 패킷 아키텍처 블루프린트 (2x2 박스 배제, 좌->우 엔드투엔드 흐름)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"{rel_date} 출시된 {decide_model}은 호출당 최대 {num(d_spec['items_per_call'])}문항에 대해 선택지 확률만 반환합니다",
        )

        tl_bar = fit(
            VGroup(
                pill(f"{rel_date} {decide_model} 출시", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.6, z=8),
                arrow_2d([0, 0, 0], [0.42, 0, 0], color=C_GOLD, sw=2.4, tip=0.10, z=8),
                pill(
                    f"하루 {num(lim_decide)}회, 분당 {num(pm_lim['calls'])}회, 입력 {num(pm_lim['tokens'])}토큰 (AI Studio 무료 티어 기준)",
                    fg=C_WHITE,
                    bg=C_PANEL_HI,
                    border=C_CYAN,
                    size=11.2,
                    z=8,
                ),
            ).arrange(RIGHT, buff=0.14),
            max_w=12.00,
        ).move_to([0.0, 2.56, 0]).set_z_index(8)

        # Stage 1 (Left): 입력 패킷 엔벨로프 (특약 단위(추출 단위) + 최대 1,000문항)
        pkt_box = RoundedRectangle(corner_radius=0.10, width=3.74, height=4.16, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.2).move_to([-4.12, -0.06, 0]).set_z_index(4)
        pkt_hdr = fit(txt(f"① 입력 패킷: {TERM['unit_first']}", size=11.8, color=C_CYAN, bold=True, z=7), max_w=3.48).move_to([-4.12, 1.64, 0])

        pkt_top = RoundedRectangle(corner_radius=0.06, width=3.32, height=1.10, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=1.5).move_to([-4.12, 0.74, 0]).set_z_index(5)
        pkt_top_c = VGroup(
            svg_icon("doc_text", size=0.50, col=C_CYAN, accent=C_GOLD, z=7).move_to([-5.32, 0.74, 0]),
            fit(
                VGroup(
                    txt(f"{TERM['unit']} 원문 텍스트", size=11.0, color=C_WHITE, bold=True, z=7),
                    txt("호출당 단일 원문 동시 전달", size=9.8, color=C_INK_1, bold=True, z=7),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.04),
                max_w=2.44,
            ).move_to([-3.72, 0.74, 0]),
        )
        plus_badge = pill("+", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.0, px=0.10, py=0.02, z=8).move_to([-4.12, -0.02, 0])

        pkt_bot = RoundedRectangle(corner_radius=0.06, width=3.32, height=1.56, fill_color=C_BG_SUB, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.5).move_to([-4.12, -1.04, 0]).set_z_index(5)
        pkt_bot_t = fit(txt(f"검증 문항 최대 {num(d_spec['items_per_call'])}개 (호출당 사양)", size=10.6, color=C_GOLD, bold=True, z=7), max_w=3.10).move_to([-4.12, -0.52, 0])
        q_dots = VGroup(
            *[
                Dot([-5.12 + (k % 9) * 0.25, -0.96 - (k // 9) * 0.26, 0], radius=0.050, color=C_GOLD if k % 2 == 0 else C_MINT).set_z_index(7)
                for k in range(18)
            ]
        )
        pkt_ex_note = txt("(문항 배열 예시 그림)", size=9.6, color=C_INK_1, z=7).move_to([-4.12, -1.58, 0])
        st5_left = VGroup(pkt_box, pkt_hdr, pkt_top, pkt_top_c, plus_badge, pkt_bot, pkt_bot_t, q_dots, pkt_ex_note)

        # Stage 2 (Center): 비생성 선택지 채점 코어 & 2가지 정형 판정 사양
        d1_c = np.array([0.0, 0.14, 0.0])
        d1_outer_dash = DashedVMobject(Circle(radius=1.22, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.2).move_to(d1_c), num_dashes=28).set_z_index(6)
        d1_core = Circle(radius=1.02, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_VIOLET, stroke_width=3.0).move_to(d1_c).set_z_index(7)
        d1_ic = svg_icon("cpu_decide", size=0.58, col=C_GOLD, accent=C_CYAN, tile=False, sw=2.3, z=9).move_to(d1_c + UP * 0.42)
        d1_txt = fit(
            VGroup(
                txt(decide_model, size=12.4, color=C_GOLD, bold=True, z=9),
                txt(f"출력 토큰 {num(d_spec['output_tokens'])}", size=11.0, color=C_MINT, bold=True, z=9),
                txt(f"하루 {num(lim_decide)}회 무료", size=10.2, color=C_INK_0, bold=True, z=9),
            ).arrange(DOWN, buff=0.04),
            max_w=1.74,
        ).move_to(d1_c + DOWN * 0.30)

        modes_3 = [
            pill("예 / 아니오 양자 판정", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.6, px=0.11, py=0.05, z=8),
            pill(f"{num(d_spec['choices_min'])}~{num(d_spec['choices_max'])}지선다 매핑", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.6, px=0.11, py=0.05, z=8),
        ]
        modes_row = fit(VGroup(*modes_3).arrange(DOWN, buff=0.12), max_w=3.20).move_to([0.0, -1.62, 0])
        modes_hdr = fit(txt(f"② {num(len(modes_3))}가지 정형 선택지 사양", size=11.4, color=C_VIOLET, bold=True, z=8), max_w=3.20).move_to([0.0, 1.72, 0])
        st5_center = VGroup(d1_outer_dash, d1_core, d1_ic, d1_txt, modes_hdr, modes_row)

        # Stage 3 (Right): 표본 기반 임계값 보정 결과
        cal_box = RoundedRectangle(corner_radius=0.10, width=3.74, height=4.16, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_MINT, stroke_width=2.2).move_to([4.12, -0.06, 0]).set_z_index(4)
        cal_hdr = fit(txt("③ 표본 기반 임계값 보정", size=11.8, color=C_MINT, bold=True, z=7), max_w=3.48).move_to([4.12, 1.64, 0])

        cal_r1 = RoundedRectangle(corner_radius=0.06, width=3.34, height=1.24, fill_color="#232012", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=1.6).move_to([4.12, 0.62, 0]).set_z_index(5)
        cal_r1_c = VGroup(
            svg_icon("shield_check", size=0.50, col=C_GOLD, accent=C_MINT, z=7).move_to([2.88, 0.62, 0]),
            fit(
                VGroup(
                    txt(f"오류 반전 {num(cal_flip['rows'])}행 테스트", size=11.0, color=C_GOLD, bold=True, z=7),
                    txt(f"확정 통과 {num(cal_flip['passed'])}행 차단 ✓", size=10.8, color=C_WHITE, bold=True, z=7),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.06),
                max_w=2.42,
            ).move_to([4.50, 0.62, 0]),
        )

        cal_r2 = RoundedRectangle(corner_radius=0.06, width=3.34, height=1.24, fill_color="#112820", fill_opacity=0.96, stroke_color=C_MINT, stroke_width=1.6).move_to([4.12, -0.82, 0]).set_z_index(5)
        cal_r2_c = VGroup(
            svg_icon("agent_bot", size=0.50, col=C_MINT, accent=C_CYAN, z=7).move_to([2.88, -0.82, 0]),
            fit(
                VGroup(
                    txt(f"오류 행 {cal_band['wrong_caught_pct']}% 검출", size=11.0, color=C_MINT, bold=True, z=7),
                    txt("타 모델 재추출 구간으로 이관 ✓", size=10.4, color=C_WHITE, bold=True, z=7),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.06),
                max_w=2.42,
            ).move_to([4.50, -0.82, 0]),
        )
        cal_foot = fit(txt(f"{TERM['ours']} 상품요약서 소규모 표본 기준 보정 결과", size=10.2, color=C_INK_1, bold=True, z=7), max_w=3.48).move_to([4.12, -1.74, 0])
        st5_right = VGroup(cal_box, cal_hdr, cal_r1, cal_r1_c, cal_r2, cal_r2_c, cal_foot)

        link_5b_l = arrow_2d([-2.18, 0.14, 0], [-1.30, 0.14, 0], color=C_CYAN, sw=2.8, tip=0.12, z=8)
        link_5b_r = arrow_2d([1.30, 0.14, 0], [2.18, 0.14, 0], color=C_MINT, sw=2.8, tip=0.12, z=8)

        self.add(d1_outer_dash)
        self.cam_move(
            zoom=1.28,
            center=[-2.15, 0.0, 0],
            anims=[
                FadeOut(beat5a_all, shift=UP * 0.10),
                FadeIn(st5_left, shift=RIGHT * 0.12),
                GrowArrow(link_5b_l),
                FadeIn(VGroup(d1_core, d1_ic, d1_txt, modes_hdr, modes_row), scale=0.90),
                Rotate(d1_outer_dash, angle=PI / 2, about_point=d1_c),
            ],
            rt=1.60,
        )
        self.remove(beat5a_all)
        self.play(LaggedStart(*[Indicate(d, color=WHITE, scale_factor=1.45) for d in q_dots], lag_ratio=0.025), run_time=0.95)
        self.wait(1.90)

        self.cam_move(
            zoom=1.28,
            center=[2.15, 0.0, 0],
            anims=[
                GrowArrow(link_5b_r),
                FadeIn(st5_right, shift=LEFT * 0.12),
            ],
            rt=1.40,
        )
        self.play(Circumscribe(cal_r1, color=C_GOLD, stroke_width=2.4, buff=0.03), run_time=0.80)
        self.wait(1.90)

        self.reset_cam_2d(anims=[FadeIn(tl_bar, shift=DOWN * 0.08)], rt=1.10)
        ch5_stage = VGroup(tl_bar, st5_left, link_5b_l, st5_center, link_5b_r, st5_right)
        self.check_bounds(ch5_stage, "CH5B PACKET ARCHITECTURE")
        self.wait(3.80)

        # ===================================================================
        # 6장: 검증, 분류 단계
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch5_stage,
            hl,
            hr,
            hb,
            6,
            "검증, 분류 단계: 분당 토큰 한도와 확률 임계값 설계",
            f"참/거짓 질의의 확률 중첩, {TERM['rider_cond']} {TERM['batch_query']} 오류, 분당 토큰 한도 대기를 해결했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 6A: 오픈 3구역 수리 시각화 트립틱 (밀도 곡선 중첩, 캡슐 게이트 누수, 누적 대기 시간 막대)
        # -------------------------------------------------------------------
        top_res_6 = fit(
            pill(
                f"한도 조건: 호출은 하루 {num(lim_decide)}회이나 입력량은 분당 {num(pm_lim['tokens'])}토큰 상한 존재 (AI Studio 무료 티어 기준)",
                fg=C_VIOLET,
                bg=C_PANEL_HI,
                border=C_VIOLET,
                size=11.8,
                z=9,
            ),
            max_w=12.00,
        ).move_to([0.0, 2.56, 0])

        div_6a_1 = DashedLine([-2.04, -2.10, 0], [-2.04, 2.05, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.6).set_z_index(3)
        div_6a_2 = DashedLine([2.04, -2.10, 0], [2.04, 2.05, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.6).set_z_index(3)

        # Zone 1: 참/거짓 확률 밀도 중첩 곡선
        z6_1_hdr = fit(
            VGroup(
                svg_icon("alert_warn", size=0.42, col=C_AMBER, accent=C_CORAL, z=8),
                txt("병목 ① 참/거짓 질의 확률 중첩", size=12.0, color=C_AMBER, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.74,
        ).move_to([-4.08, 1.70, 0])
        ax_c1 = Line([-5.78, -0.88, 0], [-2.38, -0.88, 0], color=C_SLATE, stroke_width=2.2).set_z_index(5)
        zone_mush = Rectangle(width=1.58, height=1.88, fill_color=C_AMBER, fill_opacity=0.20, stroke_color=C_AMBER, stroke_width=1.6).move_to([-3.92, 0.06, 0]).set_z_index(5)
        curve_t = ParametricFunction(
            lambda u: np.array([-5.62 + u * 3.08, -0.88 + 1.52 * math.exp(-(((u - 0.58) / 0.21) ** 2)), 0]),
            t_range=[0, 1, 0.02],
            color=C_GOLD,
            stroke_width=3.2,
        ).set_z_index(7)
        curve_f = ParametricFunction(
            lambda u: np.array([-5.62 + u * 3.08, -0.88 + 1.36 * math.exp(-(((u - 0.43) / 0.21) ** 2)), 0]),
            t_range=[0, 1, 0.02],
            color=C_CORAL,
            stroke_width=3.0,
        ).set_z_index(7)
        lbl_mush = pill(f"{tf_rng['low']:.2f}~{tf_rng['high']:.2f} 중첩 (예시 그림)", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=10.2, px=0.09, py=0.035, z=8).move_to([-3.92, 1.12, 0])
        lbl_ax_c1 = txt(f"{0.0:.1f}            {tf_rng['low']:.1f}    {tf_rng['high']:.1f}          {1.0:.1f}", size=10.2, color=C_INK_1, z=6).move_to([-4.08, -1.16, 0])
        z6_1_foot = fit(
            VGroup(
                txt("면책 조건 참/거짓 질의 시", size=10.6, color=C_INK_0, bold=True, z=7),
                txt(f"정상 행도 {tf_rng['low']:.2f}~{tf_rng['high']:.2f} 구간 분포", size=10.2, color=C_AMBER, bold=True, z=7),
            ).arrange(DOWN, buff=0.06),
            max_w=3.70,
        ).move_to([-4.08, -1.74, 0])

        # Zone 2: 특약 부가 조건 일괄 질의 캡슐 누수
        z6_2_hdr = fit(
            VGroup(
                svg_icon("git_lineage", size=0.42, col=C_CORAL, accent=C_GOLD, z=8),
                txt(f"병목 ② {TERM['rider_cond']} {TERM['batch_query']}", size=12.0, color=C_CORAL, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.80,
        ).move_to([0.0, 1.70, 0])
        capsule_box = DashedVMobject(
            RoundedRectangle(corner_radius=0.18, width=2.36, height=2.14, fill_opacity=0.0, stroke_color=C_AMBER, stroke_width=2.4).move_to([-0.54, 0.08, 0]),
            num_dashes=26,
        ).set_z_index(6)
        cap_items = VGroup(
            pill("정상 특약 (예시) ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=10.0, px=0.08, py=0.03, z=7),
            pill("정상 특약 (예시) ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=10.0, px=0.08, py=0.03, z=7),
            pill("오매칭 특약 ×", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=10.0, px=0.08, py=0.03, z=7),
            pill("오매칭 특약 ×", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=10.0, px=0.08, py=0.03, z=7),
        ).arrange(DOWN, buff=0.10).move_to([-0.54, 0.08, 0])
        leak_arr = arrow_2d([0.70, 0.08, 0], [1.08, 0.08, 0], color=C_CORAL, sw=2.6, tip=0.10, z=7)
        leak_t_grp = VGroup(
            txt(f"{bnd_chk['bundled_probability']:.2f}", size=11.0, color=WHITE, bold=True, z=9),
            txt("통과?!", size=10.2, color=WHITE, bold=True, z=9),
        ).arrange(DOWN, buff=0.04)
        leak_bg = RoundedRectangle(corner_radius=0.08, width=leak_t_grp.width + 0.24, height=leak_t_grp.height + 0.16, fill_color=C_CORAL, fill_opacity=0.98, stroke_color=WHITE, stroke_width=1.6).set_z_index(8)
        leak_stamp = VGroup(leak_bg, leak_t_grp.move_to(leak_bg)).move_to([1.52, 0.08, 0])
        z6_2_foot = fit(
            VGroup(
                txt(f"{TERM['rider_cond']} {TERM['batch_query']} 시", size=10.6, color=C_INK_0, bold=True, z=7),
                txt(f"오매칭 특약 {num(bnd_chk['wrong_riders'])}건 통과", size=10.2, color=C_CORAL, bold=True, z=7),
            ).arrange(DOWN, buff=0.06),
            max_w=3.70,
        ).move_to([0.0, -1.74, 0])

        # Zone 3: 매핑 재질의 예상 시간 누적 막대 (실측 비율 분할)
        z6_3_hdr = fit(
            VGroup(
                svg_icon("calendar_clock", size=0.42, col=C_VIOLET, accent=C_AMBER, z=8),
                txt("병목 ③ 매핑 재질의 예상 소요 시간", size=12.0, color=C_VIOLET, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.80,
        ).move_to([4.08, 1.70, 0])
        tot_min = m_req["estimated_minutes"]
        wt_min = m_req["waiting_minutes"]
        run_min = tot_min - wt_min
        bar_6a_w = 3.44
        w_run_part = bar_6a_w * (run_min / tot_min)
        w_wt_part = bar_6a_w * (wt_min / tot_min)

        t_lbl_top = fit(pill(f"실행 전 전체 약 {num(tot_min)}분 예상", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=10.8, z=7), max_w=3.44).move_to([4.08, 0.88, 0])
        t_bar_shell = RoundedRectangle(corner_radius=0.06, width=bar_6a_w, height=0.52, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_VIOLET, stroke_width=1.8).move_to([4.08, 0.16, 0]).set_z_index(5)
        t_bar_run = Rectangle(width=w_run_part, height=0.44, fill_color="#2B214A", fill_opacity=0.96, stroke_width=0).move_to([4.08 - bar_6a_w / 2 + w_run_part / 2, 0.16, 0]).set_z_index(6)
        t_bar_wt = Rectangle(width=w_wt_part, height=0.44, fill_color=C_AMBER, fill_opacity=0.96, stroke_width=0).move_to([4.08 + bar_6a_w / 2 - w_wt_part / 2, 0.16, 0]).set_z_index(6)
        t_lbl_wt = fit(pill(f"분당 토큰 한도 대기 약 {num(wt_min)}분 예상", fg=C_AMBER, bg="#261A0B", border=C_AMBER, size=10.4, z=8), max_w=3.44).move_to([4.08, -0.58, 0])
        z6_3_foot = fit(
            VGroup(
                txt(f"한화 {TERM['map_wait']} {num(m_req['rows'])}행", size=10.6, color=C_INK_0, bold=True, z=7),
                txt("재질의 실행 전 예상치", size=10.2, color=C_VIOLET, bold=True, z=7),
            ).arrange(DOWN, buff=0.06),
            max_w=3.70,
        ).move_to([4.08, -1.74, 0])

        # Zone 1 -> Zone 2 -> Zone 3 시연
        self.cam_move(
            zoom=1.36,
            center=[-4.08, -0.05, 0],
            anims=[
                FadeIn(VGroup(z6_1_hdr, ax_c1, zone_mush, lbl_ax_c1, z6_1_foot, div_6a_1)),
                Create(curve_t),
                Create(curve_f),
                FadeIn(lbl_mush, scale=1.15),
            ],
            rt=1.45,
        )
        self.wait(2.30)

        self.cam_move(
            zoom=1.36,
            center=[0.0, -0.05, 0],
            anims=[
                FadeIn(VGroup(z6_2_hdr, capsule_box, cap_items, z6_2_foot, div_6a_2)),
                GrowArrow(leak_arr),
                FadeIn(leak_stamp, scale=1.30),
            ],
            rt=1.40,
        )
        self.wait(2.30)

        self.cam_move(
            zoom=1.36,
            center=[4.08, -0.05, 0],
            anims=[
                FadeIn(VGroup(z6_3_hdr, t_lbl_top, t_bar_shell, z6_3_foot)),
                GrowFromEdge(t_bar_run, LEFT),
                GrowFromEdge(t_bar_wt, LEFT),
                FadeIn(t_lbl_wt, shift=UP * 0.06),
            ],
            rt=1.45,
        )
        self.wait(2.30)

        self.reset_cam_2d(anims=[FadeIn(top_res_6, shift=DOWN * 0.08)], rt=1.05)
        beat6a_all = VGroup(
            top_res_6, div_6a_1, div_6a_2,
            z6_1_hdr, ax_c1, zone_mush, curve_t, curve_f, lbl_mush, lbl_ax_c1, z6_1_foot,
            z6_2_hdr, capsule_box, cap_items, leak_arr, leak_stamp, z6_2_foot,
            z6_3_hdr, t_lbl_top, t_bar_shell, t_bar_run, t_bar_wt, t_lbl_wt, z6_3_foot,
        )
        self.check_bounds(beat6a_all, "CH6A DATA VIZ TRIPTYCH")
        self.wait(3.20)

        # -------------------------------------------------------------------
        # Beat 6B: True 3D 확률 공간과 두 수평 기준면 (0.75, 0.40) + 고대비 bb_badge
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"해결 ①, ② 원문 단일 입력 후 {TERM['rider_cond']}은 개별 질의하고, 대칭 선택지로 정상 값과 반전 오류값을 분리했습니다",
        )

        sep_p0, sep_p1 = bnd_chk["separated_probabilities"]

        batch_card = RoundedRectangle(
            corner_radius=0.09, width=3.92, height=4.18, fill_color="#091018", fill_opacity=0.97, stroke_color=C_CYAN, stroke_width=2.2
        ).move_to([-4.22, 0.06, 0]).set_z_index(25)
        batch_hdr = fit(txt("해결 ① 단일 원문 입력, 문항별 개별 질의", size=12.4, color=C_CYAN, bold=True, z=26), max_w=3.62).move_to([-4.22, 1.76, 0])
        in_node_6b = pill("단일 원문", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.4, px=0.10, py=0.04, z=26).move_to([-5.42, 0.20, 0])
        fan_targets = VGroup(
            fit(pill("지급액, 감액, 면책 개별 질의", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=10.2, px=0.08, py=0.035, z=26), max_w=2.48).move_to([-3.50, 1.06, 0]),
            fit(pill(f"표준담보 {num(cov_in_use)}개 매핑", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=10.2, px=0.08, py=0.035, z=26), max_w=2.48).move_to([-3.50, 0.48, 0]),
            fit(pill(f"{TERM['rider_cond']} 개별 질의 ({sep_p0:.2f}, {sep_p1:.2f})", fg=C_GOLD, bg="#383016", border=C_GOLD, size=10.0, px=0.08, py=0.035, z=26), max_w=2.50).move_to([-3.50, -0.10, 0]),
            fit(pill(f"{TERM['trend']} 선별, 병합", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=10.2, px=0.08, py=0.035, z=26), max_w=2.48).move_to([-3.50, -0.68, 0]),
        )
        fan_arrows = VGroup(*[arrow_2d(in_node_6b.get_right(), ft.get_left(), color=C_GOLD if idx == 2 else C_CYAN, sw=1.9, tip=0.08, z=26) for idx, ft in enumerate(fan_targets)])
        batch_foot = fit(txt("원문 일치 항목은 질의 생략, 부가 조건은 개별 분리", size=10.4, color=C_INK_0, z=26), max_w=3.64).move_to([-4.22, -1.62, 0])

        hud_6b_top = fit(
            pill(
                f"해결 ② 대칭 선택지('조건 있음 / 없음')와 개별 질의로 기준면({v_conf:.2f}, {v_reex:.2f}) 상하로 확률 분리",
                fg=C_DARK_INK,
                bg=C_GOLD,
                border=WHITE,
                size=11.8,
                z=25,
            ),
            max_w=12.00,
        ).move_to([0.0, 2.58, 0])
        calib_chip = fit(
            pill(
                f"임계값 보정: 인위적 오류 반전 {num(cal_flip['rows'])}행 중 확정 통과 {num(cal_flip['passed'])}행 ({TERM['ours']} 요약서 소규모 표본 기준) ✓",
                fg=C_MINT,
                bg="#091018",
                border=C_MINT,
                size=11.4,
                z=25,
            ),
            max_w=12.00,
        ).move_to([0.0, -2.68, 0])
        hud_6b_grp = VGroup(hud_6b_top, batch_card, batch_hdr, in_node_6b, fan_targets, fan_arrows, batch_foot, calib_chip)

        pb_z0 = -0.22
        pb_h = 1.76
        pb_cx = 1.65
        pb_floor = floor_grid_3d(-1.35, 4.65, -1.10, 1.10, z_val=pb_z0, step_x=1.50, step_y=1.10, col=C_CYAN_DIM)

        z_plane_75 = pb_z0 + v_conf * pb_h
        z_plane_40 = pb_z0 + v_reex * pb_h
        plane_75 = glass_plane_3d(pb_cx, 0.0, z_plane_75, 6.00, 2.28, C_GOLD, fill_op=0.16, sw=2.3, tier=2.0)
        plane_40 = glass_plane_3d(pb_cx, 0.0, z_plane_40, 6.00, 2.28, C_CORAL, fill_op=0.15, sw=2.1, tier=-2.0)
        pb_cuts = [(z_plane_40, -4.0), (z_plane_75, 0.0)]

        y_bef, y_aft = 0.56, -0.48
        x_p = [-0.60, 0.90, 2.40, 3.90]

        p_bef_bars = VGroup(
            pillar_3d_sliced(x_p[0], y_bef, 0.66, 0.52, tf_rng["low"] * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_AMBER, opacity=0.76, stroke_col=C_AMBER),
            pillar_3d_sliced(x_p[1], y_bef, 0.66, 0.52, tf_rng["high"] * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_AMBER, opacity=0.80, stroke_col=WHITE),
            pillar_3d_sliced(x_p[2], y_bef, 0.66, 0.52, bnd_chk["bundled_probability"] * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_CORAL, opacity=0.86, stroke_col=WHITE),
        )

        p_aft_bars = VGroup(
            pillar_3d_sliced(x_p[0], y_aft, 0.66, 0.52, sym_prob["correct_min"] * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_GOLD, opacity=0.92, stroke_col=WHITE, sw=1.6),
            pillar_3d_sliced(x_p[1], y_aft, 0.66, 0.52, sym_prob["correct_min"] * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_GOLD, opacity=0.92, stroke_col=WHITE, sw=1.6),
            pillar_3d_sliced(x_p[2] - 0.22, y_aft, 0.35, 0.48, sep_p0 * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_CYAN, opacity=0.88, stroke_col=WHITE, sw=1.4),
            pillar_3d_sliced(x_p[2] + 0.22, y_aft, 0.35, 0.48, sep_p1 * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_CYAN, opacity=0.88, stroke_col=WHITE, sw=1.4),
            pillar_3d_sliced(x_p[3], y_aft, 0.66, 0.52, sym_prob["flipped_max"] * pb_h, base_z=pb_z0, cuts=pb_cuts, top_tier=4.0, col=C_CORAL, opacity=0.90, stroke_col=C_CORAL, sw=1.4),
        )

        bb_pl_75 = bb_badge(f"확정 기준면 {v_conf:.2f}", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.8).move_to([4.55, 1.08, z_plane_75 + 0.16])
        bb_pl_40 = bb_badge(f"재추출 기준면 {v_reex:.2f}", fg=C_WHITE, bg="#3B1219", border=C_CORAL, size=11.8).move_to([4.55, 1.08, z_plane_40 - 0.08])
        bb_y_bef = bb_badge(f"후면: 변경 전 (참/거짓, {TERM['batch_query']})", fg=C_AMBER, bg="#1A1206", border=C_AMBER, size=10.8).move_to([-0.38, y_bef + 0.68, pb_z0 + 0.14])
        bb_y_aft = bb_badge("전면: 변경 후 (대칭, 개별 질의)", fg=C_GOLD, bg="#181408", border=C_GOLD, size=10.6).move_to([1.35, -1.48, pb_z0 - 0.18])

        bb_bef_rng = bb_badge(f"참/거짓 {tf_rng['low']:.2f}~{tf_rng['high']:.2f}", fg=C_AMBER, bg="#1A1206", border=C_AMBER, size=11.4).move_to([x_p[1] + 0.05, y_bef + 0.36, pb_z0 + tf_rng["high"] * pb_h + 0.48])
        bb_bef_bnd = bb_badge(f"{TERM['batch_query']} {bnd_chk['bundled_probability']:.2f} 오류 통과 ×", fg=C_WHITE, bg="#3B1219", border=C_CORAL, size=11.4).move_to([x_p[2] + 0.45, y_bef + 0.28, pb_z0 + bnd_chk["bundled_probability"] * pb_h + 0.32])

        bb_aft_corr = bb_badge(f"정상 값 {sym_prob['correct_min']:.2f}↑", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=12.4).move_to([x_p[0] - 0.15, y_aft - 0.16, pb_z0 + sym_prob["correct_min"] * pb_h + 0.28])
        bb_aft_sep = bb_badge(f"개별 질의 {sep_p0:.2f}, {sep_p1:.2f} 검출 ✓", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=11.4).move_to([x_p[2] + 0.18, y_aft - 0.02, pb_z0 + sep_p1 * pb_h + 0.50])
        bb_aft_flip = bb_badge(f"반전 오류값 {sym_prob['flipped_max']:.2f}↓", fg=C_CORAL, bg="#2A0F14", border=C_CORAL, size=11.4).move_to([x_p[3] - 0.12, y_aft + 0.08, pb_z0 + sym_prob["flipped_max"] * pb_h + 0.42])

        bbs_6b_init = [bb_pl_75, bb_pl_40, bb_y_bef, bb_y_aft, bb_bef_rng, bb_bef_bnd]
        bbs_6b_aft = [bb_aft_corr, bb_aft_sep, bb_aft_flip]
        all_6b_bbs = [*bbs_6b_init, *bbs_6b_aft]

        self.register_billboards(*all_6b_bbs)
        self.add_fixed_in_frame_mobjects(hud_6b_grp)
        self.remove(calib_chip)

        self.cam_move(
            phi=58 * DEGREES,
            theta=-62 * DEGREES,
            zoom=0.92,
            center=[0.55, 0.0, 0.22],
            anims=[
                FadeOut(beat6a_all, shift=UP * 0.10),
                FadeIn(VGroup(hud_6b_top, batch_card, batch_hdr, in_node_6b, batch_foot), shift=RIGHT * 0.08),
                LaggedStart(*[GrowArrow(fa) for fa in fan_arrows], lag_ratio=0.06),
                LaggedStart(*[FadeIn(ft, shift=RIGHT * 0.06) for ft in fan_targets], lag_ratio=0.06),
                FadeIn(pb_floor),
                FadeIn(VGroup(plane_40, plane_75)),
                LaggedStart(*[FadeIn(pb, shift=OUT * 0.35) for pb in p_bef_bars], lag_ratio=0.09),
                FadeIn(VGroup(*bbs_6b_init)),
            ],
            rt=1.65,
        )
        self.remove(beat6a_all)
        self.wait(2.00)

        self.add_fixed_in_frame_mobjects(calib_chip)
        self.cam_move(
            phi=50 * DEGREES,
            theta=-30 * DEGREES,
            zoom=0.90,
            center=[0.58, -0.02, 0.24],
            anims=[
                LaggedStart(*[FadeIn(pa, shift=OUT * 0.45) for pa in p_aft_bars], lag_ratio=0.08),
                FadeIn(VGroup(*bbs_6b_aft)),
                FadeIn(calib_chip, shift=UP * 0.08),
            ],
            rt=2.10,
        )
        self.check_bounds(hud_6b_grp, "CH6B HUD")
        self.wait(4.40)

        prob_3d_all = VGroup(pb_floor, plane_40, plane_75, p_bef_bars, p_aft_bars)

        # -------------------------------------------------------------------
        # Beat 6C: 정밀 NPU 3갈래 라우터 스위치보드 + 60초 토큰 윈도우 & 시장 동향 실측 가로 막대 차트
        # -------------------------------------------------------------------
        win_sec = win_cfg["window_seconds"]
        win_margin = win_cfg["margin_pct"]
        lim_tok = pm_lim["tokens"]

        hb = self.update_subtitle(
            hb,
            f"해결 ③, ④ 확률 임계값({v_conf:.2f}, {v_reex:.2f})으로 분기하고, 최근 {num(win_sec)}초 입력 토큰을 {num(guard_tok)} 이하로 제어합니다",
        )

        # 좌측 NPU 라우터 허브 (기존 폴리곤 노즐 대체)
        router_hub_box = RoundedRectangle(corner_radius=0.10, width=1.86, height=1.56, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.2).move_to([-4.98, 0.42, 0]).set_z_index(5)
        router_ic = svg_icon("cpu_decide", size=0.52, col=C_GOLD, accent=C_CYAN, tile=False, sw=2.2, z=8).move_to([-4.98, 0.78, 0])
        router_lbl = fit(
            VGroup(
                txt("해결 ③ 임계값", size=10.6, color=C_CYAN, bold=True, z=8),
                txt("분기 라우터", size=11.4, color=C_GOLD, bold=True, z=8),
            ).arrange(DOWN, buff=0.03),
            max_w=1.64,
        ).move_to([-4.98, 0.08, 0])
        router_hub = VGroup(router_hub_box, router_ic, router_lbl)

        gate_x, th_high_y, th_low_y = -2.92, 1.24, -0.32
        meter_bar = Line([gate_x, -1.68, 0], [gate_x, 2.36, 0], color=C_SLATE, stroke_width=3.2).set_z_index(4)
        line_75 = DashedLine([-3.15, th_high_y, 0], [1.38, th_high_y, 0], dash_length=0.10, color=C_GOLD, stroke_width=1.9).set_z_index(3)
        line_40 = DashedLine([-3.15, th_low_y, 0], [1.38, th_low_y, 0], dash_length=0.10, color=C_CORAL, stroke_width=1.9).set_z_index(3)
        knob_75 = pill(f"확률 {v_conf:.2f} 기준", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.0, px=0.10, py=0.04).move_to([gate_x, th_high_y + 0.26, 0]).set_z_index(8)
        knob_40 = pill(f"확률 {v_reex:.2f} 기준", fg=WHITE, bg=C_CORAL, border=WHITE, size=11.0, px=0.10, py=0.04).move_to([gate_x, th_low_y - 0.26, 0]).set_z_index(8)

        z_top = RoundedRectangle(corner_radius=0.08, width=3.18, height=0.92, fill_color="#232B1E", fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=2.2).move_to([-0.14, 1.84, 0]).set_z_index(4)
        zt_ic = svg_icon("database_master", size=0.44, col=C_GOLD, accent=C_MINT, z=7).move_to([-1.36, 1.84, 0])
        zt_lbl = fit(VGroup(txt(f"{v_conf:.2f} 이상: 자동 확정", size=12.4, color=C_GOLD, bold=True, z=6), txt(f"{TERM['master']} 시트 반영", size=10.8, color=C_INK_0, z=6)).arrange(DOWN, aligned_edge=LEFT, buff=0.04), max_w=2.36).move_to([0.22, 1.84, 0])

        z_mid = RoundedRectangle(corner_radius=0.08, width=3.18, height=0.96, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.2).move_to([-0.14, 0.46, 0]).set_z_index(4)
        zm_ic = svg_icon("doc_check", size=0.44, col=C_CYAN, accent=C_WHITE, z=7).move_to([-1.36, 0.46, 0])
        zm_lbl = fit(VGroup(txt(f"{v_reex:.2f}~{v_conf:.2f}: {TERM['review_wait']} 이관", size=12.0, color=C_WHITE, bold=True, z=6), txt("원문 근거와 함께 표시", size=10.6, color=C_CYAN, z=6)).arrange(DOWN, aligned_edge=LEFT, buff=0.04), max_w=2.36).move_to([0.22, 0.46, 0])

        z_bot = RoundedRectangle(corner_radius=0.08, width=3.18, height=0.96, fill_color="#281419", fill_opacity=0.96, stroke_color=C_CORAL, stroke_width=2.1).move_to([-0.14, -1.10, 0]).set_z_index(4)
        zb_ic = svg_icon("agent_bot", size=0.44, col=C_CORAL, accent=C_VIOLET, z=7).move_to([-1.36, -1.10, 0])
        excl_lbl = fit(
            VGroup(
                txt(f"{v_reex:.2f} 미만: 타 모델 재추출", size=11.8, color=C_CORAL, bold=True, z=6),
                txt(f"오류 행 {cal_band['wrong_caught_pct']}% 이관 ({TERM['ours']} 소규모 표본)", size=9.8, color=C_INK_0, z=6),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.04),
            max_w=2.38,
        ).move_to([0.22, -1.10, 0])

        retry_arc = CubicBezier(
            np.array([-1.73, -1.10, 0]), np.array([-2.30, -2.06, 0]), np.array([-4.30, -2.06, 0]), np.array([-4.98, -0.36, 0]), color=C_VIOLET, stroke_width=2.3
        ).set_z_index(4)
        retry_lbl = pill("보조, 상위 모델 재추출 루프", fg=C_VIOLET, bg=C_PANEL, border=C_VIOLET, size=10.4, px=0.10, py=0.035).move_to([-3.38, -1.96, 0]).set_z_index(7)

        # 우측: 60초 토큰 슬라이딩 윈도우 + 시장 동향 7분류 실측 가로 막대 차트
        mkt_card = RoundedRectangle(
            corner_radius=0.09, width=4.22, height=4.44, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_VIOLET, stroke_width=2.3
        ).move_to([3.86, 0.24, 0]).set_z_index(4)
        mkt_title = fit(
            VGroup(
                svg_icon("calendar_clock", size=0.38, col=C_VIOLET, accent=C_GOLD, z=8),
                txt(f"{num(win_sec)}초 토큰 윈도우와 {TERM['trend']} {num(cat_cnt)}분류", size=11.8, color=C_VIOLET, bold=True, z=7),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.96,
        ).move_to([3.86, 2.08, 0])

        rule_bar_w = 3.72
        guard_bar_w = rule_bar_w * (guard_tok / lim_tok)
        rule_bar_bg = RoundedRectangle(corner_radius=0.04, width=rule_bar_w, height=0.26, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.4).move_to([3.86, 1.62, 0]).set_z_index(6)
        rule_bar_guard = RoundedRectangle(corner_radius=0.03, width=guard_bar_w, height=0.18, fill_color="#1A5642", fill_opacity=0.88, stroke_color=C_MINT, stroke_width=1.2).move_to([3.86 - rule_bar_w / 2 + guard_bar_w / 2, 1.62, 0]).set_z_index(7)
        win_bracket = RoundedRectangle(corner_radius=0.04, width=1.18, height=0.34, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.2).move_to([2.68, 1.62, 0]).set_z_index(8)
        safe_txt = fit(
            txt(f"대기 기준: 최근 {num(win_sec)}초 추정치 {num(guard_tok)} / 한도 {num(lim_tok)} (여유 {num(win_margin)}%, 실측 아님)", size=9.8, color=C_MINT, bold=True, z=8),
            max_w=3.94,
        ).move_to([3.86, 1.26, 0])

        max_cat_v = max(cats_by_cnt.values())
        cat_bar_max_w = 1.62
        cat_rows = VGroup()
        cat_colors = [C_GOLD, C_MINT, C_CYAN, C_CORAL, C_VIOLET, C_AMBER, C_INK_0]
        sorted_cats = sorted(cat_list, key=lambda nm: cats_by_cnt[nm], reverse=True)
        for idx, c_nm in enumerate(sorted_cats):
            cy_r = 0.86 - idx * 0.34
            cnt_v = cats_by_cnt[c_nm]
            bw_c = max(0.08, cat_bar_max_w * (cnt_v / max_cat_v))
            col_c = cat_colors[idx % len(cat_colors)]
            nm_t = fit(txt(c_nm, size=10.0, color=C_INK_0, bold=True, z=7), max_w=1.42).move_to([2.68, cy_r, 0])
            b_bg = RoundedRectangle(corner_radius=0.03, width=cat_bar_max_w, height=0.18, fill_color=C_BG_SUB, fill_opacity=0.95, stroke_width=0).move_to([3.52 + cat_bar_max_w / 2, cy_r, 0]).set_z_index(6)
            b_fg = RoundedRectangle(corner_radius=0.03, width=bw_c, height=0.18, fill_color=col_c, fill_opacity=0.92, stroke_width=0).move_to([3.52 + bw_c / 2, cy_r, 0]).set_z_index(7)
            val_t = txt(f"{num(cnt_v)}건", size=10.0, color=col_c, bold=True, z=8).move_to([5.52, cy_r, 0])
            cat_rows.add(VGroup(nm_t, b_bg, b_fg, val_t))

        mkt_foot = fit(txt(f"{TERM['snapshot']} {TERM['trend']} 합계 {num(news_total)}건, 초기 적재는 {TERM['extract_dual']} {TERM['cross_verify']}", size=10.0, color=C_GOLD, bold=True, z=7), max_w=3.94).move_to([3.86, -1.66, 0])
        mkt_group = VGroup(mkt_card, mkt_title, rule_bar_bg, rule_bar_guard, win_bracket, safe_txt, cat_rows, mkt_foot)

        quota_bar = fit(
            pill(
                f"한도 점검: 한도 초과 실패 기록은 {num(quota_fails)}건이나 재시도 성공 호출은 미기록되어 한도 초과 여부는 미확인 (오류 반전 {num(cal_flip['rows'])}행 통과 {num(cal_flip['passed'])}행, {TERM['ours']} 소규모 표본)",
                fg=C_INK_0,
                bg=C_PANEL_HI,
                border=C_SLATE,
                size=10.8,
            ),
            max_w=12.00,
        ).move_to([0.0, -2.58, 0]).set_z_index(9)

        self.reset_cam_2d(
            anims=[
                FadeOut(prob_3d_all),
                FadeOut(VGroup(*all_6b_bbs)),
                FadeOut(hud_6b_grp),
                FadeIn(router_hub, shift=RIGHT * 0.12),
                Create(meter_bar),
                Create(line_75),
                Create(line_40),
                FadeIn(knob_75),
                FadeIn(knob_40),
                FadeIn(VGroup(z_top, zt_ic, zt_lbl, z_mid, zm_ic, zm_lbl, z_bot, zb_ic, excl_lbl)),
                Create(retry_arc),
                FadeIn(retry_lbl),
                FadeIn(VGroup(mkt_card, mkt_title, rule_bar_bg, rule_bar_guard, win_bracket, safe_txt, mkt_foot), shift=LEFT * 0.14),
                LaggedStart(*[FadeIn(cr) for cr in cat_rows], lag_ratio=0.06),
            ],
            rt=1.35,
        )
        self.clear_billboards(*all_6b_bbs)
        self.remove_fixed_in_frame_mobjects(hud_6b_grp)
        self.remove(prob_3d_all, hud_6b_grp)
        self.wait(1.20)

        p_start = router_hub_box.get_right()
        particles, mkt_pulses = VGroup(), VGroup()
        stream_anims = []
        for k in range(5):
            end_y = 1.66 + (k % 3) * 0.18
            pt = glow_dot(p_start, color=C_GOLD, r=0.060, z=12)
            particles.add(pt)
            stream_anims.append(
                Succession(Wait(k * 0.12), MoveAlongPath(pt, CubicBezier(p_start, p_start + RIGHT * 0.9, np.array([-2.3, end_y, 0]), np.array([-1.73, end_y, 0])), run_time=1.35))
            )
        for k in range(3):
            end_y = 0.34 + (k % 2) * 0.24
            pt = glow_dot(p_start, color=C_CYAN, r=0.060, z=12)
            particles.add(pt)
            stream_anims.append(
                Succession(Wait(0.15 + k * 0.16), MoveAlongPath(pt, CubicBezier(p_start, p_start + RIGHT * 0.9, np.array([-2.3, end_y, 0]), np.array([-1.73, end_y, 0])), run_time=1.35))
            )
        for k, sy in enumerate([0.86, 0.52, 0.18]):
            mp = glow_dot([1.45, 1.84, 0], color=C_VIOLET, r=0.060, z=13)
            mkt_pulses.add(mp)
            stream_anims.append(
                Succession(
                    Wait(0.30 + k * 0.22),
                    MoveAlongPath(mp, CubicBezier(np.array([1.45, 1.84, 0]), np.array([1.72, sy + 0.3, 0]), np.array([1.72, sy, 0]), np.array([1.95, sy, 0])), run_time=1.20),
                )
            )

        rescue_pt = glow_dot(p_start, color=C_VIOLET, r=0.064, z=13)
        self.add(particles, mkt_pulses, rescue_pt)

        self.cam_move(
            zoom=1.26,
            center=[-1.85, -0.10, 0],
            anims=[
                *stream_anims,
                MoveAlongPath(rescue_pt, CubicBezier(p_start, p_start + RIGHT * 0.85, np.array([-2.3, -1.10, 0]), np.array([-1.73, -1.10, 0])), run_time=1.20),
            ],
            rt=1.75,
        )
        self.wait(1.75)

        self.cam_move(
            zoom=1.30,
            center=[2.75, 0.28, 0],
            anims=[
                FadeOut(mkt_pulses, scale=0.4),
                MoveAlongPath(rescue_pt, retry_arc, run_time=1.15),
                win_bracket.animate.move_to([4.92, 1.62, 0]),
                LaggedStart(*[Indicate(cr[2], color=WHITE, scale_factor=1.08) for cr in cat_rows[:4]], lag_ratio=0.10),
            ],
            rt=1.50,
        )
        self.remove(mkt_pulses, *mkt_pulses)
        self.wait(1.80)

        self.reset_cam_2d(
            anims=[
                MoveAlongPath(
                    rescue_pt,
                    CubicBezier(np.array([-4.98, -0.36, 0]), np.array([-3.4, 1.84, 0]), np.array([-2.3, 1.84, 0]), np.array([-1.73, 1.84, 0])),
                ),
                FadeOut(particles, scale=0.4),
                FadeIn(quota_bar, shift=UP * 0.08),
            ],
            rt=1.15,
        )
        self.play(FadeOut(rescue_pt, scale=0.4), run_time=0.25)
        self.remove(particles, *particles, rescue_pt)

        ch6_stage = VGroup(
            router_hub, meter_bar, line_75, line_40, knob_75, knob_40,
            z_top, zt_ic, zt_lbl, z_mid, zm_ic, zm_lbl, z_bot, zb_ic, excl_lbl, retry_arc, retry_lbl,
            mkt_group, quota_bar,
        )
        self.check_bounds(ch6_stage, "CH6C ROUTER & BAR CHART")
        self.wait(4.50)

        self.fade_out_part(ch6_stage, hl, hr, hb)
