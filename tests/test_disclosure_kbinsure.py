from urllib.parse import parse_qsl

import pytest

try:
    from postlife.disclosure import kbinsure
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import kbinsure

# 2026-11-19에 공시실에서 받은 응답의 형태 (화면은 EUC-KR HTML이다. 행은 실제 응답에서 골라 옮기고 메뉴는 뺐다)
# 목록(/CG802030001.ec). 판매중과 판매중지는 줄바꿈 자리가 다르다. 쪽 넘김 단추에 다음 쪽 첫 행 번호가 있다
LIST_HTML = """<form id="prdtList" name="prdtList" method="post" action="/CG802030001.ec">
<input type="hidden" name="devonTargetRow" id="devonTargetRow" value="1" />
<table class="tb_list"><tbody>
\t\t<tr>
\t\t\t<td>판매중
\t\t\t\t</td>
\t\t\t<td>상해보험</td>
\t\t\t<td>25442</td>
\t\t\t<td class="tx_lt thnone"><a href="javascript:detail('25442','c','1');">KB Yes!365 건강보험(세만기)(무배당)(26.09)</a>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>판매중
\t\t\t\t</td>
\t\t\t<td>제휴</td>
\t\t\t<td>25444</td>
\t\t\t<td class="tx_lt thnone"><a href="javascript:detail('25444','g','1');">KB 해피365 건강보험(세만기)(무배당)(26.09)</a>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t\t판매중지</td>
\t\t\t<td>일반보험</td>
\t\t\t<td>14138</td>
\t\t\t<td class="tx_lt thnone"><a href="javascript:detail('14138','1','1');">화재배상책임보험</a>
\t\t\t</td>
\t\t</tr>
</tbody></table>
<div class="paging mgt15">
  <span style="font-weight:bold;">1</span>&nbsp;|&nbsp;<a href="#" onclick="goPage('11'); return false;" title="2 페이지로 이동">2</a>
  <a href="#" onclick="goPage('101'); return false;" title="다음 인덱스로 이동"></a>
  <a href="#" onclick="goPage('4081'); return false;" title="끝 페이지로 이동"></a>
</div>
</form>"""
# 마지막 쪽: 쪽 넘김 단추에 goPage가 없다 (devonRowSize=200으로 96행이 한 번에 온 응답)
LAST_PAGE_HTML = """<form id="prdtList" name="prdtList" method="post" action="/CG802030001.ec"><table><tbody>
\t\t<tr>
\t\t\t<td>판매중
\t\t\t\t</td>
\t\t\t<td>상해보험</td>
\t\t\t<td>25422</td>
\t\t\t<td class="tx_lt thnone"><a href="javascript:detail('25422','c','1');">KB 3.N.5 슬기로운 간편건강보험Plus(세만기)(무배당)(26.09)</a>
\t\t\t</td>
\t\t</tr>
</tbody></table>
<div class="paging mgt15">
  <span style="font-weight:bold;">1</span>
</div></form>"""


def detail_html(title, rows):
    body = ""
    for start, end, files, note in rows:
        cells = "".join(f'<td>\n<a href="/CG802030003.ec?fileNm={f}" ><img src="/images/common/button/btn_check_pdf.gif" '
                        f'alt="PDF 보기"></a>\n</td>' for f in files)
        body += (f'<tr>\n<td class="vfont_s02">{start}</td>\n<td class="vfont_s02">{end}</td>\n{cells}\n'
                 f'<td  class="thnone">{note}</td>\n</tr>\n')
    return (f'<table class="tb_view"><tbody><tr>\n<td class="tit">\n\t\t\t\t{title}\n\t\t\t</td>\n</tr>'
            f'<tr><td class="thnone"><table class="tb_default04" summary="판매시작일, 판매종료일 …">'
            f'<caption>{title}</caption><thead><tr><th scope="col">판매시작일</th><th scope="col">판매종료일</th>'
            f'<th scope="col">보험약관</th><th scope="col">사업방법서</th><th scope="col">상품요약서</th>'
            f'<!--  <th scope="col">설명서</th> --><th scope="col" class="thnone">비고</th></tr></thead>'
            f'<tbody>\n{body}</tbody></table></td></tr></tbody></table>')


# 상세(/CG802030002.ec). 열린 판매기간은 종료일 칸이 빈칸이다. 확장자 대소문자가 섞여 온다
DETAIL_HTML = detail_html("[상해보험] KB 닥터플러스 건강보험(세만기)(무배당)(26.09)", [
    ("20260901", "20260930", ["25443_1_1.pdf", "25443_1_2.pdf", "25443_1_3.pdf"], ""),
    ("20261001", "        ", ["25443_2_1.pdf", "25443_2_2.pdf", "25443_2_3.Pdf"], ""),
])
# 간편심사 상품: 같은 판매기간에 간편심사형과 일반심사형 두 행이 있고 파일 이름에 (간편), (일반)이 붙는다
DETAIL_SIMPLE_HTML = detail_html("[상해보험] KB 3.N.5 슬기로운 간편건강보험Plus(세만기)(무배당)(26.09)", [
    ("20260901", "20260930", ["25422_1_1(간편).pdf", "25422_1_2(간편).pdf", "25422_1_3(간편).Pdf"], "간편심사형"),
    ("20260901", "20260930", ["25422_1_1(일반).pdf", "25422_1_2(일반).Pdf", "25422_1_3(일반).pdf"], "일반심사형"),
    ("20261001", "        ", ["25422_2_1(간편).pdf", "25422_2_2(간편).pdf", "25422_2_3(간편).pdf"], "간편심사형"),
    ("20261001", "        ", ["25422_2_1(일반).pdf", "25422_2_2(일반).pdf", "25422_2_3(일반).pdf"], "일반심사형"),
])
# 없는 파일을 내려받으려 할 때: 상태 200, 오류 화면 HTML
ERROR_HTML = """<title>상품목록(약관)(약관다운로드) | KB손해보험 [A]</title>
<script type="text/javascript">var _jrl2 = '/CG802030003.ec?jsp=error.jsp';</script>
<script type="text/javascript">xTrackerError("","01","default","해당 파일이 존재하지 않습니다.".replace(/\\\\n/g, '\\r\\n'),"","")</script>
<div class="error_visual bdGray2"><p><img src="/images/common/comm/tit_error_sorry.gif" alt="고객님, 대단히 죄송합니다."></p></div>"""


def euc(text):
    return text.encode("cp949")


def test_list_rows_and_status():
    products = kbinsure.parse_products(euc(LIST_HTML))
    assert [(p.code, p.kind, p.gubun, p.seq, p.selling) for p in products] == [
        ("25442", "상해보험", "c", "1", True), ("25444", "제휴", "g", "1", True), ("14138", "일반보험", "1", "1", False)]
    assert products[0].name == "KB Yes!365 건강보험(세만기)(무배당)(26.09)"
    assert kbinsure.next_row(euc(LIST_HTML), 1) == 11
    assert kbinsure.next_row(euc(LAST_PAGE_HTML), 1) is None
    with pytest.raises(ValueError, match="목록 화면이 아님"):
        kbinsure.parse_products(euc("<html><body>점검 중</body></html>"))


def test_detail_periods_and_documents():
    title, periods = kbinsure.parse_detail(euc(DETAIL_HTML))
    assert kbinsure.split_title(title) == ("상해보험", "KB 닥터플러스 건강보험(세만기)(무배당)(26.09)")
    assert [(p.start, p.end, p.note) for p in periods] == [("2026-09-01", "2026-09-30", ""), ("2026-10-01", None, "")]
    assert periods[1].files == {"약관": "25443_2_1.pdf", "사업방법서": "25443_2_2.pdf", "상품요약서": "25443_2_3.Pdf"}
    product = kbinsure.Product("25443", "KB 닥터플러스 건강보험(세만기)(무배당)(26.09)", "상해보험", "c")
    docs = kbinsure.documents_of(product, periods)
    assert [(d.kind, d.file_name, d.period_no) for d in docs][2] == ("상품요약서", "25443_2_3.Pdf", "2")
    assert {d.file_name for d in kbinsure.documents_of(product, periods, on="2026-09-15")} == {
        "25443_1_1.pdf", "25443_1_2.pdf", "25443_1_3.pdf"}
    assert kbinsure.documents_of(product, periods, on="2026-08-31") == []


def test_simple_product_has_two_rows_per_period():
    _, periods = kbinsure.parse_detail(euc(DETAIL_SIMPLE_HTML))
    latest = kbinsure.pick_periods(periods)
    assert [(p.start, p.note) for p in latest] == [("2026-10-01", "간편심사형"), ("2026-10-01", "일반심사형")]
    product = kbinsure.Product("25422", "KB 3.N.5 슬기로운 간편건강보험Plus(세만기)(무배당)(26.09)", "상해보험", "c")
    docs = kbinsure.documents_of(product, periods, note="간편심사형")
    assert [d.file_name for d in docs] == ["25422_2_1(간편).pdf", "25422_2_2(간편).pdf", "25422_2_3(간편).pdf"]
    assert {d.note for d in docs} == {"간편심사형"}
    assert kbinsure.file_parts("25422_2_3(간편).pdf") == ("25422", "2", "3", "간편")
    assert kbinsure.file_parts("25443_2_3.Pdf") == ("25443", "2", "3", "")
    assert kbinsure.file_parts("이름만.pdf") == ("", "", "", "")


def test_error_page_is_raised():
    with pytest.raises(ValueError, match="해당 파일이 존재하지 않습니다"):
        kbinsure.parse_detail(euc(ERROR_HTML))


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply
            headers = {"Content-Type": "application/octet-stream" if reply.startswith(b"%PDF-")
                       else "text/html; charset=euc-kr"}

            def raise_for_status(self):
                pass

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def form(sent):
    return dict(parse_qsl(sent[2]["data"], encoding="cp949", keep_blank_values=True))


def test_list_products_sends_euc_kr_form_and_pages():
    s = FakeSession([euc(LIST_HTML), euc(LAST_PAGE_HTML)])
    products = kbinsure.list_products(s, "건강", rows=10)
    assert [p.code for p in products] == ["25442", "25444", "14138", "25422"]
    (m1, url1, kw1), (m2, url2, _) = s.sent
    assert (m1, url1) == ("POST", "https://www.kbinsure.co.kr/CG802030001.ec") and url2 == url1
    assert kw1["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert "goodsNm=%B0%C7%B0%AD" in kw1["data"]             # "건강"을 EUC-KR로 싸서 보낸다
    first, second = form(s.sent[0]), form(s.sent[1])
    assert first == {"devonTargetRow": "1", "devonOrderBy": "", "devonRowSize": "10", "gubun": " ", "goodsNm": "건강",
                     "onsaleYn": "Y", "bojongNo": "", "bojongSeq": "", "search_onsale_yn": "Y", "search_bojong_no": "",
                     "search_gubun": " ", "search_goods_nm": "건강"}
    assert second["devonTargetRow"] == "11"
    s = FakeSession([euc(LAST_PAGE_HTML)])
    kbinsure.list_products(s, "", selling=None, gubun="c", code="25422")
    assert {k: v for k, v in form(s.sent[0]).items() if k in ("onsaleYn", "gubun", "bojongNo")} == {
        "onsaleYn": " ", "gubun": "c", "bojongNo": "25422"}


def test_list_documents_sends_what_detail_sends():
    s = FakeSession([euc(DETAIL_SIMPLE_HTML)])
    product = kbinsure.Product("25422", "KB 3.N.5 슬기로운 간편건강보험Plus(세만기)(무배당)(26.09)", "상해보험", "c")
    docs = kbinsure.list_documents(s, product, note="일반심사형")
    assert [d.kind for d in docs] == ["약관", "사업방법서", "상품요약서"] and docs[0].file_name == "25422_2_1(일반).pdf"
    assert s.sent[0][1] == "https://www.kbinsure.co.kr/CG802030002.ec"
    sent = form(s.sent[0])
    assert (sent["bojongNo"], sent["gubun"], sent["bojongSeq"]) == ("25422", "c", "1")


def test_download_url_and_non_pdf():
    doc = kbinsure.Document("25422", "슬기로운", "상품요약서", "25422_2_3(간편).pdf", "2026-10-01", None, "간편심사형")
    s = FakeSession([b"%PDF-1.5 ..."])
    assert kbinsure.download(s, doc).startswith(b"%PDF-")
    # 실제로 내려받기에 성공한 주소와 같은 꼴: 한글은 EUC-KR로 싸고 괄호는 그대로 둔다
    assert s.sent[0][:2] == ("GET", "https://www.kbinsure.co.kr/CG802030003.ec?fileNm=25422_2_3(%B0%A3%C6%ED).pdf")
    assert kbinsure.download_url("25443_2_3.Pdf").endswith("fileNm=25443_2_3.Pdf")
    with pytest.raises(ValueError, match="해당 파일이 존재하지 않습니다"):   # 없는 파일: 상태 200, 오류 화면
        kbinsure.download(FakeSession([euc(ERROR_HTML)]), doc)
