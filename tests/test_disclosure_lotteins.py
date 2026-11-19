import pytest

try:
    from postlife.disclosure import lotteins
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import lotteins

# 2026-11-19에 공시실(POST /CChannelSvl)에서 받은 응답의 형태. 행은 실제 응답에서 골라 옮겼고 앞뒤 화면 스크립트는 줄였다.
# 응답은 EUC-KR HTML이고, 부모 화면의 칸을 비우는 줄이 먼저, 내용을 넣는 줄이 뒤에 온다.
STEP4_BLANK = ("<dl class='pro_select'><dt>상품명</dt><dd><span><br></span></dd><dt class='pt20'>판매기간</dt>"
               "<dd><span><br></span></dd></dl><ul class='pdf_btn'><li><img src='/web/C/images/com/btn/btn_cdh_pdf01.gif' "
               "alt='사업방법서'></li></ul>")
# 2단계 상품 목록 (장기보험 > 상해,질병). 판매상품 탭과 판매중지 탭('0001'처럼 0을 채운 순번)
STEP2 = (
    '<script>\n\tparent.document.getElementById("step2view").style.display="";\n'
    '\tparent.document.getElementById("step2view").innerHTML="";\n'
    f'\tparent.document.getElementById("step4view").innerHTML="{STEP4_BLANK}";\n</script>\n<script>\n'
    "\tparent.document.getElementById(\"step2view\").innerHTML = \"<ul class='product_list'>"
    "<li id='adde18'><a onclick=step3('03','01','1104');classchkStep2(18,41);> "
    "<span>(무) let:simple 3N5 간편맞춤 건강보험(세만기형)(2604)</span></a></li>"
    "<li id='adde21'><a onclick=step3('03','01','1110');classchkStep2(21,41);> "
    "<span>(무) let:smile 종합건강보험(더끌림 포맨)(2604)</span></a></li></ul>\";\n</script>\n<!--시작-->\n"
)
STEP2_CLOSED = (
    "<script>\n\tparent.document.getElementById(\"step2view\").innerHTML = \"<ul class='product_list'>"
    "<li id='adde0'><a onclick=step3('03','01','0001');classchkStep2(0,1082);> <span>(무) 롯데 실손의료보험(1501)</span></a></li>"
    "</ul>\";\n</script>"
)
# 3단계 판매기간. 최근 기간부터 오고, 열린 기간은 '현재'로 적힌다. </a>와 </span> 순서가 뒤바뀐 채로 온다
STEP3 = (
    '<script>\n\tparent.document.getElementById("step3view").style.display="";\n'
    '\tparent.document.getElementById("step3view").innerHTML="";\n</script>\n</body>\n<script>\n'
    "\tparent.document.getElementById(\"step3view\").innerHTML = \"<ul class='product_list'>"
    "<li id='addf0'><a onclick=step4('03','01','1110','20260801');classchkStep3(0,3);><span>2026.08.01 ~ 현재</a></span></li>"
    "<li id='addf1'><a onclick=step4('03','01','1110','20260701');classchkStep3(1,3);><span>2026.07.01 ~ 2026.07.31</a></span></li>"
    "<li id='addf2'><a onclick=step4('03','01','1110','20260401');classchkStep3(2,3);><span>2026.04.01 ~ 2026.06.30</a></span></li>"
    "</ul>\";\n</script>"
)
# 4단계 서류 목록. 링크는 따옴표 없이 온다
STEP4 = (
    "<script>\n\tparent.document.getElementById(\"step4view\").innerHTML = \"<dl class='pro_select'><dt>상품명</dt>"
    "<dd><span>(무) let:smile 종합건강보험(더끌림 포맨)(2604)</span></dd><dt class='pt20'>판매기간</dt>"
    "<dd><span>2026.08.01 ~ 현재</span></dd></dl><ul class='pdf_btn'>"
    "<li><a href=/upload/C/newProduct/forman_sb_08.pdf  title='새창열림_사업방법서 PDF보기' target='_blank'>"
    "<img src='/web/C/images/com/btn/btn_cdh_pdf01_on.gif' alt='사업방법서'></a></li>"
    "<li><a href=/upload/C/newProduct/forman_yoyak_08.pdf  title='새창열림_상품요약서 PDF보기' target='_blank'>"
    "<img src='/web/C/images/com/btn/btn_cdh_pdf02_on.gif' alt='상품요약서'></a></li>"
    "<li><a href=/upload/C/newProduct/forman_yak_08.pdf  title='새창열림_약관 PDF보기' target='_blank'>"
    "<img src='/web/C/images/com/btn/btn_cdh_pdf03_on.gif' alt='약관'></a></li></ul>\";\n</script>"
)


def _row(group, name, period, yak, sb, yoy):
    def cell(path, kind, n):
        img = f"<img src='/web/C/images/com/btn/btn_cdh_list0{n}.gif' alt='{kind}'>"
        return f"<a href={path}  title='새창열림_{kind} PDF보기' target='_blank'>{img}</a>" if path else img
    return (f"<tr><td class='alignC'>{group}</td><td class='alignC'>{name}</td><td class='alignC'>{period}</td>"
            f"<td class='alignC'>{cell(yak, '약관', 1)}</td><td class='alignC'>{cell(sb, '사업방법서', 2)}</td>"
            f"<td class='lst alignC'>{cell(yoy, '상품요약서', 3)}</td></tr>")


def _table(title, count, rows):
    return (f"<p class='tit_pd_info_h4'><span class='t_s12'>{title}</span><span class='t_bnone'>(총 {count}건)</span></p>"
            "\t\t\t\t\t<table class='tb_default'><thead><tr><th scope='col'>상품군</th><th scope='col'>상품명</th>"
            "<th scope='col'>판매기간</th><th scope='col'>보험약관</th><th scope='col'>사업방법서</th>"
            "<th scope='col' class='lst'>상품요약서</th></tr></thead><tbody>" + "".join(rows) + "\t\t</tbody></table>")


def _search(selling_table, closed_table):
    return ('<!--검색시작-->\n<script>\n\tparent.document.getElementById("searchviewissale").innerHTML="";\n'
            '\tparent.document.getElementById("searchviewisnotsale").innerHTML="";\n</script>\n</body>\n<script>\n'
            f'\tparent.document.getElementById("searchviewissale").innerHTML = "{selling_table}";\n'
            f'\tparent.document.getElementById("searchviewisnotsale").innerHTML = "{closed_table}";\n</script>')


# 상품명 검색. 판매상품 표에도 지난 판매기간이 오고, 판매종료상품 표에도 '현재'로 열린 기간이 있다. 요약서가 없는 옛 행도 있다
SELLING_ROWS = [
    _row("장기", "(무) let:simple 3N5 간편맞춤 건강보험(세만기형)(2604)", "2026.09.01 ~ <br>2026.10.30",
         "/upload/C/newProduct/3N5_A_YAK.pdf", "/upload/C/newProduct/3N5_A_SB.pdf", "/upload/C/newProduct/3N5_A_YOYAK.pdf"),
    _row("장기", "(무) let:simple 3N5 간편맞춤 건강보험(세만기형)(2604)", "2026.10.31 ~ <br>현재",
         "/upload/C/newProduct/3n5_a_yak.pdf", "/upload/C/newProduct/3n5_a_sb.pdf", "/upload/C/newProduct/3n5_a_yoyak.pdf"),
]
CLOSED_ROWS = [
    _row("장기", "(무) let:care 생활상해종합보험(주택플러스)(2601)", "2026.01.01 ~ <br>현재",
         "/upload/C/newProduct/care_livingsanghae(2601)_yak_v3.pdf", "/upload/C/newProduct/care_livingsanghae(2601)_sb.pdf",
         "/upload/C/newProduct/care_livingsanghae(2601)_yoyak.pdf"),
    _row("장기", "(무) 동의보감 건강보험(남성형)", "2000.10.02 ~ <br>2001.03.31",
         "/upload/C/FCKFilesFile/sangpum/clause_disease_02.pdf", "/upload/C/FCKFilesFile/sangpum/clause_disease_02_sb.pdf", ""),
]
SEARCH = _search(_table("판매상품", 2, SELLING_ROWS), _table("판매종료상품", 2, CLOSED_ROWS))
NONE_ROW = "<tr><td class='alignC lst' colspan='6'>검색된 판매상품이 없습니다.</td></tr>"
SEARCH_NONE = _search(_table("판매상품", 0, [NONE_ROW]), _table("판매종료상품", 0, [NONE_ROW]))
# 공시 응답이 아닌 화면(상태 코드와 무관하게 칸을 채우는 줄이 없다). 실제로 받아 본 오류 응답은 없다
NOT_DISCLOSURE = "<!doctype html><html><head><title>롯데손해보험 페이지안내</title></head><body></body></html>"
# 없는 서류 경로: 상태 404, text/html 안내 화면 (실제 응답의 머리)
NOT_FOUND = '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="euc-kr">\n<title>롯데손해보험 페이지안내</title>'


def test_products_keep_site_sequence_as_text():
    products = lotteins.parse_products(STEP2, "03", "01", "상해,질병")
    assert [(p.scode, p.name) for p in products] == [
        ("1104", "(무) let:simple 3N5 간편맞춤 건강보험(세만기형)(2604)"), ("1110", "(무) let:smile 종합건강보험(더끌림 포맨)(2604)")]
    assert products[0].selling and products[0].kind == "상해,질병"
    closed = lotteins.parse_products(STEP2_CLOSED, selling=False)
    assert closed[0].scode == "0001" and not closed[0].selling


def test_periods_and_pick():
    periods = lotteins.parse_periods("포맨", STEP3)
    assert [(p.start, p.end, p.scode) for p in periods] == [
        ("2026-04-01", "2026-06-30", "1110"), ("2026-07-01", "2026-07-31", "1110"), ("2026-08-01", None, "1110")]
    assert lotteins.pick_period(periods).start == "2026-08-01" and periods[-1].is_open
    assert lotteins.pick_period(periods, "2026-07-15").start == "2026-07-01"
    assert lotteins.pick_period(periods, "2026-03-31") is None


def test_documents_from_step4():
    docs = lotteins.parse_documents(STEP4, "1110")
    assert [d.kind for d in docs] == ["사업방법서", "상품요약서", "약관"]
    assert docs[1].path == "/upload/C/newProduct/forman_yoyak_08.pdf" and docs[1].file_name == "forman_yoyak_08.pdf"
    assert (docs[0].start, docs[0].end, docs[0].scode) == ("2026-08-01", None, "1110")
    assert docs[0].name == "(무) let:smile 종합건강보험(더끌림 포맨)(2604)"
    # 2·3단계 응답이 넣는 빈 칸(아무것도 고르지 않은 상태)
    assert lotteins.parse_documents(f'<script>parent.document.getElementById("step4view").innerHTML="{STEP4_BLANK}";</script>') == []


def test_search_rows_both_tables():
    rows = lotteins.parse_search(SEARCH)
    assert [(r.start, r.end, r.selling, r.group) for r in rows] == [
        ("2026-09-01", "2026-10-30", True, "장기"), ("2026-10-31", None, True, "장기"),
        ("2026-01-01", None, False, "장기"), ("2000-10-02", "2001-03-31", False, "장기")]
    assert rows[1].files == {"약관": "/upload/C/newProduct/3n5_a_yak.pdf", "사업방법서": "/upload/C/newProduct/3n5_a_sb.pdf",
                             "상품요약서": "/upload/C/newProduct/3n5_a_yoyak.pdf"}
    assert rows[2].is_open and not rows[2].selling          # 판매종료상품 표에 있지만 열린 기간
    assert [d.kind for d in rows[3].documents] == ["사업방법서", "약관"]   # 요약서 칸은 그림만 있다
    assert rows[1].documents[1].path.endswith("3n5_a_yoyak.pdf") and rows[1].scode == ""
    assert lotteins.parse_search(SEARCH_NONE) == []


def test_not_disclosure_and_bad_shapes_are_raised():
    with pytest.raises(ValueError, match="step2view"):
        lotteins.parse_products(NOT_DISCLOSURE)
    with pytest.raises(ValueError, match="searchviewissale"):
        lotteins.parse_search(NOT_DISCLOSURE)
    with pytest.raises(ValueError, match="건수"):   # 표 위 건수와 읽은 행 수가 다르면 꼴이 바뀐 것
        lotteins.parse_search(_search(_table("판매상품", 3, SELLING_ROWS), _table("판매종료상품", 2, CLOSED_ROWS)))
    with pytest.raises(ValueError, match="다름"):   # 판매기간 표시와 요청 값이 어긋남
        lotteins.parse_periods("x", STEP3.replace("'20260701'", "'20260702'"))


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        status, body, ctype = self.replies.pop(0)

        class R:
            status_code = status
            content = body if isinstance(body, bytes) else body.encode("cp949")
            headers = {"Content-Type": ctype}

            def raise_for_status(self):
                if status >= 400:
                    raise RuntimeError(status)

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


HTML = "text/html;charset=euc-kr"


def test_list_products_sends_the_page_form():
    s = FakeSession([(200, STEP2_CLOSED, HTML)])
    products = lotteins.list_products(s, selling=False, categories=lotteins.HEALTH)
    assert products[0].scode == "0001" and products[0].kind == "상해,질병"
    method, url, kw = s.sent[0]
    assert (method, url) == ("POST", "https://www.lotteins.co.kr/CChannelSvl")
    # 실제로 보내 확인한 본문과 같은 꼴 (필드 순서도 화면 폼과 같다)
    assert kw["data"] == (b"ops_tc=dfi.c.d.g.cmd.Cdg079Cmd&task=gostep2isnotsale&rtnUri=/web/C/D/H/cdh190_result.jsp"
                          b"&lcode=03&mcode=01&scode=&startdate=&issale=N&srcPrdNm=")
    assert kw["headers"]["Content-Type"] == "application/x-www-form-urlencoded"


def test_list_documents_asks_latest_period_then_documents():
    s = FakeSession([(200, STEP3, HTML), (200, STEP4, HTML)])
    product = lotteins.Product("1110", "(무) let:smile 종합건강보험(더끌림 포맨)(2604)")
    docs = lotteins.list_documents(s, product)
    assert [d.kind for d in docs] == ["사업방법서", "상품요약서", "약관"]
    (_, _, kw1), (_, _, kw2) = s.sent
    assert b"task=gostep3issale" in kw1["data"] and b"scode=1110&startdate=&issale=Y" in kw1["data"]
    assert b"task=gostep4issale" in kw2["data"] and b"scode=1110&startdate=20260801&issale=Y" in kw2["data"]


def test_search_keyword_is_sent_in_euc_kr():
    s = FakeSession([(200, SEARCH, HTML)])
    assert len(lotteins.search_products(s, "건강")) == 4
    assert s.sent[0][2]["data"].endswith(b"task=searchKey&rtnUri=/web/C/D/H/cdh190_result.jsp"
                                         b"&lcode=&mcode=&scode=&startdate=&issale=Y&srcPrdNm=%B0%C7%B0%AD")


def test_download_url_and_non_pdf():
    doc = lotteins.Document("포우먼", "약관", "/upload/C/newProduct/FORWOMAN_YAK(1,2).pdf", "2026-07-01", "2026-07-31")
    s = FakeSession([(200, b"%PDF-1.4 ...", "application/pdf")])
    assert lotteins.download(s, doc).startswith(b"%PDF-")
    # 괄호와 쉼표는 그대로 둔다 (화면 링크 그대로)
    assert s.sent[0][:2] == ("GET", "https://www.lotteins.co.kr/upload/C/newProduct/FORWOMAN_YAK(1,2).pdf")
    with pytest.raises(ValueError, match="상태 404"):   # 없는 파일: 404와 HTML 안내 화면
        lotteins.download(FakeSession([(404, NOT_FOUND, "text/html")]), "/upload/C/newProduct/no_such.pdf")
