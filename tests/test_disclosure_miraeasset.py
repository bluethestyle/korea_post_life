import json

import pytest

try:
    from postlife.disclosure import miraeasset
except ImportError:  # 초안을 저장소 밖에서 단독으로 돌릴 때
    import miraeasset

# 2026-11-19에 공시실에서 받은 응답의 형태 (행은 실제 응답에서 골라 옮김)
CATEGORIES = {"prodDvsnData": [{"text2": "보장성▷건강/암", "seq": 573546},
                               {"text2": "보장성▷간편고지/간편심사", "seq": 573666}]}
_META = {"file_path": "//upload/work_excel", "regp": "00133033", "tableCode": None,
         "file_nm": "D_상품공시_가격공시정리자료_20260801_v2.xlsx", "title": "2026년 08월공시",
         "regDtm": "2026-08-19 14:50:19", "workDvsn": "D", "text4": None, "text5": None, "pSeq": 472}


def _item(seq, cells):
    return {**_META, "text1": cells["sheetNm"], "text2": cells["cell0"], "text3": cells["cell1"], "seq": seq,
            "jsonData": json.dumps(cells, ensure_ascii=False)}


# 판매중인상품 탭: 열린 기간(종료일 "")과 닫힌 지난 기간. 사업방법서 파일 날짜가 판매 시작일과 다르다
OPEN = {"cell4": "M-케어 건강보험 무배당_상품요약서_20260711.pdf", "cell5": "M-케어 건강보험 무배당_약관_20260711.pdf",
        "cell2": "2026-07-11", "cell3": "", "sheetNo": "0", "cell6": "M-케어 건강보험 무배당_사업방법서_20260701.pdf",
        "cell7": "/html/gongci/upload/1/", "cell0": "보장성▷건강/암", "cell1": "M-케어 건강보험 무배당", "sheetNm": "판매중인상품"}
CLOSED = {**OPEN, "cell2": "2026-07-01", "cell3": "2026-07-10",
          "cell4": "M-케어 건강보험 무배당_상품요약서_20260701.pdf", "cell5": "M-케어 건강보험 무배당_약관_20260701.pdf"}
PAGE = {"list": [_item(573560, OPEN), _item(573561, CLOSED)], "rows": 120, "pageNum": 1, "totalPage": 2}
PAGE2 = {"list": [_item(573670, {**OPEN, "cell2": "2026-06-01", "cell3": "2026-06-30"})],
         "rows": 120, "pageNum": 2, "totalPage": 2}
# 판매중지상품 탭: cell4가 최종판매일이고 서류와 경로가 한 칸씩 밀린다
STOPPED = {"list": [_item(577100, {
    "cell4": "2023-09-30", "cell5": "헬스케어 간편건강생활보험(325) 무배당_상품요약서_20230501.pdf", "cell2": "2023-09-15",
    "cell3": "2023-09-30", "sheetNo": "1", "cell8": "/html/gongci/upload/1/",
    "cell6": "헬스케어 간편건강생활보험(325) 무배당_약관_20230501.pdf",
    "cell7": "헬스케어 간편건강생활보험(325) 무배당_사업방법서_20230915.pdf", "cell0": "보장성▷간편고지/간편심사",
    "cell1": "헬스케어 간편건강생활보험(325) 무배당", "sheetNm": "판매중지상품"})], "rows": 35, "pageNum": 1, "totalPage": 1}
# 검색어(text3)는 이름 일부 일치: 해약환급금이 없는 유형이 함께 온다
SEARCH = {"list": [_item(573688, {**OPEN, "cell1": "M-케어 건강보험(간편고지) 무배당", "cell2": "2026-07-01",
                                  "cell4": "M-케어 건강보험(간편고지) 무배당_상품요약서_20260701.pdf"}),
                   _item(573700, {**OPEN, "cell1": "M-케어 건강보험(간편고지) 무배당 [해약환급금이 없는 유형]",
                                  "cell2": "2024-04-01", "cell3": "2024-05-31"})],
          "rows": 2, "pageNum": 1, "totalPage": 1}
# Accept에 application/json이 없을 때: 상태 200, 본문은 "페이지: " 뒤에 HTML 안내 화면
NOTICE = '페이지: <!DOCTYPE html>\r\n<html lang="ko">\r\n<head>\r\n<title></title>'.encode()
# 없는 파일을 내려받을 때: 상태 200, text/html
MISSING = '\n\n\n<!DOCTYPE html>\n<html><head><title>Mirae Asset M-LIFE</title><script>alert("파일이 존재하지 않습니다.");</script>'.encode()
# 누리집 상품안내 메뉴(/home/prod/getProdList.do). JSON_DATA는 JSON 글이고 실제로는 상품 소개 글이 길게 들어 있다
MENU = {"prodInfo": [{"PROD_CD": "A3729", "ORDER_NUM": 6, "PROD_DVSN": "암/건강보험", "HOT_YN": "Y", "NEW_YN": "",
                      "PROD_NM": "M-케어 건강보험",
                      "JSON_DATA": json.dumps({"publicNm": "M-케어 건강보험 무배당", "publicCd": "A3729",
                                               "detailProdNm": "M-케어 건강보험", "prodType": "B"}, ensure_ascii=False)},
                     {"PROD_CD": "A3730", "ORDER_NUM": 0, "PROD_DVSN": "암/건강보험", "PROD_NM": "M-케어 건강보험(간편고지)",
                      "JSON_DATA": json.dumps({"publicNm": "M-케어 건강보험(간편고지) 무배당", "publicCd": "A3730"},
                                              ensure_ascii=False)}]}


def test_categories():
    assert miraeasset.parse_categories(CATEGORIES) == ["보장성▷건강/암", "보장성▷간편고지/간편심사"]


def test_page_rows_and_documents():
    page = miraeasset.parse_page(PAGE)
    assert (page.rows, page.page, page.pages) == (120, 1, 2)
    first, closed = page.periods
    assert (first.name, first.start, first.end, first.selling, first.category) == (
        "M-케어 건강보험 무배당", "2026-07-11", None, True, "보장성▷건강/암")
    assert closed.end == "2026-07-10" and first.source == "2026년 08월공시" and first.seq == "573560"
    docs = first.documents()
    assert [d.kind for d in docs] == ["상품요약서", "약관", "사업방법서"]
    assert docs[2].file_name.endswith("_20260701.pdf") and docs[2].start == "2026-07-11"
    assert {d.path for d in docs} == {"/html/gongci/upload/1/"}
    assert miraeasset.pick_period(page.periods) is first
    assert miraeasset.pick_period(page.periods, "2026-07-05") is closed
    assert miraeasset.pick_period(page.periods, "2026-01-01") is None


def test_stopped_tab_shifts_cells():
    (p,) = miraeasset.parse_page(STOPPED, selling=False).periods
    assert not p.selling and p.last_sale == "2023-09-30" and p.end == "2023-09-30"
    assert p.files["사업방법서"].endswith("_20230915.pdf") and p.path == "/html/gongci/upload/1/"
    # 탭 이름(sheetNm)이 행에 있으면 그것을 따른다
    assert not miraeasset.parse_page(STOPPED, selling=True).periods[0].selling


def test_multi_file_cell_and_json_list():
    cells = {**OPEN, "cell5": "약관_1.pdf\n약관_2.pdf"}
    body = {"list": [{"seq": 1, "jsonData": json.dumps([cells], ensure_ascii=False)}], "rows": 1, "pageNum": 1, "totalPage": 1}
    docs = miraeasset.parse_page(body).periods[0].documents()
    assert [d.file_name for d in docs if d.kind == "약관"] == ["약관_1.pdf", "약관_2.pdf"]


def test_bad_shapes_are_raised():
    with pytest.raises(ValueError, match="JSON이 아님"):
        miraeasset._json(NOTICE)
    with pytest.raises(ValueError, match="list"):
        miraeasset.parse_page({"rows": 0})
    with pytest.raises(ValueError, match="prodDvsnData"):
        miraeasset.parse_categories({"list": []})
    with pytest.raises(ValueError, match="암호화"):
        miraeasset.parse_codes({"sCmmnEncrypt": "abc"})


def test_codes_from_product_menu():
    assert miraeasset.parse_codes(MENU) == {"M-케어 건강보험 무배당": "A3729", "M-케어 건강보험(간편고지) 무배당": "A3730"}


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def post(self, url, **kw):
        self.sent.append(("POST", url, kw))
        reply = self.replies.pop(0)
        body = reply if isinstance(reply, bytes) else json.dumps(reply, ensure_ascii=False).encode()
        pdf = isinstance(reply, bytes) and reply.startswith(b"%PDF-")

        class R:
            content = body
            headers = {"Content-Type": "application/pdf;charset=EUC-KR" if pdf else "text/html; charset=UTF-8"}

            def raise_for_status(self):
                pass

        return R()


def test_list_products_walks_pages_and_sends_what_the_page_sends():
    s = FakeSession([PAGE, PAGE2])
    periods = miraeasset.list_products(s, category="보장성▷건강/암")
    assert len(periods) == 3
    (_, url1, kw1), (_, url2, kw2) = s.sent
    assert url1 == "https://life.miraeasset.com/micro/disclosure/selectWorkDvsnDataPaging.do"
    assert kw1["data"] == {"workDvsn": "D", "text1": "판매중인상품", "text2": "보장성▷건강/암", "text3": "", "pageNum": "0"}
    assert kw2["data"]["pageNum"] == "1"
    assert "application/json" in kw1["headers"]["Accept"]
    assert kw1["headers"]["Content-Type"] == "application/x-www-form-urlencoded; charset=UTF-8"
    s = FakeSession([CATEGORIES])
    miraeasset.list_categories(s, selling=False)
    assert s.sent[0][1].endswith("/micro/disclosure/selectProdDvsnGroup.do")
    assert s.sent[0][2]["data"] == {"workDvsn": "D", "text1": "판매중지상품"}


def test_list_documents_keeps_exact_name():
    s = FakeSession([SEARCH])
    docs = miraeasset.list_documents(s, "M-케어 건강보험(간편고지) 무배당")
    assert s.sent[0][2]["data"]["text3"] == "M-케어 건강보험(간편고지) 무배당"
    assert {d.name for d in docs} == {"M-케어 건강보험(간편고지) 무배당"} and docs[0].start == "2026-07-01"
    with pytest.raises(ValueError, match="JSON이 아님"):
        miraeasset.list_documents(FakeSession([NOTICE]), "x")


def test_download_form_and_non_pdf():
    doc = miraeasset.parse_page(PAGE).periods[0].documents()[0]
    s = FakeSession([b"%PDF-1.5 ..."])
    assert miraeasset.download(s, doc).startswith(b"%PDF-")
    # 실제로 내려받기에 성공한 요청과 같은 꼴 (경로 앞에 /uploadwas/life/ 를 붙여 "//"가 생긴다)
    assert s.sent[0][1] == "https://life.miraeasset.com/micro/cmmnFileDown.do"
    assert s.sent[0][2]["data"] == {"pathType": "gongci_u1", "fileName": "M-케어 건강보험 무배당_상품요약서_20260711.pdf",
                                    "orgFileName": "M-케어 건강보험 무배당_상품요약서_20260711.pdf",
                                    "filePath": "/uploadwas/life//html/gongci/upload/1/"}
    with pytest.raises(ValueError, match="파일이 존재하지 않습니다"):
        miraeasset.download(FakeSession([MISSING]), doc)
