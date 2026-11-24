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
    capacity_ring,
    fact,
    fit,
    floor_grid_3d,
    glass_plane_3d,
    glow_dot,
    label_ko,
    make_doc_icon,
    make_filter_gate,
    make_firewall_barrier,
    make_loupe,
    make_mini_portal,
    make_shield_icon,
    make_silo_pool,
    num,
    pillar_3d,
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
        unpinned_msg = label_ko(fact("unpinned_agent_incident"))
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
            f"수집 단계: 회사별 상품공시와 주간 {TERM['trend']} 수집",
            f"초기 수집 {num(n_struct)}건 중 대상 기간 외 {num(n_out)}건 유입, 접속 차단, 검색 후보 오류가 발생했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 3A: 각 문제를 크게 동적 시연한 뒤 4분할 진단 차트로 조립
        # -------------------------------------------------------------------
        res_box_3 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.1).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_3 = pill("가용 자원과 한도 조건", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.4, z=7).move_to([-4.38, 1.92, 0])
        rg_1 = capacity_ring([-5.15, 0.72, 0], 0.58, C_AMBER, "주간 한도 여유", "최상위 모델 제한", z=6)
        rg_2 = capacity_ring([-3.62, 0.72, 0], 0.58, C_CYAN, "무료 검색", f"하루 {num(lim_search)}회 상한", z=6)
        res_bars_3 = fit(
            VGroup(
                pill(f"GitHub Actions 월 {num(act_mins)}분 무료", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=11.0, z=7),
                pill(f"유료 수집, 뉴스 API 비용 {num(op_cost)}원", fg=C_INK_0, bg=C_BG_SUB, border=C_SLATE, size=11.0, z=7),
                txt(f"{num(team_sz)}인 체제, {num(news_inst_cnt)}개 기관 동향 점검", size=10.8, color=C_INK_1, bold=True, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.08,
        ).move_to([-4.38, -1.14, 0])
        res_grp_3 = VGroup(res_box_3, res_hdr_3, rg_1, rg_2, res_bars_3)
        vs_arr_3 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.8, tip=0.13, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=col, stroke_width=2.1).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=12.2, color=col, bold=True, z=7), max_w=3.48).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        q3_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 모델 미지정 서브에이전트 실행")
        unpin_l = pill("구현 에이전트 (미지정)", fg=C_WHITE, bg=C_BG_SUB, border=C_SLATE, size=10.4, px=0.09, py=0.04, z=7).move_to([-1.06, 1.16, 0])
        unpin_arr = arrow_2d([-0.20, 1.16, 0], [0.18, 1.16, 0], color=C_AMBER, sw=2.2, tip=0.09, z=7)
        unpin_r = pill("최상위 모델 실행 ×", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=10.4, px=0.09, py=0.04, z=7).move_to([0.98, 1.16, 0])
        q3_1_cap = fit(txt(f"{unpinned_msg} (소모량 미기록)", size=10.6, color=C_INK_0, z=7), max_w=3.50).move_to([-0.10, 0.50, 0])
        card_3_1 = VGroup(q3_1, unpin_l, unpin_arr, unpin_r, q3_1_cap)

        q3_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 회사별 공시 구조 상이와 접속 차단")
        sk1 = make_mini_portal([2.44, 1.22, 0], variant="table", col=C_CYAN, z=6)
        sk2 = make_mini_portal([2.93, 1.22, 0], variant="tree", col=C_GOLD, z=6)
        sk3 = make_mini_portal([3.42, 1.22, 0], variant="modal", col=C_VIOLET, z=6)
        blk_arr = arrow_2d([3.68, 1.22, 0], [4.32, 1.22, 0], color=C_CORAL, sw=2.4, tip=0.10, z=7)
        blk_wall = make_firewall_barrier([4.48, 1.22, 0], h=0.74, col=C_CORAL, z=8)
        blk_tag = pill(f"{num(hf_block_code)} 차단 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=10.4, px=0.08, py=0.04, z=8).move_to([5.18, 1.22, 0])
        q3_2_cap = fit(txt("한화손해보험 목록 요청 차단, 우회 금지 원칙", size=10.6, color=C_INK_0, z=7), max_w=3.50).move_to([3.88, 0.50, 0])
        card_3_2 = VGroup(q3_2, sk1, sk2, sk3, blk_arr, blk_wall, blk_tag, q3_2_cap)

        q3_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 검색 후보 오류와 API 보관 제한")
        m_fail1 = fit(pill(f"첫째 후보: {num(rej_cand['error_status'])} 오류 ({num(rej_cand['error_tries'])}회) ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.4, px=0.08, py=0.04, z=7), max_w=2.18).move_to([-0.90, -0.94, 0])
        m_fail2 = fit(pill(f"둘째 후보: 출처 {num(rej_cand['sources_found'])}건 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.4, px=0.08, py=0.04, z=7), max_w=2.18).move_to([-0.90, -1.42, 0])
        lock_body = RoundedRectangle(corner_radius=0.06, width=0.50, height=0.40, fill_color="#1D1632", fill_opacity=1.0, stroke_color=C_VIOLET, stroke_width=2.1).move_to([1.02, -1.24, 0]).set_z_index(7)
        lock_shackle = Arc(radius=0.16, start_angle=0, angle=PI, arc_center=[1.02, -1.03, 0], color=C_VIOLET, stroke_width=2.5).set_z_index(7)
        lock_keyhole = VGroup(
            Dot([1.02, -1.21, 0], radius=0.042, color=C_GOLD),
            Line([1.02, -1.21, 0], [1.02, -1.33, 0], color=C_GOLD, stroke_width=2.4),
        ).set_z_index(8)
        lock_lbl = fit(txt(f"네이버 API 보관 {num(nav_days)}일 상한", size=10.4, color=C_VIOLET, bold=True, z=7), max_w=1.48).move_to([1.02, -1.62, 0])
        card_3_3 = VGroup(q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_keyhole, lock_lbl)

        q3_4 = diag_frame(3.88, -1.14, C_CORAL, f"문제 ④ 수집 기간 외 {TERM['trend']} 유입")
        dots_27_cyan, dots_27_final = VGroup(), VGroup()
        for k in range(n_struct):
            rr, cc = divmod(k, 9)
            pt_d = [2.60 + cc * 0.32, -0.82 - rr * 0.28, 0]
            is_in_window = k >= n_out
            dots_27_cyan.add(Circle(radius=0.088, fill_color=C_CYAN, fill_opacity=0.88, stroke_color=C_CYAN, stroke_width=1.1).move_to(pt_d).set_z_index(7))
            dcol = C_GOLD if is_in_window else C_CORAL
            dots_27_final.add(Circle(radius=0.088, fill_color=dcol, fill_opacity=0.96, stroke_color=WHITE if is_in_window else dcol, stroke_width=1.2).move_to(pt_d).set_z_index(7))
        q3_4_cap = fit(txt(f"정형화 {num(n_struct)}건 중 기간 외 {num(n_out)}건, 기간 내 {num(n_in_win)}건", size=10.6, color=C_CORAL, bold=True, z=7), max_w=3.50).move_to([3.88, -1.84, 0])

        # Step 1: 자원 카드 등장
        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[FadeIn(res_grp_3, shift=RIGHT * 0.14), GrowArrow(vs_arr_3)],
            rt=1.20,
        )
        self.wait(1.20)

        # Step 2: 문제 ①, ②를 우측 중앙에서 크게 동적 시연 후 상단 슬롯으로 도킹
        top_pair_3a = VGroup(card_3_1, card_3_2)
        top_pos_3a = top_pair_3a.get_center().copy()
        top_pair_3a.scale(1.08).move_to([1.95, 0.10, 0])
        self.play(
            FadeIn(VGroup(q3_1, unpin_l, q3_1_cap)),
            FadeIn(VGroup(q3_2, sk1, sk2, sk3, blk_wall, blk_tag, q3_2_cap)),
            run_time=1.00,
        )
        self.play(
            GrowArrow(unpin_arr),
            FadeIn(unpin_r, scale=1.18),
            GrowArrow(blk_arr),
            Flash(blk_wall.get_center(), color=C_CORAL, line_length=0.28, num_lines=10),
            run_time=1.15,
        )
        self.wait(2.10)
        self.play(top_pair_3a.animate.scale(1.0 / 1.08).move_to(top_pos_3a), run_time=0.95)

        # Step 3: 문제 ③, ④를 하단에서 크게 동적 시연 후 연결 보드 완성
        date_blade = Line([2.42, -0.62, 0], [2.42, -1.58, 0], color=C_CORAL, stroke_width=4.2).set_z_index(12)
        self.play(
            FadeIn(card_3_3, shift=UP * 0.10),
            FadeIn(VGroup(q3_4, dots_27_cyan), shift=UP * 0.10),
            run_time=0.95,
        )
        self.add(date_blade)
        self.cam_move(
            zoom=1.34,
            center=[1.92, -1.14, 0],
            anims=[
                date_blade.animate.move_to([5.28, -1.10, 0]),
                ReplacementTransform(dots_27_cyan, dots_27_final),
                FadeIn(q3_4_cap, shift=UP * 0.06),
            ],
            rt=1.40,
        )
        self.remove(date_blade)
        self.wait(2.00)
        self.reset_cam_2d(rt=1.00)

        beat3a_all = VGroup(res_grp_3, vs_arr_3, card_3_1, card_3_2, card_3_3, q3_4, dots_27_final, q3_4_cap)
        self.check_bounds(beat3a_all, "CH3A RESOURCE & OBSTACLES")
        self.wait(2.40)

        # -------------------------------------------------------------------
        # Beat 3B: 역할 분업을 단계별로 동적 시연 후 파이프라인 연결
        # -------------------------------------------------------------------
        role_stages = ["조사", "총괄", "구현", "점검"]
        hb = self.update_subtitle(
            hb,
            "해결 ① 조사, 총괄(Claude), 구현, 점검으로 역할을 나누고 서브에이전트마다 모델을 명시했습니다",
        )

        role_banner = fit(
            pill(f"해결책 ① {num(len(role_stages))}단계 분업: 작업별 모델을 명시하고 수집 구현과 재호출 해시 점검을 분리", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=12.4, z=9),
            max_w=12.00,
        ).move_to([0.0, 2.58, 0])

        s1_c = np.array([-4.55, 0.25, 0.0])
        s1_hdr = pill("① 사전 조사", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=12.2, z=8).move_to([-4.55, 1.82, 0])
        s1_dome = Circle(radius=1.08, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_VIOLET, stroke_width=2.3).move_to(s1_c).set_z_index(4)
        s1_inner = Circle(radius=0.62, fill_opacity=0.0, stroke_color=C_SLATE, stroke_width=1.2).move_to(s1_c).set_z_index(5)
        s1_arm = Line(s1_c, s1_c + UP * 1.04, color=C_GOLD, stroke_width=3.0).set_z_index(8)
        s1_beacons = VGroup(
            *[
                Dot(
                    s1_c + np.array([0.86 * math.cos(k * TAU / target_total), 0.86 * math.sin(k * TAU / target_total), 0.0]),
                    radius=0.055,
                    color=C_CYAN if k < target_counts["생명보험"] else C_GOLD,
                ).set_z_index(7)
                for k in range(target_total)
            ]
        )
        s1_cap = fit(
            VGroup(
                txt(f"생명보험 {num(target_counts['생명보험'])}개사, 손해보험 {num(target_counts['손해보험'])}개사", size=11.0, color=C_INK_0, bold=True, z=7),
                txt("(총자산 기사 기준, 공식 순위 미확정)", size=10.0, color=C_INK_1, z=7),
            ).arrange(DOWN, buff=0.04),
            max_w=2.68,
        ).move_to([-4.55, -1.16, 0])
        st1_grp = VGroup(s1_hdr, s1_dome, s1_inner, s1_arm, s1_beacons, s1_cap)

        s2_hdr = pill("② 총괄 지휘 (Claude)", fg=C_GOLD, bg="#383016", border=C_GOLD, size=12.2, z=8).move_to([-1.55, 1.82, 0])
        s2_mold = VGroup(
            RegularPolygon(n=6, fill_color="#2A2312", fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.5).scale(0.66),
            RegularPolygon(n=6, fill_opacity=0.0, stroke_color=WHITE, stroke_width=1.0, stroke_opacity=0.45).scale(0.54),
        ).move_to([-2.12, 0.25, 0]).set_z_index(6)
        s2_mold_t = fit(VGroup(txt(pilot_org, size=10.8, color=C_GOLD, bold=True, z=8), txt("시범 표준", size=10.4, color=WHITE, bold=True, z=8)).arrange(DOWN, buff=0.04), max_w=1.06).move_to(s2_mold)
        s2_prism = VGroup(
            Polygon([-1.32, 0.62, 0], [-0.82, 0.36, 0], [-0.82, 0.14, 0], [-1.32, -0.12, 0], fill_color="#112B38", fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.2),
            Line([-1.24, 0.46, 0], [-0.90, 0.25, 0], color=WHITE, stroke_width=1.4, stroke_opacity=0.55),
            Dot([-0.82, 0.25, 0], radius=0.048, color=C_GOLD),
        ).set_z_index(6)
        s2_rays = VGroup(*[Line([-0.82, 0.25, 0], [-0.28, -0.52 + k * 0.22, 0], color=C_GOLD if k % 2 == 0 else C_CYAN, stroke_width=2.0).set_z_index(5) for k in range(8)])
        s2_cap = fit(txt(f"시범 구현 후 {num(batch_cnt)}개사 수집 배분", size=10.8, color=C_INK_0, bold=True, z=7), max_w=2.66).move_to([-1.55, -1.16, 0])
        st2_grp = VGroup(s2_hdr, s2_mold, s2_mold_t, s2_prism, s2_rays, s2_cap)

        s3_hdr = pill(f"③ 수집 구현 ×{num(batch_cnt)}", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.2, z=8).move_to([1.55, 1.82, 0])
        s3_tag = pill("모델 명시 서브에이전트", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=10.4, px=0.10, py=0.035, z=8).move_to([1.55, 1.28, 0])
        s3_lanes = VGroup()
        for k in range(batch_cnt):
            ly = 0.92 - k * 0.115
            ln_c = C_CORAL if k >= auto_cnt else C_CYAN
            s3_lanes.add(VGroup(Line([0.52, ly, 0], [2.42, ly, 0], color=ln_c, stroke_width=1.8, stroke_opacity=0.90), Dot([2.46, ly, 0], radius=0.036, color=ln_c)).set_z_index(6))
        s3_cap = fit(txt(f"{num(auto_cnt)}개사 자동 수집, 차단 {num(blocked_cnt)}개사 수동 다운로드", size=10.6, color=C_INK_0, bold=True, z=7), max_w=2.70).move_to([1.55, -1.16, 0])
        st3_grp = VGroup(s3_hdr, s3_tag, s3_lanes, s3_cap)

        s4_hdr = pill(f"④ 독립 점검 ×{num(auto_cnt)}", fg=C_MINT, bg="#16382C", border=C_MINT, size=12.2, z=8).move_to([4.55, 1.82, 0])
        s4_tag = pill("점검 모델(sonnet)", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=10.4, px=0.10, py=0.035, z=8).move_to([4.55, 1.28, 0])
        pdf_a = make_doc_icon(0.74, 0.76, col=C_CYAN, badge_txt="수집 PDF", z=7).move_to([3.84, 0.44, 0])
        pdf_b = make_doc_icon(0.74, 0.76, col=C_GOLD, badge_txt="재호출 PDF", z=7).move_to([5.26, 0.44, 0])
        hash_seal = make_shield_icon(
            [4.55, -0.36, 0],
            scale_f=1.32,
            col=C_MINT,
            bg="#112820",
            mark_mob=txt("해시 일치\n쪽수 ✓", size=9.6, color=C_MINT, bold=True),
            z=9,
        )
        s4_cap = fit(txt(f"수집 모듈 {num(auto_cnt)}개사 재호출 해시 대조", size=10.6, color=C_INK_0, bold=True, z=7), max_w=2.68).move_to([4.55, -1.16, 0])
        st4_grp = VGroup(s4_hdr, s4_tag, pdf_a, pdf_b, hash_seal, s4_cap)

        relay_links = VGroup(
            arrow_2d([-3.40, 0.25, 0], [-2.78, 0.25, 0], color=C_VIOLET, sw=2.6, tip=0.12, z=7),
            arrow_2d([-0.22, 0.25, 0], [0.42, 0.25, 0], color=C_GOLD, sw=2.6, tip=0.12, z=7),
            arrow_2d([2.58, 0.25, 0], [3.28, 0.25, 0], color=C_CYAN, sw=2.6, tip=0.12, z=7),
        )

        ret_path = VMobject(color=C_GOLD, stroke_width=2.6).set_z_index(5)
        ret_path.set_points_as_corners([[4.55, -1.48, 0], [4.55, -2.18, 0], [-1.55, -2.18, 0], [-1.55, -1.52, 0]])
        ret_tip = Arrow([-1.55, -1.78, 0], [-1.55, -1.46, 0], buff=0, color=C_GOLD, stroke_width=2.6, tip_length=0.12).set_z_index(6)
        ret_lbl = fit(
            pill(f"배치 시점 전체 {TERM['test']} {num(batch_tests)}건 통과, 수집 PDF {num(batch_pdfs)}건 진본과 쪽수 확인 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=12.0, z=8),
            max_w=9.10,
        ).move_to([1.50, -2.18, 0])

        self.add(s1_arm)
        self.cam_move(
            zoom=1.34,
            center=[-3.05, 0.25, 0],
            anims=[
                FadeOut(beat3a_all, shift=UP * 0.10),
                FadeIn(VGroup(s1_hdr, s1_dome, s1_inner, s1_beacons, s1_cap)),
                Rotate(s1_arm, angle=-TAU, about_point=s1_c),
                GrowArrow(relay_links[0]),
                FadeIn(VGroup(s2_hdr, s2_mold, s2_mold_t, s2_prism, s2_cap)),
                Create(s2_rays, lag_ratio=0.06),
            ],
            rt=1.65,
        )
        self.remove(beat3a_all)
        self.wait(1.85)

        self.cam_move(
            zoom=1.34,
            center=[3.00, 0.25, 0],
            anims=[
                GrowArrow(relay_links[1]),
                FadeIn(VGroup(s3_hdr, s3_tag, s3_cap)),
                LaggedStart(*[Create(ln[0]) for ln in s3_lanes], lag_ratio=0.03),
                LaggedStart(*[FadeIn(ln[1], scale=0.4) for ln in s3_lanes], lag_ratio=0.03),
                GrowArrow(relay_links[2]),
                FadeIn(VGroup(s4_hdr, s4_tag, pdf_a, pdf_b, s4_cap)),
            ],
            rt=1.65,
        )
        self.play(
            pdf_a.animate.shift(RIGHT * 0.22 + DOWN * 0.18),
            pdf_b.animate.shift(LEFT * 0.22 + DOWN * 0.18),
            FadeIn(hash_seal, scale=1.35),
            Flash([4.55, -0.34, 0], color=C_MINT, line_length=0.28, num_lines=10),
            run_time=0.95,
        )
        self.wait(1.85)

        ret_pulse = glow_dot([4.55, -1.48, 0], color=C_GOLD, r=0.075, z=14)
        self.add(ret_pulse)
        self.reset_cam_2d(
            anims=[
                FadeIn(role_banner, shift=DOWN * 0.08),
                Create(ret_path),
                FadeIn(ret_tip),
                MoveAlongPath(ret_pulse, ret_path),
                FadeIn(ret_lbl, shift=UP * 0.06),
            ],
            rt=1.30,
        )
        self.remove(ret_pulse)

        beat3b_roles = VGroup(role_banner, st1_grp, st2_grp, st3_grp, st4_grp, relay_links, ret_path, ret_tip, ret_lbl)
        self.check_bounds(beat3b_roles, "CH3B AGENT ROLES")
        self.wait(3.00)

        # -------------------------------------------------------------------
        # Beat 3C: True 3D Cylindrical 16-Insurer Ring Arena (큰 bb_badge + 여유 있는 2차 파동)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"시범({pilot_org}) 구현 후 실행한 {num(batch_cnt)}개사 중 {num(auto_cnt)}개사는 대표 상품 문서 수집과 해시 점검을 마쳤고, 차단 {num(blocked_cnt)}개사는 수동으로 다운로드합니다",
        )

        def hud_stage_card(lbl: str, sub: str, col: str, y_pos: float) -> VGroup:
            b = RoundedRectangle(corner_radius=0.08, width=3.02, height=0.94, fill_color="#091018", fill_opacity=0.97, stroke_color=col, stroke_width=2.1).move_to([-4.62, y_pos, 0]).set_z_index(25)
            tg = fit(VGroup(txt(lbl, size=11.8, color=col, bold=True, z=26), txt(sub, size=10.4, color=C_INK_0, z=26)).arrange(DOWN, buff=0.05), max_w=2.82).move_to(b)
            return VGroup(b, tg)

        hud_3c_1 = hud_stage_card(f"시범 기준: {pilot_org}", "한화생명, 삼성화재는 선행 구축", C_GOLD, 1.56)
        hud_3c_2 = hud_stage_card(f"일차 단계: 수집 ×{num(batch_cnt)}", f"{num(auto_cnt)}개사 대표 상품 수집, {num(blocked_cnt)}개사 차단", C_CYAN, 0.42)
        hud_3c_3 = hud_stage_card(f"이차 단계: 점검 ×{num(auto_cnt)}", "sonnet 재호출 해시 일치 확인", C_MINT, -0.72)
        hud_3c_note = fit(
            pill("막대 높이: 단계 표시 (대기 -> 수집 -> 점검 예시 그림)", fg=C_INK_0, bg="#091018", border=C_SLATE, size=10.2, px=0.10, py=0.04, z=25),
            max_w=3.02,
        ).move_to([-4.62, -1.56, 0])
        done_3c_pill = fit(
            pill(
                f"결과: {num(auto_cnt)}개사 대표 상품 문서 수집 및 해시 점검 완료, 차단 {num(blocked_cnt)}개사 수동 다운로드, PDF {num(batch_pdfs)}건 확보 ✓",
                fg=C_DARK_INK,
                bg=C_GOLD,
                border=WHITE,
                size=12.0,
                z=25,
            ),
            max_w=12.00,
        ).move_to([0.0, -2.54, 0])
        hud_3c_left = VGroup(hud_3c_1, hud_3c_2, hud_3c_3, hud_3c_note)

        ring_cx, ring_cy, ring_bz = 1.48, 0.56, -0.42
        ring_rx, ring_ry = 2.92, 1.58
        arena_rings = VGroup(
            *[
                Circle(radius=1.0, fill_opacity=0.0, stroke_color=C_CYAN_DIM if idx < 2 else C_CYAN, stroke_width=1.4, stroke_opacity=0.58)
                .stretch_to_fit_width(2 * ring_rx * sc)
                .stretch_to_fit_height(2 * ring_ry * sc)
                .move_to([ring_cx, ring_cy, ring_bz])
                for idx, sc in enumerate([0.36, 0.68, 1.00])
            ]
        )
        pilot_tower = pillar_3d(ring_cx, ring_cy, 0.64, 0.64, 1.62, base_z=ring_bz, col=C_GOLD, opacity=0.90, stroke_col=WHITE, sw=1.7)
        bb_pilot = bb_badge(f"시범: {pilot_org}", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=13.2).move_to([ring_cx, ring_cy, ring_bz + 2.02])

        arena_spokes = VGroup()
        ring_pillars: list[Prism] = []
        ring_pillars_grp = VGroup()
        ring_coords: list[tuple[float, float, bool]] = []
        blocked_wall_3d = VGroup()
        bb_blocked = VGroup()
        front_idx = 8

        for idx, nm in enumerate(batch_orgs):
            ang = math.pi / 2 - idx * (TAU / len(batch_orgs))
            px = ring_cx + ring_rx * math.cos(ang)
            py = ring_cy + ring_ry * math.sin(ang)
            is_blocked = nm == "한화손해보험"
            ring_coords.append((px, py, is_blocked))

            sp_col = C_CORAL if is_blocked else C_SLATE
            arena_spokes.add(Line([ring_cx, ring_cy, ring_bz], [px, py, ring_bz], color=sp_col, stroke_width=1.5, stroke_opacity=0.68))

            init_h = 0.28 if is_blocked else 0.18
            p_col = C_CORAL if is_blocked else C_SLATE
            pr = pillar_3d(px, py, 0.36, 0.36, init_h, base_z=ring_bz, col=p_col, opacity=0.88 if is_blocked else 0.50, stroke_col=WHITE if is_blocked else C_SLATE, sw=1.3)
            ring_pillars.append(pr)
            ring_pillars_grp.add(pr)

            if is_blocked:
                wx = ring_cx + (ring_rx - 0.55) * math.cos(ang)
                wy = ring_cy + (ring_ry - 0.40) * math.sin(ang)
                wall_p = pillar_3d(wx, wy, 0.16, 0.52, 0.78, base_z=ring_bz, col=C_CORAL, opacity=0.94, stroke_col=WHITE, sw=1.5).rotate(ang, axis=OUT)
                blocked_wall_3d.add(wall_p)
                bb_blocked = bb_badge(
                    f"{nm}: {num(hf_block_code)} 차단",
                    "우회 금지 -> 수동 다운로드",
                    fg=C_WHITE,
                    bg="#3B1219",
                    border=C_CORAL,
                    size=12.6,
                    sub_size=11.0,
                    sub_col=C_GOLD,
                ).move_to([px - 0.25, py + 0.20, ring_bz + 1.10])

        fx0, fy0, _ = ring_coords[front_idx]
        bb_verified = bb_badge(
            f"{batch_orgs[0]}, {batch_orgs[front_idx]} 등 {num(auto_cnt)}개사",
            "대표 상품 수집 + sonnet 해시 일치 ✓",
            fg=C_DARK_INK,
            bg=C_GOLD,
            border=WHITE,
            size=12.8,
            sub_size=11.2,
            sub_col=C_DARK_INK,
        ).move_to([fx0 - 0.10, fy0 - 0.10, ring_bz + 1.62])

        all_3c_bbs = [bb_pilot, bb_blocked, bb_verified]
        self.register_billboards(*all_3c_bbs)
        self.add_fixed_in_frame_mobjects(hud_3c_left, done_3c_pill)
        self.remove(done_3c_pill)

        self.cam_move(
            phi=54 * DEGREES,
            theta=-68 * DEGREES,
            zoom=0.98,
            center=[0.45, 0.24, 0.08],
            anims=[
                FadeOut(beat3b_roles, shift=UP * 0.10),
                FadeIn(hud_3c_left, shift=RIGHT * 0.10),
                FadeIn(arena_rings),
                Create(arena_spokes, lag_ratio=0.02),
                FadeIn(pilot_tower, shift=OUT * 0.35),
                FadeIn(ring_pillars_grp, lag_ratio=0.02),
                FadeIn(blocked_wall_3d, shift=OUT * 0.25),
                FadeIn(VGroup(bb_pilot, bb_blocked)),
            ],
            rt=1.45,
        )
        self.remove(beat3b_roles)
        self.wait(1.60)

        wave_ring_1 = Circle(radius=0.45, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=4.4).move_to([ring_cx, ring_cy, ring_bz + 0.06])
        self.add(wave_ring_1)
        fetch_3d_anims = []
        for idx, (px, py, is_blocked) in enumerate(ring_coords):
            if is_blocked:
                continue
            target_pr = pillar_3d(px, py, 0.36, 0.36, 0.76, base_z=ring_bz, col=C_CYAN, opacity=0.80, stroke_col=C_CYAN, sw=1.4)
            fetch_3d_anims.append(Transform(ring_pillars[idx], target_pr))
        self.cam_move(
            theta=-50 * DEGREES,
            anims=[
                wave_ring_1.animate.scale(6.2).set_stroke(opacity=0.0),
                LaggedStart(*fetch_3d_anims, lag_ratio=0.035),
            ],
            rt=1.70,
        )
        self.remove(wave_ring_1)
        self.wait(1.60)

        wave_ring_2 = Circle(radius=0.45, fill_opacity=0.0, stroke_color=C_MINT, stroke_width=4.6).move_to([ring_cx, ring_cy, ring_bz + 0.10])
        self.add(wave_ring_2)
        ver_3d_anims = []
        for idx, (px, py, is_blocked) in enumerate(ring_coords):
            if is_blocked:
                continue
            gold_pr = pillar_3d(px, py, 0.36, 0.36, 1.28, base_z=ring_bz, col=C_GOLD, opacity=0.88, stroke_col=WHITE, sw=1.5)
            ver_3d_anims.append(Transform(ring_pillars[idx], gold_pr))
        self.add_fixed_in_frame_mobjects(done_3c_pill)
        self.cam_move(
            phi=50 * DEGREES,
            theta=-34 * DEGREES,
            anims=[
                wave_ring_2.animate.scale(6.2).set_stroke(opacity=0.0),
                LaggedStart(*ver_3d_anims, lag_ratio=0.035),
                FadeIn(bb_verified),
                FadeIn(done_3c_pill, shift=UP * 0.06),
            ],
            rt=1.80,
        )
        self.remove(wave_ring_2)
        self.check_bounds(VGroup(hud_3c_left, done_3c_pill), "CH3C HUD")
        self.wait(3.20)

        arena_3d_all = VGroup(arena_rings, arena_spokes, pilot_tower, ring_pillars_grp, blocked_wall_3d)

        # -------------------------------------------------------------------
        # Beat 3D: Pure 2D 7-Day Rotating Schedule + News Filter (큰 글씨 + 느긋한 회전)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"해결 ② 하루 {num(lim_search)}회 검색 한도에 맞춰 요일별로 배분하고, 대상 기간 외 {num(n_out)}건을 필터링했습니다",
        )

        rad_c = np.array([-3.08, 0.16, 0.0])
        rad_r = 1.28
        rad_rings = VGroup(
            Circle(radius=rad_r, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.8, stroke_opacity=0.75).move_to(rad_c),
            Circle(radius=0.88, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.1, stroke_opacity=0.38).move_to(rad_c),
            Circle(radius=0.48, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.2).move_to(rad_c),
        ).set_z_index(4)
        rad_core_t = VGroup(txt("요일별", size=11.6, color=C_GOLD, bold=True, z=8), txt("검색 배분", size=10.6, color=C_INK_0, bold=True, z=8)).arrange(DOWN, buff=0.03).move_to(rad_c)

        plan_items = list(daily_plan.items())
        n_days = len(plan_items)
        day_dots, day_lbls = VGroup(), VGroup()
        for d_i, (day_k, info) in enumerate(plan_items):
            q_cnt = info["queries"]
            orgs_d = info["orgs"]
            if q_cnt == 0:
                d_nm = f"{day_k}: 재수집, 마감 ({num(q_cnt)}회)"
                d_col = C_MINT
            else:
                d_nm = f"{day_k}: {orgs_d[0]} 외 ({num(q_cnt)}회)"
                d_col = C_GOLD if day_k == "금" else (C_VIOLET if day_k == "토" else C_CYAN)
            ang = math.pi / 2 - d_i * (2 * math.pi / n_days)
            dp = rad_c + np.array([rad_r * math.cos(ang), rad_r * math.sin(ang), 0.0])
            d_dot = Circle(radius=0.11, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=d_col, stroke_width=2.2).move_to(dp).set_z_index(7)
            day_dots.add(d_dot)
            d_lbl = fit(txt(d_nm, size=10.2, color=d_col if d_i >= 4 else C_INK_0, bold=True, z=7), max_w=1.64)
            d_lbl.next_to(d_dot, UP if d_i == 0 else (RIGHT if d_i in (1, 2) else (DOWN if d_i in (3, 4) else LEFT)), buff=0.08)
            if d_i == 3:
                d_lbl.shift(RIGHT * 0.46)
            elif d_i == 4:
                d_lbl.shift(LEFT * 0.46)
            day_lbls.add(d_lbl)
        rad_caption = fit(
            pill(f"하루 {num(lim_search)}회 무료 한도 안에서 {num(news_inst_cnt)}개 기관 순환 점검", fg=C_CYAN, bg=C_PANEL, border=C_CYAN, size=11.4),
            max_w=5.15,
        ).move_to([-3.08, -2.52, 0])

        sweep_ang = ValueTracker(math.pi / 2)
        sweep_beam = always_redraw(
            lambda: VGroup(
                Sector(radius=rad_r - 0.02, start_angle=sweep_ang.get_value() - 0.48, angle=0.48, fill_color=C_CYAN, fill_opacity=0.24, stroke_width=0).shift(rad_c),
                Line(rad_c, rad_c + np.array([rad_r * math.cos(sweep_ang.get_value()), rad_r * math.sin(sweep_ang.get_value()), 0.0]), color=C_GOLD, stroke_width=3.0),
            ).set_z_index(6)
        )

        g1_x, g2_x, g3_x = 0.52, 2.28, 4.02
        gate_specs = [
            (g1_x, C_CYAN, "① 발표일 우선 기재"),
            (g2_x, C_CORAL, "② 기간 외 코드 제외"),
            (g3_x, C_MINT, "③ 대상 외 종목 제외"),
        ]
        sieve_gates = VGroup()
        for gx, g_col, g_top in gate_specs:
            sieve_gates.add(
                VGroup(
                    make_filter_gate(gx, y_bot=-1.38, y_top=1.38, gap_half=0.48, col=g_col, z=6),
                    fit(pill(g_top, fg=g_col, bg=C_PANEL_HI, border=g_col, size=11.0, px=0.10, py=0.05, z=8), max_w=1.74).move_to([gx, 1.80, 0]),
                )
            )
        cut_note = fit(
            pill(f"{num(n_struct)}건 중 기간 외 {num(n_out)}건 제외, 기간 내 {num(n_in_win)}건", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=11.2, z=8),
            max_w=3.55,
        ).move_to([g2_x - 0.08, -2.02, 0])
        noise_note = fit(txt(f"{excl_lines}, {excl_topics} 등 필터링 (탈락 입자는 예시 그림)", size=10.2, color=C_INK_1, z=7), max_w=3.42).move_to([g3_x + 0.02, -1.66, 0])
        clean_pool = make_silo_pool([5.42, 0.05, 0], w=1.46, h=2.04, col=C_GOLD, accent=C_MINT, z=4)
        pool_lbl = fit(
            VGroup(
                txt(f"선별된 {TERM['trend']}", size=11.6, color=C_GOLD, bold=True, z=7),
                txt(f"{TERM['master']} 기록 ✓", size=11.0, color=C_MINT, bold=True, z=7),
            ).arrange(DOWN, buff=0.07),
            max_w=1.32,
        ).move_to(clean_pool.get_top() + DOWN * 0.54)

        self.reset_cam_2d(
            anims=[
                FadeOut(arena_3d_all),
                FadeOut(VGroup(*all_3c_bbs)),
                FadeOut(hud_3c_left),
                FadeOut(done_3c_pill),
                FadeIn(rad_rings),
                FadeIn(rad_core_t),
                FadeIn(day_dots, lag_ratio=0.06),
                FadeIn(day_lbls),
                FadeIn(rad_caption, shift=UP * 0.08),
                FadeIn(sieve_gates, lag_ratio=0.12),
                FadeIn(VGroup(clean_pool, pool_lbl), shift=LEFT * 0.10),
            ],
            rt=1.20,
        )
        self.clear_billboards(*all_3c_bbs)
        self.remove_fixed_in_frame_mobjects(hud_3c_left, done_3c_pill)
        self.remove(arena_3d_all, hud_3c_left, done_3c_pill, *ring_pillars)
        self.wait(1.30)

        self.add(sweep_beam)
        good_news_pts, bad_date_pts, bad_noise_pts = VGroup(), VGroup(), VGroup()
        sieve_anims = []
        emit_pt = rad_c + RIGHT * rad_r
        for k in range(n_in_win):
            pt = glow_dot(emit_pt, color=C_GOLD, r=0.060, z=12)
            good_news_pts.add(pt)
            sieve_anims.append(Succession(Wait(k * 0.22), MoveAlongPath(pt, Line(emit_pt + UP * ((-0.35 + k * 0.24) * 0.4), np.array([5.40, -0.58 + k * 0.20, 0])), run_time=1.80)))
        for k in range(n_out):
            pt_b = glow_dot(emit_pt, color=C_CORAL, r=0.042, z=11)
            bad_date_pts.add(pt_b)
            sieve_anims.append(
                Succession(
                    Wait(0.05 + k * 0.045),
                    MoveAlongPath(
                        pt_b,
                        CubicBezier(emit_pt, np.array([0.8, 0.38 - (k % 5) * 0.16, 0]), np.array([g2_x - 0.05, -0.25, 0]), np.array([g2_x, -1.52, 0])),
                        run_time=1.35,
                    ),
                )
            )
        for k in range(2):
            pt_n = glow_dot(emit_pt, color=C_AMBER, r=0.052, z=11)
            bad_noise_pts.add(pt_n)
            sieve_anims.append(Succession(Wait(0.30 + k * 0.28), MoveAlongPath(pt_n, CubicBezier(emit_pt, np.array([1.8, 0.2, 0]), np.array([g3_x - 0.05, -0.2, 0]), np.array([g3_x, -1.45, 0])), run_time=1.45)))

        self.add(good_news_pts, bad_date_pts, bad_noise_pts)
        self.cam_move(
            zoom=1.22,
            center=[2.00, -0.05, 0],
            anims=[
                sweep_ang.animate.set_value(math.pi / 2 - 2 * math.pi),
                *sieve_anims,
                FadeIn(cut_note, shift=UP * 0.08),
                FadeIn(noise_note),
                *[d.animate.set_fill(C_CYAN_DIM, opacity=0.95) for d in day_dots],
            ],
            rt=2.60,
            rate_func=linear,
        )
        self.reset_cam_2d(
            anims=[FadeOut(bad_date_pts, scale=0.3), FadeOut(bad_noise_pts, scale=0.3), Circumscribe(clean_pool, color=C_GOLD, stroke_width=2.5, buff=0.04)],
            rt=1.00,
        )
        self.remove(bad_date_pts, *bad_date_pts, bad_noise_pts, *bad_noise_pts)
        sweep_beam.clear_updaters()

        ch3_stage = VGroup(rad_rings, rad_core_t, day_dots, day_lbls, rad_caption, sweep_beam, sieve_gates, cut_note, noise_note, clean_pool, pool_lbl, good_news_pts)
        self.check_bounds(ch3_stage, "CH3D RADAR SIEVE")
        self.wait(3.00)

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
        rev_old = fact("example_targeted_anticancer", "revisions", 0)
        rev_new = fact("example_targeted_anticancer", "revisions", -1)
        basis_mw = rev_new["basis_manwon"]
        pay_old_mw = rev_old["pay_manwon"]
        old_red_months = rev_old["reduce"][0]["months"]
        old_red_rate = rev_old["reduce"][0]["rate"]
        old_red_mw = round(pay_old_mw * old_red_rate)
        old_red_yr = old_red_months // 12

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
            f"{TERM['extract']} 단계: 상품요약서와 사업방법서의 급부 및 가입한도 {TERM['extract']}",
            "대용량 상품요약서 호출 부담, 수치 직접 추출 오류, 이미지형 요약서, 가입한도 초기화 결함을 해결했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 4A: 각 추출 난제를 크게 동적으로 시연한 뒤 4분할 진단 차트로 조립
        # -------------------------------------------------------------------
        res_box_4 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.1).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_4 = pill("추출 도구와 한도 조건", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.4, z=7).move_to([-4.38, 1.92, 0])
        rg4_1 = capacity_ring([-5.15, 0.72, 0], 0.58, C_CYAN, TERM["extractor"], f"하루 {num(lim_ext)}회 무료", z=6)
        rg4_2 = capacity_ring([-3.62, 0.72, 0], 0.58, C_CORAL, "상위 재추출", f"하루 {num(lim_up)}회 상한", z=6)
        res_notes_4 = fit(
            VGroup(
                pill("PDF 표 규칙 추출 코드", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=11.0, z=7),
                pill(f"서브에이전트 {TERM['extract_dual']}, 제미나이 패널", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=10.8, z=7),
                txt("텍스트 표 요약서와 이미지형 요약서 혼재", size=10.6, color=C_INK_1, bold=True, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.08,
        ).move_to([-4.38, -1.14, 0])
        res_grp_4 = VGroup(res_box_4, res_hdr_4, rg4_1, rg4_2, res_notes_4)
        vs_arr_4 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.8, tip=0.13, z=8)

        q4_1 = diag_frame(-0.10, 1.18, C_AMBER, f"문제 ① {num(hw_pages)}쪽 상품요약서 {TERM['extract_init']} 호출 부담")
        bar_base_y = 0.58
        ceil_h = 0.92
        b_1doc_h = ceil_h * (hw_calls / lim_ext)
        ceil_ln = DashedLine([-1.65, bar_base_y + ceil_h, 0], [1.45, bar_base_y + ceil_h, 0], dash_length=0.07, color=C_CYAN, stroke_width=2.0).set_z_index(7)
        ceil_lbl = txt(f"하루 {num(lim_ext)}회 한도", size=10.4, color=C_CYAN, bold=True, z=8).move_to([-1.00, bar_base_y + ceil_h + 0.16, 0])
        b_1doc = Rectangle(width=0.54, height=b_1doc_h, fill_color=C_AMBER, fill_opacity=0.94, stroke_color=WHITE, stroke_width=1.1).move_to([-0.72, bar_base_y + b_1doc_h / 2, 0]).set_z_index(6)
        q4_1_t1 = fit(txt(f"한화 {TERM['extract_init']} {num(hw_calls)}회 ({num(hw_mins)}분)", size=10.6, color=C_AMBER, bold=True, z=7), max_w=1.96).move_to([0.56, bar_base_y + 0.42, 0])
        q4_1_t2 = fit(txt("기존 상품 초기 적재는 비API 경로로 분리", size=10.4, color=C_INK_0, z=7), max_w=3.50).move_to([-0.10, 0.36, 0])
        card_4_1 = VGroup(q4_1, ceil_ln, ceil_lbl, b_1doc, q4_1_t1, q4_1_t2)

        q4_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 수치 직접 추출 오류와 낮은 확정 건수")
        mis_calc = fit(
            VGroup(
                pill(f"원문 {num(ta_mis['correct_pay_manwon'])}만, {num(red_pct)}%", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=10.2, px=0.08, py=0.03),
                arrow_2d([0, 0, 0], [0.28, 0, 0], color=C_CORAL, sw=1.8, tip=0.08),
                pill(f"오류 {num(ta_mis['misread_pay_manwon'])}만, {num(ta_mis['misread_reduced_manwon'])}만 ×", fg=C_WHITE, bg=C_CORAL_DIM, border=C_CORAL, size=10.2, px=0.08, py=0.03),
            ).arrange(RIGHT, buff=0.08),
            max_w=3.48,
        ).move_to([3.88, 1.30, 0]).set_z_index(7)
        prog_w_max = 2.88
        prog_w_22 = prog_w_max * (ts_rows["before"] / ts_rows["total"])
        prog_bg = RoundedRectangle(corner_radius=0.04, width=prog_w_max, height=0.24, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.3).move_to([3.88, 0.78, 0]).set_z_index(6)
        prog_22 = Rectangle(width=prog_w_22, height=0.18, fill_color=C_AMBER, fill_opacity=0.92, stroke_width=0).move_to([3.88 - prog_w_max / 2 + prog_w_22 / 2, 0.78, 0]).set_z_index(7)
        q4_2_cap = fit(txt(f"{TERM['ours']} 상품요약서 {num(ts_rows['total'])}행 중 {num(ts_rows['before'])}행 확정", size=10.6, color=C_AMBER, bold=True, z=7), max_w=3.48).move_to([3.88, 0.44, 0])
        card_4_2 = VGroup(q4_2, mis_calc, prog_bg, prog_22, q4_2_cap)

        q4_3 = diag_frame(-0.10, -1.14, C_VIOLET, f"문제 ③ 미래에셋 요약서 {num(img_pages)}쪽 전체 이미지 문서")
        mosaic_compact, mosaic = VGroup(), VGroup()
        for k in range(12):
            rr, cc = divmod(k, 6)
            c0 = make_doc_icon(0.28, 0.28, col=C_VIOLET, is_image=True, z=7).move_to([-0.85 + cc * 0.31, -0.92 - rr * 0.30, 0])
            c1 = make_doc_icon(0.34, 0.32, col=C_VIOLET, is_image=True, z=7).move_to([-1.15 + cc * 0.42, -0.86 - rr * 0.36, 0])
            mosaic_compact.add(c0)
            mosaic.add(c1)
        q4_3_cap = fit(
            VGroup(
                txt(f"대조용 페이지 로컬 {TERM['ocr']}(tesseract) {num(ocr_test['chars'])}자 중 누락 {num(ocr_test['missed'])}, 오자 {num(ocr_test['wrong'])}", size=10.2, color=C_CORAL, bold=True, z=7),
                txt("(수치 추출 제외, 급부 표 페이지 탐색에만 사용)", size=9.8, color=C_INK_1, z=7),
            ).arrange(DOWN, buff=0.04),
            max_w=3.52,
        ).move_to([-0.10, -1.76, 0])

        q4_4 = diag_frame(3.88, -1.14, C_CORAL, f"문제 ④ {TERM['mock_test']}의 {TERM['rider_limit']} 초기화")
        lim_bars_before = VGroup(
            *[Rectangle(width=0.92, height=0.12, fill_color=C_CYAN, fill_opacity=0.94, stroke_width=0).move_to([2.88, -0.82 - k * 0.17, 0]).set_z_index(7) for k in range(4)]
        )
        wipe_l_lbl = txt(f"{TERM['rider_limit']} {num(prot_rows)}행", size=10.2, color=C_CYAN, bold=True, z=7).move_to([2.88, -1.52, 0])
        wipe_arr = arrow_2d([3.52, -1.08, 0], [4.00, -1.08, 0], color=C_CORAL, sw=2.4, tip=0.09, z=7)
        wipe_r = fit(pill("모의 시트: 한도 행 전체 삭제 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=10.0, px=0.08, py=0.04, z=8), max_w=1.64).move_to([4.84, -1.08, 0])
        q4_4_cap = fit(txt("급부 재추출 시 가입한도 초기화 결함을 실행 전 수정", size=10.4, color=C_INK_0, z=7), max_w=3.50).move_to([3.88, -1.82, 0])

        self.play(FadeIn(res_grp_4, shift=RIGHT * 0.12), GrowArrow(vs_arr_4), run_time=1.00)
        self.wait(1.00)

        # Spotlight ① & ②
        self.cam_move(
            zoom=1.32,
            center=[1.88, 1.18, 0],
            anims=[
                FadeIn(VGroup(q4_1, ceil_ln, ceil_lbl, q4_1_t1, q4_1_t2)),
                GrowFromEdge(b_1doc, DOWN),
                FadeIn(VGroup(q4_2, prog_bg, q4_2_cap)),
                FadeIn(mis_calc, shift=RIGHT * 0.12),
                GrowFromEdge(prog_22, LEFT),
            ],
            rt=1.45,
        )
        self.wait(2.20)

        # Spotlight ③ & ④
        self.play(FadeIn(VGroup(q4_3, mosaic_compact)), FadeIn(VGroup(q4_4, lim_bars_before, wipe_l_lbl, q4_4_cap)), run_time=0.70)
        self.cam_move(
            zoom=1.32,
            center=[1.88, -1.14, 0],
            anims=[
                ReplacementTransform(mosaic_compact, mosaic),
                FadeIn(q4_3_cap, shift=UP * 0.05),
                GrowArrow(wipe_arr),
                lim_bars_before.animate.set_opacity(0.16),
                FadeIn(wipe_r, scale=1.22),
            ],
            rt=1.45,
        )
        self.wait(2.20)
        self.reset_cam_2d(rt=1.00)

        beat4a_all = VGroup(
            res_grp_4, vs_arr_4,
            card_4_1, card_4_2,
            q4_3, mosaic, q4_3_cap,
            q4_4, lim_bars_before, wipe_l_lbl, wipe_arr, wipe_r, q4_4_cap,
        )
        self.check_bounds(beat4a_all, "CH4A EXTRACT DIAGNOSTIC")
        self.wait(2.40)

        # -------------------------------------------------------------------
        # Beat 4B: True 3D (경과 기간 X * 개정 차수 Y * 실제 지급액 Z) 계단 지형 + 고대비 bb_badge
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 모델은 원문 텍스트만 추출하고 수치 계산은 코드가 수행하며, 삼성화재는 PDF 표 규칙으로 추출합니다",
        )

        dual_path_bar = fit(
            pill(f"초기 적재 분리: 기존 상품은 코드 규칙, 서브에이전트 {TERM['extract_dual']}, 제미나이 패널로 처리하고 무료 API는 주간 갱신에 사용", fg=C_GOLD, bg="#091018", border=C_GOLD_DEEP, size=11.8, z=25),
            max_w=12.00,
        ).move_to([0.0, 2.58, 0])

        hud_4b_top = RoundedRectangle(corner_radius=0.08, width=3.62, height=1.96, fill_color="#091018", fill_opacity=0.97, stroke_color=C_CYAN, stroke_width=2.2).move_to([-4.34, 1.02, 0]).set_z_index(25)
        hud_4b_top_t = fit(
            VGroup(
                txt("모델: 원문 텍스트만 추출 (계산 분리)", size=12.0, color=C_CYAN, bold=True, z=26),
                pill(f"{rev_new['benefit']} {num(pay_new_mw)}만 원", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=10.6, px=0.09, py=0.035, z=26),
                pill(f"계약일부터 {num(red_months)}개월 이내 {num(red_pct)}% 감액 지급, 면책기간 {num(wait_days)}일", fg=C_WHITE, bg=C_BG_SUB, border=C_SLATE, size=10.2, px=0.09, py=0.035, z=26),
                txt(f"{TERM['ours']} {num(ts_rows['total'])}행 중 {num(ts_rows['before'])}행 -> {num(ts_rows['after'])}행 확정 ✓", size=10.8, color=C_MINT, bold=True, z=26),
            ).arrange(DOWN, buff=0.09),
            max_w=3.38,
        ).move_to(hud_4b_top)

        hud_4b_bot = RoundedRectangle(corner_radius=0.08, width=3.62, height=1.68, fill_color="#091018", fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.2).move_to([-4.34, -1.04, 0]).set_z_index(25)
        hud_4b_bot_t = fit(
            VGroup(
                txt("코드: 지급액 계산, PDF 표 규칙 추출", size=11.8, color=C_GOLD, bold=True, z=26),
                txt(f"기준 가입금액 {num(basis_mw)}만 원 예시", size=10.8, color=C_WHITE, bold=True, z=26),
                txt(f"삼성화재 {TERM['snapshot']} 급부 {num(sf_total)}건 추출", size=10.8, color=C_CYAN, bold=True, z=26),
                txt(f"(제미나이 독립 구조화와 {num(sf_check)}행 대조)", size=10.0, color=C_INK_1, z=26),
            ).arrange(DOWN, buff=0.07),
            max_w=3.38,
        ).move_to(hud_4b_bot)
        hud_4b_grp = VGroup(dual_path_bar, hud_4b_top, hud_4b_top_t, hud_4b_bot, hud_4b_bot_t)

        step_bz = -0.52
        step_floor = floor_grid_3d(-1.25, 5.05, -1.28, 1.28, z_val=step_bz, step_x=1.575, step_y=1.28, col=C_CYAN_DIM)
        h_max_pay = 1.66

        x_cols = [-0.48, 1.00, 2.48, 3.96]
        y_old, y_new = 0.68, -0.62

        old_pays = [0, old_red_mw, old_red_mw, pay_old_mw]
        new_pays = [0, reduced_pay_mw, pay_new_mw, pay_new_mw]

        blocks_old, blocks_new = VGroup(), VGroup()
        for cx, mw in zip(x_cols, old_pays):
            bh = 0.05 if mw == 0 else h_max_pay * (mw / pay_new_mw)
            bcol = C_CORAL if mw == 0 else (C_SLATE if mw == old_red_mw else C_CYAN)
            blocks_old.add(pillar_3d(cx, y_old, 1.26, 0.84, bh, base_z=step_bz, col=bcol, opacity=0.76, stroke_col=WHITE if mw == pay_old_mw else bcol, sw=1.4))

        for cx, mw in zip(x_cols, new_pays):
            bh = 0.05 if mw == 0 else h_max_pay * (mw / pay_new_mw)
            bcol = C_CORAL if mw == 0 else (C_CYAN if mw == reduced_pay_mw else C_GOLD)
            blocks_new.add(pillar_3d(cx, y_new, 1.26, 0.84, bh, base_z=step_bz, col=bcol, opacity=0.88, stroke_col=WHITE if mw == pay_new_mw else bcol, sw=1.6))

        bb_row_old = bb_badge(f"직전 {rev_old['revision_no']} ({num(old_red_yr)}년 감액)", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=11.6).move_to([-0.35, y_old + 0.85, step_bz + 1.24])
        bb_row_new = bb_badge(f"현행 {rev_new['revision_no']} ({num(red_yr)}년 감액)", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.6).move_to([-1.32, y_new - 0.15, step_bz + 0.72])

        bb_x0 = bb_badge(f"면책기간 {num(wait_days)}일", fg=C_CORAL, bg="#2A0F14", border=C_CORAL, size=11.0).move_to([x_cols[0] - 0.04, -1.36, step_bz + 0.06])
        bb_x1 = bb_badge(f"{num(red_yr)}년 미만", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=11.2).move_to([x_cols[1], -1.36, step_bz + 0.06])
        bb_x2 = bb_badge(f"{num(red_yr)}~{num(old_red_yr)}년 구간", fg=C_GOLD, bg="#181408", border=C_GOLD, size=11.2).move_to([x_cols[2], -1.36, step_bz + 0.06])
        bb_x3 = bb_badge(f"{num(old_red_yr)}년 경과", fg=C_GOLD, bg="#181408", border=C_GOLD, size=11.2).move_to([x_cols[3], -1.36, step_bz + 0.06])

        bb_v_old_red = bb_badge(f"직전 {num(old_red_mw)}만 원", fg=C_INK_0, bg="#0E151E", border=C_SLATE, size=11.4).move_to([x_cols[1] + 0.22, y_old + 0.46, step_bz + h_max_pay * (old_red_mw / pay_new_mw) + 0.36])
        bb_v_old_full = bb_badge(f"직전 {num(pay_old_mw)}만 원", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=11.6).move_to([x_cols[3] + 0.25, y_old + 0.42, step_bz + h_max_pay * (pay_old_mw / pay_new_mw) + 0.36])
        bb_v_new_red = bb_badge(f"현행 {num(reduced_pay_mw)}만 원", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=11.8).move_to([x_cols[1] + 0.12, y_new + 0.02, step_bz + h_max_pay * (reduced_pay_mw / pay_new_mw) + 0.48])
        bb_v_new_full = bb_badge(f"현행 {num(pay_new_mw)}만 원 ▲", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=12.8).move_to([x_cols[2] + 0.65, y_new - 0.18, step_bz + h_max_pay + 0.34])

        bbs_4b_old = [bb_row_old, bb_x0, bb_x1, bb_x2, bb_x3, bb_v_old_red, bb_v_old_full]
        bbs_4b_new = [bb_row_new, bb_v_new_red, bb_v_new_full]
        bbs_4b = [*bbs_4b_old, *bbs_4b_new]
        self.register_billboards(*bbs_4b)
        self.add_fixed_in_frame_mobjects(hud_4b_grp)

        self.cam_move(
            phi=54 * DEGREES,
            theta=-60 * DEGREES,
            zoom=0.92,
            center=[0.48, -0.05, 0.16],
            anims=[
                FadeOut(beat4a_all, shift=UP * 0.10),
                FadeIn(hud_4b_grp, shift=RIGHT * 0.08),
                FadeIn(step_floor),
                LaggedStart(*[FadeIn(bo, shift=OUT * 0.35) for bo in blocks_old], lag_ratio=0.09),
                FadeIn(VGroup(*bbs_4b_old)),
            ],
            rt=1.65,
        )
        self.remove(beat4a_all)
        self.wait(1.90)

        self.cam_move(
            phi=48 * DEGREES,
            theta=-34 * DEGREES,
            zoom=0.92,
            center=[0.52, -0.06, 0.18],
            anims=[
                LaggedStart(*[FadeIn(bn, shift=OUT * 0.48) for bn in blocks_new], lag_ratio=0.09),
                FadeIn(VGroup(*bbs_4b_new)),
            ],
            rt=2.10,
        )
        self.check_bounds(hud_4b_grp, "CH4B HUD")
        self.wait(3.20)

        step_3d_all = VGroup(step_floor, blocks_old, blocks_new)

        # -------------------------------------------------------------------
        # Beat 4C: True 3D 상하 2단 시트 교차 검증 -> 정면 대형 확대경
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            f"해결 ② 이미지형 요약서는 제미나이 패널과 sonnet 에이전트로 {TERM['extract_dual']}해 {TERM['cross_verify']}하고, 재추출 보호를 {TERM['test']}했습니다",
        )

        same_rep_banner = fit(
            pill(
                f"동일 {TERM['extractor']} 반복 {TERM['test']}: {num(same_rep['pages'])}쪽 중 {num(same_rep['wrong_same_way'])}쪽에서 {TERM['extract_init']}과 동일한 오류가 반복되어 이종 {TERM['extractor']}로 {TERM['cross_verify']}",
                fg=C_AMBER,
                bg="#091018",
                border=C_AMBER,
                size=11.8,
                z=25,
            ),
            max_w=12.00,
        ).move_to([0.0, 2.58, 0])

        rows_n, cols_n = 5, 7
        z_top_sh, z_bot_sh = 0.66, -0.66
        top_plate = glass_plane_3d(0.15, -0.05, z_top_sh, 4.90, 2.86, C_CYAN, fill_op=0.14, sw=2.2)
        bot_plate = glass_plane_3d(0.15, -0.05, z_bot_sh, 4.90, 2.86, C_GOLD, fill_op=0.14, sw=2.2)

        top_cells_3d, bot_cells_3d, match_rays_3d = VGroup(), VGroup(), VGroup()
        mismatch_rc = (2, 4)
        diff_x3, diff_y3 = 0.0, 0.0
        for r in range(rows_n):
            for c in range(cols_n):
                cx3 = -1.77 + c * 0.64
                cy3 = 0.95 - r * 0.50
                is_diff = (r, c) == mismatch_rc
                tc = RoundedRectangle(corner_radius=0.03, width=0.50, height=0.36, fill_color=C_CYAN_DIM, fill_opacity=0.68, stroke_color=C_CYAN, stroke_width=1.2).move_to([cx3, cy3, z_top_sh])
                bc = RoundedRectangle(corner_radius=0.03, width=0.50, height=0.36, fill_color="#2A2312", fill_opacity=0.68, stroke_color=C_GOLD, stroke_width=1.2).move_to([cx3, cy3, z_bot_sh])
                top_cells_3d.add(tc)
                bot_cells_3d.add(bc)
                if is_diff:
                    diff_x3, diff_y3 = cx3, cy3
                else:
                    match_rays_3d.add(Line([cx3, cy3, z_bot_sh], [cx3, cy3, z_top_sh], color=C_MINT, stroke_width=1.5, stroke_opacity=0.75))

        diff_pillar_3d = pillar_3d(diff_x3, diff_y3, 0.46, 0.34, z_top_sh - z_bot_sh + 0.32, base_z=z_bot_sh - 0.16, col=C_AMBER, opacity=0.92, stroke_col=WHITE, sw=1.7)
        scan_sheet_3d = Prism(dimensions=[0.09, 3.05, 1.62], fill_color=C_MINT, fill_opacity=0.34, stroke_color=C_MINT, stroke_width=1.9).move_to([-2.30, -0.05, 0.0])

        bb_sh_top = bb_badge(f"상단 {TERM['extract']}: 제미나이 구독 패널", fg=C_CYAN, bg="#07131C", border=C_CYAN, size=12.4).move_to([-3.55, 0.58, z_top_sh])
        bb_sh_bot = bb_badge(f"하단 {TERM['extract']}: sonnet 에이전트", fg=C_GOLD, bg="#181408", border=C_GOLD, size=12.4).move_to([-3.55, -0.58, z_bot_sh])
        bb_sh_diff = bb_badge("불일치 행 -> Claude 대조 검증", "(예시 그림)", fg=C_DARK_INK, bg=C_AMBER, border=WHITE, size=12.2, sub_size=10.6, sub_col=C_DARK_INK).move_to([diff_x3 + 1.75, diff_y3, 0.25])
        bbs_4c = [bb_sh_top, bb_sh_bot, bb_sh_diff]

        self.register_billboards(*bbs_4c)
        self.add_fixed_in_frame_mobjects(same_rep_banner)

        self.cam_move(
            phi=56 * DEGREES,
            theta=-56 * DEGREES,
            zoom=0.98,
            center=[-0.15, -0.02, 0.0],
            anims=[
                FadeOut(step_3d_all),
                FadeOut(VGroup(*bbs_4b)),
                FadeOut(hud_4b_grp),
                FadeIn(same_rep_banner, shift=DOWN * 0.08),
                FadeIn(VGroup(top_plate, bot_plate)),
                FadeIn(top_cells_3d, lag_ratio=0.01),
                FadeIn(bot_cells_3d, lag_ratio=0.01),
                FadeIn(VGroup(bb_sh_top, bb_sh_bot)),
            ],
            rt=1.45,
        )
        self.clear_billboards(*bbs_4b)
        self.remove_fixed_in_frame_mobjects(hud_4b_grp)
        self.remove(step_3d_all, hud_4b_grp)
        self.wait(1.50)

        self.add(scan_sheet_3d)
        self.cam_move(
            phi=50 * DEGREES,
            theta=-32 * DEGREES,
            anims=[
                scan_sheet_3d.animate.move_to([2.60, -0.05, 0.0]),
                Create(match_rays_3d, lag_ratio=0.018),
                FadeIn(diff_pillar_3d, scale=1.15),
                FadeIn(bb_sh_diff),
            ],
            rt=1.90,
        )
        self.remove(scan_sheet_3d)
        self.wait(2.10)

        dual_3d_all = VGroup(top_plate, bot_plate, top_cells_3d, bot_cells_3d, match_rays_3d, diff_pillar_3d)

        # 정면 대형 확대경 + 요약 배너로 연결
        gx0, gy0 = -3.95, 1.08
        dx_g, dy_g = 0.62, 0.48
        cells_grid_2d = VGroup()
        mismatch_cell_2d = None
        for r in range(rows_n):
            for c in range(cols_n):
                is_diff = (r, c) == mismatch_rc
                cell = RoundedRectangle(
                    corner_radius=0.04,
                    width=0.52,
                    height=0.38,
                    fill_color="#283124" if is_diff else C_PANEL_HI,
                    fill_opacity=0.96,
                    stroke_color=C_GOLD if is_diff else C_MINT,
                    stroke_width=2.6 if is_diff else 1.5,
                ).move_to([gx0 + c * dx_g, gy0 - r * dy_g, 0]).set_z_index(4)
                cells_grid_2d.add(cell)
                if is_diff:
                    mismatch_cell_2d = cell
        assert mismatch_cell_2d is not None

        grid_2d_hdr = fit(
            pill(f"제미나이 패널 × sonnet {TERM['extract_dual']} {TERM['cross_verify']} (셀과 불일치 위치는 예시 그림)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.0, z=8),
            max_w=5.25,
        ).move_to([-2.09, 1.74, 0])

        loupe_c = np.array([3.20, 0.16, 0.0])
        loupe_optic = make_loupe(loupe_c, radius=1.50, col=C_GOLD, cone_origin=mismatch_cell_2d.get_right(), z=6)
        loupe_hdr = txt("불일치 행만 정밀 검수", size=13.0, color=C_GOLD, bold=True, z=9).move_to(loupe_c + UP * 0.74)
        loupe_zero = fit(txt(f"지급률, 금액 불일치: {num(img_mismatches)}건", size=12.6, color=C_MINT, bold=True, z=9), max_w=2.66).move_to(loupe_c + UP * 0.15)
        loupe_sub = fit(txt(f"{TERM['extract_dual']} 결과가 일치했으며\n텍스트 차이는 Claude가 대조 확정", size=10.8, color=C_INK_0, bold=True, z=9), max_w=2.66).move_to(loupe_c + DOWN * 0.48)

        img_summary = fit(
            pill(
                f"이미지형 요약서 {num(img_pages)}쪽(약 {num(img_chars_man)}만 자) 확정, 과거 한화 자료 모의 {TERM['test']}로 급부ID {num(inh_rows)}행 승계 확인(실제 재추출 미확인) ✓",
                fg=C_DARK_INK,
                bg=C_GOLD,
                border=WHITE,
                size=11.6,
            ),
            max_w=12.00,
        ).move_to([0.0, -2.42, 0]).set_z_index(8)

        same_rep_2d = fit(
            pill(
                f"동일 {TERM['extractor']} 반복 {TERM['test']}: {num(same_rep['pages'])}쪽 중 {num(same_rep['wrong_same_way'])}쪽에서 {TERM['extract_init']}과 동일한 오류가 반복되어 이종 {TERM['extractor']}로 {TERM['cross_verify']}",
                fg=C_AMBER,
                bg=C_PANEL_HI,
                border=C_AMBER,
                size=11.8,
                z=9,
            ),
            max_w=12.00,
        ).move_to([0.0, 2.58, 0])

        self.reset_cam_2d(
            anims=[
                FadeOut(dual_3d_all),
                FadeOut(VGroup(*bbs_4c)),
                FadeOut(same_rep_banner),
                FadeIn(same_rep_2d),
                FadeIn(grid_2d_hdr),
                FadeIn(cells_grid_2d),
                FadeIn(VGroup(loupe_optic, loupe_hdr, loupe_zero, loupe_sub), scale=0.94),
                FadeIn(img_summary, shift=UP * 0.08),
            ],
            rt=1.25,
        )
        self.clear_billboards(*bbs_4c)
        self.remove_fixed_in_frame_mobjects(same_rep_banner)
        self.remove(dual_3d_all, same_rep_banner)

        ch4_stage = VGroup(same_rep_2d, grid_2d_hdr, cells_grid_2d, loupe_optic, loupe_hdr, loupe_zero, loupe_sub, img_summary)
        self.check_bounds(ch4_stage, "CH4C CROSS READ")
        self.wait(3.40)

        self.fade_out_part(ch4_stage, hl, hr, hb)
