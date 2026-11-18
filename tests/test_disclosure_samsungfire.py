try:
    from postlife.disclosure import samsungfire
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import samsungfire

# 2026-11-18에 상품공시에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮김)
LIST = {"sfmi.nexus.b2c.currentStage": "P", "responseMessage": {
    "header": {"tranId": "VH.HDIF0103", "longTran": False, "resultCode": "0000",
               "perfLog": {"fwProcTime": 2, "bizProcTime": 317, "reqMsgSize": 0}},
    "body": {"result": "S", "data": {"list": [
        {"prdName": "무배당 삼성화재 건강보험 THE FIT 파트너(2610.1)(일반형)", "prdGun": "장기", "prdGb": "건강",
         "saleChannel": "대면", "prdCode": "ZPB446030", "jongGb": "0", "saleStDt": "20261012", "saleEnDt": "99991231",
         "prdfilename1": "/publication/pdf/ZPB446030_0_20261012_file1.pdf",
         "prdfilename2": "/publication/pdf/ZPB446030_0_20261012_file2.pdf",
         "prdfilename3": "/publication/pdf/ZPB446030_0_20261012_file3.pdf"},
        {"prdName": "무배당 삼성화재 건강보험 New마이헬스파트너(2608.9)(일반형)", "prdGun": "장기", "prdGb": "건강",
         "saleChannel": "대면", "prdCode": "ZPB446020", "jongGb": "0", "saleStDt": "20260818", "saleEnDt": "20261011",
         "prdfilename1": "/publication/pdf/ZPB446020_0_20260818_file1.pdf",
         "prdfilename2": "/publication/pdf/ZPB446020_0_20260818_file2.pdf",
         "prdfilename3": "/publication/pdf/ZPB446020_0_20260818_file3.pdf"},
        # 판매 중인 상품의 지난 판매기간: displayGb 1이지만 종료일이 닫혀 있다
        {"prdName": "무배당 삼성화재 간편보험 새로고침100세(2608.7) 1종(납입면제형)", "prdGun": "장기", "prdGb": "건강",
         "saleChannel": "대면", "prdCode": "ZPB335070", "jongGb": "0", "saleStDt": "20260818", "saleEnDt": "20261011",
         "displayGb": "1", "prdfilename1": "/publication/pdf/ZPB335070_0_20260818_file1.pdf"},
        {"prdName": "무배당 삼성화재 간편보험 새로고침100세(2608.7) 1종(납입면제형)", "prdGun": "장기", "prdGb": "건강",
         "saleChannel": "대면", "prdCode": "ZPB335070", "jongGb": "0", "saleStDt": "20261012", "saleEnDt": "99991231",
         "prdfilename1": "/publication/pdf/ZPB335070_0_20261012_file1.pdf"},
        # 종료일은 열려 있지만 '판매중지' 탭에 고정된 상품
        {"prdName": "무배당 삼성화재 건강보험 내돈내삼4160(2504.6) 2종(납입면제,해약환급금 미지급형Ⅱ)", "prdGun": "장기",
         "prdGb": "건강", "saleChannel": "대면", "prdCode": "ZPB387041", "jongGb": "0", "saleStDt": "20250501",
         "saleEnDt": "99991231", "displayGb": "2", "prdfilename1": "/publication/pdf/ZPB387041_0_20250501_file1.pdf"},
        # 서류 경로가 상품코드 규칙을 따르지 않는 행도 있다. 경로는 만들지 말고 응답 값을 쓴다
        {"prdName": "종업원복지보장보험", "prdGun": "일반보험", "prdGb": "상해", "saleChannel": "대면",
         "prdCode": "KR1294P", "jongGb": "0", "saleStDt": "20180518", "saleEnDt": "20190101",
         "prdfilename1": "/publication/pdf/76035_0_20180518_file1.pdf"},
        # 옛 상품은 한 상품코드 아래 종 구분(jongGb)으로 종이 갈린다
        {"prdName": "무배당 캐치투보장보험(1501.17) 1종", "prdGun": "장기", "saleChannel": "대면", "prdCode": "95867",
         "jongGb": "1", "saleStDt": "20150101", "saleEnDt": "99991231",
         "prdfilename1": "/publication/pdf/95867_1_20150101_file1.pdf"},
        {"prdName": "무배당 캐치투보장보험(1501.17) 2종", "prdGun": "장기", "saleChannel": "대면", "prdCode": "95867",
         "jongGb": "2", "saleStDt": "20150101", "saleEnDt": "99991231",
         "prdfilename1": "/publication/pdf/95867_2_20150101_file1.pdf"},
        # 같은 (코드, 종 구분, 개시일)이 닫힌 행과 열린 행으로 겹쳐 오기도 한다
        {"prdName": "가족결합 영업보험료 할인 제도성 특별약관", "prdGun": "장기", "saleChannel": "제도성 특약",
         "prdCode": "TL5808", "jongGb": "0", "saleStDt": "20260818", "saleEnDt": "20261011", "displayGb": "1",
         "prdfilename1": "/publication/pdf/TL5808_0_20260818_file1.pdf"},
        {"prdName": "가족결합 영업보험료 할인 제도성 특별약관", "prdGun": "장기", "saleChannel": "제도성 특약",
         "prdCode": "TL5808", "jongGb": "0", "saleStDt": "20260818", "saleEnDt": "99991231",
         "prdfilename1": "/publication/pdf/TL5808_0_20260818_file1.pdf"},
    ]}}}}
SEARCH = {"sfmi.nexus.b2c.currentStage": "P", "responseMessage": {
    "header": {"tranId": "VH.HDIF0114", "longTran": False, "resultCode": "0000"},
    "body": {"result": "S", "data": {"list": [
        {"prdName": "무배당 삼성화재 건강보험 THE FIT 파트너(2610.1)(일반형)", "prdGun": "장기", "saleStDt": "20261012",
         "saleEnDt": "99991231", "prdfilename1": "/publication/pdf/ZPB446030_0_20261012_file1.pdf",
         "prdfilename2": "/publication/pdf/ZPB446030_0_20261012_file2.pdf",
         "prdfilename3": "/publication/pdf/ZPB446030_0_20261012_file3.pdf"},
    ]}}}}
ERROR = {"responseMessage": {"header": {"tranId": "VH.HDIF0103", "resultCode": "9999",
                                         "errorMsg": {"errorCode": "BIHAU00001", "displayMsg": "로그인 세션이 없습니다."}}}}


def test_products_are_one_per_sale_period_with_selling_flag():
    products = samsungfire.parse_products(LIST)
    by = {(p.code, p.start): p for p in products if p.jong == "0"}
    assert len(products) == 9
    fit = by[("ZPB446030", "2026-10-12")]
    assert fit.selling and fit.end is None and fit.channel == "대면" and fit.group == "건강"
    assert by[("ZPB446020", "2026-08-18")].end == "2026-10-11" and not by[("ZPB446020", "2026-08-18")].selling
    assert not by[("ZPB335070", "2026-08-18")].selling and by[("ZPB335070", "2026-10-12")].selling
    assert not by[("ZPB387041", "2025-05-01")].selling   # 판매중지 탭 고정
    assert by[("TL5808", "2026-08-18")].selling            # 겹친 행은 판매 중인 쪽을 남긴다
    assert [(p.jong, p.name[-2:]) for p in products if p.code == "95867"] == [("1", "1종"), ("2", "2종")]


def test_search_rows_take_code_from_file_path():
    (p,) = samsungfire.parse_products(SEARCH)
    assert p.code == "ZPB446030" and p.jong == "0" and p.start == "2026-10-12" and p.selling


def test_documents_follow_the_period_that_contains_the_date():
    products = samsungfire.parse_products(LIST)
    docs = samsungfire.parse_documents("ZPB446030", products)
    assert [d.kind for d in docs] == ["약관", "사업방법서", "상품요약서"]
    assert docs[2].path == "/publication/pdf/ZPB446030_0_20261012_file3.pdf" and docs[2].registered == "2026-10-12"
    old = samsungfire.parse_documents("ZPB335070", products, on="2026-09-01")
    assert [d.path for d in old] == ["/publication/pdf/ZPB335070_0_20260818_file1.pdf"]
    assert samsungfire.parse_documents("ZPB335070", products, on="2026-01-01") == []
    assert [d.path for d in samsungfire.parse_documents("95867", products, jong="2")] == [
        "/publication/pdf/95867_2_20150101_file1.pdf"]
    # 응답에 실린 경로를 그대로 쓴다
    assert samsungfire.parse_documents("KR1294P", products)[0].file_name == "76035_0_20180518_file1.pdf"


def test_server_error_is_raised():
    import pytest

    with pytest.raises(ValueError, match="BIHAU00001"):
        samsungfire.parse_products(ERROR)


class FakeSession:
    def __init__(self, content=b"", payload=None):
        self.content = content
        self.payload = payload
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        outer = self

        class R:
            content = outer.content
            headers = {"Content-Type": "application/pdf"}
            encoding = None

            def raise_for_status(self):
                pass

            def json(self):
                return outer.payload

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def test_list_request_matches_what_the_page_sends():
    s = FakeSession(payload=LIST)
    selling = samsungfire.list_products(s)
    assert {p.code for p in selling} == {"ZPB446030", "ZPB335070", "95867", "TL5808"}
    method, url, kw = s.sent[0]
    assert (method, url) == ("POST", "https://www.samsungfire.com/vh/data/VH.HDIF0103.do")
    assert kw["data"] == b"header=%7B%22tranId%22%3A%22VH.HDIF0103%22%7D"
    assert kw["headers"]["Referer"].endswith("/vh/page/VH.HPIF0103.do")

    s = FakeSession(payload=SEARCH)
    samsungfire.search_products(s, "THE FIT 파트너")
    body = s.sent[0][2]["data"].decode()
    assert s.sent[0][1].endswith("/vh/data/VH.HDIF0114.do")
    assert body.startswith("header=%7B%22tranId%22%3A%22VH.HDIF0114%22%7D&body=%7B%22kwd%22%3A%22THE%20FIT%20")
    assert body.endswith("%22cate%22%3A%22%22%2C%22from%22%3A%22%22%2C%22to%22%3A%22%22%7D")


def test_list_documents_reuses_products_and_download_rejects_non_pdf():
    import pytest

    s = FakeSession(b"%PDF-1.7 ...")
    products = samsungfire.parse_products(LIST)
    doc = samsungfire.list_documents(s, "ZPB446030", products=products)[2]
    assert s.sent == []                      # 목록을 다시 받지 않는다
    assert samsungfire.download(s, doc).startswith(b"%PDF-")
    assert s.sent[0][:2] == ("GET", "https://www.samsungfire.com/publication/pdf/ZPB446030_0_20261012_file3.pdf")
    with pytest.raises(ValueError):
        samsungfire.download(FakeSession(b"<html>"), doc)
