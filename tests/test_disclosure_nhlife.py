import pytest

try:
    from postlife.disclosure import nhlife
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import nhlife

# 2026-11-19에 공시실에서 받은 응답의 꼴 (행은 실제 응답에서 골라 옮기고 메뉴, 빈 줄, 꾸밈은 덜어냄)
# 상품 목록 (판매중, 건강/재해보험 2쪽). 화면 위쪽 검색 단추도 linkPage(1)을 부른다
LIST = """
<button type="button" class="wid150" onclick="linkPage(1); return false;">검 색</button>
<p style="position:absolute;top:-20px;font-weight:bold;">전체 22 건</p>
<table class="tbl_Type01 mb8 fs14"><thead><tr><th scope="col">보험종류</th><th scope="col">상품명</th>
<th scope="col">판매여부</th><th scope="col">기간별 다운로드</th></tr></thead>
<tbody>
  <tr>
    <th scope="row">
        건강/재해보험
    </th>
    <td class="tLeft" title="건강플러스NH통합보험(무배당)_2609" >건강플러스NH통합보험(무배당)_2609</td>
    <td>
        판매중
    </td>
    <td>
      <span class="button large"><button type="button" onclick="goAnonm(this.value, '1');" value="건강플러스NH통합보험(무배당)_2609" title="확인">확인</button></span>
    </td>
  </tr>
  <tr>
    <th scope="row">
        건강/재해보험
    </th>
    <td class="tLeft" title="백세팔팔NH건강보험(갱신형,비갱신형,무배당)_2506" >백세팔팔NH건강보험(갱신형,비갱신형,무배당)_2506</td>
    <td>
        판매중
    </td>
    <td>
      <span class="button large"><button type="button" onclick="goAnonm(this.value, '1');" value="백세팔팔NH건강보험(갱신형,비갱신형,무배당)_2506" title="확인">확인</button></span>
    </td>
  </tr>
</tbody></table>
<div class="pagenate">
<p class="paging"><span><button type="button" onclick="linkPage(1);return false; ">1</button></span>&#160;<span class="selected"><button type="button">2</button></span>&#160;<span><button type="button" onclick="linkPage(3);return false; ">3</button></span>&#160;
</p></div>
"""
# 판매중지 목록 한 행. 쪽이 10개를 넘으면 '마지막 페이지 이동' 단추에 끝 쪽 번호가 있다
LIST_STOPPED = """
<p style="position:absolute;top:-20px;font-weight:bold;">전체 267 건</p>
<tbody>
  <tr><th scope="row">건강/재해보험</th>
    <td class="tLeft" title="(무)NH꼭필요한암보험" >(무)NH꼭필요한암보험</td>
    <td>판매중지</td>
    <td><span class="button large"><button type="button" onclick="goAnonm(this.value, '1');" value="(무)NH꼭필요한암보험" title="확인">확인</button></span></td>
  </tr>
</tbody>
<p class="paging"><span class="selected"><button type="button">1</button></span>&#160;<span><button type="button" onclick="linkPage(10);return false; ">10</button></span>&#160;<span><button class="pagingBtn next" type="button" onclick="linkPage(11);return false; "><em>다음 페이지 이동</em></button></span>&#160;<span><button class="pagingBtn last" type="button" onclick="linkPage(27);return false; "><em>마지막 페이지 이동</em></button></span>&#160;
"""
# 검색 결과가 없을 때
LIST_EMPTY = """
<button type="button" class="wid150" onclick="linkPage(1); return false;">검 색</button>
<p style="position:absolute;top:-20px;font-weight:bold;">전체 0 건</p>
<tbody>
<tr>
<td colspan=4>
데이터가 없습니다.
</td>
</tr>
</tbody>
"""


def _popup_row(span, file_id):
    cells = "".join(
        f"""<td><span class="button small icon"><span class="pdf"><button type="button" onclick="popupPdfViewer('{file_id}', '{i}')"><span class="hide">핑크케어NH건강보험(무배당) {k} 다운로드</span></button></span></span></td>"""
        for i, k in enumerate(("상품요약서", "사업방법서", "보험약관")))
    return f"""<!-- 첨부파일 번호 세팅 -->\n<tr>\n<td>\n\t\t\t{span}\n</td>\n{cells}\n</tr>"""


# 서류 목록 (판매기간 6건 가운데 첫 쪽 5건 중 둘). 새 기간이 위에 오고, 열린 기간은 '~ 현재'다
POPUP = f"""
<input type="hidden" id="popSelProdNm" value="핑크케어NH건강보험(무배당)"/>
<div class="box_type3 mb15"><h5 class="product_title">핑크케어NH건강보험(무배당)</h5></div>
<p style="margin-bottom:revert; font-weight:bold;">전체 <strong>6</strong> 건</p>
<table><thead><tr><th scope="col">판매기간</th><th scope="col">상품요약서</th><th scope="col">사업방법서</th><th scope="col">보험약관</th></tr></thead>
<tbody>
{_popup_row("2026-09-01 ~ 현재", "FILE_000000000024581")}
{_popup_row("2026-01-01 ~ 2026-08-31", "FILE_000000000023626")}
</tbody></table>
<div class="pagenate"><p class="paging"><span class="selected"><button type="button">1</button></span>&#160;<span><button type="button" onclick="popLinkPage(2);return false; ">2</button></span>&#160;
</p></div>
"""
POPUP_P2 = f"""
<h5 class="product_title">핑크케어NH건강보험(무배당)</h5>
<p>전체 <strong>6</strong> 건</p>
<tbody>
{_popup_row("2024-09-01 ~ 2024-12-31", "FILE_000000000021000")}
</tbody>
<p class="paging"><span><button type="button" onclick="popLinkPage(1);return false; ">1</button></span>&#160;<span class="selected"><button type="button">2</button></span>&#160;</p>
"""
# 보험상품 메뉴(HOIG0010M00)의 왼쪽 목록
MENU = """
<li><a href="#NHLife" onclick="goTotPage('CTGR01');" id="CTGR01">종신/정기보험</a>
<ul class="snbDep" id="CTGR01">
    <li><a href="#NHLife" onclick="goPage('N0001224');" id="N0001224">퍼펙트라이프NH종신보험(해약환급금일부지급형,무배당)_2611</a></li>
</ul></li>
<li><a href="#NHLife" onclick="goTotPage('CTGR04');" id="CTGR04">건강/재해보험</a>
<ul class="snbDep" id="CTGR04">
    <li><a href="#NHLife" onclick="goPage('N0001217');" id="N0001217">건강플러스NH통합보험(무배당)_2609</a></li>
    <li><a href="#NHLife" onclick="goPage('N0001148');" id="N0001148">백세팔팔NH건강보험(갱신형,비갱신형,무배당)_2506</a></li>
</ul></li>
"""
# 없는 순번(fileSeqn=9)을 내려받으려 했을 때: 상태 200, text/html, 1,797바이트의 오류 화면
ERROR_PAGE = ("\n\n\n<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\">\n<html><head><title>NH농협생명</title></head>"
              "<body><p>네트워크 장애로 서비스를 이용하실 수 없습니다.</p><p>잠시 후 다시 접속해 주십시오.</p></body></html>")


def test_list_rows_names_and_pages():
    page = nhlife.parse_list(LIST)
    assert page.total == 22 and page.pages == 3
    assert [p.name for p in page.rows] == ["건강플러스NH통합보험(무배당)_2609",
                                           "백세팔팔NH건강보험(갱신형,비갱신형,무배당)_2506"]
    assert page.rows[0].kind == "건강/재해보험" and page.rows[0].selling
    stopped = nhlife.parse_list(LIST_STOPPED)
    assert stopped.pages == 27 and not stopped.rows[0].selling and stopped.rows[0].name == "(무)NH꼭필요한암보험"
    empty = nhlife.parse_list(LIST_EMPTY)
    assert (empty.total, empty.rows, empty.pages) == (0, (), 1)


def test_popup_periods_and_documents():
    page = nhlife.parse_popup(POPUP)
    assert page.total == 6 and page.pages == 2
    open_, closed = page.rows
    assert (open_.start, open_.end) == ("2026-09-01", None) and closed.end == "2026-08-31"
    assert [(d.kind, d.seq) for d in open_.documents] == [("상품요약서", "0"), ("사업방법서", "1"), ("약관", "2")]
    assert open_.document("사업방법서").file_id == "FILE_000000000024581"
    assert open_.documents[0].name == "핑크케어NH건강보험(무배당)"
    assert nhlife.pick_period(page.rows).start == "2026-09-01"
    assert nhlife.pick_period(page.rows, "2026-03-01").start == "2026-01-01"
    assert nhlife.pick_period(page.rows, "2025-12-31") is None


def test_menu_codes():
    codes = nhlife.parse_menu_codes(MENU)
    assert codes["건강플러스NH통합보험(무배당)_2609"] == ("N0001217", "건강/재해보험")
    assert codes["퍼펙트라이프NH종신보험(해약환급금일부지급형,무배당)_2611"] == ("N0001224", "종신/정기보험")


def test_error_page_is_raised():
    with pytest.raises(ValueError, match="전체 N 건"):
        nhlife.parse_list(ERROR_PAGE)
    with pytest.raises(ValueError, match="상품명"):
        nhlife.parse_popup(ERROR_PAGE)


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else reply.encode("utf-8")
            text = reply if isinstance(reply, str) else ""
            headers = {"Content-Type": "application/octet-stream;charset=UTF-8" if isinstance(reply, bytes)
                       else "text/html; charset=UTF-8"}
            encoding = None

            def raise_for_status(self):
                pass

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def test_list_products_walks_pages_with_page_form():
    s = FakeSession([LIST, LIST, LIST])   # 22건이라 3쪽. 쪽마다 같은 표본을 돌려준다
    rows = nhlife.list_products(s, selling=True, category="CTGR04")
    assert len(rows) == 6 and len(s.sent) == 3
    (m1, url1, kw1), (_, _, kw2), (_, _, kw3) = s.sent
    assert (m1, url1) == ("POST", "https://www.nhlife.co.kr/ho/on/HOON0004M00.nhl")
    assert kw1["data"] == {"prsPagcn": "1", "selProdNm": "", "useyn": "Y", "prodDcd": "CTGR04", "prodnm": ""}
    assert kw2["data"]["prsPagcn"] == "2" and kw3["data"]["prsPagcn"] == "3"
    assert kw1["headers"]["Content-Type"].startswith("application/x-www-form-urlencoded")
    s = FakeSession([LIST_EMPTY])
    assert nhlife.list_products(s, selling=None, keyword="간편") == []
    assert s.sent[0][2]["data"]["useyn"] == "" and s.sent[0][2]["data"]["prodnm"] == "간편"


def test_list_periods_reads_every_popup_page():
    s = FakeSession([POPUP, POPUP_P2])
    periods = nhlife.list_periods(s, "핑크케어NH건강보험(무배당)")
    assert [p.start for p in periods] == ["2026-09-01", "2026-01-01", "2024-09-01"]
    (_, url1, kw1), (_, _, kw2) = s.sent
    assert url1 == "https://www.nhlife.co.kr/ho/on/HOON0004P10.nhl"
    assert kw1["data"]["selProdNm"] == "핑크케어NH건강보험(무배당)" and kw2["data"]["prsPagcn"] == "2"
    docs = nhlife.list_documents(FakeSession([POPUP, POPUP_P2]), "핑크케어NH건강보험(무배당)", on="2026-05-01")
    assert {d.file_id for d in docs} == {"FILE_000000000023626"}


def test_download_url_and_non_pdf():
    doc = nhlife.parse_popup(POPUP).rows[0].document("상품요약서")
    s = FakeSession([b"%PDF-1.6\r%\xff\xff\xff\xff\n..."])
    assert nhlife.download(s, doc).startswith(b"%PDF-")
    # 실제로 받은 주소와 같은 꼴 (건강플러스 요약서: apdFlid=FILE_000000000024583&fileSeqn=0)
    assert s.sent[0][:2] == ("GET", "https://www.nhlife.co.kr/pdfViewer.nhl?apdFlid=FILE_000000000024581&fileSeqn=0")
    assert s.sent[0][2]["headers"]["Referer"].startswith("https://www.nhlife.co.kr/pdfViewerPopup.nhl?")
    with pytest.raises(ValueError, match="PDF가 아닌 응답"):   # 없는 파일: 상태 200, 오류 화면
        nhlife.download(FakeSession([ERROR_PAGE]), doc)


def test_file_name_from_header():
    raw = "[상품요약서]건강플러스NH통합보험(무배당)_2609_vf.pdf".encode("utf-8").decode("latin-1")
    assert nhlife.file_name_of({"Content-Disposition": f'attachment;filename="{raw}"'}) == \
        "[상품요약서]건강플러스NH통합보험(무배당)_2609_vf.pdf"
    assert nhlife.file_name_of({}) == ""
