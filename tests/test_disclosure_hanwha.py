try:
    from postlife.disclosure import hanwha
except ImportError:   # 저장소에 넣기 전, 초안 폴더에서 바로 돌릴 때
    import hanwha

OK = {"msg": "DBMS processing succeeded!", "code": "0000", "type": "dbms"}
NAME = "한화생명 시그니처 H통합보험 무배당"

# 2026-11-18에 공시실에서 받은 응답의 형태
# getList.do (sellFlag=Y, schText=연금): 상품구분은 여러 개인데 list2에는 첫 번째 상품구분의 상품만 온다
LIST = {"list1": [{"SELL_TYPE": "SA", "GOODS_TYPE": "GB", "SELL_TYPE_NM": "개인", "GOODS_TYPE_NM": "연금"},
                  {"SELL_TYPE": "SE", "GOODS_TYPE": "GB", "SELL_TYPE_NM": "다이렉트", "GOODS_TYPE_NM": "연금"}],
        "status": OK,
        "list2": [{"IDX": 2331, "GOODS_NAME": "한화생명 연금저축 하이드림연금보험"},
                  {"IDX": 2254, "GOODS_NAME": "한화생명 시그니처 암보험 2.0 무배당 "}],
        "list3": []}
# getList2.do (sellType=SE, goodsType=GB)
LIST2 = {"list2": [{"IDX": 2288, "GOODS_NAME": "한화생명 스마트V연금보험 무배당"},
                   {"IDX": 2331, "GOODS_NAME": "한화생명 연금저축 하이드림연금보험"}],
         "status": OK, "list3": []}
# getList3.do (goodsIndex=2597)
DOCS = {"list3": [
    {"GOODS_NAME": NAME, "SELL_START_DT": "2026-10-01", "SELL_END_DT": "          ",
     "FILE_NAME1": NAME + "_상품요약서_20261001.pdf", "FILE_NAME2": NAME + "_사업방법서_20261001.pdf",
     "FILE_NAME3": NAME + "_약관_20261001.pdf", "FILE_NAME4": NAME + "_주요내용요약서_20261001.pdf"},
    {"GOODS_NAME": NAME, "SELL_START_DT": "2026-09-01", "SELL_END_DT": "2026-09-30",
     "FILE_NAME2": NAME + "_사업방법서_20260901.pdf", "FILE_NAME3": NAME + "_약관_20260901.pdf.pdf",
     "FILE_NAME4": NAME + "_주요내용요약서_20260901.pdf"},
    {"GOODS_NAME": NAME, "SELL_START_DT": "2026-05-04", "SELL_END_DT": "2026-05-31",
     "FILE_NAME2": NAME + "_사업방법서_20260504.pdf", "FILE_NAME3": NAME + "_약관_20260504.pdf",
     "FILE_NAME4": NAME + "_주요내용요약서_20260504_1.pdf"},
], "status": OK}
EMPTY = {"list3": [], "status": OK}   # 없는 상품번호(goodsIndex=999999)
# 파일이 없을 때: 상태 코드 200, text/html, EUC-KR 안내 화면
MISSING = ('\r\n\t<Script Language=javascript>\r\n\t\talert("파일이 존재하지 않아 다운로드 할 수 없습니다.'
           '\\n관리자에게 문의하시기 바랍니다..");\r\n\t</Script>\r\n').encode("cp949")


def test_products_and_categories():
    assert hanwha.parse_categories(LIST) == [("SA", "GB", "개인 연금"), ("SE", "GB", "다이렉트 연금")]
    products = hanwha.parse_products(LIST, True, "개인 연금")
    assert [(p.code, p.selling, p.category) for p in products] == [("2331", True, "개인 연금"), ("2254", True, "개인 연금")]
    assert products[1].name == "한화생명 시그니처 암보험 2.0 무배당"   # 이름 끝 빈칸은 버린다


def test_documents_per_sale_period():
    docs = hanwha.parse_documents("2597", DOCS)
    assert [d.kind for d in docs if d.start == "2026-10-01"] == ["상품요약서", "사업방법서", "약관"]
    assert all(d.end is None for d in docs if d.start == "2026-10-01")
    # 지난 판에는 상품요약서가 없고, 주요내용요약서는 받지 않는다
    assert [(d.kind, d.end) for d in docs if d.start == "2026-09-01"] == [("사업방법서", "2026-09-30"), ("약관", "2026-09-30")]
    assert hanwha.parse_documents("999999", EMPTY) == []


def test_pick_version():
    docs = hanwha.parse_documents("2597", DOCS)
    assert {d.start for d in hanwha.pick_version(docs)} == {"2026-10-01"}
    assert {d.file_name for d in hanwha.pick_version(docs, "2026-05-20")} == {
        NAME + "_사업방법서_20260504.pdf", NAME + "_약관_20260504.pdf"}
    assert hanwha.pick_version(docs, "2026-01-15") == []   # 판매 시작(2026-05-04) 전


def test_failed_status_is_an_error():
    import pytest

    with pytest.raises(ValueError):
        hanwha.parse_documents("2597", {"list3": [], "status": {"code": "9999", "msg": "x"}})


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def post(self, url, **kw):
        self.sent.append((url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else b""
            headers = {"Content-Type": "Application/Unknown"}
            encoding = None

            def raise_for_status(self):
                pass

            def json(self):
                return reply

        return R()


def test_list_products_walks_every_category():
    s = FakeSession([LIST, LIST2])
    products = hanwha.list_products(s, selling=True, search="연금")
    assert [p.code for p in products] == ["2331", "2254", "2288"]   # 두 상품구분에 겹친 2331은 한 번만
    assert s.sent[0][0].endswith("/getList.do") and s.sent[1][0].endswith("/getList2.do")
    assert "sellFlag=Y" in s.sent[0][1]["data"] and "schText=%EC%97%B0%EA%B8%88" in s.sent[0][1]["data"]
    assert "sellType=SE" in s.sent[1][1]["data"] and "goodsType=GB" in s.sent[1][1]["data"]


def test_list_documents_sends_product_number():
    s = FakeSession([DOCS])
    docs = hanwha.list_documents(s, "2597")
    assert [d.kind for d in docs] == ["상품요약서", "사업방법서", "약관"]
    assert "goodsIndex=2597" in s.sent[0][1]["data"]


def test_download_sends_euc_kr_name_and_rejects_non_pdf():
    import pytest

    doc = hanwha.parse_documents("2597", DOCS)[1]
    ok = FakeSession([b"%PDF-1.7 ..."])
    assert hanwha.download(ok, doc).startswith(b"%PDF-")
    url, kw = ok.sent[0]
    assert url == "https://file.hanwhalife.com/www/announce/goods/download_chk.asp"
    # 실제로 내려받기에 성공한 요청 본문과 같다 (한글은 EUC-KR, 빈칸은 %20)
    assert kw["data"] == ("file_name=%C7%D1%C8%AD%BB%FD%B8%ED%20%BD%C3%B1%D7%B4%CF%C3%B3%20H%C5%EB%C7%D5%BA%B8%C7%E8"
                          "%20%B9%AB%B9%E8%B4%E7_%BB%E7%BE%F7%B9%E6%B9%FD%BC%AD_20261001.pdf")
    with pytest.raises(ValueError, match="파일이 존재하지 않아"):
        hanwha.download(FakeSession([MISSING]), doc)
