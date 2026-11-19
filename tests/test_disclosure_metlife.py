import pytest

try:
    from postlife.disclosure import metlife
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import metlife

# 2026-11-19에 공시실에서 받은 화면 HTML의 형태 (표 부분만, 행은 실제 응답에서 골라 줄여 옮김)
HEAD = """<table class="tblList contentTable"><caption>…</caption><thead>
<tr><th scope="col" rowspan=2>구분</th><th scope="col" rowspan=2>주보험상품명</th><th scope="col" rowspan=2>판매기간</th>
<th scope="col" rowspan=2>사업방법서</th>{summary}<th scope="col" rowspan=2>약관</th>
<th scope="col" colspan=2>상품설명서</th><th scope="col" rowspan=2>특약</th></tr>
<tr><th scope="col" >남</th><th scope="col" >여</th></tr></thead><tbody>"""
DOWN = '<td><a href="/pn/mcvrgProd/mcvrgProdDownloadFile.do?insProdSeq={p}&seq={s}&fnum={f}" class="btnDown" title=\'x\'>\n {name}\n</a></td>'
NONE = "<td>\n -\n</td>"
RIDERS = """<td><a href="javascript:;" class='btnTxt' onclick="popUpOpen('/pn/mcvrgProd/retrieveMcvrgProdPop.do', {p} , {s} )">특약보기</a></td>"""
# 판매상품 목록(검색 결과도 같은 꼴). 첫 판매기간 행은 판매기간 칸부터, 지난 행은 구분과 상품명 칸을 앞에 한 번 더 둔다
SELLING = HEAD.format(summary='<th scope="col" rowspan=2>상품요약서</th>') + f"""
<tr><th id="row_0_0" class="bgW" rowspan="2">\n 보장\n </th><td rowspan="2">\n 무배당 360 종합보장보험(무해약환급금형)\n </td>
<td colspan="7"><button class="button toggler" data-row="row_0_0">이전 판매기간 펼치기</button></td></tr>
<tr ><td>\n 2026.07.01 ~ \n</td>
{DOWN.format(p=733, s=4172, f="01", name="27_01_사업방법서_무배당360종합보장보험(무해약환급금형)_202601_v1.pdf")}
{DOWN.format(p=733, s=4172, f="02", name="상품요약서_무배당360종합보장보험(무해약환급금형)_20260701.pdf")}
{DOWN.format(p=733, s=4172, f="03", name="무배당 360종합보장보험(무해약환급금형)_12286_12288_12287_12289_20260701.pdf")}
{NONE}{NONE}{RIDERS.format(p=733, s=4172)}</tr>
<tr class="row_0_0" style="display:none;"><th class="bgW row_0_0_gubn">\n 보장\n </th><td>\n 무배당 360 종합보장보험(무해약환급금형)\n </td>
<td>\n 2026.05.04 ~ 2026.06.30\n</td>
{DOWN.format(p=733, s=4028, f="01", name="27_01_사업방법서_무배당360종합보장보험(무해약환급금형)_202601_v1.pdf")}
{NONE}
{DOWN.format(p=733, s=4028, f="03", name="무배당 360종합보장보험(무해약환급금형)_12141_12143_12142_12144_20260101.pdf")}
{NONE}{NONE}{RIDERS.format(p=733, s=4028)}</tr>
<tr><th id="row_0_1" class="bgW" rowspan="2">\n 보장\n </th><td rowspan="2">\n 무배당 간편가입 360 종합보장보험(갱신형)\n </td>
<td colspan="7"><button class="button toggler" data-row="row_0_1">이전 판매기간 펼치기</button></td></tr>
<tr ><td>\n 2026.07.01 ~ \n</td>
{DOWN.format(p=857, s=4177, f="01", name="29_01_사업방법서_무배당 간편가입 360 종합보장보험(갱신형)_202602.pdf")}
{DOWN.format(p=857, s=4177, f="02", name="상품요약서_무배당간편가입360종합보장보험(갱신형)_20260701.pdf")}
{DOWN.format(p=857, s=4177, f="03", name="무배당 간편가입360종합보장보험(갱신형)_12064_20260701.pdf")}
{NONE}{NONE}{RIDERS.format(p=857, s=4177)}</tr>
</tbody></table>"""
# 판매중지 목록: 상품요약서 칸이 없고, 팝업 주소가 다르다
STOPPED = HEAD.format(summary="") + f"""
<tr><th id="row_0_0" class="bgW" rowspan="2">\n 보장\n </th><td rowspan="2">\n 무배당 하이라이프종신보험\n </td>
<td colspan="6"><button class="button toggler" data-row="row_0_0">이전 판매기간 펼치기</button></td></tr>
<tr ><td>\n 2019.04.01 ~ 2020.04.09\n</td>
{DOWN.format(p=1, s=388, f="01", name="사업방법서_무배당하이라이프종신보험_20190401.pdf")}
{DOWN.format(p=1, s=388, f="03", name="무배당 하이라이프종신보험 약관.pdf")}
{NONE}{NONE}<td><a href="javascript:;" class='btnTxt' onclick="popUpOpen('/pn/saleStop/retrieveSaleStopPop.do', 1 , 388 )">특약보기</a></td></tr>
</tbody></table>"""
# 검색 결과가 없을 때: 표 없이 안내 상자만 온다
NO_RESULT = """<div class="topSchWrap"><input id="searchKeyword" name="searchKeyword" type="text" value="없는상품이름"/></div>
<!-- s : 검색 결과가 없을 경우 --><div class="schMsgBox"><p class="txt">검색 결과가 없습니다.</p></div>"""
# 없는 서류를 달라고 했을 때: 상태 200, text/html 255바이트
ERROR_PAGE = """<!DOCTYPE html><html><head><title>Error</title></head><body>    에러가 발생했습니다!</body></html>"""


def test_selling_list_rows():
    products = metlife.parse_list(SELLING)
    assert [(p.ins_prod_seq, p.name, p.category, p.selling) for p in products] == [
        ("733", "무배당 360 종합보장보험(무해약환급금형)", "보장", True),
        ("857", "무배당 간편가입 360 종합보장보험(갱신형)", "보장", True)]
    general = products[0]
    assert [(q.seq, q.start, q.end) for q in general.periods] == [("4172", "2026-07-01", None), ("4028", "2026-05-04", "2026-06-30")]
    assert general.current.seq == "4172"
    docs = general.current.documents
    assert [(d.kind, d.fnum) for d in docs] == [("사업방법서", "01"), ("상품요약서", "02"), ("약관", "03")]
    assert docs[1].file_name == "상품요약서_무배당360종합보장보험(무해약환급금형)_20260701.pdf"
    assert set(general.periods[1].files) == {"사업방법서", "약관"}   # 지난 판매기간에는 요약서가 없다
    assert general.current.codes == ("12286", "12288", "12287", "12289") and products[1].current.codes == ("12064",)


def test_stopped_list_maps_columns_by_header():
    (p,) = metlife.parse_list(STOPPED, selling=False)
    assert (p.ins_prod_seq, p.selling, p.current) == ("1", False, None)
    assert p.periods[0].files == {"사업방법서": "사업방법서_무배당하이라이프종신보험_20190401.pdf",
                                  "약관": "무배당 하이라이프종신보험 약관.pdf"}   # 세 번째 서류 칸이 요약서가 아니라 약관이다


def test_pick_and_find():
    products = metlife.parse_list(SELLING)
    periods = metlife.find_product(products, "무배당  360 종합보장보험(무해약환급금형)").periods
    assert metlife.pick_period(periods).seq == "4172"
    assert metlife.pick_period(periods, "2026-06-01").seq == "4028"
    assert metlife.pick_period(periods, "2026-05-01") is None
    assert metlife.find_product(products, "무배당 360 종합보장보험") is None   # 부분 일치는 고르지 않는다


def test_no_result_and_bad_page():
    assert metlife.parse_list(NO_RESULT) == []
    with pytest.raises(ValueError, match="tblList"):
        metlife.parse_list(ERROR_PAGE)
    with pytest.raises(ValueError, match="머리행"):
        metlife.parse_list('<table class="tblList"><thead><tr><th>특약상품명</th></tr></thead><tbody></tbody></table>')


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def _reply(self, method, url, kw):
        self.sent.append((method, url, kw))
        reply = self.replies.pop(0)
        body = reply if isinstance(reply, bytes) else reply.encode("utf-8")

        class R:
            content = body
            text = body.decode("utf-8", errors="replace")
            headers = {} if isinstance(reply, bytes) else {"Content-Type": "text/html; charset=utf-8"}
            encoding = None

            def raise_for_status(self):
                pass

        return R()

    def post(self, url, **kw):
        return self._reply("POST", url, kw)

    def get(self, url, **kw):
        return self._reply("GET", url, kw)


def test_list_requests_send_what_the_page_sends():
    s = FakeSession([SELLING, SELLING, STOPPED])
    assert len(metlife.list_products(s)) == 2
    metlife.list_products(s, "360 종합보장")
    metlife.list_products(s, "하이라이프", selling=False)
    (m1, u1, k1), (m2, u2, k2), (m3, u3, k3) = s.sent
    assert (m1, u1) == ("GET", "https://brand.metlife.co.kr/pn/mcvrgProd/retrieveMcvrgProdMain.do") and "data" not in k1
    assert (m2, u2) == ("POST", u1)
    assert k2["data"] == {"searchKeyword": "360 종합보장", "insProdSeq": "", "fnum": "", "seq": ""}
    assert (m3, u3) == ("POST", "https://brand.metlife.co.kr/pn/saleStop/retrieveSaleStopProdMain.do")
    assert k3["data"]["searchCondition"] == "0" and k3["data"]["searchKeyword"] == "하이라이프"


def test_list_documents_searches_by_name():
    s = FakeSession([SELLING, NO_RESULT])
    docs = metlife.list_documents(s, "무배당 간편가입 360 종합보장보험(갱신형)")
    assert [(d.ins_prod_seq, d.seq, d.kind) for d in docs] == [("857", "4177", "사업방법서"), ("857", "4177", "상품요약서"),
                                                                ("857", "4177", "약관")]
    assert s.sent[0][2]["data"]["searchKeyword"] == "무배당 간편가입 360 종합보장보험(갱신형)"
    assert metlife.list_documents(s, "없는상품이름") == []


def test_download_url_and_non_pdf():
    doc = metlife.parse_list(SELLING)[0].current.documents[1]
    # 실제로 내려받기에 성공한 주소와 같은 꼴
    assert doc.url == "https://brand.metlife.co.kr/pn/mcvrgProd/mcvrgProdDownloadFile.do?insProdSeq=733&seq=4172&fnum=02"
    s = FakeSession([b"%PDF-1.4 ..."])
    assert metlife.download(s, doc).startswith(b"%PDF-")
    assert s.sent[0][:2] == ("GET", doc.url)
    with pytest.raises(ValueError, match="에러가 발생했습니다"):
        metlife.download(FakeSession([ERROR_PAGE]), doc)
