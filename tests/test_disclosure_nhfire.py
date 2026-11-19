import pytest

try:
    from postlife.disclosure import nhfire
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import nhfire

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮김)
# 상품구분 목록 (pdtSelYn=Y, pdtGrCd=01). 칸마다 같은 이름의 요소가 줄지어 오고, pdtGrCd만 하나 더 왔다
CATEGORIES = """<?xml version='1.0' encoding="UTF-8"?>
<xsync><LMultiData onAfterAction="fnSetPdtDcdList"><pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtDcd><![CDATA[01]]></pdtDcd>
<pdtDcd><![CDATA[05]]></pdtDcd>
<pdtDcdNm><![CDATA[화재/재물]]></pdtDcdNm>
<pdtDcdNm><![CDATA[건강/어린이]]></pdtDcdNm>
<pdtSelYn><![CDATA[Y]]></pdtSelYn>
<pdtSelYn><![CDATA[Y]]></pdtSelYn>
<sortSeqn><![CDATA[1]]></sortSeqn>
<sortSeqn><![CDATA[4]]></sortSeqn>
</LMultiData></xsync>""".encode("utf-8")

# 상품명 목록. 앞 세 행은 판매상품(pdtGrCd=01, pdtDcd 빈 값), 뒤 세 행은 판매중지(pdtDcd=05, basicDate=20120302, flag=A).
# 이름에 "(무) "가 든 행, ntgDivdYn=Y라 화면이 "(무)"를 붙이는 행, 개정 연월이 addPdtNm에 따로 오는 행,
# addPdtNm이 빈칸 하나인 행, 상품구분이 빈 행(제도성 특별약관)이 섞여 온다
PRODUCTS = """<?xml version='1.0' encoding="UTF-8"?>
<xsync><LMultiData onAfterAction="fnSetPdtCdList"><pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtGrCd><![CDATA[]]></pdtGrCd>
<pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtGrCd><![CDATA[01]]></pdtGrCd>
<pdtDcd><![CDATA[05]]></pdtDcd>
<pdtDcd><![CDATA[05]]></pdtDcd>
<pdtDcd><![CDATA[]]></pdtDcd>
<pdtDcd><![CDATA[05]]></pdtDcd>
<pdtDcd><![CDATA[05]]></pdtDcd>
<pdtDcd><![CDATA[05]]></pdtDcd>
<pdtCd><![CDATA[D311887]]></pdtCd>
<pdtCd><![CDATA[D313714]]></pdtCd>
<pdtCd><![CDATA[911111]]></pdtCd>
<pdtCd><![CDATA[D311881]]></pdtCd>
<pdtCd><![CDATA[D31181H]]></pdtCd>
<pdtCd><![CDATA[D312213]]></pdtCd>
<pdtNm><![CDATA[(무) NH가성비굿건강보험[1종:납입면제형/표준형/갱신형]2604]]></pdtNm>
<pdtNm><![CDATA[(무) NH하나로간편한건강보험[1종:세만기(355/해약환급금미지급Ⅱ/납면)]2601]]></pdtNm>
<pdtNm><![CDATA[다자녀가정 할인 제도성 특별약관]]></pdtNm>
<pdtNm><![CDATA[NH가성비굿건강보험[1종:납입면제형/표준형/갱신형]]]></pdtNm>
<pdtNm><![CDATA[(무) NH가성비굿건강보험[4종:해약환급금미지급형Ⅱ]2601]]></pdtNm>
<pdtNm><![CDATA[(무)NH가성비굿플러스어린이보험2004]]></pdtNm>
<addPdtNm><![CDATA[]]></addPdtNm>
<addPdtNm><![CDATA[]]></addPdtNm>
<addPdtNm><![CDATA[]]></addPdtNm>
<addPdtNm><![CDATA[2304]]></addPdtNm>
<addPdtNm><![CDATA[]]></addPdtNm>
<addPdtNm><![CDATA[ ]]></addPdtNm>
<ntgDivdYn><![CDATA[N]]></ntgDivdYn>
<ntgDivdYn><![CDATA[N]]></ntgDivdYn>
<ntgDivdYn><![CDATA[N]]></ntgDivdYn>
<ntgDivdYn><![CDATA[Y]]></ntgDivdYn>
<ntgDivdYn><![CDATA[Y]]></ntgDivdYn>
<ntgDivdYn><![CDATA[N]]></ntgDivdYn>
</LMultiData></xsync>""".encode("utf-8")

# 서류 목록 (fileType=05, pdtCd=D311887). 판매기간마다 fileId 하나. 순번은 파일 이름이 없어도 온다(상품안내장, 업무방법서)
PERIODS = """<?xml version='1.0' encoding="UTF-8"?>
<xsync><LMultiData onAfterAction="fnSetPdtInfoList"><pdtHstNo><![CDATA[20260630145150067624]]></pdtHstNo>
<pdtHstNo><![CDATA[20260401173001233785]]></pdtHstNo>
<pdtCd><![CDATA[D311887]]></pdtCd>
<pdtCd><![CDATA[D311887]]></pdtCd>
<pdtNm><![CDATA[(무) NH가성비굿건강보험[1종:납입면제형/표준형/갱신형]2604]]></pdtNm>
<pdtNm><![CDATA[(무) NH가성비굿건강보험[1종:납입면제형/표준형/갱신형]2604]]></pdtNm>
<addPdtNm><![CDATA[]]></addPdtNm>
<addPdtNm><![CDATA[]]></addPdtNm>
<ntgDivdYn><![CDATA[N]]></ntgDivdYn>
<ntgDivdYn><![CDATA[N]]></ntgDivdYn>
<pdtSelStDt><![CDATA[20260701]]></pdtSelStDt>
<pdtSelStDt><![CDATA[20260401]]></pdtSelStDt>
<pdtSelEdDt><![CDATA[99991231]]></pdtSelEdDt>
<pdtSelEdDt><![CDATA[20260630]]></pdtSelEdDt>
<fileId><![CDATA[F004242259]]></fileId>
<fileId><![CDATA[F003957358]]></fileId>
<plcndAfileSeqn><![CDATA[1]]></plcndAfileSeqn>
<plcndAfileSeqn><![CDATA[1]]></plcndAfileSeqn>
<smmrAfileSeqn><![CDATA[2]]></smmrAfileSeqn>
<smmrAfileSeqn><![CDATA[2]]></smmrAfileSeqn>
<ntcltAfileSeqn><![CDATA[3]]></ntcltAfileSeqn>
<ntcltAfileSeqn><![CDATA[3]]></ntcltAfileSeqn>
<bzMtdAfileSeqn><![CDATA[4]]></bzMtdAfileSeqn>
<bzMtdAfileSeqn><![CDATA[4]]></bzMtdAfileSeqn>
<fireMtdAfileSeqn><![CDATA[5]]></fireMtdAfileSeqn>
<fireMtdAfileSeqn><![CDATA[5]]></fireMtdAfileSeqn>
<plcndAfileNm><![CDATA[(무) NH가성비굿건강보험(1~2종).pdf]]></plcndAfileNm>
<plcndAfileNm><![CDATA[(무)NH가성비굿건강보험2604_약관(1-2종).pdf]]></plcndAfileNm>
<smmrAfileNm><![CDATA[(공시용) 무배당 NH가성비굿건강보험2604_상품요약서.pdf]]></smmrAfileNm>
<smmrAfileNm><![CDATA[(공시용) 무배당 NH가성비굿건강보험2604_상품요약서.pdf]]></smmrAfileNm>
<ntcltAfileNm><![CDATA[]]></ntcltAfileNm>
<ntcltAfileNm><![CDATA[]]></ntcltAfileNm>
<bzMtdAfileNm><![CDATA[무배당 NH가성비굿건강보험2604_사업방법서별지.pdf]]></bzMtdAfileNm>
<bzMtdAfileNm><![CDATA[(공시용) 무배당 NH가성비굿건강보험2604_사업방법서별지.pdf]]></bzMtdAfileNm>
<fireMtdAfileNm><![CDATA[]]></fireMtdAfileNm>
<fireMtdAfileNm><![CDATA[]]></fireMtdAfileNm>
<cfmtYn><![CDATA[Y]]></cfmtYn>
<cfmtYn><![CDATA[Y]]></cfmtYn>
</LMultiData></xsync>""".encode("utf-8")
# 화면 규칙(cfmtYn이 Y나 빈 값인 행만 보인다)을 시험하려고 만든 행. 실제 응답에서 N을 본 적은 없다
UNCONFIRMED = PERIODS.replace(b"<cfmtYn><![CDATA[Y]]></cfmtYn>\n</LMultiData>", b"<cfmtYn><![CDATA[N]]></cfmtYn>\n</LMultiData>")
EMPTY = b"<?xml version='1.0' encoding=\"UTF-8\"?>\n<xsync><LMultiData onAfterAction=\"fnSetPdtInfoList\"></LMultiData></xsync>"
# 화면 스크립트(xsync.js callback)가 처리하는 오류 꼴. 실제 응답으로 받아 본 적은 없다
ERROR = "<?xml version='1.0' encoding=\"UTF-8\"?>\n<xsync error=\"true\"><![CDATA[ERR-1 처리 중 오류]]></xsync>".encode()


def test_categories_follow_key_column():
    cats = nhfire.parse_categories(CATEGORIES, "01")
    assert [(c.group, c.code, c.name, c.selling) for c in cats] == [("01", "01", "화재/재물", True),
                                                                    ("01", "05", "건강/어린이", True)]


def test_product_names_as_the_page_shows():
    products = nhfire.parse_products(PRODUCTS)
    assert [p.code for p in products] == ["D311887", "D313714", "911111", "D311881", "D31181H", "D312213"]
    names = [p.name for p in products]
    assert names[0] == "(무) NH가성비굿건강보험[1종:납입면제형/표준형/갱신형]2604"
    assert names[3] == "(무)NH가성비굿건강보험[1종:납입면제형/표준형/갱신형]2304"   # "(무)" + pdtNm + addPdtNm
    assert names[4].startswith("(무)(무) ")    # 화면에도 두 번 붙는다
    assert names[5] == "(무)NH가성비굿플러스어린이보험2004"   # addPdtNm 빈칸 하나는 지운다
    assert products[2].category == "" and products[0].category == "05"
    assert [p.code for p in nhfire.find_products(products, "가성비굿 건강")] == ["D311887", "D311881", "D31181H"]


def test_periods_documents_and_pick():
    periods = nhfire.parse_periods(PERIODS)
    assert [(p.start, p.end, p.file_id) for p in periods] == [("2026-04-01", "2026-06-30", "F003957358"),
                                                             ("2026-07-01", None, "F004242259")]
    assert periods[1].code == "D311887" and periods[1].name.endswith("2604")
    latest = nhfire.pick_period(periods)
    assert latest.file_id == "F004242259"
    assert nhfire.pick_period(periods, "2026-05-15").file_id == "F003957358"
    assert nhfire.pick_period(periods, "2026-03-31") is None
    docs = nhfire.documents_of(latest)
    # 파일 이름이 빈 상품안내장, 업무방법서는 순번이 와도 빠진다
    assert [(d.kind, d.seq) for d in docs] == [("약관", "1"), ("상품요약서", "2"), ("사업방법서", "4")]
    assert docs[1].file_name == "(공시용) 무배당 NH가성비굿건강보험2604_상품요약서.pdf"
    assert [p.start for p in nhfire.parse_periods(UNCONFIRMED)] == ["2026-07-01"]
    assert nhfire.parse_periods(EMPTY) == []


def test_error_and_bad_shape_are_raised():
    with pytest.raises(ValueError, match="ERR-1"):
        nhfire.parse_products(ERROR)
    with pytest.raises(ValueError, match="XML이 아님"):
        nhfire.parse_periods(b"<html><body>error</body>")
    with pytest.raises(ValueError, match="LMultiData"):
        nhfire.parse_periods(b"<xsync></xsync>")


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
            content = body

            def raise_for_status(self):
                if status >= 400:
                    raise RuntimeError(status)

        R.headers = headers
        return R()


def test_requests_send_what_the_page_sends():
    s = FakeSession([PRODUCTS, PRODUCTS, PERIODS, CATEGORIES])
    nhfire.list_products(s)
    nhfire.list_products(s, category="05", selling=False)
    docs = nhfire.list_documents(s, "D311887")
    nhfire.list_categories(s, "01")
    (u1, k1), (u2, k2), (u3, k3), (u4, k4) = s.sent
    assert u1 == "https://www.nhfire.co.kr/front/announce/retrievePdtCd.ajax"
    assert k1["data"] == b"type=ajax&pdtSelYn=Y&pdtGrCd=01&pdtDcd="
    assert k1["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert k2["data"] == b"type=ajax&pdtSelYn=N&pdtGrCd=01&pdtDcd=05&basicDate=20120302&flag=A"
    assert u3.endswith("/front/announce/retrievePdtInfo.ajax")
    assert k3["data"] == b"type=ajax&fileType=05&pdtCd=D311887"
    assert {d.file_id for d in docs} == {"F004242259"}
    assert u4.endswith("/front/announce/retrievePdtDcd.ajax") and k4["data"] == b"type=ajax&pdtSelYn=Y&pdtGrCd=01"


def test_download_and_non_pdf():
    doc = nhfire.documents_of(nhfire.pick_period(nhfire.parse_periods(PERIODS)))[1]
    s = FakeSession([(200, b"%PDF-1.6\r%...", {"Content-Type": "application/octet-stream;charset=UTF-8"})])
    assert nhfire.download(s, doc).startswith(b"%PDF-")
    url, kw = s.sent[0]
    assert url == "https://www.nhfire.co.kr/imageView/downloadFile.ajax"
    assert kw["data"] == b"fileId=F004242259&afileSeqn=2" and kw["allow_redirects"] is False
    # 없는 서류(파일 이름이 빈 순번 3): 302로 다른 화면에 보낸다
    moved = (302, b"<head><title>Document moved</title>", {"Location": "http://www.nhfire.co.kr/file/downloadFile.nhfire",
                                                           "Content-Disposition": 'inline;filename="nullnull"'})
    with pytest.raises(ValueError, match="302"):
        nhfire.download(FakeSession([moved]), doc)
    with pytest.raises(ValueError, match="PDF가 아닌"):
        nhfire.download(FakeSession([(200, b"<html>error</html>", {"Content-Type": "text/html"})]), doc)
