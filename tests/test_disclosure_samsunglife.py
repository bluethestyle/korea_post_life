from urllib.parse import parse_qsl

import pytest

try:
    from postlife.disclosure import samsunglife as sl
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import samsunglife as sl

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮기고 쓰지 않는 칸은 뺐다)
# 판매상품 탭: 대면 건강, 상품요약서가 없는 행, 중·소분류가 빈 온라인 행, 서류를 다른 꼴로 주는 법인 행
SALES = {"code": "200", "message": "SUCCESS", "response": [
    {"goodsCode": "LP0842003AB01V10A01", "goodsName": "삼성New플러스원건강보험(2608)(무배당,저해약환급금형)",
     "fromdate": "20260923", "todate": "99999999", "status": "상품운용", "filename1": "1790146773625",
     "filename2": "1790146756187", "filename3": "1790146744906", "lCode": "판매중", "mCode": "개인", "gCode": "보장성",
     "sCode": "건강", "totalRows": "288", "pageSize": "3000", "boardNum": "52", "gubun": "개인>보장성>건강", "pageNo": 1},
    {"goodsCode": "LP07460023", "goodsName": "삼성5대재해골절보장보험(2505)(무배당)", "fromdate": "20260923",
     "todate": "99999999", "status": "상품운용", "filename2": "1790038031793", "filename3": "1790038022762",
     "lCode": "판매중", "mCode": "개인", "gCode": "보장성", "sCode": "기타(상해/정기)", "totalRows": "288",
     "gubun": "개인>보장성>기타(상해/정기)", "pageNo": 1},
    {"goodsCode": "LP0853002AB01V10A014", "goodsName": "삼성팩건강보험(2607)(무배당,무해약환급금형)", "fromdate": "20260923",
     "todate": "99999999", "status": "상품운용", "filename1": "1790836227901", "filename2": "1790836210276",
     "filename3": "1790836236464", "lCode": "판매중", "mCode": "온라인", "totalRows": "288", "gubun": "온라인>", "pageNo": 1},
    {"goodsCode": "1466757894708", "goodsName": "퇴직보험", "fromdate": "20160627", "todate": "99999999",
     "status": "상품운용", "filepath2": "/uploadDir/corp/2016/0627/701/", "filename2": "1466757894708-701-.pdf",
     "lCode": "판매중", "mCode": "법인상품", "gCode": "퇴직", "sCode": "퇴직", "totalRows": "288", "gubun": "법인>퇴직"},
]}
# 전체 탭 검색: 같은 상품코드의 지난 판매기간은 "판매중지"로 오고 상품요약서가 빠져 있기도 하다. 개정판은 코드가 다르다
ALL = {"code": "200", "message": "SUCCESS", "response": [
    {"goodsCode": "LP0842003AB01V10A01", "goodsName": "삼성New플러스원건강보험(2608)(무배당,저해약환급금형)",
     "fromdate": "20260923", "todate": "99999999", "status": "상품운용", "filename1": "1790146773625",
     "filename2": "1790146756187", "filename3": "1790146744906", "lCode": "판매중", "mCode": "개인", "totalRows": "3"},
    {"goodsCode": "LP0842003AB01V10A01", "goodsName": "삼성New플러스원건강보험(2608)(무배당,저해약환급금형)",
     "fromdate": "20260813", "todate": "20260922", "status": "상품운용", "filename2": "1787552378362",
     "filename3": "1787552404470", "lCode": "판매중지", "mCode": "개인", "totalRows": "3"},
    {"goodsCode": "LP0842002AB01V10A01", "goodsName": "삼성New플러스원건강보험(2607)(무배당,저해약환급금형)",
     "fromdate": "20260701", "todate": "20260812", "status": "상품운용", "filename2": "x", "filename3": "y",
     "lCode": "판매중지", "mCode": "개인", "totalRows": "3"},
]}
# 쪽 크기를 넘는 값을 보냈을 때. 상태 코드는 200이다
ERROR = {"code": "9999", "message": "서비스 처리중 오류가 발생했습니다.<br/>삼성생명 콜센터(1588-3114)로 문의해 주세요.",
         "response": {"code": "9999", "message": "UNKNOWN ERROR",
                      "description": "서비스 처리중 오류가 발생했습니다.<br/>삼성생명 콜센터(1588-3114)로 문의해 주세요."}}
# XView.do 뷰어 HTML에서 쓰는 부분만
VIEWER_HTML = """<script type="text/javascript" >
        var title = '1790146773625.pdf';
        var options = { "fileinfo" : { "filetype" : "pdf",
                "filepath" : '../uploadDir/doc/2026/0923/LP0842003/101/1790146773625.pdf', },
            "loading" : { "downloadURL" : '../uploadDir/doc/2026/0923/LP0842003/101/1790146773625.pdf',
                "viewmode" : "slide" } }
</script>"""


def test_sales_rows():
    rows = sl.parse_periods(SALES)
    assert [r.code for r in rows] == ["LP0842003AB01V10A01", "LP07460023", "LP0853002AB01V10A014", "1466757894708"]
    p = rows[0]
    assert (p.start, p.end, p.selling, p.status) == ("2026-09-23", None, True, "상품운용")
    assert (p.channel, p.group, p.kind, p.category) == ("개인", "보장성", "건강", "개인>보장성>건강")
    assert p.files == {"상품요약서": "1790146773625", "사업방법서": "1790146756187", "약관": "1790146744906"}
    assert "상품요약서" not in rows[1].files
    assert rows[2].channel == "온라인" and rows[2].group == "" and rows[2].kind == ""
    assert rows[3].corporate and rows[3].files == {}     # 법인 상품의 서류 꼴은 다루지 않는다
    assert sl.total_rows(SALES) == 288


def test_documents_and_doc_types():
    docs = sl.documents_of(sl.parse_periods(SALES)[0])
    assert [(d.kind, d.doc_type, d.doc_id) for d in docs] == [
        ("상품요약서", "101", "1790146773625"), ("사업방법서", "401", "1790146756187"), ("약관", "301", "1790146744906")]
    assert docs[0].code == "LP0842003AB01V10A01" and docs[0].start == "2026-09-23" and docs[0].end is None


def test_periods_first_start_and_pick():
    rows = sl.parse_periods(ALL)
    assert [r.selling for r in rows] == [True, False, False]
    assert rows[1].end == "2026-09-22"
    code = "LP0842003AB01V10A01"
    assert sl.first_start(rows, code) == "2026-08-13"
    assert sl.pick_period(rows, code).start == "2026-09-23"
    assert sl.pick_period(rows, code, "2026-09-01").start == "2026-08-13"
    assert sl.pick_period(rows, code, "2026-07-15") is None
    assert sl.pick_period(rows, None, "2026-07-15").code == "LP0842002AB01V10A01"


def test_server_error_and_bad_shape_are_raised():
    with pytest.raises(ValueError, match="9999"):
        sl.parse_periods(ERROR)
    with pytest.raises(ValueError):
        sl.parse_periods([])
    with pytest.raises(ValueError):
        sl.parse_periods({"code": "200", "response": {"list": []}})
    # 결과가 없을 때의 실제 응답은 받아 보지 않았다. 빈 목록이 오면 빈 결과로 본다
    assert sl.parse_periods({"code": "200", "message": "SUCCESS", "response": []}) == []


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
                       else "text/html; charset=UTF-8"}
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


def test_list_sends_what_the_page_sends_and_pages():
    s = FakeSession([SALES])
    rows = sl.list_products(s, "sales", "건강")
    assert len(rows) == 4 and len(s.sent) == 1
    method, url, kw = s.sent[0]
    assert (method, url) == ("POST", "https://www.samsunglife.com/gw/api/product/disclosure/product/prdt/salesPrdtList")
    # 화면(qs.stringify)과 같은 순서와 꼴. '전체'는 빈칸 한 글자이고 %20으로 간다. 실제로 응답을 받은 본문과 같다
    assert kw["data"] == ("mCode=%20&gCode=%20&sCode=%20&searchYear=&goodsName=%EA%B1%B4%EA%B0%95"
                          "&pageNo=1&pageRows=3000")
    assert kw["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert "dcpChnlTyp" not in kw["headers"]    # 이 머리가 있으면 화면은 본문을 암호화한다

    # totalRows만큼 쪽을 넘긴다
    page1 = {"code": "200", "response": ALL["response"][:2]}
    page2 = {"code": "200", "response": ALL["response"][2:]}
    s = FakeSession([page1, page2])
    rows = sl.list_products(s, "all", "플러스원", page_rows=2)
    assert len(rows) == 3 and s.sent[1][1].endswith("/salesAllPrdtList")
    assert dict(parse_qsl(s.sent[1][2]["data"]))["pageNo"] == "2"
    with pytest.raises(ValueError):
        sl.list_products(FakeSession([]), "selling")


def test_list_documents_picks_period_by_code():
    s = FakeSession([ALL])
    docs = sl.list_documents(s, "LP0842003AB01V10A01", "플러스원", on="2026-09-01")
    assert [(d.kind, d.doc_id) for d in docs] == [("사업방법서", "1787552378362"), ("약관", "1787552404470")]
    assert s.sent[0][1].endswith("/salesAllPrdtList")


def test_download_reads_pdf_path_from_viewer():
    doc = sl.documents_of(sl.parse_periods(SALES)[0])[0]
    s = FakeSession([VIEWER_HTML.encode(), b"%PDF-1.6 ..."])
    assert sl.download(s, doc).startswith(b"%PDF-")
    (m1, url1, _), (m2, url2, kw2) = s.sent
    # 실제로 받은 주소와 같은 꼴 (name은 encodeURI: 쉼표와 괄호는 그대로)
    assert url1 == ("https://pcms.samsunglife.com/XView.do?docID=1790146773625&name="
                    "%EC%82%BC%EC%84%B1New%ED%94%8C%EB%9F%AC%EC%8A%A4%EC%9B%90%EA%B1%B4%EA%B0%95%EB%B3%B4%ED%97%98"
                    "(2608)(%EB%AC%B4%EB%B0%B0%EB%8B%B9,"
                    "%EC%A0%80%ED%95%B4%EC%95%BD%ED%99%98%EA%B8%89%EA%B8%88%ED%98%95)"
                    "&isDown=false&loadingType=1&contentType=&docKey=&tsId=")
    assert (m2, url2) == ("GET", "https://pcms.samsunglife.com/uploadDir/doc/2026/0923/LP0842003/101/1790146773625.pdf")
    assert kw2["headers"]["Referer"] == url1


def test_download_errors():
    doc = sl.documents_of(sl.parse_periods(SALES)[0])[0]
    with pytest.raises(ValueError, match="downloadURL"):
        sl.download(FakeSession([b"<html><body>error</body></html>"]), doc)
    with pytest.raises(ValueError, match="PDF가 아닌"):
        sl.download(FakeSession([VIEWER_HTML.encode(), b"<!DOCTYPE html><html>error</html>"]), doc)
