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
    capacity_ring,
    fit,
    glow_dot,
    pill,
    txt,
)


class Part2CollectExtractScene(PostLifeBaseScene):
    def construct(self) -> None:
        self.init_cinema_canvas()

        # ===================================================================
        # 3장 [~50s]: 수집 단계 — 무료 한도 안에서 19개사 약관과 최신 뉴스만 정확히 모으는 법
        # ===================================================================
        hl, hr, hb = self.make_hud(
            3,
            "수집 단계 — 무료 한도 안에서 19개 보험사 약관과 최신 뉴스를 모으는 법",
            "비용 0원 환경에서 AI 한도 부족, 홈페이지 접속 거부, 철 지난 옛날 뉴스 섞임이라는 네 가지 문제를 만났습니다",
        )

        # -------------------------------------------------------------------
        # Beat 3A: Easy Step-by-Step Tour of the 4 Collection Obstacles
        # -------------------------------------------------------------------
        res_box_3 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_3 = pill("주어진 무료 환경 조건", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, z=7).move_to([-4.38, 1.92, 0])
        rg_1 = capacity_ring([-5.15, 0.72, 0], 0.58, 0.84, C_AMBER, "최고급 AI", "사용 횟수 빠듯", z=6)
        rg_2 = capacity_ring([-3.62, 0.72, 0], 0.58, 0.20, C_CYAN, "무료 검색", "하루 20번 제한", z=6)
        res_bars_3 = fit(
            VGroup(
                pill("무료 자동 실행 (월 2,000분)", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.8, z=7),
                pill("유료 수집 프로그램 예산 0원", fg=C_INK_1, bg=C_BG_SUB, border=C_SLATE, size=9.8, z=7),
                txt("혼자서 19개 보험사를 매주 점검", size=9.6, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.04,
        ).move_to([-4.38, -1.14, 0])
        res_grp_3 = VGroup(res_box_3, res_hdr_3, rg_1, rg_2, res_bars_3)
        vs_arr_3 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        def diag_frame(cx: float, cy: float, col: str, title_s: str) -> VGroup:
            bx = RoundedRectangle(corner_radius=0.08, width=3.74, height=2.12, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=col, stroke_width=1.9).move_to([cx, cy, 0]).set_z_index(4)
            th = fit(txt(title_s, size=10.6, color=col, bold=True, z=7), max_w=3.46).move_to([cx, cy + 0.76, 0])
            return VGroup(bx, th)

        q3_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 비싼 AI만 쓰다 사용량 바닥")
        bat_bg = RoundedRectangle(corner_radius=0.04, width=2.10, height=0.34, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.5).move_to([-0.68, 1.14, 0]).set_z_index(6)
        bat_full = Rectangle(width=1.96, height=0.22, fill_color=C_GOLD, fill_opacity=0.9, stroke_width=0).move_to([-0.68, 1.14, 0]).set_z_index(7)
        bat_low = Rectangle(width=0.28, height=0.22, fill_color=C_CORAL, fill_opacity=0.95, stroke_width=0).move_to([-1.52, 1.14, 0]).set_z_index(7)
        q3_1_chip = pill("말로만 완료?", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.8, px=0.08, py=0.03, z=7).move_to([1.02, 1.14, 0])
        q3_1_cap = txt("단순 작업에도 최고급 AI가 자동 소모됨", size=9.2, color=C_INK_1, z=7).move_to([-0.10, 0.50, 0])

        q3_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② 홈페이지마다 다르고 접속 거부")
        sk1 = RegularPolygon(n=3, fill_color=C_CYAN_DIM, fill_opacity=0.9, stroke_color=C_CYAN, stroke_width=1.5).scale(0.18).move_to([2.48, 1.24, 0]).set_z_index(6)
        sk2 = RegularPolygon(n=6, fill_color=C_PANEL_HI, fill_opacity=0.9, stroke_color=C_GOLD, stroke_width=1.5).scale(0.18).move_to([2.95, 1.24, 0]).set_z_index(6)
        sk3 = Square(side_length=0.28, fill_color=C_PANEL_HI, fill_opacity=0.9, stroke_color=C_VIOLET, stroke_width=1.5).move_to([3.42, 1.24, 0]).set_z_index(6)
        blk_arr = arrow_2d([3.68, 1.24, 0], [4.38, 1.24, 0], color=C_CORAL, sw=2.2, tip=0.10, z=7)
        blk_wall = Rectangle(width=0.16, height=0.68, fill_color=C_CORAL, fill_opacity=0.98, stroke_color=WHITE, stroke_width=1.0).move_to([4.50, 1.24, 0]).set_z_index(8)
        blk_tag = pill("접속 거부 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=8.8, px=0.07, py=0.03, z=8).move_to([5.16, 1.24, 0])
        q3_2_cap = txt("19곳 구조가 다 다르고 한화손보는 차단됨", size=9.2, color=C_INK_1, z=7).move_to([3.88, 0.50, 0])

        q3_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 검색 오류 · 포털 뉴스 저장 금지")
        m_fail1 = pill("검색AI A : 연결 끊김 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.6, px=0.08, py=0.04, z=7).move_to([-1.02, -0.96, 0])
        m_fail2 = pill("검색AI B : 출처 없음 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.6, px=0.08, py=0.04, z=7).move_to([-1.02, -1.42, 0])
        lock_body = RoundedRectangle(corner_radius=0.04, width=0.44, height=0.36, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=C_VIOLET, stroke_width=1.8).move_to([0.96, -1.24, 0]).set_z_index(7)
        lock_shackle = Arc(radius=0.14, start_angle=0, angle=PI, color=C_VIOLET, stroke_width=2.0).move_to([0.96, -0.98, 0]).set_z_index(7)
        lock_lbl = txt("포털 뉴스 보관 제한", size=8.8, color=C_VIOLET, bold=True, z=7).move_to([0.96, -1.62, 0])

        q3_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 철 지난 옛날 기사가 섞여 들어옴")
        dots_27_cyan, dots_27_final = VGroup(), VGroup()
        for k in range(27):
            rr, cc = divmod(k, 9)
            pt_d = [2.60 + cc * 0.32, -0.82 - rr * 0.28, 0]
            is_valid = k >= 23
            dots_27_cyan.add(Circle(radius=0.085, fill_color=C_CYAN, fill_opacity=0.85, stroke_color=C_CYAN, stroke_width=1.0).move_to(pt_d).set_z_index(7))
            dcol = C_GOLD if is_valid else C_CORAL
            dots_27_final.add(Circle(radius=0.085, fill_color=dcol, fill_opacity=0.95, stroke_color=WHITE if is_valid else dcol, stroke_width=1.2).move_to(pt_d).set_z_index(7))
        q3_4_cap = txt("찾아온 27건 중 23건이 기간 지난 옛날 기사!", size=9.0, color=C_CORAL, bold=True, z=7).move_to([3.88, -1.84, 0])

        self.show_initial_hud(
            hl,
            hr,
            hb,
            extra_anims=[
                FadeIn(VGroup(res_box_3, res_hdr_3, rg_1[0], rg_1[2], rg_2[0], rg_2[2], res_bars_3), shift=RIGHT * 0.12),
                Create(rg_1[1]),
                Create(rg_2[1]),
                GrowArrow(vs_arr_3),
                FadeIn(VGroup(q3_1, bat_bg, bat_full, q3_1_chip, q3_1_cap)),
                FadeIn(VGroup(q3_2, sk1, sk2, sk3, blk_wall, blk_tag, q3_2_cap)),
                FadeIn(VGroup(q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_lbl)),
                FadeIn(VGroup(q3_4, dots_27_cyan)),
            ],
            rt=1.20,
        )

        # Calm close-up 1: Battery drain & blocked download wall
        pkt_hit = glow_dot([3.58, 1.24, 0], color=C_CYAN, r=0.06, z=12)
        self.add(pkt_hit)
        self.cam_move(
            zoom=1.38,
            center=[1.90, 1.18, 0],
            anims=[
                ReplacementTransform(bat_full, bat_low),
                GrowArrow(blk_arr),
                MoveAlongPath(pkt_hit, CubicBezier([3.58, 1.24, 0], [4.42, 1.24, 0], [4.42, 1.24, 0], [3.85, 1.62, 0])),
                Flash([4.45, 1.24, 0], color=C_CORAL, line_length=0.22, num_lines=8),
            ],
            rt=1.20,
        )
        self.remove(pkt_hit)
        self.wait(0.60)

        # Calm close-up 2: Old news cutoff blade turning 23 of 27 dots red
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
            rt=1.20,
        )
        self.remove(date_blade)
        self.wait(0.75)
        self.reset_cam_2d(rt=0.90)

        beat3a_all = VGroup(
            res_grp_3, vs_arr_3,
            q3_1, bat_bg, bat_low, q3_1_chip, q3_1_cap,
            q3_2, sk1, sk2, sk3, blk_arr, blk_wall, blk_tag, q3_2_cap,
            q3_3, m_fail1, m_fail2, lock_body, lock_shackle, lock_lbl,
            q3_4, dots_27_final, q3_4_cap,
        )
        self.check_bounds(beat3a_all, "CH3A RESOURCE & OBSTACLES")
        self.wait(1.40)

        # -------------------------------------------------------------------
        # Beat 3B: Easy 4-Step Team Division (Scout -> Sample Mold -> 16 Workers -> Double-Download Check)
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① 사람 팀처럼 '조사 → 본보기 제작 → 16곳 동시 다운로드 → 다시 받아 원본 대조'로 역할을 나눴습니다",
            rt=0.40,
        )

        role_banner = fit(
            pill("해결책 ① 4단계 역할 분담 : 작업 난이도에 맞는 AI를 따로 지정해 한도를 아끼고, 다운로드 담당과 검사 담당을 분리", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.8, z=9),
            max_w=11.85,
        ).move_to([0.0, 2.58, 0])

        s1_c = np.array([-4.55, 0.25, 0.0])
        s1_hdr = pill("① 사전 조사 담당", fg=C_VIOLET, bg=C_PANEL_HI, border=C_VIOLET, size=10.8, z=8).move_to([-4.55, 1.82, 0])
        s1_dome = Circle(radius=1.08, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_VIOLET, stroke_width=2.2).move_to(s1_c).set_z_index(4)
        s1_inner = Circle(radius=0.62, fill_opacity=0.0, stroke_color=C_SLATE, stroke_width=1.1).move_to(s1_c).set_z_index(5)
        s1_arm = Line(s1_c, s1_c + UP * 1.04, color=C_GOLD, stroke_width=2.8).set_z_index(8)
        s1_beacons = VGroup(
            *[Dot(s1_c + np.array([0.86 * math.cos(k * TAU / 19), 0.86 * math.sin(k * TAU / 19), 0.0]), radius=0.052, color=C_CYAN if k < 10 else C_GOLD).set_z_index(7) for k in range(19)]
        )
        s1_cap = fit(txt("생보 10곳 · 손보 9곳 대표상품 찾기", size=9.5, color=C_INK_1, bold=True, z=7), max_w=2.55).move_to([-4.55, -1.16, 0])
        st1_grp = VGroup(s1_hdr, s1_dome, s1_inner, s1_arm, s1_beacons, s1_cap)

        s2_hdr = pill("② 총괄 설계 담당", fg=C_GOLD, bg="#383016", border=C_GOLD, size=10.8, z=8).move_to([-1.55, 1.82, 0])
        s2_mold = RegularPolygon(n=6, fill_color="#2A2312", fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.4).scale(0.62).move_to([-2.12, 0.25, 0]).set_z_index(6)
        s2_mold_t = fit(VGroup(txt("DB손보", size=10.0, color=C_GOLD, bold=True, z=8), txt("모범 본보기", size=9.2, color=WHITE, bold=True, z=8)).arrange(DOWN, buff=0.03), max_w=0.98).move_to(s2_mold)
        s2_prism = RegularPolygon(n=3, fill_color=C_CYAN_DIM, fill_opacity=0.85, stroke_color=C_CYAN, stroke_width=2.0).scale(0.46).rotate(-PI / 6).move_to([-1.08, 0.25, 0]).set_z_index(6)
        s2_rays = VGroup(*[Line([-0.82, 0.25, 0], [-0.28, -0.52 + k * 0.22, 0], color=C_GOLD if k % 2 == 0 else C_CYAN, stroke_width=1.8).set_z_index(5) for k in range(8)])
        s2_cap = fit(txt("본보기 1개를 완성해 16곳에 배분", size=9.5, color=C_INK_1, bold=True, z=7), max_w=2.55).move_to([-1.55, -1.16, 0])
        st2_grp = VGroup(s2_hdr, s2_mold, s2_mold_t, s2_prism, s2_rays, s2_cap)

        s3_hdr = pill("③ 다운로드 담당 ×16", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, z=8).move_to([1.55, 1.82, 0])
        s3_tag = pill("빠른 작업용 AI 지정", fg=C_CYAN, bg=C_BG_SUB, border=C_CYAN, size=8.8, px=0.08, py=0.03, z=8).move_to([1.55, 1.28, 0])
        s3_lanes = VGroup()
        for k in range(8):
            ly = 0.86 - k * 0.21
            ln_c = C_CORAL if k == 6 else C_CYAN
            s3_lanes.add(VGroup(Line([0.52, ly, 0], [2.42, ly, 0], color=ln_c, stroke_width=2.2, stroke_opacity=0.85), Dot([2.46, ly, 0], radius=0.048, color=ln_c)).set_z_index(6))
        s3_cap = fit(txt("15곳 자동 수집 · 차단 1곳 직접 반입", size=9.5, color=C_INK_1, bold=True, z=7), max_w=2.60).move_to([1.55, -1.16, 0])
        st3_grp = VGroup(s3_hdr, s3_tag, s3_lanes, s3_cap)

        s4_hdr = pill("④ 원본 검사 담당 ×16", fg=C_MINT, bg="#16382C", border=C_MINT, size=10.8, z=8).move_to([4.55, 1.82, 0])
        s4_tag = pill("가벼운 검사 전용 AI", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=8.8, px=0.08, py=0.03, z=8).move_to([4.55, 1.28, 0])
        pdf_a = VGroup(
            RoundedRectangle(corner_radius=0.05, width=0.96, height=0.58, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_CYAN, stroke_width=2.0),
            txt("받아온\n약관", size=8.6, color=C_CYAN, bold=True),
        ).move_to([3.80, 0.42, 0]).set_z_index(7)
        pdf_b = VGroup(
            RoundedRectangle(corner_radius=0.05, width=0.96, height=0.58, fill_color=C_PANEL_HI, fill_opacity=0.98, stroke_color=C_GOLD, stroke_width=2.0),
            txt("새로 받은\n약관", size=8.6, color=C_GOLD, bold=True),
        ).move_to([5.30, 0.42, 0]).set_z_index(7)
        hash_seal = VGroup(
            RegularPolygon(n=6, fill_color="#16382C", fill_opacity=1.0, stroke_color=C_MINT, stroke_width=2.4).scale(0.40),
            txt("원본 일치\n100% ✓", size=8.4, color=C_MINT, bold=True),
        ).move_to([4.55, -0.34, 0]).set_z_index(9)
        s4_cap = fit(txt("한 번 더 내려받아 똑같은지 직접 확인", size=9.5, color=C_INK_1, bold=True, z=7), max_w=2.65).move_to([4.55, -1.16, 0])
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
            pill("총괄 최종 확인 완료 : 약관·요약서 58개 파일 모두 진짜 원본이며 쪽수까지 정상임을 검증 ✓", fg=C_DARK_INK, bg=C_GOLD, border=WHITE, size=10.2, z=8),
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
            rt=1.35,
        )
        self.remove(beat3a_all)
        self.wait(0.75)

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
            rt=1.35,
        )
        self.play(
            pdf_a.animate.shift(RIGHT * 0.22 + DOWN * 0.18),
            pdf_b.animate.shift(LEFT * 0.22 + DOWN * 0.18),
            FadeIn(hash_seal, scale=1.35),
            Flash([4.55, -0.34, 0], color=C_MINT, line_length=0.25, num_lines=10),
            run_time=0.75,
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
            rt=1.05,
        )
        self.remove(ret_pulse)

        beat3b_roles = VGroup(role_banner, st1_grp, st2_grp, st3_grp, st4_grp, relay_links, ret_path, ret_tip, ret_lbl)
        self.check_bounds(beat3b_roles, "CH3B AGENT ROLES")
        self.wait(1.85)

        # -------------------------------------------------------------------
        # Beat 3C: 3D 16-Insurer Terrain + Two Verification Waves
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "16개 보험사 약관을 먼저 내려받은 뒤(파란 물결), 검사 담당이 한 번 더 내려받아 확인합니다(초록 물결)",
            rt=0.38,
        )

        def mini_disp_box(lbl: str, sub: str, col: str, y_pos: float) -> VGroup:
            b = RoundedRectangle(corner_radius=0.07, width=2.48, height=1.02, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=col, stroke_width=2.0).move_to([-4.62, y_pos, 0]).set_z_index(6)
            tg = fit(VGroup(txt(lbl, size=11.6, color=col, bold=True, z=8), txt(sub, size=9.6, color=C_INK_1, z=8)).arrange(DOWN, buff=0.05), max_w=2.24).move_to(b)
            return VGroup(b, tg)

        ag_lead = mini_disp_box("② 총괄 설계 담당", "본보기 배포 · 최종 승인", C_GOLD, 1.62)
        ag_fetch = mini_disp_box("③ 다운로드 담당 ×16", "16개 보험사 약관 수집", C_CYAN, 0.12)
        ag_ver = mini_disp_box("④ 원본 검사 담당 ×16", "다시 내려받아 똑같은지 비교", C_MINT, -1.38)
        disp_stack = VGroup(
            ag_lead, ag_fetch, ag_ver,
            arrow_2d(ag_lead[0].get_bottom(), ag_fetch[0].get_top(), color=C_GOLD, sw=1.8, tip=0.09, z=7),
            arrow_2d(ag_fetch[0].get_bottom(), ag_ver[0].get_top(), color=C_CYAN, sw=1.8, tip=0.09, z=7),
        )

        org_names = [
            "DB손보", "삼성화재", "한화생명", "삼성생명",
            "교보생명", "신한라이프", "KB손보", "현대해상",
            "메리츠", "NH생명", "NH손보", "한화손보",
            "동양생명", "흥국생명", "롯데손보", "미래에셋",
        ]
        board_x = [-0.95, 0.90, 2.75, 4.60]
        board_y = [1.68, 0.68, -0.32, -1.32]
        ins_rects: list[RoundedRectangle] = []
        ins_statuses: list[Text] = []
        ins_prisms: list[Prism] = []
        ins_board = VGroup()
        prisms_grp = VGroup()

        for idx, nm in enumerate(org_names):
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            is_pilot = nm == "DB손보"
            is_blocked = nm == "한화손보"
            init_col = C_GOLD if is_pilot else (C_CORAL if is_blocked else C_SLATE)
            init_fill = "#283124" if is_pilot else (C_CORAL_DIM if is_blocked else C_PANEL)
            rect = RoundedRectangle(corner_radius=0.06, width=1.68, height=0.78, fill_color=init_fill, fill_opacity=0.95, stroke_color=init_col, stroke_width=2.0 if (is_pilot or is_blocked) else 1.4).move_to([cx, cy, 0]).set_z_index(5)
            t_nm = txt(nm, size=11.4, color=WHITE if not is_blocked else C_CORAL, bold=True, z=7).move_to([cx, cy + 0.14, 0])
            t_st = txt("모범 본보기 ✓" if is_pilot else ("차단 → 직접반입" if is_blocked else "수집 대기"), size=9.6, color=C_GOLD if is_pilot else (C_CORAL if is_blocked else C_INK_2), bold=(is_pilot or is_blocked), z=7).move_to([cx, cy - 0.16, 0])
            ins_rects.append(rect)
            ins_statuses.append(t_st)
            ins_board.add(VGroup(rect, t_nm, t_st))

            zh = 0.72 if is_pilot else (0.18 if is_blocked else 0.12)
            pr = Prism(dimensions=[1.52, 0.64, zh], fill_color=init_col, fill_opacity=0.22, stroke_color=init_col, stroke_width=1.0).move_to([cx, cy, zh / 2])
            ins_prisms.append(pr)
            prisms_grp.add(pr)

        fetch_beam = arrow_2d(ag_fetch[0].get_right(), [-1.80, 0.12, 0], color=C_CYAN, sw=2.8, tip=0.14, z=8)
        ver_beam = arrow_2d(ag_ver[0].get_right(), [-1.80, -1.10, 0], color=C_MINT, sw=2.8, tip=0.14, z=8)
        lead_ret_beam = arrow_2d([-1.80, 1.62, 0], ag_lead[0].get_right(), color=C_GOLD, sw=2.8, tip=0.14, z=8)

        curtain_1 = Prism(dimensions=[0.08, 4.10, 1.15], fill_color=C_CYAN, fill_opacity=0.35, stroke_color=C_CYAN, stroke_width=1.8).move_to([-1.82, 0.18, 0.58])
        curtain_2 = Prism(dimensions=[0.08, 4.10, 1.35], fill_color=C_MINT, fill_opacity=0.35, stroke_color=C_MINT, stroke_width=1.8).move_to([-1.82, 0.18, 0.68])
        done_3c_pill = fit(pill("결과 : 15개 보험사 자동 다운로드·원본 대조 완료 · 접속 거부 1곳(한화손보) 직접 반입 · 약관 58종 확보 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=11.0, z=9), max_w=11.85).move_to([0.0, -2.48, 0])

        self.cam_move(
            phi=50 * DEGREES,
            theta=-56 * DEGREES,
            zoom=0.94,
            center=[0.35, 0.0, 0.15],
            anims=[FadeOut(beat3b_roles, shift=UP * 0.10), FadeIn(disp_stack), FadeIn(ins_board), FadeIn(prisms_grp)],
            rt=1.15,
        )
        self.remove(beat3b_roles)

        fetch_status_targets = []
        fetch_anims = []
        for idx in range(16):
            if idx in (0, 11):
                continue
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            nt = txt("다운로드 완료", size=9.6, color=C_CYAN, bold=True, z=7).move_to([cx, cy - 0.16, 0])
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
            rt=1.25,
        )
        self.remove(curtain_1)
        for idx, nt in fetch_status_targets:
            ins_statuses[idx] = nt

        ver_anims = []
        for idx in range(16):
            if idx in (0, 11):
                continue
            r_i, c_i = divmod(idx, 4)
            cx, cy = board_x[c_i], board_y[r_i]
            vt = txt("원본 일치 확인 ✓", size=9.4, color=C_GOLD, bold=True, z=7).move_to([cx, cy - 0.16, 0])
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
            rt=1.20,
        )
        self.remove(curtain_2)
        self.reset_cam_2d(
            anims=[FadeOut(prisms_grp), GrowArrow(lead_ret_beam), Circumscribe(ag_lead[0], color=C_GOLD, stroke_width=2.2, buff=0.03), FadeIn(done_3c_pill, shift=UP * 0.06)],
            rt=0.90,
        )
        self.remove(prisms_grp, *ins_prisms)

        ver_status_grp = VGroup(*ins_statuses)
        beat3c_all = VGroup(disp_stack, ins_board, ver_status_grp, fetch_beam, ver_beam, lead_ret_beam, done_3c_pill)
        self.check_bounds(beat3c_all, "CH3C DUAL WAVE")
        self.wait(1.75)

        # -------------------------------------------------------------------
        # Beat 3D: 7-Day Rotating Schedule + 3-Step News Sieve
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 하루 20번 무료 검색에 맞춰 요일별로 회사를 나눠 찾고, 3단 거름망으로 옛날 기사를 걸러냅니다",
            rt=0.40,
        )

        rad_c = np.array([-3.38, 0.14, 0.0])
        rad_r = 1.48
        rad_rings = VGroup(
            Circle(radius=rad_r, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.6, stroke_opacity=0.70).move_to(rad_c),
            Circle(radius=0.99, fill_opacity=0.0, stroke_color=C_CYAN, stroke_width=1.0, stroke_opacity=0.35).move_to(rad_c),
            Circle(radius=0.52, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_GOLD, stroke_width=2.0).move_to(rad_c),
        ).set_z_index(4)
        rad_core_t = VGroup(txt("요일별", size=11.5, color=C_GOLD, bold=True, z=8), txt("나눠 찾기", size=10.5, color=C_INK_1, z=8)).arrange(DOWN, buff=0.03).move_to(rad_c)

        day_specs = [("월 대형 생보", C_CYAN), ("화 대형 손보", C_CYAN), ("수 주력 손보", C_CYAN), ("목 중견 생보", C_CYAN), ("금 우체국·손보", C_GOLD), ("토 독점신담보", C_VIOLET), ("일 빠진곳 보완", C_MINT)]
        day_dots, day_lbls = VGroup(), VGroup()
        for d_i, (d_nm, d_col) in enumerate(day_specs):
            ang = math.pi / 2 - d_i * (2 * math.pi / 7)
            dp = rad_c + np.array([rad_r * math.cos(ang), rad_r * math.sin(ang), 0.0])
            d_dot = Circle(radius=0.11, fill_color=C_PANEL_HI, fill_opacity=1.0, stroke_color=d_col, stroke_width=2.0).move_to(dp).set_z_index(7)
            day_dots.add(d_dot)
            d_lbl = txt(d_nm, size=10.2, color=d_col if d_i >= 4 else C_INK_1, bold=(d_i >= 4), z=7)
            d_lbl.next_to(d_dot, UP if d_i == 0 else (RIGHT if d_i in (1, 2) else (DOWN if d_i in (3, 4) else LEFT)), buff=0.09)
            day_lbls.add(d_lbl)
        rad_caption = pill("하루 20번 무료 검색 안에서 19개사 골고루 점검", fg=C_CYAN, bg=C_PANEL, border=C_CYAN, size=10.6).move_to([-3.38, -2.52, 0])

        sweep_ang = ValueTracker(math.pi / 2)
        sweep_beam = always_redraw(
            lambda: VGroup(
                Sector(radius=rad_r - 0.02, start_angle=sweep_ang.get_value() - 0.48, angle=0.48, fill_color=C_CYAN, fill_opacity=0.22, stroke_width=0).shift(rad_c),
                Line(rad_c, rad_c + np.array([rad_r * math.cos(sweep_ang.get_value()), rad_r * math.sin(sweep_ang.get_value()), 0.0]), color=C_GOLD, stroke_width=2.8),
            ).set_z_index(6)
        )

        g1_x, g2_x, g3_x = 0.25, 2.10, 3.95
        sieve_gates = VGroup()
        for gx, g_col, g_top in [(g1_x, C_CYAN, "① 기사 날짜 확인"), (g2_x, C_CORAL, "② 옛날 기사 자동 탈락"), (g3_x, C_MINT, "③ 무관한 보험 제외")]:
            sieve_gates.add(
                VGroup(
                    Line([gx, 0.55, 0], [gx, 1.38, 0], color=g_col, stroke_width=4.2).set_z_index(6),
                    Line([gx, -1.38, 0], [gx, -0.45, 0], color=g_col, stroke_width=4.2).set_z_index(6),
                    DashedLine([gx, -0.45, 0], [gx, 0.55, 0], dash_length=0.07, color=g_col, stroke_width=1.6).set_z_index(5),
                    fit(pill(g_top, fg=g_col, bg=C_PANEL_HI, border=g_col, size=10.4, px=0.10, py=0.05, z=8), max_w=1.76).move_to([gx, 1.78, 0]),
                )
            )
        cut_note = pill("기간 지난 옛날 기사 23건 탈락 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=10.4, z=8).move_to([g2_x - 0.20, -2.02, 0])
        noise_note = txt("펫보험·운전자·단순 홍보 제외", size=10.0, color=C_INK_2, z=7).move_to([g3_x + 0.14, -1.66, 0])
        clean_pool = RoundedRectangle(corner_radius=0.08, width=1.46, height=1.98, fill_color="#182B24", fill_opacity=0.94, stroke_color=C_GOLD, stroke_width=2.2).move_to([5.40, 0.05, 0]).set_z_index(4)
        pool_lbl = VGroup(txt("진짜 최신 소식", size=11.2, color=C_GOLD, bold=True, z=7), txt("기준표 저장 ✓", size=11.0, color=C_MINT, bold=True, z=7)).arrange(DOWN, buff=0.07).move_to(clean_pool.get_top() + DOWN * 0.44)

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
        for k in range(4):
            pt = glow_dot(emit_pt, color=C_GOLD, r=0.055, z=12)
            good_news_pts.add(pt)
            sieve_anims.append(Succession(Wait(k * 0.14), MoveAlongPath(pt, Line(emit_pt + UP * ((-0.35 + k * 0.24) * 0.4), np.array([5.38, -0.58 + k * 0.20, 0])), run_time=1.35)))
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
            rt=1.90,
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
        self.wait(1.85)

        # ===================================================================
        # 4장 [~46s]: 추출 단계 — AI는 '받아쓰기'만, 금액 계산은 '컴퓨터 공식'으로 분리!
        # ===================================================================
        hl, hr, hb = self.switch_hud(
            ch3_stage,
            hl,
            hr,
            hb,
            4,
            "추출 단계 — AI 실수 없이 수백 쪽 약관과 그림 문서를 정확히 읽어내는 법",
            "두꺼운 약관 한도 초과, AI의 암산 실수, 글자가 안 긁히는 그림 문서, 기존 데이터 증발 문제를 해결했습니다",
        )
        print(f"[TIMING] Ch3 end: {self.renderer.time:.2f}s")

        res_box_4 = RoundedRectangle(corner_radius=0.09, width=3.36, height=4.68, fill_color=C_PANEL, fill_opacity=0.95, stroke_color=C_CYAN, stroke_width=2.0).move_to([-4.38, 0.02, 0]).set_z_index(4)
        res_hdr_4 = pill("주어진 읽기 도구 조건", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8, z=7).move_to([-4.38, 1.92, 0])
        rg4_1 = capacity_ring([-5.15, 0.72, 0], 0.58, 0.55, C_CYAN, "기본 읽기 AI", "하루 500번 무료", z=6)
        rg4_2 = capacity_ring([-3.62, 0.72, 0], 0.58, 0.16, C_CORAL, "고급 재확인", "하루 20번 제한", z=6)
        res_notes_4 = fit(
            VGroup(
                pill("정해진 표 읽기 프로그램 자체 제작", fg=C_MINT, bg=C_BG_SUB, border=C_MINT, size=9.6, z=7),
                pill("구독형 AI 채팅창 보조 활용", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=9.6, z=7),
                txt("일반 표 문서와 그림 문서가 섞여 있음", size=9.4, color=C_INK_2, z=7),
            ).arrange(DOWN, buff=0.14),
            max_w=3.04,
        ).move_to([-4.38, -1.14, 0])
        res_grp_4 = VGroup(res_box_4, res_hdr_4, rg4_1, rg4_2, res_notes_4)
        vs_arr_4 = arrow_2d([-2.62, 0.02, 0], [-2.06, 0.02, 0], color=C_CORAL, sw=2.6, tip=0.12, z=8)

        q4_1 = diag_frame(-0.10, 1.18, C_AMBER, "문제 ① 567쪽 약관 → 하루 무료 횟수 초과")
        ceil_ln = DashedLine([-1.65, 1.26, 0], [1.45, 1.26, 0], dash_length=0.07, color=C_CORAL, stroke_width=1.8).set_z_index(7)
        ceil_lbl = txt("하루 500번 한도", size=8.6, color=C_CORAL, bold=True, z=8).move_to([-1.12, 1.44, 0])
        b_1doc = Rectangle(width=0.46, height=0.62, fill_color=C_AMBER, fill_opacity=0.9, stroke_width=0).move_to([-0.22, 0.88, 0]).set_z_index(6)
        b_all = Rectangle(width=0.46, height=1.18, fill_color=C_CORAL, fill_opacity=0.95, stroke_color=WHITE, stroke_width=1.0).move_to([0.65, 1.16, 0]).set_z_index(6)
        q4_1_t1 = txt("1권에 341번", size=8.4, color=C_AMBER, bold=True, z=7).move_to([-0.22, 0.42, 0])
        q4_1_t2 = txt("19곳은 초과!", size=8.6, color=C_CORAL, bold=True, z=7).move_to([0.65, 0.42, 0])

        q4_2 = diag_frame(3.88, 1.18, C_CORAL, "문제 ② AI가 암산하다 금액을 틀림")
        mis_calc = VGroup(
            pill("약관: 2천만의 50%", fg=C_GOLD, bg=C_BG_SUB, border=C_GOLD_DEEP, size=8.4, px=0.07, py=0.03).move_to([2.85, 1.30, 0]),
            arrow_2d([3.56, 1.30, 0], [3.88, 1.30, 0], color=C_CORAL, sw=1.6, tip=0.07),
            pill("엉뚱한 금액 ×", fg=C_CORAL, bg=C_CORAL_DIM, border=C_CORAL, size=8.4, px=0.07, py=0.03).move_to([4.68, 1.30, 0]),
        ).set_z_index(7)
        prog_bg = RoundedRectangle(corner_radius=0.04, width=2.90, height=0.22, fill_color=C_BG_SUB, fill_opacity=1.0, stroke_color=C_SLATE, stroke_width=1.2).move_to([3.88, 0.78, 0]).set_z_index(6)
        prog_22 = Rectangle(width=1.30, height=0.16, fill_color=C_AMBER, fill_opacity=0.9, stroke_width=0).move_to([3.08, 0.78, 0]).set_z_index(7)
        q4_2_cap = txt("49줄 중 22줄만 통과하고 절반 넘게 멈춤", size=9.0, color=C_AMBER, bold=True, z=7).move_to([3.88, 0.46, 0])

        q4_3 = diag_frame(-0.10, -1.14, C_VIOLET, "문제 ③ 308쪽 전체가 '조각난 그림 파일'")
        mosaic_compact, mosaic = VGroup(), VGroup()
        for k in range(12):
            rr, cc = divmod(k, 6)
            is_bad = k in (2, 5, 7, 10)
            c0 = RoundedRectangle(corner_radius=0.01, width=0.30, height=0.26, fill_color=C_PANEL_HI, fill_opacity=0.95, stroke_color=C_VIOLET, stroke_width=1.0).move_to([-0.85 + cc * 0.31, -0.98 - rr * 0.27, 0]).set_z_index(7)
            c1 = RoundedRectangle(corner_radius=0.02, width=0.34, height=0.28, fill_color=C_CORAL_DIM if is_bad else C_PANEL_HI, fill_opacity=0.95, stroke_color=C_CORAL if is_bad else C_VIOLET, stroke_width=1.5).move_to([-1.15 + cc * 0.42, -0.90 - rr * 0.38, 0]).set_z_index(7)
            mosaic_compact.add(c0)
            mosaic.add(c1)
        q4_3_cap = txt("글자가 안 긁히고 일반 판독기는 210글자 오타 ×", size=8.8, color=C_CORAL, bold=True, z=7).move_to([-0.10, -1.82, 0])

        q4_4 = diag_frame(3.88, -1.14, C_CORAL, "문제 ④ 일부만 다시 읽히면 기존 표가 지워짐")
        lim_bars_before = VGroup(
            *[Rectangle(width=0.92, height=0.11, fill_color=C_CYAN, fill_opacity=0.92, stroke_width=0).move_to([2.88, -0.82 - k * 0.17, 0]).set_z_index(7) for k in range(4)]
        )
        wipe_l_lbl = txt("기존 한도 166줄", size=8.4, color=C_CYAN, bold=True, z=7).move_to([2.88, -1.52, 0])
        wipe_arr = arrow_2d([3.52, -1.08, 0], [4.08, -1.08, 0], color=C_CORAL, sw=2.2, tip=0.09, z=7)
        wipe_r = pill("0줄로 증발 ×", fg=WHITE, bg=C_CORAL, border=WHITE, size=9.2, px=0.10, py=0.04, z=8).move_to([4.82, -1.08, 0])
        q4_4_cap = txt("특약 일부만 고치려다 전체 한도가 날아감", size=9.0, color=C_INK_1, z=7).move_to([3.88, -1.82, 0])

        self.play(
            FadeIn(VGroup(res_box_4, res_hdr_4, rg4_1[0], rg4_1[2], rg4_2[0], rg4_2[2], res_notes_4), shift=RIGHT * 0.12),
            Create(rg4_1[1]), Create(rg4_2[1]), GrowArrow(vs_arr_4),
            FadeIn(VGroup(q4_1, ceil_ln, ceil_lbl, q4_1_t1)), GrowFromEdge(b_1doc, DOWN),
            FadeIn(VGroup(q4_2, prog_bg, q4_2_cap)),
            FadeIn(VGroup(q4_3, mosaic_compact)),
            FadeIn(VGroup(q4_4, lim_bars_before, wipe_l_lbl, q4_4_cap)),
            run_time=1.15,
        )

        self.cam_move(
            zoom=1.36,
            center=[1.88, 1.18, 0],
            anims=[GrowFromEdge(b_all, DOWN), FadeIn(q4_1_t2), Flash([0.65, 1.26, 0], color=C_CORAL, line_length=0.22, num_lines=8), FadeIn(mis_calc, shift=RIGHT * 0.10), GrowFromEdge(prog_22, LEFT)],
            rt=1.15,
        )
        self.wait(0.65)

        self.cam_move(
            zoom=1.36,
            center=[1.88, -1.14, 0],
            anims=[ReplacementTransform(mosaic_compact, mosaic), FadeIn(q4_3_cap, shift=UP * 0.05), GrowArrow(wipe_arr), lim_bars_before.animate.set_opacity(0.14), FadeIn(wipe_r, scale=1.25)],
            rt=1.15,
        )
        self.wait(0.65)
        self.reset_cam_2d(rt=0.85)

        beat4a_all = VGroup(
            res_grp_4, vs_arr_4,
            q4_1, ceil_ln, ceil_lbl, b_1doc, b_all, q4_1_t1, q4_1_t2,
            q4_2, mis_calc, prog_bg, prog_22, q4_2_cap,
            q4_3, mosaic, q4_3_cap,
            q4_4, lim_bars_before, wipe_l_lbl, wipe_arr, wipe_r, q4_4_cap,
        )
        self.check_bounds(beat4a_all, "CH4A EXTRACT DIAGNOSTIC")
        self.wait(1.40)

        # -------------------------------------------------------------------
        # Beat 4B: AI = Verbatim Copy Only, Computer Code = 100% Math!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ① AI는 암산하지 않고 약관 글자 그대로 베껴 적기만 하고, 금액 계산은 100% 컴퓨터 공식이 맡습니다",
            rt=0.40,
        )

        dual_path_bar = fit(
            pill("무료 한도 절약법 : 처음 쌓인 대량 약관은 표 읽기 규칙으로 처리하고, 무료 AI 횟수는 매주 새로 나오는 약관에만 아껴 씁니다", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.8, z=9),
            max_w=11.85,
        ).move_to([0.0, 2.60, 0])

        src_tok1 = pill("진단보험금 2,000만원", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=13.0)
        src_tok2 = pill("1년 미만 50% 감액", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=13.0)
        src_tok3 = pill("90일 면책기간", fg=C_INK_0, bg=C_PANEL_HI, border=C_INK_1, size=13.0)
        src_tokens = VGroup(src_tok1, src_tok2, src_tok3).arrange(DOWN, buff=0.22).move_to([-4.25, -0.05, 0])
        src_hdr = txt("약관에 적힌 원래 문장", size=12.0, color=C_INK_1, bold=True, z=7).move_to([-4.25, 1.38, 0])

        stencil_frame = RoundedRectangle(corner_radius=0.08, width=3.15, height=1.06, fill_color=C_PANEL_HI, fill_opacity=0.96, stroke_color=C_CYAN, stroke_width=2.0).move_to([-0.42, 1.56, 0]).set_z_index(4)
        stencil_title = txt("받아쓰기 전용 AI (암산 금지!)", size=12.0, color=C_CYAN, bold=True, z=6).move_to(stencil_frame.get_top() + DOWN * 0.25)
        stencil_sub = txt("정확히 통과한 줄 : 22줄 → 39줄로 상승 ✓", size=10.2, color=C_MINT, bold=True, z=6).move_to(stencil_frame.get_bottom() + UP * 0.24)
        stencil_out = pill('"2,000만원 / 1년미만 50% / 90일"', fg=C_GOLD, bg=C_PANEL, border=C_GOLD, size=11.6).move_to([3.65, 1.56, 0])
        arr_up_in = arrow_2d(src_tok1.get_right(), stencil_frame.get_left(), color=C_CYAN, sw=2.0)
        arr_up_out = arrow_2d(stencil_frame.get_right(), stencil_out.get_left(), color=C_GOLD, sw=2.0)

        ax_origin = np.array([-1.55, -2.35, 0.0])
        x_axis = Arrow(ax_origin, ax_origin + RIGHT * 6.95, buff=0, color=C_INK_2, stroke_width=2.0, tip_length=0.14).set_z_index(4)
        y_axis = Arrow(ax_origin, ax_origin + UP * 2.38, buff=0, color=C_INK_2, stroke_width=2.0, tip_length=0.14).set_z_index(4)
        code_badge = fit(pill("금액·기간 계산 프로그램 (실수 0%) — 삼성화재 681건은 AI 없이 표에서 바로 추출", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=10.8), max_w=6.65).move_to([2.05, 0.36, 0])
        arr_dn_in = arrow_2d(src_tok2.get_right(), code_badge.get_left() + LEFT * 0.06, color=C_CYAN, sw=2.0)

        y_1000, y_2000 = ax_origin[1] + 0.90, ax_origin[1] + 1.80
        x_90d, x_1yr, x_end = ax_origin[0] + 1.45, ax_origin[0] + 3.75, ax_origin[0] + 6.45
        dash_1000 = DashedLine([ax_origin[0], y_1000, 0], [x_1yr, y_1000, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.2).set_z_index(3)
        dash_2000 = DashedLine([ax_origin[0], y_2000, 0], [x_end, y_2000, 0], dash_length=0.08, color=C_SLATE, stroke_width=1.2).set_z_index(3)
        lbl_y1 = txt("1,000만", size=11.4, color=C_CYAN, bold=True, z=6).move_to([ax_origin[0] - 0.52, y_1000, 0])
        lbl_y2 = txt("2,000만", size=11.4, color=C_GOLD, bold=True, z=6).move_to([ax_origin[0] - 0.52, y_2000, 0])
        lbl_x0 = txt("90일 이내(0원)", size=10.4, color=C_CORAL, bold=True, z=6).move_to([(ax_origin[0] + x_90d) / 2, ax_origin[1] - 0.28, 0])
        lbl_x1 = txt("1년 미만 (절반 1,000만)", size=10.4, color=C_CYAN, bold=True, z=6).move_to([(x_90d + x_1yr) / 2, ax_origin[1] - 0.28, 0])
        lbl_x2 = txt("1년 이후 (전액 2,000만)", size=10.4, color=C_GOLD, bold=True, z=6).move_to([(x_1yr + x_end) / 2, ax_origin[1] - 0.28, 0])

        area_half = Rectangle(width=x_1yr - x_90d, height=0.90, fill_color=C_CYAN, fill_opacity=0.18, stroke_width=0).move_to([(x_90d + x_1yr) / 2, ax_origin[1] + 0.45, 0]).set_z_index(2)
        area_full = Rectangle(width=x_end - x_1yr, height=1.80, fill_color=C_GOLD, fill_opacity=0.22, stroke_width=0).move_to([(x_1yr + x_end) / 2, ax_origin[1] + 0.90, 0]).set_z_index(2)
        step_curve = VMobject(color=C_GOLD, stroke_width=3.6).set_z_index(7)
        step_curve.set_points_as_corners([[ax_origin[0], ax_origin[1], 0], [x_90d, ax_origin[1], 0], [x_90d, y_1000, 0], [x_1yr, y_1000, 0], [x_1yr, y_2000, 0], [x_end, y_2000, 0]])

        terrace_half = Prism(dimensions=[x_1yr - x_90d, 0.90, 0.42], fill_color=C_CYAN, fill_opacity=0.26, stroke_color=C_CYAN, stroke_width=1.2).move_to([(x_90d + x_1yr) / 2, ax_origin[1] + 0.45, 0.21])
        terrace_full = Prism(dimensions=[x_end - x_1yr, 1.80, 0.84], fill_color=C_GOLD, fill_opacity=0.30, stroke_color=C_GOLD, stroke_width=1.4).move_to([(x_1yr + x_end) / 2, ax_origin[1] + 0.90, 0.42])

        self.cam_move(
            phi=42 * DEGREES,
            theta=-64 * DEGREES,
            zoom=0.94,
            center=[0.35, -0.25, 0.15],
            anims=[
                FadeOut(beat4a_all, shift=UP * 0.10),
                FadeIn(dual_path_bar), FadeIn(src_hdr),
                LaggedStart(*[FadeIn(t, shift=RIGHT * 0.12) for t in src_tokens], lag_ratio=0.08),
                FadeIn(VGroup(stencil_frame, stencil_title, stencil_sub)),
                GrowArrow(arr_up_in), Create(x_axis), Create(y_axis), FadeIn(code_badge), GrowArrow(arr_dn_in),
                Create(step_curve),
                FadeIn(terrace_half, shift=OUT * 0.2), FadeIn(terrace_full, shift=OUT * 0.35),
            ],
            rt=1.30,
        )
        self.remove(beat4a_all)
        self.wait(0.75)
        self.reset_cam_2d(
            anims=[
                FadeOut(terrace_half), FadeOut(terrace_full),
                GrowArrow(arr_up_out), FadeIn(stencil_out, shift=RIGHT * 0.12),
                Create(dash_1000), Create(dash_2000),
                FadeIn(VGroup(lbl_y1, lbl_y2, lbl_x0, lbl_x1, lbl_x2)),
                FadeIn(area_half), FadeIn(area_full),
            ],
            rt=1.05,
        )
        self.remove(terrace_half, terrace_full)

        beat4b_all = VGroup(
            dual_path_bar, src_hdr, src_tokens, stencil_frame, stencil_title, stencil_sub, stencil_out, arr_up_in, arr_up_out,
            x_axis, y_axis, code_badge, dash_1000, dash_2000, lbl_y1, lbl_y2, lbl_x0, lbl_x1, lbl_x2, area_half, area_full, step_curve, arr_dn_in,
        )
        self.check_bounds(beat4b_all, "CH4B STENCIL & CODE")
        self.wait(1.90)

        # -------------------------------------------------------------------
        # Beat 4C: Two AIs Read Picture Document Separately -> Magnifier Fixes Any Mismatch!
        # -------------------------------------------------------------------
        hb = self.update_subtitle(
            hb,
            "해결 ② 글자가 안 긁히는 308쪽 그림 문서는 서로 다른 AI 두 개가 따로 읽고, 다른 칸만 원본을 확대해 고칩니다",
            rt=0.40,
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

        emit_left = pill("첫 번째 AI가 읽기", fg=C_CYAN, bg=C_PANEL_HI, border=C_CYAN, size=11.8).move_to([-4.95, 0.12, 0])
        emit_top = pill("두 번째 AI가 교차 확인", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD, size=11.8).move_to([-0.80, 2.22, 0])
        laser_x = Prism(dimensions=[0.07, 3.20, 0.85], fill_color=C_CYAN, fill_opacity=0.35, stroke_color=C_CYAN, stroke_width=1.8).move_to([-3.55, 0.08, 0.42])
        laser_y = Prism(dimensions=[5.55, 0.07, 0.85], fill_color=C_GOLD, fill_opacity=0.35, stroke_color=C_GOLD, stroke_width=1.8).move_to([-0.80, 1.62, 0.42])

        self.cam_move(
            phi=46 * DEGREES,
            theta=-58 * DEGREES,
            zoom=0.98,
            center=[-0.80, 0.0, 0.1],
            anims=[FadeOut(beat4b_all, shift=UP * 0.10), FadeIn(cells), FadeIn(emit_left), FadeIn(emit_top)],
            rt=1.00,
        )
        self.remove(beat4b_all)

        self.add(laser_x)
        self.play(
            laser_x.animate.move_to([1.95, 0.08, 0.42]),
            LaggedStart(*[AnimationGroup(*[cell_grid[r][c].animate.set_fill(C_CYAN_DIM, opacity=0.85).set_stroke(C_CYAN, width=1.6) for r in range(rows_n)]) for c in range(cols_n)], lag_ratio=0.07),
            run_time=0.95,
        )
        self.remove(laser_x)

        err_cell = cell_grid[err_r][err_c]
        err_spike = Prism(dimensions=[cw, ch, 0.95], fill_color=C_CORAL, fill_opacity=0.72, stroke_color=WHITE, stroke_width=1.8).move_to(err_cell.get_center() + OUT * 0.475)

        self.add(laser_y)
        row_anims = []
        for r in range(rows_n):
            r_group = []
            for c in range(cols_n):
                if r == err_r and c == err_c:
                    r_group.append(cell_grid[r][c].animate.set_fill(C_CORAL, opacity=0.95).set_stroke(WHITE, width=2.8))
                else:
                    r_group.append(cell_grid[r][c].animate.set_fill("#1D332B", opacity=0.92).set_stroke(C_MINT, width=1.5))
            row_anims.append(AnimationGroup(*r_group))

        self.play(laser_y.animate.move_to([-0.80, -1.45, 0.42]), LaggedStart(*row_anims, lag_ratio=0.09), FadeIn(err_spike, shift=OUT * 0.35), run_time=1.00)
        self.remove(laser_y)

        lens_center = np.array([4.18, 0.15, 0.0])
        lens_circle = Circle(radius=1.36, fill_color=C_PANEL_HI, fill_opacity=0.97, stroke_color=C_GOLD, stroke_width=2.8).move_to(lens_center).set_z_index(8)
        lens_title = fit(txt("다르게 읽은 칸만 원본 확대", size=11.8, color=C_GOLD, bold=True, z=9), max_w=2.22).move_to(lens_center + UP * 0.76)
        wrong_val = txt("잘못 읽은 값: 1,000만원", size=12.0, color=C_CORAL, z=9).move_to(lens_center + UP * 0.20)
        strike_ln = Line(wrong_val.get_left() + LEFT * 0.06, wrong_val.get_right() + RIGHT * 0.06, color=C_CORAL, stroke_width=2.4).set_z_index(10)
        fixed_val = fit(txt("원본 확인 확정: 2,000만원 ✓", size=12.8, color=C_MINT, bold=True, z=9), max_w=2.38).move_to(lens_center + DOWN * 0.28)
        callout_1 = Line(err_cell.get_corner(UR), lens_circle.get_left() + UP * 0.55, color=C_GOLD, stroke_width=1.6).set_z_index(7)
        callout_2 = Line(err_cell.get_corner(DR), lens_circle.get_left() + DOWN * 0.55, color=C_GOLD, stroke_width=1.6).set_z_index(7)
        safeguard_bar = fit(
            pill("결과 : 308쪽 그림 문서 금액 오차 0건 달성 · 다시 읽을 때도 이미 확인 끝난 1,039줄은 지워지지 않게 잠금 보호 ✓", fg=C_GOLD, bg=C_PANEL_HI, border=C_GOLD_DEEP, size=10.8),
            max_w=11.85,
        ).move_to([0.0, -2.52, 0]).set_z_index(9)

        self.cam_move(
            phi=0 * DEGREES,
            theta=-90 * DEGREES,
            zoom=1.36,
            center=[2.45, 0.12, 0],
            anims=[FadeOut(err_spike), Create(callout_1), Create(callout_2), FadeIn(lens_circle, scale=0.85), FadeIn(lens_title), FadeIn(wrong_val)],
            rt=1.05,
        )
        self.remove(err_spike)
        self.wait(0.55)
        self.reset_cam_2d(
            anims=[Create(strike_ln), FadeIn(fixed_val, shift=UP * 0.10), err_cell.animate.set_fill(C_GOLD, opacity=0.95).set_stroke(WHITE, width=2.4), FadeIn(safeguard_bar, shift=UP * 0.10)],
            rt=1.05,
        )

        ch4_stage = VGroup(cells, emit_left, emit_top, lens_circle, lens_title, wrong_val, strike_ln, fixed_val, callout_1, callout_2, safeguard_bar)
        self.check_bounds(ch4_stage, "CH4C CROSS READ & SAFEGUARD")
        self.wait(2.20)
        print(f"[TIMING] Part 2 end: {self.renderer.time:.2f}s")

        self.fade_out_part(ch4_stage, hl, hr, hb)
