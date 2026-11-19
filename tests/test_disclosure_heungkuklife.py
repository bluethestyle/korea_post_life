import pytest

try:
    from postlife.disclosure import heungkuklife as hk
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import heungkuklife as hk

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮김. 암호값은 길이 130~200자의 값을 짧은 자리표시로 바꿈)
# 응답은 EUC-KR(cp949) 글자 하나다: 상품명 목록 %||% null %||% 서류 행 목록. 끝에 줄바꿈이 붙는다.
NAMES_PART = ("(무) 흥국생명 3.6.5.1원플러스간편건강보험(해약환급금미지급형V2)%,%%|%"
              "(무)흥국생명 다(多)사랑통합보험V2%,%%|%(무)흥국생명 다사랑3N5간편건강보험%,%")
ROWS = [
    # 판매 중인 판매기간인데 상품요약서 파일 이름이 비어 있다(암호값은 온다)
    ["2026.11.02", "", "P0001901~P0002201", "4388", "ENC-A1",
     "(무)흥국생명 다(多)사랑통합보험V2_인쇄용약관(20261102_P0001901~P0002201)_공시용.pdf",
     "ENC-B1", "(무)흥국생명 다(多)사랑통합보험V2_사업(202608)_v1.pdf", "ENC-C1", ""],
    ["2026.11.02", "", "P0001501~P0001801<br>갱신형", "4387", "ENC-A2",
     "(무)흥국생명 다(多)사랑통합보험V2(갱신형)_인쇄용약관(20261102_P0001501~P0001801)_공시용.pdf",
     "ENC-B2", "(무)흥국생명 다(多)사랑통합보험V2(갱신형)_사업(202608).pdf", "ENC-C2", ""],
    ["2026.08.10", "2026.11.01", "P0001901~P0002201", "4333", "ENC-A3",
     "(무)흥국생명 다(多)사랑통합보험V2_인쇄용약관(20260810_P0001901~P0002201)_공시용.pdf",
     "ENC-B3", "(무)흥국생명 다(多)사랑통합보험V2_사업(202608)_v1.pdf",
     "ENC-C3", "(무)흥국생명 다(多)사랑통합보험V2_상품요약서(20260810).pdf"],
    ["2026.08.10", "2026.11.01", "P0001501~P0001801<br>갱신형", "4332", "ENC-A4",
     "(무)흥국생명 다(多)사랑통합보험V2(갱신형)_인쇄용약관(20260810_P0001501~P0001801)_공시용.pdf",
     "ENC-B4", "(무)흥국생명 다(多)사랑통합보험V2(갱신형)_사업(202608).pdf",
     "ENC-C4", "(무)흥국생명 다(多)사랑통합보험V2_상품요약서(20260810).pdf"],
    # 2026년 6월 상품코드 체계 변경 전 판매기간. 소문자 p로 적힌 행도 있다
    ["2025.06.30", "2025.07.31", "P2163300~p2163400", "3981", "ENC-A5",
     "(무)흥국생명 다(多)사랑통합보험V2_인쇄용약관(20250630_21633_21634)_v2_공시.pdf",
     "ENC-B5", "(무)흥국생명 다(多)사랑통합보험V2_사업(202504).pdf",
     "ENC-C5", "(무)흥국생명 다(多)사랑통합보험V2_상품요약서(20250521).pdf"],
]
NAME = "(무)흥국생명 다(多)사랑통합보험V2"
DOCS_TEXT = NAMES_PART + "%||%null%||%" + "%|%".join("%,%".join(r) for r in ROWS) + "\n"
# 검색어만 보냈을 때, 상품명이 맞지 않을 때: 서류 행 자리가 줄바꿈 하나다
SEARCH_TEXT = NAMES_PART + "%||%null%||%\n"
# 내려받기 실패(없는 파일, 빈 암호값): 상태 200, text/html, alert 스크립트 164바이트
FAILED = ("<SCRIPT LANGUAGE='JavaScript'>\n<!-- \n\n    alert('파일을 다운로드하는데 실패했습니다. \\n"
          "입출력 에러가 발생하였습니다.'); \n\n    history.back(); \n\n//--> \n\n</SCRIPT> \n\n").encode("cp949")


def test_escape_twice_matches_what_the_page_sent():
    # 실제로 응답을 받은 요청 본문에서 옮김
    assert hk.escape_twice("(무)흥국생명 다(多)사랑") == (
        "%28%25EB%25AC%25B4%29%25ED%259D%25A5%25EA%25B5%25AD%25EC%2583%259D%25EB%25AA%2585%2520"
        "%25EB%258B%25A4%28%25E5%25A4%259A%29%25EC%2582%25AC%25EB%259E%2591")
    assert hk.escape_twice("건강보험") == "%25EA%25B1%25B4%25EA%25B0%2595%25EB%25B3%25B4%25ED%2597%2598"
    assert hk.escape_twice("") == ""


def test_names():
    assert hk.parse_names(DOCS_TEXT) == ["(무) 흥국생명 3.6.5.1원플러스간편건강보험(해약환급금미지급형V2)",
                                         NAME, "(무)흥국생명 다사랑3N5간편건강보험"]
    assert hk.parse_names("null%||%null%||%\n") == []


def test_documents_skip_empty_file_names_and_clean_codes():
    docs = hk.parse_documents(NAME, DOCS_TEXT)
    assert len(docs) == 3 * 5 - 2   # 판매 중인 두 행에 요약서 파일 이름이 없다
    first = [d for d in docs if d.seq == "4388"]
    assert [d.kind for d in first] == ["약관", "사업방법서"]
    assert first[1].enc == "ENC-B1" and first[1].start == "2026-11-02" and first[1].end is None
    renew = next(d for d in docs if d.seq == "4387")
    assert renew.code == "P0001501~P0001801 갱신형" and renew.codes == ("P0001501", "P0001801")
    old = next(d for d in docs if d.seq == "3981")
    assert old.codes == ("P2163300", "P2163400") and old.end == "2025-07-31"
    assert hk.parse_documents(NAME, SEARCH_TEXT) == []


def test_pick_version_fills_missing_summary_from_previous_period():
    docs = hk.parse_documents(NAME, DOCS_TEXT)
    latest = hk.pick_version(docs)
    assert {(d.kind, d.seq) for d in latest} == {("약관", "4388"), ("사업방법서", "4388"), ("약관", "4387"),
                                                  ("사업방법서", "4387"), ("상품요약서", "4333"), ("상품요약서", "4332")}
    summary = next(d for d in latest if d.kind == "상품요약서" and d.code == "P0001901~P0002201")
    assert (summary.start, summary.end, summary.enc) == ("2026-08-10", "2026-11-01", "ENC-C3")
    assert all(d.kind != "상품요약서" for d in hk.pick_version(docs, fill_summary=False))
    assert {d.seq for d in hk.pick_version(docs, "2026-09-01")} == {"4333", "4332"}
    assert {d.seq for d in hk.pick_version(docs, "2025-07-01")} == {"3981"}
    assert hk.pick_version(docs, "2025-01-01") == []


def test_bad_shape_is_raised():
    with pytest.raises(ValueError, match="꼴이 다름"):
        hk.parse_names("<html><body>점검 중</body></html>")


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def post(self, url, **kw):
        self.sent.append((url, kw))
        body, headers = self.replies.pop(0)

        class R:
            content = body

            def raise_for_status(self):
                pass

        R.headers = headers
        return R()


def test_list_documents_sends_what_the_page_sends():
    s = FakeSession([(DOCS_TEXT.encode("cp949"), {"Content-Type": "text/html; charset=EUC-KR"})])
    docs = hk.list_documents(s, NAME)
    assert {d.kind for d in docs} == {"약관", "사업방법서", "상품요약서"}
    url, kw = s.sent[0]
    assert url == "https://www.heungkuklife.co.kr/front/public/saleProductAjax.do"
    assert kw["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert kw["data"].decode() == ("searchFlgSale=Y&beforeYn=&searchCdPublicPrtType1=I101&searchCdPublicPrtType2="
                                   "&searchCdPublicPrtType3=" + hk.escape_twice(NAME) + "&searchText=")


def test_list_products_stopped_tab_and_search():
    s = FakeSession([(SEARCH_TEXT.encode("cp949"), {})])
    products = hk.list_products(s, selling=False, search="건강보험")
    assert [p.name for p in products][1] == NAME and not products[0].selling
    assert s.sent[0][1]["data"].decode() == (
        "searchFlgSale=N&beforeYn=N&searchCdPublicPrtType1=I101&searchCdPublicPrtType2=&searchCdPublicPrtType3="
        "&searchText=%25EA%25B1%25B4%25EA%25B0%2595%25EB%25B3%25B4%25ED%2597%2598")


def test_download_form_and_failures():
    doc = hk.parse_documents(NAME, DOCS_TEXT)[1]
    ok = (b"%PDF-1.6\r%...", {"Content-Type": "application/octet-stream; charset=ISO-8859-1",
                              "Content-Disposition": "attachment; filename=20260807202427001100772100.pdf"})
    s = FakeSession([ok])
    assert hk.download(s, doc).startswith(b"%PDF-")
    url, kw = s.sent[0]
    assert url == "https://www.heungkuklife.co.kr/servlet/DownLoadEnc.do"
    assert [k for k, _ in kw["files"]] == ["searchFlgSale", "searchCdPublicPrtType1", "searchCdPublicPrtType2",
                                           "searchCdPublicPrtType3", "beforeYn", "encValue", "searchText"]
    assert dict(kw["files"])["encValue"] == (None, b"ENC-B1")
    with pytest.raises(ValueError, match="입출력 에러"):
        hk.download(FakeSession([(FAILED, {"Content-Type": "text/html; charset=euc-kr"})]), doc)
    # 화면 스크립트가 처리하는 일일 한도 응답. 실제로 받아 본 적은 없다
    with pytest.raises(ValueError, match="횟수 초과"):
        hk.download(FakeSession([(b"", {"Content-Disposition": "attachment; filename=DOWN_LIMIT"})]), doc)
