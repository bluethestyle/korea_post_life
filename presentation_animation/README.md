# 우체국보험 상품·청약 판단 지원 앱 — 발표 시연 애니메이션

발표 슬라이드 중간에 삽입하여 핵심 원리와 문제 해결 과정을 3차원 기하 도형·인포그래픽과 다큐멘터리식 카메라 워킹(`줌인 · 패닝 · 3D 회전 구도`)으로 전달하기 위한 **Manim `ThreeDScene` (`1920x1080 · 60fps`) 애니메이션**입니다.

## 서사 구성 (4부 분할본 + 전체 통합본)

1. **Part 1 (`Part1ServiceScene`, 1~2장)** — 3D 공시 문서 협곡에서 출발하는 서비스 목표 정의 및 3D 궤도형 조건 허브로 연동되는 6대 핵심 기능
2. **Part 2 (`Part2CollectExtractScene`, 3~4장)** — 수집·추출 현미경 장애 진단 보드, 3D 16개사 레이저 커튼 2단 스캔, 3D 계단형 지급액 블록 및 308쪽 직교 레이저 교차 판독
3. **Part 3 (`Part3DecisionScene`, 5~6장)** — 판정 전용 AI(`Jev → gemini-decision-1`) 3D 자이로 코어 특성과 3D 24기둥 황금 확률 첨탑(`0.94↑ vs 0.06↓`) · 60초 토큰 창 제어
4. **Part 4 (`Part4OntologyImpactScene`, 7~9장)** — 3D Z축 적층 온톨로지 평면, 54노드 3D 지식그래프 은하 공전 및 합산 탐색 다이브, 관문·치료여정 줌 투어, 전후 업무 혁신 트래킹 인포그래픽

## 환경 준비 및 렌더링 실행 방법

FFmpeg와 한글 글꼴(`Noto Sans KR`)이 설치된 환경에서 실행합니다.

```bash
cd presentation_animation
python -m venv .venv
# Windows: .\.venv\Scripts\pip install -r requirements.txt
# Linux/macOS: .venv/bin/pip install -r requirements.txt

# 저해상도(480p15) 검수용 프리뷰 렌더링
manim -ql postlife_demo.py Part1ServiceScene Part2CollectExtractScene Part3DecisionScene Part4OntologyImpactScene

# 고해상도(1080p60) 본 렌더링
manim -qh postlife_demo.py Part1ServiceScene Part2CollectExtractScene Part3DecisionScene Part4OntologyImpactScene
```

## 소스 파일 구조

- `common.py` : 공통 색상 팔레트, 기하 도형·텍스트 헬퍼, Cairo 원점 고정 `ThreeDScene` 카메라·고정 자막 바(`fixed_in_frame`) 베이스 클래스
- `part1_service.py` : 1장(3D 문서 협곡 · 기준 충돌 다이브 · 이원화 서비스 투사) · 2장(3D 궤도 조건 허브 · 핵심 화면 클로즈업 투어)
- `part2_collect_extract.py` : 3장(현미경 진단 · 3D 16개사 레이저 스캔 · 물리 게이트) · 4장(3D 계단 지급액 블록 · 3D 직교 레이저 교차 판독)
- `part3_decision.py` : 5장(`Jev` 패닝 · `decision-1` 3D 코어) · 6장(병목 줌인 · 3D 24기둥 황금 확률 첨탑 · 재추출 루프 추적)
- `part4_ontology_impact.py` : 7장(3D Z평면 적층 · 54노드 3D 은하 공전) · 8장(허브 다이브 · 관문/치료 줌 투어 · A4 카드) · 9장(전후 혁신 트래킹 도넛 지표)
- `postlife_demo.py` : 4개 파트 통합 엔트리포인트
- `storyboard.md` : 전체 9장 3D 공간 · 카메라 스토리보드 해설
