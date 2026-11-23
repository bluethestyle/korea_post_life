# 우체국보험 상품·청약 판단 지원 앱 — 발표 시연 애니메이션

발표 슬라이드 중간에 삽입하여 핵심 원리와 문제 해결 과정을 시각적 도형·인포그래픽으로 전달하기 위한 **Manim (`1920x1080 · 60fps`) 애니메이션**입니다.

## 서사 구성 (4부 분할본 + 전체 통합본)

1. **Part 1 (`Part1ServiceScene`, 1~2장)** — 우리가 만들려는 서비스 정의 및 중앙 조건 다이얼로 연동되는 6대 핵심 기능
2. **Part 2 (`Part2CollectExtractScene`, 3~4장)** — 공시·시장동향 수집 및 문서 추출 프로세스의 가용 자원 · 2×2 장애 진단 보드 · 해결 설계
3. **Part 3 (`Part3DecisionScene`, 5~6장)** — 판정 전용 AI(`Jev → gemini-decision-1`) 방사형 특성과 검증·분류 3열 병목 차트 및 해법
4. **Part 4 (`Part4OntologyImpactScene`, 7~9장)** — 온톨로지·지식그래프 담보 분석, 관문·치료여정 5단계 차트, 4대 실무 전략·응대 카드, 도입 전후 3대 업무 혁신 인포그래픽

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

- `common.py` : 공통 색상 팔레트, 기하 도형·텍스트 헬퍼, 상·하단 HUD 및 화면 경계 검사 베이스 클래스
- `part1_service.py` : 1장(서비스 목표 미니 대시보드) · 2장(중앙 조건 다이얼 6대 기능 방사형 연동)
- `part2_collect_extract.py` : 3장(수집 진단 보드·4단계 에이전트 분업) · 4장(추출 진단 보드·원문/코드 분리 및 308쪽 교차 판독)
- `part3_decision.py` : 5장(`Jev` 및 `gemini-decision-1` 배경·4분면 특성) · 6장(검증·분류 3열 병목 차트·양극 분리 및 토큰 창 제어)
- `part4_ontology_impact.py` : 7장(온톨로지 진단 보드·3계층 및 76종 확장) · 8장(합산 탐색·관문/치료 5단계 차트·응대 카드) · 9장(전후 업무 혁신 도넛 지표)
- `postlife_demo.py` : 4개 파트 통합 엔트리포인트
- `storyboard.md` : 전체 9장 스토리보드 해설
