from urllib.parse import parse_qsl

import pytest

try:
    from postlife.disclosure import kblife
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import kblife

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮기고, 같은 꼴의 칸은 줄였다)
PAGING_ONE = {"pgSize": 200, "firstPgNo": 0, "prevPgNo": 1, "startPgNo": 1, "currentPgNo": 1, "endPgNo": 1,
              "nextPgNo": 1, "finalPgNo": 1, "pageTotalCnt": 160, "pgGroupCnt": 10}
_COMMON = {"PER_TYPE": "P", "PAGE": 1, "TOTALCOUNT": 160}
# 판매상품 탭(tabType=1). 열린 판매기간은 "2026/10/01 ~ "이고 종료일 칸이 없다. 지난 판매기간에도 요약서 경로가 있기도 하다
NAME_GEN = "KB 딱좋은 요즘 건강보험 무배당(일반심사형)(해약환급금 미지급형)(계약자적립액 미지급형)"
NAME_RENEW = "KB 딱좋은 요즘 건강보험 무배당(갱신형)(일반심사형)(해약환급금 미지급형)"
NAME_RIDER = "무배당 암∙뇌졸중∙급성심근경색증 진단특약(해약환급금 미지급형)"
SELLING = {"pagingVO": PAGING_ONE, "list": [
    {**_COMMON, "P_CODE": "335000106", "UPFILE": "/channel/product/explain/5A76.pdf", "TYPENAME": "3" + NAME_GEN,
     "CNT": 2, "SALE_DATE": "2026/10/01 ~ ", "UPFILE1": "/channel/product/explain/F019.pdf",
     "UPFILE2": "/channel/product/terms/24A9.pdf", "HEADER": 1, "PCODE_GBN": "S", "RNK": 125, "NAME": NAME_GEN,
     "ORDER1": "3", "SEQNO": "501619094", "RNUM": 473, "TYPE_CODE": "INS03", "TYPE": "보장"},
    {**_COMMON, "P_CODE": "335000106", "PROD_SALE_END_DATE": "20260930", "UPFILE": "/channel/product/explain/BBA0.pdf",
     "TYPENAME": "3" + NAME_GEN, "CNT": 2, "SALE_DATE": "2026/07/01 ~ 2026/09/30",
     "UPFILE1": "/channel/product/explain/861A.pdf", "UPFILE2": "/channel/product/terms/6A04.pdf", "HEADER": 2,
     "PCODE_GBN": "0", "RNK": 125, "NAME": NAME_GEN, "ORDER1": "3", "SEQNO": "501618132", "RNUM": 474,
     "TYPE_CODE": "INS03", "TYPE": "보장"},
    # 개정하면서 상품코드 끝자리가 바뀐 판매기간 (437200106 ← 337200105)
    {**_COMMON, "P_CODE": "437200106", "SALE_DATE": "2026/10/01 ~ ", "HEADER": 1, "CNT": 7, "SEQNO": "501619073",
     "NAME": NAME_RENEW, "UPFILE": "/channel/product/explain/DCB5.pdf", "UPFILE1": "/channel/product/explain/8D62.pdf",
     "UPFILE2": "/channel/product/terms/9DBC.pdf", "TYPE_CODE": "INS03", "TYPE": "보장"},
    {**_COMMON, "P_CODE": "337200105", "SALE_DATE": "2026/05/01 ~ 2026/06/30", "PROD_SALE_END_DATE": "20260630",
     "HEADER": 4, "CNT": 7, "SEQNO": "501617479", "NAME": NAME_RENEW, "UPFILE1": "/channel/product/explain/5B51.pdf",
     "UPFILE2": "/channel/product/terms/07D2.pdf", "TYPE_CODE": "INS03", "TYPE": "보장"},
    # 약관 칸에 단추가 하나 더 붙는 특약(UPFILE3)
    {**_COMMON, "P_CODE": "803003106", "TYPENAME": "10" + NAME_RIDER, "CNT": 2, "SALE_DATE": "2026/07/01 ~ ",
     "UPFILE1": "/channel/product/explain/7F23.pdf", "UPFILE2": "/channel/product/terms/599F.pdf", "HEADER": 1,
     "PCODE_GBN": "S", "RNK": 49, "UPFILE3": "/channel/product/terms/115D.pdf", "NAME": NAME_RIDER, "ORDER1": "10",
     "SEQNO": "501618377", "RNUM": 222, "TYPE_CODE": "INS10", "TYPE": "특약"},
    # 제도성 특약에는 상품코드가 "NULL"인 것도 있다
    {**_COMMON, "P_CODE": "NULL", "CNT": 1, "SALE_DATE": "2026/04/01 ~ ", "UPFILE1": "/channel/product/explain/53D4.pdf",
     "UPFILE2": "/channel/product/terms/7FA1.pdf", "HEADER": 1, "NAME": "보험료 납입유예특약", "SEQNO": "501617385",
     "TYPE_CODE": "INS10", "TYPE": "특약"},
]}
# 판매중지 탭(tabType=2). 판매기간에 빈칸이 없고, 요약서(UPFILE) 칸이 없다. pageSize 20이면 상품 40개가 두 쪽이다
STOPPED_PAGE1 = {"pagingVO": {**PAGING_ONE, "pgSize": 20, "endPgNo": 2, "nextPgNo": 2, "finalPgNo": 2, "pageTotalCnt": 40},
                 "list": [{"P_CODE": "338800104", "PROD_SALE_END_DATE": "20260630", "PER_TYPE": "P", "CNT": 3,
                           "SALE_DATE": "2026/04/01~2026/06/30", "UPFILE1": "/channel/product/explain/8A23.pdf",
                           "UPFILE2": "/channel/product/terms/8655.pdf", "HEADER": 1, "PAGE": 1, "PCODE_GBN": "S",
                           "RNK": 1, "NAME": "KB 3.10.5 딱좋은 초경증 건강보험 무배당(간편심사형)", "ORDER1": "3",
                           "SEQNO": "501617372", "RNUM": 1, "TYPE_CODE": "INS03", "TYPE": "보장", "TOTALCOUNT": 40}]}
STOPPED_PAGE2 = {"pagingVO": {**STOPPED_PAGE1["pagingVO"], "currentPgNo": 2},
                 "list": [{**STOPPED_PAGE1["list"][0], "SEQNO": "501616705", "HEADER": 2, "PAGE": 2,
                           "SALE_DATE": "2026/02/09~2026/03/31", "PROD_SALE_END_DATE": "20260331"}]}
EMPTY = {"pagingVO": {**PAGING_ONE, "finalPgNo": 0, "endPgNo": 0, "pageTotalCnt": 0}, "list": []}


def test_periods_dates_files_and_codes():
    periods = kblife.parse_periods(SELLING)
    assert [(p.seqno, p.code, p.start, p.end) for p in periods[:4]] == [
        ("501619094", "335000106", "2026-10-01", None), ("501618132", "335000106", "2026-07-01", "2026-09-30"),
        ("501619073", "437200106", "2026-10-01", None), ("501617479", "337200105", "2026-05-01", "2026-06-30")]
    assert set(periods[0].files) == {"상품요약서", "사업방법서", "약관"}
    assert set(periods[3].files) == {"사업방법서", "약관"}
    assert periods[4].files["약관 추가1"].endswith("115D.pdf") and periods[4].category == "특약"
    assert periods[0].category_code == "INS03" and not periods[0].group_policy
    stopped = kblife.parse_periods(STOPPED_PAGE1)
    assert (stopped[0].start, stopped[0].end) == ("2026-04-01", "2026-06-30") and "상품요약서" not in stopped[0].files


def test_products_group_by_name_and_pick_period():
    products = kblife.group_products(kblife.parse_periods(SELLING))
    assert [p.name for p in products] == [NAME_GEN, NAME_RENEW, NAME_RIDER, "보험료 납입유예특약"]
    gen, renew = products[0], products[1]
    assert (gen.code, gen.start, gen.open) == ("335000106", "2026-10-01", True)
    assert renew.code == "437200106"           # 가장 최근 판매기간의 코드
    assert kblife.pick_period(gen.periods).seqno == "501619094"
    assert kblife.pick_period(gen.periods, "2026-08-15").seqno == "501618132"
    assert kblife.pick_period(gen.periods, "2026-06-30") is None
    assert kblife.page_info(SELLING) == (1, 1, 160)


def test_documents_use_seqno_and_box_not_file_path():
    period = kblife.parse_periods(SELLING)[0]
    docs = {d.kind: d for d in kblife.documents_of(period)}
    # 실제로 PDF를 받은 주소와 같은 꼴 (요약서 0, 사업방법서 1, 약관은 product-terms의 2)
    assert docs["상품요약서"].url == "https://www.kblife.co.kr/api/archive/archives/download/product-explain/501619094/0"
    assert docs["사업방법서"].url.endswith("/product-explain/501619094/1")
    assert docs["약관"].url.endswith("/product-terms/501619094/2")
    rider = {d.kind: d for d in kblife.documents_of(kblife.parse_periods(SELLING)[4])}
    assert rider["약관 추가1"].url.endswith("/product-terms/501618377/8")


def test_bad_shape_is_raised():
    with pytest.raises(ValueError):
        kblife.parse_periods({"pagingVO": PAGING_ONE})
    with pytest.raises(ValueError):
        kblife.parse_periods(["not", "a", "dict"])
    with pytest.raises(ValueError):
        kblife.page_info({"list": []})
    assert kblife.parse_periods(EMPTY) == []


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)

        class R:
            status_code = 200
            content = reply if isinstance(reply, bytes) else b""
            # 없는 파일은 상태 200, Content-Type 없음, 본문 0바이트로 왔다
            headers = {"Content-Type": "application/pdf"} if isinstance(reply, bytes) and reply else {}
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


def test_list_sends_what_the_page_sends_and_follows_pages():
    s = FakeSession([STOPPED_PAGE1, STOPPED_PAGE2])
    periods = kblife.list_periods(s, kblife.STOPPED, name="딱좋은", page_size=20)
    assert [p.seqno for p in periods] == ["501617372", "501616705"]
    (m1, url1, kw1), (_, _, kw2) = s.sent
    assert (m1, url1) == ("POST", "https://www.kblife.co.kr/customer-common/API/productList1.do")
    assert kw1["headers"]["Content-Type"].startswith("application/x-www-form-urlencoded")
    assert kw1["data"].decode() == "pageSize=20&paGroupCnt=10&pageIndex=1&tabType=2&srchType=&pdNm=%EB%94%B1%EC%A2%8B%EC%9D%80"
    assert dict(parse_qsl(kw2["data"].decode(), keep_blank_values=True))["pageIndex"] == "2"


def test_list_documents_keeps_exact_name_only():
    s = FakeSession([SELLING])
    docs = kblife.list_documents(s, NAME_GEN, on="2026-08-01")
    assert {d.seqno for d in docs} == {"501618132"} and {d.kind for d in docs} == {"상품요약서", "사업방법서", "약관"}
    sent = dict(parse_qsl(s.sent[0][2]["data"].decode(), keep_blank_values=True))
    # 괄호가 든 이름을 그대로 보내면 서버가 0건을 돌려준다. 괄호 앞까지만 보낸다
    assert sent == {"pageSize": "200", "paGroupCnt": "10", "pageIndex": "1", "tabType": "1", "srchType": "",
                    "pdNm": "KB 딱좋은 요즘 건강보험 무배당"}
    assert kblife.list_documents(FakeSession([SELLING]), "KB 딱좋은 요즘 건강보험 무배당") == []   # 일부만 같은 이름
    assert kblife.keyword_of(NAME_RIDER) == NAME_RIDER.split("(")[0] and kblife.keyword_of("(무)상품") == ""


def test_download_pdf_and_empty_body():
    doc = kblife.documents_of(kblife.parse_periods(SELLING)[0])[0]
    s = FakeSession([b"%PDF-1.7 ..."])
    assert kblife.download(s, doc).startswith(b"%PDF-")
    assert s.sent[0][:2] == ("GET", "https://www.kblife.co.kr/api/archive/archives/download/product-explain/501619094/0")
    with pytest.raises(ValueError, match="0바이트"):
        kblife.download(FakeSession([b""]), doc)
