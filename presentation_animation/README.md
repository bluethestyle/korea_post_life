# 우체국보험 상품·청약 판단 지원 앱 — 발표 시연 애니메이션

보험 상품 구조나 AI 기술을 처음 접하는 청중도 **첫 시청에 문제와 해결 원리를 직관적으로 이해**할 수 있도록, 모든 전문용어를 쉬운 일상 언어로 풀어 쓰고 기구적 도형 메타포·선택적 3차원(`ThreeDScene`) 구도·다큐멘터리 카메라 워킹(`클로즈업 · 패닝 · 펄스 추적`)으로 구성한 **Manim (`1920x1080 · 60fps`) 발표 시연 애니메이션**입니다.

## 서사 구성 (4부 분할본 + 전체 통합본)

1. **Part 1 (`Part1ServiceScene`, 1~2장)** — 수백 쪽 약관 비교와 창구 전달 문제를 해결하는 서비스 목표 및 고객 조건 다이얼로 연동되는 6가지 핵심 기능
2. **Part 2 (`Part2CollectExtractScene`, 3~4장)** — 약관 수집 4단계 역할 분담(두 번 내려받아 원본 대조), AI 받아쓰기와 컴퓨터 계산 공식 분리, 308쪽 그림 요약서 두 AI 교차 확인
3. **Part 3 (`Part3DecisionScene`, 5~6장)** — 글짓기 없이 객관식 확률만 찍는 채점 전용 AI(`Jev → gemini-decision-1`) 원리, `'있음 vs 없음'` 양자택일 황금 첨탑(`94점↑ vs 6점↓`), 3단 신호등 분류 및 1분 속도 조절기
4. **Part 4 (`Part4OntologyImpactScene`, 7~9장)** — 가벼운 3층 구조(`2.97MB`), 6,615건 공통 기준 연결 지도(실선·점선 구분 및 `52→76종` 확장), 나눠 파는 특약 합산 보장 탐색, 창구 A4 1장 요약 카드 및 도입 전후 변화 도넛 지표

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
- `part1_service.py` : 1장(3D 약관 기둥 숲 · 기준 충돌 클로즈업 · 본부 화면 & 창구 A4 요약 카드) · 2장(조건 다이얼 회전 · 6가지 핵심 기능 클로즈업 투어)
- `part2_collect_extract.py` : 3장(수집 장애 투어 · 4단계 역할 분담 기구 · 3D 16개사 2단 확인 물결) · 4장(받아쓰기 AI × 계산 프로그램 3D 계단 · 두 AI 교차 읽기)
- `part3_decision.py` : 5장(글짓기 AI vs 채점 전용 AI `Jev` · `decision-1` 3D 코어) · 6장(애매한 점수 해결 3D 황금 첨탑 · 3단 신호등 · 1분 속도 조절기)
- `part4_ontology_impact.py` : 7장(3D 3층 구조 · 3D 공통 기준 연결 지도 · `52→76종` 흡수) · 8장(합산 보장 탐색 · 가입 표 & 치료 5단계 · 4가지 지침 & A4 카드) · 9장(도입 전후 변화 도넛 지표)
- `postlife_demo.py` : 4개 파트 통합 엔트리포인트
- `storyboard.md` : 전체 9장 쉬운 설명 포인트 · 도형 메타포 · 카메라 연출 해설
