import json

import pytest

try:
    from postlife.disclosure import dbins
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import dbins

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮김)
# 2단계 상품명 목록 (장기보험 / Off-Line / 질병). &는 &amp;로 온다
NAMES = {"result": [{"PDC_NM": "무배당 프로미라이프 New I`mOK 암보험2607"},
                    {"PDC_NM": "무배당 프로미라이프 마니&amp;또 통합암보험2609"}]}
# 3단계 판매기간 목록. 닫힌 기간에만 종료일이 있다
PERIODS = {"result": [{"SL_STR_DT": "20260701", "SQNO": 10606, "SL_FIN_DT": "20260817"},
                      {"SL_STR_DT": "20260818", "SQNO": 10805, "SL_FIN_DT": "20261018"},
                      {"SL_STR_DT": "20261019", "SQNO": 10884}]}
# 4단계 서류 목록: 열린 기간(종료일 없음)과 판매중지 상품의 닫힌 기간
DOCS = {"result": [{"SL_STR_DT": "20260701", "CNSL_SMAR_FINM": "요약_30636(25)_20260701.pdf", "SQNO": 10601,
                    "BIZ_MDDC_FINM": "사방_30636(25)_20260701.pdf", "INPL_FINM": "약관_30636(25)_20260701.pdf",
                    "PDC_NM": "무배당 프로미라이프 참좋은 훼밀리더블플러스종합보험2607"}]}
DOCS_CLOSED = {"result": [{"SL_STR_DT": "20260401", "CNSL_SMAR_FINM": "요약_30636(23)_20260401.pdf", "SQNO": 10345,
                           "BIZ_MDDC_FINM": "사방_30636(23)_20260401.pdf", "SL_FIN_DT": "20260430",
                           "INPL_FINM": "약관_30636(23)_20260401.pdf",
                           "PDC_NM": "무배당 프로미라이프 참좋은 훼밀리더블플러스종합보험2604"}]}
# 5단계 검색. 선택 상품과 같은 응답에 판매중지 행, 요약서가 없는 행, 옛 파일 이름 꼴이 섞여 온다
SEARCH = {"result": [
    {"ARC_PDC_SL_YN": "1", "CNSL_SMAR_FINM": "요약_31267(00)_20261101.pdf", "SALE_BEGIN_DAY": "2026.11.01", "SQNO": 10928,
     "BIZ_MDDC_FINM": "사방_31267(00)_20261101.pdf", "ARC_KND_LGCG_NM": "장기보험",
     "INPL_FINM": "약관_31267(00)_20261101.pdf", "PDC_NM": "무배당 프로미라이프 나에게 맞춘 간편건강보험2611"},
    {"ARC_PDC_SL_YN": "1", "SALE_BEGIN_DAY": "2026.11.16", "SQNO": 10956, "BIZ_MDDC_FINM": "사방_31253(01)_20261116.pdf",
     "ARC_KND_LGCG_NM": "장기보험", "INPL_FINM": "약관_31253(01)_20261116.pdf",
     "PDC_NM": "무배당 프로미라이프 나에게맞춘중증케어간편건강보험2611"},
    {"ARC_PDC_SL_YN": "0", "SALE_BEGIN_DAY": "2018.10.01", "SQNO": 654, "BIZ_MDDC_FINM": "10513_20181001_사업_아파트종합보험(0).pdf",
     "ARC_KND_LGCG_NM": "일반", "INPL_FINM": "10513_20181001_약관_아파트종합보험(0).pdf", "PDC_NM": "아파트종합보험"},
]}
EMPTY = {"result": []}   # 탭 값(arc_pdc_sl_yn)이 상품과 맞지 않을 때, &amp;를 풀지 않은 이름을 보냈을 때
# 화면 스크립트(comnUtil.js)가 처리하는 오류 꼴. 실제 응답으로 받아 본 적은 없다
ERROR = {"errMsg": {"rspnCd": "-997", "rspnMsgCtnt": "이용 가능 시간이 아닙니다."}}


def test_names_are_unescaped():
    products = dbins.parse_products(NAMES, "장기보험", "Off-Line", "질병")
    assert [p.name for p in products] == ["무배당 프로미라이프 New I`mOK 암보험2607", "무배당 프로미라이프 마니&또 통합암보험2609"]
    assert products[0].channel == "Off-Line" and products[0].selling


def test_periods_and_pick():
    periods = dbins.parse_periods("행복플러스", PERIODS)
    assert [(p.sqno, p.start, p.end) for p in periods] == [
        ("10606", "2026-07-01", "2026-08-17"), ("10805", "2026-08-18", "2026-10-18"), ("10884", "2026-10-19", None)]
    assert dbins.pick_period(periods).sqno == "10884"
    assert dbins.pick_period(periods, "2026-09-01").sqno == "10805"
    assert dbins.pick_period(periods, "2026-06-30") is None
    assert dbins.parse_periods("x", EMPTY) == []


def test_documents_carry_code_from_file_name():
    docs = dbins.parse_documents(DOCS)
    assert [d.kind for d in docs] == ["사업방법서", "상품요약서", "약관"]
    assert {d.code for d in docs} == {"30636"} and docs[1].file_name == "요약_30636(25)_20260701.pdf"
    assert docs[0].start == "2026-07-01" and docs[0].end is None and docs[0].sqno == "10601"
    closed = dbins.parse_documents(DOCS_CLOSED)
    assert closed[0].end == "2026-04-30" and closed[0].name.endswith("2604")


def test_search_rows():
    rows = dbins.parse_search(SEARCH)
    assert [(r.code, r.start, r.selling, r.group) for r in rows] == [
        ("31267", "2026-11-01", True, "장기보험"), ("31253", "2026-11-16", True, "장기보험"), ("10513", "2018-10-01", False, "일반")]
    assert "상품요약서" not in rows[1].files and set(rows[0].files) == {"사업방법서", "상품요약서", "약관"}
    assert dbins.code_of("요약_30633(25)_20260701.pdf") == ("30633", "25")
    assert dbins.code_of("이름만.pdf") == ("", "")


def test_server_error_and_bad_shape_are_raised():
    with pytest.raises(ValueError, match="-997"):
        dbins.parse_periods("x", ERROR)
    with pytest.raises(ValueError):
        dbins.parse_search({"list": []})


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else b""
            headers = {"Content-Type": "application/pdf;charset=UTF-8" if isinstance(reply, bytes) and reply else ""}
            encoding = None

            def raise_for_status(self):
                pass

            def json(self):
                return reply

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def test_list_documents_sends_what_the_page_sends():
    s = FakeSession([PERIODS, DOCS])
    docs = dbins.list_documents(s, "무배당 프로미라이프 마니&또 통합암보험2609")
    assert [d.kind for d in docs] == ["사업방법서", "상품요약서", "약관"]
    (m1, url1, kw1), (m2, url2, kw2) = s.sent
    assert (m1, url1) == ("POST", "https://www.idbins.com/insuPcPbanFindProductStep3_AX.do")
    assert json.loads(kw1["data"]) == {"pdc_nm": "무배당 프로미라이프 마니&또 통합암보험2609", "arc_pdc_sl_yn": "1"}
    assert kw1["headers"]["Content-Type"].startswith("application/json")
    assert url2.endswith("/insuPcPbanFindProductStep4_AX.do") and json.loads(kw2["data"]) == {"sqno": "10884", "arc_pdc_sl_yn": "1"}


def test_list_products_walks_categories_and_search_body():
    s = FakeSession([NAMES, {"result": [{"PDC_NM": "무배당 프로미라이프 New I`mOK 암보험2607"}]}])
    cats = (("장기보험", "Off-Line", "질병"), ("장기보험", "TM/CM", "질병"))
    products = dbins.list_products(s, selling=False, categories=cats)
    assert len(products) == 2 and not products[0].selling   # 두 칸에 나온 이름은 한 번만
    assert json.loads(s.sent[1][2]["data"]) == {"arc_knd_lgcg_nm": "장기보험", "sl_chn_nm": "TM/CM",
                                                "arc_knd_mdcg_nm": "질병", "arc_pdc_sl_yn": "0"}
    s = FakeSession([SEARCH])
    dbins.search_products(s, "간편건강")
    assert s.sent[0][1].endswith("/insuPcPbanFindProductStep5_AX.do")
    assert s.sent[0][2]["data"].decode() == '{"searchCheck":"0","keyword":"간편건강","beginDate":"","endDate":""}'


def test_download_url_and_non_pdf():
    doc = dbins.parse_documents(DOCS)[1]
    s = FakeSession([b"%PDF-1.4 ..."])
    assert dbins.download(s, doc).startswith(b"%PDF-")
    # 실제로 내려받기에 성공한 주소(요약_30633(25)…, 요약_31267(00)…)와 같은 꼴 (encodeURIComponent: 한글은 바꾸고 괄호는 그대로)
    assert s.sent[0][:2] == ("GET", "https://www.idbins.com/cYakgwanDown.do?FilePath=InsProduct/"
                                    "%EC%9A%94%EC%95%BD_30636(25)_20260701.pdf")
    with pytest.raises(ValueError, match="0바이트"):   # 없는 파일: 상태 200, 본문 0바이트
        dbins.download(FakeSession([b""]), doc)
