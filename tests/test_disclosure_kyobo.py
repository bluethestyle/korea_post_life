import json

import pytest

try:
    from postlife.disclosure import kyobo
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import kyobo

OK = {"code": "SUCCESS", "message": "정상처리되었습니다."}
# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 칸을 줄여 옮김. 담당자 이름, 직원 번호 칸은 뺐다)
# 상품 목록: 대면 상품, 판매중 목록에 있지만 판매기간과 서류가 없는 다이렉트판, 중도부가특약 행
LIST = {"header": OK, "body": {"listCnt": 3, "pageInfo": {"startNumber": 1, "totLstCnt": 3, "endNumber": 1,
                                                           "scrCurPage": 1, "totPageCnt": 1}, "list": [
    {"dgtPdtAtrSeqtId": 37288, "dgtPdtCd": "1001031", "dgtPdtAtrNm": "교보마이플랜건강보험Ⅱ (무배당)",
     "dgtPdtAtrMclCd": "PAMS04", "dgtPdtAtrSmclCd": "02", "saleYn": "Y", "dgtMseAddiPsYn": "N",
     "saleStDt": "2026-08-26", "saleEdDt": None, "apStDtm": "2026-08-26", "apEdDtm": None, "maxSlsTerm": None,
     "a1": "ZjE2MDZkYWUt_교보마이플랜건강보험Ⅱ (무배당) 상품요약서(2026.08.26).pdf",
     "a2": "MWM0ZjZjZjkt_교보마이플랜건강보험Ⅱ (무배당) 공시용 통합약관(2026.08.26).pdf",
     "a3": "YzVkZTU0ZmIt_교보마이플랜건강보험Ⅱ (무배당) 사업방법서(2026.08.26).pdf", "a4": None},
    {"dgtPdtAtrSeqtId": 37289, "dgtPdtCd": "1001032", "dgtPdtAtrNm": "교보마이플랜건강보험Ⅱ [D](무배당)",
     "dgtPdtAtrMclCd": "PAMS06", "dgtPdtAtrSmclCd": "02", "saleYn": "Y", "dgtMseAddiPsYn": "N",
     "saleStDt": None, "saleEdDt": None, "a1": None, "a2": None, "a3": None},
    {"dgtPdtAtrSeqtId": 33706, "dgtPdtCd": "1001027", "dgtPdtAtrNm": "교보평생건강보험 PLUS (무배당) 중도부가특약",
     "dgtPdtAtrMclCd": "PAMS04", "dgtPdtAtrSmclCd": "04", "saleYn": "Y", "dgtMseAddiPsYn": "Y",
     "saleStDt": "2026-02-25", "a1": None, "a2": "ZTJmZDVjMjAt_3. 교보평생건강보험 PLUS (무배당) 중도부가 통합약관.pdf", "a3": None},
]}}
# 판매여부 '전체'로 검색한 응답의 판매중지 행. saleStDt가 마지막 판매기간(2026-06-29~2026-08-25)의 다음날로 온다
STOPPED = {"header": OK, "body": {"listCnt": 1, "pageInfo": {"totPageCnt": 1}, "list": [
    {"dgtPdtAtrSeqtId": 21614, "dgtPdtCd": "1001031", "dgtPdtAtrNm": "교보마이플랜건강보험 (무배당)",
     "dgtPdtAtrMclCd": "PAMS04", "dgtPdtAtrSmclCd": "02", "saleYn": "N", "dgtMseAddiPsYn": "N",
     "saleStDt": "2026-08-26", "saleEdDt": None, "apStDtm": "2026-06-29", "apEdDtm": "2026-08-25",
     "a1": "YjU0ZjQ3OTYt_교보마이플랜건강보험 (무배당) 상품요약서(2026.06.29).pdf"}]}}
# 서류 목록: 판매기간(list)과 파일(list2)이 같은 순서로 온다. 최근 판매기간이 먼저이고 상품요약서는 거기에만 있다
DETAIL = {"header": OK, "body": {
    "list": [{"dgtPdtPdSeqtId": 9891, "dgtPdtAtrDvCd": "M", "dgtPdtAtrSeq": 21614,
              "saleStDt": "2026-06-29", "saleEdDt": "2026-08-25"},
             {"dgtPdtPdSeqtId": 9762, "dgtPdtAtrDvCd": "M", "dgtPdtAtrSeq": 21614,
              "saleStDt": "2026-04-01", "saleEdDt": "2026-06-28"},
             {"dgtPdtPdSeqtId": 8609, "dgtPdtAtrDvCd": "M", "dgtPdtAtrSeq": 21614,
              "saleStDt": "2024-05-10", "saleEdDt": "2024-08-31"}],
    "list2": [{"real01": "교보마이플랜건강보험 (무배당) 상품요약서(2026.06.29).pdf",
               "temp01": "YjU0ZjQ3OTYt_교보마이플랜건강보험 (무배당) 상품요약서(2026.06.29).pdf",
               "real02": "1001031_교보마이플랜건강보험 (무배당)_26.6.29 공시용 통합약관.pdf",
               "temp02": "YjBkMzA3MTkt_1001031_교보마이플랜건강보험 (무배당)_26.6.29 공시용 통합약관.pdf",
               "real03": "02.교보마이플랜건강보험 (무배당) 사업방법서(2026.06.29).pdf",
               "temp03": "YTViZmEyZjEt_02.교보마이플랜건강보험 (무배당) 사업방법서(2026.06.29).pdf",
               "temp04": None, "temp05": None},
              {"real01": None, "temp01": None,
               "real02": "1001031_교보마이플랜건강보험 (무배당)_2026.4.1 공시용 통합약관.pdf",
               "temp02": "NmM1YWI3NDAt_1001031_교보마이플랜건강보험 (무배당)_2026.4.1 공시용 통합약관.pdf",
               "real03": "02.교보마이플랜건강보험 (무배당) 사업방법서(2026.01.01).pdf",
               "temp03": "NjI2NDVmMjAt_02.교보마이플랜건강보험 (무배당) 사업방법서(2026.01.01).pdf"},
              {"real02": "1001031_교보마이플랜건강보험 (무배당)_2024.05.11 공시용 통합약관.pdf",
               "temp02": "ZjE2ZmMyMTAt_1001031_교보마이플랜건강보험 (무배당)_2024.05.11 공시용 통합약관.pdf",
               "real03": "교보마이플랜건강보험 (무배당) 사업방법서(2024.05.10).pdf",
               "temp03": "MDJmZjJkYWUt_교보마이플랜건강보험 (무배당) 사업방법서(2024.05.10).pdf"}]}}
# 판매 중인 기간 하나 (종료일 없음)
CURRENT = {"header": OK, "body": {
    "list": [{"dgtPdtPdSeqtId": 9935, "dgtPdtAtrSeq": 37288, "saleStDt": "2026-08-26", "saleEdDt": None}],
    "list2": [{"real01": "교보마이플랜건강보험Ⅱ (무배당) 상품요약서(2026.08.26).pdf",
               "temp01": "ZjE2MDZkYWUt_교보마이플랜건강보험Ⅱ (무배당) 상품요약서(2026.08.26).pdf",
               "real03": "교보마이플랜건강보험Ⅱ (무배당) 사업방법서(2026.08.26).pdf",
               "temp03": "YzVkZTU0ZmIt_교보마이플랜건강보험Ⅱ (무배당) 사업방법서(2026.08.26).pdf"}]}}
# 잘못된 요청: 상태 200에 header.code FAIL, body null (숫자가 아닌 번호로 받아 본 응답)
FAIL = {"header": {"code": "FAIL", "message": "죄송합니다. 처리 중 오류가 발생하였습니다."}, "body": None}
# 없는 파일: 상태 404와 JSON
MISSING = b'{"header":{"code":"404","message":"FAIL"},"body":null}'


def test_products_from_list():
    products = kyobo.parse_products(LIST)
    assert [(p.seq, p.code, p.selling, p.rider_addon) for p in products] == [
        ("37288", "1001031", True, False), ("37289", "1001032", True, False), ("33706", "1001027", True, True)]
    main = products[0]
    assert main.label == "보장성보험(암/건강)" and main.start == "2026-08-26"
    assert main.files["상품요약서"].endswith("상품요약서(2026.08.26).pdf") and set(main.files) == {"상품요약서", "약관", "사업방법서"}
    # 판매중 목록에 있어도 판매기간과 서류가 없는 행이 있다
    assert products[1].start is None and products[1].files == {} and products[1].label == "통신판매전용상품"
    assert products[2].files == {"약관": "ZTJmZDVjMjAt_3. 교보평생건강보험 PLUS (무배당) 중도부가 통합약관.pdf"}
    stopped = kyobo.parse_products(STOPPED)[0]
    assert not stopped.selling and stopped.code == main.code   # 세대가 바뀐 상품이 상품코드를 같이 쓴다
    assert kyobo.page_count(LIST) == 1


def test_documents_by_period():
    product = kyobo.parse_products(STOPPED)[0]
    docs = kyobo.parse_documents(DETAIL, product)
    assert [(d.period, d.kind) for d in docs] == [
        ("9891", "상품요약서"), ("9891", "약관"), ("9891", "사업방법서"),
        ("9762", "약관"), ("9762", "사업방법서"), ("8609", "약관"), ("8609", "사업방법서")]
    first = docs[0]
    assert (first.seq, first.start, first.end, first.name) == ("21614", "2026-06-29", "2026-08-25", "교보마이플랜건강보험 (무배당)")
    assert first.real_name == "교보마이플랜건강보험 (무배당) 상품요약서(2026.06.29).pdf"
    assert first.file_name.startswith("YjU0ZjQ3OTYt_")
    assert [d.kind for d in kyobo.pick_version(docs)] == ["상품요약서", "약관", "사업방법서"]
    assert {d.period for d in kyobo.pick_version(docs, "2026-05-01")} == {"9762"}
    assert kyobo.pick_version(docs, "2024-12-01") == []
    current = kyobo.parse_documents(CURRENT)
    assert [(d.kind, d.end, d.seq) for d in current] == [("상품요약서", None, "37288"), ("사업방법서", None, "37288")]


def test_open_end_marker_and_pension_kinds():
    # 화면 스크립트가 '종료일 없음'으로 다루는 값(실제 응답에서 본 적은 없다)과 퇴직연금의 첫 칸(계약서)
    body = {"header": OK, "body": {"list": [{"dgtPdtPdSeqtId": 1, "dgtPdtAtrSeq": 148, "saleStDt": "2026-10-01",
                                             "saleEdDt": "0001-01-01 BC"}],
                                   "list2": [{"temp01": "a_계약서.pdf", "temp02": "b_약관.pdf"}]}}
    pension = kyobo.Product("148", "x", "교보 확정기여형 퇴직연금 운용관리계약", True, "PAMS08", "01")
    docs = kyobo.parse_documents(body, pension)
    assert [(d.kind, d.end, d.real_name) for d in docs] == [("계약서", None, "a_계약서.pdf"), ("약관", None, "b_약관.pdf")]


def test_server_error_and_bad_shape_are_raised():
    with pytest.raises(ValueError, match="FAIL"):
        kyobo.parse_documents(FAIL)
    with pytest.raises(ValueError, match="FAIL"):
        kyobo.parse_products(FAIL)
    with pytest.raises(ValueError):
        kyobo.parse_products({"list": []})
    with pytest.raises(ValueError, match="수가 다름"):
        kyobo.parse_documents({"header": OK, "body": {"list": DETAIL["body"]["list"], "list2": []}})


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)
        status = 404 if reply == MISSING else 200

        class R:
            status_code = status
            content = reply if isinstance(reply, bytes) else b""
            headers = {"Content-Type": "application/pdf" if isinstance(reply, bytes) and reply.startswith(b"%PDF")
                       else "application/json"}
            encoding = None

            def raise_for_status(self):
                if status >= 400:
                    raise AssertionError("download는 상태 코드보다 본문을 먼저 본다")

            def json(self):
                return reply

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def test_search_sends_what_the_page_sends_and_walks_pages():
    page1 = json.loads(json.dumps(LIST))
    page1["body"]["pageInfo"]["totPageCnt"] = 2
    s = FakeSession([page1, STOPPED])
    products = kyobo.search_products(s, "마이플랜", selling=None, page_size=3)
    assert len(products) == 4 and [m for m, _, _ in s.sent] == ["POST", "POST"]
    url, kw = s.sent[0][1], s.sent[0][2]
    assert url == "https://www.kyobo.com/dtc/product-official/find-allProductSearch"
    assert kw["headers"]["Content-Type"].startswith("application/json") and kw["headers"]["_NOW_PAGE_CD"] == "PDSDRNL9001PS"
    assert json.loads(kw["data"]) == {"dgtPdtAtrDvCd": "M", "dgtPdtAtrLclCd": "", "dgtPdtAtrMclCd": "99",
                                      "dgtPdtAtrSmclCd": "99", "saleYn": "99", "dgtMseAddiPsYn": "", "searchTxt": "마이플랜",
                                      "currentPage": 1, "pagePerSize": 3, "pageNumber": 10, "deviceDv": "pc"}
    assert "마이플랜".encode() in kw["data"]   # 화면의 JSON.stringify처럼 한글을 그대로 보낸다
    assert json.loads(s.sent[1][2]["data"])["currentPage"] == 2
    s = FakeSession([LIST])
    kyobo.list_products(s)
    assert json.loads(s.sent[0][2]["data"])["saleYn"] == "Y"


def test_list_documents_sends_row_number():
    s = FakeSession([DETAIL])
    product = kyobo.parse_products(STOPPED)[0]
    docs = kyobo.list_documents(s, product)
    assert {d.period for d in docs} == {"9891"}
    assert s.sent[0][1] == "https://www.kyobo.com/dtc/product-official/find-allProductSearchDetail"
    assert json.loads(s.sent[0][2]["data"]) == {"dgtPdtPdSeqtId": "21614"}


def test_download_url_and_non_pdf():
    doc = kyobo.parse_documents(CURRENT)[0]
    s = FakeSession([b"%PDF-1.5 ..."])
    assert kyobo.download(s, doc).startswith(b"%PDF-")
    # 실제로 내려받기에 성공한 주소와 같은 꼴 (encodeURI: 한글과 빈칸은 바꾸고 괄호는 그대로)
    assert s.sent[0][:2] == ("GET", "https://www.kyobo.com/file/ajax/download?fName=/dtc/pdf/mm/ZjE2MDZkYWUt_"
                                    "%EA%B5%90%EB%B3%B4%EB%A7%88%EC%9D%B4%ED%94%8C%EB%9E%9C%EA%B1%B4%EA%B0%95%EB%B3%B4%ED%97%98"
                                    "%E2%85%A1%20(%EB%AC%B4%EB%B0%B0%EB%8B%B9)%20%EC%83%81%ED%92%88%EC%9A%94%EC%95%BD%EC%84%9C"
                                    "(2026.08.26).pdf")
    with pytest.raises(ValueError, match="상태 404"):   # 없는 파일: 상태 404와 JSON
        kyobo.download(FakeSession([MISSING]), doc)
    assert kyobo.file_url("a&b+c#d.pdf").endswith("a%26b%2Bc%23d.pdf")
