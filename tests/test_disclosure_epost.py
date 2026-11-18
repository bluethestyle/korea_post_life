from postlife.disclosure import epost

# 2026-11-18에 공시실에서 받은 응답의 형태
LIST = [
    {"GDS_CD": "P500130", "GDS_NM": "무배당 우체국간편한건강보험(20년갱신형) 2606 2종(간편가입325)",
     "GDS_BGNG_YMD": "20260617", "GDS_END_YMD": "99991231", "SPTL": "약관"},
    {"GDS_CD": "P500130", "GDS_NM": "무배당 우체국간편한건강보험(20년갱신형) 2606 2종(간편가입325)",
     "GDS_BGNG_YMD": "20260617", "GDS_END_YMD": "99991231", "SPTL": "상품요약서"},
    {"GDS_CD": "P400069", "GDS_NM": "무배당 우체국통합건강보험 2504", "GDS_BGNG_YMD": "20250403", "GDS_END_YMD": "20261231"},
]
DOCS = {"docsList": [
    {"insuBascDocuCd": "01", "orgnFileNm": "saeop_P500129-P500130-P500131-P500132_202606.pdf",
     "strgFileNm": "/dat_docs/01/saeop_P500129-P500130-P500131-P500132_202606.pdf",
     "frstRegDt": "2026-06-16 13:01:40.000", "useYn": "Y", "delYn": "N"},
    {"insuBascDocuCd": "04", "orgnFileNm": "yoyak.pdf", "strgFileNm": "/dat_docs/04/yoyak.pdf",
     "frstRegDt": "2026-06-16 13:01:40.000", "useYn": "Y", "delYn": "Y"},
    {"insuBascDocuCd": "99", "orgnFileNm": "etc.pdf", "strgFileNm": "/dat_docs/99/etc.pdf"},
]}


def test_products_are_deduplicated_by_code():
    products = epost.parse_products(LIST)
    assert [p.code for p in products] == ["P400069", "P500130"]
    assert products[1].start == "2026-06-17" and products[1].end is None
    assert products[0].end == "2026-12-31"


def test_documents_keep_only_known_kinds_in_use():
    docs = epost.parse_documents("P500130", DOCS)
    assert [(d.kind, d.registered) for d in docs] == [("사업방법서", "2026-06-16")]
    assert docs[0].path.startswith("/dat_docs/01/")


class FakeSession:
    def __init__(self, content):
        self.content = content
        self.sent = []

    def post(self, url, **kw):
        self.sent.append((url, kw))
        outer = self

        class R:
            content = outer.content

            def raise_for_status(self):
                pass

        return R()


def test_download_rejects_non_pdf():
    import pytest

    doc = epost.parse_documents("P500130", DOCS)[0]
    ok = FakeSession(b"%PDF-1.7 ...")
    assert epost.download(ok, doc).startswith(b"%PDF-")
    assert ok.sent[0][1]["data"]["localFilePath"] == doc.path
    with pytest.raises(ValueError):
        epost.download(FakeSession(b"<html>"), doc)
