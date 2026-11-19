import json

import pytest

try:
    from postlife.disclosure import shinhanlife
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import shinhanlife

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮기고, null 칸과 머리 칸 일부는 뺐다)
_ROOT = "/repo/DigitalPlattform/cdh/cdhi/gd/pr/"
ONE = "신한(간편가입)통합건강보험 원(ONE)(무배당, 해약환급금 미지급형)"
HEADER = {"reqUrl": "/co/wcms/nodeInfoListPage.pwkjson", "serviceKey": "co/wcms/nodeInfoListPage", "resSuc": True,
          "resMsg": None, "resCode": None, "resMsgVo": None, "validateSuc": True, "inOutDataEnc": True, "dbDataEnc": False}
# 판매중 목록(selectListGoods): 상품 × 상품구분마다 가장 최근 판매기간 한 행. 종료일 99991231…은 열린 기간이다
LIST = {"elHeader": HEADER, "elData": {"listCount": 123, "pageNum": 1, "totalPageCount": 1, "sessionTokenKey": None,
                                        "securityData": None, "e2e_data1": None, "nodeInfoVoList": [
    {"wsId": "DigitalPlattform", "ndId": "6775adda95af424da2bb", "catId": "M160991914330045272",
     "title": ONE + "_일반_판매중_15", "meta01": "신한라이프", "meta02": "일반", "meta03": "보장", "meta04": "7000375",
     "meta05": ONE, "meta06": "TRUE", "meta07": "20260804000000", "meta08": "99991231235959",
     "meta09": _ROOT + "__media/상품요약서_" + ONE + "_260804.pdf",
     "meta10": _ROOT + "__etc/사업방법서_" + ONE + "_260401_v1.pdf",
     "meta11": _ROOT + "__etc/SHL0524_" + ONE + "_260804.pdf", "meta12": None, "meta13": None, "meta14": "229", "meta15": "15"},
    # 이름에 대괄호, 종료일이 99991231000000인 행
    {"wsId": "DigitalPlattform", "ndId": "cfd3ff496eba40cebfba", "meta01": "신한라이프", "meta02": "TM", "meta03": "보장",
     "meta04": "7000375", "meta05": "[순환계Plan] 신한(간편가입)통합건강보험 원(ONE)Core(무배당, 해약환급금 미지급형)",
     "meta06": "TRUE", "meta07": "20261012000000", "meta08": "99991231000000",
     "meta09": _ROOT + "__media/상품요약서_[순환계Plan] 신한(간편가입)통합건강보험 원(ONE)Core(무배당, 해약환급금 미지급형)_20261012_v1.0.pdf",
     "meta10": _ROOT + "__etc/사업방법서_" + ONE + "_260401.pdf", "meta11": None, "meta15": "1"},
    # 요약서와 상품코드가 없는 행
    {"wsId": "DigitalPlattform", "ndId": "90bdd4607ee84f4188ba", "meta01": "신한라이프", "meta02": "단체", "meta03": "연금",
     "meta04": None, "meta05": "무배당 신한 이율보증형 퇴직적립식보험", "meta06": "TRUE", "meta07": "20231018082250",
     "meta08": "99991231000000", "meta09": None,
     "meta10": _ROOT + "__etc/(무)신한 이율보증형 퇴직적립식보험_사업방법서_231018(1).pdf",
     "meta11": _ROOT + "__etc/(무)신한 이율보증형 퇴직적립식보험_약관_231018_v2.pdf", "meta12": "노출", "meta15": "3"},
]}}
# 판매기간 이력(selectAllListGoods): 목록 행을 뺀 지난 판매기간. 요약서가 없고, 상품코드가 비거나 다른 값이다
HISTORY = {"elHeader": HEADER, "elData": {"listCount": 0, "pageNum": 0, "totalPageCount": 1, "nodeInfoVoList": [
    {"wsId": "DigitalPlattform", "ndId": "a1", "meta01": "신한라이프", "meta02": "일반", "meta03": "보장", "meta04": "7000375",
     "meta05": ONE, "meta06": "TRUE", "meta07": "20260401000000", "meta08": "20260506235959",
     "meta10": _ROOT + "__etc/사업방법서_" + ONE + "_260401_v1.pdf",
     "meta11": _ROOT + "__etc/맞춤형약관_" + ONE + "_260317.pdf", "meta15": "15"},
    {"wsId": "DigitalPlattform", "ndId": "1f14eeee4ff44b5c8688", "meta01": "신한라이프", "meta02": "일반", "meta03": "보장",
     "meta05": ONE, "meta06": "TRUE", "meta07": "20251104000000", "meta08": "20251231235959",
     "meta10": _ROOT + "__etc/사업방법서_신한(간편가입)통합건강보험원(ONE)(무배당, 해약환급금 미지급형)_250401_v0.2_계약전알릴의무 수정.pdf",
     "meta11": _ROOT + "__etc/판매약관_" + ONE + "_대면_251104.pdf", "meta15": "15"},
    {"wsId": "DigitalPlattform", "ndId": "a3", "meta01": "신한라이프", "meta02": "일반", "meta03": "보장", "meta04": "7000317",
     "meta05": ONE, "meta06": "TRUE", "meta07": "20251014000000", "meta08": "20251103235959",
     "meta10": _ROOT + "__etc/사업방법서_x.pdf", "meta11": _ROOT + "__etc/판매약관_x.pdf", "meta15": "15"},
]}}
# 판매중지 목록(meta06 "FALSE")의 행. 판매중지 상품에도 요약서가 없다
STOPPED = {"elHeader": HEADER, "elData": {"listCount": 6, "pageNum": 1, "totalPageCount": 1, "nodeInfoVoList": [
    {"wsId": "DigitalPlattform", "ndId": "s1", "meta01": "신한라이프", "meta02": "일반", "meta03": "보장", "meta04": "7000377",
     "meta05": "신한(간편가입)통합건강보험 ONE더우먼(무배당, 해약환급금 미지급형)", "meta06": "FALSE",
     "meta07": "20260507000000", "meta08": "20260630235959", "meta09": None,
     "meta10": _ROOT + "__etc/사업방법서_y.pdf", "meta11": _ROOT + "__etc/판매약관_y.pdf", "meta15": "12"},
]}}
# 화면 스크립트(dp.common.js dp.Ajax.send)가 실패로 처리하는 꼴. 실제 응답으로 받아 본 적은 없다
ERROR = {"elHeader": {**HEADER, "resSuc": False, "resCode": "EL.ERROR", "resMsg": "오류",
                      "resMsgVo": {"msgId": "CDP00005", "basicMsgCtt": "잘못된 요청 입니다."}}, "elData": {}}
# 없는 서류 주소: 302로 /error.html에 넘어가고, 따라가면 상태 200 HTML이 온다 (본문은 줄였다)
ERROR_PAGE = b"<!DOCTYPE html>\n<html lang=\"ko\"><head><title>\xec\x98\xa4\xeb\xa5\x98</title>"


def test_list_rows():
    rows = shinhanlife.parse_products(LIST)
    one, core, group = rows
    assert (one.name, one.code, one.channel, one.kind, one.start, one.end) == (ONE, "7000375", "일반", "보장", "2026-08-04", None)
    assert one.selling and one.periods == 15 and one.company == "신한라이프"
    assert [d.kind for d in one.documents] == ["상품요약서", "사업방법서", "약관"]
    assert core.end is None and core.name.startswith("[순환계Plan]") and "약관" not in core.files
    assert group.code == "" and group.start == "2023-10-18" and "상품요약서" not in group.files
    assert shinhanlife.find_product(rows, ONE, "일반") is one
    assert shinhanlife.find_product(rows, ONE, "TM") is None
    assert shinhanlife.page_count(LIST) == 1


def test_history_periods_and_pick():
    past = shinhanlife.parse_products(HISTORY)
    assert [(p.start, p.end, p.code) for p in past] == [
        ("2026-04-01", "2026-05-06", "7000375"), ("2025-11-04", "2025-12-31", ""), ("2025-10-14", "2025-11-03", "7000317")]
    assert all("상품요약서" not in p.files for p in past)
    now = shinhanlife.parse_products(LIST)[0]
    periods = past + [now]
    assert shinhanlife.pick_period(periods).start == "2026-08-04"
    assert shinhanlife.pick_period(periods, "2026-05-01").start == "2026-04-01"
    assert shinhanlife.pick_period(periods, "2026-06-01") is None   # 이력 표본에 없는 기간
    stopped = shinhanlife.parse_products(STOPPED)[0]
    assert not stopped.selling and stopped.end == "2026-06-30"


def test_file_url_follows_page_script():
    doc = next(d for d in shinhanlife.parse_products(LIST)[0].documents if d.kind == "사업방법서")
    # 실제로 내려받기에 성공한 주소. /repo/DigitalPlattform → /bizxpress, encodeURI(빈칸과 한글은 바꾸고 쉼표와 괄호는 그대로)
    assert doc.url == (
        "https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/"
        "%EC%82%AC%EC%97%85%EB%B0%A9%EB%B2%95%EC%84%9C_%EC%8B%A0%ED%95%9C(%EA%B0%84%ED%8E%B8%EA%B0%80%EC%9E%85)"
        "%ED%86%B5%ED%95%A9%EA%B1%B4%EA%B0%95%EB%B3%B4%ED%97%98%20%EC%9B%90(ONE)(%EB%AC%B4%EB%B0%B0%EB%8B%B9,"
        "%20%ED%95%B4%EC%95%BD%ED%99%98%EA%B8%89%EA%B8%88%20%EB%AF%B8%EC%A7%80%EA%B8%89%ED%98%95)_260401_v1.pdf")
    assert doc.file_name == "사업방법서_" + ONE + "_260401_v1.pdf"
    # encodeURI는 대괄호를 바꾼다 (대괄호가 든 파일은 내려받아 보지 않았다)
    assert shinhanlife.file_url(_ROOT + "__media/a_[b].pdf").endswith("/bizxpress/cdh/cdhi/gd/pr/__media/a_%5Bb%5D.pdf")


def test_server_error_and_bad_shape_are_raised():
    with pytest.raises(ValueError, match="CDP00005"):
        shinhanlife.parse_products(ERROR)
    with pytest.raises(ValueError, match="nodeInfoVoList"):
        shinhanlife.parse_products({"elHeader": HEADER, "elData": {"listCount": 0}})
    with pytest.raises(ValueError, match="elHeader"):
        shinhanlife.parse_products({"result": []})
    with pytest.raises(ValueError):
        shinhanlife.parse_products([])


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else b""
            headers = {"Content-Type": "application/pdf" if isinstance(reply, bytes) and reply.startswith(b"%PDF")
                       else "text/html"}
            status_code = 200
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


def test_list_products_sends_what_the_page_sends():
    s = FakeSession([LIST])
    assert len(shinhanlife.list_products(s)) == 3
    method, url, kw = s.sent[0]
    assert (method, url) == ("POST", "https://www.shinhanlife.co.kr/co/wcms/nodeInfoListPage.pwkjson")
    body = json.loads(kw["data"])
    assert body["userHeader"] == {"scrnId": "cdhi0030", "appliDtptDutjCd": "DH"}
    assert body["elData"] == {"catId": "M160991914330045272", "pageSize": 1000, "pageIndex": 1, "method": "selectListGoods",
                              "meta02": "", "meta03": "", "title": "", "meta06": "TRUE", "scrnId": "cdhi0030"}
    assert kw["headers"]["X-AJAX-CALL"] == "true" and kw["headers"]["Proworks-Body"] == "Y"
    assert kw["headers"]["Content-Type"].startswith("application/json")
    # 판매중지: 화면과 탭 값이 바뀐다
    s = FakeSession([STOPPED])
    shinhanlife.list_products(s, selling=False, search="통합건강보험")
    el = json.loads(s.sent[0][2]["data"])["elData"]
    assert (el["meta06"], el["meta01"], el["title"], el["scrnId"]) == ("FALSE", "신한라이프", "통합건강보험", "cdhi0040t01")


def test_list_products_follows_page_count():
    first = {**LIST, "elData": {**LIST["elData"], "totalPageCount": 2}}
    s = FakeSession([first, STOPPED])
    assert len(shinhanlife.list_products(s, page_size=3)) == 4
    assert [json.loads(k["data"])["elData"]["pageIndex"] for _, _, k in s.sent] == [1, 2]


def test_list_documents_current_and_past():
    s = FakeSession([LIST])
    docs = shinhanlife.list_documents(s, ONE)
    assert [(d.kind, d.start) for d in docs] == [("상품요약서", "2026-08-04"), ("사업방법서", "2026-08-04"), ("약관", "2026-08-04")]
    assert json.loads(s.sent[0][2]["data"])["elData"]["title"] == ONE and len(s.sent) == 1
    s = FakeSession([LIST, HISTORY])
    docs = shinhanlife.list_documents(s, ONE, on="2026-05-01")
    assert [(d.kind, d.start, d.end) for d in docs] == [("사업방법서", "2026-04-01", "2026-05-06"), ("약관", "2026-04-01", "2026-05-06")]
    method, url, kw = s.sent[1]
    assert url == "https://www.shinhanlife.co.kr/co/wcms/nodeInfoList.pwkjson"
    el = json.loads(kw["data"])["elData"]
    assert (el["method"], el["meta05"], el["meta02"], el["meta03"], el["meta06"]) == ("selectAllListGoods", ONE, "일반", "보장", "TRUE")
    assert shinhanlife.list_documents(FakeSession([LIST]), "없는 상품") == []


def test_download_pdf_and_error_page():
    doc = shinhanlife.parse_products(LIST)[0].documents[1]
    s = FakeSession([b"%PDF-1.6 ..."])
    assert shinhanlife.download(s, doc).startswith(b"%PDF-")
    assert s.sent[0][0] == "GET" and s.sent[0][1] == doc.url
    with pytest.raises(ValueError, match="PDF가 아닌 응답"):
        shinhanlife.download(FakeSession([ERROR_PAGE]), doc)
