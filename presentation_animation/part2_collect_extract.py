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
    C_MINT,
    C_PANEL,
    C_PANEL_HI,
    C_SLATE,
    C_VIOLET,
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


class Part2CollectExtractScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        target_counts = fact("comparison_target_counts")
        target_total = sum(target_counts.values())
        fc_news = fact("first_collect_news")
        n_struct = fc_news["structured"]
        n_out = fc_news["out_of_window"]
        n_in_win = n_struct - n_out

        lim_search = fact("daily_limit_search")
        act_mins = fact("actions_free_minutes_per_month")
        op_cost = fact("operating_cost_won")
        team_sz = fact("team_size")
        news_inst_cnt = fact("market_news_institution_count")
        unpinned_msg = fact("unpinned_agent_incident")
        hf_block_code = fact("hanwhafire_block_status")
        rej_cand = fact("search_candidates_rejected")
        nav_days = fact("news_api_storage_limit_days")

        pilot_org = fact("disclosure_pilot_org")
        batch_orgs = fact("disclosure_batch_orgs")
        batch_cnt = fact("disclosure_batch_org_count")
        auto_cnt = fact("disclosure_batch_auto_org_count")
        blocked_cnt = batch_cnt - auto_cnt
        batch_pdfs = fact("disclosure_batch_pdf_count")
        batch_tests = fact("disclosure_batch_test_count")

        daily_plan = fact("collect_daily_plan")
        excl_lines = ", ".join(fact("news_excluded_lines")[:2])
        excl_topics = ", ".join(fact("news_excluded_topics")[:2])

        # ===================================================================
        # 3장: 수집 단계
        # ===================================================================
        hl, hr, hb = self.make_hud(
            3,
            f"수집 단계: 정밀 비교 대상 {num(target_total)}곳 공시와 시장 소식 수집",
            f"첫 수집 {num(n_struct)}건 가운데 구간 밖 {num(n_out)}건 유입, 접속 차단, 검색 후보 오류에 부딪혔습니다",
        )

        res_box_3 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_3 = pill("가용 자원과 한도 조건", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, z=7).move_to([-4.38, 1.92, 0])
        rg_1 = capacity_ring([-5.15, 0.72, 0], 0.58, C_AMBER, "최상위 모델", "주간 한도 빠듯", z=6)
        rg_2 = capacity_ring([-3.62, 0.72, 0], 0.58, C_CYAN, "무료 검색", f"하루 {num(lim_search)}회 상한", z=6)
        res_bars_3 = fit(
            VGroup(
                pill(f"GitHub Actions 월 {num(act_mins)}분 무료", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.6, z=7),
                pill(f"유료 수집, 뉴스 API 비용 {num(op_cost)}원", fg=C_INK_1, bg=C_BG_SUB, border=C_SLATE, size=9.6, z=7),
                txt(f"{num(team_sz)}인 체제, {num(news_inst_cnt)}개 기관 소식 점검", size=9.4, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.04,
        ).move_to([-4.38, -1.14, 0])
        res_grp_3 = VGroup(res_box_3, res_hdr_3, rg_1, rg_2, res_bars_3)
        vs_arr_3 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=1.9).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=10.4, color=col, bold=True, z=7), max_w=3.46).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        q3_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 모델 미지정 서브에이전트 실행")
        unpin_l = pill("구현 에이전트 (미지정)", fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=8.4, px=0.07, py=0.03, z=7).move_to([-1.06, 1.16, 0])
        unpin_arr = arrow_2d([-0.24, 1.16, 0], [0.16, 1.16, 0], color=C_AMBER, sw=1.8, tip=0.08, z=7)
        unpin_r = pill("최상위 모델 실행 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.4, px=0.07, py=0.03, z=7).move_to([0.96, 1.16, 0])
        q3_1_cap = fit(txt(f"{unpinned_msg} (소모량은 미기록)", size=8.6, color=C_INK_1, z=7), max_w=3.48).move_to([-0.10, 0.50, 0])

        q3_2 = diag_frame(3.88, 1.18, C_CORAL, f"문제 ② 대상 {num(target_total)}곳 구조 상이, 접속 차단")
        sk1 = RegularPolygon(n=3, fill_color=C_CYAN_DIM, fill_opacity=0.9, stroke_color=C_CYAN, stroke_width=1.5).scale(0.18).move_to([2.48, 1.24, 0]).set_z_index(6)
        sk2 = RegularPolygon(n=6, fill_color=C_PANEL_HI, fill_opacity=0.9, stroke_color=C_GOLD, stroke_width=1.5).scale(0.18).move_to([2.95, 1.24, 0]).set_z_index(6)
        sk3 = Square(side_length=0.28, fill_color=C_PANEL_HI, fill_opacity=0.9, stroke_color=C_VIOLET, stroke_width=1.5).move_to([3.42, 1.24, 0]).set_z_index(6)
        blk_arr = arrow_2d([3.68, 1.24, 0], [4.38, 1.24, 0], color=C_CORAL, sw=2.2, tip=0.10, z=7)
        blk_wall = Rectangle(width=0.16, height=0.68, fill_color=C_CORAL, fill_opacity=0.98, stroke_color=WHITE, stroke_width=1.0).move_to([4.50, 1.24, 0]).set_z_index(8)
        blk_tag = pill(f"{num(hf_block_code)} 차단 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.6, px=0.07, py=0.03, z=8).move_to([5.16, 1.24, 0])
        q3_2_cap = fit(txt("한화손해보험 목록 요청 차단, 우회하지 않기로 결정", size=8.8, color=C_INK_1, z=7), max_w=3.48).move_to([3.88, 0.50, 0])

        q3_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 검색 후보 오류와 API 보관 제한")
        m_fail1 = fit(pill(f"후보 첫째: {num(rej_cand['error_status'])} 오류 ({num(rej_cand['error_tries'])}회) ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.2, px=0.07, py=0.04, z=7), max_w=2.12).move_to([-0.92, -0.96, 0])
        m_fail2 = fit(pill(f"후보 둘째: 출처 {num(rej_cand['sources_found'])}건 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.2, px=0.07, py=0.04, z=7), max_w=2.12).move_to([-0.92, -1.42, 0])
        lock_body = RoundedRectangle(corner_radius=0.04, width=0.44, height=0.36, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=C_VIOLET, stroke_width=1.8).move_to([1.02, -1.24, 0]).set_z_index(7)
        lock_shackle = Arc(radius=0.14, start_angle=0, angle=PI, color=C_VIOLET, stroke_width=2.0).move_to([1.02, -0.98, 0]).set_z_index(7)
        lock_lbl = fit(txt(f"네이버 API 보관 {num(nav_days)}일 상한", size=8.4, color=C_VIOLET, bold=True, z=7), max_w=1.42).move_to([1.02, -1.62, 0])

        q3_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 수집 구간 밖 소식이 섞여 유입")
        dots_27_cyan, dots_27_final = VGroup(), VGroup()
        for k in range(n_struct):
            rr, cc = divmod(k, 9)
            pt_d = [2.60 + cc * 0.32, -0.82 - rr * 0.28, 0]
            is_in_window = k >= n_out
            dots_27_cyan.add(Circle(radius=0.085, fill_color=C_CYAN, fill_opacity=0.85, stroke_color=C_CYAN, stroke_width=1.0).move_to(pt_d).set_z_index(7))
            dcol = C_GOLD if is_in_window else C_CORAL
            dots_27_final.add(Circle(radius=0.085, fill_color=dcol, fill_opacity=0.95, stroke_color=WHITE if is_in_window else dcol, stroke_width=1.2).move_to(pt_d).set_z_index(7))
        q3_4_cap = fit(txt(f"정형화 {num(n_struct)}건 중 구간 밖 {num(n_out)}건, 구간 안 {num(n_in_win)}건", size=8.8, color=C_CORAL, bold=True, z=7), max_w=3.48).move_to([3.88, -1.84, 0])

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(res_grp_3, shift=RIGHT * 0.12),
                GrowArrow(vs_arr_3),
                FadeIn(VGroup(q3_1, unpin_l, q3_1_cap)),
                FadeIn(VGroup(q3_2, sk1, sk2, sk3, blk_wall, blk_tag, q3_2_cap)),
                FadeIn(VGroup(q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_lbl)),
                FadeIn(VGroup(q3_4, dots_27_cyan)),
            ],
            rt=1.15,
        )

        pkt_hit = glow_dot([3.58, 1.24, 0], color=C_CYAN, r=0.06, z=12)
        self.add(pkt_hit)
        self.cam_move(
            zoom=1.38,
            center=[1.90, 1.18, 0],
            anims=[
                GrowArrow(unpin_arr),
                FadeIn(unpin_r, scale=1.12),
                GrowArrow(blk_arr),
                MoveAlongPath(pkt_hit, CubicBezier([3.58, 1.24, 0], [4.42, 1.24, 0], [4.42, 1.24, 0], [3.85, 1.62, 0])),
                Flash([4.45, 1.24, 0], color=C_CORAL, line_length=0.22, num_lines=8),
            ],
            rt=1.15,
        )
        self.remove(pkt_hit)
        self.wait(0.65)

        date_blade = Line([2.42, -0.62, 0], [2.42, -1.58, 0], color=C_CORAL, stroke_width=4.0).set_z_index(12)
        self.add(date_blade)
        self.cam_move(
            zoom=1.52,
            center=[3.88, -1.14, 0],
            anims=[
                date_blade.animate.move_to([5.28, -1.10, 0]),
                ReplacementTransform(dots_27_cyan, dots_27_final),
                FadeIn(q3_4_cap, shift=UP * 0.06),
            ],
            rt=1.15,
        )
        self.remove(date_blade)
        self.wait(0.75)
        self.reset_cam_2d(rt=0.85)

        beat3a_all = VGroup(
            res_grp_3, vs_arr_3,
            q3_1, unpin_l, unpin_arr, unpin_r, q3_1_cap,
            q3_2, sk1, sk2, sk3, blk_arr, blk_wall, blk_tag, q3_2_cap,
            q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_lbl,
            q3_4, dots_27_final, q3_4_cap,
        )
        self.check_bounds(beat3a_all, "CH3A RESOURCE & OBSTACLES")
        self.wait(1.30)

        # -------------------------------------------------------------------
        # Beat 3B: 4-Role Agent Division
        # -------------------------------------------------------------------
        role_stages = ["조사", "총괄", "구현", "점검"]
        hb = self.update_subtitle(
            hb,
            "해결 ① 조사, 총괄(Claude), 구현, 점검으로 역할을 나누고 서브에이전트마다 모델을 명시했습니다",
            rt=0.40,
        )

        role_banner = fit(
            pill(f"해결책 ① {num(len(role_stages))}단계 분업: 작업마다 모델을 지정하고 수집 구현과 재호출 해시 점검을 분리", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.8, z=9),
            max_w=11.85,
        ).move_to([0.0, 2.58, 0])

        s1_c = np.array([-4.55, 0.25, 0.0])
        s1_hdr = pill("① 사전 조사", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=10.8, z=8).move_to([-4.55, 1.82, 0])
        s1_dome = Circle(radius=1.08, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_VIOLET, stroke_width=2.2).move_to(s1_c).set_z_index(4)
        s1_inner = Circle(radius=0.62, fill_opacity=0.0, stroke_color=C_SLATE, stroke_width=1.1).move_to(s1_c).set_z_index(5)
        s1_arm = Line(s1_c, s1_c + UP * 1.04, color=C_GOLD, stroke_width=2.8).set_z_index(8)
        s1_beacons = VGroup(
            *[
                Dot(
                    s1_c + np.array([0.86 * math.cos(k * TAU / target_total), 0.86 * math.sin(k * TAU / target_total), 0.0]),
                    radius=0.052,
                    color=C_CYAN if k < target_counts["생명보험"] else C_GOLD,
                ).set_z_index(7)
                for k in range(target_total)
            ]
        )
        s1_cap = fit(
            VGroup(
                txt(f"생명보험 {num(target_counts['생명보험'])}곳, 손해보험 {num(target_counts['손해보험'])}곳", size=9.2, color=C_INK_1, bold=True, z=7),
                txt("(총자산 기사 기준, 공식 순위 미확정)", size=8.0, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.03),
            max_w=2.62,
        ).move_to([-4.55, -1.16, 0])
        st1_grp = VGroup(s1_hdr, s1_dome, s1_inner, s1_arm, s1_beacons, s1_cap)

        s2_hdr = pill("② 총괄 지휘 (Claude)", fg=C_GOLD, bg="#383016", border=C_GOLD, size=10.8, z=8).move_to([-1.55, 1.82, 0])
        s2_mold = RegularPolygon(n=6, fill_color="#2A2312", fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.4).scale(0.62).move_to([-2.12, 0.25, 0]).set_z_index(6)
        s2_mold_t = fit(VGroup(txt(pilot_org, size=9.6, color=C_GOLD, bold=True, z=8), txt("시범 표준", size=9.0, color=WHITE, bold=True, z=8)).arrange(DOWN, buff=0.03), max_w=1.02).move_to(s2_mold)
        s2_prism = RegularPolygon(n=3, fill_color=C_CYAN_DIM, fill_opacity=0.85, stroke_color=C_CYAN, stroke_width=2.0).scale(0.46).rotate(-PI / 6).move_to([-1.08, 0.25, 0]).set_z_index(6)
        s2_rays = VGroup(*[Line([-0.82, 0.25, 0], [-0.28, -0.52 + k * 0.22, 0], color=C_GOLD if k % 2 == 0 else C_CYAN, stroke_width=1.8).set_z_index(5) for k in range(8)])
        s2_cap = fit(txt(f"시범 완성 뒤 워크플로 {num(batch_cnt)}곳 배분", size=9.2, color=C_INK_1, bold=True, z=7), max_w=2.58).move_to([-1.55, -1.16, 0])
        st2_grp = VGroup(s2_hdr, s2_mold, s2_mold_t, s2_prism, s2_rays, s2_cap)

        s3_hdr = pill(f"③ 수집 구현 ×{num(batch_cnt)}", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, z=8).move_to([1.55, 1.82, 0])
        s3_tag = pill("모델 명시 서브에이전트", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.8, px=0.08, py=0.03, z=8).move_to([1.55, 1.28, 0])
        s3_lanes = VGroup()
        for k in range(8):
            ly = 0.86 - k * 0.21
            ln_c = C_CORAL if k == 6 else C_CYAN
            s3_lanes.add(VGroup(Line([0.52, ly, 0], [2.42, ly, 0], color=ln_c, stroke_width=2.2, stroke_opacity=0.85), Dot([2.46, ly, 0], radius=0.048, color=ln_c)).set_z_index(6))
        s3_cap = fit(txt(f"{num(auto_cnt)}곳 자동 수집, 차단 {num(blocked_cnt)}곳 사람이 내려받음", size=9.0, color=C_INK_1, bold=True, z=7), max_w=2.66).move_to([1.55, -1.16, 0])
        st3_grp = VGroup(s3_hdr, s3_tag, s3_lanes, s3_cap)

        s4_hdr = pill(f"④ 독립 점검 ×{num(auto_cnt)}", fg=C_MINT, bg="#16382C", border=C_MINT, size=10.8, z=8).move_to([4.55, 1.82, 0])
        s4_tag = pill("점검 모델(sonnet)", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.08, py=0.03, z=8).move_to([4.55, 1.28, 0])
        pdf_a = VGroup(
            RoundedRectangle(corner_radius=0.05, width=0.96, height=0.58, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_CYAN, stroke_width=2.0),
            txt("수집본\nPDF", size=8.6, color=C_CYAN, bold=True),
        ).move_to([3.80, 0.42, 0]).set_z_index(7)
        pdf_b = VGroup(
            RoundedRectangle(corner_radius=0.05, width=0.96, height=0.58, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.0),
            txt("재호출\nPDF", size=8.6, color=C_GOLD, bold=True),
        ).move_to([5.30, 0.42, 0]).set_z_index(7)
        hash_seal = VGroup(
            RegularPolygon(n=6, fill_color="#16382C", fill_opacity=1.0, stroke_color=C_MINT, stroke_width=2.4).scale(0.40),
            txt("해시 일치\n쪽수 확인 ✓", size=8.0, color=C_MINT, bold=True),
        ).move_to([4.55, -0.34, 0]).set_z_index(9)
        s4_cap = fit(txt(f"모듈이 있는 {num(auto_cnt)}곳 재호출 해시 대조", size=9.0, color=C_INK_1, bold=True, z=7), max_w=2.65).move_to([4.55, -1.16, 0])
        st4_grp = VGroup(s4_hdr, s4_tag, pdf_a, pdf_b, hash_seal, s4_cap)

        relay_links = VGroup(
            arrow_2d([-3.40, 0.25, 0], [-2.78, 0.25, 0], color=C_VIOLET, sw=2.4, tip=0.11, z=7),
            arrow_2d([-0.22, 0.25, 0], [0.42, 0.25, 0], color=C_GOLD, sw=2.4, tip=0.11, z=7),
            arrow_2d([2.58, 0.25, 0], [3.28, 0.25, 0], color=C_CYAN, sw=2.4, tip=0.11, z=7),
        )

        ret_path = VMobject(color=C_GOLD, stroke_width=2.4).set_z_index(5)
        ret_path.set_points_as_corners([[4.55, -1.48, 0], [4.55, -2.18, 0], [-1.55, -2.18, 0], [-1.55, -1.52, 0]])
        ret_tip = Arrow([-1.55, -1.78, 0], [-1.55, -1.46, 0], buff=0, color=C_GOLD, stroke_width=2.4, tip_length=0.12).set_z_index(6)
        ret_lbl = fit(
            pill(f"그때 전체 시험 {num(batch_tests)}건 통과, 받은 PDF 문서 {num(batch_pdfs)}개 진본과 쪽수 직접 확인 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.2, z=8),
            max_w=8.60,
        ).move_to([1.50, -2.18, 0])

        self.add(s1_arm)
        self.cam_move(
            zoom=1.38,
            center=[-3.05, 0.25, 0],
            anims=[
                FadeOut(beat3a_all, shift=UP * 0.10),
                FadeIn(VGroup(s1_hdr, s1_dome, s1_inner, s1_beacons, s1_cap)),
                Rotate(s1_arm, angle=-TAU, about_point=s1_c),
                GrowArrow(relay_links[0]),
                FadeIn(VGroup(s2_hdr, s2_mold, s2_mold_t, s2_prism, s2_cap)),
                Create(s2_rays, lag_ratio=0.05),
            ],
            rt=1.25,
        )
        self.remove(beat3a_all)
        self.wait(0.70)

        self.cam_move(
            zoom=1.38,
            center=[3.00, 0.25, 0],
            anims=[
                GrowArrow(relay_links[1]),
                FadeIn(VGroup(s3_hdr, s3_tag, s3_cap)),
                LaggedStart(*[Create(ln[0]) for ln in s3_lanes], lag_ratio=0.04),
                LaggedStart(*[FadeIn(ln[1], scale=0.4) for ln in s3_lanes], lag_ratio=0.04),
                GrowArrow(relay_links[2]),
                FadeIn(VGroup(s4_hdr, s4_tag, pdf_a, pdf_b, s4_cap)),
            ],
            rt=1.25,
        )
        self.play(
            pdf_a.animate.shift(RIGHT * 0.22 + DOWN * 0.18),
            pdf_b.animate.shift(LEFT * 0.22 + DOWN * 0.18),
            FadeIn(hash_seal, scale=1.35),
            Flash([4.55, -0.34, 0], color=C_MINT, line_length=0.25, num_lines=10),
            run_time=0.70,
        )
        self.wait(0.65)

        ret_pulse = glow_dot([4.55, -1.48, 0], color=C_GOLD, r=0.07, z=14)
        self.add(ret_pulse)
        self.reset_cam_2d(
            anims=[
                FadeIn(role_banner, shift=DOWN * 0.08),
                Create(ret_path),
                FadeIn(ret_tip),
                MoveAlongPath(ret_pulse, ret_path),
                FadeIn(ret_lbl, shift=UP * 0.06),
            ],
            rt=1.00,
        )
        self.remove(ret_pulse)

        beat3b_roles = VGroup(role_banner, st1_grp, st2_grp, st3_grp, st4_grp, relay_links, ret_path, ret_tip, ret_lbl)
        self.check_bounds(beat3b_roles, "CH3B AGENT ROLES")
        self.wait(1.60)

        # -------------------------------------------------------------------
        # Beat 3C: 16 Batch Insurers Dual Wave (from disclosure_batch_orgs)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"시범({pilot_org}) 뒤 돌린 {num(batch_cnt)}곳 가운데 {num(auto_cnt)}곳은 자동 수집과 해시 점검을 마쳤고, 차단 {num(blocked_cnt)}곳은 사람이 내려받습니다",
            rt=0.38,
        )

        def mini_disp_box(lbl: str, sub: str, col: str, y_pos: float) -> VGroup:
            b = RoundedRectangle(corner_radius=0.07, width=2.48, height=0.96, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=col, stroke_width=2.0).move_to([-4.62, y_pos, 0]).set_z_index(6)
            tg = fit(VGroup(txt(lbl, size=11.0, color=col, bold=True, z=8), txt(sub, size=9.2, color=C_INK_1, z=8)).arrange(DOWN, buff=0.05), max_w=2.26).move_to(b)
            return VGroup(b, tg)

        ag_lead = mini_disp_box(f"시범: {pilot_org}", "한화생명, 삼성화재는 선행 구축", C_GOLD, 1.62)
        ag_fetch = mini_disp_box(f"③ 수집 에이전트 ×{num(batch_cnt)}", f"시범 뒤 {num(batch_cnt)}곳 일괄 실행", C_CYAN, 0.12)
        ag_ver = mini_disp_box(f"④ 점검 에이전트 ×{num(auto_cnt)}", "점검 모델(sonnet) 재호출 대조", C_MINT, -1.38)
        disp_stack = VGroup(
            ag_lead, ag_fetch, ag_ver,
            arrow_2d(ag_lead[0].get_bottom(), ag_fetch[0].get_top(), color=C_GOLD, sw=1.8, tip=0.09, z=7),
            arrow_2d(ag_fetch[0].get_bottom(), ag_ver[0].get_top(), color=C_CYAN, sw=1.8, tip=0.09, z=7),
        )

        board_x = [-0.95, 0.90, 2.75, 4.60]
        board_y = [1.68, 0.68, -0.32, -1.32]
        ins_rects: list[RoundedRectangle] = []
        ins_statuses: list[Mobject] = []
        ins_prisms: list[Prism] = []
        ins_board = VGroup()
        prisms_grp = VGroup()

        for idx, nm in enumerate(batch_orgs):
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            is_blocked = nm == "한화손해보험"
            init_col = C_CORAL if is_blocked else C_SLATE
            init_fill = C_CORAL_DIM if is_blocked else C_PANEL
            rect = RoundedRectangle(corner_radius=0.06, width=1.68, height=0.78, fill_color=init_fill, fill_opacity=0.95, stroke_color=init_col, stroke_width=2.0 if is_blocked else 1.4).move_to([cx, cy, 0]).set_z_index(5)
            t_nm = fit(txt(nm, size=10.8, color=WHITE if not is_blocked else C_CORAL, bold=True, z=7), max_w=1.50).move_to([cx, cy + 0.14, 0])
            t_st = fit(
                txt(f"{num(hf_block_code)} 차단 -> 사람이 내려받음" if is_blocked else "수집 대기", size=8.8, color=C_CORAL if is_blocked else C_INK_2, bold=is_blocked, z=7),
                max_w=1.52,
            ).move_to([cx, cy - 0.16, 0])
            ins_rects.append(rect)
            ins_statuses.append(t_st)
            ins_board.add(VGroup(rect, t_nm, t_st))

            zh = 0.18 if is_blocked else 0.12
            pr = Prism(dimensions=[1.52, 0.64, zh], fill_color=init_col, fill_opacity=0.22, stroke_color=init_col, stroke_width=1.0).move_to([cx, cy, zh / 2])
            ins_prisms.append(pr)
            prisms_grp.add(pr)

        fetch_beam = arrow_2d(ag_fetch[0].get_right(), [-1.80, 0.12, 0], color=C_CYAN, sw=2.8, tip=0.14, z=8)
        ver_beam = arrow_2d(ag_ver[0].get_right(), [-1.80, -1.10, 0], color=C_MINT, sw=2.8, tip=0.14, z=8)
        lead_ret_beam = arrow_2d([-1.80, 1.62, 0], ag_lead[0].get_right(), color=C_GOLD, sw=2.8, tip=0.14, z=8)

        curtain_1 = Prism(dimensions=[0.08, 4.10, 1.15], fill_color=C_CYAN, fill_opacity=0.35, stroke_color=C_CYAN, stroke_width=1.8).move_to([-1.82, 0.18, 0.58])
        curtain_2 = Prism(dimensions=[0.08, 4.10, 1.35], fill_color=C_MINT, fill_opacity=0.35, stroke_color=C_MINT, stroke_width=1.8).move_to([-1.82, 0.18, 0.68])
        done_3c_pill = fit(
            pill(
                f"결과: {num(auto_cnt)}곳 무인증 수집과 해시 점검 완료, 차단 {num(blocked_cnt)}곳 사람이 내려받음, PDF 문서 {num(batch_pdfs)}개 확보 ✓",
                fg=C_GOLD,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=10.6,
                z=9,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.48, 0])

        self.cam_move(
            phi=50 * DEGREES,
            theta=-56 * DEGREES,
            zoom=0.94,
            center=[0.35, 0.0, 0.15],
            anims=[FadeOut(beat3b_roles, shift=UP * 0.10), FadeIn(disp_stack), FadeIn(ins_board), FadeIn(prisms_grp)],
            rt=1.10,
        )
        self.remove(beat3b_roles)

        fetch_status_targets = []
        fetch_anims = []
        for idx in range(len(batch_orgs)):
            if batch_orgs[idx] == "한화손해보험":
                continue
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            nt = txt("수집 완료", size=9.2, color=C_CYAN, bold=True, z=7).move_to([cx, cy - 0.16, 0])
            new_pr = Prism(dimensions=[1.52, 0.64, 0.48], fill_color=C_CYAN, fill_opacity=0.28, stroke_color=C_CYAN, stroke_width=1.2).move_to([cx, cy, 0.24])
            fetch_status_targets.append((idx, nt))
            fetch_anims.append(
                AnimationGroup(
                    ins_rects[idx].animate.set_stroke(C_CYAN, width=2.0).set_fill(C_CYAN_DIM, opacity=0.75),
                    ReplacementTransform(ins_statuses[idx], nt),
                    Transform(ins_prisms[idx], new_pr),
                )
            )

        self.add(curtain_1)
        self.cam_move(
            theta=-44 * DEGREES,
            anims=[GrowArrow(fetch_beam), curtain_1.animate.move_to([5.65, 0.18, 0.58]), LaggedStart(*fetch_anims, lag_ratio=0.035)],
            rt=1.20,
        )
        self.remove(curtain_1)
        for idx, nt in fetch_status_targets:
            ins_statuses[idx] = nt

        ver_anims = []
        for idx in range(len(batch_orgs)):
            if batch_orgs[idx] == "한화손해보험":
                continue
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            vt = txt("해시 일치 확인 ✓", size=9.0, color=C_GOLD, bold=True, z=7).move_to([cx, cy - 0.16, 0])
            gold_pr = Prism(dimensions=[1.52, 0.64, 0.72], fill_color=C_GOLD, fill_opacity=0.26, stroke_color=C_GOLD, stroke_width=1.3).move_to([cx, cy, 0.36])
            ver_anims.append(
                AnimationGroup(
                    ins_rects[idx].animate.set_stroke(C_GOLD, width=2.1).set_fill("#283124", opacity=0.95),
                    ReplacementTransform(ins_statuses[idx], vt),
                    Transform(ins_prisms[idx], gold_pr),
                )
            )
            ins_statuses[idx] = vt

        self.add(curtain_2)
        self.cam_move(
            theta=-34 * DEGREES,
            anims=[GrowArrow(ver_beam), curtain_2.animate.move_to([5.65, 0.18, 0.68]), LaggedStart(*ver_anims, lag_ratio=0.035)],
            rt=1.15,
        )
        self.remove(curtain_2)
        self.reset_cam_2d(
            anims=[FadeOut(prisms_grp), GrowArrow(lead_ret_beam), Circumscribe(ag_lead[0], color=C_GOLD, stroke_width=2.2, buff=0.03), FadeIn(done_3c_pill, shift=UP * 0.06)],
            rt=0.85,
        )
        self.remove(prisms_grp, *ins_prisms)

        ver_status_grp = VGroup(*ins_statuses)
        beat3c_all = VGroup(disp_stack, ins_board, ver_status_grp, fetch_beam, ver_beam, lead_ret_beam, done_3c_pill)
        self.check_bounds(beat3c_all, "CH3C DUAL WAVE")
        self.wait(1.60)

        # -------------------------------------------------------------------
        # Beat 3D: 7-Day Rotating Schedule (from collect_daily_plan) + News Filter
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"해결 ② 하루 {num(lim_search)}회 검색 한도에 맞춰 요일별로 나누고, 첫 수집 구간 밖 {num(n_out)}건을 걸러냈습니다",
            rt=0.40,
        )

        rad_c = np.array([-3.08, 0.14, 0.0])
        rad_r = 1.30
        rad_rings = VGroup(
            Circle(radius=rad_r, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.6, stroke_opacity=0.70).move_to(rad_c),
            Circle(radius=0.88, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.0, stroke_opacity=0.35).move_to(rad_c),
            Circle(radius=0.46, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=2.0).move_to(rad_c),
        ).set_z_index(4)
        rad_core_t = VGroup(txt("요일별", size=10.6, color=C_GOLD, bold=True, z=8), txt("검색 배분", size=9.6, color=C_INK_1, z=8)).arrange(DOWN, buff=0.03).move_to(rad_c)

        plan_items = list(daily_plan.items())
        n_days = len(plan_items)
        day_dots, day_lbls = VGroup(), VGroup()
        for d_i, (day_k, info) in enumerate(plan_items):
            q_cnt = info["queries"]
            orgs_d = info["orgs"]
            if q_cnt == 0:
                d_nm = f"{day_k}: 실패 재수집, 마감 ({num(q_cnt)}회)"
                d_col = C_MINT
            else:
                d_nm = f"{day_k}: {orgs_d[0]} 등 {num(len(orgs_d))}곳 ({num(q_cnt)}회)"
                d_col = C_GOLD if day_k == "금" else (C_VIOLET if day_k == "토" else C_CYAN)
            ang = math.pi / 2 - d_i * (2 * math.pi / n_days)
            dp = rad_c + np.array([rad_r * math.cos(ang), rad_r * math.sin(ang), 0.0])
            d_dot = Circle(radius=0.10, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=d_col, stroke_width=2.0).move_to(dp).set_z_index(7)
            day_dots.add(d_dot)
            d_lbl = fit(txt(d_nm, size=8.4, color=d_col if d_i >= 4 else C_INK_1, bold=(d_i >= 4), z=7), max_w=1.62)
            d_lbl.next_to(d_dot, UP if d_i == 0 else (RIGHT if d_i in (1, 2) else (DOWN if d_i in (3, 4) else LEFT)), buff=0.07)
            day_lbls.add(d_lbl)
        rad_caption = fit(
            pill(f"하루 {num(lim_search)}회 무료 한도 안에서 {num(news_inst_cnt)}개 기관 순환 점검", fg=C_CYAN, bg=C_PANEL, border=C_CYAN, size=9.8),
            max_w=5.10,
        ).move_to([-3.08, -2.52, 0])

        sweep_ang = ValueTracker(math.pi / 2)
        sweep_beam = always_redraw(
            lambda: VGroup(
                Sector(radius=rad_r - 0.02, start_angle=sweep_ang.get_value() - 0.48, angle=0.48, fill_color=C_CYAN, fill_opacity=0.22, stroke_width=0).shift(rad_c),
                Line(rad_c, rad_c + np.array([rad_r * math.cos(sweep_ang.get_value()), rad_r * math.sin(sweep_ang.get_value()), 0.0]), color=C_GOLD, stroke_width=2.8),
            ).set_z_index(6)
        )

        g1_x, g2_x, g3_x = 0.52, 2.28, 4.02
        gate_specs = [
            (g1_x, C_CYAN, "① 발표일을 먼저 적게 함"),
            (g2_x, C_CORAL, "② 코드가 날짜 확인해 버림"),
            (g3_x, C_MINT, "③ 무관 종목과 주제 제외"),
        ]
        sieve_gates = VGroup()
        for gx, g_col, g_top in gate_specs:
            sieve_gates.add(
                VGroup(
                    Line([gx, 0.55, 0], [gx, 1.38, 0], color=g_col, stroke_width=4.2).set_z_index(6),
                    Line([gx, -1.38, 0], [gx, -0.45, 0], color=g_col, stroke_width=4.2).set_z_index(6),
                    DashedLine([gx, -0.45, 0], [gx, 0.55, 0], dash_length=0.07, color=g_col, stroke_width=1.6).set_z_index(5),
                    fit(pill(g_top, fg=g_col, bg=C_PANEL_HI, border=g_col, size=9.8, px=0.09, py=0.05, z=8), max_w=1.74).move_to([gx, 1.78, 0]),
                )
            )
        cut_note = fit(
            pill(f"{num(n_struct)}건 중 구간 밖 {num(n_out)}건 버림, 구간 안 {num(n_in_win)}건", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=9.6, z=8),
            max_w=3.40,
        ).move_to([g2_x - 0.10, -2.02, 0])
        noise_note = fit(txt(f"{excl_lines}, {excl_topics} 등 제외", size=8.8, color=C_INK_2, z=7), max_w=2.90).move_to([g3_x + 0.08, -1.66, 0])
        clean_pool = RoundedRectangle(corner_radius=0.08, width=1.42, height=1.98, fill_color="#182B24", fill_opacity=0.94, stroke_color=C_GOLD, stroke_width=2.2).move_to([5.42, 0.05, 0]).set_z_index(4)
        pool_lbl = fit(VGroup(txt("선별 통과 소식", size=10.8, color=C_GOLD, bold=True, z=7), txt("정본 탭 기록 ✓", size=10.4, color=C_MINT, bold=True, z=7)).arrange(DOWN, buff=0.07), max_w=1.26).move_to(clean_pool.get_top() + DOWN * 0.44)

        self.play(
            FadeOut(beat3c_all, shift=UP * 0.10),
            FadeIn(rad_rings), FadeIn(rad_core_t), FadeIn(day_dots, lag_ratio=0.05), FadeIn(day_lbls), FadeIn(rad_caption, shift=UP * 0.08),
            FadeIn(sieve_gates, lag_ratio=0.10), FadeIn(VGroup(clean_pool, pool_lbl), shift=LEFT * 0.10),
            run_time=0.95,
        )
        self.remove(beat3c_all, *ins_statuses)

        self.add(sweep_beam)
        good_news_pts, bad_date_pts, bad_noise_pts = VGroup(), VGroup(), VGroup()
        sieve_anims = []
        emit_pt = rad_c + RIGHT * rad_r
        for k in range(n_in_win):
            pt = glow_dot(emit_pt, color=C_GOLD, r=0.055, z=12)
            good_news_pts.add(pt)
            sieve_anims.append(Succession(Wait(k * 0.14), MoveAlongPath(pt, Line(emit_pt + UP * ((-0.35 + k * 0.24) * 0.4), np.array([5.40, -0.58 + k * 0.20, 0])), run_time=1.35)))
        for k in range(5):
            pt_b = glow_dot(emit_pt, color=C_CORAL, r=0.052, z=11)
            bad_date_pts.add(pt_b)
            sieve_anims.append(Succession(Wait(0.06 + k * 0.11), MoveAlongPath(pt_b, CubicBezier(emit_pt, np.array([0.8, 0.35 - k * 0.18, 0]), np.array([g2_x - 0.05, -0.25, 0]), np.array([g2_x, -1.55, 0])), run_time=1.05)))
        for k in range(2):
            pt_n = glow_dot(emit_pt, color=C_AMBER, r=0.050, z=11)
            bad_noise_pts.add(pt_n)
            sieve_anims.append(Succession(Wait(0.20 + k * 0.18), MoveAlongPath(pt_n, CubicBezier(emit_pt, np.array([1.8, 0.2, 0]), np.array([g3_x - 0.05, -0.2, 0]), np.array([g3_x, -1.45, 0])), run_time=1.10)))

        self.add(good_news_pts, bad_date_pts, bad_noise_pts)
        self.cam_move(
            zoom=1.26,
            center=[2.05, -0.05, 0],
            anims=[
                sweep_ang.animate.set_value(math.pi / 2 - 2 * math.pi),
                *sieve_anims,
                FadeIn(cut_note, shift=UP * 0.08),
                FadeIn(noise_note),
                *[d.animate.set_fill(C_CYAN_DIM, opacity=0.95) for d in day_dots],
            ],
            rt=1.80,
            rate_func=linear,
        )
        self.reset_cam_2d(
            anims=[FadeOut(bad_date_pts, scale=0.3), FadeOut(bad_noise_pts, scale=0.3), Circumscribe(clean_pool, color=C_GOLD, stroke_width=2.2, buff=0.04)],
            rt=0.80,
        )
        self.remove(bad_date_pts, *bad_date_pts, bad_noise_pts, *bad_noise_pts)
        sweep_beam.clear_updaters()

        ch3_stage = VGroup(rad_rings, rad_core_t, day_dots, day_lbls, rad_caption, sweep_beam, sieve_gates, cut_note, noise_note, clean_pool, pool_lbl, good_news_pts)
        self.check_bounds(ch3_stage, "CH3D RADAR SIEVE")
        self.wait(1.60)

        # ===================================================================
        # 4장: 추출 단계
        # ===================================================================
        hw_pages = fact("hanwha_summary_pages")
        hw_first = fact("hanwha_first_extract")
        hw_calls = hw_first["calls"]
        hw_mins = hw_first["minutes"]
        lim_ext = fact("daily_limit_extract")
        lim_up = fact("daily_limit_upper")

        ts_rows = fact("text_switch_confirmed_rows")
        ta_mis = fact("targeted_anticancer_misread")
        rev_new = fact("example_targeted_anticancer", "revisions", -1)
        basis_mw = rev_new["basis_manwon"]
        pay_new_mw = rev_new["pay_manwon"]
        wait_days = rev_new["waiting_days"]
        red_months = rev_new["reduce"][0]["months"]
        red_rate = rev_new["reduce"][0]["rate"]
        red_pct = round(red_rate * 100)
        reduced_pay_mw = round(pay_new_mw * red_rate)
        red_yr = red_months // 12

        img_doc = fact("image_doc")
        img_pages = img_doc["pages"]
        img_chars_man = round(img_doc["chars"] / 10000)
        img_mismatches = img_doc["amount_mismatches"]
        same_rep = fact("image_doc_same_reader_repeat")
        ocr_test = fact("local_ocr_test")
        prot_rows = fact("rider_limit_rows_protected")
        inh_rows = fact("id_inherit_simulated_rows")
        sf_check = fact("samsungfire_crosscheck_rows")
        sf_total = fact("benefits_by_org", "SAMSUNGFIRE")

        hl, hr, hb = self.switch_hud(
            ch3_stage,
            hl,
            hr,
            hb,
            4,
            "추출 단계: 요약서와 사업방법서에서 급부와 한도를 뽑는 방법",
            "대용량 요약서 호출 부담, 숫자 직접 추출 오독, 그림 요약서, 한도 초기화 결함에 부딪혔습니다",
        )

        res_box_4 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_4 = pill("추출 도구와 한도 조건", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, z=7).move_to([-4.38, 1.92, 0])
        rg4_1 = capacity_ring([-5.15, 0.72, 0], 0.58, C_CYAN, "추출 모델", f"하루 {num(lim_ext)}회 무료", z=6)
        rg4_2 = capacity_ring([-3.62, 0.72, 0], 0.58, C_CORAL, "상위 재추출", f"하루 {num(lim_up)}회 상한", z=6)
        res_notes_4 = fit(
            VGroup(
                pill("PDF 표 규칙 추출 코드", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.6, z=7),
                pill("서브에이전트 두 판독, 제미나이 패널", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=9.4, z=7),
                txt("정형 표 요약서와 그림 요약서가 섞여 있음", size=9.2, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.04,
        ).move_to([-4.38, -1.14, 0])
        res_grp_4 = VGroup(res_box_4, res_hdr_4, rg4_1, rg4_2, res_notes_4)
        vs_arr_4 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        q4_1 = diag_frame(-0.10, 1.18, C_AMBER, f"문제 ① {num(hw_pages)}쪽 요약서 첫 추출 호출 부담")
        bar_base_y = 0.58
        ceil_h = 0.92
        b_1doc_h = ceil_h * (hw_calls / lim_ext)
        ceil_ln = DashedLine([-1.65, bar_base_y + ceil_h, 0], [1.45, bar_base_y + ceil_h, 0], dash_length=0.07, color=C_CYAN, stroke_width=1.8).set_z_index(7)
        ceil_lbl = txt(f"하루 {num(lim_ext)}회 한도", size=8.4, color=C_CYAN, bold=True, z=8).move_to([-1.05, bar_base_y + ceil_h + 0.16, 0])
        b_1doc = Rectangle(width=0.52, height=b_1doc_h, fill_color=C_AMBER, fill_opacity=0.92, stroke_color=WHITE, stroke_width=1.0).move_to([-0.72, bar_base_y + b_1doc_h / 2, 0]).set_z_index(6)
        q4_1_t1 = fit(txt(f"한화 첫 추출 {num(hw_calls)}회 ({num(hw_mins)}분)", size=8.6, color=C_AMBER, bold=True, z=7), max_w=1.88).move_to([0.56, bar_base_y + 0.42, 0])
        q4_1_t2 = fit(txt("기존 상품 초기 적재는 API 밖 경로로 전환", size=8.4, color=C_INK_1, z=7), max_w=3.48).move_to([-0.10, 0.36, 0])

        q4_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 숫자 직접 추출 오독과 낮은 확정 수")
        mis_calc = fit(
            VGroup(
                pill(f"원문 {num(ta_mis['correct_pay_manwon'])}만, {num(red_pct)}%", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=8.2, px=0.07, py=0.03),
                arrow_2d([0, 0, 0], [0.28, 0, 0], color=C_CORAL, sw=1.6, tip=0.07),
                pill(f"오독 {num(ta_mis['misread_pay_manwon'])}만, {num(ta_mis['misread_reduced_manwon'])}만 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.2, px=0.07, py=0.03),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.44,
        ).move_to([3.88, 1.30, 0]).set_z_index(7)
        prog_w_max = 2.86
        prog_w_22 = prog_w_max * (ts_rows["before"] / ts_rows["total"])
        prog_bg = RoundedRectangle(corner_radius=0.04, width=prog_w_max, height=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.2).move_to([3.88, 0.78, 0]).set_z_index(6)
        prog_22 = Rectangle(width=prog_w_22, height=0.16, fill_color=C_AMBER, fill_opacity=0.9, stroke_width=0).move_to([3.88 - prog_w_max / 2 + prog_w_22 / 2, 0.78, 0]).set_z_index(7)
        q4_2_cap = fit(txt(f"우체국 요약서 {num(ts_rows['total'])}줄 가운데 {num(ts_rows['before'])}줄 확정", size=8.8, color=C_AMBER, bold=True, z=7), max_w=3.44).move_to([3.88, 0.44, 0])

        q4_3 = diag_frame(-0.10, -1.14, C_VIOLET, f"문제 ③ 미래에셋 요약서 {num(img_pages)}쪽이 통째 그림")
        mosaic_compact, mosaic = VGroup(), VGroup()
        for k in range(12):
            rr, cc = divmod(k, 6)
            c0 = RoundedRectangle(corner_radius=0.01, width=0.30, height=0.24, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_VIOLET, stroke_width=1.0).move_to([-0.85 + cc * 0.31, -0.94 - rr * 0.25, 0]).set_z_index(7)
            c1 = RoundedRectangle(corner_radius=0.02, width=0.34, height=0.26, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_VIOLET, stroke_width=1.4).move_to([-1.15 + cc * 0.42, -0.88 - rr * 0.34, 0]).set_z_index(7)
            mosaic_compact.add(c0)
            mosaic.add(c1)
        q4_3_cap = fit(
            VGroup(
                txt(f"대조용 쪽 로컬 OCR(tesseract) {num(ocr_test['chars'])}자 중 누락 {num(ocr_test['missed'])}, 오자 {num(ocr_test['wrong'])}", size=8.2, color=C_CORAL, bold=True, z=7),
                txt("(값 추출에는 쓰지 않고 급부 표 쪽 찾기에만 사용)", size=7.8, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.03),
            max_w=3.48,
        ).move_to([-0.10, -1.76, 0])

        q4_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 가짜 시트 시험의 특약 한도 초기화")
        lim_bars_before = VGroup(
            *[Rectangle(width=0.92, height=0.11, fill_color=C_CYAN, fill_opacity=0.92, stroke_width=0).move_to([2.88, -0.82 - k * 0.17, 0]).set_z_index(7) for k in range(4)]
        )
        wipe_l_lbl = txt(f"특약 한도 {num(prot_rows)}줄", size=8.4, color=C_CYAN, bold=True, z=7).move_to([2.88, -1.52, 0])
        wipe_arr = arrow_2d([3.52, -1.08, 0], [4.04, -1.08, 0], color=C_CORAL, sw=2.2, tip=0.09, z=7)
        wipe_r = pill(f"가짜 시트 {num(0)}줄 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.8, px=0.09, py=0.04, z=8).move_to([4.84, -1.08, 0])
        q4_4_cap = fit(txt("급부만 다시 뽑을 때 비워질 결함을 실제 실행 전에 수정", size=8.6, color=C_INK_1, z=7), max_w=3.48).move_to([3.88, -1.82, 0])

        self.play(
            FadeIn(res_grp_4, shift=RIGHT * 0.12),
            GrowArrow(vs_arr_4),
            FadeIn(VGroup(q4_1, ceil_ln, ceil_lbl, q4_1_t1, q4_1_t2)),
            GrowFromEdge(b_1doc, DOWN),
            FadeIn(VGroup(q4_2, prog_bg, q4_2_cap)),
            FadeIn(VGroup(q4_3, mosaic_compact)),
            FadeIn(VGroup(q4_4, lim_bars_before, wipe_l_lbl, q4_4_cap)),
            run_time=1.10,
        )

        self.cam_move(
            zoom=1.36,
            center=[1.88, 1.18, 0],
            anims=[
                Circumscribe(q4_1[0], color=C_AMBER, stroke_width=2.0, buff=0.03),
                FadeIn(mis_calc, shift=RIGHT * 0.10),
                GrowFromEdge(prog_22, LEFT),
            ],
            rt=1.10,
        )
        self.wait(0.65)

        self.cam_move(
            zoom=1.36,
            center=[1.88, -1.14, 0],
            anims=[
                ReplacementTransform(mosaic_compact, mosaic),
                FadeIn(q4_3_cap, shift=UP * 0.05),
                GrowArrow(wipe_arr),
                lim_bars_before.animate.set_opacity(0.14),
                FadeIn(wipe_r, scale=1.25),
            ],
            rt=1.10,
        )
        self.wait(0.65)
        self.reset_cam_2d(rt=0.80)

        beat4a_all = VGroup(
            res_grp_4, vs_arr_4,
            q4_1, ceil_ln, ceil_lbl, b_1doc, q4_1_t1, q4_1_t2,
            q4_2, mis_calc, prog_bg, prog_22, q4_2_cap,
            q4_3, mosaic, q4_3_cap,
            q4_4, lim_bars_before, wipe_l_lbl, wipe_arr, wipe_r, q4_4_cap,
        )
        self.check_bounds(beat4a_all, "CH4A EXTRACT DIAGNOSTIC")
        self.wait(1.30)

        # -------------------------------------------------------------------
        # Beat 4B: Verbatim Text Copy vs Deterministic Code Math
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 모델은 요약서 원문 글자만 옮기고 숫자는 코드가 계산하며, 삼성화재는 PDF 표 규칙으로 뽑습니다",
            rt=0.40,
        )

        dual_path_bar = fit(
            pill("초기 적재 분리: 기존 상품은 코드 규칙, 서브에이전트 두 판독, 제미나이 패널로 처리하고 무료 API는 주간 갱신에 사용", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.6, z=9),
            max_w=11.85,
        ).move_to([0.0, 2.60, 0])

        src_tok1 = fit(pill(f"{rev_new['benefit']} {num(pay_new_mw)}만 원", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0), max_w=3.85)
        src_tok2 = fit(pill(f"계약일부터 {num(red_months)}개월 {num(red_pct)}% 감액", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.0), max_w=3.85)
        src_tok3 = fit(pill(f"면책 {num(wait_days)}일", fg=C_INK_0, bg=C_PANEL_HI, border=C_INK_1, size=11.0), max_w=3.85)
        src_tokens = VGroup(src_tok1, src_tok2, src_tok3).arrange(DOWN, buff=0.20).move_to([-4.25, -0.05, 0])
        src_hdr = fit(txt(f"요약서 원문 값 (기준 가입 {num(basis_mw)}만 원)", size=11.0, color=C_INK_1, bold=True, z=7), max_w=3.85).move_to([-4.25, 1.38, 0])

        stencil_frame = RoundedRectangle(corner_radius=0.08, width=3.18, height=1.06, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0).move_to([-0.38, 1.56, 0]).set_z_index(4)
        stencil_title = fit(txt("모델은 원문 글자만 전달 (계산 제외)", size=11.2, color=C_CYAN, bold=True, z=6), max_w=2.96).move_to(stencil_frame.get_top() + DOWN * 0.25)
        stencil_sub = fit(txt(f"확정 줄 수: {num(ts_rows['total'])}줄 중 {num(ts_rows['before'])}줄 -> {num(ts_rows['after'])}줄 ✓", size=9.8, color=C_MINT, bold=True, z=6), max_w=2.96).move_to(stencil_frame.get_bottom() + UP * 0.24)
        stencil_out = fit(pill(f"지급 {num(pay_new_mw)}만 원, {num(red_months)}개월 {num(red_pct)}%, 면책 {num(wait_days)}일", fg=C_GOLD, bg=C_PANEL, border=C_GOLD, size=10.6), max_w=4.15).move_to([3.68, 1.56, 0])
        arr_up_in = arrow_2d(src_tok1.get_right(), stencil_frame.get_left(), color=C_CYAN, sw=2.0)
        arr_up_out = arrow_2d(stencil_frame.get_right(), stencil_out.get_left(), color=C_GOLD, sw=2.0)

        ax_origin = np.array([-1.55, -2.35, 0.0])
        x_axis = Arrow(ax_origin, ax_origin + RIGHT * 6.95, buff=0, color=C_INK_2, stroke_width=2.0, tip_length=0.14).set_z_index(4)
        y_axis = Arrow(ax_origin, ax_origin + UP * 2.38, buff=0, color=C_INK_2, stroke_width=2.0, tip_length=0.14).set_z_index(4)
        code_badge = fit(
            pill(f"코드 계산과 표 규칙 추출: 삼성화재 사본 급부 {num(sf_total)}건 (제미나이 독립 구조화와 {num(sf_check)}줄 대조)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.0),
            max_w=6.85,
        ).move_to([2.05, 0.36, 0])
        arr_dn_in = arrow_2d(src_tok2.get_right(), code_badge.get_left() + LEFT * 0.06, color=C_CYAN, sw=2.0)

        full_step_h = 1.80
        red_step_h = full_step_h * red_rate
        y_1000, y_2000 = ax_origin[1] + red_step_h, ax_origin[1] + full_step_h
        x_90d, x_1yr, x_end = ax_origin[0] + 1.45, ax_origin[0] + 3.75, ax_origin[0] + 6.45
        dash_1000 = DashedLine([ax_origin[0], y_1000, 0], [x_1yr, y_1000, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.2).set_z_index(3)
        dash_2000 = DashedLine([ax_origin[0], y_2000, 0], [x_end, y_2000, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.2).set_z_index(3)
        y_lbl_1 = txt(f"{num(reduced_pay_mw)}만", size=10.6, color=C_CYAN, bold=True, z=6).move_to([ax_origin[0] - 0.56, y_1000, 0])
        y_lbl_2 = txt(f"{num(pay_new_mw)}만", size=10.6, color=C_GOLD, bold=True, z=6).move_to([ax_origin[0] - 0.56, y_2000, 0])

        step_path = VMobject(color=C_GOLD, stroke_width=3.8).set_z_index(7)
        step_path.set_points_as_corners([[ax_origin[0], ax_origin[1], 0], [x_90d, ax_origin[1], 0], [x_90d, y_1000, 0], [x_1yr, y_1000, 0], [x_1yr, y_2000, 0], [x_end, y_2000, 0]])
        area_50 = Rectangle(width=x_1yr - x_90d, height=red_step_h, fill_color=C_CYAN, fill_opacity=0.18, stroke_width=0).move_to([(x_90d + x_1yr) / 2, ax_origin[1] + red_step_h / 2, 0]).set_z_index(2)
        area_100 = Rectangle(width=x_end - x_1yr, height=full_step_h, fill_color=C_GOLD, fill_opacity=0.22, stroke_width=0).move_to([(x_1yr + x_end) / 2, ax_origin[1] + full_step_h / 2, 0]).set_z_index(2)
        step_3d_50 = Prism(dimensions=[x_1yr - x_90d - 0.06, red_step_h, 0.52], fill_color=C_CYAN, fill_opacity=0.28, stroke_color=C_CYAN, stroke_width=1.2).move_to([(x_90d + x_1yr) / 2, ax_origin[1] + red_step_h / 2, 0.26])
        step_3d_100 = Prism(dimensions=[x_end - x_1yr - 0.06, full_step_h, 0.96], fill_color=C_GOLD, fill_opacity=0.32, stroke_color=C_GOLD, stroke_width=1.4).move_to([(x_1yr + x_end) / 2, ax_origin[1] + full_step_h / 2, 0.48])
        steps_3d_grp = VGroup(step_3d_50, step_3d_100)

        xl_1 = txt(f"{num(wait_days)}일 면책 ({num(0)}원)", size=9.8, color=C_CORAL, bold=True, z=6).move_to([(ax_origin[0] + x_90d) / 2, ax_origin[1] - 0.28, 0])
        xl_2 = txt(f"{num(red_yr)}년 미만 ({num(reduced_pay_mw)}만 원)", size=9.8, color=C_CYAN, bold=True, z=6).move_to([(x_90d + x_1yr) / 2, ax_origin[1] - 0.28, 0])
        xl_3 = txt(f"{num(red_yr)}년 경과 ({num(pay_new_mw)}만 원)", size=9.8, color=C_GOLD, bold=True, z=6).move_to([(x_1yr + x_end) / 2, ax_origin[1] - 0.28, 0])

        self.cam_move(
            phi=44 * DEGREES,
            theta=-64 * DEGREES,
            zoom=0.92,
            center=[0.35, -0.35, 0.20],
            anims=[
                FadeOut(beat4a_all, shift=UP * 0.10),
                FadeIn(src_hdr),
                FadeIn(src_tokens, shift=RIGHT * 0.14),
                GrowArrow(arr_up_in),
                FadeIn(VGroup(stencil_frame, stencil_title, stencil_sub)),
                GrowArrow(arr_up_out),
                FadeIn(stencil_out, shift=RIGHT * 0.10),
                Create(x_axis),
                Create(y_axis),
                GrowArrow(arr_dn_in),
                FadeIn(code_badge),
                Create(dash_1000),
                Create(dash_2000),
                FadeIn(VGroup(y_lbl_1, y_lbl_2, xl_1, xl_2, xl_3)),
                Create(step_path),
                FadeIn(steps_3d_grp, shift=OUT * 0.3),
            ],
            rt=1.35,
        )
        self.remove(beat4a_all)
        self.cam_move(theta=-50 * DEGREES, rt=0.70)
        self.reset_cam_2d(
            anims=[FadeOut(steps_3d_grp), FadeIn(area_50), FadeIn(area_100), FadeIn(dual_path_bar, shift=DOWN * 0.08)],
            rt=0.80,
        )
        self.remove(steps_3d_grp)

        beat4b_all = VGroup(
            dual_path_bar, src_hdr, src_tokens, arr_up_in, stencil_frame, stencil_title, stencil_sub, arr_up_out, stencil_out,
            x_axis, y_axis, arr_dn_in, code_badge, dash_1000, dash_2000, y_lbl_1, y_lbl_2, step_path, area_50, area_100, xl_1, xl_2, xl_3,
        )
        self.check_bounds(beat4b_all, "CH4B STENCIL VS STEP")
        self.wait(1.60)

        # -------------------------------------------------------------------
        # Beat 4C: 308-Page Image Doc Cross-Reading & Simulated ID Inheritance
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 그림 요약서는 제미나이 패널과 sonnet 에이전트가 따로 읽고, 재추출 보호는 지난 자료로 시험했습니다",
            rt=0.38,
        )

        same_rep_banner = fit(
            pill(
                f"같은 판독기 반복 시험: {num(same_rep['pages'])}쪽 중 {num(same_rep['wrong_same_way'])}쪽에서 첫 판독과 같은 식으로 틀려 서로 다른 두 판독기를 교차 사용",
                fg=C_AMBER,
                bg=C_PANEL_HI,
                border=C_AMBER,
                size=10.2,
                z=9,
            ),
            max_w=11.85,
        ).move_to([0.0, 2.58, 0])

        rows_n, cols_n = 5, 7
        gx0, gy0 = -2.25, 1.18
        dx_g, dy_g = 0.62, 0.50
        cells_grid = VGroup()
        mismatch_idx = (2, 4)
        mismatch_cell = None
        for r in range(rows_n):
            for c in range(cols_n):
                cell = RoundedRectangle(corner_radius=0.04, width=0.52, height=0.40, fill_color=C_PANEL_HI, fill_opacity=0.92, stroke_color=C_SLATE, stroke_width=1.2).move_to([gx0 + c * dx_g, gy0 - r * dy_g, 0]).set_z_index(4)
                cells_grid.add(cell)
                if (r, c) == mismatch_idx:
                    mismatch_cell = cell
        assert mismatch_cell is not None

        r1_badge = pill("제미나이 구독 패널 판독", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.2).move_to([-4.62, -0.05, 0]).set_z_index(8)
        r2_badge = pill("sonnet 에이전트 판독", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=10.2).move_to([gx0 + 3 * dx_g, 1.88, 0]).set_z_index(8)

        beam_h_3d = Prism(dimensions=[0.10, 2.65, 0.80], fill_color=C_CYAN, fill_opacity=0.38, stroke_color=C_CYAN, stroke_width=1.8).move_to([gx0 - 0.5, gy0 - 2 * dy_g, 0.40])
        beam_v_3d = Prism(dimensions=[4.45, 0.10, 0.80], fill_color=C_GOLD, fill_opacity=0.38, stroke_color=C_GOLD, stroke_width=1.8).move_to([gx0 + 3 * dx_g, gy0 + 0.45, 0.40])
        err_spike_3d = Prism(dimensions=[0.46, 0.36, 1.05], fill_color=C_AMBER, fill_opacity=0.88, stroke_color=WHITE, stroke_width=1.4).move_to([mismatch_cell.get_center()[0], mismatch_cell.get_center()[1], 0.52])

        loupe_c = np.array([3.95, 0.05, 0.0])
        loupe_ring = Circle(radius=1.35, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=2.6).move_to(loupe_c).set_z_index(6)
        loupe_hdr = txt("어긋난 글자 줄만 확대", size=11.0, color=C_GOLD, bold=True, z=8).move_to(loupe_c + UP * 0.66)
        loupe_zero = fit(txt(f"지급률, 금액 어긋남: {num(img_mismatches)}곳", size=10.6, color=C_MINT, bold=True, z=8), max_w=2.36).move_to(loupe_c + UP * 0.12)
        loupe_sub = fit(txt("두 판독이 같았다는 뜻이며\n어긋난 글자는 Claude가 판정", size=8.8, color=C_INK_1, z=8), max_w=2.34).move_to(loupe_c + DOWN * 0.46)
        loupe_link = DashedLine(mismatch_cell.get_right(), loupe_ring.get_left(), dash_length=0.08, color=C_GOLD, stroke_width=2.0).set_z_index(5)

        img_summary = fit(
            pill(
                f"그림 요약서 {num(img_pages)}쪽(약 {num(img_chars_man)}만 자) 확정, 지난 한화 자료 시험으로 급부ID {num(inh_rows)}줄 이어받기 확인(실제 재추출 확인 전) ✓",
                fg=C_GOLD,
                bg=C_PANEL_HI,
                border=C_GOLD_DEEP,
                size=10.0,
            ),
            max_w=11.85,
        ).move_to([0.0, -2.38, 0]).set_z_index(8)

        self.cam_move(
            phi=48 * DEGREES,
            theta=-55 * DEGREES,
            zoom=0.96,
            center=[-0.35, -0.05, 0.15],
            anims=[FadeOut(beat4b_all, shift=UP * 0.10), FadeIn(cells_grid, lag_ratio=0.008), FadeIn(r1_badge), FadeIn(r2_badge)],
            rt=1.05,
        )
        self.remove(beat4b_all)

        self.add(beam_h_3d, beam_v_3d)
        self.cam_move(
            theta=-42 * DEGREES,
            anims=[
                beam_h_3d.animate.move_to([gx0 + 6.5 * dx_g, gy0 - 2 * dy_g, 0.40]),
                beam_v_3d.animate.move_to([gx0 + 3 * dx_g, gy0 - 4.45 * dy_g, 0.40]),
                *[c.animate.set_stroke(C_MINT, width=1.6) for c in cells_grid if c is not mismatch_cell],
                mismatch_cell.animate.set_fill("#3D2B0D", opacity=0.98).set_stroke(C_AMBER, width=2.6),
                FadeIn(err_spike_3d, shift=OUT * 0.4),
            ],
            rt=1.20,
        )
        self.remove(beam_h_3d, beam_v_3d)

        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.34,
            center=[2.35, 0.05, 0],
            anims=[
                FadeOut(err_spike_3d),
                Create(loupe_link),
                FadeIn(VGroup(loupe_ring, loupe_hdr, loupe_zero, loupe_sub), scale=0.90),
                mismatch_cell.animate.set_fill("#283124", opacity=0.98).set_stroke(C_GOLD, width=2.4),
            ],
            rt=1.05,
        )
        self.remove(err_spike_3d)
        self.wait(0.75)

        self.reset_cam_2d(
            anims=[FadeIn(same_rep_banner, shift=DOWN * 0.08), FadeIn(img_summary, shift=UP * 0.08)],
            rt=0.85,
        )

        ch4_stage = VGroup(same_rep_banner, cells_grid, r1_badge, r2_badge, loupe_link, loupe_ring, loupe_hdr, loupe_zero, loupe_sub, img_summary)
        self.check_bounds(ch4_stage, "CH4C CROSS READ")
        self.wait(1.70)

        self.fade_out_part(ch4_stage, hl, hr, hb)
