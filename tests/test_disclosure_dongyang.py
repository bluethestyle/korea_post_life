import pytest

try:
    from postlife.disclosure import dongyang
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import dongyang

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮기고 빈칸과 빈 줄만 줄임)
# 판매상품 목록 한 쪽: 서버가 그린 HTML 표. 지난 판매기간이 있는 행만 상품명에 selectDetailGoods 링크가 있다
ROW_WITH_HISTORY = """<tr>
<td>48</td>
<td>
\t일반보험
</td>
<td>
\t보장성
</td>
<td class="tleft tb_1depth">
\t<a class="off" href="javascript:void(0);" onclick="javascript:selectDetailGoods(this, '무배당우리WON하는보장보험', '48','01', fnCallback);">
\t무배당우리WON하는보장보험
\t</a>
</td>
<td>
\t2026.10.01
</td>
<td>
\t
</td>
<td>
\t<a href="javascript:MasFiledownload('_N', '34D0mcpfsYRy3uc50Abppyaqd8pb0SwZ');"><img src="/image/common/icon_pdf.gif" alt="상품요약서 다운로드" /></a>
</td>
<td>
\t<a href="javascript:MasFiledownload('_N', '34D0mcpfsYRy3uc50Abpp8K7XF+/qrto')"><img src="/image/common/icon_pdf.gif" alt="사업방법서 다운로드" /></a>
</td>
<td>
\t<a href="javascript:MasFiledownload('_N', '34D0mcpfsYRy3uc50Abppxh90DL2Orhz')"><img src="/image/common/icon_pdf.gif" alt="보험약관 다운로드" /></a>\t\t\t\t\t\t
</td>
<td class="lastCell">
\t-
\t<!-- a href="javascript:alert('준비중입니다.');"><img src="/image/common/icon_pdf.gif" alt="운용관리 계약서 다운로드" /></a-->
</td>
</tr>"""
ROW_NO_HISTORY = """<tr>
<td>59</td>
<td>일반보험 </td>
<td>보장성 </td>
<td class="tleft tb_1depth">
\t무배당우리WON하는치아보험(갱신형)
</td>
<td>2026.01.01 </td>
<td> </td>
<td><a href="javascript:MasFiledownload('_N', '34D0mcpfsYQWEyAEH7Es8KuhlkrAYgFr');"><img src="/image/common/icon_pdf.gif" alt="상품요약서 다운로드" /></a></td>
<td><a href="javascript:MasFiledownload('_N', '34D0mcpfsYQWEyAEH7Es8KKXUf7UiR8H')"><img src="/image/common/icon_pdf.gif" alt="사업방법서 다운로드" /></a></td>
<td><a href="javascript:MasFiledownload('_N', '34D0mcpfsYQWEyAEH7Es8HhmkEuJniG2')"><img src="/image/common/icon_pdf.gif" alt="보험약관 다운로드" /></a></td>
<td class="lastCell">-</td>
</tr>"""
# 상품요약서가 없는 칸은 alert 링크이고, 퇴직연금 상품에는 운용관리계약서가 있다
ROW_RETIREMENT = """<tr>
<td>31</td>
<td>단체보험 </td>
<td>퇴직연금/보험 </td>
<td class="tleft tb_1depth">
\t<a class="off" href="javascript:void(0);" onclick="javascript:selectDetailGoods(this, '무배당확정기여형자산관리퇴직연금보험', '31','02', fnCallback);">
\t무배당확정기여형자산관리퇴직연금보험
\t</a>
</td>
<td>2025.04.01 </td>
<td></td>
<td><a href="javascript:alert('준비중입니다ALL.');"><img src="/image/common/icon_pdf.gif" alt="상품요약서 다운로드" /></a></td>
<td><a href="javascript:MasFiledownload('_N', 'zGwYr/sGvoZbqRZnU1E1su/IBdKoijhr')"><img src="/image/common/icon_pdf.gif" alt="사업방법서 다운로드" /></a></td>
<td><a href="javascript:MasFiledownload('_N', 'zGwYr/sGvoZbqRZnU1E1sgTRbp6b2ZK7')"><img src="/image/common/icon_pdf.gif" alt="보험약관 다운로드" /></a></td>
<td class="lastCell"><a href="javascript:MasFiledownload('_N', 'zGwYr/sGvoZbqRZnU1E1sp95kLJ0DkBF')" class="lastCell"><img src="/image/common/icon_pdf.gif" alt="운용관리 계약서 다운로드" /></a></td>
</tr>"""


# 상품명으로 거른 응답: 이름 속 검색어를 <b>로 감싸 오고, 번호를 다시 매긴다 (nameStr=보장보험, sale_kind=01)
ROW_SEARCHED = """<tr>
<td>3</td>
<td>
\t일반보험
</td>
<td>
\t보장성
</td>
<td class="tleft tb_1depth">
\t <a class="off" href="javascript:void(0);" onclick="javascript:selectDetailGoods(this, '무배당우리WON하는간편보장보험(갱신형)', '3','01', fnCallback);">
\t\t무배당우리WON하는간편<b>보장보험</b>(갱신형)
\t</a>
</td>
<td>
\t2026.07.01
</td>
<td></td>
<td><a href="javascript:MasFiledownload('_N', '34D0mcpfsYTtnFS3GP9AANziQTwQxIOX');"><img src="/image/common/icon_pdf.gif" alt="상품요약서 다운로드" /></a></td>
<td><a href="javascript:MasFiledownload('_N', '34D0mcpfsYTtnFS3GP9AAArReS1MAfHz')"><img src="/image/common/icon_pdf.gif" alt="사업방법서 다운로드" /></a></td>
<td><a href="javascript:MasFiledownload('_N', '34D0mcpfsYTtnFS3GP9AACldMnwDMM13')"><img src="/image/common/icon_pdf.gif" alt="보험약관 다운로드" /></a></td>
<td class="lastCell">-</td>
</tr>"""


def page(rows, total=59):
    return f"""<p class="tableInfo search">
<span class="only">총 <strong>{total}</strong>건</span>
</p>
<table class="tableStyle" summary="전체보험 상품목록의 판매상품을 번호, 판매채널, 구분, 상품명, 판매기간, 상품요약서, 사업방법서, 보험약관, 운용관리계약서로 나타낸 표">
<caption>판매상품</caption>
<thead>
<tr>
<th scope="col">번호</th><th scope="col">판매채널</th><th scope="col">구분</th><th scope="col">상품명</th>
<th scope="col">판매기간(시작)</th><th scope="col">판매기간(종료)</th><th scope="col">상품요약서</th>
<th scope="col">사업방법서</th><th scope="col">보험약관</th><th scope="col" class="lastCell">운용관리계약서</th>
</tr>
</thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
<div class="paging"><ul><li><strong>1</strong></li>
<li><a href="javascript:PP_Query('mainform', 'dw_99', '2');">2</a></li></ul></div>"""


LIST_PAGE = page([ROW_WITH_HISTORY, ROW_NO_HISTORY, ROW_RETIREMENT])
# 없는 주소나 없는 서류 값에 오는 안내 화면 (내려받기는 상태 404로 온다)
NOT_FOUND = ("<html><head><title>수호천사동양생명</title><script>(function(w,d,s,l,i){w[l]=w[l]||[];})"
             "(window,document,'script','dataLayer','GTM');</script></head><body><p>죄송합니다. "
             "현재 요청하신 페이지를 찾을 수 없습니다.</p></body></html>")
# 지난 판매기간: JSON 앞에 빈 줄이 붙어 온다. 닫힌 기간만 오고, 서류가 없는 기간(FILE_GRP_ID가 빈칸)도 있다
HISTORY = "\n\n\n\n\n\n\n\n\n\n" + (
    '{"isLogin":false,"dw":{"dw_00":['
    '{"SALE_FINISH_DT":"20260930","FILE_PATH2":"\\/eGIS\\/webapps\\/hp\\/web\\/filedir\\/gongsi\\/","FILE_GRP_ID4":"",'
    '"FILE_PATH3":"\\/eGIS\\/webapps\\/hp\\/web\\/filedir\\/gongsi\\/","FILE_GRP_ID5":"","SALE_START_DT":"20260901",'
    '"FILE_PATH1":"\\/eGIS\\/webapps\\/hp\\/web\\/filedir\\/gongsi\\/","FILE_NM1":"상품요약서_무배당우리WON하는보장보험_20260901.pdf",'
    '"FILE_GRP_ID1":"34D0mcpfsYSK1WJ0QwIH3c6qRKXBfEgF","INSU_KIND_NM":"","FILE_GRP_ID2":"34D0mcpfsYSK1WJ0QwIH3YnSOu1RGSXv",'
    '"FILE_PATH4":"","GOODS_KIND_NM":"보장성","FILE_GRP_ID3":"34D0mcpfsYSK1WJ0QwIH3cu7t4I8UqAJ","FILE_PATH5":"","FILE_NM4":"",'
    '"FILE_NM5":"","FILE_NM2":"사업방법서_무배당우리WON하는보장보험_20260701.pdf","FILE_NM3":"통합약관_무배당우리WON하는보장보험.pdf",'
    '"INSERT_DT":"20260915160207","SALE_KIND_NM":"일반보험","GOODS_NM":"무배당우리WON하는보장보험"},'
    '{"SALE_FINISH_DT":"20251116","FILE_PATH2":"","FILE_GRP_ID4":"","FILE_PATH3":"","FILE_GRP_ID5":"","SALE_START_DT":"20251001",'
    '"FILE_PATH1":"","FILE_NM1":"","FILE_GRP_ID1":"","INSU_KIND_NM":"","FILE_GRP_ID2":"","FILE_PATH4":"","GOODS_KIND_NM":"보장성",'
    '"FILE_GRP_ID3":"","FILE_PATH5":"","FILE_NM4":"","FILE_NM5":"","FILE_NM2":"","FILE_NM3":"","INSERT_DT":"20251015163702",'
    '"SALE_KIND_NM":"일반보험","GOODS_NM":"무배당우리WON하는보장보험"}]}}')
# 내려받기 응답 머리: UTF-8 파일 이름을 requests가 latin-1로 읽은 꼴
DISPOSITION = "attachment; filename=" + "사업방법서_무배당우리WON하는보장보험_20260701.pdf".encode().decode("latin-1") + ";"


def test_list_rows():
    total, rows = dongyang.parse_list(LIST_PAGE)
    assert total == 59 and [p.no for p in rows] == ["48", "59", "31"]
    p = rows[0]
    assert (p.name, p.channel, p.kind, p.start, p.end) == ("무배당우리WON하는보장보험", "일반보험", "보장성", "2026-10-01", None)
    assert p.files == {"상품요약서": "34D0mcpfsYRy3uc50Abppyaqd8pb0SwZ", "사업방법서": "34D0mcpfsYRy3uc50Abpp8K7XF+/qrto",
                       "약관": "34D0mcpfsYRy3uc50Abppxh90DL2Orhz"}   # 주석 안의 운용관리계약서 링크는 서류가 아니다
    assert p.sale_kind == "01" and p.has_history
    assert rows[1].name == "무배당우리WON하는치아보험(갱신형)" and not rows[1].has_history


def test_missing_document_cell():
    retirement = dongyang.parse_list(LIST_PAGE)[1][2]
    assert set(retirement.files) == {"사업방법서", "약관", "운용관리계약서"}     # alert('준비중입니다ALL.') 칸은 서류가 없다
    assert retirement.sale_kind == "02" and retirement.channel == "단체보험"
    assert [d.kind for d in dongyang.documents_of(retirement)] == ["사업방법서", "약관", "운용관리계약서"]


def test_search_highlight_is_not_part_of_name():
    total, rows = dongyang.parse_list(page([ROW_SEARCHED], total=9))
    assert total == 9 and rows[0].name == "무배당우리WON하는간편보장보험(갱신형)" and rows[0].no == "3"
    assert rows[0].sale_kind == "01" and len(rows[0].files) == 3


def test_not_a_list_page_is_raised():
    with pytest.raises(ValueError, match="목록 표가 없는 응답: .*페이지를 찾을 수 없습니다"):
        dongyang.parse_list(NOT_FOUND)


def test_history_rows():
    periods = dongyang.parse_history(HISTORY)
    assert [(p.start, p.end) for p in periods] == [("2026-09-01", "2026-09-30"), ("2025-10-01", "2025-11-16")]
    p = periods[0]
    assert p.files["사업방법서"] == "34D0mcpfsYSK1WJ0QwIH3YnSOu1RGSXv" and p.channel == "일반보험" and p.kind == "보장성"
    # 사업방법서는 판매기간보다 앞선 날짜의 파일이 그대로 걸려 있다
    assert p.file_names["사업방법서"].endswith("_20260701.pdf")
    assert periods[1].files == {} and dongyang.documents_of(periods[1]) == []
    docs = dongyang.documents_of(p)
    assert [(d.kind, d.start, d.end) for d in docs][0] == ("상품요약서", "2026-09-01", "2026-09-30")


def test_history_bad_shape_is_raised():
    with pytest.raises(ValueError, match="dw.dw_00"):
        dongyang.parse_history('\n\n{"isLogin":false}')
    with pytest.raises(ValueError, match="JSON이 아님"):
        dongyang.parse_history(NOT_FOUND)


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def post(self, url, **kw):
        self.sent.append((url, kw))
        reply = self.replies.pop(0)
        status, body, headers = reply if isinstance(reply, tuple) else (200, reply, {})

        class R:
            status_code = status
            content = body if isinstance(body, bytes) else body.encode("utf-8")
            text = body if isinstance(body, str) else ""
            encoding = None

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(f"HTTP {self.status_code}")

        R.headers = headers
        return R()


def test_list_products_walks_pages_like_the_screen():
    s = FakeSession([page([ROW_WITH_HISTORY, ROW_NO_HISTORY], total=3), page([ROW_RETIREMENT], total=3)])
    products = dongyang.list_products(s)
    assert [p.no for p in products] == ["48", "59", "31"]
    (url1, kw1), (url2, kw2) = s.sent
    assert url1 == url2 == "https://pbano.myangel.co.kr/paging/WE_AC_WEPAAP020100L"
    assert kw1["data"]["_biz_op_code"] == "IQY" and kw1["data"]["_paging_page_idx"] == "1"
    # 화면의 PP_Query('mainform', 'dw_99', '2')와 같은 값
    assert {k: kw2["data"][k] for k in ("_biz_op_code", "_paging_action", "_paging_dw_name", "_paging_page_idx")} == {
        "_biz_op_code": "_Q", "_paging_action": "PP", "_paging_dw_name": "dw_99", "_paging_page_idx": "2"}
    s = FakeSession([page([ROW_WITH_HISTORY], total=1)])
    dongyang.list_products(s, sale_kind="01", search="보장보험")
    assert {k: s.sent[0][1]["data"][k] for k in ("sale_kind", "saleCode", "nameStr", "searchWord", "goods_kind")} == {
        "sale_kind": "01", "saleCode": "01", "nameStr": "보장보험", "searchWord": "보장보험", "goods_kind": "ALL"}


def test_list_documents_current_and_past():
    rows = dongyang.parse_list(LIST_PAGE)[1]
    s = FakeSession([])
    assert [d.kind for d in dongyang.list_documents(s, rows[0])] == ["상품요약서", "사업방법서", "약관"]
    assert dongyang.list_documents(s, rows[0], "2026-11-19")[0].start == "2026-10-01" and s.sent == []   # 요청 없이
    s = FakeSession([HISTORY])
    docs = dongyang.list_documents(s, rows[0], "2026-09-15")
    assert {d.start for d in docs} == {"2026-09-01"} and docs[1].file_name.endswith("_20260701.pdf")
    url, kw = s.sent[0]
    assert url == "https://pbano.myangel.co.kr/process/WE_AC_WEPAAP020100D"
    assert kw["data"] == {"_biz_op_code": "IQY_D", "GOODS_NM": "무배당우리WON하는보장보험", "SALE_KIND": "01"}
    assert dongyang.list_documents(FakeSession([]), rows[1], "2025-01-01") == []   # 지난 판매기간이 없는 상품


def test_download_form_and_non_pdf():
    doc = dongyang.documents_of(dongyang.parse_list(LIST_PAGE)[1][0])[1]
    s = FakeSession([(200, b"%PDF-1.7 ...", {"Content-Type": "application/octet-stream;charset=UTF-8",
                                              "Content-Disposition": DISPOSITION})])
    assert dongyang.download(s, doc).startswith(b"%PDF-")
    url, kw = s.sent[0]
    assert url == "https://pbano.myangel.co.kr/process/CO_ComDownload"
    assert kw["data"] == {"_biz_op_code": "FDL", "FILE_GRP_ID": "34D0mcpfsYRy3uc50Abpp8K7XF+/qrto",
                          "FILE_PATH": "", "FILE_NAME": "", "USER_FILE_NM": ""}
    with pytest.raises(ValueError, match="PDF가 아닌 응답.*죄송합니다"):     # 상태 200인데 안내 화면이 온 경우
        dongyang.download(FakeSession([(200, NOT_FOUND, {"Content-Type": "text/html; charset=UTF-8"})]), doc)
    with pytest.raises(RuntimeError, match="404"):                          # 없는 서류 값: 상태 404
        dongyang.download(FakeSession([(404, NOT_FOUND, {})]), doc)
    assert dongyang.attachment_name(DISPOSITION) == "사업방법서_무배당우리WON하는보장보험_20260701.pdf"
    assert dongyang.attachment_name(None) == ""
