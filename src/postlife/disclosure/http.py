"""공시실 접속용 세션. 구형 암호 방식만 받는 서버가 있어 암호 목록을 넓힌다. 인증서 검증은 그대로 한다."""
from __future__ import annotations

import ssl

import requests
from requests.adapters import HTTPAdapter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; postlife-disclosure)",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class LegacyCipherAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def session() -> requests.Session:
    s = requests.Session()
    s.mount("https://", LegacyCipherAdapter())
    s.headers.update(HEADERS)
    return s
