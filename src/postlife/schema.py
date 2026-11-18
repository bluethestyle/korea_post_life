"""구글 시트 정본의 탭과 열 정의.

docs/planning.md 5.5의 표와 같아야 한다. tests/test_schema.py가 둘을 대조한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str
    type: str  # str, int, float, bool, date, datetime
    required: bool


@dataclass(frozen=True)
class Tab:
    name: str
    key: str
    mode: str  # replace(개정 시 교체), append(누적), human(담당자 관리)
    parent: str | None  # replace 탭에서 종형으로 거슬러 오르는 열
    columns: tuple[Column, ...]

    @property
    def header(self) -> list[str]:
        return [c.name for c in self.columns]


TABS: dict[str, Tab] = {
    "sys_상품종형": Tab(
        name="sys_상품종형",
        key="종형ID",
        mode="replace",
        parent="종형ID",
        columns=(
            Column("종형ID", "str", True),
            Column("개정판ID", "str", True),
            Column("모상품ID", "str", True),
            Column("종형계보키", "str", True),
            Column("기관코드", "str", True),
            Column("공시상품코드", "str", True),
            Column("공시상품명", "str", True),
            Column("종형명", "str", True),
            Column("비교역할구분", "str", True),
            Column("심사유형", "str", True),
            Column("간편고지약칭", "str", True),
            Column("고지최근소견개월", "int", False),
            Column("고지입원수술년수", "int", False),
            Column("고지중대질병년수", "int", False),
            Column("갱신유형", "str", True),
            Column("갱신주기년", "int", False),
            Column("환급유형", "str", False),
            Column("납입면제적용", "bool", False),
            Column("적용시작일", "date", True),
            Column("판매종료일", "date", False),
            Column("공시목록URL", "str", True),
            Column("요약서해시", "str", False),
            Column("사업방법서해시", "str", False),
            Column("약관별표해시", "str", False),
        ),
    ),
    "sys_가입조건": Tab(
        name="sys_가입조건",
        key="조건행ID",
        mode="replace",
        parent="종형ID",
        columns=(
            Column("조건행ID", "str", True),
            Column("종형ID", "str", True),
            Column("특약ID", "str", False),
            Column("보험기간구분", "str", True),
            Column("납입기간구분", "str", True),
            Column("성별", "str", False),
            Column("최저가입나이", "int", True),
            Column("최고가입나이", "int", True),
            Column("구간최대가입금액만원", "float", False),
        ),
    ),
    "sys_특약": Tab(
        name="sys_특약",
        key="특약ID",
        mode="replace",
        parent="종형ID",
        columns=(
            Column("특약ID", "str", True),
            Column("종형ID", "str", True),
            Column("특약계보키", "str", True),
            Column("담보구분", "str", True),
            Column("원시특약명", "str", True),
            Column("갱신여부", "bool", True),
            Column("갱신주기년", "int", False),
            Column("최소가입금액만원", "float", False),
            Column("최대가입금액만원", "float", False),
            Column("합산한도기준키", "str", False),
        ),
    ),
    "sys_급부": Tab(
        name="sys_급부",
        key="급부ID",
        mode="replace",
        parent="특약ID",
        columns=(
            Column("급부ID", "str", True),
            Column("특약ID", "str", True),
            Column("원시급부명", "str", True),
            Column("급부역할", "str", True),
            Column("기준가입금액만원", "float", True),
            Column("기준지급금액만원", "float", True),
            Column("지급횟수제한", "str", False),
            Column("면책기간일수", "int", True),
            Column("감액개월1", "int", False),
            Column("감액지급률1", "float", False),
            Column("감액개월2", "int", False),
            Column("감액지급률2", "float", False),
            Column("근거문서종류", "str", False),
            Column("근거문서쪽수", "int", False),
        ),
    ),
    "sys_보험료예시": Tab(
        name="sys_보험료예시",
        key="보험료행ID",
        mode="replace",
        parent="특약ID",
        columns=(
            Column("보험료행ID", "str", True),
            Column("특약ID", "str", True),
            Column("가입나이", "int", True),
            Column("성별", "str", True),
            Column("보험기간구분", "str", True),
            Column("납입기간구분", "str", True),
            Column("기준가입금액만원", "float", True),
            Column("월납보험료원", "int", True),
            Column("출처구분", "str", True),
        ),
    ),
    "sys_결합제약": Tab(
        name="sys_결합제약",
        key="제약ID",
        mode="replace",
        parent="종형ID",
        columns=(
            Column("제약ID", "str", True),
            Column("종형ID", "str", True),
            Column("기준특약ID", "str", True),
            Column("대상특약ID", "str", True),
            Column("제약유형", "str", True),
            Column("제약수치", "float", False),
            Column("제약단위", "str", False),
            Column("근거문구", "str", False),
        ),
    ),
    "sys_급부질병코드": Tab(
        name="sys_급부질병코드",
        key="질병매핑ID",
        mode="replace",
        parent="급부ID",
        columns=(
            Column("질병매핑ID", "str", True),
            Column("급부ID", "str", True),
            Column("KCD버전", "str", True),
            Column("시작코드", "str", True),
            Column("끝코드", "str", True),
            Column("포함여부", "str", True),
            Column("별표명", "str", False),
        ),
    ),
    "sys_시장동향": Tab(
        name="sys_시장동향",
        key="동향ID",
        mode="append",
        parent=None,
        columns=(
            Column("동향ID", "str", True),
            Column("수집주차", "str", True),
            Column("발표일자", "date", True),
            Column("기관코드", "str", True),
            Column("분류유형", "str", True),
            Column("관련종형ID", "str", False),
            Column("관련표준담보ID", "str", False),
            Column("핵심요약", "str", True),
            Column("매체명", "str", False),
            Column("출처URL", "str", True),
            Column("수집경로", "str", True),
            Column("판정확률", "float", False),
        ),
    ),
    "sys_작업로그": Tab(
        name="sys_작업로그",
        key="로그ID",
        mode="append",
        parent=None,
        columns=(
            Column("로그ID", "str", True),
            Column("실행일시", "datetime", True),
            Column("작업단계", "str", True),
            Column("대상탭", "str", True),
            Column("대상행ID", "str", True),
            Column("대상열", "str", False),
            Column("변경전값", "str", False),
            Column("변경후값", "str", False),
            Column("호출모델", "str", False),
            Column("판정확률", "float", False),
            Column("결과", "str", True),
            Column("사유", "str", False),
        ),
    ),
    "hum_표준담보사전": Tab(
        name="hum_표준담보사전",
        key="표준담보ID",
        mode="human",
        parent=None,
        columns=(
            Column("표준담보ID", "str", True),
            Column("보장대분류", "str", True),
            Column("보장중분류", "str", True),
            Column("표준담보명", "str", True),
            Column("급부유형", "str", True),
            Column("비교기준단위만원", "float", True),
            Column("사용여부", "bool", True),
        ),
    ),
    "hum_표준질병군": Tab(
        name="hum_표준질병군",
        key="질병군코드행ID",
        mode="human",
        parent=None,
        columns=(
            Column("질병군코드행ID", "str", True),
            Column("질병군ID", "str", True),
            Column("질병군명", "str", True),
            Column("KCD버전", "str", True),
            Column("시작코드", "str", True),
            Column("끝코드", "str", True),
        ),
    ),
    "hum_담보매핑": Tab(
        name="hum_담보매핑",
        key="급부ID",
        mode="human",
        parent=None,
        columns=(
            Column("급부ID", "str", True),
            Column("공시상품명", "str", True),
            Column("원시특약명", "str", True),
            Column("원시급부명", "str", True),
            Column("추천표준담보ID", "str", False),
            Column("추천표준담보명", "str", False),
            Column("매핑확률", "float", False),
            Column("확정표준담보ID", "str", False),
            Column("검토상태", "str", True),
            Column("담당자메모", "str", False),
        ),
    ),
    "hum_기준값": Tab(
        name="hum_기준값",
        key="기준키",
        mode="human",
        parent=None,
        columns=(
            Column("기준키", "str", True),
            Column("기준분류", "str", True),
            Column("기준명", "str", True),
            Column("수치값", "float", False),
            Column("문자값", "str", False),
            Column("단위", "str", False),
            Column("근거", "str", False),
            Column("적용시작일", "date", True),
        ),
    ),
}

TAB_ORDER: list[str] = list(TABS)
