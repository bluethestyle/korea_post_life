import pytest

try:
    from postlife.disclosure import heungkukfire as hk
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import heungkukfire as hk

# 2026-11-19에 공시실에서 받은 목록 화면의 꼴 (메뉴와 스크립트는 빼고, 목록 폼과 행만 줄여 옮김)
MENU = '<div id="gnb"><table><tbody><tr><td>메뉴</td></tr></tbody></table></div>'


def page(mode, rows, paging):
    return (MENU + '<form id="frm" action="/FRW/announce/insGoodsGongsiSale.do" method="post">'
            '<input type="hidden" name="page" id="page" />'
            f'<input type="hidden" name="mode" id="mode" value="{mode}" />'
            '<input type="hidden" name="type" id="type" value="1" />'
            '<table><caption>보험상품공시 테이블입니다.</caption><thead><tr><th scope="col">구분</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<div class="paginate clfix mb40"><div class="btn_wrap">{paging}</div></div></form>'
            '<form method="post" id="downForm" action="#"><input type="hidden" name="mode" value="View" /></form>')


def button(real, save, label):
    return (f'<span class="btn_white7"><a href="#"  title="{real}" onclick="fn_filedownX(\'/Upload/gongsi/goods/\',\'{real}\', '
            f'\'{save}\'); return false;">{label}</a></span>\n')


def row(category, year, name, sold, buttons):
    return (f'\n<tr>\n<td><span>{category}</span></td>\n<td><span>{year}</span></td>\n'
            f'<td class="t_left"><span>{name}</span></td>\n<td class=""><span class="fz14">{sold} </span></td>\n'
            f'<td>\n{"".join(buttons)}\n</td>\n</tr>\n')


NAME = "무배당 흥Good 든든한 3N5 간편종합보험(26.11)(1종)"
# 판매 탭 1쪽(7쪽 가운데). 요약서와 사업방법서 별지는 원래 이름이 상품명과 띄어쓰기, 종 표기가 다르다
SELLING = page("go", row("의료/건강", "2026", NAME, "2026-11-01", [
    button("무배당 흥Good 든든한 3N5 간편종합보험(26.11) 1종_약관.pdf", "1794469286953712.pdf", "상품약관"),
    button("무배당 흥Good 든든한 3N5 간편종합보험(26.11)(1~2종)_사업방법서 별지.pdf", "1794469287104249.pdf", "사업방법서"),
    button("무배당 흥Good 든든한 3N5 간편종합보험(26.11)_상품요약서.pdf", "179446928712454.pdf", "상품요약서"),
]) + row("연금/저축", "2026", "무배당 흥Good 스페셜저축보험(26.08)", "2026-08-01", [   # 요약서 단추가 없는 행
    button("무배당 흥Good 스페셜저축보험(26.08)_약관.pdf", "1785818662490652.pdf", "상품약관"),
    button("무배당 흥Good 스페셜저축보험(26.08)_사업방법서 별지.pdf", "1785818662553818.pdf", "사업방법서"),
]), '<a class="go_first"></a><a href="#" class="on"><span>1</span></a>'
    '<a href="javascript:goPage(2);"><span>2</span></a><a href="javascript:goPage(3);"><span>3</span></a>'
    '<a href="javascript:goPage(2);" class="go_next"></a><a href="javascript:goPage(7);" class="go_end"></a>')
# 판매중지 탭 마지막 쪽: 판매일이 기간으로 오고, '마지막으로' 링크가 없다. 약관 원래 이름에 "HKF0003_" 같은 앞붙이가 붙기도 한다.
# 둘째 행은 실제 응답에서 옮긴 것이 아니다. 같은 이름이 판매기간마다 여러 행일 때를 보려고 만들었다
STOPPED_ROWS = row("의료/건강", "2026", "무배당 흥Good The건강한 4565 종합보험(26.10)(2종)", "2026-10-01 ~ 2026-10-31", [
    button("HKF0003_약관_무배당 흥Good The건강한 4565 종합보험(26.10)(2종).pdf", "1793328935535175.pdf", "상품약관"),
    button("무배당 흥Good The건강한 4565 종합보험(26.10)_상품요약서.pdf", "179194214132975.pdf", "상품요약서"),
]) + row("의료/건강", "2026", "무배당 흥Good The건강한 4565 종합보험(26.10)(2종)", "2026-05-04 ~ 2026-06-30", [])
STOPPED = page("stop", STOPPED_ROWS, '<a href="javascript:goPage(1);"><span>1</span></a>'
               '<a href="javascript:goPage(3);"><span>3</span></a><a href="#" class="on"><span>4</span></a>')
# 상품명 전체로 검색했을 때: 한 행, 쪽 링크는 현재 쪽뿐
FOUND = page("go", row("의료/건강", "2026", NAME, "2026-11-01", [
    button("무배당 흥Good 든든한 3N5 간편종합보험(26.11)_상품요약서.pdf", "179446928712454.pdf", "상품요약서")]),
    '<a href="#" class="on"><span>1</span></a>')
# 상품 소개 화면 등 목록이 아닌 응답
NOT_LIST = "<!DOCTYPE html><html><body>" + MENU + "</body></html>"
# 없는 파일을 요청했을 때의 응답(상태 200, text/html 194바이트)
MISSING = ("<SCRIPT LANGUAGE='JavaScript'>\n<!-- \n\n    alert('파일을 다운로드하는데 실패했습니다. \\n파일이 지정한 경로에 없습니다.');"
           "\n    history.back();\n//-->\n</SCRIPT>").encode("utf-8")


def test_selling_page_rows_documents_and_last_page():
    products, last = hk.parse_list(SELLING)
    assert last == 7 and len(products) == 2
    p = products[0]
    assert (p.name, p.category, p.year, p.start, p.end, p.selling) == (NAME, "의료/건강", "2026", "2026-11-01", None, True)
    assert [d.kind for d in p.documents] == ["약관", "사업방법서", "상품요약서"]
    summary = p.files["상품요약서"]
    assert (summary.file_name, summary.save_name, summary.path) == (
        "무배당 흥Good 든든한 3N5 간편종합보험(26.11)_상품요약서.pdf", "179446928712454.pdf", "/Upload/gongsi/goods/")
    assert p.files["사업방법서"].file_name.endswith("_사업방법서 별지.pdf")
    assert set(products[1].files) == {"약관", "사업방법서"}


def test_stopped_page_periods_and_last_page():
    products, last = hk.parse_list(STOPPED)
    assert last == 4
    assert [(p.start, p.end, p.selling) for p in products] == [
        ("2026-10-01", "2026-10-31", False), ("2026-05-04", "2026-06-30", False)]
    assert products[1].documents == ()
    assert hk.parse_list(FOUND)[1] == 1


def test_not_a_list_page_is_raised():
    with pytest.raises(ValueError, match="목록 화면이 아님"):
        hk.parse_list(NOT_LIST)


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def post(self, url, **kw):
        self.sent.append((url, kw))
        reply = self.replies.pop(0)

        class R:
            content = reply if isinstance(reply, bytes) else reply.encode("utf-8")
            text = reply if isinstance(reply, str) else ""
            headers = {"Content-Type": "application/octet-stream;charset=UTF-8" if content.startswith(b"%PDF")
                       else "text/html; charset=UTF-8"}
            encoding = None

            def raise_for_status(self):
                pass

        return R()


def test_list_products_walks_pages_with_the_page_form():
    first = SELLING.replace("goPage(7)", "goPage(2)").replace("goPage(3)", "goPage(2)")
    last = page("go", row("의료/건강", "2011", "실손의료비 보장 무사고할인 특별약관", "2011-10-01", []),
                '<a href="javascript:goPage(1);"><span>1</span></a><a href="#" class="on"><span>2</span></a>')
    s = FakeSession([first, last])
    products = hk.list_products(s)
    assert len(products) == 3 and len(s.sent) == 2 and all(p.selling for p in products)
    (url1, kw1), (url2, kw2) = s.sent
    assert url1 == "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do"
    assert kw1["data"] == {"page": "1", "mode": "go", "type": "1", "searchvalue": ""}
    assert kw2["data"]["page"] == "2"


def test_list_documents_searches_full_name_and_keeps_exact_match():
    s = FakeSession([FOUND])
    docs = hk.list_documents(s, NAME)
    assert [d.save_name for d in docs] == ["179446928712454.pdf"]
    assert s.sent[0][1]["data"] == {"page": "1", "mode": "go", "type": "1", "searchvalue": NAME}
    s = FakeSession([page("stop", STOPPED_ROWS, '<a href="#" class="on"><span>1</span></a>')])
    # 같은 이름이 판매기간마다 여러 행이면 개시일이 가장 늦은 행
    docs = hk.list_documents(s, "무배당 흥Good The건강한 4565 종합보험(26.10)(2종)", selling=False)
    assert [d.kind for d in docs] == ["약관", "상품요약서"] and docs[0].start == "2026-10-01"
    assert s.sent[0][1]["data"]["mode"] == "stop"
    assert hk.list_documents(FakeSession([FOUND]), "다른 상품") == []


def test_download_form_and_non_pdf():
    doc = hk.parse_list(SELLING)[0][0].files["상품요약서"]
    s = FakeSession([b"%PDF-1.6 ..."])
    assert hk.download(s, doc).startswith(b"%PDF-")
    url, kw = s.sent[0]
    # 실제로 받은 요청과 같은 꼴: 원래 이름과 저장 이름을 폼으로 보낸다 (fileEncYn은 없어도 됐다)
    assert url == "https://www.heungkukfire.co.kr/common/download.do" and kw["params"]["temp"].isdigit()
    assert kw["data"] == {"filePath": "/Upload/gongsi/goods/", "fileSaveName": "179446928712454.pdf", "mode": "View",
                          "fileRealName": "무배당 흥Good 든든한 3N5 간편종합보험(26.11)_상품요약서.pdf"}
    with pytest.raises(ValueError, match="파일이 지정한 경로에 없습니다"):
        hk.download(FakeSession([MISSING]), doc)
