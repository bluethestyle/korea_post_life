import json

import pytest

try:
    from postlife.disclosure import hyundai
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import hyundai

OK = {"exception": None, "exceptionOccurred": False}
INFO = [{"tranId": "HHCA0310M38S", "code": "JEF51012", "show": "2", "type": "INFO", "message": "정상처리 되었습니다"}]


def row(name, start, end, ids, cat="0302", rep="131A"):
    """목록 행 (실제 행에는 clsCd1~20, insCd 같은 null 칸이 더 있다)."""
    clau, mthd, smry = ids
    return {"prodCatCd": cat, "insCd": None, "slStDt": start, "slEdDt": end, "clauApnflId": clau, "userMthdApnflId": mthd,
            "prodSmryApnflId": smry, "prodNoteApnflId": None, "repInsCd": rep, "repInsYn": "Y", "intRtPlctYn": "N",
            "slCh": None, "prodTy": None, "seqno": 0, "slYn": "Y" if end is None else "N", "prodNm": name}


# 2026-11-19에 공시실에서 받은 상품 목록(HHCA0310M38S {}) 응답의 형태. 행은 실제 응답에서 골라 줄였다.
# 시작일 뒤에 빈칸이 붙고, 상품명 앞에 탭이 붙은 행이 있다. 판매 중지 목록에도 같은 상품의 지난 판매기간이 온다.
LIST = {"data": {
    "slYProdList": [
        row("무배당현대해상퍼펙트플러스종합보험(세만기형)(Hi2610) 1종(일반형), 2종(납입면제형)", "20261021  ", None,
            ("ca1769c5-d0e7-46d8-878c-03d3ee817295", "7c377f40-1a50-4b65-9ed0-bea5d649c321",
             "aec9da01-53c3-4659-a1af-df53b49a4af1")),
        row("\t(무)현대해상내삶엔(3N)맞춤간편건강보험(세만기형)(Hi2607) 3종(표준형)(일반심사)", "20260801  ", None,
            ("85fbe5be-0000-0000-0000-000000000000", "07dc082f-0000-0000-0000-000000000000", None), rep="11F0"),
        row("(무)암주요치료비(연간1회한,진단후5년)보장 특별약관", None, None, ("x", "y", None), cat="0309", rep=None),
    ],
    "slNProdList": [
        row("무배당현대해상퍼펙트플러스종합보험(세만기형)(Hi2607) 1종(일반형), 2종(납입면제형)", "20260801  ", "20261020",
            ("c1", "093e5b9a-0000-0000-0000-000000000000", "9e7d43f8-0000-0000-0000-000000000000")),
    ],
    "searchWordList": [], "hhca0051VOList": [], "recommendCnt": 0, "searchData": None, "searchType": None,
}, "messages": INFO, "responseStatus": OK}
# 서류 정보(HHCA0310M26S) 응답의 형태
FILE = {"data": {"apnflId": "aec9da01-53c3-4659-a1af-df53b49a4af1", "savPath": "/data/202611",
                 "savFileNm": "20261102135115454", "flExts": "pdf", "fileSz": 1944078, "delYn": "N",
                 "originalFileNm": "(무)현대해상퍼펙트플러스종합보험(세만기형)(Hi2610)_상품요약서.pdf"},
        "messages": INFO, "responseStatus": OK}
# 없는 첨부 ID를 보냈을 때: 상태 200, 정상 메시지, 값은 모두 null
FILE_MISSING = {"data": {"apnflId": None, "savPath": None, "savFileNm": None, "flExts": None, "fileSz": 0,
                         "originalFileNm": None}, "messages": INFO, "responseStatus": OK}
# 없는 파일을 내려받을 때: 상태 200, text/html, 경고창을 띄우는 스크립트
NOT_FOUND = b"<script>\nif (typeof top.alertInfo == 'function') {\n\tif (top.isEngSite()) {\n\t\ttop.alertInfo('File not found.');"
# 화면 공통 스크립트(common.js)가 처리하는 오류 꼴. 실제 응답으로 받아 본 적은 없다
ERROR = {"data": None, "messages": [],
         "responseStatus": {"exception": {"tranId": "HHCA0310M38S", "code": "X", "message": "처리 중 오류"},
                            "exceptionOccurred": True}}


def test_list_rows():
    products = hyundai.parse_products(LIST)
    assert len(products) == 3   # 시작일이 없는 행은 버린다
    pp, ns, old = products
    assert pp.name.startswith("무배당현대해상퍼펙트플러스") and pp.start == "2026-10-21" and pp.end is None and pp.selling
    assert ns.name.startswith("(무)현대해상내삶엔")   # 앞의 탭을 뗀다
    assert (old.start, old.end, old.selling) == ("2026-08-01", "2026-10-20", False)
    assert pp.files == {"약관": "ca1769c5-d0e7-46d8-878c-03d3ee817295", "사업방법서": "7c377f40-1a50-4b65-9ed0-bea5d649c321",
                        "상품요약서": "aec9da01-53c3-4659-a1af-df53b49a4af1"}
    assert "상품요약서" not in ns.files and ns.rep_code == "11F0"
    assert pp.category_name == "장기보험/상해성"
    docs = hyundai.documents_of(pp, ("상품요약서", "사업방법서"))
    assert [d.kind for d in docs] == ["사업방법서", "상품요약서"] and docs[1].apnfl_id.startswith("aec9da01")


def test_find_by_name_and_date():
    products = hyundai.parse_products(LIST)
    assert [p.start for p in hyundai.find(products, "퍼펙트플러스", on="2026-11-19")] == ["2026-10-21"]
    closed = hyundai.find(products, "퍼펙트플러스", on="2026-09-01", selling=None)
    assert [(p.start, p.end) for p in closed] == [("2026-08-01", "2026-10-20")]
    assert hyundai.find(products, "퍼펙트플러스", on="2026-09-01") == []


def test_single_object_list_is_wrapped():
    body = {"data": {"slYProdList": LIST["data"]["slYProdList"][0], "slNProdList": None},
            "messages": INFO, "responseStatus": OK}   # 화면의 generateValidJson이 처리하는 꼴
    assert len(hyundai.parse_products(body)) == 1


def test_file_info_and_url():
    info = hyundai.parse_file_info(FILE)
    assert info.size == 1944078 and info.original_name.endswith("_상품요약서.pdf")
    # 실제로 내려받기에 성공한 주소와 같은 꼴
    assert info.url == "https://www.hi.co.kr/FileActionServlet/preview/0/data/202611/20261102135115454.pdf"
    odd = hyundai.FileInfo("x", "data/202608", "a+b 요약", "pdf")
    assert odd.url == "https://www.hi.co.kr/FileActionServlet/preview/0/data/202608/a%2Bb%20%EC%9A%94%EC%95%BD.pdf"


def test_missing_file_and_server_error_are_raised():
    with pytest.raises(ValueError, match="savPath"):
        hyundai.parse_file_info(FILE_MISSING)
    with pytest.raises(ValueError, match="처리 중 오류"):
        hyundai.parse_products(ERROR)
    with pytest.raises(ValueError):
        hyundai.parse_products({"list": []})
    with pytest.raises(ValueError, match="상품 목록이 없음"):
        hyundai.parse_products({"data": {"savPath": "/x"}, "messages": INFO, "responseStatus": OK})


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def post(self, url, **kw):
        self.sent.append(("POST", url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else b""
            headers = {"Content-Type": "application/pdf" if isinstance(reply, bytes) and reply.startswith(b"%PDF")
                       else "text/html; charset=UTF-8"}
            encoding = None

            def raise_for_status(self):
                pass

            def json(self):
                return reply

        return R()


def test_list_and_search_send_what_the_page_sends():
    s = FakeSession([LIST, LIST])
    hyundai.list_products(s)
    hyundai.search_products(s, "간편한3.10.10")
    (m1, url1, kw1), (_, url2, kw2) = s.sent
    assert (m1, url1) == ("POST", "https://www.hi.co.kr/ajax.xhi") and url2 == url1
    sent = json.loads(kw1["data"])
    assert sent["request"] == {} and kw1["headers"]["Content-Type"] == "application/json"
    head = sent["header"]
    assert (head["tranId"], head["channelId"], head["menuId"], head["loginId"]) == ("HHCA0310M38S", "HI-HOME", "100932", None)
    assert len(head["gId"]) == 30
    assert json.loads(kw2["data"])["request"] == {"searchData": "간편한3.10.10", "searchDate": "", "searchType": "0",
                                                  "searchKeyword": 1}


def test_download_asks_path_then_posts_and_rejects_non_pdf():
    doc = hyundai.documents_of(hyundai.parse_products(LIST)[0], ("상품요약서",))[0]
    s = FakeSession([FILE, b"%PDF-1.6 ..."])
    assert hyundai.download(s, doc).startswith(b"%PDF-")
    (_, url1, kw1), (m2, url2, _) = s.sent
    assert json.loads(kw1["data"])["header"]["tranId"] == "HHCA0310M26S"
    assert json.loads(kw1["data"])["request"] == {"apnflId": "aec9da01-53c3-4659-a1af-df53b49a4af1"}
    assert (m2, url2) == ("POST", "https://www.hi.co.kr/FileActionServlet/preview/0/data/202611/20261102135115454.pdf")
    with pytest.raises(ValueError, match="PDF가 아닌 응답"):   # 없는 파일: 상태 200, 경고창 스크립트
        hyundai.download(FakeSession([FILE, NOT_FOUND]), doc)
    with pytest.raises(ValueError, match="savPath"):          # 없는 첨부 ID: 내려받기 요청을 보내지 않는다
        hyundai.download(FakeSession([FILE_MISSING]), doc)
