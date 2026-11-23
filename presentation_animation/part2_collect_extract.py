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
    C_WHITE,
    PostLifeBaseScene,
    arrow_2d,
    build_canvas,
    capacity_ring,
    cross_mark,
    fit,
    glow_dot,
    pill,
    txt,
)


class Part2CollectExtractScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.add(build_canvas())

        # ===================================================================
        # 3장 [~36s]: 수집 프로세스 — 시각적 장애 진단 보드와 4단계 에이전트 분업 해법
        # ===================================================================
        hl, hr, hb = self.make_hud(
            3,
            "수집 프로세스 — 한정된 호출 한도와 19개사 공시 장벽을 넘은 방법",
            "최상위 모델 한도 소모, 접속 차단, 27건 중 23건의 기간 경과 기사 유입 등 네 가지 문제를 직면했습니다",
        )

        # -------------------------------------------------------------------
        # Beat 3A: Left Resource Gauges + Right 2x2 Visual Obstacle Quadrant
        # -------------------------------------------------------------------
        res_box_3 = RoundedRectangle(
            corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.0
        ).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_3 = pill("가용 자원 · 한도", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.0, z=7).move_to([-4.38, 1.92, 0])

        rg_1 = capacity_ring([-5.15, 0.72, 0], 0.58, 0.84, C_AMBER, "최상위 AI", "주간 한도 빠듯", z=6)
        rg_2 = capacity_ring([-3.62, 0.72, 0], 0.58, 0.20, C_CYAN, "무료 검색", "일 20회 상한", z=6)
        res_bars_3 = fit(
            VGroup(
                pill("무서버 배치 (월 2,000분 무료)", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.8, z=7),
                pill("유료 크롤링·뉴스 API 예산 0원", fg=C_INK_1, bg=C_BG_SUB, border=C_SLATE, size=9.8, z=7),
                txt("1인 체제 · 19개 기관 상시 점검", size=9.6, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.04,
        ).move_to([-4.38, -1.14, 0])
        res_grp_3 = VGroup(res_box_3, res_hdr_3, rg_1, rg_2, res_bars_3)

        vs_arr_3 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        # 2x2 Visual Obstacle Cards (x = -0.10, 3.88 | y = 1.18, -1.14)
        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=1.9).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=10.8, color=col, bold=True, z=7), max_w=3.44).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        # Q1 (-0.10, 1.18): Unspecified model draining battery bar + unchecked report
        q3_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 모델 미지정 시 최상위 한도 급감")
        bat_bg = RoundedRectangle(corner_radius=0.04, width=2.10, height=0.34, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.5).move_to([-0.68, 1.14, 0]).set_z_index(6)
        bat_full = Rectangle(width=1.96, height=0.22, fill_color=C_GOLD, fill_opacity=0.9, stroke_width=0).move_to([-0.68, 1.14, 0]).set_z_index(7)
        bat_low = Rectangle(width=0.32, height=0.22, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([-1.50, 1.14, 0]).set_z_index(7)
        q3_1_chip = pill("완료보고 ? 미검증", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.8, px=0.08, py=0.03, z=7).move_to([1.02, 1.14, 0])
        q3_1_cap = txt("최상위 모델 자동 호출 소모 · 구두 보고 불신", size=9.2, color=C_INK_1, z=7).move_to([-0.10, 0.50, 0])

        # Q2 (3.88, 1.18): 3 mismatched sockets + 400 blocked wall
        q3_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 19개사 규격 상이 · 한화손보 차단")
        sk1 = RegularPolygon(n=3, fill_color=C_CYAN_DIM, fill_opacity=0.9, stroke_color=C_CYAN, stroke_width=1.5).scale(0.18).move_to([2.48, 1.24, 0]).set_z_index(6)
        sk2 = RegularPolygon(n=6, fill_color=C_PANEL_HI, fill_opacity=0.9, stroke_color=C_GOLD, stroke_width=1.5).scale(0.18).move_to([2.95, 1.24, 0]).set_z_index(6)
        sk3 = Square(side_length=0.28, fill_color=C_PANEL_HI, fill_opacity=0.9, stroke_color=C_VIOLET, stroke_width=1.5).move_to([3.42, 1.24, 0]).set_z_index(6)
        blk_arr = arrow_2d([3.78, 1.24, 0], [4.38, 1.24, 0], color=C_CORAL, sw=2.2, tip=0.10, z=7)
        blk_wall = Rectangle(width=0.14, height=0.62, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([4.50, 1.24, 0]).set_z_index(8)
        blk_tag = pill("400 차단 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.8, px=0.07, py=0.03, z=8).move_to([5.15, 1.24, 0])
        q3_2_cap = txt("폼·문자코드 제각각 · 한화손보 자동접속 차단", size=9.2, color=C_INK_1, z=7).move_to([3.88, 0.50, 0])

        # Q3 (-0.10, -1.14): Failed candidate models + API lock icon
        q3_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 검색 후보 실패 · 뉴스 API 약관 제약")
        m_fail1 = pill("후보A : 503 오류 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.8, px=0.08, py=0.04, z=7).move_to([-1.05, -0.96, 0])
        m_fail2 = pill("후보B : 출처 0건 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.8, px=0.08, py=0.04, z=7).move_to([-1.05, -1.42, 0])
        lock_body = RoundedRectangle(corner_radius=0.04, width=0.44, height=0.36, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=C_VIOLET, stroke_width=1.8).move_to([0.92, -1.24, 0]).set_z_index(7)
        lock_shackle = Arc(radius=0.14, start_angle=0, angle=PI, color=C_VIOLET, stroke_width=2.0).move_to([0.92, -0.98, 0]).set_z_index(7)
        lock_lbl = txt("포털 API 보관제한", size=8.8, color=C_VIOLET, bold=True, z=7).move_to([0.92, -1.62, 0])

        # Q4 (3.88, -1.14): 27-dot matrix (23 turn RED out-of-date vs 4 GOLD valid!)
        q3_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 기간 조건 무시 (27건 중 23건 기간 경과)")
        dots_27 = VGroup()
        for k in range(27):
            rr, cc = divmod(k, 9)
            is_valid = k >= 23
            dcol = C_GOLD if is_valid else C_CORAL
            dots_27.add(
                Circle(radius=0.085, fill_color=dcol, fill_opacity=0.92, stroke_color=WHITE if is_valid else dcol, stroke_width=1.0)
                .move_to([2.60 + cc * 0.32, -0.82 - rr * 0.28, 0]).set_z_index(7)
            )
        q3_4_cap = txt("붉은 점 23건 기간 밖 기사 · 유효 기사 단 4건", size=9.2, color=C_CORAL, bold=True, z=7).move_to([3.88, -1.84, 0])

        self.play(
            FadeIn(hl, shift=DOWN * 0.08),
            FadeIn(hr, shift=DOWN * 0.08),
            FadeIn(hb, shift=UP * 0.08),
            FadeIn(VGroup(res_box_3, res_hdr_3, rg_1[0], rg_1[2], rg_2[0], rg_2[2], res_bars_3), shift=RIGHT * 0.12),
            Create(rg_1[1]),
            Create(rg_2[1]),
            GrowArrow(vs_arr_3),
            FadeIn(VGroup(q3_1, bat_bg, bat_full, q3_1_chip, q3_1_cap)),
            FadeIn(VGroup(q3_2, sk1, sk2, sk3, blk_wall, blk_tag, q3_2_cap)),
            run_time=1.05,
        )
        self.play(
            ReplacementTransform(bat_full, bat_low),
            GrowArrow(blk_arr),
            FadeIn(VGroup(q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_lbl), shift=UP * 0.08),
            FadeIn(q3_4),
            LaggedStart(*[FadeIn(d, scale=0.4) for d in dots_27], lag_ratio=0.02),
            FadeIn(q3_4_cap),
            run_time=1.15,
        )
        beat3a_all = VGroup(
            res_grp_3, vs_arr_3,
            q3_1, bat_bg, bat_low, q3_1_chip, q3_1_cap,
            q3_2, sk1, sk2, sk3, blk_arr, blk_wall, blk_tag, q3_2_cap,
            q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_lbl,
            q3_4, dots_27, q3_4_cap,
        )
        self.check_bounds(beat3a_all, "CH3A VISUAL DIAGNOSTIC")
        self.wait(2.65)

        # -------------------------------------------------------------------
        # Beat 3B: Solution 1 - Iconized 4-Stage Agent Role Division Diagram
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 조사 · 총괄 시범 표준화 · 수집 구현 · 독립 재호출 검증으로 역할을 나누고 모델을 분리 지정했습니다",
            rt=0.38,
        )

        prin_3b = fit(
            pill(
                "해결 설계 ① 4단계 에이전트 분업 : 작업별 모델 명시로 한도 절감 · 구현과 검증 에이전트 분리(재호출 검증만 인정)",
                fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.2,
            ),
            max_w=11.85,
        ).move_to([0.0, 2.58, 0]).set_z_index(9)

        # Build 4 visual-diagram cards (each has a dedicated geometric infographic in its body!)
        def role_vis_card(rx: float, r_col: str, r_title: str, r_model: str, vis_grp: VGroup, r_foot: str) -> VGroup:
            rc = RoundedRectangle(corner_radius=0.08, width=2.62, height=3.42, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=r_col, stroke_width=2.1).move_to([rx, 0.25, 0]).set_z_index(4)
            rt = fit(txt(r_title, size=13.2, color=r_col, bold=True, z=7), max_w=2.36).move_to([rx, 1.56, 0])
            rm = fit(pill(r_model, fg=C_INK_0, bg=C_PANEL_HI, border=r_col, size=9.8, px=0.10, py=0.035, z=7), max_w=2.34).move_to([rx, 1.10, 0])
            vis_grp.move_to([rx, 0.10, 0]).set_z_index(7)
            rf = fit(txt(r_foot, size=9.8, color=C_INK_1, bold=True, z=7), max_w=2.36).move_to([rx, -1.06, 0])
            return VGroup(rc, rt, rm, vis_grp, rf)

        # Vis 1: Web compass + 19 insurer dots
        rv1_dots = VGroup(*[Dot([0.52 * math.cos(k * 2 * PI / 10), 0.52 * math.sin(k * 2 * PI / 10), 0], radius=0.045, color=C_VIOLET if k < 5 else C_CYAN) for k in range(10)])
        rv1 = VGroup(
            Circle(radius=0.52, fill_opacity=0.0, stroke_color=C_VIOLET, stroke_width=1.5),
            rv1_dots,
            pill("19개사 선정", fg=C_VIOLET, bg=C_BG_SUB, border=C_VIOLET, size=9.2, px=0.08, py=0.03),
        )
        rc_1 = role_vis_card(-4.68, C_VIOLET, "① 사전 조사 AI", "웹 탐색 · 주력상품 단서", rv1, "생보 10 · 손보 9곳 확정")

        # Vis 2: Pilot standard stamp -> 4 fan-out tracks
        rv2_tracks = VGroup(*[arrow_2d([0.12, 0.24 - k * 0.16, 0], [0.72, 0.36 - k * 0.24, 0], color=C_GOLD, sw=1.6, tip=0.07) for k in range(4)])
        rv2 = VGroup(
            pill("DB손보\n시범표준", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=9.0, px=0.09, py=0.05).move_to([-0.42, 0, 0]),
            rv2_tracks,
        )
        rc_2 = role_vis_card(-1.56, C_GOLD, "② 총괄 에이전트", "표준 확립 · 분할 지시", rv2, "파일 충돌 0건 · 16개사 배분")

        # Vis 3: 15 cyan auto blocks + 1 coral manual block
        rv3_grid = VGroup()
        for k in range(16):
            rr, cc = divmod(k, 4)
            is_blk = k == 11
            rv3_grid.add(
                RoundedRectangle(corner_radius=0.03, width=0.28, height=0.20, fill_color=C_CORAL_DIM if is_blk else C_CYAN_DIM, fill_opacity=0.95, stroke_color=C_CORAL if is_blk else C_CYAN, stroke_width=1.4)
                .move_to([-0.54 + cc * 0.36, 0.36 - rr * 0.24, 0])
            )
        rc_3 = role_vis_card(1.56, C_CYAN, "③ 수집 구현 ×16", "구현 전용 모델 명시", rv3_grid, "15곳 자동 · 차단 1곳 수동분리")

        # Vis 4: Hash comparison scale (File Hash == Re-call Hash)
        rv4 = VGroup(
            pill("수집본 PDF", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.8, px=0.07, py=0.03).move_to([-0.62, 0.22, 0]),
            pill("재호출 PDF", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.07, py=0.03).move_to([0.62, 0.22, 0]),
            pill("해시 일치 ✓", fg=C_DARK_INK, bg=C_MINT, border=WHITE, size=9.4, px=0.10, py=0.04).move_to([0.0, -0.26, 0]),
        )
        rc_4 = role_vis_card(4.68, C_MINT, "④ 독립 검증 ×16", "검증 전용 경량 모델", rv4, "실제 재호출 · 완료보고 불신")

        role_cards = VGroup(rc_1, rc_2, rc_3, rc_4)
        handoff_arrs = VGroup(
            arrow_2d([-3.34, 0.25, 0], [-2.90, 0.25, 0], color=C_VIOLET, sw=2.4, tip=0.12, z=8),
            arrow_2d([-0.22, 0.25, 0], [0.22, 0.25, 0], color=C_GOLD, sw=2.4, tip=0.12, z=8),
            arrow_2d([2.90, 0.25, 0], [3.34, 0.25, 0], color=C_CYAN, sw=2.4, tip=0.12, z=8),
        )
        ret_line_1 = Line([4.68, -1.46, 0], [4.68, -2.38, 0], color=C_GOLD, stroke_width=2.2).set_z_index(5)
        ret_line_2 = Line([4.68, -2.38, 0], [-1.56, -2.38, 0], color=C_GOLD, stroke_width=2.2).set_z_index(5)
        ret_arr_up = arrow_2d([-1.56, -2.38, 0], [-1.56, -1.48, 0], color=C_GOLD, sw=2.2, tip=0.12, z=6)
        ret_badge = fit(
            pill("총괄 최종 검수 승인 : 전체 시험 579건 통과 · 공시 문서 58종 PDF 진본·쪽수 직접 확인 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=11.2, z=9),
            max_w=8.60,
        ).move_to([1.56, -2.38, 0])

        self.play(
            FadeOut(beat3a_all, shift=UP * 0.10),
            FadeIn(prin_3b, shift=DOWN * 0.08),
            LaggedStart(*[FadeIn(rc, shift=UP * 0.10) for rc in role_cards], lag_ratio=0.10),
            LaggedStart(*[GrowArrow(ha) for ha in handoff_arrs], lag_ratio=0.12),
            run_time=1.20,
        )
        self.remove(beat3a_all)
        self.play(
            Create(ret_line_1),
            Create(ret_line_2),
            GrowArrow(ret_arr_up),
            FadeIn(ret_badge, shift=UP * 0.06),
            Circumscribe(rc_2[0], color=C_GOLD, stroke_width=2.2, buff=0.03),
            run_time=0.90,
        )
        beat3b_roles = VGroup(prin_3b, role_cards, handoff_arrs, ret_line_1, ret_line_2, ret_arr_up, ret_badge)
        self.check_bounds(beat3b_roles, "CH3B AGENT ROLE INFOGRAPHIC")
        self.wait(2.50)

        # -------------------------------------------------------------------
        # Beat 3C: 16-Insurer Parallel Collection Wave + Independent Re-Verify Wave
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "16개 보험사에 수집 파동과 독립 재검증 파동이 차례로 지나가며, 접속 차단 1곳은 우회 없이 수동 분리합니다",
            rt=0.38,
        )

        def make_disp_box(yc: float, col: str, t_top: str, t_bot: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=2.76, height=1.02, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=col, stroke_width=2.2).move_to([-4.62, yc, 0]).set_z_index(6)
            tt = fit(VGroup(txt(t_top, size=12.6, color=col, bold=True, z=8), txt(t_bot, size=10.4, color=C_INK_1, z=8)).arrange(DOWN, buff=0.05), max_w=2.48).move_to(bx)
            return VGroup(bx, tt)

        ag_lead = make_disp_box(1.62, C_GOLD, "② 총괄 에이전트", "표준 배포 · 최종 검수 승인")
        ag_fetch = make_disp_box(0.12, C_CYAN, "③ 수집 에이전트 ×16", "사별 모듈 구축 · 문서 수령")
        ag_ver = make_disp_box(-1.38, C_MINT, "④ 검증 에이전트 ×16", "독립 재호출 · 해시 대조")
        disp_stack = VGroup(
            ag_lead, ag_fetch, ag_ver,
            arrow_2d(ag_lead[0].get_bottom(), ag_fetch[0].get_top(), color=C_GOLD, sw=2.0, tip=0.10, z=7),
            arrow_2d(ag_fetch[0].get_bottom(), ag_ver[0].get_top(), color=C_CYAN, sw=2.0, tip=0.10, z=7),
        )

        org_names = [
            "DB손보", "삼성화재", "한화생명", "삼성생명",
            "교보생명", "신한라이프", "KB손보", "현대해상",
            "메리츠", "NH생명", "NH손보", "한화손보",
            "동양생명", "흥국생명", "롯데손보", "미래에셋",
        ]
        board_x = [-0.88, 0.98, 2.84, 4.70]
        board_y = [1.68, 0.68, -0.32, -1.32]
        ins_rects: list[RoundedRectangle] = []
        ins_statuses: list[Text] = []
        ins_board = VGroup()

        for idx, nm in enumerate(org_names):
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            is_pilot = nm == "DB손보"
            is_blocked = nm == "한화손보"
            init_col = C_GOLD if is_pilot else (C_CORAL if is_blocked else C_SLATE)
            init_fill = "#283124" if is_pilot else (C_CORAL_DIM if is_blocked else C_PANEL)
            rect = RoundedRectangle(
                corner_radius=0.06, width=1.68, height=0.78, fill_color=init_fill, fill_opacity=0.95,
                stroke_color=init_col, stroke_width=2.0 if (is_pilot or is_blocked) else 1.4,
            ).move_to([cx, cy, 0]).set_z_index(5)
            t_nm = txt(nm, size=11.4, color=WHITE if not is_blocked else C_CORAL, bold=True, z=7).move_to([cx, cy + 0.14, 0])
            st_str = "시범 표준 ✓" if is_pilot else ("차단 → 수동반입" if is_blocked else "배정 대기")
            st_col = C_GOLD if is_pilot else (C_CORAL if is_blocked else C_INK_2)
            t_st = txt(st_str, size=9.6, color=st_col, bold=(is_pilot or is_blocked), z=7).move_to([cx, cy - 0.16, 0])
            ins_rects.append(rect)
            ins_statuses.append(t_st)
            ins_board.add(VGroup(rect, t_nm, t_st))

        fetch_beam = arrow_2d(ag_fetch[0].get_right(), [-1.80, 0.12, 0], color=C_CYAN, sw=2.8, tip=0.14, z=8)
        ver_beam = arrow_2d(ag_ver[0].get_right(), [-1.80, -1.10, 0], color=C_MINT, sw=2.8, tip=0.14, z=8)
        lead_ret_beam = arrow_2d([-1.80, 1.62, 0], ag_lead[0].get_right(), color=C_GOLD, sw=2.8, tip=0.14, z=8)

        wave_scan_1 = Line([-1.82, -1.85, 0], [-1.82, 2.15, 0], color=C_CYAN, stroke_width=4.2).set_z_index(10)
        wave_scan_2 = Line([-1.82, -1.85, 0], [-1.82, 2.15, 0], color=C_MINT, stroke_width=4.2).set_z_index(10)
        done_3c_pill = fit(
            pill("실행 결과 : 15개사 무인증 자동수집·해시검증 완료 · 1개사(한화손보) 수동 분리 · 문서 58종 진본 확정 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.3, z=9),
            max_w=11.85,
        ).move_to([0.0, -2.48, 0])

        self.play(
            FadeOut(beat3b_roles, shift=UP * 0.10),
            FadeIn(disp_stack, shift=RIGHT * 0.12),
            FadeIn(ins_board, lag_ratio=0.02),
            run_time=0.85,
        )
        self.remove(beat3b_roles)

        fetch_status_targets = []
        fetch_anims = []
        for idx in range(16):
            if idx in (0, 11):
                continue
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            nt = txt("문서 수령 완료", size=9.6, color=C_CYAN, bold=True, z=7).move_to([cx, cy - 0.16, 0])
            fetch_status_targets.append((idx, nt))
            fetch_anims.append(
                AnimationGroup(
                    ins_rects[idx].animate.set_stroke(C_CYAN, width=2.0).set_fill(C_CYAN_DIM, opacity=0.75),
                    ReplacementTransform(ins_statuses[idx], nt),
                )
            )

        self.add(wave_scan_1)
        self.play(
            GrowArrow(fetch_beam),
            Circumscribe(ag_fetch[0], color=C_CYAN, stroke_width=2.0, buff=0.03),
            wave_scan_1.animate.move_to([5.62, 0.15, 0]),
            LaggedStart(*fetch_anims, lag_ratio=0.04),
            run_time=1.05,
        )
        self.remove(wave_scan_1)
        for idx, nt in fetch_status_targets:
            ins_statuses[idx] = nt

        ver_anims = []
        for idx in range(16):
            if idx in (0, 11):
                continue
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            vt = txt("재호출 해시 일치 ✓", size=9.4, color=C_GOLD, bold=True, z=7).move_to([cx, cy - 0.16, 0])
            ver_anims.append(
                AnimationGroup(
                    ins_rects[idx].animate.set_stroke(C_GOLD, width=2.1).set_fill("#283124", opacity=0.95),
                    ReplacementTransform(ins_statuses[idx], vt),
                )
            )
            ins_statuses[idx] = vt

        self.add(wave_scan_2)
        self.play(
            GrowArrow(ver_beam),
            Circumscribe(ag_ver[0], color=C_MINT, stroke_width=2.0, buff=0.03),
            wave_scan_2.animate.move_to([5.62, 0.15, 0]),
            LaggedStart(*ver_anims, lag_ratio=0.04),
            run_time=1.05,
        )
        self.remove(wave_scan_2)
        self.play(
            GrowArrow(lead_ret_beam),
            Circumscribe(ag_lead[0], color=C_GOLD, stroke_width=2.2, buff=0.03),
            FadeIn(done_3c_pill, shift=UP * 0.06),
            run_time=0.70,
        )
        ver_status_grp = VGroup(*ins_statuses)
        beat3c_all = VGroup(disp_stack, ins_board, ver_status_grp, fetch_beam, ver_beam, lead_ret_beam, done_3c_pill)
        self.check_bounds(beat3c_all, "CH3C DUAL WAVE")
        self.wait(2.20)

        # -------------------------------------------------------------------
        # Beat 3D: Solution 2 - 7-Day Rotating Radar + 3-Gate Deflecting Filter
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 하루 20회 검색 한도에 맞춰 요일별로 기관을 나누고, 코드 날짜 검증으로 기간 밖 23건을 걸러냈습니다",
            rt=0.38,
        )

        rad_c = np.array([-3.38, 0.14, 0.0])
        rad_r = 1.48
        rad_rings = VGroup(
            Circle(radius=rad_r, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.6, stroke_opacity=0.70).move_to(rad_c),
            Circle(radius=0.99, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.0, stroke_opacity=0.35).move_to(rad_c),
            Circle(radius=0.52, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=2.0).move_to(rad_c),
        ).set_z_index(4)
        rad_core_t = VGroup(txt("요일별", size=11.5, color=C_GOLD, bold=True, z=8), txt("순환 수집", size=10.5, color=C_INK_1, z=8)).arrange(DOWN, buff=0.03).move_to(rad_c)

        day_specs = [
            ("월 대형 생보", C_CYAN), ("화 대형 손보", C_CYAN), ("수 주력 손보", C_CYAN),
            ("목 중견 생보", C_CYAN), ("금 우체국·손보", C_GOLD), ("토 배타적사용권", C_VIOLET), ("일 누락분 보완", C_MINT),
        ]
        day_dots, day_lbls = VGroup(), VGroup()
        for d_i, (d_nm, d_col) in enumerate(day_specs):
            ang = math.pi / 2 - d_i * (2 * math.pi / 7)
            dp = rad_c + np.array([rad_r * math.cos(ang), rad_r * math.sin(ang), 0.0])
            d_dot = Circle(radius=0.11, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=d_col, stroke_width=2.0).move_to(dp).set_z_index(7)
            day_dots.add(d_dot)
            d_lbl = txt(d_nm, size=10.3, color=d_col if d_i >= 4 else C_INK_1, bold=(d_i >= 4), z=7)
            if d_i == 0:
                d_lbl.next_to(d_dot, UP, buff=0.09)
            elif d_i in (1, 2):
                d_lbl.next_to(d_dot, RIGHT, buff=0.09)
            elif d_i in (3, 4):
                d_lbl.next_to(d_dot, DOWN, buff=0.09)
            else:
                d_lbl.next_to(d_dot, LEFT, buff=0.09)
            day_lbls.add(d_lbl)

        rad_caption = pill("일 20회 무료 한도 안에서 19개 기관 순환 점검", fg=C_CYAN, bg=C_PANEL, border=C_CYAN, size=10.8).move_to([-3.38, -2.52, 0])

        sweep_ang = ValueTracker(math.pi / 2)
        sweep_beam = always_redraw(
            lambda: VGroup(
                Sector(radius=rad_r - 0.02, start_angle=sweep_ang.get_value() - 0.48, angle=0.48, fill_color=C_CYAN, fill_opacity=0.22, stroke_width=0).shift(rad_c),
                Line(rad_c, rad_c + np.array([rad_r * math.cos(sweep_ang.get_value()), rad_r * math.sin(sweep_ang.get_value()), 0.0]), color=C_GOLD, stroke_width=2.8),
            ).set_z_index(6)
        )

        g1_x, g2_x, g3_x = 0.25, 2.10, 3.95
        sieve_gates = VGroup()
        for gx, g_col, g_top in [(g1_x, C_CYAN, "① 발행일 선기재 확인"), (g2_x, C_CORAL, "② 코드 날짜 대조 절단"), (g3_x, C_MINT, "③ 비대상 종목 제외")]:
            top_post = Line([gx, 0.55, 0], [gx, 1.38, 0], color=g_col, stroke_width=4.2).set_z_index(6)
            bot_post = Line([gx, -1.38, 0], [gx, -0.45, 0], color=g_col, stroke_width=4.2).set_z_index(6)
            slit_dash = DashedLine([gx, -0.45, 0], [gx, 0.55, 0], dash_length=0.07, color=g_col, stroke_width=1.6).set_z_index(5)
            gp = fit(pill(g_top, fg=g_col, bg=C_PANEL_HI, border=g_col, size=10.6, px=0.10, py=0.05, z=8), max_w=1.74).move_to([gx, 1.78, 0])
            sieve_gates.add(VGroup(top_post, bot_post, slit_dash, gp))

        cut_note = pill("27건 중 기간 밖 23건 차단 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.6, z=8).move_to([g2_x - 0.24, -2.02, 0])
        noise_note = txt("반려동물·운전자·단순 홍보 제외", size=10.2, color=C_INK_2, z=7).move_to([g3_x + 0.14, -1.66, 0])

        clean_pool = RoundedRectangle(corner_radius=0.08, width=1.42, height=1.98, fill_color="#182B24", fill_opacity=0.94, stroke_color=C_GOLD, stroke_width=2.2).move_to([5.40, 0.05, 0]).set_z_index(4)
        pool_lbl = VGroup(txt("유효 시장동향", size=11.5, color=C_GOLD, bold=True, z=7), txt("정본 반영 ✓", size=11.5, color=C_MINT, bold=True, z=7)).arrange(DOWN, buff=0.07).move_to(clean_pool.get_top() + DOWN * 0.44)

        self.play(
            FadeOut(beat3c_all, shift=UP * 0.10),
            FadeIn(rad_rings), FadeIn(rad_core_t),
            FadeIn(day_dots, lag_ratio=0.05), FadeIn(day_lbls), FadeIn(rad_caption, shift=UP * 0.08),
            FadeIn(sieve_gates, lag_ratio=0.10), FadeIn(VGroup(clean_pool, pool_lbl), shift=LEFT * 0.10),
            run_time=0.95,
        )
        self.remove(beat3c_all, *ins_statuses)

        self.add(sweep_beam)
        good_news_pts, bad_date_pts, bad_noise_pts = VGroup(), VGroup(), VGroup()
        sieve_anims = []
        emit_pt = rad_c + RIGHT * rad_r

        for k in range(4):
            pt = glow_dot(emit_pt, color=C_GOLD, r=0.055, z=12)
            good_news_pts.add(pt)
            sieve_anims.append(Succession(Wait(k * 0.14), MoveAlongPath(pt, Line(emit_pt + UP * ((-0.35 + k * 0.24) * 0.4), np.array([5.38, -0.58 + k * 0.20, 0])), run_time=1.25)))

        for k in range(5):
            pt_b = glow_dot(emit_pt, color=C_CORAL, r=0.052, z=11)
            bad_date_pts.add(pt_b)
            sieve_anims.append(Succession(Wait(0.06 + k * 0.11), MoveAlongPath(pt_b, CubicBezier(emit_pt, np.array([0.8, 0.35 - k * 0.18, 0]), np.array([g2_x - 0.05, -0.25, 0]), np.array([g2_x, -1.55, 0])), run_time=0.98)))

        for k in range(2):
            pt_n = glow_dot(emit_pt, color=C_AMBER, r=0.050, z=11)
            bad_noise_pts.add(pt_n)
            sieve_anims.append(Succession(Wait(0.20 + k * 0.18), MoveAlongPath(pt_n, CubicBezier(emit_pt, np.array([1.8, 0.2, 0]), np.array([g3_x - 0.05, -0.2, 0]), np.array([g3_x, -1.45, 0])), run_time=1.05)))

        self.add(good_news_pts, bad_date_pts, bad_noise_pts)
        self.play(
            sweep_ang.animate.set_value(math.pi / 2 - 2 * math.pi),
            *sieve_anims,
            FadeIn(cut_note, shift=UP * 0.08), FadeIn(noise_note),
            *[d.animate.set_fill(C_CYAN_DIM, opacity=0.95) for d in day_dots],
            run_time=1.85, rate_func=linear,
        )
        self.play(FadeOut(bad_date_pts, scale=0.3), FadeOut(bad_noise_pts, scale=0.3), Circumscribe(clean_pool, color=C_GOLD, stroke_width=2.2, buff=0.04), run_time=0.55)
        self.remove(bad_date_pts, *bad_date_pts, bad_noise_pts, *bad_noise_pts)
        sweep_beam.clear_updaters()

        ch3_stage = VGroup(rad_rings, rad_core_t, day_dots, day_lbls, rad_caption, sweep_beam, sieve_gates, cut_note, noise_note, clean_pool, pool_lbl, good_news_pts)
        self.check_bounds(ch3_stage, "CH3D RADAR SIEVE")
        self.wait(2.20)

        # ===================================================================
        # 4장 [~34s]: 추출 프로세스 — 시각적 난제 진단 보드와 원문·코드 분리 해법
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch3_stage,
            hl,
            hr,
            hb,
            4,
            "추출 프로세스 — 대용량·이미지 문서 난제를 원문 전사와 코드 계산으로 해결",
            "567쪽 한도 초과, 숫자 오독, 308쪽 조각 그림 문서, 재추출 한도 유실의 네 가지 난관을 만났습니다",
        )
        print(f"[TIMING] Ch3 end: {self.renderer.time:.2f}s")

        # -------------------------------------------------------------------
        # Beat 4A: Left Resource Gauges + Right 2x2 Visual Extraction Obstacles
        # -------------------------------------------------------------------
        res_box_4 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_4 = pill("추출 자원 · 한도", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.0, z=7).move_to([-4.38, 1.92, 0])

        rg4_1 = capacity_ring([-5.15, 0.72, 0], 0.58, 0.55, C_CYAN, "경량 추출 AI", "일 500회 무료", z=6)
        rg4_2 = capacity_ring([-3.62, 0.72, 0], 0.58, 0.16, C_CORAL, "상위 재추출", "일 20회 상한", z=6)
        res_notes_4 = fit(
            VGroup(
                pill("제미나이 구독 패널 병행", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=9.8, z=7),
                pill("표·문구 규칙 파서 자체 구현", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.8, z=7),
                txt("정형 표 + 비정형 약관 혼재 환경", size=9.6, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.04,
        ).move_to([-4.38, -1.14, 0])
        res_grp_4 = VGroup(res_box_4, res_hdr_4, rg4_1, rg4_2, res_notes_4)
        vs_arr_4 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        # Q1 (-0.10, 1.18): 567p towering bar bursting past 500/day ceiling
        q4_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 567쪽 대용량 · 일일 한도 초과")
        ceil_ln = DashedLine([-1.65, 1.26, 0], [1.45, 1.26, 0], dash_length=0.07, color=C_CORAL, stroke_width=1.8).set_z_index(7)
        ceil_lbl = txt("일 500회 상한", size=8.6, color=C_CORAL, bold=True, z=8).move_to([-1.18, 1.44, 0])
        b_1doc = Rectangle(width=0.46, height=0.62, fill_color=C_AMBER, fill_opacity=0.9, stroke_width=0).move_to([-0.22, 0.88, 0]).set_z_index(6)
        b_all = Rectangle(width=0.46, height=1.12, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([0.65, 1.13, 0]).set_z_index(6)
        q4_1_t1 = txt("1권 341회", size=8.4, color=C_AMBER, bold=True, z=7).move_to([-0.22, 0.42, 0])
        q4_1_t2 = txt("19개사 초과!", size=8.6, color=C_CORAL, bold=True, z=7).move_to([0.65, 0.42, 0])

        # Q2 (3.88, 1.18): Direct number extraction error + 22/49 stuck bar
        q4_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 숫자 직접 추출 오독 (확정 22/49줄)")
        mis_calc = VGroup(
            pill("원문 2천만·50%", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=8.4, px=0.07, py=0.03).move_to([2.85, 1.30, 0]),
            arrow_2d([3.52, 1.30, 0], [3.86, 1.30, 0], color=C_CORAL, sw=1.6, tip=0.07),
            pill("1천만·1천만 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.4, px=0.07, py=0.03).move_to([4.68, 1.30, 0]),
        ).set_z_index(7)
        prog_bg = RoundedRectangle(corner_radius=0.04, width=2.90, height=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.2).move_to([3.88, 0.78, 0]).set_z_index(6)
        prog_22 = Rectangle(width=1.30, height=0.16, fill_color=C_AMBER, fill_opacity=0.9, stroke_width=0).move_to([3.08, 0.78, 0]).set_z_index(7)
        q4_2_cap = txt("초기 확정 줄 45% 정체 (22 / 49줄)", size=9.0, color=C_AMBER, bold=True, z=7).move_to([3.88, 0.46, 0])

        # Q3 (-0.10, -1.14): 308p image mosaic tiles with OCR holes
        q4_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 미래에셋 308쪽 조각 그림 문서")
        mosaic = VGroup()
        for k in range(12):
            rr, cc = divmod(k, 6)
            is_err = k in (2, 5, 7, 10)
            mosaic.add(
                RoundedRectangle(corner_radius=0.02, width=0.34, height=0.28, fill_color=C_CORAL_DIM if is_err else C_PANEL_HI, fill_opacity=0.95, stroke_color=C_CORAL if is_err else C_VIOLET, stroke_width=1.4)
                .move_to([-1.15 + cc * 0.42, -0.92 - rr * 0.36, 0]).set_z_index(7)
            )
        q4_3_cap = txt("텍스트 분리 불가 · 자체 문자판독 210자 오류 ×", size=9.0, color=C_CORAL, bold=True, z=7).move_to([-0.10, -1.82, 0])

        # Q4 (3.88, -1.14): Partial re-run wiping 166 limit rows
        q4_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 부분 재추출 시 특약 한도 유실 버그")
        wipe_l = pill("특약 한도 166줄", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=9.0, px=0.09, py=0.04, z=7).move_to([2.90, -1.10, 0])
        wipe_arr = arrow_2d([3.68, -1.10, 0], [4.12, -1.10, 0], color=C_CORAL, sw=2.0, tip=0.09, z=7)
        wipe_r = pill("0줄 초기화 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.0, px=0.09, py=0.04, z=7).move_to([4.85, -1.10, 0])
        q4_4_cap = txt("급부만 재추출할 때 한도 증발 · 급부ID 흔들림", size=9.0, color=C_INK_1, z=7).move_to([3.88, -1.78, 0])

        self.play(
            FadeIn(VGroup(res_box_4, res_hdr_4, rg4_1[0], rg4_1[2], rg4_2[0], rg4_2[2], res_notes_4), shift=RIGHT * 0.12),
            Create(rg4_1[1]), Create(rg4_2[1]),
            GrowArrow(vs_arr_4),
            FadeIn(VGroup(q4_1, ceil_ln, ceil_lbl, q4_1_t1, q4_1_t2)),
            GrowFromEdge(b_1doc, DOWN), GrowFromEdge(b_all, DOWN),
            FadeIn(VGroup(q4_2, mis_calc, prog_bg, q4_2_cap)),
            GrowFromEdge(prog_22, LEFT),
            run_time=1.10,
        )
        self.play(
            FadeIn(q4_3),
            LaggedStart(*[FadeIn(tl, scale=0.6) for tl in mosaic], lag_ratio=0.03),
            FadeIn(q4_3_cap),
            FadeIn(VGroup(q4_4, wipe_l, wipe_r, q4_4_cap)),
            GrowArrow(wipe_arr),
            run_time=1.05,
        )
        beat4a_all = VGroup(
            res_grp_4, vs_arr_4,
            q4_1, ceil_ln, ceil_lbl, b_1doc, b_all, q4_1_t1, q4_1_t2,
            q4_2, mis_calc, prog_bg, prog_22, q4_2_cap,
            q4_3, mosaic, q4_3_cap,
            q4_4, wipe_l, wipe_arr, wipe_r, q4_4_cap,
        )
        self.check_bounds(beat4a_all, "CH4A EXTRACT DIAGNOSTIC")
        self.wait(2.65)

        # -------------------------------------------------------------------
        # Beat 4B: Solution 1 - Dual Loading Path + Verbatim AI vs Step Math
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 초기 대량 적재와 주간 운영 경로를 나누고, AI는 원문 문구만 옮기며 숫자 환산은 전량 코드가 맡습니다",
            rt=0.38,
        )

        dual_path_bar = fit(
            pill("한도 해법 : 기존 대량 약관 초기 적재는 구독 패널·규칙 파서로 처리하고, 무료 API 한도는 주간 신상품·개정분에 집중", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.1, z=9),
            max_w=11.85,
        ).move_to([0.0, 2.60, 0])

        src_tok1 = pill("진단보험금 2,000만원", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=13.2)
        src_tok2 = pill("1년 미만 50% 감액", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=13.2)
        src_tok3 = pill("90일 면책기간", fg=C_INK_0, bg=C_PANEL_HI, border=C_INK_1, size=13.2)
        src_tokens = VGroup(src_tok1, src_tok2, src_tok3).arrange(DOWN, buff=0.22).move_to([-4.25, -0.05, 0])
        src_hdr = txt("약관 원문 문구", size=12.2, color=C_INK_1, bold=True, z=7).move_to([-4.25, 1.38, 0])

        stencil_frame = RoundedRectangle(corner_radius=0.08, width=3.05, height=1.04, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0).move_to([-0.42, 1.56, 0]).set_z_index(4)
        stencil_title = txt("원문 추출 AI (요약·계산 금지)", size=12.4, color=C_CYAN, bold=True, z=6).move_to(stencil_frame.get_top() + DOWN * 0.25)
        stencil_sub = txt("확정 줄 22줄 → 39줄로 즉시 향상 ✓", size=10.6, color=C_MINT, bold=True, z=6).move_to(stencil_frame.get_bottom() + UP * 0.24)
        stencil_out = pill('"2,000만원 / 1년미만 50% / 90일"', fg=C_GOLD, bg=C_PANEL, border=C_GOLD, size=11.8).move_to([3.62, 1.56, 0])
        arr_up_in = arrow_2d(src_tok1.get_right(), stencil_frame.get_left(), color=C_CYAN, sw=2.0)
        arr_up_out = arrow_2d(stencil_frame.get_right(), stencil_out.get_left(), color=C_GOLD, sw=2.0)

        ax_origin = np.array([-1.55, -2.35, 0.0])
        x_axis = Arrow(ax_origin, ax_origin + RIGHT * 6.95, buff=0, color=C_INK_2, stroke_width=2.0, tip_length=0.14).set_z_index(4)
        y_axis = Arrow(ax_origin, ax_origin + UP * 2.38, buff=0, color=C_INK_2, stroke_width=2.0, tip_length=0.14).set_z_index(4)
        code_badge = fit(
            pill("금액·기간 환산 코드 & 정형 급부표 규칙 파서 (삼성화재 681건 AI 없이 직접 추출)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.0),
            max_w=6.60,
        ).move_to([2.05, 0.36, 0])
        arr_dn_in = arrow_2d(src_tok2.get_right(), code_badge.get_left() + LEFT * 0.06, color=C_CYAN, sw=2.0)

        y_1000, y_2000 = ax_origin[1] + 0.90, ax_origin[1] + 1.80
        x_90d, x_1yr, x_end = ax_origin[0] + 1.45, ax_origin[0] + 3.75, ax_origin[0] + 6.45
        dash_1000 = DashedLine([ax_origin[0], y_1000, 0], [x_1yr, y_1000, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.2).set_z_index(3)
        dash_2000 = DashedLine([ax_origin[0], y_2000, 0], [x_end, y_2000, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.2).set_z_index(3)
        lbl_y1 = txt("1,000만", size=11.4, color=C_CYAN, bold=True, z=6).move_to([ax_origin[0] - 0.52, y_1000, 0])
        lbl_y2 = txt("2,000만", size=11.4, color=C_GOLD, bold=True, z=6).move_to([ax_origin[0] - 0.52, y_2000, 0])
        lbl_x0 = txt("90일 면책(0원)", size=10.6, color=C_CORAL, bold=True, z=6).move_to([(ax_origin[0] + x_90d) / 2, ax_origin[1] - 0.28, 0])
        lbl_x1 = txt("1년 미만 (50% 감액)", size=10.6, color=C_CYAN, bold=True, z=6).move_to([(x_90d + x_1yr) / 2, ax_origin[1] - 0.28, 0])
        lbl_x2 = txt("1년 경과 (100% 지급)", size=10.6, color=C_GOLD, bold=True, z=6).move_to([(x_1yr + x_end) / 2, ax_origin[1] - 0.28, 0])

        area_half = Rectangle(width=x_1yr - x_90d, height=0.90, fill_color=C_CYAN, fill_opacity=0.18, stroke_width=0).move_to([(x_90d + x_1yr) / 2, ax_origin[1] + 0.45, 0]).set_z_index(2)
        area_full = Rectangle(width=x_end - x_1yr, height=1.80, fill_color=C_GOLD, fill_opacity=0.22, stroke_width=0).move_to([(x_1yr + x_end) / 2, ax_origin[1] + 0.90, 0]).set_z_index(2)
        step_curve = VMobject(color=C_GOLD, stroke_width=3.6).set_z_index(7)
        step_curve.set_points_as_corners([[ax_origin[0], ax_origin[1], 0], [x_90d, ax_origin[1], 0], [x_90d, y_1000, 0], [x_1yr, y_1000, 0], [x_1yr, y_2000, 0], [x_end, y_2000, 0]])

        self.play(
            FadeOut(beat4a_all, shift=UP * 0.10),
            FadeIn(dual_path_bar, shift=DOWN * 0.08),
            FadeIn(src_hdr),
            LaggedStart(*[FadeIn(t, shift=RIGHT * 0.12) for t in src_tokens], lag_ratio=0.08),
            FadeIn(VGroup(stencil_frame, stencil_title, stencil_sub), shift=UP * 0.10),
            GrowArrow(arr_up_in), Create(x_axis), Create(y_axis), FadeIn(code_badge), GrowArrow(arr_dn_in),
            run_time=1.05,
        )
        self.remove(beat4a_all)
        self.play(
            GrowArrow(arr_up_out), FadeIn(stencil_out, shift=RIGHT * 0.12),
            Create(dash_1000), Create(dash_2000),
            FadeIn(VGroup(lbl_y1, lbl_y2, lbl_x0, lbl_x1, lbl_x2)),
            Create(step_curve), FadeIn(area_half), FadeIn(area_full),
            run_time=1.10,
        )
        beat4b_all = VGroup(
            dual_path_bar, src_hdr, src_tokens, stencil_frame, stencil_title, stencil_sub, stencil_out, arr_up_in, arr_up_out,
            x_axis, y_axis, code_badge, dash_1000, dash_2000, lbl_y1, lbl_y2, lbl_x0, lbl_x1, lbl_x2, area_half, area_full, step_curve, arr_dn_in,
        )
        self.check_bounds(beat4b_all, "CH4B STENCIL & CODE")
        self.wait(2.40)

        # -------------------------------------------------------------------
        # Beat 4C: Solution 2 - 308p Image Dual-Model Cross-Read + Rerun Safeguard
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 그림으로 된 308쪽 요약서는 서로 다른 두 모델이 따로 읽고 대조하며, 재추출 유실 방지 장치를 더했습니다",
            rt=0.38,
        )

        rows_n, cols_n = 5, 8
        err_r, err_c = 2, 5
        cells = VGroup()
        cell_grid: list[list[RoundedRectangle]] = []
        gx0, gy0 = -3.15, 1.25
        cw, ch, gap = 0.56, 0.46, 0.11
        for r in range(rows_n):
            row_list = []
            for c in range(cols_n):
                cell = RoundedRectangle(corner_radius=0.05, width=cw, height=ch, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_SLATE, stroke_width=1.3).move_to([gx0 + c * (cw + gap), gy0 - r * (ch + gap), 0]).set_z_index(3)
                row_list.append(cell)
                cells.add(cell)
            cell_grid.append(row_list)

        emit_left = pill("1차 독립 판독 (모델 A)", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=12.0).move_to([-4.95, 0.12, 0])
        emit_top = pill("2차 교차 판독 (다른 계열 모델 B)", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=12.0).move_to([-0.80, 2.22, 0])
        wave_line_x = Line([-3.55, -1.45, 0], [-3.55, 1.62, 0], color=C_CYAN, stroke_width=4.0).set_z_index(10)
        wave_line_y = Line([-3.55, 1.62, 0], [1.95, 1.62, 0], color=C_GOLD, stroke_width=4.0).set_z_index(10)

        self.play(FadeOut(beat4b_all, shift=UP * 0.10), FadeIn(cells, lag_ratio=0.01), FadeIn(emit_left, shift=RIGHT * 0.12), FadeIn(emit_top, shift=DOWN * 0.12), run_time=0.85)
        self.remove(beat4b_all)

        self.add(wave_line_x)
        self.play(
            wave_line_x.animate.move_to([1.95, 0.08, 0]),
            LaggedStart(*[AnimationGroup(*[cell_grid[r][c].animate.set_fill(C_CYAN_DIM, opacity=0.85).set_stroke(C_CYAN, width=1.6) for r in range(rows_n)]) for c in range(cols_n)], lag_ratio=0.08),
            run_time=0.95,
        )
        self.remove(wave_line_x)

        self.add(wave_line_y)
        row_anims = []
        for r in range(rows_n):
            r_group = []
            for c in range(cols_n):
                if r == err_r and c == err_c:
                    r_group.append(cell_grid[r][c].animate.set_fill(C_CORAL, opacity=0.95).set_stroke(WHITE, width=2.8))
                else:
                    r_group.append(cell_grid[r][c].animate.set_fill("#1D332B", opacity=0.92).set_stroke(C_MINT, width=1.5))
            row_anims.append(AnimationGroup(*r_group))

        self.play(wave_line_y.animate.move_to([-0.80, -1.45, 0]), LaggedStart(*row_anims, lag_ratio=0.10), run_time=1.00)
        self.remove(wave_line_y)

        err_cell = cell_grid[err_r][err_c]
        sonar_1 = Circle(radius=0.18, fill_opacity=0.0, stroke_color=C_CORAL, stroke_width=3.0).move_to(err_cell.get_center()).set_z_index(11)
        lens_center = np.array([4.18, 0.15, 0.0])
        lens_circle = Circle(radius=1.36, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.8).move_to(lens_center).set_z_index(8)
        lens_title = fit(txt("불일치 줄 원문 확대 대조", size=12.0, color=C_GOLD, bold=True, z=9), max_w=2.15).move_to(lens_center + UP * 0.76)
        wrong_val = txt("오독: 1,000만원", size=13.0, color=C_CORAL, z=9).move_to(lens_center + UP * 0.20)
        strike_ln = Line(wrong_val.get_left() + LEFT * 0.06, wrong_val.get_right() + RIGHT * 0.06, color=C_CORAL, stroke_width=2.4).set_z_index(10)
        fixed_val = fit(txt("원문 확정: 2,000만원 ✓", size=13.5, color=C_MINT, bold=True, z=9), max_w=2.35).move_to(lens_center + DOWN * 0.28)
        safeguard_bar = fit(
            pill("이미지 요약서 308쪽(31만 자) 지급액 불일치 0건 · 결과 파일 선보존 · 재추출 시 기존 확정 줄·급부ID(1,039줄) 보호 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.1),
            max_w=11.85,
        ).move_to([0.0, -2.52, 0]).set_z_index(9)
        callout_1 = Line(err_cell.get_corner(UR), lens_circle.get_left() + UP * 0.55, color=C_GOLD, stroke_width=1.6).set_z_index(7)
        callout_2 = Line(err_cell.get_corner(DR), lens_circle.get_left() + DOWN * 0.55, color=C_GOLD, stroke_width=1.6).set_z_index(7)

        self.add(sonar_1)
        self.play(sonar_1.animate.scale(3.4).set_stroke(opacity=0.0), Create(callout_1), Create(callout_2), FadeIn(lens_circle, scale=0.85), FadeIn(lens_title), FadeIn(wrong_val), run_time=0.80)
        self.remove(sonar_1)
        self.play(Create(strike_ln), FadeIn(fixed_val, shift=UP * 0.10), err_cell.animate.set_fill(C_GOLD, opacity=0.95).set_stroke(WHITE, width=2.4), FadeIn(safeguard_bar, shift=UP * 0.10), run_time=0.85)

        ch4_stage = VGroup(cells, emit_left, emit_top, lens_circle, lens_title, wrong_val, strike_ln, fixed_val, callout_1, callout_2, safeguard_bar)
        self.check_bounds(ch4_stage, "CH4C CROSS READ & SAFEGUARD")
        self.wait(2.65)
        print(f"[TIMING] Part 2 end: {self.renderer.time:.2f}s")

        self.fade_out_part(ch4_stage, hl, hr, hb)
