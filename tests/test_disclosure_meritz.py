import json

import pytest

try:
    from postlife.disclosure import meritz
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import meritz

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮김).
# 응답 header는 칸이 30개쯤 오지만 성공 여부(prcesResultDivCd)와 몇 칸만 남겼다. "#[E]" 암호값은 짧게 줄였다.
OK = {"prcesResultDivCd": "0", "encryDivCd": "0", "screenId": "/disclosure/product-announcement/product-list.do"}

# retrievePdList (판매상품 탭, srtSq "3"): 분류 목록과 그 분류의 상품명
PD_LIST = {"msg": {}, "header": OK, "body": {
    "pdList": [{"srtSq": 1, "cdNm": "자동차보험"}, {"srtSq": 3, "cdNm": "통합보험"}, {"srtSq": 7, "cdNm": "상해보험"}],
    "pdDtlList": [
        {"ttlNm": "무배당 알파Plus보장보험2610", "cmCommCd": "4104", "srtSq": 3, "nwPdCd": "6AFLT", "cdNm": "통합보험"},
        {"ttlNm": "무배당 메리츠 케어프리보험 M-Basket2610", "cmCommCd": "4104", "srtSq": 3, "nwPdCd": "6AFLU",
         "cdNm": "통합보험"}]}}
# srtSq "1" 응답: 자동차보험 상품코드는 숫자 다섯 자리다
PD_LIST_1 = {"msg": {}, "header": OK, "body": {
    "pdList": PD_LIST["body"]["pdList"],
    "pdDtlList": [{"ttlNm": "Readycar개인용자동차보험", "cmCommCd": "4102", "srtSq": 1, "nwPdCd": "71000", "cdNm": "자동차보험"}]}}
PD_LIST_7 = {"msg": {}, "header": OK, "body": {
    "pdList": PD_LIST["body"]["pdList"],
    "pdDtlList": [
        {"ttlNm": "무배당 메리츠 통합간편건강보험(세만기형)2610(통합간편심사형)", "cmCommCd": "4108", "srtSq": 7,
         "nwPdCd": "6AFMG", "cdNm": "상해보험"},
        {"ttlNm": "무배당 알파Plus보장보험2610", "cmCommCd": "4108", "srtSq": 7, "nwPdCd": "6AFLT", "cdNm": "상해보험"}]}}

# 서류 목록(검색, 상품명별, 분류별이 같은 꼴). 열린 기간은 종료일이 "-", 닫힌 기간은 8자리.
# 일반보험 행에는 file3(요약서)이 없다. 모든 칸에 "<칸>#[E]" 암호값이 함께 온다
OPEN_ROW = {"putupEdDdTm": "-", "putupEdDdTm#[E]": "rIac=", "bgnDt": "20261030", "putupStDdTm": "20261031",
            "ttlNm": "무배당 알파Plus보장보험2610", "ttlNm#[E]": "wvdR=", "ntbdDtlSeq": 31013, "ntbdDtlSeq#[E]": "uPaZ=",
            "file1": "/cu/ctl/202611020726309320051U.pdf", "file1#[E]": "xwTn+9/A==",
            "file2": "/cu/ctl/202611161038133160087U.pdf", "file2#[E]": "jpV5+8/B==",
            "file3": "/cu/ctl/202611161038133210089U.pdf", "file3#[E]": "w/BS+m/C=="}
CLOSED_ROW = {"putupEdDdTm": "20260925", "bgnDt": "20260910", "putupStDdTm": "20260910", "ttlNm": "개인용자동차보험",
              "ntbdDtlSeq": 30864, "file1": "/cu/car/202609101509591770045U.pdf", "file1#[E]": "Ys1=",
              "file2": "/cu/car/202609101509591770046U.pdf", "file2#[E]": "Ys2=",
              "file3": "/cu/car/202609101509591770047U.pdf", "file3#[E]": "Ys3="}
NO_SUMMARY_ROW = {"putupEdDdTm": "-", "bgnDt": "20260720", "putupStDdTm": "20260715", "ttlNm": "도난보험",
                  "ntbdDtlSeq": 30712, "file1": "/cu/ctf/202607200849304790421U.pdf", "file1#[E]": "Zz1=",
                  "file2": "/cu/ctf/202607200849304790422U.pdf", "file2#[E]": "Zz2=", "file3": ""}
SAL_LIST = {"msg": {}, "header": OK, "body": {"salPdList": [OPEN_ROW, CLOSED_ROW, NO_SUMMARY_ROW]}}
# 상품코드로 조회한 응답: 지난 판매기간과 지금 판매기간 (상품명은 개정 연월이 붙어 바뀌므로 판매기간이 하나뿐인 경우가 많다)
FOR_CODE = {"msg": {}, "header": OK, "body": {"salPdList": [
    {**CLOSED_ROW, "ttlNm": "무배당 알파Plus보장보험2610", "putupStDdTm": "20261001", "putupEdDdTm": "20261030",
     "ntbdDtlSeq": 31000},
    OPEN_ROW]}}
EMPTY = {"msg": {}, "header": OK, "body": {"salPdList": []}}
# 화면 스크립트(salPdLst.js, http.js)가 처리하는 오류 꼴. 실제 응답으로 받아 본 적은 없다
ERROR = {"msg": {"standCd": "FCGCMH00004", "standMsg": "서비스 이용 시간이 아닙니다."}, "header": {"prcesResultDivCd": "1"}}
# 웹 방화벽 차단 화면(상태 200, text/html). 다른 세션의 암호값으로 내려받기 확인을 보냈을 때 받았다
BLOCKED = b"<br>\r\n<br>\r\n<center>\r\n<h2>\r\nWeb firewall security policies have been blocked.\r\n</h2>"


def test_categories_and_products():
    cats = meritz.parse_categories(PD_LIST)
    assert [(c.seq, c.name) for c in cats] == [("1", "자동차보험"), ("3", "통합보험"), ("7", "상해보험")]
    products = meritz.parse_products(PD_LIST, seq="3")
    assert [(p.code, p.category, p.category_code) for p in products] == [("6AFLT", "통합보험", "4104"),
                                                                        ("6AFLU", "통합보험", "4104")]
    assert products[0].name == "무배당 알파Plus보장보험2610" and products[0].selling
    assert meritz.parse_products(PD_LIST, seq="7") == []   # 화면처럼 요청한 분류의 행만 남긴다


def test_periods_open_closed_and_missing_summary():
    rows = meritz.parse_periods(SAL_LIST)
    assert [(p.seq, p.start, p.end, p.posted) for p in rows] == [
        ("31013", "2026-10-31", None, "2026-10-30"), ("30864", "2026-09-10", "2026-09-25", "2026-09-10"),
        ("30712", "2026-07-15", None, "2026-07-20")]
    assert rows[0].open and not rows[1].open
    assert set(rows[0].files) == {"약관", "사업방법서", "상품요약서"} and set(rows[2].files) == {"약관", "사업방법서"}
    assert rows[0].tokens["상품요약서"] == "w/BS+m/C==" and rows[0].code == ""
    assert meritz.parse_periods(EMPTY) == []


def test_documents_and_pick():
    periods = meritz.parse_periods(FOR_CODE, code="6AFLT")
    assert meritz.pick_period(periods).seq == "31013"
    assert meritz.pick_period(periods, "2026-10-15").seq == "31000"
    assert meritz.pick_period(periods, "2026-09-30") is None
    docs = meritz.pick_period(periods).documents()
    assert [d.kind for d in docs] == ["약관", "사업방법서", "상품요약서"]
    summary = docs[2]
    assert (summary.code, summary.file_name, summary.token) == ("6AFLT", "202611161038133210089U.pdf", "w/BS+m/C==")
    assert summary.download_name == "무배당 알파Plus보장보험2610요약서.pdf"
    found = meritz.parse_periods(SAL_LIST)[0]
    assert {d.code for d in meritz.documents_of(found, "6AFLT")} == {"6AFLT"}


def test_server_error_and_bad_shape_are_raised():
    with pytest.raises(ValueError, match="FCGCMH00004"):
        meritz.parse_periods(ERROR)
    with pytest.raises(ValueError):
        meritz.parse_periods({"result": []})
    with pytest.raises(ValueError):
        meritz.parse_periods({"msg": {}, "header": OK, "body": {"salPdList": "x"}})


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else json.dumps(reply).encode()
            headers = {"Content-Type": "application/octet-stream;charset=UTF-8" if isinstance(reply, bytes)
                       else "application/json;charset=UTF-8"}
            encoding = None

            def raise_for_status(self):
                pass

            def json(self):
                if isinstance(reply, bytes):
                    return json.loads(reply.decode("utf-8", errors="replace"))
                return reply

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def test_list_documents_sends_what_the_page_sends():
    s = FakeSession([FOR_CODE])
    docs = meritz.list_documents(s, "6AFLT")
    assert [d.kind for d in docs] == ["약관", "사업방법서", "상품요약서"] and docs[0].start == "2026-10-31"
    method, url, kw = s.sent[0]
    assert method == "POST" and url.startswith("https://www.meritzfire.com/json.smart?v=")
    sent = json.loads(kw["data"])
    assert sent["body"] == {"notfYn": "Y", "nwPdCd": "6AFLT"}
    assert sent["header"]["rcvmsgSrvId"] == "f.cg.he.cu.ua.o.bc.PbanBc.retrieveSalPdListForCdNm"
    assert sent["header"]["encryDivCd"] == "0" and len(sent["header"]["teleMsgReqDttm"]) == 17
    assert kw["headers"]["Content-Type"].startswith("application/json")


def test_search_and_category_walk():
    s = FakeSession([SAL_LIST])
    rows = meritz.search_products(s, "건강", selling=False)
    sent = json.loads(s.sent[0][2]["data"])
    assert sent["body"] == {"notfYn": "N", "keyWord": "건강"} and sent["header"]["lowrnkScreenId"] == "/03"
    assert sent["header"]["rcvmsgSrvId"].endswith(".retrieveSalPdSchList") and not rows[0].selling
    # 첫 요청(srtSq "1")에서 분류 목록을 얻고, 고른 분류만 하나씩 더 묻는다. 두 분류에 나온 상품코드는 한 번만
    s = FakeSession([PD_LIST_1, PD_LIST, PD_LIST_7])
    products = meritz.list_products(s, categories=("통합보험", "상해보험"))
    assert [p.code for p in products] == ["6AFLT", "6AFLU", "6AFMG"]
    assert [json.loads(k["data"])["body"] for _, _, k in s.sent] == [
        {"notfYn": "Y", "srtSq": "1"}, {"notfYn": "Y", "srtSq": "3"}, {"notfYn": "Y", "srtSq": "7"}]


def test_html_instead_of_json_is_raised():
    with pytest.raises(ValueError, match="JSON이 아님"):
        meritz.search_products(FakeSession([BLOCKED]), "건강")


def test_download_two_steps_and_non_pdf():
    doc = meritz.parse_periods(FOR_CODE, code="6AFLT")[1].documents()[2]
    s = FakeSession([{"resultMsg": ""}, b"%PDF-1.6 ..."])
    assert meritz.download(s, doc).startswith(b"%PDF-")
    (m1, url1, kw1), (m2, url2, kw2) = s.sent
    assert (m1, url1, m2, url2) == ("POST", "https://www.meritzfire.com/hp/fileDownload.do",
                                    "GET", "https://www.meritzfire.com/hp/fileDownload.do")
    # 화면처럼 path와 id 둘 다 암호값, 이름의 괄호는 미리 %28 %29로 바꾼다
    assert kw1["data"] == {"path": "w/BS+m/C==", "id": "w/BS+m/C==", "orgFileName": "무배당 알파Plus보장보험2610요약서.pdf",
                           "check": "Y"}
    assert kw2["params"]["check"] == "N" and kw2["params"]["id"] == "w/BS+m/C=="
    assert meritz._uri_param("암보험(세만기형)2610, A/B요약서.pdf") == "암보험%28세만기형%292610%2C A／B요약서.pdf"
    with pytest.raises(ValueError, match="JSON이 아님"):          # 다른 세션의 암호값: 방화벽 차단 화면
        meritz.download(FakeSession([BLOCKED]), doc)
    with pytest.raises(ValueError, match="거절"):   # 화면은 resultMsg가 비지 않으면 알림을 띄운다. 실제 문구는 받아 본 적 없다
        meritz.download(FakeSession([{"resultMsg": "(거절 문구)"}]), doc)
    with pytest.raises(ValueError, match="PDF가 아닌"):
        meritz.download(FakeSession([{"resultMsg": ""}, b"<html>error</html>"]), doc)
    with pytest.raises(ValueError, match="암호값이 없음"):
        meritz.download(FakeSession([]), meritz.Document("1", "x", "약관", "/cu/x.pdf"))
