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


class Part3DecisionScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        decide_model = fact("models", "decide")
        rel_date = fact("decision_model_release_date")
        d_spec = fact("decision_model_spec")
        d_uses = fact("decision_model_uses")
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
        # 5장: 판정 모델의 원리와 적용 영역 (100% Pure 2D)
        # ===================================================================
        hl, hr, hb = self.make_hud(
            5,
            f"판정 모델 {decide_model}: 선택지마다 확률만 돌려주는 방식",
            "판정 모델은 글을 쓰지 않고 정해진 선택지마다 확률만 돌려줍니다",
        )

        # -------------------------------------------------------------------
        # Beat 5A: Pure 2D Generative Model vs Non-Generative Decision Model
        # -------------------------------------------------------------------
        gen_card = RoundedRectangle(
            corner_radius=0.09, width=4.16, height=4.52, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_SLATE, stroke_width=2.0
        ).move_to([-4.02, 0.05, 0]).set_z_index(3)
        gen_hdr = fit(pill("일반 문장 생성 호출 (작문 방식)", fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=11.0), max_w=3.80).move_to([-4.02, 1.86, 0]).set_z_index(6)

        sw_c = np.array([-5.38, 1.14, 0.0])
        sw_ring = Circle(radius=0.26, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_AMBER, stroke_width=2.0).move_to(sw_c).set_z_index(7)
        sw_hand = Line(sw_c, sw_c + UP * 0.21, color=C_AMBER, stroke_width=2.4).set_z_index(11)

        gen_tok_row = fit(
            VGroup(
                pill('"특약"', fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.4, px=0.08, py=0.04),
                pill('"검토"', fg=C_INK_0, bg=C_PANEL_HI, border=C_SLATE, size=10.4, px=0.08, py=0.04),
                pill('"서술..."', fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=10.4, px=0.08, py=0.04),
                pill("(예시)", fg=C_INK_2, bg=C_BG_SUB, border=C_SLATE, size=9.6, px=0.07, py=0.04),
            ).arrange(RIGHT, buff=0.07),
            max_w=3.05,
        ).move_to([-3.52, 1.14, 0]).set_z_index(6)

        wob_fn = ParametricFunction(
            lambda u: np.array([-5.65 + u * 3.26, 0.28 + 0.16 * math.sin(8.0 * u), 0.0]),
            t_range=[0, 1, 0.02],
            color=C_AMBER,
            stroke_width=2.4,
        ).set_z_index(6)
        wob_lbl = fit(txt("문장 토큰을 출력하는 서술 방식 (예시 그림)", size=9.4, color=C_INK_1, bold=True, z=6), max_w=3.82).move_to([-4.02, -0.22, 0])

        gen_gauges = fit(
            VGroup(
                pill("문장 출력 토큰 발생", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=9.2, px=0.09, py=0.05),
                pill(f"판정 모델은 출력 토큰 {num(d_spec['output_tokens'])}", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.2, px=0.09, py=0.05),
            ).arrange(RIGHT, buff=0.10),
            max_w=3.82,
        ).move_to([-4.02, -0.92, 0]).set_z_index(6)
        gen_foot = fit(pill(f"채점과 분류는 최대 {num(d_spec['items_per_call'])}문항 확률 반환 사양으로 처리", fg=C_INK_1, bg=C_PANEL_HI, border=C_SLATE, size=9.4, z=6), max_w=3.82).move_to([-4.02, -1.64, 0])
        gen_grp = VGroup(gen_card, gen_hdr, sw_ring, sw_hand, gen_gauges, gen_foot)

        shift_arrow = arrow_2d([-1.82, 0.05, 0], [-0.96, 0.05, 0], color=C_GOLD, sw=2.8, tip=0.15, z=8)
        shift_lbl = pill("문장 생성 생략", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.4, px=0.09, py=0.04, z=9).move_to([-1.39, 0.48, 0])

        dec_card = RoundedRectangle(
            corner_radius=0.09, width=6.92, height=4.52, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_GOLD, stroke_width=2.2
        ).move_to([2.62, 0.05, 0]).set_z_index(3)
        dec_top_row = fit(
            VGroup(
                pill(f"{rel_date} 출시", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.4, px=0.11, py=0.04),
                txt(f"비생성 판정 모델 {decide_model}", size=13.6, color=C_GOLD, bold=True, z=7),
            ).arrange(RIGHT, buff=0.16),
            max_w=6.45,
        ).move_to([2.62, 1.86, 0]).set_z_index(7)

        dec_in = pill("특약 원문과 문항", fg=C_INK_0, bg=C_PANEL_HI, border=C_CYAN, size=10.0, px=0.10, py=0.06, z=7).move_to([0.22, 0.84, 0])
        dec_core = RoundedRectangle(
            corner_radius=0.08, width=1.96, height=0.98, fill_color="#1D2736", fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.2
        ).move_to([2.24, 0.84, 0]).set_z_index(6)
        dec_core_t = fit(
            VGroup(
                txt(decide_model, size=11.0, color=C_GOLD, bold=True, z=7),
                txt(f"출력 토큰 = {num(d_spec['output_tokens'])}", size=9.8, color=C_MINT, bold=True, z=7),
            ).arrange(DOWN, buff=0.05),
            max_w=1.80,
        ).move_to(dec_core)
        dec_in_arr = arrow_2d(dec_in.get_right(), dec_core.get_left(), color=C_CYAN, sw=2.0, tip=0.10, z=7)

        w_scale = 1.18
        w_corr = w_scale * sym_prob["correct_min"]
        w_flip = w_scale * sym_prob["flipped_max"]
        dec_bars, dec_out_arrs = VGroup(), VGroup()
        for b_i, (by, b_lbl, b_val, b_w, b_col) in enumerate(
            [
                (1.06, "맞는 값", f"{sym_prob['correct_min']:.2f}↑", w_corr, C_GOLD),
                (0.62, "뒤집은 값", f"{sym_prob['flipped_max']:.2f}↓", w_flip, C_SLATE),
            ]
        ):
            dec_out_arrs.add(arrow_2d(dec_core.get_right(), [3.38, by, 0], color=C_GOLD if b_i == 0 else C_SLATE, sw=1.7, tip=0.09, z=6))
            lt = txt(b_lbl, size=9.6, color=C_INK_1 if b_i > 0 else WHITE, bold=(b_i == 0), z=7).move_to([3.82, by, 0])
            br = Rectangle(width=b_w, height=0.18, fill_color=b_col, fill_opacity=0.95, stroke_width=0).move_to([4.28 + b_w / 2, by, 0]).set_z_index(7)
            vt = txt(b_val, size=9.8, color=C_GOLD if b_i == 0 else C_INK_2, bold=(b_i == 0), z=7).next_to(br, RIGHT, buff=0.08)
            dec_bars.add(VGroup(lt, br, vt))

        dec_div = Line([-0.55, 0.06, 0], [5.80, 0.06, 0], color=C_SLATE, stroke_width=1.2).set_z_index(5)
        dec_use_hdr = fit(
            txt(f"이 앱이 판정 모델을 쓴 {num(len(d_uses))}가지 일 (기존 상품 초기 적재는 두 판독 교차 확인)", size=10.0, color=C_WHITE, bold=True, z=7),
            max_w=6.45,
        ).move_to([2.62, -0.24, 0])

        def app_tile(tx: float, ty: float, col: str, icon_g: VGroup, label_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.06, width=3.06, height=0.66, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=col, stroke_width=1.6
            ).move_to([tx, ty, 0]).set_z_index(6)
            icon_g.move_to([tx - 1.15, ty, 0]).set_z_index(8)
            lb = fit(txt(label_s, size=10.2, color=col, bold=True, z=8), max_w=2.24).move_to([tx + 0.24, ty, 0])
            return VGroup(bx, icon_g, lb)

        ic_u1 = VGroup(
            RegularPolygon(n=6, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_CYAN, stroke_width=1.6).scale(0.18),
            txt("✓", size=9.5, color=C_CYAN, bold=True),
        )
        ic_u2 = VGroup(
            arrow_2d([-0.16, 0, 0], [0.14, 0.14, 0], color=C_GOLD, sw=1.8, tip=0.07),
            arrow_2d([-0.16, 0, 0], [0.14, -0.14, 0], color=C_GOLD, sw=1.8, tip=0.07),
        )
        ic_u3 = VGroup(
            *[
                Rectangle(width=0.09, height=0.24, fill_color=c, fill_opacity=0.9, stroke_width=0).move_to([-0.12 + i * 0.12, 0, 0])
                for i, c in enumerate([C_MINT, C_CYAN, C_GOLD])
            ]
        )
        ic_u4 = VGroup(Circle(radius=0.16, fill_opacity=0.0, stroke_color=C_VIOLET, stroke_width=1.6), Dot([0, 0, 0], radius=0.05, color=C_GOLD))

        dec_uses = VGroup(
            app_tile(1.02, -0.82, C_CYAN, ic_u1, f"① {d_uses[0]}"),
            app_tile(4.24, -0.82, C_GOLD, ic_u2, f"② {d_uses[1]}"),
            app_tile(1.02, -1.62, C_MINT, ic_u3, f"③ {d_uses[2]}"),
            app_tile(4.24, -1.62, C_VIOLET, ic_u4, f"④ {d_uses[3]}"),
        )

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
        self.wait(0.75)

        self.cam_move(
            zoom=1.28,
            center=[2.45, 0.65, 0],
            anims=[
                GrowArrow(shift_arrow),
                FadeIn(shift_lbl, scale=0.85),
                FadeIn(VGroup(dec_card, dec_top_row, dec_in, dec_core, dec_core_t, dec_div, dec_use_hdr), shift=LEFT * 0.12),
                GrowArrow(dec_in_arr),
                Flash([2.24, 0.84, 0], color=C_GOLD, line_length=0.28, num_lines=10),
                LaggedStart(*[GrowArrow(oa) for oa in dec_out_arrs], lag_ratio=0.05),
                GrowFromEdge(dec_bars[0][1], LEFT),
                FadeIn(VGroup(dec_bars[0][0], dec_bars[0][2], dec_bars[1])),
            ],
            rt=1.15,
        )
        self.wait(0.75)

        self.reset_cam_2d(
            anims=[LaggedStart(*[FadeIn(u, shift=UP * 0.06, scale=0.95) for u in dec_uses], lag_ratio=0.08)],
            rt=0.95,
        )

        beat5a_all = VGroup(
            gen_grp,
            gen_tok_row,
            wob_fn,
            wob_lbl,
            shift_arrow,
            shift_lbl,
            dec_card,
            dec_top_row,
            dec_in,
            dec_in_arr,
            dec_core,
            dec_core_t,
            dec_out_arrs,
            dec_bars,
            dec_div,
            dec_use_hdr,
            dec_uses,
        )
        self.check_bounds(beat5a_all, "CH5A DECISION MODEL")
        self.wait(1.60)

        # -------------------------------------------------------------------
        # Beat 5B: Pure 2D 'gemini-decision-1' Spec & Sample Calibration (No 2D Card Tilt)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"{rel_date} 나온 {decide_model}은 한 번에 최대 {num(d_spec['items_per_call'])}문항을 받고 선택지 확률만 반환합니다",
            rt=0.40,
        )

        tl_bar = fit(
            VGroup(
                pill(f"{rel_date} {decide_model} 출시", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.4, z=8),
                arrow_2d([0, 0, 0], [0.45, 0, 0], color=C_GOLD, sw=2.2, tip=0.10, z=8),
                pill(
                    f"하루 {num(lim_decide)}회, 분당 {num(pm_lim['calls'])}회, 입력 {num(pm_lim['tokens'])}토큰 (AI Studio 무료 티어 기준)",
                    fg=C_INK_0,
                    bg=C_PANEL_HI,
                    border=C_CYAN,
                    size=10.2,
                    z=8,
                ),
            ).arrange(RIGHT, buff=0.14),
            max_w=11.80,
        ).move_to([0.0, 2.58, 0]).set_z_index(8)

        d1_c = np.array([0.0, -0.18, 0.0])
        d1_outer_dash = DashedVMobject(Circle(radius=1.16, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.0).move_to(d1_c), num_dashes=26).set_z_index(6)
        d1_ring = Circle(radius=1.04, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.4, stroke_opacity=0.75).move_to(d1_c).set_z_index(6)
        d1_core = Circle(radius=0.92, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_VIOLET, stroke_width=3.0).move_to(d1_c).set_z_index(7)
        d1_txt = fit(
            VGroup(
                txt(decide_model, size=11.8, color=C_GOLD, bold=True, z=8),
                txt(f"출력 토큰 {num(d_spec['output_tokens'])}", size=10.2, color=C_MINT, bold=True, z=8),
                txt(f"하루 {num(lim_decide)}회 무료", size=9.6, color=C_INK_1, z=8),
            ).arrange(DOWN, buff=0.06),
            max_w=1.64,
        ).move_to(d1_c)
        d1_hub_grp = VGroup(d1_outer_dash, d1_ring, d1_core, d1_txt)

        def trait_quad(qx: float, qy: float, col: str, head_s: str, vis_g: VGroup, sub_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.08, width=4.35, height=1.96, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.0
            ).move_to([qx, qy, 0]).set_z_index(4)
            th = fit(txt(head_s, size=10.8, color=col, bold=True, z=7), max_w=4.05).move_to([qx, qy + 0.68, 0])
            vis_g = fit(vis_g, max_w=4.00).move_to([qx, qy - 0.02, 0]).set_z_index(7)
            ts = fit(txt(sub_s, size=9.0, color=C_INK_1, z=7), max_w=4.05).move_to([qx, qy - 0.70, 0])
            return VGroup(bx, th, vis_g, ts)

        tv1 = VGroup(
            pill("특약 조각 원문 글", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.6, px=0.08, py=0.03).move_to([-1.05, 0.16, 0]),
            pill("그 조각의 문항", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.6, px=0.08, py=0.03).move_to([-1.05, -0.20, 0]),
            arrow_2d([-0.28, 0.0, 0], [0.18, 0.0, 0], color=C_CYAN, sw=2.0, tip=0.09),
            pill("함께 전달", fg=C_GOLD, bg="#383016", border=C_GOLD, size=9.2, px=0.10, py=0.05).move_to([0.92, 0.0, 0]),
        )
        tq1 = trait_quad(-3.98, 1.02, C_CYAN, "특성 ① 이 앱의 입력 단위", tv1, "특약 조각의 원문 글과 그 조각의 문항을 함께 보냄")

        q_dots = VGroup(*[Dot([0.15 + (k % 6) * 0.21, 0.18 - (k // 6) * 0.18, 0], radius=0.042, color=C_GOLD if k % 2 == 0 else C_MINT) for k in range(18)])
        tv2 = VGroup(
            pill("원문 한 번", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=8.6, px=0.08, py=0.04).move_to([-1.18, 0.0, 0]),
            arrow_2d([-0.60, 0.0, 0], [-0.08, 0.0, 0], color=C_GOLD, sw=2.2, tip=0.09),
            q_dots,
            txt("(예시 그림)", size=7.6, color=C_INK_2).move_to([0.68, -0.34, 0]),
        )
        tq2 = trait_quad(
            3.98, 1.02, C_GOLD,
            f"특성 ② 한 번에 최대 {num(d_spec['items_per_call'])}문항 사양",
            tv2,
            f"한 번 호출에 받을 수 있는 문항 수 최대 {num(d_spec['items_per_call'])}개",
        )

        modes_3 = [
            pill("예 / 아니오", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.2, px=0.10, py=0.05),
            pill(f"{num(d_spec['choices_min'])}~{num(d_spec['choices_max'])}지선다", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD, size=9.2, px=0.10, py=0.05),
        ]
        tv3 = VGroup(*modes_3).arrange(RIGHT, buff=0.18)
        tq3 = trait_quad(-3.98, -1.38, C_VIOLET, f"특성 ③ {num(len(modes_3))}가지 정형 판정 방식", tv3, "정해진 선택지마다 확률만 돌려주는 사양")

        tv4 = VGroup(
            pill(f"뒤집은 {num(cal_flip['rows'])}줄 통과 {num(cal_flip['passed'])}줄", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.4, px=0.08, py=0.04),
            pill(f"틀린 줄 {cal_band['wrong_caught_pct']}% 재추출행", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.4, px=0.08, py=0.04),
        ).arrange(RIGHT, buff=0.10)
        tq4 = trait_quad(
            3.98, -1.38, C_MINT,
            "특성 ④ 표본에서 잰 경계값 검증",
            tv4,
            "우체국 요약서만으로 맞춘 좁은 표본 결과",
        )

        spokes_5b = VGroup(
            arrow_2d(d1_c + np.array([-0.82, 0.55, 0]), [-1.78, 0.85, 0], color=C_CYAN, sw=2.0, tip=0.10, z=6),
            arrow_2d(d1_c + np.array([0.82, 0.55, 0]), [1.78, 0.85, 0], color=C_GOLD, sw=2.0, tip=0.10, z=6),
            arrow_2d(d1_c + np.array([-0.82, -0.55, 0]), [-1.78, -1.20, 0], color=C_VIOLET, sw=2.0, tip=0.10, z=6),
            arrow_2d(d1_c + np.array([0.82, -0.55, 0]), [1.78, -1.20, 0], color=C_MINT, sw=2.0, tip=0.10, z=6),
        )

        self.add(d1_outer_dash)
        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.42,
            center=[0.0, -0.18, 0.0],
            anims=[
                FadeOut(beat5a_all, shift=UP * 0.10),
                FadeIn(VGroup(d1_ring, d1_core, d1_txt), scale=0.84),
                Rotate(d1_outer_dash, angle=PI / 2, about_point=d1_c),
            ],
            rt=0.95,
        )
        self.remove(beat5a_all)

        self.cam_move(
            zoom=1.00,
            center=[0.0, -0.10, 0.0],
            anims=[
                Rotate(d1_outer_dash, angle=PI / 2, about_point=d1_c),
                LaggedStart(*[GrowArrow(sp) for sp in spokes_5b], lag_ratio=0.06),
                LaggedStart(*[FadeIn(tq, scale=0.94) for tq in [tq1, tq2, tq3, tq4]], lag_ratio=0.08),
            ],
            rt=1.00,
        )

        self.cam_move(
            zoom=1.32,
            center=[-3.85, -0.18, 0],
            anims=[
                Circumscribe(tq1[0], color=C_CYAN, stroke_width=2.0, buff=0.03),
                Circumscribe(tq3[0], color=C_VIOLET, stroke_width=2.0, buff=0.03),
            ],
            rt=0.95,
        )
        self.wait(0.55)

        self.cam_move(
            zoom=1.32,
            center=[3.85, -0.18, 0],
            anims=[
                LaggedStart(*[Indicate(d, color=WHITE, scale_factor=1.5) for d in q_dots], lag_ratio=0.03),
                Circumscribe(tq2[0], color=C_GOLD, stroke_width=2.0, buff=0.03),
                Circumscribe(tq4[0], color=C_MINT, stroke_width=2.0, buff=0.03),
            ],
            rt=1.05,
        )
        self.wait(0.60)

        self.reset_cam_2d(anims=[FadeIn(tl_bar, shift=DOWN * 0.08)], rt=0.80)

        ch5_stage = VGroup(tl_bar, d1_hub_grp, spokes_5b, tq1, tq2, tq3, tq4)
        self.check_bounds(ch5_stage, "CH5B RADIAL TRAITS")
        self.wait(1.60)

        # ===================================================================
        # 6장: 검증, 분류 단계
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch5_stage,
            hl,
            hr,
            hb,
            6,
            "검증, 분류 단계: 분당 토큰 한도와 모호한 확률 문제를 푼 방법",
            "참/거짓 질문의 확률 겹침, 결합 제약 묶음 질문의 오류 통과, 분당 토큰 창 대기에 부딪혔습니다",
        )

        # -------------------------------------------------------------------
        # Beat 6A: Pure 2D Bottlenecks
        # -------------------------------------------------------------------
        top_res_6 = fit(
            pill(
                f"한도 조건: 호출은 하루 {num(lim_decide)}회이나 입력량은 분당 {num(pm_lim['tokens'])}토큰 상한 존재 (AI Studio 무료 티어 기준)",
                fg=C_VIOLET,
                bg=C_PANEL_HI,
                border=C_VIOLET,
                size=10.6,
                z=9,
            ),
            max_w=11.80,
        ).move_to([0.0, 2.58, 0])

        def col_diag_card(cx: float, col: str, title_s: str, foot_s: str) -> VGroup:
            bx = RoundedRectangle(
                corner_radius=0.09, width=3.76, height=4.28, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=2.1
            ).move_to([cx, -0.08, 0]).set_z_index(4)
            th = fit(txt(title_s, size=11.0, color=col, bold=True, z=7), max_w=3.44).move_to([cx, 1.66, 0])
            tf = fit(txt(foot_s, size=9.2, color=C_INK_1, z=7), max_w=3.46).move_to([cx, -1.74, 0])
            return VGroup(bx, th, tf)

        c6_1 = col_diag_card(
            -4.02, C_AMBER, "문제 ① 참/거짓 질문 시 확률 겹침",
            f"면책 조건 참/거짓 질문 시 맞는 줄도 {tf_rng['low']:.2f}~{tf_rng['high']:.2f}에 머묾",
        )
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
        lbl_mush = pill(f"{tf_rng['low']:.2f}~{tf_rng['high']:.2f} 겹침 (예시 그림)", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.6, px=0.08, py=0.03, z=8).move_to([-3.85, 1.08, 0])
        lbl_ax_c1 = txt(f"{0.0:.1f}          {tf_rng['low']:.1f}   {tf_rng['high']:.1f}        {1.0:.1f}", size=8.4, color=C_INK_2, z=6).move_to([-4.02, -1.20, 0])

        c6_2 = col_diag_card(
            0.0, C_CORAL, "문제 ② 결합 제약을 묶어 물을 때 오류 통과",
            f"결합 제약을 묶어 물으면 잘못 끼어든 특약 {num(bnd_chk['wrong_riders'])}개 통과",
        )
        bundle_loop = DashedVMobject(Circle(radius=0.92, fill_opacity=0.0, stroke_color=C_AMBER, stroke_width=2.2).move_to([-0.38, 0.10, 0]), num_dashes=22).set_z_index(6)
        b_d1 = pill("맞는 특약 (예시) ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.2, px=0.06, py=0.03, z=7).move_to([-0.38, 0.62, 0])
        b_d2 = pill("맞는 특약 (예시) ✓", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.2, px=0.06, py=0.03, z=7).move_to([-0.38, 0.24, 0])
        b_d3 = pill("잘못 끼어든 특약 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.2, px=0.06, py=0.03, z=7).move_to([-0.38, -0.14, 0])
        b_d4 = pill("잘못 끼어든 특약 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.2, px=0.06, py=0.03, z=7).move_to([-0.38, -0.52, 0])
        leak_arr = arrow_2d([0.58, 0.10, 0], [1.02, 0.10, 0], color=C_CORAL, sw=2.0, tip=0.09, z=7)
        leak_stamp = pill(f"{bnd_chk['bundled_probability']:.2f}\n통과?!", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.2, px=0.09, py=0.05, z=8).move_to([1.42, 0.10, 0])

        c6_3 = col_diag_card(
            4.02, C_VIOLET, "문제 ③ 매핑 재질의 실행 전 시간 어림",
            f"한화 대기 {num(m_req['rows'])}줄 재질의 실행 전 어림값 (분당 토큰 창 대기 포함)",
        )
        est_total_h = 2.20
        wait_ratio = m_req["waiting_minutes"] / m_req["estimated_minutes"]
        wait_h = est_total_h * wait_ratio
        therm_bg = RoundedRectangle(
            corner_radius=0.06, width=0.68, height=est_total_h, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_VIOLET, stroke_width=1.6
        ).move_to([3.12, 0.02, 0]).set_z_index(5)
        therm_wait = RoundedRectangle(
            corner_radius=0.05, width=0.56, height=wait_h, fill_color=C_AMBER, fill_opacity=0.95, stroke_width=0
        ).move_to([3.12, 0.02 - est_total_h / 2 + wait_h / 2, 0]).set_z_index(6)
        est_tag = fit(pill(f"실행 전 약 {num(m_req['estimated_minutes'])}분 어림", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.8, px=0.08, py=0.04, z=8), max_w=2.16).move_to([4.62, 0.62, 0])
        delay_tag = fit(pill(f"토큰 창 대기 약 {num(m_req['waiting_minutes'])}분 어림", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.6, px=0.08, py=0.04, z=8), max_w=2.16).move_to([4.62, -0.28, 0])

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
                FadeIn(VGroup(c6_3, therm_bg)),
            ],
            rt=1.05,
        )
        self.wait(0.65)

        self.cam_move(
            zoom=1.38,
            center=[2.15, -0.08, 0],
            anims=[
                Rotate(bundle_loop, angle=PI / 2),
                GrowArrow(leak_arr),
                FadeIn(leak_stamp, scale=1.35),
                GrowFromEdge(therm_wait, DOWN),
                FadeIn(est_tag, shift=UP * 0.06),
                FadeIn(delay_tag),
            ],
            rt=1.15,
        )
        self.wait(0.70)
        self.reset_cam_2d(rt=0.80)

        beat6a_all = VGroup(
            top_res_6,
            c6_1, ax_c1, zone_mush, curve_t, curve_f, lbl_mush, lbl_ax_c1,
            c6_2, bundle_loop, b_d1, b_d2, b_d3, b_d4, leak_arr, leak_stamp,
            c6_3, therm_bg, therm_wait, est_tag, delay_tag,
        )
        self.check_bounds(beat6a_all, "CH6A VISUAL BOTTLENECKS")
        self.wait(1.40)

        # -------------------------------------------------------------------
        # Beat 6B: True 3D Probability & Threshold Slicing Space (z=0.75 & z=0.40 Glass Planes)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ①, ② 원문을 한 번 보내되 결합 제약은 하나씩 묻고, 대칭 선택지로 맞는 값과 뒤집은 값을 갈랐습니다",
            rt=0.40,
        )

        sep_p0, sep_p1 = bnd_chk["separated_probabilities"]

        # Fixed-in-frame Left HUD (never skewed!)
        batch_card = RoundedRectangle(
            corner_radius=0.09, width=3.84, height=4.16, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-4.22, 0.06, 0]).set_z_index(25)
        batch_hdr = fit(txt("해결 ① 원문을 한 번 입력, 문항별 분리", size=11.0, color=C_CYAN, bold=True, z=26), max_w=3.54).move_to([-4.22, 1.76, 0])
        in_node_6b = pill("원문 한 번", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.0, px=0.09, py=0.04, z=26).move_to([-5.42, 0.20, 0])
        fan_targets = VGroup(
            fit(pill("지급액, 감액, 면책 따로 묻기", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.4, px=0.07, py=0.035, z=26), max_w=2.42).move_to([-3.52, 1.06, 0]),
            fit(pill(f"표준담보 {num(cov_in_use)}개 매핑", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.6, px=0.07, py=0.035, z=26), max_w=2.42).move_to([-3.52, 0.48, 0]),
            fit(pill(f"결합 제약 분리 ({sep_p0:.2f}, {sep_p1:.2f})", fg=C_GOLD, bg="#383016", border=C_GOLD, size=8.4, px=0.07, py=0.035, z=26), max_w=2.42).move_to([-3.52, -0.10, 0]),
            fit(pill("시장 소식 선별, 병합", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=8.6, px=0.07, py=0.035, z=26), max_w=2.42).move_to([-3.52, -0.68, 0]),
        )
        fan_arrows = VGroup(*[arrow_2d(in_node_6b.get_right(), ft.get_left(), color=C_GOLD if idx == 2 else C_CYAN, sw=1.7, tip=0.08, z=26) for idx, ft in enumerate(fan_targets)])
        batch_foot = fit(txt("원문 그대로인 값은 묻지 않고 제약은 개별 분리", size=8.6, color=C_INK_1, z=26), max_w=3.56).move_to([-4.22, -1.62, 0])

        hud_6b_top = fit(
            pill(
                f"해결 ② 대칭 선택지('조건 있음 / 없음')와 개별 질문이 기준면({v_conf:.2f}, {v_reex:.2f}) 위아래로 확률을 분리",
                fg=C_DARK_INK,
                bg=C_GOLD,
                border=WHITE,
                size=10.2,
                z=25,
            ),
            max_w=11.85,
        ).move_to([0.0, 2.58, 0])
        calib_chip = fit(
            pill(
                f"경계값 보정: 일부러 틀리게 바꾼 {num(cal_flip['rows'])}줄 중 확정 통과 {num(cal_flip['passed'])}줄 (우체국 요약서만으로 맞춘 좁은 표본) ✓",
                fg=C_MINT,
                bg=C_PANEL_HI,
                border=C_MINT,
                size=10.0,
                z=25,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.52, 0])
        hud_6b_grp = VGroup(hud_6b_top, batch_card, batch_hdr, in_node_6b, fan_targets, fan_arrows, batch_foot, calib_chip)

        # True 3D Probability & Slicing Threshold Space (X=문항, Y=변경 전/후, Z=확률 0..1)
        pb_z0 = -0.58
        pb_h = 2.02
        pb_cx = 1.65
        pb_floor = floor_grid_3d(-1.35, 4.65, -1.22, 1.22, z_val=pb_z0, step_x=1.50, step_y=1.22, col=C_CYAN_DIM)

        z_plane_75 = pb_z0 + v_conf * pb_h
        z_plane_40 = pb_z0 + v_reex * pb_h
        plane_75 = glass_plane_3d(pb_cx, 0.0, z_plane_75, 6.00, 2.48, C_GOLD, fill_op=0.15, sw=2.2)
        plane_40 = glass_plane_3d(pb_cx, 0.0, z_plane_40, 6.00, 2.48, C_CORAL, fill_op=0.14, sw=2.0)

        y_bef, y_aft = 0.58, -0.58
        x_p = [-0.60, 0.90, 2.40, 3.90]

        # Back row (Before: 참/거짓 질문 0.50~0.80, 결합 제약 묶음 0.80 오류 통과)
        p_bef_bars = VGroup(
            pillar_3d(x_p[0], y_bef, 0.66, 0.56, tf_rng["low"] * pb_h, base_z=pb_z0, col=C_AMBER, opacity=0.72, stroke_col=C_AMBER),
            pillar_3d(x_p[1], y_bef, 0.66, 0.56, tf_rng["high"] * pb_h, base_z=pb_z0, col=C_AMBER, opacity=0.76, stroke_col=WHITE),
            pillar_3d(x_p[2], y_bef, 0.66, 0.56, bnd_chk["bundled_probability"] * pb_h, base_z=pb_z0, col=C_CORAL, opacity=0.84, stroke_col=WHITE),
        )

        # Front row (After: 대칭 선택지 맞는 값 0.94↑, 결합 제약 분리 0.42/0.47, 뒤집은 값 0.06↓)
        p_aft_bars = VGroup(
            pillar_3d(x_p[0], y_aft, 0.66, 0.56, sym_prob["correct_min"] * pb_h, base_z=pb_z0, col=C_GOLD, opacity=0.90, stroke_col=WHITE, sw=1.5),
            pillar_3d(x_p[1], y_aft, 0.66, 0.56, sym_prob["correct_min"] * pb_h, base_z=pb_z0, col=C_GOLD, opacity=0.90, stroke_col=WHITE, sw=1.5),
            pillar_3d(x_p[2] - 0.22, y_aft, 0.35, 0.52, sep_p0 * pb_h, base_z=pb_z0, col=C_CYAN, opacity=0.86, stroke_col=WHITE, sw=1.3),
            pillar_3d(x_p[2] + 0.22, y_aft, 0.35, 0.52, sep_p1 * pb_h, base_z=pb_z0, col=C_CYAN, opacity=0.86, stroke_col=WHITE, sw=1.3),
            pillar_3d(x_p[3], y_aft, 0.66, 0.56, sym_prob["flipped_max"] * pb_h, base_z=pb_z0, col=C_CORAL, opacity=0.88, stroke_col=C_CORAL, sw=1.3),
        )

        bb_pl_75 = pill(f"확정 기준면 {v_conf:.2f}", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=8.6, px=0.08, py=0.025, z=16).move_to([4.55, 1.15, z_plane_75 + 0.14])
        bb_pl_40 = pill(f"재추출 기준면 {v_reex:.2f}", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.6, px=0.08, py=0.025, z=16).move_to([4.55, 1.15, z_plane_40 - 0.08])
        bb_y_bef = pill("뒤쪽: 변경 전 (참/거짓, 묶음)", fg=C_AMBER, bg=C_PANEL_HI, border=C_AMBER, size=8.0, px=0.07, py=0.025, z=15).move_to([-0.38, y_bef + 0.72, pb_z0 + 0.14])
        bb_y_aft = pill("앞쪽: 변경 후 (대칭, 개별)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=8.0, px=0.07, py=0.025, z=15).move_to([0.30, y_aft - 0.68, pb_z0 + 0.14])

        bb_bef_rng = pill(f"참/거짓 {tf_rng['low']:.2f}~{tf_rng['high']:.2f}", fg=C_AMBER, bg=C_BG_SUB, border=C_AMBER, size=8.4, px=0.07, py=0.025, z=16).move_to([x_p[1] + 0.05, y_bef + 0.28, pb_z0 + tf_rng["high"] * pb_h + 0.30])
        bb_bef_bnd = pill(f"묶음 {bnd_chk['bundled_probability']:.2f} 오류 통과 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.4, px=0.07, py=0.025, z=16).move_to([x_p[2] + 0.45, y_bef + 0.28, pb_z0 + bnd_chk["bundled_probability"] * pb_h + 0.30])

        bb_aft_corr = pill(f"맞는 값 {sym_prob['correct_min']:.2f}↑", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.0, px=0.08, py=0.03, z=17).move_to([x_p[0] - 0.15, y_aft - 0.18, pb_z0 + sym_prob["correct_min"] * pb_h + 0.26])
        bb_aft_sep = pill(f"분리 {sep_p0:.2f}, {sep_p1:.2f} 확인 ✓", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.4, px=0.07, py=0.025, z=17).move_to([x_p[2] - 0.05, y_aft - 0.18, pb_z0 + sep_p1 * pb_h + 0.28])
        bb_aft_flip = pill(f"뒤집은 값 {sym_prob['flipped_max']:.2f}↓", fg=C_CORAL, bg=C_BG_SUB, border=C_CORAL, size=8.6, px=0.07, py=0.025, z=17).move_to([x_p[3], y_aft - 0.05, pb_z0 + sym_prob["flipped_max"] * pb_h + 0.34])

        bbs_6b_init = [bb_pl_75, bb_pl_40, bb_y_bef, bb_y_aft, bb_bef_rng, bb_bef_bnd]
        bbs_6b_aft = [bb_aft_corr, bb_aft_sep, bb_aft_flip]
        all_6b_bbs = [*bbs_6b_init, *bbs_6b_aft]

        self.register_billboards(*all_6b_bbs)
        self.add_fixed_in_frame_mobjects(hud_6b_grp)
        self.remove(calib_chip)

        self.cam_move(
            phi=60 * DEGREES,
            theta=-64 * DEGREES,
            zoom=0.96,
            center=[0.55, 0.0, -0.05],
            anims=[
                FadeOut(beat6a_all, shift=UP * 0.10),
                FadeIn(VGroup(hud_6b_top, batch_card, batch_hdr, in_node_6b, batch_foot), shift=RIGHT * 0.08),
                LaggedStart(*[GrowArrow(fa) for fa in fan_arrows], lag_ratio=0.05),
                LaggedStart(*[FadeIn(ft, shift=RIGHT * 0.06) for ft in fan_targets], lag_ratio=0.05),
                FadeIn(pb_floor),
                FadeIn(VGroup(plane_40, plane_75)),
                LaggedStart(*[FadeIn(pb, shift=OUT * 0.35) for pb in p_bef_bars], lag_ratio=0.08),
                FadeIn(VGroup(*bbs_6b_init)),
            ],
            rt=1.20,
        )
        self.remove(beat6a_all)
        self.wait(0.50)

        self.add_fixed_in_frame_mobjects(calib_chip)
        self.cam_move(
            phi=52 * DEGREES,
            theta=-28 * DEGREES,
            zoom=1.00,
            center=[0.65, -0.05, 0.0],
            anims=[
                LaggedStart(*[FadeIn(pa, shift=OUT * 0.45) for pa in p_aft_bars], lag_ratio=0.07),
                FadeIn(VGroup(*bbs_6b_aft)),
                FadeIn(calib_chip, shift=UP * 0.08),
            ],
            rt=1.30,
        )
        self.check_bounds(hud_6b_grp, "CH6B HUD")
        self.wait(1.25)

        prob_3d_all = VGroup(pb_floor, plane_40, plane_75, p_bef_bars, p_aft_bars)

        # -------------------------------------------------------------------
        # Beat 6C: Pure 2D 3-Band Threshold Routing + 60s Token Guard Rule & 7 News Categories
        # -------------------------------------------------------------------
        win_sec = win_cfg["window_seconds"]
        win_margin = win_cfg["margin_pct"]
        lim_tok = pm_lim["tokens"]

        hb = self.update_subtitle(
            hb,
            f"해결 ③, ④ 확률 경계({v_conf:.2f}, {v_reex:.2f})로 나누고, 최근 {num(win_sec)}초 입력 토큰을 {num(guard_tok)} 아래로 맞춥니다",
            rt=0.40,
        )

        nozzle = RoundedRectangle(
            corner_radius=0.08, width=1.52, height=1.06, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-5.15, 0.40, 0]).set_z_index(5)
        noz_txt = fit(
            VGroup(
                txt("해결 ③", size=10.8, color=C_CYAN, bold=True, z=7),
                txt("확률 경계", size=12.0, color=C_VIOLET, bold=True, z=7),
                txt("분기 처리", size=11.0, color=C_INK_1, z=7),
            ).arrange(DOWN, buff=0.03),
            max_w=1.34,
        ).move_to(nozzle)

        gate_x, th_high_y, th_low_y = -2.85, 1.25, -0.32
        meter_bar = Line([gate_x, -1.70, 0], [gate_x, 2.38, 0], color=C_SLATE, stroke_width=3.0).set_z_index(4)
        line_75 = DashedLine([-3.10, th_high_y, 0], [1.48, th_high_y, 0], dash_length=0.10, color=C_GOLD, stroke_width=1.7).set_z_index(3)
        line_40 = DashedLine([-3.10, th_low_y, 0], [1.48, th_low_y, 0], dash_length=0.10, color=C_CORAL, stroke_width=1.7).set_z_index(3)
        knob_75 = pill(f"확률 {v_conf:.2f} 기준", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.2, px=0.10, py=0.04).move_to([-2.85, th_high_y + 0.25, 0]).set_z_index(8)
        knob_40 = pill(f"확률 {v_reex:.2f} 기준", fg=WHITE, bg=C_CORAL, border=WHITE, size=10.2, px=0.10, py=0.04).move_to([-2.85, th_low_y - 0.25, 0]).set_z_index(8)

        z_top = RoundedRectangle(corner_radius=0.08, width=2.76, height=0.88, fill_color="#232B1E", fill_opacity=0.94, stroke_color=C_GOLD, stroke_width=2.1).move_to([0.12, 1.85, 0]).set_z_index(4)
        zt_lbl = fit(VGroup(txt(f"{v_conf:.2f} 이상: 자동 확정", size=12.2, color=C_GOLD, bold=True, z=6), txt("정본 시트 반영", size=10.4, color=C_INK_1, z=6)).arrange(DOWN, buff=0.04), max_w=2.56).move_to(z_top)
        z_mid = RoundedRectangle(corner_radius=0.08, width=2.76, height=0.96, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_WHITE, stroke_width=2.1).move_to([0.12, 0.46, 0]).set_z_index(4)
        zm_lbl = fit(VGroup(txt(f"{v_reex:.2f}~{v_conf:.2f}: 사람 검토 이관", size=11.6, color=C_WHITE, bold=True, z=6), txt("원문 근거와 함께 제시", size=10.2, color=C_CYAN, z=6)).arrange(DOWN, buff=0.04), max_w=2.56).move_to(z_mid)
        excl_wall = Line([-1.05, -1.55, 0], [-1.05, -0.70, 0], color=C_CORAL, stroke_width=4.6).set_z_index(6)
        excl_lbl = fit(
            VGroup(
                txt(f"{v_reex:.2f} 미만: 다른 모델 재추출", size=11.4, color=C_CORAL, bold=True, z=6),
                txt(f"틀린 줄 {cal_band['wrong_caught_pct']}% 이동 (우체국 요약서 좁은 표본)", size=9.2, color=C_INK_1, z=6),
            ).arrange(DOWN, buff=0.04),
            max_w=2.72,
        ).move_to([0.35, -1.12, 0])

        retry_arc = CubicBezier(
            np.array([-1.55, -1.08, 0]), np.array([-2.05, -2.05, 0]), np.array([-4.05, -2.05, 0]), np.array([-4.42, -0.08, 0]), color=C_VIOLET, stroke_width=2.0
        ).set_z_index(4)
        retry_lbl = pill("보조, 상위 모델 재추출", fg=C_VIOLET, bg=C_PANEL, border=C_VIOLET, size=9.8, px=0.09, py=0.04).move_to([-2.95, -1.96, 0]).set_z_index(7)

        mkt_card = RoundedRectangle(
            corner_radius=0.09, width=3.96, height=4.34, fill_color=C_PANEL, fill_opacity=0.94, stroke_color=C_VIOLET, stroke_width=2.2
        ).move_to([3.92, 0.25, 0]).set_z_index(4)
        mkt_title = fit(txt(f"시장 소식 {num(cat_cnt)}분류와 {num(win_sec)}초 토큰 창", size=11.6, color=C_VIOLET, bold=True, z=7), max_w=3.68).move_to([3.92, 2.04, 0])

        rule_bar_w = 3.40
        guard_bar_w = rule_bar_w * (guard_tok / lim_tok)
        rule_bar_bg = RoundedRectangle(corner_radius=0.04, width=rule_bar_w, height=0.26, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.4).move_to([3.92, 1.56, 0]).set_z_index(6)
        rule_bar_guard = RoundedRectangle(corner_radius=0.03, width=guard_bar_w, height=0.18, fill_color="#1A5642", fill_opacity=0.85, stroke_color=C_MINT, stroke_width=1.2).move_to([3.92 - rule_bar_w / 2 + guard_bar_w / 2, 1.56, 0]).set_z_index(7)
        win_bracket = RoundedRectangle(corner_radius=0.04, width=1.18, height=0.34, fill_opacity=0.0, stroke_color=C_GOLD, stroke_width=2.0).move_to([2.85, 1.56, 0]).set_z_index(8)
        safe_txt = fit(
            txt(f"기다리는 기준: 최근 {num(win_sec)}초 어림 {num(guard_tok)} / 한도 {num(lim_tok)} (여유 {num(win_margin)}%, 잰 사용량 아님)", size=8.2, color=C_MINT, bold=True, z=8),
            max_w=3.64,
        ).move_to([3.92, 1.18, 0])

        cat_chips = VGroup()
        cat_colors = [C_GOLD, C_MINT, C_CYAN, C_CORAL, C_VIOLET, C_AMBER, C_INK_0]
        for idx, c_nm in enumerate(cat_list):
            r_c, c_c = divmod(idx, 2)
            cx_c = 3.04 if c_c == 0 else 4.80
            cy_c = 0.68 - r_c * 0.48
            col_c = cat_colors[idx % len(cat_colors)]
            ch = fit(
                pill(f"{c_nm} ({num(cats_by_cnt[c_nm])}건)", fg=col_c, bg=C_PANEL_HI, border=col_c, size=8.8, px=0.09, py=0.04, z=7),
                max_w=1.68,
            ).move_to([cx_c, cy_c, 0])
            cat_chips.add(ch)

        mkt_foot = fit(txt(f"사본 시장 소식 합계 {num(news_total)}건, 초기 적재는 두 판독 교차 확인", size=8.8, color=C_GOLD, bold=True, z=7), max_w=3.64).move_to([3.92, -1.56, 0])
        mkt_group = VGroup(mkt_card, mkt_title, rule_bar_bg, rule_bar_guard, win_bracket, safe_txt, cat_chips, mkt_foot)

        quota_bar = fit(
            pill(
                f"한도 점검: 한도 초과로 실패한 기록은 {num(quota_fails)}건이나 재시도해 성공한 호출은 기록에 남지 않아 한도를 넘겼는지는 알 수 없음 (뒤집은 {num(cal_flip['rows'])}줄 통과 {num(cal_flip['passed'])}줄, 우체국 요약서 좁은 표본)",
                fg=C_INK_0,
                bg=C_PANEL_HI,
                border=C_SLATE,
                size=9.4,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.58, 0]).set_z_index(9)

        self.reset_cam_2d(
            anims=[
                FadeOut(prob_3d_all),
                FadeOut(VGroup(*all_6b_bbs)),
                FadeOut(hud_6b_grp),
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
            ],
            rt=1.05,
        )
        self.clear_billboards(*all_6b_bbs)
        self.remove_fixed_in_frame_mobjects(hud_6b_grp)
        self.remove(prob_3d_all, hud_6b_grp)

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
        for k, sy in enumerate([0.68, 0.20, -0.28]):
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

        self.cam_move(
            zoom=1.30,
            center=[-1.65, -0.12, 0],
            anims=[
                *stream_anims,
                MoveAlongPath(blocked_pt, CubicBezier(p_start, p_start + RIGHT * 1.0, np.array([-2.2, -1.08, 0]), np.array([-1.12, -1.08, 0])), run_time=0.90),
                MoveAlongPath(rescue_pt, CubicBezier(p_start, p_start + RIGHT * 0.9, np.array([-2.3, -1.08, 0]), np.array([-1.55, -1.08, 0])), run_time=0.80),
            ],
            rt=1.35,
        )
        self.wait(0.60)

        self.cam_move(
            zoom=1.34,
            center=[2.65, 0.32, 0],
            anims=[
                FadeOut(blocked_pt, scale=0.3),
                FadeOut(mkt_pulses, scale=0.4),
                MoveAlongPath(rescue_pt, retry_arc, run_time=0.85),
                win_bracket.animate.move_to([4.85, 1.56, 0]),
                LaggedStart(*[Circumscribe(ch[0], color=C_GOLD, stroke_width=1.8, buff=0.02) for ch in cat_chips[:4]], lag_ratio=0.10),
            ],
            rt=1.10,
        )
        self.remove(blocked_pt, mkt_pulses, *mkt_pulses)
        self.wait(0.60)

        self.reset_cam_2d(
            anims=[
                MoveAlongPath(
                    rescue_pt,
                    CubicBezier(np.array([-4.42, -0.08, 0]), np.array([-3.2, 1.88, 0]), np.array([-2.0, 1.88, 0]), np.array([-1.28, 1.88, 0])),
                )
            ],
            rt=0.80,
        )

        ch6_stage = VGroup(
            nozzle, noz_txt, meter_bar, line_75, line_40, knob_75, knob_40,
            z_top, zt_lbl, z_mid, zm_lbl, excl_wall, excl_lbl, retry_arc, retry_lbl,
            particles, rescue_pt, mkt_group, quota_bar,
        )
        self.check_bounds(ch6_stage, "CH6C ROUTING & QUOTA")
        self.wait(1.75)

        self.fade_out_part(ch6_stage, hl, hr, hb)
