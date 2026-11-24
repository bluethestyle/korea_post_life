# 우체국보험 상품·청약 판단 지원 시스템: 발표 시연 애니메이션

발표 슬라이드 사이에 배치해 문제 해결 구조와 데이터 흐름을 기하 인포그래픽, 세 축에 구조적 의미가 있는 3차원(`ThreeDScene` + 고대비 정면 빌보드 배지) 공간, 그리고 개별 개념을 중앙에서 동적으로 시연한 뒤 최종 2차원 종합 차트로 결합하는 정면 연출로 보여 주기 위한 Manim 애니메이션입니다. 화면 용어는 `common.py`의 보험과 IT 실무 용어 상수(`TERM`, `label_ko`)로 통일했으며, 발표자가 현장에서 설명하며 진행할 수 있도록 큰 글꼴과 여유 있는 정지 호흡을 두었습니다.

화면에 표시하는 모든 수치와 목록은 저장소 루트에서 `python scripts/export_presentation_facts.py`로 생성한 `presentation_animation/facts.json`에서 조회합니다. 영상 코드와 문서에서는 `facts.json`을 수동으로 편집하지 않습니다.

## 장면 구성 (분할본 네 편과 전체 통합본)

- **Part 1 (`Part1ServiceScene`, 1~2장)**: 공시 문서 대조의 어려움과 오프라인 단독 HTML 화면, 창구용 A4 단일 응대 화법 문서, 기본 조건(`reference_condition`, `default_base_variant`)에 연동되는 운영 화면(`site_screen_count`) 구성
- **Part 2 (`Part2CollectExtractScene`, 3~4장)**: 수집 단계의 서브에이전트 역할 분담(`disclosure_pilot_org`, `disclosure_batch_orgs`)과 요일별 시장 동향 수집(`collect_daily_plan`), 추출 단계의 원문 텍스트 추출과 코드 계산 분리(`example_targeted_anticancer`) 및 이미지형 요약서(`image_doc`) 이중 추출 교차 검증
- **Part 3 (`Part3DecisionScene`, 5~6장)**: 비생성 판정 모델(`models.decide`, `decision_model_spec`, `decision_model_uses`)의 원리와 특약 단위(추출 단위) 입력, 대칭 선택지 문항 설계(`symmetric_choice_probability`), 확률 임계값 분기(`verify_confirm_threshold`, `verify_reextract_threshold`), 분당 토큰 대기 기준(`decide_tokens_per_minute_guard`)
- **Part 4 (`Part4OntologyImpactScene`, 7~9장)**: 원천 사실, 표준 기준, 분석 및 인사이트 계층 구조와 표준담보 사전 확장(`dictionary_initial_size`, `dictionary_second_expansion`, `standard_coverage_in_use`), 포함과 통합 관계(`coverage_relations_by_kind`, `relation_covered_coverages`) 탐색, 고객군별 가입 가능 현황(`segment_map_cell_count`, `segment_map_grid`), 치료 단계(`treatment_stages`), 영업 인사이트(`sales_insight_categories`)와 응대 화법(`card_category_order`), 기존 수작업 방식 대비 구현된 구조와 미측정 과제(`not_yet_measured`)

## 사전 준비 (시스템 도구 확인)

렌더링에는 Python 3.12, `FFmpeg`, 한글 글꼴(`Noto Sans KR`)이 필요합니다. 실행 전에 아래 명령으로 설치 여부를 확인합니다.

```bash
# FFmpeg 설치 확인
ffmpeg -version

# 한글 글꼴 확인 (Linux / macOS)
fc-list : family | grep -i "Noto Sans KR"
```

Windows PowerShell에서는 아래 명령으로 글꼴 설치 여부를 확인할 수 있습니다.

```powershell
Add-Type -AssemblyName System.Drawing
(New-Object System.Drawing.Text.InstalledFontCollection).Families.Name | Select-String "Noto Sans KR"
```

## 가상환경 설치 및 렌더링 실행

이 폴더(`presentation_animation/`)는 Manim과 Cairo 의존성 격리를 위해 저장소 루트의 가상환경(`uv venv --python 3.12 .venv`)과 별도로 폴더 내부에 `.venv`를 만들어 실행합니다. 렌더링과 검증에 사용한 패키지 버전은 `manim==0.22.1`, `networkx==3.7`이며 `requirements.txt`에 고정되어 있습니다.

```bash
cd presentation_animation
python -m venv .venv

# Linux / macOS 가상환경 활성화 및 설치
source .venv/bin/activate
pip install -r requirements.txt

# Windows PowerShell 가상환경 활성화 및 설치
# .\.venv\Scripts\Activate.ps1
# pip install -r requirements.txt
```

### 1) 저해상도(480p15) 검수용 프리뷰 렌더링

가상환경을 활성화한 상태이거나 `.venv/bin/manim`(Windows는 `.\.venv\Scripts\manim`) 경로를 직접 지정해 실행합니다.

```bash
.venv/bin/manim -ql postlife_demo.py Part1ServiceScene Part2CollectExtractScene Part3DecisionScene Part4OntologyImpactScene
```

### 2) 고해상도(1080p60) 분할본 렌더링 및 전체 통합본 생성

```bash
.venv/bin/manim -qh postlife_demo.py Part1ServiceScene Part2CollectExtractScene Part3DecisionScene Part4OntologyImpactScene

# 분할본 이름을 스토리보드 파일명에 맞춰 복사하고 FFmpeg concat으로 통합본 생성
cp media/videos/postlife_demo/1080p60/Part1ServiceScene.mp4 우체국보험_발표시연_Part1_서비스목표와_구현기능_1080p60.mp4
cp media/videos/postlife_demo/1080p60/Part2CollectExtractScene.mp4 우체국보험_발표시연_Part2_자원제약과_난제해결_수집추출_1080p60.mp4
cp media/videos/postlife_demo/1080p60/Part3DecisionScene.mp4 우체국보험_발표시연_Part3_판정AI배경과_검증분류_해법_1080p60.mp4
cp media/videos/postlife_demo/1080p60/Part4OntologyImpactScene.mp4 우체국보험_발표시연_Part4_온톨로지해석과_업무혁신결과_1080p60.mp4

cat <<'EOF' > concat_list.txt
file '우체국보험_발표시연_Part1_서비스목표와_구현기능_1080p60.mp4'
file '우체국보험_발표시연_Part2_자원제약과_난제해결_수집추출_1080p60.mp4'
file '우체국보험_발표시연_Part3_판정AI배경과_검증분류_해법_1080p60.mp4'
file '우체국보험_발표시연_Part4_온톨로지해석과_업무혁신결과_1080p60.mp4'
EOF

ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy -movflags +faststart 우체국보험_발표시연_애니메이션_1080p60.mp4
```

## 소스 파일 구조

- `facts.json`: 저장소 루트의 `scripts/export_presentation_facts.py`가 생성하는 사실 자료 (수동 편집 금지)
- `common.py`: `fact()`, `num()`, 실무 용어 상수 `TERM`과 `label_ko()`, 색상 팔레트, 도형 도우미, 원점 고정 `ThreeDScene` 베이스 클래스
- `part1_service.py`: 1장(구축 목표 서비스와 이원화 전달 구조), 2장(기본 조건 다이얼과 운영 화면 구성)
- `part2_collect_extract.py`: 3장(수집 단계 분업과 시장 동향 선별), 4장(원문 텍스트 추출과 코드 계산 분리, 이미지형 요약서 이중 추출 교차 검증)
- `part3_decision.py`: 5장(판정 모델 원리와 적용 영역), 6장(대칭 선택지 확률 분리, 임계값 분기, 분당 토큰 윈도우 대기 기준)
- `part4_ontology_impact.py`: 7장(온톨로지 세 계층과 표준담보 사전 확장), 8장(포함과 통합 관계 탐색, 고객군별 가입 가능 현황, 영업 인사이트와 응대 화법), 9장(기존 수작업 방식과 구현된 비교 시스템 전후 대조)
- `postlife_demo.py`: 네 장면 통합 엔트리포인트
- `storyboard.md`: 장별 도형 구성, 참조 열쇠, 카메라 연출 해설
